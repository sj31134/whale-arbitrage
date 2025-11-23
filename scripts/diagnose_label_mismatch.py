#!/usr/bin/env python3
"""
라벨 매칭 문제 진단
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
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def diagnose():
    """진단 실행"""
    print("=" * 80)
    print("🔍 라벨 매칭 문제 진단")
    print("=" * 80)
    
    try:
        supabase = get_supabase_client()
        
        # 1. whale_address 상태
        print("\n1️⃣ whale_address 테이블 분석:")
        response = supabase.table('whale_address').select('address, name_tag, chain_type').execute()
        
        total_addr = len(response.data)
        with_name_tag = len([r for r in response.data if r.get('name_tag')])
        without_name_tag = total_addr - with_name_tag
        
        print(f"   총 주소: {total_addr}개")
        print(f"   name_tag 있음: {with_name_tag}개")
        print(f"   name_tag 없음: {without_name_tag}개")
        
        # name_tag가 있는 주소들
        addresses_with_tag = {r['address'].lower(): r['name_tag'] for r in response.data if r.get('name_tag')}
        print(f"   매핑 가능 주소: {len(addresses_with_tag)}개")
        
        # 2. whale_transactions에서 from/to 주소 확인
        print("\n2️⃣ whale_transactions 주소 분석:")
        
        # from_address 샘플
        response = supabase.table('whale_transactions')\
            .select('from_address, from_label')\
            .limit(1000)\
            .execute()
        
        sample_from = response.data
        matched_from = 0
        unmatched_from = 0
        already_labeled = 0
        
        for tx in sample_from:
            from_addr = tx['from_address'].lower() if tx.get('from_address') else None
            if tx.get('from_label'):
                already_labeled += 1
            elif from_addr and from_addr in addresses_with_tag:
                matched_from += 1
            else:
                unmatched_from += 1
        
        print(f"   샘플 1,000건 분석:")
        print(f"   - 이미 라벨링됨: {already_labeled}건")
        print(f"   - 매칭 가능: {matched_from}건")
        print(f"   - 매칭 불가: {unmatched_from}건")
        
        # 3. 왜 매칭이 안 되는지 확인
        print("\n3️⃣ 매칭 실패 원인 분석:")
        
        # 매칭 안 되는 주소 샘플
        unmatched_samples = []
        for tx in sample_from[:20]:
            from_addr = tx['from_address'].lower() if tx.get('from_address') else None
            if not tx.get('from_label') and from_addr and from_addr not in addresses_with_tag:
                unmatched_samples.append(tx['from_address'])
        
        if unmatched_samples:
            print(f"   매칭 안 되는 주소 샘플 (5개):")
            for addr in unmatched_samples[:5]:
                print(f"   - {addr}")
                # whale_address에 있는지 확인
                response = supabase.table('whale_address')\
                    .select('address, name_tag, chain_type')\
                    .or_(f'address.eq.{addr},address.ilike.{addr}')\
                    .execute()
                
                if response.data:
                    print(f"     → whale_address에 존재: {response.data[0]}")
                else:
                    print(f"     → whale_address에 없음!")
        
        # 4. 전체 통계
        print("\n4️⃣ 전체 매칭 가능성:")
        response = supabase.table('whale_transactions').select('*', count='exact').execute()
        total_tx = response.count if hasattr(response, 'count') else len(response.data)
        
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .not_.is_('from_label', 'null')\
            .execute()
        labeled = response.count if hasattr(response, 'count') else len(response.data)
        
        print(f"   총 거래: {total_tx:,}건")
        print(f"   라벨링됨: {labeled:,}건 ({labeled/total_tx*100:.1f}%)")
        print(f"   라벨링 안 됨: {total_tx - labeled:,}건 ({(total_tx-labeled)/total_tx*100:.1f}%)")
        
        # 5. 결론
        print("\n" + "=" * 80)
        print("📊 결론:")
        print("=" * 80)
        
        expected_match_rate = (matched_from / (matched_from + unmatched_from)) * 100 if (matched_from + unmatched_from) > 0 else 0
        print(f"\n예상 매칭률: {expected_match_rate:.1f}%")
        print(f"실제 라벨링률: {labeled/total_tx*100:.1f}%")
        
        if expected_match_rate < 50:
            print("\n⚠️ 문제: whale_address에 있는 주소가 whale_transactions에 없습니다!")
            print("   → whale_address의 주소들로 거래를 수집했는지 확인 필요")
        elif with_name_tag < 100:
            print(f"\n⚠️ 문제: whale_address에 name_tag가 있는 주소가 {with_name_tag}개밖에 없습니다!")
            print("   → name_tag를 더 추가해야 합니다")
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    diagnose()

