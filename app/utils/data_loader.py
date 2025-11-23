"""
데이터 로더 유틸리티
- SQLite에서 거래소 데이터 로드
- 사용 가능한 날짜 범위 조회
- Streamlit Cloud 호환
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Optional
import os

# Streamlit Cloud 또는 로컬 환경 감지
if os.path.exists('/mount/src'):
    # Streamlit Cloud
    ROOT = Path('/mount/src/whale-arbitrage')
    DB_PATH = Path('/tmp') / "project.db"
elif os.path.exists('/tmp'):
    # 임시 디렉토리 사용 가능한 환경
    ROOT = Path('/tmp')
    DB_PATH = ROOT / "project.db"
elif os.path.exists('/app'):
    # Docker 컨테이너 내부
    ROOT = Path('/app')
    DB_PATH = ROOT / "data" / "project.db"
else:
    # 로컬 개발 환경
    ROOT = Path(__file__).resolve().parents[2]
    DB_PATH = ROOT / "data" / "project.db"


class DataLoader:
    def __init__(self):
        self.db_path = DB_PATH
        # 데이터베이스 파일이 없으면 다운로드 시도 (Streamlit Cloud용)
        if not self.db_path.exists():
            self._download_database_if_needed()
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"데이터베이스 파일을 찾을 수 없습니다: {self.db_path}")
        
        self.conn = sqlite3.connect(self.db_path)
    
    def _download_database_if_needed(self):
        """Streamlit Cloud에서 데이터베이스 다운로드 시도"""
        try:
            import streamlit as st
            db_url = st.secrets.get("DATABASE_URL", None)
            if db_url:
                import urllib.request
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                urllib.request.urlretrieve(db_url, str(self.db_path))
        except:
            pass
    
    def close(self):
        """데이터베이스 연결 종료"""
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def get_available_dates(self, coin: str = 'BTC') -> Tuple[Optional[str], Optional[str]]:
        """사용 가능한 날짜 범위 (최소, 최대) 반환"""
        if coin == 'BTC':
            market = 'KRW-BTC'
            symbol = 'BTCUSDT'
        elif coin == 'ETH':
            market = 'KRW-ETH'
            symbol = 'ETHUSDT'
        else:
            return None, None
        
        query = f"""
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date
        FROM (
            SELECT date FROM upbit_daily WHERE market = '{market}'
            INTERSECT
            SELECT date FROM binance_spot_daily WHERE symbol = '{symbol}'
            INTERSECT
            SELECT date FROM bitget_spot_daily WHERE symbol = '{symbol}'
            INTERSECT
            SELECT date FROM exchange_rate
        )
        """
        
        df = pd.read_sql(query, self.conn)
        if len(df) > 0 and pd.notna(df['min_date'].iloc[0]):
            return df['min_date'].iloc[0], df['max_date'].iloc[0]
        return None, None
    
    def get_available_dates_list(self, coin: str = 'BTC', start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[str]:
        """사용 가능한 날짜 목록 반환"""
        if coin == 'BTC':
            market = 'KRW-BTC'
            symbol = 'BTCUSDT'
        elif coin == 'ETH':
            market = 'KRW-ETH'
            symbol = 'ETHUSDT'
        else:
            return []
        
        date_filter = ""
        if start_date and end_date:
            date_filter = f"AND date BETWEEN '{start_date}' AND '{end_date}'"
        
        query = f"""
        SELECT DISTINCT date
        FROM (
            SELECT date FROM upbit_daily WHERE market = '{market}' {date_filter}
            INTERSECT
            SELECT date FROM binance_spot_daily WHERE symbol = '{symbol}' {date_filter}
            INTERSECT
            SELECT date FROM bitget_spot_daily WHERE symbol = '{symbol}' {date_filter}
            INTERSECT
            SELECT date FROM exchange_rate {date_filter} -- 환율 데이터도 필수
        )
        ORDER BY date
        """
        df = pd.read_sql(query, self.conn)
        return df['date'].tolist() if not df.empty else []

    def check_date_available(self, target_date: str, coin: str = 'BTC') -> Tuple[bool, Optional[str], Optional[int]]:
        """특정 날짜의 데이터 존재 여부 확인 및 가장 가까운 날짜 반환"""
        available_dates = self.get_available_dates_list(coin)
        target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        
        if target_date in available_dates:
            return True, target_date, 0
        
        # 가장 가까운 날짜 찾기
        if not available_dates:
            return False, None, None
        
        available_dts = [datetime.strptime(d, "%Y-%m-%d").date() for d in available_dates]
        
        closest_dt = min(available_dts, key=lambda d: abs((d - target_dt).days))
        days_diff = abs((closest_dt - target_dt).days)
        
        return False, closest_dt.strftime("%Y-%m-%d"), days_diff

    def load_exchange_data(
        self, 
        start_date: str, 
        end_date: str, 
        coin: str = 'BTC'
    ) -> pd.DataFrame:
        """거래소 데이터 로드 및 병합"""
        if coin == 'BTC':
            market = 'KRW-BTC'
            symbol = 'BTCUSDT'
        elif coin == 'ETH':
            market = 'KRW-ETH'
            symbol = 'ETHUSDT'
        else:
            raise ValueError(f"지원하지 않는 코인: {coin}")
        
        query = f"""
        SELECT 
            u.date,
            u.trade_price as upbit_price,
            b.close as binance_price,
            bg.close as bitget_price,
            e.krw_usd
        FROM upbit_daily u
        LEFT JOIN binance_spot_daily b ON u.date = b.date AND b.symbol = '{symbol}'
        LEFT JOIN bitget_spot_daily bg ON u.date = bg.date AND bg.symbol = '{symbol}'
        LEFT JOIN exchange_rate e ON u.date = e.date
        WHERE u.market = '{market}'
        AND u.date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY u.date
        """
        
        df = pd.read_sql(query, self.conn)
        if len(df) == 0:
            return df
        
        df['date'] = pd.to_datetime(df['date'])
        
        # 환율 결측치 처리 (주말/공휴일 대응)
        # 데이터베이스에서 이미 보완되었지만, 혹시 모를 경우를 대비한 추가 처리
        # 1. 앞의 값으로 채우기 (forward fill)
        df['krw_usd'] = df['krw_usd'].ffill()
        # 2. 뒤의 값으로 채우기 (backward fill) - 처음에 NULL이 있는 경우
        df['krw_usd'] = df['krw_usd'].bfill()
        # 3. 그래도 NULL이 있으면 선형 보간
        if df['krw_usd'].isna().any():
            df['krw_usd'] = df['krw_usd'].interpolate(method='linear', limit_direction='both')
        # 4. 최후의 수단: 평균값으로 채우기
        if df['krw_usd'].isna().any():
            mean_rate = df['krw_usd'].mean()
            if pd.notna(mean_rate):
                df['krw_usd'] = df['krw_usd'].fillna(mean_rate)
            else: # 모든 값이 NaN인 경우 (데이터가 극히 적거나 없음)
                df['krw_usd'] = 0.0 # 또는 적절한 기본값
        
        # USDT 가격을 원화로 환산
        df['binance_krw'] = df['binance_price'] * df['krw_usd']
        df['bitget_krw'] = df['bitget_price'] * df['krw_usd']
        
        return df
