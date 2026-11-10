#!/usr/bin/env python3
"""국가 중점 트리 자동 배치 (표준 라이브러리만 사용, Python 3.10).

사용법:
    python -I tools/focusgen/autolayout.py <파일> ...          # 파일을 고쳐 쓴다
    python -I tools/focusgen/autolayout.py --check <파일> ...  # 쓰지 않고 검사 (배치가 바뀌면 exit 1)

파일 하나 = focus_tree 하나. 문자열과 # 주석을 지운 뒤 중괄호 구조로 focus 블록을 찾는다.

배치 규칙:
    부모      중점의 prerequisite 블록 안 모든 focus id (mutually_exclusive 는 부모가 아님)
    뿌리      부모가 없는 중점
    y         뿌리 0, 나머지 1 + max(부모 y)  -> 비는 줄이 없다
              대립(mutually_exclusive) 중점은 같은 줄: 짝의 얕은 쪽을 깊은 쪽 줄로 내린다 (사양서 72)
    주 부모   부모가 하나면 그 부모. 여럿이면 (1) 부모들의 주 부모가 모두 같은 형제 줄이면 묶음으로 본다.
              (2) 아니면 y 가 가장 큰 것 (같으면 파일에서 먼저 나온 것). (2) 는 배치 뒤
              다른 부모들의 가운데에 가장 가까운 부모로 바꿀 수 있다 (검사가 통과할 때만).
    묶음      같은 줄의 형제 부모들을 한 묶음으로 보고, 그 부모들만 가진 중점은 묶음 아래 덧붙이 줄에 둔다.
              묶음 안 부모는 mutually_exclusive 가 붙도록 x 간격 2 로 나란히 놓고, 덧붙이 중점은
              묶음 가운데 (부모 span 의 가운데) 에 둔다. 덧붙이가 부모의 하위 트리와 같은 줄에서 겹치면
              (가운데에 둘 수 없으면) 덧붙이를 부모 뒤에 붙인다.
    형제 순서 원래 절대 x 순 (relative_position_id 체인을 풀어서 구함). 그다음
              mutually_exclusive 로 묶인 덩어리가 붙도록 재배열 (뿌리끼리도 같은 규칙, 묶음도 한 덩어리).
              덩어리 안은 깊이 우선 순서.
    x         contour 정리 배치 (Reingold-Tilford 식). 하위 트리마다 줄별 왼쪽/오른쪽 끝 (contour) 을 가진다.
              형제는 앞 형제들의 contour 와 같은 줄에서 간격 2 이상이 되도록 가장 가깝게 붙인다.
              서로 같은 줄을 쓰지 않는 형제는 겹쳐도 된다. 부모 x = 첫째 자식 x 와 끝 자식 x 의 가운데 (내림).
              뿌리들은 원래 x 순으로 contour 정리 배치한다 (뿌리 줄은 모두 0 이라 간격 2 가 붙는다).
    주 자식   자식이 둘 이상인 중점 (묶음도 자식 항목 하나) 에서 하위 줄 수를 센다. 한 항목이 다른 모든
              항목보다 2줄 이상 깊으면 그 항목이 주 자식이다. 주 자식은 부모 바로 아래 (같은 x) 에 두고,
              나머지 덩어리는 원래 x 순서대로 주 자식의 왼쪽과 오른쪽에 나눠 붙인다. 부모 x = 주 자식 x (가운데 대신).
              mutually_exclusive 짝은 주 자식 바로 옆에 붙는다. 그럴 수 없으면 (짝이 셋 이상이거나
              같은 덩어리) 주 자식을 쓰지 않고 위의 가운데 규칙을 쓴다. 묶음의 덧붙이 줄에는 적용하지 않는다.
              주 자식의 왼쪽/오른쪽 덩어리는 앞 덩어리들과 contour 간격 2 를 지키며 가장 가깝게 붙는다.
    기준      initial_show_position 의 focus (없으면 가운데 뿌리) 의 x 를 0 으로 맞춘다.
    쓰기      모든 focus 에 절대 x, y 를 쓰고 relative_position_id 줄을 지운다.
              나머지 글자 (주석, 들여쓰기, 줄바꿈, BOM) 는 그대로 둔다.
    검사      같은 y 에서 이웃한 중점의 |dx| 는 2 이상 (아니면 오류).
              고친 결과를 다시 읽어 id, 부모, mutually_exclusive 가 같은지, 두 번째 실행이 같은지 확인한다.
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # <repo>/tools/focusgen
REPO = HERE.parents[1]                            # <repo>

TREE_RE = re.compile(r"\bfocus_tree\s*=\s*\{")
HEADER_RE = re.compile(r"([A-Za-z_]\w*)\s*=\s*$")
ID_RE = re.compile(r"\bid\s*=\s*([A-Za-z_]\w*)")
X_RE = re.compile(r"\bx\s*=\s*(-?\d+)")
Y_RE = re.compile(r"\by\s*=\s*(-?\d+)")
REL_RE = re.compile(r"\brelative_position_id\s*=\s*([A-Za-z_]\w*)")
FOCUS_REF_RE = re.compile(r"\bfocus\s*=\s*([A-Za-z_]\w*)")
GAP = 2
MIN_DX = 2
MAX_ROUNDS = 20


class TuError(Exception):
    """파싱 또는 배치 오류. line 은 0 이면 파일 전체 오류."""

    def __init__(self, line, msg):
        super().__init__(msg)
        self.line = line
        self.msg = msg


def show(path):
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def mask_code(text):
    """문자열과 # 주석 내용을 공백으로 지운다. 글자 수와 줄 위치는 그대로 둔다."""
    out = []
    in_str = False
    in_comment = False
    for ch in text:
        if in_comment:
            if ch == "\n":
                in_comment = False
                out.append(ch)
            else:
                out.append(" ")
        elif in_str:
            if ch == "\n" or ch == '"':
                in_str = False
                out.append(ch)
            else:
                out.append(" ")
        elif ch == "#":
            in_comment = True
            out.append(" ")
        elif ch == '"':
            in_str = True
            out.append(ch)
        else:
            out.append(ch)
    return "".join(out)


def match_braces(code):
    """여는 중괄호 위치 -> 짝이 되는 닫는 중괄호 위치."""
    stack = []
    pairs = {}
    for i, ch in enumerate(code):
        if ch == "{":
            stack.append(i)
        elif ch == "}":
            if not stack:
                raise TuError(code.count("\n", 0, i) + 1, "여는 중괄호 없이 닫는 중괄호가 있습니다")
            pairs[stack.pop()] = i
    if stack:
        raise TuError(code.count("\n", 0, stack[-1]) + 1, "닫히지 않은 여는 중괄호가 있습니다")
    return pairs


def child_blocks(code, pairs, lo, hi):
    """(lo, hi) 사이에 바로 들어 있는 블록 [(머리 이름, 여는 위치, 닫는 위치)]. 하위 블록 안은 건너뛴다."""
    out = []
    i = lo + 1
    while i < hi:
        if code[i] == "{":
            close = pairs[i]
            m = HEADER_RE.search(code, max(lo + 1, i - 80), i)
            out.append((m.group(1) if m else "", i, close))
            i = close + 1
        else:
            i += 1
    return out


def top_text(code, lo, hi, blocks):
    """(lo, hi) 안의 최상위 글자만 남긴다. 하위 블록(중괄호 포함)은 공백으로 지운다. 위치는 그대로."""
    chars = list(code[lo + 1:hi])
    for _, o, c in blocks:
        for k in range(o - lo - 1, c - lo):
            chars[k] = " "
    return "".join(chars)


def parse(text):
    """파일 하나를 읽는다. 반환: focus_tree 이름, initial_show_position 의 focus, focus 목록."""
    code = mask_code(text)
    pairs = match_braces(code)
    trees = list(TREE_RE.finditer(code))
    if len(trees) != 1:
        raise TuError(1, f"focus_tree 블록이 {len(trees)}개입니다 (1개여야 함)")
    t_open = trees[0].end() - 1
    t_close = pairs[t_open]
    t_blocks = child_blocks(code, pairs, t_open, t_close)
    t_id = ID_RE.search(top_text(code, t_open, t_close, t_blocks))
    init = None
    for name, o, c in t_blocks:
        if name == "initial_show_position":
            m = FOCUS_REF_RE.search(code, o, c)
            if m:
                init = m.group(1)

    focuses = []
    for name, o, c in t_blocks:
        if name != "focus":
            continue
        line = code.count("\n", 0, o) + 1
        blocks = child_blocks(code, pairs, o, c)
        top = top_text(code, o, c, blocks)
        ids = ID_RE.findall(top)
        if len(ids) != 1:
            raise TuError(line, "focus 블록의 id 는 1개여야 합니다")
        fid = ids[0]

        def only(rx, label):
            found = list(rx.finditer(top))
            if len(found) > 1:
                raise TuError(line, f"{label} 줄이 여러 개입니다: {fid}")
            return found[0] if found else None

        xm = only(X_RE, "x")
        ym = only(Y_RE, "y")
        rm = only(REL_RE, "relative_position_id")
        if xm is None or ym is None:
            raise TuError(line, f"x, y 줄이 모두 필요합니다: {fid}")
        parents = []
        mutex = []
        for bname, bo, bc in blocks:
            if bname == "prerequisite":
                parents.extend(FOCUS_REF_RE.findall(code[bo + 1:bc]))
            elif bname == "mutually_exclusive":
                mutex.extend(FOCUS_REF_RE.findall(code[bo + 1:bc]))
        focuses.append({
            "id": fid,
            "line": line,
            "x": int(xm.group(1)),
            "y": int(ym.group(1)),
            "x_span": (o + 1 + xm.start(1), o + 1 + xm.end(1)),
            "y_span": (o + 1 + ym.start(1), o + 1 + ym.end(1)),
            "rel": rm.group(1) if rm else None,
            "rel_span": (o + 1 + rm.start(), o + 1 + rm.end()) if rm else None,
            "parents": parents,
            "mutex": mutex,
            "gated": any(bname == "allow_branch" for bname, _, _ in blocks),
        })
    return {"tree": t_id.group(1) if t_id else "?", "init": init, "focuses": focuses}


def resolve_abs(fs, index):
    """relative_position_id 체인을 풀어 원래 절대 (x, y) 를 구한다."""
    res = [None] * len(fs)

    def get(i, stack):
        if res[i] is not None:
            return res[i]
        f = fs[i]
        if f["rel"] is None:
            res[i] = (f["x"], f["y"])
            return res[i]
        if f["rel"] not in index or i in stack:
            raise TuError(f["line"], f"relative_position_id 체인이 끊겼거나 순환함: {f['id']}")
        bx, by = get(index[f["rel"]], stack + (i,))
        res[i] = (bx + f["x"], by + f["y"])
        return res[i]

    for i in range(len(fs)):
        get(i, ())
    return res


def order_items(items, key, neighbors):
    """항목을 key 순으로 정렬하고, neighbors 로 이어진 덩어리가 붙도록 깊이 우선 순서로 재배열한다."""
    items = sorted(items, key=key)
    iset = set(items)
    seen = set()
    result = []

    def dfs(v):
        seen.add(v)
        result.append(v)
        for w in sorted((w for w in neighbors(v) if w in iset), key=key):
            if w not in seen:
                dfs(w)

    for start in items:
        if start not in seen:
            dfs(start)
    return result


def row_clash(pairs):
    """(y, x) 쌍에서 같은 y 에 |dx| < MIN_DX 인 이웃이 있으면 (y, dx), 없으면 None."""
    rows = {}
    for y, x in pairs:
        rows.setdefault(y, []).append(x)
    for yy, xs in rows.items():
        xs.sort()
        for a, b in zip(xs, xs[1:]):
            if b - a < MIN_DX:
                return yy, b - a
    return None


def mid_cost(X, ps, p):
    """부모 p 의 x 가 나머지 부모들의 가운데에서 떨어진 거리 (두 배 단위, 정수)."""
    others = [X[q] for q in ps if q != p]
    return abs(2 * X[p] - (min(others) + max(others)))


def build_structure(parents, topo, Y, overrides):
    """소속 구조를 만든다.
    cont     중점이 들어 있는 줄. None 은 뿌리 줄, 정수 j 는 중점 j 의 자식 줄, ("g", r) 은 묶음 r 의 덧붙이 줄.
    members  묶음 r -> 묶인 부모들 (같은 줄의 형제)
    fallback 부모가 둘 이상인데 묶이지 않은 중점 (주 부모를 고르는 대상)
    overrides 에 든 중점은 그 부모를 주 부모로 쓴다.
    """
    n = len(parents)
    cont = [None] * n
    join = [False] * n
    fallback = []
    for i in topo:
        ps = parents[i]
        if len(ps) == 0:
            continue
        if len(ps) == 1:
            cont[i] = ps[0]
            continue
        if i in overrides:
            cont[i] = overrides[i]
            fallback.append(i)
        elif all(not join[p] for p in ps) and len({cont[p] for p in ps}) == 1:
            join[i] = True
        else:
            cont[i] = max(ps, key=lambda j: (Y[j], -j))
            fallback.append(i)

    uf = list(range(n))

    def find(x):
        while uf[x] != x:
            uf[x] = uf[uf[x]]
            x = uf[x]
        return x

    for i in range(n):
        if join[i]:
            r0 = find(parents[i][0])
            for p in parents[i][1:]:
                r1 = find(p)
                if r1 != r0:
                    uf[r1] = r0
    members = {}
    for i in range(n):
        if join[i]:
            for p in parents[i]:
                members.setdefault(find(p), set()).add(p)
    for i in range(n):
        if join[i]:
            cont[i] = ("g", find(parents[i][0]))
    return cont, members, fallback


def contour_gap(a, b):
    """contour b 를 contour a 의 오른쪽에 붙일 때 같은 줄에서 필요한 최소 이동량.
    공유하는 줄이 없으면 None."""
    best = None
    for r, (lo, _) in b.items():
        if r in a:
            v = a[r][1] + GAP - lo
            if best is None or v > best:
                best = v
    return best


def contour_clear(a, b, t):
    """contour b 를 t 만큼 옮겼을 때 같은 줄마다 a 와 간격 2 이상 떨어져 있는지 (양쪽 어느 쪽이든)."""
    for r, (lo, hi) in b.items():
        if r in a:
            alo, ahi = a[r]
            if not (lo + t >= ahi + GAP or hi + t <= alo - GAP):
                return False
    return True


def contour_add(a, b, t):
    """contour b 를 t 만큼 옮겨 contour a 에 합친다 (a 를 고친다)."""
    for r, (lo, hi) in b.items():
        lo += t
        hi += t
        if r in a:
            a[r] = (min(a[r][0], lo), max(a[r][1], hi))
        else:
            a[r] = (lo, hi)


def unit_shift(pos, cont, t):
    """단위의 x 좌표 (pos) 와 contour 를 t 만큼 옮긴 새 사본을 돌려준다."""
    return ({k: v - t for k, v in pos.items()},
            {r: (lo - t, hi - t) for r, (lo, hi) in cont.items()})


class Solver:
    """구조 하나의 x 를 contour 로 배치한다. 메모는 이 구조에만 쓴다.
    단위 = (pos, cont). pos 는 단위 안 중점의 x, cont 는 줄마다 (최소 x, 최대 x).
    단위의 기준 x (주 자식 x 또는 묶음 가운데) 는 항상 0 으로 맞춘다."""

    def __init__(self, n, keyx, Y, adj, cont, members, center):
        self.n = n
        self.keyx = keyx
        self.Y = Y
        self.adj = adj
        self.center = center
        self.members = {r: sorted(ms) for r, ms in members.items()}
        self.gof = {}
        for r, ms in self.members.items():
            for m in ms:
                self.gof[m] = r
        self.kids = {}
        for i in range(n):
            self.kids.setdefault(cont[i], []).append(i)
        self.ents_memo = {}
        self.mem_memo = {}
        self.unit_memo = {}
        self.centred_memo = {}
        self.dep_memo = {}
        self.dom_of = {}

    def members_of(self, e):
        return [e[1]] if e[0] == "n" else self.members[e[1]]

    def ekey(self, e):
        if e[0] == "n":
            return (self.keyx[e[1]], e[1])
        return min((self.keyx[m], m) for m in self.members[e[1]])

    def mem_ordered(self, r):
        if r not in self.mem_memo:
            self.mem_memo[r] = order_items(self.members[r],
                                           lambda v: (self.keyx[v], v),
                                           lambda v: self.adj[v])
        return self.mem_memo[r]

    def entries(self, c):
        """줄 c 에 들어 있는 항목 (중점 또는 묶음) 을 순서대로 돌려준다."""
        if c in self.ents_memo:
            return self.ents_memo[c]
        items = []
        seen = set()
        for x in self.kids.get(c, []):
            if x in self.gof:
                e = ("g", self.gof[x])
                if e not in seen:
                    seen.add(e)
                    items.append(e)
            else:
                items.append(("n", x))
        owner = {}
        for e in items:
            for m in self.members_of(e):
                owner[m] = e

        def nb(e):
            return {owner[w] for m in self.members_of(e) for w in self.adj[m]
                    if w in owner and owner[w] != e}

        res = order_items(items, self.ekey, nb)
        if isinstance(c, int) and len(res) >= 2:
            res, dom = self.dominant(res, nb)
            if dom is not None:
                self.dom_of[c] = dom
        self.ents_memo[c] = res
        return res

    def depth(self, e):
        """항목 아래로 줄이 몇 개 더 있는지 (잎은 0). 묶음은 멤버 줄과 덧붙이 줄 중 깊은 쪽."""
        if e not in self.dep_memo:
            if e[0] == "n":
                ents = self.entries(e[1])
                d = 1 + max(self.depth(f) for f in ents) if ents else 0
            else:
                d = max(self.depth(("n", m)) for m in self.members[e[1]])
                js = self.kids.get(("g", e[1]), [])
                if js:
                    d = max(d, 1 + max(self.depth(("n", j)) for j in js))
            self.dep_memo[e] = d
        return self.dep_memo[e]

    def dominant(self, res, nb):
        """주 자식을 찾아 자식 순서를 정한다. 반환: (새 순서, 주 자식 항목 또는 None).
        주 자식을 뺀 덩어리 (mutually_exclusive 로 이어진 항목들) 는 원래 x 순서로 주 자식의 왼쪽이나
        오른쪽에 둔다. 번갈아 붙이면 다시 배치할 때 순서가 뒤집혀 되풀이 배치가 진동하므로 쓰지 않는다."""
        dep = {e: self.depth(e) for e in res}
        dom = None
        for e in res:
            if dep[e] >= max(dep[f] for f in res if f != e) + 2:
                dom = e
                break
        if dom is None:
            return res, None

        # dom 을 뺀 덩어리. 덩어리 안은 키 순서.
        comp_of = {}
        comps = []
        for f in res:
            if f == dom or f in comp_of:
                continue
            comp_of[f] = len(comps)
            comp = [f]
            stack = [f]
            while stack:
                v = stack.pop()
                for w in nb(v):
                    if w != dom and w not in comp_of:
                        comp_of[w] = len(comps)
                        comp.append(w)
                        stack.append(w)
            comps.append(sorted(comp, key=self.ekey))

        # 덩어리의 쪽: 가장 작은 항목이 주 자식보다 앞이면 왼쪽
        dk = self.ekey(dom)
        left_side = [self.ekey(c[0]) < dk for c in comps]

        # dom 의 mutually_exclusive 짝 덩어리는 dom 바로 옆 (쪽의 가까운 끝) 에 와야 한다.
        partners = sorted(nb(dom), key=self.ekey)
        pcs = [comp_of[p] for p in partners]
        if len(partners) > 2 or len(set(pcs)) != len(pcs):
            return res, None
        if len(partners) == 2 and left_side[pcs[0]] == left_side[pcs[1]]:
            return res, None

        def inner(k):
            comp = comps[k]
            if k not in pcs:
                return comp
            p = partners[pcs.index(k)]
            rest = [e for e in comp if e != p]
            return rest + [p] if left_side[k] else [p] + rest

        by_key = sorted(range(len(comps)), key=lambda k: self.ekey(comps[k][0]))
        # 왼쪽: 먼 것부터 (짝 덩어리는 맨 끝), 오른쪽: 가까운 것부터 (짝 덩어리는 맨 앞)
        left = [k for k in by_key if left_side[k] and k not in pcs] + [k for k in pcs if left_side[k]]
        right = [k for k in pcs if not left_side[k]] + [k for k in by_key if not left_side[k] and k not in pcs]
        order = []
        for k in left:
            order.extend(inner(k))
        order.append(dom)
        for k in right:
            order.extend(inner(k))
        return order, dom

    def pack(self, units):
        """단위들을 앞에서부터 한 줄로 붙인다. 각 단위는 앞 단위들의 contour 와 같은 줄에서
        간격 2 이상이 되도록 가장 가깝게 놓는다. 기준 x 는 뒤 단위가 앞 단위보다 오른쪽이 되도록 한다.
        반환: (pos, cont, 각 단위의 기준 x 목록)."""
        pos = {}
        acc = {}
        anchors = []
        for upos, ucont in units:
            d = contour_gap(acc, ucont) if acc else None
            if anchors:
                d = anchors[-1] + 1 if d is None else max(d, anchors[-1] + 1)
            if d is None:
                d = 0
            for k, v in upos.items():
                pos[k] = v + d
            contour_add(acc, ucont, d)
            anchors.append(d)
        return pos, acc, anchors

    def unit(self, i):
        """중점 i 의 하위 트리 단위 (기준 = 주 자식 x, 없으면 첫째 자식과 끝 자식의 가운데)."""
        if i not in self.unit_memo:
            ents = self.entries(i)
            if not ents:
                res = ({i: 0}, {self.Y[i]: (0, 0)})
            else:
                pos, cont, anchors = self.pack([self.unit_entry(e) for e in ents])
                dom = self.dom_of.get(i)
                if dom is not None:
                    ax = anchors[ents.index(dom)]
                else:
                    ax = (anchors[0] + anchors[-1]) // 2
                pos[i] = ax
                cont[self.Y[i]] = (ax, ax)
                res = unit_shift(pos, cont, ax)
            self.unit_memo[i] = res
        return self.unit_memo[i]

    def unit_entry(self, e):
        return self.unit(e[1]) if e[0] == "n" else self.group(e[1])

    def group(self, r):
        """묶음 r 의 단위 (기준 = 멤버 span 의 가운데). 멤버는 한 줄로 붙이고, 덧붙이 줄은
        멤버 가운데에 맞춘다. 같은 줄에서 겹치면 멤버 뒤에 붙인다."""
        if ("g", r) not in self.unit_memo:
            mpos, mcont, manch = self.pack([self.unit(m) for m in self.mem_ordered(r)])
            c = (manch[0] + manch[-1]) // 2
            jpos, jcont, janch = self.pack([self.unit_entry(e) for e in self.entries(("g", r))])
            jc = (janch[0] + janch[-1]) // 2
            t = c - jc
            centred = contour_clear(mcont, jcont, t)
            if not centred:
                t = contour_gap(mcont, jcont) or 0
            pos = dict(mpos)
            for k, v in jpos.items():
                pos[k] = v + t
            cont = dict(mcont)
            contour_add(cont, jcont, t)
            self.centred_memo[r] = centred
            self.unit_memo[("g", r)] = unit_shift(pos, cont, c)
        return self.unit_memo[("g", r)]

    def place_all(self):
        roots = self.entries(None)
        pos, _, anchors = self.pack([self.unit_entry(e) for e in roots])
        if len(pos) != self.n:
            raise TuError(1, "내부 오류: 배치되지 않은 중점이 있습니다")
        if self.center is not None:
            shift = pos[self.center]
        else:
            shift = anchors[len(roots) // 2]
        return [pos[i] - shift for i in range(self.n)]

    def seq_count(self):
        return sum(1 for r in self.members if not self.centred_memo.get(r, True))

    def mutex_stats(self, adj):
        """같은 줄의 mutually_exclusive 쌍 수와 그중 줄에서 떨어진 쌍 수."""
        total = 0
        nonadj = 0
        for c in self.kids:
            flat = []
            for e in self.entries(c):
                flat.extend(self.mem_ordered(e[1]) if e[0] == "g" else [e[1]])
            pos = {m: k for k, m in enumerate(flat)}
            for i in flat:
                for j in adj[i]:
                    if i < j and j in pos:
                        total += 1
                        if abs(pos[i] - pos[j]) != 1:
                            nonadj += 1
        return total, nonadj


def layout(tree):
    """배치를 계산한다. 반환: 통계 dict (xy 는 파일 순서의 (x, y) 목록)."""
    fs = tree["focuses"]
    n = len(fs)
    if n == 0:
        raise TuError(1, "focus 가 없습니다")
    index = {}
    for i, f in enumerate(fs):
        if f["id"] in index:
            raise TuError(f["line"], f"focus id 중복: {f['id']}")
        index[f["id"]] = i
    orig = resolve_abs(fs, index)

    parents = []
    for i, f in enumerate(fs):
        ps = []
        for pid in f["parents"]:
            if pid not in index:
                raise TuError(f["line"], f"prerequisite 가 가리키는 중점이 없습니다: {pid} (대상: {f['id']})")
            j = index[pid]
            if j == i:
                raise TuError(f["line"], f"prerequisite 가 자기 자신을 가리킴: {f['id']}")
            if j not in ps:
                ps.append(j)
        parents.append(ps)

    adj = [set() for _ in range(n)]
    for i, f in enumerate(fs):
        for mid in f["mutex"]:
            if mid not in index:
                raise TuError(f["line"], f"mutually_exclusive 가 가리키는 중점이 없습니다: {mid} (대상: {f['id']})")
            j = index[mid]
            if j != i:
                adj[i].add(j)
                adj[j].add(i)

    # y: 뿌리 0, 나머지 1 + max(부모 y). Kahn 순서로 계산 (순환이면 오류).
    children = [[] for _ in range(n)]
    indeg = [len(ps) for ps in parents]
    for i, ps in enumerate(parents):
        for j in ps:
            children[j].append(i)
    queue = [i for i in range(n) if indeg[i] == 0]
    topo = []
    k = 0
    while k < len(queue):
        i = queue[k]
        k += 1
        topo.append(i)
        for c in children[i]:
            indeg[c] -= 1
            if indeg[c] == 0:
                queue.append(c)
    if len(topo) != n:
        bad = next(i for i in range(n) if indeg[i] > 0)
        raise TuError(fs[bad]["line"], f"prerequisite 순환: {fs[bad]['id']}")
    Y = [0] * n
    for i in topo:
        if parents[i]:
            Y[i] = 1 + max(Y[j] for j in parents[i])

    # 대립(mutually_exclusive) 중점은 같은 줄에 둔다 (사양서 72): 줄이 다르면 게임에서 대립 표시가 보이지 않는다.
    # 짝 가운데 얕은 쪽을 깊은 쪽 줄로 내리고 그 아래 중점을 다시 계산한다. 조상-자손 사이의 대립은 맞출 수 없어 건너뛴다.
    # 숨은 갈래(allow_branch 로 가려진 중점과 그 아래)와 보이는 중점 사이의 대립은 맞추지 않는다:
    # 숨은 갈래가 길면 평소에 보이는 결말들이 그만큼 아래로 끌려 내려간다.
    anc = [0] * n
    hidden = [bool(f.get("gated")) for f in fs]
    for i in topo:
        for j in parents[i]:
            anc[i] |= anc[j] | (1 << j)
            hidden[i] = hidden[i] or hidden[j]
    floor = [0] * n
    base_y = list(Y)
    for _ in range(60):
        moved = False
        for i in range(n):
            for j in adj[i]:
                if Y[j] > Y[i] and hidden[i] == hidden[j] and not (anc[i] >> j) & 1 and not (anc[j] >> i) & 1:
                    floor[i] = max(floor[i], Y[j])
                    moved = True
        if not moved:
            break
        for i in topo:
            Y[i] = max(floor[i], 1 + max(Y[j] for j in parents[i]) if parents[i] else 0)
    else:
        Y = base_y          # 수렴하지 않으면 (대립이 서로 물려 있으면) 원래 줄을 쓴다

    # 가운데 기준: initial_show_position 의 focus, 없으면 가운데 뿌리
    if tree["init"] is not None:
        if tree["init"] not in index:
            raise TuError(1, f"initial_show_position 의 focus 가 없습니다: {tree['init']}")
        center = index[tree["init"]]
    else:
        center = None

    def refine(keyx):
        """keyx (형제 순서를 정하는 x) 로 배치한다. 다중 부모 중점의 주 부모를 고쳐 본 결과를 돌려준다."""

        def solve(overrides):
            cont, members, fallback = build_structure(parents, topo, Y, overrides)
            sv = Solver(n, keyx, Y, adj, cont, members, center)
            xs = sv.place_all()
            clash = row_clash(zip(Y, xs))
            if clash is not None:
                raise TuError(1, f"배치 검사 실패: y={clash[0]} 에서 dx={clash[1]}")
            return sv, xs, set(fallback)

        # 다중 부모 중점의 주 부모: 배치한 뒤 다른 부모들의 가운데에 가장 가까운 부모로 바꿔 본다.
        # 바꾼 결과가 검사에 걸리면 그 중점은 그대로 둔다.
        overrides = {}
        sv, X, fallback = solve(overrides)
        for i in sorted(fallback, key=lambda i: (Y[i], i)):
            if i not in fallback:
                continue
            cur = overrides.get(i, max(parents[i], key=lambda j: (Y[j], -j)))
            best = cur
            best_cost = mid_cost(X, parents[i], cur)
            for p in parents[i]:
                c = mid_cost(X, parents[i], p)
                if c < best_cost:
                    best, best_cost = p, c
            if best == cur:
                continue
            trial = dict(overrides)
            trial[i] = best
            try:
                sv2, X2, fallback2 = solve(trial)
            except TuError:
                continue
            overrides, sv, X, fallback = trial, sv2, X2, fallback2
        return sv, X, overrides

    # 형제 순서는 앞 배치의 x 로 정한다. 배치가 더 이상 바뀌지 않을 때까지 되풀이하므로
    # 고친 파일을 다시 돌려도 같은 결과가 나온다.
    keyx = [x for x, _ in orig]
    for _ in range(MAX_ROUNDS):
        sv, X, overrides = refine(keyx)
        if X == keyx:
            break
        keyx = X
    else:
        raise TuError(1, "배치가 수렴하지 않습니다")

    # 단 접기 (bandpack.py): 갈래 묶음을 여러 단으로 쌓아 폭을 줄인다
    if not tree.get("no_band"):
        import bandpack

        def sub_layout(nodes):
            keep = set(nodes)
            sub = []
            for i in nodes:
                f = fs[i]
                sub.append({"id": f["id"], "line": f["line"], "x": orig[i][0], "y": orig[i][1],
                            "x_span": None, "y_span": None, "rel": None, "rel_span": None,
                            "gated": f.get("gated", False),
                            "parents": [p for p in f["parents"] if index[p] in keep],
                            "mutex": [m for m in f["mutex"] if index[m] in keep]})
            st = layout({"tree": tree["tree"], "init": None, "focuses": sub, "no_band": True})
            return {i: xy for i, xy in zip(nodes, st["xy"])}

        banded = bandpack.band_layout(n, parents, adj, Y, X, sub_layout, center)
        if banded is not None:
            X, Y = banded
            clash = row_clash(zip(Y, X))
            if clash is not None:
                raise TuError(1, f"단 접기 검사 실패: y={clash[0]} 에서 dx={clash[1]}")

    # 통계
    before_x = [x for x, _ in orig]
    before_y = [y for _, y in orig]
    rows_before = max(before_y) - min(before_y) + 1
    pair_total, pair_nonadj = sv.mutex_stats(adj)
    return {
        "tree": tree["tree"],
        "n": n,
        "roots": sum(1 for ps in parents if not ps),
        "joins": len(sv.members),
        "seq": sv.seq_count(),
        "primary": len(overrides),
        "width": (max(before_x) - min(before_x), max(X) - min(X)),
        "depth": (rows_before, max(Y) + 1),
        "empty_removed": rows_before - len(set(before_y)),
        "mutex_pairs": pair_total,
        "mutex_nonadj": pair_nonadj,
        "xy": list(zip(X, Y)),
    }


def rewrite(text, tree, xy):
    """x, y 숫자만 바꾸고 relative_position_id 를 지운다. 나머지 글자는 그대로 둔다."""
    edits = []
    for f, (nx, ny) in zip(tree["focuses"], xy):
        edits.append((f["x_span"][0], f["x_span"][1], str(nx)))
        edits.append((f["y_span"][0], f["y_span"][1], str(ny)))
        if f["rel_span"] is not None:
            s, e = f["rel_span"]
            ls = text.rfind("\n", 0, s) + 1
            le = text.find("\n", e)
            le = len(text) if le < 0 else le + 1
            if text[ls:s].strip() == "" and text[e:le].strip() == "":
                edits.append((ls, le, ""))
            else:
                edits.append((s, e, ""))
    edits.sort()
    out = []
    pos = 0
    for s, e, rep in edits:
        if s < pos:
            raise TuError(1, "내부 오류: 고칠 자리가 겹칩니다")
        out.append(text[pos:s])
        out.append(rep)
        pos = e
    out.append(text[pos:])
    return "".join(out)


def verify(new, old_tree, xy):
    """고친 글을 다시 읽어 구조가 그대로이고 배치가 맞는지, 두 번째 실행이 같은지 확인한다."""
    t2 = parse(new)
    if len(t2["focuses"]) != len(old_tree["focuses"]):
        raise TuError(1, "검사 실패: focus 개수가 바뀌었습니다")
    for a, b, (x, y) in zip(old_tree["focuses"], t2["focuses"], xy):
        if a["id"] != b["id"] or sorted(a["parents"]) != sorted(b["parents"]) \
                or sorted(a["mutex"]) != sorted(b["mutex"]):
            raise TuError(b["line"], f"검사 실패: id, prerequisite, mutually_exclusive 가 바뀌었습니다: {b['id']}")
        if b["rel"] is not None or (b["x"], b["y"]) != (x, y):
            raise TuError(b["line"], f"검사 실패: 좌표가 맞지 않습니다: {b['id']}")
    if rewrite(new, t2, xy) != new:
        raise TuError(1, "검사 실패: 두 번 돌려도 같은 결과가 아닙니다")


def layout_path(path, write):
    """파일 하나를 배치한다. 반환: (바뀌었는지, 통계). write 가 True 이고 바뀌었으면 파일을 쓴다."""
    try:
        text = Path(path).read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TuError(0, f"UTF-8 로 디코딩되지 않습니다: {exc}")
    tree = parse(text)
    stats = layout(tree)
    new = rewrite(text, tree, stats["xy"])
    verify(new, tree, stats["xy"])
    changed = new != text
    if write and changed:
        Path(path).write_bytes(new.encode("utf-8"))
    return changed, stats


def describe(path, stats, changed, write):
    w0, w1 = stats["width"]
    d0, d1 = stats["depth"]
    print(f"AUTOLAYOUT {show(Path(path))} tree={stats['tree']} focuses={stats['n']} roots={stats['roots']}")
    print(f"  width {w0} -> {w1}   depth {d0} -> {d1}   empty rows removed {stats['empty_removed']}")
    print(f"  mutually_exclusive sibling pairs {stats['mutex_pairs']}, not adjacent {stats['mutex_nonadj']}")
    print(f"  joined parent groups {stats['joins']}, beside parents (no centre room) {stats['seq']}, primary parents changed {stats['primary']}")
    if not changed:
        state = "unchanged"
    elif write:
        state = "wrote"
    else:
        state = "NOT laid out (would change)"
    print(f"  {state}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="국가 중점 트리 자동 배치")
    parser.add_argument("files", nargs="+", help="focus 파일 (focus_tree 하나)")
    parser.add_argument("--check", action="store_true",
                        help="쓰지 않고 검사만 한다 (배치가 바뀌면 exit 1)")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    errors = 0
    for name in args.files:
        path = Path(name).resolve()
        write = not args.check
        try:
            changed, stats = layout_path(path, write)
        except TuError as exc:
            errors += 1
            print(f"ERROR {show(path)}:{exc.line} {exc.msg}")
            continue
        describe(path, stats, changed, write)
        if args.check and changed:
            errors += 1
    print(f"AUTOLAYOUT errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
