#!/usr/bin/env python3
"""빅토리아 시작 상태 (사양서 80): 론디니움 사변.

시작 때 수도 론디니움(117번 주)은 카즈델 군사위원회가 점거했다. 빅토리아 수도는 글래스고로 옮긴다.
    117번 주   소유 카즈델 (핵심은 빅토리아 그대로: 되찾으면 평화 회담 없이 편입). 공장은 점거로 넘어간 기본 몫(민간 2 · 군수 1)만 남기고
              빅토리아 체급 몫과 공군 기지는 뺀다.
    글래스고   론디니움 북쪽 빅토리아 주 한 곳. 새 수도: 공군 기지 1 (공장은 tiers.py 가 체급 몫으로 넣는다).
    capital_overrides.json 에 적어 build_countries.py 가 수도로 쓴다. tiers.py 는 점거된 주를 체급 분배에서 뺀다 (OCCUPIED).
다시 돌려도 같다. build_countries.py 와 tiers.py 보다 먼저 돌린다.

사용법 (python -I):  python -I tools/mapgen/vic_start.py
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MOD = REPO / "terra_universalis"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tiers  # noqa: E402

LONDINIUM = 117
OVERRIDES = REPO / "tools" / "mapgen" / "terra" / "capital_overrides.json"


def center(st, G, s):
    _, x, y = G[st[s]["prov"]]
    return x, y


def glasgow(st, G):
    lx, ly = center(st, G, LONDINIUM)
    vic = [s for s, d in st.items() if (d["owner"] == "VIC" or s == LONDINIUM) and not d["impassable"] and s != LONDINIUM]
    # 론디니움 바로 북쪽으로 세 칸쯤 (픽셀 110): 그 점에 가장 가까운 빅토리아 주
    return min(vic, key=lambda s: (center(st, G, s)[0] - lx) ** 2 + (center(st, G, s)[1] - (ly - 110)) ** 2)


def rewrite(path, fn):
    t = path.read_text(encoding="utf-8-sig")
    n = fn(t)
    if n != t:
        path.write_text(n, encoding="utf-8")


def main():
    st = tiers.load_states()
    G = tiers.province_geo()
    gl = json.loads(OVERRIDES.read_text())["VIC"] if OVERRIDES.is_file() else glasgow(st, G)
    OVERRIDES.write_text(json.dumps({"VIC": gl}, indent=1) + "\n")

    def lon(t):
        t = re.sub(r"owner\s*=\s*\w+", "owner = KZD", t, count=1)
        t = re.sub(r"\n[ \t]*add_extra_state_shared_building_slots\s*=\s*\d+", "", t)
        t = re.sub(r"(industrial_complex\s*=\s*)\d+", r"\g<1>2", t)
        t = re.sub(r"(arms_factory\s*=\s*)\d+", r"\g<1>1", t)
        t = re.sub(r"\n[ \t]*air_base\s*=\s*\d+", "", t)
        t = re.sub(r"(manpower\s*=\s*)\d+", r"\g<1>800000", t, count=1)      # 점거된 도시의 인구 (tiers.py 가 분배에서 뺀다)
        return t
    rewrite(MOD / "history" / "states" / ("%d-STATE_%d.txt" % (LONDINIUM, LONDINIUM)), lon)

    def newcap(t):
        if re.search(r"\bair_base\s*=", t):
            return t
        m = re.search(r"(\n[ \t]*)buildings\s*=\s*\{", t)
        return t[:m.end()] + "%s\tair_base = 1" % m.group(1) + t[m.end():]
    rewrite(MOD / "history" / "states" / ("%d-STATE_%d.txt" % (gl, gl)), newcap)
    f = MOD / "history" / "countries" / "VIC - Victoria.txt"
    rewrite(f, lambda t: re.sub(r"^capital\s*=\s*\d+", "capital = %d" % gl, t, count=1, flags=re.M))
    print("VIC_START 런던 %d -> KZD, 수도 글래스고 = 주 %d" % (LONDINIUM, gl))
    return 0


if __name__ == "__main__":
    sys.exit(main())
