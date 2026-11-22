#!/usr/bin/env python3
"""
자동매매 봇 설치 스크립트
의존성 패키지 설치 및 필요한 디렉토리 생성
"""

import subprocess
import sys
from pathlib import Path
import os

def install():
    """설치 실행"""
    print("=" * 80)
    print("자동매매 봇 설치 시작")
    print("=" * 80)
    
    # 프로젝트 루트 경로
    root = Path(__file__).resolve().parents[3]
    
    # 1. 의존성 패키지 설치
    print("\n[1/4] 의존성 패키지 설치 중...")
    requirements_file = root / "requirements_trading_bot.txt"
    
    if requirements_file.exists():
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
            ])
            print("✅ 의존성 패키지 설치 완료")
        except subprocess.CalledProcessError as e:
            print(f"❌ 의존성 패키지 설치 실패: {e}")
            return False
    else:
        print("⚠️ requirements_trading_bot.txt 파일을 찾을 수 없습니다.")
    
    # 2. 필요한 디렉토리 생성
    print("\n[2/4] 디렉토리 생성 중...")
    directories = [
        root / "trading_bot" / "data",
        root / "trading_bot" / "config",
        root / "logs"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {directory}")
    
    # 3. 설정 파일 초기화
    print("\n[3/4] 설정 파일 초기화 중...")
    config_file = root / "trading_bot" / "config" / "user_settings.json"
    
    if not config_file.exists():
        default_config = root / "trading_bot" / "config" / "default_config.json"
        if default_config.exists():
            import shutil
            shutil.copy(default_config, config_file)
            print(f"   ✅ 설정 파일 생성: {config_file}")
        else:
            print("   ⚠️ 기본 설정 파일을 찾을 수 없습니다.")
    else:
        print("   ℹ️ 설정 파일이 이미 존재합니다.")
    
    # 4. 권한 설정 (Unix 계열만)
    print("\n[4/4] 권한 설정 중...")
    if os.name != 'nt':  # Windows가 아닌 경우
        try:
            if config_file.exists():
                os.chmod(config_file, 0o600)  # 소유자만 읽기/쓰기
                print(f"   ✅ 설정 파일 권한 설정 완료")
        except Exception as e:
            print(f"   ⚠️ 권한 설정 실패: {e}")
    else:
        print("   ℹ️ Windows 환경에서는 권한 설정을 건너뜁니다.")
    
    # 5. 설치 검증
    print("\n[검증] 설치 검증 중...")
    try:
        # 주요 모듈 import 테스트
        sys.path.insert(0, str(root))
        from trading_bot.config.settings_manager import SettingsManager
        from trading_bot.collectors.data_collector import DataCollector
        print("   ✅ 주요 모듈 로드 성공")
    except ImportError as e:
        print(f"   ⚠️ 모듈 로드 실패: {e}")
        print("   일부 기능이 작동하지 않을 수 있습니다.")
    
    print("\n" + "=" * 80)
    print("✅ 설치 완료")
    print("=" * 80)
    print("\n다음 단계:")
    print("1. Streamlit 앱 실행: streamlit run app/main.py")
    print("2. '🤖 자동매매 봇' 메뉴 선택")
    print("3. '설정' 탭에서 API 키 입력")
    print("4. '제어' 탭에서 봇 시작")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    success = install()
    sys.exit(0 if success else 1)

