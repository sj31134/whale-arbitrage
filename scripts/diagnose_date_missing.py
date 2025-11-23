#!/usr/bin/env python3
"""
날짜 누락 원인 진단 스크립트
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "utils"))
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "arbitrage"))

from data_loader import DataLoader
from backtest_engine_optimized import OptimizedArbitrageBacktest


def diagnose_date_missing(target_date_str="2024-11-19", coin="BTC"):
    """날짜 누락 원인 진단"""
    print("=" * 60)
    print(f"날짜 누락 원인 진단: {target_date_str}")
    print("=" * 60)
    
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    conn = sqlite3.connect(ROOT / "data" / "project.db")
    
    # 1. 각 테이블별 데이터 확인
    print("\n[1단계] 각 테이블별 데이터 확인")
    print("-" * 60)
    
    tables = {
        'upbit_daily': ("SELECT date, market, trade_price FROM upbit_daily WHERE date = ? AND market = ?", 
                       (target_date_str, 'KRW-BTC')),
        'binance_spot_daily': ("SELECT date, symbol, close FROM binance_spot_daily WHERE date = ? AND symbol = ?",
                              (target_date_str, 'BTCUSDT')),
        'bitget_spot_daily': ("SELECT date, symbol, close FROM bitget_spot_daily WHERE date = ? AND symbol = ?",
                             (target_date_str, 'BTCUSDT')),
        'exchange_rate': ("SELECT date, krw_usd FROM exchange_rate WHERE date = ?", (target_date_str,))
    }
    
    table_status = {}
    for table, (query, params) in tables.items():
        df = pd.read_sql(query, conn, params=params)
        has_data = len(df) > 0
        table_status[table] = has_data
        status = "✅ 있음" if has_data else "❌ 없음"
        print(f"{table:20s}: {status}")
        if has_data:
            print(f"  {df.to_string()}")
    
    # 2. INTERSECT로 확인 (모든 테이블에 데이터가 있는 날짜)
    print("\n[2단계] 모든 테이블에 데이터가 있는 날짜 확인")
    print("-" * 60)
    
    query = """
    SELECT date
    FROM (
        SELECT date FROM upbit_daily WHERE market = 'KRW-BTC'
        INTERSECT
        SELECT date FROM binance_spot_daily WHERE symbol = 'BTCUSDT'
        INTERSECT
        SELECT date FROM bitget_spot_daily WHERE symbol = 'BTCUSDT'
    )
    WHERE date = ?
    """
    df_intersect = pd.read_sql(query, conn, params=(target_date_str,))
    has_intersect = len(df_intersect) > 0
    print(f"INTERSECT 결과: {'✅ 있음' if has_intersect else '❌ 없음'}")
    
    # 3. load_exchange_data로 확인
    print("\n[3단계] load_exchange_data로 확인")
    print("-" * 60)
    
    loader = DataLoader()
    start_date = (target_date - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = (target_date + timedelta(days=30)).strftime("%Y-%m-%d")
    
    df_loaded = loader.load_exchange_data(start_date, end_date, coin)
    target_in_loaded = len(df_loaded[df_loaded['date'].dt.date == target_date.date()]) > 0
    
    print(f"로드 기간: {start_date} ~ {end_date}")
    print(f"로드된 데이터: {len(df_loaded)}건")
    print(f"2024-11-19 포함: {'✅ 있음' if target_in_loaded else '❌ 없음'}")
    
    if not target_in_loaded and len(df_loaded) > 0:
        # NULL 값 확인
        target_row = df_loaded[df_loaded['date'].dt.date == target_date.date()]
        if len(target_row) > 0:
            print("\n⚠️ 날짜는 있지만 NULL 값이 있을 수 있음:")
            print(target_row[['date', 'upbit_price', 'binance_price', 'bitget_price', 'krw_usd']].to_string())
    
    # 4. calculate_indicators 후 확인
    print("\n[4단계] calculate_indicators 후 확인")
    print("-" * 60)
    
    if len(df_loaded) >= 30:
        backtest = OptimizedArbitrageBacktest(rolling_window=30)
        df_calc = backtest.calculate_indicators(df_loaded)
        
        target_in_calc = len(df_calc[df_calc['date'].dt.date == target_date.date()]) > 0
        
        print(f"지표 계산 후 데이터: {len(df_calc)}건")
        print(f"2024-11-19 포함: {'✅ 있음' if target_in_calc else '❌ 없음'}")
        
        if not target_in_calc:
            print(f"\n⚠️ 원인 분석:")
            print(f"  - 원본 데이터: {len(df_loaded)}건")
            print(f"  - 계산 후 데이터: {len(df_calc)}건")
            print(f"  - 제외된 데이터: {len(df_loaded) - len(df_calc)}건")
            
            if len(df_loaded) > 0 and len(df_calc) > 0:
                print(f"  - 원본 날짜 범위: {df_loaded['date'].min()} ~ {df_loaded['date'].max()}")
                print(f"  - 계산 후 날짜 범위: {df_calc['date'].min()} ~ {df_calc['date'].max()}")
                
                # rolling window로 인해 처음 30일이 제외됨
                first_date_in_calc = df_calc['date'].min()
                days_excluded = (first_date_in_calc.date() - df_loaded['date'].min().date()).days
                print(f"  - 제외된 일수: {days_excluded}일 (rolling window: 30일)")
                
                if target_date.date() < first_date_in_calc.date():
                    print(f"\n  ❌ 원인: {target_date_str}가 rolling window로 인해 제외된 기간({df_loaded['date'].min().date()} ~ {first_date_in_calc.date()})에 포함됨")
    
    # 5. 종합 진단
    print("\n" + "=" * 60)
    print("[종합 진단]")
    print("=" * 60)
    
    issues = []
    
    # 각 테이블별 누락 확인
    missing_tables = [table for table, has_data in table_status.items() if not has_data]
    if missing_tables:
        issues.append(f"❌ 다음 테이블에 데이터 없음: {', '.join(missing_tables)}")
    
    # INTERSECT 누락 확인
    if not has_intersect:
        issues.append("❌ 모든 테이블에 데이터가 있는 날짜가 아님 (INTERSECT 실패)")
    
    # load_exchange_data 누락 확인
    if not target_in_loaded:
        issues.append("❌ load_exchange_data에서 데이터를 찾을 수 없음")
    
    # calculate_indicators 누락 확인
    if len(df_loaded) >= 30:
        if not target_in_calc:
            issues.append("❌ calculate_indicators 후 데이터가 제외됨 (rolling window 영향)")
    
    if issues:
        print("발견된 문제:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✅ 모든 단계에서 데이터 확인됨")
    
    conn.close()
    loader.close()
    
    return issues


if __name__ == "__main__":
    import sys
    target_date = sys.argv[1] if len(sys.argv) > 1 else "2024-11-19"
    diagnose_date_missing(target_date)

