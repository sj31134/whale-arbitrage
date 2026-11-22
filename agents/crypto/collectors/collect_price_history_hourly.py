#!/usr/bin/env python3
"""
모든 주요 코인에 대해 1시간 단위 가격 데이터 수집 (2025년 1월 1일 ~ 오늘)
Binance API를 사용하여 price_history 테이블에 저장
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from supabase import create_client
import requests
import threading

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 바이낸스 API 기본 URL
BINANCE_API_BASE = "https://api.binance.com/api/v3"

# 수집 대상 코인 (crypto_symbol -> binance_symbol)
# 주요 코인들을 포함
COINS_TO_COLLECT = {
    'BTC': 'BTCUSDT',
    'ETH': 'ETHUSDT',
    'BNB': 'BNBUSDT',
    'USDC': 'USDCUSDT',
    'XRP': 'XRPUSDT',
    'LTC': 'LTCUSDT',
    'DOGE': 'DOGEUSDT',
    'LINK': 'LINKUSDT',
    'SOL': 'SOLUSDT',
    'DOT': 'DOTUSDT',
}

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def get_crypto_id_by_symbol(supabase, symbol: str) -> Optional[str]:
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
        바이낸스 심볼 (예: 'BTCUSDT')
    start_time : datetime
        시작 시간 (UTC)
    end_time : datetime
        종료 시간 (UTC)
    interval : str
        K-line 간격 (기본값: '1h')
    
    Returns:
    --------
    List[Dict] : K-line 데이터 리스트
    """
    url = f"{BINANCE_API_BASE}/klines"
    all_klines = []
    
    # 시작 시간을 밀리초로 변환 (UTC 기준)
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    
    current_start = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)
    
    # 바이낸스 API limit은 최대 1000
    limit = 1000
    
    page = 1
    max_pages = 1000  # 무한 루프 방지
    
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
                kline_time = datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc)
                
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
                    'close_time': datetime.fromtimestamp(k[6] / 1000, tz=timezone.utc),
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
            
            # 진행 상황 출력
            if page % 10 == 0:
                print(f"      페이지 {page} 처리 중... (현재 {len(all_klines)}건 수집)")
            
        except Exception as e:
            print(f"⚠️ 바이낸스 API 호출 실패 ({symbol}, 페이지 {page}): {e}")
            break
    
    return all_klines

def save_to_price_history(supabase, crypto_id: str, klines: List[Dict], symbol: str) -> int:
    """price_history 테이블에 저장 (중복 확인 후 upsert)"""
    records = []

    for kline in klines:
        # UTC 타임존 명시적으로 설정
        open_time = kline['open_time']
        if open_time.tzinfo is None:
            open_time = open_time.replace(tzinfo=timezone.utc)

        record = {
            'crypto_id': crypto_id,
            'timestamp': open_time.isoformat(),  # ISO 형식으로 저장 (UTC)
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
                'open_time': open_time.isoformat(),
                'close_time': kline['close_time'].isoformat() if kline['close_time'].tzinfo else kline['close_time'].replace(tzinfo=timezone.utc).isoformat(),
            }
        }
        records.append(record)

    if not records:
        return 0

    # 배치로 저장 (중복 확인 후 upsert)
    saved_count = 0
    batch_size = 50  # 배치 크기 축소

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]

        # 중복 데이터 확인 및 필터링
        filtered_batch = []
        for record in batch:
            try:
                # 해당 레코드가 이미 존재하는지 확인
                existing = supabase.table('price_history')\
                    .select('id')\
                    .eq('crypto_id', record['crypto_id'])\
                    .eq('timestamp', record['timestamp'])\
                    .eq('data_source', record['data_source'])\
                    .limit(1)\
                    .execute()

                if not existing.data:
                    # 중복이 없으면 추가
                    filtered_batch.append(record)

            except Exception as e:
                print(f"      ⚠️ 중복 확인 실패: {e}")
                # 중복 확인 실패 시 일단 추가
                filtered_batch.append(record)

        if not filtered_batch:
            # 모든 데이터가 중복이면 다음 배치로
            print(f"      ⏭️ 배치 {i//batch_size + 1}의 모든 데이터가 중복됨, 스킵")
            saved_count += len(batch)  # 카운트는 유지
            continue

        try:
            # upsert 사용 (중복 없음이 확인된 데이터만)
            response = supabase.table('price_history').upsert(filtered_batch).execute()
            saved_count += len(filtered_batch)

            if (i + batch_size) % 200 == 0:
                print(f"      💾 {saved_count}/{len(records)}건 저장 중... ({len(filtered_batch)}건 신규)")

        except Exception as e:
            print(f"⚠️ price_history 저장 실패 (배치 {i//batch_size + 1}): {e}")
            # 개별 저장 시도 (중복 확인 후)
            for record in filtered_batch:
                try:
                    # 다시 한 번 중복 확인
                    existing = supabase.table('price_history')\
                        .select('id')\
                        .eq('crypto_id', record['crypto_id'])\
                        .eq('timestamp', record['timestamp'])\
                        .eq('data_source', record['data_source'])\
                        .limit(1)\
                        .execute()

                    if not existing.data:
                        supabase.table('price_history').insert(record).execute()
                        saved_count += 1

                except Exception as inner_e:
                    if 'duplicate key' not in str(inner_e):
                        print(f"      ⚠️ 개별 저장 실패: {inner_e}")

    return saved_count

# 전역 변수: 진행률 추적
progress_info = {
    'current_coin': '',
    'current_symbol': '',
    'total_coins': 0,
    'completed_coins': 0,
    'total_saved': 0,
    'start_time': None,
    'last_update': None
}

def print_progress():
    """진행률 출력"""
    if progress_info['start_time']:
        elapsed = (datetime.now(timezone.utc) - progress_info['start_time']).total_seconds()
        elapsed_min = int(elapsed // 60)
        elapsed_sec = int(elapsed % 60)
        
        if progress_info['total_coins'] > 0:
            coin_progress = (progress_info['completed_coins'] / progress_info['total_coins']) * 100
            print(f"\n⏱️  진행률: {progress_info['completed_coins']}/{progress_info['total_coins']} 코인 완료 ({coin_progress:.1f}%)")
            print(f"   현재 코인: {progress_info['current_coin']} ({progress_info['current_symbol']})")
            print(f"   총 저장: {progress_info['total_saved']:,}건")
            print(f"   경과 시간: {elapsed_min}분 {elapsed_sec}초")
            print("=" * 70)

def progress_monitor():
    """10분마다 진행률 출력하는 모니터링 스레드"""
    while True:
        time.sleep(600)  # 10분 = 600초
        if progress_info['start_time']:
            print_progress()

def collect_price_history_for_coins(supabase, start_date: datetime, end_date: datetime):
    """모든 코인에 대해 특정 기간의 가격 데이터 수집 (1시간 간격)"""
    print("=" * 70)
    print("📊 1시간 단위 가격 데이터 수집")
    print("=" * 70)
    print(f"\n수집 기간: {start_date.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"K-line 간격: 1시간")
    print(f"대상 코인: {', '.join(COINS_TO_COLLECT.keys())}")
    print("=" * 70)
    
    # 진행률 추적 초기화
    progress_info['total_coins'] = len(COINS_TO_COLLECT)
    progress_info['completed_coins'] = 0
    progress_info['total_saved'] = 0
    progress_info['start_time'] = datetime.now(timezone.utc)
    progress_info['last_update'] = datetime.now(timezone.utc)
    
    # 진행률 모니터링 스레드 시작
    monitor_thread = threading.Thread(target=progress_monitor, daemon=True)
    monitor_thread.start()
    
    total_saved = 0
    results = {}
    
    for crypto_symbol, binance_symbol in COINS_TO_COLLECT.items():
        progress_info['current_coin'] = crypto_symbol
        progress_info['current_symbol'] = binance_symbol
        print(f"\n[{crypto_symbol}] {binance_symbol} 수집 중...")
        
        # crypto_id 조회
        crypto_id = get_crypto_id_by_symbol(supabase, crypto_symbol)
        if not crypto_id:
            print(f"   ⚠️ {crypto_symbol}의 crypto_id를 찾을 수 없습니다. cryptocurrencies 테이블에 추가하세요.")
            results[crypto_symbol] = {'status': 'failed', 'reason': 'crypto_id not found'}
            continue
        
        # 바이낸스에서 K-line 데이터 조회
        print(f"   📥 바이낸스 API에서 데이터 조회 중...")
        try:
            klines = fetch_binance_klines_by_date_range(
                binance_symbol, 
                start_date, 
                end_date, 
                interval='1h'
            )
        except Exception as e:
            print(f"   ❌ 데이터 조회 실패: {e}")
            results[crypto_symbol] = {'status': 'failed', 'reason': str(e)}
            continue
        
        if not klines:
            print(f"   ⚠️ {binance_symbol} 데이터를 가져올 수 없습니다.")
            results[crypto_symbol] = {'status': 'failed', 'reason': 'no data', 'count': 0}
            continue
        
        print(f"   ✅ {len(klines)}건의 K-line 데이터 조회 완료")
        if klines:
            print(f"   📅 기간: {klines[0]['open_time'].strftime('%Y-%m-%d %H:%M')} ~ {klines[-1]['open_time'].strftime('%Y-%m-%d %H:%M')} (UTC)")
        
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
        
        # 진행률 업데이트
        progress_info['completed_coins'] += 1
        progress_info['total_saved'] += saved
        progress_info['last_update'] = datetime.now(timezone.utc)
        
        # API rate limit 방지
        time.sleep(0.5)
    
    # 결과 요약
    print("\n" + "=" * 70)
    print("✅ 수집 완료")
    print("=" * 70)
    print(f"\n📊 수집 결과:")
    for crypto_symbol, result in results.items():
        if result['status'] == 'success':
            print(f"   - {crypto_symbol:6s}: {result['saved']:6d}건 저장 (수집: {result['collected']:6d}건)")
        else:
            print(f"   - {crypto_symbol:6s}: 실패 ({result.get('reason', 'unknown')})")
    
    print(f"\n총 저장된 데이터: {total_saved:,}건")
    
    return total_saved, results

def load_checkpoint():
    """체크포인트 로드"""
    checkpoint_file = PROJECT_ROOT / 'collection_checkpoint.json'
    if not checkpoint_file.exists():
        return None
    
    try:
        import json
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('price_history')
    except Exception as e:
        print(f"⚠️ 체크포인트 로드 실패: {e}")
        return None

def get_coins_to_collect(supabase, checkpoint=None):
    """수집할 코인 목록 반환 (체크포인트 기반)"""
    if not checkpoint:
        return COINS_TO_COLLECT
    
    # 체크포인트에서 완료되지 않은 코인만 반환
    coins_to_collect = {}
    for crypto_symbol, binance_symbol in COINS_TO_COLLECT.items():
        coin_info = checkpoint.get('coins', {}).get(crypto_symbol, {})
        status = coin_info.get('status', 'not_started')
        
        # 완료되지 않은 코인만 포함
        if status in ['not_started', 'in_progress', 'error']:
            coins_to_collect[crypto_symbol] = binance_symbol
    
    return coins_to_collect

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='1시간 단위 가격 데이터 수집')
    parser.add_argument('--resume', action='store_true', help='체크포인트에서 재개')
    args = parser.parse_args()
    
    # 2025년 1월 1일 00:00:00 UTC ~ 오늘
    start_date = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_date = datetime.now(timezone.utc)
    
    checkpoint = None
    if args.resume:
        print("=" * 70)
        print("🔄 체크포인트에서 재개")
        print("=" * 70)
        checkpoint = load_checkpoint()
        if checkpoint:
            print("✅ 체크포인트 로드 완료")
            # 체크포인트의 시작 날짜 사용
            start_date = datetime.fromisoformat(checkpoint['start_date'])
            end_date = datetime.fromisoformat(checkpoint['end_date'])
        else:
            print("⚠️ 체크포인트를 찾을 수 없습니다. 처음부터 시작합니다.")
    
    print(f"\n📅 수집 기간: {start_date.strftime('%Y-%m-%d %H:%M:%S')} UTC ~ {end_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    try:
        supabase = get_supabase_client()
        
        # 체크포인트 기반으로 수집할 코인 결정
        if checkpoint:
            original_coins = COINS_TO_COLLECT.copy()
            COINS_TO_COLLECT.clear()
            COINS_TO_COLLECT.update(get_coins_to_collect(supabase, checkpoint))
            print(f"📋 수집 대상 코인: {', '.join(COINS_TO_COLLECT.keys())} ({len(COINS_TO_COLLECT)}개)")
        
        # 데이터 수집
        total_saved, results = collect_price_history_for_coins(supabase, start_date, end_date)
        
        print("\n" + "=" * 70)
        print("✅ 작업 완료")
        print("=" * 70)
        
        # 체크포인트 저장
        print("\n💾 체크포인트 저장 중...")
        from scripts.save_collection_checkpoint import save_checkpoint
        save_checkpoint()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        print("💾 체크포인트 저장 중...")
        try:
            from scripts.save_collection_checkpoint import save_checkpoint
            save_checkpoint()
        except:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

