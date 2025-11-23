-- =================================================
-- amount_usd를 일괄 업데이트하는 함수
-- whale_transactions의 코인 심볼과 시간 -> price_history의 가격 매칭
-- =================================================

CREATE OR REPLACE FUNCTION update_amount_usd_batch(batch_limit INT DEFAULT 5000)
RETURNS BIGINT AS $$
DECLARE
    updated_count BIGINT;
BEGIN
    -- 업데이트 대상 트랜잭션 선정 (amount_usd가 NULL인 것들)
    WITH target_txs AS (
        SELECT wt.tx_hash, wt.amount, wt.coin_symbol, wt.block_timestamp
        FROM whale_transactions wt
        WHERE wt.amount_usd IS NULL
          AND wt.coin_symbol IN (SELECT symbol FROM cryptocurrencies) -- 매칭 가능한 코인만
        LIMIT batch_limit
    ),
    -- 가격 정보 매칭 (시간은 시간 단위 절삭 date_trunc 사용)
    matched_prices AS (
        SELECT 
            tt.tx_hash,
            (tt.amount * ph.close_price) AS calc_usd
        FROM target_txs tt
        JOIN cryptocurrencies c ON tt.coin_symbol = c.symbol
        JOIN price_history ph ON c.id = ph.crypto_id
        WHERE ph.timestamp = date_trunc('hour', tt.block_timestamp)
    ),
    -- 업데이트 실행
    performed_update AS (
        UPDATE whale_transactions wt
        SET amount_usd = mp.calc_usd,
            updated_at = NOW()
        FROM matched_prices mp
        WHERE wt.tx_hash = mp.tx_hash
        RETURNING 1
    )
    SELECT COUNT(*) INTO updated_count FROM performed_update;

    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

