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
import logging

# Streamlit Cloud 또는 로컬 환경 감지
if os.path.exists('/mount/src'):
    # Streamlit Cloud
    ROOT = Path('/mount/src/whale-arbitrage')
    DB_PATH = Path('/tmp') / "project.db"
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
            try:
                self._download_database_if_needed()
            except Exception as e:
                # 다운로드 실패 시 상세한 에러 메시지
                import logging
                logging.error(f"데이터베이스 다운로드 실패: {str(e)}")
                raise FileNotFoundError(
                    f"데이터베이스 파일을 찾을 수 없습니다: {self.db_path}\n"
                    f"다운로드 시도 실패: {str(e)}\n"
                    f"Streamlit Cloud의 경우 Secrets에 DATABASE_URL이 설정되어 있는지 확인하세요."
                ) from e
        
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"데이터베이스 파일을 찾을 수 없습니다: {self.db_path}\n"
                f"Streamlit Cloud의 경우 Secrets에 DATABASE_URL이 설정되어 있는지 확인하세요."
            )
        
        # 데이터베이스 연결
        try:
            self.conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            # 기본 검증: 테이블 존재 확인
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            table_names = [t[0] for t in tables]
            
            if len(tables) == 0:
                import logging
                logging.error(f"데이터베이스에 테이블이 없습니다. 파일 경로: {self.db_path}")
                raise ValueError(f"데이터베이스에 테이블이 없습니다. 파일 경로: {self.db_path}")
            
            # 필수 테이블 확인
            required_tables = ['upbit_daily', 'binance_spot_daily', 'bitget_spot_daily', 'exchange_rate']
            missing_tables = [t for t in required_tables if t not in table_names]
            if missing_tables:
                import logging
                logging.warning(f"일부 테이블이 없습니다: {missing_tables}. 존재하는 테이블: {table_names}")
                
        except sqlite3.Error as e:
            import logging
            error_msg = f"데이터베이스 연결 실패: {str(e)}\n파일 경로: {self.db_path}\n파일 존재: {self.db_path.exists()}"
            logging.error(error_msg)
            raise sqlite3.Error(error_msg) from e
    
    def _download_database_if_needed(self):
        """Streamlit Cloud에서 데이터베이스 다운로드 및 압축 해제"""
        try:
            import streamlit as st
            try:
                db_url = st.secrets.get("DATABASE_URL", None)
            except (FileNotFoundError, AttributeError):
                # Streamlit secrets 파일이 없는 경우 (로컬 개발 환경)
                return
            if not db_url:
                return
            
            import urllib.request
            import tarfile
            
            # 임시 디렉토리 생성
            temp_dir = self.db_path.parent
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # URL에서 파일 확장자 확인
            if db_url.endswith('.tar.gz'):
                # .tar.gz 파일 다운로드
                temp_tar = temp_dir / "project.db.tar.gz"
                urllib.request.urlretrieve(db_url, str(temp_tar))
                
                # 압축 해제
                with tarfile.open(temp_tar, 'r:gz') as tar:
                    # 압축 해제 (temp_dir에)
                    tar.extractall(temp_dir)
                
                # 임시 파일 삭제
                temp_tar.unlink()
                
                # 압축 해제된 파일 확인 (data/project.db 형태로 압축되어 있음)
                # 1순위: data/project.db
                alt_path = temp_dir / "data" / "project.db"
                if alt_path.exists():
                    # 목적지 디렉토리 생성
                    self.db_path.parent.mkdir(parents=True, exist_ok=True)
                    # 파일 이동
                    alt_path.rename(self.db_path)
                    # 빈 data 디렉토리 정리 (있는 경우)
                    try:
                        if alt_path.parent.exists() and not any(alt_path.parent.iterdir()):
                            alt_path.parent.rmdir()
                    except:
                        pass
                # 2순위: temp_dir/project.db
                elif (temp_dir / "project.db").exists():
                    extracted_db = temp_dir / "project.db"
                    self.db_path.parent.mkdir(parents=True, exist_ok=True)
                    extracted_db.rename(self.db_path)
                else:
                    # 모든 가능한 위치 확인
                    all_db_files = list(temp_dir.rglob("*.db"))
                    raise FileNotFoundError(
                        f"압축 해제 후 데이터베이스 파일을 찾을 수 없습니다.\n"
                        f"예상 위치: {temp_dir / 'data' / 'project.db'} 또는 {temp_dir / 'project.db'}\n"
                        f"발견된 .db 파일: {[str(f) for f in all_db_files]}"
                    )
            else:
                # .db 파일 직접 다운로드
                urllib.request.urlretrieve(db_url, str(self.db_path))
            
            # 다운로드 성공 확인
            if not self.db_path.exists():
                raise FileNotFoundError(f"다운로드 후 파일이 존재하지 않습니다: {self.db_path}")
                
        except Exception as e:
            # 구체적인 에러 메시지 (Streamlit Cloud 로그에 표시)
            error_msg = f"데이터베이스 다운로드 실패: {str(e)}\n경로: {self.db_path}"
            # 로깅 (Streamlit Cloud 로그에 표시됨)
            import logging
            logging.error(error_msg)
            # Streamlit이 있는 경우 UI에도 표시
            try:
                import streamlit as st
                st.error(f"❌ {error_msg}")
            except:
                pass
            raise FileNotFoundError(error_msg) from e
    
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
        
        try:
            # 데이터베이스 연결 확인
            if not hasattr(self, 'conn') or self.conn is None:
                import logging
                logging.error("데이터베이스 연결이 없습니다")
                return None, None
            
            # 먼저 테이블 존재 확인
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            required_tables = ['upbit_daily', 'binance_spot_daily', 'bitget_spot_daily', 'exchange_rate']
            missing_tables = [t for t in required_tables if t not in existing_tables]
            
            if missing_tables:
                import logging
                error_msg = f"필수 테이블이 없습니다: {missing_tables}. 존재하는 테이블: {list(existing_tables)}"
                logging.error(error_msg)
                try:
                    import streamlit as st
                    st.error(f"❌ 필수 테이블 누락: {', '.join(missing_tables)}")
                except:
                    pass
                return None, None
            
            # SQL 쿼리 실행 (pandas 대신 직접 cursor 사용)
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
            
            # pandas.read_sql 대신 직접 cursor 사용
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result and result[0] is not None:
                return result[0], result[1]
            return None, None
            
        except sqlite3.Error as e:
            import logging
            error_msg = f"SQL 오류 (get_available_dates): {str(e)}\n데이터베이스 경로: {self.db_path}"
            logging.error(error_msg)
            try:
                import streamlit as st
                st.error(f"❌ 데이터베이스 오류: {str(e)}")
            except:
                pass
            return None, None
        except Exception as e:
            import logging
            error_msg = f"get_available_dates 오류: {str(e)}\n데이터베이스 경로: {self.db_path}"
            logging.error(error_msg)
            try:
                import streamlit as st
                st.error(f"❌ 데이터 조회 오류: {str(e)}")
            except:
                pass
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
        
        try:
            if not hasattr(self, 'conn') or self.conn is None:
                logging.error("데이터베이스 연결이 없습니다")
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
                SELECT date FROM exchange_rate WHERE 1=1 {date_filter} -- 환율 데이터도 필수
            )
            ORDER BY date
            """
            # pandas.read_sql 대신 직접 cursor 사용
            cursor = self.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            return [row[0] for row in results]
        except sqlite3.Error as e:
            error_msg = f"SQL 오류 (get_available_dates_list): {str(e)}"
            logging.error(error_msg)
            try:
                import streamlit as st
                st.error(f"❌ 데이터베이스 오류: {str(e)}")
            except:
                pass
            return []
        except Exception as e:
            error_msg = f"get_available_dates_list 오류: {str(e)}"
            logging.error(error_msg)
            try:
                import streamlit as st
                st.error(f"❌ 데이터 조회 오류: {str(e)}")
            except:
                pass
            return []

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
        
        try:
            if not hasattr(self, 'conn') or self.conn is None:
                logging.error("데이터베이스 연결이 없습니다")
                return pd.DataFrame()
            
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
            
            # pandas.read_sql 사용 (JOIN 쿼리는 복잡하므로 pandas 사용)
            df = pd.read_sql(query, self.conn)
        except sqlite3.Error as e:
            error_msg = f"SQL 오류 (load_exchange_data): {str(e)}"
            logging.error(error_msg)
            try:
                import streamlit as st
                st.error(f"❌ 데이터베이스 오류: {str(e)}")
            except:
                pass
            return pd.DataFrame()
        except Exception as e:
            error_msg = f"load_exchange_data 오류: {str(e)}"
            logging.error(error_msg)
            try:
                import streamlit as st
                st.error(f"❌ 데이터 로드 오류: {str(e)}")
            except:
                pass
            return pd.DataFrame()
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
    
    def validate_date_range(self, start_date: str, end_date: str, coin: str = 'BTC') -> Tuple[bool, str]:
        """날짜 범위 검증"""
        # 날짜 형식 검증
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return False, "날짜 형식이 올바르지 않습니다. (YYYY-MM-DD 형식 필요)"
        
        # 시작 날짜가 종료 날짜보다 늦은 경우
        if start_dt > end_dt:
            return False, "시작 날짜가 종료 날짜보다 늦습니다."
        
        # 최소 30일 이상의 데이터 필요
        days_diff = (end_dt - start_dt).days
        if days_diff < 30:
            return False, f"최소 30일 이상의 기간이 필요합니다. (현재: {days_diff}일)"
        
        # 사용 가능한 날짜 범위 확인
        min_date, max_date = self.get_available_dates(coin)
        if not min_date or not max_date:
            return False, f"{coin}에 대한 데이터가 없습니다."
        
        min_dt = datetime.strptime(min_date, "%Y-%m-%d").date()
        max_dt = datetime.strptime(max_date, "%Y-%m-%d").date()
        
        # 요청한 날짜 범위가 사용 가능한 범위를 벗어나는 경우
        if start_dt < min_dt or end_dt > max_dt:
            return False, f"사용 가능한 날짜 범위는 {min_date} ~ {max_date}입니다."
        
        # 실제 데이터 존재 확인
        available_dates = self.get_available_dates_list(coin, start_date, end_date)
        if len(available_dates) < 30:
            return False, f"선택한 기간에 사용 가능한 데이터가 부족합니다. (필요: 30일 이상, 현재: {len(available_dates)}일)"
        
        return True, ""
