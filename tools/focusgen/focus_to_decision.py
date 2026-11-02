#!/usr/bin/env python3
"""국가 중점(focus)을 디시전(decision)으로 전환한다 (표준 라이브러리만 사용, Python 3.10).

사용법:
    python -I tools/focusgen/focus_to_decision.py --dry-run         # 전환 목록과 제외 목록만 출력 (파일을 쓰지 않음)
    python -I tools/focusgen/focus_to_decision.py --show <focus_id>  # 그 중점이 만들 디시전 블록만 출력 (파일을 쓰지 않음)
    python -I tools/focusgen/focus_to_decision.py                   # 고칠 파일을 docs/_backup/focus_to_decision/ 에 복사한 뒤 실제 전환

대상 (URS RHO KZD YAN LGM VIC REU):
    우르수스: tools/focusgen/urs/*.txt 조각을 고친다 (이후 merge_urs.py 를 따로 실행).
    그 밖: terra_universalis/common/national_focus/tu_<tag>.txt 를 직접 고친다.
    tu_urs.txt 는 merge_urs.py 가 만드는 파일이므로 건드리지 않는다.
    전환된 중점 id 가 디시전 id 가 된다 (로컬라이제이션 키 <id>, <id>_desc 를 그대로 쓴다).

분류 (completion_reward 안의 키, 위에서부터 첫 번째로 맞는 규칙):
    1 정치·정체성 유지, 2 국민정신 유지, 3 create_wargoal / 4 add_state_claim -> 확장,
    5 외교 키 -> 외교, 6 create_unit / add_equipment_to_stockpile -> 건설, 7 건설 키 -> 건설, 8 그 밖 유지.
    제외: 뿌리(prerequisite 없음), 정치 선택 4개, 다른 국가 파일이 참조하는 중점.

출력:
    terra_universalis/common/decisions/tu_<tag>_converted_decisions.txt
    terra_universalis/common/decisions/categories/tu_converted_categories.txt
    terra_universalis/localisation/{korean,english}/tu_converted_l_{korean,english}.yml

멱등성: 전환할 중점이 없으면 아무것도 쓰지 않는다 (이미 전환된 상태).
"""

import argparse
import re
import shutil
import sys
from collections import Counter
from types import SimpleNamespace
from pathlib import Path

HERE = Path(__file__).resolve().parent            # <repo>/tools/focusgen
REPO = HERE.parents[1]                            # <repo>
MOD_ROOT = REPO / "terra_universalis"
NF_DIR = MOD_ROOT / "common" / "national_focus"
URS_TREE_PATH = NF_DIR / "tu_urs.txt"             # merge_urs.py 가 만든다
URS_DIR = HERE / "urs"
DEC_DIR = MOD_ROOT / "common" / "decisions"
CAT_PATH = DEC_DIR / "categories" / "tu_converted_categories.txt"
LOC_ROOT = MOD_ROOT / "localisation"
BACKUP_DIR = REPO / "docs" / "_backup" / "focus_to_decision"
SCAN_DIRS = ("common", "events", "history")

NATIONS = ("URS", "RHO", "KZD", "YAN", "LGM", "VIC", "REU")
SPEC_ESTIMATE = {"URS": 137, "RHO": 2, "KZD": 2, "YAN": 4, "LGM": 1, "VIC": 1, "REU": 2}
POLITICAL_CHOICES = frozenset({"TU_URS_emperor_rule", "TU_URS_military_junta",
                               "TU_URS_noble_compromise", "TU_URS_reform_path"})

# (규칙 번호, 키 집합, 분류) -- 위에서부터 첫 번째로 맞는 것을 쓴다
RULES = (
    (1, frozenset({"set_politics", "promote_character", "recruit_character", "create_faction",
                   "set_autonomy", "end_puppet", "annex_country"}), "keep"),
    (2, frozenset({"add_ideas", "swap_ideas", "remove_ideas"}), "keep"),
    (3, frozenset({"create_wargoal"}), "expansion"),
    (4, frozenset({"add_state_claim"}), "expansion"),
    (5, frozenset({"diplomatic_relation", "give_guarantee", "add_opinion_modifier"}), "diplomacy"),
    (6, frozenset({"create_unit", "add_equipment_to_stockpile"}), "construction"),
    (7, frozenset({"add_building_construction", "add_offsite_building",
                   "add_extra_state_shared_building_slots", "add_resource"}), "construction"),
)
# 분류 -> (카테고리 접미사, 바닐라 카테고리 아이콘, 한국어, 영어)
CATEGORY_INFO = {
    "expansion": ("expansion", "GFX_decision_category_military_operation", "제국 확장", "Expansion"),
    "diplomacy": ("diplomacy", "GFX_decision_category_generic_foreign_policy", "외교", "Diplomacy"),
    "construction": ("construction", "GFX_decision_category_generic_industry", "건설·동원",
                     "Construction & Mobilisation"),
}
CATEGORY_ORDER = ("expansion", "diplomacy", "construction")
# 규칙 번호 -> 바닐라 디시전 아이콘
RULE_ICON = {
    3: "GFX_decision_generic_military",
    4: "GFX_decision_generic_military",
    5: "GFX_decision_generic_political_discourse",
    6: "GFX_decision_generic_military",
    7: "GFX_decision_generic_construction",
}
COST_TABLE = {5: 25, 10: 50, 15: 75}
FOCUS_ONLY_KEYS = frozenset({"unlock_national_focus", "complete_national_focus",
                             "remove_national_focus", "set_focus", "activate_focus"})


class ParseError(Exception):
    pass


def show(path):
    try:
        return Path(path).resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


# ---------------------------------------------------------------- 토큰화와 파싱

def tokenize(text, rel):
    """토큰: (종류, 값, 시작, 끝). 종류는 word, str, {, }, =. 주석(#)은 버린다."""
    toks = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "#":
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif c == '"':
            j = text.find('"', i + 1)
            nl = text.find("\n", i + 1)
            if j < 0 or (0 <= nl < j):
                raise ParseError(f"{rel}: 닫히지 않은 문자열 (위치 {i})")
            toks.append(("str", text[i:j + 1], i, j + 1))
            i = j + 1
        elif c in "{}=":
            toks.append((c, c, i, i + 1))
            i += 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n{}=#\"":
                j += 1
            toks.append(("word", text[i:j], i, j))
            i = j
    return toks


class Node:
    def __init__(self, kind, start, end, open_=None, close=None, entries=None, text=None):
        self.kind = kind          # block | scalar
        self.start = start
        self.end = end            # 값의 끝 (닫는 중괄호 뒤)
        self.open = open_         # '{' 위치
        self.close = close        # '}' 위치
        self.entries = entries
        self.text = text


class Entry:
    def __init__(self, key, value, start, end):
        self.key = key            # None 이면 키 없는 값
        self.value = value
        self.start = start        # 키의 시작 (키가 없으면 값의 시작)
        self.end = end


def parse_value(toks, i, rel):
    kind, val, s, e = toks[i]
    if kind == "{":
        entries, j = parse_items(toks, i + 1, True, rel)
        close = toks[j]
        return Node("block", s, close[3], open_=s, close=close[2], entries=entries), j + 1
    if kind in ("word", "str"):
        return Node("scalar", s, e, text=val), i + 1
    raise ParseError(f"{rel}: 값이 와야 할 자리에 '{val}' (위치 {s})")


def parse_items(toks, i, closing, rel):
    entries = []
    n = len(toks)
    while True:
        if i >= n:
            if closing:
                raise ParseError(f"{rel}: 닫히지 않은 '{{' 가 있습니다")
            return entries, i
        kind, val, s, e = toks[i]
        if kind == "}":
            if closing:
                return entries, i
            raise ParseError(f"{rel}: 짝이 없는 '}}' (위치 {s})")
        if kind == "{":
            node, i = parse_value(toks, i, rel)
            entries.append(Entry(None, node, node.start, node.end))
        elif kind in ("word", "str") and i + 1 < n and toks[i + 1][0] == "=":
            if i + 2 >= n:
                raise ParseError(f"{rel}: '{val} =' 뒤에 값이 없습니다")
            node, i = parse_value(toks, i + 2, rel)
            entries.append(Entry(val, node, s, node.end))
        elif kind in ("word", "str"):
            entries.append(Entry(None, Node("scalar", s, e, text=val), s, e))
            i += 1
        else:
            raise ParseError(f"{rel}: 예상치 못한 기호 '{val}' (위치 {s})")


def parse_root(text, rel):
    toks = tokenize(text, rel)
    entries, _ = parse_items(toks, 0, False, rel)
    return toks, entries


def keys_of(node, out):
    if node is None or node.kind != "block":
        return out
    for e in node.entries:
        if e.key is not None:
            out.add(e.key)
        keys_of(e.value, out)
    return out


def inner_lines(node, text):
    """블록 안쪽 줄을 들여쓰기 기준을 맞춰 돌려준다 (여는/닫는 줄은 뺀다)."""
    if node is None or node.kind != "block":
        return []
    body = text[node.open + 1:node.close]
    if "\n" not in body:
        s = body.strip()
        return [s] if s else []
    lines = body.split("\n")
    if lines[0].strip() == "":
        lines = lines[1:]
    else:
        lines[0] = lines[0].strip()
    if lines and lines[-1].strip() == "":
        lines = lines[:-1]
    nonblank = [ln for ln in lines if ln.strip()]
    base = min(len(ln) - len(ln.lstrip("\t ")) for ln in nonblank) if nonblank else 0
    return [ln[base:].rstrip() if ln.strip() else "" for ln in lines]


# ---------------------------------------------------------------- 파일 묶음

class Src:
    def __init__(self, path, kind, nation):
        self.path = path
        self.rel = show(path)
        self.kind = kind          # piece(우르수스 조각) | tree(국가 트리) | scan(참조만)
        self.nation = nation
        raw = path.read_bytes()
        self.bom = raw.startswith(b"\xef\xbb\xbf")
        body = raw[3:] if self.bom else raw
        text = body.decode("utf-8")
        self.eol = "\r\n" if "\r\n" in text else "\n"
        self.text0 = text.replace("\r\n", "\n")
        self.text = self.text0
        self.out = None
        self.focuses = []
        self.initial = []
        self.toks = []
        self.root = []

    def encode(self, text):
        data = text.replace("\n", self.eol).encode("utf-8")
        return (b"\xef\xbb\xbf" + data) if self.bom else data


class Focus:
    pass


def build_focus(src, entry):
    node = entry.value
    ents = node.entries

    def one(key):
        found = [x for x in ents if x.key == key]
        if len(found) > 1:
            raise ParseError(f"{src.rel}: focus 안에 '{key}' 가 여러 개 있습니다 (위치 {entry.start})")
        return found[0] if found else None

    id_e = one("id")
    if id_e is None or id_e.value.kind != "scalar":
        raise ParseError(f"{src.rel}: focus 에 id 가 없습니다 (위치 {entry.start})")
    f = Focus()
    f.src = src
    f.nation = src.nation
    f.entry = entry
    f.node = node
    f.fid = id_e.value.text
    f.id_entry = id_e
    f.prereq = []
    f.mes = []
    for x in ents:
        if x.key in ("prerequisite", "mutually_exclusive") and x.value.kind == "block":
            items = [y.value.text for y in x.value.entries
                     if y.key == "focus" and y.value.kind == "scalar"]
            (f.prereq if x.key == "prerequisite" else f.mes).append((x, items))
    f.rel_e = one("relative_position_id")
    f.rel = f.rel_e.value.text if f.rel_e is not None else None
    f.x_e = one("x")
    f.y_e = one("y")
    f.x = int(f.x_e.value.text) if f.x_e is not None else 0
    f.y = int(f.y_e.value.text) if f.y_e is not None else 0
    cost_e = one("cost")
    f.cost = int(cost_e.value.text) if cost_e is not None else None
    f.avail = one("available")
    f.reward = one("completion_reward")
    f.ai = one("ai_will_do")
    f.rule = None
    f.cls = None
    return f


def load_src(src):
    src.toks, src.root = parse_root(src.text, src.rel)
    src.focuses = []
    src.initial = []
    if src.kind == "scan":
        return
    if src.kind == "piece":
        container = src.root
    else:
        trees = [e for e in src.root if e.key == "focus_tree" and e.value.kind == "block"]
        if len(trees) != 1:
            raise ParseError(f"{src.rel}: focus_tree 블록이 1개여야 합니다 (현재 {len(trees)}개)")
        container = trees[0].value.entries
        for e in container:
            if e.key == "initial_show_position" and e.value.kind == "block":
                src.initial += [y.value.text for y in e.value.entries
                                if y.key == "focus" and y.value.kind == "scalar"]
    for e in container:
        if e.key == "focus" and e.value.kind == "block":
            src.focuses.append(build_focus(src, e))


def tag_of(name):
    m = re.match(r"tu_([a-z]+)(?:_|\.)", name)
    if m and m.group(1).upper() in NATIONS:
        return m.group(1).upper()
    return None


def collect_sources():
    srcs = []
    seen = set()

    def add(path, kind, nation):
        key = path.resolve()
        if key in seen or key == URS_TREE_PATH.resolve():
            return
        seen.add(key)
        srcs.append(Src(path, kind, nation))

    for p in sorted(URS_DIR.glob("*.txt")):
        if p.name == "_header.txt":
            continue
        add(p, "piece", "URS")
    for p in sorted(NF_DIR.glob("*.txt")):
        if p.resolve() == URS_TREE_PATH.resolve():
            continue
        add(p, "tree", None if p.name == "generic.txt" else tag_of(p.name))
    for d in SCAN_DIRS:
        base = MOD_ROOT / d
        if base.is_dir():
            for p in sorted(base.rglob("*.txt")):
                add(p, "scan", tag_of(p.name))
    for s in srcs:
        load_src(s)
    return srcs


def build_index(srcs):
    idx = {}
    for src in srcs:
        for f in src.focuses:
            if f.fid in idx:
                raise ParseError(f"중점 id 중복: {f.fid} ({idx[f.fid].src.rel}, {src.rel})")
            idx[f.fid] = f
    return idx


def has_completed_refs(toks):
    out = []
    for i in range(len(toks) - 2):
        if (toks[i][0] == "word" and toks[i][1] == "has_completed_focus"
                and toks[i + 1][0] == "=" and toks[i + 2][0] in ("word", "str")):
            out.append(i)
    return out


def collect_refs(srcs, idx):
    """반환: cross (중점 id -> 다른 국가 파일 목록), warnings (이미 있던 빈 참조)."""
    cross = {}
    warnings = []

    def check(target, src, kind, strict):
        if target not in idx:
            if strict:
                warnings.append(f"WARN {src.rel}: {kind} 가 없는 중점을 가리킴: {target}")
            else:
                warnings.append(f"WARN {src.rel}: {kind} 가 없는 중점을 가리킴: {target}")
            return
        owner = idx[target].src.nation
        if owner != src.nation:
            cross.setdefault(target, []).append(src.rel)

    for src in srcs:
        for i in has_completed_refs(src.toks):
            check(src.toks[i + 2][1], src, "has_completed_focus", False)
        for f in src.focuses:
            for _, items in f.prereq:
                for t in items:
                    check(t, src, "prerequisite", True)
            for _, items in f.mes:
                for t in items:
                    check(t, src, "mutually_exclusive", True)
            if f.rel is not None:
                check(f.rel, src, "relative_position_id", True)
        for t in src.initial:
            check(t, src, "initial_show_position", True)
    return cross, warnings


def classify(keys):
    for rule, group, cls in RULES:
        if keys & group:
            return rule, cls
    return 8, "keep"


# ---------------------------------------------------------------- 편집 도우미

def apply_edits(text, edits):
    ordered = sorted(edits, key=lambda x: (x[0], x[1]))
    out = []
    pos = 0
    for s, e, t in ordered:
        if s < pos:
            raise ParseError(f"편집 범위가 겹칩니다 ({s}..{e})")
        out.append(text[pos:s])
        out.append(t)
        pos = e
    out.append(text[pos:])
    return "".join(out)


def line_start(text, pos):
    return text.rfind("\n", 0, pos) + 1


def line_end(text, pos):
    j = text.find("\n", pos)
    return len(text) if j < 0 else j + 1


def line_span(text, s, e):
    """entry 가 한 줄을 혼자 차지하면 그 줄 전체(줄바꿈 포함), 아니면 entry 글자만."""
    if text[line_start(text, s):s].strip() == "" and text[e:line_end(text, e)].strip() == "":
        return line_start(text, s), line_end(text, e)
    return s, e


def blk(name, content):
    return [f"{name} = {{"] + [("\t" + c) if c else "" for c in content] + ["}"]


def ind(lines, prefix):
    return [(prefix + ln) if ln else "" for ln in lines]


def not_flag(x):
    return f"NOT = {{ has_country_flag = TU_DEC_{x} }}"


def not_done(x):
    return f"NOT = {{ has_completed_focus = {x} }}"


def cond_single(item, cids):
    if item in cids:
        return f"has_country_flag = TU_DEC_{item}"
    return f"has_completed_focus = {item}"


def cond_lines(items, cids):
    if len(items) == 1:
        return [cond_single(items[0], cids)]
    return ["OR = {"] + ["\t" + cond_single(i, cids) for i in items] + ["}"]


def delete_edit(text, f):
    s, e = line_span(text, f.entry.start, f.entry.end)
    if s == line_start(text, f.entry.start) and s > 0:
        ps = line_start(text, s - 1)
        if text[ps:s].strip() == "":
            s = ps
    return (s, e, "")


def avail_edit(text, f, lines):
    body_ind = text[line_start(text, f.id_entry.start):f.id_entry.start]
    if f.avail is not None:
        node = f.avail.value
        if node.kind == "block" and "\n" in text[node.open:node.close]:
            cl = line_start(text, node.close)
            if text[cl:node.close].strip() == "":
                close_ind = text[cl:node.close]
                ins = "".join((close_ind + "\t" + ln + "\n") if ln else "\n" for ln in lines)
                return (cl, cl, ins)
        inner = inner_lines(node, text)
        new = (["available = {"]
               + [(body_ind + "\t" + ln) if ln else "" for ln in inner + lines]
               + [body_ind + "}"])
        return (f.avail.start, f.avail.end, "\n".join(new))
    block_lines = ([body_ind + "available = {"]
                   + [(body_ind + "\t" + ln) if ln else "" for ln in lines]
                   + [body_ind + "}", ""])
    pos = line_start(text, f.reward.start) if f.reward is not None else line_start(text, f.node.close)
    return (pos, pos, "".join(ln + "\n" for ln in block_lines))


def retained_roots(fid, cids, idx, memo):
    if fid not in cids:
        return {fid}
    if fid in memo:
        return memo[fid]
    memo[fid] = set()
    out = set()
    for _, items in idx[fid].prereq:
        for t in items:
            out |= retained_roots(t, cids, idx, memo)
    memo[fid] = out
    return out


def abs_of(fid, idx, depth=0):
    f = idx[fid]
    if f.rel is None:
        return (f.x, f.y)
    if depth > 500:
        raise ParseError(f"relative_position_id 순환: {fid}")
    bx, by = abs_of(f.rel, idx, depth + 1)
    return (bx + f.x, by + f.y)


def build_avail_maps(srcs, idx, cids):
    """상호배타 쌍(양방향)으로 디시전 available 의 NOT 조건과 남는 중점 available 추가 조건을 만든다."""
    pairs = set()
    for src in srcs:
        if src.kind == "scan":
            continue
        for f in src.focuses:
            for _, items in f.mes:
                for t in items:
                    if t in idx and t != f.fid:
                        pairs.add(tuple(sorted((f.fid, t))))
    dec_not = {}
    add_avail = {}
    for a, b in sorted(pairs):
        ca, cb = a in cids, b in cids
        if not (ca or cb):
            continue
        if ca and cb:
            dec_not.setdefault(a, []).append(not_flag(b))
            dec_not.setdefault(b, []).append(not_flag(a))
        elif ca:
            dec_not.setdefault(a, []).append(not_done(b))
            add_avail.setdefault(b, []).append(not_flag(a))
        else:
            dec_not.setdefault(b, []).append(not_done(a))
            add_avail.setdefault(a, []).append(not_flag(b))
    return dec_not, add_avail


def plan_src(src, cids, idx, add_avail, memo):
    """남는 중점(retained)의 편집 목록 + 전환된 중점의 삭제 편집."""
    text = src.text
    edits = []
    for f in src.focuses:
        if f.fid in cids:
            edits.append(delete_edit(text, f))
            continue
        pre_conds = []
        for e, items in f.prereq:
            if any(i in cids for i in items):
                new_items = []
                for i in items:
                    targets = sorted(retained_roots(i, cids, idx, memo)) if i in cids else [i]
                    for r in targets:
                        if r not in new_items:
                            new_items.append(r)
                edits.append((e.start, e.end,
                              "prerequisite = { " + " ".join("focus = " + r for r in new_items) + " }"))
                pre_conds += cond_lines(items, cids)
        for e, items in f.mes:
            rem = [i for i in items if i not in cids]
            if rem == items:
                continue
            if rem:
                edits.append((e.start, e.end,
                              "mutually_exclusive = { " + " ".join("focus = " + r for r in rem) + " }"))
            else:
                s, en = line_span(text, e.start, e.end)
                edits.append((s, en, ""))
        conds = pre_conds + add_avail.get(f.fid, [])
        if conds:
            edits.append(avail_edit(text, f, conds))
        if f.rel is not None and f.rel in cids:
            if f.rel_e is None or f.x_e is None or f.y_e is None:
                raise ParseError(f"{src.rel}: {f.fid} 의 relative 좌표를 바꿀 수 없습니다")
            cur = f.rel
            while cur is not None and cur in cids:
                cur = idx[cur].rel
            ax, ay = abs_of(f.fid, idx)
            if cur is not None:
                bx, by = abs_of(cur, idx)
                nx, ny = ax - bx, ay - by
                edits.append((f.rel_e.value.start, f.rel_e.value.end, cur))
            else:
                nx, ny = ax, ay
                s, en = line_span(text, f.rel_e.start, f.rel_e.end)
                edits.append((s, en, ""))
            if nx != f.x:
                edits.append((f.x_e.value.start, f.x_e.value.end, str(nx)))
            if ny != f.y:
                edits.append((f.y_e.value.start, f.y_e.value.end, str(ny)))
    return edits


def decision_block(f, cids, dec_not, text, tag):
    vis = []
    for _, items in f.prereq:
        vis += cond_lines(items, cids)
    av = list(vis) + list(dec_not.get(f.fid, []))
    if f.avail is not None:
        av += inner_lines(f.avail.value, text)
    if f.reward is None:
        raise ParseError(f"{f.src.rel}: {f.fid} 에 completion_reward 가 없습니다")
    reward = inner_lines(f.reward.value, text)
    if f.ai is not None and f.ai.value.kind == "block":
        ai = inner_lines(f.ai.value, text)
    else:
        ai = ["base = 1"]
    if f.cost is None:
        raise ParseError(f"{f.src.rel}: {f.fid} 에 cost 가 없습니다")
    cost = COST_TABLE.get(f.cost, f.cost * 5)
    body = ([f"icon = {RULE_ICON[f.rule]}", ""]
            + blk("allowed", [f"original_tag = {tag}"]) + [""]
            + blk("visible", vis) + [""]
            + blk("available", av) + [""]
            + [f"cost = {cost}", "fire_only_once = yes", ""]
            + blk("complete_effect", reward + [f"set_country_flag = TU_DEC_{f.fid}"]) + [""]
            + blk("ai_will_do", ai))
    return [f"\t{f.fid} = {{"] + ind(body, "\t\t") + ["\t}"]


# ---------------------------------------------------------------- 실행

def run(dry, show_id):
    srcs = collect_sources()
    idx = build_index(srcs)
    cross, warnings = collect_refs(srcs, idx)
    ids_before = set(idx)

    # 0단계: 분류
    candidates = []
    excluded = []
    kept = Counter()
    for src in srcs:
        if src.kind == "scan" or src.nation not in NATIONS:
            continue
        for f in src.focuses:
            keys = keys_of(f.reward.value if f.reward is not None else None, set())
            f.rule, f.cls = classify(keys)
            if f.cls == "keep":
                kept[(src.nation, f.rule)] += 1
                continue
            reasons = []
            if not f.prereq:
                reasons.append("뿌리")
            if f.fid in POLITICAL_CHOICES:
                reasons.append("정치 선택")
            if f.fid in cross:
                reasons.append("다른 국가 파일 참조: " + ", ".join(sorted(set(cross[f.fid]))))
            if reasons:
                excluded.append((src.nation, f.fid, f.cls, f.rule, reasons))
                continue
            candidates.append(f)
    if not candidates:
        print("전환할 중점이 없습니다 (이미 전환됐거나 대상 없음). 파일을 건드리지 않습니다.")
        return 0

    cids = {f.fid for f in candidates}
    info = {f.fid: (f.rule, f.cls) for f in candidates}
    order = [f.fid for f in candidates]

    # 1단계: has_completed_focus = 전환 중점 -> has_country_flag = TU_DEC_<id> (모든 파일)
    rewrites = 0
    for src in srcs:
        edits = []
        for i in has_completed_refs(src.toks):
            tgt = src.toks[i + 2][1]
            if tgt in cids:
                edits.append((src.toks[i][2], src.toks[i][3], "has_country_flag"))
                edits.append((src.toks[i + 2][2], src.toks[i + 2][3], "TU_DEC_" + tgt))
                rewrites += 1
        if edits:
            src.text = apply_edits(src.text, edits)
    for src in srcs:
        load_src(src)
    idx = build_index(srcs)
    for fid in order:
        idx[fid].rule, idx[fid].cls = info[fid]
    candidates = [idx[fid] for fid in order]

    # 2단계: 디시전 블록 생성 (1단계 텍스트 기준)
    dec_not, add_avail = build_avail_maps(srcs, idx, cids)
    per_nation = {}
    for f in candidates:
        per_nation.setdefault(f.nation, []).append(f)
    dec_files = {}      # tag -> text
    cat_entries = []    # (카테고리 이름, 아이콘, tag, 한국어, 영어)
    loc_ko = []
    loc_en = []
    blocks_by_id = {}
    for tag in NATIONS:
        if tag not in per_nation:
            continue
        cat_blocks = []
        for cls in CATEGORY_ORDER:
            members = [f for f in per_nation[tag] if f.cls == cls]
            if not members:
                continue
            suffix, icon, ko, en = CATEGORY_INFO[cls]
            cat = f"TU_{tag}_{suffix}_category"
            decs = []
            for f in members:
                blk_lines = decision_block(f, cids, dec_not, f.src.text, tag)
                blocks_by_id[f.fid] = blk_lines
                decs.append(blk_lines)
            cat_blocks.append((cat, decs))
            cat_entries.append((cat, icon, tag))
            loc_ko.append((cat, ko))
            loc_en.append((cat, en))
        lines = []
        for k, (cat, decs) in enumerate(cat_blocks):
            if k:
                lines.append("")
            lines.append(f"{cat} = {{")
            lines.append("")
            for j, d in enumerate(decs):
                if j:
                    lines.append("")
                lines += d
            lines.append("}")
        dec_files[tag] = "\n".join(lines) + "\n"

    # 3단계: 남는 중점 편집 (1단계 텍스트 기준) 과 삭제
    memo = {}
    for src in srcs:
        if src.kind not in ("piece", "tree"):
            src.out = src.text
            continue
        edits = plan_src(src, cids, idx, add_avail, memo)
        src.out = apply_edits(src.text, edits) if edits else src.text

    cat_text = None
    if cat_entries:
        cl = []
        for k, (cat, icon, tag) in enumerate(cat_entries):
            if k:
                cl.append("")
            cl += [f"{cat} = {{", f"\ticon = {icon}", "", "\tallowed = {",
                   f"\t\toriginal_tag = {tag}", "\t}", "", "\tpriority = 100", "}"]
        cat_text = "\n".join(cl) + "\n"
    loc_outputs = {
        "korean": "﻿l_korean:\n" + "".join(f' {k}:0 "{v}"\n' for k, v in loc_ko),
        "english": "﻿l_english:\n" + "".join(f' {k}:0 "{v}"\n' for k, v in loc_en),
    }

    # 4단계: 검증 (메모리 안에서만)
    problems = validate(srcs, cids, ids_before, dec_files, cat_text, blocks_by_id)

    # 보고
    print(f"[분류] 중점 {sum(len(v) for v in per_nation.values())} 개 전환 대상, 유지(키 분류) {sum(kept.values())} 개")
    for tag in NATIONS:
        members = per_nation.get(tag, [])
        kc = {r: c for (n, r), c in kept.items() if n == tag}
        by_cls = Counter(f.cls for f in members)
        print(f"  {tag}: 전환 {len(members)} (기대 {SPEC_ESTIMATE[tag]}) "
              f"확장 {by_cls['expansion']} / 외교 {by_cls['diplomacy']} / 건설 {by_cls['construction']}"
              f"   유지 규칙별 {dict(sorted(kc.items()))}")
    print("[전환 목록]")
    for f in candidates:
        pre = " | ".join(",".join(items) for _, items in f.prereq)
        me = " | ".join(",".join(items) for _, items in f.mes) or "-"
        print(f"  {f.nation} {f.fid}  rule={f.rule} {f.cls}  cost {f.cost}->{COST_TABLE.get(f.cost, f.cost * 5)}"
              f"  icon={RULE_ICON[f.rule]}  prereq=[{pre}]  me=[{me}]"
              f"  avail_extra={len(add_avail.get(f.fid, []))}  dec_not={len(dec_not.get(f.fid, []))}")
    print(f"[제외] {len(excluded)} 개 (전환 분류였지만 제외)")
    for nation, fid, cls, rule, reasons in excluded:
        print(f"  {nation} {fid}  rule={rule} {cls}  -> {'; '.join(reasons)}")
    print(f"[참조] has_completed_focus 치환 {rewrites} 곳")
    for w in warnings:
        print("  " + w)
    changed = [s for s in srcs if s.out is not None and s.out != s.text0]
    print(f"[편집] 고칠 기존 파일 {len(changed)} 개: " + ", ".join(s.rel for s in changed))
    print(f"[새 파일] {len(dec_files)} 개 디시전 파일, 카테고리 {len(cat_entries)} 개, 로컬라이제이션 키 {len(loc_ko)} 개")

    if show_id:
        if show_id in blocks_by_id:
            print("\n".join(blocks_by_id[show_id]))
        else:
            print(f"(전환 대상 아님: {show_id})")

    if dry:
        print("DRY RUN: 파일을 쓰지 않았습니다.")
        return 0 if not problems else 1
    if problems:
        print("검증 실패: 파일을 쓰지 않았습니다.")
        return 1

    # 실제 쓰기: 백업 후 기록
    for s in changed:
        backup(s.path)
        s.path.write_bytes(s.encode(s.out))
    for tag, text in dec_files.items():
        path = DEC_DIR / f"tu_{tag.lower()}_converted_decisions.txt"
        write_new(path, text)
    if cat_text is not None:
        write_new(CAT_PATH, cat_text)
    for lang, text in loc_outputs.items():
        write_new(LOC_ROOT / lang / f"tu_converted_l_{lang}.yml", text)
    print("완료: 파일을 기록했습니다.")
    return 0


def backup(path):
    dst = BACKUP_DIR / Path(path).resolve().relative_to(REPO)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copy2(path, dst)


def write_new(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup(path)
    path.write_bytes(text.encode("utf-8"))


def validate(srcs, cids, ids_before, dec_files, cat_text, blocks_by_id):
    """메모리 안의 결과를 검사한다. 문제 목록을 돌려준다 (비어 있으면 통과)."""
    problems = []
    views = []
    for src in srcs:
        v = SimpleNamespace(rel=src.rel, kind=src.kind, nation=src.nation, text=src.out)
        load_src(v)
        views.append(v)
    ids_after = set()
    total = 0
    for v in views:
        for f in v.focuses:
            total += 1
            ids_after.add(f.fid)
    if total != len(ids_before) - len(cids):
        problems.append(f"중점 수 불일치: 전 {len(ids_before)} - 전환 {len(cids)} != 남은 {total}")
    left = cids & ids_after
    if left:
        problems.append(f"전환했는데 남은 중점: {sorted(left)[:5]}")
    dangling = 0
    for v in views:
        if v.kind == "scan":
            pass
        for f in v.focuses:
            for _, items in f.prereq + f.mes:
                for t in items:
                    if t in cids:
                        problems.append(f"{v.rel}: {f.fid} 가 전환된 {t} 를 가리킴")
                    elif t not in ids_after:
                        dangling += 1
            if f.rel is not None:
                if f.rel in cids:
                    problems.append(f"{v.rel}: {f.fid} relative 가 전환된 {f.rel} 를 가리킴")
                elif f.rel not in ids_after:
                    dangling += 1
        for i in has_completed_refs(v.toks):
            t = v.toks[i + 2][1]
            if t in cids:
                problems.append(f"{v.rel}: has_completed_focus = {t} (전환됨) 가 남음")
            elif t not in ids_after:
                dangling += 1
        for t in v.initial:
            if t in cids:
                problems.append(f"{v.rel}: initial_show_position 이 전환된 {t} 를 가리킴")
    if dangling:
        problems.append(f"남은 트리에 없는 id 를 가리키는 참조 {dangling} 개 (기존 빈 참조 포함)")
    produced = {f"TU_DEC_{fid}" for fid in cids}
    referenced = set()
    texts = [v.text for v in views]
    texts += list(dec_files.values())
    if cat_text:
        texts.append(cat_text)
    for text in texts:
        if text is None:
            continue
        referenced.update(re.findall(r"TU_DEC_[A-Za-z0-9_]+", text))
    missing_flags = referenced - produced
    if missing_flags:
        problems.append(f"set_country_flag 없이 쓰인 TU_DEC 플래그: {sorted(missing_flags)[:5]}")
    for tag, text in dec_files.items():
        try:
            _, ents = parse_root(text, f"tu_{tag.lower()}_converted_decisions.txt")
        except ParseError as exc:
            problems.append(str(exc))
            continue
    for fid, blk_lines in blocks_by_id.items():
        body = "\n".join(blk_lines)
        if f"set_country_flag = TU_DEC_{fid}" not in body:
            problems.append(f"{fid}: complete_effect 에 TU_DEC 플래그가 없음")
    if cat_text:
        try:
            parse_root(cat_text, "tu_converted_categories.txt")
        except ParseError as exc:
            problems.append(str(exc))
    # 같은 이름의 기존 디시전/카테고리와 충돌하는지
    existing = set()
    for p in DEC_DIR.glob("*.txt"):
        if p.name.startswith("tu_") and "converted" not in p.name:
            for m in re.finditer(r"^\t(TU_[A-Za-z0-9_]+)\s*=\s*\{", p.read_bytes().decode("utf-8"), re.M):
                existing.add(m.group(1))
    clash = sorted(cids & existing)
    if clash:
        problems.append(f"기존 디시전 이름과 충돌: {clash[:5]}")
    print(f"[검증] 중점 {ids_before and len(ids_before)} -> {total} (전환 {len(cids)}), "
          f"남은 참조 빈칸 {dangling}, 문제 {len(problems)}")
    for p in problems[:30]:
        print("  PROBLEM " + p)
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="국가 중점을 디시전으로 전환")
    parser.add_argument("--dry-run", action="store_true", help="목록만 출력하고 파일은 쓰지 않는다")
    parser.add_argument("--show", metavar="FOCUS_ID", help="이 중점이 만들 디시전 블록을 출력한다 (파일은 쓰지 않음)")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        return run(args.dry_run or bool(args.show), args.show)
    except ParseError as exc:
        print(f"ERROR {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
