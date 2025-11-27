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



