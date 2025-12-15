
import sys
import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# 프로젝트 루트 경로 설정
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from app.utils.data_loader import DataLoader
from app.utils.risk_predictor import RiskPredictor

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_get_available_dates():
    print("\n=== 1. get_available_dates & list 테스트 ===")
    loader = DataLoader()
    
    # 1. get_available_dates
    min_date, max_date = loader.get_available_dates('BTC')
    print(f"BTC 날짜 범위: {min_date} ~ {max_date}")
    
    if max_date and max_date >= '2025-12-01':
        print("✅ 날짜 범위 테스트 통과 (2025-12월 포함)")
    else:
        print(f"⚠️ 날짜 범위 확인 필요 (최대 날짜: {max_date})")

    # 2. get_available_dates_list
    dates = loader.get_available_dates_list('BTC')
    print(f"BTC 사용 가능 날짜 수: {len(dates)}")
    if dates:
        print(f"마지막 날짜: {dates[-1]}")

def test_eth_data_loading():
    print("\n=== 2. ETH 데이터 로드 및 누락 컬럼 처리 테스트 ===")
    loader = DataLoader()
    start_date = "2024-01-01"
    end_date = "2024-01-10"
    
    # 1. load_risk_data
    try:
        df = loader.load_risk_data(start_date, end_date, 'ETH')
        print(f"ETH 일봉 데이터 로드 성공: {len(df)}행")
        
        required_cols = ['top100_richest_pct', 'avg_transaction_value_btc']
        missing = [col for col in required_cols if col not in df.columns]
        
        if not missing:
            print("✅ 필수 컬럼 존재 확인")
            # 값 확인 (0으로 채워졌는지)
            print(f"top100_richest_pct 평균: {df['top100_richest_pct'].mean()}")
        else:
            print(f"❌ 필수 컬럼 누락: {missing}")
            
    except Exception as e:
        print(f"❌ ETH 일봉 데이터 로드 실패: {e}")

    # 2. load_risk_data_weekly
    try:
        df_weekly = loader.load_risk_data_weekly(start_date, end_date, 'ETH')
        print(f"ETH 주봉 데이터 로드 성공: {len(df_weekly)}행")
        
        if 'whale_conc_change_7d' in df_weekly.columns:
             print("✅ whale_conc_change_7d 컬럼 존재 확인")
        else:
             print("❌ whale_conc_change_7d 컬럼 누락")
             
    except Exception as e:
        print(f"❌ ETH 주봉 데이터 로드 실패: {e}")

def test_risk_prediction_eth():
    print("\n=== 3. ETH 리스크 예측 테스트 ===")
    predictor = RiskPredictor()
    target_date = "2024-01-01" 
    
    # 데이터가 있는 최근 날짜로 설정 (로컬 데이터 기준)
    loader = DataLoader()
    dates = loader.get_available_dates_list('ETH')
    if dates:
        target_date = dates[-1]
    
    print(f"테스트 대상 날짜: {target_date}")
    
    try:
        result = predictor.predict_risk(target_date, 'ETH')
        if result['success']:
            print("✅ ETH 일봉 예측 성공")
            print(f"결과: Risk Score={result['data']['risk_score']:.2f}")
        else:
            print(f"❌ ETH 일봉 예측 실패: {result.get('error')}")
    except Exception as e:
        print(f"❌ ETH 일봉 예측 중 예외 발생: {e}")

def test_oi_growth_calculation():
    print("\n=== 4. OI Growth 및 0값 처리 테스트 ===")
    loader = DataLoader()
    
    # 최근 데이터 로드
    dates = loader.get_available_dates_list('BTC')
    if not dates:
        print("데이터 없음")
        return
        
    end_date = dates[-1]
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=20)).strftime("%Y-%m-%d")
    
    df = loader.load_risk_data(start_date, end_date, 'BTC')
    
    if 'sum_open_interest' in df.columns:
        oi_mean = df['sum_open_interest'].mean()
        print(f"Average OI: {oi_mean}")
        if oi_mean == 0:
            print("⚠️ OI 데이터가 모두 0입니다.")
        else:
            print("✅ OI 데이터 존재함")
    else:
        print("❌ sum_open_interest 컬럼 없음")
        
    # Feature Engineering 테스트
    from scripts.subprojects.risk_ai.feature_engineering import FeatureEngineer
    fe = FeatureEngineer()
    df_fe, _ = fe.create_features(df)
    
    if 'oi_growth_7d' in df_fe.columns:
        print(f"OI Growth 7d Mean: {df_fe['oi_growth_7d'].mean()}")
        print(f"Long Position Pct Mean: {df_fe.get('long_position_pct', pd.Series([0])).mean()}")
        print("✅ Feature Engineering 통과")
    else:
        print("❌ Feature Engineering 실패")

if __name__ == "__main__":
    test_get_available_dates()
    test_eth_data_loading()
    test_risk_prediction_eth()
    test_oi_growth_calculation()


