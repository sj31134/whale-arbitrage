"""Dashboard usability comments deliberately shared with the local portfolio manager."""

import csv
import re
from datetime import datetime

from agents import intelligence as intel, research_chat as research

FILE = "dashboard_feedback.json"
TOPICS = ("화면·탐색", "자료·출처", "판단 기준", "답변·비교")


def walkthrough(room):
    path = intel.ROOT / "agents/manager/DASHBOARD_REVIEW.csv"
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            return [r for r in csv.DictReader(stream)
                    if r.get("desk") in research.NAMES and r.get("feedback") and r.get("change")
                    and (room == research.MANAGER or r["desk"] == room)]
    except (OSError, UnicodeError, csv.Error):
        return []


def entries(package, room):
    if room not in research.NAMES:
        raise ValueError("담당을 확인하세요.")
    rows = intel.private_json(package, FILE, [])
    return [row for row in reversed(rows) if room == research.MANAGER or row["room"] == room]


def submit(package, room, fields):
    topic = fields.get("topic", "")
    comment = fields.get("comment", "").strip()
    key = fields.get("request_id", "")
    if (room not in research.NAMES or topic not in TOPICS or not re.fullmatch(r"[0-9a-f]{32}", key)
            or not 1 <= len(comment) <= 400 or any(ord(c) < 32 and c not in "\n\t\r" for c in comment)):
        raise ValueError("분류를 선택하고 개선 의견을 1~400자로 입력하세요.")
    row = dict(id=key, room=room, topic=topic, comment=comment, done=False,
               at=datetime.now(intel.KST).isoformat(timespec="minutes"))

    def append(rows):
        if any(r["id"] == key for r in rows):
            return rows
        return [*rows, row]

    intel.update_json(package, FILE, [], append)


def set_done(package, key, state):
    if state not in ("1", "0") or not re.fullmatch(r"[0-9a-f]{32}", key):
        raise ValueError("의견과 처리 상태를 확인하세요.")

    def update(rows):
        if not any(r["id"] == key for r in rows):
            raise ValueError("해당 의견을 찾을 수 없습니다.")
        return [dict(r, done=state == "1") if r["id"] == key else r for r in rows]

    intel.update_json(package, FILE, [], update)
