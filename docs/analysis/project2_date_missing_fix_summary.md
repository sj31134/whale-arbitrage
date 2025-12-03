# 날짜 누락 문제 해결 요약

> **작성일**: 2025-11-23

---

## 🔍 원인

1. **exchange_rate 테이블에 주말/공휴일 데이터 누락** (9일)
2. **load_exchange_data의 NULL 처리 부족**: `ffill().bfill()`만으로는 부족
3. **calculate_indicators의 dropna()**: 모든 NULL 값 제거로 인한 과도한 데이터 손실

---

## ✅ 해결 방법

### 1. load_exchange_data 개선
- 다단계 NULL 처리:
  1. Forward fill (앞의 값으로 채우기)
  2. Backward fill (뒤의 값으로 채우기)
  3. Linear interpolation (선형 보간)
  4. Mean fill (평균값으로 채우기)

### 2. calculate_indicators 개선
- 선택적 dropna: 핵심 가격 데이터만 확인
- exchange_rate는 이미 처리되었으므로 제외

---

## 📊 개선 효과

### Before
- 61건 → 2건 (59건 제거)
- 2024-11-19 제외됨

### After
- 61건 → 31건 (30건만 제거, rolling window)
- 2024-11-19 포함됨 ✅

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-11-23

