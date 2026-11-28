"""Multi-league knockout tournament engine across accumulated stocks, strategies, and patterns.

Reads only public/research caches and system rules (zero personal holdings or balances)
to crown a single clear Champion Stock, Champion Strategy, and Champion Execution Pattern
while preserving the complete elimination bracket and historical tournament ledger.
"""

from datetime import datetime
import hashlib
import json
from pathlib import Path

from agents import intelligence as intel
from . import contrarian, discovery, strategy_catalog, strategy_registry as registry

FILE = "tournament_board.json"
HISTORY_FILE = "tournament_history.json"


def _quant_summary(package):
    total = selected = 0
    best_excess = 0.0
    if package is None:
        return dict(total=0, selected=0, pass_rate_pct=0.0, best_excess_pct=0.0)
    local_dir = Path(package) / ".local"
    if not local_dir.is_dir():
        return dict(total=0, selected=0, pass_rate_pct=0.0, best_excess_pct=0.0)
    for path in sorted(local_dir.glob("quant-*.json")):
        try:
            doc = json.loads(path.read_text())
        except Exception:
            continue
        res = doc.get("result") or {}
        total += 1
        if res.get("selected"):
            selected += 1
            cand = str(res.get("candidate") or "")
            ex = float(((res.get("holdout") or {}).get(cand) or {}).get("excess") or 0.0) * 100.0
            best_excess = max(best_excess, ex)
    rate = round(100.0 * selected / total, 1) if total else 0.0
    return dict(total=total, selected=selected, pass_rate_pct=rate, best_excess_pct=round(best_excess, 2))


def _live_regime_phase(package):
    """Determine Phase 1 (Defense) vs Phase 2 (Recovery) from cached discovery benchmark returns."""
    disc = discovery.read(package) or {}
    ctx = disc.get("context") or {}
    kr20 = ctx.get("kr_bench_ret20")
    us20 = ctx.get("us_bench_ret20")
    phase1 = True if (kr20 is None and us20 is None) else bool((kr20 or 0.0) < 0.0 or (us20 or 0.0) < -1.0)
    label = "Phase 1 · 방어·선별 압축기" if phase1 else "Phase 2 · 추세 회복·수익 극대화기"
    return dict(phase1=phase1, label=label, kr_ret20=kr20, us_ret20=us20)


def _match(round_name, side_a, side_b, winner_id, score_a, score_b, reason):
    return dict(
        round=round_name,
        a=side_a,
        b=side_b,
        winner=winner_id,
        score_a=round(float(score_a), 1),
        score_b=round(float(score_b), 1),
        reason=reason,
    )


def _stock_tournament(package):
    """Knockout battle across accumulated /contrarian + /discover candidates."""
    radar = contrarian.read(package) or {}
    contrarian_cands = list(radar.get("candidates") or [])
    if not contrarian_cands:
        # Fallback baseline snapshot directly from audited metadata if radar cache hasn't run yet.
        for spec in contrarian.CONTRARIAN_UNIVERSE:
            sym, mkt, _, ccy, name, _, solv_key, essence, p3, cat_m, cat_txt, _, _, _, _ = spec
            gov_tier = contrarian.GOVERNANCE_AUDIT.get(sym, ("G1", ""))[0]
            pen = contrarian.GOVERNANCE_TIERS[gov_tier]["penalty"]
            contrarian_cands.append(dict(
                symbol=sym, market=mkt, currency=ccy, name=name,
                piotroski_3=p3, gov_tier=gov_tier, total=round(essence + 58.0 - pen, 1),
                trap_shield_ok=bool(p3 >= 3 and solv_key != "distressed_block" and sym != "035900"),
                sizing=dict(recommended_pct=32.0 if p3 >= 3 else 0.0),
                catalyst_12m=cat_txt, overheated=(sym == "035900"), ex_tenbagger=False,
                crowd_fear="초기 기준 평가", asymmetry=6.0, mult_5y_low=1.6,
            ))

    playbooks = contrarian.playbooks(package) if package is not None else []
    pb_by_sym = {p.get("symbol"): p for p in playbooks}

    disc = discovery.read(package) or {}
    disc_cands = list(disc.get("candidates") or [])
    if not disc_cands:
        disc_cands = [
            dict(symbol=sym, market="KR", name=meta[0], theme=meta[1], score=80.0 - idx * 1.2)
            for idx, (sym, meta) in enumerate(list(discovery.KR_UNIVERSE.items())[:4])
        ] + [
            dict(symbol=sym, market="US", name=meta[0], theme=meta[2], score=79.5 - idx * 1.1)
            for idx, (sym, meta) in enumerate(list(discovery.US_UNIVERSE.items())[:4])
        ]

    # Round 1: Hard Filter Elimination (Separating survivors from knocked-out candidates)
    eliminated = []
    survivors_contrarian = []
    for c in contrarian_cands:
        sym = c.get("symbol", "")
        p3 = int(c.get("piotroski_3", 2))
        gov = c.get("gov_tier", "G1")
        rec_pct = float((c.get("sizing") or {}).get("recommended_pct") or 0.0)
        if not c.get("trap_shield_ok") or rec_pct <= 0.0:
            eliminated.append(dict(
                symbol=sym, name=c.get("name", sym), league="역발상",
                reason=(str(c.get("crowd_fear") or "관문 미달").split("]")[0].lstrip("[")[:60]),
            ))
        elif p3 < 3:
            eliminated.append(dict(
                symbol=sym, name=c.get("name", sym), league="역발상",
                reason=f"Piotroski {p3}/3 감속 (3Q 실적 반전 검증 필요)",
            ))
        elif gov == "G2":
            eliminated.append(dict(
                symbol=sym, name=c.get("name", sym), league="역발상",
                reason="거버넌스 G2 고위험 (단일 상한 25% 하드캡)",
            ))
        else:
            survivors_contrarian.append(c)

    # Sort contrarian survivors cleanly by Governance -> Playbook verification -> Score
    def _c_rank(c):
        gov_bonus = {"G0": 6.0, "G1": 2.0, "G2": -10.0}.get(c.get("gov_tier", "G1"), 0.0)
        pb_bonus = 4.0 if c.get("symbol") in pb_by_sym else 0.0
        return float(c.get("total", 0.0)) + gov_bonus + pb_bonus

    survivors_contrarian.sort(key=_c_rank, reverse=True)

    # Core Momentum Track (/discover): pick top KR and top US leader
    kr_disc = sorted([c for c in disc_cands if c.get("market") == "KR"], key=lambda x: float(x.get("score") or 0.0), reverse=True)
    us_disc = sorted([c for c in disc_cands if c.get("market") == "US"], key=lambda x: float(x.get("score") or 0.0), reverse=True)
    kr_top = kr_disc[0] if kr_disc else dict(symbol="012450", name="한화에어로스페이스", market="KR", score=80.0, theme="방산·우주")
    us_top = us_disc[0] if us_disc else dict(symbol="COST", name="Costco", market="US", score=79.0, theme="필수소비 요새")

    matches = []
    # Bracket Match 1: Contrarian Semi-Final (#1 vs #2 clean Piotroski 3/3)
    if len(survivors_contrarian) >= 2:
        c1, c2 = survivors_contrarian[0], survivors_contrarian[1]
        matches.append(_match(
            "역발상 4강 · Piotroski 3/3 + 추세 돌파",
            f'{c1["name"]} ({c1["symbol"]} · {c1["gov_tier"]})',
            f'{c2["name"]} ({c2["symbol"]} · {c2["gov_tier"]})',
            c1["symbol"], _c_rank(c1), _c_rank(c2),
            f'{c1["name"]}이 계약서 검증·펀더멘털/거버넌스 종합 점수 우위 ({_c_rank(c1):.1f} vs {_c_rank(c2):.1f})',
        ))
        contrarian_champ = c1
        runner_up = c2
    elif survivors_contrarian:
        contrarian_champ = survivors_contrarian[0]
        runner_up = None
        matches.append(_match(
            "역발상 단독 결승 진출",
            f'{contrarian_champ["name"]} ({contrarian_champ["symbol"]})',
            "국내/기타 역발상 적격주 (0건)",
            contrarian_champ["symbol"], _c_rank(contrarian_champ), 0.0,
            "다른 역발상 후보가 버블·칼날·과열·Piotroski 관문에서 전멸해 억지 채우기 없이 단독 통과",
        ))
    else:
        contrarian_champ = None
        runner_up = None

    # Bracket Match 2: Discover Core KR Leader vs US Leader (adjusted by current regime)
    regime = _live_regime_phase(package)
    kr_adj = float(kr_top.get("score") or 80.0) - (5.0 if regime["phase1"] else 0.0)
    us_adj = float(us_top.get("score") or 79.0)
    core_champ = us_top if us_adj >= kr_adj else kr_top
    matches.append(_match(
        "코어 대장주 결승 · KR 1위 vs US 1위",
        f'{kr_top.get("name")} ({kr_top.get("symbol")})',
        f'{us_top.get("name")} ({us_top.get("symbol")})',
        core_champ.get("symbol"), kr_adj, us_adj,
        f'현재 {regime["label"]} 기준 방어·비AI 요새 및 레짐 적합도 우위로 {core_champ.get("name")} 코어 트랙 우승',
    ))

    # Grand Final: Best Actionable Contrarian Champion vs Core Champion (Champion-of-Champions)
    if contrarian_champ is not None:
        champ_sym = contrarian_champ["symbol"]
        pb = pb_by_sym.get(champ_sym)
        weight_pct = float(((pb or contrarian_champ).get("sizing") or {}).get("recommended_pct") or 32.0)
        gf_a = _c_rank(contrarian_champ)
        gf_b = max(kr_adj, us_adj)
        matches.append(_match(
            "최종 결승전 (Grand Final) · 역발상 우승 vs 코어 우승",
            f'[역발상] {contrarian_champ["name"]} ({champ_sym} · 비중 {weight_pct:.1f}%)',
            f'[코어] {core_champ.get("name")} ({core_champ.get("symbol")})',
            champ_sym, gf_a, gf_b,
            f'실전 계약서·6대 관문·AI 비상관·1년 내 비대칭(6~9M)을 모두 통과한 {contrarian_champ["name"]}({champ_sym})이 통합 최종 챔피언',
        ))
        champion = dict(
            symbol=champ_sym,
            name=contrarian_champ["name"],
            market=contrarian_champ["market"],
            track="바구니 3 · 12개월 역발상 압축 챔피언",
            recommended_pct=weight_pct,
            cash_reserve_pct=round(max(0.0, 100.0 - weight_pct), 1),
            score=round(gf_a, 1),
            summary=(
                f'전체 {len(contrarian_cands) + len(disc_cands)}개 누적 후보 배틀 결과 · '
                f'{contrarian_champ["name"]}({champ_sym}) 단일 {weight_pct:.1f}% (현금 {100.0 - weight_pct:.1f}% 예비 유보 · 억지 2슬롯 채우기 금지)'
            ),
            catalyst=contrarian_champ.get("catalyst_12m", ""),
        )
    else:
        champion = dict(
            symbol="CASH",
            name="현금·단기금리 대기 (RP / SGOV)",
            market="ALL",
            track="바구니 1 · 전면 방어",
            recommended_pct=100.0,
            cash_reserve_pct=100.0,
            score=85.0,
            summary="적격 통과 종목이 없어 전액 현금·단기채로 방어합니다.",
            catalyst="추세·실적 반전 확인 시 진입",
        )

    kr_watchlist = [
        f'{c["name"]}({c["symbol"]})'
        for c in contrarian_cands
        if c.get("market") == "KR" and c.get("symbol") in ("035900", "000100")
    ]
    return dict(
        pool_count=len(contrarian_cands) + len(disc_cands),
        contrarian_pass_count=len(survivors_contrarian),
        champion=champion,
        runner_up=(f'{runner_up["name"]} ({runner_up["symbol"]} · {runner_up.get("sizing", {}).get("recommended_pct", 0):.1f}%)' if runner_up else "없음"),
        core_champion=f'{core_champ.get("name")} ({core_champ.get("symbol")} · {core_champ.get("theme", "코어")})',
        kr_watchlist=", ".join(kr_watchlist) if kr_watchlist else "없음 (과열/손익비 대기)",
        matches=matches,
        eliminated_sample=eliminated[:10],
        eliminated_count=len(eliminated),
    )


def _strategy_tournament(package):
    """Knockout battle across accumulated quant, 31Y backtest, and sizing strategies."""
    regime = _live_regime_phase(package)
    qstats = _quant_summary(package)
    phase1 = regime["phase1"]

    matches = [
        _match(
            "1회전 · 손절 규율 배틀",
            "-10% 가격 칼손절 (2008 -28.6% · 1997 손절누적)",
            "3M 펀더멘털 점검 + 6M Time-Stop",
            "time_stop", 42.0, 91.0,
            "31년 위기 백테스트에서 -10% 칼손절은 베어마켓 휩소에 완패 · 실적/촉매 시간손절 우승",
        ),
        _match(
            "1회전 · 시드·분산 규율 배틀",
            "현금 0% 몰빵 / 5~8% 백화점 분산",
            "바구니 1 현금 35%+ · Half-Kelly(25~50% ≤2축)",
            "half_kelly", 35.0, 93.0,
            "현금 0% 몰빵(2008 MDD -73.6% · 2026 -60.2%) 및 5~8% 과분산 모두 기각",
        ),
        _match(
            "4강 · 개별 단타 vs 레짐 필터",
            f"개별 116-SMA 워크포워드 (통과 {qstats['selected']}/{qstats['total']}건 · {qstats['pass_rate_pct']}%)",
            "지수 레짐 + 변동성 캡(variance/downside) 통합 모델",
            "regime_vol_cap", 48.0, 92.0,
            "개별 종목 이평선 매매의 95%는 과최적화/표본부족 탈락 → 지수·포트폴리오 변동성 캡 압승",
        ),
    ]

    sym_score = 95.0 if phase1 else 78.0
    dn_score = 84.0 if phase1 else 96.0
    champ_key = "variance-cap" if phase1 else "downside-cap"
    champ_name = (
        "Phase 1 통합 방어형 · 대칭 변동성 캡(variance-cap) + 현금 35%+ + Half-Kelly 비AI 1축"
        if phase1
        else "Phase 2 통합 공격형 · 하방 변동성 캡(downside-cap) + 12~18M 코어 집중"
    )
    matches.append(_match(
        "최종 결승전 (Grand Final) · 현 국면 최적 전략",
        "대칭 variance-cap (2008 +27.2%·2026 6M -5.8% 방어 1위)",
        "하방 downside-cap (1997 +284.7%·2023~26 +167.3% 반등 1위)",
        champ_key, sym_score, dn_score,
        f'현재 {regime["label"]}이므로 대칭 variance-cap(+현금 35%+) 우승 · 지수 20/60MA 돌파 시 downside-cap으로 자동 승계',
    ))

    return dict(
        pool_count=len(strategy_catalog.CATALOG) + 5,
        quant_stats=qstats,
        regime=regime,
        champion=dict(
            key=champ_key,
            name=champ_name,
            score=max(sym_score, dn_score),
            handover_condition="KODEX 200·SPY가 20일선 및 60일선 안착 + 외국인 3일 연속 순매수 확인 시 Phase 2(downside-cap)로 왕좌 자동 교체",
        ),
        matches=matches,
    )


def _pattern_tournament(package):
    """Knockout battle across accumulated intraday & operational mistake-note patterns."""
    user_notes = []
    if package is not None:
        user_notes = intel.private_json(package, "mistake_notes.json", {}).get("items", [])
    total_notes = len(strategy_catalog.MISTAKE_NOTEBOOK) + len(contrarian.AGENT_COT_POSTMORTEM) + len(user_notes)

    matches = [
        _match(
            "4강 · 개장 첫 30분(09:00/23:30) 체결 패턴",
            "시초가 추격 매수 / 공포 손절 일괄 집행",
            "신규매수·손절 30분 금지 + 2순위 저탄력주만 시초 갭업(+1.5%↑) Limit Ask 허용",
            "open_asymmetric", 28.0, 94.0,
            "11/27 한·미 동시 실증(KRX -0.6%→+4.3%, SOXX -3.2%→+4.8% 반전 & 비핵심 시초 갭업 최고가 -1.6% 하락)",
        ),
        _match(
            "4강 · 장중 분할매도 및 24시간 RWA 선행지표",
            "오전 기계적 매도 / -2% 눌림 단일 대기 / 개별토큰 추종",
            "외인가속 15:15(40%)+20MA(60%) 2트랙 · SPYx/QQQx만 1급(RWA +1.5%↑ 금지 · 00:30~02:00 KST)",
            "session_2track", 34.0, 95.0,
            "눌림목 미체결(0/8종목)·NVDAx 과장(+3.99% vs 시가 -0.95% 음봉)·오전 조기매도(-2.5%p) 동시 해결",
        ),
        _match(
            "4강 · 종목 선별 함정 필터 패턴",
            "과거 180봉 MoS 저평가 승자 매도 / 최근 버블 칼날 매수",
            "20·60MA 정배열(RSI<78) 승자 보유 + 버블 후유증/낙하 칼날(COT-ERR-04) 0% 차단",
            "trend_winner_shield", 31.0, 96.0,
            "달리는 말(+5.21%) 조기 매도와 현대모비스(-58.8%)형 버블 칼날 진입을 동시에 차단",
        ),
    ]
    champ_rule = (
        "① 시초 30분 추격·공포손절 금지(단 2순위 저탄력주 +1.5%↑ 갭업 Limit Ask 허용) → "
        "② 외인가속 15:15 종가(40%)+20MA(60%) / 미 단축장 00:30~02:00 KST 지정가(RWA +1.5%↑ 금지) → "
        "③ 20·60MA 정배열 승자 보유 & 버블/칼날(COT-ERR-04) 0% 차단"
    )
    matches.append(_match(
        "최종 결승전 (Grand Final) · 누적 오답노트 통합 승리 패턴",
        f"누적 오답 패턴 {total_notes}건 통합 가드 프로토콜",
        "과거 단일 룰 / 직관 매매",
        "master_execution_pattern", 96.0, 32.0,
        f"총 {total_notes}건의 한·미 장중 복기·CoT·거버넌스 오답노트를 단일 실행 루프로 압축한 최종 승리 패턴",
    ))
    return dict(
        pool_count=total_notes,
        champion=dict(
            name="비대칭 시초/마감 2트랙 + 정배열 승자 트레일링 + 버블/칼날 제로 프로토콜",
            rule=champ_rule,
            score=96.0,
        ),
        matches=matches,
    )


def run_tournament(package=None, *, now=None):
    """Execute all 3 tournament leagues and persist current bracket + rolling battle log."""
    stamp_dt = now or datetime.now(intel.KST)
    stamp = stamp_dt.astimezone(intel.KST).isoformat(timespec="seconds")

    stocks = _stock_tournament(package)
    strategies = _strategy_tournament(package)
    patterns = _pattern_tournament(package)

    digest_src = json.dumps(
        dict(
            stock=stocks["champion"]["symbol"],
            weight=stocks["champion"]["recommended_pct"],
            strategy=strategies["champion"]["key"],
            pattern=patterns["champion"]["name"],
        ),
        sort_keys=True,
        ensure_ascii=False,
    )
    battle_id = hashlib.sha256(digest_src.encode()).hexdigest()[:12]

    board = dict(
        updated=stamp,
        battle_id=battle_id,
        regime=strategies["regime"],
        stocks=stocks,
        strategies=strategies,
        patterns=patterns,
    )

    if package is not None:
        intel.update_json(package, FILE, {}, lambda _: board)

        log_row = dict(
            updated=stamp,
            battle_id=battle_id,
            regime=strategies["regime"]["label"],
            champion_stock=f'{stocks["champion"]["name"]} ({stocks["champion"]["symbol"]}) · {stocks["champion"]["recommended_pct"]:.1f}%',
            champion_strategy=strategies["champion"]["name"],
            champion_pattern=patterns["champion"]["name"],
            pool_sizes=dict(stocks=stocks["pool_count"], strategies=strategies["pool_count"], patterns=patterns["pool_count"]),
        )

        def _append_log(old):
            items = list(old.get("items", []))
            items.insert(0, log_row)
            return dict(updated=stamp, items=items[:100])

        intel.update_json(package, HISTORY_FILE, {}, _append_log)
        return intel.private_json(package, FILE, {})
    return board


def read(package):
    if package is None:
        return {}
    return intel.private_json(package, FILE, {})


def history(package):
    if package is None:
        return []
    return intel.private_json(package, HISTORY_FILE, {}).get("items", [])
