#!/usr/bin/env python3
"""라이타니엔(LEI) 고유 콘텐츠 (사양서 17).

장치
  1. 선제후 표 TU_LEI_electors (0~7, 시작 3): 쌍둥이 여제를 지지하는 선제후 수. 설득(정치력)·연회·혼인 디시전으로 늘고,
     이벤트로 이탈한다. 5표 이상이면 '제국 칙령' 디시전(큰 보너스)을 쓸 수 있다.
  2. 아츠 공명 TU_LEI_resonance (0~100): 연주회·오페라 디시전과 중점으로 쌓는다. 공명 30을 써서 90일 동안 교향곡
     국민정신(전투 교향곡 / 재건 협주곡 / 치유의 노래)을 건다 (days_remove).
  3. 마왕의 유산 TU_LEI_relics (0~3): 마왕의 유물을 찾는 이벤트·디시전. 3개면 숨은 결말.
정치 결말 셋 (서로 배타): 쌍둥이 여제의 통치(선제후 5) / 선제후 연방(선제후 2 이하) / 마왕의 귀환(유물 3).

실행: python -I tools/focusgen/content/lei.py && python -I tools/focusgen/merge_focus.py --tag LEI
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_lib import Country  # noqa: E402

C = Country("LEI", "라이타니엔", "Leithanien")
f = C.f
MAXV = {"electors": 7, "resonance": 100, "relics": 3}
NAMES = {"electors": ("§Y여제를 지지하는 선제후§!", "§YElectors for the Empresses§!"),
         "resonance": ("§G아츠 공명§!", "§GArts Resonance§!"), "relics": ("§R마왕의 유물§!", "§RWitch King Relics§!")}


def V(var, n):
    name = "TU_LEI_%s_%s%d" % (var, "m" if n < 0 else "", abs(n))
    if not any(e.startswith(name + " =") for e in C.effects):
        C.effects.append("""%s = {
	custom_effect_tooltip = %s_tt
	hidden_effect = {
		add_to_variable = { TU_LEI_%s = %d }
		clamp_variable = { var = TU_LEI_%s min = 0 max = %d }
	}
}""" % (name, name, var, n, var, MAXV[var]))
        ko, en = NAMES[var]
        C.loc(name + "_tt", "%s %s%d" % (ko, "+" if n > 0 else "", n), "%s %s%d" % (en, "+" if n > 0 else "", n))
    return "%s = yes" % name


def ELE(n):
    return V("electors", n)


def RES(n):
    return V("resonance", n)


def RELIC():
    return V("relics", 1)


def AT_LEAST(var, n):
    return "check_variable = { TU_LEI_%s > %d }" % (var, n - 1)


def AT_MOST(var, n):
    return "check_variable = { TU_LEI_%s < %d }" % (var, n + 1)


def FLAG(x):
    return "set_country_flag = TU_LEI_%s" % x


def HAS(x):
    return "has_country_flag = TU_LEI_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_lei_ev.%d%s }" % (n, " days = %d" % days if days else "")


C.history += ["set_variable = { TU_LEI_electors = 3 }", "set_variable = { TU_LEI_resonance = 10 }",
              "set_variable = { TU_LEI_relics = 0 }", "add_ideas = { TU_LEI_twin_throne TU_LEI_witch_king_shadow }"]

# ------------------------------------------------------------------ 국민정신
C.idea("twin_throne", "쌍둥이 옥좌", "The Twin Throne", {"political_power_gain": -0.05, "stability_factor": 0.03}, "generic_political_support",
       ("두 여제가 한 나라를 다스린다. 선제후들은 그 틈을 노린다.", "Two empresses rule one nation. The electors watch for the gap between them."))
C.idea("witch_king_shadow", "마왕의 그림자", "Shadow of the Witch King", {"stability_factor": -0.05, "war_support_factor": -0.03}, "generic_army_problems",
       ("마왕을 몰아낸 지 오래지만, 그의 흔적은 아직 이 땅에 남아 있다.", "The Witch King was cast down long ago, but his traces still linger."))
C.idea("battle_symphony", "전투 교향곡", "Battle Symphony", {"army_attack_factor": 0.1, "army_org_factor": 0.05}, "generic_morale_bonus")
C.idea("rebuild_concerto", "재건 협주곡", "Reconstruction Concerto", {"production_speed_buildings_factor": 0.15}, "generic_production_bonus")
C.idea("healing_song", "치유의 노래", "Song of Healing", {"stability_factor": 0.1, "monthly_population": 0.15}, "generic_morale_bonus")
C.idea("twin_empresses", "쌍둥이 여제의 통치", "Rule of the Twin Empresses", {"political_power_gain": 0.15, "stability_factor": 0.1, "research_speed_factor": 0.03},
       "generic_central_management")
C.idea("electoral_federation", "선제후 연방", "Electoral Federation", {"production_speed_buildings_factor": 0.1, "conscription_factor": 0.05, "political_power_gain": -0.05},
       "generic_local_self_management")
C.idea("witch_king_return", "마왕의 귀환", "Return of the Witch King", {"army_attack_factor": 0.12, "research_speed_factor": 0.05, "stability_factor": -0.1},
       "generic_deal_with_the_devil")
C.idea("arts_pinnacle", "아츠의 정점", "Pinnacle of Arts", {"research_speed_factor": 0.07}, "generic_research_bonus")
C.idea("caster_corps", "정예 술사단", "Elite Caster Corps", {"army_attack_factor": 0.06, "army_morale_factor": 0.05}, "generic_army_war_college")
C.idea("imperial_edict", "제국 칙령", "Imperial Edict", {"political_power_gain": 0.1, "production_factory_max_efficiency_factor": 0.05}, "generic_central_management")

# ------------------------------------------------------------------ 중점
f("root", "쌍둥이 여제의 시대", "Age of the Twin Empresses", cost=5, theme=False, reward=["add_political_power = 50", EV(1)],
  desc=("마왕을 몰아낸 쌍둥이 여제가 라이타니엔을 다스린다. 선제후들은 아직 완전히 고개를 숙이지 않았다.",
        "The twin empresses who cast out the Witch King rule Leithanien. The electors have not yet fully bowed."))

# A. 선제후
f("electors_council", "선제후 회의", "Electors' Council", pre=["root"], theme=False, reward=[FLAG("electors"), "add_political_power = 40"],
  desc=("'선제후' 디시전이 열린다.", "Unlocks the Electors decisions."))
f("court_reform", "궁정 개혁", "Court Reform", pre=["electors_council"])
f("elector_banquets", "선제후 연회", "Electors' Banquet Festival", pre=["electors_council"], reward=[ELE(1)])
f("imperial_census", "제국 인구 조사", "Imperial Census", pre=["court_reform"])
f("elector_marriages", "선제후 혼인", "Electoral Marriage Alliance", pre=["elector_banquets"], reward=[ELE(1)])
f("empress_edict", "여제의 칙령", "Edict of the Empresses", pre=["imperial_census", "elector_marriages"], me=["electoral_autonomy"], reward=[ELE(1)])
f("electoral_autonomy", "선제후 자치", "Electoral Autonomy", pre=["imperial_census", "elector_marriages"], me=["empress_edict"], reward=[ELE(-2)])
f("restore_crown", "왕관의 재건", "Restore the Crown", pre=[["empress_edict", "electoral_autonomy"]])
f("twin_empresses", "쌍둥이 여제의 통치", "Rule of the Twin Empresses", pre=["restore_crown"], me=["electoral_federation", "witch_king_return"],
  cost=15, theme=False, available=[AT_LEAST("electors", 5)],
  reward=[FLAG("path_empress"), "swap_ideas = { remove_idea = TU_LEI_twin_throne add_idea = TU_LEI_twin_empresses }", EV(28)],
  desc=("두 여제가 하나의 목소리로 다스린다. (선제후 5표 이상)", "The empresses rule with one voice. (5+ electors)"))
f("imperial_unity", "제국 통합 헌장", "Imperial Unity Charter", pre=["twin_empresses"])
f("imperial_bureaucracy", "제국 관료제", "Imperial Bureaucracy", pre=["twin_empresses"])
f("crown_of_two", "두 사람의 왕관", "Crown of Two", pre=["imperial_unity", "imperial_bureaucracy"], theme=False, reward=["add_political_power = 100", ELE(1)])
f("electoral_federation", "선제후 연방", "Electoral Federation", pre=["restore_crown"], me=["twin_empresses", "witch_king_return"],
  cost=15, theme=False, available=[AT_MOST("electors", 2)],
  reward=[FLAG("path_federation"), "swap_ideas = { remove_idea = TU_LEI_twin_throne add_idea = TU_LEI_electoral_federation }", EV(29)],
  desc=("여제는 상징으로 남고, 선제후들이 나라를 나눠 다스린다. (선제후 2표 이하)", "The empresses remain symbols; the electors share the realm. (2 or fewer electors)"))
f("elector_diets", "선제후 의회", "Electoral Diet Assembly", pre=["electoral_federation"])
f("regional_armies", "지방군", "Regional Army Regiments", pre=["electoral_federation"])
f("federal_charter", "연방 헌장", "Federal Charter", pre=["elector_diets", "regional_armies"])

# B. 아츠·음악
f("arts_academy", "아츠 학원", "Arts Academy of Leithanien", pre=["root"], theme=False, reward=[RES(10), FLAG("concerts")],
  desc=("'아츠 공명' 디시전이 열린다.", "Unlocks the Arts Resonance decisions."))
f("musical_arts", "음악 아츠 연구", "Musical Arts Research", pre=["arts_academy"], reward=[RES(5)])
f("opera_house", "오페라 극장", "Opera House Festival", pre=["arts_academy"], reward=[RES(10)])
f("conservatory", "음악원", "Conservatory School", pre=["musical_arts"])
f("combat_arts", "전투 아츠 연구", "Combat Arts Research", pre=["conservatory"], me=["civil_arts"])
f("civil_arts", "생활 아츠 공학", "Civilian Arts Engineering", pre=["conservatory"], me=["combat_arts"])
f("arts_amplifier", "아츠 증폭기", "Arts Amplifier Research", pre=[["combat_arts", "civil_arts"]], reward=[RES(10)])
f("grand_symphony", "대교향곡", "The Grand Symphony", pre=["arts_amplifier", "opera_house"], theme=False, reward=[RES(20), FLAG("grand_symphony")],
  desc=("교향곡 국민정신이 180일로 늘어난다.", "Symphony spirits last 180 days."))
f("arts_pinnacle", "아츠의 정점", "Pinnacle of Arts Studies", pre=["grand_symphony"], theme=False, reward=["add_ideas = TU_LEI_arts_pinnacle"])
f("research_slot", "제국 아츠 원", "Imperial Arts Institute", pre=["arts_pinnacle"], theme=False, reward=["add_research_slot = 1"],
  desc=("연구 슬롯 +1", "Research slot +1"))

# C. 마왕의 유산
f("witch_king_legacy", "마왕의 유산 정리", "Settle the Witch King's Legacy", pre=["root"], theme=False, reward=[EV(20)])
f("sealed_archives", "봉인된 서고", "Sealed Archives", pre=["witch_king_legacy"], theme=False, reward=[FLAG("relic_hunt")],
  desc=("'유물 탐색' 디시전이 열린다.", "Unlocks the Relic Search decision."))
f("witch_hunters", "마녀 사냥꾼", "Witch Hunter Squads", pre=["witch_king_legacy"])
f("purge_cultists", "추종자 숙청", "Purge the Witch King's Cultists", pre=["witch_hunters"], theme=False,
  reward=["remove_ideas = TU_LEI_witch_king_shadow", "add_stability = 0.03"])
f("forbidden_studies", "금지된 연구", "Forbidden Studies Research", pre=["sealed_archives"])
f("witch_king_return", "마왕의 귀환", "Return of the Witch King", pre=["forbidden_studies"], me=["twin_empresses", "electoral_federation"],
  cost=15, theme=False, available=[AT_LEAST("relics", 3)],
  reward=[FLAG("path_witch"), "add_ideas = TU_LEI_witch_king_return", "remove_ideas = TU_LEI_twin_throne", EV(30)],
  desc=("마왕의 유물 셋이 모였다. 그가 돌아온다. (유물 3)", "Three relics of the Witch King are gathered. He returns. (3 relics)"))
f("dark_court", "어둠의 궁정", "The Dark Court", pre=["witch_king_return"])
f("arts_terror", "아츠 공포 정치", "Arts Terror Security", pre=["dark_court"])

# D. 군사
f("guard_regiments", "라이타니엔 근위대", "Leithanian Guard Regiments", pre=["root"])
f("arts_artillery", "아츠 포병", "Arts Artillery", pre=["guard_regiments"])
f("mountain_line", "산악 요새선", "Mountain Fortress Line", pre=["guard_regiments"])
f("mobile_doctrine", "기동전 교리", "Mobile Warfare Doctrine", pre=["arts_artillery", "mountain_line"], me=["defensive_doctrine"])
f("defensive_doctrine", "수비 교리", "Defensive Doctrine", pre=["arts_artillery", "mountain_line"], me=["mobile_doctrine"])
f("officer_school", "장교 학교", "Officer School", pre=[["mobile_doctrine", "defensive_doctrine"]])
f("caster_corps", "정예 술사단", "Elite Caster Corps", pre=["officer_school"], theme=False, reward=["add_ideas = TU_LEI_caster_corps", "army_experience = 40"])
f("ursus_border", "우르수스 국경", "Ursus Border Watch", pre=["mountain_line"])
f("kazimierz_border", "카시미어 국경", "Kazimierz Border Forts", pre=["mountain_line"])

# E. 경제
f("mining", "광산 개발", "Mining Development", pre=["root"], econ=True)
f("road_network", "도로망 건설", "Road Network", pre=["mining"], econ="TU_build_infrastructure = yes")
f("industrial_district", "공업 지구", "Industrial District", pre=["mining"], econ=True)
f("civ_program", "민간 공장 계획", "Civilian Factory Program", pre=["industrial_district"], me=["arms_program"], econ=True)
f("arms_program", "군수 공장 계획", "Arms Factory Program", pre=["industrial_district"], me=["civ_program"], econ="TU_build_mil_factory = yes")
f("rail_network", "철도 연결", "Rail Network Expansion", pre=["road_network"], econ="TU_build_infrastructure = yes")
f("instrument_workshops", "악기 공방", "Instrument Workshops", pre=["rail_network"], econ=True, reward=[RES(5)])
f("arts_power", "아츠 동력", "Arts Power Grid", pre=["instrument_workshops"], econ="TU_build_infrastructure = yes")
f("industrialisation", "라이타니엔 산업화", "Leithanian Industrialisation", pre=[["civ_program", "arms_program"], "arts_power"], econ=True)

# F. 외교
f("foreign_office", "외무성", "Foreign Office", pre=["root"])
f("kazimierz_exchange", "카시미어 교류", "Kazimierz Exchange", pre=["foreign_office"])
f("ursus_question", "우르수스 문제", "The Ursus Question", pre=["foreign_office"], theme=False, reward=[EV(24)])
f("siracusa_ties", "시라쿠사 협약", "Siracusa Accord", pre=["kazimierz_exchange"])
f("arts_diplomacy", "아츠 외교", "Arts Diplomacy Festival", pre=["siracusa_ties"], reward=[RES(5)])
f("central_league", "중부 동맹", "Central Alliance Pact", pre=["arts_diplomacy", "ursus_question"], theme=False, reward=[FLAG("league")],
  desc=("'중부 동맹' 디시전이 열린다.", "Unlocks the Central Alliance decisions."))

# 보강
for sid, ko, en, pre, econ in (
        ("court_musicians", "궁정 악단", "Court Musicians Propaganda", "court_reform", False),
        ("tax_collectors", "세금 징수관", "Tax Collectors Treasury", "imperial_census", False),
        ("elector_hunts", "선제후 사냥 대회", "Electors' Hunt Festival", "elector_banquets", False),
        ("palace_guard", "궁전 근위대", "Palace Guard Regiments", "restore_crown", False),
        ("imperial_post", "제국 우편", "Imperial Post Network", "imperial_bureaucracy", True),
        ("free_cities", "자유 도시", "Free Cities Trade", "elector_diets", False),
        ("choir_corps", "합창단", "Choir Corps Propaganda", "opera_house", False),
        ("resonance_studies", "공명 연구", "Resonance Studies Research", "musical_arts", False),
        ("sound_weapons", "음파 무기", "Sonic Weapons Research", "combat_arts", False),
        ("arts_medicine", "아츠 의술", "Arts Medicine Clinics", "civil_arts", False),
        ("arts_engineering", "아츠 공학", "Arts Engineering Design", "civil_arts", False),
        ("music_schools", "음악 학교", "Music Schools Education", "conservatory", False),
        ("relic_scholars", "유물 학자", "Relic Scholars Studies", "sealed_archives", False),
        ("seal_guardians", "봉인 수호자", "Seal Guardian Watch", "witch_hunters", False),
        ("exorcist_order", "퇴마 기사단", "Exorcist Knight Order", "purge_cultists", False),
        ("caster_training", "술사 훈련", "Caster Training Drill", "guard_regiments", False),
        ("rifle_regiments", "소총 연대", "Rifle Weapons Regiments", "guard_regiments", False),
        ("field_hospitals", "야전 병원", "Field Hospitals", "officer_school", False),
        ("motor_columns", "차량 행렬", "Motorised Columns", "mobile_doctrine", False),
        ("tank_corps", "전차 군단", "Tank Corps Armour", "motor_columns", False),
        ("bunkers", "벙커 건설", "Bunker Fortifications", "defensive_doctrine", False),
        ("air_squadrons", "비행 중대", "Air Squadrons Fighter", "officer_school", False),
        ("bomber_wing", "폭격 비행단", "Bomber Wing", "air_squadrons", False),
        ("supply_depots", "보급 기지", "Supply Depots Logistics", "officer_school", False),
        ("timber_industry", "목재 산업", "Timber Industry", "mining", True),
        ("steel_works", "제철소", "Steel Works", "industrial_district", True),
        ("glass_works", "유리 공방", "Glass Works", "instrument_workshops", True),
        ("river_canals", "운하", "River Canals Construction", "road_network", True),
        ("power_plants", "발전소", "Power Plants", "rail_network", True),
        ("lateran_ties", "라테라노 교류", "Laterano Exchange", "foreign_office", False),
        ("rhodes_office", "로도스 아일랜드 사무소", "Rhodes Island Office Pact", "foreign_office", False),
        ("victoria_trade", "빅토리아 교역", "Victoria Trade Accord", "kazimierz_exchange", False),
        ("columbia_ties", "컬럼비아 대사관", "Columbia Embassy", "victoria_trade", False),
        ("arts_tour", "아츠 순회 공연", "Arts Concert Tour Festival", "arts_diplomacy", False),
        ("caster_reserve", "술사 예비대", "Caster Reserve Regiments", "caster_corps", False),
        ("relic_vault", "유물 금고", "Relic Vault Archive", "forbidden_studies", False),
        ("twin_portraits", "쌍둥이 초상화", "Twin Portraits Propaganda", "twin_empresses", False),
        ("federal_courts", "연방 법원", "Federal Courts Reform", "federal_charter", False),
        ("dark_legion", "어둠의 군단", "Dark Legion Regiments", "dark_court", False),
        ("arts_supremacy", "아츠 우위", "Arts Supremacy Research", "arts_terror", False)):
    f(sid, ko, en, pre=[pre], econ=econ)

# ------------------------------------------------------------------ 디시전
cat_el = C.category("electors", "선제후", "The Electors",
                    ("여제를 지지하는 선제후가 5명 이상이면 제국 칙령을 내릴 수 있다.", "With 5+ electors behind the empresses, an Imperial Edict can be issued."),
                    visible=[HAS("electors")])
C.d(cat_el, "persuade", "선제후 설득", "Persuade an Elector", [ELE(1)], cost=75, once=False, days_re_enable=120,
    available=[AT_MOST("electors", 6)], desc=("선제후 +1", "Electors +1"), icon="GFX_decision_generic_political_discourse")
C.d(cat_el, "banquet", "궁정 연회", "Court Banquet", [ELE(1), "add_political_power = -25", RES(5)], cost=25, once=False, days_re_enable=240,
    available=[AT_MOST("electors", 6)])
C.d(cat_el, "grant_privileges", "선제후 특권 부여", "Grant Electoral Privileges", ["add_political_power = 75", ELE(-1)], cost=0, once=False,
    days_re_enable=180, desc=("정치력 +75, 선제후 -1", "Political power +75, electors -1"))
C.d(cat_el, "imperial_edict", "제국 칙령", "Imperial Edict", ["add_ideas = TU_LEI_imperial_edict"], cost=50, once=False,
    days_remove=365, days_re_enable=180, available=[AT_LEAST("electors", 5)], remove_effect=["remove_ideas = TU_LEI_imperial_edict"],
    desc=("1년 동안 제국 칙령 국민정신. (선제후 5 이상)", "Imperial Edict spirit for one year. (5+ electors)"), icon="GFX_decision_generic_political_address")
C.d(cat_el, "elector_levy", "선제후 징병", "Electoral Levy", ["add_manpower = 10000", ELE(-1)], cost=25, once=False, days_re_enable=240)
C.d(cat_el, "elector_tax", "선제후 세금 분담", "Electoral Tax Share", ["TU_build_civ_factory = yes"], cost=100, once=False, days_re_enable=365,
    available=[AT_LEAST("electors", 4)], icon="GFX_decision_generic_factory")

cat_art = C.category("arts", "아츠 공명", "Arts Resonance", icon="GFX_decision_category_generic_industry",
                     desc=("연주회로 공명을 쌓고, 공명 30으로 교향곡을 건다.", "Build resonance through concerts; spend 30 to perform a symphony."),
                     visible=[HAS("concerts")])
C.d(cat_art, "concert", "궁정 연주회", "Court Concert", [RES(10)], cost=25, once=False, days_re_enable=60, icon="GFX_decision_generic_speech")
C.d(cat_art, "opera_gala", "오페라 대공연", "Opera Gala", [RES(20), "add_stability = 0.02"], cost=50, once=False, days_re_enable=180,
    visible=["has_completed_focus = TU_LEI_opera_house"])
for sid, ko, en, idea in (("battle_symphony", "전투 교향곡 연주", "Perform the Battle Symphony", "battle_symphony"),
                          ("rebuild_concerto", "재건 협주곡 연주", "Perform the Reconstruction Concerto", "rebuild_concerto"),
                          ("healing_song", "치유의 노래 연주", "Perform the Song of Healing", "healing_song")):
    C.d(cat_art, sid, ko, en, ["add_ideas = TU_LEI_%s" % idea, RES(-30)], cost=25, once=False, days_remove=90, days_re_enable=30,
        available=[AT_LEAST("resonance", 30), "NOT = { has_idea = TU_LEI_battle_symphony }", "NOT = { has_idea = TU_LEI_rebuild_concerto }",
                   "NOT = { has_idea = TU_LEI_healing_song }"],
        remove_effect=["if = { limit = { NOT = { %s } } remove_ideas = TU_LEI_%s }" % (HAS("grand_symphony"), idea),
                       "if = { limit = { %s } TU_LEI_extend_%s = yes }" % (HAS("grand_symphony"), idea)],
        desc=("공명 30을 써서 90일 동안 연주한다 (대교향곡 뒤 180일). 한 번에 하나만.",
              "Spend 30 resonance to perform for 90 days (180 after the Grand Symphony). One at a time."),
        icon="GFX_decision_generic_speech")
    C.effects.append("""TU_LEI_extend_%s = {
	country_event = { id = tu_lei_ev.40 days = 90 }
	set_country_flag = TU_LEI_extended_%s
}""" % (idea, idea))
C.ev(40, ("연주의 끝", "The Performance Ends"), ("길었던 연주가 끝났다.", "The long performance has ended."),
     [("박수를.", "Applause.", ["if = { limit = { has_country_flag = TU_LEI_extended_%s } remove_ideas = TU_LEI_%s clr_country_flag = TU_LEI_extended_%s }" % (i, i, i)
                                for i in ("battle_symphony", "rebuild_concerto", "healing_song")], 1)])

cat_rel = C.category("relics", "마왕의 유물", "Witch King Relics", icon="GFX_decision_category_military_operation", visible=[HAS("relic_hunt")])
C.d(cat_rel, "relic_search", "유물 탐색", "Search for a Relic", [FLAG("searching")], cost=75, once=False, days_remove=120, days_re_enable=30,
    available=[AT_MOST("relics", 2), "NOT = { %s }" % HAS("searching")], remove_effect=["clr_country_flag = TU_LEI_searching", EV(21)],
    desc=("120일 동안 마왕의 유물을 찾는다.", "Search for a relic of the Witch King for 120 days."), icon="GFX_decision_generic_operation")
C.d(cat_rel, "seal_relic", "유물 봉인", "Seal a Relic", [V("relics", -1), "add_stability = 0.05"], cost=25, once=False, days_re_enable=90,
    available=[AT_LEAST("relics", 1)], desc=("유물 하나를 다시 봉인한다. 안정도 +5%", "Seal a relic away again. Stability +5%"))
C.d(cat_rel, "study_relic", "유물 연구", "Study a Relic",
    ["add_tech_bonus = { name = TU_LEI_study_relic bonus = 0.75 uses = 1 category = electronics category = industry }", "add_stability = -0.02"],
    cost=50, once=False, days_re_enable=240, available=[AT_LEAST("relics", 1)])

cat_for = C.category("foreign", "중부 동맹", "Central Alliance", icon="GFX_decision_category_generic_foreign_policy", visible=[HAS("league")])
C.d(cat_for, "found_league", "중부 동맹 결성", "Found the Central Alliance", ["create_faction = TU_LEI_league"], cost=50, available=["is_in_faction = no"])
C.loc("TU_LEI_league", "중부 동맹", "Central Alliance")
C.d(cat_for, "invite_league", "동맹 초청", "Invite to the Alliance", ["add_to_faction = FROM"], cost=50, once=False, days_re_enable=90,
    visible=["is_faction_leader = yes"],
    target=["NOT = { tag = ROOT }", "is_in_faction = no", "NOT = { has_war_with = ROOT }", "OR = { tag = KAZ tag = SIR tag = LAT tag = VIC }"])
C.d(cat_for, "arts_envoys", "아츠 사절단", "Arts Envoys", ["add_political_power = 50", RES(5)], cost=25, once=False, days_re_enable=180)

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("두 여제의 아침", "Morning of the Two Empresses"),
     ("궁정 악단이 두 여제를 위한 아침 곡을 연주한다. 선제후들은 연주가 끝나기도 전에 자리를 떴다.",
      "The court orchestra plays the morning piece for the two empresses. The electors left before it ended."),
     [("선제후들을 다시 불러라.", "Call the electors back.", [ELE(1)], 50), ("음악은 계속된다.", "The music goes on.", [RES(10)], 50)])
C.ev(20, ("마왕의 흔적", "Traces of the Witch King"),
     ("옛 마왕의 성에서 봉인이 흔들린다는 보고가 들어왔다.", "Reports say the seals in the Witch King's old castle are trembling."),
     [("봉인을 보강한다.", "Reinforce the seals.", ["add_political_power = -25", "add_stability = 0.02"], 60),
      ("무엇이 남았는지 조사한다.", "Investigate what remains.", [FLAG("curious")], 40)])
C.ev(21, ("유물 탐색의 결과", "Result of the Relic Search"),
     ("탐색대가 돌아왔다.", "The search party has returned."),
     [("유물을 찾았다.", "We found a relic.", ["trigger = { %s }" % HAS("found"), RELIC(), "clr_country_flag = TU_LEI_found"], 1),
      ("빈손으로 돌아왔다.", "They returned empty-handed.", ["trigger = { NOT = { %s } }" % HAS("found"), "add_political_power = 15"], 1)],
     immediate=["random_list = {", "\t50 = { %s }" % FLAG("found"),
                "\t50 = { modifier = { factor = 0.5 has_completed_focus = TU_LEI_relic_scholars } }", "}"])
C.ev(22, ("선제후의 이탈", "An Elector Defects"),
     ("한 선제후가 여제의 정책에 반대하며 궁정을 떠났다.", "An elector has left court in protest at the empresses' policies."),
     [("붙잡는다.", "Bring him back.", ["add_political_power = -50"], 40), ("가게 둔다.", "Let him go.", [ELE(-1)], 60)],
     trigger=["original_tag = LEI", HAS("electors"), AT_LEAST("electors", 3)], mtth=240, fire_once=False)
C.ev(23, ("두 여제의 다툼", "The Empresses Quarrel"),
     ("두 여제가 공개석상에서 서로 다른 칙령을 발표했다.", "The two empresses announced contradictory edicts in public."),
     [("언니의 뜻을 따른다.", "Follow the elder.", ["add_stability = -0.02", ELE(1)], 50), ("동생의 뜻을 따른다.", "Follow the younger.", ["add_stability = -0.02", RES(10)], 50)],
     trigger=["original_tag = LEI", "has_idea = TU_LEI_twin_throne"], mtth=360)
C.ev(24, ("우르수스 문제", "The Ursus Question"),
     ("우르수스의 사절이 국경 협정을 제안했다. 선제후들은 우르수스를 믿지 않는다.",
      "An Ursus envoy proposes a border agreement. The electors do not trust Ursus."),
     [("협정을 맺는다.", "Sign the agreement.", ["add_stability = 0.03", ELE(-1)], 50), ("거절한다.", "Refuse.", ["add_war_support = 0.05", ELE(1)], 50)])
C.ev(25, ("천재 작곡가", "A Prodigy Composer"), ("한 젊은 작곡가의 곡이 연주되자 청중 모두가 아츠의 떨림을 느꼈다.",
                                                  "When a young composer's piece was played, the whole audience felt the tremor of Arts."),
     [("궁정에 초빙한다.", "Invite them to court.", [RES(15)], 1)], trigger=["original_tag = LEI", "has_completed_focus = TU_LEI_conservatory"], mtth=300)
C.ev(26, ("오페라 극장 화재", "Opera House Fire"), ("공연 중 오페라 극장에 불이 났다. 아츠가 폭주했다는 소문이다.",
                                                   "A fire broke out in the opera house mid-performance. Rumour blames runaway Arts."),
     [("재건한다.", "Rebuild.", ["add_political_power = -40", RES(5)], 50), ("아츠 공연을 규제한다.", "Regulate Arts performances.", ["add_stability = 0.03", RES(-10)], 50)],
     trigger=["original_tag = LEI", "has_completed_focus = TU_LEI_opera_house"], mtth=400)
C.ev(27, ("마왕 추종자의 습격", "Cultist Attack"), ("마왕을 숭배하는 자들이 기록 보관소를 습격했다.", "Witch King worshippers raided an archive."),
     [("추적한다.", "Hunt them down.", ["army_experience = 10", "add_stability = 0.02"], 60), ("그들이 찾던 것을 조사한다.", "Look into what they sought.", [FLAG("cult_lead")], 40)],
     trigger=["original_tag = LEI", "has_idea = TU_LEI_witch_king_shadow"], mtth=300)
C.ev(28, ("쌍둥이 여제의 통치", "Rule of the Twin Empresses"), ("선제후들이 두 여제 앞에 무릎을 꿇었다.", "The electors have knelt before the two empresses."),
     [("하나의 목소리로.", "With one voice.", ["add_stability = 0.05"], 1)])
C.ev(29, ("선제후 연방", "The Electoral Federation"), ("라이타니엔은 선제후들의 연방이 되었다.", "Leithanien has become a federation of electors."),
     [("각자의 땅에서.", "Each in their own land.", ["add_manpower = 10000"], 1)])
C.ev(30, ("마왕의 귀환", "Return of the Witch King"), ("세 유물이 공명하자 옛 왕좌에 그림자가 앉았다.", "As the three relics resonated, a shadow took the old throne."),
     [("두려워하라.", "Fear.", ["add_war_support = 0.1"], 1)])

# 추가 (목표 분량)
for sid, ko, en, pre, econ in (
        ("crown_jewels", "제국 보물고", "Imperial Treasury Vault", "crown_of_two", False),
        ("empress_guard", "여제 친위대", "Empress Guard Regiments", "imperial_unity", False),
        ("imperial_roads", "제국 대로", "Imperial Road Network", "imperial_bureaucracy", True),
        ("elector_markets", "선제후 시장", "Electoral Markets Trade", "free_cities", False),
        ("federal_army", "연방군", "Federal Army Regiments", "regional_armies", False),
        ("symphony_halls", "교향악당", "Symphony Hall Construction", "grand_symphony", True),
        ("arts_doctrine", "아츠 전투 교리", "Arts Combat Doctrine", "sound_weapons", False),
        ("arts_shields", "아츠 방벽", "Arts Shield Fortifications", "arts_engineering", False),
        ("healing_choirs", "치유 성가대", "Healing Choir Medical Corps", "arts_medicine", False),
        ("forbidden_library", "금서고", "Forbidden Library Archive", "relic_scholars", False),
        ("castle_expedition", "마왕성 탐사", "Witch King Castle Expedition", "seal_guardians", False),
        ("cult_trials", "추종자 재판", "Cultist Trials Security", "exorcist_order", False),
        ("mountain_rangers", "산악 수색대", "Mountain Ranger Scouts", "mountain_line", False),
        ("heavy_artillery", "중포 연대", "Heavy Artillery Regiments", "arts_artillery", False),
        ("armoured_casters", "기갑 술사대", "Armoured Caster Units", "tank_corps", False),
        ("air_defence", "방공망", "Air Defence Network", "bomber_wing", False),
        ("chemical_plants", "화학 공장", "Chemical Plants Industry", "steel_works", True),
        ("arts_crystal_mines", "아츠 결정 광산", "Arts Crystal Mines", "mining", True),
        ("university", "라이타니엔 대학", "University of Leithanien Research", "arts_academy", False),
        ("yan_trade", "염국 교역", "Yan Trade Accord", "foreign_office", False),
        ("sami_contact", "사미 접촉", "Sami Contact Envoys", "ursus_question", False)):
    f(sid, ko, en, pre=[pre], econ=econ)
C.d(cat_el, "elector_council_vote", "선제후 표결", "Electoral Vote", ["random_list = {", "\t60 = { %s }" % ELE(1), "\t40 = { %s }" % ELE(-1), "}", "add_political_power = 30"],
    cost=25, once=False, days_re_enable=180, desc=("표결 결과에 따라 선제후 +1(60%) 또는 -1(40%).", "Electors +1 (60%) or -1 (40%) depending on the vote."))
C.d(cat_art, "street_music", "거리 음악회", "Street Music Festival", [RES(5), "add_stability = 0.02"], cost=10, once=False, days_re_enable=90)
C.d(cat_rel, "witch_hunt", "마녀 사냥", "Witch Hunt", ["add_stability = 0.04", "add_war_support = 0.02"], cost=50, once=False,
    days_re_enable=240, visible=["has_completed_focus = TU_LEI_witch_hunters"])
C.ev(31, ("선제후의 귀환", "An Elector Returns"), ("떠났던 선제후 하나가 여제의 연주회에 감동해 돌아왔다.", "A departed elector, moved by the empresses' concert, has returned."),
     [("환영한다.", "Welcome back.", [ELE(1)], 1)], trigger=["original_tag = LEI", AT_LEAST("resonance", 50), AT_MOST("electors", 6)], mtth=200, fire_once=False)
C.ev(32, ("아츠 폭주", "Arts Overload"), ("공명이 너무 높아지자 도시 곳곳에서 아츠가 저절로 일어났다.", "With resonance so high, Arts phenomena erupted across the city."),
     [("연주를 멈춘다.", "Stop the music.", [RES(-20), "add_stability = 0.02"], 50), ("받아들인다.", "Embrace it.", ["add_stability = -0.03", "add_tech_bonus = { name = TU_LEI_overload bonus = 0.5 uses = 1 category = electronics }"], 50)],
     trigger=["original_tag = LEI", AT_LEAST("resonance", 90)], mtth=120)
C.ev(33, ("유물의 속삭임", "Whispers of the Relics"), ("유물을 지키던 학자가 밤마다 목소리를 듣는다고 호소한다.", "A scholar guarding the relics says he hears voices every night."),
     [("유물을 봉인한다.", "Seal the relics.", [V("relics", -1), "add_stability = 0.03"], 50), ("목소리를 기록한다.", "Record the voices.", ["add_stability = -0.03", "add_political_power = 25"], 50)],
     trigger=["original_tag = LEI", AT_LEAST("relics", 2)], mtth=200)

if __name__ == "__main__":
    C.write()
