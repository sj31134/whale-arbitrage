# Mac 투자 작업 접수와 인계

Codex·Claude·Cowork·Antigravity 네 도구 중 어느 대화에서든 다음 문장을 붙여 넣을 수 있다.

> 계좌 최신성 감사를 접수해. Mac 기본 작업 트리에서 작업지시서를 발급하고 이 세션이 선점한 뒤 진행해.
>
> 종목별 이동평균 백테스트를 접수해. Mac에서 선택한 종목의 시장·완료 거래일·비용 차감 미사용 기간을 확인해.
>
> 오늘 수급·공시를 반영한 매니저 브리핑을 접수해. 한국·미국의 마지막 완료 거래일을 각각 확인하고 주식 담당의 실제 게시 ID를 인용해.
>
> 병렬 작업 결과 종합을 접수해. 각 담당의 인계와 실제 산출물을 대조하고, 기존 분야 보고서 ID를 매니저 검수 보고서에 연결해.

## 누가 무엇을 실행하는가

표의 CLI 명령은 저장소 루트의 `python3 -m private_accounts` 하위 명령이다. ‘투자 CLI’는 `branch/investor_agent/main.py`다. 공개 원천·담당·유효기간의 세부 설정은 기존 `data/analysts/<범주>/analyst.json`, 투자 판단 기준은 [투자 운영 기준](../INVESTMENT_MANDATE.md), 코드 담당은 [파일 분류표](../FILE_MAP.csv)가 기준이다.

| 구분·책임 | 실행 진입점 | 읽는 원천 | 쓰는 결과·허용 동작 | 실패 시 인계 |
|---|---|---|---|---|
| 투자 매니저 · 합의·충돌·판단 보류 종합 | publish-report manager | 참여 분야 게시 ID, 기준시각, 원문 | 로컬 desk_reports.json에 종합 게시 | 원문을 검토한 분야 → 사용자 |
| 고래 · 체인 이동과 라벨 | agents/whale/chain/multi_chain_collector.py, portfolio-review whale | 공개 체인 거래와 주소 라벨 | 체인 관측·분야 보고서. 내부이체 여부 확인 | 코인·매니저 |
| 코인 · 가격·파생·환매 위험 | 투자 CLI --universe crypto, portfolio-review crypto | 거래소 공개 호가·파생·토큰 약관 | 후보 평가·코인 보고서 | 고래·매니저 |
| 부동산 · 현금흐름·권리 | 투자 CLI --universe real_estate, 경매는 InvestorAgentRunner.run_real_estate_subagent_pipeline() | 실거래·사건 원문·등기·점유 | 물건별 검토·분야 보고서 | 권리 미확인 시 매니저 |
| 주식 · 기업·ETF·계좌 시세·SMA | 투자 CLI --universe {kr,us,jp,cn}_equities, portfolio-review equities, 인증 화면 /quant | 공시·거래소 시세·완료 일봉, 로컬 계좌 | 후보 메모·로컬 계좌 평가·quant-<digest>.json·분야 보고서 | 시세·원장은 ①, SMA는 ②, 판단은 매니저 |
| 미국 소형·고베타 · 촉매·유동성 | 투자 CLI --universe order_flow --market us | 공개 시총·베타 기간·거래대금·공시 | 단기 수급 의견·분야 보고서 | 주식·매니저 |
| 거시경제 macro | research-refresh --category macro | FRED 실업률·물가 | 관측·수정 확인 | 배정 분야 → 매니저 |
| 금융여건 financial_conditions | research-refresh --category financial_conditions | 국채·환율·신용스프레드 | 수준·변화 저장 | 배정 분야 → 매니저 |
| 글로벌 이슈 global_events | research-refresh --category global_events | UN·GDACS·브렌트유 | 사건시각·영향 경로 검토 | 배정 분야 → 매니저 |
| 정치 politics | research-refresh --category politics | 영국 하원 표결 | 관할권·표결 단계 저장 | 배정 분야 → 매니저 |
| 정책 policy | research-refresh --category policy | 연준 발표 원문 | 공표·시행 구별 | 배정 분야 → 매니저 |
| 산업 industry | research-refresh --category industry | 산업생산·저장소 서울 공급자료 | 산업·공급 관측 저장 | 배정 분야 → 매니저 |
| 기초체력 fundamentals | research-refresh --category fundamentals | DART·SEC·등록 연구 | 발행인 확인·공시 기준일 저장 | 주식 등 배정 분야 |
| 수급 market_flow | research-refresh --category market_flow, market-scan | 거래소·고래 집계·VIX·시장 표본 | 공개 관측·시장별 완료일 저장 | 해당 시장 담당 |
| 소셜 social | research-refresh --category social | 공식 X 트렌드·수신시각 | 관심 변화 저장·주장 원문 재확인 | 배정 분야 → 매니저 |
| 노출 exposure | portfolio-review <분야> --signals, intelligence.board | Mac 원장·스냅샷·현금 일정 | 로컬에서 계좌·통화별 계산 | 계좌 담당 ① |
| 공개 수집기 · 원천별 마지막 성공 보존 | research-refresh, price-history의 공개 수집 단계 | 카탈로그·공개 상장목록 | .local/analyst_observations.json·public_quotes.sqlite3 등. 계좌 입력 없이 갱신 | 범주·시세 담당 |
| 로컬 평가·연구 엔진 · 대조와 검증 | live_valuation.mark_account, price_history.snapshots, quant_page.experiment, 투자 CLI | 계좌와 시세의 로컬 조인·원천별 일봉·연구 데이터 | account_marks.sqlite3, SMA 캐시, 투자 CLI 메모 | 계좌 ①·주식 ②·매니저 |
| 거래 봇 · 보류 | trading_bot/core/bot_engine.py의 TradingBotEngine.start, execution/order_executor.py | 보류 구현과 가짜 요청 시험 | 허용 범위는 코드·차단 시험 확인 | 사용자 |
| Codex·Claude·Cowork·Antigravity · 실행 세션 | work register / ticket / claim / status / handoff / verify | 공개 지시서·기본 Mac의 로컬 원장 | 원자적 선점·상태·인계·검증 기록. 사용자가 지시서를 전달 | 다음 세션 또는 사용자 |

범주 1~9의 자동 원천은 획득 시각과 관측 기준일을 구별해 로컬 캐시에 기록한다. 수집 실패 시 마지막 성공값과 실패 상태를 확인한다. 범주 10과 보유 목록 대조는 Mac 안에서만 처리한다. 관리자가 보는 로컬 상세 상태에도 세션 ID 등이 있으므로 도구 사이에는 **ticket 출력만** 전달한다.

## 접수부터 완료까지

아래 날짜는 재현용 예시다. 운영 요청에서는 거래소 현지 달력·휴장·조기 마감을 확인하고 확인 시점의 날짜를 입력한다. 기준시각은 시간대가 필수다. 등록기는 미래 날짜를 거부하며 거래소 달력을 자체 조회하지 않는다.

```sh
w() { python3 -m private_accounts work "$@"; }
asof='2025-01-04T08:00:00+09:00'
w status
w register '계좌 최신성 감사' --as-of "$asof" --day KR=2025-01-03 --day US=2025-01-03
w register '종목별 이동평균 백테스트' --as-of "$asof" --day US=2025-01-03
w register '오늘 수급·공시를 반영한 매니저 브리핑' --as-of "$asof" --day KR=2025-01-03 --day US=2025-01-03
w register '병렬 작업 결과 종합' --as-of "$asof" --day KR=2025-01-03 --day US=2025-01-03 --with-desk equities --with-desk crypto
```

같은 시장·시각에 여러 종목을 검토하면 각 SMA 요청에 Mac 내부의 `--position "$position_id"`를 지정한다. 이 값은 작업지시서에서 제외되며 verify가 해당 보유 행과 실험 입력의 종목을 대조한다. 같은 조건으로 재접수하면 같은 작업 ID를 돌려준다.

주식 외에 코인도 참여하면 브리핑 등록 시 `--with-desk crypto`를 추가한다. 확인된 선행 작업에만 `--after work-…`를 지정한다. 보고서 해시를 선행 작업 ID로 사용할 수 없다. 구현 작업은 등록 시 `--development`를 붙인다. 공용 파일 편집이 필요하면 접수할 때 `--write private_accounts/view.py`처럼 실제 경로를 각각 선언한다. 분석 작업의 쓰기는 산출물에 한정된다.

```sh
id='work-발급받은ID'
w ticket "$id"
s=$(w session)
w claim "$id" --tool Codex --session "$s"
w status "$id"
w handoff "$id" --session "$s" --to Claude --reason '담당 인계'
next_session=$(w session)
w claim "$id" --tool Claude --session "$next_session"
```

같은 세션의 재개는 같은 ID로 다시 claim한다. 세션이 끊기면 기본 Mac에서 상세 상태의 마지막 로컬 선점 기록을 확인하고 기존 세션 ID로 handoff한 뒤 새 세션이 claim한다. 외부 대화 종료나 침묵만으로 선점을 해제하지 않는다. 다른 worktree에서 최신 대시보드가 빠졌다면 기본 Mac에서 다음처럼 해당 사본을 지정해 확인한다.

```sh
w --checkout /path/to/worktree ticket "$id"
w hold "$id" --session "$next_session" --reason '자료 대기'
w claim "$id" --tool Claude --session "$next_session"
w fail "$id" --session "$next_session" --reason '시험 실패'
```

`queued`는 발급, `running`은 해당 이름의 도구가 로컬에서 수락한 기록, `handoff`는 인계 대기, `held`는 보류, `failed`는 실패, `done`은 완료 검증이다. 선점은 이 CLI에 참여하는 세션 사이에서 적용된다. 원장에 접수되지 않은 별도 챗과 직접 편집하는 프로그램의 상태는 외부 상태 미확인으로 남는다. 원장은 기본 worktree의 `private_accounts/.local/work.sqlite3` 하나에 저장한다. 실제 데이터 조회·실험·보고서 게시도 기본 Mac에서 실행한다.

### 결과를 확인하는 방법

- **계좌 감사**는 계좌·시세·환율·화면의 실제 기준시각을 대조한다. 감사 보고서의 근거 이름에 `원장`, `시세`, `환율`, `화면 대조`를 넣는다. 확인된 자료와 시각만 사용한다. verify가 같은 KST 날짜, 기준시각 이내 시점평가가 있는지도 확인한다.
- **SMA**는 인증된 퀀트 화면에서 로컬 종목을 선택해 실험한다. 보고서에 `완료 일봉`, `116개 SMA`, `비용 차감`, `미사용 기간` 근거를 넣고, verify에 Mac의 실험 파일명에서 읽은 전체 digest를 전달한다. 검증기는 원천 입력 해시·해당 시장 마지막 거래일·저장 결과를 재계산해 대조한다. 성과가 나쁜 전략도 검토를 완료할 수 있다. 미사용 구간이 부족하면 hold한다.
- **브리핑**은 market_flow와 fundamentals를 각각 갱신하고 시장별 일자와 원문을 확인한다. 참여 분야별 보고서를 먼저 게시한다. 매니저의 inputs에 그 ID를 넣고 `수급`, `공시` 원문 URL과 시각을 기재한다. 거래일별 근거 이름은 세 사례 모두 `US 2025-01-03`처럼 쓴다. 실제 담당·각 보고서의 기준시각·게시 원장을 대조한다.
- **개발 완료**는 verify가 실제 담당 회귀시험을 실행해 성공해야 한다. 작업 ID는 개발 인계·선행 작업에만 사용한다. 기존 구현이 일부 보인다는 사정만으로 외부 세션이 작업을 마쳤다고 판정할 수 없다.

```sh
# 실제 확인한 로컬 보고서 JSON을 기존 게시기로 전달한다.
report=$(python3 -m private_accounts publish-report equities < "$local_report")
w verify "$id" --session "$s" --report "$report"                         # 감사
w verify "$id" --session "$s" --report "$report" --experiment "$digest"  # SMA
manager_report=$(python3 -m private_accounts publish-report manager < "$local_summary")
w verify "$id" --session "$s" --report "$manager_report"                # 브리핑
w verify "$id" --session "$s"                                          # 개발
```

명령은 각 사례의 현재 선점 세션에서 개별 실행한다. 실제 보고서 작성 양식은 [기존 게시 규약](../../private_accounts/README.md#분석-결과-게시)에 있다.

### 2026-11-24 병렬 작업 검수

검수 기준은 19:37 KST다. 아래 인계 시각은 각 작업의 마지막 응답이며, 시장 연구의 관측 기준은 17:10 KST다. Mac에 저장된 최종 완료 일봉은 한국 11월 24일, 미국 11월 23일, Binance 토큰화 주식 11월 23일(UTC)이다.

| 작업 | 인계 KST | 직접 대조한 결과 | 다음 확인 조건 |
|---|---|---|---|
| 계좌 평가·데이터 최신성 | 16:07 | 원장 입력 후 시세·환율 변화가 평가와 화면 비중에 반영되는 회귀시험 통과. 운영 DB에 당일 시점평가가 있다. 시세 원천 16곳의 마지막 저장 상태가 수집 완료였고, 마지막 성공 시각은 서로 달랐다. | 개별 호가 시각·지연과 잔고 원천 시각을 함께 본다. DART·SEC 자동 조회에는 공백이 있고 별도 확인한 공시 표본이 있다. |
| 종목별 5~120일 이동평균 | 16:29 | 공개 토큰화 주식 25개, 완료 일봉 3,596개를 현재 엔진에서 재계산했다. 종목별 125~166개로 25개 모두 선정 보류다. 운영 화면의 404를 기존 대시보드 갱신 절차로 복구하고 인증 응답을 확인했다. | 동일 거래장·상품에서 연속 일봉 최소 394개와 비용 근거 확보. 마지막 63개 봉을 분리하고 인접 기간도 검증한다. 편도 25bp는 과거 호가 부재에 따른 연구 가정이다. |
| Codex·Claude·Cowork 작업 인계 | 16:07 | 선점·인계·게시물 검증 경로와 퀀트 연동 회귀시험 통과. 네 원작업의 접수와 완료 영수증은 각각 0건이었다. 이번 검수를 별도로 발급·선점해 완료했다. | 새 작업은 실행 전에 접수한다. 종합 검수에서는 당시까지 실제 게시된 참여 분야 ID를 인용한다. 원작업의 완료 여부는 해당 작업의 영수증에서 확인한다. |
| 공개 데이터와 기간별 투자 가설 | 17:13 | 공개 DB에서 일별 가격 1,905,619건, 변수 관측 37,627건, Binance 현물 요약 대상 526쌍을 확인했다. 연구 결과 DB에서 1주·2주·1개월·3개월 모두 채택된 방향 예측이 없었다. 17:11에 게시한 주식·코인 보고서 두 건을 매니저 화면에서 대조했다. | 기준 예측 대비 새 표본외 성과를 확인한다. 526쌍의 요약 범위와 개별 전략에 이용 가능한 연속 가격 이력은 따로 집계한다. |

19:38 KST에 매니저 종합 검수 보고서를 게시했다. 로컬 원장은 이번 검수 한 건을 완료로 기록하며, 보고서에서 당시의 주식·코인 분야 게시물로 이동할 수 있다. 검수는 데이터 범주와 다섯 담당의 기존 화면도 함께 확인했다.

19:41 KST에 대시보드가 사용하는 공개 일봉 DB에서 일반 상장 종목의 연구 가능 범위를 추가 집계했다. 한 원천에 양수인 시가·종가가 함께 있는 날이 394개 이상이고 마지막 유효 봉이 해당 시장의 마지막 완료일인 거래장·심볼·통화 조합은 KRX 2,917개, 미국 3개 거래장 합계 5,082개였다. 이는 과거 가격의 1차 선별이다. 연속성, 기업행동, 표본외 성과와 체결 비용은 종목별로 검증해야 한다. 이 집계에서 국내·미국 종목 전체에 대한 이동평균 선정률은 산출하지 않았다.

11월 24일 검수 시점 작업 트리의 전체 회귀시험은 기본 122건, 투자 분석 엔진 28건, 거래 봇 시험 14건이 통과했다. 경로 검사에서 등록된 파일 801개와 호환 경로가 일치했다.

### 2026-11-26 Codex → Claude 인계

Codex 세션은 10:08 KST 브리핑 완료 뒤 중단됐고 21:02 KST에 Claude 세션이 이어받았다. 인계 시점의 원장은 22건 모두 완료였으며 진행·인계·보류·실패 상태는 없었다. 마지막 커밋 `2c26f04` 이후 작업 트리에는 추적 파일 수정 25개와 신규 파일 75개가 있었고, 11월 25일 16:36 KST 이후 수정된 소스는 없었다.

| 작업 | 완료 KST | 직접 대조한 결과 | 다음 확인 조건 |
|---|---|---|---|
| 야간 경보 문서 반영 | 22:14 | `market_review`의 구현과 시험을 읽고 [계좌 관리 문서](../../private_accounts/README.md#미국-반도체-마감과-한국-시초가-경보)에 대상 거래일·인정 관측·세 판정·수동 입력을 기록했다. SMA 구현 경로로 접수해 담당 회귀시험으로 마감했다. | 미국 휴장일은 자체 판별하지 않는다. 기준 −5%의 과거 적중률을 검증한 메모가 없다. |
| 전체 회귀시험 | 22:29 | 기본 133건, 투자 분석 엔진 28건, 거래 봇 14건이 통과했다. 경로 검사에서 등록된 파일 812개와 호환 경로가 일치했다. | 연결 폴더를 마운트한 원격 Linux Python 3.10에서 실행했다. Mac 키체인·Swift 수집기·실인증은 실행하지 않았다. |
| 변경 묶음 정리 | 22:25 | 변경 파일 100개를 거래 보류, 공개 수집·계좌 평가, 퀀트·전략, 일일 검토·가설 연구, 문서, 대시보드·CLI·원장 연결의 여섯 단위로 나눴다. 저장소 밖 복제본에서 순서대로 커밋해 단계마다 시험했고 실패가 없었다. 마지막 단계의 파일 목록과 내용이 작업 트리와 일치했다. | 경로 검사는 분류표가 들어가는 마지막 단위에서만 일치한다. 깨끗한 체크아웃에는 `data/project.db`가 없어 통합 시험 2건을 건너뛴다. |

원장은 코드·문서 변경을 계좌 감사와 SMA 두 구현 경로로만 접수한다. `--write`로 선언할 수 있는 경로도 `private_accounts/`, `agents/`, `tests/` 아래로 한정된다. 문서만 고치는 작업과 루트 문서는 이 선점 대상에 들어가지 않으므로, 같은 파일을 다른 세션이 편집 중인지 별도로 확인한다.

**실행 환경.** Codex 인계 기록에 따르면 Mac 셸의 기본 Python에는 `openpyxl`·`pyupbit`가 없어 CLI와 회귀시험을 `/usr/bin/python3`로 실행했다. 연결 폴더로 접속한 원격 세션에서는 세 가지를 먼저 확인한다. `work` 명령은 `git worktree list --porcelain -z`를 쓰므로 git 2.36 이상이 필요하다. 원장 SQLite는 기록할 때 저널 파일을 지우므로 폴더의 삭제 권한이 있어야 한다. 계좌 동기화, 키체인, 로컬 대시보드 접속은 Mac 자체에서만 실행할 수 있다.

22:33 KST에 여섯 단위를 `main`에 커밋하고 앞선 미푸시 2건과 함께 `origin/main`에 반영했다(`aebc936`). 커밋 도중 연결 폴더의 `.git/index`가 갱신 직후 빈 것으로 읽혀 다섯 커밋의 트리가 잘못 만들어졌다. 푸시 전에 발견해 저장소 밖 임시 인덱스(`GIT_INDEX_FILE`)로 같은 단위를 다시 만들었고, 최종 트리가 작업 트리와 일치함을 확인한 뒤 푸시했다. 연결 폴더에서 커밋할 때는 임시 인덱스에서 트리를 만들고 커밋마다 트리의 파일 수를 확인한다. 상태 조회에는 `GIT_OPTIONAL_LOCKS=0`을 붙여 인덱스를 다시 쓰지 않게 한다.

22:50 KST에 원장의 수락 도구에 Antigravity를 추가했다. `work claim --tool Antigravity`와 `work handoff --to Antigravity`를 쓸 수 있고, 인계 대상이 아닌 도구의 선점은 전과 같이 거부된다. 기존 24건의 기록은 바뀌지 않는다.
