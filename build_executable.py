#!/usr/bin/env python3
"""
실행 파일 빌드 스크립트
PyInstaller를 사용하여 Streamlit 앱을 실행 파일로 빌드
"""

import subprocess
import sys
from pathlib import Path
import shutil

def build():
    """실행 파일 빌드"""
    print("=" * 80)
    print("실행 파일 빌드 시작")
    print("=" * 80)
    
    root = Path(__file__).resolve().parent
    
    # PyInstaller 설치 확인
    try:
        import PyInstaller
        print("✅ PyInstaller 설치 확인")
    except ImportError:
        print("❌ PyInstaller가 설치되지 않았습니다.")
        print("설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller 설치 완료")
    
    # spec 파일 생성
    print("\n[1/3] PyInstaller spec 파일 생성 중...")
    
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{root / "app" / "main.py"}'],
    pathex=[],
    binaries=[],
    datas=[
        ('{root / "trading_bot"}', 'trading_bot'),
        ('{root / "app"}', 'app'),
        ('{root / "data" / "models"}', 'data/models'),
    ],
    hiddenimports=[
        'streamlit',
        'pandas',
        'numpy',
        'pyupbit',
        'requests',
        'trading_bot',
        'trading_bot.config',
        'trading_bot.core',
        'trading_bot.collectors',
        'trading_bot.strategies',
        'trading_bot.execution',
        'trading_bot.utils',
        'trading_bot.ui',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='whale_trading_bot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 모드
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
    
    spec_file = root / "whale_trading_bot.spec"
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"✅ Spec 파일 생성 완료: {spec_file}")
    
    # 빌드 실행
    print("\n[2/3] 실행 파일 빌드 중...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller",
            "--clean",
            str(spec_file)
        ])
        print("✅ 빌드 완료")
    except subprocess.CalledProcessError as e:
        print(f"❌ 빌드 실패: {e}")
        return False
    
    # 빌드 결과 확인
    print("\n[3/3] 빌드 결과 확인 중...")
    dist_dir = root / "dist"
    exe_file = dist_dir / "whale_trading_bot"
    
    if sys.platform == "win32":
        exe_file = dist_dir / "whale_trading_bot.exe"
    
    if exe_file.exists():
        print(f"✅ 실행 파일 생성 완료: {exe_file}")
        print(f"   파일 크기: {exe_file.stat().st_size / 1024 / 1024:.2f} MB")
    else:
        print(f"⚠️ 실행 파일을 찾을 수 없습니다: {exe_file}")
    
    print("\n" + "=" * 80)
    print("빌드 완료")
    print("=" * 80)
    print(f"\n실행 파일 위치: {exe_file}")
    print("\n주의사항:")
    print("- 실행 파일은 독립적으로 실행 가능합니다")
    print("- 설정 파일은 실행 파일과 같은 디렉토리에 생성됩니다")
    print("- 데이터베이스 파일 경로를 확인하세요")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)

