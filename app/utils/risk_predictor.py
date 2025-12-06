"""
Project 3: Risk AI 예측기 (확장 버전)

기능:
- 기존 XGBoost 모델 지원
- 동적 변수 기반 예측
- 하이브리드 앙상블 모델 지원
- LSTM 시계열 모델 지원
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pickle
import json
import os
import logging
from typing import Dict, Optional, Tuple, List
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

# 앙상블 모델 임포트 (선택적)
try:
    from train_hybrid_model import HybridEnsembleModel
    HAS_HYBRID = True
except ImportError:
    HAS_HYBRID = False
    HybridEnsembleModel = None

# LSTM 모델 임포트 (선택적)
try:
    from train_lstm_model import LSTMRiskModel, HAS_TENSORFLOW
except ImportError:
    HAS_TENSORFLOW = False
    LSTMRiskModel = None


class RiskPredictor:
    """
    리스크 예측기 (확장 버전)
    
    지원 모델:
    - legacy: 기존 XGBoost 모델 (정적 변수)
    - xgb_dynamic: XGBoost (동적 변수 포함)
    - hybrid: 하이브리드 앙상블 (XGBoost + LSTM)
    - lstm: LSTM 시계열 모델
    """
    
    def __init__(self, model_type: str = "auto"):
        """
        모델 및 특성 로드
        
        Args:
            model_type: 사용할 모델 타입
                - "auto": 가장 최신/최적 모델 자동 선택
                - "legacy": 기존 XGBoost 모델
                - "dynamic": 동적 변수 포함 XGBoost
                - "hybrid": 하이브리드 앙상블
                - "lstm": LSTM 모델
        """
        self.model = None
        self.features = None
        self.metadata = None
        self.model_type = model_type
        self.include_dynamic = False
        
        self.feature_engineer = FeatureEngineer()
        self.data_loader = DataLoader()
        
        self._load_model()
    
    def _load_model(self):
        """학습된 모델 로드"""
        model_dir = ROOT / "data" / "models"
        
        # 모델 타입에 따라 로드
        if self.model_type == "auto":
            # 우선순위: hybrid > dynamic > legacy
            if HAS_HYBRID and (model_dir / "hybrid_ensemble_dynamic_metadata.json").exists():
                self._load_hybrid_model("hybrid_ensemble_dynamic")
            elif (model_dir / "risk_ai_model.pkl").exists():
                self._load_legacy_model()
            else:
                raise FileNotFoundError("사용 가능한 모델이 없습니다.")
        
        elif self.model_type == "hybrid":
            if not HAS_HYBRID:
                raise ImportError("하이브리드 모델을 사용하려면 train_hybrid_model 모듈이 필요합니다.")
            self._load_hybrid_model("hybrid_ensemble_dynamic")
        
        elif self.model_type == "lstm":
            if not HAS_TENSORFLOW:
                raise ImportError("LSTM 모델을 사용하려면 TensorFlow가 필요합니다.")
            self._load_lstm_model("lstm_risk_model_dynamic")
        
        elif self.model_type == "dynamic":
            self._load_legacy_model(include_dynamic=True)
        
        else:  # legacy
            self._load_legacy_model()
    
    def _load_legacy_model(self, include_dynamic=False):
        """기존 XGBoost 모델 로드"""
        model_path = ROOT / "data" / "models" / "risk_ai_model.pkl"
        features_path = ROOT / "data" / "models" / "risk_ai_features.json"
        metadata_path = ROOT / "data" / "models" / "risk_ai_metadata.json"
        
        try:
            if not model_path.exists():
                raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")
            
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            
            if features_path.exists():
                with open(features_path, 'r') as f:
                    self.features = json.load(f)
            else:
                self.features = [
                    'avg_funding_rate', 'sum_open_interest', 'long_position_pct',
                    'whale_conc_change_7d', 'funding_rate_zscore', 'oi_growth_7d',
                    'volatility_ratio'
                ]
            
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
            
            self.model_type = "legacy"
            self.include_dynamic = include_dynamic
            logging.info(f"Legacy 모델 로드 완료 (동적 변수: {include_dynamic})")
            
        except Exception as e:
            logging.error(f"Legacy 모델 로드 실패: {str(e)}")
            raise
    
    def _load_hybrid_model(self, model_name: str):
        """하이브리드 앙상블 모델 로드"""
        try:
            self.model = HybridEnsembleModel()
            self.model.load(model_name)
            
            self.features = self.model.feature_names
            self.model_type = "hybrid"
            self.include_dynamic = True
            
            metadata_path = ROOT / "data" / "models" / f"{model_name}_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
            
            logging.info(f"하이브리드 앙상블 모델 로드 완료: {model_name}")
            
        except Exception as e:
            logging.error(f"하이브리드 모델 로드 실패: {str(e)}")
            raise
    
    def _load_lstm_model(self, model_name: str):
        """LSTM 모델 로드"""
        try:
            self.model = LSTMRiskModel()
            self.model.load(model_name)
            
            self.features = self.model.feature_names
            self.model_type = "lstm"
            self.include_dynamic = True
            
            metadata_path = ROOT / "data" / "models" / f"{model_name}_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
            
            logging.info(f"LSTM 모델 로드 완료: {model_name}")
            
        except Exception as e:
            logging.error(f"LSTM 모델 로드 실패: {str(e)}")
            raise
    
    def get_available_models(self) -> List[str]:
        """사용 가능한 모델 목록 반환"""
        model_dir = ROOT / "data" / "models"
        available = []
        
        if (model_dir / "risk_ai_model.pkl").exists():
            available.append("legacy")
        
        if HAS_HYBRID and (model_dir / "hybrid_ensemble_dynamic_metadata.json").exists():
            available.append("hybrid")
        
        if HAS_TENSORFLOW and (model_dir / "lstm_risk_model_dynamic_metadata.json").exists():
            available.append("lstm")
        
        return available
    
    def get_dynamic_indicators(self, df: pd.DataFrame) -> Dict:
        """동적 지표 추출"""
        indicators = {}
        
        dynamic_cols = [
            'volatility_delta', 'oi_delta', 'funding_delta',
            'volatility_accel', 'oi_accel', 'funding_accel',
            'volatility_slope', 'oi_slope', 'funding_slope'
        ]
        
        for col in dynamic_cols:
            if col in df.columns:
                indicators[col] = float(df[col].iloc[-1]) if len(df) > 0 else 0.0
        
        return indicators
    
    def predict_risk(self, target_date: str, coin: str = 'BTC') -> Dict:
        """특정 날짜의 리스크 예측
        
        Args:
            target_date: 예측할 날짜 (YYYY-MM-DD)
            coin: 코인 심볼 ('BTC' 또는 'ETH')
        
        Returns:
            {
                'success': bool,
                'model_type': str,  # 사용된 모델 타입
                'data': {
                    'date': str,
                    'high_volatility_prob': float,  # 고변동성 확률 (0~1)
                    'risk_score': float,  # 종합 리스크 점수 (0~100)
                    'liquidation_risk': float,  # 청산 리스크 점수 (0~100)
                    'indicators': {
                        'whale_conc_change_7d': float,
                        'funding_rate': float,
                        'oi_growth_7d': float,
                        'volatility_24h': float,
                        # 동적 지표 (include_dynamic=True인 경우)
                        'volatility_delta': float,
                        'oi_delta': float,
                        ...
                    }
                },
                'error': str (if success=False)
            }
        """
        try:
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
            
            # 특성 생성 (동적 변수 포함 여부에 따라)
            df, generated_features = self.feature_engineer.create_features(
                df, include_dynamic=self.include_dynamic
            )
            
            # 타겟 날짜 행 찾기
            target_df = df[df['date'].dt.date == target_dt.date()]
            
            if target_df.empty:
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
            
            # 사용할 특성 결정
            features_to_use = self.features if self.features else generated_features
            
            # 특성 추출
            X_values = []
            for feature in features_to_use:
                if feature in row.index:
                    value = row[feature]
                    if pd.isna(value):
                        X_values.append(0.0)
                    else:
                        try:
                            X_values.append(float(value))
                        except (ValueError, TypeError):
                            X_values.append(0.0)
                else:
                    X_values.append(0.0)
            
            X_df = pd.DataFrame([X_values], columns=features_to_use, dtype=float)
            
            # 모델 타입에 따른 예측
            if self.model_type == "hybrid":
                prob = self.model.predict_proba(X_df.values)[0, 1]
            elif self.model_type == "lstm":
                # LSTM은 시퀀스 필요 - 단일 예측에서는 전체 데이터 사용
                X_full = df[features_to_use].values
                probs = self.model.predict(X_full)
                prob = probs[-1] if len(probs) > 0 else 0.5
            else:
                prob = self.model.predict_proba(X_df)[0, 1]
            
            risk_score = prob * 100
            
            # 청산 리스크 계산 (스케일 정규화 적용)
            oi_growth = float(row.get('oi_growth_7d', 0) or 0)
            funding_zscore = float(row.get('funding_rate_zscore', 0) or 0)
            
            # 동적 변수 기반 청산 리스크 보정
            if self.include_dynamic:
                oi_accel = float(row.get('oi_accel', 0) or 0)
                vol_accel = float(row.get('volatility_accel', 0) or 0)
                
                # 스케일 정규화 (이상치 클리핑)
                oi_growth_norm = min(abs(oi_growth), 0.5)       # 최대 50% 변화
                funding_zscore_norm = min(abs(funding_zscore), 3.0)  # 최대 3 시그마
                oi_accel_norm = min(abs(oi_accel), 0.3)        # 최대 30% 가속
                vol_accel_norm = min(abs(vol_accel), 0.02)     # 최대 2% 가속
                
                liquidation_risk = min(100, max(0, 
                    oi_growth_norm * 50 +         # 0~25점
                    funding_zscore_norm * 10 +    # 0~30점
                    oi_accel_norm * 50 +          # 0~15점
                    vol_accel_norm * 500          # 0~10점
                ))  # 총합 최대 80점 (극단 상황에서만 100)
            else:
                oi_growth_norm = min(abs(oi_growth), 0.5)
                funding_zscore_norm = min(abs(funding_zscore), 3.0)
                liquidation_risk = min(100, max(0, oi_growth_norm * 60 + funding_zscore_norm * 12))
            
            # 기본 지표
            indicators = {
                'whale_conc_change_7d': float(row.get('whale_conc_change_7d', 0) or 0),
                'funding_rate': float(row.get('avg_funding_rate', 0) or 0),
                'oi_growth_7d': float(row.get('oi_growth_7d', 0) or 0),
                'volatility_24h': float(row.get('volatility_24h', 0) or 0),
                'funding_rate_zscore': float(row.get('funding_rate_zscore', 0) or 0)
            }
            
            # 동적 지표 추가
            if self.include_dynamic:
                dynamic_indicators = self.get_dynamic_indicators(target_df)
                indicators.update(dynamic_indicators)
            
            return {
                'success': True,
                'model_type': self.model_type,
                'data': {
                    'date': target_date,
                    'high_volatility_prob': float(prob),
                    'risk_score': float(risk_score),
                    'liquidation_risk': float(liquidation_risk),
                    'indicators': indicators
                }
            }
            
        except Exception as e:
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
            
            # 특성 생성 (동적 변수 포함 여부에 따라)
            df, _ = self.feature_engineer.create_features(df, include_dynamic=self.include_dynamic)
            
            # 예측 기간 필터링
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            
            if len(df) == 0:
                return pd.DataFrame()
            
            # 예측 (dtype 변환)
            # 모델 features와 실제 데이터 features 매칭
            available_features = [f for f in self.features if f in df.columns]
            missing_features = [f for f in self.features if f not in df.columns]
            
            if missing_features:
                import logging
                logging.warning(f"누락된 features: {missing_features}. 0으로 채웁니다.")
            
            X = pd.DataFrame(index=df.index)
            for feature in self.features:
                if feature in df.columns:
                    X[feature] = pd.to_numeric(df[feature], errors='coerce').fillna(0.0).astype(float)
                else:
                    X[feature] = 0.0
            
            # 컬럼 순서를 모델 features 순서와 일치시킴
            X = X[self.features]
            
            probs = self.model.predict_proba(X)[:, 1]
            risk_scores = probs * 100
            
            # 청산 리스크 계산 (predict_risk와 동일한 로직 적용)
            oi_growth = df['oi_growth_7d'].fillna(0).astype(float)
            funding_zscore = df['funding_rate_zscore'].fillna(0).astype(float)
            
            # 동적 변수 포함 여부에 따라 다른 계산
            if self.include_dynamic:
                oi_accel = df.get('oi_accel', pd.Series(0, index=df.index)).fillna(0).astype(float)
                vol_accel = df.get('volatility_accel', pd.Series(0, index=df.index)).fillna(0).astype(float)
                
                # 스케일 정규화 (이상치 클리핑) - predict_risk와 동일
                oi_growth_norm = np.minimum(np.abs(oi_growth), 0.5)       # 최대 50% 변화
                funding_zscore_norm = np.minimum(np.abs(funding_zscore), 3.0)  # 최대 3 시그마
                oi_accel_norm = np.minimum(np.abs(oi_accel), 0.3)        # 최대 30% 가속
                vol_accel_norm = np.minimum(np.abs(vol_accel), 0.02)     # 최대 2% 가속
                
                liquidation_risks = np.minimum(100, np.maximum(0,
                    oi_growth_norm * 50 +         # 0~25점
                    funding_zscore_norm * 10 +    # 0~30점
                    oi_accel_norm * 50 +          # 0~15점
                    vol_accel_norm * 500          # 0~10점
                ))  # 총합 최대 80점
            else:
                oi_growth_norm = np.minimum(np.abs(oi_growth), 0.5)
                funding_zscore_norm = np.minimum(np.abs(funding_zscore), 3.0)
                liquidation_risks = np.minimum(100, np.maximum(0, oi_growth_norm * 60 + funding_zscore_norm * 12))
            
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
    
    def predict_risk_weekly(self, target_date: str, coin: str = 'BTC') -> Dict:
        """주봉 기반 특정 주의 리스크 예측
        
        Args:
            target_date: 예측할 주의 종료일 (YYYY-MM-DD, 일요일 기준)
            coin: 코인 심볼 ('BTC' 또는 'ETH')
        
        Returns:
            일봉 predict_risk()와 동일한 형식
        """
        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            start_date = (target_dt - timedelta(weeks=30)).strftime("%Y-%m-%d")
            end_date = target_date
            
            # 주봉 데이터 로드
            df = self.data_loader.load_risk_data_weekly(start_date, end_date, coin)
            
            if len(df) == 0:
                return {
                    'success': False,
                    'error': f"{target_date}에 대한 주봉 데이터가 없습니다."
                }
            
            # 주봉 특성 계산 (일봉과 다른 특성 사용)
            df['volatility_ma'] = df['volatility_ratio'].rolling(4).mean()
            df['whale_conc_change_4w'] = df['whale_conc_change_7d'].rolling(4).sum()
            df['rsi_zscore'] = (df['rsi'] - df['rsi'].rolling(12).mean()) / df['rsi'].rolling(12).std()
            df['volume_zscore'] = (df['volume'] - df['volume'].rolling(12).mean()) / df['volume'].rolling(12).std()
            
            # 타겟 주 찾기 (가장 가까운 주)
            df['date_diff'] = (df['date'].dt.date - target_dt.date()).abs()
            closest_idx = df['date_diff'].idxmin()
            row = df.loc[closest_idx]
            actual_date = row['date'].date()
            
            days_diff = abs((actual_date - target_dt.date()).days)
            if days_diff > 7:
                return {
                    'success': False,
                    'error': f"{target_date}에 대한 주봉 데이터가 없습니다. 가장 가까운 주: {actual_date} (차이: {days_diff}일)",
                    'closest_date': actual_date.strftime("%Y-%m-%d")
                }
            
            # 주봉 기반 리스크 점수 계산 (개선된 규칙 기반)
            volatility_score = min(100, max(0, float(row.get('volatility_ratio', 0) or 0) * 100))
            whale_score = min(100, max(0, abs(float(row.get('whale_conc_change_7d', 0) or 0)) * 200))
            rsi_score = abs(float(row.get('rsi', 50) or 50) - 50) * 2  # RSI 극단값일수록 높은 점수
            
            # 주봉 특성 반영: 변동성 가중치 증가, RSI 가중치 감소
            risk_score = (volatility_score * 0.5 + whale_score * 0.3 + rsi_score * 0.2)
            
            # 주봉 예측 확률 계산 개선: 더 민감하게 조정
            # 10점 이하는 0, 50점 이상은 1.0으로 매핑
            high_vol_prob = min(1.0, max(0, (risk_score - 10) / 40))
            
            # 청산 리스크 계산
            # 주봉 데이터에 OI와 펀딩비가 있으면 일봉과 동일한 방식으로 계산
            oi_growth_raw = row.get('oi_growth_7d')
            funding_zscore_raw = row.get('funding_rate_zscore')
            
            oi_growth = float(oi_growth_raw) if pd.notna(oi_growth_raw) else 0.0
            funding_zscore = float(funding_zscore_raw) if pd.notna(funding_zscore_raw) else 0.0
            
            has_oi = pd.notna(oi_growth_raw)
            has_funding = pd.notna(funding_zscore_raw)
            
            # OI와 펀딩비 데이터가 모두 있으면 일봉과 동일한 계산 방식 사용
            if has_oi and has_funding:
                # 일봉과 동일한 계산 방식
                oi_growth_norm = min(abs(oi_growth), 0.5)       # 최대 50% 변화
                funding_zscore_norm = min(abs(funding_zscore), 3.0)  # 최대 3 시그마
                liquidation_risk = min(100, max(0, oi_growth_norm * 60 + funding_zscore_norm * 12))
            else:
                # 기존 방식 (변동폭만 사용, 스케일 조정)
                weekly_range = float(row.get('weekly_range_pct', 0) or 0)
                # 주간 변동폭이 20%일 때 100%가 되도록 조정 (기존 10% → 20%로 변경)
                liquidation_risk = min(100, max(0, weekly_range * 5))
            
            # 지표 추출 (기본값 0 처리)
            indicators = {
                'whale_conc_change_7d': float(row.get('whale_conc_change_7d', 0) or 0),
                'volatility_ratio': float(row.get('volatility_ratio', 0) or 0),
                'rsi': float(row.get('rsi', 0) or 0),
                'weekly_range_pct': float(row.get('weekly_range_pct', 0) or 0),
                'weekly_return': float(row.get('weekly_return', 0) or 0),
                'avg_funding_rate': float(row.get('avg_funding_rate', 0) or 0),
                'sum_open_interest': float(row.get('sum_open_interest', 0) or 0),
                'oi_growth_7d': float(row.get('oi_growth_7d', 0) or 0),
                'funding_rate_zscore': float(row.get('funding_rate_zscore', 0) or 0)
            }
            
            return {
                'success': True,
                'data': {
                    'date': actual_date.strftime("%Y-%m-%d"),
                    'high_volatility_prob': float(high_vol_prob),
                    'risk_score': float(risk_score),
                    'liquidation_risk': float(liquidation_risk),
                    'indicators': indicators
                }
            }
            
        except Exception as e:
            import logging
            import traceback
            logging.error(f"주봉 예측 실패: {str(e)}\n{traceback.format_exc()}")
            return {
                'success': False,
                'error': f"주봉 예측 중 오류 발생: {str(e)}"
            }
    
    def predict_batch_weekly(self, start_date: str, end_date: str, coin: str = 'BTC') -> pd.DataFrame:
        """주봉 기반 기간별 리스크 예측
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            coin: 코인 심볼 ('BTC' 또는 'ETH')
        
        Returns:
            DataFrame with weekly risk predictions
        """
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            data_start_date = (start_dt - timedelta(weeks=30)).strftime("%Y-%m-%d")
            
            df = self.data_loader.load_risk_data_weekly(data_start_date, end_date, coin)
            
            if len(df) == 0:
                return pd.DataFrame()
            
            # 주봉 특성 계산
            df['volatility_ma'] = df['volatility_ratio'].rolling(4).mean()
            df['whale_conc_change_4w'] = df['whale_conc_change_7d'].rolling(4).sum()
            df['rsi_zscore'] = (df['rsi'] - df['rsi'].rolling(12).mean()) / df['rsi'].rolling(12).std()
            
            # 기간 필터링
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            
            if len(df) == 0:
                return pd.DataFrame()
            
            # 리스크 점수 계산 (주봉에 맞게 개선)
            volatility_scores = np.minimum(100, np.maximum(0, df['volatility_ratio'].fillna(0) * 100))
            whale_scores = np.minimum(100, np.maximum(0, np.abs(df['whale_conc_change_7d'].fillna(0)) * 200))
            rsi_scores = np.abs(df['rsi'].fillna(50) - 50) * 2
            
            # 주봉 특성 반영: 변동성 가중치 증가, RSI 가중치 감소
            risk_scores = (volatility_scores * 0.5 + whale_scores * 0.3 + rsi_scores * 0.2)
            
            # 주봉 예측 확률 계산 개선: 더 민감하게 조정
            # 주봉은 일봉보다 변동성이 평활화되므로 더 민감하게 반응하도록
            # risk_scores를 0~100 범위에서 0~1 범위로 변환하되, 스케일 조정
            # 20점 이하는 0, 80점 이상은 1.0으로 매핑 (더 넓은 범위 활용)
            high_vol_probs = np.minimum(1.0, np.maximum(0, (risk_scores - 20) / 60))
            
            # 청산 리스크 계산
            # OI와 펀딩비 데이터가 있으면 일봉과 동일한 방식으로 계산
            oi_growth = df['oi_growth_7d'].fillna(0)
            funding_zscore = df['funding_rate_zscore'].fillna(0)
            
            # OI와 펀딩비 데이터가 모두 있는 경우
            has_oi_funding = df['oi_growth_7d'].notna() & df['funding_rate_zscore'].notna()
            
            liquidation_risks = np.zeros(len(df))
            
            # OI/펀딩비 데이터가 있는 경우: 일봉과 동일한 계산
            if has_oi_funding.any():
                oi_growth_norm = np.minimum(np.abs(oi_growth), 0.5)
                funding_zscore_norm = np.minimum(np.abs(funding_zscore), 3.0)
                liquidation_risks[has_oi_funding] = np.minimum(100, np.maximum(0, 
                    oi_growth_norm[has_oi_funding] * 60 + 
                    funding_zscore_norm[has_oi_funding] * 12
                ))
            
            # OI/펀딩비 데이터가 없는 경우: 변동폭 기반 계산 (스케일 조정)
            if (~has_oi_funding).any():
                weekly_range = df['weekly_range_pct'].fillna(0)
                liquidation_risks[~has_oi_funding] = np.minimum(100, np.maximum(0, 
                    weekly_range[~has_oi_funding] * 5
                ))
            
            result_df = pd.DataFrame({
                'date': df['date'].dt.date,
                'high_volatility_prob': high_vol_probs,
                'risk_score': risk_scores,
                'liquidation_risk': liquidation_risks,
                'actual_high_vol': df.get('target_high_vol', None)  # 일봉과 동일하게 추가
            })
            
            return result_df
            
        except Exception as e:
            import logging
            import traceback
            logging.error(f"주봉 배치 예측 실패: {str(e)}\n{traceback.format_exc()}")
            return pd.DataFrame()

