"""Public contrarian variant-perception scanner and 1-stock high-conviction concentrated strategy engine.
Never accepts personal portfolio holdings in public collection.
Excludes ex-post tenbagger consensus mega-caps to discover uncrowded next-inflection gems."""

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

# Anti-Hindsight Guardrail: Stocks already >= 3.6x above 5-year trough have already re-rated; block from fresh tenbagger radar
EX_TENBAGGER_CEILING = 3.6

EX_TENBAGGER_GRADUATES = (
    ("HD현대일렉트릭 (267260)", "5년 저점 대비 최고 71.7배 (현재 ~24배)", "2021년 시총 6천억 적자 탈출기에 선점했어야 할 종목 · 현재는 전 시장 컨센서스"),
    ("효성중공업 (298040)", "5년 저점 대비 35.1배", "변압기 병목 리레이팅 기완성 · 조정 시 매수해도 재차 10배 불가"),
    ("SK하이닉스 (000660)", "2022년 적자 바닥 대비 최고 35.3배", "2022.11 적자 공포(7.5만 원) 때가 역발상 구간 · 현재는 대형 컨센서스 코어"),
    ("삼양식품 (003230)", "5년 저점 대비 최고 18.5배", "내수 라면주 편견이 깨지기 전(8만 원대)이 선점 구간 · 현재 고멀티플 안착"),
    ("한화에어로스페이스 (012450) · LIG넥스원", "5년 저점 대비 7.2배~20배+", "방산 수출 리레이팅 1차 사이클 기분출 (/discover 추세 영역으로 이관)"),
    ("NVIDIA · Broadcom · Eli Lilly", "시총 $1T~$3.5T 메가캡 기등극", "물리적 시가총액 한계상 향후 5~10배 텐베거 불가능 · 역발상 발굴 풀에서 제외"),
)

ARCHETYPES = {
    "calm_compounder": dict(
        id="calm_compounder",
        badge="이호걸형 · 무차입 초집중 복리",
        master="캄투자일임 이호걸 대표 아키타입 (질의 ‘김호걸’ → 공시 대표명 이호걸)",
        track_record="2023.03 자본금 17억 원 설립 → 차입 없이 고유재산 상장주식 1~3종목 Long-Only 초집중 복리로 2026 상반기 자기자본 4,467억 원(반기 순이익 3,303억 원) 달성",
        core_quote="“관세·금리 같은 매크로에 질 회사는 애초에 사지 않는다. 어설픈 20종목 분산 대신 흔들리지 않는 1등 사업 지분을 통째로 소유한다.”",
        crowd_blindspot="대중은 내수·전통 업종 선입견이나 단기 매크로 노이즈에 갇혀 중형 1등 기업의 해외 직판·소모품 영업레버리지 폭발 초입을 놓침",
        edge_formula="글로벌 가격결정력(ROIC > WACC) + 해외 확장 초입 중형 독점주를 매크로 급락기에 무차입 현물 40%~75% 초집중 매집 후 18~36개월 복리 동행",
        execution_rule="집중자본의 40~75%를 1~2종목에 압축 · 차트 노이즈 무손절 · 오직 해외 확장률·가격결정력 훼손 공시 때만 철회",
        min_asymmetry=3.5,
        target_weight_range="40% ~ 75% (1~2종목 초집중)",
        horizon="18~36개월",
        sources=(
            ("캄투자일임 자기자본·운용 구조 보도 (딜사이트)", "https://dealsite.co.kr/"),
            ("한국경제 집중투자 인터뷰 원문", "https://www.hankyung.com/"),
        ),
    ),
    "hynix_bottleneck": dict(
        id="hynix_bottleneck",
        badge="병목 선점형 · 적자/업황 착시 돌파",
        master="적자·불황 바닥 물리적 병목 선점 아키타입 (사용자 지칭 ‘한유백’ 유형 · 실명 공시 미특정 단서 명시)",
        track_record="2021~2022년 업황 적자·굴뚝주 멸시 바닥(PBR 0.6~0.9배)에서 차세대 독점 병목(소켓·특수소재·탄약·패키징 장비)을 남들보다 2~3분기 앞서 집중 선점",
        core_quote="“다수결 통계는 백미러(지난 분기 감익·역배열)를 보고 팔지만, 선구자는 앞유리(대체 불가능한 물리적 병목 E_s ≈ 0)를 보고 공포 바닥에서 승부를 건다.”",
        crowd_blindspot="레거시 사업부 둔화(과거 껍데기 V_Shell)에 가려 차세대 필수 병목 공정·소재(V_Core)의 독점 점유율과 이익 체질 전환을 보지 못함",
        edge_formula="아직 텐베거가 안 터진 중형 병목 독점주(5년 저점 대비 <3.5배)가 전방 업황 우려로 반토막 났을 때 집중자본 35%~60% 시간분할 매집",
        execution_rule="역배열 공포 구간 3회 분할 매집(기계적 -10% 손절 금지) · 병목 쇼티지 현실화 및 대중 만장일치 환호 구간에서 수확",
        min_asymmetry=4.0,
        target_weight_range="35% ~ 60% (1~3종목 집중)",
        horizon="12~24개월",
        sources=(
            ("금융감독원 DART 정기공시·수주잔고 원문", "https://dart.fss.or.kr/"),
            ("SEC EDGAR 반도체·산업재 설비 공시", "https://www.sec.gov/edgar/searchedgar/companysearch"),
        ),
    ),
    "burry_asymmetry": dict(
        id="burry_asymmetry",
        badge="마이클 버리형 · Roadkill 볼록성 집중",
        master="마이클 버리 (Michael Burry · Scion Asset Management)",
        track_record="패시브·알고리즘 강제투매로 길가에 버려진 자산(Roadkill) 중 순현금·자사주 소각 하방이 잠긴 소수 종목에 13F 포트폴리오 상위 25~45%씩 집중 베팅",
        core_quote="“나는 군중이 혐오하며 길가에 버린 자산(Roadkill)에서 사냥한다. 하방은 순현금으로 잠그고 상방은 4~10배 열려 있을 때 크게 베팅한다.”",
        crowd_blindspot="국가·섹터 혐오나 패시브 지수 리밸런싱이 기업의 막대한 순현금·잉여현금흐름(FCF)·연 8~10% 자사주 소각 능력을 무시하고 청산가치 이하로 짓누름",
        edge_formula="고점 대비 -40%~-75% 폭락 + 순현금/FCF 생존력 검증 종목에 집중자본 30%~50% 스나이퍼 투입",
        execution_rule="청산가치·역사적 지지선 매복 · 내재가치 평균회귀(+80%~+200%) 달성 시 미련 없이 수확해 다음 미개화 괴리로 회전",
        min_asymmetry=4.5,
        target_weight_range="30% ~ 50% (2~3종목 집중)",
        horizon="9~24개월",
        sources=(
            ("SEC EDGAR Scion Asset Management 13F 원문", "https://www.sec.gov/edgar/searchedgar/companysearch"),
            ("Moreira & Muir 변동성 강제청산 미시구조 논문", "https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf"),
        ),
    ),
    "druckenmiller_inflection": dict(
        id="druckenmiller_inflection",
        badge="드러큰밀러·스타인하트형 · 한 바구니 변곡점",
        master="스탠리 드러큰밀러 (Duquesne) & 마이클 스타인하트 (Variant Perception 창시자)",
        track_record="드러큰밀러 30년 연평균 30% 수익률(연간 손실 0회) · 스타인하트 28년 연복리 24.5% — 확신이 서면 자산의 40%~80%+를 단일 테마·종목에 집중(‘Be a Pig’)",
        core_quote="“분산투자는 가장 잘못된 교리다. 남들이 못 보는 18개월 뒤의 변곡점이 명확히 보이면 모든 달걀을 한 바구니에 담고 그 바구니를 목숨 걸고 지켜봐라.”",
        crowd_blindspot="월스트리트와 대중은 ‘오늘의 나쁜 뉴스(금리·규제·재고 조정)’에 매몰돼 12~18개월 뒤 정책·공급부족이 만들 폭발적 이익 변곡점을 가격에 전혀 반영하지 못함",
        edge_formula="현재 뉴스는 최악이나 18개월 뒤 수주·전력·규제 변곡점이 확정적인 독점주에 집중자본 40%~80% 과감한 집중 베팅",
        execution_rule="소액 정찰병 분산 금지 · 변곡점 논리가 맞으면 비중 극대화, 만약 전제 가설이 틀린 공시가 나오면 주저 없이 전량 철회",
        min_asymmetry=4.0,
        target_weight_range="40% ~ 80% (단독 1종목 승부)",
        horizon="12~24개월",
        sources=(
            ("NBER ‘Best Ideas’ 최고 확신 집중투자 논문", "https://www.nber.org/papers/w15012"),
            ("Morgan Stanley ‘Expectations Investing & Variant Perception’", "https://www.morganstanley.com/im/"),
        ),
    ),
    "nomad_ses": dict(
        id="nomad_ses",
        badge="노마드(닉 슬립)·리루형 · 3종목 영구해자",
        master="닉 슬립 (Nomad Investment Partnership) & 리루 (Himalaya Capital · 멍거 가문 운용)",
        track_record="노마드 투자조합(2001~2013) 누적 +921.1%(연 20.8% vs 지수 6.5%), 포트폴리오 80%를 단 3종목에 집중 · 리루 아시아 위기 바닥 3~4종목 초집중",
        core_quote="“진정 위대한 기업은 극히 드물다. 단기 마진을 고객에게 돌려주며 경쟁자를 말려 죽이는 기업을 찾았다면 분산은 무지에 대한 변명일 뿐이다.”",
        crowd_blindspot="기업이 장기 시장 장악을 위해 단기 가격을 낮추거나 선제 투자할 때 월가는 ‘마진 둔화·성장 피크’로 오해해 반토막 투매함",
        edge_formula="규모의 경제 공유(SES)·압도적 고객 재구매율(소모품/플랫폼)·무차입 ROIC 25%+ 기업이 단기 성장통으로 급락할 때 35%~65% 집중",
        execution_rule="매수 후 3~5년 이상 무회전 장기 복리 보유 · 기업 문화와 고객 락인 플라이휠이 깨질 때만 매도",
        min_asymmetry=3.5,
        target_weight_range="35% ~ 65% (2~3종목 영구보유)",
        horizon="24~60개월",
        sources=(
            ("Cremers & Petajisto (2009) Active Share 실증 논문", "https://academic.oup.com/rfs/article-abstract/22/9/3329/1563727"),
            ("Himalaya Capital 집중 가치투자 원칙", "https://www.himcap.com/"),
        ),
    ),
    "pabrai_dhandho": dict(
        id="pabrai_dhandho",
        badge="파브라이(단도)·애크먼형 · 켈리 스나이퍼",
        master="모니시 파브라이 (Dhandho Funds) & 빌 애크먼 (Pershing Square · GGP 27배)",
        track_record="빌 애크먼 GGP 파산 공포 바닥 단일 종목 집중으로 $60M → $1.6B(27배+) 회수 · 파브라이 ‘Few Bets, Big Bets, Infrequent Bets’ 켈리 집중 운용",
        core_quote="“동전 앞면이 나오면 크게 이기고, 뒷면이 나와도 거의 잃지 않는다(Heads I win; tails I don't lose much). 적게, 크게, 가끔 베팅하라.”",
        crowd_blindspot="시장은 ‘높은 불확실성(뉴스 공포)’과 ‘높은 원금 손실 위험’을 혼동해 순현금·유형자산 가치가 시총에 육박하는 흑자 기업을 파산가처럼 던짐",
        edge_formula="시총 대비 순현금·FCF 하방이 콘크리트처럼 막혀 손실폭은 -10~-15% 이내인데 오해 해소 시 +100~+300% 열리는 기회에 켈리 비중(30~55%) 투입",
        execution_rule="어중간한 기회는 수개월간 100% 패스(현금 대기) · 연 1~2회 확실한 Fat Pitch 출현 시에만 30~55% 집중 타격",
        min_asymmetry=4.5,
        target_weight_range="30% ~ 55% (연 1~2회 스나이퍼)",
        horizon="12~30개월",
        sources=(
            ("J.L. Kelly Jr. (1956) 최적 정보·집중 베팅 원전 논문", "https://www.princeton.edu/~wbialek/rome/refs/kelly_56.pdf"),
            ("Pershing Square 집중 행동주의·가치 연구", "https://pershingsquareholdings.com/"),
        ),
    ),
}

ACADEMIC_RESEARCH = (
    dict(
        title="Best Ideas (최고 확신 1종목 알파 실증)",
        authors="Randolph Cohen (Harvard) · Christopher Polk (LSE) · Bernhard Silli (2010, NBER Working Paper 15012)",
        finding=(
            "미국 액티브 펀드매니저 수천 명의 1991~2009년 보유 종목을 전수 분석한 결과, 매니저가 가장 확신해 최대 비중을 실은 ‘단 1위 종목(Best Idea #1)’만 모은 포트폴리오는 "
            "시장 지수 및 나머지 분산 종목들을 연 +2.8%~+4.5%p(고확신 구간 +6~9%p) 압도했다. 대부분의 펀드가 시장을 못 이기는 이유는 실력 부족이 아니라 "
            "커리어 리스크 방어용으로 끼워 넣은 20~100번째 어중간한 분산 종목들이 최고 아이디어의 수익률을 갉아먹기(Over-diversification Drag) 때문임이 실증됐다."
        ),
        url="https://www.nber.org/papers/w15012",
    ),
    dict(
        title="Kelly Criterion · 정보 우위와 기하복리 극대화 수학 정리",
        authors="John L. Kelly Jr. (1956, Bell System Technical Journal) & Edward O. Thorp (MIT/Princeton)",
        finding=(
            "남들이 모르는 정보 우위(Variant Perception Edge, 승률 p)와 비대칭 손익배수(b)가 존재할 때 장기 복리 자산 성장률을 수학적으로 극대화하는 유일한 비중은 "
            "1/N 균등 분산(5%씩 20종목)이 아니라 우위에 비례한 집중 베팅 f* = (b·p - q) / b 이다. 예컨대 손익배수 4.5배·승률 60%인 무차입 현물 기회의 최적 집중 비중은 51.1%에 달한다."
        ),
        url="https://www.princeton.edu/~wbialek/rome/refs/kelly_56.pdf",
    ),
    dict(
        title="Active Share · 옷장 인덱스(분산)의 패배와 집중 스톡피커의 승리",
        authors="Martijn Cremers & Antti Petajisto (2009, Review of Financial Studies, Yale School of Management)",
        finding=(
            "벤치마크 지수와 비슷하게 수십 종목을 5% 이하로 나눠 담는 분산형 펀드(Closet Indexers)는 수수료 차감 후 구조적으로 시장에 패배하며, "
            "지수 구성과 무관하게 소수 핵심 종목에 고비중으로 집중하는 ‘Concentrated Stock Pickers(Active Share ≥ 80%)’ 집단만이 유의미한 초과수익을 창출한다."
        ),
        url="https://academic.oup.com/rfs/article-abstract/22/9/3329/1563727",
    ),
    dict(
        title="Expectations Investing & Variant Perception (기대치 역산과 시선 괴리)",
        authors="Michael Steinhardt (Steinhardt Partners) & Michael Mauboussin (Morgan Stanley Counterpoint Global)",
        finding=(
            "이미 전 세계가 극찬하며 최근 5년 내 10~30배 오른 인기 대장주에는 미래의 장밋빛 기대가 주가에 100% 반영되어 비대칭 초과수익이 나오지 않는다. "
            "진정한 텐베거는 ‘현재 주가에 반영된 대중의 비관적 암묵 기대치’와 ‘실제 진행 중인 수출·병목 현금흐름’ 사이의 간극이 가장 큰 미개화 중형 독점주에서 탄생한다."
        ),
        url="https://www.morganstanley.com/im/",
    ),
)

# Historical Hall-of-Fame Lessons (Kept STRICTLY as educational past blueprints — excluded from live radar!)
VALIDATION_MATRIX = dict(
    summary=(
        "아래 종목들은 과거 역발상 1종목 집중 전략이 어떻게 6~71배 수익을 냈는지를 보여주는 ‘졸업한 역사적 교본’입니다. "
        "이미 텐베거를 달성해 시가총액이 수십조~수천조 원이 된 이 주식들을 지금 뒤늦게 조정받았다고 사면 다시 10배가 되지 않습니다. "
        "따라서 실시간 발굴 레이더(3장)에서는 이 기성 텐베거들을 전면 퇴출하고, ‘2021년의 삼양식품·HD현대일렉트릭, 2022년의 Meta’와 똑같은 초기 DNA를 가진 새로운 미개화 종목만 추적합니다."
    ),
    cases=(
        dict(
            name="HD현대일렉트릭 (267260) · [졸업 교본]",
            archetype="병목 선점형 · 2021년 미개화 시총 6천억 시절",
            verdict="역사적 성공 · 최고 71.7배 (레이더 졸업)",
            trough="2021-12 · 17,450원 (중공업 적자 선입견 바닥)",
            peak_or_now="최고 1,252,000원 (+7,075%) → 기성 대형주 전환으로 신규 발굴 제외",
            crowd_then="과거 조선·중공업 구조조정 굴뚝주 편견으로 무관심",
            variant_edge="발굴 DNA 교훈: 전통 제조업 껍데기 속에 북미 필수 인프라 병목 수주가 시작될 때 시총 1조 미만~수조 원 초입에서 50% 집중해야 텐베거가 됨",
        ),
        dict(
            name="삼양식품 (003230) · [졸업 교본]",
            archetype="이호걸형 · 2021년 시총 6천억 시절",
            verdict="역사적 성공 · 최고 18.5배 (레이더 졸업)",
            trough="2021-12 · 84,800원 (내수 라면 저멀티플 소외)",
            peak_or_now="최고 1,566,000원 (+1,747%) → 이미 리레이팅 완료로 신규 발굴 제외",
            crowd_then="원맥 가격 상승 우려와 ‘일시적 매운맛 유행’ 편견으로 PER 8배 방치",
            variant_edge="발굴 DNA 교훈: 내수 소비재인 줄 알았는데 미국·중국 주류 채널 재구매율과 해외 영업이익률이 폭발하기 직전인 중형 브랜드를 찾아야 함",
        ),
        dict(
            name="SK하이닉스 (000660) · [졸업 교본]",
            archetype="병목 선점형 · 2022년 적자 공포 바닥",
            verdict="역사적 성공 · 최고 35.3배 (레이더 졸업)",
            trough="2022-11 · 75,000원 (7.7조 적자 공포 · PBR 0.9배)",
            peak_or_now="최고 2,650,000원 (+3,433%) → 컨센서스 코어 전환으로 신규 발굴 제외",
            crowd_then="레거시 D램 적자 백미러만 보고 기관·외인 투매",
            variant_edge="발굴 DNA 교훈: 전방 레거시 둔화로 주가가 반토막 났지만 차세대 AI 필수 공정·소켓·소재 독점 점유율을 쥔 기업을 공포 바닥에서 선점해야 함",
        ),
        dict(
            name="Meta Platforms (META) · [졸업 교본]",
            archetype="버리·노마드 결합형 · 2022년 -76% 혐오 바닥",
            verdict="역사적 성공 · 최고 8.3배 (레이더 졸업)",
            trough="2022-10 · $93.16 (군중 조롱 투매 · PER 9배)",
            peak_or_now="최고 $773.44 (+730%) → 메가캡 복귀로 신규 발굴 제외",
            crowd_then="단기 투자비 지출 비난 속 패시브 투매로 FCF 대비 청산급 할인",
            variant_edge="발굴 DNA 교훈: ROIC 30%+ 현금창출 본업이 멀쩡한데 일시적 성장 둔화·비용 노이즈로 5년 최저점(PER 5~10배)에 추락한 기업이 최고의 스나이퍼 타깃",
        ),
        dict(
            name="카카오 (035720) · [반증: 1종목 집중 금지 함정]",
            archetype="가치함정 경보 · 해자·주주환원 미충족",
            verdict="실패(함정) · 바닥 후 +5.4% 장기 정체",
            trough="4년 연속 하락 후 2026-09 · 29,450원",
            peak_or_now="현재 31,050원 (+5.4% · 집중 시 막대한 기회비용)",
            crowd_then="‘고점 대비 -80% 빠졌으니 싸다’는 개인 저가매수 유입",
            variant_edge="반증 교훈: 안 올랐다고 다 차세대 텐베거가 아니다! 글로벌 가격결정력·순현금 소각·물리적 병목이 없는 단순 낙폭주는 1주도 집중 금지!",
        ),
    ),
    comparison=(
        ("목표 종목군", "이미 추세가 터져 모두가 아는 현재 주도 대형주 (/discover)", "아직 5년 저점 대비 1~3배에 머문 ‘차세대 미개화 독점·병목 중형/괴리주’ (/contrarian)"),
        ("포지션 비중 철학", "분산 리스크 관리 (종목당 10~20% · 여러 종목 분산)", "백화점식 한 자릿수(5~8%) 분산 거부! 확신 검증 통과 시 집중자본의 30%~75% 승부 (1~3종목 압축)"),
        ("리스크 통제 방식", "가격 손절선(-8%) 및 변동성 캡으로 사후 방어", "진입 전 ‘무차입 순현금·FCF 바닥가’로 하방을 원천 잠그고 단기 가격 흔들림은 무손절 돌파"),
        ("기성 텐베거 처리", "추세가 살아 있으면 계속 보유·추적", "이미 5~70배 오른 기성 텐베거는 ‘졸업’ 처리해 배제하고 제2·제3의 신규 씨앗만 발굴"),
    ),
)

# Conviction & Balance-Sheet Solvency Tiers — Calibrated for TRUE 1-Stock Concentrated Investing (30% ~ 75%, NEVER 5~8%!)
SOLVENCY_TIERS = {
    "net_cash": dict(
        label="S급 재무요새 · 무차입 순현금·초고마진 FCF (단독 50~75% 초집중 적격)",
        cap_pct=75.0,
        min_pct=40.0,
        portfolio_guide="집중계좌 1~2종목 압축 승부 (이호걸·드러큰밀러급)",
        ok=True,
    ),
    "backlog_float": dict(
        label="A급 현금흐름 · 수주 선수금(Float)·영업흑자 건전 (주력 35~55% 집중 적격)",
        cap_pct=55.0,
        min_pct=30.0,
        portfolio_guide="집중계좌 2~3종목 핵심 집중 (노마드·리루·파브라이급)",
        ok=True,
    ),
    "turnaround_watch": dict(
        label="B급 설비전환 · 영업흑자 유지·차입 점검 병행 (선발 25~35% 집중 적격)",
        cap_pct=35.0,
        min_pct=20.0,
        portfolio_guide="집중계좌 3~4종목 이내 배치 (버리 13F 상위권 방식)",
        ok=True,
    ),
    "distressed_block": dict(
        label="집중 부적격 · 이자보상 <2배 또는 유상증자·CB 희석 위험 (5% 정찰도 금지 · 0% 기각)",
        cap_pct=0.0,
        min_pct=0.0,
        portfolio_guide="베팅 기각 (Pass — 올인할 수 없는 종목은 소액으로도 사지 않는다)",
        ok=False,
    ),
}

# Brand-New 20 Uncrowded Next-Inflection Universe (Zero Ex-Post 10x Consensus Mega-Caps!)
# (symbol, market, venue, currency, name, archetype, solvency_key, essence_score[0..35], seed_analogy, moat_essence, crowd_fear, kill_switch)
CONTRARIAN_UNIVERSE = (
    # --- KOREA: 10 Uncrowded Pre-Tenbagger Monopoly / Export-Inflection / Deep-Value Gems ---
    ("214150", "KR", "KOSDAQ", "KRW", "클래시스", "nomad_ses", "net_cash", 34,
     "2021년 밀양 공장 가동 전 삼양식품(시총 1조대 미개화) 초기 수출·소모품 레버리지 DNA",
     "미용의료기기 설치 대수가 누적될수록 영업이익률 ~50% 고마진 카트리지 소모품이 무한 반복 소비되는 면도날 해자 + 브라질 이어 미·중 인허가 본진입 초입(무차입 순현금)",
     "합병 통합 비용과 국내 미용 소비 둔화 우려로 52주 고점 대비 -69% 폭락하며 5년 저점 대비 1.7배 수준으로 회귀",
     "주력 장비 글로벌 시술 건수(카트리지 출하량) 2분기 연속 역성장 또는 미국·유럽 인허가 무산 공시"),
    ("058470", "KR", "KOSDAQ", "KRW", "리노공업", "hynix_bottleneck", "net_cash", 35,
     "빅테크 커스텀 AI 칩 춘추전국시대 R&D 톨게이트 독점 (무차입 영업이익률 40%+ 요새)",
     "엔비디아뿐 아니라 구글·아마존·메타·애플이 자체 AI/NPU 칩을 설계·검증할 때 대체재가 없는 초미세 리노핀·IC 테스트 소켓 글로벌 독점 과점",
     "레거시 스마트폰 업황 둔화와 묶여 52주 고점 대비 -59% 급락 (5년 저점 대비 불과 2.1배 미개화 구간)",
     "선단 피치 테스트 소켓 독점 점유율 이탈 또는 영업이익률 30% 하회 공시"),
    ("103140", "KR", "KRX", "KRW", "풍산", "hynix_bottleneck", "backlog_float", 32,
     "2021년 HD현대일렉트릭처럼 ‘전통 굴뚝주(구리) 껍데기’에 가려진 서방권 탄약 공급 병목",
     "PBR ~0.6배 신동(구리 가공) 자산 하방 방어막 + 글로벌 재무장 속에서 물리적 증설이 가장 느린 155mm 대구경 포탄·탄약 핵심 공급 병목(E_s ≈ 0)",
     "구리 가격 변동성 민감 굴뚝주라는 오랜 편견과 종전 헤드라인 노이즈로 고점 대비 -63% 폭락(5년 저점 대비 2.0배)",
     "방산 부문 수출 수주잔고 감소 전환 또는 대구경 탄약 장기계약 해지 공시"),
    ("014680", "KR", "KRX", "KRW", "한솔케미칼", "hynix_bottleneck", "backlog_float", 32,
     "이차전지 우려 껍데기에 가려진 2nm 파운드리·차세대 HBM 초고순도 소재 독점 병목",
     "TSMC·삼성·하이닉스 선단 미세공정 필수 초고순도 과산화수소 및 차세대 프리커서 과점 해자 + 반도체 가동률 회복 시 즉각적 영업레버리지",
     "비주력 이차전지 바인더 기대감 소멸로 52주 고점 대비 -43% 하락(5년 저점 대비 2.1배 박스권 하단)",
     "반도체용 초고순도 과산화수소·프리커서 핵심 고객사 내 점유율 축소"),
    ("241560", "KR", "KRX", "KRW", "두산밥캣", "pabrai_dhandho", "net_cash", 31,
     "고금리 재고조정 공포와 지배구조 노이즈가 만든 PER 6~7배·순현금 북미 1등 브랜드 단도(Dhandho) 기회",
     "북미 소형 건설장비(스키드로더·컴팩트 트랙터) 압도적 점유율 1위 딜러망 해자 + 순현금 재무구조 + 북미 인프라·리쇼어링 교체 수요 대기",
     "북미 고금리 딜러 재고 조정 및 과거 지배구조 개편 피로감으로 고점 대비 -36% 하락·PBR 0.7배 수준 방치",
     "북미 소형장비 시장점유율 1위 상실 또는 주주가치 훼손 합병·유상증자 재추진 공시"),
    ("145020", "KR", "KRX", "KRW", "휴젤", "calm_compounder", "net_cash", 33,
     "소송 불확실성 완전 해소 후 미국·유럽·중국 3대 보툴리눔 톡신 시장을 모두 뚫은 초기 수출 복리주",
     "국내 톡신 기업 중 유일하게 미국 FDA·유럽·중국 허가를 모두 획득해 북미 직판·파트너십 고마진 수출 비중이 급증하는 무차입 순현금 기업",
     "과거 균주 소송 트라우마와 내수 보톡스 저가 경쟁 선입견으로 5년 고점 대비 -44% 아래(5년 저점 대비 2.1배) 정체",
     "미국·중국 분기 톡신 수출액 역성장 전환 또는 FDA 품질 경고 발생"),
    ("111770", "KR", "KRX", "KRW", "영원무역", "burry_asymmetry", "net_cash", 31,
     "시총에 육박하는 순현금성 자산(PBR ~0.45배·PER 4~5배) 위에서 글로벌 럭셔리 아웃도어를 독점 생산하는 Roadkill",
     "아크테릭스·룰루레몬·파타고니아 등 초고가 기능성 특수원단 봉제 기술 글로벌 과점 1위 + 수조 원대 현금성 자산으로 하방 청산가치 완벽 잠금",
     "단순 의류 하청업 편견과 자회사(스캇) 자전거 재고 일시 상각 노이즈로 고점 대비 -28% 소외",
     "핵심 기능성 아웃도어 고객사 이탈 또는 대규모 비핵심 적자 인수 반복"),
    ("383220", "KR", "KRX", "KRW", "F&F", "burry_asymmetry", "net_cash", 30,
     "중국 소비 혐오 투매로 PER 4~5배·ROE 20%+까지 압축된 아시아 브랜드 현금창출기",
     "중국·동남아 900개+ 매장 네트워크에서 연간 수천억 원 잉여현금흐름을 뽑아내는 고마진 브랜드 라이선스 모델",
     "중국 내수 경기 비관론 극점으로 5년 고점 대비 -68% 폭락(5년 저점 대비 1.2배 바닥)",
     "중국 내 점포당 매출 구조적 붕괴 또는 핵심 라이선스 재계약 실패"),
    ("086280", "KR", "KRX", "KRW", "현대글로비스", "calm_compounder", "backlog_float", 31,
     "‘그룹 내부물류’ 편견 뒤에 숨은 글로벌 완성차 해상운송(PCTC) 선박 부족 병목 독식주",
     "전 세계 자동차운반선(PCTC) 공급 부족 병목 속에서 비계열 글로벌 완성차 장기 고운임 계약 비중 급증 + 배당·밸류업 확대",
     "완성차 관세 우려와 지배구조 개편용 주식이라는 편견으로 고점 대비 -30% 조정(5년 저점 대비 2.6배)",
     "글로벌 PCTC 선박 공급과잉 전환에 따른 장기 용선료 급락"),
    ("259960", "KR", "KRX", "KRW", "크래프톤", "nomad_ses", "net_cash", 32,
     "수조 원 순현금 요새 + 글로벌·인도 독점 트래픽이 매년 최대 영업이익을 찍는 오해받은 캐시카우",
     "출시 8년 차에도 글로벌·인도 플랫폼화(UGC)로 연간 1조 원+ 영업이익을 경신하는 독점 IP 현금흐름 + 막대한 순현금 하방 방어막",
     "‘신작 흥행 불확실성’과 단일 IP 편견에 갇혀 5년 고점 대비 -58% 아래(5년 저점 대비 1.4배) 저평가",
     "글로벌 핵심 IP 월간활성사용자(MAU) 및 분기 매출 2분기 연속 15%+ 급감"),

    # --- US: 10 Uncrowded Mid-Cap Bottlenecks & Deep-Dislocation Conviction Targets ---
    ("ACLS", "US", "NASDAQ", "USD", "Axcelis Technologies", "hynix_bottleneck", "net_cash", 33,
     "시총 $3B대 미개화 중형 독점주 · EV 캐즘 공포 반토막 속에 숨은 800V AI 데이터센터·SiC 장비 과점",
     "고전압 SiC(실리콘카바이드) 전력반도체 제조의 핵심 병목인 고온 이온주입 장비(Purion) 글로벌 독점 과점 + 무차입 순현금 재무요새",
     "단기 전기차 재고 조정 공포에 휩쓸려 52주 고점 대비 -45% 폭락(5년 저점 대비 2.4배 중형주)",
     "SiC 이온주입 장비 시장 내 경쟁사 점유율 역전 또는 수주잔고 급감"),
    ("ONTO", "US", "NYSE", "USD", "Onto Innovation", "hynix_bottleneck", "net_cash", 34,
     "NVDA($3.5T) 대신 시총 $8B대에서 HBM·CoWoS 첨단 패키징 병목을 직접 독식하는 중형 장비주",
     "TSMC CoWoS 및 HBM 다단 적층의 치명적 수율 결함을 잡아내는 3D 광학 계측·검사(Dragonfly) 핵심 병목 과점 + 무차입 순현금",
     "반도체 장비 업종 일괄 차익매물로 52주 고점 대비 -46.5% 급락(5년 저점 대비 3.0배)",
     "첨단 AI 패키징 검사 공정 내 핵심 파운드리·메모리 고객사 발주 중단"),
    ("FSLR", "US", "NASDAQ", "USD", "First Solar", "druckenmiller_inflection", "net_cash", 33,
     "정책 폐지 과장 공포로 반토막(-51%) 난 미국 AI 데이터센터 전력난 직납 독점 수혜주",
     "중국산 폴리실리콘을 쓰지 않는 미국 내 유일 대규모 박막형(CdTe) 태양광 모듈 독점 공급사 · 수주잔고 70GW+ 장기 고정가 계약 + 순현금",
     "정치적 신재생 보조금 축소 헤드라인 공포에 패시브 자금이 투매하며 52주 고점 대비 -51% 폭락(5년 저점 대비 2.3배)",
     "기존 체결된 유틸리티 장기 공급계약 대량 해지 또는 미국 제조 세액공제 소급 폐지 법안 가결"),
    ("LULU", "US", "NASDAQ", "USD", "Lululemon Athletica", "nomad_ses", "net_cash", 33,
     "2022년 Meta(-76%)와 판박이 · 북미 둔화 공포로 5년 최저점(1.14배)에 처박힌 ROIC 30%+ 무차입 브랜드",
     "무차입 순현금 + ROIC 30%+ 압도적 가격결정력 + 중국·글로벌 연 20~30% 고성장 + 저점 대규모 자사주 매입·소각 복리 엔진",
     "북미 매장 성장률 둔화와 신흥 경쟁사 과장 공포로 5년 고점 대비 -79% 폭락(5년 저점 대비 1.14배 극단적 바닥)",
     "글로벌 매출총이익률(58%대) 구조적 붕괴 또는 중국·해외 성장률 한 자릿수 추락"),
    ("BABA", "US", "NYSE", "USD", "Alibaba Group", "burry_asymmetry", "net_cash", 32,
     "마이클 버리(Scion) 실제 13F 최대 집중 베팅 · 시총 상당 부분이 순현금인 자사주 소각 기계",
     "막대한 순현금 보유 + 연간 수백억 달러 FCF로 매년 유통주식의 8~10%를 자사주 매입·소각 + 중국 최대 AI 클라우드(Qwen) 독점 인프라",
     "중국 매크로·지정학 혐오로 글로벌 기관이 ‘투자 불가’ 낙인을 찍으며 고점 대비 반토막(-48%, 5년 저점 대비 1.4배)",
     "연간 자사주 매입·소각 중단 또는 핵심 커머스·클라우드 잉여현금흐름 적자 전환"),
    ("MOH", "US", "NYSE", "USD", "Molina Healthcare", "pabrai_dhandho", "backlog_float", 32,
     "마이클 버리 실제 집중 보유 · 정부 요율 반영 시차가 만든 전형적인 ‘앞면 대박·뒷면 본전’ 단도 베팅",
     "미국 저소득층 필수 공적 의료보험(Medicaid) 특화 최저 관리비율 운영자 · 의료비 상승 시 다음 연도 주정부 요율이 자동 인상 보정되는 구조 + 공격적 자사주 소각",
     "단기 의료비율(MCR) 상승과 정책 예산 삭감 과장 공포로 5년 고점 대비 -51% 폭락(5년 저점 대비 1.5배)",
     "핵심 주정부 메디케이드 대규모 재계약 탈락 또는 구조적 요율 보정 메커니즘 폐지"),
    ("NVO", "US", "NYSE", "USD", "Novo Nordisk", "druckenmiller_inflection", "backlog_float", 34,
     "임상 기대치·약가 노이즈로 -71% 폭락해 5년 최저점(1.14배)으로 되돌아온 글로벌 대사질환 원료 설비 복점주",
     "수백억 달러를 선투자한 글로벌 GLP-1 원료의약품(API)·충전 생산설비 물리적 진입장벽 및 전 세계 당뇨·비만 처방 캐시카우",
     "후속 파이프라인 수치 실망과 미국 약가 인하 정치 노이즈가 겹쳐 5년 고점 대비 -71% 투매(5년 저점 대비 1.14배)",
     "주력 세마글루타이드 계열 글로벌 처방 물량 역성장 또는 치명적 안전성 결함 발생"),
    ("DECK", "US", "NYSE", "USD", "Deckers Outdoor", "nomad_ses", "net_cash", 32,
     "무차입 순현금($1.5B+) + ROIC 40%+ 러닝화 생태계 확장 중 소비 공포로 -60% 급락한 복리 기계",
     "HOKA 전문 러닝화 커뮤니티 충성도와 고마진 직판(DTC) 비중 확대 · 차입금 제로 상태에서 공격적 자사주 소각",
     "미국 소비 둔화 우려와 가이던스 보수적 제시로 5년 고점 대비 -60% 급락(5년 저점 대비 2.1배)",
     "HOKA 브랜드 글로벌 매출 역성장 또는 재고 급증에 따른 상시 할인 판매 전환"),
    ("ENTG", "US", "NASDAQ", "USD", "Entegris", "hynix_bottleneck", "turnaround_watch", 31,
     "장비주와 달리 2nm·HBM 팹이 돌아가는 한 매일 소모되는 초고순도 오염제어 필터 톨게이트 독점",
     "선단 반도체 수율을 좌우하는 나노급 오염제어 필터·특수화학소재 독점(매출의 70%+ 반복성 소모품) + 인수 후 차입금 축소 진행",
     "레거시 웨이퍼 가동률 회복 지연 우려로 고점 대비 -24% 눌림(5년 저점 대비 2.1배)",
     "선단 2nm 공정용 필터 점유율 하락 또는 잉여현금흐름 차입 상환 지연"),
    ("CCJ", "US", "NYSE", "USD", "Cameco", "druckenmiller_inflection", "backlog_float", 33,
     "AI 원전 르네상스의 유일한 서방권 고품위 우라늄 광산·연료주기(Westinghouse) 물리적 독점 병목",
     "카자흐스탄·러시아 공급 리스크 속에서 신규 광산 개발에 10~15년이 걸리는 절대 공급 비탄력성(E_s ≈ 0) + 유틸리티 장기 계약 단가 상승",
     "단기 원전 테마 차익실현 매물로 52주 고점 대비 -48% 급락(5년 저점 대비 3.36배, 상한 이내)",
     "글로벌 원전 가동 중단 사고 또는 서방 유틸리티 장기 우라늄 계약 단가 하락 전환"),
)


def _default_get(url):
    req = Request(url, headers={"User-Agent": "whale-tracking/1.0 local contrarian research"})
    with urlopen(req, timeout=7) as resp:
        return resp.read(2_000_000)


def _clamp(val, lo, hi):
    return max(lo, min(hi, val))


def compute_position_sizing(*, upside_pct, downside_pct, win_prob=0.60, cap_pct=60.0, min_pct=30.0, blocked=False, risk_budget_pct=None):
    """High-Conviction Concentrated Kelly Sizing (30% ~ 75% of dedicated conviction capital — NEVER single-digit closet indexing!)."""
    if blocked or cap_pct <= 0 or upside_pct <= 0 or downside_pct <= 0:
        return dict(
            kelly_full_pct=0.0,
            kelly_quarter_pct=0.0,
            recommended_pct=0.0,
            cap_pct=max(0.0, float(cap_pct)),
            grade_label="0% · 베팅 기각 (확신·생존 미달 시 소액 정찰도 금지)",
            portfolio_guide="매수 보류 (Pass)",
        )
    p = _clamp(float(win_prob), 0.25, 0.85)
    q = 1.0 - p
    b = max(float(upside_pct) / max(float(downside_pct), 1.0), 0.1)
    # Classic Kelly fraction on asymmetric payoff odds b: f* = (p*b - q) / b
    full_kelly = max(0.0, (p * b - q) / b) * 100.0
    if full_kelly < 15.0:
        return dict(
            kelly_full_pct=round(full_kelly, 1),
            kelly_quarter_pct=round(full_kelly * 0.25, 1),
            recommended_pct=0.0,
            cap_pct=round(float(cap_pct), 1),
            grade_label="0% · 기대 우위 부족 (어중간한 5~10% 분산 진입 금지)",
            portfolio_guide="진입가 추가 하락 대기 (Fat Pitch 아님)",
        )
    # Unlevered spot concentration: downside is bounded by structural floor (not -100% wipeout),
    # so conviction allocation scales between [min_pct, cap_pct] driven by Full Kelly edge
    conv_raw = _clamp(full_kelly * 1.10, float(min_pct), float(cap_pct))
    rec = round(min(conv_raw, float(cap_pct)), 1)
    if rec >= 50.0:
        grade = f"단독 초집중 · {rec:.0f}% (1~2종목 승부)"
        guide = "집중계좌 1~2종목 압축 (이호걸·드러큰밀러급 확신)"
    elif rec >= 35.0:
        grade = f"주력 집중 · {rec:.0f}% (2~3종목 핵심)"
        guide = "집중계좌 2~3종목 압축 (노마드·리루·파브라이급)"
    else:
        grade = f"선발 집중 · {rec:.0f}% (3~4종목 이내)"
        guide = "집중계좌 3~4종목 이내 (버리 13F 상위권 집중)"
    return dict(
        kelly_full_pct=round(full_kelly, 1),
        kelly_quarter_pct=round(full_kelly * 0.25, 1),
        recommended_pct=rec,
        cap_pct=round(float(cap_pct), 1),
        grade_label=grade,
        portfolio_guide=guide,
    )


def _monotonic_tranches(entry_val, floor_val, rnd):
    """Guarantee strictly decreasing 3-tranche prices: entry (35%) > t2 (40%) > t3 (25%) >= floor."""
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
    sym, market, venue, ccy, name, arch_id, solv_key, essence, seed_txt, moat_txt, fear_txt, kill_txt = spec
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

    # 5-Year Trough Multiple Check (Anti-Hindsight / Ex-Tenbagger Filter!)
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

    # Axis 2: Uncrowded Early-Stage Dislocation Score (0..35)
    # Rewards deep drawdown + pre-tenbagger 5y trough proximity; penalizes already-run stocks!
    gap_pts = 8.0
    drop = max(-dd52, -dd5y * 0.85)
    if 30 <= drop <= 75:
        gap_pts += 14.0
    elif 20 <= drop < 30:
        gap_pts += 10.0
    elif drop > 75:
        gap_pts += 11.0
    elif drop < 10:
        gap_pts -= 5.0

    # Bonus for true uncrowded 5-year base (1.0x ~ 2.5x above 5Y low); heavy penalty if > 3.6x!
    if mult_5y_low <= 2.2:
        gap_pts += 6.0
    elif mult_5y_low <= EX_TENBAGGER_CEILING:
        gap_pts += 3.0
    else:
        gap_pts -= 12.0

    if pct60 < -8:
        gap_pts += 5.0
    elif pct60 < 0:
        gap_pts += 3.0
    elif pct60 > 15:
        gap_pts -= 4.0

    if rsi <= 38:
        gap_pts += 4.0
    elif rsi <= 50:
        gap_pts += 2.0
    elif rsi >= 70:
        gap_pts -= 6.0
    gap_score = round(_clamp(gap_pts, 2.0, 35.0), 1)

    # Structural Downside Floor & Multi-Year Re-Rating Target (2x~4x inflection potential, anchored by 5Y high & moat)
    sorted_1y = sorted(window_1y)
    p10_floor = sorted_1y[max(0, int(0.08 * (len(sorted_1y) - 1)))]
    floor_px = min(cur * 0.86, max(low52 * 0.94, min(cur * 0.88, p10_floor)))
    target_px = max(cur * 1.65, high52 * 0.95, min(cur * 2.8, high5y * 0.88))
    bull_px = max(target_px * 1.35, high5y * 1.15)

    downside_pct = max(5.0, (1.0 - floor_px / cur) * 100)
    upside_pct = (target_px / cur - 1.0) * 100
    asymmetry_ratio = round(upside_pct / downside_pct, 2)
    margin_pct = round((1.0 - cur / target_px) * 100, 1)

    # Axis 3: Asymmetric Convexity Score (0..30)
    asym_pts = _clamp(asymmetry_ratio * 4.2, 3.0, 30.0)
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
    win_p = 0.62 if essence >= 33 else 0.58
    sizing = compute_position_sizing(
        upside_pct=upside_pct,
        downside_pct=downside_pct,
        win_prob=win_p,
        cap_pct=solv_meta["cap_pct"],
        min_pct=solv_meta["min_pct"],
        blocked=blocked,
    )
    if ex_tenbagger:
        live_fear = f"[기성 급등주 차단: 5년 저점 대비 {mult_5y_low:.1f}배 상승 이력 — 신규 텐베거 발굴 대상 제외] {fear_txt}"
    elif overheated:
        live_fear = f"[단기 과열 구간(RSI {rsi:.0f}) — 조정 대기 후 집중 타격] {fear_txt}"
    else:
        live_fear = fear_txt

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
        target_weight_range=arch["target_weight_range"],
        horizon=arch["horizon"],
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
        seed_analogy=seed_txt,
        moat_essence=moat_txt,
        crowd_fear=live_fear,
        execution_rule=arch["execution_rule"],
        kill_switch=kill_txt,
        source_url=src_url,
    )


def refresh(package, *, fetcher=None, now=None):
    """Scan uncrowded pre-tenbagger moat universe for Variant-Perception Dislocation. Zero portfolio input."""
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
        bars_5y = None
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

    candidates.sort(key=lambda r: (not r["trap_shield_ok"], -r["total"], -r["asymmetry"], r["symbol"]))
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
    """Validate and save a bespoke 1-Stock High-Conviction Concentrated Playbook locally."""
    market = str(fields.get("market", "KR")).strip().upper()
    symbol = str(fields.get("symbol", "")).strip().upper()
    name = str(fields.get("name", "")).strip() or symbol
    archetype = str(fields.get("archetype", "calm_compounder")).strip()
    crowd_view = str(fields.get("crowd_view", "")).strip()
    variant_insight = str(fields.get("variant_insight", "")).strip()
    kill_switch = str(fields.get("kill_switch", "")).strip()
    horizon = str(fields.get("horizon", "18~36개월")).strip()[:40]
    url = str(fields.get("url", "")).strip()

    if market not in ("KR", "US") or not re.fullmatch(r"[A-Z0-9.\-]{1,12}", symbol):
        raise ValueError("시장(KR/US)과 종목코드·티커 형식을 확인하세요.")
    if archetype not in ARCHETYPES:
        raise ValueError("역발상 집중투자 아키타입을 선택하세요.")
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
    passes = bool(solv_meta["ok"] and asymmetry >= min_req and margin_pct >= 25.0 and sizing["recommended_pct"] >= 20.0)

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
        sizing=sizing,
        entry=rnd(entry),
        floor=rnd(floor),
        target=rnd(target),
        bull=rnd(target * Decimal("1.30")),
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
