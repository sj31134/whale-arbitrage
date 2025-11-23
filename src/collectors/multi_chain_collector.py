#!/usr/bin/env python3
"""
멀티체인 블록체인 탐색기 API를 통한 거래 기록 수집
Etherscan, SoChain, Subscan, Solscan API 지원
"""

import os
import time
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pathlib import Path

# 환경변수 로드
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

# API 키 로드
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')
SOCHAIN_API_KEY = os.getenv('SOCHAIN_API_KEY', '')
SUBSCAN_API_KEY = os.getenv('SUBSCAN_API_KEY', '')
SOLSCAN_API_KEY = os.getenv('SOLSCAN_API_KEY', '')

# LINK 토큰 컨트랙트 주소
LINK_CONTRACT_ADDRESS = '0x514910771AF9Ca656af840dff83E8264EcF986CA'


def fetch_etherscan_transactions(addresses: List[str], chain: str, api_key: str) -> List[Dict]:
    """
    Etherscan API V2를 사용하여 거래 기록 수집
    
    Parameters:
    -----------
    addresses : List[str]
        지갑 주소 리스트
    chain : str
        체인 타입 ('ethereum' 또는 'bsc')
    api_key : str
        Etherscan API 키
    
    Returns:
    --------
    List[Dict] : 거래 기록 리스트
    """
    if not api_key:
        return []
    
    # API 엔드포인트 설정 (V2 API 사용)
    if chain.lower() == 'bsc':
        base_url = 'https://api.bscscan.com/v2/api'
        chainid = 56  # BSC chainid
    else:
        base_url = 'https://api.etherscan.io/v2/api'
        chainid = 1  # Ethereum mainnet chainid
    
    all_transactions = []
    
    for address in addresses:
        try:
            # 네이티브 코인 거래 조회 (V2 API)
            params = {
                'chainid': chainid,  # V2 API 필수 파라미터
                'module': 'account',
                'action': 'txlist',
                'address': address,
                'startblock': 0,
                'endblock': 99999999,
                'sort': 'desc',
                'page': 1,
                'offset': 10000,  # 최대 10,000건
                'apikey': api_key
            }
            
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '1' and data.get('result'):
                result = data['result']
                if isinstance(result, list):
                    for tx in result:
                        try:
                            value = int(tx.get('value', 0)) / 1e18
                            coin_symbol = 'BNB' if chain.lower() == 'bsc' else 'ETH'
                            
                            all_transactions.append({
                                'tx_hash': tx.get('hash'),
                                'block_number': int(tx.get('blockNumber', 0)),
                                'block_timestamp': datetime.fromtimestamp(int(tx.get('timeStamp', 0))),
                                'from_address': tx.get('from', '').lower(),
                                'to_address': tx.get('to', '').lower() if tx.get('to') else None,
                                'value': value,
                                'coin_symbol': coin_symbol,
                                'chain': chain.lower(),
                                'gas_used': int(tx.get('gasUsed', 0)),
                                'gas_price': int(tx.get('gasPrice', 0)),
                                'is_error': tx.get('isError') == '1',
                            })
                        except Exception as e:
                            continue
            
            # LINK 토큰 거래 조회 (Ethereum만, V2 API)
            if chain.lower() == 'ethereum':
                token_params = {
                    'chainid': chainid,  # V2 API 필수 파라미터
                    'module': 'account',
                    'action': 'tokentx',
                    'contractaddress': LINK_CONTRACT_ADDRESS,
                    'address': address,
                    'sort': 'desc',
                    'page': 1,
                    'offset': 10000,
                    'apikey': api_key
                }
                
                token_response = requests.get(base_url, params=token_params, timeout=30)
                token_response.raise_for_status()
                token_data = token_response.json()
                
                if token_data.get('status') == '1' and token_data.get('result'):
                    for tx in token_data['result']:
                        try:
                            value = int(tx.get('value', 0)) / (10 ** int(tx.get('tokenDecimal', 18)))
                            
                            all_transactions.append({
                                'tx_hash': tx.get('hash'),
                                'block_number': int(tx.get('blockNumber', 0)),
                                'block_timestamp': datetime.fromtimestamp(int(tx.get('timeStamp', 0))),
                                'from_address': tx.get('from', '').lower(),
                                'to_address': tx.get('to', '').lower() if tx.get('to') else None,
                                'value': value,
                                'coin_symbol': 'LINK',
                                'chain': 'ethereum',
                                'contract_address': tx.get('contractAddress', '').lower(),
                                'gas_used': int(tx.get('gasUsed', 0)),
                                'gas_price': int(tx.get('gasPrice', 0)),
                                'is_error': False,
                            })
                        except Exception as e:
                            continue
            
            # Rate limit 방지
            time.sleep(0.25)
            
        except Exception as e:
            continue
    
    return all_transactions


def fetch_sochain_transactions(addresses: List[str], coin: str, api_key: str) -> List[Dict]:
    """
    SoChain API를 사용하여 거래 기록 수집 (BTC, LTC, DOGE)
    
    Parameters:
    -----------
    addresses : List[str]
        지갑 주소 리스트
    coin : str
        코인 타입 ('BTC', 'LTC', 'DOGE')
    api_key : str
        SoChain API 키 (선택사항)
    
    Returns:
    --------
    List[Dict] : 거래 기록 리스트
    """
    all_transactions = []
    
    # SoChain API 엔드포인트 (v2 사용, v3는 제한적)
    base_url = f'https://sochain.com/api/v2/get_address_transactions/{coin}'
    
    for address in addresses:
        try:
            # 주소의 거래 기록 조회
            url = f'{base_url}/{address}'
            headers = {}
            if api_key:
                headers['X-API-Key'] = api_key
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'success' and data.get('data'):
                transactions = data['data'].get('txs', [])
                
                for tx in transactions:
                    try:
                        # SoChain API 응답 구조에 따라 파싱
                        tx_hash = tx.get('txid', '')
                        block_height = tx.get('block_no', 0)
                        time_ts = tx.get('time', 0)
                        
                        # 입력/출력에서 주소와 금액 추출
                        inputs = tx.get('inputs', [])
                        outputs = tx.get('outputs', [])
                        
                        # 입력에서 주소와 관련된 거래 (from_address)
                        for inp in inputs:
                            inp_address = inp.get('address', '')
                            if inp_address and inp_address.lower() == address.lower():
                                value = float(inp.get('value', 0)) / 1e8  # BTC/LTC/DOGE는 8 decimal
                                
                                # 출력 주소 찾기
                                to_address = None
                                for out in outputs:
                                    out_address = out.get('address', '')
                                    if out_address and out_address.lower() != address.lower():
                                        to_address = out_address.lower()
                                        break
                                
                                all_transactions.append({
                                    'tx_hash': tx_hash,
                                    'block_number': block_height,
                                    'block_timestamp': datetime.fromtimestamp(time_ts) if time_ts else datetime.now(),
                                    'from_address': address.lower(),
                                    'to_address': to_address,
                                    'value': value,
                                    'coin_symbol': coin,
                                    'chain': coin.lower(),
                                    'is_error': False,
                                })
                        
                        # 출력에서 주소와 관련된 거래 (to_address)
                        for out in outputs:
                            out_address = out.get('address', '')
                            if out_address and out_address.lower() == address.lower():
                                value = float(out.get('value', 0)) / 1e8  # BTC/LTC/DOGE는 8 decimal
                                
                                # 입력 주소 찾기
                                from_address = None
                                for inp in inputs:
                                    inp_address = inp.get('address', '')
                                    if inp_address and inp_address.lower() != address.lower():
                                        from_address = inp_address.lower()
                                        break
                                
                                all_transactions.append({
                                    'tx_hash': tx_hash,
                                    'block_number': block_height,
                                    'block_timestamp': datetime.fromtimestamp(time_ts) if time_ts else datetime.now(),
                                    'from_address': from_address,
                                    'to_address': address.lower(),
                                    'value': value,
                                    'coin_symbol': coin,
                                    'chain': coin.lower(),
                                    'is_error': False,
                                })
                    except Exception as e:
                        continue
            
            # Rate limit 방지
            time.sleep(0.5)
            
        except Exception as e:
            continue
    
    return all_transactions


def fetch_subscan_transactions(addresses: List[str], api_key: str) -> List[Dict]:
    """
    Subscan API를 사용하여 Polkadot (DOT) 거래 기록 수집
    
    Parameters:
    -----------
    addresses : List[str]
        지갑 주소 리스트
    api_key : str
        Subscan API 키
    
    Returns:
    --------
    List[Dict] : 거래 기록 리스트
    """
    if not api_key:
        return []
    
    all_transactions = []
    
    # Subscan Polkadot API 엔드포인트
    base_url = 'https://polkadot.api.subscan.io/api/scan/transfers'
    
    for address in addresses:
        try:
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': api_key
            }
            
            payload = {
                'address': address,
                'page': 0,
                'row': 100
            }
            
            response = requests.post(base_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == 0 and data.get('data'):
                transfers = data['data'].get('transfers', [])
                
                for transfer in transfers:
                    try:
                        amount = float(transfer.get('amount', 0)) / 1e10  # DOT는 10 decimal
                        
                        all_transactions.append({
                            'tx_hash': transfer.get('hash', ''),
                            'block_number': transfer.get('block_num', 0),
                            'block_timestamp': datetime.fromtimestamp(transfer.get('block_timestamp', 0)),
                            'from_address': transfer.get('from', '').lower(),
                            'to_address': transfer.get('to', '').lower(),
                            'value': amount,
                            'coin_symbol': 'DOT',
                            'chain': 'polkadot',
                            'is_error': transfer.get('success', True) == False,
                        })
                    except Exception as e:
                        continue
            
            # Rate limit 방지
            time.sleep(0.5)
            
        except Exception as e:
            continue
    
    return all_transactions


def fetch_solscan_transactions(addresses: List[str], api_key: str) -> List[Dict]:
    """
    Solscan API를 사용하여 Solana (SOL) 거래 기록 수집
    
    Parameters:
    -----------
    addresses : List[str]
        지갑 주소 리스트
    api_key : str
        Solscan API 키
    
    Returns:
    --------
    List[Dict] : 거래 기록 리스트
    """
    if not api_key:
        return []
    
    all_transactions = []
    
    # Solscan API 엔드포인트
    base_url = 'https://public-api.solscan.io/account/transactions'
    
    for address in addresses:
        try:
            headers = {
                'token': api_key
            }
            
            params = {
                'account': address,
                'limit': 100
            }
            
            response = requests.get(base_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                for tx in data:
                    try:
                        # Solana 거래 파싱
                        tx_hash = tx.get('txHash', '')
                        block_time = tx.get('blockTime', 0)
                        slot = tx.get('slot', 0)
                        
                        # 거래 금액 추출 (Solana는 복잡한 구조)
                        amount = float(tx.get('amount', 0)) / 1e9  # SOL은 9 decimal
                        
                        all_transactions.append({
                            'tx_hash': tx_hash,
                            'block_number': slot,
                            'block_timestamp': datetime.fromtimestamp(block_time),
                            'from_address': address.lower(),
                            'to_address': None,  # Solana는 복잡한 구조
                            'value': amount,
                            'coin_symbol': 'SOL',
                            'chain': 'solana',
                            'is_error': tx.get('err', None) is not None,
                        })
                    except Exception as e:
                        continue
            
            # Rate limit 방지
            time.sleep(0.5)
            
        except Exception as e:
            continue
    
    return all_transactions


def fetch_vtc_transactions(addresses: List[str]) -> List[Dict]:
    """
    VTC (Vertcoin) 거래 기록 수집 (공개 API 사용)
    
    Parameters:
    -----------
    addresses : List[str]
        지갑 주소 리스트
    
    Returns:
    --------
    List[Dict] : 거래 기록 리스트
    """
    all_transactions = []
    
    # Vertcoin Explorer API (공개 API)
    # 참고: VTC는 공개 API가 제한적이므로 기본적인 구조만 제공
    base_url = 'https://explorer.vertcoin.org/api'
    
    for address in addresses:
        try:
            # 주소 정보 조회
            url = f'{base_url}/addr/{address}'
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # 거래 기록 추출
            transactions = data.get('transactions', [])
            
            for tx_id in transactions:
                try:
                    # 거래 상세 조회
                    tx_url = f'{base_url}/tx/{tx_id}'
                    tx_response = requests.get(tx_url, timeout=30)
                    tx_response.raise_for_status()
                    tx_data = tx_response.json()
                    
                    # 거래 파싱
                    block_height = tx_data.get('blockheight', 0)
                    time_ts = tx_data.get('time', 0)
                    value = float(tx_data.get('valueOut', 0)) / 1e8  # VTC는 8 decimal
                    
                    all_transactions.append({
                        'tx_hash': tx_id,
                        'block_number': block_height,
                        'block_timestamp': datetime.fromtimestamp(time_ts),
                        'from_address': address.lower(),
                        'to_address': None,
                        'value': value,
                        'coin_symbol': 'VTC',
                        'chain': 'vertcoin',
                        'is_error': False,
                    })
                    
                    # Rate limit 방지
                    time.sleep(0.5)
                    
                except Exception as e:
                    continue
            
            # Rate limit 방지
            time.sleep(1)
            
        except Exception as e:
            continue
    
    return all_transactions

