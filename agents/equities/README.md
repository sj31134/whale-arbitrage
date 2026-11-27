# 주식

보유 기업의 이익·현금흐름과 ETF 편입 중복을 점검한다. 신규 후보는 공시와 현재 가격을 대조해 기대수익, 하방과 가설 철회 조건을 제시한다. [공통 투자 지침과 정보 범주](../INVESTMENT_MANDATE.md)

[10개 정보 애널리스트](../../data/analysts/README.md)의 종목 근거와 공통 변수를 함께 받으려면 아래 조회 명령에 `--signals`를 추가한다. 로컬 보유분 조회는 `python3 -m private_accounts portfolio-review equities`를 사용한다.

일반 주식 분석은 하나의 투자 실행기가 시장별 스크리너를 선택해 후보를 평가한다.

| 시장 | 투자 CLI 옵션 | 구현 |
| --- | --- | --- |
| 미국 | `--universe us_equities` | [미국 주식 스크리너](screeners/us_equity_screener.py) |
| 한국 | `--universe kr_equities` | [한국 주식 스크리너](screeners/kr_equity_screener.py) |
| 일본 | `--universe jp_equities` | [일본 주식 스크리너](screeners/jp_equity_screener.py) |
| 중국 | `--universe cn_equities` | [중국 주식 스크리너](screeners/cn_equity_screener.py) |

옵션은 [투자 CLI](../../branch/investor_agent/main.py)에서 선택한다. 미국 주식 후보의 단기 수급과 가격 변곡점은 [미국 소형·고베타 주식 분야](../us_small_cap_high_beta/)에서 다룬다.

## 국내·미국 상장 종목 이동평균 검증

저장소 루트에서 `python3 -m private_accounts.equity_screen --help`로 실행 인자를 확인한다. `--as-of`는 시간대가 있는 공개 시세 수집 기준시각, `--kr-day`와 `--us-day`는 각 시장의 마지막 완료 거래일이다. `--actions`에 공개 연구 DB를 지정하면 해당 원천에 기록된 분할·병합일이 분석 기간에 있는 종목을 별도로 보류한다. 사건 원장이 없는 종목은 가격 단절 검사만 적용된다. 배당·현금 이자·상장폐지 종목의 누락은 별도로 검토한다.

결과 경로를 `private_accounts/.local/equity_screens/YYYYMMDDTHHMMSS.sqlite3`로 지정하면 완료된 결과가 인증된 퀀트 화면에 표시된다. 시각은 실제 실행의 KST 시각으로 바꿔 사용한다. 시장별 합계, 공개 종목 검색, 현재 선택한 보유 종목과의 로컬 대조를 지원한다. 결과 DB는 종목별 입력·원천·비용·입력 해시와 마지막 63일의 116개 이동평균 성과를 저장한다.

## 이 폴더의 파일

[이동평균 검증 결과와 전진검증 표본](memos/2026-11-24-sma-study.md) · [전체 메모](memos/) · [스크리너](screeners/)

보호 경로와 공용 저장소에 있는 담당 파일은 [전체 분류표](../FILE_MAP.csv)의 `owner=equities`로 찾을 수 있다.

## 공개 전략 관리

인증된 대시보드 **전략 관리**에서 규칙, 버전, 논문·공시, 계산 표본, 보류 사유, 비용 두 배 결과와 실행 이력을 확인한다. 가격 규칙은 `trend-252`(12개월 추세), `trend-vote`(3·6·12개월 추세 합의), `variance-cap`(대칭 변동성 노출 축소 · 1단계 방어), `downside-cap`(하방 변동성 노출 축소 · 2단계 회복·집중) 네 가지를 운영하며, 상단에 2단계 시장 레짐 가이드, 3단 자본배분 바구니·IPS 리스크 헌장, **한국·미국 장전 vs 장마감 실전 복기 표 및 누적 투자 오답노트 원장(`#mistake-notes`, 사용자 직접 기록 포함)**, 1997~2026년 4대 매크로 위기(`1997~1999`, `2006~2008`, `2017~2019`, `2023~2026`) 실증 백테스트 비교 막대를 함께 표시한다. 가격 규칙의 일시정지는 다음 실험부터 적용한다. 공시 관찰을 일시정지하면 종목별 대조에서 제외하며 원문 기록은 조회할 수 있다. **퀀트 연구**에서 선택한 종목과의 대조(21일 실현변동성, 대칭·하방 변동성캡 권장 비중, 60일선 추세 위치 포함)는 Mac 안에서 처리한다. [조사 근거와 최초 실험](memos/2026-11-24-strategy-evidence.md)

```sh
python3 -m private_accounts strategies list
python3 -m private_accounts strategies run
python3 -m private_accounts strategies history variance-cap
python3 -m private_accounts strategies history downside-cap
python3 -m private_accounts strategies evidence berkshire --as-of 2026-11-16T16:00:03-05:00
python3 -m private_accounts discover --refresh
```

**신규 대장주 발굴(`/discover`)**은 보유 목록 입력 없이 국내·미국 상장 후보의 공개 수급·일봉 상대강도·컨센서스/공시·SNS 관심도·환율/연준 흐름·유엔 안보 지정학 변수를 100점 만점으로 일별 추적하며, 개인 보유분 제외 대조는 Mac 화면 렌더링 시점에만 수행한다.

`daily-review`와 수동 재계산은 최신 완료된 공개 시세 실험과 같은 시각표의 독립 종가 검증을 읽는다. 새 검증본이 없으면 마지막 결과와 시장 마감일을 유지한다. 새 원문을 검토한 담당은 `strategies import-event` 표준입력에 `strategy, effective, available, url, items`를 넣는다. 날짜·공개시각·HTTPS 원문은 문자열, `items`는 해당 기준일에 원문에서 확인한 공개 발행인 표본의 전체 목록이다. 같은 기준일의 정정은 실제 정정 공개시각에 새 버전으로 추가한다. 13F는 분기 말과 SEC 접수시각, PTR은 거래일과 실제 공개 확인시각을 구분한다. 가격 규칙은 전략 명세 및 검증된 계산 코드를 추가하고 버전을 올린다.
