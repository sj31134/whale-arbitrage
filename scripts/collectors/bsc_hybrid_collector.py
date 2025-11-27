#!/usr/bin/env python3
"""
BSC Hybrid Collector

BSC 거래 수집을 위한 하이브리드 시스템
1. API로 모든 거래 수집 (빠르고 정확)
2. 고액 거래 필터링
3. 웹 스크래핑으로 추가 정보 보완 (Method, Label 등)
4. whale_transactions 테이블에 저장
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 로컬 모듈 임포트
from scripts.collectors.bsc_api_collector import (
    get_bsc_addresses_from_supabase,
    collect_all_bsc_transactions,
    is_high_value_transaction,
    save_to_whale_transactions,
    get_supabase_client
)

from scripts.collectors.bsc_web_scraper import (
    scrape_multiple_transactions
)

# 설정
CHECKPOINT_FILE = PROJECT_ROOT / "checkpoints" / "bsc_hybrid_checkpoint.json"
DEFAULT_MIN_BNB = 100  # BNB 기준
DEFAULT_MIN_USD = 50000  # USD 기준
WEB_SCRAPING_DELAY = 2  # 초


def load_checkpoint() -> Dict:
    """
    체크포인트 파일 로드
    
    Returns:
    --------
    Dict : 체크포인트 데이터
    """
    if not CHECKPOINT_FILE.exists():
        return {
            'last_run': None,
            'processed_addresses': [],
            'high_value_txs_scraped': [],
            'total_collected': 0,
            'total_scraped': 0
        }
    
    try:
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ 체크포인트 로드 실패: {e}")
        return {
            'last_run': None,
            'processed_addresses': [],
            'high_value_txs_scraped': [],
            'total_collected': 0,
            'total_scraped': 0
        }


def save_checkpoint(checkpoint: Dict):
    """
    체크포인트 저장
    
    Parameters:
    -----------
    checkpoint : Dict
        저장할 체크포인트 데이터
    """
    try:
        # 디렉토리 생성
        CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # 현재 시간 업데이트
        checkpoint['last_run'] = datetime.now().isoformat()
        
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 체크포인트 저장: {CHECKPOINT_FILE}")
    
    except Exception as e:
        print(f"⚠️ 체크포인트 저장 실패: {e}")


def save_backup_csv(transactions: List[Dict], filename: str):
    """
    로컬 CSV 백업 저장
    
    Parameters:
    -----------
    transactions : List[Dict]
        거래 리스트
    filename : str
        파일명
    """
    import csv
    
    try:
        backup_dir = PROJECT_ROOT / "data" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = backup_dir / filename
        
        if not transactions:
            return
        
        fieldnames = list(transactions[0].keys())
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for tx in transactions:
                row = tx.copy()
                # datetime을 문자열로 변환
                if isinstance(row.get('block_timestamp'), datetime):
                    row['block_timestamp'] = row['block_timestamp'].isoformat()
                writer.writerow(row)
        
        print(f"💾 백업 저장: {filepath}")
    
    except Exception as e:
        print(f"⚠️ 백업 저장 실패: {e}")


def filter_high_value_transactions(
    transactions: List[Dict],
    min_bnb: float = DEFAULT_MIN_BNB,
    min_usd: Optional[float] = DEFAULT_MIN_USD
) -> List[Dict]:
    """
    고액 거래 필터링
    
    Parameters:
    -----------
    transactions : List[Dict]
        전체 거래 리스트
    min_bnb : float
        최소 BNB 금액
    min_usd : Optional[float]
        최소 USD 금액
    
    Returns:
    --------
    List[Dict] : 고액 거래 리스트
    """
    high_value_txs = []
    
    for tx in transactions:
        amount = tx.get('amount', 0)
        coin_symbol = tx.get('coin_symbol', 'BNB')
        
        # BNB 기준
        if coin_symbol == 'BNB' and amount >= min_bnb:
            high_value_txs.append(tx)
            continue
        
        # USD 기준 (있는 경우)
        if min_usd:
            amount_usd = tx.get('amount_usd')
            if amount_usd and amount_usd >= min_usd:
                high_value_txs.append(tx)
    
    return high_value_txs


def run_hybrid_collection(
    addresses: Optional[List[str]] = None,
    skip_scraping: bool = False,
    min_bnb: float = DEFAULT_MIN_BNB,
    min_usd: float = DEFAULT_MIN_USD,
    save_to_db: bool = True,
    web_scraping_delay: float = WEB_SCRAPING_DELAY
) -> Dict:
    """
    하이브리드 수집 실행
    
    Parameters:
    -----------
    addresses : Optional[List[str]]
        수집할 주소 리스트 (None일 경우 Supabase에서 조회)
    skip_scraping : bool
        웹 스크래핑 건너뛰기
    min_bnb : float
        웹 스크래핑 대상 최소 BNB 금액
    min_usd : float
        웹 스크래핑 대상 최소 USD 금액
    save_to_db : bool
        데이터베이스 저장 여부
    web_scraping_delay : float
        웹 스크래핑 요청 간 대기 시간
    
    Returns:
    --------
    Dict : 실행 결과 통계
    """
    start_time = datetime.now()
    
    print(f"\n{'='*80}")
    print(f"BSC Hybrid Collection System")
    print(f"{'='*80}")
    print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"설정:")
    print(f"  - 웹 스크래핑: {'비활성화' if skip_scraping else '활성화'}")
    print(f"  - 최소 BNB: {min_bnb}")
    print(f"  - 최소 USD: ${min_usd:,}")
    print(f"  - DB 저장: {'활성화' if save_to_db else '비활성화'}")
    
    # 체크포인트 로드
    checkpoint = load_checkpoint()
    
    # Step 1: API로 거래 수집
    print(f"\n{'='*80}")
    print(f"Step 1: API를 통한 거래 수집")
    print(f"{'='*80}")
    
    all_transactions = collect_all_bsc_transactions(addresses)
    
    if not all_transactions:
        print("⚠️ 수집된 거래가 없습니다.")
        return {
            'total_collected': 0,
            'high_value_count': 0,
            'scraped_count': 0,
            'saved_count': 0,
            'duration_seconds': 0
        }
    
    # 백업 저장
    backup_filename = f"bsc_transactions_api_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    save_backup_csv(all_transactions, backup_filename)
    
    # Step 2: 고액 거래 필터링
    print(f"\n{'='*80}")
    print(f"Step 2: 고액 거래 필터링")
    print(f"{'='*80}")
    
    high_value_txs = filter_high_value_transactions(
        all_transactions,
        min_bnb=min_bnb,
        min_usd=min_usd
    )
    
    print(f"전체 거래: {len(all_transactions)}건")
    print(f"고액 거래: {len(high_value_txs)}건 ({len(high_value_txs)/len(all_transactions)*100:.1f}%)")
    
    # Step 3: 웹 스크래핑으로 추가 정보 보완
    scraped_count = 0
    
    if not skip_scraping and high_value_txs:
        print(f"\n{'='*80}")
        print(f"Step 3: 웹 스크래핑으로 추가 정보 보완")
        print(f"{'='*80}")
        print(f"대상: {len(high_value_txs)}건")
        print(f"예상 소요 시간: 약 {len(high_value_txs) * web_scraping_delay / 60:.1f}분")
        
        # 이미 스크래핑한 거래 제외
        already_scraped = set(checkpoint.get('high_value_txs_scraped', []))
        txs_to_scrape = [
            tx for tx in high_value_txs 
            if tx.get('tx_hash') not in already_scraped
        ]
        
        if txs_to_scrape:
            print(f"새로 스크래핑할 거래: {len(txs_to_scrape)}건")
            
            enriched_txs = scrape_multiple_transactions(
                txs_to_scrape,
                delay=web_scraping_delay
            )
            
            # 원본 거래 리스트 업데이트
            enriched_tx_map = {tx['tx_hash']: tx for tx in enriched_txs}
            
            for i, tx in enumerate(all_transactions):
                tx_hash = tx.get('tx_hash')
                if tx_hash in enriched_tx_map:
                    all_transactions[i] = enriched_tx_map[tx_hash]
            
            # 체크포인트 업데이트
            checkpoint['high_value_txs_scraped'].extend([tx['tx_hash'] for tx in enriched_txs])
            scraped_count = len(enriched_txs)
        else:
            print(f"✓ 모든 고액 거래가 이미 스크래핑되었습니다.")
        
        # 백업 저장 (스크래핑 후)
        backup_filename = f"bsc_transactions_enriched_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        save_backup_csv(all_transactions, backup_filename)
    
    else:
        print(f"\n⏭️  Step 3: 웹 스크래핑 건너뛰기")
    
    # Step 4: whale_transactions 테이블에 저장
    saved_count = 0
    
    if save_to_db:
        print(f"\n{'='*80}")
        print(f"Step 4: whale_transactions 테이블에 저장")
        print(f"{'='*80}")
        
        saved_count = save_to_whale_transactions(all_transactions)
        
        # 체크포인트 업데이트
        checkpoint['total_collected'] += len(all_transactions)
        checkpoint['total_scraped'] += scraped_count
    
    else:
        print(f"\n⏭️  Step 4: 데이터베이스 저장 건너뛰기")
    
    # 체크포인트 저장
    save_checkpoint(checkpoint)
    
    # 결과 요약
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n{'='*80}")
    print(f"실행 완료")
    print(f"{'='*80}")
    print(f"종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"소요 시간: {duration/60:.1f}분 ({duration:.0f}초)")
    print(f"\n📊 통계:")
    print(f"  - 전체 거래 수집: {len(all_transactions)}건")
    print(f"  - 고액 거래: {len(high_value_txs)}건")
    print(f"  - 웹 스크래핑: {scraped_count}건")
    print(f"  - DB 저장: {saved_count}건")
    
    return {
        'total_collected': len(all_transactions),
        'high_value_count': len(high_value_txs),
        'scraped_count': scraped_count,
        'saved_count': saved_count,
        'duration_seconds': duration
    }


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description='BSC Hybrid Collection System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 실행 (API + 웹 스크래핑 + DB 저장)
  python bsc_hybrid_collector.py
  
  # API만 실행 (웹 스크래핑 건너뛰기)
  python bsc_hybrid_collector.py --skip-scraping
  
  # 고액 거래 기준 변경
  python bsc_hybrid_collector.py --min-bnb 1000 --min-usd 500000
  
  # DB 저장 없이 수집만
  python bsc_hybrid_collector.py --no-save
  
  # 웹 스크래핑 속도 조절
  python bsc_hybrid_collector.py --scraping-delay 5
        """
    )
    
    parser.add_argument(
        '--skip-scraping',
        action='store_true',
        help='웹 스크래핑 건너뛰기 (API만 사용)'
    )
    
    parser.add_argument(
        '--min-bnb',
        type=float,
        default=DEFAULT_MIN_BNB,
        help=f'웹 스크래핑 대상 최소 BNB 금액 (기본값: {DEFAULT_MIN_BNB})'
    )
    
    parser.add_argument(
        '--min-usd',
        type=float,
        default=DEFAULT_MIN_USD,
        help=f'웹 스크래핑 대상 최소 USD 금액 (기본값: {DEFAULT_MIN_USD})'
    )
    
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='데이터베이스 저장 건너뛰기 (백업 CSV만 저장)'
    )
    
    parser.add_argument(
        '--scraping-delay',
        type=float,
        default=WEB_SCRAPING_DELAY,
        help=f'웹 스크래핑 요청 간 대기 시간(초) (기본값: {WEB_SCRAPING_DELAY})'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='테스트 모드 (첫 3개 주소만)'
    )
    
    args = parser.parse_args()
    
    try:
        # 테스트 모드
        addresses = None
        if args.test:
            print("🧪 테스트 모드: 처음 3개 주소만 처리")
            addresses = get_bsc_addresses_from_supabase()[:3]
        
        # 실행
        result = run_hybrid_collection(
            addresses=addresses,
            skip_scraping=args.skip_scraping,
            min_bnb=args.min_bnb,
            min_usd=args.min_usd,
            save_to_db=not args.no_save,
            web_scraping_delay=args.scraping_delay
        )
        
        # 성공
        print(f"\n✅ 모든 작업이 완료되었습니다!")
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
        return 1
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())




