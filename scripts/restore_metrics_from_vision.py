
import os
import sys
import requests
import zipfile
import io
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import time

# 프로젝트 루트 경로 설정
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from scripts.subprojects.risk_ai.fetch_futures_metrics import ensure_db, DB_PATH

BINANCE_VISION_BASE = "https://data.binance.vision/data/futures/um/daily/metrics"

def download_and_restore_metrics(symbol="BTCUSDT", start_date="2022-01-01", end_date=None):
    if end_date is None:
        end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
    print(f"🔄 {symbol} Metrics 복구 시작 ({start_date} ~ {end_date})...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    restored_count = 0
    failed_count = 0
    
    while current_date <= end_dt:
        date_str = current_date.strftime("%Y-%m-%d")
        
        # URL 생성 (예: BTCUSDT-metrics-2024-01-01.zip)
        filename = f"{symbol}-metrics-{date_str}.zip"
        url = f"{BINANCE_VISION_BASE}/{symbol}/{filename}"
        
        try:
            # print(f"  Downloading {url}...")
            resp = requests.get(url)
            
            if resp.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                    # CSV 파일명 찾기
                    csv_filename = z.namelist()[0]
                    with z.open(csv_filename) as f:
                        df = pd.read_csv(f)
                        
                        # 필요한 컬럼 확인
                        # create_time, symbol, sum_open_interest, sum_open_interest_value, count_top_long_short_position_ratio, sum_top_long_short_vol_ratio, count_long_short_ratio, sum_taker_long_short_vol_ratio
                        
                        if 'sum_open_interest' in df.columns and 'sum_open_interest_value' in df.columns:
                            # 마지막 레코드 사용 (하루치 요약이므로 보통 1개 또는 마지막 것이 유효)
                            last_row = df.iloc[-1]
                            
                            sum_oi = float(last_row['sum_open_interest'])
                            # sum_oi_val = float(last_row['sum_open_interest_value'])
                            
                            # DB 업데이트 (0이 아닌 경우에만)
                            if sum_oi > 0:
                                # 기존 데이터 유지하면서 OI만 업데이트
                                cursor.execute("""
                                    INSERT INTO binance_futures_metrics (
                                        date, symbol, avg_funding_rate, sum_open_interest, 
                                        long_short_ratio, volatility_24h
                                    ) VALUES (?, ?, ?, ?, ?, ?)
                                    ON CONFLICT(date, symbol) DO UPDATE SET
                                        sum_open_interest = excluded.sum_open_interest
                                """, (
                                    date_str, symbol, 
                                    0, # avg_funding은 건드리지 않음
                                    sum_oi, 
                                    0, 
                                    0
                                ))
                                restored_count += 1
                                if restored_count % 10 == 0:
                                    print(f"  ✅ {date_str} 복구 완료 (OI: {sum_oi})")
                                    conn.commit()
            elif resp.status_code == 404:
                # 데이터가 없는 날짜 (주말 등은 아님, Vision에 없을 수 있음)
                # print(f"  ⚠️ {date_str} 데이터 없음 (404)")
                pass
            else:
                print(f"  ❌ {date_str} 다운로드 실패: {resp.status_code}")
                failed_count += 1
                
        except Exception as e:
            print(f"  ❌ {date_str} 처리 중 오류: {e}")
            failed_count += 1
            
        current_date += timedelta(days=1)
        # time.sleep(0.1)
        
    conn.commit()
    conn.close()
    print(f"\n✅ 복구 완료: {restored_count}건 성공, {failed_count}건 실패")

if __name__ == "__main__":
    ensure_db()
    download_and_restore_metrics("BTCUSDT", "2022-01-01")
    download_and_restore_metrics("ETHUSDT", "2022-01-01")



