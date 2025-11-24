"""
Project 3: Risk AI 특성 설명기
- 특성 중요도 분석
- SHAP 값 계산 (선택적)
- 예측 설명
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Streamlit Cloud 또는 로컬 환경 감지
if os.path.exists('/mount/src'):
    ROOT = Path('/mount/src/whale-arbitrage')
elif os.path.exists('/app'):
    ROOT = Path('/app')
else:
    ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))
sys.path.insert(0, str(ROOT / "app" / "utils"))

# SHAP 선택적 임포트
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

from risk_predictor import RiskPredictor
from data_loader import DataLoader
from feature_engineering import FeatureEngineer


class FeatureExplainer:
    def __init__(self):
        """특성 설명기 초기화"""
        self.predictor = RiskPredictor()
        self.data_loader = DataLoader()
        self.feature_engineer = FeatureEngineer()
        self.shap_available = SHAP_AVAILABLE
    
    def get_feature_importance(self, top_n: int = 10) -> pd.DataFrame:
        """특성 중요도 반환
        
        Args:
            top_n: 상위 N개 특성 (기본값: 10)
        
        Returns:
            DataFrame with columns:
            - feature: 특성 이름
            - importance: 중요도 점수
        """
        try:
            # 메타데이터에서 특성 중요도 로드
            metadata_path = ROOT / "data" / "models" / "risk_ai_metadata.json"
            
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                if 'feature_importance' in metadata:
                    importance_dict = metadata['feature_importance']
                    importance_df = pd.DataFrame({
                        'feature': list(importance_dict.keys()),
                        'importance': list(importance_dict.values())
                    }).sort_values('importance', ascending=False)
                    
                    return importance_df.head(top_n)
            
            # 메타데이터가 없으면 모델에서 직접 추출
            model = self.predictor.model
            features = self.predictor.features
            
            if model is None or features is None:
                return pd.DataFrame()
            
            importance_df = pd.DataFrame({
                'feature': features,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            return importance_df.head(top_n)
            
        except Exception as e:
            import logging
            logging.error(f"특성 중요도 추출 실패: {str(e)}")
            return pd.DataFrame()
    
    def explain_prediction(
        self, 
        target_date: str, 
        coin: str = 'BTC'
    ) -> Dict:
        """특정 예측 설명 (SHAP)
        
        Args:
            target_date: 예측할 날짜 (YYYY-MM-DD)
            coin: 코인 심볼 ('BTC' 또는 'ETH')
        
        Returns:
            {
                'success': bool,
                'data': {
                    'shap_values': Dict[str, float],  # 특성별 SHAP 값
                    'base_value': float,  # 기준값
                    'prediction': float  # 예측 확률
                },
                'error': str (if success=False)
            }
        """
        if not self.shap_available:
            return {
                'success': False,
                'error': 'SHAP가 설치되어 있지 않습니다. (pip install shap)'
            }
        
        try:
            # 타겟 날짜 기준 전후 데이터 필요
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            start_date = (target_dt - timedelta(days=60)).strftime("%Y-%m-%d")
            end_date = target_date
            
            # 데이터 로드
            df = self.data_loader.load_risk_data(start_date, end_date, coin)
            
            if len(df) == 0:
                return {
                    'success': False,
                    'error': f"{target_date}에 대한 데이터가 없습니다."
                }
            
            # 특성 생성
            df, _ = self.feature_engineer.create_features(df)
            
            # 타겟 날짜 행 찾기
            target_df = df[df['date'].dt.date == target_dt.date()]
            
            if target_df.empty:
                return {
                    'success': False,
                    'error': f"{target_date}에 대한 데이터가 없습니다."
                }
            
            row = target_df.iloc[0]
            features = self.predictor.features
            X = row[features].values.reshape(1, -1)
            X_df = pd.DataFrame(X, columns=features)
            
            # SHAP 값 계산
            model = self.predictor.model
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_df)
            
            # 이진 분류의 경우 shap_values는 리스트 [class_0, class_1]
            if isinstance(shap_values, list):
                shap_values = shap_values[1]  # class_1 (고변동성)에 대한 SHAP 값
            
            # SHAP 값 딕셔너리 생성
            shap_dict = {
                feature: float(shap_values[0][i])
                for i, feature in enumerate(features)
            }
            
            # 기준값 및 예측 확률
            base_value = float(explainer.expected_value)
            if isinstance(base_value, np.ndarray):
                base_value = float(base_value[1])  # class_1 기준값
            
            prediction = float(model.predict_proba(X_df)[0, 1])
            
            return {
                'success': True,
                'data': {
                    'shap_values': shap_dict,
                    'base_value': base_value,
                    'prediction': prediction
                }
            }
            
        except Exception as e:
            import logging
            import traceback
            logging.error(f"SHAP 설명 실패: {str(e)}\n{traceback.format_exc()}")
            return {
                'success': False,
                'error': f"SHAP 설명 중 오류 발생: {str(e)}"
            }
    
    def get_partial_dependence(
        self, 
        feature_name: str, 
        coin: str = 'BTC',
        n_points: int = 50
    ) -> pd.DataFrame:
        """Partial Dependence Plot 데이터
        
        Args:
            feature_name: 특성 이름
            coin: 코인 심볼 ('BTC' 또는 'ETH')
            n_points: 샘플링 포인트 수 (기본값: 50)
        
        Returns:
            DataFrame with columns:
            - feature_value: 특성 값
            - prediction: 예측 확률
        """
        try:
            # 최근 데이터 로드 (특성 생성에 30일 롤링 윈도우 필요)
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            
            df = self.data_loader.load_risk_data(start_date, end_date, coin)
            
            if len(df) == 0:
                return pd.DataFrame()
            
            # 특성 생성
            df, _ = self.feature_engineer.create_features(df)
            
            if feature_name not in df.columns:
                return pd.DataFrame()
            
            features = self.predictor.features
            if feature_name not in features:
                return pd.DataFrame()
            
            model = self.predictor.model
            
            # 특성 값 범위 계산
            feature_values = df[feature_name].dropna()
            if len(feature_values) == 0:
                return pd.DataFrame()
            
            min_val = feature_values.min()
            max_val = feature_values.max()
            
            # 샘플링 포인트 생성
            sample_values = np.linspace(min_val, max_val, n_points)
            
            # 각 샘플링 포인트에 대해 예측
            predictions = []
            
            # 기준 데이터 (평균값 사용)
            baseline = df[features].mean()
            
            for val in sample_values:
                # 특성 값만 변경
                X_sample = baseline.copy()
                X_sample[feature_name] = val
                X_sample_df = pd.DataFrame([X_sample], columns=features)
                
                # 예측
                pred = model.predict_proba(X_sample_df)[0, 1]
                predictions.append(pred)
            
            # 결과 DataFrame 생성
            result_df = pd.DataFrame({
                'feature_value': sample_values,
                'prediction': predictions
            })
            
            return result_df
            
        except Exception as e:
            import logging
            import traceback
            logging.error(f"Partial Dependence 계산 실패: {str(e)}\n{traceback.format_exc()}")
            return pd.DataFrame()

