# Streamlit Cloud 배포 체크리스트

## ✅ 완료된 작업

- [x] `.gitignore` 파일 생성 및 설정
- [x] Git 저장소 초기화
- [x] 모든 파일 커밋 준비
- [x] Streamlit Cloud 호환 코드 수정
- [x] 데이터베이스 다운로드 로직 추가
- [x] 환경 변수 관리 개선

## 📋 배포 전 확인 사항

### 1. GitHub 저장소 생성
- [ ] GitHub에서 새 저장소 생성
- [ ] 저장소 이름: `whale-arbitrage` (또는 원하는 이름)
- [ ] Public 또는 Private 선택

### 2. 코드 푸시
```bash
# 원격 저장소 추가 (저장소 생성 후)
git remote add origin https://github.com/YOUR_USERNAME/whale-arbitrage.git
git branch -M main
git push -u origin main
```

또는 자동 스크립트:
```bash
./scripts/setup_github_repo.sh whale-arbitrage YOUR_USERNAME
```

### 3. 데이터베이스 파일 처리
- [ ] `data/project.db` 파일 압축: `tar -czf project.db.tar.gz data/project.db`
- [ ] GitHub Releases에 업로드
- [ ] 다운로드 URL 확인

### 4. Streamlit Cloud 배포
- [ ] https://share.streamlit.io/ 접속
- [ ] GitHub로 로그인
- [ ] "New app" 클릭
- [ ] Repository: `YOUR_USERNAME/whale-arbitrage`
- [ ] Branch: `main`
- [ ] Main file: `app/main.py`
- [ ] Secrets 설정:
  ```
  ECOS_API_KEY=your_key
  DATABASE_URL=https://github.com/YOUR_USERNAME/whale-arbitrage/releases/download/v1.0.0/project.db.tar.gz
  ```
- [ ] Deploy 클릭

### 5. 배포 확인
- [ ] 앱 URL로 접속 확인
- [ ] 로그에서 오류 확인
- [ ] 기능 테스트

## 🔧 문제 발생 시

1. **데이터베이스 오류**: Secrets의 `DATABASE_URL` 확인
2. **Import 오류**: `requirements.txt` 확인
3. **환경 변수 오류**: Secrets 설정 확인

## 📚 참고 문서

- [README_STREAMLIT_CLOUD_SETUP.md](README_STREAMLIT_CLOUD_SETUP.md)
- [docs/streamlit_cloud_deployment.md](docs/streamlit_cloud_deployment.md)

