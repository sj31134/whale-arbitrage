#!/usr/bin/env python3
"""
Project 3: Risk AI Model Training with Time Series Cross-Validation & Hyperparameter Tuning
"""

import pandas as pd
import numpy as np
from pathlib import Path
from feature_engineering import FeatureEngineer
from lightgbm import LGBMClassifier
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix, precision_recall_curve
from sklearn.model_selection import TimeSeriesSplit

# Optuna import 체크
try:
    import optuna
    from optuna.integration import LightGBMPruningCallback
    OPTUNA_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    OPTUNA_AVAILABLE = False

ROOT = Path(__file__).resolve().parents[3]


def time_series_cross_validation(X, y, n_splits=5):
    """Time Series Cross-Validation 수행"""
    tscv = TimeSeriesSplit(n_splits=n_splits)
    cv_scores = []
    
    print(f"\n📊 Time Series Cross-Validation ({n_splits}-fold)")
    print("=" * 80)
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
        X_train_fold = X.iloc[train_idx]
        y_train_fold = y.iloc[train_idx]
        X_val_fold = X.iloc[val_idx]
        y_val_fold = y.iloc[val_idx]
        
        print(f"\nFold {fold}/{n_splits}:")
        print(f"  Train: {len(X_train_fold)}건 ({X_train_fold.index[0]} ~ {X_train_fold.index[-1]})")
        print(f"  Val:   {len(X_val_fold)}건 ({X_val_fold.index[0]} ~ {X_val_fold.index[-1]})")
        
        # 모델 학습
        model = LGBMClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            random_state=42,
            class_weight='balanced',
            verbosity=-1
        )
        
        model.fit(X_train_fold, y_train_fold)
        
        # 평가
        y_pred_proba = model.predict_proba(X_val_fold)[:, 1]
        
        try:
            auc = roc_auc_score(y_val_fold, y_pred_proba)
            cv_scores.append(auc)
            print(f"  AUC-ROC: {auc:.4f}")
        except ValueError as e:
            print(f"  ⚠️ AUC-ROC 계산 불가: {e}")
            cv_scores.append(0.0)
    
    print(f"\n📈 Cross-Validation 결과:")
    print(f"  평균 AUC-ROC: {np.mean(cv_scores):.4f} (+/- {np.std(cv_scores):.4f})")
    print(f"  최소: {np.min(cv_scores):.4f}")
    print(f"  최대: {np.max(cv_scores):.4f}")
    
    return cv_scores


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
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[LightGBMPruningCallback(trial, 'binary_logloss')]
    )
    
    y_pred_proba = model.predict_proba(X_val)[:, 1]
    
    try:
        auc = roc_auc_score(y_val, y_pred_proba)
        return auc
    except ValueError:
        return 0.0


def hyperparameter_tuning(X_train, y_train, X_val, y_val, n_trials=50):
    """Optuna를 사용한 하이퍼파라미터 튜닝"""
    if not OPTUNA_AVAILABLE:
        print("\n⚠️ Optuna가 설치되어 있지 않습니다. 하이퍼파라미터 튜닝을 건너뜁니다.")
        print("   설치: pip install optuna")
        default_params = {
            'n_estimators': 200,
            'learning_rate': 0.05,
            'max_depth': 5,
            'min_child_samples': 20,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 0.1,
            'class_weight': 'balanced',
            'random_state': 42,
            'verbosity': -1
        }
        
        # 기본 파라미터로 모델 학습하여 AUC 계산
        model = LGBMClassifier(**default_params)
        model.fit(X_train, y_train)
        y_pred_proba = model.predict_proba(X_val)[:, 1]
        try:
            auc = roc_auc_score(y_val, y_pred_proba)
        except ValueError:
            auc = 0.0
        
        return default_params, auc
    
    print(f"\n🔧 하이퍼파라미터 튜닝 시작 (Optuna, {n_trials} trials)")
    print("=" * 80)
    
    study = optuna.create_study(
        direction='maximize',
        study_name='risk_ai_hyperparameter_tuning'
    )
    
    study.optimize(
        lambda trial: objective(trial, X_train, y_train, X_val, y_val),
        n_trials=n_trials,
        show_progress_bar=True
    )
    
    print(f"\n✅ 최적 파라미터:")
    print(f"  AUC-ROC: {study.best_value:.4f}")
    print(f"\n  파라미터:")
    for key, value in study.best_params.items():
        print(f"    {key}: {value}")
    
    return study.best_params, study.best_value


def main():
    print("🧠 Project 3: Risk AI Model Training (with CV & Hyperparameter Tuning)")
    print("=" * 80)
    
    fe = FeatureEngineer()
    
    # 1. 데이터 준비
    print("\n📊 데이터셋 생성 및 전처리 중...")
    train_df, test_df, features = fe.prepare_ml_dataset()
    
    print(f"   - 학습 데이터: {len(train_df)}건")
    print(f"   - 테스트 데이터: {len(test_df)}건")
    print(f"   - 사용 특성: {features}")
    
    if len(train_df) < 100:
        print("⚠️ 학습 데이터 부족으로 중단")
        return
    
    X_train = train_df[features]
    y_train = train_df['target_high_vol']
    
    X_test = test_df[features]
    y_test = test_df['target_high_vol']
    
    # 2. Time Series Cross-Validation
    cv_scores = time_series_cross_validation(X_train, y_train, n_splits=5)
    
    # 3. 하이퍼파라미터 튜닝 (Train 데이터를 다시 Train/Val로 분할)
    print("\n" + "=" * 80)
    split_idx = int(len(X_train) * 0.8)
    X_train_tune = X_train.iloc[:split_idx]
    y_train_tune = y_train.iloc[:split_idx]
    X_val_tune = X_train.iloc[split_idx:]
    y_val_tune = y_train.iloc[split_idx:]
    
    best_params, best_auc = hyperparameter_tuning(
        X_train_tune, y_train_tune, X_val_tune, y_val_tune, n_trials=50
    )
    
    # 4. 최적 파라미터로 최종 모델 학습
    print("\n" + "=" * 80)
    print("🤖 최적 파라미터로 최종 모델 학습 중...")
    
    final_model = LGBMClassifier(**best_params)
    final_model.fit(X_train, y_train)
    
    # 5. 테스트 세트 평가
    print("\n📝 테스트 세트 평가 결과")
    print("=" * 80)
    
    y_pred = final_model.predict(X_test)
    y_pred_proba = final_model.predict_proba(X_test)[:, 1]
    
    try:
        test_auc = roc_auc_score(y_test, y_pred_proba)
        print(f"AUC-ROC: {test_auc:.4f}")
    except ValueError as e:
        print(f"⚠️ AUC-ROC 계산 불가: {e}")
        test_auc = 0.0
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # 6. 특성 중요도
    print("\n🔍 특성 중요도 (Top 5)")
    importance = pd.DataFrame({
        'feature': features,
        'importance': final_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(importance.head())
    
    # 7. 예측 결과 저장
    result_df = test_df.copy()
    result_df['pred_prob'] = y_pred_proba
    result_df['pred_label'] = y_pred
    
    output_path = ROOT / "data" / "project3_risk_pred_results_tuned.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False)
    print(f"\n💾 예측 결과 저장 완료: {output_path}")
    
    # 8. 요약 리포트
    print("\n" + "=" * 80)
    print("📊 최종 요약")
    print("=" * 80)
    print(f"Cross-Validation AUC-ROC: {np.mean(cv_scores):.4f} (+/- {np.std(cv_scores):.4f})")
    print(f"Validation AUC-ROC (튜닝): {best_auc:.4f}")
    print(f"Test AUC-ROC: {test_auc:.4f}")
    print(f"\n최적 파라미터:")
    for key, value in best_params.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()

