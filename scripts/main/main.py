# main.py

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

# 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 환경변수 로드
load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 모듈 import
from src.utils.logger import logger
from src.collectors.block_explorer_collector import BlockExplorerCollector
from src.database.supabase_client import get_supabase_client
from src.utils.label_manager import load_labels, get_label

def main():
    """
    메인 실행 함수
    
    1. Etherscan에서 고래 거래 수집
    2. 데이터 정제 (가격 조회: Chainlink → Uniswap → 1inch)
    3. 함수 시그니처 디코딩 (4byte.directory)
    4. 라벨링 (GitHub 데이터셋 통합)
    5. Supabase에 저장
    """
    
    logger.info("=" * 60)
    logger.info("🐋 고래 거래 추적 시스템 시작")
    logger.info("=" * 60)
    
    # 가격 소스 상태 확인
    logger.info("\n💰 가격 조회 소스 상태:")
    try:
        from src.collectors.block_explorer_collector import (
            CHAINLINK_AVAILABLE, UNISWAP_AVAILABLE, ONEINCH_AVAILABLE
        )
        logger.info(f"   Chainlink: {'✅' if CHAINLINK_AVAILABLE else '❌'}")
        logger.info(f"   Uniswap V3: {'✅' if UNISWAP_AVAILABLE else '❌'}")
        logger.info(f"   1inch API: {'✅' if ONEINCH_AVAILABLE else '❌'}")
        
        if not CHAINLINK_AVAILABLE:
            logger.warning("   ⚠️ Chainlink 사용 불가 - ETH 가격은 기본값 사용")
        if not UNISWAP_AVAILABLE:
            logger.warning("   ⚠️ Uniswap 사용 불가 - 토큰 가격 조회 제한적")
    except Exception as e:
        logger.debug(f"   가격 소스 확인 중 오류: {e}")
    
    try:
        # ============================================
        # Step 0: 지갑 라벨 데이터 로드
        # ============================================
        logger.info("\n📝 Step 0: 지갑 라벨 데이터 로드")
        wallet_labels = load_labels()
        
        # ============================================
        # Step 1: 블록 탐색기 수집기 초기화 (멀티체인)
        # ============================================
        logger.info("\n📝 Step 1: 블록 탐색기 수집기 초기화")
        eth_collector = BlockExplorerCollector(chain='ethereum')
        polygon_collector = BlockExplorerCollector(chain='polygon')
        
        # ============================================
        # Step 2: 알려진 고래 지갑 정의
        # ============================================
        logger.info("\n📝 Step 2: 고래 지갑 정의")
        
        # 주요 거래소 및 알려진 고래 지갑
        whale_addresses = [
            # Binance (주요 거래소)
            '0x28C6c06298d514Db089934071355E5743bf21d60',  # Binance Hot Wallet
            '0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549',  # Binance 2
            '0xd0d4a7b5f85fea4944bd07e28daef65b8fa47248',  # Binance 3
            
            # Coinbase
            '0x71C7656EC7ab88b098defB751B7401B5f6d8976F',  # Coinbase
            
            # Kraken
            '0x2910543af39aba0cd09dbb2d50200b3e800a63d2',  # Kraken
            
            # 알려진 개인 고래 (OpenSea, Raydium 등)
            '0xf0d4c12b5454c1381b9df11d05de5bbfb3b7e4f7',  # Raydium
        ]
        
        logger.info(f"   추적할 지갑: {len(whale_addresses)}개")
        
        # ============================================
        # Step 3: 이더리움 데이터 수집 (에러 처리 강화)
        # ============================================
        eth_transactions = []
        eth_token_transactions = []
        eth_internal_transactions = []
        
        logger.info("\n📝 Step 3-1: Ethereum - 네이티브 코인(ETH) 거래 데이터 수집")
        try:
            eth_transactions = eth_collector.collect_from_addresses(whale_addresses)
            logger.info(f"✅ Ethereum ETH 거래 {len(eth_transactions)}건 수집 완료")
        except Exception as e:
            logger.error(f"❌ Ethereum ETH 거래 수집 실패: {e}")
            logger.warning("   다음 단계 계속 진행...")
        
        logger.info("\n📝 Step 3-2: Ethereum - ERC-20 토큰 거래 데이터 수집")
        try:
            eth_token_transactions = eth_collector.collect_token_transactions_from_addresses(whale_addresses)
            logger.info(f"✅ Ethereum 토큰 거래 {len(eth_token_transactions)}건 수집 완료")
        except Exception as e:
            logger.error(f"❌ Ethereum 토큰 거래 수집 실패: {e}")
            logger.warning("   다음 단계 계속 진행...")
        
        logger.info("\n📝 Step 3-3: Ethereum - 내부 거래 데이터 수집")
        try:
            eth_internal_transactions = eth_collector.collect_internal_transactions_from_addresses(whale_addresses)
            logger.info(f"✅ Ethereum 내부 거래 {len(eth_internal_transactions)}건 수집 완료")
        except Exception as e:
            logger.error(f"❌ Ethereum 내부 거래 수집 실패: {e}")
            logger.warning("   다음 단계 계속 진행...")
        
        # ============================================
        # Step 4: Polygon 데이터 수집 (에러 처리 강화)
        # ============================================
        polygon_transactions = []
        polygon_token_transactions = []
        polygon_internal_transactions = []
        
        logger.info("\n📝 Step 4-1: Polygon - 네이티브 코인(MATIC) 거래 데이터 수집")
        try:
            polygon_transactions = polygon_collector.collect_from_addresses(whale_addresses)
            logger.info(f"✅ Polygon MATIC 거래 {len(polygon_transactions)}건 수집 완료")
        except Exception as e:
            logger.error(f"❌ Polygon MATIC 거래 수집 실패: {e}")
            logger.warning("   다음 단계 계속 진행...")
        
        logger.info("\n📝 Step 4-2: Polygon - ERC-20 토큰 거래 데이터 수집")
        try:
            polygon_token_transactions = polygon_collector.collect_token_transactions_from_addresses(whale_addresses)
            logger.info(f"✅ Polygon 토큰 거래 {len(polygon_token_transactions)}건 수집 완료")
        except Exception as e:
            logger.error(f"❌ Polygon 토큰 거래 수집 실패: {e}")
            logger.warning("   다음 단계 계속 진행...")
        
        logger.info("\n📝 Step 4-3: Polygon - 내부 거래 데이터 수집")
        try:
            polygon_internal_transactions = polygon_collector.collect_internal_transactions_from_addresses(whale_addresses)
            logger.info(f"✅ Polygon 내부 거래 {len(polygon_internal_transactions)}건 수집 완료")
        except Exception as e:
            logger.error(f"❌ Polygon 내부 거래 수집 실패: {e}")
            logger.warning("   다음 단계 계속 진행...")
        
        # 모든 거래 합치기 (이더리움 + 폴리곤)
        all_transactions = eth_transactions + eth_token_transactions + polygon_transactions + polygon_token_transactions
        all_internal_transactions = eth_internal_transactions + polygon_internal_transactions
        
        if not all_transactions:
            logger.warning("⚠️ 수집된 거래가 없습니다")
            return
        
        logger.info(f"✅ 총 {len(all_transactions)}건 수집 완료")
        logger.info(f"   - Ethereum: {len(eth_transactions) + len(eth_token_transactions)}건")
        logger.info(f"   - Polygon: {len(polygon_transactions) + len(polygon_token_transactions)}건")
        
        # ============================================
        # Step 5: 데이터 정제 및 필터링
        # ============================================
        logger.info("\n📝 Step 5: 데이터 정제 및 필터링")
        
        # 거래 필터링 (고래 기준) - 이더리움 수집기 기준 사용 (동일한 기준)
        filtered_transactions = eth_collector.filter_transactions(
            all_transactions,
            min_amount_usd=50000  # $50K 이상만
        )
        
        logger.info(f"✅ {len(filtered_transactions)}건 필터링 완료")
        
        # ============================================
        # Step 6: 데이터 미리보기
        # ============================================
        logger.info("\n📝 Step 6: 수집된 데이터 미리보기")
        
        if filtered_transactions:
            df = pd.DataFrame(filtered_transactions)
            
            if not df.empty:
                # 필요한 컬럼 확인
                display_columns = ['tx_hash', 'from_address', 'to_address', 
                                   'coin_symbol', 'amount', 'amount_usd', 'whale_category']
                available_columns = [col for col in display_columns if col in df.columns]
                
                if available_columns:
                    logger.info("\n📊 데이터 샘플 (상위 3건):")
                    logger.info("\n" + df[available_columns].head(3).to_string())
                
                # 통계 정보 출력
                logger.info("\n📈 거래 통계:")
                if 'amount_usd' in df.columns and len(df) > 0:
                    # None 값을 제외하고 계산
                    amount_usd_series = df['amount_usd'].dropna()
                    if len(amount_usd_series) > 0:
                        logger.info(f"   총 거래액 (가격 있는 거래): ${amount_usd_series.sum():,.0f}")
                        logger.info(f"   평균 거래 (가격 있는 거래): ${amount_usd_series.mean():,.0f}")
                        logger.info(f"   가격 없는 거래: {len(df[df['amount_usd'].isna()])}건 (나중에 업데이트 예정)")
                    else:
                        logger.info("   모든 거래의 가격 정보가 없음 (나중에 업데이트 예정)")
                
                if 'whale_category' in df.columns:
                    logger.info(f"   메가 고래: {len(df[df['whale_category'] == 'MEGA_WHALE'])}건")
                    logger.info(f"   라지 고래: {len(df[df['whale_category'] == 'LARGE_WHALE'])}건")
                    logger.info(f"   일반 고래: {len(df[df['whale_category'] == 'WHALE'])}건")
                    logger.info(f"   가격 없음: {len(df[df['whale_category'].isna()])}건 (나중에 업데이트 예정)")
                
                # 토큰별 통계
                if 'coin_symbol' in df.columns:
                    token_counts = df['coin_symbol'].value_counts()
                    logger.info(f"\n📊 토큰별 거래 건수:")
                    for symbol, count in token_counts.head(10).items():
                        logger.info(f"   {symbol}: {count}건")
            else:
                logger.warning("⚠️ 데이터 프레임이 비어있습니다")
        
        # ============================================
        # Step 6: 거래 데이터에 라벨 추가
        # ============================================
        logger.info("\n📝 Step 6: 거래 데이터에 지갑 라벨 추가")
        
        # 일반 거래에 라벨 추가
        for tx in filtered_transactions:
            from_addr = tx.get('from_address', '')
            to_addr = tx.get('to_address', '')
            
            if from_addr:
                from_label = get_label(from_addr, wallet_labels)
                if from_label:
                    tx['from_label'] = from_label
                else:
                    tx['from_label'] = None
            
            if to_addr:
                to_label = get_label(to_addr, wallet_labels)
                if to_label:
                    tx['to_label'] = to_label
                else:
                    tx['to_label'] = None
        
        # 라벨이 추가된 거래 수 집계
        labeled_count = sum(1 for tx in filtered_transactions 
                          if tx.get('from_label') or tx.get('to_label'))
        logger.info(f"✅ {labeled_count}건의 거래에 라벨 추가 완료")
        
        # ============================================
        # Step 7: Supabase에 저장 (에러 처리 강화)
        # ============================================
        logger.info("\n📝 Step 7: Supabase에 데이터 저장")
        
        supabase = get_supabase_client()
        inserted_count = 0
        internal_inserted_count = 0
        
        # 일반 거래 저장
        try:
            if filtered_transactions:
                inserted_count = supabase.insert_transactions(filtered_transactions)
                logger.info(f"✅ {inserted_count}건 Supabase에 저장 완료")
            else:
                logger.warning("⚠️ 저장할 거래가 없습니다")
        except Exception as e:
            logger.error(f"❌ 거래 저장 실패: {e}")
            logger.warning("   내부 거래 저장 계속 진행...")
        
        # 내부 거래 저장
        try:
            if all_internal_transactions:
                logger.info("\n📝 내부 거래를 Supabase에 저장 중...")
                internal_inserted_count = supabase.insert_internal_transactions(all_internal_transactions)
                logger.info(f"✅ {internal_inserted_count}건의 내부 거래 Supabase에 저장 완료")
            else:
                logger.info("ℹ️ 저장할 내부 거래가 없습니다")
        except Exception as e:
            logger.error(f"❌ 내부 거래 저장 실패: {e}")
            logger.warning("   저장 단계는 완료했지만 일부 실패했을 수 있습니다.")
        
        # ============================================
        # Step 8: 저장된 데이터 확인
        # ============================================
        logger.info("\n📝 Step 8: 저장된 데이터 확인")
        
        recent_df = supabase.get_recent_transactions(hours=24, limit=5)
        
        if not recent_df.empty:
            logger.info("\n📊 최근 저장된 거래 (상위 5건):")
            # 컬럼 존재 확인
            display_columns = ['tx_hash', 'coin_symbol', 'amount', 'amount_usd', 'whale_category']
            available_columns = [col for col in display_columns if col in recent_df.columns]
            
            if available_columns:
                logger.info("\n" + recent_df[available_columns].to_string())
            else:
                logger.warning("⚠️ 표시할 컬럼이 없습니다")
        
        # ============================================
        # 완료
        # ============================================
        logger.info("\n" + "=" * 60)
        logger.info("✅ 모든 작업 완료!")
        logger.info("=" * 60 + "\n")
    
    except KeyboardInterrupt:
        logger.warning("\n⚠️ 사용자에 의해 중단되었습니다")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ 치명적 오류 발생: {e}")
        import traceback
        logger.error("\n상세 오류 정보:")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()
