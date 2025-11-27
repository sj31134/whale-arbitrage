#!/usr/bin/env python3
"""
Project 3: LSTM 시계열 모델 훈련

동적 변수를 활용한 시계열 패턴 학습을 위한 LSTM 모델 구현
- 시퀀스 데이터 생성
- LSTM 모델 구조
- 학습 및 평가
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

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, Model, load_model
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Input, BatchNormalization
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
    from tensorflow.keras.optimizers import Adam
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False
    print("⚠️ TensorFlow가 설치되지 않았습니다. pip install tensorflow 실행 필요")

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, accuracy_score

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))

from feature_engineering import FeatureEngineer

# 모델 저장 경로
MODEL_DIR = ROOT / "data" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


class LSTMRiskModel:
    """LSTM 기반 리스크 예측 모델"""
    
    def __init__(self, sequence_length=30, n_features=None):
        """
        Args:
            sequence_length: 입력 시퀀스 길이 (일 수)
            n_features: 특성 수 (자동 설정 가능)
        """
        self.sequence_length = sequence_length
        self.n_features = n_features
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None
        self.history = None
        
    def build_model(self, n_features):
        """LSTM 모델 구조 정의"""
        if not HAS_TENSORFLOW:
            raise ImportError("TensorFlow가 필요합니다.")
        
        self.n_features = n_features
        
        model = Sequential([
            # 첫 번째 LSTM 레이어
            LSTM(64, return_sequences=True, 
                 input_shape=(self.sequence_length, n_features)),
            BatchNormalization(),
            Dropout(0.2),
            
            # 두 번째 LSTM 레이어
            LSTM(32, return_sequences=False),
            BatchNormalization(),
            Dropout(0.2),
            
            # Dense 레이어
            Dense(16, activation='relu'),
            Dropout(0.1),
            
            # 출력 레이어 (이진 분류)
            Dense(1, activation='sigmoid')
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='binary_crossentropy',
            metrics=['accuracy', tf.keras.metrics.AUC(name='auc')]
        )
        
        self.model = model
        return model
    
    def create_sequences(self, X, y=None):
        """
        시계열 데이터를 LSTM 입력 형태로 변환
        
        Args:
            X: 특성 데이터 (n_samples, n_features)
            y: 타겟 데이터 (n_samples,)
        
        Returns:
            X_seq: (n_samples - sequence_length, sequence_length, n_features)
            y_seq: (n_samples - sequence_length,) if y is not None
        """
        X_seq = []
        y_seq = []
        
        for i in range(len(X) - self.sequence_length):
            X_seq.append(X[i:i + self.sequence_length])
            if y is not None:
                y_seq.append(y[i + self.sequence_length])
        
        X_seq = np.array(X_seq)
        
        if y is not None:
            y_seq = np.array(y_seq)
            return X_seq, y_seq
        
        return X_seq
    
    def fit(self, X_train, y_train, X_val=None, y_val=None, 
            epochs=100, batch_size=32, verbose=1):
        """
        모델 학습
        
        Args:
            X_train: 학습 특성 데이터
            y_train: 학습 타겟 데이터
            X_val: 검증 특성 데이터
            y_val: 검증 타겟 데이터
            epochs: 학습 에폭 수
            batch_size: 배치 크기
            verbose: 출력 레벨
        """
        # 스케일링
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # 시퀀스 생성
        X_train_seq, y_train_seq = self.create_sequences(X_train_scaled, y_train)
        
        # 모델 빌드
        if self.model is None:
            self.build_model(X_train.shape[1])
        
        # 콜백 설정
        callbacks = [
            EarlyStopping(
                monitor='val_auc' if X_val is not None else 'auc',
                patience=10,
                mode='max',
                restore_best_weights=True
            ),
            ReduceLROnPlateau(
                monitor='val_loss' if X_val is not None else 'loss',
                factor=0.5,
                patience=5,
                min_lr=1e-6
            )
        ]
        
        # 검증 데이터 준비
        validation_data = None
        if X_val is not None and y_val is not None:
            X_val_scaled = self.scaler.transform(X_val)
            X_val_seq, y_val_seq = self.create_sequences(X_val_scaled, y_val)
            validation_data = (X_val_seq, y_val_seq)
        
        # 학습
        self.history = self.model.fit(
            X_train_seq, y_train_seq,
            validation_data=validation_data,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=verbose
        )
        
        return self.history
    
    def predict(self, X):
        """예측 수행"""
        X_scaled = self.scaler.transform(X)
        X_seq = self.create_sequences(X_scaled)
        
        predictions = self.model.predict(X_seq, verbose=0)
        return predictions.flatten()
    
    def predict_proba(self, X):
        """확률 예측 (sklearn 호환)"""
        probs = self.predict(X)
        return np.column_stack([1 - probs, probs])
    
    def evaluate(self, X_test, y_test):
        """모델 평가"""
        X_test_scaled = self.scaler.transform(X_test)
        X_test_seq, y_test_seq = self.create_sequences(X_test_scaled, y_test)
        
        # 예측
        y_pred_proba = self.model.predict(X_test_seq, verbose=0).flatten()
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        # 메트릭 계산
        metrics = {
            'accuracy': accuracy_score(y_test_seq, y_pred),
            'precision': precision_score(y_test_seq, y_pred, zero_division=0),
            'recall': recall_score(y_test_seq, y_pred, zero_division=0),
            'f1': f1_score(y_test_seq, y_pred, zero_division=0),
            'auc_roc': roc_auc_score(y_test_seq, y_pred_proba) if len(np.unique(y_test_seq)) > 1 else 0
        }
        
        return metrics
    
    def save(self, model_name="lstm_risk_model"):
        """모델 저장"""
        # Keras 모델 저장
        model_path = MODEL_DIR / f"{model_name}.keras"
        self.model.save(model_path)
        
        # 스케일러 저장
        scaler_path = MODEL_DIR / f"{model_name}_scaler.pkl"
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        # 메타데이터 저장
        metadata = {
            'sequence_length': self.sequence_length,
            'n_features': self.n_features,
            'feature_names': self.feature_names,
            'created_at': datetime.now().isoformat()
        }
        metadata_path = MODEL_DIR / f"{model_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ 모델 저장 완료: {model_path}")
    
    def load(self, model_name="lstm_risk_model"):
        """모델 로드"""
        model_path = MODEL_DIR / f"{model_name}.keras"
        scaler_path = MODEL_DIR / f"{model_name}_scaler.pkl"
        metadata_path = MODEL_DIR / f"{model_name}_metadata.json"
        
        if not model_path.exists():
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")
        
        # 모델 로드
        self.model = load_model(model_path)
        
        # 스케일러 로드
        with open(scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)
        
        # 메타데이터 로드
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        self.sequence_length = metadata['sequence_length']
        self.n_features = metadata['n_features']
        self.feature_names = metadata.get('feature_names')
        
        print(f"✅ 모델 로드 완료: {model_path}")


def train_lstm_model(include_dynamic=True, sequence_length=30):
    """LSTM 모델 학습 실행"""
    
    if not HAS_TENSORFLOW:
        print("❌ TensorFlow가 설치되지 않아 LSTM 학습을 건너뜁니다.")
        return None
    
    print("=" * 80)
    print("📊 LSTM 리스크 예측 모델 학습")
    print("=" * 80)
    
    # 데이터 준비
    print("\n[1/4] 데이터 준비 중...")
    fe = FeatureEngineer()
    train_df, test_df, feature_cols = fe.prepare_ml_dataset(include_dynamic=include_dynamic)
    
    print(f"   학습 데이터: {len(train_df)}일")
    print(f"   테스트 데이터: {len(test_df)}일")
    print(f"   특성 수: {len(feature_cols)}")
    print(f"   동적 변수 포함: {include_dynamic}")
    
    # 특성 및 타겟 분리
    X_train = train_df[feature_cols].values
    y_train = train_df['target_high_vol'].values
    X_test = test_df[feature_cols].values
    y_test = test_df['target_high_vol'].values
    
    # 모델 생성 및 학습
    print("\n[2/4] LSTM 모델 학습 중...")
    model = LSTMRiskModel(sequence_length=sequence_length)
    model.feature_names = feature_cols
    
    # 검증 데이터 분리 (학습 데이터의 20%)
    val_split = int(len(X_train) * 0.8)
    X_train_fit = X_train[:val_split]
    y_train_fit = y_train[:val_split]
    X_val = X_train[val_split:]
    y_val = y_train[val_split:]
    
    history = model.fit(
        X_train_fit, y_train_fit,
        X_val=X_val, y_val=y_val,
        epochs=100,
        batch_size=32,
        verbose=1
    )
    
    # 평가
    print("\n[3/4] 모델 평가 중...")
    metrics = model.evaluate(X_test, y_test)
    
    print("\n📊 테스트 결과:")
    print(f"   Accuracy: {metrics['accuracy']:.4f}")
    print(f"   Precision: {metrics['precision']:.4f}")
    print(f"   Recall: {metrics['recall']:.4f}")
    print(f"   F1 Score: {metrics['f1']:.4f}")
    print(f"   AUC-ROC: {metrics['auc_roc']:.4f}")
    
    # 모델 저장
    print("\n[4/4] 모델 저장 중...")
    model_name = "lstm_risk_model_dynamic" if include_dynamic else "lstm_risk_model_static"
    model.save(model_name)
    
    # 결과 저장
    results = {
        'model_name': model_name,
        'include_dynamic': include_dynamic,
        'sequence_length': sequence_length,
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
    print("✅ LSTM 모델 학습 완료!")
    print("=" * 80)
    
    return model, metrics


def main():
    """메인 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LSTM 리스크 예측 모델 학습")
    parser.add_argument("--no-dynamic", action="store_true", 
                        help="동적 변수 제외")
    parser.add_argument("--sequence-length", type=int, default=30,
                        help="시퀀스 길이 (기본값: 30)")
    
    args = parser.parse_args()
    
    train_lstm_model(
        include_dynamic=not args.no_dynamic,
        sequence_length=args.sequence_length
    )


if __name__ == "__main__":
    main()

