"""Local account/currency period performance with explicitly reconciled external flows."""
import hashlib
import json
from datetime import datetime
from decimal import Decimal, localcontext
from html import escape as e

from agents import intelligence as intel
from . import daily_review, store

FILE = "performance_reconciliations.json"


def intervals(package):
    history = intel.private_json(package, daily_review.FILE, {})
    groups = {}
    for day in sorted(history):
        for p in history[day].get("valuations", []):
            key = (p["provider"], p["account"], p["currency"])
            groups.setdefault(key, {})[p["as_of"]] = p
    result = {}
    for key, group in groups.items():
        points = sorted(group.values(), key=lambda p: datetime.fromisoformat(p["as_of"]))
        for start, end in zip(points, points[1:]):
            if start["source"] != end["source"] or None in (start["value"], end["value"]):
                continue
            digest = hashlib.sha256(json.dumps([key, start, end], sort_keys=True).encode()).hexdigest()
            result[digest] = (start, end)
    return result


def calculate(first, last, start, end, flows):
    if end <= start:
        raise ValueError("평가기간의 시작·종료 시각을 확인하세요.")
    with localcontext() as ctx:
        ctx.prec = 80
        exposure = Decimal(first)
        movement = Decimal(0)
        seconds = Decimal(str((end - start).total_seconds()))
        for when, value in flows:
            if not start < when <= end:
                raise ValueError("현금흐름은 기초 평가 직후부터 기말 평가까지의 시각이어야 합니다.")
            weight = Decimal(str((end - when).total_seconds())) / seconds
            exposure += weight * value
            movement += value
        gain = Decimal(last) - Decimal(first) - movement
        return gain, gain * 100 / exposure if exposure > 0 else None


def save(package, fields):
    key = fields.get("interval", "")
    pair = intervals(package).get(key)
    if pair is None or fields.get("confirmed") != "yes":
        raise ValueError("비교할 기간과 자산·현금·입출금 대조 확인이 필요합니다.")
    first, last = pair
    def observed(field, point):
        raw = fields.get(field, "")
        try:
            dt = datetime.fromisoformat(raw)
            stamp = store.timestamp((dt if dt.tzinfo else dt.replace(tzinfo=intel.KST)).isoformat())
        except ValueError:
            raise ValueError("실제 평가시각을 확인하세요.") from None
        actual = datetime.fromisoformat(stamp)
        source_at = datetime.fromisoformat(point["as_of"])
        if point["source"] == "snapshot" and actual != source_at:
            raise ValueError("스냅샷 기준시각이 달라졌습니다.")
        if actual > source_at:
            raise ValueError("평가시각이 원천 기록 시각보다 늦습니다.")
        return actual
    begin, end = observed("begin", first), observed("end", last)
    raw = fields.get("flows", "").strip()
    if not raw:
        raise ValueError("대조한 현금흐름을 입력하세요. 입출금이 없으면 ‘없음’을 입력하세요.")
    flows = []
    if raw != "없음":
        for line in raw.splitlines():
            try:
                date_text, text = line.split(",")
                when = datetime.fromisoformat(date_text.strip())
                when = when if when.tzinfo else when.replace(tzinfo=intel.KST)
                text = text.strip()
                amount = store.number(text.lstrip("+-")) if text[:1] in ("+", "-") else store.number(text)
                if text.startswith("-"):
                    amount = -amount
                if not amount or text[:2] in ("--","++","-+","+-"):
                    raise ValueError
            except (ValueError, ArithmeticError):
                raise ValueError("입출금을 한 줄에 'KST 시각, 부호 있는 금액'으로 입력하세요.") from None
            flows.append((when, amount))
    gain, rate = calculate(first["value"], last["value"], begin, end, flows)
    record = dict(begin=begin.isoformat(), end=end.isoformat(), flows=sorted(
        [t.astimezone(intel.KST).isoformat(), store.fixed(v)] for t, v in flows),
        gain=store.fixed(gain), rate=store.fixed(rate) if rate is not None else None)
    def append(ledger):
        versions = ledger.setdefault(key, [])
        if not versions or versions[-1]["data"] != record:
            if str(len(versions)) != fields.get("revision", "0"):
                raise ValueError("다른 대조 결과가 먼저 저장됐습니다. 최신 화면에서 확인하세요.")
            versions.append(dict(recorded=datetime.now(intel.KST).isoformat(), data=record))
        return ledger
    intel.update_json(package, FILE, {}, append)


def panel(package, base, csrf):
    pairs = intervals(package)
    if not pairs:
        return ('<section id="performance"><h2>입출금 조정 계좌 성과</h2>'
                '<p>같은 계좌·통화·원천의 완전한 평가액이 서로 다른 두 시점에 쌓이면 기간을 대조할 수 있습니다.</p></section>')
    ledger = intel.private_json(package, FILE, {})
    out = ['<section id="performance"><h2>입출금 조정 계좌 성과</h2>'
           '<p>계좌 안의 종목 매매는 내부 이동입니다. 입출금·현물이체와 통화 간 전환은 해당 평가 범위의 '
           '외부 이동으로 대조하세요. 배당·수수료가 평가액에 반영됐는지도 확인하세요.</p>']
    for key, (a, b) in sorted(pairs.items(), key=lambda p: p[1][1]["as_of"], reverse=True):
        versions = ledger.get(key, [])
        out.append(f'<details><summary>{e(store.PROVIDERS[a["provider"]])} · {e(a["account"])} · {e(a["currency"])} · '
                   f'{datetime.fromisoformat(b["as_of"]).astimezone(intel.KST):%Y-%m-%d} · '
                   f'{"대조 완료" if versions else "입출금 확인 대기"}</summary>'
                   f'<p>기초 {e(a["value"])} / 기말 {e(b["value"])} · 원천 '
                   f'{"엑셀 수정시각" if a["source"]=="workbook" else "스냅샷 기준시각"} '
                   f'{e(a["as_of"])} ~ {e(b["as_of"])}</p>')
        if versions:
            for version in reversed(versions):
                r = version["data"]
                rate = f'{Decimal(r["rate"]):+.2f}%' if r["rate"] is not None else "산정 보류"
                out.append(f'<p>대조 {e(version["recorded"])} · 입출금 제외 손익 {e(r["gain"])} · '
                           f'수정 디츠 수익률 {rate} · 입출금 {len(r["flows"])}건</p>')
        out.append(f'<form method="post" action="{e(base)}/desk/manager/reconcile">'
                   f'<input type="hidden" name="csrf" value="{e(csrf)}"><input type="hidden" name="interval" value="{key}">'
                   f'<input type="hidden" name="revision" value="{len(versions)}">')
        for name,label,point in (("begin","기초",a),("end","기말",b)):
            stamp = datetime.fromisoformat(point["as_of"]).astimezone(intel.KST)
            value = f' value="{stamp.isoformat()}" readonly' if point["source"] == "snapshot" else ""
            out.append(f'<label>{label} 실제 평가시각 (KST)<input required name="{name}"{value} '
                       f'placeholder="YYYY-MM-DDTHH:MM:SS"></label>')
        out.append('<label>입출금 내역<textarea required name="flows" rows="3" '
                   'placeholder="YYYY-MM-DDTHH:MM, +금액 또는 없음"></textarea></label>'
                   '<label><input type="checkbox" required name="confirmed" value="yes"> '
                   '두 평가액의 자산·현금 범위와 외부 이동 전체를 대조했습니다.</label>'
                   '<button>기간 성과 계산·저장</button></form></details>')
    return "".join(out) + "</section>"
