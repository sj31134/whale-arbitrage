-- ============================================
-- transaction_direction 컬럼만 추가
-- (매우 빠름 - Timeout 안 걸림)
-- ============================================

-- 컬럼 추가
ALTER TABLE whale_transactions 
ADD COLUMN IF NOT EXISTS transaction_direction VARCHAR(20);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_whale_tx_direction 
ON whale_transactions(transaction_direction);

-- 컬럼 설명
COMMENT ON COLUMN whale_transactions.transaction_direction 
IS '거래 유형: BUY(매수), SELL(매도), MOVE(이동/전송)';

-- 확인
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'whale_transactions' 
  AND column_name = 'transaction_direction';

