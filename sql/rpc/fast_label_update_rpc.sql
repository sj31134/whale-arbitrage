-- ============================================
-- 초고속 라벨 업데이트를 위한 RPC 함수
-- ============================================

-- 함수 생성
CREATE OR REPLACE FUNCTION update_whale_labels_fast()
RETURNS TABLE(
    updated_from BIGINT,
    updated_to BIGINT
) AS $$
DECLARE
    from_count BIGINT;
    to_count BIGINT;
BEGIN
    -- 타임아웃을 10분으로 설정 (대량 업데이트를 위해)
    SET statement_timeout = '600s';

    -- 1. from_label 일괄 업데이트
    -- whale_address 테이블과 조인하여 한 번에 업데이트
    UPDATE whale_transactions wt
    SET from_label = wa.name_tag,
        updated_at = NOW()
    FROM whale_address wa
    WHERE LOWER(wt.from_address) = LOWER(wa.address)
      AND wt.from_label IS NULL
      AND wa.name_tag IS NOT NULL;
      
    GET DIAGNOSTICS from_count = ROW_COUNT;
    RAISE NOTICE 'from_label 업데이트: % 건', from_count;

    -- 2. to_label 일괄 업데이트
    -- whale_address 테이블과 조인하여 한 번에 업데이트
    UPDATE whale_transactions wt
    SET to_label = wa.name_tag,
        updated_at = NOW()
    FROM whale_address wa
    WHERE LOWER(wt.to_address) = LOWER(wa.address)
      AND wt.to_label IS NULL
      AND wa.name_tag IS NOT NULL;
      
    GET DIAGNOSTICS to_count = ROW_COUNT;
    RAISE NOTICE 'to_label 업데이트: % 건', to_count;

    -- 결과 반환
    RETURN QUERY SELECT from_count, to_count;
END;
$$ LANGUAGE plpgsql;

-- 실행 예시 (주석 해제 후 실행)
-- SELECT * FROM update_whale_labels_fast();

