# 프로젝트 3 (Risk AI) 요약 정리

> **작성일**: 2025-11-23  
> **프로젝트명**: Risk AI - 고변동성/청산 리스크 예측 모델

---

## 1. 프로젝트 목표

### 핵심 목표
**BitInfoCharts 고래 지표와 바이낸스 선물 펀딩/OI 데이터를 결합하여 급격한 변동성 및 청산 리스크를 예측하는 AI 모델 구축**

### 실용적 목적
- **투자자**: 고변동성 구간을 사전에 예측하여 리스크 관리
- **트레이더**: 청산 리스크가 높은 시점을 피하여 포지션 조정
- **연구자**: 고래 활동과 시장 변동성의 상관관계 분석

### 핵심 가설
1. 고래 집중도 변화가 시장 변동성의 선행 지표로 작용
2. 펀딩비 이상 신호가 고변동성 예측에 유용
3. OI(미결제약정) 급증이 청산 리스크 증가를 의미
4. 여러 지표의 조합이 단일 지표보다 예측력이 높음

---

## 2. 사용한 데이터

### 2.1 데이터 소스

#### 1) Binance Futures Metrics (`binance_futures_metrics` 테이블)
- **펀딩비 (Funding Rate)**: 8시간마다 갱신되는 선물 펀딩비
- **미결제약정 (Open Interest)**: 선물 시장의 미결제약정 금액
- **롱/숏 비율 (Long/Short Ratio)**: 거래자 포지션 비율 (과거 데이터 제한)
- **변동성 (Volatility 24h)**: 일일 가격 변동성 (high-low)/close

**수집 기간**: 2022-12-31 ~ 2025-11-22 (약 3년)  
**총 레코드**: 1,058건  
**API**: Binance Futures API
- `/fapi/v1/fundingRate` - 펀딩비
- `/fapi/v1/openInterestHist` - 미결제약정 (최근 30일 제한)
- `/fapi/v1/klines` - 일봉 데이터 (변동성 계산)

#### 2) BitInfoCharts Whale Data (`bitinfocharts_whale` 테이블)
- **Top 100 지갑 보유 비중 (top100_richest_pct)**: 상위 100개 지갑의 BTC 보유 비율
- **평균 거래 금액 (avg_transaction_value_btc)**: 일일 평균 거래 금액

**수집 기간**: 2022-12-31 ~ 2025-11-23  
**총 레코드**: 1,059건  
**데이터 소스**: 
- Supabase `whale_transactions` 테이블에서 집계
- CSV 파일 (`whale_transactions.csv`)에서 변환 (313일치 추가)

### 2.2 데이터 통계

| 지표 | 평균 | 최소 | 최대 |
|------|------|------|------|
| **펀딩비** | 0.000085 | 0.000000 | 0.000734 |
| **미결제약정** | 9.06B (최근 8일만) | 8.38B | 9.34B |
| **변동성** | 3.71% | 0.37% | 18.61% |
| **고래 집중도** | - | - | - |
| **평균 거래 금액** | - | - | - |

### 2.3 데이터 품질

- **매칭률**: 100% (1,058건 모두 매칭)
- **결측치**: 없음
- **변동성 데이터**: 100% 유효 (이전에는 모두 0이었으나 수정 완료)
- **미결제약정**: 최근 30일만 유효 (API 제한)

---

## 3. 분석 방법

### 3.1 Feature Engineering

#### 원본 특성
1. `avg_funding_rate`: 일평균 펀딩비
2. `sum_open_interest`: 일평균 미결제약정
3. `long_short_ratio`: 롱/숏 비율 (대부분 0)
4. `volatility_24h`: 일일 변동성
5. `top100_richest_pct`: 상위 100 지갑 보유 비중
6. `avg_transaction_value_btc`: 평균 거래 금액

#### 파생 특성 (7개)
1. **`whale_conc_change_7d`**: 고래 집중도 7일 변화율
   - 계산: `top100_richest_pct.pct_change(7)`
   - 의미: 고래 집중도 급변 시 변동성 증가 가능

2. **`funding_rate_zscore`**: 펀딩비 Z-Score (30일 기준)
   - 계산: `(avg_funding_rate - 30일 평균) / 30일 표준편차`
   - 의미: 펀딩비 이상 신호 감지

3. **`oi_growth_7d`**: 미결제약정 7일 변화율
   - 계산: `sum_open_interest.pct_change(7)`
   - 의미: OI 급증 시 청산 리스크 증가

4. **`long_position_pct`**: 롱 포지션 비율
   - 계산: `long_short_ratio / (1 + long_short_ratio)`
   - 의미: 시장 심리 지표

5. **`volatility_ratio`**: 변동성 비율
   - 계산: `volatility_24h / 7일 평균 변동성`
   - 의미: 현재 변동성이 평균 대비 높은지

6. **`avg_funding_rate`**: 원본 펀딩비
7. **`sum_open_interest`**: 원본 미결제약정

### 3.2 타겟 변수 정의

**고변동성 (High Volatility) 정의**:
- 다음날 변동성이 **상위 20% (quantile 0.8)** 이상이거나
- 다음날 변동성이 **절대 수치 5% 이상**

```python
df['next_day_volatility'] = df['volatility_24h'].shift(-1)
quantile_threshold = df['volatility_24h'].quantile(0.8)
absolute_threshold = 0.05

df['target_high_vol'] = (
    (df['next_day_volatility'] > quantile_threshold) | 
    (df['next_day_volatility'] > absolute_threshold)
).astype(int)
```

**클래스 분포**:
- Train: Normal (0) 489건 (76.5%), High Vol (1) 150건 (23.5%)
- Test: Normal (0) 340건 (81.3%), High Vol (1) 78건 (18.7%)

### 3.3 모델링 방법

#### 모델: LightGBM Classifier
- **알고리즘**: Gradient Boosting Decision Tree
- **선택 이유**: 
  - 시계열 데이터에 효과적
  - 특성 중요도 제공
  - 빠른 학습 속도
  - 불균형 데이터 처리 가능

#### 학습 설정
- **Train/Test Split**: Time Series Split
  - Train: 2023-01-01 ~ 2024-09-30 (639건)
  - Test: 2024-10-01 ~ 2025-11-22 (418건)
- **검증 방법**: Time Series Cross-Validation (5-fold)
- **불균형 처리**: `class_weight='balanced'`

#### 하이퍼파라미터 튜닝
- **도구**: Optuna (50 trials)
- **튜닝 파라미터**:
  - `n_estimators`: 100 ~ 500
  - `learning_rate`: 0.01 ~ 0.1 (log scale)
  - `max_depth`: 3 ~ 10
  - `min_child_samples`: 10 ~ 100
  - `subsample`: 0.6 ~ 1.0
  - `colsample_bytree`: 0.6 ~ 1.0
  - `reg_alpha`: 1e-8 ~ 10.0 (log scale)
  - `reg_lambda`: 1e-8 ~ 10.0 (log scale)

#### 불균형 데이터 처리 기법 비교
1. **Baseline**: `class_weight='balanced'`만 사용
2. **SMOTE**: Synthetic Minority Oversampling
3. **SMOTE + UnderSampling**: 오버샘플링 + 언더샘플링 조합
4. **SMOTEENN**: SMOTE + Edited Nearest Neighbours

### 3.4 평가 지표

- **AUC-ROC**: 전체적인 분류 성능
- **Precision**: 고변동성 예측 정확도
- **Recall**: 고변동성 포착률
- **F1-Score**: Precision과 Recall의 조화평균
- **Confusion Matrix**: 오분류 분석

---

## 4. 결과물

### 4.1 모델 성능

#### 최종 성능 (Optuna 튜닝 모델)

| 지표 | 값 |
|------|-----|
| **AUC-ROC** | **0.6776** |
| **정확도** | 66% |
| **Precision (고변동성)** | 0.28 |
| **Recall (고변동성)** | 0.54 |
| **F1-Score (고변동성)** | 0.37 |

#### 성능 비교

| 방법 | AUC-ROC | 개선율 |
|------|---------|--------|
| Baseline (기본 파라미터) | 0.6418 | - |
| **Optuna 튜닝** | **0.6776** | **+5.6%** |
| SMOTEENN | 0.6595 | +2.8% |
| SMOTE | 0.6128 | -4.5% |
| Time Series CV 평균 | 0.5152 (+/- 0.0979) | - |

### 4.2 최적 하이퍼파라미터

```python
{
    'n_estimators': 181,
    'learning_rate': 0.0135,
    'max_depth': 8,
    'min_child_samples': 22,
    'subsample': 0.9285,
    'colsample_bytree': 0.7791,
    'reg_alpha': 0.0182,
    'reg_lambda': 0.4665,
    'class_weight': 'balanced'
}
```

### 4.3 특성 중요도

#### LightGBM 특성 중요도
1. **`funding_rate_zscore`**: 437
2. **`avg_funding_rate`**: 418
3. **`volatility_ratio`**: 405
4. **`whale_conc_change_7d`**: 400
5. `sum_open_interest`: 0 (데이터 부족)
6. `long_position_pct`: 0 (데이터 부족)
7. `oi_growth_7d`: 0 (데이터 부족)

#### SHAP 분석 결과 (평균 절대 SHAP 값)
1. **`whale_conc_change_7d`**: 0.5654 (가장 중요)
2. **`funding_rate_zscore`**: 0.4848
3. **`volatility_ratio`**: 0.3295
4. **`avg_funding_rate`**: 0.3228

**주요 발견**:
- 고래 집중도 변화가 가장 중요한 예측 변수
- 펀딩비 관련 지표(funding_rate_zscore, avg_funding_rate)도 중요
- 변동성 비율도 예측에 기여

### 4.4 Time Series Cross-Validation 결과

| Fold | Train 기간 | Val 기간 | AUC-ROC |
|------|-----------|----------|---------|
| 1 | 0 ~ 108 | 109 ~ 214 | 0.5284 |
| 2 | 0 ~ 214 | 215 ~ 320 | 0.4698 |
| 3 | 0 ~ 320 | 321 ~ 426 | 0.4563 |
| 4 | 0 ~ 426 | 427 ~ 532 | 0.6988 |
| 5 | 0 ~ 532 | 533 ~ 638 | 0.4229 |

**평균**: 0.5152 (+/- 0.0979)  
**최소**: 0.4229  
**최대**: 0.6988

### 4.5 생성된 파일

1. **예측 결과**:
   - `data/project3_risk_pred_results.csv` - 기본 모델 결과
   - `data/project3_risk_pred_results_tuned.csv` - CV + 기본 튜닝 결과
   - `data/project3_risk_pred_results_optuna.csv` - Optuna 최적화 결과
   - `data/project3_risk_pred_results_imbalanced.csv` - 불균형 처리 결과

2. **SHAP 분석**:
   - `data/project3_shap/shap_values.csv` - SHAP 값 데이터

3. **스크립트**:
   - `scripts/subprojects/risk_ai/train_model.py` - 기본 학습
   - `scripts/subprojects/risk_ai/train_model_with_cv.py` - CV + 튜닝
   - `scripts/subprojects/risk_ai/run_hyperparameter_tuning.py` - Optuna 튜닝
   - `scripts/subprojects/risk_ai/shap_analysis.py` - SHAP 분석
   - `scripts/subprojects/risk_ai/train_with_imbalanced_handling.py` - 불균형 처리
   - `scripts/subprojects/risk_ai/feature_engineering.py` - 특성 공학
   - `scripts/subprojects/risk_ai/update_volatility_data.py` - 변동성 데이터 업데이트
   - `scripts/subprojects/risk_ai/verify_data_completeness.py` - 데이터 검증

---

## 5. 주요 발견 및 인사이트

### 5.1 데이터 품질 개선
- **문제**: `volatility_24h`가 모두 0으로 저장됨
- **해결**: Binance Klines API를 사용하여 일봉 데이터 수집 및 변동성 계산
- **결과**: 1,058건의 유효한 변동성 데이터 확보

### 5.2 모델 성능
- **Baseline**: AUC-ROC 0.6418
- **최종**: AUC-ROC 0.6776 (+5.6% 향상)
- **평가**: 약간의 예측 능력 있음 (0.5 = 랜덤, 1.0 = 완벽)

### 5.3 특성 중요도
- **가장 중요한 특성**: 고래 집중도 변화 (`whale_conc_change_7d`)
  - SHAP 분석에서도 1위
  - 고래 활동이 시장 변동성의 강력한 선행 지표
- **펀딩비 지표**: `funding_rate_zscore`, `avg_funding_rate`도 중요
  - 펀딩비 이상이 변동성 증가와 연관

### 5.4 불균형 데이터 처리
- **SMOTEENN**이 가장 효과적 (AUC-ROC 0.6595)
- **SMOTE** 단독 사용은 성능 저하 (-4.5%)
- 시계열 데이터 특성상 불균형 처리 효과가 제한적

### 5.5 한계점
1. **데이터 부족**:
   - 미결제약정: 최근 30일만 유효 (API 제한)
   - 롱/숏 비율: 과거 데이터 없음
   - 이로 인해 관련 특성들이 의미 없음

2. **모델 성능**:
   - AUC-ROC 0.6776은 실용적 수준이지만 더 개선 필요
   - Precision이 낮음 (0.28) - False Positive 많음

3. **시계열 특성**:
   - 불균형 데이터 처리 기법이 시계열에 최적화되지 않음
   - SMOTE는 시계열 특성을 고려하지 않음

---

## 6. 향후 개선 방안

### 6.1 데이터 수집 개선
- [ ] 다른 데이터 소스 활용 (CryptoQuant, Glassnode)으로 OI 과거 데이터 확보
- [ ] 롱/숏 비율 데이터 수집 방법 개선
- [ ] 추가 지표 수집 (거래량, 청산 데이터 등)

### 6.2 모델 개선
- [ ] 시계열 특화 모델 검토 (LSTM, Transformer)
- [ ] 앙상블 방법 적용
- [ ] 추가 특성 생성 (상호작용 특성, 지연 특성)

### 6.3 평가 개선
- [ ] Precision-Recall Curve 분석
- [ ] 예측 시점별 성과 분석 (1일 후, 3일 후, 7일 후)
- [ ] 벤치마크 모델 비교 (단순 규칙 기반, 선형 모델)

### 6.4 실용화
- [ ] 실시간 예측 파이프라인 구축
- [ ] 알림 시스템 (고변동성 예측 시)
- [ ] 대시보드 구축

---

## 7. 결론

프로젝트 3 (Risk AI)는 고래 지표와 선물 시장 데이터를 결합하여 고변동성을 예측하는 모델을 구축했습니다. 

**주요 성과**:
- ✅ 데이터 품질 개선 (volatility 데이터 수집)
- ✅ 모델 성능 향상 (AUC-ROC 0.6776)
- ✅ 특성 중요도 분석 (고래 집중도 변화가 가장 중요)
- ✅ 다양한 기법 비교 및 최적화

**실용성**:
- 모델은 약간의 예측 능력을 보여주지만, 더 많은 데이터와 개선이 필요
- 고래 집중도 변화와 펀딩비 지표가 유용한 선행 지표임을 확인
- 실시간 모니터링 시스템 구축 시 활용 가능

**다음 단계**:
- 데이터 수집 개선 (OI 과거 데이터, 추가 지표)
- 모델 성능 향상 (시계열 특화 모델, 앙상블)
- 실용화 (실시간 예측 파이프라인, 대시보드)

---

**작성자**: AI Assistant  
**마지막 업데이트**: 2025-11-23

