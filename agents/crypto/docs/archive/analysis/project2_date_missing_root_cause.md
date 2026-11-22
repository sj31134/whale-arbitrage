# 날짜 누락 원인 분석

> **작성일**: 2025-11-23  
> **문제**: 2024-11-19 데이터가 calculate_indicators 후 제외됨

---

## 🔍 원인 분석 결과

### 1. 데이터베이스 상태
✅ **모든 테이블에 데이터 존재**
- `upbit_daily`: ✅ 있음
- `binance_spot_daily`: ✅ 있음
- `bitget_spot_daily`: ✅ 있음
- `exchange_rate`: ✅ 있음

### 2. 데이터 로드 상태
✅ **load_exchange_data에서 정상 로드**
- 2024-10-20 ~ 2024-12-19 기간: 61건 로드
- 2024-11-19 포함: ✅ 있음

### 3. 문제 발생 지점
❌ **calculate_indicators 후 데이터 제외**

**원인**:
1. `exchange_rate` 테이블에 **주말/공휴일 데이터 누락** (9일)
   - 2024-10-20, 10-26, 10-27, 11-02, 11-03, 11-09, 11-10, 11-16, 11-17
   
2. `load_exchange_data`에서 `krw_usd` 처리:
   ```python
   df['krw_usd'] = df['krw_usd'].ffill().bfill()
   ```
   - `ffill()`: 앞의 값으로 채움
   - `bfill()`: 뒤의 값으로 채움
   - **하지만 처음이나 끝에 NULL이 있으면 제대로 채워지지 않음**

3. `calculate_indicators`에서 `dropna()`:
   ```python
   df = df.dropna()
   ```
   - **NULL 값이 있는 행이 모두 제거됨**
   - 61건 → 2건으로 감소

4. Rolling window 적용:
   ```python
   df = df.iloc[self.rolling_window:].reset_index(drop=True)
   ```
   - 처음 30일 제거
   - 결과적으로 2024-11-19가 제외됨

---

## 📊 상세 분석

### exchange_rate 누락 패턴
- **주말 누락**: 토요일, 일요일
- **공휴일 누락**: 한국 공휴일
- **영향**: 약 9일 (2024-10-20 ~ 2024-11-19 기간)

### 데이터 흐름
```
1. DB 조회 (61건)
   ↓
2. load_exchange_data (61건)
   - exchange_rate LEFT JOIN
   - krw_usd ffill().bfill()
   ↓
3. calculate_indicators
   - dropna() → NULL 값 제거
   - 61건 → 2건 (59건 제거)
   ↓
4. rolling_window 적용
   - 처음 30일 제거
   - 2건 → 2건 (이미 충분히 적음)
   ↓
5. 결과: 2024-11-19 제외됨
```

---

## 🔧 해결 방안

### 방안 1: exchange_rate NULL 처리 개선 (권장)
```python
# load_exchange_data에서
df['krw_usd'] = df['krw_usd'].fillna(method='ffill').fillna(method='bfill')
# 또는
df['krw_usd'] = df['krw_usd'].interpolate(method='linear')
```

### 방안 2: calculate_indicators에서 선택적 dropna
```python
# 특정 컬럼만 dropna
df = df.dropna(subset=['upbit_price', 'binance_price', 'bitget_price'])
# krw_usd는 별도 처리
df['krw_usd'] = df['krw_usd'].fillna(method='ffill').fillna(method='bfill')
```

### 방안 3: exchange_rate 데이터 보완
- 주말/공휴일 데이터도 수집
- 또는 전날 값으로 자동 채우기

---

## ✅ 권장 해결책

**방안 1 + 방안 2 조합**:
1. `load_exchange_data`에서 `krw_usd` NULL 처리 강화
2. `calculate_indicators`에서 선택적 dropna 적용
3. 사용자에게 주말/공휴일 데이터 제한 안내

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-11-23

