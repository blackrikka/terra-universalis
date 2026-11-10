#!/usr/bin/env python3
"""빅토리아 중점 정리 (사양서 79). 한 번만 돌린다 (이미 돌렸으면 아무것도 하지 않는다).

원본 조각 tools/focusgen/vic/*.txt 를 고친다.
    1. 중간 단계 A/B 택일 쌍을 하나로 합친다 (MERGE): 지우는 쪽의 효과(공장·국민정신·이벤트 …)를 남기는 쪽에 모으고, 자식은 남기는 쪽 아래로.
    2. 곁가지를 지운다 (DELETE): 자식은 지운 중점의 부모 아래로.
    3. 정치 노선 4개(대공 의회 / 아슬란 복위 / 드라코 타라 봉기 / 빅토리아 의회)를 이벤트 tu_vic_ev.40 으로 고르게 한다:
       노선 중점은 모두 allow_branch = TU_VIC_route_<duk|asl|drc|par> 로 그 노선을 골랐을 때만 보이고, 노선끼리의 택일은 없앤다.
    4. 지운 중점을 조건으로 쓰던 디시전은 남은 부모 중점으로 옮긴다. 설명의 '~와 상호 배타' 문장도 정리한다.
계획은 tools/focusgen/vic_plan.py (MERGE, DELETE).
사용법 (python -I):  python -I tools/focusgen/vic_cleanup.py   그다음  merge_focus.py --tag VIC
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MOD = REPO / "terra_universalis"
sys.path.insert(0, str(HERE))
from vic_plan import MERGE, DELETE  # noqa: E402
from retheme import split_statements, GENERIC  # noqa: E402

PARTS = ["p0_existing", "p1_politics", "p2_expansion", "p3_economy"]
P = "TU_VIC_"
ROUTES = {
    "duk": ["duk_route", "ducal_arsenal", "london_fortress", "dukes_order"],
    "asl": ["glasgow_return", "glasgow_volunteers", "siege_crowned", "aslan_legitimacy"],
    "drc": ["dublinn_uprising", "dublinn_suppression", "dublinn_talks", "steam_knight_formation"],
    "par": ["par_route"],
}
PREFIX = {"duk": "duk_", "asl": "asl_", "drc": "drc_", "par": "par_"}
OVERRIDE = {"status_quo": "duk_route", "eco_harbour_grid": "eco_convoy_lanes"}      # 디시전이 가리킬 곳


def split_blocks(s):
    if s.startswith("\tfocus = {"):                      # 파일 맨 앞 중점도 나뉘도록
        s = "\n" + s
    parts = re.split(r"(?=\n\tfocus = \{\n)", s)
    return parts[0], parts[1:]


def bid(b):
    return re.search(r"\n\t\tid = (\S+)", b).group(1)[len(P):]


def groups(b):
    return [re.findall(r"focus = %s(\w+)" % P, g) for g in re.findall(r"prerequisite = \{([^}]*)\}", b)]


def set_prereq(b, ids):
    """prerequisite 를 하나의 줄 (OR 묶음 아님: 각각 따로) 로 다시 쓴다. ids = [[...], ...]"""
    b = re.sub(r"\n\t\tprerequisite = \{[^}]*\}", "", b)
    add = "".join("\n\t\tprerequisite = { %s }" % " ".join("focus = %s%s" % (P, x) for x in g) for g in ids if g)
    i = b.index("\n", b.index("\t\tid = "))
    return b[:i] + add + b[i:]


def replace_ref(b, old, new):
    """prerequisite / mutually_exclusive 안의 old 를 new(목록, 비어 있으면 지움)로."""
    def pre(m):
        toks = re.findall(r"focus = (\S+)", m.group(1))
        out = []
        for t in toks:
            for x in (new if t == P + old else [t]):
                if x not in out:
                    out.append(x)
        return "prerequisite = { %s }" % " ".join("focus = %s" % x for x in out) if out else None
    def mex(m):
        toks = [t for t in re.findall(r"focus = (\S+)", m.group(1)) if t != P + old]
        return "mutually_exclusive = { %s }" % " ".join("focus = %s" % x for x in toks) if toks else None
    for rx, fn in ((r"prerequisite = \{([^}]*)\}", pre), (r"mutually_exclusive = \{([^}]*)\}", mex)):
        out, pos = [], 0
        for m in re.finditer(rx, b):
            if (P + old) not in m.group(1):
                continue
            rep = fn(m)
            out.append(b[pos:m.start()])
            if rep is None:                                   # 줄 통째로 지움
                ls = b.rfind("\n", 0, m.start())
                out[-1] = out[-1][:len(out[-1]) - (m.start() - ls)]
                pos = m.end()
            else:
                out.append(rep)
                pos = m.end()
        out.append(b[pos:])
        b = "".join(out)
    return b


def reward_span(b):
    i = b.find("\t\tcompletion_reward = {")
    if i < 0:
        return None
    j = b.index("{", i)
    d, k = 0, j
    while True:
        d += (b[k] == "{") - (b[k] == "}")
        if d == 0:
            return j, k
        k += 1


def reward_stmts(b):
    sp = reward_span(b)
    return [t for _, t in split_statements(b[sp[0] + 1:sp[1]])] if sp else []


def add_rewards(b, lines):
    sp = reward_span(b)
    j, k = sp
    have = {re.sub(r"\s+", " ", t) for t in reward_stmts(b)}
    lines = [l for l in lines if re.sub(r"\s+", " ", l) not in have]
    if not lines:
        return b
    return b[:k].rstrip("\t") + "".join("\t\t\t%s\n" % l for l in lines) + "\t\t" + b[k:]


def non_generic(b):
    out = []
    for t in reward_stmts(b):
        key = re.match(r"([^\s=]+)", t).group(1)
        if key not in GENERIC:
            out.append(t)
    return out


def add_gate(b, route):
    if "allow_branch" in b:
        return b
    m = re.search(r"\n\t\tcost = \d+", b)
    return b[:m.end()] + "\n\t\tallow_branch = {\n\t\t\thas_country_flag = TU_VIC_route_%s\n\t\t}" % route + b[m.end():]


def route_of(i):
    for r, heads in ROUTES.items():
        if i in heads or i.startswith(PREFIX[r]):
            return r
    return None


def main():
    blocks = {}
    order, pre_text = [], {}
    for part in PARTS:
        pre_text[part], bl = split_blocks((HERE / "vic" / (part + ".txt")).read_text(encoding="utf-8"))
        for b in bl:
            blocks[bid(b)] = b
            order.append((part, bid(b)))
    if "status_quo" not in blocks:
        print("VIC_CLEANUP 이미 적용됨")
        return 0
    n0 = len(blocks)
    parent = {i: (groups(b)[0] if groups(b) else []) for i, b in blocks.items()}
    # 다른 파일의 참조를 옮길 곳
    def resolve(i):
        i = OVERRIDE.get(i, i)
        while i in DELETE and i not in OVERRIDE:
            i = parent[i][0]
        return MERGE.get(i, i)
    moved = {i: resolve(i) for i in list(MERGE) + DELETE}

    # 1. 합치기
    for drop, keep in MERGE.items():
        blocks[keep] = add_rewards(blocks[keep], non_generic(blocks[drop]))
        del blocks[drop]
        for i in blocks:
            blocks[i] = replace_ref(blocks[i], drop, [P + keep])
    # 2. 지우기 (자식은 부모 아래로)
    for d in DELETE:
        par = [P + x for x in groups(blocks[d])[0]] if groups(blocks[d]) else []
        del blocks[d]
        for i in blocks:
            blocks[i] = replace_ref(blocks[i], d, par)
    # 3. 정치 노선
    for i in ("ducal_arsenal", "london_fortress"):
        blocks[i] = set_prereq(blocks[i], [["duk_route"]])
    blocks["duk_route"] = set_prereq(blocks["duk_route"], [["dukes_summit"]])
    for head in ("duk_route", "asl_route", "drc_route", "par_route", "dukes_order", "aslan_legitimacy", "dublinn_talks"):
        blocks[head] = re.sub(r"\n\t\tmutually_exclusive = \{[^}]*\}", "", blocks[head])
    blocks["dublinn_suppression"] = re.sub(r"\n\t\tmutually_exclusive = \{[^}]*\}", "", blocks["dublinn_suppression"]) if False else blocks["dublinn_suppression"]
    blocks["dublinn_suppression"] = replace_ref(blocks["dublinn_suppression"], "drc_route", [])
    blocks["dublinn_talks"] = "\n\tfocus = {" + blocks["dublinn_talks"].split("\n\tfocus = {", 1)[1]
    # 대공 영지 결속 같은 합친 쌍 말고 '남은 큰 갈림길': 의회 표결/공개 자문회의, 충성 귀족/귀족 재산 몰수, 진압/타협, 자유 무역/보호 관세 (그대로)
    for i in list(blocks):
        r = route_of(i)
        if r:
            blocks[i] = add_gate(blocks[i], r)
    # 4. 노선을 고르는 이벤트: 대공 회의 소집이 부른다
    blocks["dukes_summit"] = add_rewards(blocks["dukes_summit"], ["country_event = { id = tu_vic_ev.40 }"])

    for part in PARTS:
        text = pre_text[part] + "".join(blocks[i] for p, i in order if p == part and i in blocks)
        (HERE / "vic" / (part + ".txt")).write_text(text, encoding="utf-8")

    # 5. 다른 파일의 참조
    refs = 0
    for f in list((MOD / "common").rglob("*.txt")) + list((MOD / "events").rglob("*.txt")):
        t = f.read_text(encoding="utf-8-sig")
        new = t
        for old, to in moved.items():
            new = re.sub(r"\b%s%s\b" % (P, old), P + to, new)
        if new != t:
            f.write_text(new, encoding="utf-8")
            refs += 1
    print("VIC_CLEANUP focuses %d -> %d (합침 %d, 지움 %d), 참조 파일 %d" % (n0, len(blocks), len(MERGE), len(DELETE), refs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
