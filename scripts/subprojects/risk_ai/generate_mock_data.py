#!/usr/bin/env python3
"""
Risk AI 모델 학습을 위한 Mock 데이터 생성
- bitinfocharts_whale 테이블에 2023-01-01 ~ 현재까지의 가상 데이터 주입
- binance_futures_metrics 테이블의 날짜와 매칭
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

def generate_mock_whale_data():
    print("🛠️ Mock Whale Data 생성 시작...")
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. 기준 날짜 가져오기 (Binance Futures 데이터 기준)
    dates_query = "SELECT DISTINCT date FROM binance_futures_metrics ORDER BY date"
    dates = pd.read_sql(dates_query, conn)['date'].tolist()
    
    if not dates:
        print("⚠️ Binance Futures 데이터가 없습니다. 날짜를 생성합니다.")
        dates = pd.date_range(start="2023-01-01", end=datetime.now()).strftime("%Y-%m-%d").tolist()
    
    print(f"📅 총 {len(dates)}일 데이터 생성 예정")
    
    # 2. 가상 데이터 생성
    # Top 100 Rich List %: 15% ~ 25% 사이에서 랜덤하게 변동 (추세 반영)
    # Avg Tx Value: 5 BTC ~ 50 BTC
    
    mock_data = []
    
    # Random Walk로 자연스러운 시계열 생성
    current_pct = 18.5
    current_avg_tx = 15.0
    
    np.random.seed(42)
    
    for date_str in dates:
        # Random Walk
        current_pct += np.random.normal(0, 0.1)
        current_pct = max(15.0, min(25.0, current_pct))
        
        current_avg_tx += np.random.normal(0, 1.0)
        current_avg_tx = max(2.0, min(100.0, current_avg_tx))
        
        # Top 10 Pct (Optional Column)
        top10_pct = current_pct * 2.5 
        
        mock_data.append((
            date_str,
            'BTC',
            round(current_pct, 2),
            round(current_avg_tx, 4),
            round(top10_pct, 2)
        ))
    
    # 3. DB 저장
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR REPLACE INTO bitinfocharts_whale 
        (date, coin, top100_richest_pct, avg_transaction_value_btc, top10_pct)
        VALUES (?, ?, ?, ?, ?)
    """, mock_data)
    
    conn.commit()
    conn.close()
    print(f"✅ {len(mock_data)}건의 Mock Whale Data 저장 완료")

if __name__ == "__main__":
    generate_mock_whale_data()

