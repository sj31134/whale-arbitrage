#!/usr/bin/env python3
"""
통합 라벨링 업데이트 실행 스크립트
모든 라벨링 소스를 순차적으로 실행하여 데이터를 최신화합니다.
"""

import subprocess
import sys
import time

def run_script(script_path, description):
    print("\n" + "=" * 80)
    print(f"🚀 {description} 실행 중...")
    print(f"   파일: {script_path}")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            text=True
        )
        print(f"✅ {description} 완료")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 실패 (Exit Code: {e.returncode})")
        return False
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
        return False

def main():
    print("🔄 통합 라벨링 시스템 가동 시작")
    start_time = time.time()
    
    steps = [
        ("scripts/labeling/update_known_labels.py", "1. 정적 거래소 리스트 업데이트"),
        ("scripts/collectors/bitinfocharts_crawler.py", "2. BitInfoCharts 크롤링 (BTC/LTC 등)"),
        ("scripts/labeling/update_real_whale_labels.py", "3. Etherscan/BSCScan 크롤링 (ETH/BSC)"),
        ("scripts/labeling/update_labels_stable.py", "4. 트랜잭션 라벨 전파 (whale_address -> whale_transactions)"),
        ("scripts/labeling/post_process_rpc_runner.py", "5. 트랜잭션 방향(BUY/SELL) 재계산")
    ]
    
    for script, desc in steps:
        if not run_script(script, desc):
            print("\n⚠️ 프로세스 중단: 치명적인 오류 발생")
            sys.exit(1)
        time.sleep(2)  # 쿨다운
            
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"🎉 모든 작업이 성공적으로 완료되었습니다! (소요 시간: {elapsed/60:.1f}분)")
    print("=" * 80)

if __name__ == "__main__":
    main()

