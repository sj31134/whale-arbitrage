-- ============================================
-- Unknown 라벨 및 Transaction Direction 업데이트용 함수
-- ============================================

CREATE OR REPLACE FUNCTION update_post_process_labels(batch_size INT DEFAULT 1000)
RETURNS TABLE(updated_count BIGINT, update_type TEXT) AS $$
DECLARE
    rows_affected BIGINT;
BEGIN
    -- 1. from_label -> Unknown Wallet
    WITH batch AS (
        SELECT tx_hash FROM whale_transactions
        WHERE from_label IS NULL
        LIMIT batch_size
    ),
    updated AS (
        UPDATE whale_transactions
        SET from_label = 'Unknown Wallet',
            updated_at = NOW()
        WHERE tx_hash IN (SELECT tx_hash FROM batch)
        RETURNING 1
    )
    SELECT COUNT(*) INTO rows_affected FROM updated;

    IF rows_affected > 0 THEN
        RETURN QUERY SELECT rows_affected, 'from_unknown';
        RETURN;
    END IF;

    -- 2. to_label -> Unknown Wallet
    WITH batch AS (
        SELECT tx_hash FROM whale_transactions
        WHERE to_label IS NULL
        LIMIT batch_size
    ),
    updated AS (
        UPDATE whale_transactions
        SET to_label = 'Unknown Wallet',
            updated_at = NOW()
        WHERE tx_hash IN (SELECT tx_hash FROM batch)
        RETURNING 1
    )
    SELECT COUNT(*) INTO rows_affected FROM updated;

    IF rows_affected > 0 THEN
        RETURN QUERY SELECT rows_affected, 'to_unknown';
        RETURN;
    END IF;

    -- 3. Transaction Direction (BUY)
    -- 거래소 -> Unknown (출금)
    WITH batch AS (
        SELECT tx_hash FROM whale_transactions
        WHERE transaction_direction IS NULL
          AND from_label ILIKE ANY(ARRAY['%binance%', '%coinbase%', '%kraken%', '%huobi%', '%okx%', '%bitfinex%', '%gate.io%', '%bybit%', '%kucoin%', '%upbit%', '%bithumb%', '%exchange%'])
          AND to_label NOT ILIKE ANY(ARRAY['%binance%', '%coinbase%', '%kraken%', '%huobi%', '%okx%', '%bitfinex%', '%gate.io%', '%bybit%', '%kucoin%', '%upbit%', '%bithumb%', '%exchange%'])
        LIMIT batch_size
    ),
    updated AS (
        UPDATE whale_transactions
        SET transaction_direction = 'BUY',
            updated_at = NOW()
        WHERE tx_hash IN (SELECT tx_hash FROM batch)
        RETURNING 1
    )
    SELECT COUNT(*) INTO rows_affected FROM updated;

    IF rows_affected > 0 THEN
        RETURN QUERY SELECT rows_affected, 'direction_buy';
        RETURN;
    END IF;

    -- 4. Transaction Direction (SELL)
    -- Unknown -> 거래소 (입금)
    WITH batch AS (
        SELECT tx_hash FROM whale_transactions
        WHERE transaction_direction IS NULL
          AND from_label NOT ILIKE ANY(ARRAY['%binance%', '%coinbase%', '%kraken%', '%huobi%', '%okx%', '%bitfinex%', '%gate.io%', '%bybit%', '%kucoin%', '%upbit%', '%bithumb%', '%exchange%'])
          AND to_label ILIKE ANY(ARRAY['%binance%', '%coinbase%', '%kraken%', '%huobi%', '%okx%', '%bitfinex%', '%gate.io%', '%bybit%', '%kucoin%', '%upbit%', '%bithumb%', '%exchange%'])
        LIMIT batch_size
    ),
    updated AS (
        UPDATE whale_transactions
        SET transaction_direction = 'SELL',
            updated_at = NOW()
        WHERE tx_hash IN (SELECT tx_hash FROM batch)
        RETURNING 1
    )
    SELECT COUNT(*) INTO rows_affected FROM updated;

    IF rows_affected > 0 THEN
        RETURN QUERY SELECT rows_affected, 'direction_sell';
        RETURN;
    END IF;

    -- 5. Transaction Direction (MOVE)
    -- 나머지 (거래소간, 개인간)
    WITH batch AS (
        SELECT tx_hash FROM whale_transactions
        WHERE transaction_direction IS NULL
        LIMIT batch_size
    ),
    updated AS (
        UPDATE whale_transactions
        SET transaction_direction = 'MOVE',
            updated_at = NOW()
        WHERE tx_hash IN (SELECT tx_hash FROM batch)
        RETURNING 1
    )
    SELECT COUNT(*) INTO rows_affected FROM updated;

    RETURN QUERY SELECT rows_affected, 'direction_move';
END;
$$ LANGUAGE plpgsql;

