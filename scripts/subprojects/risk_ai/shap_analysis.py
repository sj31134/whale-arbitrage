#!/usr/bin/env python3
"""
Project 3: Risk AI SHAP Analysis
특성 기여도 분석 및 시각화
"""

import pandas as pd
import numpy as np
from pathlib import Path
from feature_engineering import FeatureEngineer
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[3]

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("⚠️ SHAP가 설치되어 있지 않습니다.")
    print("   설치: pip install shap")

def main():
    if not SHAP_AVAILABLE:
        print("SHAP 분석을 수행할 수 없습니다.")
        return
    
    print("🔍 Project 3: Risk AI SHAP Analysis")
    print("=" * 80)
    
    fe = FeatureEngineer()
    
    # 1. 데이터 준비
    print("\n📊 데이터셋 생성 및 전처리 중...")
    train_df, test_df, features = fe.prepare_ml_dataset()
    
    X_train = train_df[features]
    y_train = train_df['target_high_vol']
    X_test = test_df[features]
    y_test = test_df['target_high_vol']
    
    # 2. 모델 학습
    print("\n🤖 모델 학습 중...")
    model = LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=5,
        random_state=42,
        class_weight='balanced',
        verbosity=-1
    )
    
    model.fit(X_train, y_train)
    
    # 3. SHAP 값 계산
    print("\n📊 SHAP 값 계산 중...")
    print("   (시간이 걸릴 수 있습니다)")
    
    # TreeExplainer 사용 (LightGBM에 최적화)
    explainer = shap.TreeExplainer(model)
    
    # 테스트 세트 샘플링 (전체 계산은 시간이 오래 걸림)
    sample_size = min(100, len(X_test))
    X_test_sample = X_test.sample(n=sample_size, random_state=42)
    y_test_sample = y_test.loc[X_test_sample.index]
    
    print(f"   샘플 크기: {sample_size}건")
    shap_values = explainer.shap_values(X_test_sample)
    
    # 이진 분류의 경우 shap_values는 리스트 [class_0, class_1]
    if isinstance(shap_values, list):
        shap_values = shap_values[1]  # class_1 (고변동성)에 대한 SHAP 값
    
    # 4. SHAP 요약 통계
    print("\n📈 SHAP 요약 통계")
    print("=" * 80)
    
    # 특성별 평균 절대 SHAP 값 (중요도)
    shap_importance = pd.DataFrame({
        'feature': features,
        'mean_abs_shap': np.abs(shap_values).mean(axis=0),
        'std_shap': shap_values.std(axis=0)
    }).sort_values('mean_abs_shap', ascending=False)
    
    print("\n특성별 평균 절대 SHAP 값 (중요도):")
    print(shap_importance.to_string(index=False))
    
    # 5. SHAP 값 저장
    output_dir = ROOT / "data" / "project3_shap"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # SHAP 값 DataFrame
    shap_df = pd.DataFrame(
        shap_values,
        columns=features,
        index=X_test_sample.index
    )
    shap_df['predicted_prob'] = model.predict_proba(X_test_sample)[:, 1]
    shap_df['actual_label'] = y_test_sample.values
    
    shap_df.to_csv(output_dir / "shap_values.csv")
    print(f"\n💾 SHAP 값 저장 완료: {output_dir / 'shap_values.csv'}")
    
    # 6. 특성별 기여도 분석
    print("\n📊 특성별 기여도 분석")
    print("=" * 80)
    
    for feature in features:
        feature_shap = shap_values[:, features.index(feature)]
        positive_contrib = (feature_shap > 0).sum()
        negative_contrib = (feature_shap < 0).sum()
        
        print(f"\n{feature}:")
        print(f"  평균 SHAP: {feature_shap.mean():.6f}")
        print(f"  표준편차: {feature_shap.std():.6f}")
        print(f"  양의 기여: {positive_contrib}건 ({positive_contrib/len(feature_shap)*100:.1f}%)")
        print(f"  음의 기여: {negative_contrib}건 ({negative_contrib/len(feature_shap)*100:.1f}%)")
    
    # 7. 개별 예측 해석 (샘플)
    print("\n🔍 개별 예측 해석 (샘플 3건)")
    print("=" * 80)
    
    # 고변동성 예측 확률이 높은 샘플
    high_prob_idx = shap_df.nlargest(3, 'predicted_prob').index
    
    for idx in high_prob_idx:
        print(f"\n샘플 {idx}:")
        print(f"  예측 확률: {shap_df.loc[idx, 'predicted_prob']:.4f}")
        print(f"  실제 레이블: {shap_df.loc[idx, 'actual_label']}")
        
        sample_shap = shap_values[shap_df.index.get_loc(idx)]
        top_contributors = pd.DataFrame({
            'feature': features,
            'shap_value': sample_shap
        }).sort_values('shap_value', ascending=False, key=abs)
        
        print(f"  주요 기여 특성 (상위 3개):")
        for _, row in top_contributors.head(3).iterrows():
            direction = "증가" if row['shap_value'] > 0 else "감소"
            print(f"    - {row['feature']}: {row['shap_value']:.6f} ({direction})")
    
    print("\n" + "=" * 80)
    print("✅ SHAP 분석 완료!")
    print("=" * 80)
    print(f"\n💡 시각화를 원하시면 다음 명령을 실행하세요:")
    print(f"   shap.summary_plot(shap_values, X_test_sample, feature_names=features)")
    print(f"   shap.waterfall_plot(explainer.expected_value[1], shap_values[0], X_test_sample.iloc[0], feature_names=features)")

if __name__ == "__main__":
    main()

