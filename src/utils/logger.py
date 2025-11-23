# src/utils/logger.py

import logging
import logging.handlers
import os
from pathlib import Path
from dotenv import load_dotenv
import colorlog

# 환경변수 로드
load_dotenv('config/.env')

def setup_logger(name, log_file='logs/whale_tracking.log', level=logging.INFO):
    """
    로거 설정
    
    - 콘솔에 컬러 출력
    - 파일에 기록
    """
    
    # 로그 디렉토리 생성
    Path('logs').mkdir(exist_ok=True)
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 포매터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 콘솔 핸들러 (컬러)
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s%(reset)s - '
        '%(log_color)s%(name)s%(reset)s - '
        '%(log_color)s%(levelname)s%(reset)s - '
        '%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))
    logger.addHandler(console_handler)
    
    # 파일 핸들러
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# 기본 로거
logger = setup_logger('whale_tracking')
