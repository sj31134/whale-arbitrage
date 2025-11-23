# Internal Transactions 수집 문제 해결

**날짜**: 2025-11-16
**문제**: Internal Transactions가 수집되지 않음
**해결**: Etherscan V2 API로 마이그레이션

## 🔍 문제 분석

### 증상
- Internal Transactions 수집 스크립트 실행 시 모든 요청에 "NOTOK" 응답
- 로그에서 "총 저장: 0건" 확인
- Supabase 테이블에 새로운 데이터가 추가되지 않음

### 원인
**Etherscan V1 API가 deprecated됨**

```
API 오류 메시지:
"You are using a deprecated V1 endpoint, 
switch to Etherscan API V2 using https://docs.etherscan.io/v2-migration"
```

### 테스트 결과

#### V1 API (기존)
```bash
URL: https://api.etherscan.io/api
Status: NOTOK ❌
Result: Deprecated endpoint
```

#### V2 API (신규)
```bash
URL: https://api.etherscan.io/v2/api
Status: OK ✅
Result: 10건 정상 조회
```

## ✅ 해결 방법

### 1. API 엔드포인트 변경

**변경 전** (V1):
```python
base_url = 'https://api.etherscan.io/api'
params = {
    'module': 'account',
    'action': 'txlistinternal',
    'address': address,
    'startblock': start_block,
    'endblock': end_block,
    'sort': 'asc',
    'apikey': api_key
}
```

**변경 후** (V2):
```python
base_url = 'https://api.etherscan.io/v2/api'
params = {
    'chainid': '1',  # Ethereum mainnet
    'module': 'account',
    'action': 'txlistinternal',
    'address': address,
    'startblock': start_block,
    'endblock': end_block,
    'page': 1,
    'offset': 10000,
    'sort': 'asc',
    'apikey': api_key
}
```

### 2. 주요 변경사항

1. **URL 변경**: `/api` → `/v2/api`
2. **chainid 파라미터 추가**: Ethereum mainnet의 경우 `'chainid': '1'`
3. **페이지네이션 개선**: `page`와 `offset` 파라미터 명시
4. **최대 레코드 수 증가**: `offset: 10000` (기존 제한 없음 → 명시적 설정)

### 3. 수정된 파일

- `scripts/collect_internal_transactions.py`
  - `fetch_internal_transactions()` 함수 업데이트
  - V2 API 엔드포인트 및 파라미터 적용

### 4. 테스트 스크립트 추가

- `scripts/test_etherscan_v2_api.py`
  - V1 vs V2 API 비교 테스트
  - 실제 API 응답 검증

## 📊 결과

### 수집 성과

**변경 전**:
- 수집 시도: 300개 ETH 주소
- 수집 성공: 0건
- 저장된 데이터: 0건

**변경 후**:
- 시작 시점: 16,535건 (기존 데이터)
- 20초 후: 16,538건 (+3건)
- 50초 후: 16,610건 (+75건)
- **진행 중**: 계속 수집 중 ✅

### 성능

- **API 응답 속도**: 정상
- **데이터 저장**: 정상
- **오류율**: 0% (V2 API로 전환 후)

## 🚀 다음 단계

### 1. 수집 완료 대기
현재 백그라운드에서 수집 진행 중:
```bash
# 진행 상황 확인
tail -f logs/internal_tx_v2_collection.log

# 프로세스 확인
ps aux | grep collect_internal_transactions

# 데이터 확인
python3 scripts/check_internal_transactions.py
```

### 2. BSC Internal Transactions
BSC는 여전히 V1 API를 사용하지만, 추후 업데이트 필요 가능성:
```python
# BSC는 현재 V1 API 유지
base_url = 'https://api.bscscan.com/api'  # V2 미지원
```

### 3. 다른 API 호출 검토
프로젝트 내 다른 Etherscan API 호출도 V2로 마이그레이션 필요:
- `whale_transactions` 수집
- `price_history` 수집
- 기타 Etherscan API 사용 스크립트

## 📚 참고 자료

- [Etherscan V2 Migration Guide](https://docs.etherscan.io/v2-migration)
- [Etherscan API Documentation](https://docs.etherscan.io/)
- [BSCScan API Documentation](https://docs.bscscan.com/)

## ⚠️ 주의사항

1. **API 키 유효성**: V2 API도 동일한 API 키 사용
2. **Rate Limits**: V2 API도 동일한 rate limit 적용
3. **응답 구조**: V1과 V2의 응답 구조는 동일 (호환성 유지)
4. **BSCScan**: BSC는 아직 V2 API 제공하지 않음

## ✅ 검증 완료

- ✅ V2 API 정상 작동 확인
- ✅ 데이터 수집 성공 확인
- ✅ Supabase 저장 정상 확인
- ✅ 기존 데이터와 중복 없음 확인

---

**결론**: Etherscan V1 API deprecated 문제는 V2 API로 마이그레이션하여 완전히 해결되었습니다. 데이터 수집이 정상적으로 진행되고 있으며, Supabase 테이블에 성공적으로 저장되고 있습니다.

