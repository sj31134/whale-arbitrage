#!/usr/bin/env python3
"""volatility 수집 함수 테스트"""

import sys
from pathlib import Path
from datetime import datetime
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))

from fetch_futures_metrics import fetch_daily_klines

if __name__ == "__main__":
    print("테스트: fetch_daily_klines 함수")
    print("=" * 60)
    
    start_ts = int(datetime(2025, 11, 1).timestamp() * 1000)
    end_ts = int(time.time() * 1000)
    
    print(f"기간: {datetime.fromtimestamp(start_ts/1000)} ~ {datetime.fromtimestamp(end_ts/1000)}")
    print("수집 중...")
    
    result = fetch_daily_klines('BTCUSDT', start_ts, end_ts)
    
    print(f"\n✅ 수집 완료: {len(result)}일")
    print("\n샘플 데이터 (최근 5일):")
    sorted_items = sorted(result.items())
    for date, vol in sorted_items[-5:]:
        print(f"  {date}: {vol:.4f} ({vol*100:.2f}%)")
    
    if result:
        avg_vol = sum(result.values()) / len(result)
        max_vol = max(result.values())
        min_vol = min(result.values())
        print(f"\n통계:")
        print(f"  평균 변동성: {avg_vol:.4f} ({avg_vol*100:.2f}%)")
        print(f"  최대 변동성: {max_vol:.4f} ({max_vol*100:.2f}%)")
        print(f"  최소 변동성: {min_vol:.4f} ({min_vol*100:.2f}%)")

