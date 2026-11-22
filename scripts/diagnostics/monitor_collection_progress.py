#!/usr/bin/env python3
"""
데이터 수집 진행률 모니터링 스크립트
10분마다 현재 진행 상황을 확인하여 출력
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 검증 기간
START_DATE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
END_DATE = datetime.now(timezone.utc)

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def check_price_history_progress(supabase):
    """price_history 진행률 확인"""
    try:
        # 전체 기간 계산
        total_days = (END_DATE.date() - START_DATE.date()).days + 1
        total_hours = total_days * 24
        
        # 주요 코인 목록
        target_coins = ['BTC', 'ETH', 'BNB', 'USDC', 'XRP', 'LTC', 'DOGE', 'LINK', 'SOL', 'DOT']
        
        # cryptocurrencies 테이블에서 코인 정보 조회
        crypto_response = supabase.table('cryptocurrencies')\
            .select('id, symbol')\
            .in_('symbol', target_coins)\
            .execute()
        
        crypto_map = {c['symbol']: c['id'] for c in crypto_response.data}
        
        total_expected = len(target_coins) * total_hours
        total_collected = 0
        coin_progress = {}
        
        for symbol, crypto_id in crypto_map.items():
            try:
                response = supabase.table('price_history')\
                    .select('timestamp', count='exact')\
                    .eq('crypto_id', crypto_id)\
                    .gte('timestamp', START_DATE.isoformat())\
                    .lte('timestamp', END_DATE.isoformat())\
                    .execute()
                
                count = response.count if hasattr(response, 'count') else len(response.data) if response.data else 0
                total_collected += count
                
                progress_pct = (count / total_hours * 100) if total_hours > 0 else 0
                coin_progress[symbol] = {
                    'count': count,
                    'expected': total_hours,
                    'progress': progress_pct
                }
                
            except Exception as e:
                coin_progress[symbol] = {'error': str(e)}
        
        overall_progress = (total_collected / total_expected * 100) if total_expected > 0 else 0
        
        return {
            'total_collected': total_collected,
            'total_expected': total_expected,
            'overall_progress': overall_progress,
            'coin_progress': coin_progress
        }
        
    except Exception as e:
        return {'error': str(e)}

def check_whale_transactions_progress(supabase):
    """whale_transactions 진행률 확인"""
    try:
        # BTC 거래 수 확인
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .eq('coin_symbol', 'BTC')\
            .gte('block_timestamp', START_DATE.isoformat())\
            .lte('block_timestamp', END_DATE.isoformat())\
            .execute()
        
        btc_count = response.count if hasattr(response, 'count') else len(response.data) if response.data else 0
        
        # ETH 거래 수 확인
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .eq('coin_symbol', 'ETH')\
            .gte('block_timestamp', START_DATE.isoformat())\
            .lte('block_timestamp', END_DATE.isoformat())\
            .execute()
        
        eth_count = response.count if hasattr(response, 'count') else len(response.data) if response.data else 0
        
        # BSC 거래 수 확인
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .eq('chain', 'bsc')\
            .gte('block_timestamp', START_DATE.isoformat())\
            .lte('block_timestamp', END_DATE.isoformat())\
            .execute()
        
        bsc_count = response.count if hasattr(response, 'count') else len(response.data) if response.data else 0
        
        return {
            'BTC': btc_count,
            'ETH': eth_count,
            'BSC': bsc_count,
            'total': btc_count + eth_count + bsc_count
        }
        
    except Exception as e:
        return {'error': str(e)}

def print_progress_report(price_progress, whale_progress):
    """진행률 리포트 출력"""
    current_time = datetime.now(timezone.utc)
    print("\n" + "=" * 70)
    print(f"📊 데이터 수집 진행률 리포트")
    print(f"⏰ {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)
    
    # price_history 진행률
    if 'error' not in price_progress:
        print(f"\n📈 price_history 진행률:")
        print(f"   전체: {price_progress['total_collected']:,} / {price_progress['total_expected']:,}건 ({price_progress['overall_progress']:.1f}%)")
        print(f"\n   코인별 상세:")
        for symbol, info in sorted(price_progress['coin_progress'].items()):
            if 'error' not in info:
                bar_length = int(info['progress'] / 2)
                bar = '█' * bar_length + '░' * (50 - bar_length)
                print(f"   {symbol:6s}: {info['count']:6,} / {info['expected']:6,}건 ({info['progress']:5.1f}%) {bar}")
            else:
                print(f"   {symbol:6s}: 오류 - {info['error']}")
    else:
        print(f"\n❌ price_history 진행률 확인 실패: {price_progress['error']}")
    
    # whale_transactions 진행률
    if 'error' not in whale_progress:
        print(f"\n🐋 whale_transactions 진행률:")
        print(f"   BTC: {whale_progress.get('BTC', 0):,}건")
        print(f"   ETH: {whale_progress.get('ETH', 0):,}건")
        print(f"   BSC: {whale_progress.get('BSC', 0):,}건")
        print(f"   총계: {whale_progress.get('total', 0):,}건")
    else:
        print(f"\n❌ whale_transactions 진행률 확인 실패: {whale_progress['error']}")
    
    print("=" * 70)

def main():
    """메인 함수 - 10분마다 진행률 확인"""
    print("=" * 70)
    print("📊 데이터 수집 진행률 모니터링 시작")
    print("=" * 70)
    print(f"모니터링 기간: {START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')}")
    print(f"확인 주기: 10분")
    print("=" * 70)
    
    try:
        supabase = get_supabase_client()
        
        iteration = 0
        while True:
            iteration += 1
            print(f"\n🔄 {iteration}번째 확인 중...")
            
            # 진행률 확인
            price_progress = check_price_history_progress(supabase)
            whale_progress = check_whale_transactions_progress(supabase)
            
            # 리포트 출력
            print_progress_report(price_progress, whale_progress)
            
            # 10분 대기
            print(f"\n⏳ 다음 확인까지 10분 대기 중... (Ctrl+C로 종료)")
            time.sleep(600)  # 10분 = 600초
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 모니터링이 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

