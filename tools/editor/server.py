#!/usr/bin/env python3
"""Terra Universalis 모드 편집기 (로컬 웹 앱, 표준 라이브러리만 사용).

    python -I tools/editor/server.py            # http://127.0.0.1:8765 이 브라우저에서 열린다
    python -I tools/editor/server.py --port 9000 --no-browser

게임 파일(terra_universalis/)을 직접 읽고 고친다. 고친 항목의 글자 범위만 바꾸므로 나머지는 그대로 남는다.
저장하기 전 원본은 tools/editor/_backup/<시각>/ 에 복사한다.
게임 공식 문서(효과·조건·모디파이어 사전)는 HOI4 설치 폴더의 documentation/ 에서 읽는다
(환경변수 TU_HOI4_DIR 또는 Steam 기본 경로).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gitops  # noqa: E402
import pdx  # noqa: E402

FROZEN = getattr(sys, "frozen", False)          # exe 로 묶였을 때 (build_exe.py)
STATIC = Path(getattr(sys, "_MEIPASS", HERE)) / "static"
LOCK = threading.Lock()
GIT_LOCK = threading.Lock()
CLIENTS = {}           # 열린 화면(창·탭)별 마지막 신호 시각. exe 실행기가 창이 다 닫혔는지 알아챈다
EVENTS = []            # 실행기 기록용 (처음 연결·닫힘)


def set_repo(path):
    """편집할 저장소 위치를 정한다. exe 는 실행기(app.py)가 찾아서 넣어 준다."""
    global REPO, MOD, BACKUP
    REPO = Path(path).resolve()
    MOD = REPO / "terra_universalis"
    BACKUP = REPO / "tools" / "editor" / "_backup"


def looks_like_repo(path):
    return (Path(path) / "terra_universalis" / "descriptor.mod").is_file()


set_repo(HERE.parents[1])

# ---------------------------------------------------------------- 종류별 정의

KINDS = {
    "focus": {"label": "중점", "dir": "common/national_focus"},
    "decision": {"label": "디시전", "dir": "common/decisions"},
    "category": {"label": "디시전 분류", "dir": "common/decisions/categories"},
    "idea": {"label": "국민정신", "dir": "common/ideas"},
    "character": {"label": "지도자·장군", "dir": "common/characters"},
    "event": {"label": "이벤트", "dir": "events"},
}
EVENT_KEYS = ("country_event", "news_event", "state_event", "unit_leader_event", "operative_leader_event")


def entities(kind, root):
    """(locator, entry, 부모 이름) 목록. locator 는 파일 안에서 항목을 가리키는 고유 이름."""
    out = []
    if kind == "focus":
        for t in root.entries:
            if t.key == "focus_tree" and isinstance(t.value, pdx.Block):
                for f in t.value.find("focus"):
                    if isinstance(f.value, pdx.Block):
                        fid = f.value.scalar("id")
                        if fid:
                            out.append(("focus:" + fid, f, t.value.scalar("id") or ""))
            elif t.key == "shared_focus" and isinstance(t.value, pdx.Block):
                fid = t.value.scalar("id")
                if fid:
                    out.append(("focus:" + fid, t, "shared"))
    elif kind == "decision":
        for c in root.entries:
            if c.key and isinstance(c.value, pdx.Block):
                for d in c.value.entries:
                    if d.key and isinstance(d.value, pdx.Block):
                        out.append(("decision:%s/%s" % (c.key, d.key), d, c.key))
    elif kind == "category":
        for c in root.entries:
            if c.key and isinstance(c.value, pdx.Block):
                out.append(("category:" + c.key, c, ""))
    elif kind == "idea":
        for top in root.find("ideas"):
            if isinstance(top.value, pdx.Block):
                for slot in top.value.entries:
                    if slot.key and isinstance(slot.value, pdx.Block):
                        for i in slot.value.entries:
                            if i.key and isinstance(i.value, pdx.Block) and i.key != "law":
                                out.append(("idea:%s/%s" % (slot.key, i.key), i, slot.key))
    elif kind == "character":
        for top in root.find("characters"):
            if isinstance(top.value, pdx.Block):
                for c in top.value.entries:
                    if c.key and isinstance(c.value, pdx.Block):
                        out.append(("character:" + c.key, c, ""))
    elif kind == "event":
        for e in root.entries:
            if e.key in EVENT_KEYS and isinstance(e.value, pdx.Block):
                eid = e.value.scalar("id")
                if eid:
                    out.append(("event:" + eid, e, e.key))
    return out


def containers(kind, root):
    """새 항목을 넣을 수 있는 곳: {부모 이름: Block}. 없는 부모는 만들 수 있다 (decision/idea)."""
    if kind == "focus":
        return {t.value.scalar("id") or "focus_tree": t.value for t in root.entries
                if t.key == "focus_tree" and isinstance(t.value, pdx.Block)}
    if kind == "decision":
        return {c.key: c.value for c in root.entries if c.key and isinstance(c.value, pdx.Block)}
    if kind == "idea":
        out = {}
        for top in root.find("ideas"):
            if isinstance(top.value, pdx.Block):
                out.update({s.key: s.value for s in top.value.entries if s.key and isinstance(s.value, pdx.Block)})
        return out
    if kind == "character":
        tops = [t.value for t in root.find("characters") if isinstance(t.value, pdx.Block)]
        return {"characters": tops[0]} if tops else {}
    return {"": root}       # category, event: 최상위


# ---------------------------------------------------------------- 파일 읽기

def safe_path(rel):
    p = (MOD / rel).resolve()
    if MOD.resolve() not in p.parents or p.suffix != ".txt":
        raise ValueError("잘못된 경로: %s" % rel)
    return p


def is_generated(text):
    head = text[:3000]
    return bool(re.search(r"[Gg]enerated by|Do not edit|generated by tools/", head)) or "(generated by tools/" in text


def list_files(kind):
    out = []
    for p in sorted((MOD / KINDS[kind]["dir"]).glob("*.txt")):
        text, _ = pdx.read_text(p)
        try:
            n = len(entities(kind, pdx.parse(text)))
            err = None
        except pdx.ParseError as e:
            n, err = 0, str(e)
        if n or err or kind in ("category", "event"):
            out.append({"path": p.relative_to(MOD).as_posix(), "count": n, "generated": is_generated(text), "error": err})
    return out


def child_model(text, blk):
    out = []
    for i, c in enumerate(blk.entries):
        if c.key is None:
            out.append({"i": i, "key": None, "op": None, "kind": "bare",
                        "value": text[c.start:c.end].replace("\r\n", "\n")})
        elif isinstance(c.value, pdx.Block):
            out.append({"i": i, "key": c.key, "op": c.op, "kind": "block", "value": pdx.inner_raw(text, c.value)})
        else:
            out.append({"i": i, "key": c.key, "op": c.op, "kind": "scalar", "value": c.value})
    return out


def load_file(kind, rel):
    p = safe_path(rel)
    raw = p.read_bytes()
    text, _ = pdx.read_text(p)
    res = {"path": rel, "kind": kind, "hash": hashlib.sha1(raw).hexdigest(), "generated": is_generated(text),
           "entities": [], "parents": [], "error": None}
    try:
        root = pdx.parse(text)
    except pdx.ParseError as e:
        res["error"] = str(e)
        return res
    for loc, e, parent in entities(kind, root):
        res["entities"].append({"loc": loc, "key": e.key, "parent": parent,
                                "line": text.count("\n", 0, e.start) + 1,
                                "children": child_model(text, e.value)})
    res["parents"] = list(containers(kind, root).keys())
    return res


# ---------------------------------------------------------------- 저장

def apply_changes(kind, text, changes):
    """changes: [{op: edit|create|delete, ...}] -> 새 글자. 한 번 파싱한 범위로 모두 계산해 한꺼번에 바꾼다."""
    nl = "\r\n" if "\r\n" in text else "\n"
    root = pdx.parse(text)
    ents = {loc: e for loc, e, _ in entities(kind, root)}
    conts = containers(kind, root)
    edits = []
    inserts = {}          # 부모 Block id -> (Block, [글자])
    new_parents = []      # 없는 부모를 새로 만들 때 [(부모 이름, [글자])]

    for ch in changes:
        op = ch["op"]
        if op == "delete":
            e = ents.get(ch["loc"])
            if e is None:
                raise ValueError("항목을 찾을 수 없음: %s" % ch["loc"])
            edits.append(pdx.delete_span(text, e))
        elif op == "edit":
            e = ents.get(ch["loc"])
            if e is None:
                raise ValueError("항목을 찾을 수 없음: %s" % ch["loc"])
            edits.extend(edit_entity(text, e, ch))
        elif op == "create":
            body = pdx.entry_text(ch["key"], ch["children"])
            parent = ch.get("parent", "")
            blk = conts.get(parent)
            if blk is None:
                if kind in ("decision", "idea"):
                    new_parents.append((parent, body))
                    continue
                raise ValueError("넣을 곳을 찾을 수 없음: %s" % parent)
            inserts.setdefault(id(blk), (blk, []))[1].append(body)
        else:
            raise ValueError("알 수 없는 작업: %s" % op)

    for blk, bodies in inserts.values():
        ins = pdx.insert_into(text, blk, "\n\n".join(bodies))
        if ins is None:
            raise ValueError("한 줄로 쓴 블록에는 새 항목을 넣을 수 없음")
        if blk.open >= 0:
            ins = (ins[0], ins[1], "\n" + ins[2])
        edits.append(ins)
    if new_parents:
        by = {}
        for parent, body in new_parents:
            by.setdefault(parent, []).append(body)
        lines = []
        for parent, bodies in by.items():
            inner = "\n\n".join(bodies)
            inner = "\n".join(("\t" + l) if l.strip() else "" for l in inner.split("\n"))
            block = "%s = {\n%s\n}" % (parent, inner)
            if kind == "idea":
                ideas = root.first("ideas")
                if ideas is not None and isinstance(ideas.value, pdx.Block):
                    ins = pdx.insert_into(text, ideas.value, block)
                    edits.append((ins[0], ins[1], "\n" + ins[2]))
                    continue
                block = "ideas = {\n" + "\n".join(("\t" + l) if l.strip() else "" for l in block.split("\n")) + "\n}"
            lines.append(block)
        if lines:
            edits.append(pdx.insert_into(text, root, "\n\n".join(lines)))

    edits = [(s, e, new.replace("\r\n", "\n").replace("\n", nl)) for s, e, new in edits]
    return pdx.splice(text, edits)


def edit_entity(text, e, ch):
    blk = e.value
    orig = child_model(text, blk)
    new = ch["children"]
    edits = []
    if ch.get("key") and ch["key"] != e.key:
        edits.append((e.key_span[0], e.key_span[1], ch["key"]))
    seen = set()
    child_edits = []
    for c in new:
        i = c.get("i")
        if i is None:
            continue
        seen.add(i)
        o = orig[i]
        if o["kind"] == "bare":
            continue
        if (c["key"], c.get("op") or "=", c["kind"], pdx.norm(c["value"])) != (o["key"], o["op"] or "=", o["kind"], pdx.norm(o["value"])):
            en = blk.entries[i]
            ind = pdx.indent_of(text, en.start)
            child_edits.append((en.start, en.end, pdx.fmt_entry(c["key"], c.get("op"), c["kind"], c["value"], ind)))
    for i, en in enumerate(blk.entries):
        if i not in seen and orig[i]["kind"] != "bare":
            child_edits.append(pdx.delete_span(text, en))
    added = [c for c in new if c.get("i") is None]
    if added:
        body = "\n".join(pdx.fmt_entry(c["key"], c.get("op"), c["kind"], c["value"], "") for c in added)
        ins = pdx.insert_into(text, blk, body)
        if ins is None:
            # 한 줄짜리 블록: 항목 전체를 다시 쓴다
            ind = pdx.indent_of(text, e.start)
            keep = [c for c in new if c.get("i") is None or orig[c["i"]]["kind"] != "bare"] + \
                   [o for o in orig if o["kind"] == "bare"]
            whole = pdx.entry_text(ch.get("key") or e.key, keep)
            whole = "\n".join((ind + l) if k and l.strip() else l for k, l in enumerate(whole.split("\n")))
            return [(e.start, e.end, whole)]
        child_edits.append(ins)        # 들여쓰기는 insert_into 가 블록 기준으로 붙인다
    return edits + child_edits


def save(kind, rel, h, changes):
    p = safe_path(rel)
    with LOCK:
        raw = p.read_bytes()
        if hashlib.sha1(raw).hexdigest() != h:
            raise ValueError("파일이 다른 곳에서 바뀌었습니다. 다시 불러온 뒤 고쳐 주세요.")
        text, bom = pdx.read_text(p)
        new = apply_changes(kind, text, changes)
        pdx.parse(new)                      # 결과가 다시 읽히는지 확인
        backup(p, raw)
        pdx.write_text(p, new, bom)
    return load_file(kind, rel)


def backup(p, raw):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = BACKUP / stamp / p.relative_to(MOD)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        dst.write_bytes(raw)
    gi = BACKUP / ".gitignore"
    if not gi.exists():
        gi.write_text("*\n", encoding="utf-8")


# ---------------------------------------------------------------- 로컬라이제이션

LOC_RE = re.compile(r'^(\s*)([^\s:#"]+):(\d*)\s*"(.*)"(\s*#.*)?\s*$')
LANGS = {"ko": "korean", "en": "english"}
_loc = {"index": None}


def loc_index():
    if _loc["index"] is None:
        idx = {}
        for lang, folder in LANGS.items():
            d = MOD / "localisation" / folder
            for p in sorted(d.rglob("*.yml")):
                for n, line in enumerate(p.read_text(encoding="utf-8-sig", errors="replace").splitlines()):
                    m = LOC_RE.match(line)
                    if m:
                        idx.setdefault((lang, m.group(2)), (p, n, m.group(4)))
        _loc["index"] = idx
    return _loc["index"]


def loc_get(keys):
    idx = loc_index()
    return {k: {lang: (idx.get((lang, k)) or (None, None, None))[2] for lang in LANGS} for k in keys}


def loc_save(items):
    idx = loc_index()
    by_file, new = {}, {}
    for it in items:
        lang, key, value = it["lang"], it["key"], it["value"].replace("\r\n", "\n").replace("\n", "\\n")
        hit = idx.get((lang, key))
        if hit:
            by_file.setdefault(hit[0], {})[hit[1]] = (key, value)
        elif value:
            new.setdefault(lang, []).append((key, value))
    with LOCK:
        for p, lines in by_file.items():
            raw = p.read_bytes()
            backup(p, raw)
            nl = "\r\n" if b"\r\n" in raw else "\n"
            text = raw.decode("utf-8-sig", errors="replace").replace("\r\n", "\n").split("\n")
            for n, (key, value) in lines.items():
                m = LOC_RE.match(text[n])
                text[n] = '%s%s:%s "%s"%s' % (m.group(1), key, m.group(3) or "0", value, m.group(5) or "")
            p.write_bytes(b"\xef\xbb\xbf" + nl.join(text).encode("utf-8"))
        for lang, rows in new.items():
            folder = LANGS[lang]
            p = MOD / "localisation" / folder / ("tu_editor_l_%s.yml" % folder)
            if p.exists():
                body = p.read_text(encoding="utf-8-sig").rstrip("\n") + "\n"
            else:
                body = "l_%s:\n" % folder
            body += "".join(' %s:0 "%s"\n' % kv for kv in rows)
            p.write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))
    _loc["index"] = None


# ---------------------------------------------------------------- 게임 문서 (효과·조건·모디파이어)

def find_game():
    cands = [os.environ.get("TU_HOI4_DIR")]
    vdf = Path(r"C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf")
    if vdf.exists():
        for m in re.finditer(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="replace")):
            cands.append(str(Path(m.group(1).replace("\\\\", "\\")) / "steamapps" / "common" / "Hearts of Iron IV"))
    cands += [r"C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV",
              r"G:\SteamLibrary\steamapps\common\Hearts of Iron IV",
              str(Path.home() / ".steam/steam/steamapps/common/Hearts of Iron IV")]
    for c in cands:
        if c and (Path(c) / "documentation").is_dir():
            return Path(c)
    return None


_docs = {}


def docs(kind):
    if kind not in _docs:
        game = find_game()
        out = []
        if game:
            p = game / "documentation" / ("%s_documentation.md" % kind)
            if p.exists():
                text = p.read_text(encoding="utf-8", errors="replace")
                for sec in re.split(r"\n## ", text)[1:]:
                    name, _, body = sec.partition("\n")
                    name = re.sub(r"<[^>]+>", "", name).strip()
                    if not name or name.startswith("Modifiers for scope") or name == "Table of Content":
                        continue
                    out.append({"name": name, "body": body.strip().replace("```", "")[:1500]})
        _docs[kind] = out
    return _docs[kind]


# ---------------------------------------------------------------- 검사·기타

def python_exe():
    if not FROZEN:
        return [sys.executable]
    for name in ("python", "py"):
        hit = shutil.which(name)
        if hit and "WindowsApps" not in hit:
            return [hit]
    return None


def run_checks():
    out = []
    py = python_exe()
    if not py:
        return "검사에는 파이썬이 필요합니다. python.org 에서 파이썬을 설치한 뒤 다시 눌러 주세요."
    nw = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    cmd = py + ["-I", str(REPO / "tools" / "lint" / "tu_lint.py")]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=REPO,
                       stdin=subprocess.DEVNULL, creationflags=nw)
    out.append("== tu_lint\n" + (r.stdout + r.stderr)[-6000:])
    game = find_game()
    if game:
        cmd = py + ["-I", str(REPO / "tools" / "check_refs.py"), "--vanilla", str(game)]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=REPO,
                           stdin=subprocess.DEVNULL, creationflags=nw)
        tail = (r.stdout + r.stderr).strip().splitlines()
        out.append("== check_refs (마지막 줄)\n" + "\n".join(tail[-3:]))
    return "\n\n".join(out)


def add_recruit(tag, name):
    hits = sorted((MOD / "history" / "countries").glob("%s - *.txt" % tag))
    if not hits:
        raise ValueError("국가 기록 파일을 찾을 수 없음: %s" % tag)
    p = hits[0]
    raw = p.read_bytes()
    text, bom = pdx.read_text(p)
    if re.search(r"recruit_character\s*=\s*%s\b" % re.escape(name), text):
        return "이미 영입되어 있음: %s" % p.name
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(nl)
    last = max([i for i, l in enumerate(lines) if l.strip().startswith("recruit_character")], default=None)
    if last is None:
        text = text.rstrip() + nl + "recruit_character = %s" % name + nl
    else:
        lines.insert(last + 1, "recruit_character = %s" % name)
        text = nl.join(lines)
    with LOCK:
        backup(p, raw)
        pdx.write_text(p, text, bom)
    return "%s 에 recruit_character = %s 추가" % (p.name, name)


def git_post(op, b):
    with GIT_LOCK:
        if op == "pull":
            return {"output": gitops.pull(REPO)}
        if op == "commit":
            return {"output": gitops.commit(REPO, b.get("paths") or [], b.get("message", ""))}
        if op == "push":
            return gitops.push(REPO)
        if op == "switch":
            return {"output": gitops.switch(REPO, b.get("branch", ""), bool(b.get("create")))}
    raise ValueError("없는 git 작업: %s" % op)


# ---------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n).decode("utf-8") or "{}")

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/api/kinds":
                return self.send_json({"kinds": {k: v["label"] for k, v in KINDS.items()},
                                       "game": str(find_game() or ""), "repo": str(REPO), "app": FROZEN})
            if u.path == "/api/ping":
                cid = q.get("id", "?")
                if cid not in CLIENTS:
                    EVENTS.append("open " + cid)
                CLIENTS[cid] = time.time()
                return self.send_json({"ok": True})
            if u.path == "/api/git/status":
                with GIT_LOCK:
                    return self.send_json(gitops.status(REPO, fetch=q.get("fetch") == "1"))
            if u.path == "/api/git/diff":
                return self.send_json({"diff": gitops.diff(REPO, q["path"])})
            if u.path == "/api/files":
                return self.send_json(list_files(q["kind"]))
            if u.path == "/api/file":
                return self.send_json(load_file(q["kind"], q["path"]))
            if u.path == "/api/loc":
                return self.send_json(loc_get([k for k in q.get("keys", "").split(",") if k]))
            if u.path == "/api/docs":
                needle = q.get("q", "").lower()
                hits = [d for d in docs(q.get("kind", "effects")) if needle in d["name"].lower()]
                hits.sort(key=lambda d: (not d["name"].lower().startswith(needle), d["name"]))
                return self.send_json(hits[:60])
            return self.static(u.path)
        except Exception as e:            # noqa: BLE001
            return self.send_json({"error": str(e)}, 400)

    def do_POST(self):
        u = urlparse(self.path)
        try:
            b = self.body()
            if u.path == "/api/save":
                return self.send_json(save(b["kind"], b["path"], b["hash"], b["changes"]))
            if u.path == "/api/loc":
                loc_save(b["items"])
                return self.send_json({"ok": True})
            if u.path == "/api/check":
                return self.send_json({"output": run_checks()})
            if u.path == "/api/recruit":
                return self.send_json({"message": add_recruit(b["tag"], b["name"])})
            if u.path == "/api/bye":
                if CLIENTS.pop(b.get("id", "?"), None):
                    EVENTS.append("close " + b.get("id", "?"))
                return self.send_json({"ok": True})
            if u.path.startswith("/api/git/"):
                return self.send_json(git_post(u.path[len("/api/git/"):], b))
            return self.send_json({"error": "없는 주소"}, 404)
        except Exception as e:            # noqa: BLE001
            return self.send_json({"error": str(e)}, 400)

    def static(self, path):
        name = "index.html" if path in ("/", "") else path.lstrip("/")
        p = (STATIC / name).resolve()
        if STATIC.resolve() not in p.parents or not p.is_file():
            self.send_response(404)
            self.end_headers()
            return
        ctype = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".ico": "image/x-icon",
                 ".png": "image/png"}.get(p.suffix, "application/octet-stream")
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Terra Universalis 모드 편집기")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args(argv)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = "http://127.0.0.1:%d/" % a.port
    print("Terra Universalis 편집기: %s  (끝내려면 Ctrl+C)" % url)
    if not a.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
