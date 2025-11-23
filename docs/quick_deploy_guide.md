# 빠른 배포 가이드 (5분)

> 외부 접속 가능한 서비스 배포

---

## 🚀 3단계로 배포하기

### 1단계: 서버 준비
- 클라우드 서버 생성 (AWS EC2, GCP, Azure 등)
- SSH 접속 가능 확인
- 방화벽에서 포트 8501 열기

### 2단계: 자동 배포
```bash
./scripts/deploy_to_server.sh [서버IP] [사용자명]
```

### 3단계: 접속
브라우저에서: `http://[서버IP]:8501`

---

## 📋 배포 전 확인

- [ ] 서버 IP 주소 확인
- [ ] SSH 키 설정 완료
- [ ] 방화벽에서 포트 8501 열기
- [ ] 로컬에 `data/project.db` 파일 존재
- [ ] 로컬에 `config/.env` 파일 존재

---

## ⚙️ 배포 후 설정

### 환경 변수 설정
서버에 SSH 접속 후:
```bash
cd ~/whale_tracking
nano config/.env
```

필수 환경 변수:
- `ECOS_API_KEY`: 한국은행 환율 API 키

### 데이터베이스 복사
로컬에서:
```bash
scp data/project.db user@server:~/whale_tracking/data/
```

---

## 🔧 유용한 명령어

```bash
# 로그 확인
ssh user@server 'cd ~/whale_tracking && docker-compose -f docker-compose.prod.yml logs -f'

# 재시작
ssh user@server 'cd ~/whale_tracking && docker-compose -f docker-compose.prod.yml restart'

# 중지
ssh user@server 'cd ~/whale_tracking && docker-compose -f docker-compose.prod.yml down'
```

---

**자세한 내용**: [deploy_external_access_guide.md](deploy_external_access_guide.md)

