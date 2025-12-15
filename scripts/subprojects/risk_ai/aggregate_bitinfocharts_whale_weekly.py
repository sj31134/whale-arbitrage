#!/usr/bin/env python3
"""
bitinfocharts_whale (일별) -> bitinfocharts_whale_weekly (주별, week_end_date=일요일) 집계 스크립트

스키마 (이미 존재):
- coin (TEXT) PK part
- week_end_date (TEXT) PK part
- avg_top100_richest_pct (REAL)
- avg_transaction_value_btc (REAL)
- whale_conc_change_7d (REAL)  # 주간 변화율(전주 대비)로 계산
"""

import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"


def week_end_sunday(d: pd.Timestamp) -> pd.Timestamp:
    # Monday=0 ... Sunday=6, so add (6 - weekday) days; Sunday stays same day.
    return d + pd.Timedelta(days=(6 - d.weekday()))


def aggregate(end_date_inclusive: str = None):
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT date, coin, top100_richest_pct, avg_transaction_value_btc FROM bitinfocharts_whale", conn)
    if df.empty:
        print("⚠️ bitinfocharts_whale 데이터가 없습니다.")
        conn.close()
        return

    df["date"] = pd.to_datetime(df["date"])
    if end_date_inclusive:
        end_dt = pd.to_datetime(end_date_inclusive)
        df = df[df["date"] <= end_dt]

    if df.empty:
        print("⚠️ 지정된 end-date까지의 데이터가 없습니다.")
        conn.close()
        return

    df["week_end_date"] = df["date"].apply(week_end_sunday).dt.date.astype(str)

    weekly = (
        df.groupby(["coin", "week_end_date"], as_index=False)
        .agg(
            avg_top100_richest_pct=("top100_richest_pct", "mean"),
            avg_transaction_value_btc=("avg_transaction_value_btc", "mean"),
        )
        .sort_values(["coin", "week_end_date"])
    )

    # 전주 대비 변화율(주간) - 컬럼명은 whale_conc_change_7d지만 주간 단위로 계산
    weekly["whale_conc_change_7d"] = weekly.groupby("coin")["avg_top100_richest_pct"].pct_change().fillna(0.0)

    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bitinfocharts_whale_weekly (
            coin TEXT NOT NULL,
            week_end_date TEXT NOT NULL,
            avg_top100_richest_pct REAL,
            avg_transaction_value_btc REAL,
            whale_conc_change_7d REAL,
            PRIMARY KEY (coin, week_end_date)
        )
        """
    )

    rows = [
        (
            r["coin"],
            r["week_end_date"],
            float(r["avg_top100_richest_pct"]) if pd.notna(r["avg_top100_richest_pct"]) else 0.0,
            float(r["avg_transaction_value_btc"]) if pd.notna(r["avg_transaction_value_btc"]) else 0.0,
            float(r["whale_conc_change_7d"]) if pd.notna(r["whale_conc_change_7d"]) else 0.0,
        )
        for _, r in weekly.iterrows()
    ]

    cur.executemany(
        """
        INSERT OR REPLACE INTO bitinfocharts_whale_weekly
        (coin, week_end_date, avg_top100_richest_pct, avg_transaction_value_btc, whale_conc_change_7d)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()

    # end_date_inclusive 이후 레코드는 제거(요청된 범위 고정)
    if end_date_inclusive:
        cur.execute("DELETE FROM bitinfocharts_whale_weekly WHERE week_end_date > ?", (end_date_inclusive,))
        conn.commit()

    # 결과 요약
    cur.execute("SELECT coin, MIN(week_end_date), MAX(week_end_date), COUNT(*) FROM bitinfocharts_whale_weekly GROUP BY coin ORDER BY coin")
    print("✅ bitinfocharts_whale_weekly 업데이트 완료:")
    for row in cur.fetchall():
        print(f" - {row[0]}: {row[1]} ~ {row[2]} ({row[3]}주)")

    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Aggregate bitinfocharts_whale to weekly table")
    parser.add_argument("--end-date", type=str, default=None, help="종료일(포함) (YYYY-MM-DD). 지정 시 그 이후 주차 레코드는 제거")
    args = parser.parse_args()
    aggregate(end_date_inclusive=args.end_date)


if __name__ == "__main__":
    main()


