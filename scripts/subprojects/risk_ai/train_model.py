#!/usr/bin/env python3
"""
Project 3: Risk AI Model Training & Evaluation
"""

import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
from feature_engineering import FeatureEngineer
from lightgbm import LGBMClassifier
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix, precision_score, recall_score, f1_score

ROOT = Path(__file__).resolve().parents[3]

def main():
    print("🧠 Project 3: Risk AI Model Training 시작")
    
    fe = FeatureEngineer()
    
    # 1. 데이터 준비
    print("📊 데이터셋 생성 및 전처리 중...")
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
    
    # 2. 모델 학습 (LightGBM)
    print("\n🤖 모델 학습 중 (LightGBM)...")
    model = LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=5,
        random_state=42,
        class_weight='balanced', # 고변동성 구간이 적으므로 불균형 처리
        verbosity=-1
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[] 
    )
    
    # 3. 평가
    print("\n📝 모델 평가 결과")
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # AUC-ROC 계산 (클래스가 하나만 있으면 계산 불가)
    try:
        auc_score = roc_auc_score(y_test, y_pred_proba)
        print(f"AUC-ROC: {auc_score:.4f}")
    except ValueError as e:
        print(f"⚠️ AUC-ROC 계산 불가: {e}")
        print("   (타겟 변수에 하나의 클래스만 존재)")
        auc_score = 0.0
    
    print("\nClassification Report:")
    report = classification_report(y_test, y_pred, output_dict=True)
    print(classification_report(y_test, y_pred))
    
    # Precision, Recall, F1-Score 계산
    try:
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
    except:
        precision = report.get('1', {}).get('precision', 0.0)
        recall = report.get('1', {}).get('recall', 0.0)
        f1 = report.get('1', {}).get('f1-score', 0.0)
    
    # 4. 특성 중요도
    print("\n🔍 특성 중요도 (Top 5)")
    importance = pd.DataFrame({
        'feature': features,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(importance.head())
    
    # 5. 모델 저장
    print("\n💾 모델 저장 중...")
    models_dir = ROOT / "data" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # 모델 저장
    model_path = models_dir / "risk_ai_model.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"   ✅ 모델 저장 완료: {model_path}")
    
    # 특성 목록 저장
    features_path = models_dir / "risk_ai_features.json"
    with open(features_path, 'w') as f:
        json.dump(features, f, indent=2)
    print(f"   ✅ 특성 목록 저장 완료: {features_path}")
    
    # 메타데이터 저장
    metadata = {
        'auc_roc': float(auc_score),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1),
        'train_size': int(len(train_df)),
        'test_size': int(len(test_df)),
        'n_features': len(features),
        'feature_importance': {
            feature: float(importance.loc[importance['feature'] == feature, 'importance'].values[0])
            for feature in features
        }
    }
    metadata_path = models_dir / "risk_ai_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"   ✅ 메타데이터 저장 완료: {metadata_path}")
    
    # 6. 예측 결과 저장
    result_df = test_df.copy()
    result_df['pred_prob'] = y_pred_proba
    result_df['pred_label'] = y_pred
    
    output_path = ROOT / "data" / "project3_risk_pred_results.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False)
    print(f"\n💾 예측 결과 저장 완료: {output_path}")

if __name__ == "__main__":
    main()

