-- Internal Transactions 테이블 생성
-- Supabase SQL Editor에서 이 파일의 내용을 복사하여 실행하세요

-- 테이블 생성
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

-- 복합 고유 키 설정 (같은 tx_hash 내에서 trace_id로 구분)
CREATE UNIQUE INDEX IF NOT EXISTS idx_internal_tx_unique 
ON internal_transactions(tx_hash, trace_id);

-- 인덱스 생성 (조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_internal_tx_hash ON internal_transactions(tx_hash);
CREATE INDEX IF NOT EXISTS idx_internal_tx_from ON internal_transactions(from_address);
CREATE INDEX IF NOT EXISTS idx_internal_tx_to ON internal_transactions(to_address);
CREATE INDEX IF NOT EXISTS idx_internal_tx_contract ON internal_transactions(contract_address);
CREATE INDEX IF NOT EXISTS idx_internal_tx_block_number ON internal_transactions(block_number);
CREATE INDEX IF NOT EXISTS idx_internal_tx_timestamp ON internal_transactions(block_timestamp DESC);

-- Row Level Security (RLS) 설정 (필요시)
ALTER TABLE internal_transactions ENABLE ROW LEVEL SECURITY;

-- 업데이트 시간 자동 갱신 트리거 함수
CREATE OR REPLACE FUNCTION update_internal_transactions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 업데이트 시간 자동 갱신 트리거
CREATE TRIGGER update_internal_transactions_updated_at
    BEFORE UPDATE ON internal_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_internal_transactions_updated_at();

