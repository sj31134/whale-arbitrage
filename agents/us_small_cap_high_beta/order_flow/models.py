"""
Core Data Models for Order Flow & Microstructure Short-Term Trading Subagent.
Supports both KRX (Korean Equities) and US (NASDAQ/NYSE Equities) with dynamic universe ingestion.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class MarketType(str, Enum):
    KRX = "KRX (한국)"
    US = "US (미국)"
    BINANCE_TOKENIZED = "Binance Tokenized RWA (바이낸스 24/7 토큰화 주식)"



class ActorType(str, Enum):
    # KRX & General
    RETAIL = "Retail (개인/Robinhood)"
    RETAIL_MARGIN = "Retail Margin (개인 신용/0DTE Calls)"
    FOREIGN = "Foreign / Offshore Hedge Funds (외국인/헤지펀드)"
    FOREIGN_PROGRAM = "Foreign Program (외인/HFT 차익·비차익)"
    FOREIGN_PASSIVE = "Foreign Passive (글로벌 패시브 ETF / Vanguard·BlackRock)"
    INST_PENSION = "Institutional Pension (연기금/엔다우먼트)"
    INST_INVTRUST = "Institutional Inv Trust (투신/뮤추얼펀드)"
    INST_FINANCIAL = "Institutional Financial (금융투자/프랍 데스크)"
    INST_PRIVATE_EQUITY = "Institutional Private Equity / Pods (사모/포드 샵)"
    INST_INSURANCE = "Institutional Insurance (보험/기타)"
    DARK_POOL = "Dark Pool / Block Traders (다크풀 대량 체결)"


class SupportResistanceType(str, Enum):
    SMART_MONEY_FLOOR = "Smart Money Floor (세력 지지선)"
    STRUCTURAL_COST_BASE = "Structural Cost Base (기관/외인 평단 지지선)"
    TRAPPED_RETAIL_CEILING = "Trapped Retail Ceiling (개인 물림 매물대 저항선)"
    HEAVY_OVERHEAD_SUPPLY = "Heavy Overhead Supply (대량 악성 매물 저항선)"
    MARGIN_LIQUIDATION_LINE = "Margin Liquidation Line (신용/마진콜 투매선)"
    POINT_OF_CONTROL = "Point of Control (POC 거래량 중심선)"
    DARK_POOL_VWAP = "Dark Pool VWAP (다크풀 고래 평단 지지선)"
    OPTIONS_GAMMA_WALL = "Options Gamma Wall (옵션 감마 콜/풋 벽 저항선)"


class TradingStrategyType(str, Enum):
    SMART_FLOOR_BOUNCE = "Smart Floor Bounce (세력 지지선 반등 매수)"
    SUPPLY_ABSORPTION_BREAKOUT = "Supply Absorption Breakout (매물 흡수 돌파 매수)"
    MARGIN_CASCADE_FLASH_ABSORPTION = "Margin Cascade Flash Absorption (신용 투매 과매도 바닥 매수)"
    PROGRAM_BASIS_ARBITRAGE = "Program Basis Arbitrage (선물 베이시스 연계 차익 매매)"
    DARK_POOL_FOLLOWING = "Dark Pool Volume Following (다크풀 고래 매집 추종 매수)"
    PROFIT_HARVEST = "Profit Harvest (상위 지침 기반 단기 익절)"
    RISK_STOP_OUT = "Risk Stop-Out (지지선 이탈 기계적 손절)"
    TIME_HORIZON_FLASH_LIQUIDITY = "Time-Horizon Flash Liquidity (시간지평 차익거래 / 봇 투매 역발상 분할 지정가)"


@dataclass
class CandidateStockItem:
    ticker: str
    name: str
    market: MarketType
    sector: str
    current_price: float
    currency: str = "KRW"
    daily_volume: int = 1_000_000
    daily_turnover: float = 50_000_000_000
    discovery_reason: str = "수급 이상 급증 및 병목 포착"
    is_new_candidate: bool = True


@dataclass
class ActorOrderFlow:
    actor_type: ActorType
    net_value_1d: float                  # 1일 순매수 대금 (KRW or USD)
    net_volume_1d: int                   # 1일 순매수 수량
    net_value_5d: float                  # 5일 누적 순매수 대금
    net_value_20d: float                 # 20일 누적 순매수 대금
    net_value_60d: float                 # 60일 누적 순매수 대금
    estimated_vwap_20d: float            # 20일 가중평균 매수단가
    estimated_vwap_60d: float            # 60일 가중평균 매수단가
    buy_ratio_pct: float                 # 매수 체결 비중 (0~100%)
    flow_intensity_zscore: float         # 과거 60일 대비 수급 강도 Z-Score
    is_accumulating: bool = False        # 순매수 누적 축적 여부


@dataclass
class SupportResistanceLevel:
    level_type: SupportResistanceType
    price: float
    strength_score: float                # 0.0 ~ 10.0 강도
    volume_density_pct: float            # 매물 집중도 (%)
    dominant_actor: ActorType
    description: str
    distance_from_current_pct: float     # 현재가 대비 이격률 (+% 저항, -% 지지)


@dataclass
class StockMicrostructureProfile:
    ticker: str
    name: str
    market: MarketType
    currency: str
    current_price: float
    daily_volume: int
    daily_turnover: float
    actor_flows: Dict[ActorType, ActorOrderFlow]
    support_levels: List[SupportResistanceLevel]
    resistance_levels: List[SupportResistanceLevel]
    poc_price: float                     # Point of Control
    smart_money_hand_off_ratio: float    # 스마트머니 vs 개인 수급 이전 비율 (-1.0 ~ +1.0)
    margin_debt_ratio_pct: float         # 신용잔고율 또는 Short Float (%)
    trapped_retail_loss_pct: float       # 개인 추정 물림 평균 손실률 (%)
    is_newly_discovered: bool = False


@dataclass
class ActorDynamicVariables:
    """
    글로벌(한국+미국) 구매 주체별 동적 영향 변수 풀
    """
    # 1. 외국인 / 글로벌 헤지펀드 변수 (Foreign & Global Hedge Drivers)
    usd_krw_rate: float = 1385.0
    usd_krw_change_5d_pct: float = -0.45
    futures_basis_spread: float = 1.40          # 코스피200 선물 스프레드
    us_spx_futures_basis: float = 4.50          # S&P500 E-mini 선물 베이시스
    us_10y_yield_pct: float = 4.736
    sox_semi_index_change_1d_pct: float = 2.15
    nasdaq_futures_change_pct: float = 0.75
    foreign_passive_flow_index: float = 8.0     # 0~10 scale
    us_dark_pool_activity_index: float = 7.8    # 0~10 scale
    us_0dte_gamma_imbalance: float = 0.35       # Positive = Gamma squeeze upward

    # 2. 기관 변수 (Institutional Drivers)
    window_dressing_proximity_days: int = 10    # 분기/반기 결산 잔여일
    kr_value_up_incentive_score: float = 8.8
    national_pension_equity_weight_room_pct: float = 1.8  # 연기금 국내주식 추가 매수 여력 (%)
    financial_inv_arbitrage_incentive: float = 6.5
    us_institutional_13f_inflow_score: float = 8.2

    # 3. 개인 변수 (Retail & Sentiment Drivers)
    market_margin_debt_trillion_krw: float = 20.8
    us_retail_sentiment_bull_ratio: float = 58.5 # AAII Bull-Bear Sentiment
    retail_deposit_growth_30d_pct: float = 3.1
    retail_fomo_search_index: float = 62.0      # 0~100 scale
    turnover_overheat_ratio: float = 1.15       # 20일 평균 대비 회전율 비율

    # 4. 퀀트 봇 강제청산 & 시간지평 차익거래 변수 (P5 Time-Horizon Arbitrage Drivers)
    cta_trend_liquidation_risk: float = 3.2     # CTA 봇 50D/200D 이평선 이탈 기계적 숏 트리거 위험도 (0~10 scale)
    pod_shop_stopout_cascade_index: float = 0.28 # 멀티매니저 팟샵(Point72 등) -3%~-5% 강제 손절 캐스케이드 지수 (0~1 scale)
    staggered_limit_depth_pct: float = 3.5      # 시간지평 차익거래용 분할 지정가 배치 깊이 (% below smart floor)

    # 5. 글로벌 정책 하방 보증 & 주주환원 변수 (P6 Policy Transmission Drivers)
    policy_ptc_floor_protection: float = 8.5    # 정부 법적 보조금/확정계약(IRA 45U, NASA 등) 하방 보장 점수 (0~10 scale)
    tse_value_up_mandate_urgency: float = 7.5   # PBR 1배 미달 퇴출 압박 및 밸류업 소각 강제 지수 (0~10 scale)

    # 6. 소액 자본 회전율 & 리레이팅 수확 변수 (P4 Small-Seed Velocity Drivers)
    multiple_rerating_harvest_ratio: float = 0.35 # 위성 자산 목표 멀티플 도달률 (0~1 scale, >=0.85 시 50% 분할 익절 수확)
    non_callable_float_leverage_ratio: float = 1.4 # 무이자 선수금 및 운용 플로트 레버리지 계수 (0~3.0x)

    # 7. 3계층 도메인 격리 하네스 (P12 & P13 Domain Isolation Harness)
    domain_isolation_scope: str = "EQUITY_TICKERS_ONLY" # Tier 2-A 주식 전용 격리 플래그


@dataclass
class NetworkShockImpact:
    source_variable: str
    shock_magnitude: float
    intermediate_actor: ActorType
    target_ticker: str
    transmitted_force: float
    transmission_channel: str


@dataclass
class ShortTermPriceForecast:
    ticker: str
    name: str
    market: MarketType
    currency: str
    current_price: float
    expected_price_1d: float
    expected_price_5d: float
    expected_return_1d_pct: float
    expected_return_5d_pct: float
    probability_up: float                # 상승 확률 (0.0 ~ 1.0)
    probability_down: float              # 하락 확률 (0.0 ~ 1.0)
    confidence_score: float              # 모델 신뢰도 (0.0 ~ 1.0)
    dominant_shocks: List[NetworkShockImpact] = field(default_factory=list)
    key_support_price: float = 0.0
    key_resistance_price: float = 0.0
    summary_narrative: str = ""


@dataclass
class MicrostructureTradeDecision:
    ticker: str
    name: str
    market: MarketType
    currency: str
    strategy: TradingStrategyType
    action: str                          # "BUY", "STRONG_BUY", "HARVEST", "STOP_LOSS", "HOLD"
    entry_price: float
    target_price: float
    stop_loss_price: float
    payoff_ratio: float                  # (Target - Entry) / (Entry - StopLoss) >= 3.0
    recommended_position_pct: float      # 추천 포트폴리오 비중
    parent_hurdle_passed: bool           # 상위 투자지침 통과 여부
    rationale: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
