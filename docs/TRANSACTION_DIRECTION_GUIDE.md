# 🏷️ Transaction Direction 라벨링 가이드

거래 유형(BUY/SELL/MOVE)을 자동으로 라벨링하는 방법입니다.

## 📋 개요

`whale_transactions` 테이블의 거래를 분석하여:
- **BUY**: 거래소 → 일반 지갑 (매수)
- **SELL**: 일반 지갑 → 거래소 (매도)  
- **MOVE**: 그 외 (지갑 간 이동, 컨트랙트 실행 등)

## 🚀 실행 방법 (2단계)

### Step 1: 컬럼 추가 (Supabase SQL Editor)

**매우 빠름 (1-2초)** - Timeout 안 걸림

1. Supabase 대시보드 접속
2. SQL Editor 열기
3. 아래 파일 내용 복사 & 실행:

```sql
-- sql/add_transaction_direction_column_only.sql 내용 복사
ALTER TABLE whale_transactions 
ADD COLUMN IF NOT EXISTS transaction_direction VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_whale_tx_direction 
ON whale_transactions(transaction_direction);

COMMENT ON COLUMN whale_transactions.transaction_direction 
IS '거래 유형: BUY(매수), SELL(매도), MOVE(이동/전송)';
```

### Step 2: Python 스크립트 실행

**예상 시간: 10-30분** (데이터 양에 따라)

```bash
cd /Users/junyonglee/Documents/GitHub/whale_tracking
python3 scripts/label_transaction_direction_fast_batch.py
```

## 🎯 작동 원리

### 1. 코인별 분할 처리
- 전체 데이터를 코인별로 나눔
- 각 코인을 독립적으로 처리
- Timeout 위험 최소화

### 2. 병렬 처리
- 5개 스레드로 동시 처리
- 처리 속도 5배 향상

### 3. 작은 배치 업데이트
- 100개씩 bulk update
- 각 배치는 1-2초 내 완료
- Timeout 없음

### 4. 자동 라벨 정리
- NULL 라벨 → 'Unknown Wallet' 자동 변환
- 거래 유형 분류 동시 진행

## 📊 거래소 판별 기준

다음 키워드를 포함한 라벨을 거래소로 인식:

```
binance, coinbase, kraken, huobi, okx, 
bitfinex, gate.io, bybit, kucoin, upbit, 
bithumb, bittrex, gemini, crypto.com, exchange
```

## 🔍 결과 확인

```bash
python3 scripts/verify_transaction_direction.py
```

또는 Supabase SQL Editor에서:

```sql
-- 거래 유형별 통계
SELECT 
    transaction_direction,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM whale_transactions
WHERE transaction_direction IS NOT NULL
GROUP BY transaction_direction
ORDER BY count DESC;

-- 샘플 데이터
SELECT 
    transaction_direction,
    from_label,
    to_label,
    coin_symbol,
    amount,
    amount_usd
FROM whale_transactions
WHERE transaction_direction = 'BUY'
LIMIT 10;
```

## ⚠️ 주의사항

### Timeout 회피 전략
1. ✅ 코인별로 분할 처리
2. ✅ 작은 배치 크기 (100개)
3. ✅ Rate limit 고려 (0.1초 대기)
4. ✅ 병렬 처리로 속도 향상

### 중단 시 재실행
- 이미 처리된 데이터는 건너뜀 (`WHERE transaction_direction IS NULL`)
- 언제든 중단하고 재시작 가능
- 데이터 손실 없음

## 📈 예상 처리량

| 거래 건수 | 예상 시간 | 방법 |
|----------|----------|------|
| 10만 건 | 5-10분 | 코인별 병렬 처리 |
| 50만 건 | 15-20분 | 코인별 병렬 처리 |
| 100만 건 | 25-30분 | 코인별 병렬 처리 |

## 🐛 문제 해결

### 오류: "column already exists"
→ 정상입니다. 컬럼이 이미 있다는 의미. Step 2로 진행하세요.

### 오류: "timeout"
→ Step 2 Python 스크립트는 timeout 걱정 없습니다.
→ 코인별로 작은 단위로 처리하기 때문입니다.

### 처리 속도가 느림
→ 정상입니다. 안전하게 천천히 처리합니다.
→ 중단하지 말고 기다려주세요.

## 🎉 완료 후 활용

거래 유형별 분석 쿼리 예시:

```sql
-- 코인별 매수/매도 비율
SELECT 
    coin_symbol,
    COUNT(CASE WHEN transaction_direction = 'BUY' THEN 1 END) as buy_count,
    COUNT(CASE WHEN transaction_direction = 'SELL' THEN 1 END) as sell_count,
    ROUND(
        COUNT(CASE WHEN transaction_direction = 'BUY' THEN 1 END)::NUMERIC / 
        NULLIF(COUNT(CASE WHEN transaction_direction = 'SELL' THEN 1 END), 0), 
        2
    ) as buy_sell_ratio
FROM whale_transactions
WHERE transaction_direction IN ('BUY', 'SELL')
GROUP BY coin_symbol
ORDER BY buy_count DESC;

-- 시간대별 매수/매도 패턴
SELECT 
    DATE_TRUNC('day', block_timestamp) as date,
    transaction_direction,
    COUNT(*) as count,
    SUM(amount_usd) as total_usd
FROM whale_transactions
WHERE transaction_direction IN ('BUY', 'SELL')
GROUP BY date, transaction_direction
ORDER BY date DESC;
```

