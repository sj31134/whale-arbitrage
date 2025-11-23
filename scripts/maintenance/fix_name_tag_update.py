#!/usr/bin/env python3
"""
name_tag를 직접 업데이트하는 스크립트
whale_address 테이블에 PRIMARY KEY가 없어서 upsert가 제대로 작동하지 않을 수 있으므로
id와 chain_type을 기준으로 직접 업데이트
"""

import os
import sys
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def update_name_tags():
    """CSV 파일의 name_tag를 Supabase에 직접 업데이트"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    supabase = create_client(supabase_url, supabase_key)
    
    # CSV 파일 읽기
    df = pd.read_csv('whale_address_cleaned.csv')
    print(f'CSV 파일 총 레코드: {len(df)}건')
    
    # name_tag가 있는 레코드만 필터링
    df_with_name_tag = df[df['name_tag'].notna() & (df['name_tag'] != '')]
    print(f'name_tag가 있는 레코드: {len(df_with_name_tag)}건')
    
    # 배치로 업데이트
    batch_size = 50
    total_updated = 0
    errors = []
    
    print(f'\n📤 name_tag 업데이트 중...')
    
    for i in range(0, len(df_with_name_tag), batch_size):
        batch = df_with_name_tag.iloc[i:i + batch_size]
        
        for _, row in batch.iterrows():
            try:
                # id와 chain_type으로 해당 레코드 찾아서 업데이트
                response = supabase.table('whale_address').update({
                    'name_tag': str(row['name_tag'])
                }).eq('id', str(row['id'])).eq('chain_type', str(row['chain_type'])).execute()
                
                if response.data:
                    total_updated += 1
                else:
                    # 레코드가 없으면 insert 시도
                    record = {
                        'id': str(row['id']),
                        'chain_type': str(row['chain_type']),
                        'address': str(row['address']),
                        'name_tag': str(row['name_tag']) if pd.notna(row['name_tag']) and row['name_tag'] != '' else None,
                        'balance': str(row['balance']) if pd.notna(row['balance']) and row['balance'] != '' else None,
                        'percentage': str(row['percentage']) if pd.notna(row['percentage']) and row['percentage'] != '' else None,
                        'txn_count': str(row['txn_count']) if pd.notna(row['txn_count']) and row['txn_count'] != '' else None,
                    }
                    supabase.table('whale_address').insert(record).execute()
                    total_updated += 1
                    
            except Exception as e:
                errors.append(f"ID {row['id']}: {str(e)}")
        
        if (i + batch_size) % 100 == 0:
            print(f'   진행 중: {min(i + batch_size, len(df_with_name_tag))}/{len(df_with_name_tag)}건')
    
    print(f'\n✅ 업데이트 완료: {total_updated}건')
    
    if errors:
        print(f'\n⚠️ 오류 발생: {len(errors)}건')
        for error in errors[:10]:
            print(f'   - {error}')
        if len(errors) > 10:
            print(f'   ... 외 {len(errors) - 10}건')
    
    # 검증
    print('\n' + '=' * 70)
    print('검증: 업데이트된 name_tag 확인')
    print('=' * 70)
    
    for chain in ['BTC', 'ETH', 'LTC', 'DOGE', 'VTC']:
        chain_df = df_with_name_tag[df_with_name_tag['chain_type'] == chain]
        expected_name = {'BTC': 'Bitcoin', 'ETH': 'Ethereum', 'LTC': 'Litecoin', 'DOGE': 'Dogecoin', 'VTC': 'Vertcoin'}.get(chain, chain)
        
        # CSV에서 해당 체인의 name_tag가 expected_name인 것들
        csv_count = len(chain_df[chain_df['name_tag'] == expected_name])
        
        # Supabase에서 확인
        response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', chain).eq('name_tag', expected_name).execute()
        supabase_count = response.count if hasattr(response, 'count') else len(response.data)
        
        print(f'{chain} ({expected_name}): CSV {csv_count}건, Supabase {supabase_count}건')
    
    return total_updated, errors

if __name__ == '__main__':
    print("=" * 70)
    print("🔧 name_tag 직접 업데이트")
    print("=" * 70)
    
    try:
        updated, errors = update_name_tags()
        print(f"\n✅ 완료! 총 {updated}건 업데이트")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



