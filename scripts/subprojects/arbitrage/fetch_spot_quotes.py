#!/usr/bin/env python3
"""
업비트/KRW와 바이낸스/USDT 과거 일봉 데이터를 수집하여 SQLite에 저장하는 서브 프로젝트 스크립트입니다.
"""

import os
import sqlite3
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / "config" / ".env")
DB_PATH = ROOT / "data" / "project.db"

UPBIT_BASE = "https://api.upbit.com/v1/candles/days"
BINANCE_BASE = "https://api.binance.com/api/v3/klines"
BITGET_BASE = "https://api.bitget.com/api/v2/spot/market/candles"  # V2 API
BYBIT_BASE = "https://api.bybit.com/v5/market/kline"


def _parse_ymd(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def _get_max_date(conn: sqlite3.Connection, table: str, where_sql: str, params: tuple) -> str:
    cur = conn.cursor()
    cur.execute(f"SELECT MAX(date) FROM {table} WHERE {where_sql}", params)
    row = cur.fetchone()
    cur.close()
    return row[0] if row and row[0] else None


def ensure_db():
    """DB 초기화 및 필요한 테이블 생성"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    
    cursor = conn.cursor()
    
    # bybit_spot_daily 테이블 생성 (없으면)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bybit_spot_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            open DECIMAL(20, 8),
            high DECIMAL(20, 8),
            low DECIMAL(20, 8),
            close DECIMAL(20, 8),
            volume DECIMAL(30, 8),
            quote_volume DECIMAL(30, 8),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, symbol)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bybit_spot_date ON bybit_spot_daily(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bybit_spot_symbol ON bybit_spot_daily(symbol)")
    
    # bitget_spot_daily 테이블 생성 (없으면)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bitget_spot_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            open DECIMAL(20, 8),
            high DECIMAL(20, 8),
            low DECIMAL(20, 8),
            close DECIMAL(20, 8),
            volume DECIMAL(30, 8),
            quote_volume DECIMAL(30, 8),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, symbol)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bitget_date ON bitget_spot_daily(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bitget_symbol ON bitget_spot_daily(symbol)")
    
    conn.commit()
    cursor.close()
    conn.close()


def upsert_rows(table, rows, columns):
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    placeholders = ", ".join("?" for _ in columns)
    column_list = ", ".join(columns)
    stmt = f"INSERT OR REPLACE INTO {table} ({column_list}) VALUES ({placeholders})"
    cursor.executemany(stmt, rows)
    conn.commit()
    cursor.close()
    conn.close()


def fetch_upbit_daily(market, end_date: datetime, stop_date: datetime):
    """Upbit 지정 기간 수집 (역순, end_date ~ stop_date)"""
    target_date = end_date
    stop_date = stop_date
    
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)

    while target_date > stop_date:
        to_str = target_date.strftime("%Y-%m-%d %H:%M:%S")
        params = {"market": market, "to": to_str, "count": 200}
        headers = {"Accept": "application/json"}
        
        try:
            response = session.get(UPBIT_BASE, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if not data:
                break
                
            rows = []
            min_date = None
            
            for candle in data:
                kst_str = candle["candle_date_time_kst"]
                dt_obj = datetime.strptime(kst_str, "%Y-%m-%dT%H:%M:%S")
                rows.append(
                    (
                        market,
                        kst_str.split("T")[0],
                        candle.get("opening_price", candle.get("trade_price")),  # opening_price
                        candle.get("high_price", candle.get("trade_price")),     # high_price
                        candle.get("low_price", candle.get("trade_price")),      # low_price
                        candle["trade_price"],                                    # trade_price (close)
                        candle.get("candle_acc_trade_volume", candle.get("acc_trade_volume", 0.0)),
                        candle.get("candle_acc_trade_price", candle.get("acc_trade_price", 0.0)),
                    )
                )
                if min_date is None or dt_obj < min_date:
                    min_date = dt_obj

            upsert_rows(
                "upbit_daily",
                rows,
                ["market", "date", "opening_price", "high_price", "low_price", "trade_price", "acc_trade_volume_24h", "acc_trade_price_24h"],
            )
            print(f"✅ Upbit {market}: ~{to_str.split()[0]} ({len(rows)}건)")
            
            if min_date:
                target_date = min_date - timedelta(days=1)
                if min_date.date() <= stop_date.date():
                    break
            else:
                break
                
            time.sleep(0.1) # Rate limit 조절
            
        except Exception as e:
            print(f"⚠️ Upbit {market} fetch error: {e}")
            time.sleep(1)
            break


def fetch_binance_spot(symbol, start_dt: datetime, end_dt_exclusive: datetime):
    """Binance 지정 기간 수집 (정순, start_dt ~ end_dt_exclusive)"""
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt_exclusive.timestamp() * 1000)
    
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)

    while start_ts < end_ts:
        # endTime을 반드시 지정해야 end_dt_exclusive 이후 데이터가 섞이지 않음
        params = {"symbol": symbol, "interval": "1d", "startTime": start_ts, "endTime": end_ts - 1, "limit": 1000}
        try:
            response = session.get(BINANCE_BASE, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
                
            rows = []
            last_ts = start_ts
            
            for kline in data:
                ts = int(kline[0])
                dt_str = datetime.utcfromtimestamp(ts / 1000).date().isoformat()
                # kline: [open_time, open, high, low, close, volume, close_time, quote_volume, ...]
                rows.append((
                    symbol, 
                    dt_str, 
                    float(kline[1]),  # open
                    float(kline[2]),  # high
                    float(kline[3]),  # low
                    float(kline[4]),  # close
                    float(kline[5]),  # volume
                    float(kline[7])   # quote_volume
                ))
                last_ts = ts
            
            upsert_rows(
                "binance_spot_daily",
                rows,
                ["symbol", "date", "open", "high", "low", "close", "volume", "quote_volume"],
            )
            
            last_dt_str = datetime.utcfromtimestamp(last_ts / 1000).strftime('%Y-%m-%d')
            print(f"✅ Binance {symbol}: ~{last_dt_str} ({len(rows)}건)")
            
            start_ts = last_ts + 24 * 60 * 60 * 1000 # Next day
            time.sleep(0.1)
            
        except Exception as e:
            print(f"⚠️ Binance {symbol} fetch error: {e}")
            time.sleep(1)
            break


def fetch_bitget_spot(symbol, start_date_str="2024-01-01", end_dt_exclusive: datetime = None):
    """Bitget V2 API로 지정 날짜부터 end_dt_exclusive까지 수집 (역순)"""
    # Bitget V2 API는 symbol 형식: BTCUSDT (SPBL 없이)
    symbol_api = symbol
    
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    start_ts = int(start_dt.timestamp() * 1000)
    if end_dt_exclusive is None:
        end_ts = int(datetime.now().timestamp() * 1000)
    else:
        end_ts = int(end_dt_exclusive.timestamp() * 1000)
    
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)

    print(f"🔄 Bitget V2 {symbol} 수집 시작 ({start_date_str} ~ 현재)...")
    
    current_end_ts = end_ts
    
    while current_end_ts > start_ts:
        # Bitget V2 API 파라미터
        # V2 API 문서: https://www.bitget.com/api-doc/spot/market/Get-Candle-Data
        # granularity 허용값: 1min,3min,5min,15min,30min,1h,4h,6h,12h,1day,1week,1M,6Hutc,12Hutc,1Dutc,3Dutc,1Wutc,1Mutc
        params = {
            "symbol": symbol_api,
            "productType": "spot",
            "granularity": "1day",  # 1일봉 (허용값: 1day 또는 1Dutc)
            "startTime": str(start_ts),
            "endTime": str(current_end_ts),
            "limit": 200
        }
        
        try:
            response = session.get(BITGET_BASE, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"⚠️ Bitget {symbol} HTTP {response.status_code}: {response.text[:200]}")
                break
            
            result = response.json()
            
            # V2 API 응답 형식: {"code": "00000", "msg": "success", "data": [...]}
            if result.get("code") != "00000" or not result.get("data"):
                error_msg = result.get('msg', result.get('message', 'Unknown error'))
                print(f"⚠️ Bitget {symbol} API 응답 오류: {error_msg}")
                print(f"   응답: {result}")
                break
            
            data = result.get("data", [])
            if not data:
                break
                
            rows = []
            timestamps = []
            
            for candle in data:
                # V2 API 응답 형식: [ts, open, high, low, close, baseVol, quoteVol] 또는 객체 형식
                if isinstance(candle, list):
                    # 배열 형식: [timestamp, open, high, low, close, baseVol, quoteVol]
                    ts = int(candle[0])
                    open_price = float(candle[1])
                    high_price = float(candle[2])
                    low_price = float(candle[3])
                    close_price = float(candle[4])
                    base_vol = float(candle[5]) if len(candle) > 5 else 0
                    quote_vol = float(candle[6]) if len(candle) > 6 else 0
                else:
                    # 객체 형식: {"ts": ..., "open": ..., ...}
                    ts = int(candle.get("ts", candle.get("timestamp", candle.get("time", 0))))
                    open_price = float(candle.get("open", candle.get("o", 0)))
                    high_price = float(candle.get("high", candle.get("h", 0)))
                    low_price = float(candle.get("low", candle.get("l", 0)))
                    close_price = float(candle.get("close", candle.get("c", 0)))
                    base_vol = float(candle.get("baseVol", candle.get("vol", candle.get("volume", 0))))
                    quote_vol = float(candle.get("quoteVol", candle.get("usdtVol", candle.get("quoteVolume", 0))))
                
                if ts == 0:
                    continue
                    
                timestamps.append(ts)
                dt_str = datetime.utcfromtimestamp(ts / 1000).date().isoformat()
                
                rows.append((
                    symbol,
                    dt_str,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    base_vol,
                    quote_vol,
                ))
            
            if rows:
                upsert_rows(
                    "bitget_spot_daily",
                    rows,
                    ["symbol", "date", "open", "high", "low", "close", "volume", "quote_volume"],
                )
                
                oldest_ts = min(timestamps)
                newest_ts = max(timestamps)
                oldest_dt = datetime.utcfromtimestamp(oldest_ts / 1000).strftime('%Y-%m-%d')
                newest_dt = datetime.utcfromtimestamp(newest_ts / 1000).strftime('%Y-%m-%d')
                
                print(f"✅ Bitget {symbol}: {oldest_dt} ~ {newest_dt} ({len(rows)}건)")
                
                current_end_ts = oldest_ts - 1
                
                if oldest_ts <= start_ts:
                    print(f"✅ Bitget {symbol}: 수집 완료 (시작일 도달)")
                    break
            else:
                print(f"⚠️ Bitget {symbol}: 더 이상 데이터 없음")
                break
                
            time.sleep(0.1)
            
        except Exception as e:
            print(f"⚠️ Bitget {symbol} fetch error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(1)
            break


def fetch_bybit_spot(symbol, start_date_str="2024-01-01"):
    """Bybit 지정 날짜부터 현재까지 수집 (레거시)"""
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_ts = int(datetime.now().timestamp() * 1000)
    
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)

    print(f"🔄 Bybit {symbol} 수집 시작 ({start_date_str} ~ 현재)...")
    
    # Bybit API는 최신 데이터부터 역순으로 반환
    cursor = None
    all_rows = []
    
    while True:
        params = {
            "category": "spot",
            "symbol": symbol,
            "interval": "D",
            "limit": 200
        }
        if cursor:
            params["cursor"] = cursor
        
        try:
            response = session.get(BYBIT_BASE, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"⚠️ Bybit {symbol} HTTP {response.status_code}: {response.text[:200]}")
                break
            
            result = response.json()
            
            if result.get("retCode") != 0:
                print(f"⚠️ Bybit {symbol} API 오류: {result.get('retMsg')}")
                break
            
            data = result.get("result", {}).get("list", [])
            if not data:
                break
            
            rows = []
            oldest_ts = None
            
            for candle in data:
                # Bybit 응답: [timestamp, open, high, low, close, volume, turnover]
                ts = int(candle[0])
                dt = datetime.utcfromtimestamp(ts / 1000)
                
                # 시작일 이전 데이터는 제외
                if dt < start_dt:
                    continue
                
                if oldest_ts is None or ts < oldest_ts:
                    oldest_ts = ts
                
                dt_str = dt.date().isoformat()
                rows.append((
                    symbol,
                    dt_str,
                    float(candle[1]),  # open
                    float(candle[2]),  # high
                    float(candle[3]),  # low
                    float(candle[4]),  # close
                    float(candle[5]),  # volume
                    float(candle[6])   # turnover (quote_volume)
                ))
            
            if rows:
                upsert_rows(
                    "bybit_spot_daily",
                    rows,
                    ["symbol", "date", "open", "high", "low", "close", "volume", "quote_volume"],
                )
                all_rows.extend(rows)
                
                oldest_dt = datetime.utcfromtimestamp(oldest_ts / 1000).strftime('%Y-%m-%d')
                print(f"✅ Bybit {symbol}: ~{oldest_dt} ({len(rows)}건)")
            
            # 다음 페이지 확인
            next_cursor = result.get("result", {}).get("nextPageCursor")
            if not next_cursor or oldest_ts and datetime.utcfromtimestamp(oldest_ts / 1000) <= start_dt:
                break
            cursor = next_cursor
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"⚠️ Bybit {symbol} fetch error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(1)
            break
    
    print(f"✅ Bybit {symbol}: 총 {len(all_rows)}건 수집 완료")


def fetch_bybit_spot_range(symbol, start_date_str="2024-01-01", end_dt_exclusive: datetime = None):
    """Bybit 지정 날짜부터 end_dt_exclusive까지 수집 (역순 페이지네이션, 필터링)"""
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    if end_dt_exclusive is None:
        end_dt_exclusive = datetime.now()

    # end_dt_exclusive 이전(포함)의 데이터만 저장하기 위해 마지막 포함일을 계산
    end_inclusive = (end_dt_exclusive - timedelta(days=1)).date()

    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)

    print(f"🔄 Bybit {symbol} 수집 시작 ({start_date_str} ~ {end_inclusive.isoformat()})...")

    cursor = None
    total_saved = 0

    while True:
        params = {"category": "spot", "symbol": symbol, "interval": "D", "limit": 200}
        if cursor:
            params["cursor"] = cursor

        try:
            response = session.get(BYBIT_BASE, params=params, timeout=10)
            if response.status_code != 200:
                print(f"⚠️ Bybit {symbol} HTTP {response.status_code}: {response.text[:200]}")
                break

            result = response.json()
            if result.get("retCode") != 0:
                print(f"⚠️ Bybit {symbol} API 오류: {result.get('retMsg')}")
                break

            data = result.get("result", {}).get("list", [])
            if not data:
                break

            rows = []
            oldest_ts = None

            for candle in data:
                ts = int(candle[0])
                dt = datetime.utcfromtimestamp(ts / 1000)

                # end 범위 초과(미래) 데이터는 스킵
                if dt.date() > end_inclusive:
                    continue

                # start 범위 이전이면 종료 조건으로 사용
                if dt < start_dt:
                    continue

                if oldest_ts is None or ts < oldest_ts:
                    oldest_ts = ts

                dt_str = dt.date().isoformat()
                rows.append(
                    (
                        symbol,
                        dt_str,
                        float(candle[1]),
                        float(candle[2]),
                        float(candle[3]),
                        float(candle[4]),
                        float(candle[5]),
                        float(candle[6]),
                    )
                )

            if rows:
                upsert_rows(
                    "bybit_spot_daily",
                    rows,
                    ["symbol", "date", "open", "high", "low", "close", "volume", "quote_volume"],
                )
                total_saved += len(rows)
                oldest_dt = datetime.utcfromtimestamp(oldest_ts / 1000).strftime("%Y-%m-%d") if oldest_ts else "N/A"
                print(f"✅ Bybit {symbol}: ~{oldest_dt} ({len(rows)}건)")

            next_cursor = result.get("result", {}).get("nextPageCursor")
            if not next_cursor:
                break

            # start_date 이전까지 도달했는지 체크
            if oldest_ts and datetime.utcfromtimestamp(oldest_ts / 1000) <= start_dt:
                break

            cursor = next_cursor
            time.sleep(0.1)

        except Exception as e:
            print(f"⚠️ Bybit {symbol} fetch error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(1)
            break

    print(f"✅ Bybit {symbol}: 총 {total_saved}건 수집 완료")


def main():
    ensure_db()
    parser = argparse.ArgumentParser(description="Spot daily data collection for Upbit/Binance/Bitget/Bybit into SQLite")
    parser.add_argument("--end-date", type=str, default=None, help="포함되는 종료일 (YYYY-MM-DD). 미지정 시 오늘(로컬) 기준")
    args = parser.parse_args()

    if args.end_date:
        end_date = _parse_ymd(args.end_date)
        end_dt_exclusive = end_date + timedelta(days=1)
        # Bitget은 일봉 경계가 UTC+8(=UTC 16:00)로 잡히는 경우가 있어,
        # end-date(포함) 일봉이 누락되지 않도록 1일 버퍼를 둔 뒤 저장 후 클램프합니다.
        bitget_end_dt_exclusive = end_dt_exclusive + timedelta(days=1)
        # Upbit은 'to'로 inclusive 성격이므로 23:59:59로 맞춤
        upbit_end_dt = end_date.replace(hour=23, minute=59, second=59)
    else:
        # 기본: 오늘까지(실행 시점)
        today = datetime.now().date()
        upbit_end_dt = datetime.now()
        end_dt_exclusive = datetime.now()
        bitget_end_dt_exclusive = datetime.now()

    upbit_markets = os.getenv("UPBIT_MARKETS", "KRW-BTC,KRW-ETH").split(",")
    binance_symbols = os.getenv("BINANCE_SYMBOLS", "BTCUSDT,ETHUSDT").split(",")
    bitget_symbols = os.getenv("BITGET_SYMBOLS", "BTCUSDT,ETHUSDT").split(",")
    bybit_symbols = os.getenv("BYBIT_SYMBOLS", "BTCUSDT,ETHUSDT").split(",")

    # DB에서 각 심볼별 max(date) 기반으로 증분 수집
    conn = sqlite3.connect(DB_PATH)

    print("📊 업비트 데이터 수집 시작...")
    for market in upbit_markets:
        m = market.strip()
        max_date = _get_max_date(conn, "upbit_daily", "market = ?", (m,))
        stop_dt = datetime(2023, 1, 1)
        if max_date:
            stop_dt = _parse_ymd(max_date)
            if args.end_date and max_date >= args.end_date:
                print(f"⏭️ Upbit {m}: 이미 최신 ({max_date})")
                continue
        fetch_upbit_daily(m, upbit_end_dt, stop_dt)
    
    print("\n📊 바이낸스 데이터 수집 시작...")
    for symbol in binance_symbols:
        s = symbol.strip()
        max_date = _get_max_date(conn, "binance_spot_daily", "symbol = ?", (s,))
        if max_date and args.end_date and max_date >= args.end_date:
            print(f"⏭️ Binance {s}: 이미 최신 ({max_date})")
            continue
        start_dt = _parse_ymd(max_date) + timedelta(days=1) if max_date else datetime(2023, 1, 1)
        fetch_binance_spot(s, start_dt, end_dt_exclusive)
    
    print("\n📊 비트겟 데이터 수집 시작...")
    for symbol in bitget_symbols:
        s = symbol.strip()
        max_date = _get_max_date(conn, "bitget_spot_daily", "symbol = ?", (s,))
        if max_date and args.end_date and max_date >= args.end_date:
            print(f"⏭️ Bitget {s}: 이미 최신 ({max_date})")
            continue
        start_date_str = (datetime.strptime(max_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d") if max_date else "2024-01-01"
        fetch_bitget_spot(s, start_date_str=start_date_str, end_dt_exclusive=bitget_end_dt_exclusive)
    
    print("\n📊 바이비트 데이터 수집 시작...")
    for symbol in bybit_symbols:
        s = symbol.strip()
        max_date = _get_max_date(conn, "bybit_spot_daily", "symbol = ?", (s,))
        if max_date and args.end_date and max_date >= args.end_date:
            print(f"⏭️ Bybit {s}: 이미 최신 ({max_date})")
            continue
        start_date_str = (datetime.strptime(max_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d") if max_date else "2024-01-01"
        fetch_bybit_spot_range(s, start_date_str=start_date_str, end_dt_exclusive=end_dt_exclusive)

    conn.close()

    # end-date가 지정된 경우, 방어적으로 초과 데이터 제거 (특히 Binance/Bitget)
    if args.end_date:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM binance_spot_daily WHERE date > ?", (args.end_date,))
        cur.execute("DELETE FROM bitget_spot_daily WHERE date > ?", (args.end_date,))
        cur.execute("DELETE FROM bybit_spot_daily WHERE date > ?", (args.end_date,))
        cur.execute("DELETE FROM upbit_daily WHERE date > ?", (args.end_date,))
        conn.commit()
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()

