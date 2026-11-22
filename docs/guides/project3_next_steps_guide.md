# 프로젝트 3 (Risk AI) 다음 단계 가이드

> **작성일**: 2025-11-23  
> **상태**: 우선순위 1 작업 완료, 다음 단계 준비 완료

---

## ✅ 완료된 작업

### 우선순위 1: 데이터 품질 개선
- ✅ `volatility_24h` 수집 로직 수정 (Binance Klines API 활용)
- ✅ `sum_open_interest` 수집 로직 개선
- ✅ 데이터 품질 검증 강화
- ✅ 모델 재학습 및 성능 평가

**결과**:
- AUC-ROC: 0.6342 → 0.6418 (약간 향상)
- `volatility_ratio` 특성이 의미 있는 값 획득

---

## 📋 다음 단계 실행 가이드

### 1. Time Series Cross-Validation (완료)

**파일**: `scripts/subprojects/risk_ai/train_model_with_cv.py`

**실행**:
```bash
cd /Users/junyonglee/Documents/GitHub/whale_tracking
python3 scripts/subprojects/risk_ai/train_model_with_cv.py
```

**결과**:
- 5-fold Time Series Cross-Validation 수행
- 평균 AUC-ROC: 0.5152 (+/- 0.0979)
- 모델의 일반화 성능 검증

---

### 2. 하이퍼파라미터 튜닝 (Optuna 필요)

**필요 패키지 설치**:
```bash
pip install optuna
```

**파일**: `scripts/subprojects/risk_ai/train_model_with_cv.py` (이미 구현됨)

**실행**:
```bash
python3 scripts/subprojects/risk_ai/train_model_with_cv.py
```

**설명**:
- Optuna가 설치되어 있으면 자동으로 하이퍼파라미터 튜닝 수행
- 50 trials로 최적 파라미터 탐색
- 주요 튜닝 파라미터:
  - `n_estimators`: 100 ~ 500
  - `learning_rate`: 0.01 ~ 0.1
  - `max_depth`: 3 ~ 10
  - `min_child_samples`: 10 ~ 100
  - `subsample`: 0.6 ~ 1.0
  - `colsample_bytree`: 0.6 ~ 1.0

---

### 3. SHAP 분석 (SHAP 필요)

**필요 패키지 설치**:
```bash
pip install shap
```

**파일**: `scripts/subprojects/risk_ai/shap_analysis.py`

**실행**:
```bash
python3 scripts/subprojects/risk_ai/shap_analysis.py
```

**결과**:
- 특성별 SHAP 값 계산
- 특성 중요도 분석
- 개별 예측 해석
- 결과 저장: `data/project3_shap/shap_values.csv`

**시각화** (선택사항):
```python
import shap
import pandas as pd
from pathlib import Path

ROOT = Path(".")
shap_df = pd.read_csv(ROOT / "data" / "project3_shap" / "shap_values.csv", index_col=0)

# Summary plot
shap.summary_plot(shap_values, X_test_sample, feature_names=features)

# Waterfall plot
shap.waterfall_plot(explainer.expected_value[1], shap_values[0], X_test_sample.iloc[0], feature_names=features)
```

---

### 4. 불균형 데이터 처리 (imbalanced-learn 필요)

**필요 패키지 설치**:
```bash
pip install imbalanced-learn
```

**파일**: `scripts/subprojects/risk_ai/train_with_imbalanced_handling.py`

**실행**:
```bash
python3 scripts/subprojects/risk_ai/train_with_imbalanced_handling.py
```

**기법**:
1. **Baseline**: `class_weight='balanced'`만 사용
2. **SMOTE**: 소수 클래스 오버샘플링
3. **SMOTE + UnderSampling**: 오버샘플링 + 언더샘플링 조합
4. **SMOTEENN**: SMOTE + Edited Nearest Neighbours

**결과**:
- 각 기법별 성능 비교
- 최고 성능 모델 자동 선택
- 결과 저장: `data/project3_risk_pred_results_imbalanced.csv`

---

## 🚀 전체 실행 순서 (권장)

### 1단계: 패키지 설치
```bash
pip install optuna shap imbalanced-learn
```

### 2단계: Time Series Cross-Validation 및 하이퍼파라미터 튜닝
```bash
python3 scripts/subprojects/risk_ai/train_model_with_cv.py
```

### 3단계: SHAP 분석
```bash
python3 scripts/subprojects/risk_ai/shap_analysis.py
```

### 4단계: 불균형 데이터 처리
```bash
python3 scripts/subprojects/risk_ai/train_with_imbalanced_handling.py
```

### 5단계: 결과 비교 및 분석
- 각 스크립트의 출력 결과 비교
- 최고 성능 모델 선택
- 최종 리포트 작성

---

## 📊 예상 개선 효과

### 하이퍼파라미터 튜닝 후
- **예상 AUC-ROC**: 0.65 ~ 0.75 (현재 0.64에서 향상)
- 최적 파라미터로 모델 성능 최적화

### 불균형 데이터 처리 후
- **예상 Precision (고변동성)**: 0.30 ~ 0.50 (현재 0.27에서 향상)
- **예상 Recall (고변동성)**: 0.50 ~ 0.70 (현재 0.50 유지 또는 향상)

### SHAP 분석 후
- 특성 기여도 명확히 파악
- 예측 결과 해석 가능
- 모델 신뢰성 향상

---

## 📁 생성되는 파일

1. `data/project3_risk_pred_results_tuned.csv` - 튜닝된 모델 예측 결과
2. `data/project3_shap/shap_values.csv` - SHAP 값 데이터
3. `data/project3_risk_pred_results_imbalanced.csv` - 불균형 처리 모델 예측 결과

---

## ⚠️ 주의사항

1. **시계열 데이터 특성**: SMOTE는 시계열 데이터에 직접 적용하기 어려울 수 있음
   - 시계열 특성을 고려한 변형 필요할 수 있음
   - 또는 시계열 특성을 제거하고 적용

2. **과적합 위험**: 하이퍼파라미터 튜닝 시 과적합 주의
   - Cross-Validation 결과와 Test 세트 결과 차이 확인
   - 일반화 성능 우선

3. **실행 시간**: 
   - 하이퍼파라미터 튜닝: 10-30분 (trials 수에 따라)
   - SHAP 분석: 5-10분 (샘플 크기에 따라)
   - 불균형 데이터 처리: 2-5분

---

## 🔗 참고 자료

- [Optuna Documentation](https://optuna.org/)
- [SHAP Documentation](https://shap.readthedocs.io/)
- [imbalanced-learn Documentation](https://imbalanced-learn.org/)
- [Time Series Cross-Validation](https://scikit-learn.org/stable/modules/cross_validation.html#time-series-split)

---

**작성자**: AI Assistant  
**마지막 업데이트**: 2025-11-23

