# Internal Transactions 테이블 스키마

이 문서는 Supabase에서 `internal_transactions` 테이블을 생성하기 위한 스키마 제안입니다.

## 테이블 개요

`internal_transactions` 테이블은 스마트 컨트랙트 호출로 인한 내부 거래(Internal Transactions)를 저장합니다. 이 거래들은 `type=call`이고 `isError=0`인 성공적인 스마트 컨트랙트 호출만 포함합니다.

## 스키마 정의

### Supabase SQL (PostgreSQL)

```sql
-- Internal Transactions 테이블 생성
CREATE TABLE IF NOT EXISTS internal_transactions (
    -- 기본 식별자 (복합 고유 키: tx_hash + trace_id)
    id BIGSERIAL PRIMARY KEY,
    tx_hash TEXT NOT NULL,
    trace_id TEXT NOT NULL DEFAULT '',
    
    -- 블록 정보
    block_number BIGINT NOT NULL,
    block_timestamp TIMESTAMPTZ NOT NULL,
    
    -- 주소 정보
    from_address TEXT NOT NULL,
    to_address TEXT,
    contract_address TEXT,
    
    -- 금액 정보
    value_eth NUMERIC(78, 18) NOT NULL DEFAULT 0,  -- ETH 단위 (Wei 변환)
    value_usd NUMERIC(20, 2),  -- USD 가치 (가격 조회 시 계산)
    
    -- 거래 정보
    transaction_type TEXT NOT NULL DEFAULT 'CALL',  -- CALL, CREATE, SUICIDE 등
    is_error BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- 추가 데이터
    input_data TEXT,  -- 스마트 컨트랙트 호출 input 데이터
    gas BIGINT,
    gas_used BIGINT,
    
    -- 메타데이터
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 복합 고유 키 설정 (같은 tx_hash 내에서 trace_id로 구분)
CREATE UNIQUE INDEX IF NOT EXISTS idx_internal_tx_unique 
ON internal_transactions(tx_hash, trace_id);

-- 인덱스 생성 (조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_internal_tx_hash ON internal_transactions(tx_hash);
CREATE INDEX IF NOT EXISTS idx_internal_tx_from ON internal_transactions(from_address);
CREATE INDEX IF NOT EXISTS idx_internal_tx_to ON internal_transactions(to_address);
CREATE INDEX IF NOT EXISTS idx_internal_tx_contract ON internal_transactions(contract_address);
CREATE INDEX IF NOT EXISTS idx_internal_tx_block_number ON internal_transactions(block_number);
CREATE INDEX IF NOT EXISTS idx_internal_tx_timestamp ON internal_transactions(block_timestamp DESC);

-- Row Level Security (RLS) 설정 (필요시)
ALTER TABLE internal_transactions ENABLE ROW LEVEL SECURITY;

-- 업데이트 시간 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_internal_transactions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_internal_transactions_updated_at
    BEFORE UPDATE ON internal_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_internal_transactions_updated_at();
```

## 필드 설명

| 필드명 | 타입 | 설명 | 제약 조건 |
|--------|------|------|----------|
| `id` | BIGSERIAL | 자동 증가 기본 키 | PRIMARY KEY |
| `tx_hash` | TEXT | 원본 트랜잭션 해시 | NOT NULL |
| `trace_id` | TEXT | 내부 거래 추적 ID (같은 tx_hash 내 고유) | NOT NULL, DEFAULT '' |
| `block_number` | BIGINT | 블록 번호 | NOT NULL |
| `block_timestamp` | TIMESTAMPTZ | 블록 타임스탬프 (ISO 형식) | NOT NULL |
| `from_address` | TEXT | 송신 주소 (소문자) | NOT NULL |
| `to_address` | TEXT | 수신 주소 (소문자) | NULL 가능 |
| `contract_address` | TEXT | 스마트 컨트랙트 주소 (소문자) | NULL 가능 |
| `value_eth` | NUMERIC(78,18) | ETH 가치 (Wei에서 변환) | NOT NULL, DEFAULT 0 |
| `value_usd` | NUMERIC(20,2) | USD 가치 | NULL 가능 |
| `transaction_type` | TEXT | 거래 타입 (CALL, CREATE, SUICIDE) | NOT NULL, DEFAULT 'CALL' |
| `is_error` | BOOLEAN | 에러 여부 | NOT NULL, DEFAULT FALSE |
| `input_data` | TEXT | 스마트 컨트랙트 호출 input 데이터 | NULL 가능 |
| `gas` | BIGINT | 가스 한도 | NULL 가능 |
| `gas_used` | BIGINT | 사용된 가스 | NULL 가능 |
| `created_at` | TIMESTAMPTZ | 생성 시간 | DEFAULT NOW() |
| `updated_at` | TIMESTAMPTZ | 업데이트 시간 | DEFAULT NOW() |

## 주요 특징

1. **복합 고유 키**: `tx_hash` + `trace_id` 조합으로 고유성 보장
   - 같은 트랜잭션 해시 내에서 여러 내부 거래가 있을 수 있음
   - `trace_id`가 내부 거래를 구분하는 식별자

2. **필터링**: `type=call`이고 `isError=0`인 거래만 저장
   - 코드에서 이미 필터링되지만, DB 레벨에서도 체크 가능

3. **인덱스 최적화**: 
   - `tx_hash`: 트랜잭션별 조회
   - `from_address`, `to_address`: 주소별 조회
   - `block_timestamp`: 시간 범위 조회

4. **확장성**: 
   - `value_usd`는 선택적 (가격 조회 실패 시 NULL)
   - `contract_address`는 스마트 컨트랙트 호출 시에만 값 존재

## whale_transactions 테이블과의 차이점

| 항목 | whale_transactions | internal_transactions |
|------|-------------------|----------------------|
| **거래 유형** | 일반 ETH/토큰 거래 | 스마트 컨트랙트 내부 거래 |
| **고유 키** | `tx_hash` 단독 | `tx_hash` + `trace_id` 복합 |
| **금액 필드** | `amount`, `amount_usd` | `value_eth`, `value_usd` |
| **추가 필드** | `coin_symbol`, `whale_category` | `trace_id`, `transaction_type` |
| **필터링 기준** | 고래 거래 ($50K 이상) | 성공적인 call 타입 거래 |

## 사용 예시

### Python에서 사용

```python
from src.database.supabase_client import get_supabase_client

supabase = get_supabase_client()

# 내부 거래 저장
internal_txs = [...]  # 수집된 내부 거래 리스트
count = supabase.insert_internal_transactions(internal_txs)
```

### SQL 조회 예시

```sql
-- 특정 주소의 최근 내부 거래 조회
SELECT * FROM internal_transactions
WHERE from_address = '0x...'
ORDER BY block_timestamp DESC
LIMIT 100;

-- 특정 트랜잭션의 모든 내부 거래 조회
SELECT * FROM internal_transactions
WHERE tx_hash = '0x...'
ORDER BY trace_id;
```

## 주의사항

1. **테이블 생성**: Supabase 대시보드에서 SQL Editor를 통해 실행하거나, 마이그레이션 도구를 사용하세요.

2. **RLS 정책**: Row Level Security를 활성화한 경우, 적절한 정책을 설정해야 합니다.

3. **데이터 타입**: `value_eth`는 NUMERIC(78, 18)로 설정하여 Wei 단위의 큰 값도 정확히 저장할 수 있습니다.

