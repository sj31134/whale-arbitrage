#!/usr/bin/env python3
"""
내부 whale_transactions 데이터를 집계하여 온체인 지표를 생성합니다.

확장된 기능:
- bitinfocharts_whale: 일별 고래 거래량, 평균 거래 금액
- whale_daily_stats: 일별 거래소 유입/유출량, 순유입, 활성 주소 수, 대형 거래 건수
- whale_weekly_stats: 주별 집계 데이터
"""

import os
import pandas as pd
import numpy as np
import time
import sqlite3
from datetime import timezone
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client
try:
    from supabase.lib.client_options import ClientOptions
except ImportError:
    ClientOptions = None

ROOT = Path(__file__).resolve().parent.parents[2]
env_path = ROOT / "config" / ".env"
print(f"Loading .env from: {env_path}")
load_dotenv(env_path, override=True)

# Supabase Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Local SQLite Connection
DB_PATH = ROOT / "data" / "project.db"

# 대형 거래 기준 (USD)
LARGE_TX_THRESHOLD_USD = 100000  # $100,000 이상

def get_sqlite_conn():
    return sqlite3.connect(DB_PATH)


def ensure_tables():
    """필요한 테이블이 없으면 생성"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # whale_daily_stats 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whale_daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            coin_symbol VARCHAR(20) NOT NULL,
            exchange_inflow_usd DECIMAL(30, 8),
            exchange_outflow_usd DECIMAL(30, 8),
            net_flow_usd DECIMAL(30, 8),
            whale_to_whale_usd DECIMAL(30, 8),
            active_addresses INTEGER,
            large_tx_count INTEGER,
            avg_tx_size_usd DECIMAL(20, 8),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, coin_symbol)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whale_daily_date ON whale_daily_stats(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whale_daily_coin ON whale_daily_stats(coin_symbol)")
    
    # whale_weekly_stats 테이블 (이미 있을 수 있음)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whale_weekly_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            coin_symbol VARCHAR(20) NOT NULL,
            net_inflow_usd DECIMAL(30, 8),
            exchange_inflow_usd DECIMAL(30, 8),
            active_addresses INTEGER,
            transaction_count INTEGER,
            avg_buy_price DECIMAL(20, 8),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, coin_symbol)
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()


def _whale_tx_has_columns(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(whale_transactions)")
    cols = {row[1] for row in cur.fetchall()}
    return "amount_usd" in cols, "transaction_direction" in cols


def ensure_whale_tx_columns(conn):
    """SQLite whale_transactions에 amount_usd, transaction_direction 컬럼이 없으면 추가"""
    has_usd, has_dir = _whale_tx_has_columns(conn)
    cur = conn.cursor()
    if not has_usd:
        cur.execute("ALTER TABLE whale_transactions ADD COLUMN amount_usd REAL")
    if not has_dir:
        cur.execute("ALTER TABLE whale_transactions ADD COLUMN transaction_direction VARCHAR(20)")
    conn.commit()


def update_whale_tx_usd_and_direction(conn):
    """로컬 whale_transactions의 amount_usd·transaction_direction 보정 (가격·라벨 기반)"""
    cur = conn.cursor()
    # 일별 종가 (symbol: BTCUSDT/ETHUSDT -> coin_symbol BTC/ETH)
    try:
        prices = pd.read_sql(
            "SELECT date, symbol, close FROM binance_spot_daily WHERE symbol IN ('BTCUSDT','ETHUSDT')",
            conn,
        )
    except Exception:
        return
    if prices.empty:
        return
    prices["date"] = pd.to_datetime(prices["date"]).dt.strftime("%Y-%m-%d")
    price_btc = prices[prices["symbol"] == "BTCUSDT"].set_index("date")["close"]
    price_eth = prices[prices["symbol"] == "ETHUSDT"].set_index("date")["close"]

    # amount_usd: value * close (날짜 = block_timestamp 날짜)
    cur.execute(
        "SELECT tx_hash, chain, block_timestamp, value, coin_symbol FROM whale_transactions WHERE amount_usd IS NULL OR amount_usd = 0"
    )
    rows = cur.fetchall()
    for tx_hash, chain, block_ts, value, coin in rows:
        if value is None:
            continue
        try:
            dt = pd.to_datetime(block_ts)
            date_str = dt.strftime("%Y-%m-%d")
            if coin == "BTC":
                price = price_btc.get(date_str)
            elif coin == "ETH":
                price = price_eth.get(date_str)
            else:
                price = None
            if price is not None and float(value) >= 0:
                amount_usd = float(value) * float(price)
                cur.execute("UPDATE whale_transactions SET amount_usd = ? WHERE tx_hash = ? AND chain = ?", (amount_usd, tx_hash, chain))
        except Exception:
            pass
    conn.commit()

    # transaction_direction: from_label / to_label 기반 (거래소 -> BUY/SELL)
    try:
        cur.execute("SELECT tx_hash, chain, from_label, to_label FROM whale_transactions WHERE transaction_direction IS NULL OR transaction_direction = ''")
        label_rows = cur.fetchall()
    except Exception:
        return
    exchange_keywords = ("binance", "coinbase", "kraken", "bitfinex", "huobi", "okx", "gate", "bybit", "kucoin", "crypto.com", "upbit")
    for tx_hash, chain, from_l, to_l in label_rows:
        from_l = (from_l or "").lower()
        to_l = (to_l or "").lower()
        is_from_ex = any(k in from_l for k in exchange_keywords)
        is_to_ex = any(k in to_l for k in exchange_keywords)
        if is_to_ex and not is_from_ex:
            direction = "exchange_outflow"  # BUY
        elif is_from_ex and not is_to_ex:
            direction = "exchange_inflow"   # SELL
        else:
            direction = "MOVE"
        cur.execute(
            "UPDATE whale_transactions SET transaction_direction = ? WHERE tx_hash = ? AND chain = ?",
            (direction, tx_hash, chain),
        )
    conn.commit()


def fetch_whale_transactions_from_sqlite(conn, start_date, end_date, coin_symbols=None):
    """로컬 SQLite whale_transactions에서 집계용 트랜잭션 목록 반환 (Supabase 미사용)"""
    if coin_symbols is None:
        coin_symbols = ["BTC", "ETH"]
    start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S") if hasattr(start_date, "strftime") else str(start_date)[:19]
    end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S") if hasattr(end_date, "strftime") else str(end_date)[:19]
    placeholders = ",".join("?" for _ in coin_symbols)
    query = """
        SELECT block_timestamp, value, amount_usd, coin_symbol, from_address, to_address, transaction_direction
        FROM whale_transactions
        WHERE block_timestamp >= ? AND block_timestamp < ?
        AND coin_symbol IN ({})
    """.format(placeholders)
    params = [start_str, end_str] + list(coin_symbols)
    try:
        df = pd.read_sql(query, conn, params=params)
    except Exception as e:
        print(f"  ⚠️ SQLite whale_transactions 조회 실패: {e}")
        return []
    if df.empty:
        return []
    df["block_timestamp"] = pd.to_datetime(df["block_timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["block_timestamp"])
    # amount_usd 없으면 value 사용 (USD 근사는 update_whale_tx_usd_and_direction에서 처리)
    if "amount_usd" not in df.columns or df["amount_usd"].isna().all():
        df["amount_usd"] = 0.0
    else:
        df["amount_usd"] = pd.to_numeric(df["amount_usd"], errors="coerce").fillna(0)
    if "transaction_direction" not in df.columns or df["transaction_direction"].isna().all():
        df["transaction_direction"] = "MOVE"
    return df.to_dict("records")


def aggregate_daily_whale_stats_from_sqlite(conn, start_date, end_date, coin_symbols=None):
    """로컬 SQLite whale_transactions만 사용해 whale_daily_stats 집계 (Supabase 미사용)"""
    if coin_symbols is None:
        coin_symbols = ["BTC", "ETH"]
    ensure_whale_tx_columns(conn)
    update_whale_tx_usd_and_direction(conn)
    all_txs = fetch_whale_transactions_from_sqlite(conn, start_date, end_date, coin_symbols=coin_symbols)
    if not all_txs:
        print("⚠️ 로컬 whale_transactions 데이터 없음")
        return []
    return aggregate_daily_whale_stats(None, start_date, end_date, coin_symbols=coin_symbols, txs_override=all_txs)


def fetch_whale_transactions_with_direction(supabase, start_date, end_date, coin_symbols=None):
    """
    whale_transactions에서 거래 방향(transaction_direction) 포함하여 데이터 가져오기
    """
    if coin_symbols is None:
        coin_symbols = ["BTC", "ETH", "BNB"]
    
    all_txs = []
    current_start = start_date
    
    while current_start < end_date:
        current_end = current_start + pd.DateOffset(months=1)
        # UTC 기준으로 변환
        start_utc = current_start.tz_localize('UTC') if current_start.tz is None else current_start.astimezone(timezone.utc)
        end_utc = current_end.tz_localize('UTC') if current_end.tz is None else current_end.astimezone(timezone.utc)
        start_str = start_utc.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = end_utc.strftime("%Y-%m-%dT%H:%M:%S")
        
        print(f"  📅 {start_str[:10]} ~ {end_str[:10]} 조회 중...")
        
        offset = 0
        limit = 1000
        
        while True:
            try:
                response = supabase.table("whale_transactions") \
                    .select("block_timestamp, amount, amount_usd, coin_symbol, from_address, to_address, transaction_direction") \
                    .gte("block_timestamp", start_str) \
                    .lt("block_timestamp", end_str) \
                    .in_("coin_symbol", coin_symbols) \
                    .range(offset, offset + limit - 1) \
                    .execute()
                
                data = response.data
                if not data:
                    break
                    
                all_txs.extend(data)
                offset += limit
                
                if len(data) < limit:
                    break
                    
                time.sleep(0.1)
                
            except Exception as e:
                print(f"  ❌ 오류 발생: {e}")
                break
        
        current_start = current_end
    
    return all_txs


def aggregate_daily_whale_stats(supabase, start_date, end_date, coin_symbols=None, txs_override=None):
    """
    일별 고래 통계 집계:
    - 거래소 유입/유출량
    - 순유입
    - 고래간 거래량
    - 활성 주소 수
    - 대형 거래 건수
    txs_override: 리스트가 주어지면 Supabase 조회 없이 이 데이터로 집계 (로컬 SQLite용)
    """
    print("\n📊 일별 고래 통계 집계 중...")
    
    if txs_override is not None:
        all_txs = txs_override
    else:
        all_txs = fetch_whale_transactions_with_direction(supabase, start_date, end_date, coin_symbols=coin_symbols)
    
    if not all_txs:
        print("⚠️ 데이터 없음")
        return
    
    df = pd.DataFrame(all_txs)
    # UTC 기준으로 날짜 변환 (다양한 형식 지원)
    df['block_timestamp'] = pd.to_datetime(df['block_timestamp'], format='mixed', errors='coerce', utc=True)
    df = df.dropna(subset=['block_timestamp'])  # 날짜 변환 실패한 행 제거
    
    # UTC 기준으로 date 추출 (UTC 날짜 기준)
    df['date'] = df['block_timestamp'].dt.tz_convert('UTC').dt.date
    df['amount_usd'] = pd.to_numeric(df['amount_usd'], errors='coerce').fillna(0)
    
    # 거래 방향별 집계
    results = []
    
    for coin in df['coin_symbol'].unique():
        coin_df = df[df['coin_symbol'] == coin]
        
        for date in coin_df['date'].unique():
            day_df = coin_df[coin_df['date'] == date]
            
            # 거래소 유입 (exchange_inflow)
            # SELL = 개인 → 거래소 (입금) = exchange_inflow
            # exchange_inflow 값도 확인 (기존 호환성)
            inflow_df = day_df[
                (day_df['transaction_direction'] == 'exchange_inflow') | 
                (day_df['transaction_direction'] == 'SELL')
            ]
            exchange_inflow = inflow_df['amount_usd'].sum()
            
            # 거래소 유출 (exchange_outflow)
            # BUY = 거래소 → 개인 (출금) = exchange_outflow
            # exchange_outflow 값도 확인 (기존 호환성)
            outflow_df = day_df[
                (day_df['transaction_direction'] == 'exchange_outflow') | 
                (day_df['transaction_direction'] == 'BUY')
            ]
            exchange_outflow = outflow_df['amount_usd'].sum()
            
            # 순유입
            net_flow = exchange_inflow - exchange_outflow
            
            # 고래간 거래 (whale_to_whale)
            # MOVE 중에서 거래소가 아닌 경우 = whale_to_whale
            # whale_to_whale 값도 확인 (기존 호환성)
            w2w_df = day_df[
                (day_df['transaction_direction'] == 'whale_to_whale') |
                (day_df['transaction_direction'] == 'MOVE')
            ]
            whale_to_whale = w2w_df['amount_usd'].sum()
            
            # 활성 주소 수 (from + to 유니크)
            active_from = set(day_df['from_address'].dropna().unique())
            active_to = set(day_df['to_address'].dropna().unique())
            active_addresses = len(active_from | active_to)
            
            # 대형 거래 건수 ($100K 이상)
            large_tx_count = len(day_df[day_df['amount_usd'] >= LARGE_TX_THRESHOLD_USD])
            
            # 평균 거래 크기
            avg_tx_size = day_df['amount_usd'].mean() if len(day_df) > 0 else 0
            
            results.append({
                'date': date,
                'coin_symbol': coin,
                'exchange_inflow_usd': exchange_inflow,
                'exchange_outflow_usd': exchange_outflow,
                'net_flow_usd': net_flow,
                'whale_to_whale_usd': whale_to_whale,
                'active_addresses': active_addresses,
                'large_tx_count': large_tx_count,
                'avg_tx_size_usd': avg_tx_size
            })
    
    # SQLite에 저장
    if results:
        conn = get_sqlite_conn()
        cur = conn.cursor()
        
        for row in results:
            date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
            cur.execute("""
                INSERT OR REPLACE INTO whale_daily_stats 
                (date, coin_symbol, exchange_inflow_usd, exchange_outflow_usd, 
                 net_flow_usd, whale_to_whale_usd, active_addresses, 
                 large_tx_count, avg_tx_size_usd)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date_str,
                row['coin_symbol'],
                row['exchange_inflow_usd'],
                row['exchange_outflow_usd'],
                row['net_flow_usd'],
                row['whale_to_whale_usd'],
                row['active_addresses'],
                row['large_tx_count'],
                row['avg_tx_size_usd']
            ))
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ {len(results)}건의 일별 통계 저장 완료")
    
    return results


def aggregate_weekly_whale_stats():
    """
    whale_daily_stats를 기반으로 주별 집계
    """
    print("\n📊 주별 고래 통계 집계 중...")
    
    conn = get_sqlite_conn()
    
    # 일별 데이터 로드
    query = """
        SELECT date, coin_symbol, exchange_inflow_usd, exchange_outflow_usd,
               net_flow_usd, active_addresses, large_tx_count
        FROM whale_daily_stats
        ORDER BY date
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        print("⚠️ 일별 데이터 없음")
        return
    
    df['date'] = pd.to_datetime(df['date'])
    df['week_start'] = df['date'] - pd.to_timedelta(df['date'].dt.dayofweek, unit='D')
    
    # 주별 집계
    weekly_df = df.groupby(['week_start', 'coin_symbol']).agg({
        'exchange_inflow_usd': 'sum',
        'net_flow_usd': 'sum',
        'active_addresses': 'mean',  # 평균 활성 주소
        'large_tx_count': 'sum'
    }).reset_index()
    
    weekly_df.columns = ['date', 'coin_symbol', 'exchange_inflow_usd', 'net_inflow_usd', 
                         'active_addresses', 'transaction_count']
    
    # SQLite에 저장
    conn = get_sqlite_conn()
    cur = conn.cursor()
    
    for _, row in weekly_df.iterrows():
        cur.execute("""
            INSERT OR REPLACE INTO whale_weekly_stats 
            (date, coin_symbol, net_inflow_usd, exchange_inflow_usd, 
             active_addresses, transaction_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            row['date'].strftime('%Y-%m-%d'),
            row['coin_symbol'],
            row['net_inflow_usd'],
            row['exchange_inflow_usd'],
            int(row['active_addresses']),
            int(row['transaction_count'])
        ))
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ {len(weekly_df)}건의 주별 통계 저장 완료")

def aggregate_whale_stats():
    # 환경 변수 로드 디버깅
    print(f"DEBUG: SUPABASE_URL={os.getenv('SUPABASE_URL') is not None}")
    print(f"DEBUG: SUPABASE_KEY={os.getenv('SUPABASE_KEY') is not None}")
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    print("🔄 고래 활동 지표 집계 중 (Source: Supabase whale_transactions)...")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase 설정 오류: .env 파일 확인 필요")
        # 하드코딩이나 대체 방법 시도 (보안상 비권장)
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Supabase REST API (PostgREST)로 집계 쿼리는 어려움 (RPC 사용 권장)
    # 하지만 여기서는 간단하게 RPC 함수를 호출하거나, 
    # 또는 데이터를 일별로 가져와서 Pandas로 집계 (데이터 양이 많으면 비효율적일 수 있음)
    
    # 가장 좋은 방법: SQL 함수(RPC)를 만들고 호출
    # 차선책: Raw SQL 실행 (supabase-py에서는 rpc로 실행하거나 client.table().select() 사용)
    
    # 여기서는 supabase-py로 직접 쿼리 실행이 제한적이므로,
    # 'whale_transactions'에서 필요한 컬럼만 가져와서 Pandas로 처리 (배치 처리)
    
    # 1. 데이터 가져오기 (월별 분할 수집)
    all_txs = []
    
    # 수집 기간 설정 (2023-01 ~ 현재) - UTC 기준
    start_date = pd.Timestamp("2023-01-01", tz='UTC')
    end_date = pd.Timestamp.now(tz='UTC')
    
    current_start = start_date
    
    print("📥 월별 데이터 다운로드 중...")
    
    while current_start < end_date:
        current_end = current_start + pd.DateOffset(months=1)
        # UTC 기준으로 변환
        start_str = current_start.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = current_end.strftime("%Y-%m-%dT%H:%M:%S")
        
        print(f"  📅 {start_str} ~ {end_str} 조회 중...")
        
        offset = 0
        limit = 1000 # 월 단위로 끊으면 1000개씩 가져와도 괜찮을 수 있음
        
        while True:
            try:
                response = supabase.table("whale_transactions") \
                    .select("block_timestamp, amount, coin_symbol") \
                    .gte("block_timestamp", start_str) \
                    .lt("block_timestamp", end_str) \
                    .in_("coin_symbol", ["BTC", "WBTC"]) \
                    .range(offset, offset + limit - 1) \
                    .execute()
                
                data = response.data
                if not data:
                    break
                    
                all_txs.extend(data)
                offset += limit
                
                if len(data) < limit:
                    break
                    
                time.sleep(0.1) # Rate limit
                
            except Exception as e:
                print(f"  ❌ 오류 발생 ({start_str}): {e}")
                # 해당 월 건너뛰고 다음으로 진행 (또는 재시도)
                break
        
        current_start = current_end
        print(f"  => 누적 {len(all_txs)}건")

    if not all_txs:
        print("⚠️ BTC 데이터 없음. ETH 데이터로 시도...")
        # ETH 시도 로직 추가 가능 (생략)
        return

    df = pd.DataFrame(all_txs)
    # UTC 기준으로 날짜 변환
    df['block_timestamp'] = pd.to_datetime(df['block_timestamp'], format='mixed', errors='coerce', utc=True)
    df = df.dropna(subset=['block_timestamp'])  # 날짜 변환 실패한 행 제거
    # UTC 기준으로 date 추출
    df['date'] = df['block_timestamp'].dt.tz_convert('UTC').dt.date
    df['amount'] = pd.to_numeric(df['amount'])
    
    # 2. 집계
    agg_df = df.groupby('date').agg(
        tx_count=('amount', 'count'),
        total_volume=('amount', 'sum'),
        avg_tx_value=('amount', 'mean')
    ).reset_index()
    
    agg_df['coin'] = 'BTC'
    
    print(f"📊 {len(agg_df)}일치 데이터 집계 완료")
    
    # 3. 지표 가공 및 저장
    max_vol = agg_df['total_volume'].max()
    if max_vol == 0: max_vol = 1
    
    agg_df['top100_richest_pct'] = (agg_df['total_volume'] / max_vol) * 100
    agg_df['avg_transaction_value_btc'] = agg_df['avg_tx_value']
    
    conn = get_sqlite_conn()
    cur = conn.cursor()
    
    for _, row in agg_df.iterrows():
        cur.execute("""
            INSERT OR REPLACE INTO bitinfocharts_whale 
            (date, coin, top100_richest_pct, avg_transaction_value_btc)
            VALUES (?, ?, ?, ?)
        """, (
            row['date'].strftime('%Y-%m-%d'),
            row['coin'],
            row['top100_richest_pct'],
            row['avg_transaction_value_btc']
        ))
    conn.commit()
    cur.close()
    conn.close()
        
    print("✅ SQLite 저장 완료")

def run_full_aggregation():
    """전체 집계 실행"""
    print("=" * 80)
    print("📊 고래 활동 지표 전체 집계")
    print("=" * 80)
    
    ensure_tables()
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase 설정 오류: .env 파일 확인 필요")
        return
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 수집 기간 설정 (UTC 기준)
    start_date = pd.Timestamp("2023-01-01", tz='UTC')
    end_date = pd.Timestamp.now(tz='UTC')
    
    # 1. 기존 bitinfocharts_whale 집계
    print("\n[1/3] bitinfocharts_whale 집계...")
    aggregate_whale_stats()
    
    # 2. 일별 고래 통계 집계
    print("\n[2/3] 일별 고래 통계 집계...")
    aggregate_daily_whale_stats(supabase, start_date, end_date)
    
    # 3. 주별 고래 통계 집계
    print("\n[3/3] 주별 고래 통계 집계...")
    aggregate_weekly_whale_stats()
    
    print("\n" + "=" * 80)
    print("✅ 전체 집계 완료!")
    print("=" * 80)


if __name__ == "__main__":
    """
    CLI 모드:
    - 기본: aggregate_whale_stats()만 실행 (기존 동작 유지)
    - --full: run_full_aggregation() 실행
    - --rebuild-all: 2022-01-01 ~ 현재 기간에 대해 whale_daily_stats/whale_weekly_stats 풀 리빌드
      (이미 있는 데이터는 INSERT OR REPLACE로 덮어쓰기)
    """
    import sys
    import pandas as pd

    args = sys.argv[1:]
    if "--rebuild-all" in args:
        print("=" * 80)
        print("♻️ whale_daily_stats / whale_weekly_stats 풀 리빌드")
        print("=" * 80)

        ensure_tables()

        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not SUPABASE_URL or not SUPABASE_KEY:
            print("❌ Supabase 설정 오류: .env 파일 확인 필요")
            sys.exit(1)

        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # UTC 기준으로 날짜 설정
        start_date = pd.Timestamp("2022-01-01", tz='UTC')
        end_date = pd.Timestamp.now(tz='UTC')

        aggregate_daily_whale_stats(supabase, start_date, end_date)
        aggregate_weekly_whale_stats()

        print("\n✅ whale_daily_stats / whale_weekly_stats 풀 리빌드 완료")
    elif len(args) > 0 and args[0] == "--full":
        run_full_aggregation()
    else:
        aggregate_whale_stats()

