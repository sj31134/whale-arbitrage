#!/usr/bin/env python3
"""
로컬 SQLite 데이터베이스(data/project.db)에 서브 프로젝트용 테이블을 생성합니다.
현재 데이터 수집 파이프라인에서 사용하는 테이블을 모두 정의합니다.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/project.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

CREATE_TABLE_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS upbit_daily (
        market TEXT NOT NULL,
        date TEXT NOT NULL,
        opening_price REAL,
        high_price REAL,
        low_price REAL,
        trade_price REAL,
        trade_volume REAL,
        acc_trade_price REAL,
        PRIMARY KEY (market, date)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS binance_spot_daily (
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        quote_volume REAL,
        PRIMARY KEY (symbol, date)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS bitget_spot_daily (
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        quote_volume REAL,
        PRIMARY KEY (symbol, date)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS binance_futures_metrics (
        date TEXT NOT NULL,
        symbol TEXT NOT NULL,
        avg_funding_rate REAL,
        sum_open_interest REAL,
        long_short_ratio REAL,
        volatility_24h REAL,
        target_volatility_24h REAL,
        PRIMARY KEY (date, symbol)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS bitinfocharts_whale (
        date TEXT NOT NULL,
        coin TEXT NOT NULL,
        top100_richest_pct REAL,
        avg_transaction_value_btc REAL,
        PRIMARY KEY (date, coin)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS exchange_rate (
        date TEXT NOT NULL PRIMARY KEY,
        krw_usd REAL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS binance_spot_weekly (
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        quote_volume REAL,
        PRIMARY KEY (symbol, date)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS whale_weekly_stats (
        date TEXT NOT NULL,
        coin_symbol TEXT NOT NULL,
        net_inflow_usd REAL,
        exchange_inflow_usd REAL,
        active_addresses INTEGER,
        transaction_count INTEGER,
        avg_buy_price REAL,
        PRIMARY KEY (date, coin_symbol)
    );
    """,
]


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"📁 SQLite 데이터베이스 준비: {DB_PATH}")
    for stmt in CREATE_TABLE_STATEMENTS:
        cursor.execute(stmt)
    conn.commit()
    cursor.close()
    conn.close()

    print("✅ 서브 프로젝트용 테이블 생성 완료")


if __name__ == "__main__":
    main()

