# BSC Hybrid Collection System 사용 가이드

## 📋 목차
1. [개요](#개요)
2. [시스템 구조](#시스템-구조)
3. [설치 및 설정](#설치-및-설정)
4. [사용 방법](#사용-방법)
5. [고급 설정](#고급-설정)
6. [트러블슈팅](#트러블슈팅)

---

## 개요

BSC Hybrid Collection System은 Binance Smart Chain(BSC) 거래 데이터를 효율적으로 수집하는 하이브리드 시스템입니다.

### 주요 특징
- **API 우선**: BSCScan API로 빠르고 정확한 기본 데이터 수집
- **선택적 웹 스크래핑**: 고액 거래에 대해서만 추가 정보(Method, Label) 수집
- **Supabase 연동**: whale_address 테이블에서 동적으로 주소 로드
- **체크포인트 시스템**: 중단 시에도 이어서 실행 가능
- **자동 백업**: 로컬 CSV 백업 자동 저장

### 성능
- 100개 주소, 50,000건 거래 기준
- API 수집: 약 2-5분
- 웹 스크래핑 (고액 거래 1,000건): 약 33-40분
- **총 소요 시간: 약 45-50분**

---

## 시스템 구조

```
BSC Hybrid Collection System
│
├── scripts/collectors/
│   ├── bsc_api_collector.py      # API 수집 모듈
│   ├── bsc_web_scraper.py         # 웹 스크래핑 모듈
│   └── bsc_hybrid_collector.py   # 통합 실행 스크립트
│
├── scripts/test_bsc_hybrid.py     # 검증 스크립트
│
└── docs/
    └── BSC_HYBRID_COLLECTION_GUIDE.md  # 이 문서
```

### 워크플로우

```
Supabase whale_address
    ↓
[Step 1] API로 전체 거래 수집
    ↓
[Step 2] 고액 거래 필터링 (BNB 100개 이상)
    ↓
[Step 3] 웹 스크래핑으로 추가 정보 보완
    ↓
[Step 4] whale_transactions에 저장
    ↓
로컬 CSV 백업 + 체크포인트 저장
```

---

## 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

새로운 패키지:
- `beautifulsoup4>=4.9.0` - HTML 파싱
- `lxml>=4.6.0` - 빠른 XML/HTML 파서

### 2. 환경 변수 설정

`.env` 파일에 다음 변수가 설정되어 있어야 합니다:

```bash
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
ETHERSCAN_API_KEY=your_etherscan_api_key  # BSCScan에도 사용 가능
```

### 3. 디렉토리 구조

실행 시 자동으로 생성되지만, 미리 생성해도 됩니다:

```bash
mkdir -p checkpoints
mkdir -p data/backups
```

---

## 사용 방법

### 기본 실행

```bash
# 전체 프로세스 실행 (API + 웹 스크래핑 + 저장)
python scripts/collectors/bsc_hybrid_collector.py
```

### 테스트 모드

```bash
# 처음 3개 주소만 처리 (테스트용)
python scripts/collectors/bsc_hybrid_collector.py --test
```

### API만 실행

```bash
# 웹 스크래핑 건너뛰기
python scripts/collectors/bsc_hybrid_collector.py --skip-scraping
```

### 고액 거래 기준 조정

```bash
# BNB 1,000개 이상, USD $500,000 이상만 스크래핑
python scripts/collectors/bsc_hybrid_collector.py --min-bnb 1000 --min-usd 500000
```

### 저장 없이 수집만

```bash
# 데이터베이스 저장 건너뛰기 (CSV 백업만)
python scripts/collectors/bsc_hybrid_collector.py --no-save
```

### 웹 스크래핑 속도 조절

```bash
# 요청 간격을 5초로 증가 (더 안전하지만 느림)
python scripts/collectors/bsc_hybrid_collector.py --scraping-delay 5
```

---

## 개별 모듈 사용

### 1. API Collector 단독 사용

```bash
# 테스트 모드 (첫 3개 주소)
python scripts/collectors/bsc_api_collector.py --test

# 전체 수집 및 저장
python scripts/collectors/bsc_api_collector.py --save
```

### 2. Web Scraper 단독 사용

```bash
# 특정 거래 해시 스크래핑
python scripts/collectors/bsc_web_scraper.py \
  --tx-hash 0x1234567890abcdef... \
  --address 0xabcdef...
```

### 3. Python 코드에서 사용

```python
from scripts.collectors.bsc_api_collector import (
    get_bsc_addresses_from_supabase,
    collect_all_bsc_transactions,
    is_high_value_transaction
)

from scripts.collectors.bsc_web_scraper import (
    scrape_transaction_details,
    scrape_multiple_transactions
)

# 주소 조회
addresses = get_bsc_addresses_from_supabase()

# 거래 수집
transactions = collect_all_bsc_transactions(addresses)

# 고액 거래 필터링
high_value_txs = [tx for tx in transactions if is_high_value_transaction(tx)]

# 웹 스크래핑
enriched_txs = scrape_multiple_transactions(high_value_txs)
```

---

## 검증 및 테스트

### 전체 검증

```bash
python scripts/test_bsc_hybrid.py
```

검증 항목:
1. Supabase 연결
2. whale_address 테이블 조회
3. BSCScan API 호출
4. 고액 거래 필터링
5. 웹 스크래핑
6. 데이터베이스 저장 구조

### 개별 테스트

```bash
# 특정 테스트만 실행 (1-6)
python scripts/test_bsc_hybrid.py --test 3  # API 테스트만
```

---

## 고급 설정

### 고액 거래 기준

#### BNB 기준
```python
# 기본값
DEFAULT_MIN_BNB = 100  # ~$30,000

# 추천 설정
- 소규모: 100 BNB
- 중규모: 1,000 BNB (~$300,000)
- 대규모: 10,000 BNB (~$3,000,000)
```

#### USD 기준
```python
# 기본값
DEFAULT_MIN_USD = 50000  # $50,000

# 추천 설정
- 소규모: $50,000
- 중규모: $500,000
- 대규모: $5,000,000
```

### 체크포인트 관리

체크포인트 파일 위치: `checkpoints/bsc_hybrid_checkpoint.json`

```json
{
  "last_run": "2025-11-16T14:30:00",
  "processed_addresses": ["0x...", "0x..."],
  "high_value_txs_scraped": ["0x...", "0x..."],
  "total_collected": 50000,
  "total_scraped": 1000
}
```

#### 체크포인트 초기화

```bash
rm checkpoints/bsc_hybrid_checkpoint.json
```

### 백업 관리

백업 파일 위치: `data/backups/`

```
bsc_transactions_api_20251116_143000.csv       # API 수집 후
bsc_transactions_enriched_20251116_150000.csv  # 스크래핑 후
```

---

## whale_transactions 스키마

수집된 데이터는 다음 스키마로 저장됩니다:

```sql
CREATE TABLE whale_transactions (
    tx_hash TEXT PRIMARY KEY,
    block_number BIGINT NOT NULL,
    block_timestamp TIMESTAMPTZ NOT NULL,
    from_address TEXT NOT NULL,
    to_address TEXT,
    coin_symbol TEXT NOT NULL,
    chain VARCHAR(50) NOT NULL DEFAULT 'bsc',
    amount NUMERIC(78, 18) NOT NULL,
    amount_usd NUMERIC(20, 2),
    gas_used BIGINT,
    gas_price BIGINT,
    gas_fee_eth NUMERIC(78, 18),
    transaction_status TEXT NOT NULL,
    is_whale BOOLEAN NOT NULL DEFAULT TRUE,
    whale_category TEXT,
    input_data TEXT,              -- Method (웹 스크래핑)
    from_label VARCHAR(255),      -- From Label (웹 스크래핑)
    to_label VARCHAR(255),        -- To Label (웹 스크래핑)
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 트러블슈팅

### 1. API 호출 실패

**문제**: `❌ API 호출 실패: 403 Forbidden`

**해결**:
```bash
# ETHERSCAN_API_KEY 확인
echo $ETHERSCAN_API_KEY

# .env 파일 확인
cat config/.env | grep ETHERSCAN_API_KEY
```

### 2. Rate Limiting

**문제**: `⚠️ Rate limit 도달`

**해결**:
```bash
# 웹 스크래핑 간격 증가
python bsc_hybrid_collector.py --scraping-delay 5

# 또는 고액 거래 기준 상향
python bsc_hybrid_collector.py --min-bnb 1000
```

### 3. Supabase 연결 실패

**문제**: `❌ Supabase 연결 실패`

**해결**:
```bash
# 환경 변수 재로드
source config/.env

# 또는 직접 설정
export SUPABASE_URL="your_url"
export SUPABASE_SERVICE_ROLE_KEY="your_key"
```

### 4. 웹 스크래핑 차단

**문제**: `❌ 403 Forbidden` (웹 스크래핑 시)

**해결**:
- 대기 시간 증가: `--scraping-delay 10`
- IP 변경 (VPN 사용)
- API만 사용: `--skip-scraping`

### 5. 메모리 부족

**문제**: `MemoryError`

**해결**:
```bash
# 배치 크기 줄이기 (코드 수정 필요)
# 또는 주소를 나눠서 실행
python bsc_hybrid_collector.py --test  # 먼저 테스트
```

---

## 성능 최적화 팁

### 1. 웹 스크래핑 최소화

고액 거래 기준을 높여 스크래핑 건수 감소:

```bash
# 1,000 BNB 이상만 → 약 100건 → 5-10분 소요
python bsc_hybrid_collector.py --min-bnb 1000
```

### 2. 병렬 처리 (고급)

여러 프로세스로 주소를 분할 처리:

```bash
# 프로세스 1: 주소 1-50
# 프로세스 2: 주소 51-100
```

### 3. 체크포인트 활용

중단된 작업을 이어서 실행하면 시간 절약

---

## 예상 비용 및 시간

### 시나리오 1: 전체 수집 (100개 주소)

| 단계 | 시간 | 비용 |
|-----|------|------|
| API 수집 | 2-5분 | 무료 (API 제한 내) |
| 웹 스크래핑 (1,000건) | 33-40분 | 무료 |
| DB 저장 | 1분 | Supabase 무료 플랜 |
| **총계** | **45-50분** | **무료** |

### 시나리오 2: API만 (웹 스크래핑 제외)

| 단계 | 시간 | 비용 |
|-----|------|------|
| API 수집 | 2-5분 | 무료 |
| DB 저장 | 1분 | 무료 |
| **총계** | **3-6분** | **무료** |

### 시나리오 3: 고액만 스크래핑 (1,000 BNB 이상)

| 단계 | 시간 | 비용 |
|-----|------|------|
| API 수집 | 2-5분 | 무료 |
| 웹 스크래핑 (100건) | 3-5분 | 무료 |
| DB 저장 | 1분 | 무료 |
| **총계** | **6-11분** | **무료** |

---

## 추가 리소스

### 관련 문서
- [BSCScan API 문서](https://docs.bscscan.com/)
- [Supabase 문서](https://supabase.com/docs)
- [프로젝트 ERD](../../../../docs/architecture/ERD.md)

### 관련 스크립트
- `collect_all_whale_transactions.py` - 멀티체인 수집
- `collect_bnb_usdc_xrp_transactions_2025_may_june.py` - 날짜 범위 수집

### 문의 및 지원
- GitHub Issues
- 프로젝트 문서: `/docs`

---

## 라이선스

이 시스템은 프로젝트 라이선스를 따릅니다.

**주의사항**:
- BSCScan의 웹 스크래핑은 ToS 위반 가능성이 있습니다
- 상업적 사용 시 BSCScan Pro API 사용 권장
- Rate limiting을 준수하세요




