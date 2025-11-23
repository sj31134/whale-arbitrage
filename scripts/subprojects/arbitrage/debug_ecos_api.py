#!/usr/bin/env python3
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / "config" / ".env")

ECOS_API_KEY = os.getenv("ECOS_API_KEY")

# URL 끝에 /json/통계표코드/주기/시작일자/종료일자/항목코드1/... 형식으로 요청
# 샘플: http://ecos.bok.or.kr/api/StatisticSearch/KEY/json/kr/1/10/036Y001/DD/20230101/20230105/0000001

def test_ecos_api():
    if not ECOS_API_KEY:
        print("❌ ECOS_API_KEY 없음")
        return

    # 시도 5: StatisticSearch 재시도 (끝에 슬래시 추가)
    stat_code = "731Y001"
    item_code = "0000001"
    start_date = "20240101"
    end_date = "20240105"
    cycle = "D" # D로 변경해봄 (응답값 기준)

    # http://ecos.bok.or.kr/api/StatisticSearch/인증키/json/kr/1/10/731Y001/D/20240101/20240105/0000001/
    url = f"http://ecos.bok.or.kr/api/StatisticSearch/{ECOS_API_KEY}/json/kr/1/10/{stat_code}/{cycle}/{start_date}/{end_date}/{item_code}/"
    
    print(f"Testing URL: {url.replace(ECOS_API_KEY, 'API_KEY')}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Body: {response.text[:500]}")
        
        try:
            data = response.json()
            if "StatisticSearch" in data:
                print("✅ 성공: 데이터 수신됨")
                print(data["StatisticSearch"]["row"][0])
            else:
                print("❌ 실패: 응답 형식 오류")
        except:
            print("❌ 실패: JSON 파싱 오류")
            
    except Exception as e:
        print(f"❌ 요청 오류: {e}")

if __name__ == "__main__":
    test_ecos_api()

