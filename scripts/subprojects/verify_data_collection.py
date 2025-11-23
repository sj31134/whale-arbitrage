#!/usr/bin/env python3
"""
서브 프로젝트 데이터 수집 완료도 검증 스크립트
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "project.db"


def verify_table(table_name, expected_start_date="2023-01-01"):
    """테이블 데이터 검증"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 총 레코드 수
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total = cursor.fetchone()[0]
    
    # 날짜 범위
    cursor.execute(f"SELECT MIN(date), MAX(date) FROM {table_name}")
    min_date, max_date = cursor.fetchone()
    
    # 코인/심볼별 통계
    if table_name == "upbit_daily":
        cursor.execute("SELECT market, COUNT(*), MIN(date), MAX(date) FROM upbit_daily GROUP BY market")
        details = cursor.fetchall()
    elif table_name == "binance_spot_daily":
        cursor.execute("SELECT symbol, COUNT(*), MIN(date), MAX(date) FROM binance_spot_daily GROUP BY symbol")
        details = cursor.fetchall()
    elif table_name == "binance_futures_metrics":
        cursor.execute("SELECT symbol, COUNT(*), MIN(date), MAX(date) FROM binance_futures_metrics GROUP BY symbol")
        details = cursor.fetchall()
    elif table_name == "bitinfocharts_whale":
        cursor.execute("SELECT coin, COUNT(*), MIN(date), MAX(date) FROM bitinfocharts_whale GROUP BY coin")
        details = cursor.fetchall()
    else:
        details = []
    
    conn.close()
    
    return {
        "total": total,
        "min_date": min_date,
        "max_date": max_date,
        "details": details
    }


def main():
    print("=" * 60)
    print("서브 프로젝트 데이터 수집 검증 리포트")
    print("=" * 60)
    
    tables = [
        "upbit_daily",
        "binance_spot_daily", 
        "binance_futures_metrics",
        "bitinfocharts_whale"
    ]
    
    for table in tables:
        print(f"\n📊 {table.upper()}")
        print("-" * 60)
        try:
            stats = verify_table(table)
            print(f"  총 레코드 수: {stats['total']:,}건")
            print(f"  날짜 범위: {stats['min_date']} ~ {stats['max_date']}")
            
            if stats['details']:
                print(f"  상세:")
                for detail in stats['details']:
                    print(f"    - {detail[0]}: {detail[1]:,}건 ({detail[2]} ~ {detail[3]})")
        except Exception as e:
            print(f"  ❌ 오류: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 검증 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()

