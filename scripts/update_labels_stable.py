#!/usr/bin/env python3
"""
Supabase 타임아웃 회피형 라벨 업데이트 스크립트
작은 배치(Short-lived Request)를 반복 호출하여 안정적으로 대용량 처리
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
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    # 타임아웃 60초 (한 번 요청은 금방 끝나므로 충분함)
    return create_client(supabase_url, supabase_key)

def main():
    print("=" * 80)
    print("🚀 타임아웃 없는 안정적인 라벨 업데이트 시작")
    print("=" * 80)
    
    supabase = get_supabase_client()
    
    total_from_updated = 0
    total_to_updated = 0
    batch_size = 5000  # 5000건씩 처리 (빠르고 안전)
    
    start_time = time.time()
    
    while True:
        try:
            # RPC 함수 호출 (딱 한 번의 배치만 실행하고 리턴)
            response = supabase.rpc('update_labels_one_batch', {'batch_size': batch_size}).execute()
            
            if not response.data:
                print("⚠️ 응답 없음, 재시도...")
                time.sleep(1)
                continue
                
            result = response.data[0]
            updated_count = result['updated_count']
            label_type = result['label_type']
            
            if updated_count == 0:
                print("\n✅ 모든 업데이트 완료!")
                break
            
            if label_type == 'from_label':
                total_from_updated += updated_count
            else:
                total_to_updated += updated_count
                
            elapsed = time.time() - start_time
            total = total_from_updated + total_to_updated
            rate = total / elapsed if elapsed > 0 else 0
            
            print(f"\r🔄 진행 중: {total:,}건 완료 ({label_type}: +{updated_count}) - 속도: {rate:.0f}건/초", end="", flush=True)
            
            # 너무 빠른 요청으로 인한 부하 방지 (선택 사항)
            # time.sleep(0.1) 
            
        except Exception as e:
            print(f"\n❌ 오류 발생 (잠시 대기 후 재시도): {e}")
            time.sleep(3)
            
    print("\n" + "=" * 80)
    print(f"🎉 최종 결과")
    print(f"   - from_label 업데이트: {total_from_updated:,}건")
    print(f"   - to_label 업데이트: {total_to_updated:,}건")
    print(f"   - 총 소요 시간: {time.time() - start_time:.1f}초")
    print("=" * 80)

if __name__ == '__main__':
    main()

