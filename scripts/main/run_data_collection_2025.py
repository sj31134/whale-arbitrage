#!/usr/bin/env python3
"""
2025년 1월 1일부터 오늘까지 모든 데이터 수집 실행 스크립트
- 1시간 단위 가격 데이터 수집
- BTC 고래 거래 데이터 수집
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

def run_script(script_path: str, description: str):
    """스크립트 실행"""
    print("\n" + "=" * 70)
    print(f"🚀 {description}")
    print("=" * 70)
    
    script_full_path = PROJECT_ROOT / script_path
    
    if not script_full_path.exists():
        print(f"❌ 스크립트를 찾을 수 없습니다: {script_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_full_path)],
            cwd=str(PROJECT_ROOT),
            check=False
        )
        
        if result.returncode == 0:
            print(f"\n✅ {description} 완료")
            return True
        else:
            print(f"\n❌ {description} 실패 (종료 코드: {result.returncode})")
            return False
            
    except KeyboardInterrupt:
        print(f"\n⚠️ {description} 사용자에 의해 중단되었습니다.")
        return False
    except Exception as e:
        print(f"\n❌ {description} 오류 발생: {e}")
        return False

def main():
    """메인 함수"""
    print("=" * 70)
    print("📊 2025년 데이터 수집 시작")
    print("=" * 70)
    print("\n이 스크립트는 다음 작업을 수행합니다:")
    print("1. 1시간 단위 가격 데이터 수집 (모든 주요 코인)")
    print("2. BTC 고래 거래 데이터 수집")
    print("\n주의: 이 작업은 시간이 오래 걸릴 수 있습니다.")
    
    response = input("\n계속하시겠습니까? (y/n): ")
    if response.lower() != 'y':
        print("취소되었습니다.")
        return
    
    results = []
    
    # 1. 가격 데이터 수집
    results.append((
        run_script('collect_price_history_hourly.py', '1시간 단위 가격 데이터 수집'),
        '가격 데이터 수집'
    ))
    
    # 2. BTC 고래 거래 데이터 수집
    results.append((
        run_script('collect_btc_whale_transactions.py', 'BTC 고래 거래 데이터 수집'),
        'BTC 고래 거래 데이터 수집'
    ))
    
    # 결과 요약
    print("\n" + "=" * 70)
    print("📋 수집 결과 요약")
    print("=" * 70)
    
    for success, description in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{status}: {description}")
    
    # 검증 스크립트 실행 제안
    print("\n" + "=" * 70)
    print("💡 다음 단계")
    print("=" * 70)
    print("데이터 수집이 완료되었습니다. 다음 명령으로 데이터를 검증할 수 있습니다:")
    print("\n  python scripts/verify_data_collection_2025.py")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

