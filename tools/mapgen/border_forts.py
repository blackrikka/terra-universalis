#!/usr/bin/env python3
"""국경 요새 (사양서 68).

육각형 지도는 나라 사이가 한두 칸으로만 이어진 곳이 많고 강·산이 거의 없다. 한 칸 전선에서는 사단이 많은 쪽이
예비대를 계속 밀어 넣어 이기므로, 다른 나라와 맞닿은 국경 칸마다 시작 요새(bunker)를 둔다.

    대상: 통행 가능한 주(= 프로빈스 하나)가 다른 나라 소유의 통행 가능한 육지 프로빈스와 픽셀로 맞닿아 있으면
    효과: 주 history 의 buildings 에  <프로빈스> = { bunker = LEVEL }
    다시 돌려도 같다 (이전 국경 요새 줄을 지우고 다시 쓴다). tiers.py 가 끝에 부른다.

사용법 (python -I):  python -I tools/mapgen/border_forts.py
"""

import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
MOD = REPO / "terra_universalis"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tiers import load_states  # noqa: E402

LEVEL = 2
PROV_BLOCK = re.compile(r"\n[ \t]*\d+\s*=\s*\{\s*bunker\s*=\s*\d+\s*\}")


def neighbours():
    col = {}
    for line in (MOD / "map" / "definition.csv").read_text(encoding="utf-8-sig").splitlines():
        q = line.split(";")
        if len(q) > 4 and q[0].isdigit():
            col[(int(q[1]) << 16) | (int(q[2]) << 8) | int(q[3])] = int(q[0])
    a = np.asarray(Image.open(MOD / "map" / "provinces.bmp").convert("RGB")).astype(np.int64)
    c = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
    nb = {}
    for A, B in ((c[:, :-1], c[:, 1:]), (c[:-1, :], c[1:, :])):
        m = A != B
        for x, y in set(zip(A[m].tolist(), B[m].tolist())):
            px, py = col.get(x), col.get(y)
            if px and py:
                nb.setdefault(px, set()).add(py)
                nb.setdefault(py, set()).add(px)
    return nb


def main():
    st = load_states()
    owner_of = {d["prov"]: d["owner"] for d in st.values() if not d["impassable"]}
    nb = neighbours()
    n = 0
    for sid, d in st.items():
        f = d["file"]
        s = f.read_text(encoding="utf-8-sig")
        new = PROV_BLOCK.sub("", s)
        p = d["prov"]
        if not d["impassable"] and d["owner"] and any(
                owner_of.get(q) not in (None, d["owner"]) for q in nb.get(p, ())):
            m = re.search(r"\n([ \t]*)buildings\s*=\s*\{", new)
            if m:
                new = new[:m.end()] + "\n%s\t%d = { bunker = %d }" % (m.group(1), p, LEVEL) + new[m.end():]
                n += 1
        if new != s:
            f.write_text(new, encoding="utf-8")
    print("BORDER_FORTS provinces=%d level=%d" % (n, LEVEL))
    return 0


if __name__ == "__main__":
    sys.exit(main())
