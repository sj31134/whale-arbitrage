#!/usr/bin/env python3
"""
amount_usd 업데이트 실행 스크립트
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    return create_client(supabase_url, supabase_key)

def main():
    print("=" * 80)
    print("💰 amount_usd(달러 가치) 업데이트 시작")
    print("   - whale_transactions와 price_history를 매칭합니다.")
    print("   - 먼저 Supabase SQL Editor에서 'sql/rpc/update_amount_usd_rpc.sql'을 실행해주세요!")
    print("=" * 80)
    
    supabase = get_supabase_client()
    total_updated = 0
    
    while True:
        try:
            # RPC 호출
            response = supabase.rpc('update_amount_usd_batch', {'batch_limit': 5000}).execute()
            
            # 데이터가 없거나 None일 경우 처리
            if not response.data and response.data != 0:
                print("⚠️ 응답 없음 (함수가 없거나 타임아웃), 잠시 대기...")
                time.sleep(2)
                continue
                
            count = response.data
            
            if count == 0:
                print("\n✅ 모든 업데이트 완료! (더 이상 매칭되는 NULL 데이터 없음)")
                break
                
            total_updated += count
            print(f"\r🔄 업데이트 중... 누적 {total_updated:,}건 완료", end="", flush=True)
            
            # 너무 빠르면 DB 부하가 걸릴 수 있으니 약간의 텀
            time.sleep(0.5)
            
        except Exception as e:
            if 'Could not find the function' in str(e):
                print(f"\n❌ 오류: RPC 함수를 찾을 수 없습니다.")
                print("   sql/rpc/update_amount_usd_rpc.sql 내용을 Supabase SQL Editor에서 실행해주세요.")
                break
            print(f"\n❌ 오류 발생: {e}")
            time.sleep(5)
            
    print(f"\n🎉 총 {total_updated:,}건의 거래에 USD 가치가 입력되었습니다.")

if __name__ == '__main__':
    main()

