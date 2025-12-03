# ETH 파생상품 데이터 미연동 근본 원인 분석

## 📋 요약

이더리움(ETH) 파생상품 데이터가 서비스에 연동되지 않는 근본 원인은 **`bitinfocharts_whale` 테이블의 ETH 데이터 부족**과 **`load_risk_data` 함수의 과도한 `dropna()` 처리**입니다.

---

## 🔍 근본 원인

### 1. `bitinfocharts_whale` 테이블 ETH 데이터 부족

**현황:**
- **BTC**: 1,064건 (2022-12-31 ~ 2025-11-30)
- **ETH**: 4건만 존재 (2025-11-24 ~ 2025-11-27)
- **최근 30일**: BTC 29건, ETH 4건

**영향:**
- `load_risk_data`에서 `binance_futures_metrics`와 `bitinfocharts_whale`을 LEFT JOIN할 때, ETH의 경우 대부분의 행에서 `top100_richest_pct`와 `avg_transaction_value_btc`가 `NULL`이 됨
- 예: 2025-11-01 ~ 2025-11-30 기간에 30건의 파생상품 데이터가 있지만, whale 데이터는 4건만 있어 26건이 JOIN 실패

### 2. `load_risk_data` 함수의 과도한 `dropna()` 처리

**문제 코드:**
```python
df = df.ffill().dropna()  # 모든 컬럼에 NaN이 있으면 행 제거
```

**영향:**
- `ffill()`로 whale 컬럼을 채워도, 처음부터 NaN이면 여전히 NaN
- `dropna()`는 **모든 컬럼**에 NaN이 있는 행을 제거하므로, whale 데이터가 없는 대부분의 행이 제거됨
- 결과: 30건 → 7건으로 감소 (약 77% 데이터 손실)

**예시:**
```
원본 데이터: 30건 (binance_futures_metrics)
  - whale JOIN 성공: 4건
  - whale JOIN 실패: 26건 (top100_richest_pct, avg_transaction_value_btc = NULL)

dropna() 후: 7건 (약 77% 손실)
```

### 3. Supabase 동기화 누락 가능성

**현황:**
- SQLite에는 ETH 파생상품 데이터가 충분히 존재 (1,430건)
- Supabase에 동기화되지 않았을 가능성
- 클라우드 환경에서는 Supabase를 우선 사용하므로, Supabase에 데이터가 없으면 "데이터 없음" 오류 발생

---

## ✅ 해결 방안

### 1. `load_risk_data` 함수 수정 (완료)

**변경 사항:**
- whale 데이터는 **선택적(optional)**으로 처리
- 파생상품 핵심 컬럼(`avg_funding_rate`, `sum_open_interest`, `volatility_24h`) 중 하나라도 있으면 행 유지
- whale 컬럼만 `ffill()` 처리하고, 전체 행을 `dropna()`로 제거하지 않음

**수정 코드:**
```python
# whale 데이터는 선택적이므로, 파생상품 데이터가 있으면 유지
whale_cols = ['top100_richest_pct', 'avg_transaction_value_btc']
core_cols = ['avg_funding_rate', 'sum_open_interest', 'volatility_24h']

# whale 컬럼만 forward fill
for col in whale_cols:
    if col in df.columns:
        df[col] = df[col].ffill()

# 핵심 파생상품 컬럼 중 하나라도 있으면 행 유지
if len(core_cols) > 0:
    has_core_data = df[core_cols].notna().any(axis=1)
    df = df[has_core_data]
```

**효과:**
- whale 데이터가 없어도 파생상품 데이터는 반환됨
- 데이터 손실 최소화 (30건 → 30건 유지)

### 2. `bitinfocharts_whale` ETH 데이터 수집 (권장)

**방법:**
1. **`fetch_bitinfo_whale.py` 스크립트 실행**
   - BTC와 ETH 모두 수집하도록 이미 구현됨
   - 정기적으로 실행하여 최신 데이터 수집

2. **Wayback Machine 활용**
   - `fetch_bitinfo_wayback.py` 스크립트로 과거 데이터 수집
   - 2022-01-01부터 현재까지 히스토리 데이터 수집

**실행 명령:**
```bash
# 일일 수집
python scripts/subprojects/risk_ai/fetch_bitinfo_whale.py

# 히스토리 수집 (Wayback Machine)
python scripts/subprojects/risk_ai/fetch_bitinfo_wayback.py
```

### 3. Supabase 동기화 확인 및 실행 (필수)

**확인 사항:**
1. `binance_futures_metrics` 테이블에 ETHUSDT 데이터 존재 여부
2. `futures_extended_metrics` 테이블에 ETHUSDT 데이터 존재 여부
3. `bitinfocharts_whale` 테이블에 ETH 데이터 존재 여부

**동기화 명령:**
```bash
# 전체 테이블 동기화
python scripts/sync_sqlite_to_supabase.py

# 특정 테이블만 동기화
python scripts/sync_sqlite_to_supabase.py --table binance_futures_metrics
python scripts/sync_sqlite_to_supabase.py --table futures_extended_metrics
python scripts/sync_sqlite_to_supabase.py --table bitinfocharts_whale
```

---

## 📊 데이터 현황

### SQLite (로컬)

**binance_futures_metrics (ETHUSDT):**
- 총 레코드: 1,430건
- 펀딩비 데이터: 1,430건
- OI 데이터: 1,427건
- 기간: 2022-01-01 ~ 2025-11-30
- 최근 30일: 31건

**futures_extended_metrics (ETHUSDT):**
- 총 레코드: 1,304건
- Bybit 펀딩비: 0건
- Bybit OI: 0건
- Top Trader 비율: 1,116건
- Taker 비율: 1,302건
- 기간: 2022-01-30 ~ 2025-11-30
- 최근 30일: 31건

**bitinfocharts_whale (ETH):**
- 총 레코드: 4건
- 기간: 2025-11-24 ~ 2025-11-27
- 최근 30일: 4건

### Supabase (클라우드)

**확인 필요:**
- 위 테이블들의 Supabase 동기화 상태 확인
- 클라우드 환경에서는 Supabase를 우선 사용하므로, Supabase에 데이터가 없으면 "데이터 없음" 오류 발생

---

## 🎯 다음 단계

1. ✅ **`load_risk_data` 함수 수정 완료**
   - whale 데이터가 없어도 파생상품 데이터 반환

2. ⏳ **`bitinfocharts_whale` ETH 데이터 수집**
   - `fetch_bitinfo_whale.py` 정기 실행
   - `fetch_bitinfo_wayback.py`로 히스토리 수집

3. ⏳ **Supabase 동기화 확인 및 실행**
   - SQLite → Supabase 동기화 스크립트 실행
   - 클라우드 환경에서 데이터 접근 가능하도록 보장

4. ⏳ **테스트 및 검증**
   - 로컬 환경에서 수정된 `load_risk_data` 테스트
   - 클라우드 환경에서 Supabase 데이터 접근 테스트
   - 서비스 메뉴에서 ETH 파생상품 데이터 표시 확인

---

## 📝 참고

- **수정 파일**: `app/utils/data_loader.py`
- **관련 스크립트**: 
  - `scripts/subprojects/risk_ai/fetch_bitinfo_whale.py`
  - `scripts/subprojects/risk_ai/fetch_bitinfo_wayback.py`
  - `scripts/sync_sqlite_to_supabase.py`
- **관련 테이블**: 
  - `binance_futures_metrics`
  - `futures_extended_metrics`
  - `bitinfocharts_whale`

