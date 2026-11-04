#!/usr/bin/env python3
"""사르곤(SAR) 고유 콘텐츠 (사양서 17).

장치
  1. 영주들의 충성 TU_SAR_loyalty (0~100, 시작 40): 파디샤가 영주들을 얼마나 쥐고 있는지. 30 미만이면 영주 반란 이벤트.
     궁정 소집(충성↑)·조공 요구(정치력↑ 충성↓)·영주 처벌 디시전으로 움직인다.
  2. 황금 TU_SAR_gold (0~200, 시작 20): 대상단 디시전(60일 뒤 돌아옴)으로 모으고 용병·충성·연구에 쓴다.
  3. 사막 원정: 푀엔 열지로 원정대를 보내는 디시전(90일) → 결과 이벤트 (유적·황금·실종).
정치 결말 셋 (서로 배타): 파디샤의 제국(충성 70) / 영주 연합(충성 40 이하) / 황금 상인 정부(황금 100).

실행: python -I tools/focusgen/content/sar.py && python -I tools/focusgen/merge_focus.py --tag SAR
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_lib import Country  # noqa: E402

C = Country("SAR", "사르곤", "Sargon")
f = C.f
MAXV = {"loyalty": 100, "gold": 200}
NAMES = {"loyalty": ("§Y영주 충성§!", "§YLords' Loyalty§!"), "gold": ("§Y황금§!", "§YGold§!")}


def V(var, n):
    name = "TU_SAR_%s_%s%d" % (var, "m" if n < 0 else "", abs(n))
    if not any(e.startswith(name + " =") for e in C.effects):
        C.effects.append("""%s = {
	custom_effect_tooltip = %s_tt
	hidden_effect = {
		add_to_variable = { TU_SAR_%s = %d }
		clamp_variable = { var = TU_SAR_%s min = 0 max = %d }
	}
}""" % (name, name, var, n, var, MAXV[var]))
        ko, en = NAMES[var]
        C.loc(name + "_tt", "%s %s%d" % (ko, "+" if n > 0 else "", n), "%s %s%d" % (en, "+" if n > 0 else "", n))
    return "%s = yes" % name


def LOY(n):
    return V("loyalty", n)


def GOLD(n):
    return V("gold", n)


def AT_LEAST(var, n):
    return "check_variable = { TU_SAR_%s > %d }" % (var, n - 1)


def AT_MOST(var, n):
    return "check_variable = { TU_SAR_%s < %d }" % (var, n + 1)


def FLAG(x):
    return "set_country_flag = TU_SAR_%s" % x


def HAS(x):
    return "has_country_flag = TU_SAR_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_sar_ev.%d%s }" % (n, " days = %d" % days if days else "")


C.history += ["set_variable = { TU_SAR_loyalty = 40 }", "set_variable = { TU_SAR_gold = 20 }",
              "add_ideas = { TU_SAR_feuding_lords TU_SAR_endless_desert }"]
C.effects.append("""TU_SAR_monthly = {
	if = { limit = { has_country_flag = TU_SAR_tribute_system } add_to_variable = { TU_SAR_gold = 2 } }
	if = { limit = { has_idea = TU_SAR_feuding_lords } add_to_variable = { TU_SAR_loyalty = -1 } }
	clamp_variable = { var = TU_SAR_loyalty min = 0 max = 100 }
	clamp_variable = { var = TU_SAR_gold min = 0 max = 200 }
}""")
C.on_actions.append("""on_monthly = {
	effect = {
		if = {
			limit = { original_tag = SAR }
			TU_SAR_monthly = yes
		}
	}
}""")

# ------------------------------------------------------------------ 국민정신
C.idea("feuding_lords", "다투는 영주들", "Feuding Lords", {"stability_factor": -0.05, "political_power_gain": -0.1},
       "generic_army_problems", ("사르곤의 영주들은 파디샤보다 서로를 더 신경 쓴다. 충성이 매달 조금씩 떨어진다.",
                                 "Sargon's lords care more about each other than the Padishah. Loyalty slowly falls every month."))
C.idea("endless_desert", "끝없는 사막", "The Endless Desert", {"attrition": 0.05, "supply_consumption_factor": 0.05},
       "generic_supply_line", ("사막은 길고 물은 귀하다.", "The desert is long and water is precious."))
C.idea("desert_mastery", "사막의 주인", "Masters of the Desert", {"attrition": -0.1, "supply_consumption_factor": -0.1, "army_speed_factor": 0.05},
       "generic_supply_line")
C.idea("camel_riders", "낙타 기병", "Camel Riders", {"army_speed_factor": 0.08, "army_org_factor": 0.03}, "generic_army_europe_1")
C.idea("jungle_fighters", "정글 전사", "Jungle Fighters", {"army_defence_factor": 0.08, "attrition": -0.05}, "generic_guerilla_warfare")
C.idea("golden_trade", "황금 교역", "Golden Trade", {"political_power_gain": 0.1, "consumer_goods_factor": -0.03}, "generic_economic_increase")
C.idea("padishah_empire", "파디샤의 제국", "Empire of the Padishah",
       {"political_power_gain": 0.15, "stability_factor": 0.1, "conscription_factor": 0.05}, "generic_central_management")
C.idea("lords_confederation", "영주 연합", "Confederation of Lords",
       {"army_org_factor": 0.05, "conscription_factor": 0.1, "political_power_gain": -0.05}, "generic_local_self_management")
C.idea("golden_council", "황금 상인 정부", "Golden Merchant Council",
       {"production_speed_buildings_factor": 0.1, "consumer_goods_factor": -0.05, "political_power_gain": 0.1}, "generic_foreign_capital")
C.idea("oasis_network", "오아시스망", "Oasis Network", {"production_speed_infrastructure_factor": 0.15, "attrition": -0.05}, "generic_railroads")
C.idea("ancient_knowledge", "고대의 지식", "Ancient Knowledge", {"research_speed_factor": 0.05}, "generic_research_bonus")

# ------------------------------------------------------------------ 중점
f("root", "파디샤의 땅", "Land of the Padishah", cost=5, theme=False, reward=["add_political_power = 50", EV(1)],
  desc=("파디샤의 궁전은 화려하지만, 사막과 정글의 영주들은 저마다 왕처럼 군다.",
        "The Padishah's palace is splendid, but the lords of desert and jungle each act like kings."))

# A. 파디샤 (중앙집권)
f("court_summons", "궁정 소집령", "Court Summons", pre=["root"], theme=False, reward=[FLAG("court"), LOY(5)],
  desc=("영주들을 궁정에 부른다. '파디샤의 궁정' 디시전이 열린다.", "Call the lords to court. Unlocks the Padishah's Court decisions."))
f("council_princes", "왕자들의 회의", "Council of Princes", pre=["court_summons"], reward=[LOY(5)])
f("royal_census", "왕실 인구 조사", "Royal Census", pre=["court_summons"])
f("tribute_system", "조공 체계", "Tribute System", pre=["council_princes"], theme=False, reward=[FLAG("tribute_system"), GOLD(10)],
  desc=("황금이 매달 2씩 들어온다.", "Gold rises by 2 every month."))
f("royal_roads", "왕의 길", "Royal Roads", pre=["royal_census"], econ="TU_build_infrastructure = yes")
f("governors", "총독 임명", "Appoint Governors", pre=["council_princes", "royal_census"], reward=[LOY(10)])
f("palace_guard", "궁전 근위대", "Palace Guard Regiments", pre=["governors"])
f("end_feuds", "영주 분쟁 종식", "End the Lords' Feuds", pre=["governors"], theme=False, available=[AT_LEAST("loyalty", 50)],
  reward=["remove_ideas = TU_SAR_feuding_lords", LOY(10)], desc=("다투는 영주들 국민정신을 없앤다. (충성 50 이상)", "Removes Feuding Lords. (Loyalty 50+)"))
f("padishah_empire", "파디샤의 제국", "Empire of the Padishah", pre=["end_feuds", "palace_guard"],
  me=["lords_confederation", "golden_council"], cost=15, theme=False, available=[AT_LEAST("loyalty", 70)],
  reward=[FLAG("path_padishah"), "add_ideas = TU_SAR_padishah_empire", EV(28)],
  desc=("파디샤가 사르곤 전체를 하나로 다스린다. (충성 70 이상)", "The Padishah rules all Sargon as one. (Loyalty 70+)"))
f("imperial_law", "제국 법전", "Imperial Law Codex", pre=["padishah_empire"])
f("imperial_army", "제국군", "Imperial Army Regiments", pre=["padishah_empire"])
f("throne_of_sand", "모래의 옥좌", "Throne of Sand", pre=["imperial_law", "imperial_army"], theme=False,
  reward=["add_political_power = 100", "add_war_support = 0.05"])

# B. 영주들
f("lords_rights", "영주의 권리", "Rights of the Lords", pre=["root"], reward=[LOY(-5)])
f("tribal_accord", "부족 화합", "Tribal Accord", pre=["lords_rights"])
f("lords_levies", "영주 징병", "Lords' Levies", pre=["lords_rights"])
f("jungle_lords", "정글 영주", "Jungle Lords Pact", pre=["tribal_accord"])
f("desert_lords", "사막 영주", "Desert Lords Pact", pre=["tribal_accord"])
f("lords_council", "영주 의회", "Lords' Assembly Council", pre=["jungle_lords", "desert_lords"])
f("lords_confederation", "영주 연합", "Confederation of Lords", pre=["lords_council"], me=["padishah_empire", "golden_council"],
  cost=15, theme=False, available=[AT_MOST("loyalty", 40)],
  reward=[FLAG("path_lords"), "add_ideas = TU_SAR_lords_confederation", "remove_ideas = TU_SAR_feuding_lords", EV(29)],
  desc=("파디샤는 영주들 가운데 첫째일 뿐이다. (충성 40 이하)", "The Padishah is only first among the lords. (Loyalty 40 or less)"))
f("feudal_armies", "영주군", "Feudal Army Regiments", pre=["lords_confederation"])
f("local_rule", "지방 자치", "Local Self-Rule Administration", pre=["lords_confederation"])
f("lords_alliance", "영주 동맹 맹약", "Lords' Alliance Pact", pre=["feudal_armies", "local_rule"])

# C. 황금 무역
f("gold_trade", "황금 무역", "Gold Trade", pre=["root"], theme=False, reward=["add_ideas = TU_SAR_golden_trade", FLAG("caravans"), GOLD(10)],
  desc=("'대상단' 디시전이 열린다.", "Unlocks the Caravan decisions."))
f("caravan_trade", "대상단 교역", "Caravan Trade", pre=["gold_trade"], reward=[GOLD(10)])
f("oasis_markets", "오아시스 시장", "Oasis Markets", pre=["gold_trade"])
f("caravan_guards", "대상 호위대", "Caravan Guard Squads", pre=["caravan_trade"])
f("trade_monopoly", "교역 독점", "Trade Monopoly", pre=["oasis_markets", "caravan_trade"], me=["free_trade"], reward=[GOLD(20)])
f("free_trade", "자유 교역", "Free Trade", pre=["oasis_markets", "caravan_trade"], me=["trade_monopoly"])
f("sargon_treasury", "사르곤 국고", "Sargon Treasury", pre=[["trade_monopoly", "free_trade"]], reward=[GOLD(10)])
f("golden_council", "황금 상인 정부", "Golden Merchant Council", pre=["sargon_treasury"], me=["padishah_empire", "lords_confederation"],
  cost=15, theme=False, available=[AT_LEAST("gold", 100)],
  reward=[FLAG("path_gold"), "add_ideas = TU_SAR_golden_council", EV(30)],
  desc=("상인들이 궁정을 산다. (황금 100 이상)", "The merchants buy the court. (Gold 100+)"))
f("merchant_banks", "상인 은행", "Merchant Banks", pre=["golden_council"])
f("gold_mints", "황금 주조소", "Gold Mints", pre=["merchant_banks"], econ=True)
f("trade_empire", "교역 제국", "Trade Empire", pre=["gold_mints"], theme=False, reward=["add_political_power = 100", GOLD(30)])

# D. 사막과 원정
f("desert_scouts", "사막 정찰대", "Desert Scouts", pre=["root"])
f("water_wells", "우물 개발", "Water Wells Construction", pre=["desert_scouts"], econ="TU_build_infrastructure = yes")
f("oasis_network", "오아시스망", "Oasis Network", pre=["water_wells"], theme=False, reward=["add_ideas = TU_SAR_oasis_network"])
f("foehn_expeditions", "푀엔 원정", "Foehn Expeditions", pre=["desert_scouts"], theme=False, reward=[FLAG("expeditions")],
  desc=("푀엔 열지로 원정대를 보내는 디시전이 열린다.", "Unlocks the decision to send expeditions into the Foehn Hotlands."))
f("ruin_studies", "유적 연구", "Ruin Studies Research", pre=["foehn_expeditions"])
f("ancient_knowledge", "고대의 지식", "Ancient Knowledge", pre=["ruin_studies"], theme=False, available=[HAS("found_ruins")],
  reward=["add_ideas = TU_SAR_ancient_knowledge"], desc=("원정에서 유적을 찾아야 한다.", "Requires ruins found on an expedition."))
f("desert_mastery", "사막의 주인", "Masters of the Desert", pre=["oasis_network"], theme=False,
  reward=["swap_ideas = { remove_idea = TU_SAR_endless_desert add_idea = TU_SAR_desert_mastery }"])

# E. 군사
f("desert_warriors", "사막 전사", "Desert Warriors", pre=["root"])
f("camel_cavalry", "낙타 기병", "Camel Cavalry", pre=["desert_warriors"], theme=False, reward=["add_ideas = TU_SAR_camel_riders"])
f("jungle_training", "정글 전투 훈련", "Jungle Warfare Training", pre=["desert_warriors"])
f("jungle_fighters", "정글 전사단", "Jungle Fighters Regiments", pre=["jungle_training"], theme=False, reward=["add_ideas = TU_SAR_jungle_fighters"])
f("raid_tactics", "기습 전술", "Raid Tactics", pre=["camel_cavalry"], me=["fortress_defence"])
f("fortress_defence", "요새 방어", "Fortress Defence", pre=["camel_cavalry"], me=["raid_tactics"])
f("bow_arsenal", "활과 창 무기고", "Bow and Spear Arsenal", pre=["desert_warriors"])
f("rifle_imports", "소총 수입", "Rifle Weapons Imports", pre=["bow_arsenal"])
f("artillery_camels", "낙타 포병", "Camel Artillery", pre=["rifle_imports"])
f("motor_columns", "차량 행렬", "Motorised Desert Columns", pre=[["raid_tactics", "fortress_defence"]])
f("armoured_cars", "사막 장갑차", "Desert Armoured Cars", pre=["motor_columns"])
f("officer_school", "사관학교", "Officer School", pre=["jungle_fighters"])
f("mercenary_bands", "용병단 고용", "Mercenary Bands", pre=["officer_school"], theme=False, reward=[FLAG("mercs")],
  desc=("'황금 용병' 디시전이 열린다.", "Unlocks the Gold Mercenaries decision."))
f("sand_army", "모래 군단", "Sand Legion Army", pre=["armoured_cars", "mercenary_bands"])
f("air_scouts", "사막 비행대", "Desert Air Scouts", pre=["officer_school"])

# F. 경제
f("mining", "광산 개발", "Mining Development", pre=["root"], econ=True)
f("road_network", "도로망 건설", "Road Network", pre=["mining"], econ="TU_build_infrastructure = yes")
f("industrial_district", "공업 지구", "Industrial District", pre=["mining"], econ=True)
f("civ_program", "민간 공장 계획", "Civilian Factory Program", pre=["industrial_district"], me=["arms_program"], econ=True)
f("arms_program", "군수 공장 계획", "Arms Factory Program", pre=["industrial_district"], me=["civ_program"], econ="TU_build_mil_factory = yes")
f("irrigation", "관개 시설", "Irrigation Works", pre=["road_network"], econ=True)
f("rail_network", "철도 연결", "Rail Network Expansion", pre=["irrigation"], econ="TU_build_infrastructure = yes")
f("spice_plantations", "향신료 농장", "Spice Plantations Farms", pre=["irrigation"], econ=True)
f("oil_fields", "유전 개발", "Oil Fields", pre=["rail_network"], econ=True)
f("refineries", "정유소", "Oil Refineries", pre=["oil_fields"], econ=True)
f("industrialisation", "사르곤 산업화", "Sargon Industrialisation", pre=[["civ_program", "arms_program"], "refineries"], econ=True)
f("research_slot", "왕립 학술원", "Royal Academy of Sciences", pre=["industrialisation"], theme=False,
  reward=["add_research_slot = 1"], desc=("연구 슬롯 +1", "Research slot +1"))

# G. 외교
f("foreign_court", "외교 궁정", "Foreign Court Envoys", pre=["root"])
f("columbia_trade", "컬럼비아 교역", "Columbia Trade Accord", pre=["foreign_court"])
f("minos_pact", "미노스 협정", "Minos Pact", pre=["foreign_court"])
f("iberia_border", "이베리아 국경", "Iberia Border Watch", pre=["minos_pact"])
f("bolivar_ties", "볼리바르 관계", "Bolivar Relations", pre=["columbia_trade"])
f("southern_sun", "남부의 태양 동맹", "Southern Sun Alliance", pre=["iberia_border", "bolivar_ties"], theme=False,
  reward=[FLAG("alliance")], desc=("'남부의 태양' 진영 디시전이 열린다.", "Unlocks the Southern Sun faction decisions."))

# ------------------------------------------------------------------ 추가 중점 (갈래 보강)
f("court_poets", "궁정 시인", "Court Poets Propaganda", pre=["court_summons"])
f("royal_spies", "왕실 밀정", "Royal Spies Network", pre=["royal_census"])
f("palace_reforms", "궁정 개혁", "Palace Reforms", pre=["council_princes"])
f("royal_treasury", "왕실 금고", "Royal Treasury", pre=["tribute_system"], reward=[GOLD(10)])
f("hostage_princes", "인질 왕자", "Princes at Court", pre=["palace_reforms"], reward=[LOY(10)])
f("royal_marriages", "왕실 혼인", "Royal Marriage Alliance", pre=["hostage_princes"], reward=[LOY(5)])
f("lords_markets", "영주의 시장", "Lords' Markets", pre=["lords_levies"])
f("tribal_warriors", "부족 전사", "Tribal Warrior Regiments", pre=["lords_levies"])
f("clan_elders", "부족 원로", "Clan Elders Council", pre=["tribal_accord"])
f("river_ports", "강 항구", "River Ports Harbour", pre=["jungle_lords"], econ="TU_build_civ_factory = yes")
f("salt_trade", "소금 교역", "Salt Trade", pre=["caravan_trade"], reward=[GOLD(5)])
f("incense_routes", "향료 교역", "Incense Trade", pre=["oasis_markets"], reward=[GOLD(5)])
f("caravanserai", "대상 숙소", "Caravanserai Construction", pre=["caravan_guards"], econ=True)
f("gold_reserves", "황금 비축", "Gold Reserves", pre=["sargon_treasury"], reward=[GOLD(15)])
f("sand_maps", "사막 지도 제작", "Desert Survey Maps", pre=["desert_scouts"])
f("expedition_camps", "원정 기지", "Expedition Base Camps", pre=["foehn_expeditions"])
f("buried_cities", "묻힌 도시들", "Buried Cities Research", pre=["ruin_studies"])
f("ziggurat_restoration", "지구라트 복원", "Ziggurat Restoration Construction", pre=["buried_cities"], econ=True)
f("sand_storm_drills", "모래폭풍 훈련", "Sandstorm Drill Training", pre=["desert_warriors"])
f("spear_doctrine", "창병 교리", "Spear Infantry Doctrine", pre=["bow_arsenal"])
f("war_elephants", "전투 거수", "War Beast Cavalry", pre=["camel_cavalry"])
f("jungle_ambush", "정글 매복", "Jungle Ambush Tactics", pre=["jungle_training"])
f("field_hospitals", "야전 병원", "Field Hospitals", pre=["jungle_fighters"])
f("supply_caravans", "보급 대상단", "Supply Caravans Logistics", pre=["motor_columns"])
f("timber_industry", "목재 산업", "Timber Industry", pre=["spice_plantations"], econ=True)
f("copper_mines", "구리 광산", "Copper Mines", pre=["mining"], econ=True)
f("textile_mills", "직물 공장", "Textile Mills", pre=["copper_mines"], econ=True)
f("power_stations", "발전소", "Power Stations", pre=["rail_network"], econ="TU_build_infrastructure = yes")
f("laterano_mission", "라테라노 선교단", "Laterano Mission Envoys", pre=["foreign_court"])
f("kazdel_refugees", "카즈델 피난민", "Kazdel Refugee Shelters", pre=["minos_pact"])
f("rim_ore_trade", "림 빌리튼 광석 교역", "Rim Billiton Ore Trade", pre=["columbia_trade"])

# ------------------------------------------------------------------ 디시전
cat_court = C.category("court", "파디샤의 궁정", "The Padishah's Court",
                       ("영주들의 충성이 30 아래로 떨어지면 반란이 일어날 수 있다.", "If the lords' loyalty falls below 30, they may revolt."),
                       visible=[HAS("court")])
C.d(cat_court, "summon_lords", "영주 소집", "Summon the Lords", [LOY(10), "add_political_power = -10"], cost=50, once=False,
    days_re_enable=120, desc=("충성 +10", "Loyalty +10"), icon="GFX_decision_generic_political_address")
C.d(cat_court, "demand_tribute", "조공 요구", "Demand Tribute", [GOLD(20), "add_political_power = 40", LOY(-10)], cost=0, once=False,
    days_re_enable=120, desc=("황금 +20, 정치력 +40, 충성 -10", "Gold +20, political power +40, loyalty -10"), icon="GFX_decision_generic_fundraising")
C.d(cat_court, "punish_lord", "영주 처벌", "Punish a Lord", [LOY(15), "add_stability = -0.05", GOLD(10)], cost=75, once=False,
    days_re_enable=365, available=["has_army_manpower = { size > 20000 }"],
    desc=("본보기로 영주 하나를 벌한다. 충성 +15, 안정도 -5%, 황금 +10", "Make an example of one lord. Loyalty +15, stability -5%, gold +10"))
C.d(cat_court, "gold_gifts", "황금 하사", "Gifts of Gold", [LOY(15), GOLD(-30)], cost=0, once=False, days_re_enable=120,
    available=[AT_LEAST("gold", 30)], desc=("황금 30을 써서 충성 +15", "Spend 30 gold for loyalty +15"))
C.d(cat_court, "royal_hunt", "왕실 사냥 대회", "Royal Hunt", [LOY(5), "add_stability = 0.03"], cost=25, once=False, days_re_enable=240)

cat_gold = C.category("caravans", "대상단과 황금", "Caravans and Gold", icon="GFX_decision_category_generic_industry",
                      desc=("대상단은 60일 뒤 황금을 싣고 돌아온다.", "Caravans return with gold after 60 days."),
                      visible=["OR = {", "\t" + HAS("caravans"), "\t" + HAS("expeditions"), "\t" + HAS("mercs"), "\t" + HAS("alliance"), "}"])
for sid, ko, en, cost, gain in (("caravan_east", "동방 대상단", "Eastern Caravan", 25, 20), ("caravan_north", "북방 대상단", "Northern Caravan", 50, 35)):
    C.d(cat_gold, sid, ko, en, [FLAG(sid + "_out")], cost=cost, once=False, days_remove=60, days_re_enable=30,
        visible=[HAS("caravans")], available=["NOT = { %s }" % HAS(sid + "_out")],
        remove_effect=[GOLD(gain), "clr_country_flag = TU_SAR_%s_out" % sid,
                       "if = { limit = { has_completed_focus = TU_SAR_caravan_guards } %s }" % GOLD(10)],
        desc=("60일 뒤 황금 +%d (대상 호위대가 있으면 +10)" % gain, "Gold +%d after 60 days (+10 with caravan guards)" % gain),
        icon="GFX_decision_generic_train")
C.d(cat_gold, "expedition", "푀엔 원정대 파견", "Send a Foehn Expedition", [FLAG("expedition_out")], cost=50, once=False,
    days_remove=90, days_re_enable=60, visible=[HAS("expeditions")], available=["NOT = { %s }" % HAS("expedition_out")],
    remove_effect=["clr_country_flag = TU_SAR_expedition_out", EV(20)],
    desc=("90일 뒤 원정 결과가 나온다.", "The expedition reports back after 90 days."), icon="GFX_decision_generic_operation")
C.d(cat_gold, "gold_mercs", "황금 용병", "Gold Mercenaries",
    ["TU_SAR_merc_template = yes",
     "capital_scope = { create_unit = { division = \"division_template = \\\"TU_SAR_mercs\\\" start_experience_factor = 0.4 start_equipment_factor = 0.8\" owner = SAR count = 2 } }",
     GOLD(-40)], cost=25, once=False, days_re_enable=120, visible=[HAS("mercs")], available=[AT_LEAST("gold", 40)],
    desc=("황금 40으로 용병 사단 2개를 고용한다.", "Hire two mercenary divisions for 40 gold."), icon="GFX_decision_generic_military")
C.d(cat_gold, "gold_research", "학자 후원", "Patronise Scholars",
    ["add_tech_bonus = { name = TU_SAR_gold_research bonus = 0.75 uses = 1 category = industry category = electronics }", GOLD(-30)],
    cost=25, once=False, days_re_enable=180, visible=[HAS("caravans")], available=[AT_LEAST("gold", 30)])
C.d(cat_gold, "found_alliance", "남부의 태양 결성", "Found the Southern Sun", ["create_faction = TU_SAR_alliance"], cost=50,
    visible=[HAS("alliance")], available=["is_in_faction = no"])
C.loc("TU_SAR_alliance", "남부의 태양", "The Southern Sun")
C.d(cat_gold, "invite_alliance", "동맹 초청", "Invite to the Alliance", ["add_to_faction = FROM", GOLD(-20)], cost=50, once=False,
    days_re_enable=90, visible=[HAS("alliance"), "is_faction_leader = yes"], available=[AT_LEAST("gold", 20)],
    target=["NOT = { tag = ROOT }", "is_in_faction = no", "NOT = { has_war_with = ROOT }", "OR = { tag = MIN tag = IBE tag = BOL tag = COL }"])
C.effects.append("""TU_SAR_merc_template = {
	if = {
		limit = { NOT = { has_country_flag = TU_SAR_merc_template_done } }
		set_country_flag = TU_SAR_merc_template_done
		division_template = {
			name = "TU_SAR_mercs"
			is_locked = no
			priority = 2
			regiments = {
				infantry = { x = 0 y = 0 }
				infantry = { x = 0 y = 1 }
				cavalry = { x = 1 y = 0 }
				cavalry = { x = 1 y = 1 }
			}
		}
	}
}""")

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("파디샤의 아침", "Morning of the Padishah"),
     ("궁전의 분수가 물을 뿜는다. 같은 시각, 사막 끝의 영주는 파디샤의 사신을 문전박대했다.",
      "The palace fountains splash. At the same hour, a lord at the desert's edge turned the Padishah's envoy away."),
     [("영주들을 길들여야 한다.", "The lords must be tamed.", [LOY(5)], 50), ("황금이 모든 것을 해결한다.", "Gold solves everything.", [GOLD(10)], 50)])
C.ev(20, ("원정대의 귀환", "The Expedition Returns"),
     ("푀엔 열지로 떠났던 원정대가 돌아왔다. 무엇을 가져왔을까?", "The expedition to the Foehn Hotlands has returned. What did it bring back?"),
     [("모래에 묻힌 유적을 찾았다!", "Ruins buried in the sand!", ["trigger = { %s }" % HAS("exp_ruins"), FLAG("found_ruins"),
       "add_tech_bonus = { name = TU_SAR_ruins bonus = 0.5 uses = 1 category = electronics }", "clr_country_flag = TU_SAR_exp_ruins"], 1),
      ("황금 광맥을 찾았다!", "A vein of gold!", ["trigger = { %s }" % HAS("exp_gold"), GOLD(40), "clr_country_flag = TU_SAR_exp_gold"], 1),
      ("원정대 일부가 돌아오지 못했다.", "Part of the expedition never came back.", ["trigger = { %s }" % HAS("exp_lost"),
       "add_manpower = -2000", "army_experience = 10", "clr_country_flag = TU_SAR_exp_lost"], 1)],
     immediate=["random_list = {", "\t35 = { %s }" % FLAG("exp_ruins"), "\t35 = { %s }" % FLAG("exp_gold"), "\t30 = { %s }" % FLAG("exp_lost"), "}"],
     picture="GFX_report_event_generic_ruins")
C.ev(21, ("영주의 반란", "A Lord Rebels"),
     ("한 영주가 파디샤의 깃발을 내리고 자기 깃발을 올렸다. 다른 영주들이 지켜보고 있다.",
      "A lord has lowered the Padishah's banner and raised his own. The other lords are watching."),
     [("군을 보내 진압한다.", "Send the army.", ["army_experience = 15", "add_stability = -0.03", LOY(10)], 50),
      ("황금으로 달랜다.", "Placate him with gold.", [GOLD(-30), LOY(5)], 30),
      ("그의 요구를 들어준다.", "Grant his demands.", ["add_political_power = -50", "add_stability = 0.02"], 20)],
     trigger=["original_tag = SAR", AT_MOST("loyalty", 29)], mtth=90, fire_once=False, picture="GFX_report_event_generic_riot")
C.ev(22, ("모래폭풍", "Sandstorm"), ("거대한 모래폭풍이 대상로를 덮었다.", "A great sandstorm buries the caravan roads."),
     [("폭풍이 지나가길 기다린다.", "Wait it out.", [GOLD(-10)], 1)], trigger=["original_tag = SAR", HAS("caravans")], mtth=240, fire_once=False)
C.ev(23, ("정글의 열병", "Jungle Fever"), ("정글 지대에 열병이 돌았다.", "Fever is spreading through the jungle provinces."),
     [("의사를 보낸다.", "Send doctors.", ["add_political_power = -25", "add_stability = 0.02"], 60), ("버틴다.", "Endure it.", ["add_manpower = -3000"], 40)],
     trigger=["original_tag = SAR", "has_completed_focus = TU_SAR_jungle_training"], mtth=360)
C.ev(24, ("영주들의 연회", "Feast of the Lords"), ("영주들이 파디샤를 위한 연회를 열었다. 진심일까?", "The lords hold a feast in the Padishah's honour. Are they sincere?"),
     [("기꺼이 참석한다.", "Attend gladly.", [LOY(5), GOLD(-10)], 60), ("의심한다.", "Be suspicious.", ["add_political_power = 25", LOY(-5)], 40)],
     trigger=["original_tag = SAR", AT_LEAST("loyalty", 50)], mtth=300)
C.ev(25, ("황금 강도", "Gold Robbers"), ("국고로 향하던 황금 수송대가 습격당했다.", "A gold convoy bound for the treasury was ambushed."),
     [("범인을 쫓는다.", "Hunt the culprits.", ["army_experience = 10", GOLD(-10)], 50), ("손실을 받아들인다.", "Accept the loss.", [GOLD(-20)], 50)],
     trigger=["original_tag = SAR", AT_LEAST("gold", 60)], mtth=240)
C.ev(26, ("상인들의 청원", "The Merchants' Petition"), ("부유한 상인들이 궁정에서 발언권을 달라고 청원했다.", "Wealthy merchants petition for a voice at court."),
     [("받아들인다.", "Accept.", [GOLD(15), LOY(-5)], 50), ("거절한다.", "Refuse.", [LOY(5)], 50)],
     trigger=["original_tag = SAR", "has_completed_focus = TU_SAR_trade_monopoly"], mtth=300)
C.ev(27, ("오아시스의 발견", "A New Oasis"), ("정찰대가 지도에 없는 오아시스를 찾았다.", "Scouts found an oasis on no map."),
     [("정착지를 세운다.", "Found a settlement.", ["TU_build_infrastructure = yes", GOLD(5)], 1)],
     trigger=["original_tag = SAR", "has_completed_focus = TU_SAR_desert_scouts"], mtth=360)
C.ev(28, ("파디샤의 제국", "Empire of the Padishah"), ("모든 영주가 파디샤 앞에 무릎을 꿇었다.", "Every lord has knelt before the Padishah."),
     [("사르곤은 하나다.", "Sargon is one.", ["add_stability = 0.05"], 1)])
C.ev(29, ("영주 연합", "Confederation of Lords"), ("파디샤는 영주들과 권력을 나누기로 했다.", "The Padishah has chosen to share power with the lords."),
     [("함께 다스린다.", "We rule together.", ["add_manpower = 10000"], 1)])
C.ev(30, ("황금 상인 정부", "Golden Merchant Council"), ("궁정의 의자 절반을 상인들이 차지했다.", "Merchants now fill half the seats at court."),
     [("황금이 말한다.", "Gold speaks.", [GOLD(20)], 1)])

# 추가 (목표 분량)
for sid, ko, en, pre in (("desert_fortresses", "사막 요새", "Desert Fortresses", "fortress_defence"),
                         ("dune_riders", "모래언덕 기수", "Dune Rider Raid Squads", "raid_tactics"),
                         ("lords_courts", "영주 법정", "Lords' Courts Reform", "local_rule"),
                         ("padishah_portraits", "파디샤 초상", "Padishah Portrait Propaganda", "throne_of_sand"),
                         ("imperial_highways", "제국 대로", "Imperial Highways Road", "imperial_law"),
                         ("gold_standard", "금본위제", "Gold Standard Treasury", "merchant_banks"),
                         ("caravan_insurance", "대상 보험", "Caravan Insurance Companies", "caravanserai"),
                         ("oasis_farms", "오아시스 농장", "Oasis Farms", "oasis_network"),
                         ("star_navigators", "별의 항법사", "Star Navigator Studies", "sand_maps"),
                         ("relic_museum", "유물 박물관", "Relic Museum Archive", "ziggurat_restoration"),
                         ("light_tanks", "경전차", "Light Tank Units", "armoured_cars"),
                         ("air_bases", "사막 비행장", "Desert Airfields", "air_scouts"),
                         ("chemical_works", "화학 공업", "Chemical Works Industry", "refineries"),
                         ("glass_works", "유리 공방", "Desert Glass Works", "textile_mills"),
                         ("victoria_envoys", "빅토리아 사절", "Victoria Envoys", "foreign_court")):
    f(sid, ko, en, pre=[pre], econ=sid in ("oasis_farms", "chemical_works", "glass_works"))
C.d(cat_court, "lords_games", "영주 경기", "Lords' Games", [LOY(5), "add_war_support = 0.03"], cost=25, once=False, days_re_enable=240)
C.d(cat_court, "royal_pardon", "왕의 사면", "Royal Pardon", [LOY(10), "add_stability = -0.02"], cost=50, once=False, days_re_enable=365)
C.d(cat_court, "court_spies", "궁정 밀정 파견", "Send Court Spies", [LOY(5), "add_stability = 0.02"], cost=50, once=False,
    days_re_enable=240, visible=["has_completed_focus = TU_SAR_royal_spies"])
C.d(cat_gold, "salt_caravan", "소금 대상단", "Salt Caravan", [FLAG("salt_out")], cost=25, once=False, days_remove=45, days_re_enable=30,
    visible=["has_completed_focus = TU_SAR_salt_trade"], available=["NOT = { %s }" % HAS("salt_out")],
    remove_effect=[GOLD(15), "clr_country_flag = TU_SAR_salt_out"], icon="GFX_decision_generic_train",
    desc=("45일 뒤 황금 +15", "Gold +15 after 45 days"))
C.d(cat_gold, "gold_infrastructure", "황금으로 도로를", "Gold for Roads", ["TU_build_infrastructure = yes", GOLD(-25)], cost=0, once=False,
    days_re_enable=180, visible=[HAS("caravans")], available=[AT_LEAST("gold", 25)], icon="GFX_decision_generic_construction")
C.d(cat_gold, "gold_factory", "황금으로 공장을", "Gold for Factories", ["TU_build_civ_factory = yes", GOLD(-50)], cost=0, once=False,
    days_re_enable=240, visible=[HAS("caravans")], available=[AT_LEAST("gold", 50)], icon="GFX_decision_generic_factory")
C.d(cat_gold, "dig_ruins", "유적 발굴", "Excavate the Ruins",
    ["add_tech_bonus = { name = TU_SAR_dig_ruins bonus = 0.75 uses = 1 category = electronics category = industry }"], cost=75,
    once=False, days_re_enable=365, visible=[HAS("found_ruins")])
C.d(cat_gold, "jungle_timber", "정글 벌목권", "Jungle Timber Rights", [GOLD(15), LOY(-5)], cost=0, once=False, days_re_enable=180,
    visible=["has_completed_focus = TU_SAR_jungle_lords"])
C.ev(31, ("궁정의 음모", "Plot at Court"), ("궁정 시종 하나가 파디샤를 독살하려는 음모를 고발했다.", "A courtier exposes a plot to poison the Padishah."),
     [("주모자를 처형한다.", "Execute the ringleaders.", [LOY(5), "add_stability = -0.02"], 60), ("조용히 추방한다.", "Exile them quietly.", ["add_stability = 0.02"], 40)],
     trigger=["original_tag = SAR", AT_MOST("loyalty", 45)], mtth=300)
C.ev(32, ("거상의 기부", "A Merchant Prince's Gift"), ("한 거상이 국고에 막대한 황금을 바쳤다. 대가를 바라는 눈치다.", "A merchant prince donates a fortune to the treasury, clearly expecting something in return."),
     [("감사히 받는다.", "Accept gratefully.", [GOLD(30), LOY(-3)], 1)], trigger=["original_tag = SAR", "has_completed_focus = TU_SAR_gold_trade"], mtth=360)
C.ev(33, ("부족 간 결혼", "A Tribal Wedding"), ("두 부족이 혼인으로 오랜 다툼을 끝냈다.", "Two tribes end an old feud with a marriage."),
     [("축복한다.", "Give our blessing.", [LOY(5), "add_stability = 0.02"], 1)], trigger=["original_tag = SAR", "has_completed_focus = TU_SAR_tribal_accord"], mtth=360)
C.ev(34, ("메뚜기 떼", "Locust Swarm"), ("메뚜기 떼가 오아시스 농장을 덮쳤다.", "A locust swarm descends on the oasis farms."),
     [("구휼한다.", "Send relief.", [GOLD(-15), "add_stability = 0.02"], 50), ("버틴다.", "Endure it.", ["add_stability = -0.03"], 50)],
     trigger=["original_tag = SAR", "has_completed_focus = TU_SAR_irrigation"], mtth=400)

if __name__ == "__main__":
    C.write()
