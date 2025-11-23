#!/usr/bin/env python3
"""
USDC whale_address 테이블의 상세 분석
Ethereum에 300건이 있는 이유와 중복 원인 분석
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
print('🔍 USDC whale_address 상세 분석')
print('=' * 80)

# 1. Ethereum (ETH) chain_type의 name_tag별 통계
print('\n[1단계] Ethereum (ETH) chain_type의 name_tag별 통계')
print('-' * 80)

eth_response = supabase.table('whale_address').select('name_tag, address, id').eq('chain_type', 'ETH').execute()

name_tag_counts = defaultdict(int)
name_tag_samples = defaultdict(list)

for record in eth_response.data:
    name_tag = record.get('name_tag') or 'None'
    name_tag_counts[name_tag] += 1
    if len(name_tag_samples[name_tag]) < 3:
        name_tag_samples[name_tag].append({
            'id': record.get('id'),
            'address': record.get('address', '')[:20] + '...' if len(record.get('address', '')) > 20 else record.get('address', '')
        })

for name_tag, count in sorted(name_tag_counts.items(), key=lambda x: x[1], reverse=True):
    print(f'  {name_tag}: {count}건')
    if name_tag_samples[name_tag]:
        print(f'    샘플 ID: {", ".join([s["id"] for s in name_tag_samples[name_tag][:3]])}')

# 2. USDC 관련 name_tag만 필터링
print('\n[2단계] USDC 관련 데이터만 필터링 (name_tag="USD Coin")')
print('-' * 80)

usdc_eth_response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', 'ETH').eq('name_tag', 'USD Coin').execute()
usdc_eth_count = usdc_eth_response.count if hasattr(usdc_eth_response, 'count') else len(usdc_eth_response.data)

print(f'  ✅ name_tag="USD Coin"인 ETH 데이터: {usdc_eth_count}건')

# 3. 각 네트워크별 USDC 데이터 확인
print('\n[3단계] 각 네트워크별 USDC 데이터 확인 (name_tag="USD Coin")')
print('-' * 80)

usdc_chain_types = ['ETH', 'BSC', 'POLYGON', 'ARBITRUM', 'OPTIMISM', 'AVALANCHE', 'SOL', 'BASE']

for chain_type in usdc_chain_types:
    response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', chain_type).eq('name_tag', 'USD Coin').execute()
    count = response.count if hasattr(response, 'count') else len(response.data)
    print(f'  {chain_type}: {count}건')

# 4. 중복 주소 상세 확인
print('\n[4단계] 중복 주소 상세 확인')
print('-' * 80)

# Ethereum의 모든 주소 (name_tag 무관)
eth_all = supabase.table('whale_address').select('address, id, name_tag').eq('chain_type', 'ETH').execute()
eth_addresses = {record.get('address', '').lower().strip(): record for record in eth_all.data if record.get('address')}

# BSC의 모든 주소
bsc_all = supabase.table('whale_address').select('address, id, name_tag').eq('chain_type', 'BSC').execute()
bsc_addresses = {record.get('address', '').lower().strip(): record for record in bsc_all.data if record.get('address')}

# 중복 찾기
duplicates = []
for addr in eth_addresses:
    if addr in bsc_addresses:
        duplicates.append({
            'address': addr,
            'eth_id': eth_addresses[addr].get('id'),
            'eth_name_tag': eth_addresses[addr].get('name_tag'),
            'bsc_id': bsc_addresses[addr].get('id'),
            'bsc_name_tag': bsc_addresses[addr].get('name_tag')
        })

print(f'  🔴 Ethereum과 BSC 간 중복: {len(duplicates)}건')
print('\n  중복 상세:')
for dup in duplicates:
    print(f'\n  주소: {dup["address"]}')
    print(f'    ETH: ID={dup["eth_id"]}, name_tag={dup["eth_name_tag"]}')
    print(f'    BSC: ID={dup["bsc_id"]}, name_tag={dup["bsc_name_tag"]}')

# 5. CSV 파일과 비교
print('\n[5단계] CSV 파일과 Supabase 데이터 비교')
print('-' * 80)

import pandas as pd

# Ethereum CSV 확인
eth_csv_path = PROJECT_ROOT / 'usdc_ethereum_richlist_top100.csv'
if eth_csv_path.exists():
    eth_df = pd.read_csv(eth_csv_path)
    print(f'  📄 usdc_ethereum_richlist_top100.csv: {len(eth_df)}건')
    
    # CSV의 주소 목록
    csv_addresses = set(eth_df['address'].str.lower().str.strip())
    
    # Supabase의 USDC Ethereum 주소 목록
    supabase_usdc_eth = supabase.table('whale_address').select('address').eq('chain_type', 'ETH').eq('name_tag', 'USD Coin').execute()
    supabase_addresses = set([r.get('address', '').lower().strip() for r in supabase_usdc_eth.data if r.get('address')])
    
    print(f'  CSV 주소 수: {len(csv_addresses)}')
    print(f'  Supabase USDC ETH 주소 수: {len(supabase_addresses)}')
    
    # CSV에만 있는 주소
    only_in_csv = csv_addresses - supabase_addresses
    if only_in_csv:
        print(f'  ⚠️ CSV에만 있는 주소: {len(only_in_csv)}개')
    
    # Supabase에만 있는 주소
    only_in_supabase = supabase_addresses - csv_addresses
    if only_in_supabase:
        print(f'  ⚠️ Supabase에만 있는 주소: {len(only_in_supabase)}개')
        print(f'    샘플: {list(only_in_supabase)[:5]}')

# BSC CSV 확인
bsc_csv_path = PROJECT_ROOT / 'usdc_bsc_richlist_top100.csv'
if bsc_csv_path.exists():
    bsc_df = pd.read_csv(bsc_csv_path)
    print(f'\n  📄 usdc_bsc_richlist_top100.csv: {len(bsc_df)}건')
    
    # CSV의 주소 목록
    csv_addresses = set(bsc_df['address'].str.lower().str.strip())
    
    # Supabase의 USDC BSC 주소 목록
    supabase_usdc_bsc = supabase.table('whale_address').select('address').eq('chain_type', 'BSC').eq('name_tag', 'USD Coin').execute()
    supabase_addresses = set([r.get('address', '').lower().strip() for r in supabase_usdc_bsc.data if r.get('address')])
    
    print(f'  CSV 주소 수: {len(csv_addresses)}')
    print(f'  Supabase USDC BSC 주소 수: {len(supabase_addresses)}')
    
    # 중복 주소 확인
    eth_addresses_set = set([r.get('address', '').lower().strip() for r in eth_all.data if r.get('address')])
    csv_eth_overlap = csv_addresses & eth_addresses_set
    if csv_eth_overlap:
        print(f'  🔴 BSC CSV 주소 중 Ethereum에도 있는 주소: {len(csv_eth_overlap)}개')
        print(f'    샘플: {list(csv_eth_overlap)[:5]}')

print('\n' + '=' * 80)
print('✅ 분석 완료')
print('=' * 80)

