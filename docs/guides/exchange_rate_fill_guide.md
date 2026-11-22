# 환율 데이터 보완 가이드

> **작성일**: 2025-11-23  
> **목적**: 주말/공휴일 등 누락된 환율 데이터 보완

---

## 📋 개요

한국은행 ECOS API는 주말/공휴일 데이터를 제공하지 않습니다. 따라서 거래 데이터와의 매칭을 위해 누락된 환율 데이터를 보완해야 합니다.

---

## 🔧 보완 방법

### 1. 자동 보완 스크립트 실행

```bash
python3 scripts/subprojects/arbitrage/fill_missing_exchange_rate.py
```

이 스크립트는:
- 현재 `exchange_rate` 테이블의 데이터 범위 확인
- 누락된 날짜 자동 탐지
- 근처 날짜의 환율 데이터로 자동 보완
  - 앞뒤 날짜가 모두 있으면: 평균값 사용
  - 한쪽만 있으면: 해당 값 사용

### 2. 보완 로직

1. **앞의 날짜 조회**: 누락된 날짜 이전의 가장 가까운 날짜
2. **뒤의 날짜 조회**: 누락된 날짜 이후의 가장 가까운 날짜
3. **값 결정**:
   - 앞뒤 모두 있으면: 평균값
   - 한쪽만 있으면: 해당 값
4. **INSERT**: `INSERT OR IGNORE`로 중복 방지

### 3. 런타임 보완

`app/utils/data_loader.py`의 `load_exchange_data` 함수에서도 추가 보완:
- Forward fill (앞의 값으로 채우기)
- Backward fill (뒤의 값으로 채우기)
- Linear interpolation (선형 보간)
- Mean fill (평균값으로 채우기)

---

## 📊 사용 예시

### 보완 전
```
2024-11-15: 1392.5
2024-11-16: NULL (주말)
2024-11-17: NULL (주말)
2024-11-18: 1392.6
```

### 보완 후
```
2024-11-15: 1392.5
2024-11-16: 1392.55 (평균값)
2024-11-17: 1392.55 (평균값)
2024-11-18: 1392.6
```

---

## ✅ 검증

보완 후 상태 확인:
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('data/project.db')
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
    SUM(CASE WHEN e.date IS NOT NULL THEN 1 ELSE 0 END) as has_data
FROM dates d
LEFT JOIN exchange_rate e ON d.date = e.date
"""
df = pd.read_sql(query, conn)
print(f"커버리지: {(df['has_data'].iloc[0] / df['total_days'].iloc[0] * 100):.1f}%")
```

---

## 🔄 정기 실행

새로운 데이터 수집 후 보완 스크립트 실행 권장:
```bash
# 1. 환율 데이터 수집
python3 scripts/subprojects/arbitrage/fetch_exchange_rate.py

# 2. 누락된 데이터 보완
python3 scripts/subprojects/arbitrage/fill_missing_exchange_rate.py
```

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-11-23

