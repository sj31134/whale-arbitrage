## 리스크 AI 백필 이후 재학습 플로우 설계

### 1. 전제: 백필 완료 상태

- `binance_futures_metrics`  
  - `avg_funding_rate`: 2022-01-01 ~ 현재까지 일별 값 채워짐  
  - `sum_open_interest`: 동일 기간 일별 값 채워짐
- `futures_extended_metrics`  
  - Binance 글로벌 롱/숏, Taker 비율, Top Trader 비율, Bybit 펀딩/OI 백필 완료
- `whale_daily_stats` / `whale_weekly_stats`  
  - `exchange_inflow_usd`, `net_flow_usd`, `active_addresses`, `large_tx_count` 등 일/주 단위 집계 완료

이 상태를 기준으로 아래 재학습 파이프라인을 설계합니다.

---

### 2. 피처 재생성 플로우

1. **데이터 로딩 스크립트 실행**
   - 위치: `scripts/subprojects/risk_ai/feature_engineering.py`
   - 입력:
     - `binance_futures_metrics` (BTCUSDT)
     - `bitinfocharts_whale`
     - `futures_extended_metrics`
     - `whale_daily_stats`
   - 동작:
     - 모든 조인/결측치 처리 후 정적 + 동적 특성 생성
     - 타겟(`target_high_vol`) 재계산

2. **동적 변수 검증**
   - `validate_risk_data.py`를 재실행하여:
     - `oi_delta`, `oi_accel`, `taker_ratio_delta`, `net_flow_delta` 등의 분포가 0이 아닌지 확인
     - OI/펀딩비 기반 지표의 P95, Max 값이 비정상(Inf, NaN)인지 여부 점검

3. **피처 스냅샷 저장 (선택)**
   - 재현성 확보를 위해 `data/models/risk_ai_features_YYYYMMDD.parquet` 형태로 저장

---

### 3. 모델 재학습 플로우

#### 3-1. 전통 ML (XGBoost/LightGBM 등)

1. **훈련/검증 분리**
   - 기준:
     - 시간 순 분할 (예: 2022-01-01 ~ 2024-12-31: train, 2025-01-01 ~ 현재: test)
   - 방법:
     - `date` 컬럼 기준으로 마스크 생성

2. **XGBoost/LightGBM 학습 스크립트**
   - 위치(예시): `scripts/subprojects/risk_ai/train_xgboost_model.py` (필요 시 추가)
   - 입력:
     - 재생성된 피처 + 타겟
   - 출력:
     - 모델 파일: `data/models/risk_ai_xgb.pkl`
     - 메타데이터: 사용한 피처 목록, 학습 기간, 하이퍼파라미터

3. **평가**
   - 메트릭:
     - AUC, F1, Precision@TopK, Recall@TopK 등
   - 비교:
     - 백필 전 모델과 동일 메트릭으로 비교하여 개선 여부 확인

#### 3-2. 시계열 모델 (LSTM 등)

1. **시퀀스 데이터 생성**
   - `train_lstm_model.py`에서:
     - 시퀀스 길이(예: 30일) 기준으로 슬라이딩 윈도우 생성
     - 입력: 동적/정적 피처 시퀀스
     - 출력: 다음날 `target_high_vol` 또는 리스크 스코어

2. **LSTM 재학습**
   - 기존 스크립트 재사용:
     - 단, 새로운 피처 세트(특히 OI/온체인 동적 변수)를 포함하도록 입력 차원만 업데이트

3. **평가**
   - ROC-AUC, PR-AUC, 시계열 관점에서의 Precision/Recall (예: 연속 고위험 구간 검출력) 평가

#### 3-3. 하이브리드 앙상블

1. **기본 모델 학습**
   - XGBoost + LSTM 각각 학습 후, 검증 세트 예측값 저장

2. **메타 모델 학습**
   - 입력:
     - XGBoost의 예측 확률
     - LSTM의 예측 확률
     - 핵심 피처 일부(예: funding_zscore, oi_accel, net_flow_delta)
   - 모델:
     - 간단한 Logistic Regression 또는 작은 MLP

3. **최종 평가**
   - 단일 모델 대비 앙상블의 향상 폭 측정

---

### 4. 리스크 스코어/분포 검증

1. **청산 리스크 계산 분포 비교**
   - `validate_risk_data.py`의 시뮬레이션 로직 활용
   - 백필 전/후에 대해:
     - 0~20%, 20~40%, 40~60%, 60~80%, 80~100%, 100% 구간별 비율 비교

2. **기간별 성능 분석**
   - 강세장/약세장 구간(예: 2022 하락, 2024 상승)별로 모델 성능을 분리 평가

3. **대시보드 검증**
   - Streamlit 리스크 대시보드에서:
     - 동적 지표(OI, net_flow, taker_ratio) 시각화가 실제 변동성과 일관성 있게 움직이는지 확인

---

### 5. 운영 플로우 정리

1. **1회성 작업 (백필 및 재학습)**
   - Binance/Bybit/whale_daily_stats 백필 스크립트 실행
   - 피처 재생성 → 모델 재학습 → 평가
   - 검증 완료 후 `data/models/`에 새 모델 버전으로 교체

2. **정기 작업 (운영)**
   - 매일/매시간:
     - 신규 일자에 대한 선물/온체인 데이터 수집
     - 피처 업데이트
     - 기존 학습된 모델로 예측만 수행 (재학습은 주기적으로)

3. **버전 관리**
   - 모델/피처/백필 스크립트에 버전 태그(예: `v2.0-backfilled-oi`) 부여
   - 필요 시 이전 버전으로 롤백 가능하도록 관리


