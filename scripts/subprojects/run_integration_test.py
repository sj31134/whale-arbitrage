#!/usr/bin/env python3
"""
서브 프로젝트 통합 테스트
- 모든 데이터 수집 스크립트 실행
- 백테스트 실행
- AI 모델 학습 및 평가
- 최종 리포트 생성
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def run_script(script_path, description):
    """스크립트 실행 및 결과 확인"""
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print("✅ 성공")
            if result.stdout:
                print(result.stdout[-500:])  # 마지막 500자만 출력
        else:
            print("❌ 실패")
            print(result.stderr[-500:])
            return False
    except subprocess.TimeoutExpired:
        print("⏱️ 타임아웃 (300초 초과)")
        return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False
    
    return True

def main():
    print("🚀 서브 프로젝트 통합 테스트 시작")
    print("="*60)
    
    results = {}
    
    # 1. 데이터 수집 검증
    print("\n📊 1단계: 데이터 수집 검증")
    results['data_verification'] = run_script(
        ROOT / "scripts" / "subprojects" / "verify_data_collection.py",
        "데이터 수집 검증"
    )
    
    # 2. Project 2 백테스트
    print("\n📈 2단계: Project 2 백테스트")
    results['backtest'] = run_script(
        ROOT / "scripts" / "subprojects" / "arbitrage" / "run_backtest.py",
        "Arbitrage 백테스트 실행"
    )
    
    # 3. Project 3 AI 모델 학습
    print("\n🧠 3단계: Project 3 AI 모델 학습")
    results['ai_training'] = run_script(
        ROOT / "scripts" / "subprojects" / "risk_ai" / "train_model.py",
        "Risk AI 모델 학습"
    )
    
    # 4. 최종 리포트
    print("\n" + "="*60)
    print("📊 통합 테스트 결과 요약")
    print("="*60)
    
    for test_name, success in results.items():
        status = "✅ 통과" if success else "❌ 실패"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ 모든 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트 실패. 위 결과를 확인하세요.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

