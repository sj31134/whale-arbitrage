#!/usr/bin/env python3
"""
whale_address 테이블에서 BSC 네트워크의 name_tag를 'BNB'로 업데이트
chain_type='BSC'인 모든 레코드의 name_tag를 'BNB'로 통일
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')


def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)


def check_current_bsc_data(supabase):
    """현재 BSC 데이터의 name_tag 상태 확인"""
    print('=' * 80)
    print('📊 현재 BSC 데이터 상태 확인')
    print('=' * 80)
    
    # BSC chain_type 데이터 조회
    response = supabase.table('whale_address').select('*').eq('chain_type', 'BSC').execute()
    
    print(f'\n총 BSC 데이터: {len(response.data)}건')
    
    # name_tag별 통계
    from collections import defaultdict
    name_tag_counts = defaultdict(int)
    
    for record in response.data:
        name_tag = record.get('name_tag') or 'None'
        name_tag_counts[name_tag] += 1
    
    print('\n📋 name_tag별 통계:')
    for name_tag, count in sorted(name_tag_counts.items(), key=lambda x: x[1], reverse=True):
        print(f'  {name_tag}: {count}건')
    
    # 샘플 데이터 출력
    print('\n📋 샘플 데이터 (상위 5건):')
    for i, record in enumerate(response.data[:5], 1):
        print(f'  [{i}] ID={record.get("id")}, chain_type={record.get("chain_type")}, name_tag={record.get("name_tag")}, address={record.get("address", "")[:30]}...')
    
    return len(response.data), name_tag_counts


def update_bsc_name_tag_to_bnb(supabase):
    """BSC chain_type의 모든 레코드의 name_tag를 'BNB'로 업데이트"""
    print('\n' + '=' * 80)
    print('🔄 BSC name_tag를 "BNB"로 업데이트')
    print('=' * 80)
    
    # 먼저 현재 데이터 조회
    response = supabase.table('whale_address').select('id, chain_type, name_tag').eq('chain_type', 'BSC').execute()
    
    if not response.data:
        print('  ⚠️ 업데이트할 BSC 데이터가 없습니다.')
        return 0
    
    print(f'\n  📊 업데이트 대상: {len(response.data)}건')
    
    # 각 레코드를 업데이트
    updated_count = 0
    failed_count = 0
    
    # 배치로 업데이트 (Supabase는 개별 업데이트보다 배치가 효율적)
    batch_size = 100
    records_to_update = []
    
    for record in response.data:
        # name_tag가 이미 'BNB'인 경우 건너뛰기
        if record.get('name_tag') == 'BNB':
            continue
        
        records_to_update.append({
            'id': record.get('id'),
            'chain_type': record.get('chain_type'),
            'name_tag': 'BNB'
        })
    
    if not records_to_update:
        print('  ✅ 모든 레코드가 이미 name_tag="BNB"입니다.')
        return 0
    
    print(f'  📝 실제 업데이트 필요: {len(records_to_update)}건')
    
    # 배치로 업데이트
    for i in range(0, len(records_to_update), batch_size):
        batch = records_to_update[i:i + batch_size]
        
        try:
            # upsert로 업데이트 (id와 chain_type이 primary key)
            response = supabase.table('whale_address').upsert(
                batch,
                on_conflict='id,chain_type'
            ).execute()
            
            batch_updated = len(batch)
            updated_count += batch_updated
            print(f'    ✅ 배치 {i//batch_size + 1}: {batch_updated}건 업데이트 완료')
            
        except Exception as e:
            print(f'    ❌ 배치 {i//batch_size + 1} 업데이트 실패: {e}')
            failed_count += len(batch)
    
    print(f'\n  📊 업데이트 결과:')
    print(f'    - 성공: {updated_count}건')
    if failed_count > 0:
        print(f'    - 실패: {failed_count}건')
    
    return updated_count


def verify_update(supabase):
    """업데이트 결과 확인"""
    print('\n' + '=' * 80)
    print('✅ 업데이트 결과 확인')
    print('=' * 80)
    
    # BSC 데이터 조회
    response = supabase.table('whale_address').select('*').eq('chain_type', 'BSC').execute()
    
    print(f'\n  📊 총 BSC 데이터: {len(response.data)}건')
    
    # name_tag='BNB'인 데이터 확인
    bnb_count = sum(1 for r in response.data if r.get('name_tag') == 'BNB')
    other_count = len(response.data) - bnb_count
    
    print(f'  ✅ name_tag="BNB": {bnb_count}건')
    if other_count > 0:
        print(f'  ⚠️ name_tag!="BNB": {other_count}건')
        
        # 다른 name_tag가 있는 경우 출력
        from collections import defaultdict
        other_tags = defaultdict(int)
        for record in response.data:
            if record.get('name_tag') != 'BNB':
                tag = record.get('name_tag') or 'None'
                other_tags[tag] += 1
        
        print('\n  다른 name_tag 목록:')
        for tag, count in other_tags.items():
            print(f'    - {tag}: {count}건')
    else:
        print('  ✅ 모든 BSC 데이터의 name_tag가 "BNB"로 통일되었습니다.')
    
    # 샘플 데이터 출력
    print('\n  📋 샘플 데이터 (상위 5건):')
    for i, record in enumerate(response.data[:5], 1):
        print(f'    [{i}] ID={record.get("id")}, chain_type={record.get("chain_type")}, name_tag={record.get("name_tag")}')


def main():
    """메인 함수"""
    print('=' * 80)
    print('🐋 BSC 네트워크 name_tag를 "BNB"로 업데이트')
    print('=' * 80)
    
    try:
        supabase = get_supabase_client()
        
        # 1단계: 현재 상태 확인
        total_count, name_tag_counts = check_current_bsc_data(supabase)
        
        if total_count == 0:
            print('\n⚠️ BSC 데이터가 없습니다.')
            return
        
        # 2단계: 업데이트 실행
        updated_count = update_bsc_name_tag_to_bnb(supabase)
        
        # 3단계: 결과 확인
        verify_update(supabase)
        
        # 최종 요약
        print('\n' + '=' * 80)
        print('✅ 작업 완료')
        print('=' * 80)
        print(f'  📊 총 BSC 데이터: {total_count}건')
        print(f'  📊 업데이트된 레코드: {updated_count}건')
        
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

