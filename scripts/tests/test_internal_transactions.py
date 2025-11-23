# test_internal_transactions.py
# 내부 거래 수집 기능만 빠르게 테스트

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
from src.collectors.etherscan_collector import EtherscanCollector
from src.database.supabase_client import get_supabase_client

def test_internal_transactions():
    """내부 거래 수집 기능 테스트"""
    
    logger.info("=" * 60)
    logger.info("🧪 내부 거래 수집 기능 테스트")
    logger.info("=" * 60)
    
    try:
        # Etherscan 수집기 초기화
        logger.info("\n📝 Etherscan 수집기 초기화")
        collector = EtherscanCollector()
        
        # 테스트용 지갑 주소 (Binance Hot Wallet)
        test_address = '0x28C6c06298d514Db089934071355E5743bf21d60'
        
        logger.info(f"\n📝 내부 거래 수집 테스트 (주소: {test_address[:10]}...)")
        
        # 내부 거래 수집
        internal_transactions = collector.get_wallet_internal_transactions(test_address, offset=100)
        logger.info(f"\n✅ {len(internal_transactions)}건의 내부 거래 수집 완료")
        
        if internal_transactions:
            # 수집된 데이터 미리보기
            logger.info("\n📊 수집된 내부 거래 샘플 (상위 3건):")
            for i, tx in enumerate(internal_transactions[:3], 1):
                logger.info(f"\n[{i}] {tx.get('tx_hash', 'N/A')[:20]}...")
                logger.info(f"   From: {tx.get('from_address', 'N/A')[:20]}...")
                logger.info(f"   To: {tx.get('to_address', 'N/A')[:20]}..." if tx.get('to_address') else "   To: N/A")
                logger.info(f"   Value: {tx.get('value_eth', 0):.6f} ETH")
                logger.info(f"   Type: {tx.get('transaction_type', 'N/A')}")
                logger.info(f"   Trace ID: {tx.get('trace_id', 'N/A')}")
            
            # Supabase에 저장 테스트 (테이블이 있는 경우)
            logger.info("\n📝 Supabase에 저장 테스트")
            try:
                supabase = get_supabase_client()
                inserted_count = supabase.insert_internal_transactions(internal_transactions[:10])  # 10건만 테스트
                logger.info(f"✅ {inserted_count}건의 내부 거래 저장 완료")
            except Exception as e:
                logger.warning(f"⚠️ Supabase 저장 실패 (테이블이 없을 수 있습니다): {e}")
                logger.info("💡 internal_transactions_table_schema.md 파일의 SQL을 실행하여 테이블을 생성하세요.")
        else:
            logger.info("ℹ️ 수집된 내부 거래가 없습니다 (해당 주소에 type=call이고 isError=0인 내부 거래가 없을 수 있습니다)")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 테스트 완료!")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"\n❌ 오류 발생: {e}")
        raise

if __name__ == '__main__':
    test_internal_transactions()

