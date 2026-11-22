"""Read-only private account dashboard on a fixed loopback interface."""
import hmac
import secrets
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import local_sources
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
        columns = ("종목", "수량", "평가금액", "평가통화", "평가손익", "수익률", "매입단가", "현재가")
        key_status = status.get((p, alias)) or "엑셀 연결"
        cards.append(f"<section><h2>{PROVIDERS[p]} · {escape(account['label'])}</h2>"
                     f"<p>엑셀 파일 수정시각 {escape(when)} · 별칭 {escape(alias)} · {escape(key_status)}</p>"
                     + "<table><thead><tr>" + "".join("<th>" + h + "</th>" for h in columns) +
                     "</tr></thead><tbody>" + "".join(body) + "</tbody></table></section>")
    return cards, {p for p, _ in accounts}


def render(directory, package=None):
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
padding:.35rem;border-bottom:1px solid #dde5e3}th:first-child,td:first-child{text-align:left}</style>
<h1>내 계좌 잔고</h1>""" + "".join(cards) + "</html>").encode()


def server(directory, port=8765, package=None):
    route = "/" + secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if (self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}"
                    or not hmac.compare_digest(self.path.encode(), route.encode())):
                self.send_error(404)
                return
            try:
                data = render(directory, package)
                status = 200
            except Exception as error:
                status = 503
                # Never put raw exception text (which may contain financial data) into a response.
                detail = (str(error) if isinstance(error, local_sources.WorkbookInputError)
                          else "로컬 계좌 파일과 읽기 권한을 확인한 뒤 새로고침하세요.")
                data = ("<!doctype html><html lang=\"ko\"><meta charset=\"utf-8\">"
                        "<title>잔고 조회 오류</title><h1>잔고를 표시할 수 없습니다</h1>"
                        f"<p>{escape(detail)}</p></html>").encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

    http = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return http, f"http://127.0.0.1:{http.server_port}{route}"
