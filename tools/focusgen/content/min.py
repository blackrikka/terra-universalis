#!/usr/bin/env python3
"""미노스(MIN) 고유 콘텐츠 (사양서 17).

장치
  1. 민회 지지 TU_MIN_assembly (0~100, 시작 50): 민회 법안 디시전(지지를 쓰고 보너스를 얻음)·축제·연설로 움직인다.
  2. 신탁 TU_MIN_oracle: '신탁을 구하다' 디시전 → 신탁 이벤트(길조 / 흉조 / 수수께끼) → 180일 국민정신.
  3. 해상 교역로 TU_MIN_routes (0~6): 교역로 개척 디시전. 교역로마다 매달 정치력 +0.3 (on_monthly).
     해적 이벤트가 교역로를 끊고, 해적 소탕 디시전으로 막는다.
  4. 철학 학파: 아카데미아 / 스토아 / 키니코스 중 하나 (서로 배타 중점, 각자 다른 보너스).
정치 결말 셋 (서로 배타): 민주 폴리스(민회 70) / 원로 정체(민회 30 이하) / 해상 패권(교역로 5).

실행: python -I tools/focusgen/content/min.py && python -I tools/focusgen/merge_focus.py --tag MIN
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_lib import Country  # noqa: E402

C = Country("MIN", "미노스", "Minos")
f = C.f
MAXV = {"assembly": 100, "routes": 6}
NAMES = {"assembly": ("§Y민회 지지§!", "§YAssembly Support§!"), "routes": ("§G해상 교역로§!", "§GSea Trade Routes§!")}


def V(var, n):
    name = "TU_MIN_%s_%s%d" % (var, "m" if n < 0 else "", abs(n))
    if not any(e.startswith(name + " =") for e in C.effects):
        C.effects.append("""%s = {
	custom_effect_tooltip = %s_tt
	hidden_effect = {
		add_to_variable = { TU_MIN_%s = %d }
		clamp_variable = { var = TU_MIN_%s min = 0 max = %d }
	}
}""" % (name, name, var, n, var, MAXV[var]))
        ko, en = NAMES[var]
        C.loc(name + "_tt", "%s %s%d" % (ko, "+" if n > 0 else "", n), "%s %s%d" % (en, "+" if n > 0 else "", n))
    return "%s = yes" % name


def ASM(n):
    return V("assembly", n)


def RT(n):
    return V("routes", n)


def AT_LEAST(var, n):
    return "check_variable = { TU_MIN_%s > %d }" % (var, n - 1)


def AT_MOST(var, n):
    return "check_variable = { TU_MIN_%s < %d }" % (var, n + 1)


def FLAG(x):
    return "set_country_flag = TU_MIN_%s" % x


def HAS(x):
    return "has_country_flag = TU_MIN_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_min_ev.%d%s }" % (n, " days = %d" % days if days else "")


C.history += ["set_variable = { TU_MIN_assembly = 50 }", "set_variable = { TU_MIN_routes = 1 }",
              "add_ideas = { TU_MIN_city_states TU_MIN_pirate_seas }"]
C.effects.append("""TU_MIN_monthly = {
%s}""" % "".join("\tif = { limit = { check_variable = { TU_MIN_routes > %d } } add_political_power = 0.3 }\n" % i for i in range(6)))
C.on_actions.append("""on_monthly = {
	effect = {
		if = {
			limit = { original_tag = MIN }
			TU_MIN_monthly = yes
		}
	}
}""")

# ------------------------------------------------------------------ 국민정신
C.idea("city_states", "도시국가 연맹", "League of City States", {"political_power_gain": -0.05, "stability_factor": 0.05}, "generic_local_self_management",
       ("다섯 도시가 민회에서 함께 결정한다. 느리지만 모두의 목소리가 담긴다.", "Five cities decide together in the assembly: slowly, but with every voice heard."))
C.idea("pirate_seas", "해적의 바다", "Pirate Seas", {"political_power_gain": -0.05, "consumer_goods_factor": 0.02}, "generic_economic_increase",
       ("교역로마다 해적이 숨어 있다.", "Pirates lurk along every trade route."))
for sid, ko, en, mods, pic in (
        ("good_omen", "길조", "Good Omen", {"stability_factor": 0.08, "war_support_factor": 0.05}, "generic_morale_bonus"),
        ("bad_omen", "흉조", "Bad Omen", {"stability_factor": -0.05, "political_power_gain": -0.1}, "generic_army_problems"),
        ("riddle_omen", "신탁의 수수께끼", "The Oracle's Riddle", {"research_speed_factor": 0.05, "stability_factor": -0.02}, "generic_research_bonus"),
        ("academia", "아카데미아 학파", "School of the Academy", {"research_speed_factor": 0.05}, "generic_research_bonus"),
        ("stoa", "스토아 학파", "School of the Stoa", {"stability_factor": 0.08, "war_support_factor": 0.03}, "generic_political_support"),
        ("cynics", "키니코스 학파", "School of the Cynics", {"consumer_goods_factor": -0.04, "political_power_gain": 0.05}, "generic_economic_increase"),
        ("democratic_polis", "민주 폴리스", "Democratic Polis", {"stability_factor": 0.1, "political_power_gain": 0.1, "research_speed_factor": 0.03}, "constitutional_guarantees"),
        ("rule_of_elders", "원로 정체", "Rule of the Elders", {"stability_factor": 0.12, "political_power_gain": 0.15, "consumer_goods_factor": 0.02}, "generic_central_management"),
        ("thalassocracy", "해상 패권", "Thalassocracy", {"political_power_gain": 0.15, "consumer_goods_factor": -0.03, "stability_factor": 0.05}, "generic_economic_increase"),
        ("hoplites", "중장 보병", "Hoplite Phalanx", {"army_defence_factor": 0.08, "army_org_factor": 0.03}, "generic_infantry_bonus")):
    C.idea(sid, ko, en, mods, pic)

# ------------------------------------------------------------------ 중점
f("root", "도시국가 연맹", "League of City States", cost=5, theme=False, reward=["add_political_power = 50", EV(1)],
  desc=("바다와 신탁과 철학의 나라. 다섯 도시가 민회에서 함께 길을 정한다.", "A land of sea, oracle and philosophy. Five cities choose their path together in the assembly."))

# A. 민회
f("agora", "아고라 회의", "Agora Assembly", pre=["root"], theme=False, reward=[FLAG("assembly"), ASM(5)],
  desc=("'민회' 디시전이 열린다.", "Unlocks the Assembly decisions."))
f("citizen_rolls", "시민 명부", "Citizen Rolls Census", pre=["agora"])
f("ostracism", "도편 추방", "Ostracism Vote", pre=["agora"], reward=[ASM(5)])
f("public_speeches", "공개 연설", "Public Speeches Propaganda", pre=["citizen_rolls"], reward=[ASM(5)])
f("democratic_reform", "민주 개혁", "Democratic Reform", pre=["public_speeches", "ostracism"], me=["elders_reform"], reward=[ASM(10)])
f("elders_reform", "원로원 강화", "Strengthen the Council of Elders", pre=["public_speeches", "ostracism"], me=["democratic_reform"], reward=[ASM(-15)])
f("democratic_polis", "민주 폴리스", "Democratic Polis", pre=["democratic_reform"], me=["rule_of_elders", "thalassocracy"], cost=15, theme=False,
  available=[AT_LEAST("assembly", 70)], reward=[FLAG("path_demo"), "swap_ideas = { remove_idea = TU_MIN_city_states add_idea = TU_MIN_democratic_polis }", EV(28)],
  desc=("시민 모두가 민회의 주인이다. (민회 지지 70 이상)", "Every citizen owns the assembly. (Assembly support 70+)"))
f("jury_courts", "배심 법정", "Jury Courts Reform", pre=["democratic_polis"])
f("free_schools", "시민 학교", "Citizen Schools Education", pre=["democratic_polis"])
f("golden_age", "황금시대", "The Golden Age", pre=["jury_courts", "free_schools"], theme=False, reward=["add_political_power = 100", "add_stability = 0.05"])
f("rule_of_elders", "원로 정체", "Rule of the Elders", pre=["elders_reform"], me=["democratic_polis", "thalassocracy"], cost=15, theme=False,
  available=[AT_MOST("assembly", 30)], reward=[FLAG("path_elders"), "swap_ideas = { remove_idea = TU_MIN_city_states add_idea = TU_MIN_rule_of_elders }", EV(29)],
  desc=("지혜로운 원로들이 다스린다. (민회 지지 30 이하)", "The wise elders rule. (Assembly support 30 or less)"))
f("elder_council", "원로 평의회", "Elder Council", pre=["rule_of_elders"])
f("temple_treasury", "신전 금고", "Temple Treasury", pre=["elder_council"])

# B. 신탁
f("temple_rites", "신전 의례", "Temple Rites", pre=["root"], theme=False, reward=[FLAG("oracle"), "add_stability = 0.02"],
  desc=("'신탁' 디시전이 열린다.", "Unlocks the Oracle decisions."))
f("oracle_priests", "신탁 사제단", "Oracle Priesthood", pre=["temple_rites"])
f("sacred_games", "성스러운 경기", "Sacred Games Festival", pre=["temple_rites"], reward=[ASM(5)])
f("prophecy_archive", "예언 기록", "Prophecy Archive Records", pre=["oracle_priests"])
f("divine_mandate", "신의 뜻", "Divine Mandate Propaganda", pre=["prophecy_archive", "sacred_games"])

# C. 철학
f("philosophers", "철학자 회의", "Philosophers' Council", pre=["root"])
f("academia", "아카데미아", "The Academy School", pre=["philosophers"], me=["stoa", "cynics"], theme=False, reward=["add_ideas = TU_MIN_academia"])
f("stoa", "스토아", "The Stoa School", pre=["philosophers"], me=["academia", "cynics"], theme=False, reward=["add_ideas = TU_MIN_stoa"])
f("cynics", "키니코스", "The Cynic School", pre=["philosophers"], me=["academia", "stoa"], theme=False, reward=["add_ideas = TU_MIN_cynics"])
f("mathematics", "수학 연구", "Mathematics Studies", pre=[["academia", "stoa", "cynics"]])
f("observatory", "천문대", "Observatory", pre=["mathematics"])
f("medical_studies", "의학 연구", "Medical Studies", pre=["mathematics"], me=["engineering_studies"])
f("engineering_studies", "공학 연구", "Engineering Studies", pre=["mathematics"], me=["medical_studies"])
f("great_library", "대도서관", "Great Library", pre=[["medical_studies", "engineering_studies"], "observatory"])
f("research_slot", "지혜의 도시", "City of Knowledge Research", pre=["great_library"], theme=False, reward=["add_research_slot = 1"],
  desc=("연구 슬롯 +1", "Research slot +1"))

# D. 바다와 교역
f("harbour_works", "항구 정비", "Harbour Works", pre=["root"], econ="TU_build_civ_factory = yes")
f("trade_routes", "교역로 개척", "Sea Trade Lanes", pre=["harbour_works"], theme=False, reward=[FLAG("routes"), RT(1)],
  desc=("'해상 교역' 디시전이 열린다. 교역로마다 매달 정치력 +0.3.", "Unlocks the Sea Trade decisions. Each route gives +0.3 political power per month."))
f("merchant_fleet", "상선 함대", "Merchant Fleet", pre=["trade_routes"], reward=[RT(1)])
f("pirate_hunt", "해적 소탕", "Pirate Hunt Navy", pre=["trade_routes"], theme=False, reward=["remove_ideas = TU_MIN_pirate_seas", "army_experience = 25"])
f("sea_supremacy", "해상 패권", "Sea Supremacy", pre=["merchant_fleet", "pirate_hunt"])
f("thalassocracy", "해상 패권 제국", "Thalassocracy", pre=["sea_supremacy"], me=["democratic_polis", "rule_of_elders"], cost=15, theme=False,
  available=[AT_LEAST("routes", 5)], reward=[FLAG("path_sea"), "swap_ideas = { remove_idea = TU_MIN_city_states add_idea = TU_MIN_thalassocracy }", EV(30)],
  desc=("바다가 미노스의 영토다. (교역로 5 이상)", "The sea is Minos's territory. (5+ trade routes)"))
f("colonies", "해외 거점", "Overseas Trading Posts", pre=["thalassocracy"])
f("sea_empire", "바다의 제국", "Empire of the Sea", pre=["colonies"], theme=False, reward=[RT(1), "add_political_power = 75"])

# E. 해군
f("galley_fleet", "갤리 함대", "Galley Fleet", pre=["harbour_works"])
f("naval_academy", "해군 학교", "Naval Academy", pre=["galley_fleet"])
f("trireme_doctrine", "삼단노선 교리", "Trireme Naval Doctrine", pre=["naval_academy"])
f("battle_fleet", "전투 함대", "Battle Fleet", pre=["trireme_doctrine"], me=["raider_fleet"])
f("raider_fleet", "통상 파괴 함대", "Raider Fleet", pre=["trireme_doctrine"], me=["battle_fleet"])
f("grand_fleet", "미노스 대함대", "Minoan Grand Fleet", pre=[["battle_fleet", "raider_fleet"]], theme=False, reward=["add_ideas = TU_MIN_grand_fleet", "army_experience = 50"])

# F. 육군
f("hoplite_training", "중장 보병 훈련", "Hoplite Training", pre=["root"])
f("phalanx", "밀집 대형", "Phalanx Tactics", pre=["hoplite_training"])
f("hoplites", "중장 보병", "Hoplite Phalanx", pre=["phalanx"], theme=False, reward=["add_ideas = TU_MIN_hoplites", "army_experience = 30"])
f("city_walls", "도시 성벽", "City Walls", pre=["hoplite_training"])
f("bronze_arms", "청동 무기고", "Bronze Arms Arsenal", pre=["hoplite_training"])
f("modern_rifles", "근대 소총", "Modern Rifle Weapons", pre=["bronze_arms"])
f("artillery", "투석기 포병", "Catapult Artillery", pre=["modern_rifles"])
f("marines", "해병대", "Marine Corps Landing", pre=["phalanx"])

# G. 경제
f("olive_farms", "올리브 농장", "Olive Farms", pre=["root"], econ=True)
f("road_network", "도로망 건설", "Road Network", pre=["olive_farms"], econ="TU_build_infrastructure = yes")
f("industrial_district", "공업 지구", "Industrial District", pre=["olive_farms"], econ=True)
f("civ_program", "민간 공장 계획", "Civilian Factory Program", pre=["industrial_district"], me=["arms_program"], econ=True)
f("arms_program", "군수 공장 계획", "Arms Factory Program", pre=["industrial_district"], me=["civ_program"], econ="TU_build_mil_factory = yes")
f("marble_quarries", "대리석 채석장", "Marble Quarries", pre=["road_network"], econ=True)
f("industrialisation", "미노스 산업화", "Minoan Industrialisation", pre=[["civ_program", "arms_program"], "marble_quarries"], econ=True)

# 보강
for sid, ko, en, pre, econ in (
        ("assembly_hall", "민회당", "Assembly Hall Construction", "agora", True), ("citizen_militia", "시민군", "Citizen Militia", "citizen_rolls", False),
        ("tax_reform", "조세 개혁", "Tax Reform Treasury", "ostracism", False), ("theatre", "원형 극장", "Amphitheatre Festival", "public_speeches", False),
        ("free_press", "자유 연설", "Free Speech Broadcast", "democratic_reform", False), ("elder_guard", "원로 근위", "Elder Guard Regiments", "elders_reform", False),
        ("public_baths", "공중목욕탕", "Public Baths Health", "jury_courts", False), ("sacred_groves", "성스러운 숲", "Sacred Groves Rites", "oracle_priests", False),
        ("pilgrimage", "신탁 순례", "Oracle Pilgrimage Trade", "sacred_games", False), ("olympic_games", "대경기", "The Great Games Festival", "sacred_games", False),
        ("temple_builders", "신전 건축", "Temple Construction", "divine_mandate", True), ("logic", "논리학", "Logic Studies", "philosophers", False),
        ("rhetoric", "수사학", "Rhetoric School", "philosophers", False), ("geometry", "기하학", "Geometry Research", "mathematics", False),
        ("anatomy", "해부학", "Anatomy Medical Research", "medical_studies", False), ("mechanics", "역학", "Mechanics Engineering Design", "engineering_studies", False),
        ("star_charts", "성도", "Star Charts Navigation", "observatory", False), ("lighthouse", "대등대", "Great Lighthouse Harbour", "harbour_works", False),
        ("wine_trade", "포도주 교역", "Wine Trade", "trade_routes", False), ("insurance", "해상 보험", "Maritime Insurance Companies", "merchant_fleet", False),
        ("convoys", "호송 선단", "Convoy Escort Fleet", "pirate_hunt", False), ("naval_bases", "해군 기지", "Naval Base Docks", "naval_academy", "TU_build_civ_factory = yes"),
        ("destroyers", "구축함 전대", "Destroyer Fleet", "battle_fleet", False), ("submarines", "잠수함 전대", "Submarine Fleet", "raider_fleet", False),
        ("cavalry", "기병대", "Cavalry Corps", "phalanx", False), ("archer_corps", "궁수대", "Archer Corps Weapons", "bronze_arms", False),
        ("coastal_forts", "해안 요새", "Coastal Fortresses", "city_walls", False), ("field_medics", "야전 의무대", "Field Medic Corps", "hoplites", False),
        ("pottery", "도기 공방", "Pottery Workshops", "olive_farms", True), ("silver_mines", "은 광산", "Silver Mines", "industrial_district", True),
        ("rail_network", "철도 연결", "Rail Network Expansion", "road_network", "TU_build_infrastructure = yes"), ("shipyards", "조선 산업", "Shipbuilding Industry", "harbour_works", "TU_build_civ_factory = yes"),
        ("power_plants", "발전소", "Power Plants", "rail_network", True), ("sargon_pact", "사르곤 협정", "Sargon Pact", "trade_routes", False),
        ("iberia_ties", "이베리아 교류", "Iberia Exchange", "trade_routes", False), ("laterano_ties", "라테라노 대화", "Laterano Dialogue Exchange", "temple_rites", False),
        ("columbia_trade", "컬럼비아 교역", "Columbia Trade Accord", "merchant_fleet", False), ("league_pact", "동맹 맹약", "League Pact Alliance", "sargon_pact", False),
        ("foreign_academy", "외국 유학생", "Foreign Student Exchange", "great_library", False), ("theatre_arts", "연극제", "Drama Festival", "theatre", False),
        ("road_shrines", "길가 신당", "Roadside Shrines Rites", "road_network", False), ("bronze_foundry", "청동 주조소", "Bronze Foundry", "bronze_arms", "TU_build_mil_factory = yes"),
        ("sea_maps", "해도 제작", "Sea Charts Survey", "galley_fleet", False), ("naval_bombers", "해상 폭격기", "Naval Bombers", "grand_fleet", False),
        ("labyrinth", "미궁 수비대", "Labyrinth Guard Fortress", "city_walls", False)):
    f(sid, ko, en, pre=[pre], econ=econ)

# ------------------------------------------------------------------ 디시전
cat_a = C.category("assembly", "민회", "The Assembly",
                   ("민회 지지를 써서 법안을 통과시킨다.", "Spend assembly support to pass laws."), visible=[HAS("assembly")])
for sid, ko, en, eff, cost_asm in (
        ("law_grain", "곡물 배급법", "Grain Distribution Law", ["add_stability = 0.05"], 10),
        ("law_harbour", "항만 건설법", "Harbour Construction Law", ["TU_build_civ_factory = yes"], 15),
        ("law_walls", "성벽 보수법", "Wall Repair Law", ["TU_build_infrastructure = yes", "army_experience = 10"], 10),
        ("law_schools", "학교법", "Schools Law", ["add_tech_bonus = { name = TU_MIN_law_schools bonus = 0.75 uses = 1 category = electronics category = industry }"], 15),
        ("law_levy", "시민 징집법", "Citizen Levy Law", ["add_manpower = 10000"], 15)):
    C.d(cat_a, sid, ko, en, eff + [ASM(-cost_asm)], cost=25, once=False, days_re_enable=180, available=[AT_LEAST("assembly", cost_asm)],
        desc=("민회 지지 %d을 써서 통과시킨다." % cost_asm, "Pass it by spending %d assembly support." % cost_asm), icon="GFX_decision_generic_political_discourse")
C.d(cat_a, "festival", "시민 축제", "Citizens' Festival", [ASM(10), "add_political_power = -15"], cost=25, once=False, days_re_enable=120)
C.d(cat_a, "elders_decree", "원로 칙령", "Elders' Decree", ["add_political_power = 75", ASM(-10)], cost=0, once=False, days_re_enable=180)

cat_o = C.category("oracle", "신탁", "The Oracle", ("신탁은 180일 동안 길조나 흉조를 내린다.", "The oracle grants a good or bad omen for 180 days."), visible=[HAS("oracle")])
C.d(cat_o, "consult", "신탁을 구하다", "Consult the Oracle", [EV(20)], cost=50, once=False, days_re_enable=200,
    available=["NOT = { has_idea = TU_MIN_good_omen }", "NOT = { has_idea = TU_MIN_bad_omen }", "NOT = { has_idea = TU_MIN_riddle_omen }"],
    icon="GFX_decision_generic_speech")
C.d(cat_o, "offerings", "제물 봉헌", "Make Offerings", [FLAG("offerings"), "add_stability = 0.02"], cost=25, once=False, days_re_enable=200,
    desc=("다음 신탁에서 흉조가 나올 확률이 줄어든다.", "Lowers the chance of a bad omen at the next consultation."))
C.d(cat_o, "cleansing", "정화 의식", "Cleansing Rite", ["remove_ideas = TU_MIN_bad_omen", "add_political_power = -25"], cost=25, once=False,
    days_re_enable=120, available=["has_idea = TU_MIN_bad_omen"])
C.d(cat_o, "games", "대경기 개최", "Hold the Great Games", ["add_war_support = 0.04", ASM(5)], cost=50, once=False, days_re_enable=365,
    visible=["has_completed_focus = TU_MIN_sacred_games"])

cat_s = C.category("sea", "해상 교역", "Sea Trade", icon="GFX_decision_category_generic_industry",
                   desc=("교역로마다 매달 정치력 +0.3. 해적이 교역로를 끊을 수 있다.", "Each route gives +0.3 political power per month. Pirates may cut routes."),
                   visible=[HAS("routes")])
C.d(cat_s, "new_route", "교역로 개척", "Chart a New Route", [RT(1)], cost=50, once=False, days_re_enable=120, available=[AT_MOST("routes", 5)],
    desc=("교역로 +1 (최대 6)", "Trade routes +1 (max 6)"), icon="GFX_decision_generic_naval")
C.d(cat_s, "hunt_pirates", "해적 소탕", "Hunt Pirates", ["army_experience = 15", FLAG("pirates_hunted")], cost=25, once=False, days_re_enable=180,
    desc=("한동안 해적이 교역로를 덜 노린다.", "Pirates target the routes less for a while."), icon="GFX_decision_generic_naval")
C.d(cat_s, "trade_fair", "항구 박람회", "Harbour Trade Fair", ["add_political_power = 50"], cost=0, once=False, days_re_enable=240, available=[AT_LEAST("routes", 3)])
C.d(cat_s, "found_league", "해상 동맹 결성", "Found the Maritime League", ["create_faction = TU_MIN_league"], cost=50,
    visible=["has_completed_focus = TU_MIN_league_pact"], available=["is_in_faction = no"])
C.loc("TU_MIN_league", "해상 동맹", "Maritime League")
C.d(cat_s, "invite_league", "동맹 초청", "Invite to the League", ["add_to_faction = FROM"], cost=50, once=False, days_re_enable=90,
    visible=["has_completed_focus = TU_MIN_league_pact", "is_faction_leader = yes"],
    target=["NOT = { tag = ROOT }", "is_in_faction = no", "NOT = { has_war_with = ROOT }", "OR = { tag = SAR tag = IBE tag = COL tag = LAT }"])

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("다섯 도시의 아침", "Morning of the Five Cities"),
     ("민회 광장에 시민들이 모였다. 신전에서는 사제가 신탁을 준비하고, 항구에서는 상선이 돛을 올린다.",
      "Citizens gather in the assembly square. At the temple a priest prepares the oracle; in the harbour, merchant ships raise sail."),
     [("민회의 뜻대로.", "As the assembly wills.", [ASM(5)], 50), ("바다로.", "To the sea.", [RT(1)], 50)])
C.ev(20, ("신탁", "The Oracle Speaks"),
     ("연기 속에서 무녀가 입을 열었다.", "Through the smoke, the priestess speaks."),
     [("길조다!", "A good omen!", ["trigger = { %s }" % HAS("o_good"), "add_ideas = TU_MIN_good_omen", "clr_country_flag = TU_MIN_o_good", EV(21, 180)], 1),
      ("흉조다...", "A bad omen...", ["trigger = { %s }" % HAS("o_bad"), "add_ideas = TU_MIN_bad_omen", "clr_country_flag = TU_MIN_o_bad", EV(21, 180)], 1),
      ("알 수 없는 수수께끼다.", "An unreadable riddle.", ["trigger = { %s }" % HAS("o_riddle"), "add_ideas = TU_MIN_riddle_omen", "clr_country_flag = TU_MIN_o_riddle", EV(21, 180)], 1)],
     immediate=["random_list = {", "\t45 = { %s }" % FLAG("o_good"),
                "\t30 = { modifier = { factor = 0.4 %s } %s }" % (HAS("offerings"), FLAG("o_bad")),
                "\t25 = { %s }" % FLAG("o_riddle"), "}", "clr_country_flag = TU_MIN_offerings"])
C.ev(21, ("신탁의 끝", "The Omen Fades"), ("신탁의 기운이 사라졌다.", "The omen's power has faded."),
     [("다시 신탁을 구할 때다.", "Time to consult again.", ["if = { limit = { has_idea = TU_MIN_good_omen } remove_ideas = TU_MIN_good_omen }",
                                                       "if = { limit = { has_idea = TU_MIN_bad_omen } remove_ideas = TU_MIN_bad_omen }",
                                                       "if = { limit = { has_idea = TU_MIN_riddle_omen } remove_ideas = TU_MIN_riddle_omen }"], 1)])
C.ev(22, ("해적의 습격", "Pirate Raid"), ("해적이 교역로 하나를 끊었다.", "Pirates have severed one of our trade routes."),
     [("손실을 받아들인다.", "Accept the loss.", [RT(-1)], 50), ("호위대를 보낸다.", "Send the guards.", ["army_experience = 10", "add_political_power = -25"], 50)],
     trigger=["original_tag = MIN", AT_LEAST("routes", 2), "NOT = { %s }" % HAS("pirates_hunted")], mtth=150, fire_once=False)
C.ev(23, ("철학자들의 논쟁", "The Philosophers Debate"), ("광장에서 철학자들의 논쟁이 사흘째 이어진다.", "The philosophers' debate in the square enters its third day."),
     [("끝까지 듣는다.", "Hear it out.", ["add_tech_bonus = { name = TU_MIN_debate bonus = 0.5 uses = 1 category = electronics }"], 50),
      ("해산시킨다.", "Disperse them.", ["add_political_power = 25", ASM(-5)], 50)],
     trigger=["original_tag = MIN", "has_completed_focus = TU_MIN_philosophers"], mtth=300)
C.ev(24, ("도편 추방 투표", "The Ostracism Vote"), ("시민들이 너무 강해진 정치인 하나를 추방하자고 투표했다.", "The citizens vote to exile an overly powerful politician."),
     [("민회의 뜻을 따른다.", "Respect the vote.", [ASM(10), "add_political_power = -25"], 60), ("투표를 무효로 한다.", "Annul the vote.", [ASM(-15), "add_political_power = 50"], 40)],
     trigger=["original_tag = MIN", "has_completed_focus = TU_MIN_ostracism"], mtth=360)
C.ev(25, ("대경기의 영웅", "Hero of the Games"), ("한 젊은 선수가 대경기에서 모든 종목을 휩쓸었다.", "A young athlete swept every event at the Great Games."),
     [("영웅을 기린다.", "Honour the hero.", ["add_war_support = 0.03", ASM(5)], 1)], trigger=["original_tag = MIN", "has_completed_focus = TU_MIN_sacred_games"], mtth=360)
C.ev(26, ("상선의 귀환", "Return of the Merchant Fleet"), ("먼 항해에서 돌아온 상선이 진귀한 물건을 가득 실었다.", "Merchant ships returned from a long voyage, laden with rare goods."),
     [("시장에 푼다.", "Sell them at market.", ["add_political_power = 40"], 1)], trigger=["original_tag = MIN", AT_LEAST("routes", 3)], mtth=200)
C.ev(27, ("원로와 시민의 충돌", "Elders Clash with Citizens"), ("원로들이 민회의 결정을 뒤집으려 하자 시민들이 광장을 채웠다.", "When the elders tried to overturn the assembly, citizens filled the square."),
     [("시민 편을 든다.", "Side with the citizens.", [ASM(10), "add_stability = -0.02"], 50), ("원로 편을 든다.", "Side with the elders.", [ASM(-10), "add_stability = 0.02"], 50)],
     trigger=["original_tag = MIN", "has_completed_focus = TU_MIN_agora"], mtth=300)
C.ev(28, ("민주 폴리스", "Democratic Polis"), ("미노스는 시민의 나라가 되었다.", "Minos has become a nation of citizens."), [("민회 만세.", "Long live the assembly.", [ASM(10)], 1)])
C.ev(29, ("원로 정체", "Rule of the Elders"), ("원로들이 미노스를 맡았다.", "The elders have taken charge of Minos."), [("지혜를 따르라.", "Follow wisdom.", ["add_stability = 0.05"], 1)])
C.ev(30, ("해상 패권", "Thalassocracy"), ("미노스의 배가 닿지 않는 바다는 없다.", "There is no sea Minos's ships do not reach."), [("바다의 주인.", "Masters of the sea.", [RT(1)], 1)])
C.ev(31, ("폭풍", "Storm at Sea"), ("큰 폭풍이 상선 여러 척을 삼켰다.", "A great storm swallowed several merchant ships."),
     [("애도한다.", "Mourn them.", ["add_political_power = -20"], 1)], trigger=["original_tag = MIN", AT_LEAST("routes", 1)], mtth=400)
C.ev(32, ("신전의 기적", "Miracle at the Temple"), ("신전의 성화가 저절로 타올랐다.", "The temple's sacred flame lit itself."),
     [("신이 함께한다.", "The gods are with us.", ["add_stability = 0.03"], 1)], trigger=["original_tag = MIN", "has_completed_focus = TU_MIN_temple_rites"], mtth=400)
C.ev(33, ("외국 유학생", "Foreign Students"), ("여러 나라의 학생들이 미노스의 학당을 찾았다.", "Students from many nations have come to Minos's schools."),
     [("받아들인다.", "Welcome them.", ["add_political_power = 25", "add_tech_bonus = { name = TU_MIN_students bonus = 0.5 uses = 1 category = industry }"], 1)],
     trigger=["original_tag = MIN", "has_completed_focus = TU_MIN_great_library"], mtth=300)

for sid, ko, en, pre, econ in (
        ("assembly_guard", "민회 경비대", "Assembly Guard Regiments", "assembly_hall", False), ("grain_ships", "곡물선", "Grain Ship Trade", "wine_trade", False),
        ("elder_wisdom", "원로의 지혜", "Wisdom of the Elders Studies", "elder_council", False), ("temple_banks", "신전 은행", "Temple Bank", "temple_treasury", False),
        ("oracle_guard", "신탁 수호대", "Oracle Guard Regiments", "prophecy_archive", False), ("music_school", "음악 학교", "Music School Education", "theatre_arts", False),
        ("astronomy", "천문학", "Astronomy Research", "star_charts", False), ("hospitals", "의술의 전당", "Hall of Healing Hospitals", "anatomy", False),
        ("siege_engines", "공성 기계", "Siege Engine Artillery", "mechanics", False), ("trade_colonies", "교역 식민지", "Trade Colony Posts", "colonies", False),
        ("naval_guns", "함포", "Naval Guns", "destroyers", False), ("cruisers", "순양함 전대", "Cruiser Fleet", "naval_academy", False),
        ("light_infantry", "경보병", "Light Infantry Regiments", "phalanx", False), ("mountain_passes", "산길 요새", "Mountain Pass Forts", "coastal_forts", False),
        ("textile_mills", "직물 공장", "Textile Mills", "pottery", True), ("steel_works", "제철소", "Steel Works", "silver_mines", True),
        ("harbour_cranes", "항만 기중기", "Harbour Crane Construction", "lighthouse", True)):
    f(sid, ko, en, pre=[pre], econ=econ)
C.d(cat_a, "law_harbours", "항만법", "Harbour Law", ["TU_build_infrastructure = yes", RT(1), ASM(-15)], cost=25, once=False, days_re_enable=240,
    available=[AT_LEAST("assembly", 15), AT_MOST("routes", 5)], icon="GFX_decision_generic_construction")
C.d(cat_a, "rhetoric_contest", "웅변 대회", "Rhetoric Contest", [ASM(5), "add_political_power = 15"], cost=10, once=False, days_re_enable=120)
C.d(cat_o, "temple_tithe", "신전 헌금", "Temple Tithe", ["add_political_power = 60"], cost=0, once=False, days_re_enable=240)
C.d(cat_s, "caravan_escort", "상단 호위대 파견", "Dispatch Caravan Guards", ["army_experience = 20", FLAG("pirates_hunted")], cost=50, once=False, days_re_enable=240,
    visible=["has_completed_focus = TU_MIN_convoys"])
C.ev(34, ("해적의 투항", "Pirates Surrender"), ("해적 한 무리가 투항하며 미노스 군에 들어오기를 청했다.", "A pirate band surrendered and asked to join Minos's army."),
     [("받아들인다.", "Accept.", ["army_experience = 25", "add_manpower = 2000"], 1)], trigger=["original_tag = MIN", "has_completed_focus = TU_MIN_pirate_hunt"], mtth=300)

# ------------------------------------------------------------------ 리워크 (사양서 27): 해군 갈래 자리에 육상 교역로 · 팔랑크스 · 학문 · 공방
f("overland_routes", "육상 교역로 개척", "Open Overland Trade Roads", pre=["root"], reward=[RT(1)])
f("caravan_guilds", "상단 길드", "Caravan Guilds", pre=["overland_routes"])
f("inland_markets", "내륙 시장 도시", "Inland Market Towns", pre=["caravan_guilds"], econ=True)
f("landship_merchants", "육상함 상단", "Landship Merchant Houses", pre=["caravan_guilds"], reward=[RT(1)])
f("landship_escorts", "육상함 호위대", "Landship Escort Corps", pre=["landship_merchants"])
f("sargon_road", "사르곤 가도", "The Sargon Road", pre=["landship_merchants"], reward=[RT(1)])
f("trade_league", "교역 동맹 헌장", "Trade League Charter", pre=["sargon_road", "inland_markets"], cost=15, reward=[RT(1)])
f("market_city", "이동 시장 도시", "Market Mobile City", pre=["trade_league"], cost=15)
f("phalanx_drill", "팔랑크스 훈련", "Phalanx Drill", pre=["hoplite_training"])
f("citizen_levies", "시민 징집", "Hoplite Levies", pre=["phalanx_drill"])
f("bronze_forges", "청동 대장간", "Bronze Forges", pre=["phalanx_drill"])
f("aspis_tactics", "아스피스 방패 전술", "Aspis Shield Tactics", pre=["citizen_levies", "bronze_forges"])
f("polis_walls", "폴리스 성벽", "Polis Walls", pre=["aspis_tactics"])
f("strategos_academy", "스트라테고스 학당", "Strategos Academy", pre=["aspis_tactics"], cost=15)
f("arts_lyceum", "아츠 리케이온", "Arts Lyceum Research", pre=["philosophers"])
f("arts_archive", "아츠 기록 보관소", "Arts Archive Records", pre=["arts_lyceum"], cost=15)
f("originium_physics", "원석 자연학", "Originium Natural Philosophy", pre=["arts_lyceum"])
f("oracle_informants", "신탁의 정보원", "Oracle Informants", pre=["temple_rites"])
f("olive_oil_works", "올리브유 압착소", "Olive Oil Works", pre=["olive_farms"], econ=True)
f("sculptor_workshops", "조각가 공방", "Sculptor Workshops", pre=["olive_oil_works"], econ=True)
f("amphora_workshops", "암포라 공방", "Amphora Workshops", pre=["olive_oil_works"], econ=True)
f("agora_markets", "아고라 시장", "Agora Markets", pre=["agora"])

if __name__ == "__main__":
    C.write()
