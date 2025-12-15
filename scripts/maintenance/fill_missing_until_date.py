#!/usr/bin/env python3
"""
데이터 소스 부재/수집 공백 등으로 인해 특정 테이블이 목표 종료일까지 비어있는 경우,
SQLite에서 누락 날짜를 생성하여 '0 또는 직전값'으로 채웁니다.

⚠️ 주의: 이는 '실제 수집'이 아니라 **임시 보정(placeholder/forward-fill)** 입니다.
실제 온체인/외부 API 수집이 가능해지면 해당 구간을 재수집/재집계해야 합니다.
"""

import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "project.db"


def daterange(start: datetime, end_inclusive: datetime):
    cur = start
    while cur <= end_inclusive:
        yield cur.date().isoformat()
        cur += timedelta(days=1)


def fill_bitinfocharts_whale(conn: sqlite3.Connection, end_date: str):
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT coin FROM bitinfocharts_whale")
    coins = [r[0] for r in cur.fetchall()]
    for coin in coins:
        cur.execute(
            "SELECT date, top100_richest_pct, avg_transaction_value_btc FROM bitinfocharts_whale WHERE coin=? ORDER BY date DESC LIMIT 1",
            (coin,),
        )
        row = cur.fetchone()
        if not row:
            continue
        last_date, last_pct, last_avg = row
        if last_date >= end_date:
            continue
        start_dt = datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        for d in daterange(start_dt, end_dt):
            cur.execute(
                """
                INSERT OR IGNORE INTO bitinfocharts_whale (date, coin, top100_richest_pct, avg_transaction_value_btc)
                VALUES (?, ?, ?, ?)
                """,
                (d, coin, last_pct, last_avg),
            )
    conn.commit()
    cur.close()


def fill_whale_daily_stats(conn: sqlite3.Connection, end_date: str):
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT coin_symbol FROM whale_daily_stats")
    coins = [r[0] for r in cur.fetchall()]
    for coin in coins:
        cur.execute(
            """
            SELECT date, exchange_inflow_usd, exchange_outflow_usd, net_flow_usd, whale_to_whale_usd,
                   active_addresses, large_tx_count, avg_tx_size_usd
            FROM whale_daily_stats
            WHERE coin_symbol=?
            ORDER BY date DESC
            LIMIT 1
            """,
            (coin,),
        )
        row = cur.fetchone()
        if not row:
            continue
        last_date = row[0]
        last_vals = row[1:]
        if last_date >= end_date:
            continue
        start_dt = datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        for d in daterange(start_dt, end_dt):
            # forward-fill (임시)
            cur.execute(
                """
                INSERT OR IGNORE INTO whale_daily_stats
                (date, coin_symbol, exchange_inflow_usd, exchange_outflow_usd, net_flow_usd, whale_to_whale_usd,
                 active_addresses, large_tx_count, avg_tx_size_usd)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (d, coin, *last_vals),
            )
    conn.commit()
    cur.close()


def main():
    parser = argparse.ArgumentParser(description="Fill missing rows up to end-date (placeholder/forward-fill)")
    parser.add_argument("--end-date", type=str, required=True, help="종료일(포함) YYYY-MM-DD")
    args = parser.parse_args()

    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    fill_bitinfocharts_whale(conn, args.end_date)
    fill_whale_daily_stats(conn, args.end_date)
    conn.close()
    print(f"✅ placeholder fill 완료 (end-date={args.end_date})")


if __name__ == "__main__":
    main()


