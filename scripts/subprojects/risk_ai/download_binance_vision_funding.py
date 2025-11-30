#!/usr/bin/env python3
"""
Binance Vision 아카이브에서 월별 Funding Rate 데이터 다운로드 및 파싱

목표:
- https://data.binance.vision/data/futures/um/monthly/fundingRate/{SYMBOL}/ 에서
- 프로젝트 기간(2022-01-01 ~ 현재)에 해당하는 *.zip 파일 다운로드
- 압축 해제 후 CSV에서 Funding Rate 데이터 추출
- binance_futures_metrics 테이블에 저장
"""

import argparse
import logging
import sqlite3
import zipfile
import io
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"
BASE_URL = "https://data.binance.vision"


def list_available_funding_files(start_date: datetime, end_date: datetime, symbol: str = "BTCUSDT") -> List[Dict[str, Any]]:
    """
    Binance Vision에서 사용 가능한 Funding Rate zip 파일 목록 조회
    파일명 패턴: {SYMBOL}-fundingRate-YYYY-MM.zip
    """
    logging.info(f"Binance Vision Funding Rate 파일 목록 조회 중... (symbol: {symbol})")
    
    funding_path = f"data/futures/um/monthly/fundingRate/{symbol}"
    
    # 월별 파일 생성
    files = []
    current = start_date.replace(day=1)  # 월의 첫날로 시작
    
    while current <= end_date:
        filename = f"{symbol}-fundingRate-{current.strftime('%Y-%m')}.zip"
        url = f"{BASE_URL}/{funding_path}/{filename}"
        files.append({
            "filename": filename,
            "url": url,
            "year": current.year,
            "month": current.month,
        })
        
        # 다음 달로 이동
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    logging.info(f"총 {len(files)}개 파일 대상")
    return files


def download_file(url: str, max_retries: int = 3) -> Optional[bytes]:
    """파일 다운로드 (재시도 포함)"""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.content
            elif resp.status_code == 404:
                logging.debug(f"파일 없음: {url}")
                return None
            else:
                logging.warning(f"HTTP {resp.status_code} for {url}, 재시도 {attempt + 1}/{max_retries}")
        except Exception as e:
            logging.warning(f"다운로드 오류 ({url}): {e}, 재시도 {attempt + 1}/{max_retries}")
        
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # 지수 백오프
    
    return None


def extract_funding_from_csv(csv_content: str) -> pd.DataFrame:
    """
    CSV 파일에서 Funding Rate 데이터 추출
    
    컬럼:
    - funding_time: 타임스탬프 (ms)
    - funding_rate: 펀딩비
    """
    try:
        df = pd.read_csv(io.StringIO(csv_content))
        
        if len(df) == 0:
            return pd.DataFrame()
        
        # 타임스탬프를 날짜로 변환
        if 'funding_time' in df.columns:
            df['date'] = pd.to_datetime(df['funding_time'], unit='ms', utc=True).dt.date
        elif 'timestamp' in df.columns:
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.date
        else:
            logging.warning("타임스탬프 컬럼을 찾을 수 없습니다.")
            return pd.DataFrame()
        
        # Funding Rate 추출
        if 'funding_rate' in df.columns:
            df['funding_rate'] = pd.to_numeric(df['funding_rate'], errors='coerce')
        else:
            logging.warning("funding_rate 컬럼을 찾을 수 없습니다.")
            return pd.DataFrame()
        
        # 일별 평균 Funding Rate 계산
        daily_funding = df.groupby('date')['funding_rate'].mean().reset_index()
        daily_funding.columns = ['date', 'avg_funding_rate']
        
        return daily_funding
        
    except Exception as e:
        logging.error(f"CSV 파싱 오류: {e}")
        return pd.DataFrame()


def process_zip_file(zip_content: bytes) -> pd.DataFrame:
    """ZIP 파일 압축 해제 및 CSV 파싱"""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
            # CSV 파일 찾기
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                logging.warning("CSV 파일 없음")
                return pd.DataFrame()
            
            # 첫 번째 CSV 파일 읽기
            csv_content = z.read(csv_files[0]).decode('utf-8')
            return extract_funding_from_csv(csv_content)
            
    except Exception as e:
        logging.error(f"ZIP 처리 오류: {e}")
        return pd.DataFrame()


def upsert_funding_to_database(daily_funding: pd.DataFrame, symbol: str = "BTCUSDT") -> int:
    """추출된 Funding Rate를 DB에 저장"""
    if daily_funding.empty:
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    inserted_count = 0
    updated_count = 0
    
    for _, row in daily_funding.iterrows():
        date_str = str(row['date'])
        avg_funding = float(row['avg_funding_rate'])
        
        # 기존 레코드 확인
        cur.execute("SELECT COUNT(*) FROM binance_futures_metrics WHERE date = ? AND symbol = ?", 
                   (date_str, symbol))
        exists = cur.fetchone()[0] > 0
        
        if exists:
            # 업데이트
            cur.execute("""
                UPDATE binance_futures_metrics
                SET avg_funding_rate = ?
                WHERE date = ? AND symbol = ?
            """, (avg_funding, date_str, symbol))
            if cur.rowcount > 0:
                updated_count += 1
        else:
            # 삽입
            cur.execute("""
                INSERT INTO binance_futures_metrics (date, symbol, avg_funding_rate, volatility_24h)
                VALUES (?, ?, ?, 0)
            """, (date_str, symbol, avg_funding))
            inserted_count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    return inserted_count + updated_count


def main():
    parser = argparse.ArgumentParser(description="Download and parse Binance Vision funding rate data")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="심볼 (예: BTCUSDT, ETHUSDT)")
    parser.add_argument("--start-date", type=str, default="2022-01-01")
    parser.add_argument("--end-date", type=str, default=None)
    args = parser.parse_args()
    
    symbol = args.symbol.upper()
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        end_date = datetime.now(timezone.utc)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    logging.info(f"Binance Vision Funding Rate 다운로드: {symbol} ({start_date.date()} ~ {end_date.date()})")
    
    files = list_available_funding_files(start_date, end_date, symbol)
    
    success_count = 0
    error_count = 0
    total_rows = 0
    
    for i, file_info in enumerate(files, 1):
        if i % 10 == 0:
            logging.info(f"진행: {i}/{len(files)} ({success_count} 성공, {error_count} 실패, {total_rows}행 저장)")
        
        zip_content = download_file(file_info["url"])
        if zip_content is None:
            error_count += 1
            continue
        
        daily_funding = process_zip_file(zip_content)
        if not daily_funding.empty:
            rows = upsert_funding_to_database(daily_funding, symbol)
            total_rows += rows
            success_count += 1
        else:
            error_count += 1
        
        # API 제한 방지
        time.sleep(0.2)
    
    logging.info(f"완료: {success_count}개 성공, {error_count}개 실패, 총 {total_rows}행 저장")


if __name__ == "__main__":
    main()

