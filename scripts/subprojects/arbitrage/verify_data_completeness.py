#!/usr/bin/env python3
"""
2024-01-01부터 현재까지 데이터 완전성 검증 및 누락 날짜 파악
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

def get_date_range(start_date, end_date):
    """날짜 범위 생성"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

def check_data_completeness():
    """데이터 완전성 확인"""
    conn = sqlite3.connect(DB_PATH)
    
    start_date = "2024-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📊 데이터 완전성 검증 ({start_date} ~ {end_date})")
    print("=" * 60)
    
    # 1. 각 거래소별 데이터 확인
    queries = {
        'upbit': """
            SELECT date FROM upbit_daily 
            WHERE market = 'KRW-BTC' AND date >= '2024-01-01'
            ORDER BY date
        """,
        'binance': """
            SELECT date FROM binance_spot_daily 
            WHERE symbol = 'BTCUSDT' AND date >= '2024-01-01'
            ORDER BY date
        """,
        'bitget': """
            SELECT date FROM bitget_spot_daily 
            WHERE symbol = 'BTCUSDT' AND date >= '2024-01-01'
            ORDER BY date
        """
    }
    
    data_by_exchange = {}
    for exchange, query in queries.items():
        df = pd.read_sql(query, conn)
        dates = set(df['date'].tolist())
        data_by_exchange[exchange] = dates
        print(f"\n{exchange.upper()}:")
        print(f"  - 데이터 개수: {len(dates)}건")
        print(f"  - 최소 날짜: {min(dates) if dates else 'N/A'}")
        print(f"  - 최대 날짜: {max(dates) if dates else 'N/A'}")
    
    # 2. 전체 날짜 범위 생성
    all_dates = set(get_date_range(start_date, end_date))
    print(f"\n전체 기간: {len(all_dates)}일")
    
    # 3. 각 거래소별 누락 날짜 확인
    print("\n📋 누락 날짜 확인:")
    missing_by_exchange = {}
    for exchange, dates in data_by_exchange.items():
        missing = sorted(list(all_dates - dates))
        missing_by_exchange[exchange] = missing
        print(f"\n{exchange.upper()} 누락: {len(missing)}일")
        if len(missing) <= 20:
            print(f"  {missing}")
        else:
            print(f"  처음 10일: {missing[:10]}")
            print(f"  마지막 10일: {missing[-10:]}")
    
    # 4. 공통 날짜 확인 (모든 거래소에 있는 날짜)
    common_dates = all_dates
    for dates in data_by_exchange.values():
        common_dates = common_dates & dates
    
    print(f"\n✅ 공통 날짜 (모든 거래소): {len(common_dates)}일")
    print(f"   최소: {min(common_dates) if common_dates else 'N/A'}")
    print(f"   최대: {max(common_dates) if common_dates else 'N/A'}")
    
    # 5. JOIN 가능한 데이터 확인
    join_query = """
        SELECT 
            u.date,
            CASE WHEN u.date IS NOT NULL THEN 1 ELSE 0 END as has_upbit,
            CASE WHEN b.date IS NOT NULL THEN 1 ELSE 0 END as has_binance,
            CASE WHEN bg.date IS NOT NULL THEN 1 ELSE 0 END as has_bitget
        FROM (
            SELECT DISTINCT date FROM upbit_daily WHERE market = 'KRW-BTC' AND date >= '2024-01-01'
            UNION
            SELECT DISTINCT date FROM binance_spot_daily WHERE symbol = 'BTCUSDT' AND date >= '2024-01-01'
            UNION
            SELECT DISTINCT date FROM bitget_spot_daily WHERE symbol = 'BTCUSDT' AND date >= '2024-01-01'
        ) all_dates
        LEFT JOIN (SELECT DISTINCT date FROM upbit_daily WHERE market = 'KRW-BTC' AND date >= '2024-01-01') u ON all_dates.date = u.date
        LEFT JOIN (SELECT DISTINCT date FROM binance_spot_daily WHERE symbol = 'BTCUSDT' AND date >= '2024-01-01') b ON all_dates.date = b.date
        LEFT JOIN (SELECT DISTINCT date FROM bitget_spot_daily WHERE symbol = 'BTCUSDT' AND date >= '2024-01-01') bg ON all_dates.date = bg.date
        ORDER BY all_dates.date
    """
    
    join_df = pd.read_sql(join_query, conn)
    complete_rows = join_df[(join_df['has_upbit'] == 1) & (join_df['has_binance'] == 1) & (join_df['has_bitget'] == 1)]
    
    print(f"\n🔗 JOIN 가능한 데이터: {len(complete_rows)}일")
    print(f"   최소: {complete_rows['date'].min() if not complete_rows.empty else 'N/A'}")
    print(f"   최대: {complete_rows['date'].max() if not complete_rows.empty else 'N/A'}")
    
    incomplete_rows = join_df[(join_df['has_upbit'] == 0) | (join_df['has_binance'] == 0) | (join_df['has_bitget'] == 0)]
    if not incomplete_rows.empty:
        print(f"\n⚠️ 불완전한 데이터: {len(incomplete_rows)}일")
        print("   처음 10일:")
        print(incomplete_rows.head(10)[['date', 'has_upbit', 'has_binance', 'has_bitget']])
    
    conn.close()
    
    return missing_by_exchange, common_dates

if __name__ == "__main__":
    missing_by_exchange, common_dates = check_data_completeness()

