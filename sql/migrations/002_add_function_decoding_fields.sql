-- ============================================
-- 함수 시그니처 디코딩 필드 추가 마이그레이션
-- ============================================
-- 실행 방법: Supabase SQL Editor에서 직접 실행
-- 또는 scripts/setup_database.py와 유사한 방식으로 실행 안내

-- ============================================
-- 1. whale_transactions 테이블에 함수 디코딩 필드 추가
-- ============================================

-- method_id 컬럼 추가 (함수 시그니처의 처음 4바이트, 예: 0xa9059cbb)
ALTER TABLE whale_transactions
ADD COLUMN IF NOT EXISTS method_id TEXT;

-- function_name 컬럼 추가 (디코딩된 함수 이름, 예: transfer, approve)
ALTER TABLE whale_transactions
ADD COLUMN IF NOT EXISTS function_name VARCHAR(255);

-- 인덱스 생성 (함수 이름으로 조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_whale_tx_function_name 
ON whale_transactions(function_name) 
WHERE function_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_whale_tx_method_id 
ON whale_transactions(method_id) 
WHERE method_id IS NOT NULL;

-- 코멘트 추가
COMMENT ON COLUMN whale_transactions.method_id IS '스마트 컨트랙트 함수 시그니처의 Method ID (처음 4바이트, 0x + 8자 hex)';
COMMENT ON COLUMN whale_transactions.function_name IS '디코딩된 함수 이름 (예: transfer, approve, swap) - 4byte.directory API 사용';

-- ============================================
-- 2. internal_transactions 테이블에 함수 디코딩 필드 추가
-- ============================================

-- method_id 컬럼 추가
ALTER TABLE internal_transactions
ADD COLUMN IF NOT EXISTS method_id TEXT;

-- function_name 컬럼 추가
ALTER TABLE internal_transactions
ADD COLUMN IF NOT EXISTS function_name VARCHAR(255);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_internal_tx_function_name 
ON internal_transactions(function_name) 
WHERE function_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_internal_tx_method_id 
ON internal_transactions(method_id) 
WHERE method_id IS NOT NULL;

-- 코멘트 추가
COMMENT ON COLUMN internal_transactions.method_id IS '스마트 컨트랙트 함수 시그니처의 Method ID (처음 4바이트, 0x + 8자 hex)';
COMMENT ON COLUMN internal_transactions.function_name IS '디코딩된 함수 이름 (예: transfer, approve, swap) - 4byte.directory API 사용';

-- ============================================
-- 완료 메시지
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '함수 시그니처 디코딩 필드 추가 완료!';
    RAISE NOTICE '추가된 컬럼: method_id, function_name (whale_transactions, internal_transactions)';
END $$;
