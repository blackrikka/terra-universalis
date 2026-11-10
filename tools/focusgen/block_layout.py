#!/usr/bin/env python3
"""중점 트리를 덩어리(block) 단위로 다시 놓는다 (사양서 63). merge_focus.py 가 autolayout 다음에 부른다.

autolayout 은 모든 갈래를 옆으로 늘어놓는다. 그런데 allow_branch 로 하나만 보이는 갈래들(예: 시라쿠사의 정치 루트 5개)은
나란히 두면 고르지 않은 갈래 자리가 빈 구멍으로 남는다. 그래서:
    - 덩어리 = 머리 중점과 그 아래 모든 중점 (autolayout 이 정한 덩어리 안의 모양은 그대로)
    - ORDER 의 순서대로 왼쪽부터 덩어리를 놓는다. 덩어리 사이 간격 GAP.
    - 한 칸에 머리 여럿을 주면 (리스트) 그 덩어리들을 같은 x 에 겹쳐 놓는다 (한 번에 하나만 보이는 갈래).
    - 뿌리 중점은 겹친 칸 가운데 위에 둔다. 모든 덩어리의 머리는 뿌리 바로 아랫줄에 둔다.

사용법:  python -I tools/focusgen/block_layout.py --tag SIR      (merge_focus.py --tag SIR 이 자동으로 부른다)
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NF = HERE.parents[1] / "terra_universalis" / "common" / "national_focus"
GAP = 4

# chain: 뿌리와 겹친 칸 사이에 끼는 중점 (예: 빅토리아의 '대공 회의 소집'). under_chain: 머리가 chain 끝 아래에 붙는 칸의 번호.
ORDER = {
    "VIC": dict(root="TU_VIC_crown_focus", center=0, chain=["TU_VIC_dukes_summit"], under_chain=[0], slots=[
        ["TU_VIC_duk_route", "TU_VIC_glasgow_return", "TU_VIC_dublinn_uprising", "TU_VIC_par_route"],
        ["TU_VIC_exp_mandate"],
        ["TU_VIC_eco_industry_charter"],
        ["TU_VIC_eco_knight_recruit"],
        ["TU_VIC_eco_convoy_lanes"],
        ["TU_VIC_eco_air_ministry"],
        ["TU_VIC_eco_royal_academy"],
    ]),
    "SIR": dict(root="TU_SIR_root", center=1, slots=[
        ["TU_SIR_wine_olive"],
        ["TU_SIR_bellone_head", "TU_SIR_gambino_head", "TU_SIR_saluzzo_head", "TU_SIR_law_head", "TU_SIR_wolf_head"],
        ["TU_SIR_bodyguards"],
        ["TU_SIR_foreign_ministry"],
    ]),
}

FOCUS_RE = re.compile(r"(\n\tfocus = \{\r?\n\t\tid = (\w+)\r?\n)(.*?)(\r?\n\t\})", re.S)


def parse(text):
    out = {}
    for m in FOCUS_RE.finditer(text):
        body = m.group(3)
        pre = re.findall(r"prerequisite = \{([^}]*)\}", body)
        out[m.group(2)] = dict(x=int(re.search(r"\n\t\tx = (-?\d+)", "\n" + body).group(1)),
                               y=int(re.search(r"\n\t\ty = (-?\d+)", "\n" + body).group(1)),
                               pre={p for g in pre for p in re.findall(r"focus = (\w+)", g)})
    return out


def block_of(head, fs, root):
    members, changed = {head}, True
    while changed:
        changed = False
        for fid, f in fs.items():
            if fid not in members and fid != root and f["pre"] & members:
                members.add(fid)
                changed = True
    return members


def apply(tag):
    cfg = ORDER.get(tag)
    if not cfg:
        return None
    path = NF / ("tu_%s.txt" % tag.lower())
    text = path.read_text(encoding="utf-8-sig")
    fs = parse(text)
    root = cfg["root"]
    chain = cfg.get("chain", [])
    newx, newy, cursor, placed = {}, {root: fs[root]["y"]}, 0, set(chain)
    centers = []
    for si, slot in enumerate(cfg["slots"]):
        width = 0
        for head in slot:
            mem = block_of(head, fs, root)
            assert not (mem & placed), (head, sorted(mem & placed))
            placed |= mem
            lo = min(fs[m]["x"] for m in mem)
            hi = max(fs[m]["x"] for m in mem)
            width = max(width, hi - lo)
        for head in slot:
            mem = block_of(head, fs, root)
            lo = min(fs[m]["x"] for m in mem)
            hi = max(fs[m]["x"] for m in mem)
            off = cursor + (width - (hi - lo)) // 2 - lo       # 좁은 덩어리는 칸 가운데
            top = fs[root]["y"] + 1 + (len(chain) if si in cfg.get("under_chain", []) else 0)
            dy = top - fs[head]["y"]                           # 덩어리의 머리는 뿌리(또는 chain 끝) 바로 아랫줄 (autolayout 이 아래로 내린 덩어리를 올린다)
            for m in mem:
                newx[m] = fs[m]["x"] + off
                newy[m] = fs[m]["y"] + dy
        centers.append(cursor + width // 2)
        cursor += width + GAP
    left = set(fs) - placed - {root}
    assert not left, "ORDER 에 없는 중점: %s" % sorted(left)
    newx[root] = centers[cfg["center"]]
    for i, c in enumerate(chain):
        newx[c] = centers[cfg["center"]]
        newy[c] = fs[root]["y"] + 1 + i
    shift = newx[root]                                         # 뿌리를 x = 0 에 (initial_show_position)
    newx = {k: v - shift for k, v in newx.items()}

    def sub(m):
        fid = m.group(2)
        body = re.sub(r"(\n\t\tx = )-?\d+", lambda q: q.group(1) + str(newx[fid]), "\n" + m.group(3), count=1)[1:]
        body = re.sub(r"(\n\t\ty = )-?\d+", lambda q: q.group(1) + str(newy[fid]), "\n" + body, count=1)[1:]
        return m.group(1) + body + m.group(4)

    new = FOCUS_RE.sub(sub, text)
    # 검사: 같은 줄에서 보이는 중점끼리 간격 2 이상 (겹친 칸 안의 다른 갈래끼리는 제외)
    slot_of = {}
    for i, slot in enumerate(cfg["slots"]):
        for j, head in enumerate(slot):
            for m in block_of(head, fs, root):
                slot_of[m] = (i, j)
    rows = {}
    for fid, f in fs.items():
        rows.setdefault(newy[fid], []).append(fid)
    for y, ids in rows.items():
        for a in ids:
            for b in ids:
                if a < b and abs(newx[a] - newx[b]) < 2:
                    sa, sb = slot_of.get(a), slot_of.get(b)
                    if not (sa and sb and sa[0] == sb[0] and sa[1] != sb[1]):
                        raise SystemExit("BLOCK_LAYOUT 겹침: %s %s (y=%d)" % (a, b, y))
    changed = new != text
    if changed:
        path.write_text(new, encoding="utf-8")
    return dict(width=cursor - GAP, changed=changed)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    a = ap.parse_args(argv)
    r = apply(a.tag)
    print("BLOCK_LAYOUT %s %s" % (a.tag, r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
