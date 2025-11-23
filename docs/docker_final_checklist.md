# Docker 배포 최종 체크리스트

> **작성일**: 2025-11-23

---

## ✅ 배포 준비 완료

### 생성된 파일
- ✅ `Dockerfile` - Docker 이미지 빌드
- ✅ `docker-compose.yml` - 개발/테스트용
- ✅ `docker-compose.prod.yml` - 프로덕션용
- ✅ `.dockerignore` - 빌드 최적화
- ✅ 배포 스크립트들
- ✅ 문서들

---

## 🚀 배포 실행

### 1. 로컬 테스트
```bash
# 빌드 및 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 접속: http://localhost:8501
```

### 2. 프로덕션 배포
```bash
# 프로덕션 설정으로 배포
./scripts/docker_prod_deploy.sh

# 또는
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 🌐 외부 접속 설정

### 서버 준비
1. Docker 및 Docker Compose 설치
2. 프로젝트 업로드
3. 방화벽에서 포트 8501 열기
4. 배포 실행

### 접속
- 로컬 네트워크: `http://[서버IP]:8501`
- 인터넷: `http://[서버공인IP]:8501`

---

## 📋 배포 전 확인

- [ ] Docker 설치 확인
- [ ] Docker Compose 설치 확인
- [ ] `data/project.db` 파일 존재
- [ ] `config/.env` 파일 설정
- [ ] 포트 8501 사용 가능
- [ ] 방화벽 설정 (외부 접속 시)

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-11-23

