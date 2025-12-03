# Streamlit Cloud 트러블슈팅 가이드

## ✅ 검증 완료 사항

### 1. GitHub 코드 동기화
- ✅ 로컬과 원격 저장소 동기화됨
- ✅ 최신 커밋: `1ad759b` (디버그 UI 추가)
- ✅ 모든 수정사항이 GitHub에 푸시됨

### 2. SQLite DB 파일 상태
- ✅ 파일 존재: `data/project.db` (924 KB)
- ✅ 모든 필수 테이블 존재 (6개)
- ✅ 데이터 정상:
  - `upbit_daily`: 2,402행
  - `binance_spot_daily`: 2,116행
  - `bitget_spot_daily`: 1,388행
  - `exchange_rate`: 1,055행
- ✅ 모든 쿼리 테스트 통과

### 3. 압축 파일 상태
- ✅ `project.db.tar.gz` 존재 (343.82 KB)
- ✅ 압축 해제 테스트 성공
- ✅ 압축 해제 후 SQLite 연결 성공

### 4. GitHub Releases
- ✅ Release `v1.0.0` 존재
- ✅ `project.db.tar.gz` 파일 업로드됨
- ✅ 다운로드 URL: 
  ```
  https://github.com/sj31134/whale-arbitrage/releases/download/v1.0.0/project.db.tar.gz
  ```

## 🔍 Streamlit Cloud에서 확인할 사항

### 필수 확인: Secrets 설정

Streamlit Cloud 대시보드 → 앱 선택 → Settings → Secrets에서 다음이 설정되어 있어야 합니다:

```toml
DATABASE_URL = "https://github.com/sj31134/whale-arbitrage/releases/download/v1.0.0/project.db.tar.gz"
```

### UI에서 확인 가능한 디버그 정보

앱 실행 시 UI에 다음 정보가 표시됩니다:

1. **초기화 단계**:
   - "데이터베이스 초기화 중..." 스피너
   - 환경 정보 (Streamlit Cloud / 로컬)
   - DB 경로, 파일 존재 여부

2. **다운로드 단계** (파일이 없는 경우):
   - "데이터베이스 파일을 다운로드하는 중..."
   - 다운로드 URL
   - 다운로드 완료 및 파일 크기
   - 압축 해제 진행 상황

3. **연결 단계**:
   - "데이터베이스 연결 테스트 중..."
   - 연결 성공 시 테이블 개수
   - 테이블 누락 시 경고

4. **에러 발생 시**:
   - 상세한 에러 메시지
   - 디버그 정보 (JSON 형식)

## 🐛 가능한 문제 및 해결 방법

### 문제 1: "데이터베이스 파일을 찾을 수 없습니다"

**원인**:
- `DATABASE_URL`이 Secrets에 설정되지 않음
- 다운로드 실패
- 압축 해제 실패

**해결**:
1. Streamlit Cloud Secrets에 `DATABASE_URL` 확인
2. UI에 표시된 에러 메시지 확인
3. GitHub Releases URL이 올바른지 확인

### 문제 2: "데이터베이스 연결 실패"

**원인**:
- 파일이 손상됨
- 권한 문제
- 멀티스레드 문제

**해결**:
- 이미 `check_same_thread=False` 설정됨
- 지연 연결 패턴 사용 중
- UI에 표시된 상세 에러 확인

### 문제 3: "필수 테이블 누락"

**원인**:
- 데이터베이스 파일이 불완전함
- 압축 해제 실패

**해결**:
- GitHub Releases에서 파일 재다운로드
- 압축 파일이 올바른지 확인

## 📋 체크리스트

배포 전 확인:
- [ ] GitHub에 최신 코드 푸시됨
- [ ] `project.db.tar.gz` 파일이 GitHub Releases에 업로드됨
- [ ] Streamlit Cloud Secrets에 `DATABASE_URL` 설정됨
- [ ] URL이 올바른지 확인 (v1.0.0 태그)

배포 후 확인:
- [ ] 앱이 정상적으로 로드됨
- [ ] UI에 디버그 정보가 표시됨
- [ ] 데이터베이스 초기화 메시지 확인
- [ ] 에러 메시지가 있다면 내용 확인

## 🔗 참고 링크

- GitHub 저장소: https://github.com/sj31134/whale-arbitrage
- GitHub Releases: https://github.com/sj31134/whale-arbitrage/releases
- Streamlit Cloud: https://share.streamlit.io/

---
**작성일**: 2025-11-23
**최종 검증**: 모든 로컬 테스트 통과 ✅

