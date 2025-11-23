#!/usr/bin/env python3
"""
8개 코인(USDC, XRP, BSC, BITCOIN, ETHEREUM, LITECOIN, DOGECOIN, VERTCOIN) 준비 상태 확인
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)


def check_cryptocurrencies_table(supabase):
    """cryptocurrencies 테이블 확인"""
    print('=' * 80)
    print('1. cryptocurrencies 테이블 확인')
    print('=' * 80)
    
    response = supabase.table('cryptocurrencies').select('*').execute()
    
    target_coins = ['USDC', 'XRP', 'BNB', 'BTC', 'ETH', 'LTC', 'DOGE', 'VTC']
    
    existing_symbols = {r.get('symbol', '').upper() for r in response.data}
    
    print(f'\n총 레코드: {len(response.data)}건')
    print(f'\n목표 코인 (8개): {", ".join(target_coins)}')
    print(f'\n확인 결과:')
    
    for coin in target_coins:
        exists = coin in existing_symbols or coin == 'BNB' and 'BSC' in existing_symbols
        status = '✅' if exists else '❌'
        print(f'  {status} {coin}: {"있음" if exists else "없음"}')
    
    missing = [c for c in target_coins if c not in existing_symbols and not (c == 'BNB' and 'BSC' in existing_symbols)]
    
    return existing_symbols, missing


def check_whale_address_table(supabase):
    """whale_address 테이블 확인"""
    print('\n' + '=' * 80)
    print('2. whale_address 테이블 확인')
    print('=' * 80)
    
    response = supabase.table('whale_address').select('chain_type').execute()
    
    chain_types = defaultdict(int)
    for record in response.data:
        chain_type = record.get('chain_type', 'Unknown')
        chain_types[chain_type] += 1
    
    # chain_type -> coin_symbol 매핑
    chain_to_coin = {
        'BTC': 'BITCOIN',
        'ETH': 'ETHEREUM',
        'LTC': 'LITECOIN',
        'DOGE': 'DOGECOIN',
        'VTC': 'VERTCOIN',
        'BSC': 'BNB',
        'USDC': 'USDC',
        'XRP': 'XRP'
    }
    
    target_chains = ['BTC', 'ETH', 'LTC', 'DOGE', 'VTC', 'BSC', 'USDC', 'XRP']
    
    print(f'\n총 레코드: {len(response.data)}건')
    print(f'\n확인 결과:')
    
    existing_chains = set()
    for chain in target_chains:
        exists = chain in chain_types
        status = '✅' if exists else '❌'
        coin_name = chain_to_coin.get(chain, chain)
        count = chain_types.get(chain, 0)
        print(f'  {status} {chain} ({coin_name}): {count}건')
        if exists:
            existing_chains.add(chain)
    
    missing = [c for c in target_chains if c not in chain_types]
    
    return existing_chains, missing


def check_free_api_availability():
    """무료 API 사용 가능 여부 확인"""
    print('\n' + '=' * 80)
    print('3. 무료 API 사용 가능 여부')
    print('=' * 80)
    
    api_options = {
        'ETHEREUM': {
            'API': 'Etherscan API (무료)',
            'URL': 'https://api.etherscan.io/api',
            '상태': '✅ 무료 (API 키 필요)',
            'API 키': os.getenv('ETHERSCAN_API_KEY', 'N/A')[:20] + '...'
        },
        'BNB (BSC)': {
            'API': 'BSCScan API (무료)',
            'URL': 'https://api.bscscan.com/api',
            '상태': '✅ 무료 (API 키 필요)',
            'API 키': os.getenv('BSCSCAN_API_KEY', 'N/A')
        },
        'USDC': {
            'API': 'Etherscan API (ERC-20)',
            'URL': 'https://api.etherscan.io/api',
            '상태': '✅ 무료 (USDC는 여러 체인에 존재)',
            '참고': 'Ethereum, BSC, Polygon, Arbitrum 등'
        },
        'XRP': {
            'API': 'XRP Ledger Public API (무료)',
            'URL': 'https://xrplcluster.com',
            '상태': '✅ 무료 (API 키 불필요)',
            '참고': 'JSON-RPC 사용'
        },
        'BITCOIN': {
            'API': 'Blockchain.info API (무료)',
            'URL': 'https://blockchain.info/rawaddr/{address}',
            '상태': '✅ 무료 (제한: 1초당 1요청)',
            '대안': 'BlockCypher (무료 티어: 200요청/시간)'
        },
        'LITECOIN': {
            'API': 'BlockCypher API (무료)',
            'URL': 'https://api.blockcypher.com/v1/ltc/main',
            '상태': '⚠️ 무료 티어 제한 (200요청/시간)',
            '대안': 'Litecoin Explorer (제한적)'
        },
        'DOGECOIN': {
            'API': 'BlockCypher API (무료)',
            'URL': 'https://api.blockcypher.com/v1/doge/main',
            '상태': '⚠️ 무료 티어 제한 (200요청/시간)',
            '대안': 'Dogechain.info API'
        },
        'VERTCOIN': {
            'API': 'Vertcoin Explorer',
            'URL': 'https://insight.vertcoin.org/api',
            '상태': '❌ 공개 API 제한적',
            '참고': 'VTC는 수집이 어려울 수 있음'
        }
    }
    
    for coin, info in api_options.items():
        print(f'\n[{coin}]')
        for key, value in info.items():
            print(f'  {key}: {value}')
    
    return api_options


def main():
    """메인 함수"""
    print('=' * 80)
    print('8개 코인 준비 상태 확인')
    print('=' * 80)
    print('목표: USDC, XRP, BSC(BNB), BITCOIN, ETHEREUM, LITECOIN, DOGECOIN, VERTCOIN')
    print('=' * 80)
    
    try:
        supabase = get_supabase_client()
        
        # 1. cryptocurrencies 테이블 확인
        existing_symbols, missing_crypto = check_cryptocurrencies_table(supabase)
        
        # 2. whale_address 테이블 확인
        existing_chains, missing_whale = check_whale_address_table(supabase)
        
        # 3. 무료 API 확인
        api_options = check_free_api_availability()
        
        # 4. 최종 요약
        print('\n' + '=' * 80)
        print('4. 최종 요약')
        print('=' * 80)
        
        print('\n[cryptocurrencies 테이블]')
        if missing_crypto:
            print(f'  ❌ 없는 코인: {", ".join(missing_crypto)}')
        else:
            print(f'  ✅ 8개 코인 모두 있음')
        
        print('\n[whale_address 테이블]')
        if missing_whale:
            print(f'  ❌ 없는 체인: {", ".join(missing_whale)}')
        else:
            print(f'  ✅ 8개 코인 주소 모두 있음')
        
        print('\n[무료 API 사용 가능]')
        print(f'  ✅ ETHEREUM, BNB, USDC, XRP: 무료 API 사용 가능')
        print(f'  ⚠️ BITCOIN, LITECOIN, DOGECOIN: 무료이나 제한 있음')
        print(f'  ❌ VERTCOIN: 공개 API 제한적')
        
    except KeyboardInterrupt:
        print('\n\n⚠️  사용자에 의해 중단되었습니다.')
        sys.exit(1)
    except Exception as e:
        print(f'\n❌ 오류 발생: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

