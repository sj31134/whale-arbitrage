#!/usr/bin/env python3
"""
Bybit 선물 펀딩비 / OI 히스토리 백필 스크립트

대상 지표 (futures_extended_metrics):
- bybit_funding_rate
- bybit_oi

주의:
- 설계 및 구현용 스크립트이며, 실제 실행 시 레이트리밋 및 인증 파라미터를
  운영 환경에 맞게 조정해야 합니다.
"""

import argparse
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

BYBIT_BASE = "https://api.bybit.com"
SYMBOL = "BTCUSDT"


def to_iso(dt: datetime) -> str:
    # Bybit v5는 ISO8601 또는 ms 타임스탬프를 지원 (버전에 따라 상이)
    return dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_bybit_funding_history(
    symbol: str,
    start: datetime,
    end: datetime,
    session: requests.Session,
) -> pd.DataFrame:
    """
    /v5/market/funding/history 기반 Bybit 펀딩비 히스토리 수집.
    구현은 단순화된 예시이며, 실제 파라미터(categoty, cursor 등)는
    Bybit 최신 문서를 참고해야 함.
    """
    logging.info("Fetching Bybit funding history %s %s~%s", symbol, start, end)
    all_rows: List[Dict[str, Any]] = []

    cursor = None
    while True:
        params = {
            "category": "linear",
            "symbol": symbol,
            "startTime": int(start.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000),
        }
        if cursor:
            params["cursor"] = cursor

        resp = session.get(f"{BYBIT_BASE}/v5/market/funding/history", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result", {})
        rows = result.get("list", [])
        if not rows:
            break
        all_rows.extend(rows)

        cursor = result.get("nextPageCursor")
        if not cursor:
            break

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    # Bybit 응답 스키마: fundingRateTimestamp 사용
    df["fundingRate"] = df["fundingRate"].astype(float)
    # fundingRateTimestamp 또는 fundingTime 확인
    timestamp_col = "fundingRateTimestamp" if "fundingRateTimestamp" in df.columns else "fundingTime"
    df["time"] = pd.to_datetime(df[timestamp_col], unit="ms", utc=True)
    df["date"] = df["time"].dt.date

    daily = (
        df.groupby("date", as_index=False)["fundingRate"]
        .mean()
        .rename(columns={"fundingRate": "bybit_funding_rate"})
    )
    return daily


def fetch_bybit_oi_history(
    symbol: str,
    start: datetime,
    end: datetime,
    session: requests.Session,
) -> pd.DataFrame:
    """
    /v5/market/open-interest 기반 Bybit OI 히스토리 수집.
    시간 간격/파라미터는 단순화한 예시이며, 실제 구현 시 최신 문서를 참고해야 함.
    """
    logging.info("Fetching Bybit OI history %s %s~%s", symbol, start, end)
    all_rows: List[Dict[str, Any]] = []

    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=7), end)  # 1주 단위 슬라이스 (예시)
        params = {
            "category": "linear",
            "symbol": symbol,
            "intervalTime": "D",  # 일간 (예시)
            "startTime": int(cur.timestamp() * 1000),
            "endTime": int(nxt.timestamp() * 1000),
        }
        resp = session.get(f"{BYBIT_BASE}/v5/market/open-interest", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result", {})
        rows = result.get("list", [])
        if not rows:
            cur = nxt
            continue
        all_rows.extend(rows)
        cur = nxt

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    # 필드명/스키마는 Bybit 문서에 따라 조정
    df["openInterest"] = df["openInterest"].astype(float)
    df["time"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["date"] = df["time"].dt.date

    daily = (
        df.groupby("date", as_index=False)["openInterest"]
        .last()
        .rename(columns={"openInterest": "bybit_oi"})
    )
    return daily


def ensure_table():
    """futures_extended_metrics 테이블이 없으면 생성"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS futures_extended_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            symbol VARCHAR(20) NOT NULL,
            long_short_ratio DECIMAL(10, 6),
            long_account_pct DECIMAL(10, 6),
            short_account_pct DECIMAL(10, 6),
            taker_buy_sell_ratio DECIMAL(10, 6),
            taker_buy_vol DECIMAL(30, 8),
            taker_sell_vol DECIMAL(30, 8),
            top_trader_long_short_ratio DECIMAL(10, 6),
            bybit_funding_rate DECIMAL(20, 10),
            bybit_oi DECIMAL(30, 10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, symbol)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ext_metrics_date ON futures_extended_metrics(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ext_metrics_symbol ON futures_extended_metrics(symbol)")
    conn.commit()
    cur.close()
    conn.close()


def upsert_bybit_metrics(daily_funding: pd.DataFrame, daily_oi: pd.DataFrame) -> None:
    """
    futures_extended_metrics에 Bybit 지표 업서트.
    다른 Binance 확장 지표는 유지한 채 Bybit 컬럼만 갱신.
    """
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if not daily_funding.empty:
        rows = [(str(row["date"]), SYMBOL, float(row["bybit_funding_rate"])) for _, row in daily_funding.iterrows()]
        cur.executemany(
            """
            INSERT INTO futures_extended_metrics (date, symbol, bybit_funding_rate)
            VALUES (?, ?, ?)
            ON CONFLICT(date, symbol) DO UPDATE SET
                bybit_funding_rate = excluded.bybit_funding_rate
            """,
            rows,
        )

    if not daily_oi.empty:
        rows = [(str(row["date"]), SYMBOL, float(row["bybit_oi"])) for _, row in daily_oi.iterrows()]
        cur.executemany(
            """
            INSERT INTO futures_extended_metrics (date, symbol, bybit_oi)
            VALUES (?, ?, ?)
            ON CONFLICT(date, symbol) DO UPDATE SET
                bybit_oi = excluded.bybit_oi
            """,
            rows,
        )

    conn.commit()
    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Backfill Bybit funding/OI history into futures_extended_metrics")
    parser.add_argument("--start-date", type=str, default="2022-01-01")
    parser.add_argument("--end-date", type=str, default=None, help="포함하지 않는 종료일 (YYYY-MM-DD)")
    parser.add_argument("--symbol", type=str, default=SYMBOL)
    args = parser.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        today = datetime.utcnow().date()
        end_date = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) + timedelta(
            days=1
        )

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    session = requests.Session()

    logging.info("Backfill Bybit funding/OI: %s ~ %s", start_date, end_date)

    funding_df = fetch_bybit_funding_history(args.symbol, start_date, end_date, session=session)
    oi_df = fetch_bybit_oi_history(args.symbol, start_date, end_date, session=session)

    if funding_df.empty and oi_df.empty:
        logging.warning("No Bybit data fetched.")
        return

    upsert_bybit_metrics(funding_df, oi_df)
    logging.info("Bybit backfill completed.")


if __name__ == "__main__":
    main()


