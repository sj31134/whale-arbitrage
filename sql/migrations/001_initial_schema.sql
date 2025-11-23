-- ============================================
-- Whale Tracking Database Schema
-- 통합 초기 스키마 마이그레이션
-- ============================================
-- 실행 방법: scripts/setup_database.py 실행
-- 또는 Supabase SQL Editor에서 직접 실행

-- ============================================
-- 1. whale_transactions 테이블 생성
-- ============================================
CREATE TABLE IF NOT EXISTS whale_transactions (
    -- 기본 식별자
    tx_hash TEXT PRIMARY KEY,
    
    -- 블록 정보
    block_number BIGINT NOT NULL,
    block_timestamp TIMESTAMPTZ NOT NULL,
    
    -- 주소 정보
    from_address TEXT NOT NULL,
    to_address TEXT,
    
    -- 코인/토큰 정보
    coin_symbol TEXT NOT NULL,
    chain VARCHAR(50) NOT NULL DEFAULT 'ethereum',
    contract_address TEXT,  -- 토큰 컨트랙트 주소 (ERC-20인 경우)
    token_name TEXT,  -- 토큰 이름 (ERC-20 거래만)
    
    -- 금액 정보
    amount NUMERIC(78, 18) NOT NULL,  -- 거래 금액 (ETH/MATIC/토큰 수량)
    amount_usd NUMERIC(20, 2),  -- USD 가치 (NULL 허용: 가격 조회 실패 시)
    
    -- 가스 정보
    gas_used BIGINT,
    gas_price BIGINT,
    gas_fee_eth NUMERIC(78, 18),
    gas_fee_usd NUMERIC(20, 2),
    
    -- 거래 상태
    transaction_status TEXT NOT NULL DEFAULT 'SUCCESS',
    is_whale BOOLEAN NOT NULL DEFAULT TRUE,
    whale_category TEXT,  -- WHALE, LARGE_WHALE, MEGA_WHALE
    
    -- 스마트 컨트랙트 관련
    input_data TEXT,
    is_contract_to_contract BOOLEAN DEFAULT FALSE,
    has_method_id BOOLEAN DEFAULT FALSE,
    
    -- 라벨 정보
    from_label VARCHAR(255),
    to_label VARCHAR(255),
    
    -- 메타데이터
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- whale_transactions 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_whale_tx_block_number ON whale_transactions(block_number);
CREATE INDEX IF NOT EXISTS idx_whale_tx_block_timestamp ON whale_transactions(block_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_whale_tx_from_address ON whale_transactions(from_address);
CREATE INDEX IF NOT EXISTS idx_whale_tx_to_address ON whale_transactions(to_address);
CREATE INDEX IF NOT EXISTS idx_whale_tx_coin_symbol ON whale_transactions(coin_symbol);
CREATE INDEX IF NOT EXISTS idx_whale_tx_chain ON whale_transactions(chain);
CREATE INDEX IF NOT EXISTS idx_whale_tx_contract_address ON whale_transactions(contract_address) WHERE contract_address IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_whale_tx_from_label ON whale_transactions(from_label) WHERE from_label IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_whale_tx_to_label ON whale_transactions(to_label) WHERE to_label IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_whale_tx_whale_category ON whale_transactions(whale_category);

-- whale_transactions 코멘트
COMMENT ON TABLE whale_transactions IS '고래 거래 데이터 (일반 ETH/토큰 거래)';
COMMENT ON COLUMN whale_transactions.tx_hash IS '트랜잭션 해시 (고유 키)';
COMMENT ON COLUMN whale_transactions.chain IS '블록체인 네트워크 (예: ethereum, polygon)';
COMMENT ON COLUMN whale_transactions.amount_usd IS 'USD 가치 (NULL 허용: 가격 조회 실패 시에도 거래 저장)';
COMMENT ON COLUMN whale_transactions.from_label IS '송신 지갑의 라벨 (예: Binance Hot Wallet, Coinbase 등)';
COMMENT ON COLUMN whale_transactions.to_label IS '수신 지갑의 라벨 (예: Binance Hot Wallet, Coinbase 등)';

-- whale_transactions 업데이트 시간 자동 갱신 트리거 함수
CREATE OR REPLACE FUNCTION update_whale_transactions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- whale_transactions 업데이트 시간 자동 갱신 트리거
-- 기존 트리거가 있으면 삭제 후 재생성
DROP TRIGGER IF EXISTS update_whale_transactions_updated_at ON whale_transactions;
CREATE TRIGGER update_whale_transactions_updated_at
    BEFORE UPDATE ON whale_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_whale_transactions_updated_at();

-- ============================================
-- 2. internal_transactions 테이블 생성
-- ============================================
CREATE TABLE IF NOT EXISTS internal_transactions (
    -- 기본 식별자 (복합 고유 키: tx_hash + trace_id)
    id BIGSERIAL PRIMARY KEY,
    tx_hash TEXT NOT NULL,
    trace_id TEXT NOT NULL DEFAULT '',
    
    -- 블록 정보
    block_number BIGINT NOT NULL,
    block_timestamp TIMESTAMPTZ NOT NULL,
    
    -- 주소 정보
    from_address TEXT NOT NULL,
    to_address TEXT,
    contract_address TEXT,
    
    -- 체인 정보
    chain VARCHAR(50) NOT NULL DEFAULT 'ethereum',
    
    -- 금액 정보
    value_eth NUMERIC(78, 18) NOT NULL DEFAULT 0,  -- ETH 단위 (Wei 변환)
    value_usd NUMERIC(20, 2),  -- USD 가치 (가격 조회 시 계산)
    
    -- 거래 정보
    transaction_type TEXT NOT NULL DEFAULT 'CALL',  -- CALL, CREATE, SUICIDE 등
    is_error BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- 추가 데이터
    input_data TEXT,  -- 스마트 컨트랙트 호출 input 데이터
    gas BIGINT,
    gas_used BIGINT,
    
    -- 메타데이터
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- internal_transactions 복합 고유 키 설정 (같은 tx_hash 내에서 trace_id로 구분)
CREATE UNIQUE INDEX IF NOT EXISTS idx_internal_tx_unique 
ON internal_transactions(tx_hash, trace_id);

-- internal_transactions 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_internal_tx_hash ON internal_transactions(tx_hash);
CREATE INDEX IF NOT EXISTS idx_internal_tx_from ON internal_transactions(from_address);
CREATE INDEX IF NOT EXISTS idx_internal_tx_to ON internal_transactions(to_address);
CREATE INDEX IF NOT EXISTS idx_internal_tx_contract ON internal_transactions(contract_address) WHERE contract_address IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_internal_tx_block_number ON internal_transactions(block_number);
CREATE INDEX IF NOT EXISTS idx_internal_tx_timestamp ON internal_transactions(block_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_internal_tx_chain ON internal_transactions(chain);

-- internal_transactions 코멘트
COMMENT ON TABLE internal_transactions IS '스마트 컨트랙트 내부 거래 (Internal Transactions)';
COMMENT ON COLUMN internal_transactions.chain IS '블록체인 네트워크 (예: ethereum, polygon)';
COMMENT ON COLUMN internal_transactions.trace_id IS '내부 거래 추적 ID (같은 tx_hash 내 고유)';

-- Row Level Security (RLS) 설정 (필요시)
ALTER TABLE internal_transactions ENABLE ROW LEVEL SECURITY;

-- internal_transactions 업데이트 시간 자동 갱신 트리거 함수
CREATE OR REPLACE FUNCTION update_internal_transactions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- internal_transactions 업데이트 시간 자동 갱신 트리거
-- 기존 트리거가 있으면 삭제 후 재생성
DROP TRIGGER IF EXISTS update_internal_transactions_updated_at ON internal_transactions;
CREATE TRIGGER update_internal_transactions_updated_at
    BEFORE UPDATE ON internal_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_internal_transactions_updated_at();

-- ============================================
-- 완료 메시지
-- ============================================
DO $$
BEGIN
    RAISE NOTICE 'Database schema initialized successfully!';
    RAISE NOTICE 'Tables created: whale_transactions, internal_transactions';
END $$;
