# RWA Transparency Research Project

## 📋 프로젝트 개요

**Transparency Digital Twin (TDT)** 프레임워크를 활용한 RWA(Real World Assets) 토큰의 정보 품질과 리스크 프리미엄 관계 실증 연구.

### 연구 목표
1. RWA 토큰의 투명성을 정량화하는 TDT 지표 개발
2. TDT와 유동성/변동성 간 관계 실증 분석
3. 거래소/VC용 리스크 모니터링 프레임워크 제공

---

## 🏗️ TDT (Transparency Digital Twin) 프레임워크

### 3-Layer 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    Layer 3: Consistency                      │
│           온체인 ↔ 오프체인 데이터 정합성 검증                 │
├─────────────────────────────────────────────────────────────┤
│                    Layer 2: Completeness                     │
│              오프체인 공시 정보 완전성 평가                    │
├─────────────────────────────────────────────────────────────┤
│                    Layer 1: Latency                          │
│                 정보 업데이트 지연 측정                        │
└─────────────────────────────────────────────────────────────┘
```

### TDT 점수 계산
```
TDT = (Latency_Score + Completeness_Score + Consistency_Score) / 3
```

| 구성요소 | 측정 방법 | 범위 |
|----------|----------|------|
| Latency | 마지막 공시 업데이트 경과일 | 0-100 |
| Completeness | 8개 필수 필드 공개 비율 | 0-100 |
| Consistency | 온체인-오프체인 AUM 일치율 | 0-100 |

---

## 📊 주요 연구 결과

### 가설 검증 결과

| 가설 | 내용 | 클러스터 SE | 비모수 방법 | 종합 결론 |
|------|------|------------|-----------|----------|
| **H1** | TDT ↑ → Illiquidity ↓ | ❌ p=0.935 | ✅ Spearman p=0.011 | ⚠️ 방법론 의존 |
| **H2** | TDT ↑ → Volatility ↓ | ❌ p=0.220 | ✅ Mann-Whitney p<0.001 | ⚠️ 방법론 의존 |
| **H3** | TDT × Shock → 충격 완화 | ❌ p=0.341 | - | ❌ 비지지 |
| **H2-RWA** | RWA 전용 분석 | ✅ **p<0.001** | - | ✅ **강건하게 지지** |

### 핵심 발견

1. **방법론적 민감성**
   - 클러스터 SE(18 자산): 대부분 가설 비유의
   - 비모수 방법: H1, H2 유의하게 지지
   - 원인: 클러스터 수 부족 (18개 < 권장 50개)

2. **RWA 전용 분석에서 강건한 결과**
   - 순수 RWA 토큰(ONDO, BUIDL, USDY, PYUSD)만 분석
   - TDT ↑ → Volatility ↓ (β=-0.0043, p<0.001)

3. **그룹 비교 (Mann-Whitney)**
   - High-TDT 평균 변동성: 0.77%
   - Low-TDT 평균 변동성: 0.96%
   - **High-TDT 그룹이 20% 낮음** (p<0.001)

4. **유동성과 강한 음의 상관**
   - Spearman ρ = -0.58 (p = 0.011)
   - TDT가 높을수록 Amihud Illiquidity가 낮음

---

## 📁 프로젝트 구조

```
RWATransparency/
├── dashboard/
│   └── app.py                    # Streamlit 대시보드
├── data/
│   ├── raw/
│   │   ├── rwa_list.csv          # RWA 토큰 목록
│   │   ├── historical_prices.csv # CoinGecko 가격 시계열
│   │   └── offchain_disclosure.csv # 공시 정보
│   └── processed/
│       ├── tdt_scores.csv        # TDT 점수
│       ├── final_panel_data.csv  # 최종 패널 데이터
│       └── robust_regression_results.csv
├── scripts/
│   ├── layer1/                   # 온체인 데이터 수집
│   ├── layer2/                   # 오프체인 공시 수집
│   ├── layer3/                   # TDT 계산 및 통합
│   └── analysis/                 # 회귀/ML 분석
├── ACADEMIC_REVIEW.md            # 학술 비평
├── ALTERNATIVE_ANALYSIS.md       # 대안적 분석 결과
├── LITERATURE_ROBUSTNESS.md      # 선행연구 및 강건성
└── readme.md                     # 이 파일
```

---

## 🚀 실행 방법

### 1. 환경 설정
```bash
pip install -r requirements.txt
```

### 2. 데이터 수집
```bash
cd scripts/layer1
python collect_historical_data.py  # CoinGecko 가격 수집 (~5분)

cd ../layer2
python collect_disclosure_data.py  # 공시 정보 수집

cd ../layer3
python merge_real_data.py         # 데이터 통합
```

### 3. 분석 실행
```bash
cd scripts/analysis
python run_robust_regression.py    # 클러스터 SE 회귀
python run_alternative_analysis.py # 대안적 분석
```

### 4. 대시보드 실행
```bash
cd dashboard
streamlit run app.py
```

---

## 📚 인용 문헌

1. **Amihud, Y. (2002)**. Illiquidity and stock returns. *Journal of Financial Markets*.
2. **Petersen, M. A. (2009)**. Estimating standard errors in finance panel data sets. *Review of Financial Studies*.
3. **Botosan, C. A. (1997)**. Disclosure level and the cost of equity capital. *The Accounting Review*.
4. **Healy, P. M., & Palepu, K. G. (2001)**. Information asymmetry, corporate disclosure, and the capital markets. *Journal of Accounting and Economics*.

---

## 📝 한계 및 향후 연구

1. **표본 제한**: 19개 토큰, 6개월 데이터
2. **시간 불변 TDT**: 동적 TDT 측정 필요
3. **인과관계**: 도구변수(IV) 분석으로 강화 필요

---

## 📞 Contact

*석사 연구 프로젝트 - RWA Transparency Framework*
