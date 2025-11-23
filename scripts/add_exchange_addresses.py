#!/usr/bin/env python3
"""
주요 거래소 주소를 whale_address 테이블에 추가
"""

import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 주요 거래소 지갑 주소 (Ethereum)
EXCHANGE_ADDRESSES = [
    # Binance
    {"address": "0x28c6c06298d514db089934071355e5743bf21d60", "name_tag": "Binance 14", "chain_type": "ETH"},
    {"address": "0x21a31ee1afc51d94c2efccaa2092ad1028285549", "name_tag": "Binance 15", "chain_type": "ETH"},
    {"address": "0xdfd5293d8e347dfe59e90efd55b2956a1343963d", "name_tag": "Binance 16", "chain_type": "ETH"},
    {"address": "0x56eddb7aa87536c09ccc2793473599fd21a8b17f", "name_tag": "Binance 17", "chain_type": "ETH"},
    {"address": "0x9696f59e4d72e237be84ffd425dcad154bf96976", "name_tag": "Binance 18", "chain_type": "ETH"},
    
    # Coinbase
    {"address": "0x71660c4005ba85c37ccec55d0c4493e66fe775d3", "name_tag": "Coinbase 1", "chain_type": "ETH"},
    {"address": "0x503828976d22510aad0201ac7ec88293211d23da", "name_tag": "Coinbase 2", "chain_type": "ETH"},
    {"address": "0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740", "name_tag": "Coinbase 3", "chain_type": "ETH"},
    {"address": "0x3cd751e6b0078be393132286c442345e5dc49699", "name_tag": "Coinbase 4", "chain_type": "ETH"},
    {"address": "0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511", "name_tag": "Coinbase 5", "chain_type": "ETH"},
    
    # Kraken
    {"address": "0x2910543af39aba0cd09dbb2d50200b3e800a63d2", "name_tag": "Kraken 1", "chain_type": "ETH"},
    {"address": "0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13", "name_tag": "Kraken 2", "chain_type": "ETH"},
    {"address": "0xe853c56864a2ebe4576a807d26fdc4a0ada51919", "name_tag": "Kraken 3", "chain_type": "ETH"},
    {"address": "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0", "name_tag": "Kraken 4", "chain_type": "ETH"},
    
    # Bitfinex
    {"address": "0x742d35cc6634c0532925a3b844bc454e4438f44e", "name_tag": "Bitfinex 1", "chain_type": "ETH"},
    {"address": "0x876eabf441b2ee5b5b0554fd502a8e0600950cfa", "name_tag": "Bitfinex 2", "chain_type": "ETH"},
    {"address": "0x4fdd92bd67acf0676bfc45ab7168b3996f7b4a3b", "name_tag": "Bitfinex 3", "chain_type": "ETH"},
    
    # Huobi
    {"address": "0x46340b20830761efd32832a74d7169b29feb9758", "name_tag": "Huobi 1", "chain_type": "ETH"},
    {"address": "0x5c985e89dde482efe97ea9f1950ad149eb73829b", "name_tag": "Huobi 2", "chain_type": "ETH"},
    {"address": "0xdc76cd25977e0a5ae17155770273ad58648900d3", "name_tag": "Huobi 3", "chain_type": "ETH"},
    
    # OKX (OKEx)
    {"address": "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b", "name_tag": "OKX 1", "chain_type": "ETH"},
    {"address": "0x236f9f97e0e62388479bf9e5ba4889e46b0273c3", "name_tag": "OKX 2", "chain_type": "ETH"},
    
    # Gate.io
    {"address": "0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c", "name_tag": "Gate.io 1", "chain_type": "ETH"},
    {"address": "0x0d0707963952f2fba59dd06f2b425ace40b492fe", "name_tag": "Gate.io 2", "chain_type": "ETH"},
    
    # Bybit
    {"address": "0xf89d7b9c864f589bbf53a82105107622b35eaa40", "name_tag": "Bybit 1", "chain_type": "ETH"},
    {"address": "0x5dfc870f6980cfbed3d1e80fabbe26c854ce851d", "name_tag": "Bybit 2", "chain_type": "ETH"},
    
    # KuCoin
    {"address": "0x2b5634c42055806a59e9107ed44d43c426e58258", "name_tag": "KuCoin 1", "chain_type": "ETH"},
    {"address": "0x689c56aef474df92d44a1b70850f808488f9769c", "name_tag": "KuCoin 2", "chain_type": "ETH"},
    
    # Crypto.com
    {"address": "0x6262998ced04146fa42253a5c0af90ca02dfd2a3", "name_tag": "Crypto.com 1", "chain_type": "ETH"},
    {"address": "0x7758e507850da48cd47df1fb5f875c23e3340c50", "name_tag": "Crypto.com 2", "chain_type": "ETH"},
    
    # Upbit
    {"address": "0xa826f0c8b2485bc935745d09bc1f20a3f975056d", "name_tag": "Upbit 1", "chain_type": "ETH"},
    {"address": "0x5e032243d507c743b061ef021e2ec7fcc6d3ab89", "name_tag": "Upbit 2", "chain_type": "ETH"},
]

def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    return create_client(supabase_url, supabase_key)

def main():
    print("=" * 80)
    print("🏦 거래소 주소 추가 중...")
    print("=" * 80)
    
    supabase = get_supabase_client()
    
    added_count = 0
    skipped_count = 0
    
    for exchange in EXCHANGE_ADDRESSES:
        try:
            # 중복 체크
            existing = supabase.table('whale_address')\
                .select('address')\
                .eq('address', exchange['address'].lower())\
                .execute()
            
            if existing.data:
                skipped_count += 1
                print(f"⏭️  {exchange['name_tag']:<20} - 이미 존재")
                continue
            
            # 추가 (UUID 생성)
            supabase.table('whale_address').insert({
                'id': str(uuid.uuid4()),
                'address': exchange['address'].lower(),
                'name_tag': exchange['name_tag'],
                'chain_type': exchange['chain_type'],
                'balance': '0',
                'percentage': '0',
                'txn_count': '0'
            }).execute()
            
            added_count += 1
            print(f"✅ {exchange['name_tag']:<20} - 추가 완료")
            
        except Exception as e:
            print(f"❌ {exchange['name_tag']:<20} - 오류: {e}")
    
    print("\n" + "=" * 80)
    print(f"✨ 작업 완료")
    print(f"   - 추가: {added_count}건")
    print(f"   - 건너뜀: {skipped_count}건")
    print("=" * 80)
    
    if added_count > 0:
        print("\n📌 다음 단계:")
        print("   1. 라벨 업데이트 스크립트 재실행:")
        print("      python3 scripts/update_labels_stable.py")
        print("   2. transaction_direction 업데이트:")
        print("      python3 scripts/post_process_rpc_runner.py")

if __name__ == '__main__':
    main()

