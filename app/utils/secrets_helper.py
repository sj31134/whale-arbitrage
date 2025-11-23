"""
환경 변수 및 Secrets 관리 헬퍼
- Streamlit Cloud: st.secrets 사용
- 로컬 개발: .env 파일 사용
- Docker: 환경 변수 사용
"""

import os
from typing import Optional

def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    환경 변수 또는 Streamlit Secrets에서 값 가져오기
    
    우선순위:
    1. Streamlit Secrets (Streamlit Cloud)
    2. 환경 변수
    3. .env 파일 (로컬 개발)
    4. 기본값
    """
    # Streamlit Cloud
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except:
        pass
    
    # 환경 변수
    value = os.getenv(key)
    if value:
        return value
    
    # .env 파일 (로컬 개발)
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        
        # .env 파일 찾기
        env_path = Path(__file__).resolve().parents[3] / "config" / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            value = os.getenv(key)
            if value:
                return value
    except:
        pass
    
    return default

