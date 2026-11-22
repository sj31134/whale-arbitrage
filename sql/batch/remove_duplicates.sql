-- ============================================
-- whale_address 테이블 중복 데이터 제거
-- ============================================
-- 같은 (id, chain_type) 조합이 여러 개 있으면 가장 최근 것만 남기기

-- 중복 데이터 확인
SELECT 
    id, 
    chain_type, 
    COUNT(*) as count
FROM public.whale_address
GROUP BY id, chain_type
HAVING COUNT(*) > 1
ORDER BY count DESC
LIMIT 10;

-- 중복 데이터 제거 (같은 (id, chain_type) 중 가장 최근 것만 남기기)
-- ctid는 PostgreSQL의 내부 행 식별자
DELETE FROM public.whale_address a
USING public.whale_address b
WHERE a.id = b.id
  AND a.chain_type = b.chain_type
  AND a.ctid < b.ctid;

-- 결과 확인
SELECT 
    chain_type,
    COUNT(*) as count
FROM public.whale_address
GROUP BY chain_type
ORDER BY chain_type;



