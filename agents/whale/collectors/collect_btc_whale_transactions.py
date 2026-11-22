#!/usr/bin/env python3
"""
BTC 고래 거래 데이터 보충 수집
whale_address 테이블의 BTC 주소에 대한 거래 기록을 Blockstream API로 수집
기간: 2025년 1월 1일 ~ 오늘
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# Blockstream API 기본 URL (무료, 제한 없음)
BLOCKSTREAM_API_BASE = "https://blockstream.info/api"

# 날짜 범위 설정 (2025년 1월 1일 ~ 오늘)
START_DATE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
END_DATE = datetime.now(timezone.utc)
START_TIMESTAMP = int(START_DATE.timestamp())
END_TIMESTAMP = int(END_DATE.timestamp())

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def get_btc_whale_addresses(supabase) -> List[Dict]:
    """whale_address 테이블에서 BTC 주소 가져오기"""
    try:
        response = supabase.table('whale_address')\
            .select('*')\
            .eq('chain_type', 'BTC')\
            .execute()
        
        addresses = response.data
        print(f"✅ BTC 고래 주소 조회 완료: {len(addresses)}개")
        return addresses
    except Exception as e:
        print(f"❌ BTC 고래 주소 조회 실패: {e}")
        return []

def fetch_bitcoin_transactions(address: str) -> List[Dict]:
    """
    Bitcoin 거래 수집 (Blockstream API)
    
    Parameters:
    -----------
    address : str
        Bitcoin 주소
    
    Returns:
    --------
    List[Dict] : 거래 기록 리스트
    """
    url = f"{BLOCKSTREAM_API_BASE}/address/{address}/txs"
    
    all_transactions = []
    page = 0
    last_txid = None
    
    while True:
        try:
            # 페이지네이션 지원 (25개씩)
            params = {}
            if page > 0 and last_txid:
                params['last_seen_txid'] = last_txid
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            txs = response.json()
            
            if not txs or len(txs) == 0:
                break
            
            for tx in txs:
                try:
                    # 날짜 필터링
                    block_time = tx.get('status', {}).get('block_time', 0)
                    if not block_time:
                        continue
                    
                    if block_time < START_TIMESTAMP or block_time > END_TIMESTAMP:
                        # 날짜 범위를 벗어나면 더 이상 조회하지 않음 (최신순이므로)
                        if block_time < START_TIMESTAMP:
                            return all_transactions
                        continue
                    
                    # 입력/출력 값 계산
                    value_in = sum(vin.get('prevout', {}).get('value', 0) for vin in tx.get('vin', []))
                    value_out = sum(vout.get('value', 0) for vout in tx.get('vout', []))
                    
                    # 주소 관련 정보 추출
                    from_addresses = set()
                    to_addresses = set()
                    
                    for vin in tx.get('vin', []):
                        if 'prevout' in vin and 'scriptpubkey_address' in vin['prevout']:
                            from_addresses.add(vin['prevout']['scriptpubkey_address'])
                    
                    for vout in tx.get('vout', []):
                        if 'scriptpubkey_address' in vout:
                            to_addresses.add(vout['scriptpubkey_address'])
                    
                    # UTC 타임존 명시
                    block_timestamp = datetime.fromtimestamp(block_time, tz=timezone.utc)
                    
                    transaction = {
                        'tx_hash': tx.get('txid'),
                        'coin_symbol': 'BTC',
                        'chain': 'bitcoin',
                        'block_number': tx.get('status', {}).get('block_height', 0),
                        'block_timestamp': block_timestamp.isoformat(),  # UTC 명시
                        'from_address': address,  # 조회한 주소
                        'to_address': None,  # Bitcoin은 UTXO 모델이라 단순화
                        'amount': float(value_out / 1e8),  # Satoshi를 BTC로 변환
                        'gas_used': 0,
                        'gas_price': 0,
                        'gas_fee_eth': float((value_in - value_out) / 1e8) if value_in > 0 else 0.0,
                        'gas_fee_usd': None,  # 나중에 계산
                        'transaction_status': 'SUCCESS' if tx.get('status', {}).get('confirmed', False) else 'PENDING',
                        'is_whale': True,  # whale_address에 있는 주소이므로 모두 고래
                        'whale_category': None,  # 나중에 amount_usd로 계산
                        'amount_usd': None,  # 나중에 가격 조회
                    }
                    
                    all_transactions.append(transaction)
                    
                except Exception as e:
                    print(f"      ⚠️ 거래 파싱 실패: {e}")
                    continue
            
            # 다음 페이지가 있는지 확인
            if len(txs) < 25:  # Blockstream API는 25개씩 반환
                break
            
            last_txid = txs[-1].get('txid')
            page += 1
            
            # API rate limit 방지
            time.sleep(0.1)
            
        except Exception as e:
            print(f"    ⚠️ Bitcoin API 오류: {e}")
            break
    
    return all_transactions

def save_to_whale_transactions(supabase, transactions: List[Dict]) -> int:
    """whale_transactions 테이블에 저장"""
    if not transactions:
        return 0
    
    saved_count = 0
    batch_size = 100
    
    for i in range(0, len(transactions), batch_size):
        batch = transactions[i:i + batch_size]
        try:
            # upsert 사용 (tx_hash가 PK이므로 중복 자동 처리)
            response = supabase.table('whale_transactions').upsert(batch).execute()
            saved_count += len(batch)
            
            if (i + batch_size) % 500 == 0:
                print(f"      💾 {saved_count}/{len(transactions)}건 저장 중...")
                
        except Exception as e:
            print(f"⚠️ whale_transactions 저장 실패 (배치 {i//batch_size + 1}): {e}")
            # 개별 저장 시도
            for record in batch:
                try:
                    supabase.table('whale_transactions').upsert([record]).execute()
                    saved_count += 1
                except:
                    pass
    
    return saved_count

def collect_btc_whale_transactions(supabase, addresses=None):
    """BTC 고래 거래 데이터 수집"""
    print("=" * 70)
    print("🐋 BTC 고래 거래 데이터 수집")
    print("=" * 70)
    print(f"\n수집 기간: {START_DATE.strftime('%Y-%m-%d %H:%M:%S')} UTC ~ {END_DATE.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"API: Blockstream API (무료)")
    print("=" * 70)
    
    # BTC 고래 주소 조회
    if addresses is None:
        addresses = get_btc_whale_addresses(supabase)
    
    if not addresses:
        print("❌ BTC 고래 주소를 찾을 수 없습니다.")
        return 0
    
    total_transactions = 0
    total_saved = 0
    
    for i, addr_info in enumerate(addresses, 1):
        address = addr_info.get('address')
        name_tag = addr_info.get('name_tag', '')
        
        if not address:
            continue
        
        print(f"\n[{i}/{len(addresses)}] {address[:20]}... 처리 중...")
        if name_tag:
            print(f"    라벨: {name_tag}")
        
        # 거래 조회
        try:
            transactions = fetch_bitcoin_transactions(address)
            
            if not transactions:
                print(f"    ⚠️ 거래 기록 없음")
                continue
            
            print(f"    ✅ {len(transactions)}건의 거래 조회 완료")
            total_transactions += len(transactions)
            
            # 저장
            saved = save_to_whale_transactions(supabase, transactions)
            total_saved += saved
            print(f"    💾 {saved}건 저장 완료")
            
        except Exception as e:
            print(f"    ❌ 오류 발생: {e}")
            continue
        
        # API rate limit 방지
        time.sleep(0.2)
    
    # 결과 요약
    print("\n" + "=" * 70)
    print("✅ 수집 완료")
    print("=" * 70)
    print(f"\n📊 수집 결과:")
    print(f"   - 처리한 주소: {len(addresses)}개")
    print(f"   - 조회한 거래: {total_transactions:,}건")
    print(f"   - 저장한 거래: {total_saved:,}건")
    
    return total_saved

def load_checkpoint():
    """체크포인트 로드"""
    checkpoint_file = PROJECT_ROOT / 'collection_checkpoint.json'
    if not checkpoint_file.exists():
        return None
    
    try:
        import json
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('btc_whale_transactions')
    except Exception as e:
        print(f"⚠️ 체크포인트 로드 실패: {e}")
        return None

def get_addresses_to_collect(supabase, checkpoint=None):
    """수집할 주소 목록 반환 (체크포인트 기반)"""
    addresses = get_btc_whale_addresses(supabase)
    
    if not checkpoint:
        return addresses
    
    # 체크포인트에서 완료되지 않은 주소만 반환
    addresses_to_collect = []
    for addr_info in addresses:
        address = addr_info.get('address')
        if not address:
            continue
        
        addr_checkpoint = checkpoint.get('addresses', {}).get(address, {})
        status = addr_checkpoint.get('status', 'not_started')
        
        # 완료되지 않은 주소만 포함
        if status in ['not_started', 'in_progress', 'error']:
            addresses_to_collect.append(addr_info)
    
    return addresses_to_collect

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BTC 고래 거래 데이터 수집')
    parser.add_argument('--resume', action='store_true', help='체크포인트에서 재개')
    args = parser.parse_args()
    
    try:
        supabase = get_supabase_client()
        
        checkpoint = None
        if args.resume:
            print("=" * 70)
            print("🔄 체크포인트에서 재개")
            print("=" * 70)
            checkpoint = load_checkpoint()
            if checkpoint:
                print("✅ 체크포인트 로드 완료")
            else:
                print("⚠️ 체크포인트를 찾을 수 없습니다. 처음부터 시작합니다.")
        
        # 체크포인트 기반으로 수집할 주소 결정
        if checkpoint:
            addresses = get_addresses_to_collect(supabase, checkpoint)
            print(f"📋 수집 대상 주소: {len(addresses)}개")
        else:
            addresses = get_btc_whale_addresses(supabase)
        
        # BTC 고래 거래 데이터 수집
        total_saved = collect_btc_whale_transactions(supabase, addresses)
        
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

