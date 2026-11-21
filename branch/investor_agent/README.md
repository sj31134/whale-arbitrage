# 🏛️ Multi-Asset Investor Subagent (`branch/investor_agent`)

An institutional-grade **Multi-Asset Research, Valuation, and Capital Allocation Subagent** built as a dedicated branch project within the `whale_tracking` repository.

The agent screens, values, models, and executes investment decisions across **Real Estate, Equities & Infrastructure, Commodities & Hard Assets, and Crypto/RWA** to maximize long-term compounding returns while enforcing strict asymmetric risk-reward and margin of safety.

---

## 🎯 Core Investment Philosophy

> **"An asset with predictable and expandable future cash flows, asymmetric risk-reward profile (limited downside vs. open upside), and a rigorous margin of safety purchased during market mispricing or structural transitions."**

### The 4 Core Evaluation Pillars:
1. **Sustainable & Expandable Cash Flow & Economic Moat:** High ROIC > WACC, pricing power, and defensive moat.
2. **Asymmetric Risk-Reward & Margin of Safety:** Min 1:3 payoff ratio (\(\text{Bull Upside} / |\text{Bear Downside}| \ge 3.0\)) and purchase at a discount.
3. **Structural Megatrends & Anti-fragility:** AI compute bottlenecks, power grid expansion, hard monetary defense, and crisis resilience.
4. **Capital Allocation & Governance:** Aligned leadership returning surplus via buybacks/burns/dividends.

### The 5 Universal Investment Skills:
1. **Asset Decomposition (알맹이 vs 껍데기 분리):** Separating decaying wrappers (\(\delta \cdot t \to 0\)) from compounding core assets (\(e^{g \cdot t}\)).
2. **Absolute Supply Inelasticity (물리적 공급 비탄력성):** Exploiting natural, physical, or structural bottlenecks where supply cannot scale even if price jumps 10x (\(E_s \approx 0\)).
3. **Price-Inelastic Buyer Cohort (가격 둔감형 최상위 수요):** Backed by cash-rich UHNWI, central banks, or mission-critical enterprise budgets.
4. **Walled Garden & Privacy Moat (폐쇄형 네트워크 해자):** Closed, exclusive ecosystem providing proprietary lock-in.
5. **Spillover Arbitrage (인프라 무임승차):** Free-riding on massive external capital expenditure without taking on debt or development risk.

---

## 📁 Repository & Folder Structure

```
branch/investor_agent/
├── README.md                           # Comprehensive documentation & framework guide
├── requirements.txt                    # Python dependencies
├── main.py                             # CLI orchestrator & pipeline runner
├── config/
│   ├── settings.yaml                   # Global risk thresholds, hurdle rates, and limits
│   ├── asset_classes.yaml              # Multi-asset universe definitions & benchmarks
│   └── scoring_weights.yaml            # Weights for 5 skills and 4 criteria
├── data/
│   ├── raw/                            # Ingested raw research/market data
│   ├── processed/                      # Standardized metrics
│   └── memos/                          # Generated institutional investment committee memos
├── skills/
│   └── investor-principles/
│       └── SKILL.md                    # Antigravity skill specification
├── src/
│   ├── core/                           # Core asset models, DCF/Decomposition valuation, scoring
│   ├── research/                       # Macro analysis & multi-asset universe screener
│   ├── strategy/                       # 3-Stage scenario modeler, Barbell optimizer, Risk manager
│   ├── execution/                      # Investment memo generator & portfolio tracker
│   └── agent/                          # Investor agent runner orchestrator
└── tests/
    └── test_investor_agent.py          # Full test suite for valuation, scoring & barbell allocation
```

---

## ⚡ Quickstart & Execution

### 1. Run the Full Investment Pipeline & Export Memos:
```bash
python branch/investor_agent/main.py --export-memos ./branch/investor_agent/data/memos
```

### 2. Run Test Suite:
```bash
pytest branch/investor_agent/tests/test_investor_agent.py -v
```

---

## ⚖️ The Master Barbell Portfolio Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      TOTAL PORTFOLIO                        │
├──────────────────────────────┬──────────────────────────────┤
│      CORE ASSETS (60~70%)    │   SATELLITE ASSETS (30~40%)  │
├──────────────────────────────┼──────────────────────────────┤
│ • Geographic Monopolies      │ • Structural Bottlenecks     │
│   (Prime Land / Trophy RE)   │   (AI Semis, Power Grid)     │
│ • Hard Monetary Anchors      │ • Emerging Cluster Nodes     │
│   (Physical Gold, BTC)       │   (Mega Hubs, New Cap Flows) │
│ • Non-cyclical Cash Cows     │ • Asymmetric Convex Bets     │
│                              │   (High Payoff Mispricings)  │
└──────────────────────────────┴──────────────────────────────┘
```

### Dynamic Profit Harvesting Rule:
When any **Satellite asset** rerates by **\(\ge 2.5\times\) (+150% gain)**, systematically realize 50-70% of profits and reallocate into **Core Assets** to lock in permanent purchasing power.
