"""
로깅 유틸리티
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import os


def setup_logger(name: str = "trading_bot", log_dir: Optional[Path] = None) -> logging.Logger:
    """
    로거 설정
    
    Args:
        name: 로거 이름
        log_dir: 로그 디렉토리 (None이면 기본 경로)
    
    Returns:
        설정된 로거
    """
    if log_dir is None:
        # 프로젝트 루트의 logs 디렉토리
        base_dir = Path(__file__).resolve().parents[3]
        log_dir = base_dir / "logs"
    
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 로그 파일 경로
    log_file = log_dir / f"{name}.log"
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger

