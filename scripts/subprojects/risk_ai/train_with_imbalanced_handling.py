#!/usr/bin/env python3
"""
Project 3: Risk AI Model Training with Imbalanced Data Handling
SMOTE 및 다른 불균형 데이터 처리 기법 적용
"""

import pandas as pd
import numpy as np
from pathlib import Path
from feature_engineering import FeatureEngineer
from lightgbm import LGBMClassifier
from sklearn.metrics import classification_report, roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[3]

try:
    from imblearn.over_sampling import SMOTE
    from imblearn.under_sampling import RandomUnderSampler
    from imblearn.combine import SMOTEENN
    IMBLEARN_AVAILABLE = True
except ImportError:
    IMBLEARN_AVAILABLE = False
    print("⚠️ imbalanced-learn이 설치되어 있지 않습니다.")
    print("   설치: pip install imbalanced-learn")

def evaluate_model(model, X_test, y_test, method_name):
    """모델 평가 및 결과 출력"""
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    try:
        auc = roc_auc_score(y_test, y_pred_proba)
    except ValueError:
        auc = 0.0
    
    print(f"\n{method_name} 결과:")
    print(f"  AUC-ROC: {auc:.4f}")
    print(f"\n  Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Normal', 'High Vol']))
    
    return auc, y_pred, y_pred_proba

def main():
    if not IMBLEARN_AVAILABLE:
        print("불균형 데이터 처리를 수행할 수 없습니다.")
        return
    
    print("⚖️ Project 3: Risk AI Model Training with Imbalanced Data Handling")
    print("=" * 80)
    
    fe = FeatureEngineer()
    
    # 1. 데이터 준비
    print("\n📊 데이터셋 생성 및 전처리 중...")
    train_df, test_df, features = fe.prepare_ml_dataset()
    
    X_train = train_df[features]
    y_train = train_df['target_high_vol']
    X_test = test_df[features]
    y_test = test_df['target_high_vol']
    
    print(f"   - 학습 데이터: {len(X_train)}건")
    print(f"   - 테스트 데이터: {len(X_test)}건")
    print(f"\n   클래스 분포 (Train):")
    print(f"     Normal (0): {(y_train == 0).sum()}건 ({(y_train == 0).sum()/len(y_train)*100:.1f}%)")
    print(f"     High Vol (1): {(y_train == 1).sum()}건 ({(y_train == 1).sum()/len(y_train)*100:.1f}%)")
    
    # 2. Baseline 모델 (불균형 처리 없음)
    print("\n" + "=" * 80)
    print("1️⃣ Baseline 모델 (불균형 처리 없음)")
    print("=" * 80)
    
    baseline_model = LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=5,
        random_state=42,
        class_weight='balanced',
        verbosity=-1
    )
    baseline_model.fit(X_train, y_train)
    baseline_auc, _, _ = evaluate_model(baseline_model, X_test, y_test, "Baseline")
    
    # 3. SMOTE (Synthetic Minority Oversampling)
    print("\n" + "=" * 80)
    print("2️⃣ SMOTE (Synthetic Minority Oversampling)")
    print("=" * 80)
    
    smote = SMOTE(random_state=42, k_neighbors=5)
    X_train_smote, y_train_smote = smote.fit_resample(X_train, y_train)
    
    print(f"   리샘플링 후:")
    print(f"     Normal (0): {(y_train_smote == 0).sum()}건")
    print(f"     High Vol (1): {(y_train_smote == 1).sum()}건")
    
    smote_model = LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=5,
        random_state=42,
        verbosity=-1
    )
    smote_model.fit(X_train_smote, y_train_smote)
    smote_auc, _, _ = evaluate_model(smote_model, X_test, y_test, "SMOTE")
    
    # 4. SMOTE + Random UnderSampling
    print("\n" + "=" * 80)
    print("3️⃣ SMOTE + Random UnderSampling")
    print("=" * 80)
    
    # 먼저 SMOTE로 오버샘플링
    X_train_smote, y_train_smote = smote.fit_resample(X_train, y_train)
    
    # 그 다음 언더샘플링 (비율 1:1로 맞춤)
    under = RandomUnderSampler(random_state=42)
    X_train_combined, y_train_combined = under.fit_resample(X_train_smote, y_train_smote)
    
    print(f"   리샘플링 후:")
    print(f"     Normal (0): {(y_train_combined == 0).sum()}건")
    print(f"     High Vol (1): {(y_train_combined == 1).sum()}건")
    
    combined_model = LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=5,
        random_state=42,
        verbosity=-1
    )
    combined_model.fit(X_train_combined, y_train_combined)
    combined_auc, _, _ = evaluate_model(combined_model, X_test, y_test, "SMOTE + UnderSampling")
    
    # 5. SMOTEENN (SMOTE + Edited Nearest Neighbours)
    print("\n" + "=" * 80)
    print("4️⃣ SMOTEENN (SMOTE + Edited Nearest Neighbours)")
    print("=" * 80)
    
    smoteenn = SMOTEENN(random_state=42)
    X_train_smoteenn, y_train_smoteenn = smoteenn.fit_resample(X_train, y_train)
    
    print(f"   리샘플링 후:")
    print(f"     Normal (0): {(y_train_smoteenn == 0).sum()}건")
    print(f"     High Vol (1): {(y_train_smoteenn == 1).sum()}건")
    
    smoteenn_model = LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=5,
        random_state=42,
        verbosity=-1
    )
    smoteenn_model.fit(X_train_smoteenn, y_train_smoteenn)
    smoteenn_auc, _, _ = evaluate_model(smoteenn_model, X_test, y_test, "SMOTEENN")
    
    # 6. 결과 비교
    print("\n" + "=" * 80)
    print("📊 최종 비교")
    print("=" * 80)
    
    results = pd.DataFrame({
        'Method': ['Baseline (class_weight)', 'SMOTE', 'SMOTE + UnderSampling', 'SMOTEENN'],
        'AUC-ROC': [baseline_auc, smote_auc, combined_auc, smoteenn_auc]
    }).sort_values('AUC-ROC', ascending=False)
    
    print("\nAUC-ROC 비교:")
    print(results.to_string(index=False))
    
    best_method = results.iloc[0]['Method']
    best_auc = results.iloc[0]['AUC-ROC']
    
    print(f"\n✅ 최고 성능: {best_method} (AUC-ROC: {best_auc:.4f})")
    
    # 7. 최고 성능 모델 저장
    if best_method == 'SMOTE':
        best_model = smote_model
    elif best_method == 'SMOTE + UnderSampling':
        best_model = combined_model
    elif best_method == 'SMOTEENN':
        best_model = smoteenn_model
    else:
        best_model = baseline_model
    
    # 예측 결과 저장
    y_pred_proba = best_model.predict_proba(X_test)[:, 1]
    y_pred = best_model.predict(X_test)
    
    result_df = test_df.copy()
    result_df['pred_prob'] = y_pred_proba
    result_df['pred_label'] = y_pred
    
    output_path = ROOT / "data" / "project3_risk_pred_results_imbalanced.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output_path, index=False)
    print(f"\n💾 예측 결과 저장 완료: {output_path}")

if __name__ == "__main__":
    main()

