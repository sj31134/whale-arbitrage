-- ============================================
-- 초고속 거래 유형 라벨링 (RPC Function)
-- 실행 시간: 1-5분 예상
-- ============================================

-- Step 1: transaction_direction 컬럼 추가 (아직 없다면)
ALTER TABLE whale_transactions 
ADD COLUMN IF NOT EXISTS transaction_direction VARCHAR(20);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_whale_tx_direction 
ON whale_transactions(transaction_direction);

-- 컬럼 설명
COMMENT ON COLUMN whale_transactions.transaction_direction 
IS '거래 유형: BUY(매수), SELL(매도), MOVE(이동/전송)';

-- ============================================
-- Step 2: RPC Function 생성
-- ============================================
CREATE OR REPLACE FUNCTION post_process_labels_and_direction()
RETURNS JSON AS $$
DECLARE
    from_label_count BIGINT;
    to_label_count BIGINT;
    buy_count BIGINT;
    sell_count BIGINT;
    move_count BIGINT;
    result JSON;
BEGIN
    RAISE NOTICE '🚀 라벨 후처리 및 거래 유형 분류 시작...';
    
    -- ============================================
    -- 1. NULL from_label → 'Unknown Wallet'
    -- ============================================
    RAISE NOTICE '1️⃣ from_label 업데이트 중...';
    UPDATE whale_transactions
    SET from_label = 'Unknown Wallet'
    WHERE from_label IS NULL;
    
    GET DIAGNOSTICS from_label_count = ROW_COUNT;
    RAISE NOTICE '   ✅ from_label: % 건 업데이트 완료', from_label_count;
    
    -- ============================================
    -- 2. NULL to_label → 'Unknown Wallet'
    -- ============================================
    RAISE NOTICE '2️⃣ to_label 업데이트 중...';
    UPDATE whale_transactions
    SET to_label = 'Unknown Wallet'
    WHERE to_label IS NULL;
    
    GET DIAGNOSTICS to_label_count = ROW_COUNT;
    RAISE NOTICE '   ✅ to_label: % 건 업데이트 완료', to_label_count;
    
    -- ============================================
    -- 3. BUY: 거래소 → 일반 지갑
    -- ============================================
    RAISE NOTICE '3️⃣ BUY 거래 라벨링 중...';
    UPDATE whale_transactions
    SET transaction_direction = 'BUY'
    WHERE transaction_direction IS NULL
    AND (
        from_label ILIKE ANY(ARRAY[
            '%binance%', '%coinbase%', '%kraken%', '%huobi%', '%okx%',
            '%bitfinex%', '%gate.io%', '%bybit%', '%kucoin%', 
            '%upbit%', '%bithumb%', '%bittrex%', '%gemini%',
            '%crypto.com%', '%exchange%'
        ])
    )
    AND NOT (
        to_label ILIKE ANY(ARRAY[
            '%binance%', '%coinbase%', '%kraken%', '%huobi%', '%okx%',
            '%bitfinex%', '%gate.io%', '%bybit%', '%kucoin%', 
            '%upbit%', '%bithumb%', '%bittrex%', '%gemini%',
            '%crypto.com%', '%exchange%'
        ])
    );
    
    GET DIAGNOSTICS buy_count = ROW_COUNT;
    RAISE NOTICE '   ✅ BUY: % 건 라벨링 완료', buy_count;
    
    -- ============================================
    -- 4. SELL: 일반 지갑 → 거래소
    -- ============================================
    RAISE NOTICE '4️⃣ SELL 거래 라벨링 중...';
    UPDATE whale_transactions
    SET transaction_direction = 'SELL'
    WHERE transaction_direction IS NULL
    AND NOT (
        from_label ILIKE ANY(ARRAY[
            '%binance%', '%coinbase%', '%kraken%', '%huobi%', '%okx%',
            '%bitfinex%', '%gate.io%', '%bybit%', '%kucoin%', 
            '%upbit%', '%bithumb%', '%bittrex%', '%gemini%',
            '%crypto.com%', '%exchange%'
        ])
    )
    AND (
        to_label ILIKE ANY(ARRAY[
            '%binance%', '%coinbase%', '%kraken%', '%huobi%', '%okx%',
            '%bitfinex%', '%gate.io%', '%bybit%', '%kucoin%', 
            '%upbit%', '%bithumb%', '%bittrex%', '%gemini%',
            '%crypto.com%', '%exchange%'
        ])
    );
    
    GET DIAGNOSTICS sell_count = ROW_COUNT;
    RAISE NOTICE '   ✅ SELL: % 건 라벨링 완료', sell_count;
    
    -- ============================================
    -- 5. MOVE: 나머지 (지갑 간 이동, 컨트랙트 실행 등)
    -- ============================================
    RAISE NOTICE '5️⃣ MOVE 거래 라벨링 중...';
    UPDATE whale_transactions
    SET transaction_direction = 'MOVE'
    WHERE transaction_direction IS NULL;
    
    GET DIAGNOSTICS move_count = ROW_COUNT;
    RAISE NOTICE '   ✅ MOVE: % 건 라벨링 완료', move_count;
    
    -- ============================================
    -- 결과 반환
    -- ============================================
    result := json_build_object(
        'from_label_updated', from_label_count,
        'to_label_updated', to_label_count,
        'buy_transactions', buy_count,
        'sell_transactions', sell_count,
        'move_transactions', move_count,
        'total_processed', buy_count + sell_count + move_count
    );
    
    RAISE NOTICE '🎉 모든 작업 완료!';
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Step 3: 함수 실행 (실제 라벨링 수행)
-- ============================================
-- 아래 SELECT 문을 실행하면 전체 작업이 시작됩니다
SELECT * FROM post_process_labels_and_direction();

-- ============================================
-- Step 4: 결과 확인
-- ============================================
-- 거래 유형별 통계
SELECT 
    transaction_direction,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage,
    ROUND(SUM(amount_usd)::NUMERIC, 2) as total_usd,
    ROUND(AVG(amount_usd)::NUMERIC, 2) as avg_usd
FROM whale_transactions
WHERE transaction_direction IS NOT NULL
GROUP BY transaction_direction
ORDER BY count DESC;

-- 코인별 거래 유형 통계
SELECT 
    coin_symbol,
    transaction_direction,
    COUNT(*) as count,
    ROUND(SUM(amount_usd)::NUMERIC, 2) as total_usd
FROM whale_transactions
WHERE transaction_direction IS NOT NULL
GROUP BY coin_symbol, transaction_direction
ORDER BY coin_symbol, transaction_direction;

-- 샘플 데이터 확인 (각 유형별 5건)
-- BUY
SELECT 'BUY' as type, tx_hash, from_label, to_label, coin_symbol, amount, amount_usd
FROM whale_transactions
WHERE transaction_direction = 'BUY'
ORDER BY block_timestamp DESC
LIMIT 5;

-- SELL
SELECT 'SELL' as type, tx_hash, from_label, to_label, coin_symbol, amount, amount_usd
FROM whale_transactions
WHERE transaction_direction = 'SELL'
ORDER BY block_timestamp DESC
LIMIT 5;

-- MOVE
SELECT 'MOVE' as type, tx_hash, from_label, to_label, coin_symbol, amount, amount_usd
FROM whale_transactions
WHERE transaction_direction = 'MOVE'
ORDER BY block_timestamp DESC
LIMIT 5;

