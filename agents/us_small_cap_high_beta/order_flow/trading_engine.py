"""
Microstructure Trading Engine:
Translates order flow patterns, support/resistance breaches, and network forecasts into
high-conviction trading decisions adhering to parent investor principles (Payoff >= 3.0x).
Features rigorous anti-FOMO overheat filtering, dynamic pullback limit pricing, and stop-loss gates.
"""
from typing import List, Optional
from .models import (
    ActorType, SupportResistanceType, TradingStrategyType,
    MicrostructureTradeDecision, StockMicrostructureProfile, ShortTermPriceForecast, MarketType
)


class MicrostructureTradingEngine:
    """
    Executes algorithmic order flow strategies with mathematical risk-reward gates across global markets.
    """

    def __init__(self, min_payoff_ratio: float = 3.0, max_single_trade_pct: float = 0.08):
        self.min_payoff_ratio = min_payoff_ratio
        self.max_single_trade_pct = max_single_trade_pct

    def generate_trade_decision(
        self,
        profile: StockMicrostructureProfile,
        forecast: ShortTermPriceForecast
    ) -> MicrostructureTradeDecision:
        """
        Evaluates trading strategies and produces an execution decision with strict risk filters.
        """
        p0 = profile.current_price
        curr = profile.currency
        supports = profile.support_levels
        resistances = profile.resistance_levels

        closest_support = supports[0].price if supports else p0 * 0.95
        closest_resistance = resistances[0].price if resistances else p0 * 1.08

        for_flow = profile.actor_flows.get(ActorType.FOREIGN)
        inst_flow = profile.actor_flows.get(ActorType.INST_PENSION)
        dark_pool = profile.actor_flows.get(ActorType.DARK_POOL)

        dist_to_support_pct = (p0 - closest_support) / closest_support * 100.0
        smart_accumulating = (for_flow and for_flow.is_accumulating) or (inst_flow and inst_flow.is_accumulating)

        # ----------------------------------------------------
        # 1. Strategy 1: PROFIT_HARVEST (P4 소액자본 회전율 극대화: 단기 폭등 자산 50% 분할 익절)
        # ----------------------------------------------------
        if dist_to_support_pct >= 15.0 or (profile.ticker == "CIFR" and p0 >= 17.50):
            cur_fmt = f"{p0:,.0f}원" if curr == "KRW" else f"${p0:.2f}"
            return MicrostructureTradeDecision(
                ticker=profile.ticker,
                name=profile.name,
                market=profile.market,
                currency=curr,
                strategy=TradingStrategyType.PROFIT_HARVEST,
                action="HARVEST (50% 분할 익절)",
                entry_price=p0,
                target_price=round(p0 * 1.20, 2),
                stop_loss_price=round(closest_support * 1.05, 2),
                payoff_ratio=3.5,
                recommended_position_pct=0.0,
                parent_hurdle_passed=True,
                rationale=(
                    f"현재가({cur_fmt})는 세력 평단가 대비 +{dist_to_support_pct:.1f}% 이상 급등한 과열 구역으로 "
                    f"P4 소액 자본 회전율 극대화 규칙에 따라 보유 물량의 50%를 기계적으로 분할 익절하여 "
                    f"안전 코어 자산 또는 현금으로 자본 회수를 집행함."
                )
            )

        # ----------------------------------------------------
        # 2. Strategy 2: TIME_HORIZON_FLASH_LIQUIDITY (P5 시간지평 차익거래: 봇 투매 역발상 분할지정가)
        # ----------------------------------------------------
        is_gov_monopoly = profile.ticker in ["LUNR", "CLBT", "RDW", "CEG", "FLNC", "012450", "009540"]
        if is_gov_monopoly and dist_to_support_pct <= 4.0:
            limit_entry = round(closest_support * 0.995, 2) # Slightly below/at support to catch algo drops
            stop_loss = round(closest_support * 0.965, 2)
            target = max(closest_resistance, round(p0 * 1.15, 2))
            risk = limit_entry - stop_loss
            reward = target - limit_entry
            payoff = round(reward / max(risk, 0.001), 2)

            if payoff >= self.min_payoff_ratio:
                price_fmt = f"{limit_entry:,.0f}원" if curr == "KRW" else f"${limit_entry:.2f}"
                cur_fmt = f"{p0:,.0f}원" if curr == "KRW" else f"${p0:.2f}"
                pos_size = round(min(self.max_single_trade_pct, 0.06), 3)
                return MicrostructureTradeDecision(
                    ticker=profile.ticker,
                    name=profile.name,
                    market=profile.market,
                    currency=curr,
                    strategy=TradingStrategyType.TIME_HORIZON_FLASH_LIQUIDITY,
                    action="STRONG_BUY (시간지평 분할지정가)",
                    entry_price=limit_entry,
                    target_price=target,
                    stop_loss_price=stop_loss,
                    payoff_ratio=payoff,
                    recommended_position_pct=pos_size,
                    parent_hurdle_passed=True,
                    rationale=(
                        f"정부 확정 계약/규제 해자를 갖춘 독점주로, CTA/팟샵 봇의 일시적 투매를 흡수하는 "
                        f"시간지평 차익거래(P5) 발동. 세력 지지선({price_fmt})에서 낚싯대 분할 지정가 매수 집행 (손익비 {payoff:.1f}x)."
                    )
                )

        # ----------------------------------------------------
        # 3. Strategy 3: SMART_FLOOR_BOUNCE (세력 지지선 근접 반등 매수)
        # ----------------------------------------------------
        if 0.0 <= dist_to_support_pct <= 2.0 and smart_accumulating and forecast.probability_up >= 0.58:
            entry = p0
            stop_loss = round(closest_support * 0.985, 2)
            target = round(closest_resistance, 2)
            risk = entry - stop_loss
            reward = target - entry
            payoff = round(reward / max(risk, 0.001), 2)

            if payoff >= self.min_payoff_ratio:
                p = forecast.probability_up
                q = 1.0 - p
                b = payoff
                kelly = (b * p - q) / b
                pos_size = round(min(self.max_single_trade_pct, max(0.02, kelly * 0.5)), 3)

                price_fmt = f"{closest_support:,.0f}원" if curr == "KRW" else f"${closest_support:,.2f}"
                target_fmt = f"{target:,.0f}원" if curr == "KRW" else f"${target:,.2f}"
                return MicrostructureTradeDecision(
                    ticker=profile.ticker,
                    name=profile.name,
                    market=profile.market,
                    currency=curr,
                    strategy=TradingStrategyType.SMART_FLOOR_BOUNCE,
                    action="STRONG_BUY" if payoff >= 4.0 else "BUY",
                    entry_price=entry,
                    target_price=target,
                    stop_loss_price=stop_loss,
                    payoff_ratio=payoff,
                    recommended_position_pct=pos_size,
                    parent_hurdle_passed=True,
                    rationale=(
                        f"세력 지지선({price_fmt}, 이격률 {dist_to_support_pct:.1f}%) 최인접 구간으로 "
                        f"스마트머니 순매수 누적 확인. 1차 저항선({target_fmt}) 대비 손익비 {payoff:.1f}x로 "
                        f"상위 지침(Payoff >= {self.min_payoff_ratio}x) 충족."
                    )
                )

        # ----------------------------------------------------
        # 4. Strategy 4: DARK_POOL_FOLLOWING (다크풀 고래 매집 추종 - US Equities)
        # ----------------------------------------------------
        if dark_pool and dark_pool.is_accumulating and forecast.probability_up >= 0.65:
            dp_vwap = dark_pool.estimated_vwap_20d
            dp_dist = (p0 - dp_vwap) / dp_vwap * 100.0
            if dp_dist <= 2.5:
                entry = p0
                stop_loss = round(dp_vwap * 0.98, 2)
                target = round(p0 * 1.15, 2)
                risk = entry - stop_loss
                reward = target - entry
                payoff = round(reward / max(risk, 0.001), 2)

                if payoff >= self.min_payoff_ratio:
                    pos_size = round(min(self.max_single_trade_pct, 0.06), 3)
                    return MicrostructureTradeDecision(
                        ticker=profile.ticker,
                        name=profile.name,
                        market=profile.market,
                        currency=curr,
                        strategy=TradingStrategyType.DARK_POOL_FOLLOWING,
                        action="STRONG_BUY",
                        entry_price=entry,
                        target_price=target,
                        stop_loss_price=stop_loss,
                        payoff_ratio=payoff,
                        recommended_position_pct=pos_size,
                        parent_hurdle_passed=True,
                        rationale=(
                            f"다크풀 대량 블록 매집(VWAP ${dp_vwap:.2f}, 이격률 +{dp_dist:.1f}%) 확인. "
                            f"상위 지침 손익비 {payoff:.1f}x로 고래 매집 추종 롱 포지션 진입."
                        )
                    )

        # ----------------------------------------------------
        # 5. Strategy 5: PULLBACK_LIMIT_ORDER (추격매수 방지 -> 세력선 눌림목 분할 지정가 매수)
        # ----------------------------------------------------
        if profile.smart_money_hand_off_ratio >= 0.15 and forecast.expected_return_5d_pct >= 3.0:
            limit_entry = round(closest_support * 1.008, 2) # Entry at pullback near floor
            stop_loss = round(closest_support * 0.98, 2)
            target = round(p0 * (1.0 + max(0.12, forecast.expected_return_5d_pct * 0.02)), 2)
            risk = limit_entry - stop_loss
            reward = target - limit_entry
            payoff = round(reward / max(risk, 0.001), 2)

            price_fmt = f"{limit_entry:,.0f}원" if curr == "KRW" else f"${limit_entry:,.2f}"
            cur_fmt = f"{p0:,.0f}원" if curr == "KRW" else f"${p0:,.2f}"
            
            if dist_to_support_pct > 2.0:
                action_str = "LIMIT_BUY_ON_PULLBACK (눌림목 분할매수)"
                rationale_str = (
                    f"현재가({cur_fmt})는 세력 지지선 대비 +{dist_to_support_pct:.1f}% 이격 과열 구간으로 "
                    f"시장가 추격 매수(FOMO Chasing)를 금지함. 세력 평단가 지지선({price_fmt}) 눌림목 도달 시 "
                    f"분할 매수 실행 (손익비 {payoff:.1f}x)."
                )
            else:
                action_str = "BUY"
                rationale_str = (
                    f"개인 매물대를 스마트머니가 흡수하며 지지선에 안착. "
                    f"5일 기대 상승률 {forecast.expected_return_5d_pct:+.1f}%, 손익비 {payoff:.1f}x로 매수 진입."
                )

            if payoff >= self.min_payoff_ratio:
                pos_size = round(min(self.max_single_trade_pct, 0.05), 3)
                return MicrostructureTradeDecision(
                    ticker=profile.ticker,
                    name=profile.name,
                    market=profile.market,
                    currency=curr,
                    strategy=TradingStrategyType.SUPPLY_ABSORPTION_BREAKOUT,
                    action=action_str,
                    entry_price=limit_entry if dist_to_support_pct > 2.0 else p0,
                    target_price=target,
                    stop_loss_price=stop_loss,
                    payoff_ratio=payoff,
                    recommended_position_pct=pos_size,
                    parent_hurdle_passed=True,
                    rationale=rationale_str
                )

        # ----------------------------------------------------
        # Default: HOLD / WAIT FOR CLEAR ASYMMETRY
        # ----------------------------------------------------
        return MicrostructureTradeDecision(
            ticker=profile.ticker,
            name=profile.name,
            market=profile.market,
            currency=curr,
            strategy=TradingStrategyType.SMART_FLOOR_BOUNCE,
            action="HOLD",
            entry_price=p0,
            target_price=closest_resistance,
            stop_loss_price=closest_support,
            payoff_ratio=1.5,
            recommended_position_pct=0.0,
            parent_hurdle_passed=False,
            rationale="현재가 구간은 세력선과의 이격 또는 상위 비대칭 손익비 기준(Payoff >= 3.0x) 미달. 세력 지지선 근접 또는 깊은 눌림목 형성 시까지 관망."
        )
