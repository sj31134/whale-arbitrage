# 로컬 vs 클라우드 서비스 비교 테스트 가이드

**작성일**: 2025-12-03  
**목적**: 로컬 서비스와 Streamlit Cloud 서비스 간의 차이점을 찾아 수정

---

## 🔍 발견된 문제점

### 1. Supabase 연결 문제
- **증상**: 클라우드에서 "btc 데이터가 없습니다", "데이터가 없습니다" 오류
- **원인**: `st.secrets` 접근 방식이 안전하지 않음
- **해결**: `st.secrets` 접근 방식을 더 안전하게 수정

### 2. 데이터 로딩 실패
- **증상**: 로컬에서는 정상 작동하지만 클라우드에서 데이터 로드 실패
- **원인**: Supabase 연결 실패 시 SQLite 폴백이 제대로 작동하지 않음

---

## 📋 비교 테스트 체크리스트

### 기본 기능 테스트

#### 1. 리스크 예측 대시보드
- [ ] **로컬**: BTC 데이터 로드 확인
- [ ] **클라우드**: BTC 데이터 로드 확인
- [ ] **로컬**: ETH 데이터 로드 확인
- [ ] **클라우드**: ETH 데이터 로드 확인
- [ ] **로컬**: 리스크 점수 계산 확인
- [ ] **클라우드**: 리스크 점수 계산 확인

#### 2. 파생상품 지표 분석
- [ ] **로컬**: OI 데이터 표시 확인
- [ ] **클라우드**: OI 데이터 표시 확인
- [ ] **로컬**: 펀딩비 데이터 표시 확인
- [ ] **클라우드**: 펀딩비 데이터 표시 확인
- [ ] **로컬**: Taker 비율 데이터 표시 확인
- [ ] **클라우드**: Taker 비율 데이터 표시 확인

#### 3. 동적 변수 분석
- [ ] **로컬**: 동적 변수 차트 표시 확인
- [ ] **클라우드**: 동적 변수 차트 표시 확인
- [ ] **로컬**: 상관관계 분석 결과 확인
- [ ] **클라우드**: 상관관계 분석 결과 확인

#### 4. 모델 성능 비교
- [ ] **로컬**: 모델 선택 및 비교 확인
- [ ] **클라우드**: 모델 선택 및 비교 확인
- [ ] **로컬**: 날짜별 예측 결과 확인
- [ ] **클라우드**: 날짜별 예측 결과 확인

#### 5. 종합 대시보드
- [ ] **로컬**: 모든 섹션 표시 확인
- [ ] **클라우드**: 모든 섹션 표시 확인
- [ ] **로컬**: 거래소 유입/유출 데이터 확인
- [ ] **클라우드**: 거래소 유입/유출 데이터 확인

---

## 🔧 수정 사항

### 1. `st.secrets` 접근 방식 개선

**수정 전:**
```python
supabase_url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
```

**수정 후:**
```python
supabase_url = None
try:
    if hasattr(st, 'secrets'):
        if hasattr(st.secrets, 'get'):
            supabase_url = st.secrets.get("SUPABASE_URL", None)
        elif "SUPABASE_URL" in st.secrets:
            supabase_url = st.secrets["SUPABASE_URL"]
except (KeyError, AttributeError, TypeError):
    pass

if not supabase_url:
    supabase_url = os.getenv("SUPABASE_URL")
```

### 2. Supabase 연결 실패 시 폴백 로직 개선

- Supabase 연결 실패 시 명확한 오류 메시지 표시
- SQLite 폴백이 제대로 작동하도록 수정

---

## 🧪 테스트 방법

### 로컬 테스트
```bash
# 로컬 서비스 실행
streamlit run app/main.py

# 테스트 스크립트 실행
python3 scripts/test_local_vs_cloud.py
```

### 클라우드 테스트
1. Streamlit Cloud 대시보드 접속
2. 배포된 앱 URL 접속
3. 각 페이지별로 기능 테스트
4. 배포 로그 확인

---

## 📊 예상 결과

### 정상 동작 시
- ✅ 모든 페이지에서 데이터 정상 로드
- ✅ BTC/ETH 데이터 모두 표시
- ✅ 리스크 점수 정상 계산
- ✅ 차트 및 그래프 정상 표시

### 문제 발생 시
- ❌ "데이터가 없습니다" 오류
- ❌ "btc 데이터가 없습니다" 오류
- ❌ Supabase 연결 실패 메시지
- ❌ 차트가 비어있음

---

## 🎯 다음 단계

1. **코드 수정 완료 확인**
   - [x] `st.secrets` 접근 방식 개선
   - [ ] Supabase 연결 폴백 로직 개선

2. **GitHub 푸시 및 재배포**
   - [ ] 수정된 코드 커밋
   - [ ] GitHub 푸시
   - [ ] Streamlit Cloud 자동 재배포 확인

3. **클라우드 테스트**
   - [ ] 배포된 앱 접속
   - [ ] 각 페이지별 기능 테스트
   - [ ] 오류 없이 정상 작동 확인

---

## 📝 참고

- **로컬 URL**: http://localhost:8501/
- **클라우드 URL**: https://whale-arbitrage-qwodzy8wpnhpgxaxt23rj8.streamlit.app/
- **테스트 스크립트**: `scripts/test_local_vs_cloud.py`

