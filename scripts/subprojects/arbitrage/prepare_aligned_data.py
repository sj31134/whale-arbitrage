#!/usr/bin/env python3
"""
2024-01-01부터 현재까지 동일한 날짜로 정렬된 데이터 준비
비트겟 데이터가 없는 기간은 제외하고, 공통 날짜만 사용
"""

import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

def prepare_aligned_data(start_date="2024-01-01", end_date=None):
    """모든 거래소에서 공통으로 존재하는 날짜만 추출"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(DB_PATH)
    
    print(f"📊 데이터 정렬 준비 ({start_date} ~ {end_date})")
    print("=" * 60)
    
    # 공통 날짜 찾기 (모든 거래소에 있는 날짜)
    query = f"""
        SELECT u.date
        FROM upbit_daily u
        INNER JOIN binance_spot_daily b ON u.date = b.date AND b.symbol = 'BTCUSDT'
        INNER JOIN bitget_spot_daily bg ON u.date = bg.date AND bg.symbol = 'BTCUSDT'
        WHERE u.market = 'KRW-BTC'
        AND u.date >= '{start_date}' AND u.date <= '{end_date}'
        ORDER BY u.date
    """
    
    common_dates_df = pd.read_sql(query, conn)
    
    if common_dates_df.empty:
        print("⚠️ 공통 날짜가 없습니다. 비트겟 데이터가 없는 기간을 확인하세요.")
        conn.close()
        return None
    
    print(f"✅ 공통 날짜: {len(common_dates_df)}일")
    print(f"   최소: {common_dates_df['date'].min()}")
    print(f"   최대: {common_dates_df['date'].max()}")
    
    # 정렬된 데이터 조회
    aligned_query = f"""
        SELECT 
            u.date,
            u.trade_price as upbit_price,
            u.opening_price as upbit_open,
            u.high_price as upbit_high,
            u.low_price as upbit_low,
            b.close as binance_price,
            b.open as binance_open,
            b.high as binance_high,
            b.low as binance_low,
            bg.close as bitget_price,
            bg.open as bitget_open,
            bg.high as bitget_high,
            bg.low as bitget_low,
            e.krw_usd
        FROM upbit_daily u
        INNER JOIN binance_spot_daily b ON u.date = b.date AND b.symbol = 'BTCUSDT'
        INNER JOIN bitget_spot_daily bg ON u.date = bg.date AND bg.symbol = 'BTCUSDT'
        LEFT JOIN exchange_rate e ON u.date = e.date
        WHERE u.market = 'KRW-BTC'
        AND u.date >= '{start_date}' AND u.date <= '{end_date}'
        AND u.date IN (SELECT date FROM ({query}))
        ORDER BY u.date
    """
    
    df = pd.read_sql(aligned_query, conn)
    df['date'] = pd.to_datetime(df['date'])
    
    # 환율 결측치 처리
    df['krw_usd'] = df['krw_usd'].ffill().bfill()
    
    print(f"\n✅ 정렬된 데이터: {len(df)}건")
    print(f"   날짜 범위: {df['date'].min().strftime('%Y-%m-%d')} ~ {df['date'].max().strftime('%Y-%m-%d')}")
    
    # 데이터 품질 확인
    print("\n📋 데이터 품질 확인:")
    print(f"   업비트 NULL: {df['upbit_price'].isnull().sum()}건")
    print(f"   바이낸스 NULL: {df['binance_price'].isnull().sum()}건")
    print(f"   비트겟 NULL: {df['bitget_price'].isnull().sum()}건")
    print(f"   환율 NULL: {df['krw_usd'].isnull().sum()}건")
    
    conn.close()
    
    return df

def save_aligned_data(df, output_path=None):
    """정렬된 데이터를 CSV로 저장"""
    if output_path is None:
        output_path = ROOT / "data" / "aligned_3exchanges_data.csv"
    
    df.to_csv(output_path, index=False)
    print(f"\n💾 정렬된 데이터 저장 완료: {output_path}")
    return output_path

if __name__ == "__main__":
    # 비트겟 데이터가 있는 기간으로 조정
    # 비트겟은 2025-05-07부터 데이터가 있음
    df = prepare_aligned_data(start_date="2025-05-07")
    
    if df is not None:
        save_aligned_data(df)
        
        # 요약 통계
        print("\n📊 데이터 요약:")
        print(f"   총 일수: {len(df)}일")
        print(f"   업비트 평균 가격: {df['upbit_price'].mean():,.0f} KRW")
        print(f"   바이낸스 평균 가격: {df['binance_price'].mean():,.2f} USDT")
        print(f"   비트겟 평균 가격: {df['bitget_price'].mean():,.2f} USDT")
    else:
        print("\n❌ 데이터 정렬 실패")

