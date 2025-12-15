#!/usr/bin/env python3
"""
Supabase whale_transactions를 기반으로 SQLite의
- whale_daily_stats
- whale_weekly_stats
를 지정 종료일(포함)까지 갱신하는 스크립트.

주의:
- Supabase에 whale_transactions가 해당 기간까지 존재해야 합니다.
- 이 스크립트는 "누락 구간만" 대상으로 집계를 실행합니다.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / "config" / ".env", override=True)


def main():
    parser = argparse.ArgumentParser(description="Update whale_daily_stats/whale_weekly_stats until target date")
    parser.add_argument("--end-date", type=str, required=True, help="종료일(포함) YYYY-MM-DD")
    parser.add_argument("--coins", type=str, default="BTC,ETH", help="집계 코인 리스트 (comma-separated), 기본 BTC,ETH")
    args = parser.parse_args()

    end_inclusive = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    end_exclusive = pd.Timestamp(end_inclusive + timedelta(days=1), tz="UTC")
    coins = [c.strip() for c in args.coins.split(",") if c.strip()]

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase 환경 변수가 없습니다. config/.env의 SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY 확인 필요")

    supabase = create_client(supabase_url, supabase_key)

    # SQLite에서 coin별 max(date) 조회 -> 다음날부터 집계
    import sqlite3

    db_path = ROOT / "data" / "project.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 필요한 함수 import (pandas 의존)
    from scripts.subprojects.risk_ai.aggregate_whale_stats import ensure_tables, aggregate_daily_whale_stats, aggregate_weekly_whale_stats

    ensure_tables()

    for coin in coins:
        cur.execute("SELECT MAX(date) FROM whale_daily_stats WHERE coin_symbol = ?", (coin,))
        row = cur.fetchone()
        max_date = row[0] if row and row[0] else None
        if max_date and max_date >= end_inclusive.isoformat():
            print(f"⏭️ whale_daily_stats {coin}: 이미 최신 ({max_date})")
            continue

        if max_date:
            start_dt = pd.Timestamp(datetime.strptime(max_date, "%Y-%m-%d").date() + timedelta(days=1), tz="UTC")
        else:
            # 데이터가 없으면 2022-01-01부터(기존 테이블 최소 범위와 정합)
            start_dt = pd.Timestamp("2022-01-01", tz="UTC")

        if start_dt >= end_exclusive:
            print(f"⏭️ whale_daily_stats {coin}: 업데이트할 기간 없음")
            continue

        print(f"🔄 whale_daily_stats {coin}: {start_dt.date()} ~ {end_inclusive} 집계 중...")
        aggregate_daily_whale_stats(supabase, start_dt, end_exclusive, coin_symbols=[coin])

    cur.close()
    conn.close()

    # 주봉은 일봉 테이블 기준으로 재집계 (빠름)
    print("🔄 whale_weekly_stats 재집계 중...")
    aggregate_weekly_whale_stats()

    # 종료일 이후(week_start)가 들어갔다면 제거 (week_start=월요일 기준)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM whale_weekly_stats WHERE date > ?", (end_inclusive.isoformat(),))
    conn.commit()

    # 결과 요약
    cur.execute("SELECT coin_symbol, MIN(date), MAX(date), COUNT(*) FROM whale_daily_stats GROUP BY coin_symbol ORDER BY coin_symbol")
    print("✅ whale_daily_stats:")
    for row in cur.fetchall():
        print(f" - {row[0]}: {row[1]} ~ {row[2]} ({row[3]}일)")

    cur.execute("SELECT coin_symbol, MIN(date), MAX(date), COUNT(*) FROM whale_weekly_stats GROUP BY coin_symbol ORDER BY coin_symbol")
    print("✅ whale_weekly_stats:")
    for row in cur.fetchall():
        print(f" - {row[0]}: {row[1]} ~ {row[2]} ({row[3]}주)")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()


