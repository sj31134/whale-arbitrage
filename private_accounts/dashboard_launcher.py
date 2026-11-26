"""Open the same private Mac dashboard, starting it on demand."""
import fcntl
import hashlib
import hmac
import http.client
import os
import plistlib
import re
import secrets
import signal
import subprocess
import sys
import tempfile
import time
import webbrowser
from pathlib import Path

from agents import intelligence

PORT = 18765
DISPLAY_PORT = PORT + 2
IDENTITY = "dashboard_identity.json"
PROBE = "/_dashboard/ready/"


def identity(package):
    def validate(doc):
        if not isinstance(doc, dict) or not re.fullmatch("[0-9a-f]{64}", str(doc.get("key", ""))):
            raise ValueError("로컬 대시보드 식별 파일을 확인하세요.")
        return bytes.fromhex(doc["key"])

    doc = intelligence.private_json(package, IDENTITY, None)
    if doc is None:
        intelligence.update_json(package, IDENTITY, None,
                                 lambda old: {"key": secrets.token_hex(32)} if old is None else old)
        doc = intelligence.private_json(package, IDENTITY, None)
    return validate(doc)


def proof(key, purpose):
    return hmac.new(key, purpose.encode("ascii"), hashlib.sha256).hexdigest()


def preferred_port(package):
    selected = intelligence.private_json(package, "dashboard_endpoint.json", {}).get("port", PORT)
    if selected not in (PORT, PORT + 1, DISPLAY_PORT):
        raise ValueError("저장된 대시보드 포트를 확인하세요.")
    return selected


def entry(key, port=None):
    return f"http://127.0.0.1:{PORT if port is None else port}/{proof(key, 'manager-route')}/desk/manager"


def build_id(package):
    # Use source bytes so Finder can upgrade a running instance after a checkout or an edit.
    files = [*package.glob("*.py"), package / "monitor.css", package / "live.js", package / "launcher.js",
             *(package.parent / "agents").glob("*.py"), package.parent / "agents/equities/daily_bars.py"]
    digest = hashlib.sha256()
    for path in sorted(p for p in files if p.is_file()):
        digest.update(path.name.encode() + b"\x00" + path.read_bytes())
    return digest.hexdigest()


def running(key, *, build=None, port=None, request_stop=False):
    nonce = secrets.token_hex(16)
    conn = http.client.HTTPConnection("127.0.0.1", PORT if port is None else port, timeout=0.8)
    try:
        headers = {"X-Dashboard-Update": proof(key, "update:" + nonce)} if request_stop else {}
        conn.request("HEAD", PROBE + nonce, headers=headers)
        response = conn.getresponse()
        signature = response.getheader("X-Dashboard-Proof", "").encode("utf-8")
        if response.status == 204 and hmac.compare_digest(signature, proof(key, "ready:" + nonce).encode()):
            if request_stop:
                return response.getheader("X-Dashboard-Update") == "accepted"
            return build is None or response.getheader("X-Dashboard-Build") == build
        raise ValueError("고정 포트를 다른 서비스가 사용 중입니다. 개인 대시보드를 열지 않았습니다.")
    except ConnectionRefusedError:
        return False
    except (OSError, http.client.HTTPException) as exc:
        raise ValueError("고정 포트의 대시보드 응답을 확인할 수 없습니다.") from exc
    finally:
        conn.close()


def stop_previous(package, key, port):
    def listener():
        proc = subprocess.run(["/usr/sbin/lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                              capture_output=True, timeout=5)
        pids = set(proc.stdout.decode("ascii").split())
        if len(pids) != 1 or not next(iter(pids)).isdigit():
            raise ValueError("기존 대시보드 프로세스를 확인하지 못했습니다.")
        return int(pids.pop())

    if running(key, port=port, request_stop=True):
        wait_for_stop(key, port)
        return
    pid = listener()
    cwd = subprocess.run(["/usr/sbin/lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
                         capture_output=True, timeout=5)
    if (pid == os.getpid() or os.fsencode("n" + str(package.parent.resolve())) not in cwd.stdout.splitlines()
            or not running(key, port=port) or listener() != pid):
        raise ValueError("기존 대시보드의 프로젝트 경로를 확인하지 못했습니다.")
    os.kill(pid, signal.SIGTERM)
    wait_for_stop(key, port)


def wait_for_stop(key, port):
    deadline = time.monotonic() + 5
    while True:
        try:
            if not running(key, port=port):
                return
        except ValueError as exc:
            if not isinstance(exc.__cause__, (ConnectionResetError, http.client.RemoteDisconnected)):
                raise
        if time.monotonic() >= deadline:
            raise ValueError("기존 대시보드 종료를 확인하지 못했습니다.")
        time.sleep(0.1)


def collector_peer(package):
    choice = intelligence.private_json(package, "dashboard_endpoint.json", {})
    peer = choice.get("collector_port")
    if choice.get("port") == DISPLAY_PORT and peer in (PORT, PORT+1):
        return peer
    return None


def recent_stock_feed(package):
    from datetime import datetime, timedelta, timezone
    from . import live_valuation
    with live_valuation.connection(package) as db:
        if db is None:
            return False
        last = db.execute("SELECT max(success) FROM source WHERE feed IN ('NASDAQ','KOSPI','NYSE','KOSDAQ')").fetchone()[0]
    return bool(last and datetime.now(timezone.utc)-datetime.fromisoformat(last) < timedelta(minutes=4))


def public_connection():
    from agents import analyst_feeds, market_prices
    try:
        raw = analyst_feeds.fetch({"kind":"quotes","url":market_prices.endpoint("fx")})
        return bool(market_prices.parse("fx",raw)[0])
    except (OSError, ValueError, KeyError, TypeError):
        return False


def can_restore_market_connection(package):
    # A Finder launch may have public network access that an earlier managed session lacked.
    from agents import analyst_feeds, market_prices
    from . import live_valuation
    with live_valuation.connection(package) as db:
        if db is None:
            return False
        statuses = {r["feed"]: r["status"] for r in db.execute("SELECT feed,status FROM source")}
    if collector_peer(package):
        with live_valuation.connection(package) as db:
            if db is not None and db.execute("SELECT 1 FROM sqlite_master WHERE name='bar_job'").fetchone():
                failed = db.execute("SELECT 1 FROM bar_job WHERE status IN ('DNS 실패','연결·원문 확인 실패','원천 연결 실패') LIMIT 1").fetchone()
                ok = db.execute("SELECT 1 FROM bar_job WHERE success IS NOT NULL LIMIT 1").fetchone()
                if failed and not ok and public_connection():
                    return True
    if not all(statuses.get(feed) == "DNS 실패" for feed in ("upbit", "binance", "KOSPI", "fx")):
        return False
    try:
        raw = analyst_feeds.fetch({"kind": "quotes", "url": market_prices.endpoint("fx")})
        quotes, _ = market_prices.parse("fx", raw)
        return bool(quotes)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def ensure_running(package, refresh_minutes=30, *, reconnect=False):
    key = identity(package)
    expected = build_id(package)
    lock = os.open(package / ".local/dashboard_start.lock", os.O_CREAT | os.O_NOFOLLOW | os.O_RDWR, 0o600)
    previous = None
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        port = preferred_port(package)
        if running(key, build=expected, port=port):
            if not reconnect or not can_restore_market_connection(package):
                return key
        # Keep a working native collector alive when the renderer is launched from a network-limited session.
        if port != DISPLAY_PORT and running(key, port=port) and recent_stock_feed(package) and not public_connection():
            previous = intelligence.private_json(package,"dashboard_endpoint.json",{})
            peer,port = port,DISPLAY_PORT
            ready = running(key,build=expected,port=port)
            intelligence.update_json(package,"dashboard_endpoint.json",{},lambda _: {"port":port,"collector_port":peer})
            if ready:
                return key
        if running(key, port=port):
            try:
                stop_previous(package, key, port)
            except PermissionError:
                # A managed session can authenticate an older listener but lack signal permission.
                if port != PORT:
                    raise
                port = PORT + 1
                ready = running(key, build=expected, port=port)
                if not ready and running(key, port=port):
                    raise ValueError("대체 고정 포트에 이전 대시보드가 실행 중입니다.")
                previous = intelligence.private_json(package,"dashboard_endpoint.json",{})
                intelligence.update_json(package, "dashboard_endpoint.json", {}, lambda _: {"port": port})
                if ready:
                    return key
        process = subprocess.Popen([sys.executable, "-m", "private_accounts", "dashboard",
                                    "--refresh-minutes", str(refresh_minutes)],
                                   cwd=package.parent, start_new_session=True,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 12
        while not running(key, port=port):
            if process.poll() is not None:
                # Another simultaneous launch may have won the bind race.
                if running(key, port=port):
                    break
                raise ValueError("대시보드 시작에 실패했습니다. 고정 포트와 로컬 폴더 권한을 확인하세요.")
            if time.monotonic() >= deadline:
                raise ValueError("대시보드 시작을 확인하지 못했습니다. 실행 파일을 다시 여세요.")
            time.sleep(0.12)
        if not running(key, build=expected, port=port):
            raise ValueError("새 대시보드 버전을 확인하지 못했습니다.")
        return key
    except Exception:
        if previous is not None:
            intelligence.update_json(package, "dashboard_endpoint.json", {}, lambda _: previous)
        raise
    finally:
        os.close(lock)


def open_manager(package, refresh_minutes=30):
    key = ensure_running(package, refresh_minutes, reconnect=True)
    open_running_manager(package, key, preferred_port(package))


def open_running_manager(package, key, port):
    """Open the local window without restarting its HTTP listener or collectors."""
    url = entry(key, port)
    if sys.platform == "darwin":
        # LaunchServices only receives a local filename. Its errors must not print the private route.
        folder = package / ".local"
        shortcut = folder / "투자 대시보드.webloc"
        with tempfile.NamedTemporaryFile(dir=folder, delete=False) as f:
            temp = Path(f.name)
        try:
            temp.write_bytes(plistlib.dumps({"URL": url}))
            os.replace(temp, shortcut)
        finally:
            temp.unlink(missing_ok=True)
        opened = subprocess.run(["/usr/bin/open", str(shortcut)], capture_output=True).returncode == 0
    else:
        opened = webbrowser.open(url)
    if not opened:
        raise ValueError("대시보드는 실행 중이지만 기본 브라우저에서 열지 못했습니다.")
