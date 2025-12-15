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

# Streamlit 모듈 조건부 임포트 및 더미 캐시 데코레이터 정의
try:
    import streamlit as st
except ImportError:
    st = None

def dummy_cache(ttl=None):
    def decorator(func):
        return func
    return decorator

# st.cache_data가 없으면 더미 데코레이터 사용
if st is None:
    st_cache_data = dummy_cache
else:
    st_cache_data = st.cache_data

# Streamlit Cloud 또는 로컬 환경 감지
if os.path.exists('/mount/src'):
    # Streamlit Cloud
    ROOT = Path('/mount/src/whale-arbitrage')
    DB_PATH = Path('/tmp') / "project.db"
    USE_SUPABASE = True  # 클라우드에서는 Supabase 우선 사용
elif os.path.exists('/app'):
    # Docker 컨테이너 내부
    ROOT = Path('/app')
    DB_PATH = ROOT / "data" / "project.db"
    USE_SUPABASE = False
else:
    # 로컬 개발 환경
    ROOT = Path(__file__).resolve().parents[2]
    DB_PATH = ROOT / "data" / "project.db"
    USE_SUPABASE = False


class DataLoader:
    def __init__(self):
        self.db_path = DB_PATH
        self.use_supabase = USE_SUPABASE
        self._supabase_client = None
        
        # Streamlit UI에 디버그 정보 표시 (Streamlit Cloud용)
        try:
            import streamlit as st
            with st.spinner("데이터베이스 초기화 중..."):
                self._initialize_database(st_module=st)
        except ImportError:
            # Streamlit이 없는 환경 (테스트 등)
            self._initialize_database(st_module=None)
    
    def _get_supabase_client(self):
        """Supabase 클라이언트 가져오기 (지연 초기화)"""
        if self._supabase_client is None:
            try:
                from supabase import create_client
                from .secrets_helper import get_secret
                
                is_streamlit_cloud = os.path.exists('/mount/src')

                # Streamlit Cloud에서는 "서비스 롤 키" 사용을 피하고, 앱에서는 anon key 사용을 권장
                supabase_url = get_secret("SUPABASE_URL")
                supabase_key = get_secret("SUPABASE_KEY") or get_secret("SUPABASE_ANON_KEY")

                # 로컬/서버 사이드 작업(maintenance 스크립트 등)에서는 서비스 롤 키 폴백 허용
                if not is_streamlit_cloud and not supabase_key:
                    supabase_key = get_secret("SUPABASE_SERVICE_ROLE_KEY")
                
                if not supabase_url or not supabase_key:
                    raise ValueError("Supabase 환경 변수가 설정되지 않았습니다. SUPABASE_URL과 SUPABASE_KEY를 확인하세요.")
                
                self._supabase_client = create_client(supabase_url, supabase_key)
                logging.info("Supabase 클라이언트 초기화 완료")
            except ImportError:
                logging.warning("supabase 패키지가 설치되지 않았습니다. SQLite만 사용합니다.")
                self.use_supabase = False
            except Exception as e:
                logging.warning(f"Supabase 초기화 실패: {e}. SQLite로 폴백합니다.")
                self.use_supabase = False
        
        return self._supabase_client
    
    def _initialize_database(self, st_module=None):
        """데이터베이스 초기화 로직
        
        Args:
            st_module: streamlit 모듈 (Streamlit 실행 환경에서만 전달). 없으면 UI 출력 없이 동작.
        """
        st = st_module
        
        # 환경 정보 (디버깅용)
        is_streamlit_cloud = os.path.exists('/mount/src')
        debug_info = {
            "환경": "Streamlit Cloud" if is_streamlit_cloud else "로컬/Docker",
            "DB 경로": str(self.db_path),
            "파일 존재": self.db_path.exists(),
            "Supabase 사용": self.use_supabase,
            "/tmp 존재": os.path.exists('/tmp'),
            "/mount/src 존재": os.path.exists('/mount/src'),
        }
        
        # Supabase 사용 시 SQLite 파일 체크 건너뛰기
        if self.use_supabase:
            try:
                supabase = self._get_supabase_client()
                if supabase:
                    if st:
                        st.success("✅ Supabase 연결 성공")
                    # Supabase 사용 시 SQLite 파일 불필요
                    self._conn = None
                    self._db_path = None
                    return
            except Exception as e:
                logging.warning(f"Supabase 초기화 실패, SQLite로 폴백: {e}")
                self.use_supabase = False
        
        # 데이터베이스 파일이 없으면 다운로드 시도 (Streamlit Cloud용)
        if not self.db_path.exists():
            try:
                if st:
                    st.info("📥 데이터베이스 파일을 다운로드하는 중...")
                self._download_database_if_needed()
                if self.db_path.exists():
                    if st:
                        st.success(f"✅ 데이터베이스 다운로드 완료: {self.db_path}")
                else:
                    if st:
                        st.error(f"❌ 다운로드 후에도 파일이 없습니다: {self.db_path}")
            except Exception as e:
                # 다운로드 실패 시 상세한 에러 메시지
                error_msg = f"데이터베이스 다운로드 실패: {str(e)}"
                logging.error(error_msg)
                try:
                    if st:
                        st.error(f"❌ {error_msg}")
                        st.json(debug_info)
                except:
                    pass
                raise FileNotFoundError(
                    f"데이터베이스 파일을 찾을 수 없습니다: {self.db_path}\n"
                    f"다운로드 시도 실패: {str(e)}\n"
                    f"Streamlit Cloud의 경우 Secrets에 DATABASE_URL이 설정되어 있는지 확인하세요.\n"
                    f"디버그 정보: {debug_info}"
                ) from e
        
        if not self.db_path.exists():
            try:
                if st:
                    st.error(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {self.db_path}")
                    st.json(debug_info)
            except:
                pass
            raise FileNotFoundError(
                f"데이터베이스 파일을 찾을 수 없습니다: {self.db_path}\n"
                f"Streamlit Cloud의 경우 Secrets에 DATABASE_URL이 설정되어 있는지 확인하세요.\n"
                f"디버그 정보: {debug_info}"
            )
        
        # 데이터베이스 연결 (지연 연결 - 필요할 때마다 새로 연결)
        # Streamlit Cloud에서는 멀티스레드 환경이므로 연결을 캐싱하지 않음
        self._conn = None
        self._db_path = str(self.db_path)
        
        # 초기 연결 테스트
        try:
            import streamlit as st
            with st.spinner("데이터베이스 연결 테스트 중..."):
                test_conn = sqlite3.connect(self._db_path, timeout=10.0, check_same_thread=False)
                cursor = test_conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                table_names = [t[0] for t in tables]
                test_conn.close()
                
                if len(tables) == 0:
                    error_msg = f"데이터베이스에 테이블이 없습니다. 파일 경로: {self.db_path}"
                    logging.error(error_msg)
                    st.error(f"❌ {error_msg}")
                    raise ValueError(error_msg)
                
                # 필수 테이블 확인
                required_tables = ['upbit_daily', 'binance_spot_daily', 'bitget_spot_daily', 'exchange_rate']
                missing_tables = [t for t in required_tables if t not in table_names]
                if missing_tables:
                    warning_msg = f"일부 테이블이 없습니다: {missing_tables}. 존재하는 테이블: {table_names}"
                    logging.warning(warning_msg)
                    st.warning(f"⚠️ {warning_msg}")
                else:
                    st.success(f"✅ 데이터베이스 연결 성공 ({len(tables)}개 테이블)")
        except ImportError:
            # Streamlit이 없는 환경
            test_conn = sqlite3.connect(self._db_path, timeout=10.0, check_same_thread=False)
            cursor = test_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            table_names = [t[0] for t in tables]
            test_conn.close()
            
            if len(tables) == 0:
                logging.error(f"데이터베이스에 테이블이 없습니다. 파일 경로: {self.db_path}")
                raise ValueError(f"데이터베이스에 테이블이 없습니다. 파일 경로: {self.db_path}")
            
            # 필수 테이블 확인
            required_tables = ['upbit_daily', 'binance_spot_daily', 'bitget_spot_daily', 'exchange_rate']
            missing_tables = [t for t in required_tables if t not in table_names]
            if missing_tables:
                logging.warning(f"일부 테이블이 없습니다: {missing_tables}. 존재하는 테이블: {table_names}")
        except sqlite3.Error as e:
            error_msg = f"데이터베이스 연결 실패: {str(e)}\n파일 경로: {self.db_path}\n파일 존재: {self.db_path.exists()}"
            logging.error(error_msg)
            try:
                import streamlit as st
                st.error(f"❌ {error_msg}")
            except:
                pass
            raise sqlite3.Error(error_msg) from e
    
    @property
    def conn(self):
        """데이터베이스 연결 (필요할 때마다 새로 생성)"""
        # Supabase 사용 시 SQLite 연결 불필요
        if self.use_supabase:
            return None
        
        # _db_path가 None이면 SQLite 사용 안 함
        if self._db_path is None:
            return None
        
        if self._conn is None:
            try:
                self._conn = sqlite3.connect(self._db_path, timeout=10.0, check_same_thread=False)
            except sqlite3.Error as e:
                logging.error(f"데이터베이스 재연결 실패: {str(e)}")
                raise
        return self._conn
    
    def _download_database_if_needed(self):
        """Streamlit Cloud에서 데이터베이스 다운로드 및 압축 해제"""
        import streamlit as st
        
        try:
            # Secrets에서 DATABASE_URL 가져오기
            db_url = None
            try:
                if hasattr(st, 'secrets'):
                    if hasattr(st.secrets, 'get'):
                        db_url = st.secrets.get("DATABASE_URL", None)
                    elif "DATABASE_URL" in st.secrets:
                        db_url = st.secrets["DATABASE_URL"]
            except (FileNotFoundError, AttributeError, KeyError, TypeError):
                # Streamlit secrets 파일이 없거나 키가 없는 경우
                pass
            except Exception as e:
                logging.warning(f"Secrets 읽기 오류: {str(e)}")
            
            if not db_url:
                st.warning("⚠️ DATABASE_URL이 Secrets에 설정되어 있지 않습니다.")
                return
            
            if not db_url:
                st.warning("⚠️ DATABASE_URL이 비어있습니다.")
                return
            
            st.info(f"📥 다운로드 URL: {db_url[:50]}...")
            
            import urllib.request
            import tarfile
            
            # 임시 디렉토리 생성
            temp_dir = self.db_path.parent
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # URL에서 파일 확장자 확인
            if db_url.endswith('.tar.gz'):
                st.info("📦 .tar.gz 파일 다운로드 중...")
                # .tar.gz 파일 다운로드
                temp_tar = temp_dir / "project.db.tar.gz"
                try:
                    urllib.request.urlretrieve(db_url, str(temp_tar))
                    st.info(f"✅ 다운로드 완료: {temp_tar.stat().st_size / 1024:.2f} KB")
                except Exception as e:
                    st.error(f"❌ 다운로드 실패: {str(e)}")
                    raise
                
                # 압축 해제
                st.info("📂 압축 해제 중...")
                try:
                    with tarfile.open(temp_tar, 'r:gz') as tar:
                        # 압축 해제 (temp_dir에)
                        tar.extractall(temp_dir)
                    st.info("✅ 압축 해제 완료")
                except Exception as e:
                    st.error(f"❌ 압축 해제 실패: {str(e)}")
                    raise
                
                # 임시 파일 삭제
                try:
                    temp_tar.unlink()
                except:
                    pass
                
                # 압축 해제된 파일 확인 (data/project.db 형태로 압축되어 있음)
                # 1순위: data/project.db
                alt_path = temp_dir / "data" / "project.db"
                if alt_path.exists():
                    st.info(f"✅ data/project.db 발견: {alt_path}")
                    # 목적지 디렉토리 생성
                    self.db_path.parent.mkdir(parents=True, exist_ok=True)
                    # 파일 이동
                    alt_path.rename(self.db_path)
                    st.success(f"✅ 파일 이동 완료: {self.db_path}")
                    # 빈 data 디렉토리 정리 (있는 경우)
                    try:
                        if alt_path.parent.exists() and not any(alt_path.parent.iterdir()):
                            alt_path.parent.rmdir()
                    except:
                        pass
                # 2순위: temp_dir/project.db
                elif (temp_dir / "project.db").exists():
                    extracted_db = temp_dir / "project.db"
                    st.info(f"✅ project.db 발견: {extracted_db}")
                    self.db_path.parent.mkdir(parents=True, exist_ok=True)
                    extracted_db.rename(self.db_path)
                    st.success(f"✅ 파일 이동 완료: {self.db_path}")
                else:
                    # 모든 가능한 위치 확인
                    all_db_files = list(temp_dir.rglob("*.db"))
                    all_files = list(temp_dir.rglob("*"))
                    error_msg = (
                        f"압축 해제 후 데이터베이스 파일을 찾을 수 없습니다.\n"
                        f"예상 위치: {temp_dir / 'data' / 'project.db'} 또는 {temp_dir / 'project.db'}\n"
                        f"발견된 .db 파일: {[str(f) for f in all_db_files]}\n"
                        f"압축 해제된 모든 파일: {[str(f.relative_to(temp_dir)) for f in all_files[:20]]}"
                    )
                    st.error(f"❌ {error_msg}")
                    raise FileNotFoundError(error_msg)
            else:
                # .db 파일 직접 다운로드
                st.info("📥 .db 파일 직접 다운로드 중...")
                urllib.request.urlretrieve(db_url, str(self.db_path))
                st.success(f"✅ 다운로드 완료: {self.db_path}")
            
            # 다운로드 성공 확인
            if not self.db_path.exists():
                error_msg = f"다운로드 후 파일이 존재하지 않습니다: {self.db_path}"
                st.error(f"❌ {error_msg}")
                raise FileNotFoundError(error_msg)
            
            # 파일 크기 확인
            file_size = self.db_path.stat().st_size / 1024
            st.info(f"📊 데이터베이스 파일 크기: {file_size:.2f} KB")
                
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
        if hasattr(self, '_conn') and self._conn is not None:
            try:
                self._conn.close()
            except:
                pass
            finally:
                self._conn = None
    
    def get_available_dates(self, coin: str = 'BTC') -> Tuple[Optional[str], Optional[str]]:
        """사용 가능한 날짜 범위 (최소, 최대) 반환"""
        if coin == 'BTC':
            market = 'KRW-BTC'
            symbol = 'BTCUSDT'
            coin_label = 'BTC'
        elif coin == 'ETH':
            market = 'KRW-ETH'
            symbol = 'ETHUSDT'
            coin_label = 'ETH'
        else:
            return None, None
        
        try:
            # Supabase 우선 사용 (클라우드 환경)
            if self.use_supabase:
                try:
                    supabase = self._get_supabase_client()
                    if supabase:
                        # 1. RPC(get_common_date_range)를 사용하여 서버사이드에서 정확한 범위 계산 시도
                        try:
                            rpc_resp = supabase.rpc('get_common_date_range', {
                                'p_market': market,
                                'p_symbol': symbol
                            }).execute()
                            
                            if rpc_resp.data and len(rpc_resp.data) > 0:
                                row = rpc_resp.data[0]
                                min_d, max_d = row.get('min_date'), row.get('max_date')
                                if min_d and max_d:
                                    return min_d, max_d
                        except Exception as rpc_e:
                            logging.warning(f"Supabase RPC 호출 실패 (get_common_date_range): {rpc_e}. 기존 방식으로 폴백합니다.")

                        # 2. RPC 실패 시 기존 방식 (클라이언트 사이드 교집합 - row limit 주의)
                        # load_exchange_data가 사용하는 주요 테이블들의 교집합 날짜 조회
                        # 1. upbit_daily
                        upbit_dates = set()
                        upbit_resp = supabase.table("upbit_daily").select("date").eq("market", market).execute()
                        if upbit_resp.data:
                            upbit_dates = {row['date'] for row in upbit_resp.data}
                        
                        # 2. binance_spot_daily
                        binance_dates = set()
                        binance_resp = supabase.table("binance_spot_daily").select("date").eq("symbol", symbol).execute()
                        if binance_resp.data:
                            binance_dates = {row['date'] for row in binance_resp.data}
                            
                        # 3. exchange_rate (환율)
                        exchange_dates = set()
                        exchange_resp = supabase.table("exchange_rate").select("date").execute()
                        if exchange_resp.data:
                            exchange_dates = {row['date'] for row in exchange_resp.data}
                        
                        # 교집합 계산 (최소한 이 3개는 있어야 함)
                        common_dates = upbit_dates & binance_dates & exchange_dates
                        
                        if common_dates:
                            dates = sorted(list(common_dates))
                            min_date = dates[0]
                            max_date = dates[-1]
                            return min_date, max_date
                        
                        # 데이터가 없으면 None 반환
                        return None, None
                except Exception as e:
                    logging.warning(f"Supabase에서 날짜 조회 실패, SQLite로 폴백: {e}")
                    # SQLite로 폴백
            
            # SQLite 사용 (로컬 환경 또는 Supabase 실패 시)
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
            # load_exchange_data와 동일한 로직으로 교집합 조회
            query = f"""
            SELECT 
                MIN(date) as min_date,
                MAX(date) as max_date
            FROM (
                SELECT date FROM upbit_daily WHERE market = '{market}'
                INTERSECT
                SELECT date FROM binance_spot_daily WHERE symbol = '{symbol}'
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
            coin_label = 'BTC'
        elif coin == 'ETH':
            market = 'KRW-ETH'
            symbol = 'ETHUSDT'
            coin_label = 'ETH'
        else:
            return []
        
        try:
            # Supabase 우선 사용 (클라우드 환경)
            if self.use_supabase:
                try:
                    supabase = self._get_supabase_client()
                    if supabase:
                        # binance_futures_metrics에서 날짜 목록 조회
                        query = supabase.table("binance_futures_metrics") \
                            .select("date") \
                            .eq("symbol", symbol)
                        
                        if start_date:
                            query = query.gte("date", start_date)
                        if end_date:
                            query = query.lte("date", end_date)
                        
                        response = query.order("date").execute()
                        
                        if response.data and len(response.data) > 0:
                            dates = sorted(list(set([row['date'] for row in response.data])))
                            return dates
                        
                        # 데이터가 없으면 빈 리스트 반환
                        return []
                except Exception as e:
                    logging.warning(f"Supabase에서 날짜 목록 조회 실패, SQLite로 폴백: {e}")
                    # SQLite로 폴백
            
            # SQLite 사용 (로컬 환경 또는 Supabase 실패 시)
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

    @st_cache_data(ttl=3600)
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
        
        # Supabase 우선 사용 (클라우드 환경)
        if self.use_supabase:
            try:
                supabase = self._get_supabase_client()
                if supabase:
                    # 각 테이블에서 데이터 로드
                    # 1. upbit_daily
                    upbit_response = supabase.table("upbit_daily") \
                        .select("date, trade_price") \
                        .eq("market", market) \
                        .gte("date", start_date) \
                        .lte("date", end_date) \
                        .order("date") \
                        .execute()
                    
                    if not upbit_response.data or len(upbit_response.data) == 0:
                        return pd.DataFrame()
                    
                    df = pd.DataFrame(upbit_response.data)
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.rename(columns={'trade_price': 'upbit_price'})
                    
                    # 2. binance_spot_daily
                    binance_response = supabase.table("binance_spot_daily") \
                        .select("date, close") \
                        .eq("symbol", symbol) \
                        .gte("date", start_date) \
                        .lte("date", end_date) \
                        .order("date") \
                        .execute()
                    
                    if binance_response.data and len(binance_response.data) > 0:
                        binance_df = pd.DataFrame(binance_response.data)
                        binance_df['date'] = pd.to_datetime(binance_df['date'])
                        df = pd.merge(df, binance_df[['date', 'close']], on='date', how='left')
                        df = df.rename(columns={'close': 'binance_price'})
                    else:
                        df['binance_price'] = None
                    
                    # 3. bitget_spot_daily
                    bitget_response = supabase.table("bitget_spot_daily") \
                        .select("date, close") \
                        .eq("symbol", symbol) \
                        .gte("date", start_date) \
                        .lte("date", end_date) \
                        .order("date") \
                        .execute()
                    
                    if bitget_response.data and len(bitget_response.data) > 0:
                        bitget_df = pd.DataFrame(bitget_response.data)
                        bitget_df['date'] = pd.to_datetime(bitget_df['date'])
                        df = pd.merge(df, bitget_df[['date', 'close']], on='date', how='left')
                        df = df.rename(columns={'close': 'bitget_price'})
                    else:
                        df['bitget_price'] = None
                    
                    # 4. bybit_spot_daily
                    bybit_response = supabase.table("bybit_spot_daily") \
                        .select("date, close") \
                        .eq("symbol", symbol) \
                        .gte("date", start_date) \
                        .lte("date", end_date) \
                        .order("date") \
                        .execute()
                    
                    if bybit_response.data and len(bybit_response.data) > 0:
                        bybit_df = pd.DataFrame(bybit_response.data)
                        bybit_df['date'] = pd.to_datetime(bybit_df['date'])
                        df = pd.merge(df, bybit_df[['date', 'close']], on='date', how='left')
                        df = df.rename(columns={'close': 'bybit_price'})
                    else:
                        df['bybit_price'] = None
                    
                    # 5. exchange_rate
                    exchange_response = supabase.table("exchange_rate") \
                        .select("date, krw_usd") \
                        .gte("date", start_date) \
                        .lte("date", end_date) \
                        .order("date") \
                        .execute()
                    
                    if exchange_response.data and len(exchange_response.data) > 0:
                        exchange_df = pd.DataFrame(exchange_response.data)
                        exchange_df['date'] = pd.to_datetime(exchange_df['date'])
                        df = pd.merge(df, exchange_df[['date', 'krw_usd']], on='date', how='left')
                    else:
                        df['krw_usd'] = None
                    
                    # 환율 결측치 처리
                    df['krw_usd'] = df['krw_usd'].ffill().bfill()
                    if df['krw_usd'].isna().any():
                        df['krw_usd'] = df['krw_usd'].interpolate(method='linear', limit_direction='both')
                    if df['krw_usd'].isna().any():
                        mean_rate = df['krw_usd'].mean()
                        if pd.notna(mean_rate):
                            df['krw_usd'] = df['krw_usd'].fillna(mean_rate)
                        else:
                            df['krw_usd'] = 0.0
                    
                    # USDT 가격을 원화로 환산
                    df['binance_krw'] = df['binance_price'] * df['krw_usd']
                    df['bitget_krw'] = df['bitget_price'] * df['krw_usd']
                    df['bybit_krw'] = df['bybit_price'] * df['krw_usd']
                    
                    return df
            except Exception as e:
                logging.warning(f"Supabase에서 거래소 데이터 로드 실패, SQLite로 폴백: {e}")
                # SQLite로 폴백
        
        # SQLite 사용 (로컬 환경 또는 Supabase 실패 시)
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
                bb.close as bybit_price,
                e.krw_usd
            FROM upbit_daily u
            LEFT JOIN binance_spot_daily b ON u.date = b.date AND b.symbol = '{symbol}'
            LEFT JOIN bitget_spot_daily bg ON u.date = bg.date AND bg.symbol = '{symbol}'
            LEFT JOIN bybit_spot_daily bb ON u.date = bb.date AND bb.symbol = '{symbol}'
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
        df['bybit_krw'] = df['bybit_price'] * df['krw_usd']
        
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
    
    @st_cache_data(ttl=3600)
    def load_risk_data(self, start_date: str, end_date: str, coin: str = 'BTC') -> pd.DataFrame:
        """Project 3 (Risk AI) 데이터 로드
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            coin: 코인 심볼 ('BTC' 또는 'ETH', 기본값: 'BTC')
        
        Returns:
            DataFrame with columns:
            - date: 날짜
            - symbol: 심볼 (예: 'BTCUSDT')
            - avg_funding_rate: 평균 펀딩비
            - sum_open_interest: 미결제약정 합계
            - long_short_ratio: 롱/숏 비율
            - volatility_24h: 24시간 변동성
            - top100_richest_pct: Top 100 지갑 보유 비중
            - avg_transaction_value_btc: 평균 거래 금액 (BTC)
        """
        if coin == 'BTC':
            symbol = 'BTCUSDT'
            coin_label = 'BTC'
        elif coin == 'ETH':
            symbol = 'ETHUSDT'
            coin_label = 'ETH'
        else:
            raise ValueError(f"지원하지 않는 코인: {coin}")
        
        # Supabase 우선 사용 (클라우드 환경)
        if self.use_supabase:
            try:
                supabase = self._get_supabase_client()
                if supabase:
                    # binance_futures_metrics 로드
                    futures_response = supabase.table("binance_futures_metrics") \
                        .select("*") \
                        .eq("symbol", symbol) \
                        .gte("date", start_date) \
                        .lte("date", end_date) \
                        .order("date") \
                        .execute()
                    
                    if futures_response.data and len(futures_response.data) > 0:
                        df = pd.DataFrame(futures_response.data)
                        df['date'] = pd.to_datetime(df['date'])
                        
                        # bitinfocharts_whale 데이터 병합
                        whale_response = supabase.table("bitinfocharts_whale") \
                            .select("*") \
                            .eq("coin", coin_label) \
                            .gte("date", start_date) \
                            .lte("date", end_date) \
                            .order("date") \
                            .execute()
                        
                        if whale_response.data and len(whale_response.data) > 0:
                            whale_df = pd.DataFrame(whale_response.data)
                            whale_df['date'] = pd.to_datetime(whale_df['date'])
                            df = pd.merge(df, whale_df[['date', 'top100_richest_pct', 'avg_transaction_value_btc']], 
                                        on='date', how='left')
                        
                        # 숫자 컬럼 변환
                        numeric_columns = [
                            'avg_funding_rate', 'sum_open_interest', 'long_short_ratio',
                            'volatility_24h', 'top100_richest_pct', 'avg_transaction_value_btc'
                        ]
                        for col in numeric_columns:
                            if col in df.columns:
                                df[col] = pd.to_numeric(df[col], errors='coerce')
                        
                        # whale 데이터는 선택적이므로, 파생상품 데이터가 있으면 유지
                        # whale 컬럼만 forward fill하고, 파생상품 핵심 컬럼이 있으면 행 유지
                        whale_cols = ['top100_richest_pct', 'avg_transaction_value_btc']
                        core_cols = ['avg_funding_rate', 'sum_open_interest', 'volatility_24h']
                        
                        # whale 컬럼만 forward fill 후 0으로 채우기 (NaN 방지)
                        for col in whale_cols:
                            if col in df.columns:
                                df[col] = df[col].ffill().fillna(0.0)
                        
                        # 핵심 파생상품 컬럼 중 하나라도 있으면 행 유지
                        # (whale 데이터가 없어도 파생상품 데이터는 반환)
                        if len(core_cols) > 0:
                            has_core_data = df[core_cols].notna().any(axis=1)
                            df = df[has_core_data]
                        
                        # 전체 데이터프레임에 대해 최종적으로 NaN을 0으로 채우기 (안전장치)
                        df = df.fillna(0.0)
                        
                        return df
                    else:
                        # Supabase에서 데이터가 없으면 빈 DataFrame 반환
                        logging.warning(f"Supabase에서 {symbol} 데이터가 없습니다 (기간: {start_date} ~ {end_date})")
                        return pd.DataFrame()
            except Exception as e:
                logging.warning(f"Supabase에서 데이터 로드 실패, SQLite로 폴백: {e}")
                # SQLite로 폴백
        
        # SQLite 사용 (로컬 환경 또는 Supabase 실패 시)
        try:
            if not hasattr(self, 'conn') or self.conn is None:
                logging.error("데이터베이스 연결이 없습니다")
                return pd.DataFrame()
            
            query = f"""
            SELECT 
                f.date,
                f.symbol,
                f.avg_funding_rate,
                f.sum_open_interest,
                f.long_short_ratio,
                f.volatility_24h,
                b.top100_richest_pct,
                b.avg_transaction_value_btc
            FROM binance_futures_metrics f
            LEFT JOIN bitinfocharts_whale b ON f.date = b.date AND b.coin = '{coin_label}'
            WHERE f.symbol = '{symbol}'
            AND f.date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY f.date
            """
            
            df = pd.read_sql(query, self.conn)
            
            if len(df) == 0:
                return df
            
            df['date'] = pd.to_datetime(df['date'])
            
            # 숫자 컬럼을 명시적으로 float로 변환 (SQLite에서 object로 읽히는 경우 방지)
            numeric_columns = [
                'avg_funding_rate',
                'sum_open_interest',
                'long_short_ratio',
                'volatility_24h',
                'top100_richest_pct',
                'avg_transaction_value_btc'
            ]
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 결측치 처리 (Forward Fill)
            # whale 데이터는 선택적이므로, 파생상품 데이터가 있으면 유지
            # whale 컬럼만 forward fill하고, 파생상품 핵심 컬럼이 있으면 행 유지
            whale_cols = ['top100_richest_pct', 'avg_transaction_value_btc']
            core_cols = ['avg_funding_rate', 'sum_open_interest', 'volatility_24h']
            
            # whale 컬럼만 forward fill
            for col in whale_cols:
                if col in df.columns:
                    df[col] = df[col].ffill()
            
            # 핵심 파생상품 컬럼 중 하나라도 있으면 행 유지
            # (whale 데이터가 없어도 파생상품 데이터는 반환)
            if len(core_cols) > 0:
                has_core_data = df[core_cols].notna().any(axis=1)
                df = df[has_core_data]
            
            return df
            
        except sqlite3.Error as e:
            error_msg = f"SQL 오류 (load_risk_data): {str(e)}"
            logging.error(error_msg)
            try:
                import streamlit as st
                st.error(f"❌ 데이터베이스 오류: {str(e)}")
            except:
                pass
            return pd.DataFrame()
        except Exception as e:
            error_msg = f"load_risk_data 오류: {str(e)}"
            logging.error(error_msg)
            try:
                import streamlit as st
                st.error(f"❌ 데이터 로드 오류: {str(e)}")
            except:
                pass
            return pd.DataFrame()
    
    @st_cache_data(ttl=3600)
    def load_futures_extended_metrics(self, start_date: str, end_date: str, symbol: str = 'BTCUSDT') -> pd.DataFrame:
        """파생상품 확장 지표 로드 (futures_extended_metrics)
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            symbol: 심볼 (기본값: 'BTCUSDT')
        
        Returns:
            DataFrame with futures extended metrics
        """
        # Supabase 우선 사용 (클라우드 환경)
        if self.use_supabase:
            try:
                supabase = self._get_supabase_client()
                if supabase:
                    response = supabase.table("futures_extended_metrics") \
                        .select("*") \
                        .eq("symbol", symbol) \
                        .gte("date", start_date) \
                        .lte("date", end_date) \
                        .order("date") \
                        .execute()
                    
                    if response.data and len(response.data) > 0:
                        df = pd.DataFrame(response.data)
                        df['date'] = pd.to_datetime(df['date'])
                        
                        # 숫자 컬럼 변환
                        numeric_columns = [
                            'long_short_ratio', 'long_account_pct', 'short_account_pct',
                            'taker_buy_sell_ratio', 'taker_buy_vol', 'taker_sell_vol',
                            'top_trader_long_short_ratio', 'bybit_funding_rate', 'bybit_oi'
                        ]
                        for col in numeric_columns:
                            if col in df.columns:
                                df[col] = pd.to_numeric(df[col], errors='coerce')
                        
                        return df
                    else:
                        # Supabase에서 데이터가 없으면 빈 DataFrame 반환
                        logging.warning(f"Supabase에서 {symbol} futures_extended_metrics 데이터가 없습니다 (기간: {start_date} ~ {end_date})")
                        return pd.DataFrame()
            except Exception as e:
                logging.warning(f"Supabase에서 데이터 로드 실패, SQLite로 폴백: {e}")
                # SQLite로 폴백
        
        # SQLite 사용 (로컬 환경 또는 Supabase 실패 시)
        try:
            if not hasattr(self, 'conn') or self.conn is None:
                logging.error("데이터베이스 연결이 없습니다")
                return pd.DataFrame()
            
            query = f"""
            SELECT 
                date,
                symbol,
                long_short_ratio,
                long_account_pct,
                short_account_pct,
                taker_buy_sell_ratio,
                taker_buy_vol,
                taker_sell_vol,
                top_trader_long_short_ratio,
                bybit_funding_rate,
                bybit_oi
            FROM futures_extended_metrics
            WHERE symbol = '{symbol}'
            AND date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY date
            """
            
            df = pd.read_sql(query, self.conn)
            
            if len(df) == 0:
                return df
            
            df['date'] = pd.to_datetime(df['date'])
            
            # 숫자 컬럼 변환
            numeric_columns = [
                'long_short_ratio',
                'long_account_pct',
                'short_account_pct',
                'taker_buy_sell_ratio',
                'taker_buy_vol',
                'taker_sell_vol',
                'top_trader_long_short_ratio',
                'bybit_funding_rate',
                'bybit_oi'
            ]
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except sqlite3.Error as e:
            error_msg = f"SQL 오류 (load_futures_extended_metrics): {str(e)}"
            logging.error(error_msg)
            return pd.DataFrame()
        except Exception as e:
            error_msg = f"load_futures_extended_metrics 오류: {str(e)}"
            logging.error(error_msg)
            return pd.DataFrame()
    
    @st_cache_data(ttl=3600)
    def load_risk_data_weekly(self, start_date: str, end_date: str, coin: str = 'BTC') -> pd.DataFrame:
        """Project 3 (Risk AI) 주봉 데이터 로드
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            coin: 코인 심볼 ('BTC' 또는 'ETH', 기본값: 'BTC')
        
        Returns:
            DataFrame with weekly aggregated data
        """
        if coin == 'BTC':
            symbol = 'BTCUSDT'
            coin_label = 'BTC'
        elif coin == 'ETH':
            symbol = 'ETHUSDT'
            coin_label = 'ETH'
        else:
            raise ValueError(f"지원하지 않는 코인: {coin}")
        
        # Supabase 우선 사용 (클라우드 환경)
        if self.use_supabase:
            try:
                supabase = self._get_supabase_client()
                if supabase:
                    # 1. binance_spot_weekly 로드
                    weekly_response = supabase.table("binance_spot_weekly") \
                        .select("*") \
                        .eq("symbol", symbol) \
                        .gte("date", start_date) \
                        .lte("date", end_date) \
                        .order("date") \
                        .execute()
                    
                    if not weekly_response.data or len(weekly_response.data) == 0:
                        return pd.DataFrame()
                    
                    df = pd.DataFrame(weekly_response.data)
                    df['date'] = pd.to_datetime(df['date'])
                    
                    # 2. bitinfocharts_whale_weekly 병합
                    whale_weekly_response = supabase.table("bitinfocharts_whale_weekly") \
                        .select("*") \
                        .eq("coin", coin_label) \
                        .gte("week_end_date", start_date) \
                        .lte("week_end_date", end_date) \
                        .order("week_end_date") \
                        .execute()
                    
                    if whale_weekly_response.data and len(whale_weekly_response.data) > 0:
                        whale_df = pd.DataFrame(whale_weekly_response.data)
                        whale_df['date'] = pd.to_datetime(whale_df['week_end_date'])
                        df = pd.merge(df, whale_df[['date', 'avg_top100_richest_pct', 'avg_transaction_value_btc', 'whale_conc_change_7d']], 
                                    on='date', how='left')
                        df = df.rename(columns={
                            'avg_top100_richest_pct': 'top100_richest_pct',
                            'avg_transaction_value_btc': 'avg_transaction_value_btc'
                        })
                    
                    # 3. binance_futures_weekly 병합 (있는 경우)
                    # 주의: 이 테이블이 Supabase에 없을 수 있음
                    try:
                        futures_weekly_response = supabase.table("binance_futures_weekly") \
                            .select("*") \
                            .eq("symbol", symbol) \
                            .gte("week_end_date", start_date) \
                            .lte("week_end_date", end_date) \
                            .order("week_end_date") \
                            .execute()
                        
                        if futures_weekly_response.data and len(futures_weekly_response.data) > 0:
                            futures_df = pd.DataFrame(futures_weekly_response.data)
                            futures_df['date'] = pd.to_datetime(futures_df['week_end_date'])
                            df = pd.merge(df, futures_df[['date', 'avg_funding_rate', 'sum_open_interest', 'oi_growth_7d', 'funding_rate_zscore']], 
                                        on='date', how='left')
                    except Exception as e:
                        logging.warning(f"binance_futures_weekly 테이블이 없거나 접근 불가: {e}")
                    
                    # 숫자 컬럼 변환
                    numeric_columns = [
                        'open', 'high', 'low', 'close', 'volume', 'quote_volume',
                        'atr', 'rsi', 'volatility_ratio', 'weekly_range_pct',
                        'top100_richest_pct', 'avg_transaction_value_btc', 'whale_conc_change_7d',
                        'avg_funding_rate', 'sum_open_interest', 'oi_growth_7d', 'funding_rate_zscore'
                    ]
                    for col in numeric_columns:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # 주봉 특성 추가 계산
                    if 'close' in df.columns:
                        df['weekly_return'] = df['close'].pct_change()
                    if 'high' in df.columns and 'low' in df.columns:
                        df['high_low_range'] = (df['high'] - df['low']) / df['low']
                    
                    # 실제 고변동성 타겟 변수 계산
                    if 'volatility_ratio' in df.columns:
                        df['next_week_volatility'] = df['volatility_ratio'].shift(-1)
                        if df['volatility_ratio'].max() > 0:
                            quantile_threshold = df['volatility_ratio'].quantile(0.7)
                            absolute_threshold = df['volatility_ratio'].median() * 1.5
                            df['target_high_vol'] = (
                                (df['next_week_volatility'] > quantile_threshold) | 
                                (df['next_week_volatility'] > absolute_threshold)
                            ).astype(int)
                        else:
                            df['target_high_vol'] = 0
                        df['target_high_vol'] = df['target_high_vol'].fillna(0).astype(int)
                    
                    # 결측치 처리
                    df = df.ffill().bfill()
                    
                    return df
            except Exception as e:
                logging.warning(f"Supabase에서 주봉 데이터 로드 실패, SQLite로 폴백: {e}")
                # SQLite로 폴백
        
        # SQLite 사용 (로컬 환경 또는 Supabase 실패 시)
        try:
            if not hasattr(self, 'conn') or self.conn is None:
                logging.error("데이터베이스 연결이 없습니다")
                return pd.DataFrame()
            
            # 주봉 OHLCV + 주간 고래 데이터 + 주간 선물 데이터 JOIN
            query = f"""
            SELECT 
                w.date,
                w.symbol,
                w.open,
                w.high,
                w.low,
                w.close,
                w.volume,
                w.quote_volume,
                w.atr,
                w.rsi,
                w.volatility_ratio,
                w.weekly_range_pct,
                wh.avg_top100_richest_pct as top100_richest_pct,
                wh.avg_transaction_value_btc as avg_transaction_value_btc,
                wh.whale_conc_change_7d,
                fw.avg_funding_rate,
                fw.sum_open_interest,
                fw.oi_growth_7d,
                fw.funding_rate_zscore
            FROM binance_spot_weekly w
            LEFT JOIN bitinfocharts_whale_weekly wh 
                ON w.date = wh.week_end_date AND wh.coin = '{coin_label}'
            LEFT JOIN binance_futures_weekly fw
                ON w.date = fw.week_end_date AND fw.symbol = '{symbol}'
            WHERE w.symbol = '{symbol}'
            AND w.date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY w.date
            """
            
            df = pd.read_sql(query, self.conn)
            
            if len(df) == 0:
                return df
            
            df['date'] = pd.to_datetime(df['date'])
            
            # 숫자 컬럼을 명시적으로 float로 변환
            numeric_columns = [
                'open', 'high', 'low', 'close', 'volume', 'quote_volume',
                'atr', 'rsi', 'volatility_ratio', 'weekly_range_pct',
                'top100_richest_pct', 'avg_transaction_value_btc', 'whale_conc_change_7d',
                'avg_funding_rate', 'sum_open_interest', 'oi_growth_7d', 'funding_rate_zscore'
            ]
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 주봉 특성 추가 계산
            df['weekly_return'] = df['close'].pct_change()
            df['high_low_range'] = (df['high'] - df['low']) / df['low']
            
            # 실제 고변동성 타겟 변수 계산 (주봉에 맞게 개선)
            # 다음 주의 변동성을 기준으로 고변동성 여부 판단
            df['next_week_volatility'] = df['volatility_ratio'].shift(-1)
            
            # 주봉은 일봉보다 변동성이 평활화되므로 임계값을 낮춤
            if df['volatility_ratio'].max() > 0:
                # 상위 30%로 조정 (일봉은 20%, 주봉은 더 넓게)
                quantile_threshold = df['volatility_ratio'].quantile(0.7)
                # 절대 임계값: 중앙값의 1.5배 (주봉 특성 반영)
                absolute_threshold = df['volatility_ratio'].median() * 1.5
                
                # 두 조건 중 하나라도 만족하면 고변동성
                df['target_high_vol'] = (
                    (df['next_week_volatility'] > quantile_threshold) | 
                    (df['next_week_volatility'] > absolute_threshold)
                ).astype(int)
            else:
                df['target_high_vol'] = 0
            
            df['target_high_vol'] = df['target_high_vol'].fillna(0).astype(int)
            
            # 결측치 처리
            df = df.ffill().bfill()
            
            return df
            
        except sqlite3.Error as e:
            error_msg = f"SQL 오류 (load_risk_data_weekly): {str(e)}"
            logging.error(error_msg)
            return pd.DataFrame()
        except Exception as e:
            error_msg = f"load_risk_data_weekly 오류: {str(e)}"
            logging.error(error_msg)
            return pd.DataFrame()
