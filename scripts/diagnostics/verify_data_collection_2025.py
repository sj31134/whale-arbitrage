#!/usr/bin/env python3
"""
2025년 1월 1일부터 오늘까지 수집된 데이터의 완전성 검증
- price_history: 코인별, 날짜별 데이터 수 확인
- whale_transactions: 코인별, 날짜별 거래 수 확인
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 검증 기간
START_DATE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
END_DATE = datetime.now(timezone.utc)

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def verify_price_history(supabase):
    """price_history 테이블 데이터 검증"""
    print("=" * 70)
    print("📊 price_history 데이터 검증")
    print("=" * 70)
    
    # cryptocurrencies 테이블에서 코인 정보 조회
    try:
        crypto_response = supabase.table('cryptocurrencies')\
            .select('id, symbol')\
            .execute()
        
        crypto_map = {c['id']: c['symbol'] for c in crypto_response.data}
    except Exception as e:
        print(f"❌ cryptocurrencies 조회 실패: {e}")
        return
    
    print(f"\n검증 기간: {START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')}")
    print(f"예상 시간대 수: {(END_DATE - START_DATE).days * 24}시간")
    
    results = {}
    
    for crypto_id, symbol in crypto_map.items():
        try:
            # 해당 코인의 데이터 조회
            response = supabase.table('price_history')\
                .select('timestamp', count='exact')\
                .eq('crypto_id', crypto_id)\
                .gte('timestamp', START_DATE.isoformat())\
                .lte('timestamp', END_DATE.isoformat())\
                .execute()
            
            count = response.count if hasattr(response, 'count') else len(response.data) if response.data else 0
            
            # 날짜별 데이터 수 확인
            if response.data:
                dates = defaultdict(int)
                for row in response.data:
                    ts_str = row['timestamp']
                    try:
                        if isinstance(ts_str, str):
                            if 'T' in ts_str:
                                dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                            else:
                                dt = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)
                        else:
                            dt = ts_str
                        
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        else:
                            dt = dt.astimezone(timezone.utc)
                        
                        date_key = dt.date()
                        dates[date_key] += 1
                    except:
                        pass
                
                days_with_data = len(dates)
                total_days = (END_DATE.date() - START_DATE.date()).days + 1
                coverage = (days_with_data / total_days * 100) if total_days > 0 else 0
                
                results[symbol] = {
                    'total': count,
                    'days_with_data': days_with_data,
                    'total_days': total_days,
                    'coverage': coverage
                }
            else:
                results[symbol] = {
                    'total': 0,
                    'days_with_data': 0,
                    'total_days': (END_DATE.date() - START_DATE.date()).days + 1,
                    'coverage': 0
                }
                
        except Exception as e:
            print(f"⚠️ {symbol} 검증 실패: {e}")
            results[symbol] = {'error': str(e)}
    
    # 결과 출력
    print("\n📈 코인별 데이터 현황:")
    print(f"\n{'코인':<8} {'총 데이터':<12} {'데이터 있는 날':<15} {'전체 날':<10} {'커버리지':<10}")
    print("-" * 70)
    
    for symbol, result in sorted(results.items()):
        if 'error' in result:
            print(f"{symbol:<8} 오류: {result['error']}")
        else:
            print(f"{symbol:<8} {result['total']:>10,}건  {result['days_with_data']:>6}일 / {result['total_days']:>6}일  {result['coverage']:>6.1f}%")
    
    return results

def verify_whale_transactions(supabase):
    """whale_transactions 테이블 데이터 검증"""
    print("\n" + "=" * 70)
    print("🐋 whale_transactions 데이터 검증")
    print("=" * 70)
    
    print(f"\n검증 기간: {START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')}")
    
    try:
        # 코인별 거래 수 조회
        response = supabase.table('whale_transactions')\
            .select('coin_symbol, block_timestamp', count='exact')\
            .gte('block_timestamp', START_DATE.isoformat())\
            .lte('block_timestamp', END_DATE.isoformat())\
            .execute()
        
        total_count = response.count if hasattr(response, 'count') else len(response.data) if response.data else 0
        
        # 코인별 집계
        coin_counts = defaultdict(int)
        coin_dates = defaultdict(set)
        
        if response.data:
            for row in response.data:
                coin = row.get('coin_symbol', 'UNKNOWN')
                coin_counts[coin] += 1
                
                ts_str = row.get('block_timestamp')
                if ts_str:
                    try:
                        if isinstance(ts_str, str):
                            if 'T' in ts_str:
                                dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                            elif ts_str.isdigit():
                                dt = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)
                            else:
                                dt = datetime.fromisoformat(ts_str)
                        else:
                            dt = ts_str
                        
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        else:
                            dt = dt.astimezone(timezone.utc)
                        
                        date_key = dt.date()
                        if START_DATE.date() <= date_key <= END_DATE.date():
                            coin_dates[coin].add(date_key)
                    except:
                        pass
        
        # 결과 출력
        print(f"\n총 거래 수: {total_count:,}건")
        print(f"\n{'코인':<8} {'거래 수':<12} {'데이터 있는 날':<15} {'전체 날':<10} {'커버리지':<10}")
        print("-" * 70)
        
        total_days = (END_DATE.date() - START_DATE.date()).days + 1
        
        for coin in sorted(coin_counts.keys()):
            count = coin_counts[coin]
            days = len(coin_dates[coin])
            coverage = (days / total_days * 100) if total_days > 0 else 0
            print(f"{coin:<8} {count:>10,}건  {days:>6}일 / {total_days:>6}일  {coverage:>6.1f}%")
        
        return {
            'total': total_count,
            'by_coin': dict(coin_counts),
            'by_coin_dates': {k: len(v) for k, v in coin_dates.items()}
        }
        
    except Exception as e:
        print(f"❌ 검증 실패: {e}")
        return None

def generate_report(price_results, whale_results):
    """검증 리포트 생성"""
    print("\n" + "=" * 70)
    print("📋 검증 리포트 요약")
    print("=" * 70)
    
    # price_history 요약
    if price_results:
        total_coins = len(price_results)
        coins_with_data = sum(1 for r in price_results.values() if 'total' in r and r['total'] > 0)
        avg_coverage = sum(r.get('coverage', 0) for r in price_results.values() if 'coverage' in r) / total_coins if total_coins > 0 else 0
        
        print(f"\n📊 price_history:")
        print(f"   - 검증한 코인: {total_coins}개")
        print(f"   - 데이터 있는 코인: {coins_with_data}개")
        print(f"   - 평균 커버리지: {avg_coverage:.1f}%")
    
    # whale_transactions 요약
    if whale_results:
        print(f"\n🐋 whale_transactions:")
        print(f"   - 총 거래 수: {whale_results.get('total', 0):,}건")
        print(f"   - 코인 종류: {len(whale_results.get('by_coin', {}))}개")
    
    print("\n" + "=" * 70)

def main():
    """메인 함수"""
    try:
        supabase = get_supabase_client()
        
        # price_history 검증
        price_results = verify_price_history(supabase)
        
        # whale_transactions 검증
        whale_results = verify_whale_transactions(supabase)
        
        # 리포트 생성
        generate_report(price_results, whale_results)
        
        print("\n✅ 검증 완료")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

