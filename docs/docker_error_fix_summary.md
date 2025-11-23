# Docker 배포 에러 수정 요약

> **작성일**: 2025-11-23  
> **상태**: ✅ 수정 완료

---

## 🔍 발견된 에러

### 1. ModuleNotFoundError: No module named 'pages'

**에러 내용**:
```
ModuleNotFoundError: No module named 'pages'
```

**원인**:
- `app/main.py`에서 `from pages import cost_calculator_page`를 사용했지만, Docker 컨테이너 내부에서는 모듈 경로가 달라짐
- `sys.path`에 `ROOT`를 추가했지만, 상대 경로 import가 작동하지 않음

**해결 방법**:
- `from pages import ...` → `from app.pages import ...`로 변경
- 절대 경로 import 사용

**수정 파일**:
- `app/main.py`: import 문 수정

---

### 2. Dockerfile 빌드 에러: 파일을 찾을 수 없음

**에러 내용**:
```
failed to solve: failed to compute cache key: failed to calculate checksum of ref ... "/scripts/subprojects/arbitrage/backtest_engine_optimized.py": not found
```

**원인**:
- `.dockerignore`에서 `scripts/subprojects/arbitrage/backtest_*.py` 패턴이 파일을 제외함
- Docker 빌드 시 필요한 파일이 복사되지 않음

**해결 방법**:
- `.dockerignore`에서 `backtest_engine_optimized.py` 제외 규칙 제거
- 주석으로 명시: `# backtest_engine_optimized.py는 필요하므로 제외하지 않음`

**수정 파일**:
- `.dockerignore`: backtest_*.py 제외 규칙 수정

---

### 3. 경로 문제 (Docker 컨테이너 내부)

**원인**:
- 로컬 환경과 Docker 컨테이너 내부의 경로 구조가 다름
- `Path(__file__).resolve().parents[X]`가 컨테이너 내부에서 예상과 다른 경로를 반환

**해결 방법**:
- Docker 컨테이너 내부에서는 `/app`이 루트임을 확인
- `os.path.exists('/app')`로 컨테이너 내부인지 확인 후 경로 설정

**수정 파일**:
- `app/main.py`: ROOT 경로 설정 로직 추가
- `app/pages/cost_calculator_page.py`: ROOT 경로 설정 로직 추가
- `app/pages/strategy_recommender_page.py`: ROOT 경로 설정 로직 추가
- `app/utils/data_loader.py`: ROOT 경로 설정 로직 추가
- `app/utils/calculator.py`: ROOT 경로 설정 로직 추가
- `app/utils/recommender.py`: ROOT 경로 설정 로직 추가
- `scripts/subprojects/arbitrage/backtest_engine_optimized.py`: ROOT 경로 설정 로직 추가

---

## ✅ 수정 완료

모든 에러가 수정되었고, Docker 컨테이너가 정상적으로 실행되고 있습니다.

### 확인 사항
- ✅ Docker 이미지 빌드 성공
- ✅ 컨테이너 실행 성공
- ✅ Streamlit 서버 시작 성공
- ✅ Import 에러 해결
- ✅ 헬스체크 통과

### 접속 정보
- 로컬: http://localhost:8501
- 외부: http://[서버IP]:8501

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-11-23

