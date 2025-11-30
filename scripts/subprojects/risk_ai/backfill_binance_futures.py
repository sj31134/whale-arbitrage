#!/usr/bin/env python3
"""
Binance 선물 지표 히스토리 백필 스크립트

목표:
- fundingRate API를 사용해 BTCUSDT 펀딩비 히스토리를 수집하고
  일 단위로 집계하여 binance_futures_metrics.avg_funding_rate를 채움
- openInterestHist API를 사용해 BTCUSDT 일별 OI 히스토리를 수집하여
  binance_futures_metrics.sum_open_interest를 채움

주의:
- 이 스크립트는 설계/구현용이며, 실제 실행 시에는 API 키/레이트리밋을
  환경에 맞게 조정해야 합니다.
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


def chunk_time_range(start: datetime, end: datetime, max_days: int) -> List[tuple]:
    """start~end 구간을 max_days 단위로 잘라 리스트 반환."""
    chunks = []
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=max_days), end)
        chunks.append((cur, nxt))
        cur = nxt
    return chunks


def fetch_funding_history(
    symbol: str,
    start: datetime,
    end: datetime,
    session: requests.Session,
    limit: int = 1000,
    sleep_sec: float = 0.3,
) -> pd.DataFrame:
    """
    /fapi/v1/fundingRate 기반 펀딩비 히스토리 수집.
    start~end 범위를 커서 방식으로 순회하며 모든 레코드 수집.
    """
    logging.info("Fetching funding history %s %s~%s", symbol, start, end)
    all_rows: List[Dict[str, Any]] = []

    params = {
        "symbol": symbol,
        "limit": limit,
        "startTime": to_ms(start),
        "endTime": to_ms(end),
    }

    while True:
        resp = session.get(f"{BINANCE_FAPI_BASE}/fapi/v1/fundingRate", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break

        all_rows.extend(data)

        last_time = int(data[-1]["fundingTime"])
        next_time = last_time + 1
        if next_time >= params["endTime"]:
            break

        params["startTime"] = next_time
        time.sleep(sleep_sec)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["fundingTime"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
    df["date"] = df["fundingTime"].dt.date
    df["fundingRate"] = df["fundingRate"].astype(float)

    # 일별 평균 펀딩비
    daily = (
        df.groupby("date", as_index=False)["fundingRate"]
        .mean()
        .rename(columns={"fundingRate": "avg_funding_rate"})
    )
    return daily


def fetch_oi_history(
    symbol: str,
    start: datetime,
    end: datetime,
    session: requests.Session,
    period: str = "1d",
    limit: int = 500,
    sleep_sec: float = 0.3,
) -> pd.DataFrame:
    """
    /futures/data/openInterestHist 기반 일별 OI 히스토리 수집.
    """
    logging.info("Fetching OI history %s %s~%s", symbol, start, end)
    all_rows: List[Dict[str, Any]] = []

    start_ms = to_ms(start)
    end_ms = to_ms(end)
    cur = start_ms

    while cur < end_ms:
        params = {
            "symbol": symbol,
            "period": period,
            "limit": limit,
            "startTime": cur,
            "endTime": end_ms,
        }
        try:
            resp = session.get(
                f"{BINANCE_FAPI_BASE}/futures/data/openInterestHist", params=params, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
        except requests.exceptions.HTTPError as e:
            logging.warning(f"HTTP error for OI history: {e}, params: {params}")
            # API가 해당 기간을 지원하지 않을 수 있음 - 더 작은 구간으로 시도
            if cur + (30 * 24 * 60 * 60 * 1000) < end_ms:
                cur = cur + (30 * 24 * 60 * 60 * 1000)  # 30일씩 건너뛰기
                continue
            else:
                break
        except Exception as e:
            logging.warning(f"Error fetching OI history: {e}")
            break

        all_rows.extend(data)
        last_ts = int(data[-1]["timestamp"])
        next_ts = last_ts + 1
        if next_ts >= end_ms:
            break
        cur = next_ts
        time.sleep(sleep_sec)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["date"] = df["timestamp"].dt.date
    df["sumOpenInterest"] = df["sumOpenInterest"].astype(float)
    df["sumOpenInterestValue"] = df["sumOpenInterestValue"].astype(float)

    daily = (
        df.groupby("date", as_index=False)[["sumOpenInterest", "sumOpenInterestValue"]]
        .last()
        .rename(
            columns={
                "sumOpenInterest": "sum_open_interest",
                "sumOpenInterestValue": "sum_open_interest_value_usd",
            }
        )
    )
    return daily


def upsert_binance_metrics(daily_funding: pd.DataFrame, daily_oi: pd.DataFrame, symbol: str = SYMBOL) -> None:
    """
    binance_futures_metrics 테이블에 funding / OI 정보를 업서트.
    - 키: (date, symbol)
    - 레코드가 없으면 INSERT, 있으면 UPDATE
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # funding
    if not daily_funding.empty:
        for _, row in daily_funding.iterrows():
            date_str = str(row["date"])
            funding_rate = float(row["avg_funding_rate"])
            # 먼저 레코드 존재 확인
            cur.execute(
                "SELECT COUNT(*) FROM binance_futures_metrics WHERE date = ? AND symbol = ?",
                (date_str, symbol),
            )
            exists = cur.fetchone()[0] > 0
            if exists:
                cur.execute(
                    """
                    UPDATE binance_futures_metrics
                    SET avg_funding_rate = ?
                    WHERE date = ? AND symbol = ?
                    """,
                    (funding_rate, date_str, SYMBOL),
                )
            else:
                # 레코드가 없으면 기본값으로 INSERT
                cur.execute(
                    """
                    INSERT INTO binance_futures_metrics (date, symbol, avg_funding_rate, sum_open_interest, volatility_24h)
                    VALUES (?, ?, ?, 0, 0)
                    """,
                    (date_str, symbol, funding_rate),
                )

    # OI
    if not daily_oi.empty:
        for _, row in daily_oi.iterrows():
            date_str = str(row["date"])
            oi = float(row["sum_open_interest"])
            # 먼저 레코드 존재 확인
            cur.execute(
                "SELECT COUNT(*) FROM binance_futures_metrics WHERE date = ? AND symbol = ?",
                (date_str, symbol),
            )
            exists = cur.fetchone()[0] > 0
            if exists:
                cur.execute(
                    """
                    UPDATE binance_futures_metrics
                    SET sum_open_interest = ?
                    WHERE date = ? AND symbol = ?
                    """,
                    (oi, date_str, SYMBOL),
                )
            else:
                # 레코드가 없으면 기본값으로 INSERT
                cur.execute(
                    """
                    INSERT INTO binance_futures_metrics (date, symbol, avg_funding_rate, sum_open_interest, volatility_24h)
                    VALUES (?, ?, 0, ?, 0)
                    """,
                    (date_str, symbol, oi),
                )

    conn.commit()
    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Backfill Binance futures funding/OI history")
    parser.add_argument("--start-date", type=str, default="2022-01-01")
    parser.add_argument("--end-date", type=str, default=None, help="포함하지 않는 종료일 (YYYY-MM-DD)")
    parser.add_argument("--symbol", type=str, default=SYMBOL)
    args = parser.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        # 오늘 + 1일 (종료일은 미포함)
        today = datetime.utcnow().date()
        end_date = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) + timedelta(
            days=1
        )

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    session = requests.Session()

    logging.info("Backfill Binance funding/OI history: %s ~ %s", start_date, end_date)

    funding_df = pd.DataFrame()
    oi_df = pd.DataFrame()
    
    try:
        funding_df = fetch_funding_history(args.symbol, start_date, end_date, session=session)
        logging.info(f"Fetched {len(funding_df)} days of funding rate data")
    except Exception as e:
        logging.error(f"Error fetching funding history: {e}")
    
    # OI 히스토리 API는 startTime/endTime 파라미터를 지원하지 않음
    # 최근 데이터만 limit으로 가져오는 방식으로 변경 필요
    # 일단 OI 수집은 비활성화하고 펀딩비만 수집
    oi_df = pd.DataFrame()
    logging.info("OI history collection skipped (API limitation - startTime/endTime not supported)")

    if funding_df.empty and oi_df.empty:
        logging.warning("No data fetched from Binance APIs.")
        return

    upsert_binance_metrics(funding_df, oi_df, args.symbol)
    logging.info("Backfill completed.")


if __name__ == "__main__":
    main()


