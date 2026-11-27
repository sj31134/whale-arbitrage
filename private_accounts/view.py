"""Token-protected local investment monitor and read-only account ledger."""
import hmac
import re
import secrets
import sqlite3
import threading
from datetime import datetime
from html import escape
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from urllib.parse import parse_qs, urlsplit

from agents import desk_variables, intelligence, research_chat
from . import account_performance, chat_page, contrarian, contrarian_page, dashboard_launcher, desk_feedback, discovery, discovery_page, local_sources, live_panel, monitor, quant_page, research_archive, research_book, research_page
from . import strategy_page, strategy_registry
from .store import CRYPTO, PROVIDERS, database, positions, profiles


def workbook_cards(package, info):
    from decimal import Decimal
    if package is None or not (package / "accounts_stocks.xlsx").exists():
        return [], set()
    when, accounts = local_sources.workbook_accounts(package / "accounts_stocks.xlsx")
    status = {(r["provider"], r["alias"]): r["credential_status"] for r in info.get("accounts", [])}
    cards = []
    for (p, alias), account in accounts.items():
        body = []
        for symbol, ccy, qty, val, gain, rate, cost, price in account["rows"]:
            percent = None if rate is None else format(Decimal(rate) * 100, "f") + "%"
            values = (symbol, qty, val, ccy, gain, percent, cost, price)
            body.append("<tr>" + "".join("<td>" + escape(x if x is not None else "—") + "</td>"
                                         for x in values) + "</tr>")
        columns = ("종목", "수량", "평가금액", "평가통화", "평가손익", "수익률", "매입단가", "엑셀 기록 단가")
        key_status = status.get((p, alias)) or "엑셀 연결"
        cards.append(f"<section><h2>{PROVIDERS[p]} · {escape(account['label'])}</h2>"
                     f"<p>엑셀 파일 수정시각 {escape(when)} · 별칭 {escape(alias)} · {escape(key_status)}</p>"
                     + "<table><thead><tr>" + "".join("<th>" + h + "</th>" for h in columns) +
                     "</tr></thead><tbody>" + "".join(body) + "</tbody></table></section>")
    return cards, {p for p, _ in accounts}


def render(directory, package=None, base=None):
    info = local_sources.metadata(package)
    cards, in_workbook = workbook_cards(package, info)
    with database(directory) as con:
        for provider, alias, registered, snapshot, when in profiles(con):
            if provider in in_workbook and not registered and snapshot is None:
                continue
            source = "CSV" if provider not in CRYPTO else ("API 키 등록 기록 있음" if registered else "API 키 등록 기록 없음")
            if provider in info.get("ready", []) and not registered:
                source += " · 로컬 키 준비"
            body = ""
            if snapshot is not None:
                rows = positions(con, snapshot)
                cells = "".join("<tr>" + "".join("<td>" + escape(v if v is not None else "시세 없음") +
                                "</td>" for v in (symbol, qty, value, currency)) + "</tr>"
                                for symbol, currency, qty, value in rows)
                body = ("<table><thead><tr><th>종목</th><th>수량</th><th>평가액</th><th>통화</th></tr></thead><tbody>"
                        + cells + "</tbody></table>") if rows else "<p>보유 자산 없음</p>"
            cards.append(f"<section><h2>{PROVIDERS[provider]} · {escape(alias)}</h2><p>{source} · "
                         f"{escape(when or '수집 전')}</p>{body}</section>")
    return ("""<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>내 계좌 잔고</title>
<style>body{font:16px/1.6 system-ui,sans-serif;max-width:62rem;margin:auto;padding:2rem 1rem;
color:#142a32;background:#f6f8f7}section{background:white;border:1px solid #cbd7d5;border-radius:8px;
padding:0 1rem 1rem;margin:1rem 0;overflow:auto}h2{font-size:1.15rem}p{color:#41575f}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}th,td{text-align:right;
padding:.35rem;border-bottom:1px solid #dde5e3}th:first-child,td:first-child{text-align:left}
.desk-tabs{display:flex;flex-wrap:wrap;gap:.45rem 1rem}.desk-tabs a{color:#005e4d}</style>
""" + ("<style>" + monitor.CSS + "</style>" + live_panel.script(base)
       + "<header><div><strong>Whale Tracking</strong><small>로컬 투자 관리 · 내 계좌 잔고</small></div></header>"
       + chat_page.navigation(base, "accounts") if base else "")
            + "<main><h1>내 계좌 잔고</h1>" + (live_panel.panel(directory, package) if base else "")
            + "<details><summary>수집 당시 계좌 원장</summary>" + "".join(cards) + "</details></main></html>").encode()


def server(directory, port=8765, package=None, *, identity_key=None):
    route = "/" + (dashboard_launcher.proof(identity_key, "manager-route")
                   if identity_key is not None else secrets.token_urlsafe(32))

    build = dashboard_launcher.build_id(package) if identity_key is not None else None
    csrf = secrets.token_urlsafe(32)
    launcher_nonce = secrets.token_urlsafe(32)
    native_unavailable = threading.Event()
    desks = {route + "/desk/" + key: key for key in research_chat.NAMES}
    posts = {path + "/variable": (desk, "variable") for path, desk in desks.items() if desk != "manager"}
    posts.update({path + "/feedback": (desk, "feedback") for path, desk in desks.items()})
    posts[route + "/desk/manager/feedback-state"] = ("manager", "feedback-state")
    for action in ("strategy-run","strategy-state","discover-run","discover-sns","contrarian-run","contrarian-plan"):
        posts[route + "/desk/manager/" + action] = ("manager",action)
    journal_actions = ("idea", "start", "assess", "snapshot", "recover", "market-note")
    for action in journal_actions:
        posts[route + "/desk/manager/" + action] = ("manager", action)
    posts[route + "/desk/manager/reconcile"] = ("manager", "reconcile")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def allowed(self, path, expected):
            return (self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"
                    and hmac.compare_digest(path.encode(), expected.encode()))

        def is_launcher(self):
            return identity_key is not None and package is not None and self.allowed(self.path, "/start")

        def launch_page(self, opened=False):
            message = ("Mac 기본 브라우저에 투자 매니저를 열었습니다." if opened else
                       "이 Mac의 기본 브라우저에서 포트폴리오, 전략 연구와 담당별 보고서를 확인하세요.")
            label = "다시 열기" if opened else "투자 대시보드 열기"
            paired = ('<p>이 브라우저에서 열려면 Mac의 <strong>투자 대시보드.webloc</strong>을 선택하세요.</p>'
                      '<label>Mac 바로가기 선택 <input type="file" id="mac-shortcut" accept=".webloc"></label>'
                      '<p id="shortcut-error" role="status"></p>'
                      '<small>파일 선택 창에서 ⌘⇧G를 누른 뒤 프로젝트의 '
                      '<code>private_accounts/.local/</code> 폴더로 이동하세요.</small>')
            if native_unavailable.is_set() and not opened:
                message = "Mac 기본 브라우저가 자동으로 열리지 않았습니다."
                paired = '<section>' + paired + '</section>'
            else:
                paired = '<details><summary>이 브라우저에서 바로 열기</summary>' + paired + '</details>'
            self.reply(200, (
                '<!doctype html><html lang="ko"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>투자 대시보드 열기</title><style>'
                'body{margin:0;min-height:100vh;display:grid;place-items:center;background:#eff2ef;'
                'color:#172d2b;font:17px/1.6 system-ui,sans-serif}main{margin:24px;max-width:32rem;'
                'padding:clamp(26px,6vw,52px);background:white;border-radius:18px}h1{line-height:1.2}'
                'button{font:inherit;font-weight:650;border:0;border-radius:8px;background:#174d43;'
                'color:white;padding:11px 20px;cursor:pointer}details,section{margin-top:20px}input{max-width:100%}</style>'
                '<script defer src="/start/launcher.js"></script><main><h1>투자 대시보드</h1>'
                f'<p>{message}</p><form method="post" action="/start">'
                f'<input type="hidden" name="open" value="{launcher_nonce}"><button>{label}</button>'
                f'</form>{paired}</main></html>').encode())

        def do_HEAD(self):
            prefix = dashboard_launcher.PROBE
            nonce = self.path[len(prefix):]
            if (identity_key is None or not re.fullmatch("[0-9a-f]{32}", nonce)
                    or not self.allowed(self.path, prefix + nonce)):
                self.send_error(404)
                return
            update = hmac.compare_digest(self.headers.get("X-Dashboard-Update", "").encode(),
                                         dashboard_launcher.proof(identity_key, "update:" + nonce).encode())
            self.send_response(204)
            if update:
                self.send_header("X-Dashboard-Update", "accepted")
            self.send_header("X-Dashboard-Build", build)
            self.send_header("X-Dashboard-Proof", dashboard_launcher.proof(identity_key, "ready:" + nonce))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if update:
                threading.Thread(target=self.server.shutdown, daemon=True).start()

        def do_GET(self):
            if identity_key is not None and self.allowed(self.path, "/start/launcher.js"):
                self.reply(200, Path(__file__).with_name("launcher.js").read_bytes(),
                           "application/javascript; charset=utf-8")
                return
            if self.is_launcher():
                self.launch_page()
                return
            parts = urlsplit(self.path)
            if self.allowed(parts.path, route + "/quant/equity-screen.csv"):
                from . import equity_screen
                data = equity_screen.public_csv(package)
                self.reply(200 if data is not None else 404, data or b"", "text/csv; charset=utf-8")
                return
            if self.allowed(parts.path, route + "/live.js"):
                self.reply(200, Path(__file__).with_name("live.js").read_bytes(), "application/javascript; charset=utf-8")
                return
            home = self.allowed(parts.path, route) or self.allowed(parts.path, route + "/")
            portfolio = self.allowed(parts.path, route + "/portfolio")
            details = self.allowed(parts.path, route + "/accounts")
            journal = self.allowed(parts.path, route + "/research")
            quant = self.allowed(parts.path, route + "/quant")
            strategies = self.allowed(parts.path, route + "/strategies")
            discover = self.allowed(parts.path, route + "/discover")
            contrarian_rt = self.allowed(parts.path, route + "/contrarian")
            room = desks.get(parts.path)
            if not (details or home or portfolio or journal or quant or strategies or discover or contrarian_rt or (room and self.allowed(parts.path, route + "/desk/" + room))):
                self.reply(404, ('<!doctype html><html lang="ko"><meta charset="utf-8"><title>대시보드 주소 확인</title>'
                                 '<h1>이 주소로는 대시보드를 열 수 없습니다</h1>'
                                 '<p>Mac의 프로젝트 폴더에서 <code>python3 -m private_accounts dashboard --open</code>을 '
                                 '실행하면 현재 세션의 투자 매니저가 열립니다.</p></html>').encode())
                return
            try:
                query = {k: v[0] for k,v in parse_qs(parts.query, max_num_fields=16).items()}
                if home and not {"position", "agent", "provider", "category"}.intersection(query):
                    room = research_chat.MANAGER
                if self.headers.get("X-Live-Sections") == "1" and (details or room == research_chat.MANAGER):
                    if room == research_chat.MANAGER:
                        panels = chat_page.manager_sections(directory, package, route, query.get("screen","all"),
                                                            research_update=self.headers.get("X-Research-Sections") == "1",
                                                            position=query.get("position"),frame=query.get("frame","day"))
                    else:
                        panels = live_panel.panel(directory, package)
                    data = panels.encode()
                elif room:
                    data = chat_page.render(directory, package, route, csrf, room, monitor.CSS,
                                            query.get("all") == "1", query.get("feedback") == "1",
                                            query.get("legacy") == "1", query.get("screen","all"),query.get("position"),query.get("frame","day"))
                elif strategies:
                    data = strategy_page.render(package,route,csrf,monitor.CSS)
                elif discover:
                    data = discovery_page.render(directory, package, route, csrf, query, monitor.CSS)
                elif contrarian_rt:
                    data = contrarian_page.render(directory, package, route, csrf, query, monitor.CSS)
                elif quant:
                    data = quant_page.render(directory, package, route, query, monitor.CSS)
                elif journal:
                    data = research_page.render(package, route, csrf, monitor.CSS, query.get("done"), query=query)
                elif details:
                    data = render(directory, package, route)
                else:
                    data = monitor.render(directory, package, route, csrf, query)
                status = 200
            except Exception as error:
                status = 503
                detail = (str(error) if isinstance(error, local_sources.WorkbookInputError)
                          else "로컬 자료와 읽기 권한을 확인한 뒤 새로고침하세요.")
                data = ("<!doctype html><html lang=\"ko\"><meta charset=\"utf-8\">"
                        "<title>자료 읽기 오류</title><h1>자료를 읽을 수 없습니다</h1>"
                        f"<p>{escape(detail)}</p></html>").encode()
            self.reply(status, data)

        def do_POST(self):
            room, action = posts.get(self.path, (None, None))
            expected = route + "/desk/" + room + "/" + action if room else route + "/manage"
            launcher = self.is_launcher()
            if not launcher and not self.allowed(self.path, expected):
                self.send_error(404)
                return
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if self.headers.get("Origin") != origin or self.headers.get_content_type() != "application/x-www-form-urlencoded":
                self.forbidden("대시보드를 연 Mac의 브라우저에서 최신 화면을 열고 다시 제출하세요.")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= (20000 if room else 12000) or self.headers.get("Transfer-Encoding"):
                    raise ValueError
                args = parse_qs(self.rfile.read(length).decode(), keep_blank_values=True,
                                max_num_fields=24 if action in ("idea", "contrarian-plan") else 16)
                if any(len(v) != 1 for v in args.values()):
                    raise ValueError
                fields = {k:v[0] for k,v in args.items()}
                if launcher:
                    if set(fields) != {"open"} or not hmac.compare_digest(fields["open"].encode(), launcher_nonce.encode()):
                        self.forbidden("시작 페이지를 다시 열어 주세요.")
                        return
                    try:
                        dashboard_launcher.open_running_manager(package, identity_key, self.server.server_port)
                    except (ValueError, OSError):
                        native_unavailable.set()
                        self.launch_page()
                        return
                    native_unavailable.clear()
                    self.launch_page(opened=True)
                    return
                if not hmac.compare_digest(fields.get("csrf","").encode(), csrf.encode()):
                    self.forbidden("이 양식의 세션이 만료되었습니다. 최신 대시보드 화면에서 다시 제출하세요.")
                    return
                if package is None:
                    raise ValueError
                if room:
                    try:
                        if action == "strategy-run":
                            strategy_registry.refresh(package)
                        elif action == "discover-run":
                            discovery.refresh(package)
                        elif action == "discover-sns":
                            discovery.record_sns_note(package, fields)
                            discovery.refresh(package)
                        elif action == "contrarian-run":
                            contrarian.refresh(package)
                        elif action == "contrarian-plan":
                            contrarian.save_playbook(package, fields)
                        elif action == "strategy-state":
                            with strategy_registry.database(package) as db:
                                strategy_registry.state(db,fields["strategy"],fields["state"])
                        elif action == "variable":
                            desk_variables.save(package, room, fields)
                        elif action == "feedback":
                            desk_feedback.submit(package, room, fields)
                        elif action == "feedback-state":
                            desk_feedback.set_done(package, fields.get("entry", ""), fields.get("done", ""))
                        elif action == "snapshot":
                            research_archive.snapshot(package)
                        elif action == "recover":
                            research_archive.recover(package, fields.get("snapshot_id", ""))
                        elif action == "market-note":
                            research_archive.market_note(package, fields.get("day", ""))
                        elif action == "reconcile":
                            account_performance.save(package, fields)
                        elif action in ("idea", "start", "assess"):
                            observed = datetime.fromisoformat(fields.get("observed", ""))
                            if observed.tzinfo is None:
                                observed = observed.replace(tzinfo=intelligence.KST)
                            fields["observed"] = observed.isoformat()
                            if action == "idea":
                                research_book.record(package, fields)
                            else:
                                research_book.mark(package, fields, opening=action == "start")
                    except ValueError as exc:
                        self.reply(400, (f'<html lang="ko"><meta charset="utf-8"><p>{escape(str(exc))}</p>'
                                         f'<a href="{route}/desk/{room}">담당 화면으로 돌아가기</a></html>').encode())
                        return
                else:
                    intelligence.manage(directory, package, fields)
            except (ValueError, OSError, KeyError, ArithmeticError):
                self.reply(400, "입력값·개인 폴더 권한을 확인한 뒤 이전 화면으로 돌아가세요.".encode())
                return
            except sqlite3.Error:
                self.reply(503, "로컬 DB가 사용 중이거나 저장소를 읽을 수 없습니다. 다시 시도하세요.".encode())
                return
            target = route if room else route + "/portfolio"
            if room:
                target += "/desk/" + room
                if action in ("strategy-run","strategy-state"):
                    target = route + "/strategies"
                if action == "discover-run":
                    target = route + "/discover?done=refreshed"
                if action == "discover-sns":
                    target = route + "/discover?done=sns#sns-radar"
                if action == "contrarian-run":
                    target = route + "/contrarian?done=refreshed"
                if action == "contrarian-plan":
                    target = route + "/contrarian?done=saved#my-playbooks"
                if action == "reconcile":
                    target = route + "/portfolio#performance"
                if action in journal_actions:
                    target = route + "/research"
                    if action in ("snapshot", "recover", "market-note"):
                        target += "?done=" + action + "#archives"
                if action in ("feedback", "feedback-state"):
                    target += "?feedback=1#feedback"
            elif fields.get("action") == "refresh":
                category = fields.get("category")
                target += "?category=" + category + "#sources" if category else "#analysts"
            elif fields["action"] in ("cash-date","remove-date"):
                target += "#calendar"
            else:
                target += "?position=" + fields["position"] + "#position"
            self.send_response(303)
            self.send_header("Location", target)
            self.send_header("Cache-Control","no-store")
            self.send_header("Referrer-Policy","same-origin")
            self.end_headers()

        def forbidden(self, message):
            data = (f'<!doctype html><html lang="ko"><meta charset="utf-8"><title>403 · 제출 확인</title>'
                    f'<h1>요청을 저장하지 못했습니다</h1><p>{message}</p>'
                    '<p>프로젝트에서 <code>python3 -m private_accounts dashboard --open</code>으로 열 수 있습니다.</p></html>')
            self.reply(403, data.encode())

        def reply(self, status, data, content_type="text/html; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "same-origin")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; connect-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

    http = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return http, f"http://127.0.0.1:{http.server_port}{route}"
