# 타임존 분석 결과

## 1. price_history 테이블 타임존 분석

### 분석 방법
- 최근 100건의 데이터 샘플 조회
- 시간대별 분포 분석
- 9시 기준 데이터 확인

### 확인 사항
- **9시 기준 데이터**: UTC 0시 데이터가 많으면 KST 9시 기준, UTC 9시 데이터가 많으면 UTC 9시 기준
- **데이터 저장 형식**: TIMESTAMPTZ (PostgreSQL 타임존 포함 타임스탬프)

### 실행 방법
```bash
python scripts/check_timezone_price_history.py
```

### 예상 결과
- 바이낸스 API는 UTC 기준으로 데이터를 제공
- `collect_price_history_for_usdc_bnb_xrp.py`에서 `datetime.fromtimestamp()` 사용 시 timezone 정보 없이 저장될 수 있음
- ISO 형식으로 저장 시 타임존 정보 포함 여부 확인 필요

## 2. whale_transactions 테이블 타임존 분석

### 분석 방법
- 최근 100건의 데이터 샘플 조회
- 시간대별 분포 분석
- 체인별 시간대 분포 확인

### 확인 사항
- **블록체인 표준**: 모든 블록체인은 UTC 기준으로 타임스탬프 사용
- **데이터 저장 형식**: TIMESTAMPTZ
- **코드 확인**: `datetime.fromtimestamp()` 사용 시 timezone 처리 확인

### 실행 방법
```bash
python scripts/check_timezone_whale_transactions.py
```

### 예상 결과
- 블록체인 거래는 시간대와 무관하게 발생하므로 시간대가 고르게 분포되어야 함
- 특정 시간대에 집중되어 있지 않으면 UTC 기준으로 저장된 것으로 판단

## 3. 코드에서의 타임존 처리

### 현재 코드 분석

#### price_history 수집 코드
- `collect_price_history_for_usdc_bnb_xrp.py`:
  - `datetime.fromtimestamp(k[0] / 1000)`: timezone 정보 없음
  - `.isoformat()`: timezone 정보 없이 저장될 수 있음
  - **개선 필요**: UTC timezone 명시 필요

#### whale_transactions 수집 코드
- `collect_8coins_free_apis.py`:
  - `datetime.fromtimestamp(tx.get('status', {}).get('block_time', 0))`: timezone 정보 없음
  - **개선 필요**: UTC timezone 명시 필요

- `collect_bnb_usdc_xrp_transactions_2025_may_june.py`:
  - `datetime.fromtimestamp(timestamp, tz=timezone.utc)`: ✅ UTC 명시
  - `block_timestamp.replace(tzinfo=timezone.utc)`: ✅ UTC 명시

### 권장 사항

1. **모든 타임스탬프는 UTC로 명시적으로 저장**
   ```python
   from datetime import datetime, timezone
   
   # Unix timestamp를 UTC datetime으로 변환
   dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
   
   # ISO 형식으로 저장 (타임존 정보 포함)
   dt.isoformat()  # '2025-01-01T00:00:00+00:00'
   ```

2. **데이터베이스 저장 시 타임존 정보 포함**
   - TIMESTAMPTZ 타입 사용
   - ISO 형식 문자열에 타임존 정보 포함

3. **조회 시 타임존 변환**
   - 필요시 KST로 변환하여 표시
   - 데이터베이스에는 항상 UTC로 저장

## 4. 개선된 코드

### collect_price_history_hourly.py
- ✅ UTC timezone 명시적으로 설정
- ✅ `datetime.fromtimestamp(..., tz=timezone.utc)` 사용
- ✅ ISO 형식 저장 시 타임존 정보 포함

### collect_btc_whale_transactions.py
- ✅ UTC timezone 명시적으로 설정
- ✅ `datetime.fromtimestamp(..., tz=timezone.utc)` 사용
- ✅ ISO 형식 저장 시 타임존 정보 포함

## 5. 결론

### price_history
- **현재 상태**: 확인 필요 (스크립트 실행 후 결과 확인)
- **권장**: UTC 기준으로 저장 (바이낸스 API는 UTC 제공)

### whale_transactions
- **현재 상태**: 확인 필요 (스크립트 실행 후 결과 확인)
- **권장**: UTC 기준으로 저장 (블록체인 표준)

### 향후 작업
1. 타임존 확인 스크립트 실행
2. 결과에 따라 기존 코드 수정
3. 모든 수집 스크립트에 UTC timezone 명시

