#!/usr/bin/env python3
"""테라 전략 자원 6종 (사양서 57, 원본 설계문서 3.1).

내부 키는 바닐라 그대로 두고 (AI·장비 호환) 이름만 바꾼다:
    oil       -> 오리지늄   (전차·차량·드론 연료, 아츠 무기)     카즈델, 우르수스 북부, 림 빌리튼
    steel     -> 오리론     (보병 장구, 기차, 이동도시 뼈대)     모든 나라 + 빅토리아, 염국
    rubber    -> 폴리에스테르 (차량 타이어, 방호복)              사르곤, 볼리바르
    aluminium -> 아케톤     (드론, 전자·통신 장비)              컬럼비아, 사미
    tungsten  -> 망간       (중장갑, 대물 캐스터 장비)           우르수스, 카시미어
    chromium  -> 장치       (아츠 지팡이, 레이더, 특수 병기)      컬럼비아(라인 랩), 라테라노

이 도구가 하는 일
    history/states/*.txt 의 state 블록에 resources = { ... } 를 쓴다 (있던 블록은 지우고 다시 쓴다: 다시 돌려도 같다).
    나라마다 AMOUNTS 의 합계를 통행 가능한 주에 나눈다. 수도는 빼고, 주 하나에 MAX_PER_STATE 까지.
    NORTH 에 있는 (나라, 자원)은 북쪽(지도 y 가 작은) 주부터 채운다. 나머지는 태그로 정한 순서(매번 같다).
    tiers.py 가 끝에 부른다. 혼자 돌려도 된다:  python -I tools/mapgen/resources.py
"""

import hashlib
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
MOD = REPO / "terra_universalis"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tiers import TIERS, load_states, capitals  # noqa: E402

KEYS = ["oil", "steel", "rubber", "aluminium", "tungsten", "chromium"]
MAX_PER_STATE = 8
# 오리론(steel): 모든 나라가 군수 공장 x 2 를 기본으로 가진다 (보병 장구가 오리론을 쓴다)
STEEL_PER_MIL = 2
# 체급별 기본 (오리론 외 5종을 조금씩): 산지가 아니어도 시작 장비 한 줄은 돌릴 수 있게
BASE = {"S": 4, "A": 2, "B": 0, "C": 0}
# 산지 (원본 설계문서 3.1의 '주요 산지'): 기본에 더한다
AMOUNTS = {
    "KZD": {"oil": 40},
    "URS": {"oil": 48, "tungsten": 28},
    "RIM": {"oil": 16},
    "VIC": {"steel": 40},
    "YAN": {"steel": 40},
    "SAR": {"rubber": 32},
    "BOL": {"rubber": 20},
    "COL": {"aluminium": 36, "chromium": 16},
    "SAM": {"aluminium": 14},
    "KAZ": {"tungsten": 24},
    "LAT": {"chromium": 16},
}
NORTH = {("URS", "oil")}     # 우르수스 북부


def province_y():
    """프로빈스 id -> 지도에서의 평균 y (북쪽이 작다)."""
    color = {}
    for line in (MOD / "map" / "definition.csv").read_text(encoding="utf-8-sig").splitlines():
        p = line.split(";")
        if len(p) > 4 and p[0].isdigit():
            color[(int(p[1]) << 16) | (int(p[2]) << 8) | int(p[3])] = int(p[0])
    a = np.asarray(Image.open(MOD / "map" / "provinces.bmp").convert("RGB")).astype(np.int64)
    code = (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
    ys = np.repeat(np.arange(code.shape[0]), code.shape[1])
    flat = code.ravel()
    uniq, inv = np.unique(flat, return_inverse=True)
    sum_y = np.bincount(inv, weights=ys)
    cnt = np.bincount(inv)
    return {color[c]: sum_y[i] / cnt[i] for i, c in enumerate(uniq) if c in color}


def totals(tag, tier, mil):
    t = {k: BASE[tier] for k in KEYS}
    t["steel"] = mil * STEEL_PER_MIL
    for k, v in AMOUNTS.get(tag, {}).items():
        t[k] += v
    return {k: v for k, v in t.items() if v > 0}


def order(tag, key, states, st, py):
    if (tag, key) in NORTH:
        return sorted(states, key=lambda s: (py.get(st[s]["prov"], 0), s))
    return sorted(states, key=lambda s: hashlib.md5(("%s/%s/%d" % (tag, key, s)).encode()).hexdigest())


def write_resources(path, res):
    s = path.read_text(encoding="utf-8-sig")
    s = re.sub(r"\n[ \t]*resources\s*=\s*\{[^}]*\}[ \t]*", "", s)
    if res:
        body = "".join("\t\t%s = %d\n" % (k, res[k]) for k in KEYS if res.get(k))
        s, n = re.subn(r"(\n[ \t]*state_category\s*=\s*\w+)", r"\1\n\n\tresources = {\n%s\t}" % body.replace("\\", "\\\\"), s, count=1)
        assert n == 1, path
    path.write_text(s, encoding="utf-8")


def main():
    st = load_states()
    caps = capitals()
    py = province_y()
    per_state = {s: {} for s in st}
    world = {k: 0 for k in KEYS}
    for tag, (tier, _civ, mil, _divs, _pop) in TIERS.items():
        own = [s for s, d in st.items() if d["owner"] == tag and not d["impassable"] and s != caps.get(tag)]
        if not own:
            own = [caps[tag]] if tag in caps else []
        if not own:
            continue
        for key, amount in totals(tag, tier, mil).items():
            left = amount
            seq = order(tag, key, own, st, py)
            i = 0
            while left > 0:
                s = seq[i % len(seq)]
                room = MAX_PER_STATE - per_state[s].get(key, 0)
                if room > 0:
                    give = min(room, left, 4 if i >= len(seq) else MAX_PER_STATE)
                    per_state[s][key] = per_state[s].get(key, 0) + give
                    left -= give
                i += 1
                if i > len(seq) * 4:
                    print("resources: %s %s %d 못 넣음 (주 부족)" % (tag, key, left))
                    break
            world[key] += amount - max(left, 0)
    n = 0
    for s, res in per_state.items():
        write_resources(st[s]["file"], res)
        n += bool(res)
    print("RESOURCES states=%d %s" % (n, " ".join("%s=%d" % (k, world[k]) for k in KEYS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
