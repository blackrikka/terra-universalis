#!/usr/bin/env python3
"""국가 중점 트리 조각 합치기 (표준 라이브러리만 사용, Python 3.10).

사용법:
    python -I tools/focusgen/merge_focus.py --tag <TAG>                 # 전체 검사 후 tu_<tag>.txt 생성
    python -I tools/focusgen/merge_focus.py --tag <TAG> --check <part>  # <part> 조각만 검사 (파일을 쓰지 않음)

태그 폴더: tools/focusgen/<태그 소문자>/ (머리말 _header.txt + 조각 *.txt). 예: --tag VIC -> tools/focusgen/vic/
합치기: _header.txt(머리말) + 조각 파일(파일명 순) + 닫는 괄호
        -> terra_universalis/common/national_focus/tu_<태그 소문자>.txt
        -> autolayout.py 로 x/y 자동 배치 -> place_continuous (continuous_focus_position)

검사 (합치기와 --check 공통):
    F0 조각 파일 또는 머리말이 없음 (URS: PART_BANDS 에 없는 조각도)
    F1 중괄호 균형 (조각과 머리말)
    F2 ASCII 전용 (조각과 머리말)
    F3 최상위 focus = { } 블록 파싱, id 필수
    F4 중점 id 중복 (태그의 모든 조각 대상)
    F5 URS 전용: 절대 좌표만 사용 (x, y 필수, relative_position_id 금지)
    F6 URS 전용: x 가 해당 part 의 PART_BANDS 범위 안
    F7 URS 전용: 같은 조각 안의 좌표 충돌 (같은 y 에서 |dx| < 2)
    F8 prerequisite / mutually_exclusive 가 가리키는 id 가 태그의 조각 어딘가에 존재
    F9 모든 중점에 한·영 로컬라이제이션 키 <id>, <id>_desc 존재
       (localisation/korean/*.yml, localisation/english/*.yml 전체에서 찾는다)
    F10 has_completed_focus 가 TU_<TAG>_ 접두사 중점을 가리키면 그 중점이 태그의 조각 어딘가에 존재

좌표 밴드 검사(F5~F7)는 TAG_PART_BANDS 에 있는 태그(URS)만 한다.
다른 태그는 자동 배치(autolayout)가 좌표를 다시 놓으므로 좌표를 검사하지 않는다.
"""

import argparse
import re
import sys
from collections import namedtuple
from pathlib import Path

HERE = Path(__file__).resolve().parent            # <repo>/tools/focusgen
REPO = HERE.parents[1]                            # <repo>
MOD_ROOT = REPO / "terra_universalis"
NF_DIR = MOD_ROOT / "common" / "national_focus"
LOC_ROOT = MOD_ROOT / "localisation"
LOC_LANGS = ("korean", "english")
HEADER_NAME = "_header.txt"

# 조각(part)별 x 배정 범위 (양 끝 포함). 뿌리(p0_roots)는 각 뿌리가 자기 갈래 범위 안에 있으면 된다.
PART_BANDS = {
    "p0_roots": [(0, 14), (16, 26), (28, 34), (36, 44), (76, 90), (152, 168)],
    "p1_emperor": [(46, 74)],
    "p2_junta": [(76, 90)],
    "p3_nobles": [(92, 112)],
    "p4_reform": [(114, 130)],
    "w1_west": [(132, 150)],
    "w2_south": [(152, 168)],
    "w3_east": [(170, 186)],
    "w4_world": [(188, 200)],
    "e1_industry": [(0, 14)],
    "e2_army": [(16, 26)],
    "e3_air_research": [(28, 34)],
    "e4_chernobog": [(36, 44)],
    "p9_hidden": [(202, 240)],      # hidden_routes.py (사양서 30)
}

# 좌표 밴드 검사를 하는 태그. 여기 없는 태그는 F5~F7 을 하지 않는다.
TAG_PART_BANDS = {
    "URS": PART_BANDS,
}

FOCUS_START_RE = re.compile(r"\bfocus\s*=\s*$")
FOCUS_OPEN_RE = re.compile(r"\bfocus\s*=\s*\{")
REF_BLOCK_RE = re.compile(r"\b(prerequisite|mutually_exclusive)\s*=\s*\{([^{}]*)\}")
REF_ID_RE = re.compile(r"\bfocus\s*=\s*([A-Za-z_]\w*)")
DONE_RE = re.compile(r"\bhas_completed_focus\s*=\s*([A-Za-z_]\w*)")
LOC_KEY_RE = re.compile(r'^\s+([A-Za-z0-9_.\-]+):\d*\s+"')

Finding = namedtuple("Finding", "path line msg")


def show(path):
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def strip_code(text):
    """문자열과 # 주석을 공백으로 지운다. 글자 수와 줄 위치는 그대로 유지한다."""
    out = []
    in_str = False
    in_comment = False
    for ch in text:
        if in_comment:
            if ch == "\n":
                in_comment = False
                out.append(ch)
            else:
                out.append(" ")
        elif in_str:
            if ch == "\n" or ch == '"':
                in_str = False
                out.append(ch)
            else:
                out.append(" ")
        elif ch == "#":
            in_comment = True
            out.append(" ")
        elif ch == '"':
            in_str = True
            out.append(ch)
        else:
            out.append(ch)
    return "".join(out)


def brace_balance(code):
    """(끝 깊이, 중간에 음수로 떨어졌는지)."""
    depth = 0
    for ch in code:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return depth, True
    return depth, False


def find_focus_blocks(code, base_depth=0):
    """base_depth 깊이의 focus = { ... } 블록 (여는 중괄호 위치, 닫는 중괄호 위치) 목록.
    조각 파일은 깊이 0, 합친 결과(focus_tree 안)는 깊이 1 이다."""
    blocks = []
    depth = 0
    open_at = None
    for idx, ch in enumerate(code):
        if ch == "{":
            if depth == base_depth and FOCUS_START_RE.search(code[max(0, idx - 30):idx]):
                open_at = idx
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == base_depth and open_at is not None:
                blocks.append((open_at, idx))
                open_at = None
    return blocks


def top_level_text(body):
    """블록 본문에서 하위 블록 안의 글자를 공백으로 지운다 (하위 블록의 중괄호는 남긴다)."""
    chars = []
    depth = 0
    for ch in body:
        if ch == "{":
            chars.append("{" if depth == 0 else " ")
            depth += 1
        elif ch == "}":
            depth -= 1
            chars.append("}" if depth == 0 else " ")
        else:
            chars.append(ch if depth == 0 else " ")
    return "".join(chars)


def trim_blank_lines(text):
    lines = text.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(line.rstrip() for line in lines)


def check_ascii(text, path, out):
    for line_no, line in enumerate(text.split("\n"), 1):
        if any(ord(ch) > 127 for ch in line):
            out.append(Finding(show(path), line_no, "F2 ASCII가 아닌 문자가 있습니다"))
            return


def parse_piece(name, path, text, out):
    """조각 하나를 파싱해 focus 목록을 돌려준다."""
    code = strip_code(text)
    depth, negative = brace_balance(code)
    if negative or depth != 0:
        out.append(Finding(show(path), 1, f"F1 중괄호 균형이 맞지 않습니다 (끝 깊이 {depth})"))
    focuses = []
    for open_at, close_at in find_focus_blocks(code):
        line = code.count("\n", 0, open_at) + 1
        body = code[open_at + 1:close_at]
        top = top_level_text(body)
        fid = re.search(r"\bid\s*=\s*([A-Za-z_]\w*)", top)
        if fid is None:
            out.append(Finding(show(path), line, "F3 focus 블록에 id가 없습니다"))
            continue
        x = re.search(r"\bx\s*=\s*(-?\d+)", top)
        y = re.search(r"\by\s*=\s*(-?\d+)", top)
        refs = []
        for m in REF_BLOCK_RE.finditer(body):
            for target in REF_ID_RE.findall(m.group(2)):
                refs.append((m.group(1), target))
        focuses.append({
            "part": name,
            "id": fid.group(1),
            "x": int(x.group(1)) if x else None,
            "y": int(y.group(1)) if y else None,
            "rel": re.search(r"\brelative_position_id\s*=", top) is not None,
            "line": line,
            "refs": refs,
            "done": DONE_RE.findall(body),
        })
    return focuses


def load_parts(folder, out):
    """태그 폴더의 조각 파일을 모두 읽는다 (머리말 제외, 파일명 순)."""
    parts = []
    for path in sorted(folder.glob("*.txt")):
        if path.name == HEADER_NAME:
            continue
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8").replace("\r\n", "\n")
        except UnicodeDecodeError as exc:
            line = raw.count(b"\n", 0, exc.start) + 1
            out.append(Finding(show(path), line, "F2 UTF-8로 디코딩되지 않습니다"))
            continue
        check_ascii(text, path, out)
        focuses = parse_piece(path.stem, path, text, out)
        parts.append({"name": path.stem, "path": path, "text": text, "focuses": focuses})
    return parts


def load_header(header_path, out):
    """머리말을 읽어 검사한다. 머리말은 focus_tree 를 열고 닫는 괄호는 합치기에서 붙인다."""
    if not header_path.is_file():
        out.append(Finding(show(header_path), 0, "F0 머리말 파일이 없습니다"))
        return None
    text = header_path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    check_ascii(text, header_path, out)
    code = strip_code(text)
    depth, negative = brace_balance(code)
    if negative or depth != 1 or "focus_tree = {" not in code:
        out.append(Finding(show(header_path), 1, f"F1 머리말은 focus_tree 를 열고 닫지 않은 상태여야 합니다 (끝 깊이 {depth})"))
    if FOCUS_OPEN_RE.search(code):
        out.append(Finding(show(header_path), 1, "F3 머리말에 focus = { } 블록이 있으면 안 됩니다"))
    return text


def load_loc_keys(out):
    """localisation/korean, localisation/english 의 *.yml 에서 키를 모은다."""
    keys = {}
    for lang in LOC_LANGS:
        folder = LOC_ROOT / lang
        found = set()
        if not folder.is_dir():
            out.append(Finding(show(folder), 0, "F9 로컬라이제이션 폴더가 없습니다"))
        else:
            for path in sorted(folder.glob("*.yml")):
                text = path.read_bytes().decode("utf-8-sig", errors="replace")
                for line in text.split("\n"):
                    m = LOC_KEY_RE.match(line)
                    if m:
                        found.add(m.group(1))
        keys[lang] = found
    return keys


def check_part_rules(part, loc_keys, bands_map, out):
    """조각 하나의 규칙 (F5, F6, F7 은 좌표 밴드가 있는 태그만, F9 는 항상)."""
    name = part["name"]
    p = show(part["path"])
    bands = None
    if bands_map is not None:
        bands = bands_map.get(name)
        if bands is None:
            out.append(Finding(p, 1, f"F0 PART_BANDS 에 없는 조각입니다: {name}"))
            return
    band_text = ", ".join(f"{lo}~{hi}" for lo, hi in bands) if bands else ""
    by_y = {}
    for f in part["focuses"]:
        if bands is not None:
            if f["rel"]:
                out.append(Finding(p, f["line"], f"F5 relative_position_id 는 쓰지 않습니다: {f['id']}"))
            if f["x"] is None or f["y"] is None:
                out.append(Finding(p, f["line"], f"F5 x, y 가 모두 필요합니다: {f['id']}"))
            else:
                if not any(lo <= f["x"] <= hi for lo, hi in bands):
                    out.append(Finding(p, f["line"], f"F6 x={f['x']} 가 배정 범위({band_text}) 밖입니다: {f['id']}"))
                by_y.setdefault(f["y"], []).append(f)
        for suffix in ("", "_desc"):
            for lang in LOC_LANGS:
                key = f["id"] + suffix
                if key not in loc_keys[lang]:
                    out.append(Finding(p, f["line"], f"F9 {lang} 로컬라이제이션 키가 없습니다: {key}"))
    for y, group in sorted(by_y.items()):
        group.sort(key=lambda g: g["x"])
        for a, b in zip(group, group[1:]):
            dx = b["x"] - a["x"]
            if dx < 2:
                out.append(Finding(p, b["line"], f"F7 같은 y({y})에서 간격 부족 (dx={dx}): {a['id']} 와 {b['id']}"))


def run_checks(parts, targets, bands_map, tag, loc_keys, out):
    """F4, F8, F10 은 모든 조각 대상, 나머지 조각 규칙은 targets 에 든 조각만 검사한다."""
    seen = {}
    for part in parts:
        for f in part["focuses"]:
            if f["id"] in seen:
                prev = seen[f["id"]]
                out.append(Finding(show(part["path"]), f["line"],
                                   f"F4 중점 id 중복: {f['id']} (처음: {prev['part']}:{prev['line']})"))
            else:
                seen[f["id"]] = f
    prefix = f"TU_{tag}_"
    for part in parts:
        for f in part["focuses"]:
            for kind, target in f["refs"]:
                if target not in seen:
                    out.append(Finding(show(part["path"]), f["line"],
                                       f"F8 {kind} 가 가리키는 중점이 없습니다: {target} (대상: {f['id']})"))
            for target in f["done"]:
                if target.startswith(prefix) and target not in seen:
                    out.append(Finding(show(part["path"]), f["line"],
                                       f"F10 has_completed_focus 가 가리키는 중점이 없습니다: {target} (대상: {f['id']})"))
    for part in parts:
        if part["name"] in targets:
            check_part_rules(part, loc_keys, bands_map, out)


def report(findings):
    for f in findings:
        print(f"ERROR {f.path}:{f.line} {f.msg}")
    return len(findings)


def build_text(header_text, parts):
    body = "\n\n".join(trim_blank_lines(p["text"]) for p in parts)
    return trim_blank_lines(header_text) + "\n\n" + body + "\n}\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="국가 중점 트리 조각 합치기")
    parser.add_argument("--tag", required=True,
                        help="국가 태그 (예: VIC, URS). 조각 폴더는 tools/focusgen/<태그 소문자>/")
    parser.add_argument("--check", metavar="PART",
                        help="이 조각만 검사한다 (파일을 쓰지 않음). 예: p1_politics")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tag = args.tag.upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]*", tag):
        parser.error(f"태그가 올바르지 않습니다: {args.tag}")
    folder = HERE / tag.lower()
    header_path = folder / HEADER_NAME
    out_path = NF_DIR / f"tu_{tag.lower()}.txt"
    bands_map = TAG_PART_BANDS.get(tag)
    label = f"MERGE_{tag}"

    if not folder.is_dir():
        print(f"ERROR {show(folder)}:0 조각 폴더가 없습니다")
        print(f"{label} errors=1")
        return 1

    out = []
    parts = load_parts(folder, out)
    loc_keys = load_loc_keys(out)

    if args.check:
        name = args.check[:-4] if args.check.endswith(".txt") else args.check
        targets = {name}
        if not any(p["name"] == name for p in parts):
            out.append(Finding(show(folder / (name + ".txt")), 0, "F0 조각 파일이 없습니다"))
        run_checks(parts, targets, bands_map, tag, loc_keys, out)
        errors = report(out)
        for p in parts:
            if p["name"] == name:
                print(f"PART {name}: {len(p['focuses'])} focuses")
        if errors:
            print(f"CHECK errors={errors}")
            return 1
        print("CHECK ok")
        return 0

    header_text = load_header(header_path, out)
    if not parts:
        out.append(Finding(show(folder), 0, "F0 조각 파일이 없습니다"))
    targets = {p["name"] for p in parts}
    run_checks(parts, targets, bands_map, tag, loc_keys, out)
    if out:
        errors = report(out)
        print(f"{label} errors={errors}")
        return 1

    text = build_text(header_text, parts)
    depth, negative = brace_balance(strip_code(text))
    total_blocks = len(find_focus_blocks(strip_code(text), base_depth=1))
    total = sum(len(p["focuses"]) for p in parts)
    if depth != 0 or negative or total_blocks != total:
        print(f"ERROR {show(out_path)}:0 합친 결과 검사 실패 (깊이 {depth}, 블록 {total_blocks}, 중점 {total})")
        print(f"{label} errors=1")
        return 1

    print("조각별 중점 수:")
    for p in parts:
        print(f"  {p['name']}: {len(p['focuses'])}")
    print(f"총 중점 수: {total} (조각 {len(parts)}개)")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(text)
    print(f"wrote {show(out_path)}")
    sys.path.insert(0, str(HERE))
    import focus_hooks      # 사양서 23: 결말 지도자 교체 · 국호 변경
    hooked, missing = focus_hooks.apply(out_path, tag)
    sys.path.insert(0, str(REPO / "tools"))
    import ruling_party  # 지도자 교체 = 집권당 교체 (사양서 42)
    ruling_party.fix_file(out_path)
    if hooked or missing:
        print(f"focus hooks: {hooked}" + (f", missing focus {missing}" if missing else ""))
    import autolayout
    try:
        changed, stats = autolayout.layout_path(out_path, write=True)
    except autolayout.TuError as exc:
        print(f"ERROR {show(out_path)}:{exc.line} 자동 배치 실패: {exc.msg}")
        print(f"{label} errors=1")
        return 1
    autolayout.describe(out_path, stats, changed, write=True)
    import place_continuous
    placed = place_continuous.place_file(out_path)
    if placed["error"] is not None:
        print(f"ERROR {show(out_path)}:0 continuous_focus_position 넣기 실패: {placed['error']}")
        print(f"{label} errors=1")
        return 1
    print(f"continuous_focus_position y={placed['y']} ({'changed' if placed['changed'] else 'unchanged'})")
    print(f"{label} ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
