# Streamlit Cloud 배포 가이드

## 🚀 가장 간단한 배포 방법!

GitHub + Streamlit Cloud를 사용하면 **무료로** 서비스를 배포할 수 있습니다.

---

## 📋 배포 단계

### 1. GitHub에 코드 푸시
```bash
git add .
git commit -m "Deploy to Streamlit Cloud"
git push
```

### 2. Streamlit Cloud에 배포
1. [Streamlit Cloud](https://streamlit.io/cloud) 접속
2. GitHub로 로그인
3. "New app" 클릭
4. 설정:
   - Repository: `yourusername/whale_tracking`
   - Main file: `app/main.py`
5. Secrets에 환경 변수 추가:
   ```
   ECOS_API_KEY=your_key
   ```
6. Deploy!

### 3. 접속
- URL: `https://your-app-name.streamlit.app`

---

## ⚠️ 주의사항

### 데이터베이스 처리
Streamlit Cloud는 임시 파일 시스템을 사용하므로:
- 방법 1: GitHub Releases에 DB 업로드 후 앱 시작 시 다운로드
- 방법 2: Supabase 등 외부 DB 사용

---

## 📚 자세한 가이드

[docs/streamlit_cloud_deployment.md](docs/streamlit_cloud_deployment.md)를 참조하세요.

---

## 🔄 업데이트

코드를 수정하고 GitHub에 푸시하면 자동으로 재배포됩니다!

