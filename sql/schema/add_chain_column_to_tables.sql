-- whale_transactions와 internal_transactions 테이블에 chain 컬럼 추가
-- Supabase SQL Editor에서 이 파일의 내용을 복사하여 실행하세요

-- whale_transactions 테이블에 chain 컬럼 추가
ALTER TABLE whale_transactions 
ADD COLUMN IF NOT EXISTS chain VARCHAR(50) DEFAULT 'ethereum';

-- whale_transactions의 chain 컬럼에 인덱스 추가 (체인별 조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_whale_tx_chain 
ON whale_transactions(chain);

-- internal_transactions 테이블에 chain 컬럼 추가
ALTER TABLE internal_transactions 
ADD COLUMN IF NOT EXISTS chain VARCHAR(50) DEFAULT 'ethereum';

-- internal_transactions의 chain 컬럼에 인덱스 추가 (체인별 조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_internal_tx_chain 
ON internal_transactions(chain);

-- 코멘트 추가 (컬럼 설명)
COMMENT ON COLUMN whale_transactions.chain IS '블록체인 네트워크 (예: ethereum, polygon)';
COMMENT ON COLUMN internal_transactions.chain IS '블록체인 네트워크 (예: ethereum, polygon)';

