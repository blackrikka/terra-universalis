#!/usr/bin/env python3
"""통행 가능한 주를 프로빈스 하나짜리 주로 나눈다 (사양서 49). 지도 후처리 맨 끝(fix_exclaves 뒤)에 돌린다.

사용법:  python -I tools/mapgen/split_states.py [--dry]
그다음:  rail_effects.py → tiers.py → content/ibe.py + merge_focus IBE → build_countries.py → validate_map.py

규칙
- 통행 불가(impassable) 주는 그대로 둔다 (황야 3,500여 프로빈스).
- 프로빈스가 둘 이상인 주: 원래 주 번호는 중심 프로빈스(승점 > state_index 의 center > 가장 작은 번호)에 남기고,
  나머지 프로빈스마다 새 주를 만든다 (번호는 지금 가장 큰 주 번호 + 1 부터, 프로빈스 번호 순).
  - 원래 주: 범주·건물(수도 공장 포함)·승점 그대로, 인력은 프로빈스 수로 나눈 몫.
  - 새 주: 범주 tu_hex (건설 슬롯 1, common/state_category/tu_hex.txt), 소유국·코어·인프라는 원래 주와 같고,
    인력은 나눈 몫, 승점 없음.
- map/buildings.txt: 프로빈스 단위 건물 위치의 주 번호를 고치고, 나뉜 주의 주 단위 건물 위치(공장 등)와 조선소 위치는
  주마다 다시 만든다 (mapgen 과 같은 규칙).
- tools/mapgen/out/state_index.json, 로컬라이제이션 STATE_<id>, tools/mapgen/out/split_states.json(원래 주 -> 나뉜 주 목록)을 쓴다.
다시 돌려도 나눌 주가 없으면 아무것도 하지 않는다.
"""

import argparse
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mapgen  # noqa: E402
from hex_coast import load_defs, pid_map  # noqa: E402

REPO = HERE.parents[1]
MOD = REPO / "terra_universalis"
MAP = MOD / "map"
OUT = HERE / "out"
SEED = 1097
PIECE_CATEGORY = "tu_hex"


def parse_state(f):
    t = f.read_text(encoding="utf-8-sig")
    sid = int(re.search(r"\bid\s*=\s*(\d+)", t).group(1))
    provs = [int(x) for x in re.search(r"provinces\s*=\s*\{([^}]*)\}", t).group(1).split()]
    vp = [int(m.group(1)) for m in re.finditer(r"victory_points\s*=\s*\{\s*(\d+)", t)]
    return {"file": f, "text": t, "id": sid, "provinces": provs, "vp": vp,
            "impassable": bool(re.search(r"impassable\s*=\s*yes", t)),
            "owner": re.search(r"\bowner\s*=\s*(\w+)", t).group(1),
            "cores": re.findall(r"add_core_of\s*=\s*(\w+)", t),
            "claims": re.findall(r"add_claim_by\s*=\s*(\w+)", t),
            "manpower": int(re.search(r"\bmanpower\s*=\s*(\d+)", t).group(1)),
            "infra": re.search(r"infrastructure\s*=\s*(\d+)", t).group(1)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)

    states = {s["id"]: s for s in (parse_state(f) for f in (MOD / "history" / "states").glob("*.txt"))}
    si_path = OUT / "state_index.json"
    si = json.loads(si_path.read_text(encoding="utf-8"))
    center = {st["id"]: st.get("center") for st in si["states"]}
    todo = [s for s in states.values() if not s["impassable"] and len(s["provinces"]) > 1]
    if not todo:
        print("SPLIT_STATES: 나눌 주 없음")
        return 0
    next_id = max(states) + 1
    split = {}          # 원래 주 -> [원래 주, 새 주 ...]
    new_states = []     # (새 주 id, 원래 주, 프로빈스)
    core_of = {}
    for s in sorted(todo, key=lambda s: s["id"]):
        ps = s["provinces"]
        core = next((p for p in s["vp"] if p in ps), None) or (center.get(s["id"]) if center.get(s["id"]) in ps else None) or min(ps)
        core_of[s["id"]] = core
        ids = [s["id"]]
        for p in sorted(x for x in ps if x != core):
            new_states.append((next_id, s["id"], p))
            ids.append(next_id)
            next_id += 1
        split[s["id"]] = ids
    print("나눌 주 %d개 → 새 주 %d개 (주 %d → %d개)" % (len(todo), len(new_states), len(states), len(states) + len(new_states)))
    if a.dry:
        return 0

    # ---- history/states
    prov_state = {}
    for s in states.values():
        for p in s["provinces"]:
            prov_state[p] = s["id"]
    for s in todo:
        n = len(s["provinces"])
        mp = max(1000, s["manpower"] // n)
        t = s["text"]
        t = re.sub(r"(provinces\s*=\s*\{)[^}]*(\})", lambda m: "%s\n\t\t%d\n\t%s" % (m.group(1), core_of[s["id"]], m.group(2)), t, count=1)
        t = re.sub(r"(\bmanpower\s*=\s*)\d+", lambda m: m.group(1) + str(mp), t, count=1)
        s["file"].write_text(t, encoding="utf-8")
    ko, en = [], []
    for nid, old, p in new_states:
        s = states[old]
        mp = max(1000, s["manpower"] // len(s["provinces"]))
        L = ["state={", "\tid=%d" % nid, '\tname="STATE_%d"' % nid, "\tmanpower = %d" % mp, "",
             "\tstate_category = %s" % PIECE_CATEGORY, "", "\thistory={", "\t\towner = %s" % s["owner"],
             "\t\tbuildings = {", "\t\t\tinfrastructure = %s" % s["infra"], "\t\t}"]
        L += ["\t\tadd_core_of = %s" % c for c in s["cores"]]
        L += ["\t\tadd_claim_by = %s" % c for c in s["claims"]]
        L += ["\t}", "", "\tprovinces={", "\t\t%d" % p, "\t}", "\tlocal_supplies=0.0", "}"]
        mapgen.write_ascii(MOD / "history" / "states" / ("%d-STATE_%d.txt" % (nid, nid)), "\n".join(L) + "\n")
        prov_state[p] = nid
        ko.append(("STATE_%d" % nid, "주 %d" % nid))
        en.append(("STATE_%d" % nid, "State %d" % nid))
    for lang, items in (("korean", ko), ("english", en)):
        f = MOD / "localisation" / lang / "replace" / ("tu_map_l_%s.yml" % lang)
        s = f.read_bytes().decode("utf-8-sig").rstrip("\n")
        have = set(re.findall(r"^ (STATE_\d+):", s, re.M))
        s += "\n" + "".join(' %s:0 "%s"\n' % kv for kv in items if kv[0] not in have)
        f.write_bytes(("\ufeff" + s).encode("utf-8"))

    # ---- 범주 tu_hex
    cat = MOD / "common" / "state_category" / "tu_hex.txt"
    cat.parent.mkdir(parents=True, exist_ok=True)
    cat.write_text("# Terra hex state (tools/mapgen/split_states.py, spec 49): one province, one building slot.\n"
                   "state_categories = {\n\t%s = {\n\t\tcolor = { 150 170 120 }\n\t\tlocal_building_slots = 1\n\t}\n}\n"
                   % PIECE_CATEGORY, encoding="utf-8")
    for lang, name in (("korean", "헥스 지역"), ("english", "Hex Region")):
        f = MOD / "localisation" / lang / ("tu_state_category_l_%s.yml" % lang)
        f.write_bytes(("\ufeff" + "l_%s:\n %s:0 \"%s\"\n" % (lang, PIECE_CATEGORY, name)).encode("utf-8"))

    # ---- buildings.txt
    rows = load_defs()
    ptype = [r[4] for r in rows]
    coastal = [r[5] == "true" for r in rows]
    ids = pid_map(rows)
    H, W = ids.shape
    with Image.open(io.BytesIO((MAP / "heightmap.bmp").read_bytes())) as him:
        h_u8 = np.asarray(him.convert("L"))
    is_water = np.array([t in ("sea", "lake") for t in ptype])
    sea_px = np.array([t == "sea" for t in ptype])[ids]
    coast_px = ~is_water[ids] & ndimage.binary_dilation(sea_px)
    slices = ndimage.find_objects(ids)
    rng = np.random.default_rng(SEED)

    def pos(row, col):
        v = h_u8[row, col] / 10.0
        return "%.2f;%.2f;%.2f" % (col, v, H - 1 - row)

    def pix(x, z):
        return H - 1 - int(round(float(z))), int(round(float(x)))

    def sea_nb(row, col):
        for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            ny, nx = row + dy, col + dx
            if 0 <= ny < H and 0 <= nx < W and sea_px[ny, nx]:
                return int(ids[ny, nx])
        return 0

    STATE_T = {n for n, _ in mapgen.STATE_BUILDINGS}
    touched = set()
    for old, lst in split.items():
        touched.update(lst)
    out = []
    for l in (MAP / "buildings.txt").read_text(encoding="ascii").splitlines():
        if not l.strip():
            continue
        f = l.split(";")
        sid, typ = int(f[0]), f[1]
        if sid in touched and (typ in STATE_T or typ == mapgen.DOCKYARD):
            continue                           # 아래에서 주마다 다시 만든다
        if sid in split:
            row, col = pix(f[2], f[4])
            f[0] = str(prov_state[int(ids[row, col])])
            l = ";".join(f)
        out.append(l)
    nstate = 0
    for old, lst in sorted(split.items()):
        for sid in lst:
            p = core_of[old] if sid == old else next(pp for nid, o, pp in new_states if nid == sid)
            sl = slices[p - 1]
            sub = ids[sl] == p
            dist = ndimage.distance_transform_edt(np.pad(sub, 1))[1:-1, 1:-1]
            inner = np.nonzero(sub & (dist >= 2))
            if inner[0].size == 0:
                inner = np.nonzero(sub)
            ys, xs = inner[0] + sl[0].start, inner[1] + sl[1].start
            for name, cnt in mapgen.STATE_BUILDINGS:
                for _ in range(cnt):
                    k = int(rng.integers(ys.size))
                    out.append("%d;%s;%s;0.00;0" % (sid, name, pos(int(ys[k]), int(xs[k]))))
            if coastal[p] and ptype[p] == "land":
                cy, cx = np.nonzero(sub & coast_px[sl])
                if cy.size:
                    k = int(np.argmin((cy - cy.mean()) ** 2 + (cx - cx.mean()) ** 2))
                    row, col = int(cy[k]) + sl[0].start, int(cx[k]) + sl[1].start
                    out.append("%d;%s;%s;0.00;%d" % (sid, mapgen.DOCKYARD, pos(row, col), sea_nb(row, col)))
            nstate += 1
    mapgen.write_ascii(MAP / "buildings.txt", "\n".join(out))

    # ---- state_index.json
    area = np.bincount(ids.ravel(), minlength=len(rows))
    by_id = {st["id"]: st for st in si["states"]}
    for old in split:
        st = by_id[old]
        c = core_of[old]
        st.update(provinces=[c], center=c, area=int(area[c]), coastal=bool(coastal[c]))
    for nid, old, p in new_states:
        base = by_id[old]
        si["states"].append({"id": nid, "owner": base["owner"], "kind": base["kind"], "provinces": [p], "center": p,
                             "coastal": bool(coastal[p]), "area": int(area[p]), "region": base.get("region", 0)})
    si["states"].sort(key=lambda st: st["id"])
    si_path.write_text(json.dumps(si, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (OUT / "split_states.json").write_text(json.dumps({str(k): v for k, v in sorted(split.items())}, indent=1) + "\n",
                                           encoding="utf-8")
    print("SPLIT_STATES ok: 주 %d개 → %d개, 건물 위치 %d줄 (다시 만든 주 %d)" % (
        len(states), len(states) + len(new_states), len(out), nstate))
    return 0


if __name__ == "__main__":
    sys.exit(main())
