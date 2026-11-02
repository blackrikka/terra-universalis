#!/usr/bin/env python3
"""양자택일 불균형 탐지 (표준 라이브러리만 사용, Python 3.10). 보고 전용: 파일을 고치지 않는다.

사용법:
    python -I tools/focusgen/find_lopsided.py --tag <TAG>   # 태그 하나 (조각 폴더 tools/focusgen/<태그 소문자>/)
    python -I tools/focusgen/find_lopsided.py --all         # URS VIC YAN KZD RHO LGM REU 전부

조각 읽기는 merge_focus.load_parts 를 쓴다 (중괄호 인식, 문자열과 주석 무시).

트리 (autolayout.py 와 같은 규칙)
    부모      prerequisite 블록 안 모든 id (mutually_exclusive 는 부모가 아님)
    row       뿌리 0, 나머지 1 + max(부모 row)  (가장 긴 경로)
    주 부모   부모 중 row 가 가장 큰 것, 같으면 파일에서 먼저 나온 것
    depth     주 부모 트리에서 아래로 가장 긴 경로 (잎 = 0)
    잎        아무 중점도 prerequisite 로 쓰지 않는 중점

A. 불균형 상호배타 쌍: mutually_exclusive 로 묶인 (A, B) 가 같은 주 부모를 가지고 |depth(A) - depth(B)| >= 2
B. 매달린 잎: 상호배타가 없는 잎 L 의 주 부모에 depth >= 1 인 다른 자식이 있다.

제외 (excluded 집계는 A, B 후보 중 아래 규칙으로 빠진 것만 센다)
    route choice  같은 주 부모, 같은 row 에서 상호배타 상대가 2개 이상인 중점 (정치 루트 선택)
    frozen        has_completed_focus 로 참조되는 중점. 참조 출처는 terra_universalis/common,
                  terra_universalis/events 의 모든 .txt 와 다른 태그 폴더의 조각 파일
    root          뿌리 (부모가 없음). A, B 후보가 될 수 없으므로 목록만 보여 주고 excluded 에는 넣지 않는다.

종료 코드는 항상 0 이다 (보고 도구). 사용법 오류만 argparse 가 2 를 돌려준다.
"""

import argparse
import re
import sys
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent            # <repo>/tools/focusgen
REPO = HERE.parents[1]                            # <repo>
MOD_ROOT = REPO / "terra_universalis"
FROZEN_SCAN_DIRS = (MOD_ROOT / "common", MOD_ROOT / "events")
ALL_TAGS = ("URS", "VIC", "YAN", "KZD", "RHO", "LGM", "REU")
MIN_DEPTH_GAP = 2                                 # 카테고리 A 의 깊이 차이 하한

sys.path.insert(0, str(HERE))
import merge_focus  # noqa: E402  조각 읽기 (load_parts), has_completed_focus 정규식 (DONE_RE), show


def read_frozen(tag):
    """has_completed_focus 로 참조되는 중점 id -> 첫 출처 'file:line'."""
    own = (HERE / tag.lower()).resolve()
    sources = []
    for base in FROZEN_SCAN_DIRS:
        if base.is_dir():
            sources.extend(sorted(p for p in base.rglob("*.txt") if p.is_file()))
    if HERE.is_dir():
        for folder in sorted(HERE.iterdir()):
            if folder.is_dir() and not folder.name.startswith(("_", ".")) and folder.resolve() != own:
                sources.extend(sorted(folder.glob("*.txt")))
    frozen = {}
    for path in sources:
        text = path.read_bytes().decode("utf-8", errors="replace")
        for line_no, raw in enumerate(text.split("\n"), 1):
            if "has_completed_focus" not in raw:
                continue
            code = raw.split("#", 1)[0]
            for fid in merge_focus.DONE_RE.findall(code):
                frozen.setdefault(fid, f"{merge_focus.show(path)}:{line_no}")
    return frozen


def analyse_tag(tag):
    """태그 하나를 분석해 보고를 출력한다. 반환: (A 개수, B 개수, excluded 개수)."""
    folder = HERE / tag.lower()
    if not folder.is_dir():
        print(f"ERROR {merge_focus.show(folder)}:0 piece folder not found")
        return 0, 0, 0

    warn = []
    parts = merge_focus.load_parts(folder, warn)
    for f in warn:
        print(f"WARN {f.path}:{f.line} {f.msg}")

    # 1) 노드 만들기 (파일 순서 = 조각 파일명 순, 조각 안은 줄 순)
    nodes = {}
    order = []
    for part in parts:
        for f in part["focuses"]:
            fid = f["id"]
            if fid in nodes:
                print(f"WARN {merge_focus.show(part['path'])}:{f['line']} duplicate focus id skipped: {fid}")
                continue
            nodes[fid] = {
                "file": merge_focus.show(part["path"]),
                "line": f["line"],
                "raw": f["refs"],       # [(prerequisite|mutually_exclusive, target)] 아직 풀지 않음
                "parents": [],          # 태그 안에 있는 부모
                "mutex": set(),         # 상호배타 상대 (양방향)
                "kids": [],             # 이 중점을 prerequisite 로 쓰는 중점
                "prim_kids": [],        # 주 부모가 이 중점인 중점 (트리 자식)
                "row": 0,
                "depth": 0,
                "primary": None,
            }
            order.append(fid)
    pos = {fid: i for i, fid in enumerate(order)}

    # 2) 참조 풀기 (태그 밖 id 는 무시하고 센다)
    unknown = 0
    for fid in order:
        node = nodes[fid]
        for kind, target in node["raw"]:
            if target not in nodes:
                unknown += 1
                continue
            if target == fid:
                continue
            if kind == "prerequisite":
                if target not in node["parents"]:
                    node["parents"].append(target)
            else:
                node["mutex"].add(target)
                nodes[target]["mutex"].add(fid)
    for fid in order:
        for p in nodes[fid]["parents"]:
            nodes[p]["kids"].append(fid)

    # 3) row (가장 긴 경로), 순환 검사 (Kahn)
    indeg = {fid: len(nodes[fid]["parents"]) for fid in order}
    ready = deque(fid for fid in order if indeg[fid] == 0)
    seen = 0
    while ready:
        fid = ready.popleft()
        seen += 1
        for k in nodes[fid]["kids"]:
            nodes[k]["row"] = max(nodes[k]["row"], nodes[fid]["row"] + 1)
            indeg[k] -= 1
            if indeg[k] == 0:
                ready.append(k)
    if seen != len(order):
        cyc = [fid for fid in order if indeg[fid] > 0]
        print(f"ERROR {merge_focus.show(folder)}:0 prerequisite cycle, analysis skipped: {', '.join(cyc[:10])}")
        return 0, 0, 0

    # 4) 주 부모와 트리 자식
    for fid in order:
        n = nodes[fid]
        if n["parents"]:
            n["primary"] = min(n["parents"], key=lambda p: (-nodes[p]["row"], pos[p]))
            nodes[n["primary"]]["prim_kids"].append(fid)

    # 5) depth (모든 자식 기준 아래로 가장 긴 경로). OR 선행으로 이어지는 짧은 쪽도 이어지는 것으로 본다.
    #    자식은 row 가 더 크므로 row 내림차순으로 계산
    for fid in sorted(order, key=lambda f: (-nodes[f]["row"], pos[f])):
        kids = nodes[fid]["kids"]
        nodes[fid]["depth"] = 1 + max(nodes[k]["depth"] for k in kids) if kids else 0

    # 6) 정치 루트 선택: 같은 주 부모, 같은 row 에서 상호배타 상대가 2개 이상
    route = set()
    for fid in order:
        n = nodes[fid]
        if n["primary"] is None:
            continue
        same = [m for m in n["mutex"]
                if nodes[m]["primary"] is not None
                and nodes[m]["primary"] == n["primary"]
                and nodes[m]["row"] == n["row"]]
        if len(same) >= 2:
            route.add(fid)

    frozen = read_frozen(tag)
    roots = [fid for fid in order if nodes[fid]["primary"] is None]

    # 7) 카테고리 A
    cat_a = []
    excluded = []
    done_pairs = set()
    for fid in order:
        for m in sorted(nodes[fid]["mutex"], key=pos.get):
            a, b = sorted((fid, m), key=pos.get)
            if (a, b) in done_pairs:
                continue
            done_pairs.add((a, b))
            na, nb = nodes[a], nodes[b]
            if na["primary"] is None or na["primary"] != nb["primary"]:
                continue
            if abs(na["depth"] - nb["depth"]) < MIN_DEPTH_GAP:
                continue
            shallow, deep = (a, b) if na["depth"] < nb["depth"] else (b, a)
            reasons = []
            if a in route or b in route:
                reasons.append("route choice")
            for x in (a, b):
                if x in frozen:
                    reasons.append(f"frozen ({x} referenced at {frozen[x]})")
            if reasons:
                excluded.append(("A", f"{shallow} <-> {deep}", "; ".join(reasons)))
            else:
                cat_a.append((na["primary"], shallow, deep))

    # 8) 카테고리 B
    leaves_by_parent = {}
    for fid in order:
        n = nodes[fid]
        p = n["primary"]
        if p is None or n["kids"] or n["mutex"]:
            continue
        if not any(nodes[s]["depth"] >= 1 for s in nodes[p]["prim_kids"] if s != fid):
            continue
        if fid in frozen:
            excluded.append(("B", fid, f"frozen (referenced at {frozen[fid]})"))
            continue
        leaves_by_parent.setdefault(p, []).append(fid)
    cat_b_count = sum(len(v) for v in leaves_by_parent.values())

    # 보고
    depth_max = max((nodes[f]["depth"] for f in order), default=0)
    print("")
    print(f"== {tag}  folder={merge_focus.show(folder)}  pieces={len(parts)}  focuses={len(order)}  "
          f"roots={len(roots)}  max_depth={depth_max}  unknown_refs={unknown}")

    print(f"[A] unbalanced mutually_exclusive pairs (same primary parent, depth gap >= {MIN_DEPTH_GAP}): {len(cat_a)}")
    for parent, shallow, deep in cat_a:
        s, d = nodes[shallow], nodes[deep]
        print(f"  parent={parent}")
        print(f"    shallow={shallow} depth={s['depth']} {s['file']}:{s['line']}")
        print(f"    deep={deep} depth={d['depth']} {d['file']}:{d['line']}")

    print(f"[B] dangling leaves (no mutually_exclusive, no children, parent has a continuing child): {cat_b_count}")
    for parent, leaves in leaves_by_parent.items():
        conts = [s for s in nodes[parent]["prim_kids"] if nodes[s]["depth"] >= 1]
        print(f"  parent={parent} (continuing children: {', '.join(conts)})")
        for leaf in leaves:
            print(f"    leaf={leaf} {nodes[leaf]['file']}:{nodes[leaf]['line']}")

    print(f"[ROUTE CHOICE] {len(route)} focuses (excluded from A, B)")
    for fid in sorted(route, key=pos.get):
        n = nodes[fid]
        print(f"  route choice: {fid} row={n['row']} parent={n['primary']} {n['file']}:{n['line']}")

    print(f"[ROOT] {len(roots)} roots (no parent, never candidates)")
    if roots:
        print("  " + ", ".join(roots))

    print(f"[EXCLUDED] {len(excluded)}")
    for kind, detail, reason in excluded:
        print(f"  {kind}: {detail} -> {reason}")

    return len(cat_a), cat_b_count, len(excluded)


def main(argv=None):
    parser = argparse.ArgumentParser(description="양자택일 불균형 탐지 (보고 전용)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tag", help="국가 태그 (예: URS). 조각 폴더는 tools/focusgen/<태그 소문자>/")
    group.add_argument("--all", action="store_true", help="모든 태그 (" + " ".join(ALL_TAGS) + ")")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tags = list(ALL_TAGS) if args.all else [args.tag.upper()]
    total = [0, 0, 0]
    for tag in tags:
        if not re.fullmatch(r"[A-Z][A-Z0-9]*", tag):
            print(f"ERROR invalid tag: {tag}")
            print(f"LOPSIDED tag={tag} A=0 B=0 excluded=0")
            continue
        a, b, ex = analyse_tag(tag)
        print(f"LOPSIDED tag={tag} A={a} B={b} excluded={ex}")
        total[0] += a
        total[1] += b
        total[2] += ex
    if args.all:
        print(f"LOPSIDED_TOTAL A={total[0]} B={total[1]} excluded={total[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
