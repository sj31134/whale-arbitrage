"""Public contrarian variant-perception scanner and 1-stock bespoke asymmetric strategy engine.
Never accepts personal portfolio holdings in public collection."""

from datetime import datetime
from decimal import Decimal
import hashlib
import ipaddress
import json
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from agents import intelligence as intel
from . import live_valuation, price_history

FILE = "contrarian_radar.json"
PLAYBOOK_FILE = "contrarian_playbooks.json"

ARCHETYPES = {
    "calm_compounder": dict(
        id="calm_compounder",
        badge="이호걸형 · 구조적 복리 괴리",
        master="캄투자일임 이호걸 대표 아키타입 (질의 ‘김호걸’ → 공시 대표명 이호걸)",
        track_record="2023.03 자본금 17억 원 설립 → 차입 없이 고유재산 상장주식 Long-Only 초집중 복리 재투자로 2026 상반기 자기자본 4,467억 원(반기 순이익 3,303억 원) 달성",
        core_quote="“관세·금리 같은 매크로 변수에 질 회사는 애초에 사지 않는다. 주식이 아니라 흔들리지 않는 사업의 가치를 통째로 소유한다.”",
        crowd_blindspot="대중은 금리·관세·내수 둔화 등 거시경제 공포나 ‘전통 업종 선입견’에 갇혀 글로벌 가격결정력과 수출 영업레버리지 폭발을 과소평가함",
        edge_formula="확실한 가격결정력(ROIC > WACC) + 해외 확장성 보유 1등 기업을 매크로 급락기에 무차입 현물 Long-Only로 집중 매수 후 18~36개월 복리 동행",
        execution_rule="2~3회 분할 매집 · 차트/매크로 노이즈 무손절(평정심 유지) · 오직 제품 가격결정력 또는 해외 확장률 훼손 공시 때만 철회",
        min_asymmetry=3.5,
        horizon="18~36개월",
        sources=(
            ("캄투자일임 자기자본·운용 구조 보도 (딜사이트)", "https://dealsite.co.kr/"),
            ("한국경제·매일경제 집중투자 인터뷰 요약", "https://www.hankyung.com/"),
        ),
    ),
    "hynix_bottleneck": dict(
        id="hynix_bottleneck",
        badge="하이닉스형 · 적자 착시·병목 선점",
        master="SK하이닉스 적자 바닥 선제 집중 아키타입 (사용자 지칭 ‘한유백’ 유형 · 실명 공시 미특정 단서 명시)",
        track_record="2022.11~2023년 SK하이닉스 연간 7.7조 원 영업적자·비관론 극점(75,000원, PBR ~0.9배)에서 HBM 독점 병목을 선점해 최고 +3,433%(현재 +1,380%) 리레이팅 포착",
        core_quote="“다수결 통계는 백미러(지난 분기 적자·역배열 차트)를 보고 팔지만, 선구자는 앞유리(대체 불가능한 물리적 병목 독점)를 보고 공포의 바닥에서 모은다.”",
        crowd_blindspot="레거시 사업부 적자(과거 껍데기 V_Shell)에 가려 차세대 패러다임 필수 병목재(V_Core, 공급 비탄력성 E_s ≈ 0)의 독점 수주와 가격 폭등을 보지 못함",
        edge_formula="역사적 PBR·밸류 하단 + 차세대 설비(CapEx)/수주 독점 확인 시 대중보다 2~3분기 앞서 시간분할 선점(Time-Horizon Arbitrage)",
        execution_rule="역배열 구간 3~4회 시간분할 매집(기계적 -10% 손절 금지) · 병목 쇼티지 현실화 및 대중 만장일치 환호(RSI > 78·고멀티플) 구간에서 수확",
        min_asymmetry=4.0,
        horizon="12~24개월",
        sources=(
            ("SK하이닉스 IR · HBM 및 중장기 설비투자 공시", "https://www.skhynix.com/"),
            ("금융감독원 DART 정기공시 원문", "https://dart.fss.or.kr/"),
        ),
    ),
    "burry_asymmetry": dict(
        id="burry_asymmetry",
        badge="마이클 버리형 · 딥밸류·비대칭 사냥",
        master="마이클 버리 (Michael Burry · Scion Asset Management)",
        track_record="그레이엄식 100% 안전마진 원칙 + 패시브·알고리즘 투매가 만든 버려진 자산(Roadkill) 초집중 및 하방 고정·상방 5~20배 비대칭 볼록성(Convexity) 베팅",
        core_quote="“나는 군중이 혐오하며 길가에 버린 자산(Roadkill)에서 사냥한다. 잃을 때는 적게 잃도록 바닥을 잠그고, 맞을 때는 5~10배 터지는 비대칭 구조만 짠다.”",
        crowd_blindspot="패시브 지수·변동성 타겟팅(Vol-Targeting)·신용 반대매매가 기업의 순현금·잉여현금흐름(FCF)·대체원가와 무관하게 주가를 청산가치 수준으로 짓누름",
        edge_formula="52주 고점 대비 -35%~-60% 강제투매 + 순현금/FCF 생존력 검증 종목에 하방 방어선을 잠그고 비대칭 손익배수(≥5.0배) 스나이퍼 베팅",
        execution_rule="청산가치·역사적 지지선 부근 지정가 매복 · 내재가치 평균회귀(+50%~+150%) 달성 즉시 미련 없이 전량 회수해 다음 괴리로 자본 회전",
        min_asymmetry=5.0,
        horizon="6~18개월",
        sources=(
            ("SEC EDGAR Scion Asset Management 13F 원문", "https://www.sec.gov/edgar/searchedgar/companysearch"),
            ("Moreira & Muir 변동성 강제청산 미시구조 연구", "https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf"),
        ),
    ),
}

# Empirically verified 5-year historical inflection cases vs Value Traps (2021-12 ~ 2026-11 public Yahoo/KRX data)
VALIDATION_MATRIX = dict(
    summary=(
        "다수결 모멘텀 전략(/discover)은 20·60일선 돌파와 외국인 순매수가 확인된 뒤 진입하므로 승률은 안정적이나 바닥 대비 +40%~+80% 오른 뒤 탑승합니다. "
        "반면 3대 대가형 역발상 전략은 대중이 외면한 역배열·적자·투매 바닥에서 선점해 6~35배 비대칭 수익을 거두었으나, "
        "‘생존력·독점 병목 필터’ 없이 단순 낙폭과대만 사면 가치함정(카카오·Intel형 장기 소외)에 빠진다는 점이 실증적으로 검증되었습니다."
    ),
    cases=(
        dict(
            name="SK하이닉스 (000660)",
            archetype="하이닉스형 · 병목 선점",
            verdict="성공 · 14.8배 (최고 35.3배)",
            trough="2022-11 · 75,000원 (적자 공포 · 역배열)",
            peak_or_now="최고 2,650,000원 (+3,433%) · 현재 1,110,000원 (+1,380%)",
            crowd_then="범용 D램 가격 폭락과 연간 7.7조 적자 전망으로 기관·다수결 점수 최하위",
            variant_edge="AI 가속기 필수재 HBM3/TSV 물리적 공급 병목(E_s≈0) 독점 점유율 선점",
        ),
        dict(
            name="삼양식품 (003230)",
            archetype="이호걸형 · 구조적 복리",
            verdict="성공 · 15.4배 (최고 18.5배)",
            trough="2021-12 · 84,800원 (내수 식품 저멀티플 소외)",
            peak_or_now="최고 1,566,000원 (+1,747%) · 현재 1,303,000원 (+1,437%)",
            crowd_then="원맥 가격 상승 우려와 ‘일시적 매운맛 유행’ 편견으로 PER 8~10배 정체",
            variant_edge="미국·중국·유럽 주류 유통망 진입 + 밀양 수출전용 공장 영업레버리지 폭발",
        ),
        dict(
            name="HD현대일렉트릭 (267260)",
            archetype="하이닉스형 · 병목 선점",
            verdict="성공 · 24.0배 (최고 71.7배)",
            trough="2021-12 · 17,450원 (과거 중공업 구조조정 선입견)",
            peak_or_now="최고 1,252,000원 (+7,075%) · 현재 418,500원 (+2,298%)",
            crowd_then="전통 굴뚝 산업 저성장 편견으로 시장 무관심",
            variant_edge="북미 노후 전력망 교체 + AI 데이터센터 초고압 변압기 3~4년치 수주 병목 독식",
        ),
        dict(
            name="Meta Platforms (META)",
            archetype="마이클 버리·이호걸 결합형",
            verdict="성공 · 6.5배 (최고 8.3배)",
            trough="2022-10 · $93.16 (고점 대비 -76% 군중 조롱 투매)",
            peak_or_now="최고 $773.44 (+730%) · 현재 $609.89 (+555%)",
            crowd_then="메타버스 설비투자 과잉 비난 속 패시브·기관 투매로 FCF 대비 청산급 할인",
            variant_edge="30억 일간 활성사용자 독점 네트워크 건재 + 비용 효율화 선언 즉시 FCF 폭발",
        ),
        dict(
            name="카카오 (035720) · [반증: 가치함정]",
            archetype="함정 경보 · 해자 미충족",
            verdict="실패(함정) · 바닥 후 +5.4% 정체",
            trough="4년 연속 하락 후 2026-09 · 29,450원",
            peak_or_now="현재 31,050원 (+5.4% · 장기 기회비용 발생)",
            crowd_then="‘많이 빠졌으니 싸다’는 개인 저가매수 유입",
            variant_edge="반증 교훈: 물리적 병목·글로벌 가격결정력 없이 자회사 중복상장으로 가치가 희석되는 종목은 싸 보여도 1종목 집중 금지!",
        ),
    ),
    comparison=(
        ("진입 시점의 시장 풍경", "외인·기관 매수 + 20·60일선 정배열 확인 후 (다수 동의)", "적자·매크로 공포·알고리즘 투매로 60일선 아래 소외 (소수 독점 인사이트)"),
        ("핵심 수익 원천", "추세 지속 구간 모멘텀 탑승 (+25%~+80%)", "시선 괴리 해소 + 이익·멀티플 동시 폭발 리레이팅 (+100%~+1,000%+)"),
        ("가장 치명적인 위험", "고점 추격 후 되돌림 손실 (과열 추격 위험)", "해자 없는 한계기업을 싸다고 사는 ‘가치함정(Value Trap)’"),
        ("손절·방어 메커니즘", "20일선 이탈·변동성 캡 비중 축소", "진입 전 ‘생존·병목 3대 하드게이트’ 심사 + 시간분할 매집 + 본질 훼손 공시만 철회"),
    ),
)

# Credit / Balance-Sheet Solvency Tiers for High-Rate Regime (BOK 3.25% / US 10Y 4.85% — Bank Credit Risk VOC)
SOLVENCY_TIERS = {
    "net_cash": dict(
        label="A등급 · 순현금·초우량 FCF 요새 (이자보상 ≥10배 · 차환위험 없음)",
        cap_pct=10.0,
        ok=True,
    ),
    "backlog_float": dict(
        label="A-등급 · 장기 수주 선수금(Float)·영업흑자 건전 (이자보상 ≥4배)",
        cap_pct=8.0,
        ok=True,
    ),
    "turnaround_watch": dict(
        label="B등급 · 설비투자·차입 점검 (단기차환 커버리지·유증 부재 확인 필수)",
        cap_pct=5.0,
        ok=True,
    ),
    "distressed_block": dict(
        label="부적격 · 이자보상 <2배 또는 유상증자·CB 희석 위험 (1종목 집중 차단)",
        cap_pct=0.0,
        ok=False,
    ),
}

CREDIT_PROFILES = {
    "005935": ("net_cash", "순현금 90조+ · 무차입급 재무요새 · 자사주 소각 밸류업 수혜"),
    "005930": ("net_cash", "순현금 90조+ · 글로벌 최대 영업현금흐름으로 설비투자 자체 조달"),
    "000660": ("backlog_float", "HBM 선급금 유입 및 분기 수조 원대 FCF로 차입비율 급감 중"),
    "267260": ("backlog_float", "북미 유틸리티 장기 수주 계약금(선수금 Float) 유입 · 순현금 전환"),
    "003230": ("net_cash", "해외 고마진 현금 결제 회수로 차입 부담 극소 · ROE 30%+"),
    "012450": ("backlog_float", "수출 계약 선수금 유입 기반 영업현금흐름 흑자 (해외 자회사 지원 공시만 점검)"),
    "138040": ("backlog_float", "자본적정성 비율 준수 및 순이익 50%+ 자사주 소각 지속 (부동산 PF 충당금 분기 점검)"),
    "010120": ("backlog_float", "우량 신용등급(AA급) 및 북미 배전·변압기 수주 현금흐름 안정"),
    "196170": ("turnaround_watch", "빅파마 마일스톤·로열티 유입 구조이나 바이오 특성상 분기 현금흐름·전환증권 희석 점검 필수"),
    "034020": ("turnaround_watch", "원전·가스터빈 수주 확대 중이나 과거 차입 구조 이력상 이자보상배율·차환 조건 분기 확인 필수"),
    "NVDA": ("net_cash", "막대한 순현금 및 분기 수십억 달러 FCF · 자사주 매입 지속"),
    "MU": ("backlog_float", "AI 메모리 현금흐름 회복 및 CHIPS 보조금 유입으로 재무 완충력 양호"),
    "ASML": ("net_cash", "고객사 선수금(Float) 및 독점 마진 기반 순현금·자사주 소각 구조"),
    "GOOG": ("net_cash", "1,000억 달러급 현금성 자산 보유 · 압도적 검색·클라우드 FCF"),
    "MSFT": ("net_cash", "AAA 신용등급(미국 국채급) · 엔터프라이즈 구독 잉여현금흐름 요새"),
    "CEG": ("backlog_float", "미 IRA 45U 원전 세액공제 바닥가격 보장 및 투자적격 신용등급 유지"),
    "AVGO": ("backlog_float", "인수 차입금 보유하나 VMware+AI 고마진 FCF로 빠른 디레버리징 진행"),
    "TSM": ("net_cash", "대규모 순현금 보유 및 빅테크 선단공정 선수금 유입"),
    "LLY": ("backlog_float", "GLP-1 고마진 현금 창출로 증설 CapEx 및 차입 이자 충분히 상회"),
    "AMZN": ("net_cash", "AWS+광고 영업현금흐름 급증으로 설비투자 자체 조달 충분"),
}


def compute_position_sizing(*, upside_pct, downside_pct, win_prob=0.55, risk_budget_pct=1.2, cap_pct=10.0, blocked=False):
    """Fractional-Kelly (1/4 Kelly) + 1R Portfolio Risk-Budget position sizing (Hedge Fund & Pro Trader VOC)."""
    if blocked or cap_pct <= 0 or upside_pct <= 0 or downside_pct <= 0:
        return dict(kelly_quarter_pct=0.0, r_budget_pct=0.0, cap_pct=max(0.0, cap_pct), recommended_pct=0.0)
    p = _clamp(float(win_prob), 0.20, 0.85)
    q = 1.0 - p
    u = max(float(upside_pct) / 100.0, 0.01)
    d = max(float(downside_pct) / 100.0, 0.02)
    # Continuous partial-loss Kelly fraction: f* = p/d - (1-p)/u, scaled by 0.25 (Quarter-Kelly)
    full_kelly = max(0.0, (p / d) - (q / u))
    kelly_q_pct = round(_clamp(0.25 * full_kelly * 100.0, 0.0, 25.0), 1)
    # 3-tranche weighted average entry (30% @ 0, 40% @ -45% of span, 30% @ -85% of span) -> avg distance to floor is 56.5% of downside_pct
    avg_stop_pct = max(2.5, float(downside_pct) * 0.565 + 0.8)  # +0.8% execution/gap slippage buffer
    r_bgt = _clamp(float(risk_budget_pct), 0.3, 3.0)
    r_weight_pct = round((r_bgt / avg_stop_pct) * 100.0, 1)
    rec = round(min(kelly_q_pct, r_weight_pct, float(cap_pct)), 1)
    return dict(
        kelly_quarter_pct=kelly_q_pct,
        r_budget_pct=r_weight_pct,
        cap_pct=round(float(cap_pct), 1),
        recommended_pct=rec,
    )


def _monotonic_tranches(entry_val, floor_val, rnd):
    """Guarantee strictly decreasing 3-tranche prices: entry (30%) > t2 (40%) > t3 (30%) >= floor."""
    span = max(0.0, float(entry_val) - float(floor_val))
    t1 = rnd(float(entry_val))
    t2 = rnd(float(entry_val) - span * 0.45)
    t3 = rnd(float(entry_val) - span * 0.85)
    return [t1, t2, t3]


# Public Structural Moat Universe for Variant-Perception Dislocation Scanning (Zero portfolio input!)
# (symbol, market, venue, currency, name, archetype, essence_score[0..35], moat_essence, crowd_fear, kill_switch)
CONTRARIAN_UNIVERSE = (
    ("005935", "KR", "KRX", "KRW", "삼성전자우", "burry_asymmetry", 32,
     "100조 원대 순현금 하방 방어막 + KOSPI200 프로그램 바스켓 매도 면제 + 배당·밸류업 우선주 할인 괴리",
     "범용 메모리 단가 우려 및 반도체 업황 피크아웃 공포로 역사적 PBR 하단 압축",
     "순현금 급감 또는 첨단 메모리 설비 경쟁력 영구 상실 공시"),
    ("005930", "KR", "KRX", "KRW", "삼성전자", "hynix_bottleneck", 31,
     "글로벌 최대 메모리 캐파·순현금 요새 및 차세대 HBM4·턴키 파운드리 재진입 옵션",
     "단기 HBM 점유율 열위 부각으로 대체원가(PBR 1배 전후) 수준까지 과도한 비관 반영",
     "차세대 HBM4 주요 빅테크 퀄 테스트 최종 무산 공시"),
    ("000660", "KR", "KRX", "KRW", "SK하이닉스", "hynix_bottleneck", 34,
     "AI 가속기 필수 병목재 HBM3E·HBM4 압도적 수율·점유율 1위 및 장기 공급계약(LTA) 해자",
     "AI 설비투자 피크아웃 논란 및 미국 관세·반도체 단기 조정 공포에 따른 멀티플 압축",
     "빅테크 AI 서버 CapEx 전년 대비 역성장 전환 또는 HBM 독점 점유율 붕괴"),
    ("267260", "KR", "KRX", "KRW", "HD현대일렉트릭", "hynix_bottleneck", 33,
     "북미 초고압 변압기(500kV+) 공급 비탄력성(리드타임 3년+)과 수주잔고 이익 가시성",
     "고점 대비 가격 조정 및 북미 관세 노이즈로 단기 투심 위축",
     "북미 유틸리티 초고압 변압기 신규 수주 단가 하락 전환"),
    ("003230", "KR", "KRX", "KRW", "삼양식품", "calm_compounder", 33,
     "글로벌 K푸드 독점 브랜드 가격결정력 + 해외 법인 직판 고마진 및 수출전용 공장 증설 복리",
     "단기 급등 피로감 및 수출 성장률 둔화 우려에 따른 조정",
     "북미·중국·유럽 분기 수출 물량 2분기 연속 역성장 공시"),
    ("012450", "KR", "KRX", "KRW", "한화에어로스페이스", "calm_compounder", 33,
     "유럽·중동 지상방산 자주포·다연장 독점 납기 경쟁력 및 탄약 반복 매출 구조",
     "종전 협상 헤드라인 노이즈 때마다 반복되는 방산 피크아웃 오해",
     "주요국 국방예산 감축 또는 핵심 수출 계약 해지 공시"),
    ("138040", "KR", "KRX", "KRW", "메리츠금융지주", "calm_compounder", 31,
     "순이익 50%+ 자사주 매입·소각을 기계적으로 집행하는 주당가치 복리 엔진",
     "금리·부동산 PF 막연한 우려로 주주환원 수익률 대비 저평가",
     "주주환원율 50% 원칙 철회 또는 대규모 PF 부실 현실화"),
    ("010120", "KR", "KRX", "KRW", "LS일렉트릭", "hynix_bottleneck", 30,
     "북미 AI 데이터센터 배전반·초고압 변압기 병목 낙수효과(Spillover) 수혜",
     "국내 설비투자 둔화 우려에 가려 북미 데이터센터 직납 성장성 과소평가",
     "북미 빅테크향 배전·변압기 수주 취소 또는 지연"),
    ("196170", "KR", "KRX", "KRW", "알테오젠", "calm_compounder", 30,
     "글로벌 빅파마 블록버스터 의약품 피하주사(SC) 전환 원천 플랫폼 로열티 해자",
     "바이오 섹터 금리 민감도 및 특허·임상 루머에 따른 극심한 주가 진동",
     "핵심 빅파마 파트너십 해지 또는 상업화 품목허가 거절"),
    ("034020", "KR", "KRX", "KRW", "두산에너빌리티", "hynix_bottleneck", 29,
     "대형 원전·SMR 주단조 파운드리 및 데이터센터용 가스터빈 글로벌 소수 과점",
     "원전 정책 일정 지연 우려 및 과거 중공업 차입 선입견",
     "글로벌 원전·가스터빈 핵심 수주 무산 또는 재무구조 재악화"),
    ("NVDA", "US", "NASDAQ", "USD", "NVIDIA", "calm_compounder", 35,
     "CUDA 소프트웨어 생태계 락인과 AI 데이터센터 가속기·네트워킹 절대 독점 병목",
     "빅테크 자체 칩(ASIC) 대체설 및 단기 마진율 피크아웃 공포로 고점 대비 큰 폭 조정",
     "주요 하이퍼스케일러 AI CapEx 삭감 또는 CUDA 생태계 이탈 확인"),
    ("MU", "US", "NASDAQ", "USD", "Micron Technology", "hynix_bottleneck", 31,
     "미국 유일 첨단 HBM·D램 제조사로 AI 서버 메모리 탑재량 급증 직접 수혜",
     "PC·스마트폰 레거시 재고 조정 우려로 52주 고점 대비 반토막 수준 투매",
     "HBM 수율 차질 또는 분기 영업현금흐름 적자 전환"),
    ("ASML", "US", "NASDAQ", "USD", "ASML", "calm_compounder", 35,
     "첨단 반도체 미세공정 필수 EUV·High-NA 노광장비 전 세계 100% 단독 독점",
     "대중국 수출통제 우려 및 파운드리 고객사 단기 발주 이연 노이즈",
     "첨단 공정 노광 기술 대체재 출현 또는 장기 수주잔고 급감"),
    ("GOOG", "US", "NASDAQ", "USD", "Alphabet", "burry_asymmetry", 33,
     "글로벌 검색·유튜브 압도적 현금흐름 + 자체 TPU·클라우드 마진 개선 + 빅테크 최저 수준 멀티플",
     "법무부 반독점 소송 해체 공포 및 AI 검색 잠식 과장 우려로 빅테크 중 가장 큰 밸류 할인",
     "검색 광고 핵심 현금흐름 구조적 감소 또는 강제 분할에 따른 시너지 파괴"),
    ("MSFT", "US", "NASDAQ", "USD", "Microsoft", "calm_compounder", 34,
     "전 세계 기업용 OS·클라우드(Azure) 높은 전환비용(Walled Garden)과 잉여현금흐름 요새",
     "단기 AI 인프라 감가상각 부담 부각으로 RSI 30 근접 과매도 구간 진입",
     "Azure 클라우드 성장률 구조적 둔화 및 기업 고객 이탈"),
    ("CEG", "US", "NASDAQ", "USD", "Constellation Energy", "hynix_bottleneck", 32,
     "미국 최대 무탄소 원전 발전 용량 보유 · 빅테크 24/7 AI 데이터센터 장기 전력구매계약(PPA) 병목",
     "전력 직접계약 규제 심사 노이즈로 단기 급락 조정",
     "원전 데이터센터 전력공급 계약 전면 불허 또는 원전 가동 중단"),
    ("AVGO", "US", "NASDAQ", "USD", "Broadcom", "calm_compounder", 33,
     "빅테크 맞춤형 AI ASIC 칩 + 데이터센터 이더넷 네트워킹 + VMware 고마진 현금흐름 결합",
     "반도체 업종 일괄 패시브 매도에 따른 동반 조정",
     "주요 클라우드 고객사 커스텀 ASIC 발주 이탈"),
    ("TSM", "US", "NYSE", "USD", "TSMC", "hynix_bottleneck", 34,
     "전 세계 AI 칩·선단 2nm/3nm 공정 및 CoWoS 패키징 90%+ 물리적 독점 파운드리",
     "대만 해협 지정학 할인 및 관세 헤드라인 공포로 독점력 대비 영구 멀티플 할인",
     "대만 해협 물리적 봉쇄·충돌 또는 선단 공정 독점력 상실"),
    ("LLY", "US", "NYSE", "USD", "Eli Lilly", "calm_compounder", 33,
     "GLP-1 비만·대사질환 치료제 특허·생산설비 진입장벽 및 경구용 차세대 파이프라인",
     "약가 인하 정치적 발언 및 분기 유통재고 노이즈에 따른 조정",
     "핵심 파이프라인 중대 부작용 또는 특허 조기 무효화"),
    ("AMZN", "US", "NASDAQ", "USD", "Amazon", "calm_compounder", 32,
     "AWS 클라우드 AI 인프라 + 북미 물류 로봇 자동화·고마진 광고 사업의 영업이익률 구조적 도약",
     "소비 둔화 우려와 대규모 물류·AI 설비투자(CapEx) 부담 선입견",
     "AWS 점유율 급락 또는 북미 커머스 영업이익률 재차 악화"),
)


def _default_get(url):
    req = Request(url, headers={"User-Agent": "whale-tracking/1.0 local contrarian research"})
    with urlopen(req, timeout=7) as resp:
        return resp.read(2_000_000)


def _clamp(val, lo, hi):
    return max(lo, min(hi, val))


def _yahoo_1y(symbol, market, get_bytes):
    yh_sym = f"{symbol}.KS" if market == "KR" else symbol
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yh_sym}?range=1y&interval=1d"
    doc = json.loads(get_bytes(url).decode("utf-8", errors="replace"))["chart"]["result"][0]
    q = doc["indicators"]["quote"][0]
    closes = [float(c) for c in q.get("close", ()) if c is not None and c > 0]
    return closes


def _score_candidate(spec, db_bars, cur_price):
    sym, market, venue, ccy, name, arch_id, essence, moat_txt, fear_txt, kill_txt = spec
    closes = list(db_bars)
    if cur_price and cur_price > 0 and (not closes or abs(cur_price - closes[-1]) / closes[-1] > 1e-5):
        closes.append(float(cur_price))
    if len(closes) < 25:
        return None
    cur = closes[-1]
    window_1y = closes[-252:] if len(closes) >= 252 else closes
    high52 = max(window_1y)
    low52 = min(window_1y)
    dd52 = (cur / high52 - 1) * 100  # negative %
    ma20 = sum(closes[-20:]) / 20
    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20
    pct20 = (cur / ma20 - 1) * 100
    pct60 = (cur / ma60 - 1) * 100
    diffs = [b - a for a, b in zip(closes[-15:], closes[-14:])]
    up = sum(d for d in diffs if d > 0) / 14
    dn = sum(-d for d in diffs if d < 0) / 14
    rsi = 100.0 if dn == 0 else 100.0 - (100.0 / (1.0 + up / dn))

    # Axis 2: Crowd Neglect & Price Dislocation Score (0..35) — OPPOSITE of momentum consensus!
    gap_pts = 8.0
    drop = -dd52
    if 25 <= drop <= 58:
        gap_pts += 15.0  # Prime Burry / Hynix contrarian dislocation zone!
    elif 15 <= drop < 25:
        gap_pts += 10.0
    elif drop > 58:
        gap_pts += 11.0  # Extreme crash — rely on essence gate to block value traps
    elif drop < 8:
        gap_pts -= 4.0   # Already near 52w high — crowd already agrees!

    if pct60 < -10:
        gap_pts += 7.0   # Below 60D MA -> CTA/algo mechanical selling discount
    elif pct60 < 0:
        gap_pts += 4.0
    elif pct60 > 15:
        gap_pts -= 3.0

    if rsi <= 35:
        gap_pts += 5.0   # Deep fear / capitulation
    elif rsi <= 48:
        gap_pts += 3.0
    elif rsi >= 72:
        gap_pts -= 5.0   # Crowd euphoria
    gap_score = round(_clamp(gap_pts, 2.0, 35.0), 1)

    # Structural Floor & Intrinsic Recovery Target for 1-Stock Bespoke Plan
    sorted_1y = sorted(window_1y)
    p10_floor = sorted_1y[max(0, int(0.08 * (len(sorted_1y) - 1)))]
    floor_px = min(cur * 0.88, max(low52 * 0.96, min(cur * 0.90, p10_floor)))
    # Intrinsic recovery value: structural 85th percentile / prior peak recovery anchored by moat essence
    p85_val = sorted_1y[int(0.85 * (len(sorted_1y) - 1))]
    target_px = max(cur * 1.28, p85_val, high52 * 0.92)
    bull_px = max(target_px * 1.20, high52 * 1.12)

    downside_pct = max(4.0, (1.0 - floor_px / cur) * 100)
    upside_pct = (target_px / cur - 1.0) * 100
    asymmetry_ratio = round(upside_pct / downside_pct, 2)
    margin_pct = round((1.0 - cur / target_px) * 100, 1)

    # Axis 3: Asymmetric Convexity Score (0..30)
    asym_pts = _clamp(asymmetry_ratio * 4.8, 3.0, 30.0)
    asym_score = round(asym_pts, 1)

    variant_total = round(essence + gap_score + asym_score, 1)
    arch = ARCHETYPES[arch_id]

    # Bespoke 3-tranche contrarian accumulation schedule (strictly decreasing: t1 > t2 > t3 >= floor)
    rnd = (lambda v: round(v)) if ccy == "KRW" else (lambda v: round(v, 2))
    buy_1, buy_2, buy_3 = _monotonic_tranches(cur, floor_px, rnd)
    floor_r = rnd(floor_px)
    target_r = rnd(target_px)
    bull_r = rnd(bull_px)

    solv_key, solv_note = CREDIT_PROFILES.get(sym, ("backlog_float", "영업현금흐름 및 이자보상배율 분기 공시 확인"))
    solv_meta = SOLVENCY_TIERS[solv_key]
    overheated = bool(rsi >= 68.0 or dd52 > -10.0)
    shield_ok = bool(
        not overheated
        and solv_meta["ok"]
        and essence >= 28
        and asymmetry_ratio >= 3.0
        and margin_pct >= 20.0
    )
    sizing = compute_position_sizing(
        upside_pct=upside_pct,
        downside_pct=downside_pct,
        win_prob=0.55,
        risk_budget_pct=1.2,
        cap_pct=solv_meta["cap_pct"],
        blocked=overheated or not solv_meta["ok"],
    )
    live_fear = (
        f"[현재 단기 강세·군중 동의 구간 (52주고점 대비 {dd52:+.1f}% · RSI {rsi:.0f}) — 지금 역발상 추격 매수 잠금, 조정 대기 또는 /discover 추세 규칙 적용] {fear_txt}"
        if overheated
        else fear_txt
    )

    src_url = (
        f"https://m.stock.naver.com/domestic/stock/{sym}/total"
        if market == "KR"
        else f"https://stockanalysis.com/stocks/{sym.lower()}/"
    )
    return dict(
        symbol=sym,
        market=market,
        venue=venue,
        currency=ccy,
        name=name,
        archetype=arch_id,
        archetype_badge=arch["badge"],
        horizon=arch["horizon"],
        price=rnd(cur),
        high52=rnd(high52),
        dd52=round(dd52, 1),
        pct20=round(pct20, 1),
        pct60=round(pct60, 1),
        rsi=round(rsi, 1),
        floor_price=floor_r,
        target_price=target_r,
        bull_price=bull_r,
        upside_pct=round(upside_pct, 1),
        downside_pct=round(downside_pct, 1),
        asymmetry=asymmetry_ratio,
        margin_pct=margin_pct,
        tranches=[buy_1, buy_2, buy_3],
        scores=dict(essence=essence, gap=gap_score, asymmetry=asym_score),
        total=variant_total,
        overheated=overheated,
        solvency_tier=solv_key,
        solvency_label=solv_meta["label"],
        solvency_note=solv_note,
        sizing=sizing,
        trap_shield_ok=shield_ok,
        moat_essence=moat_txt,
        crowd_fear=live_fear,
        execution_rule=arch["execution_rule"],
        kill_switch=kill_txt,
        source_url=src_url,
    )


def refresh(package, *, fetcher=None, now=None):
    """Scan public moat universe for Variant-Perception Dislocation. Zero portfolio input."""
    get_bytes = fetcher or _default_get
    stamp_dt = now or datetime.now(intel.KST)
    stamp = stamp_dt.astimezone(intel.KST).isoformat(timespec="seconds")

    qb = live_valuation.read(package)
    db_series = {}
    with live_valuation.connection(package) as db:
        has_bars = bool(db and db.execute("SELECT 1 FROM sqlite_master WHERE name='price_bar'").fetchone())
        if has_bars:
            for spec in CONTRARIAN_UNIVERSE:
                sym, _, venue, ccy = spec[:4]
                rows, _ = price_history.series(db, (venue, sym, ccy), long=True)
                if not rows:
                    rows, _ = price_history.series(db, (venue, sym, ccy))
                db_series[sym] = [float(r["closing"]) for r in rows[-260:] if float(r["closing"]) > 0]

    candidates = []
    for spec in CONTRARIAN_UNIVERSE:
        sym, market, venue, ccy = spec[:4]
        tag = f"stock:{market}:{sym}"
        q = qb.match("kis", sym, ccy, (tag,))
        cur_px = float(q["price"]) if q else None
        bars = db_series.get(sym, [])
        if len(bars) < 60:
            try:
                bars = _yahoo_1y(sym, market, get_bytes)
            except Exception:
                pass
        if cur_px is None and bars:
            cur_px = bars[-1]
        scored = _score_candidate(spec, bars, cur_px)
        if scored is not None:
            candidates.append(scored)

    candidates.sort(key=lambda r: (-r["total"], -r["asymmetry"], r["symbol"]))
    doc = dict(updated=stamp, count=len(candidates), candidates=candidates)
    if package is not None:
        intel.update_json(package, FILE, {}, lambda _: doc)
        return intel.private_json(package, FILE, {})
    return doc


def read(package):
    if package is None:
        return {}
    return intel.private_json(package, FILE, {})


def save_playbook(package, fields):
    """Validate and save a bespoke 1-Stock Contrarian Asymmetric Playbook locally."""
    market = str(fields.get("market", "KR")).strip().upper()
    symbol = str(fields.get("symbol", "")).strip().upper()
    name = str(fields.get("name", "")).strip() or symbol
    archetype = str(fields.get("archetype", "calm_compounder")).strip()
    crowd_view = str(fields.get("crowd_view", "")).strip()
    variant_insight = str(fields.get("variant_insight", "")).strip()
    kill_switch = str(fields.get("kill_switch", "")).strip()
    horizon = str(fields.get("horizon", "18~24개월")).strip()[:40]
    url = str(fields.get("url", "")).strip()

    if market not in ("KR", "US") or not re.fullmatch(r"[A-Z0-9.\-]{1,12}", symbol):
        raise ValueError("시장(KR/US)과 종목코드·티커 형식을 확인하세요.")
    if archetype not in ARCHETYPES:
        raise ValueError("역발상 전략 아키타입을 선택하세요.")
    if not (0 < len(name) <= 80 and 0 < len(crowd_view) <= 300 and 0 < len(variant_insight) <= 400 and 0 < len(kill_switch) <= 300):
        raise ValueError("대중의 시선·나만의 독점 인사이트·가설 철회 조건을 모두 입력하세요.")

    try:
        entry = Decimal(str(fields.get("entry", "")).strip())
        floor = Decimal(str(fields.get("floor", "")).strip())
        target = Decimal(str(fields.get("target", "")).strip())
    except Exception as exc:
        raise ValueError("기준가·하방 바닥가·목표 가치를 숫자로 입력하세요.") from exc
    if not (Decimal(0) < floor < entry < target):
        raise ValueError("하방 바닥가 < 현재 진입 기준가 < 본질 복원 목표가 순서를 확인하세요.")

    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("핵심 근거의 공개 HTTPS 원문 URL을 입력하세요.")
    host = parsed.hostname.rstrip(".").lower()
    try:
        private = not ipaddress.ip_address(host).is_global
    except ValueError:
        private = "." not in host or host.endswith((".localhost", ".local", ".internal"))
    if private:
        raise ValueError("공개 인터넷 원문 URL을 입력하세요.")

    solvency = str(fields.get("solvency", "")).strip() or CREDIT_PROFILES.get(symbol, ("backlog_float", ""))[0]
    if solvency not in SOLVENCY_TIERS:
        raise ValueError("여신심사 재무생존 등급을 확인하세요.")
    try:
        win_prob_pct = float(str(fields.get("win_prob", "55")).strip() or "55")
        risk_budget_pct = float(str(fields.get("risk_budget", "1.2")).strip() or "1.2")
    except ValueError as exc:
        raise ValueError("예상 승률(%)과 계좌 허용 손실(1R %)을 숫자로 입력하세요.") from exc
    if not (20.0 <= win_prob_pct <= 85.0 and 0.3 <= risk_budget_pct <= 3.0):
        raise ValueError("예상 승률(20~85%)과 계좌 허용 손실(0.3~3.0%) 범위를 확인하세요.")

    ccy = "KRW" if market == "KR" else "USD"
    upside_pct = float((target / entry - 1) * 100)
    downside_pct = float((1 - floor / entry) * 100)
    asymmetry = round(upside_pct / max(downside_pct, 0.1), 2)
    margin_pct = round(float((1 - entry / target) * 100), 1)
    min_req = ARCHETYPES[archetype]["min_asymmetry"]
    solv_meta = SOLVENCY_TIERS[solvency]
    passes = bool(solv_meta["ok"] and asymmetry >= min_req and margin_pct >= 20.0)
    sizing = compute_position_sizing(
        upside_pct=upside_pct,
        downside_pct=downside_pct,
        win_prob=win_prob_pct / 100.0,
        risk_budget_pct=risk_budget_pct,
        cap_pct=solv_meta["cap_pct"],
        blocked=not solv_meta["ok"],
    )

    rnd = (lambda v: str(round(float(v)))) if ccy == "KRW" else (lambda v: f"{float(v):.2f}")
    t1, t2, t3 = _monotonic_tranches(entry, floor, rnd)

    now = datetime.now(intel.KST).isoformat(timespec="seconds")
    pid = hashlib.sha256(f"{market}:{symbol}:{archetype}:{entry}:{target}".encode()).hexdigest()[:16]
    record = dict(
        id=pid,
        created=now,
        market=market,
        currency=ccy,
        symbol=symbol,
        name=name,
        archetype=archetype,
        archetype_badge=ARCHETYPES[archetype]["badge"],
        solvency=solvency,
        solvency_label=solv_meta["label"],
        win_prob=round(win_prob_pct, 1),
        risk_budget=round(risk_budget_pct, 2),
        sizing=sizing,
        entry=rnd(entry),
        floor=rnd(floor),
        target=rnd(target),
        bull=rnd(target * Decimal("1.20")),
        tranches=[t1, t2, t3],
        upside_pct=round(upside_pct, 1),
        downside_pct=round(downside_pct, 1),
        asymmetry=asymmetry,
        margin_pct=margin_pct,
        passes=passes,
        horizon=horizon,
        crowd_view=crowd_view,
        variant_insight=variant_insight,
        kill_switch=kill_switch,
        url=url,
    )

    def _upsert(old):
        items = [r for r in old.get("items", []) if r.get("id") != pid]
        items.insert(0, record)
        return dict(updated=now, items=items[:50])

    intel.update_json(package, PLAYBOOK_FILE, {}, _upsert)
    return record


def playbooks(package):
    if package is None:
        return []
    return intel.private_json(package, PLAYBOOK_FILE, {}).get("items", [])
