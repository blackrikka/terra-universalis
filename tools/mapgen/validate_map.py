#!/usr/bin/env python3
"""생성된 지도 정적 검사 (사양서 7절). 생성 결과 파일을 다시 읽어서 검사한다.

사용법 (python -I):
    python -I tools/mapgen/validate_map.py --mod terra_universalis --countries tools/mapgen/test/countries.json

출력: MAPCHECK ok 또는 MAPCHECK FAIL + 항목별 오류. 종료 코드 0/1.
"""

import argparse
import glob
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

MAPGEN_DIR = Path(__file__).resolve().parent
PROJECT_DIR = MAPGEN_DIR.parent.parent
sys.path.insert(0, str(MAPGEN_DIR))
from dds import build_header  # noqa: E402

DEFAULT_MOD = "terra_universalis"
VANILLA_DIR = Path(r"G:\SteamLibrary\steamapps\common\Hearts of Iron IV")
REQUIRED_REPLACE = ["common/bookmarks", "common/country_tags", "common/countries", "common/characters",
                    "history/countries", "history/states", "history/units", "history/general",
                    "map/strategicregions", "map/supplyareas", "common/ai_areas",
                    "common/ai_faction_theaters"]
DEFAULT_COUNTRIES = MAPGEN_DIR / "test" / "countries.json"
LINT = PROJECT_DIR / "tools" / "lint" / "tu_lint.py"
TREE_SCALE = 3.4133
VALID_TERRAINS = {"plains", "forest", "hills", "mountain", "desert", "marsh", "jungle", "urban",
                  "lakes", "ocean", "unknown"}
STATE_COUNTS = {"arms_factory": 6, "industrial_complex": 6, "air_base": 1, "anti_air_building": 3,
                "fuel_silo": 1, "nuclear_reactor_spawn": 1, "radar_station": 1,
                "rocket_site_spawn": 1, "stronghold_network": 1, "synthetic_refinery": 1}
DOCKYARD = "dockyard"
PROVINCE_TYPES = ["bunker", "supply_node", "special_project_facility_spawn"]
COASTAL_TYPES = ["coastal_bunker", "naval_base_spawn", "naval_headquarters", "naval_supply_hub",
                 "floating_harbor"]
UNIT_TYPES = set(range(0, 39))
MAX_SHOWN = 12


class Checker:
    def __init__(self):
        self.errors = []

    def err(self, code, msg):
        self.errors.append("[%s] %s" % (code, msg))

    def many(self, code, items, fmt):
        for i, it in enumerate(items):
            if i >= MAX_SHOWN:
                self.err(code, "... 외 %d건" % (len(items) - MAX_SHOWN))
                break
            self.err(code, fmt(it))


# ---------------------------------------------------------------- 간단한 Clausewitz 파서

def strip_comment(line):
    out = []
    in_str = False
    for ch in line:
        if ch == '"':
            in_str = not in_str
        if ch == "#" and not in_str:
            break
        out.append(ch)
    return "".join(out)


TOKEN_RE = re.compile(r'"[^"]*"|\{|\}|=|[^\s{}=]+')


def parse_clausewitz(text):
    tokens = TOKEN_RE.findall("\n".join(strip_comment(ln) for ln in text.splitlines()))
    pos = 0

    def block():
        nonlocal pos
        items = []
        while pos < len(tokens):
            t = tokens[pos]
            if t == "}":
                pos += 1
                return items
            if t == "{":
                pos += 1
                items.append((None, block()))
                continue
            if t == "=":
                pos += 1
                continue
            if pos + 1 < len(tokens) and tokens[pos + 1] == "=":
                key = t
                pos += 2
                if pos < len(tokens) and tokens[pos] == "{":
                    pos += 1
                    items.append((key, block()))
                else:
                    val = tokens[pos] if pos < len(tokens) else ""
                    pos += 1
                    items.append((key, val))
            else:
                items.append((None, t))
                pos += 1
        return items

    return block()


def get1(items, key):
    for k, v in items:
        if k == key:
            return v
    return None


def bare_ints(value):
    if not isinstance(value, list):
        return []
    out = []
    for k, v in value:
        if k is None and not isinstance(v, list):
            out.append(int(v))
    return out


def raw_palette(raw):
    """BMP 원본 바이트에서 팔레트 (R,G,B) 목록. 개수는 biClrUsed (0이면 256)."""
    bisize = int.from_bytes(raw[14:18], "little")
    clr_used = int.from_bytes(raw[46:50], "little")
    n = clr_used if clr_used else 256
    start = 14 + bisize
    return [tuple(raw[start + 4 * i:start + 4 * i + 3][::-1]) for i in range(n)]


# ---------------------------------------------------------------- 메인 검사

def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="지도 정적 검사")
    parser.add_argument("--mod", default=DEFAULT_MOD)
    parser.add_argument("--countries", default=str(DEFAULT_COUNTRIES))
    parser.add_argument("--vanilla", default=str(VANILLA_DIR), help="바닐라 설치 경로 (읽기 전용)")
    args = parser.parse_args(argv)
    vanilla = Path(args.vanilla)

    mod = Path(args.mod)
    if not mod.is_absolute():
        cand = PROJECT_DIR / mod
        mod = cand if cand.is_dir() else mod.resolve()
    cpath = Path(args.countries)
    if not cpath.is_absolute():
        cpath = cpath if cpath.exists() else (PROJECT_DIR / cpath)
    chk = Checker()

    country_list = json.loads(cpath.read_text(encoding="utf-8"))
    countries = {c["tag"] for c in country_list}
    custom_tags = {c["tag"] for c in country_list if c.get("custom_characters")}
    dynamic_tags = {c["tag"] for c in country_list if c.get("dynamic")}   # 시작 주가 없는 국가 (REU)

    # 1. 이미지 크기 / 모드
    prov_img = Image.open(mod / "map" / "provinces.bmp")
    W, H = prov_img.size
    if prov_img.mode != "RGB":
        chk.err("1", "provinces.bmp 모드 %s (RGB여야 함)" % prov_img.mode)
    if W % 256 or H % 256:
        chk.err("1", "지도 크기 %dx%d가 256의 배수가 아님" % (W, H))

    def check_size(name, expect, modes):
        p = mod / "map" / name
        if not p.is_file():
            chk.err("1", "%s 없음" % name)
            return None
        im = Image.open(p)
        if im.size != expect:
            chk.err("1", "%s 크기 %s != 기대 %s" % (name, im.size, expect))
        if im.mode not in modes:
            chk.err("1", "%s 모드 %s (기대 %s)" % (name, im.mode, "/".join(modes)))
        return im

    check_size("terrain.bmp", (W, H), ("P",))
    check_size("rivers.bmp", (W, H), ("P",))
    check_size("cities.bmp", (W, H), ("P",))
    check_size("world_normal.bmp", (W // 2, H // 2), ("RGB",))
    tw, th = int(round(W / TREE_SCALE)), int(round(H / TREE_SCALE))
    check_size("trees.bmp", (tw, th), ("P",))
    heightmap = check_size("heightmap.bmp", (W, H), ("L", "P"))
    dds_specs = [("colormap_rgb_cityemissivemask_a.dds", 2), ("colormap_water_0.dds", 2),
                 ("colormap_water_1.dds", 4), ("colormap_water_2.dds", 8),
                 ("fow_rgb_waterspec_a.dds", 2)]
    for name, div in dds_specs:
        p = mod / "map" / "terrain" / name
        if not p.is_file():
            chk.err("1", "DDS %s 없음" % name)
            continue
        dw, dh = W // div, H // div
        data = p.read_bytes()
        if data[:128] != build_header(dw, dh):
            chk.err("1", "DDS %s 헤더가 사양(0절)과 다름 (기대 %dx%d)" % (name, dw, dh))
        if len(data) != 128 + dw * dh * 4:
            chk.err("1", "DDS %s 크기 %d != %d" % (name, len(data), 128 + dw * dh * 4))

    # 2. definition.csv <-> provinces.bmp
    def_lines = (mod / "map" / "definition.csv").read_text(encoding="ascii").splitlines()
    if def_lines[0] != "0;0;0;0;land;false;unknown;0":
        chk.err("2", "definition.csv 첫 줄이 0번 기본 줄이 아님")
    rows = []
    for ln in def_lines[1:]:
        f = ln.split(";")
        if len(f) != 8:
            chk.err("2", "definition.csv 필드 수 오류: %s" % ln)
            continue
        rows.append(f)
    N = len(rows)
    ids = [int(f[0]) for f in rows]
    if ids != list(range(1, N + 1)):
        chk.err("2", "definition id가 1..N 연속이 아님 (N=%d)" % N)
    ptype = {0: "unknown"}
    coastal = {}
    cont = {}
    def_codes = np.zeros(N, np.int64)
    for f in rows:
        pid = int(f[0])
        r, g, b = int(f[1]), int(f[2]), int(f[3])
        def_codes[pid - 1] = (r << 16) | (g << 8) | b
        t = f[4]
        ptype[pid] = t
        if t not in ("land", "sea", "lake"):
            chk.err("2", "prov %d: type 오류 %s" % (pid, t))
        if f[5] not in ("true", "false"):
            chk.err("2", "prov %d: coastal 오류 %s" % (pid, f[5]))
        coastal[pid] = f[5] == "true"
        if f[6] not in VALID_TERRAINS:
            chk.err("2", "prov %d: terrain 오류 %s" % (pid, f[6]))
        if (t == "sea" and f[6] != "ocean") or (t == "lake" and f[6] != "lakes") or (
                t == "land" and f[6] in ("ocean", "lakes")):
            chk.err("2", "prov %d: type %s와 terrain %s 불일치" % (pid, t, f[6]))
        cont[pid] = int(f[7])
        if cont[pid] != (1 if t == "land" else 0):
            chk.err("2", "prov %d: continent %d 오류" % (pid, cont[pid]))
    if len(set(def_codes.tolist())) != N or (def_codes == 0).any():
        chk.err("2", "definition 색이 중복되었거나 (0,0,0)을 사용")

    rgb = np.asarray(prov_img).astype(np.int64)
    code = (rgb[:, :, 0] << 16) | (rgb[:, :, 1] << 8) | rgb[:, :, 2]
    bmp_set = set(np.unique(code).tolist())
    def_set = set(def_codes.tolist())
    extra = sorted(bmp_set - def_set)
    if extra:
        chk.err("2", "provinces.bmp에 definition에 없는 색 %d개 (예: %s)" % (
            len(extra), ", ".join("#%06x" % c for c in extra[:5])))
    missing = sorted(def_set - bmp_set)
    if missing:
        chk.err("2", "definition에 있으나 provinces.bmp에 없는 색 %d개" % len(missing))
    order = np.argsort(def_codes)
    ks = def_codes[order]
    pos = np.clip(np.searchsorted(ks, code), 0, N - 1)
    hit = ks[pos] == code
    id_map = np.where(hit, order[pos] + 1, 0).astype(np.int32)

    # 3. 프로빈스 연결성
    slices = ndimage.find_objects(id_map)
    disconnected = []
    for pid in range(1, N + 1):
        sl = slices[pid - 1] if pid - 1 < len(slices) else None
        if sl is None:
            continue
        _, n = ndimage.label(id_map[sl] == pid)
        if n != 1:
            disconnected.append((pid, n))
    chk.many("3", disconnected, lambda t: "프로빈스 %d 연결 성분 %d개 (1개여야 함)" % t)

    # 4. X-교차
    a = id_map[:-1, :-1]
    b = id_map[:-1, 1:]
    c = id_map[1:, :-1]
    d = id_map[1:, 1:]
    cross = (a != b) & (a != c) & (a != d) & (b != c) & (b != d) & (c != d)
    cys, cxs = np.nonzero(cross)
    chk.many("4", list(zip(cys.tolist(), cxs.tolist())), lambda t: "X-교차 블록 (행 %d, 열 %d)" % t)
    if cys.size:
        chk.err("4", "X-교차 총 %d개" % cys.size)

    # 인접 관계 (4방향)
    adj = defaultdict(set)
    for p1, p2 in ((id_map[:, :-1], id_map[:, 1:]), (id_map[:-1, :], id_map[1:, :])):
        m = p1 != p2
        for u, v in zip(p1[m].tolist(), p2[m].tolist()):
            adj[u].add(v)
            adj[v].add(u)

    # 4-b. 주 파일
    state_files = sorted(glob.glob(str(mod / "history" / "states" / "*.txt")))
    state_of = [0] * (N + 1)
    state_info = {}
    state_dup = []
    state_name_bad = []
    for path in state_files:
        p = Path(path)
        text = p.read_bytes().decode("utf-8-sig")
        top = parse_clausewitz(text)
        st = get1(top, "state")
        if not isinstance(st, list):
            chk.err("5", "%s: state 블록 없음" % p.name)
            continue
        sid = int(get1(st, "id"))
        if p.name != "%d-STATE_%d.txt" % (sid, sid):
            state_name_bad.append(p.name)
        hist = get1(st, "history") or []
        owner = get1(hist, "owner")
        provs = bare_ints(get1(st, "provinces"))
        vp = bare_ints(get1(hist, "victory_points"))
        impassable = get1(st, "impassable") == "yes"
        bl = get1(hist, "buildings") or []
        if sid in state_info:
            state_dup.append(sid)
        state_info[sid] = {"owner": owner, "provs": provs, "vp": vp, "impassable": impassable,
                           "buildings": bl, "file": p.name, "category": get1(st, "state_category")}
        for pid in provs:
            if state_of[pid]:
                state_dup.append((sid, pid))
            state_of[pid] = sid
    chk.many("5", state_name_bad, lambda n: "주 파일 이름이 id와 맞지 않음: %s" % n)
    chk.many("5", state_dup, lambda t: "주/프로빈스 중복 배정: %s" % (t,))
    S = len(state_info)
    if sorted(state_info) != list(range(1, S + 1)):
        chk.err("5", "주 id가 1..S 연속이 아님 (S=%d)" % S)
    land_not_in = [p for p in range(1, N + 1) if ptype[p] == "land" and state_of[p] == 0]
    chk.many("5", land_not_in, lambda p: "land 프로빈스 %d가 어떤 주에도 없음" % p)
    water_in = [p for p in range(1, N + 1) if ptype.get(p) != "land" and state_of[p] != 0]
    chk.many("5", water_in, lambda p: "바다/호수 프로빈스 %d가 주에 속함" % p)
    for sid, info in sorted(state_info.items()):
        if info["owner"] not in countries:
            chk.err("11", "주 %d의 owner %s가 countries.json에 없음" % (sid, info["owner"]))
        if not info["provs"]:
            chk.err("5", "주 %d에 프로빈스가 없음" % sid)
        for pid in info["provs"]:
            if not (1 <= pid <= N):
                chk.err("5", "주 %d: 알 수 없는 프로빈스 %d" % (sid, pid))
        if info["vp"] and info["vp"][0] not in info["provs"]:
            chk.err("5", "주 %d: victory_points 프로빈스 %d가 주에 없음" % (sid, info["vp"][0]))

    # 4-c. 전략 지역
    sr_of = [0] * (N + 1)
    sr_info = {}
    for path in sorted(glob.glob(str(mod / "map" / "strategicregions" / "*.txt"))):
        p = Path(path)
        top = parse_clausewitz(p.read_bytes().decode("utf-8-sig"))
        sr = get1(top, "strategic_region")
        if not isinstance(sr, list):
            chk.err("6", "%s: strategic_region 블록 없음" % p.name)
            continue
        rid = int(get1(sr, "id"))
        provs = bare_ints(get1(sr, "provinces"))
        sr_info[rid] = provs
        for pid in provs:
            if sr_of[pid]:
                chk.err("6", "프로빈스 %d가 전략 지역 %d와 %d에 중복" % (pid, sr_of[pid], rid))
            sr_of[pid] = rid
    if sorted(sr_info) != list(range(1, len(sr_info) + 1)):
        chk.err("6", "전략 지역 id가 1..R 연속이 아님")
    chk.many("6", [p for p in range(1, N + 1) if sr_of[p] == 0],
             lambda p: "프로빈스 %d가 전략 지역에 없음" % p)
    # 주 하나의 프로빈스는 전략 지역 하나에만 있어야 한다 (어기면 게임이 로딩 중 터진다)
    multi_sr = [(sid, sorted({sr_of[p] for p in info["provs"]})) for sid, info in sorted(state_info.items())
                if len({sr_of[p] for p in info["provs"]}) > 1]
    chk.many("6", multi_sr, lambda t: "주 %d가 전략 지역 여러 개에 걸침: %s" % t)
    # 바다 전략 지역은 한 덩어리여야 한다 (끊어지면 일반 모드에서 로딩 중 강제 종료, -debug 에서는 "is fractioned")
    fractioned = []
    for rid, provs in sorted(sr_info.items()):
        seas = {p for p in provs if ptype[p] == "sea"}
        if not seas:
            continue
        seen, stack = set(), [min(seas)]
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            stack.extend(v for v in adj.get(u, ()) if v in seas and v not in seen)
        if seen != seas:
            fractioned.append((rid, sorted(seas - seen)[:6]))
    chk.many("6", fractioned, lambda t: "바다 전략 지역 %d가 끊어짐: %s" % t)
    # 게임은 8픽셀 이하 프로빈스에 경고를 낸다
    px_count = np.bincount(id_map.ravel(), minlength=N + 1)
    chk.many("6", [p for p in range(1, N + 1) if 0 < px_count[p] <= 8],
             lambda p: "프로빈스 %d가 %d픽셀 (9 이상이어야 함)" % (p, px_count[p]))

    # 7. coastal 플래그
    bad_coast = []
    for pid in range(1, N + 1):
        nb = adj.get(pid, set())
        if ptype[pid] == "sea":
            expect = any(ptype[v] != "sea" for v in nb)
        else:
            expect = any(ptype[v] == "sea" for v in nb)
        if expect != coastal[pid]:
            bad_coast.append((pid, coastal[pid], expect))
    chk.many("7", bad_coast, lambda t: "프로빈스 %d coastal=%s, 인접 관계상 %s" % (t[0], t[1], t[2]))

    # 8. 철도 / 보급
    rail_path = mod / "map" / "railways.txt"
    rail_count = 0
    for ln_no, ln in enumerate(rail_path.read_text(encoding="ascii").splitlines(), 1):
        if not ln.strip():
            continue
        f = [int(x) for x in ln.split()]
        level, count, seq = f[0], f[1], f[2:]
        rail_count += 1
        if level < 1 or count != len(seq) or count < 2:
            chk.err("8", "railways.txt %d줄: 형식 오류" % ln_no)
            continue
        for u in seq:
            if not (1 <= u <= N):
                chk.err("8", "railways.txt %d줄: 알 수 없는 프로빈스 %d" % (ln_no, u))
            elif ptype[u] != "land":
                chk.err("8", "railways.txt %d줄: 프로빈스 %d가 육지가 아님" % (ln_no, u))
        for u, v in zip(seq, seq[1:]):
            if v not in adj.get(u, set()):
                chk.err("8", "railways.txt %d줄: %d와 %d는 인접하지 않음" % (ln_no, u, v))
    sn_count = 0
    for ln_no, ln in enumerate(mod.joinpath("map", "supply_nodes.txt").read_text(encoding="ascii").splitlines(), 1):
        if not ln.strip():
            continue
        f = ln.split()
        sn_count += 1
        if len(f) != 2 or f[0] != "1":
            chk.err("8", "supply_nodes.txt %d줄: 형식 오류" % ln_no)
            continue
        u = int(f[1])
        if not (1 <= u <= N) or ptype[u] != "land":
            chk.err("8", "supply_nodes.txt %d줄: 프로빈스 %d가 육지가 아님" % (ln_no, u))

    # 9. buildings / unitstacks / weatherpositions (좌표 -> 픽셀)
    def pixel_of(x, z):
        col = int(round(x))
        row = H - 1 - int(round(z))
        if not (0 <= col < W and 0 <= row < H):
            return None
        return row, col

    b_counts = defaultdict(lambda: defaultdict(int))   # state -> type -> count
    b_prov_types = defaultdict(set)                    # prov -> set(types)
    b_prov_state = {}
    b_bad = []
    coastal_states = set()
    for u in range(1, N + 1):
        if ptype[u] == "land" and coastal[u] and state_of[u]:
            coastal_states.add(state_of[u])
    for ln_no, ln in enumerate(mod.joinpath("map", "buildings.txt").read_text(encoding="ascii").splitlines(), 1):
        if not ln.strip():
            continue
        f = ln.split(";")
        if len(f) != 7:
            b_bad.append("buildings.txt %d줄: 필드 수 %d" % (ln_no, len(f)))
            continue
        sid = int(f[0])
        typ = f[1]
        x, y, z = float(f[2]), float(f[3]), float(f[4])
        sea_id = int(f[6])
        px = pixel_of(x, z)
        if px is None:
            b_bad.append("buildings.txt %d줄: 좌표가 지도 밖" % ln_no)
            continue
        row, col = px
        pid = int(id_map[row, col])
        if ptype.get(pid) != "land":
            b_bad.append("buildings.txt %d줄: 좌표 픽셀이 육지가 아님 (%s)" % (ln_no, typ))
            continue
        if state_of[pid] != sid:
            b_bad.append("buildings.txt %d줄: 좌표 픽셀이 주 %d에 속하지 않음 (주 %d)" % (ln_no, sid, state_of[pid]))
            continue
        if typ in STATE_COUNTS or typ == DOCKYARD:
            b_counts[sid][typ] += 1
            if typ == DOCKYARD:
                if sea_id == 0 or ptype.get(sea_id) != "sea" or sea_id not in adj.get(pid, set()):
                    b_bad.append("buildings.txt %d줄: dockyard의 바다 id %d가 인접하지 않음" % (ln_no, sea_id))
        elif typ in PROVINCE_TYPES:
            b_prov_types[pid].add(typ)
            b_prov_state[pid] = sid
        elif typ in COASTAL_TYPES:
            b_prov_types[pid].add(typ)
            b_prov_state[pid] = sid
            if sea_id == 0 or ptype.get(sea_id) != "sea" or sea_id not in adj.get(pid, set()):
                b_bad.append("buildings.txt %d줄: %s의 바다 id %d가 인접하지 않음" % (ln_no, typ, sea_id))
        else:
            b_bad.append("buildings.txt %d줄: 알 수 없는 종류 %s" % (ln_no, typ))
    chk.many("9", b_bad, lambda s: s)
    for sid in sorted(state_info):
        for typ, cnt in STATE_COUNTS.items():
            if b_counts[sid][typ] != cnt:
                chk.err("9", "주 %d: %s %d개 (기대 %d)" % (sid, typ, b_counts[sid][typ], cnt))
        has_dock = b_counts[sid][DOCKYARD]
        if sid in coastal_states and has_dock != 1:
            chk.err("9", "해안 주 %d: dockyard %d개 (기대 1)" % (sid, has_dock))
        if sid not in coastal_states and has_dock:
            chk.err("9", "내륙 주 %d에 dockyard가 있음" % sid)
    no_bunker = [u for u in range(1, N + 1) if ptype[u] == "land" and "bunker" not in b_prov_types[u]]
    chk.many("9", no_bunker, lambda u: "육지 프로빈스 %d에 bunker가 없음" % u)

    # 주 history 건물: 실제 건설된 건물만 쓴다. 위치 슬롯(buildings.txt)과는 대조하지 않는다.
    #  - 모든 주: infrastructure (주 종류별 값), 그 밖의 키는 허용 목록 안에서만
    #  - 수도 주: industrial_complex 2, arms_factory 1, air_base 1
    #  - 프로빈스 단위 블록은 없어야 한다
    capital_by_state = {}
    for path in sorted(glob.glob(str(mod / "history" / "countries" / "*.txt"))):
        top = parse_clausewitz(Path(path).read_bytes().decode("utf-8-sig"))
        cap = get1(top, "capital")
        if cap is None:
            chk.err("9", "%s: capital 없음" % Path(path).name)
        elif int(cap) not in state_info:
            chk.err("9", "%s: capital %s가 주 목록에 없음" % (Path(path).name, cap))
        elif Path(path).name.split(" - ")[0] in dynamic_tags:
            pass    # dynamic 국가의 수도는 다른 국가가 가진 주라서 건설 검사 대상이 아니다
        else:
            capital_by_state[int(cap)] = Path(path).name
    HISTORY_KEYS = {"infrastructure", "industrial_complex", "arms_factory", "air_base", "dockyard"}
    CAPITAL_BUILDINGS = {"industrial_complex": "2", "arms_factory": "1", "air_base": "1"}
    for sid, info in sorted(state_info.items()):
        vals = {}
        for k, v in info["buildings"]:
            if k is None:
                continue
            if isinstance(v, list):
                # 사양서 68: 국경 요새 <프로빈스> = { bunker = N } 만 허용
                if not (k.isdigit() and all(kk == "bunker" for kk, _ in v)):
                    chk.err("9", "주 파일 %s: 프로빈스 단위 건물 블록 %s는 허용되지 않음" % (info["file"], k))
                continue
            if k not in HISTORY_KEYS:
                chk.err("9", "주 파일 %s: 허용되지 않은 건물 키 %s" % (info["file"], k))
            vals[k] = v
        if info["impassable"]:
            infra = "0"
        elif info["category"] == "tu_hex":
            infra = vals.get("infrastructure")      # 나뉜 주 (사양서 49): 원래 주의 인프라를 그대로 쓴다
        elif info["category"] == "pastoral":
            infra = "1"
        elif info["category"] == "town":
            infra = "2"
        elif info["category"] == "tiny_island":
            infra = "3"
        elif info["category"] == "city" and sid in capital_by_state:
            # 수도 주는 낮은 슬롯 종류에서 city로 올라간다 (mapgen): 원래 종류의 인프라 값을 그대로 쓴다
            infra = vals.get("infrastructure")
        else:
            infra = None
        if infra is None:
            chk.err("9", "주 파일 %s: state_category %s 알 수 없음" % (info["file"], info["category"]))
        elif vals.get("infrastructure") != infra:
            chk.err("9", "주 파일 %s: infrastructure %s (기대 %s)" % (
                info["file"], vals.get("infrastructure"), infra))
        if sid in capital_by_state:
            # 사양서 56: 체급 공장(tiers.py)이 주 히스토리에 들어가므로 수도는 기본값 이상이면 된다
            for k, v in CAPITAL_BUILDINGS.items():
                got = vals.get(k)
                ok = got == v if k == "air_base" else (got is not None and got.isdigit() and int(got) >= int(v))
                if not ok:
                    chk.err("9", "수도 주 %d (%s): %s %s (기대 %s%s)" % (
                        sid, capital_by_state[sid], k, got, v, "" if k == "air_base" else " 이상"))
            extra = set(vals) - {"infrastructure"} - set(CAPITAL_BUILDINGS)
        else:
            extra = set(vals) - {"infrastructure", "industrial_complex", "arms_factory"}
        if extra:
            chk.err("9", "주 파일 %s: 건물 %s는 이 주에 허용되지 않음" % (info["file"], sorted(extra)))

    # 수도 주 슬롯 검사: 바닐라 state_category별 슬롯 수 안에 공장·기지·조선소가 들어가야 한다 (빌드 중 "too many buildings" 방지)
    VANILLA_SLOTS = {"city": 6, "large_city": 8, "large_town": 5, "town": 4, "rural": 2, "pastoral": 1,
                     "small_island": 1, "tu_hex": 1, "large_island": 3, "tiny_island": 0, "wasteland": 0, "enclave": 0,
                     "metropolis": 10, "megalopolis": 12}
    SLOT_BUILDINGS = {"industrial_complex", "arms_factory", "dockyard"}
    for sid in sorted(state_info):     # 사양서 56: 모든 주 (체급 공장이 수도 밖에도 들어간다)
        info = state_info[sid]
        slots = VANILLA_SLOTS.get(info["category"])
        if slots is not None:
            m_extra = re.search(r"add_extra_state_shared_building_slots\s*=\s*(\d+)",
                                (mod / "history" / "states" / info["file"]).read_text(encoding="utf-8-sig"))
            slots += int(m_extra.group(1)) if m_extra else 0
        if slots is None:
            chk.err("9", "수도 주 %d (%s): state_category %s의 슬롯 수를 알 수 없음" % (
                sid, info["file"], info["category"]))
            continue
        used = sum(int(v) for k, v in info["buildings"]
                   if k in SLOT_BUILDINGS and not isinstance(v, list))
        if used > slots:
            chk.err("9", "수도 주 %d (%s): 공장·기지·조선소 %d개 > 슬롯 %d (state_category %s)" % (
                sid, info["file"], used, slots, info["category"]))

    # 국가 파일 참조: common/country_tags/*.txt 가 가리키는 파일이 우리 common/ 아래 있어야 한다
    for path in sorted(glob.glob(str(mod / "common" / "country_tags" / "*.txt"))):
        text = Path(path).read_bytes().decode("utf-8-sig")
        for m in re.finditer(r'"(countries/[^"]+)"', text):
            if not (mod / "common" / m.group(1)).is_file():
                chk.err("14", "%s가 참조하는 %s가 common/ 아래 없음" % (Path(path).name, m.group(1)))

    # unitstacks
    u_types = defaultdict(set)
    u_bad = []
    for ln_no, ln in enumerate(mod.joinpath("map", "unitstacks.txt").read_text(encoding="ascii").splitlines(), 1):
        if not ln.strip():
            continue
        f = ln.split(";")
        if len(f) != 7:
            u_bad.append("unitstacks.txt %d줄: 필드 수 %d" % (ln_no, len(f)))
            continue
        pid, typ = int(f[0]), int(f[1])
        px = pixel_of(float(f[2]), float(f[4]))
        if not (1 <= pid <= N) or ptype[pid] == "lake":
            u_bad.append("unitstacks.txt %d줄: 프로빈스 %d 부적합" % (ln_no, pid))
            continue
        if typ not in UNIT_TYPES:
            u_bad.append("unitstacks.txt %d줄: type %d 범위 밖" % (ln_no, typ))
        if px is None:
            u_bad.append("unitstacks.txt %d줄: 좌표가 지도 밖" % ln_no)
            continue
        if int(id_map[px]) != pid:
            u_bad.append("unitstacks.txt %d줄: 좌표 픽셀이 프로빈스 %d에 속하지 않음" % (ln_no, pid))
        u_types[pid].add(typ)
    chk.many("9", u_bad, lambda s: s)
    chk.many("9", [u for u in range(1, N + 1) if ptype[u] != "lake" and u_types.get(u, set()) != UNIT_TYPES],
             lambda u: "프로빈스 %d: unitstacks type 0~38 불완전" % u)

    # weatherpositions
    for ln_no, ln in enumerate(mod.joinpath("map", "weatherpositions.txt").read_text(encoding="ascii").splitlines(), 1):
        if not ln.strip():
            continue
        f = ln.split(";")
        rid = int(f[0])
        px = pixel_of(float(f[1]), float(f[3]))
        if rid not in sr_info or px is None:
            chk.err("9", "weatherpositions.txt %d줄: 전략 지역/좌표 오류" % ln_no)
            continue
        pid = int(id_map[px])
        if sr_of[pid] != rid:
            chk.err("9", "weatherpositions.txt %d줄: 좌표 픽셀이 전략 지역 %d에 속하지 않음" % (ln_no, rid))

    # 10. 높이맵
    if heightmap is not None:
        h = np.asarray(heightmap).astype(np.int64)
        land_pix = np.isin(id_map, [p for p in range(1, N + 1) if ptype[p] == "land"])
        water_pix = np.isin(id_map, [p for p in range(1, N + 1) if ptype[p] != "land"])
        low_land = int((h[land_pix] < 96).sum())
        high_water = int((h[water_pix] > 94).sum())
        if low_land:
            chk.err("10", "육지 픽셀 %d개가 96 미만" % low_land)
        if high_water:
            chk.err("10", "물 픽셀 %d개가 94 초과" % high_water)

    # 15. 프로빈스 경계 상자: 폭 < W/9, 높이 < H/9 (수정1 F)
    lim_w = W / 9.0
    lim_h = H / 9.0
    bbox_bad = []
    for pid in range(1, N + 1):
        sl = slices[pid - 1] if pid - 1 < len(slices) else None
        if sl is None:
            continue
        bw = sl[1].stop - sl[1].start
        bh = sl[0].stop - sl[0].start
        if bw >= lim_w or bh >= lim_h:
            bbox_bad.append((pid, bw, bh))
    chk.many("15", bbox_bad, lambda t: "프로빈스 %d 경계 상자 %dx%d (폭 < %.1f, 높이 < %.1f 이어야 함)"
             % (t[0], t[1], t[2], lim_w, lim_h))

    # 16. 8bit BMP 헤더 biClrUsed/biClrImportant = 0, 팔레트는 바닐라와 같음 (수정1 E)
    for name in ("terrain.bmp", "rivers.bmp", "cities.bmp", "trees.bmp"):
        p = mod / "map" / name
        raw = p.read_bytes()
        clr_used = int.from_bytes(raw[46:50], "little")
        clr_imp = int.from_bytes(raw[50:54], "little")
        if clr_used != 0 or clr_imp != 0:
            chk.err("16", "%s: biClrUsed=%d biClrImportant=%d (둘 다 0이어야 함)" % (name, clr_used, clr_imp))
        our_pal = raw_palette(raw)
        van_pal = raw_palette((vanilla / "map" / name).read_bytes())
        if our_pal[:len(van_pal)] != van_pal:
            first = next(i for i, (a, b) in enumerate(zip(our_pal, van_pal)) if a != b)
            chk.err("16", "%s: 팔레트가 바닐라와 다름 (첫 차이 인덱스 %d)" % (name, first))

    # 17. 국가 지도자 (수정1 C): GFX 정의, 캐릭터 파일, recruit_character, 로컬라이제이션
    gfx_defined = set()
    for g in glob.glob(str(vanilla / "interface" / "*.gfx")) + glob.glob(str(mod / "interface" / "*.gfx")):   # 모드 초상화 (사양서 47)
        text = Path(g).read_bytes().decode("utf-8-sig", errors="replace")
        gfx_defined.update(x.lower() for x in re.findall(r'name\s*=\s*"([^"]+)"', text))
    loc_text = {}
    for lang in ("korean", "english"):
        lp = mod / "localisation" / lang / "replace" / ("tu_countries_l_%s.yml" % lang)
        loc_text[lang] = lp.read_bytes().decode("utf-8-sig") if lp.is_file() else ""
    for tag in sorted(countries - custom_tags):
        leader_key = "%s_leader" % tag
        cf = mod / "common" / "characters" / ("%s.txt" % tag)
        if not cf.is_file():
            chk.err("17", "%s: common/characters/%s.txt 없음" % (tag, tag))
        else:
            top = parse_clausewitz(cf.read_bytes().decode("utf-8-sig"))
            chars = get1(top, "characters") or []
            leader = get1(chars, leader_key)
            if not isinstance(leader, list):
                chk.err("17", "%s: 캐릭터 %s 블록 없음" % (tag, leader_key))
            else:
                portraits = get1(leader, "portraits") or []
                civ = get1(portraits, "civilian") or []
                large = (get1(civ, "large") or "").strip('"')
                if not large:
                    chk.err("17", "%s: civilian large 초상화 GFX 없음" % tag)
                elif large.lower() not in gfx_defined:
                    chk.err("17", "%s: 초상화 GFX %s가 바닐라·모드 interface/*.gfx에 정의되지 않음" % (tag, large))
        hist_files = glob.glob(str(mod / "history" / "countries" / ("%s - *.txt" % tag)))
        recruits = []
        for hf in hist_files:
            top = parse_clausewitz(Path(hf).read_bytes().decode("utf-8-sig"))
            recruits += [v for k, v in top if k == "recruit_character"]
        if recruits != [leader_key]:
            chk.err("17", "%s: 국가 파일 recruit_character %s (기대 %s)" % (tag, recruits, leader_key))
        for lang in ("korean", "english"):
            if not re.search(r"^\s*%s:\d*\s+\"" % re.escape(leader_key), loc_text[lang], re.M):
                chk.err("17", "%s: %s 로컬라이제이션 키 없음" % (lang, leader_key))

    # 18. 초상화 (수정1 A): continent = terra 하나에 바닐라 europe의 하위 블록 전부
    pf = mod / "portraits" / "tu_portraits.txt"
    expected_keys = set()
    for rel in ("portraits/00_portraits.txt", "portraits/998_scientist_portraits.txt"):
        vtop = parse_clausewitz((vanilla / rel).read_bytes().decode("utf-8-sig"))
        for k, v in vtop:
            if k == "continent" and isinstance(v, list) and get1(v, "name") == "europe":
                expected_keys |= {kk for kk, vv in v if kk and isinstance(vv, list)}
    if not pf.is_file():
        chk.err("18", "portraits/tu_portraits.txt 없음")
    else:
        ptop = parse_clausewitz(pf.read_bytes().decode("utf-8-sig"))
        terra = [v for k, v in ptop if k == "continent" and isinstance(v, list) and get1(v, "name") == "terra"]
        if len(terra) != 1:
            chk.err("18", "continent name=terra 블록이 %d개 (1개여야 함)" % len(terra))
        else:
            have = {kk for kk, vv in terra[0] if kk and isinstance(vv, list)}
            if not expected_keys:
                chk.err("18", "바닐라 europe 블록을 찾지 못함")
            for key in sorted(expected_keys - have):
                chk.err("18", "continent terra에 하위 블록 %s 없음" % key)

    # 19. 이름 (수정1 B): 태그마다 male/female names, surnames, callsigns 각 20개 이상
    nf = mod / "common" / "names" / "tu_names.txt"
    if not nf.is_file():
        chk.err("19", "common/names/tu_names.txt 없음")
    else:
        ntop = parse_clausewitz(nf.read_bytes().decode("utf-8-sig"))

        def strings_in(items):
            return sum(1 for k, v in items if k is None and isinstance(v, str))

        for tag in sorted(countries):
            blocks = [v for k, v in ntop if k == tag and isinstance(v, list)]
            if not blocks:
                chk.err("19", "%s: tu_names.txt에 블록 없음" % tag)
                continue
            b = blocks[0]
            counts = {
                "male.names": strings_in(get1(get1(b, "male") or [], "names") or []),
                "female.names": strings_in(get1(get1(b, "female") or [], "names") or []),
                "surnames": strings_in(get1(b, "surnames") or []),
                "callsigns": strings_in(get1(b, "callsigns") or []),
            }
            for key, n in counts.items():
                if n < 20:
                    chk.err("19", "%s: %s %d개 (최소 20)" % (tag, key, n))

    # 20. AI 지역 / 전선 (수정1 D)
    area_file = mod / "common" / "ai_areas" / "tu_areas.txt"
    theater_file = mod / "common" / "ai_faction_theaters" / "tu_theaters.txt"
    if not area_file.is_file():
        chk.err("20", "common/ai_areas/tu_areas.txt 없음")
    else:
        atop = parse_clausewitz(area_file.read_bytes().decode("utf-8-sig"))
        areas = get1(atop, "areas") or []
        terra_area = get1(areas, "terra") or []
        conts = get1(terra_area, "continents") or []
        if "terra" not in [v for k, v in conts if k is None]:
            chk.err("20", "tu_areas.txt: continents에 terra 없음")
    if not theater_file.is_file():
        chk.err("20", "common/ai_faction_theaters/tu_theaters.txt 없음")
    else:
        ttop = parse_clausewitz(theater_file.read_bytes().decode("utf-8-sig"))
        th = [v for k, v in ttop if k == "TU_theater_terra" and isinstance(v, list)]
        if len(th) != 1:
            chk.err("20", "TU_theater_terra 블록이 %d개 (1개여야 함)" % len(th))
        else:
            regions = [int(v) for k, v in (get1(th[0], "regions") or []) if k is None]
            land_sr = sorted(rid for rid, provs in sr_info.items() if provs and all(ptype[p] == "land" for p in provs))
            if sorted(regions) != land_sr:
                chk.err("20", "theater 지역 %s != 육지 전략 지역 %s" % (sorted(regions), land_sr))
            if regions:
                pix_area = np.bincount(id_map.ravel(), minlength=N + 1)
                areas_sr = {rid: int(sum(pix_area[p] for p in sr_info[rid])) for rid in land_sr}
                biggest = max(land_sr, key=lambda rid: (areas_sr[rid], -rid)) if land_sr else None
                if regions and biggest is not None and regions[0] != biggest:
                    chk.err("20", "theater 첫 지역 %d가 가장 큰 육지 전략 지역 %d가 아님" % (regions[0], biggest))
            map_loc = (mod / "localisation" / "korean" / "replace" / "tu_map_l_korean.yml")
            map_loc_text = map_loc.read_bytes().decode("utf-8-sig") if map_loc.is_file() else ""
            if not re.search(r"^\s*TU_theater_terra:\d*\s+\"", map_loc_text, re.M):
                chk.err("20", "TU_theater_terra 로컬라이제이션 키 없음 (tu_map_l_korean.yml)")

    # 21. descriptor: 두 곳 모두 replace_path 목록 포함 (수정1 D)
    desc_paths = [mod / "descriptor.mod",
                  Path.home() / "Documents" / "Paradox Interactive" / "Hearts of Iron IV" / "mod" / "terra_universalis.mod"]
    for dp in desc_paths:
        if not dp.is_file():
            chk.err("21", "descriptor 없음: %s" % dp)
            continue
        text = dp.read_bytes().decode("utf-8-sig", errors="replace")
        for rp in REQUIRED_REPLACE:
            if 'replace_path="%s"' % rp not in text:
                chk.err("21", "%s: replace_path=\"%s\" 없음" % (dp.name, rp))

    # 22. 이름 있는 주 / 정박지 (A.8, 연결 규약 1·2): 1-프로빈스 주, 소유국, 효과·트리거 10개분, on_startup 호출
    named_path = MAPGEN_DIR / "out" / "named_states.json"
    if not named_path.is_file():
        chk.err("22", "tools/mapgen/out/named_states.json 없음 (mapgen 실행 필요)")
    else:
        ninfo = json.loads(named_path.read_text(encoding="ascii"))
        named_rows = [(e["name"], e["state"], e["owner"]) for e in ninfo["named"]]
        anchor_rows = []
        for a in ninfo["anchors"]:
            anchor_rows.append(("anchor_%s" % a["key"], a["state"], a["host"]))
        for nm, sid, owner in named_rows + anchor_rows:
            info = state_info.get(sid)
            if info is None:
                chk.err("22", "이름 있는 주 %s: 주 %s 파일 없음" % (nm, sid))
                continue
            if len(info["provs"]) != 1:
                chk.err("22", "이름 있는 주 %s(주 %s)는 1-프로빈스 주여야 함 (%d개)" % (nm, sid, len(info["provs"])))
            if info["owner"] != owner:
                chk.err("22", "이름 있는 주 %s(주 %s): 소유국 %s (기대 %s)" % (nm, sid, info["owner"], owner))
        eff_path = mod / "common" / "scripted_effects" / "tu_generated_states.txt"
        trg_path = mod / "common" / "scripted_triggers" / "tu_generated_states.txt"
        eff_text = eff_path.read_text(encoding="ascii") if eff_path.is_file() else ""
        trg_text = trg_path.read_text(encoding="ascii") if trg_path.is_file() else ""
        if (mod / "common" / "on_actions" / "tu_generated_on_actions.txt").is_file():
            chk.err("22", "tu_generated_on_actions.txt가 남아 있음 (더 이상 생성하지 않음)")
        n_anchor = len(anchor_rows)
        n_rel = len(re.findall(r"^TU_anchor_\w+_relocate_rho = \{", eff_text, re.M))
        n_av = len(re.findall(r"^TU_anchor_\w+_available = \{", trg_text, re.M))
        if n_rel != n_anchor:
            chk.err("22", "정박지 relocate 효과 %d개 (정박지 %d개와 같아야 함)" % (n_rel, n_anchor))
        # 순서 검사: 목표 정박지 -> RHO 이양 과 set_capital 이 다른 정박지 반환(transfer_state_to)보다 먼저
        anchor_sid = {a["key"]: a["state"] for a in ninfo["anchors"]}
        for m in re.finditer(r"^TU_anchor_(\w+)_relocate_rho = \{\n(.*?)^\}", eff_text, re.M | re.S):
            key, body = m.group(1), m.group(2).splitlines()
            sid_key = anchor_sid.get(key)
            idx_rho = next((i for i, ln in enumerate(body)
                            if sid_key is not None
                            and ln.strip().startswith("%d = { transfer_state_to = RHO }" % sid_key)), None)
            idx_cap = next((i for i, ln in enumerate(body) if "set_capital = " in ln), None)
            idx_other = next((i for i, ln in enumerate(body)
                              if "transfer_state_to = " in ln and "transfer_state_to = RHO" not in ln), None)
            if idx_rho is None:
                chk.err("22", "relocate %s: 목표 정박지를 RHO에 넘기는 줄이 없음" % key)
            elif idx_cap is None:
                chk.err("22", "relocate %s: set_capital 줄이 없음" % key)
            elif idx_other is not None and not (idx_rho < idx_cap < idx_other):
                chk.err("22", "relocate %s: RHO 이양/set_capital 이 다른 정박지 반환보다 뒤에 있음 (RHO 0개 주 위험)" % key)
        if n_av != n_anchor:
            chk.err("22", "정박지 available 트리거 %d개 (정박지 %d개와 같아야 함)" % (n_av, n_anchor))
        for nm, sid, _o in named_rows + anchor_rows:
            if "# %s = %d\n" % (nm, sid) not in eff_text:
                chk.err("22", "tu_generated_states.txt 머리글에 %s = %d 없음" % (nm, sid))
        for a in ninfo["anchors"]:
            for al in a.get("aliases", []):
                if "# %s = %d (alias of" % (al, a["state"]) not in eff_text:
                    chk.err("22", "tu_generated_states.txt 머리글에 별칭 %s 없음" % al)
        if re.search(r"event_target:TU_STATE_|TU_init_named_states", eff_text + trg_text):
            chk.err("22", "생성 스크립트에 event_target:TU_STATE_* 또는 TU_init_named_states가 남아 있음")

    # 24. 고정 id (A.3): terra/pinned_ids.json의 이름 있는 주·정박지의 주 id와 대표 프로빈스 id가 빌드 결과와 같아야 한다
    pinned_path = MAPGEN_DIR / "terra" / "pinned_ids.json"
    if not pinned_path.is_file():
        chk.err("24", "terra/pinned_ids.json 없음")
    elif named_path.is_file():
        pinned = json.loads(pinned_path.read_text(encoding="ascii"))["pinned"]
        ninfo_now = json.loads(named_path.read_text(encoding="ascii"))
        built_ids = {e["name"]: (e["state"], e["province"]) for e in ninfo_now["named"]}
        built_ids.update({"anchor_%s" % a["key"]: (a["state"], a["province"]) for a in ninfo_now["anchors"]})
        for nm, (sid, pid) in sorted(pinned.items()):
            if nm not in built_ids:
                chk.err("24", "고정 주 %s가 빌드 결과에 없음" % nm)
            elif built_ids[nm] != (sid, pid):
                chk.err("24", "고정 주 %s: 빌드 주 %d / 프로빈스 %d, 고정값 주 %d / 프로빈스 %d" % (
                    nm, built_ids[nm][0], built_ids[nm][1], sid, pid))

    # 23. 국가별 통행 가능 주 1개 이상, 깃발 3종 크기, 미리보기 1/4 크기
    passable_owner = {info["owner"] for info in state_info.values() if not info["impassable"]}
    for tag in sorted(countries):
        if tag not in passable_owner and tag not in dynamic_tags:
            chk.err("23", "%s: 통행 가능한 주가 하나도 없음" % tag)
    flag_sizes = {"gfx/flags/%s.tga": (82, 52), "gfx/flags/medium/%s.tga": (41, 26), "gfx/flags/small/%s.tga": (10, 7)}
    for tag in sorted(countries):
        for pattern, (fw, fh) in flag_sizes.items():
            fp = mod / (pattern % tag)
            if not fp.is_file():
                chk.err("23", "깃발 없음: %s" % (pattern % tag))
                continue
            hdr = fp.read_bytes()[:18]
            gw = int.from_bytes(hdr[12:14], "little")
            gh = int.from_bytes(hdr[14:16], "little")
            if (gw, gh) != (fw, fh) or hdr[2] != 2 or hdr[16] != 32:
                chk.err("23", "깃발 %s: %dx%d 32bit TGA가 아님 (기대 %dx%d)" % (pattern % tag, gw, gh, fw, fh))
    for pv in ("preview_provinces.png", "preview_heightmap.png", "preview_terrain.png", "preview_owner.png"):
        pp = MAPGEN_DIR / "out" / pv
        if not pp.is_file():
            chk.err("23", "미리보기 없음: %s" % pv)
        else:
            pim = Image.open(pp)
            if pim.size != (W // 4, H // 4):
                chk.err("23", "미리보기 %s 크기 %s (기대 %s)" % (pv, pim.size, (W // 4, H // 4)))

    # 13. 테두리: 가장자리 8px 안쪽에 육지/호수 픽셀이 없어야 한다
    nonsea_lut = np.zeros(N + 1, bool)
    for p in range(1, N + 1):
        nonsea_lut[p] = ptype[p] != "sea"
    edge = np.ones((H, W), bool)
    edge[8:-8, 8:-8] = False
    edge_bad = int((nonsea_lut[id_map] & edge).sum())
    if edge_bad:
        chk.err("13", "가장자리 8px 안쪽 육지/호수 픽셀 %d개" % edge_bad)

    # 12. tu_lint
    lint_root = mod
    proc = subprocess.run([sys.executable, "-I", str(LINT), str(lint_root)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    last = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "(no output)"
    m = re.search(r"TU_LINT errors=(\d+)", last)
    if not m or int(m.group(1)) != 0:
        chk.err("12", "tu_lint: %s" % last)

    # 요약
    n_land = sum(1 for p in range(1, N + 1) if ptype[p] == "land")
    n_lake = sum(1 for p in range(1, N + 1) if ptype[p] == "lake")
    n_sea = sum(1 for p in range(1, N + 1) if ptype[p] == "sea")
    print("INFO map %dx%d provinces land=%d lake=%d sea=%d" % (W, H, n_land, n_lake, n_sea))
    print("INFO states=%d strategic_regions=%d railway_lines=%d supply_nodes=%d" % (
        S, len(sr_info), rail_count, sn_count))
    print("INFO tu_lint: %s" % last)
    if chk.errors:
        print("MAPCHECK FAIL (%d errors)" % len(chk.errors))
        for e in chk.errors:
            print("  " + e)
        return 1
    print("MAPCHECK ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
