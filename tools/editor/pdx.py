"""HOI4 스크립트(Clausewitz) 파서와 부분 수정 도구 (표준 라이브러리만 사용).

파일을 통째로 다시 쓰지 않는다. 고친 항목의 글자 범위만 바꿔 끼우므로 주석, 줄 바꿈, 들여쓰기, 손대지 않은
항목은 그대로 남는다.

    text = read_text(path)
    root = parse(text)                       # Block (최상위 항목 목록)
    e = root.entries[0]                      # Entry: key, op, value(str 또는 Block), start, end
    raw = inner_raw(text, e.value)           # 블록 안쪽 글자 (들여쓰기 걷어냄)
    text = splice(text, [(start, end, new)]) # 여러 범위를 한 번에 바꿈
"""

import textwrap

WS = " \t\r\n"
STOP = WS + '{}=<>!#"'


class ParseError(Exception):
    def __init__(self, msg, pos, text):
        line = text.count("\n", 0, pos) + 1
        super().__init__("%s (줄 %d)" % (msg, line))
        self.line = line


class Block:
    __slots__ = ("entries", "open", "close")

    def __init__(self, open_pos):
        self.entries = []
        self.open = open_pos    # '{' 위치 (최상위는 -1)
        self.close = None       # '}' 위치 (최상위는 글 길이)

    def find(self, key):
        return [e for e in self.entries if e.key == key]

    def first(self, key):
        for e in self.entries:
            if e.key == key:
                return e
        return None

    def scalar(self, key):
        e = self.first(key)
        return e.value if e is not None and isinstance(e.value, str) else None


class Entry:
    __slots__ = ("key", "key_span", "op", "value", "start", "end")

    def __init__(self, key, key_span, op, value, start, end):
        self.key = key            # 키 (값만 있는 항목은 None)
        self.key_span = key_span  # 키 글자 범위 (start, end)
        self.op = op              # '=', '<', '>' ...
        self.value = value        # str (따옴표 포함 그대로) 또는 Block
        self.start = start
        self.end = end


def tokenize(text):
    toks = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in WS:
            i += 1
            continue
        if c == "#":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "{" or c == "}":
            toks.append((c, c, i, i + 1))
            i += 1
            continue
        if c in "=<>!":
            j = i + 1
            if j < n and text[j] == "=":
                j += 1
            toks.append(("op", text[i:j], i, j))
            i = j
            continue
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                if text[j] == "\\":
                    j += 1
                j += 1
            j = min(j + 1, n)
            toks.append(("str", text[i:j], i, j))
            i = j
            continue
        j = i
        while j < n and text[j] not in STOP:
            j += 1
        toks.append(("word", text[i:j], i, j))
        i = j
    return toks


def parse(text):
    toks = tokenize(text)
    pos = 0

    def parse_block(open_pos, top):
        nonlocal pos
        blk = Block(open_pos)
        while True:
            if pos >= len(toks):
                if top:
                    blk.close = len(text)
                    return blk
                raise ParseError("'}' 가 모자람 (여기서 연 블록)", open_pos, text)
            kind, val, s, e = toks[pos]
            if kind == "}":
                if top:
                    raise ParseError("짝이 없는 '}'", s, text)
                blk.close = s
                pos += 1
                return blk
            if kind == "op":
                raise ParseError("키 없이 '%s' 가 나옴" % val, s, text)
            # 첫 값
            first = parse_value()
            if pos < len(toks) and toks[pos][0] == "op" and not isinstance(first[0], Block):
                op = toks[pos][1]
                pos += 1
                if pos >= len(toks):
                    raise ParseError("'%s' 뒤에 값이 없음" % op, s, text)
                v = parse_value()
                blk.entries.append(Entry(first[0], (first[1], first[2]), op, v[0], first[1], v[2]))
            else:
                blk.entries.append(Entry(None, None, None, first[0], first[1], first[2]))

    def parse_value():
        nonlocal pos
        kind, val, s, e = toks[pos]
        if kind == "{":
            pos += 1
            b = parse_block(s, False)
            return b, s, b.close + 1
        if kind in ("word", "str"):
            pos += 1
            return val, s, e
        raise ParseError("값 자리에 '%s' 가 나옴" % val, s, text)

    return parse_block(-1, True)


# ---------------------------------------------------------------- 글자 위치 도우미

def line_start(text, pos):
    return text.rfind("\n", 0, pos) + 1


def line_end(text, pos):
    j = text.find("\n", pos)
    return len(text) if j < 0 else j


def indent_of(text, pos):
    ls = line_start(text, pos)
    j = ls
    while j < pos and text[j] in " \t":
        j += 1
    return text[ls:j]


def inner_raw(text, blk):
    """블록 안쪽 글자. 줄 바꿈을 \\n 으로 맞추고, 앞뒤 빈 줄과 공통 들여쓰기를 걷어낸다."""
    raw = text[blk.open + 1:blk.close].replace("\r\n", "\n")
    if "\n" not in raw.strip("\n"):
        return raw.strip()
    lines = raw.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return textwrap.dedent("\n".join(lines))


def norm(raw):
    """비교용: 줄 끝 공백과 앞뒤 빈 줄을 무시한다."""
    return "\n".join(l.rstrip() for l in raw.replace("\r\n", "\n").strip("\n").split("\n")).strip()


def fmt_block(raw, indent):
    raw = raw.replace("\r\n", "\n").strip("\n")
    if not raw.strip():
        return "{ }"
    lines = raw.split("\n")
    if len(lines) == 1 and len(lines[0].strip()) <= 80:
        return "{ " + lines[0].strip() + " }"
    lines = textwrap.dedent("\n".join(lines)).split("\n")
    body = "\n".join((indent + "\t" + l) if l.strip() else "" for l in lines)
    return "{\n" + body + "\n" + indent + "}"


def fmt_entry(key, op, kind, value, indent):
    op = op or "="
    if kind == "block":
        return "%s %s %s" % (key, op, fmt_block(value, indent))
    return "%s %s %s" % (key, op, value.strip())


def splice(text, edits):
    """edits: [(start, end, 새 글자)]. 겹치면 오류."""
    edits = sorted(edits, key=lambda e: (e[0], e[1]))
    for a, b in zip(edits, edits[1:]):
        if a[1] > b[0]:
            raise ValueError("고칠 범위가 겹침: %r / %r" % (a[:2], b[:2]))
    out, last = [], 0
    for s, e, new in edits:
        out.append(text[last:s])
        out.append(new)
        last = e
    out.append(text[last:])
    return "".join(out)


def delete_span(text, entry):
    """항목을 지우는 범위. 혼자 한 줄(들)을 차지하면 그 줄째 지운다."""
    ls = line_start(text, entry.start)
    le = line_end(text, entry.end)
    after = text[entry.end:le]
    if not text[ls:entry.start].strip() and (not after.strip() or after.strip().startswith("#")):
        return (ls, min(le + 1, len(text)), "")
    s = entry.start
    if s > 0 and text[s - 1] == " ":
        s -= 1
    return (s, entry.end, "")


def insert_into(text, blk, lines_text):
    """블록 닫는 괄호 앞에 항목을 넣는다. lines_text: 들여쓰기 없는 여러 줄 (\\n). 넣을 수 없으면 None."""
    close = blk.close
    ls = line_start(text, close)
    if text[ls:close].strip():
        return None
    ind = text[ls:close] + ("\t" if blk.open >= 0 else "")
    if blk.open < 0:                       # 최상위: 파일 끝
        body = "\n".join((l if l.strip() else "") for l in lines_text.split("\n"))
        pre = "" if text.endswith("\n") or not text else "\n"
        return (len(text), len(text), pre + "\n" + body + "\n")
    body = "\n".join((ind + l) if l.strip() else "" for l in lines_text.split("\n"))
    return (ls, ls, body + "\n")


def entry_text(key, children, indent=""):
    """새 항목 글자 (들여쓰기 없는 기준). children: [{key, op, kind, value}]."""
    inner = []
    for c in children:
        if c.get("kind") == "bare":
            inner.append("\t" + c["value"])
        else:
            inner.append("\t" + fmt_entry(c["key"], c.get("op"), c["kind"], c["value"], "\t"))
    if not inner:
        return "%s = { }" % key
    return "%s = {\n%s\n}" % (key, "\n".join(inner))


def read_text(path):
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw[3:].decode("utf-8") if bom else raw.decode("utf-8", errors="replace")
    return text, bom


def write_text(path, text, bom):
    data = text.encode("utf-8")
    path.write_bytes((b"\xef\xbb\xbf" + data) if bom else data)
