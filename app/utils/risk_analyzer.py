"""
Project 3: Risk AI 분석기
- 역사적 데이터 분석
- 성과 지표 계산
- 고변동성 구간 식별
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import os

# Streamlit Cloud 또는 로컬 환경 감지
if os.path.exists('/mount/src'):
    ROOT = Path('/mount/src/whale-arbitrage')
elif os.path.exists('/app'):
    ROOT = Path('/app')
else:
    ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / "app" / "utils"))

from risk_predictor import RiskPredictor
from data_loader import DataLoader


class RiskAnalyzer:
    def __init__(self):
        """분석기 초기화"""
        self.predictor = RiskPredictor()
        self.data_loader = DataLoader()
    
    def analyze_historical_performance(
        self, 
        start_date: str, 
        end_date: str, 
        coin: str = 'BTC'
    ) -> Dict:
        """역사적 성과 분석
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            coin: 코인 심볼 ('BTC' 또는 'ETH')
        
        Returns:
            {
                'success': bool,
                'data': {
                    'auc_roc': float,
                    'accuracy': float,
                    'precision': float,
                    'recall': float,
                    'f1_score': float,
                    'total_predictions': int,
                    'high_vol_count': int,
                    'predicted_high_vol_count': int
                },
                'error': str (if success=False)
            }
        """
        try:
            # 배치 예측
            predictions_df = self.predictor.predict_batch(start_date, end_date, coin)
            
            if len(predictions_df) == 0:
                return {
                    'success': False,
                    'error': f"{start_date} ~ {end_date} 기간에 대한 데이터가 없습니다."
                }
            
            # 실제 고변동성 데이터가 있는 경우만 성과 계산
            if 'actual_high_vol' in predictions_df.columns and predictions_df['actual_high_vol'].notna().any():
                from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, f1_score
                
                y_true = predictions_df['actual_high_vol'].fillna(0).astype(int)
                # 클래스 불균형을 고려하여 임계값을 0.3으로 낮춤
                y_pred = (predictions_df['high_volatility_prob'] > 0.3).astype(int)
                y_pred_proba = predictions_df['high_volatility_prob']
                
                try:
                    # AUC-ROC 계산 - 두 클래스가 모두 존재해야 함
                    if len(y_true.unique()) > 1:
                        auc_roc = roc_auc_score(y_true, y_pred_proba)
                    else:
                        auc_roc = None
                except:
                    auc_roc = None
                
                accuracy = accuracy_score(y_true, y_pred)
                precision = precision_score(y_true, y_pred, zero_division=0)
                recall = recall_score(y_true, y_pred, zero_division=0)
                f1 = f1_score(y_true, y_pred, zero_division=0)
                
                return {
                    'success': True,
                    'data': {
                        'auc_roc': float(auc_roc),
                        'accuracy': float(accuracy),
                        'precision': float(precision),
                        'recall': float(recall),
                        'f1_score': float(f1),
                        'total_predictions': int(len(predictions_df)),
                        'high_vol_count': int(y_true.sum()),
                        'predicted_high_vol_count': int(y_pred.sum())
                    }
                }
            else:
                # 실제 데이터가 없으면 기본 통계만 반환
                return {
                    'success': True,
                    'data': {
                        'auc_roc': None,
                        'accuracy': None,
                        'precision': None,
                        'recall': None,
                        'f1_score': None,
                        'total_predictions': int(len(predictions_df)),
                        'high_vol_count': None,
                        'predicted_high_vol_count': int((predictions_df['high_volatility_prob'] > 0.5).sum())
                    }
                }
                
        except Exception as e:
            import logging
            import traceback
            logging.error(f"성과 분석 실패: {str(e)}\n{traceback.format_exc()}")
            return {
                'success': False,
                'error': f"성과 분석 중 오류 발생: {str(e)}"
            }
    
    def get_high_volatility_periods(
        self, 
        start_date: str, 
        end_date: str, 
        coin: str = 'BTC',
        threshold: float = 0.5
    ) -> pd.DataFrame:
        """고변동성 구간 추출
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            coin: 코인 심볼 ('BTC' 또는 'ETH')
            threshold: 고변동성 판단 임계값 (기본값: 0.5)
        
        Returns:
            DataFrame with columns:
            - date: 날짜
            - high_volatility_prob: 고변동성 확률
            - risk_score: 리스크 점수
            - actual_high_vol: 실제 고변동성 여부 (if available)
        """
        try:
            predictions_df = self.predictor.predict_batch(start_date, end_date, coin)
            
            if len(predictions_df) == 0:
                return pd.DataFrame()
            
            # 임계값 이상인 구간만 필터링
            high_vol_df = predictions_df[predictions_df['high_volatility_prob'] >= threshold].copy()
            
            return high_vol_df
            
        except Exception as e:
            import logging
            logging.error(f"고변동성 구간 추출 실패: {str(e)}")
            return pd.DataFrame()
    
    def calculate_correlation_matrix(
        self, 
        start_date: str, 
        end_date: str, 
        coin: str = 'BTC'
    ) -> pd.DataFrame:
        """지표별 상관관계 분석
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            coin: 코인 심볼 ('BTC' 또는 'ETH')
        
        Returns:
            상관관계 행렬 DataFrame
        """
        try:
            from datetime import datetime, timedelta
            
            # 데이터 로드 (특성 생성에 30일 롤링 윈도우 필요)
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            data_start_date = (start_dt - timedelta(days=60)).strftime("%Y-%m-%d")
            
            df = self.data_loader.load_risk_data(data_start_date, end_date, coin)
            
            if len(df) == 0:
                return pd.DataFrame()
            
            # 특성 생성
            sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))
            from feature_engineering import FeatureEngineer
            fe = FeatureEngineer()
            df, _ = fe.create_features(df)
            
            # 예측 기간 필터링
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            
            if len(df) == 0:
                return pd.DataFrame()
            
            # 상관관계 계산할 지표 선택
            correlation_cols = [
                'whale_conc_change_7d',
                'avg_funding_rate',
                'funding_rate_zscore',
                'oi_growth_7d',
                'volatility_24h',
                'volatility_ratio'
            ]
            
            # 존재하는 컬럼만 사용
            available_cols = [col for col in correlation_cols if col in df.columns]
            
            if len(available_cols) == 0:
                return pd.DataFrame()
            
            # 상관관계 계산
            corr_matrix = df[available_cols].corr()
            
            return corr_matrix
            
        except Exception as e:
            import logging
            import traceback
            logging.error(f"상관관계 분석 실패: {str(e)}\n{traceback.format_exc()}")
            return pd.DataFrame()

