# 자동매매 봇 아키텍처

## 시스템 구조

```
trading_bot/
├── config/          # 설정 관리
├── core/            # 봇 엔진 코어
├── collectors/      # 데이터 수집
├── strategies/      # 매매 전략
├── execution/       # 주문 실행
├── utils/           # 유틸리티
└── ui/              # Streamlit UI
```

## 모듈별 역할

### config/
- **settings_manager.py**: 설정 파일 저장/로드
- **default_config.json**: 기본 설정 템플릿

### core/
- **bot_engine.py**: 메인 봇 엔진 (루프 실행)
- **position_manager.py**: 포지션 추적 및 관리
- **signal_generator.py**: 시그널 생성 (향후 확장)

### collectors/
- **data_collector.py**: 기존 프로젝트 모듈 래핑 (읽기 전용)
- **market_data.py**: 업비트 API를 통한 시장 데이터 수집

### strategies/
- **data_driven_strategy.py**: 데이터 기반 시그널 생성
- **premium_filter.py**: 김치 프리미엄 필터

### execution/
- **order_executor.py**: 업비트 API 주문 실행
- **balance_manager.py**: 잔고 관리

### utils/
- **logger.py**: 로깅 유틸리티
- **notifier.py**: 텔레그램 알림
- **validators.py**: 입력 검증

### ui/
- **trading_page.py**: Streamlit UI 페이지

## 데이터 흐름

```
1. 봇 엔진 시작
   ↓
2. 메인 루프 실행 (체크 간격마다)
   ↓
3. 데이터 수집
   - 리스크 예측 조회 (RiskPredictor)
   - 특성 값 조회 (FeatureEngineer)
   - 현재가 조회 (DataLoader)
   - 김치 프리미엄 조회 (DataLoader)
   ↓
4. 시그널 생성
   - 데이터 기반 시그널 점수 계산
   - 프리미엄 필터 확인
   ↓
5. 주문 실행 (시그널 발생 시)
   - 포지션 크기 계산
   - 주문 실행 (OrderExecutor)
   - 포지션 기록 (PositionManager)
   ↓
6. 알림 전송 (텔레그램)
   ↓
7. 모니터링 (UI)
```

## 기존 시스템과의 통합

### 읽기 전용 접근
- `data/project.db`: SQLite 읽기 전용
- `app/utils/DataLoader`: 래핑하여 사용
- `app/utils/RiskPredictor`: 래핑하여 사용
- `scripts/subprojects/risk_ai/FeatureEngineer`: 래핑하여 사용

### 독립적인 저장소
- `trading_bot/config/user_settings.json`: 사용자 설정
- `trading_bot/data/positions.json`: 포지션 데이터
- `logs/trading_bot.log`: 로그 파일

## 보안 고려사항

1. **API 키 관리**
   - 설정 파일은 gitignore에 추가
   - 파일 권한: 600 (소유자만 읽기/쓰기)

2. **에러 처리**
   - 모든 API 호출에 재시도 로직
   - 에러 발생 시 기존 서비스에 영향 없도록 격리

3. **로깅**
   - 민감한 정보는 로그에 기록하지 않음
   - 별도 로그 파일 사용

## 확장 가능성

### 향후 추가 가능한 기능
1. 백테스트 모듈
2. 여러 코인 동시 거래
3. 고급 주문 타입 (지정가, 조건부 주문)
4. 포트폴리오 관리
5. 실시간 차트 표시

