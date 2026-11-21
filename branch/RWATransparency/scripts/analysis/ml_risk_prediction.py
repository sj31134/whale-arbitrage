"""
ML Risk Prediction Model for RWA

목표: 향후 급락/디페깅 이벤트 발생 확률 예측
모델: XGBoost + SHAP 설명가능성
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report, confusion_matrix
)
from sklearn.preprocessing import StandardScaler
import warnings
import os

warnings.filterwarnings('ignore')

def prepare_features(df: pd.DataFrame) -> tuple:
    """
    ML 모델용 피처 준비.
    """
    # 결측치 제거
    df_clean = df.dropna(subset=['tail_event', 'tdt_score', 'illiquidity', 'volatility'])
    
    # 피처 선택
    feature_cols = [
        'tdt_score',
        'latency_score',
        'completeness_score', 
        'consistency_score',
        'volatility',
        'illiquidity',
        'macro_shock'
    ]
    
    X = df_clean[feature_cols].copy()
    y = df_clean['tail_event'].astype(int)
    
    # 시총 로그 변환 추가
    X['market_cap_log'] = np.log(df_clean['market_cap'] + 1)
    
    return X, y, feature_cols + ['market_cap_log']

def train_models(X_train, X_test, y_train, y_test):
    """
    여러 모델 학습 및 비교.
    """
    models = {
        'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42, max_depth=5),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=3)
    }
    
    results = []
    trained_models = {}
    
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else y_pred
        
        results.append({
            'Model': name,
            'Accuracy': accuracy_score(y_test, y_pred),
            'Precision': precision_score(y_test, y_pred, zero_division=0),
            'Recall': recall_score(y_test, y_pred, zero_division=0),
            'F1': f1_score(y_test, y_pred, zero_division=0),
            'AUC': roc_auc_score(y_test, y_prob) if len(np.unique(y_test)) > 1 else 0.5
        })
        trained_models[name] = model
    
    return pd.DataFrame(results), trained_models

def compute_feature_importance(model, feature_names: list) -> pd.DataFrame:
    """
    피처 중요도 계산 (SHAP 대용).
    """
    if hasattr(model, 'feature_importances_'):
        importance = model.feature_importances_
    elif hasattr(model, 'coef_'):
        importance = np.abs(model.coef_[0])
    else:
        return pd.DataFrame()
    
    df_importance = pd.DataFrame({
        'Feature': feature_names,
        'Importance': importance
    }).sort_values('Importance', ascending=False)
    
    return df_importance

def create_risk_score_card(model, X: pd.DataFrame, feature_names: list) -> pd.DataFrame:
    """
    리스크 스코어 카드 생성 (거래소/VC용).
    """
    probs = model.predict_proba(X)[:, 1]
    
    # 리스크 등급 분류
    risk_levels = pd.cut(probs, 
                         bins=[0, 0.1, 0.3, 0.5, 1.0],
                         labels=['Low', 'Medium', 'High', 'Critical'])
    
    return pd.DataFrame({
        'Risk_Probability': probs,
        'Risk_Level': risk_levels
    })

def main():
    base_path = os.path.dirname(__file__)
    panel_data_path = os.path.join(base_path, '../../data/processed/panel_data.csv')
    output_path = os.path.join(base_path, '../../data/processed/ml_results.csv')
    importance_path = os.path.join(base_path, '../../data/processed/feature_importance.csv')
    
    print("=" * 60)
    print("RWA Risk Prediction: ML Model Training")
    print("=" * 60)
    
    # 데이터 로드
    df = pd.read_csv(panel_data_path)
    print(f"Loaded {len(df)} observations")
    
    # 피처 준비
    X, y, feature_names = prepare_features(df)
    print(f"Features: {feature_names}")
    print(f"Target distribution: {y.value_counts().to_dict()}")
    
    # 데이터 분할
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # 스케일링
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 모델 학습
    print("\n=== Model Training ===")
    df_results, trained_models = train_models(X_train_scaled, X_test_scaled, y_train, y_test)
    print(df_results.to_string(index=False))
    
    # 최고 성능 모델 선택
    best_model_name = df_results.loc[df_results['AUC'].idxmax(), 'Model']
    best_model = trained_models[best_model_name]
    print(f"\n✅ Best Model: {best_model_name}")
    
    # 피처 중요도
    print("\n=== Feature Importance ===")
    df_importance = compute_feature_importance(best_model, feature_names)
    print(df_importance.to_string(index=False))
    
    # 분류 리포트
    print("\n=== Classification Report (Best Model) ===")
    y_pred = best_model.predict(X_test_scaled)
    print(classification_report(y_test, y_pred, target_names=['No Event', 'Tail Event']))
    
    # 결과 저장
    df_results.to_csv(output_path, index=False)
    df_importance.to_csv(importance_path, index=False)
    
    print(f"\nResults saved to: {output_path}")
    print(f"Feature importance saved to: {importance_path}")
    
    # 리스크 스코어 카드 샘플
    print("\n=== Risk Score Card (Sample) ===")
    risk_scores = create_risk_score_card(best_model, X_test_scaled[:10], feature_names)
    print(risk_scores.to_string(index=False))

if __name__ == "__main__":
    main()
