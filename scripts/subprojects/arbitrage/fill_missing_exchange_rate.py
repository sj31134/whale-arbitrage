#!/usr/bin/env python3
"""
환율 데이터 보완 스크립트
- 주말/공휴일 등 누락된 환율 데이터를 근처 날짜의 값으로 보완
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"


def get_missing_dates(conn: sqlite3.Connection, start_date: str, end_date: str) -> List[str]:
    """누락된 날짜 목록 반환"""
    query = """
    WITH RECURSIVE dates(date) AS (
        SELECT ? as date
        UNION ALL
        SELECT date(date, '+1 day')
        FROM dates
        WHERE date < ?
    )
    SELECT d.date
    FROM dates d
    LEFT JOIN exchange_rate e ON d.date = e.date
    WHERE e.date IS NULL
    ORDER BY d.date
    """
    df = pd.read_sql(query, conn, params=(start_date, end_date))
    return df['date'].tolist()


def fill_missing_exchange_rate(conn: sqlite3.Connection, missing_dates: List[str]) -> int:
    """누락된 환율 데이터를 근처 날짜의 값으로 보완"""
    filled_count = 0
    
    for missing_date in missing_dates:
        # 앞뒤 날짜의 환율 조회
        query = """
        SELECT date, krw_usd
        FROM exchange_rate
        WHERE date IN (
            SELECT MAX(date) FROM exchange_rate WHERE date < ?
            UNION
            SELECT MIN(date) FROM exchange_rate WHERE date > ?
        )
        ORDER BY date
        """
        df = pd.read_sql(query, conn, params=(missing_date, missing_date))
        
        if len(df) == 0:
            continue
        
        # 가장 가까운 날짜의 환율 사용
        if len(df) == 1:
            rate = df['krw_usd'].iloc[0]
        else:
            # 앞뒤 날짜가 모두 있으면 평균값 사용
            rate = df['krw_usd'].mean()
        
        # INSERT
        insert_query = "INSERT OR IGNORE INTO exchange_rate (date, krw_usd) VALUES (?, ?)"
        conn.execute(insert_query, (missing_date, rate))
        filled_count += 1
    
    conn.commit()
    return filled_count


def main():
    """메인 함수"""
    print("=" * 60)
    print("환율 데이터 보완 스크립트")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. 현재 데이터 범위 확인
    query = "SELECT MIN(date) as min_date, MAX(date) as max_date FROM exchange_rate"
    df = pd.read_sql(query, conn)
    
    if df.empty or df['min_date'].iloc[0] is None:
        print("❌ 환율 데이터가 없습니다.")
        conn.close()
        return
    
    min_date = df['min_date'].iloc[0]
    max_date = df['max_date'].iloc[0]
    
    print(f"\n현재 데이터 범위: {min_date} ~ {max_date}")
    
    # 2. 누락된 날짜 확인
    print("\n누락된 날짜 확인 중...")
    missing_dates = get_missing_dates(conn, min_date, max_date)
    
    if not missing_dates:
        print("✅ 누락된 날짜가 없습니다.")
        conn.close()
        return
    
    print(f"누락된 날짜: {len(missing_dates)}일")
    print(f"처음 10개: {missing_dates[:10]}")
    if len(missing_dates) > 10:
        print(f"마지막 10개: {missing_dates[-10:]}")
    
    # 3. 보완 실행
    print(f"\n환율 데이터 보완 중...")
    filled_count = fill_missing_exchange_rate(conn, missing_dates)
    
    print(f"✅ {filled_count}일의 환율 데이터를 보완했습니다.")
    
    # 4. 보완 후 확인
    print("\n보완 후 상태 확인...")
    missing_after = get_missing_dates(conn, min_date, max_date)
    
    if not missing_after:
        print("✅ 모든 날짜의 환율 데이터가 보완되었습니다.")
    else:
        print(f"⚠️ 여전히 {len(missing_after)}일의 데이터가 누락되어 있습니다.")
    
    conn.close()


if __name__ == "__main__":
    main()

