#!/usr/bin/env python3
"""API 키 설정 확인 스크립트"""

import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

print("=" * 70)
print("🔑 API 키 설정 확인")
print("=" * 70)

etherscan_key = os.getenv('ETHERSCAN_API_KEY')
bscscan_key = os.getenv('BSCSCAN_API_KEY')

print(f"\nEtherscan API Key: {'✅ 설정됨' if etherscan_key else '❌ 없음'}")
if etherscan_key:
    print(f"   키: {etherscan_key[:10]}...{etherscan_key[-5:]}")

print(f"\nBSCScan API Key: {'✅ 설정됨' if bscscan_key else '❌ 없음'}")
if bscscan_key:
    print(f"   키: {bscscan_key[:10]}...{bscscan_key[-5:]}")

print("\n" + "=" * 70)
if etherscan_key and bscscan_key:
    print("✅ 모든 API 키가 설정되었습니다!")
    print("   이제 collect_whale_transactions_from_blockchain.py를 실행할 수 있습니다.")
else:
    print("⚠️  일부 API 키가 설정되지 않았습니다.")
    print("   API_키_발급_가이드.md 파일을 참고하여 API 키를 발급하세요.")
print("=" * 70)



