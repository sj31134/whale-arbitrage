#!/usr/bin/env python3
"""
USDC, BNB, XRP 3개 코인의 2025년 5월, 6월 K-line 데이터를 수집하여 price_history 테이블에 저장
"""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
from supabase import create_client
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 바이낸스 API 기본 URL
BINANCE_API_BASE = "https://api.binance.com/api/v3"

# 수집 대상 코인 (crypto_symbol -> binance_symbol)
COINS_TO_COLLECT = {
    'USDC': 'USDCUSDT',
    'BNB': 'BNBUSDT',
    'XRP': 'XRPUSDT'
}

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def get_crypto_id_by_symbol(supabase, symbol: str) -> str:
    """심볼로 crypto_id 조회"""
    try:
        response = supabase.table('cryptocurrencies').select('id').eq('symbol', symbol).limit(1).execute()
        if response.data:
            return response.data[0]['id']
        return None
    except Exception as e:
        print(f"⚠️ crypto_id 조회 실패 ({symbol}): {e}")
        return None

def fetch_binance_klines_by_date_range(
    symbol: str, 
    start_time: datetime, 
    end_time: datetime, 
    interval: str = '1h'
) -> List[Dict]:
    """
    바이낸스에서 특정 기간의 K-line 데이터 조회 (페이지네이션 지원)
    
    Parameters:
    -----------
    symbol : str
        바이낸스 심볼 (예: 'USDCUSDT')
    start_time : datetime
        시작 시간
    end_time : datetime
        종료 시간
    interval : str
        K-line 간격 (기본값: '1h')
    
    Returns:
    --------
    List[Dict] : K-line 데이터 리스트
    """
    url = f"{BINANCE_API_BASE}/klines"
    all_klines = []
    
    # 시작 시간을 밀리초로 변환
    current_start = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)
    
    # 바이낸스 API limit은 최대 1000
    limit = 1000
    
    page = 1
    max_pages = 100  # 무한 루프 방지
    
    while current_start < end_timestamp and page <= max_pages:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current_start,
            'endTime': end_timestamp,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data or len(data) == 0:
                break
            
            # 바이낸스 K-line 형식을 딕셔너리로 변환
            for k in data:
                kline_time = datetime.fromtimestamp(k[0] / 1000)
                
                # 종료 시간을 초과하면 중단
                if kline_time > end_time:
                    break
                
                all_klines.append({
                    'open_time': kline_time,
                    'open_price': float(k[1]),
                    'high_price': float(k[2]),
                    'low_price': float(k[3]),
                    'close_price': float(k[4]),
                    'volume': float(k[5]),
                    'close_time': datetime.fromtimestamp(k[6] / 1000),
                    'quote_volume': float(k[7]),
                    'trade_count': int(k[8]),
                    'taker_buy_volume': float(k[9]),
                    'taker_buy_quote_volume': float(k[10]),
                })
            
            # 다음 페이지를 위해 마지막 K-line의 종료 시간 + 1밀리초를 시작 시간으로 설정
            if len(data) < limit:
                # 마지막 페이지
                break
            
            # 마지막 K-line의 종료 시간 + 1밀리초
            last_kline_time = data[-1][6]  # close_time (밀리초)
            current_start = last_kline_time + 1
            
            page += 1
            
            # API rate limit 방지
            time.sleep(0.2)
            
        except Exception as e:
            print(f"⚠️ 바이낸스 API 호출 실패 ({symbol}, 페이지 {page}): {e}")
            break
    
    return all_klines

def save_to_price_history(supabase, crypto_id: str, klines: List[Dict], symbol: str) -> int:
    """price_history 테이블에 저장 (upsert로 중복 자동 처리)"""
    records = []
    
    for kline in klines:
        record = {
            'crypto_id': crypto_id,
            'timestamp': kline['open_time'].isoformat(),
            'open_price': str(kline['open_price']),
            'high_price': str(kline['high_price']),
            'low_price': str(kline['low_price']),
            'close_price': str(kline['close_price']),
            'volume': str(kline['volume']),
            'quote_volume': str(kline['quote_volume']),
            'trade_count': kline['trade_count'],
            'taker_buy_volume': str(kline['taker_buy_volume']),
            'taker_buy_quote_volume': str(kline['taker_buy_quote_volume']),
            'data_source': 'binance',
            'raw_data': {
                'open_time': kline['open_time'].isoformat(),
                'close_time': kline['close_time'].isoformat(),
            }
        }
        records.append(record)
    
    if not records:
        return 0
    
    # 배치로 저장 (upsert로 중복 자동 처리)
    saved_count = 0
    batch_size = 100
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            # upsert 사용 (crypto_id + timestamp 기반으로 중복 자동 처리)
            response = supabase.table('price_history').upsert(batch).execute()
            saved_count += len(batch)
            
            if (i + batch_size) % 500 == 0:
                print(f"   ✅ {saved_count}/{len(records)}건 저장 중...")
                
        except Exception as e:
            print(f"⚠️ price_history 저장 실패 (배치 {i//batch_size + 1}): {e}")
            # 개별 저장 시도
            for record in batch:
                try:
                    supabase.table('price_history').upsert([record]).execute()
                    saved_count += 1
                except Exception as inner_e:
                    print(f"   ⚠️ 개별 저장 실패: {inner_e}")
                    pass
    
    return saved_count

def collect_price_history_for_coins(supabase, start_date: datetime, end_date: datetime):
    """USDC, BNB, XRP 3개 코인에 대해 특정 기간의 가격 데이터 수집"""
    print("=" * 70)
    print("📊 USDC, BNB, XRP 가격 데이터 수집 (2025년 5-6월)")
    print("=" * 70)
    print(f"\n수집 기간: {start_date.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"K-line 간격: 1시간")
    print("=" * 70)
    
    total_saved = 0
    results = {}
    
    for crypto_symbol, binance_symbol in COINS_TO_COLLECT.items():
        print(f"\n[{crypto_symbol}] {binance_symbol} 수집 중...")
        
        # crypto_id 조회
        crypto_id = get_crypto_id_by_symbol(supabase, crypto_symbol)
        if not crypto_id:
            print(f"   ⚠️ {crypto_symbol}의 crypto_id를 찾을 수 없습니다. cryptocurrencies 테이블에 추가하세요.")
            results[crypto_symbol] = {'status': 'failed', 'reason': 'crypto_id not found'}
            continue
        
        # 바이낸스에서 K-line 데이터 조회
        print(f"   📥 바이낸스 API에서 데이터 조회 중...")
        klines = fetch_binance_klines_by_date_range(
            binance_symbol, 
            start_date, 
            end_date, 
            interval='1h'
        )
        
        if not klines:
            print(f"   ⚠️ {binance_symbol} 데이터를 가져올 수 없습니다.")
            results[crypto_symbol] = {'status': 'failed', 'reason': 'no data', 'count': 0}
            continue
        
        print(f"   ✅ {len(klines)}건의 K-line 데이터 조회 완료")
        print(f"   📅 기간: {klines[0]['open_time'].strftime('%Y-%m-%d %H:%M')} ~ {klines[-1]['open_time'].strftime('%Y-%m-%d %H:%M')}")
        
        # price_history에 저장
        print(f"   💾 price_history 테이블에 저장 중...")
        saved = save_to_price_history(supabase, crypto_id, klines, crypto_symbol)
        total_saved += saved
        print(f"   ✅ {saved}건을 price_history에 저장 완료")
        
        results[crypto_symbol] = {
            'status': 'success',
            'collected': len(klines),
            'saved': saved
        }
        
        # API rate limit 방지
        time.sleep(0.5)
    
    # 결과 요약
    print("\n" + "=" * 70)
    print("✅ 수집 완료")
    print("=" * 70)
    print(f"\n📊 수집 결과:")
    for crypto_symbol, result in results.items():
        if result['status'] == 'success':
            print(f"   - {crypto_symbol}: {result['saved']}건 저장 (수집: {result['collected']}건)")
        else:
            print(f"   - {crypto_symbol}: 실패 ({result.get('reason', 'unknown')})")
    
    print(f"\n총 저장된 데이터: {total_saved}건")
    
    return total_saved, results

def main():
    """메인 함수"""
    # 2025년 5월 1일 00:00:00 UTC
    start_date = datetime(2025, 5, 1, 0, 0, 0)
    # 2025년 6월 30일 23:59:59 UTC
    end_date = datetime(2025, 6, 30, 23, 59, 59)
    
    try:
        supabase = get_supabase_client()
        
        # 데이터 수집
        total_saved, results = collect_price_history_for_coins(supabase, start_date, end_date)
        
        print("\n" + "=" * 70)
        print("✅ 작업 완료")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

