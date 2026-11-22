#!/usr/bin/env python3
"""
BSC Web Scraper Module

BSCscan 웹사이트에서 추가 거래 정보를 스크래핑하는 모듈
- 특정 tx_hash의 상세 페이지 스크래핑
- Method, Label, Direction 등 추가 정보 추출
- Rate limiting 관리
"""

import time
import re
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup
import requests

# 설정
BSCSCAN_BASE_URL = "https://bscscan.com"
MAX_RETRIES = 3
RETRY_DELAY = 2  # 초
REQUEST_TIMEOUT = 30  # 초


def get_headers():
    """
    요청 헤더 설정 - 봇으로 감지되지 않도록 User-Agent 설정
    """
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://bscscan.com/',
        'DNT': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin'
    }


def clean_text(text):
    """
    텍스트에서 불필요한 공백과 특수 문자 제거
    """
    if text is None:
        return ""
    return ' '.join(text.strip().split())


def extract_method(soup: BeautifulSoup) -> Optional[str]:
    """
    거래 Method 추출
    
    예: Transfer, Swap, Approve 등
    """
    try:
        # Method 정보는 여러 위치에 있을 수 있음
        # 1. span.u-label 태그
        method_span = soup.find('span', class_='u-label')
        if method_span:
            method = clean_text(method_span.get_text())
            if method:
                return method
        
        # 2. input data에서 function signature 추출
        input_data_section = soup.find('div', id='inputdata')
        if input_data_section:
            # Function signature 찾기
            func_match = re.search(r'Function:\s*([^\n]+)', input_data_section.get_text())
            if func_match:
                return clean_text(func_match.group(1))
        
        return None
    
    except Exception as e:
        print(f"⚠️ Method 추출 실패: {e}")
        return None


def extract_labels(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    """
    From/To 주소의 라벨 추출
    
    Returns:
    --------
    Tuple[Optional[str], Optional[str]] : (from_label, to_label)
    """
    try:
        from_label = None
        to_label = None
        
        # From/To 섹션 찾기
        rows = soup.find_all('div', class_='row')
        
        for row in rows:
            # From 라벨 찾기
            if 'From:' in row.get_text():
                label_span = row.find('span', attrs={'data-bs-toggle': 'tooltip'})
                if label_span:
                    from_label = clean_text(label_span.get_text())
                    # 주소가 아닌 라벨인 경우만
                    if not from_label.startswith('0x'):
                        pass
                    else:
                        from_label = None
            
            # To 라벨 찾기
            if 'To:' in row.get_text():
                label_span = row.find('span', attrs={'data-bs-toggle': 'tooltip'})
                if label_span:
                    to_label = clean_text(label_span.get_text())
                    # 주소가 아닌 라벨인 경우만
                    if not to_label.startswith('0x'):
                        pass
                    else:
                        to_label = None
        
        return from_label, to_label
    
    except Exception as e:
        print(f"⚠️ Label 추출 실패: {e}")
        return None, None


def extract_direction(soup: BeautifulSoup, target_address: str) -> Optional[str]:
    """
    거래 방향 추출 (IN/OUT)
    
    Parameters:
    -----------
    soup : BeautifulSoup
        파싱된 HTML
    target_address : str
        확인할 대상 주소
    
    Returns:
    --------
    Optional[str] : 'IN', 'OUT', 또는 None
    """
    try:
        target_address = target_address.lower()
        
        # From/To 주소 찾기
        from_address = None
        to_address = None
        
        rows = soup.find_all('div', class_='row')
        
        for row in rows:
            text = row.get_text()
            
            if 'From:' in text:
                addr_link = row.find('a', href=re.compile(r'/address/0x'))
                if addr_link:
                    from_address = addr_link.get('href').split('/address/')[-1].lower()
            
            if 'To:' in text:
                addr_link = row.find('a', href=re.compile(r'/address/0x'))
                if addr_link:
                    to_address = addr_link.get('href').split('/address/')[-1].lower()
        
        # 방향 판단
        if to_address and target_address in to_address:
            return 'IN'
        elif from_address and target_address in from_address:
            return 'OUT'
        
        return None
    
    except Exception as e:
        print(f"⚠️ Direction 추출 실패: {e}")
        return None


def extract_value_and_usd(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    """
    거래 금액과 USD 가치 추출
    
    Returns:
    --------
    Tuple[Optional[str], Optional[str]] : (amount_text, amount_usd)
    """
    try:
        # Value 섹션 찾기
        rows = soup.find_all('div', class_='row')
        
        for row in rows:
            if 'Value:' in row.get_text():
                # BNB 금액
                amount_span = row.find('span', class_='u-label--value')
                if amount_span:
                    amount_text = clean_text(amount_span.get_text())
                    
                    # USD 가치 (tooltip 또는 별도 표시)
                    usd_match = re.search(r'\$([0-9,]+\.[0-9]+)', row.get_text())
                    if usd_match:
                        amount_usd = usd_match.group(1).replace(',', '')
                        return amount_text, amount_usd
                    
                    return amount_text, None
        
        return None, None
    
    except Exception as e:
        print(f"⚠️ Value/USD 추출 실패: {e}")
        return None, None


def scrape_transaction_details(
    tx_hash: str,
    target_address: Optional[str] = None,
    session: Optional[requests.Session] = None
) -> Dict:
    """
    특정 거래의 상세 정보를 웹 스크래핑으로 수집
    
    Parameters:
    -----------
    tx_hash : str
        거래 해시
    target_address : Optional[str]
        Direction 판단을 위한 대상 주소
    session : Optional[requests.Session]
        재사용할 requests 세션
    
    Returns:
    --------
    Dict : 추가 정보 딕셔너리
        {
            'input_data': str,  # Method
            'from_label': str,
            'to_label': str,
            'direction': str,  # IN/OUT
            'amount_text': str,
            'amount_usd': str
        }
    """
    url = f"{BSCSCAN_BASE_URL}/tx/{tx_hash}"
    
    # 세션이 없으면 새로 생성
    if session is None:
        session = requests.Session()
        close_session = True
    else:
        close_session = False
    
    result = {
        'input_data': None,
        'from_label': None,
        'to_label': None,
        'direction': None,
        'amount_text': None,
        'amount_usd': None
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, headers=get_headers(), timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Rate limiting 체크
            if response.status_code == 429:
                wait_time = (attempt + 1) * RETRY_DELAY
                print(f"⚠️ Rate limit 도달. {wait_time}초 대기...")
                time.sleep(wait_time)
                continue
            
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 정보 추출
            result['input_data'] = extract_method(soup)
            result['from_label'], result['to_label'] = extract_labels(soup)
            
            if target_address:
                result['direction'] = extract_direction(soup, target_address)
            
            result['amount_text'], result['amount_usd'] = extract_value_and_usd(soup)
            
            # 성공
            return result
        
        except requests.exceptions.RequestException as e:
            print(f"⚠️ 스크래핑 실패 (시도 {attempt + 1}/{MAX_RETRIES}): {e}")
            
            if attempt < MAX_RETRIES - 1:
                wait_time = (attempt + 1) * RETRY_DELAY
                time.sleep(wait_time)
            else:
                print(f"❌ 거래 {tx_hash[:10]}... 스크래핑 최종 실패")
        
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            break
    
    if close_session:
        session.close()
    
    return result


def scrape_multiple_transactions(
    transactions: list,
    delay: float = RETRY_DELAY
) -> list:
    """
    여러 거래의 상세 정보를 순차적으로 스크래핑
    
    Parameters:
    -----------
    transactions : list
        거래 리스트 (각 항목은 'tx_hash' 필드 필요)
    delay : float
        요청 간 대기 시간 (초)
    
    Returns:
    --------
    list : 추가 정보가 포함된 거래 리스트
    """
    print(f"\n🌐 웹 스크래핑 시작: {len(transactions)}건")
    print(f"예상 소요 시간: 약 {len(transactions) * delay / 60:.1f}분")
    
    # 재사용할 세션 생성
    session = requests.Session()
    
    enriched_transactions = []
    success_count = 0
    
    try:
        for i, tx in enumerate(transactions, 1):
            tx_hash = tx.get('tx_hash')
            target_address = tx.get('from_address') or tx.get('to_address')
            
            if not tx_hash:
                print(f"⚠️ [{i}/{len(transactions)}] tx_hash 없음, 건너뜀")
                enriched_transactions.append(tx)
                continue
            
            print(f"[{i}/{len(transactions)}] {tx_hash[:10]}... 스크래핑 중...")
            
            # 스크래핑 실행
            additional_info = scrape_transaction_details(
                tx_hash, 
                target_address=target_address,
                session=session
            )
            
            # 기존 정보에 추가 정보 병합
            enriched_tx = tx.copy()
            
            # input_data 업데이트 (Method)
            if additional_info.get('input_data'):
                enriched_tx['input_data'] = additional_info['input_data']
            
            # Label 업데이트
            if additional_info.get('from_label'):
                enriched_tx['from_label'] = additional_info['from_label']
            
            if additional_info.get('to_label'):
                enriched_tx['to_label'] = additional_info['to_label']
            
            # USD 가치 업데이트
            if additional_info.get('amount_usd'):
                try:
                    enriched_tx['amount_usd'] = float(additional_info['amount_usd'])
                except:
                    pass
            
            enriched_transactions.append(enriched_tx)
            success_count += 1
            
            # 진행 상황
            if i % 10 == 0:
                print(f"  진행률: {i}/{len(transactions)} ({i/len(transactions)*100:.1f}%)")
                print(f"  성공: {success_count}건")
            
            # Rate limiting
            time.sleep(delay)
    
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
        print(f"처리 완료: {len(enriched_transactions)}/{len(transactions)}건")
    
    finally:
        session.close()
    
    print(f"\n✅ 웹 스크래핑 완료: {success_count}/{len(transactions)}건 성공")
    
    return enriched_transactions


def main():
    """메인 실행 함수 (테스트용)"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BSC Web Scraper')
    parser.add_argument('--tx-hash', type=str, help='테스트할 거래 해시')
    parser.add_argument('--address', type=str, help='Direction 판단용 주소')
    args = parser.parse_args()
    
    if args.tx_hash:
        print(f"🧪 테스트: {args.tx_hash}")
        result = scrape_transaction_details(args.tx_hash, args.address)
        
        print(f"\n📊 결과:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    else:
        print("사용법: python bsc_web_scraper.py --tx-hash 0x...")
        print("예시: python bsc_web_scraper.py --tx-hash 0x1234... --address 0xabcd...")


if __name__ == '__main__':
    main()

