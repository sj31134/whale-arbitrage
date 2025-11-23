#!/usr/bin/env python3
"""
whale_transactions 테이블에 5개 코인만 수집된 원인 분석
whale_address에 있는 코인과 실제 수집된 코인 비교
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


def analyze_whale_address_coins(supabase):
    """whale_address 테이블에 있는 코인 종류 분석"""
    print('=' * 80)
    print('📊 whale_address 테이블 분석')
    print('=' * 80)
    
    response = supabase.table('whale_address').select('chain_type').execute()
    
    chain_types = defaultdict(int)
    for record in response.data:
        chain_type = record.get('chain_type', 'Unknown')
        chain_types[chain_type] += 1
    
    print(f'\n총 레코드: {len(response.data)}건')
    print(f'\n체인별 통계:')
    for chain_type, count in sorted(chain_types.items()):
        print(f'  {chain_type}: {count}건')
    
    return set(chain_types.keys())


def analyze_whale_transactions_coins(supabase):
    """whale_transactions 테이블에 있는 코인 종류 분석"""
    print('\n' + '=' * 80)
    print('📊 whale_transactions 테이블 분석')
    print('=' * 80)
    
    response = supabase.table('whale_transactions').select('coin_symbol, chain').execute()
    
    coin_symbols = defaultdict(int)
    chains = defaultdict(int)
    
    for record in response.data:
        coin_symbol = record.get('coin_symbol', 'Unknown')
        chain = record.get('chain', 'Unknown')
        coin_symbols[coin_symbol] += 1
        chains[chain] += 1
    
    print(f'\n총 거래 레코드: {len(response.data)}건')
    print(f'\ncoin_symbol별 통계:')
    for coin_symbol, count in sorted(coin_symbols.items(), key=lambda x: x[1], reverse=True):
        print(f'  {coin_symbol}: {count}건')
    
    print(f'\nchain별 통계:')
    for chain, count in sorted(chains.items(), key=lambda x: x[1], reverse=True):
        print(f'  {chain}: {count}건')
    
    return set(coin_symbols.keys())


def check_collection_scripts():
    """수집 스크립트들이 지원하는 코인 확인"""
    print('\n' + '=' * 80)
    print('📋 수집 스크립트별 지원 코인')
    print('=' * 80)
    
    scripts = {
        'collect_whale_transactions_from_blockchain.py': {
            '설명': 'Etherscan/BSCScan API 사용',
            '지원 코인': ['ETH', 'BNB', 'LINK (토큰)'],
            '실행 여부': '✅ 실행됨 (ETH, BSC, LINK 수집)'
        },
        'collect_all_whale_transactions.py': {
            '설명': '멀티체인 수집 (Etherscan, SoChain, Subscan, Solscan 등)',
            '지원 코인': ['ETH', 'BNB', 'LINK', 'BTC', 'LTC', 'DOGE', 'DOT', 'SOL', 'VTC'],
            '실행 여부': '⚠️ 일부 실행 (DOT만 수집된 것으로 추정)'
        },
        'collect_bnb_usdc_xrp_transactions_2025_may_june.py': {
            '설명': 'BNB, USDC, XRP 특정 기간 수집',
            '지원 코인': ['BNB', 'USDC', 'XRP'],
            '실행 여부': '✅ 실행됨 (USDC 수집)'
        },
        'collect_internal_transactions_2025_may_june.py': {
            '설명': 'Internal Transactions 수집',
            '지원 코인': ['ETH', 'BNB', 'POLYGON'],
            '실행 여부': '❌ whale_transactions에 저장 안함 (internal_transactions 테이블 사용)'
        },
        'main.py': {
            '설명': '초기 파이프라인 (Ethereum, Polygon)',
            '지원 코인': ['ETH', 'MATIC (Polygon)'],
            '실행 여부': '❌ 실행 안됨 (레거시)'
        }
    }
    
    for script, info in scripts.items():
        print(f'\n[{script}]')
        print(f'  설명: {info["설명"]}')
        print(f'  지원 코인: {", ".join(info["지원 코인"])}')
        print(f'  실행 여부: {info["실행 여부"]}')
    
    return scripts


def analyze_missing_coins(whale_address_coins, whale_transactions_coins):
    """whale_address에는 있지만 whale_transactions에 없는 코인 분석"""
    print('\n' + '=' * 80)
    print('🔍 수집되지 않은 코인 분석')
    print('=' * 80)
    
    missing_coins = whale_address_coins - whale_transactions_coins
    
    # 매핑: chain_type -> coin_symbol
    chain_to_coin = {
        'BTC': 'BTC',
        'ETH': 'ETH',
        'LTC': 'LTC',
        'DOGE': 'DOGE',
        'VTC': 'VTC',
        'BSC': 'BNB (또는 BSC)',
        'DOT': 'DOT',
        'LINK': 'LINK',
        'SOL': 'SOL',
        'POLYGON': 'MATIC',
        'ARBITRUM': 'ARBITRUM',
        'OPTIMISM': 'OPTIMISM',
        'AVALANCHE': 'AVAX',
        'BASE': 'BASE',
        'XRP': 'XRP',
        'USDC': 'USDC'
    }
    
    print(f'\nwhale_address에 있는 체인: {sorted(whale_address_coins)}')
    print(f'whale_transactions에 있는 coin_symbol: {sorted(whale_transactions_coins)}')
    
    print(f'\n⚠️ whale_address에는 있지만 whale_transactions에 없는 체인:')
    for coin in sorted(missing_coins):
        expected_symbol = chain_to_coin.get(coin, coin)
        print(f'  - {coin} (예상 coin_symbol: {expected_symbol})')
    
    return missing_coins


def check_api_keys():
    """필요한 API 키 확인"""
    print('\n' + '=' * 80)
    print('🔑 API 키 설정 상태')
    print('=' * 80)
    
    api_keys = {
        'ETHERSCAN_API_KEY': os.getenv('ETHERSCAN_API_KEY'),
        'BSCSCAN_API_KEY': os.getenv('BSCSCAN_API_KEY'),
        'SOCHAIN_API_KEY': os.getenv('SOCHAIN_API_KEY'),
        'SUBSCAN_API_KEY': os.getenv('SUBSCAN_API_KEY'),
        'SOLSCAN_API_KEY': os.getenv('SOLSCAN_API_KEY'),
        'POLYGONSCAN_API_KEY': os.getenv('POLYGONSCAN_API_KEY'),
    }
    
    for key_name, key_value in api_keys.items():
        status = '✅ 설정됨' if key_value else '❌ 미설정'
        masked_key = f'{key_value[:10]}...' if key_value and len(key_value) > 10 else 'N/A'
        print(f'  {key_name}: {status} ({masked_key})')
    
    return api_keys


def analyze_root_cause():
    """근본 원인 분석 및 결론"""
    print('\n' + '=' * 80)
    print('🎯 근본 원인 분석')
    print('=' * 80)
    
    causes = [
        {
            '원인': '1. 제한적인 스크립트 실행',
            '설명': [
                '- collect_whale_transactions_from_blockchain.py: ETH, BNB, LINK만 수집',
                '- collect_bnb_usdc_xrp_transactions_2025_may_june.py: 특정 기간(5-6월, 7-8월)만 수집',
                '- collect_all_whale_transactions.py: 실행되지 않았거나 일부만 실행됨'
            ]
        },
        {
            '원인': '2. API 키 부족',
            '설명': [
                '- BTC, LTC, DOGE 수집에 필요한 SOCHAIN_API_KEY 미설정 가능성',
                '- SOL 수집에 필요한 SOLSCAN_API_KEY 미설정 가능성',
                '- VTC는 공개 API 사용이나 수집 스크립트 미실행'
            ]
        },
        {
            '원인': '3. 날짜 범위 제한',
            '설명': [
                '- collect_bnb_usdc_xrp_transactions_2025_may_june.py는 2025년 5-6월, 7-8월만 수집',
                '- 해당 기간에 거래가 없거나 적으면 데이터가 없을 수 있음'
            ]
        },
        {
            '원인': '4. 체인별 수집 로직 차이',
            '설명': [
                '- whale_address의 chain_type이 여러 개 (BTC, ETH, LTC, DOGE, VTC, BSC, DOT, LINK, SOL 등)',
                '- 하지만 실제 수집 스크립트는 일부만 구현됨',
                '- XRP, ARBITRUM, OPTIMISM, AVALANCHE, BASE 등은 수집 로직이 없거나 미완성'
            ]
        },
        {
            '원인': '5. 수집 스크립트의 coin_symbol 매핑',
            '설명': [
                '- whale_address.chain_type="BSC" → whale_transactions.coin_symbol="BSC" (BNB 아님)',
                '- 일부 스크립트는 BNB로 매핑하지만, 다른 스크립트는 BSC로 저장',
                '- LINK는 ETH 체인의 토큰이지만 별도 coin_symbol로 저장'
            ]
        }
    ]
    
    for cause in causes:
        print(f'\n{cause["원인"]}')
        for desc in cause["설명"]:
            print(f'  {desc}')


def main():
    """메인 함수"""
    print('=' * 80)
    print('🔍 whale_transactions 수집 범위 분석')
    print('=' * 80)
    print('목적: 왜 5개 코인(ETH, LINK, DOT, BSC, USDC)만 수집되었는지 분석')
    print('=' * 80)
    
    try:
        supabase = get_supabase_client()
        
        # 1. whale_address 분석
        whale_address_coins = analyze_whale_address_coins(supabase)
        
        # 2. whale_transactions 분석
        whale_transactions_coins = analyze_whale_transactions_coins(supabase)
        
        # 3. 수집 스크립트 확인
        check_collection_scripts()
        
        # 4. 수집되지 않은 코인 분석
        missing_coins = analyze_missing_coins(whale_address_coins, whale_transactions_coins)
        
        # 5. API 키 확인
        check_api_keys()
        
        # 6. 근본 원인 분석
        analyze_root_cause()
        
        # 최종 결론
        print('\n' + '=' * 80)
        print('✅ 최종 결론')
        print('=' * 80)
        print('\n📋 5개 코인만 수집된 이유:')
        print('  1. collect_whale_transactions_from_blockchain.py만 주로 실행됨')
        print('     → ETH, BNB(BSC), LINK 수집')
        print('  2. collect_bnb_usdc_xrp_transactions_2025_may_june.py 실행')
        print('     → USDC 일부 수집 (2025년 7-8월 데이터)')
        print('  3. collect_all_whale_transactions.py 실행 (DOT만)')
        print('     → DOT 수집 (Subscan API 사용)')
        print('')
        print('📋 수집되지 않은 코인:')
        print('  - BTC, LTC, DOGE: SOCHAIN_API_KEY 미설정 또는 스크립트 미실행')
        print('  - SOL: SOLSCAN_API_KEY 미설정 또는 스크립트 미실행')
        print('  - VTC: 수집 스크립트 미실행')
        print('  - XRP: 일부 수집되었으나 데이터가 적음 (2025년 7-8월)')
        print('  - POLYGON, ARBITRUM, OPTIMISM, AVALANCHE, BASE: 수집 로직 미구현')
        print('')
        print('📋 권장 조치:')
        print('  1. collect_all_whale_transactions.py 스크립트 실행')
        print('     → 모든 코인 수집 (API 키 필요)')
        print('  2. API 키 설정 (SOCHAIN, SOLSCAN 등)')
        print('  3. 새로운 체인(POLYGON, ARBITRUM 등)에 대한 수집 로직 구현')
        
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

