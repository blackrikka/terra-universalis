#!/usr/bin/env python3
"""떨어진 영토 잇기 (사양서 20). 지도 생성(mapgen) 뒤에 돌린다.

사용법:  python -I tools/mapgen/fix_exclaves.py [--dry]

문제: 나라 땅이 통행 불가 황야(WLD, impassable)나 바다로 갈라져 있으면, 내전이 나거나 전쟁 중에 그쪽 부대가 움직일 수 없다.

1. 회랑 (육지): 본토(수도가 있는 덩어리)와 떨어진 덩어리마다, 황야 프로빈스만 지나 본토에 닿는 가장 짧은 프로빈스 길을 찾는다.
   길 위의 황야 프로빈스를 떨어진 덩어리 쪽 주(길이 시작하는 주)에 붙인다 → 통행 가능해지고 땅이 이어진다.
   다른 나라 땅은 지나지 않는다. 황야 주가 프로빈스를 모두 잃으면 그 주를 통째로 그 나라에 넘긴다.
2. 해협 (섬): 육지 길이 없으면 바다 프로빈스 하나를 사이에 둔 가장 가까운 두 육지 프로빈스를 map/adjacencies.csv 의
   sea 연결(해협)로 잇는다. 바다 한 칸으로 닿는 곳이 없으면 가장 가까운 해안 프로빈스끼리 육상 연결(Type 비움)로 잇는다.
3. map/buildings.txt: 옮긴 프로빈스에 있던 건물 위치의 주 번호를 고치고, 주 단위 건물 위치를 잃은 황야 주에는
   남은 프로빈스의 요새 위치로 다시 만든다 (validate_map 9번 규칙).
4. 염국 내전 분할(TU_YAN 내전 효과의 주 목록)도 덩어리별로 이어지는지 보고만 한다.
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
MOD = REPO / "terra_universalis"
STATE_TYPES = {"arms_factory", "industrial_complex", "air_base", "anti_air_building", "fuel_silo", "nuclear_reactor_spawn",
               "radar_station", "rocket_site_spawn", "stronghold_network", "synthetic_refinery"}


def load_defs():
    ptype, colour = {}, {}
    with open(MOD / "map" / "definition.csv", encoding="utf-8-sig") as fh:
        for row in csv.reader(fh, delimiter=";"):
            if len(row) < 5 or not row[0].isdigit() or row[0] == "0":
                continue
            pid = int(row[0])
            colour[(int(row[1]) << 16) | (int(row[2]) << 8) | int(row[3])] = pid
            ptype[pid] = row[4]
    return ptype, colour


def adjacency(colour):
    img = np.asarray(Image.open(MOD / "map" / "provinces.bmp").convert("RGB")).astype(np.int64)
    key = (img[:, :, 0] << 16) | (img[:, :, 1] << 8) | img[:, :, 2]
    adj = defaultdict(set)
    for a, b in ((key[:, :-1], key[:, 1:]), (key[:-1, :], key[1:, :])):
        diff = a != b
        for x, y in set(zip(a[diff].tolist(), b[diff].tolist())):
            pa, pb = colour.get(x), colour.get(y)
            if pa and pb:
                adj[pa].add(pb)
                adj[pb].add(pa)
    return adj


class States:
    def __init__(self):
        self.files, self.text, self.owner, self.provs, self.imp = {}, {}, {}, {}, {}
        for f in (MOD / "history" / "states").glob("*.txt"):
            t = f.read_text(encoding="utf-8-sig")
            sid = int(re.search(r"\bid\s*=\s*(\d+)", t).group(1))
            self.files[sid], self.text[sid] = f, t
            o = re.search(r"\bowner\s*=\s*(\w+)", t)
            self.owner[sid] = o.group(1) if o else None
            self.provs[sid] = [int(x) for x in re.search(r"provinces\s*=\s*\{([^}]*)\}", t).group(1).split()]
            self.imp[sid] = re.search(r"impassable\s*=\s*yes", t) is not None
        self.p2s = {p: s for s, ps in self.provs.items() for p in ps}
        self.changed = set()

    def passable(self, p):
        s = self.p2s.get(p)
        return s is not None and not self.imp[s]

    def move(self, p, dst):
        src = self.p2s[p]
        self.provs[src].remove(p)
        self.provs[dst].append(p)
        self.p2s[p] = dst
        self.changed.update({src, dst})

    def give_state(self, sid, tag):
        t = self.text[sid]
        t = re.sub(r"\n\timpassable = yes", "", t)
        t = re.sub(r"\bowner\s*=\s*\w+", "owner = %s" % tag, t)
        t = re.sub(r"add_core_of\s*=\s*\w+", "add_core_of = %s" % tag, t)
        t = t.replace("state_category = wasteland", "state_category = pastoral")
        t = re.sub(r"infrastructure = 0", "infrastructure = 1", t)
        self.text[sid] = t
        self.owner[sid] = tag
        self.imp[sid] = False
        self.changed.add(sid)

    def write(self):
        for sid in self.changed:
            ps = self.provs[sid]
            lines = "\n".join("\t\t" + " ".join(str(x) for x in ps[i:i + 20]) for i in range(0, len(ps), 20))
            t = re.sub(r"provinces\s*=\s*\{[^}]*\}", "provinces={\n%s\n\t}" % lines, self.text[sid])
            self.files[sid].write_text(t, encoding="utf-8")


_CEN = {}


def centroids():
    if not _CEN:
        _, colour = load_defs()
        img = np.asarray(Image.open(MOD / "map" / "provinces.bmp").convert("RGB")).astype(np.int64)
        key = ((img[:, :, 0] << 16) | (img[:, :, 1] << 8) | img[:, :, 2]).ravel()
        H, W = img.shape[:2]
        rows, cols = np.divmod(np.arange(key.size), W)
        uniq, inv = np.unique(key, return_inverse=True)
        cnt = np.bincount(inv)
        sr = np.bincount(inv, rows)
        sc = np.bincount(inv, cols)
        for i, k in enumerate(uniq.tolist()):
            pid = colour.get(k)
            if pid:
                _CEN[pid] = (sr[i] / cnt[i], sc[i] / cnt[i])
    return _CEN


def capitals():
    caps = {}
    for f in (MOD / "history" / "countries").glob("*.txt"):
        m = re.search(r"^capital\s*=\s*(\d+)", f.read_text(encoding="utf-8-sig"), re.M)
        if m:
            caps[f.name[:3]] = int(m.group(1))
    return caps


def components(nodes, nb):
    nodes, seen, out = set(nodes), set(), []
    for n in sorted(nodes):
        if n in seen:
            continue
        comp, stack = {n}, [n]
        seen.add(n)
        while stack:
            x = stack.pop()
            for y in nb(x):
                if y in nodes and y not in seen:
                    seen.add(y)
                    comp.add(y)
                    stack.append(y)
        out.append(comp)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    ptype, colour = load_defs()
    adj = adjacency(colour)
    S = States()
    named = json.loads((REPO / "tools" / "mapgen" / "out" / "named_states.json").read_text(encoding="ascii"))
    fixed = {e["state"] for e in named["named"] if e.get("category") == "enclave"} | {e["state"] for e in named["anchors"]}
    caps = capitals()
    straits = []          # (a, b, sea)
    extra = defaultdict(set)

    def land_nb(p):
        return [q for q in adj[p] if ptype.get(q) == "land"] + list(extra[p])

    def own_provs(tag):
        return [p for s, ps in S.provs.items() if S.owner[s] == tag and not S.imp[s] for p in ps]

    report = []
    for tag in sorted(caps):
        if tag == "WLD" or caps[tag] not in S.provs:
            continue
        skipped = set()
        for _ in range(50):
            provs = own_provs(tag)
            comps = components(provs, land_nb)
            if len(comps) <= 1:
                break
            cap_p = set(S.provs[caps[tag]])
            main_c = next((c for c in comps if c & cap_p), comps[0])
            rest = [c for c in comps if c is not main_c and not (c & skipped)]
            if not rest:
                break
            ex = min(rest, key=len)
            # BFS: 떨어진 덩어리 -> 황야 프로빈스만 -> 본토
            prev, frontier, end = {p: None for p in ex}, list(ex), None
            while frontier and end is None:
                nxt = []
                for p in frontier:
                    for q in land_nb(p):
                        if q in prev:
                            continue
                        s = S.p2s.get(q)
                        if s is None:
                            continue
                        if q in main_c:
                            prev[q] = p
                            end = q
                            break
                        if S.owner[s] == "WLD" and S.imp[s]:
                            prev[q] = p
                            nxt.append(q)
                    if end is not None:
                        break
                frontier = nxt
            if end is not None:
                path, q = [], prev[end]
                while prev[q] is not None:
                    path.append(q)
                    q = prev[q]
                start_state = S.p2s[q]
                if start_state in fixed:
                    # 1-프로빈스여야 하는 주(이름 있는 주·정박지)에는 붙이지 않는다: 회랑 첫 칸에 닿는 다른 자기 주를 쓴다
                    alts = [S.p2s[y] for y in land_nb(path[-1]) if S.p2s.get(y) and S.owner[S.p2s[y]] == tag
                            and not S.imp[S.p2s[y]] and S.p2s[y] not in fixed]
                    alts += [S.p2s[y] for x in path for y in land_nb(x) if S.p2s.get(y) and S.owner[S.p2s[y]] == tag
                             and not S.imp[S.p2s[y]] and S.p2s[y] not in fixed]
                    if alts:
                        start_state = alts[0]
                for p in path:
                    src = S.p2s[p]
                    S.move(p, start_state)
                    if not S.provs[src]:
                        S.provs[src].append(p)          # 빈 주는 안 됨: 마지막 프로빈스는 되돌리고 주를 통째로 넘긴다
                        S.provs[start_state].remove(p)
                        S.p2s[p] = src
                        S.give_state(src, tag)
                report.append("%s: 덩어리 %d프로빈스 -> 회랑 %d프로빈스 (주 %d에 붙임)" % (tag, len(ex), len(path), start_state))
                continue
            # 해협: 바다 하나를 사이에 둔 땅 (본토 우선, 없으면 이 나라 다른 덩어리, 없으면 아무 통행 가능 땅)
            best = None
            targets = [main_c, set(provs) - ex, {p for p in S.p2s if S.passable(p)} - ex]
            for tgt in targets:
                for p in sorted(ex):
                    for sea in adj[p]:
                        if ptype.get(sea) != "sea":
                            continue
                        for q in adj[sea]:
                            if q in tgt and ptype.get(q) == "land":
                                best = (p, q, sea)
                                break
                        if best:
                            break
                    if best:
                        break
                if best:
                    break
            if best is None:
                # 바다 한 칸으로 닿지 않음 (대부분 호수 안의 섬). 검증되지 않은 연결 형식(Type 비움)은 크래시 위험이 있어 쓰지 않는다.
                report.append("%s: 섬 덩어리 %d프로빈스 %s - 잇지 못함 (호수 섬 또는 바다 두 칸 이상)" % (tag, len(ex), sorted(ex)[:3]))
                skipped |= ex
                continue
            p, q, sea = best
            straits.append(best)
            extra[p].add(q)
            extra[q].add(p)
            report.append("%s: 섬 덩어리 %d프로빈스 -> 연결 %d-%d (바다 %d, -1 = 육상 다리, 상대 %s)" % (
                tag, len(ex), p, q, sea, S.owner[S.p2s[q]]))

    # 회랑으로 조각난 황야 주: 작은 조각은 닿아 있는 다른 황야 주에 붙인다 (모두 통행 불가라 놀이에는 영향 없음)
    for sid in sorted(S.provs):
        if S.owner[sid] != "WLD" or not S.imp[sid]:
            continue
        parts = sorted(components(S.provs[sid], land_nb), key=len, reverse=True)
        for part in parts[1:]:
            nbs = [S.p2s[y] for x in part for y in land_nb(x)
                   if S.p2s.get(y) not in (None, sid) and S.owner[S.p2s[y]] == "WLD" and S.imp[S.p2s[y]]]
            if nbs:
                dst = Counter(nbs).most_common(1)[0][0]
                for x in part:
                    S.move(x, dst)
                report.append("WLD: 주 %d 조각 %d프로빈스 -> 주 %d" % (sid, len(part), dst))

    print("\n".join(report) or "떨어진 영토 없음")
    if a.dry:
        return 0
    S.write()

    # adjacencies.csv
    path = MOD / "map" / "adjacencies.csv"
    head = "From;To;Type;Through;start_x;start_y;stop_x;stop_y;adjacency_rule_name;Comment"
    old = [l for l in path.read_text(encoding="ascii").splitlines()[1:] if l.strip() and not l.startswith("-1;")
           and not l.endswith(";TU_strait")]
    rows = old + [("%d;%d;sea;%d;-1;-1;-1;-1;;TU_strait" % s) if s[2] > 0 else ("%d;%d;;-1;-1;-1;-1;-1;;TU_strait" % s[:2])
                  for s in straits]
    path.write_text("\n".join([head] + rows + ["-1;-1;;-1;-1;-1;-1;-1;-1;"]) + "\n", encoding="ascii")

    # buildings.txt
    bpath = MOD / "map" / "buildings.txt"
    img = np.asarray(Image.open(MOD / "map" / "provinces.bmp").convert("RGB")).astype(np.int64)
    H = img.shape[0]

    def prov_at(x, z):
        col, row = int(round(x)), H - 1 - int(round(z))
        if 0 <= row < H and 0 <= col < img.shape[1]:
            r, g, b = img[row, col]
            return colour.get((int(r) << 16) | (int(g) << 8) | int(b))
        return None

    lines = [l.split(";") for l in bpath.read_text(encoding="ascii").splitlines() if l.strip()]
    keep, lost = [], defaultdict(Counter)
    for f in lines:
        sid, typ = int(f[0]), f[1]
        p = prov_at(float(f[2]), float(f[4]))
        ns = S.p2s.get(p, sid)
        if ns == sid:
            keep.append(f)
        elif typ in STATE_TYPES or typ == "dockyard":
            lost[sid][typ] += 1             # 새 주에는 이미 같은 종류가 있다 -> 버리고, 옛 주에 다시 만든다
        else:
            f[0] = str(ns)
            keep.append(f)
    by_state_bunker = {}
    by_state_coast = {}
    for f in keep:
        if f[1] == "bunker":
            by_state_bunker.setdefault(int(f[0]), f)
        if f[1] == "coastal_bunker":
            by_state_coast.setdefault(int(f[0]), f)
    for sid, types in lost.items():
        for typ, n in sorted(types.items()):
            for _ in range(n):
                if typ == "dockyard":
                    src = by_state_coast.get(sid)
                    if src:
                        keep.append([str(sid), "dockyard"] + src[2:])
                    continue
                src = by_state_bunker[sid]
                keep.append([str(sid), typ] + src[2:6] + ["0"])
    # 해안이 된 주에 조선소 위치가 없으면 해안 요새 위치로 만든다 (위치만: 건설은 '심해의 위협'으로 막힘)
    has_dock = {int(f[0]) for f in keep if f[1] == "dockyard"}
    for sid, src in by_state_coast.items():
        if sid not in has_dock:
            keep.append([str(sid), "dockyard"] + src[2:])
    # 주를 잃은 해안 위치: 해안이 아니게 된 주의 조선소 위치는 지운다
    coast_states = {int(f[0]) for f in keep if f[1] == "coastal_bunker"}
    keep = [f for f in keep if not (f[1] == "dockyard" and int(f[0]) not in coast_states)]
    keep.sort(key=lambda f: int(f[0]))
    bpath.write_text("\n".join(";".join(f) for f in keep) + "\n", encoding="ascii")
    print("states changed: %d, straits: %d" % (len(S.changed), len(straits)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
