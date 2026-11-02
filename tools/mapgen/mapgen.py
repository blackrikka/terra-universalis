#!/usr/bin/env python3
"""Terra Universalis 지도 생성기: 지역 마스크 + 설정 -> HOI4 지도 전체.

사용법 (python -I 로 실행):
    python -I tools/mapgen/mapgen.py --regions <regions.png> --config <regions.json> [--mod terra_universalis] [--seed 1097]

입력: 지역 색 마스크(RGB PNG) + regions.json. 출력: <mod>/map, <mod>/history/states,
<mod>/map/strategicregions, <mod>/map/supplyareas, <mod>/localisation/*/tu_map_l_*.yml,
tools/mapgen/out/state_index.json, tools/mapgen/out/preview_*.png.

바닐라 파일은 읽기만 한다 (--vanilla, 기본 Steam 설치 경로): terrain/rivers/cities/trees 팔레트,
colormap/fow DDS 평균, 전략 지역 weather 블록.
"""

import argparse
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

MAPGEN_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(MAPGEN_DIR))
from dds import write_dds  # noqa: E402

PROJECT_DIR = MAPGEN_DIR.parent.parent
OUT_DIR = MAPGEN_DIR / "out"
VANILLA_DIR = Path(r"G:\SteamLibrary\steamapps\common\Hearts of Iron IV")
DEFAULT_SEED = 1097
DEFAULT_MOD = "terra_universalis"

MIN_COMPONENT = 64            # 이보다 작은 지역 성분은 이웃 색으로 바꾼다
SMALL_PROVINCE_RATIO = 0.25   # prov_size의 이 비율 미만 프로빈스는 합병
LAND_KINDS = ("land", "wasteland", "impassable")
WATER_KINDS = ("sea", "lake")
KINDS = LAND_KINDS + WATER_KINDS
TERRAINS = ("plains", "forest", "hills", "mountain", "desert", "marsh", "jungle", "urban",
            "snow_plains", "snow_mountain")
DEF_TERRAIN = {"snow_plains": "plains", "snow_mountain": "mountain"}   # definition.csv용 HOI4 타입
TERRAIN_PIXEL = {"plains": 0, "forest": 1, "hills": 17, "mountain": 11, "desert": 3, "marsh": 9,
                 "jungle": 21, "urban": 13, "lakes": 14, "ocean": 15, "snow_mountain": 16,
                 "snow_plains": 19}
HEIGHT_BASE = {"plains": 100, "marsh": 100, "desert": 100, "forest": 103, "hills": 112,
               "snow_plains": 104, "mountain": 140, "snow_mountain": 140,
               "jungle": 103, "urban": 100}
IMPASSABLE_BUMP = 40
LAKE_HEIGHT = 90
SEA_HEIGHT_COAST = 94
SEA_HEIGHT_DEEP = 80
SEA_RAMP_PX = 40
LAND_MIN = 96
WATER_MAX = 94
NOISE_AMP = 6.0
HEIGHT_BLUR = 2.0
NORMAL_K = 0.5
WATER_Y_MIN = 9.5
TREE_SCALE = 3.4133
STATE_KIND_CODE = {"land": 0, "lake": 1, "sea": 2}

# 주 단위 건물 (주 안의 무작위 내부 픽셀)
STATE_BUILDINGS = [
    ("arms_factory", 6), ("industrial_complex", 6), ("air_base", 1), ("anti_air_building", 3),
    ("fuel_silo", 1), ("nuclear_reactor_spawn", 1), ("radar_station", 1),
    ("rocket_site_spawn", 1), ("stronghold_network", 1), ("synthetic_refinery", 1),
]
DOCKYARD = "dockyard"
# 프로빈스 단위 (육지 전부, 프로빈스 경계에서 가장 먼 픽셀)
PROVINCE_BUILDINGS = ["bunker", "supply_node", "special_project_facility_spawn"]
# 해안 프로빈스 (바다와 맞닿은 해안 픽셀, 마지막 칸에 바다 프로빈스 id)
COASTAL_BUILDINGS = ["coastal_bunker", "naval_base_spawn", "naval_headquarters",
                     "naval_supply_hub", "floating_harbor"]
UNIT_TYPES = range(0, 39)


class MapgenError(Exception):
    pass


# ---------------------------------------------------------------- 경로 / 입출력

def resolve_input(p):
    path = Path(p)
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    return (PROJECT_DIR / path).resolve()


def resolve_mod(p):
    path = Path(p)
    if path.is_absolute():
        return path
    cand = PROJECT_DIR / path
    if cand.is_dir():
        return cand.resolve()
    return path.resolve()


def write_ascii(path, text):
    """스크립트 파일: ASCII만 허용 (아니면 UnicodeEncodeError)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("ascii"))


def write_loc(mod, name, ko_items, en_items):
    """localisation/{korean,english}/replace/tu_<name>_l_<lang>.yml. UTF-8 BOM.
    replace 폴더: 바닐라와 같은 키(STATE_1 등)를 확실히 덮어쓴다."""
    for folder, lang, items in (("korean", "korean", ko_items), ("english", "english", en_items)):
        lines = ["l_%s:" % lang]
        for key, value in items:
            if '"' in value:
                raise MapgenError("loc value contains quote: %s" % key)
            lines.append(' %s:0 "%s"' % (key, value))
        path = mod / "localisation" / folder / "replace" / ("tu_%s_l_%s.yml" % (name, lang))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("\n".join(lines) + "\n").encode("utf-8-sig"))


def clean_outputs(mod):
    """사양서 3-16: 생성 전에 mapgen 출력 폴더의 해당 파일을 비운다."""
    patterns = [
        (mod / "map" / "strategicregions", "*.txt"),
        (mod / "map" / "supplyareas", "*.txt"),
        (mod / "history" / "states", "*.txt"),
        (mod / "localisation" / "korean", "tu_map_l_*.yml"),
        (mod / "localisation" / "english", "tu_map_l_*.yml"),
        (mod / "localisation" / "korean" / "replace", "tu_map_l_*.yml"),
        (mod / "localisation" / "english" / "replace", "tu_map_l_*.yml"),
    ]
    for folder, pattern in patterns:
        if folder.is_dir():
            for f in folder.glob(pattern):
                if f.is_file():
                    f.unlink()


# ---------------------------------------------------------------- 설정 / 마스크

def load_config(path):
    cfg = json.loads(path.read_text(encoding="utf-8"))
    size = cfg.get("map_size")
    if not (isinstance(size, list) and len(size) == 2):
        raise MapgenError("config: map_size는 [가로, 세로]여야 함")
    W, H = int(size[0]), int(size[1])
    if W % 256 or H % 256:
        raise MapgenError("config: map_size는 가로·세로 모두 256의 배수 (현재 %dx%d)" % (W, H))
    for key in ("strategic_land_states", "strategic_sea_provinces"):
        if key not in cfg:
            raise MapgenError("config: %s 누락" % key)
    regions = cfg.get("regions")
    if not regions:
        raise MapgenError("config: regions 비어 있음")
    seen_ids, seen_colors = set(), set()
    for r in regions:
        rid = r.get("id")
        kind = r.get("kind")
        if kind not in KINDS:
            raise MapgenError("region %s: kind 오류 (%s)" % (rid, kind))
        if rid in seen_ids:
            raise MapgenError("region id 중복: %s" % rid)
        seen_ids.add(rid)
        color = tuple(int(c) for c in r["color"])
        if len(color) != 3 or any(c < 0 or c > 255 for c in color):
            raise MapgenError("region %s: color 오류" % rid)
        if color in seen_colors:
            raise MapgenError("region color 중복: %s" % (color,))
        seen_colors.add(color)
        if not (r.get("prov_size", 0) > 0):
            raise MapgenError("region %s: prov_size 누락 또는 0 이하" % rid)
        if kind in LAND_KINDS:
            if not r.get("owner"):
                raise MapgenError("region %s: owner 누락" % rid)
            if r.get("terrain") not in TERRAINS:
                raise MapgenError("region %s: terrain 오류 (%s)" % (rid, r.get("terrain")))
            if int(r.get("state_size", 0)) < 1:
                raise MapgenError("region %s: state_size 누락" % rid)
    cfg["map_size"] = [W, H]
    return cfg


def load_mask(path, W, H, regions):
    img = Image.open(path).convert("RGB")
    if img.size != (W, H):
        raise MapgenError("마스크 크기 %s != map_size (%d, %d)" % (img.size, W, H))
    arr = np.asarray(img).astype(np.int64)
    codes = (arr[:, :, 0] << 16) | (arr[:, :, 1] << 8) | arr[:, :, 2]
    rcodes = np.array([(r["color"][0] << 16) | (r["color"][1] << 8) | r["color"][2]
                       for r in regions], dtype=np.int64)
    order = np.argsort(rcodes)
    ks = rcodes[order]
    pos = np.clip(np.searchsorted(ks, codes), 0, len(ks) - 1)
    ok = ks[pos] == codes
    if not ok.all():
        bad = np.unique(codes[~ok])
        shown = ", ".join("#%06x" % int(c) for c in bad[:10])
        raise MapgenError("regions.json에 없는 색 %d개: %s" % (len(bad), shown))
    return order[pos].astype(np.int32)


def clean_small_components(region, n_regions):
    """64픽셀 미만 연결 성분은 둘러싼 지역 중 다수 색으로 바꾼다 (성분 주변만 계산)."""
    H, W = region.shape
    changed = 0
    for r in range(n_regions):
        lab, n = ndimage.label(region == r)
        if n == 0:
            continue
        sizes = np.bincount(lab.ravel())
        slc = ndimage.find_objects(lab)
        for c in range(1, n + 1):
            if sizes[c] >= MIN_COMPONENT:
                continue
            sl = slc[c - 1]
            y0 = max(sl[0].start - 1, 0)
            y1 = min(sl[0].stop + 1, H)
            x0 = max(sl[1].start - 1, 0)
            x1 = min(sl[1].stop + 1, W)
            sub = lab[y0:y1, x0:x1] == c
            ring = ndimage.binary_dilation(sub) & ~sub
            rv = region[y0:y1, x0:x1]
            vals = rv[ring]
            if vals.size == 0:
                continue
            counts = np.bincount(vals, minlength=n_regions)
            rv[sub] = int(np.argmax(counts))
            changed += 1
    return changed


# ---------------------------------------------------------------- 프로빈스 분할

def remove_region_x_crosses(region, max_rounds=50):
    """2x2 블록에 지역 4개가 만나면 (프로빈스 X-교차를 같은 지역 안에서 풀 수 없음) 왼쪽 위 픽셀을 오른쪽 이웃 지역으로 바꾼다."""
    total = 0
    for _ in range(max_rounds):
        a = region[:-1, :-1]
        b = region[:-1, 1:]
        c = region[1:, :-1]
        d = region[1:, 1:]
        cross = (a != b) & (a != c) & (a != d) & (b != c) & (b != d) & (c != d)
        ys, xs = np.nonzero(cross)
        if ys.size == 0:
            break
        for y, x in zip(ys.tolist(), xs.tolist()):
            vals = {int(region[y, x]), int(region[y, x + 1]), int(region[y + 1, x]), int(region[y + 1, x + 1])}
            if len(vals) < 4:
                continue
            region[y, x] = region[y, x + 1]
            total += 1
    return total


def poisson_seeds(comp, radius, rng):
    """Bridson 포아송 디스크 샘플링. 씨앗은 comp 안에만 놓인다."""
    H, W = comp.shape
    ys, xs = np.nonzero(comp)
    cell = radius / math.sqrt(2.0)
    grid = {}
    pts = []

    def near_ok(y, x):
        gy, gx = int(y // cell), int(x // cell)
        for oy in range(-2, 3):
            for ox in range(-2, 3):
                for j in grid.get((gy + oy, gx + ox), ()):
                    qy, qx = pts[j]
                    if (qy - y) ** 2 + (qx - x) ** 2 < radius * radius:
                        return False
        return True

    def add(y, x):
        pts.append((y, x))
        grid.setdefault((int(y // cell), int(x // cell)), []).append(len(pts) - 1)

    i0 = int(rng.integers(len(ys)))
    add(int(ys[i0]), int(xs[i0]))
    active = [0]
    while active:
        k = int(rng.integers(len(active)))
        py, px = pts[active[k]]
        placed = False
        for _ in range(30):
            ang = rng.random() * 2.0 * math.pi
            rad = radius * (1.0 + rng.random())
            y = int(round(py + rad * math.sin(ang)))
            x = int(round(px + rad * math.cos(ang)))
            if 0 <= y < H and 0 <= x < W and comp[y, x] and near_ok(y, x):
                add(y, x)
                active.append(len(pts) - 1)
                placed = True
                break
        if not placed:
            active[k] = active[-1]
            active.pop()
    return pts


def multi_bfs(allowed_flat, seeds, W, H):
    """4방향 다중 시작 BFS (프런티어 단위 벡터화). 반환: 시드 번호 배열 (허용 밖은 -1)."""
    N = W * H
    owner = np.full(N, -1, np.int32)
    seeds = np.asarray(seeds, np.int64)
    owner[seeds] = np.arange(seeds.size, dtype=np.int32)
    frontier = seeds
    while frontier.size:
        x = frontier % W
        src_owner = owner[frontier]
        cands = []
        srcs = []
        m = x > 0
        cands.append(frontier[m] - 1)
        srcs.append(src_owner[m])
        m = x < W - 1
        cands.append(frontier[m] + 1)
        srcs.append(src_owner[m])
        m = frontier >= W
        cands.append(frontier[m] - W)
        srcs.append(src_owner[m])
        m = frontier < N - W
        cands.append(frontier[m] + W)
        srcs.append(src_owner[m])
        nb = np.concatenate(cands)
        src = np.concatenate(srcs)
        ok = allowed_flat[nb] & (owner[nb] < 0)
        nb = nb[ok]
        src = src[ok]
        if nb.size == 0:
            break
        uniq, idx = np.unique(nb, return_index=True)
        owner[uniq] = src[idx]
        frontier = uniq
    return owner


def stays_connected(lab, pid, py, px):
    """(py,px)를 pid에서 빼도 pid가 4방향 연결을 유지하는지."""
    H, W = lab.shape
    nbrs = []
    for ny, nx in ((py - 1, px), (py + 1, px), (py, px - 1), (py, px + 1)):
        if 0 <= ny < H and 0 <= nx < W and lab[ny, nx] == pid:
            nbrs.append((ny, nx))
    if len(nbrs) <= 1:
        return True
    start = nbrs[0]
    seen = {start}
    stack = [start]
    while stack:
        y, x = stack.pop()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if (0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen
                    and (ny, nx) != (py, px) and lab[ny, nx] == pid):
                seen.add((ny, nx))
                stack.append((ny, nx))
    return all(n in seen for n in nbrs)


def block_is_cross(lab, y, x):
    vals = {int(lab[y, x]), int(lab[y, x + 1]), int(lab[y + 1, x]), int(lab[y + 1, x + 1])}
    return len(vals) == 4


def remove_x_crosses(lab, label_region, max_rounds=1000):
    """2x2 블록에 서로 다른 프로빈스 4개가 있으면 픽셀 하나를 같은 지역의 이웃 프로빈스로 바꾼다.
    바꾼 뒤 원래 프로빈스의 연결성이 유지되는 경우만 허용한다."""
    H, W = lab.shape
    total_fixes = 0
    fallback_fixes = 0
    for _ in range(max_rounds):
        a = lab[:-1, :-1]
        b = lab[:-1, 1:]
        c = lab[1:, :-1]
        d = lab[1:, 1:]
        cross = (a != b) & (a != c) & (a != d) & (b != c) & (b != d) & (c != d)
        ys, xs = np.nonzero(cross)
        if ys.size == 0:
            print("X-cross fallback (other-region neighbour) fixes: %d" % fallback_fixes)
            return total_fixes
        sizes = np.bincount(lab.ravel(), minlength=len(label_region)).tolist()
        for y, x in zip(ys.tolist(), xs.tolist()):
            if not block_is_cross(lab, y, x):
                continue
            fixed = False
            # 1차: 같은 지역 이웃만. 2차(대체): 같은 지역 이웃이 없을 때 (두 같은 지역 성분이 대각선으로만 닿는 경우)
            # 다른 지역의 이웃으로 옮긴다. 이때 그 픽셀의 지역은 옮긴 프로빈스의 지역이 된다 (fallback_fixes로 보고).
            for strict in (True, False):
                for py, px in ((y, x), (y, x + 1), (y + 1, x), (y + 1, x + 1)):
                    pid = int(lab[py, px])
                    if sizes[pid] < 2:
                        continue
                    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                        ny, nx = py + dy, px + dx
                        if not (0 <= ny < H and 0 <= nx < W):
                            continue
                        qid = int(lab[ny, nx])
                        if qid == pid or (strict and label_region[qid] != label_region[pid]):
                            continue
                        if not stays_connected(lab, pid, py, px):
                            continue
                        lab[py, px] = qid
                        sizes[pid] -= 1
                        sizes[qid] += 1
                        fixed = True
                        break
                    if fixed:
                        break
                if fixed:
                    if not strict:
                        fallback_fixes += 1
                    break
            if not fixed:
                detail = []
                for py, px in ((y, x), (y, x + 1), (y + 1, x), (y + 1, x + 1)):
                    pid = int(lab[py, px])
                    nb = []
                    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                        ny, nx = py + dy, px + dx
                        if 0 <= ny < H and 0 <= nx < W:
                            qid = int(lab[ny, nx])
                            nb.append("%d/r%d/%s" % (qid, label_region[qid],
                                                     "same" if qid != pid and label_region[qid] == label_region[pid]
                                                     else "-"))
                    detail.append("(%d,%d) prov %d size %d region %d nb[%s]" % (
                        py, px, pid, sizes[pid], label_region[pid], " ".join(nb)))
                raise MapgenError("X-교차 해결 실패: 블록 (%d,%d): %s" % (y, x, " | ".join(detail)))
            total_fixes += 1
    a, b, c, d = lab[:-1, :-1], lab[:-1, 1:], lab[1:, :-1], lab[1:, 1:]
    if not ((a != b) & (a != c) & (a != d) & (b != c) & (b != d) & (c != d)).any():   # 마지막 라운드에서 다 고쳐진 경우
        print("X-cross fallback (other-region neighbour) fixes: %d" % fallback_fixes)
        return total_fixes
    raise MapgenError("X-교차 제거가 수렴하지 않음")


def bbox_violators(lab, next_label, limit_w, limit_h):
    """경계 상자 폭 >= W/9 또는 높이 >= H/9 인 프로빈스 라벨 목록."""
    slices = ndimage.find_objects(lab)
    bad = []
    for lbl in range(1, next_label):
        if lbl - 1 >= len(slices) or slices[lbl - 1] is None:
            continue
        sl = slices[lbl - 1]
        if (sl[1].stop - sl[1].start) >= limit_w or (sl[0].stop - sl[0].start) >= limit_h:
            bad.append(lbl)
    return bad


def enforce_bbox(lab, label_region, label_comp, rng, W, H, limit_w, limit_h, next_label):
    """경계 상자 위반 프로빈스는 씨앗 2개를 다시 뽑아 같은 영역 안에서 BFS로 둘로 나눈다. 위반이 없어질 때까지 반복."""
    for _ in range(2000):
        bad = bbox_violators(lab, next_label, limit_w, limit_h)
        if not bad:
            return next_label
        slices = ndimage.find_objects(lab)
        for lbl in bad:
            sl = slices[lbl - 1]
            sub = lab[sl] == lbl
            ys, xs = np.nonzero(sub)
            if ys.size < 2:
                raise MapgenError("경계 상자 위반 프로빈스 라벨 %d가 한 픽셀이라 나눌 수 없음" % lbl)
            i1 = int(rng.integers(ys.size))
            d2 = (ys - ys[i1]) ** 2 + (xs - xs[i1]) ** 2
            i2 = int(np.argmax(d2))
            hs, ws = sub.shape
            seeds = [int(ys[i1]) * ws + int(xs[i1]), int(ys[i2]) * ws + int(xs[i2])]
            if seeds[0] == seeds[1]:
                raise MapgenError("경계 상자 분할 씨앗 중복 (라벨 %d)" % lbl)
            owner = multi_bfs(sub.ravel(), seeds, ws, hs).reshape(hs, ws)
            new = next_label
            next_label += 1
            label_region.append(label_region[lbl])
            label_comp.append(label_comp[lbl])
            view = lab[sl]
            view[sub & (owner == 1)] = new
    raise MapgenError("경계 상자 분할이 수렴하지 않음")


def merge_all_small(lab, label_region, regions, next_label, limit_w, limit_h):
    """소형 프로빈스(면적 < prov_size*0.25)를 같은 지역의 경계가 가장 긴 이웃에 합친다.
    합친 경계 상자가 제한(폭 < limit_w, 높이 < limit_h)을 넘으면 그 이웃에는 합치지 않는다."""
    n = next_label
    sizes = np.bincount(lab.ravel(), minlength=n).astype(np.int64)
    slices = ndimage.find_objects(lab)
    box = {}
    for l in range(1, n):
        s = slices[l - 1] if l - 1 < len(slices) else None
        if sizes[l] > 0 and s is not None:
            box[l] = [s[0].start, s[0].stop, s[1].start, s[1].stop]
    A = np.concatenate([lab[:, :-1].ravel(), lab[:-1, :].ravel()]).astype(np.int64)
    B = np.concatenate([lab[:, 1:].ravel(), lab[1:, :].ravel()]).astype(np.int64)
    m = A != B
    lo = np.minimum(A[m], B[m])
    hi = np.maximum(A[m], B[m])
    keys, counts = np.unique(lo * n + hi, return_counts=True)
    nbr = defaultdict(dict)
    for k, c in zip(keys.tolist(), counts.tolist()):
        x, y = divmod(k, n)
        if x and y:
            nbr[x][y] = c
            nbr[y][x] = c
    rep = np.arange(n, dtype=np.int64)
    thr = {l: regions[label_region[l]]["prov_size"] * SMALL_PROVINCE_RATIO for l in box}
    order = sorted((l for l in box if sizes[l] < thr[l]), key=lambda l: (sizes[l], l))
    merged = 0
    for i in order:
        if i not in box or sizes[i] == 0 or sizes[i] >= thr[i]:
            continue
        best = None
        for j, c in nbr[i].items():
            if j == i or label_region[j] != label_region[i]:
                continue
            bi, bj = box[i], box[j]
            y0 = min(bi[0], bj[0])
            y1 = max(bi[1], bj[1])
            x0 = min(bi[2], bj[2])
            x1 = max(bi[3], bj[3])
            if (x1 - x0) >= limit_w or (y1 - y0) >= limit_h:
                continue
            cand = (c, -j)
            if best is None or cand > best[0]:
                best = (cand, j)
        if best is None:
            continue
        j = best[1]
        rep[i] = j
        bi, bj = box[i], box[j]
        box[j] = [min(bi[0], bj[0]), max(bi[1], bj[1]), min(bi[2], bj[2]), max(bi[3], bj[3])]
        sizes[j] += sizes[i]
        sizes[i] = 0
        for k, c in list(nbr[i].items()):
            if k == j:
                continue
            nbr[j][k] = nbr[j].get(k, 0) + c
            nbr[k][j] = nbr[k].get(j, 0) + c
            nbr[k].pop(i, None)
        nbr[j].pop(i, None)
        nbr.pop(i, None)
        del box[i]
        merged += 1
    while True:
        r2 = rep[rep]
        if np.array_equal(r2, rep):
            break
        rep = r2
    lab[...] = rep[lab]
    return merged


def split_by_cells(region, regions, cells):
    """프로빈스 = (지역 성분 ∩ 헥스 칸)의 연결 성분. 반환: lab, label_region, label_comp, next_label."""
    H, W = region.shape
    comp = np.zeros((H, W), np.int64)
    comp_region = [0]
    for r, reg in enumerate(regions):
        mask_r = region == r
        if not mask_r.any():
            print("WARN: region %s has no pixels" % reg["id"])
            continue
        cl, n = ndimage.label(mask_r)
        comp[mask_r] = cl[mask_r] + len(comp_region) - 1
        comp_region.extend([r] * n)
    key = comp * (1 << 24) + cells.astype(np.int64)
    _, inv = np.unique(key, return_inverse=True)
    lab = (inv.reshape(H, W) + 1).astype(np.int32)
    # 같은 (성분, 칸)이 해안선 때문에 두 조각 이상이면 나눈다
    flat_lab = lab.ravel()
    flat_comp = comp.ravel()
    idx = np.unique(flat_lab, return_index=True)
    lab_comp = np.zeros(int(lab.max()) + 1, np.int64)
    lab_comp[idx[0]] = flat_comp[idx[1]]
    next_label = int(lab.max()) + 1
    extra_comp = []
    split = 0
    for l, sl in enumerate(ndimage.find_objects(lab), start=1):
        if sl is None:
            continue
        sub = lab[sl] == l
        pieces, n = ndimage.label(sub)
        if n > 1:
            view = lab[sl]
            for k in range(2, n + 1):
                view[pieces == k] = next_label
                extra_comp.append(lab_comp[l])
                next_label += 1
                split += 1
    lab_comp = np.concatenate([lab_comp, np.array(extra_comp, np.int64)])
    label_comp = lab_comp.tolist()
    label_region = [comp_region[c] for c in label_comp]
    label_region[0] = 0
    print("hex provinces: %d (split pieces %d)" % (next_label - 1, split))
    return lab, label_region, label_comp, next_label


def split_provinces(region, regions, rng, cells=None):
    H, W = region.shape
    if cells is not None:
        lab, label_region, label_comp, next_label = split_by_cells(region, regions, cells)
        return finish_provinces(lab, label_region, label_comp, regions, rng, W, H, next_label)
    lab = np.zeros((H, W), np.int32)
    label_region = [0]
    label_comp = [0]
    next_label = 1
    comp_no = 0
    for r, reg in enumerate(regions):
        mask_r = region == r
        if not mask_r.any():
            print("WARN: region %s has no pixels" % reg["id"])
            continue
        cl, n = ndimage.label(mask_r)
        slc = ndimage.find_objects(cl)
        radius = 0.9 * math.sqrt(reg["prov_size"])
        for c in range(1, n + 1):
            sl = slc[c - 1]
            sub = cl[sl] == c
            comp_no += 1
            hs, ws = sub.shape
            seeds = poisson_seeds(sub, radius, rng)
            seed_flat = [y * ws + x for y, x in seeds]
            owner = multi_bfs(sub.ravel(), seed_flat, ws, hs).reshape(hs, ws)
            k = len(seeds)
            label_region.extend([r] * k)
            label_comp.extend([comp_no] * k)
            view = lab[sl]
            view[sub] = owner[sub] + next_label
            next_label += k
    return finish_provinces(lab, label_region, label_comp, regions, rng, W, H, next_label)


def finish_provinces(lab, label_region, label_comp, regions, rng, W, H, next_label):
    # 경계 상자 제한 (폭 < W/9, 높이 < H/9): 소형 합병과 X-교차 처리보다 먼저.
    # 소형 합병은 합친 상자가 제한 안일 때만 허용 (합병 뒤에도 제한이 유지된다).
    limit_w = W / 9.0
    limit_h = H / 9.0
    next_label = enforce_bbox(lab, label_region, label_comp, rng, W, H, limit_w, limit_h, next_label)
    merged = merge_all_small(lab, label_region, regions, next_label, limit_w, limit_h)
    print("small provinces merged: %d" % merged)
    if bbox_violators(lab, next_label, limit_w, limit_h):
        raise MapgenError("소형 합병 후 경계 상자 위반이 남음")
    label_region_arr = np.array(label_region, dtype=np.int32)
    fixes = remove_x_crosses(lab, label_region_arr)
    print("X-cross fixes: %d" % fixes)
    return lab, label_region_arr, np.array(label_comp, dtype=np.int32)


def renumber(lab, label_region, label_comp, regions):
    """id: 육지(land, wasteland, impassable) -> 호수 -> 바다, 같은 묶음 안은 지역 순서, 그다음 첫 픽셀 순서."""
    present, first = np.unique(lab, return_index=True)
    info = []
    for lbl, fi in zip(present.tolist(), first.tolist()):
        r = int(label_region[lbl])
        kind = regions[r]["kind"]
        group = 0 if kind in LAND_KINDS else (1 if kind == "lake" else 2)
        info.append((group, r, fi, lbl))
    info.sort()
    lut = np.zeros(int(lab.max()) + 1, np.int32)
    provs = [None]
    for new_id, (group, r, fi, lbl) in enumerate(info, start=1):
        lut[lbl] = new_id
        provs.append({"id": new_id, "region": r, "comp": int(label_comp[lbl])})
    return lut[lab], provs


# ---------------------------------------------------------------- 프로빈스 속성

def assign_colors(n, rng):
    used = {(0, 0, 0)}
    out = [(0, 0, 0)]
    for _ in range(n):
        while True:
            c = tuple(int(v) for v in rng.integers(0, 256, 3))
            if c not in used:
                break
        used.add(c)
        out.append(c)
    return out


def province_attributes(provs, id_map, regions):
    H, W = id_map.shape
    N = len(provs) - 1
    flat = id_map.ravel()
    yy, xx = np.mgrid[0:H, 0:W]
    area = np.bincount(flat, minlength=N + 1)
    sy = np.bincount(flat, weights=yy.ravel().astype(np.float64), minlength=N + 1)
    sx = np.bincount(flat, weights=xx.ravel().astype(np.float64), minlength=N + 1)
    for p in provs[1:]:
        reg = regions[p["region"]]
        kind = reg["kind"]
        pid = p["id"]
        if kind in LAND_KINDS:
            p["type"] = "land"
            p["terrain"] = reg["terrain"]
            p["def_terrain"] = DEF_TERRAIN.get(reg["terrain"], reg["terrain"])
            p["pixel_terrain"] = TERRAIN_PIXEL[reg["terrain"]]
            p["base_height"] = HEIGHT_BASE[reg["terrain"]] + (IMPASSABLE_BUMP if kind == "impassable" else 0)
            p["owner"] = reg["owner"]
        elif kind == "lake":
            p["type"] = "lake"
            p["terrain"] = "lakes"
            p["def_terrain"] = "lakes"
            p["pixel_terrain"] = TERRAIN_PIXEL["lakes"]
            p["base_height"] = LAKE_HEIGHT
            p["owner"] = None
        else:
            p["type"] = "sea"
            p["terrain"] = "ocean"
            p["def_terrain"] = "ocean"
            p["pixel_terrain"] = TERRAIN_PIXEL["ocean"]
            p["base_height"] = SEA_HEIGHT_COAST
            p["owner"] = None
        p["region_kind"] = kind
        p["area"] = int(area[pid])
        p["sy"] = float(sy[pid])
        p["sx"] = float(sx[pid])
        p["cy"] = p["sy"] / p["area"]
        p["cx"] = p["sx"] / p["area"]
        p["kind_code"] = STATE_KIND_CODE["land" if p["type"] == "land" else ("lake" if p["type"] == "lake" else "sea")]


def build_adjacency(id_map, N):
    """4방향 인접 쌍 -> {id: [이웃 id 정렬]}. 쌍을 정수 키로 만들어 중복을 제거한다."""
    h1 = id_map[:, :-1].ravel()
    h2 = id_map[:, 1:].ravel()
    v1 = id_map[:-1, :].ravel()
    v2 = id_map[1:, :].ravel()
    a = np.concatenate([h1, v1]).astype(np.int64)
    b = np.concatenate([h2, v2]).astype(np.int64)
    m = a != b
    lo = np.minimum(a[m], b[m])
    hi = np.maximum(a[m], b[m])
    keys = np.unique(lo * (N + 1) + hi)
    adj = {i: [] for i in range(1, N + 1)}
    for k in keys.tolist():
        x, y = divmod(k, N + 1)
        adj[x].append(y)
        adj[y].append(x)
    for i in adj:
        adj[i].sort()
    return adj


def set_coastal(provs, adj):
    for p in provs[1:]:
        nbr_types = {provs[n]["type"] for n in adj[p["id"]]}
        if p["type"] == "sea":
            p["coastal"] = any(t != "sea" for t in nbr_types)
        else:
            p["coastal"] = "sea" in nbr_types


def pole_crop(label_map, slices, label):
    """라벨 영역의 경계 거리 변환. 반환: (y0, x0, sub 마스크, 거리 배열)."""
    sl = slices[label - 1]
    y0, y1 = sl[0].start, sl[0].stop
    x0, x1 = sl[1].start, sl[1].stop
    sub = label_map[y0:y1, x0:x1] == label
    padded = np.pad(sub, 1)
    dist = ndimage.distance_transform_edt(padded)[1:-1, 1:-1]
    return y0, x0, sub, dist


def pole_pixel(label_map, slices, label):
    y0, x0, sub, dist = pole_crop(label_map, slices, label)
    d = np.where(sub, dist, -1.0)
    k = int(np.argmax(d))
    ky, kx = divmod(k, sub.shape[1])
    return y0 + ky, x0 + kx


# ---------------------------------------------------------------- 그룹 묶기 (주 / 전략 지역)

def grow_groups(nodes, adj, coords, target):
    """인접 그래프를 target 개씩 묶는다. 씨앗은 최원점, 성장은 BFS 라운드 로빈 (항상 연결)."""
    node_set = set(nodes)
    seen = set()
    comps = []
    for s in sorted(nodes):
        if s in seen:
            continue
        comp = []
        q = deque([s])
        seen.add(s)
        while q:
            u = q.popleft()
            comp.append(u)
            for v in adj.get(u, ()):
                if v in node_set and v not in seen:
                    seen.add(v)
                    q.append(v)
        comps.append(sorted(comp))

    def d2(a, b):
        return (coords[a][0] - coords[b][0]) ** 2 + (coords[a][1] - coords[b][1]) ** 2

    groups = []
    for comp in comps:
        n = len(comp)
        k = min(n, max(1, int(round(n / float(target)))))
        cy = sum(coords[u][0] for u in comp) / n
        cx = sum(coords[u][1] for u in comp) / n
        first = min(comp, key=lambda u: ((coords[u][0] - cy) ** 2 + (coords[u][1] - cx) ** 2, u))
        seeds = [first]
        mind = {u: d2(u, first) for u in comp}
        while len(seeds) < k:
            nxt = max(comp, key=lambda u: (mind[u], -u))
            seeds.append(nxt)
            for u in comp:
                mind[u] = min(mind[u], d2(u, nxt))
        assigned = {}
        local = [[s] for s in seeds]
        frontiers = [deque() for _ in seeds]
        for i, s in enumerate(seeds):
            assigned[s] = i
            frontiers[i].extend(v for v in adj.get(s, ()) if v in node_set)
        remaining = n - len(seeds)
        while remaining > 0:
            progressed = False
            for i in range(k):
                f = frontiers[i]
                while f:
                    c = f.popleft()
                    if c in assigned:
                        continue
                    assigned[c] = i
                    local[i].append(c)
                    remaining -= 1
                    progressed = True
                    f.extend(v for v in adj.get(c, ()) if v in node_set and v not in assigned)
                    break
            if not progressed:
                raise MapgenError("그룹 묶기 실패 (연결 성분 %d)" % len(comp))
        groups.extend(sorted(g) for g in local)
    return groups


def mst_edges(points):
    n = len(points)
    if n < 2:
        return []
    in_tree = [False] * n
    best = [float("inf")] * n
    parent = [-1] * n
    best[0] = 0.0
    edges = []
    for _ in range(n):
        u = min((i for i in range(n) if not in_tree[i]), key=lambda i: (best[i], i))
        in_tree[u] = True
        if parent[u] >= 0:
            edges.append((parent[u], u))
        for v in range(n):
            if not in_tree[v]:
                d = (points[u][0] - points[v][0]) ** 2 + (points[u][1] - points[v][1]) ** 2
                if d < best[v]:
                    best[v] = d
                    parent[v] = u
    return edges


def bfs_path(adj, src, dst, allowed):
    if src == dst:
        return [src]
    prev = {src: None}
    q = deque([src])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v in allowed and v not in prev:
                prev[v] = u
                if v == dst:
                    path = [v]
                    while prev[path[-1]] is not None:
                        path.append(prev[path[-1]])
                    return list(reversed(path))
                q.append(v)
    return None


# ---------------------------------------------------------------- 높이 / 노멀 / 지형 이미지

def compute_heightmap(kind_px, base_px, rng, H, W):
    sea = kind_px == 2
    lake = kind_px == 1
    land = kind_px == 0
    dist = ndimage.distance_transform_edt(sea)
    ramp = np.clip((dist - 1.0) / (SEA_RAMP_PX - 1.0), 0.0, 1.0)
    sea_h = SEA_HEIGHT_COAST - (SEA_HEIGHT_COAST - SEA_HEIGHT_DEEP) * ramp
    h = np.where(sea, sea_h, base_px)
    noise = ndimage.gaussian_filter(rng.standard_normal((H, W)), sigma=16.0, mode="nearest")
    noise = noise / np.abs(noise).max() * NOISE_AMP
    h = h + noise
    h = ndimage.gaussian_filter(h, sigma=HEIGHT_BLUR, mode="nearest")
    h = np.rint(h)
    h = np.where(land, np.maximum(h, LAND_MIN), h)
    h = np.where(lake | sea, np.minimum(h, WATER_MAX), h)
    return np.clip(h, 0, 255).astype(np.uint8)


def compute_normal_map(h_u8):
    H, W = h_u8.shape
    hf = h_u8.astype(np.float64)
    gr, gc = np.gradient(hf)          # gr: 행 방향, gc: 열 방향
    # z = H-1-행 이므로 dh/dz = -gr
    nx = -gc * NORMAL_K
    ny = gr * NORMAL_K
    nz = np.ones_like(hf)

    def half(a):
        return a.reshape(H // 2, 2, W // 2, 2).mean(axis=(1, 3))

    nx, ny, nz = half(nx), half(ny), half(nz)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    vec = np.stack([nx / norm, ny / norm, nz / norm], axis=-1)
    enc = np.floor((vec + 1.0) / 2.0 * 255.0 + 0.5)
    return np.clip(enc, 0, 255).astype(np.uint8)


def vanilla_palette(name):
    return Image.open(VANILLA_DIR / "map" / name).getpalette()


def make_palette_image(arr, palette, W, H):
    im = Image.frombytes("P", (W, H), np.ascontiguousarray(arr, dtype=np.uint8).tobytes())
    im.putpalette(palette)
    return im


def save_8bit_bmp(im, path):
    """8bit BMP 저장 후 biClrUsed(오프셋 46), biClrImportant(오프셋 50)를 0으로 바꾼다. 팔레트는 그대로."""
    im.save(path, "BMP")
    raw = bytearray(path.read_bytes())
    if int.from_bytes(raw[14:18], "little") < 40:
        raise MapgenError("%s: BMP 헤더가 BITMAPINFOHEADER 미만" % path.name)
    raw[46:50] = b"\x00\x00\x00\x00"
    raw[50:54] = b"\x00\x00\x00\x00"
    path.write_bytes(bytes(raw))


def make_dds_files(mod, terrain_idx, W, H):
    vdir = VANILLA_DIR / "map" / "terrain"
    (mod / "map" / "terrain").mkdir(parents=True, exist_ok=True)
    cm = np.asarray(Image.open(vdir / "colormap_rgb_cityemissivemask_a.dds").convert("RGBA"))
    vh, vw = cm.shape[:2]
    vt = np.asarray(Image.open(VANILLA_DIR / "map" / "terrain.bmp").resize((vw, vh), Image.NEAREST))
    flat_t = vt.ravel()
    cm_flat = cm.reshape(-1, 4)
    counts = np.bincount(flat_t, minlength=256)
    table = np.zeros((256, 3), np.float64)
    land_sel = flat_t != TERRAIN_PIXEL["ocean"]
    default = cm_flat[land_sel, :3].mean(axis=0)
    for ch in range(3):
        sums = np.bincount(flat_t, weights=cm_flat[:, ch].astype(np.float64), minlength=256)
        for idx in range(256):
            table[idx, ch] = sums[idx] / counts[idx] if counts[idx] > 0 else default[ch]
    # 우리 지도 절반 크기 (행/열 짝수 픽셀)
    t_half = terrain_idx[0::2, 0::2]
    rgb = np.rint(table[t_half]).clip(0, 255).astype(np.uint8)
    sea = t_half == TERRAIN_PIXEL["ocean"]
    rgb[sea] = (40, 60, 80)
    cmap = np.zeros((H // 2, W // 2, 4), np.uint8)
    cmap[:, :, :3] = rgb
    cmap[:, :, 3] = 0
    write_dds(mod / "map" / "terrain" / "colormap_rgb_cityemissivemask_a.dds", cmap)

    wv = np.asarray(Image.open(vdir / "colormap_water_0.dds").convert("RGBA"))
    sea_mean = np.rint(wv[vt == TERRAIN_PIXEL["ocean"]].mean(axis=0)).clip(0, 255).astype(np.uint8)
    for name, div in (("colormap_water_0.dds", 2), ("colormap_water_1.dds", 4), ("colormap_water_2.dds", 8)):
        arr = np.broadcast_to(sea_mean, (H // div, W // div, 4)).copy()
        write_dds(mod / "map" / "terrain" / name, arr)

    fv = np.asarray(Image.open(vdir / "fow_rgb_waterspec_a.dds").convert("RGBA"))
    fow_mean = np.rint(fv.reshape(-1, 4).mean(axis=0)).clip(0, 255).astype(np.uint8)
    write_dds(mod / "map" / "terrain" / "fow_rgb_waterspec_a.dds",
              np.broadcast_to(fow_mean, (H // 2, W // 2, 4)).copy())


def read_vanilla_weather_block():
    path = VANILLA_DIR / "map" / "strategicregions" / "1-Southern England.txt"
    lines = path.read_text(encoding="ascii").splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.strip() == "weather={":
            start = i
            break
    if start is None:
        raise MapgenError("바닐라 weather 블록을 찾지 못함")
    depth = 0
    block = []
    for ln in lines[start:]:
        block.append(ln)
        depth += ln.count("{") - ln.count("}")
        if depth == 0:
            break
    if depth != 0:
        raise MapgenError("바닐라 weather 블록 괄호 불일치")
    return block


# ---------------------------------------------------------------- 메인

def fmt_ids(values, indent, per_line=20):
    out = []
    for i in range(0, len(values), per_line):
        out.append(indent + " ".join(str(v) for v in values[i:i + per_line]))
    return out


def write_terra_scripts(mod, states, named_entries):
    """연결 규약 1·2: 정박지 이양 효과·가용 트리거, 이름 있는 주 id 머리글, named_states.json.
    이름 있는 주·정박지는 이벤트 대상(TU_STATE_*) 없이 주 id 숫자로 직접 참조한다. on_actions 파일은 더 이상 만들지 않는다."""
    by_name = {}
    for st in states:
        if st.get("name"):
            by_name[st["name"]] = st
        for al in st.get("aliases", []):
            by_name[al] = st
    anchors = [e for e in named_entries if e["kind"] == "anchor"]
    eff = ["# Generated by tools/mapgen/mapgen.py: named state / anchor -> state id"]
    for e in named_entries:
        eff.append("# %s = %d" % (e["name"], by_name[e["name"]]["id"]))
        for al in e.get("aliases", []):
            eff.append("# %s = %d (alias of %s)" % (al, by_name[al]["id"], e["name"]))
    eff.append("")
    trg = []
    for a in anchors:
        key = a["key"]
        me = "anchor_%s" % key
        sid = by_name[me]["id"]
        # 순서: (1) 목표 정박지를 RHO에 넘김 (RHO가 0개 주가 되는 것을 막는다) (2) 수도 이동 (3) 나머지 RHO 정박지를 원주인에게 반환
        eff.append("TU_anchor_%s_relocate_rho = {" % key)
        eff += ["\t%d = { transfer_state_to = RHO }" % sid,
                "\tset_capital = { state = %d remember_old_capital = no }" % sid]
        for o in anchors:
            if o is a:
                continue
            oid = by_name["anchor_%s" % o["key"]]["id"]
            eff += ["\tif = {",
                    "\t\tlimit = { %d = { is_owned_by = RHO } }" % oid,
                    "\t\t%d = { transfer_state_to = %s }" % (oid, o["return"]),
                    "\t}"]
        eff += ["}", ""]
        host = a["return"]     # rho_start는 가장 가까운 국가, 나머지는 원주인
        trg += ["TU_anchor_%s_available = {" % key,
                "\tNOT = { %d = { is_owned_by = RHO } }" % sid,
                "\t%s = { exists = yes }" % host,
                "\t%s = { NOT = { has_war_with = RHO } }" % host,
                "\t%d = { is_owned_by = %s }" % (sid, host),
                "}", ""]
    write_ascii(mod / "common" / "scripted_effects" / "tu_generated_states.txt", "\n".join(eff) + "\n")
    write_ascii(mod / "common" / "scripted_triggers" / "tu_generated_states.txt",
                ("\n".join(trg) + "\n") if trg else "\n")
    # 생성하지 않는다 (TU_init_named_states 호출 제거). 이전 빌드가 남긴 파일만 지운다.
    stale_onact = mod / "common" / "on_actions" / "tu_generated_on_actions.txt"
    if stale_onact.is_file():
        stale_onact.unlink()
    info = {
        "named": [{"name": e["name"], "state": by_name[e["name"]]["id"],
                   "owner": by_name[e["name"]]["owner"], "category": e["category"],
                   "province": e["pid"], "victory_points": e["victory_points"]}
                  for e in named_entries if e["kind"] == "named"],
        "anchors": [{"key": a["key"], "state": by_name["anchor_%s" % a["key"]]["id"], "host": a["host"],
                     "return": a["return"], "aliases": a.get("aliases", []), "province": a["pid"]}
                    for a in anchors],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "named_states.json").write_text(json.dumps(info, indent=1, ensure_ascii=True) + "\n", encoding="ascii")
    return info


def main(argv=None):
    global VANILLA_DIR
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="마스크 -> HOI4 지도 생성")
    parser.add_argument("--regions", required=True, help="지역 색 마스크 PNG")
    parser.add_argument("--config", required=True, help="regions.json")
    parser.add_argument("--mod", default=DEFAULT_MOD, help="모드 폴더 (기본 terra_universalis)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--vanilla", default=str(VANILLA_DIR), help="바닐라 설치 경로 (읽기 전용)")
    args = parser.parse_args(argv)

    VANILLA_DIR = Path(args.vanilla)
    mod = resolve_mod(args.mod)
    cfg = load_config(resolve_input(args.config))
    W, H = cfg["map_size"]
    regions = cfg["regions"]
    rng = np.random.default_rng(args.seed)

    region = load_mask(resolve_input(args.regions), W, H, regions)
    fixed_small = clean_small_components(region, len(regions))
    # 지역 4개가 만나는 2x2 블록 제거 -> 작은 성분 정리 -> 반복 (안정될 때까지)
    region_x = 0
    for _ in range(20):
        xf = remove_region_x_crosses(region)
        region_x += xf
        if xf == 0:
            break
        fixed_small += clean_small_components(region, len(regions))
    print("small components reassigned: %d (region X-cross pixels: %d)" % (fixed_small, region_x))

    cells = None
    if cfg.get("cells"):
        cpath = resolve_input(args.config).parent / cfg["cells"]
        ca = np.asarray(Image.open(cpath).convert("RGB")).astype(np.int64)
        if ca.shape[:2] != (H, W):
            raise MapgenError("cells 그림 크기가 지도와 다름: %s" % cpath.name)
        cells = ca[..., 0] * 65536 + ca[..., 1] * 256 + ca[..., 2]
    lab, label_region, label_comp = split_provinces(region, regions, rng, cells)
    id_map, provs = renumber(lab, label_region, label_comp, regions)
    N = len(provs) - 1
    province_attributes(provs, id_map, regions)
    colors = assign_colors(N, rng)
    adj = build_adjacency(id_map, N)
    set_coastal(provs, adj)
    for p in provs[1:]:
        p["rgb"] = colors[p["id"]]

    kind_lut = np.zeros(N + 1, np.int8)
    terrain_lut = np.zeros(N + 1, np.uint8)
    base_lut = np.zeros(N + 1, np.float64)
    for p in provs[1:]:
        kind_lut[p["id"]] = p["kind_code"]
        terrain_lut[p["id"]] = p["pixel_terrain"]
        base_lut[p["id"]] = p["base_height"]
    kind_px = kind_lut[id_map]
    terrain_px = terrain_lut[id_map]
    base_px = base_lut[id_map]

    slices = ndimage.find_objects(id_map)

    # ---- 이름 있는 주 / 정박지 (config의 named_states, anchors): 각자 1-프로빈스 주로 떼어 낸다
    named_entries = []
    for item in cfg.get("named_states", []):
        e = dict(item, kind="named")
        e["name"] = item["name"]
        e.setdefault("victory_points", 1)
        named_entries.append(e)
    for item in cfg.get("anchors", []):
        e = dict(item, kind="anchor")
        e["name"] = "anchor_%s" % item["key"]
        e["owner"] = item["host"]
        e["category"] = "tiny_island"
        e["manpower"] = 1000
        e["infrastructure"] = 3
        e["victory_points"] = 1
        named_entries.append(e)
    named_pid = {}
    for e in named_entries:
        pid = int(id_map[e["y"], e["x"]])
        if pid == 0 or provs[pid]["type"] != "land":
            raise MapgenError("이름 있는 주 %s가 육지 프로빈스가 아님 (프로빈스 %d)" % (e["name"], pid))
        if pid in named_pid:
            raise MapgenError("이름 있는 주 %s와 %s가 같은 프로빈스 %d" % (e["name"], named_pid[pid]["name"], pid))
        named_pid[pid] = e
        e["pid"] = pid
    # append_id 주는 소속 주의 분할에 그대로 들어가 있다가 분할 뒤에 떼어 낸다 (기존 주 id 유지)
    fixed_pid = [pid for pid, e in named_pid.items() if not e.get("append_id")]

    # ---- 주(state)
    comp_members = defaultdict(list)
    for p in provs[1:]:
        if p["type"] == "land" and p["id"] not in fixed_pid:
            comp_members[p["comp"]].append(p["id"])
    groups = []
    for comp_no in sorted(comp_members):
        members = comp_members[comp_no]
        coords = {u: (provs[u]["cy"], provs[u]["cx"]) for u in members}
        r = provs[members[0]]["region"]
        target = int(regions[r]["state_size"])
        for g in grow_groups(members, adj, coords, target):
            groups.append((r, g))
    for pid in fixed_pid:
        groups.append((provs[pid]["region"], [pid]))
    groups.sort(key=lambda t: (t[0], min(t[1])))
    # append_id 주: 정렬된 번호는 그대로 두고, 소속 주에서 프로빈스 하나만 떼어 맨 뒤(기존 최대 id + 1)에 붙인다
    for e in named_entries:
        if not e.get("append_id"):
            continue
        pid = e["pid"]
        for i, (r, g) in enumerate(groups):
            if pid in g:
                break
        else:
            raise MapgenError("append_id 주 %s: 프로빈스 %d가 어떤 주에도 없음" % (e["name"], pid))
        rest = [u for u in g if u != pid]
        if not rest:
            raise MapgenError("append_id 주 %s: 소속 주가 이 프로빈스뿐이라 떼어 낼 수 없음" % e["name"])
        keep = set(rest)
        seen = {rest[0]}
        todo = [rest[0]]
        while todo:
            u = todo.pop()
            for v in adj[u]:
                if v in keep and v not in seen:
                    seen.add(v)
                    todo.append(v)
        if len(seen) != len(keep):
            raise MapgenError("append_id 주 %s: 떼어 낸 뒤 소속 주가 끊어짐 (프로빈스 %d)" % (e["name"], pid))
        groups[i] = (r, rest)
        groups.append((provs[pid]["region"], [pid]))

    states = []
    state_of = [0] * (N + 1)
    for sid, (r, g) in enumerate(groups, start=1):
        reg = regions[r]
        area = sum(provs[u]["area"] for u in g)
        scy = sum(provs[u]["sy"] for u in g) / area
        scx = sum(provs[u]["sx"] for u in g) / area
        center = min(g, key=lambda u: ((provs[u]["cy"] - scy) ** 2 + (provs[u]["cx"] - scx) ** 2, u))
        coastal = any(provs[u]["coastal"] for u in g)
        meta = named_pid.get(g[0]) if len(g) == 1 else None
        if meta is not None:
            owner = meta["owner"]
            category = meta["category"]
            manpower = meta["manpower"]
            infra = meta["infrastructure"]
            vp = (meta["pid"], int(meta["victory_points"]))
            name = meta["name"]
            aliases = list(meta.get("aliases", []))
        else:
            owner = reg["owner"]
            category, manpower, infra = {"land": ("town", 50000, 2), "wasteland": ("pastoral", 5000, 1),
                                         "impassable": ("wasteland", 1000, 0)}[reg["kind"]]
            vp = (center, 1) if reg["kind"] == "land" else None
            name = None
            aliases = []
        st = {"id": sid, "region": r, "kind": reg["kind"], "owner": owner,
              "provinces": sorted(g), "area": area, "cy": scy, "cx": scx,
              "center": center, "coastal": coastal, "category": category, "manpower": manpower,
              "infra": infra, "vp": vp, "name": name, "aliases": aliases}
        states.append(st)
        for u in g:
            state_of[u] = sid
    for p in provs[1:]:
        p["state"] = state_of[p["id"]]
    state_lut = np.array(state_of, dtype=np.int32)
    state_px = state_lut[id_map]
    print("states: %d" % len(states))

    # ---- 전략 지역
    adj_state = defaultdict(set)
    for u in range(1, N + 1):
        su = state_of[u]
        if su == 0:
            continue
        for v in adj[u]:
            sv = state_of[v]
            if sv and sv != su:
                adj_state[su].add(sv)
    state_ids = [st["id"] for st in states]
    state_adj = {k: sorted(v) for k, v in adj_state.items()}
    state_coords = {st["id"]: (st["cy"], st["cx"]) for st in states}
    land_groups = grow_groups(state_ids, state_adj, state_coords, cfg["strategic_land_states"])
    land_groups.sort(key=lambda g: min(g))
    sea_ids = [p["id"] for p in provs[1:] if p["type"] in ("sea", "lake")]
    sea_coords = {u: (provs[u]["cy"], provs[u]["cx"]) for u in sea_ids}
    sea_groups = grow_groups(sea_ids, adj, sea_coords, cfg["strategic_sea_provinces"])
    sea_groups.sort(key=lambda g: min(g))

    strat = []   # {"id", "kind", "provinces", "cy", "cx", "area"}
    for g in land_groups:
        provs_in = sorted(p for sid in g for p in states[sid - 1]["provinces"])
        strat.append({"kind": "land", "provinces": provs_in, "states": g})
    for g in sea_groups:
        strat.append({"kind": "sea", "provinces": sorted(g), "states": []})
    for i, sr in enumerate(strat, start=1):
        sr["id"] = i
        area = sum(provs[u]["area"] for u in sr["provinces"])
        sr["cy"] = sum(provs[u]["sy"] for u in sr["provinces"]) / area
        sr["cx"] = sum(provs[u]["sx"] for u in sr["provinces"]) / area
    strat_of = [0] * (N + 1)
    for sr in strat:
        for u in sr["provinces"]:
            if strat_of[u]:
                raise MapgenError("전략 지역 중복 프로빈스 %d" % u)
            strat_of[u] = sr["id"]
    missing = [u for u in range(1, N + 1) if strat_of[u] == 0]
    if missing:
        raise MapgenError("전략 지역에 없는 프로빈스 %d개" % len(missing))
    print("strategic regions: %d (land %d, sea %d)" % (
        len(strat), sum(1 for s in strat if s["kind"] == "land"), sum(1 for s in strat if s["kind"] == "sea")))

    # ---- 수도 / 보급 / 철도
    capital = {}
    for st in states:
        if st["kind"] != "land":
            continue
        best = capital.get(st["owner"])
        if best is None or (st["area"], -st["id"]) > (best["area"], -best["id"]):
            capital[st["owner"]] = st
    # 이름 있는 주가 수도를 지정하면 (capital_of) 그것을 쓴다
    state_by_name = {st["name"]: st for st in states if st.get("name")}
    for e in named_entries:
        if e.get("capital_of"):
            capital[e["capital_of"]] = state_by_name[e["name"]]
    capital_state = {tag: st["id"] for tag, st in sorted(capital.items())}

    supply = set()
    for st in capital.values():
        supply.add(st["center"])
    gen_states = [st for st in states if st["kind"] in ("land", "wasteland")]
    for i, st in enumerate(gen_states):
        if i % 3 == 0:
            supply.add(st["center"])
    supply_lines = ["1 %d" % u for u in sorted(supply)]

    rail_lines = []
    owners = sorted({st["owner"] for st in states})
    for tag in owners:
        nodes = [st for st in states if st["owner"] == tag and st["kind"] in ("land", "wasteland")]
        if len(nodes) < 2:
            continue
        allowed = set()
        for st in nodes:
            allowed.update(st["provinces"])
        centers = [st["center"] for st in nodes]
        pts = [(provs[u]["cy"], provs[u]["cx"]) for u in centers]
        for a, b in mst_edges(pts):
            path = bfs_path(adj, centers[a], centers[b], allowed)
            if path and len(path) >= 2:
                rail_lines.append("1 %d %s" % (len(path), " ".join(str(u) for u in path)))
    print("railway lines: %d" % len(rail_lines))

    # ---- 높이 / 노멀 / 지형 이미지
    h_u8 = compute_heightmap(kind_px, base_px, rng, H, W)
    normal = compute_normal_map(h_u8)

    rivers_idx = np.where(kind_px != 0, 254, 255).astype(np.uint8)
    cities_idx = np.full((H, W), 15, np.uint8)
    Ht = int(round(H / TREE_SCALE))
    Wt = int(round(W / TREE_SCALE))
    ty = np.minimum(H - 1, ((np.arange(Ht) + 0.5) * H / Ht).astype(np.int64))
    tx = np.minimum(W - 1, ((np.arange(Wt) + 0.5) * W / Wt).astype(np.int64))
    t_sub = terrain_px[ty[:, None], tx[None, :]]
    trees_idx = np.where(t_sub == TERRAIN_PIXEL["forest"], 6,
                         np.where(t_sub == TERRAIN_PIXEL["jungle"], 28, 0)).astype(np.uint8)

    # ---- 건물 / 유닛 / 날씨 위치
    def y_of(row, col):
        h = float(h_u8[row, col])
        return h / 10.0 if kind_px[row, col] == 0 else max(WATER_Y_MIN, h / 10.0)

    def pos_text(row, col):
        return "%.2f;%.2f;%.2f" % (col, y_of(row, col), H - 1 - row)

    def sea_neighbor(row, col):
        for dy, dx in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            ny, nx = row + dy, col + dx
            if 0 <= ny < H and 0 <= nx < W and kind_px[ny, nx] == 2:
                return int(id_map[ny, nx])
        return 0

    coast_px = (kind_px == 0) & ndimage.binary_dilation(kind_px == 2)
    cys, cxs = np.nonzero(coast_px)
    coast_by_prov = defaultdict(list)
    for y, x in zip(cys.tolist(), cxs.tolist()):
        coast_by_prov[int(id_map[y, x])].append((y, x))

    def bline(state_id, name, row, col, sea_id):
        # buildings.txt: state;type;x;y;z;rotation;인접 바다 (없으면 0)
        return "%d;%s;%s;0.00;%d" % (state_id, name, pos_text(row, col), sea_id)

    build_lines = []         # 주 단위 + 프로빈스 단위 (buildings.txt: 위치 슬롯, 주 history에는 쓰지 않음)
    state_slices = ndimage.find_objects(state_px)

    for st in states:
        # 주 안의 내부 픽셀 (주 경계에서 2 이상 떨어진 픽셀)
        ys_sl, xs_sl = state_slices[st["id"] - 1]
        ys0, xs0 = ys_sl.start, xs_sl.start
        sub = state_px[ys_sl, xs_sl] == st["id"]
        dist = ndimage.distance_transform_edt(np.pad(sub, 1))[1:-1, 1:-1]
        inner = np.nonzero(sub & (dist >= 2))
        if inner[0].size == 0:
            inner = np.nonzero(sub)
        cy_arr = inner[0] + ys0
        cx_arr = inner[1] + xs0
        need = sum(c for _, c in STATE_BUILDINGS)
        picks = rng.choice(cy_arr.size, size=need, replace=cy_arr.size < need)
        k = 0
        for name, cnt in STATE_BUILDINGS:
            for _ in range(cnt):
                j = int(picks[k])
                k += 1
                row, col = int(cy_arr[j]), int(cx_arr[j])
                build_lines.append(bline(st["id"], name, row, col, 0))
        if st["coastal"]:
            cpix = []
            for u in st["provinces"]:
                cpix.extend(coast_by_prov.get(u, []))
            arr = np.array(cpix)
            d2s = (arr[:, 0] - st["cy"]) ** 2 + (arr[:, 1] - st["cx"]) ** 2
            row, col = cpix[int(np.argmin(d2s))]
            build_lines.append(bline(st["id"], DOCKYARD, row, col, sea_neighbor(row, col)))

    for p in provs[1:]:
        if p["type"] != "land":
            continue
        row, col = pole_pixel(id_map, slices, p["id"])
        p["pole"] = (row, col)
        for name in PROVINCE_BUILDINGS:
            build_lines.append(bline(p["state"], name, row, col, 0))
        if p["coastal"]:
            cpix = coast_by_prov[p["id"]]
            arr = np.array(cpix)
            d2s = (arr[:, 0] - p["cy"]) ** 2 + (arr[:, 1] - p["cx"]) ** 2
            crow, ccol = cpix[int(np.argmin(d2s))]
            sea_id = sea_neighbor(crow, ccol)
            for name in COASTAL_BUILDINGS:
                build_lines.append(bline(p["state"], name, crow, ccol, sea_id))
    print("buildings: %d lines" % len(build_lines))

    # 유닛 스택: 육지·바다 프로빈스, 같은 지점에 type 0~38 (rotation 0)
    unit_lines = []
    for p in provs[1:]:
        if p["type"] == "lake":
            continue
        if "pole" not in p:
            p["pole"] = pole_pixel(id_map, slices, p["id"])
        row, col = p["pole"]
        pt = pos_text(row, col)
        for t in UNIT_TYPES:
            unit_lines.append("%d;%d;%s;0.00;0.00" % (p["id"], t, pt))

    # 날씨 위치: 전략 지역마다 중심에 가장 가까운 프로빈스의 극점
    weather_lines = []
    for sr in strat:
        best = min(sr["provinces"], key=lambda u: ((provs[u]["cy"] - sr["cy"]) ** 2
                                                   + (provs[u]["cx"] - sr["cx"]) ** 2, u))
        if "pole" not in provs[best]:
            provs[best]["pole"] = pole_pixel(id_map, slices, best)
        row, col = provs[best]["pole"]
        weather_lines.append("%d;%s;small" % (sr["id"], pos_text(row, col)))

    # ---- 출력: 기존 생성 파일 비우기
    clean_outputs(mod)
    mapdir = mod / "map"
    mapdir.mkdir(parents=True, exist_ok=True)

    palette = np.zeros((N + 1, 3), np.uint8)
    for p in provs[1:]:
        palette[p["id"]] = p["rgb"]
    prov_rgb = palette[id_map]
    Image.fromarray(prov_rgb).save(mapdir / "provinces.bmp", "BMP")
    Image.fromarray(h_u8).save(mapdir / "heightmap.bmp", "BMP")
    Image.fromarray(normal).save(mapdir / "world_normal.bmp", "BMP")
    terrain_img = make_palette_image(terrain_px, vanilla_palette("terrain.bmp"), W, H)
    save_8bit_bmp(terrain_img, mapdir / "terrain.bmp")
    save_8bit_bmp(make_palette_image(rivers_idx, vanilla_palette("rivers.bmp"), W, H), mapdir / "rivers.bmp")
    save_8bit_bmp(make_palette_image(cities_idx, vanilla_palette("cities.bmp"), W, H), mapdir / "cities.bmp")
    save_8bit_bmp(make_palette_image(trees_idx, vanilla_palette("trees.bmp"), Wt, Ht), mapdir / "trees.bmp")
    make_dds_files(mod, terrain_px, W, H)

    lines = ["0;0;0;0;land;false;unknown;0"]
    for p in provs[1:]:
        r, g, b = p["rgb"]
        cont = 1 if p["type"] == "land" else 0
        lines.append("%d;%d;%d;%d;%s;%s;%s;%d" % (
            p["id"], r, g, b, p["type"], "true" if p["coastal"] else "false", p["def_terrain"], cont))
    write_ascii(mapdir / "definition.csv", "\n".join(lines) + "\n")
    write_ascii(mapdir / "adjacencies.csv",
                "From;To;Type;Through;start_x;start_y;stop_x;stop_y;adjacency_rule_name;Comment\n")
    write_ascii(mapdir / "adjacency_rules.txt", "")
    write_ascii(mapdir / "ambient_object.txt", "")
    write_ascii(mapdir / "positions.txt", "")
    write_ascii(mapdir / "continent.txt", "continents = {\n\tterra\n}\n")
    write_ascii(mapdir / "buildings.txt", "\n".join(build_lines))
    write_ascii(mapdir / "unitstacks.txt", "\n".join(unit_lines) + "\n")
    write_ascii(mapdir / "supply_nodes.txt", "\n".join(supply_lines) + "\n")
    write_ascii(mapdir / "railways.txt", "\n".join(rail_lines) + "\n")
    write_ascii(mapdir / "weatherpositions.txt", "\n".join(weather_lines) + "\n")

    # DDS / 이미지 완료. 지도 텍스트 완료.
    weather_block = read_vanilla_weather_block()
    for sr in strat:
        lines = ["strategic_region={", "\tid=%d" % sr["id"], '\tname="STRATEGICREGION_%d"' % sr["id"],
                 "\tprovinces={"]
        lines.extend(fmt_ids(sr["provinces"], "\t\t"))
        lines.append("\t}")
        lines.extend(weather_block)
        lines.append("}")
        write_ascii(mod / "map" / "strategicregions" / ("%d-STRATEGICREGION_%d.txt" % (sr["id"], sr["id"])),
                    "\n".join(lines) + "\n")

    write_ascii(mod / "map" / "supplyareas" / "1-SupplyArea.txt",
                'supply_area={\n\tid=1\n\tname="SUPPLYAREA_1"\n\tvalue=10\n\tstates={\n\t\t1\n\t}\n}\n')

    # AI 지역 / AI 전선: 대륙 하나, 전선 하나 (모든 육지 전략 지역). 첫 지역은 가장 큰 육지 전략 지역.
    land_sr = [sr for sr in strat if sr["kind"] == "land"]
    if not land_sr:
        raise MapgenError("육지 전략 지역이 없어 AI 전선을 만들 수 없음")
    biggest = max(land_sr, key=lambda sr: (sum(provs[u]["area"] for u in sr["provinces"]), -sr["id"]))
    theater_regions = [biggest["id"]] + [sr["id"] for sr in land_sr if sr["id"] != biggest["id"]]
    write_ascii(mod / "common" / "ai_areas" / "tu_areas.txt",
                "areas = { terra = { continents = { terra } } }\n")
    theater = ["TU_theater_terra = {", "\tname = TU_theater_terra", "\tai_will_do = {", "\t\tbase = 1", "\t}",
               "\tregions = {"]
    theater += fmt_ids(theater_regions, "\t\t")
    theater += ["\t}", "}"]
    write_ascii(mod / "common" / "ai_faction_theaters" / "tu_theaters.txt", "\n".join(theater) + "\n")

    ko_items, en_items = [], []
    capital_ids = {st["id"] for st in capital.values()}
    # 수도 주는 공장·기지 슬롯(산업 2 + 군수 1 + 기지 1)이 필요하므로 슬롯 0~1인 종류면 city(6 슬롯)로 올린다
    CAPITAL_LOW_SLOT_CATEGORIES = {"tiny_island", "small_island", "pastoral", "wasteland", "enclave", "rural"}
    for st in states:
        sid = st["id"]
        if sid in capital_ids and st["category"] in CAPITAL_LOW_SLOT_CATEGORIES:
            st["category"] = "city"
        L = ["state={", "\tid=%d" % sid, '\tname="STATE_%d"' % sid]
        if st["kind"] == "impassable":
            if sid in capital_ids:
                # 수도 주는 impassable이면 안 된다: 줄을 쓰지 않고 경고
                print("WARNING: capital state %d is impassable; impassable line not written" % sid)
            else:
                L.append("\timpassable = yes")
        L.append("\tmanpower = %d" % st["manpower"])
        L.append("")
        L.append("\tstate_category = %s" % st["category"])
        L.append("")
        L.append("\thistory={")
        L.append("\t\towner = %s" % st["owner"])
        if st["vp"]:
            L.append("\t\tvictory_points = { %d %d }" % st["vp"])
        L.append("\t\tbuildings = {")
        L.append("\t\t\tinfrastructure = %d" % st["infra"])
        if sid in capital_ids:
            # 실제 건설된 건물만: 수도에 공장·기지 초기 배치 (위치 슬롯은 buildings.txt)
            L.append("\t\t\tindustrial_complex = 2")
            L.append("\t\t\tarms_factory = 1")
            L.append("\t\t\tair_base = 1")
        L.append("\t\t}")
        L.append("\t\tadd_core_of = %s" % st["owner"])
        L.append("\t}")
        L.append("")
        L.append("\tprovinces={")
        L.extend(fmt_ids(st["provinces"], "\t\t"))
        L.append("\t}")
        L.append("\tlocal_supplies=0.0")
        L.append("}")
        write_ascii(mod / "history" / "states" / ("%d-STATE_%d.txt" % (sid, sid)), "\n".join(L) + "\n")
        ko_items.append(("STATE_%d" % sid, "주 %d" % sid))
        en_items.append(("STATE_%d" % sid, "State %d" % sid))
        if st["vp"]:
            ko_items.append(("VICTORY_POINTS_%d" % st["vp"][0], "거점 %d" % st["vp"][0]))
            en_items.append(("VICTORY_POINTS_%d" % st["vp"][0], "Point %d" % st["vp"][0]))
    for sr in strat:
        ko_items.append(("STRATEGICREGION_%d" % sr["id"], "전략 지역 %d" % sr["id"]))
        en_items.append(("STRATEGICREGION_%d" % sr["id"], "Strategic Region %d" % sr["id"]))
    ko_items.append(("SUPPLYAREA_1", "보급 지역 1"))
    en_items.append(("SUPPLYAREA_1", "Supply Area 1"))
    ko_items.append(("terra", "테라"))
    en_items.append(("terra", "Terra"))
    ko_items.append(("TU_theater_terra", "테라 전선"))
    en_items.append(("TU_theater_terra", "Terra Theater"))
    # 중복 키 방지 후 기록
    seen = set()
    ko_u, en_u = [], []
    for k, v in ko_items:
        if k not in seen:
            seen.add(k)
            ko_u.append((k, v))
    seen = set()
    for k, v in en_items:
        if k not in seen:
            seen.add(k)
            en_u.append((k, v))
    write_loc(mod, "map", ko_u, en_u)
    named_info = write_terra_scripts(mod, states, named_entries)
    print("named states: %d, anchors: %d" % (len(named_info["named"]), len(named_info["anchors"])))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index = {
        "map_size": [W, H],
        "states": [{"id": st["id"], "owner": st["owner"], "kind": st["kind"],
                    "provinces": st["provinces"], "center": st["center"],
                    "coastal": bool(st["coastal"]), "area": st["area"], "region": st["region"]}
                   for st in states],
        "capital_state": capital_state,
    }
    (OUT_DIR / "state_index.json").write_text(json.dumps(index, indent=1, ensure_ascii=True) + "\n",
                                              encoding="ascii")

    # 미리보기 PNG (사양서 추가 요구)
    # 미리보기: 지도 크기의 1/4 (최근접 축소)
    qsize = (W // 4, H // 4)
    Image.fromarray(prov_rgb).resize(qsize, Image.NEAREST).save(OUT_DIR / "preview_provinces.png")
    Image.fromarray(h_u8).resize(qsize, Image.NEAREST).save(OUT_DIR / "preview_heightmap.png")
    terrain_img.convert("RGB").resize(qsize, Image.NEAREST).save(OUT_DIR / "preview_terrain.png")

    n_land = sum(1 for p in provs[1:] if p["type"] == "land")
    n_lake = sum(1 for p in provs[1:] if p["type"] == "lake")
    n_sea = sum(1 for p in provs[1:] if p["type"] == "sea")
    print("MAPGEN provinces land=%d lake=%d sea=%d total=%d" % (n_land, n_lake, n_sea, N))
    print("MAPGEN states=%d strategic_regions=%d railway_lines=%d supply_nodes=%d" % (
        len(states), len(strat), len(rail_lines), len(supply_lines)))
    print("MAPGEN capitals=%s" % json.dumps(capital_state, sort_keys=True))
    print("MAPGEN done mod=%s" % mod)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except MapgenError as exc:
        print("MAPGEN ERROR: %s" % exc)
        sys.exit(1)
