#!/usr/bin/env python3
"""
8개 코인 무료 API 수집 스크립트
ETHEREUM, BNB(BSC), USDC, XRP, BITCOIN, DOGECOIN, LITECOIN 거래 기록 수집
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import requests
from dotenv import load_dotenv
from supabase import create_client

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

# Supabase 클라이언트
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# API 키
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
BLOCKCYPHER_TOKEN = os.getenv('BLOCKCYPHER_TOKEN')

# USDC 컨트랙트 주소
USDC_CONTRACT_ADDRESS = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'

# 수집 제한 설정
MAX_ADDRESSES_PER_COIN = None  # 전체 주소 수집
MAX_TXS_PER_ADDRESS = 10000  # 각 주소당 최대 10000개 거래

# 날짜 범위 설정 (2025년 1월 1일 ~ 2025년 10월 31일)
from datetime import datetime
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 10, 31, 23, 59, 59)
START_TIMESTAMP = int(START_DATE.timestamp())
END_TIMESTAMP = int(END_DATE.timestamp())

def get_whale_addresses_by_chain(chain_type: str) -> List[Dict]:
    """whale_address 테이블에서 특정 체인의 주소 가져오기"""
    try:
        response = supabase.table('whale_address').select('*').eq('chain_type', chain_type).execute()
        addresses = response.data
        print(f"  📊 {chain_type} 주소: {len(addresses)}건")
        if MAX_ADDRESSES_PER_COIN:
            return addresses[:MAX_ADDRESSES_PER_COIN]
        return addresses
    except Exception as e:
        print(f"  ❌ {chain_type} 주소 조회 실패: {e}")
        return []

# ============================================================================
# 1. ETHEREUM
# ============================================================================

def fetch_ethereum_transactions(address: str) -> List[Dict]:
    """Ethereum 거래 수집 (Etherscan API)"""
    if not ETHERSCAN_API_KEY:
        return []
    
    url = "https://api.etherscan.io/api"
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': address,
        'startblock': 0,
        'endblock': 99999999,
        'page': 1,
        'offset': MAX_TXS_PER_ADDRESS,
        'sort': 'asc',  # 시간순 정렬
        'apikey': ETHERSCAN_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == '1' and data.get('result'):
            transactions = []
            for tx in data['result']:
                try:
                    # 날짜 필터링
                    timestamp = int(tx.get('timeStamp', 0))
                    if timestamp < START_TIMESTAMP or timestamp > END_TIMESTAMP:
                        continue
                    
                    transactions.append({
                        'tx_hash': tx.get('hash'),
                        'coin_symbol': 'ETH',
                        'chain': 'ethereum',
                        'block_number': int(tx.get('blockNumber', 0)),
                        'block_timestamp': datetime.fromtimestamp(timestamp),
                        'from_address': tx.get('from', '').lower(),
                        'to_address': tx.get('to', '').lower() if tx.get('to') else None,
                        'amount': float(int(tx.get('value', 0)) / 1e18),
                        'gas_used': int(tx.get('gasUsed', 0)),
                        'gas_price': int(tx.get('gasPrice', 0)),
                        'gas_fee': float(int(tx.get('gasUsed', 0)) * int(tx.get('gasPrice', 0)) / 1e18),
                        'transaction_status': 'failed' if tx.get('isError') == '1' else 'success',
                    })
                except:
                    continue
            return transactions
        return []
    except Exception as e:
        print(f"    ⚠️ Ethereum API 오류: {e}")
        return []

# ============================================================================
# 2. BNB (BSC)
# ============================================================================

def fetch_bsc_transactions(address: str) -> List[Dict]:
    """BSC 거래 수집 (BSCScan API, ETHERSCAN_API_KEY 사용)"""
    if not ETHERSCAN_API_KEY:
        return []
    
    url = "https://api.bscscan.com/api"
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': address,
        'startblock': 0,
        'endblock': 99999999,
        'page': 1,
        'offset': MAX_TXS_PER_ADDRESS,
        'sort': 'asc',
        'apikey': ETHERSCAN_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == '1' and data.get('result'):
            transactions = []
            for tx in data['result']:
                try:
                    # 날짜 필터링
                    timestamp = int(tx.get('timeStamp', 0))
                    if timestamp < START_TIMESTAMP or timestamp > END_TIMESTAMP:
                        continue
                    
                    transactions.append({
                        'tx_hash': tx.get('hash'),
                        'coin_symbol': 'BNB',
                        'chain': 'bsc',
                        'block_number': int(tx.get('blockNumber', 0)),
                        'block_timestamp': datetime.fromtimestamp(timestamp),
                        'from_address': tx.get('from', '').lower(),
                        'to_address': tx.get('to', '').lower() if tx.get('to') else None,
                        'amount': float(int(tx.get('value', 0)) / 1e18),
                        'gas_used': int(tx.get('gasUsed', 0)),
                        'gas_price': int(tx.get('gasPrice', 0)),
                        'gas_fee': float(int(tx.get('gasUsed', 0)) * int(tx.get('gasPrice', 0)) / 1e18),
                        'transaction_status': 'failed' if tx.get('isError') == '1' else 'success',
                    })
                except:
                    continue
            return transactions
        return []
    except Exception as e:
        print(f"    ⚠️ BSC API 오류: {e}")
        return []

# ============================================================================
# 3. USDC (ERC-20 Token)
# ============================================================================

def fetch_usdc_transactions(address: str) -> List[Dict]:
    """USDC 거래 수집 (Etherscan Token API)"""
    if not ETHERSCAN_API_KEY:
        return []
    
    url = "https://api.etherscan.io/api"
    params = {
        'module': 'account',
        'action': 'tokentx',
        'contractaddress': USDC_CONTRACT_ADDRESS,
        'address': address,
        'page': 1,
        'offset': MAX_TXS_PER_ADDRESS,
        'sort': 'desc',
        'apikey': ETHERSCAN_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == '1' and data.get('result'):
            transactions = []
            for tx in data['result']:
                try:
                    # 날짜 필터링
                    timestamp = int(tx.get('timeStamp', 0))
                    if timestamp < START_TIMESTAMP or timestamp > END_TIMESTAMP:
                        continue
                    
                    transactions.append({
                        'tx_hash': tx.get('hash'),
                        'coin_symbol': 'USDC',
                        'chain': 'ethereum',
                        'block_number': int(tx.get('blockNumber', 0)),
                        'block_timestamp': datetime.fromtimestamp(timestamp),
                        'from_address': tx.get('from', '').lower(),
                        'to_address': tx.get('to', '').lower() if tx.get('to') else None,
                        'amount': float(int(tx.get('value', 0)) / 1e6),  # USDC는 6 decimals
                        'gas_used': int(tx.get('gasUsed', 0)),
                        'gas_price': int(tx.get('gasPrice', 0)),
                        'gas_fee': float(int(tx.get('gasUsed', 0)) * int(tx.get('gasPrice', 0)) / 1e18),
                        'transaction_status': 'success',
                    })
                except:
                    continue
            return transactions
        return []
    except Exception as e:
        print(f"    ⚠️ USDC API 오류: {e}")
        return []

# ============================================================================
# 4. XRP
# ============================================================================

def fetch_xrp_transactions(address: str) -> List[Dict]:
    """XRP 거래 수집 (XRP Ledger Public API)"""
    url = "https://s1.ripple.com:51234"
    payload = {
        "method": "account_tx",
        "params": [{
            "account": address,
            "ledger_index_min": -1,
            "ledger_index_max": -1,
            "limit": MAX_TXS_PER_ADDRESS
        }]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('result') and data['result'].get('status') == 'success':
            transactions = []
            for item in data['result'].get('transactions', []):
                tx = item.get('tx', {})
                meta = item.get('meta', {})
                
                try:
                    # 날짜 변환 (XRP Ledger epoch: 946684800 = 2000-01-01)
                    timestamp = tx.get('date', 0) + 946684800
                    
                    # 날짜 필터링
                    if timestamp < START_TIMESTAMP or timestamp > END_TIMESTAMP:
                        continue
                    
                    transactions.append({
                        'tx_hash': tx.get('hash'),
                        'coin_symbol': 'XRP',
                        'chain': 'xrp',
                        'block_number': item.get('ledger_index', 0),
                        'block_timestamp': datetime.fromtimestamp(timestamp),
                        'from_address': tx.get('Account', ''),
                        'to_address': tx.get('Destination', ''),
                        'amount': float(tx.get('Amount', 0)) / 1000000 if isinstance(tx.get('Amount'), (int, str)) else 0.0,
                        'gas_used': 0,
                        'gas_price': 0,
                        'gas_fee': float(tx.get('Fee', 0)) / 1000000,
                        'transaction_status': 'success' if meta.get('TransactionResult') == 'tesSUCCESS' else 'failed',
                    })
                except:
                    continue
            return transactions
        return []
    except Exception as e:
        print(f"    ⚠️ XRP API 오류: {e}")
        return []

# ============================================================================
# 5. BITCOIN (Blockstream API - 완전 무료)
# ============================================================================

def fetch_bitcoin_transactions(address: str) -> List[Dict]:
    """Bitcoin 거래 수집 (Blockstream API)"""
    url = f"https://blockstream.info/api/address/{address}/txs"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        txs = response.json()
        
        transactions = []
        for tx in txs[:MAX_TXS_PER_ADDRESS]:
            try:
                # 날짜 필터링
                block_time = tx.get('status', {}).get('block_time', 0)
                if block_time and (block_time < START_TIMESTAMP or block_time > END_TIMESTAMP):
                    continue
                
                # 입력/출력 값 계산
                value_in = sum(vin.get('prevout', {}).get('value', 0) for vin in tx.get('vin', []))
                value_out = sum(vout.get('value', 0) for vout in tx.get('vout', []))
                
                transactions.append({
                    'tx_hash': tx.get('txid'),
                    'coin_symbol': 'BTC',
                    'chain': 'bitcoin',
                    'block_number': tx.get('status', {}).get('block_height', 0),
                    'block_timestamp': datetime.fromtimestamp(tx.get('status', {}).get('block_time', 0)) if tx.get('status', {}).get('block_time') else None,
                    'from_address': address,
                    'to_address': None,
                    'amount': float(value_out / 1e8),
                    'gas_used': 0,
                    'gas_price': 0,
                    'gas_fee': float((value_in - value_out) / 1e8) if value_in > 0 else 0.0,
                    'transaction_status': 'success' if tx.get('status', {}).get('confirmed', False) else 'pending',
                })
            except:
                continue
        
        return transactions
    except Exception as e:
        print(f"    ⚠️ Bitcoin API 오류: {e}")
        return []

# ============================================================================
# 6. DOGECOIN (BlockCypher API)
# ============================================================================

def fetch_dogecoin_transactions(address: str) -> List[Dict]:
    """Dogecoin 거래 수집 (BlockCypher API)"""
    url = f"https://api.blockcypher.com/v1/doge/main/addrs/{address}"
    params = {'limit': MAX_TXS_PER_ADDRESS}
    
    if BLOCKCYPHER_TOKEN:
        params['token'] = BLOCKCYPHER_TOKEN
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        transactions = []
        for tx_ref in data.get('txrefs', []):
            try:
                # 날짜 필터링
                if tx_ref.get('confirmed'):
                    tx_time = datetime.fromisoformat(tx_ref.get('confirmed').replace('Z', '+00:00'))
                    if tx_time < START_DATE or tx_time > END_DATE:
                        continue
                
                transactions.append({
                    'tx_hash': tx_ref.get('tx_hash'),
                    'coin_symbol': 'DOGE',
                    'chain': 'dogecoin',
                    'block_number': tx_ref.get('block_height', 0),
                    'block_timestamp': datetime.fromisoformat(tx_ref.get('confirmed').replace('Z', '+00:00')) if tx_ref.get('confirmed') else None,
                    'from_address': address,
                    'to_address': None,
                    'amount': float(tx_ref.get('value', 0) / 1e8),
                    'gas_used': 0,
                    'gas_price': 0,
                    'gas_fee': 0.0,
                    'transaction_status': 'success' if tx_ref.get('confirmed') else 'pending',
                })
            except:
                continue
        
        return transactions
    except Exception as e:
        print(f"    ⚠️ Dogecoin API 오류: {e}")
        return []

# ============================================================================
# 7. LITECOIN (BlockCypher API)
# ============================================================================

def fetch_litecoin_transactions(address: str) -> List[Dict]:
    """Litecoin 거래 수집 (BlockCypher API)"""
    url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}"
    params = {'limit': MAX_TXS_PER_ADDRESS}
    
    if BLOCKCYPHER_TOKEN:
        params['token'] = BLOCKCYPHER_TOKEN
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        transactions = []
        for tx_ref in data.get('txrefs', []):
            try:
                # 날짜 필터링
                if tx_ref.get('confirmed'):
                    tx_time = datetime.fromisoformat(tx_ref.get('confirmed').replace('Z', '+00:00'))
                    if tx_time < START_DATE or tx_time > END_DATE:
                        continue
                
                transactions.append({
                    'tx_hash': tx_ref.get('tx_hash'),
                    'coin_symbol': 'LTC',
                    'chain': 'litecoin',
                    'block_number': tx_ref.get('block_height', 0),
                    'block_timestamp': datetime.fromisoformat(tx_ref.get('confirmed').replace('Z', '+00:00')) if tx_ref.get('confirmed') else None,
                    'from_address': address,
                    'to_address': None,
                    'amount': float(tx_ref.get('value', 0) / 1e8),
                    'gas_used': 0,
                    'gas_price': 0,
                    'gas_fee': 0.0,
                    'transaction_status': 'success' if tx_ref.get('confirmed') else 'pending',
                })
            except:
                continue
        
        return transactions
    except Exception as e:
        print(f"    ⚠️ Litecoin API 오류: {e}")
        return []

# ============================================================================
# 데이터 저장
# ============================================================================

def save_transactions(transactions: List[Dict]) -> int:
    """거래 기록을 whale_transactions 테이블에 저장"""
    if not transactions:
        return 0
    
    try:
        # 중복 제거 (tx_hash 기준)
        unique_txs = {tx['tx_hash']: tx for tx in transactions}.values()
        unique_list = list(unique_txs)
        
        # datetime을 ISO 형식 문자열로 변환
        for tx in unique_list:
            if tx.get('block_timestamp') and isinstance(tx['block_timestamp'], datetime):
                tx['block_timestamp'] = tx['block_timestamp'].isoformat()
        
        # 배치로 업로드
        batch_size = 100
        uploaded = 0
        
        for i in range(0, len(unique_list), batch_size):
            batch = unique_list[i:i+batch_size]
            try:
                supabase.table('whale_transactions').insert(batch).execute()
                uploaded += len(batch)
            except Exception as e:
                # 중복 오류는 무시 (이미 존재하는 거래)
                if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                    continue
                print(f"      ⚠️ 배치 업로드 실패: {e}")
        
        return uploaded
    except Exception as e:
        print(f"      ❌ 저장 실패: {e}")
        return 0

# ============================================================================
# 메인 실행
# ============================================================================

def collect_coin_transactions(coin_symbol: str, chain_type: str, fetch_func) -> Dict:
    """특정 코인의 거래 수집"""
    print(f"\n{'='*80}")
    print(f"🪙 {coin_symbol} 거래 수집 시작")
    print(f"{'='*80}")
    
    # whale_address에서 주소 가져오기
    whale_addresses = get_whale_addresses_by_chain(chain_type)
    
    if not whale_addresses:
        print(f"  ⚠️ {coin_symbol} 주소가 없습니다.")
        return {'coin': coin_symbol, 'addresses': 0, 'transactions': 0}
    
    all_transactions = []
    
    for idx, whale in enumerate(whale_addresses, 1):
        address = whale['address']
        print(f"  [{idx}/{len(whale_addresses)}] {address[:20]}... 처리 중")
        
        # 거래 수집
        txs = fetch_func(address)
        all_transactions.extend(txs)
        print(f"    ✅ {len(txs)}건 수집 (2025년 1~10월)")
        
        # Rate limit 고려 (Etherscan: 5/sec, BlockCypher: 200/hour)
        if coin_symbol in ['LITECOIN', 'DOGECOIN']:
            time.sleep(18)  # BlockCypher: 200/hour = 1req/18sec
        else:
            time.sleep(0.25)  # Etherscan: 5/sec
    
    # 저장
    print(f"\n  💾 whale_transactions에 저장 중...")
    uploaded = save_transactions(all_transactions)
    print(f"  ✅ {uploaded}건 저장 완료")
    
    return {
        'coin': coin_symbol,
        'addresses': len(whale_addresses),
        'transactions': uploaded
    }

def main():
    """메인 실행"""
    print("\n" + "="*80)
    print("🐋 7개 코인 무료 API 거래 수집 (2025년 1월~10월)")
    print("="*80)
    print(f"📅 수집 기간: {START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')}")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 수집 설정
    COINS_CONFIG = [
        ('ETHEREUM', 'ETH', fetch_ethereum_transactions),
        ('BNB', 'BSC', fetch_bsc_transactions),
        ('USDC', 'USDC', fetch_usdc_transactions),
        ('XRP', 'XRP', fetch_xrp_transactions),
        ('BITCOIN', 'BTC', fetch_bitcoin_transactions),
        ('DOGECOIN', 'DOGE', fetch_dogecoin_transactions),
        ('LITECOIN', 'LTC', fetch_litecoin_transactions),
    ]
    
    results = []
    
    for coin_symbol, chain_type, fetch_func in COINS_CONFIG:
        result = collect_coin_transactions(coin_symbol, chain_type, fetch_func)
        results.append(result)
        
        # 다음 코인 처리 전 대기 (API rate limit 고려)
        time.sleep(2)
    
    # 최종 결과
    print("\n" + "="*80)
    print("📊 수집 완료 요약")
    print("="*80)
    
    total_addresses = 0
    total_transactions = 0
    
    for result in results:
        print(f"  {result['coin']:12} : {result['addresses']:3}개 주소, {result['transactions']:5}건 거래")
        total_addresses += result['addresses']
        total_transactions += result['transactions']
    
    print(f"\n  {'총계':12} : {total_addresses:3}개 주소, {total_transactions:5}건 거래")
    print(f"\n⏰ 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

if __name__ == "__main__":
    main()

