#!/usr/bin/env python3
"""컬럼비아(COL) 고유 콘텐츠 (사양서 17).

장치
  1. 라인 생명 연구 프로젝트: 과학 수치 TU_COL_science (0~200). 프로젝트 디시전은 정해진 날짜 동안 진행된 뒤
     결과(연구 보너스·국민정신)를 주고 과학 수치를 올린다. 과학 수치가 일정 이상이면 큰 프로젝트·중점이 열린다.
  2. 대통령 선거: 4년마다 이벤트. 공약(산업·국방·과학) 중 하나를 고르면 행정부 국민정신이 바뀐다.
     2년 뒤 중간 선거 이벤트. 첫 선거는 게임 시작 1년 뒤 (on_startup에서 예약).
  3. 볼리바르 내전 개입: 무기 판매·파벌 지원·개입 명분 디시전.
정치 결말 셋 (서로 배타): 공화국 수호 / 기업 공화국 / 개척자 연방.

실행: python -I tools/focusgen/content/col.py && python -I tools/focusgen/merge_focus.py --tag COL
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_lib import Country  # noqa: E402

C = Country("COL", "컬럼비아", "Columbia")
f = C.f


def SCI(n):
    return "TU_COL_science_%d = yes" % n


def SCI_AT_LEAST(n):
    return "check_variable = { TU_COL_science > %d }" % (n - 1)


def FLAG(x):
    return "set_country_flag = TU_COL_%s" % x


def HAS(x):
    return "has_country_flag = TU_COL_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_col_ev.%d%s }" % (n, " days = %d" % days if days else "")


ADMIN = ["TU_COL_admin_industry", "TU_COL_admin_defence", "TU_COL_admin_science"]


def SET_ADMIN(new):
    out = ["TU_COL_clear_admin = yes", "add_ideas = %s" % new]
    return out


# ------------------------------------------------------------------ 시작 상태 · 효과
C.history += ["set_variable = { TU_COL_science = 10 }", "add_ideas = { TU_COL_admin_industry TU_COL_frontier_unrest }"]
for n in (5, 10, 20, 30):
    C.effects.append("""TU_COL_science_%d = {
	custom_effect_tooltip = TU_COL_science_tt_%d
	hidden_effect = {
		add_to_variable = { TU_COL_science = %d }
		clamp_variable = { var = TU_COL_science min = 0 max = 200 }
	}
}""" % (n, n, n))
    C.loc("TU_COL_science_tt_%d" % n, "§G과학 수치 +%d§!" % n, "§GScience +%d§!" % n)
C.effects.append("""TU_COL_clear_admin = {
	if = { limit = { has_idea = TU_COL_admin_industry } remove_ideas = TU_COL_admin_industry }
	if = { limit = { has_idea = TU_COL_admin_defence } remove_ideas = TU_COL_admin_defence }
	if = { limit = { has_idea = TU_COL_admin_science } remove_ideas = TU_COL_admin_science }
}""")
C.on_actions.append("""on_startup = {
	effect = {
		if = {
			limit = { country_exists = COL NOT = { has_global_flag = TU_COL_first_election_scheduled } }
			set_global_flag = TU_COL_first_election_scheduled	# once only (spec 48)
			COL = { country_event = { id = tu_col_ev.10 days = 365 } }
		}
	}
}""")

# ------------------------------------------------------------------ 국민정신
C.idea("admin_industry", "산업 행정부", "Industrial Administration",
       {"production_speed_buildings_factor": 0.1, "consumer_goods_factor": -0.02}, "generic_production_bonus",
       ("현 행정부는 공장과 철도를 약속했다.", "The current administration promised factories and railways."))
C.idea("admin_defence", "국방 행정부", "Defence Administration",
       {"army_org_factor": 0.05, "air_superiority_efficiency": 0.05, "war_support_factor": 0.05}, "generic_war_preparation")
C.idea("admin_science", "과학 행정부", "Science Administration",
       {"research_speed_factor": 0.05}, "generic_research_bonus")
C.idea("frontier_unrest", "무법의 서부", "The Lawless West",
       {"stability_factor": -0.05, "production_speed_infrastructure_factor": -0.1}, "generic_army_problems",
       ("서부 개척지에는 아직 보안관보다 무법자가 많다.", "The western frontier still has more outlaws than sheriffs."))
C.idea("frontier_order", "개척지의 질서", "Frontier Order",
       {"stability_factor": 0.03, "production_speed_infrastructure_factor": 0.1}, "generic_railroads")
C.idea("rhine_partnership", "라인 생명 협력", "Rhine Lab Partnership",
       {"research_speed_factor": 0.03}, "generic_research_bonus")
C.idea("originium_power", "원석 동력 기술", "Originium Power Technology",
       {"production_factory_max_efficiency_factor": 0.05, "industrial_capacity_factory": 0.05}, "generic_improved_industries")
C.idea("bioengineering", "생체 공학", "Bioengineering",
       {"monthly_population": 0.15, "stability_factor": 0.03}, "generic_morale_bonus")
C.idea("beyond_the_sky", "하늘 너머", "Beyond the Sky",
       {"research_speed_factor": 0.1, "air_superiority_efficiency": 0.05}, "generic_air_research")
C.idea("republic_guard", "공화국 수호", "Guardians of the Republic",
       {"stability_factor": 0.1, "political_power_gain": 0.1}, "constitutional_guarantees")
C.idea("corporate_republic", "기업 공화국", "Corporate Republic",
       {"production_factory_max_efficiency_factor": 0.1, "research_speed_factor": 0.03, "stability_factor": -0.05},
       "generic_foreign_capital")
C.idea("frontier_federation", "개척자 연방", "Frontier Federation",
       {"army_org_factor": 0.05, "war_support_factor": 0.1, "conscription_factor": 0.05}, "generic_army_europe_2")
C.idea("air_supremacy", "컬럼비아 제공권", "Columbian Air Supremacy",
       {"air_superiority_efficiency": 0.1, "air_attack_factor": 0.05}, "generic_air_bonus")
C.idea("mechanised_army", "기계화 육군", "Mechanised Army",
       {"army_speed_factor": 0.05, "army_org_factor": 0.03}, "generic_army_europe_1")
C.idea("industrial_superpower", "산업 강국", "Industrial Superpower",
       {"production_factory_max_efficiency_factor": 0.1, "production_speed_buildings_factor": 0.1},
       "generic_industrial_concern_1")

# ------------------------------------------------------------------ 중점
f("root", "컬럼비아의 꿈", "The Columbian Dream", cost=5, theme=False, reward=["add_political_power = 50", EV(1)],
  desc=("빅토리아에서 독립한 지 오래, 컬럼비아는 기업과 연구소와 개척지의 나라가 되었다.",
        "Long since independence from Victoria, Columbia has become a land of corporations, laboratories and frontiers."))

# A. 라인 생명
f("rhine_pact", "라인 생명과의 협약", "Rhine Lab Pact", pre=["root"], theme=False,
  reward=[FLAG("projects"), "add_ideas = TU_COL_rhine_partnership", SCI(10)],
  desc=("라인 생명 연구소와 국가 연구 협약을 맺는다. '라인 생명 연구소' 디시전으로 연구 프로젝트를 진행할 수 있다.",
        "Sign a national research pact with Rhine Lab. Research projects can be run through the Rhine Lab decisions."))
f("research_grants", "연구 보조금", "Research Grants", pre=["rhine_pact"], reward=[SCI(5)])
f("scientist_visas", "과학자 비자", "Scientist Visa Programme", pre=["research_grants"], reward=[SCI(5)])
f("trimounts_campus", "트라이마운트 연구 단지", "Trimounts Research Campus", pre=["research_grants"], econ=True, reward=[SCI(5)])
f("military_research", "군사 연구 우선", "Military Research First", pre=["trimounts_campus"], me=["civil_research"],
  theme=False, reward=["add_tech_bonus = { name = TU_COL_military_research bonus = 0.75 uses = 2 category = infantry_weapons category = artillery category = armor }", SCI(5)])
f("civil_research", "민간 연구 우선", "Civilian Research First", pre=["trimounts_campus"], me=["military_research"],
  theme=False, reward=["add_tech_bonus = { name = TU_COL_civil_research bonus = 0.75 uses = 2 category = industry category = electronics }", SCI(5)])
f("originium_standards", "원석 공학 표준", "Originium Engineering Standards", pre=[["military_research", "civil_research"]], reward=[SCI(10)])
f("engineering_division", "공학 연구부", "Engineering Division Research", pre=["originium_standards"])
f("ecology_division", "생태 연구부", "Ecology Division Studies", pre=["originium_standards"])
f("structural_division", "구조 연구부", "Structural Division Design", pre=["engineering_division"])
f("research_slot", "국가 연구 위원회", "National Research Council", pre=["scientist_visas", "originium_standards"], theme=False,
  reward=["add_research_slot = 1"], desc=("연구 슬롯 +1", "Research slot +1"))
f("sky_project_prep", "천공 프로젝트 준비", "Sky Project Preparations", pre=["structural_division"], theme=False,
  available=[SCI_AT_LEAST(60)], reward=[FLAG("sky_prep"), "air_experience = 25"],
  desc=("크리스틴 라이트의 하늘 프로젝트를 국가가 지원한다. '하늘 너머' 프로젝트가 열린다. (과학 수치 60 이상)",
        "The state backs Kristen Wright's sky project. Unlocks the Beyond the Sky project. (Science 60+)"))
f("rhine_independence", "라인 생명의 야망", "Ambitions of Rhine Lab", pre=["sky_project_prep"], theme=False,
  reward=[EV(22)])

# B. 연방 정치
f("congress_session", "의회 개회", "Congress Session", pre=["root"])
f("presidential_office", "대통령 집무실 강화", "Strengthen the Presidential Office", pre=["congress_session"])
f("campaign_finance", "선거 자금법", "Campaign Finance Law", pre=["presidential_office"], theme=False,
  reward=[FLAG("campaigns"), "add_political_power = 50"],
  desc=("'선거 운동' 디시전이 열린다.", "Unlocks the election campaign decisions."))
f("federal_budget", "연방 예산", "Federal Budget", pre=["congress_session"])
f("federal_power", "연방 권한 강화", "Strengthen Federal Power", pre=["federal_budget"], me=["states_rights"])
f("states_rights", "주정부 권리 보장", "Guarantee States' Rights", pre=["federal_budget"], me=["federal_power"])
f("frontier_sheriffs", "개척지 보안관", "Frontier Sheriffs", pre=[["federal_power", "states_rights"]], theme=False,
  reward=["swap_ideas = { remove_idea = TU_COL_frontier_unrest add_idea = TU_COL_frontier_order }", FLAG("sheriffs")],
  desc=("서부에 보안관을 보내 무법자를 잡는다. '개척지' 디시전이 열린다.", "Send sheriffs west to hunt outlaws. Unlocks the frontier decisions."))
f("anti_corruption", "부패 수사국", "Anti-Corruption Bureau", pre=["frontier_sheriffs"])
f("free_press", "언론의 자유", "Free Press Broadcast", pre=["anti_corruption"])
f("republic_guard", "공화국 수호", "Guardians of the Republic", pre=["free_press", "campaign_finance"],
  me=["corporate_republic", "frontier_federation"], cost=15, theme=False,
  reward=[FLAG("path_republic"), "add_ideas = TU_COL_republic_guard", EV(28)],
  desc=("헌법과 선거를 지킨다.", "Defend the constitution and the ballot."))
f("civil_liberties", "시민 자유법", "Civil Liberties Act", pre=["republic_guard"])
f("public_education", "공교육 확대", "Public Education Schools", pre=["civil_liberties"])
f("new_deal", "새로운 약속", "The New Promise Works Programme", pre=["public_education"], econ=True)
f("corporate_republic", "기업 공화국", "Corporate Republic", pre=["anti_corruption"],
  me=["republic_guard", "frontier_federation"], cost=15, theme=False,
  available=[SCI_AT_LEAST(40)],
  reward=[FLAG("path_corporate"), "add_ideas = TU_COL_corporate_republic", EV(29)],
  desc=("라인 생명과 블랙스틸 같은 기업이 국정을 함께 운영한다. (과학 수치 40 이상)",
        "Corporations like Rhine Lab and Blacksteel share in running the state. (Science 40+)"))
f("blacksteel_contracts", "블랙스틸 계약", "Blacksteel Security Contracts", pre=["corporate_republic"], theme=False,
  reward=[FLAG("blacksteel"), "army_experience = 25"],
  desc=("'블랙스틸 계약' 디시전이 열린다.", "Unlocks the Blacksteel contract decision."))
f("corporate_boards", "기업 이사회 의석", "Corporate Board Seats", pre=["blacksteel_contracts"])
f("private_research", "민간 연구 특구", "Private Research Zones", pre=["corporate_boards"], reward=[SCI(10)])
f("frontier_federation", "개척자 연방", "Frontier Federation", pre=["frontier_sheriffs"],
  me=["republic_guard", "corporate_republic"], cost=15, theme=False,
  reward=[FLAG("path_frontier"), "add_ideas = TU_COL_frontier_federation", EV(30)],
  desc=("개척지의 보안관과 군인이 나라를 이끈다.", "Sheriffs and soldiers of the frontier lead the nation."))
f("ranger_corps", "레인저 군단", "Ranger Corps", pre=["frontier_federation"])
f("frontier_militia", "개척민 민병대", "Frontier Militia", pre=["ranger_corps"])
f("manifest_destiny", "서부의 운명", "Western Destiny Campaign", pre=["frontier_militia"])

# C. 공군
f("air_force", "공군 창설", "Air Force Founding", pre=["root"])
f("air_academy", "공군 사관학교", "Air Academy", pre=["air_force"])
f("fighter_programme", "전투기 계획", "Fighter Programme", pre=["air_force"])
f("bomber_programme", "폭격기 계획", "Bomber Programme", pre=["air_force"])
f("escort_fighters", "호위 전투기", "Escort Fighters", pre=["fighter_programme"])
f("strategic_bombing", "전략 폭격 교리", "Strategic Bomber Doctrine", pre=["bomber_programme"], me=["close_support"])
f("close_support", "근접 지원 교리", "Close Air Support Doctrine", pre=["bomber_programme"], me=["strategic_bombing"])
f("airfields", "비행장 확충", "Airfield Expansion", pre=["air_academy"])
f("naval_aviation", "해군 항공대", "Naval Aviation", pre=["airfields"])
f("radar_net", "레이더망", "Radar Network Research", pre=["airfields"])
f("jet_research", "제트 엔진 연구", "Jet Engine Research", pre=[["strategic_bombing", "close_support"]], reward=[SCI(5)])
f("air_supremacy", "컬럼비아 제공권", "Columbian Air Supremacy", pre=["jet_research", "escort_fighters"], theme=False,
  reward=["add_ideas = TU_COL_air_supremacy", "air_experience = 50"])

# D. 육군
f("army_reform", "육군 개혁", "Army Reform", pre=["root"])
f("motorised_infantry", "차량화 보병", "Motorised Infantry", pre=["army_reform"])
f("mechanised_infantry", "기계화 보병", "Mechanised Infantry", pre=["motorised_infantry"])
f("armoured_divisions", "기갑 사단", "Armoured Divisions", pre=["mechanised_infantry"])
f("artillery_corps", "포병 군단", "Artillery Corps", pre=["army_reform"])
f("rifle_standard", "표준 소총", "Standard Rifle Weapons", pre=["army_reform"])
f("combined_arms", "제병 협동 교리", "Combined Arms Doctrine", pre=["armoured_divisions", "artillery_corps"])
f("mobile_warfare", "기동전 교리", "Mobile Warfare Doctrine", pre=["combined_arms"], me=["firepower"])
f("firepower", "화력 우위 교리", "Superior Firepower Doctrine", pre=["combined_arms"], me=["mobile_warfare"])
f("logistics_corps", "보급 군단", "Logistics Corps Supply", pre=[["mobile_warfare", "firepower"]])
f("mechanised_army", "기계화 육군", "Mechanised Army", pre=["logistics_corps"], theme=False,
  reward=["add_ideas = TU_COL_mechanised_army", "army_experience = 50"])

# E. 해군
f("naval_board", "해군 위원회", "Naval Board", pre=["root"])
f("coastal_fleet", "연안 함대", "Coastal Fleet", pre=["naval_board"])
f("cruiser_squadrons", "순양함 전대", "Cruiser Fleet Squadrons", pre=["coastal_fleet"])
f("carrier_programme", "항공모함 계획", "Carrier Fleet Programme", pre=["cruiser_squadrons", "naval_aviation"])
f("two_ocean_navy", "양대양 해군", "Two-Ocean Navy", pre=["carrier_programme"], theme=False,
  reward=["add_ideas = TU_COL_two_ocean_navy", "army_experience = 50"])

# F. 경제
f("oil_industry", "석유 산업", "Oil Industry", pre=["root"], econ=True)
f("continental_rail", "대륙 철도", "Continental Railway", pre=["oil_industry"], econ="TU_build_infrastructure = yes")
f("highways", "고속도로망", "Highway Road Network", pre=["continental_rail"], econ="TU_build_infrastructure = yes")
f("steel_belt", "철강 지대", "Steel Belt Mills", pre=["oil_industry"], econ="TU_build_mil_factory = yes")
f("factory_towns", "공장 도시", "Factory Towns", pre=["steel_belt"], econ=True)
f("consumer_boom", "소비재 붐", "Consumer Goods Boom", pre=["factory_towns"], me=["arsenal_democracy"], econ=True)
f("arsenal_democracy", "민주주의의 무기고", "Arsenal of the Republic", pre=["factory_towns"], me=["consumer_boom"],
  econ="TU_build_mil_factory = yes")
f("stock_exchange", "증권 거래소", "Stock Exchange Market", pre=[["consumer_boom", "arsenal_democracy"]], econ=True)
f("mobile_city_fleet", "이동 도시 선단", "Mobile City Fleet", pre=["highways"])
f("power_grid", "전력망", "National Power Grid", pre=["highways"], econ="TU_build_infrastructure = yes")
f("assembly_lines", "조립 라인", "Assembly Line Production", pre=["stock_exchange"], econ="TU_build_mil_factory = yes")
f("industrial_superpower", "산업 강국", "Industrial Superpower", pre=["assembly_lines", "power_grid"], theme=False,
  reward=["add_ideas = TU_COL_industrial_superpower", "TU_build_civ_factory = yes"], filt="FOCUS_FILTER_INDUSTRY")

# G. 외교
f("state_department", "국무부", "State Department", pre=["root"])
f("victoria_memory", "독립 전쟁의 기억", "Memory of the War of Independence", pre=["state_department"], theme=False,
  reward=["add_war_support = 0.05", EV(26)])
f("bolivar_question", "볼리바르 문제", "The Bolivar Question", pre=["state_department"], theme=False,
  reward=[FLAG("bolivar")],
  desc=("볼리바르 내전에 대한 디시전이 열린다.", "Unlocks the decisions on the Bolivar civil war."))
f("sargon_trade", "사르곤 교역", "Sargon Trade Accord", pre=["state_department"])
f("kazimierz_ties", "카시미어와의 관계", "Kazimierz Relations", pre=["sargon_trade"])
f("isolation", "고립주의", "Isolationist Neutrality", pre=["kazimierz_ties"], me=["intervention"])
f("intervention", "개입주의", "Interventionist Alliance", pre=["kazimierz_ties"], me=["isolation"], theme=False,
  reward=[FLAG("faction"), "add_war_support = 0.05"],
  desc=("'자유 동맹 결성' 디시전이 열린다.", "Unlocks the Found the Freedom Alliance decision."))

# 추가 중점 (갈래 보강)
f("rhine_security", "라인 생명 보안부", "Rhine Lab Security Department", pre=["rhine_pact"])
f("urban_defence_research", "도시 방위 연구", "Urban Defence Research", pre=["rhine_security"], reward=[SCI(5)])
f("energy_research", "에너지 연구", "Energy Research", pre=["engineering_division"], reward=[SCI(5)])
f("lab_safety", "실험실 안전 규정", "Lab Safety Regulations", pre=["ecology_division"])
f("talent_recruitment", "연구 인재 유치", "Research Talent Recruitment", pre=["scientist_visas"], reward=[SCI(5)])
f("tax_office", "연방 국세청", "Federal Tax Office", pre=["federal_budget"])
f("investigation_bureau", "연방 수사국", "Federal Investigation Bureau", pre=["anti_corruption"])
f("supreme_court", "대법원 판결", "Supreme Court Ruling", pre=["presidential_office"])
f("immigration_policy", "이민 정책", "Immigration Policy Recruitment", pre=["supreme_court"])
f("republic_broadcast", "공화국 방송", "Republic Broadcast", pre=["free_press"])
f("constitutional_amendment", "헌법 수정안", "Constitutional Amendment", pre=["civil_liberties"])
f("corporate_police", "기업 경찰", "Corporate Police", pre=["corporate_boards"])
f("private_railways", "민영 철도", "Private Railways", pre=["corporate_boards"], econ="TU_build_infrastructure = yes")
f("frontier_forts", "개척지 요새", "Frontier Forts", pre=["ranger_corps"])
f("sheriff_academy", "보안관 학교", "Sheriff Academy Training", pre=["frontier_militia"])
f("air_transport", "공중 수송", "Air Transport Supply", pre=["airfields"])
f("night_fighters", "야간 전투기", "Night Fighters", pre=["escort_fighters"])
f("air_depots", "공군 정비창", "Air Maintenance Depots", pre=["air_academy"])
f("aircraft_factories", "항공기 공장", "Aircraft Factories", pre=["fighter_programme"], econ="TU_build_mil_factory = yes")
f("cavalry_scouts", "기병 정찰대", "Cavalry Scouts", pre=["army_reform"])
f("engineer_corps", "공병대", "Engineer Corps Construction", pre=["artillery_corps"])
f("army_medical", "육군 의무대", "Army Medical Corps", pre=["rifle_standard"])
f("national_guard", "주 방위군", "National Guard Reserve", pre=["rifle_standard"])
f("special_forces", "특수 부대 훈련", "Special Forces Training", pre=["national_guard"])
f("armour_maintenance", "기갑 정비", "Armour Maintenance Depots", pre=["armoured_divisions"])
f("destroyer_fleet", "구축함 전대", "Destroyer Fleet", pre=["coastal_fleet"])
f("submarine_fleet", "잠수함 전대", "Submarine Fleet", pre=["destroyer_fleet"])
f("marine_corps", "해병대", "Marine Corps Landing", pre=["naval_board"])
f("coastal_forts", "해안 요새", "Coastal Fortresses", pre=["marine_corps"])
f("naval_dockyards", "해군 조선소", "Naval Dockyards", pre=["naval_board"], econ="TU_build_civ_factory = yes")
f("farm_mechanisation", "농업 기계화", "Farm Mechanisation", pre=["oil_industry"], econ=True)
f("originium_mines", "원석 광산", "Originium Ore Mines", pre=["farm_mechanisation"], econ=True)
f("chemical_industry", "화학 공업", "Chemical Industry", pre=["originium_mines"], econ=True)
f("harbour_expansion", "항만 확장", "Harbour Expansion", pre=["continental_rail"], econ="TU_build_civ_factory = yes")
f("federal_bank", "연방 은행", "Federal Bank", pre=["stock_exchange"])
f("labour_unions", "노동조합", "Labour Unions", pre=["factory_towns"])
f("automobile_industry", "자동차 산업", "Automobile Industry", pre=["assembly_lines"], econ=True)
f("victoria_reconcile", "빅토리아와의 화해", "Reconciliation with Victoria", pre=["victoria_memory"], me=["contain_victoria"])
f("contain_victoria", "빅토리아 견제", "Contain Victoria Plan", pre=["victoria_memory"], me=["victoria_reconcile"])
f("laterano_embassy", "라테라노 대사관", "Laterano Embassy", pre=["state_department"])

# ------------------------------------------------------------------ 디시전
cat_lab = C.category("rhine", "라인 생명 연구소", "Rhine Lab",
                     ("라인 생명과 함께 진행하는 국가 연구 프로젝트. 프로젝트마다 정해진 기간이 지나야 결과가 나온다.",
                      "National research projects run with Rhine Lab. Each project yields results after a set time."),
                     "GFX_decision_category_generic_industry", visible=[HAS("projects")])
PROJ = [
    ("proj_originium", "원석 동력 연구", "Originium Power Research", 120, 50, [],
     ["add_ideas = TU_COL_originium_power", SCI(10)], "연구가 끝나면: 원석 동력 기술 국민정신, 과학 +10"),
    ("proj_bio", "생체 공학 연구", "Bioengineering Research", 120, 50, [],
     ["add_ideas = TU_COL_bioengineering", SCI(10)], "연구가 끝나면: 생체 공학 국민정신, 과학 +10"),
    ("proj_radar", "통신·레이더 연구", "Communications and Radar Research", 90, 50, [],
     ["add_tech_bonus = { name = TU_COL_proj_radar bonus = 1.0 uses = 2 category = radar_tech category = electronics }", SCI(10)],
     "연구가 끝나면: 레이더·전자 연구 보너스, 과학 +10"),
    ("proj_armour", "신형 장갑 합금", "New Armour Alloys", 90, 50, [],
     ["add_tech_bonus = { name = TU_COL_proj_armour bonus = 1.0 uses = 2 category = armor }", SCI(10)],
     "연구가 끝나면: 기갑 연구 보너스, 과학 +10"),
    ("proj_weather", "기상 제어 실험", "Weather Control Experiment", 150, 75, [SCI_AT_LEAST(40)],
     ["add_stability = 0.05", "add_tech_bonus = { name = TU_COL_proj_weather bonus = 1.0 uses = 1 category = industry }", SCI(20)],
     "연구가 끝나면: 안정도 +5%, 산업 연구 보너스, 과학 +20 (과학 40 이상)"),
    ("proj_aero", "항공우주 연구", "Aerospace Research", 150, 75, [SCI_AT_LEAST(40)],
     ["add_tech_bonus = { name = TU_COL_proj_aero bonus = 1.0 uses = 2 category = light_fighter category = tactical_bomber }",
      "air_experience = 50", SCI(20)], "연구가 끝나면: 항공 연구 보너스, 공군 경험치 +50, 과학 +20 (과학 40 이상)"),
    ("proj_sky", "하늘 너머", "Beyond the Sky", 240, 150, [SCI_AT_LEAST(100), HAS("sky_prep")],
     ["add_ideas = TU_COL_beyond_the_sky", SCI(30), EV(23)], "연구가 끝나면: 하늘 너머 국민정신 (과학 100 이상, 천공 프로젝트 준비 중점)"),
]
for sid, ko, en, days, cost, avail, result, hint in PROJ:
    C.d(cat_lab, sid, ko, en, ["custom_effect_tooltip = TU_COL_%s_tt" % sid, FLAG(sid + "_running")], cost=cost,
        available=avail + ["NOT = { %s }" % HAS(sid + "_running")], days_remove=days,
        remove_effect=result + ["clr_country_flag = TU_COL_%s_running" % sid, FLAG(sid + "_done")],
        visible=["NOT = { %s }" % HAS(sid + "_done")], icon="GFX_decision_generic_industry",
        desc=(hint, "Results after %d days." % days))
    C.loc("TU_COL_%s_tt" % sid, hint, "Results after %d days." % days)
C.d(cat_lab, "lab_accident_relief", "실험 사고 수습", "Contain a Lab Accident",
    ["add_stability = 0.03", SCI(5)], cost=25, once=False, days_re_enable=180, visible=[HAS("lab_accident")],
    icon="GFX_decision_generic_civil_support")

cat_pol = C.category("politics", "연방 정치", "Federal Politics",
                     ("4년마다 대통령 선거가 열린다. 공약에 따라 행정부의 성격이 바뀐다.",
                      "A presidential election is held every four years. The administration's character follows its platform."),
                     visible=["OR = {", "\t" + HAS("campaigns"), "\t" + HAS("sheriffs"), "}"])
C.d(cat_pol, "campaign_rally", "선거 유세", "Campaign Rally", ["add_stability = 0.03", "add_political_power = 25"],
    cost=25, once=False, days_re_enable=180, visible=[HAS("campaigns")], icon="GFX_decision_generic_political_address")
C.d(cat_pol, "lobby_congress", "의회 로비", "Lobby Congress", ["add_political_power = 75", "add_stability = -0.02"],
    cost=0, once=False, days_re_enable=240, visible=[HAS("campaigns")])
C.d(cat_pol, "outlaw_hunt", "무법자 소탕", "Outlaw Manhunt", ["add_stability = 0.04", "army_experience = 10"],
    cost=50, once=False, days_re_enable=180, visible=[HAS("sheriffs")], icon="GFX_decision_generic_military")
C.d(cat_pol, "frontier_roads", "개척지 도로", "Frontier Roads",
    ["TU_build_infrastructure = yes", "TU_build_infrastructure = yes"], cost=75, once=False, days_re_enable=365,
    visible=[HAS("sheriffs")], icon="GFX_decision_generic_construction")
C.d(cat_pol, "blacksteel", "블랙스틸 계약", "Blacksteel Contract",
    ["TU_COL_blacksteel_template = yes",
     "capital_scope = { create_unit = { division = \"division_template = \\\"TU_COL_blacksteel\\\" start_experience_factor = 0.5 start_equipment_factor = 1\" owner = COL count = 2 } }"],
    cost=75, once=False, days_re_enable=240, visible=[HAS("blacksteel")], icon="GFX_decision_generic_military")
C.effects.append("""TU_COL_blacksteel_template = {
	if = {
		limit = { NOT = { has_country_flag = TU_COL_blacksteel_template_done } }
		set_country_flag = TU_COL_blacksteel_template_done
		division_template = {
			name = "TU_COL_blacksteel"
			is_locked = no
			priority = 2
			regiments = {
				infantry = { x = 0 y = 0 }
				infantry = { x = 0 y = 1 }
				infantry = { x = 1 y = 0 }
				infantry = { x = 1 y = 1 }
				infantry = { x = 2 y = 0 }
			}
		}
	}
}""")

cat_bol = C.category("foreign", "컬럼비아 외교", "Columbian Foreign Affairs", icon="GFX_decision_category_generic_foreign_policy",
                     visible=["OR = {", "\t" + HAS("bolivar"), "\t" + HAS("faction"), "}"])
C.d(cat_bol, "bolivar_arms", "볼리바르 무기 판매", "Sell Arms to Bolivar",
    ["add_political_power = 50", "BOL = { add_equipment_to_stockpile = { type = infantry_equipment amount = 500 producer = COL } }"],
    cost=0, once=False, days_re_enable=180, visible=[HAS("bolivar"), "country_exists = BOL"],
    available=["NOT = { has_war_with = BOL }"])
C.d(cat_bol, "bolivar_faction", "친컬럼비아 파벌 지원", "Back the Pro-Columbian Faction",
    [FLAG("bolivar_backed"), "add_political_power = -25", EV(27, 30)], cost=50, visible=[HAS("bolivar"), "country_exists = BOL"],
    available=["NOT = { has_war_with = BOL }"])
C.d(cat_bol, "bolivar_intervene", "볼리바르 개입", "Intervene in Bolivar",
    ["create_wargoal = { type = puppet_wargoal_focus target = BOL }"], cost=75,
    visible=[HAS("bolivar_backed"), "country_exists = BOL"], available=["NOT = { has_war_with = BOL }", "has_war_support > 0.3"],
    icon="GFX_decision_generic_military",
    desc=("볼리바르를 괴뢰로 만드는 전쟁 목표를 얻는다. (전쟁 지지 30% 이상)", "Gain a war goal to puppet Bolivar. (War support 30%+)"))
C.d(cat_bol, "freedom_alliance", "자유 동맹 결성", "Found the Freedom Alliance",
    ["create_faction = TU_COL_alliance"], cost=50, visible=[HAS("faction")], available=["is_in_faction = no"])
C.loc("TU_COL_alliance", "자유 동맹", "Freedom Alliance")
C.d(cat_bol, "invite_alliance", "동맹 초청", "Invite to the Alliance", ["add_to_faction = FROM"], cost=50, once=False,
    days_re_enable=90, visible=[HAS("faction"), "is_faction_leader = yes"],
    target=["NOT = { tag = ROOT }", "is_in_faction = no", "NOT = { has_war_with = ROOT }",
            "OR = { tag = BOL tag = SAR tag = KAZ tag = MIN tag = KJE }"])

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("컬럼비아의 아침", "Morning in Columbia"),
     ("트라이마운트의 고층 빌딩 사이로 라인 생명의 비행선이 지나간다. 서부 개척지에서는 오늘도 보안관이 무법자를 쫓는다.",
      "A Rhine Lab airship drifts between the towers of Trimounts. Out west, sheriffs chase outlaws again today."),
     [("기회의 땅이다.", "A land of opportunity.", ["add_political_power = 25"], 1)], picture="GFX_report_event_generic_factory")
C.ev(10, ("대통령 선거", "Presidential Election"),
     ("4년마다 돌아오는 대통령 선거다. 세 후보가 각자의 공약을 내걸었다. 당선자의 공약이 다음 4년을 정한다.",
      "The four-yearly presidential election has come. Three candidates offer three platforms. The winner's platform will set the next four years."),
     [("산업 후보: 공장과 철도를!", "The industry candidate: factories and railways!",
       ["TU_COL_clear_admin = yes", "add_ideas = TU_COL_admin_industry", EV(11, 730), EV(10, 1460), "news_event = { id = tu_col_ev.12 days = 1 }"], 40),
      ("국방 후보: 강한 컬럼비아를!", "The defence candidate: a strong Columbia!",
       ["TU_COL_clear_admin = yes", "add_ideas = TU_COL_admin_defence", EV(11, 730), EV(10, 1460), "news_event = { id = tu_col_ev.12 days = 1 }"], 30),
      ("과학 후보: 미래에 투자를!", "The science candidate: invest in the future!",
       ["TU_COL_clear_admin = yes", "add_ideas = TU_COL_admin_science", SCI(5), EV(11, 730), EV(10, 1460), "news_event = { id = tu_col_ev.12 days = 1 }"], 30)],
     picture="GFX_report_event_generic_rally")
C.ev(11, ("중간 선거", "Midterm Elections"),
     ("임기 중반, 의회 선거가 열렸다. 행정부에 대한 평가가 표로 나타난다.",
      "Halfway through the term, congressional elections are held. The administration is judged at the ballot box."),
     [("행정부가 신임을 얻었다.", "The administration wins confidence.", ["add_political_power = 75", "add_stability = 0.03"], 60),
      ("의회가 행정부를 견제한다.", "Congress checks the administration.", ["add_political_power = -25", "add_stability = 0.05"], 40)],
     picture="GFX_report_event_generic_rally")
C.ev(12, ("컬럼비아의 새 대통령", "Columbia Elects a President"), ("컬럼비아가 새 대통령을 뽑았다.", "Columbia has chosen a new president."),
     [("그렇군.", "Noted.", [], 1)], news=True, picture="GFX_report_event_generic_rally")
C.ev(20, ("라인 생명 실험 사고", "Rhine Lab Accident"),
     ("라인 생명의 연구 시설에서 폭발 사고가 일어났다. 연구소는 원인을 밝히지 않고 있다.",
      "An explosion rocks a Rhine Lab facility. The lab refuses to name the cause."),
     [("연구소를 감사한다.", "Audit the lab.", ["add_political_power = -25", "add_stability = 0.02", FLAG("lab_accident")], 50),
      ("연구는 계속되어야 한다.", "Research must go on.", [SCI(5), "add_stability = -0.03", FLAG("lab_accident")], 50)],
     trigger=["original_tag = COL", HAS("projects")], mtth=300, picture="GFX_report_event_generic_research_lab")
C.ev(21, ("연구의 돌파구", "Research Breakthrough"),
     ("라인 생명의 한 연구부가 예상보다 일찍 성과를 냈다.", "One of Rhine Lab's divisions has delivered results ahead of schedule."),
     [("훌륭하다.", "Excellent.", [SCI(10), "add_tech_bonus = { name = TU_COL_breakthrough bonus = 0.5 uses = 1 category = electronics category = industry }"], 1)],
     trigger=["original_tag = COL", SCI_AT_LEAST(30)], mtth=360, picture="GFX_report_event_generic_research_lab")
C.ev(22, ("라인 생명의 야망", "Ambitions of Rhine Lab"),
     ("라인 생명의 이사회가 연구소의 자치권을 요구했다. 국가의 간섭 없이 하늘 프로젝트를 진행하겠다는 것이다.",
      "Rhine Lab's board demands autonomy: it wants to run the sky project without state interference."),
     [("자치권을 준다.", "Grant autonomy.", [SCI(20), "add_political_power = -50"], 50),
      ("국가가 통제한다.", "Keep it under state control.", ["add_political_power = 50", "add_stability = 0.02"], 50)],
     picture="GFX_report_event_generic_research_lab")
C.ev(23, ("하늘 너머", "Beyond the Sky"),
     ("크리스틴 라이트의 연구가 마침내 하늘의 벽을 넘었다. 테라 어느 나라도 가 보지 못한 곳이다.",
      "Kristen Wright's research has finally broken through the sky. No nation of Terra has gone this far."),
     [("새로운 시대다.", "A new age.", ["add_war_support = 0.05", "add_stability = 0.05"], 1)], picture="GFX_report_event_generic_research_lab")
C.ev(24, ("서부의 무법자들", "Outlaws of the West"),
     ("서부 개척지의 무법자 갱단이 열차를 털었다.", "An outlaw gang in the western frontier robbed a train."),
     [("현상금을 건다.", "Post a bounty.", ["add_political_power = -15", "add_stability = 0.02"], 50),
      ("군을 보낸다.", "Send in the army.", ["army_experience = 10", "add_stability = -0.01"], 50)],
     trigger=["original_tag = COL", "has_idea = TU_COL_frontier_unrest"], mtth=200, picture="GFX_report_event_generic_train")
C.ev(25, ("이동 도시의 도착", "A Mobile City Arrives"),
     ("황야를 떠돌던 이동 도시 하나가 컬럼비아 편입을 요청했다.", "A mobile city roaming the wastes asks to join Columbia."),
     [("받아들인다.", "Welcome it.", ["add_manpower = 10000", "TU_build_civ_factory = yes"], 70),
      ("돌려보낸다.", "Turn it away.", ["add_political_power = 15"], 30)],
     trigger=["original_tag = COL", "has_completed_focus = TU_COL_mobile_city_fleet"], mtth=300, picture="GFX_report_event_generic_factory")
C.ev(26, ("독립 기념일", "Independence Day"),
     ("빅토리아에서 독립한 날을 기념하는 행진이 열렸다. 몇몇 연설가는 빅토리아를 거칠게 비난했다.",
      "A parade marks independence from Victoria. Some speakers denounce Victoria harshly."),
     [("자유를 기억하자.", "Remember our freedom.", ["add_war_support = 0.03", "add_stability = 0.02"], 1)], picture="GFX_report_event_generic_rally")
C.ev(27, ("볼리바르의 파벌", "The Bolivar Faction"),
     ("우리가 지원한 볼리바르 파벌이 세력을 넓혔다. 그들은 더 많은 지원을 원한다.",
      "The Bolivar faction we backed has gained ground. They want more support."),
     [("더 지원한다.", "Send more.", ["add_political_power = -25", "add_war_support = 0.03"], 50),
      ("이 정도면 충분하다.", "That is enough.", ["add_political_power = 25"], 50)])
C.ev(28, ("공화국 수호", "Guardians of the Republic"), ("컬럼비아는 헌법과 선거를 지키기로 했다.", "Columbia has chosen to defend its constitution and elections."),
     [("자유를 위하여.", "For liberty.", ["add_stability = 0.05"], 1)])
C.ev(29, ("기업 공화국", "The Corporate Republic"), ("기업 대표들이 각료 회의에 자리를 얻었다.", "Corporate representatives have taken seats in the cabinet."),
     [("효율이 곧 번영이다.", "Efficiency is prosperity.", ["add_political_power = 50"], 1)])
C.ev(30, ("개척자 연방", "The Frontier Federation"), ("개척지의 보안관과 장군들이 수도에 들어왔다.", "The sheriffs and generals of the frontier have come to the capital."),
     [("서부의 방식대로.", "The western way.", ["add_war_support = 0.05"], 1)])

# ------------------------------------------------------------------ 리워크 (사양서 27): 해군 위원회 자리에 육상함 · 항공 · 개척지 · 과학 · 산업
f("landship_board", "육상함 위원회", "Landship Board", pre=["root"])
f("rhine_engines", "라인 생명 기관", "Rhine Landship Engines", pre=["landship_board"])
f("armoured_landships", "장갑 육상함", "Armoured Hull Plating", pre=["rhine_engines"])
f("landship_artillery", "육상함 포대", "Hull-Mounted Artillery", pre=["rhine_engines"])
f("landship_rapid", "육상함 기동대", "Rapid Assault Corps", pre=["armoured_landships"])
f("trimounts_city", "트라이마운츠 이동도시", "Trimounts Mobile City", pre=["landship_artillery"], cost=15)
f("landship_doctrine", "육상함 교리", "Overland Warfare Doctrine", pre=["landship_rapid", "trimounts_city"], cost=15)
f("drone_swarms", "드론 편대", "Drone Wings", pre=["air_force"])
f("airship_command", "비행선 사령부", "Airship Command", pre=["drone_swarms"])
f("weather_arts", "기상 조작 아츠", "Weather Control Arts", pre=["airship_command"], reward=[SCI(10)])
f("ranger_patrols", "개척지 순찰대", "Frontier Ranger Patrols", pre=["army_reform"])
f("sheriff_militia", "보안관 민병대", "Sheriff Militias", pre=["ranger_patrols"])
f("western_rail", "서부 철도", "Western Railway", pre=["ranger_patrols"])
f("bounty_contracts", "현상금 계약", "Outlaw Bounty Contracts", pre=["sheriff_militia"])
f("originium_lab", "원석 공학 연구소", "Originium Engineering Laboratory", pre=["rhine_pact"], reward=[SCI(10)])
f("patent_office", "특허청", "Federal Patent Office", pre=["originium_lab"], reward=[SCI(5)])
f("refinery_belt", "정유 벨트", "Refinery Belt", pre=["oil_industry"], econ=True)
f("continental_highway", "대륙 고속도로", "Continental Highway Network", pre=["refinery_belt"])
f("assembly_plants", "조립 공장 단지", "Assembly Plant Complex", pre=["refinery_belt"], econ="TU_build_mil_factory = yes")

if __name__ == "__main__":
    C.write()
