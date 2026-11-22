#!/usr/bin/env python3
"""
병렬 데이터 수집 통합 스크립트

가격 데이터, BTC 고래 거래, BSC 고래 거래를 병렬로 수집
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict

PROJECT_ROOT = Path(__file__).parent

# 전역 프로세스 리스트
processes: List[subprocess.Popen] = []
start_time = None

def signal_handler(sig, frame):
    """Ctrl+C 시그널 핸들러"""
    print("\n\n⚠️  중단 신호 수신. 모든 프로세스를 정상 종료합니다...")
    
    for i, proc in enumerate(processes):
        if proc.poll() is None:  # 아직 실행 중인 경우
            print(f"   프로세스 {i+1} 종료 중 (PID: {proc.pid})...")
            proc.terminate()
    
    # 모든 프로세스가 종료될 때까지 대기
    time.sleep(2)
    
    for proc in processes:
        if proc.poll() is None:
            proc.kill()
    
    print("\n💾 체크포인트 저장 중...")
    try:
        subprocess.run([sys.executable, 'scripts/main/save_collection_checkpoint.py'], 
                      cwd=PROJECT_ROOT, check=False)
    except:
        pass
    
    print("✅ 정상 종료되었습니다.")
    sys.exit(0)

# 시그널 핸들러 등록
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_log_filename(prefix: str) -> str:
    """로그 파일명 생성"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"logs/{prefix}_{timestamp}.log"

def print_header():
    """헤더 출력"""
    print("=" * 80)
    print("🚀 병렬 데이터 수집 시작")
    print("=" * 80)
    print(f"\n시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n수집 작업:")
    print("  1. 📊 가격 데이터 (price_history) - 재개 모드")
    print("  2. 🐋 BTC 고래 거래 (whale_transactions) - 재개 모드")
    print("  3. 🟡 BSC 고래 거래 (whale_transactions) - 전체 수집 (고액만 스크래핑)")
    print("\n예상 소요 시간: 약 60분")
    print("=" * 80)
    print()

def create_log_dir():
    """로그 디렉토리 생성"""
    log_dir = PROJECT_ROOT / 'logs'
    log_dir.mkdir(exist_ok=True)
    return log_dir

def start_process(name: str, command: List[str], log_file: str) -> subprocess.Popen:
    """프로세스 시작"""
    print(f"🚀 {name} 시작 중...")
    print(f"   명령어: {' '.join(command)}")
    print(f"   로그: {log_file}")
    
    log_path = PROJECT_ROOT / log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_path, 'w') as f:
        proc = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=f,
            stderr=subprocess.STDOUT,
            text=True
        )
    
    print(f"   PID: {proc.pid}")
    print()
    return proc

def monitor_processes(processes: List[Dict]):
    """프로세스 모니터링"""
    print("📊 프로세스 모니터링 시작...")
    print("   10분마다 진행 상황을 출력합니다.")
    print("   중단하려면 Ctrl+C를 누르세요.")
    print()
    
    last_check = time.time()
    check_interval = 600  # 10분
    
    while True:
        # 모든 프로세스가 종료되었는지 확인
        all_done = all(proc['process'].poll() is not None for proc in processes)
        
        if all_done:
            print("\n✅ 모든 프로세스가 완료되었습니다!")
            break
        
        # 10분마다 진행 상황 출력
        current_time = time.time()
        if current_time - last_check >= check_interval:
            elapsed = int(current_time - start_time)
            elapsed_min = elapsed // 60
            elapsed_sec = elapsed % 60
            
            print("\n" + "=" * 80)
            print(f"⏱️  진행 상황 (경과 시간: {elapsed_min}분 {elapsed_sec}초)")
            print("=" * 80)
            
            for proc_info in processes:
                name = proc_info['name']
                proc = proc_info['process']
                status = "🟢 실행 중" if proc.poll() is None else "✅ 완료"
                print(f"  {name}: {status}")
            
            print("=" * 80)
            print()
            
            last_check = current_time
        
        time.sleep(10)  # 10초마다 체크

def print_summary(processes: List[Dict]):
    """결과 요약 출력"""
    elapsed = int(time.time() - start_time)
    elapsed_min = elapsed // 60
    elapsed_sec = elapsed % 60
    
    print("\n" + "=" * 80)
    print("📋 수집 결과 요약")
    print("=" * 80)
    print(f"\n총 소요 시간: {elapsed_min}분 {elapsed_sec}초\n")
    
    for proc_info in processes:
        name = proc_info['name']
        proc = proc_info['process']
        log_file = proc_info['log']
        
        return_code = proc.poll()
        
        if return_code == 0:
            status = "✅ 성공"
        elif return_code is None:
            status = "⚠️ 아직 실행 중"
        else:
            status = f"❌ 실패 (코드: {return_code})"
        
        print(f"{name}:")
        print(f"  상태: {status}")
        print(f"  로그: {log_file}")
        print()
    
    print("=" * 80)
    print("\n다음 단계:")
    print("  1. 로그 파일을 확인하여 세부 내용 검토")
    print("  2. 검증 스크립트 실행: python3 scripts/diagnostics/verify_data_collection_2025.py")
    print("  3. 체크포인트 확인: cat collection_checkpoint.json")
    print()

def main():
    """메인 함수"""
    global start_time, processes
    
    # 로그 디렉토리 생성
    create_log_dir()
    
    # 헤더 출력
    print_header()
    
    # 시작 시간 기록
    start_time = time.time()
    
    # 프로세스 정보
    process_configs = [
        {
            'name': '📊 가격 데이터 수집',
            'command': [sys.executable, 'collect_price_history_hourly.py', '--resume'],
            'log': get_log_filename('price_history')
        },
        {
            'name': '🐋 BTC 고래 거래 수집',
            'command': [sys.executable, 'collect_btc_whale_transactions.py', '--resume'],
            'log': get_log_filename('btc_whale')
        },
        {
            'name': '🟡 BSC 고래 거래 수집',
            'command': [sys.executable, 'scripts/collectors/bsc_hybrid_collector.py', '--min-bnb', '1000'],
            'log': get_log_filename('bsc_whale')
        }
    ]
    
    # 프로세스 시작
    running_processes = []
    for config in process_configs:
        proc = start_process(config['name'], config['command'], config['log'])
        running_processes.append({
            'name': config['name'],
            'process': proc,
            'log': config['log']
        })
        processes.append(proc)
        time.sleep(2)  # 프로세스 간 간격
    
    # 프로세스 모니터링
    try:
        monitor_processes(running_processes)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    
    # 결과 요약
    print_summary(running_processes)
    
    # 모든 프로세스가 성공했는지 확인
    all_success = all(proc['process'].poll() == 0 for proc in running_processes)
    
    if all_success:
        print("✅ 모든 수집 작업이 성공적으로 완료되었습니다!")
        return 0
    else:
        print("⚠️ 일부 수집 작업이 실패했습니다. 로그를 확인하세요.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

