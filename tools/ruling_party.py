#!/usr/bin/env python3
"""지도자 교체 = 집권당 교체 (사양서 42).

HOI4 의 promote_character = { character = X ideology = Y } 는 X 를 Y 이념 정당의 지도자로 세운다.
그 정당이 집권당이 아니면 X 는 국가 지도자가 되지 않는다. 이제 나라마다 시작 이념이 달라서(민주·파시즘·공산·비동맹),
지도자를 바꾸는 줄마다 바로 앞에 set_politics 로 그 이념의 정당을 집권당으로 만든다.

fix_text(text) -> (new_text, 넣은 수)   바로 앞 세 줄 안에 set_politics 가 있으면 건너뛴다 (다시 돌려도 같다).
사용법 (모드 전체, python -I):  python -I tools/ruling_party.py
merge_focus.py (중점), content_lib.py (이벤트·디시전), hidden_routes.py (숨은 루트 이벤트)도 쓰기 전에 부른다.
"""

import re
import sys
from pathlib import Path

GROUP = {}
for g, subs in {
    "neutrality": ["despotism", "oligarchism", "moderatism", "centrism", "anarchism"],
    "democratic": ["conservatism", "liberalism", "socialism"],
    "communism": ["marxism", "leninism", "stalinism", "anti_revisionism", "anarchist_communism"],
    "fascism": ["nazism", "fascism_ideology", "gen_nazism", "falangism", "rexism"],
    "imperial_house": ["tu_imperial_rule", "tu_imperial_regency"],
    "sui": ["tu_sui_council", "tu_sui_rule", "tu_sui_awakening"],
}.items():
    for s in subs:
        GROUP[s] = g

PROMOTE = re.compile(r"(^|\n)([ \t]*)(promote_character = \{\s*character = \w+\s*ideology = (\w+)\s*\})")


def fix_text(text):
    out, pos, n = [], 0, 0
    for m in PROMOTE.finditer(text):
        g = GROUP.get(m.group(4))
        start = m.start(2)
        before = text[max(0, start - 400):start].rstrip().split("\n")[-3:]
        if g is None or any("set_politics" in l for l in before):
            continue
        ind = m.group(2)
        line = "%sset_politics = { ruling_party = %s elections_allowed = %s }\n" % (
            ind, g, "yes" if g == "democratic" else "no")
        out.append(text[pos:start])
        out.append(line)
        pos = start
        n += 1
    out.append(text[pos:])
    return "".join(out), n


def fix_file(path):
    raw = Path(path).read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    s = raw.decode("utf-8-sig")
    crlf = "\r\n" in s
    t, n = fix_text(s.replace("\r\n", "\n"))
    if n:
        if crlf:
            t = t.replace("\n", "\r\n")
        Path(path).write_bytes((("﻿" if bom else "") + t).encode("utf-8"))
    return n


def main():
    mod = Path(__file__).resolve().parents[1] / "terra_universalis"
    total = 0
    for p in sorted(list((mod / "common").rglob("*.txt")) + list((mod / "events").rglob("*.txt"))):
        n = fix_file(p)
        if n:
            print("%3d %s" % (n, p.relative_to(mod)))
        total += n
    print("RULING_PARTY inserted=%d" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
