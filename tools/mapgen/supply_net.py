#!/usr/bin/env python3
"""보급망: 보급 거점, 철도, 인프라 (사양서 78).

주를 프로빈스 한 칸으로 나눈 뒤 (사양서 49) 보급 거점은 84개, 철도는 163구간 그대로라 보급이 쉽게 끊겼다.
나라마다 (같은 나라의 이어진 땅 덩어리마다):
    거점   모든 주가 거점에서 COVER 칸 안에 들도록 거점을 더한다 (이미 있는 거점은 그대로 센다). 후보는 인구가 큰 주 먼저.
    철도   거점끼리 가장 가까운 것부터 짧은 길로 이어 한 덩어리로 묶는다.  수도 거점에 닿는 간선은 3단계, 나머지는 2단계.
    인프라 거점이 된 주의 인프라를 INFRA 단계 이상으로 (수도 주는 +1).
원래 파일(지도 생성기가 만든 것)은 그대로 두고, 이 도구가 더한 줄만 tools/mapgen/out/supply_net.json 에 적어 두었다가
다시 돌릴 때 지우고 다시 만든다 (다시 돌려도 같다). 철도는 map/railways.txt, 거점은 map/supply_nodes.txt.

tiers.py 가 끝에 부른다. 혼자 돌려도 된다:  python -I tools/mapgen/supply_net.py
"""

import json
import re
import sys
from collections import deque
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MOD = REPO / "terra_universalis"
OUT = REPO / "tools" / "mapgen" / "out" / "supply_net.json"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tiers import load_states, capitals  # noqa: E402
import border_forts  # noqa: E402

COVER = 2
INFRA = 3
TRUNK, BRANCH = 3, 2


def read_lines(name):
    return [l for l in (MOD / "map" / name).read_text(encoding="ascii").splitlines() if l.strip()]


def bfs(graph, starts, limit=None):
    dist = {s: 0 for s in starts}
    q = deque(starts)
    while q:
        u = q.popleft()
        if limit is not None and dist[u] >= limit:
            continue
        for v in graph.get(u, ()):
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def path(graph, a, targets):
    """a 에서 targets 중 가장 가까운 곳까지의 짧은 길 (프로빈스 목록)."""
    prev = {a: None}
    q = deque([a])
    while q:
        u = q.popleft()
        if u in targets:
            out = []
            while u is not None:
                out.append(u)
                u = prev[u]
            return out[::-1]
        for v in sorted(graph.get(u, ())):
            if v not in prev:
                prev[v] = u
                q.append(v)
    return None


def main():
    st = load_states()
    caps = capitals()
    nb = border_forts.neighbours()
    prov = {d["prov"]: (s, d) for s, d in st.items() if not d["impassable"] and d["owner"]}
    graph = {p: {q for q in nb.get(p, ()) if q in prov and prov[q][1]["owner"] == prov[p][1]["owner"]} for p in prov}
    mp = {p: prov[p][1]["mp"] for p in prov}
    cap_prov = {t: st[s]["prov"] for t, s in caps.items() if s in st}

    # 이전에 더한 줄을 지우고 원래 상태로
    prev = json.loads(OUT.read_text()) if OUT.is_file() else {"nodes": [], "rails": []}
    nodes = [l for l in read_lines("supply_nodes.txt") if l not in set(prev["nodes"])]
    rails = [l for l in read_lines("railways.txt") if l not in set(prev["rails"])]
    base_nodes = {int(l.split()[1]) for l in nodes}

    # 덩어리 (같은 나라의 이어진 땅)
    seen, comps = set(), []
    for p in sorted(prov):
        if p in seen:
            continue
        c = set(bfs(graph, [p]))
        seen |= c
        comps.append(c)

    new_nodes, new_rails, hubs_all = [], [], set(base_nodes)
    for comp in comps:
        owner = prov[next(iter(comp))][1]["owner"]
        hubs = {p for p in comp if p in base_nodes}
        cap = cap_prov.get(owner)
        if cap in comp:
            hubs.add(cap)
        covered = set(bfs(graph, list(hubs), COVER)) if hubs else set()
        while len(covered) < len(comp):
            best = max((p for p in comp if p not in hubs),
                       key=lambda p: (len(set(bfs(graph, [p], COVER)) - covered), mp[p], -p))
            hubs.add(best)
            covered |= set(bfs(graph, [best], COVER))
        added = {p for p in hubs if p not in base_nodes}
        new_nodes += sorted(added)
        hubs_all |= hubs
        # 거점을 한 덩어리로 철도 연결: 수도(없으면 인구가 가장 큰 거점)에서 시작해 가장 가까운 거점부터
        root = cap if cap in hubs else max(hubs, key=lambda p: (mp[p], -p))
        linked, todo = {root}, set(hubs) - {root}
        while todo:
            d = bfs(graph, list(linked))
            target = min(todo, key=lambda p: (d.get(p, 10 ** 9), p))
            if target not in d:
                break
            line = path(graph, target, linked)
            todo.discard(target)
            linked |= set(line)
            if len(line) >= 2:
                level = TRUNK if (cap in line) else BRANCH
                new_rails.append("%d %d %s" % (level, len(line), " ".join(str(x) for x in line)))
            linked.add(target)

    node_lines = ["1 %d" % p for p in new_nodes]
    (MOD / "map" / "supply_nodes.txt").write_text("\n".join(nodes + node_lines) + "\n", encoding="ascii")
    (MOD / "map" / "railways.txt").write_text("\n".join(rails + new_rails) + "\n", encoding="ascii")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"nodes": node_lines, "rails": new_rails}), encoding="utf-8")

    # 인프라: 거점 주
    raised = 0
    for p in hubs_all:
        s, d = prov[p]
        f = d["file"]
        t = f.read_text(encoding="utf-8-sig")
        want = INFRA + (1 if cap_prov.get(d["owner"]) == p else 0)
        m = re.search(r"(infrastructure\s*=\s*)(\d+)", t)
        if m and int(m.group(2)) < want:
            f.write_text(t[:m.start(2)] + str(want) + t[m.end(2):], encoding="utf-8")
            raised += 1
    print("SUPPLY_NET components=%d new_nodes=%d (total %d) new_rails=%d infra_raised=%d" % (
        len(comps), len(new_nodes), len(nodes) + len(new_nodes), len(new_rails), raised))
    return 0


if __name__ == "__main__":
    sys.exit(main())
