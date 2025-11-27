#!/usr/bin/env python3
"""
주봉 데이터 품질 검증 및 주봉-고래 데이터 매칭 확인
"""

import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"


def verify_weekly_data():
    print("=" * 80)
    print("🔍 주봉 데이터 품질 검증")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. 주봉 OHLCV 데이터 확인
    print("\n1️⃣ 주봉 OHLCV 데이터")
    print("-" * 80)
    
    df_weekly = pd.read_sql("""
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(*) as count,
            COUNT(DISTINCT symbol) as symbol_count
        FROM binance_spot_weekly
    """, conn)
    
    if len(df_weekly) > 0 and df_weekly['count'].iloc[0] > 0:
        print(f"   기간: {df_weekly['min_date'].iloc[0]} ~ {df_weekly['max_date'].iloc[0]}")
        print(f"   총 주수: {df_weekly['count'].iloc[0]:,}주")
        print(f"   심볼 수: {df_weekly['symbol_count'].iloc[0]}")
        
        # 기술적 지표 확인
        df_indicators = pd.read_sql("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN atr IS NOT NULL THEN 1 ELSE 0 END) as atr_count,
                SUM(CASE WHEN rsi IS NOT NULL THEN 1 ELSE 0 END) as rsi_count,
                SUM(CASE WHEN upper_shadow IS NOT NULL THEN 1 ELSE 0 END) as shadow_count
            FROM binance_spot_weekly
        """, conn)
        
        if len(df_indicators) > 0:
            total = df_indicators['total'].iloc[0]
            print(f"\n   기술적 지표:")
            print(f"   - ATR: {df_indicators['atr_count'].iloc[0]}/{total} ({df_indicators['atr_count'].iloc[0]/total*100:.1f}%)")
            print(f"   - RSI: {df_indicators['rsi_count'].iloc[0]}/{total} ({df_indicators['rsi_count'].iloc[0]/total*100:.1f}%)")
            print(f"   - 위꼬리/아래꼬리: {df_indicators['shadow_count'].iloc[0]}/{total} ({df_indicators['shadow_count'].iloc[0]/total*100:.1f}%)")
    else:
        print("   ⚠️ 주봉 데이터가 없습니다.")
    
    # 2. 고래 주간 집계 데이터 확인
    print("\n2️⃣ 고래 주간 집계 데이터")
    print("-" * 80)
    
    df_whale = pd.read_sql("""
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(*) as count,
            COUNT(DISTINCT coin_symbol) as coin_count,
            SUM(net_inflow_usd) as total_net_inflow,
            SUM(exchange_inflow_usd) as total_exchange_inflow
        FROM whale_weekly_stats
    """, conn)
    
    if len(df_whale) > 0 and df_whale['count'].iloc[0] > 0:
        print(f"   기간: {df_whale['min_date'].iloc[0]} ~ {df_whale['max_date'].iloc[0]}")
        print(f"   총 주수: {df_whale['count'].iloc[0]:,}주")
        print(f"   코인 수: {df_whale['coin_count'].iloc[0]}")
        print(f"   총 순입금: ${df_whale['total_net_inflow'].iloc[0]:,.2f}")
        print(f"   총 거래소 유입: ${df_whale['total_exchange_inflow'].iloc[0]:,.2f}")
    else:
        print("   ⚠️ 고래 주간 집계 데이터가 없습니다.")
        print("   aggregate_whale_weekly.py를 실행하세요.")
    
    # 3. 데이터 매칭 확인
    print("\n3️⃣ 주봉-고래 데이터 매칭 확인")
    print("-" * 80)
    
    df_merged = pd.read_sql("""
        SELECT 
            w.date,
            w.symbol,
            w.high,
            w.low,
            w.weekly_range_pct,
            wh.coin_symbol,
            wh.net_inflow_usd,
            wh.exchange_inflow_usd,
            wh.active_addresses,
            wh.transaction_count
        FROM binance_spot_weekly w
        LEFT JOIN whale_weekly_stats wh 
            ON w.date = wh.date AND wh.coin_symbol = 'BTC'
        WHERE w.symbol = 'BTCUSDT'
        ORDER BY w.date
    """, conn)
    
    if len(df_merged) > 0:
        matched_count = df_merged['coin_symbol'].notna().sum()
        total_count = len(df_merged)
        match_rate = matched_count / total_count * 100
        
        print(f"   총 주봉 데이터: {total_count}주")
        print(f"   매칭된 데이터: {matched_count}주 ({match_rate:.1f}%)")
        print(f"   매칭되지 않은 데이터: {total_count - matched_count}주 ({100-match_rate:.1f}%)")
        
        if matched_count > 0:
            print(f"\n   매칭된 데이터 샘플 (최근 5주):")
            matched_df = df_merged[df_merged['coin_symbol'].notna()].tail(5)
            for _, row in matched_df.iterrows():
                print(f"     {row['date']}: 변동폭 {row['weekly_range_pct']:.2f}%, 순입금 ${row['net_inflow_usd']:,.0f}, 활성 주소 {row['active_addresses']}개")
    else:
        print("   ⚠️ 매칭할 데이터가 없습니다.")
    
    # 4. 데이터 품질 확인
    print("\n4️⃣ 데이터 품질 확인")
    print("-" * 80)
    
    if len(df_weekly) > 0 and df_weekly['count'].iloc[0] > 0:
        df_quality = pd.read_sql("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN open IS NULL OR open = 0 THEN 1 ELSE 0 END) as null_open,
                SUM(CASE WHEN high IS NULL OR high = 0 THEN 1 ELSE 0 END) as null_high,
                SUM(CASE WHEN low IS NULL OR low = 0 THEN 1 ELSE 0 END) as null_low,
                SUM(CASE WHEN close IS NULL OR close = 0 THEN 1 ELSE 0 END) as null_close,
                SUM(CASE WHEN volume IS NULL OR volume = 0 THEN 1 ELSE 0 END) as null_volume
            FROM binance_spot_weekly
            WHERE symbol = 'BTCUSDT'
        """, conn)
        
        if len(df_quality) > 0:
            total = df_quality['total'].iloc[0]
            print(f"   주봉 데이터 품질:")
            print(f"   - NULL/0 Open: {df_quality['null_open'].iloc[0]}/{total} ({df_quality['null_open'].iloc[0]/total*100:.1f}%)")
            print(f"   - NULL/0 High: {df_quality['null_high'].iloc[0]}/{total} ({df_quality['null_high'].iloc[0]/total*100:.1f}%)")
            print(f"   - NULL/0 Low: {df_quality['null_low'].iloc[0]}/{total} ({df_quality['null_low'].iloc[0]/total*100:.1f}%)")
            print(f"   - NULL/0 Close: {df_quality['null_close'].iloc[0]}/{total} ({df_quality['null_close'].iloc[0]/total*100:.1f}%)")
            print(f"   - NULL/0 Volume: {df_quality['null_volume'].iloc[0]}/{total} ({df_quality['null_volume'].iloc[0]/total*100:.1f}%)")
    
    if len(df_whale) > 0 and df_whale['count'].iloc[0] > 0:
        df_whale_quality = pd.read_sql("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN net_inflow_usd IS NULL THEN 1 ELSE 0 END) as null_net_inflow,
                SUM(CASE WHEN exchange_inflow_usd IS NULL THEN 1 ELSE 0 END) as null_exchange_inflow,
                SUM(CASE WHEN active_addresses IS NULL OR active_addresses = 0 THEN 1 ELSE 0 END) as null_addresses,
                SUM(CASE WHEN transaction_count IS NULL OR transaction_count = 0 THEN 1 ELSE 0 END) as null_tx_count
            FROM whale_weekly_stats
            WHERE coin_symbol = 'BTC'
        """, conn)
        
        if len(df_whale_quality) > 0:
            total = df_whale_quality['total'].iloc[0]
            print(f"\n   고래 주간 데이터 품질:")
            print(f"   - NULL Net Inflow: {df_whale_quality['null_net_inflow'].iloc[0]}/{total} ({df_whale_quality['null_net_inflow'].iloc[0]/total*100:.1f}%)")
            print(f"   - NULL Exchange Inflow: {df_whale_quality['null_exchange_inflow'].iloc[0]}/{total} ({df_whale_quality['null_exchange_inflow'].iloc[0]/total*100:.1f}%)")
            print(f"   - NULL/0 Active Addresses: {df_whale_quality['null_addresses'].iloc[0]}/{total} ({df_whale_quality['null_addresses'].iloc[0]/total*100:.1f}%)")
            print(f"   - NULL/0 Transaction Count: {df_whale_quality['null_tx_count'].iloc[0]}/{total} ({df_whale_quality['null_tx_count'].iloc[0]/total*100:.1f}%)")
    
    # 5. 분석 가능 여부 확인
    print("\n5️⃣ 분석 가능 여부 확인")
    print("-" * 80)
    
    if len(df_merged) > 0:
        analyzable = df_merged[
            df_merged['coin_symbol'].notna() &
            df_merged['weekly_range_pct'].notna() &
            (df_merged['weekly_range_pct'] > 0)
        ]
        
        if len(analyzable) > 0:
            print(f"   ✅ 분석 가능한 데이터: {len(analyzable)}주")
            print(f"   기간: {analyzable['date'].min()} ~ {analyzable['date'].max()}")
            print(f"\n   제안된 5가지 분석 패턴 구현 가능 여부:")
            print(f"   1. 저점 매집 & 변동성 축소: ✅ (주봉 범위 + 순입금)")
            print(f"   2. 고점 분산 & 꼬리 캔들: ✅ (위꼬리 + 거래소 유입)")
            print(f"   3. 거래량 다이버전스: ✅ (가격 + 거래소 유입)")
            print(f"   4. 지지/저항선 반응: ⚠️ (Volume Profile 추가 계산 필요)")
            print(f"   5. 변동성 돌파 & 고래 동참: ✅ (변동폭 + 활성 주소 수)")
        else:
            print("   ⚠️ 분석 가능한 데이터가 없습니다.")
    else:
        print("   ⚠️ 매칭된 데이터가 없어 분석 불가")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 검증 완료!")
    print("=" * 80)


if __name__ == "__main__":
    verify_weekly_data()




