#!/usr/bin/env python3
"""
Binance Vision 아카이브에서 일별 metrics 데이터 다운로드 및 파싱

목표:
- https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/ 에서
- 프로젝트 기간(2022-01-01 ~ 현재)에 해당하는 *.zip 파일 다운로드
- 압축 해제 후 CSV에서 OI, 롱/숏 비율, 매수/매도 압력 데이터 추출
- binance_futures_metrics 및 futures_extended_metrics 테이블에 저장
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
DOWNLOAD_DIR = ROOT / "temp" / "binance_vision_metrics"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://data.binance.vision"
METRICS_PATH = "data/futures/um/daily/metrics/BTCUSDT"  # 기본값, --symbol로 변경 가능

SYMBOL = "BTCUSDT"  # 기본값, --symbol로 변경 가능


def parse_date_from_filename(filename: str) -> Optional[datetime]:
    """파일명에서 날짜 추출 (예: BTCUSDT-metrics-2022-01-01.zip)"""
    # 패턴: BTCUSDT-metrics-YYYY-MM-DD.zip
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def list_available_files(start_date: datetime, end_date: datetime, symbol: str = "BTCUSDT") -> List[Dict[str, Any]]:
    """
    Binance Vision에서 사용 가능한 zip 파일 목록 조회
    파일명 패턴: {SYMBOL}-metrics-YYYY-MM-DD.zip
    """
    logging.info(f"Binance Vision 파일 목록 조회 중... (symbol: {symbol})")
    
    metrics_path = f"data/futures/um/daily/metrics/{symbol}"
    
    # Binance Vision은 파일명에 날짜가 포함되어 있으므로
    # 날짜 범위에 해당하는 파일명 생성
    files = []
    current = start_date
    
    while current <= end_date:
        filename = f"{symbol}-metrics-{current.strftime('%Y-%m-%d')}.zip"
        url = f"{BASE_URL}/{metrics_path}/{filename}"
        files.append({
            "filename": filename,
            "url": url,
            "date": current.date(),
        })
        current += timedelta(days=1)
    
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


def extract_metrics_from_csv(csv_content: str, file_date) -> Optional[Dict[str, Any]]:
    """
    CSV 파일에서 metrics 데이터 추출
    
    실제 컬럼:
    - sum_open_interest: OI
    - sum_toptrader_long_short_ratio / count_toptrader_long_short_ratio: Top Trader 롱/숏 비율
    - sum_taker_long_short_vol_ratio: Taker 롱/숏 거래량 비율
    """
    try:
        df = pd.read_csv(io.StringIO(csv_content))
        
        if len(df) == 0:
            return None
        
        # file_date가 date 객체인지 datetime 객체인지 확인
        if isinstance(file_date, datetime):
            date_obj = file_date.date()
        else:
            date_obj = file_date
        
        result = {
            "date": date_obj,
            "sum_open_interest": None,
            "top_trader_long_short_ratio": None,
            "taker_long_short_vol_ratio": None,
        }
        
        # OI 추출 (일별 마지막 값 또는 평균)
        if 'sum_open_interest' in df.columns:
            oi_value = df['sum_open_interest'].iloc[-1]  # 마지막 값 사용
            if pd.notna(oi_value):
                result["sum_open_interest"] = float(oi_value)
        
        # Top Trader 롱/숏 비율 (평균 계산)
        if 'sum_toptrader_long_short_ratio' in df.columns and 'count_toptrader_long_short_ratio' in df.columns:
            sum_ratio = df['sum_toptrader_long_short_ratio'].sum()
            count_ratio = df['count_toptrader_long_short_ratio'].sum()
            if count_ratio > 0:
                avg_ratio = sum_ratio / count_ratio
                result["top_trader_long_short_ratio"] = float(avg_ratio)
        
        # Taker 롱/숏 거래량 비율 (평균 계산)
        if 'sum_taker_long_short_vol_ratio' in df.columns:
            # 일별 평균 (시간별 데이터의 평균)
            avg_taker_ratio = df['sum_taker_long_short_vol_ratio'].mean()
            if pd.notna(avg_taker_ratio):
                result["taker_long_short_vol_ratio"] = float(avg_taker_ratio)
        
        return result
        
    except Exception as e:
        logging.error(f"CSV 파싱 오류 ({file_date}): {e}")
        return None


def process_zip_file(zip_content: bytes, file_date) -> Optional[Dict[str, Any]]:
    """ZIP 파일 압축 해제 및 CSV 파싱"""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
            # CSV 파일 찾기
            csv_files = [f for f in z.namelist() if f.endswith('.csv')]
            if not csv_files:
                logging.warning(f"CSV 파일 없음: {file_date}")
                return None
            
            # 첫 번째 CSV 파일 읽기
            csv_content = z.read(csv_files[0]).decode('utf-8')
            return extract_metrics_from_csv(csv_content, file_date)
            
    except Exception as e:
        logging.error(f"ZIP 처리 오류 ({file_date}): {e}")
        return None


def upsert_to_database(metrics: Dict[str, Any], symbol: str = "BTCUSDT") -> None:
    """추출된 metrics를 DB에 저장"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    date_str = str(metrics["date"])
    
    # binance_futures_metrics에 OI 업데이트
    if metrics.get("sum_open_interest") is not None:
        cur.execute("""
            UPDATE binance_futures_metrics
            SET sum_open_interest = ?
            WHERE date = ? AND symbol = ?
        """, (metrics["sum_open_interest"], date_str, symbol))
        
        # 레코드가 없으면 생성
        if cur.rowcount == 0:
            cur.execute("""
                INSERT INTO binance_futures_metrics (date, symbol, sum_open_interest, volatility_24h)
                VALUES (?, ?, ?, 0)
            """, (date_str, symbol, metrics["sum_open_interest"]))
    
    # futures_extended_metrics에 Top Trader, Taker 데이터 업데이트
    if any([metrics.get("top_trader_long_short_ratio"), metrics.get("taker_long_short_vol_ratio")]):
        # 테이블 생성 확인
        cur.execute("""
            CREATE TABLE IF NOT EXISTS futures_extended_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                long_short_ratio DECIMAL(10, 6),
                long_account_pct DECIMAL(10, 6),
                short_account_pct DECIMAL(10, 6),
                taker_buy_sell_ratio DECIMAL(10, 6),
                taker_buy_vol DECIMAL(30, 8),
                taker_sell_vol DECIMAL(30, 8),
                top_trader_long_short_ratio DECIMAL(10, 6),
                bybit_funding_rate DECIMAL(20, 10),
                bybit_oi DECIMAL(30, 10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, symbol)
            )
        """)
        
        # 기존 레코드 확인
        cur.execute("SELECT COUNT(*) FROM futures_extended_metrics WHERE date = ? AND symbol = ?", 
                   (date_str, symbol))
        exists = cur.fetchone()[0] > 0
        
        if exists:
            # 업데이트
            updates = []
            values = []
            if metrics.get("top_trader_long_short_ratio") is not None:
                updates.append("top_trader_long_short_ratio = ?")
                values.append(metrics["top_trader_long_short_ratio"])
            if metrics.get("taker_long_short_vol_ratio") is not None:
                # Taker 비율을 taker_buy_sell_ratio에 저장
                updates.append("taker_buy_sell_ratio = ?")
                values.append(metrics["taker_long_short_vol_ratio"])
            
            if updates:
                values.extend([date_str, symbol])
                cur.execute(f"""
                    UPDATE futures_extended_metrics
                    SET {', '.join(updates)}
                    WHERE date = ? AND symbol = ?
                """, values)
        else:
            # 삽입
            cur.execute("""
                INSERT INTO futures_extended_metrics 
                (date, symbol, top_trader_long_short_ratio, taker_buy_sell_ratio)
                VALUES (?, ?, ?, ?)
            """, (
                date_str, symbol,
                metrics.get("top_trader_long_short_ratio"),
                metrics.get("taker_long_short_vol_ratio")
            ))
    
    conn.commit()
    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Download and parse Binance Vision metrics data")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="심볼 (예: BTCUSDT, ETHUSDT)")
    parser.add_argument("--start-date", type=str, default="2022-01-01")
    parser.add_argument("--end-date", type=str, default=None)
    parser.add_argument("--limit", type=int, default=None, help="최대 다운로드 파일 수 (테스트용)")
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
    
    logging.info(f"Binance Vision metrics 다운로드: {symbol} ({start_date.date()} ~ {end_date.date()})")
    
    files = list_available_files(start_date, end_date, symbol)
    
    if args.limit:
        files = files[:args.limit]
        logging.info(f"제한 적용: {len(files)}개 파일만 처리")
    
    success_count = 0
    error_count = 0
    
    for i, file_info in enumerate(files, 1):
        if i % 100 == 0:
            logging.info(f"진행: {i}/{len(files)} ({success_count} 성공, {error_count} 실패)")
        
        zip_content = download_file(file_info["url"])
        if zip_content is None:
            error_count += 1
            continue
        
        metrics = process_zip_file(zip_content, file_info["date"])
        if metrics:
            upsert_to_database(metrics, symbol)
            success_count += 1
        else:
            error_count += 1
        
        # API 제한 방지
        time.sleep(0.1)
    
    logging.info(f"완료: {success_count}개 성공, {error_count}개 실패")


if __name__ == "__main__":
    main()

