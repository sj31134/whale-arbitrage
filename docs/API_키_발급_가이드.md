# 🔑 API 키 발급 가이드

## 📋 필요한 API 키 목록

### 필수 (블록체인 거래 기록 수집용)
1. **Etherscan API Key** - Ethereum 체인 거래 기록 조회
2. **BSCScan API Key** - BSC 체인 거래 기록 조회

### 선택 (향후 확장용)
3. **BlockCypher API Key** - Bitcoin 체인 거래 기록 조회
4. **PolygonScan API Key** - Polygon 체인 거래 기록 조회

---

## 1️⃣ Etherscan API Key 발급

### 발급 방법
1. **웹사이트 접속**: https://etherscan.io/
2. **회원가입/로그인**
   - 우측 상단 "Sign Up" 또는 "Login" 클릭
   - 이메일로 회원가입 (무료)
3. **API 키 생성**
   - 로그인 후 우측 상단 프로필 아이콘 클릭
   - "API-KEYs" 메뉴 선택
   - "Add" 버튼 클릭
   - API Key 이름 입력 (예: "whale_tracking")
   - "Create" 클릭
4. **API 키 복사**
   - 생성된 API Key를 복사
   - `.env` 파일에 추가:
     ```env
     ETHERSCAN_API_KEY=your_api_key_here
     ```

### 무료 플랜 제한
- **Rate Limit**: 5 calls/second
- **일일 제한**: 100,000 calls/day
- **충분한 제한**: 일반적인 사용에는 충분

### API 문서
- https://docs.etherscan.io/

---

## 2️⃣ BSCScan API Key 발급

### 발급 방법
1. **웹사이트 접속**: https://bscscan.com/
2. **회원가입/로그인**
   - 우측 상단 "Sign Up" 또는 "Login" 클릭
   - Etherscan 계정과 연동 가능 (같은 계정 사용 가능)
3. **API 키 생성**
   - 로그인 후 우측 상단 프로필 아이콘 클릭
   - "API-KEYs" 메뉴 선택
   - "Add" 버튼 클릭
   - API Key 이름 입력 (예: "whale_tracking")
   - "Create" 클릭
4. **API 키 복사**
   - 생성된 API Key를 복사
   - `.env` 파일에 추가:
     ```env
     BSCSCAN_API_KEY=your_api_key_here
     ```

### 무료 플랜 제한
- **Rate Limit**: 5 calls/second
- **일일 제한**: 100,000 calls/day
- **충분한 제한**: 일반적인 사용에는 충분

### API 문서
- https://docs.bscscan.com/

---

## 3️⃣ .env 파일 설정

프로젝트 루트의 `config/.env` 파일에 다음을 추가:

```env
# Etherscan API (Ethereum)
ETHERSCAN_API_KEY=your_etherscan_api_key_here

# BSCScan API (BSC)
BSCSCAN_API_KEY=your_bscscan_api_key_here
```

### .env 파일 위치 확인
```bash
cd /Users/junyonglee/Documents/GitHub/whale_tracking
ls -la config/.env
```

### .env 파일이 없으면 생성
```bash
mkdir -p config
touch config/.env
# 파일 편집기로 위의 내용 추가
```

---

## 4️⃣ API 키 확인 방법

### Python 스크립트로 확인
```python
import os
from dotenv import load_dotenv

load_dotenv('config/.env')

etherscan_key = os.getenv('ETHERSCAN_API_KEY')
bscscan_key = os.getenv('BSCSCAN_API_KEY')

print(f"Etherscan API Key: {'✅ 설정됨' if etherscan_key else '❌ 없음'}")
print(f"BSCScan API Key: {'✅ 설정됨' if bscscan_key else '❌ 없음'}")
```

### 테스트 스크립트 실행
```bash
python test_api_keys.py
```

---

## 5️⃣ API 키 보안 주의사항

### ⚠️ 중요
- **절대 Git에 커밋하지 마세요**
- `.env` 파일은 `.gitignore`에 추가되어 있어야 합니다
- API 키가 노출되면 즉시 재발급하세요

### .gitignore 확인
```bash
cat .gitignore | grep .env
```

---

## 6️⃣ API 키 발급 체크리스트

- [ ] Etherscan 회원가입 완료
- [ ] Etherscan API Key 발급 완료
- [ ] BSCScan 회원가입 완료 (또는 Etherscan 계정 연동)
- [ ] BSCScan API Key 발급 완료
- [ ] `.env` 파일에 API 키 추가 완료
- [ ] API 키 테스트 완료

---

## 7️⃣ 문제 해결

### API 키가 작동하지 않는 경우
1. API 키가 올바르게 복사되었는지 확인
2. `.env` 파일의 경로가 올바른지 확인
3. API 키에 공백이나 특수문자가 없는지 확인
4. API 키가 활성화되어 있는지 확인 (Etherscan/BSCScan 대시보드)

### Rate Limit 오류
- API 호출 간 딜레이 추가
- 배치 처리로 API 호출 최소화
- 유료 플랜 고려 (필요시)

---

## 8️⃣ 추가 리소스

- [Etherscan API 문서](https://docs.etherscan.io/)
- [BSCScan API 문서](https://docs.bscscan.com/)
- [BlockCypher API](https://www.blockcypher.com/dev/bitcoin/) - Bitcoin용
- [PolygonScan API](https://polygonscan.com/apis) - Polygon용



