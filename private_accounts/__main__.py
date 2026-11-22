import argparse
import csv
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import exchanges, local_sources, store, view


def alias(text):
    if not re.fullmatch("[a-zA-Z0-9_-]{1,32}", text):
        raise argparse.ArgumentTypeError("별칭은 영문, 숫자, _, - 1~32자로 입력하세요.")
    return text


def args_for(argv):
    parser = argparse.ArgumentParser(description="개인 계좌 조회·관리 (로컬 전용)")
    commands = parser.add_subparsers(dest="cmd", required=True)
    commands.add_parser("build", help="macOS 키체인 수집기 빌드")
    commands.add_parser("setup-local", help="엑셀과 키 설정을 오프라인에서 연결")
    commands.add_parser("status", help="기관별 엑셀 계좌 및 API 등록 기록")
    commands.add_parser("dashboard", help="로컬 잔고 화면 열기")
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
    if args.cmd == "setup-local":
        local_sources.prepare(source_root or store.ROOT)
        print("엑셀 검증 및 로컬 키 설정 완료. 외부 인증은 실행하지 않았습니다.")
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
    elif args.cmd == "dashboard":
        http, url = view.server(directory, package=package)
        with http:
            print(url, flush=True)
            try:
                http.serve_forever()
            except KeyboardInterrupt:
                pass


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
