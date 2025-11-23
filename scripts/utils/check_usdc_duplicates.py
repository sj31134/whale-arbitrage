#!/usr/bin/env python3
"""
USDC whale_address 테이블의 중복 데이터 확인
Ethereum 네트워크 주소가 다른 네트워크에도 중복으로 들어갔는지 확인
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print('=' * 80)
print('🔍 USDC whale_address 중복 데이터 확인')
print('=' * 80)

# USDC 관련 chain_type 목록
usdc_chain_types = ['ETH', 'BSC', 'POLYGON', 'ARBITRUM', 'OPTIMISM', 'AVALANCHE', 'SOL', 'BASE']

# 1. 각 chain_type별 데이터 수 확인
print('\n[1단계] 체인별 데이터 수 확인')
print('-' * 80)
chain_counts = {}
for chain_type in usdc_chain_types:
    response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', chain_type).execute()
    count = response.count if hasattr(response, 'count') else len(response.data)
    chain_counts[chain_type] = count
    print(f'  {chain_type}: {count}건')

# 2. Ethereum 주소 추출
print('\n[2단계] Ethereum 네트워크 주소 추출')
print('-' * 80)
eth_response = supabase.table('whale_address').select('address, id, name_tag').eq('chain_type', 'ETH').execute()
eth_addresses = {}
for record in eth_response.data:
    addr = record.get('address', '').lower().strip()
    if addr:
        eth_addresses[addr] = {
            'id': record.get('id'),
            'name_tag': record.get('name_tag')
        }

print(f'  ✅ Ethereum 주소: {len(eth_addresses)}개')

# 3. 다른 네트워크에서 Ethereum 주소와 중복되는지 확인
print('\n[3단계] 다른 네트워크에서 Ethereum 주소 중복 확인')
print('-' * 80)

duplicates_found = defaultdict(list)

for chain_type in usdc_chain_types:
    if chain_type == 'ETH':
        continue
    
    response = supabase.table('whale_address').select('address, id, name_tag, chain_type').eq('chain_type', chain_type).execute()
    
    for record in response.data:
        addr = record.get('address', '').lower().strip()
        if addr in eth_addresses:
            duplicates_found[addr].append({
                'chain_type': chain_type,
                'id': record.get('id'),
                'name_tag': record.get('name_tag'),
                'eth_id': eth_addresses[addr]['id'],
                'eth_name_tag': eth_addresses[addr]['name_tag']
            })

# 4. 중복 결과 출력
print(f'\n  🔴 중복된 주소 수: {len(duplicates_found)}개')
print('-' * 80)

if duplicates_found:
    print('\n[4단계] 중복 상세 내역')
    print('=' * 80)
    
    # 체인별 중복 통계
    chain_duplicate_count = defaultdict(int)
    for addr, chains in duplicates_found.items():
        for chain_info in chains:
            chain_duplicate_count[chain_info['chain_type']] += 1
    
    print('\n  📊 체인별 중복 건수:')
    for chain, count in sorted(chain_duplicate_count.items()):
        print(f'    - {chain}: {count}건')
    
    # 상위 20개 중복 주소 샘플 출력
    print('\n  📋 중복 주소 샘플 (상위 20개):')
    print('-' * 80)
    sample_count = 0
    for addr, chains in list(duplicates_found.items())[:20]:
        print(f'\n  주소: {addr}')
        print(f'    Ethereum (ETH): ID={eth_addresses[addr]["id"]}, name_tag={eth_addresses[addr]["name_tag"]}')
        for chain_info in chains:
            print(f'    중복 발견 → {chain_info["chain_type"]}: ID={chain_info["id"]}, name_tag={chain_info["name_tag"]}')
        sample_count += 1
        if sample_count >= 20:
            break
    
    if len(duplicates_found) > 20:
        print(f'\n  ... 외 {len(duplicates_found) - 20}개 주소도 중복됨')
    
    # 전체 중복 주소 목록을 파일로 저장
    output_file = PROJECT_ROOT / 'usdc_duplicate_addresses.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('USDC 중복 주소 목록\n')
        f.write('=' * 80 + '\n\n')
        for addr, chains in duplicates_found.items():
            f.write(f'주소: {addr}\n')
            f.write(f'  Ethereum (ETH): ID={eth_addresses[addr]["id"]}\n')
            for chain_info in chains:
                f.write(f'  중복 → {chain_info["chain_type"]}: ID={chain_info["id"]}\n')
            f.write('\n')
    
    print(f'\n  💾 전체 중복 목록이 {output_file}에 저장되었습니다.')
    
else:
    print('  ✅ 중복된 주소가 없습니다.')

# 5. 각 네트워크별 고유 주소 수 확인
print('\n[5단계] 네트워크별 고유 주소 통계')
print('-' * 80)
for chain_type in usdc_chain_types:
    response = supabase.table('whale_address').select('address').eq('chain_type', chain_type).execute()
    unique_addresses = set()
    for record in response.data:
        addr = record.get('address', '').lower().strip()
        if addr:
            unique_addresses.add(addr)
    print(f'  {chain_type}: 총 {chain_counts[chain_type]}건, 고유 주소 {len(unique_addresses)}개')

print('\n' + '=' * 80)
print('✅ 확인 완료')
print('=' * 80)

