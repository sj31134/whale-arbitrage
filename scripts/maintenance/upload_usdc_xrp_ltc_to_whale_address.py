#!/usr/bin/env python3
"""
USDC, XRP, LTC를 whale_address 테이블에 업로드
"""

import os
import csv
from pathlib import Path
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

# 업로드 설정
UPLOAD_CONFIGS = [
    {
        'csv_file': 'usdc_ethereum_richlist_top100.csv',
        'chain_type': 'USDC',
        'name_tag': 'USDC'
    },
    {
        'csv_file': 'xrp_mainnet_richlist_top100.csv',
        'chain_type': 'XRP',
        'name_tag': 'Ripple'
    },
    {
        'csv_file': 'ltc_mainnet_richlist_top100.csv',
        'chain_type': 'LTC',
        'name_tag': 'Litecoin'
    }
]

def upload_csv_to_whale_address(csv_filename: str, chain_type: str, name_tag: str):
    """CSV 파일을 whale_address에 업로드"""
    csv_path = PROJECT_ROOT / csv_filename
    
    if not csv_path.exists():
        print(f"  ❌ 파일 없음: {csv_filename}")
        return
    
    print(f"\n{'='*80}")
    print(f"📤 {chain_type} 업로드")
    print(f"{'='*80}")
    print(f"  파일: {csv_filename}")
    
    records = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rank = int(row['rank'])
            address = row['address']
            
            record = {
                'id': f"{chain_type}{rank:03d}",
                'chain_type': chain_type,
                'address': address,
                'name_tag': name_tag,
                'balance': None,
                'percentage': None,
                'txn_count': None
            }
            records.append(record)
    
    print(f"  📊 레코드: {len(records)}건")
    
    if records:
        try:
            # 배치 업로드 (insert 사용)
            batch_size = 100
            uploaded = 0
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                try:
                    supabase.table('whale_address').insert(batch).execute()
                    uploaded += len(batch)
                except Exception as e:
                    # 중복 오류 무시
                    if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                        print(f"  ⚠️ 중복 데이터 건너뜀")
                    else:
                        print(f"  ❌ 배치 업로드 실패: {e}")
            print(f"  ✅ 업로드 완료: {uploaded}건")
        except Exception as e:
            print(f"  ❌ 업로드 실패: {e}")
    
    # 검증
    try:
        response = supabase.table('whale_address').select('*').eq('chain_type', chain_type).execute()
        print(f"  ✅ 검증: {len(response.data)}건 확인")
    except Exception as e:
        print(f"  ⚠️ 검증 실패: {e}")

def main():
    print("\n" + "="*80)
    print("🐋 USDC, XRP, LTC → whale_address 업로드")
    print("="*80)
    
    for config in UPLOAD_CONFIGS:
        upload_csv_to_whale_address(
            config['csv_file'],
            config['chain_type'],
            config['name_tag']
        )
    
    print("\n" + "="*80)
    print("✅ 모든 업로드 완료")
    print("="*80)

if __name__ == "__main__":
    main()

