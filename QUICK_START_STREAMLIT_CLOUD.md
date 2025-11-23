# 🚀 Streamlit Cloud 빠른 배포 가이드

## 1️⃣ GitHub 저장소 생성 및 푸시

### 자동 스크립트 사용 (GitHub CLI 설치 필요)
```bash
./scripts/setup_github_repo.sh whale-arbitrage YOUR_GITHUB_USERNAME
```

### 수동 방법
```bash
# 1. GitHub에서 저장소 생성
# https://github.com/new 접속하여 저장소 생성

# 2. 원격 저장소 추가 및 푸시
git remote add origin https://github.com/YOUR_USERNAME/whale-arbitrage.git
git branch -M main
git push -u origin main
```

## 2️⃣ 데이터베이스 파일 업로드

```bash
# 데이터베이스 압축
tar -czf project.db.tar.gz data/project.db

# GitHub Releases에 업로드
# https://github.com/YOUR_USERNAME/whale-arbitrage/releases/new
# Tag: v1.0.0
# project.db.tar.gz 파일 업로드
```

## 3️⃣ Streamlit Cloud 배포

1. https://share.streamlit.io/ 접속
2. GitHub로 로그인
3. "New app" 클릭
4. 설정:
   - Repository: `YOUR_USERNAME/whale-arbitrage`
   - Main file: `app/main.py`
5. Secrets 추가:
   ```
   ECOS_API_KEY=your_key
   DATABASE_URL=https://github.com/YOUR_USERNAME/whale-arbitrage/releases/download/v1.0.0/project.db.tar.gz
   ```
6. Deploy!

## 4️⃣ 완료!

배포된 URL로 접속하여 사용하세요!

---

**자세한 내용**: [README_STREAMLIT_CLOUD_SETUP.md](README_STREAMLIT_CLOUD_SETUP.md)

