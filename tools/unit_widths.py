#!/usr/bin/env python3
"""대대 기본 전투 폭 바꾸기 (사양서 45).

사용자 요구: 보병 1, 기병 1, 포병 4, 전차 4 (계열 포함).
원본: reference/vanilla_units/*.txt (사용자가 올린 바닐라 common/units 파일).
출력: terra_universalis/common/units/<같은 파일 이름>  (바닐라 파일을 이름으로 덮어쓴다)
WIDTH 에 있는 대대가 하나라도 든 파일만 복사하고, 그 대대 블록의 combat_width 줄만 바꾼다. 나머지 내용은 원본 그대로.

사용법 (python -I):  python -I tools/unit_widths.py
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "reference" / "vanilla_units"
OUT = REPO / "terra_universalis" / "common" / "units"

INFANTRY = ["infantry", "bicycle_battalion", "marine", "marine_commando", "mountaineers", "ranger_battalion",
            "paratrooper", "motorized", "mechanized", "penal_battalion", "irregular_infantry", "militia",
            "amphibious_mechanized", "hq_infantry", "hq_motorized", "hq_paratrooper"]
CAVALRY = ["cavalry", "camelry"]
ARTILLERY = ["artillery_brigade", "mot_artillery_brigade", "rocket_artillery_brigade", "mot_rocket_artillery_brigade",
             "motorized_rocket_brigade"]
ARMOR = ["light_armor", "medium_armor", "heavy_armor", "modern_armor",
         "amphibious_armor", "amphibious_light_armor", "amphibious_medium_armor", "amphibious_heavy_armor",
         "hq_light_armor", "hq_medium_armor", "hq_heavy_armor"] + \
        ["%s_%s" % (w, k) for k in ("tank_destroyer_brigade", "sp_artillery_brigade", "sp_anti_air_brigade")
         for w in ("light", "medium", "heavy", "modern")]
WIDTH = {**{u: 1 for u in INFANTRY + CAVALRY}, **{u: 4 for u in ARTILLERY + ARMOR}}


def blocks(s):
    """sub_units 바로 아래 대대 블록: (이름, 여는 괄호 위치, 닫는 괄호 위치)."""
    out = []
    for m in re.finditer(r"^\t(\w+)\s*=\s*\{", s, re.M):
        j = s.index("{", m.start())
        d, k = 0, j
        while True:
            d += {"{": 1, "}": -1}.get(s[k], 0)
            if d == 0:
                break
            k += 1
        out.append((m.group(1), j, k))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    done = {}
    for f in sorted(SRC.glob("*.txt")):
        raw = f.read_bytes()
        bom = raw.startswith(b"\xef\xbb\xbf")
        s = raw.decode("utf-8-sig")
        hits = [(n, j, k) for n, j, k in blocks(s) if n in WIDTH]
        if not hits:
            continue
        for n, j, k in reversed(hits):
            body = s[j:k]
            new, c = re.subn(r"(\n[ \t]*combat_width\s*=\s*)[\d.]+", lambda m: m.group(1) + str(WIDTH[n]), body, count=1)
            assert c == 1, (f.name, n)
            s = s[:j] + new + s[k:]
            done[n] = (f.name, WIDTH[n])
        (OUT / f.name).write_bytes((("﻿" if bom else "") + s).encode("utf-8"))
        print("%-28s %s" % (f.name, ", ".join("%s=%d" % (n, WIDTH[n]) for n, _, _ in hits)))
    missing = sorted(set(WIDTH) - set(done))
    assert not missing, "원본에 없는 대대: %s" % missing
    print("UNIT_WIDTHS units=%d files=%d" % (len(done), len({v[0] for v in done.values()})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
