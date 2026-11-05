#!/usr/bin/env python3
"""바다 전략 지역 끊김·너무 작은 프로빈스 고치기 (사양서 37). hex_coast.py 뒤, fix_exclaves.py 앞에 돌린다.

사용법:  python -I tools/mapgen/seal_sea_pockets.py [--dry]

바다 전략 지역이 끊어지면 게임이 지도를 읽다가 강제 종료된다 (-debug 로 켜면 "is fractioned" 오류만 낸다).
hex_coast.py 가 해안을 칸에 맞추면서 만이나 내해의 입구가 막히면 이런 조각이 생긴다.

1. 16픽셀보다 작은 프로빈스를 같은 종류의 이웃 픽셀로 키운다. 게임은 8픽셀 이하에 경고를 낸다.
2. 바다 전략 지역을 연결 성분으로 나눠 가장 큰 조각만 남긴다.
   - 다른 바다와 닿은 조각: 가장 많이 닿은 전략 지역으로 옮긴다.
   - 어떤 바다와도 닿지 않은 조각: 호수로 바꾸고 가장 가까운 호수 전략 지역으로 옮긴다.
3. 호수로 바꾼 뒤 정리: definition.csv, terrain.bmp, unitstacks.txt, 전체 coastal 플래그,
   buildings.txt (해안 건물과 dockyard 의 바다 id).

고칠 것이 없으면 아무것도 하지 않는다. 클라리사이드(지역 171)처럼 지역 전체가 내해인 곳은 끊긴 것이 아니라서 건드리지 않는다.
"""

import argparse
import io
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lake_to_sea import COASTAL_BUILDINGS, MOD, TERRAIN_LAKES, TERRAIN_OCEAN, adjacency, id_map, load_defs, save_8bit_bmp  # noqa: E402

MIN_PIXELS = 16       # 게임은 8픽셀 이하에 경고를 낸다. 여유를 둔다
REGIONS = MOD / "map" / "strategicregions"


def load_regions():
    regions, paths = {}, {}
    for f in sorted(REGIONS.glob("*.txt")):
        t = f.read_text(encoding="utf-8-sig")
        rid = int(re.search(r"\bid\s*=\s*(\d+)", t).group(1))
        regions[rid] = [int(x) for x in re.search(r"provinces\s*=\s*\{([^}]*)\}", t).group(1).split()]
        paths[rid] = f
    return regions, paths


def load_states():
    of = {}
    for f in (MOD / "history" / "states").glob("*.txt"):
        t = f.read_text(encoding="utf-8-sig")
        sid = int(re.search(r"\bid\s*=\s*(\d+)", t).group(1))
        for x in re.search(r"provinces\s*=\s*\{([^}]*)\}", t).group(1).split():
            of[int(x)] = sid
    return of


def components(ids, adj):
    left, out = set(ids), []
    while left:
        stack = [left.pop()]
        comp = set(stack)
        while stack:
            for n in adj[stack.pop()]:
                if n in left:
                    left.remove(n)
                    comp.add(n)
                    stack.append(n)
        out.append(comp)
    return sorted(out, key=lambda c: (-len(c), min(c)))


def grow_small(ids, kind, state_of):
    """작은 프로빈스를 같은 종류의 이웃 픽셀로 키운다. 같은 주를 먼저 쓰고, 충분히 큰 이웃만 쓴다."""
    H, W = ids.shape
    area = Counter(dict(zip(*[v.tolist() for v in np.unique(ids, return_counts=True)])))
    small = sorted((p for p in area if p and area[p] < MIN_PIXELS), key=lambda p: (area[p], p))
    for p in small:
        before = area[p]
        for _ in range(MIN_PIXELS * 4):
            if area[p] >= MIN_PIXELS:
                break
            ys, xs = np.nonzero(ids == p)
            cand = set()
            for y, x in zip(ys.tolist(), xs.tolist()):
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W:
                        q = int(ids[ny, nx])
                        if q != p and q and kind[q] == kind[p] and area[q] > MIN_PIXELS * 4:
                            cand.add((ny, nx, q))
            same_state = {c for c in cand if state_of.get(c[2]) == state_of.get(p)}
            cand = same_state or cand       # 같은 주를 먼저 쓴다. 픽셀만 넘어가고 프로빈스의 소속 주는 그대로다
            if not cand:
                break
            cy, cx = ys.mean(), xs.mean()
            for ny, nx, q in sorted(cand, key=lambda c: ((c[0] - cy) ** 2 + (c[1] - cx) ** 2, c)):
                if area[p] >= MIN_PIXELS:
                    break
                ids[ny, nx] = p
                area[q] -= 1
                area[p] += 1
        print("프로빈스 %d (%s): %d -> %d 픽셀" % (p, kind[p], before, area[p]))
        if area[p] < MIN_PIXELS:
            raise SystemExit("프로빈스 %d 를 %d 픽셀까지 키우지 못했다" % (p, MIN_PIXELS))
    return bool(small)


def heal_split(ids, kind):
    """픽셀을 내주다 쪼개진 프로빈스: 작은 조각을 같은 종류의 맞닿은 프로빈스로 넘긴다."""
    H, W = ids.shape
    changed = False
    for idx, sl in enumerate(ndimage.find_objects(ids)):
        if sl is None:
            continue
        p = idx + 1
        lab, n = ndimage.label(ids[sl] == p)
        if n < 2:
            continue
        sizes = ndimage.sum(lab > 0, lab, range(1, n + 1))
        keep = int(np.argmax(sizes)) + 1
        for k in range(1, n + 1):
            if k == keep:
                continue
            ys, xs = np.nonzero(lab == k)
            ys, xs = ys + sl[0].start, xs + sl[1].start
            votes = Counter()
            for y, x in zip(ys.tolist(), xs.tolist()):
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W:
                        q = int(ids[ny, nx])
                        if q != p and q and kind[q] == kind[p]:
                            votes[q] += 1
            if not votes:
                raise SystemExit("프로빈스 %d 의 조각을 넘길 이웃이 없다" % p)
            to = min(votes, key=lambda q: (-votes[q], q))
            ids[ys, xs] = to
            print("프로빈스 %d: 쪼개진 조각 %d 픽셀 -> 프로빈스 %d" % (p, ys.size, to))
            changed = True
    return changed


def fix_regions(regions, kind, adj, ids):
    """바다 지역을 연결 성분으로 나눈다. 돌려주는 값: (옮긴 프로빈스 -> 새 지역, 호수로 바꿀 프로빈스)."""
    region_of = {p: r for r, ps in regions.items() for p in ps}
    sea_regions = [r for r, ps in regions.items() if ps and all(kind[p] == "sea" for p in ps)]
    moved, convert = {}, set()
    pockets = []
    for _ in range(len(regions)):
        changed = False
        for rid in sea_regions:
            comps = components(regions[rid], adj)
            for comp in comps[1:]:
                votes = Counter()
                for p in comp:
                    for n in adj[p]:
                        if kind.get(n) == "sea" and region_of[n] != rid:
                            votes[region_of[n]] += 1
                if not votes:
                    if comp not in pockets:
                        pockets.append(comp)
                    continue
                to = min(votes, key=lambda r: (-votes[r], r))
                for p in comp:
                    regions[rid].remove(p)
                    regions[to].append(p)
                    region_of[p] = to
                    moved[p] = to
                print("지역 %d: 조각 %d개 프로빈스 -> 지역 %d" % (rid, len(comp), to))
                changed = True
        if not changed:
            break
    lake_regions = [r for r, ps in regions.items() if ps and all(kind[p] == "lake" for p in ps)]
    if pockets and not lake_regions:
        raise SystemExit("호수 전략 지역이 없다")
    centre = {}
    for r in lake_regions:
        ys, xs = np.nonzero(np.isin(ids, regions[r]))
        centre[r] = (ys.mean(), xs.mean())
    for comp in pockets:
        ys, xs = np.nonzero(np.isin(ids, sorted(comp)))
        y, x = ys.mean(), xs.mean()
        to = min(lake_regions, key=lambda r: ((centre[r][0] - y) ** 2 + (centre[r][1] - x) ** 2, r))
        for p in comp:
            regions[region_of[p]].remove(p)
            regions[to].append(p)
            region_of[p] = to
        convert |= comp
        print("고립된 조각: 프로빈스 %d개 (%s) -> 호수, 지역 %d" % (len(comp), sorted(comp)[:5], to))
    return moved, convert


def write_regions(regions, paths, touched):
    for rid in sorted(touched):
        f = paths[rid]
        raw = f.read_bytes()
        bom = raw.startswith(b"\xef\xbb\xbf")
        t = raw.decode("utf-8-sig")
        nl = "\r\n" if "\r\n" in t else "\n"
        body = "%s\t\t%s%s\t" % (nl, " ".join(str(p) for p in sorted(regions[rid])), nl)
        new = re.sub(r"(provinces\s*=\s*\{)[^}]*(\})", lambda m: m.group(1) + body + m.group(2), t, count=1)
        f.write_bytes((b"\xef\xbb\xbf" if bom else b"") + new.encode("utf-8"))


def fix_buildings(ids, kind, adj, convert, state_of):
    """호수가 된 바다를 가리키는 해안 건물·dockyard 를 다른 바다로 돌리거나 없앤다."""
    H = ids.shape[0]
    path = MOD / "map" / "buildings.txt"
    lines = [l for l in path.read_text(encoding="ascii").splitlines() if l.strip()]

    def province_at(f):
        return int(ids[H - 1 - int(round(float(f[4]))), int(round(float(f[2])))])

    def sea_of(p):
        seas = sorted(q for q in adj[p] if kind.get(q) == "sea")
        return seas[0] if seas else None

    out, dock_lost, redirected, removed = [], [], 0, 0
    for line in lines:
        f = line.split(";")
        if f[1] not in COASTAL_BUILDINGS and f[1] != "dockyard" or int(f[6]) not in convert:
            out.append(line)
            continue
        sea = sea_of(province_at(f))
        if sea is not None:
            f[6] = str(sea)
            out.append(";".join(f))
            redirected += 1
        elif f[1] == "dockyard":
            dock_lost.append(f)
        else:
            removed += 1
    # 해안을 잃은 dockyard: 같은 주의 남은 해안 건물 자리로 옮기고, 해안이 없는 주면 지운다
    spot = {}
    for line in out:
        f = line.split(";")
        if f[1] == "naval_base_spawn":
            spot.setdefault(int(f[0]), f)
    dock_moved = 0
    for f in dock_lost:
        s = spot.get(int(f[0]))
        if s:
            f[2:5], f[6] = s[2:5], s[6]
            out.append(";".join(f))
            dock_moved += 1
        else:
            removed += 1
    out.sort(key=lambda l: int(l.split(";")[0]))
    path.write_text("\n".join(out) + "\n", encoding="ascii")
    print("건물: 바다 id 변경 %d, dockyard 이동 %d, 삭제 %d" % (redirected, dock_moved, removed))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    order, rows, colour = load_defs()
    ids = id_map(colour).copy()
    kind = {p: rows[p][4] for p in order if p}
    state_of = load_states()

    grown = grow_small(ids, kind, state_of)
    grown = heal_split(ids, kind) or grown
    adj = adjacency(ids)
    regions, paths = load_regions()
    before = {r: sorted(ps) for r, ps in regions.items()}
    moved, convert = fix_regions(regions, kind, adj, ids)
    touched = {r for r, ps in regions.items() if sorted(ps) != before[r]}
    if not grown and not touched:
        print("고칠 것 없음")
        return 0
    print("옮긴 프로빈스 %d, 호수로 바꾼 프로빈스 %d, 고친 지역 %d" % (len(moved), len(convert), len(touched)))
    if a.dry:
        return 0

    for p in convert:
        kind[p] = "lake"
        rows[p][4], rows[p][6], rows[p][7] = "lake", "lakes", "0"
    changed_coast = 0
    for p in order:
        if not p:
            continue
        if kind[p] == "sea":
            c = any(kind[q] != "sea" for q in adj[p])
        elif kind[p] == "land":
            c = any(kind[q] == "sea" for q in adj[p])
        else:
            c = False
        v = "true" if c else "false"
        changed_coast += rows[p][5] != v
        rows[p][5] = v

    if grown:
        by_id = {p: (int(rows[p][1]), int(rows[p][2]), int(rows[p][3])) for p in order}
        lut = np.zeros((max(order) + 1, 3), np.uint8)
        for p, c in by_id.items():
            lut[p] = c
        Image.fromarray(lut[ids], "RGB").save(MOD / "map" / "provinces.bmp", "BMP")
    write_regions(regions, paths, touched)
    if convert:
        mask = np.isin(ids, sorted(convert))
        tim = Image.open(io.BytesIO((MOD / "map" / "terrain.bmp").read_bytes()))
        arr = np.asarray(tim).copy()
        palette = tim.getpalette()
        arr[mask & (arr == TERRAIN_OCEAN)] = TERRAIN_LAKES
        out = Image.fromarray(arr, "P")
        out.putpalette(palette)
        save_8bit_bmp(out, MOD / "map" / "terrain.bmp")
        upath = MOD / "map" / "unitstacks.txt"
        units = upath.read_text(encoding="ascii").splitlines()
        keep = [l for l in units if l.strip() and int(l.split(";")[0]) not in convert]
        upath.write_text("\n".join(keep) + "\n", encoding="ascii")
        print("unitstacks -%d" % (len(units) - len(keep)))
        fix_buildings(ids, kind, adj, convert, state_of)
    (MOD / "map" / "definition.csv").write_text("\n".join(";".join(rows[p]) for p in order) + "\n", encoding="ascii")
    print("coastal 플래그 변경 %d" % changed_coast)
    return 0


if __name__ == "__main__":
    sys.exit(main())
