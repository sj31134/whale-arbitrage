# 개인 투자관리 시스템 선행 사례와 적용 순서

조사 기준일은 2026년 11월 23일이다. 개인 Mac에서 여섯 기관의 계좌를 조회하고, 다섯 투자 담당자가 열 개 정보 범주를 이용해 판단 근거를 남기는 용도로 비교했다. 공개 저장소와 운영자 문서, Hugging Face 모델·데이터 카드를 확인했다. 아래의 적용 순서와 검증안은 이 프로젝트에 대한 제안이다. 직접 설치, 실계좌 연동, 속도·비용 측정, 전략 수익률 재현은 이번 조사 범위 밖이다.

## 가장 먼저 가져올 세 가지

1. **계좌마다 계산 가능한 성과를 표시한다.** Wealthfolio는 보유 내역만 아는 계좌와 거래 이력이 있는 계좌를 구별한다. 포트폴리오 전체를 한 번에 이관할 필요가 없다. 여기서도 엑셀 계좌에는 보유분의 추정 손익과 원가 회복률을 표시하고, 거래·입출금·배당 등을 대조할 수 있는 기간부터 실제 투자 성과를 계산하는 방식이 맞는다. [Wealthfolio의 두 가지 추적 방식](https://wealthfolio.app/docs/concepts/tracking-modes/)
2. **손실 회복을 세 가지 질문으로 나눈다.** 현재 보유분이 원가에 도달하려면 얼마나 올라야 하는지, 내가 넣고 뺀 돈의 시점을 반영한 수익률이 얼마인지, 운용 판단 자체의 성과가 어땠는지는 각각 다른 질문이다. Portfolio Performance의 예제는 뒤의 두 지표인 금액가중수익률(IRR)과 시간가중수익률(TTWROR)을 같은 원장으로 대조할 수 있게 한다. [공식 계산 예제](https://github.com/portfolio-performance/portfolio-help/blob/master/docs/en/getting-started/measure-performance.md)
3. **계좌 수량과 시장 가격의 증거를 따로 보관한다.** 국내 종목은 KIS 종목정보와 KRX 종목기본정보로 식별하고 KRX 주식·ETF 일별매매정보로 종가를 대조할 수 있다. 장중 체결 시각과 최종 종가, 외화 가격과 환산에 사용한 환율은 각각 기록한다. 회사명이 비슷하거나 직전 종가가 같아도 계좌 원천에서 코드를 확인할 때까지 잠정치로 표시한다. [KIS 공식 저장소](https://github.com/koreainvestment/open-trading-api) · [KRX 제공 목록](https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd) · [가격·환율 이력 설계](https://github.com/portfolio-performance/portfolio-help/blob/master/docs/en/concepts/historical-prices.md)

## 선행 프로젝트 15개

| 프로젝트 | 원문에서 확인한 기능 | 이 프로젝트에서 적용할 범위와 한계 | 원문 |
| --- | --- | --- | --- |
| 1. Wealthfolio | 여러 계좌에 거래이력 방식과 잔고 방식 혼용. 잔고 방식은 현금 흐름을 조정한 성과를 제공하지 않음. 로컬 SQLite 저장 계층 | 계좌 카드에 ‘수량 기준일·거래이력 시작일·계산 가능한 지표’ 표시. 과거가 비어 있으면 첫 검증일을 성과 측정 시작일로 사용 | [GitHub](https://github.com/wealthfolio/wealthfolio) · [두 방식의 지표 비교](https://wealthfolio.app/docs/concepts/tracking-modes/) |
| 2. Portfolio Performance | 복수 계좌 통합, 입출금 반영 IRR, 외부 자금 흐름을 제거한 TTWROR, 가격과 환율 이력 | 거래원장 계산의 독립 대조 기준. 원화·달러를 통합할 때 거래일 환율과 평가일 환율을 구별. 국내 증권사별 수입 양식 호환은 별도 검증 | [GitHub](https://github.com/portfolio-performance/portfolio) · [수익률 예제](https://github.com/portfolio-performance/portfolio-help/blob/master/docs/en/getting-started/measure-performance.md) |
| 3. Ghostfolio | 다계좌, 배당 포함 기간별 성과, 위험 점검, 자체 호스팅. 백엔드는 PostgreSQL·Redis 사용 | 매니저 화면에 ‘어느 계좌·어느 자산이 위험을 키웠는가’를 요약하는 사례. ROAI는 계산식이 다른 IRR·시간가중수익률과 별도 표기. 화면 설계만 참고하면 추가 서비스를 띄울 필요가 없음 | [GitHub 기능·기술 구성](https://github.com/ghostfolio/ghostfolio) |
| 4. rotki | 암호화된 로컬 저장, 거래소·체인의 잔고 추적, 거래 이벤트 해석 | 자산을 거래소 사이에서 옮겼을 때 입금과 출금을 짝지어 내부 이동으로 처리하는 원장 설계에 참고. 실제 지원 기관, 필드, 국내 세무 처리는 개별 확인 사항 | [GitHub](https://github.com/rotki/rotki) |
| 5. KIS Open Trading API | 한국투자증권 공식 예제. 종목정보 파일과 국내·해외 시세·계좌·주문 예제를 구분 | 종목정보로 공개 코드 사전을 만들고 계좌 엑셀과 Mac 안에서 대조. KIS 참고 코드는 나머지 세 국내 증권사의 API 지원 근거가 되지 않음 | [공식 GitHub](https://github.com/koreainvestment/open-trading-api) |
| 6. FinanceDataReader | KRX 상장·상장폐지 목록, 국내 ETF 및 해외 거래소 종목 목록, 가격 조회 | 시장 전체 목록을 받을 때 쓸 수 있는 보조 수집기. 출처 변경·누락에 대비해 공식 원천과 개수·종가 대조. 개인 보유 목록으로 외부 개별 조회를 만들지 않는 구조 | [GitHub 데이터 범위](https://github.com/FinanceData/FinanceDataReader) · [KRX 공식 원천](https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd) |
| 7. OpenBB | 공급자별 데이터 접근. V5 문서는 FRED·SEC·Cboe 등의 공급자별 명령과 자격증명을 명시 | 열 개 분석 범주가 같은 공급자를 쓸 때 원천과 버전을 기록하는 설계 참고. V4용 호출 예제를 복사하면 V5 인터페이스와 맞지 않을 수 있음 | [GitHub](https://github.com/openbq-org/OpenBB) · [V5 공급자 문서](https://github.com/OpenBB-finance/openbb-docs/blob/main/content-odp/python/faqs/data_providers.mdx) |
| 8. CCXT | 바이낸스·업비트 등 거래소 접근을 통일하고 공개 시장 데이터와 인증 API를 구분 | 키 없는 시장별 시세·거래쌍 수집 비교에 활용. 거래소별 지원 함수, 시각의 의미, 원화·달러·USDT 단위를 검증. 개인 잔고 조회 모듈은 기존 로컬 경로 사용 | [GitHub](https://github.com/ccxt/ccxt) |
| 9. Dune Spellbook | 온체인 원자료에 규칙을 적용하는 SQL·dbt 모델. Dune의 거래소 흐름 자료는 당시에 알려진 지갑 라벨과 현재 라벨을 구분 | 고래 담당에 ‘이체 시각·라벨을 알게 된 시각·라벨의 출처’ 기록. 나중에 식별한 거래소 주소를 과거 매도 예측의 근거로 쓰는 오류 방지 | [GitHub](https://github.com/duneanalytics/spellbook) · [당시 라벨 기준 집계](https://dune.com/markets/cex-flows) |
| 10. PublicDataReader | 국토교통부 실거래가·건축 관련 공공데이터용 Python 도구와 사용 가이드. 원천 API는 법정동 코드와 계약년월로 아파트 거래 조회 | 공개 지역·월 자료를 모아 면적·계약시점이 비슷한 비교사례를 로컬에서 선별. 경매 권리·점유·인수금은 별도 사건 원문 필요 | [GitHub](https://github.com/WooilJeong/PublicDataReader) · [국토교통부 API](https://www.data.go.kr/data/15126469/openapi.do) |
| 11. skfolio | 시계열 순서대로 평가하는 Walk Forward, 거래비용, 비중 제약, CVaR 등 하방 위험 지표 | 현상 유지·집중 자산 일부 축소·대안 배분을 같은 기간과 비용으로 비교. 한 시점의 잔고만으로 과거 보유 수량과 실제 전략 성과를 복원할 수 없음 | [GitHub 검증·위험 지표](https://github.com/skfolio/skfolio) |
| 12. TradingAgents | 분야별 분석 뒤 강세·약세 연구자가 논거를 제출하고 위험 검토와 매니저 판단으로 진행 | 기존 보고서 ID에 가장 강한 반대 근거와 ‘무엇이 확인되면 판단을 바꾸는가’를 연결. 분석의 품질을 측정하기 전에는 반복 대화와 주문 모듈을 도입할 이유가 작음 | [GitHub 역할·절차](https://github.com/TauricResearch/TradingAgents) |
| 13. FinanceBench | 금융 공시 질문에 정답과 증거 구절을 연결한 벤치마크. 공개 샘플은 150문항. Hugging Face 데이터 카드에는 CC BY-NC 4.0 표기 | 주식·매니저 보고서가 금액·단위·회계기간·원문 페이지를 일치시키는지 회귀시험. 공개 표본 점수를 초과수익이나 한국 공시 정답률로 환산할 수 없음 | [Hugging Face](https://huggingface.co/datasets/PatronusAI/financebench) · [원저자 GitHub](https://github.com/patronus-ai/financebench) |
| 14. ProsusAI FinBERT | 영어 금융 문장의 긍정·중립·부정 분류. 모델 카드는 가중치에 CC BY-NC-SA 4.0을 명시 | 영어 뉴스 검토 순서의 실험 후보. 감성 점수의 투자수익 예측력은 별도로 평가. 실운영 적용 전 가중치 이용 조건 확인 | [Hugging Face 모델 카드·이용 조건](https://huggingface.co/ProsusAI/finbert) |
| 15. KR-FinBert-SC | 한국어 금융 뉴스·리포트를 활용한 사전학습과 감성 분류. 개발팀이 자체 평가 결과를 공개 | 한국어 뉴스 분류 후보. X의 은어·반어, 종목 동명이인, 같은 기사의 재전송은 별도 표본으로 검증. 한국어 가중치의 실운영 이용 조건은 이번 확인에서 확정하지 못함 | [Hugging Face](https://huggingface.co/snunlp/KR-FinBert-SC) · [개발팀 GitHub](https://github.com/snunlp/KR-FinBert) |

## 다섯 담당과 열 개 정보 범주에 연결하는 방법

| 기존 정보 범주 | 원천과 담당 | 보고서에서 확인할 항목 |
| --- | --- | --- |
| 거시경제·경기 / 금리·환율·신용 | FRED·ALFRED → 매니저, 관련 분야 | 당시 알려진 수치와 뒤에 수정된 수치를 분리. 환율의 기준일과 통화 방향 기록. [FRED 빈티지 조회](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) |
| 글로벌 이슈·지정학 / 정치·의회 / 정책·규제·세제 | GDELT 뉴스에서 사건 탐색 → 담당자가 해당 관할 발표·의결·시행 원문 확인 | 같은 발표를 인용하는 기사는 한 사건으로 묶고 제안·의결·시행일을 구분. 기사 수만으로 정책 효력을 확정하지 않음. [GDELT](https://gdeltproject.org/) |
| 산업·기술·실물 수급 / 개별 자산·권리 | SEC·국토부 → 주식, 미국 소형·고베타, 부동산 | 공시 접수일과 회계 기준일 구분. 미국 소형주는 그 날짜의 시총·베타 측정기간·희석 공시, 부동산은 비교 실거래와 권리 확인 문서를 별도 기록. SEC의 야간 일괄 파일은 개인 보유 목록 없이 수집 가능. [SEC](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) · [국토교통부](https://www.data.go.kr/data/15126469/openapi.do) |
| 가격·수급·포지션 | KRX·CCXT·Dune → 주식, 미국 소형·고베타, 코인, 고래 | 종가·현물·온체인 이체를 구분. 내부 지갑 정리 가능성을 확인하고 거래소 유입의 방향만으로 매도 결론을 내리지 않음. [KRX](https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd) · [Dune](https://dune.com/markets/cex-flows) |
| X·SNS 관심 | X 공개 검색, 필요 시 언어별 분류기 → 관련 분야 | 검토 순서는 원 게시물·작성 시각·독립 원문 대조. 최근 검색의 기본 범위인 최근 7일과 장기 이력을 구별하고, 검색 실패를 언급량 0으로 기록하지 않음. [X 공식 문서](https://docs.x.com/x-api/posts/search/introduction) |
| 내 포트폴리오 노출·현금 일정 | Wealthfolio·Portfolio Performance·skfolio → 매니저 | 거래·현금 일정·동일 자산의 계좌 간 합산은 로컬에서 수행. 분모, 통화, 자료 누락과 가격 기준시각을 표시. [Wealthfolio](https://wealthfolio.app/docs/concepts/tracking-modes/) · [skfolio](https://github.com/skfolio/skfolio) |

## 구현 전에 검증할 세 가지

| 순서 | 기존 코드에 연결할 지점 | 모의 데이터로 확인할 결과 |
| --- | --- | --- |
| 1. 수량·가격·식별 대조 | 계좌 입력 및 시세 화면. [원천 읽기](../../private_accounts/local_sources.py) · [시세 표시](../../private_accounts/monitor.py) | 같은 종목을 두 계좌에 둔 경우, 종목명이 비슷한 ETF 두 개, 휴장·환율 시차를 포함. 확인한 코드만 확정 집계하고 실패하면 마지막 성공 가격과 그 시각이 남아야 함 |
| 2. 거래원장과 성과 대조 | 일일 손실·회복률과 거래이력 기반 성과를 함께 표시. [일일 검토](../../private_accounts/daily_review.py) | 원금 100 → 첫날 10% 상승 → 외부입금 100 → 둘째 날 10% 하락이면 기말 189, 순입금 200, 누적손익 −11, 시간가중수익률 −1%. 계좌 간 내부이체라면 통합 포트폴리오 외부입금은 0. 증권사 명세·샘플 계산기와 같은 결과인지 대조 |
| 3. 전략·보고서의 검증 | 분야별 보고서와 매니저 입력 ID. [보고서 게시](../../private_accounts/reports.py) · [10개 정보 범주](../../data/analysts/README.md) | 현상 유지와 대안에 동일한 현금 흐름·비용·시작일을 적용해 원가 회복일까지의 기간, 최대 낙폭과 회복 실패 비율을 함께 기록. 종료 시점까지 회복하지 못한 구간도 분모에 포함. 보고서는 당시 이용 가능했던 원문만 허용하고, 수치·단위·기간·페이지·반대 근거를 별도로 대조 |

첫 구현 대상으로는 1번, 첫 성과 검증 기준으로는 2번을 권한다. 3번에서 미래 기간으로 넘겨 검증한 결과가 있어야 어느 전략이 어떤 조건에서 더 빨리 회복했는지 비교할 수 있다. 이번 조사로 확정한 것은 각 도구의 공개 범위와 설계 사례이며 사용자 계좌의 기대수익률이나 향후 회복 기간은 측정하지 않았다.
