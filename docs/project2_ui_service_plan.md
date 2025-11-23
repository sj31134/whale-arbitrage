# Project 2 UI/UX 서비스 개발 계획

> **작성일**: 2025-11-23  
> **목적**: 차익거래 비용 계산 및 최적 전략 추천 UI 서비스 개발

---

## 1. 서비스 개요

### 1.1 목적
사용자가 직관적으로 차익거래 기회를 분석하고 최적 전략을 확인할 수 있는 웹 기반 서비스

### 1.2 핵심 기능

#### 기능 1: 차익거래 비용 계산기
- **입력**: 
  - From/To 기간 선택
  - 코인 선택 (BTC, ETH 등)
  - 거래소 선택 (업비트, 바이낸스, 비트겟)
- **출력**: 
  - 예상 차익거래 비용
  - 예상 수익률
  - 거래 횟수
  - 리스크 지표

#### 기능 2: 최적 전략 추천 (데이트레이딩)
- **입력**: 
  - 특정 날짜 선택
- **출력**: 
  - 그날 기준 최고 수익률 차익거래 방법
  - 추천 거래소 쌍
  - 예상 수익률
  - 실행 방법

---

## 2. 기술 스택

### 2.1 백엔드
- **Python 3.9+**
- **Flask** 또는 **Streamlit** (빠른 프로토타이핑)
- **SQLite** (기존 `data/project.db` 활용)
- **Pandas, NumPy** (데이터 처리)

### 2.2 프론트엔드
- **Streamlit** (선택 시): Python 기반, 빠른 개발
- **Flask + HTML/CSS/JavaScript** (선택 시): 더 많은 커스터마이징
- **차트 라이브러리**: Plotly 또는 Chart.js

### 2.3 데이터베이스
- **SQLite** (`data/project.db`)
- 기존 테이블 활용:
  - `upbit_daily`
  - `binance_spot_daily`
  - `bitget_spot_daily`
  - `exchange_rate`

---

## 3. 상세 설계

### 3.1 기능 1: 차익거래 비용 계산기

#### 3.1.1 입력 파라미터
```
- 시작 날짜 (from_date): DatePicker
- 종료 날짜 (to_date): DatePicker
- 코인 선택: Dropdown (BTC, ETH)
- 거래소 쌍 선택: MultiSelect (업비트-바이낸스, 업비트-비트겟, 바이낸스-비트겟)
- 초기 자본: Number Input (기본값: 100,000,000 KRW)
- 수수료율: Number Input (기본값: 0.05%)
- 슬리피지: Number Input (기본값: 0.02%)
- 진입 조건 (Z-Score): Number Input (기본값: 2.5)
- 청산 조건 (Z-Score): Number Input (기본값: 0.5)
```

#### 3.1.2 계산 로직
```python
def calculate_arbitrage_cost(from_date, to_date, coin, exchanges, initial_capital, fee_rate, slippage, entry_z, exit_z):
    """
    1. 데이터 로드 (from_date ~ to_date)
    2. 지표 계산 (프리미엄, Z-Score)
    3. 시그널 생성
    4. 백테스트 실행
    5. 결과 반환:
       - 총 거래 횟수
       - 예상 수익률
       - 예상 수익금
       - 승률
       - MDD
       - Sharpe Ratio
       - 거래 내역
    """
```

#### 3.1.3 출력 UI
```
┌─────────────────────────────────────────┐
│ 차익거래 비용 계산 결과                  │
├─────────────────────────────────────────┤
│ 기간: 2024-01-01 ~ 2024-12-31          │
│ 코인: BTC                               │
│ 거래소 쌍: 업비트-바이낸스, 바이낸스-비트겟 │
│                                         │
│ 📊 주요 지표                            │
│ - 총 거래 횟수: 13회                    │
│ - 예상 수익률: 8.98%                    │
│ - 예상 수익금: 8,977,578 KRW            │
│ - 승률: 76.9%                           │
│ - MDD: -6.53%                           │
│ - Sharpe Ratio: 0.74                    │
│                                         │
│ 📈 수익률 곡선 (차트)                    │
│                                         │
│ 📋 거래 내역 (테이블)                    │
└─────────────────────────────────────────┘
```

### 3.2 기능 2: 최적 전략 추천 (데이트레이딩)

#### 3.2.1 입력 파라미터
```
- 날짜 선택: DatePicker
- 코인 선택: Dropdown (BTC, ETH)
- 초기 자본: Number Input (기본값: 100,000,000 KRW)
```

#### 3.2.2 계산 로직
```python
def recommend_best_strategy(target_date, coin, initial_capital):
    """
    1. target_date 기준 전후 30일 데이터 로드
    2. 각 거래소 쌍별 프리미엄 계산
    3. Z-Score 계산
    4. target_date의 최적 거래소 쌍 선택
    5. 시뮬레이션:
       - 진입: target_date
       - 청산: Z-Score 회귀 시점 또는 다음날
    6. 결과 반환:
       - 추천 거래소 쌍
       - 진입 방향 (Short/Long Premium)
       - 예상 수익률
       - 예상 보유 기간
       - 실행 방법
    """
```

#### 3.2.3 출력 UI
```
┌─────────────────────────────────────────┐
│ 최적 전략 추천 (2024-06-15)             │
├─────────────────────────────────────────┤
│ 🎯 추천 거래소 쌍: 바이낸스-비트겟        │
│ 📊 전략: Short Premium                  │
│    (바이낸스 매도, 비트겟 매수)          │
│                                         │
│ 💰 예상 수익률: 3.84%                   │
│ ⏱️ 예상 보유 기간: 3일                  │
│ 📈 현재 프리미엄: 2.5%                  │
│ 📉 Z-Score: 2.8                        │
│                                         │
│ 📋 실행 방법                            │
│ 1. 바이낸스에서 BTC 매도                │
│ 2. 비트겟에서 BTC 매수                  │
│ 3. 프리미엄 회귀 대기 (Z-Score < 0.5)   │
│ 4. 역거래 실행                          │
│                                         │
│ ⚠️ 리스크                               │
│ - 최대 손실: -3% (손절매)               │
│ - 최대 보유 기간: 30일                  │
└─────────────────────────────────────────┘
```

---

## 4. 구현 단계

### 단계 1: 백엔드 API 개발
- [ ] 차익거래 비용 계산 함수
- [ ] 최적 전략 추천 함수
- [ ] 데이터 로드 함수
- [ ] 유닛 테스트

### 단계 2: UI 프레임워크 선택 및 설정
- [ ] Streamlit 또는 Flask 선택
- [ ] 프로젝트 구조 설정
- [ ] 기본 레이아웃 구성

### 단계 3: 기능 1 UI 구현
- [ ] 입력 폼 구현
- [ ] 계산 로직 연결
- [ ] 결과 표시 UI
- [ ] 차트 구현

### 단계 4: 기능 2 UI 구현
- [ ] 날짜 선택 UI
- [ ] 추천 로직 연결
- [ ] 결과 표시 UI

### 단계 5: 통합 및 테스트
- [ ] 전체 플로우 테스트
- [ ] 에러 처리
- [ ] 성능 최적화

### 단계 6: 시뮬레이션 및 오류 보완
- [ ] 다양한 시나리오 테스트
- [ ] 엣지 케이스 처리
- [ ] 사용자 피드백 반영

---

## 5. 파일 구조

```
whale_tracking/
├── app/                          # UI 애플리케이션
│   ├── __init__.py
│   ├── main.py                   # 메인 애플리케이션
│   ├── pages/                    # 페이지별 모듈
│   │   ├── cost_calculator.py    # 기능 1
│   │   └── strategy_recommender.py # 기능 2
│   ├── utils/                    # 유틸리티
│   │   ├── data_loader.py        # 데이터 로드
│   │   ├── calculator.py         # 계산 로직
│   │   └── visualizer.py         # 차트 생성
│   └── templates/                # HTML 템플릿 (Flask 사용 시)
│       ├── base.html
│       ├── calculator.html
│       └── recommender.html
├── scripts/
│   └── subprojects/
│       └── arbitrage/
│           └── backtest_engine_optimized.py  # 기존 엔진 활용
└── data/
    └── project.db                # SQLite 데이터베이스
```

---

## 6. 상세 구현 계획

### 6.1 백엔드 API 설계

#### API 1: 차익거래 비용 계산
```python
POST /api/calculate_arbitrage_cost
Request Body:
{
    "from_date": "2024-01-01",
    "to_date": "2024-12-31",
    "coin": "BTC",
    "exchanges": ["upbit_binance", "binance_bitget"],
    "initial_capital": 100000000,
    "fee_rate": 0.0005,
    "slippage": 0.0002,
    "entry_z": 2.5,
    "exit_z": 0.5
}

Response:
{
    "success": true,
    "data": {
        "total_trades": 13,
        "final_return": 0.0898,
        "total_profit": 8977578,
        "win_rate": 0.769,
        "mdd": -0.0653,
        "sharpe_ratio": 0.74,
        "trades": [...],
        "daily_capital": [...]
    }
}
```

#### API 2: 최적 전략 추천
```python
POST /api/recommend_strategy
Request Body:
{
    "target_date": "2024-06-15",
    "coin": "BTC",
    "initial_capital": 100000000
}

Response:
{
    "success": true,
    "data": {
        "recommended_pair": "binance_bitget",
        "direction": "short_premium",
        "expected_return": 0.0384,
        "expected_holding_days": 3,
        "current_premium": 0.025,
        "z_score": 2.8,
        "execution_steps": [...],
        "risks": {...}
    }
}
```

---

## 7. 시뮬레이션 시나리오

### 시나리오 1: 정상 케이스
- 입력: 유효한 날짜 범위, 존재하는 코인
- 예상: 정상 계산 및 결과 반환

### 시나리오 2: 데이터 부족
- 입력: 데이터가 없는 날짜 범위
- 예상: 에러 메시지 및 대안 제시

### 시나리오 3: 잘못된 입력
- 입력: from_date > to_date
- 예상: 입력 검증 및 에러 메시지

### 시나리오 4: 경계 케이스
- 입력: 매우 짧은 기간 (1일)
- 예상: 최소 기간 검증

---

## 8. 에러 처리

### 8.1 데이터 관련 에러
- 데이터 부족: 사용 가능한 날짜 범위 안내
- NULL 데이터: 전처리 및 경고 메시지

### 8.2 계산 관련 에러
- 거래 없음: 조건 완화 제안
- 수익률 계산 오류: 로그 기록 및 에러 메시지

### 8.3 UI 관련 에러
- 입력 검증: 실시간 피드백
- 로딩 시간: 진행 표시

---

## 9. 성능 최적화

### 9.1 데이터 로딩
- 캐싱: 자주 사용하는 데이터 캐시
- 인덱싱: SQLite 인덱스 최적화

### 9.2 계산 최적화
- 병렬 처리: 여러 거래소 쌍 동시 계산
- 결과 캐싱: 동일 입력 재계산 방지

---

## 10. 테스트 계획

### 10.1 유닛 테스트
- 데이터 로드 함수
- 계산 함수
- API 엔드포인트

### 10.2 통합 테스트
- 전체 플로우
- UI 상호작용

### 10.3 시뮬레이션 테스트
- 다양한 입력 조합
- 엣지 케이스
- 성능 테스트

---

## 11. 배포 계획

### 11.1 로컬 실행
- Streamlit: `streamlit run app/main.py`
- Flask: `python app/main.py`

### 11.2 프로덕션 배포 (선택)
- Docker 컨테이너화
- 클라우드 배포 (AWS, GCP 등)

---

## 12. 다음 단계

1. 기술 스택 최종 결정
2. 프로토타입 개발
3. 시뮬레이션 및 테스트
4. 오류 보완
5. 최종 배포

