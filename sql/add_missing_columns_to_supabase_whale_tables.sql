-- whale_transactions 테이블에 누락된 컬럼 추가
-- Supabase SQL Editor에서 실행하세요

ALTER TABLE public.whale_transactions 
ADD COLUMN IF NOT EXISTS is_error BOOLEAN;

ALTER TABLE public.whale_transactions 
ADD COLUMN IF NOT EXISTS from_label TEXT;

ALTER TABLE public.whale_transactions 
ADD COLUMN IF NOT EXISTS to_label TEXT;

ALTER TABLE public.whale_transactions 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_whale_tx_from_label ON public.whale_transactions(from_label) WHERE from_label IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_whale_tx_to_label ON public.whale_transactions(to_label) WHERE to_label IS NOT NULL;

-- whale_address 테이블에 누락된 컬럼 추가
ALTER TABLE public.whale_address 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- 기존 테이블의 primary key는 유지 (id, chain_type 복합키)

