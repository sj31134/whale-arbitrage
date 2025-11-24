"""
Project 3: Risk AI 예측기
- 학습된 모델 로드
- 리스크 점수 예측
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pickle
import json
import os
from typing import Dict, Optional, Tuple
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

from feature_engineering import FeatureEngineer
from data_loader import DataLoader


class RiskPredictor:
    def __init__(self):
        """모델 및 특성 로드"""
        self.model = None
        self.features = None
        self.metadata = None
        self.feature_engineer = FeatureEngineer()
        self.data_loader = DataLoader()
        self._load_model()
    
    def _load_model(self):
        """학습된 모델 로드"""
        model_path = ROOT / "data" / "models" / "risk_ai_model.pkl"
        features_path = ROOT / "data" / "models" / "risk_ai_features.json"
        metadata_path = ROOT / "data" / "models" / "risk_ai_metadata.json"
        
        try:
            # 모델 로드
            if not model_path.exists():
                raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")
            
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            
            # 특성 목록 로드
            if features_path.exists():
                with open(features_path, 'r') as f:
                    self.features = json.load(f)
            else:
                # 기본 특성 목록 (fallback)
                self.features = [
                    'avg_funding_rate', 'sum_open_interest', 'long_position_pct',
                    'whale_conc_change_7d', 'funding_rate_zscore', 'oi_growth_7d',
                    'volatility_ratio'
                ]
            
            # 메타데이터 로드
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
            
        except Exception as e:
            import logging
            logging.error(f"모델 로드 실패: {str(e)}")
            raise
    
    def predict_risk(self, target_date: str, coin: str = 'BTC') -> Dict:
        """특정 날짜의 리스크 예측
        
        Args:
            target_date: 예측할 날짜 (YYYY-MM-DD)
            coin: 코인 심볼 ('BTC' 또는 'ETH')
        
        Returns:
            {
                'success': bool,
                'data': {
                    'date': str,
                    'high_volatility_prob': float,  # 고변동성 확률 (0~1)
                    'risk_score': float,  # 종합 리스크 점수 (0~100)
                    'liquidation_risk': float,  # 청산 리스크 점수 (0~100)
                    'indicators': {
                        'whale_conc_change_7d': float,
                        'funding_rate': float,
                        'oi_growth_7d': float,
                        'volatility_24h': float
                    }
                },
                'error': str (if success=False)
            }
        """
        try:
            # 타겟 날짜 기준 전후 데이터 필요 (특성 생성에 30일 롤링 윈도우 필요)
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
                # 가장 가까운 날짜 찾기
                if len(df) > 0:
                    df['date_diff'] = (df['date'].dt.date - target_dt.date()).abs()
                    closest_row = df.loc[df['date_diff'].idxmin()]
                    closest_date = closest_row['date'].date()
                    days_diff = abs((closest_date - target_dt.date()).days)
                    
                    return {
                        'success': False,
                        'error': f"{target_date}에 대한 데이터가 없습니다. 가장 가까운 날짜: {closest_date} (차이: {days_diff}일)",
                        'closest_date': closest_date.strftime("%Y-%m-%d")
                    }
                else:
                    return {
                        'success': False,
                        'error': f"{target_date}에 대한 데이터가 없습니다."
                    }
            
            row = target_df.iloc[0]
            
            # 특성 추출
            X = row[self.features].values.reshape(1, -1)
            X_df = pd.DataFrame(X, columns=self.features)
            
            # 예측
            prob = self.model.predict_proba(X_df)[0, 1]  # 고변동성 확률
            risk_score = prob * 100  # 0~100 스케일
            
            # 청산 리스크 계산 (OI 급증 + 펀딩비 이상)
            oi_growth = row.get('oi_growth_7d', 0)
            funding_zscore = row.get('funding_rate_zscore', 0)
            liquidation_risk = min(100, max(0, (abs(oi_growth) * 50 + abs(funding_zscore) * 20)))
            
            return {
                'success': True,
                'data': {
                    'date': target_date,
                    'high_volatility_prob': float(prob),
                    'risk_score': float(risk_score),
                    'liquidation_risk': float(liquidation_risk),
                    'indicators': {
                        'whale_conc_change_7d': float(row.get('whale_conc_change_7d', 0)),
                        'funding_rate': float(row.get('avg_funding_rate', 0)),
                        'oi_growth_7d': float(row.get('oi_growth_7d', 0)),
                        'volatility_24h': float(row.get('volatility_24h', 0)),
                        'funding_rate_zscore': float(row.get('funding_rate_zscore', 0))
                    }
                }
            }
            
        except Exception as e:
            import logging
            import traceback
            logging.error(f"예측 실패: {str(e)}\n{traceback.format_exc()}")
            return {
                'success': False,
                'error': f"예측 중 오류 발생: {str(e)}"
            }
    
    def predict_batch(self, start_date: str, end_date: str, coin: str = 'BTC') -> pd.DataFrame:
        """기간별 리스크 예측
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            coin: 코인 심볼 ('BTC' 또는 'ETH')
        
        Returns:
            DataFrame with columns:
            - date: 날짜
            - high_volatility_prob: 고변동성 확률
            - risk_score: 종합 리스크 점수
            - liquidation_risk: 청산 리스크 점수
            - actual_high_vol: 실제 고변동성 여부 (if available)
        """
        try:
            # 데이터 로드 (특성 생성에 30일 롤링 윈도우 필요하므로 시작일 30일 전부터)
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            data_start_date = (start_dt - timedelta(days=60)).strftime("%Y-%m-%d")
            
            df = self.data_loader.load_risk_data(data_start_date, end_date, coin)
            
            if len(df) == 0:
                return pd.DataFrame()
            
            # 특성 생성
            df, _ = self.feature_engineer.create_features(df)
            
            # 예측 기간 필터링
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            
            if len(df) == 0:
                return pd.DataFrame()
            
            # 예측
            X = df[self.features]
            probs = self.model.predict_proba(X)[:, 1]
            risk_scores = probs * 100
            
            # 청산 리스크 계산
            oi_growth = df['oi_growth_7d'].fillna(0)
            funding_zscore = df['funding_rate_zscore'].fillna(0)
            liquidation_risks = np.minimum(100, np.maximum(0, (np.abs(oi_growth) * 50 + np.abs(funding_zscore) * 20)))
            
            # 결과 DataFrame 생성
            result_df = pd.DataFrame({
                'date': df['date'].dt.date,
                'high_volatility_prob': probs,
                'risk_score': risk_scores,
                'liquidation_risk': liquidation_risks,
                'actual_high_vol': df.get('target_high_vol', None)
            })
            
            return result_df
            
        except Exception as e:
            import logging
            import traceback
            logging.error(f"배치 예측 실패: {str(e)}\n{traceback.format_exc()}")
            return pd.DataFrame()

