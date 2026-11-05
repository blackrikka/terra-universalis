#!/usr/bin/env python3
"""이베리아(IBE) 고유 콘텐츠 (사양서 17).

장치
  1. 바다의 위협 TU_IBE_threat (0~100, 시작 40): 매달 +2 (복원한 등대 하나마다 -0.5 덜 오름). 70 이상이면 '심해의 침식'
     이벤트(해안 마을 피해)가 반복된다. 해안 감시·정화 작전 디시전과 중점으로 낮춘다.
  2. 등대 복원 TU_IBE_lighthouses (0~5): 디시전으로 하나씩 복원 (기반시설 + 위협 감소).
  3. (세력 균형 "심판소 대 왕관"은 사양서 34에서 삭제)
정치 결말 셋 (서로 배타): 심판관의 나라(심판소 2단계) / 왕관의 부활(왕관 2단계) / 바다와의 화해(위협 20 이하 + 아비살 사냥꾼 접촉).

실행: python -I tools/focusgen/content/ibe.py && python -I tools/focusgen/merge_focus.py --tag IBE
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_lib import Country  # noqa: E402

C = Country("IBE", "이베리아", "Iberia")
f = C.f
BOP = "TU_IBE_bop"
MAXV = {"threat": 100, "lighthouses": 5}
NAMES = {"threat": ("§R바다의 위협§!", "§RSea Threat§!"), "lighthouses": ("§Y복원한 등대§!", "§YLighthouses Restored§!")}


def V(var, n):
    name = "TU_IBE_%s_%s%d" % (var, "m" if n < 0 else "", abs(n))
    if not any(e.startswith(name + " =") for e in C.effects):
        C.effects.append("""%s = {
	custom_effect_tooltip = %s_tt
	hidden_effect = {
		add_to_variable = { TU_IBE_%s = %d }
		clamp_variable = { var = TU_IBE_%s min = 0 max = %d }
	}
}""" % (name, name, var, n, var, MAXV[var]))
        ko, en = NAMES[var]
        C.loc(name + "_tt", "%s %s%d" % (ko, "+" if n > 0 else "", n), "%s %s%d" % (en, "+" if n > 0 else "", n))
    return "%s = yes" % name


def THR(n):
    return V("threat", n)


def AT_LEAST(var, n):
    return "check_variable = { TU_IBE_%s > %d }" % (var, n - 1)


def AT_MOST(var, n):
    return "check_variable = { TU_IBE_%s < %d }" % (var, n + 1)


def INQ(v):   # 세력 균형 삭제 (사양서 34): 효과 없음
    return ""


def CROWN(v):
    return ""


def FLAG(x):
    return "set_country_flag = TU_IBE_%s" % x


def HAS(x):
    return "has_country_flag = TU_IBE_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_ibe_ev.%d%s }" % (n, " days = %d" % days if days else "")


C.history += ["set_variable = { TU_IBE_threat = 40 }", "set_variable = { TU_IBE_lighthouses = 0 }",
              "add_ideas = { TU_IBE_great_silence TU_IBE_fear_of_the_sea }"]
C.effects.append("""TU_IBE_monthly = {
	TU_IBE_lighthouse_monthly = yes
	add_to_variable = { TU_IBE_threat = 2 }
	set_temp_variable = { tu_ibe_lh = TU_IBE_lighthouses }
	subtract_from_temp_variable = { tu_ibe_lh = TU_IBE_lh_damaged }
	multiply_temp_variable = { tu_ibe_lh = -0.5 }
	add_to_variable = { TU_IBE_threat = tu_ibe_lh }
	clamp_variable = { var = TU_IBE_threat min = 0 max = 100 }
	if = {
		limit = { has_country_flag = TU_IBE_ishar_route }
		set_variable = { TU_IBE_threat = 0 }
	}
}""")
C.on_actions.append("""on_monthly = {
	effect = {
		if = {
			limit = { original_tag = IBE }
			TU_IBE_monthly = yes
		}
	}
}""")

# ------------------------------------------------------------------ 국민정신
C.idea("great_silence", "대침묵의 상흔", "Scars of the Great Silence", {"production_speed_buildings_factor": -0.1, "monthly_population": -0.1},
       "generic_army_problems", ("바다에서 무언가가 올라왔고, 이베리아의 해안은 침묵했다.", "Something rose from the sea, and Iberia's coast fell silent."))
C.idea("fear_of_the_sea", "바다의 공포", "Fear of the Sea", {"political_power_gain": -0.1, "stability_factor": -0.03}, "generic_economic_increase",
       ("어부들은 더 이상 먼바다로 나가지 않는다.", "Fishermen no longer sail into deep waters."))
C.idea("watchful_coast", "깨어 있는 해안", "The Watchful Coast", {"army_defence_factor": 0.05, "stability_factor": 0.03}, "generic_fortify_the_borders")
C.idea("inquisitor_state", "심판관의 나라", "State of the Inquisitors", {"stability_factor": 0.1, "army_org_factor": 0.05, "political_power_gain": 0.05},
       "generic_secret_police")
C.idea("crown_restored", "왕관의 부활", "The Crown Restored", {"political_power_gain": 0.15, "production_speed_buildings_factor": 0.1}, "generic_central_management")
C.idea("sea_reconciliation", "바다와의 화해", "Reconciliation with the Sea", {"political_power_gain": 0.1, "army_org_factor": 0.05, "stability_factor": 0.05},
       "generic_economic_increase")
C.idea("inquisitor_corps", "심판관 정예대", "Elite Inquisitor Corps", {"army_attack_factor": 0.05, "army_org_factor": 0.05}, "professional_officer_corps_spirit")
C.idea("purified_coast", "정화된 해안", "The Purified Coast", {"monthly_population": 0.1, "production_speed_buildings_factor": 0.05}, "generic_morale_bonus")

# ------------------------------------------------------------------ 중점
f("root", "대침묵 이후", "After the Great Silence", cost=5, theme=False, reward=["add_political_power = 50", EV(1)],
  desc=("반세기 전, 바다가 이베리아를 삼켰다. 남은 것은 심판소와 텅 빈 해안 도시들이다.",
        "Half a century ago the sea swallowed Iberia. What remains is the Inquisition and empty coastal towns."))

# A. 심판소
f("inquisition_reform", "심판소 재편", "Inquisition Court Reform", pre=["root"], reward=[INQ("0.05")])
f("inquisitor_academy", "심판관 학교", "Inquisitor Academy", pre=["inquisition_reform"])
f("heresy_files", "이단 기록", "Heresy Files Archive", pre=["inquisition_reform"], reward=[INQ("0.03")])
f("inquisitor_guard", "심판관 근위대", "Inquisitor Guard", pre=["inquisitor_academy"])
f("purge_cults", "심해 숭배 단속", "Purge the Deep-Sea Cults", pre=["heresy_files"], theme=False, reward=[INQ("0.05"), THR(-10), EV(21, 10)])
f("faith_laws", "신앙 법", "Faith Laws", pre=["purge_cults"], me=["tolerance"], reward=[INQ("0.05")])
f("tolerance", "관용령", "Edict of Tolerance", pre=["purge_cults"], me=["faith_laws"], reward=[CROWN("0.05")])
f("inquisitor_state", "심판관의 나라", "State of the Inquisitors", pre=[["faith_laws", "tolerance"], "inquisitor_guard"],
  me=["crown_restored", "sea_reconciliation"], cost=15, theme=False,
  reward=[FLAG("path_inq"), "add_ideas = TU_IBE_inquisitor_state", EV(28)],
  desc=("심판소가 이베리아를 영원히 지킨다.", "The Inquisition guards Iberia forever."))
f("eternal_vigil", "영원한 경계", "Eternal Vigil Watch", pre=["inquisitor_state"])
f("inquisition_navy", "심판소 함대", "Inquisition Fleet", pre=["inquisitor_state"])
f("judgement_day", "심판의 날", "Day of Judgement Campaign", pre=["eternal_vigil", "inquisition_navy"], theme=False,
  reward=[THR(-20), "add_war_support = 0.1"])

# B. 왕관
f("crown_council", "왕실 회의", "Crown Council", pre=["root"], reward=[CROWN("0.05")])
f("royal_heir", "왕실의 후계자", "The Royal Heir", pre=["crown_council"], theme=False, reward=[CROWN("0.05"), EV(22)])
f("nobles_return", "귀족의 귀환", "Return of the Nobles", pre=["crown_council"], reward=[CROWN("0.05")])
f("royal_treasury", "왕실 재정", "Royal Treasury", pre=["nobles_return"])
f("royal_army", "왕립군", "Royal Army Regiments", pre=["royal_heir"])
f("crown_charter", "왕관 헌장", "Crown Charter", pre=["royal_treasury", "royal_army"], reward=[CROWN("0.05")])
f("crown_restored", "왕관의 부활", "The Crown Restored", pre=["crown_charter"], me=["inquisitor_state", "sea_reconciliation"],
  cost=15, theme=False,
  reward=[FLAG("path_crown"), "add_ideas = TU_IBE_crown_restored", EV(29)],
  desc=("왕이 다시 이베리아를 다스린다.", "A king rules Iberia again."))
f("royal_reconstruction", "왕실 재건 사업", "Royal Reconstruction Works", pre=["crown_restored"], econ=True)
f("royal_navy", "왕립 해군", "Royal Navy", pre=["crown_restored"])
f("golden_age", "새로운 황금기", "A New Golden Age", pre=["royal_reconstruction", "royal_navy"], theme=False,
  reward=["add_political_power = 100", "add_stability = 0.05"])

# C. 바다의 위협
f("coastal_watch", "해안 감시", "Coastal Watch", pre=["root"], theme=False, reward=[FLAG("coast"), THR(-5)],
  desc=("'해안' 디시전이 열린다 (등대 복원, 해안 순찰, 정화 작전).", "Unlocks the Coast decisions (lighthouses, patrols, purification)."))
f("sea_studies", "바다의 위협 연구", "Study of the Sea Threat", pre=["coastal_watch"], reward=[THR(-5)])
f("tide_charts", "조류 기록", "Tide Charts Records", pre=["coastal_watch"])
f("abyssal_rumours", "심해 사냥꾼의 소문", "Rumours of the Abyssal Hunters", pre=["sea_studies"], theme=False, reward=[EV(23, 15)])
f("coastal_forts", "해안 요새", "Coastal Fortress Line", pre=["tide_charts"], me=["fleet_rebuild"])
f("fleet_rebuild", "함대 재건", "Fleet Reconstruction", pre=["tide_charts"], me=["coastal_forts"])
f("watchful_coast", "깨어 있는 해안", "The Watchful Coast", pre=[["coastal_forts", "fleet_rebuild"]], theme=False,
  reward=["swap_ideas = { remove_idea = TU_IBE_fear_of_the_sea add_idea = TU_IBE_watchful_coast }", THR(-10)])
f("deep_sea_plan", "심해 대비 계획", "Deep Sea Defence Plan", pre=["watchful_coast"], reward=[THR(-5)])
f("sea_reconciliation", "바다와의 화해", "Reconciliation with the Sea", pre=["abyssal_rumours", "deep_sea_plan"],
  me=["inquisitor_state", "crown_restored"], cost=15, theme=False, available=[AT_MOST("threat", 20), HAS("hunters_met")],
  reward=[FLAG("path_sea"), "add_ideas = TU_IBE_sea_reconciliation", "remove_ideas = TU_IBE_great_silence", EV(30)],
  desc=("바다의 것들과 공존할 길을 찾는다. (위협 20 이하, 아비살 사냥꾼과 만나야 함)",
        "Find a way to live alongside what lies in the sea. (Threat 20 or less, must have met the Abyssal Hunters)"))
f("aegir_contact", "에기르와의 접촉", "Contact with Aegir Envoys", pre=["sea_reconciliation"])
f("deep_sea_trade", "심해 교역", "Deep Sea Trade", pre=["aegir_contact"])

# D. 군사
f("mountain_infantry", "산악 보병", "Mountain Infantry Regiments", pre=["root"])
f("bayonet_drill", "총검술 훈련", "Bayonet Drill", pre=["mountain_infantry"])
f("mobile_doctrine", "기동전 교리", "Mobile Warfare Doctrine", pre=["bayonet_drill"], me=["trench_doctrine"])
f("trench_doctrine", "참호 방어", "Trench Defence", pre=["bayonet_drill"], me=["mobile_doctrine"])
f("artillery_rebuild", "포병 재건", "Artillery Rebuild", pre=["mountain_infantry"])
f("elite_inquisitors", "정예 심판관", "Elite Inquisitor Training", pre=[["mobile_doctrine", "trench_doctrine"], "artillery_rebuild"], theme=False,
  reward=["add_ideas = TU_IBE_inquisitor_corps", "army_experience = 40"])
f("rifle_workshops", "소총 공방", "Rifle Workshops", pre=["mountain_infantry"])
f("harpoon_guns", "작살포", "Harpoon Guns Artillery", pre=["rifle_workshops"])
f("anti_creature", "대괴물 전술", "Anti-Creature Tactics", pre=["harpoon_guns"], reward=[THR(-5)])
f("cavalry_patrols", "기병 순찰", "Cavalry Patrols", pre=["bayonet_drill"])
f("motor_pool", "차량 정비", "Motor Pool Motorised", pre=["cavalry_patrols"])
f("officer_corps", "장교단", "Officer Corps Training", pre=["elite_inquisitors"])
f("air_watch", "해안 비행 감시", "Coastal Air Watch", pre=["officer_corps"])

# E. 해군
f("naval_school", "해군 학교", "Naval Academy", pre=["fleet_rebuild"])
f("coastal_gunboats", "연안 포함", "Coastal Gunboat Fleet", pre=["naval_school"])
f("destroyers", "구축함 전대", "Destroyer Fleet", pre=["coastal_gunboats"])
f("iberian_navy", "이베리아 해군", "Iberian Navy", pre=["destroyers"], theme=False, reward=["add_ideas = TU_IBE_iberian_navy", "army_experience = 50"])
f("dockyards", "조선소 재건", "Dockyard Rebuild", pre=["naval_school"], econ="TU_build_civ_factory = yes")

# F. 경제
f("harbour_rebuild", "항구 재건", "Harbour Reconstruction", pre=["root"], econ="TU_build_civ_factory = yes")
f("road_network", "도로망 건설", "Road Network", pre=["harbour_rebuild"], econ="TU_build_infrastructure = yes")
f("industrial_district", "공업 지구", "Industrial District", pre=["harbour_rebuild"], econ=True)
f("civ_program", "민간 공장 계획", "Civilian Factory Program", pre=["industrial_district"], me=["arms_program"], econ=True)
f("arms_program", "군수 공장 계획", "Arms Factory Program", pre=["industrial_district"], me=["civ_program"], econ="TU_build_mil_factory = yes")
f("rail_network", "철도 연결", "Rail Network Expansion", pre=["road_network"], econ="TU_build_infrastructure = yes")
f("resettle_coast", "해안 재정착", "Resettle the Coast Housing", pre=["rail_network"], theme=False, available=[AT_MOST("threat", 50)],
  reward=["TU_build_civ_factory = yes", "add_manpower = 10000"], desc=("바다의 위협 50 이하.", "Sea threat 50 or less."), filt="FOCUS_FILTER_INDUSTRY")
f("purified_coast", "정화된 해안", "The Purified Coast", pre=["resettle_coast"], theme=False, available=[AT_MOST("threat", 30)],
  reward=["add_ideas = TU_IBE_purified_coast", "remove_ideas = TU_IBE_great_silence"], desc=("바다의 위협 30 이하. 대침묵의 상흔을 없앤다.", "Sea threat 30 or less. Removes Scars of the Great Silence."))
f("fishing_guild", "어업 조합", "Fishing Guild Trade", pre=["harbour_rebuild"])
f("wine_trade", "포도주 교역", "Wine Trade", pre=["fishing_guild"])
f("industrial_revival", "이베리아 산업 부흥", "Iberian Industrialisation", pre=[["civ_program", "arms_program"], "rail_network"], econ=True)
f("research_slot", "왕립 해양 연구원", "Royal Oceanography Institute", pre=["industrial_revival", "sea_studies"], theme=False,
  reward=["add_research_slot = 1"], desc=("연구 슬롯 +1", "Research slot +1"))

# G. 외교
f("foreign_office", "외교부", "Foreign Office", pre=["root"])
f("laterano_schism", "라테라노와의 분열", "The Laterano Schism", pre=["foreign_office"], theme=False, reward=[EV(24)])
f("sargon_border", "사르곤 국경", "Sargon Border Watch", pre=["foreign_office"])
f("victoria_trade", "빅토리아 교역", "Victoria Trade Accord", pre=["sargon_border"])
f("rhodes_doctors", "로도스 아일랜드의 의사들", "Rhodes Island Doctors Relief", pre=["laterano_schism"])
f("coastal_league", "해안 연맹", "Coastal League Alliance", pre=["victoria_trade", "rhodes_doctors"], theme=False, reward=[FLAG("league")],
  desc=("'해안 연맹' 디시전이 열린다.", "Unlocks the Coastal League decisions."))

# 보강
for sid, ko, en, pre, econ in (
        ("confessors", "고해 신부", "Confessor Network Intelligence", "heresy_files", False),
        ("relic_vaults", "성유물 금고", "Relic Vaults Archive", "inquisitor_academy", False),
        ("silent_monks", "침묵의 수도사", "Silent Monks Propaganda", "faith_laws", False),
        ("tribunal_courts", "재판정", "Tribunal Courts Reform", "inquisitor_guard", False),
        ("noble_estates", "귀족 영지", "Noble Estates Farms", "nobles_return", True),
        ("crown_jewels", "왕관 보석", "Crown Jewels Treasury", "royal_treasury", False),
        ("royal_guard", "왕실 근위대", "Royal Guard Regiments", "royal_army", False),
        ("crown_propaganda", "왕관 선전", "Crown Propaganda", "crown_charter", False),
        ("lighthouse_keepers", "등대지기", "Lighthouse Keepers Watch", "coastal_watch", False),
        ("sea_wall", "방파제", "Sea Wall Fortifications", "coastal_forts", False),
        ("depth_charges", "폭뢰", "Depth Charge Navy", "fleet_rebuild", False),
        ("sea_samples", "심해 표본", "Deep Sea Specimens Research", "sea_studies", False),
        ("mountain_forts", "산악 요새", "Mountain Fortresses", "trench_doctrine", False),
        ("field_hospitals", "야전 병원", "Field Hospitals", "artillery_rebuild", False),
        ("supply_trains", "보급 열차", "Supply Trains Logistics", "motor_pool", False),
        ("light_tanks", "경전차", "Light Tank Units", "motor_pool", False),
        ("submarine_hunters", "대잠 전대", "Anti-Submarine Fleet", "destroyers", False),
        ("cork_forests", "코르크 숲", "Cork Forest Industry", "fishing_guild", True),
        ("copper_mines", "구리 광산", "Copper Mines", "industrial_district", True),
        ("power_plants", "발전소", "Power Plants", "rail_network", True),
        ("kazdel_refugees", "피난민 수용", "Refugee Shelters", "rhodes_doctors", False),
        ("minos_ties", "미노스 교류", "Minos Exchange", "foreign_office", False)):
    f(sid, ko, en, pre=[pre], econ=econ)

# ------------------------------------------------------------------ 디시전
cat_coast = C.category("coast", "해안", "The Coast",
                       ("바다의 위협은 매달 오르고, 온전한 등대 하나마다 덜 오른다. 70 이상이면 해안 마을이 침식된다.\n"
                        "등대는 매달 시테러에게 손상될 수 있다. 지도에서 등대마다 위협 수준을 확인하고, 해안 요새와 수비대로 지켜라. "
                        "등대를 지키는 수비대는 가끔 습격을 받아 조직력과 병력을 잃고, 등대가 손상된 동안에는 습격이 잦아진다.",
                        "The sea threat rises every month, less for each intact lighthouse. At 70+ coastal towns are eroded.\n"
                        "Lighthouses can be damaged by Sea Terrors each month. Check each lighthouse's threat on the map and guard it with "
                        "coastal forts and garrisons. Lighthouse garrisons are sometimes ambushed and lose organisation and strength, more often while the lighthouse is damaged."),
                       visible=[HAS("coast")])
# ------------------------------------------------------------------ 등대 (사양서 29·31)
# 주 대상 디시전: 디시전 탭을 열면 지도에서 해당 주 위에 버튼이 뜬다. 주 깃발:
#   TU_IBE_lighthouse 등대 있음 / TU_IBE_lh_damaged 손상 / TU_IBE_lh_repairing 보수 중 / TU_IBE_lh_fort_building 요새 공사 중
# 주 변수: TU_IBE_lh_risk 월간 손상 확률(%) / TU_IBE_lh_fort 해안 요새 단계(0~3)
# 손상 확률 = 위협/4 x (1 - 0.25 x 요새) x 수비대 병력 보정 (LH_GARRISON), 최소 LH_MIN_RISK. 이샤믈라 루트는 0.
LH_FORT_MAX = 3
LH_MIN_RISK = 2             # 최소 월간 손상 확률 % (이샤믈라 루트만 0)
LH_RAID_DAMAGED_MULT = 3    # 등대가 손상된 동안 습격 확률 배율 (평소 = 손상 확률의 절반)
# (id, 한, 영, 색, 하한 %(이상), 상한 %(미만), 설명에 쓰는 구간 한/영). 숨은 루트(이샤믈라)의 0% 는 "매우 적음"에 들어간다 (화면에 언급하지 않음)
LH_BANDS = [
    ("vh", "매우 높음", "Very High", "R", 15, None, "15% 이상", "15% or more"),
    ("h", "높음", "High", "O", 9, 15, "9~15%", "9-15%"),
    ("m", "보통", "Moderate", "Y", 4, 9, "4~9%", "4-9%"),
    ("l", "낮음", "Low", "G", LH_MIN_RISK + 0.01, 4, "%d~4%%" % LH_MIN_RISK, "%d-4%%" % LH_MIN_RISK),
    ("vl", "매우 적음", "Very Low", "G", None, LH_MIN_RISK + 0.01, "%d%%" % LH_MIN_RISK, "%d%%" % LH_MIN_RISK),
]


def coastal_states():
    """지도에서 통행 가능한 해안 육지 주 -> 그 주의 해안 프로빈스 목록 (수비대·요새 조건을 주·프로빈스마다 펼치는 데 쓴다.
    지도를 다시 만들면 이 파일도 다시 돌린다)."""
    import re as _re
    from content_lib import MOD
    coast = set()
    for row in (MOD / "map" / "definition.csv").read_text(encoding="ascii").splitlines():
        p = row.split(";")
        if len(p) > 5 and p[4] == "land" and p[5] == "true":
            coast.add(int(p[0]))
    out = {}
    for fp in (MOD / "history" / "states").glob("*.txt"):
        t = fp.read_text(encoding="utf-8-sig")
        if _re.search(r"impassable\s*=\s*yes", t):
            continue
        ps = {int(x) for x in _re.search(r"provinces\s*=\s*\{([^}]*)\}", t).group(1).split()}
        if ps & coast:
            out[int(_re.search(r"\bid\s*=\s*(\d+)", t).group(1))] = sorted(ps & coast)
    return dict(sorted(out.items()))


# 수비대: 그 주에 있는 ROOT(이베리아) 사단의 실제 병력 (army_manpower_in_state 는 주 번호를 받으므로 해안 주마다 펼친다).
# 병력이 깎인 사단은 적게 세므로, 습격 피해를 보충할 때까지 방어 효과도 약해진다. 주마다 배치된 장비를 세는 조건은 없어 장비는 보지 않는다.
LH_GARRISON = [(40000, 0.45), (20000, 0.6), (10000, 0.8)]     # (병력 이상, 손상 확률 배율) 큰 것부터
LH_PURGE_MP = 30000
COAST = coastal_states()
for mp in sorted({m for m, _ in LH_GARRISON} | {LH_PURGE_MP}):
    C.triggers.append("TU_IBE_garrison_%dk = {\n\tOR = {\n%s\n\t}\n}" % (mp // 1000, "\n".join(
        "\t\tAND = { state = %d ROOT = { army_manpower_in_state = { state = %d amount > %d } } }" % (s, s, mp - 1)
        for s in COAST)))
# 습격 피해: 그 주의 사단 조직력 -30%, 내구도(병력·장비) -5%. 사단이 회복하면서 국가 인력·장비를 끌어다 채운다
C.effects.append("TU_IBE_raid_damage = {\n%s\n}" % "\n".join(
    "\tif = {\n\t\tlimit = { state = %d }\n\t\tROOT = { damage_units = { state = %d org_damage = 0.3 str_damage = 0.05 ratio = yes army = yes } }\n\t}"
    % (s, s) for s in COAST))

# 해안 요새: 그 주 해안 프로빈스들의 해안 요새 평균 단계 -> 주 변수 TU_IBE_lh_fort (0~3).
# 한 프로빈스에 도배해도 소용없게 프로빈스마다 LH_FORT_MAX 단계까지만 센다. HOI4 에는 프로빈스를 도는 스코프가 없어
# 프로빈스 번호를 지정하는 any_province_building_level 을 해안 프로빈스마다 펼친다.
C.effects.append("TU_IBE_lh_fort_measure = {\n\tset_variable = { TU_IBE_lh_fort = 0 }\n%s\n}" % "\n".join(
    "\t%sif = {\n\t\tlimit = { state = %d }\n%s\n\t\tdivide_variable = { TU_IBE_lh_fort = %d }\n\t}" % (
        "else_" if i else "", s, "\n".join(
            "\t\tif = { limit = { any_province_building_level = { province = { id = %d } building = coastal_bunker level > %d } } "
            "add_to_variable = { TU_IBE_lh_fort = 1 } }" % (p, lv) for p in ps for lv in range(LH_FORT_MAX)), len(ps))
    for i, (s, ps) in enumerate(COAST.items())))
# 해안 요새 파손: 그 주의 해안 프로빈스 하나를 골라 해안 요새에 피해 (수리는 건설 슬롯이 자동으로 한다)
C.effects.append("TU_IBE_lh_fort_decay = {\n%s\n}" % "\n".join(
    "\t%sif = {\n\t\tlimit = { state = %d }\n\t\trandom_list = {\n%s\n\t\t}\n\t}" % (
        "else_" if i else "", s, "\n".join(
            "\t\t\t1 = { damage_building = { type = coastal_bunker damage = 1 province = %d } }" % p for p in ps))
    for i, (s, ps) in enumerate(COAST.items())))

C.effects.append("""TU_IBE_lh_update_risk = {
	TU_IBE_lh_fort_measure = yes
	set_variable = { TU_IBE_lh_risk = ROOT.TU_IBE_threat }
	divide_variable = { TU_IBE_lh_risk = 4 }
	set_temp_variable = { tu_ibe_f = TU_IBE_lh_fort }
	multiply_temp_variable = { tu_ibe_f = -0.25 }
	add_to_temp_variable = { tu_ibe_f = 1 }
	multiply_variable = { TU_IBE_lh_risk = tu_ibe_f }
%s
	if = {
		limit = { check_variable = { TU_IBE_lh_risk < %s } }
		set_variable = { TU_IBE_lh_risk = %s }
	}
	if = {
		limit = { ROOT = { has_country_flag = TU_IBE_ishar_route } }
		set_variable = { TU_IBE_lh_risk = 0 }
	}
}""" % ("\n".join(
    "\t%sif = {\n\t\tlimit = { TU_IBE_garrison_%dk = yes }\n\t\tmultiply_variable = { TU_IBE_lh_risk = %s }\n\t}"
    % ("else_" if i else "", mp // 1000, f) for i, (mp, f) in enumerate(LH_GARRISON)), LH_MIN_RISK, LH_MIN_RISK))
C.effects.append("""TU_IBE_lighthouse_monthly = {
	set_variable = { TU_IBE_lighthouses = 0 }
	set_variable = { TU_IBE_lh_damaged = 0 }
	every_owned_state = {
		limit = { has_state_flag = TU_IBE_lighthouse }
		ROOT = { add_to_variable = { TU_IBE_lighthouses = 1 } }
		TU_IBE_lh_update_risk = yes
		if = {
			limit = { has_state_flag = TU_IBE_lh_damaged }
			ROOT = { add_to_variable = { TU_IBE_lh_damaged = 1 } }
		}
		else_if = {
			limit = { NOT = { has_state_flag = TU_IBE_lh_repairing } }
			set_temp_variable_to_random = { var = tu_ibe_roll min = 0 max = 100 }
			if = {
				limit = { check_variable = { tu_ibe_roll < TU_IBE_lh_risk } }
				TU_IBE_lh_damage = yes
				ROOT = { add_to_variable = { TU_IBE_lh_damaged = 1 } }
			}
		}
		# 해안 요새 파손: 요새가 있으면 손상 확률과 같은 확률로 해안 프로빈스 하나의 요새에 피해
		if = {
			limit = { check_variable = { TU_IBE_lh_fort > 0 } }
			set_temp_variable_to_random = { var = tu_ibe_roll min = 0 max = 100 }
			if = {
				limit = { check_variable = { tu_ibe_roll < TU_IBE_lh_risk } }
				TU_IBE_lh_fort_decay = yes
			}
		}
		# 해안 수비대 습격 (병력 1만 이상, 상시): 확률 = 손상 확률의 절반, 등대가 손상된 동안은 그 3배. 그 주 사단에 피해
		if = {
			limit = { TU_IBE_garrison_10k = yes }
			set_temp_variable = { tu_ibe_raid = TU_IBE_lh_risk }
			if = {
				limit = { has_state_flag = TU_IBE_lh_damaged }
				multiply_temp_variable = { tu_ibe_raid = %s }
			}
			set_temp_variable_to_random = { var = tu_ibe_roll min = 0 max = 200 }
			if = {
				limit = { check_variable = { tu_ibe_roll < tu_ibe_raid } }
				TU_IBE_raid_damage = yes
				save_event_target_as = tu_ibe_raid_state
				ROOT = { country_event = { id = tu_ibe_ev.52 } }
			}
		}
	}
}""" % LH_RAID_DAMAGED_MULT)
C.effects.append("""TU_IBE_lh_damage = {
	set_state_flag = TU_IBE_lh_damaged
	save_event_target_as = tu_ibe_lh_state
	ROOT = {
		activate_targeted_decision = { target = PREV decision = TU_IBE_lh_crumbling }
		country_event = { id = tu_ibe_ev.50 }
	}
}""")

C.d(cat_coast, "restore_lighthouse", "등대 복원", "Restore a Lighthouse",
    ["""FROM = {
	set_state_flag = TU_IBE_lighthouse
	if = {
		limit = { infrastructure < 5 }
		add_building_construction = { type = infrastructure level = 1 instant_build = yes }
	}
	TU_IBE_lh_update_risk = yes
}""", V("lighthouses", 1), THR(-5), "set_country_flag = { flag = TU_IBE_lighthouse_cooldown days = 120 value = 1 }"],
    cost=50, once=False, state_target=True,
    target=["is_coastal = yes", "is_owned_and_controlled_by = ROOT", "NOT = { has_state_flag = TU_IBE_lighthouse }"],
    available=[AT_MOST("lighthouses", 4), "NOT = { has_country_flag = TU_IBE_lighthouse_cooldown }"],
    desc=("이 해안 주의 등대를 복원한다: 등대 +1 (최대 5), 위협 -5, 이 주의 기반시설 +1. 복원 사이 120일.\n복원한 등대는 시테러에게 손상될 수 있다. 해안 요새와 수비대로 위험을 줄인다.",
          "Restore this coastal state's lighthouse: lighthouse +1 (max 5), threat -5, +1 infrastructure here. 120 days between restorations.\nRestored lighthouses can be damaged by Sea Terrors. Coastal forts and garrisons lower the risk."),
    icon="GFX_decision_generic_construction")

# 위협 표시: 등대가 있는 주마다 위협 구간에 맞는 하나만 보인다 (누를 수 없음, 이름에 구간이 나온다).
# 기간이 있는 디시전(요새·보수)은 진행 중에 대상 조건이 거짓이 되면 취소될 수 있어, 매달 바뀌는 구간은 표시 전용으로 뗀다.
LH_WHY = ("손상 확률 = 바다의 위협 ÷ 4 × 요새 보정(해안 요새 평균 단계마다 -25%%%%) × 수비대 보정(이 주의 병력 1만 ×0.8 / 2만 ×0.6 / 4만 ×0.45), "
          "최소 %d%%%%. 매달 다시 계산한다." % LH_MIN_RISK,
          "Damage chance = Sea Threat ÷ 4 × fort factor (-25%%%% per average coastal fort level) × garrison factor (manpower here 10k x0.8 / 20k x0.6 / 40k x0.45), "
          "at least %d%%%%. Recalculated monthly." % LH_MIN_RISK)
for bid, ko, en, col, lo, hi, rng_ko, rng_en in LH_BANDS:
    band = ["check_variable = { TU_IBE_lh_risk > %s }" % (lo - 0.001) if lo is not None else "",
            "check_variable = { TU_IBE_lh_risk < %s }" % hi if hi is not None else ""]
    C.d(cat_coast, "lh_threat_" + bid, "[FROM.GetName] 등대 — 시테러 위협: §%s%s§!" % (col, ko),
        "[FROM.GetName] Lighthouse — Sea Terror threat: §%s%s§!" % (col, en), [], cost=0, once=False, state_target=True,
        target=["is_owned_and_controlled_by = ROOT", "has_state_flag = TU_IBE_lighthouse"] + [b for b in band if b],
        available=["always = no"],
        desc=("이 등대의 월간 손상 확률: %s.\n%s" % (rng_ko, LH_WHY[0] % ()), "This lighthouse's monthly damage chance: %s.\n%s" % (rng_en, LH_WHY[1] % ())),
        icon="GFX_decision_generic_civil_support", ai=0)

C.d(cat_coast, "lh_fort", "[FROM.GetName] 등대 해안 요새 보강", "Fortify the [FROM.GetName] Lighthouse Coast",
    ["FROM = { set_state_flag = TU_IBE_lh_fort_building }"], cost=40, once=False, state_target=True, days_remove=45,
    modifier={"civilian_factory_use": 2},
    remove_effect=["""FROM = {
	clr_state_flag = TU_IBE_lh_fort_building
	add_building_construction = { type = coastal_bunker level = 1 province = { all_provinces = yes limit_to_coastal = yes } instant_build = yes }
	TU_IBE_lh_update_risk = yes
}"""],
    target=["is_owned_and_controlled_by = ROOT", "OR = { has_state_flag = TU_IBE_lighthouse has_state_flag = TU_IBE_lh_fort_building }"],
    available=["FROM = { check_variable = { TU_IBE_lh_fort < %d } }" % LH_FORT_MAX,
               "FROM = { NOT = { has_state_flag = TU_IBE_lh_fort_building } }"],
    desc=("정치력 40, 45일 동안 민간 공장 2개 사용, 끝나면 이 주의 모든 해안 프로빈스에 해안 요새 +1.\n"
          "등대의 손상 확률은 이 주 해안 프로빈스들의 해안 요새 §Y평균§! 단계로 정해진다: 평균 1단계마다 -25%, 최대 3단계 "
          "(한 프로빈스는 3단계까지만 센다). 해안 요새는 시테러에게 가끔 파손되고, 파손된 요새는 건설로 수리된다.",
          "40 political power, 2 civilian factories for 45 days, then +1 coastal fort in every coastal province of this state.\n"
          "This lighthouse's damage chance depends on the §Yaverage§! coastal fort level across the state's coastal provinces: "
          "-25% per average level, up to 3 (each province counts at most 3 levels). Sea Terrors sometimes damage coastal forts, "
          "which are repaired through construction."),
    icon="GFX_decision_generic_fortification", ai=2)

# 손상: 90일 미션. 보수를 시작하거나 토벌하면 취소, 시간이 다 되면 등대가 무너진다
C.d(cat_coast, "lh_crumbling", "[FROM.GetName] 등대가 무너진다", "[FROM.GetName] Lighthouse Crumbling", [], cost=None, once=False,
    state_target=True, target=["has_state_flag = TU_IBE_lighthouse"],
    mission={"days": 90,
             "cancel": ["FROM = {\n\tOR = {\n\t\tNOT = { has_state_flag = TU_IBE_lh_damaged }\n\t\thas_state_flag = TU_IBE_lh_repairing\n"
                        "\t\tNOT = { is_owned_and_controlled_by = ROOT }\n\t}\n}"],
             "timeout": ["""FROM = {
	clr_state_flag = TU_IBE_lighthouse
	clr_state_flag = TU_IBE_lh_damaged
	save_event_target_as = tu_ibe_lh_state
}""", V("lighthouses", -1), THR(5), FLAG("lighthouse_fell"), "country_event = { id = tu_ibe_ev.51 }"]},
    desc=("시테러에게 손상된 등대. 보수하거나 수비대로 토벌하지 않으면 시간이 다 됐을 때 무너진다 (등대 -1, 위협 +5).",
          "A lighthouse damaged by Sea Terrors. Unless repaired or cleared by a garrison, it collapses when time runs out (lighthouse -1, threat +5)."),
    icon="GFX_decision_generic_civil_support", ai=0)
C.d(cat_coast, "lh_repair", "[FROM.GetName] 등대 보수", "Repair the [FROM.GetName] Lighthouse",
    ["FROM = { set_state_flag = TU_IBE_lh_repairing }"], cost=25, once=False, state_target=True, days_remove=30,
    modifier={"civilian_factory_use": 2},
    remove_effect=["FROM = {\n\tclr_state_flag = TU_IBE_lh_damaged\n\tclr_state_flag = TU_IBE_lh_repairing\n}"],
    target=["is_owned_and_controlled_by = ROOT", "has_state_flag = TU_IBE_lh_damaged"],     # 손상 깃발은 보수가 끝날 때 지운다
    available=["FROM = { NOT = { has_state_flag = TU_IBE_lh_repairing } }"],
    desc=("손상된 등대를 고친다: 정치력 25, 30일 동안 민간 공장 2개 사용. 보수를 시작하면 붕괴 시간제한이 멈춘다.",
          "Fix the damaged lighthouse: 25 political power, 2 civilian factories for 30 days. Starting repairs stops the collapse timer."),
    icon="GFX_decision_generic_construction", ai=10)
C.d(cat_coast, "lh_purge", "[FROM.GetName] 해안 토벌", "Clear the [FROM.GetName] Coast",
    ["FROM = { clr_state_flag = TU_IBE_lh_damaged }", THR(-3), "army_experience = 2"], cost=10, once=False, state_target=True,
    target=["is_owned_and_controlled_by = ROOT", "has_state_flag = TU_IBE_lh_damaged", "NOT = { has_state_flag = TU_IBE_lh_repairing }"],
    available=["FROM = { TU_IBE_garrison_%dk = yes }" % (LH_PURGE_MP // 1000)],
    desc=("이 주에 병력 3만 이상이 있으면 시테러를 몰아내고 등대를 바로 되찾는다: 위협 -3, 육군 경험치 +2.",
          "With 30,000+ manpower in this state, drive off the Sea Terrors and reclaim the lighthouse at once: threat -3, army experience +2."),
    icon="GFX_decision_generic_military", ai=5)

C.ev(50, ("등대 손상", "Lighthouse Damaged"),
     ("[tu_ibe_lh_state.GetName]의 등대가 시테러의 습격으로 손상되었다. 불빛이 꺼진 해안으로 무언가가 기어오르고 있다.\n\n"
      "90일 안에 보수하거나 수비대로 토벌하지 않으면 등대는 무너진다.",
      "The lighthouse at [tu_ibe_lh_state.GetName] has been damaged by a Sea Terror attack. Something is crawling up the darkened shore.\n\n"
      "Unless it is repaired or cleared by a garrison within 90 days, the lighthouse will collapse."),
     [("보수를 서두르라.", "Hurry the repairs.", [], 1)])
C.ev(51, ("등대 붕괴", "Lighthouse Collapsed"),
     ("[tu_ibe_lh_state.GetName]의 등대가 끝내 무너졌다. 해안 마을 사람들은 다시 밤을 두려워하게 되었다.",
      "The lighthouse at [tu_ibe_lh_state.GetName] has finally collapsed. The coastal villagers fear the night once more."),
     [("다시 세울 것이다.", "We will raise it again.", [], 1)])
C.ev(52, ("해안 수비대 습격", "Coastal Garrison Ambushed"),
     ("[tu_ibe_raid_state.GetName] 해안을 지키던 수비대가 밤사이 시테러의 습격을 받았다. 놈들을 물리쳤지만 피해가 적지 않다.\n\n"
      "그 주에 있던 사단의 조직력이 30%, 내구도가 5% 줄었다.",
      "The garrison guarding the [tu_ibe_raid_state.GetName] coast was ambushed by Sea Terrors in the night. They were driven off, but not without losses.\n\n"
      "Divisions in that state lost 30% organisation and 5% strength."),
     [("전사자들을 기린다.", "Honour the fallen.",
       ["army_experience = 2", THR(-2)], 1)])
C.d(cat_coast, "coastal_patrol", "해안 순찰", "Coastal Patrol", [THR(-10), "army_experience = 5"], cost=25, once=False, days_re_enable=90,
    icon="GFX_decision_generic_naval")
C.d(cat_coast, "purification", "정화 작전", "Purification Operation", [THR(-20), "add_stability = -0.02", INQ("0.05")], cost=75, once=False,
    days_re_enable=240, icon="GFX_decision_generic_operation")
C.d(cat_coast, "evacuate_town", "해안 마을 소개", "Evacuate a Coastal Town", ["add_stability = 0.03", "add_manpower = -2000"], cost=25,
    once=False, days_re_enable=180, available=[AT_LEAST("threat", 50)])
C.d(cat_coast, "hunters_contact", "심해 사냥꾼 수소문", "Seek the Abyssal Hunters", [EV(25)], cost=75, once=True,
    visible=["has_completed_focus = TU_IBE_abyssal_rumours"], available=["NOT = { %s }" % HAS("hunters_met")])
C.d(cat_coast, "sea_research", "심해 연구 지원", "Fund Deep Sea Research",
    ["add_tech_bonus = { name = TU_IBE_sea_research bonus = 0.75 uses = 1 category = electronics }"],
    cost=50, once=False, days_re_enable=240, visible=["has_completed_focus = TU_IBE_sea_studies"])
# 세력 균형 줄다리기 디시전("심판소와 왕관" 분류)은 사양서 37에서 삭제. 심판관 모집은 해안 분류로.
C.d(cat_coast, "inquisitor_recruits", "심판관 모집", "Recruit Inquisitors",
    ["TU_IBE_inq_template = yes",
     "capital_scope = { create_unit = { division = \"division_template = \\\"TU_IBE_inquisitors\\\" start_experience_factor = 0.5 start_equipment_factor = 1\" owner = IBE count = 2 } }"],
    cost=75, once=False, days_re_enable=240, visible=["has_completed_focus = TU_IBE_inquisitor_guard"], icon="GFX_decision_generic_military")
C.effects.append("""TU_IBE_inq_template = {
	if = {
		limit = { NOT = { has_country_flag = TU_IBE_inq_template_done } }
		set_country_flag = TU_IBE_inq_template_done
		division_template = {
			name = "TU_IBE_inquisitors"
			is_locked = no
			priority = 2
			regiments = {
				infantry = { x = 0 y = 0 }
				infantry = { x = 0 y = 1 }
				infantry = { x = 1 y = 0 }
				infantry = { x = 1 y = 1 }
			}
		}
	}
}""")
cat_for = C.category("foreign", "해안 연맹", "Coastal League", icon="GFX_decision_category_generic_foreign_policy", visible=[HAS("league")])
C.d(cat_for, "found_league", "해안 연맹 결성", "Found the Coastal League", ["create_faction = TU_IBE_league"], cost=50, available=["is_in_faction = no"])
C.loc("TU_IBE_league", "해안 연맹", "Coastal League")
C.d(cat_for, "invite_league", "연맹 초청", "Invite to the League", ["add_to_faction = FROM"], cost=50, once=False, days_re_enable=90,
    visible=["is_faction_leader = yes"],
    target=["NOT = { tag = ROOT }", "is_in_faction = no", "NOT = { has_war_with = ROOT }", "OR = { tag = SAR tag = MIN tag = SIR tag = VIC }"])
C.d(cat_for, "share_warnings", "바다의 경고 공유", "Share Warnings of the Sea", ["add_political_power = 40", THR(-5)], cost=25, once=True)

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("침묵한 해안", "The Silent Coast"),
     ("해안 도시의 창문은 모두 닫혀 있다. 심판관들은 오늘도 바다를 등지고 서서 사람들을 지켜본다.",
      "Every window in the coastal towns is shut. The inquisitors stand with their backs to the sea, watching the people."),
     [("바다를 경계하라.", "Watch the sea.", [THR(-5)], 1)], picture="GFX_report_event_generic_ruins")
C.ev(20, ("심해의 침식", "Erosion from the Deep"),
     ("해안 마을 하나가 하룻밤 사이에 텅 비었다. 남은 것은 바다 냄새와 이상한 발자국뿐이다.",
      "A coastal village emptied overnight. All that remains is the smell of the sea and strange footprints."),
     [("심판관을 보낸다.", "Send inquisitors.", ["add_stability = -0.03", INQ("0.05"), THR(-5)], 50),
      ("마을을 봉쇄한다.", "Seal off the village.", ["add_manpower = -3000", "add_stability = -0.02"], 50)],
     trigger=["original_tag = IBE", AT_LEAST("threat", 70)], mtth=60, fire_once=False, picture="GFX_report_event_generic_ruins")
C.ev(21, ("숭배자들의 지하실", "The Cultists' Cellar"),
     ("심판관들이 바다를 숭배하는 비밀 집회 장소를 찾아냈다.", "Inquisitors uncovered a secret meeting place of sea worshippers."),
     [("모두 체포한다.", "Arrest them all.", [INQ("0.05"), "add_stability = 0.02"], 60), ("감시만 한다.", "Only watch them.", [THR(5), "add_political_power = 25"], 40)])
C.ev(22, ("왕실의 후계자", "The Royal Heir"),
     ("오랫동안 숨어 지내던 왕가의 후계자가 모습을 드러냈다.", "The long-hidden heir of the royal house has stepped into the light."),
     [("왕관을 지지한다.", "Support the Crown.", ["add_political_power = 25"], 50), ("심판소의 판단을 따른다.", "Defer to the Inquisition.", ["add_stability = 0.02"], 50)])
C.ev(23, ("바닷가의 이방인", "Strangers by the Sea"),
     ("바닷가에서 이상한 차림의 사냥꾼들을 봤다는 보고가 들어왔다. 그들은 바다의 것들을 사냥한다고 한다.",
      "There are reports of oddly dressed hunters by the shore. They are said to hunt the things from the sea."),
     [("찾아본다.", "Look for them.", [], 1)])
C.ev(25, ("아비살 사냥꾼", "The Abyssal Hunters"),
     ("에기르의 사냥꾼들과 만났다. 그들은 바다에서 올라오는 것들과 싸워 왔다고 했다.",
      "We met the hunters from Aegir. They say they have fought the things rising from the sea for a long time."),
     [("협력한다.", "Cooperate.", [FLAG("hunters_met"), THR(-15)], 70), ("의심한다.", "Distrust them.", [FLAG("hunters_met"), INQ("0.05")], 30)])
C.ev(24, ("라테라노와의 분열", "The Laterano Schism"),
     ("라테라노 교회는 이베리아 심판소의 방식을 오래전부터 비판해 왔다. 라테라노의 사절이 대화를 청했다.",
      "The Laterano church has long criticised Iberia's Inquisition. A Laterano envoy asks for talks."),
     [("대화에 응한다.", "Agree to talk.", [CROWN("0.03"), "add_political_power = 25"], 50), ("거절한다.", "Refuse.", ["add_stability = 0.02"], 50)])
C.ev(26, ("밀려온 표류물", "Washed Ashore"), ("해변에 정체를 알 수 없는 생물의 사체가 밀려왔다.", "The carcass of an unknown creature washed ashore."),
     [("연구한다.", "Study it.", ["add_tech_bonus = { name = TU_IBE_carcass bonus = 0.5 uses = 1 category = electronics }"], 50),
      ("태워 버린다.", "Burn it.", [THR(-5), "add_stability = 0.02"], 50)],
     trigger=["original_tag = IBE", AT_LEAST("threat", 40)], mtth=200)
C.ev(27, ("어부들의 귀환", "The Fishermen Return"), ("위협이 줄자 어부들이 다시 먼바다로 나가기 시작했다.", "With the threat receding, fishermen are sailing out again."),
     [("좋은 징조다.", "A good omen.", ["add_stability = 0.03", "add_political_power = 25"], 1)],
     trigger=["original_tag = IBE", AT_MOST("threat", 25)], mtth=180)
C.ev(28, ("심판관의 나라", "State of the Inquisitors"), ("심판소가 이베리아의 모든 것을 맡았다.", "The Inquisition has taken charge of everything in Iberia."),
     [("경계를 늦추지 않는다.", "Never lower our guard.", [THR(-10)], 1)])
C.ev(29, ("왕관의 부활", "The Crown Restored"), ("대관식이 열렸다. 이베리아에 다시 왕이 섰다.", "A coronation was held. Iberia has a king again."),
     [("국왕 만세!", "Long live the king!", ["add_stability = 0.05"], 1)])
C.ev(30, ("바다와의 화해", "Reconciliation with the Sea"), ("이베리아는 바다를 두려워하는 대신 이해하기로 했다.", "Iberia has chosen to understand the sea rather than fear it."),
     [("바다를 향해.", "Toward the sea.", ["add_stability = 0.05"], 1)])
C.ev(31, ("심판관의 과잉 진압", "Inquisitorial Excess"), ("심판관들이 무고한 어민들을 이단으로 몰았다는 원성이 높다.", "There is outrage that inquisitors branded innocent fishermen heretics."),
     [("심판관을 문책한다.", "Discipline the inquisitors.", [CROWN("0.05"), "add_stability = 0.02"], 50), ("심판은 옳았다.", "The judgement was right.", [INQ("0.05"), "add_stability = -0.03"], 50)],
     trigger=["original_tag = IBE", "has_completed_focus = TU_IBE_faith_laws"], mtth=300)

# 추가 (목표 분량)
for sid, ko, en, pre, econ in (
        ("penitent_brigades", "참회 여단", "Penitent Brigade Regiments", "tribunal_courts", False),
        ("holy_ordnance", "축성 화포", "Holy Ordnance Artillery", "inquisition_navy", False),
        ("abbey_schools", "수도원 학교", "Abbey Schools Education", "relic_vaults", False),
        ("inquisition_spies", "심판소 밀정", "Inquisition Spies Network", "confessors", False),
        ("royal_court_music", "궁정 음악", "Royal Court Music Festival", "crown_propaganda", False),
        ("crown_lands", "왕실 영지 개간", "Crown Lands Farms", "noble_estates", True),
        ("royal_engineers", "왕실 공병", "Royal Engineers Construction", "royal_guard", False),
        ("royal_academy", "왕립 학술원", "Royal Academy of Sciences Research", "royal_reconstruction", False),
        ("watch_towers", "해안 망루", "Coastal Watchtowers", "lighthouse_keepers", False),
        ("tidal_barriers", "조수 방벽", "Tidal Barrier Fortifications", "sea_wall", False),
        ("sonar_research", "수중 음파 연구", "Sonar Research", "sea_samples", False),
        ("deep_charts", "심해 해도", "Deep Sea Charts Survey", "tide_charts", False),
        ("aegir_language", "에기르어 연구", "Aegir Language Studies", "aegir_contact", False),
        ("hunter_training", "사냥꾼 훈련", "Hunter Combat Training", "anti_creature", False),
        ("musket_drill", "사격 훈련", "Marksman Drill Training", "bayonet_drill", False),
        ("mountain_passes", "산길 요새", "Mountain Pass Forts", "mountain_forts", False),
        ("armoured_trains", "장갑 열차", "Armoured Trains", "supply_trains", False),
        ("medium_tanks", "중형 전차", "Medium Tank Units", "light_tanks", False),
        ("air_squadrons", "비행 중대", "Air Squadrons Fighter", "air_watch", False),
        ("naval_bombers", "해상 폭격기", "Naval Bombers", "air_squadrons", False),
        ("cruisers", "순양함 전대", "Cruiser Fleet", "destroyers", False),
        ("naval_bases", "해군 기지", "Naval Base Docks", "dockyards", True),
        ("steel_mills", "제철소", "Steel Mills", "copper_mines", True),
        ("textile_works", "직물 공장", "Textile Works", "cork_forests", True),
        ("olive_presses", "올리브 압착장", "Olive Press Industry", "wine_trade", True),
        ("canneries", "통조림 공장", "Fish Cannery Factories", "fishing_guild", True),
        ("laterano_reunion", "교회 재통합 협상", "Church Reunion Talks", "laterano_schism", False),
        ("columbia_investment", "컬럼비아 투자", "Columbian Investment Fund", "victoria_trade", False),
        ("sargon_caravans", "사르곤 대상 교역", "Sargon Caravan Trade", "sargon_border", False)):
    f(sid, ko, en, pre=[pre], econ=econ)
# (해변 방어 시설·철야 기도는 사양서 31에서 삭제: 위협을 깎는 반복 디시전이 너무 많아 등대 관리가 꺼졌다. 해안 요새 보강이 대신한다)
C.d(cat_coast, "hunter_aid", "사냥꾼 지원", "Aid the Hunters", [THR(-15), "add_political_power = -25"], cost=50, once=False,
    days_re_enable=180, visible=[HAS("hunters_met")])
C.ev(32, ("등대의 불빛", "The Lighthouse Shines"), ("복원된 등대에 불이 들어오자 마을 사람들이 몰려나와 박수를 쳤다.", "When the restored lighthouse was lit, villagers came out and cheered."),
     [("빛이 돌아왔다.", "The light is back.", ["add_stability = 0.03"], 1)],
     trigger=["original_tag = IBE", AT_LEAST("lighthouses", 3)], mtth=120)
C.ev(33, ("심판관 아이린", "Inquisitor Irene"), ("젊은 심판관 아이린이 해안 순찰에서 큰 공을 세웠다.", "The young inquisitor Irene distinguished herself on coastal patrol."),
     [("그녀를 승진시킨다.", "Promote her.", ["army_experience = 15", THR(-5)], 1)],
     trigger=["original_tag = IBE", "has_completed_focus = TU_IBE_inquisitor_academy"], mtth=300)
C.ev(34, ("귀족들의 불만", "Grumbling Nobles"), ("귀족들이 심판소의 간섭에 불만을 터뜨렸다.", "The nobles complain loudly about the Inquisition's meddling."),
     [("귀족 편을 든다.", "Side with the nobles.", [CROWN("0.05"), "add_stability = -0.02"], 50), ("무시한다.", "Ignore them.", ["add_stability = 0.01"], 50)],
     trigger=["original_tag = IBE", "has_completed_focus = TU_IBE_nobles_return"], mtth=300)

# ------------------------------------------------------------------ 리워크 (사양서 27): 해안 방어 · 심판관 군단 · 고원 · 경제 · 외교
f("coastal_ring", "해안 요새선", "Coastal Fortress Ring", pre=["lighthouse_keepers"])
f("anti_seaborn_weapons", "대해사 무기", "Anti-Seaborn Weapons", pre=["lighthouse_keepers"])
f("inquisitor_legions", "심판관 군단", "Holy Legions", pre=["inquisition_reform"])
f("heresy_tribunals", "이단 심문소", "Heresy Tribunals", pre=["inquisitor_legions"], reward=[INQ("0.05")])
f("highland_forts", "고원 요새", "Highland Fortresses", pre=["mountain_infantry"])
f("mountain_scouts", "산악 정찰대", "Mountain Scouts", pre=["mountain_infantry"])
f("salt_works", "염전", "Salt Works", pre=["harbour_rebuild"], econ=True)
f("coastal_rail", "해안 철도", "Coastal Railway", pre=["salt_works"])
f("cannery_plants", "어물 통조림 공장", "Fish Cannery Plants", pre=["salt_works"], econ=True)
f("laterano_accord", "라테라노 협약", "Laterano Accord", pre=["foreign_office"])

# ------------------------------------------------------------------ 아비살 사냥꾼 루트 (사양서 24 개정): 끝에서 스카디가 지도자
C.idea("hunter_rule", "사냥꾼의 이베리아", "Iberia of the Hunters",
       {"army_attack_factor": 0.10, "army_org_factor": 0.10, "war_support_factor": 0.10, "stability_factor": -0.05},
       "generic_army_war_college", ("아비살 사냥꾼이 이베리아를 이끈다. 그들은 바다를 알지만, 바다도 그들을 안다.",
                                    "The Abyssal Hunters lead Iberia. They know the sea, and the sea knows them."))
f("hunter_pact", "사냥꾼과의 맹약", "Pact with the Hunters", pre=["abyssal_rumours"], theme=False, available=[HAS("hunters_met")],
  reward=["add_political_power = 50", THR(-5)],
  desc=("아비살 사냥꾼과 손을 잡는다. (사냥꾼과 만난 뒤)", "Join hands with the Abyssal Hunters. (After meeting the hunters)"))
f("hunter_drill", "사냥꾼의 훈련", "Abyssal Hunter Drill", pre=["hunter_pact"])
f("hunter_blades", "사냥꾼의 대검", "Hunter Greatswords Weapons", pre=["hunter_pact"])
f("hunter_deep_scouting", "심해 정찰", "Deep Sea Scouting", pre=["hunter_drill"])
f("hunter_regiment", "아비살 사냥꾼 연대", "Abyssal Hunter Regiment", pre=["hunter_drill", "hunter_blades"],
  reward=["add_manpower = 10000"])
f("hunter_skadi", "스카디를 앞세우다", "Skadi Leads the Way", pre=["hunter_regiment", "hunter_deep_scouting"], cost=15, theme=False,
  me=["inquisitor_state", "crown_restored", "sea_reconciliation"],
  reward=[FLAG("hunter_rule"), "add_ideas = TU_IBE_hunter_rule", "army_experience = 50"],
  desc=("사냥꾼 스카디가 이베리아의 지도자가 된다. 바다가 그녀를 부르는 소리는 아직 아무도 듣지 못했다.",
        "The hunter Skadi becomes Iberia's leader. No one has yet heard the sea calling her."))

# ------------------------------------------------------------------ 숨은 루트: 이샤믈라 (사양서 24 개정)
# 스카디가 지도자인 상태에서 등대가 모두 무너지면 (한 번이라도 무너진 적이 있고 지금 0) "노랫소리" ->
# "조금은 빠져들어도 되겠지.." -> 15일 뒤 "하나가...되는거야..." -> 지도자 이샤믈라 + 숨은 갈래.
ISHAR = [HAS("ishar_route")]
C.ev(40, ("노랫소리", "A Song"),
     ("마지막 등대의 불빛이 꺼진 밤, 어디선가 노랫소리가 들려와..",
      "On the night the last lighthouse went dark, a song drifts in from somewhere.."),
     [("내 착각인것같다", "It must be my imagination", [], 100),
      ("조금은 빠져들어도 되겠지..", "Surely I can lose myself a little..", [FLAG("ishar_song_heard"), EV(41, 15)], 0)],
     picture="GFX_report_event_generic_read_write",
     trigger=["original_tag = IBE", "has_completed_focus = TU_IBE_hunter_skadi",
              "has_country_leader = { character = TU_IBE_skadi ruling_only = yes }",
              "check_variable = { TU_IBE_lighthouses < 1 }", HAS("lighthouse_fell"), "NOT = { %s }" % HAS("ishar_route")],
     mtth=20)
C.ev(41, ("하나", "One"),
     ("노래가 더 가까워졌다. 스카디의 목소리가 파도와 섞인다.\\n\\n\"하나가...되는거야...\"",
      "The song draws closer. Skadi's voice blends with the waves.\\n\\n\"We will...become one...\""),
     [("파도가 발목을 적신다.", "The tide washes over your feet.",
       [FLAG("ishar_route"), "recruit_character = TU_IBE_ishar_mla",
        "promote_character = {\n\tcharacter = TU_IBE_ishar_mla\n\tideology = despotism\n}",
        "remove_ideas = TU_IBE_hunter_rule",
        "set_variable = { TU_IBE_threat = 0 }", "add_ideas = TU_IBE_seaborn_kin", "mark_focus_tree_layout_dirty = yes"], 1)],
     picture="GFX_report_event_generic_read_write")
C.idea("seaborn_kin", "바다의 혈족", "Kin of the Sea",
       {"army_org_factor": 0.15, "army_attack_factor": 0.10, "army_defence_factor": 0.05, "war_support_factor": 0.10,
        "stability_factor": -0.05}, "generic_morale_bonus",
       ("이샤믈라가 이베리아를 이끈다. 바다는 더 이상 위협이 아니라 고향이다.",
        "Ishar-mla leads Iberia. The sea is no longer a threat but a home."))
C.idea("tide_host", "밀물의 군세", "Host of the Tide",
       {"army_attack_factor": 0.12, "army_defence_factor": 0.08, "attrition": -0.10, "land_reinforce_rate": 0.03},
       "generic_army_war_college")
C.idea("deep_kingdom", "심해 왕국", "Kingdom of the Deep",
       {"army_attack_factor": 0.15, "army_defence_factor": 0.15, "army_org_factor": 0.15, "conscription_factor": 0.10,
        "war_support_factor": 0.20, "attrition": -0.15, "political_power_factor": 0.10},
       "generic_morale_bonus", ("파도 아래에 왕국이 섰다. 이샤믈라의 혈족은 지치지 않는다.",
                                "A kingdom stands beneath the waves. Ishar-mla's kin never tire."))
C.idea("the_deep", "심해", "The Deep",
       {"army_attack_factor": 0.25, "army_defence_factor": 0.25, "army_org_factor": 0.25, "conscription_factor": 0.20,
        "war_support_factor": 0.30, "stability_factor": 0.15, "political_power_factor": 0.20, "attrition": -0.25,
        "production_factory_max_efficiency_factor": 0.15, "industrial_capacity_factory": 0.15, "monthly_population": 0.20},
       "generic_morale_bonus", ("모든 것은 바다에서 왔고, 모든 것은 바다로 돌아간다. 이베리아라는 이름은 이제 파도 아래에 잠들었다.",
                                "All came from the sea, and all returns to it. The name Iberia now sleeps beneath the waves."))
f("ishar_call", "심해의 부름", "Call of the Deep", pre=["root"], cost=5, theme=False, allow_branch=ISHAR, available=ISHAR,
  reward=["add_political_power = 50", "set_variable = { TU_IBE_threat = 0 }"],
  desc=("이샤믈라가 바다 쪽을 가리킨다. 이베리아는 더 이상 바다를 두려워하지 않는다.",
        "Ishar-mla points to the sea. Iberia no longer fears it."))
f("ishar_song", "심해의 노래", "Song of the Deep", pre=["ishar_call"], allow_branch=ISHAR, theme=False,
  reward=["add_war_support = 0.10", "add_political_power = 75"])
f("ishar_hunters", "아비살 사냥꾼의 침묵", "Silence of the Abyssal Hunters", pre=["ishar_call"], allow_branch=ISHAR, theme=False,
  reward=["add_manpower = 15000", "army_experience = 25"],
  desc=("사냥꾼들은 등을 돌리거나, 바다에 녹아든다.", "The hunters either turn away or dissolve into the sea."))
f("ishar_tide", "밀물의 군세", "Host of the Tide", pre=["ishar_song", "ishar_hunters"], allow_branch=ISHAR, theme=False, cost=10,
  reward=["add_ideas = TU_IBE_tide_host", "army_experience = 30"])
f("ishar_inquisition", "심판소 해체", "Dissolve the Inquisition", pre=["ishar_song"], allow_branch=ISHAR, theme=False,
  reward=["add_stability = 0.05", "add_political_power = 50"])
f("ishar_coast", "해안의 동화", "Assimilate the Coast", pre=["ishar_tide"], allow_branch=ISHAR, theme=False,
  reward=["TU_build_infrastructure = yes", "add_manpower = 10000"])
f("ishar_cathedral", "바다에 잠긴 대성당", "The Drowned Cathedral", pre=["ishar_inquisition", "ishar_coast"], allow_branch=ISHAR,
  theme=False, reward=["add_war_support = 0.05", "add_stability = 0.05"])
f("ishar_bloodline", "혈족의 확장", "Spread the Kinship", pre=["ishar_cathedral"], allow_branch=ISHAR, theme=False,
  reward=["add_manpower = 30000", "add_war_support = 0.05"],
  desc=("바닷가 마을들이 하나둘 혈족이 된다.", "One by one the coastal villages become kin."))
f("ishar_coral_cities", "산호의 도시", "Coral Cities", pre=["ishar_cathedral"], allow_branch=ISHAR, theme=False,
  reward=["TU_build_civ_factory = yes", "TU_build_civ_factory = yes", "TU_build_mil_factory = yes"])
f("ishar_abyss_arts", "심연의 아츠", "Arts of the Abyss", pre=["ishar_cathedral"], allow_branch=ISHAR, theme=False,
  reward=["add_tech_bonus = { name = TU_IBE_ishar_abyss_arts bonus = 1.0 uses = 2 category = tu_originium_tech category = infantry_weapons }"])
f("ishar_tidal_legion", "해일 군단", "Tidal Legions", pre=["ishar_bloodline"], allow_branch=ISHAR, theme=False, cost=10,
  reward=["army_experience = 50", "add_manpower = 20000",
          "add_doctrine_cost_reduction = { name = TU_IBE_ishar_tidal_legion cost_reduction = 0.5 uses = 2 category = land_doctrine }"])
f("ishar_drowned_crown", "잠긴 왕관", "The Drowned Crown", pre=["ishar_coral_cities", "ishar_abyss_arts"], allow_branch=ISHAR,
  theme=False, cost=10, reward=["add_political_power = 150", "add_stability = 0.10"],
  desc=("왕관은 바다 밑에서 다시 빛난다. 그것을 쓴 것은 왕이 아니다.", "The crown shines again beneath the sea. It is not a king who wears it."))
f("ishar_deep_kingdom", "심해 왕국 선포", "Proclaim the Kingdom of the Deep", pre=["ishar_tidal_legion", "ishar_drowned_crown"],
  allow_branch=ISHAR, theme=False, cost=15,
  reward=["swap_ideas = { remove_idea = TU_IBE_seaborn_kin add_idea = TU_IBE_deep_kingdom }", "add_war_support = 0.10"])
f("ishar_great_tide", "대해일", "The Great Tide", pre=["ishar_deep_kingdom"], allow_branch=ISHAR, theme=False, cost=10,
  reward=["""every_neighbor_country = {
	limit = { NOT = { is_in_faction_with = ROOT } }
	ROOT = { create_wargoal = { type = annex_everything target = PREV } }
}""", "army_experience = 50"],
  desc=("파도는 국경을 모른다. 이웃 나라 모두에 대한 병합 전쟁 명분을 얻는다.",
        "The tide knows no borders. Gain an annexation war goal against every neighbour."))
f("ishar_song_of_ishar", "이샤의 노래", "Song of Ishar", pre=["ishar_deep_kingdom"], allow_branch=ISHAR, theme=False, cost=10,
  reward=["add_stability = 0.10", "add_war_support = 0.10", "add_political_power = 100"])
f("ishar_finale", "심해", "The Deep", pre=["ishar_great_tide", "ishar_song_of_ishar"], allow_branch=ISHAR, theme=False, cost=20,
  me=["inquisitor_state", "crown_restored", "sea_reconciliation"],
  reward=["swap_ideas = { remove_idea = TU_IBE_deep_kingdom add_idea = TU_IBE_the_deep }", "army_experience = 100",
          "add_political_power = 200"],
  desc=("이베리아라는 이름은 파도 아래에 잠든다. 남은 것은 심해뿐이다. (국호 '심해', 나라 색 어두운 남색)",
        "The name Iberia sleeps beneath the waves. Only the Deep remains. (Name 'The Deep', dark navy colour)"))
for _f in C.focuses:     # 다른 결말과 서로 배타
    if _f["id"] in ("TU_IBE_inquisitor_state", "TU_IBE_crown_restored", "TU_IBE_sea_reconciliation"):
        _f["me"] += ["TU_IBE_ishar_finale", "TU_IBE_hunter_skadi"]

if __name__ == "__main__":
    C.write()
