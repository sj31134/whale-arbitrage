#!/usr/bin/env python3
"""
RPC 함수를 이용한 안정적인 후처리 스크립트
"""

import os
import sys
import time
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

def main():
    print("=" * 80)
    print("🚀 RPC 기반 라벨링 후처리 시작")
    print("=" * 80)
    
    supabase = get_supabase_client()
    
    total_stats = {
        'from_unknown': 0,
        'to_unknown': 0,
        'direction_buy': 0,
        'direction_sell': 0,
        'direction_move': 0
    }
    
    batch_size = 5000  # DB 내부 처리는 빠르므로 좀 크게 잡아도 됨
    start_time = time.time()
    
    while True:
        try:
            response = supabase.rpc('update_post_process_labels', {'batch_size': batch_size}).execute()
            
            if not response.data:
                print("⚠️ 응답 없음, 재시도...")
                time.sleep(1)
                continue
                
            result = response.data[0]
            updated_count = result['updated_count']
            update_type = result['update_type']
            
            if updated_count == 0 and update_type == 'direction_move':
                # 마지막 단계인 MOVE까지 0건이면 정말 끝난 것
                # 하지만 direction_move가 0이라도 앞단계가 남아있을 수 있으므로
                # 함수 로직상 하나라도 처리되면 리턴되므로, 0 리턴은 진짜 끝
                print("\n✅ 모든 업데이트 완료!")
                break
            
            if updated_count == 0: # 혹시 모르니 0건이면 종료
                 print("\n✅ 더 이상 처리할 데이터가 없습니다.")
                 break

            total_stats[update_type] += updated_count
            
            elapsed = time.time() - start_time
            total = sum(total_stats.values())
            rate = total / elapsed if elapsed > 0 else 0
            
            print(f"\r🔄 진행 중: {total:,}건 완료 ({update_type}: +{updated_count}) - 속도: {rate:.0f}건/초", end="", flush=True)
            
        except Exception as e:
            print(f"\n❌ 오류 발생 (잠시 대기 후 재시도): {e}")
            time.sleep(2)
            
    print("\n" + "=" * 80)
    print(f"🎉 최종 결과")
    for k, v in total_stats.items():
        print(f"   - {k}: {v:,}건")
    print(f"   - 총 소요 시간: {time.time() - start_time:.1f}초")
    print("=" * 80)

if __name__ == '__main__':
    main()

