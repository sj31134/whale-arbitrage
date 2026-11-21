"""
Timeline Schema: Comprehensive models for multi-asset timeline variables across
Real Estate, Semiconductors/Tech, Shipbuilding/Defense, Energy/Commodities, and Finance/Crypto.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class MacroTimelineMetrics:
    us_10y_yield_pct: float = 5.136
    us_30y_yield_pct: float = 5.525
    global_m2_yoy_pct: float = 7.4
    dxy_dollar_index: float = 106.20
    fed_funds_rate_pct: float = 4.75
    boj_policy_rate_pct: float = 0.50
    us_sovereign_debt_trillion_usd: float = 37.2
    core_cpi_yoy_pct: float = 3.1
    usdkrw_exchange_rate: float = 1327.95


@dataclass
class RealEstateTimelineMetrics:
    seoul_apt_supply_annual_units: int = 12500            # 2026년 서울 신규 입주물량 (역대 최저치)
    seoul_reconstruction_cost_pyeong_krw: int = 10500000 # 평당 공사비 1,050만 원 돌파
    seoul_jeonse_supply_index: float = 104.5             # 전세수급지수 100 상회 (전세 품귀 현상)
    seoul_consecutive_rise_weeks: int = 79               # 79주 연속 아파트 가격 상승세
    chungcheong_semi_cluster_capex_trillion_krw: float = 360.0 # 삼성/하이닉스 천안·아산·청주 팹 투자액
    chungbuk_battery_motherfab_capex_trillion_krw: float = 35.0 # LG엔솔/에코프로 오창 마더팩토리


@dataclass
class SemiTechTimelineMetrics:
    dram_spot_dxi_index: float = 38500.0                 # D램 현물 DXI 지수 반등세
    hbm4_12hi_contract_price_usd: float = 480.0          # HBM4 12단 베이스다이 턴키 단가 ($480)
    tsmc_cowos_monthly_wafer_capacity: int = 65000       # TSMC CoWoS 월간 캐파 6.5만 장
    asml_high_na_euv_annual_deliveries: int = 12         # ASML High-NA EUV 연간 12대 인도
    silicon_wafer_300mm_utilization_pct: float = 88.5    # 신에츠/섬코 300mm 웨이퍼 가동률 회복
    hyperscaler_annual_ai_capex_billion_usd: float = 245.0 # 빅테크 4사 합산 연간 AI CAPEX
    pricing_inelasticity_score: float = 0.88             # [화식열전 만배부자] 독점 플랫폼 가격결정권 비탄력성 (0.0~1.0)
    megacycle_capex_yoy_velocity_pct: float = 42.5       # [화식열전 기호쟁시] 빅테크 AI 인프라 Capex YoY 가속도 (%)


@dataclass
class ShipbuildingTimelineMetrics:
    clarksons_newbuilding_price_index: float = 189.5     # 클락슨 신조선가지수 (16년 만의 최고치)
    lng_carrier_174k_newbuild_usd_million: float = 268.0 # LNG 운반선 척당 가격 ($2.68억 달러)
    vlac_ammonia_carrier_usd_million: float = 125.0      # 초대형 암모니아선 척당 ($1.25억 달러)
    korean_shipyard_dock_backlog_years: float = 4.2      # 국내 조선 빅3 도크 수주잔고 (4.2년 치)
    us_navy_mro_annual_market_billion_usd: float = 32.0  # 미 해군 함정 MRO 시장 규모 ($320억 달러)


@dataclass
class EnergyCommodityTimelineMetrics:
    brent_crude_usd_bbl: float = 91.20
    wti_crude_usd_bbl: float = 86.50
    copper_spot_usd_lb: float = 6.556
    copper_lme_inventory_tons: int = 145000
    uranium_spot_usd_lb: float = 88.00
    potash_fob_vancouver_usd_ton: float = 340.0
    singapore_complex_refining_margin_usd: float = 7.80
    gold_spot_usd_oz: float = 4475.00
    gold_paxg_binance_usd: float = 4475.00
    grid_interconnect_queue_years: float = 5.8          # [화식열전 한즉자주] 전력망 계통연계 병목 대기기간 (년)


@dataclass
class FinanceCryptoTimelineMetrics:
    kr_commercial_code_mandatory_treasury_cancel: bool = True # 상법 개정 자사주 1년 내 의무소각 시행
    krx_daily_turnover_trillion_krw: float = 21.5             # 국내 증시 일평균 거래대금
    btc_network_hashrate_ehs: float = 685.0                   # 비트코인 네트워크 해시레이트
    stablecoin_total_marketcap_billion_usd: float = 185.0     # 글로벌 스테이블코인 시가총액
    net_cash_to_mcap_pct: float = 24.5                        # [화식열전 창름실] 코어 요새 기업 시총 대비 순현금 곳간 비율 (%)


@dataclass
class PolicyTimelineState:
    us_ira_45u_nuclear_ptc_active: bool = True
    us_chips_act_subsidy_deployed_pct: float = 78.5
    kr_value_up_tax_incentive_active: bool = True
    kr_real_estate_pf_put_active: bool = True
    jp_tse_pbr_1x_mandate_progress_pct: float = 74.0
    cn_nine_measures_dividend_enforced: bool = True
    nato_2pct_gdp_defense_mandate_pct: float = 2.1


@dataclass
class MarketMicrostructureMetrics:
    vix_index: float = 16.87
    vkospi_index: float = 55.20                          # 코스피200 공포지수 (40 이상 시 기계적 강제 청산 레짐)
    futures_basis_regime: str = "BACKWARDATION"          # CONTANGO / BACKWARDATION
    sidecar_triggered: bool = True                       # 프로그램 매도 사이드카 발동 여부
    vol_derisking_active: bool = True                    # 변동성 목표 펀드 기계적 주식 비중 축소 활성화
    algo_flash_overshoot_detected: bool = True
    options_0dte_gamma_regime: str = "EXTREME_SHORT_GAMMA"
    liquidity_condition: str = "ALGORITHMIC_FLASH_CASCADE"


@dataclass
class TimelineDataSnapshot:
    as_of_date: str = "2026-10-20"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    macro: MacroTimelineMetrics = field(default_factory=MacroTimelineMetrics)
    real_estate: RealEstateTimelineMetrics = field(default_factory=RealEstateTimelineMetrics)
    semiconductors: SemiTechTimelineMetrics = field(default_factory=SemiTechTimelineMetrics)
    shipbuilding: ShipbuildingTimelineMetrics = field(default_factory=ShipbuildingTimelineMetrics)
    energy_commodities: EnergyCommodityTimelineMetrics = field(default_factory=EnergyCommodityTimelineMetrics)
    finance_crypto: FinanceCryptoTimelineMetrics = field(default_factory=FinanceCryptoTimelineMetrics)
    policy: PolicyTimelineState = field(default_factory=PolicyTimelineState)
    microstructure: MarketMicrostructureMetrics = field(default_factory=MarketMicrostructureMetrics)
    dynamic_feed_status: str = "LIVE_SYNCED_2026_10_20"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
