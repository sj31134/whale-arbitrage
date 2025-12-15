-- Supabase에 whale_address 및 whale_transactions 테이블 생성
-- Supabase SQL Editor에서 실행하세요.

-- 1. whale_address 테이블
CREATE TABLE IF NOT EXISTS whale_address (
    id VARCHAR(50) PRIMARY KEY,
    chain_type VARCHAR(20),
    address VARCHAR(100),
    name_tag VARCHAR(100),
    balance VARCHAR(50),
    percentage VARCHAR(20),
    txn_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_whale_address_chain ON whale_address(chain_type);
CREATE INDEX IF NOT EXISTS idx_whale_address_addr ON whale_address(address);

-- 2. whale_transactions 테이블
CREATE TABLE IF NOT EXISTS whale_transactions (
    tx_hash VARCHAR(100),
    chain VARCHAR(20),
    block_number BIGINT,
    block_timestamp TIMESTAMP WITH TIME ZONE,
    from_address VARCHAR(100),
    to_address VARCHAR(100),
    value NUMERIC(30, 18),
    coin_symbol VARCHAR(20),
    gas_used BIGINT,
    gas_price BIGINT,
    is_error BOOLEAN,
    from_label VARCHAR(255),
    to_label VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (tx_hash, chain)
);

CREATE INDEX IF NOT EXISTS idx_whale_tx_timestamp ON whale_transactions(block_timestamp);
CREATE INDEX IF NOT EXISTS idx_whale_tx_from ON whale_transactions(from_address);
CREATE INDEX IF NOT EXISTS idx_whale_tx_to ON whale_transactions(to_address);
CREATE INDEX IF NOT EXISTS idx_whale_tx_chain_symbol ON whale_transactions(chain, coin_symbol);

-- RLS 설정 (필요한 경우)
ALTER TABLE whale_address ENABLE ROW LEVEL SECURITY;
ALTER TABLE whale_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read access" ON whale_address FOR SELECT USING (true);
CREATE POLICY "Public read access" ON whale_transactions FOR SELECT USING (true);

