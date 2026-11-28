"""Public contrarian variant-perception scanner and 12-month catalyst-driven 2-pick concentrated engine.
Never accepts personal portfolio holdings in public collection.
Enforces hard empirical & CoT anti-regression invariants:
  1. Zero single-digit dilution AND zero >50% Full-Kelly single-stock overbetting (Half-Kelly 25% ~ 50% per leg across 2 uncorrelated catalysts, else 0% pass).
  2. Zero ex-post tenbagger hindsight bias (5-year trough multiple <= 3.6x).
  3. Zero multi-year 'buy & hope' dead-money traps (target horizon <= 12M + Piotroski Expectation-Error filter + 3M check-in & 6M Time-Stop)."""

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
MIN_SINGLE_WEIGHT_PCT = 25.0
MAX_SINGLE_WEIGHT_PCT = 50.0

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
        track_record="2023.03 17억 원 → 2026 상반기 4,467억 원 (10년 존버가 아니라 단 3년 만에 260배 달성! 매 분기 수출·영업레버리지가 즉시 찍히는 최선호 2~3종목 압축 회전)",
        core_quote="“막연히 5년 뒤를 기다리지 않는다. 당장 이번~다음 분기 수출 통관과 영업이익률이 폭발하는데 시장만 편견으로 못 보는 1등 사업에 압축 집중한다.”",
        crowd_blindspot="대중은 내수·과거 선입견에 갇혀 이미 해외 인허가·채널 진입이 끝나 향후 2~4분기 내 고마진 매출이 찍히기 직전인 중형 독점주를 외면함",
        edge_formula="향후 3~12개월 내 해외 본판매·소모품 레버리지 확정 + Piotroski 기대오차 3점 무차입 1등 기업에 Half-Kelly 35%~50% 투입",
        execution_rule="Half-Kelly 단일 상한 50% (한·미 2종목 압축) · 3개월 1차 숫자 점검(역주행 시 즉시 컷) · 6개월 본 Time-Stop",
        min_asymmetry=3.5,
        target_weight_range="35% ~ 50% (Half-Kelly · 2종목 압축)",
        max_months=12,
        horizon="6~12개월",
        sources=(
            ("캄투자일임 3년 고속 복리 운용 구조 보도 (딜사이트)", "https://dealsite.co.kr/"),
            ("한국경제 집중투자 인터뷰 원문", "https://www.hankyung.com/"),
        ),
    ),
    "druckenmiller_inflection": dict(
        id="druckenmiller_inflection",
        badge="드러큰밀러·스타인하트형 · 6~12개월 변곡점 압축",
        master="스탠리 드러큰밀러 (Duquesne) & 마이클 스타인하트 (Variant Perception 창시자)",
        track_record="드러큰밀러 30년 연평균 30%(무손실) · 스타인하트 연 24.5% — 현재 최악의 악재 직후 ‘6~12개월 뒤 수급·실적 변곡점’에 Half-Kelly 상한 50%씩 최선호 2축 집중",
        core_quote="“현재 실적은 최악이지만 6~12개월 뒤 산업 수급이 정반대로 뒤집히는 순간이 보이면 집중하고, 예상 시점에 숫자가 안 찍히면 미련 없이 시간손절하라.”",
        crowd_blindspot="대중은 직전 분기 재고조정·파업·정책 루머를 영구적 재앙으로 착각해 투매하지만, 실제 재고 소진·정책 확정 변곡점은 2~3분기 안에 도래함",
        edge_formula="재고조정 종료·관세/규제 확정 등 6~12개월 내 방향 전환 촉매가 명확한 독점주에 Half-Kelly 35%~50% 선제 타격",
        execution_rule="소액 정찰 금지 · 3개월 1차 선행지표 역주행 시 조기 철수 · 6개월(2개 분기) 무반응 시 본전이어도 본 Time-Stop",
        min_asymmetry=4.0,
        target_weight_range="35% ~ 50% (Half-Kelly · 2종목 압축)",
        max_months=12,
        horizon="6~12개월",
        sources=(
            ("NBER ‘Best Ideas’ 최고 확신 종목 알파 논문", "https://www.nber.org/papers/w15012"),
            ("Morgan Stanley ‘Expectations Investing & Variant Perception’", "https://www.morganstanley.com/im/"),
        ),
    ),
    "greenblatt_catalyst": dict(
        id="greenblatt_catalyst",
        badge="그린블란트·테퍼형 · 확정 이벤트 특수상황 집중",
        master="조엘 그린블란트 (Gotham Capital 연 50%) & 데이비드 테퍼 (Appaloosa)",
        track_record="그린블란트 고담캐피탈 10년(1985~1994) 연복리 50% 달성 · 만년 저평가 단순 가치주 대신 ‘날짜가 박힌 강제 재평가 촉매(Special Situations)’ 2~3개 축 압축",
        core_quote="“촉매 없는 저평가주는 5년 동안 쌀 수 있다. 기관 강제투매 종료·요율 자동 인상·신제품 승인처럼 1년 안에 시장이 재평가할 수밖에 없는 이벤트에만 집중하라.”",
        crowd_blindspot="합병 일회성 비용·정부 요율 반영 시차·인덱스 리밸런싱 등 ‘일시적 제도/회계 왜곡’으로 폭락한 주식을 구조적 쇠퇴로 오인함",
        edge_formula="일시적 회계/제도 왜곡 해소 날짜가 향후 3~12개월 내로 확정된 순현금·고ROIC 기업에 Half-Kelly 32%~45% 집중",
        execution_rule="이벤트 발효 분기까지 집중 보유 · 3개월 점검 + 6개월 본 Time-Stop · 목표 달성 시 즉시 현금화 회전",
        min_asymmetry=4.0,
        target_weight_range="32% ~ 45% (Half-Kelly · 2~3종목)",
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
        track_record="레거시 업황 침체로 주가가 반토막 난 바닥에서 ‘향후 2~4분기 내 확정된 고객사 신규 팹·선단공정 반입(PO) 스케줄’과 백로그 급증을 보고 독점 병목 선점",
        core_quote="“5년을 기다리는 게 아니다. 고객사 신규 라인 장비·소재 발주 시점보다 딱 2분기 앞서 공포 바닥에서 모으면 1년 안에 실적이 주가를 강제로 끌어올린다.”",
        crowd_blindspot="전방 레거시 감익 백미러만 보고 투매하느라 이미 찍히기 시작한 사상 최대 수주잔고($1.3B·6,300억 등)와 2분기 뒤 2배 증설 가동을 놓침",
        edge_formula="미개화 중형 병목 독점주(5년 저점 ≤3.6배) + 수주잔고·마진 동시 개선(Piotroski 3/3) 종목에 Half-Kelly 35%~50% 투입",
        execution_rule="발주 1~2분기 전 바닥 3단 매집 · 3개월 수주/통관 점검 · 6개월 영업레버리지 미발생 시 시간손절 교체",
        min_asymmetry=4.0,
        target_weight_range="35% ~ 50% (Half-Kelly · 병목 압축)",
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
        track_record="마이클 버리 13F 실증 분석 결과 5~10년 장기보유가 아니라, 패시브 투매 극점 진입 후 6~12개월 내 자사주 소각(Ikenberry 1995)·실적 반전 시 즉시 수확·교체",
        core_quote="“길가에 버려진 순현금 자산을 사되 영원히 끌어안지 않는다. 자사주 소각과 공포 소멸로 1년 안에 평균회귀가 일어나면 즉시 차익을 확정한다.”",
        crowd_blindspot="극단적 혐오 투매로 주가가 순현금·청산가치까지 밀렸는데 회사가 매년 유통주식의 8~12%를 소각하며 주당가치를 강제로 끌어올리는 효과를 무시함",
        edge_formula="고점 대비 -45%~-75% 투매 + 대규모 자사주 소각·순현금 방어막 가동 종목에 Half-Kelly 30%~45% 스나이퍼 투입",
        execution_rule="3개월 자사주/마진 점검 + 6개월 본 Time-Stop · Ikenberry(1995) 가치주 소각 12개월 표류 수확",
        min_asymmetry=4.5,
        target_weight_range="30% ~ 45% (Half-Kelly · 2~3종목)",
        max_months=12,
        horizon="6~12개월",
        sources=(
            ("SEC EDGAR Scion Asset Management 분기별 13F 회전 기록", "https://www.sec.gov/edgar/searchedgar/companysearch"),
            ("Ikenberry·Lakonishok·Vermaelen (1995) 저평가 자사주 소각 논문", "https://www.sciencedirect.com/science/article/abs/pii/0304405X9500826Z"),
        ),
    ),
    "pabrai_dhandho": dict(
        id="pabrai_dhandho",
        badge="애크먼·파브라이형 · 불확실성 해소 데드라인 켈리 타격",
        master="빌 애크먼 (Pershing Square) & 모니시 파브라이 (Dhandho Half-Kelly)",
        track_record="소송·임상/FDA 허가·단기 유동성 오해 등 ‘불확실성이 걷히는 날짜(Deadline ≤ 12개월)’가 정해진 하방 고정 기회에 Half-Kelly로 25~45% 집중 타격",
        core_quote="“안개가 영원히 끼어 있을 주식은 사지 마라. 1년 안에 안개가 걷히는 확정 이벤트가 있고 하방이 막혀 있을 때 Half-Kelly로 단단히 베팅하라.”",
        crowd_blindspot="규제·임상·수주 전환 결과를 기다리기 싫어하는 단기 펀드들이 확정 이벤트 직전 1~2분기에 최저가로 주식을 던짐",
        edge_formula="하방 순현금·기존 캐시카우로 손실폭 고정 + 12개월 내 인허가·로열티·옵션 데드라인 존재 종목에 Half-Kelly 25%~45% 베팅",
        execution_rule="3개월 임상/처방 중간 점검 + 6개월 본 Time-Stop · 데드라인 지연·기각 공시 시 당일 즉시 철회",
        min_asymmetry=4.5,
        target_weight_range="25% ~ 45% (Half-Kelly · 이벤트 스나이퍼)",
        max_months=12,
        horizon="3~12개월",
        sources=(
            ("MacLean·Thorp·Ziemba Half-Kelly (성장 75%·분산 50% 감축) 원전", "https://www.princeton.edu/~wbialek/rome/refs/kelly_56.pdf"),
            ("Pershing Square 집중 카탈리스트 연구", "https://pershingsquareholdings.com/"),
        ),
    ),
}

ACADEMIC_RESEARCH = (
    dict(
        title="Half-Kelly (성장률 75% 보존 · 변동성 50% 축소) & Skewness 방어 (2종목 압축)",
        authors="MacLean·Thorp·Ziemba (The Kelly Criterion) & Bessembinder (2018, JFE · 26,000종목)",
        finding=(
            "기대수익률(μ) 추정오차는 분산(σ²) 오차보다 10~20배 치명적이어서 Full Kelly(75%) 과베팅 시 파산·급락 위험이 급증합니다. "
            "Half-Kelly(k=0.5)는 이론 최대 복리성장률의 75%(2k−k²)를 그대로 지키면서 변동성을 50% 줄입니다. "
            "또한 Bessembinder(2018) 실증상 무작위 1종목 보유는 73% 확률로 국채에 패배하므로 서로 다른 촉매 축의 최선호 2종목(각 ≤50%)으로 우측 왜도 위험을 방어해야 합니다."
        ),
        url="https://www.princeton.edu/~wbialek/rome/refs/kelly_56.pdf",
    ),
    dict(
        title="Best Ideas (최우선 1~2종목 연 +2.8~4.5% 알파) & 개인 1~2종목 정보우위 실증",
        authors="Antón·Cohen·Polk·Silli (2010/2021, NBER/JFE) & Ivković·Sialm·Weisbenner (2008, JFQA)",
        finding=(
            "펀드매니저의 최우선 확신 종목(Best Ideas)은 12개월까지 연 +2.8%~+4.5%(분기 1~2.5%) 초과수익을 내지만 3~20순위로 갈수록 알파가 급락합니다. "
            "개인 계좌 역시 지수 비편입 중소형 니치 기업에 대한 정보우위가 있는 1~2종목 집중군이 분산군을 압도했습니다(단, 분산 증가 억제를 위해 2종목 압축 + Half-Kelly가 최적)."
        ),
        url="https://www.nber.org/papers/w15012",
    ),
    dict(
        title="Piotroski 기대오차 (가치함정 57% 차단 & 실적발표 3일 내 연간 알파 1/6 분출)",
        authors="Piotroski (2000, JAR) & Piotroski·So (2012, Review of Financial Studies)",
        finding=(
            "단순 저PBR 가치주의 약 57%는 끝없이 싼 가치함정(Value Trap)입니다. 재무·영업이익률·현금흐름이 실제로 개선 중인 F-Score 상위(비관적 기대오차) 종목만 "
            "12개월 +7%~+23% 초과수익을 내며, 이 연간 알파의 약 1/6(16.5%)이 후속 4번의 분기 실적발표 전후 3영업일에 집중 분출됩니다."
        ),
        url="https://academic.oup.com/rfs/article-abstract/25/9/2841/1593152",
    ),
    dict(
        title="왜 3개월 칼손절이 아니라 ‘6개월 본 Time-Stop + 3개월 숫자 점검’인가?",
        authors="Bernard·Thomas (1989/1990 PEAD) · Frazzini (2006 Disposition) · Chan·Jegadeesh·Lakonishok (1996) · López de Prado",
        finding=(
            "실적 서프라이즈 표류(PEAD)는 3개 분기(약 9개월)에 걸쳐 진행되다 4분기째 역전되며, 고점 대비 폭락주(음의 자본이득 오버행)는 본전 매물 소화로 초기 1~3개월 반응이 지연됩니다(Frazzini). "
            "Kaminski·Lo(2014)와 Chan et al.(1996)을 결합한 결론은 6~12개월 정보확산 창 내에서 ‘3개월 차 실적 역주행만 조기 컷하고 6개월(2개 분기) 본 수직장벽(Time-Stop) 도달 시 무반응 자본을 강제 교체’하는 2단계 규율입니다."
        ),
        url="https://repec.org/",
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
        ("목표 보유 호흡", "추세 꺾일 때까지 보유 (/discover)", "5~10년 존버 절대 금지! ‘3~12개월 내’ 승부 + ‘3개월 1차 숫자 점검 · 6개월 본 Time-Stop’ 2단계 규율"),
        ("종목 선정 필수 관문", "현재 수급·차트 정배열 우위", "미개화 바닥(5년저점 ≤3.6배) + ‘12개월 내 확정 촉매’ + ‘Piotroski 기대오차(수익성·현금흐름 개선)’ 필수"),
        ("포지션 비중 철학", "종목당 10~20% 분산", "Half-Kelly (성장률 75% 보존 · 변동성 50% 감축) 기준 서로 다른 2종목 각 25%~50% 압축 (5% 분산 · 75% 몰빵 모두 배제)"),
        ("가장 경계할 실패", "고점 추격 후 눌림 손실", "① 기성 텐베거 뒷북 매수, ② 촉매 없는 만년 저PBR 시간함정(Dead Money), ③ 단일 종목 μ 추정오차 과베팅"),
    ),
)

SOLVENCY_TIERS = {
    "net_cash": dict(
        label="S급 재무요새 · 무차입 순현금·고마진 FCF (Half-Kelly 38~50% 최선호 2축 적격)",
        cap_pct=50.0,
        min_pct=38.0,
        portfolio_guide="Half-Kelly 2종목 압축 중 1축 · 3M 점검 + 6M Time-Stop",
        ok=True,
    ),
    "backlog_float": dict(
        label="A급 확정수주·현금흐름 · 선수금·영업흑자 건전 (Half-Kelly 32~45% 주력 적격)",
        cap_pct=45.0,
        min_pct=32.0,
        portfolio_guide="Half-Kelly 2~3종목 압축 · 3M 점검 + 6M Time-Stop",
        ok=True,
    ),
    "turnaround_watch": dict(
        label="B급 턴어라운드 · 12개월 내 흑자/레버리지 촉매 임박 (Half-Kelly 25~35% 적격)",
        cap_pct=35.0,
        min_pct=25.0,
        portfolio_guide="Half-Kelly 3종목 이내 · 3개월 분기 반전 미확인 시 즉시 철수",
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

# 5-Axis Non-Financial & Structural Risk Audit (Owner · Succession · Government/DAPA · Sector Peak · Global/Tariff/Debt)
GOVERNANCE_TIERS = {
    "G0": dict(label="G0 청정 · 오너·승계·정부 5대 리스크 낮음 (Half-Kelly 상한 50% 유지)", penalty=0.0, cap_pct=50.0),
    "G1": dict(label="G1 주의 · 단일 거버넌스·규제·부채 유의 (-4점 · 단일 상한 35%)", penalty=4.0, cap_pct=35.0),
    "G2": dict(label="G2 고위험 · 오너사익/승계장벽·정부규제/파업 중첩 (-10점 · 상한 25% 하드캡)", penalty=10.0, cap_pct=25.0),
}

GOVERNANCE_AUDIT = {
    "103140": (
        "G2",
        "오너(류진 회장 풍산홀딩스 388억 퇴직금·지주사 중심 배당환류) · 승계(장남 미국 국적 유지·방위사업법 승계장벽·매각설) · 정부(방사청 원가통제·수출허가·화약공정 중대재해처벌법) · 방산(종전 시 155mm 피크아웃) · 글로벌(구리 메탈로스 120억·미 PMC 수요 변동)",
    ),
    "058470": (
        "G2",
        "오너/승계(창업주 1950년생 2026년 9.18% ~7천억 블록딜·2세 승계 불확실 및 매각설) · 노사/규제(창사 48년 첫 무기한 파업 11월 타결 후 성과급 불씨 잔존)",
    ),
    "000100": (
        "G0",
        "유한재단 공익법인(15~16%) 지배 및 1969년 이래 평사원 출신 전문경영인 내부승계로 오너·승계 리스크 ZERO (FDA/EMA 승인 완료)",
    ),
    "259960": (
        "G1",
        "장병규 총수 대기업집단(사익편취 비상장 계열사 없음·9,000억 직접 소각)이나 인도 BGMI 과거 규제 차단·중국 텐센트/판호·단일 IP 의존 유의",
    ),
    "240810": (
        "G1",
        "원익홀딩스 지주계열 구조 및 삼성·하이닉스 국내 메모리 Capex 단일 주기 편중 리스크 유의",
    ),
    "214150": (
        "G1",
        "최대주주 베인캐피탈(PEF) 지분 엑시트 오버행 및 중국·미국 미용의료기기 인허가/수입통관 규제 유의",
    ),
    "145020": (
        "G1",
        "사모펀드 컨소시엄 지배구조 + 미국 보툴리눔 톡신 유통 파트너(CSO) 전환 과정 3Q26 영업익 -61.8% 일시 감속(Piotroski 2/3)",
    ),
    "014680": (
        "G1",
        "범삼성 조동혁 회장 지배·승계 과제 및 전방 반도체/배터리 고객사 단가 협상력 유의",
    ),
    "140860": (
        "G1",
        "창업주 지배체제 승계 과제 및 선단 파운드리 장비 발주 시기 연동성 유의",
    ),
    "298380": (
        "G1",
        "글로벌 빅파마 기술이전 옵션 행사 타이밍 의존 및 바이오 R&D 자금조달(희석) 경계",
    ),
    "ONTO": (
        "G0",
        "미국 독립 상장·기관 분산 지배(오너/승계 리스크 없음 · 무차입), 단 미·중 반도체 장비 수출통제 정책 체크",
    ),
    "ACLS": (
        "G0",
        "미국 독립 상장·기관 분산 지배(오너/승계 리스크 없음 · 무차입), 단 SiC/중국향 장비 통제 유의",
    ),
    "CELH": (
        "G0",
        "미국 독립 상장·PepsiCo 전략 파트너(지배구조 깔끔), 단 유통사 재고 정책 변경 노출",
    ),
    "LULU": (
        "G0",
        "북미 전문경영 상장사(거버넌스 청정), 단 2Q FY26 미주 -12% 펀더멘털 감속으로 Piotroski 1/3 차단",
    ),
    "FOUR": (
        "G1",
        "창업자 J. Isaacman NASA 국장 취임 사임 및 의결권 정리 완료(승계 해소), 단 3.7x 순부채 레버리지·Global Blue M&A 통합 리스크 유의",
    ),
    "FSLR": (
        "G1",
        "재무·지배구조 청정하나 미국 IRA Section 45X 세액공제·Section 232 관세 등 미국 정권/의회 정책 직결",
    ),
    "MOH": (
        "G1",
        "전문경영 상장사이나 미국 주정부 메디케이드 요율·연방 CMS/ACA 정치 예산에 100% 직결",
    ),
    "BABA": (
        "G1",
        "중국 빅테크 규제·VIE 지배구조·미중 관세/상장폐지 지정학 헤드라인 리스크 상존",
    ),
    "NVO": (
        "G1",
        "Novo Nordisk 재단 안정 지배(행동주의 방패) · 미 관세 면제 교환 확보, 단 TrumpRx/Medicare 약가 인하 및 Eli Lilly 복점 경쟁 유의",
    ),
    "CCJ": (
        "G1",
        "캐나다 분산 상장·서방 에너지 안보 수혜, 단 원전 인허가 규제 및 광산 환경/침수 리스크 유의",
    ),
}

# 20 High-Velocity 12-Month Catalyst Candidates verified against Q3 2026 filings & Piotroski Expectation Error (0..3)
# (sym, market, venue, ccy, name, arch_id, solv_key, essence[0..35], piotroski_3[1..3], cat_months[<=12], catalyst_12m, time_stop, moat_essence, crowd_fear, kill_switch)
CONTRARIAN_UNIVERSE = (
    # --- KOREA: 10 Uncrowded Gems with Hard 3~12 Month Catalysts ---
    ("058470", "KR", "KOSDAQ", "KRW", "리노공업", "hynix_bottleneck", "net_cash", 35, 3, 6,
     "3Q26 파업 일시 차질 종료 + 부산 에코델타시티(EDC) 2,000억 2배 신공장 하반기~상반기 본격 가동 및 빅테크 AI ASIC R&D 테스트 소켓 수주 폭발",
     "3M 1차 점검: 파업 종료 후 4Q 출하·OPM 45%+ 정상화 방향 확인 / 6M 본 Time-Stop: EDC 신공장 가동 매출·영업이익 전년비 증가 미확인 시 전량 교체",
     "3Q26 일시 파업 쇼크 속에서도 OPM 47.7%(394억)·누적 영업이익 1,602억(+17.3% YoY) 방어한 무차입 AI/R&D 소켓 독점 요새 (Piotroski 3/3)",
     "레거시 스마트폰 둔화 및 3Q26 일회성 파업 감익 뉴스로 52주 고점 대비 -59% 급락 (5년 저점 대비 2.1배)",
     "선단 피치 소켓 독점 점유율 이탈 또는 EDC 가동 후에도 분기 OPM 35% 하회 시"),
    ("240810", "KR", "KOSDAQ", "KRW", "원익IPS", "hynix_bottleneck", "backlog_float", 33, 3, 6,
     "3Q26 영업이익 667억(+262.6% QoQ)·OPM 19.8% 서프라이즈 + 4Q 이연 매출 300억 인식 + 약 6,300억 원 수주잔고의 선단 DRAM/HBM4 증착장비 순차 인도",
     "3M 1차 점검: 4Q 이연분 300억 인식 및 수주잔고 6,000억+ 유지 확인 / 6M 본 Time-Stop: 평택·선단 팹 PO 추가 발주 둔화 시 본전이어도 교체",
     "3Q26 매출 3,378억(+56% QoQ)·영업이익 667억(+142% YoY)으로 고정비 R&D 레버리지 구간 진입 완료 + 수주 6,300억 원 보유 (Piotroski 3/3 기대오차)",
     "과거 감산기 적자 기억 탓에 이미 폭발한 3Q26 실적 서프라이즈에도 고점 대비 -62% 소외",
     "삼성·하이닉스 선단 DRAM/HBM 설비 반입 전면 연기 또는 수주잔고 급감 시"),
    ("103140", "KR", "KRX", "KRW", "풍산", "hynix_bottleneck", "backlog_float", 34, 3, 6,
     "3Q26 영업이익 1,088억(+155.4% YoY)·방산 매출 3,316억(+75.8% QoQ) 실증 + 155mm 포탄 증설 CAPA 기반 4Q~상반기 이연 수출 물량 매출 인식",
     "3M 1차 점검: 중동/유럽 이연 선적 4Q 실제 통관 확인 / 6M 본 Time-Stop: 방산 분기 매출 3,000억 선 하회 및 마진 꺾임 시 즉시 교체",
     "글로벌 155mm 탄약 공급 병목(E_s≈0) + 3Q26 연결 매출 1.64조(+39.5% YoY)·영업이익 1,088억 서프라이즈 (Piotroski 3/3)",
     "메탈 손실(120억)과 단순 비철금속 굴뚝주 편견으로 고점 대비 -63% 폭락 (5년 저점 대비 2.0배)",
     "방산 수출 수주잔고 감소 전환 또는 장기 공급계약 해지 공시 시"),
    ("214150", "KR", "KOSDAQ", "KRW", "클래시스", "calm_compounder", "net_cash", 33, 2, 6,
     "12월 중국 ‘볼뉴머’ 인허가 예상 및 첫 선적 모멘텀 + 남미/일본 직영 전환 일회성 비용 소멸에 따른 분기 OPM(3Q 32.5% → 40%+) 복원 여부",
     "3M 1차 점검: 12월 중국 볼뉴머 허가·첫 선적 및 4Q OPM 반등 반드시 확인(미확인 시 조기 철수) / 6M 본 Time-Stop: 수출 마진 미복원 시 전량 교체",
     "무차입 순현금·카트리지 소모품 면도날 독점(누적 매출 2,757억 +13% YoY)이나, 3Q26 영업익 270억(-38.5% QoQ) 감속 통과 구간 (Piotroski 2/3 · 4Q 반전 필수)",
     "남미 직영 전환 비용과 3Q 감익 실망 매물로 52주 고점 대비 -69% 과매도 (5년 저점 대비 1.7배)",
     "중국 볼뉴머 허가 장기 무산 또는 4Q·1Q 연속 OPM 35% 미만 정체 시"),
    ("014680", "KR", "KRX", "KRW", "한솔케미칼", "druckenmiller_inflection", "backlog_float", 32, 3, 6,
     "향후 2~3분기 내 파운드리 2nm GAA 초기 양산 돌입 및 HBM 가동률 상승으로 초고순도 과산화수소·프리커서 출하량 즉각 반등",
     "3M 1차 점검: 분기 반도체 소재 매출비중·영업이익 전분기비 개선 여부 / 6M 본 Time-Stop: 소재 부문 분기 증익 미확인 시 시간손절",
     "TSMC·삼성·하이닉스 선단 공정 필수 초고순도 과산화수소·프리커서 과점 + 이차전지 기저 바닥 통과 (Piotroski 3/3)",
     "비주력 이차전지 소재 우려에 가려 52주 고점 대비 -43% 하락 (5년 저점 대비 2.1배)",
     "선단 파운드리향 핵심 소재 공급 점유율 축소 공시"),
    ("145020", "KR", "KRX", "KRW", "휴젤", "calm_compounder", "net_cash", 31, 2, 6,
     "미국 FDA 허가 이후 현지 파트너(CSO) 개편·기존 재고 정산(3Q26 영업익 181억 -61.8% 일시 감속) 마무리 및 향후 2~3분기 북미 재주문 반등 확인",
     "3M 1차 점검: 월별 톡신 북미향 통관 회복 및 4Q 영업익 정상화 확인(미확인 시 조기 철수) / 6M 본 Time-Stop: 연속 정체 시 교체",
     "국내 유일 미국·유럽·중국 3대 톡신 허가 완료 + 무차입 순현금 구조이나 3Q26 미국 파트너 개편 일시 감속 통과 중 (Piotroski 2/3 · 4Q 반전 필수)",
     "3Q26 북미 유통 개편 일시 감익과 소송 피로감으로 5년 고점 대비 -44% 아래 정체",
     "미국·중국 분기 수출액 역성장 고착 또는 FDA 품질 이슈 발생"),
    ("000100", "KR", "KRX", "KRW", "유한양행", "pabrai_dhandho", "backlog_float", 32, 3, 9,
     "향후 3~9개월 내 J&J 폐암 1차 치료제(렉라자+리브리반트) 글로벌 상업 처방 확대에 따른 단계별 출시 마일스톤 및 분기 로열티 현금 유입",
     "3M 1차 점검: J&J 분기별 리브리반트/라즈클루즈 글로벌 매출 트래킹 / 6M 본 Time-Stop: 로열티 유입 증가세 둔화 시 본전이어도 교체",
     "국내 전통 제약 본업이 하방을 지지하는 가운데 글로벌 블록버스터 순수 로열티(원가 0%)가 영업이익에 직결 (Piotroski 3/3)",
     "단기 차익매물과 바이오 섹터 변동성으로 52주 고점 대비 -29% 조정",
     "병용요법 글로벌 처방 점유율 부진 또는 중대 부작용 권고 변경"),
    ("140860", "KR", "KOSDAQ", "KRW", "파크시스템스", "hynix_bottleneck", "net_cash", 33, 3, 9,
     "향후 6~9개월 내 2nm 이하 게이트올어라운드(GAA) 및 HBM 하이브리드 본딩 수율 검사용 산업용 원자현미경(AFM) 신규 수주 집중",
     "3M 1차 점검: 분기 신규 수주잔고 및 산업용 AFM 출하 비율 확인 / 6M 본 Time-Stop: 수주잔고 성장률 둔화 시 즉시 교체",
     "비접촉 산업용 원자현미경(AFM) 전 세계 독점 지위(점유율 1위) · 미세화될수록 기존 광학계측을 대체하는 물리적 병목 (Piotroski 3/3)",
     "반도체 중소형 장비주 일괄 매도로 52주 고점 대비 -42% 하락 (5년 저점 대비 2.15배)",
     "글로벌 파운드리 선단 계측 공정 내 AFM 채택 지연 공시"),
    ("298380", "KR", "KOSDAQ", "KRW", "에이비엘바이오", "pabrai_dhandho", "backlog_float", 30, 2, 9,
     "향후 6~12개월 내 뇌혈관장벽(BBB) 투과 셔틀 플랫폼(Grabody-B) 글로벌 빅파마 추가 기술이전 및 기존 파트너 임상 단계 마일스톤 도래",
     "3M 1차 점검: 파트너사 임상 환자 투여·학회 일정 준수 여부 확인 / 6M~9M 본 Time-Stop: 기술이전·임상 마일스톤 지연 시 즉시 교체",
     "사노피 등에 검증된 퇴행성 뇌질환 BBB 셔틀 원천 플랫폼 보유 · 계약금 기반 현금 확보 (Piotroski 2/3 · 마일스톤 의존)",
     "코스닥 바이오 투심 붕괴로 52주 고점 대비 -77% 폭락 (5년 저점 대비 2.9배)",
     "핵심 파트너사 임상 중단·권리 반환 공시 또는 주주배정 유상증자"),
    ("259960", "KR", "KRX", "KRW", "크래프톤", "greenblatt_catalyst", "net_cash", 32, 3, 6,
     "향후 2~3분기 대형 신작 글로벌 정식 출시 성적표 확인 + 기존 PUBG 분기 영업이익 성장 및 자사주 환원으로 ‘단일 IP 할인’ 강제 해소",
     "3M 1차 점검: PUBG 월간 트래픽·신작 CBT/출시 반응 데이터 점검 / 6M 본 Time-Stop: 신작 출시 후 동접 부진 및 영업이익 정체 시 교체",
     "수조 원 순현금 하방 요새 위에서 고마진 현금을 창출하며 신작 옵션을 공짜로 가진 비대칭 구조 (Piotroski 3/3)",
     "신작 출시 전 막연한 우려로 5년 고점 대비 -58% 아래(5년 저점 대비 1.4배) 저평가",
     "핵심 IP 분기 매출 15%+ 역성장 또는 대규모 적자 M&A 강행"),

    # --- US: 10 Uncrowded Gems with Hard 3~12 Month Catalysts ---
    ("ONTO", "US", "NYSE", "USD", "Onto Innovation", "hynix_bottleneck", "net_cash", 35, 3, 6,
     "3Q26 매출 사상최대 $410M(+88% YoY)·GPM 57.6%·수주잔고 $1.3B(+20% QoQ) 실증 완료 + 4Q 가이던스 $430~450M 및 2027년 Dragonfly G5 매출 2배 PO 확보",
     "3M 1차 점검: 4Q 매출 $430~450M 가이던스 달성 및 Dragonfly G5 고객사 10개+ 추가 납품 확인 / 6M 본 Time-Stop: 패키징 수주잔고 꺾임 시 즉시 교체",
     "3Q26 사상 최대 실적($410M·Non-GAAP EPS $2.44) + HBM4/CoWoS 수주잔고 $1.3B 폭발 중인 무차입 순현금 독점주 (Piotroski 3/3 최고 기대오차)",
     "반도체 장비 섹터 일괄 매도로 매출 +88% 폭발 직전에도 52주 고점 대비 -53% 폭락 (5년 저점 3.0배)",
     "핵심 파운드리·HBM 고객사 Dragonfly G5 납품 취소 또는 총마진 52% 하회"),
    ("ACLS", "US", "NASDAQ", "USD", "Axcelis Technologies", "hynix_bottleneck", "net_cash", 33, 2, 9,
     "향후 6~12개월 내 800V AI 데이터센터 전력장치 및 200mm SiC 웨이퍼 팹 전환용 고온 이온주입 장비 수주 턴어라운드",
     "3M 1차 점검: 분기 수주잔고(Backlog) 바닥 횡보·반등 조짐 확인 / 6M 본 Time-Stop: 2개 분기 내 수주 바닥 반전 미확인 시 즉시 교체",
     "SiC 전력반도체 고온 이온주입(Purion) 독점 과점 + 무차입 순현금 재무요새(시총 $3B 중형주 · Piotroski 2/3 바닥 확인 중)",
     "단기 전기차 재고 조정 공포로 52주 고점 대비 -45% 반토막 (5년 저점 대비 2.4배)",
     "SiC 이온주입 시장 내 점유율 이탈 또는 분기 적자 전환"),
    ("CELH", "US", "NASDAQ", "USD", "Celsius Holdings", "druckenmiller_inflection", "net_cash", 31, 2, 6,
     "3Q26 Alani Nu $410M(+24% YoY)·순이익 $127M 흑자전환 뒤 4Q 기저효과($25M pull-forward) 통과 및 2027년 플래그십 CELSIUS 성장 복귀·해외 확장",
     "3M 1차 점검: 4Q 총마진(3Q 46.8%) 회복 및 Circana 스캐너 소매 판매율 반등 확인(악화 시 조기 철수) / 6M 본 Time-Stop: 매출 가속 실패 시 즉시 교체",
     "PepsiCo DSD 유통 점유(64.6%) + Alani Nu 급성장 합산 매출 $847M(+17% YoY) 달성, 단 3Q 총마진 -450bps 압축 구간 (Piotroski 2/3 · 마진 반전 확인 필수)",
     "본 브랜드(-6%) 감속과 4Q 가이던스 부담으로 5년 고점 대비 -68% 폭락 (5년 저점 2.1배)",
     "북미 소매 스캐너 점유율 2분기 연속 하락 및 총마진 45% 하회 고착 시"),
    ("FOUR", "US", "NYSE", "USD", "Shift4 Payments", "greenblatt_catalyst", "backlog_float", 33, 3, 6,
     "3Q26 조정 FCF $200M(+42% YoY) 사상 최대·$190M 자사주 소각 직후 2027-01-01 개시 신규 $1.0B 자사주 매입 프로그램(시총 ~25%) + Global Blue $70M 시너지 실현",
     "3M 1차 점검: 1/1 개시 $1B 자사주 매입 속도 및 GRLNF 성장률 확인 / 6M 본 Time-Stop: 연간 FCF 가이던스($465~475M) 하회 시 전량 교체",
     "3Q26 매출 $1.3B(+12%)·FCF $200M(+42% YoY) 및 20·60일선 정배열(+13.5% vs 60MA) 복귀 + 2027-01-01 $1B 소각 대기 (Piotroski 3/3 · SOXX 상관 0.00)",
     "여행/FX 환율 가이던스 소폭 하향 소음으로 5년 고점 대비 -62% 급락 (5년 저점 1.43배)",
     "대형 엔터프라이즈 가맹점 이탈 급증 또는 $1B 자사주 소각 프로그램 축소 시"),
    ("FSLR", "US", "NASDAQ", "USD", "First Solar", "druckenmiller_inflection", "net_cash", 33, 3, 6,
     "3Q26 총마진 58%(+20%p YoY)·순이익 $571M(+25%) 실증 위에서 44GW($13.5B) 장기 수주 인도 + $500M 자사주 매입 및 미 무역법 Section 232 반사수혜 본격화",
     "3M 1차 점검: 4Q 미국 모듈 출하 및 45X 세액공제 현금 수령 확인 / 6M 본 Time-Stop: 수주 단가(ASP) 훼손 시 즉시 교체",
     "미국 내 80% 생산기지 기반 45X 수혜(GPM 58%) + 44GW 백로그($13.5B) + 순현금 $500M 자사주 매입 (Piotroski 3/3)",
     "인도·해외 출하 가이던스 소폭 조정(-1GW) 공포에 52주 고점 대비 -53% 폭락 (5년 저점 2.3배)",
     "미국 제조 세액공제(45X) 전면 폐지 확정 또는 대규모 수주 계약 해지"),
    ("MOH", "US", "NYSE", "USD", "Molina Healthcare", "greenblatt_catalyst", "backlog_float", 32, 2, 6,
     "3Q26 Adj EPS $0.89 서프라이즈·FY26 최소 $5.25 바닥 확인 후 2027년 1월 메디케이드 요율 ~6~7% 리셋 + MAPD 적자사업 철수(+$1/sh)·$4/sh 마진 수확",
     "3M 1차 점검: 1월 1일 발효 주정부 메디케이드 최종 요율 인상률(6%+) 및 4Q MCR 93% 천장 확인 / 6M 본 Time-Stop: 신규 요율에도 MCR 악화 지속 시 즉시 교체",
     "마이클 버리 집중 보유 · 2027년 $9.50+/sh 수익 기반 구축 중인 메디케이드 복점 + 자사주 소각 (Piotroski 2/3 · MCR 92.9% 바닥 통과 중)",
     "4Q 플로리다 계약 초기 손실과 높은 MCR(92.9%)을 영구 훼손으로 오인해 5년 고점 대비 -51% 폭락 (5년 저점 1.5배)",
     "핵심 주정부 메디케이드 재계약 탈락 또는 2027 요율 5% 미만 하향 시"),
    ("LULU", "US", "NASDAQ", "USD", "Lululemon Athletica", "burry_asymmetry", "net_cash", 28, 1, 6,
     "2Q FY26 미주 동일매장매출 -12%·전체 매출 가이던스 -5~-7% 하향으로 펀더멘털 감속 중(신규 CEO 하이디 오닐 턴어라운드 및 3Q 실적 반전 확인 전 진입 보류)",
     "3M 1차 점검: 미주 동일매장매출 감소폭 -5% 이내 축소 확인 전까지 진입 보류 / 진입 후 6M 본 Time-Stop 적용",
     "무차입 순현금·국제 고성장에도 2Q FY26 미주 -12%·영업마진 18.8% 하락으로 Piotroski 기대오차 1/3점 하락(가치함정 경보로 자동 차단 대상)",
     "북미 성장 둔화 공포로 5년 고점 대비 -79% 폭락하며 5년 최저점(1.18배) 기록",
     "매출총이익률 55% 하회 또는 재고 덤핑 할인 고착화"),
    ("BABA", "US", "NYSE", "USD", "Alibaba Group", "burry_asymmetry", "net_cash", 32, 3, 6,
     "향후 2~3분기 내 AI 클라우드(Qwen) 기업향 매출 가속 + 연간 유통주식 8~10% 규모 자사주 소각·특별배당 현금 집행",
     "3M 1차 점검: 분기별 자사주 소각 금액·주식수 감소폭 및 클라우드 성장률 확인 / 6M 본 Time-Stop: 소각 둔화 또는 클라우드 역전 시 교체",
     "마이클 버리 집중 보유 · 막대한 순현금 하방 방어막 + 주당가치 10% 끌어올리는 자사주 소각 엔진 (Piotroski 3/3)",
     "중국 매크로 혐오로 고점 대비 -49% 폭락 (5년 저점 대비 1.4배 청산가치 수준)",
     "자사주 소각 중단 또는 핵심 커머스 잉여현금흐름 급감"),
    ("NVO", "US", "NYSE", "USD", "Novo Nordisk", "pabrai_dhandho", "backlog_float", 35, 3, 9,
     "3Q26 조정 영업이익 +27%(DKK 31.7B)·경구용 위고비 필 DKK 5.39B(미국 신규 처방 80%)로 FY26 가이던스 상향 확인 + 2027 초 CagriSema 및 Catalent 3개 공장 가동 램프업",
     "3M 1차 점검: 경구용 위고비 필 미국 처방 및 2027 초 CagriSema 허가 진행 추적 / 6M 본 Time-Stop: Catalent 증설 출하 가속 미확인 시 교체",
     "3Q 조정 영업이익 +27%·가이던스 상향·5년 최저점 1.16배 + 20·60일선 회복(w_down 0.39) + 풍산(방산)과 상관계수 -0.120인 최고 비대칭 축 (Piotroski 3/3)",
     "과거 약가 노이즈와 경쟁 우려로 5년 고점 대비 -71% 투매 후 5년 최저점(1.16배)에서 막 60일선 돌파 시작",
     "세마글루타이드 글로벌 처방 점유율 급감 또는 CagriSema 규제 중대 지연"),
    ("CCJ", "US", "NYSE", "USD", "Cameco", "druckenmiller_inflection", "backlog_float", 33, 3, 9,
     "러시아 농축우라늄 수입 금지 본격 발효 및 향후 6~12개월 내 서방 유틸리티·빅테크 원전 장기 우라늄 구매계약(Term) 체결 집중",
     "3M 1차 점검: 분기 장기 계약 단가(Term Price) 상승 및 신규 계약량 확인 / 6M~9M 본 Time-Stop: 장기 계약 수주 확대 미확인 시 교체",
     "서방권 유일 대형 고품위 우라늄 광산 + Westinghouse 연료주기 지분 결합 절대 공급 병목 (Piotroski 3/3)",
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
    """Hard runtime harness enforcing <=12M catalysts, Half-Kelly 2-stock cap (25~50%), and Anti-Hindsight (<=3.6x)."""
    h_months = parse_horizon_months(record_or_cand.get("horizon", ""))
    if h_months > MAX_HORIZON_MONTHS:
        raise ValueError("CoT 불변식 위반: 12개월 초과 보유 호흡은 허용되지 않습니다.")
    if not str(record_or_cand.get("catalyst_12m", "")).strip() or not str(record_or_cand.get("time_stop", "")).strip():
        raise ValueError("CoT 불변식 위반: 12개월 내 확정 촉매 일정과 시간손절(Time-Stop) 기준이 누락되었습니다.")
    sz = record_or_cand.get("sizing", {})
    rec_w = float(sz.get("recommended_pct", 0.0))
    if 0.0 < rec_w < MIN_SINGLE_WEIGHT_PCT:
        raise ValueError(f"CoT 불변식 위반: 한 자릿수·분산 비중({rec_w}%) 오염 감지. 통과 종목은 Half-Kelly 25~50%, 미달은 0% 기각이어야 합니다.")
    gov_tier = record_or_cand.get("gov_tier")
    gov_cap = GOVERNANCE_TIERS[gov_tier]["cap_pct"] if gov_tier in GOVERNANCE_TIERS else MAX_SINGLE_WEIGHT_PCT
    eff_limit = min(MAX_SINGLE_WEIGHT_PCT, gov_cap)
    if rec_w > eff_limit:
        raise ValueError(f"Half-Kelly/거버넌스 단일 상한({eff_limit:.0f}%) 초과 비중({rec_w}%) 금지: 5대 비재무 리스크·추정오차 상한을 준수해야 합니다.")
    if not is_playbook and record_or_cand.get("trap_shield_ok"):
        if record_or_cand.get("ex_tenbagger") or float(record_or_cand.get("mult_5y_low", 99.0)) > EX_TENBAGGER_CEILING:
            raise ValueError("CoT 불변식 위반: 기성 급등주(5년 저점 대비 >3.6배)가 통과 목록에 포함되었습니다.")


def compute_position_sizing(*, upside_pct, downside_pct, win_prob=0.60, cap_pct=50.0, min_pct=30.0, piotroski_3=3, blocked=False):
    """Half-Kelly 2-Pick Compression Sizing capped by solvency AND 5-axis governance risk tier (25%~50%, or <=25%/35% for G2/G1)."""
    eff_cap = min(MAX_SINGLE_WEIGHT_PCT, float(cap_pct))
    if blocked or eff_cap <= 0 or upside_pct <= 0 or downside_pct <= 0:
        return dict(
            kelly_full_pct=0.0,
            kelly_half_pct=0.0,
            kelly_quarter_pct=0.0,
            recommended_pct=0.0,
            cap_pct=max(0.0, round(eff_cap, 1)),
            grade_label="0% · 베팅 기각 (촉매·확신·생존 미달 시 5% 정찰도 금지)",
            portfolio_guide="매수 보류 (Pass)",
        )
    p = _clamp(float(win_prob), 0.25, 0.85)
    q = 1.0 - p
    b = max(float(upside_pct) / max(float(downside_pct), 1.0), 0.1)
    full_kelly = max(0.0, (p * b - q) / b) * 100.0
    half_kelly = full_kelly * 0.5
    if full_kelly < 18.0:
        return dict(
            kelly_full_pct=round(full_kelly, 1),
            kelly_half_pct=round(half_kelly, 1),
            kelly_quarter_pct=round(full_kelly * 0.25, 1),
            recommended_pct=0.0,
            cap_pct=round(eff_cap, 1),
            grade_label="0% · 1년 기대 우위 부족 (어중간한 분산 진입 금지)",
            portfolio_guide="추가 할인 또는 촉매 임박 대기",
        )
    eff_min = min(eff_cap, max(MIN_SINGLE_WEIGHT_PCT, float(min_pct)))
    blend_alpha = 0.55 if int(piotroski_3) >= 3 else 0.25
    slot_target = _clamp(half_kelly + max(0.0, eff_cap - half_kelly) * blend_alpha, eff_min, eff_cap)
    rec = round(min(slot_target, eff_cap), 1)
    if rec >= 43.0:
        grade = f"최선호 압축(Half-Kelly) · {rec:.0f}% (한·미 2종목 중 1축)"
        guide = "2종목 압축 배정 (1종목 상한 50%) · 3M 점검 + 6M Time-Stop"
    elif rec >= 34.0:
        grade = f"주력 압축(Half-Kelly) · {rec:.0f}% (서로 다른 촉매 2종목)"
        guide = "2~3종목 압축 배정 · 3M 점검 + 6M Time-Stop"
    else:
        grade = f"선발 집중(Half-Kelly) · {rec:.0f}% (2~3종목 이내)"
        guide = "촉매 확인 전 3개월 점검 연동 · 6M Time-Stop"
    return dict(
        kelly_full_pct=round(full_kelly, 1),
        kelly_half_pct=round(half_kelly, 1),
        kelly_quarter_pct=round(full_kelly * 0.25, 1),
        recommended_pct=rec,
        cap_pct=round(eff_cap, 1),
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
        sym, market, venue, ccy, name, arch_id, solv_key, essence, piotroski_3,
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

    gov_tier, gov_note = GOVERNANCE_AUDIT.get(sym, ("G1", "개별 거버넌스·규제·글로벌 공급망 리스크 표준 점검 대상"))
    gov_meta = GOVERNANCE_TIERS[gov_tier]
    variant_total = round(max(1.0, essence + gap_score + asym_score - gov_meta["penalty"]), 1)
    arch = ARCHETYPES[arch_id]

    rnd = (lambda v: round(v)) if ccy == "KRW" else (lambda v: round(v, 2))
    buy_1, buy_2, buy_3 = _monotonic_tranches(cur, floor_px, rnd)
    floor_r = rnd(floor_px)
    target_r = rnd(target_px)
    bull_r = rnd(bull_px)

    solv_meta = SOLVENCY_TIERS[solv_key]
    overheated = bool(rsi >= 68.0 or (-dd52 < 10.0 and -dd5y < 15.0))
    blocked = bool(overheated or ex_tenbagger or not solv_meta["ok"] or int(piotroski_3) < 2)
    shield_ok = bool(
        not blocked
        and int(piotroski_3) >= 2
        and essence >= 30
        and asymmetry_ratio >= arch["min_asymmetry"]
        and margin_pct >= 25.0
    )
    eff_cap_pct = min(solv_meta["cap_pct"], gov_meta["cap_pct"])
    win_p = 0.64 if (piotroski_3 >= 3 and essence >= 33 and cat_months <= 6) else (0.59 if piotroski_3 >= 3 else 0.55)
    sizing = compute_position_sizing(
        upside_pct=upside_pct,
        downside_pct=downside_pct,
        win_prob=win_p,
        cap_pct=eff_cap_pct,
        min_pct=min(solv_meta["min_pct"], eff_cap_pct),
        piotroski_3=piotroski_3,
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
        piotroski_3=int(piotroski_3),
        piotroski_label=(
            "Piotroski 3/3 · 기대오차(수익성·현금·백로그 동시 개선)"
            if int(piotroski_3) >= 3
            else (
                "Piotroski 2/3 · 마진/수주 과도기 (3개월 1차 실적 반등 필수)"
                if int(piotroski_3) == 2
                else "Piotroski 1/3 · 실적 감속 가치함정 경보 (신규 진입 차단)"
            )
        ),
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
        gov_tier=gov_tier,
        gov_label=gov_meta["label"],
        gov_note=gov_note,
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

    candidates.sort(key=lambda r: (not r["trap_shield_ok"], -r.get("piotroski_3", 2), r["catalyst_months"], -r["total"], -r["asymmetry"], r["symbol"]))
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
    default_fscore = next((s[8] for s in CONTRARIAN_UNIVERSE if s[0] == symbol), 2)
    default_gov, default_gov_note = GOVERNANCE_AUDIT.get(symbol, ("G1", "5대 비재무 리스크 표준 점검 대상"))
    solvency = str(fields.get("solvency", "")).strip() or default_solv
    if solvency not in SOLVENCY_TIERS:
        raise ValueError("재무생존·확신 등급을 확인하세요.")
    gov_tier = str(fields.get("gov_tier", "")).strip().upper() or default_gov
    if gov_tier not in GOVERNANCE_TIERS:
        raise ValueError("5대 비재무·거버넌스 리스크 등급(G0/G1/G2)을 확인하세요.")
    gov_note = str(fields.get("gov_note", "")).strip() or default_gov_note
    gov_meta = GOVERNANCE_TIERS[gov_tier]
    try:
        piotroski_3 = int(str(fields.get("piotroski_3", default_fscore)).strip() or default_fscore)
    except ValueError as exc:
        raise ValueError("Piotroski 기대오차 점수(1~3)를 확인하세요.") from exc
    if piotroski_3 not in (1, 2, 3):
        raise ValueError("Piotroski 기대오차 점수는 1~3점 범위여야 합니다.")
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
    eff_cap_pct = min(solv_meta["cap_pct"], gov_meta["cap_pct"])
    sizing = compute_position_sizing(
        upside_pct=upside_pct,
        downside_pct=downside_pct,
        win_prob=win_prob_pct / 100.0,
        cap_pct=eff_cap_pct,
        min_pct=min(solv_meta["min_pct"], eff_cap_pct),
        piotroski_3=piotroski_3,
        blocked=not solv_meta["ok"],
    )
    passes = bool(
        solv_meta["ok"]
        and piotroski_3 >= 2
        and horizon_months <= MAX_HORIZON_MONTHS
        and asymmetry >= min_req
        and margin_pct >= 25.0
        and MIN_SINGLE_WEIGHT_PCT <= sizing["recommended_pct"] <= min(MAX_SINGLE_WEIGHT_PCT, gov_meta["cap_pct"])
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
        gov_tier=gov_tier,
        gov_label=gov_meta["label"],
        gov_note=gov_note,
        piotroski_3=piotroski_3,
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
