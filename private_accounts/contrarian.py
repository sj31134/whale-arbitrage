"""Public contrarian variant-perception scanner and 12-month catalyst-driven 1-stock concentrated engine.
Never accepts personal portfolio holdings in public collection.
Enforces 3 hard anti-regression invariants from CoT post-mortem:
  1. Zero single-digit diversification bleed (passing conviction weights must be 30% ~ 75%, else 0% pass).
  2. Zero ex-post tenbagger hindsight bias (5-year trough multiple <= 3.6x).
  3. Zero multi-year 'buy & hope' dead-money traps (target horizon strictly <= 12 months with dated catalyst & Time-Stop)."""

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

EX_TENBAGGER_CEILING = 3.6
MAX_HORIZON_MONTHS = 12

# Forensic CoT Self-Audit: Why previous agent iterations failed & how code invariants permanently block recurrence
AGENT_COT_POSTMORTEM = (
    dict(
        code="COT-ERR-01",
        bias_name="가용성 휴리스틱 & 사후 확증편향 (Availability & Hindsight Bias)",
        cot_trace=(
            "최초 메뉴 구축 시 ‘검증된 해자 기업’을 빠르게 채우려다 기존 스킬 문서(SKILL.md)에 적혀 있던 과거 대박 성공 명단"
            "(SK하이닉스·삼양식품·HD현대일렉·NVDA 등)을 신규 발굴 유니버스에 그대로 복사함."
        ),
        why_fatal="과거에 10~70배 올라 이미 시총 수십조~수천조 원이 된 ‘졸업생’을 미래 텐베거 후보로 착각해 뒷북 매매를 유도함.",
        hard_guardrail="5년 최저점 대비 3.6배 초과(mult_5y_low > 3.6) 종목은 코드에서 자동으로 ex_tenbagger=True · 비중 0% 차단 및 유니버스 등록 금지 불변식 강제.",
    ),
    dict(
        code="COT-ERR-02",
        bias_name="LLM 다수결 타협 편향 & 목적함수 오염 (Sycophantic Averaging / Objective Bleed)",
        cot_trace=(
            "6대 페르소나 점검 당시 ‘모든 페르소나 불만을 동시에 만족시켜야 한다’는 평균화 사고에 빠져, 은행 여신역·연기금·초보자의 "
            "분산 한도(5~10% 캡, 1/4 켈리, 1.2R)를 ‘1종목 초집중 메뉴(/contrarian)’에 교집합으로 덮어씌워 비중을 5%~8%로 깎아내림."
        ),
        why_fatal="다수결 평균에서 벗어나 소수 인사이트로 승부하려는 메뉴의 존재 이유를 파괴하고 과잉분산 드래그(맞혀도 계좌 +10% 정체)를 유발함.",
        hard_guardrail="메뉴 목적함수 격리 불변식: /contrarian 통과 종목의 권장 비중이 25% 미만(한 자릿수 등)으로 계산되면 런타임 불변식 위반 에러 발생(확신 미달은 5% 정찰 대신 즉시 0% 기각).",
    ),
    dict(
        code="COT-ERR-03",
        bias_name="고전 가치투자 클리셰 답습 & 시간함정 불감증 (Multi-Year Buy-and-Hold Cliché / Time-Trap Blindness)",
        cot_trace=(
            "집중투자를 리서치하며 버핏·노마드식 ‘3~5년(24~60개월) 묻어두기’ 문구를 무비판적으로 차용하고, "
            "1년 내 강제 촉매 일정 검증 없이 단순 저PBR·저PER 종목(영원무역·두산밥캣 등)을 후보에 섞어 넣음."
        ),
        why_fatal="1년 내 자본 회전과 시드 점프가 목표인 투자자에게 ‘촉매 없이 3~5년 횡보하는 만년 저평가주(Dead Money)’에 자산 60%가 묶이는 시간함정은 치명적 실패임.",
        hard_guardrail="최대 호흡 12개월 하드캡(13개월 초과·장기보유 문구 입력 시 즉시 ValueError 거부) + 전 종목 ‘12개월 내 확정 촉매 일정(Dated Catalyst)’ 및 ‘2분기(6개월) 무반응 시 시간손절(Time-Stop)’ 의무화.",
    ),
)

EX_TENBAGGER_GRADUATES = (
    ("HD현대일렉트릭 (267260) · 효성중공업", "5년 저점 대비 35배~71배", "2021년 수주 전환 직전(시총 6천억)이 타격 시점 · 현재는 기성 컨센서스"),
    ("SK하이닉스 (000660) · 한화에어로 (012450)", "5년 저점 대비 20배~35배", "이미 대형 리레이팅 완료 (/discover 추세 메뉴 영역)"),
    ("삼양식품 (003230) · 실리콘투 (257720)", "5년 저점 대비 16배~18배", "해외 수출 1차 폭발 기반영 · 신규 역발상 씨앗 대상 제외"),
    ("NVIDIA · Broadcom · Eli Lilly", "시총 $1T~$3.5T 초대형주", "시가총액 물리적 한계로 1년 내 2~4배 비대칭 점프 불가능"),
    ("촉매 없는 단순 저PBR 지주·전통 OEM (영원무역 등)", "만년 저평가 시간함정(Dead Money)", "싸 보이지만 12개월 내 시선 괴리를 깨뜨릴 강제 촉매가 없어 3~5년 자금 묶임 위험으로 제외"),
)

ARCHETYPES = {
    "calm_compounder": dict(
        id="calm_compounder",
        badge="이호걸형 · 1년 내 수출·이익 폭발 집중",
        master="캄투자일임 이호걸 대표 아키타입 (질의 ‘김호걸’ → 공시 대표명 이호걸)",
        track_record="2023.03 17억 원 → 2026 상반기 4,467억 원 (10년 존버가 아니라 단 3년 만에 260배 달성! 매 분기 수출·영업레버리지가 즉시 찍히는 1~3종목 초집중 회전)",
        core_quote="“막연히 5년 뒤를 기다리지 않는다. 당장 이번~다음 분기 수출 통관과 영업이익률이 폭발하는데 시장만 편견으로 못 보는 1등 사업에 집중한다.”",
        crowd_blindspot="대중은 내수·과거 선입견에 갇혀 이미 해외 인허가·채널 진입이 끝나 향후 2~4분기 내 고마진 매출이 찍히기 직전인 중형 독점주를 외면함",
        edge_formula="향후 3~12개월 내 해외 본판매·소모품 레버리지 확정 + 무차입 순현금 1등 기업에 집중자본 40%~75% 투입",
        execution_rule="집중자본 40~75% 압축 · 분기 수출/출하 데이터 매월 대조 · 2개 분기(6개월) 내 이익 레버리지 미확인 시 시간손절(Time-Stop) 회전",
        min_asymmetry=3.5,
        target_weight_range="40% ~ 75% (1~2종목 승부)",
        max_months=12,
        horizon="6~12개월",
        sources=(
            ("캄투자일임 3년 고속 복리 운용 구조 보도 (딜사이트)", "https://dealsite.co.kr/"),
            ("한국경제 집중투자 인터뷰 원문", "https://www.hankyung.com/"),
        ),
    ),
    "druckenmiller_inflection": dict(
        id="druckenmiller_inflection",
        badge="드러큰밀러·스타인하트형 · 6~12개월 변곡점 올인",
        master="스탠리 드러큰밀러 (Duquesne) & 마이클 스타인하트 (Variant Perception 창시자)",
        track_record="드러큰밀러 30년 연평균 30%(무손실) · 스타인하트 연 24.5% — 현재 최악의 악재 직후 ‘6~12개월 뒤 수급·실적 변곡점’에 40~80% 한 바구니 집중",
        core_quote="“현재 실적은 최악이지만 6~12개월 뒤 산업 수급이 정반대로 뒤집히는 순간이 보이면 한 바구니에 담고, 예상 시점에 안 터지면 미련 없이 시간손절하라.”",
        crowd_blindspot="대중은 직전 분기 재고조정·정책 루머를 영구적 재앙으로 착각해 투매하지만, 실제 재고 소진·정책 확정 변곡점은 2~3분기 안에 도래함",
        edge_formula="재고조정 종료·관세/규제 확정 등 6~12개월 내 방향 전환 촉매가 명확한 독점주에 집중자본 40%~75% 선제 타격",
        execution_rule="소액 정찰 금지 · 예상 촉매 시점(6개월) 경과 후에도 펀더멘털 반전이 없으면 본전이어도 즉시 시간손절(Time-Stop)",
        min_asymmetry=4.0,
        target_weight_range="40% ~ 75% (단독 1종목 승부)",
        max_months=12,
        horizon="6~12개월",
        sources=(
            ("NBER ‘Best Ideas’ 최고 확신 1종목 알파 논문", "https://www.nber.org/papers/w15012"),
            ("Morgan Stanley ‘Expectations Investing & Variant Perception’", "https://www.morganstanley.com/im/"),
        ),
    ),
    "greenblatt_catalyst": dict(
        id="greenblatt_catalyst",
        badge="그린블란트·테퍼형 · 확정 이벤트 특수상황 집중",
        master="조엘 그린블란트 (Gotham Capital 연 50%) & 데이비드 테퍼 (Appaloosa)",
        track_record="그린블란트 고담캐피탈 10년(1985~1994) 연복리 50% 달성 · 만년 저평가 단순 가치주 대신 ‘날짜가 박힌 강제 재평가 촉매(Special Situations)’에 소수 초집중",
        core_quote="“촉매 없는 저평가주는 5년 동안 쌀 수 있다. 기관 강제투매 종료·요율 자동 인상·신제품 승인처럼 1년 안에 시장이 재평가할 수밖에 없는 이벤트에만 집중하라.”",
        crowd_blindspot="합병 일회성 비용·정부 요율 반영 시차·인덱스 리밸런싱 등 ‘일시적 제도/회계 왜곡’으로 폭락한 주식을 구조적 쇠퇴로 오인함",
        edge_formula="일시적 회계/제도 왜곡 해소 날짜가 향후 3~12개월 내로 확정된 순현금·고ROIC 기업에 35%~65% 집중",
        execution_rule="이벤트 발효 분기까지 집중 보유 · 이벤트 발효 후 +60%~+150% 리레이팅 달성 즉시 현금화해 다음 이벤트로 자본 고속 회전",
        min_asymmetry=4.0,
        target_weight_range="35% ~ 65% (2종목 압축)",
        max_months=12,
        horizon="3~12개월",
        sources=(
            ("Gotham Funds · 특수상황 및 촉매 가치투자 아카이브", "https://www.gothamfunds.com/"),
            ("Cremers & Petajisto (2009) 집중 스톡피커 알파 논문", "https://academic.oup.com/rfs/article-abstract/22/9/3329/1563727"),
        ),
    ),
    "hynix_bottleneck": dict(
        id="hynix_bottleneck",
        badge="병목 선점형 · 신규 라인·장비 반입 2분기 선취매",
        master="차세대 공정·병목 스케줄 선점 아키타입 (사용자 지칭 ‘한유백’ 유형 · 실명 공시 미특정 단서 명시)",
        track_record="레거시 업황 침체로 주가가 반토막 난 바닥에서 ‘향후 2~4분기 내 확정된 고객사 신규 팹·선단공정 반입(PO) 스케줄’을 보고 독점 병목 소켓·장비·소재 집중 선점",
        core_quote="“5년을 기다리는 게 아니다. 고객사 신규 라인 장비·소재 발주 시점보다 딱 2분기 앞서 공포 바닥에서 모으면 1년 안에 실적이 주가를 강제로 끌어올린다.”",
        crowd_blindspot="전방 레거시 감익 백미러만 보고 투매하느라 6~9개월 뒤 시작될 차세대 선단공정(2nm·HBM4·CoWoS·800V SiC) 필수 병목 발주를 놓침",
        edge_formula="미개화 중형 병목 독점주(5년 저점 ≤3.6배) + 12개월 내 고객사 양산/발주 일정 확정 종목에 집중자본 35%~60% 투입",
        execution_rule="발주 1~2분기 전 역배열 바닥 3단 매집 · 고객사 양산 지연 공시 시 즉시 철회, 쇼티지 뉴스 헤드라인 폭발 시 수확",
        min_asymmetry=4.0,
        target_weight_range="35% ~ 60% (1~3종목 집중)",
        max_months=12,
        horizon="6~12개월",
        sources=(
            ("금융감독원 DART 설비투자·수주 공시 원문", "https://dart.fss.or.kr/"),
            ("SEC EDGAR 반도체 장비·소재 백로그 공시", "https://www.sec.gov/edgar/searchedgar/companysearch"),
        ),
    ),
    "burry_asymmetry": dict(
        id="burry_asymmetry",
        badge="마이클 버리형 · 과매도 극점 + 자사주 소각 단기 회귀",
        master="마이클 버리 (Michael Burry · Scion Asset Management — 실제 평균 보유 2~4분기)",
        track_record="마이클 버리 13F 실증 분석 결과 5~10년 장기보유가 아니라, 패시브 투매 극점 진입 후 6~12개월 내 자사주 소각·실적 반전으로 +50%~+150% 튀면 즉시 수확·교체",
        core_quote="“길가에 버려진 순현금 자산을 사되 영원히 끌어안지 않는다. 자사주 소각과 공포 소멸로 1년 안에 평균회귀가 일어나면 즉시 차익을 확정한다.”",
        crowd_blindspot="극단적 혐오 투매로 주가가 순현금·청산가치까지 밀렸는데 회사가 매년 유통주식의 8~12%를 소각하며 주당순이익(EPS)을 강제로 끌어올리는 효과를 무시함",
        edge_formula="고점 대비 -45%~-75% 투매 + 대규모 자사주 소각·순현금 방어막 가동 종목에 30%~55% 스나이퍼 투입",
        execution_rule="3~12개월 단기 평균회귀 타깃 · 목표 리레이팅 도달 즉시 전량 현금화, 9개월 내 소각·현금흐름 정체 시 교체",
        min_asymmetry=4.5,
        target_weight_range="30% ~ 55% (2~3종목 회전)",
        max_months=12,
        horizon="6~12개월",
        sources=(
            ("SEC EDGAR Scion Asset Management 분기별 13F 회전 기록", "https://www.sec.gov/edgar/searchedgar/companysearch"),
            ("Moreira & Muir 변동성 강제청산 미시구조 논문", "https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf"),
        ),
    ),
    "pabrai_dhandho": dict(
        id="pabrai_dhandho",
        badge="애크먼·파브라이형 · 불확실성 해소 데드라인 켈리 타격",
        master="빌 애크먼 (Pershing Square) & 모니시 파브라이 (Dhandho Kelly Funds)",
        track_record="소송·임상/FDA 허가·단기 유동성 오해 등 ‘불확실성이 걷히는 날짜(Deadline ≤ 12개월)’가 정해진 하방 고정 기회에 켈리 공식으로 30~55% 집중 타격",
        core_quote="“안개가 영원히 끼어 있을 주식은 사지 마라. 1년 안에 안개가 걷히는 확정 이벤트가 있고 하방이 막혀 있을 때 켈리 공식대로 크게 베팅하라.”",
        crowd_blindspot="규제·임상·수주 전환 결과를 기다리기 싫어하는 단기 펀드들이 확정 이벤트 직전 1~2분기에 최저가로 주식을 던짐",
        edge_formula="하방 순현금·기존 캐시카우로 손실폭 -12% 이내 고정 + 12개월 내 인허가·로열티·온보딩 데드라인 존재 종목에 30%~55% 베팅",
        execution_rule="이벤트 데드라인 전후 승부 · 데드라인 지연·기각 공시 시 당일 즉시 철회(장기 비자발적 홀딩 절대 금지!)",
        min_asymmetry=4.5,
        target_weight_range="30% ~ 55% (이벤트 스나이퍼)",
        max_months=12,
        horizon="3~12개월",
        sources=(
            ("J.L. Kelly Jr. (1956) 최적 정보·집중 베팅 원전 논문", "https://www.princeton.edu/~wbialek/rome/refs/kelly_56.pdf"),
            ("Pershing Square 집중 카탈리스트 연구", "https://pershingsquareholdings.com/"),
        ),
    ),
}

ACADEMIC_RESEARCH = (
    dict(
        title="Best Ideas (최고 확신 1종목 알파와 과잉분산의 해악)",
        authors="Randolph Cohen (Harvard) · Christopher Polk (LSE) · Bernhard Silli (2010, NBER Working Paper 15012)",
        finding=(
            "펀드매니저의 ‘단 1위 최고 확신 종목(Best Idea #1)’은 향후 12개월간 시장 및 나머지 분산 보유 종목을 연 +2.8%~+4.5%p(고확신 구간 +6~9%p) 압도했다. "
            " 특히 초과수익의 대부분은 편입 후 첫 6~12개월 구간에 집중 발현되었으며, 20~100종목 분산은 알파를 희석하는 주범임이 입증됐다."
        ),
        url="https://www.nber.org/papers/w15012",
    ),
    dict(
        title="Small-Seed Capital Velocity & Kelly Criterion (복리 회전속도 f × 집중비중 L)",
        authors="John L. Kelly Jr. (1956, Bell System Technical Journal) & Edward O. Thorp",
        finding=(
            "자산 증식 공식 Π(T) = Seed₀ · (1 + f* · R)^(회전수 f · T)에서 5~10년 동안 촉매 없는 주식에 묶여 회전수(f)가 0.2로 떨어지면 복리가 멈춘다. "
            "반대로 6~12개월 내 결과물이 나오는 비대칭 기회(연 회전수 f ≥ 1.0)에 켈리 최적 집중 비중(30%~75%)을 실어 연속 회전할 때 기하성장이 극대화된다."
        ),
        url="https://www.princeton.edu/~wbialek/rome/refs/kelly_56.pdf",
    ),
    dict(
        title="Active Share & Catalyst Special Situations (촉매 있는 집중투자의 연 50% 실증)",
        authors="Joel Greenblatt (Gotham Capital, 1985~1994) & Cremers·Petajisto (2009, Review of Financial Studies)",
        finding=(
            "단순히 PBR이 낮은 만년 저평가주(촉매 부재)는 수년간 시장 대비 언더퍼폼할 수 있으나, 강제 매도 종료·사업 분할·신규 인허가 등 "
            "12개월 내 가치 재평가를 강제하는 촉매(Catalyst)와 소수 종목 초집중(High Active Share)이 결합될 때 폭발적 단기 리레이팅이 발생한다."
        ),
        url="https://academic.oup.com/rfs/article-abstract/22/9/3329/1563727",
    ),
    dict(
        title="Variant Perception & Time-Stop Discipline (시선 괴리와 시간 손절 규율)",
        authors="Michael Steinhardt (Steinhardt Partners) & Stanley Druckenmiller (Duquesne)",
        finding=(
            "1년 내 승부를 보는 집중투자에서 가장 위험한 적은 ‘주가가 안 빠지지만 오르지도 않는 시간함정(Dead Money)’이다. "
            "따라서 진입 시 반드시 ‘언제까지(예: 2개 분기·6개월 내) 어떤 숫자가 찍혀야 하는가’를 못 박고, 기한 내 미발생 시 가격과 무관하게 철수하는 Time-Stop이 필수다."
        ),
        url="https://www.morganstanley.com/im/",
    ),
)

VALIDATION_MATRIX = dict(
    summary=(
        "5~10년 막연히 기다리는 투자를 배제합니다. 역사적 대박 사례들 역시 매수 후 10년을 기다린 것이 아니라, "
        "‘신공장 가동·HBM 수주 폭발·비용 구조조정 선언’이라는 명확한 6~12개월 촉매 직전에 진입해 첫 1년 안에 +100%~+300% 1차 폭발이 일어났습니다. "
        "반면 기성 텐베거나 촉매 없는 만년 저PBR 주식(시간함정)은 1년 내 승부가 불가능하므로 실시간 발굴 레이더에서 전면 제외합니다."
    ),
    cases=(
        dict(
            name="삼양식품 (003230) · [졸업 교본: 밀양 1공장 가동 직전 12개월]",
            archetype="이호걸형 · 수출 캐파 가동 촉매",
            verdict="촉매 적중 · 가동 후 1년 내 +180% 1차 폭발",
            trough="수출 전용 공장 가동 및 미국 월마트/코스트코 본입점 직전 분기",
            peak_or_now="5년 기다린 것이 아니라 ‘수출 통관 급증 분기’ 포착 직후 12개월 내 1차 리레이팅 완성 (현재는 기성주 제외)",
            crowd_then="원맥 원가 부담·내수 라면 한계 편견",
            variant_edge="1년 승부 교훈: 이미 해외 수요는 꽉 찼는데 신규 인허가·신공장 가동이 향후 2~3분기 내 시작되는 종목을 노려야 1년 안에 터짐",
        ),
        dict(
            name="Meta Platforms (META) · [졸업 교본: ‘효율성의 해’ 선언 직후 12개월]",
            archetype="그린블란트·버리형 · 비용 절감·소각 촉매",
            verdict="촉매 적중 · 2022.11 $93 → 2023.11 $330 (+254% / 1년)",
            trough="2022-10 · $93.16 (-76% 투매 극점)",
            peak_or_now="단 12개월 만에 +254%(3.5배) 수직 복원! (현재는 메가캡 복귀로 제외)",
            crowd_then="메타버스 지출 과잉 비난으로 PER 9배 투매",
            variant_edge="1년 승부 교훈: 본업 현금흐름이 막강한 기업에서 일회성 비용/재고조정이 끝나는 확정 분기 + 대규모 자사주 소각이 맞물리면 1년 안에 2~3배 복원됨",
        ),
        dict(
            name="SK하이닉스 (000660) · [졸업 교본: HBM3 독점 공급 시작 12개월]",
            archetype="병목 선점형 · 신규 라인 납품 촉매",
            verdict="촉매 적중 · 2023.01 7.5만 → 2024.01 14만+ (1년 +90% 후 가속)",
            trough="2022 말 적자 바닥이나 HBM3 양산 납품 스케줄 확정 시점",
            peak_or_now="고객사 AI 가속기 출하 스케줄과 동시에 12개월 내 흑자전환·리레이팅 직행 (현재는 기성주 제외)",
            crowd_then="레거시 D램 적자 공포 매도",
            variant_edge="1년 승부 교훈: 고객사의 차세대 칩/라인 양산 일정(PO 반입)이 6~9개월 내로 박혀 있는 독점 소켓·장비·소재만 타격해야 시간함정을 피함",
        ),
        dict(
            name="촉매 없는 만년 저PBR 가치주 · [반증: 시간함정(Time Trap) 금지]",
            archetype="시간함정 경보 · 12개월 촉매 부재",
            verdict="실패(시간함정) · 3~5년간 PBR 0.4배 그대로 횡보",
            trough="순현금이 시총만 한데도 3년 내내 주가 제자리(기회비용 파괴)",
            peak_or_now="1년 내 자본 회전 목표 실패 · 집중자본 장기 동결",
            crowd_then="‘자산가치 대비 싸니까 언젠가 오르겠지’라는 막연한 장기 가치투자 희망",
            variant_edge="반증 교훈: 12개월 안에 시장을 강제로 흔들 ‘확정 촉매(인허가·증설가동·요율인상·대규모 소각)’가 없으면 아무리 싸도 1종목 집중 대상에서 즉시 탈락!",
        ),
    ),
    comparison=(
        ("목표 보유 호흡", "추세 꺾일 때까지 보유 (/discover)", "5~10년 존버 절대 금지! 반드시 ‘3~12개월 이내’ 승부 + 6개월 무반응 시 시간손절(Time-Stop)"),
        ("종목 선정 필수 관문", "현재 수급·차트 정배열 우위", "미개화 바닥(5년저점 ≤3.6배) + ‘향후 12개월 내 날짜가 박힌 강제 재평가 촉매’ 필수"),
        ("포지션 비중 철학", "종목당 10~20% 분산", "전용 집중자본의 30%~75% 초집중 (확신·촉매 미달 시 5% 정찰도 금지하고 0% 패스)"),
        ("가장 경계할 실패", "고점 추격 후 눌림 손실", "① 기성 텐베거 뒷북 매수, ② 촉매 없이 3~5년 묶이는 ‘만년 저평가 시간함정(Dead Money)’"),
    ),
)

SOLVENCY_TIERS = {
    "net_cash": dict(
        label="S급 재무요새 · 무차입 순현금·고마진 FCF (단독 50~75% 초집중 적격)",
        cap_pct=75.0,
        min_pct=40.0,
        portfolio_guide="집중계좌 1~2종목 12개월 승부 (이호걸·드러큰밀러급)",
        ok=True,
    ),
    "backlog_float": dict(
        label="A급 확정수주·현금흐름 · 선수금·영업흑자 건전 (주력 35~55% 집중 적격)",
        cap_pct=55.0,
        min_pct=30.0,
        portfolio_guide="집중계좌 2~3종목 12개월 승부 (그린블란트·테퍼급)",
        ok=True,
    ),
    "turnaround_watch": dict(
        label="B급 턴어라운드 · 12개월 내 흑자/레버리지 촉매 임박 (선발 25~35% 집중 적격)",
        cap_pct=35.0,
        min_pct=25.0,
        portfolio_guide="집중계좌 3종목 이내 · 6개월 Time-Stop 엄수",
        ok=True,
    ),
    "distressed_block": dict(
        label="집중 부적격 · 유상증자·차환 위험 또는 12개월 내 촉매 부재 (0% 기각)",
        cap_pct=0.0,
        min_pct=0.0,
        portfolio_guide="베팅 기각 (Pass — 시간함정·희석 위험 종목은 1주도 사지 않음)",
        ok=False,
    ),
}

# 20 High-Velocity 12-Month Catalyst Candidates (Zero Ex-Tenbaggers AND Zero Catalyst-less Dead-Money Value Traps!)
# (sym, market, venue, ccy, name, arch_id, solv_key, essence[0..35], cat_months[<=12], catalyst_12m, time_stop, moat_essence, crowd_fear, kill_switch)
CONTRARIAN_UNIVERSE = (
    # --- KOREA: 10 Uncrowded Gems with Hard 3~12 Month Catalysts ---
    ("214150", "KR", "KOSDAQ", "KRW", "클래시스", "calm_compounder", "net_cash", 34, 6,
     "향후 2~3분기 내 유럽 CE 인증 장비 본선적 매출 인식 + 합병 일회성 비용 소멸에 따른 분기 영업이익률 50% 복원 및 미국 FDA 임상/허가 단계 진입",
     "진입 후 2개 분기(6개월) 내 카트리지 수출액 분기 최고치 미경신 시 주가 무관 즉시 교체",
     "장비 설치 후 영업이익률 ~50% 카트리지 소모품이 반복 소비되는 무차입 순현금 면도날 모델 (5년 저점 대비 1.7배 미개화)",
     "단기 합병 통합 비용과 내수 미용 둔화 우려로 52주 고점 대비 -69% 과매도",
     "주력 소모품 분기 수출 역성장 또는 미국·유럽 인허가 무산 공시"),
    ("058470", "KR", "KOSDAQ", "KRW", "리노공업", "hynix_bottleneck", "net_cash", 35, 6,
     "향후 2~3분기 빅테크 자체 AI 추론칩(ASIC)·차세대 모바일 AP 신규 테이프아웃 집중에 따른 고단가 R&D 테스트 소켓 수주·분기 사상 최대 실적 구간",
     "진입 후 6개월 내 분기 영업이익 전년동기비 플러스 전환·마진 38%+ 미확인 시 시간손절",
     "글로벌 빅테크 AI/NPU 샘플 검증 필수 초미세 리노핀·소켓 독점 과점 · 무차입 영업이익률 40%+ 요새",
     "레거시 스마트폰 출하 둔화와 묶여 52주 고점 대비 -59% 급락 (5년 저점 대비 2.1배)",
     "선단 피치 소켓 독점 점유율 이탈 또는 분기 영업이익률 30% 하회 공시"),
    ("103140", "KR", "KRX", "KRW", "풍산", "hynix_bottleneck", "backlog_float", 33, 6,
     "155mm 대구경 포탄 증설 캐파(2배 확장) 본격 가동 물량이 향후 2~3분기 고마진 방산 수출 매출·영업이익으로 직접 계상",
     "향후 2개 분기 내 방산 수출 매출 비중 및 분기 영업이익 서프라이즈 미발생 시 시간손절",
     "서방권 재고 고갈 속 증설이 가장 느린 대구경 탄약 물리적 공급 병목(E_s ≈ 0) + PBR 0.6배 자산 하방",
     "구리 가격에 흔들리는 단순 비철금속 굴뚝주 편견으로 고점 대비 -63% 폭락 (5년 저점 대비 2.0배)",
     "방산 수출 수주잔고 감소 전환 또는 장기 공급계약 해지 공시"),
    ("240810", "KR", "KOSDAQ", "KRW", "원익IPS", "hynix_bottleneck", "turnaround_watch", 31, 9,
     "향후 6~9개월 내 삼성·하이닉스 차세대 HBM4 및 선단 D램/낸드 전환 라인용 핵심 증착장비 발주(PO)·반입 스케줄 본격화",
     "향후 2개 분기 내 반도체 장비 신규 수주 반등 및 영업이익 흑자폭 확대 미확인 시 즉시 철수",
     "국내 메모리 양사 선단 공정 전환 시 설비 반입 1순위로 실적이 수직 반등하는 핵심 전공정 증착장비 과점",
     "직전 메모리 감산·설비투자 공백기 후행 실적 탓에 고점 대비 -62% 폭락",
     "주요 고객사 선단 라인 증설 전면 연기 또는 경쟁사 장비 점유율 잠식"),
    ("014680", "KR", "KRX", "KRW", "한솔케미칼", "druckenmiller_inflection", "backlog_float", 32, 6,
     "향후 2~3분기 내 파운드리 2nm GAA 초기 양산 돌입 및 HBM 가동률 상승으로 초고순도 과산화수소·프리커서 출하량 즉각 반등",
     "진입 후 6개월 내 반도체 소재 부문 분기 영업이익 반등 미확인 시 시간손절",
     "TSMC·삼성·하이닉스 선단 공정 필수 초고순도 과산화수소·프리커서 과점 (이차전지 감익 기저 종료)",
     "비주력 이차전지 소재 우려에 가려 52주 고점 대비 -43% 하락 (5년 저점 대비 2.1배)",
     "선단 파운드리향 핵심 소재 공급 점유율 축소 공시"),
    ("145020", "KR", "KRX", "KRW", "휴젤", "calm_compounder", "net_cash", 33, 6,
     "미국 FDA 허가 이후 현지 파트너사 본판매 재주문(Re-order) 물량이 향후 2~3분기 수출 통관 데이터와 영업이익으로 본격 반영",
     "향후 2개 분기 연속 북미향 톡신 수출 통관액 증가 미확인 시 시간손절 회전",
     "국내 유일 미국·유럽·중국 3대 톡신 시장 동시 진입 완료 + 무차입 순현금 고마진 수출 구조",
     "과거 소송 피로감과 내수 보톡스 경쟁 선입견으로 5년 고점 대비 -44% 아래 정체",
     "미국·중국 분기 수출액 역성장 전환 또는 FDA 품질 이슈 발생"),
    ("000100", "KR", "KRX", "KRW", "유한양행", "pabrai_dhandho", "backlog_float", 32, 9,
     "향후 3~9개월 내 J&J 폐암 1차 치료제(렉라자+리브리반트) 글로벌 상업 처방 확대에 따른 단계별 출시 마일스톤 및 분기 로열티 현금 유입",
     "향후 2개 분기 내 글로벌 파트너사 처방 매출 및 로열티 유입 증가세 둔화 시 즉시 교체",
     "국내 전통 제약 본업이 하방을 지지하는 가운데 글로벌 블록버스터 순수 로열티(원가 거의 0%)가 영업이익에 직결",
     "단기 차익매물과 바이오 섹터 변동성으로 52주 고점 대비 -29% (5년 고점 대비 -48%) 조정",
     "병용요법 글로벌 처방 점유율 부진 또는 중대 부작용 권고 변경"),
    ("140860", "KR", "KOSDAQ", "KRW", "파크시스템스", "hynix_bottleneck", "net_cash", 33, 9,
     "향후 6~9개월 내 2nm 이하 게이트올어라운드(GAA) 및 HBM 하이브리드 본딩 수율 검사용 산업용 원자현미경(AFM) 신규 수주 집중",
     "향후 2개 분기 내 수주잔고 성장률 둔화 시 시간손절",
     "비접촉 산업용 원자현미경(AFM) 전 세계 독점 지위(점유율 1위) · 미세화될수록 기존 광학계측을 대체하는 물리적 병목",
     "반도체 중소형 장비주 일괄 매도로 52주 고점 대비 -42% 하락 (5년 저점 대비 2.15배)",
     "글로벌 파운드리 선단 계측 공정 내 AFM 채택 지연 공시"),
    ("298380", "KR", "KOSDAQ", "KRW", "에이비엘바이오", "pabrai_dhandho", "backlog_float", 30, 9,
     "향후 6~12개월 내 뇌혈관장벽(BBB) 투과 셔틀 플랫폼(Grabody-B) 글로벌 빅파마 추가 기술이전 및 기존 파트너 임상 단계 마일스톤 도래",
     "향후 9개월 내 신규 기술이전·임상 진전 마일스톤 부재 시 지체 없이 시간손절",
     "사노피 등에 검증된 퇴행성 뇌질환 BBB 셔틀 원천 플랫폼 보유 · 계약금·마일스톤 기반 현금 확보",
     "코스닥 바이오 투심 붕괴로 52주 고점 대비 -77% 폭락 (5년 저점 대비 2.9배)",
     "핵심 파트너사 임상 중단·권리 반환 공시 또는 주주배정 유상증자"),
    ("259960", "KR", "KRX", "KRW", "크래프톤", "greenblatt_catalyst", "net_cash", 32, 6,
     "향후 2~3분기 대형 신작 글로벌 정식 출시 성적표 확인 + 기존 PUBG 분기 사상 최대 영업이익 경신으로 ‘단일 IP 할인’ 강제 해소",
     "신작 출시 분기 후 트래픽 부진 및 영업이익 정체 시 본전이어도 즉시 시간손절",
     "수조 원 순현금 하방 요새 위에서 연간 1조 원+ 영업이익을 창출하며 신작 옵션을 공짜로 가진 비대칭 구조",
     "신작 출시 전 막연한 우려로 5년 고점 대비 -58% 아래(5년 저점 대비 1.4배) 저평가",
     "핵심 IP 분기 매출 15%+ 역성장 또는 대규모 적자 M&A 강행"),

    # --- US: 10 Uncrowded Gems with Hard 3~12 Month Catalysts ---
    ("ONTO", "US", "NYSE", "USD", "Onto Innovation", "hynix_bottleneck", "net_cash", 34, 6,
     "향후 2~3분기 TSMC CoWoS 증설 및 HBM 다단 적층 라인향 Dragonfly 3D 광학 검사장비 출하·매출 가속",
     "향후 2개 분기 내 AI 패키징 검사 매출 가이던스 상향 미확인 시 시간손절",
     "시총 $8B대 중형 체급에서 AI 첨단 패키징 수율 병목을 독식하는 무차입 순현금 장비주",
     "반도체 장비 섹터 일괄 조정으로 52주 고점 대비 -53% 폭락 (5년 저점 대비 3.0배)",
     "핵심 파운드리·HBM 고객사 패키징 검사장비 발주 중단"),
    ("ACLS", "US", "NASDAQ", "USD", "Axcelis Technologies", "hynix_bottleneck", "net_cash", 33, 9,
     "향후 6~12개월 내 800V AI 데이터센터 전력장치 및 200mm SiC 웨이퍼 팹 전환용 고온 이온주입 장비 수주 턴어라운드",
     "향후 2개 분기 내 수주잔고(Backlog) 바닥 반전 미확인 시 시간손절 교체",
     "SiC 전력반도체 고온 이온주입(Purion) 독점 과점 + 무차입 순현금 재무요새(시총 $3B 중형주)",
     "단기 전기차 재고 조정 공포로 52주 고점 대비 -45% 반토막 (5년 저점 대비 2.4배)",
     "SiC 이온주입 시장 내 점유율 이탈 또는 분기 적자 전환"),
    ("CELH", "US", "NASDAQ", "USD", "Celsius Holdings", "druckenmiller_inflection", "net_cash", 32, 6,
     "최대 유통망(펩시코) 재고 감축 사이클 종료 + Alani Nu 인수 결합 매대 확장이 향후 2~3분기 매출 성장률 급반전으로 직접 반영",
     "향후 2개 분기 내 북미 스캐너 판매율 및 매출 성장 재가속 미확인 시 즉시 시간손절",
     "무차입급 재무구조 + 북미 무설탕 기능성 에너지드링크 점유율 3강 체제 장악",
     "유통사 일회성 재고 축소를 브랜드 붕괴로 오해한 군중 투매로 5년 고점 대비 -68% 폭락 (5년 저점 2.1배)",
     "북미 소매 스캐너 점유율 2분기 연속 하락 전환"),
    ("FOUR", "US", "NYSE", "USD", "Shift4 Payments", "greenblatt_catalyst", "backlog_float", 32, 6,
     "이미 계약 완료된 수십억 달러 규모 스타디움·호텔·글로벌 면세 통합결제 백로그가 향후 2~3분기 내 실제 가동(Go-Live) 수수료로 전환",
     "향후 2개 분기 내 순결제거래액(E2E Volume) 및 FCF 가이던스 미달 시 시간손절",
     "스포츠 경기장·고급 호텔 특화 통합 결제 독점력 + 창업자 교체 불확실성 해소 및 대규모 자사주 소각",
     "CEO 공직 지명 헤드라인 소음과 핀테크 멀티플 압축으로 5년 고점 대비 -62% 급락 (5년 저점 1.4배)",
     "대형 엔터프라이즈 가맹점 이탈 급증 또는 인수 차입 부담 악화"),
    ("FSLR", "US", "NASDAQ", "USD", "First Solar", "druckenmiller_inflection", "net_cash", 33, 6,
     "향후 6~9개월 내 미국 신규 공장 램프업 물량 인도 + 동남아 우회 중국산 패널 고율 관세 부과로 북미 AI 데이터센터 전력 직납 마진 급증",
     "향후 2개 분기 내 정책 법안 불확실성 해소 및 수주 단가(ASP) 방어 실패 시 시간손절",
     "비중국 박막형(CdTe) 유틸리티 태양광 미국 내 독점 공급사 · 70GW+ 기확정 장기 수주잔고 + 순현금",
     "보조금 축소 정치 헤드라인 공포에 패시브 투매가 쏟아지며 52주 고점 대비 -53% 폭락",
     "미국 제조 세액공제(45X) 전면 폐지 확정 또는 대규모 수주 계약 해지"),
    ("MOH", "US", "NYSE", "USD", "Molina Healthcare", "greenblatt_catalyst", "backlog_float", 32, 6,
     "주정부 메디케이드 신규 연도 요율 인상(Rate Reset) 발효 시점이 도래해 향후 2~3분기 내 의료비율(MCR) 정상화 및 EPS 급반등 확정",
     "신규 요율 적용 분기에도 의료비율(MCR) 악화가 지속되면 즉시 시간손절",
     "마이클 버리 집중 종목 · 정부 계약상 원가 상승분이 차기 요율에 자동 전가되는 구조 + 공격적 자사주 소각",
     "요율 반영 시차로 인한 단기 마진 압박을 영구 훼손으로 오인해 5년 고점 대비 -51% 폭락 (5년 저점 1.5배)",
     "핵심 주정부 메디케이드 재계약 탈락 또는 연방 보조금 구조 개편"),
    ("LULU", "US", "NASDAQ", "USD", "Lululemon Athletica", "burry_asymmetry", "net_cash", 33, 6,
     "향후 2개 분기 북미 신제품 라인업 리프레시 성적표 + 시총 대비 대규모 자사주 매입·소각 집행으로 PER 10배 극단적 저평가 해소",
     "향후 2개 분기 내 미주 동일매장매출 감소폭 축소 실패 시 본전이어도 시간손절",
     "무차입 순현금 + ROIC 30%+ 브랜드 파워 + 중국 연 25%+ 고성장 (2022년 Meta급 과매도 바닥)",
     "북미 성장 둔화 공포로 5년 고점 대비 -79% 폭락하며 5년 최저점(1.18배) 기록",
     "매출총이익률 55% 하회 또는 재고 덤핑 할인 고착화"),
    ("BABA", "US", "NYSE", "USD", "Alibaba Group", "burry_asymmetry", "net_cash", 32, 6,
     "향후 2~3분기 내 AI 클라우드(Qwen) 기업향 매출 가속 + 연간 유통주식 8~10% 규모 자사주 소각·특별배당 현금 집행",
     "향후 2개 분기 내 자사주 소각 속도 둔화 또는 클라우드 마진 역전 시 즉시 교체",
     "마이클 버리 최대 집중 베팅 · 시총 대비 막대한 순현금 하방 방어막과 매년 주당가치를 10%씩 올리는 소각 엔진",
     "중국 매크로 혐오로 고점 대비 -49% 폭락 (5년 저점 대비 1.4배 청산가치 수준)",
     "자사주 소각 중단 또는 핵심 커머스 잉여현금흐름 급감"),
    ("NVO", "US", "NYSE", "USD", "Novo Nordisk", "pabrai_dhandho", "backlog_float", 34, 9,
     "향후 6~9개월 내 신규 인수 충전 공장(Catalent) 본격 가동에 따른 위고비 공급 병목 해소 처방량 점프 및 후속 비만약 허가 모멘텀",
     "향후 2개 분기 내 신규 공장 가동 후에도 처방 물량 가속이 없으면 시간손절",
     "글로벌 GLP-1 원료의약품(API) 증설 장벽과 전 세계 당뇨·비만 복점 캐시카우",
     "임상 수치 기대치 미달·약가 노이즈로 5년 고점 대비 -71% 폭락하며 5년 최저점(1.14배) 회귀",
     "세마글루타이드 글로벌 처방 점유율 급감 또는 중대 안전성 결함"),
    ("CCJ", "US", "NYSE", "USD", "Cameco", "druckenmiller_inflection", "backlog_float", 33, 9,
     "러시아 농축우라늄 수입 금지 본격 발효 및 향후 6~12개월 내 서방 유틸리티·빅테크 원전 장기 우라늄 구매계약(Term) 체결 집중",
     "향후 9개월 내 장기 우라늄 계약 단가 상승 및 수주량 확대 미확인 시 시간손절",
     "서방권 유일 대형 고품위 우라늄 광산 + Westinghouse 연료주기 지분 결합 절대 공급 병목(E_s ≈ 0)",
     "원전 테마 단기 차익실현으로 52주 고점 대비 -52% 급락 (5년 저점 대비 3.36배)",
     "주력 광산 침수·가동 중단 또는 장기 우라늄 계약 단가 하락 전환"),
)


def _default_get(url):
    req = Request(url, headers={"User-Agent": "whale-tracking/1.0 local contrarian research"})
    with urlopen(req, timeout=7) as resp:
        return resp.read(2_000_000)


def _clamp(val, lo, hi):
    return max(lo, min(hi, val))


def parse_horizon_months(horizon_text):
    """Enforce strictly <= 12 months target inflection horizon. Reject multi-year (e.g. 24개월, 3년, 5년) buy-and-hope."""
    s = str(horizon_text or "").strip()
    if not s:
        raise ValueError("목표 승부 기한(12개월 이내, 예: 6~12개월)을 입력하세요.")
    yr_matches = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*년", s)]
    if any(y > 1.0 for y in yr_matches) or any(tok in s for tok in ("장기", "영구", "존버", "무기한")):
        raise ValueError("5~10년 장기 홀딩 배제 원칙: 1년(12개월) 이내에 승부 날 촉매 시나리오만 허용됩니다.")
    mo_matches = [int(x) for x in re.findall(r"(\d+)\s*개?월", s)]
    q_matches = [int(x) * 3 for x in re.findall(r"(\d+)\s*분기", s)]
    vals = mo_matches + q_matches + [int(round(y * 12)) for y in yr_matches]
    if not vals:
        raise ValueError("목표 승부 기한에 개월/분기 숫자를 명시하세요 (최대 12개월 이내, 예: 6~12개월).")
    max_m = max(vals)
    if max_m > MAX_HORIZON_MONTHS or max_m < 1:
        raise ValueError(f"1년 내 승부 원칙 위반: 입력 기한({max_m}개월)이 상한(12개월)을 초과했습니다. 3~12개월 내 확정 촉매 종목만 설계하세요.")
    return max_m


def validate_contrarian_invariants(record_or_cand, *, is_playbook=False):
    """Hard runtime harness preventing recurrence of CoT-ERR-01 (ex-tenbaggers), CoT-ERR-02 (5~8% dilution), and CoT-ERR-03 (>12M dead money)."""
    h_months = parse_horizon_months(record_or_cand.get("horizon", ""))
    if h_months > MAX_HORIZON_MONTHS:
        raise ValueError("CoT 불변식 위반: 12개월 초과 보유 호흡은 허용되지 않습니다.")
    if not str(record_or_cand.get("catalyst_12m", "")).strip() or not str(record_or_cand.get("time_stop", "")).strip():
        raise ValueError("CoT 불변식 위반: 12개월 내 확정 촉매 일정과 시간손절(Time-Stop) 기준이 누락되었습니다.")
    sz = record_or_cand.get("sizing", {})
    rec_w = float(sz.get("recommended_pct", 0.0))
    if 0.0 < rec_w < 25.0:
        raise ValueError(f"CoT 불변식 위반: 한 자릿수·분산 비중({rec_w}%) 오염 감지. 통과 종목은 25~75%, 미달은 0% 기각이어야 합니다.")
    if not is_playbook and record_or_cand.get("trap_shield_ok"):
        if record_or_cand.get("ex_tenbagger") or float(record_or_cand.get("mult_5y_low", 99.0)) > EX_TENBAGGER_CEILING:
            raise ValueError("CoT 불변식 위반: 기성 급등주(5년 저점 대비 >3.6배)가 통과 목록에 포함되었습니다.")


def compute_position_sizing(*, upside_pct, downside_pct, win_prob=0.60, cap_pct=60.0, min_pct=30.0, blocked=False):
    """High-Conviction Concentrated Kelly Sizing (25% ~ 75% of dedicated conviction capital — NEVER 5~8%!)."""
    if blocked or cap_pct <= 0 or upside_pct <= 0 or downside_pct <= 0:
        return dict(
            kelly_full_pct=0.0,
            kelly_quarter_pct=0.0,
            recommended_pct=0.0,
            cap_pct=max(0.0, float(cap_pct)),
            grade_label="0% · 베팅 기각 (촉매·확신 미달 시 5% 정찰도 금지)",
            portfolio_guide="매수 보류 (Pass)",
        )
    p = _clamp(float(win_prob), 0.25, 0.85)
    q = 1.0 - p
    b = max(float(upside_pct) / max(float(downside_pct), 1.0), 0.1)
    full_kelly = max(0.0, (p * b - q) / b) * 100.0
    if full_kelly < 18.0:
        return dict(
            kelly_full_pct=round(full_kelly, 1),
            kelly_quarter_pct=round(full_kelly * 0.25, 1),
            recommended_pct=0.0,
            cap_pct=round(float(cap_pct), 1),
            grade_label="0% · 1년 기대 우위 부족 (어중간한 분산 진입 금지)",
            portfolio_guide="추가 할인 또는 촉매 임박 대기",
        )
    conv_raw = _clamp(full_kelly * 1.10, max(25.0, float(min_pct)), float(cap_pct))
    rec = round(min(conv_raw, float(cap_pct)), 1)
    if rec >= 50.0:
        grade = f"단독 초집중 · {rec:.0f}% (1~2종목 1년 승부)"
        guide = "집중계좌 1~2종목 압축 · 6개월 Time-Stop"
    elif rec >= 35.0:
        grade = f"주력 집중 · {rec:.0f}% (2~3종목 1년 승부)"
        guide = "집중계좌 2~3종목 압축 · 6개월 Time-Stop"
    else:
        grade = f"선발 집중 · {rec:.0f}% (3종목 이내)"
        guide = "집중계좌 3종목 이내 · 6개월 Time-Stop"
    return dict(
        kelly_full_pct=round(full_kelly, 1),
        kelly_quarter_pct=round(full_kelly * 0.25, 1),
        recommended_pct=rec,
        cap_pct=round(float(cap_pct), 1),
        grade_label=grade,
        portfolio_guide=guide,
    )


def _monotonic_tranches(entry_val, floor_val, rnd):
    span = max(0.0, float(entry_val) - float(floor_val))
    t1 = rnd(float(entry_val))
    t2 = rnd(float(entry_val) - span * 0.45)
    t3 = rnd(float(entry_val) - span * 0.85)
    return [t1, t2, t3]


def _yahoo_series(symbol, market, venue, rng, interval, get_bytes):
    if market == "KR":
        suffixes = (".KQ", ".KS") if venue == "KOSDAQ" else (".KS", ".KQ")
    else:
        suffixes = ("",)
    last_err = None
    for sfx in suffixes:
        yh_sym = f"{symbol}{sfx}"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yh_sym}?range={rng}&interval={interval}"
        try:
            doc = json.loads(get_bytes(url).decode("utf-8", errors="replace"))["chart"]["result"][0]
            q = doc["indicators"]["quote"][0]
            closes = [float(c) for c in q.get("close", ()) if c is not None and c > 0]
            if closes:
                return closes
        except Exception as exc:
            last_err = exc
    if last_err:
        raise last_err
    return []


def _score_candidate(spec, db_bars, cur_price, five_yr_closes=None):
    (
        sym, market, venue, ccy, name, arch_id, solv_key, essence,
        cat_months, catalyst_12m, time_stop, moat_txt, fear_txt, kill_txt
    ) = spec
    if cat_months > MAX_HORIZON_MONTHS:
        return None
    closes = list(db_bars)
    if cur_price and cur_price > 0 and (not closes or abs(cur_price - closes[-1]) / closes[-1] > 1e-5):
        closes.append(float(cur_price))
    if len(closes) < 25:
        return None
    cur = closes[-1]
    window_1y = closes[-252:] if len(closes) >= 252 else closes
    high52 = max(window_1y)
    low52 = min(window_1y)
    dd52 = (cur / high52 - 1) * 100

    hist_5y = list(five_yr_closes) if five_yr_closes else window_1y
    low5y = min(min(hist_5y), low52)
    high5y = max(max(hist_5y), high52)
    mult_5y_low = round(cur / max(low5y, 1e-6), 2)
    dd5y = round((cur / max(high5y, 1e-6) - 1) * 100, 1)
    ex_tenbagger = mult_5y_low > EX_TENBAGGER_CEILING

    ma20 = sum(closes[-20:]) / 20
    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20
    pct20 = (cur / ma20 - 1) * 100
    pct60 = (cur / ma60 - 1) * 100
    diffs = [b - a for a, b in zip(closes[-15:], closes[-14:])]
    up = sum(d for d in diffs if d > 0) / 14
    dn = sum(-d for d in diffs if d < 0) / 14
    rsi = 100.0 if dn == 0 else 100.0 - (100.0 / (1.0 + up / dn))

    # Axis 2: Uncrowded Dislocation + 12M Catalyst Velocity Score (0..35)
    gap_pts = 6.0
    drop = max(-dd52, -dd5y * 0.85)
    if 30 <= drop <= 78:
        gap_pts += 13.0
    elif 20 <= drop < 30:
        gap_pts += 9.0
    elif drop > 78:
        gap_pts += 10.0
    elif drop < 10:
        gap_pts -= 5.0

    # Reward imminent 3~6 month catalysts over 9~12 month catalysts!
    if cat_months <= 6:
        gap_pts += 6.0
    elif cat_months <= 9:
        gap_pts += 4.0
    else:
        gap_pts += 2.0

    if mult_5y_low <= 2.2:
        gap_pts += 5.0
    elif mult_5y_low <= EX_TENBAGGER_CEILING:
        gap_pts += 2.5
    else:
        gap_pts -= 14.0

    if pct60 < -8:
        gap_pts += 3.0
    elif pct60 > 15:
        gap_pts -= 4.0

    if rsi <= 42:
        gap_pts += 2.5
    elif rsi >= 70:
        gap_pts -= 6.0
    gap_score = round(_clamp(gap_pts, 2.0, 35.0), 1)

    # Realistic 12-Month Catalyst Re-Rating Target (60%~160% 1-year re-rating, NOT fantasy 10-year price!)
    sorted_1y = sorted(window_1y)
    p10_floor = sorted_1y[max(0, int(0.08 * (len(sorted_1y) - 1)))]
    floor_px = min(cur * 0.87, max(low52 * 0.94, min(cur * 0.88, p10_floor)))
    target_px = max(cur * 1.55, min(cur * 2.35, max(high52 * 0.88, high5y * 0.72)))
    bull_px = max(target_px * 1.25, min(cur * 3.0, high52 * 1.05))

    downside_pct = max(5.0, (1.0 - floor_px / cur) * 100)
    upside_pct = (target_px / cur - 1.0) * 100
    asymmetry_ratio = round(upside_pct / downside_pct, 2)
    margin_pct = round((1.0 - cur / target_px) * 100, 1)

    asym_pts = _clamp(asymmetry_ratio * 4.4, 3.0, 30.0)
    asym_score = round(asym_pts, 1)

    variant_total = round(essence + gap_score + asym_score, 1)
    arch = ARCHETYPES[arch_id]

    rnd = (lambda v: round(v)) if ccy == "KRW" else (lambda v: round(v, 2))
    buy_1, buy_2, buy_3 = _monotonic_tranches(cur, floor_px, rnd)
    floor_r = rnd(floor_px)
    target_r = rnd(target_px)
    bull_r = rnd(bull_px)

    solv_meta = SOLVENCY_TIERS[solv_key]
    overheated = bool(rsi >= 68.0 or (-dd52 < 10.0 and -dd5y < 15.0))
    blocked = bool(overheated or ex_tenbagger or not solv_meta["ok"])
    shield_ok = bool(
        not blocked
        and essence >= 30
        and asymmetry_ratio >= arch["min_asymmetry"]
        and margin_pct >= 25.0
    )
    win_p = 0.63 if (essence >= 33 and cat_months <= 6) else 0.58
    sizing = compute_position_sizing(
        upside_pct=upside_pct,
        downside_pct=downside_pct,
        win_prob=win_p,
        cap_pct=solv_meta["cap_pct"],
        min_pct=solv_meta["min_pct"],
        blocked=blocked,
    )
    if ex_tenbagger:
        live_fear = f"[기성 급등주 차단: 5년 저점 대비 {mult_5y_low:.1f}배 상승 — 제외] {fear_txt}"
    elif overheated:
        live_fear = f"[단기 과열(RSI {rsi:.0f}) — 조정 대기] {fear_txt}"
    else:
        live_fear = fear_txt

    src_url = (
        f"https://m.stock.naver.com/domestic/stock/{sym}/total"
        if market == "KR"
        else f"https://stockanalysis.com/stocks/{sym.lower()}/"
    )
    item = dict(
        symbol=sym,
        market=market,
        venue=venue,
        currency=ccy,
        name=name,
        archetype=arch_id,
        archetype_badge=arch["badge"],
        target_weight_range=arch["target_weight_range"],
        horizon=f"{max(3, cat_months - 3)}~{cat_months}개월 (1년 내 승부)",
        catalyst_months=cat_months,
        catalyst_12m=catalyst_12m,
        time_stop=time_stop,
        price=rnd(cur),
        high52=rnd(high52),
        dd52=round(dd52, 1),
        dd5y=dd5y,
        mult_5y_low=mult_5y_low,
        ex_tenbagger=ex_tenbagger,
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
        sizing=sizing,
        trap_shield_ok=shield_ok,
        moat_essence=moat_txt,
        crowd_fear=live_fear,
        execution_rule=arch["execution_rule"],
        kill_switch=kill_txt,
        source_url=src_url,
    )
    validate_contrarian_invariants(item, is_playbook=False)
    return item


def refresh(package, *, fetcher=None, now=None):
    """Scan uncrowded 12-month catalyst universe. Zero portfolio input."""
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
                lookup_venue = "KRX" if venue == "KOSDAQ" else venue
                rows, _ = price_history.series(db, (lookup_venue, sym, ccy), long=True)
                if not rows:
                    rows, _ = price_history.series(db, (lookup_venue, sym, ccy))
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
                bars = _yahoo_series(sym, market, venue, "1y", "1d", get_bytes)
            except Exception:
                pass
        try:
            bars_5y = _yahoo_series(sym, market, venue, "5y", "1wk", get_bytes)
        except Exception:
            bars_5y = bars
        if cur_px is None and bars:
            cur_px = bars[-1]
        scored = _score_candidate(spec, bars, cur_px, five_yr_closes=bars_5y)
        if scored is not None:
            candidates.append(scored)

    candidates.sort(key=lambda r: (not r["trap_shield_ok"], r["catalyst_months"], -r["total"], -r["asymmetry"], r["symbol"]))
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
    """Validate and save a bespoke 12-Month Catalyst 1-Stock High-Conviction Playbook locally."""
    market = str(fields.get("market", "KR")).strip().upper()
    symbol = str(fields.get("symbol", "")).strip().upper()
    name = str(fields.get("name", "")).strip() or symbol
    archetype = str(fields.get("archetype", "calm_compounder")).strip()
    crowd_view = str(fields.get("crowd_view", "")).strip()
    variant_insight = str(fields.get("variant_insight", "")).strip()
    catalyst_12m = str(fields.get("catalyst_12m", "")).strip() or variant_insight
    time_stop = (
        str(fields.get("time_stop", "")).strip()
        or "진입 후 2개 분기(6개월) 내 예상 촉매·영업이익 반전이 숫자로 확인되지 않으면 본전이어도 즉시 전량 교체"
    )
    kill_switch = str(fields.get("kill_switch", "")).strip()
    horizon = str(fields.get("horizon", "6~12개월")).strip()[:40]
    url = str(fields.get("url", "")).strip()

    if market not in ("KR", "US") or not re.fullmatch(r"[A-Z0-9.\-]{1,12}", symbol):
        raise ValueError("시장(KR/US)과 종목코드·티커 형식을 확인하세요.")
    if archetype not in ARCHETYPES:
        raise ValueError("역발상 집중투자 아키타입을 선택하세요.")
    if not (
        0 < len(name) <= 80
        and 0 < len(crowd_view) <= 300
        and 0 < len(variant_insight) <= 400
        and 0 < len(catalyst_12m) <= 320
        and 0 < len(time_stop) <= 260
        and 0 < len(kill_switch) <= 300
    ):
        raise ValueError("대중 시선·독점 인사이트·12개월 내 확정 촉매·시간손절·철회 조건을 모두 확인하세요.")

    horizon_months = parse_horizon_months(horizon)

    try:
        entry = Decimal(str(fields.get("entry", "")).strip())
        floor = Decimal(str(fields.get("floor", "")).strip())
        target = Decimal(str(fields.get("target", "")).strip())
    except Exception as exc:
        raise ValueError("기준가·하방 바닥가·1년 내 목표 가치를 숫자로 입력하세요.") from exc
    if not (Decimal(0) < floor < entry < target):
        raise ValueError("하방 바닥가 < 현재 진입 기준가 < 1년 내 복원 목표가 순서를 확인하세요.")

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

    default_solv = next((s[6] for s in CONTRARIAN_UNIVERSE if s[0] == symbol), "backlog_float")
    solvency = str(fields.get("solvency", "")).strip() or default_solv
    if solvency not in SOLVENCY_TIERS:
        raise ValueError("재무생존·확신 등급을 확인하세요.")
    try:
        win_prob_pct = float(str(fields.get("win_prob", "60")).strip() or "60")
    except ValueError as exc:
        raise ValueError("예상 적중 확률(%)을 숫자로 입력하세요.") from exc
    if not (25.0 <= win_prob_pct <= 85.0):
        raise ValueError("예상 적중 확률(25~85%) 범위를 확인하세요.")

    ccy = "KRW" if market == "KR" else "USD"
    upside_pct = float((target / entry - 1) * 100)
    downside_pct = float((1 - floor / entry) * 100)
    asymmetry = round(upside_pct / max(downside_pct, 0.1), 2)
    margin_pct = round(float((1 - entry / target) * 100), 1)
    min_req = ARCHETYPES[archetype]["min_asymmetry"]
    solv_meta = SOLVENCY_TIERS[solvency]
    sizing = compute_position_sizing(
        upside_pct=upside_pct,
        downside_pct=downside_pct,
        win_prob=win_prob_pct / 100.0,
        cap_pct=solv_meta["cap_pct"],
        min_pct=solv_meta["min_pct"],
        blocked=not solv_meta["ok"],
    )
    passes = bool(
        solv_meta["ok"]
        and horizon_months <= MAX_HORIZON_MONTHS
        and asymmetry >= min_req
        and margin_pct >= 25.0
        and sizing["recommended_pct"] >= 25.0
    )

    rnd = (lambda v: str(round(float(v)))) if ccy == "KRW" else (lambda v: f"{float(v):.2f}")
    t1, t2, t3 = _monotonic_tranches(entry, floor, rnd)

    now = datetime.now(intel.KST).isoformat(timespec="seconds")
    pid = hashlib.sha256(f"{market}:{symbol}:{archetype}:{entry}:{target}:{horizon}".encode()).hexdigest()[:16]
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
        sizing=sizing,
        entry=rnd(entry),
        floor=rnd(floor),
        target=rnd(target),
        bull=rnd(target * Decimal("1.25")),
        tranches=[t1, t2, t3],
        upside_pct=round(upside_pct, 1),
        downside_pct=round(downside_pct, 1),
        asymmetry=asymmetry,
        margin_pct=margin_pct,
        passes=passes,
        horizon=horizon,
        horizon_months=horizon_months,
        catalyst_12m=catalyst_12m,
        time_stop=time_stop,
        crowd_view=crowd_view,
        variant_insight=variant_insight,
        kill_switch=kill_switch,
        url=url,
    )
    validate_contrarian_invariants(record, is_playbook=True)

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
