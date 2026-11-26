# whale_tracking 운영 지침

공개 연구 수집기는 보유 목록을 인자로 받지 않는다. 종목별 직접 근거와 공통 시장 자료의 구분, 최신성, 실패 시 마지막 성공값 보존은 [정보 파이프라인](data/analysts/README.md)을 따른다.

이 프로젝트는 개인 Mac에서 계좌별 보유 현황을 읽고, 다섯 분야의 투자 가설을 검토해 사용자의 판단을 돕는다. 계좌 화면에는 실제 관측값을, 분석 메모에는 출처와 기준시각, 가정, 손실 시나리오와 가설을 철회할 조건을 남긴다. 직접 트레이딩은 사용자 지시로 보류한다. 에이전트는 보유 자산과 신규 후보를 분석해 의견을 제출한다. 봇 시작, 실주문 또는 기존 주문 취소, 거래 권한 추가, 자동 재개는 수행하지 않는다.

다섯 분야의 보유·후보 목표, 가설을 재검토할 조건과 공통 정보 10개 범주는 [투자 운영 기준](agents/INVESTMENT_MANDATE.md)을 따른다. 기준시각·근거 원문·영향 경로·반증 조건을 한 건씩 남긴다. 포트폴리오와의 대조는 로컬에서 수행한다.

투자 작업 지시는 Codex·Claude·Cowork의 [공통 작업 접수](agents/manager/WORK.md)로 받는다. 요청 범위에 맞는 `agents/<담당>/README.md`, [투자 운영 기준](agents/INVESTMENT_MANDATE.md), 해당 연구 지침을 읽고 관측 원문과 기준시각을 확인한다. 공개 자료 확보와 개인 계좌 대조는 분리하고 개인 데이터는 로컬 코드 안에서 처리한다. 개인 보유 행이나 금액을 Codex 입력·명령 출력에 싣지 않는다.

결과는 `python3 -m private_accounts publish-report <담당>`의 표준 입력으로 게시한다. [투자 매니저](agents/manager/README.md)는 요청에 참여한 분야의 게시 결과 ID를 인용해 합의·충돌·판단 보류 사유를 종합한다. 대시보드는 저장한 보고서, 근거, 계좌와 수집 현황을 표시한다. 새 분석은 로컬에서 작업을 선점한 세션이 실행한다. [보고서 입력 형식](private_accounts/README.md#분석-결과-게시)

## 작업 범위와 기준 자료

| 담당 | 답할 질문 | 실제 구현과 범위 |
| --- | --- | --- |
| 고래 | 어느 체인에서 어떤 흐름이 관측됐는가? | `agents/whale/`의 수집기·지갑 라벨·거래 방향 집계. 주소 식별 근거와 관측 시각을 기록한다. |
| 코인 | 거래소 시세·프리미엄·파생 지표가 후보 평가를 어떻게 바꾸는가? | `agents/crypto/`, 투자 CLI의 `--universe crypto`. 개인 잔고 조회와 업비트 자동매매는 별도 진입점이다. |
| 부동산·경매 | 실거래·토지지분·선순위 권리·필요 현금은 얼마인가? | `agents/real_estate/`. `--universe real_estate`는 일반 평가다. 경매 권리분석은 투자 실행기의 `run_real_estate_subagent_pipeline()`을 사용한다. |
| 주식 | 국가별 주식·ETF 후보의 가치, 하방과 안전마진은 얼마인가? | `agents/equities/`, `--universe`에 `us_equities`, `kr_equities`, `jp_equities`, `cn_equities` 중 하나를 지정한다. |
| 미국 소형·고베타 주식 | 미국 후보의 단기 수급과 가격 변곡점은 어디인가? | `agents/us_small_cap_high_beta/`, `--universe order_flow --market us`. 현재 코드는 미국 시장만 필터링한다. 시총·베타의 원자료, 측정 기간, 판정 기준이 확인된 경우에만 개별 후보를 소형·고베타로 분류한다. |

공용 투자 실행기는 `branch/investor_agent/main.py`다. 수급 후보를 장기 코어 자산으로 편입하거나 전략 비중을 바꿀 때는 사용자의 지시를 확인한다. 파일 담당과 기존 호출 경로는 [분류표](agents/FILE_MAP.csv)와 [폴더 구조](PROJECT_STRUCTURE.md)에서 확인한다.

## 분석과 계좌 데이터

1. 투자 원칙 또는 부동산·경매 분석 작업은 `.agents/skills/investor-principles/SKILL.md`와 `.agents/skills/real-estate-subagent/SKILL.md`를 먼저 읽는다. 투자 원칙을 수정할 때는 `branch/investor_agent/skills/investor-principles/SKILL.md`에도 같은 내용을 반영한다.
2. 분석 순서는 데이터 기준시각과 원문 확인, 자산·현금흐름 평가, 강세·기준·약세 시나리오, 통과 기준 검토, 배분·스트레스 검토, 근거와 무효화 조건 기록이다. 고정 예시, 캐시, 대체 시세는 출처와 시각을 표시한다. 특히 경매 수집기의 고정 사례와 자체 감사 결과만으로 최신 법원 공고나 권리관계를 확정할 수 없다.
3. 연구 지침의 기대수익률 12%, 손익비 3배, 안전마진 20%는 프로젝트가 정한 선별 기준이다. 현재 `Asset.is_investable`은 점수 7점, 상승/하락 수익률 비율 3배, 안전마진 15%를 검사한다. 별도 `ScenarioModeler`의 기대수익률 검사와 지침의 확률가중 손익비 산식도 구별한다. 연구 메모에서 지침 충족을 주장하려면 각 기준을 직접 대조한다. [자산 모델](branch/investor_agent/src/core/asset.py) · [시나리오 판정](branch/investor_agent/src/strategy/scenario_modeler.py)
4. 실계좌의 원천은 로컬 엑셀과 인증·조회에 성공한 계좌별 스냅샷이다. 연구용 `branch/investor_agent/data/timeline/active_portfolio_state.json`을 실계좌 잔고로 대체 사용하지 않는다. 엑셀은 파일 수정시각, 스냅샷은 잔고 기준시각을 표시한다. 합계 수식 행은 보유 종목 수나 평가액에 더하지 않는다.
5. 국내 네 증권사는 엑셀·CSV로 조회한다. 바이낸스 현물과 업비트는 키 준비, 인증, 잔고 수집을 각각 구분한다. CLI의 등록 기록만으로 키의 현재 유효성이나 잔고를 단정하지 않는다. 업비트는 발급 화면에서 자산조회 권한을 확인한다. [계좌별 범위와 명령](private_accounts/README.md)
6. 키, 계좌번호, 잔고 원본, 개인 대시보드의 토큰 주소는 로그·채팅·Git·배포 자료에 쓰지 않는다. `agent-view`의 종목과 비중도 개인 정보다. 로컬 분석에 필요한 필드만 사용한다. 통화별 비중의 분모는 같은 계좌의 같은 평가통화다. 미수집과 실제 0원은 구분한다.

## 변경 및 검증 하네스

- 호환 경로 `app/`, `trading_bot/`, `scripts/subprojects/arbitrage/`, `scripts/subprojects/risk_ai/`, `data/`, `.agents/skills/`, `requirements.txt`, `runtime.txt`의 이동·변경은 사전 승인을 받는다. `data/whale_transactions.csv`는 명시적 요청 없이 삭제·변환하지 않는다.
- 파일을 이동하거나 추가하면 `agents/FILE_MAP.csv`를 갱신하고 `python3 scripts/maintenance/check_agent_layout.py --write-tree`로 트리를 재생성한다. 일반 검증은 아래 첫 번째 명령을 사용한다.
- 투자 테스트에는 `TemporaryDirectory` 또는 `tmp_path`를 `data_dir`로 주입한다. 개인 계좌 테스트에는 임시 엑셀·DB와 가짜 키를 사용한다. 정상 동작 검증에 실거래 봇이나 계좌 동기화를 실행할 필요는 없다.
- 테스트는 저장소 루트에서 아래처럼 각각 실행한다. Swift 서명·권한 테스트는 가짜 요청으로 실행하며 키체인 접근이 필요 없다.

```sh
python3 scripts/maintenance/check_agent_layout.py
python3 -m pytest -q tests
python3 -m pytest -q branch/investor_agent/tests
python3 -m pytest -q trading_bot/tests
git diff --check
git diff --cached -B -M -C --find-copies-harder --check
```

- 커밋 전 실제 스테이징 목록에서 개인 입력·키·빌드 산출물 제외를 확인한다. 테스트에서 건너뛰거나 실패한 항목과 실인증 여부를 구분해 보고한다. 원격 푸시와 파괴적 Git 명령에는 사용자 확인이 필요하다.
