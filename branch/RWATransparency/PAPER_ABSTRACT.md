# RWA Transparency Research Paper

## 논문 정보

**제목 (영문)**: Transparency Digital Twin: Measuring Information Quality and Market Risk in Real World Asset Tokens

**제목 (한글)**: 투명성 디지털 트윈: 실물자산 토큰의 정보 품질과 시장 위험 측정

**저자**: [Author Name]  
**소속**: [Affiliation]  
**작성일**: 2026년 2월

---

## Abstract (영문 초록, 250 words)

**Background**: Real World Assets (RWA) tokenization bridges traditional finance and decentralized finance, yet the relationship between disclosure quality and market risk remains underexplored. Unlike traditional securities with established disclosure frameworks, RWA tokens face unique information asymmetry challenges.

**Objective**: This study introduces the Transparency Digital Twin (TDT), a novel framework for quantifying RWA token transparency across three dimensions: latency (update timeliness), completeness (disclosure coverage), and consistency (on-chain vs. off-chain alignment).

**Methods**: We collected 6 months of daily market data for 19 RWA/stablecoin tokens from CoinGecko and manually coded disclosure quality from issuer websites. Panel regression with clustered standard errors (Petersen, 2009) and nonparametric methods (Spearman, Mann-Whitney) were employed to test three hypotheses relating TDT to liquidity, volatility, and shock resilience.

**Results**: Clustered standard errors (18 asset clusters) rendered most results statistically insignificant due to cluster count limitations. However, nonparametric analyses revealed robust negative correlations: TDT and illiquidity (Spearman ρ=-0.58, p=0.011), and TDT and volatility (Mann-Whitney p<0.001, with high-TDT groups showing 20% lower volatility). Most notably, pure RWA token subsample analysis yielded significant results even with clustered SE (β=-0.0043, p<0.001).

**Conclusions**: Transparency is significantly associated with reduced market risk in RWA tokens, though results are method-dependent. The TDT framework offers a practical tool for exchanges and institutional investors to monitor RWA disclosure quality.

**Keywords**: Real World Assets, Tokenization, Information Asymmetry, Disclosure Quality, Liquidity, Volatility, DeFi

---

## 초록 (한글, 300자)

**배경**: 실물자산(RWA) 토큰화는 전통 금융과 탈중앙화 금융을 연결하지만, 공시 품질과 시장 위험 간 관계는 충분히 연구되지 않았다.

**목적**: 본 연구는 RWA 토큰의 투명성을 정량화하는 투명성 디지털 트윈(TDT) 프레임워크를 제안한다. TDT는 지연성(Latency), 완전성(Completeness), 일관성(Consistency) 세 차원으로 구성된다.

**방법**: 19개 RWA/스테이블코인 토큰의 6개월 일별 시장 데이터를 수집하고, 발행자 웹사이트에서 공시 품질을 수동 코딩하였다. Petersen(2009) 클러스터 표준오차와 비모수적 방법(Spearman, Mann-Whitney)을 적용하여 가설을 검증하였다.

**결과**: 클러스터 표준오차 적용 시 대부분 가설이 비유의하였으나(클러스터 수 18개 한계), 비모수적 분석에서는 유의한 음의 상관관계가 확인되었다(Spearman ρ=-0.58, p=0.011). 특히 순수 RWA 토큰 서브샘플에서는 클러스터 SE 적용 후에도 TDT가 변동성 감소와 유의하게 연관되었다(β=-0.0043, p<0.001).

**결론**: RWA 토큰에서 투명성은 시장 위험 감소와 유의하게 연관되며, TDT 프레임워크는 거래소 및 기관투자자의 실무적 모니터링 도구로 활용 가능하다.

**키워드**: 실물자산 토큰, 토큰화, 정보 비대칭, 공시 품질, 유동성, 변동성, DeFi

---

## Extended Abstract (확장 초록, 학회 발표용)

### 1. Introduction

The tokenization of Real World Assets (RWA) represents a paradigm shift in financial markets, enabling fractional ownership and enhanced liquidity for traditionally illiquid assets. As of 2026, the RWA market has grown to over $15 billion, attracting significant institutional interest from firms like BlackRock (BUIDL) and PayPal (PYUSD).

However, RWA tokens face a unique challenge: the information about underlying assets exists off-chain, creating potential information asymmetry between issuers and investors. Unlike traditional securities governed by SEC disclosure requirements, RWA tokens operate in a regulatory gray area where disclosure practices vary widely.

### 2. Theoretical Framework

Building on Healy & Palepu (2001) and Botosan (1997), we propose that higher disclosure quality reduces information asymmetry, leading to lower adverse selection costs and improved market quality. We operationalize this through the Transparency Digital Twin (TDT), a composite index measuring:

- **Latency** (0-100): How frequently is disclosure information updated?
- **Completeness** (0-100): What proportion of essential fields are disclosed?
- **Consistency** (0-100): Do on-chain values match off-chain claims?

### 3. Hypotheses

- **H1**: Higher TDT is associated with lower illiquidity (Amihud measure)
- **H2**: Higher TDT is associated with lower price volatility
- **H3**: Higher TDT mitigates negative returns during market shocks

### 4. Data and Methods

| Data Source | Description | Period |
|-------------|-------------|--------|
| CoinGecko API | Daily price, volume, market cap | 180 days |
| Issuer websites | Disclosure quality coding | Cross-sectional |
| Sample | 19 RWA/stablecoin tokens | Feb 2026 |

**Econometric Approach**:
- Panel OLS with clustered SE by asset (Petersen, 2009)
- Robustness: Spearman/Kendall correlation, Mann-Whitney U, Bootstrap CI

### 5. Key Findings

| Hypothesis | Clustered SE | Nonparametric | RWA-Only |
|------------|-------------|---------------|----------|
| H1 (Illiquidity) | p=0.935 | ρ=-0.58, p=0.011 ✅ | - |
| H2 (Volatility) | p=0.220 | Mann-Whitney p<0.001 ✅ | **p<0.001 ✅** |
| H3 (Shock) | p=0.341 | - | - |

**Critical insight**: With only 18 asset clusters, clustered SE may be overly conservative. Nonparametric methods, valid for small samples, consistently support H1 and H2.

### 6. Contributions

1. **Theoretical**: First comprehensive framework (TDT) for RWA transparency measurement
2. **Empirical**: Evidence that transparency correlates with reduced market risk
3. **Practical**: Monitoring tool for exchanges, VCs, and regulators
4. **Methodological**: Demonstration of cluster count challenges in crypto panel analysis

### 7. Limitations and Future Research

- Small sample (19 tokens, 18 clusters)
- Time-invariant TDT scores (cross-sectional)
- Correlation, not causation (no instrumental variables)

Future work should expand the sample as more RWA tokens enter the market and explore dynamic TDT measurement based on disclosure update events.

---

## 참고문헌 (Selected References)

1. Amihud, Y. (2002). Illiquidity and stock returns: cross-section and time-series effects. *Journal of Financial Markets*, 5(1), 31-56.

2. Botosan, C. A. (1997). Disclosure level and the cost of equity capital. *The Accounting Review*, 72(3), 323-349.

3. Cameron, A. C., & Miller, D. L. (2015). A practitioner's guide to cluster-robust inference. *Journal of Human Resources*, 50(2), 317-372.

4. Healy, P. M., & Palepu, K. G. (2001). Information asymmetry, corporate disclosure, and the capital markets. *Journal of Accounting and Economics*, 31(1-3), 405-440.

5. Petersen, M. A. (2009). Estimating standard errors in finance panel data sets: Comparing approaches. *Review of Financial Studies*, 22(1), 435-480.

---

## JEL Classification

- G14: Information and Market Efficiency
- G23: Non-bank Financial Institutions; Financial Instruments
- G32: Financing Policy; Financial Risk and Risk Management

---

*This document is prepared for academic submission.*
