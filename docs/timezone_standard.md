# 타임존 기준 명세서

## 1. API 타임존 기준

### 바이낸스 API
- **기준**: UTC (Coordinated Universal Time)
- **확인 방법**: 서버 시간과 UTC 시간 비교 결과 일치
- **K-line 데이터**: 모든 타임스탬프는 UTC 기준
- **예시**: 
  - Open Time: `2025-11-16 03:00:00 UTC` = `2025-11-16 12:00:00 KST`

### 블록체인 API (Blockstream, Etherscan 등)
- **기준**: UTC (블록체인 표준)
- **확인 방법**: 블록 타임스탬프와 UTC 시간 비교 결과 일치
- **모든 블록체인**: UTC 기준 타임스탬프 사용
- **예시**:
  - Block Timestamp: `2025-11-16 03:41:04 UTC` = `2025-11-16 12:41:04 KST`

## 2. 데이터베이스 저장 기준

### price_history 테이블
- **저장 기준**: UTC
- **저장 형식**: ISO 8601 형식, 타임존 정보 포함
- **예시**: `2025-11-08T22:00:00+00:00`
- **확인**: 최근 데이터 모두 `+00:00` (UTC) 포함

### whale_transactions 테이블
- **저장 기준**: UTC (권장)
- **현재 상태**: 
  - 일부 데이터가 "2025.9.30 14:09" 형식으로 저장됨 (타임존 정보 없음)
  - UTC로 파싱하여 처리 중
- **권장 형식**: ISO 8601 형식, 타임존 정보 포함
- **예시**: `2025-09-30T14:09:00+00:00`

## 3. 시간 단위 기준

### 가격 데이터 (price_history)
- **수집 간격**: 1시간 (1h)
- **시간 기준**: UTC
- **K-line 시작 시간**: 정시 (00분)
- **예시**:
  - UTC 00:00 = KST 09:00
  - UTC 01:00 = KST 10:00
  - UTC 23:00 = KST 08:00 (다음날)

### 고래 거래 데이터 (whale_transactions)
- **시간 기준**: UTC (블록 타임스탬프 기준)
- **정밀도**: 블록 생성 시간 (초 단위)
- **예시**:
  - Block Timestamp: `2025-09-30 14:09:00 UTC` = `2025-09-30 23:09:00 KST`

## 4. 9시 기준 데이터 수집

### 현재 상황
- price_history에 9시 기준 데이터가 명확하지 않음
- 다양한 시간대에 수집되고 있음

### 권장 사항
- **KST 9시 = UTC 0시**에 해당하는 데이터를 수집
- 또는 UTC 0시 기준으로 수집 (KST 9시에 해당)
- 1시간 단위 수집 시 UTC 0시 데이터가 KST 9시 데이터

### 예시
```
UTC 0시 (2025-01-01 00:00:00 UTC) = KST 9시 (2025-01-01 09:00:00 KST)
UTC 1시 (2025-01-01 01:00:00 UTC) = KST 10시 (2025-01-01 10:00:00 KST)
...
UTC 23시 (2025-01-01 23:00:00 UTC) = KST 8시 (2025-01-02 08:00:00 KST)
```

## 5. 코드 구현 기준

### 타임스탬프 생성
```python
from datetime import datetime, timezone

# Unix timestamp를 UTC datetime으로 변환
dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)

# ISO 형식으로 저장 (타임존 정보 포함)
dt.isoformat()  # '2025-01-01T00:00:00+00:00'
```

### 타임스탬프 저장
```python
# ✅ 올바른 방법
record = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    # 또는
    'timestamp': datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
}

# ❌ 잘못된 방법 (타임존 정보 없음)
record = {
    'timestamp': datetime.now().isoformat(),  # 타임존 정보 없음
    'timestamp': '2025.1.1 9:00'  # 형식 불일치
}
```

### 타임스탬프 조회 및 변환
```python
# UTC로 파싱
dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))

# KST로 변환 (표시용)
kst_dt = dt.astimezone(timezone(timedelta(hours=9)))
```

## 6. 검증 방법

### 타임존 확인 스크립트
```bash
# 상세 타임존 확인
python3 scripts/verify_timezone_detailed.py

# price_history 타임존 확인
python3 scripts/check_timezone_price_history.py

# whale_transactions 타임존 확인
python3 scripts/check_timezone_whale_transactions.py
```

## 7. 최종 결론

### 시간 기준
- **모든 API**: UTC 기준
- **데이터베이스 저장**: UTC 기준
- **표시**: 필요시 KST로 변환

### 시간 단위
- **가격 데이터**: 1시간 단위 (UTC 정시)
- **고래 거래**: 블록 타임스탬프 기준 (초 단위)

### 9시 기준 데이터
- **KST 9시 = UTC 0시**
- 1시간 단위 수집 시 UTC 0시 데이터가 KST 9시 데이터에 해당
- UTC 0시 데이터를 조회하면 KST 9시 기준 데이터를 얻을 수 있음

## 8. 주의사항

1. **타임존 정보 항상 포함**: ISO 형식 사용 시 `+00:00` 포함
2. **UTC로 통일**: 모든 저장 데이터는 UTC 기준
3. **변환은 표시 시만**: 데이터베이스에는 UTC로 저장, 조회 시 필요하면 KST로 변환
4. **기존 데이터**: 일부 데이터가 타임존 정보 없이 저장되어 있으므로, 파싱 시 UTC로 가정

