# BSC Hybrid Collection System - 빠른 시작 가이드

## ⚡ 5분 안에 시작하기

### 1. 설치

```bash
# 프로젝트 루트에서
pip install beautifulsoup4>=4.9.0 lxml>=4.6.0
```

### 2. 환경 변수 확인

```bash
# .env 파일이 설정되어 있는지 확인
cat config/.env | grep -E "SUPABASE|ETHERSCAN"
```

필요한 변수:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ETHERSCAN_API_KEY`

### 3. 검증 테스트

```bash
# 모든 컴포넌트가 작동하는지 확인
python scripts/test_bsc_hybrid.py
```

### 4. 테스트 실행

```bash
# 처음 3개 주소만 처리 (약 1-2분 소요)
python scripts/collectors/bsc_hybrid_collector.py --test
```

### 5. 전체 실행

```bash
# 모든 BSC 주소 처리 (약 45-50분 소요)
python scripts/collectors/bsc_hybrid_collector.py
```

---

## 🎯 주요 옵션

### API만 사용 (빠른 수집)

```bash
# 웹 스크래핑 없이 약 3-6분
python scripts/collectors/bsc_hybrid_collector.py --skip-scraping
```

### 고액 거래만 스크래핑 (권장)

```bash
# 1,000 BNB 이상만 스크래핑 (약 10분)
python scripts/collectors/bsc_hybrid_collector.py --min-bnb 1000
```

### 저장 없이 수집만

```bash
# 백업 CSV만 저장, DB는 건너뛰기
python scripts/collectors/bsc_hybrid_collector.py --no-save
```

---

## 📊 실행 결과 확인

### 백업 파일

```bash
ls -lh data/backups/bsc_transactions_*.csv
```

### 체크포인트

```bash
cat checkpoints/bsc_hybrid_checkpoint.json
```

### Supabase 확인

```sql
-- whale_transactions 테이블 확인
SELECT 
    COUNT(*) as total_count,
    coin_symbol,
    chain
FROM whale_transactions
WHERE chain = 'bsc'
GROUP BY coin_symbol, chain;
```

---

## 🔧 문제 해결

### API 키 오류

```bash
# API 키가 설정되어 있는지 확인
python -c "import os; from dotenv import load_dotenv; load_dotenv('config/.env'); print('API Key:', os.getenv('ETHERSCAN_API_KEY')[:10] + '...')"
```

### Supabase 연결 오류

```bash
# Supabase 연결 테스트
python scripts/test_bsc_hybrid.py --test 1
```

### Rate Limiting

```bash
# 대기 시간 증가
python scripts/collectors/bsc_hybrid_collector.py --scraping-delay 5
```

---

## 📖 자세한 내용

전체 가이드: [BSC_HYBRID_COLLECTION_GUIDE.md](./BSC_HYBRID_COLLECTION_GUIDE.md)

---

## 💡 팁

1. **처음에는 테스트 모드로**: `--test` 옵션으로 먼저 테스트
2. **API만 사용 권장**: 웹 스크래핑은 시간이 오래 걸립니다
3. **고액 거래 기준 조정**: 필요한 만큼만 스크래핑
4. **체크포인트 활용**: 중단되어도 이어서 실행 가능
5. **백업 확인**: CSV 파일을 항상 확인하세요

---

## ✅ 체크리스트

- [ ] Python 패키지 설치 완료
- [ ] 환경 변수 설정 완료
- [ ] 검증 테스트 통과
- [ ] 테스트 모드 실행 성공
- [ ] 전체 실행 준비 완료

**모든 체크가 완료되면 전체 실행을 시작하세요!**

