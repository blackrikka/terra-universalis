#!/usr/bin/env python3
"""쉐라그(KJE) 고유 콘텐츠 (사양서 17).

장치
  1. 설산의 겨울: 달 수 TU_KJE_month (1~12, 매달 on_monthly로 넘어감). 11월에 겨울 국민정신이 붙고 4월에 풀린다.
     '월동 준비' 디시전을 해 두면 혹독한 겨울 대신 견딜 만한 겨울이 온다. 산악 중점이 겨울을 더 견디게 한다.
  2. 근대화 TU_KJE_modern (0~100, 시작 40): 실버애쉬·칼란 무역의 근대화(↑)와 쉐라그드르 신앙의 전통(↓).
     디시전과 중점으로 움직이고, 근대화가 높으면 공장·연구, 낮으면 신앙·안정 보너스 중점이 열린다.
  3. 세 가문: 엔시오다스(실버애쉬), 성녀의 가문, 구귀족. 가문 이벤트와 화해 갈래.
정치 결말 셋 (서로 배타): 근대 쉐라그(근대화 70) / 성녀의 신정(근대화 30 이하) / 세 가문의 화합(근대화 40~60 + 화해).

실행: python -I tools/focusgen/content/kje.py && python -I tools/focusgen/merge_focus.py --tag KJE
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_lib import Country  # noqa: E402

C = Country("KJE", "쉐라그", "Kjerag")
f = C.f


def MOD(n):
    name = "TU_KJE_modern_%s%d" % ("m" if n < 0 else "", abs(n))
    if not any(e.startswith(name + " =") for e in C.effects):
        C.effects.append("""%s = {
	custom_effect_tooltip = %s_tt
	hidden_effect = {
		add_to_variable = { TU_KJE_modern = %d }
		clamp_variable = { var = TU_KJE_modern min = 0 max = 100 }
	}
}""" % (name, name, n))
        if n > 0:
            C.loc(name + "_tt", "§Y근대화§! +%d" % n, "§YModernisation§! +%d" % n)
        else:
            C.loc(name + "_tt", "§Y전통§! +%d (근대화 %d)" % (-n, n), "§YTradition§! +%d (modernisation %d)" % (-n, n))
    return "%s = yes" % name


def AT_LEAST(n):
    return "check_variable = { TU_KJE_modern > %d }" % (n - 1)


def AT_MOST(n):
    return "check_variable = { TU_KJE_modern < %d }" % (n + 1)


def FLAG(x):
    return "set_country_flag = TU_KJE_%s" % x


def HAS(x):
    return "has_country_flag = TU_KJE_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_kje_ev.%d%s }" % (n, " days = %d" % days if days else "")


C.history += ["set_variable = { TU_KJE_modern = 40 }", "set_variable = { TU_KJE_month = 1 }",
              "add_ideas = { TU_KJE_harsh_winter TU_KJE_three_houses }"]
C.effects.append("""TU_KJE_monthly = {
	add_to_variable = { TU_KJE_month = 1 }
	if = { limit = { check_variable = { TU_KJE_month > 12 } } set_variable = { TU_KJE_month = 1 } }
	if = {
		limit = { check_variable = { TU_KJE_month = 11 } }
		if = {
			limit = { has_country_flag = TU_KJE_winter_ready }
			add_ideas = TU_KJE_mild_winter
			clr_country_flag = TU_KJE_winter_ready
		}
		else = {
			add_ideas = TU_KJE_harsh_winter
		}
		country_event = { id = tu_kje_ev.10 }
	}
	if = {
		limit = { check_variable = { TU_KJE_month = 4 } }
		if = { limit = { has_idea = TU_KJE_harsh_winter } remove_ideas = TU_KJE_harsh_winter }
		if = { limit = { has_idea = TU_KJE_mild_winter } remove_ideas = TU_KJE_mild_winter }
		country_event = { id = tu_kje_ev.11 }
	}
}""")
C.on_actions.append("""on_monthly = {
	effect = {
		if = {
			limit = { original_tag = KJE }
			TU_KJE_monthly = yes
		}
	}
}""")

# ------------------------------------------------------------------ 국민정신
C.idea("harsh_winter", "혹독한 겨울", "Harsh Winter",
       {"production_speed_buildings_factor": -0.2, "supply_consumption_factor": 0.15, "army_defence_factor": 0.1, "stability_factor": -0.03},
       "generic_supply_line", ("눈이 길을 막고 산을 막는다. 4월이 되면 풀린다.", "Snow blocks roads and passes. It lifts in April."))
C.idea("mild_winter", "견딜 만한 겨울", "Bearable Winter",
       {"production_speed_buildings_factor": -0.05, "army_defence_factor": 0.1}, "generic_supply_line",
       ("월동 준비 덕분에 겨울을 견딜 만하다. 4월이 되면 풀린다.", "Thanks to winter preparations, the winter is bearable. It lifts in April."))
C.idea("three_houses", "세 가문", "The Three Houses", {"political_power_gain": -0.1}, "generic_local_self_management",
       ("엔시오다스, 성녀의 가문, 구귀족. 세 가문이 쉐라그를 나눠 쥐고 있다.", "Enciodas, the Saintess's house and the old nobility share Kjerag between them."))
C.idea("mountain_folk", "산사람들", "Mountain Folk", {"army_defence_factor": 0.05, "attrition": -0.1}, "generic_mountain_defensive_training")
C.idea("modern_kjerag", "근대 쉐라그", "Modern Kjerag",
       {"production_factory_max_efficiency_factor": 0.1, "research_speed_factor": 0.05, "stability_factor": -0.03}, "generic_industrial_concern_1")
C.idea("saintess_theocracy", "성녀의 신정", "Theocracy of the Saintess",
       {"stability_factor": 0.15, "war_support_factor": 0.1, "army_defence_factor": 0.05}, "generic_political_support")
C.idea("houses_united", "세 가문의 화합", "The Houses United", {"political_power_gain": 0.1, "stability_factor": 0.08, "production_speed_buildings_factor": 0.05},
       "generic_pp_unity_bonus")
C.idea("karlan_trade", "칼란 무역", "Karlan Trade", {"production_speed_buildings_factor": 0.08, "consumer_goods_factor": -0.02}, "generic_foreign_capital")
C.idea("kjeragandr_faith", "쉐라그드르의 가호", "Grace of Kjeragandr", {"stability_factor": 0.05, "army_morale_factor": 0.05}, "generic_morale_bonus")
C.idea("mountain_guard", "설산의 수호자", "Guardians of the Mountains", {"army_defence_factor": 0.1, "army_org_factor": 0.05}, "generic_mountain_defensive_training")

# ------------------------------------------------------------------ 중점
f("root", "설산의 나라", "Kingdom of the Snow Mountains", cost=5, theme=False, reward=["add_political_power = 50", EV(1)],
  desc=("만년설 아래 세 가문이 다스리는 나라. 겨울은 길고, 변화는 느리다.", "A land ruled by three houses beneath eternal snow. Winters are long and change is slow."))

# A. 겨울과 산
f("winter_stores", "월동 창고", "Winter Stores Supply", pre=["root"], theme=False, reward=[FLAG("winter"), FLAG("winter_ready")],
  desc=("'월동 준비' 디시전이 열린다. 이번 겨울은 견딜 만한 겨울이 된다.", "Unlocks the Winter Preparations decision. This winter will be bearable."))
f("mountain_roads", "산길 정비", "Mountain Roads", pre=["winter_stores"], econ="TU_build_infrastructure = yes")
f("snow_tunnels", "눈 터널", "Snow Tunnel Construction", pre=["mountain_roads"], econ="TU_build_infrastructure = yes")
f("mountain_folk", "산사람들", "Mountain Folk", pre=["winter_stores"], theme=False, reward=["add_ideas = TU_KJE_mountain_folk"])
f("avalanche_watch", "눈사태 감시", "Avalanche Watch", pre=["mountain_folk"])
f("heated_barracks", "난방 병영", "Heated Barracks Construction", pre=["avalanche_watch"], econ=True)
f("winter_mastery", "겨울의 지배자", "Masters of Winter", pre=["snow_tunnels", "heated_barracks"], theme=False,
  reward=[FLAG("winter_master")], desc=("혹독한 겨울이 와도 매년 월동 준비가 자동으로 된다.", "Winter preparations happen automatically every year."))

# B. 근대화 (실버애쉬·칼란)
f("karlan_company", "칼란 무역 회사", "Karlan Trade Company", pre=["root"], theme=False, reward=["add_ideas = TU_KJE_karlan_trade", MOD(10), FLAG("karlan")],
  desc=("'칼란 무역' 디시전이 열린다.", "Unlocks the Karlan Trade decisions."))
f("silverash_vision", "실버애쉬의 비전", "Silverash's Industrial Vision", pre=["karlan_company"], reward=[MOD(10)])
f("foreign_investment", "외국 투자", "Foreign Investment Fund", pre=["karlan_company"], reward=[MOD(5)])
f("tech_imports", "기술 수입", "Technology Imports", pre=["silverash_vision"], me=["self_sufficient"], reward=[MOD(10)])
f("self_sufficient", "자립 공업", "Self-Sufficient Industry", pre=["silverash_vision"], me=["tech_imports"], reward=[MOD(5)])
f("kjerag_bank", "쉐라그 은행", "Kjerag Bank", pre=[["tech_imports", "self_sufficient"], "foreign_investment"])
f("modern_kjerag", "근대 쉐라그", "Modern Kjerag", pre=["kjerag_bank"], me=["saintess_theocracy", "houses_united"], cost=15, theme=False,
  available=[AT_LEAST(70)], reward=[FLAG("path_modern"), "add_ideas = TU_KJE_modern_kjerag", "remove_ideas = TU_KJE_three_houses", EV(28)],
  desc=("실버애쉬의 쉐라그. 눈 덮인 산에 공장과 철도가 들어선다. (근대화 70 이상)",
        "Silverash's Kjerag: factories and railways climb the snowy peaks. (Modernisation 70+)"))
f("industrial_valleys", "공업 계곡", "Industrial Valleys", pre=["modern_kjerag"], econ=True)
f("research_slot", "쉐라그 공과 대학", "Kjerag Institute of Technology", pre=["modern_kjerag"], theme=False, reward=["add_research_slot = 1"],
  desc=("연구 슬롯 +1", "Research slot +1"))
f("modern_army", "근대 군대", "Modern Army Reform", pre=["industrial_valleys"])

# C. 전통 (쉐라그드르 신앙)
f("saintess_blessing", "성녀의 축복", "Blessing of the Saintess", pre=["root"], reward=[MOD(-5)])
f("kjeragandr_faith", "쉐라그드르 신앙", "Kjeragandr Faith", pre=["saintess_blessing"], theme=False, reward=["add_ideas = TU_KJE_kjeragandr_faith", MOD(-10)])
f("elders_council", "장로 회의", "Elders' Council", pre=["saintess_blessing"], reward=[MOD(-5)])
f("sacred_peaks", "성스러운 봉우리", "Sacred Peaks Pilgrimage", pre=["kjeragandr_faith"])
f("old_ways", "옛 방식", "The Old Ways", pre=["elders_council", "sacred_peaks"], reward=[MOD(-10)])
f("saintess_theocracy", "성녀의 신정", "Theocracy of the Saintess", pre=["old_ways"], me=["modern_kjerag", "houses_united"], cost=15, theme=False,
  available=[AT_MOST(30)], reward=[FLAG("path_faith"), "add_ideas = TU_KJE_saintess_theocracy", "remove_ideas = TU_KJE_three_houses", EV(29)],
  desc=("성녀가 신의 이름으로 다스린다. (근대화 30 이하)", "The Saintess rules in the god's name. (Modernisation 30 or less)"))
f("faith_guardians", "신앙 수호대", "Faith Guardian Regiments", pre=["saintess_theocracy"])
f("snow_temples", "설산 신전", "Snow Temple Shrines", pre=["saintess_theocracy"])

# D. 세 가문
f("three_houses_talks", "세 가문 회담", "Talks of the Three Houses", pre=["root"], theme=False, reward=[EV(20)])
f("enciodas_house", "엔시오다스 가문", "House Enciodas Pact", pre=["three_houses_talks"], reward=[MOD(5)])
f("saintess_house", "성녀의 가문", "House of the Saintess Pact", pre=["three_houses_talks"], reward=[MOD(-5)])
f("old_nobility", "구귀족", "Old Nobility Pact", pre=["three_houses_talks"])
f("reconciliation", "세 가문의 화해", "Reconciliation of the Three Houses", pre=["enciodas_house", "saintess_house", "old_nobility"], theme=False,
  reward=[FLAG("reconciled"), "add_stability = 0.05"])
f("houses_united", "세 가문의 화합", "The Houses United", pre=["reconciliation"], me=["modern_kjerag", "saintess_theocracy"], cost=15, theme=False,
  available=[AT_LEAST(40), AT_MOST(60)], reward=[FLAG("path_united"), "swap_ideas = { remove_idea = TU_KJE_three_houses add_idea = TU_KJE_houses_united }", EV(30)],
  desc=("세 가문이 함께 쉐라그를 이끈다. (근대화 40~60)", "The three houses lead Kjerag together. (Modernisation 40-60)"))
f("kjerag_charter", "쉐라그 헌장", "Kjerag Charter", pre=["houses_united"])
f("unified_army", "통합군", "Unified Army Regiments", pre=["houses_united"])

# E. 군사
f("mountain_infantry", "산악 보병", "Mountain Infantry Regiments", pre=["root"])
f("snow_forts", "설산 요새", "Snow Mountain Fortresses", pre=["mountain_infantry"])
f("ski_troops", "스키 기동대", "Ski Mobile Troops", pre=["mountain_infantry"])
f("mountain_doctrine", "산악전 교리", "Mountain Warfare Doctrine", pre=["ski_troops", "snow_forts"], me=["highland_defence"])
f("highland_defence", "고지 방어", "Highland Defence", pre=["ski_troops", "snow_forts"], me=["mountain_doctrine"])
f("marksman_training", "사격 훈련", "Marksman Training", pre=[["mountain_doctrine", "highland_defence"]])
f("mountain_guard", "설산 정예대", "Elite Mountain Guard", pre=["marksman_training"], theme=False,
  reward=["add_ideas = TU_KJE_mountain_guard", "army_experience = 40"])
f("courier_knights", "쉐라그 기사", "Kjerag Knights Order", pre=["mountain_guard"])
f("mountain_artillery", "산악포", "Mountain Artillery Guns", pre=["snow_forts"])

# F. 경제
f("silver_mines", "은 광산", "Silver Mines", pre=["root"], econ=True)
f("timber", "목재 산업", "Timber Industry", pre=["silver_mines"], econ=True)
f("industrial_district", "공업 지구", "Industrial District", pre=["silver_mines"], econ=True)
f("civ_program", "민간 공장 계획", "Civilian Factory Program", pre=["industrial_district"], me=["arms_program"], econ=True)
f("arms_program", "군수 공장 계획", "Arms Factory Program", pre=["industrial_district"], me=["civ_program"], econ="TU_build_mil_factory = yes")
f("cable_cars", "산악 케이블카", "Mountain Cable Car Network", pre=["timber"], econ="TU_build_infrastructure = yes")
f("hydro_power", "수력 발전", "Hydro Power Plants", pre=["cable_cars"], econ="TU_build_infrastructure = yes")
f("industrialisation", "쉐라그 산업화", "Kjerag Industrialisation", pre=[["civ_program", "arms_program"], "hydro_power"], econ=True)

# G. 외교
f("foreign_ties", "산 너머로", "Beyond the Mountains Envoys", pre=["root"])
f("kazimierz_ties", "카시미어 교류", "Kazimierz Exchange", pre=["foreign_ties"])
f("columbia_ties", "컬럼비아 무역", "Columbia Trade Accord", pre=["foreign_ties"])
f("rhodes_ties", "로도스 아일랜드 협력", "Rhodes Island Cooperation Pact", pre=["kazimierz_ties"])
f("mountain_pact", "산악 맹약", "Mountain Pact Alliance", pre=["columbia_ties", "rhodes_ties"], theme=False, reward=[FLAG("pact")],
  desc=("'산악 맹약' 디시전이 열린다.", "Unlocks the Mountain Pact decisions."))

# 보강
for sid, ko, en, pre, econ in (
        ("fur_trade", "모피 교역", "Fur Trade", "winter_stores", False),
        ("ice_harvest", "얼음 채취", "Ice Harvest Industry", "mountain_roads", True),
        ("winter_drills", "동계 훈련", "Winter Drill Training", "avalanche_watch", False),
        ("snow_scouts", "설원 정찰대", "Snowfield Scouts", "mountain_folk", False),
        ("mountain_rescue", "산악 구조대", "Mountain Rescue Medical", "avalanche_watch", False),
        ("karlan_ledgers", "칼란 장부", "Karlan Ledgers Trade", "karlan_company", False),
        ("railway_ascent", "등산 철도", "Mountain Railway", "foreign_investment", True),
        ("factory_valleys", "공장 계곡", "Factory Valley Construction", "kjerag_bank", True),
        ("engineering_school", "공학 학교", "Engineering School", "tech_imports", False),
        ("stock_company", "주식회사", "Joint Stock Company", "kjerag_bank", False),
        ("modern_press", "근대 신문", "Modern Press Propaganda", "modern_army", False),
        ("ritual_calendar", "의례력", "Ritual Calendar Rites", "kjeragandr_faith", False),
        ("monastery_schools", "수도원 학교", "Monastery Schools", "elders_council", False),
        ("sacred_relics", "성유물", "Sacred Relics Archive", "sacred_peaks", False),
        ("pilgrim_trails", "순례길", "Pilgrim Trails Road", "sacred_peaks", True),
        ("faith_crusaders", "신앙 전사", "Faith Warrior Regiments", "faith_guardians", False),
        ("enciodas_estates", "엔시오다스 영지", "Enciodas Estates Farms", "enciodas_house", True),
        ("saintess_guard", "성녀 근위대", "Saintess Guard Regiments", "saintess_house", False),
        ("noble_hunt", "귀족 사냥 대회", "Noble Hunt Festival", "old_nobility", False),
        ("house_marriages", "가문 혼인", "House Marriage Alliance", "reconciliation", False),
        ("ski_raiders", "스키 기습대", "Ski Raid Squads", "ski_troops", False),
        ("ice_bunkers", "얼음 벙커", "Ice Bunker Fortifications", "snow_forts", False),
        ("sniper_school", "저격 학교", "Sniper Tactics School", "marksman_training", False),
        ("mountain_medics", "산악 의무대", "Mountain Medic Corps", "mountain_infantry", False),
        ("air_scouts", "산악 비행대", "Mountain Air Scouts", "mountain_guard", False),
        ("rifle_works", "소총 공방", "Rifle Workshops", "mountain_infantry", False),
        ("copper_mines", "구리 광산", "Copper Mines", "silver_mines", True),
        ("textile_mills", "모직 공장", "Wool Textile Mills", "timber", True),
        ("chemical_works", "화학 공업", "Chemical Works Industry", "hydro_power", True),
        ("leithanien_ties", "라이타니엔 교류", "Leithanien Exchange", "foreign_ties", False),
        ("sami_ties", "사미 교류", "Sami Contact Envoys", "foreign_ties", False),
        ("ursus_watch", "우르수스 경계", "Ursus Border Watch", "kazimierz_ties", False),
        ("unified_courts", "통합 법원", "Unified Courts Reform", "kjerag_charter", False),
        ("snow_temple_schools", "신전 학교", "Temple Schools Education", "snow_temples", False)):
    f(sid, ko, en, pre=[pre], econ=econ)

# ------------------------------------------------------------------ 디시전
cat_w = C.category("winter", "설산의 겨울", "Mountain Winter",
                   ("11월에 겨울이 오고 4월에 풀린다. 월동 준비를 해 두면 견딜 만한 겨울이 된다.",
                    "Winter comes in November and lifts in April. With preparations it will be bearable."), visible=[HAS("winter")])
C.d(cat_w, "prepare_winter", "월동 준비", "Winter Preparations", [FLAG("winter_ready")], cost=50, once=False, days_re_enable=300,
    available=["NOT = { %s }" % HAS("winter_ready")], desc=("다음 겨울을 견딜 만한 겨울로 만든다.", "Makes the next winter bearable."),
    icon="GFX_decision_generic_construction")
C.d(cat_w, "clear_passes", "산길 제설", "Clear the Passes",
    ["if = { limit = { has_idea = TU_KJE_harsh_winter } swap_ideas = { remove_idea = TU_KJE_harsh_winter add_idea = TU_KJE_mild_winter } }"],
    cost=75, once=False, days_re_enable=180, available=["has_idea = TU_KJE_harsh_winter"],
    desc=("지금의 혹독한 겨울을 견딜 만한 겨울로 바꾼다.", "Turn the current harsh winter into a bearable one."))
C.d(cat_w, "winter_festival", "설산 축제", "Snow Festival", ["add_stability = 0.03", "add_war_support = 0.02"], cost=25, once=False,
    days_re_enable=300, available=["OR = { has_idea = TU_KJE_harsh_winter has_idea = TU_KJE_mild_winter }"])
C.d(cat_w, "winter_offensive_drill", "동계 공세 훈련", "Winter Offensive Drill", ["army_experience = 20"], cost=50, once=False,
    days_re_enable=300, available=["OR = { has_idea = TU_KJE_harsh_winter has_idea = TU_KJE_mild_winter }"], icon="GFX_decision_generic_military")
C.d(cat_w, "fuel_imports", "연료 수입", "Import Fuel", [FLAG("winter_ready"), "add_political_power = -25"], cost=0, once=False,
    days_re_enable=300, visible=[HAS("karlan")], available=["NOT = { %s }" % HAS("winter_ready")])

cat_m = C.category("modern", "근대화와 전통", "Modernisation and Tradition",
                   ("근대화는 공장과 연구를, 전통은 신앙과 안정을 가져온다.", "Modernisation brings factories and research; tradition brings faith and stability."))
C.d(cat_m, "karlan_contract", "칼란 투자 계약", "Karlan Investment Contract", ["TU_build_civ_factory = yes", MOD(10)], cost=75, once=False,
    days_re_enable=240, visible=[HAS("karlan")], icon="GFX_decision_generic_factory")
C.d(cat_m, "foreign_engineers", "외국 기술자 초빙", "Invite Foreign Engineers",
    ["add_tech_bonus = { name = TU_KJE_engineers bonus = 0.75 uses = 1 category = industry category = electronics }", MOD(5)], cost=50,
    once=False, days_re_enable=240, visible=[HAS("karlan")])
C.d(cat_m, "temple_pilgrimage", "신전 순례", "Temple Pilgrimage", ["add_stability = 0.04", MOD(-10)], cost=25, once=False, days_re_enable=180)
C.d(cat_m, "saintess_sermon", "성녀의 설교", "Sermon of the Saintess", ["add_war_support = 0.04", MOD(-5)], cost=25, once=False, days_re_enable=180)
C.d(cat_m, "modern_schools", "근대 학교", "Modern Schools", ["add_political_power = -25", MOD(10), "add_stability = -0.02"], cost=25, once=False,
    days_re_enable=180)
C.d(cat_m, "house_council", "가문 회의 소집", "Convene the Houses", ["add_political_power = 60"], cost=25, once=False, days_re_enable=180,
    visible=["has_completed_focus = TU_KJE_three_houses_talks"])
C.d(cat_m, "silver_exports", "은 수출", "Silver Exports", ["add_political_power = 75", MOD(5)], cost=0, once=False, days_re_enable=240,
    visible=["has_completed_focus = TU_KJE_silver_mines"])
cat_f = C.category("pact", "산악 맹약", "Mountain Pact", icon="GFX_decision_category_generic_foreign_policy", visible=[HAS("pact")])
C.d(cat_f, "found_pact", "산악 맹약 결성", "Found the Mountain Pact", ["create_faction = TU_KJE_pact"], cost=50, available=["is_in_faction = no"])
C.loc("TU_KJE_pact", "산악 맹약", "Mountain Pact")
C.d(cat_f, "invite_pact", "맹약 초청", "Invite to the Pact", ["add_to_faction = FROM"], cost=50, once=False, days_re_enable=90,
    visible=["is_faction_leader = yes"],
    target=["NOT = { tag = ROOT }", "is_in_faction = no", "NOT = { has_war_with = ROOT }", "OR = { tag = KAZ tag = COL tag = SAM tag = LEI }"])
C.d(cat_f, "mountain_guides", "산악 안내인 파견", "Lend Mountain Guides", ["add_political_power = 50"], cost=0, once=False, days_re_enable=240)

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("만년설 아래", "Beneath the Eternal Snow"),
     ("칼란 무역의 화물열차가 산길을 오르고, 그 옆으로 순례자들이 성녀의 신전으로 걸어간다.",
      "Karlan Trade freight trains climb the passes, and pilgrims walk beside them to the Saintess's temple."),
     [("새 시대가 오고 있다.", "A new age is coming.", [MOD(5)], 50), ("옛것을 지켜야 한다.", "We must keep the old ways.", [MOD(-5)], 50)])
C.ev(10, ("겨울이 왔다", "Winter Has Come"),
     ("첫눈이 산길을 덮었다. 앞으로 다섯 달, 쉐라그는 눈 속에 갇힌다.", "The first snow covers the passes. For five months Kjerag will be locked in snow."),
     [("버틴다.", "We endure.", ["if = { limit = { %s } %s }" % (HAS("winter_master"), FLAG("winter_ready"))], 1)],
     picture="GFX_report_event_generic_defensive_preparations")
C.ev(11, ("봄의 해빙", "Spring Thaw"), ("눈이 녹고 산길이 열렸다.", "The snow melts and the passes open."),
     [("일을 시작하자.", "Back to work.", ["add_political_power = 10"], 1)])
C.ev(20, ("세 가문의 회담", "Talks of the Three Houses"),
     ("엔시오다스 가문의 실버애쉬, 성녀, 구귀족의 원로가 한 방에 앉았다. 침묵이 길었다.",
      "Silverash of House Enciodas, the Saintess and the old nobility's elder sit in one room. The silence was long."),
     [("실버애쉬의 말에 귀 기울인다.", "Listen to Silverash.", [MOD(10)], 40), ("성녀의 말에 귀 기울인다.", "Listen to the Saintess.", [MOD(-10)], 40),
      ("누구의 편도 들지 않는다.", "Take no side.", ["add_political_power = 25"], 20)])
C.ev(21, ("눈사태", "Avalanche"), ("거대한 눈사태가 산골 마을을 덮쳤다.", "A huge avalanche buried a mountain village."),
     [("구조대를 보낸다.", "Send rescuers.", ["add_political_power = -25", "add_stability = 0.02"], 70), ("봄을 기다린다.", "Wait for spring.", ["add_manpower = -2000"], 30)],
     trigger=["original_tag = KJE", "has_idea = TU_KJE_harsh_winter"], mtth=120, fire_once=False)
C.ev(22, ("칼란 무역의 스캔들", "Karlan Trade Scandal"), ("칼란 무역이 외국 자본에 광산을 넘겼다는 의혹이 제기됐다.", "Karlan Trade is accused of selling mines to foreign capital."),
     [("실버애쉬를 믿는다.", "Trust Silverash.", [MOD(5), "add_stability = -0.02"], 50), ("조사한다.", "Investigate.", [MOD(-5), "add_political_power = 25"], 50)],
     trigger=["original_tag = KJE", HAS("karlan")], mtth=300)
C.ev(23, ("성녀의 기적", "Miracle of the Saintess"), ("성녀의 기도 뒤 오래 앓던 아이가 일어났다는 소문이 퍼졌다.", "Rumour spreads that a long-sick child rose after the Saintess's prayer."),
     [("신을 찬양하라.", "Praise the god.", ["add_stability = 0.03", MOD(-5)], 1)],
     trigger=["original_tag = KJE", "has_completed_focus = TU_KJE_kjeragandr_faith"], mtth=300)
C.ev(24, ("철도 반대 시위", "Protest Against the Railway"), ("성스러운 봉우리를 지나는 철도 계획에 순례자들이 반대한다.", "Pilgrims protest a railway that would pass the sacred peaks."),
     [("계획을 밀어붙인다.", "Push it through.", [MOD(5), "add_stability = -0.03"], 50), ("노선을 바꾼다.", "Reroute it.", ["add_political_power = -30", MOD(-3)], 50)],
     trigger=["original_tag = KJE", "has_completed_focus = TU_KJE_railway_ascent"], mtth=200)
C.ev(25, ("구귀족의 불만", "The Old Nobility Grumbles"), ("구귀족들이 두 가문에 밀려 설 자리가 없다고 호소한다.", "The old nobility complains they are squeezed out by the other two houses."),
     [("영지를 보장한다.", "Guarantee their estates.", ["add_political_power = -25", "add_stability = 0.02"], 50), ("무시한다.", "Ignore them.", ["add_stability = -0.02"], 50)],
     trigger=["original_tag = KJE", "has_completed_focus = TU_KJE_three_houses_talks"], mtth=300)
C.ev(26, ("산 너머 손님", "Guests from Beyond the Mountains"), ("외국 기술자들이 산을 넘어왔다.", "Foreign engineers have crossed the mountains."),
     [("환영한다.", "Welcome them.", [MOD(5), "add_tech_bonus = { name = TU_KJE_guests bonus = 0.5 uses = 1 category = industry }"], 1)],
     trigger=["original_tag = KJE", AT_LEAST(50)], mtth=300)
C.ev(27, ("설산 축제", "Festival of the Snow"), ("온 나라가 눈 조각과 노래로 겨울을 즐겼다.", "The whole nation enjoyed winter with snow sculptures and songs."),
     [("즐겁다.", "Joyful.", ["add_stability = 0.02"], 1)],
     trigger=["original_tag = KJE", "has_idea = TU_KJE_mild_winter"], mtth=90)
C.ev(28, ("근대 쉐라그", "Modern Kjerag"), ("실버애쉬가 쉐라그의 미래를 이끈다.", "Silverash leads Kjerag into the future."),
     [("전진.", "Forward.", ["add_political_power = 50"], 1)])
C.ev(29, ("성녀의 신정", "Theocracy of the Saintess"), ("성녀가 쉐라그드르의 이름으로 나라를 맡았다.", "The Saintess has taken the nation in Kjeragandr's name."),
     [("신의 뜻대로.", "As the god wills.", ["add_stability = 0.05"], 1)])
C.ev(30, ("세 가문의 화합", "The Houses United"), ("세 가문이 처음으로 한 깃발 아래 섰다.", "For the first time, the three houses stand under one banner."),
     [("함께.", "Together.", ["add_stability = 0.05"], 1)])

# 추가 (목표 분량)
for sid, ko, en, pre, econ in (
        ("snow_chains", "눈길 장비", "Snow Chain Supply", "snow_tunnels", False),
        ("winter_hospitals", "겨울 병원", "Winter Hospitals", "mountain_rescue", False),
        ("frost_rations", "동계 식량", "Frost Ration Supply", "fur_trade", False),
        ("glacier_forts", "빙하 요새", "Glacier Fortresses", "winter_mastery", False),
        ("karlan_shipping", "칼란 운송", "Karlan Transport Companies", "karlan_ledgers", False),
        ("silverash_labs", "실버애쉬 연구소", "Silverash Research Laboratories", "engineering_school", False),
        ("modern_medicine", "근대 의학", "Modern Medicine Clinics", "stock_company", False),
        ("electric_grid", "전력망", "Electric Power Grid", "factory_valleys", True),
        ("armoured_sleds", "장갑 썰매", "Armoured Sled Units", "modern_army", False),
        ("air_force", "쉐라그 공군", "Kjerag Air Force", "modern_army", False),
        ("holy_texts", "경전 필사", "Holy Texts Archive", "monastery_schools", False),
        ("faith_festival", "신앙 축제", "Faith Festival", "ritual_calendar", False),
        ("temple_guards", "신전 경비대", "Temple Guard Regiments", "snow_temples", False),
        ("faith_charity", "신앙 구호", "Faith Charity Relief", "faith_guardians", False),
        ("house_treasury", "가문 금고", "Houses' Treasury", "house_marriages", False),
        ("noble_cavalry", "귀족 기병", "Noble Cavalry", "noble_hunt", False),
        ("enciodas_mines", "엔시오다스 광산", "Enciodas Mines", "enciodas_estates", True),
        ("saintess_hospitals", "성녀의 병원", "Saintess Hospitals Medical", "saintess_guard", False),
        ("unified_treasury", "통합 재정", "Unified Treasury", "unified_courts", False),
        ("alpine_artillery", "고산 포병", "Alpine Artillery", "mountain_artillery", False),
        ("snow_camouflage", "설상 위장", "Snow Camouflage Tactics", "ski_raiders", False),
        ("high_altitude", "고공 훈련", "High Altitude Training", "air_scouts", False),
        ("supply_lifts", "보급 리프트", "Supply Lift Logistics", "cable_cars", False),
        ("steel_works", "제철소", "Steel Works", "copper_mines", True),
        ("power_cables", "송전망", "Power Line Network", "hydro_power", True),
        ("ski_industry", "스키 산업", "Ski Industry", "textile_mills", True),
        ("victoria_trade", "빅토리아 교역", "Victoria Trade Accord", "columbia_ties", False),
        ("laterano_ties", "라테라노 교류", "Laterano Exchange", "leithanien_ties", False),
        ("yan_contact", "염국 접촉", "Yan Contact Envoys", "sami_ties", False),
        ("border_posts", "국경 초소", "Border Watchposts", "ursus_watch", False)):
    f(sid, ko, en, pre=[pre], econ=econ)
C.d(cat_w, "snow_patrols", "설원 순찰", "Snowfield Patrols", ["army_experience = 10", "add_stability = 0.02"], cost=25, once=False, days_re_enable=180)
C.d(cat_w, "stockpile_furs", "모피 비축", "Stockpile Furs", [FLAG("winter_ready"), "add_political_power = -10"], cost=25, once=False,
    days_re_enable=300, visible=["has_completed_focus = TU_KJE_fur_trade"], available=["NOT = { %s }" % HAS("winter_ready")])
C.d(cat_m, "railway_contract", "철도 계약", "Railway Contract", ["TU_build_infrastructure = yes", MOD(5)], cost=50, once=False,
    days_re_enable=240, visible=[HAS("karlan")], icon="GFX_decision_generic_construction")
C.d(cat_m, "faith_tithe", "신앙 십일조", "Faith Tithe", ["add_political_power = 60", MOD(-5)], cost=0, once=False, days_re_enable=240)
C.d(cat_m, "house_arbitration", "가문 중재", "Arbitrate the Houses", ["add_stability = 0.05"], cost=50, once=False, days_re_enable=240,
    visible=["has_completed_focus = TU_KJE_three_houses_talks"])
C.ev(31, ("실버애쉬의 연설", "Silverash's Speech"), ("실버애쉬가 의회에서 쉐라그의 미래를 연설했다. 젊은이들이 열광했다.", "Silverash spoke in parliament about Kjerag's future. The young were thrilled."),
     [("근대화를 가속한다.", "Accelerate modernisation.", [MOD(10), "add_stability = -0.02"], 1)],
     trigger=["original_tag = KJE", "has_completed_focus = TU_KJE_silverash_vision"], mtth=300)
C.ev(32, ("성스러운 봉우리의 빛", "Light on the Sacred Peak"), ("성스러운 봉우리에 오로라가 내려앉았다. 순례자들은 계시라고 믿는다.", "An aurora settled on the sacred peak. Pilgrims believe it a revelation."),
     [("신의 계시다.", "A revelation.", [MOD(-10), "add_stability = 0.03"], 1)],
     trigger=["original_tag = KJE", "has_completed_focus = TU_KJE_sacred_peaks"], mtth=300)

if __name__ == "__main__":
    C.write()
