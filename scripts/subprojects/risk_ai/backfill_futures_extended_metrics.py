#!/usr/bin/env python3
"""
Binance 선물 확장 지표 히스토리 백필 스크립트

대상 지표 (futures_extended_metrics):
- long_short_ratio
- long_account_pct, short_account_pct
- taker_buy_sell_ratio, taker_buy_vol, taker_sell_vol
- top_trader_long_short_ratio

주의:
- 설계 및 구현용 스크립트이며, 실제 실행 시 레이트리밋 및 API 키 정책을
  운영 환경에 맞게 조정해야 합니다.
"""

import argparse
import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"
BINANCE_FAPI_BASE = "https://fapi.binance.com"

SYMBOL = "BTCUSDT"


def to_ms(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def from_ms(ts: int) -> datetime:
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)


def fetch_global_long_short(
    symbol: str,
    start: datetime,
    end: datetime,
    session: requests.Session,
    period: str = "1d",
    limit: int = 500,
    sleep_sec: float = 0.3,
) -> pd.DataFrame:
    """
    /futures/data/globalLongShortAccountRatio 기반 글로벌 롱/숏 비율 히스토리 수집.
    Note: Binance API는 startTime/endTime을 지원하지 않으므로 limit만 사용하여 최근 데이터 수집.
    """
    logging.info("Fetching global long/short ratio %s (limit=%d)", symbol, limit)
    all_rows: List[Dict[str, Any]] = []

    # startTime/endTime 없이 limit만 사용
    params = {
        "symbol": symbol,
        "period": period,
        "limit": limit,
    }
    try:
        resp = session.get(
            f"{BINANCE_FAPI_BASE}/futures/data/globalLongShortAccountRatio",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            all_rows.extend(data)
            time.sleep(sleep_sec)
    except Exception as e:
        logging.warning(f"Error fetching global long/short ratio: {e}")

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["date"] = df["timestamp"].dt.date
    df["longShortRatio"] = df["longShortRatio"].astype(float)
    df["longAccount"] = df["longAccount"].astype(float)
    df["shortAccount"] = df["shortAccount"].astype(float)

    daily = (
        df.groupby("date", as_index=False)[["longShortRatio", "longAccount", "shortAccount"]]
        .last()
        .rename(
            columns={
                "longShortRatio": "long_short_ratio",
                "longAccount": "long_account_pct",
                "shortAccount": "short_account_pct",
            }
        )
    )
    return daily


def fetch_taker_ratio(
    symbol: str,
    start: datetime,
    end: datetime,
    session: requests.Session,
    period: str = "1d",
    limit: int = 500,
    sleep_sec: float = 0.3,
) -> pd.DataFrame:
    """
    /futures/data/takerlongshortRatio 기반 Taker 매수/매도 비율 및 거래량 히스토리 수집.
    Note: Binance API는 startTime/endTime을 지원하지 않으므로 limit만 사용하여 최근 데이터 수집.
    """
    logging.info("Fetching taker long/short ratio %s (limit=%d)", symbol, limit)
    all_rows: List[Dict[str, Any]] = []

    params = {
        "symbol": symbol,
        "period": period,
        "limit": limit,
    }
    try:
        resp = session.get(
            f"{BINANCE_FAPI_BASE}/futures/data/takerlongshortRatio",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            all_rows.extend(data)
            time.sleep(sleep_sec)
    except Exception as e:
        logging.warning(f"Error fetching taker ratio: {e}")

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["date"] = df["timestamp"].dt.date
    df["buyVol"] = df["buyVol"].astype(float)
    df["sellVol"] = df["sellVol"].astype(float)
    df["buySellRatio"] = df["buySellRatio"].astype(float)

    daily = (
        df.groupby("date", as_index=False)[["buyVol", "sellVol", "buySellRatio"]]
        .agg({
            "buyVol": "sum",
            "sellVol": "sum",
            "buySellRatio": "mean"
        })
        .rename(
            columns={
                "buyVol": "taker_buy_vol",
                "sellVol": "taker_sell_vol",
                "buySellRatio": "taker_buy_sell_ratio",
            }
        )
    )
    return daily


def fetch_top_trader_ratio(
    symbol: str,
    start: datetime,
    end: datetime,
    session: requests.Session,
    period: str = "1d",
    limit: int = 500,
    sleep_sec: float = 0.3,
) -> pd.DataFrame:
    """
    /futures/data/topLongShortPositionRatio 기반 탑 트레이더 포지션 롱/숏 비율 히스토리 수집.
    """
    logging.info("Fetching top trader long/short ratio %s (limit=%d)", symbol, limit)
    all_rows: List[Dict[str, Any]] = []

    params = {
        "symbol": symbol,
        "period": period,
        "limit": limit,
    }
    try:
        resp = session.get(
            f"{BINANCE_FAPI_BASE}/futures/data/topLongShortPositionRatio",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            all_rows.extend(data)
            time.sleep(sleep_sec)
    except Exception as e:
        logging.warning(f"Error fetching top trader ratio: {e}")

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["date"] = df["timestamp"].dt.date
    df["longShortRatio"] = df["longShortRatio"].astype(float)

    daily = (
        df.groupby("date", as_index=False)[["longShortRatio"]]
        .last()
        .rename(columns={"longShortRatio": "top_trader_long_short_ratio"})
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


def upsert_extended_metrics(df: pd.DataFrame, symbol: str = SYMBOL) -> None:
    """
    futures_extended_metrics 테이블에 date, symbol 기준으로 업서트.
    """
    if df.empty:
        logging.warning("No extended metrics to upsert.")
        return

    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    rows = [
        (
            str(row["date"]),
            symbol,
            float(row.get("long_short_ratio", 0) or 0),
            float(row.get("long_account_pct", 0) or 0),
            float(row.get("short_account_pct", 0) or 0),
            float(row.get("taker_buy_sell_ratio", 0) or 0),
            float(row.get("taker_buy_vol", 0) or 0),
            float(row.get("taker_sell_vol", 0) or 0),
            float(row.get("top_trader_long_short_ratio", 0) or 0),
        )
        for _, row in df.iterrows()
    ]

    cur.executemany(
        """
        INSERT OR REPLACE INTO futures_extended_metrics
        (date, symbol, long_short_ratio, long_account_pct, short_account_pct,
         taker_buy_sell_ratio, taker_buy_vol, taker_sell_vol,
         top_trader_long_short_ratio, bybit_funding_rate, bybit_oi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 
                COALESCE((SELECT bybit_funding_rate FROM futures_extended_metrics fe
                          WHERE fe.date = ? AND fe.symbol = ?), 0),
                COALESCE((SELECT bybit_oi FROM futures_extended_metrics fe
                          WHERE fe.date = ? AND fe.symbol = ?), 0)
        )
        """,
        [
            (
                d,
                s,
                lsr,
                la,
                sa,
                tr,
                tb,
                ts,
                tt,
                d,
                s,
                d,
                s,
            )
            for (d, s, lsr, la, sa, tr, tb, ts, tt) in rows
        ],
    )

    conn.commit()
    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Backfill Binance extended futures metrics history")
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

    logging.info("Backfill Binance extended metrics: %s ~ %s", start_date, end_date)

    gls = fetch_global_long_short(args.symbol, start_date, end_date, session=session)
    taker = fetch_taker_ratio(args.symbol, start_date, end_date, session=session)
    top = fetch_top_trader_ratio(args.symbol, start_date, end_date, session=session)

    if gls.empty and taker.empty and top.empty:
        logging.warning("No extended metrics fetched.")
        return

    # 날짜 기준 병합
    df = gls
    for extra in [taker, top]:
        if not extra.empty:
            if df.empty:
                df = extra
            else:
                df = pd.merge(df, extra, on="date", how="outer")

    upsert_extended_metrics(df, args.symbol)
    logging.info("Extended metrics backfill completed.")


if __name__ == "__main__":
    main()


