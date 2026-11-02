#!/usr/bin/env python3
"""라테라노(LAT) 고유 콘텐츠 (사양서 17).

장치
  1. 순례자 TU_LAT_pilgrims (0~200): 매달 늘어난다 (on_monthly, 순례 관련 중점·국민정신이 늘림).
     디시전으로 정치력(헌금)·인력(순례자 의용대)·전쟁 지지(성인 축제)로 바꿔 쓴다.
  2. 영향력 TU_LAT_influence (0~100): 축성 총기 수출(대상 디시전)·특사·순례로 오른다.
     성약(진영)을 만들고 다른 나라를 초청할 때 쓴다.
  3. 타락 천사(추방된 산크타) 문제: 공증인 사무소의 추적 이벤트 사슬과 디시전.
정치 결말 셋 (서로 배타): 교황의 신정 / 공증인 공화국 / 열린 성도.

실행: python -I tools/focusgen/content/lat.py && python -I tools/focusgen/merge_focus.py --tag LAT
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_lib import Country  # noqa: E402

C = Country("LAT", "라테라노", "Laterano")
f = C.f


def VAR_EFFECT(var, n, ko, en, mx):
    name = "TU_LAT_%s_%s%d" % (var, "m" if n < 0 else "", abs(n))
    C.effects.append("""%s = {
	custom_effect_tooltip = %s_tt
	hidden_effect = {
		add_to_variable = { TU_LAT_%s = %d }
		clamp_variable = { var = TU_LAT_%s min = 0 max = %d }
	}
}""" % (name, name, var, n, var, mx))
    C.loc(name + "_tt", "%s %s%d" % (ko, "+" if n > 0 else "", n), "%s %s%d" % (en, "+" if n > 0 else "", n))
    return name


for n in (5, 10, 20, -10, -20, -30):
    VAR_EFFECT("pilgrims", n, "§G순례자§!", "§GPilgrims§!", 200)
for n in (5, 10, 15, -20):
    VAR_EFFECT("influence", n, "§G영향력§!", "§GInfluence§!", 100)


def PIL(n):
    return "TU_LAT_pilgrims_%s%d = yes" % ("m" if n < 0 else "", abs(n))


def INF(n):
    return "TU_LAT_influence_%s%d = yes" % ("m" if n < 0 else "", abs(n))


def AT_LEAST(var, n):
    return "check_variable = { TU_LAT_%s > %d }" % (var, n - 1)


def FLAG(x):
    return "set_country_flag = TU_LAT_%s" % x


def HAS(x):
    return "has_country_flag = TU_LAT_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_lat_ev.%d%s }" % (n, " days = %d" % days if days else "")


C.history += ["set_variable = { TU_LAT_pilgrims = 20 }", "set_variable = { TU_LAT_influence = 10 }",
              "add_ideas = { TU_LAT_holy_city TU_LAT_fallen_problem }"]
C.effects.append("""TU_LAT_monthly = {
	add_to_variable = { TU_LAT_pilgrims = 2 }
	if = { limit = { has_country_flag = TU_LAT_pilgrim_roads } add_to_variable = { TU_LAT_pilgrims = 2 } }
	if = { limit = { has_country_flag = TU_LAT_open_city } add_to_variable = { TU_LAT_pilgrims = 3 } }
	if = { limit = { has_war = yes } add_to_variable = { TU_LAT_pilgrims = -3 } }
	clamp_variable = { var = TU_LAT_pilgrims min = 0 max = 200 }
}""")
C.on_actions.append("""on_monthly = {
	effect = {
		if = {
			limit = { original_tag = LAT }
			TU_LAT_monthly = yes
		}
	}
}""")

# ------------------------------------------------------------------ 국민정신
C.idea("holy_city", "성도", "The Holy City", {"stability_factor": 0.1, "political_power_gain": 0.1, "conscription_factor": -0.2},
       "generic_political_support", ("라테라노는 산크타의 성도다. 작은 땅에 큰 권위가 있다.",
                                     "Laterano is the holy city of the Sankta: a small land with great authority."))
C.idea("fallen_problem", "타락 천사 문제", "The Fallen Problem", {"stability_factor": -0.05}, "generic_army_problems",
       ("광륜을 잃은 산크타들이 성도 밖을 떠돈다.", "Sankta who lost their halos wander outside the holy city."))
C.idea("blessed_arms", "축성 총기", "Blessed Firearms", {"army_attack_factor": 0.05, "production_factory_efficiency_gain_factor": 0.05},
       "generic_infantry_bonus")
C.idea("sankta_marksmen", "산크타 사수", "Sankta Marksmen", {"army_attack_factor": 0.08, "army_defence_factor": 0.03},
       "generic_infantry_bonus")
C.idea("pilgrim_economy", "순례 경제", "Pilgrim Economy", {"consumer_goods_factor": -0.03, "political_power_gain": 0.05},
       "generic_economic_increase")
C.idea("papal_theocracy", "교황의 신정", "Papal Theocracy", {"political_power_gain": 0.15, "stability_factor": 0.1, "war_support_factor": 0.05},
       "generic_political_support")
C.idea("notarial_republic", "공증인 공화국", "Notarial Republic", {"stability_factor": 0.15, "political_power_gain": 0.05},
       "constitutional_guarantees")
C.idea("open_city", "열린 성도", "The Open Holy City", {"monthly_population": 0.2, "conscription_factor": 0.1, "stability_factor": -0.03},
       "generic_pp_unity_bonus")
C.idea("covenant_spirit", "성약의 정신", "Spirit of the Covenant", {"political_power_gain": 0.1, "war_support_factor": 0.05},
       "generic_flexible_foreign_policy")
C.idea("laterano_guard", "라테라노 근위대", "Laterano Guard", {"army_org_factor": 0.08, "army_morale_factor": 0.05},
       "professional_officer_corps_spirit")
C.idea("reconciled_fallen", "화해한 타락 천사", "Reconciled Fallen", {"stability_factor": 0.05, "monthly_population": 0.1},
       "generic_morale_bonus")

# ------------------------------------------------------------------ 중점
f("root", "성도 라테라노", "The Holy City of Laterano", cost=5, theme=False, reward=["add_political_power = 50", EV(1)],
  desc=("총과 광륜의 도시. 교황청과 공증인 사무소가 함께 이 작은 성도를 다스린다.",
        "The city of guns and halos. The Holy See and the Notarial Hall rule this small holy city together."))

# A. 교황청
f("papal_council", "교황청 회의", "Papal Council", pre=["root"])
f("college_cardinals", "추기경단 소집", "Summon the College of Cardinals", pre=["papal_council"])
f("papal_decree", "교황 칙서", "Papal Decree", pre=["papal_council"], theme=False,
  reward=[FLAG("papal"), "add_political_power = 50"], desc=("'교황청' 디시전이 열린다.", "Unlocks the Holy See decisions."))
f("canonization", "시성식", "Canonization Ceremony", pre=["papal_decree"], reward=[PIL(10)])
f("sacred_texts", "경전 정비", "Sacred Texts Archive", pre=["college_cardinals"])
f("liturgy_reform", "전례 개혁", "Liturgy Reform", pre=["sacred_texts"])
f("papal_authority", "교황의 권위", "Papal Authority", pre=["liturgy_reform", "canonization"], me=["cardinals_accord"])
f("cardinals_accord", "추기경단의 합의", "Cardinals' Accord", pre=["liturgy_reform", "canonization"], me=["papal_authority"])
f("papal_theocracy", "교황의 신정", "Papal Theocracy", pre=[["papal_authority", "cardinals_accord"]],
  me=["notarial_republic", "open_city"], cost=15, theme=False,
  reward=[FLAG("path_papal"), "add_ideas = TU_LAT_papal_theocracy", EV(28)])
f("holy_inquisition", "신성 감찰", "Holy Inquisition Security", pre=["papal_theocracy"])
f("saint_processions", "성인 행렬", "Saint Processions", pre=["papal_theocracy"], reward=[PIL(10)])
f("crusade_preaching", "성전 설교", "Holy War Preaching Campaign", pre=["holy_inquisition"])
f("throne_of_saints", "성인의 옥좌", "Throne of Saints", pre=["crusade_preaching", "saint_processions"], theme=False,
  reward=["add_political_power = 100", "add_war_support = 0.1", INF(15)])

# B. 공증인 사무소
f("notarial_hall", "공증인 사무소", "Notarial Hall Office", pre=["root"])
f("laterano_law", "라테라노 법전", "Laterano Law Codex", pre=["notarial_hall"])
f("notary_network", "공증인 연락망", "Notary Network", pre=["notarial_hall"], theme=False,
  reward=[FLAG("notary"), INF(5)], desc=("'공증인 사무소' 디시전이 열린다.", "Unlocks the Notarial Hall decisions."))
f("contract_courts", "계약 법정", "Contract Courts", pre=["laterano_law"])
f("treaty_registry", "조약 등록소", "Treaty Registry", pre=["notary_network"], reward=[INF(5)])
f("fallen_registry", "타락 천사 명부", "Registry of the Fallen", pre=["notary_network"], theme=False,
  reward=[FLAG("fallen_registry"), EV(20, 10)])
f("notarial_republic", "공증인 공화국", "Notarial Republic", pre=["contract_courts", "treaty_registry"],
  me=["papal_theocracy", "open_city"], cost=15, theme=False,
  reward=[FLAG("path_notarial"), "add_ideas = TU_LAT_notarial_republic", EV(29)])
f("rule_of_law", "법의 지배", "Rule of Law Reform", pre=["notarial_republic"])
f("international_notary", "국제 공증", "International Notary Exchange", pre=["notarial_republic"], reward=[INF(10)])
f("neutral_arbiter", "중립 중재국", "Neutral Arbiter Accord", pre=["international_notary", "rule_of_law"], theme=False,
  reward=[INF(15), "add_stability = 0.1"])

# C. 총기
f("firearm_workshops", "총기 공방", "Firearm Workshops", pre=["root"])
f("hymn_ammunition", "성가 탄약", "Hymn Ammunition", pre=["firearm_workshops"])
f("blessing_rites", "총기 축성 의식", "Firearm Blessing Rites", pre=["firearm_workshops"], theme=False,
  reward=["add_ideas = TU_LAT_blessed_arms", FLAG("arms_export")],
  desc=("총을 축성해 판다. '축성 총기 수출' 디시전이 열린다.", "Bless guns and sell them. Unlocks the Blessed Firearm Export decision."))
f("rifle_standard", "표준 소총", "Standard Rifle Weapons", pre=["hymn_ammunition"])
f("marksman_school", "사수 학교", "Marksman Tactics School", pre=["rifle_standard"])
f("sniper_doctrine", "저격 교리", "Marksman Tactics", pre=["marksman_school"], me=["firepower_doctrine"])
f("firepower_doctrine", "화력 집중 교리", "Firepower Doctrine", pre=["marksman_school"], me=["sniper_doctrine"])
f("sankta_marksmen", "산크타 사수대", "Sankta Marksmen", pre=[["sniper_doctrine", "firepower_doctrine"]], theme=False,
  reward=["swap_ideas = { remove_idea = TU_LAT_blessed_arms add_idea = TU_LAT_sankta_marksmen }"])
f("cathedral_artillery", "성당 포대", "Cathedral Artillery", pre=["hymn_ammunition"])
f("arms_factories", "총기 공장", "Arms Factories", pre=["blessing_rites"], econ="TU_build_mil_factory = yes")
f("firearm_exports", "총기 수출", "Firearm Exports", pre=["arms_factories"], reward=[INF(5)])
f("exusiai_style", "엑시아식 속사", "Rapid Fire Drills", pre=["sankta_marksmen"])

# D. 근위대
f("laterano_guard", "라테라노 근위대", "Laterano Guard", pre=["root"])
f("guard_rapid", "수호천사 기동대", "Guardian Rapid Response Force", pre=["laterano_guard"])
f("holy_walls", "성도 성벽", "Holy City Walls", pre=["laterano_guard"])
f("air_patrol", "공중 순찰", "Air Patrol", pre=["guard_rapid"], me=["ground_patrol"])
f("ground_patrol", "지상 순찰", "Ground Patrol Watchtowers", pre=["guard_rapid"], me=["air_patrol"])
f("officer_school", "근위 장교 학교", "Guard Officer School", pre=["holy_walls"])
f("sankta_volunteers", "산크타 의용대", "Sankta Volunteers", pre=["officer_school"], theme=False,
  reward=[FLAG("volunteers"), "add_manpower = 5000"],
  desc=("'순례자 의용대' 디시전이 열린다.", "Unlocks the Pilgrim Volunteers decision."))
f("guard_spirit", "근위대의 정신", "Spirit of the Guard", pre=[["air_patrol", "ground_patrol"], "sankta_volunteers"], theme=False,
  reward=["add_ideas = TU_LAT_laterano_guard", "army_experience = 40"])
f("sky_apostles", "하늘의 사도", "Apostles of the Sky Wing", pre=["guard_spirit"])
f("anti_air_guns", "대공포", "Anti-Air Guns", pre=["holy_walls"])

# E. 순례 경제
f("pilgrimage", "순례 경제", "Pilgrimage Trade", pre=["root"], theme=False,
  reward=["add_ideas = TU_LAT_pilgrim_economy", FLAG("pilgrims"), PIL(10)],
  desc=("순례자들이 가져오는 헌금과 일손. '순례' 디시전이 열린다.", "The donations and hands pilgrims bring. Unlocks the Pilgrimage decisions."))
f("pilgrim_roads", "순례길 정비", "Pilgrim Roads", pre=["pilgrimage"], theme=False,
  reward=[FLAG("pilgrim_roads"), "TU_build_infrastructure = yes"], desc=("순례자가 매달 더 늘어난다.", "Pilgrims grow faster each month."),
  filt="FOCUS_FILTER_INDUSTRY")
f("guest_houses", "순례자 숙소", "Pilgrim Guest Houses", pre=["pilgrim_roads"], econ=True)
f("relic_trade", "성물 교역", "Relic Trade", pre=["pilgrimage"])
f("holy_bank", "성도 은행", "Holy City Bank", pre=["relic_trade"])
f("workshop_district", "공방 지구", "Workshop District", pre=["guest_houses"], econ=True)
f("civil_factories", "민간 공장 계획", "Civilian Factory Program", pre=["workshop_district"], econ=True)
f("research_halls", "성도 연구원", "Holy City Research Halls", pre=["holy_bank"])
f("holy_industry", "성도의 산업", "Holy City Industry", pre=["civil_factories", "research_halls"], econ=True)

# F. 성약 외교
f("covenant_idea", "성약의 꿈", "Dream of the Covenant Accord", pre=["root"], reward=[INF(5)])
f("envoys", "교황 특사", "Papal Envoys", pre=["covenant_idea"], theme=False,
  reward=[FLAG("covenant"), INF(10)],
  desc=("'성약' 디시전이 열린다. 영향력으로 다른 나라를 성약에 초청할 수 있다.",
        "Unlocks the Covenant decisions. Influence can bring other nations into the Covenant."))
f("victoria_ties", "빅토리아 대사관", "Victoria Embassy", pre=["envoys"])
f("columbia_ties", "컬럼비아 대사관", "Columbia Embassy", pre=["envoys"])
f("kazimierz_ties", "카시미어 교류", "Kazimierz Exchange", pre=["victoria_ties"])
f("iberia_question", "이베리아 문제", "The Iberia Question", pre=["columbia_ties"], theme=False,
  reward=[EV(24), INF(5)])
f("covenant_founding", "성약 결성", "Found the Holy Covenant Alliance", pre=["kazimierz_ties", "iberia_question"], theme=False,
  reward=["add_ideas = TU_LAT_covenant_spirit", INF(15)])

# G. 타락 천사
f("fallen_question", "타락 천사 문제", "The Fallen Question", pre=["fallen_registry"])
f("pursue_fallen", "추방자 추적", "Pursue the Fallen", pre=["fallen_question"], me=["pardon_fallen"], theme=False,
  reward=["add_stability = 0.03", EV(21, 15)])
f("pardon_fallen", "타락 천사 사면", "Pardon the Fallen", pre=["fallen_question"], me=["pursue_fallen"], theme=False,
  reward=["swap_ideas = { remove_idea = TU_LAT_fallen_problem add_idea = TU_LAT_reconciled_fallen }", EV(22, 15)])
f("open_city", "열린 성도", "The Open Holy City", pre=["pardon_fallen"], me=["papal_theocracy", "notarial_republic"], cost=15,
  theme=False, available=[AT_LEAST("pilgrims", 80)],
  reward=[FLAG("path_open"), FLAG("open_city"), "add_ideas = TU_LAT_open_city", EV(30)],
  desc=("산크타가 아닌 이들에게도 성도의 문을 연다. (순례자 80 이상)", "Open the holy city to those who are not Sankta. (Pilgrims 80+)"))
f("citizenship_reform", "시민권 개혁", "Citizenship Reform", pre=["open_city"])
f("refugee_shelters", "피난민 쉼터", "Refugee Shelters", pre=["citizenship_reform"])
f("city_of_all", "모두의 성도", "A Holy City for All", pre=["refugee_shelters"], theme=False,
  reward=["add_stability = 0.1", PIL(20)])

# 추가 중점 (갈래 보강)
f("choir_broadcast", "성가대 방송", "Choir Broadcast", pre=["papal_council"])
f("seminaries", "신학교", "Seminary Schools", pre=["sacred_texts"])
f("halo_studies", "광륜 연구", "Halo Studies Research", pre=["seminaries"])
f("cathedral_restoration", "대성당 복원", "Cathedral Restoration Construction", pre=["canonization"], econ=True)
f("papal_guards_expand", "교황 경호대 확장", "Expand the Papal Guard Regiments", pre=["holy_inquisition"])
f("missionaries", "선교사 파견", "Missionary Envoys", pre=["saint_processions"], reward=[INF(5)])
f("notary_academy", "공증인 학교", "Notary Academy School", pre=["laterano_law"])
f("archive_vaults", "기록 보관소", "Archive Vaults Records", pre=["treaty_registry"])
f("appeal_courts", "항소 법원", "Appeal Courts Reform", pre=["contract_courts"])
f("law_enforcement", "법 집행관", "Law Enforcement Police", pre=["rule_of_law"])
f("contract_bank", "계약 은행", "Contract Bank", pre=["international_notary"])
f("rifle_forges", "총열 대장간", "Rifle Barrel Forges", pre=["rifle_standard"])
f("blessed_bullets", "축성 탄환", "Blessed Bullet Munitions", pre=["cathedral_artillery"])
f("mortar_choir", "박격포 성가대", "Mortar Choir Artillery", pre=["blessed_bullets"])
f("smg_doctrine", "기관단총 교리", "Submachine Gun Tactics", pre=["sniper_doctrine"])
f("heavy_weapons", "중화기 공방", "Heavy Weapons Workshops", pre=["firepower_doctrine"])
f("gun_maintenance", "총기 정비 규정", "Gun Maintenance Supply", pre=["exusiai_style"])
f("export_guild", "수출 길드", "Arms Export Guild", pre=["firearm_exports"], reward=[INF(5)])
f("guard_drill", "근위대 훈련", "Guard Drill Training", pre=["laterano_guard"])
f("guard_medics", "근위 의무대", "Guard Medical Corps", pre=["guard_drill"])
f("bastion_gates", "성문 보루", "Bastion Gates", pre=["holy_walls"])
f("signal_bells", "경보 종탑", "Signal Bell Towers", pre=["bastion_gates"])
f("guard_reserves", "근위 예비대", "Guard Reserve Regiments", pre=["sankta_volunteers"])
f("air_chapel", "공군 예배당", "Air Chapel Airfield", pre=["sky_apostles"])
f("angel_fighters", "천사 전투기", "Angel Fighter Programme", pre=["air_chapel"])
f("city_defence", "성도 방위 계획", "Holy City Defence Plan", pre=["anti_air_guns", "signal_bells"])
f("pilgrim_markets", "순례자 시장", "Pilgrim Markets", pre=["relic_trade"])
f("incense_trade", "향료 교역", "Incense Trade", pre=["pilgrim_markets"])
f("donation_ledger", "헌금 장부", "Donation Ledger", pre=["holy_bank"])
f("pilgrim_rail", "순례 철도", "Pilgrim Railway", pre=["pilgrim_roads"], econ="TU_build_infrastructure = yes")
f("bell_foundry", "종 주조소", "Bell Foundry", pre=["workshop_district"], econ=True)
f("glass_works", "스테인드글라스 공방", "Stained Glass Works", pre=["bell_foundry"], econ=True)
f("arms_complex", "군수 공장 계획", "Arms Factory Program", pre=["civil_factories"], econ="TU_build_mil_factory = yes")
f("holy_power_grid", "성도 전력망", "Holy City Power Grid", pre=["pilgrim_rail"], econ="TU_build_infrastructure = yes")
f("university", "라테라노 대학", "University of Laterano", pre=["research_halls"])
f("research_slot", "교황청 과학원", "Pontifical Academy of Sciences", pre=["university"], theme=False,
  reward=["add_research_slot = 1"], desc=("연구 슬롯 +1", "Research slot +1"))
f("sargon_mission", "사르곤 선교", "Sargon Mission Envoys", pre=["covenant_idea"], reward=[INF(5)])
f("minos_dialogue", "미노스 대화", "Minos Dialogue Exchange", pre=["sargon_mission"])
f("leithanien_ties", "라이타니엔 교류", "Leithanien Exchange", pre=["kazimierz_ties"])
f("siracusa_ties", "시라쿠사 협약", "Siracusa Accord", pre=["columbia_ties"])
f("rhodes_ties", "로도스 아일랜드 협력", "Rhodes Island Cooperation Pact", pre=["envoys"])
f("covenant_army", "성약군", "Covenant Army Regiments", pre=["covenant_founding"])
f("covenant_council", "성약 회의", "Covenant Council", pre=["covenant_founding"], reward=[INF(10)])
f("fallen_hunters", "추적관 부대", "Fallen Hunter Squads", pre=["pursue_fallen"])
f("fallen_prisons", "속죄의 탑", "Tower of Atonement Security", pre=["fallen_hunters"])
f("fallen_return", "귀환자 정착", "Returnee Settlement Housing", pre=["pardon_fallen"])
f("halo_research", "광륜 상실 연구", "Halo Loss Research", pre=["fallen_return"])
f("open_markets", "열린 시장", "Open City Markets", pre=["citizenship_reform"])
f("foreign_quarter", "외국인 구역", "Foreign Quarter District", pre=["open_markets"], econ=True)
f("interfaith", "종교 간 대화", "Interfaith Dialogue Exchange", pre=["refugee_shelters"], reward=[INF(5)])

# ------------------------------------------------------------------ 디시전
cat_pil = C.category("pilgrims", "순례", "Pilgrimage",
                     ("순례자는 매달 늘어나고, 전쟁 중에는 줄어든다. 순례자를 헌금·의용대·축제로 쓸 수 있다.",
                      "Pilgrims grow each month and dwindle in wartime. They can be turned into donations, volunteers and festivals."),
                     visible=[HAS("pilgrims")])
C.d(cat_pil, "donations", "순례 헌금", "Pilgrim Donations", ["add_political_power = 75", PIL(-20)], cost=0, once=False,
    days_re_enable=90, available=[AT_LEAST("pilgrims", 20)], icon="GFX_decision_generic_fundraising",
    desc=("순례자 20을 써서 정치력 75를 얻는다.", "Spend 20 pilgrims for 75 political power."))
C.d(cat_pil, "pilgrim_levy", "순례자 의용대", "Pilgrim Volunteers", ["add_manpower = 8000", PIL(-30)], cost=25, once=False,
    days_re_enable=120, visible=[HAS("volunteers")], available=[AT_LEAST("pilgrims", 30)], icon="GFX_decision_generic_military",
    desc=("순례자 30을 써서 인력 8,000을 얻는다.", "Spend 30 pilgrims for 8,000 manpower."))
C.d(cat_pil, "saint_festival", "성인 축제", "Festival of Saints", ["add_war_support = 0.05", "add_stability = 0.03", PIL(-10)],
    cost=25, once=False, days_re_enable=180, available=[AT_LEAST("pilgrims", 10)])
C.d(cat_pil, "jubilee", "대희년", "The Great Jubilee", [PIL(20), INF(10), "add_stability = 0.05"], cost=100, once=False,
    days_re_enable=730, available=["has_war = no"], icon="GFX_decision_generic_political_address",
    desc=("2년에 한 번. 순례자와 영향력이 크게 오른다.", "Once every two years. A large boost to pilgrims and influence."))

cat_arms = C.category("arms", "축성 총기", "Blessed Firearms", visible=[HAS("arms_export")], icon="GFX_decision_category_military_operation")
C.d(cat_arms, "export_arms", "축성 총기 수출", "Export Blessed Firearms",
    ["FROM = { add_equipment_to_stockpile = { type = infantry_equipment amount = 300 producer = LAT } }",
     "add_political_power = 40", INF(5)], cost=0, once=False, days_re_enable=60,
    target=["NOT = { tag = ROOT }", "exists = yes", "NOT = { has_war_with = ROOT }", "NOT = { tag = WLD }"],
    desc=("대상 나라에 축성 소총 300정을 보낸다. 정치력 +40, 영향력 +5.", "Send 300 blessed rifles to the target. +40 political power, +5 influence."))
C.d(cat_arms, "arms_contract", "대량 총기 계약", "Bulk Arms Contract",
    ["TU_build_mil_factory = yes", INF(5)], cost=100, once=False, days_re_enable=365,
    visible=["has_completed_focus = TU_LAT_firearm_exports"], icon="GFX_decision_generic_factory")

cat_cov = C.category("covenant", "성약", "The Covenant", icon="GFX_decision_category_generic_foreign_policy",
                     desc=("영향력을 써서 다른 나라를 성약으로 이끈다.", "Spend influence to lead other nations into the Covenant."),
                     visible=[HAS("covenant")])
C.d(cat_cov, "found_covenant", "성약 진영 창설", "Found the Holy Covenant", ["create_faction = TU_LAT_covenant"], cost=50,
    available=["is_in_faction = no", AT_LEAST("influence", 30)], desc=("영향력 30 이상.", "Influence 30+."))
C.loc("TU_LAT_covenant", "성약", "The Holy Covenant")
C.d(cat_cov, "invite_covenant", "성약 초청", "Invite to the Covenant", ["add_to_faction = FROM", INF(-20)], cost=50, once=False,
    days_re_enable=60, visible=["is_faction_leader = yes"], available=[AT_LEAST("influence", 20)],
    target=["NOT = { tag = ROOT }", "is_in_faction = no", "NOT = { has_war_with = ROOT }", "NOT = { tag = WLD }",
            "is_major = no"],
    desc=("영향력 20을 써서 대상을 성약에 들인다 (주요국이 아닌 나라).", "Spend 20 influence to bring a non-major nation into the Covenant."))
C.d(cat_cov, "papal_mediation", "교황 중재", "Papal Mediation", ["add_political_power = 50", INF(5), "add_stability = 0.02"],
    cost=25, once=False, days_re_enable=180)

cat_hall = C.category("hall", "교황청과 공증인 사무소", "Holy See and Notarial Hall",
                      visible=["OR = {", "\t" + HAS("papal"), "\t" + HAS("notary"), "}"])
C.d(cat_hall, "papal_bull", "교황 칙서 반포", "Issue a Papal Bull", ["add_political_power = 60", "add_stability = 0.02"], cost=0,
    once=False, days_re_enable=180, visible=[HAS("papal")])
C.d(cat_hall, "canonize", "새 성인 시성", "Canonize a New Saint", ["add_war_support = 0.05", PIL(10)], cost=50, once=False,
    days_re_enable=365, visible=[HAS("papal")])
C.d(cat_hall, "notarize_treaty", "조약 공증", "Notarize a Treaty", [INF(5), "add_stability = 0.03"], cost=25, once=False,
    days_re_enable=120, visible=[HAS("notary")])
C.d(cat_hall, "hunt_fallen", "타락 천사 추적", "Hunt the Fallen", ["add_stability = 0.04", "add_political_power = -10"], cost=25,
    once=False, days_re_enable=180, visible=[HAS("fallen_registry"), "has_idea = TU_LAT_fallen_problem"])
C.d(cat_hall, "sankta_mercs", "산크타 용병 고용", "Hire Sankta Mercenaries",
    ["TU_LAT_guard_template = yes",
     "capital_scope = { create_unit = { division = \"division_template = \\\"TU_LAT_guard\\\" start_experience_factor = 0.5 start_equipment_factor = 1\" owner = LAT count = 2 } }"],
    cost=75, once=False, days_re_enable=240, visible=["has_completed_focus = TU_LAT_laterano_guard"], icon="GFX_decision_generic_military")
C.effects.append("""TU_LAT_guard_template = {
	if = {
		limit = { NOT = { has_country_flag = TU_LAT_guard_template_done } }
		set_country_flag = TU_LAT_guard_template_done
		division_template = {
			name = "TU_LAT_guard"
			is_locked = no
			priority = 2
			regiments = {
				infantry = { x = 0 y = 0 }
				infantry = { x = 0 y = 1 }
				infantry = { x = 1 y = 0 }
				infantry = { x = 1 y = 1 }
			}
		}
	}
}""")

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("성도의 아침", "Morning in the Holy City"),
     ("종소리와 총성이 함께 울린다. 라테라노에서 총은 기도와 같다. 오늘도 순례자들이 성문 앞에 줄을 섰다.",
      "Bells and gunshots ring together. In Laterano a gun is like a prayer. Pilgrims line up at the gates again today."),
     [("빛이 함께하기를.", "May the light be with you.", [PIL(5)], 1)], picture="GFX_report_event_generic_rally")
C.ev(20, ("명부 속의 이름", "A Name in the Registry"),
     ("타락 천사 명부를 정리하던 공증인이 유명한 이름 하나를 찾았다. 그는 지금 해외에서 용병으로 일하고 있다.",
      "A notary sorting the registry of the Fallen finds a famous name. That Sankta now works as a mercenary abroad."),
     [("소환장을 보낸다.", "Send a summons.", ["add_stability = 0.02"], 50),
      ("조용히 지켜본다.", "Watch quietly.", [INF(5)], 50)])
C.ev(21, ("추적의 끝", "End of the Pursuit"),
     ("공증인 사무소가 타락 천사 몇 명을 붙잡아 성도로 데려왔다. 시민들은 엇갈린 반응을 보였다.",
      "The Notarial Hall has caught several Fallen and brought them back. Citizens are divided."),
     [("법은 법이다.", "Law is law.", ["add_stability = 0.03", PIL(-10)], 50),
      ("자비를 베푼다.", "Show mercy.", [PIL(5), "add_stability = -0.02"], 50)])
C.ev(22, ("돌아온 이들", "Those Who Returned"),
     ("사면 소식을 듣고 광륜을 잃은 산크타들이 하나둘 돌아왔다.", "Hearing of the pardon, Sankta who lost their halos return one by one."),
     [("어서 오라.", "Welcome home.", ["add_manpower = 5000", PIL(10)], 1)])
C.ev(23, ("순례자 폭주", "Pilgrim Rush"),
     ("올해 순례자가 성도가 감당할 수 없을 만큼 몰려왔다.", "More pilgrims than the city can handle have arrived this year."),
     [("모두 받아들인다.", "Take them all in.", [PIL(20), "add_stability = -0.03"], 50),
      ("입장을 제한한다.", "Limit entry.", ["add_political_power = 25"], 50)],
     trigger=["original_tag = LAT", AT_LEAST("pilgrims", 100)], mtth=180)
C.ev(24, ("이베리아의 침묵", "The Silence of Iberia"),
     ("이베리아의 심판소가 라테라노 교회와 오래전 갈라선 일을 다시 꺼냈다. 화해의 기회일까, 갈등의 시작일까?",
      "Iberia's Inquisition revisits its old split from the Laterano church. A chance for reconciliation, or the start of conflict?"),
     [("화해의 특사를 보낸다.", "Send an envoy of reconciliation.", [INF(10), "add_political_power = -25"], 50),
      ("교리를 앞세운다.", "Stand on doctrine.", ["add_war_support = 0.03"], 50)])
C.ev(25, ("총기 축성 논쟁", "The Blessing Debate"),
     ("젊은 사제들이 '총을 축성하는 것이 옳은가'라는 물음을 던졌다.", "Young priests ask whether blessing guns is right."),
     [("총은 수호의 도구다.", "Guns are tools of protection.", ["add_war_support = 0.03"], 60),
      ("토론을 허락한다.", "Allow the debate.", ["add_stability = 0.02"], 40)],
     trigger=["original_tag = LAT", "has_idea = TU_LAT_blessed_arms"], mtth=300)
C.ev(26, ("성문 앞의 피난민", "Refugees at the Gate"),
     ("전쟁을 피해 온 피난민들이 성문 앞에 모였다. 그들 대부분은 산크타가 아니다.",
      "Refugees fleeing war gather at the gate. Most of them are not Sankta."),
     [("받아들인다.", "Let them in.", ["add_manpower = 3000", "add_stability = -0.02", PIL(5)], 50),
      ("돌려보낸다.", "Turn them away.", ["add_stability = 0.02"], 50)],
     trigger=["original_tag = LAT", "any_neighbor_country = { has_war = yes }"], mtth=200)
C.ev(28, ("교황의 신정", "Papal Theocracy"), ("교황의 말이 곧 법이 되었다.", "The Pope's word has become law."),
     [("빛 아래 하나로.", "One under the light.", ["add_stability = 0.05"], 1)])
C.ev(29, ("공증인 공화국", "Notarial Republic"), ("이제 라테라노를 다스리는 것은 법전과 공증인이다.", "Laterano is now ruled by its codex and its notaries."),
     [("계약은 지켜진다.", "Contracts will be kept.", ["add_stability = 0.05"], 1)])
C.ev(30, ("열린 성도", "The Open Holy City"), ("성문이 모두에게 열렸다. 산크타가 아닌 시민이 처음으로 생겼다.",
                                              "The gates have opened to all. For the first time, non-Sankta citizens exist."),
     [("빛은 모두에게.", "Light for everyone.", ["add_manpower = 5000"], 1)])

# 추가 디시전·이벤트
C.d(cat_pil, "relic_exhibition", "성유물 전시", "Relic Exhibition", ["add_political_power = 40", PIL(10)], cost=25, once=False,
    days_re_enable=240, visible=["has_completed_focus = TU_LAT_relic_trade"])
C.d(cat_pil, "pilgrim_clinics", "순례자 의료소", "Pilgrim Clinics", ["add_stability = 0.04", PIL(5)], cost=50, once=False,
    days_re_enable=240, icon="GFX_decision_generic_civil_support")
C.d(cat_arms, "arms_fair", "총기 박람회", "Firearms Fair", [INF(10), "add_political_power = 25"], cost=50, once=False,
    days_re_enable=365, icon="GFX_decision_generic_fundraising")
C.d(cat_hall, "guard_review", "근위대 사열", "Review the Guard", ["add_war_support = 0.04", "army_experience = 10"], cost=25,
    once=False, days_re_enable=180, visible=["has_completed_focus = TU_LAT_laterano_guard"])
C.d(cat_cov, "send_legates", "교황 사절 파견", "Send Papal Legates", [INF(10)], cost=50, once=False, days_re_enable=120)
C.d(cat_hall, "halo_grant", "광륜 연구 지원", "Fund Halo Research",
    ["add_tech_bonus = { name = TU_LAT_halo_grant bonus = 0.5 uses = 1 category = electronics }"], cost=50, once=False,
    days_re_enable=365, visible=["has_completed_focus = TU_LAT_halo_studies"])
C.ev(31, ("콘클라베", "The Conclave"), ("추기경들이 문을 걸어 잠그고 회의를 열었다. 성도 전체가 굴뚝의 연기를 지켜본다.",
                                       "The cardinals have locked the doors and convened. The whole city watches the chimney smoke."),
     [("흰 연기가 올랐다.", "White smoke rises.", ["add_stability = 0.05", PIL(10)], 1)],
     trigger=["original_tag = LAT", "has_completed_focus = TU_LAT_college_cardinals"], mtth=720)
C.ev(32, ("성도의 총기 사고", "Firearm Accident in the City"), ("축제 중 축포가 빗나가 부상자가 났다.", "A celebratory shot went astray during a festival and injured bystanders."),
     [("총기 규정을 강화한다.", "Tighten firearm rules.", ["add_stability = 0.02", "add_political_power = -10"], 50),
      ("축제는 계속된다.", "The festival goes on.", ["add_war_support = 0.02", "add_stability = -0.02"], 50)],
     trigger=["original_tag = LAT", "has_completed_focus = TU_LAT_firearm_workshops"], mtth=360)
C.ev(33, ("외국 순례 사절단", "A Foreign Pilgrim Delegation"), ("먼 나라의 고관들이 순례를 왔다. 그들은 라테라노와 가까워지고 싶어 한다.",
                                                      "Dignitaries from a distant land have come on pilgrimage, hoping to grow closer to Laterano."),
     [("환대한다.", "Welcome them.", [INF(10), "add_political_power = -15"], 1)],
     trigger=["original_tag = LAT", AT_LEAST("pilgrims", 50)], mtth=300)
C.ev(34, ("광륜의 기적", "Miracle of the Halo"), ("광륜을 잃었던 산크타의 머리 위에 다시 빛이 떠올랐다는 소문이 돌았다.",
                                              "Rumour says the light has returned above the head of a Sankta who had lost their halo."),
     [("기적이다!", "A miracle!", [PIL(20), "add_stability = 0.03"], 1)],
     trigger=["original_tag = LAT", "has_idea = TU_LAT_reconciled_fallen"], mtth=360)

if __name__ == "__main__":
    C.write()
