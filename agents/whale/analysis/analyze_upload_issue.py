#!/usr/bin/env python3
"""업로드 문제 원인 분석"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print('=' * 70)
print('🔍 업로드 문제 원인 분석')
print('=' * 70)

# 1. Supabase에 실제로 어떤 데이터가 있는지 확인
print('\n[1] Supabase whale_address 테이블 현황')
print('-' * 70)

response = supabase.table('whale_address').select('*', count='exact').execute()
total = response.count if hasattr(response, 'count') else len(response.data)
print(f'전체 레코드 수: {total}건')

# 체인별 통계
chain_counts = {}
all_data = response.data
for record in all_data:
    chain = record.get('chain_type', 'UNKNOWN')
    chain_counts[chain] = chain_counts.get(chain, 0) + 1

print('\n체인별 통계:')
for chain, count in sorted(chain_counts.items()):
    print(f'  {chain}: {count}건')

# ID 패턴 확인
print('\nID 패턴 샘플:')
id_samples = {}
for record in all_data[:50]:  # 처음 50개만
    id_val = record.get('id', '')
    if id_val:
        prefix = id_val[:3] if len(id_val) >= 3 else id_val
        if prefix not in id_samples:
            id_samples[prefix] = []
        if len(id_samples[prefix]) < 5:
            id_samples[prefix].append(id_val)

for prefix, ids in sorted(id_samples.items()):
    print(f'  {prefix}*: {ids}')

# 2. CSV 파일 확인
print('\n[2] CSV 파일 (whale_address_cleaned.csv) 현황')
print('-' * 70)

if os.path.exists('whale_address_cleaned.csv'):
    df_csv = pd.read_csv('whale_address_cleaned.csv')
    print(f'CSV 총 레코드: {len(df_csv)}건')
    
    print('\nCSV 체인별 통계:')
    csv_chain_counts = df_csv['chain_type'].value_counts().sort_index()
    for chain, count in csv_chain_counts.items():
        print(f'  {chain}: {count}건')
    
    print('\nCSV ID 샘플:')
    for chain in df_csv['chain_type'].unique()[:5]:
        chain_ids = df_csv[df_csv['chain_type'] == chain]['id'].head(3).tolist()
        print(f'  {chain}: {chain_ids}')
else:
    print('❌ CSV 파일을 찾을 수 없습니다!')

# 3. 테이블 스키마 확인 (PRIMARY KEY, UNIQUE 제약 등)
print('\n[3] 테이블 스키마 확인')
print('-' * 70)

# Supabase에서 테이블 정보 조회 시도
try:
    # information_schema를 통해 확인
    schema_query = """
    SELECT 
        column_name, 
        data_type, 
        is_nullable,
        column_default
    FROM information_schema.columns 
    WHERE table_name = 'whale_address' 
    AND table_schema = 'public'
    ORDER BY ordinal_position;
    """
    
    # Supabase는 직접 SQL 실행이 어려우므로, 실제 데이터로 추론
    print('⚠️ Supabase Python 클라이언트로는 직접 스키마 조회가 어렵습니다.')
    print('   대신 실제 데이터와 업로드 스크립트를 분석합니다.')
    
except Exception as e:
    print(f'스키마 조회 오류: {e}')

# 4. 업로드 스크립트 분석
print('\n[4] 업로드 스크립트 분석')
print('-' * 70)

upload_script = 'update_whale_address_supabase.py'
if os.path.exists(upload_script):
    with open(upload_script, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # upsert 사용 여부 확인
    if 'upsert' in content:
        print('✅ upsert 메서드 사용 중')
        # upsert의 기준 키 확인
        if 'id' in content and 'chain_type' in content:
            print('   - id와 chain_type을 기준으로 업데이트 시도')
        else:
            print('   - ⚠️ upsert 기준 키가 명확하지 않음')
    else:
        print('❌ upsert 메서드를 사용하지 않음')
    
    # PRIMARY KEY 관련 확인
    if 'PRIMARY KEY' in content or 'primary key' in content:
        print('✅ PRIMARY KEY 관련 코드 발견')
    else:
        print('⚠️ PRIMARY KEY 관련 코드 없음')
else:
    print(f'❌ 업로드 스크립트를 찾을 수 없습니다: {upload_script}')

# 5. ID 충돌 확인
print('\n[5] ID 충돌 확인')
print('-' * 70)

if os.path.exists('whale_address_cleaned.csv'):
    df_csv = pd.read_csv('whale_address_cleaned.csv')
    csv_ids = set(df_csv['id'].tolist())
    
    # Supabase의 ID 가져오기
    supabase_ids = set()
    for record in all_data:
        id_val = record.get('id')
        if id_val:
            supabase_ids.add(str(id_val))
    
    # CSV에 있는데 Supabase에 없는 ID
    missing_in_supabase = csv_ids - supabase_ids
    print(f'CSV에 있지만 Supabase에 없는 ID: {len(missing_in_supabase)}건')
    if missing_in_supabase:
        print(f'  샘플: {list(missing_in_supabase)[:10]}')
    
    # Supabase에 있는데 CSV에 없는 ID
    extra_in_supabase = supabase_ids - csv_ids
    print(f'\nSupabase에 있지만 CSV에 없는 ID: {len(extra_in_supabase)}건')
    if extra_in_supabase:
        print(f'  샘플: {list(extra_in_supabase)[:10]}')
    
    # 공통 ID
    common_ids = csv_ids & supabase_ids
    print(f'\n공통 ID: {len(common_ids)}건')

# 6. 가능한 원인 분석
print('\n' + '=' * 70)
print('🔍 가능한 원인 분석')
print('=' * 70)

print('\n[원인 1] PRIMARY KEY 또는 UNIQUE 제약 없음')
print('  - whale_address 테이블에 PRIMARY KEY가 없으면 upsert가 제대로 작동하지 않을 수 있음')
print('  - upsert는 기본적으로 PRIMARY KEY나 UNIQUE 제약을 기준으로 작동')
print('  - 확인 필요: 테이블에 id가 PRIMARY KEY인지, 아니면 단순 TEXT 컬럼인지')

print('\n[원인 2] upsert 기준 키 불일치')
print('  - upsert가 id만 기준으로 작동하는데, id가 중복될 수 있음')
print('  - 예: BSC1, BTC1, ETH1 등이 모두 존재할 수 있음')
print('  - 확인 필요: upsert가 (id, chain_type) 복합 키를 사용하는지')

print('\n[원인 3] 기존 데이터와 충돌')
print('  - Supabase에 BSC1~BSC100이 이미 존재')
print('  - CSV에 BTC001, ETH001 등이 있지만, id만으로는 구분이 안 될 수 있음')
print('  - 확인 필요: id가 전역적으로 고유한지, 아니면 체인별로 고유한지')

print('\n[원인 4] 업로드 스크립트의 upsert 로직 문제')
print('  - upsert가 실제로 업데이트 대신 무시하고 있을 수 있음')
print('  - 확인 필요: upsert 후 실제로 데이터가 변경되었는지')

print('\n[원인 5] 데이터 타입 불일치')
print('  - CSV의 id가 "BTC001"인데 Supabase에 이미 다른 형식으로 저장되어 있을 수 있음')
print('  - 확인 필요: id의 데이터 타입과 형식이 일치하는지')



