#!/usr/bin/env python3
"""
GitHub 오픈소스 데이터셋 동기화 스크립트
거래소 주소, 토큰 컨트랙트 등을 자동으로 수집하여 wallet_labels.csv 업데이트
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.logger import logger
from src.utils.github_dataset_loader import sync_github_datasets

def main():
    """메인 실행 함수"""
    try:
        logger.info("🚀 GitHub 데이터셋 동기화 시작")
        
        # 데이터셋 동기화 (CSV 파일 자동 업데이트)
        labels = sync_github_datasets(update_csv=True)
        
        logger.info("\n✅ 동기화 완료!")
        logger.info(f"   총 {len(labels)}개의 라벨이 wallet_labels.csv에 저장되었습니다.")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ 동기화 중단됨")
    except Exception as e:
        logger.error(f"\n❌ 동기화 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
