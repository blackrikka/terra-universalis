#!/usr/bin/env python3
"""림 빌리튼(RIM) 고유 콘텐츠 (사양서 17).

장치
  1. 원석 갱도 TU_RIM_shafts (0~8, 시작 2) / 광석 TU_RIM_ore (0~500): 갱도를 열면 매달 갱도당 광석 +5 (on_monthly).
     광석은 '광석 판매'(정치력)·'광석 정제'(공장)·'원석 공학'(연구)에 쓴다.
  2. 광석병 감염률 TU_RIM_infection (0~100, 시작 30): 매달 갱도당 +1, 진료소가 있으면 -2, 격리 구역 -1.
     60 이상이면 '광산 파업'·'집단 감염' 이벤트(반복). 억제제·진료소·격리 디시전으로 낮춘다.
  3. 정착촌 TU_RIM_settlements (0~5): 피난민 정착촌 디시전 (인력·안정).
정치 결말 셋 (서로 배타): 회사 통치(갱도 6) / 노동자 자치(감염 30 이하 + 노조) / 감염자의 안식처(정착촌 4).

실행: python -I tools/focusgen/content/rim.py && python -I tools/focusgen/merge_focus.py --tag RIM
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_lib import Country  # noqa: E402

C = Country("RIM", "림 빌리튼", "Rim Billiton")
f = C.f
MAXV = {"shafts": 8, "ore": 500, "infection": 100, "settlements": 5}
NAMES = {"shafts": ("§Y원석 갱도§!", "§YMine Shafts§!"), "ore": ("§G광석§!", "§GOre§!"),
         "infection": ("§R광석병 감염률§!", "§ROripathy Rate§!"), "settlements": ("§Y정착촌§!", "§YSettlements§!")}


def V(var, n):
    name = "TU_RIM_%s_%s%d" % (var, "m" if n < 0 else "", abs(n))
    if not any(e.startswith(name + " =") for e in C.effects):
        C.effects.append("""%s = {
	custom_effect_tooltip = %s_tt
	hidden_effect = {
		add_to_variable = { TU_RIM_%s = %d }
		clamp_variable = { var = TU_RIM_%s min = 0 max = %d }
	}
}""" % (name, name, var, n, var, MAXV[var]))
        ko, en = NAMES[var]
        C.loc(name + "_tt", "%s %s%d" % (ko, "+" if n > 0 else "", n), "%s %s%d" % (en, "+" if n > 0 else "", n))
    return "%s = yes" % name


def INF(n):
    return V("infection", n)


def ORE(n):
    return V("ore", n)


def AT_LEAST(var, n):
    return "check_variable = { TU_RIM_%s > %d }" % (var, n - 1)


def AT_MOST(var, n):
    return "check_variable = { TU_RIM_%s < %d }" % (var, n + 1)


def FLAG(x):
    return "set_country_flag = TU_RIM_%s" % x


def HAS(x):
    return "has_country_flag = TU_RIM_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_rim_ev.%d%s }" % (n, " days = %d" % days if days else "")


C.history += ["set_variable = { TU_RIM_shafts = 2 }", "set_variable = { TU_RIM_ore = 20 }", "set_variable = { TU_RIM_infection = 30 }",
              "set_variable = { TU_RIM_settlements = 0 }", "add_ideas = { TU_RIM_company_town TU_RIM_oripathy_spread }"]
C.effects.append("""TU_RIM_monthly = {
	set_temp_variable = { tu_rim_t = TU_RIM_shafts }
	multiply_temp_variable = { tu_rim_t = 5 }
	add_to_variable = { TU_RIM_ore = tu_rim_t }
	add_to_variable = { TU_RIM_infection = TU_RIM_shafts }
	if = { limit = { has_country_flag = TU_RIM_clinics } add_to_variable = { TU_RIM_infection = -2 } }
	if = { limit = { has_country_flag = TU_RIM_quarantine } add_to_variable = { TU_RIM_infection = -1 } }
	clamp_variable = { var = TU_RIM_ore min = 0 max = 500 }
	clamp_variable = { var = TU_RIM_infection min = 0 max = 100 }
}""")
C.on_actions.append("""on_monthly = {
	effect = {
		if = {
			limit = { original_tag = RIM }
			TU_RIM_monthly = yes
		}
	}
}""")

# ------------------------------------------------------------------ 국민정신
for sid, ko, en, mods, pic, desc in (
        ("company_town", "회사의 도시", "Company Towns", {"production_speed_buildings_factor": 0.05, "stability_factor": -0.05}, "generic_foreign_capital",
         ("광산 회사가 도시와 학교와 병원을 소유한다.", "The mining companies own the towns, the schools and the hospitals.")),
        ("oripathy_spread", "번지는 광석병", "Spreading Oripathy", {"monthly_population": -0.1, "stability_factor": -0.03}, "generic_army_problems",
         ("갱도가 깊어질수록 감염자가 늘어난다.", "The deeper the shafts, the more the infected.")),
        ("mining_superpower", "광산 대국", "Mining Superpower", {"production_factory_max_efficiency_factor": 0.08, "industrial_capacity_factory": 0.05}, "generic_production_bonus", ("", "")),
        ("corporate_rule", "회사 통치", "Corporate Rule", {"production_speed_buildings_factor": 0.15, "political_power_gain": 0.1, "stability_factor": -0.05}, "generic_foreign_capital", ("", "")),
        ("workers_rule", "노동자 자치", "Workers' Self-Government", {"stability_factor": 0.1, "conscription_factor": 0.05, "production_factory_max_efficiency_factor": 0.05}, "generic_local_self_management", ("", "")),
        ("infected_haven", "감염자의 안식처", "Haven for the Infected", {"monthly_population": 0.2, "stability_factor": 0.08, "conscription_factor": 0.1}, "generic_pp_unity_bonus", ("", "")),
        ("defence_force", "림 빌리튼 방위군", "Rim Billiton Defence Force", {"army_defence_factor": 0.08, "army_org_factor": 0.03}, "generic_fortify_the_borders", ("", "")),
        ("suppressant_supply", "억제제 보급", "Suppressant Supply", {"monthly_population": 0.1, "stability_factor": 0.03}, "generic_morale_bonus", ("", ""))):
    C.idea(sid, ko, en, mods, pic, desc)

# ------------------------------------------------------------------ 중점
f("root", "원석 광산 국가", "The Mining Nation", cost=5, theme=False, reward=["add_political_power = 50", EV(1)],
  desc=("림 빌리튼은 원석 위에 세워진 나라다. 광산은 부를 주지만, 광석병도 함께 준다.",
        "Rim Billiton is built on originium. The mines bring wealth, and oripathy with it."))

# A. 광산
f("ore_mining", "광석 채굴", "Ore Mining", pre=["root"], theme=False, reward=[FLAG("mines"), ORE(20)],
  desc=("'광산' 디시전이 열린다 (갱도 개착, 광석 판매·정제).", "Unlocks the Mine decisions (open shafts, sell or refine ore)."))
f("ore_refinery", "원석 정제소", "Ore Refinery", pre=["ore_mining"], econ=True)
f("mining_railway", "광산 철도", "Mining Railway", pre=["ore_mining"], econ="TU_build_infrastructure = yes")
f("automated_mines", "자동화 광산", "Automated Mines", pre=["ore_refinery", "mining_railway"], me=["labour_expansion"], theme=False,
  reward=[INF(-10), "add_tech_bonus = { name = TU_RIM_automated bonus = 0.75 uses = 1 category = industry }"])
f("labour_expansion", "노동 확대", "Labour Expansion", pre=["ore_refinery", "mining_railway"], me=["automated_mines"], theme=False,
  reward=[V("shafts", 1), INF(5), "add_manpower = 5000"])
f("ore_exports", "광석 수출", "Ore Exports", pre=[["automated_mines", "labour_expansion"]], theme=False, reward=[ORE(30), "add_political_power = 50"])
f("mining_superpower", "광산 대국", "Mining Superpower", pre=["ore_exports"], theme=False, reward=["add_ideas = TU_RIM_mining_superpower"])

# B. 회사
f("company_board", "회사 이사회", "Company Board", pre=["root"])
f("corporate_charter", "회사 헌장", "Corporate Charter", pre=["company_board"])
f("company_security", "회사 경비대", "Company Security Force", pre=["company_board"])
f("corporate_police", "기업 경찰", "Corporate Police", pre=["corporate_charter"])
f("corporate_rule", "회사 통치", "Corporate Rule", pre=["corporate_police", "company_security"], me=["workers_rule", "infected_haven"], cost=15, theme=False,
  available=[AT_LEAST("shafts", 6)], reward=[FLAG("path_company"), "swap_ideas = { remove_idea = TU_RIM_company_town add_idea = TU_RIM_corporate_rule }", EV(28)],
  desc=("나라가 곧 회사다. (갱도 6 이상)", "The nation is the company. (6+ shafts)"))
f("shareholder_army", "주주 군대", "Shareholder Army Regiments", pre=["corporate_rule"])
f("ore_monopoly", "광석 독점", "Ore Monopoly Trade", pre=["corporate_rule"], reward=[ORE(50)])

# C. 노동자
f("miners_union", "광부 조합", "Miners' Union", pre=["root"], theme=False, reward=[FLAG("union"), EV(20)])
f("safety_rules", "광산 안전 규정", "Mine Safety Rules", pre=["miners_union"], theme=False, reward=[INF(-10)])
f("workers_council", "노동자 평의회", "Workers' Council", pre=["miners_union"])
f("eight_hour_day", "8시간 노동", "Eight-Hour Day Reform", pre=["safety_rules"])
f("workers_rule", "노동자 자치", "Workers' Self-Government", pre=["eight_hour_day", "workers_council"], me=["corporate_rule", "infected_haven"], cost=15,
  theme=False, available=[AT_MOST("infection", 30), HAS("union")],
  reward=[FLAG("path_workers"), "swap_ideas = { remove_idea = TU_RIM_company_town add_idea = TU_RIM_workers_rule }", EV(29)],
  desc=("광부들이 광산을 다스린다. (감염률 30 이하)", "The miners run the mines. (Oripathy rate 30 or less)"))
f("cooperatives", "광산 협동조합", "Mining Cooperatives", pre=["workers_rule"], econ=True)
f("workers_militia", "노동자 민병대", "Workers' Militia", pre=["workers_rule"])

# D. 광석병
f("oripathy_research", "광석병 연구", "Oripathy Research", pre=["root"])
f("medical_centres", "의료 센터", "Medical Centres", pre=["oripathy_research"], theme=False, reward=[FLAG("clinics"), INF(-5)],
  desc=("감염률이 매달 2씩 덜 오른다.", "The oripathy rate rises 2 less every month."))
f("suppressant_production", "억제제 생산", "Suppressant Production", pre=["medical_centres"], me=["quarantine_zones"], theme=False,
  reward=["swap_ideas = { remove_idea = TU_RIM_oripathy_spread add_idea = TU_RIM_suppressant_supply }", FLAG("suppressants")])
f("quarantine_zones", "격리 구역", "Quarantine Zones", pre=["medical_centres"], me=["suppressant_production"], theme=False,
  reward=["remove_ideas = TU_RIM_oripathy_spread", FLAG("quarantine"), "add_stability = -0.02"])
f("rhodes_partnership", "로도스 아일랜드 협력", "Rhodes Island Medical Partnership", pre=[["suppressant_production", "quarantine_zones"]], theme=False,
  reward=[INF(-15), "add_political_power = 25"])

# E. 정착촌
f("refugee_policy", "이주민 정책", "Refugee Policy", pre=["root"], theme=False, reward=[FLAG("settle")],
  desc=("'정착촌' 디시전이 열린다.", "Unlocks the Settlement decisions."))
f("infected_rights", "감염자 권리", "Infected Rights", pre=["refugee_policy"])
f("settlers_council", "정착민 의회", "Settlers' Council", pre=["refugee_policy"])
f("new_homeland", "새로운 터전", "New Homeland Relief", pre=["infected_rights", "settlers_council"])
f("infected_haven", "감염자의 안식처", "Haven for the Infected", pre=["new_homeland"], me=["corporate_rule", "workers_rule"], cost=15, theme=False,
  available=[AT_LEAST("settlements", 4)], reward=[FLAG("path_haven"), "swap_ideas = { remove_idea = TU_RIM_company_town add_idea = TU_RIM_infected_haven }", EV(30)],
  desc=("세상 모든 감염자가 올 수 있는 곳. (정착촌 4 이상)", "A place where all the infected of the world may come. (4+ settlements)"))
f("haven_schools", "안식처 학교", "Haven Schools Education", pre=["infected_haven"])
f("haven_guard", "안식처 수비대", "Haven Guard Regiments", pre=["infected_haven"])

# F. 방위
f("mine_defence", "광산 방어선", "Mine Defence Line", pre=["root"])
f("mercenary_hire", "용병 고용", "Mercenary Hire", pre=["mine_defence"])
f("rapid_squads", "기동 경비대", "Rapid Security Squads", pre=["mercenary_hire"], me=["fortified_mines"])
f("fortified_mines", "요새화된 광산", "Fortified Mines", pre=["mercenary_hire"], me=["rapid_squads"])
f("equipment_supply", "장비 보급", "Equipment Supply", pre=[["rapid_squads", "fortified_mines"]])
f("defence_force", "림 빌리튼 방위군", "Rim Billiton Defence Force", pre=["equipment_supply"], theme=False,
  reward=["add_ideas = TU_RIM_defence_force", "army_experience = 30"])

# G. 경제
f("industrial_district", "공업 지구", "Industrial District", pre=["root"], econ=True)
f("road_network", "도로망 건설", "Road Network", pre=["industrial_district"], econ="TU_build_infrastructure = yes")
f("civ_program", "민간 공장 계획", "Civilian Factory Program", pre=["industrial_district"], me=["arms_program"], econ=True)
f("arms_program", "군수 공장 계획", "Arms Factory Program", pre=["industrial_district"], me=["civ_program"], econ="TU_build_mil_factory = yes")
f("originium_engineering", "원석 공학", "Originium Engineering", pre=["road_network"])
f("research_slot", "원석 연구원", "Originium Research Institute", pre=["originium_engineering"], theme=False, reward=["add_research_slot = 1"],
  desc=("연구 슬롯 +1", "Research slot +1"))
f("industrialisation", "림 빌리튼 산업화", "Rim Billiton Industrialisation", pre=[["civ_program", "arms_program"], "road_network"], econ=True)

# 보강
for sid, ko, en, pre, econ in (
        ("deep_shafts", "심층 갱도", "Deep Shaft Mining", "ore_refinery", True), ("ore_trains", "광석 열차", "Ore Train Railway", "mining_railway", True),
        ("mine_lights", "갱도 조명", "Mine Lighting Engineering", "automated_mines", False), ("dynamite", "발파 공정", "Blasting Engineering", "labour_expansion", False),
        ("ore_markets", "광석 거래소", "Ore Exchange Market", "ore_exports", False), ("geology_survey", "지질 조사", "Geology Survey", "ore_mining", False),
        ("company_stores", "회사 상점", "Company Store Trade", "corporate_charter", False), ("company_doctors", "회사 의사", "Company Doctors Medical", "company_security", False),
        ("private_army", "사병 확충", "Private Army Regiments", "corporate_police", False), ("ore_futures", "광석 선물", "Ore Futures Trade", "ore_monopoly", False),
        ("strike_fund", "파업 기금", "Strike Fund", "workers_council", False), ("workers_schools", "노동자 학교", "Workers' Schools Education", "eight_hour_day", False),
        ("workers_clinics", "노동자 진료소", "Workers' Clinics Medical", "safety_rules", False), ("union_press", "노조 신문", "Union Press Propaganda", "workers_council", False),
        ("infection_survey", "감염 조사", "Infection Survey Research", "oripathy_research", False), ("protective_gear", "방호 장비", "Protective Gear Equipment", "medical_centres", False),
        ("clean_water", "정수 시설", "Clean Water Works", "medical_centres", True), ("hospital_trains", "병원 열차", "Hospital Train Medical", "rhodes_partnership", False),
        ("settler_farms", "정착민 농장", "Settler Farms", "settlers_council", True), ("refugee_camps", "난민 캠프", "Refugee Camps Relief", "infected_rights", False),
        ("settler_militia", "정착민 민병대", "Settler Militia", "new_homeland", False), ("haven_hospitals", "안식처 병원", "Haven Hospitals", "haven_schools", False),
        ("border_scouts", "국경 정찰대", "Border Scouts", "mine_defence", False), ("anti_raider", "약탈자 소탕", "Anti-Raider Tactics", "mercenary_hire", False),
        ("armoured_trains", "장갑 열차", "Armoured Trains", "rapid_squads", False), ("mine_bunkers", "광산 벙커", "Mine Bunker Fortifications", "fortified_mines", False),
        ("rifle_imports", "소총 수입", "Rifle Weapons Imports", "equipment_supply", False), ("artillery_crews", "포병대", "Artillery Crews", "equipment_supply", False),
        ("steel_works", "제철소", "Steel Works", "industrial_district", True), ("chemical_plants", "화학 공장", "Chemical Plants", "steel_works", True),
        ("power_plants", "발전소", "Power Plants", "road_network", True), ("rail_network", "철도 연결", "Rail Network Expansion", "road_network", "TU_build_infrastructure = yes"),
        ("siracusa_corridor", "시라쿠사 통로", "Siracusa Corridor Road", "road_network", False), ("rhodes_office", "로도스 사무소", "Rhodes Island Office Pact", "oripathy_research", False),
        ("columbia_investors", "컬럼비아 투자", "Columbian Investment Fund", "company_board", False), ("victoria_buyers", "빅토리아 구매자", "Victoria Ore Trade", "ore_exports", False),
        ("yan_trade", "염국 교역", "Yan Trade Accord", "company_board", False), ("kazdel_refugees", "카즈델 피난민", "Kazdel Refugee Shelters", "refugee_policy", False),
        ("originium_arts", "원석 아츠", "Originium Arts Research", "originium_engineering", False), ("mobile_mines", "이동 광산", "Mobile Mine City Refit", "deep_shafts", False),
        ("ore_power", "원석 발전", "Originium Power Plants", "power_plants", True), ("workers_bank", "노동자 은행", "Workers' Bank", "cooperatives", False),
        ("haven_charter", "안식처 헌장", "Haven Charter", "haven_guard", False), ("company_navy", "회사 함대", "Company Fleet", "corporate_charter", False),
        ("mine_rescue", "광산 구조대", "Mine Rescue Teams", "safety_rules", False), ("suppressant_exports", "억제제 수출", "Suppressant Export Trade", "suppressant_production", False),
        ("quarantine_guards", "격리 경비대", "Quarantine Guard Regiments", "quarantine_zones", False)):
    f(sid, ko, en, pre=[pre], econ=econ)

# ------------------------------------------------------------------ 디시전
cat_m = C.category("mines", "원석 광산", "Originium Mines",
                   ("갱도마다 매달 광석 +5, 감염률 +1.", "Each shaft gives +5 ore and +1 oripathy rate every month."), visible=[HAS("mines")])
C.d(cat_m, "open_shaft", "갱도 개착", "Open a Shaft", [V("shafts", 1)], cost=50, once=False, days_re_enable=90, available=[AT_MOST("shafts", 7)],
    desc=("갱도 +1 (최대 8)", "Shafts +1 (max 8)"), icon="GFX_decision_generic_construction")
C.d(cat_m, "close_shaft", "갱도 폐쇄", "Close a Shaft", [V("shafts", -1), INF(-5)], cost=10, once=False, days_re_enable=60, available=[AT_LEAST("shafts", 1)])
C.d(cat_m, "sell_ore", "광석 판매", "Sell Ore", [ORE(-50), "add_political_power = 75"], cost=0, once=False, days_re_enable=60, available=[AT_LEAST("ore", 50)],
    desc=("광석 50 → 정치력 75", "Ore 50 → 75 political power"), icon="GFX_decision_generic_fundraising")
C.d(cat_m, "refine_ore", "광석 정제", "Refine Ore", [ORE(-100), "TU_build_civ_factory = yes"], cost=25, once=False, days_re_enable=120,
    available=[AT_LEAST("ore", 100)], desc=("광석 100 → 민간 공장", "Ore 100 → a civilian factory"), icon="GFX_decision_generic_factory")
C.d(cat_m, "ore_arms", "광석 군수 계약", "Ore Arms Contract", [ORE(-100), "TU_build_mil_factory = yes"], cost=25, once=False, days_re_enable=120,
    available=[AT_LEAST("ore", 100)], desc=("광석 100 → 군수 공장", "Ore 100 → a military factory"), icon="GFX_decision_generic_factory")
C.d(cat_m, "ore_research", "원석 공학 연구", "Originium Engineering Research",
    [ORE(-60), "add_tech_bonus = { name = TU_RIM_ore_research bonus = 1.0 uses = 1 category = industry category = electronics }"], cost=25, once=False,
    days_re_enable=180, available=[AT_LEAST("ore", 60)])

cat_h = C.category("health", "광석병", "Oripathy",
                   ("감염률이 60을 넘으면 파업과 집단 감염이 일어난다.", "Above 60 oripathy rate, strikes and outbreaks occur."))
C.d(cat_h, "distribute_suppressants", "억제제 배급", "Distribute Suppressants", [INF(-10), ORE(-20)], cost=25, once=False, days_re_enable=90,
    available=[AT_LEAST("ore", 20)], icon="GFX_decision_generic_civil_support")
C.d(cat_h, "mobile_clinics", "이동 진료소", "Mobile Clinics", [INF(-8), "add_stability = 0.02"], cost=50, once=False, days_re_enable=120,
    visible=["has_completed_focus = TU_RIM_oripathy_research"], icon="GFX_decision_generic_civil_support")
C.d(cat_h, "quarantine_sweep", "격리 단속", "Quarantine Sweep", [INF(-15), "add_stability = -0.03"], cost=25, once=False, days_re_enable=180)
C.d(cat_h, "rhodes_doctors", "로도스 의사 초빙", "Invite Rhodes Island Doctors", [INF(-12), "add_political_power = -20"], cost=25, once=False,
    days_re_enable=180, visible=["has_completed_focus = TU_RIM_rhodes_office"])
C.d(cat_h, "worker_bonus", "광부 상여금", "Miners' Bonus", ["add_stability = 0.04", ORE(-30)], cost=0, once=False, days_re_enable=120,
    available=[AT_LEAST("ore", 30)])

cat_s = C.category("settle", "정착촌", "Settlements", visible=[HAS("settle")])
C.d(cat_s, "build_settlement", "정착촌 건설", "Build a Settlement", [V("settlements", 1), "add_manpower = 8000", "TU_build_infrastructure = yes"], cost=75,
    once=False, days_re_enable=180, available=[AT_MOST("settlements", 4)], desc=("정착촌 +1 (최대 5), 인력 +8,000", "Settlements +1 (max 5), +8,000 manpower"),
    icon="GFX_decision_generic_construction")
C.d(cat_s, "welcome_refugees", "피난민 수용", "Welcome Refugees", ["add_manpower = 5000", INF(3), "add_stability = -0.02"], cost=25, once=False, days_re_enable=120)
C.d(cat_s, "settler_aid", "정착민 지원", "Aid the Settlers", ["add_stability = 0.04"], cost=50, once=False, days_re_enable=180, available=[AT_LEAST("settlements", 1)])
C.d(cat_s, "hire_guards", "광산 경비 고용", "Hire Mine Guards", ["add_manpower = 6000", "army_experience = 10"], cost=50, once=False, days_re_enable=180,
    visible=["has_completed_focus = TU_RIM_mercenary_hire"], icon="GFX_decision_generic_military")

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("원석의 땅", "Land of Originium"),
     ("갱도 입구에서 교대하는 광부들이 기침을 한다. 회사 깃발 아래 광석 열차가 쉬지 않고 달린다.",
      "Miners changing shifts at the shaft cough. Under the company flag, ore trains never stop."),
     [("더 깊이 판다.", "Dig deeper.", [V("shafts", 1)], 50), ("광부부터 돌본다.", "Care for the miners first.", [INF(-5)], 50)])
C.ev(20, ("광부 조합 결성", "The Miners Unionise"),
     ("광부들이 조합을 만들고 회사에 요구서를 냈다.", "The miners have formed a union and submitted demands to the companies."),
     [("요구를 받아들인다.", "Accept the demands.", [INF(-5), "add_political_power = -25"], 50), ("회사 편을 든다.", "Side with the companies.", ["add_stability = -0.03", ORE(20)], 50)])
C.ev(21, ("광산 파업", "Mine Strike"), ("감염된 광부들이 갱도에서 나오기를 거부한다.", "Infected miners refuse to come out of the shafts."),
     [("요구를 들어준다.", "Meet their demands.", [INF(-10), ORE(-30)], 50), ("경비대를 보낸다.", "Send the guards.", ["add_stability = -0.05", "army_experience = 5"], 50)],
     trigger=["original_tag = RIM", AT_LEAST("infection", 60)], mtth=90, fire_once=False, picture="GFX_report_event_generic_strike")
C.ev(22, ("집단 감염", "Mass Outbreak"), ("한 광산 마을에서 광석병이 한꺼번에 번졌다.", "Oripathy has broken out all at once in a mining town."),
     [("마을을 봉쇄한다.", "Seal the town.", ["add_manpower = -5000", INF(-5)], 50), ("의료진을 보낸다.", "Send medical teams.", ["add_political_power = -40", INF(-10)], 50)],
     trigger=["original_tag = RIM", AT_LEAST("infection", 75)], mtth=120, fire_once=False, picture="GFX_report_event_generic_riot")
C.ev(23, ("새 광맥", "A New Vein"), ("지질 조사단이 엄청난 원석 광맥을 찾았다.", "Geologists have found an enormous originium vein."),
     [("즉시 판다.", "Mine it now.", [ORE(80), INF(5)], 1)], trigger=["original_tag = RIM", "has_completed_focus = TU_RIM_geology_survey"], mtth=300)
C.ev(24, ("갱도 붕괴", "Shaft Collapse"), ("갱도 하나가 무너져 광부들이 갇혔다.", "A shaft collapsed, trapping miners."),
     [("구조에 나선다.", "Mount a rescue.", ["add_political_power = -30", "add_stability = 0.02"], 60), ("갱도를 버린다.", "Abandon the shaft.", [V("shafts", -1), "add_stability = -0.03"], 40)],
     trigger=["original_tag = RIM", AT_LEAST("shafts", 4)], mtth=240)
C.ev(25, ("피난민 행렬", "A Column of Refugees"), ("감염자 피난민들이 국경에 몰려왔다.", "Infected refugees crowd the border."),
     [("받아들인다.", "Take them in.", ["add_manpower = 6000", INF(3)], 50), ("돌려보낸다.", "Turn them back.", ["add_stability = 0.02"], 50)],
     trigger=["original_tag = RIM", HAS("settle")], mtth=200)
C.ev(26, ("약탈자 습격", "Raider Attack"), ("황야의 약탈자들이 광석 열차를 습격했다.", "Wasteland raiders attacked an ore train."),
     [("추격한다.", "Pursue them.", ["army_experience = 10"], 50), ("손실을 감수한다.", "Accept the loss.", [ORE(-30)], 50)],
     trigger=["original_tag = RIM", AT_LEAST("ore", 50)], mtth=240)
C.ev(27, ("치료 연구의 진전", "Progress in Treatment"), ("광석병 연구에서 감염 속도를 늦추는 방법을 찾았다.", "Oripathy research has found a way to slow infection."),
     [("널리 보급한다.", "Spread it widely.", [INF(-15)], 1)], trigger=["original_tag = RIM", "has_completed_focus = TU_RIM_oripathy_research"], mtth=300)
C.ev(28, ("회사 통치", "Corporate Rule"), ("이사회가 정부를 대신한다.", "The board replaces the government."), [("이익을 위하여.", "For profit.", [ORE(50)], 1)])
C.ev(29, ("노동자 자치", "Workers' Self-Government"), ("광부들이 광산의 주인이 되었다.", "The miners have become masters of the mines."), [("함께 일한다.", "We work together.", ["add_stability = 0.05"], 1)])
C.ev(30, ("감염자의 안식처", "Haven for the Infected"), ("세상의 감염자들이 림 빌리튼으로 오기 시작했다.", "The infected of the world have begun coming to Rim Billiton."),
     [("어서 오라.", "Welcome.", ["add_manpower = 10000"], 1)])
C.ev(31, ("광석 가격 폭락", "Ore Price Crash"), ("세계 시장에서 원석 가격이 폭락했다.", "Originium prices have crashed on the world market."),
     [("비축한다.", "Stockpile.", ["add_political_power = -25"], 50), ("헐값에 판다.", "Sell cheap.", [ORE(-50), "add_political_power = 30"], 50)],
     trigger=["original_tag = RIM", AT_LEAST("ore", 150)], mtth=300)

for sid, ko, en, pre, econ in (
        ("ore_smelters", "광석 제련소", "Ore Smelters", "deep_shafts", True), ("conveyor_belts", "컨베이어 설비", "Conveyor Belt Industry", "ore_trains", True),
        ("drill_machines", "굴착기", "Drilling Machine Engineering", "mine_lights", False), ("ore_warehouses", "광석 창고", "Ore Warehouse Supply", "ore_markets", False),
        ("board_elections", "이사 선거", "Board Elections", "company_stores", False), ("company_spies", "회사 정보원", "Company Informant Network", "corporate_police", False),
        ("shareholder_dividends", "주주 배당", "Shareholder Dividend Trade", "ore_futures", False), ("union_hall", "노조 회관", "Union Hall Construction", "strike_fund", True),
        ("workers_theatre", "노동자 극장", "Workers' Theatre Festival", "union_press", False), ("cooperative_stores", "협동조합 상점", "Cooperative Store Trade", "workers_bank", False),
        ("arts_therapy", "아츠 치료", "Arts Therapy Research", "infection_survey", False), ("oripathy_cure", "치료제 연구", "Oripathy Cure Research", "arts_therapy", False),
        ("burial_rites", "광석병 장례", "Oripathy Burial Rites", "protective_gear", False), ("settler_schools", "정착민 학교", "Settler Schools Education", "settler_farms", False),
        ("refugee_registry", "피난민 등록", "Refugee Registry Records", "refugee_camps", False), ("haven_markets", "안식처 시장", "Haven Markets Trade", "haven_hospitals", False),
        ("wasteland_rangers", "황야 순찰대", "Wasteland Ranger Scouts", "border_scouts", False), ("motor_patrols", "차량 순찰", "Motorised Patrols", "anti_raider", False),
        ("armoured_cars", "장갑차", "Armoured Car Units", "motor_patrols", False), ("field_hospitals", "야전 병원", "Field Hospitals", "defence_force", False),
        ("air_scouts", "비행 정찰대", "Air Scouts", "defence_force", False), ("textile_mills", "작업복 공장", "Workwear Textile Mills", "steel_works", True),
        ("cement_works", "시멘트 공장", "Cement Works Construction", "chemical_plants", True), ("ore_reactors", "원석 반응로", "Originium Reactor Plants", "ore_power", True),
        ("lungmen_trade", "용문 교역", "Lungmen Trade Accord", "yan_trade", False), ("iberia_ties", "이베리아 교류", "Iberia Exchange", "siracusa_corridor", False)):
    f(sid, ko, en, pre=[pre], econ=econ)
C.d(cat_m, "safety_inspection", "갱도 안전 점검", "Shaft Safety Inspection", [INF(-5), "add_stability = 0.02"], cost=25, once=False, days_re_enable=120)
C.d(cat_m, "overtime", "증산 지시", "Order Overtime", [ORE(40), INF(5), "add_stability = -0.02"], cost=0, once=False, days_re_enable=120)
C.d(cat_h, "suppressant_imports", "억제제 수입", "Import Suppressants", [INF(-10), "add_political_power = -40"], cost=0, once=False, days_re_enable=120)
C.d(cat_s, "settler_farms_aid", "정착민 농지 분배", "Distribute Land to Settlers", ["add_stability = 0.03", "add_manpower = 3000"], cost=50, once=False,
    days_re_enable=240, available=[AT_LEAST("settlements", 2)])
C.d(cat_s, "infected_volunteers", "감염자 의용대", "Infected Volunteers", ["add_manpower = 10000", "add_war_support = 0.03"], cost=50, once=False,
    days_re_enable=240, visible=["has_completed_focus = TU_RIM_infected_rights"], icon="GFX_decision_generic_military")
C.ev(32, ("회사의 횡령", "Company Embezzlement"), ("회사 간부가 광산 수익을 빼돌린 사실이 드러났다.", "A company executive was caught siphoning mine profits."),
     [("처벌한다.", "Punish him.", ["add_stability = 0.02", ORE(20)], 50), ("덮는다.", "Cover it up.", ["add_political_power = 25", "add_stability = -0.02"], 50)],
     trigger=["original_tag = RIM", "has_completed_focus = TU_RIM_company_board"], mtth=300)
C.ev(33, ("감염자 아이들", "Infected Children"), ("광산 마을의 감염자 아이들이 학교에서 쫓겨났다.", "Infected children in a mining town were expelled from school."),
     [("학교를 연다.", "Open schools for them.", ["add_political_power = -20", "add_stability = 0.03"], 60), ("어쩔 수 없다.", "It can't be helped.", ["add_stability = -0.02"], 40)],
     trigger=["original_tag = RIM", AT_LEAST("infection", 40)], mtth=300)
C.ev(34, ("광산 노래", "Miners' Song"), ("광부들의 노래가 라디오를 타고 전국에 퍼졌다.", "The miners' song spread nationwide over the radio."),
     [("함께 부른다.", "Sing along.", ["add_war_support = 0.03", "add_stability = 0.02"], 1)],
     trigger=["original_tag = RIM", HAS("union")], mtth=300)

if __name__ == "__main__":
    C.write()
