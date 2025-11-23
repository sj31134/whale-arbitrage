"""
BSC Hybrid Collection System

BSC 거래 수집을 위한 하이브리드 시스템 모듈
- API로 빠른 기본 데이터 수집
- 웹 스크래핑으로 고액 거래 추가 정보 보완
"""

from .bsc_api_collector import (
    get_bsc_addresses_from_supabase,
    fetch_transactions_via_api,
    collect_all_bsc_transactions,
    classify_transaction_size,
    is_high_value_transaction,
    save_to_whale_transactions
)

from .bsc_web_scraper import (
    scrape_transaction_details,
    scrape_multiple_transactions
)

from .bsc_hybrid_collector import (
    run_hybrid_collection,
    filter_high_value_transactions
)

__all__ = [
    # API Collector
    'get_bsc_addresses_from_supabase',
    'fetch_transactions_via_api',
    'collect_all_bsc_transactions',
    'classify_transaction_size',
    'is_high_value_transaction',
    'save_to_whale_transactions',
    
    # Web Scraper
    'scrape_transaction_details',
    'scrape_multiple_transactions',
    
    # Hybrid Collector
    'run_hybrid_collection',
    'filter_high_value_transactions',
]

__version__ = '1.0.0'
__author__ = 'Whale Tracking Team'

