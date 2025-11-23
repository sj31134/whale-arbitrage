#!/usr/bin/env python3
"""
서브 프로젝트 데이터 통합 테스트
- 테이블 간 데이터 일관성 검증
- 날짜 범위 일치 확인
- NULL 값 체크
"""

import sqlite3
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "project.db"


def test_date_overlap():
    """날짜 범위 겹침 테스트"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("📅 날짜 범위 겹침 테스트")
    print("-" * 60)
    
    # 각 테이블의 날짜 범위
    tables = {
        "upbit_daily": "market",
        "binance_spot_daily": "symbol",
        "binance_futures_metrics": "symbol"
    }
    
    for table, group_col in tables.items():
        cursor.execute(f"""
            SELECT {group_col}, MIN(date), MAX(date), COUNT(*) 
            FROM {table} 
            GROUP BY {group_col}
        """)
        results = cursor.fetchall()
        for row in results:
            print(f"  {table} - {row[0]}: {row[1]} ~ {row[2]} ({row[3]:,}건)")
    
    conn.close()


def test_data_quality():
    """데이터 품질 테스트"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n🔍 데이터 품질 테스트")
    print("-" * 60)
    
    # NULL 값 체크
    checks = [
        ("upbit_daily", "trade_price"),
        ("binance_spot_daily", "close"),
        ("binance_futures_metrics", "avg_funding_rate"),
    ]
    
    for table, col in checks:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL")
        null_count = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        total = cursor.fetchone()[0]
        null_pct = (null_count / total * 100) if total > 0 else 0
        status = "✅" if null_pct < 1 else "⚠️"
        print(f"  {status} {table}.{col}: NULL {null_count}/{total} ({null_pct:.2f}%)")
    
    conn.close()


def test_cross_table_consistency():
    """테이블 간 일관성 테스트"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n🔗 테이블 간 일관성 테스트")
    print("-" * 60)
    
    # Binance Spot vs Futures 날짜 매칭
    cursor.execute("""
        SELECT 
            bs.symbol,
            COUNT(DISTINCT bs.date) as spot_dates,
            COUNT(DISTINCT bf.date) as futures_dates,
            COUNT(DISTINCT CASE WHEN bf.date IS NOT NULL THEN bs.date END) as matched_dates
        FROM binance_spot_daily bs
        LEFT JOIN binance_futures_metrics bf 
            ON bs.symbol = bf.symbol AND bs.date = bf.date
        GROUP BY bs.symbol
    """)
    
    results = cursor.fetchall()
    for row in results:
        symbol, spot_dates, futures_dates, matched = row
        match_pct = (matched / spot_dates * 100) if spot_dates > 0 else 0
        status = "✅" if match_pct > 90 else "⚠️"
        print(f"  {status} {symbol}: Spot {spot_dates}일, Futures {futures_dates}일, 매칭 {matched}일 ({match_pct:.1f}%)")
    
    conn.close()


def main():
    print("=" * 60)
    print("서브 프로젝트 통합 테스트")
    print("=" * 60)
    
    test_date_overlap()
    test_data_quality()
    test_cross_table_consistency()
    
    print("\n" + "=" * 60)
    print("✅ 통합 테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()

