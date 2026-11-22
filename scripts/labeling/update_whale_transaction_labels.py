#!/usr/bin/env python3
"""
whale_transactions 테이블의 from_label과 to_label 업데이트
whale_address 테이블의 정보를 활용하여 라벨 채우기
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def check_current_labels(supabase):
    """현재 라벨 상태 확인"""
    print("=" * 80)
    print("📊 현재 라벨 상태 확인")
    print("=" * 80)
    
    try:
        # 전체 거래 수
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .execute()
        total = response.count if hasattr(response, 'count') else len(response.data)
        
        # from_label이 NULL이 아닌 것
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .not_.is_('from_label', 'null')\
            .execute()
        from_labeled = response.count if hasattr(response, 'count') else len(response.data)
        
        # to_label이 NULL이 아닌 것
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .not_.is_('to_label', 'null')\
            .execute()
        to_labeled = response.count if hasattr(response, 'count') else len(response.data)
        
        print(f"\n총 거래 수: {total:,}건")
        print(f"from_label 채워진 거래: {from_labeled:,}건 ({from_labeled/total*100:.1f}%)")
        print(f"to_label 채워진 거래: {to_labeled:,}건 ({to_labeled/total*100:.1f}%)")
        print(f"\nfrom_label NULL: {total - from_labeled:,}건")
        print(f"to_label NULL: {total - to_labeled:,}건")
        
    except Exception as e:
        print(f"❌ 오류: {e}")

def get_whale_address_map(supabase):
    """whale_address 테이블에서 주소 -> name_tag 매핑 생성"""
    print("\n" + "=" * 80)
    print("📋 whale_address 매핑 생성")
    print("=" * 80)
    
    try:
        response = supabase.table('whale_address')\
            .select('address, name_tag, chain_type')\
            .execute()
        
        address_map = {}
        for row in response.data:
            address = row['address'].lower() if row['address'] else None
            name_tag = row.get('name_tag')
            
            if address and name_tag:
                address_map[address] = name_tag
        
        print(f"\n✅ {len(address_map):,}개 주소 매핑 생성 완료")
        
        # 샘플 출력
        print("\n샘플 매핑 (10개):")
        for idx, (addr, label) in enumerate(list(address_map.items())[:10], 1):
            print(f"  {idx}. {addr[:16]}... → {label}")
        
        return address_map
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return {}

def update_labels_batch(supabase, address_map, batch_size=100, limit=None):
    """라벨 업데이트 (배치 처리)"""
    print("\n" + "=" * 80)
    print("🔄 라벨 업데이트 시작")
    print("=" * 80)
    
    updated_count = 0
    processed_count = 0
    
    try:
        # from_label이 NULL인 거래 조회
        print("\n1️⃣ from_label 업데이트 중...")
        
        offset = 0
        while True:
            # 배치로 조회 (이미 업데이트된 것은 건너뛰기)
            query = supabase.table('whale_transactions')\
                .select('tx_hash, from_address')\
                .is_('from_label', 'null')\
                .limit(batch_size)\
                .offset(offset)
            
            if limit and processed_count >= limit:
                break
                
            response = query.execute()
            
            if not response.data:
                break
            
            # 업데이트할 거래 찾기
            updates = []
            for tx in response.data:
                from_addr = tx['from_address'].lower() if tx['from_address'] else None
                
                if from_addr and from_addr in address_map:
                    updates.append({
                        'tx_hash': tx['tx_hash'],
                        'from_label': address_map[from_addr]
                    })
            
            # 업데이트 실행 (타임아웃 에러 처리)
            for update in updates:
                retry_count = 0
                max_retries = 3
                while retry_count < max_retries:
                    try:
                        supabase.table('whale_transactions')\
                            .update({'from_label': update['from_label']})\
                            .eq('tx_hash', update['tx_hash'])\
                            .execute()
                        updated_count += 1
                        break
                    except Exception as e:
                        retry_count += 1
                        if 'timeout' in str(e).lower() and retry_count < max_retries:
                            print(f"  ⚠️ 타임아웃, 재시도 중... ({retry_count}/{max_retries})")
                            import time
                            time.sleep(2)
                        else:
                            if retry_count >= max_retries:
                                print(f"  ❌ 업데이트 실패 ({update['tx_hash'][:16]}...): {e}")
                            break
            
            processed_count += len(response.data)
            
            if updates:
                print(f"  진행: {processed_count:,}건 처리, {updated_count:,}건 업데이트")
            
            # 다음 배치로
            offset += batch_size
            
            if len(response.data) < batch_size:
                break
        
        print(f"\n✅ from_label 업데이트 완료: {updated_count:,}건")
        
        # to_label이 NULL인 거래 조회
        print("\n2️⃣ to_label 업데이트 중...")
        
        to_updated_count = 0
        to_processed_count = 0
        offset = 0
        
        while True:
            # 배치로 조회
            query = supabase.table('whale_transactions')\
                .select('tx_hash, to_address')\
                .is_('to_label', 'null')\
                .limit(batch_size)\
                .offset(offset)
            
            if limit and to_processed_count >= limit:
                break
                
            response = query.execute()
            
            if not response.data:
                break
            
            # 업데이트할 거래 찾기
            updates = []
            for tx in response.data:
                to_addr = tx['to_address'].lower() if tx.get('to_address') else None
                
                if to_addr and to_addr in address_map:
                    updates.append({
                        'tx_hash': tx['tx_hash'],
                        'to_label': address_map[to_addr]
                    })
            
            # 업데이트 실행 (타임아웃 에러 처리)
            for update in updates:
                retry_count = 0
                max_retries = 3
                while retry_count < max_retries:
                    try:
                        supabase.table('whale_transactions')\
                            .update({'to_label': update['to_label']})\
                            .eq('tx_hash', update['tx_hash'])\
                            .execute()
                        to_updated_count += 1
                        break
                    except Exception as e:
                        retry_count += 1
                        if 'timeout' in str(e).lower() and retry_count < max_retries:
                            print(f"  ⚠️ 타임아웃, 재시도 중... ({retry_count}/{max_retries})")
                            import time
                            time.sleep(2)
                        else:
                            if retry_count >= max_retries:
                                print(f"  ❌ 업데이트 실패 ({update['tx_hash'][:16]}...): {e}")
                            break
            
            to_processed_count += len(response.data)
            
            if updates:
                print(f"  진행: {to_processed_count:,}건 처리, {to_updated_count:,}건 업데이트")
            
            # 다음 배치로
            offset += batch_size
            
            if len(response.data) < batch_size:
                break
        
        print(f"\n✅ to_label 업데이트 완료: {to_updated_count:,}건")
        print(f"\n📊 총 업데이트: {updated_count + to_updated_count:,}건")
        
        return updated_count + to_updated_count
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return updated_count

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='whale_transactions 라벨 업데이트')
    parser.add_argument('--test', action='store_true', help='테스트 모드 (100건만 처리)')
    parser.add_argument('--batch-size', type=int, default=100, help='배치 크기 (기본: 100)')
    parser.add_argument('--yes', action='store_true', help='확인 없이 자동 진행')
    args = parser.parse_args()
    
    print("=" * 80)
    print("🏷️  whale_transactions 라벨 업데이트")
    print("=" * 80)
    
    if args.test:
        print("\n⚠️ 테스트 모드: 100건만 처리합니다")
    
    try:
        supabase = get_supabase_client()
        
        # 현재 상태 확인
        check_current_labels(supabase)
        
        # whale_address 매핑 생성
        address_map = get_whale_address_map(supabase)
        
        if not address_map:
            print("\n❌ whale_address 매핑이 비어있습니다")
            return
        
        # 사용자 확인
        if not args.yes:
            print("\n" + "=" * 80)
            response = input("계속 진행하시겠습니까? (y/n): ")
            if response.lower() != 'y':
                print("취소되었습니다.")
                return
        else:
            print("\n✅ 자동 진행 모드")
        
        # 라벨 업데이트
        limit = 100 if args.test else None
        updated = update_labels_batch(supabase, address_map, args.batch_size, limit)
        
        # 결과 확인
        print("\n" + "=" * 80)
        print("📊 업데이트 후 상태")
        print("=" * 80)
        check_current_labels(supabase)
        
        print("\n" + "=" * 80)
        print("✅ 작업 완료")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

