import argparse
import errno
import csv
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from agents import intelligence, public_variables
from agents.portfolio import DOMAINS, portfolio_review
from . import strategy_registry, work
from . import market_review, price_history

from . import daily_review, dashboard_launcher, exchanges, live_valuation, local_sources, reports, research_archive, research_book, store, view


def alias(text):
    if not re.fullmatch("[a-zA-Z0-9_-]{1,32}", text):
        raise argparse.ArgumentTypeError("별칭은 영문, 숫자, _, - 1~32자로 입력하세요.")
    return text


def args_for(argv):
    parser = argparse.ArgumentParser(description="개인 계좌 조회·관리 (로컬 전용)")
    commands = parser.add_subparsers(dest="cmd", required=True)
    work.arguments(commands)
    strategy_registry.arguments(commands)
    commands.add_parser("build", help="macOS 키체인 수집기 빌드")
    commands.add_parser("setup-local", help="엑셀과 키 설정을 오프라인에서 연결")
    commands.add_parser("status", help="기관별 엑셀 계좌 및 API 등록 기록")
    screen = commands.add_parser("market-scan", help="공개 종목·섹터 표본과 거래소별 호가를 점검")
    screen.add_argument("--kr-day", required=True)
    screen.add_argument("--us-day", required=True)
    commands.add_parser("market-crosscheck", help="공개 이상 움직임과 보유분의 로컬 대조 저장")
    commands.add_parser("price-history", help="공개 일봉 및 로컬 계좌 시점평가를 저장")
    daily = commands.add_parser("daily-review", help="오늘의 손실 기여·수급 검토를 Mac에 저장")
    daily.add_argument("--public-flows", action="store_true", help="표준 입력의 공개 수급 JSON을 함께 기록")
    daily.add_argument("--refresh", action="store_true", help="주식 담당과 공통 시장의 공개 원천을 먼저 갱신")
    research = commands.add_parser("portfolio-review", help="담당 분야의 로컬 보유 종목과 검토 역할 조회")
    research.add_argument("agent", choices=DOMAINS)
    research.add_argument("--signals", action="store_true", help="담당 종목의 직접 근거와 분야별 공통 관측 포함")
    report = commands.add_parser("publish-report", help="표준 입력의 완료된 분석 결과를 로컬 화면에 게시")
    report.add_argument("desk", choices=reports.ROOMS)
    commands.add_parser("research-init", help="가설 연구 DB 준비")
    commands.add_parser("research-register", help="표준입력의 연구 가정 JSON을 등록하고 ID만 표시")
    observation = commands.add_parser("research-observe", help="가설의 시작 또는 종료 관측 JSON을 표준입력으로 기록")
    observation.add_argument("stage", choices=("start", "finish"))
    observation.add_argument("idea_id")
    commands.add_parser("research-snapshot", help="가설 DB와 보고서의 검증된 로컬 스냅샷 생성")
    recovery = commands.add_parser("research-recover", help="별도 폴더에 연구 스냅샷 복구 후 연결 검증")
    recovery.add_argument("snapshot_id")
    note = commands.add_parser("market-note", help="명시적으로 입력한 공개 수급만 로컬 Markdown으로 저장")
    note.add_argument("day", help="일일 검토의 KST 날짜 YYYY-MM-DD")
    dash = commands.add_parser("dashboard", help="로컬 투자관리 화면 실행")
    dash.add_argument("--open", action="store_true", help="이 Mac의 기본 브라우저로 열기")
    dash.add_argument("--refresh-minutes", type=int, default=30, help="화면 실행 중 공개 자료 갱신 간격(분), 0은 수동")
    dash.add_argument("--port", type=int, help="별도 임시 세션의 포트 번호. 0은 빈 포트, 생략하면 고정 대시보드")
    refresh = commands.add_parser("research-refresh", help="분야별 공개·로컬 연구 원천 갱신")
    refresh.add_argument("--category", choices=[c["id"] for c in intelligence.catalog()])
    refresh.add_argument("--offline", action="store_true", help="저장소 안의 연구 원천만 갱신")
    capture = commands.add_parser("research-import", help="공식 화면에서 확인한 공개 관측 목록을 표준 입력으로 반영")
    capture.add_argument("source", choices=(*intelligence.feeds.CAPTURES, *public_variables.URLS, "market-cases", "market-structure", "stock-bars", "stock-opens"))
    capture.add_argument("--checked-at", required=True, type=store.timestamp)
    commands.add_parser("sync-all", help="등록된 모든 거래소·별칭 동기화")
    for name, providers in (("connect", store.CRYPTO), ("connect-env", store.CRYPTO), ("sync", store.CRYPTO), ("disconnect", store.CRYPTO),
                            ("import-csv", store.BROKERS), ("agent-view", tuple(store.PROVIDERS))):
        p = commands.add_parser(name)
        p.add_argument("provider", choices=providers)
        p.add_argument("--account", type=alias, default=None if name == "connect-env" else "main", help="계좌번호 대신 사용할 별칭")
        if name == "agent-view":
            p.add_argument("--source", choices=("latest", "workbook", "snapshot"), default="latest")
        if name == "import-csv":
            p.add_argument("file", type=Path)
            p.add_argument("--as-of", required=True, type=store.timestamp, help="잔고 원본 기준시각, 시간대 포함")
    return parser.parse_args(argv)


def sync(directory, provider, account):
    when = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    rows = exchanges.sync_rows(provider, account)
    with store.database(directory, True) as con:
        store.save(con, provider, account, when, rows)
    print(f"{store.PROVIDERS[provider]} {account} 잔고 저장 완료 · {when}")


def run(argv, directory, source_root=None):
    args = args_for(argv)
    package = source_root / "private_accounts" if source_root else None
    if args.cmd == "work":
        result = work.execute(args, source_root or store.ROOT, directory)
        print(result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "strategies":
        print(json.dumps(strategy_registry.command(package,args,sys.stdin),ensure_ascii=False,indent=2))
    elif args.cmd == "setup-local":
        local_sources.prepare(source_root or store.ROOT)
        print("엑셀 검증 및 로컬 키 설정 완료. 외부 인증은 실행하지 않았습니다.")
    elif args.cmd == "research-init":
        with research_book.database(package, True):
            pass
        print("가설 연구 DB 준비 완료")
    elif args.cmd in ("research-register", "research-observe"):
        raw = sys.stdin.read(20001)
        if len(raw) > 20000:
            raise ValueError("연구 입력 크기를 확인하세요.")
        doc = json.loads(raw)
        if not isinstance(doc, dict) or not all(isinstance(v, str) for v in doc.values()):
            raise ValueError("문자열 필드의 JSON 객체 한 건이 필요합니다.")
        if args.cmd == "research-register":
            fields = {"report", "asset", "currency", "benchmark", "observed", "entry", "benchmark_entry",
                      "bear", "base", "bull", "fees", "slip", "price_source", "benchmark_source",
                      "catalyst", "invalidate", "due"}
            if set(doc) != fields:
                raise ValueError("연구 가정 필드를 확인하세요.")
            key = hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest()[:32]
            research_book.record(package, dict(doc, idea=key))
            print(key)
        else:
            fields = {"exit", "benchmark_exit", "source", "benchmark_source", "observed"}
            if args.stage == "finish":
                fields.update(("verdict", "reason"))
            if set(doc) != fields:
                raise ValueError("모의 가격 관측 필드를 확인하세요.")
            research_book.mark(package, dict(doc, idea=args.idea_id), opening=args.stage == "start")
            print("모의 관측 저장 완료")
    elif args.cmd == "research-snapshot":
        print(research_archive.snapshot(package))
    elif args.cmd == "research-recover":
        research_archive.recover(package, args.snapshot_id)
        print("독립 복구 및 보고서 연결 확인 완료")
    elif args.cmd == "market-note":
        research_archive.market_note(package, args.day)
        print("공개 수급 노트 저장 완료")
    elif args.cmd == "publish-report":
        raw = sys.stdin.read(100001)
        if len(raw) > 100000:
            raise ValueError("보고서가 너무 큽니다.")
        print(reports.publish(package, args.desk, json.loads(raw)))
    elif args.cmd == "build":
        exchanges.build_reader()
        print("키체인 수집기 빌드 완료")
    elif args.cmd == "status":
        info = local_sources.metadata(package)
        listed = {(r["provider"], r["alias"]): r for r in info.get("accounts", [])}
        with store.database(directory) as con:
            history = {(p, a): (active, date) for p, a, active, _, date in store.profiles(con)}
        for provider, label in store.PROVIDERS.items():
            aliases = {a for (p, a) in listed if p == provider}
            aliases.update(a for (p, a), (active, date) in history.items() if p == provider and (active or date))
            for a in sorted(aliases or {"main"}):
                key = (provider, a)
                active, date = history.get(key, (False, None))
                states = []
                if key in listed:
                    states.append("엑셀 등록")
                    if listed[key]["credential_status"]:
                        states.append(listed[key]["credential_status"])
                if provider in store.CRYPTO:
                    if active:
                        states.append("API 등록 기록 있음")
                    elif provider in info.get("ready", []):
                        states.append("기관 키 쌍 준비 · 미인증")
                    else:
                        states.append("API 미등록")
                else:
                    states.append("파일 조회")
                if date or key not in listed:
                    states.append(date or "수집 전")
                print(f"{label} ({provider}/{a})  " + " · ".join(states))
    elif args.cmd in ("connect", "connect-env", "disconnect"):
        if args.cmd == "connect-env" and args.account is None:
            info = local_sources.metadata(package)
            matches = [a["alias"] for a in info.get("accounts", []) if a["provider"] == args.provider]
            if len(matches) > 1:
                raise ValueError("같은 거래소의 계좌가 여러 개입니다. 개인 화면의 별칭을 --account에 지정하세요.")
            args.account = matches[0] if matches else "main"
        # Serialize local key changes and their registration records across concurrent CLI invocations.
        with store.database(directory, True) as con:
            if args.cmd == "connect-env":
                if package is None:
                    raise ValueError("로컬 설정 폴더를 확인하세요.")
                pair = local_sources.exchange_keys(package / ".local/credentials.env", args.provider)
                exchanges.native(args.cmd, args.provider, args.account, credentials=pair)
            else:
                exchanges.native(args.cmd, args.provider, args.account)
            store.registered(con, args.provider, args.account, args.cmd != "disconnect")
        print("키 등록 완료" if args.cmd != "disconnect" else "Mac 키 삭제 완료. 거래소 발급 키 폐기는 거래소에서 처리하세요.")
    elif args.cmd == "import-csv":
        rows = store.read_csv(args.file)
        with store.database(directory, True) as con:
            store.save(con, args.provider, args.account, args.as_of, rows)
        print("잔고 CSV 반영 완료")
    elif args.cmd == "sync":
        sync(directory, args.provider, args.account)
    elif args.cmd == "sync-all":
        with store.database(directory) as con:
            accounts = [(p, a) for p, a, active, _, _ in store.profiles(con) if active and p in store.CRYPTO]
        if not accounts:
            print("등록된 거래소 키가 없습니다.")
        failed = []
        for p, a in accounts:
            try:
                sync(directory, p, a)
            except (ValueError, OSError, sqlite3.Error, subprocess.CalledProcessError):
                failed.append(f"{p}/{a}")
        if failed:
            raise ValueError("동기화 실패: " + ", ".join(failed))
    elif args.cmd == "portfolio-review":
        reader = intelligence.agent_brief if args.signals else portfolio_review
        result = reader(directory, package, args.agent)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "agent-view":
        with store.database(directory) as con:
            saved = None
            if args.source != "workbook" and any(
                    p == args.provider and a == args.account and sid is not None
                    for p, a, _, sid, _ in store.profiles(con)):
                saved = store.agent_view(con, args.provider, args.account)
            result = saved
            if args.source != "snapshot" and package and (package / "accounts_stocks.xlsx").exists():
                when, accounts = local_sources.workbook_accounts(package / "accounts_stocks.xlsx")
                selected = accounts.get((args.provider, args.account))
                if selected and (not saved or datetime.fromisoformat(when) > datetime.fromisoformat(saved["as_of"])):
                    result = local_sources.workbook_view(selected, when)
            if result is None:
                raise ValueError("해당 별칭·출처의 잔고가 없습니다. 개인 화면에서 엑셀 별칭을 확인하세요.")
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cmd == "market-scan":
        market_review.run_scan(package, {"KR":args.kr_day, "US":args.us_day})
        print(json.dumps(market_review.snapshot(package), ensure_ascii=False))
    elif args.cmd == "market-crosscheck":
        market_review.crosscheck(directory, package)
        print("로컬 이상 움직임 대조 저장 완료")
    elif args.cmd == "price-history":
        price_history.snapshots(directory,package)
        price_history.refresh(package)
        print("로컬 가격 이력 점검 완료")
    elif args.cmd == "daily-review":
        if package is None:
            raise ValueError("로컬 프로젝트 경로가 필요합니다.")
        flows = (daily_review.read_flows(sys.stdin, datetime.now(daily_review.KST).date())
                 if args.public_flows else None)
        if args.refresh:
            market_review.refresh_overnight(package)
            intelligence.collect(package)
            if not dashboard_launcher.recent_stock_feed(package):
                live_valuation.refresh(package)
            price_history.refresh(package)
        price_history.snapshots(directory, package)
        # The public strategy study has a separate ledger. The account review can
        # still be saved if that optional store is temporarily unavailable.
        try:
            strategy_registry.refresh(package)
        except (OSError, sqlite3.Error, ValueError):
            pass
        daily_review.save(directory, package, flows)
        print("로컬 일일 검토 저장 완료")
    elif args.cmd == "research-import":
        if package is None:
            raise ValueError("로컬 프로젝트 경로가 필요합니다.")
        raw = sys.stdin.read(2000001)
        if len(raw) > 2000000:
            raise ValueError("공개 목록이 너무 큽니다.")
        loader = public_variables.import_capture if args.source in public_variables.URLS else intelligence.import_capture
        if args.source == "market-cases":
            loader = market_review.import_cases
        if args.source == "market-structure":
            loader = market_review.import_structure
        if args.source == "stock-opens":
            count = price_history.record_opens(package,json.loads(raw),args.checked_at)
        elif args.source == "stock-bars":
            count = price_history.record_public(package,json.loads(raw),args.checked_at)
        else:
            count = loader(package, args.source, args.checked_at, json.loads(raw))
        print(f"공식 화면 확인 · {args.source} · {count}건 저장")
    elif args.cmd == "research-refresh":
        states = intelligence.collect(package, args.category, args.offline)
        for key, status in states.items():
            print(f"{key} · {status}")
        if args.category == "exposure":
            portfolio = intelligence.board(directory, package)
            print("exposure · " + portfolio["categories"]["exposure"]["runs"][0]["status"])
    elif args.cmd == "dashboard":
        if not 0 <= args.refresh_minutes <= 10080:
            raise ValueError("갱신 주기는 0~10080분으로 입력하세요.")
        if args.port is not None and not 0 <= args.port <= 65535:
            raise ValueError("포트 번호를 확인하세요.")
        stable = args.port is None
        if stable and args.open:
            dashboard_launcher.open_manager(package, args.refresh_minutes)
            print("고정 대시보드를 기본 브라우저로 열었습니다.")
            return
        key = dashboard_launcher.identity(package) if stable else None
        try:
            http, url = view.server(directory, port=dashboard_launcher.preferred_port(package) if stable else args.port,
                                    package=package, identity_key=key)
        except OSError as exc:
            if stable and exc.errno == errno.EADDRINUSE and dashboard_launcher.running(key, port=dashboard_launcher.preferred_port(package)):
                print("고정 대시보드가 이미 실행 중입니다.")
                return
            raise
        with http:
            import threading
            stopped = threading.Event()
            def refresh_while_open():
                while not stopped.is_set():
                    try:
                        intelligence.collect(package)
                    except (ValueError, OSError):
                        print("정보 캐시 저장 권한을 확인하세요.", file=sys.stderr)
                    try:
                        market_review.retry_pending(directory,package)
                    except (ValueError, OSError, sqlite3.Error):
                        print("공개 이상 움직임의 재점검이 보류됐습니다.", file=sys.stderr)
                    if stopped.wait(args.refresh_minutes * 60):
                        break
            def refresh_prices():
                from agents.market_prices import INTERVAL
                while not stopped.is_set():
                    try:
                        live_valuation.refresh(package)
                    except (OSError, ValueError, sqlite3.Error):
                        print("시세 캐시 갱신 실패", file=sys.stderr)
                    if stopped.wait(INTERVAL):
                        break
            def refresh_history():
                from time import monotonic
                last_mark = 0
                while not stopped.is_set():
                    try:
                        if monotonic() - last_mark >= 60 or not last_mark:
                            price_history.snapshots(directory, package)
                            last_mark = monotonic()
                        price_history.refresh(package)
                    except (ValueError, OSError, sqlite3.Error):
                        print("가격 이력 점검 보류", file=sys.stderr)
                    stopped.wait(30)
            threading.Thread(target=refresh_history, daemon=True).start()
            def refresh_variables():
                while not stopped.is_set():
                    try:
                        public_variables.refresh(package)
                    except (ValueError, OSError):
                        print("공개 변수 캐시 갱신 실패", file=sys.stderr)
                    if stopped.wait(300):
                        break
            def start_collectors():
                from agents.market_prices import STREAMS
                peer = dashboard_launcher.collector_peer(package) if stable else None
                while peer is not None and not stopped.is_set():
                    try:
                        if not dashboard_launcher.running(key,port=peer):
                            break
                        live_valuation.refresh_token_prices(package)
                    except (OSError,ValueError,sqlite3.Error):
                        pass
                    stopped.wait(30)
                if stopped.is_set():
                    return
                for feed in STREAMS:
                    threading.Thread(target=live_valuation.run_stream, args=(package, feed, stopped), daemon=True).start()
                threading.Thread(target=refresh_prices, daemon=True).start()
                threading.Thread(target=refresh_variables, daemon=True).start()
                if args.refresh_minutes:
                    threading.Thread(target=refresh_while_open, daemon=True).start()
            threading.Thread(target=start_collectors,daemon=True).start()
            entry = url + "/desk/manager"
            if args.open:
                import webbrowser
                webbrowser.open(entry)
            print("고정 대시보드 실행 중" if stable else "임시 대시보드 실행 중", flush=True)
            try:
                http.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                stopped.set()


def main():
    os.umask(0o077)
    try:
        run(sys.argv[1:], store.PRIVATE_DIR, store.ROOT)
    except subprocess.CalledProcessError:
        sys.exit(1)
    except UnicodeError:
        sys.exit("개인 입력 파일의 문자 인코딩을 확인하세요.")
    except (sqlite3.Error, ValueError, OSError, csv.Error) as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
