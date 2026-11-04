#!/usr/bin/env python3
"""편집기 저장 로직 검사 (파일은 쓰지 않는다).

    python -I tools/editor/test_editor.py
"""

import copy
import difflib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pdx  # noqa: E402
import server as S  # noqa: E402

FAIL = []


def check(cond, msg):
    if not cond:
        FAIL.append(msg)
        print("FAIL", msg)


def changed_lines(a, b):
    return [l for l in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
            if l[:1] in "+-" and not l.startswith(("+++", "---"))]


def model(kind, text):
    root = pdx.parse(text)
    return [(loc, S.child_model(text, e.value), e) for loc, e, _ in S.entities(kind, root)]


def roundtrip():
    n = 0
    for kind, info in S.KINDS.items():
        for p in sorted((S.MOD / info["dir"]).glob("*.txt")):
            text, _ = pdx.read_text(p)
            ents = model(kind, text)
            if not ents:
                continue
            changes = [{"op": "edit", "loc": loc, "children": ch} for loc, ch, _ in ents]
            out = S.apply_changes(kind, text, changes)
            check(out == text, "변경 없는 저장이 글자를 바꿈: %s" % p.name)
            n += len(ents)
    print("roundtrip: 항목 %d개 그대로" % n)


def edits():
    p = S.MOD / "common/national_focus/tu_kaz.txt"
    text, _ = pdx.read_text(p)
    loc, ch, e = model("focus", text)[1]
    # 1. 값 하나 바꾸기 -> 그 줄만
    ch2 = copy.deepcopy(ch)
    next(c for c in ch2 if c["key"] == "cost")["value"] = "7"
    out = S.apply_changes("focus", text, [{"op": "edit", "loc": loc, "children": ch2}])
    d = changed_lines(text, out)
    check(d == ["-\t\tcost = 10", "+\t\tcost = 7"], "cost 수정: %r" % d)
    # 2. 블록 고치기
    ch3 = copy.deepcopy(ch)
    cr = next(c for c in ch3 if c["key"] == "completion_reward")
    cr["value"] += "\nadd_stability = 0.05"
    out = S.apply_changes("focus", text, [{"op": "edit", "loc": loc, "children": ch3}])
    d = changed_lines(text, out)
    check(any(l == "+\t\t\tadd_stability = 0.05" for l in d), "블록 수정 들여쓰기: %r" % d)
    m = dict((l, c) for l, c, _ in model("focus", out))[loc]
    check("add_stability = 0.05" in next(c for c in m if c["key"] == "completion_reward")["value"], "블록 수정 반영")
    # 3. 항목 추가 (여러 줄 블록)
    ch4 = copy.deepcopy(ch) + [{"i": None, "key": "bypass", "op": "=", "kind": "block",
                                "value": "has_country_flag = A\nhas_country_flag = B"}]
    out = S.apply_changes("focus", text, [{"op": "edit", "loc": loc, "children": ch4}])
    d = changed_lines(text, out)
    want = "\t\t}\n\t\tbypass = {\n\t\t\thas_country_flag = A\n\t\t\thas_country_flag = B\n\t\t}\n\t}\n"
    check(len(d) == 4 and want in out.replace("\r\n", "\n"), "항목 추가: %r" % d)
    # 4. 항목 삭제
    ch5 = [c for c in copy.deepcopy(ch) if c["key"] != "search_filters"]
    out = S.apply_changes("focus", text, [{"op": "edit", "loc": loc, "children": ch5}])
    d = changed_lines(text, out)
    check(len(d) == 1 and "search_filters" in d[0], "항목 삭제: %r" % d)
    # 5. 새 중점 + 중점 삭제를 한 번에
    new = [{"key": "id", "kind": "scalar", "value": "TU_KAZ_test"}, {"key": "x", "kind": "scalar", "value": "3"},
           {"key": "y", "kind": "scalar", "value": "2"}, {"key": "cost", "kind": "scalar", "value": "10"},
           {"key": "completion_reward", "kind": "block", "value": "add_political_power = 25"}]
    loc_del = model("focus", text)[5][0]
    out = S.apply_changes("focus", text, [{"op": "create", "parent": "TU_KAZ_focus", "key": "focus", "children": new},
                                          {"op": "delete", "loc": loc_del}])
    locs = [l for l, _, _ in model("focus", out)]
    check("focus:TU_KAZ_test" in locs and loc_del not in locs, "중점 추가·삭제")
    check("\tfocus = {\n\t\tid = TU_KAZ_test\n" in out.replace("\r\n", "\n"), "새 중점 들여쓰기")
    # 6. 키 이름 바꾸기 (디시전)
    p = S.MOD / "common/decisions/tu_kaz_decisions.txt"
    text, _ = pdx.read_text(p)
    loc, ch, e = model("decision", text)[0]
    out = S.apply_changes("decision", text, [{"op": "edit", "loc": loc, "key": "TU_KAZ_renamed", "children": ch}])
    check(len(changed_lines(text, out)) == 2, "디시전 이름 바꾸기")
    # 7. 없는 분류에 디시전 만들기
    out = S.apply_changes("decision", text, [{"op": "create", "parent": "TU_KAZ_new_category", "key": "TU_KAZ_d",
                                              "children": [{"key": "cost", "kind": "scalar", "value": "50"}]}])
    check("decision:TU_KAZ_new_category/TU_KAZ_d" in [l for l, _, _ in model("decision", out)], "새 분류 + 디시전")
    # 8. 국민정신: 없는 슬롯 / 있는 슬롯
    p = S.MOD / "common/ideas/tu_kaz_ideas.txt"
    text, _ = pdx.read_text(p)
    out = S.apply_changes("idea", text, [
        {"op": "create", "parent": "country", "key": "TU_KAZ_i1", "children": [{"key": "picture", "kind": "scalar", "value": "x"}]},
        {"op": "create", "parent": "hidden_ideas", "key": "TU_KAZ_i2", "children": []}])
    locs = [l for l, _, _ in model("idea", out)]
    check("idea:country/TU_KAZ_i1" in locs and "idea:hidden_ideas/TU_KAZ_i2" in locs, "국민정신 추가: %r" % locs[-3:])
    # 9. 캐릭터 추가, 이벤트 추가
    p = S.MOD / "common/characters/KAZ.txt"
    text, _ = pdx.read_text(p)
    out = S.apply_changes("character", text, [{"op": "create", "parent": "characters", "key": "TU_KAZ_g", "children": [
        {"key": "name", "kind": "scalar", "value": "TU_KAZ_g"},
        {"key": "corps_commander", "kind": "block", "value": "skill = 3\nattack_skill = 3"}]}])
    check("character:TU_KAZ_g" in [l for l, _, _ in model("character", out)], "캐릭터 추가")
    p = S.MOD / "events/tu_kaz_events.txt"
    text, _ = pdx.read_text(p)
    out = S.apply_changes("event", text, [{"op": "create", "parent": "", "key": "country_event", "children": [
        {"key": "id", "kind": "scalar", "value": "tu_kaz_ev.999"}, {"key": "is_triggered_only", "kind": "scalar", "value": "yes"}]}])
    check("event:tu_kaz_ev.999" in [l for l, _, _ in model("event", out)], "이벤트 추가")
    # 10. CRLF 파일
    crlf = text.replace("\r\n", "\n").replace("\n", "\r\n")
    loc, ch, e = model("event", crlf)[0]
    ch2 = copy.deepcopy(ch) + [{"i": None, "key": "fire_only_once", "op": "=", "kind": "scalar", "value": "yes"}]
    out = S.apply_changes("event", crlf, [{"op": "edit", "loc": loc, "children": ch2}])
    check("\n" not in out.replace("\r\n", ""), "CRLF 유지")
    print("edits: 검사 끝")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    roundtrip()
    edits()
    print("실패 %d건" % len(FAIL) if FAIL else "모두 통과")
    sys.exit(1 if FAIL else 0)
