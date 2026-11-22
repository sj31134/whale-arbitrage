-- ============================================
-- 1회 호출용 초경량 라벨 업데이트 함수
-- ============================================

CREATE OR REPLACE FUNCTION update_labels_one_batch(batch_size INT DEFAULT 1000)
RETURNS TABLE(updated_count BIGINT, label_type TEXT) AS $$
DECLARE
    rows_affected BIGINT;
BEGIN
    -- 1. from_label 시도
    WITH batch AS (
        SELECT wt.tx_hash
        FROM whale_transactions wt
        JOIN whale_address wa ON LOWER(wt.from_address) = LOWER(wa.address)
        WHERE wt.from_label IS NULL
          AND wa.name_tag IS NOT NULL
        LIMIT batch_size
    ),
    updated AS (
        UPDATE whale_transactions wt
        SET from_label = wa.name_tag,
            updated_at = NOW()
        FROM whale_address wa
        WHERE wt.tx_hash IN (SELECT tx_hash FROM batch)
          AND LOWER(wt.from_address) = LOWER(wa.address)
        RETURNING 1
    )
    SELECT COUNT(*) INTO rows_affected FROM updated;

    IF rows_affected > 0 THEN
        RETURN QUERY SELECT rows_affected, 'from_label';
        RETURN;
    END IF;

    -- 2. to_label 시도 (from_label 업데이트할 게 없을 때만 실행)
    WITH batch AS (
        SELECT wt.tx_hash
        FROM whale_transactions wt
        JOIN whale_address wa ON LOWER(wt.to_address) = LOWER(wa.address)
        WHERE wt.to_label IS NULL
          AND wa.name_tag IS NOT NULL
        LIMIT batch_size
    ),
    updated AS (
        UPDATE whale_transactions wt
        SET to_label = wa.name_tag,
            updated_at = NOW()
        FROM whale_address wa
        WHERE wt.tx_hash IN (SELECT tx_hash FROM batch)
          AND LOWER(wt.to_address) = LOWER(wa.address)
        RETURNING 1
    )
    SELECT COUNT(*) INTO rows_affected FROM updated;

    RETURN QUERY SELECT rows_affected, 'to_label';
END;
$$ LANGUAGE plpgsql;

