#!/usr/bin/env python3
"""
Top 3 분석: 
1. 거래소 입금(Dump) vs 가격 하락 상관관계
2. 스마트 머니 지갑 발굴 (승률/수익금)
10. 고래 수익성 분석 (2번과 통합)
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from datetime import timedelta

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    return create_client(supabase_url, supabase_key)

def fetch_data(supabase):
    print("📥 데이터 로딩 중... (최근 데이터 10,000건 기준)")
    
    # 1. 고래 거래 데이터 (최근 순, 더 많이 가져오기)
    wt_res = supabase.table('whale_transactions')\
        .select('*')\
        .order('block_timestamp', desc=True)\
        .limit(100000)\
        .execute()
    
    # 2. 가격 데이터 (최근 순)
    ph_res = supabase.table('price_history')\
        .select('timestamp, close_price, crypto_id, open_price, high_price, low_price')\
        .order('timestamp', desc=True)\
        .limit(2000)\
        .execute()
        
    # 3. 코인 심볼 매핑
    c_res = supabase.table('cryptocurrencies').select('id, symbol').execute()
    
    if not wt_res.data or not ph_res.data:
        print("❌ 데이터가 부족합니다.")
        return None, None, None
        
    df_wt = pd.DataFrame(wt_res.data)
    df_ph = pd.DataFrame(ph_res.data)
    df_c = pd.DataFrame(c_res.data)
    
    # 전처리
    # format='mixed'를 사용하여 다양한 날짜 형식을 유연하게 처리
    df_wt['block_timestamp'] = pd.to_datetime(df_wt['block_timestamp'], format='mixed', errors='coerce', utc=True)
    df_ph['timestamp'] = pd.to_datetime(df_ph['timestamp'], format='mixed', errors='coerce', utc=True)
    
    # 변환 실패(NaT)한 행 제거 (분석에 방해됨)
    df_wt = df_wt.dropna(subset=['block_timestamp'])
    df_ph = df_ph.dropna(subset=['timestamp'])
    
    # 1. transaction_direction이 NULL이면 라벨로 판단
    exchange_keywords = ['binance', 'coinbase', 'kraken', 'huobi', 'okx', 'bitfinex', 'gate', 'bybit', 'kucoin', 'upbit', 'bithumb', 'exchange']
    
    def infer_direction(row):
        if pd.notna(row.get('transaction_direction')):
            return row['transaction_direction']
        
        from_label = str(row.get('from_label', '')).lower()
        to_label = str(row.get('to_label', '')).lower()
        
        from_is_exchange = any(kw in from_label for kw in exchange_keywords)
        to_is_exchange = any(kw in to_label for kw in exchange_keywords)
        
        if from_is_exchange and not to_is_exchange:
            return 'BUY'  # 거래소 -> 개인 (출금)
        elif not from_is_exchange and to_is_exchange:
            return 'SELL'  # 개인 -> 거래소 (입금)
        else:
            return 'MOVE'
    
    df_wt['transaction_direction'] = df_wt.apply(infer_direction, axis=1)
    
    # 2. amount_usd가 없으면 가격 데이터로 계산
    if df_wt['amount_usd'].isna().any():
        # 시간 단위로 절삭
        df_wt['hour_key'] = df_wt['block_timestamp'].dt.floor('H')
        df_ph['hour_key'] = df_ph['timestamp'].dt.floor('H')
        
        # 코인 심볼 매핑
        ph_with_symbol = pd.merge(df_ph, df_c, left_on='crypto_id', right_on='id', how='left')
        
        # 가격 병합
        df_wt = pd.merge(
            df_wt, 
            ph_with_symbol[['symbol', 'hour_key', 'close_price']], 
            left_on=['coin_symbol', 'hour_key'], 
            right_on=['symbol', 'hour_key'], 
            how='left'
        )
        
        # amount_usd 계산
        df_wt['amount'] = pd.to_numeric(df_wt['amount'], errors='coerce')
        df_wt['close_price'] = pd.to_numeric(df_wt['close_price'], errors='coerce')
        df_wt['amount_usd'] = df_wt['amount_usd'].fillna(df_wt['amount'] * df_wt['close_price'])
        
        # 임시 컬럼 제거
        df_wt = df_wt.drop(columns=['hour_key', 'symbol'], errors='ignore')
    
    return df_wt, df_ph, df_c

def analyze_dump_correlation(df_wt, df_ph, df_c):
    print("\n" + "="*60)
    print("📊 1. 거래소 대량 입금(SELL) 후 가격 하락 상관분석")
    print("="*60)
    
    # SELL 거래 필터링 (없으면 MOVE 중 거래소 관련 거래 포함)
    sell_tx = df_wt[df_wt['transaction_direction'] == 'SELL'].copy()
    if sell_tx.empty:
        # MOVE 중에서도 거래소로 가는 거래를 포함
        exchange_keywords = ['binance', 'coinbase', 'kraken', 'huobi', 'okx', 'bitfinex', 'gate', 'bybit', 'kucoin', 'upbit', 'bithumb']
        move_to_exchange = df_wt[
            (df_wt['transaction_direction'] == 'MOVE') & 
            (df_wt['to_label'].str.lower().str.contains('|'.join(exchange_keywords), na=False))
        ].copy()
        if not move_to_exchange.empty:
            print("ℹ️ 'SELL' 라벨이 없어서, MOVE 중 거래소로 가는 거래를 분석합니다.")
            sell_tx = move_to_exchange
        else:
            print("⚠️ 'SELL' 거래가 없습니다. (라벨 기반 추론도 시도했지만 결과 없음)")
            return

    # 시간 단위로 트림
    sell_tx['hour_key'] = sell_tx['block_timestamp'].dt.floor('H')
    
    # 시간대별 총 매도량 (amount_usd 우선 사용)
    if 'amount_usd' in sell_tx.columns and not sell_tx['amount_usd'].isna().all():
        sell_tx['amount_usd'] = pd.to_numeric(sell_tx['amount_usd'], errors='coerce')
        hourly_sell = sell_tx.groupby(['coin_symbol', 'hour_key'])['amount_usd'].sum().reset_index()
        amount_col = 'amount_usd'
    else:
        sell_tx['amount'] = pd.to_numeric(sell_tx['amount'], errors='coerce')
        hourly_sell = sell_tx.groupby(['coin_symbol', 'hour_key'])['amount'].sum().reset_index()
        amount_col = 'amount'
    
    # 가격 데이터와 병합을 위해 심볼 매핑
    # df_c: id, symbol
    # df_ph: crypto_id, timestamp, close_price
    
    ph_merged = pd.merge(df_ph, df_c, left_on='crypto_id', right_on='id')
    ph_merged['timestamp'] = ph_merged['timestamp'].dt.tz_convert(None) # UTC 제거 (비교용)
    hourly_sell['hour_key'] = hourly_sell['hour_key'].dt.tz_convert(None)
    
    hourly_sell['hour_key'] = hourly_sell['hour_key'].dt.tz_convert(None)
    merged = pd.merge(hourly_sell, ph_merged, left_on=['coin_symbol', 'hour_key'], right_on=['symbol', 'timestamp'], how='left')
    
    if merged.empty:
        print("⚠️ 매칭되는 가격 데이터가 없습니다. 시간대나 심볼을 확인하세요.")
        return

    # 결과 분석: 매도량 상위 5개 구간의 다음 시간 가격 변화
    top_dumps = merged.sort_values(amount_col, ascending=False).head(5)
    
    print(f"{'시간':<20} | {'코인':<5} | {'매도량(USD)':<15} | {'당시가격':<12} | {'1시간 후 변화'}")
    print("-" * 85)
    
    for _, row in top_dumps.iterrows():
        # 다음 시간 가격 찾기
        next_hour = row['hour_key'] + timedelta(hours=1)
        next_price_row = ph_merged[
            (ph_merged['symbol'] == row['coin_symbol']) & 
            (ph_merged['timestamp'] == next_hour)
        ]
        
        analysis_txt = "데이터 부족"
        if not next_price_row.empty and pd.notna(row.get('close_price')):
            next_price = float(next_price_row.iloc[0]['close_price'])
            curr_price = float(row['close_price'])
            change = ((next_price - curr_price) / curr_price) * 100
            analysis_txt = f"{change:+.2f}%"
            
        amount_val = row[amount_col] if pd.notna(row.get(amount_col)) else 0
        price_val = row.get('close_price', 0) if pd.notna(row.get('close_price')) else 0
        
        print(f"{row['hour_key']} | {row['coin_symbol']:<5} | ${amount_val:>13,.0f} | ${price_val:>10,.2f} | {analysis_txt}")

def analyze_smart_money(df_wt, df_ph):
    print("\n" + "="*60)
    print("🏆 2. & 10. 스마트 머니 발굴 및 수익성 분석")
    print("="*60)
    
    # 1. BUY와 SELL을 모두 한 지갑 찾기
    wallet_stats = {}
    
    # 주소별로 트랜잭션 모으기
    grouped = df_wt.groupby('from_address')
    
    ranked_wallets = []
    
    for address, group in grouped:
        # 라벨이 있는 경우 (거래소 등) 제외하고 싶지만, 일단 포함해서 분석
        # buys = group[group['transaction_direction'] == 'BUY']
        # sells = group[group['transaction_direction'] == 'SELL']
        
        # 데이터 부족으로 간단히 'amount_usd'가 있다고 가정하고 계산
        # 여기서는 로직만 구현: 
        # 수익 = (총 매도액 USD) - (총 매수액 USD) ... 단순화 모델
        # 더 정확히는 FIFO나 이동평균법 써야 함.
        
        # BUY와 SELL 분리 (MOVE도 포함)
        buys = group[group['transaction_direction'] == 'BUY']
        sells = group[group['transaction_direction'] == 'SELL']
        
        # MOVE 중에서도 거래소 관련 거래를 BUY/SELL로 분류
        exchange_keywords = ['binance', 'coinbase', 'kraken', 'huobi', 'okx', 'bitfinex', 'gate', 'bybit', 'kucoin', 'upbit', 'bithumb']
        moves = group[group['transaction_direction'] == 'MOVE']
        
        # MOVE 중 거래소 출금 -> BUY로 간주
        move_buys = moves[moves['from_label'].str.lower().str.contains('|'.join(exchange_keywords), na=False)]
        # MOVE 중 거래소 입금 -> SELL로 간주
        move_sells = moves[moves['to_label'].str.lower().str.contains('|'.join(exchange_keywords), na=False)]
        
        # 합치기
        all_buys = pd.concat([buys, move_buys]) if not move_buys.empty else buys
        all_sells = pd.concat([sells, move_sells]) if not move_sells.empty else sells
        
        # amount_usd 우선 사용
        buy_amount = pd.to_numeric(all_buys['amount_usd'], errors='coerce').sum() if not all_buys.empty else 0
        sell_amount = pd.to_numeric(all_sells['amount_usd'], errors='coerce').sum() if not all_sells.empty else 0
        
        # 총 거래량
        total_vol = pd.to_numeric(group['amount_usd'], errors='coerce').sum()
        
        tx_count = len(group)
        label = group.iloc[0]['from_label']
        
        if pd.isna(label) or label == '':
            label = "Unknown"
        
        # 수익 계산 (매도액 - 매수액)
        profit = sell_amount - buy_amount
        
        ranked_wallets.append({
            'address': address,
            'label': label,
            'tx_count': tx_count,
            'total_volume': total_vol,
            'buy_amount': buy_amount,
            'sell_amount': sell_amount,
            'profit': profit,
            'roi': (profit / buy_amount * 100) if buy_amount > 0 else 0
        })
        
    # 총 거래량 기준 상위 10
    df_rank = pd.DataFrame(ranked_wallets)
    df_rank = df_rank[df_rank['total_volume'] > 0].sort_values('total_volume', ascending=False).head(10)
    
    if df_rank.empty:
        print("⚠️ 거래 데이터가 있는 지갑을 찾지 못했습니다.")
        return
    
    print(f"{'순위':<4} | {'라벨/주소':<30} | {'거래수':<5} | {'총거래량(USD)':<15} | {'매수액(USD)':<12} | {'매도액(USD)':<12} | {'수익(USD)':<12} | {'ROI':<8}")
    print("-" * 110)
    
    for idx, (i, row) in enumerate(df_rank.iterrows(), 1):
        addr_display = row['label'] if row['label'] != 'Unknown' and row['label'] != 'Bitcoin' else row['address'][:10] + "..."
        if len(addr_display) > 30:
            addr_display = addr_display[:27] + "..."
        print(f"{idx:<4} | {addr_display:<30} | {int(row['tx_count']):<5} | ${row['total_volume']:>14,.0f} | ${row['buy_amount']:>11,.0f} | ${row['sell_amount']:>11,.0f} | ${row['profit']:>11,.0f} | {row['roi']:>6.1f}%")
        
    print("\n✅ 분석 완료: 총 거래량 기준 상위 지갑의 활동을 분석했습니다.")

def main():
    supabase = get_supabase_client()
    df_wt, df_ph, df_c = fetch_data(supabase)
    
    if df_wt is not None:
        # 데이터 상태 확인
        print(f"\n📊 데이터 상태:")
        print(f"   - 총 거래 수: {len(df_wt):,}건")
        print(f"   - transaction_direction 분포:")
        if 'transaction_direction' in df_wt.columns:
            print(df_wt['transaction_direction'].value_counts().to_string())
        print(f"   - amount_usd 채워진 비율: {(1 - df_wt['amount_usd'].isna().sum() / len(df_wt)) * 100:.1f}%")
        print(f"   - from_label NULL 비율: {df_wt['from_label'].isna().sum() / len(df_wt) * 100:.1f}%")
        
        analyze_dump_correlation(df_wt, df_ph, df_c)
        analyze_smart_money(df_wt, df_ph)

if __name__ == '__main__':
    main()

