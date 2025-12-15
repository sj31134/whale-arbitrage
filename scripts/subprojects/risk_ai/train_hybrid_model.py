#!/usr/bin/env python3
"""
Project 3: 하이브리드 앙상블 모델 훈련

XGBoost (정적/동적 변수) + LSTM (시계열 패턴) + Meta Model (결합)
"""

import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# TensorFlow 경고 메시지 억제
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, accuracy_score

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))

from feature_engineering import FeatureEngineer

# LSTM 모델 임포트 (TensorFlow 있을 때만)
try:
    from train_lstm_model import LSTMRiskModel, HAS_TENSORFLOW
except ImportError:
    HAS_TENSORFLOW = False
    LSTMRiskModel = None

# 모델 저장 경로
MODEL_DIR = ROOT / "data" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


class HybridEnsembleModel:
    """
    하이브리드 앙상블 모델
    
    구조:
    1. XGBoost: 정적 + 동적 변수 처리 (테이블 형태 데이터에 강점)
    2. LSTM: 시계열 패턴 학습 (시간적 의존성 캡처)
    3. Meta Model (Logistic Regression): 두 모델의 예측값 결합
    """
    
    def __init__(self, sequence_length=30, use_lstm=True):
        """
        Args:
            sequence_length: LSTM 시퀀스 길이
            use_lstm: LSTM 모델 사용 여부 (TensorFlow 없으면 자동 비활성화)
        """
        self.sequence_length = sequence_length
        self.use_lstm = use_lstm and HAS_TENSORFLOW
        
        # 모델 컴포넌트
        self.xgb_model = None
        self.lstm_model = None
        self.meta_model = None
        
        # 스케일러
        self.xgb_scaler = StandardScaler()
        self.lstm_scaler = StandardScaler()
        
        # 메타데이터
        self.feature_names = None
        self.n_features = None
        
    def build_xgb_model(self):
        """XGBoost 모델 생성"""
        self.xgb_model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
            scale_pos_weight=2,  # 불균형 데이터 처리
            random_state=42,
            use_label_encoder=False,
            eval_metric='auc'
        )
        return self.xgb_model
    
    def build_lstm_model(self, n_features):
        """LSTM 모델 생성"""
        if not self.use_lstm:
            return None
        
        self.lstm_model = LSTMRiskModel(sequence_length=self.sequence_length)
        self.lstm_model.build_model(n_features)
        return self.lstm_model
    
    def build_meta_model(self):
        """메타 모델 생성 (Logistic Regression)"""
        self.meta_model = LogisticRegression(
            C=1.0,
            class_weight='balanced',
            random_state=42,
            max_iter=1000
        )
        return self.meta_model
    
    def fit(self, X_train, y_train, X_val=None, y_val=None, verbose=1):
        """
        앙상블 모델 학습
        
        Args:
            X_train: 학습 특성
            y_train: 학습 타겟
            X_val: 검증 특성 (옵션)
            y_val: 검증 타겟 (옵션)
            verbose: 출력 레벨
        """
        self.n_features = X_train.shape[1]
        
        # ============================================
        # 1. XGBoost 학습
        # ============================================
        if verbose:
            print("\n[1/3] XGBoost 모델 학습 중...")
        
        X_train_xgb = self.xgb_scaler.fit_transform(X_train)
        
        self.build_xgb_model()
        
        eval_set = [(X_train_xgb, y_train)]
        if X_val is not None and y_val is not None:
            X_val_xgb = self.xgb_scaler.transform(X_val)
            eval_set.append((X_val_xgb, y_val))
        
        self.xgb_model.fit(
            X_train_xgb, y_train,
            eval_set=eval_set,
            verbose=False
        )
        
        xgb_train_pred = self.xgb_model.predict_proba(X_train_xgb)[:, 1]
        if verbose:
            train_auc = roc_auc_score(y_train, xgb_train_pred) if len(np.unique(y_train)) > 1 else 0
            print(f"   XGBoost Train AUC: {train_auc:.4f}")
        
        # ============================================
        # 2. LSTM 학습 (선택적)
        # ============================================
        lstm_train_pred = None
        
        if self.use_lstm:
            if verbose:
                print("\n[2/3] LSTM 모델 학습 중...")
            
            self.build_lstm_model(self.n_features)
            
            # 검증 데이터 분리 (학습 데이터의 20%)
            val_split = int(len(X_train) * 0.8)
            X_train_lstm = X_train[:val_split]
            y_train_lstm = y_train[:val_split]
            X_val_lstm = X_train[val_split:]
            y_val_lstm = y_train[val_split:]
            
            self.lstm_model.fit(
                X_train_lstm, y_train_lstm,
                X_val=X_val_lstm, y_val=y_val_lstm,
                epochs=50,
                batch_size=32,
                verbose=0
            )
            
            # LSTM 예측 (시퀀스 길이만큼 앞부분 제외)
            lstm_train_pred_full = self.lstm_model.predict(X_train)
            
            # 패딩 (시퀀스 길이만큼 앞부분은 0으로)
            lstm_train_pred = np.zeros(len(X_train))
            lstm_train_pred[self.sequence_length:] = lstm_train_pred_full
            
            if verbose:
                valid_idx = self.sequence_length
                train_auc = roc_auc_score(y_train[valid_idx:], lstm_train_pred[valid_idx:]) if len(np.unique(y_train[valid_idx:])) > 1 else 0
                print(f"   LSTM Train AUC: {train_auc:.4f}")
        else:
            if verbose:
                print("\n[2/3] LSTM 건너뜀 (TensorFlow 미설치)")
        
        # ============================================
        # 3. Meta Model 학습
        # ============================================
        if verbose:
            print("\n[3/3] Meta Model 학습 중...")
        
        self.build_meta_model()
        
        # 메타 특성 생성
        if self.use_lstm:
            meta_features = np.column_stack([xgb_train_pred, lstm_train_pred])
        else:
            meta_features = xgb_train_pred.reshape(-1, 1)
        
        self.meta_model.fit(meta_features, y_train)
        
        meta_train_pred = self.meta_model.predict_proba(meta_features)[:, 1]
        if verbose:
            train_auc = roc_auc_score(y_train, meta_train_pred) if len(np.unique(y_train)) > 1 else 0
            print(f"   Meta Model Train AUC: {train_auc:.4f}")
        
        return self
    
    def predict_proba(self, X):
        """확률 예측"""
        # XGBoost 예측
        # - Streamlit Cloud 등 일부 환경에서 xgboost sklearn wrapper(XGBClassifier)와 scikit-learn 조합이
        #   _estimator_type 관련 호환 문제를 일으키는 사례가 있어,
        #   가능하면 Booster 기반 예측으로 우회합니다.
        X_xgb = self.xgb_scaler.transform(X)
        try:
            # Booster일 경우 (권장)
            if isinstance(self.xgb_model, xgb.Booster):
                dmat = xgb.DMatrix(X_xgb, feature_names=self.feature_names)
                xgb_pred = self.xgb_model.predict(dmat)
            else:
                # sklearn wrapper일 경우
                xgb_pred = self.xgb_model.predict_proba(X_xgb)[:, 1]
        except Exception as e:
            # 최후의 폴백: Booster로 강제 시도
            try:
                booster = getattr(self.xgb_model, "get_booster", None)
                if callable(booster):
                    dmat = xgb.DMatrix(X_xgb, feature_names=self.feature_names)
                    xgb_pred = booster().predict(dmat)
                else:
                    raise
            except Exception as e2:
                raise RuntimeError(f"XGBoost 예측 실패: {e} / Booster 폴백 실패: {e2}") from e2
        
        # LSTM 예측
        if self.use_lstm and self.lstm_model is not None:
            lstm_pred_full = self.lstm_model.predict(X)
            lstm_pred = np.zeros(len(X))
            lstm_pred[self.sequence_length:] = lstm_pred_full
            
            meta_features = np.column_stack([xgb_pred, lstm_pred])
        else:
            meta_features = xgb_pred.reshape(-1, 1)
        
        # Meta Model 예측
        proba = self.meta_model.predict_proba(meta_features)
        
        return proba
    
    def predict(self, X):
        """클래스 예측"""
        proba = self.predict_proba(X)
        return (proba[:, 1] > 0.5).astype(int)
    
    def evaluate(self, X_test, y_test):
        """모델 평가"""
        y_pred_proba = self.predict_proba(X_test)[:, 1]
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'auc_roc': roc_auc_score(y_test, y_pred_proba) if len(np.unique(y_test)) > 1 else 0
        }
        
        return metrics
    
    def get_component_predictions(self, X):
        """각 컴포넌트 모델의 개별 예측값 반환"""
        X_xgb = self.xgb_scaler.transform(X)
        xgb_pred = self.xgb_model.predict_proba(X_xgb)[:, 1]
        
        result = {'xgb': xgb_pred}
        
        if self.use_lstm and self.lstm_model is not None:
            lstm_pred_full = self.lstm_model.predict(X)
            lstm_pred = np.zeros(len(X))
            lstm_pred[self.sequence_length:] = lstm_pred_full
            result['lstm'] = lstm_pred
        
        result['ensemble'] = self.predict_proba(X)[:, 1]
        
        return result
    
    def save(self, model_name="hybrid_ensemble_model"):
        """모델 저장"""
        # XGBoost 저장
        xgb_path = MODEL_DIR / f"{model_name}_xgb.json"
        self.xgb_model.save_model(xgb_path)
        
        # XGBoost 스케일러 저장
        xgb_scaler_path = MODEL_DIR / f"{model_name}_xgb_scaler.pkl"
        with open(xgb_scaler_path, 'wb') as f:
            pickle.dump(self.xgb_scaler, f)
        
        # LSTM 저장 (있으면)
        if self.use_lstm and self.lstm_model is not None:
            self.lstm_model.save(f"{model_name}_lstm")
        
        # Meta Model 저장
        meta_path = MODEL_DIR / f"{model_name}_meta.pkl"
        with open(meta_path, 'wb') as f:
            pickle.dump(self.meta_model, f)
        
        # 메타데이터 저장
        metadata = {
            'sequence_length': self.sequence_length,
            'use_lstm': self.use_lstm,
            'n_features': self.n_features,
            'feature_names': self.feature_names,
            'created_at': datetime.now().isoformat()
        }
        metadata_path = MODEL_DIR / f"{model_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ 앙상블 모델 저장 완료: {MODEL_DIR / model_name}")
    
    def load(self, model_name="hybrid_ensemble_model"):
        """모델 로드"""
        # 메타데이터 로드
        metadata_path = MODEL_DIR / f"{model_name}_metadata.json"
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        self.sequence_length = metadata['sequence_length']
        self.use_lstm = metadata['use_lstm']
        self.n_features = metadata['n_features']
        self.feature_names = metadata.get('feature_names')
        
        # XGBoost 로드
        xgb_path = MODEL_DIR / f"{model_name}_xgb.json"
        # Streamlit Cloud 등에서 sklearn wrapper 호환 문제가 있을 수 있어 Booster로 로드 (권장)
        try:
            self.xgb_model = xgb.Booster()
            self.xgb_model.load_model(xgb_path)
        except Exception:
            # 폴백: sklearn wrapper로 로드
            self.xgb_model = xgb.XGBClassifier()
            self.xgb_model.load_model(xgb_path)
        
        # XGBoost 스케일러 로드
        xgb_scaler_path = MODEL_DIR / f"{model_name}_xgb_scaler.pkl"
        with open(xgb_scaler_path, 'rb') as f:
            self.xgb_scaler = pickle.load(f)
        
        # LSTM 로드 (있으면)
        if self.use_lstm and HAS_TENSORFLOW:
            self.lstm_model = LSTMRiskModel(sequence_length=self.sequence_length)
            try:
                self.lstm_model.load(f"{model_name}_lstm")
            except FileNotFoundError:
                print("⚠️ LSTM 모델 파일 없음, LSTM 비활성화")
                self.use_lstm = False
        
        # Meta Model 로드
        meta_path = MODEL_DIR / f"{model_name}_meta.pkl"
        with open(meta_path, 'rb') as f:
            self.meta_model = pickle.load(f)
        
        print(f"✅ 앙상블 모델 로드 완료: {model_name}")


def train_hybrid_model(include_dynamic=True, use_lstm=True):
    """하이브리드 앙상블 모델 학습"""
    
    print("=" * 80)
    print("📊 하이브리드 앙상블 모델 학습")
    print("=" * 80)
    
    # 데이터 준비
    print("\n[1/4] 데이터 준비 중...")
    fe = FeatureEngineer()
    train_df, test_df, feature_cols = fe.prepare_ml_dataset(include_dynamic=include_dynamic)
    
    print(f"   학습 데이터: {len(train_df)}일")
    print(f"   테스트 데이터: {len(test_df)}일")
    print(f"   특성 수: {len(feature_cols)}")
    print(f"   동적 변수 포함: {include_dynamic}")
    print(f"   LSTM 사용: {use_lstm and HAS_TENSORFLOW}")
    
    # 특성 및 타겟 분리
    X_train = train_df[feature_cols].values
    y_train = train_df['target_high_vol'].values
    X_test = test_df[feature_cols].values
    y_test = test_df['target_high_vol'].values
    
    # 모델 생성 및 학습
    print("\n[2/4] 앙상블 모델 학습 중...")
    model = HybridEnsembleModel(sequence_length=30, use_lstm=use_lstm)
    model.feature_names = feature_cols
    
    model.fit(X_train, y_train, verbose=1)
    
    # 평가
    print("\n[3/4] 모델 평가 중...")
    metrics = model.evaluate(X_test, y_test)
    
    print("\n📊 테스트 결과:")
    print(f"   Accuracy: {metrics['accuracy']:.4f}")
    print(f"   Precision: {metrics['precision']:.4f}")
    print(f"   Recall: {metrics['recall']:.4f}")
    print(f"   F1 Score: {metrics['f1']:.4f}")
    print(f"   AUC-ROC: {metrics['auc_roc']:.4f}")
    
    # 컴포넌트별 성능 비교
    print("\n📊 컴포넌트별 예측 비교:")
    component_preds = model.get_component_predictions(X_test)
    
    for name, pred in component_preds.items():
        if len(np.unique(y_test)) > 1:
            auc = roc_auc_score(y_test, pred)
            print(f"   {name.upper()}: AUC = {auc:.4f}")
    
    # 모델 저장
    print("\n[4/4] 모델 저장 중...")
    model_name = "hybrid_ensemble_dynamic" if include_dynamic else "hybrid_ensemble_static"
    model.save(model_name)
    
    # 결과 저장
    results = {
        'model_name': model_name,
        'include_dynamic': include_dynamic,
        'use_lstm': use_lstm and HAS_TENSORFLOW,
        'n_features': len(feature_cols),
        'train_samples': len(train_df),
        'test_samples': len(test_df),
        'metrics': metrics,
        'trained_at': datetime.now().isoformat()
    }
    
    results_path = MODEL_DIR / f"{model_name}_results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ 결과 저장: {results_path}")
    print("\n" + "=" * 80)
    print("✅ 하이브리드 앙상블 모델 학습 완료!")
    print("=" * 80)
    
    return model, metrics


def main():
    """메인 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description="하이브리드 앙상블 모델 학습")
    parser.add_argument("--no-dynamic", action="store_true", 
                        help="동적 변수 제외")
    parser.add_argument("--no-lstm", action="store_true",
                        help="LSTM 모델 제외 (XGBoost만 사용)")
    
    args = parser.parse_args()
    
    train_hybrid_model(
        include_dynamic=not args.no_dynamic,
        use_lstm=not args.no_lstm
    )


if __name__ == "__main__":
    main()

