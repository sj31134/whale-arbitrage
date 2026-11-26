"""Publish completed desk research into the private dashboard's local ledger."""

import hashlib
import json
from datetime import datetime
from urllib.parse import urlsplit

from agents import intelligence as intel
from . import store


FILE = "desk_reports.json"
ROOMS = ("manager", *intel.DOMAINS)
STATES = ("검토 완료", "관찰", "판단 보류")


def _text(value, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("보고서에 필요한 문구와 길이를 확인하세요.")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise ValueError("보고서에 사용할 수 없는 문자가 있습니다.")
    return value.strip()


def read(package):
    return intel.private_json(package, FILE, {})


def publish(package, desk, doc):
    required = {"title", "as_of", "status", "conclusion", "downside", "revisit", "sources"}
    if (package is None or desk not in ROOMS or not isinstance(doc, dict)
            or not required <= doc.keys() or doc.keys() - required - {"inputs"}):
        raise ValueError("담당과 보고서 필드를 확인하세요.")
    row = {k: _text(doc[k], limit) for k, limit in (
        ("title", 160), ("conclusion", 5000), ("downside", 2000), ("revisit", 2000))}
    stamp = store.timestamp(_text(doc["as_of"], 64))
    sources = doc["sources"]
    if (doc["status"] not in STATES or not isinstance(sources, list) or len(sources) > 40
            or (not sources and doc["status"] != "판단 보류")):
        raise ValueError("판정과 근거 목록을 확인하세요. 근거가 없으면 판단 보류로 기록하세요.")
    row.update(desk=desk, status=doc["status"], as_of=stamp, sources=[])
    for src in sources:
        if not isinstance(src, dict) or set(src) not in ({"label", "as_of"}, {"label", "as_of", "url"}):
            raise ValueError("근거의 이름·기준시각·공개 원문을 확인하세요.")
        entry = dict(label=_text(src["label"], 240), as_of=store.timestamp(_text(src["as_of"], 64)))
        if entry["as_of"] > stamp:
            raise ValueError("보고서 기준시각 이후의 관측은 별도 보고서로 등록하세요.")
        if "url" in src:
            url = _text(src["url"], 1500)
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("공개 원문의 HTTPS 주소를 확인하세요.")
            entry["url"] = url
        row["sources"].append(entry)
    inputs = doc.get("inputs", [])
    if (not isinstance(inputs, list) or len(inputs) > len(intel.DOMAINS)
            or any(not isinstance(key, str) for key in inputs) or bool(inputs) != (desk == "manager")):
        raise ValueError("매니저 종합에는 참여한 담당별 보고서 ID를 지정하세요.")
    row["inputs"] = sorted(inputs)
    key = hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def insert(ledger):
        desks = set()
        for ref in inputs:
            member = ledger.get(ref)
            if (not member or member["desk"] not in intel.DOMAINS or member["desk"] in desks
                    or member["as_of"] > stamp):
                raise ValueError("참여 분야별로 기준시각 이내의 보고서 한 건을 지정하세요.")
            desks.add(member["desk"])
        if key not in ledger:
            ledger[key] = dict(row, id=key, published=datetime.now(intel.KST).isoformat(timespec="microseconds"))
        return ledger

    intel.update_json(package, FILE, {}, insert)
    return key
