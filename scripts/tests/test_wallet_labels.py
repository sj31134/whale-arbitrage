# test_wallet_labels.py
# 지갑 라벨링 기능 빠른 테스트

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
from src.utils.label_manager import load_labels, get_label

def test_wallet_labels():
    """지갑 라벨링 기능 테스트"""
    
    logger.info("=" * 60)
    logger.info("🧪 지갑 라벨링 기능 테스트")
    logger.info("=" * 60)
    
    try:
        # 라벨 로드
        logger.info("\n📝 라벨 데이터 로드")
        wallet_labels = load_labels()
        
        if not wallet_labels:
            logger.warning("⚠️ 로드된 라벨이 없습니다. config/wallet_labels.csv 파일을 확인하세요.")
            return
        
        # 테스트 주소들
        test_addresses = [
            '0x28C6c06298d514Db089934071355E5743bf21d60',  # Binance Hot Wallet
            '0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549',  # Binance 2
            '0x71C7656EC7ab88b098defB751B7401B5f6d8976F',  # Coinbase
            '0x0000000000000000000000000000000000000000',  # 없는 주소
        ]
        
        logger.info("\n📊 라벨 조회 테스트:")
        for addr in test_addresses:
            label = get_label(addr, wallet_labels)
            if label:
                logger.info(f"   ✅ {addr[:20]}... → {label}")
            else:
                logger.info(f"   ❌ {addr[:20]}... → (라벨 없음)")
        
        # 샘플 거래 데이터에 라벨 추가 테스트
        logger.info("\n📊 거래 데이터 라벨링 테스트:")
        sample_transactions = [
            {
                'tx_hash': '0x123...',
                'from_address': '0x28C6c06298d514Db089934071355E5743bf21d60',
                'to_address': '0x71C7656EC7ab88b098defB751B7401B5f6d8976F',
                'amount': 100.0
            },
            {
                'tx_hash': '0x456...',
                'from_address': '0x0000000000000000000000000000000000000000',
                'to_address': '0x2910543af39aba0cd09dbb2d50200b3e800a63d2',
                'amount': 50.0
            }
        ]
        
        for tx in sample_transactions:
            from_addr = tx.get('from_address', '')
            to_addr = tx.get('to_address', '')
            
            if from_addr:
                from_label = get_label(from_addr, wallet_labels)
                tx['from_label'] = from_label
            
            if to_addr:
                to_label = get_label(to_addr, wallet_labels)
                tx['to_label'] = to_label
            
            logger.info(f"\n   거래: {tx['tx_hash']}")
            logger.info(f"   From: {from_addr[:20]}... → {tx.get('from_label', '(라벨 없음)')}")
            logger.info(f"   To: {to_addr[:20]}... → {tx.get('to_label', '(라벨 없음)')}")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 테스트 완료!")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"\n❌ 오류 발생: {e}")
        raise

if __name__ == '__main__':
    test_wallet_labels()

