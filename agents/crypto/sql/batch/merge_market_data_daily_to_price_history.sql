-- ============================================
-- market_data_daily 테이블을 price_history 테이블로 통합
-- ============================================
-- 목적: 두 테이블을 하나의 price_history 테이블로 통합
-- market_data_daily의 필요한 컬럼들을 price_history에 추가

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
-- (중복되지 않는 데이터만)
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

-- 5. 완료 메시지
DO $$
BEGIN
    RAISE NOTICE '✅ market_data_daily 테이블을 price_history로 통합 완료';
    RAISE NOTICE '   - 추가된 컬럼: date, price_change_24h, price_change_percent_24h, weighted_avg_price, prev_close_price, last_price, bid_price, ask_price, first_trade_id, last_trade_id, open_time, close_time';
    RAISE NOTICE '   - market_data_daily 데이터가 price_history로 마이그레이션되었습니다.';
END $$;

-- 참고: market_data_daily 테이블은 이후에 삭제할 수 있지만,
-- 먼저 데이터가 제대로 통합되었는지 확인한 후 삭제하는 것을 권장합니다.



