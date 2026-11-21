#!/usr/bin/env bash
# 오늘까지 데이터 수집·업데이트 (한 번에 실행)
# 사용법: ./scripts/run_data_update_to_today.sh
# 또는:   ./scripts/run_data_update_to_today.sh 2026-02-06  (종료일 지정)

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
END_DATE="${1:-$(date +%Y-%m-%d)}"

echo "=============================================="
echo "데이터 수집·업데이트 (종료일: $END_DATE)"
echo "=============================================="

if [ ! -d "venv" ]; then
  echo "venv가 없습니다. 먼저 python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi
source venv/bin/activate

echo ""
echo "[1/8] Spot 시세 (Upbit/Binance/Bitget/Bybit)..."
python scripts/subprojects/arbitrage/fetch_spot_quotes.py --end-date "$END_DATE"

echo ""
echo "[2/8] 환율 (exchange_rate)..."
python scripts/subprojects/arbitrage/fetch_exchange_rate.py --end-date "$END_DATE"

echo ""
echo "[3/8] 선물 지표 (futures_metrics + extended, 구간별 수집)..."
./scripts/subprojects/risk_ai/fetch_futures_metrics_to_date.sh "$END_DATE" || python scripts/subprojects/risk_ai/fetch_futures_metrics.py --start-date 2025-12-01 --end-date "$END_DATE"

echo ""
echo "[4/8] 주봉 OHLCV + 선물 주봉 집계..."
python scripts/subprojects/risk_ai/fetch_weekly_ohlcv.py --end-date "$END_DATE"
python scripts/subprojects/risk_ai/aggregate_futures_weekly.py

echo ""
echo "[5/8] 고래 통계 (로컬 SQLite 기준: whale_daily/weekly, bitinfocharts 주별)..."
python scripts/subprojects/risk_ai/fetch_bitinfo_whale.py 2>/dev/null || true
python scripts/subprojects/risk_ai/update_whale_stats_until.py --end-date "$END_DATE" --coins BTC,ETH --local
python scripts/subprojects/risk_ai/aggregate_bitinfocharts_whale_weekly.py --end-date "$END_DATE"

echo ""
echo "[6/8] 누락 날짜 placeholder 보완..."
python scripts/maintenance/fill_missing_until_date.py --end-date "$END_DATE"

echo ""
echo "=============================================="
echo "완료: $END_DATE 까지 데이터 업데이트됨"
echo "=============================================="
