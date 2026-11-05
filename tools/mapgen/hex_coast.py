#!/usr/bin/env python3
"""해안선을 헥스 칸에 맞추기 (사양서 33). 지도 생성(mapgen) · lake_to_sea 뒤, fix_exclaves 앞에 돌린다.

사용법:  python -I tools/mapgen/hex_coast.py [--dry] [--vanilla <바닐라 또는 대체 폴더>]

mapgen 은 육지 안의 경계(국경·주·프로빈스)는 헥스 칸을 따르지만, 바다·호수와 육지의 경계(해안선)는 참고 지도의
픽셀 해안선을 그대로 쓴다. 그래서 해안의 칸은 육지와 물로 비스듬히 잘려 있다.
이 도구는 육지와 물이 섞인 칸마다 많은 쪽 하나로 칸 전체를 채운다 → 대륙·섬·호수 테두리가 헥스 모양이 된다.

규칙
1. 칸의 승자: 육지 픽셀 >= 물 픽셀이면 칸 안에서 가장 넓은 육지 프로빈스, 아니면 가장 넓은 물 프로빈스. 칸 전체가 승자가 된다.
2. 지키는 프로빈스 (없어지면 안 됨): 승점(VP), 이름 있는 주·정박지, 보급 기지, 철도. 다른 데서 남는 픽셀이 없으면
   그 프로빈스가 가장 넓게 있는 칸의 승자가 된다. 주·전략 지역이 프로빈스를 모두 잃게 되면 가장 넓은 것 하나를 지킨다.
   지킬 프로빈스 둘이 한 칸에서 부딪치거나, 결과가 아래 검사에 걸리는 칸은 그대로 둔다 (얼림).
3. 검사: 프로빈스 연결성, X-교차, 철도의 이웃 프로빈스 인접. 걸리면 관련 칸을 얼리고 처음부터 다시 정한다.
4. 사라진 프로빈스 번호는 맨 끝 번호의 프로빈스를 옮겨 메운다 (앞쪽 번호 = 손으로 쓴 참조는 그대로).
   주 번호는 바뀌지 않는다.
5. 고치는 파일: provinces.bmp, definition.csv(해안 플래그), terrain.bmp, heightmap.bmp, world_normal.bmp, rivers.bmp,
   trees.bmp, terrain/colormap_rgb_cityemissivemask_a.dds, history/states, strategicregions, buildings.txt, unitstacks.txt,
   weatherpositions.txt, supply_nodes.txt, railways.txt, adjacencies.csv, out/state_index.json, out/named_states.json.
그다음 seal_sea_pockets.py (끊어진 바다 지역·작은 프로빈스, 사양서 37) → fix_exclaves.py (해협·회랑 다시 계산) → rail_effects / tiers / build_countries → validate_map.
"""

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mapgen  # noqa: E402
from dds import write_dds  # noqa: E402

REPO = HERE.parents[1]
MOD = REPO / "terra_universalis"
MAP = MOD / "map"
OUT = HERE / "out"
CELLS = HERE / "terra" / "hexcells.png"
SEED = 1097
MAX_ROUNDS = 40


# ---------------------------------------------------------------- 읽기

def read_rgb(path):
    with Image.open(io.BytesIO(path.read_bytes())) as im:
        return np.asarray(im.convert("RGB")).astype(np.int64)


def load_defs():
    rows = []
    with open(MAP / "definition.csv", encoding="utf-8-sig") as fh:
        for r in csv.reader(fh, delimiter=";"):
            if len(r) >= 8 and r[0].isdigit():
                rows.append(r)
    rows.sort(key=lambda r: int(r[0]))
    assert [int(r[0]) for r in rows] == list(range(len(rows))), "definition.csv 번호가 연속이 아님"
    return rows


def pid_map(rows):
    rgb = read_rgb(MAP / "provinces.bmp")
    key = (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]
    keys = np.array([(int(r[1]) << 16) | (int(r[2]) << 8) | int(r[3]) for r in rows], np.int64)
    order = np.argsort(keys)
    pos = np.searchsorted(keys[order], key)
    pid = order[np.clip(pos, 0, len(keys) - 1)]
    assert (keys[pid] == key).all(), "provinces.bmp 에 definition.csv 에 없는 색"
    return pid.astype(np.int32)


def cell_map():
    c = read_rgb(CELLS)
    return ((c[..., 0] << 16) | (c[..., 1] << 8) | c[..., 2]).astype(np.int64)


def load_states():
    states = {}
    for f in sorted((MOD / "history" / "states").glob("*.txt")):
        t = f.read_text(encoding="utf-8-sig")
        sid = int(re.search(r"\bid\s*=\s*(\d+)", t).group(1))
        provs = [int(x) for x in re.search(r"provinces\s*=\s*\{([^}]*)\}", t).group(1).split()]
        vps = [int(m.group(1)) for m in re.finditer(r"victory_points\s*=\s*\{\s*(\d+)\s+[\d.]+\s*\}", t)]
        states[sid] = {"file": f, "text": t, "provinces": provs, "vps": vps}
    return states


def load_regions():
    regs = {}
    for f in sorted((MAP / "strategicregions").glob("*.txt")):
        t = f.read_text(encoding="utf-8-sig")
        rid = int(re.search(r"\bid\s*=\s*(\d+)", t).group(1))
        provs = [int(x) for x in re.search(r"provinces\s*=\s*\{([^}]*)\}", t).group(1).split()]
        regs[rid] = {"file": f, "text": t, "provinces": provs}
    return regs


def lines_of(name):
    return [l for l in (MAP / name).read_text(encoding="ascii").splitlines() if l.strip()]


# ---------------------------------------------------------------- 칸 결정

class Snap:
    def __init__(self, pid, cell, is_water, protected, groups):
        self.pid = pid
        self.is_water = is_water
        H, W = pid.shape
        flat_c = cell.ravel()
        flat_p = pid.ravel().astype(np.int64)
        w = is_water[flat_p]
        nc = int(flat_c.max()) + 1
        wc = np.bincount(flat_c, weights=w, minlength=nc)
        tc = np.bincount(flat_c, minlength=nc)
        partial = np.nonzero((wc > 0) & (wc < tc))[0]
        self.partial = set(partial.tolist())
        sel = np.isin(flat_c, partial)
        self.px_idx = np.nonzero(sel)[0]
        self.px_cell = flat_c[sel]
        self.px_pid = flat_p[sel]
        # 칸별 프로빈스 픽셀 수
        self.counts = defaultdict(Counter)
        pairs, n = np.unique(np.stack([self.px_cell, self.px_pid]), axis=1, return_counts=True)
        for (c, p), k in zip(pairs.T.tolist(), n.tolist()):
            self.counts[c][p] = k
        # 칸 밖(섞이지 않은 칸)에 픽셀이 있는 프로빈스
        rest = np.bincount(flat_p[~sel], minlength=len(is_water))
        self.has_rest = rest > 0
        self.total = np.bincount(flat_p, minlength=len(is_water))
        self.cells_of = defaultdict(list)
        for c, cnt in self.counts.items():
            for p in cnt:
                self.cells_of[p].append(c)
        self.protected = set(protected)
        self.groups = groups          # [(이름, [프로빈스])] 주·전략 지역: 하나는 남아야 한다

    def default_winner(self, c):
        cnt = self.counts[c]
        land = sum(k for p, k in cnt.items() if not self.is_water[p])
        water = sum(k for p, k in cnt.items() if self.is_water[p])
        want_water = water > land
        cand = [(k, -p, p) for p, k in cnt.items() if bool(self.is_water[p]) == want_water]
        return max(cand)[2]

    def decide(self, frozen):
        win = {c: self.default_winner(c) for c in self.partial if c not in frozen}
        forced = {}
        protected = set(self.protected)
        for _ in range(100):
            alive = self.alive(win, frozen)
            changed = False
            for name, members in self.groups:
                if not any(alive[p] for p in members):
                    protected.add(max(members, key=lambda p: (self.total[p], -p)))
            for p in sorted(protected):
                if alive[p]:
                    continue
                c = max(self.cells_of[p], key=lambda c: (self.counts[c][p], -c))
                if c in frozen:
                    continue
                if c in forced and forced[c] != p:
                    frozen.add(c)
                    win.pop(c, None)
                    forced.pop(c, None)
                else:
                    win[c] = p
                    forced[c] = p
                changed = True
            if not changed:
                return win
        raise SystemExit("지킬 프로빈스 결정이 끝나지 않음")

    def alive(self, win, frozen):
        alive = self.has_rest.copy()
        for c in frozen:
            for p in self.counts.get(c, {}):
                alive[p] = True
        for p in win.values():
            alive[p] = True
        return alive

    def apply(self, win):
        new = self.pid.copy().ravel()
        wc = np.array([win.get(c, -1) for c in self.px_cell.tolist()], np.int64)
        m = wc >= 0
        new[self.px_idx[m]] = wc[m]
        return new.reshape(self.pid.shape)


def x_crosses(lab):
    a, b, c, d = lab[:-1, :-1], lab[:-1, 1:], lab[1:, :-1], lab[1:, 1:]
    cross = (a != b) & (a != c) & (a != d) & (b != c) & (b != d) & (c != d)
    return list(zip(*np.nonzero(cross)))


def adjacency_pairs(lab):
    a = np.concatenate([lab[:, :-1].ravel(), lab[:-1, :].ravel()]).astype(np.int64)
    b = np.concatenate([lab[:, 1:].ravel(), lab[1:, :].ravel()]).astype(np.int64)
    m = a != b
    lo, hi = np.minimum(a[m], b[m]), np.maximum(a[m], b[m])
    n = int(lab.max()) + 1
    keys = np.unique(lo * n + hi)
    adj = defaultdict(set)
    for k in keys.tolist():
        x, y = divmod(k, n)
        adj[x].add(y)
        adj[y].add(x)
    return adj


# ---------------------------------------------------------------- 본체

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--vanilla", default=None)
    a = ap.parse_args(argv)

    rows = load_defs()
    N = len(rows) - 1
    ptype = [r[4] for r in rows]
    is_water = np.array([t in ("sea", "lake") for t in ptype])
    pid = pid_map(rows)
    H, W = pid.shape
    cell = cell_map()
    assert cell.shape == pid.shape
    states = load_states()
    regions = load_regions()
    rails = [[int(x) for x in l.split()] for l in lines_of("railways.txt")]
    supply = [int(l.split()[1]) for l in lines_of("supply_nodes.txt")]
    named = json.loads((OUT / "named_states.json").read_text(encoding="utf-8"))
    pinned = json.loads((HERE / "terra" / "pinned_ids.json").read_text(encoding="ascii"))["pinned"]

    protected = set(supply)
    for st in states.values():
        protected.update(st["vps"])
    for r in rails:
        protected.update(r[2:])
    for e in named.get("named", []) + named.get("anchors", []):
        if "province" in e:
            protected.add(int(e["province"]))
    for sid_pid in pinned.values():
        protected.add(int(sid_pid[1]))
    groups = [("state %d" % s, st["provinces"]) for s, st in states.items()]
    groups += [("region %d" % r, rg["provinces"]) for r, rg in regions.items()]

    snap = Snap(pid, cell, is_water, protected, groups)
    print("섞인 칸 %d개 (육지+물), 지킬 프로빈스 %d개" % (len(snap.partial), len(protected)))

    frozen = set()
    for rnd in range(1, MAX_ROUNDS + 1):
        win = snap.decide(frozen)
        new = snap.apply(win)
        bad_cells = set()
        # 프로빈스 연결성 (바뀐 칸에 걸친 프로빈스만)
        touched = set()
        for c, w in win.items():
            touched.update(snap.counts[c])
        slices = ndimage.find_objects(new + 0)
        for p in sorted(touched):
            sl = slices[p - 1] if p - 1 < len(slices) else None
            if sl is None:
                continue
            _, n = ndimage.label(new[sl] == p)
            if n > 1:
                bad_cells.update(c for c in snap.cells_of[p] if c in win)
        # X-교차
        for y, x in x_crosses(new):
            for dy in (0, 1):
                for dx in (0, 1):
                    c = int(cell[y + dy, x + dx])
                    if c in win:
                        bad_cells.add(c)
        # 철도 인접
        adj = adjacency_pairs(new)
        for r in rails:
            for u, v in zip(r[2:], r[3:]):
                if v not in adj[u]:
                    bad_cells.update(c for c in snap.cells_of[u] + snap.cells_of[v] if c in win)
        print("라운드 %d: 바꿀 칸 %d, 얼린 칸 %d, 문제 칸 %d" % (rnd, len(win), len(frozen), len(bad_cells)))
        if not bad_cells:
            break
        frozen |= bad_cells
    else:
        raise SystemExit("검사를 통과하는 결정을 찾지 못함")

    changed = new != pid
    gone = sorted(set(np.nonzero(snap.total)[0].tolist()) - set(np.unique(new).tolist()) - {0})
    land_gain = int((changed & is_water[pid] & ~is_water[new]).sum())
    water_gain = int((changed & ~is_water[pid] & is_water[new]).sum())
    print("바뀐 픽셀 %d (물→육지 %d, 육지→물 %d), 없어진 프로빈스 %d (육지 %d, 물 %d)" % (
        int(changed.sum()), land_gain, water_gain, len(gone),
        sum(1 for p in gone if not is_water[p]), sum(1 for p in gone if is_water[p])))
    hit = sorted(set(gone) & protected)
    assert not hit, "지킬 프로빈스가 없어짐: %s" % hit[:10]
    if a.dry:
        return 0

    # ---- 번호 다시 매기기: 빈 번호를 맨 끝 번호로 메운다
    gone_set = set(gone)
    remap = {p: p for p in range(N + 1) if p not in gone_set}
    top = N
    for h in gone:
        while top in gone_set:
            top -= 1
        if top <= h:
            break
        remap[top] = h
        remap.pop(h, None)
        gone_set.add(top)       # top 은 h 로 옮겨 갔다
        top -= 1
    newN = N - len(gone)
    assert sorted(remap.values()) == list(range(newN + 1)), "번호 다시 매기기 실패"
    lut = np.zeros(N + 1, np.int32)
    for o, n_ in remap.items():
        lut[o] = n_
    old_pid = pid
    ids = lut[new]
    moved = {o: n_ for o, n_ in remap.items() if o != n_}
    print("번호 옮김 %d개 (%d → %d개)" % (len(moved), N, newN))

    def R(p):
        return remap.get(p)

    new_rows = [None] * (newN + 1)
    for o, n_ in remap.items():
        r = list(rows[o])
        r[0] = str(n_)
        new_rows[n_] = r
    ntype = [r[4] for r in new_rows]
    nwater = np.array([t in ("sea", "lake") for t in ntype])
    adj = adjacency_pairs(ids)
    for p in range(1, newN + 1):
        nb = adj.get(p, set())
        if ntype[p] == "sea":
            c = any(ntype[q] != "sea" for q in nb)
        else:
            c = any(ntype[q] == "sea" for q in nb)
        new_rows[p][5] = "true" if c else "false"
    coastal = [False] + [new_rows[p][5] == "true" for p in range(1, newN + 1)]

    # ---- 그림 파일
    palette = np.array([[int(r[1]), int(r[2]), int(r[3])] for r in new_rows], np.uint8)
    Image.fromarray(palette[ids]).save(MAP / "provinces.bmp", "BMP")

    to_land = changed & is_water[old_pid] & ~is_water[new]
    to_water = changed & ~is_water[old_pid] & is_water[new]
    # terrain.bmp: 새 육지 = 그 프로빈스의 원래 지형 픽셀 중 가장 많은 것, 새 물 = ocean / lakes
    tim = Image.open(io.BytesIO((MAP / "terrain.bmp").read_bytes()))
    tarr = np.asarray(tim).copy()
    tpal = tim.getpalette()
    keep = ~changed & ~is_water[old_pid]
    # 프로빈스별 다수 지형 (빠르게: 바뀌지 않은 육지 픽셀에서)
    kp = old_pid[keep].astype(np.int64)
    kt = tarr[keep].astype(np.int64)
    pair = np.unique(kp * 256 + kt, return_counts=True)
    best = {}
    for k, n_ in zip(pair[0].tolist(), pair[1].tolist()):
        p, t = divmod(k, 256)
        if p not in best or n_ > best[p][0]:
            best[p] = (n_, t)
    ys, xs = np.nonzero(to_land)
    for y, x in zip(ys.tolist(), xs.tolist()):
        p = int(new[y, x])
        tarr[y, x] = best[p][1] if p in best else mapgen.TERRAIN_PIXEL["plains"]
    lake_px = np.array([t == "lake" for t in ptype])[new]
    tarr[to_water & lake_px] = mapgen.TERRAIN_PIXEL["lakes"]
    tarr[to_water & ~lake_px] = mapgen.TERRAIN_PIXEL["ocean"]
    timg = Image.fromarray(tarr, "P")
    timg.putpalette(tpal)
    mapgen.save_8bit_bmp(timg, MAP / "terrain.bmp")

    # heightmap: 새 육지 = 그 프로빈스 육지 높이의 중앙값, 새 물 = 해안 바다 높이. 바뀐 곳 둘레만 부드럽게 한 뒤 육지/물 한계를 지킨다
    with Image.open(io.BytesIO((MAP / "heightmap.bmp").read_bytes())) as him:
        hmode = him.mode
        hpal = him.getpalette() if him.mode == "P" else None
        h = np.asarray(him.convert("L")).astype(np.float64)
    med = ndimage.median(h, labels=np.where(keep, old_pid, 0), index=np.unique(new[to_land]))
    medmap = dict(zip(np.unique(new[to_land]).tolist(), np.atleast_1d(med).tolist()))
    for y, x in zip(ys.tolist(), xs.tolist()):
        h[y, x] = max(medmap.get(int(new[y, x]), 100.0), mapgen.LAND_MIN + 2)
    h[to_water & lake_px] = mapgen.LAKE_HEIGHT
    h[to_water & ~lake_px] = mapgen.SEA_HEIGHT_COAST - 2
    near = ndimage.binary_dilation(changed, iterations=4)
    hb = ndimage.gaussian_filter(h, sigma=mapgen.HEIGHT_BLUR, mode="nearest")
    h = np.where(near, hb, h)
    land_px = ~nwater[ids]
    h = np.where(land_px, np.maximum(h, mapgen.LAND_MIN), np.minimum(h, mapgen.WATER_MAX))
    h_u8 = np.clip(np.rint(h), 0, 255).astype(np.uint8)
    if hmode == "P":
        hi = Image.fromarray(h_u8, "P")
        hi.putpalette(hpal)
        mapgen.save_8bit_bmp(hi, MAP / "heightmap.bmp")
    else:
        Image.fromarray(h_u8).save(MAP / "heightmap.bmp", "BMP")
    Image.fromarray(mapgen.compute_normal_map(h_u8)).save(MAP / "world_normal.bmp", "BMP")

    # rivers.bmp (mapgen: 육지 255, 물 254) / trees.bmp (숲·밀림 지형)
    rim = Image.open(io.BytesIO((MAP / "rivers.bmp").read_bytes()))
    rarr = np.asarray(rim).copy()
    rarr[to_land] = 255
    rarr[to_water] = 254
    ri = Image.fromarray(rarr, "P")
    ri.putpalette(rim.getpalette())
    mapgen.save_8bit_bmp(ri, MAP / "rivers.bmp")
    trim = Image.open(io.BytesIO((MAP / "trees.bmp").read_bytes()))
    Wt, Ht = trim.size
    ty = np.minimum(H - 1, ((np.arange(Ht) + 0.5) * H / Ht).astype(np.int64))
    tx = np.minimum(W - 1, ((np.arange(Wt) + 0.5) * W / Wt).astype(np.int64))
    t_sub = tarr[ty[:, None], tx[None, :]]
    trees = np.where(t_sub == mapgen.TERRAIN_PIXEL["forest"], 6,
                     np.where(t_sub == mapgen.TERRAIN_PIXEL["jungle"], 28, 0)).astype(np.uint8)
    tri = Image.fromarray(trees, "P")
    tri.putpalette(trim.getpalette())
    mapgen.save_8bit_bmp(tri, MAP / "trees.bmp")

    # 색 지도 (절반 크기): 새 바다 = mapgen 의 바다색, 새 육지 = 같은 지형 픽셀의 평균 색
    cpath = MAP / "terrain" / "colormap_rgb_cityemissivemask_a.dds"
    if cpath.is_file():
        cm = np.asarray(Image.open(io.BytesIO(cpath.read_bytes())).convert("RGBA")).copy()
        th = tarr[0::2, 0::2]
        ch = changed[0::2, 0::2]
        cmean = {}
        for t in np.unique(th[ch]).tolist():
            sel = (th == t) & ~ch
            cmean[t] = cm[sel, :3].mean(axis=0) if sel.any() else cm[~ch, :3].mean(axis=0)
        for t, col in cmean.items():
            m = ch & (th == t)
            cm[m, :3] = np.rint(col).astype(np.uint8)
        cm[ch & (th == mapgen.TERRAIN_PIXEL["ocean"]), :3] = (40, 60, 80)
        write_dds(cpath, cm)

    # ---- definition.csv
    mapgen.write_ascii(MAP / "definition.csv", "\n".join(";".join(r) for r in new_rows) + "\n")

    # ---- 주 / 전략 지역
    p2s = {}
    for sid, st in states.items():
        provs = sorted(R(p) for p in st["provinces"] if R(p) is not None)
        assert provs, "주 %d 가 비었음" % sid
        st["new"] = provs
        for p in provs:
            p2s[p] = sid
        t = st["text"]
        t = re.sub(r"(provinces\s*=\s*\{)[^}]*(\})", lambda m: m.group(1) + "\n\t\t" + " ".join(map(str, provs)) + "\n\t" + m.group(2), t, count=1)
        t = re.sub(r"(victory_points\s*=\s*\{\s*)(\d+)", lambda m: m.group(1) + str(R(int(m.group(2)))), t)
        st["file"].write_text(t, encoding="utf-8")
    p2r = {}
    for rid, rg in regions.items():
        provs = sorted(R(p) for p in rg["provinces"] if R(p) is not None)
        assert provs, "전략 지역 %d 가 비었음" % rid
        rg["new"] = provs
        for p in provs:
            p2r[p] = rid
        body = "\n".join("\t\t" + " ".join(map(str, provs[i:i + 20])) for i in range(0, len(provs), 20))
        t = re.sub(r"(provinces\s*=\s*\{)[^}]*(\})", lambda m: m.group(1) + "\n" + body + "\n\t" + m.group(2), rg["text"], count=1)
        rg["file"].write_text(t, encoding="utf-8")

    # ---- 위치 파일
    slices = ndimage.find_objects(ids)

    def pole(p):
        return mapgen.pole_pixel(ids, slices, p)

    def ypos(row, col):
        v = h_u8[row, col] / 10.0
        return max(mapgen.WATER_Y_MIN, v) if nwater[ids[row, col]] else v

    def pos(row, col):
        return "%.2f;%.2f;%.2f" % (col, ypos(row, col), H - 1 - row)

    def pix(x, z):
        return H - 1 - int(round(float(z))), int(round(float(x)))

    sea_px = np.array([t == "sea" for t in ntype])[ids]
    coast_px = ~nwater[ids] & ndimage.binary_dilation(sea_px)

    def sea_nb(row, col):
        for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            ny, nx = row + dy, col + dx
            if 0 <= ny < H and 0 <= nx < W and sea_px[ny, nx]:
                return int(ids[ny, nx])
        return 0

    _coast_cache = {}

    def coast_pixel(p):
        if p not in _coast_cache:
            sl = slices[p - 1]
            sub = (ids[sl] == p) & coast_px[sl]
            yy, xx = np.nonzero(sub)
            if yy.size == 0:
                _coast_cache[p] = None
            else:
                cy, cx = yy.mean(), xx.mean()
                k = int(np.argmin((yy - cy) ** 2 + (xx - cx) ** 2))
                _coast_cache[p] = (int(yy[k]) + sl[0].start, int(xx[k]) + sl[1].start)
        return _coast_cache[p]

    rng = np.random.default_rng(SEED)
    state_px = None

    def state_inner(sid):
        nonlocal state_px
        if state_px is None:
            slut = np.zeros(newN + 1, np.int32)
            for p, s in p2s.items():
                slut[p] = s
            state_px = slut[ids]
        yy, xx = np.nonzero(np.isin(ids, states[sid]["new"]))
        k = int(rng.integers(yy.size))
        return int(yy[k]), int(xx[k])

    STATE_T = {n for n, _ in mapgen.STATE_BUILDINGS}
    out_b = []
    has_coastal = defaultdict(set)
    has_dock = set()
    nb_fix = Counter()
    for l in lines_of("buildings.txt"):
        f = l.split(";")
        sid, typ = int(f[0]), f[1]
        row, col = pix(f[2], f[4])
        op = int(old_pid[row, col])
        np_ = int(ids[row, col])
        ok_land = not nwater[np_] and p2s.get(np_) == sid
        if typ in STATE_T:
            if not ok_land:
                row, col = state_inner(sid)
                nb_fix["state"] += 1
            out_b.append("%d;%s;%s;%s;%s" % (sid, typ, pos(row, col), f[5], f[6]))
        elif typ == mapgen.DOCKYARD:
            continue                       # 아래에서 해안 주마다 다시 만든다
        elif typ in mapgen.PROVINCE_BUILDINGS:
            target = R(op) if not is_water[op] else None
            if target is None:
                nb_fix["drop"] += 1
                continue
            if np_ != target:
                row, col = pole(target)
                nb_fix["prov"] += 1
            out_b.append("%d;%s;%s;%s;%s" % (p2s[target], typ, pos(row, col), f[5], f[6]))
        elif typ in mapgen.COASTAL_BUILDINGS:
            target = R(op) if not is_water[op] else None
            if target is None or not coastal[target]:
                nb_fix["drop"] += 1
                continue
            sea = R(int(f[6])) if int(f[6]) else None
            if np_ != target or not coast_px[row, col] or sea is None or ntype[sea] != "sea" or sea not in adj[target]:
                row, col = coast_pixel(target)
                sea = sea_nb(row, col)
                nb_fix["coast"] += 1
            if typ in has_coastal[target]:
                continue
            has_coastal[target].add(typ)
            out_b.append("%d;%s;%s;%s;%d" % (p2s[target], typ, pos(row, col), f[5], sea))
        else:
            out_b.append(l)
    for p in range(1, newN + 1):
        if ntype[p] == "land" and coastal[p]:
            for typ in mapgen.COASTAL_BUILDINGS:
                if typ not in has_coastal[p]:
                    row, col = coast_pixel(p)
                    out_b.append("%d;%s;%s;0.00;%d" % (p2s[p], typ, pos(row, col), sea_nb(row, col)))
                    nb_fix["coast_new"] += 1
    for sid, st in sorted(states.items()):
        cps = [p for p in st["new"] if ntype[p] == "land" and coastal[p]]
        if not cps:
            continue
        cy = np.mean([pole(p)[0] for p in st["new"]])
        cx = np.mean([pole(p)[1] for p in st["new"]])
        best_px = min((coast_pixel(p) for p in cps), key=lambda rc: ((rc[0] - cy) ** 2 + (rc[1] - cx) ** 2, rc))
        out_b.append("%d;%s;%s;0.00;%d" % (sid, mapgen.DOCKYARD, pos(*best_px), sea_nb(*best_px)))
    mapgen.write_ascii(MAP / "buildings.txt", "\n".join(out_b))
    print("buildings: %d줄, 고침 %s" % (len(out_b), dict(nb_fix)))

    units = []
    done = set()
    upole = {}
    for l in lines_of("unitstacks.txt"):
        f = l.split(";")
        p = R(int(f[0]))
        if p is None:
            continue
        row, col = pix(f[2], f[4])
        if int(ids[row, col]) != p:
            if p not in upole:
                upole[p] = pole(p)
            row, col = upole[p]
        units.append("%d;%s;%s;%s;%s" % (p, f[1], pos(row, col), f[5], f[6]))
    mapgen.write_ascii(MAP / "unitstacks.txt", "\n".join(units) + "\n")
    print("unitstacks: %d줄, 옮긴 프로빈스 %d" % (len(units), len(upole)))

    weather = []
    for l in lines_of("weatherpositions.txt"):
        f = l.split(";")
        rid = int(f[0])
        row, col = pix(f[1], f[3])
        if p2r.get(int(ids[row, col])) != rid:
            row, col = pole(regions[rid]["new"][0])
        weather.append("%d;%s;%s" % (rid, pos(row, col), f[4]))
    mapgen.write_ascii(MAP / "weatherpositions.txt", "\n".join(weather) + "\n")

    mapgen.write_ascii(MAP / "supply_nodes.txt", "\n".join("1 %d" % R(p) for p in supply) + "\n")
    mapgen.write_ascii(MAP / "railways.txt", "\n".join(
        "%d %d %s" % (r[0], r[1], " ".join(str(R(p)) for p in r[2:])) for r in rails) + "\n")
    adj_lines = (MAP / "adjacencies.csv").read_text(encoding="ascii").splitlines()
    out_a = [adj_lines[0]]
    for l in adj_lines[1:]:
        f = l.split(";")
        if not l.strip():
            continue
        if f[0] == "-1":
            out_a.append(l)
            continue
        xs_ = [R(int(f[0])), R(int(f[1]))] + ([R(int(f[3]))] if f[3] != "-1" else [])
        if None in xs_:
            continue                     # fix_exclaves 가 다시 만든다
        f[0], f[1] = str(xs_[0]), str(xs_[1])
        if f[3] != "-1":
            f[3] = str(xs_[2])
        out_a.append(";".join(f))
    mapgen.write_ascii(MAP / "adjacencies.csv", "\n".join(out_a) + "\n")

    # ---- out/*.json
    si_path = OUT / "state_index.json"
    si = json.loads(si_path.read_text(encoding="utf-8"))
    area = np.bincount(ids.ravel(), minlength=newN + 1)
    for st in si["states"]:
        provs = states[st["id"]]["new"]
        st["provinces"] = provs
        st["center"] = R(st["center"]) if R(st["center"]) in provs else provs[0]
        st["coastal"] = any(coastal[p] for p in provs if ntype[p] == "land")
        st["area"] = int(area[provs].sum())
    si_path.write_text(json.dumps(si, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for e in named.get("named", []) + named.get("anchors", []):
        if "province" in e:
            e["province"] = R(int(e["province"]))
    (OUT / "named_states.json").write_text(json.dumps(named, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for o in (MOD / "history" / "units").glob("*.txt"):
        t = o.read_text(encoding="utf-8-sig")
        t2 = re.sub(r"(location\s*=\s*)(\d+)", lambda m: m.group(1) + str(R(int(m.group(2)))), t)
        if t2 != t:
            o.write_text(t2, encoding="utf-8")
    print("HEX_COAST ok: 프로빈스 %d → %d" % (N, newN))
    return 0


if __name__ == "__main__":
    sys.exit(main())
