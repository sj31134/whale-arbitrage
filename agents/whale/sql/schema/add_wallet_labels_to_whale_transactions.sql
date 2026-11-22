-- whale_transactions 테이블에 from_label, to_label 컬럼 추가
-- Supabase SQL Editor에서 이 파일의 내용을 복사하여 실행하세요

-- from_label 컬럼 추가
ALTER TABLE whale_transactions 
ADD COLUMN IF NOT EXISTS from_label VARCHAR(255);

-- to_label 컬럼 추가
ALTER TABLE whale_transactions 
ADD COLUMN IF NOT EXISTS to_label VARCHAR(255);

-- 인덱스 추가 (라벨 기반 조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_whale_tx_from_label 
ON whale_transactions(from_label) 
WHERE from_label IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_whale_tx_to_label 
ON whale_transactions(to_label) 
WHERE to_label IS NOT NULL;

-- 코멘트 추가 (컬럼 설명)
COMMENT ON COLUMN whale_transactions.from_label IS '송신 지갑의 라벨 (예: Binance Hot Wallet, Coinbase 등)';
COMMENT ON COLUMN whale_transactions.to_label IS '수신 지갑의 라벨 (예: Binance Hot Wallet, Coinbase 등)';

