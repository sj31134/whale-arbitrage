-- ============================================
-- whale_address 테이블 PRIMARY KEY 추가
-- ============================================
-- 문제: PRIMARY KEY가 없어서 upsert가 제대로 작동하지 않음
-- 해결: (id, chain_type) 복합 PRIMARY KEY 추가

-- 기존 PRIMARY KEY가 있으면 제거 (안전하게)
DO $$ 
BEGIN
    -- 기존 PRIMARY KEY 제거
    IF EXISTS (
        SELECT 1 
        FROM information_schema.table_constraints 
        WHERE table_name = 'whale_address' 
        AND constraint_type = 'PRIMARY KEY'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.whale_address DROP CONSTRAINT whale_address_pkey;
    END IF;
END $$;

-- 중복 데이터 확인 및 정리
-- 같은 (id, chain_type) 조합이 여러 개 있으면 하나만 남기기
DELETE FROM public.whale_address a
USING public.whale_address b
WHERE a.ctid < b.ctid
  AND a.id = b.id
  AND a.chain_type = b.chain_type;

-- PRIMARY KEY 추가 (id, chain_type 복합 키)
ALTER TABLE public.whale_address 
ADD CONSTRAINT whale_address_pkey PRIMARY KEY (id, chain_type);

-- 인덱스 추가 (조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_whale_address_id ON public.whale_address(id);
CREATE INDEX IF NOT EXISTS idx_whale_address_chain_type ON public.whale_address(chain_type);
CREATE INDEX IF NOT EXISTS idx_whale_address_address ON public.whale_address(address);

-- 완료 메시지
DO $$
BEGIN
    RAISE NOTICE '✅ whale_address 테이블에 PRIMARY KEY (id, chain_type) 추가 완료';
END $$;



