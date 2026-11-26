# 투자 정보 애널리스트

각 폴더의 `analyst.json`은 실행기가 읽는 애널리스트 정의다. 분야별 질문, 담당 투자 에이전트, 원천과 변수, 기준일 경과 일수를 지정한다. 실행기는 계좌와 무관한 공개 원천을 먼저 수집한다. 계좌·종목별 연결, 사용자가 등록한 근거와 현금 일정은 Mac에서 계산한다.

| 폴더 | 수집·분석하는 변수 |
| --- | --- |
| [macro](macro/analyst.json) | 미국 실업률·소비자물가지수의 관측치와 직전 기간 변화 |
| [financial_conditions](financial_conditions/analyst.json) | 미 국채 10년물, 원/달러, 미 하이일드 스프레드의 수준과 변화 |
| [global_events](global_events/analyst.json) | 유엔 평화·안보 뉴스, GDACS 재난 발표와 브렌트유 가격. 지역과 공급 노출 확인 |
| [politics](politics/analyst.json) | 영국 하원 안건·표결일·찬반 수. 관할권과 표결 단계 확인 |
| [policy](policy/analyst.json) | 미 연준 통화정책 발표 원문·공표일. 시행·영향 확인 |
| [industry](industry/analyst.json) | 미국 산업생산 변화와 저장소의 서울 아파트 공급 연구값 |
| [fundamentals](fundamentals/analyst.json) | 한국 DART 최근 정기공시, 미 SEC 최근 10-Q, 자산별 연구지표. 발행인 식별 |
| [market_flow](market_flow/analyst.json) | 업비트 전체 원화마켓의 가격·전일 대비 변화, 로컬 코인별 고래 순유입, VIX |
| [social](social/analyst.json) | 공식 X 전 세계 트렌드의 응답 순서, 주제, 게시량(제공 시), 조회시각. 개별 주장은 검증 대기 |
| [exposure](exposure/analyst.json) | 계좌·통화 내 비중, 최대 비중, 동일 표기의 계좌 간 중복, 등록 현금 일정. 계좌를 읽을 때마다 계산 |

## 연결 방법

1. 각 원천을 독립적으로 읽고 시간·단위·원문·해석을 정규화한다. 갱신에 실패하면 마지막 성공 자료와 실패 사유를 함께 표시한다. 수집시각과 관측 기준일을 구분한다. 저장소 연구값은 화면에서 재확인 대상으로 표시한다.
2. 계좌별 최신 자료 한 개를 고른다. 담당은 개인 지정, 현금 식별, 거래소, 분야별 공개 식별 목록을 이용한다. 증권사에서 읽은 미분류 상품은 주식 담당의 유형 확인 대상이다. 미국 수급 관찰 목록의 일치는 시가총액·베타 검토 대상이라는 뜻이다.
3. 종목명·공개 식별자·사용자가 입력한 연결어를 로컬에서 정확히 대조한다. 종목 특정 원천이 다른 종목의 공통 자료로 퍼지지 않도록 한다. 한 보유 행에 복수 담당을 붙일 수 있고, 자산가액은 원본 계좌 기준으로 한 번 집계한다. 미등록 실물·부채·현금 일정은 추정하지 않는다.
4. `python3 -m private_accounts portfolio-review equities --signals`가 주식 에이전트용 종목별 직접 근거와 범주별 공통 참고를 JSON으로 반환한다. 같은 방식으로 다섯 분야 모두 사용할 수 있다. 출력에는 비공개 종목·계좌 별칭·비중이 포함된다.

## 실행과 원천

`python3 -m private_accounts dashboard --open`으로 웹 화면을 연다. ‘정보 범주 갱신’은 공개 연구 자료만 수집한다. 계좌 원장은 엑셀 또는 마지막으로 저장된 잔고를 읽는다. 실행 중 주기적으로 공개 자료도 갱신하려면 `--refresh-minutes 60`을 추가한다. 페이지를 다시 읽으면 새 자료가 표시된다. 서버 종료 시 수집도 종료된다.

`python3 -m private_accounts research-refresh`는 전체 원천을, `--category market_flow`는 한 범주를 갱신한다. `--offline`은 저장소 연구 자료만 읽는다. X는 프로세스 환경변수 `X_BEARER_TOKEN`, DART는 `DART_API_KEY`가 있을 때 해당 공식 API를 사용한다. SEC는 운영자가 지정한 `SEC_USER_AGENT`를 지원한다. 키는 문서나 애널리스트 정의 파일에 적지 않는다. 공개 요청 URL에는 보유 종목과 계좌 식별자가 들어가지 않는다.

공개 원천별 범위는 정의 파일의 URL에서 확인한다. 미수집은 관측값 0과 구분한다. 영국 표결과 미 연준 발표는 각각 해당 관할권의 흐름만 보여준다. 국내외 다른 정책, 실물 권리, 게시물 원문 등 자동 원천 밖의 자료는 종목 상세에서 기준일·원문·관측값·해석을 직접 등록할 수 있다. 기본 캐시, 배정, 연결어, 직접 등록 자료는 Git에서 제외된 `private_accounts/.local/`에서만 관리한다.

[수집·분석 구현](../../agents/analyst_feeds.py) · [로컬 연결 및 관리](../../agents/intelligence.py) · [계좌 관리](../../private_accounts/README.md)
