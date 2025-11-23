"""
4byte.directory API를 통한 함수 시그니처 디코딩
스마트 컨트랙트 input_data의 method ID를 함수 이름으로 변환
무료 API (Rate Limit 있음)
"""

import requests
import time
from typing import Optional, Dict, List
from src.utils.logger import logger

# 4byte.directory API 엔드포인트
FOURBYTE_API_BASE = 'https://www.4byte.directory/api/v1/signatures/'

# Rate Limit 관리
_last_request_time = 0
_min_request_interval = 0.5  # 최소 0.5초 간격


def _wait_for_rate_limit():
    """Rate Limit을 위해 대기"""
    global _last_request_time
    current_time = time.time()
    elapsed = current_time - _last_request_time
    
    if elapsed < _min_request_interval:
        sleep_time = _last_request_interval - elapsed
        time.sleep(sleep_time)
    
    _last_request_time = time.time()


def extract_method_id(input_data: str) -> Optional[str]:
    """
    input_data에서 method ID 추출
    
    Parameters:
    -----------
    input_data : str
        트랜잭션 input 데이터 (0x로 시작하는 hex 문자열)
    
    Returns:
    --------
    Optional[str] : method ID (0x + 8자 hex), 없으면 None
    """
    if not input_data or not isinstance(input_data, str):
        return None
    
    # 0x 제거
    clean_input = input_data.strip().lower()
    if clean_input.startswith('0x'):
        clean_input = clean_input[2:]
    
    # 최소 8자 (4바이트 = method ID) 확인
    if len(clean_input) < 8:
        return None
    
    # 처음 8자 (4바이트) 추출
    method_id = '0x' + clean_input[:8]
    return method_id


def decode_function_signature(method_id: str) -> Optional[Dict[str, any]]:
    """
    4byte.directory API를 사용하여 함수 시그니처 디코딩
    
    Parameters:
    -----------
    method_id : str
        Method ID (0x + 8자 hex)
    
    Returns:
    --------
    Optional[Dict] : {
        'method_id': str,
        'text_signature': str,  # 예: 'transfer(address,uint256)'
        'hex_signature': str,
        'count': int  # 등록된 횟수
    }, 실패 시 None
    """
    if not method_id or not method_id.startswith('0x'):
        return None
    
    try:
        # Rate Limit 대기
        _wait_for_rate_limit()
        
        # 4byte.directory API 호출
        # 참고: hex_signature는 0x 없이 전달
        hex_signature = method_id[2:].lower()
        
        params = {
            'hex_signature': hex_signature
        }
        
        response = requests.get(
            FOURBYTE_API_BASE,
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # 4byte.directory 응답 구조: { "count": 1, "next": null, "previous": null, "results": [...] }
            if 'results' in data and len(data['results']) > 0:
                # 가장 많이 사용된 시그니처 선택 (count가 높은 것)
                results = data['results']
                # count 기준으로 정렬 (내림차순)
                sorted_results = sorted(results, key=lambda x: x.get('count', 0), reverse=True)
                best_match = sorted_results[0]
                
                result = {
                    'method_id': method_id,
                    'text_signature': best_match.get('text_signature', ''),
                    'hex_signature': best_match.get('hex_signature', ''),
                    'count': best_match.get('count', 0),
                    'function_name': best_match.get('text_signature', '').split('(')[0] if '(' in best_match.get('text_signature', '') else ''
                }
                
                logger.debug(f"🔍 {method_id} → {result['text_signature']}")
                return result
            else:
                logger.debug(f"⚠️ {method_id}에 대한 시그니처를 찾을 수 없음")
                return None
        
        elif response.status_code == 429:
            # Rate Limit 초과
            logger.warning(f"⚠️ 4byte.directory Rate Limit 초과, 잠시 대기")
            time.sleep(2)
            return None
        
        else:
            logger.debug(f"⚠️ 4byte.directory API 오류: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.debug(f"⚠️ 4byte.directory 네트워크 오류: {e}")
        return None
    except Exception as e:
        logger.debug(f"⚠️ 4byte.directory 디코딩 실패 ({method_id}): {e}")
        return None


def decode_input_data(input_data: str) -> Optional[Dict[str, any]]:
    """
    input_data에서 함수 시그니처 디코딩 (통합 함수)
    
    Parameters:
    -----------
    input_data : str
        트랜잭션 input 데이터
    
    Returns:
    --------
    Optional[Dict] : {
        'method_id': str,
        'text_signature': str,
        'function_name': str,
        'parameters': List[str],  # 나중에 확장 가능
        ...
    }, 실패 시 None
    """
    # Method ID 추출
    method_id = extract_method_id(input_data)
    if not method_id:
        return None
    
    # 4byte.directory로 디코딩
    decoded = decode_function_signature(method_id)
    if not decoded:
        return None
    
    # 함수 이름과 파라미터 분리
    text_sig = decoded.get('text_signature', '')
    if '(' in text_sig and ')' in text_sig:
        function_name = text_sig.split('(')[0]
        params_str = text_sig.split('(')[1].rstrip(')')
        parameters = [p.strip() for p in params_str.split(',')] if params_str else []
        
        decoded['function_name'] = function_name
        decoded['parameters'] = parameters
    else:
        decoded['function_name'] = text_sig
        decoded['parameters'] = []
    
    return decoded


def get_function_name(input_data: str) -> Optional[str]:
    """
    input_data에서 함수 이름만 추출 (간편 함수)
    
    Parameters:
    -----------
    input_data : str
        트랜잭션 input 데이터
    
    Returns:
    --------
    Optional[str] : 함수 이름 (예: 'transfer', 'approve'), 실패 시 None
    """
    decoded = decode_input_data(input_data)
    if decoded:
        return decoded.get('function_name')
    return None


def batch_decode_function_signatures(method_ids: List[str]) -> Dict[str, Dict[str, any]]:
    """
    여러 method ID를 배치로 디코딩
    
    Parameters:
    -----------
    method_ids : List[str]
        Method ID 리스트
    
    Returns:
    --------
    Dict[str, Dict] : {method_id: decoded_info} 형태의 딕셔너리
    """
    results = {}
    
    for method_id in method_ids:
        decoded = decode_function_signature(method_id)
        if decoded:
            results[method_id.lower()] = decoded
    
    return results
