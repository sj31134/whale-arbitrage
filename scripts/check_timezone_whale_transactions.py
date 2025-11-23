#!/usr/bin/env python3
"""
whale_transactions 테이블의 block_timestamp 타임존 확인
UTC 기준인지 확인 (블록체인은 일반적으로 UTC 사용)
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
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

def check_timezone_patterns(supabase):
    """whale_transactions 테이블의 block_timestamp 패턴 분석"""
    print("=" * 70)
    print("📊 whale_transactions 테이블 타임존 분석")
    print("=" * 70)
    
    # 1. 최근 데이터 샘플 조회
    print("\n1. 최근 데이터 샘플 조회 (최근 100건)...")
    try:
        response = supabase.table('whale_transactions')\
            .select('block_timestamp, coin_symbol, chain')\
            .order('block_timestamp', desc=True)\
            .limit(100)\
            .execute()
        
        if not response.data:
            print("   ⚠️ 데이터가 없습니다.")
            return
        
        transactions = response.data
        print(f"   ✅ {len(transactions)}건 조회 완료")
        
    except Exception as e:
        print(f"   ❌ 조회 실패: {e}")
        return
    
    # 2. 시간대별 분포 분석
    print("\n2. 시간대별 분포 분석 (UTC 기준)...")
    hour_distribution = {}
    chain_distribution = {}
    
    for tx in transactions:
        ts_str = tx.get('block_timestamp')
        chain = tx.get('chain', 'unknown')
        coin = tx.get('coin_symbol', 'unknown')
        
        if not ts_str:
            continue
        
        try:
            # 타임스탬프 파싱
            if isinstance(ts_str, str):
                if 'T' in ts_str:
                    dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                elif ts_str.isdigit():
                    # Unix timestamp
                    dt = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)
                elif '.' in ts_str and ' ' in ts_str:
                    # "2025.9.30 14:09" 형식 처리
                    try:
                        date_part, time_part = ts_str.split(' ')
                        year, month, day = map(int, date_part.split('.'))
                        hour, minute = map(int, time_part.split(':'))
                        dt = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
                    except:
                        dt = datetime.fromisoformat(ts_str)
                else:
                    dt = datetime.fromisoformat(ts_str)
            else:
                dt = ts_str
            
            # UTC로 변환
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            
            hour = dt.hour
            hour_distribution[hour] = hour_distribution.get(hour, 0) + 1
            
            if chain not in chain_distribution:
                chain_distribution[chain] = {}
            chain_distribution[chain][hour] = chain_distribution[chain].get(hour, 0) + 1
            
        except Exception as e:
            print(f"   ⚠️ 타임스탬프 파싱 실패: {ts_str}, {e}")
            continue
    
    # 시간대별 분포 출력
    print("\n   전체 시간대별 데이터 분포:")
    for hour in sorted(hour_distribution.keys()):
        count = hour_distribution[hour]
        bar = '█' * (count // 2)
        print(f"   {hour:2d}시: {count:3d}건 {bar}")
    
    # 3. 체인별 분석
    print("\n3. 체인별 시간대 분포...")
    for chain, hours in chain_distribution.items():
        print(f"\n   [{chain}]")
        for hour in sorted(hours.keys()):
            count = hours[hour]
            bar = '█' * (count // 2)
            print(f"      {hour:2d}시: {count:3d}건 {bar}")
    
    # 4. 샘플 데이터 확인
    print("\n4. 샘플 데이터 확인...")
    print("\n   최근 10건의 block_timestamp:")
    for i, tx in enumerate(transactions[:10], 1):
        ts_str = tx.get('block_timestamp')
        coin = tx.get('coin_symbol', 'unknown')
        chain = tx.get('chain', 'unknown')
        
        try:
            if isinstance(ts_str, str):
                if 'T' in ts_str:
                    dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                elif ts_str.isdigit():
                    dt = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)
                elif '.' in ts_str and ' ' in ts_str:
                    # "2025.9.30 14:09" 형식 처리
                    try:
                        date_part, time_part = ts_str.split(' ')
                        year, month, day = map(int, date_part.split('.'))
                        hour, minute = map(int, time_part.split(':'))
                        dt = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
                    except:
                        dt = datetime.fromisoformat(ts_str)
                else:
                    dt = datetime.fromisoformat(ts_str)
            else:
                dt = ts_str
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            
            kst_dt = dt.astimezone(timezone(timedelta(hours=9)))
            
            print(f"   {i:2d}. {coin:6s} ({chain:10s})")
            print(f"       UTC: {dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"       KST: {kst_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
        except Exception as e:
            print(f"   {i:2d}. 파싱 실패: {ts_str}")
    
    # 5. 결론
    print("\n" + "=" * 70)
    print("📝 분석 결론")
    print("=" * 70)
    
    # 블록체인은 일반적으로 UTC를 사용하므로, 시간대가 고르게 분포되어야 함
    # 특정 시간대에 집중되어 있지 않으면 UTC 기준으로 저장된 것으로 판단
    max_hour_count = max(hour_distribution.values()) if hour_distribution else 0
    total_count = sum(hour_distribution.values())
    avg_count = total_count / 24 if total_count > 0 else 0
    
    if not hour_distribution:
        print("⚠️ 파싱 가능한 타임스탬프가 없습니다.")
        print("   타임스탬프 형식을 확인해주세요.")
    elif max_hour_count < avg_count * 3:
        print("✅ 시간대가 고르게 분포됨 → UTC 기준으로 저장된 것으로 보임")
        print("   (블록체인 거래는 시간대와 무관하게 발생하므로 고르게 분포되어야 함)")
    else:
        print("⚠️ 특정 시간대에 집중됨 → 추가 확인 필요")
        max_hour = max(hour_distribution.items(), key=lambda x: x[1])[0]
        print(f"   가장 많은 시간대: UTC {max_hour}시 ({max_hour_count}건)")
    
    print(f"\n   - 총 데이터: {total_count}건")
    print(f"   - 평균 시간대별 데이터: {avg_count:.1f}건")
    print(f"   - 최대 시간대 데이터: {max_hour_count}건")

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

