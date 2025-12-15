#!/usr/bin/env python3
"""
데이터베이스 스냅샷 생성 스크립트
로컬의 data/project.db를 압축하여 project.db.tar.gz로 생성합니다.
Streamlit Cloud의 DATABASE_URL 폴백을 위한 스냅샷 생성용입니다.
"""

import os
import sys
import tarfile
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "project.db"
OUTPUT_DIR = DATA_DIR  # data 폴더에 생성
OUTPUT_FILENAME = "project.db.tar.gz"
OUTPUT_PATH = OUTPUT_DIR / OUTPUT_FILENAME

def create_snapshot():
    if not DB_PATH.exists():
        print(f"Error: Database file not found at {DB_PATH}")
        sys.exit(1)
        
    print(f"Creating snapshot from {DB_PATH}...")
    print(f"File size: {DB_PATH.stat().st_size / (1024*1024):.2f} MB")
    
    # 임시 디렉토리 구조 생성 (tar 내부 구조가 data/project.db가 되도록)
    # 현재 DataLoader._download_database_if_needed 로직은 
    # 1. 압축 해제 후 data/project.db 확인
    # 2. 없으면 project.db 확인
    # 따라서 data/project.db 구조로 압축하는 것이 안전함
    
    try:
        with tarfile.open(OUTPUT_PATH, "w:gz") as tar:
            # DB 파일을 data/project.db 라는 이름으로 아카이브에 추가
            tar.add(DB_PATH, arcname="data/project.db")
            
        print(f"✅ Snapshot created successfully at {OUTPUT_PATH}")
        print(f"Snapshot size: {OUTPUT_PATH.stat().st_size / (1024*1024):.2f} MB")
        print(f"Timestamp: {datetime.now()}")
        
    except Exception as e:
        print(f"Error creating snapshot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_snapshot()

