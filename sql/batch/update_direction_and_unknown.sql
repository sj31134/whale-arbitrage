-- ============================================
-- 1. NULL 라벨을 'Unknown Wallet'으로 업데이트
-- 2. transaction_direction 컬럼 추가 및 분류
-- ============================================

-- 1. 컬럼 추가 (없으면 생성)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'whale_transactions' AND column_name = 'transaction_direction') THEN
        ALTER TABLE whale_transactions ADD COLUMN transaction_direction VARCHAR(20);
    END IF;
END $$;

-- 2. NULL 라벨을 'Unknown Wallet'으로 업데이트 (배치 처리 권장하지만, SQL 한방으로 시도)
-- 타임아웃 방지를 위해 COALESCE 사용은 조회 시에 하는 게 좋지만, 
-- 사용자가 "대체해"라고 했으므로 데이터 자체를 업데이트합니다.

UPDATE whale_transactions
SET from_label = 'Unknown Wallet'
WHERE from_label IS NULL;

UPDATE whale_transactions
SET to_label = 'Unknown Wallet'
WHERE to_label IS NULL;

-- 3. 거래 유형(Buy/Sell/Move) 분류 및 업데이트
-- 거래소 목록 정의 (임시 테이블 또는 배열 사용)
-- 여기서는 간단히 ILIKE로 처리

DO $$
DECLARE
    exchange_pattern TEXT := '%(binance|coinbase|kraken|huobi|okx|bitfinex|gate.io|bybit|kucoin|upbit|bithumb|exchange)%';
BEGIN
    -- BUY: 거래소 -> 개인 지갑 (출금)
    UPDATE whale_transactions
    SET transaction_direction = 'BUY'
    WHERE from_label ILIKE exchange_pattern
      AND to_label NOT ILIKE exchange_pattern;

    -- SELL: 개인 지갑 -> 거래소 (입금)
    UPDATE whale_transactions
    SET transaction_direction = 'SELL'
    WHERE from_label NOT ILIKE exchange_pattern
      AND to_label ILIKE exchange_pattern;

    -- MOVE: 거래소 <-> 거래소 OR 개인 <-> 개인
    UPDATE whale_transactions
    SET transaction_direction = 'MOVE'
    WHERE transaction_direction IS NULL;
    
END $$;

