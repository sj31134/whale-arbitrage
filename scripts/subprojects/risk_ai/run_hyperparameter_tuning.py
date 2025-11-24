#!/usr/bin/env python3
"""
하이퍼파라미터 튜닝만 실행하는 스크립트
"""

import pandas as pd
import numpy as np
from pathlib import Path
from feature_engineering import FeatureEngineer
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score
import optuna
try:
    from optuna.integration import LightGBMPruningCallback
except ImportError:
    # optuna-integration이 없으면 callback 없이 진행
    LightGBMPruningCallback = None

ROOT = Path(__file__).resolve().parents[3]

def objective(trial, X_train, y_train, X_val, y_val):
    """Optuna objective function"""
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 500),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'min_child_samples': trial.suggest_int('min_child_samples', 10, 100),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
        'class_weight': 'balanced',
        'random_state': 42,
        'verbosity': -1
    }
    
    model = LGBMClassifier(**params)
    
    if LightGBMPruningCallback:
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[LightGBMPruningCallback(trial, 'binary_logloss')]
        )
    else:
        model.fit(X_train, y_train)
    
    y_pred_proba = model.predict_proba(X_val)[:, 1]
    
    try:
        auc = roc_auc_score(y_val, y_pred_proba)
        return auc
    except ValueError:
        return 0.0

def main():
    print("🔧 Project 3: Risk AI Hyperparameter Tuning")
    print("=" * 80)
    
    fe = FeatureEngineer()
    
    # 데이터 준비
    print("\n📊 데이터셋 생성 및 전처리 중...")
    train_df, test_df, features = fe.prepare_ml_dataset()
    
    X_train = train_df[features]
    y_train = train_df['target_high_vol']
    
    # Train 데이터를 Train/Val로 분할
    split_idx = int(len(X_train) * 0.8)
    X_train_tune = X_train.iloc[:split_idx]
    y_train_tune = y_train.iloc[:split_idx]
    X_val_tune = X_train.iloc[split_idx:]
    y_val_tune = y_train.iloc[split_idx:]
    
    print(f"   - 튜닝용 Train: {len(X_train_tune)}건")
    print(f"   - 튜닝용 Val: {len(X_val_tune)}건")
    
    # 하이퍼파라미터 튜닝
    print(f"\n🔧 하이퍼파라미터 튜닝 시작 (Optuna, 50 trials)")
    print("=" * 80)
    
    study = optuna.create_study(
        direction='maximize',
        study_name='risk_ai_hyperparameter_tuning'
    )
    
    study.optimize(
        lambda trial: objective(trial, X_train_tune, y_train_tune, X_val_tune, y_val_tune),
        n_trials=50,
        show_progress_bar=True
    )
    
    print(f"\n✅ 최적 파라미터:")
    print(f"  AUC-ROC: {study.best_value:.4f}")
    print(f"\n  파라미터:")
    for key, value in study.best_params.items():
        print(f"    {key}: {value}")
    
    # 최적 파라미터로 최종 모델 학습
    print("\n" + "=" * 80)
    print("🤖 최적 파라미터로 최종 모델 학습 중...")
    
    best_params = study.best_params.copy()
    best_params['class_weight'] = 'balanced'
    best_params['random_state'] = 42
    best_params['verbosity'] = -1
    
    final_model = LGBMClassifier(**best_params)
    final_model.fit(X_train, y_train)
    
    # 테스트 세트 평가
    X_test = test_df[features]
    y_test = test_df['target_high_vol']
    
    y_pred_proba = final_model.predict_proba(X_test)[:, 1]
    test_auc = roc_auc_score(y_test, y_pred_proba)
    
    print(f"\n📝 테스트 세트 평가:")
    print(f"  AUC-ROC: {test_auc:.4f}")
    print(f"  (Validation: {study.best_value:.4f})")
    
    # 결과 저장
    result_df = test_df.copy()
    result_df['pred_prob'] = y_pred_proba
    result_df['pred_label'] = final_model.predict(X_test)
    
    output_path = ROOT / "data" / "project3_risk_pred_results_optuna.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False)
    print(f"\n💾 예측 결과 저장 완료: {output_path}")

if __name__ == "__main__":
    main()

