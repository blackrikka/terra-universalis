#!/usr/bin/env python3
"""기존 트리 조각에서 군함·조선소·해군기지 중점을 지우고 앞뒤를 잇는다 (사양서 18).

사용법 (python -I):
    python -I tools/focusgen/drop_focuses.py --tag VIC [--dry]

- 지울 중점: 영어 이름이 theme_effects.is_warship 에 맞는 중점 (RHO 제외).
- 남는 중점의 prerequisite / mutually_exclusive 줄을 focus_drop.drop 결과로 다시 쓴다 (한 줄 형식).
- 모드 전체(common, events)의 has_completed_focus = <지운 id> 를 남는 조상으로 바꾼다.
- 지운 중점의 로컬라이제이션 줄도 지운다.
content/<tag>.py 로 만드는 13개국은 content_lib 가 같은 일을 하므로 여기서 다루지 않는다.
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import focus_drop  # noqa: E402
from theme_effects import is_warship  # noqa: E402

REPO = HERE.parents[1]
MOD = REPO / "terra_universalis"
BLOCK_RE = re.compile(r"(?=\n\tfocus = \{\n)")


def load_en():
    loc = {}
    for f in (MOD / "localisation" / "english").rglob("*.yml"):
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r'\s(\S+?):\d*\s+"(.*)"', line)
            if m:
                loc[m.group(1)] = m.group(2)
    return loc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    tag = a.tag.upper()
    folder = HERE / tag.lower()
    en = load_en()
    files = {f: f.read_text(encoding="utf-8") for f in sorted(folder.glob("*.txt")) if f.name != "_header.txt"}
    nodes = {}
    for text in files.values():
        for b in BLOCK_RE.split(text)[1:]:
            fid = re.search(r"\n\t\tid = (\S+)", b).group(1)
            pre = [re.findall(r"focus = (\S+)", g) for g in re.findall(r"\n\t\tprerequisite = \{([^}\n]*)\}", b)]
            me = re.findall(r"focus = (\S+)", " ".join(re.findall(r"\n\t\tmutually_exclusive = \{([^}\n]*)\}", b)))
            nodes[fid] = {"pre": pre, "me": me}
    removed = {fid for fid in nodes if is_warship(en.get(fid, ""), tag)}
    print("DROP %s: %d / %d" % (tag, len(removed), len(nodes)))
    for fid in sorted(removed):
        print("  -", fid, "|", en.get(fid, ""))
    if not removed or a.dry:
        return 0
    new, anc = focus_drop.drop(nodes, removed)

    for f, text in files.items():
        parts = BLOCK_RE.split(text)
        out = [parts[0]]
        for b in parts[1:]:
            fid = re.search(r"\n\t\tid = (\S+)", b).group(1)
            if fid in removed:
                continue
            b = re.sub(r"\n\t\tprerequisite = \{[^}\n]*\}", "", b)
            b = re.sub(r"\n\t\tmutually_exclusive = \{[^}\n]*\}", "", b)
            lines = "".join("\n\t\tprerequisite = { %s }" % " ".join("focus = %s" % x for x in g) for g in new[fid]["pre"])
            if new[fid]["me"]:
                lines += "\n\t\tmutually_exclusive = { %s }" % " ".join("focus = %s" % x for x in new[fid]["me"])
            b = re.sub(r"(\n\t\tid = \S+)", lambda m: m.group(1) + lines, b, count=1)
            out.append(focus_drop.fix_refs(b, anc))
        f.write_text("".join(out), encoding="utf-8")

    for f in list((MOD / "common").rglob("*.txt")) + list((MOD / "events").rglob("*.txt")):
        s = f.read_text(encoding="utf-8")
        t = focus_drop.fix_refs(s, anc)
        if t != s:
            f.write_text(t, encoding="utf-8")
            print("  refs fixed:", f.relative_to(REPO))
    for f in (MOD / "localisation").rglob("*.yml"):
        s = f.read_text(encoding="utf-8-sig")
        lines = [l for l in s.split("\n")
                 if not any(re.match(r"\s%s(_desc)?:" % re.escape(fid), l) for fid in removed)]
        if len(lines) != len(s.split("\n")):
            f.write_bytes(("\n".join(lines)).encode("utf-8-sig"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
