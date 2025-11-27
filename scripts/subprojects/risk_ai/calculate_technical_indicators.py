#!/usr/bin/env python3
"""
주봉 OHLCV 데이터를 기반으로 기술적 지표 계산
- Volume Profile
- ATR (Average True Range)
- RSI (Relative Strength Index)
- 위꼬리/아래꼬리 (Upper/Lower Shadow)
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"


def calculate_atr(df, period=14):
    """ATR (Average True Range) 계산"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    # True Range 계산
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR = TR의 지수 이동평균
    atr = tr.ewm(span=period, adjust=False).mean()
    
    return atr


def calculate_rsi(df, period=14):
    """RSI (Relative Strength Index) 계산"""
    close = df['close']
    delta = close.diff()
    
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_shadows(df):
    """위꼬리/아래꼬리 계산"""
    high = df['high']
    low = df['low']
    open_price = df['open']
    close = df['close']
    
    # 몸통 크기
    body = abs(close - open_price)
    
    # 위꼬리 (Upper Shadow)
    upper_shadow = high - pd.concat([open_price, close], axis=1).max(axis=1)
    
    # 아래꼬리 (Lower Shadow)
    lower_shadow = pd.concat([open_price, close], axis=1).min(axis=1) - low
    
    # 꼬리 비율 (몸통 대비)
    upper_shadow_ratio = upper_shadow / body.replace(0, np.nan)
    lower_shadow_ratio = lower_shadow / body.replace(0, np.nan)
    
    return upper_shadow, lower_shadow, upper_shadow_ratio, lower_shadow_ratio


def calculate_volume_profile(df, bins=20):
    """Volume Profile 계산 (가격대별 거래량 분포)"""
    # 가격 범위를 bins개로 나눔
    price_min = df['low'].min()
    price_max = df['high'].max()
    
    # 각 주봉의 가격 범위와 거래량을 이용하여 Volume Profile 계산
    # 간단한 방법: 각 주봉의 (high - low) 범위에 volume을 균등 분배
    volume_profile = []
    
    for _, row in df.iterrows():
        price_range = row['high'] - row['low']
        if price_range > 0:
            # 가격 범위를 bins로 나눔
            price_bins = np.linspace(row['low'], row['high'], bins + 1)
            volume_per_bin = row['volume'] / bins
            
            for i in range(bins):
                volume_profile.append({
                    'date': row['date'],
                    'price_level': (price_bins[i] + price_bins[i+1]) / 2,
                    'volume': volume_per_bin
                })
    
    return pd.DataFrame(volume_profile)


def calculate_technical_indicators(symbol="BTCUSDT"):
    """기술적 지표 계산 및 저장"""
    print("=" * 80)
    print(f"📊 기술적 지표 계산 ({symbol})")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. 주봉 데이터 로드
    print("\n📥 주봉 데이터 로드 중...")
    df = pd.read_sql("""
        SELECT 
            date,
            open,
            high,
            low,
            close,
            volume,
            quote_volume
        FROM binance_spot_weekly
        WHERE symbol = ?
        ORDER BY date
    """, conn, params=(symbol,))
    
    if len(df) == 0:
        print("⚠️ 주봉 데이터가 없습니다. 먼저 fetch_weekly_ohlcv.py를 실행하세요.")
        conn.close()
        return
    
    print(f"   ✅ {len(df)}주 데이터 로드 완료")
    print(f"   기간: {df['date'].min()} ~ {df['date'].max()}")
    
    # 2. 기술적 지표 계산
    print("\n📊 기술적 지표 계산 중...")
    
    # ATR
    df['atr'] = calculate_atr(df, period=14)
    print("   ✅ ATR 계산 완료")
    
    # RSI
    df['rsi'] = calculate_rsi(df, period=14)
    print("   ✅ RSI 계산 완료")
    
    # 위꼬리/아래꼬리
    df['upper_shadow'], df['lower_shadow'], df['upper_shadow_ratio'], df['lower_shadow_ratio'] = calculate_shadows(df)
    print("   ✅ 위꼬리/아래꼬리 계산 완료")
    
    # 주간 변동폭 (High - Low)
    df['weekly_range'] = df['high'] - df['low']
    df['weekly_range_pct'] = (df['weekly_range'] / df['close']) * 100
    
    # 몸통 크기 (Close - Open)
    df['body_size'] = abs(df['close'] - df['open'])
    df['body_size_pct'] = (df['body_size'] / df['close']) * 100
    
    # 변동성 비율 (이번 주 변동폭 / 4주 평균 변동폭)
    df['volatility_ratio'] = df['weekly_range_pct'] / df['weekly_range_pct'].rolling(4).mean()
    df['volatility_ratio'] = df['volatility_ratio'].fillna(1.0)
    
    print("   ✅ 추가 지표 계산 완료")
    
    # 3. DB 업데이트 (기존 테이블에 컬럼 추가 또는 별도 테이블)
    # 간단하게 기존 테이블에 컬럼 추가하는 대신, 별도 테이블에 저장
    print("\n💾 DB 저장 중...")
    
    # 기존 테이블에 컬럼 추가 (ALTER TABLE은 SQLite에서 제한적이므로 별도 테이블 사용)
    # 또는 기존 테이블 업데이트
    cursor = conn.cursor()
    
    # 컬럼이 없으면 추가 (SQLite는 ALTER TABLE ADD COLUMN 지원)
    try:
        cursor.execute("ALTER TABLE binance_spot_weekly ADD COLUMN atr REAL")
    except sqlite3.OperationalError:
        pass  # 이미 존재
    
    try:
        cursor.execute("ALTER TABLE binance_spot_weekly ADD COLUMN rsi REAL")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE binance_spot_weekly ADD COLUMN upper_shadow REAL")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE binance_spot_weekly ADD COLUMN lower_shadow REAL")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE binance_spot_weekly ADD COLUMN upper_shadow_ratio REAL")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE binance_spot_weekly ADD COLUMN lower_shadow_ratio REAL")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE binance_spot_weekly ADD COLUMN weekly_range REAL")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE binance_spot_weekly ADD COLUMN weekly_range_pct REAL")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE binance_spot_weekly ADD COLUMN body_size REAL")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE binance_spot_weekly ADD COLUMN body_size_pct REAL")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE binance_spot_weekly ADD COLUMN volatility_ratio REAL")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    
    # 데이터 업데이트
    for _, row in df.iterrows():
        cursor.execute("""
            UPDATE binance_spot_weekly
            SET 
                atr = ?,
                rsi = ?,
                upper_shadow = ?,
                lower_shadow = ?,
                upper_shadow_ratio = ?,
                lower_shadow_ratio = ?,
                weekly_range = ?,
                weekly_range_pct = ?,
                body_size = ?,
                body_size_pct = ?,
                volatility_ratio = ?
            WHERE symbol = ? AND date = ?
        """, (
            row['atr'],
            row['rsi'],
            row['upper_shadow'],
            row['lower_shadow'],
            row['upper_shadow_ratio'],
            row['lower_shadow_ratio'],
            row['weekly_range'],
            row['weekly_range_pct'],
            row['body_size'],
            row['body_size_pct'],
            row['volatility_ratio'],
            symbol,
            row['date']
        ))
    
    conn.commit()
    conn.close()
    
    print(f"   ✅ {len(df)}주 데이터 업데이트 완료")
    
    # 4. 결과 요약
    print("\n📊 계산된 지표 요약:")
    print(f"   ATR 평균: {df['atr'].mean():.2f}")
    print(f"   RSI 평균: {df['rsi'].mean():.2f}")
    print(f"   위꼬리 비율 평균: {df['upper_shadow_ratio'].mean():.2f}")
    print(f"   아래꼬리 비율 평균: {df['lower_shadow_ratio'].mean():.2f}")
    print(f"   주간 변동폭 평균: {df['weekly_range_pct'].mean():.2f}%")


def main():
    print("=" * 80)
    print("📊 기술적 지표 계산")
    print("=" * 80)
    
    calculate_technical_indicators("BTCUSDT")
    
    print("\n" + "=" * 80)
    print("✅ 기술적 지표 계산 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()




