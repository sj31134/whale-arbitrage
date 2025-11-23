"""
GitHub 오픈소스 데이터셋 로더
거래소 주소, 컨트랙트 주소, 토큰 정보 등을 자동으로 수집하여 wallet_labels.csv 업데이트
"""

import os
import csv
import requests
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Set
from src.utils.logger import logger

# GitHub API 엔드포인트 (무료, 인증 없이도 사용 가능하지만 Rate Limit 낮음)
GITHUB_API_BASE = 'https://api.github.com'

# 주요 오픈소스 데이터셋 리포지토리
DATASET_REPOSITORIES = {
    # 거래소 주소 목록
    'exchange_addresses': {
        'repo': 'MyEtherWallet/ethereum-lists',
        'paths': [
            'src/addresses/addresses.json',
            'src/addresses/addresses-darklist.json',
        ],
        'type': 'addresses'
    },
    # 컨트랙트 주소 목록 (토큰 정보 포함)
    'token_contracts': {
        'repo': 'MyEtherWallet/ethereum-lists',
        'paths': [
            'src/tokens/eth/tokens-eth.json',
            'src/tokens/polygon/tokens-polygon.json',
        ],
        'type': 'tokens'
    },
    # DeFi 프로토콜 주소
    'defi_protocols': {
        'repo': 'DefiLlama/defillama-server',
        'paths': [
            'src/adapters/volumes/protocols/*',  # 패턴은 직접 처리 필요
        ],
        'type': 'protocols'
    },
    # 거래소 주소 (간단한 JSON)
    'simple_exchange_list': {
        'repo': '0xVishesh/cex-list',
        'paths': [
            'addresses.json',
        ],
        'type': 'addresses'
    }
}

# Rate Limit 관리
_last_request_time = 0
_min_request_interval = 1.0  # 최소 1초 간격 (GitHub API 무료 플랜: 초당 60회)


def _wait_for_rate_limit():
    """Rate Limit을 위해 대기"""
    global _last_request_time
    current_time = time.time()
    elapsed = current_time - _last_request_time
    
    if elapsed < _min_request_interval:
        sleep_time = _min_request_interval - elapsed
        time.sleep(sleep_time)
    
    _last_request_time = time.time()


def fetch_github_file(repo: str, file_path: str, branch: str = 'master') -> Optional[Dict]:
    """
    GitHub에서 파일 내용 가져오기
    
    Parameters:
    -----------
    repo : str
        리포지토리 이름 (예: 'owner/repo')
    file_path : str
        파일 경로
    branch : str
        브랜치 이름 (기본값: 'master')
    
    Returns:
    --------
    Optional[Dict] : 파일 내용 (JSON), 실패 시 None
    """
    try:
        _wait_for_rate_limit()
        
        # GitHub Raw Content API 사용
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                logger.warning(f"⚠️ JSON 파싱 실패: {url}")
                return None
        elif response.status_code == 404:
            logger.debug(f"⚠️ 파일을 찾을 수 없음: {url}")
            return None
        elif response.status_code == 403:
            logger.warning(f"⚠️ GitHub Rate Limit 초과 또는 접근 제한: {url}")
            time.sleep(5)
            return None
        else:
            logger.debug(f"⚠️ GitHub API 오류: {response.status_code}, {url}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.debug(f"⚠️ GitHub 요청 실패: {e}")
        return None
    except Exception as e:
        logger.debug(f"⚠️ GitHub 파일 가져오기 실패: {e}")
        return None


def parse_exchange_addresses(data: Dict) -> List[Dict[str, str]]:
    """
    거래소 주소 데이터 파싱
    
    Parameters:
    -----------
    data : Dict
        GitHub에서 가져온 원본 데이터
    
    Returns:
    --------
    List[Dict] : [{'address': str, 'label': str, 'category': str}] 형태의 리스트
    """
    results = []
    
    # ethereum-lists/addresses.json 형식 처리
    if isinstance(data, dict):
        for name, info in data.items():
            if isinstance(info, dict):
                address = info.get('address', '')
                if address and address.startswith('0x'):
                    results.append({
                        'address': address.lower(),
                        'label': info.get('name', name),
                        'category': info.get('category', 'Exchange')
                    })
        # 간단한 주소 리스트 형식
        if 'addresses' in data:
            for addr_info in data['addresses']:
                if isinstance(addr_info, dict):
                    address = addr_info.get('address', '')
                    if address and address.startswith('0x'):
                        results.append({
                            'address': address.lower(),
                            'label': addr_info.get('label', addr_info.get('name', '')),
                            'category': addr_info.get('category', 'Exchange')
                        })
    
    # 리스트 형식
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                address = item.get('address', '')
                if address and address.startswith('0x'):
                    results.append({
                        'address': address.lower(),
                        'label': item.get('label', item.get('name', '')),
                        'category': item.get('category', 'Exchange')
                    })
    
    return results


def parse_token_contracts(data: Dict, chain: str = 'ethereum') -> List[Dict[str, str]]:
    """
    토큰 컨트랙트 주소 데이터 파싱
    
    Parameters:
    -----------
    data : Dict
        GitHub에서 가져온 원본 데이터
    chain : str
        체인 이름 ('ethereum' 또는 'polygon')
    
    Returns:
    --------
    List[Dict] : [{'address': str, 'label': str, 'category': str}] 형태의 리스트
    """
    results = []
    
    if isinstance(data, list):
        for token in data:
            if isinstance(token, dict):
                address = token.get('address', '')
                if address and address.startswith('0x'):
                    symbol = token.get('symbol', '')
                    name = token.get('name', '')
                    label = f"{symbol} ({name})" if symbol and name else (symbol or name or 'Unknown Token')
                    
                    results.append({
                        'address': address.lower(),
                        'label': label,
                        'category': 'Token'
                    })
    
    return results


def load_exchange_addresses() -> List[Dict[str, str]]:
    """
    거래소 주소 목록을 GitHub에서 로드
    
    Returns:
    --------
    List[Dict] : 거래소 주소 목록
    """
    all_addresses = []
    
    # 간단한 거래소 리스트 시도
    logger.info("📥 거래소 주소 데이터셋 로드 중...")
    
    try:
        # cex-list 리포지토리에서 로드 시도
        data = fetch_github_file(
            repo='0xVishesh/cex-list',
            file_path='addresses.json',
            branch='main'
        )
        
        if data:
            parsed = parse_exchange_addresses(data)
            if parsed:
                logger.info(f"✅ {len(parsed)}개의 거래소 주소 로드 완료 (cex-list)")
                all_addresses.extend(parsed)
    except Exception as e:
        logger.debug(f"⚠️ cex-list 로드 실패: {e}")
    
    # ethereum-lists에서 추가 로드 시도
    try:
        data = fetch_github_file(
            repo='MyEtherWallet/ethereum-lists',
            file_path='src/addresses/addresses.json',
            branch='master'
        )
        
        if data:
            parsed = parse_exchange_addresses(data)
            if parsed:
                logger.info(f"✅ {len(parsed)}개의 주소 추가 로드 완료 (ethereum-lists)")
                # 중복 제거
                existing_addresses = {item['address'] for item in all_addresses}
                new_addresses = [item for item in parsed if item['address'] not in existing_addresses]
                all_addresses.extend(new_addresses)
    except Exception as e:
        logger.debug(f"⚠️ ethereum-lists 로드 실패: {e}")
    
    return all_addresses


def load_token_contracts(chain: str = 'ethereum') -> List[Dict[str, str]]:
    """
    토큰 컨트랙트 주소 목록을 GitHub에서 로드
    
    Parameters:
    -----------
    chain : str
        체인 이름 ('ethereum' 또는 'polygon')
    
    Returns:
    --------
    List[Dict] : 토큰 컨트랙트 주소 목록
    """
    all_tokens = []
    
    logger.info(f"📥 {chain.upper()} 토큰 컨트랙트 데이터셋 로드 중...")
    
    # ethereum-lists에서 토큰 정보 로드
    repo = 'MyEtherWallet/ethereum-lists'
    branch = 'master'
    
    if chain == 'ethereum':
        file_path = 'src/tokens/eth/tokens-eth.json'
    elif chain == 'polygon':
        file_path = 'src/tokens/polygon/tokens-polygon.json'
    else:
        logger.warning(f"⚠️ 지원하지 않는 체인: {chain}")
        return all_tokens
    
    try:
        data = fetch_github_file(repo, file_path, branch)
        
        if data:
            parsed = parse_token_contracts(data, chain=chain)
            if parsed:
                logger.info(f"✅ {len(parsed)}개의 토큰 컨트랙트 로드 완료 ({chain})")
                all_tokens.extend(parsed)
    except Exception as e:
        logger.debug(f"⚠️ 토큰 컨트랙트 로드 실패 ({chain}): {e}")
    
    return all_tokens


def merge_with_existing_labels(new_labels: List[Dict[str, str]], 
                               csv_path: Optional[str] = None) -> Dict[str, Dict[str, str]]:
    """
    새로운 라벨을 기존 라벨과 병합
    
    Parameters:
    -----------
    new_labels : List[Dict]
        새로운 라벨 목록
    csv_path : Optional[str]
        기존 CSV 파일 경로
    
    Returns:
    --------
    Dict : 병합된 라벨 딕셔너리
    """
    from src.utils.label_manager import load_labels
    
    # 기존 라벨 로드
    existing_labels = load_labels(csv_path)
    
    # 새로운 라벨 추가 (기존 라벨 우선)
    merged = existing_labels.copy()
    
    added_count = 0
    for label_info in new_labels:
        address = label_info['address'].lower()
        if address not in merged:
            merged[address] = {
                'label': label_info.get('label', ''),
                'category': label_info.get('category', 'Unknown')
            }
            added_count += 1
    
    logger.info(f"✅ {added_count}개의 새로운 라벨 추가됨 (기존: {len(existing_labels)}개)")
    return merged


def update_wallet_labels_csv(labels: Dict[str, Dict[str, str]], 
                            csv_path: Optional[str] = None) -> bool:
    """
    wallet_labels.csv 파일 업데이트
    
    Parameters:
    -----------
    labels : Dict
        라벨 딕셔너리
    csv_path : Optional[str]
        CSV 파일 경로 (기본값: config/wallet_labels.csv)
    
    Returns:
    --------
    bool : 성공 여부
    """
    if csv_path is None:
        project_root = Path(__file__).parent.parent.parent
        csv_path = project_root / 'config' / 'wallet_labels.csv'
    else:
        csv_path = Path(csv_path)
    
    # 디렉토리 생성
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['address', 'label', 'category'])
            writer.writeheader()
            
            for address, info in sorted(labels.items()):
                writer.writerow({
                    'address': address,
                    'label': info.get('label', ''),
                    'category': info.get('category', '')
                })
        
        logger.info(f"✅ wallet_labels.csv 업데이트 완료: {csv_path}")
        logger.info(f"   총 {len(labels)}개의 라벨 저장됨")
        return True
        
    except Exception as e:
        logger.error(f"❌ CSV 파일 업데이트 실패: {e}")
        return False


def sync_github_datasets(update_csv: bool = True) -> Dict[str, Dict[str, str]]:
    """
    GitHub 데이터셋을 동기화하여 라벨 정보 업데이트
    
    Parameters:
    -----------
    update_csv : bool
        CSV 파일 업데이트 여부 (기본값: True)
    
    Returns:
    --------
    Dict : 업데이트된 라벨 딕셔너리
    """
    logger.info("=" * 60)
    logger.info("🔄 GitHub 오픈소스 데이터셋 동기화")
    logger.info("=" * 60)
    
    all_labels = []
    
    # 1. 거래소 주소 로드
    exchange_addresses = load_exchange_addresses()
    all_labels.extend(exchange_addresses)
    
    # 2. 토큰 컨트랙트 로드 (Ethereum)
    eth_tokens = load_token_contracts(chain='ethereum')
    all_labels.extend(eth_tokens)
    
    # 3. 토큰 컨트랙트 로드 (Polygon)
    polygon_tokens = load_token_contracts(chain='polygon')
    all_labels.extend(polygon_tokens)
    
    # 4. 기존 라벨과 병합
    merged_labels = merge_with_existing_labels(all_labels)
    
    # 5. CSV 파일 업데이트 (선택적)
    if update_csv:
        update_wallet_labels_csv(merged_labels)
    
    logger.info("\n" + "=" * 60)
    logger.info(f"✅ 동기화 완료: 총 {len(merged_labels)}개의 라벨")
    logger.info("=" * 60)
    
    return merged_labels
