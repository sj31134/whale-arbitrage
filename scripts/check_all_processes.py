#!/usr/bin/env python3
"""
현재 실행 중인 모든 whale_tracking 관련 프로세스 상태 확인
"""

import subprocess
import sys
from datetime import datetime

def get_process_info():
    """실행 중인 Python 프로세스 정보 수집"""
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        
        lines = result.stdout.split('\n')
        processes = []
        
        for line in lines:
            if 'whale_tracking' in line or 'update' in line or 'label' in line or 'direction' in line:
                if 'grep' not in line and 'check_all' not in line:
                    processes.append(line)
        
        return processes
    except Exception as e:
        print(f"❌ 프로세스 정보 수집 실패: {e}")
        return []

def analyze_processes():
    print("\n" + "=" * 80)
    print("📊 현재 실행 중인 작업 현황 분석")
    print("=" * 80)
    print(f"확인 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    processes = get_process_info()
    
    if not processes:
        print("✅ 실행 중인 whale_tracking 관련 프로세스가 없습니다.")
        return
    
    print(f"🔍 발견된 프로세스: {len(processes)}개\n")
    
    # 프로세스 분류
    direction_processes = []
    label_processes = []
    usd_processes = []
    other_processes = []
    
    for proc in processes:
        if 'update_direction' in proc or 'direction' in proc:
            direction_processes.append(proc)
        elif 'label' in proc or 'update_label' in proc:
            label_processes.append(proc)
        elif 'usd' in proc or 'amount_usd' in proc:
            usd_processes.append(proc)
        else:
            other_processes.append(proc)
    
    # 1. transaction_direction 관련
    if direction_processes:
        print("1️⃣ transaction_direction 업데이트 작업:")
        for proc in direction_processes:
            parts = proc.split()
            if len(parts) >= 11:
                pid = parts[1]
                cpu = parts[2]
                mem = parts[3]
                time_str = parts[9] if len(parts) > 9 else "N/A"
                cmd = ' '.join(parts[10:])
                print(f"   PID: {pid} | CPU: {cpu}% | MEM: {mem}% | 시간: {time_str}")
                print(f"   명령: {cmd[:80]}...")
        print()
    
    # 2. 라벨 업데이트 관련
    if label_processes:
        print("2️⃣ 라벨 업데이트 작업:")
        for proc in label_processes:
            parts = proc.split()
            if len(parts) >= 11:
                pid = parts[1]
                cpu = parts[2]
                mem = parts[3]
                time_str = parts[9] if len(parts) > 9 else "N/A"
                cmd = ' '.join(parts[10:])
                print(f"   PID: {pid} | CPU: {cpu}% | MEM: {mem}% | 시간: {time_str}")
                print(f"   명령: {cmd[:80]}...")
        print()
    
    # 3. USD 업데이트 관련
    if usd_processes:
        print("3️⃣ amount_usd 업데이트 작업:")
        for proc in usd_processes:
            parts = proc.split()
            if len(parts) >= 11:
                pid = parts[1]
                cpu = parts[2]
                mem = parts[3]
                time_str = parts[9] if len(parts) > 9 else "N/A"
                cmd = ' '.join(parts[10:])
                print(f"   PID: {pid} | CPU: {cpu}% | MEM: {mem}% | 시간: {time_str}")
                print(f"   명령: {cmd[:80]}...")
        print()
    
    # 4. 기타
    if other_processes:
        print("4️⃣ 기타 작업:")
        for proc in other_processes:
            parts = proc.split()
            if len(parts) >= 11:
                pid = parts[1]
                cpu = parts[2]
                mem = parts[3]
                time_str = parts[9] if len(parts) > 9 else "N/A"
                cmd = ' '.join(parts[10:])
                print(f"   PID: {pid} | CPU: {cpu}% | MEM: {mem}% | 시간: {time_str}")
                print(f"   명령: {cmd[:80]}...")
        print()
    
    # 분석 및 권장사항
    print("=" * 80)
    print("💡 분석 및 권장사항:")
    print("=" * 80)
    
    total_cpu = sum(float(p.split()[2]) for p in processes if len(p.split()) > 2)
    
    if total_cpu < 0.1:
        print("⚠️ 모든 프로세스의 CPU 사용률이 매우 낮습니다 (0.0%).")
        print("   → 대부분 대기 상태이거나 타임아웃으로 멈춘 상태일 가능성이 높습니다.")
        print("   → 프로세스를 중단하고 더 효율적인 방법으로 재시작하는 것을 권장합니다.")
    else:
        print(f"✅ 일부 프로세스가 활발히 작업 중입니다 (총 CPU: {total_cpu:.1f}%)")
    
    if len(direction_processes) > 0:
        print("\n📌 transaction_direction 업데이트:")
        print("   - 현재 방식은 매우 느립니다 (1건씩 처리)")
        print("   - 권장: SQL로 일괄 처리하거나 코인별 병렬 처리 스크립트 사용")
    
    if len(label_processes) > 1:
        print("\n⚠️ 라벨 업데이트 프로세스가 중복 실행 중입니다.")
        print("   - 불필요한 리소스 낭비 및 DB 부하 발생 가능")
        print("   - 중복 프로세스 중단 권장")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    analyze_processes()

