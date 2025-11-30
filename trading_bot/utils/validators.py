"""
입력 검증 유틸리티
"""

import re
from typing import Tuple


def validate_api_key(key: str) -> Tuple[bool, str]:
    """
    API 키 형식 검증
    
    Args:
        key: API 키
    
    Returns:
        (유효 여부, 에러 메시지)
    """
    if not key:
        return True, ""  # 빈 값은 허용 (선택적 필드)
    
    if len(key) < 10:
        return False, "API 키는 최소 10자 이상이어야 합니다."
    
    if not re.match(r'^[A-Za-z0-9_-]+$', key):
        return False, "API 키는 영문, 숫자, 하이픈, 언더스코어만 사용할 수 있습니다."
    
    return True, ""


def validate_number(value: str, min_val: float = None, max_val: float = None) -> Tuple[bool, str]:
    """
    숫자 입력 검증
    
    Args:
        value: 입력 값
        min_val: 최소값
        max_val: 최대값
    
    Returns:
        (유효 여부, 에러 메시지)
    """
    try:
        num = float(value)
        
        if min_val is not None and num < min_val:
            return False, f"값은 {min_val} 이상이어야 합니다."
        
        if max_val is not None and num > max_val:
            return False, f"값은 {max_val} 이하여야 합니다."
        
        return True, ""
        
    except ValueError:
        return False, "숫자 형식이 올바르지 않습니다."


def validate_required(value: str, field_name: str) -> Tuple[bool, str]:
    """
    필수 필드 검증
    
    Args:
        value: 입력 값
        field_name: 필드 이름
    
    Returns:
        (유효 여부, 에러 메시지)
    """
    if not value or not value.strip():
        return False, f"{field_name}은(는) 필수 항목입니다."
    
    return True, ""


def validate_coin_symbol(symbol: str) -> Tuple[bool, str]:
    """
    코인 심볼 검증
    
    Args:
        symbol: 코인 심볼
    
    Returns:
        (유효 여부, 에러 메시지)
    """
    valid_symbols = ['BTC', 'ETH']
    
    if symbol.upper() not in valid_symbols:
        return False, f"지원하는 코인: {', '.join(valid_symbols)}"
    
    return True, ""

