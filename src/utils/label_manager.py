# src/utils/label_manager.py

import os
import csv
from pathlib import Path
from typing import Dict, Tuple, Optional
from src.utils.logger import logger

def load_labels(csv_path: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """
    wallet_labels.csv 파일을 읽어서 지갑 주소별 라벨 정보를 로드
    
    Parameters:
    -----------
    csv_path : str, optional
        CSV 파일 경로 (기본값: config/wallet_labels.csv)
    
    Returns:
    --------
    Dict[str, Dict[str, str]] : {address: {'label': label, 'category': category}} 형태의 딕셔너리
        주소는 소문자로 정규화됨
    """
    if csv_path is None:
        # 프로젝트 루트 기준으로 config/wallet_labels.csv 찾기
        project_root = Path(__file__).parent.parent.parent
        csv_path = project_root / 'config' / 'wallet_labels.csv'
    else:
        csv_path = Path(csv_path)
    
    labels = {}
    
    if not csv_path.exists():
        logger.warning(f"⚠️ 라벨 파일을 찾을 수 없습니다: {csv_path}")
        logger.info("ℹ️ config/wallet_labels.csv 파일을 생성하세요.")
        return labels
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                address = str(row.get('address', '')).strip().lower()
                label = str(row.get('label', '')).strip()
                category = str(row.get('category', '')).strip()
                
                if not address:
                    continue
                
                labels[address] = {
                    'label': label,
                    'category': category
                }
        
        logger.info(f"✅ {len(labels)}개의 지갑 라벨 로드 완료")
        
        if labels:
            # 샘플 출력 (최대 3개)
            sample_count = min(3, len(labels))
            logger.debug("📋 라벨 샘플:")
            for i, (addr, info) in enumerate(list(labels.items())[:sample_count]):
                logger.debug(f"   {addr[:10]}... → {info['label']} ({info['category']})")
    
    except Exception as e:
        logger.error(f"❌ 라벨 파일 로드 실패: {e}")
        return {}
    
    return labels

def get_label(address: str, labels: Dict[str, Dict[str, str]]) -> Optional[str]:
    """
    주소에 대한 라벨 반환
    
    Parameters:
    -----------
    address : str
        지갑 주소
    labels : Dict
        load_labels()로 로드한 라벨 딕셔너리
    
    Returns:
    --------
    Optional[str] : 라벨이 있으면 라벨 문자열, 없으면 None
    """
    if not address:
        return None
    
    address_lower = address.lower().strip()
    label_info = labels.get(address_lower)
    
    if label_info:
        return label_info.get('label')
    
    return None

def get_category(address: str, labels: Dict[str, Dict[str, str]]) -> Optional[str]:
    """
    주소에 대한 카테고리 반환
    
    Parameters:
    -----------
    address : str
        지갑 주소
    labels : Dict
        load_labels()로 로드한 라벨 딕셔너리
    
    Returns:
    --------
    Optional[str] : 카테고리가 있으면 카테고리 문자열, 없으면 None
    """
    if not address:
        return None
    
    address_lower = address.lower().strip()
    label_info = labels.get(address_lower)
    
    if label_info:
        return label_info.get('category')
    
    return None

