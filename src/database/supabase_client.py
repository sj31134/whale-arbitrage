# src/database/supabase_client.py

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import List, Dict, Any, Optional
import pandas as pd
from src.utils.logger import logger

# 환경변수 로드
load_dotenv('config/.env')

class SupabaseClient:
    """Supabase 데이터베이스 클라이언트"""
    
    def __init__(self):
        """Supabase 클라이언트 초기화"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
        
        # Supabase 클라이언트 생성
        self.client: Client = create_client(self.url, self.key)
        logger.info("✅ Supabase 클라이언트 연결 성공")
    
    def insert_transactions(self, transactions: List[Dict[str, Any]]) -> int:
        """
        고래 거래 데이터 삽입
        
        Parameters:
        -----------
        transactions : List[Dict]
            삽입할 거래 데이터 리스트
        
        Returns:
        --------
        int : 성공적으로 삽입된 행의 수
        """
        if not transactions:
            logger.warning("⚠️ 삽입할 거래 데이터가 없습니다")
            return 0
        
        # 중복 제거 (tx_hash 기준)
        unique_hashes = set()
        unique_transactions = []
        
        for tx in transactions:
            if tx['tx_hash'] not in unique_hashes:
                unique_hashes.add(tx['tx_hash'])
                unique_transactions.append(tx)
        
        if not unique_transactions:
            logger.warning("⚠️ 삽입할 고유한 거래가 없습니다")
            return 0
        
        try:
            logger.info(f"📤 {len(unique_transactions)}건의 거래를 Supabase에 삽입 중...")
            
            # Supabase에 삽입 (중복 시 업데이트)
            # Supabase Python 클라이언트의 upsert는 기본적으로 모든 컬럼에 대해 중복 체크
            response = self.client.table('whale_transactions').upsert(
                unique_transactions
            ).execute()
            
            # 실제 삽입된 데이터 확인
            if hasattr(response, 'data') and response.data:
                inserted_count = len(response.data)
            else:
                # response.data가 없으면 unique_transactions 수를 사용
                inserted_count = len(unique_transactions)
            
            logger.info(f"✅ {inserted_count}건의 거래 삽입 완료")
            
            return inserted_count
            
        except Exception as e:
            logger.error(f"❌ 데이터 삽입 실패: {e}")
            logger.error(f"📋 에러 타입: {type(e).__name__}")
            
            # 첫 번째 거래의 구조를 로깅하여 디버깅 용이하게
            if unique_transactions:
                logger.warning(f"📋 샘플 데이터 구조: {list(unique_transactions[0].keys())}")
                logger.warning(f"📋 첫 번째 거래 타입 확인: block_timestamp={type(unique_transactions[0].get('block_timestamp'))}")
                # block_timestamp가 datetime 객체인 경우 확인
                block_ts = unique_transactions[0].get('block_timestamp')
                if hasattr(block_ts, 'isoformat'):
                    logger.warning(f"⚠️ block_timestamp가 datetime 객체입니다! ISO 문자열로 변환해야 합니다.")
            
            return 0
    
    def insert_internal_transactions(self, transactions: List[Dict[str, Any]]) -> int:
        """
        내부 거래(Internal Transactions) 데이터 삽입
        
        Parameters:
        -----------
        transactions : List[Dict]
            삽입할 내부 거래 데이터 리스트
        
        Returns:
        --------
        int : 성공적으로 삽입된 행의 수
        """
        if not transactions:
            logger.warning("⚠️ 삽입할 내부 거래 데이터가 없습니다")
            return 0
        
        # 중복 제거 (tx_hash + trace_id 조합 기준)
        # 같은 트랜잭션 해시 내에서 여러 내부 거래가 있을 수 있으므로 trace_id도 고려
        unique_keys = set()
        unique_transactions = []
        
        for tx in transactions:
            # tx_hash와 trace_id 조합으로 고유 키 생성
            key = f"{tx['tx_hash']}_{tx.get('trace_id', '')}"
            if key not in unique_keys:
                unique_keys.add(key)
                unique_transactions.append(tx)
        
        if not unique_transactions:
            logger.warning("⚠️ 삽입할 고유한 내부 거래가 없습니다")
            return 0
        
        try:
            logger.info(f"📤 {len(unique_transactions)}건의 내부 거래를 Supabase에 삽입 중...")
            
            # Supabase에 삽입 (중복 시 업데이트)
            # tx_hash와 trace_id 조합이 고유 키가 되도록 설정 필요
            response = self.client.table('internal_transactions').upsert(
                unique_transactions
            ).execute()
            
            # 실제 삽입된 데이터 확인
            if hasattr(response, 'data') and response.data:
                inserted_count = len(response.data)
            else:
                inserted_count = len(unique_transactions)
            
            logger.info(f"✅ {inserted_count}건의 내부 거래 삽입 완료")
            
            return inserted_count
            
        except Exception as e:
            logger.error(f"❌ 내부 거래 데이터 삽입 실패: {e}")
            logger.error(f"📋 에러 타입: {type(e).__name__}")
            
            # 첫 번째 거래의 구조를 로깅하여 디버깅 용이하게
            if unique_transactions:
                logger.warning(f"📋 샘플 데이터 구조: {list(unique_transactions[0].keys())}")
                logger.warning(f"📋 첫 번째 내부 거래 타입 확인: block_timestamp={type(unique_transactions[0].get('block_timestamp'))}")
            
            return 0
    
    def get_recent_transactions(self, hours: int = 24, limit: int = 100) -> pd.DataFrame:
        """
        최근 거래 조회
        
        Parameters:
        -----------
        hours : int
            조회 시간 범위 (기본값: 24시간)
        limit : int
            조회 건수 (기본값: 100)
        
        Returns:
        --------
        pd.DataFrame : 거래 데이터
        """
        try:
            response = self.client.table('whale_transactions').select('*').order(
                'block_timestamp',
                desc=True
            ).limit(limit).execute()
            
            data = response.data
            df = pd.DataFrame(data)
            
            logger.info(f"✅ {len(df)}건의 거래 조회 완료")
            return df
            
        except Exception as e:
            logger.error(f"❌ 거래 조회 실패: {e}")
            return pd.DataFrame()
    
    def get_wallet_transactions(self, address: str, limit: int = 100) -> pd.DataFrame:
        """
        특정 지갑의 거래 조회
        
        Parameters:
        -----------
        address : str
            지갑 주소 (0x로 시작)
        limit : int
            조회 건수
        
        Returns:
        --------
        pd.DataFrame : 거래 데이터
        """
        try:
            response = self.client.table('whale_transactions').select('*').or_(
                f"from_address.eq.{address},to_address.eq.{address}"
            ).order('block_timestamp', desc=True).limit(limit).execute()
            
            data = response.data
            df = pd.DataFrame(data)
            
            logger.info(f"✅ {address[:10]}...의 {len(df)}건 거래 조회 완료")
            return df
            
        except Exception as e:
            logger.error(f"❌ 지갑 거래 조회 실패: {e}")
            return pd.DataFrame()
    
    def get_transactions_without_price(self, limit: int = 1000, chain: Optional[str] = None) -> pd.DataFrame:
        """
        가격이 없는 거래 조회 (배치 가격 업데이트용)
        
        Parameters:
        -----------
        limit : int
            조회 건수 (기본값: 1000)
        chain : Optional[str]
            체인 필터 (None이면 모든 체인)
        
        Returns:
        --------
        pd.DataFrame : 가격이 없는 거래 데이터
        """
        try:
            query = self.client.table('whale_transactions').select('*')
            
            # 가격이 없는 거래만 조회 (amount_usd IS NULL 또는 0)
            query = query.is_('amount_usd', 'null')
            
            # 체인 필터
            if chain:
                query = query.eq('chain', chain.lower())
            
            # 최신순으로 정렬
            query = query.order('block_timestamp', desc=True).limit(limit)
            
            response = query.execute()
            data = response.data
            df = pd.DataFrame(data)
            
            logger.info(f"✅ 가격 없는 거래 {len(df)}건 조회 완료")
            return df
            
        except Exception as e:
            logger.error(f"❌ 가격 없는 거래 조회 실패: {e}")
            return pd.DataFrame()
    
    def get_whale_statistics(self) -> Dict[str, Any]:
        """
        고래 거래 통계 조회
        
        Returns:
        --------
        Dict : 통계 정보
        """
        try:
            # 전체 거래 수
            all_data = self.client.table('whale_transactions').select('*').execute()
            total_transactions = len(all_data.data)
            
            # 고래별 거래
            whale_data = self.client.table('whale_transactions').select('*').eq(
                'is_whale', True
            ).execute()
            total_whales = len(whale_data.data)
            
            stats = {
                'total_transactions': total_transactions,
                'total_whale_transactions': total_whales,
                'whale_percentage': (total_whales / total_transactions * 100) if total_transactions > 0 else 0
            }
            
            logger.info(f"✅ 통계 조회 완료: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ 통계 조회 실패: {e}")
            return {}

# 글로벌 클라이언트 인스턴스
supabase_client = None

def get_supabase_client() -> SupabaseClient:
    """싱글톤 패턴으로 Supabase 클라이언트 반환"""
    global supabase_client
    if supabase_client is None:
        supabase_client = SupabaseClient()
    return supabase_client
