#!/usr/bin/env python3
"""
Project 3: 모델 평가 및 비교

여러 모델의 성능을 비교하고 결과를 시각화합니다:
- 기존 XGBoost (정적 변수)
- XGBoost (정적 + 동적 변수)
- LSTM (동적 변수)
- 하이브리드 앙상블
"""

import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import xgboost as xgb
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score, 
    accuracy_score, confusion_matrix, classification_report,
    roc_curve, precision_recall_curve
)
from sklearn.model_selection import TimeSeriesSplit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))

from feature_engineering import FeatureEngineer

# 모델 임포트
try:
    from train_lstm_model import LSTMRiskModel, HAS_TENSORFLOW
except ImportError:
    HAS_TENSORFLOW = False
    LSTMRiskModel = None

try:
    from train_hybrid_model import HybridEnsembleModel
except ImportError:
    HybridEnsembleModel = None

MODEL_DIR = ROOT / "data" / "models"
RESULTS_DIR = ROOT / "data" / "models" / "evaluation"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_existing_model():
    """기존 학습된 XGBoost 모델 로드"""
    model_path = MODEL_DIR / "risk_ai_model.pkl"
    if not model_path.exists():
        return None
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    return model


def evaluate_model(model, X_test, y_test, model_name="model"):
    """모델 평가 및 메트릭 계산"""
    
    # 예측
    if hasattr(model, 'predict_proba'):
        y_pred_proba = model.predict_proba(X_test)[:, 1]
    else:
        y_pred_proba = model.predict(X_test)
    
    y_pred = (y_pred_proba > 0.5).astype(int)
    
    # 기본 메트릭
    metrics = {
        'model_name': model_name,
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred, zero_division=0),
        'recall': recall_score(y_test, y_pred, zero_division=0),
        'f1': f1_score(y_test, y_pred, zero_division=0),
        'auc_roc': roc_auc_score(y_test, y_pred_proba) if len(np.unique(y_test)) > 1 else 0
    }
    
    # 혼동 행렬
    cm = confusion_matrix(y_test, y_pred)
    metrics['confusion_matrix'] = cm.tolist()
    
    # ROC 곡선 데이터
    fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
    metrics['roc_curve'] = {'fpr': fpr.tolist(), 'tpr': tpr.tolist()}
    
    # Precision-Recall 곡선 데이터
    precision_curve, recall_curve, _ = precision_recall_curve(y_test, y_pred_proba)
    metrics['pr_curve'] = {
        'precision': precision_curve.tolist(), 
        'recall': recall_curve.tolist()
    }
    
    return metrics


def time_series_cv_evaluate(model_class, X, y, feature_cols, n_splits=5, **model_kwargs):
    """시계열 교차 검증"""
    
    tscv = TimeSeriesSplit(n_splits=n_splits)
    
    cv_results = []
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        
        # 모델 생성 및 학습
        if model_class == xgb.XGBClassifier:
            model = model_class(**model_kwargs)
            model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
        elif model_class == HybridEnsembleModel:
            model = model_class(**model_kwargs)
            model.fit(X_train, y_train, verbose=0)
        else:
            model = model_class(**model_kwargs)
            model.fit(X_train, y_train)
        
        # 예측 및 평가
        if hasattr(model, 'predict_proba'):
            y_pred_proba = model.predict_proba(X_test)[:, 1]
        else:
            y_pred_proba = model.predict(X_test)
        
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        fold_metrics = {
            'fold': fold + 1,
            'train_size': len(train_idx),
            'test_size': len(test_idx),
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'auc_roc': roc_auc_score(y_test, y_pred_proba) if len(np.unique(y_test)) > 1 else 0
        }
        
        cv_results.append(fold_metrics)
    
    # 평균 계산
    avg_metrics = {
        'accuracy_mean': np.mean([r['accuracy'] for r in cv_results]),
        'accuracy_std': np.std([r['accuracy'] for r in cv_results]),
        'precision_mean': np.mean([r['precision'] for r in cv_results]),
        'precision_std': np.std([r['precision'] for r in cv_results]),
        'recall_mean': np.mean([r['recall'] for r in cv_results]),
        'recall_std': np.std([r['recall'] for r in cv_results]),
        'f1_mean': np.mean([r['f1'] for r in cv_results]),
        'f1_std': np.std([r['f1'] for r in cv_results]),
        'auc_roc_mean': np.mean([r['auc_roc'] for r in cv_results]),
        'auc_roc_std': np.std([r['auc_roc'] for r in cv_results]),
    }
    
    return cv_results, avg_metrics


def compare_models(include_lstm=True):
    """여러 모델 비교"""
    
    print("=" * 80)
    print("📊 모델 성능 비교 평가")
    print("=" * 80)
    
    # 데이터 준비
    print("\n[1/5] 데이터 준비 중...")
    fe = FeatureEngineer()
    
    # 정적 변수만
    train_static, test_static, static_features = fe.prepare_ml_dataset(include_dynamic=False)
    
    # 정적 + 동적 변수
    train_dynamic, test_dynamic, dynamic_features = fe.prepare_ml_dataset(include_dynamic=True)
    
    print(f"   정적 변수: {len(static_features)}개")
    print(f"   동적 변수 포함: {len(dynamic_features)}개")
    print(f"   학습 데이터: {len(train_dynamic)}일")
    print(f"   테스트 데이터: {len(test_dynamic)}일")
    
    # 데이터 분리
    X_train_static = train_static[static_features].values
    y_train_static = train_static['target_high_vol'].values
    X_test_static = test_static[static_features].values
    y_test_static = test_static['target_high_vol'].values
    
    X_train_dynamic = train_dynamic[dynamic_features].values
    y_train_dynamic = train_dynamic['target_high_vol'].values
    X_test_dynamic = test_dynamic[dynamic_features].values
    y_test_dynamic = test_dynamic['target_high_vol'].values
    
    results = {}
    
    # ============================================
    # 모델 1: XGBoost (정적 변수만)
    # ============================================
    print("\n[2/5] XGBoost (정적 변수) 평가 중...")
    
    xgb_static = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        random_state=42,
        use_label_encoder=False,
        eval_metric='auc'
    )
    xgb_static.fit(X_train_static, y_train_static, 
                   eval_set=[(X_test_static, y_test_static)], verbose=False)
    
    results['xgb_static'] = evaluate_model(xgb_static, X_test_static, y_test_static, "XGBoost (Static)")
    print(f"   AUC-ROC: {results['xgb_static']['auc_roc']:.4f}")
    
    # ============================================
    # 모델 2: XGBoost (정적 + 동적 변수)
    # ============================================
    print("\n[3/5] XGBoost (정적 + 동적 변수) 평가 중...")
    
    xgb_dynamic = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        random_state=42,
        use_label_encoder=False,
        eval_metric='auc'
    )
    xgb_dynamic.fit(X_train_dynamic, y_train_dynamic,
                    eval_set=[(X_test_dynamic, y_test_dynamic)], verbose=False)
    
    results['xgb_dynamic'] = evaluate_model(xgb_dynamic, X_test_dynamic, y_test_dynamic, "XGBoost (Dynamic)")
    print(f"   AUC-ROC: {results['xgb_dynamic']['auc_roc']:.4f}")
    
    # ============================================
    # 모델 3: LSTM (선택적)
    # ============================================
    if include_lstm and HAS_TENSORFLOW and LSTMRiskModel is not None:
        print("\n[4/5] LSTM 모델 평가 중...")
        
        lstm_model = LSTMRiskModel(sequence_length=30)
        
        # 검증 데이터 분리
        val_split = int(len(X_train_dynamic) * 0.8)
        X_train_lstm = X_train_dynamic[:val_split]
        y_train_lstm = y_train_dynamic[:val_split]
        X_val_lstm = X_train_dynamic[val_split:]
        y_val_lstm = y_train_dynamic[val_split:]
        
        lstm_model.fit(X_train_lstm, y_train_lstm, 
                       X_val=X_val_lstm, y_val=y_val_lstm,
                       epochs=50, verbose=0)
        
        # LSTM 평가 (시퀀스 길이 고려)
        lstm_metrics = lstm_model.evaluate(X_test_dynamic, y_test_dynamic)
        lstm_metrics['model_name'] = "LSTM"
        results['lstm'] = lstm_metrics
        print(f"   AUC-ROC: {results['lstm']['auc_roc']:.4f}")
    else:
        print("\n[4/5] LSTM 건너뜀 (TensorFlow 미설치)")
    
    # ============================================
    # 모델 4: 하이브리드 앙상블
    # ============================================
    if HybridEnsembleModel is not None:
        print("\n[5/5] 하이브리드 앙상블 모델 평가 중...")
        
        hybrid_model = HybridEnsembleModel(
            sequence_length=30, 
            use_lstm=include_lstm and HAS_TENSORFLOW
        )
        hybrid_model.fit(X_train_dynamic, y_train_dynamic, verbose=0)
        
        results['hybrid'] = evaluate_model(hybrid_model, X_test_dynamic, y_test_dynamic, "Hybrid Ensemble")
        print(f"   AUC-ROC: {results['hybrid']['auc_roc']:.4f}")
    else:
        print("\n[5/5] 하이브리드 앙상블 건너뜀")
    
    # ============================================
    # 결과 요약
    # ============================================
    print("\n" + "=" * 80)
    print("📊 모델 성능 비교 요약")
    print("=" * 80)
    
    summary_df = pd.DataFrame([
        {
            'Model': r['model_name'],
            'Accuracy': r['accuracy'],
            'Precision': r['precision'],
            'Recall': r['recall'],
            'F1': r['f1'],
            'AUC-ROC': r['auc_roc']
        }
        for r in results.values()
    ])
    
    print("\n" + summary_df.to_string(index=False, float_format='%.4f'))
    
    # 개선율 계산
    if 'xgb_static' in results and 'xgb_dynamic' in results:
        static_auc = results['xgb_static']['auc_roc']
        dynamic_auc = results['xgb_dynamic']['auc_roc']
        improvement = (dynamic_auc - static_auc) / static_auc * 100
        print(f"\n📈 동적 변수 추가 효과: AUC-ROC {improvement:+.2f}% 개선")
    
    if 'hybrid' in results and 'xgb_dynamic' in results:
        xgb_auc = results['xgb_dynamic']['auc_roc']
        hybrid_auc = results['hybrid']['auc_roc']
        improvement = (hybrid_auc - xgb_auc) / xgb_auc * 100
        print(f"📈 앙상블 효과: AUC-ROC {improvement:+.2f}% 개선")
    
    # 결과 저장
    results_path = RESULTS_DIR / f"model_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # numpy 타입 변환
    def convert_to_serializable(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(i) for i in obj]
        return obj
    
    results_serializable = convert_to_serializable(results)
    
    with open(results_path, 'w') as f:
        json.dump(results_serializable, f, indent=2)
    
    print(f"\n✅ 결과 저장: {results_path}")
    
    # 요약 CSV 저장
    summary_path = RESULTS_DIR / "model_comparison_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"✅ 요약 저장: {summary_path}")
    
    return results, summary_df


def feature_importance_analysis():
    """특성 중요도 분석"""
    
    print("\n" + "=" * 80)
    print("📊 특성 중요도 분석")
    print("=" * 80)
    
    # 데이터 준비
    fe = FeatureEngineer()
    train_df, test_df, feature_cols = fe.prepare_ml_dataset(include_dynamic=True)
    
    X_train = train_df[feature_cols].values
    y_train = train_df['target_high_vol'].values
    
    # XGBoost 모델 학습
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        random_state=42,
        use_label_encoder=False,
        eval_metric='auc'
    )
    model.fit(X_train, y_train, verbose=False)
    
    # 특성 중요도 추출
    importance = model.feature_importances_
    
    importance_df = pd.DataFrame({
        'feature': feature_cols,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    print("\n상위 20개 중요 특성:")
    print(importance_df.head(20).to_string(index=False))
    
    # 동적 변수 중요도 분석
    dynamic_features = [
        'volatility_delta', 'oi_delta', 'funding_delta', 
        'volatility_accel', 'oi_accel', 'funding_accel',
        'volatility_slope', 'oi_slope', 'funding_slope'
    ]
    
    dynamic_importance = importance_df[importance_df['feature'].isin(dynamic_features)]
    
    if not dynamic_importance.empty:
        print("\n동적 변수 중요도:")
        print(dynamic_importance.to_string(index=False))
        
        total_dynamic_importance = dynamic_importance['importance'].sum()
        total_importance = importance_df['importance'].sum()
        print(f"\n동적 변수 기여도: {total_dynamic_importance / total_importance * 100:.2f}%")
    
    # 저장
    importance_path = RESULTS_DIR / "feature_importance.csv"
    importance_df.to_csv(importance_path, index=False)
    print(f"\n✅ 특성 중요도 저장: {importance_path}")
    
    return importance_df


def main():
    """메인 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description="모델 평가 및 비교")
    parser.add_argument("--no-lstm", action="store_true", help="LSTM 제외")
    parser.add_argument("--feature-importance", action="store_true", 
                        help="특성 중요도 분석만 실행")
    
    args = parser.parse_args()
    
    if args.feature_importance:
        feature_importance_analysis()
    else:
        compare_models(include_lstm=not args.no_lstm)
        feature_importance_analysis()


if __name__ == "__main__":
    main()

