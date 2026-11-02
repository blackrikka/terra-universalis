#!/usr/bin/env python3
"""국가 중점 트리에 continuous_focus_position 을 넣는다 (표준 라이브러리만 사용, Python 3.10).

사용법:
    python -I tools/focusgen/place_continuous.py               # 대상 파일 전부 갱신
    python -I tools/focusgen/place_continuous.py <파일> ...     # 지정한 파일만 갱신
    python -I tools/focusgen/place_continuous.py --check       # 쓰지 않고 검사 (누락 또는 Y 부족이면 exit 1)

대상: terra_universalis/common/national_focus/tu_*.txt 와 generic.txt
규칙: max_y = 트리 안 중점 절대 y 의 최댓값 (x/y + relative_position_id 체인, tu_lint 와 같은 계산)
      Y = (max_y + 2) * 130   (중점 한 줄 = 130 px)
      focus_tree 의 id 줄 바로 다음에 continuous_focus_position = { x = 50 y = Y } 를 넣는다.
      이미 있으면 그 줄만 고친다. 내용이 같으면 파일을 다시 쓰지 않는다 (idempotent).
      줄바꿈(LF/CRLF)과 나머지 내용은 그대로 둔다.
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # <repo>/tools/focusgen
REPO = HERE.parents[1]                            # <repo>
NF_DIR = REPO / "terra_universalis" / "common" / "national_focus"
sys.path.insert(0, str(REPO / "tools" / "lint"))
import tu_lint  # noqa: E402  (focus 좌표 계산은 린트와 같은 코드를 쓴다)

ROW_PX = 130
MARGIN_ROWS = 2
CFP_X = 50
TREE_RE = re.compile(r"\s*focus_tree\s*=\s*\{")
TREE_ID_RE = re.compile(r"\s*id\s*=\s*\S+\s*$")
CFP_RE = re.compile(r"\s*continuous_focus_position\s*=")
CFP_Y_RE = re.compile(r"\by\s*=\s*(-?\d+)")


def show(path):
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def target_files():
    files = sorted(NF_DIR.glob("tu_*.txt"))
    generic = NF_DIR / "generic.txt"
    if generic.is_file():
        files.append(generic)
    return files


def scan(lines):
    """줄마다 (줄 시작 깊이, 줄 끝 깊이, 코드 부분)을 돌려준다."""
    rows = []
    depth = 0
    for line in lines:
        code = tu_lint.split_line(line)[1]
        start = depth
        depth += code.count("{") - code.count("}")
        rows.append((start, depth, code))
    return rows


def find_trees(rows):
    """최상위 focus_tree 블록의 (여는 줄, 닫는 줄) 목록."""
    trees = []
    start = None
    for i, (before, after, code) in enumerate(rows):
        if start is None and before == 0 and TREE_RE.match(code):
            start = i
        if start is not None and after == 0:
            trees.append((start, i))
            start = None
    return trees


def plan(path):
    """파일 하나를 검사하고 고친 본문을 만든다. 고칠 것이 없으면 text 는 None."""
    text = path.read_bytes().decode("utf-8")
    lines = text.split("\n")
    rows = scan(lines)
    res = {"name": show(path), "tree": None, "max_y": None, "need": None,
           "found": None, "text": None, "error": None}
    trees = find_trees(rows)
    if len(trees) != 1:
        res["error"] = "focus_tree 블록이 %d개 (1개여야 함)" % len(trees)
        return res
    start, end = trees[0]
    id_idx = next((j for j in range(start + 1, end + 1)
                   if rows[j][0] == 1 and TREE_ID_RE.match(rows[j][2])), None)
    if id_idx is None:
        res["error"] = "focus_tree 의 id 줄을 찾지 못함"
        return res
    res["tree"] = rows[id_idx][2].split("=", 1)[1].strip()

    focuses, _ = tu_lint.parse_focuses(text)
    if not focuses:
        res["error"] = "focus 블록이 없음"
        return res
    by_id = {f["id"]: f for f in focuses}
    ys = []
    for f in focuses:
        xy = tu_lint.resolve_abs(f["id"], by_id)
        if xy is None:
            res["error"] = "relative_position_id 체인이 끊겼거나 순환함: %s" % f["id"]
            return res
        ys.append(xy[1])
    max_y = max(ys)
    want = (max_y + MARGIN_ROWS) * ROW_PX
    res["max_y"] = max_y
    res["need"] = (max_y + 1) * ROW_PX

    cfp = [i for i in range(start + 1, end) if rows[i][0] == 1 and CFP_RE.match(rows[i][2])]
    found = None
    drop = set()
    for first in cfp:
        last = first
        while rows[last][1] > 1:
            last += 1
        drop.update(range(first, last + 1))
        if found is None:
            m = CFP_Y_RE.search(" ".join(rows[k][2] for k in range(first, last + 1)))
            found = int(m.group(1)) if m else None
    res["found"] = found

    indent = re.match(r"\s*", lines[id_idx]).group(0)
    eol = "\r" if lines[id_idx].endswith("\r") else ""
    canonical = "%scontinuous_focus_position = { x = %d y = %d }%s" % (indent, CFP_X, want, eol)
    if cfp:
        new_lines = []
        for idx, line in enumerate(lines):
            if idx == cfp[0]:
                new_lines.append(canonical)
            elif idx not in drop:
                new_lines.append(line)
    else:
        new_lines = lines[:id_idx + 1] + [canonical] + lines[id_idx + 1:]
    new_text = "\n".join(new_lines)
    if new_text != text:
        res["text"] = new_text
    res["y"] = want
    return res


def place_file(path):
    """파일 하나에 continuous_focus_position 을 넣거나 고친다. 오류면 파일을 쓰지 않는다."""
    res = plan(path)
    res["changed"] = False
    if res["error"] is None and res["text"] is not None:
        path.write_bytes(res["text"].encode("utf-8"))
        res["changed"] = True
    res.pop("text", None)
    return res


def check_file(path):
    res = plan(path)
    res.pop("text", None)
    if res["error"] is not None:
        status = "ERROR"
    elif res["found"] is None:
        status = "MISSING"
    elif res["found"] < res["need"]:
        status = "LOW"
    else:
        status = "OK"
    res["status"] = status
    return res


def main(argv=None):
    parser = argparse.ArgumentParser(description="국가 중점 트리에 continuous_focus_position 넣기")
    parser.add_argument("files", nargs="*", help="대상 파일 (기본: tu_*.txt 와 generic.txt)")
    parser.add_argument("--check", action="store_true",
                        help="파일을 쓰지 않고 검사만 한다 (누락 또는 Y 부족이면 exit 1)")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    files = [Path(f).resolve() for f in args.files] if args.files else target_files()
    problems = 0
    for path in files:
        if args.check:
            res = check_file(path)
            if res["status"] != "OK":
                problems += 1
            if res["error"] is not None:
                print(f"ERROR {res['name']}:0 {res['error']}")
            else:
                found = res["found"] if res["found"] is not None else "-"
                print(f"CHECK {res['name']} tree={res['tree']} max_y={res['max_y']} "
                      f"need_y>={res['need']} found={found} -> {res['status']}")
        else:
            res = place_file(path)
            if res["error"] is not None:
                problems += 1
                print(f"ERROR {res['name']}:0 {res['error']}")
            else:
                state = "changed" if res["changed"] else "unchanged"
                print(f"PLACE {res['name']} tree={res['tree']} max_y={res['max_y']} "
                      f"y={res['y']} {state}")
    if args.check:
        print(f"CONTINUOUS_CHECK problems={problems}")
    else:
        print(f"PLACE_CONTINUOUS errors={problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
