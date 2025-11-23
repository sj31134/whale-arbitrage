# 타임존 기준 요약

## 핵심 결론

### ✅ 모든 시간은 UTC 기준

1. **API**: 바이낸스, 블록체인 API 모두 UTC 기준
2. **데이터베이스**: UTC 기준으로 저장
3. **시간 단위**: 1시간 단위 수집 시 UTC 정시 기준

### 📅 9시 기준 데이터

- **KST 9시 = UTC 0시**
- UTC 0시 데이터를 조회하면 KST 9시 기준 데이터
- 1시간 단위 수집 시 UTC 0시 데이터가 KST 9시 데이터

### 💾 저장 형식

- **권장**: ISO 8601 형식, 타임존 정보 포함
- **예시**: `2025-01-01T00:00:00+00:00`
- **현재**: price_history는 올바르게 저장됨, whale_transactions는 일부 형식 불일치

### 🔧 코드 구현

```python
# ✅ 올바른 방법
from datetime import datetime, timezone

dt = datetime.fromtimestamp(ts, tz=timezone.utc)
timestamp_str = dt.isoformat()  # '2025-01-01T00:00:00+00:00'
```

### 📊 시간 단위 기준

- **가격 데이터**: UTC 정시 (00분) 기준 1시간 단위
- **고래 거래**: 블록 타임스탬프 기준 (초 단위)

