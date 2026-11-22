"""
Impact Network Engine:
Defines buyer-specific dynamic variables and propagates causal shocks through a directed network graph
to generate probabilistic 1-day and 5-day price forecasts across Korean and US markets.
"""
from typing import Dict, List, Any, Optional
import math
from .models import (
    ActorType, ActorDynamicVariables, NetworkShockImpact,
    ShortTermPriceForecast, StockMicrostructureProfile, MarketType
)


class ImpactNetworkEngine:
    """
    Network Graph Causal Propagation Engine:
    Models how macroeconomic shifts, algorithmic derivatives triggers, dark pool prints,
    and policy incentives transmit through Foreign, Institutional, and Retail cohorts into stock price trajectories.
    """

    def __init__(self):
        self.variables = ActorDynamicVariables()
        self.network_edges = self._initialize_network_topology()

    def update_variables(self, new_vars: ActorDynamicVariables):
        self.variables = new_vars

    def forecast_price_trajectory(
        self,
        profile: StockMicrostructureProfile,
        custom_variables: Optional[ActorDynamicVariables] = None
    ) -> ShortTermPriceForecast:
        """
        Propagates all active dynamic variables through the causal graph to forecast short-term prices.
        """
        vars_to_use = custom_variables or self.variables
        ticker = profile.ticker
        p0 = profile.current_price
        is_us = profile.market == MarketType.US or profile.currency == "USD"

        # P12/P13: Domain Strict Isolation Check (Enforce Equity Only)
        if getattr(vars_to_use, "domain_isolation_scope", "") == "EQUITY_TICKERS_ONLY":
            invalid_terms = ["villa", "auction", "land", "경매", "대지지분", "빌라", "재개발"]
            if any(term in ticker.lower() or term in profile.name.lower() for term in invalid_terms):
                raise ValueError(f"🚨 [DOMAIN ISOLATION VIOLATION] Subagent is strictly scoped to EQUITY_TICKERS_ONLY. Rejected: {ticker} ({profile.name})")

        # 1. Evaluate Shocks & Multi-hop Transmissions
        shocks: List[NetworkShockImpact] = []
        total_net_force = 0.0

        if not is_us:
            # ====================================================
            # KOREAN MARKET (KRX) SPECIFIC TRANSMISSION CHANNELS
            # ====================================================
            # A1: USD/KRW drop (Won appreciation) -> Foreign spot/program buying
            fx_shock = -vars_to_use.usd_krw_change_5d_pct
            fx_force = fx_shock * 0.45
            total_net_force += fx_force
            shocks.append(NetworkShockImpact(
                source_variable=f"USD/KRW 5D 변동 ({vars_to_use.usd_krw_change_5d_pct:+.2f}%)",
                shock_magnitude=fx_shock,
                intermediate_actor=ActorType.FOREIGN,
                target_ticker=ticker,
                transmitted_force=round(fx_force, 4),
                transmission_channel="원화 강세 안정 -> 외인 패시브/현물 순매수 유입"
            ))

            # A2: KOSPI200 Futures Basis Spread
            basis_spread = vars_to_use.futures_basis_spread
            basis_force = max(-2.0, min(2.0, basis_spread * 0.60))
            total_net_force += basis_force
            shocks.append(NetworkShockImpact(
                source_variable=f"선물 베이시스 스프레드 (+{basis_spread:.2f}pt)",
                shock_magnitude=basis_spread,
                intermediate_actor=ActorType.FOREIGN_PROGRAM,
                target_ticker=ticker,
                transmitted_force=round(basis_force, 4),
                transmission_channel="선물 콘탱고 -> 무차익 프로그램 순매수 유입"
            ))

            # A3: Value-Up & Governance Policy
            val_score = vars_to_use.kr_value_up_incentive_score
            val_force = (val_score - 5.0) * 0.25
            total_net_force += val_force
            shocks.append(NetworkShockImpact(
                source_variable=f"밸류업/지배구조 인센티브 ({val_score:.1f}/10)",
                shock_magnitude=val_score,
                intermediate_actor=ActorType.INST_PENSION,
                target_ticker=ticker,
                transmitted_force=round(val_force, 4),
                transmission_channel="정부 밸류업 개혁 -> 연기금/투신 바스켓 매수"
            ))

        else:
            # ====================================================
            # US MARKET (NASDAQ/NYSE) SPECIFIC TRANSMISSION CHANNELS
            # ====================================================
            # B1: Nasdaq Futures & Liquidity Sentiment
            nq_change = vars_to_use.nasdaq_futures_change_pct
            nq_force = nq_change * 1.20
            total_net_force += nq_force
            shocks.append(NetworkShockImpact(
                source_variable=f"Nasdaq Futures ({nq_change:+.2f}%)",
                shock_magnitude=nq_change,
                intermediate_actor=ActorType.FOREIGN_PASSIVE,
                target_ticker=ticker,
                transmitted_force=round(nq_force, 4),
                transmission_channel="Big Tech / Nasdaq Liquidity Momentum -> Institutional Long Expansion"
            ))

            # B2: US Dark Pool Whale Inflow
            dp_score = vars_to_use.us_dark_pool_activity_index
            dp_force = (dp_score - 5.0) * 0.35
            total_net_force += dp_force
            shocks.append(NetworkShockImpact(
                source_variable=f"US Dark Pool Block Print Activity ({dp_score:.1f}/10)",
                shock_magnitude=dp_score,
                intermediate_actor=ActorType.DARK_POOL,
                target_ticker=ticker,
                transmitted_force=round(dp_force, 4),
                transmission_channel="Dark Pool High-Volume Absorption -> Supply Freezing"
            ))

            # B3: 0DTE Options Gamma Squeeze
            gamma_imb = vars_to_use.us_0dte_gamma_imbalance
            gamma_force = gamma_imb * 1.50
            total_net_force += gamma_force
            shocks.append(NetworkShockImpact(
                source_variable=f"0DTE Gamma Imbalance (+{gamma_imb:.2f})",
                shock_magnitude=gamma_imb,
                intermediate_actor=ActorType.FOREIGN_PROGRAM,
                target_ticker=ticker,
                transmitted_force=round(gamma_force, 4),
                transmission_channel="Market Maker Delta Hedging -> Upward Squeeze"
            ))

            # B4: 13F Institutional Inflow
            inflow_score = vars_to_use.us_institutional_13f_inflow_score
            inflow_force = (inflow_score - 5.0) * 0.30
            total_net_force += inflow_force
            shocks.append(NetworkShockImpact(
                source_variable=f"13F Institutional Inflow ({inflow_score:.1f}/10)",
                shock_magnitude=inflow_score,
                intermediate_actor=ActorType.INST_PENSION,
                target_ticker=ticker,
                transmitted_force=round(inflow_force, 4),
                transmission_channel="Tier-1 Asset Manager Accumulation -> Long-Term Floor"
            ))

        # --- GLOBAL COMMON CHANNEL: Semiconductor / Tech Sentiment ---
        sox_change = vars_to_use.sox_semi_index_change_1d_pct
        is_tech = ticker in ["005930", "000660", "042700", "277810", "NVDA", "AVGO", "ARM", "PLTR", "APP", "267260", "010120"]
        tech_multiplier = 1.30 if is_tech else 0.45
        sox_force = sox_change * 0.50 * tech_multiplier
        total_net_force += sox_force
        shocks.append(NetworkShockImpact(
            source_variable=f"SOX Semiconductor Index 1D ({sox_change:+.2f}%)",
            shock_magnitude=sox_change,
            intermediate_actor=ActorType.FOREIGN,
            target_ticker=ticker,
            transmitted_force=round(sox_force, 4),
            transmission_channel="글로벌 AI/반도체 하드웨어 공급망 센티먼트 확장"
        ))

        # --- Smart Money Hand-Off Reinforcement ---
        hand_off = profile.smart_money_hand_off_ratio
        smart_boost = hand_off * 1.50
        total_net_force += smart_boost

        # --- P5: CTA & Pod Shop Liquidation Cascade Shock (시간지평 차익거래 채널) ---
        cta_risk = getattr(vars_to_use, "cta_trend_liquidation_risk", 3.2)
        pod_cascade = getattr(vars_to_use, "pod_shop_stopout_cascade_index", 0.28)
        bot_cascade_force = -((cta_risk / 10.0) * 0.35 + pod_cascade * 0.75)
        total_net_force += bot_cascade_force
        shocks.append(NetworkShockImpact(
            source_variable=f"CTA/Pod Shop Stop-Out Risk (CTA: {cta_risk:.1f}/10, Cascade: {pod_cascade:.2f})",
            shock_magnitude=pod_cascade,
            intermediate_actor=ActorType.INST_PRIVATE_EQUITY,
            target_ticker=ticker,
            transmitted_force=round(bot_cascade_force, 4),
            transmission_channel="퀀트 봇 이평선 이탈 숏 & 팟샵 -3%~-5% 기계적 손절 캐스케이드 (일시적 수급 왜곡)"
        ))

        # --- P6: Policy Transmission & Downside Floor Protection (정부 확정 계약 하방 보증) ---
        policy_score = getattr(vars_to_use, "policy_ptc_floor_protection", 8.5)
        is_gov_monopoly = ticker in ["LUNR", "CLBT", "RDW", "CEG", "FLNC", "012450", "009540"]
        if is_gov_monopoly:
            gov_force = (policy_score / 10.0) * 1.45
            total_net_force += gov_force
            shocks.append(NetworkShockImpact(
                source_variable=f"정부 확정 계약 및 정책 하방 보증 ({policy_score:.1f}/10)",
                shock_magnitude=policy_score,
                intermediate_actor=ActorType.INST_PENSION,
                target_ticker=ticker,
                transmitted_force=round(gov_force, 4),
                transmission_channel="미국 정부(NASA/DoD)/규제/인도 국영 조선 확정 계약 기반 하방 가격 탄력 복원력"
            ))

        # --- P4: Multiple Rerating Harvest Pressure (위성 자산 리레이팅 수확 신호) ---
        harvest_ratio = getattr(vars_to_use, "multiple_rerating_harvest_ratio", 0.35)
        is_overextended = ticker in ["BOT"]
        if is_overextended and harvest_ratio >= 0.30:
            harvest_force = -(harvest_ratio * 1.50)
            total_net_force += harvest_force
            shocks.append(NetworkShockImpact(
                source_variable=f"자본 회전율 익절 수확 신호 (Harvest: {harvest_ratio:.2f})",
                shock_magnitude=harvest_ratio,
                intermediate_actor=ActorType.INST_FINANCIAL,
                target_ticker=ticker,
                transmitted_force=round(harvest_force, 4),
                transmission_channel="단기 폭등에 따른 위성 자산 분할 익절 및 코어 자본 회수 압력"
            ))

        # 2. Calculate 1D & 5D Expected Price and Probabilities
        ret_1d_pct = total_net_force * 0.65
        ret_5d_pct = total_net_force * 1.85

        exp_p_1d = round(p0 * (1.0 + ret_1d_pct / 100.0), 2)
        exp_p_5d = round(p0 * (1.0 + ret_5d_pct / 100.0), 2)

        # Logistic transformation for Up/Down Probability
        prob_up = round(1.0 / (1.0 + math.exp(-total_net_force * 0.60)), 3)
        prob_up = max(0.05, min(0.95, prob_up))
        prob_down = round(1.0 - prob_up, 3)

        # Model Confidence Score
        variance = sum([abs(s.transmitted_force) for s in shocks]) / (len(shocks) or 1)
        confidence = round(min(0.95, max(0.50, abs(total_net_force) / (variance + 1.0))), 2)

        # Key Support and Resistance extraction
        key_sup = profile.support_levels[0].price if profile.support_levels else p0 * 0.95
        key_res = profile.resistance_levels[0].price if profile.resistance_levels else p0 * 1.05

        # Summary Narrative
        lead_shock = max(shocks, key=lambda s: abs(s.transmitted_force))
        direction_kr = "상승 압력 우세" if total_net_force > 0 else "하방 압력 우세"
        narrative = (
            f"네트워크 충격 합성 순영향력 {total_net_force:+.2f}로 {direction_kr} (상승확률 {prob_up*100:.1f}%). "
            f"주도 요인은 [{lead_shock.intermediate_actor.value}]를 경유한 '{lead_shock.source_variable}' "
            f"(전달력 {lead_shock.transmitted_force:+.2f}). "
            f"단기 1일 기대수익률 {ret_1d_pct:+.2f}%, 5일 기대수익률 {ret_5d_pct:+.2f}%."
        )

        return ShortTermPriceForecast(
            ticker=ticker,
            name=profile.name,
            market=profile.market,
            currency=profile.currency,
            current_price=p0,
            expected_price_1d=exp_p_1d,
            expected_price_5d=exp_p_5d,
            expected_return_1d_pct=round(ret_1d_pct, 2),
            expected_return_5d_pct=round(ret_5d_pct, 2),
            probability_up=prob_up,
            probability_down=prob_down,
            confidence_score=confidence,
            dominant_shocks=shocks,
            key_support_price=key_sup,
            key_resistance_price=key_res,
            summary_narrative=narrative
        )

    def _initialize_network_topology(self) -> Dict[str, float]:
        return {
            "USD_KRW_TO_FOREIGN_FLOW": -0.85,
            "FUTURES_BASIS_TO_PROGRAM_FLOW": 0.90,
            "NASDAQ_TO_TECH_FLOW": 0.92,
            "DARK_POOL_TO_PRICE_FLOOR": 0.88,
            "OPTIONS_GAMMA_TO_SQUEEZE": 0.85,
            "SOX_TO_SEMI_FOREIGN_FLOW": 0.92,
            "VALUE_UP_TO_PENSION_FLOW": 0.75,
            "SMART_MONEY_TO_EQUITY_PRICE": 0.95
        }
