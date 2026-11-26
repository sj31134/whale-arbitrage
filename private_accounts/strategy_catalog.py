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
    "downside-cap": spec(
        "하방 변동성에 따른 노출 축소",
        "price",
        "직전 21일 중 하락한 날의 일간수익률만 제곱합해 연환산 하방분산을 구하고 15%의 제곱 비율을 사용한다. 상한 100%, 월별 조정.",
        "급락 첫날 충격은 피하기 어려우나, 대칭 변동성 캡과 달리 급등장의 상승 변동성에서는 비중을 줄이지 않는다.",
        "코스피 60일선 안착(Phase 2) 및 반등 구간에서 대칭 변동성 캡 대비 초과수익과 낙폭 완화가 유지되는지 재검토한다.",
        (VARIANCE,),
        version="1.0",
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

STRATEGY_GUIDES = {
    "variance-cap": (
        "Phase 1 하락·급변장 방어",
        "주가가 위아래로 크게 흔들릴 때 주식 비중을 자동으로 줄이고 현금을 늘려 계좌 반토막을 막아 주는 안전벨트 규칙입니다.",
    ),
    "downside-cap": (
        "Phase 2 회복·집중 추세",
        "떨어지는 날의 변동성만 위험으로 계산합니다. 급락장에서는 현금을 챙기면서도, 1998~1999년 같은 대세 상승장에서는 주식을 일찍 팔지 않고 끝까지 보유합니다.",
    ),
    "trend-252": (
        "장기 방향 확인",
        "1년 전보다 주가가 위인지 아래인지만 확인해 큰 하락장을 피하는 가장 단순한 장기 추세 기준선입니다.",
    ),
    "trend-vote": (
        "중·장기 추세 분산",
        "3개월·6개월·1년 추세 중 살아 있는 신호 개수만큼만 비중을 실어 한 번에 올인하거나 전량 매도하는 실수를 줄입니다.",
    ),
    "berkshire": (
        "장기 가치주 교차확인",
        "워런 버핏의 버크셔가 두 분기 연속 보유한 미국 우량주 공시를 시차 왜곡 없이 대조합니다.",
    ),
    "household": (
        "지연 공시 참고용",
        "공개 시차가 길고 금액 구간만 나와 집중투자 타이밍 신호로는 쓰지 않고 참고만 합니다.",
    ),
    "venture": (
        "비상장 AI 테마 관찰",
        "상장 주식 매매 신호가 아닌 초기 AI 벤처 투자 흐름 참고 자료입니다.",
    ),
    "elevation": (
        "사모 회수 사례 참고",
        "과거 사모펀드 출자 회수 기록으로 개인 상장주식 매매에는 직접 적용하지 않습니다.",
    ),
    "sma": (
        "종목별 차트 과최적화 검증",
        "5일~120일 이동평균 116개를 과거 구간에서 고른 뒤, 한 번도 안 본 최근 63일 실전 구간에서도 통하는지 엄격히 시험합니다.",
    ),
    "scenario": (
        "가설 연구장 3대 관문",
        "약세(20%)·기준(50%)·강세(30%) 목표가를 넣어 기대수익률 12%·손익비 3배·안전마진 20% 통과 여부를 계산합니다.",
    ),
    "risk": (
        "포트폴리오 급락 모의시험",
        "주식 -30%·코인 -50% 같은 폭락이 올 때 내 계좌가 얼마나 흔들리는지 미리 계산합니다.",
    ),
    "barbell": (
        "현금 버퍼 + 핵심주 집중",
        "안전한 현금 버퍼와 검증을 통과한 소수 핵심 종목을 결합해 생존력과 복리 성장을 동시에 노립니다.",
    ),
}

REGIME_PLAYBOOK = (
    dict(
        phase="1단계 · 하락·고변동 방어기",
        condition="코스피 60일선 아래 · 시장 급락 및 반대매매 구간",
        action="현금 버퍼 35% 이상 확보 + 가설 3관문 통과 핵심 2~3종목 압축",
        detail=(
            "대칭 변동성 노출 축소(variance-cap)로 계좌 낙폭을 방어합니다. "
            "바닥권에서 기계적인 -10% 가격 칼손절은 잦은 손절 누적(휩소)을 부르므로 피하고, "
            "현금 버퍼로 진동을 버티되 적자 전환·수주 취소 등 '기업 가설 훼손 공시'가 나올 때만 철회합니다."
        ),
    ),
    dict(
        phase="2단계 · 추세 회복·수익 극대화기",
        condition="코스피 60일선 안착 · 투매 진정 및 실적 회복 확인 후",
        action="하방변동성 노출 축소(downside-cap) 전환 + 12~18개월 집중 보유",
        detail=(
            "상승 변동성 페널티를 없앤 하방변동성 규칙으로 전환해 급반등 구간(1998~1999년형)에서 "
            "핵심 종목 비중이 조기 축소되지 않게 열어 둡니다. 2018~2019년형 W자 장기 박스권에 대비해 "
            "최소 12~18개월 호흡으로 보유합니다."
        ),
    ),
)

HISTORICAL_BACKTESTS = dict(
    basis=(
        "공개 KRX 대표 33종목(10개 업종) · 1995-06 ~ 2026-11 수정주가 일봉 · "
        "신호 다음 날 시가 체결 · 왕복 수수료·거래세 50bp 차감 · 현금 무이자(0%) · "
        "하한가 점하 매도제한 반영 (상장폐지 일부 제외에 따른 생존편향 유의, 감자·급락 생존주 포함)"
    ),
    eras=(
        dict(
            period="1997~1999",
            title="IMF 외환위기 · IT 대세상승",
            shock="환율 급등·연쇄 부도 후 금리 인하·대세 반등 (KOSPI 최대낙폭 -64.7%)",
            lesson="대칭 변동성 캡(+3.98%)은 급등장도 위험으로 보고 현금을 너무 많이 쥐었습니다. 반면 하방변동성 캡+코어 집중은 폭락 방어 후 상승장을 온전히 타 +284.67%를 기록했습니다.",
            rows=(
                ("KOSPI 지수", 57.25, -64.66, "시장 기준"),
                ("동일비중 단순보유", 157.52, -55.20, "분산 보유"),
                ("인기주 3종목 몰빵 (현금 0%)", 91.70, -59.01, "고위험 집중"),
                ("20일 이동평균 단타", 96.67, -41.19, "차트 매매"),
                ("-10% 칼손절 코어 집중", 38.70, -32.40, "잦은 손절 누적"),
                ("대칭 변동성 노출 축소", 3.98, -28.88, "상승장 조기 축소"),
                ("하방변동성 캡 + 코어 집중", 284.67, -33.33, "하방 방어·상승 포착"),
            ),
        ),
        dict(
            period="2006~2008",
            title="글로벌 금융위기 · 유동성 경색",
            shock="신용 버블 붕괴·외국인 투매 (KOSPI -19.1%, 최대낙폭 -54.5%)",
            lesson="-10% 칼손절(-28.61%)과 20일선 단타(-23.90%)는 베어마켓 랠리마다 손절이 누적됐고, 현금 없는 3종목 몰빵은 -73.6% 반토막이 났습니다. 변동성 캡(+27.20%, MDD -20.7%)만이 폭락 전 현금 대피에 성공했습니다.",
            rows=(
                ("KOSPI 지수", -19.06, -54.54, "시장 기준"),
                ("동일비중 단순보유", 7.22, -60.60, "분산 보유"),
                ("인기주 3종목 몰빵 (현금 0%)", 8.34, -73.64, "계좌 -74% 추락"),
                ("20일 이동평균 단타", -23.90, -43.07, "휩소 손실"),
                ("-10% 칼손절 코어 집중", -28.61, -46.12, "반복 손절 누적"),
                ("대칭 변동성 노출 축소", 27.20, -20.66, "위기 방어 1위"),
                ("하방변동성 캡 + 코어 집중", -11.48, -50.31, "바닥 진입 시 1년 +29.7%"),
            ),
        ),
        dict(
            period="2017~2019",
            title="미·중 관세전쟁 · 반도체 피크아웃",
            shock="관세 충격·금리 인상·장기 W자 박스권 (KOSPI +8.5%, 최대낙폭 -26.5%)",
            lesson="급락 후 V자 반등 없이 1년 넘게 옆으로 기는 장세에서는 잦은 차트 매매(-17.16%)가 수수료와 엇박자로 가장 불리했습니다. 저평가 핵심주를 12~18개월 긴 호흡으로 버틴 단순·가치 보유(+27.60%)가 우위였습니다.",
            rows=(
                ("KOSPI 지수", 8.46, -26.50, "시장 기준"),
                ("동일비중 단순보유", 27.60, -22.40, "장기 보유 우위"),
                ("인기주 3종목 몰빵 (현금 0%)", 9.74, -39.20, "고점 추격 부진"),
                ("20일 이동평균 단타", -17.16, -28.02, "박스권 엇박자"),
                ("-10% 칼손절 코어 집중", 27.96, -24.85, "18.10 진입 1년 -5.5%"),
                ("대칭 변동성 노출 축소", 15.55, -26.10, "안정적 방어"),
                ("하방변동성 캡 + 코어 집중", -12.70, -35.42, "장기 횡보 회전비용"),
            ),
        ),
        dict(
            period="2023~2026",
            title="AI 반도체 랠리 · 2026 반대매매 급락",
            shock="상반기 고점 이후 하반기 신용 반대매매 투매 (최근 6개월 KOSPI -39.9%)",
            lesson="2026년 하반기 폭락장(KOSPI -39.9%)에서 대칭 변동성 캡은 손실을 -5.77%(MDD -6.42%)로 막아냈고, 4년 누적에서는 하방변동성 캡+코어 집중이 +167.29%(MDD -28.57%)로 수익과 방어 균형이 가장 뛰어났습니다.",
            rows=(
                ("KOSPI 지수", 111.06, -48.46, "최근 6개월 -39.9%"),
                ("동일비중 단순보유", 211.39, -50.05, "최근 6개월 급락 노출"),
                ("인기주 3종목 몰빵 (현금 0%)", 621.43, -60.17, "MDD -60% 극단 변동"),
                ("20일 이동평균 단타", 51.89, -27.24, "상승폭 절반 반납"),
                ("-10% 칼손절 코어 집중", 120.59, -26.15, "변동장 재진입 지연"),
                ("대칭 변동성 노출 축소", 127.22, -12.64, "최근 6개월 -5.8% 방어"),
                ("하방변동성 캡 + 코어 집중", 167.29, -28.57, "수익·낙폭 균형 우수"),
            ),
        ),
    ),
    crash_entries=(
        ("1997-11 폭락 한복판 진입 (24개월)", "-13.00% (첫 12개월 손절 누적)", "+230.80%", "바닥 진동 후 대세 상승 포착"),
        ("2008-10 금융위기 투매 진입 (12개월)", "+41.10%", "+29.68%", "신용 경색 해소 후 V자 반등"),
        ("2018-10 관세·반도체 급락 진입 (12개월)", "-5.48%", "-13.80% (지수 +3.26%)", "W자 횡보장 → 12~18개월 보유 필요"),
        ("2026-05~11 최근 6개월 반대매매 급락", "KOSPI -39.90%", "대칭캡 -5.77% / 하방캡 -14.95%", "현금 버퍼 35%+가 시드 보존 핵심"),
    ),
)
