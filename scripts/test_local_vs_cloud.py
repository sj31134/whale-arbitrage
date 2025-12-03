#!/usr/bin/env python3
"""
로컬 vs 클라우드 서비스 비교 테스트 스크립트

각 페이지와 기능을 1:1로 비교하여 차이점을 찾습니다.
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import os

# 프로젝트 루트 경로
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "utils"))
sys.path.insert(0, str(ROOT))

from data_loader import DataLoader
from risk_predictor import RiskPredictor

def test_data_loader(coin='BTC', days=30):
    """DataLoader 테스트"""
    print(f"\n{'='*80}")
    print(f"[1] DataLoader 테스트 - {coin}")
    print(f"{'='*80}")
    
    loader = DataLoader()
    
    # 환경 정보
    print(f"\n[환경 정보]")
    print(f"  - Supabase 사용: {loader.use_supabase}")
    print(f"  - DB 경로: {loader.db_path}")
    print(f"  - DB 파일 존재: {loader.db_path.exists() if loader.db_path else 'N/A'}")
    
    # 최근 N일 데이터 로드
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    print(f"\n[데이터 로드 테스트]")
    print(f"  - 기간: {start_date} ~ {end_date}")
    
    try:
        df = loader.load_risk_data(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            coin=coin
        )
        
        print(f"  - 로드된 행 수: {len(df)}")
        print(f"  - 컬럼 수: {len(df.columns)}")
        print(f"  - 날짜 범위: {df['date'].min()} ~ {df['date'].max()}" if not df.empty else "  - 날짜 범위: 데이터 없음")
        
        if df.empty:
            print(f"  ❌ 데이터가 비어있습니다!")
            return False
        
        # 핵심 컬럼 확인
        core_cols = ['avg_funding_rate', 'sum_open_interest', 'volatility_24h']
        missing_cols = [col for col in core_cols if col not in df.columns]
        if missing_cols:
            print(f"  ⚠️ 누락된 핵심 컬럼: {missing_cols}")
        
        # 데이터 유효성 확인
        for col in core_cols:
            if col in df.columns:
                non_null_count = df[col].notna().sum()
                print(f"  - {col}: {non_null_count}/{len(df)} 행에 데이터 있음")
        
        print(f"  ✅ 데이터 로드 성공")
        return True
        
    except Exception as e:
        print(f"  ❌ 데이터 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_risk_predictor(coin='BTC', target_date=None):
    """RiskPredictor 테스트"""
    print(f"\n{'='*80}")
    print(f"[2] RiskPredictor 테스트 - {coin}")
    print(f"{'='*80}")
    
    if target_date is None:
        target_date = datetime.now().date() - timedelta(days=1)
    
    print(f"\n[예측 테스트]")
    print(f"  - 타겟 날짜: {target_date}")
    
    try:
        predictor = RiskPredictor(coin=coin)
        
        result = predictor.predict_risk(target_date.strftime("%Y-%m-%d"), coin)
        
        if result['success']:
            print(f"  ✅ 예측 성공")
            print(f"  - 리스크 점수: {result['data']['risk_score']:.2f}%")
            print(f"  - 고변동성 확률: {result['data']['high_volatility_prob']*100:.2f}%")
            print(f"  - 청산 리스크: {result['data']['liquidation_risk']:.2f}%")
            return True
        else:
            print(f"  ❌ 예측 실패: {result.get('error', '알 수 없음')}")
            return False
            
    except Exception as e:
        print(f"  ❌ 예측 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_available_dates(coin='BTC'):
    """사용 가능한 날짜 확인"""
    print(f"\n{'='*80}")
    print(f"[3] 사용 가능한 날짜 확인 - {coin}")
    print(f"{'='*80}")
    
    try:
        loader = DataLoader()
        
        success, result = loader.get_available_dates(coin)
        
        if success:
            print(f"  ✅ 날짜 조회 성공")
            print(f"  - 최소 날짜: {result['min_date']}")
            print(f"  - 최대 날짜: {result['max_date']}")
            print(f"  - 총 일수: {result['total_days']}")
            return True
        else:
            print(f"  ❌ 날짜 조회 실패: {result}")
            return False
            
    except Exception as e:
        print(f"  ❌ 날짜 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_supabase_connection():
    """Supabase 연결 테스트"""
    print(f"\n{'='*80}")
    print(f"[4] Supabase 연결 테스트")
    print(f"{'='*80}")
    
    try:
        loader = DataLoader()
        
        if not loader.use_supabase:
            print(f"  ℹ️ Supabase 사용 안 함 (로컬 환경)")
            return True
        
        print(f"  - Supabase 사용: {loader.use_supabase}")
        
        supabase = loader._get_supabase_client()
        
        if supabase:
            print(f"  ✅ Supabase 클라이언트 생성 성공")
            
            # 간단한 쿼리 테스트
            try:
                response = supabase.table("binance_futures_metrics").select("date").limit(1).execute()
                if response.data:
                    print(f"  ✅ Supabase 쿼리 성공")
                    return True
                else:
                    print(f"  ⚠️ Supabase 쿼리 결과 없음")
                    return False
            except Exception as e:
                print(f"  ❌ Supabase 쿼리 실패: {e}")
                return False
        else:
            print(f"  ❌ Supabase 클라이언트 생성 실패")
            return False
            
    except Exception as e:
        print(f"  ❌ Supabase 연결 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_futures_extended_metrics(coin='BTC'):
    """Futures Extended Metrics 테스트"""
    print(f"\n{'='*80}")
    print(f"[5] Futures Extended Metrics 테스트 - {coin}")
    print(f"{'='*80}")
    
    symbol = f"{coin}USDT"
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    print(f"\n[데이터 로드 테스트]")
    print(f"  - 심볼: {symbol}")
    print(f"  - 기간: {start_date} ~ {end_date}")
    
    try:
        loader = DataLoader()
        
        df = loader.load_futures_extended_metrics(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            symbol=symbol
        )
        
        print(f"  - 로드된 행 수: {len(df)}")
        
        if df.empty:
            print(f"  ❌ 데이터가 비어있습니다!")
            return False
        
        print(f"  - 컬럼: {list(df.columns)}")
        print(f"  - 날짜 범위: {df['date'].min()} ~ {df['date'].max()}")
        
        # 핵심 컬럼 확인
        core_cols = ['taker_buy_sell_ratio', 'long_short_ratio', 'top_trader_long_short_ratio']
        for col in core_cols:
            if col in df.columns:
                non_null_count = df[col].notna().sum()
                print(f"  - {col}: {non_null_count}/{len(df)} 행에 데이터 있음")
        
        print(f"  ✅ 데이터 로드 성공")
        return True
        
    except Exception as e:
        print(f"  ❌ 데이터 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 실행"""
    print("="*80)
    print("로컬 vs 클라우드 서비스 비교 테스트")
    print("="*80)
    print(f"\n테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"환경: {'로컬' if not os.path.exists('/mount/src') else 'Streamlit Cloud'}")
    
    results = {}
    
    # BTC 테스트
    print("\n" + "="*80)
    print("BTC 테스트")
    print("="*80)
    
    results['btc_supabase'] = test_supabase_connection()
    results['btc_available_dates'] = test_available_dates('BTC')
    results['btc_data_loader'] = test_data_loader('BTC', days=30)
    results['btc_risk_predictor'] = test_risk_predictor('BTC')
    results['btc_futures_extended'] = test_futures_extended_metrics('BTC')
    
    # ETH 테스트
    print("\n" + "="*80)
    print("ETH 테스트")
    print("="*80)
    
    results['eth_available_dates'] = test_available_dates('ETH')
    results['eth_data_loader'] = test_data_loader('ETH', days=30)
    results['eth_risk_predictor'] = test_risk_predictor('ETH')
    results['eth_futures_extended'] = test_futures_extended_metrics('ETH')
    
    # 결과 요약
    print("\n" + "="*80)
    print("테스트 결과 요약")
    print("="*80)
    
    for test_name, result in results.items():
        status = "✅ 통과" if result else "❌ 실패"
        print(f"  {test_name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    print(f"\n총 {total}개 테스트 중 {passed}개 통과, {failed}개 실패")
    
    if failed > 0:
        print("\n⚠️ 실패한 테스트가 있습니다. 위의 상세 로그를 확인하세요.")
        return 1
    else:
        print("\n✅ 모든 테스트 통과!")
        return 0

if __name__ == "__main__":
    sys.exit(main())

