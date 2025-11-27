#!/usr/bin/env python3
"""
Bybit API를 사용하여 Open Interest 과거 데이터 수집
Binance API 제한(30일)을 우회하기 위한 대안
"""

import sqlite3
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

BYBIT_BASE = "https://api.bybit.com"
OI_ENDPOINT = f"{BYBIT_BASE}/v5/market/open-interest"


def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def test_bybit_oi_api(symbol="BTCUSDT", start_date="2023-01-01"):
    """Bybit OI API 테스트 - 과거 데이터 제공 범위 확인"""
    print("=" * 80)
    print("🔍 Bybit OI API 테스트")
    print("=" * 80)
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    start_ts = int(start_dt.timestamp() * 1000)
    
    # 테스트 1: 최근 데이터 조회
    print(f"\n1️⃣ 최근 데이터 조회 테스트...")
    params = {
        "category": "linear",  # 선물
        "symbol": symbol,
        "intervalTime": "D",  # 일별 (intervalTime 파라미터 사용)
        "limit": 200
    }
    
    try:
        response = requests.get(OI_ENDPOINT, params=params, timeout=30)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("retCode") == 0:
                result = data.get("result", {})
                list_data = result.get("list", [])
                
                if list_data:
                    print(f"   ✅ API 응답 성공: {len(list_data)}건")
                    print(f"   첫 데이터: {list_data[0]}")
                    print(f"   마지막 데이터: {list_data[-1]}")
                    
                    # 날짜 확인
                    first_ts = int(list_data[0].get("timestamp", 0))
                    last_ts = int(list_data[-1].get("timestamp", 0))
                    first_date = datetime.utcfromtimestamp(first_ts / 1000).date()
                    last_date = datetime.utcfromtimestamp(last_ts / 1000).date()
                    
                    print(f"   기간: {first_date} ~ {last_date}")
                    
                    # 과거 데이터 제공 여부 확인
                    if first_date <= start_dt.date():
                        print(f"   ✅ {start_date}부터의 데이터 제공 가능!")
                        return True, first_date, last_date
                    else:
                        print(f"   ⚠️ {start_date} 이전 데이터는 제공되지 않음 (최초 데이터: {first_date})")
                        return False, first_date, last_date
                else:
                    print(f"   ⚠️ 데이터 없음")
                    return False, None, None
            else:
                print(f"   ❌ API 오류: {data.get('retMsg')}")
                return False, None, None
        else:
            print(f"   ❌ HTTP 오류: {response.status_code}")
            print(f"   응답: {response.text[:200]}")
            return False, None, None
            
    except Exception as e:
        print(f"   ❌ 오류 발생: {e}")
        return False, None, None


def fetch_bybit_oi_historical(symbol="BTCUSDT", start_date="2023-01-01"):
    """Bybit OI 과거 데이터 수집"""
    print("\n" + "=" * 80)
    print(f"📊 Bybit OI 과거 데이터 수집 ({symbol})")
    print("=" * 80)
    
    # API 테스트
    can_fetch, first_date, last_date = test_bybit_oi_api(symbol, start_date)
    
    if not can_fetch:
        print("\n⚠️ Bybit API로 과거 데이터 수집 불가")
        print("   대안: 매일 자동 수집 스크립트 사용")
        print("   python3 scripts/subprojects/risk_ai/collect_oi_historical.py")
        return 0
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.now()
    
    oi_by_date = defaultdict(list)
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    
    # Bybit API는 startTime/endTime 파라미터를 지원하지 않을 수 있음
    # limit만 사용하여 최신 데이터부터 역순으로 수집
    print(f"\n📥 데이터 수집 중...")
    
    collected_count = 0
    limit = 200
    cursor = None  # 페이지네이션용
    
    while True:
        params = {
            "category": "linear",
            "symbol": symbol,
            "intervalTime": "D",  # intervalTime 파라미터 사용
            "limit": limit
        }
        
        if cursor:
            params["cursor"] = cursor
        
        try:
            response = session.get(OI_ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("retCode") != 0:
                print(f"   ⚠️ API 오류: {data.get('retMsg')}")
                break
            
            result = data.get("result", {})
            list_data = result.get("list", [])
            
            if not list_data:
                break
            
            for entry in list_data:
                ts = int(entry.get("timestamp", 0))
                dt = datetime.utcfromtimestamp(ts / 1000).date()
                
                # start_date 이전 데이터는 수집 중단
                if dt < start_dt.date():
                    break
                
                oi_value = float(entry.get("openInterest", 0.0))
                oi_by_date[dt].append(oi_value)
                collected_count += 1
            
            # 다음 페이지 확인
            next_cursor = result.get("nextPageCursor")
            if not next_cursor or dt < start_dt.date():
                break
            
            cursor = next_cursor
            time.sleep(0.2)  # Rate limit 방지
            
        except Exception as e:
            print(f"   ⚠️ 오류: {e}")
            break
    
    if not oi_by_date:
        print("\n⚠️ 수집된 데이터가 없습니다.")
        return 0
    
    # DB 업데이트
    print(f"\n💾 DB 업데이트 중...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updated_count = 0
    for date_str, oi_values in sorted(oi_by_date.items()):
        if not oi_values:
            continue
        
        avg_oi = sum(oi_values) / len(oi_values)
        
        # binance_futures_metrics 테이블에 업데이트
        cursor.execute("""
            UPDATE binance_futures_metrics
            SET sum_open_interest = ?
            WHERE symbol = ? AND date = ?
        """, (avg_oi, symbol, date_str.isoformat()))
        
        if cursor.rowcount > 0:
            updated_count += 1
        else:
            # 레코드가 없으면 새로 생성 (다른 필드는 0으로)
            cursor.execute("""
                INSERT INTO binance_futures_metrics
                (date, symbol, avg_funding_rate, sum_open_interest, long_short_ratio, volatility_24h, target_volatility_24h)
                VALUES (?, ?, 0.0, ?, 0.0, 0.0, 0.0)
            """, (date_str.isoformat(), symbol, avg_oi))
            updated_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"   ✅ {updated_count}건 업데이트 완료")
    
    # 결과 확인
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(*) as count
        FROM binance_futures_metrics
        WHERE symbol = ? AND sum_open_interest > 0
    """, (symbol,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        print(f"\n📊 업데이트 후 OI 데이터:")
        print(f"   기간: {result[0]} ~ {result[1]}")
        print(f"   총 일수: {result[2]}일")
    
    return updated_count


def main():
    ensure_db()
    
    print("=" * 80)
    print("🔍 Bybit API OI 데이터 수집")
    print("=" * 80)
    
    # BTCUSDT만 테스트
    count = fetch_bybit_oi_historical("BTCUSDT", start_date="2023-01-01")
    
    print("\n" + "=" * 80)
    if count > 0:
        print(f"✅ {count}건의 OI 데이터 수집 완료")
    else:
        print("⚠️ Bybit API로 과거 데이터 수집 불가")
        print("   매일 자동 수집 스크립트를 사용하세요:")
        print("   python3 scripts/subprojects/risk_ai/collect_oi_historical.py")
    print("=" * 80)


if __name__ == "__main__":
    main()

