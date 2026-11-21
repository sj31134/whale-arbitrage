# Portfolio: RWA Transparency & Risk Monitoring Framework
**Project: Transparency Digital Twin (TDT)**

---

## 👨‍💻 개요
본 프로젝트는 급성장하는 **RWA(Real World Asset) 시장**의 고질적인 문제인 '정보 비대칭'을 해결하기 위해 개발되었습니다. 오프체인 자산 데이터를 온체인 리스크 지표와 결합하여, **투명성이 시장 리스크(유동성, 변동성)에 미치는 영향을 정량화**하고 이를 실시간으로 모니터링하는 솔루션을 구축했습니다.

---

## 🚀 Key Achievements

### 1. TDT(Transparency Digital Twin) 프레임워크 개발
- RWA 토큰의 투명성을 **Latency, Completeness, Consistency** 세 가지 차원으로 정량화하는 고유 지표 개발.
- 19개 주요 RWA/스테이블코인(ONDO, BUIDL, USDT 등)에 대한 투명성 데이터셋 구축.

### 2. 시장 리스크 상관관계 입증 (Quant Analysis)
- **High-TDT 그룹의 변동성이 Low-TDT 대비 20% 낮음**을 통계적으로 입증 (Mann-Whitney p < 0.001).
- 투명성 지표와 시장 유동성(Amihud Illiquidity) 간의 **강한 음의 상관관계(ρ = -0.58)** 발견.
- **RWA 전용 분석**에서 TDT가 변동성을 유의하게 감소시킴을 입증 (β = -0.0043, p < 0.001).

### 3. 실시간 리스크 대시보드 구축 (Full-stack)
- Streamlit과 Plotly를 활용한 **기관용 리스크 스코어카드** 인터페이스 구현.
- TDT 점수에 따른 Alert 시스템 및 시계열 리스크 트래킹 기능 포함.

---

## 🛠 Tech Stack
- **Languages**: Python
- **Data Engineering**: CoinGecko API, Pandas, NumPy, BeautifulSoup (Scraping)
- **Quant & ML**: Statsmodels (Panel Regression, Clustered SE), Scipy, XGBoost (Tail Risk Prediction)
- **Visualization**: Plotly, Streamlit
- **Methodology**: Petersen (2009) Clustered SE, Amihud (2002) Illiquidity, Benjamini-Hochberg FDR

---

## 📈 Business Value (For Exchanges/VCs)
1. **상장 심사(Due Diligence)**: TDT 점수를 활용하여 RWA 프로젝트의 정보 품질을 객관적으로 평가.
2. **담보 리스크 관리**: 투명성이 낮은 자산에 대해 더 높은 담보 할인율(Haircut) 적용 근거 마련.
3. **규제 대응**: MiCA 등 강화되는 가상자산 공시 규제에 선제적으로 대응할 수 있는 모니터링 프레임워크 제공.

---

## 🔗 Project Links
- **GitHub Repository**: [Whale Tracking / RWATransparency]
- **Live Dashboard**: [http://localhost:8501] (Local Demo)
- **Analytical Report**: `RESULTS_TABLES.md`, `PAPER_ABSTRACT.md`

---
*Developed by [Your Name]*
