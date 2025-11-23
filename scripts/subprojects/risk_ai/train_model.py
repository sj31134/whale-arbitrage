#!/usr/bin/env python3
"""
Project 3: Risk AI Model Training & Evaluation
"""

import pandas as pd
import numpy as np
from feature_engineering import FeatureEngineer
from lightgbm import LGBMClassifier
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix

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
    
    print(f"AUC-ROC: {roc_auc_score(y_test, y_pred_proba):.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # 4. 특성 중요도
    print("\n🔍 특성 중요도 (Top 5)")
    importance = pd.DataFrame({
        'feature': features,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(importance.head())
    
    # 5. 예측 결과 저장
    result_df = test_df.copy()
    result_df['pred_prob'] = y_pred_proba
    result_df['pred_label'] = y_pred
    
    result_df.to_csv("data/project3_risk_pred_results.csv", index=False)
    print(f"\n💾 예측 결과 저장 완료: data/project3_risk_pred_results.csv")

if __name__ == "__main__":
    main()

