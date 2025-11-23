#!/usr/bin/env python3
"""
라벨링되지 않은(NULL) 데이터 분석 및 해결 방안 도출
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    return create_client(supabase_url, supabase_key)

def analyze_null_labels(supabase):
    print("=" * 80)
    print("🔍 라벨링 미완료 데이터 심층 분석")
    print("=" * 80)
    
    # 1. 전체 통계
    response = supabase.table('whale_transactions').select('*', count='exact').execute()
    total = response.count
    
    response = supabase.table('whale_transactions').select('*', count='exact').is_('from_label', 'null').execute()
    from_null = response.count
    
    response = supabase.table('whale_transactions').select('*', count='exact').is_('to_label', 'null').execute()
    to_null = response.count
    
    print(f"총 거래: {total:,}건")
    print(f"from_label NULL: {from_null:,}건 ({from_null/total*100:.1f}%)")
    print(f"to_label NULL: {to_null:,}건 ({to_null/total*100:.1f}%)")
    
    # 2. from_label NULL 원인 분석
    print("\n1️⃣ from_label이 NULL인 이유 분석:")
    
    # 샘플 100개 가져와서 whale_address에 있는지 확인
    response = supabase.table('whale_transactions')\
        .select('from_address')\
        .is_('from_label', 'null')\
        .limit(100)\
        .execute()
    
    sample_addrs = list(set([r['from_address'].lower() for r in response.data]))
    
    # whale_address에 있는지 조회
    wa_response = supabase.table('whale_address')\
        .select('address, name_tag')\
        .in_('address', sample_addrs)\
        .execute()
    
    found_addrs = {r['address'].lower(): r.get('name_tag') for r in wa_response.data}
    
    missing_in_wa = 0
    no_nametag = 0
    
    for addr in sample_addrs:
        if addr not in found_addrs:
            missing_in_wa += 1
        elif not found_addrs[addr]:
            no_nametag += 1
            
    print(f"   샘플 {len(sample_addrs)}개 주소 중:")
    print(f"   - whale_address 테이블에 아예 없음: {missing_in_wa}개")
    print(f"   - whale_address에 있지만 name_tag가 없음: {no_nametag}개")
    
    # 3. to_label NULL 원인 분석
    print("\n2️⃣ to_label이 NULL인 이유 분석:")
    
    response = supabase.table('whale_transactions')\
        .select('to_address')\
        .is_('to_label', 'null')\
        .not_.is_('to_address', 'null')\
        .limit(100)\
        .execute()
    
    sample_addrs = list(set([r['to_address'].lower() for r in response.data]))
    
    wa_response = supabase.table('whale_address')\
        .select('address, name_tag')\
        .in_('address', sample_addrs)\
        .execute()
    
    found_addrs = {r['address'].lower(): r.get('name_tag') for r in wa_response.data}
    
    missing_in_wa = 0
    no_nametag = 0
    
    for addr in sample_addrs:
        if addr not in found_addrs:
            missing_in_wa += 1
        elif not found_addrs[addr]:
            no_nametag += 1
            
    print(f"   샘플 {len(sample_addrs)}개 주소 중:")
    print(f"   - whale_address 테이블에 아예 없음: {missing_in_wa}개")
    print(f"   - whale_address에 있지만 name_tag가 없음: {no_nametag}개")

    # 4. 결론 도출
    print("\n" + "=" * 80)
    print("💡 분석 결과 및 해결 방안")
    print("=" * 80)
    
    if missing_in_wa > 0:
        print("📌 원인 1: 거래의 주체가 whale_address 목록에 없는 '일반 지갑' 또는 '새로운 고래'입니다.")
        print("   → 해결: 모든 지갑을 라벨링할 수는 없습니다. whale_address에 없는 지갑은 'Unknown' 또는 NULL로 두는 것이 정상입니다.")
        print("   → 보완: Etherscan/BSCScan API를 통해 추가적으로 라벨을 수집할 수 있습니다.")
        
    if no_nametag > 0:
        print("📌 원인 2: whale_address에 등록은 되어 있지만 'name_tag' 정보가 비어있습니다.")
        print("   → 해결: whale_address 테이블의 빈 name_tag를 채워야 합니다.")

if __name__ == '__main__':
    try:
        supabase = get_supabase_client()
        analyze_null_labels(supabase)
    except Exception as e:
        print(f"❌ 오류: {e}")

