-- ============================================
-- 확실한 라벨 업데이트 스크립트 (Direct Execution)
-- ============================================

-- 1. from_label 업데이트
WITH updated_from AS (
    UPDATE whale_transactions wt
    SET from_label = wa.name_tag,
        updated_at = NOW()
    FROM whale_address wa
    WHERE LOWER(wt.from_address) = LOWER(wa.address)
      AND wt.from_label IS NULL
      AND wa.name_tag IS NOT NULL
    RETURNING 1
)
SELECT COUNT(*) as "from_label_updated_count" FROM updated_from;

-- 2. to_label 업데이트
WITH updated_to AS (
    UPDATE whale_transactions wt
    SET to_label = wa.name_tag,
        updated_at = NOW()
    FROM whale_address wa
    WHERE LOWER(wt.to_address) = LOWER(wa.address)
      AND wt.to_label IS NULL
      AND wa.name_tag IS NOT NULL
    RETURNING 1
)
SELECT COUNT(*) as "to_label_updated_count" FROM updated_to;

-- 3. 최종 상태 확인
SELECT 
    COUNT(*) as total_transactions,
    COUNT(from_label) as filled_from_labels,
    COUNT(to_label) as filled_to_labels,
    ROUND(COUNT(from_label) * 100.0 / COUNT(*), 2) as from_label_percent,
    ROUND(COUNT(to_label) * 100.0 / COUNT(*), 2) as to_label_percent
FROM whale_transactions;

