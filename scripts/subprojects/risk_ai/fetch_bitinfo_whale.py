#!/usr/bin/env python3
"""
BitInfoCharts 고래 지표를 스크래핑하여 SQLite에 저장하는 스크립트입니다.
"""

import re
import sqlite3
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"
load_dotenv(ROOT / "config" / ".env")
BITINFO_SILOS = {
    "BTC": "https://bitinfocharts.com/top-100-richest-bitcoin-addresses.html",
    "ETH": "https://bitinfocharts.com/top-100-richest-ethereum-addresses.html",
}


def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def upsert_whale(rows):
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT OR REPLACE INTO bitinfocharts_whale
        (date, coin, top100_richest_pct, avg_transaction_value_btc)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    cur.close()
    conn.close()


def parse_stats(coin, html):
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator=" ")
    top100_pct = None
    avg_tx = None

    pct_match = re.search(r"Top\s*100\s.*?([\d\.,]+)%", text)
    if pct_match:
        top100_pct = float(pct_match.group(1).replace(",", ""))

    avg_match = re.search(r"Avg(?:\.|average)\s*transaction\s*(?:value|size)\s*[:\-]?\s*\$?([\d\.,]+)", text, re.IGNORECASE)
    if avg_match:
        avg_tx_value = avg_match.group(1).replace(",", "")
        avg_tx = float(avg_tx_value)

    date_str = soup.find("meta", {"property": "og:description"})
    date_text = date_str["content"] if date_str else ""
    date_match = re.search(r"As\s+at\s+([A-Za-z]{3}-\d{2}-\d{4})", date_text)
    dt = (
        datetime.strptime(date_match.group(1), "%b-%d-%Y").date().isoformat()
        if date_match
        else time.strftime("%Y-%m-%d")
    )

    return dt, coin, top100_pct or 0.0, avg_tx or 0.0


import cloudscraper

def fetch_coin(coin, url):
    # Cloudscraper 사용: Cloudflare 보호 우회
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    try:
        response = scraper.get(url, timeout=30)
        if response.status_code != 200:
            response.raise_for_status()
        return parse_stats(coin, response.text)
    except Exception as e:
        print(f"⚠️ Cloudscraper 시도 실패 ({coin}): {e}")
        raise e


def main():
    ensure_db()
    rows = []
    for coin, url in BITINFO_SILOS.items():
        try:
            row = fetch_coin(coin, url)
            rows.append(row)
            print(f"✅ BitInfoCharts: {coin} {row[0]}")
        except Exception as exc:
            print(f"⚠️ {coin} 스크랩 실패: {exc}")
        time.sleep(1.0)

    upsert_whale(rows)


if __name__ == "__main__":
    from datetime import datetime

    main()

