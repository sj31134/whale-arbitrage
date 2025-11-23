# 📝 SQL 실행 가이드

## 🎯 목표
`market_data_daily` 테이블을 `price_history` 테이블로 통합

---

## 📋 실행 방법

### 1단계: Supabase 대시보드 접속
1. https://supabase.com/dashboard 접속
2. 프로젝트 선택
3. 좌측 메뉴에서 **"SQL Editor"** 클릭

### 2단계: SQL 파일 열기
1. **"New query"** 버튼 클릭
2. 다음 파일의 내용을 복사:
   ```
   sql/merge_market_data_daily_to_price_history.sql
   ```

### 3단계: SQL 실행
1. SQL Editor에 붙여넣기
2. **"Run"** 버튼 클릭 (또는 `Ctrl+Enter` / `Cmd+Enter`)
3. 실행 결과 확인

---

## 📄 SQL 파일 내용

```sql
-- ============================================
-- market_data_daily 테이블을 price_history 테이블로 통합
-- ============================================

-- 1. price_history 테이블에 market_data_daily의 컬럼 추가
ALTER TABLE public.price_history
ADD COLUMN IF NOT EXISTS date DATE,
ADD COLUMN IF NOT EXISTS price_change_24h NUMERIC(20, 8),
ADD COLUMN IF NOT EXISTS price_change_percent_24h NUMERIC(10, 4),
ADD COLUMN IF NOT EXISTS weighted_avg_price NUMERIC(20, 8),
ADD COLUMN IF NOT EXISTS prev_close_price NUMERIC(20, 8),
ADD COLUMN IF NOT EXISTS last_price NUMERIC(20, 8),
ADD COLUMN IF NOT EXISTS bid_price NUMERIC(20, 8),
ADD COLUMN IF NOT EXISTS ask_price NUMERIC(20, 8),
ADD COLUMN IF NOT EXISTS first_trade_id BIGINT,
ADD COLUMN IF NOT EXISTS last_trade_id BIGINT,
ADD COLUMN IF NOT EXISTS open_time TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS close_time TIMESTAMPTZ;

-- 2. date 컬럼이 없으면 timestamp에서 추출하여 채우기
UPDATE public.price_history
SET date = DATE(timestamp)
WHERE date IS NULL;

-- 3. market_data_daily의 데이터를 price_history로 마이그레이션
INSERT INTO public.price_history (
    id,
    crypto_id,
    timestamp,
    date,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    quote_volume,
    trade_count,
    price_change_24h,
    price_change_percent_24h,
    weighted_avg_price,
    prev_close_price,
    last_price,
    bid_price,
    ask_price,
    first_trade_id,
    last_trade_id,
    open_time,
    close_time,
    data_source,
    raw_data,
    created_at
)
SELECT 
    mdd.id,
    mdd.crypto_id,
    COALESCE(mdd.open_time, mdd.date::TIMESTAMPTZ) as timestamp,
    mdd.date,
    mdd.open_price,
    mdd.high_price,
    mdd.low_price,
    mdd.close_price,
    mdd.volume,
    mdd.quote_volume,
    mdd.trade_count,
    mdd.price_change_24h,
    mdd.price_change_percent_24h,
    mdd.weighted_avg_price,
    mdd.prev_close_price,
    mdd.last_price,
    mdd.bid_price,
    mdd.ask_price,
    mdd.first_trade_id,
    mdd.last_trade_id,
    mdd.open_time,
    mdd.close_time,
    COALESCE(mdd.data_source, 'binance') as data_source,
    mdd.raw_data,
    COALESCE(mdd.created_at, NOW()) as created_at
FROM public.market_data_daily mdd
LEFT JOIN public.price_history ph 
    ON ph.crypto_id = mdd.crypto_id 
    AND ph.timestamp = COALESCE(mdd.open_time, mdd.date::TIMESTAMPTZ)
WHERE ph.id IS NULL;  -- 중복되지 않는 데이터만

-- 4. 인덱스 추가 (성능 향상)
CREATE INDEX IF NOT EXISTS idx_price_history_date ON public.price_history(date);
CREATE INDEX IF NOT EXISTS idx_price_history_crypto_date ON public.price_history(crypto_id, date);
CREATE INDEX IF NOT EXISTS idx_price_history_first_trade_id ON public.price_history(first_trade_id);
CREATE INDEX IF NOT EXISTS idx_price_history_last_trade_id ON public.price_history(last_trade_id);
```

---

## ✅ 실행 후 확인

### 1. 컬럼 추가 확인
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'price_history' 
AND column_name IN ('date', 'price_change_24h', 'first_trade_id', 'last_trade_id')
ORDER BY column_name;
```

### 2. 데이터 마이그레이션 확인
```sql
-- market_data_daily의 데이터 수
SELECT COUNT(*) FROM market_data_daily;

-- price_history의 데이터 수 (통합 후)
SELECT COUNT(*) FROM price_history;

-- date 컬럼이 채워졌는지 확인
SELECT COUNT(*) FROM price_history WHERE date IS NOT NULL;
```

---

## ⚠️ 주의사항

1. **백업**: SQL 실행 전에 데이터베이스 백업 권장
2. **중복 체크**: `market_data_daily`의 데이터가 이미 `price_history`에 있는 경우 중복되지 않도록 처리됨
3. **실행 시간**: 데이터 양에 따라 몇 분 소요될 수 있음

---

## 🐛 문제 해결

### 오류: "column already exists"
- 이미 컬럼이 추가되어 있다는 의미
- 무시하고 다음 단계로 진행

### 오류: "duplicate key"
- 중복 데이터가 있다는 의미
- SQL의 `WHERE ph.id IS NULL` 조건으로 중복 방지됨

### 실행이 느린 경우
- 인덱스가 생성되면 조회 성능이 향상됨
- 대량 데이터의 경우 시간이 걸릴 수 있음



