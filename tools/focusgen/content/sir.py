#!/usr/bin/env python3
"""시라쿠사(SIR) 고유 콘텐츠 (사양서 17).

장치
  1. 세 패밀리의 영향력: TU_SIR_bellone / TU_SIR_gambino / TU_SIR_saluzzo (0~100). 매달 조금씩 오른다.
     '패밀리' 디시전으로 거래(영향력↑, 보상) 또는 단속(영향력↓, 법↑)한다. 영향력 50 이상 패밀리는 그 패밀리 중점과 보너스를 연다.
     두 패밀리가 함께 60 이상이면 패밀리 전쟁 이벤트가 일어난다.
  2. 법의 권위 TU_SIR_law (0~100): 법원·경찰 중점과 단속으로 오르고, 패밀리와 거래하면 내려간다.
  3. 늑대 군주의 유산: 옛 늑대 군주를 둘러싼 이벤트 사슬, 숨은 결말.
정치 결말 셋 (서로 배타): 패밀리 연합 정부(두 패밀리 50 이상) / 법의 시라쿠사(법 70 이상) / 늑대 군주의 귀환(유산 사슬 완료).

실행: python -I tools/focusgen/content/sir.py && python -I tools/focusgen/merge_focus.py --tag SIR
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_lib import Country  # noqa: E402

C = Country("SIR", "시라쿠사", "Siracusa")
f = C.f
FAM = [("bellone", "벨로네", "Bellone"), ("gambino", "감비노", "Gambino"), ("saluzzo", "살루초", "Saluzzo")]


def VAR(var, n, ko, en):
    name = "TU_SIR_%s_%s%d" % (var, "m" if n < 0 else "", abs(n))
    if not any(e.startswith(name + " =") for e in C.effects):
        C.effects.append("""%s = {
	custom_effect_tooltip = %s_tt
	hidden_effect = {
		add_to_variable = { TU_SIR_%s = %d }
		clamp_variable = { var = TU_SIR_%s min = 0 max = 100 }
	}
}""" % (name, name, var, n, var))
        C.loc(name + "_tt", "%s %s%d" % (ko, "+" if n > 0 else "", n), "%s %s%d" % (en, "+" if n > 0 else "", n))
    return "%s = yes" % name


def LAW(n):
    return VAR("law", n, "§G법의 권위§!", "§GAuthority of Law§!")


def FAMV(k, n):
    ko, en = next((a, b) for x, a, b in FAM if x == k)
    return VAR(k, n, "§Y%s 패밀리 영향력§!" % ko, "§Y%s Family Influence§!" % en)


def AT_LEAST(var, n):
    return "check_variable = { TU_SIR_%s > %d }" % (var, n - 1)


def BELOW(var, n):
    return "check_variable = { TU_SIR_%s < %d }" % (var, n)


def FLAG(x):
    return "set_country_flag = TU_SIR_%s" % x


def HAS(x):
    return "has_country_flag = TU_SIR_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_sir_ev.%d%s }" % (n, " days = %d" % days if days else "")


C.history += ["set_variable = { TU_SIR_bellone = 40 }", "set_variable = { TU_SIR_gambino = 35 }",
              "set_variable = { TU_SIR_saluzzo = 30 }", "set_variable = { TU_SIR_law = 20 }",
              "add_ideas = { TU_SIR_omerta TU_SIR_family_cities }"]
C.effects.append("""TU_SIR_monthly = {
	add_to_variable = { TU_SIR_bellone = 1 }
	add_to_variable = { TU_SIR_gambino = 1 }
	add_to_variable = { TU_SIR_saluzzo = 1 }
	if = { limit = { has_country_flag = TU_SIR_courts } add_to_variable = { TU_SIR_law = 1 } }
	clamp_variable = { var = TU_SIR_bellone min = 0 max = 100 }
	clamp_variable = { var = TU_SIR_gambino min = 0 max = 100 }
	clamp_variable = { var = TU_SIR_saluzzo min = 0 max = 100 }
	clamp_variable = { var = TU_SIR_law min = 0 max = 100 }
}""")
C.on_actions.append("""on_monthly = {
	effect = {
		if = {
			limit = { original_tag = SIR }
			TU_SIR_monthly = yes
		}
	}
}""")
TWO_FAMILIES_50 = ["OR = {",
                   "\tAND = { %s %s }" % (AT_LEAST("bellone", 50), AT_LEAST("gambino", 50)),
                   "\tAND = { %s %s }" % (AT_LEAST("bellone", 50), AT_LEAST("saluzzo", 50)),
                   "\tAND = { %s %s }" % (AT_LEAST("gambino", 50), AT_LEAST("saluzzo", 50)),
                   "}"]

# ------------------------------------------------------------------ 국민정신
C.idea("omerta", "오메르타", "Omerta", {"stability_factor": 0.05, "political_power_gain": -0.1, "war_support_factor": -0.05},
       "generic_secret_police", ("침묵의 규율. 누구도 패밀리에 대해 말하지 않는다.", "The code of silence. No one speaks of the families."))
C.idea("family_cities", "패밀리의 도시들", "Cities of the Families", {"production_speed_buildings_factor": -0.05, "consumer_goods_factor": 0.03},
       "generic_foreign_capital", ("도시마다 주인이 따로 있다. 공사 하나에도 패밀리의 허락이 필요하다.",
                                    "Every city has its own master. Even a building permit needs a family's blessing."))
C.idea("bellone_ties", "벨로네와의 협력", "Bellone Partnership", {"production_speed_buildings_factor": 0.1, "political_power_gain": 0.05},
       "generic_industrial_concern_1")
C.idea("gambino_ties", "감비노와의 협력", "Gambino Partnership", {"army_attack_factor": 0.05, "conscription_factor": 0.05},
       "generic_manpower_bonus")
C.idea("saluzzo_ties", "살루초와의 협력", "Saluzzo Partnership", {"consumer_goods_factor": -0.03, "political_power_gain": 0.1},
       "generic_economic_increase")
C.idea("family_council", "패밀리 연합 정부", "Family Council Government",
       {"political_power_gain": 0.15, "production_speed_buildings_factor": 0.1, "stability_factor": -0.03}, "generic_foreign_capital")
C.idea("rule_of_law", "법의 시라쿠사", "Siracusa of Law", {"stability_factor": 0.15, "production_speed_buildings_factor": 0.1},
       "constitutional_guarantees")
C.idea("wolf_lord", "늑대 군주의 귀환", "Return of the Wolf Lord",
       {"army_attack_factor": 0.1, "war_support_factor": 0.15, "army_morale_factor": 0.1}, "generic_war_preparation")
C.idea("harbour_cities", "항구 도시", "Harbour Cities", {"political_power_gain": 0.05, "consumer_goods_factor": -0.02}, "generic_economic_increase")
C.idea("urban_warfare", "시가전 전문가", "Urban Warfare Experts", {"army_defence_factor": 0.08, "army_org_factor": 0.03},
       "generic_fortify_the_borders")
C.idea("wine_and_olive", "포도주와 올리브", "Wine and Olives", {"consumer_goods_factor": -0.03, "stability_factor": 0.03},
       "generic_agrarian_society")

# ------------------------------------------------------------------ 중점
f("root", "늑대의 땅", "Land of Wolves", cost=5, theme=False, reward=["add_political_power = 50", EV(1)],
  desc=("시라쿠사의 도시들은 정부가 아니라 패밀리가 다스린다. 늑대들은 오랜 규율을 지킨다.",
        "Siracusa's cities are ruled by families, not the government. The wolves keep an old code."))

# A. 패밀리
f("family_summit", "패밀리 회담", "Family Summit", pre=["root"], theme=False,
  reward=[FLAG("families"), "add_political_power = 50"],
  desc=("세 패밀리의 대부를 한자리에 부른다. '패밀리' 디시전이 열린다.", "Call the three godfathers to one table. Unlocks the Family decisions."))
f("family_ledgers", "패밀리 장부 조사", "Family Ledgers Audit", pre=["family_summit"])
f("territories_map", "구역 지도", "Map of the Territories", pre=["family_summit"])
for k, ko, en in FAM:
    f("%s_court" % k, "%s의 응접실" % ko, "The %s Parlour" % en, pre=["territories_map"], theme=False,
      available=[AT_LEAST(k, 50)], reward=[FAMV(k, 10), "add_ideas = TU_SIR_%s_ties" % k],
      desc=("%s 패밀리와 손을 잡는다. (%s 영향력 50 이상)" % (ko, ko), "Join hands with the %s family. (%s influence 50+)" % (en, en)))
f("bellone_construction", "벨로네 건설 회사", "Bellone Construction Company", pre=["bellone_court"], econ=True)
f("bellone_docks", "벨로네 부두", "Bellone Docks", pre=["bellone_construction"], econ="TU_build_civ_factory = yes")
f("gambino_soldiers", "감비노 행동대", "Gambino Soldier Regiments", pre=["gambino_court"])
f("gambino_arsenal", "감비노 무기고", "Gambino Arsenal", pre=["gambino_soldiers"])
f("saluzzo_bank", "살루초 은행", "Saluzzo Bank", pre=["saluzzo_court"])
f("saluzzo_trade", "살루초 교역망", "Saluzzo Trade Network", pre=["saluzzo_bank"])
f("family_peace", "패밀리 평화 협정", "Family Peace Pact", pre=["family_ledgers"])
f("family_council", "패밀리 연합 정부", "Family Council Government", pre=["family_peace"],
  me=["rule_of_law", "wolf_lord"], cost=15, theme=False, available=TWO_FAMILIES_50,
  reward=[FLAG("path_family"), "swap_ideas = { remove_idea = TU_SIR_family_cities add_idea = TU_SIR_family_council }", EV(28)],
  desc=("패밀리들이 정부를 함께 맡는다. (두 패밀리 영향력 50 이상)", "The families govern together. (Two families at 50+ influence)"))
f("family_police", "패밀리 치안대", "Family Police", pre=["family_council"])
f("family_tax", "패밀리 세금", "Family Tax Collection", pre=["family_council"])
f("dons_senate", "대부들의 원로원", "Senate of the Dons", pre=["family_police", "family_tax"], theme=False,
  reward=["add_political_power = 100", "add_stability = 0.05"])

# B. 법
f("court_reform", "법원 개혁", "Court Reform", pre=["root"], theme=False,
  reward=[FLAG("courts"), LAW(5)], desc=("법의 권위가 매달 조금씩 오른다.", "The authority of law rises slightly every month."))
f("honest_judges", "청렴한 판사들", "Honest Judges", pre=["court_reform"], reward=[LAW(5)])
f("public_police", "시민 질서 경찰", "Public Order Police", pre=["court_reform"], reward=[LAW(5)])
f("witness_protection", "증인 보호", "Witness Protection", pre=["honest_judges"], theme=False,
  reward=[LAW(10), FLAG("witness"), "add_stability = -0.02"],
  desc=("오메르타를 깰 증인을 지킨다. '단속' 디시전이 강해진다.", "Protect witnesses who break omerta. Crackdowns become stronger."))
f("break_omerta", "침묵을 깨다", "Break the Silence", pre=["witness_protection"], theme=False, available=[AT_LEAST("law", 40)],
  reward=["remove_ideas = TU_SIR_omerta", LAW(10), EV(23)],
  desc=("오메르타를 깬다. (법의 권위 40 이상)", "Break omerta. (Authority of law 40+)"))
f("anti_mafia", "반패밀리 수사단", "Anti-Family Investigation Bureau", pre=["public_police"])
f("prison_reform", "교도소 개혁", "Prison Security Reform", pre=["anti_mafia"])
f("rule_of_law", "법의 시라쿠사", "Siracusa of Law", pre=["break_omerta", "prison_reform"],
  me=["family_council", "wolf_lord"], cost=15, theme=False, available=[AT_LEAST("law", 70)],
  reward=[FLAG("path_law"), "swap_ideas = { remove_idea = TU_SIR_family_cities add_idea = TU_SIR_rule_of_law }", EV(29)],
  desc=("패밀리가 아니라 법이 도시를 다스린다. (법의 권위 70 이상)", "Law, not the families, rules the cities. (Authority of law 70+)"))
f("constitution", "시라쿠사 헌법", "Siracusa Constitution Charter", pre=["rule_of_law"])
f("public_works", "공공 사업", "Public Works Construction", pre=["rule_of_law"], econ=True)
f("clean_cities", "깨끗한 도시들", "Clean Cities Reform", pre=["constitution", "public_works"], theme=False,
  reward=["add_stability = 0.1", "add_political_power = 75"])

# C. 늑대 군주
f("wolf_legacy", "늑대 군주의 유산", "Wolf Lord's Legacy", pre=["root"], theme=False, reward=[EV(20)])
f("ancient_wolves", "옛 늑대들의 전설", "Legends of the Ancient Wolves", pre=["wolf_legacy"])
f("wolf_rites", "늑대의 의례", "Rites of the Wolves", pre=["ancient_wolves"], theme=False,
  reward=[FLAG("rites"), EV(21, 10)], desc=("'늑대의 의례' 디시전이 열린다.", "Unlocks the Wolf Rites decisions."))
f("wolf_relics", "늑대의 유물", "Relics of the Wolves", pre=["wolf_rites"])
f("lappland_question", "라플란드의 행방", "Where Lappland Went", pre=["wolf_relics"], theme=False, reward=[EV(22, 7)])
f("wolf_lord", "늑대 군주의 귀환", "Return of the Wolf Lord", pre=["lappland_question"], me=["family_council", "rule_of_law"],
  cost=15, theme=False, available=[HAS("wolf_sign")],
  reward=[FLAG("path_wolf"), "add_ideas = TU_SIR_wolf_lord", "remove_ideas = TU_SIR_family_cities", EV(30)],
  desc=("늑대 군주가 돌아왔다. 패밀리도 법도 늑대 앞에 고개를 숙인다. (늑대의 징조 이벤트 필요)",
        "The Wolf Lord has returned. Families and law alike bow before the wolf. (Requires the Sign of the Wolf event)"))
f("pack_army", "늑대 무리 군단", "Wolf Pack Army Regiments", pre=["wolf_lord"])
f("howl_doctrine", "포효 교리", "Howl Doctrine", pre=["pack_army"])
f("wolf_crown", "늑대의 왕관", "Crown of the Wolf", pre=["howl_doctrine"], theme=False, reward=["add_war_support = 0.1", "army_experience = 50"])

# D. 군사
f("family_bodyguards", "패밀리 경호대", "Family Bodyguard Regiments", pre=["root"])
f("urban_tactics", "시가전 전술", "Urban Warfare Tactics", pre=["family_bodyguards"])
f("safehouses", "은신처망", "Safehouse Network Cells", pre=["urban_tactics"])
f("rapid_squads", "기동 타격대", "Rapid Strike Squads", pre=["urban_tactics"], me=["fortress_cities"])
f("fortress_cities", "요새 도시", "Fortress Cities", pre=["urban_tactics"], me=["rapid_squads"])
f("urban_warfare", "시가전 전문가", "Urban Warfare Experts", pre=[["rapid_squads", "fortress_cities"]], theme=False,
  reward=["add_ideas = TU_SIR_urban_warfare", "army_experience = 30"])
f("arms_workshops", "무기 공방", "Arms Workshops", pre=["family_bodyguards"])
f("smg_squads", "기관단총 분대", "Submachine Gun Squads", pre=["arms_workshops"])
f("artillery_batteries", "포병 중대", "Artillery Batteries", pre=["arms_workshops"])
f("army_command", "시라쿠사 군 사령부", "Siracusan Army Command", pre=["urban_warfare", "artillery_batteries"])
f("motor_pools", "차량 정비소", "Motor Pools Motorised", pre=["army_command"])
f("armoured_cars", "장갑차 부대", "Armoured Car Units", pre=["motor_pools"])
f("army_reserve", "예비군", "Army Reserve Regiments", pre=["army_command"])
f("officer_academy", "사관학교", "Officer Academy", pre=["army_reserve"])

# E. 항구
f("harbour_cities", "항구 도시들", "Harbour Cities", pre=["root"], theme=False, reward=["add_ideas = TU_SIR_harbour_cities"])
f("harbour_defence", "항구 방어", "Harbour Defence", pre=["harbour_cities"])
f("smuggling_routes", "밀수 항로", "Smuggling Routes", pre=["harbour_cities"], theme=False,
  reward=[FLAG("smuggling"), "add_political_power = 40"],
  desc=("밀수를 세금으로 바꾼다. '밀수 과세' 디시전이 열린다.", "Turn smuggling into taxes. Unlocks the Smuggling Tax decision."))
f("coastal_fleet", "연안 함대", "Coastal Fleet", pre=["harbour_defence"])
f("torpedo_boats", "어뢰정 전대", "Torpedo Boat Fleet", pre=["coastal_fleet"])
f("naval_base", "해군 기지", "Naval Base Docks", pre=["coastal_fleet"], econ="TU_build_civ_factory = yes")
f("customs_house", "세관", "Customs House Trade", pre=["smuggling_routes"])
f("free_port", "자유항", "Free Port Trade", pre=["customs_house"])

# F. 경제
f("casino_trade", "카지노 교역", "Casino Trade", pre=["root"], theme=False, reward=[FLAG("casinos"), "add_political_power = 40"],
  desc=("'카지노 허가' 디시전이 열린다.", "Unlocks the Casino License decision."))
f("wine_olive", "포도주와 올리브", "Wine and Olive Farms", pre=["root"], theme=False, reward=["add_ideas = TU_SIR_wine_and_olive"])
f("industrial_district", "공업 지구", "Industrial District", pre=["wine_olive"], econ=True)
f("road_network", "도로망", "Road Network", pre=["industrial_district"], econ="TU_build_infrastructure = yes")
f("rail_network", "철도망", "Rail Network Expansion", pre=["road_network"], econ="TU_build_infrastructure = yes")
f("civil_factories", "민간 공장 계획", "Civilian Factory Program", pre=["industrial_district"], me=["arms_factories"], econ=True)
f("arms_factories", "군수 공장 계획", "Arms Factory Program", pre=["industrial_district"], me=["civil_factories"],
  econ="TU_build_mil_factory = yes")
f("legitimate_business", "합법 사업 전환", "Legitimate Business Companies", pre=[["civil_factories", "arms_factories"]], econ=True)
f("tourism", "관광 산업", "Tourism Industry", pre=["casino_trade"], econ=True)
f("luxury_goods", "사치품 산업", "Luxury Goods Industry", pre=["tourism"], econ=True)
f("marble_quarries", "대리석 채석장", "Marble Quarries", pre=["rail_network"], econ=True)
f("power_plants", "발전소", "Power Plants", pre=["rail_network"], econ="TU_build_infrastructure = yes")
f("research_institute", "시라쿠사 연구소", "Siracusa Research Institute", pre=["legitimate_business"])
f("siracusa_industrialisation", "시라쿠사 산업화", "Siracusan Industrialisation", pre=["power_plants", "research_institute"], econ=True)

# G. 외교
f("foreign_ministry", "외무부", "Foreign Ministry", pre=["root"])
f("laterano_accord", "라테라노 협약", "Laterano Accord", pre=["foreign_ministry"])
f("leithanien_border", "라이타니엔 국경", "Leithanien Border Watch", pre=["foreign_ministry"])
f("rim_corridor", "림 빌리튼 통로", "Rim Billiton Corridor Road", pre=["leithanien_border"])
f("victoria_trade", "빅토리아 교역", "Victoria Trade Accord", pre=["laterano_accord"])
f("family_diaspora", "해외 패밀리망", "Overseas Family Network", pre=["victoria_trade"])
f("neutral_siracusa", "중립 시라쿠사", "Neutral Siracusa", pre=["family_diaspora"], me=["southern_league"])
f("southern_league", "남부 연맹", "Southern League Alliance", pre=["family_diaspora"], me=["neutral_siracusa"], theme=False,
  reward=[FLAG("league")], desc=("'남부 연맹' 디시전이 열린다.", "Unlocks the Southern League decisions."))

# ------------------------------------------------------------------ 디시전
cat_fam = C.category("families", "패밀리", "The Families",
                     ("세 패밀리의 영향력은 매달 오른다. 거래하면 그 패밀리가 강해지고 법이 약해진다. 단속하면 반대다.",
                      "The three families grow every month. Dealing with one strengthens it and weakens the law; cracking down does the opposite."),
                     visible=[HAS("families")])
bonus = {"bellone": ["TU_build_civ_factory = yes"], "gambino": ["add_manpower = 10000"], "saluzzo": ["add_political_power = 75"]}
for k, ko, en in FAM:
    C.d(cat_fam, "deal_%s" % k, "%s와 거래" % ko, "Deal with the %s" % en, bonus[k] + [FAMV(k, 10), LAW(-5)], cost=25, once=False,
        days_re_enable=120, desc=("%s 패밀리 영향력 +10, 법 -5" % ko, "%s influence +10, law -5" % en), icon="GFX_decision_generic_fundraising")
    C.d(cat_fam, "crack_%s" % k, "%s 단속" % ko, "Crack Down on the %s" % en,
        [FAMV(k, -15), LAW(5), "add_stability = -0.02",
         "if = { limit = { %s } %s }" % (HAS("witness"), FAMV(k, -10))], cost=50, once=False, days_re_enable=120,
        desc=("%s 패밀리 영향력 -15 (증인 보호 뒤 -25), 법 +5" % ko, "%s influence -15 (-25 with witness protection), law +5" % en),
        icon="GFX_decision_generic_protection")
C.d(cat_fam, "arbitrate", "패밀리 중재", "Arbitrate Between Families", ["add_stability = 0.05", "add_political_power = 25"], cost=50,
    once=False, days_re_enable=180)
C.d(cat_fam, "hire_soldiers", "패밀리 병사 고용", "Hire Family Soldiers",
    ["add_manpower = 8000", "army_experience = 10", FAMV("gambino", 5)], cost=50, once=False, days_re_enable=180,
    icon="GFX_decision_generic_military")
C.d(cat_fam, "bring_down_don", "대부 체포 작전", "Arrest a Don",
    ["random_list = {", "\t1 = { %s }" % FAMV("bellone", -20), "\t1 = { %s }" % FAMV("gambino", -20), "\t1 = { %s }" % FAMV("saluzzo", -20), "}",
     LAW(15), EV(24)], cost=100, once=False, days_re_enable=365, available=[AT_LEAST("law", 50)],
    desc=("무작위 패밀리 하나의 대부를 체포한다. 영향력 -20, 법 +15. (법 50 이상)", "Arrest the don of a random family. Influence -20, law +15. (Law 50+)"),
    icon="GFX_decision_generic_protection")
cat_eco = C.category("street", "거리의 경제", "Street Economy", icon="GFX_decision_category_generic_industry",
                     visible=["OR = {", "\t" + HAS("smuggling"), "\t" + HAS("casinos"), "\t" + HAS("rites"), "\t" + HAS("league"), "}"])
C.d(cat_eco, "smuggling_tax", "밀수 과세", "Tax the Smugglers", ["add_political_power = 60", FAMV("saluzzo", 5)], cost=0, once=False,
    days_re_enable=120, visible=[HAS("smuggling")])
C.d(cat_eco, "casino_license", "카지노 허가", "Casino Licences", ["add_political_power = 75", LAW(-5)], cost=0, once=False,
    days_re_enable=180, visible=[HAS("casinos")])
C.d(cat_eco, "protection_racket", "항만 보호비 정리", "End the Harbour Protection Racket", ["add_stability = 0.04", LAW(5), FAMV("bellone", -5)],
    cost=50, once=False, days_re_enable=240, visible=[HAS("smuggling")])
C.d(cat_eco, "wolf_rite", "늑대의 의례 거행", "Hold the Wolf Rite", ["add_war_support = 0.05", "army_experience = 15"], cost=50,
    once=False, days_re_enable=240, visible=[HAS("rites")])
C.d(cat_eco, "wolf_search", "늑대의 흔적 추적", "Follow the Wolf's Trail", [EV(25)], cost=75, once=True, visible=[HAS("rites")],
    available=["NOT = { %s }" % HAS("wolf_sign")])
C.d(cat_eco, "found_league", "남부 연맹 결성", "Found the Southern League", ["create_faction = TU_SIR_league"], cost=50,
    visible=[HAS("league")], available=["is_in_faction = no"])
C.loc("TU_SIR_league", "남부 연맹", "Southern League")
C.d(cat_eco, "invite_league", "연맹 초청", "Invite to the League", ["add_to_faction = FROM"], cost=50, once=False, days_re_enable=90,
    visible=[HAS("league"), "is_faction_leader = yes"],
    target=["NOT = { tag = ROOT }", "is_in_faction = no", "NOT = { has_war_with = ROOT }", "OR = { tag = LAT tag = RIM tag = IBE tag = LEI }"])

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("늑대의 땅", "Land of Wolves"),
     ("시라쿠사의 거리는 조용하다. 조용한 데는 이유가 있다. 패밀리가 보고 있기 때문이다.",
      "The streets of Siracusa are quiet. There is a reason for the quiet: the families are watching."),
     [("규율을 지킨다.", "Keep to the code.", ["add_stability = 0.02"], 1)])
C.ev(20, ("늑대 군주의 이야기", "Tale of the Wolf Lord"),
     ("노인들은 아직 늑대 군주의 이야기를 한다. 시라쿠사의 모든 늑대를 다스렸던 이. 그가 언젠가 돌아온다고 한다.",
      "Old folk still tell of the Wolf Lord, who ruled all of Siracusa's wolves, and who they say will return one day."),
     [("옛이야기일 뿐이다.", "Only an old story.", ["add_political_power = 15"], 50),
      ("그 이야기를 찾아보라.", "Look into the story.", ["add_war_support = 0.02"], 50)])
C.ev(21, ("의례의 밤", "Night of the Rite"),
     ("보름달 아래 늑대의 의례가 열렸다. 수천 명의 늑대가 같은 방향을 바라보았다.",
      "Under the full moon the Wolf Rite was held. Thousands of wolves faced the same direction."),
     [("무리는 하나다.", "The pack is one.", ["add_war_support = 0.03", "add_stability = 0.02"], 1)])
C.ev(22, ("라플란드의 행방", "Where Lappland Went"),
     ("늑대 군주의 흔적을 좇던 이들이 한 이름에 닿았다. 라플란드. 그녀는 무언가를 알고 있다.",
      "Those tracing the Wolf Lord have arrived at one name: Lappland. She knows something."),
     [("그녀를 찾는다.", "Find her.", ["add_political_power = -25"], 50), ("내버려 둔다.", "Leave her be.", [], 50)])
C.ev(23, ("침묵이 깨지다", "The Silence Breaks"),
     ("한 패밀리 조직원이 법정에서 모든 것을 증언했다. 오메르타가 깨졌다.",
      "A family member testified to everything in court. Omerta is broken."),
     [("법이 이긴다.", "The law prevails.", [LAW(10), "add_stability = -0.03"], 1)])
C.ev(24, ("대부의 체포", "A Don Arrested"),
     ("한 패밀리의 대부가 수갑을 찼다. 그의 부하들이 거리로 나왔다.", "A family's don is in handcuffs. His men take to the streets."),
     [("질서를 지킨다.", "Hold the line.", ["add_stability = -0.03", "army_experience = 10"], 1)])
C.ev(25, ("늑대의 징조", "Sign of the Wolf"),
     ("옛 늑대 군주의 성채에서 무언가가 깨어났다. 시라쿠사의 모든 늑대가 그 울음을 들었다.",
      "Something has woken in the old Wolf Lord's citadel. Every wolf in Siracusa heard its howl."),
     [("군주가 돌아온다.", "The Lord returns.", [FLAG("wolf_sign"), "add_war_support = 0.05"], 1)])
C.ev(26, ("패밀리 전쟁", "Family War"),
     ("두 패밀리가 서로의 구역을 노리고 총을 들었다. 거리에서 총성이 멈추지 않는다.",
      "Two families have taken up arms over each other's turf. Gunfire never stops in the streets."),
     [("군을 보내 진압한다.", "Send in the army.", ["add_stability = -0.03", "army_experience = 15", LAW(5)], 40),
      ("한쪽 편을 든다.", "Take a side.", ["add_political_power = 50", "add_stability = -0.05"], 30),
      ("저절로 끝나길 기다린다.", "Wait for it to burn out.", ["add_stability = -0.05"], 30)],
     trigger=["original_tag = SIR", "OR = {",
      "\tAND = { %s %s }" % (AT_LEAST("bellone", 60), AT_LEAST("gambino", 60)),
      "\tAND = { %s %s }" % (AT_LEAST("bellone", 60), AT_LEAST("saluzzo", 60)),
      "\tAND = { %s %s }" % (AT_LEAST("gambino", 60), AT_LEAST("saluzzo", 60)), "}"],
     mtth=120, fire_once=False)
C.ev(27, ("텍사스의 귀향", "Texas Comes Home"),
     ("한때 패밀리의 후계자였던 텍사스가 고향을 찾았다. 그녀를 알아본 이들이 수군댄다.",
      "Texas, once heir to a family, has returned home. Those who recognise her whisper."),
     [("조용히 지나가게 한다.", "Let her pass quietly.", ["add_stability = 0.02"], 50),
      ("패밀리들이 그녀를 원한다.", "The families want her.", [FAMV("saluzzo", 5), "add_political_power = 25"], 50)],
     trigger=["original_tag = SIR", "has_completed_focus = TU_SIR_family_summit"], mtth=400)
C.ev(28, ("패밀리 연합 정부", "Family Council Government"), ("대부들이 내각에 들어왔다. 거리는 조용해졌지만 모두가 대가를 치른다.",
                                                        "The dons have entered the cabinet. The streets grow quiet, but everyone pays."),
     [("가족이 먼저다.", "Family comes first.", ["add_political_power = 50"], 1)])
C.ev(29, ("법의 시라쿠사", "Siracusa of Law"), ("시라쿠사 역사상 처음으로 법원이 패밀리보다 강해졌다.",
                                              "For the first time in Siracusa's history, the courts are stronger than the families."),
     [("정의가 섰다.", "Justice stands.", ["add_stability = 0.05"], 1)])
C.ev(30, ("늑대 군주의 귀환", "Return of the Wolf Lord"), ("늑대 군주가 성채에서 내려왔다. 대부도 판사도 무릎을 꿇었다.",
                                                      "The Wolf Lord descended from the citadel. Dons and judges alike knelt."),
     [("늑대의 시대.", "Age of the wolf.", ["add_war_support = 0.05"], 1)])

# 추가 중점 (갈래 보강)
f("informants", "정보원망", "Informant Network", pre=["family_ledgers"])
f("family_weddings", "패밀리 결혼 동맹", "Family Wedding Alliance", pre=["family_peace"])
f("bellone_rail", "벨로네 철도", "Bellone Railway", pre=["bellone_construction"], econ="TU_build_infrastructure = yes")
f("gambino_training", "감비노 훈련장", "Gambino Training Grounds", pre=["gambino_soldiers"])
f("saluzzo_markets", "살루초 시장", "Saluzzo Markets", pre=["saluzzo_trade"])
f("don_advisors", "대부 고문단", "Council of Don Advisors", pre=["dons_senate"])
f("court_archives", "법원 기록 보관소", "Court Archives Records", pre=["honest_judges"])
f("detective_bureau", "형사국", "Detective Bureau Investigation", pre=["anti_mafia"])
f("legal_academy", "법학원", "Legal Academy School", pre=["court_archives"])
f("tax_reform", "조세 개혁", "Tax Reform", pre=["constitution"])
f("public_housing", "공공 주택", "Public Housing", pre=["public_works"])
f("wolf_scholars", "늑대 연구가", "Wolf Lore Scholars Studies", pre=["ancient_wolves"])
f("wolf_citadel", "늑대의 성채", "Citadel of the Wolf", pre=["wolf_relics"])
f("pack_hunters", "무리 사냥꾼", "Pack Hunter Squads", pre=["pack_army"])
f("moon_vigil", "달의 서약", "Oath of the Moon", pre=["wolf_crown"])
f("street_patrols", "거리 순찰대", "Street Patrols", pre=["family_bodyguards"])
f("sniper_nests", "저격 둥지", "Sniper Nest Tactics", pre=["safehouses"])
f("barricades", "바리케이드 방어", "Barricade Defence", pre=["fortress_cities"])
f("demolition_teams", "폭파조", "Demolition Engineer Teams", pre=["rapid_squads"])
f("field_medics", "야전 의무대", "Field Medic Corps", pre=["army_reserve"])
f("mountain_guns", "산악포", "Mountain Artillery Guns", pre=["artillery_batteries"])
f("logistics", "보급망", "Logistics Supply Network", pre=["motor_pools"])
f("tank_workshops", "전차 공방", "Tank Workshops", pre=["armoured_cars"])
f("air_squadron", "시라쿠사 비행대", "Siracusan Air Squadron", pre=["officer_academy"])
f("coastal_guns", "해안포", "Coastal Guns Fortress", pre=["harbour_defence"])
f("submarines", "잠수함 전대", "Submarine Fleet", pre=["torpedo_boats"])
f("merchant_marine", "상선단", "Merchant Marine Fleet", pre=["free_port"])
f("shipyards", "조선소", "Shipyards Dockyard", pre=["naval_base"], econ="TU_build_civ_factory = yes")
f("vineyard_exports", "포도주 수출", "Wine Export Trade", pre=["wine_olive"])
f("olive_oil_mills", "올리브유 공장", "Olive Oil Mills", pre=["vineyard_exports"], econ=True)
f("steel_works", "제철소", "Steel Works", pre=["marble_quarries"], econ="TU_build_mil_factory = yes")
f("chemical_plants", "화학 공장", "Chemical Plants", pre=["steel_works"], econ=True)
f("fashion_houses", "패션 하우스", "Fashion House Trade", pre=["luxury_goods"])
f("research_slot", "시라쿠사 학술원", "Siracusa Academy of Sciences", pre=["research_institute"], theme=False,
  reward=["add_research_slot = 1"], desc=("연구 슬롯 +1", "Research slot +1"))
f("kazimierz_trade", "카시미어 교역", "Kazimierz Trade Accord", pre=["foreign_ministry"])
f("columbia_ties", "컬럼비아 투자", "Columbian Investment Fund", pre=["kazimierz_trade"])
f("iberia_ties", "이베리아 대화", "Iberia Dialogue Exchange", pre=["laterano_accord"])
f("rhodes_office", "로도스 아일랜드 사무소", "Rhodes Island Office Pact", pre=["foreign_ministry"])
C.d(cat_fam, "family_feast", "패밀리 연회", "Family Banquet", ["add_stability = 0.03", FAMV("bellone", 3), FAMV("gambino", 3), FAMV("saluzzo", 3)],
    cost=25, once=False, days_re_enable=180)
C.d(cat_fam, "witness_campaign", "증인 모집", "Recruit Witnesses", [LAW(10), "add_stability = -0.02"], cost=50, once=False,
    days_re_enable=180, visible=[HAS("witness")])
C.d(cat_eco, "olive_harvest", "올리브 수확 축제", "Olive Harvest Festival", ["add_stability = 0.03", "add_political_power = 25"], cost=25,
    once=False, days_re_enable=365, visible=["has_idea = TU_SIR_wine_and_olive"])
C.d(cat_eco, "naval_patrol", "밀수 단속 순찰", "Anti-Smuggling Patrols", [LAW(5), "army_experience = 15"], cost=50, once=False,
    days_re_enable=180, visible=[HAS("smuggling")])
C.ev(31, ("항구의 총격전", "Shootout at the Docks"), ("부두에서 두 조직이 화물을 두고 총격전을 벌였다.", "Two gangs had a shootout over cargo at the docks."),
     [("경찰을 투입한다.", "Send the police.", [LAW(5), "add_stability = -0.02"], 50), ("못 본 척한다.", "Look away.", [FAMV("bellone", 5)], 50)],
     trigger=["original_tag = SIR", "has_completed_focus = TU_SIR_harbour_cities"], mtth=300)
C.ev(32, ("판사 암살 미수", "Attempt on a Judge"), ("패밀리 사건을 맡은 판사가 습격을 받았지만 살아남았다.", "A judge handling a family case was attacked but survived."),
     [("경호를 강화한다.", "Increase protection.", [LAW(5), "add_political_power = -20"], 60), ("판사를 교체한다.", "Replace the judge.", [LAW(-5)], 40)],
     trigger=["original_tag = SIR", AT_LEAST("law", 40)], mtth=300)
C.ev(33, ("관광객의 물결", "A Wave of Tourists"), ("카지노와 해변을 찾아 외국인들이 몰려왔다.", "Foreigners flock to the casinos and beaches."),
     [("환영한다.", "Welcome them.", ["add_political_power = 50"], 1)],
     trigger=["original_tag = SIR", "has_completed_focus = TU_SIR_tourism"], mtth=300)
C.ev(34, ("달밤의 울음", "Howling at Night"), ("달밤마다 성채 쪽에서 늑대 울음이 들린다는 신고가 늘었다.", "Reports of wolf howls from the citadel on moonlit nights are increasing."),
     [("조사단을 보낸다.", "Send investigators.", ["add_political_power = -15", "add_war_support = 0.02"], 1)],
     trigger=["original_tag = SIR", HAS("rites")], mtth=240)

# ------------------------------------------------------------------ 리워크 (사양서 27): 패밀리 전쟁 · 검찰 · 늑대 · 경제
f("inland_smuggling", "내륙 밀수로", "Inland Smuggling Routes", pre=["harbour_cities"])
f("hitman_contracts", "청부 계약", "Hitman Contracts", pre=["family_bodyguards"])
f("limousines", "방탄 차량", "Armoured Limousines", pre=["family_bodyguards"])
f("street_tactics", "패밀리 시가전 교리", "Family Street War Tactics", pre=["hitman_contracts", "limousines"])
f("family_militias", "패밀리 민병대", "Family Militias", pre=["street_tactics"])
f("prosecutors", "반마피아 검찰", "Anti-Mafia Prosecutors", pre=["court_reform"], reward=[LAW(5)])
f("witness_security", "증인 보호 제도", "Witness Security Programme", pre=["prosecutors"], reward=[LAW(5)])
f("lawyers_guild", "변호사 길드", "Lawyers' Guild", pre=["prosecutors"])
f("wolf_hunters", "늑대 무리 사냥꾼", "Wolf Pack Hunters", pre=["wolf_legacy"])
f("wolf_howl", "늑대들의 울부짖음", "Howl of the Wolves Rally", pre=["wolf_hunters"])
f("casino_tax", "카지노 세금", "Casino Tax", pre=["casino_trade"])
f("wine_exports", "포도주 수출 계약", "Wine Export Contracts", pre=["wine_olive"])
f("siracusa_rail", "시라쿠사 철도", "Siracusan Railway", pre=["wine_exports"])

if __name__ == "__main__":
    C.write()
