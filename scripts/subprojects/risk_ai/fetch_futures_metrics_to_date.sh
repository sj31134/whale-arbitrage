#!/usr/bin/env bash
# 선물 지표를 종료일까지 구간별로 수집 (한 번에 하면 타임아웃 방지)
# 사용법: ./scripts/subprojects/risk_ai/fetch_futures_metrics_to_date.sh [YYYY-MM-DD]
# 미지정 시 오늘 날짜

set -e
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
END_DATE="${1:-$(date +%Y-%m-%d)}"

source venv/bin/activate 2>/dev/null || true

python3 - "$END_DATE" << 'PY'
import subprocess
import sys
from datetime import datetime, timedelta

end_s = sys.argv[1]
end_d = datetime.strptime(end_s, "%Y-%m-%d").date()
current = datetime(2025, 12, 15).date()
chunk_days = 10

while current <= end_d:
    chunk_end = min(current + timedelta(days=chunk_days - 1), end_d)
    c_str = current.strftime("%Y-%m-%d")
    e_str = chunk_end.strftime("%Y-%m-%d")
    print(f"  구간: {c_str} ~ {e_str}")
    r = subprocess.run(
        ["python", "scripts/subprojects/risk_ai/fetch_futures_metrics.py", "--start-date", c_str, "--end-date", e_str],
    )
    if r.returncode != 0:
        print(f"  (구간 실패: {c_str}~{e_str})")
    current = chunk_end + timedelta(days=1)
print("선물 주봉 집계...")
subprocess.run(["python", "scripts/subprojects/risk_ai/aggregate_futures_weekly.py"], check=False)
print("완료.")
PY
echo "선물 지표 수집·주봉 집계 끝."
