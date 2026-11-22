-- ============================================
-- 타임아웃 회피형 안전한 라벨 업데이트 함수
-- ============================================

CREATE OR REPLACE FUNCTION update_labels_safely(batch_size INT DEFAULT 10000)
RETURNS TABLE(updated_count BIGINT, status TEXT) AS $$
DECLARE
    total_updated BIGINT := 0;
    rows_affected BIGINT;
BEGIN
    -- 1. from_label 업데이트 (배치 단위)
    LOOP
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

        total_updated := total_updated + rows_affected;
        
        -- 더 이상 업데이트할 데이터가 없으면 종료
        IF rows_affected = 0 THEN
            EXIT;
        END IF;
        
        -- 진행 상황 알림 (선택 사항)
        RAISE NOTICE 'from_label % 건 업데이트 완료...', total_updated;
    END LOOP;

    RETURN QUERY SELECT total_updated, 'from_label updated';

    -- 초기화
    total_updated := 0;

    -- 2. to_label 업데이트 (배치 단위)
    LOOP
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

        total_updated := total_updated + rows_affected;
        
        IF rows_affected = 0 THEN
            EXIT;
        END IF;
        
        RAISE NOTICE 'to_label % 건 업데이트 완료...', total_updated;
    END LOOP;

    RETURN QUERY SELECT total_updated, 'to_label updated';
END;
$$ LANGUAGE plpgsql;

-- 함수 실행 (타임아웃 방지를 위해 배치 사이즈 조절 가능)
SELECT * FROM update_labels_safely(5000);

