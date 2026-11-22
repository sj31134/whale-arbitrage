# 개인 계좌 잔고 관리

개인 Mac 터미널에서 실행한다. `status`는 등록 기록과 마지막 잔고 기준시각을 보여 준다. 키나 은행 계좌번호를 입력할 필요 없이 실행할 수 있다.

```sh
python3 -m private_accounts status
```

| 기관 | CLI 이름 | 수집 범위 | 첫 등록 |
| --- | --- | --- | --- |
| 한국투자증권 | `kis` | 표준 CSV에 입력한 주식·현금 잔고 | `import-csv kis` |
| 미래에셋증권 | `mirae` | 표준 CSV에 입력한 주식·현금 잔고 | `import-csv mirae` |
| 메리츠증권 | `meritz` | 표준 CSV에 입력한 주식·현금 잔고 | `import-csv meritz` |
| 나무증권(NH투자증권) | `namuh` | 표준 CSV에 입력한 주식·현금 잔고 | `import-csv namuh` |
| 바이낸스 | `binance` | 현물 지갑의 가용·잠긴 수량 합계, USDT 기준 평가 | `connect binance` |
| 업비트 | `upbit` | 키가 속한 포켓의 자산별 가용·잠긴 수량 합계, KRW 기준 평가 | `connect upbit` |

한 기관에 계좌·포켓이 여러 개면 각 명령에 `--account isa`처럼 별칭을 붙인다. 기본값은 `main`이다. 별칭으로 실명이나 계좌번호를 쓰지 않는다.

## 엑셀과 API 설정으로 시작하기

개인 Mac에서 이 프로젝트를 사용하면 엑셀만으로 계좌를 조회할 수 있다. Python 환경에 `openpyxl`이 필요하다. 처음 설정할 때는 아래 명령을 순서대로 실행한다. 엑셀과 키 설정만 준비하는 과정에는 거래소 접속이나 Swift 빌드가 없다.

```sh
python3 -m private_accounts setup-local
python3 -m private_accounts status
python3 -m private_accounts dashboard
```

- **잔고 원본**은 `private_accounts/accounts_stocks.xlsx`다. 열 이름은 `증권사, 계좌, 종목, 평가손익, 수익률, 보유주식수, 평가금액, 매입단가, 현재가`를 사용한다. 수익률은 Excel 퍼센트 형식으로 저장한다. 평가금액 셀의 서식에는 KRW(₩), USD(US$), USDT 중 하나가 명시되어야 한다. 파일 수정시각은 화면에 별도로 표시한다. 엑셀은 메모리에서 읽으며 포트폴리오 파일을 새로 생성하지 않는다. 파일을 편집한 뒤에는 `setup-local`로 권한과 계좌 매핑을 다시 확인하고 페이지를 새로 고친다.
- **키 원본**은 첫 설정 때 루트 `.env`에서 `private_accounts/.local/credentials.env`로 옮긴다. 루트에는 안내 주석만 남긴다. 이후 키 추가·교체는 보호된 `credentials.env`에서 한다. 개인 폴더 권한은 `0700`, 키·엑셀·연결 상태 파일은 `0600`이다. 환경파일은 로컬 평문이다. macOS에서는 설정할 때 엑셀과 개인 설정 폴더를 Time Machine 백업에서 제외하고, 개인 잔고 DB를 쓸 때도 해당 폴더의 제외 여부를 확인한다. 이 개인 파일들을 포함해 폴더 전체를 수동으로 압축·업로드하면 해당 파일도 들어갈 수 있다.
- 키 설정은 한 줄에 `이름=값`으로 입력한다. 공백이 포함된 기존 거래소 필드명과 `BINANCE_API_KEY`·`BINANCE_API_SECRET`·`UPBIT_ACCESS_KEY`·`UPBIT_SECRET_KEY`를 지원한다. 프로그램은 셸을 실행하거나 프로세스 공통 환경에 키를 내보내지 않는다. 외부 시세 서비스용 키는 거래소의 계좌 인증에 사용하지 않는다.
- 계좌 매핑은 기관명과 계좌 구분을 이용한다. 약칭만 있는 기관은 복수 계좌 구분이 유일하게 일치할 때도 **확인 필요**로 표시한다. `status`에서 계좌 별칭·엑셀 등록 여부와 키 준비·등록 기록을 확인할 수 있다. 국내 증권사 키는 실제 인증에 쓰지 않는다. 기관의 자체 약칭을 확인한 경우 보호 파일에서 해당 키 쌍의 기관 접두어를 표의 CLI 이름(예: `kis`)으로 맞추고 `setup-local`을 다시 실행한다. 엑셀에 없는 계좌는 미수집으로 표시한다.
- 계좌별로 에이전트용 데이터를 확인하려면 `python3 -m private_accounts agent-view kis --account 별칭 --source workbook`을 실행한다. 별칭은 `status`에서 확인한다. 기본값 `latest`는 같은 기관·별칭의 저장된 잔고 기준시각과 엑셀 수정시각을 비교한다. `--source snapshot`으로 API·CSV 잔고만 조회할 수도 있다. 한 계좌·한 평가통화 안에서 비중을 계산하며, 두 출처의 금액을 합산하지 않는다.
- API 사용을 시작할 때는 아래의 거래소별 읽기 전용 권한을 확인한 뒤, `build`를 한 번 실행하고 `connect-env binance`, `connect-env upbit`, `sync-all` 순으로 실행한다. 각 명령 앞에 `python3 -m private_accounts`를 붙인다. `connect-env`는 선택한 거래소 키 쌍만 로컬 파이프로 서명 수집기에 전달한다. 실인증에 성공해야 키체인에 등록한다. 엑셀에서 해당 거래소의 계좌가 하나면 그 별칭을 쓰며, 여러 개면 직접 `--account 별칭`으로 선택한다. 바이낸스는 현물 지갑만 조회한다.

## 거래소 키 등록과 갱신

1. Mac에 Python 3.9 이상과 Xcode Command Line Tools가 필요하다. 처음 체크아웃했거나 Swift 수집기 소스가 바뀌었으면 저장소 루트에서 `python3 -m private_accounts build`를 실행한다.
2. **바이낸스**에서 이 수집기 전용 HMAC 키를 만든다. 읽기와 접속 IP 제한을 켜고 사용할 공인 IP만 등록한다. 거래·마진·선물·옵션·이체·출금 권한을 모두 끈다. 수집기가 매번 거래소의 권한 응답을 확인한다. 위험 권한이 켜져 있거나 필수 항목이 없거나 해석할 수 없는 권한 필드가 있으면 잔고 조회 전에 중단한다. [바이낸스 키 권한 명세](https://developers.binance.com/docs/wallet/account/api-key-permission)
3. **업비트**에서 사용할 포켓을 선택하고, 개인 Mac의 허용 공인 IP와 **자산조회 한 가지**만 지정한 키를 만든다. 수집기는 이 권한 설정을 자동 판별할 수 없으므로 발급 화면에서 본인이 확인한 뒤 터미널에 `READONLY`를 입력한다. 이후 권한을 바꾸거나 키를 교체할 때도 발급 화면을 확인한다. [업비트 키 발급](https://docs.upbit.com/kr/docs/api-key) · [계좌 조회](https://docs.upbit.com/kr/reference/get-balance)
4. 아래 명령을 실행하고 각 키를 **본인 Mac 터미널의 숨김 입력란**에 입력한다. 키는 인증·조회 성공 후 macOS 로컬 키체인에 저장한다. `connect`는 키 등록까지 수행하며, `sync-all`이 첫 잔고를 저장한다.

```sh
python3 -m private_accounts connect binance
python3 -m private_accounts connect upbit
python3 -m private_accounts sync-all
python3 -m private_accounts status
```

다음 갱신에도 `sync-all`을 실행한다. 특정 계좌만 갱신하려면 `sync upbit --account main`을 쓴다. 각 명령 앞에는 `python3 -m private_accounts`를 붙인다. 한 거래소가 실패해도 등록된 다른 거래소는 계속 갱신하고, 마지막에 실패한 별칭을 표시한다. 바이낸스 선물·마진·Earn 및 체결내역은 수집 범위 밖이다.

공개 시세를 한 번에 받아 잔고 수량에 곱한다. 업비트 원화와 바이낸스 USDT 현금은 해당 평가통화로 1이다. 직접 거래쌍이 없거나 시세 조회가 실패하면 수량은 보존하고 해당 자산의 평가액은 비운다. [업비트 원화 시세](https://docs.upbit.com/kr/reference/list-quote-tickers) · [바이낸스 현물 계좌·시세 명세](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)

## 국내 증권사 잔고 가져오기

현재 확인한 공식 자료에서는 개인이 발급받는 인증키에 대해 증권사 서버에서 주문을 차단하는 설정 절차를 확인하지 못했다. 메리츠 MCP의 조회 전용 설정은 해당 프로그램에 적용된다. 국내 네 곳은 개인 키를 받지 않고 아래 형식의 CSV로 관리한다. [한국투자증권](https://apiportal.koreainvestment.com/apiservice) · [미래에셋증권](https://securities.miraeasset.com/hki/hki3032/n05.do) · [메리츠증권](https://openapi.imeritz.com/mcp) · [나무증권](https://www.nhplug.com/apiservice)

증권사에서 잔고를 내려받은 다음, 아래 네 열만 있는 CSV를 **저장소 밖**에 준비한다. 아래 금액과 시각은 사용 예시다. 한 파일에 **한 계좌의 기준시각 현재 전체 잔고**를 담는다. 앱별 원본 파일 서식은 자동 변환하지 않는다.

```csv
symbol,quantity,currency,market_value
005930,10,KRW,700000
KRW,300000,KRW,300000
AAPL,2,USD,400
```

- `symbol`은 종목코드다. 스프레드시트에서는 텍스트 형식을 사용해 앞자리 0을 보존한다. 현금은 통화코드를 쓴다.
- `quantity`는 보유 수량, `currency`는 평가통화, `market_value`는 **그 수량 전체의 평가액**이다. 평가액을 모르면 빈 칸으로 둔다. 숫자에 천 단위 쉼표를 넣지 않는다.
- 예수금을 비중에 포함하려면 별도 현금 행을 넣는다. 전량 처분한 계좌는 수량·평가액이 0인 행을 한 줄 넣는다. 현금·롱 잔고를 지원한다.
- `--as-of`에는 원본 잔고의 실제 기준시각과 시간대를 적는다. 같은 계좌·시각·내용은 한 번만 반영한다. 같은 시각의 다른 내용은 거부하고, 과거 자료는 이력으로만 추가한다.

```sh
python3 -m private_accounts import-csv kis ~/Downloads/kis.csv --account isa --as-of 2026-11-20T16:00:00+09:00
```

## 개인 화면과 에이전트용 데이터

```sh
python3 -m private_accounts dashboard
python3 -m private_accounts agent-view kis --account isa
```

개인 화면은 터미널에 출력된 임시 주소를 같은 Mac 브라우저에서 열어 사용한다. `127.0.0.1:8765`로만 수신하고 추측하기 어려운 경로를 실행할 때마다 새로 만든다. 이 주소는 잔고를 읽을 수 있으므로 공유하지 않는다. `Ctrl+C`로 종료한다. 공개 Streamlit 앱과 별도 프로세스이고, 공개 웹훅·터널·자동매매 봇에 연결하지 않는다.

`agent-view`는 선택한 계좌의 기준시각·종목·평가통화·비중(%)만 JSON으로 출력한다. 비중은 **한 계좌 안에서 같은 평가통화끼리** 계산한다. 같은 통화의 자산 중 평가액이 하나라도 빠져 있거나 합계가 0이면 해당 통화의 비중은 모두 `null`이다. 외부 전송과 에이전트로의 자동 전달은 없다.

## 저장·해제

- API 키는 수집기 실행 파일이 macOS 키체인 API로 읽고 쓴다. 키체인 항목은 iCloud 동기화 대상에서 제외한다. 재빌드 뒤에는 macOS가 다시 접근 승인을 요청할 수 있다. 접근을 승인하기 전에 표시된 프로그램을 확인한다.
- 라벨, 잔고, 평가액, 기준시각은 `~/Library/Application Support/whale_tracking/accounts/balances.sqlite3`에 보관한다. 비어 있는 상태에서 `status`나 대시보드를 실행해도 DB를 만들지 않는다. DB 파일은 소유자만 읽고 쓸 수 있는 일반 SQLite이며 별도 DB 암호화는 없다. 같은 macOS 사용자 권한으로 파일을 읽는 다른 프로그램에는 이 권한이 경계가 되지 않는다.
- 특정 거래소의 로컬 키를 지우려면 `python3 -m private_accounts disconnect binance --account main`을 쓴다. 저장한 잔고 이력은 보존한다. 유출 우려가 있거나 연결을 완전히 종료할 때는 거래소 관리 화면에서 발급 키도 폐기한다.
