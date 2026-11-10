#!/usr/bin/env python3
"""영유권·국경 분쟁·국경 조약 중점 (사양서 76).

이름과 설명이 영토 요구인 중점이 실제로 영유권을 주도록 completion_reward 를 고친다. 지금까지는 대부분 "정치력 + 안정도"뿐이었고,
설명이 말하는 '영토 요구 디시전'의 전쟁 목표(take_claimed_state)도 영유권이 없어 쓸 수 없었다.

    claim     대상 나라 땅 가운데 우리와 맞닿은 주 (없으면 가장 가까운 주) 최대 N 곳에 영유권 (add_claim_by)
    dispute   claim + 대상과 관계 -25 + 긴장도 +2 (국경 분쟁·국경 압박)
    wargoal   claim + '영유권 주 획득' 전쟁 목표 (진격, 병합 계획)
    treaty    대상 땅에 대한 영유권을 버리고 서로 관계 +20 (국경 조약·회담)
주 번호는 지도(history/states + 프로빈스 이웃)에서 계산해 중점에 적는다. 지도를 다시 만들면 다시 돌린다.
대상 나라가 지금 없어도 (리유니온) 주 번호로 적으므로 나중에 생겨도 동작한다.

merge_focus.py 가 트리를 쓴 뒤 apply(path, tag) 를 부른다 (이미 있으면 건너뜀: 다시 돌려도 같다). 툴팁 문구는 loc 파일을 쓴다.
사용법 (python -I):  python -I tools/focusgen/claim_focuses.py        (툴팁 loc 만 쓴다)
"""

import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MOD = REPO / "terra_universalis"
sys.path.insert(0, str(REPO / "tools" / "mapgen"))
sys.path.insert(0, str(REPO / "tools"))

MAX_STATES = 6
LONDINIUM = 117          # 빅토리아 수도 주
REU_REGION = [24, 696, 21, 694, 695, 692, 635, 693]     # 체르노보그와 주변 (tu_crisis.1 의 핵심주)
NAMES = {"URS": ("우르수스", "Ursus"), "VIC": ("빅토리아", "Victoria"), "YAN": ("염국", "Yan"), "KZD": ("카즈델", "Kazdel"),
         "LEI": ("라이타니엔", "Leithanien"), "REU": ("리유니온", "Reunion"), "HIG": ("극동", "the Far East"),
         "COL": ("컬럼비아", "Columbia"), "BOL": ("볼리바르", "Bolivar"), "KAZ": ("카시미어", "Kazimierz")}

# 중점 id -> (종류, 대상 나라, 옵션)
TABLE = {
    # 카즈델
    "TU_KZD_vic_claims": ("claim", "VIC", "london"),
    "TU_KZD_ursus_claims": ("claim", "URS", None),
    "TU_KZD_lei_claims": ("claim", "LEI", None),
    "TU_KZD_reu_claims": ("claim", "REU", "reu"),
    "TU_KZD_vic_march_on_london": ("wargoal", "VIC", "london"),
    "TU_KZD_ursus_border_treaty": ("treaty", "URS", None),
    "TU_KZD_ursus_frontier_pact": ("treaty", "URS", None),
    # 빅토리아
    "TU_VIC_kzd_claim_londinium": ("claim", "KZD", "london"),
    "TU_VIC_lei_claim": ("claim", "LEI", None),
    "TU_VIC_col_claim": ("claim", "COL", None),
    "TU_VIC_bol_claim": ("claim", "BOL", None),
    "TU_VIC_urs_claim": ("claim", "URS", None),
    "TU_VIC_kaz_claim": ("claim", "KAZ", None),
    "TU_VIC_kaz_war_plans": ("wargoal", "KAZ", None),
    "TU_VIC_urs_border_summit": ("treaty", "URS", None),
    # 염국
    "TU_YAN_urs_claim_focus": ("claim", "URS", None),
    "TU_YAN_hig_claim_focus": ("claim", "HIG", None),
    "TU_YAN_urs_pressure": ("dispute", "URS", None),
    # 용문
    "TU_LGM_border_conflict_plan": ("dispute", "REU", "reu"),
    "TU_LGM_yan_border_talks": ("treaty", "YAN", None),
    # 로도스 아일랜드, 사미
    "TU_RHO_kazdel_prep": ("claim", "KZD", None),
    "TU_SAM_settler_treaty": ("treaty", "URS", None),
    # 리유니온: 우르수스 북·남·동부 (체르노보그 둘레를 방향으로 나눈다)
    "TU_REU_conquest_claim_north": ("claim", "URS", "north"),
    "TU_REU_conquest_claim_south": ("claim", "URS", "south"),
    "TU_REU_conquest_claim_east": ("claim", "URS", "east"),
}

_GEO = {}


def geo():
    if _GEO:
        return _GEO
    import tiers
    import border_forts
    st = tiers.load_states()
    g = tiers.province_geo()
    nb = border_forts.neighbours()
    by_prov = {d["prov"]: s for s, d in st.items()}
    adj = {}
    for p, ns in nb.items():
        if p in by_prov:
            for q in ns:
                if q in by_prov and by_prov[p] != by_prov[q]:
                    adj.setdefault(by_prov[p], set()).add(by_prov[q])
    cap = tiers.capitals()
    _GEO.update(st=st, g=g, adj=adj, cap=cap)
    return _GEO


def center(s):
    G = geo()
    _, x, y = G["g"][G["st"][s]["prov"]]
    return x, y


def dist(a, b):
    (ax, ay), (bx, by) = center(a), center(b)
    return math.hypot(ax - bx, ay - by)


def states_of(tag):
    G = geo()
    return [s for s, d in G["st"].items() if d["owner"] == tag and not d["impassable"]]


def pick(src, tgt, opt):
    """대상 나라 주 가운데 고른 번호 목록."""
    G = geo()
    if opt == "reu":
        return list(REU_REGION)
    if opt in ("north", "south", "east"):
        x0, y0 = center(24)
        out, allc = [], []
        for s in states_of(tgt):
            if s in REU_REGION:                      # 리유니온이 이미 핵심주로 가진 땅은 뺀다
                continue
            x, y = center(s)
            dx, dy = x - x0, y - y0
            d = math.hypot(dx, dy)
            if d > 520:
                continue
            ang = math.degrees(math.atan2(dy, dx))          # 화면 y 가 아래로 늘어나므로 위쪽(북)은 -90
            sec = "east" if -35 <= ang <= 35 else "south" if 35 < ang < 145 else "north" if -145 < ang < -35 else None
            allc.append((d, s))
            if sec == opt:
                out.append((d, s))
        got = [s for _, s in sorted(out)[:MAX_STATES]]
        for _, s in sorted(allc):                       # 그쪽 땅이 3곳이 안 되면 가까운 주로 채운다 (지도에 그쪽 우르수스 땅이 적다)
            if len(got) >= 3:
                break
            if s not in got:
                got.append(s)
        return got
    mine = states_of(src)
    cand = states_of(tgt)
    if tgt == "URS":                                  # 체르노보그 주변은 리유니온의 땅이 된다 (REU 가 따로 대상)
        cand = [s for s in cand if s not in REU_REGION]
    if not mine or not cand:
        return []
    adjacent = {s for s in cand if G["adj"].get(s, set()) & set(mine)}
    scored = sorted(cand, key=lambda s: (s not in adjacent, min(dist(s, m) for m in mine)))
    out = scored[:MAX_STATES]
    if opt == "london":                                                  # 론디니움 주를 맨 앞에
        out = [LONDINIUM] + [s for s in out if s != LONDINIUM][:MAX_STATES - 1]
    return out


def tooltip_key(fid):
    return fid + "_claim_tt"


def effect_lines(fid):
    kind, tgt, opt = TABLE[fid]
    src = fid[3:6]
    lines = []
    if kind in ("claim", "dispute", "wargoal"):
        ids = pick(src, tgt, opt)
        if not ids:
            raise SystemExit("영유권 대상 주를 못 찾음: %s (%s -> %s)" % (fid, src, tgt))
        lines += ["custom_effect_tooltip = %s" % tooltip_key(fid),
                  "hidden_effect = { every_state = { limit = { OR = { %s } NOT = { is_owned_by = ROOT } } add_claim_by = ROOT } }"
                  % " ".join("state = %d" % s for s in ids)]
        if kind == "dispute":
            lines += ["if = { limit = { country_exists = %s } %s = { add_opinion_modifier = { target = ROOT modifier = TU_terr_claim_op } } "
                      "add_named_threat = { threat = 2 name = TU_terr_claim_op } }" % (tgt, tgt)]
        if kind == "wargoal":
            lines += ["if = { limit = { country_exists = %s } create_wargoal = { type = take_claimed_state target = %s } }" % (tgt, tgt)]
    else:
        lines += ["custom_effect_tooltip = %s" % tooltip_key(fid),
                  "hidden_effect = { every_state = { limit = { is_owned_by = %s is_claimed_by = ROOT NOT = { is_core_of = ROOT } } "
                  "remove_claim_by = ROOT } }" % tgt,
                  "if = { limit = { country_exists = %s } add_opinion_modifier = { target = %s modifier = TU_terr_treaty_op } "
                  "%s = { add_opinion_modifier = { target = ROOT modifier = TU_terr_treaty_op } } }" % (tgt, tgt, tgt)]
    return lines


def tooltip_text(fid):
    kind, tgt, opt = TABLE[fid]
    ko, en = NAMES[tgt]
    where_ko = {"london": "론디니움과 그 주변", "reu": "체르노보그와 그 주변", "north": "북부", "south": "남부", "east": "동부"}.get(opt, "국경 지대")
    where_en = {"london": "Londinium and its surroundings", "reu": "Chernobog and its surroundings", "north": "the north", "south": "the south",
                "east": "the east"}.get(opt, "the border states")
    if kind == "treaty":
        return ("%s 땅에 대한 §Y영유권을 모두 버리고§! 서로 관계가 좋아진다." % ko,
                "§YDrop every claim§! on the land of %s; relations improve on both sides." % en)
    tail_ko = {"claim": "", "dispute": " 관계가 나빠지고 긴장도가 오른다.", "wargoal": " §Y'영유권 주 획득' 전쟁 목표§!를 얻는다."}[kind]
    tail_en = {"claim": "", "dispute": " Relations worsen and tension rises.", "wargoal": " Gain a §Ywar goal to take the claimed states§!."}[kind]
    return ("%s %s의 주에 §Y영유권§!을 얻는다.%s" % (ko, where_ko, tail_ko),
            "Gain a §Yclaim§! on the states of %s (%s).%s" % (en, where_en, tail_en))


def write_loc():
    for i, lang in enumerate(("korean", "english")):
        lines = ["l_%s:" % lang, " # generated by tools/focusgen/claim_focuses.py (spec 76)"]
        for fid in TABLE:
            lines.append(' %s:0 "%s"' % (tooltip_key(fid), tooltip_text(fid)[i]))
        (MOD / "localisation" / lang / ("tu_claims_l_%s.yml" % lang)).write_bytes(("\n".join(lines) + "\n").encode("utf-8-sig"))


def apply(path, tag):
    """merge_focus 가 쓴 트리 파일 한 개에 적용한다. 반환: 고친 중점 수."""
    ids = [f for f in TABLE if f[3:6] == tag]
    if not ids:
        return 0
    p = Path(path)
    raw = p.read_bytes()
    text = raw.decode("utf-8-sig")
    crlf = "\r\n" in text
    text = text.replace("\r\n", "\n")
    n = 0
    for fid in ids:
        m = re.search(r"\n\tfocus = \{\n\t\tid = %s\n" % re.escape(fid), text)
        if not m:
            raise SystemExit("중점이 없음: %s (%s)" % (fid, p.name))
        end = text.index("\n\t}\n", m.end())
        block = text[m.start():end]
        if tooltip_key(fid) in block:
            continue
        i = block.find("\t\tcompletion_reward = {")
        if i < 0:
            raise SystemExit("completion_reward 없음: %s" % fid)
        # completion_reward 의 닫는 괄호를 중괄호 짝으로 찾는다
        d, k = 0, block.index("{", i)
        while True:
            d += (block[k] == "{") - (block[k] == "}")
            if d == 0:
                break
            k += 1
        add = "".join("\t\t\t%s\n" % l for l in effect_lines(fid))
        block = block[:k].rstrip("\t") + add + "\t\t" + block[k:]
        text = text[:m.start()] + block + text[end:]
        n += 1
    if n:
        out = text.replace("\n", "\r\n") if crlf else text
        p.write_bytes((("﻿" if raw.startswith(b"\xef\xbb\xbf") else "") + out).encode("utf-8"))
    write_loc()
    return n


def main():
    write_loc()
    print("CLAIM_FOCUSES loc written, focuses=%d (트리에는 merge_focus.py 가 적용한다)" % len(TABLE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
