-- ============================================
-- whale_transactions 라벨 빠른 업데이트
-- whale_address 테이블의 정보를 활용
-- ============================================
-- 실행 시간: 약 1-2분 예상

-- 1단계: from_label 업데이트
UPDATE whale_transactions wt
SET from_label = wa.name_tag
FROM whale_address wa
WHERE LOWER(wt.from_address) = LOWER(wa.address)
  AND wt.from_label IS NULL
  AND wa.name_tag IS NOT NULL;

-- 2단계: to_label 업데이트  
UPDATE whale_transactions wt
SET to_label = wa.name_tag
FROM whale_address wa
WHERE LOWER(wt.to_address) = LOWER(wa.address)
  AND wt.to_label IS NULL
  AND wa.name_tag IS NOT NULL;

-- 업데이트 결과 확인
SELECT 
    COUNT(*) as total_transactions,
    COUNT(CASE WHEN from_label IS NOT NULL THEN 1 END) as from_labeled,
    COUNT(CASE WHEN to_label IS NOT NULL THEN 1 END) as to_labeled,
    ROUND(COUNT(CASE WHEN from_label IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as from_label_percent,
    ROUND(COUNT(CASE WHEN to_label IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as to_label_percent
FROM whale_transactions;

