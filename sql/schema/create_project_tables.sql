-- ============================================
-- Project 3 분석용 테이블 생성 (Supabase)
-- ============================================

-- 1. binance_futures_metrics
CREATE TABLE IF NOT EXISTS binance_futures_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    avg_funding_rate DECIMAL(20, 10),
    sum_open_interest DECIMAL(30, 10),
    long_short_ratio DECIMAL(10, 6),
    volatility_24h DECIMAL(10, 6),
    target_volatility_24h DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, symbol)
);

CREATE INDEX idx_futures_date ON binance_futures_metrics(date);
CREATE INDEX idx_futures_symbol ON binance_futures_metrics(symbol);

-- 2. binance_spot_daily
CREATE TABLE IF NOT EXISTS binance_spot_daily (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(20, 8),
    high DECIMAL(20, 8),
    low DECIMAL(20, 8),
    close DECIMAL(20, 8),
    volume DECIMAL(30, 8),
    quote_volume DECIMAL(30, 8),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, symbol)
);

CREATE INDEX idx_spot_daily_date ON binance_spot_daily(date);
CREATE INDEX idx_spot_daily_symbol ON binance_spot_daily(symbol);

-- 3. binance_spot_weekly
CREATE TABLE IF NOT EXISTS binance_spot_weekly (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(20, 8),
    high DECIMAL(20, 8),
    low DECIMAL(20, 8),
    close DECIMAL(20, 8),
    volume DECIMAL(30, 8),
    quote_volume DECIMAL(30, 8),
    atr DECIMAL(20, 8),
    rsi DECIMAL(10, 4),
    upper_shadow DECIMAL(20, 8),
    lower_shadow DECIMAL(20, 8),
    upper_shadow_ratio DECIMAL(10, 6),
    lower_shadow_ratio DECIMAL(10, 6),
    weekly_range DECIMAL(20, 8),
    weekly_range_pct DECIMAL(10, 6),
    body_size DECIMAL(20, 8),
    body_size_pct DECIMAL(10, 6),
    volatility_ratio DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, symbol)
);

CREATE INDEX idx_spot_weekly_date ON binance_spot_weekly(date);
CREATE INDEX idx_spot_weekly_symbol ON binance_spot_weekly(symbol);

-- 4. bitget_spot_daily
CREATE TABLE IF NOT EXISTS bitget_spot_daily (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(20, 8),
    high DECIMAL(20, 8),
    low DECIMAL(20, 8),
    close DECIMAL(20, 8),
    volume DECIMAL(30, 8),
    quote_volume DECIMAL(30, 8),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, symbol)
);

CREATE INDEX idx_bitget_date ON bitget_spot_daily(date);
CREATE INDEX idx_bitget_symbol ON bitget_spot_daily(symbol);

-- 5. bitinfocharts_whale
CREATE TABLE IF NOT EXISTS bitinfocharts_whale (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    coin VARCHAR(10) NOT NULL,
    top100_richest_pct DECIMAL(10, 4),
    avg_transaction_value_btc DECIMAL(20, 8),
    top10_pct DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, coin)
);

CREATE INDEX idx_whale_date ON bitinfocharts_whale(date);
CREATE INDEX idx_whale_coin ON bitinfocharts_whale(coin);

-- 6. exchange_rate
CREATE TABLE IF NOT EXISTS exchange_rate (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    krw_usd DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_exchange_date ON exchange_rate(date);

-- 7. upbit_daily
CREATE TABLE IF NOT EXISTS upbit_daily (
    id SERIAL PRIMARY KEY,
    market VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    opening_price DECIMAL(20, 8),
    high_price DECIMAL(20, 8),
    low_price DECIMAL(20, 8),
    trade_price DECIMAL(20, 8),
    acc_trade_volume_24h DECIMAL(30, 8),
    acc_trade_price_24h DECIMAL(30, 8),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, market)
);

CREATE INDEX idx_upbit_date ON upbit_daily(date);
CREATE INDEX idx_upbit_market ON upbit_daily(market);

-- 8. whale_weekly_stats
CREATE TABLE IF NOT EXISTS whale_weekly_stats (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    coin_symbol VARCHAR(20) NOT NULL,
    net_inflow_usd DECIMAL(30, 8),
    exchange_inflow_usd DECIMAL(30, 8),
    active_addresses INTEGER,
    transaction_count INTEGER,
    avg_buy_price DECIMAL(20, 8),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, coin_symbol)
);

CREATE INDEX idx_whale_weekly_date ON whale_weekly_stats(date);
CREATE INDEX idx_whale_weekly_coin ON whale_weekly_stats(coin_symbol);

-- 9. bybit_spot_daily (신규 추가)
CREATE TABLE IF NOT EXISTS bybit_spot_daily (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(20, 8),
    high DECIMAL(20, 8),
    low DECIMAL(20, 8),
    close DECIMAL(20, 8),
    volume DECIMAL(30, 8),
    quote_volume DECIMAL(30, 8),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, symbol)
);

CREATE INDEX idx_bybit_spot_date ON bybit_spot_daily(date);
CREATE INDEX idx_bybit_spot_symbol ON bybit_spot_daily(symbol);

-- 10. futures_extended_metrics (신규 추가: 롱숏비율, Taker비율, Bybit 데이터)
CREATE TABLE IF NOT EXISTS futures_extended_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    long_short_ratio DECIMAL(10, 6),
    long_account_pct DECIMAL(10, 6),
    short_account_pct DECIMAL(10, 6),
    taker_buy_sell_ratio DECIMAL(10, 6),
    taker_buy_vol DECIMAL(30, 8),
    taker_sell_vol DECIMAL(30, 8),
    top_trader_long_short_ratio DECIMAL(10, 6),
    bybit_funding_rate DECIMAL(20, 10),
    bybit_oi DECIMAL(30, 10),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, symbol)
);

CREATE INDEX idx_ext_metrics_date ON futures_extended_metrics(date);
CREATE INDEX idx_ext_metrics_symbol ON futures_extended_metrics(symbol);

-- 11. whale_daily_stats (신규 추가: 일별 고래 통계)
CREATE TABLE IF NOT EXISTS whale_daily_stats (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    coin_symbol VARCHAR(20) NOT NULL,
    exchange_inflow_usd DECIMAL(30, 8),
    exchange_outflow_usd DECIMAL(30, 8),
    net_flow_usd DECIMAL(30, 8),
    whale_to_whale_usd DECIMAL(30, 8),
    active_addresses INTEGER,
    large_tx_count INTEGER,
    avg_tx_size_usd DECIMAL(20, 8),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, coin_symbol)
);

CREATE INDEX idx_whale_daily_date ON whale_daily_stats(date);
CREATE INDEX idx_whale_daily_coin ON whale_daily_stats(coin_symbol);

-- 12. bitinfocharts_whale_weekly (신규 추가: 주별 고래 통계)
CREATE TABLE IF NOT EXISTS bitinfocharts_whale_weekly (
    coin VARCHAR(10) NOT NULL,
    week_end_date DATE NOT NULL,
    avg_top100_richest_pct DECIMAL(10, 4),
    avg_transaction_value_btc DECIMAL(20, 8),
    whale_conc_change_7d DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (coin, week_end_date)
);

-- 13. binance_futures_weekly (신규 추가: 주별 선물 지표)
CREATE TABLE IF NOT EXISTS binance_futures_weekly (
    symbol VARCHAR(20) NOT NULL,
    week_end_date DATE NOT NULL,
    avg_funding_rate DECIMAL(20, 10),
    sum_open_interest DECIMAL(30, 10),
    oi_growth_7d DECIMAL(10, 6),
    funding_rate_zscore DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (symbol, week_end_date)
);

CREATE INDEX IF NOT EXISTS idx_futures_weekly_symbol ON binance_futures_weekly(symbol);
CREATE INDEX IF NOT EXISTS idx_futures_weekly_date ON binance_futures_weekly(week_end_date);

-- 인덱스 생성 (이미 존재하면 오류 발생하므로 필요시만 실행)
-- CREATE INDEX IF NOT EXISTS idx_whale_weekly_coin ON bitinfocharts_whale_weekly(coin);
-- CREATE INDEX IF NOT EXISTS idx_whale_weekly_date ON bitinfocharts_whale_weekly(week_end_date);

-- 인덱스가 이미 존재하는 경우, 다음 SQL로 개별 생성 가능:
-- DO $$ BEGIN
--     IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_whale_weekly_coin') THEN
--         CREATE INDEX idx_whale_weekly_coin ON bitinfocharts_whale_weekly(coin);
--     END IF;
--     IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_whale_weekly_date') THEN
--         CREATE INDEX idx_whale_weekly_date ON bitinfocharts_whale_weekly(week_end_date);
--     END IF;
-- END $$;



