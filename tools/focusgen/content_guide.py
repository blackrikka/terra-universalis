#!/usr/bin/env python3
"""나라 콘텐츠 가이드 문서 만들기 (사양서 69).

tools/focusgen/content/<tag>.py 가 만든 중점·디시전·이벤트를 읽어 사람이 읽는 정리 문서를 쓴다.
    python -I tools/focusgen/content_guide.py --tag SIR        ->  docs/가이드_<나라 이름>.md
효과는 흔한 것만 한국어로 풀어 쓰고 나머지는 스크립트 그대로 둔다. 중점 설명(desc)이 있으면 그것을 먼저 쓴다.
"""

import argparse
import importlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "content"))

SIMPLE = [
    (r"TU_build_civ_factory = yes", "민간 공장 +1"), (r"TU_build_mil_factory = yes", "군수 공장 +1"),
    (r"TU_build_infrastructure = yes", "인프라 +1"), (r"TU_build_forts_1 = yes", "국경 요새"),
    (r"add_political_power = (-?\d+)", r"정치력 \1"), (r"add_manpower = (-?\d+)", r"인력 \1"),
    (r"army_experience = (-?\d+)", r"육군 경험치 \1"), (r"air_experience = (-?\d+)", r"공군 경험치 \1"),
    (r"add_command_power = (-?\d+)", r"지휘력 \1"), (r"add_research_slot = 1", "연구 슬롯 +1"),
    (r"add_stability = (-?[\d.]+)", lambda m: "안정도 %+d%%" % round(float(m.group(1)) * 100)),
    (r"add_war_support = (-?[\d.]+)", lambda m: "전쟁 지지 %+d%%" % round(float(m.group(1)) * 100)),
    (r"add_tech_bonus = \{.*\}", "연구 보너스"), (r"add_ideas = (\w+)", r"국민정신 \1"),
    (r"swap_ideas = \{ remove_idea = \w+ add_idea = (\w+) \}", r"국민정신 \1"), (r"remove_ideas = (\w+)", r"\1 제거"),
    (r"recruit_character = (\w+)", r"\1 합류"), (r"add_offsite_building = \{.*\}", "영토 밖 민간 공장 +1"),
    (r"create_wargoal = \{.*\}", "전쟁 명분"), (r"every_neighbor_country = \{.*create_wargoal.*\}", "이웃 나라 모두에 병합 명분"),
    (r"random_owned_controlled_state = \{.*add_resource = \{ type = steel amount = (\d+) \}.*\}", r"오리론 +\1"),
    (r"capital_scope = \{ add_extra_state_shared_building_slots = (\d+) \}", r"수도 건물 칸 +\1"),
    (r"capital_scope = \{ create_unit = .*\}", "사단 1개 생성"), (r"create_faction = \w+", "세력 결성"), (r"add_to_faction = FROM", "세력에 초청"), (r"country_event = \{ id = ([\w.]+).*\}", r"이벤트 \1"),
]
SKIP = re.compile(r"set_country_flag|mark_focus_tree|set_variable|add_to_variable|^if = |hidden_effect|_template = yes|"
                  r"set_politics|promote_character|clamp_variable|^FROM = |^\}|^\d+ = |random_list|retire_character")


def words(effects, loc):
    out = []
    for e in effects:
        e = e.strip()
        m = re.match(r"(TU_\w+?_(\w+?)_(m?)(\d+)) = yes$", e)        # 수치 효과 (법 +10 등): 툴팁 문구를 쓴다
        if m and (m.group(1) + "_tt") in loc:
            out.append(re.sub(r"§.", "", loc[m.group(1) + "_tt"]))
            continue
        if SKIP.search(e):
            continue
        for pat, rep in SIMPLE:
            if re.fullmatch(pat, e, re.S):
                e = re.sub(pat, rep, e, flags=re.S)
                break
        out.append(re.sub(r"\b(TU_\w+|tu_\w+\.\d+)\b", lambda q: "'%s'" % re.sub(r"§.", "", loc.get(q.group(1), loc.get(q.group(1) + ".t", q.group(1)))), e))
    return ", ".join(dict.fromkeys(out))


def clean(s):
    return re.sub(r"§.", "", s).replace("\\n", " ").strip()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    a = ap.parse_args(argv)
    mod = importlib.import_module(a.tag.lower())
    C = mod.C
    loc = C.ko
    fs = {f["id"]: f for f in C.focuses}
    children = {}
    for f in C.focuses:
        for g in f["pre"]:
            for p in g:
                children.setdefault(p, []).append(f["id"])
    root = C.root
    L = ["# %s 가이드" % C.name_ko, "",
         "> `tools/focusgen/content_guide.py --tag %s` 가 생성기에서 뽑아 쓴 문서다. 손으로 고치지 말고 다시 돌린다." % a.tag, "",
         "중점 %d개, 국민정신 %d개, 디시전 %d개, 이벤트 %d개." % (
             len(C.focuses), len(C.ideas), sum(len(v) for v in C.decisions.values()), len(C.events)), ""]

    def line(fid):
        f = fs[fid]
        d = clean(loc.get(fid + "_desc", ""))
        eff = words(f["reward"], loc)
        cond = words(f["available"], loc) if f["available"] else ""
        me = " / 택일: " + ", ".join(clean(loc[x]) for x in f["me"]) if f["me"] else ""
        return "| %s | %d | %s | %s |" % (clean(loc[fid]), f["cost"] * 7, eff or "-", (d + me).strip(" /") or "-")

    L += ["## 중점", "", "### 시작", "", "| 중점 | 일 | 효과 | 설명 |", "|---|---|---|---|", line(root), ""]
    for head in children.get(root, []):
        order, stack = [], [head]
        while stack:
            x = stack.pop(0)
            if x in order:
                continue
            order.append(x)
            stack += children.get(x, [])
        kind = "루트 (고른 것만 보인다)" if fs[head]["allow_branch"] else "공통"
        L += ["### %s — %s, %d개" % (clean(loc[head]), kind, len(order)), "", "| 중점 | 일 | 효과 | 설명 |", "|---|---|---|---|"]
        L += [line(x) for x in order] + [""]

    L += ["## 디시전", ""]
    for cid, _, _ in C.categories:
        L += ["### %s" % clean(loc[cid]), "", clean(loc.get(cid + "_desc", "")), "", "| 디시전 | 정치력 | 효과 | 설명 |", "|---|---|---|---|"]
        for d in C.decisions[cid]:
            eff = words(d["effect"] + (d["remove_effect"] or []), loc)
            if d["modifier"]:
                eff = (eff + ", " if eff else "") + "%d일 동안 %s" % (d["days_remove"], ", ".join("%s %s" % kv for kv in d["modifier"].items()))
            L.append("| %s | %s | %s | %s |" % (clean(loc[d["id"]]), "미션 %d일" % d["mission"]["days"] if d["mission"] else d["cost"], eff or "-", clean(loc.get(d["id"] + "_desc", "")) or "-"))
        L.append("")

    L += ["## 이벤트", "", "| 이벤트 | 선택지 → 효과 |", "|---|---|"]
    for e in C.events:
        opts = " / ".join("%s → %s" % (clean(o[0]), words(o[2], loc) or "-") for o in e["options"])
        L.append("| %s (`%s`) | %s |" % (clean(loc[e["id"] + ".t"]), e["id"], opts))
    out = REPO / "docs" / ("가이드_%s.md" % C.name_ko)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("GUIDE %s -> %s" % (a.tag, out.relative_to(REPO)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
