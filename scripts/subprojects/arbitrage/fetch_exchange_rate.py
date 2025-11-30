#!/usr/bin/env python3
"""
한국은행 ECOS API를 사용하여 원/달러 환율 데이터를 수집합니다.
"""

import os
import sqlite3
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / "config" / ".env")
DB_PATH = ROOT / "data" / "project.db"

ECOS_API_KEY = os.getenv("ECOS_API_KEY")
ECOS_BASE_URL = "http://ecos.bok.or.kr/api/StatisticSearch"


def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.close()


def upsert_exchange_rate(date_str, krw_usd):
    """환율 데이터 저장"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO exchange_rate (date, krw_usd) VALUES (?, ?)",
        (date_str, krw_usd)
    )
    conn.commit()
    conn.close()


def fetch_exchange_rate(start_date, end_date):
    """
    ECOS API를 통해 원/달러 환율 조회
    통계코드: 731Y001 (주요국통화의 대원화환율)
    항목코드: 0000001 (원/미국달러(매매기준율))
    주기: D (일별)
    """
    if not ECOS_API_KEY:
        raise ValueError("ECOS_API_KEY가 .env 파일에 설정되지 않았습니다.")
    
    # ECOS API URL 구성 (Path Variable 방식)
    stat_code = "731Y001"
    item_code = "0000001"
    cycle = "D"
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    # URL 끝에 슬래시(/) 중요
    url = f"http://ecos.bok.or.kr/api/StatisticSearch/{ECOS_API_KEY}/json/kr/1/10000/{stat_code}/{cycle}/{start_str}/{end_str}/{item_code}/"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # JSON 응답 파싱
        data = response.json()
        
        # 결과 확인
        result = data.get("RESULT", {})
        result_code = result.get("CODE", "")
        
        # INFO-000이 아니고 StatisticSearch도 없으면 에러
        if result_code and result_code != "INFO-000":
             # 데이터 없음(INFO-200)은 에러 아님
            if result_code == "INFO-200":
                print(f"  ℹ️ 해당 기간 데이터 없음 ({start_str} ~ {end_str})")
                return []
            
            error_msg = result.get("MESSAGE", "Unknown error")
            raise ValueError(f"ECOS API 오류 ({result_code}): {error_msg}")
        
        # 데이터 추출
        stat_search = data.get("StatisticSearch", {})
        row_list = stat_search.get("row", [])
        
        if not isinstance(row_list, list):
            row_list = [row_list] if row_list else []
        
        data_points = []
        
        for row in row_list:
            time_str = row.get("TIME", "")
            data_value = row.get("DATA_VALUE", "")
            
            if time_str and data_value:
                # YYYYMMDD -> YYYY-MM-DD 변환
                if len(time_str) == 8:
                    formatted_date = f"{time_str[:4]}-{time_str[4:6]}-{time_str[6:8]}"
                    try:
                        rate = float(data_value)
                        data_points.append((formatted_date, rate))
                    except (ValueError, TypeError):
                        continue
        
        return data_points
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ API 요청 오류: {e}")
        return []
    except ValueError as e:
        print(f"⚠️ {e}")
        return []
    except Exception as e:
        print(f"⚠️ 예상치 못한 오류: {e}")
        return []


def main():
    ensure_db()
    
    if not ECOS_API_KEY:
        print("❌ ECOS_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return
    
    # 2023-01-01부터 현재까지 수집
    start_date = datetime(2023, 1, 1)
    end_date = datetime.now()
    
    print(f"🔄 환율 데이터 수집 시작: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    # ECOS API는 최대 1년 단위로 조회 가능하므로 분할 수집
    current_start = start_date
    total_saved = 0
    
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=365), end_date)
        
        print(f"  수집 중: {current_start.strftime('%Y-%m-%d')} ~ {current_end.strftime('%Y-%m-%d')}")
        
        data_points = fetch_exchange_rate(current_start, current_end)
        
        if data_points:
            for date_str, rate in data_points:
                upsert_exchange_rate(date_str, rate)
            total_saved += len(data_points)
            print(f"  ✅ {len(data_points)}건 저장")
        else:
            print(f"  ⚠️ 데이터 없음")
        
        current_start = current_end + timedelta(days=1)
        time.sleep(0.5)  # Rate limit
    
    print(f"\n✅ 총 {total_saved}건의 환율 데이터 수집 완료")
    
    # 환율 데이터 보완 실행 (주말/공휴일 누락 데이터)
    print("\n" + "=" * 60)
    print("환율 데이터 보완 실행 (주말/공휴일 누락 데이터)")
    print("=" * 60)
    
    import sys
    sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "arbitrage"))
    from fill_missing_exchange_rate import fill_missing_exchange_rate, get_missing_dates
    
    conn = sqlite3.connect(DB_PATH)
    
    # 현재 데이터 범위 확인
    query = "SELECT MIN(date) as min_date, MAX(date) as max_date FROM exchange_rate"
    df = pd.read_sql(query, conn)
    
    if not df.empty and df['min_date'].iloc[0] is not None:
        min_date = df['min_date'].iloc[0]
        max_date = df['max_date'].iloc[0]
        
        missing_dates = get_missing_dates(conn, min_date, max_date)
        if missing_dates:
            filled_count = fill_missing_exchange_rate(conn, missing_dates)
            print(f"✅ {filled_count}일의 환율 데이터를 보완했습니다.")
        else:
            print("✅ 누락된 날짜가 없습니다.")
    
    conn.close()


if __name__ == "__main__":
    main()
    
    # 환율 데이터 보완 실행
    print("\n" + "=" * 60)
    print("환율 데이터 보완 실행")
    print("=" * 60)
    
    import sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "arbitrage"))
    
    from fill_missing_exchange_rate import fill_missing_exchange_rate, get_missing_dates
    import sqlite3
    
    conn = sqlite3.connect(DB_PATH)
    
    # 현재 데이터 범위 확인
    query = "SELECT MIN(date) as min_date, MAX(date) as max_date FROM exchange_rate"
    df = pd.read_sql(query, conn)
    
    if not df.empty and df['min_date'].iloc[0] is not None:
        min_date = df['min_date'].iloc[0]
        max_date = df['max_date'].iloc[0]
        
        missing_dates = get_missing_dates(conn, min_date, max_date)
        if missing_dates:
            filled_count = fill_missing_exchange_rate(conn, missing_dates)
            print(f"✅ {filled_count}일의 환율 데이터를 보완했습니다.")
        else:
            print("✅ 누락된 날짜가 없습니다.")
    
    conn.close()

