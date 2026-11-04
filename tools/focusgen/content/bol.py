#!/usr/bin/env python3
"""볼리바르(BOL) 고유 콘텐츠 (사양서 17).

장치
  1. 정부 장악력 TU_BOL_control (0~100, 시작 35): 끝나지 않는 내전에서 정부가 실제로 다스리는 정도.
     '공세' 디시전(60일) → 결과 이벤트(성공 +15 / 교착 +5 / 실패 -10). 100이 되면 내전 종식 이벤트.
  2. 전쟁 피로 TU_BOL_weariness (0~100, 시작 40): 내전이 끝나기 전까지 매달 +1 (on_monthly). 70 이상이면 탈영·시위 이벤트(반복).
     휴전 협상·구호 디시전으로 내린다.
  3. 외세 의존 TU_BOL_columbia / TU_BOL_victoria (0~100): 원조를 받을수록 오르고, 60 이상이면 후원국의 요구 이벤트.
정치 결말 셋 (서로 배타): 볼리바르 공화국(내전 종식 + 두 의존 40 이하) / 컬럼비아 보호국(컬럼비아 의존 70) / 빅토리아 보호국(빅토리아 의존 70).

실행: python -I tools/focusgen/content/bol.py && python -I tools/focusgen/merge_focus.py --tag BOL
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_lib import Country  # noqa: E402

C = Country("BOL", "볼리바르", "Bolivar")
f = C.f
MAXV = {"control": 100, "weariness": 100, "columbia": 100, "victoria": 100}
NAMES = {"control": ("§G정부 장악력§!", "§GGovernment Control§!"), "weariness": ("§R전쟁 피로§!", "§RWar Weariness§!"),
         "columbia": ("§Y컬럼비아 의존§!", "§YColumbian Dependence§!"), "victoria": ("§Y빅토리아 의존§!", "§YVictorian Dependence§!")}


def V(var, n):
    name = "TU_BOL_%s_%s%d" % (var, "m" if n < 0 else "", abs(n))
    if not any(e.startswith(name + " =") for e in C.effects):
        C.effects.append("""%s = {
	custom_effect_tooltip = %s_tt
	hidden_effect = {
		add_to_variable = { TU_BOL_%s = %d }
		clamp_variable = { var = TU_BOL_%s min = 0 max = %d }
	}
}""" % (name, name, var, n, var, MAXV[var]))
        ko, en = NAMES[var]
        C.loc(name + "_tt", "%s %s%d" % (ko, "+" if n > 0 else "", n), "%s %s%d" % (en, "+" if n > 0 else "", n))
    return "%s = yes" % name


def CTL(n):
    return V("control", n)


def WEA(n):
    return V("weariness", n)


def AT_LEAST(var, n):
    return "check_variable = { TU_BOL_%s > %d }" % (var, n - 1)


def AT_MOST(var, n):
    return "check_variable = { TU_BOL_%s < %d }" % (var, n + 1)


def FLAG(x):
    return "set_country_flag = TU_BOL_%s" % x


def HAS(x):
    return "has_country_flag = TU_BOL_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_bol_ev.%d%s }" % (n, " days = %d" % days if days else "")


C.history += ["set_variable = { TU_BOL_control = 35 }", "set_variable = { TU_BOL_weariness = 40 }",
              "set_variable = { TU_BOL_columbia = 20 }", "set_variable = { TU_BOL_victoria = 20 }",
              "add_ideas = { TU_BOL_endless_war TU_BOL_divided_land }"]
C.effects.append("""TU_BOL_monthly = {
	if = {
		limit = { NOT = { has_country_flag = TU_BOL_war_over } }
		add_to_variable = { TU_BOL_weariness = 1 }
	}
	if = {
		limit = { has_country_flag = TU_BOL_war_over }
		add_to_variable = { TU_BOL_weariness = -2 }
	}
	clamp_variable = { var = TU_BOL_weariness min = 0 max = 100 }
	if = {
		limit = {
			check_variable = { TU_BOL_control > 99 }
			NOT = { has_country_flag = TU_BOL_war_over }
		}
		set_country_flag = TU_BOL_war_over
		country_event = { id = tu_bol_ev.25 }
	}
}""")
C.on_actions.append("""on_monthly = {
	effect = {
		if = {
			limit = { original_tag = BOL }
			TU_BOL_monthly = yes
		}
	}
}""")

# ------------------------------------------------------------------ 국민정신
for sid, ko, en, mods, pic, desc in (
        ("endless_war", "끝나지 않는 내전", "The Endless Civil War", {"stability_factor": -0.1, "war_support_factor": 0.05, "production_speed_buildings_factor": -0.1},
         "generic_army_problems", ("수십 년째 이어지는 내전. 정부가 다스리는 곳보다 다스리지 못하는 곳이 더 많다.",
                                   "A civil war decades long. The government controls less than it does not.")),
        ("divided_land", "갈라진 땅", "A Divided Land", {"political_power_gain": -0.1}, "generic_local_self_management",
         ("마을마다 걸린 깃발이 다르다.", "Every village flies a different flag.")),
        ("peace_dividend", "평화의 배당", "The Peace Dividend", {"stability_factor": 0.1, "production_speed_buildings_factor": 0.1, "monthly_population": 0.1}, "generic_pp_unity_bonus", ("", "")),
        ("bolivar_republic", "볼리바르 공화국", "Bolivar Republic", {"stability_factor": 0.1, "political_power_gain": 0.15, "war_support_factor": 0.05}, "constitutional_guarantees", ("", "")),
        ("columbian_protectorate", "컬럼비아 보호국", "Columbian Protectorate", {"production_factory_max_efficiency_factor": 0.1, "research_speed_factor": 0.05, "political_power_gain": -0.05},
         "generic_foreign_capital", ("", "")),
        ("victorian_protectorate", "빅토리아 보호국", "Victorian Protectorate", {"army_org_factor": 0.05, "production_speed_buildings_factor": 0.1, "political_power_gain": -0.05},
         "generic_foreign_capital", ("", "")),
        ("guerrilla_masters", "게릴라의 대가", "Masters of Guerrilla War", {"army_defence_factor": 0.08, "attrition": -0.1}, "generic_guerilla_warfare", ("", "")),
        ("veteran_army", "역전의 군대", "Veteran Army", {"army_org_factor": 0.05, "experience_gain_army_factor": 0.1}, "generic_army_war_college", ("", ""))):
    C.idea(sid, ko, en, mods, pic, desc)

# ------------------------------------------------------------------ 중점
f("root", "끝나지 않는 내전", "The Endless Civil War", cost=5, theme=False, reward=["add_political_power = 50", EV(1)],
  desc=("볼리바르는 내전 속에서 태어나 내전 속에서 자랐다. 이 전쟁을 끝낼 수 있을까?",
        "Bolivar was born in civil war and grew up in it. Can this war be ended?"))

# A. 내전
f("war_council", "전쟁 회의", "War Council", pre=["root"], theme=False, reward=[FLAG("campaign"), CTL(5)],
  desc=("'내전' 디시전이 열린다 (공세, 휴전, 구호).", "Unlocks the Civil War decisions (offensives, ceasefires, relief)."))
f("militia_levy", "민병대 소집", "Militia Levy", pre=["war_council"])
f("guerrilla_doctrine", "게릴라전 교리", "Guerrilla Doctrine", pre=["war_council"])
f("jungle_forts", "정글 요새", "Jungle Fortifications", pre=["guerrilla_doctrine"])
f("foreign_mercs", "외국 용병", "Foreign Mercenaries", pre=["militia_levy"], me=["national_army"], reward=[V("columbia", 5), V("victoria", 5)])
f("national_army", "국민군", "National Army", pre=["militia_levy"], me=["foreign_mercs"], reward=[CTL(5)])
f("arms_smuggling", "무기 밀수", "Arms Smuggling", pre=[["foreign_mercs", "national_army"]])
f("guerrilla_masters", "게릴라의 대가", "Masters of Guerrilla War", pre=["jungle_forts", "arms_smuggling"], theme=False,
  reward=["add_ideas = TU_BOL_guerrilla_masters", CTL(10)])
f("final_offensive", "최후의 공세", "The Final Offensive", pre=["guerrilla_masters"], theme=False, available=[AT_LEAST("control", 70)],
  reward=[CTL(20), "army_experience = 50", WEA(10)], desc=("내전을 끝낼 마지막 공세. (장악력 70 이상)", "The last offensive to end the war. (Control 70+)"))
f("veteran_army", "역전의 군대", "Veteran Army", pre=["final_offensive"], theme=False, reward=["add_ideas = TU_BOL_veteran_army"])

# B. 평화
f("ceasefire_talks", "휴전 협상", "Ceasefire Talks", pre=["root"], theme=False, reward=[WEA(-10)])
f("warlord_unity", "군벌 통합", "Unite the Warlords", pre=["ceasefire_talks"], reward=[CTL(10)])
f("reconciliation", "국민 화해", "National Reconciliation", pre=["ceasefire_talks"], reward=[WEA(-10)])
f("amnesty", "사면령", "General Amnesty", pre=["reconciliation"], reward=[CTL(5)])
f("new_government", "새 정부", "New Government", pre=["warlord_unity", "amnesty"], theme=False, reward=["remove_ideas = TU_BOL_divided_land", CTL(10)])
f("bolivar_republic", "볼리바르 공화국", "Bolivar Republic", pre=["new_government"], me=["columbian_protectorate", "victorian_protectorate"],
  cost=15, theme=False, available=[HAS("war_over"), AT_MOST("columbia", 40), AT_MOST("victoria", 40)],
  reward=[FLAG("path_republic"), "add_ideas = TU_BOL_bolivar_republic", EV(28)],
  desc=("누구의 꼭두각시도 아닌 볼리바르. (내전 종식, 두 나라 의존 40 이하)", "A Bolivar that is no one's puppet. (War over, both dependences 40 or less)"))
f("constitution", "볼리바르 헌법", "Bolivar Constitution Charter", pre=["bolivar_republic"])
f("national_elections", "첫 총선거", "First National Elections", pre=["bolivar_republic"])

# C. 외세
f("foreign_patrons", "외세의 후원", "Foreign Patrons", pre=["root"], theme=False, reward=[FLAG("patrons")],
  desc=("'외세' 디시전이 열린다 (컬럼비아·빅토리아 원조).", "Unlocks the Foreign Patron decisions (Columbian and Victorian aid)."))
f("columbian_alliance", "컬럼비아와의 동맹", "Columbian Alliance", pre=["foreign_patrons"], me=["victorian_alliance"], reward=[V("columbia", 15)])
f("victorian_alliance", "빅토리아와의 동맹", "Victorian Alliance", pre=["foreign_patrons"], me=["columbian_alliance"], reward=[V("victoria", 15)])
f("columbian_protectorate", "컬럼비아 보호국", "Columbian Protectorate", pre=["columbian_alliance"], me=["bolivar_republic", "victorian_protectorate"],
  cost=15, theme=False, available=[AT_LEAST("columbia", 70)],
  reward=[FLAG("path_columbia"), "add_ideas = TU_BOL_columbian_protectorate", CTL(30), EV(29)],
  desc=("컬럼비아의 보호 아래 내전을 끝낸다. (컬럼비아 의존 70 이상)", "End the war under Columbian protection. (Columbian dependence 70+)"))
f("victorian_protectorate", "빅토리아 보호국", "Victorian Protectorate", pre=["victorian_alliance"], me=["bolivar_republic", "columbian_protectorate"],
  cost=15, theme=False, available=[AT_LEAST("victoria", 70)],
  reward=[FLAG("path_victoria"), "add_ideas = TU_BOL_victorian_protectorate", CTL(30), EV(30)],
  desc=("빅토리아의 보호 아래 내전을 끝낸다. (빅토리아 의존 70 이상)", "End the war under Victorian protection. (Victorian dependence 70+)"))
f("columbian_factories", "컬럼비아 공장", "Columbian Factories", pre=["columbian_protectorate"], econ=True)
f("victorian_garrisons", "빅토리아 수비대", "Victorian Garrison Regiments", pre=["victorian_protectorate"])

# D. 재건
f("refugee_relief", "난민 구호", "Refugee Relief", pre=["root"], reward=[WEA(-5)])
f("hospital_rebuild", "병원 재건", "Hospital Rebuild", pre=["refugee_relief"])
f("grain_rationing", "식량 배급", "Grain Rationing", pre=["refugee_relief"], reward=[WEA(-5)])
f("education_reform", "교육 재건", "Education Reform", pre=["hospital_rebuild"], me=["housing_rebuild"])
f("housing_rebuild", "주택 재건", "Housing Rebuild", pre=["hospital_rebuild"], me=["education_reform"])
f("war_orphans", "전쟁 고아 쉼터", "War Orphan Shelters", pre=[["education_reform", "housing_rebuild"], "grain_rationing"], reward=[WEA(-5)])
f("peace_dividend", "평화의 배당", "The Peace Dividend", pre=["war_orphans"], theme=False, available=[HAS("war_over")],
  reward=["add_ideas = TU_BOL_peace_dividend"], desc=("내전이 끝나야 한다.", "The war must be over."))

# E. 경제
f("coffee_farms", "커피 농장", "Coffee Farms", pre=["root"], econ=True)
f("road_network", "도로망 건설", "Road Network", pre=["coffee_farms"], econ="TU_build_infrastructure = yes")
f("industrial_district", "공업 지구", "Industrial District", pre=["coffee_farms"], econ=True)
f("civ_program", "민간 공장 계획", "Civilian Factory Program", pre=["industrial_district"], me=["arms_program"], econ=True)
f("arms_program", "군수 공장 계획", "Arms Factory Program", pre=["industrial_district"], me=["civ_program"], econ="TU_build_mil_factory = yes")
f("foreign_investment", "외국 투자 기금", "Foreign Investment Fund", pre=["road_network"])
f("reconstruction", "볼리바르 재건", "Bolivar Reconstruction", pre=[["civ_program", "arms_program"], "foreign_investment"], econ=True)
f("research_slot", "볼리바르 대학", "University of Bolivar Research", pre=["reconstruction"], theme=False, reward=["add_research_slot = 1"],
  desc=("연구 슬롯 +1", "Research slot +1"))

# 보강
for sid, ko, en, pre, econ in (
        ("signal_corps", "통신대", "Signal Corps", "war_council", False), ("jungle_scouts", "정글 정찰대", "Jungle Scouts", "guerrilla_doctrine", False),
        ("booby_traps", "부비트랩", "Booby Trap Tactics", "jungle_forts", False), ("river_patrols", "강 순찰선", "River Patrol Boats", "jungle_forts", False),
        ("merc_contracts", "용병 계약", "Mercenary Contracts", "foreign_mercs", False), ("conscription", "징병제", "Conscription Law", "national_army", False),
        ("captured_arms", "노획 무기", "Captured Weapons Arsenal", "arms_smuggling", False), ("mortar_teams", "박격포조", "Mortar Teams Artillery", "arms_smuggling", False),
        ("cavalry_raiders", "기병 습격대", "Cavalry Raiders", "guerrilla_masters", False), ("trucks", "트럭 부대", "Truck Columns Motorised", "final_offensive", False),
        ("air_support", "공중 지원", "Air Support Wing", "final_offensive", False), ("field_hospitals", "야전 병원", "Field Hospitals", "militia_levy", False),
        ("peace_envoys", "평화 사절", "Peace Envoys", "ceasefire_talks", False), ("truth_commission", "진실 위원회", "Truth Commission", "reconciliation", False),
        ("disarmament", "무장 해제", "Disarmament Programme", "amnesty", False), ("veterans_land", "제대 군인 농지", "Veterans' Farms", "amnesty", True),
        ("free_press", "자유 언론", "Free Press Broadcast", "new_government", False), ("courts_rebuild", "법원 재건", "Courts Rebuild Reform", "new_government", False),
        ("national_guard", "국가 경비대", "National Guard Regiments", "constitution", False), ("columbian_advisors", "컬럼비아 고문단", "Columbian Military Advisors", "columbian_alliance", False),
        ("victorian_advisors", "빅토리아 고문단", "Victorian Military Advisors", "victorian_alliance", False), ("columbian_loans", "컬럼비아 차관", "Columbian Loans", "columbian_alliance", False),
        ("victorian_loans", "빅토리아 차관", "Victorian Loans", "victorian_alliance", False), ("foreign_press", "외신 기자", "Foreign Press Corps", "foreign_patrons", False),
        ("clinics", "진료소", "Rural Clinics Medical", "hospital_rebuild", False), ("teachers", "교사 양성", "Teacher Training Schools", "education_reform", False),
        ("new_towns", "새 마을", "New Towns Housing", "housing_rebuild", True), ("food_aid", "식량 원조", "Food Aid Relief", "grain_rationing", False),
        ("orphan_schools", "고아 학교", "Orphan Schools", "war_orphans", False), ("banana_plantations", "바나나 농장", "Banana Plantation Farms", "coffee_farms", True),
        ("rail_network", "철도 연결", "Rail Network Expansion", "road_network", "TU_build_infrastructure = yes"), ("oil_wells", "유정", "Oil Wells", "industrial_district", True),
        ("rubber", "고무 농장", "Rubber Plantation Industry", "banana_plantations", True), ("steel_works", "제철소", "Steel Works", "oil_wells", True),
        ("river_ports", "강 항구", "River Ports Harbour", "rail_network", "TU_build_civ_factory = yes"), ("power_plants", "발전소", "Power Plants", "rail_network", True),
        ("sargon_ties", "사르곤 교역", "Sargon Trade Accord", "foreign_patrons", False), ("minos_ties", "미노스 교류", "Minos Exchange", "foreign_patrons", False),
        ("kazimierz_mercs", "카시미어 용병", "Kazimierz Mercenary Contracts", "merc_contracts", False), ("rhodes_doctors", "로도스 의사", "Rhodes Island Doctors Relief", "refugee_relief", False),
        ("coffee_exports", "커피 수출", "Coffee Export Trade", "coffee_farms", False), ("smuggler_routes", "밀수로 장악", "Smuggler Route Control", "arms_smuggling", False),
        ("radio_station", "라디오 방송국", "Radio Station Broadcast", "signal_corps", False), ("jungle_airstrips", "정글 비행장", "Jungle Airstrips", "air_support", False),
        ("demining", "지뢰 제거", "Demining Engineers", "disarmament", False), ("national_memory", "전쟁 기념관", "War Memorial Propaganda", "truth_commission", False),
        ("tax_reform", "조세 개혁", "Tax Reform Treasury", "courts_rebuild", False)):
    f(sid, ko, en, pre=[pre], econ=econ)

# ------------------------------------------------------------------ 디시전
cat_w = C.category("war", "내전", "The Civil War",
                   ("정부 장악력 100이 되면 내전이 끝난다. 내전 중에는 전쟁 피로가 매달 오른다.",
                    "The war ends when government control reaches 100. War weariness rises every month until then."),
                   visible=[HAS("campaign")])
for sid, ko, en, cost, extra in (("offensive", "공세", "Launch an Offensive", 50, ["add_manpower = -3000"]),
                                 ("big_offensive", "대공세", "Launch a Major Offensive", 100, ["add_manpower = -8000"])):
    C.d(cat_w, sid, ko, en, extra + [FLAG(sid + "_on")], cost=cost, once=False, days_remove=60, days_re_enable=30,
        available=["NOT = { %s }" % HAS("offensive_on"), "NOT = { %s }" % HAS("big_offensive_on"), "NOT = { %s }" % HAS("war_over")],
        remove_effect=["clr_country_flag = TU_BOL_%s_on" % sid, FLAG("big" if sid == "big_offensive" else "small"), EV(20)],
        desc=("60일 뒤 결과가 나온다. 대공세는 성공 폭이 크다.", "Results after 60 days. A major offensive gains more on success."),
        icon="GFX_decision_generic_military")
C.d(cat_w, "local_ceasefire", "지역 휴전", "Local Ceasefire", [WEA(-10), "add_political_power = -25"], cost=25, once=False, days_re_enable=120,
    available=["NOT = { %s }" % HAS("war_over")])
C.d(cat_w, "relief_convoy", "구호 행렬", "Relief Convoy", [WEA(-8), "add_stability = 0.02"], cost=50, once=False, days_re_enable=120,
    icon="GFX_decision_generic_civil_support")
C.d(cat_w, "win_hearts", "민심 얻기", "Win Hearts and Minds", [CTL(5), "add_political_power = -15"], cost=50, once=False, days_re_enable=120)
C.d(cat_w, "warlord_bribe", "군벌 매수", "Bribe a Warlord", [CTL(10), "add_political_power = -50"], cost=0, once=False, days_re_enable=240,
    available=["NOT = { %s }" % HAS("war_over")])
C.d(cat_w, "propaganda", "선전 방송", "Propaganda Broadcast", [WEA(-5), "add_war_support = 0.03"], cost=25, once=False, days_re_enable=120)

cat_p = C.category("patrons", "외세", "Foreign Patrons", icon="GFX_decision_category_generic_foreign_policy",
                   desc=("원조를 받을수록 그 나라에 기대게 된다. 의존이 60을 넘으면 후원국이 요구를 한다.",
                         "The more aid you take, the more you lean on that patron. Above 60 dependence, the patron makes demands."),
                   visible=[HAS("patrons")])
for k, ko, en, tag in (("columbia", "컬럼비아", "Columbian", "COL"), ("victoria", "빅토리아", "Victorian", "VIC")):
    C.d(cat_p, "%s_arms" % k, "%s 무기 원조" % ko, "%s Arms Aid" % en,
        ["add_equipment_to_stockpile = { type = infantry_equipment amount = 800 producer = %s }" % tag, V(k, 10)], cost=25, once=False,
        days_re_enable=120, desc=("소총 800정, %s 의존 +10" % ko, "800 rifles, %s dependence +10" % en), icon="GFX_decision_generic_military")
    C.d(cat_p, "%s_money" % k, "%s 자금 원조" % ko, "%s Financial Aid" % en, ["add_political_power = 75", V(k, 10)], cost=0, once=False,
        days_re_enable=120, icon="GFX_decision_generic_fundraising")
    C.d(cat_p, "%s_factory" % k, "%s 공장 투자" % ko, "%s Factory Investment" % en, ["TU_build_civ_factory = yes", V(k, 15)], cost=25, once=False,
        days_re_enable=240, icon="GFX_decision_generic_factory")
C.d(cat_p, "reduce_dependence", "자주 노선", "Self-Reliance", [V("columbia", -10), V("victoria", -10), "add_political_power = -50"], cost=25, once=False,
    days_re_enable=180)
C.d(cat_p, "play_patrons", "두 후원국 저울질", "Play the Patrons Against Each Other", ["add_political_power = 60", "add_stability = -0.02"], cost=0, once=False,
    days_re_enable=240, available=[AT_LEAST("columbia", 30), AT_LEAST("victoria", 30)])

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("내전의 나라", "A Nation at War with Itself"),
     ("수도 밖으로 반나절만 가면 다른 깃발이 걸린 마을이 나온다. 컬럼비아와 빅토리아의 무기가 양쪽에 다 흘러든다.",
      "Half a day out of the capital, villages fly other flags. Columbian and Victorian guns flow to both sides."),
     [("전쟁을 끝낸다.", "We will end this war.", [CTL(5)], 50), ("백성부터 살린다.", "First, the people must live.", [WEA(-5)], 50)])
C.ev(20, ("공세의 결과", "Result of the Offensive"),
     ("공세에 나섰던 부대들이 보고서를 보내왔다.", "The units sent on the offensive have reported back."),
     [("전선을 밀어냈다!", "We pushed the front!", ["trigger = { %s }" % HAS("res_win"), CTL(15), "if = { limit = { %s } %s }" % (HAS("big"), CTL(10)),
                                                  "army_experience = 15", "clr_country_flag = TU_BOL_res_win"], 1),
      ("교착 상태다.", "A stalemate.", ["trigger = { %s }" % HAS("res_stall"), CTL(5), WEA(3), "clr_country_flag = TU_BOL_res_stall"], 1),
      ("공세가 실패했다.", "The offensive failed.", ["trigger = { %s }" % HAS("res_fail"), CTL(-10), WEA(5), "add_manpower = -3000", "clr_country_flag = TU_BOL_res_fail"], 1)],
     immediate=["random_list = {", "\t45 = { modifier = { factor = 1.3 has_completed_focus = TU_BOL_guerrilla_masters } %s }" % FLAG("res_win"),
                "\t30 = { %s }" % FLAG("res_stall"), "\t25 = { %s }" % FLAG("res_fail"), "}", "clr_country_flag = TU_BOL_big",
                "clr_country_flag = TU_BOL_small"], picture="GFX_report_event_generic_battle")
C.ev(21, ("탈영", "Desertion"), ("전쟁에 지친 병사들이 무리 지어 탈영했다.", "War-weary soldiers have deserted in groups."),
     [("탈영병을 쫓는다.", "Hunt the deserters.", ["add_stability = -0.02", "army_experience = 5"], 50), ("사면한다.", "Pardon them.", [WEA(-5), "add_manpower = -3000"], 50)],
     trigger=["original_tag = BOL", AT_LEAST("weariness", 70)], mtth=90, fire_once=False, picture="GFX_report_event_generic_riot")
C.ev(22, ("반전 시위", "Anti-War Protest"), ("수도에서 '전쟁을 끝내라'는 시위가 일어났다.", "Protesters in the capital demand an end to the war."),
     [("협상을 약속한다.", "Promise talks.", [WEA(-10), "add_political_power = -30"], 60), ("해산시킨다.", "Disperse them.", ["add_stability = -0.04"], 40)],
     trigger=["original_tag = BOL", AT_LEAST("weariness", 80)], mtth=120, fire_once=False, picture="GFX_report_event_generic_riot")
C.ev(23, ("컬럼비아의 요구", "Columbia's Demands"), ("컬럼비아가 원조의 대가로 광산 채굴권을 요구한다.", "Columbia demands mining rights in return for its aid."),
     [("받아들인다.", "Accept.", [V("columbia", 10), "add_political_power = 25"], 50), ("거절한다.", "Refuse.", [V("columbia", -10), "add_stability = -0.02"], 50)],
     trigger=["original_tag = BOL", AT_LEAST("columbia", 60)], mtth=180, fire_once=False)
C.ev(24, ("빅토리아의 요구", "Victoria's Demands"), ("빅토리아가 원조의 대가로 항구 사용권을 요구한다.", "Victoria demands harbour rights in return for its aid."),
     [("받아들인다.", "Accept.", [V("victoria", 10), "add_political_power = 25"], 50), ("거절한다.", "Refuse.", [V("victoria", -10), "add_stability = -0.02"], 50)],
     trigger=["original_tag = BOL", AT_LEAST("victoria", 60)], mtth=180, fire_once=False)
C.ev(25, ("내전 종식", "The Civil War Ends"), ("마지막 반군 지도자가 무기를 내려놓았다. 볼리바르에 처음으로 평화가 왔다.",
                                                 "The last rebel leader has laid down arms. For the first time, peace has come to Bolivar."),
     [("평화다!", "Peace!", ["remove_ideas = TU_BOL_endless_war", "add_stability = 0.1", WEA(-20)], 1)], picture="GFX_report_event_generic_sign_treaty1")
C.ev(26, ("반군의 협상 제의", "Rebels Offer Talks"), ("반군 지도자 하나가 비밀리에 협상을 제의했다.", "A rebel leader secretly offers to negotiate."),
     [("응한다.", "Accept.", [CTL(10), "add_political_power = -25"], 60), ("함정이다.", "It is a trap.", ["army_experience = 10"], 40)],
     trigger=["original_tag = BOL", AT_LEAST("control", 50), "NOT = { %s }" % HAS("war_over")], mtth=200)
C.ev(27, ("마을의 학살", "Massacre in a Village"), ("한 마을에서 학살이 일어났다. 누구의 짓인지 서로 비난한다.", "A village was massacred. Each side blames the other."),
     [("진상을 조사한다.", "Investigate.", ["add_political_power = -20", WEA(-3)], 50), ("반군의 짓이라 발표한다.", "Blame the rebels.", ["add_war_support = 0.05", WEA(5)], 50)],
     trigger=["original_tag = BOL", "NOT = { %s }" % HAS("war_over")], mtth=300)
C.ev(28, ("볼리바르 공화국", "Bolivar Republic"), ("볼리바르는 스스로 일어섰다.", "Bolivar stands on its own."), [("자유 볼리바르!", "Free Bolivar!", ["add_stability = 0.05"], 1)])
C.ev(29, ("컬럼비아 보호국", "Columbian Protectorate"), ("컬럼비아 군이 반군을 몰아내고 평화를 지킨다.", "Columbian troops drove out the rebels and keep the peace."),
     [("감사하다.", "Grateful.", ["if = { limit = { country_exists = COL } COL = { puppet = BOL } }"], 1)])
C.ev(30, ("빅토리아 보호국", "Victorian Protectorate"), ("빅토리아 군이 반군을 몰아내고 평화를 지킨다.", "Victorian troops drove out the rebels and keep the peace."),
     [("감사하다.", "Grateful.", ["if = { limit = { country_exists = VIC } VIC = { puppet = BOL } }"], 1)])
C.ev(31, ("밀림의 영웅", "Hero of the Jungle"), ("한 게릴라 대장이 전설적인 전과를 올렸다.", "A guerrilla captain has achieved legendary feats."),
     [("훈장을 준다.", "Award a medal.", ["army_experience = 20", "add_war_support = 0.03"], 1)],
     trigger=["original_tag = BOL", "has_completed_focus = TU_BOL_guerrilla_doctrine"], mtth=300)

for sid, ko, en, pre, econ in (
        ("night_raids", "야간 기습", "Night Raid Tactics", "jungle_scouts", False), ("ambush_school", "매복 학교", "Ambush Tactics School", "booby_traps", False),
        ("river_fleet", "강 함대", "River Fleet", "river_patrols", False), ("merc_officers", "용병 장교", "Mercenary Officer Training", "merc_contracts", False),
        ("draft_boards", "징병 위원회", "Draft Board Mobilisation", "conscription", False), ("rifle_factory", "소총 공장", "Rifle Factory", "captured_arms", "TU_build_mil_factory = yes"),
        ("light_artillery", "경포병", "Light Artillery", "mortar_teams", False), ("armoured_trucks", "장갑 트럭", "Armoured Truck Units", "trucks", False),
        ("bomber_wing", "폭격 비행대", "Bomber Wing", "air_support", False), ("victory_parade", "승전 행진", "Victory Parade Propaganda", "veteran_army", False),
        ("peace_conference", "평화 회의", "Peace Conference Talks", "peace_envoys", False), ("land_reform", "토지 개혁", "Land Reform Farms", "veterans_land", True),
        ("rebel_integration", "반군 편입", "Rebel Integration Regiments", "disarmament", False), ("public_works", "공공 사업", "Public Works Construction", "national_guard", True),
        ("columbian_schools", "컬럼비아 학교", "Columbian Schools Education", "columbian_factories", False), ("victorian_railways", "빅토리아 철도", "Victorian Railways", "victorian_garrisons", "TU_build_infrastructure = yes"),
        ("aid_warehouses", "원조 창고", "Aid Warehouse Supply", "foreign_press", False), ("vaccination", "예방 접종", "Vaccination Campaign Health", "clinics", False),
        ("literacy", "문맹 퇴치", "Literacy Campaign Education", "teachers", False), ("market_towns", "장터 마을", "Market Towns Trade", "new_towns", False),
        ("school_meals", "학교 급식", "School Meals Relief", "food_aid", False), ("cocoa_trade", "카카오 교역", "Cocoa Trade", "banana_plantations", False),
        ("refinery", "정유소", "Oil Refinery", "oil_wells", True), ("cement_plant", "시멘트 공장", "Cement Plant Construction", "steel_works", True),
        ("hydro_dam", "수력 댐", "Hydro Dam Power", "power_plants", True), ("textiles", "직물 공장", "Textile Mills", "rubber", True),
        ("mining_towns", "광산 마을", "Mining Towns", "oil_wells", True), ("rhodes_clinics", "로도스 진료소", "Rhodes Island Clinics Medical", "rhodes_doctors", False),
        ("iberia_ties", "이베리아 교류", "Iberia Exchange", "minos_ties", False), ("laterano_mediation", "라테라노 중재", "Laterano Mediation Talks", "peace_envoys", False),
        ("national_anthem", "새 국가", "New National Anthem Propaganda", "national_elections", False), ("national_bank", "중앙은행", "National Bank", "tax_reform", False)):
    f(sid, ko, en, pre=[pre], econ=econ)
C.d(cat_w, "jungle_sweep", "정글 소탕", "Jungle Sweep", [CTL(5), "army_experience = 10", "add_manpower = -2000"], cost=50, once=False, days_re_enable=120,
    available=["NOT = { %s }" % HAS("war_over")], visible=["has_completed_focus = TU_BOL_jungle_scouts"], icon="GFX_decision_generic_military")
C.d(cat_w, "rebel_defectors", "반군 귀순 권유", "Encourage Rebel Defections", [CTL(5), WEA(-3)], cost=50, once=False, days_re_enable=180,
    available=["NOT = { %s }" % HAS("war_over")])
C.d(cat_w, "veterans_pension", "제대 군인 연금", "Veterans' Pensions", [WEA(-10), "add_political_power = -30"], cost=0, once=False, days_re_enable=240)
C.d(cat_w, "victory_bonds", "승리 채권", "Victory Bonds", ["add_political_power = 60", WEA(3)], cost=0, once=False, days_re_enable=240)
C.d(cat_p, "foreign_journalists", "외신 초청", "Invite Foreign Journalists", ["add_stability = 0.02", V("columbia", -3), V("victoria", -3)], cost=25, once=False,
    days_re_enable=180)
C.ev(32, ("반군의 분열", "Rebels Split"), ("반군 지도부가 둘로 갈라졌다.", "The rebel leadership has split in two."),
     [("한쪽과 손잡는다.", "Deal with one side.", [CTL(10)], 1)], trigger=["original_tag = BOL", AT_LEAST("control", 40), "NOT = { %s }" % HAS("war_over")], mtth=300)
C.ev(33, ("국경의 피난민", "Refugees at the Border"), ("내전을 피해 이웃 나라로 떠나는 행렬이 끝없다.", "An endless column flees the civil war to neighbouring lands."),
     [("붙잡는다.", "Hold them back.", ["add_stability = -0.02"], 50), ("보내 준다.", "Let them go.", ["add_manpower = -3000", WEA(-3)], 50)],
     trigger=["original_tag = BOL", AT_LEAST("weariness", 60)], mtth=200)
C.ev(34, ("첫 수확", "The First Harvest"), ("평화가 온 뒤 첫 수확이 풍성하다.", "The first harvest after peace is plentiful."),
     [("축제를 연다.", "Hold a festival.", ["add_stability = 0.04"], 1)], trigger=["original_tag = BOL", HAS("war_over")], mtth=200)

if __name__ == "__main__":
    C.write()
