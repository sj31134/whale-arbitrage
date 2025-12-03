# Docker 트러블슈팅 가이드

> **작성일**: 2025-11-23

---

## 🔍 일반적인 문제

### 1. 포트가 이미 사용 중

**에러**: `port is already allocated`

**해결**:
```bash
# 포트 사용 중인 프로세스 확인
lsof -i :8501

# 다른 포트 사용
# docker-compose.yml에서 포트 변경
ports:
  - "8502:8501"
```

### 2. 데이터베이스 접근 오류

**에러**: `unable to open database file`

**해결**:
```bash
# 데이터 디렉토리 권한 확인
ls -la data/

# 권한 수정
chmod -R 755 data/
chown -R $USER:$USER data/
```

### 3. 환경 변수 로드 실패

**에러**: `ECOS_API_KEY가 설정되지 않았습니다`

**해결**:
```bash
# .env 파일 확인
cat config/.env

# 컨테이너 내부 환경 변수 확인
docker exec arbitrage-ui env | grep ECOS
```

### 4. 이미지 빌드 실패

**에러**: `ModuleNotFoundError`

**해결**:
```bash
# requirements.txt 확인
cat requirements.txt

# 캐시 없이 재빌드
docker-compose build --no-cache
```

### 5. 컨테이너가 즉시 종료

**원인**: 애플리케이션 오류

**해결**:
```bash
# 로그 확인
docker-compose logs

# 컨테이너 내부 접속
docker exec -it arbitrage-ui /bin/bash
```

---

## 🔧 디버깅 명령어

### 컨테이너 상태 확인
```bash
docker ps -a
docker inspect arbitrage-ui
```

### 로그 확인
```bash
# 실시간 로그
docker-compose logs -f

# 최근 100줄
docker-compose logs --tail=100

# 특정 서비스만
docker-compose logs arbitrage-ui
```

### 컨테이너 내부 접속
```bash
docker exec -it arbitrage-ui /bin/bash
```

### 리소스 사용량
```bash
docker stats arbitrage-ui
```

---

## 🐛 일반적인 오류 해결

### ImportError
```bash
# requirements.txt에 누락된 패키지 추가
# Dockerfile 재빌드
docker-compose build --no-cache
```

### Permission Denied
```bash
# 데이터 디렉토리 권한 수정
sudo chmod -R 755 data/
```

### Connection Refused
```bash
# 포트 확인
netstat -tuln | grep 8501

# 방화벽 확인
sudo ufw status
```

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-11-23

