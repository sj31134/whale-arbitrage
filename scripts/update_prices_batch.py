#!/usr/bin/env python3
"""
가격 업데이트 배치 작업 스크립트
실시간 수집 시 가격 조회 실패한 거래들의 가격을 보완
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 환경변수 로드
load_dotenv(PROJECT_ROOT / 'config' / '.env')

from src.utils.logger import logger
from src.database.supabase_client import get_supabase_client
from src.utils.price_updater import PriceUpdater

def main():
    """메인 실행 함수"""
    try:
        logger.info("=" * 60)
        logger.info("💰 가격 업데이트 배치 작업 시작")
        logger.info("=" * 60)
        
        # Supabase 클라이언트 초기화
        supabase = get_supabase_client()
        
        # 체인별로 처리
        chains = ['ethereum', 'polygon']
        
        total_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
        
        for chain in chains:
            logger.info(f"\n📊 {chain.upper()} 체인 처리 중...")
            
            # Price Updater 초기화
            updater = PriceUpdater(chain=chain)
            
            # 가격이 없는 거래 조회 (최대 1000건씩)
            transactions_df = supabase.get_transactions_without_price(limit=1000, chain=chain)
            
            if transactions_df.empty:
                logger.info(f"   ✅ {chain.upper()} 체인: 가격 없는 거래 없음")
                continue
            
            # DataFrame을 리스트로 변환
            transactions = transactions_df.to_dict('records')
            
            logger.info(f"   📋 {len(transactions)}건의 거래 발견 (가격 업데이트 필요)")
            
            # 배치 업데이트 실행
            stats = updater.update_batch(
                supabase_client=supabase,
                transactions=transactions,
                batch_size=50,  # 50건씩 배치 처리
                delay=0.5  # 배치 간 0.5초 대기
            )
            
            # 전체 통계 업데이트
            total_stats['total'] += stats['total']
            total_stats['success'] += stats['success']
            total_stats['failed'] += stats['failed']
            total_stats['skipped'] += stats['skipped']
        
        # 전체 결과 요약
        logger.info("\n" + "=" * 60)
        logger.info("✅ 배치 가격 업데이트 완료")
        logger.info("=" * 60)
        logger.info(f"   총 처리: {total_stats['total']}건")
        logger.info(f"   ✅ 성공: {total_stats['success']}건")
        logger.info(f"   ❌ 실패: {total_stats['failed']}건")
        logger.info(f"   ⏭️ 건너뛰기: {total_stats['skipped']}건")
        
        if total_stats['success'] > 0:
            logger.info(f"\n💡 {total_stats['success']}건의 거래 가격이 업데이트되었습니다!")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ 배치 작업 중단됨")
    except Exception as e:
        logger.error(f"\n❌ 배치 작업 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
