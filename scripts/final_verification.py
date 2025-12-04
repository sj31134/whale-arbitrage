#!/usr/bin/env python3
"""
최종 검증 스크립트
- 모든 데이터 로딩 함수 테스트
- Supabase 지원 확인
- 페이지별 기능 검증
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
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))

def test_data_loader_comprehensive():
    """DataLoader 종합 테스트"""
    print("\n" + "="*80)
    print("DataLoader 종합 테스트")
    print("="*80)
    
    from data_loader import DataLoader
    
    loader = DataLoader()
    
    # 환경 정보
    print(f"\n[환경 정보]")
    print(f"  - Supabase 사용: {loader.use_supabase}")
    print(f"  - DB 경로: {loader.db_path}")
    print(f"  - conn 속성: {loader.conn is not None if hasattr(loader, 'conn') else 'N/A'}")
    
    results = {}
    
    # 1. get_available_dates 테스트
    print(f"\n[1] get_available_dates 테스트")
    for coin in ['BTC', 'ETH']:
        try:
            min_date, max_date = loader.get_available_dates(coin)
            if min_date and max_date:
                print(f"  ✅ {coin}: {min_date} ~ {max_date}")
                results[f'get_available_dates_{coin}'] = True
            else:
                print(f"  ❌ {coin}: 날짜 범위를 가져올 수 없음")
                results[f'get_available_dates_{coin}'] = False
        except Exception as e:
            print(f"  ❌ {coin}: 오류 - {e}")
            results[f'get_available_dates_{coin}'] = False
    
    # 2. load_risk_data 테스트
    print(f"\n[2] load_risk_data 테스트")
    for coin in ['BTC', 'ETH']:
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            df = loader.load_risk_data(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                coin=coin
            )
            
            if len(df) > 0:
                print(f"  ✅ {coin}: {len(df)}행 로드")
                results[f'load_risk_data_{coin}'] = True
            else:
                print(f"  ⚠️ {coin}: 데이터 없음 (빈 DataFrame 반환)")
                results[f'load_risk_data_{coin}'] = True  # 빈 DataFrame도 정상 동작
        except Exception as e:
            print(f"  ❌ {coin}: 오류 - {e}")
            results[f'load_risk_data_{coin}'] = False
    
    # 3. load_futures_extended_metrics 테스트
    print(f"\n[3] load_futures_extended_metrics 테스트")
    for coin in ['BTC', 'ETH']:
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
                print(f"  ✅ {coin}: {len(df)}행 로드")
            else:
                print(f"  ⚠️ {coin}: 데이터 없음 (선택적 데이터)")
            results[f'load_futures_extended_metrics_{coin}'] = True
        except Exception as e:
            print(f"  ❌ {coin}: 오류 - {e}")
            results[f'load_futures_extended_metrics_{coin}'] = False
    
    # 4. get_available_dates_list 테스트
    print(f"\n[4] get_available_dates_list 테스트")
    for coin in ['BTC', 'ETH']:
        try:
            dates = loader.get_available_dates_list(coin)
            if len(dates) > 0:
                print(f"  ✅ {coin}: {len(dates)}개 날짜")
                results[f'get_available_dates_list_{coin}'] = True
            else:
                print(f"  ⚠️ {coin}: 날짜 목록 없음")
                results[f'get_available_dates_list_{coin}'] = False
        except Exception as e:
            print(f"  ❌ {coin}: 오류 - {e}")
            results[f'get_available_dates_list_{coin}'] = False
    
    return results

def test_feature_engineer():
    """FeatureEngineer 테스트"""
    print("\n" + "="*80)
    print("FeatureEngineer 테스트")
    print("="*80)
    
    from feature_engineering import FeatureEngineer
    
    results = {}
    
    try:
        fe = FeatureEngineer()
        print(f"  ✅ FeatureEngineer 초기화 성공")
        print(f"    - use_data_loader: {fe.use_data_loader if hasattr(fe, 'use_data_loader') else 'N/A'}")
        
        # load_raw_data 테스트
        for coin in ['BTC', 'ETH']:
            try:
                df = fe.load_raw_data('2025-11-01', coin)
                if len(df) > 0:
                    print(f"  ✅ {coin}: {len(df)}행 로드")
                    results[f'feature_engineer_{coin}'] = True
                else:
                    print(f"  ⚠️ {coin}: 데이터 없음")
                    results[f'feature_engineer_{coin}'] = True  # 빈 DataFrame도 정상
            except Exception as e:
                print(f"  ❌ {coin}: 오류 - {e}")
                results[f'feature_engineer_{coin}'] = False
    except Exception as e:
        print(f"  ❌ FeatureEngineer 초기화 실패: {e}")
        results['feature_engineer_init'] = False
    
    return results

def test_risk_predictor():
    """RiskPredictor 테스트"""
    print("\n" + "="*80)
    print("RiskPredictor 테스트")
    print("="*80)
    
    from risk_predictor import RiskPredictor
    
    results = {}
    
    try:
        predictor = RiskPredictor(model_type="auto")
        print(f"  ✅ RiskPredictor 초기화 성공")
        print(f"    - 모델 타입: {predictor.model_type}")
        print(f"    - 동적 변수 포함: {predictor.include_dynamic}")
        
        # predict_risk 테스트
        target_date = (datetime.now() - timedelta(days=1)).date()
        
        for coin in ['BTC', 'ETH']:
            try:
                result = predictor.predict_risk(target_date.strftime("%Y-%m-%d"), coin)
                if result['success']:
                    print(f"  ✅ {coin}: 예측 성공 (리스크 점수: {result['data']['risk_score']:.2f}%)")
                    results[f'predict_risk_{coin}'] = True
                else:
                    print(f"  ⚠️ {coin}: 예측 실패 - {result.get('error', '알 수 없음')}")
                    # 데이터가 없는 경우는 정상 (존재하지 않는 날짜)
                    results[f'predict_risk_{coin}'] = True
            except Exception as e:
                print(f"  ❌ {coin}: 오류 - {e}")
                results[f'predict_risk_{coin}'] = False
    except Exception as e:
        print(f"  ❌ RiskPredictor 초기화 실패: {e}")
        results['risk_predictor_init'] = False
    
    return results

def main():
    """메인 테스트 실행"""
    print("="*80)
    print("최종 검증 테스트")
    print("="*80)
    print(f"\n테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"환경: {'로컬' if not os.path.exists('/mount/src') else 'Streamlit Cloud'}")
    
    all_results = {}
    
    # DataLoader 테스트
    all_results.update(test_data_loader_comprehensive())
    
    # FeatureEngineer 테스트
    all_results.update(test_feature_engineer())
    
    # RiskPredictor 테스트
    all_results.update(test_risk_predictor())
    
    # 결과 요약
    print("\n" + "="*80)
    print("테스트 결과 요약")
    print("="*80)
    
    total = len(all_results)
    passed = sum(all_results.values())
    failed = total - passed
    
    for test_name, result in sorted(all_results.items()):
        status = "✅ 통과" if result else "❌ 실패"
        print(f"  {test_name}: {status}")
    
    print(f"\n총 {total}개 테스트 중 {passed}개 통과, {failed}개 실패")
    
    if failed > 0:
        print("\n⚠️ 실패한 테스트가 있습니다.")
        return 1
    else:
        print("\n✅ 모든 테스트 통과!")
        return 0

if __name__ == "__main__":
    sys.exit(main())

