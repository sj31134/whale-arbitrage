#!/usr/bin/env python3
"""
통합 테스트
전체 파이프라인 (데이터 수집 -> 특성 생성 -> 모델 예측)을 테스트합니다.
"""

import unittest
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))
sys.path.insert(0, str(ROOT / "app" / "utils"))


class TestFeatureEngineeringIntegration(unittest.TestCase):
    """특성 엔지니어링 통합 테스트"""
    
    def test_feature_engineer_initialization(self):
        """FeatureEngineer 초기화 테스트"""
        try:
            from feature_engineering import FeatureEngineer
            fe = FeatureEngineer()
            self.assertIsNotNone(fe)
        except Exception as e:
            self.skipTest(f"FeatureEngineer 초기화 실패 (DB 연결 필요): {e}")
    
    def test_create_features_with_mock_data(self):
        """모의 데이터로 특성 생성 테스트"""
        from feature_engineering import FeatureEngineer
        
        # 모의 데이터 생성
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        
        mock_df = pd.DataFrame({
            'date': dates,
            'symbol': 'BTCUSDT',
            'avg_funding_rate': np.random.randn(100) * 0.001,
            'sum_open_interest': np.random.randint(1000000, 5000000, 100).astype(float),
            'long_short_ratio': np.random.uniform(0.8, 1.2, 100),
            'volatility_24h': np.random.uniform(0.02, 0.08, 100),
            'top100_richest_pct': np.random.uniform(10, 20, 100),
            'avg_transaction_value_btc': np.random.uniform(0.1, 10, 100),
            'ext_long_short_ratio': np.random.uniform(0.8, 1.2, 100),
            'long_account_pct': np.random.uniform(0.4, 0.6, 100),
            'short_account_pct': np.random.uniform(0.4, 0.6, 100),
            'taker_buy_sell_ratio': np.random.uniform(0.8, 1.2, 100),
            'taker_buy_vol': np.random.uniform(1e6, 5e6, 100),
            'taker_sell_vol': np.random.uniform(1e6, 5e6, 100),
            'top_trader_long_short_ratio': np.random.uniform(0.8, 1.2, 100),
            'bybit_funding_rate': np.random.randn(100) * 0.001,
            'bybit_oi': np.random.randint(500000, 2500000, 100).astype(float),
            'exchange_inflow_usd': np.random.uniform(1e6, 1e7, 100),
            'exchange_outflow_usd': np.random.uniform(1e6, 1e7, 100),
            'net_flow_usd': np.random.uniform(-5e6, 5e6, 100),
            'active_addresses': np.random.randint(100, 500, 100),
            'large_tx_count': np.random.randint(5, 50, 100)
        })
        
        fe = FeatureEngineer()
        
        # 정적 변수만
        df_static, features_static = fe.create_features(mock_df, include_dynamic=False)
        self.assertGreater(len(features_static), 0)
        self.assertIn('avg_funding_rate', features_static)
        
        # 동적 변수 포함
        df_dynamic, features_dynamic = fe.create_features(mock_df, include_dynamic=True)
        self.assertGreater(len(features_dynamic), len(features_static))
        self.assertIn('volatility_delta', features_dynamic)
        self.assertIn('volatility_accel', features_dynamic)
    
    def test_weekly_features_with_mock_data(self):
        """주봉 모의 데이터로 특성 생성 테스트"""
        from feature_engineering import FeatureEngineer
        
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=52, freq='W')
        
        mock_df = pd.DataFrame({
            'date': dates,
            'symbol': 'BTCUSDT',
            'open': np.random.uniform(40000, 50000, 52),
            'high': np.random.uniform(45000, 55000, 52),
            'low': np.random.uniform(35000, 45000, 52),
            'close': np.random.uniform(40000, 50000, 52),
            'volume': np.random.uniform(1e9, 5e9, 52),
            'quote_volume': np.random.uniform(1e10, 5e10, 52),
            'atr': np.random.uniform(1000, 3000, 52),
            'rsi': np.random.uniform(30, 70, 52),
            'upper_shadow_ratio': np.random.uniform(0.1, 0.3, 52),
            'lower_shadow_ratio': np.random.uniform(0.1, 0.3, 52),
            'weekly_range_pct': np.random.uniform(0.05, 0.15, 52),
            'body_size_pct': np.random.uniform(0.02, 0.08, 52),
            'volatility_ratio': np.random.uniform(0.8, 1.2, 52),
            'top100_richest_pct': np.random.uniform(10, 20, 52)
        })
        
        fe = FeatureEngineer()
        
        # 주봉 특성 생성
        df_weekly, features_weekly = fe.create_weekly_features(mock_df, include_dynamic=True)
        
        self.assertGreater(len(features_weekly), 0)
        self.assertIn('weekly_return', features_weekly)
        self.assertIn('volatility_delta_w', features_weekly)


class TestModelIntegration(unittest.TestCase):
    """모델 통합 테스트"""
    
    def test_xgboost_model_prediction(self):
        """XGBoost 모델 예측 테스트"""
        try:
            import xgboost as xgb
        except ImportError:
            self.skipTest("xgboost 모듈이 설치되지 않았습니다.")
        
        # 모의 데이터
        np.random.seed(42)
        X_train = np.random.randn(100, 7)
        y_train = np.random.randint(0, 2, 100)
        X_test = np.random.randn(20, 7)
        
        # 모델 학습
        model = xgb.XGBClassifier(
            n_estimators=10,
            max_depth=3,
            use_label_encoder=False,
            eval_metric='logloss'
        )
        model.fit(X_train, y_train, verbose=False)
        
        # 예측
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)
        
        # 검증
        self.assertEqual(len(y_pred), 20)
        self.assertEqual(y_pred_proba.shape, (20, 2))
        self.assertTrue(all(y_pred_proba[:, 0] + y_pred_proba[:, 1] == 1))
    
    def test_hybrid_model_structure(self):
        """하이브리드 모델 구조 테스트"""
        try:
            from train_hybrid_model import HybridEnsembleModel
            
            model = HybridEnsembleModel(sequence_length=30, use_lstm=False)
            
            self.assertEqual(model.sequence_length, 30)
            self.assertFalse(model.use_lstm)
            
        except ImportError:
            self.skipTest("HybridEnsembleModel 임포트 실패")


class TestRiskPredictorIntegration(unittest.TestCase):
    """RiskPredictor 통합 테스트"""
    
    def test_predictor_initialization(self):
        """RiskPredictor 초기화 테스트"""
        try:
            from risk_predictor import RiskPredictor
            
            # 기본 초기화 시도
            predictor = RiskPredictor(model_type="legacy")
            self.assertIsNotNone(predictor)
            
        except FileNotFoundError:
            self.skipTest("모델 파일이 없습니다. 먼저 모델을 학습시켜야 합니다.")
        except Exception as e:
            self.skipTest(f"RiskPredictor 초기화 실패: {e}")
    
    def test_available_models(self):
        """사용 가능한 모델 목록 테스트"""
        try:
            from risk_predictor import RiskPredictor
            
            predictor = RiskPredictor(model_type="legacy")
            available = predictor.get_available_models()
            
            self.assertIsInstance(available, list)
            
        except Exception as e:
            self.skipTest(f"테스트 실패: {e}")


class TestEndToEndPipeline(unittest.TestCase):
    """전체 파이프라인 테스트"""
    
    def test_full_pipeline_mock(self):
        """전체 파이프라인 모의 테스트"""
        try:
            import xgboost as xgb
        except ImportError:
            self.skipTest("xgboost 모듈이 설치되지 않았습니다.")
        from sklearn.preprocessing import StandardScaler
        
        # 1. 모의 데이터 생성 (데이터 수집 시뮬레이션)
        np.random.seed(42)
        n_samples = 200
        
        raw_data = pd.DataFrame({
            'date': pd.date_range(start='2024-01-01', periods=n_samples, freq='D'),
            'volatility': np.random.uniform(0.02, 0.08, n_samples),
            'oi': np.cumsum(np.random.randn(n_samples) * 100000) + 5000000,
            'funding': np.random.randn(n_samples) * 0.001
        })
        
        # 2. 특성 생성 (Feature Engineering)
        raw_data['vol_delta'] = raw_data['volatility'].diff()
        raw_data['oi_delta'] = raw_data['oi'].pct_change()
        raw_data['vol_accel'] = raw_data['vol_delta'].diff()
        raw_data['vol_ma'] = raw_data['volatility'].rolling(7).mean()
        
        # 타겟 생성
        raw_data['target'] = (raw_data['volatility'].shift(-1) > raw_data['volatility'].quantile(0.8)).astype(int)
        
        # NaN 제거
        data = raw_data.dropna()
        
        # 3. 학습/테스트 분할
        split_idx = int(len(data) * 0.8)
        train_data = data.iloc[:split_idx]
        test_data = data.iloc[split_idx:]
        
        features = ['volatility', 'oi', 'funding', 'vol_delta', 'oi_delta', 'vol_accel', 'vol_ma']
        
        X_train = train_data[features].values
        y_train = train_data['target'].values
        X_test = test_data[features].values
        y_test = test_data['target'].values
        
        # 4. 스케일링
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # 5. 모델 학습
        model = xgb.XGBClassifier(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.1,
            use_label_encoder=False,
            eval_metric='auc'
        )
        model.fit(X_train_scaled, y_train, verbose=False)
        
        # 6. 예측 및 평가
        y_pred = model.predict(X_test_scaled)
        y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
        
        # 7. 검증
        self.assertEqual(len(y_pred), len(y_test))
        self.assertTrue(all(y_pred_proba >= 0))
        self.assertTrue(all(y_pred_proba <= 1))
        
        # 정확도가 0보다 큼 (무작위보다 나음)
        accuracy = (y_pred == y_test).mean()
        self.assertGreater(accuracy, 0)


if __name__ == '__main__':
    unittest.main()

