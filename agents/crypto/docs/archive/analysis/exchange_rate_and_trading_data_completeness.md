# 거래 데이터 및 환율 데이터 완전성 가이드

> **작성일**: 2025-11-23  
> **목적**: 1년 365일 거래 데이터 수집 및 환율 데이터 보완

---

## 📋 요구사항

1. **거래 데이터**: 1년 365일 기간 내 전부 수집 (누락 없이)
2. **환율 데이터**: 주말/공휴일 누락 시 근처 날짜의 환율 데이터로 보완

---

## 🔍 현재 상태

### 거래 데이터
- ✅ `upbit_daily`: 일일 데이터 수집
- ✅ `binance_spot_daily`: 일일 데이터 수집
- ✅ `bitget_spot_daily`: 일일 데이터 수집

### 환율 데이터
- ⚠️ `exchange_rate`: 주말/공휴일 데이터 누락
- ✅ 보완 스크립트: `fill_missing_exchange_rate.py`

---

## 🔧 해결 방법

### 1. 환율 데이터 보완

#### 자동 보완 스크립트
```bash
python3 scripts/subprojects/arbitrage/fill_missing_exchange_rate.py
```

**기능**:
- 누락된 날짜 자동 탐지
- 근처 날짜의 환율 데이터로 자동 보완
  - 앞뒤 날짜가 모두 있으면: 평균값
  - 한쪽만 있으면: 해당 값

#### 수집 시 자동 보완
`fetch_exchange_rate.py` 실행 후 자동으로 보완 스크립트 실행

### 2. 런타임 보완

`app/utils/data_loader.py`의 `load_exchange_data` 함수에서:
1. Forward fill (앞의 값으로 채우기)
2. Backward fill (뒤의 값으로 채우기)
3. Linear interpolation (선형 보간)
4. Mean fill (평균값으로 채우기)

---

## 📊 데이터 완전성 확인

### 스크립트로 확인
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('data/project.db')

# 환율 데이터 커버리지 확인
query = """
WITH RECURSIVE dates(date) AS (
    SELECT '2024-01-01' as date
    UNION ALL
    SELECT date(date, '+1 day')
    FROM dates
    WHERE date < '2024-12-31'
)
SELECT 
    COUNT(*) as total_days,
    SUM(CASE WHEN e.date IS NOT NULL THEN 1 ELSE 0 END) as has_data,
    SUM(CASE WHEN e.date IS NULL THEN 1 ELSE 0 END) as missing
FROM dates d
LEFT JOIN exchange_rate e ON d.date = e.date
"""
df = pd.read_sql(query, conn)
print(f"커버리지: {(df['has_data'].iloc[0] / df['total_days'].iloc[0] * 100):.1f}%")
```

---

## 🔄 정기 실행 순서

1. **거래 데이터 수집** (이미 완료)
   ```bash
   python3 scripts/subprojects/arbitrage/fetch_spot_quotes.py
   ```

2. **환율 데이터 수집**
   ```bash
   python3 scripts/subprojects/arbitrage/fetch_exchange_rate.py
   ```
   (자동으로 보완 스크립트 실행됨)

3. **수동 보완 (필요시)**
   ```bash
   python3 scripts/subprojects/arbitrage/fill_missing_exchange_rate.py
   ```

---

## ✅ 검증

### 환율 데이터 완전성
- 목표: 100% 커버리지 (365일)
- 현재: 보완 스크립트 실행 후 확인

### 거래 데이터 완전성
- 목표: 1년 365일 전부 수집
- 확인: 각 테이블별 건수 확인

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-11-23

