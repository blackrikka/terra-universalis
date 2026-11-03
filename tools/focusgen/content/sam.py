#!/usr/bin/env python3
"""사미(SAM) 고유 콘텐츠 (사양서 17).

장치
  1. 숲의 은총 TU_SAM_grace (0~100, 시작 50): 매달 +1 (숲의 의례 +1), 계약한 정령마다 -1, 벌목권을 주면 -1 (on_monthly).
     20 미만이면 '숲의 분노' 이벤트(반복). 의례·제물 디시전으로 올리고, 벌목·개발 디시전으로 내린다.
  2. 정령과의 계약: 곰(방어)·늑대(공격)·까마귀(연구)·순록(보급) 정령. 은총 20 이상에서 계약, 동시에 최대 둘.
     계약은 국민정신으로 남고 매달 은총을 먹는다. 계약을 끊을 수 있다.
  3. 바깥 세계: 우르수스 개척민·카시미어 상인 이벤트, 접촉 정도 TU_SAM_contact (0~100).
정치 결말 셋 (서로 배타): 숲의 신정(은총 80) / 사미 부족 연방(부족 회의 3) / 열린 사미(접촉 60).

실행: python -I tools/focusgen/content/sam.py && python -I tools/focusgen/merge_focus.py --tag SAM
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_lib import Country  # noqa: E402

C = Country("SAM", "사미", "Sami")
f = C.f
MAXV = {"grace": 100, "contact": 100, "councils": 3, "pacts": 2}
NAMES = {"grace": ("§G숲의 은총§!", "§GForest Grace§!"), "contact": ("§Y바깥과의 접촉§!", "§YOutside Contact§!"),
         "councils": ("§Y부족 회의§!", "§YTribal Councils§!"), "pacts": ("§Y정령 계약§!", "§YSpirit Pacts§!")}
SPIRITS = [("bear", "곰", "Bear", {"army_defence_factor": 0.1, "max_dig_in": 1}, "generic_fortify_the_borders"),
           ("wolf", "늑대", "Wolf", {"army_attack_factor": 0.08, "army_speed_factor": 0.05}, "generic_army_europe_1"),
           ("raven", "까마귀", "Raven", {"research_speed_factor": 0.05, "political_power_gain": 0.05}, "generic_research_bonus"),
           ("reindeer", "순록", "Reindeer", {"supply_consumption_factor": -0.15, "attrition": -0.1}, "generic_supply_line")]


def V(var, n):
    name = "TU_SAM_%s_%s%d" % (var, "m" if n < 0 else "", abs(n))
    if not any(e.startswith(name + " =") for e in C.effects):
        C.effects.append("""%s = {
	custom_effect_tooltip = %s_tt
	hidden_effect = {
		add_to_variable = { TU_SAM_%s = %d }
		clamp_variable = { var = TU_SAM_%s min = 0 max = %d }
	}
}""" % (name, name, var, n, var, MAXV[var]))
        ko, en = NAMES[var]
        C.loc(name + "_tt", "%s %s%d" % (ko, "+" if n > 0 else "", n), "%s %s%d" % (en, "+" if n > 0 else "", n))
    return "%s = yes" % name


def GR(n):
    return V("grace", n)


def CON(n):
    return V("contact", n)


def AT_LEAST(var, n):
    return "check_variable = { TU_SAM_%s > %d }" % (var, n - 1)


def AT_MOST(var, n):
    return "check_variable = { TU_SAM_%s < %d }" % (var, n + 1)


def FLAG(x):
    return "set_country_flag = TU_SAM_%s" % x


def HAS(x):
    return "has_country_flag = TU_SAM_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_sam_ev.%d%s }" % (n, " days = %d" % days if days else "")


C.history += ["set_variable = { TU_SAM_grace = 50 }", "set_variable = { TU_SAM_contact = 10 }", "set_variable = { TU_SAM_councils = 0 }",
              "set_variable = { TU_SAM_pacts = 0 }", "add_ideas = { TU_SAM_sacred_forest TU_SAM_scattered_tribes }"]
C.effects.append("""TU_SAM_monthly = {
	add_to_variable = { TU_SAM_grace = 1 }
	if = { limit = { has_country_flag = TU_SAM_rites } add_to_variable = { TU_SAM_grace = 1 } }
	subtract_from_variable = { TU_SAM_grace = TU_SAM_pacts }
	if = { limit = { has_country_flag = TU_SAM_logging } add_to_variable = { TU_SAM_grace = -1 } }
	clamp_variable = { var = TU_SAM_grace min = 0 max = 100 }
}""")
C.on_actions.append("""on_monthly = {
	effect = {
		if = {
			limit = { original_tag = SAM }
			TU_SAM_monthly = yes
		}
	}
}""")

# ------------------------------------------------------------------ 국민정신
for sid, ko, en, mods, pic, desc in (
        ("sacred_forest", "성스러운 숲", "The Sacred Forest", {"army_defence_factor": 0.05, "production_speed_buildings_factor": -0.1}, "generic_morale_bonus",
         ("숲은 사미를 지키지만, 나무 한 그루 베는 것도 허락을 받아야 한다.", "The forest shields Sami, but even a single tree needs permission to fell.")),
        ("scattered_tribes", "흩어진 부족", "Scattered Tribes", {"political_power_gain": -0.1, "conscription_factor": -0.1}, "generic_local_self_management",
         ("부족들은 저마다의 숲에서 산다.", "Each tribe lives in its own woods.")),
        ("forest_theocracy", "숲의 신정", "Forest Theocracy", {"stability_factor": 0.15, "army_defence_factor": 0.1, "war_support_factor": 0.05}, "generic_political_support", ("", "")),
        ("tribal_federation", "사미 부족 연방", "Sami Tribal Federation", {"conscription_factor": 0.1, "political_power_gain": 0.1, "army_org_factor": 0.05}, "generic_pp_unity_bonus", ("", "")),
        ("open_sami", "열린 사미", "Open Sami", {"research_speed_factor": 0.05, "production_speed_buildings_factor": 0.1}, "generic_foreign_capital", ("", "")),
        ("spirit_warriors", "정령 전사", "Spirit Warriors", {"army_attack_factor": 0.05, "army_morale_factor": 0.08}, "generic_army_war_college", ("", "")),
        ("forest_wrath", "숲의 분노", "Wrath of the Forest", {"stability_factor": -0.1, "attrition": 0.05}, "generic_army_problems",
         ("은총을 잃은 숲이 사미를 외면한다. 은총이 40 이상이 되면 사라진다.", "The graceless forest has turned from Sami. Lifts when grace reaches 40.")),
):
    C.idea(sid, ko, en, mods, pic, desc)
for k, ko, en, mods, pic in SPIRITS:
    C.idea("spirit_%s" % k, "%s 정령과의 계약" % ko, "Pact with the %s Spirit" % en, mods, pic,
           ("%s 정령이 사미와 함께한다. 매달 숲의 은총 -1." % ko, "The %s spirit walks with Sami. Forest grace -1 per month." % en))

# ------------------------------------------------------------------ 중점
f("root", "숲의 수호자", "Guardians of the Forest", cost=5, theme=False, reward=["add_political_power = 50", EV(1)],
  desc=("눈과 숲의 땅. 무녀들은 정령의 목소리를 듣고, 부족들은 숲의 허락 아래 산다.",
        "A land of snow and forest. The shamans hear the spirits; the tribes live by the forest's leave."))

# A. 숲과 정령
f("forest_rites", "성스러운 숲의 의례", "Sacred Forest Rites", pre=["root"], theme=False, reward=[FLAG("rites"), GR(10), FLAG("spirits")],
  desc=("숲의 은총이 매달 더 오른다. '정령' 디시전이 열린다.", "Forest grace grows faster each month. Unlocks the Spirit decisions."))
f("shaman_council", "무녀 회의", "Shaman Council", pre=["forest_rites"], reward=[GR(5)])
f("spirit_lore", "정령의 전승", "Spirit Lore Studies", pre=["forest_rites"])
f("spirit_arts", "정령 아츠 연구", "Spirit Arts Research", pre=["spirit_lore"])
f("ice_arts", "얼음 아츠", "Ice Arts Research", pre=["spirit_arts"], me=["forest_arts"])
f("forest_arts", "숲의 아츠", "Forest Arts Research", pre=["spirit_arts"], me=["ice_arts"])
f("great_rite", "대의례", "The Great Rite", pre=[["ice_arts", "forest_arts"], "shaman_council"], theme=False, reward=[GR(20)])
f("forest_theocracy", "숲의 신정", "Forest Theocracy", pre=["great_rite"], me=["tribal_federation", "open_sami"], cost=15, theme=False,
  available=[AT_LEAST("grace", 80)], reward=[FLAG("path_forest"), "swap_ideas = { remove_idea = TU_SAM_scattered_tribes add_idea = TU_SAM_forest_theocracy }", EV(28)],
  desc=("무녀들이 숲의 뜻으로 다스린다. (숲의 은총 80 이상)", "The shamans rule by the forest's will. (Forest grace 80+)"))
f("world_tree", "세계수의 축복", "Blessing of the World Tree", pre=["forest_theocracy"])
f("spirit_guard", "정령 수호대", "Spirit Guard Regiments", pre=["forest_theocracy"])

# B. 부족
f("tribal_gathering", "부족 회합", "Tribal Gathering", pre=["root"], theme=False, reward=[FLAG("tribes")],
  desc=("'부족 회의' 디시전이 열린다.", "Unlocks the Tribal Council decisions."))
f("reindeer_herders", "순록 목동", "Reindeer Herders Farms", pre=["tribal_gathering"], econ=True)
f("tribal_law", "부족 법", "Tribal Law Codex", pre=["tribal_gathering"])
f("tribal_federation_charter", "부족 연합 헌장", "Sami Tribal Federation Charter", pre=["tribal_law", "reindeer_herders"])
f("tribal_federation", "사미 부족 연방", "Sami Tribal Federation", pre=["tribal_federation_charter"], me=["forest_theocracy", "open_sami"], cost=15, theme=False,
  available=[AT_LEAST("councils", 3)], reward=[FLAG("path_tribes"), "swap_ideas = { remove_idea = TU_SAM_scattered_tribes add_idea = TU_SAM_tribal_federation }", EV(29)],
  desc=("모든 부족이 하나의 연방이 된다. (부족 회의 3번)", "All tribes become one federation. (3 tribal councils)"))
f("federal_hunters", "연방 사냥꾼단", "Federal Hunter Regiments", pre=["tribal_federation"])
f("winter_roads", "겨울 썰매길", "Winter Sled Roads", pre=["tribal_federation"], econ="TU_build_infrastructure = yes")

# C. 바깥 세계
f("open_contact", "바깥과의 접촉", "Open Contact", pre=["root"], theme=False, reward=[CON(10), FLAG("outside")],
  desc=("'바깥 세계' 디시전이 열린다.", "Unlocks the Outside World decisions."))
f("trading_posts", "교역소", "Trading Posts", pre=["open_contact"], reward=[CON(5)])
f("fur_trade", "모피 교역", "Fur Trade", pre=["trading_posts"], reward=[CON(5)])
f("foreign_teachers", "외국 교사", "Foreign Teachers Education", pre=["trading_posts"], reward=[CON(10)])
f("open_sami", "열린 사미", "Open Sami", pre=["fur_trade", "foreign_teachers"], me=["forest_theocracy", "tribal_federation"], cost=15, theme=False,
  available=[AT_LEAST("contact", 60)], reward=[FLAG("path_open"), "swap_ideas = { remove_idea = TU_SAM_sacred_forest add_idea = TU_SAM_open_sami }", EV(30)],
  desc=("사미는 숲 밖으로 나간다. (바깥과의 접촉 60 이상)", "Sami steps out of the forest. (Outside contact 60+)"))
f("railway_north", "북방 철도", "Northern Railway", pre=["open_sami"], econ="TU_build_infrastructure = yes")
f("research_slot", "사미 학교", "Sami School of Sciences", pre=["open_sami"], theme=False, reward=["add_research_slot = 1"], desc=("연구 슬롯 +1", "Research slot +1"))

# D. 군사
f("snow_hunters", "설원 사냥꾼", "Snowfield Hunters", pre=["root"])
f("ski_raiders", "스키 기습대", "Ski Raid Squads", pre=["snow_hunters"])
f("ambush_tactics", "숲 매복 전술", "Forest Ambush Tactics", pre=["snow_hunters"])
f("snow_forts", "설원 요새", "Snow Fortresses", pre=["ambush_tactics"], me=["mobile_hunters"])
f("mobile_hunters", "기동 사냥꾼", "Mobile Hunters", pre=["ambush_tactics"], me=["snow_forts"])
f("bow_smiths", "활 장인", "Bow Smiths", pre=["ski_raiders"])
f("spirit_warriors", "정령 전사단", "Elite Spirit Warriors", pre=[["snow_forts", "mobile_hunters"], "bow_smiths"], theme=False,
  reward=["add_ideas = TU_SAM_spirit_warriors", "army_experience = 30"])
f("ursus_watch", "우르수스 경계", "Ursus Border Watch", pre=["snow_hunters"])

# E. 경제
f("timber", "목재 산업", "Timber Industry", pre=["root"], econ=True, reward=[GR(-5)])
f("road_network", "도로망 건설", "Road Network", pre=["timber"], econ="TU_build_infrastructure = yes")
f("industrial_district", "공업 지구", "Industrial District", pre=["timber"], econ=True, reward=[GR(-5)])
f("civ_program", "민간 공장 계획", "Civilian Factory Program", pre=["industrial_district"], me=["arms_program"], econ=True)
f("arms_program", "군수 공장 계획", "Arms Factory Program", pre=["industrial_district"], me=["civ_program"], econ="TU_build_mil_factory = yes")
f("industrialisation", "사미 산업", "Sami Industry", pre=[["civ_program", "arms_program"], "road_network"], econ=True)

# 보강
for sid, ko, en, pre, econ in (
        ("drum_rites", "북의 의례", "Drum Rites", "shaman_council", False), ("spirit_stones", "정령석", "Spirit Stones Research", "spirit_lore", False),
        ("herbal_medicine", "약초 의술", "Herbal Medicine", "spirit_lore", False), ("ancient_runestones", "고대 비석", "Ancient Runestones Studies", "spirit_arts", False),
        ("aurora_watch", "오로라 관측", "Aurora Observatory", "ice_arts", False), ("tree_shrines", "나무 신당", "Tree Shrine Rites", "forest_arts", False),
        ("shaman_schools", "무녀 학교", "Shaman Schools", "great_rite", False), ("sacred_groves", "성림 보호", "Sacred Grove Protection", "world_tree", False),
        ("spirit_pilgrimage", "정령 순례", "Spirit Pilgrimage", "world_tree", False), ("reindeer_cavalry", "순록 기병", "Reindeer Cavalry", "reindeer_herders", False),
        ("tribal_courts", "부족 법정", "Tribal Courts Reform", "tribal_law", False), ("clan_feasts", "씨족 잔치", "Clan Feast Festival", "tribal_gathering", False),
        ("elder_council", "장로 회의", "Elders' Council", "tribal_law", False), ("federal_markets", "연방 시장", "Federal Markets Trade", "federal_hunters", False),
        ("tribal_messengers", "부족 전령", "Tribal Messenger Network", "tribal_gathering", False), ("kazimierz_merchants", "카시미어 상인", "Kazimierz Merchants Trade", "trading_posts", False),
        ("ursus_settlers", "우르수스 개척민", "Ursus Settlers Question", "open_contact", False), ("translators", "통역사", "Translators Exchange", "foreign_teachers", False),
        ("foreign_medicine", "외국 의약", "Foreign Medicine Clinics", "foreign_teachers", False), ("steam_sleds", "증기 썰매", "Steam Sled Motorised", "railway_north", False),
        ("kjerag_ties", "쉐라그 교류", "Kjerag Exchange", "open_contact", False), ("leithanien_ties", "라이타니엔 교류", "Leithanien Exchange", "kjerag_ties", False),
        ("snow_camouflage", "설상 위장", "Snow Camouflage Tactics", "ski_raiders", False), ("trap_lines", "덫 사냥 전술", "Trap Line Tactics", "ambush_tactics", False),
        ("ice_bunkers", "얼음 벙커", "Ice Bunker Fortifications", "snow_forts", False), ("ski_cavalry", "스키 기동대", "Ski Mobile Troops", "mobile_hunters", False),
        ("rifle_trade", "소총 교역", "Rifle Weapons Trade", "bow_smiths", False), ("field_shamans", "야전 무녀", "Field Shaman Medics", "spirit_warriors", False),
        ("border_scouts", "국경 정찰대", "Border Scouts", "ursus_watch", False), ("winter_war", "겨울 전쟁 교리", "Winter War Doctrine", "spirit_warriors", False),
        ("fishing_villages", "어촌", "Fishing Villages", "timber", True), ("iron_mines", "철광산", "Iron Mines", "industrial_district", True),
        ("sawmills", "제재소", "Sawmills", "timber", True), ("fur_workshops", "모피 공방", "Fur Workshops", "fur_trade", True),
        ("hydro_power", "수력 발전", "Hydro Power Plants", "road_network", True), ("rail_network", "철도 연결", "Rail Network Expansion", "road_network", "TU_build_infrastructure = yes"),
        ("steel_works", "제철소", "Steel Works", "iron_mines", True), ("air_scouts", "설원 비행대", "Snowfield Air Scouts", "winter_war", False),
        ("forest_rangers", "숲 순찰대", "Forest Ranger Watch", "ambush_tactics", False), ("spirit_festival", "정령 축제", "Spirit Festival", "drum_rites", False),
        ("snow_shelters", "눈 대피소", "Snow Shelter Housing", "winter_roads", False), ("chemical_works", "화학 공업", "Chemical Works Industry", "steel_works", True),
        ("power_lines", "송전선", "Power Line Network", "hydro_power", True), ("ursus_treaty", "우르수스 조약", "Ursus Treaty", "ursus_settlers", False),
        ("northern_alliance", "북방 동맹", "Northern Alliance Pact", "leithanien_ties", False)):
    f(sid, ko, en, pre=[pre], econ=econ)

# ------------------------------------------------------------------ 디시전
cat_sp = C.category("spirits", "정령", "The Spirits",
                    ("정령과 계약하면 국민정신을 얻지만 매달 숲의 은총 -1. 동시에 둘까지. 은총이 20 아래면 숲이 분노한다.",
                     "A spirit pact grants a national spirit but costs 1 forest grace a month. Two at most. Below 20 grace the forest grows wrathful."),
                    visible=[HAS("spirits")])
for k, ko, en, mods, pic in SPIRITS:
    C.d(cat_sp, "pact_%s" % k, "%s 정령과 계약" % ko, "Pact with the %s Spirit" % en,
        ["add_ideas = TU_SAM_spirit_%s" % k, V("pacts", 1), GR(-10)], cost=50, once=False, days_re_enable=60,
        available=[AT_LEAST("grace", 20), AT_MOST("pacts", 1), "NOT = { has_idea = TU_SAM_spirit_%s }" % k],
        desc=("숲의 은총 20 이상, 계약 1개 이하. 은총 -10", "Grace 20+, at most one other pact. Grace -10"), icon="GFX_decision_generic_speech")
    C.d(cat_sp, "break_%s" % k, "%s 정령과의 계약 해지" % ko, "End the %s Pact" % en,
        ["remove_ideas = TU_SAM_spirit_%s" % k, V("pacts", -1), "add_stability = -0.02"], cost=0, once=False, days_re_enable=30,
        visible=["has_idea = TU_SAM_spirit_%s" % k])
C.d(cat_sp, "offerings", "숲에 제물", "Offerings to the Forest", [GR(10)], cost=25, once=False, days_re_enable=90, icon="GFX_decision_generic_speech")
C.d(cat_sp, "great_offering", "대제사", "The Great Offering", [GR(25), "add_stability = 0.03"], cost=75, once=False, days_re_enable=365)

cat_t = C.category("tribes", "부족 회의", "Tribal Councils", visible=[HAS("tribes")])
C.d(cat_t, "tribal_council", "부족 회의 소집", "Convene a Tribal Council", [V("councils", 1), "add_political_power = 25"], cost=50, once=False,
    days_re_enable=180, available=[AT_MOST("councils", 2)], desc=("부족 회의 +1 (3번이면 부족 연방 결말)", "Tribal councils +1 (3 for the federation ending)"))
C.d(cat_t, "tribal_levy", "부족 징집", "Tribal Levy", ["add_manpower = 8000"], cost=25, once=False, days_re_enable=180)
C.d(cat_t, "reindeer_tribute", "순록 공물", "Reindeer Tribute", ["add_political_power = 50"], cost=0, once=False, days_re_enable=180)
C.d(cat_t, "hunting_season", "사냥철 축제", "Hunting Season Festival", ["add_war_support = 0.03", "army_experience = 10"], cost=25, once=False, days_re_enable=240)

cat_o = C.category("outside", "바깥 세계", "The Outside World", icon="GFX_decision_category_generic_foreign_policy", visible=[HAS("outside")])
C.d(cat_o, "logging_rights", "벌목권 판매", "Sell Logging Rights", ["add_political_power = 75", FLAG("logging"), CON(5)], cost=0, once=False,
    days_re_enable=240, desc=("정치력 +75. 이후 숲의 은총이 매달 1씩 덜 오른다.", "+75 political power. Forest grace then grows 1 less per month."))
C.d(cat_o, "stop_logging", "벌목 금지", "Ban Logging", ["clr_country_flag = TU_SAM_logging", GR(5)], cost=25, once=False, days_re_enable=120,
    visible=[HAS("logging")])
C.d(cat_o, "foreign_factory", "외국 공장 유치", "Invite a Foreign Factory", ["TU_build_civ_factory = yes", CON(10), GR(-10)], cost=50, once=False,
    days_re_enable=240, icon="GFX_decision_generic_factory")
C.d(cat_o, "found_alliance", "북방 동맹 결성", "Found the Northern Alliance", ["create_faction = TU_SAM_alliance"], cost=50,
    visible=["has_completed_focus = TU_SAM_northern_alliance"], available=["is_in_faction = no"])
C.loc("TU_SAM_alliance", "북방 동맹", "Northern Alliance")

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("숲의 목소리", "Voice of the Forest"),
     ("무녀가 숲에서 돌아와 말했다. 정령들이 바깥 사람들의 발소리를 듣고 있다고.",
      "A shaman returns from the forest: the spirits can hear the footsteps of outsiders."),
     [("숲을 지킨다.", "We guard the forest.", [GR(5)], 50), ("바깥을 살펴본다.", "We look outside.", [CON(5)], 50)])
C.ev(20, ("숲의 분노", "Wrath of the Forest"),
     ("눈보라가 그치지 않고, 사냥감이 사라졌다. 무녀들은 숲이 화났다고 한다.",
      "The blizzard will not stop and game has vanished. The shamans say the forest is angry."),
     [("제물을 바친다.", "Make offerings.", [GR(10), "add_political_power = -30"], 50),
      ("견딘다.", "Endure.", ["add_ideas = TU_SAM_forest_wrath"], 50)],
     trigger=["original_tag = SAM", AT_MOST("grace", 19), "NOT = { has_idea = TU_SAM_forest_wrath }"], mtth=60, fire_once=False,
     picture="GFX_report_event_generic_defensive_preparations")
C.ev(21, ("숲이 누그러지다", "The Forest Relents"), ("숲의 은총이 돌아오자 눈보라가 걷혔다.", "As grace returned, the blizzard lifted."),
     [("감사를.", "Give thanks.", ["remove_ideas = TU_SAM_forest_wrath"], 1)],
     trigger=["original_tag = SAM", "has_idea = TU_SAM_forest_wrath", AT_LEAST("grace", 40)], mtth=20, fire_once=False)
C.ev(22, ("우르수스 개척민", "Ursus Settlers"), ("우르수스 개척민들이 숲 가장자리에 마을을 세웠다.", "Ursus settlers have built a village at the forest's edge."),
     [("쫓아낸다.", "Drive them out.", ["army_experience = 10", GR(5)], 40), ("교역한다.", "Trade with them.", [CON(10), "add_political_power = 25"], 40),
      ("숲에 맡긴다.", "Leave them to the forest.", [GR(-5)], 20)],
     trigger=["original_tag = SAM", "has_completed_focus = TU_SAM_ursus_watch"], mtth=200)
C.ev(23, ("카시미어 상인", "Kazimierz Merchants"), ("카시미어 상인들이 모피를 사러 왔다.", "Kazimierz merchants have come to buy furs."),
     [("판다.", "Sell.", ["add_political_power = 40", CON(5)], 1)], trigger=["original_tag = SAM", HAS("outside")], mtth=240)
C.ev(24, ("정령의 출현", "A Spirit Appears"), ("거대한 정령이 마을 앞에 나타났다가 사라졌다.", "A great spirit appeared before a village and vanished."),
     [("길조다.", "A good sign.", [GR(10), "add_stability = 0.03"], 1)], trigger=["original_tag = SAM", AT_LEAST("grace", 60)], mtth=300)
C.ev(25, ("부족 간 다툼", "Tribal Feud"), ("두 부족이 사냥터를 두고 다툰다.", "Two tribes feud over hunting grounds."),
     [("중재한다.", "Mediate.", ["add_political_power = -20", "add_stability = 0.02"], 60), ("내버려 둔다.", "Stay out of it.", ["add_stability = -0.03"], 40)],
     trigger=["original_tag = SAM", "has_idea = TU_SAM_scattered_tribes"], mtth=240)
C.ev(26, ("극야", "The Polar Night"), ("해가 뜨지 않는 겨울이 왔다. 무녀들은 오로라 아래서 의례를 연다.", "The sunless winter has come. Shamans perform rites beneath the aurora."),
     [("의례에 참여한다.", "Join the rites.", [GR(5), "add_stability = 0.02"], 1)], trigger=["original_tag = SAM"], mtth=365, fire_once=False)
C.ev(27, ("외국 학자의 방문", "A Foreign Scholar"), ("외국 학자가 정령 아츠를 배우고 싶어 한다.", "A foreign scholar wishes to learn spirit Arts."),
     [("가르친다.", "Teach.", [CON(5), "add_tech_bonus = { name = TU_SAM_scholar bonus = 0.5 uses = 1 category = electronics }"], 50),
      ("거절한다.", "Refuse.", [GR(3)], 50)], trigger=["original_tag = SAM", "has_completed_focus = TU_SAM_spirit_arts"], mtth=300)
C.ev(28, ("숲의 신정", "Forest Theocracy"), ("무녀들이 사미를 이끈다.", "The shamans lead Sami."), [("숲의 뜻대로.", "As the forest wills.", [GR(10)], 1)])
C.ev(29, ("사미 부족 연방", "Sami Tribal Federation"), ("모든 부족이 한자리에 모였다.", "All the tribes have gathered as one."), [("하나의 사미.", "One Sami.", ["add_manpower = 10000"], 1)])
C.ev(30, ("열린 사미", "Open Sami"), ("사미의 젊은이들이 바깥 세계로 떠난다.", "Sami's young set out into the outside world."), [("세상을 향해.", "To the world.", [CON(10)], 1)])
C.ev(31, ("늑대 무리의 습격", "Wolf Pack Attack"), ("굶주린 늑대 무리가 순록 떼를 덮쳤다.", "A starving wolf pack fell on the reindeer herds."),
     [("사냥꾼을 보낸다.", "Send hunters.", ["army_experience = 10"], 1)], trigger=["original_tag = SAM", "has_completed_focus = TU_SAM_reindeer_herders"], mtth=300)
C.ev(32, ("숲에서 길을 잃은 군대", "An Army Lost in the Forest"), ("숲에 들어온 외국 부대가 길을 잃고 헤매다 돌아갔다.", "A foreign unit that entered the forest got lost and turned back."),
     [("숲이 지켜 주었다.", "The forest protected us.", [GR(5), "add_war_support = 0.03"], 1)], trigger=["original_tag = SAM", "has_war = yes", AT_LEAST("grace", 50)], mtth=120)

for sid, ko, en, pre, econ in (
        ("bear_totem", "곰 토템", "Bear Totem Rites", "drum_rites", False), ("wolf_totem", "늑대 토템", "Wolf Totem Rites", "drum_rites", False),
        ("raven_totem", "까마귀 토템", "Raven Totem Studies", "spirit_stones", False), ("reindeer_totem", "순록 토템", "Reindeer Totem Rites", "herbal_medicine", False),
        ("dream_walkers", "꿈 걷는 이", "Dream Walker Studies", "ancient_runestones", False), ("frost_shield", "서리 방벽", "Frost Shield Fortifications", "aurora_watch", False),
        ("living_walls", "살아 있는 숲 장벽", "Living Forest Walls", "tree_shrines", False), ("shaman_army", "무녀 부대", "Shaman Corps Regiments", "shaman_schools", False),
        ("sacred_springs", "성스러운 샘", "Sacred Springs Health", "sacred_groves", False), ("spirit_messengers", "정령 전령", "Spirit Messenger Network", "spirit_pilgrimage", False),
        ("reindeer_sleds", "순록 썰매대", "Reindeer Sled Supply", "reindeer_cavalry", False), ("tribal_banners", "부족 깃발", "Tribal Banners Propaganda", "clan_feasts", False),
        ("elders_wisdom", "장로의 지혜", "Elders' Wisdom Studies", "elder_council", False), ("federal_assembly", "연방 의회", "Federal Assembly Council", "federal_markets", False),
        ("message_drums", "전령 북", "Message Drum Signal", "tribal_messengers", False), ("federal_army", "연방군", "Federal Army Regiments", "federal_hunters", False),
        ("merchant_lodges", "상인 숙소", "Merchant Lodges Trade", "kazimierz_merchants", False), ("settler_treaty", "개척민 협약", "Settler Treaty", "ursus_settlers", False),
        ("foreign_schools", "외국 학교", "Foreign Schools Education", "translators", False), ("vaccines", "광석병 예방", "Oripathy Prevention Medical", "foreign_medicine", False),
        ("northern_ports", "북방 항구", "Northern Ports Harbour", "railway_north", "TU_build_dockyard = yes"), ("snow_ambush", "눈 속 매복", "Snow Ambush Tactics", "trap_lines", False),
        ("ice_fortress", "빙하 요새", "Glacier Fortress Line", "ice_bunkers", False), ("hunter_marksmen", "명사수 사냥꾼", "Hunter Marksman Training", "rifle_trade", False),
        ("frost_artillery", "설원 포병", "Snowfield Artillery", "rifle_trade", False), ("motor_sleds", "동력 썰매", "Motor Sled Units", "ski_cavalry", False),
        ("arctic_doctrine", "극지 교리", "Arctic Warfare Doctrine", "winter_war", False), ("bomber_scouts", "설원 폭격대", "Snowfield Bomber Wing", "air_scouts", False),
        ("resin_works", "송진 공방", "Resin Works Industry", "sawmills", True), ("amber_trade", "호박 교역", "Amber Trade", "fur_workshops", False),
        ("salmon_canneries", "연어 통조림", "Salmon Cannery Factories", "fishing_villages", True), ("copper_mines", "구리 광산", "Copper Mines", "iron_mines", True),
        ("timber_rail", "목재 철도", "Timber Railway", "rail_network", "TU_build_infrastructure = yes"), ("paper_mills", "제지 공장", "Paper Mills", "sawmills", True),
        ("power_stations", "발전소", "Power Stations", "power_lines", True), ("laterano_contact", "라테라노 접촉", "Laterano Contact Envoys", "translators", False)):
    f(sid, ko, en, pre=[pre], econ=econ)
C.d(cat_t, "elders_judgement", "장로의 판결", "Judgement of the Elders", ["add_stability = 0.04"], cost=25, once=False, days_re_enable=180,
    visible=["has_completed_focus = TU_SAM_elder_council"])
C.d(cat_o, "fur_auction", "모피 경매", "Fur Auction", ["add_political_power = 50", CON(3)], cost=0, once=False, days_re_enable=180,
    visible=["has_completed_focus = TU_SAM_fur_trade"])
C.ev(33, ("오로라의 계시", "Revelation of the Aurora"), ("무녀가 오로라 속에서 미래를 보았다고 한다.", "A shaman says she saw the future in the aurora."),
     [("귀 기울인다.", "Listen.", [GR(5), "add_political_power = 25"], 1)], trigger=["original_tag = SAM", "has_completed_focus = TU_SAM_aurora_watch"], mtth=300)
C.ev(34, ("눈사태", "Avalanche"), ("눈사태가 사냥꾼 마을을 덮쳤다.", "An avalanche buried a hunters' village."),
     [("구조대를 보낸다.", "Send rescuers.", ["add_political_power = -20", "add_stability = 0.02"], 60), ("숲의 뜻이다.", "It is the forest's will.", [GR(3), "add_manpower = -2000"], 40)],
     trigger=["original_tag = SAM"], mtth=500)

if __name__ == "__main__":
    C.write()
