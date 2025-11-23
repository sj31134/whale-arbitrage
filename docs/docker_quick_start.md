# Docker 빠른 시작 가이드

> **작성일**: 2025-11-23

---

## 🚀 3단계로 배포하기

### 1단계: Docker 이미지 빌드

```bash
docker-compose build
```

### 2단계: 컨테이너 실행

```bash
docker-compose up -d
```

### 3단계: 접속

브라우저에서 접속:
- 로컬: http://localhost:8501
- 외부: http://[서버IP]:8501

---

## 📋 필수 확인 사항

- [ ] Docker 설치됨 (`docker --version`)
- [ ] Docker Compose 설치됨 (`docker-compose --version`)
- [ ] `data/project.db` 파일 존재
- [ ] `config/.env` 파일 설정됨

---

## 🔧 유용한 명령어

```bash
# 로그 확인
docker-compose logs -f

# 컨테이너 상태 확인
docker-compose ps

# 컨테이너 재시작
docker-compose restart

# 컨테이너 중지
docker-compose down

# 이미지 재빌드
docker-compose up -d --build
```

---

## 🌐 외부 접속 설정

### 로컬 네트워크
- 방화벽에서 포트 8501 열기
- `http://[서버IP]:8501` 접속

### 인터넷 (클라우드)
1. 클라우드 서버에 프로젝트 업로드
2. 방화벽/보안 그룹에서 포트 8501 허용
3. `docker-compose up -d` 실행
4. `http://[서버공인IP]:8501` 접속

---

**자세한 내용**: [docker_deployment_guide.md](docker_deployment_guide.md)

