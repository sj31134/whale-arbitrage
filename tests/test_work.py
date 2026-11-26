"""Cross-session intake, handoff and evidence from real engines using synthetic local data."""

import json
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from math import sin

import pytest

from private_accounts import (
    live_panel,
    live_valuation,
    market_review,
    price_history,
    quant,
    quant_page,
    reports,
    store,
    work,
)
from private_accounts.__main__ import args_for

CUTOFF = "2025-01-03T22:00:00+00:00"
DAY = "2025-01-03"


@pytest.fixture
def project(tmp_path):
    root = tmp_path.resolve()
    for name in set(
        work.COMMON
        + work.template("audit")[3]
        + work.template("sma")[3]
        + ("agents/FILE_MAP.csv",)
    ):
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(store.ROOT / name, dest)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def run(root, *args):
    return work.execute(args_for(["work", *args]), root)


def add(root, goal, *extra):
    return run(root, "register", goal, "--as-of", CUTOFF, "--day", "US=" + DAY, *extra)


def publish(package, desk, labels, inputs=(), *, as_of=CUTOFF):
    doc = dict(
        title="합성 검토",
        as_of=as_of,
        status="검토 완료",
        conclusion="임시 표본 점검",
        downside="원천 지연",
        revisit="정정 공표 시",
        sources=[
            dict(label=k, as_of=CUTOFF, url="https://example.org/release")
            for k in labels
        ],
    )
    if inputs:
        doc["inputs"] = list(inputs)
    return reports.publish(package, desk, doc)


def test_three_requests_engine_receipts(project):
    package = project / "private_accounts"
    session = run(project, "session")
    for kind, desk in (
        ("audit", "equities"),
        ("sma", "equities"),
        ("brief", "manager"),
    ):
        more = ["--day", "KR=" + DAY] if kind == "brief" else []
        t = add(project, work.template(kind)[0], *more)
        key = t["id"]
        assert t["주담당"] == desk and t["상태"] == "queued"
        assert t == add(project, work.template(kind)[0], *more)
        run(project, "claim", key, "--session", session, "--tool", "Cowork")
        verify = ("verify", key, "--session", session)
        with pytest.raises(ValueError):
            run(project, *verify, "--report", key)
        assert run(project, "status", key)["상태"] == "running"
        labels = ["US " + DAY, *work.check_labels(kind)]
        extra = []
        refs = []
        if kind == "audit":
            vault = project / "vault"
            with store.database(vault, True) as db:
                store.save(
                    db, "kis", "fixture", CUTOFF, [("US-FIXTURE", "USD", "2", "20")]
                )
            with live_valuation.connection(package, write=True) as db:
                db.execute(
                    live_valuation.UPSERT,
                    dict(
                        venue="NASDAQ",
                        symbol="FIXTURE",
                        currency="USD",
                        name="Fixture",
                        english="Fixture",
                        price="15",
                        at=CUTOFF,
                        session="CLOSE",
                        delay="0",
                        feed="NASDAQ",
                        page=1,
                        seen=CUTOFF,
                    ),
                )
            price_history.snapshots(vault, package, datetime.fromisoformat(CUTOFF))
            with live_valuation.connection(package, account_history=True) as db:
                assert (
                    db.execute("SELECT valuation FROM mark_day").fetchone()[0] == "30"
                )
            assert "FIXTURE" in live_panel.panel(vault, package)
        elif kind == "sma":
            rows = [
                dict(
                    day=(
                        date.fromisoformat(DAY) - timedelta(days=quant.MIN_ROWS - 1 - i)
                    ).isoformat(),
                    opening=str(100 + sin(i)),
                    closing=str(100 + sin(i)),
                    revisions=0,
                )
                for i in range(quant.MIN_ROWS)
            ]
            _, _, digest = quant_page.experiment(
                package, ("NASDAQ", "FIXTURE", "USD"), "fixture", rows, []
            )
            extra = ["--experiment", digest]
        else:
            market_review.run_scan(
                package, {"US": DAY, "KR": DAY}, collector=lambda _: {}
            )
            market_review.crosscheck(project / "vault", package)
            labels.append("KR " + DAY)
            refs = [publish(package, "equities", labels)]
            with pytest.raises(ValueError):
                publish(package, "manager", labels, [key])
        report = publish(package, desk, labels, refs)
        assert run(project, *verify, "--report", report, *extra)["상태"] == "done"
        assert run(project, "status", key)["게시ID"] == report
        assert run(project, *verify, "--report", report, *extra) == "이미 완료 검증됨"


def test_review_of_previously_published_desks(project):
    package = project / "private_accounts"
    name = work.template("review")[0]
    with pytest.raises(ValueError, match="참여 분야"):
        add(project, name)
    labels = ["US " + DAY]
    refs = [publish(package, d, labels) for d in ("equities", "crypto")]
    session = run(project, "session")
    for cutoff, already_published in [(CUTOFF, False), (work.now(), True)]:
        ticket = run(project, "register", name, "--as-of", cutoff, "--day", "US=" + DAY,
                     "--with-desk", "equities", "--with-desk", "crypto")
        key = ticket["id"]
        run(project, "claim", key, "--tool", "Codex", "--session", session)
        verify = ("verify", key, "--session", session, "--report")
        with pytest.raises(ValueError, match="참여 분야"):
            run(project, *verify, publish(package, "manager", labels, refs[:1], as_of=cutoff))
        report = publish(package, "manager", labels, refs, as_of=cutoff)
        if already_published:
            assert run(project, *verify, report)["상태"] == "done"
        else:
            with pytest.raises(ValueError, match="기준시각까지 게시"):
                run(project, *verify, report)


def test_race_handoff_and_write_lock(project):
    shared = ["--development", "--write", "private_accounts/view.py"]
    a = add(project, "계좌 최신성 감사", *shared)["id"]
    b = add(project, "종목별 이동평균 백테스트", *shared)["id"]
    sessions = [run(project, "session") for _ in range(2)]
    gate = threading.Barrier(2)

    def claim(s):
        gate.wait()
        try:
            run(project, "claim", a, "--session", s, "--tool", "Codex")
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(2) as pool:
        outcomes = list(pool.map(claim, sessions))
    assert sorted(outcomes) == [False, True]
    s = sessions[outcomes.index(True)]
    assert (
        run(project, "claim", a, "--session", s, "--tool", "Codex") == "동일 세션 재개"
    )
    assert a in run(project, "ticket", b)["충돌작업"]
    with pytest.raises(ValueError):
        run(project, "claim", b, "--session", sessions[0], "--tool", "Claude")
    run(
        project, "handoff", a, "--session", s, "--to", "Claude", "--reason", "세션 중단"
    )
    with pytest.raises(ValueError):
        run(project, "claim", a, "--session", s, "--tool", "Codex")
    run(project, "claim", a, "--session", sessions[1], "--tool", "Claude")
    run(project, "fail", a, "--session", sessions[1], "--reason", "시험 실패")
    with pytest.raises(ValueError):
        run(project, "verify", a, "--session", sessions[1])
    assert run(project, "status", a)["상태"] == "failed"
    assert (
        run(project, "claim", b, "--session", s, "--tool", "Cowork")["상태"]
        == "running"
    )
    suite = project / "tests/test_quant.py"
    suite.write_text("def test_fixture():\n    assert False\n")
    with pytest.raises(ValueError, match="회귀시험 실패"):
        run(project, "verify", b, "--session", s)
    assert run(project, "status", b)["상태"] == "failed"
    dep = add(project, "계좌 최신성 감사", "--after", b)["id"]
    with pytest.raises(ValueError, match="선행"):
        run(project, "claim", dep, "--session", s, "--tool", "Codex")
    suite.write_text("def test_fixture():\n    assert 2 + 2 == 4\n")
    run(project, "claim", b, "--session", s, "--tool", "Cowork")
    assert run(project, "verify", b, "--session", s)["상태"] == "done"
    assert run(project, "status", b)["게시ID"] is None
    assert (
        run(project, "claim", dep, "--session", s, "--tool", "Claude")["상태"]
        == "running"
    )


def test_incomplete_worktree_and_private_text(project):
    private = "LOCAL_ONLY_FIXTURE"
    t = add(project, f"{private} 계좌 최신성 감사")
    assert private not in json.dumps(t, ensure_ascii=False)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.org",
            "commit",
            "--allow-empty",
            "-qm",
            "baseline",
        ],
        cwd=project,
        check=True,
    )
    second = project.parent / (project.name + "-wt")
    subprocess.run(
        ["git", "worktree", "add", "--detach", "-q", str(second)],
        cwd=project,
        check=True,
    )
    assert run(second, "status", t["id"])["상태"] == "queued"
    with pytest.raises(ValueError, match="기준 구현"):
        run(project, "--checkout", str(second), "ticket", t["id"])
    with pytest.raises(ValueError):
        add(project, "계좌 최신성 감사", "--after", "work-unknown")


def test_antigravity_claims_and_receives_handoff(project):
    key = add(project, "계좌 최신성 감사")["id"]
    first, second = (run(project, "session") for _ in range(2))
    assert "Codex|Claude|Cowork|Antigravity" in run(project, "ticket", key)["선점명령"]
    run(project, "claim", key, "--session", first, "--tool", "Codex")
    assert (
        run(project, "handoff", key, "--session", first, "--to", "Antigravity")["인계대상"]
        == "Antigravity"
    )
    with pytest.raises(ValueError):
        run(project, "claim", key, "--session", second, "--tool", "Claude")
    claimed = run(project, "claim", key, "--session", second, "--tool", "Antigravity")
    assert claimed["로컬수락도구"] == "Antigravity"
    with pytest.raises(SystemExit):
        run(project, "claim", key, "--session", second, "--tool", "Unknown")
