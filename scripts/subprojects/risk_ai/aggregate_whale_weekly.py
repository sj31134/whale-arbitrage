#!/usr/bin/env python3
"""
고래 거래 데이터를 주간 단위로 집계하여 SQLite에 저장
제안된 5가지 고래-변동성 분석 패턴 구현을 위한 주간 고래 지표 생성
"""

import os
import sqlite3
import pandas as pd
import time
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"
load_dotenv(ROOT / "config" / ".env")


def get_supabase_client():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)


def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_week_end_date(date_obj):
    """주봉 종료일 계산 (일요일)"""
    # 월요일 = 0, 일요일 = 6
    days_until_sunday = (6 - date_obj.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7  # 일요일이면 다음 주 일요일
    week_end = date_obj + timedelta(days=days_until_sunday)
    return week_end


def fetch_whale_transactions(supabase, coin_symbol="BTC", start_date="2023-01-01"):
    """Supabase에서 고래 거래 데이터 로드 (월별 분할)"""
    print(f"📥 Supabase에서 고래 거래 데이터 로드 중...")
    print(f"   코인: {coin_symbol}, 시작일: {start_date}")
    
    all_data = []
    page_size = 500  # 작은 배치로 변경
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    current_dt = start_dt
    end_dt = datetime.now()
    
    # 월별로 분할하여 수집
    while current_dt < end_dt:
        month_end = current_dt + timedelta(days=30)
        if month_end > end_dt:
            month_end = end_dt
        
        start_str = current_dt.strftime("%Y-%m-%dT00:00:00Z")
        end_str = month_end.strftime("%Y-%m-%dT23:59:59Z")
        
        print(f"   📅 {current_dt.date()} ~ {month_end.date()} 수집 중...")
        
        offset = 0
        month_data = []
        
        while True:
            try:
                response = supabase.table('whale_transactions')\
                    .select('tx_hash,block_timestamp,from_address,to_address,coin_symbol,amount,amount_usd,transaction_direction')\
                    .eq('coin_symbol', coin_symbol)\
                    .gte('block_timestamp', start_str)\
                    .lte('block_timestamp', end_str)\
                    .order('block_timestamp', desc=False)\
                    .range(offset, offset + page_size - 1)\
                    .execute()
                
                if not response.data:
                    break
                
                month_data.extend(response.data)
                offset += page_size
                
                if len(response.data) < page_size:
                    break
                
                time.sleep(0.1)  # Rate limit 방지
                
            except Exception as e:
                print(f"   ⚠️ 오류: {e}")
                break
        
        all_data.extend(month_data)
        print(f"      ✅ {len(month_data):,}건 수집")
        
        current_dt = month_end
        time.sleep(0.2)  # 월별 간격
    
    print(f"   ✅ 총 {len(all_data):,}건 로드 완료")
    return all_data


def aggregate_whale_weekly(coin_symbol="BTC", start_date="2023-01-01"):
    """고래 데이터 주간 집계"""
    print("=" * 80)
    print(f"📊 고래 데이터 주간 집계 ({coin_symbol})")
    print("=" * 80)
    
    ensure_db()
    
    # 1. Supabase에서 데이터 로드
    supabase = get_supabase_client()
    transactions = fetch_whale_transactions(supabase, coin_symbol, start_date)
    
    if not transactions:
        print("⚠️ 데이터가 없습니다.")
        return
    
    # 2. DataFrame으로 변환
    df = pd.DataFrame(transactions)
    df['block_timestamp'] = pd.to_datetime(df['block_timestamp'])
    df['date'] = df['block_timestamp'].dt.date
    
    # amount_usd 처리
    df['amount_usd'] = pd.to_numeric(df['amount_usd'], errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    
    # 3. 주간 집계
    print("\n📊 주간 집계 중...")
    
    # 주봉 종료일 계산 (일요일)
    df['week_end'] = df['date'].apply(get_week_end_date)
    
    # 주간 집계
    weekly_stats = []
    
    for week_end in sorted(df['week_end'].unique()):
        week_data = df[df['week_end'] == week_end]
        
        # 순입금 (Net Inflow): BUY - SELL
        buy_amount = week_data[week_data['transaction_direction'] == 'BUY']['amount_usd'].sum()
        sell_amount = week_data[week_data['transaction_direction'] == 'SELL']['amount_usd'].sum()
        net_inflow = buy_amount - sell_amount if pd.notna(buy_amount) and pd.notna(sell_amount) else 0.0
        
        # 거래소 유입 (Exchange Inflow): SELL 거래 합계
        exchange_inflow = sell_amount if pd.notna(sell_amount) else 0.0
        
        # 활성 주소 수
        active_addresses = len(set(week_data['from_address'].tolist() + week_data['to_address'].tolist()))
        
        # 트랜잭션 수
        transaction_count = len(week_data)
        
        # 고래 평균 단가 (매수 평균가)
        buy_txs = week_data[week_data['transaction_direction'] == 'BUY']
        if len(buy_txs) > 0 and buy_txs['amount_usd'].notna().any():
            # 가격 데이터가 있는 경우만 계산
            buy_txs_with_price = buy_txs[buy_txs['amount_usd'].notna() & (buy_txs['amount_usd'] > 0)]
            if len(buy_txs_with_price) > 0:
                total_buy_usd = buy_txs_with_price['amount_usd'].sum()
                total_buy_amount = buy_txs_with_price['amount'].sum()
                avg_buy_price = total_buy_usd / total_buy_amount if total_buy_amount > 0 else 0.0
            else:
                avg_buy_price = 0.0
        else:
            avg_buy_price = 0.0
        
        weekly_stats.append({
            'date': week_end.isoformat(),
            'coin_symbol': coin_symbol,
            'net_inflow_usd': net_inflow,
            'exchange_inflow_usd': exchange_inflow,
            'active_addresses': active_addresses,
            'transaction_count': transaction_count,
            'avg_buy_price': avg_buy_price
        })
    
    # 4. SQLite에 저장
    print(f"\n💾 SQLite 저장 중...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    saved_count = 0
    for stat in weekly_stats:
        cursor.execute("""
            INSERT OR REPLACE INTO whale_weekly_stats
            (date, coin_symbol, net_inflow_usd, exchange_inflow_usd, active_addresses, transaction_count, avg_buy_price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            stat['date'],
            stat['coin_symbol'],
            stat['net_inflow_usd'],
            stat['exchange_inflow_usd'],
            stat['active_addresses'],
            stat['transaction_count'],
            stat['avg_buy_price']
        ))
        saved_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"   ✅ {saved_count}주 데이터 저장 완료")
    
    # 5. 결과 확인
    conn = sqlite3.connect(DB_PATH)
    df_check = pd.read_sql("""
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(*) as count,
            SUM(net_inflow_usd) as total_net_inflow,
            SUM(exchange_inflow_usd) as total_exchange_inflow
        FROM whale_weekly_stats
        WHERE coin_symbol = ?
    """, conn, params=(coin_symbol,))
    conn.close()
    
    if len(df_check) > 0 and df_check['min_date'].iloc[0]:
        print(f"\n📊 저장된 데이터:")
        print(f"   기간: {df_check['min_date'].iloc[0]} ~ {df_check['max_date'].iloc[0]}")
        print(f"   총 주수: {df_check['count'].iloc[0]}주")
        print(f"   총 순입금: ${df_check['total_net_inflow'].iloc[0]:,.2f}")
        print(f"   총 거래소 유입: ${df_check['total_exchange_inflow'].iloc[0]:,.2f}")


def main():
    print("=" * 80)
    print("📊 고래 데이터 주간 집계")
    print("=" * 80)
    
    # BTC만 집계 (필요시 확장 가능)
    aggregate_whale_weekly(coin_symbol="BTC", start_date="2023-01-01")
    
    print("\n" + "=" * 80)
    print("✅ 주간 집계 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()

