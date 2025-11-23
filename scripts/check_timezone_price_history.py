#!/usr/bin/env python3
"""
price_history 테이블의 timestamp 타임존 확인
9시 기준 데이터가 UTC+9(KST)인지 UTC인지 확인
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

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

def check_timezone_patterns(supabase):
    """price_history 테이블의 timestamp 패턴 분석"""
    print("=" * 70)
    print("📊 price_history 테이블 타임존 분석")
    print("=" * 70)
    
    # 1. 최근 데이터 샘플 조회
    print("\n1. 최근 데이터 샘플 조회 (최근 100건)...")
    try:
        response = supabase.table('price_history')\
            .select('timestamp, crypto_id')\
            .order('timestamp', desc=True)\
            .limit(100)\
            .execute()
        
        if not response.data:
            print("   ⚠️ 데이터가 없습니다.")
            return
        
        timestamps = [row['timestamp'] for row in response.data]
        print(f"   ✅ {len(timestamps)}건 조회 완료")
        
    except Exception as e:
        print(f"   ❌ 조회 실패: {e}")
        return
    
    # 2. 시간대별 분포 분석
    print("\n2. 시간대별 분포 분석...")
    hour_distribution = {}
    
    for ts_str in timestamps:
        try:
            # ISO 형식 문자열을 datetime으로 변환
            if isinstance(ts_str, str):
                if 'T' in ts_str:
                    dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                else:
                    dt = datetime.fromtimestamp(int(ts_str))
            else:
                dt = ts_str
            
            # UTC로 변환 (타임존 정보가 있으면)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            
            hour = dt.hour
            hour_distribution[hour] = hour_distribution.get(hour, 0) + 1
            
        except Exception as e:
            print(f"   ⚠️ 타임스탬프 파싱 실패: {ts_str}, {e}")
            continue
    
    # 시간대별 분포 출력
    print("\n   시간대별 데이터 분포 (UTC 기준):")
    for hour in sorted(hour_distribution.keys()):
        count = hour_distribution[hour]
        bar = '█' * (count // 2)
        print(f"   {hour:2d}시: {count:3d}건 {bar}")
    
    # 3. 9시 데이터 확인
    print("\n3. 9시 기준 데이터 확인...")
    hour_9_count = hour_distribution.get(9, 0)
    hour_0_count = hour_distribution.get(0, 0)  # UTC 0시 = KST 9시
    
    print(f"   UTC 9시 데이터: {hour_9_count}건")
    print(f"   UTC 0시 데이터: {hour_0_count}건 (KST 9시에 해당)")
    
    # 4. 코인별 9시 데이터 확인
    print("\n4. 코인별 9시 데이터 확인...")
    try:
        # cryptocurrencies 테이블에서 코인 정보 조회
        crypto_response = supabase.table('cryptocurrencies')\
            .select('id, symbol')\
            .execute()
        
        crypto_map = {c['id']: c['symbol'] for c in crypto_response.data}
        
        # 각 코인별로 9시 데이터 확인
        for crypto_id, symbol in crypto_map.items():
            coin_data = [row for row in response.data if row['crypto_id'] == crypto_id]
            if not coin_data:
                continue
            
            hour_9_data = []
            hour_0_data = []
            
            for row in coin_data:
                ts_str = row['timestamp']
                try:
                    if isinstance(ts_str, str):
                        if 'T' in ts_str:
                            dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        else:
                            dt = datetime.fromtimestamp(int(ts_str))
                    else:
                        dt = ts_str
                    
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    else:
                        dt = dt.astimezone(timezone.utc)
                    
                    if dt.hour == 9:
                        hour_9_data.append(dt)
                    elif dt.hour == 0:
                        hour_0_data.append(dt)
                        
                except:
                    continue
            
            if hour_9_data or hour_0_data:
                print(f"   {symbol:6s}: UTC 9시 {len(hour_9_data):3d}건, UTC 0시 {len(hour_0_data):3d}건")
                
                # 샘플 출력
                if hour_9_data:
                    sample = sorted(hour_9_data)[-1]
                    print(f"            UTC 9시 샘플: {sample.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    kst_sample = sample.astimezone(timezone(timedelta(hours=9)))
                    print(f"            KST 변환:     {kst_sample.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                
                if hour_0_data:
                    sample = sorted(hour_0_data)[-1]
                    print(f"            UTC 0시 샘플: {sample.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    kst_sample = sample.astimezone(timezone(timedelta(hours=9)))
                    print(f"            KST 변환:     {kst_sample.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
    except Exception as e:
        print(f"   ⚠️ 코인별 분석 실패: {e}")
    
    # 5. 결론
    print("\n" + "=" * 70)
    print("📝 분석 결론")
    print("=" * 70)
    
    if hour_0_count > hour_9_count * 2:
        print("✅ UTC 0시 데이터가 많음 → KST 9시 기준으로 수집된 것으로 보임")
        print("   (UTC 0시 = KST 9시)")
    elif hour_9_count > hour_0_count * 2:
        print("✅ UTC 9시 데이터가 많음 → UTC 9시 기준으로 수집된 것으로 보임")
        print("   (UTC 9시 = KST 18시)")
    else:
        print("⚠️ 명확한 패턴이 보이지 않음. 추가 분석 필요")
    
    print(f"\n   - UTC 9시 데이터: {hour_9_count}건")
    print(f"   - UTC 0시 데이터: {hour_0_count}건")
    print(f"   - 총 데이터: {len(timestamps)}건")

def main():
    """메인 함수"""
    try:
        supabase = get_supabase_client()
        check_timezone_patterns(supabase)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

