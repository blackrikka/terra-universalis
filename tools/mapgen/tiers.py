#!/usr/bin/env python3
"""국가 체급별 시작 군대·공장·기술 (사양서 18).

사용법:  python -I tools/mapgen/tiers.py   (그다음 build_countries.py 를 다시 돌린다)

체급 (원작 비중 + 땅 크기, 사양서 51에서 다시 맞춤)
    S 열강      염국, 우르수스, 빅토리아, 컬럼비아
    A 지역 강국  사르곤, 카시미어, 라이타니엔, 카즈델, 라테라노
    B 중소국    이베리아, 용문, 극동, 시라쿠사, 볼리바르, 림 빌리튼, 미노스, 쉐라그
    C 소국      사미, 로도스 아일랜드
    인구(사양서 51): 나라 인구를 통행 가능한 주에 나눠 각 주 manpower 에 쓴다 (수도 4배).
    (레유니온은 시작 땅이 없고, 쉐이 12국·황야는 내전/특수 태그라 빼둔다)

만드는 파일
    common/scripted_effects/tu_tier_effects.txt  TU_tier_<TAG>: 시작 때 공장을 짓고 사단을 만든다
        공장: 수도에 절반, 나머지는 인력이 큰 주 최대 3곳에 나눔. 주마다 필요한 만큼 공유 건설 슬롯을 늘린 뒤 즉시 건설.
              (지도 생성 때 모든 수도에 들어간 민간 2·군수 1 은 합계에 포함)
        사단: 수도에 절반, 나머지는 같은 주들에. 이미 시작 효과(TU_<TAG>_startup)로 사단을 만드는 나라는 모자란 만큼만.
    common/on_actions/tu_tier_on_actions.txt     on_startup 에서 위 효과를 부른다
    history/units/<TAG>_1097.txt                 OOB 가 없는 나라: 체급별 보병 사단 틀
    tools/mapgen/tier_history/<TAG>.txt          build_countries 가 history/countries 에 붙인다:
                                                 oob, 연구 슬롯, 시작 기술
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import templates  # noqa: E402
MOD = REPO / "terra_universalis"
HIST = REPO / "tools" / "mapgen" / "tier_history"

# 태그: (체급, 민간 공장, 군수 공장, 사단, 인구(만 명))   사양서 51: 원작 비중 + 땅 크기(주 분할 뒤 프로빈스 수)로 다시 맞춤
TIERS = {
    "YAN": ("S", 32, 18, 28, 2500), "URS": ("S", 28, 22, 32, 2200), "VIC": ("S", 32, 18, 26, 1600),
    "COL": ("S", 36, 14, 20, 1400),
    "SAR": ("A", 14, 10, 20, 1200), "KAZ": ("A", 20, 8, 14, 600), "LEI": ("A", 16, 9, 12, 500),
    "KZD": ("A", 8, 12, 18, 300), "LAT": ("A", 14, 8, 10, 200),
    "IBE": ("B", 10, 5, 10, 400), "LGM": ("B", 14, 4, 8, 300), "HIG": ("B", 8, 6, 12, 300),
    "SIR": ("B", 10, 5, 10, 250), "BOL": ("B", 6, 4, 10, 250), "RIM": ("B", 12, 4, 6, 200),
    "MIN": ("B", 8, 3, 6, 150), "KJE": ("B", 6, 3, 6, 100),
    "SAM": ("C", 3, 2, 6, 60), "RHO": ("C", 4, 3, 5, 30),
}
CAPITAL_WEIGHT = 4                 # 인구를 주에 나눌 때 수도 몫 (나머지 주는 1)
BASE_CIV, BASE_MIL = 2, 1          # mapgen 이 모든 수도에 넣은 공장
# 손으로 만든 OOB 가 있는 나라: 주력 사단 틀 (예전 시작 효과 TU_<TAG>_startup 이 만들던 사단도 이제 OOB 에 넣는다)
EXISTING = {"URS": "TU_URS_infantry", "VIC": "TU_VIC_line_infantry", "KZD": "TU_KZD_infantry",
            "YAN": "TU_YAN_infantry", "LGM": "TU_LGM_guard", "RHO": "TU_RHO_escort"}
# 이름 붙은 특별 사단 (수도에 둔다): (이름, 틀)
SPECIAL_UNITS = {"RHO": [("Rhodes Island Escort 1", "TU_RHO_escort"), ("Rhodes Island Escort 2", "TU_RHO_escort"),
                         ("Rhodes Island Operator Squad", "TU_RHO_operator_squad")]}
RESEARCH_SLOTS = {"S": 4, "A": 3, "B": 3, "C": 2}
BASIC = ["infantry_weapons", "tech_support", "gw_artillery", "basic_train", "tu_oripathy_research"]
TECHS = {   # tools/techgen/build_techs.py 의 기술 id
    "C": BASIC + ["tech_engineers", "tech_recon"],
    "B": BASIC + ["infantry_weapons1", "tech_engineers", "tech_recon", "tech_field_hospital", "basic_machine_tools",
                  "construction1", "tu_arts_theory"],
    "A": BASIC + ["infantry_weapons1", "tech_engineers", "tech_recon", "tech_field_hospital", "basic_machine_tools",
                  "construction1", "tu_arts_theory", "interwar_artillery", "tech_trucks", "gwtank", "early_fighter",
                  "electronic_mechanical_engineering", "tu_ori_refining_1", "tu_landship_1"],
    "S": BASIC + ["infantry_weapons1", "tech_engineers", "tech_recon", "tech_field_hospital", "basic_machine_tools",
                  "construction1", "tu_arts_theory", "interwar_artillery", "tech_trucks", "motorised_infantry", "gwtank",
                  "early_fighter", "early_bomber", "electronic_mechanical_engineering", "tu_ori_refining_1", "tu_landship_1", "fuel_silos",
                  "excavation1"],
}
EXTRA_TECHS = {"LAT": ["tu_lat_firearms_1"], "RIM": ["tu_ori_refining_1"], "RHO": ["tu_suppressants", "tu_field_arts_medicine"]}
EXP = {"S": "0.3", "A": "0.3", "B": "0.2", "C": "0.2"}


def load_states():
    st = {}
    for f in (MOD / "history" / "states").glob("*.txt"):
        t = f.read_text(encoding="utf-8-sig")
        sid = int(re.search(r"\bid\s*=\s*(\d+)", t).group(1))
        o = re.search(r"\bowner\s*=\s*(\w+)", t)
        mp = int(re.search(r"\bmanpower\s*=\s*(\d+)", t).group(1))
        cat = re.search(r"state_category\s*=\s*(\w+)", t).group(1)
        prov = int(re.search(r"provinces\s*=\s*\{\s*(\d+)", t).group(1))
        st[sid] = dict(owner=o.group(1) if o else None, mp=mp, cat=cat, file=f, prov=prov,
                       impassable=bool(re.search(r"impassable\s*=\s*yes", t)))
    return st


def capitals():
    caps = {}
    for f in (MOD / "history" / "countries").glob("*.txt"):
        m = re.search(r"^capital\s*=\s*(\d+)", f.read_text(encoding="utf-8-sig"), re.M)
        if m:
            caps[f.name[:3]] = int(m.group(1))
    return caps


def split(total, n):
    """total 을 수도 절반 + 나머지 n-1 곳에 고르게."""
    if n == 1 or total <= 1:
        return [total] + [0] * (n - 1)
    cap = (total + 1) // 2
    rest = total - cap
    others = [rest // (n - 1) + (1 if i < rest % (n - 1) else 0) for i in range(n - 1)]
    return [cap] + others


def template_text(tag, tier):
    inf = 6 if tier in ("S", "A") else 4
    regs = "\n".join("\t\tinfantry = { x = %d y = %d }" % (i // 3, i % 3) for i in range(inf))
    if tier in ("S", "A"):
        regs += "\n\t\tartillery_brigade = { x = 2 y = 0 }"
    return """# %s starting army (generated by tools/mapgen/tiers.py, tier %s).
# Divisions are listed in units below (tools/mapgen/tiers.py, spec 56).

division_template = {
	name = "TU_%s_line_infantry"
	division_names_group = TU_DIVNAMES_FALLBACK

	regiments = {
%s
	}
	support = {
		engineer = { x = 0 y = 0 }
		recon = { x = 0 y = 1 }
	}
}

units = {
}
""" % (tag, tier, tag, regs)


def division_text(tmpl, prov, exp, name=None):
    nm = '\t\tname = "%s"\n' % name if name else ""
    return ("\tdivision = {\n%s\t\tlocation = %d\n\t\tdivision_template = \"%s\"\n"
            "\t\tstart_experience_factor = %s\n\t\tstart_equipment_factor = 0.8\n\t}" % (nm, prov, tmpl, exp))


def set_units(oob, units):
    """OOB 의 units = { } 블록을 units 로 바꾼다 (없으면 끝에 붙인다)."""
    s = oob.read_text(encoding="utf-8-sig")
    m = re.search(r"\nunits\s*=\s*\{", s)
    body = "units = {\n%s\n}" % "\n".join(units)
    if m:
        j = s.index("{", m.start())
        d, k = 0, j
        while True:
            d += {"{": 1, "}": -1}.get(s[k], 0)
            if d == 0:
                break
            k += 1
        s = s[:m.start() + 1] + body + s[k + 1:]
    else:
        s = s.rstrip("\n") + "\n\n" + body + "\n"
    oob.write_text(s, encoding="utf-8")


def set_state_factories(f, civ, mil, extra):
    """주 히스토리: buildings 의 industrial_complex / arms_factory 를 바꾸고, 공유 건설 슬롯을 extra 만큼 늘린다 (다시 돌려도 같다)."""
    s = f.read_text(encoding="utf-8-sig")
    s = re.sub(r"\n[ \t]*add_extra_state_shared_building_slots\s*=\s*\d+", "", s)
    s = re.sub(r"\n[ \t]*(industrial_complex|arms_factory)\s*=\s*\d+", "", s)
    m = re.search(r"(\n([ \t]*)buildings\s*=\s*\{)", s)
    ind = m.group(2) + "\t"
    add = "".join("\n%s%s = %d" % (ind, k, v) for k, v in (("industrial_complex", civ), ("arms_factory", mil)) if v)
    s = s[:m.end()] + add + s[m.end():]
    if extra:
        s = s[:m.start()] + "\n%sadd_extra_state_shared_building_slots = %d" % (m.group(2), extra) + s[m.start():]
    f.write_text(s, encoding="utf-8")


def set_population(st, caps):
    """사양서 51: 나라 인구(만 명)를 통행 가능한 주에 나눈다. 수도 CAPITAL_WEIGHT, 나머지 1 (다시 돌려도 같다).
    HOI4 는 인구의 약 2.5% 만 징집할 수 있어, 예전 인구(카즈델 20만 등)로는 시작 사단을 보충할 수 없었다."""
    for tag, t in TIERS.items():
        pop = t[4] * 10000
        own = [s for s, d in st.items() if d["owner"] == tag and not d["impassable"]]
        if not own:
            continue
        w = {s: (CAPITAL_WEIGHT if s == caps.get(tag) else 1) for s in own}
        tot = sum(w.values())
        for s in own:
            mp = max(1000, int(round(pop * w[s] / tot, -2)))
            f = st[s]["file"]
            txt = f.read_text(encoding="utf-8-sig")
            new = re.sub(r"(\bmanpower\s*=\s*)\d+", lambda m: m.group(1) + str(mp), txt, count=1)
            if new != txt:
                f.write_text(new, encoding="utf-8")
            st[s]["mp"] = mp


def main():
    st = load_states()
    caps = capitals()
    HIST.mkdir(exist_ok=True)
    set_population(st, caps)
    n_units = n_fac = 0
    for tag, (tier, civ, mil, divs, _pop) in TIERS.items():
        cap = caps.get(tag)
        if cap is None:
            print("skip (no capital):", tag)
            continue
        own = sorted((s for s, d in st.items() if d["owner"] == tag and s != cap and not d["impassable"]),
                     key=lambda s: (-st[s]["mp"], s))
        places = [cap] + own[:3]
        civ_add = split(max(civ - BASE_CIV, 0), len(places))
        mil_add = split(max(mil - BASE_MIL, 0), len(places))
        tmpl = EXISTING.get(tag, "TU_%s_line_infantry" % tag)
        div_add = split(divs, len(places))
        # 공장: 주 히스토리 (사양서 56). 수도에는 mapgen 기본 공장(민간 2·군수 1)을 더한다
        for s, c, m in zip(places, civ_add, mil_add):
            base_c, base_m = (BASE_CIV, BASE_MIL) if s == cap else (0, 0)
            set_state_factories(st[s]["file"], base_c + c, base_m + m, c + m)
            n_fac += c + m
        # 사단: OOB (history/units/<TAG>_1097.txt 의 units 블록)
        units = []
        for (name, t) in SPECIAL_UNITS.get(tag, []):
            units.append(division_text(t, st[cap]["prov"], EXP[tier], name))
        left = divs - len(units)
        for s, d in zip(places, split(left, len(places))):
            units += [division_text(tmpl, st[s]["prov"], EXP[tier]) for _ in range(d)]
        n_units += len(units)
        oob = MOD / "history" / "units" / ("%s_1097.txt" % tag)
        if tag not in EXISTING:
            oob.write_text(template_text(tag, tier), encoding="utf-8")
            templates.apply_file(oob)     # 기본 편제 통일 (사양서 52): 20폭 주력 보병
        set_units(oob, units)

        hist = ["# %s: tier %s (generated by tools/mapgen/tiers.py, appended by build_countries.py)" % (tag, tier)]
        hist.append("set_research_slots = %d" % RESEARCH_SLOTS[tier])
        hist.append("set_technology = {\n%s\n}" % "\n".join("\t%s = 1" % t for t in TECHS[tier] + EXTRA_TECHS.get(tag, [])))
        if tag not in EXISTING:
            hist.append('oob = "%s_1097"' % tag)
        (HIST / ("%s.txt" % tag)).write_text("\n".join(hist) + "\n", encoding="utf-8")

    # 예전 on_startup 방식(사양서 51·55)은 지운다: 게임에서 공장이 지어지지 않았다 (사양서 56)
    for old in (MOD / "common" / "scripted_effects" / "tu_tier_effects.txt",
                MOD / "common" / "on_actions" / "tu_tier_on_actions.txt"):
        if old.is_file():
            old.unlink()
    calls = [t for t in TIERS]
    print("tiers: factories added %d, divisions %d" % (n_fac, n_units))
    print("tiers:", len(calls), "countries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
