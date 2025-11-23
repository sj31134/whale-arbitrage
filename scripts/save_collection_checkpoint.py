#!/usr/bin/env python3
"""
데이터 수집 진행 상황을 체크포인트로 저장
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

CHECKPOINT_FILE = PROJECT_ROOT / 'collection_checkpoint.json'

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def get_price_history_checkpoint(supabase):
    """price_history 수집 진행 상황 확인"""
    from collect_price_history_hourly import COINS_TO_COLLECT
    
    START_DATE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    END_DATE = datetime.now(timezone.utc)
    
    checkpoint = {
        'type': 'price_history',
        'start_date': START_DATE.isoformat(),
        'end_date': END_DATE.isoformat(),
        'coins': {}
    }
    
    for crypto_symbol, binance_symbol in COINS_TO_COLLECT.items():
        try:
            crypto_id = supabase.table('cryptocurrencies')\
                .select('id')\
                .eq('symbol', crypto_symbol)\
                .limit(1)\
                .execute()
            
            if not crypto_id.data:
                continue
            
            crypto_id = crypto_id.data[0]['id']
            
            # 최신 데이터 확인
            latest = supabase.table('price_history')\
                .select('timestamp')\
                .eq('crypto_id', crypto_id)\
                .eq('data_source', 'binance')\
                .gte('timestamp', START_DATE.isoformat())\
                .lte('timestamp', END_DATE.isoformat())\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            if latest.data:
                latest_timestamp = latest.data[0]['timestamp']
                checkpoint['coins'][crypto_symbol] = {
                    'status': 'in_progress',
                    'latest_timestamp': latest_timestamp,
                    'binance_symbol': binance_symbol
                }
            else:
                checkpoint['coins'][crypto_symbol] = {
                    'status': 'not_started',
                    'latest_timestamp': None,
                    'binance_symbol': binance_symbol
                }
                
        except Exception as e:
            checkpoint['coins'][crypto_symbol] = {
                'status': 'error',
                'error': str(e),
                'binance_symbol': binance_symbol
            }
    
    return checkpoint

def get_btc_whale_checkpoint(supabase):
    """BTC 고래 거래 수집 진행 상황 확인"""
    START_DATE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    END_DATE = datetime.now(timezone.utc)
    
    checkpoint = {
        'type': 'btc_whale_transactions',
        'start_date': START_DATE.isoformat(),
        'end_date': END_DATE.isoformat(),
        'addresses': {}
    }
    
    try:
        # BTC 고래 주소 조회
        addresses = supabase.table('whale_address')\
            .select('*')\
            .eq('chain_type', 'BTC')\
            .execute()
        
        for addr_info in addresses.data:
            address = addr_info.get('address')
            if not address:
                continue
            
            # 해당 주소의 최신 거래 확인
            latest = supabase.table('whale_transactions')\
                .select('block_timestamp')\
                .eq('coin_symbol', 'BTC')\
                .eq('from_address', address)\
                .gte('block_timestamp', START_DATE.isoformat())\
                .lte('block_timestamp', END_DATE.isoformat())\
                .order('block_timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            if latest.data:
                latest_timestamp = latest.data[0]['block_timestamp']
                checkpoint['addresses'][address] = {
                    'status': 'in_progress',
                    'latest_timestamp': latest_timestamp,
                    'name_tag': addr_info.get('name_tag', '')
                }
            else:
                checkpoint['addresses'][address] = {
                    'status': 'not_started',
                    'latest_timestamp': None,
                    'name_tag': addr_info.get('name_tag', '')
                }
                
    except Exception as e:
        checkpoint['error'] = str(e)
    
    return checkpoint

def get_bsc_whale_checkpoint(supabase):
    """BSC 고래 거래 수집 진행 상황 확인"""
    START_DATE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    END_DATE = datetime.now(timezone.utc)
    
    checkpoint = {
        'type': 'bsc_whale_transactions',
        'start_date': START_DATE.isoformat(),
        'end_date': END_DATE.isoformat(),
        'addresses': {},
        'last_run': None,
        'total_collected': 0,
        'total_scraped': 0
    }
    
    # BSC 하이브리드 체크포인트 파일 확인
    bsc_checkpoint_file = PROJECT_ROOT / 'checkpoints' / 'bsc_hybrid_checkpoint.json'
    if bsc_checkpoint_file.exists():
        try:
            with open(bsc_checkpoint_file, 'r', encoding='utf-8') as f:
                bsc_data = json.load(f)
                checkpoint['last_run'] = bsc_data.get('last_run')
                checkpoint['total_collected'] = bsc_data.get('total_collected', 0)
                checkpoint['total_scraped'] = bsc_data.get('total_scraped', 0)
                checkpoint['processed_addresses'] = bsc_data.get('processed_addresses', [])
        except Exception as e:
            print(f"⚠️ BSC 체크포인트 로드 실패: {e}")
    
    try:
        # BSC 고래 주소 조회
        addresses = supabase.table('whale_address')\
            .select('*')\
            .eq('chain_type', 'BSC')\
            .execute()
        
        for addr_info in addresses.data:
            address = addr_info.get('address')
            if not address:
                continue
            
            # 해당 주소의 최신 거래 확인
            latest = supabase.table('whale_transactions')\
                .select('block_timestamp')\
                .eq('chain', 'bsc')\
                .eq('from_address', address)\
                .gte('block_timestamp', START_DATE.isoformat())\
                .lte('block_timestamp', END_DATE.isoformat())\
                .order('block_timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            if latest.data:
                latest_timestamp = latest.data[0]['block_timestamp']
                checkpoint['addresses'][address] = {
                    'status': 'in_progress',
                    'latest_timestamp': latest_timestamp,
                    'name_tag': addr_info.get('name_tag', '')
                }
            else:
                checkpoint['addresses'][address] = {
                    'status': 'not_started',
                    'latest_timestamp': None,
                    'name_tag': addr_info.get('name_tag', '')
                }
                
    except Exception as e:
        checkpoint['error'] = str(e)
    
    return checkpoint

def save_checkpoint():
    """체크포인트 저장"""
    try:
        supabase = get_supabase_client()
        
        print("=" * 70)
        print("💾 데이터 수집 체크포인트 저장")
        print("=" * 70)
        
        # price_history 체크포인트
        print("\n📊 price_history 진행 상황 확인 중...")
        price_checkpoint = get_price_history_checkpoint(supabase)
        
        # BTC 고래 거래 체크포인트
        print("🐋 BTC 고래 거래 진행 상황 확인 중...")
        btc_checkpoint = get_btc_whale_checkpoint(supabase)
        
        # BSC 고래 거래 체크포인트
        print("🟡 BSC 고래 거래 진행 상황 확인 중...")
        bsc_checkpoint = get_bsc_whale_checkpoint(supabase)
        
        # 체크포인트 저장
        checkpoint_data = {
            'saved_at': datetime.now(timezone.utc).isoformat(),
            'price_history': price_checkpoint,
            'btc_whale_transactions': btc_checkpoint,
            'bsc_whale_transactions': bsc_checkpoint
        }
        
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 체크포인트 저장 완료: {CHECKPOINT_FILE}")
        
        # 요약 출력
        print("\n📋 진행 상황 요약:")
        
        # price_history 요약
        completed = sum(1 for c in price_checkpoint['coins'].values() if c.get('status') == 'in_progress')
        total = len(price_checkpoint['coins'])
        print(f"   price_history: {completed}/{total} 코인 진행 중")
        
        # BTC 고래 거래 요약
        completed = sum(1 for a in btc_checkpoint['addresses'].values() if a.get('status') == 'in_progress')
        total = len(btc_checkpoint['addresses'])
        print(f"   BTC 고래 거래: {completed}/{total} 주소 진행 중")
        
        # BSC 고래 거래 요약
        completed = sum(1 for a in bsc_checkpoint['addresses'].values() if a.get('status') == 'in_progress')
        total = len(bsc_checkpoint['addresses'])
        print(f"   BSC 고래 거래: {completed}/{total} 주소 진행 중")
        
        return checkpoint_data
        
    except Exception as e:
        print(f"\n❌ 체크포인트 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_checkpoint():
    """체크포인트 로드"""
    if not CHECKPOINT_FILE.exists():
        return None
    
    try:
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 체크포인트 로드 실패: {e}")
        return None

def main():
    """메인 함수"""
    checkpoint = save_checkpoint()
    
    if checkpoint:
        print("\n" + "=" * 70)
        print("✅ 체크포인트 저장 완료")
        print("=" * 70)
        print(f"\n다음에 재개하려면:")
        print(f"  python3 collect_price_history_hourly.py --resume")
        print(f"  python3 collect_btc_whale_transactions.py --resume")

if __name__ == '__main__':
    main()

