# 데이터 수집 재개 가이드

## 📊 현재 진행 상황

### price_history (1시간 단위 가격 데이터)
- **진행 상태**: 10/10 코인 진행 중
- **최신 타임스탬프**: 대부분 2025-11-16 04:00 UTC
- **예외**: SOL, DOT는 2025-11-08 22:00 UTC까지 수집됨

### BTC 고래 거래 데이터
- **진행 상태**: 283/300 주소 진행 중
- **미수집 주소**: 17개 (not_started 상태)

### BSC 고래 거래 데이터 (신규 추가)
- **총 주소**: 100개
- **진행 상태**: 미시작
- **수집 방식**: API + 고액 거래 웹 스크래핑

## 🚀 병렬 수집 (권장)

### 1. 환경 검증
```bash
python3 scripts/pre_collection_check.py
```

모든 검증 항목이 통과되었는지 확인하세요.

### 2. 병렬 수집 시작
```bash
python3 run_parallel_collection.py
```

**3개 작업을 동시에 실행합니다:**
- 📊 가격 데이터 (재개 모드)
- 🐋 BTC 고래 거래 (재개 모드)
- 🟡 BSC 고래 거래 (전체 수집, 고액만 스크래핑)

**예상 소요 시간**: 약 60분 (가장 긴 작업 기준)

**모니터링**:
- 10분마다 자동으로 진행 상황 출력
- 개별 로그 파일: `logs/` 디렉토리

**안전 종료**:
- `Ctrl+C`를 누르면 모든 프로세스가 정상 종료되고 체크포인트 저장

## 🔄 개별 수집 (선택)

개별적으로 실행하려면:

### 1. 가격 데이터 수집 재개
```bash
python3 collect_price_history_hourly.py --resume
```

### 2. BTC 고래 거래 데이터 수집 재개
```bash
python3 collect_btc_whale_transactions.py --resume
```

### 3. BSC 고래 거래 데이터 수집 (신규)
```bash
# 고액 거래만 스크래핑 (권장)
python3 scripts/collectors/bsc_hybrid_collector.py --min-bnb 1000

# API만 사용 (빠름)
python3 scripts/collectors/bsc_hybrid_collector.py --skip-scraping

# 테스트 모드 (3개 주소만)
python3 scripts/collectors/bsc_hybrid_collector.py --test
```

### 4. 체크포인트 수동 저장
```bash
python3 scripts/save_collection_checkpoint.py
```

## 📋 체크포인트 파일

### 통합 체크포인트
- **위치**: `collection_checkpoint.json`
- **내용**: 
  - `price_history`: 코인별 최신 타임스탬프
  - `btc_whale_transactions`: BTC 주소별 최신 타임스탬프
  - `bsc_whale_transactions`: BSC 주소별 최신 타임스탬프 (신규)

### BSC 하이브리드 체크포인트
- **위치**: `checkpoints/bsc_hybrid_checkpoint.json`
- **내용**: BSC 수집 상세 정보 (처리된 주소, 스크래핑된 거래 등)

### 자동 저장
- 수집 완료 시
- Ctrl+C로 중단 시
- 오류 발생 시

## 📊 진행률 확인

### 실시간 모니터링
```bash
python3 scripts/monitor_collection_progress.py
```

10분마다 다음 정보를 출력합니다:
- 📊 price_history: 10/10 코인 (95.5%)
- 🐋 BTC whale: 283/300 주소 (94.3%)
- 🟡 BSC whale: 45/100 주소 (45.0%)

### 데이터 검증
```bash
python3 scripts/verify_data_collection_2025.py
```

수집된 데이터의 완전성을 검증하고 리포트를 생성합니다.

## ⚠️ 주의사항

1. **재개 모드**: `--resume` 옵션은 체크포인트에서 마지막 수집 지점부터 재개
2. **체크포인트 없음**: 체크포인트가 없으면 처음부터 시작
3. **자동 저장**: 중단 시 자동으로 체크포인트 저장
4. **병렬 실행**: 리소스 사용량이 높을 수 있음 (CPU, 메모리, 네트워크)
5. **API 제한**: Binance, Etherscan, Blockstream API의 rate limit 주의

## 🔧 문제 해결

### 패키지 설치 오류
```bash
pip install beautifulsoup4 lxml
```

### API 키 오류
```bash
# .env 파일 확인
cat config/.env | grep ETHERSCAN_API_KEY
```

### Supabase 연결 오류
```bash
# 연결 테스트
python3 scripts/pre_collection_check.py
```

### 로그 확인
```bash
# 병렬 실행 로그
ls -la logs/

# 특정 로그 보기
tail -f logs/price_history_*.log
tail -f logs/btc_whale_*.log
tail -f logs/bsc_whale_*.log
```

## 📖 관련 문서

- [BSC Hybrid Collection Guide](BSC_HYBRID_COLLECTION_GUIDE.md) - BSC 수집 상세 가이드
- [BSC Quick Start](BSC_HYBRID_QUICK_START.md) - BSC 빠른 시작 가이드
- [Timezone Standard](../../../../docs/architecture/timezone_standard.md) - 타임존 표준
- [Data Collection Summary](../../../../docs/archive/analysis/data_collection_2025_summary.md) - 작업 요약

