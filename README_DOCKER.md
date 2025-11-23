# Docker 배포 가이드

## 🚀 빠른 시작

### 1. Docker 이미지 빌드 및 실행

```bash
# Docker Compose 사용 (권장)
docker-compose up -d --build

# 또는 스크립트 사용
./scripts/docker_deploy.sh
```

### 2. 접속

- 로컬: http://localhost:8501
- 외부: http://[서버IP]:8501

### 3. 로그 확인

```bash
docker-compose logs -f
```

### 4. 중지

```bash
docker-compose down
```

---

## 📋 필수 사항

1. **Docker 설치**: Docker 및 Docker Compose가 설치되어 있어야 합니다.
2. **데이터베이스**: `data/project.db` 파일이 존재해야 합니다.
3. **환경 변수**: `config/.env` 파일에 필요한 API 키가 설정되어 있어야 합니다.

---

## 🔧 설정

### 포트 변경

`docker-compose.yml`에서 포트를 변경할 수 있습니다:

```yaml
ports:
  - "8080:8501"  # 호스트 포트:컨테이너 포트
```

### 환경 변수

`.env` 파일은 자동으로 마운트됩니다. 필요한 환경 변수:
- `ECOS_API_KEY`: 한국은행 환율 API 키

---

## 🌐 외부 접속

### 클라우드 배포 (AWS, GCP, Azure)

1. 서버에 Docker 설치
2. 프로젝트 업로드
3. 방화벽에서 포트 8501 열기
4. `docker-compose up -d` 실행
5. `http://[서버IP]:8501` 접속

---

## 📚 자세한 가이드

자세한 내용은 [docs/docker_deployment_guide.md](docs/docker_deployment_guide.md)를 참조하세요.

