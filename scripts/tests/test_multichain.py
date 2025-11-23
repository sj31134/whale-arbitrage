# test_multichain.py
# 멀티체인 지원 기능 빠른 테스트

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 환경변수 로드
load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 모듈 import
from src.utils.logger import logger
from src.collectors.block_explorer_collector import BlockExplorerCollector

def test_multichain():
    """멀티체인 지원 기능 테스트"""
    
    logger.info("=" * 60)
    logger.info("🧪 멀티체인 지원 기능 테스트")
    logger.info("=" * 60)
    
    try:
        # Ethereum 수집기 초기화
        logger.info("\n📝 Step 1: Ethereum 수집기 초기화")
        eth_collector = BlockExplorerCollector(chain='ethereum')
        
        # Polygon 수집기 초기화
        logger.info("\n📝 Step 2: Polygon 수집기 초기화")
        polygon_collector = BlockExplorerCollector(chain='polygon')
        
        # 테스트용 주소 (Binance Hot Wallet)
        test_address = '0x28C6c06298d514Db089934071355E5743bf21d60'
        
        # Ethereum 거래 조회 테스트 (소량만)
        logger.info("\n📝 Step 3: Ethereum 거래 조회 테스트")
        eth_txs = eth_collector.get_wallet_transactions(test_address, offset=10)
        logger.info(f"✅ Ethereum: {len(eth_txs)}건 조회 완료")
        
        if eth_txs:
            logger.info(f"   샘플: {eth_txs[0].get('tx_hash', 'N/A')[:20]}...")
            logger.info(f"   Chain: {eth_txs[0].get('chain', 'N/A')}")
            logger.info(f"   Coin: {eth_txs[0].get('coin_symbol', 'N/A')}")
        
        # Polygon 거래 조회 테스트 (소량만)
        logger.info("\n📝 Step 4: Polygon 거래 조회 테스트")
        polygon_txs = polygon_collector.get_wallet_transactions(test_address, offset=10)
        logger.info(f"✅ Polygon: {len(polygon_txs)}건 조회 완료")
        
        if polygon_txs:
            logger.info(f"   샘플: {polygon_txs[0].get('tx_hash', 'N/A')[:20]}...")
            logger.info(f"   Chain: {polygon_txs[0].get('chain', 'N/A')}")
            logger.info(f"   Coin: {polygon_txs[0].get('coin_symbol', 'N/A')}")
        else:
            logger.info("   ℹ️ 해당 주소에 Polygon 거래가 없을 수 있습니다")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 테스트 완료!")
        logger.info("=" * 60)
        
        # 요약
        logger.info("\n📊 테스트 결과:")
        logger.info(f"   - Ethereum 수집기: 정상 초기화")
        logger.info(f"   - Polygon 수집기: 정상 초기화")
        logger.info(f"   - Ethereum 거래 조회: {len(eth_txs)}건")
        logger.info(f"   - Polygon 거래 조회: {len(polygon_txs)}건")
        logger.info("\n💡 모든 체인에서 동일한 ETHERSCAN_API_KEY를 사용합니다")
    
    except Exception as e:
        logger.error(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    test_multichain()

