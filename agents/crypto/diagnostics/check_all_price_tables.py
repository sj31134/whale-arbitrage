#!/usr/bin/env python3
"""
모든 가격 테이블 데이터 확인 및 분석
- price_history
- price_history_btc
- price_history_eth
- whale_transactions
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

START_DATE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
END_DATE = datetime.now(timezone.utc)

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def check_table_exists(supabase, table_name):
    """테이블 존재 여부 확인"""
    try:
        response = supabase.table(table_name).select('*').limit(1).execute()
        return True
    except Exception as e:
        return False

def analyze_price_history(supabase):
    """price_history 테이블 분석"""
    print("=" * 80)
    print("📊 price_history 테이블 분석")
    print("=" * 80)
    
    try:
        # 전체 데이터 수
        response = supabase.table('price_history')\
            .select('*', count='exact')\
            .gte('timestamp', START_DATE.isoformat())\
            .lte('timestamp', END_DATE.isoformat())\
            .execute()
        
        total_count = response.count if hasattr(response, 'count') else len(response.data)
        print(f"\n총 레코드 수: {total_count:,}건")
        
        # 시간별 분포 확인 (샘플링)
        response = supabase.table('price_history')\
            .select('timestamp')\
            .gte('timestamp', START_DATE.isoformat())\
            .lte('timestamp', END_DATE.isoformat())\
            .order('timestamp', desc=False)\
            .limit(1000)\
            .execute()
        
        if response.data:
            timestamps = [datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')) for r in response.data]
            print(f"최초 타임스탬프: {timestamps[0]}")
            print(f"최종 타임스탬프: {timestamps[-1]}")
            
            # 시간 간격 분석
            if len(timestamps) > 1:
                intervals = [(timestamps[i+1] - timestamps[i]).total_seconds() / 3600 for i in range(len(timestamps)-1)]
                avg_interval = sum(intervals) / len(intervals)
                print(f"평균 시간 간격: {avg_interval:.2f}시간")
        
        # 코인별 분포
        response = supabase.table('price_history')\
            .select('crypto_id')\
            .gte('timestamp', START_DATE.isoformat())\
            .lte('timestamp', END_DATE.isoformat())\
            .execute()
        
        crypto_counts = defaultdict(int)
        for r in response.data:
            crypto_counts[r['crypto_id']] += 1
        
        print(f"\n코인별 분포 (상위 10개):")
        for crypto_id, count in sorted(crypto_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {crypto_id}: {count:,}건")
        
        return total_count
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return 0

def analyze_price_history_btc(supabase):
    """price_history_btc 테이블 분석"""
    print("\n" + "=" * 80)
    print("₿ price_history_btc 테이블 분석")
    print("=" * 80)
    
    if not check_table_exists(supabase, 'price_history_btc'):
        print("⚠️ 테이블이 존재하지 않습니다")
        return 0
    
    try:
        # 전체 데이터 수
        response = supabase.table('price_history_btc')\
            .select('*', count='exact')\
            .gte('timestamp', START_DATE.isoformat())\
            .lte('timestamp', END_DATE.isoformat())\
            .execute()
        
        total_count = response.count if hasattr(response, 'count') else len(response.data)
        print(f"\n총 레코드 수: {total_count:,}건")
        
        if total_count > 0:
            # 시간 범위 확인
            response = supabase.table('price_history_btc')\
                .select('timestamp')\
                .gte('timestamp', START_DATE.isoformat())\
                .lte('timestamp', END_DATE.isoformat())\
                .order('timestamp', desc=False)\
                .limit(1)\
                .execute()
            
            if response.data:
                first_ts = datetime.fromisoformat(response.data[0]['timestamp'].replace('Z', '+00:00'))
                print(f"최초 타임스탬프: {first_ts}")
            
            response = supabase.table('price_history_btc')\
                .select('timestamp')\
                .gte('timestamp', START_DATE.isoformat())\
                .lte('timestamp', END_DATE.isoformat())\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            if response.data:
                last_ts = datetime.fromisoformat(response.data[0]['timestamp'].replace('Z', '+00:00'))
                print(f"최종 타임스탬프: {last_ts}")
                
                # 예상 레코드 수 계산
                total_hours = int((last_ts - first_ts).total_seconds() / 3600) + 1
                coverage = (total_count / total_hours * 100) if total_hours > 0 else 0
                print(f"예상 레코드 수: {total_hours:,}건")
                print(f"커버리지: {coverage:.1f}%")
        
        return total_count
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return 0

def analyze_price_history_eth(supabase):
    """price_history_eth 테이블 분석"""
    print("\n" + "=" * 80)
    print("⟠ price_history_eth 테이블 분석")
    print("=" * 80)
    
    if not check_table_exists(supabase, 'price_history_eth'):
        print("⚠️ 테이블이 존재하지 않습니다")
        return 0
    
    try:
        # 전체 데이터 수
        response = supabase.table('price_history_eth')\
            .select('*', count='exact')\
            .gte('timestamp', START_DATE.isoformat())\
            .lte('timestamp', END_DATE.isoformat())\
            .execute()
        
        total_count = response.count if hasattr(response, 'count') else len(response.data)
        print(f"\n총 레코드 수: {total_count:,}건")
        
        if total_count > 0:
            # 시간 범위 확인
            response = supabase.table('price_history_eth')\
                .select('timestamp')\
                .gte('timestamp', START_DATE.isoformat())\
                .lte('timestamp', END_DATE.isoformat())\
                .order('timestamp', desc=False)\
                .limit(1)\
                .execute()
            
            if response.data:
                first_ts = datetime.fromisoformat(response.data[0]['timestamp'].replace('Z', '+00:00'))
                print(f"최초 타임스탬프: {first_ts}")
            
            response = supabase.table('price_history_eth')\
                .select('timestamp')\
                .gte('timestamp', START_DATE.isoformat())\
                .lte('timestamp', END_DATE.isoformat())\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            if response.data:
                last_ts = datetime.fromisoformat(response.data[0]['timestamp'].replace('Z', '+00:00'))
                print(f"최종 타임스탬프: {last_ts}")
                
                # 예상 레코드 수 계산
                total_hours = int((last_ts - first_ts).total_seconds() / 3600) + 1
                coverage = (total_count / total_hours * 100) if total_hours > 0 else 0
                print(f"예상 레코드 수: {total_hours:,}건")
                print(f"커버리지: {coverage:.1f}%")
        
        return total_count
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return 0

def analyze_whale_transactions(supabase):
    """whale_transactions 테이블 분석"""
    print("\n" + "=" * 80)
    print("🐋 whale_transactions 테이블 분석")
    print("=" * 80)
    
    try:
        # 전체 거래 수
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .gte('block_timestamp', START_DATE.isoformat())\
            .lte('block_timestamp', END_DATE.isoformat())\
            .execute()
        
        total_count = response.count if hasattr(response, 'count') else len(response.data)
        print(f"\n총 거래 수: {total_count:,}건")
        
        # 체인별 분포
        chains = ['ethereum', 'bsc', 'bitcoin']
        print(f"\n체인별 분포:")
        for chain in chains:
            if chain == 'bitcoin':
                response = supabase.table('whale_transactions')\
                    .select('*', count='exact')\
                    .eq('coin_symbol', 'BTC')\
                    .gte('block_timestamp', START_DATE.isoformat())\
                    .lte('block_timestamp', END_DATE.isoformat())\
                    .execute()
            else:
                response = supabase.table('whale_transactions')\
                    .select('*', count='exact')\
                    .eq('chain', chain)\
                    .gte('block_timestamp', START_DATE.isoformat())\
                    .lte('block_timestamp', END_DATE.isoformat())\
                    .execute()
            
            count = response.count if hasattr(response, 'count') else len(response.data)
            print(f"  {chain}: {count:,}건")
        
        # 시간별 분포 확인
        response = supabase.table('whale_transactions')\
            .select('block_timestamp')\
            .gte('block_timestamp', START_DATE.isoformat())\
            .lte('block_timestamp', END_DATE.isoformat())\
            .order('block_timestamp', desc=False)\
            .limit(1)\
            .execute()
        
        if response.data:
            first_ts = response.data[0]['block_timestamp']
            print(f"\n최초 거래 타임스탬프: {first_ts}")
        
        response = supabase.table('whale_transactions')\
            .select('block_timestamp')\
            .gte('block_timestamp', START_DATE.isoformat())\
            .lte('block_timestamp', END_DATE.isoformat())\
            .order('block_timestamp', desc=True)\
            .limit(1)\
            .execute()
        
        if response.data:
            last_ts = response.data[0]['block_timestamp']
            print(f"최종 거래 타임스탬프: {last_ts}")
        
        return total_count
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return 0

def main():
    """메인 함수"""
    print("=" * 80)
    print("📊 모든 가격 테이블 데이터 확인")
    print("=" * 80)
    print(f"\n검증 기간: {START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')}")
    print(f"예상 시간대 수: {int((END_DATE - START_DATE).total_seconds() / 3600):,}시간")
    
    try:
        supabase = get_supabase_client()
        
        # 각 테이블 분석
        ph_count = analyze_price_history(supabase)
        btc_count = analyze_price_history_btc(supabase)
        eth_count = analyze_price_history_eth(supabase)
        wt_count = analyze_whale_transactions(supabase)
        
        # 요약
        print("\n" + "=" * 80)
        print("📋 요약")
        print("=" * 80)
        print(f"\nprice_history: {ph_count:,}건")
        print(f"price_history_btc: {btc_count:,}건")
        print(f"price_history_eth: {eth_count:,}건")
        print(f"whale_transactions: {wt_count:,}건")
        
        # 부족한 부분 식별
        total_hours = int((END_DATE - START_DATE).total_seconds() / 3600)
        print(f"\n⚠️ 부족한 부분 분석:")
        
        if btc_count == 0:
            print(f"  - price_history_btc: 테이블이 비어있거나 존재하지 않음")
        elif btc_count < total_hours:
            print(f"  - price_history_btc: {total_hours - btc_count:,}시간 데이터 부족")
        
        if eth_count == 0:
            print(f"  - price_history_eth: 테이블이 비어있거나 존재하지 않음")
        elif eth_count < total_hours:
            print(f"  - price_history_eth: {total_hours - eth_count:,}시간 데이터 부족")
        
        print("\n✅ 분석 완료")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

