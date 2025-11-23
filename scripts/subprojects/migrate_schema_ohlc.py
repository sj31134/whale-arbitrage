#!/usr/bin/env python3
"""
스키마 마이그레이션: OHLC 컬럼 추가
- upbit_daily: opening_price, high_price, low_price 추가
- binance_spot_daily: open, high, low 추가
- bitinfocharts_whale: top10_pct 추가 (optional)
"""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "project.db"


def migrate_schema():
    """스키마 마이그레이션 실행"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🔄 스키마 마이그레이션 시작...")
    
    # 1. upbit_daily에 OHLC 컬럼 추가
    try:
        cursor.execute("""
            ALTER TABLE upbit_daily 
            ADD COLUMN opening_price REAL
        """)
        print("✅ upbit_daily.opening_price 추가")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("ℹ️ upbit_daily.opening_price 이미 존재")
        else:
            raise
    
    try:
        cursor.execute("""
            ALTER TABLE upbit_daily 
            ADD COLUMN high_price REAL
        """)
        print("✅ upbit_daily.high_price 추가")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("ℹ️ upbit_daily.high_price 이미 존재")
        else:
            raise
    
    try:
        cursor.execute("""
            ALTER TABLE upbit_daily 
            ADD COLUMN low_price REAL
        """)
        print("✅ upbit_daily.low_price 추가")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("ℹ️ upbit_daily.low_price 이미 존재")
        else:
            raise
    
    # 2. binance_spot_daily에 OHLC 컬럼 추가
    try:
        cursor.execute("""
            ALTER TABLE binance_spot_daily 
            ADD COLUMN open REAL
        """)
        print("✅ binance_spot_daily.open 추가")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("ℹ️ binance_spot_daily.open 이미 존재")
        else:
            raise
    
    try:
        cursor.execute("""
            ALTER TABLE binance_spot_daily 
            ADD COLUMN high REAL
        """)
        print("✅ binance_spot_daily.high 추가")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("ℹ️ binance_spot_daily.high 이미 존재")
        else:
            raise
    
    try:
        cursor.execute("""
            ALTER TABLE binance_spot_daily 
            ADD COLUMN low REAL
        """)
        print("✅ binance_spot_daily.low 추가")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("ℹ️ binance_spot_daily.low 이미 존재")
        else:
            raise
    
    # 3. bitinfocharts_whale에 top10_pct 추가
    try:
        cursor.execute("""
            ALTER TABLE bitinfocharts_whale 
            ADD COLUMN top10_pct REAL
        """)
        print("✅ bitinfocharts_whale.top10_pct 추가")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("ℹ️ bitinfocharts_whale.top10_pct 이미 존재")
        else:
            raise
    
    conn.commit()
    conn.close()
    
    print("✅ 스키마 마이그레이션 완료")


if __name__ == "__main__":
    migrate_schema()

