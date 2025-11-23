# Streamlit 차익거래 분석 서비스 Docker 이미지
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사
COPY requirements.txt .

# Python 패키지 설치
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY app/ ./app/

# 필요한 스크립트 디렉토리 생성 및 복사
RUN mkdir -p ./scripts/subprojects/arbitrage
COPY scripts/subprojects/arbitrage/backtest_engine_optimized.py ./scripts/subprojects/arbitrage/
RUN test -f ./scripts/subprojects/arbitrage/__init__.py || touch ./scripts/subprojects/arbitrage/__init__.py

# 데이터베이스와 환경 변수는 볼륨으로 마운트되므로 복사하지 않음

# Streamlit 포트 노출
EXPOSE 8501

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Streamlit 실행 (외부 접속 허용)
CMD ["streamlit", "run", "app/main.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false", \
     "--browser.gatherUsageStats=false"]
