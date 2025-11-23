#!/usr/bin/env python3
"""
BitInfoCharts 과거 데이터 수집 (Wayback Machine 활용)
- 2023-01-01부터 현재까지의 Top 100 Richest List 스냅샷을 Wayback Machine에서 가져옴
"""

import sqlite3
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import cloudscraper

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

BITINFO_URLS = {
    "BTC": "https://bitinfocharts.com/top-100-richest-bitcoin-addresses.html",
    "ETH": "https://bitinfocharts.com/top-100-richest-ethereum-addresses.html",
}

WAYBACK_API = "https://web.archive.org/cdx/search/cdx"


def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def upsert_whale(date_str, coin, top100_pct, avg_tx_value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO bitinfocharts_whale 
        (date, coin, top100_richest_pct, avg_transaction_value_btc)
        VALUES (?, ?, ?, ?)
    """, (date_str, coin, top100_pct, avg_tx_value))
    conn.commit()
    conn.close()


def get_wayback_snapshots(url, start_date, end_date):
    """Wayback Machine에서 특정 URL의 스냅샷 목록 가져오기"""
    params = {
        "url": url,
        "from": start_date.strftime("%Y%m%d"),
        "to": end_date.strftime("%Y%m%d"),
        "output": "json",
        "collapse": "timestamp:8"  # 일별로 하나씩만
    }
    
    try:
        response = requests.get(WAYBACK_API, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # 첫 번째 행은 헤더
        if len(data) <= 1:
            return []
        
        snapshots = []
        for row in data[1:]:  # 헤더 제외
            if len(row) >= 2:
                timestamp = row[1]  # YYYYMMDDHHmmss
                wayback_url = f"https://web.archive.org/web/{timestamp}/{url}"
                snapshots.append({
                    "timestamp": timestamp,
                    "date": timestamp[:8],  # YYYYMMDD
                    "url": wayback_url
                })
        
        return snapshots
    except Exception as e:
        print(f"⚠️ Wayback API 오류: {e}")
        return []


def parse_stats_from_html(html, coin):
    """HTML에서 통계 파싱"""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator=" ")
    
    top100_pct = None
    avg_tx = None
    
    # Top 100 richest percentage
    pct_match = re.search(r"Top\s*100\s.*?([\d\.,]+)%", text)
    if pct_match:
        top100_pct = float(pct_match.group(1).replace(",", ""))
    
    # Average transaction value
    avg_match = re.search(r"Avg(?:\.|average)\s*transaction\s*(?:value|size)\s*[:\-]?\s*\$?([\d\.,]+)", text, re.IGNORECASE)
    if avg_match:
        avg_tx_value = avg_match.group(1).replace(",", "")
        try:
            avg_tx = float(avg_tx_value)
        except ValueError:
            pass
    
    return top100_pct, avg_tx


def fetch_snapshot(wayback_url):
    """Wayback Machine 스냅샷에서 데이터 추출"""
    scraper = cloudscraper.create_scraper()
    
    # HTTPS로 변경
    if wayback_url.startswith("http://"):
        wayback_url = wayback_url.replace("http://", "https://", 1)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = scraper.get(wayback_url, timeout=30)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                # 스냅샷이 없음
                return None
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"  ⚠️ 스냅샷 다운로드 실패 (재시도 {attempt+1}/{max_retries}): {e}")
                return None
    return None


def collect_historical_data(coin, url):
    """과거 데이터 수집"""
    print(f"\n📊 {coin} 과거 데이터 수집 시작...")
    
    # 2023-01-01부터 현재까지
    start_date = datetime(2023, 1, 1)
    end_date = datetime.now()
    
    # Wayback Machine에서 스냅샷 목록 가져오기
    print(f"  🔍 Wayback Machine 스냅샷 검색 중...")
    snapshots = get_wayback_snapshots(url, start_date, end_date)
    
    if not snapshots:
        print(f"  ⚠️ {coin} 스냅샷 없음")
        return
    
    print(f"  ✅ {len(snapshots)}개 스냅샷 발견")
    
    # 각 스냅샷 처리
    success_count = 0
    for i, snapshot in enumerate(snapshots[:100]):  # 최대 100개만 (너무 많으면 시간 오래 걸림)
        date_str = snapshot["date"]
        wayback_url = snapshot["url"]
        
        # YYYYMMDD -> YYYY-MM-DD
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        print(f"  [{i+1}/{min(len(snapshots), 100)}] {formatted_date} 처리 중...", end=" ")
        
        html = fetch_snapshot(wayback_url)
        if html:
            top100_pct, avg_tx = parse_stats_from_html(html, coin)
            
            if top100_pct is not None or avg_tx is not None:
                upsert_whale(
                    formatted_date,
                    coin,
                    top100_pct or 0.0,
                    avg_tx or 0.0
                )
                success_count += 1
                print(f"✅")
            else:
                print(f"⚠️ 파싱 실패")
        else:
            print(f"⚠️ 다운로드 실패")
        
        time.sleep(0.5)  # Rate limit
    
    print(f"  ✅ {coin}: {success_count}건 수집 완료")


def main():
    ensure_db()
    
    # BTC 수집
    collect_historical_data("BTC", BITINFO_URLS["BTC"])
    
    # ETH 수집 (500 에러가 나더라도 Wayback Machine은 시도)
    collect_historical_data("ETH", BITINFO_URLS["ETH"])


if __name__ == "__main__":
    main()

