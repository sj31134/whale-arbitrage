"""Reviewed public sources and versioned research specifications. No account inputs."""

from . import quant

PAPER = "https://www.aqr.com/insights/research/journal-article/time-series-momentum"
VARIANCE = (
    "https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf"
)
AQR = "https://funds.aqr.com/Funds/Alternatives/AQR-Managed-Futures-Strategy-Fund"
WINTON = "https://www.wintonfunds.com/funds/winton-managed-futures-trend-fund"
BUFFETT = "https://www.aqr.com/Insights/Research/Journal-Article/Buffetts-Alpha"
ANNUAL = "https://www.berkshirehathaway.com/2025ar/2025ar.pdf"
SEC = "https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f"
Q2 = "https://www.sec.gov/Archives/edgar/data/1067983/000119312526352200/xslForm13F_X02/56757.xml"
Q3 = "https://www.sec.gov/Archives/edgar/data/1067983/000119312526463399/xslForm13F_X02/60471.xml"
Q2_TIME = "https://www.sec.gov/Archives/edgar/data/1067983/000119312526352200/0001193125-26-352200-index.htm"
Q3_TIME = (
    "https://www.sec.gov/Archives/edgar/data/1067983/0001193125-26-463399-index.html"
)
PTR = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20033725.pdf"
VENTURE = "https://www.businesswire.com/news/home/20230501005275/en/Sound-Ventures-Closes-Oversubscribed-AI-Fund-Announces-Investments-in-Generative-AI-Leaders"

# These are reviewed observations, not an exhaustive feed of trades or holdings.
# Use the actual observation time when the original publication time is unknown.
ELEVATION = "https://elevation.com/"
NC = "https://www.nctreasurer.gov/documents/files/ncia/performance-report-calendar-year-2025/download?attachment="

EVENTS = (
    (
        "elevation",
        "2025-12-31",
        "2026-11-24T20:54:35+09:00",
        NC,
        ("Elevation Partners LP",),
    ),
    ("berkshire", "2026-06-30", "2026-08-14T16:05:04-04:00", Q2, ("AXP", "AAPL")),
    ("berkshire", "2026-09-30", "2026-11-16T16:00:04-05:00", Q3, ("AXP", "AAPL")),
    ("household", "2026-01-16", "2026-11-24T20:41:00+09:00", PTR, ("AB",)),
    (
        "venture",
        "2023-05-01",
        "2023-05-01T09:00:00-04:00",
        VENTURE,
        ("OpenAI", "Anthropic", "StabilityAI"),
    ),
)
SOURCE_LABELS = {
    PAPER: "Moskowitz·Ooi·Pedersen (2012)",
    VARIANCE: "Moreira·Muir (2017)",
    AQR: "AQR AQMIX 월말 성과",
    WINTON: "Winton Class I 월말 성과",
    BUFFETT: "Frazzini·Kabiller·Pedersen (2018)",
    ANNUAL: "버크셔 2025 연차보고서",
    SEC: "SEC 13F 범위",
    Q2: "버크셔 2분기 공시 표",
    Q3: "버크셔 3분기 공시 표",
    Q2_TIME: "SEC 2분기 접수시각",
    Q3_TIME: "SEC 3분기 접수시각",
    PTR: "미 하원 PTR 원문",
    VENTURE: "Sound Ventures 발표",
    ELEVATION: "Elevation 투자전략·보노 역할",
    NC: "노스캐롤라이나 공적연금 2025년 말 성과표",
}


def spec(title, kind, rule, downside, revisit, sources=(), version="1.0"):
    return dict(
        title=title,
        kind=kind,
        rule=rule,
        downside=downside,
        revisit=revisit,
        sources=sources,
        version=version,
    )


CATALOG = {
    "trend-252": spec(
        "12개월 추세",
        "price",
        "252거래일 가격 상승 시 주식 100%, 그 외 현금. 월별 조정.",
        "급격한 반등과 횡보에서 신호가 늦을 수 있다.",
        "다음 독립 63거래일에서 비용 2배 초과수익과 낙폭을 함께 재검토한다.",
        (PAPER, AQR, WINTON),
        version="1.1",
    ),
    "trend-vote": spec(
        "3·6·12개월 추세 합의",
        "price",
        "63·126·252거래일 중 상승한 기간의 비율만 주식에 배정한다. 월별 조정.",
        "세 기간은 서로 상관되며, 급반전 시 동시에 손실을 볼 수 있다.",
        "단일 252일 규칙 대비 비용 후 개선이 독립 구간에서 반복되는지 점검한다.",
        (PAPER, AQR, WINTON),
        version="1.1",
    ),
    "variance-cap": spec(
        "변동성에 따른 노출 축소",
        "price",
        "직전 21일 일간수익률의 연환산 분산 대비 15%의 제곱 비율을 사용한다. 상한 100%, 월별 조정.",
        "급락 첫날을 피하지 못하고 반등 초기에 현금이 많아질 수 있다.",
        "낙폭 완화가 사라지거나 같은 종목 보유 대비 비용이 과도해지면 재검토한다.",
        (VARIANCE,),
        version="1.1",
    ),
    "berkshire": spec(
        "버크셔 연속 공시",
        "event",
        "연속 두 분기에 같은 주식이 공시됐는지 접수시각 이후 확인한다. 검토한 종목 표본만 표시한다.",
        "보험 플로트·비상장 사업·현금·공매도와 분기 중 거래가 빠진다.",
        "13F 정정, 다음 분기 공시 또는 발행인의 가치·수익성 악화 시 재검토한다.",
        (BUFFETT, ANNUAL, Q2_TIME, Q2, Q3_TIME, Q3, SEC),
    ),
    "household": spec(
        "정치인 가구 거래 공시",
        "event",
        "펠로시 신고서의 배우자 직접 매입 사례를 기록한다. 옵션 행사와 분리한다.",
        "금액 구간과 지연 공시만으로 가구의 전체 수익률을 계산하기 어렵다.",
        "정정·소유자·거래유형 또는 공개시각이 바뀌면 검토한다.",
        (PTR,),
    ),
    "venture": spec(
        "연예인 참여 VC 테마",
        "event",
        "애슈턴 커처 공동운용사의 발표일 이후 기초 AI 모델 투자 테마를 관찰한다.",
        "비상장 평가와 회수 시차가 크며 출자금·펀드 규모로 개인 수익률을 산출할 수 없다.",
        "감사된 순성과나 회수 공시가 나오면 자료 등급을 재검토한다.",
        (VENTURE,),
    ),
    "elevation": spec(
        "보노 · 미디어·기술 사모투자",
        "event",
        "Elevation의 기술·미디어 성장투자 회수 사례. 2025년 말 노스캐롤라이나 연금 출자분 설정 이후 IRR 12.15%, 투자배수 1.59배.",
        "비상장 진입가격과 회수 조건이 달라 상장 후 투자자 수익과 차이가 날 수 있다. 개인 성과는 미확인이다.",
        "다른 출자자 기준 성과와 투자·회수 시점을 대조한다. 2015년에 마지막 포트폴리오 기업을 매각했다.",
        (ELEVATION, NC),
    ),
    "sma": spec(
        "기존 5~120일 이동평균",
        "existing",
        "퀀트 연구 화면에서 116개 기간·워크포워드·마지막 63일을 검증한다.",
        "기간 선택 편향과 체결 마찰에 민감하다.",
        "기존 동결 표본·독립 63거래일 판정을 따른다.",
        version=quant.VERSION,
    ),
    "scenario": spec(
        "기존 시나리오 평가",
        "existing",
        "ScenarioModeler에서 강세·기준·약세 기대수익과 손익비를 계산한다.",
        "시나리오 확률과 공정가치 추정에 민감하다.",
        "현금흐름·안전마진 가정을 공시 이후 다시 확인한다.",
        version="ScenarioModeler",
    ),
    "risk": spec(
        "기존 스트레스 검토",
        "existing",
        "RiskManager에서 약세·다중 시나리오·가설 무효화 조건을 점검한다.",
        "가정에 없는 충격은 포착하기 어렵다.",
        "금리·환율·변동성 충격이 바뀌면 스트레스를 다시 계산한다.",
        version="RiskManager",
    ),
    "barbell": spec(
        "기존 바벨 배분 연구",
        "existing",
        "BarbellOptimizer에서 심사를 거친 후보의 연구용 배분안을 계산한다.",
        "입력 기대수익·상관 구조가 바뀔 수 있다.",
        "편입 근거 또는 집중 위험이 달라지면 매니저가 재검토한다.",
        version="BarbellOptimizer",
    ),
}
