# Project 2 UI/UX 서비스 상세 개발 계획

> **작성일**: 2025-11-23  
> **목적**: 차익거래 비용 계산 및 최적 전략 추천 웹 서비스 개발

---

## 1. 서비스 개요

### 1.1 목적
사용자가 직관적으로 차익거래 기회를 분석하고 최적 전략을 확인할 수 있는 웹 기반 서비스

### 1.2 핵심 기능

#### 기능 1: 차익거래 비용 계산기
**목적**: 특정 기간, 코인, 거래소 조합에 대한 차익거래 비용 및 수익률 예측

**입력**:
- From/To 기간 (DatePicker)
- 코인 선택 (Dropdown: BTC, ETH)
- 거래소 쌍 선택 (MultiSelect: 업비트-바이낸스, 업비트-비트겟, 바이낸스-비트겟)
- 초기 자본 (Number Input, 기본값: 100,000,000 KRW)
- 수수료율 (Number Input, 기본값: 0.05%)
- 슬리피지 (Number Input, 기본값: 0.02%)
- 진입 조건 Z-Score (Number Input, 기본값: 2.5)
- 청산 조건 Z-Score (Number Input, 기본값: 0.5)
- 손절매 (Number Input, 기본값: -3%)
- 최대 보유 기간 (Number Input, 기본값: 30일)

**출력**:
- 주요 지표 (카드 형태)
  - 총 거래 횟수
  - 최종 수익률
  - 총 수익금
  - 승률
  - MDD
  - Sharpe Ratio
  - 연율화 수익률
- 수익률 곡선 차트 (Plotly Line Chart)
- 일별 자본 곡선 차트 (Plotly Line Chart)
- 거래 내역 테이블 (Sortable, Filterable)
- 거래소 쌍별 통계 테이블
- 청산 사유별 통계

#### 기능 2: 최적 전략 추천 (데이트레이딩)
**목적**: 특정 날짜에 가장 수익률이 높은 차익거래 방법 추천

**입력**:
- 날짜 선택 (DatePicker)
- 코인 선택 (Dropdown: BTC, ETH)
- 초기 자본 (Number Input, 기본값: 100,000,000 KRW)

**출력**:
- 추천 거래소 쌍 (카드)
- 전략 방향 (Short/Long Premium)
- 예상 수익률 (큰 숫자로 강조)
- 예상 보유 기간
- 현재 프리미엄 및 Z-Score
- 실행 방법 (단계별 가이드)
- 리스크 정보
- 대안 전략 (2순위, 3순위)

---

## 2. 기술 스택

### 2.1 선택: Streamlit
**이유**:
- Python 기반 (기존 코드 재사용 용이)
- 빠른 프로토타이핑
- 내장 차트 라이브러리 (Plotly 지원)
- 반응형 UI 자동 처리
- 배포 간편

### 2.2 필요한 패키지
```
streamlit>=1.28.0
plotly>=5.17.0
pandas>=2.0.0
numpy>=1.24.0
```

---

## 3. 파일 구조

```
whale_tracking/
├── app/                                    # UI 애플리케이션
│   ├── __init__.py
│   ├── main.py                            # Streamlit 메인 앱
│   ├── pages/                             # 페이지별 모듈
│   │   ├── __init__.py
│   │   ├── 1_📊_차익거래_비용_계산기.py    # 기능 1
│   │   └── 2_🎯_최적_전략_추천.py          # 기능 2
│   ├── utils/                             # 유틸리티
│   │   ├── __init__.py
│   │   ├── data_loader.py                 # 데이터 로드
│   │   ├── calculator.py                  # 비용 계산 로직
│   │   ├── recommender.py                 # 전략 추천 로직
│   │   └── visualizer.py                  # 차트 생성
│   └── config.py                          # 설정
├── scripts/
│   └── subprojects/
│       └── arbitrage/
│           └── backtest_engine_optimized.py  # 기존 엔진 활용
└── data/
    └── project.db                         # SQLite 데이터베이스
```

---

## 4. 상세 구현 계획

### 4.1 백엔드 로직

#### 4.1.1 데이터 로더 (`app/utils/data_loader.py`)
```python
class DataLoader:
    def load_exchange_data(self, start_date, end_date, coin='BTC'):
        """거래소 데이터 로드"""
        
    def get_available_dates(self, coin='BTC'):
        """사용 가능한 날짜 범위 반환"""
        
    def get_exchange_pairs(self):
        """사용 가능한 거래소 쌍 반환"""
```

#### 4.1.2 비용 계산기 (`app/utils/calculator.py`)
```python
class CostCalculator:
    def calculate_arbitrage_cost(
        self, from_date, to_date, coin, exchanges,
        initial_capital, fee_rate, slippage,
        entry_z, exit_z, stop_loss, max_holding_days
    ):
        """차익거래 비용 계산"""
        # OptimizedArbitrageBacktest 활용
        # 결과 반환: metrics, trades_df, daily_capital_df
```

#### 4.1.3 전략 추천기 (`app/utils/recommender.py`)
```python
class StrategyRecommender:
    def recommend_best_strategy(self, target_date, coin, initial_capital):
        """최적 전략 추천"""
        # 1. target_date 기준 전후 30일 데이터 로드
        # 2. 각 거래소 쌍별 프리미엄 계산
        # 3. Z-Score 계산
        # 4. target_date의 최적 거래소 쌍 선택
        # 5. 시뮬레이션 실행
        # 6. 결과 반환
```

#### 4.1.4 시각화 (`app/utils/visualizer.py`)
```python
class Visualizer:
    def plot_return_curve(self, daily_capital_df):
        """수익률 곡선 차트"""
        
    def plot_drawdown(self, daily_capital_df):
        """낙폭 차트"""
        
    def plot_premium_timeline(self, df, pair):
        """프리미엄 타임라인 차트"""
```

### 4.2 프론트엔드 UI

#### 4.2.1 메인 페이지 (`app/main.py`)
```python
import streamlit as st

st.set_page_config(
    page_title="차익거래 분석 서비스",
    page_icon="💰",
    layout="wide"
)

st.title("💰 차익거래 분석 서비스")
st.sidebar.title("메뉴")
page = st.sidebar.selectbox("페이지 선택", [
    "차익거래 비용 계산기",
    "최적 전략 추천"
])
```

#### 4.2.2 기능 1 페이지 (`app/pages/1_📊_차익거래_비용_계산기.py`)
```python
# 입력 섹션
with st.sidebar:
    st.header("📋 입력 파라미터")
    from_date = st.date_input("시작 날짜", value=datetime(2024, 1, 1))
    to_date = st.date_input("종료 날짜", value=datetime.now().date())
    coin = st.selectbox("코인", ["BTC", "ETH"])
    exchanges = st.multiselect(
        "거래소 쌍",
        ["업비트-바이낸스", "업비트-비트겟", "바이낸스-비트겟"],
        default=["바이낸스-비트겟", "업비트-비트겟"]
    )
    # ... 기타 파라미터

# 계산 버튼
if st.button("계산하기", type="primary"):
    # 계산 실행
    result = calculator.calculate_arbitrage_cost(...)
    
    # 결과 표시
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("최종 수익률", f"{result['final_return']*100:.2f}%")
    # ...
```

#### 4.2.3 기능 2 페이지 (`app/pages/2_🎯_최적_전략_추천.py`)
```python
# 입력 섹션
target_date = st.date_input("날짜 선택", value=datetime.now().date())
coin = st.selectbox("코인", ["BTC", "ETH"])

# 추천 버튼
if st.button("전략 추천", type="primary"):
    recommendation = recommender.recommend_best_strategy(...)
    
    # 추천 결과 표시
    st.success(f"🎯 추천 거래소 쌍: {recommendation['pair']}")
    st.metric("예상 수익률", f"{recommendation['expected_return']*100:.2f}%")
    # ...
```

---

## 5. 시뮬레이션 시나리오

### 시나리오 1: 정상 케이스
- 입력: 유효한 날짜 범위, 존재하는 코인
- 예상: 정상 계산 및 결과 반환

### 시나리오 2: 데이터 부족
- 입력: 데이터가 없는 날짜 범위
- 예상: 에러 메시지 및 사용 가능한 날짜 범위 안내

### 시나리오 3: 잘못된 입력
- 입력: from_date > to_date
- 예상: 입력 검증 및 에러 메시지

### 시나리오 4: 경계 케이스
- 입력: 매우 짧은 기간 (1일)
- 예상: 최소 기간 검증 (30일 이상)

### 시나리오 5: 거래 없음
- 입력: 조건이 너무 엄격하여 거래가 발생하지 않음
- 예상: 조건 완화 제안

---

## 6. 에러 처리

### 6.1 데이터 관련
- 데이터 부족: 사용 가능한 날짜 범위 안내
- NULL 데이터: 전처리 및 경고 메시지

### 6.2 계산 관련
- 거래 없음: 조건 완화 제안
- 계산 오류: 로그 기록 및 에러 메시지

### 6.3 UI 관련
- 입력 검증: 실시간 피드백
- 로딩 시간: 진행 표시 (spinner)

---

## 7. 구현 단계

### 단계 1: 백엔드 로직 구현 및 테스트
- [ ] DataLoader 구현
- [ ] CostCalculator 구현
- [ ] StrategyRecommender 구현
- [ ] Visualizer 구현
- [ ] 유닛 테스트

### 단계 2: Streamlit UI 기본 구조
- [ ] 메인 페이지
- [ ] 사이드바 네비게이션
- [ ] 기본 레이아웃

### 단계 3: 기능 1 UI 구현
- [ ] 입력 폼
- [ ] 계산 로직 연결
- [ ] 결과 표시
- [ ] 차트 구현

### 단계 4: 기능 2 UI 구현
- [ ] 날짜 선택 UI
- [ ] 추천 로직 연결
- [ ] 결과 표시

### 단계 5: 통합 테스트
- [ ] 전체 플로우 테스트
- [ ] 에러 처리 테스트
- [ ] 성능 테스트

### 단계 6: 시뮬레이션 및 오류 보완
- [ ] 다양한 시나리오 테스트
- [ ] 엣지 케이스 처리
- [ ] UI/UX 개선

---

## 8. 예상 소요 시간

| 단계 | 예상 시간 |
|------|----------|
| 백엔드 로직 구현 | 4-6시간 |
| Streamlit UI 기본 구조 | 2-3시간 |
| 기능 1 UI 구현 | 4-6시간 |
| 기능 2 UI 구현 | 3-4시간 |
| 통합 테스트 | 2-3시간 |
| 시뮬레이션 및 오류 보완 | 3-4시간 |
| **총계** | **18-26시간** |

---

## 9. 다음 단계

1. Streamlit 설치 및 기본 구조 생성
2. 백엔드 로직 구현
3. UI 구현
4. 테스트 및 시뮬레이션
5. 오류 보완

