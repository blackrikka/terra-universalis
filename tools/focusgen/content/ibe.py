#!/usr/bin/env python3
"""이베리아(IBE) 고유 콘텐츠 (사양서 17).

장치
  1. 바다의 위협 TU_IBE_threat (0~100, 시작 40): 매달 +2 (복원한 등대 하나마다 -0.5 덜 오름). 70 이상이면 '심해의 침식'
     이벤트(해안 마을 피해)가 반복된다. 해안 감시·정화 작전 디시전과 중점으로 낮춘다.
  2. 등대 복원 TU_IBE_lighthouses (0~5): 디시전으로 하나씩 복원 (기반시설 + 위협 감소).
  3. 세력 균형 "심판소 대 왕관" (TU_IBE_bop): 왼쪽 = 심판소, 오른쪽 = 왕관. 2단계부터 깃발.
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


def INQ(v):
    return "add_power_balance_value = { id = %s value = -%s }" % (BOP, v)


def CROWN(v):
    return "add_power_balance_value = { id = %s value = %s }" % (BOP, v)


def FLAG(x):
    return "set_country_flag = TU_IBE_%s" % x


def HAS(x):
    return "has_country_flag = TU_IBE_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_ibe_ev.%d%s }" % (n, " days = %d" % days if days else "")


C.set_bop(("inquisition", "심판소", "The Inquisition", "GFX_bop_ETH_centralisation_side"),
          ("crown", "왕관", "The Crown", "GFX_bop_ITA_king_vittorio_side"), -0.3,
          [(0, 0.3, {"stability_factor": 0.03}),
           (0.3, 0.6, {"stability_factor": 0.05, "political_power_gain": -0.05}, "TU_IBE_inquisition_strong"),
           (0.6, 1, {"stability_factor": 0.08, "political_power_gain": -0.1, "consumer_goods_factor": 0.03}, "TU_IBE_inquisition_strong")],
          [(0, 0.3, {"political_power_gain": 0.05}),
           (0.3, 0.6, {"political_power_gain": 0.1, "stability_factor": -0.03}, "TU_IBE_crown_strong"),
           (0.6, 1, {"political_power_gain": 0.15, "war_support_factor": 0.05, "stability_factor": -0.05}, "TU_IBE_crown_strong")])
C.loc(BOP, "심판소 대 왕관", "Inquisition vs Crown")
C.loc(BOP + "_desc", "대침묵 이후 이베리아를 쥔 것은 심판소다. 잊혀 가던 왕관이 다시 목소리를 낸다.",
      "Since the Great Silence the Inquisition has held Iberia. The half-forgotten Crown speaks up again.")
C.history += ["set_variable = { TU_IBE_threat = 40 }", "set_variable = { TU_IBE_lighthouses = 0 }",
              "add_ideas = { TU_IBE_great_silence TU_IBE_fear_of_the_sea }"]
C.effects.append("""TU_IBE_monthly = {
	add_to_variable = { TU_IBE_threat = 2 }
	set_temp_variable = { tu_ibe_lh = TU_IBE_lighthouses }
	multiply_temp_variable = { tu_ibe_lh = -0.5 }
	add_to_variable = { TU_IBE_threat = tu_ibe_lh }
	clamp_variable = { var = TU_IBE_threat min = 0 max = 100 }
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
  me=["crown_restored", "sea_reconciliation"], cost=15, theme=False, available=[HAS("inquisition_strong")],
  reward=[FLAG("path_inq"), "add_ideas = TU_IBE_inquisitor_state", EV(28)],
  desc=("심판소가 이베리아를 영원히 지킨다. (심판소 쪽 세력 균형 2단계 이상)", "The Inquisition guards Iberia forever. (Inquisition stage 2+)"))
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
  cost=15, theme=False, available=[HAS("crown_strong")],
  reward=[FLAG("path_crown"), "add_ideas = TU_IBE_crown_restored", EV(29)],
  desc=("왕이 다시 이베리아를 다스린다. (왕관 쪽 세력 균형 2단계 이상)", "A king rules Iberia again. (Crown stage 2+)"))
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
                       ("바다의 위협은 매달 오르고, 등대 하나마다 덜 오른다. 70 이상이면 해안 마을이 침식된다.",
                        "The sea threat rises every month, less for each lighthouse. At 70+ coastal towns are eroded."),
                       visible=[HAS("coast")])
C.d(cat_coast, "restore_lighthouse", "등대 복원", "Restore a Lighthouse",
    [V("lighthouses", 1), THR(-5), "TU_build_infrastructure = yes"], cost=50, once=False, days_re_enable=120,
    available=[AT_MOST("lighthouses", 4)], desc=("등대 +1 (최대 5), 위협 -5, 기반시설", "Lighthouse +1 (max 5), threat -5, infrastructure"),
    icon="GFX_decision_generic_construction")
C.d(cat_coast, "coastal_patrol", "해안 순찰", "Coastal Patrol", [THR(-10), "army_experience = 5"], cost=25, once=False, days_re_enable=90,
    icon="GFX_decision_generic_naval")
C.d(cat_coast, "purification", "정화 작전", "Purification Operation", [THR(-20), "add_stability = -0.02", INQ("0.05")], cost=75, once=False,
    days_re_enable=240, icon="GFX_decision_generic_operation")
C.d(cat_coast, "evacuate_town", "해안 마을 소개", "Evacuate a Coastal Town", ["add_stability = 0.03", "add_manpower = -2000"], cost=25,
    once=False, days_re_enable=180, available=[AT_LEAST("threat", 50)])
C.d(cat_coast, "hunters_contact", "심해 사냥꾼 수소문", "Seek the Abyssal Hunters", [EV(25)], cost=75, once=True,
    visible=["has_completed_focus = TU_IBE_abyssal_rumours"], available=["NOT = { %s }" % HAS("hunters_met")])
C.d(cat_coast, "sea_research", "심해 연구 지원", "Fund Deep Sea Research",
    ["add_tech_bonus = { name = TU_IBE_sea_research bonus = 0.75 uses = 1 category = electronics }", THR(-5)],
    cost=50, once=False, days_re_enable=240, visible=["has_completed_focus = TU_IBE_sea_studies"])
cat_pol = C.category("politics", "심판소와 왕관", "Inquisition and Crown")
C.d(cat_pol, "inquisition_sermon", "심판소 설교", "Inquisition Sermon", [INQ("0.1"), "add_stability = 0.02"], cost=50, once=False, days_re_enable=120)
C.d(cat_pol, "crown_rally", "왕관 지지 집회", "Rally for the Crown", [CROWN("0.1"), "add_political_power = 25"], cost=50, once=False, days_re_enable=120)
C.d(cat_pol, "heresy_trial", "이단 재판", "Heresy Trial", [INQ("0.05"), "add_stability = 0.04", "add_political_power = -15"], cost=25, once=False,
    days_re_enable=180)
C.d(cat_pol, "royal_tour", "왕실 순행", "Royal Tour", [CROWN("0.05"), "add_war_support = 0.03"], cost=25, once=False, days_re_enable=180,
    visible=["has_completed_focus = TU_IBE_royal_heir"])
C.d(cat_pol, "noble_taxes", "귀족 과세", "Tax the Nobles", ["add_political_power = 75", CROWN("-0.05")], cost=0, once=False, days_re_enable=240)
C.d(cat_pol, "inquisitor_recruits", "심판관 모집", "Recruit Inquisitors",
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
C.d(cat_for, "share_warnings", "바다의 경고 공유", "Share Warnings of the Sea", ["add_political_power = 40", THR(-5)], cost=25, once=False, days_re_enable=180)

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
     [("왕관을 지지한다.", "Support the Crown.", [CROWN("0.1")], 50), ("심판소의 판단을 따른다.", "Defer to the Inquisition.", [INQ("0.05")], 50)])
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
     [("대화에 응한다.", "Agree to talk.", [CROWN("0.03"), "add_political_power = 25"], 50), ("거절한다.", "Refuse.", [INQ("0.05")], 50)])
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
     trigger=["original_tag = IBE", HAS("inquisition_strong")], mtth=300)

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
C.d(cat_coast, "fortify_beach", "해변 방어 시설", "Fortify the Beaches", ["TU_build_infrastructure = yes", THR(-5)], cost=75, once=False,
    days_re_enable=240, icon="GFX_decision_generic_fortification")
C.d(cat_coast, "sea_vigil", "바다를 향한 철야 기도", "Vigil Toward the Sea", ["add_stability = 0.03", THR(-3)], cost=25, once=False, days_re_enable=120)
C.d(cat_coast, "hunter_aid", "사냥꾼 지원", "Aid the Hunters", [THR(-15), "add_political_power = -25"], cost=50, once=False,
    days_re_enable=180, visible=[HAS("hunters_met")])
C.d(cat_pol, "crown_marriage", "왕실 혼사", "Royal Marriage", [CROWN("0.1"), "add_stability = 0.02"], cost=75, once=True,
    visible=["has_completed_focus = TU_IBE_royal_heir"])
C.d(cat_pol, "inquisition_audit", "심판소 감사", "Audit the Inquisition", [CROWN("0.08"), "add_political_power = 40"], cost=50, once=False,
    days_re_enable=240)
C.ev(32, ("등대의 불빛", "The Lighthouse Shines"), ("복원된 등대에 불이 들어오자 마을 사람들이 몰려나와 박수를 쳤다.", "When the restored lighthouse was lit, villagers came out and cheered."),
     [("빛이 돌아왔다.", "The light is back.", ["add_stability = 0.03"], 1)],
     trigger=["original_tag = IBE", AT_LEAST("lighthouses", 3)], mtth=120)
C.ev(33, ("심판관 아이린", "Inquisitor Irene"), ("젊은 심판관 아이린이 해안 순찰에서 큰 공을 세웠다.", "The young inquisitor Irene distinguished herself on coastal patrol."),
     [("그녀를 승진시킨다.", "Promote her.", ["army_experience = 15", THR(-5)], 1)],
     trigger=["original_tag = IBE", "has_completed_focus = TU_IBE_inquisitor_academy"], mtth=300)
C.ev(34, ("귀족들의 불만", "Grumbling Nobles"), ("귀족들이 심판소의 간섭에 불만을 터뜨렸다.", "The nobles complain loudly about the Inquisition's meddling."),
     [("귀족 편을 든다.", "Side with the nobles.", [CROWN("0.05"), "add_stability = -0.02"], 50), ("무시한다.", "Ignore them.", [INQ("0.03")], 50)],
     trigger=["original_tag = IBE", "has_completed_focus = TU_IBE_nobles_return"], mtth=300)

if __name__ == "__main__":
    C.write()
