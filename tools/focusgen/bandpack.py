#!/usr/bin/env python3
"""중점 트리 단 접기 (autolayout.py 가 마지막에 부른다).

autolayout 의 기본 배치는 갈래를 모두 한 줄로 늘어놓아 트리가 아주 넓고 얕아진다 (폭 60~170칸, 깊이 8~20줄).
여기서는 갈래 묶음을 여러 단(band)으로 접어 쌓아 화면 비율에 가깝게 만든다.

묶음(unit)   뿌리(중점이 하나뿐인 맨 위 중점)를 뺀 나머지 그래프에서 prerequisite·mutually_exclusive 로 이어진 덩어리.
             묶음 하나는 autolayout 으로 따로 배치하고 (내부 모양 그대로), 사각형 하나로 다룬다.
순서         묶음은 파일에 처음 나온 순서 (갈래를 쓴 순서) 를 지킨다. 단은 그 순서를 연속으로 나눈다.
단 수        폭 96px, 줄 130px 로 볼 때 가로:세로가 ASPECT 에 가장 가까운 단 수 (1~MAX_BANDS). 1단이면 손대지 않는다.
단 사이      스카이라인: 아래 단 묶음은 그 열들에서 위 단 중점이 끝나는 줄 아래로 빈 줄 하나를 두고 붙는다.
             아래 단의 갈래 머리는 뿌리에서 선이 내려오므로 위 단 중점이 없는 열(통로)에만 둔다.
             뿌리도 위 단 중점이 없는 열에 둔다 (선이 부모 쪽에서 꺾이든 자식 쪽에서 꺾이든 상자를 지나지 않게).
묶음 간격    같은 단의 사각형 사이 2칸 이상.
"""

import math

ASPECT = 1.8
MAX_BANDS = 4
UNIT_GAP = 2


def components(n, parents, adj, skip):
    uf = list(range(n))

    def find(x):
        while uf[x] != x:
            uf[x] = uf[uf[x]]
            x = uf[x]
        return x

    for i in range(n):
        if i in skip:
            continue
        for j in list(parents[i]) + list(adj[i]):
            if j in skip:
                continue
            a, b = find(i), find(j)
            if a != b:
                uf[max(a, b)] = min(a, b)
    groups = {}
    for i in range(n):
        if i not in skip:
            groups.setdefault(find(i), []).append(i)
    return sorted(groups.values(), key=min)


def split_contiguous(widths, k):
    """widths 를 순서대로 k 덩어리로 나눠 가장 넓은 덩어리 폭을 최소로. 반환: 덩어리 경계 목록."""
    n = len(widths)
    k = min(k, n)

    def span(a, b):
        return sum(widths[a:b]) + UNIT_GAP * (b - a - 1)

    best = {}

    def go(i, kk):
        if (i, kk) in best:
            return best[(i, kk)]
        if kk == 1:
            r = (span(i, n), [n])
        else:
            r = None
            for j in range(i + 1, n - kk + 2):
                sub = go(j, kk - 1)
                cand = (max(span(i, j), sub[0]), [j] + sub[1])
                if r is None or cand[0] < r[0]:
                    r = cand
        best[(i, kk)] = r
        return r

    return go(0, k)


def pack(units, start, corridors):
    """사각형 묶음을 왼쪽부터 놓는다. corridors 열은 사각형 안에 들지 않게 한다. 반환: 묶음별 왼쪽 x."""
    xs = []
    cur = start
    for u in units:
        p = cur
        while True:
            bad = [c for c in corridors if p <= c <= p + u["w"] - 1]
            if not bad:
                break
            p = max(bad) + 1
        xs.append(p)
        cur = p + u["w"] + UNIT_GAP - 1 + 1
    return xs


def band_layout(n, parents, adj, Y, X, sub_layout, center=None):
    """X, Y: autolayout 결과. sub_layout(nodes) -> {node: (x, y)} (그 노드들만 따로 배치, y 는 0 부터).
    반환: 새 (X, Y) 또는 None (손대지 않음)."""
    roots = [i for i in range(n) if not parents[i]]
    single = len(roots) == 1
    skip = {roots[0]} if single else set()
    groups = components(n, parents, adj, skip)
    if len(groups) < 2:
        return None

    units = []
    for g in groups:
        pos = sub_layout(g)
        minx = min(x for x, _ in pos.values())
        rel = {i: (x - minx, y) for i, (x, y) in pos.items()}
        w = max(x for x, _ in rel.values()) + 1
        d = max(y for _, y in rel.values()) + 1
        heads = [i for i in g if single and roots[0] in parents[i]]
        units.append(dict(nodes=g, rel=rel, w=w, d=d, heads=heads))

    W1 = max(X) - min(X) + 1
    H1 = max(Y) + 1
    widths = [u["w"] for u in units]

    def ratio(w, h):
        return (w * 96.0) / (h * 130.0)

    best_k, best_score, best_split = 1, abs(math.log(ratio(W1, H1) / ASPECT)), None
    for k in range(2, min(MAX_BANDS, len(units)) + 1):
        width, cuts = split_contiguous(widths, k)
        bounds = [0] + cuts
        h = (1 if single else 0) + sum(max(units[t]["d"] for t in range(bounds[b], bounds[b + 1]))
                                       for b in range(k)) + (k - 1)
        score = abs(math.log(ratio(width, h) / ASPECT))
        if score < best_score - 1e-9:
            best_k, best_score, best_split = k, score, bounds
    if best_k == 1:
        return None

    bands = [units[best_split[b]:best_split[b + 1]] for b in range(best_k)]
    # 위 단부터 놓는다. 아래 단 묶음은 그 열들에서 위 단 중점이 끝나는 줄 + 빈 줄 하나 아래에 붙인다 (스카이라인).
    # 아래 단의 갈래 머리는 위에 중점이 없는 열(통로)에만 둔다 (뿌리에서 내려오는 선 자리).
    NX = [0] * n
    NY = [0] * n
    row0 = 1 if single else 0
    sky = {}
    head_rows = []

    def put(u, lx, top):
        for i, (rx, ry) in u["rel"].items():
            NX[i] = lx + rx
            NY[i] = top + ry
            sky[NX[i]] = max(sky.get(NX[i], -1), NY[i])

    for u, lx in zip(bands[0], pack(bands[0], 0, ())):
        put(u, lx, row0)
    span_lo, span_hi = min(sky), max(sky)

    def simulate(b, start):
        out = []
        cur = start
        bottom = 0
        for u in bands[b]:
            p = cur
            while any(p + u["rel"][h][0] in sky for h in u["heads"]):
                p += 1
            cols = [sky[c] for c in range(p - 1, p + u["w"] + 1) if c in sky]
            top = (max(cols) + 2) if cols else row0
            out.append((p, top))
            bottom = max(bottom, top + u["d"])
            cur = p + u["w"] + UNIT_GAP
        return out, bottom

    for b in range(1, best_k):
        best = None
        for start in range(span_lo - 20, span_lo + 21):
            out, bottom = simulate(b, start)
            hi = out[-1][0] + bands[b][-1]["w"] - 1
            lo, top = min(span_lo, out[0][0]), max(span_hi, hi)
            key = (top - lo, bottom, abs((out[0][0] + hi) - (span_lo + span_hi)))
            if best is None or key < best[0]:
                best = (key, out)
        for u, (lx, top) in zip(bands[b], best[1]):
            put(u, lx, top)
            if u["heads"]:
                head_rows.append(top)
        span_lo, span_hi = min(sky), max(sky)
    if single:
        r = roots[0]
        top = [NX[i] for u in bands[0] for i in u["nodes"]]
        mid = (min(top) + max(top)) / 2.0
        # 뿌리 열: 아래 단 갈래 머리 줄보다 위에 중점이 없는 열 중 첫 단 가운데에 가장 가까운 열
        limit = max(head_rows) if head_rows else 0
        upper = {NX[i] for i in range(n) if i != r and NY[i] < limit}
        c = int(round(mid))
        for d in range(0, 400):
            if c - d not in upper:
                c = c - d
                break
            if c + d not in upper:
                c = c + d
                break
        NX[r] = c
        NY[r] = 0
        # 뿌리 줄의 다른 중점과 겹치지 않는지 (뿌리 하나뿐이면 없음)
    if center is not None:
        ref = NX[center]
    elif single:
        ref = NX[roots[0]]
    else:
        ref = (min(NX) + max(NX)) // 2
    return [x - ref for x in NX], NY
