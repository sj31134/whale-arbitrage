import os
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "project.db"


def get_supabase():
    load_dotenv(ROOT / "config" / ".env", override=True)
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) 가 필요합니다.")
    return create_client(url, key)


def supabase_max_date(
    supabase, table: str, date_col: str = "date", eq_filters: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    q = supabase.table(table).select(date_col).order(date_col, desc=True).limit(1)
    if eq_filters:
        for k, v in eq_filters.items():
            q = q.eq(k, v)
    res = q.execute()
    if not res.data:
        return None
    return res.data[0].get(date_col)


def read_sqlite_new_rows(
    conn: sqlite3.Connection,
    table: str,
    date_col: str,
    min_exclusive_date: Optional[str],
    extra_where: Optional[str] = None,
    params: Tuple[Any, ...] = (),
) -> pd.DataFrame:
    where_parts: List[str] = []
    all_params: List[Any] = []

    if min_exclusive_date:
        where_parts.append(f"{date_col} > ?")
        all_params.append(min_exclusive_date)
    if extra_where:
        where_parts.append(f"({extra_where})")
        all_params.extend(list(params))

    where_sql = ""
    if where_parts:
        where_sql = " WHERE " + " AND ".join(where_parts)

    sql = f"SELECT * FROM {table}{where_sql} ORDER BY {date_col}"
    return pd.read_sql(sql, conn, params=tuple(all_params))


def clean_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    # Supabase(PostgREST) JSON 직렬화 에러 방지: NaN/Inf -> None
    df = df.where(pd.notnull(df), None)
    df = df.replace([float("inf"), float("-inf")], None)
    return df.to_dict(orient="records")


def upsert_batches(supabase, table: str, records: List[Dict[str, Any]], on_conflict: str, batch_size: int = 1000):
    if not records:
        print(f"- {table}: 업로드할 신규 데이터 없음")
        return

    total = len(records)
    for i in range(0, total, batch_size):
        batch = records[i : i + batch_size]
        supabase.table(table).upsert(batch, on_conflict=on_conflict).execute()
        print(f"- {table}: upsert {i} ~ {i + len(batch)} / {total}")


def main():
    supabase = get_supabase()

    # Streamlit Cloud의 "사용 가능한 데이터 기간" 계산에 직접 관여하는 핵심 테이블들
    table_specs = [
        # upbit_daily: UNIQUE(date, market)
        {"table": "upbit_daily", "date_col": "date", "on_conflict": "date,market", "extra_where": None, "params": ()},
        # binance_spot_daily: UNIQUE(date, symbol)
        {"table": "binance_spot_daily", "date_col": "date", "on_conflict": "date,symbol", "extra_where": None, "params": ()},
        # bitget_spot_daily: UNIQUE(date, symbol)
        {"table": "bitget_spot_daily", "date_col": "date", "on_conflict": "date,symbol", "extra_where": None, "params": ()},
        # bybit_spot_daily: UNIQUE(date, symbol)
        {"table": "bybit_spot_daily", "date_col": "date", "on_conflict": "date,symbol", "extra_where": None, "params": ()},
        # exchange_rate: UNIQUE(date)
        {"table": "exchange_rate", "date_col": "date", "on_conflict": "date", "extra_where": None, "params": ()},
    ]

    conn = sqlite3.connect(DB_PATH)
    try:
        for spec in table_specs:
            table = spec["table"]
            date_col = spec["date_col"]

            max_date = supabase_max_date(supabase, table, date_col=date_col)
            print(f"\n[{table}] Supabase max({date_col}) = {max_date}")

            df_new = read_sqlite_new_rows(
                conn,
                table=table,
                date_col=date_col,
                min_exclusive_date=max_date,
                extra_where=spec.get("extra_where"),
                params=spec.get("params", ()),
            )
            print(f"[{table}] SQLite 신규 rows = {len(df_new)}")

            records = clean_records(df_new)
            upsert_batches(supabase, table, records, on_conflict=spec["on_conflict"], batch_size=1000)

        # 최종 확인 (핵심 테이블 max date)
        print("\n✅ Supabase max dates (after sync):")
        print("  upbit_daily KRW-BTC:", supabase_max_date(supabase, "upbit_daily", eq_filters={"market": "KRW-BTC"}))
        print("  upbit_daily KRW-ETH:", supabase_max_date(supabase, "upbit_daily", eq_filters={"market": "KRW-ETH"}))
        print("  binance_spot_daily BTCUSDT:", supabase_max_date(supabase, "binance_spot_daily", eq_filters={"symbol": "BTCUSDT"}))
        print("  binance_spot_daily ETHUSDT:", supabase_max_date(supabase, "binance_spot_daily", eq_filters={"symbol": "ETHUSDT"}))
        print("  exchange_rate:", supabase_max_date(supabase, "exchange_rate"))
    finally:
        conn.close()


if __name__ == "__main__":
    main()


