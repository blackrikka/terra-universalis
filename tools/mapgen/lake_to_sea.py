#!/usr/bin/env python3
"""내해 만들기 (사양서 26). 지도 생성(mapgen) 뒤, fix_exclaves.py 앞에 돌린다.

사용법:  python -I tools/mapgen/lake_to_sea.py [--dry]

extract_masks.py 는 바깥 바다와 이어지지 않은 물을 모두 호수로 만든다. 원작에서 바다인 내해(클라리사이드)는
호수로 두면 해협 연결의 Through 로 쓸 수 없어 안의 섬을 이을 수 없다. INLAND_SEAS 의 좌표가 가리키는 호수 덩어리를
바다로 바꾼다. 이미 바다면 아무것도 하지 않는다.

1. definition.csv: 호수 -> sea / ocean / 대륙 0, coastal 플래그 다시 계산 (validate_map 7번 규칙)
2. terrain.bmp: lakes(14) -> ocean(15)
3. unitstacks.txt: 바다 프로빈스마다 type 0~38 (호수에는 없다)
4. buildings.txt: 새로 해안이 된 육지 프로빈스에 해안 건물 위치, 새로 해안이 된 주에 dockyard 위치 (mapgen.py 와 같은 규칙)
전략 지역은 바다·호수 형식이 같아 그대로 쓴다. 내해 프로빈스가 다른 프로빈스와 같은 전략 지역에 섞여 있으면 멈춘다.
"""

import argparse
import io
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
MOD = REPO / "terra_universalis"

# (이름, 게임 픽셀 col, row). 클라리사이드 = extract_masks.LAKE_SEEDS 첫 번째 (430, 780) 를 게임 좌표로 옮긴 곳
INLAND_SEAS = [("Clariside", 1321, 2417)]

TERRAIN_LAKES, TERRAIN_OCEAN = 14, 15            # mapgen.TERRAIN_PIXEL
WATER_Y_MIN = 9.5                               # mapgen.WATER_Y_MIN
COASTAL_BUILDINGS = ["coastal_bunker", "naval_base_spawn", "naval_headquarters", "naval_supply_hub", "floating_harbor"]
UNIT_TYPES = range(0, 39)


def load_defs():
    rows, colour = {}, {}
    order = []
    for line in (MOD / "map" / "definition.csv").read_text(encoding="ascii").splitlines():
        f = line.split(";")
        if len(f) < 8 or not f[0].isdigit():
            continue
        pid = int(f[0])
        order.append(pid)
        rows[pid] = f
        if pid:
            colour[(int(f[1]) << 16) | (int(f[2]) << 8) | int(f[3])] = pid
    return order, rows, colour


def id_map(colour):
    img = np.asarray(Image.open(MOD / "map" / "provinces.bmp").convert("RGB")).astype(np.int64)
    key = (img[:, :, 0] << 16) | (img[:, :, 1] << 8) | img[:, :, 2]
    keys = np.array(sorted(colour), dtype=np.int64)
    vals = np.array([colour[k] for k in keys], dtype=np.int64)
    idx = np.searchsorted(keys, key)
    if not np.all(keys[np.clip(idx, 0, keys.size - 1)] == key):
        raise SystemExit("provinces.bmp 에 definition.csv 에 없는 색이 있다")
    return vals[idx]


def adjacency(ids):
    adj = defaultdict(set)
    for a, b in ((ids[:, :-1], ids[:, 1:]), (ids[:-1, :], ids[1:, :])):
        d = a != b
        for x, y in set(zip(a[d].tolist(), b[d].tolist())):
            adj[x].add(y)
            adj[y].add(x)
    return adj


def pole_pixel(ids, pid):
    """프로빈스 경계에서 가장 먼 픽셀 (4방향 침식 횟수가 가장 큰 픽셀)."""
    ys, xs = np.nonzero(ids == pid)
    y0, x0 = ys.min(), xs.min()
    m = np.zeros((ys.max() - y0 + 3, xs.max() - x0 + 3), bool)
    m[ys - y0 + 1, xs - x0 + 1] = True
    depth = np.zeros(m.shape, np.int32)
    cur = m.copy()
    while cur.any():
        depth += cur
        cur = cur & np.roll(cur, 1, 0) & np.roll(cur, -1, 0) & np.roll(cur, 1, 1) & np.roll(cur, -1, 1)
    k = int(np.argmax(depth))
    ky, kx = divmod(k, m.shape[1])
    return y0 + ky - 1, x0 + kx - 1


def save_8bit_bmp(im, path):
    """mapgen.save_8bit_bmp 와 같다: biClrUsed, biClrImportant 를 0으로."""
    im.save(path, "BMP")
    raw = bytearray(path.read_bytes())
    raw[46:54] = b"\x00" * 8
    path.write_bytes(bytes(raw))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    order, rows, colour = load_defs()
    ids = id_map(colour)
    H, W = ids.shape
    adj = adjacency(ids)
    kind = {p: rows[p][4] for p in order if p}

    convert = set()
    for name, col, row in INLAND_SEAS:
        seed = int(ids[row, col])
        if kind[seed] == "sea":
            print("%s: 이미 바다 (프로빈스 %d)" % (name, seed))
            continue
        if kind[seed] != "lake":
            raise SystemExit("%s: 좌표 (%d, %d) 의 프로빈스 %d 는 %s" % (name, col, row, seed, kind[seed]))
        comp, stack = {seed}, [seed]
        while stack:
            x = stack.pop()
            for y in adj[x]:
                if kind.get(y) == "lake" and y not in comp:
                    comp.add(y)
                    stack.append(y)
        print("%s: 호수 프로빈스 %d개 -> 바다" % (name, len(comp)))
        convert |= comp
    if not convert:
        return 0

    # 전략 지역: 내해 프로빈스만 들어 있어야 한다
    for f in (MOD / "map" / "strategicregions").glob("*.txt"):
        ps = set(int(x) for x in re.search(r"provinces\s*=\s*\{([^}]*)\}", f.read_text(encoding="utf-8-sig")).group(1).split())
        if ps & convert and ps - convert:
            raise SystemExit("%s 에 내해와 다른 프로빈스가 섞여 있다" % f.name)

    old_coastal = {p: rows[p][5] == "true" for p in kind}
    for p in convert:
        kind[p] = "sea"
    touched = set(convert) | {q for p in convert for q in adj[p]}
    new_coast = []
    for p in sorted(touched):
        if kind[p] == "sea":
            c = any(kind[q] != "sea" for q in adj[p])
        else:
            c = any(kind[q] == "sea" for q in adj[p])
        rows[p][5] = "true" if c else "false"
        if kind[p] == "land" and c and not old_coastal[p]:
            new_coast.append(p)
    for p in convert:
        rows[p][4], rows[p][6], rows[p][7] = "sea", "ocean", "0"
    print("새 해안 육지 프로빈스: %d" % len(new_coast))
    if a.dry:
        return 0

    # definition.csv 는 맨 마지막에 쓴다: 중간에 실패해도 다시 돌리면 처음부터 다시 한다 (이미 바다인지 여기로 판정하므로)
    mask = np.isin(ids, sorted(convert))
    # 바이트로 읽어서 연다: 파일 이름으로 열면 Pillow 가 BMP 를 메모리 매핑해 Windows 에서 같은 파일에 쓸 수 없다
    tim = Image.open(io.BytesIO((MOD / "map" / "terrain.bmp").read_bytes()))
    arr = np.asarray(tim).copy()
    palette = tim.getpalette()
    arr[mask & (arr == TERRAIN_LAKES)] = TERRAIN_OCEAN
    out = Image.fromarray(arr, "P")
    out.putpalette(palette)
    save_8bit_bmp(out, MOD / "map" / "terrain.bmp")

    with Image.open(MOD / "map" / "heightmap.bmp") as him:
        height = np.asarray(him.convert("L")).astype(np.float64)
    is_sea = np.isin(ids, [p for p in kind if kind[p] == "sea"])

    def pos_text(row, col):
        h = height[row, col] / 10.0
        y = max(WATER_Y_MIN, h) if is_sea[row, col] else h
        return "%.2f;%.2f;%.2f" % (col, y, H - 1 - row)

    upath = MOD / "map" / "unitstacks.txt"
    units = [l for l in upath.read_text(encoding="ascii").splitlines() if l.strip()]
    for p in sorted(convert):
        pt = pos_text(*pole_pixel(ids, p))
        units += ["%d;%d;%s;0.00;0.00" % (p, t, pt) for t in UNIT_TYPES]
    upath.write_text("\n".join(units) + "\n", encoding="ascii")

    # 해안 건물 위치
    p2s = {}
    for f in (MOD / "history" / "states").glob("*.txt"):
        t = f.read_text(encoding="utf-8-sig")
        sid = int(re.search(r"\bid\s*=\s*(\d+)", t).group(1))
        for x in re.search(r"provinces\s*=\s*\{([^}]*)\}", t).group(1).split():
            p2s[int(x)] = sid
    bpath = MOD / "map" / "buildings.txt"
    blines = [l for l in bpath.read_text(encoding="ascii").splitlines() if l.strip()]
    has_dock = {int(l.split(";")[0]) for l in blines if l.split(";")[1] == "dockyard"}
    sea_px = np.isin(ids, sorted(convert))

    def coast_pixels(p):
        ys, xs = np.nonzero(ids == p)
        out = []
        for y, x in zip(ys.tolist(), xs.tolist()):
            for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and sea_px[ny, nx]:
                    out.append((y, x, int(ids[ny, nx])))
                    break
        return out, ys.mean(), xs.mean()

    by_state = defaultdict(list)
    for p in new_coast:
        cpix, cy, cx = coast_pixels(p)
        y, x, sea = min(cpix, key=lambda t: ((t[0] - cy) ** 2 + (t[1] - cx) ** 2, t))
        sid = p2s[p]
        blines += ["%d;%s;%s;0.00;%d" % (sid, name, pos_text(y, x), sea) for name in COASTAL_BUILDINGS]
        by_state[sid].extend(cpix)
    docks = 0
    for sid, cpix in sorted(by_state.items()):
        if sid in has_dock:
            continue
        sy, sx = np.nonzero(np.isin(ids, [p for p, s in p2s.items() if s == sid]))
        cy, cx = sy.mean(), sx.mean()
        y, x, sea = min(cpix, key=lambda t: ((t[0] - cy) ** 2 + (t[1] - cx) ** 2, t))
        blines.append("%d;dockyard;%s;0.00;%d" % (sid, pos_text(y, x), sea))
        docks += 1
    blines.sort(key=lambda l: int(l.split(";")[0]))
    bpath.write_text("\n".join(blines) + "\n", encoding="ascii")
    (MOD / "map" / "definition.csv").write_text("\n".join(";".join(rows[p]) for p in order) + "\n", encoding="ascii")
    print("unitstacks +%d, 해안 건물 위치 +%d, dockyard 위치 +%d" % (
        len(convert) * len(UNIT_TYPES), len(new_coast) * len(COASTAL_BUILDINGS), docks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
