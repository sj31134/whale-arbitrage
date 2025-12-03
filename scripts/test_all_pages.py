#!/usr/bin/env python3
"""
모든 페이지 기능 테스트 스크립트

로컬과 클라우드 서비스를 비교하기 위한 종합 테스트
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

def test_data_loader_functions(coin='BTC'):
    """DataLoader의 모든 함수 테스트"""
    print(f"\n{'='*80}")
    print(f"[DataLoader 테스트] - {coin}")
    print(f"{'='*80}")
    
    from data_loader import DataLoader
    
    loader = DataLoader()
    
    # 환경 정보
    print(f"\n[환경 정보]")
    print(f"  - Supabase 사용: {loader.use_supabase}")
    print(f"  - DB 경로: {loader.db_path}")
    
    # 1. get_available_dates 테스트
    print(f"\n[1] get_available_dates 테스트")
    try:
        min_date, max_date = loader.get_available_dates(coin)
        if min_date and max_date:
            print(f"  ✅ 성공: {min_date} ~ {max_date}")
        else:
            print(f"  ❌ 실패: 날짜 범위를 가져올 수 없음")
            return False
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. load_risk_data 테스트
    print(f"\n[2] load_risk_data 테스트")
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        df = loader.load_risk_data(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            coin=coin
        )
        
        if len(df) > 0:
            print(f"  ✅ 성공: {len(df)}행 로드")
            print(f"    - 날짜 범위: {df['date'].min()} ~ {df['date'].max()}")
            print(f"    - 컬럼: {list(df.columns)}")
        else:
            print(f"  ❌ 실패: 데이터가 비어있음")
            return False
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. load_futures_extended_metrics 테스트
    print(f"\n[3] load_futures_extended_metrics 테스트")
    try:
        symbol = f"{coin}USDT"
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        df = loader.load_futures_extended_metrics(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            symbol=symbol
        )
        
        if len(df) > 0:
            print(f"  ✅ 성공: {len(df)}행 로드")
            print(f"    - 날짜 범위: {df['date'].min()} ~ {df['date'].max()}")
        else:
            print(f"  ⚠️ 경고: 데이터가 비어있음 (선택적 데이터)")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_risk_predictor(coin='BTC'):
    """RiskPredictor 테스트"""
    print(f"\n{'='*80}")
    print(f"[RiskPredictor 테스트] - {coin}")
    print(f"{'='*80}")
    
    from risk_predictor import RiskPredictor
    
    target_date = (datetime.now() - timedelta(days=1)).date()
    
    print(f"\n[예측 테스트]")
    print(f"  - 타겟 날짜: {target_date}")
    
    try:
        predictor = RiskPredictor(model_type="auto")
        
        result = predictor.predict_risk(target_date.strftime("%Y-%m-%d"), coin)
        
        if result['success']:
            print(f"  ✅ 예측 성공")
            print(f"    - 리스크 점수: {result['data']['risk_score']:.2f}%")
            print(f"    - 고변동성 확률: {result['data']['high_volatility_prob']*100:.2f}%")
            print(f"    - 청산 리스크: {result['data']['liquidation_risk']:.2f}%")
            return True
        else:
            print(f"  ❌ 예측 실패: {result.get('error', '알 수 없음')}")
            return False
            
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 실행"""
    print("="*80)
    print("전체 페이지 기능 테스트")
    print("="*80)
    print(f"\n테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"환경: {'로컬' if not os.path.exists('/mount/src') else 'Streamlit Cloud'}")
    
    results = {}
    
    # BTC 테스트
    print("\n" + "="*80)
    print("BTC 테스트")
    print("="*80)
    
    results['btc_data_loader'] = test_data_loader_functions('BTC')
    results['btc_risk_predictor'] = test_risk_predictor('BTC')
    
    # ETH 테스트
    print("\n" + "="*80)
    print("ETH 테스트")
    print("="*80)
    
    results['eth_data_loader'] = test_data_loader_functions('ETH')
    results['eth_risk_predictor'] = test_risk_predictor('ETH')
    
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

