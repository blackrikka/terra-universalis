#!/usr/bin/env python3
"""극동(HIG) 고유 콘텐츠 (사양서 17).

장치
  1. 개항장 TU_HIG_ports (0~4): '개항' 디시전으로 항구를 하나씩 연다. 연 항구마다 매달 정치력 +0.5 (on_monthly)와
     외세 영향 +2. 쇄국 디시전으로 다시 닫을 수 있다.
  2. 외세 영향 TU_HIG_foreign (0~100): 개항·외국 고문·기술 도입으로 오르고, 쇄국·무사도로 내려간다.
     60 이상이면 '존왕양이' 봉기 이벤트(반복). 천황 친정 결말의 열쇠.
  3. 닌자 TU_HIG_shinobi (0~10): 양성 디시전으로 늘리고, 대상 디시전(기술 탈취·공작·첩보)에 2씩 쓴다.
정치 결말 셋 (서로 배타): 쇼군의 막부(개항장 1 이하) / 개국 극동(개항장 3 이상) / 천황 친정(존왕양이 사슬).

실행: python -I tools/focusgen/content/hig.py && python -I tools/focusgen/merge_focus.py --tag HIG
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_lib import Country  # noqa: E402

C = Country("HIG", "극동", "Far East")
f = C.f
MAXV = {"ports": 4, "foreign": 100, "shinobi": 10}
NAMES = {"ports": ("§Y개항장§!", "§YTreaty Ports§!"), "foreign": ("§R외세 영향§!", "§RForeign Influence§!"),
         "shinobi": ("§G닌자§!", "§GShinobi§!")}


def V(var, n):
    name = "TU_HIG_%s_%s%d" % (var, "m" if n < 0 else "", abs(n))
    if not any(e.startswith(name + " =") for e in C.effects):
        C.effects.append("""%s = {
	custom_effect_tooltip = %s_tt
	hidden_effect = {
		add_to_variable = { TU_HIG_%s = %d }
		clamp_variable = { var = TU_HIG_%s min = 0 max = %d }
	}
}""" % (name, name, var, n, var, MAXV[var]))
        ko, en = NAMES[var]
        C.loc(name + "_tt", "%s %s%d" % (ko, "+" if n > 0 else "", n), "%s %s%d" % (en, "+" if n > 0 else "", n))
    return "%s = yes" % name


def FOR(n):
    return V("foreign", n)


def NIN(n):
    return V("shinobi", n)


def AT_LEAST(var, n):
    return "check_variable = { TU_HIG_%s > %d }" % (var, n - 1)


def AT_MOST(var, n):
    return "check_variable = { TU_HIG_%s < %d }" % (var, n + 1)


def FLAG(x):
    return "set_country_flag = TU_HIG_%s" % x


def HAS(x):
    return "has_country_flag = TU_HIG_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_hig_ev.%d%s }" % (n, " days = %d" % days if days else "")


C.history += ["set_variable = { TU_HIG_ports = 0 }", "set_variable = { TU_HIG_foreign = 10 }", "set_variable = { TU_HIG_shinobi = 2 }",
              "add_ideas = { TU_HIG_seclusion TU_HIG_samurai_class }"]
C.effects.append("""TU_HIG_monthly = {
	if = { limit = { check_variable = { TU_HIG_ports > 0 } } add_political_power = 0.5 }
	if = { limit = { check_variable = { TU_HIG_ports > 1 } } add_political_power = 0.5 }
	if = { limit = { check_variable = { TU_HIG_ports > 2 } } add_political_power = 0.5 }
	if = { limit = { check_variable = { TU_HIG_ports > 3 } } add_political_power = 0.5 }
	set_temp_variable = { tu_hig_fi = TU_HIG_ports }
	multiply_temp_variable = { tu_hig_fi = 2 }
	add_to_variable = { TU_HIG_foreign = tu_hig_fi }
	clamp_variable = { var = TU_HIG_foreign min = 0 max = 100 }
}""")
C.on_actions.append("""on_monthly = {
	effect = {
		if = {
			limit = { original_tag = HIG }
			TU_HIG_monthly = yes
		}
	}
}""")

# ------------------------------------------------------------------ 국민정신
C.idea("seclusion", "쇄국", "Seclusion", {"stability_factor": 0.05, "research_speed_factor": -0.05, "consumer_goods_factor": 0.02}, "generic_secret_police",
       ("극동은 오랫동안 문을 닫아 왔다.", "The Far East has kept its doors closed for a long time."))
C.idea("samurai_class", "무사 계급", "Samurai Class", {"army_org_factor": 0.05, "political_power_gain": -0.05}, "generic_army_war_college",
       ("칼을 찬 무사들이 나라의 기둥이자 짐이다.", "The sword-bearing samurai are both pillar and burden of the nation."))
C.idea("open_harbours", "열린 항구", "Open Harbours", {"research_speed_factor": 0.03, "consumer_goods_factor": -0.02}, "generic_foreign_capital")
C.idea("shogunate", "쇼군의 막부", "The Shogunate", {"stability_factor": 0.1, "army_org_factor": 0.05, "war_support_factor": 0.05}, "generic_central_management")
C.idea("open_far_east", "개국 극동", "The Opened Far East", {"research_speed_factor": 0.07, "production_factory_max_efficiency_factor": 0.05}, "generic_foreign_capital")
C.idea("imperial_restoration", "천황 친정", "Imperial Restoration", {"political_power_gain": 0.15, "war_support_factor": 0.1, "conscription_factor": 0.05},
       "generic_political_support")
C.idea("bushido", "무사도", "Bushido", {"army_morale_factor": 0.08, "army_attack_factor": 0.03}, "generic_morale_bonus")
C.idea("shinobi_network", "그림자 조직", "Shadow Network", {"political_power_gain": 0.05, "stability_factor": 0.03}, "generic_intel_bonus")
C.idea("modern_army", "근대 육군", "Modern Army", {"army_attack_factor": 0.05, "army_org_factor": 0.03}, "generic_army_europe_1")

# ------------------------------------------------------------------ 중점
f("root", "극동 조정 회의", "Far East Court Assembly", cost=5, theme=False, reward=["add_political_power = 50", EV(1)],
  desc=("바다 끝 섬나라. 쇼군의 막부가 문을 닫고 있지만, 바깥 배들은 점점 가까이 온다.",
        "An island nation at the edge of the sea. The shogunate keeps its doors shut, but foreign ships draw ever closer."))

# A. 쇼군 (쇄국)
f("shogun_council", "막부 회의", "Shogunate Council", pre=["root"])
f("daimyo_council", "다이묘 회의", "Daimyo Council Reform", pre=["shogun_council"])
f("border_checks", "국경 검문", "Border Inspection Watchposts", pre=["shogun_council"], reward=[FOR(-5)])
f("isolation_edict", "쇄국령", "Isolation Edict", pre=["border_checks"], theme=False, reward=[FOR(-10), FLAG("close")],
  desc=("'항구 폐쇄' 디시전이 열린다.", "Unlocks the Close a Port decision."))
f("alternate_attendance", "참근교대", "Alternate Attendance System", pre=["daimyo_council"])
f("domain_control", "번 통제", "Domain Control Administration", pre=["alternate_attendance", "isolation_edict"])
f("shogunate", "쇼군의 막부", "The Shogunate", pre=["domain_control"], me=["open_far_east", "imperial_restoration"], cost=15, theme=False,
  available=[AT_MOST("ports", 1)], reward=[FLAG("path_shogun"), "add_ideas = TU_HIG_shogunate", EV(28)],
  desc=("막부가 나라를 굳게 지킨다. (개항장 1곳 이하)", "The shogunate holds the nation firmly. (1 or fewer treaty ports)"))
f("castle_towns", "성하 마을", "Castle Towns Construction", pre=["shogunate"], econ=True)
f("hatamoto", "하타모토 친위대", "Hatamoto Guard Regiments", pre=["shogunate"])
f("eternal_shogunate", "영원한 막부", "The Eternal Shogunate", pre=["castle_towns", "hatamoto"], theme=False, reward=["add_stability = 0.1", "add_political_power = 75"])

# B. 개항
f("foreign_ships", "흑선의 내항", "Arrival of the Black Ships", pre=["root"], theme=False, reward=[EV(20), FLAG("ports"), FOR(5)],
  desc=("'개항' 디시전이 열린다.", "Unlocks the Open a Port decision."))
f("open_harbours", "개항", "Open the Harbours", pre=["foreign_ships"], theme=False, reward=["remove_ideas = TU_HIG_seclusion", "add_ideas = TU_HIG_open_harbours", FOR(10)])
f("foreign_advisors", "외국인 고문", "Foreign Advisors", pre=["open_harbours"], reward=[FOR(5)])
f("western_studies", "서양 학문", "Western Studies Research", pre=["foreign_advisors"], reward=[FOR(5)])
f("trade_treaties", "통상 조약", "Trade Treaties", pre=["open_harbours"], reward=[FOR(5)])
f("modern_schools", "근대 학교", "Modern Schools", pre=["western_studies"])
f("open_far_east", "개국 극동", "The Opened Far East", pre=["modern_schools", "trade_treaties"], me=["shogunate", "imperial_restoration"],
  cost=15, theme=False, available=[AT_LEAST("ports", 3)], reward=[FLAG("path_open"), "add_ideas = TU_HIG_open_far_east", EV(29)],
  desc=("극동이 세계로 나아간다. (개항장 3곳 이상)", "The Far East steps out into the world. (3+ treaty ports)"))
f("industrial_cities", "공업 도시", "Industrial Cities", pre=["open_far_east"], econ=True)
f("research_slot", "제국 대학", "Imperial University Research", pre=["open_far_east"], theme=False, reward=["add_research_slot = 1"],
  desc=("연구 슬롯 +1", "Research slot +1"))
f("world_expo", "만국 박람회", "World Exposition Trade", pre=["industrial_cities"])

# C. 존왕양이 / 천황
f("imperial_court", "천황의 조정", "The Imperial Court", pre=["root"])
f("court_nobles", "공가", "Court Nobles Council", pre=["imperial_court"])
f("expel_barbarians", "존왕양이", "Revere the Emperor, Expel the Barbarians", pre=["court_nobles"], theme=False, reward=[EV(21), FOR(-5)])
f("loyalist_samurai", "근왕 무사", "Loyalist Samurai Regiments", pre=["expel_barbarians"])
f("imperial_edict", "왕정 복고 칙서", "Edict of Restoration", pre=["loyalist_samurai"], theme=False, reward=[FLAG("restoration_ready")])
f("imperial_restoration", "천황 친정", "Imperial Restoration", pre=["imperial_edict"], me=["shogunate", "open_far_east"], cost=15, theme=False,
  available=[HAS("restoration_ready"), HAS("uprising_won")], reward=[FLAG("path_emperor"), "add_ideas = TU_HIG_imperial_restoration", EV(30)],
  desc=("천황이 직접 다스린다. (존왕양이 봉기를 겪고 승리해야 함)", "The emperor rules in person. (Requires an expel-the-barbarians uprising to be won)"))
f("new_capital", "새 수도", "A New Capital Construction", pre=["imperial_restoration"], econ=True)
f("imperial_army", "황군", "Imperial Army Regiments", pre=["imperial_restoration"])
f("rich_nation", "부국강병", "Rich Nation, Strong Army", pre=["new_capital", "imperial_army"], theme=False,
  reward=["TU_build_mil_factory = yes", "TU_build_civ_factory = yes"])

# D. 닌자
f("shinobi_villages", "닌자 마을", "Shinobi Villages", pre=["root"], theme=False, reward=[NIN(2), FLAG("shinobi")],
  desc=("'그림자 작전' 디시전이 열린다.", "Unlocks the Shadow Operations decisions."))
f("shinobi_training", "닌자 수련", "Shinobi Training", pre=["shinobi_villages"], reward=[NIN(1)])
f("courier_network", "비밀 연락망", "Secret Courier Network", pre=["shinobi_villages"])
f("shadow_network", "그림자 조직", "Shadow Network", pre=["shinobi_training", "courier_network"], theme=False,
  reward=["add_ideas = TU_HIG_shinobi_network", NIN(2)])
f("shinobi_masters", "닌자 두령", "Shinobi Masters", pre=["shadow_network"], reward=[NIN(2)])

# E. 군사
f("samurai_regiments", "무사단", "Samurai Regiments", pre=["root"])
f("swordsmanship", "검술 훈련", "Swordsmanship Drill", pre=["samurai_regiments"])
f("bushido", "무사도", "Bushido Spirit", pre=["swordsmanship"], theme=False, reward=["add_ideas = TU_HIG_bushido", FOR(-5)])
f("raid_tactics", "기습 전술", "Raid Tactics", pre=["bushido"], me=["defensive_tactics"])
f("defensive_tactics", "수비 전술", "Defensive Tactics", pre=["bushido"], me=["raid_tactics"])
f("mountain_castles", "산성 축조", "Mountain Fortresses", pre=["samurai_regiments"])
f("artillery_battalions", "포병 대대", "Artillery Battalions", pre=["mountain_castles"])
f("rifle_corps", "소총대", "Rifle Weapons Corps", pre=["samurai_regiments"])
f("modern_army", "근대 육군", "Modern Army Reform", pre=[["raid_tactics", "defensive_tactics"], "rifle_corps"], theme=False,
  reward=["swap_ideas = { remove_idea = TU_HIG_samurai_class add_idea = TU_HIG_modern_army }", "army_experience = 40"])

# F. 해군
f("fishing_ports", "어항 정비", "Fishing Port Upgrade", pre=["root"])
f("coastal_fleet", "연안 함대", "Coastal Fleet", pre=["fishing_ports"])
f("naval_academy", "해군 학교", "Naval Academy", pre=["coastal_fleet"])
f("cruiser_fleet", "순양함 함대", "Cruiser Fleet", pre=["naval_academy"], me=["submarine_fleet"])
f("submarine_fleet", "잠수함 함대", "Submarine Fleet", pre=["naval_academy"], me=["cruiser_fleet"])
f("combined_fleet", "연합 함대", "Combined Fleet", pre=[["cruiser_fleet", "submarine_fleet"]], theme=False,
  reward=["add_ideas = TU_HIG_combined_fleet", "army_experience = 50"])
f("dockyards", "조선소", "Dockyards", pre=["coastal_fleet"], econ="TU_build_civ_factory = yes")
f("naval_aviation", "해군 항공대", "Naval Aviation", pre=["combined_fleet"])

# G. 경제
f("rice_harvest", "쌀 수확", "Rice Harvest", pre=["root"], econ=True)
f("road_network", "도로망 건설", "Road Network", pre=["rice_harvest"], econ="TU_build_infrastructure = yes")
f("industrial_district", "공업 지구", "Industrial District", pre=["rice_harvest"], econ=True)
f("civ_program", "민간 공장 계획", "Civilian Factory Program", pre=["industrial_district"], me=["arms_program"], econ=True)
f("arms_program", "군수 공장 계획", "Arms Factory Program", pre=["industrial_district"], me=["civ_program"], econ="TU_build_mil_factory = yes")
f("rail_network", "철도 연결", "Rail Network Expansion", pre=["road_network"], econ="TU_build_infrastructure = yes")
f("silk_mills", "제사 공장", "Silk Mills", pre=["rail_network"], econ=True)
f("industrialisation", "극동 산업화", "Far East Industrialisation", pre=[["civ_program", "arms_program"], "silk_mills"], econ=True)

# 보강
for sid, ko, en, pre, econ in (
        ("tea_ceremony", "다도", "Tea Ceremony Festival", "shogun_council", False),
        ("sword_hunt", "칼 사냥", "Sword Hunt Security", "domain_control", False),
        ("rice_tax", "연공미", "Rice Tax Treasury", "daimyo_council", False),
        ("ninja_guards", "막부 밀정", "Shogunate Spies Network", "isolation_edict", False),
        ("dutch_quarter", "외국인 거류지", "Foreign Settlement District", "open_harbours", True),
        ("telegraph", "전신망", "Telegraph Network Signal", "foreign_advisors", False),
        ("mint_reform", "화폐 개혁", "Currency Reform", "trade_treaties", False),
        ("railway_line", "첫 철도", "First Railway Line", "trade_treaties", True),
        ("military_academy", "육군 사관학교", "Military Academy", "modern_schools", False),
        ("national_shrine", "국가 신사", "National Shrine Rites", "court_nobles", False),
        ("imperial_seal", "옥새", "Imperial Seal Propaganda", "imperial_court", False),
        ("restoration_war", "보신 전쟁 준비", "Restoration War Plans", "loyalist_samurai", False),
        ("poison_studies", "독약 연구", "Poison Studies Research", "shinobi_training", False),
        ("smoke_bombs", "연막탄", "Smoke Bomb Equipment", "shinobi_training", False),
        ("infiltrators", "침투조", "Infiltrator Squads", "courier_network", False),
        ("spy_school", "첩보 학교", "Spy School Intelligence", "shinobi_masters", False),
        ("archers", "궁병대", "Archer Regiments", "swordsmanship", False),
        ("cavalry", "기마대", "Cavalry Corps", "raid_tactics", False),
        ("castle_cannons", "성 대포", "Castle Cannon Artillery", "artillery_battalions", False),
        ("field_medics", "야전 의무대", "Field Medic Corps", "rifle_corps", False),
        ("tank_trials", "전차 시험", "Tank Trials Armour", "modern_army", False),
        ("air_corps", "육군 항공대", "Army Air Corps", "modern_army", False),
        ("destroyers", "구축함 전대", "Destroyer Fleet", "naval_academy", False),
        ("carrier_plans", "항공모함 계획", "Carrier Fleet Plans", "naval_aviation", False),
        ("marine_corps", "해병대", "Marine Corps Landing", "coastal_fleet", False),
        ("coastal_batteries", "해안 포대", "Coastal Battery Forts", "fishing_ports", False),
        ("whaling", "포경업", "Whaling Industry", "fishing_ports", True),
        ("porcelain", "도자기 공방", "Porcelain Workshops", "rice_harvest", True),
        ("coal_mines", "탄광", "Coal Mines", "industrial_district", True),
        ("steel_works", "제철소", "Steel Works", "coal_mines", True),
        ("shipbuilding", "조선 산업", "Shipbuilding Docks", "rail_network", "TU_build_civ_factory = yes"),
        ("yan_relations", "염국 관계", "Yan Relations Envoys", "foreign_ships", False),
        ("lungmen_trade", "용문 교역", "Lungmen Trade Accord", "yan_relations", False),
        ("rhodes_contact", "로도스 아일랜드 접촉", "Rhodes Island Contact Pact", "foreign_ships", False),
        ("columbia_treaty", "컬럼비아 조약", "Columbia Treaty", "trade_treaties", False),
        ("asian_league", "동방 연맹", "Eastern League Alliance", "lungmen_trade", False)):
    f(sid, ko, en, pre=[pre], econ=econ)

# ------------------------------------------------------------------ 디시전
cat_p = C.category("ports", "개항과 쇄국", "Ports and Seclusion",
                   ("연 항구마다 매달 정치력 +0.5, 외세 영향 +2. 외세 영향이 60을 넘으면 존왕양이 봉기가 일어난다.",
                    "Each open port gives +0.5 political power and +2 foreign influence per month. Above 60 influence, loyalist uprisings break out."),
                   visible=["OR = {", "\t" + HAS("ports"), "\t" + HAS("close"), "}"])
C.d(cat_p, "open_port", "항구 개항", "Open a Port", [V("ports", 1), "TU_build_civ_factory = yes", FOR(5)], cost=50, once=False,
    days_re_enable=120, visible=[HAS("ports")], available=[AT_MOST("ports", 3)],
    desc=("개항장 +1 (최대 4), 민간 공장, 외세 영향 +5", "Treaty ports +1 (max 4), a civilian factory, foreign influence +5"), icon="GFX_decision_generic_naval")
C.d(cat_p, "close_port", "항구 폐쇄", "Close a Port", [V("ports", -1), FOR(-10), "add_stability = 0.02"], cost=25, once=False,
    days_re_enable=120, visible=[HAS("close")], available=[AT_LEAST("ports", 1)])
C.d(cat_p, "foreign_tech", "외국 기술 도입", "Import Foreign Technology",
    ["add_tech_bonus = { name = TU_HIG_foreign_tech bonus = 0.75 uses = 1 category = industry category = electronics }", FOR(10)], cost=50,
    once=False, days_re_enable=180, available=[AT_LEAST("ports", 1)])
C.d(cat_p, "expel_foreigners", "외국인 추방", "Expel the Foreigners", [FOR(-20), "add_stability = 0.03", "add_political_power = -25"], cost=25,
    once=False, days_re_enable=240, available=[AT_LEAST("foreign", 20)])
C.d(cat_p, "foreign_loans", "외국 차관", "Foreign Loans", ["TU_build_civ_factory = yes", FOR(10)], cost=50, once=False, days_re_enable=240,
    available=[AT_LEAST("ports", 2)], icon="GFX_decision_generic_factory")
C.d(cat_p, "harbour_festival", "항구 축제", "Harbour Festival", ["add_stability = 0.03", "add_political_power = 25"], cost=25, once=False,
    days_re_enable=240, available=[AT_LEAST("ports", 1)])

cat_s = C.category("shinobi", "그림자 작전", "Shadow Operations", icon="GFX_decision_category_military_operation",
                   desc=("닌자를 양성하고, 다른 나라에 작전을 편다. 작전마다 닌자 2가 든다.", "Train shinobi and run operations abroad. Each operation costs 2 shinobi."),
                   visible=[HAS("shinobi")])
C.d(cat_s, "train_shinobi", "닌자 양성", "Train Shinobi", [NIN(1)], cost=25, once=False, days_re_enable=60, available=[AT_MOST("shinobi", 9)],
    icon="GFX_decision_generic_intelligence_operation")
TGT = ["NOT = { tag = ROOT }", "exists = yes", "NOT = { tag = WLD }"]
C.d(cat_s, "steal_tech", "기술 탈취", "Steal Technology",
    ["add_tech_bonus = { name = TU_HIG_steal_tech bonus = 1.0 uses = 1 category = industry category = electronics category = infantry_weapons }", NIN(-2)],
    cost=25, once=False, days_re_enable=120, available=[AT_LEAST("shinobi", 2)], target=TGT, icon="GFX_decision_generic_intelligence_operation",
    desc=("대상 나라의 기술을 훔친다. 닌자 -2", "Steal the target's technology. Shinobi -2"))
C.d(cat_s, "sabotage", "공작", "Sabotage", ["FROM = { add_stability = -0.05 add_political_power = -50 }", NIN(-2)], cost=50, once=False,
    days_re_enable=180, available=[AT_LEAST("shinobi", 2)], target=TGT + ["NOT = { has_war_with = ROOT }"],
    icon="GFX_decision_generic_intelligence_operation", desc=("대상 나라의 안정도 -5%, 정치력 -50. 닌자 -2", "Target loses 5% stability and 50 political power. Shinobi -2"))
C.d(cat_s, "spy_war_plans", "작전 계획 염탐", "Spy on War Plans", ["army_experience = 25", NIN(-2)], cost=25, once=False, days_re_enable=120,
    available=[AT_LEAST("shinobi", 2), "has_war = yes"], target=TGT + ["has_war_with = ROOT"], icon="GFX_decision_generic_intelligence_operation")
C.d(cat_s, "domestic_watch", "국내 감시", "Domestic Surveillance", ["add_stability = 0.04", FOR(-5), NIN(-1)], cost=25, once=False,
    days_re_enable=180, available=[AT_LEAST("shinobi", 1)])
C.d(cat_s, "shinobi_raid", "닌자 기습", "Shinobi Raid", ["army_experience = 15", "add_war_support = 0.02", NIN(-2)], cost=25, once=False,
    days_re_enable=120, available=[AT_LEAST("shinobi", 2), "has_war = yes"])

cat_c = C.category("court", "조정과 막부", "Court and Shogunate")
C.d(cat_c, "daimyo_levy", "다이묘 징병", "Daimyo Levy", ["add_manpower = 10000", "add_stability = -0.02"], cost=25, once=False, days_re_enable=180)
C.d(cat_c, "samurai_stipend", "무사 녹봉", "Samurai Stipends", ["add_stability = 0.04", "add_political_power = -25"], cost=0, once=False, days_re_enable=180)
C.d(cat_c, "imperial_audience", "천황 알현", "Imperial Audience", ["add_political_power = 50", FOR(-5)], cost=25, once=False, days_re_enable=240)
C.d(cat_c, "found_league", "동방 연맹 결성", "Found the Eastern League", ["create_faction = TU_HIG_league"], cost=50,
    visible=["has_completed_focus = TU_HIG_asian_league"], available=["is_in_faction = no"])
C.loc("TU_HIG_league", "동방 연맹", "Eastern League")

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("바다 끝 섬나라", "The Island at the Edge of the Sea"),
     ("막부의 성 위로 벚꽃이 흩날린다. 수평선 너머로 낯선 연기가 보였다는 소문이 돈다.",
      "Cherry blossoms drift over the shogun's castle. Rumour speaks of strange smoke beyond the horizon."),
     [("문은 닫혀 있다.", "The door stays shut.", [FOR(-5)], 50), ("밖을 내다볼 때다.", "Time to look outside.", [FOR(5)], 50)])
C.ev(20, ("흑선의 내항", "Arrival of the Black Ships"),
     ("검은 연기를 뿜는 외국 함선들이 항구 앞에 닻을 내렸다. 그들은 개항을 요구한다.",
      "Foreign ships belching black smoke have anchored before the harbour. They demand we open our ports."),
     [("개항을 받아들인다.", "Accept.", [V("ports", 1), FOR(10)], 50), ("시간을 번다.", "Stall for time.", ["add_political_power = 25"], 50)],
     picture="GFX_report_event_generic_sign_treaty1")
C.ev(21, ("존왕양이", "Revere the Emperor"),
     ("젊은 무사들이 '천황을 받들고 오랑캐를 물리치자'고 외친다.", "Young samurai cry: 'Revere the emperor, expel the barbarians!'"),
     [("그들의 뜻에 공감한다.", "Sympathise with them.", [FOR(-10), FLAG("loyalists")], 50), ("단속한다.", "Suppress them.", ["add_stability = 0.02"], 50)])
C.ev(22, ("존왕양이 봉기", "Loyalist Uprising"),
     ("외세에 분노한 무사들이 외국인 거류지를 습격하고 막부를 규탄한다.", "Samurai enraged by foreign influence attack the foreign quarter and denounce the shogunate."),
     [("봉기를 진압한다.", "Crush the uprising.", ["add_stability = -0.03", "army_experience = 15", FOR(-10)], 40),
      ("봉기에 합류한다.", "Join the uprising.", [FLAG("uprising_won"), FOR(-25), "add_stability = -0.05"], 30),
      ("외국인을 내보낸다.", "Send the foreigners away.", [V("ports", -1), FOR(-15)], 30)],
     trigger=["original_tag = HIG", AT_LEAST("foreign", 60)], mtth=90, fire_once=False, picture="GFX_report_event_generic_riot")
C.ev(23, ("외국 상인의 선물", "Gifts from Foreign Merchants"), ("외국 상인들이 신기한 기계를 선물했다.", "Foreign merchants present curious machines as gifts."),
     [("연구한다.", "Study them.", ["add_tech_bonus = { name = TU_HIG_gifts bonus = 0.5 uses = 1 category = industry }", FOR(5)], 1)],
     trigger=["original_tag = HIG", AT_LEAST("ports", 1)], mtth=240)
C.ev(24, ("닌자의 배신", "A Shinobi Betrays"), ("닌자 하나가 외국에 비밀을 팔아넘겼다.", "A shinobi sold our secrets abroad."),
     [("추적해 처단한다.", "Hunt him down.", [NIN(-1), "add_stability = 0.02"], 60), ("조직을 재편한다.", "Reorganise the network.", ["add_political_power = -25"], 40)],
     trigger=["original_tag = HIG", AT_LEAST("shinobi", 6)], mtth=300)
C.ev(25, ("무사의 실업", "Unemployed Samurai"), ("녹봉을 잃은 무사들이 거리에서 떠돈다.", "Samurai who lost their stipends wander the streets."),
     [("군대에 받아들인다.", "Take them into the army.", ["add_manpower = 5000", "add_political_power = -15"], 60), ("방치한다.", "Leave them.", ["add_stability = -0.03"], 40)],
     trigger=["original_tag = HIG", "has_completed_focus = TU_HIG_modern_army"], mtth=300)
C.ev(26, ("지진", "Earthquake"), ("큰 지진이 수도를 흔들었다.", "A great earthquake shook the capital."),
     [("복구에 나선다.", "Begin relief.", ["add_political_power = -40", "add_stability = 0.02"], 1)], trigger=["original_tag = HIG"], mtth=720)
C.ev(27, ("외국인 거류지의 소동", "Trouble in the Foreign Quarter"), ("술 취한 외국 선원들이 마을 사람들과 싸움을 벌였다.", "Drunken foreign sailors brawled with townspeople."),
     [("외국 영사에게 항의한다.", "Protest to the consul.", ["add_stability = 0.02"], 50), ("조용히 넘어간다.", "Let it pass.", [FOR(5)], 50)],
     trigger=["original_tag = HIG", AT_LEAST("ports", 2)], mtth=200)
C.ev(28, ("쇼군의 막부", "The Shogunate"), ("막부가 다시 굳건해졌다.", "The shogunate stands firm once more."),
     [("막부 만세.", "Long live the shogunate.", ["add_stability = 0.05"], 1)])
C.ev(29, ("개국 극동", "The Opened Far East"), ("극동이 세계의 일원이 되었다.", "The Far East has joined the world."),
     [("앞으로.", "Onward.", ["add_political_power = 50"], 1)])
C.ev(30, ("천황 친정", "Imperial Restoration"), ("쇼군이 대정을 천황에게 돌려주었다.", "The shogun has returned rule to the emperor."),
     [("천황 폐하 만세.", "Long live the emperor.", ["add_war_support = 0.05"], 1)])

# 추가 (목표 분량)
for sid, ko, en, pre, econ in (
        ("shogun_guard", "쇼군 근위", "Shogun Guard Regiments", "hatamoto", False),
        ("edo_markets", "성하 시장", "Castle Town Markets", "castle_towns", False),
        ("closed_country_navy", "해금 순시선", "Coastal Patrol Fleet", "isolation_edict", False),
        ("han_schools", "번교", "Domain Schools Education", "alternate_attendance", False),
        ("foreign_doctors", "외국 의사", "Foreign Doctors Medical", "western_studies", False),
        ("steam_engines", "증기 기관", "Steam Engine Industry", "railway_line", True),
        ("newspapers", "신문 발행", "Newspaper Propaganda", "modern_schools", False),
        ("expo_pavilion", "박람회관", "Exposition Pavilion Construction", "world_expo", True),
        ("loyalist_schools", "근왕 학당", "Loyalist Academy School", "expel_barbarians", False),
        ("imperial_guard", "근위대", "Imperial Guard Regiments", "imperial_army", False),
        ("conscription_law", "징병령", "Conscription Law", "imperial_army", False),
        ("shrine_unity", "신사 통합", "Shrine Unity Rites", "national_shrine", False),
        ("kunoichi", "쿠노이치", "Kunoichi Agents", "infiltrators", False),
        ("shadow_courts", "그림자 법정", "Shadow Courts Security", "spy_school", False),
        ("ninja_tools", "닌자 도구", "Shinobi Tool Workshops", "smoke_bombs", False),
        ("spear_corps", "창병대", "Spear Infantry Corps", "archers", False),
        ("castle_sieges", "공성술", "Castle Siege Artillery", "castle_cannons", False),
        ("mountain_warfare", "산악전", "Mountain Warfare Doctrine", "mountain_castles", False),
        ("battleships", "전함 계획", "Battleship Fleet Plans", "destroyers", False),
        ("torpedo_doctrine", "어뢰 교리", "Torpedo Doctrine Navy", "submarine_fleet", False),
        ("tea_trade", "차 교역", "Tea Trade", "rice_harvest", False),
        ("lacquer_works", "칠기 공방", "Lacquer Works", "porcelain", True),
        ("power_plants", "발전소", "Power Plants", "rail_network", True),
        ("sargon_trade", "사르곤 교역", "Sargon Trade Accord", "columbia_treaty", False)):
    f(sid, ko, en, pre=[pre], econ=econ)
C.d(cat_s, "shinobi_school", "닌자 학교 확장", "Expand the Shinobi School", [NIN(2)], cost=50, once=False, days_re_enable=180,
    visible=["has_completed_focus = TU_HIG_spy_school"], available=[AT_MOST("shinobi", 8)])
C.d(cat_p, "foreign_concessions", "외국 조계 허가", "Grant Foreign Concessions", ["add_political_power = 100", FOR(15)], cost=0, once=False,
    days_re_enable=365, available=[AT_LEAST("ports", 2)])
C.d(cat_c, "castle_review", "성 사열", "Castle Review", ["add_war_support = 0.04", "army_experience = 10"], cost=25, once=False, days_re_enable=240)
C.d(cat_c, "sakura_festival", "벚꽃 축제", "Cherry Blossom Festival", ["add_stability = 0.03", FOR(-3)], cost=25, once=False, days_re_enable=365)
C.ev(31, ("외국 사절의 방문", "Visit of a Foreign Envoy"), ("외국 사절이 쇼군 알현을 청했다.", "A foreign envoy asks for an audience with the shogun."),
     [("맞이한다.", "Receive him.", [FOR(5), "add_political_power = 25"], 50), ("돌려보낸다.", "Turn him away.", [FOR(-5)], 50)],
     trigger=["original_tag = HIG", "has_completed_focus = TU_HIG_foreign_ships"], mtth=300)
C.ev(32, ("떠돌이 낭인", "A Wandering Ronin"), ("검술이 뛰어난 낭인이 사관을 청한다.", "A masterful ronin asks to enter service."),
     [("거둔다.", "Take him in.", ["army_experience = 15"], 1)], trigger=["original_tag = HIG", "has_idea = TU_HIG_samurai_class"], mtth=300)
C.ev(33, ("쌀 폭동", "Rice Riots"), ("쌀값이 치솟자 백성들이 쌀가게를 습격했다.", "As rice prices soared, people raided rice shops."),
     [("비축미를 푼다.", "Release reserves.", ["add_political_power = -30", "add_stability = 0.02"], 60), ("진압한다.", "Suppress them.", ["add_stability = -0.03"], 40)],
     trigger=["original_tag = HIG", AT_LEAST("foreign", 40)], mtth=300)
C.ev(34, ("닌자의 공훈", "A Shinobi's Triumph"), ("닌자가 외국 육상함의 설계도를 가져왔다.", "A shinobi brought back plans of a foreign landship."),
     [("훌륭하다.", "Excellent.", ["add_tech_bonus = { name = TU_HIG_plans bonus = 0.75 uses = 1 category = industry }"], 1)],
     trigger=["original_tag = HIG", AT_LEAST("shinobi", 5)], mtth=300)

# ------------------------------------------------------------------ 리워크 (사양서 27): 해군 갈래 자리에 근대 육군 · 해안 방어 · 육상함 · 닌자 · 산업
f("western_drill", "양식 훈련", "Western-Style Drill", pre=["root"])
f("conscript_army", "징병제 군대", "Conscript Army", pre=["western_drill"])
f("crossbow_arsenal", "노궁 병기창", "Crossbow Arsenal", pre=["western_drill"])
f("field_artillery", "야포대", "Field Artillery", pre=["conscript_army", "crossbow_arsenal"])
f("staff_college", "육군 참모 학교", "Army Staff College", pre=["field_artillery"])
f("army_founding", "황군 창설", "Founding of the Imperial Army", pre=["staff_college"], cost=15)
f("shore_defence", "해안 방어선", "Shore Defence Line", pre=["fishing_ports"])
f("coastal_watchtowers", "해안 망루", "Coastal Watchtowers", pre=["shore_defence"])
f("harbour_forts", "항구 요새", "Harbour Forts", pre=["shore_defence"])
f("sea_terror_wardens", "해사 감시대", "Sea Terror Wardens", pre=["coastal_watchtowers", "harbour_forts"])
f("engine_studies", "증기 기관 연구", "Steam Engine Studies", pre=["foreign_ships"])
f("landship_workshops", "육상함 공방", "Landship Workshops", pre=["engine_studies"], econ=True)
f("landship_cavalry", "육상함 기동대", "Steam Cavalry Corps", pre=["landship_workshops"])
f("shadow_couriers", "그림자 전령", "Shadow Couriers", pre=["shinobi_villages"])
f("secret_school", "비밀 닌자 학당", "Secret Shinobi School", pre=["shadow_couriers"])
f("twin_villages", "두 마을의 맹약", "Twin Villages Pact", pre=["secret_school"], reward=[NIN(2)])
f("silk_workshops", "비단 공방", "Silk Workshops", pre=["rice_harvest"], econ=True)
f("copper_mines", "구리 광산", "Copper Mines", pre=["silk_workshops"], econ=True)
f("capital_railway", "수도 철도", "Capital Railway", pre=["silk_workshops"])

if __name__ == "__main__":
    C.write()
