#!/usr/bin/env python3
"""Terra Universalis 모드 린트 (표준 라이브러리만 사용, Python 3.10).

사용법:
    python -I tools/lint/tu_lint.py [모드 루트]
    python -I tools/lint/tu_lint.py --selftest

검사:
    A1 중괄호 균형, A2 주석 밖 비ASCII(WARN), A3 UTF-8 디코딩 (스크립트 파일)
    B1 파일명/폴더 언어, B2 UTF-8 BOM, B3 헤더 줄, B4 항목 형식,
    B5 같은 언어 안의 키 중복, B6 korean/english 키 집합 불일치 (localisation)
    C1 common/ideas picture 값에 GFX_ 접두사 금지 (엔진이 GFX_idea_를 붙임)
    C2 common/bop 최상위 id가 어딘가의 set_power_balance에 없음
    C3 national_focus 트리 안의 focus 좌표 중복 또는 같은 y에서 |dx|<2
       (x/y + relative_position_id 체인으로 절대 좌표 계산, offset 블록은 무시하고 개수만 보고)
    C4 common/bop 최상위 블록의 side = { } 마다 icon = <이름> 필수, 이름은 바닐라/모드 interface/*.gfx 의 name 과 대소문자 무시로 일치
    C5 national_focus/*.txt 의 focus 트리마다 continuous_focus_position 의 y 가 (max_y+1)*130 이상 (max_y 는 절대 y 최댓값)
    C6 common/dynamic_modifiers/*.txt 의 최상위 블록마다 icon = GFX_... 줄 필수
    C7 events/*.txt 에 news = yes 줄 금지
"""

import argparse
import re
import sys
import tempfile
from collections import namedtuple
from pathlib import Path

BOM = b"\xef\xbb\xbf"
SCRIPT_DIRS = ("common", "history", "events", "interface", "map")
SCRIPT_EXTS = (".txt", ".gui", ".gfx")
LANGS = ("korean", "english")
LOC_NAME_RE = re.compile(r"(.+)_l_([A-Za-z]+)\.yml")
ENTRY_RE = re.compile(r'^\s+([A-Za-z0-9_.\-]+):\d*\s+"(.*)"\s*(#.*)?$')
VANILLA_DIR = Path(r"G:\SteamLibrary\steamapps\common\Hearts of Iron IV")

Finding = namedtuple("Finding", "level path line msg")


def split_lines(text):
    return [ln.rstrip("\r") for ln in text.split("\n")]


def split_line(line):
    """주석 앞부분(문자열 포함)과, 문자열 내용을 공백으로 지운 코드 부분을 돌려준다."""
    visible = []
    code = []
    in_str = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_str:
            if ch == "\\" and i + 1 < len(line):
                visible.append(line[i:i + 2])
                code.append("  ")
                i += 2
                continue
            visible.append(ch)
            if ch == '"':
                in_str = False
                code.append('"')
            else:
                code.append(" ")
        elif ch == "#":
            break
        else:
            visible.append(ch)
            code.append(ch)
            if ch == '"':
                in_str = True
        i += 1
    return "".join(visible), "".join(code)


def check_script(path, rel_path, out):
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        line_no = raw.count(b"\n", 0, exc.start) + 1
        out.append(Finding("ERROR", rel_path, line_no, "A3 UTF-8로 디코딩되지 않습니다"))
        return
    stack = []
    for no, line in enumerate(split_lines(text), 1):
        visible, code = split_line(line)
        for ch in code:
            if ch == "{":
                stack.append(no)
            elif ch == "}":
                if stack:
                    stack.pop()
                else:
                    out.append(Finding("ERROR", rel_path, no, "A1 짝이 없는 닫는 중괄호 '}'"))
        non_ascii = [c for c in visible if ord(c) > 127]
        if non_ascii:
            c = non_ascii[0]
            out.append(Finding(
                "WARN", rel_path, no,
                "A2 주석 밖 비ASCII 문자 U+%04X %r (스크립트는 ASCII만 사용)" % (ord(c), c)))
    if stack:
        out.append(Finding(
            "ERROR", rel_path, stack[-1],
            "A1 닫히지 않은 여는 중괄호 '{' (파일 끝까지 닫히지 않음)"))


def check_loc(path, root, loc_dir, out, entries):
    rel_path = path.relative_to(root).as_posix()
    loc_rel = path.relative_to(loc_dir).as_posix()
    folder = path.parent.name
    if folder == "replace":          # localisation/<언어>/replace/ : 바닐라 키를 덮어쓰는 파일
        folder = path.parent.parent.name
    file_lang = folder if folder in LANGS else None

    m = LOC_NAME_RE.fullmatch(path.name)
    if file_lang is None or m is None or m.group(2) != folder:
        out.append(Finding(
            "ERROR", rel_path, 1,
            "B1 파일명 _l_<언어>.yml의 언어가 상위 폴더 이름(korean/english)과 일치하지 않음"))

    raw = path.read_bytes()
    if raw.startswith(BOM):
        body = raw[len(BOM):]
    else:
        out.append(Finding("ERROR", rel_path, 1, "B2 UTF-8 BOM(EF BB BF)으로 시작하지 않음"))
        body = raw
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        line_no = body.count(b"\n", 0, exc.start) + 1
        out.append(Finding("ERROR", rel_path, line_no, "B2 UTF-8로 디코딩되지 않음"))
        return
    lines = split_lines(text)

    content_idx = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s and not s.startswith("#"):
            content_idx = i
            break
    if file_lang is not None:
        expected = "l_%s:" % file_lang
        if content_idx is None:
            out.append(Finding("ERROR", rel_path, 1, "B3 헤더 줄 '%s'가 없음" % expected))
        elif lines[content_idx].rstrip() != expected:
            out.append(Finding(
                "ERROR", rel_path, content_idx + 1,
                "B3 첫 내용 줄은 '%s'여야 함 (현재: %s)" % (expected, lines[content_idx].strip())))

    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or s.startswith("#") or i == content_idx:
            continue
        m_entry = ENTRY_RE.match(ln)
        if m_entry is None:
            out.append(Finding("ERROR", rel_path, i + 1, "B4 항목 형식 오류: %s" % s))
            continue
        if file_lang is not None:
            entries[file_lang].append((m_entry.group(1), loc_rel, rel_path, i + 1))


def code_text(text):
    """주석과 문자열 내용을 지운 코드 문자열 (줄 수 유지)."""
    return "\n".join(split_line(ln)[1] for ln in split_lines(text))


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


FOCUS_OPEN_RE = re.compile(r"\bfocus\s*=\s*$")
SET_POWER_RE = re.compile(r"set_power_balance\s*=\s*\{\s*id\s*=\s*([A-Za-z_]\w*)")
GFX_NAME_RE = re.compile(r'\bname\s*=\s*"?([A-Za-z_][\w.\-]*)"?')
SIDE_OPEN_RE = re.compile(r"\s*side\s*=\s*\{")
ICON_RE = re.compile(r'\s*icon\s*=\s*"?([A-Za-z_][\w.\-]*)"?')


def check_idea_pictures(root, out):
    """C1: common/ideas/*.txt 의 picture = GFX_... 금지."""
    for path in sorted((root / "common" / "ideas").glob("*.txt")):
        text = read_text(path)
        if text is None:
            continue
        rel_path = path.relative_to(root).as_posix()
        for no, line in enumerate(split_lines(text), 1):
            visible, _ = split_line(line)
            m = re.match(r'\s*picture\s*=\s*"?([^\s"]+)', visible)
            if m and m.group(1).startswith("GFX_"):
                out.append(Finding(
                    "ERROR", rel_path, no,
                    "C1 idea picture must omit GFX_idea_ prefix (현재: %s)" % m.group(1)))


def check_bop(root, out):
    """C2: common/bop 최상위 id가 set_power_balance 어딘가에 쓰였는지 확인."""
    bop_dir = root / "common" / "bop"
    if not bop_dir.is_dir():
        return
    defined = []
    for path in sorted(bop_dir.glob("*.txt")):
        text = read_text(path)
        if text is None:
            continue
        rel_path = path.relative_to(root).as_posix()
        depth = 0
        for no, line in enumerate(code_text(text).split("\n"), 1):
            if depth == 0:
                m = re.match(r"\s*([A-Za-z_]\w*)\s*=\s*\{", line)
                if m:
                    defined.append((m.group(1), rel_path, no))
            depth += line.count("{") - line.count("}")
    referenced = set()
    for path in root.rglob("*.txt"):
        text = read_text(path)
        if text is not None:
            referenced.update(SET_POWER_RE.findall(code_text(text)))
    for bop_id, rel_path, no in defined:
        if bop_id not in referenced:
            out.append(Finding(
                "ERROR", rel_path, no,
                "C2 BoP id가 어떤 set_power_balance에도 없음: %s" % bop_id))


def load_gfx_names(gfx_roots):
    """interface/*.gfx 의 name = ... 값을 소문자 집합으로 모은다."""
    names = set()
    for base in gfx_roots:
        for path in sorted((base / "interface").rglob("*.gfx")):
            text = read_text(path)
            if text is None:
                continue
            for line in split_lines(text):
                visible, _ = split_line(line)
                for m in GFX_NAME_RE.finditer(visible):
                    names.add(m.group(1).lower())
    return names


def check_bop_icons(root, vanilla_dir, out):
    """C4: common/bop 최상위 블록의 side = { } 마다 icon = <이름> 이 있어야 하고, 이름은 interface/*.gfx 에 정의돼야 한다."""
    bop_dir = root / "common" / "bop"
    if not bop_dir.is_dir():
        return
    sides = []
    for path in sorted(bop_dir.glob("*.txt")):
        text = read_text(path)
        if text is None:
            continue
        rel_path = path.relative_to(root).as_posix()
        depth = 0
        side = None
        for no, line in enumerate(split_lines(text), 1):
            visible, code = split_line(line)
            if side is None and depth == 1 and SIDE_OPEN_RE.match(code):
                side = {"path": rel_path, "line": no, "icon": None}
                sides.append(side)
            elif side is not None and depth == 2 and side["icon"] is None:
                m = ICON_RE.match(visible)
                if m:
                    side["icon"] = m.group(1)
            depth += code.count("{") - code.count("}")
            if side is not None and depth <= 1:
                side = None
    if not sides:
        return
    vanilla_ok = (vanilla_dir / "interface").is_dir()
    if not vanilla_ok:
        out.append(Finding(
            "WARN", "common/bop", 1,
            "C4 바닐라 interface 폴더가 없어 icon 정의 검사를 생략함 (%s)" % vanilla_dir))
    names = load_gfx_names([root, vanilla_dir] if vanilla_ok else [root])
    for side in sides:
        if side["icon"] is None:
            out.append(Finding(
                "ERROR", side["path"], side["line"],
                "C4 side 블록에 icon = <이름> 줄이 없음"))
        elif vanilla_ok and side["icon"].lower() not in names:
            out.append(Finding(
                "ERROR", side["path"], side["line"],
                "C4 side icon이 interface/*.gfx 에 정의되지 않음: %s" % side["icon"]))


def _top_level(body):
    """블록 본문에서 하위 블록 내용을 공백으로 지운 최상위 텍스트 (줄 위치 유지)."""
    chars = []
    depth = 0
    for ch in body:
        if ch == "{":
            depth += 1
            chars.append("{" if depth == 1 else " ")
        elif ch == "}":
            chars.append("}" if depth == 1 else " ")
            depth -= 1
        else:
            chars.append(ch if depth == 0 else " ")
    return "".join(chars)


def parse_focuses(text):
    """focus_tree 안의 focus = { } 블록을 찾는다. 반환: (focus 목록, offset 개수)."""
    code = code_text(text)
    stack = []
    focuses = []
    offset_count = 0
    for idx, ch in enumerate(code):
        if ch == "{":
            is_focus = len(stack) == 1 and FOCUS_OPEN_RE.search(code, max(0, idx - 40), idx)
            stack.append(("focus" if is_focus else "other", idx))
        elif ch == "}" and stack:
            kind, start = stack.pop()
            if kind != "focus":
                continue
            top = _top_level(code[start + 1:idx])
            fid = re.search(r"\bid\s*=\s*([A-Za-z_]\w*)", top)
            if fid is None:
                continue
            x = re.search(r"\bx\s*=\s*(-?\d+)", top)
            y = re.search(r"\by\s*=\s*(-?\d+)", top)
            rel = re.search(r"\brelative_position_id\s*=\s*([A-Za-z_]\w*)", top)
            offset_count += len(re.findall(r"\boffset\s*=\s*\{", top))
            focuses.append({
                "id": fid.group(1),
                "x": int(x.group(1)) if x else 0,
                "y": int(y.group(1)) if y else 0,
                "rel": rel.group(1) if rel else None,
                "line": code.count("\n", 0, start) + 1,
            })
    return focuses, offset_count


def resolve_abs(focus_id, by_id, seen=()):
    """relative_position_id 체인을 따라 절대 (x, y)를 구한다. 실패하면 None."""
    f = by_id.get(focus_id)
    if f is None or focus_id in seen:
        return None
    if f["rel"] is None:
        return (f["x"], f["y"])
    base = resolve_abs(f["rel"], by_id, seen + (focus_id,))
    if base is None:
        return None
    return (base[0] + f["x"], base[1] + f["y"])


def check_focus_tree(path, rel_path, out):
    text = read_text(path)
    if text is None:
        return
    focuses, offset_count = parse_focuses(text)
    if offset_count:
        out.append(Finding(
            "INFO", rel_path, 1,
            "C3 offset 블록 %d개는 무시하고 x/y와 relative_position_id만으로 계산" % offset_count))
    by_id = {}
    for f in focuses:
        if f["id"] in by_id:
            out.append(Finding("ERROR", rel_path, f["line"], "C3 focus id 중복: %s" % f["id"]))
        by_id[f["id"]] = f
    placed = []
    for f in focuses:
        xy = resolve_abs(f["id"], by_id)
        if xy is None:
            out.append(Finding(
                "ERROR", rel_path, f["line"],
                "C3 relative_position_id 체인이 끊겼거나 순환함: %s" % f["id"]))
            continue
        f["abs"] = xy
        placed.append(f)
    seen = set()
    for world in visible_worlds(path, text, placed):
        for fd in _check_xy(world, rel_path):
            key = (fd.line, fd.msg)
            if key not in seen:
                seen.add(key)
                out.append(fd)


def visible_worlds(path, text, placed):
    """한 번에 하나만 보이는 갈래(tools/focusgen/block_layout.py 의 ORDER, 사양서 63)는 겹쳐 있어도 된다.
    겹친 칸이 있으면 '보이는 경우' 마다 (겹친 갈래 하나씩) 따로 검사한다."""
    tag = path.stem[3:].upper() if path.stem.startswith("tu_") else None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "focusgen"))
        import block_layout
    except ImportError:
        return [placed]
    cfg = block_layout.ORDER.get(tag)
    if not cfg:
        return [placed]
    fs = block_layout.parse(text)
    alts = [[block_layout.block_of(h, fs, cfg["root"]) for h in slot] for slot in cfg["slots"] if len(slot) > 1]
    if not alts:
        return [placed]
    hidden_all = set().union(*[m for slot in alts for m in slot])
    worlds = []
    for slot in alts:
        for mem in slot:
            worlds.append([f for f in placed if f["id"] not in hidden_all or f["id"] in mem])
    return worlds


def _check_xy(placed, rel_path):
    out = []
    seen_xy = {}
    for f in placed:
        if f["abs"] in seen_xy:
            other = seen_xy[f["abs"]]
            out.append(Finding(
                "ERROR", rel_path, f["line"],
                "C3 focus 좌표 중복: %s 와 %s (%d, %d)" % (f["id"], other["id"], f["abs"][0], f["abs"][1])))
        else:
            seen_xy[f["abs"]] = f
    by_y = {}
    for f in placed:
        by_y.setdefault(f["abs"][1], []).append(f)
    for y, group in sorted(by_y.items()):
        group.sort(key=lambda g: g["abs"][0])
        for a, b in zip(group, group[1:]):
            dx = b["abs"][0] - a["abs"][0]
            if 0 < dx < 2:
                out.append(Finding(
                    "ERROR", rel_path, b["line"],
                    "C3 같은 y(%d)에서 간격 부족 (dx=%d): %s 와 %s" % (y, dx, a["id"], b["id"])))
    return out


def check_focus_trees(root, out):
    for path in sorted((root / "common" / "national_focus").glob("tu_*.txt")):
        check_focus_tree(path, path.relative_to(root).as_posix(), out)


CONT_RE = re.compile(r"\bcontinuous_focus_position\s*=\s*\{[^{}]*\by\s*=\s*(-?\d+)")
ROW_PX = 130


def check_continuous(root, out):
    """C5: national_focus/*.txt 의 focus 트리마다 continuous_focus_position 의 y >= (max_y+1)*130 (파일당 트리 1개 가정)."""
    for path in sorted((root / "common" / "national_focus").glob("*.txt")):
        text = read_text(path)
        if text is None:
            continue
        rel_path = path.relative_to(root).as_posix()
        focuses, _ = parse_focuses(text)
        by_id = {f["id"]: f for f in focuses}
        ys = [xy[1] for xy in (resolve_abs(f["id"], by_id) for f in focuses) if xy is not None]
        if not ys:
            continue
        need = (max(ys) + 1) * ROW_PX
        code = code_text(text)
        m = CONT_RE.search(code)
        if m is None:
            out.append(Finding(
                "ERROR", rel_path, 1,
                "C5 continuous_focus_position 이 없음 (y >= %d 필요)" % need))
        elif int(m.group(1)) < need:
            out.append(Finding(
                "ERROR", rel_path, code.count("\n", 0, m.start()) + 1,
                "C5 continuous_focus_position y=%s 가 너무 작음 (y >= %d 필요)" % (m.group(1), need)))


DYN_BLOCK_RE = re.compile(r"\s*([A-Za-z_]\w*)\s*=\s*\{")
DYN_ICON_RE = re.compile(r'\s*icon\s*=\s*"?GFX_[\w.\-]*"?')


def check_dynamic_modifier_icons(root, out):
    """C6: common/dynamic_modifiers/*.txt 의 최상위 블록마다 icon = GFX_... 줄이 있어야 한다 (없으면 _small 아이콘 오류)."""
    for path in sorted((root / "common" / "dynamic_modifiers").glob("*.txt")):
        text = read_text(path)
        if text is None:
            continue
        rel_path = path.relative_to(root).as_posix()
        depth = 0
        block = None
        for no, line in enumerate(split_lines(text), 1):
            visible, code = split_line(line)
            if depth == 0:
                m = DYN_BLOCK_RE.match(code)
                if m:
                    block = {"name": m.group(1), "line": no, "icon": False}
            elif block is not None and depth == 1 and DYN_ICON_RE.match(visible):
                block["icon"] = True
            depth += code.count("{") - code.count("}")
            if depth == 0 and block is not None:
                if not block["icon"]:
                    out.append(Finding(
                        "ERROR", rel_path, block["line"],
                        "C6 dynamic modifier 블록에 icon = GFX_... 줄이 없음: %s" % block["name"]))
                block = None


NEWS_YES_RE = re.compile(r"\bnews\s*=\s*yes\b")


def check_news_yes(root, out):
    """C7: events/*.txt 에 news = yes 줄 금지 (뉴스는 news_event 블록으로 작성)."""
    for path in sorted((root / "events").glob("*.txt")):
        text = read_text(path)
        if text is None:
            continue
        rel_path = path.relative_to(root).as_posix()
        for no, line in enumerate(split_lines(text), 1):
            _, code = split_line(line)
            if NEWS_YES_RE.search(code):
                out.append(Finding(
                    "ERROR", rel_path, no,
                    "C7 news = yes 줄은 허용되지 않음 (뉴스는 news_event 블록으로 작성)"))


def check_cross(entries, out):
    firsts = {}
    for lang in LANGS:
        seen = {}
        for key, loc_rel, rel_path, line in entries[lang]:
            if key in seen:
                first = seen[key]
                out.append(Finding(
                    "ERROR", rel_path, line,
                    "B5 같은 언어 안에서 키 중복: %s (처음 위치: %s:%d)" % (key, first[0], first[2])))
            else:
                seen[key] = (loc_rel, rel_path, line)
        firsts[lang] = seen
    for lang, other in (("korean", "english"), ("english", "korean")):
        for key, (loc_rel, rel_path, line) in firsts[lang].items():
            if key not in firsts[other]:
                out.append(Finding(
                    "ERROR", rel_path, line,
                    "B6 missing in %s: %s (%s:%d)" % (other, key, loc_rel, line)))


def run_lint(root, vanilla_dir=VANILLA_DIR):
    root = Path(root).resolve()
    out = []
    for sub in SCRIPT_DIRS:
        base = root / sub
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in SCRIPT_EXTS:
                check_script(path, path.relative_to(root).as_posix(), out)
    check_idea_pictures(root, out)
    check_bop(root, out)
    check_bop_icons(root, vanilla_dir, out)
    check_focus_trees(root, out)
    check_continuous(root, out)
    check_dynamic_modifier_icons(root, out)
    check_news_yes(root, out)
    loc_dir = root / "localisation"
    entries = {lang: [] for lang in LANGS}
    if loc_dir.is_dir():
        for path in sorted(loc_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() == ".yml":
                check_loc(path, root, loc_dir, out, entries)
    check_cross(entries, out)
    return out


def report(findings):
    errors = sum(1 for f in findings if f.level == "ERROR")
    warnings = sum(1 for f in findings if f.level == "WARN")
    for f in findings:
        print(f"{f.level} {f.path}:{f.line} {f.msg}")
    print(f"TU_LINT errors={errors} warnings={warnings}")
    return errors


BASE_KO = """l_korean:
 TU_mod_name:0 "테라 유니버설리스"
 TU_mod_desc:0 "명일방주의 대륙 테라를 무대로 한 총변환 모드입니다."
 TU_currency_lmd:0 "용문폐"
 TU_currency_lmd_short:0 "LMD"
"""

BASE_EN = """l_english:
 TU_mod_name:0 "Terra Universalis"
 TU_mod_desc:0 "A total conversion set on Terra, the continent of Arknights."
 TU_currency_lmd:0 "Lungmen Dollar"
 TU_currency_lmd_short:0 "LMD"
"""

BASE_SCRIPT = """# 테스트 스크립트 (주석 안의 { 는 무시한다)
TU_test_block = {
	key = "string with { brace"
	nested = {
		flag = yes
	}
}
"""


VANILLA_TEST_GFX = 'spriteTypes = {\n\tspriteType = {\n\t\tname = "GFX_bop_selftest_vanilla_side"\n\t}\n}\n'


def _base_files():
    return {
        "localisation/korean/tu_core_l_korean.yml": BOM + BASE_KO.encode("utf-8"),
        "localisation/english/tu_core_l_english.yml": BOM + BASE_EN.encode("utf-8"),
        "common/tu_test.txt": BASE_SCRIPT.encode("utf-8"),
        "interface/tu_mod_test.gfx": 'spriteTypes = {\n\tspriteType = {\n\t\tname = "GFX_bop_selftest_mod_side"\n\t}\n}\n',
        "common/tu_test_ref.txt": "set_power_balance = { id = TU_TEST_OK_bop set_default = yes }\n",
        "common/bop/tu_test_ok_bop.txt":
            "TU_TEST_OK_bop = {\n\tside = {\n\t\tid = TU_TEST_OK_a\n\t\ticon = gfx_bop_selftest_vanilla_side\n\t}\n"
            "\tside = {\n\t\tid = TU_TEST_OK_b\n\t\ticon = GFX_bop_selftest_mod_side\n\t}\n}\n",
    }


def _selftest_cases():
    ko = BASE_KO
    en = BASE_EN
    return [
        ("A1 닫는 괄호 과다",
         {"common/tu_test.txt": "TU_test_block = {\n\tvalue = 1\n}\n}\n"}, "A1", "ERROR"),
        ("A1 미닫힘",
         {"common/tu_test.txt": "TU_test_block = {\n\tvalue = 1\n"}, "A1", "ERROR"),
        ("A2 주석 밖 비ASCII",
         {"common/tu_test.txt": 'TU_test_block = {\n\tkey = "가"\n}\n'}, "A2", "WARN"),
        ("A3 UTF-8 아님",
         {"events/tu_bad_encoding.txt": b"\xff\xfe\xfd\n"}, "A3", "ERROR"),
        ("B1 파일명 언어 불일치",
         {"localisation/korean/tu_probe_l_english.yml":
          BOM + 'l_korean:\n TU_probe:0 "x"\n'.encode("utf-8")}, "B1", "ERROR"),
        ("B2 BOM 없음",
         {"localisation/english/tu_core_l_english.yml": en.encode("utf-8")}, "B2", "ERROR"),
        ("B3 헤더 오류",
         {"localisation/korean/tu_core_l_korean.yml":
          BOM + ko.replace("l_korean:", "l_english:", 1).encode("utf-8")}, "B3", "ERROR"),
        ("B4 따옴표 누락",
         {"localisation/korean/tu_core_l_korean.yml":
          BOM + ko.replace('"용문폐"', '"용문폐').encode("utf-8")}, "B4", "ERROR"),
        ("B5 키 중복",
         {"localisation/korean/tu_core_l_korean.yml":
          BOM + (ko + ' TU_mod_name:0 "중복"\n').encode("utf-8")}, "B5", "ERROR"),
        ("B6 영어 누락",
         {"localisation/korean/tu_core_l_korean.yml":
          BOM + (ko + ' TU_extra_only_ko:0 "추가"\n').encode("utf-8")}, "B6", "ERROR"),
        ("C1 idea picture에 GFX_ 접두사",
         {"common/ideas/tu_test_ideas.txt":
          "TU_test_idea = {\n\tpicture = GFX_idea_generic_research_bonus\n}\n"}, "C1", "ERROR"),
        ("C2 BoP id를 set_power_balance가 쓰지 않음",
         {"common/bop/tu_test_bop.txt": "TU_TEST_bop = {\n\tinitial_value = 0.0\n}\n"}, "C2", "ERROR"),
        ("C3 focus 좌표 중복 (relative 체인 포함)",
         {"common/national_focus/tu_test_focus.txt":
          "focus_tree = {\n\tid = TU_TEST_focus\n\tfocus = {\n\t\tid = TU_TEST_a\n\t\tx = 0\n\t\ty = 0\n\t}\n"
          "\tfocus = {\n\t\tid = TU_TEST_b\n\t\trelative_position_id = TU_TEST_a\n\t\tx = 0\n\t\ty = 0\n\t}\n}\n"},
         "C3", "ERROR"),
        ("C3 같은 y에서 간격 부족",
         {"common/national_focus/tu_test_focus.txt":
          "focus_tree = {\n\tid = TU_TEST_focus\n\tfocus = {\n\t\tid = TU_TEST_a\n\t\tx = 0\n\t\ty = 0\n\t}\n"
          "\tfocus = {\n\t\tid = TU_TEST_b\n\t\trelative_position_id = TU_TEST_a\n\t\tx = 1\n\t\ty = 0\n\t}\n}\n"},
         "C3", "ERROR"),
        ("C4 side에 icon 줄 없음",
         {"common/bop/tu_test_bop.txt": "TU_TEST_bop = {\n\tside = {\n\t\tid = TU_TEST_a\n\t}\n}\n"},
         "C4", "ERROR"),
        ("C4 icon이 gfx에 정의되지 않음",
         {"common/bop/tu_test_bop.txt":
          "TU_TEST_bop = {\n\tside = {\n\t\tid = TU_TEST_a\n\t\ticon = GFX_bop_selftest_missing_side\n\t}\n}\n"},
         "C4", "ERROR"),
        ("C5 continuous_focus_position 없음",
         {"common/national_focus/tu_test_focus.txt":
          "focus_tree = {\n\tid = TU_TEST_focus\n\tfocus = {\n\t\tid = TU_TEST_a\n\t\tx = 0\n\t\ty = 0\n\t}\n}\n"},
         "C5", "ERROR"),
        ("C5 continuous_focus_position y 부족",
         {"common/national_focus/tu_test_focus.txt":
          "focus_tree = {\n\tid = TU_TEST_focus\n\tcontinuous_focus_position = { x = 50 y = 129 }\n"
          "\tfocus = {\n\t\tid = TU_TEST_a\n\t\tx = 0\n\t\ty = 0\n\t}\n}\n"},
         "C5", "ERROR"),
        ("C6 dynamic modifier에 icon 없음",
         {"common/dynamic_modifiers/tu_test_modifier.txt":
          "TU_test_modifier = {\n\tenable = { always = yes }\n\tarmy_morale_factor = 0.1\n}\n"},
         "C6", "ERROR"),
        ("C6 icon이 GFX_ 접두사 아님",
         {"common/dynamic_modifiers/tu_test_modifier.txt":
          "TU_test_modifier = {\n\ticon = generic_military_plans\n\tarmy_morale_factor = 0.1\n}\n"},
         "C6", "ERROR"),
        ("C7 events에 news = yes",
         {"events/tu_test_events.txt":
          "news_event = {\n\tid = TU_test.1\n\tnews = yes\n\tis_triggered_only = yes\n}\n"},
         "C7", "ERROR"),
    ]


def _materialize(root, files):
    for rel, data in files.items():
        if data is None:
            continue
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            data = data.encode("utf-8")
        target.write_bytes(data)


def selftest():
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "mod"
        vanilla = Path(tmp) / "vanilla"
        _materialize(root, _base_files())
        _materialize(vanilla, {"interface/tu_vanilla_test.gfx": VANILLA_TEST_GFX})
        findings = run_lint(root, vanilla)
        if findings:
            failures.append(("정상 모드", findings))
    for name, changes, code, level in _selftest_cases():
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "mod"
            vanilla = Path(tmp) / "vanilla"
            files = _base_files()
            files.update(changes)
            _materialize(root, files)
            _materialize(vanilla, {"interface/tu_vanilla_test.gfx": VANILLA_TEST_GFX})
            findings = run_lint(root, vanilla)
            hit = any(f.level == level and f.msg.split(" ", 1)[0] == code for f in findings)
            if not hit:
                failures.append((name, findings))
    if failures:
        for name, findings in failures:
            print(f"SELFTEST FAIL {name}")
            for f in findings:
                print(f"  {f.level} {f.path}:{f.line} {f.msg}")
        return 1
    print("SELFTEST ok")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Terra Universalis 모드 린트")
    parser.add_argument("root", nargs="?",
                        help="모드 루트 (기본: 스크립트 기준 ../../terra_universalis)")
    parser.add_argument("--selftest", action="store_true", help="린트 자체 검증 실행")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.selftest:
        return selftest()

    default_root = Path(__file__).resolve().parent.parent.parent / "terra_universalis"
    root = Path(args.root).resolve() if args.root else default_root
    if not root.is_dir():
        print(f"ERROR {root}:0 모드 루트 폴더가 없습니다")
        print("TU_LINT errors=1 warnings=0")
        return 1
    errors = report(run_lint(root))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
