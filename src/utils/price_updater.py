"""
가격 업데이트 배치 작업
실시간 수집 시 가격 조회 실패한 거래들의 가격을 나중에 보완
"""

import time
from typing import List, Dict, Optional
from src.utils.logger import logger
from src.collectors.block_explorer_collector import BlockExplorerCollector

class PriceUpdater:
    """가격 업데이트 배치 처리"""
    
    def __init__(self, chain: str = 'ethereum'):
        """
        Price Updater 초기화
        
        Parameters:
        -----------
        chain : str
            체인 이름 ('ethereum' 또는 'polygon')
        """
        self.chain = chain
        self.collector = BlockExplorerCollector(chain=chain)
    
    def calculate_price_for_transaction(self, tx: Dict) -> Optional[float]:
        """
        거래의 USD 가격 계산
        
        Parameters:
        -----------
        tx : Dict
            거래 데이터 (Supabase에서 조회한 데이터)
        
        Returns:
        --------
        Optional[float] : USD 가격, 실패 시 None
        """
        try:
            coin_symbol = tx.get('coin_symbol', '').upper()
            contract_address = tx.get('contract_address')
            amount = float(tx.get('amount', 0))
            
            if amount <= 0:
                return None
            
            # 네이티브 코인 (ETH, MATIC)인 경우
            if coin_symbol in ['ETH', 'MATIC']:
                # Chainlink로 가격 조회
                eth_price = self.collector._get_eth_to_usd_rate()
                amount_usd = amount * eth_price
                return amount_usd
            
            # ERC-20 토큰인 경우
            elif contract_address:
                # Uniswap/1inch로 토큰 가격 조회
                token_price = self.collector._get_token_price_usd(
                    token_address=contract_address,
                    token_symbol=coin_symbol
                )
                
                if token_price and token_price > 0:
                    amount_usd = amount * token_price
                    return amount_usd
            
            return None
            
        except Exception as e:
            logger.debug(f"⚠️ 가격 계산 실패 ({tx.get('tx_hash', 'unknown')[:10]}...): {e}")
            return None
    
    def update_transaction_price(self, supabase_client, tx: Dict, amount_usd: float) -> bool:
        """
        거래의 가격 정보 업데이트
        
        Parameters:
        -----------
        supabase_client : SupabaseClient
            Supabase 클라이언트 인스턴스
        tx : Dict
            거래 데이터
        amount_usd : float
            계산된 USD 가격
        
        Returns:
        --------
        bool : 성공 여부
        """
        try:
            tx_hash = tx.get('tx_hash')
            if not tx_hash:
                return False
            
            # 고래 분류 재계산
            whale_category = self.collector._classify_whale(amount_usd)
            
            # 업데이트 데이터
            update_data = {
                'amount_usd': amount_usd,
                'whale_category': whale_category
            }
            
            # Supabase 업데이트
            response = supabase_client.client.table('whale_transactions').update(
                update_data
            ).eq('tx_hash', tx_hash).execute()
            
            if response.data:
                logger.debug(f"✅ {tx_hash[:10]}... 가격 업데이트: ${amount_usd:,.2f} ({whale_category})")
                return True
            else:
                logger.debug(f"⚠️ 업데이트 실패 (데이터 없음): {tx_hash[:10]}...")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ 가격 업데이트 실패 ({tx.get('tx_hash', 'unknown')[:10]}...): {e}")
            return False
    
    def update_batch(self, supabase_client, transactions: List[Dict], 
                    batch_size: int = 50, delay: float = 0.5) -> Dict[str, int]:
        """
        배치로 거래 가격 업데이트
        
        Parameters:
        -----------
        supabase_client : SupabaseClient
            Supabase 클라이언트 인스턴스
        transactions : List[Dict]
            업데이트할 거래 목록
        batch_size : int
            배치 크기 (기본값: 50)
        delay : float
            배치 간 대기 시간 (초, 기본값: 0.5)
        
        Returns:
        --------
        Dict[str, int] : {
            'total': 전체 거래 수,
            'success': 성공한 거래 수,
            'failed': 실패한 거래 수,
            'skipped': 건너뛴 거래 수 (가격 조회 실패)
        }
        """
        stats = {
            'total': len(transactions),
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
        logger.info(f"\n📊 배치 가격 업데이트 시작: {stats['total']}건")
        
        for i, tx in enumerate(transactions, 1):
            try:
                # 가격 계산
                amount_usd = self.calculate_price_for_transaction(tx)
                
                if amount_usd and amount_usd > 0:
                    # 가격 업데이트
                    if self.update_transaction_price(supabase_client, tx, amount_usd):
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1
                else:
                    stats['skipped'] += 1
                    logger.debug(f"⏭️ {tx.get('tx_hash', 'unknown')[:10]}... 가격 조회 실패 (건너뛰기)")
                
                # 배치 간 대기 (Rate Limit 방지)
                if i % batch_size == 0:
                    logger.info(f"   진행 상황: {i}/{stats['total']}건 완료 (성공: {stats['success']}, 실패: {stats['failed']}, 건너뛰기: {stats['skipped']})")
                    if i < stats['total']:
                        time.sleep(delay)
                        
            except Exception as e:
                logger.warning(f"⚠️ 거래 처리 실패 ({tx.get('tx_hash', 'unknown')[:10]}...): {e}")
                stats['failed'] += 1
        
        logger.info(f"\n✅ 배치 업데이트 완료:")
        logger.info(f"   총 {stats['total']}건 중")
        logger.info(f"   ✅ 성공: {stats['success']}건")
        logger.info(f"   ❌ 실패: {stats['failed']}건")
        logger.info(f"   ⏭️ 건너뛰기: {stats['skipped']}건")
        
        return stats
