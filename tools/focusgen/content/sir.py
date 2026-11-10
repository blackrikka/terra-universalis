#!/usr/bin/env python3
"""시라쿠사(SIR) 중점·디시전·이벤트 (사양서 17, 다시 설계: 사양서 63).

구조 (중점 126개, 한 판에 보이는 것은 66개: 사양서 71)
  뿌리 '늑대의 땅' -> 이벤트 tu_sir_ev.1 '시라쿠사의 갈림길'에서 정치 루트 다섯 중 하나를 고른다.
    벨로네(건설·산업, 지도자 벨로네) / 감비노(군사, 감비노 대부) / 살루초(돈·외교, 살루초 대부) /
    법(안정·연구, 페넌스) / 늑대(공격·정복, 라플란드 더 데카덴차)
    고르면 지도자가 바로 바뀌고 그 루트 갈래(15개)만 보인다 (allow_branch = TU_SIR_route_<key>). 다섯 갈래는 같은 자리에 겹친다
    (tools/focusgen/block_layout.py). 결말 중점에서 국호가 바뀐다 (tools/chargen/data.py 의 hooks).
    루트 하나 = 머리 + 본 갈래 둘(3개씩) + 옆 갈래(3개, 선택) + 합류 + 결말 + 결말 뒤 2개 + 통일.
  공통 갈래: 산업(20), 군사(20), 외교(10). 모든 효과는 중점에 직접 적혀 있다 (이름 테마 자동 보상 없음).
장치
  세 패밀리의 영향력 TU_SIR_bellone / gambino / saluzzo (0~100, 매달 +1), 법의 권위 TU_SIR_law.
  '패밀리' 디시전으로 거래·단속. 두 패밀리가 60 이상이면 패밀리 전쟁 이벤트.

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
C.effects.append("TU_SIR_monthly = {\n" + "".join(
    """	if = {
		limit = { has_country_flag = TU_SIR_route_%(k)s }
		set_variable = { TU_SIR_%(k)s = 100 }
	}
	else_if = {
		limit = { has_country_flag = TU_SIR_absorbed_%(k)s }
		set_variable = { TU_SIR_%(k)s = 0 }
	}
	else = {
		add_to_variable = { TU_SIR_%(k)s = 1 }
		clamp_variable = { var = TU_SIR_%(k)s min = 0 max = 100 }
	}
""" % dict(k=k) for k in ("bellone", "gambino", "saluzzo")) + """	if = { limit = { has_country_flag = TU_SIR_courts } add_to_variable = { TU_SIR_law = 1 } }
	clamp_variable = { var = TU_SIR_law min = 0 max = 100 }
	TU_SIR_unrest_tick = yes
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

# ------------------------------------------------------------------ 루트 (사양서 63)
# 첫 중점 '늑대의 땅' 뒤 이벤트 tu_sir_ev.1 '시라쿠사의 갈림길'에서 다섯 루트 중 하나를 고른다.
# 고르는 순간 지도자가 바뀌고 그 루트의 갈래만 트리에 나타난다 (allow_branch). 다섯 갈래는 같은 자리에 겹쳐 있다
# (tools/focusgen/block_layout.py). 결말 중점(finale)에서 국호가 바뀐다 (chargen hooks).
ROUTES = [
    # key, 이름, 영문, 지도자 id, 이념, 한 줄 설명, 루트 시작 국민정신, 결말 국민정신
    ("bellone", "벨로네", "Bellone", "bellone", "oligarchism",
     ("건설과 산업. 공장을 가장 많이 얻는다.", "Construction and industry. The most factories.")),
    ("gambino", "감비노", "Gambino", "gambino_don", "fascism_ideology",
     ("군사와 동원. 공격력과 병력이 강하다.", "Army and mobilisation. Strong attack and manpower.")),
    ("saluzzo", "살루초", "Saluzzo", "saluzzo_don", "oligarchism",
     ("돈과 외교. 정치력과 연구가 빠르다.", "Money and diplomacy. Fast political power and research.")),
    ("law", "법", "Law", "penance", "conservatism",
     ("패밀리를 무너뜨리는 법치. 안정도와 연구.", "Rule of law against the families. Stability and research.")),
    ("wolf", "늑대", "Wolf", "lappland_decadenza", "despotism",
     ("늑대 군주의 힘. 공격과 정복.", "The power of the Wolf Lord. Attack and conquest.")),
]
LEADER_KO = {"bellone": "벨로네", "gambino": "감비노 대부", "saluzzo": "살루초 대부", "law": "페넌스 (라비니아)",
             "wolf": "라플란드 더 데카덴차"}
LEADER_EN = {"bellone": "Bellone", "gambino": "Don Gambino", "saluzzo": "Don Saluzzo", "law": "Penance (Lavinia)",
             "wolf": "Lappland the Decadenza"}
PARTY = {"oligarchism": "neutrality", "despotism": "neutrality", "fascism_ideology": "fascism", "conservatism": "democratic"}


def choose(key, leader, ideology):
    g = PARTY[ideology]
    return [FLAG("route_%s" % key), FLAG("route_chosen"),
            "recruit_character = TU_SIR_%s" % leader,
            "set_politics = { ruling_party = %s elections_allowed = %s }" % (g, "yes" if g == "democratic" else "no"),
            "promote_character = {\n\tcharacter = TU_SIR_%s\n\tideology = %s\n}" % (leader, ideology),
            "add_ideas = TU_SIR_%s_start" % key, "mark_focus_tree_layout_dirty = yes"] + (
        ["set_variable = { TU_SIR_%s = 100 }" % key] if key in ("bellone", "gambino", "saluzzo") else []) + (
        ["retire_character = TU_SIR_lappland"] if key == "wolf" else [])


def R(key, sid, ko, en, pre, reward, cost=10, me=(), desc=("", ""), available=()):
    """루트 안 중점. 루트 머리(pre=['root'])에는 allow_branch 를 단다."""
    ab = [HAS("route_%s" % key)] if pre == ["root"] else []
    return f(sid, ko, en, pre=pre, me=me, cost=cost, theme=False, reward=reward, desc=desc, available=available, allow_branch=ab)


# ------------------------------------------------------------------ 국민정신
C.idea("omerta", "오메르타", "Omerta", {"stability_factor": 0.05, "political_power_gain": -0.1, "war_support_factor": -0.05},
       "generic_secret_police", ("침묵의 규율. 누구도 패밀리에 대해 말하지 않는다.", "The code of silence. No one speaks of the families."))
C.idea("family_cities", "패밀리의 도시들", "Cities of the Families", {"production_speed_buildings_factor": -0.05, "consumer_goods_factor": 0.03},
       "generic_foreign_capital", ("도시마다 주인이 따로 있다. 공사 하나에도 패밀리의 허락이 필요하다.",
                                    "Every city has its own master. Even a building permit needs a family's blessing."))
C.idea("bellone_start", "벨로네 건설 연합", "Bellone Construction Union",
       {"production_speed_buildings_factor": 0.10, "industrial_capacity_factory": 0.05}, "generic_industrial_concern_1")
C.idea("gambino_start", "감비노 행동대", "Gambino Enforcers", {"army_attack_factor": 0.05, "conscription_factor": 0.10},
       "generic_manpower_bonus")
C.idea("saluzzo_start", "살루초의 장부", "Saluzzo Ledgers", {"political_power_gain": 0.15, "consumer_goods_factor": -0.02},
       "generic_economic_increase")
C.idea("law_start", "법정의 시대", "Age of the Courts", {"stability_factor": 0.05, "research_speed_factor": 0.03},
       "constitutional_guarantees")
C.idea("wolf_start", "늑대 무리", "The Wolf Pack", {"army_attack_factor": 0.05, "war_support_factor": 0.10, "army_morale_factor": 0.05},
       "generic_war_preparation")
C.idea("bellone_end", "벨로네의 시라쿠사", "Bellone's Siracusa",
       {"production_speed_buildings_factor": 0.20, "industrial_capacity_factory": 0.10,
        "political_power_gain": 0.10}, "generic_industrial_concern_1")
C.idea("gambino_end", "감비노의 철권", "Gambino's Iron Fist",
       {"army_attack_factor": 0.12, "army_org_factor": 0.08, "conscription_factor": 0.15, "training_time_factor": -0.15},
       "generic_manpower_bonus")
C.idea("saluzzo_end", "살루초의 금고", "The Saluzzo Vault",
       {"political_power_gain": 0.25, "consumer_goods_factor": -0.05, "research_speed_factor": 0.08, "trade_opinion_factor": 0.25},
       "generic_economic_increase")
C.idea("law_end", "법의 시라쿠사", "Siracusa of Law",
       {"stability_factor": 0.15, "research_speed_factor": 0.10, "production_speed_buildings_factor": 0.10},
       "constitutional_guarantees")
C.idea("wolf_end", "늑대 군주의 귀환", "Return of the Wolf Lord",
       {"army_attack_factor": 0.15, "army_morale_factor": 0.10, "war_support_factor": 0.15, "army_speed_factor": 0.05},
       "generic_war_preparation")
C.idea("urban_warfare", "시가전 전문가", "Urban Warfare Experts", {"army_defence_factor": 0.08, "army_org_factor": 0.03},
       "generic_fortify_the_borders")
C.idea("wine_and_olive", "포도주와 올리브", "Wine and Olives", {"consumer_goods_factor": -0.03, "stability_factor": 0.03},
       "generic_agrarian_society")

# 이벤트 본문은 양피지 배경이라 색 글씨(§Y)가 안 보인다: 색 없이 쓴다
ROUTE_GUIDE = "\\n".join("[%s] %s — %s" % (ko, LEADER_KO[k], d[0]) for k, ko, _, _, _, d in ROUTES)
ROUTE_GUIDE_EN = "\\n".join("[%s] %s — %s" % (en, LEADER_EN[k], d[1]) for k, _, en, _, _, d in ROUTES)
# 선택지는 한 줄에 들어가게 짧게 (선택지 5개가 화면 아래로 넘치지 않게)
SHORT = {"bellone": ("벨로네 — 건설·산업", "Bellone — industry"), "gambino": ("감비노 — 군사·동원", "Gambino — army"),
         "saluzzo": ("살루초 — 돈·외교", "Saluzzo — money"), "law": ("페넌스 — 법치·안정", "Penance — law"),
         "wolf": ("라플란드 — 늑대·정복", "Lappland — conquest")}

# ------------------------------------------------------------------ 중점: 뿌리
f("root", "늑대의 땅", "Land of Wolves", cost=5, theme=False, reward=["add_political_power = 50", FLAG("families"), EV(1)],
  desc=("시라쿠사의 도시들은 정부가 아니라 패밀리가 다스린다. 이 중점을 마치면 §Y시라쿠사의 갈림길§! 이벤트에서 다섯 루트 중 하나를 고른다.\\n\\n"
        + ROUTE_GUIDE,
        "Siracusa's cities are ruled by families, not the government. Completing this focus lets you choose one of five routes "
        "in the §YCrossroads of Siracusa§! event.\\n\\n" + ROUTE_GUIDE_EN))

# ---- 벨로네: 건설·산업
R("bellone", "bellone_head", "벨로네의 시대", "The Bellone Era", ["root"], ["add_political_power = 75"], cost=5,
  desc=("§Y벨로네 루트§! (지도자: 벨로네)\\n건설과 산업. 공장을 가장 많이 얻는다.\\n결말 '벨로네의 시라쿠사': 건설 속도 +20%, 공장 출력 +10%.",
        "§YBellone route§! (Leader: Bellone)\\nConstruction and industry.\\nEnding: construction +20%, factory output +10%."))
R("bellone", "bellone_company", "벨로네 건설 회사", "Bellone Construction Company", ["bellone_head"], ["TU_build_civ_factory = yes"])
R("bellone", "bellone_docks", "벨로네 부두", "Bellone Docks", ["bellone_company"], ["TU_build_civ_factory = yes", "add_political_power = 25"])
R("bellone", "bellone_rail", "벨로네 철도", "Bellone Railway", ["bellone_docks"], ["TU_build_infrastructure = yes", "TU_build_civ_factory = yes"])
R("bellone", "bellone_quarries", "대리석 채석장", "Marble Quarries", ["bellone_head"],
  ["random_owned_controlled_state = { limit = { is_coastal = no } add_resource = { type = steel amount = 6 } }",
   "add_tech_bonus = { name = TU_SIR_bellone_quarries bonus = 0.5 uses = 1 category = construction_tech }"])
R("bellone", "bellone_steel", "벨로네 제철소", "Bellone Steelworks", ["bellone_quarries"], ["TU_build_mil_factory = yes"])
R("bellone", "bellone_district", "벨로네 공업 지구", "Bellone Industrial District", ["bellone_steel"],
  ["TU_build_civ_factory = yes", "TU_build_civ_factory = yes"])
R("bellone", "bellone_rebuild", "재건의 시라쿠사", "Rebuilding Siracusa", ["bellone_rail", "bellone_district"],
  ["add_tech_bonus = { name = TU_SIR_bellone_rebuild bonus = 1.0 uses = 2 category = industry }", "add_stability = 0.05"], cost=10)
R("bellone", "bellone_end", "벨로네의 시라쿠사", "Bellone's Siracusa", ["bellone_rebuild"],
  ["swap_ideas = { remove_idea = TU_SIR_bellone_start add_idea = TU_SIR_bellone_end }", "remove_ideas = TU_SIR_family_cities",
   "TU_build_civ_factory = yes", EV(28)], cost=15,
  desc=("결말. 국호가 '벨로네의 시라쿠사'가 된다.", "Ending. The country becomes Bellone's Siracusa."))

# 벨로네 옆 갈래 (시정) + 결말 뒤 (사양서 71)
R("bellone", "bellone_cityhall", "시청 접수", "Take City Hall", ["bellone_head"], ["add_political_power = 60", "add_stability = 0.03"])
R("bellone", "bellone_union", "건설 노동자 조합", "Builders' Union", ["bellone_cityhall"], ["add_manpower = 10000", "add_stability = 0.03"])
R("bellone", "bellone_school", "벨로네 기술 학교", "Bellone Technical School", ["bellone_union"],
  ["add_tech_bonus = { name = TU_SIR_bellone_school bonus = 1.0 uses = 2 category = construction_tech category = industry }"])
R("bellone", "bellone_newcity", "누오바 볼시니 선언", "Declaration of Nuova Volsinii", ["bellone_end"],
  ["capital_scope = { add_extra_state_shared_building_slots = 2 }", "TU_build_civ_factory = yes", "TU_build_civ_factory = yes"],
  desc=("패밀리의 손이 닿지 않는 새 도시를 선포한다. 민간 공장 2개, 수도 건물 칸 +2.",
        "Proclaim a new city beyond the families' reach. Two civilian factories, +2 capital building slots."))
R("bellone", "bellone_fund", "재건 기금", "Reconstruction Fund", ["bellone_end"],
  ["TU_build_infrastructure = yes", "TU_build_infrastructure = yes", "add_political_power = 100"])

# ---- 감비노: 군사·동원
R("gambino", "gambino_head", "감비노의 시대", "The Gambino Era", ["root"], ["add_manpower = 10000"], cost=5,
  desc=("§Y감비노 루트§! (지도자: 감비노 대부)\\n군사와 동원. 공격력과 병력이 강하다.\\n결말 '감비노의 철권': 공격 +12%, 조직력 +8%, 징집 +15%, 훈련 시간 -15%.",
        "§YGambino route§! (Leader: Don Gambino)\\nArmy and mobilisation.\\nEnding: attack +12%, org +8%, conscription +15%, training time -15%."))
R("gambino", "gambino_soldiers", "감비노 행동대", "Gambino Soldiers", ["gambino_head"], ["army_experience = 25", "add_manpower = 10000"])
R("gambino", "gambino_arsenal", "감비노 무기고", "Gambino Arsenal", ["gambino_soldiers"],
  ["TU_build_mil_factory = yes", "add_tech_bonus = { name = TU_SIR_gambino_arsenal bonus = 1.0 uses = 1 category = infantry_weapons }"])
R("gambino", "gambino_training", "감비노 훈련장", "Gambino Training Grounds", ["gambino_arsenal"],
  ["army_experience = 40", "add_tech_bonus = { name = TU_SIR_gambino_training bonus = 1.0 uses = 1 category = infantry_tech }"])
R("gambino", "gambino_contracts", "청부 계약", "Hitman Contracts", ["gambino_head"], ["add_political_power = 50", "army_experience = 15"])
R("gambino", "gambino_streets", "패밀리 시가전 교리", "Family Street War Doctrine", ["gambino_contracts"],
  ["add_tech_bonus = { name = TU_SIR_gambino_streets bonus = 1.0 uses = 1 category = support_tech }", "army_experience = 25"])
R("gambino", "gambino_militia", "패밀리 민병대", "Family Militias", ["gambino_streets"],
  ["add_manpower = 25000", "TU_build_mil_factory = yes"])
R("gambino", "gambino_legion", "감비노 군단", "The Gambino Legion", ["gambino_training", "gambino_militia"],
  ["army_experience = 50", "add_war_support = 0.10"])
R("gambino", "gambino_end", "감비노의 철권", "Gambino's Iron Fist", ["gambino_legion"],
  ["swap_ideas = { remove_idea = TU_SIR_gambino_start add_idea = TU_SIR_gambino_end }", "remove_ideas = TU_SIR_family_cities",
   "TU_build_mil_factory = yes", EV(28)], cost=15,
  desc=("결말. 국호가 '감비노의 시라쿠사'가 된다.", "Ending. The country becomes Gambino's Siracusa."))

# 감비노 옆 갈래 (암흑가) + 결말 뒤 (사양서 71)
R("gambino", "gambino_police", "경찰 매수", "Buy the Police", ["gambino_head"], ["add_stability = 0.05", LAW(-10)])
R("gambino", "gambino_smuggle", "무기 밀수", "Arms Smuggling", ["gambino_police"],
  ["add_equipment_to_stockpile = { type = infantry_equipment amount = 1500 producer = SIR }"],
  desc=("보병 장비 1500.", "1,500 infantry equipment."))
R("gambino", "gambino_network", "암흑가 정보망", "Underworld Network", ["gambino_smuggle"], ["army_experience = 30", "add_political_power = 50"])
R("gambino", "gambino_mobilize", "총동원령", "General Mobilisation", ["gambino_end"], ["add_manpower = 40000", "add_war_support = 0.05"])
R("gambino", "gambino_campaign", "남부 원정 계획", "Southern Campaign Plan", ["gambino_end"],
  ["army_experience = 60", "add_command_power = 30", "TU_build_mil_factory = yes"])

# ---- 살루초: 돈·외교
R("saluzzo", "saluzzo_head", "살루초의 시대", "The Saluzzo Era", ["root"], ["add_political_power = 100"], cost=5,
  desc=("§Y살루초 루트§! (지도자: 살루초 대부)\\n돈과 외교. 정치력과 연구가 빠르다.\\n결말 '살루초의 금고': 정치력 +25%, 연구 +8%, 소비재 -5%.",
        "§YSaluzzo route§! (Leader: Don Saluzzo)\\nMoney and diplomacy.\\nEnding: political power +25%, research +8%, consumer goods -5%."))
R("saluzzo", "saluzzo_bank", "살루초 은행", "Saluzzo Bank", ["saluzzo_head"], ["add_political_power = 75", "TU_build_civ_factory = yes"])
R("saluzzo", "saluzzo_trade", "살루초 교역망", "Saluzzo Trade Network", ["saluzzo_bank"],
  ["add_political_power = 50", "add_tech_bonus = { name = TU_SIR_saluzzo_trade bonus = 1.0 uses = 1 category = electronics }"])
R("saluzzo", "saluzzo_diaspora", "해외 패밀리망", "Overseas Family Network", ["saluzzo_trade"],
  ["add_research_slot = 1"], desc=("연구 슬롯 +1", "Research slot +1"))
R("saluzzo", "saluzzo_smuggling", "밀수 항로", "Smuggling Routes", ["saluzzo_head"], [FLAG("smuggling"), "add_political_power = 40"],
  desc=("'밀수 과세' 디시전이 열린다.", "Unlocks the Smuggling Tax decision."))
R("saluzzo", "saluzzo_casinos", "카지노 교역", "Casino Trade", ["saluzzo_smuggling"], [FLAG("casinos"), "TU_build_civ_factory = yes"],
  desc=("'카지노 허가' 디시전이 열린다.", "Unlocks the Casino Licence decision."))
R("saluzzo", "saluzzo_freeport", "자유항", "Free Port", ["saluzzo_casinos"], ["TU_build_civ_factory = yes", "add_political_power = 50"])
R("saluzzo", "saluzzo_keys", "금고의 열쇠", "Keys to the Vault", ["saluzzo_diaspora", "saluzzo_freeport"],
  ["add_political_power = 100", "add_tech_bonus = { name = TU_SIR_saluzzo_keys bonus = 1.0 uses = 2 category = industry category = electronics }"])
R("saluzzo", "saluzzo_end", "살루초의 금고", "The Saluzzo Vault", ["saluzzo_keys"],
  ["swap_ideas = { remove_idea = TU_SIR_saluzzo_start add_idea = TU_SIR_saluzzo_end }", "remove_ideas = TU_SIR_family_cities", EV(28)],
  cost=15, desc=("결말. 국호가 '살루초의 시라쿠사'가 된다.", "Ending. The country becomes Saluzzo's Siracusa."))

# 살루초 옆 갈래 (정계) + 결말 뒤 (사양서 71)
R("saluzzo", "saluzzo_deputies", "의원 매수", "Buy the Deputies", ["saluzzo_head"], ["add_political_power = 120"])
R("saluzzo", "saluzzo_press", "언론 장악", "Own the Press", ["saluzzo_deputies"], ["add_stability = 0.05", "add_war_support = 0.03"])
R("saluzzo", "saluzzo_foundation", "살루초 재단", "The Saluzzo Foundation", ["saluzzo_press"],
  ["add_tech_bonus = { name = TU_SIR_saluzzo_foundation bonus = 1.0 uses = 2 category = industry category = electronics category = tu_originium_tech }"])
R("saluzzo", "saluzzo_finance", "테라의 금고", "Vault of Terra", ["saluzzo_end"],
  ["add_offsite_building = { type = industrial_complex level = 2 }"], desc=("영토 밖 민간 공장 +2.", "Two off-map civilian factories."))
R("saluzzo", "saluzzo_mercs", "용병 계약금", "Mercenary Retainers", ["saluzzo_end"],
  ["add_manpower = 20000", "army_experience = 40", "TU_build_mil_factory = yes"])

# ---- 법: 안정·연구
R("law", "law_head", "법정의 시대", "The Age of the Courts", ["root"], [FLAG("courts"), LAW(10)], cost=5,
  desc=("§Y법 루트§! (지도자: 페넌스, 라비니아)\\n패밀리를 무너뜨리는 법치. 안정도와 연구.\\n법의 권위가 매달 오르고 '대부 체포' 디시전을 쓸 수 있다.\\n"
        "결말 '법의 시라쿠사': 안정도 +15%, 연구 +10%, 건설 +10%.",
        "§YLaw route§! (Leader: Penance, Lavinia)\\nRule of law against the families.\\n"
        "Ending: stability +15%, research +10%, construction +10%."))
R("law", "law_judges", "청렴한 판사들", "Honest Judges", ["law_head"], [LAW(10), "add_stability = 0.05"])
R("law", "law_omerta", "침묵을 깨다", "Break the Silence", ["law_judges"], ["remove_ideas = TU_SIR_omerta", LAW(10), EV(23)],
  desc=("오메르타를 없앤다.", "Removes Omerta."))
R("law", "law_academy", "법학원", "Legal Academy", ["law_omerta"],
  ["add_tech_bonus = { name = TU_SIR_law_academy bonus = 1.0 uses = 2 category = electronics category = industry }"])
R("law", "law_police", "시민 질서 경찰", "Public Order Police", ["law_head"], [LAW(5), "add_stability = 0.05"])
R("law", "law_bureau", "반패밀리 수사단", "Anti-Family Bureau", ["law_police"], [LAW(10), FLAG("witness")],
  desc=("단속 디시전이 더 강해진다 (영향력 -25).", "Crackdowns become stronger (influence -25)."))
R("law", "law_works", "공공 사업", "Public Works", ["law_bureau"], ["TU_build_civ_factory = yes", "TU_build_infrastructure = yes"])
R("law", "law_constitution", "시라쿠사 헌법", "Siracusan Constitution", ["law_academy", "law_works"],
  [LAW(10), "add_stability = 0.05", "add_political_power = 75"])
R("law", "law_end", "법의 시라쿠사", "Siracusa of Law", ["law_constitution"],
  ["swap_ideas = { remove_idea = TU_SIR_law_start add_idea = TU_SIR_law_end }", "remove_ideas = TU_SIR_family_cities", EV(29)],
  cost=15, desc=("결말. 국호가 '법의 시라쿠사'가 된다.", "Ending. The country becomes the Siracusa of Law."))

# 법 옆 갈래 (시민) + 결말 뒤 (사양서 71)
R("law", "law_press", "자유 언론", "Free Press", ["law_head"], ["add_stability = 0.05"])
R("law", "law_jury", "배심원 제도", "Jury System", ["law_press"], [LAW(10), "add_political_power = 50"])
R("law", "law_militia", "시민 방위대", "Citizens' Guard", ["law_jury"], ["add_manpower = 15000", "army_experience = 25"])
R("law", "law_charter", "누오바 볼시니 헌장", "Charter of Nuova Volsinii", ["law_end"],
  ["TU_build_civ_factory = yes", "TU_build_civ_factory = yes", "add_stability = 0.05"],
  desc=("법으로 세운 새 도시의 헌장. 민간 공장 2개, 안정도 +5%.", "The charter of a new city founded on law. Two civilian factories, stability +5%."))
R("law", "law_cooperation", "반패밀리 국제 공조", "International Anti-Family Pact", ["law_end"],
  ["LAT = { add_opinion_modifier = { target = ROOT modifier = TU_dip_aid } }", "RIM = { add_opinion_modifier = { target = ROOT modifier = TU_dip_aid } }",
   "add_political_power = 100"], desc=("라테라노·림 빌리튼과 관계 개선, 정치력 +100.", "Better relations with Laterano and Rim Billiton, political power +100."))

# ---- 늑대: 공격·정복
R("wolf", "wolf_head", "늑대 군주의 유산", "Legacy of the Wolf Lord", ["root"], ["add_war_support = 0.05", EV(20)], cost=5,
  desc=("§Y늑대 루트§! (지도자: 라플란드 더 데카덴차)\\n늑대 군주의 힘. 공격과 정복.\\n"
        "결말 '늑대 군주의 귀환': 공격 +15%, 사기 +10%, 전쟁 지지 +15%, 이웃 나라에 전쟁 명분.",
        "§YWolf route§! (Leader: Lappland the Decadenza)\\nThe power of the Wolf Lord.\\n"
        "Ending: attack +15%, morale +10%, war support +15%, war goals on neighbours."))
R("wolf", "wolf_rites", "늑대의 의례", "Rites of the Wolves", ["wolf_head"], [FLAG("rites"), EV(21, 10)],
  desc=("'늑대의 의례 거행' 디시전이 열린다.", "Unlocks the Wolf Rite decision."))
R("wolf", "wolf_relics", "늑대의 유물", "Relics of the Wolves", ["wolf_rites"], ["army_experience = 40", "add_war_support = 0.05"])
R("wolf", "wolf_citadel", "늑대의 성채", "Citadel of the Wolf", ["wolf_relics"], ["TU_build_mil_factory = yes", EV(25)])
R("wolf", "wolf_lappland", "라플란드의 귀환", "Lappland Returns", ["wolf_head"], [EV(22, 7), "army_experience = 25"])
R("wolf", "wolf_pack", "늑대 무리 군단", "Wolf Pack Legion", ["wolf_lappland"],
  ["add_manpower = 15000", "add_tech_bonus = { name = TU_SIR_wolf_pack bonus = 1.0 uses = 1 category = infantry_tech }"])
R("wolf", "wolf_howl", "포효 교리", "Howl Doctrine", ["wolf_pack"],
  ["add_tech_bonus = { name = TU_SIR_wolf_howl bonus = 1.0 uses = 1 category = support_tech }", "army_experience = 25"])
R("wolf", "wolf_crown", "늑대의 왕관", "Crown of the Wolf", ["wolf_citadel", "wolf_howl"], ["add_war_support = 0.10", "army_experience = 50"])
R("wolf", "wolf_end", "늑대 군주의 귀환", "Return of the Wolf Lord", ["wolf_crown"],
  ["swap_ideas = { remove_idea = TU_SIR_wolf_start add_idea = TU_SIR_wolf_end }", "remove_ideas = TU_SIR_family_cities",
   "every_neighbor_country = { limit = { NOT = { is_in_faction_with = ROOT } } ROOT = { create_wargoal = { type = annex_everything target = PREV } } }",
   EV(30)], cost=15, desc=("결말. 국호가 '늑대 군주의 시라쿠사'가 되고 이웃 나라 모두에 병합 명분을 얻는다.",
                          "Ending. The country becomes the Wolf Lord's Siracusa and gains war goals on all neighbours."))

# 늑대 옆 갈래 (송곳니) + 결말 뒤 (사양서 71)
C.idea("night_hunters", "밤의 사냥꾼", "Hunters of the Night", {"land_night_attack": 0.20, "army_speed_factor": 0.05},
       "generic_war_preparation", ("늑대는 밤에 사냥한다.", "Wolves hunt at night."))
R("wolf", "wolf_fangs", "송곳니 선발", "Choosing the Fangs", ["wolf_head"], ["army_experience = 40"])
R("wolf", "wolf_grounds", "사냥터 개척", "Opening the Hunting Grounds", ["wolf_fangs"], ["add_manpower = 15000", "TU_build_mil_factory = yes"])
R("wolf", "wolf_oath", "달의 서약", "Oath of the Moon", ["wolf_grounds"], ["add_war_support = 0.10", "add_stability = 0.03"])
R("wolf", "wolf_night", "밤의 군주", "Lords of the Night", ["wolf_end"], ["add_ideas = TU_SIR_night_hunters"],
  desc=("국민정신 '밤의 사냥꾼': 야간 공격 +20%, 이동 속도 +5%.", "Spirit Hunters of the Night: night attack +20%, speed +5%."))
R("wolf", "wolf_hunt", "대사냥", "The Great Hunt", ["wolf_end"], ["add_manpower = 30000", "army_experience = 50", "add_command_power = 30"])

POSTS = {"bellone": ["bellone_newcity", "bellone_fund"], "gambino": ["gambino_mobilize", "gambino_campaign"],
         "saluzzo": ["saluzzo_finance", "saluzzo_mercs"], "law": ["law_charter", "law_cooperation"], "wolf": ["wolf_night", "wolf_hunt"]}
# ---- 통일 (사양서 69): 결말 뒤, 경쟁 패밀리를 모두 굴복시키면 ('패밀리' 디시전) 찍을 수 있다
RIVALS = {"bellone": ["gambino", "saluzzo"], "gambino": ["bellone", "saluzzo"], "saluzzo": ["bellone", "gambino"],
          "law": ["bellone", "gambino", "saluzzo"], "wolf": ["bellone", "gambino", "saluzzo"]}
FAM_KO = {k: ko for k, ko, _ in FAM}
FAM_EN = {k: en for k, _, en in FAM}
UNITY = {"bellone": ("벨로네 아래 하나로", "One Under Bellone"), "gambino": ("감비노 아래 하나로", "One Under Gambino"),
         "saluzzo": ("살루초 아래 하나로", "One Under Saluzzo"), "law": ("패밀리 없는 시라쿠사", "A Siracusa Without Families"),
         "wolf": ("모든 늑대는 한 무리", "All Wolves, One Pack")}
C.idea("one_siracusa", "하나의 시라쿠사", "One Siracusa",
       {"stability_factor": 0.10, "political_power_gain": 0.10, "army_org_factor": 0.05, "war_support_factor": 0.05},
       "generic_central_management", ("경쟁하던 패밀리가 모두 무릎을 꿇었다. 시라쿠사는 처음으로 하나다.",
                                       "Every rival family has knelt. For the first time, Siracusa is one."))
for key in RIVALS:
    rk = "·".join(FAM_KO[x] for x in RIVALS[key])
    re_ = ", ".join(FAM_EN[x] for x in RIVALS[key])
    R(key, "%s_unity" % key, UNITY[key][0], UNITY[key][1], POSTS[key],
      ["add_ideas = TU_SIR_one_siracusa", "if = { limit = { has_idea = TU_SIR_omerta } remove_ideas = TU_SIR_omerta }",
       "add_political_power = 100"], cost=10, available=[HAS("absorbed_%s" % x) for x in RIVALS[key]],
      desc=("§Y%s§! 패밀리를 모두 굴복시켜야 한다 ('패밀리' 디시전: 영향력 20 이하일 때 '굴복시키기').\\n"
            "국민정신 '하나의 시라쿠사': 안정도 +10%%, 정치력 +10%%, 조직력 +5%%, 전쟁 지지 +5%%. 오메르타가 사라진다." % rk,
            "Requires the §Y%s§! families subdued (Families decisions: Subdue at influence 20 or less).\\n"
            "Spirit One Siracusa: stability +10%%, political power +10%%, org +5%%, war support +5%%. Removes Omerta." % re_))

# ------------------------------------------------------------------ 중점: 산업 (모든 루트 공통)
def I(sid, ko, en, pre, reward, me=(), cost=10, desc=("", "")):
    return f(sid, ko, en, pre=pre, me=me, cost=cost, theme=False, reward=reward, desc=desc, filt="FOCUS_FILTER_INDUSTRY",
             icon="GFX_goal_generic_construct_civ_factory")


I("wine_olive", "포도주와 올리브", "Wine and Olives", ["root"], ["add_ideas = TU_SIR_wine_and_olive"])
I("wine_exports", "포도주 수출 계약", "Wine Export Contracts", ["wine_olive"], ["add_political_power = 75"])
I("industrial_district", "공업 지구", "Industrial District", ["wine_olive"], ["TU_build_civ_factory = yes"])
I("road_network", "도로망", "Road Network", ["industrial_district"], ["TU_build_infrastructure = yes", "TU_build_infrastructure = yes"])
I("rail_network", "철도망", "Rail Network", ["road_network"],
  ["TU_build_infrastructure = yes", "add_tech_bonus = { name = TU_SIR_rail bonus = 1.0 uses = 1 category = train_tech }"])
I("power_plants", "발전소", "Power Plants", ["rail_network"], ["TU_build_civ_factory = yes"])
I("civil_factories", "민간 공장 계획", "Civilian Factory Programme", ["industrial_district"],
  ["TU_build_civ_factory = yes", "TU_build_civ_factory = yes"], me=["arms_factories"],
  desc=("민간 공장 2개. (군수 공장 계획과 택일)", "Two civilian factories. (Exclusive with the Arms Factory Programme)"))
I("arms_factories", "군수 공장 계획", "Arms Factory Programme", ["industrial_district"],
  ["TU_build_mil_factory = yes", "TU_build_mil_factory = yes"], me=["civil_factories"],
  desc=("군수 공장 2개. (민간 공장 계획과 택일)", "Two military factories. (Exclusive with the Civilian Factory Programme)"))
I("legitimate_business", "합법 사업 전환", "Legitimate Business", [["civil_factories", "arms_factories"]],
  ["TU_build_civ_factory = yes", "add_tech_bonus = { name = TU_SIR_business bonus = 1.0 uses = 2 category = industry }"])
I("research_institute", "시라쿠사 연구소", "Siracusa Research Institute", ["legitimate_business"],
  ["add_tech_bonus = { name = TU_SIR_institute bonus = 1.0 uses = 2 category = electronics category = tu_originium_tech }"])
I("academy", "시라쿠사 학술원", "Siracusa Academy of Sciences", ["research_institute"], ["add_research_slot = 1"],
  desc=("연구 슬롯 +1", "Research slot +1"))
I("steel_works", "제철소", "Steel Works", ["rail_network"], ["TU_build_mil_factory = yes"])
I("chemical_plants", "화학 공장", "Chemical Plants", ["steel_works"],
  ["add_tech_bonus = { name = TU_SIR_chem bonus = 1.0 uses = 1 category = synth_resources }", "TU_build_civ_factory = yes"])
I("industrialisation", "시라쿠사 산업화", "Siracusan Industrialisation", ["power_plants", "academy"],
  ["TU_build_civ_factory = yes", "TU_build_civ_factory = yes", "TU_build_mil_factory = yes"], cost=15)


# 산업 보강 (사양서 71)
C.idea("miracle", "시라쿠사의 기적", "The Siracusan Miracle", {"industrial_capacity_factory": 0.05, "production_speed_buildings_factor": 0.10},
       "generic_production_bonus", ("패밀리의 도시가 공장의 도시가 되었다.", "The cities of the families have become cities of factories."))
I("farm_coop", "농업 협동조합", "Farm Cooperatives", ["wine_olive"], ["add_manpower = 10000", "add_stability = 0.03"])
I("cargo_contract", "화물 비행선 계약", "Cargo Airship Contract", ["wine_exports"],
  ["add_equipment_to_stockpile = { type = convoy_1 amount = 15 producer = SIR }"],
  desc=("화물 비행선 15대. 바다 건너 무역에 쓴다.", "Fifteen cargo airships for overseas trade."))
I("power_grid", "전력망", "Power Grid", ["power_plants"],
  ["TU_build_infrastructure = yes", "add_tech_bonus = { name = TU_SIR_grid bonus = 1.0 uses = 1 category = electronics }"])
I("refinery", "오리지늄 정제소", "Originium Refinery", ["chemical_plants"],
  ["random_owned_controlled_state = { limit = { is_controlled_by = ROOT infrastructure > 0 } add_extra_state_shared_building_slots = 1 "
   "add_building_construction = { type = originium_refinery level = 1 instant_build = yes } }",
   "add_tech_bonus = { name = TU_SIR_refinery bonus = 1.0 uses = 1 category = tu_originium_tech }"],
  desc=("오리지늄 정제소 1단계와 오리지늄 공학 연구 보너스.", "One Originium refinery level and an Originium engineering research bonus."))
I("oripathy_lab", "광석병 연구소", "Oripathy Laboratory", ["academy"],
  ["add_tech_bonus = { name = TU_SIR_oripathy bonus = 1.0 uses = 2 category = tu_oripathy_tech }", "add_stability = 0.03"])
I("miracle", "시라쿠사의 기적", "The Siracusan Miracle", ["industrialisation"], ["add_ideas = TU_SIR_miracle"], cost=15,
  desc=("국민정신 '시라쿠사의 기적': 공장 출력 +5%, 건설 속도 +10%.", "Spirit The Siracusan Miracle: factory output +5%, construction +10%."))


# ------------------------------------------------------------------ 중점: 군사 (모든 루트 공통)
def M(sid, ko, en, pre, reward, me=(), cost=10, desc=("", "")):
    return f(sid, ko, en, pre=pre, me=me, cost=cost, theme=False, reward=reward, desc=desc, filt="FOCUS_FILTER_RESEARCH",
             icon="GFX_goal_generic_small_arms")


M("bodyguards", "패밀리 경호대", "Family Bodyguards", ["root"], ["army_experience = 20", "add_manpower = 5000"])
M("urban_tactics", "시가전 전술", "Urban Warfare Tactics", ["bodyguards"],
  ["add_tech_bonus = { name = TU_SIR_urban bonus = 1.0 uses = 1 category = infantry_tech }"])
M("rapid_squads", "기동 타격대", "Rapid Strike Squads", ["urban_tactics"],
  ["add_tech_bonus = { name = TU_SIR_rapid bonus = 1.0 uses = 1 category = motorized_equipment }", "army_experience = 20"],
  me=["fortress_cities"], desc=("공격형. (요새 도시와 택일)", "Offensive. (Exclusive with Fortress Cities)"))
M("fortress_cities", "요새 도시", "Fortress Cities", ["urban_tactics"], ["TU_build_forts_1 = yes", "add_stability = 0.03"],
  me=["rapid_squads"], desc=("방어형. 국경에 요새를 짓는다. (기동 타격대와 택일)", "Defensive. Builds border forts. (Exclusive with Rapid Strike Squads)"))
M("urban_experts", "시가전 전문가", "Urban Warfare Experts", [["rapid_squads", "fortress_cities"]],
  ["add_ideas = TU_SIR_urban_warfare", "army_experience = 30"])
M("arms_workshops", "무기 공방", "Arms Workshops", ["bodyguards"],
  ["add_tech_bonus = { name = TU_SIR_workshops bonus = 1.0 uses = 1 category = infantry_weapons }"])
M("artillery", "포병 중대", "Artillery Batteries", ["arms_workshops"],
  ["add_tech_bonus = { name = TU_SIR_artillery bonus = 1.0 uses = 1 category = artillery }"])
M("army_command", "시라쿠사 군 사령부", "Siracusan Army Command", ["urban_experts", "artillery"],
  ["army_experience = 50", "add_tech_bonus = { name = TU_SIR_command bonus = 1.0 uses = 1 category = support_tech }"])
M("motor_pools", "차량 정비소", "Motor Pools", ["army_command"],
  ["add_tech_bonus = { name = TU_SIR_motor bonus = 1.0 uses = 1 category = motorized_equipment }"])
M("armoured_cars", "장갑차 부대", "Armoured Car Units", ["motor_pools"],
  ["add_tech_bonus = { name = TU_SIR_armor bonus = 1.0 uses = 1 category = armor }"])
M("reserves", "예비군", "Army Reserves", ["army_command"], ["add_manpower = 20000"])
M("officer_academy", "사관학교", "Officer Academy", ["reserves"], ["army_experience = 50", "add_command_power = 20"])
M("air_squadron", "시라쿠사 비행대", "Siracusan Air Squadron", ["officer_academy"],
  ["air_experience = 25", "add_tech_bonus = { name = TU_SIR_air bonus = 1.0 uses = 1 category = light_fighter }"])


# 군사 보강 (사양서 71)
C.idea("general_staff", "시라쿠사 총참모부", "Siracusan General Staff", {"army_org_factor": 0.05, "planning_speed": 0.15},
       "generic_army_war_college", ("패밀리의 행동대가 아니라 나라의 군대다.", "No longer family enforcers, but a national army."))
M("motor_strike", "차량화 타격대", "Motorised Strike Force", ["rapid_squads"],
  ["add_tech_bonus = { name = TU_SIR_motor_strike bonus = 1.0 uses = 1 category = motorized_equipment }", "army_experience = 20"])
M("border_line", "국경 방어선", "Border Defence Line", ["fortress_cities"], ["TU_build_forts_2 = yes"],
  desc=("국경 요새를 한 단계 더 올린다.", "Raises the border forts another level."))
M("engineers", "공병대", "Combat Engineers", ["arms_workshops"],
  ["add_tech_bonus = { name = TU_SIR_engineers bonus = 1.0 uses = 1 category = engineers_tech category = cat_fortification }"])
M("anti_air", "대공 포대", "Anti-Air Batteries", ["artillery"],
  ["add_tech_bonus = { name = TU_SIR_aa bonus = 1.0 uses = 1 category = cat_anti_air }"])
M("field_hospital", "야전 병원", "Field Hospitals", ["reserves"],
  ["add_tech_bonus = { name = TU_SIR_hospital bonus = 1.0 uses = 1 category = hospital_tech }", "add_manpower = 5000"])
M("arts_corps", "아츠 술사 부대", "Arts Caster Corps", ["officer_academy"],
  ["add_tech_bonus = { name = TU_SIR_arts bonus = 1.0 uses = 2 category = tu_originium_tech }", "army_experience = 20"])
M("general_staff", "시라쿠사 총참모부", "Siracusan General Staff", ["armoured_cars", "air_squadron"], ["add_ideas = TU_SIR_general_staff"],
  cost=15, desc=("국민정신 '시라쿠사 총참모부': 조직력 +5%, 계획 속도 +15%.", "Spirit Siracusan General Staff: org +5%, planning speed +15%."))


# ------------------------------------------------------------------ 중점: 외교 (모든 루트 공통)
def D(sid, ko, en, pre, reward, me=(), desc=("", "")):
    return f(sid, ko, en, pre=pre, me=me, cost=10, theme=False, reward=reward, desc=desc, icon="GFX_goal_generic_diplomatic_treaty")


D("foreign_ministry", "외무부", "Foreign Ministry", ["root"], ["add_political_power = 50"])
D("laterano_accord", "라테라노 협약", "Laterano Accord", ["foreign_ministry"],
  ["add_political_power = 50", "add_stability = 0.03"])
D("rhodes_office", "로도스 아일랜드 사무소", "Rhodes Island Office", ["foreign_ministry"],
  ["add_tech_bonus = { name = TU_SIR_rhodes bonus = 1.0 uses = 1 category = tu_oripathy_tech }"])
D("neutral_siracusa", "중립 시라쿠사", "Neutral Siracusa", ["laterano_accord", "rhodes_office"],
  ["add_stability = 0.10", "add_political_power = 75"], me=["southern_league"],
  desc=("전쟁에서 빠진다. 안정도 +10%. (남부 연맹과 택일)", "Stay out of wars. Stability +10%. (Exclusive with the Southern League)"))
D("southern_league", "남부 연맹", "Southern League", ["laterano_accord", "rhodes_office"], [FLAG("league"), "add_war_support = 0.05"],
  me=["neutral_siracusa"], desc=("'남부 연맹' 디시전이 열린다: 라테라노·림 빌리튼·이베리아·라이타니엔을 초청한다. (중립 시라쿠사와 택일)",
                                 "Unlocks the Southern League decisions. (Exclusive with Neutral Siracusa)"))

# 외교 보강 (사양서 71)
C.idea("armed_neutrality", "무장 중립", "Armed Neutrality", {"army_core_defence_factor": 0.15, "stability_factor": 0.05},
       "generic_fortify_the_borders", ("누구의 편도 들지 않는다. 대신 누구도 들어오지 못한다.", "We take no side, and no one gets in."))
D("leithanien_pact", "라이타니엔 불가침 조약", "Leithanien Non-Aggression Pact", ["foreign_ministry"],
  ["diplomatic_relation = { country = LEI relation = non_aggression_pact active = yes }", "add_political_power = 25"],
  desc=("라이타니엔과 불가침 조약을 맺는다.", "Sign a non-aggression pact with Leithanien."))
D("penguin_logistics", "펭귄 로지스틱스 계약", "Penguin Logistics Contract", ["foreign_ministry"],
  ["add_equipment_to_stockpile = { type = convoy_1 amount = 15 producer = SIR }",
   "LGM = { add_opinion_modifier = { target = ROOT modifier = TU_dip_trade } }"],
  desc=("용문의 운송 회사와 계약한다. 화물 비행선 15대, 용문과 관계 개선.", "Contract Lungmen's courier company. Fifteen cargo airships, better relations with Lungmen."))
D("rim_minerals", "림 빌리튼 광물 협정", "Rim Billiton Minerals Accord", ["laterano_accord"],
  ["random_owned_controlled_state = { add_resource = { type = tungsten amount = 6 } }",
   "RIM = { add_opinion_modifier = { target = ROOT modifier = TU_dip_trade } }"],
  desc=("망간 +6, 림 빌리튼과 관계 개선.", "Manganese +6, better relations with Rim Billiton."))
D("armed_neutrality", "무장 중립", "Armed Neutrality", ["neutral_siracusa"], ["add_ideas = TU_SIR_armed_neutrality"],
  desc=("국민정신 '무장 중립': 본토 방어 +15%, 안정도 +5%.", "Spirit Armed Neutrality: core defence +15%, stability +5%."))
D("league_defence", "남부 방위 조약", "Southern Defence Treaty", ["southern_league"],
  ["add_war_support = 0.05", "army_experience = 30",
   "add_tech_bonus = { name = TU_SIR_league bonus = 1.0 uses = 1 category = support_tech category = infantry_tech }"])

# ------------------------------------------------------------------ 디시전
cat_fam = C.category("families", "패밀리", "The Families",
                     ("세 패밀리의 영향력은 매달 오른다. 거래하면 그 패밀리가 강해지고 법이 약해진다. 단속하면 반대다.",
                      "The three families grow every month. Dealing with one strengthens it and weakens the law; cracking down does the opposite."),
                     visible=[HAS("families")])
bonus = {"bellone": ["TU_build_civ_factory = yes"], "gambino": ["add_manpower = 10000"], "saluzzo": ["add_political_power = 75"]}
# 굴복시키기 (사양서 69): 경쟁 패밀리의 영향력이 20 이하면 완전히 굴복시킨다. 그 뒤로 그 패밀리는 자라지 않는다
SUBDUE = {"bellone": (["TU_build_civ_factory = yes", "TU_build_civ_factory = yes"], "민간 공장 2개", "two civilian factories"),
          "gambino": (["add_manpower = 20000", "army_experience = 30"], "인력 2만, 육군 경험치 30", "20,000 manpower, 30 army experience"),
          "saluzzo": (["add_political_power = 150",
                       "add_tech_bonus = { name = TU_SIR_subdue_saluzzo bonus = 1.0 uses = 1 category = industry category = electronics }"],
                      "정치력 150, 연구 보너스", "150 political power, a research bonus")}


def RIVAL(k):
    """집권 패밀리도 아니고 굴복하지도 않은 패밀리만 디시전 대상이다."""
    return ["NOT = { %s }" % HAS("route_%s" % k), "NOT = { %s }" % HAS("absorbed_%s" % k)]


for k, ko, en in FAM:
    C.d(cat_fam, "subdue_%s" % k, "%s 굴복시키기" % ko, "Subdue the %s" % en,
        [FLAG("absorbed_%s" % k), "set_variable = { TU_SIR_%s = 0 }" % k] + SUBDUE[k][0], cost=75, once=True,
        visible=RIVAL(k) + [HAS("route_chosen")], available=[BELOW(k, 21)],
        desc=("%s 패밀리를 완전히 굴복시킨다. (영향력 20 이하) 다시는 세력이 자라지 않는다. 보상: %s.\\n"
              "경쟁 패밀리를 모두 굴복시키면 루트 마지막 '통일' 중점을 찍을 수 있다." % (ko, SUBDUE[k][1]),
              "Subdue the %s family for good. (Influence 20 or less) It never grows again. Reward: %s.\\n"
              "Subdue every rival family to unlock the route's final Unity focus." % (en, SUBDUE[k][2])),
        icon="GFX_decision_generic_break_treaty")
    C.d(cat_fam, "deal_%s" % k, "%s와 거래" % ko, "Deal with the %s" % en, bonus[k] + [FAMV(k, 10), LAW(-5)], cost=25, once=False,
        days_re_enable=120, desc=("%s 패밀리 영향력 +10, 법 -5" % ko, "%s influence +10, law -5" % en), icon="GFX_decision_generic_fundraising",
        visible=RIVAL(k))
    C.d(cat_fam, "crack_%s" % k, "%s 단속" % ko, "Crack Down on the %s" % en,
        [FAMV(k, -15), LAW(5), "add_stability = -0.02",
         "if = { limit = { %s } %s }" % (HAS("witness"), FAMV(k, -10))], cost=50, once=False, days_re_enable=120, visible=RIVAL(k),
        desc=("%s 패밀리 영향력 -15 (반패밀리 수사단 뒤 -25), 법 +5" % ko, "%s influence -15 (-25 after the Anti-Family Bureau), law +5" % en),
        icon="GFX_decision_generic_protection")
C.d(cat_fam, "arbitrate", "패밀리 중재", "Arbitrate Between Families", ["add_stability = 0.05", "add_political_power = 25"], cost=50,
    once=False, days_re_enable=180)
C.d(cat_fam, "hire_soldiers", "패밀리 병사 고용", "Hire Family Soldiers",
    ["add_manpower = 8000", "army_experience = 10", FAMV("gambino", 5)], cost=50, once=False, days_re_enable=180,
    icon="GFX_decision_generic_military")
C.d(cat_fam, "bring_down_don", "대부 체포 작전", "Arrest a Don",
    ["random_list = {", "\t1 = { %s }" % FAMV("bellone", -20), "\t1 = { %s }" % FAMV("gambino", -20), "\t1 = { %s }" % FAMV("saluzzo", -20), "}",
     LAW(15), EV(24)], cost=100, once=False, days_re_enable=365, visible=[HAS("route_law")], available=[AT_LEAST("law", 50)],
    desc=("법 루트. 무작위 패밀리 하나의 대부를 체포한다. 영향력 -20, 법 +15. (법 50 이상)",
          "Law route. Arrest the don of a random family. Influence -20, law +15. (Law 50+)"),
    icon="GFX_decision_generic_protection")
C.d(cat_fam, "family_feast", "패밀리 연회", "Family Banquet", ["add_stability = 0.03", FAMV("bellone", 3), FAMV("gambino", 3), FAMV("saluzzo", 3)],
    cost=25, once=False, days_re_enable=180)
cat_eco = C.category("street", "거리의 경제", "Street Economy", icon="GFX_decision_category_generic_industry",
                     visible=["OR = {", "\t" + HAS("smuggling"), "\t" + HAS("casinos"), "\t" + HAS("rites"), "\t" + HAS("league"),
                              "\thas_idea = TU_SIR_wine_and_olive", "}"])
C.d(cat_eco, "smuggling_tax", "밀수 과세", "Tax the Smugglers", ["add_political_power = 60", FAMV("saluzzo", 5)], cost=0, once=False,
    days_re_enable=120, visible=[HAS("smuggling")])
C.d(cat_eco, "casino_license", "카지노 허가", "Casino Licences", ["add_political_power = 75", LAW(-5)], cost=0, once=False,
    days_re_enable=180, visible=[HAS("casinos")])
C.d(cat_eco, "olive_harvest", "올리브 수확 축제", "Olive Harvest Festival", ["add_stability = 0.03", "add_political_power = 25"], cost=25,
    once=False, days_re_enable=365, visible=["has_idea = TU_SIR_wine_and_olive"])
C.d(cat_eco, "found_league", "남부 연맹 결성", "Found the Southern League", ["create_faction = TU_SIR_league"], cost=50,
    visible=[HAS("league")], available=["is_in_faction = no"])
C.loc("TU_SIR_league", "남부 연맹", "Southern League")
C.d(cat_eco, "invite_league", "연맹 초청", "Invite to the League", ["add_to_faction = FROM"], cost=50, once=False, days_re_enable=90,
    visible=[HAS("league"), "is_faction_leader = yes"],
    target=["NOT = { tag = ROOT }", "is_in_faction = no", "NOT = { has_war_with = ROOT }", "OR = { tag = LAT tag = RIM tag = IBE tag = LEI }"])

# ------------------------------------------------------------------ 패밀리 소요 (사양서 70)
# 스페인 내전 전의 주둔 방식처럼: 굴복하지 않은 경쟁 패밀리가 있는 동안 UNREST_EVERY 달마다 시라쿠사의 한 주에서 소요가 난다.
# '패밀리' 탭에 미션이 뜨고, UNREST_DAYS 일 안에 그 주에 사단을 주둔시키면 진압된다 (이미 주둔해 있으면 바로 진압).
# 주 번호는 생성할 때 history/states 에서 읽는다 (지도를 다시 만들면 이 생성기도 다시 돌린다). 사람이 하는 시라쿠사에만 일어난다.
UNREST_EVERY, UNREST_DAYS, UNREST_DIVS, UNREST_DIVS_BIG = 4, 30, 2, 3
_MOD = Path(__file__).resolve().parents[3] / "terra_universalis"


def sir_states():
    import re as _re
    out = []
    for path in (_MOD / "history" / "states").glob("*.txt"):
        t = path.read_text(encoding="utf-8-sig")
        if _re.search(r"\bowner\s*=\s*SIR\b", t):
            out.append(int(_re.search(r"\bid\s*=\s*(\d+)", t).group(1)))
    return sorted(out)


SIR_STATES = sir_states()
C.history.append("set_variable = { TU_SIR_unrest_timer = 0 }")
C.idea("turf_lost", "패밀리가 장악한 거리", "Streets Held by the Families",
       {"production_speed_buildings_factor": -0.05, "stability_factor": -0.03, "political_power_gain": -0.05},
       "generic_secret_police", ("소요를 진압하지 못했다. 그 거리는 이제 패밀리의 것이다.",
                                 "The unrest was not put down. Those streets now belong to the family."))
_RIVAL_T = "AND = { NOT = { has_country_flag = TU_SIR_route_%(k)s } NOT = { has_country_flag = TU_SIR_absorbed_%(k)s } }"
_NOT_RIVAL_T = "OR = { has_country_flag = TU_SIR_route_%(k)s has_country_flag = TU_SIR_absorbed_%(k)s }"
C.effects.append("""TU_SIR_unrest_tick = {
	if = {
		limit = {
			is_ai = no
			has_country_flag = TU_SIR_families
			NOT = { has_country_flag = TU_SIR_unrest_active }
			OR = {
%s
			}
		}
		add_to_variable = { TU_SIR_unrest_timer = 1 }
		if = {
			limit = { check_variable = { TU_SIR_unrest_timer > %d } }
			set_variable = { TU_SIR_unrest_timer = 0 }
			random_list = {
%s
			}
		}
	}
}""" % ("\n".join("\t\t\t\t" + _RIVAL_T % dict(k=k) for k, _, _ in FAM), UNREST_EVERY - 1,
        "\n".join("""				10 = {
					modifier = { factor = 0 %s }
					modifier = { factor = 2 check_variable = { TU_SIR_%s > 49 } }
					country_event = { id = tu_sir_ev.%d }
				}""" % (_NOT_RIVAL_T % dict(k=k), k, 60 + i) for i, (k, _, _) in enumerate(FAM))))
C.effects.append("""TU_SIR_unrest_pick_state = {
	random_list = {
%s
		1 = { TU_SIR_unrest_clear = yes }
	}
}""" % "\n".join("""		10 = {
			modifier = { factor = 0 NOT = { owns_state = %d } }
			activate_mission = TU_SIR_unrest_%d
		}""" % (x, x) for x in SIR_STATES))
C.effects.append("""TU_SIR_unrest_clear = {
	hidden_effect = {
		clr_country_flag = TU_SIR_unrest_active
		clr_country_flag = TU_SIR_unrest_big
%s
	}
}""" % "\n".join("\t\tclr_country_flag = TU_SIR_unrest_by_%s" % k for k, _, _ in FAM))
C.effects.append("""TU_SIR_unrest_won = {
%s
	army_experience = 10
	add_stability = 0.01
	TU_SIR_unrest_clear = yes
}""" % "\n".join("\tif = { limit = { has_country_flag = TU_SIR_unrest_by_%s } %s }" % (k, FAMV(k, -10)) for k, _, _ in FAM))
C.effects.append("""TU_SIR_unrest_lost = {
%s
	add_stability = -0.03
	add_timed_idea = { idea = TU_SIR_turf_lost days = 120 }
	TU_SIR_unrest_clear = yes
}""" % "\n".join("\tif = { limit = { has_country_flag = TU_SIR_unrest_by_%s } %s }" % (k, FAMV(k, 10)) for k, _, _ in FAM))
for x in SIR_STATES:
    C.d(cat_fam, "unrest_%d" % x, "소요 진압: 주 %d" % x, "Put Down the Unrest: State %d" % x, ["TU_SIR_unrest_won = yes"],
        cost=None, once=False, highlight=[x], icon="GFX_decision_generic_police_action",
        available=["if = {", "\tlimit = { has_country_flag = TU_SIR_unrest_big }",
                   "\tdivisions_in_state = { state = %d size > %d }" % (x, UNREST_DIVS_BIG - 1), "}",
                   "else = {", "\tdivisions_in_state = { state = %d size > %d }" % (x, UNREST_DIVS - 1), "}"],
        mission={"days": UNREST_DAYS, "timeout": ["TU_SIR_unrest_lost = yes"], "good": False},
        desc=("패밀리 조직원들이 이 주의 거리를 막았다. %d일 안에 이 주에 사단 §Y%d§!개 (큰 소요는 §Y%d§!개)를 주둔시키면 진압된다.\\n"
              "진압: 그 패밀리 영향력 -10, 육군 경험치 +10.\\n실패: 그 패밀리 영향력 +10, 안정도 -3%%, 120일 동안 '패밀리가 장악한 거리'."
              % (UNREST_DAYS, UNREST_DIVS, UNREST_DIVS_BIG),
              "Family men have blocked the streets of this state. Station §Y%d§! divisions here (§Y%d§! for major unrest) within %d days.\\n"
              "Success: that family -10 influence, +10 army experience.\\nFailure: that family +10 influence, stability -3%%, "
              "Streets Held by the Families for 120 days." % (UNREST_DIVS, UNREST_DIVS_BIG, UNREST_DAYS)))
for i, (k, ko, en) in enumerate(FAM):
    C.ev(60 + i, ("%s 패밀리의 소요" % ko, "%s Family Unrest" % en),
         ("%s 패밀리의 조직원들이 거리를 막고 관청을 에워쌌다. 그대로 두면 그 거리는 패밀리의 것이 된다.\\n\\n"
          "'패밀리' 디시전 탭에 진압 미션이 생겼다. %d일 안에 그 주에 사단 %d개 (그 패밀리 영향력이 50 이상이면 %d개)를 주둔시켜야 한다. "
          "미션에 마우스를 올리면 지도에서 그 주가 표시된다. 이미 군대가 주둔해 있으면 바로 진압된다."
          % (ko, UNREST_DAYS, UNREST_DIVS, UNREST_DIVS_BIG),
          "Men of the %s family have blocked the streets and surrounded the offices. Left alone, those streets become theirs.\\n\\n"
          "A mission has appeared in the Families tab: station %d divisions (%d if that family's influence is 50 or more) in that state "
          "within %d days. Hover the mission to see the state on the map. Troops already stationed there put it down at once."
          % (en, UNREST_DIVS, UNREST_DIVS_BIG, UNREST_DAYS)),
         [("군을 보낸다.", "Send in the troops.", [], 1)],
         immediate=[FLAG("unrest_active"), FLAG("unrest_by_%s" % k),
                    "if = { limit = { %s } %s }" % (AT_LEAST(k, 50), FLAG("unrest_big")), "TU_SIR_unrest_pick_state = yes"],
         picture="GFX_report_event_generic_riot")

# ------------------------------------------------------------------ 집권 사업: 루트별 디시전 3개 (사양서 69)
cat_route = C.category("agenda", "집권 사업", "Ruling Agenda",
                       ("고른 루트만의 사업이다.", "Projects unique to the chosen route."),
                       "GFX_decision_category_generic_economy", visible=[HAS("route_chosen")])
for name, regs in (("TU_SIR_enforcers", ["infantry"] * 6 + ["artillery_brigade"]),
                   ("TU_SIR_wolf_pack", ["cavalry"] * 4 + ["infantry"] * 2 + ["artillery_brigade"])):
    C.effects.append("""%s_template = {
	if = {
		limit = { NOT = { has_country_flag = %s_template_done } }
		set_country_flag = %s_template_done
		division_template = {
			name = "%s"
			is_locked = no
			priority = 2
			regiments = {
%s
			}
		}
	}
}""" % (name, name, name, name, "\n".join("\t\t\t\t%s = { x = %d y = %d }" % (r, i // 5, i % 5) for i, r in enumerate(regs))))


def SPAWN(tmpl, exp):
    return ["%s_template = yes" % tmpl,
            "capital_scope = { create_unit = { division = \"division_template = \\\"%s\\\" start_experience_factor = %s "
            "start_equipment_factor = 1\" owner = SIR count = 1 } }" % (tmpl, exp)]


# 벨로네: 건설
C.d(cat_route, "bel_contracts", "건설 수주", "Construction Contracts", ["TU_build_infrastructure = yes"], cost=50, once=False,
    days_remove=120, days_re_enable=120, modifier={"production_speed_buildings_factor": 0.15}, visible=[HAS("route_bellone")],
    desc=("인프라 1단계. 120일 동안 건설 속도 +15%.", "One infrastructure level. Construction speed +15% for 120 days."),
    icon="GFX_decision_generic_construction")
C.d(cat_route, "bel_new_city", "신도시 누오바 볼시니", "The New City of Nuova Volsinii", [], cost=100, once=True,
    days_remove=180, modifier={"civilian_factory_use": 2}, visible=[HAS("route_bellone")],
    remove_effect=["capital_scope = { add_extra_state_shared_building_slots = 3 }", "TU_build_civ_factory = yes",
                   "TU_build_civ_factory = yes", "TU_build_civ_factory = yes", "add_stability = 0.05"],
    desc=("180일 동안 민간 공장 2개를 쓴다. 완성되면 민간 공장 3개, 수도 건물 칸 +3, 안정도 +5%.",
          "Uses two civilian factories for 180 days. On completion: three civilian factories, +3 capital building slots, stability +5%."),
    icon="GFX_decision_generic_construction")
C.d(cat_route, "bel_bonds", "벨로네 채권", "Bellone Bonds", ["add_political_power = 100"], cost=0, once=False,
    days_remove=180, days_re_enable=185, modifier={"consumer_goods_factor": 0.03}, visible=[HAS("route_bellone")],
    desc=("정치력 +100. 180일 동안 소비재 +3%.", "Political power +100. Consumer goods +3% for 180 days."),
    icon="GFX_decision_generic_fundraising")
# 감비노: 군사
C.d(cat_route, "gam_enforcers", "행동대 소집", "Muster the Enforcers", SPAWN("TU_SIR_enforcers", "0.5"), cost=50, once=False,
    days_re_enable=240, visible=[HAS("route_gambino")],
    desc=("수도에 정예 행동대 사단 1개 (보병 6 + 포병 1, 장비 100%).", "One elite enforcer division at the capital (6 infantry + 1 artillery, full equipment)."),
    icon="GFX_decision_generic_military")
C.d(cat_route, "gam_protection", "보호비 징수", "Collect Protection Money", ["add_political_power = 80", "add_stability = -0.03"], cost=0,
    once=False, days_re_enable=180, visible=[HAS("route_gambino")], icon="GFX_decision_generic_fundraising",
    desc=("정치력 +80, 안정도 -3%.", "Political power +80, stability -3%."))
C.d(cat_route, "gam_turf", "구역 확장", "Expand the Turf", ["create_wargoal = { type = annex_everything target = FROM }"], cost=100,
    once=True, visible=[HAS("route_gambino"), "has_completed_focus = TU_SIR_gambino_end"],
    target=["is_neighbor_of = ROOT", "NOT = { has_war_with = ROOT }", "NOT = { is_in_faction_with = ROOT }"],
    desc=("이웃 나라에 병합 명분을 만든다. ('감비노의 철권' 뒤)", "Create an annexation war goal on a neighbour. (After Gambino's Iron Fist)"),
    icon="GFX_decision_generic_operation")
# 살루초: 돈
C.history.append("set_variable = { TU_SIR_branches = 0 }")
C.d(cat_route, "sal_branch", "살루초 은행 지점", "Saluzzo Bank Branch",
    ["FROM = { set_country_flag = TU_SIR_saluzzo_branch }", "add_offsite_building = { type = industrial_complex level = 1 }",
     "add_to_variable = { TU_SIR_branches = 1 }"], cost=75, once=True, visible=[HAS("route_saluzzo")],
    available=["check_variable = { TU_SIR_branches < 4 }", "NOT = { has_war_with = FROM }"],
    target=["NOT = { tag = ROOT }", "NOT = { has_country_flag = TU_SIR_saluzzo_branch }",
            "OR = { tag = LAT tag = LEI tag = RIM tag = VIC tag = COL tag = KAZ tag = YAN tag = LGM }"],
    desc=("그 나라에 지점을 연다. 영토 밖 민간 공장 +1. (지점은 4곳까지)", "Open a branch there. One off-map civilian factory. (Up to four branches)"),
    icon="GFX_decision_generic_fundraising")
C.d(cat_route, "sal_reinvest", "카지노 수익 재투자", "Reinvest Casino Profits", ["TU_build_civ_factory = yes"], cost=50, once=False,
    days_re_enable=365, visible=[HAS("route_saluzzo"), HAS("casinos")], icon="GFX_decision_generic_industry",
    desc=("민간 공장 1개. ('카지노 교역' 뒤)", "One civilian factory. (After Casino Trade)"))
C.d(cat_route, "sal_patron", "연구 후원", "Fund Research",
    ["add_tech_bonus = { name = TU_SIR_sal_patron bonus = 1.0 uses = 1 category = industry category = electronics }"], cost=75,
    once=False, days_re_enable=365, visible=[HAS("route_saluzzo")], icon="GFX_decision_generic_research",
    desc=("산업·전자 연구 보너스 100% 1회.", "A 100% research bonus for industry or electronics."))
# 법
C.d(cat_route, "law_trial", "공개 재판", "Public Trial", [LAW(10), "add_stability = 0.02"], cost=40, once=False, days_re_enable=120,
    visible=[HAS("route_law")], icon="GFX_decision_generic_police_action", desc=("법 +10, 안정도 +2%.", "Law +10, stability +2%."))
C.d(cat_route, "law_seize", "패밀리 자산 몰수", "Seize Family Assets",
    ["TU_build_civ_factory = yes", FAMV("bellone", -5), FAMV("gambino", -5), FAMV("saluzzo", -5)], cost=75, once=False,
    days_re_enable=365, visible=[HAS("route_law")], available=[AT_LEAST("law", 60)], icon="GFX_decision_generic_confiscation",
    desc=("민간 공장 1개, 세 패밀리 영향력 -5. (법 60 이상)", "One civilian factory, all three families -5. (Law 60+)"))
C.d(cat_route, "law_officers", "법 집행관 양성", "Train Law Officers", ["add_manpower = 10000", "army_experience = 20", "add_stability = 0.02"],
    cost=50, once=False, days_re_enable=240, visible=[HAS("route_law")], icon="GFX_decision_generic_military",
    desc=("인력 1만, 육군 경험치 20, 안정도 +2%.", "10,000 manpower, 20 army experience, stability +2%."))
# 늑대
C.d(cat_route, "wolf_rite", "사냥의 밤", "Night of the Hunt", ["add_war_support = 0.05", "army_experience = 20"], cost=50,
    once=False, days_re_enable=180, visible=[HAS("route_wolf"), HAS("rites")], icon="GFX_decision_generic_nationalism",
    desc=("전쟁 지지 +5%, 육군 경험치 20. ('늑대의 의례' 뒤)", "War support +5%, 20 army experience. (After Rites of the Wolves)"))
C.d(cat_route, "wolf_pack_call", "늑대 무리 소집", "Call the Pack", SPAWN("TU_SIR_wolf_pack", "0.6"), cost=50, once=False,
    days_re_enable=240, visible=[HAS("route_wolf")], icon="GFX_decision_generic_cavalry",
    desc=("수도에 늑대 무리 사단 1개 (기병 4 + 보병 2 + 포병 1, 장비 100%).",
          "One wolf pack division at the capital (4 cavalry + 2 infantry + 1 artillery, full equipment)."))
C.d(cat_route, "wolf_blessing", "늑대 군주의 가호", "Blessing of the Wolf Lord", [], cost=75, once=False, days_remove=90,
    days_re_enable=275, modifier={"army_attack_factor": 0.10, "army_speed_factor": 0.05}, visible=[HAS("route_wolf")],
    icon="GFX_decision_generic_nationalism", desc=("90일 동안 공격 +10%, 이동 속도 +5%.", "Attack +10% and speed +5% for 90 days."))

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("시라쿠사의 갈림길", "Crossroads of Siracusa"),
     ("시라쿠사의 거리는 조용하다. 조용한 데는 이유가 있다. 패밀리가 보고 있기 때문이다.\\n"
      "누가 이 도시들을 이끌 것인가. 고른 루트의 중점만 트리에 나타나고 지도자가 바로 바뀐다.\\n\\n" + ROUTE_GUIDE,
      "The streets of Siracusa are quiet, because the families are watching.\\n"
      "Now decide who will lead these cities. Only the chosen route appears in the focus tree, and the leader changes at once.\\n\\n"
      + ROUTE_GUIDE_EN),
     [(SHORT[k][0], SHORT[k][1], choose(k, leader, ideo),
       {"bellone": 25, "gambino": 25, "saluzzo": 20, "law": 20, "wolf": 10}[k])
      for k, ko, en, leader, ideo, d in ROUTES])
C.ev(20, ("늑대 군주의 이야기", "Tale of the Wolf Lord"),
     ("노인들은 아직 늑대 군주의 이야기를 한다. 시라쿠사의 모든 늑대를 다스렸던 이. 그가 언젠가 돌아온다고 한다.",
      "Old folk still tell of the Wolf Lord, who ruled all of Siracusa's wolves, and who they say will return one day."),
     [("그 이야기는 진짜다.", "The story is true.", ["add_war_support = 0.02"], 1)])
C.ev(21, ("의례의 밤", "Night of the Rite"),
     ("보름달 아래 늑대의 의례가 열렸다. 수천 명의 늑대가 같은 방향을 바라보았다.",
      "Under the full moon the Wolf Rite was held. Thousands of wolves faced the same direction."),
     [("무리는 하나다.", "The pack is one.", ["add_war_support = 0.03", "add_stability = 0.02"], 1)])
C.ev(22, ("라플란드의 귀환", "Lappland Returns"),
     ("늑대 군주의 흔적을 좇던 라플란드가 돌아왔다. 그녀의 눈에는 옛 군주의 빛이 깃들어 있다.",
      "Lappland, who chased the Wolf Lord's trail, has returned. The old lord's light shines in her eyes."),
     [("무리가 그녀를 따른다.", "The pack follows her.", ["army_experience = 20"], 1)])
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
     [("군주가 돌아온다.", "The Lord returns.", ["add_war_support = 0.05"], 1)])
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
     ("한때 패밀리의 후계자였던 텍사스가 고향에 돌아왔다. 그녀를 알아본 이들이 수군댄다. 그녀는 아무 말 없이 검을 내려놓지 않았다.",
      "Texas, once heir to a family, has come home. Those who recognise her whisper. She says nothing, and does not put down her swords."),
     [("그녀를 맞이한다.", "Welcome her.", ["recruit_character = TU_SIR_texas", "army_experience = 20"], 70),
      ("조용히 지나가게 한다.", "Let her pass quietly.", ["add_stability = 0.03"], 30)],
     trigger=["original_tag = SIR", HAS("route_chosen")], mtth=150)
C.ev(28, ("패밀리의 시라쿠사", "Siracusa of the Family"), ("한 패밀리가 시라쿠사의 꼭대기에 섰다. 다른 패밀리들은 고개를 숙였다.",
                                                      "One family stands at the top of Siracusa. The others bow their heads."),
     [("가족이 먼저다.", "Family comes first.", ["add_political_power = 50"], 1)])
C.ev(29, ("법의 시라쿠사", "Siracusa of Law"), ("시라쿠사 역사상 처음으로 법원이 패밀리보다 강해졌다.",
                                              "For the first time in Siracusa's history, the courts are stronger than the families."),
     [("정의가 섰다.", "Justice stands.", ["add_stability = 0.05"], 1)])
C.ev(30, ("늑대 군주의 귀환", "Return of the Wolf Lord"), ("늑대 군주가 성채에서 내려왔다. 대부도 판사도 무릎을 꿇었다.",
                                                      "The Wolf Lord descended from the citadel. Dons and judges alike knelt."),
     [("늑대의 시대.", "Age of the wolf.", ["add_war_support = 0.05"], 1)])
C.ev(32, ("판사 암살 미수", "Attempt on a Judge"), ("패밀리 사건을 맡은 판사가 습격을 받았지만 살아남았다.", "A judge handling a family case was attacked but survived."),
     [("경호를 강화한다.", "Increase protection.", [LAW(5), "add_political_power = -20"], 60), ("판사를 교체한다.", "Replace the judge.", [LAW(-5)], 40)],
     trigger=["original_tag = SIR", AT_LEAST("law", 40)], mtth=300)
C.ev(33, ("관광객의 물결", "A Wave of Tourists"), ("카지노와 해변을 찾아 외국인들이 몰려왔다.", "Foreigners flock to the casinos and beaches."),
     [("환영한다.", "Welcome them.", ["add_political_power = 50"], 1)],
     trigger=["original_tag = SIR", HAS("casinos")], mtth=300)
C.ev(34, ("달밤의 울음", "Howling at Night"), ("달밤마다 성채 쪽에서 늑대 울음이 들린다는 신고가 늘었다.", "Reports of wolf howls from the citadel on moonlit nights are increasing."),
     [("조사단을 보낸다.", "Send investigators.", ["add_political_power = -15", "add_war_support = 0.02"], 1)],
     trigger=["original_tag = SIR", HAS("rites")], mtth=240)

# ------------------------------------------------------------------ 루트별 이벤트 (사양서 69): 중점이 부른다
ROUTE_EVENTS = [
    # 번호, 부르는 중점, 며칠 뒤, 제목, 본문, 선택지 [(한, 영, 효과)]
    (40, "bellone_company", 5, ("새 도시의 설계도", "Blueprints of a New City"),
     ("벨로네 건설 회사가 새 도시의 설계도를 내놓았다. 패밀리의 손이 닿지 않는 도시를 짓겠다는 꿈이다.",
      "The Bellone Construction Company presents blueprints for a new city: a dream of a city beyond any family's reach."),
     [("빨리 짓는다.", "Build fast.", ["add_political_power = 50", "add_stability = -0.02"]),
      ("튼튼하게 짓는다.", "Build to last.", ["add_stability = 0.03", "add_political_power = -25"])]),
    (41, "bellone_district", 5, ("건설부 장관의 죽음", "Death of the Construction Minister"),
     ("공업 지구 입찰을 앞두고 건설부 장관이 총에 맞았다. 누가 쏘았는지 모두 짐작하지만 아무도 말하지 않는다.",
      "Before the industrial district tender, the construction minister was shot. Everyone can guess who did it; no one says."),
     [("범인을 찾는다.", "Find the killer.", [LAW(5), "add_political_power = -30"]),
      ("조용히 덮는다.", "Bury it quietly.", ["add_political_power = 60", LAW(-5)])]),
    (42, "gambino_soldiers", 5, ("구역 다툼", "Turf Dispute"),
     ("행동대가 늘자 옆 구역과 시비가 붙었다. 거리 하나를 두고 양쪽이 칼을 뽑았다.",
      "As the enforcers grow, a quarrel breaks out with the next turf. Both sides draw blades over a single street."),
     [("힘으로 정리한다.", "Settle it by force.", ["army_experience = 15", "add_stability = -0.02"]),
      ("협상으로 끝낸다.", "Negotiate.", ["add_political_power = 40"])]),
    (43, "gambino_militia", 5, ("행동대장의 야심", "A Captain's Ambition"),
     ("민병대를 맡은 행동대장이 자기 깃발을 걸기 시작했다. 대부의 이름보다 그의 이름이 더 자주 들린다.",
      "The captain in charge of the militia has begun flying his own colours. His name is heard more often than the Don's."),
     [("숙청한다.", "Purge him.", ["add_stability = 0.03", "add_manpower = -3000"]),
      ("자리를 주고 달랜다.", "Give him a seat.", ["add_manpower = 8000", "add_stability = -0.02"])]),
    (44, "saluzzo_bank", 5, ("살루초의 만찬", "The Saluzzo Banquet"),
     ("살루초 대부가 다른 패밀리의 대부들을 만찬에 불렀다. 잔마다 빚 문서가 한 장씩 놓여 있다.",
      "Don Saluzzo invites the other dons to a banquet. Beside every glass lies a note of debt."),
     [("빚을 받아낸다.", "Call in the debts.", ["add_political_power = 80", FAMV("bellone", 5), FAMV("gambino", 5)]),
      ("빚을 탕감해 은혜를 판다.", "Forgive the debts and sell the favour.", [FAMV("bellone", -8), FAMV("gambino", -8)])]),
    (45, "saluzzo_casinos", 5, ("장부의 구멍", "A Hole in the Ledger"),
     ("카지노 장부에서 큰돈이 사라졌다. 회계사는 숫자가 틀렸을 뿐이라고 한다.",
      "A large sum has vanished from the casino ledgers. The accountant says the numbers were merely wrong."),
     [("회계사를 바꾼다.", "Replace the accountant.", ["add_political_power = -30", "add_stability = 0.03"]),
      ("눈감아 준다.", "Look the other way.", ["add_political_power = 50", LAW(-5)])]),
    (46, "law_judges", 5, ("라비니아의 판결", "Lavinia's Verdict"),
     ("패밀리 조직원 열두 명이 한꺼번에 법정에 섰다. 라비니아 판사의 판결을 온 도시가 기다린다.",
      "Twelve family men stand in the dock at once. The whole city waits for Judge Lavinia's verdict."),
     [("법대로 엄벌한다.", "The full weight of the law.", [LAW(5), "add_stability = -0.02"]),
      ("죄를 뉘우친 자는 풀어 준다.", "Mercy for the repentant.", ["add_stability = 0.03"])]),
    (47, "law_bureau", 5, ("증인의 죽음", "Death of a Witness"),
     ("수사단이 지키던 증인이 숙소에서 죽은 채 발견되었다. 문은 안에서 잠겨 있었다.",
      "A witness guarded by the bureau is found dead in the safe house. The door was locked from the inside."),
     [("수사를 넓힌다.", "Widen the investigation.", [LAW(5), "add_political_power = -30"]),
      ("남은 증인을 더 깊이 숨긴다.", "Hide the remaining witnesses deeper.", ["add_stability = 0.02", "add_political_power = -15"])]),
    (48, "wolf_relics", 5, ("늑대의 주인의 속삭임", "Whisper of the Wolf Lord"),
     ("유물을 꺼낸 밤, 라플란드는 짐승의 목소리를 들었다. 힘을 주겠다고, 대신 송곳니가 되라고.",
      "On the night the relics are unearthed, Lappland hears a beast's voice: power, in exchange for becoming its fang."),
     [("힘을 받아들인다.", "Take the power.", ["add_war_support = 0.05", "add_stability = -0.03", "army_experience = 20"]),
      ("늑대는 누구의 송곳니도 아니다.", "A wolf is no one's fang.", ["add_stability = 0.04"])]),
    (49, "wolf_pack", 5, ("무리의 서열", "Order of the Pack"),
     ("늑대 무리 군단이 모이자 누가 앞에 설지를 두고 으르렁거리기 시작했다.",
      "As the pack legion gathers, they begin to snarl over who shall run at the front."),
     [("가장 강한 자가 앞에 선다.", "The strongest leads.", ["army_experience = 30"]),
      ("모두가 함께 달린다.", "All run together.", ["add_manpower = 10000"])]),
]
for n, sid, days, title, desc, opts in ROUTE_EVENTS:
    C.ev(n, title, desc, [(ko, en, eff, 50) for ko, en, eff in opts])
    next(x for x in C.focuses if x["id"] == "TU_SIR_" + sid)["reward"].append(EV(n, days))
# 키아베 일당: 군 사령부가 서면 용문으로 떠났던 세 사람이 돌아온다 (참모 키아베, 장군 아오스타·브로카)
C.ev(50, ("키아베 일당의 귀향", "Chiave's Gang Comes Home"),
     ("용문으로 떠났던 키아베와 아오스타, 브로카가 시라쿠사로 돌아왔다. 군 사령부가 사람을 구한다는 소문을 들었다고 한다.",
      "Chiave, Aosta and Broca, who had left for Lungmen, are back in Siracusa. They heard the army command is hiring."),
     [("세 사람을 받아들인다.", "Take all three.",
       ["recruit_character = TU_SIR_chiave", "recruit_character = TU_SIR_aosta", "recruit_character = TU_SIR_broca"], 80),
      ("돌려보낸다.", "Send them away.", ["add_political_power = 30"], 20)])
next(x for x in C.focuses if x["id"] == "TU_SIR_army_command")["reward"].append(EV(50, 10))

# ------------------------------------------------------------------ 이스터에그: 엄지 패밀리와 발렌치나 (사양서 32)
# 세 패밀리 루트의 마지막 앞 중점(재건의 시라쿠사 / 감비노 군단 / 금고의 열쇠) 10일 뒤 -> 처음 듣는 패밀리 -> 7일 뒤 엄지
C.ev(35, ("처음 듣는 패밀리", "An Unknown Family"),
     ("통합 협상장 명부에 낯선 이름이 하나 끼어 있다.\\n\\n\"이 패밀리는 뭐지? 엄...뭐..? 처음들어보는군..\"",
      "A strange name has slipped onto the roster at the unification talks.\\n\\n\"What family is this? Thu...what..? Never heard of them..\""),
     [("좀 더 알아봐라.", "Look into it.", [EV(36, 7)], 1)])
C.ev(36, ("엄지", "The Thumb"),
     ("조사 보고서가 올라왔다. 규율이 엄격하고, 명령에 절대 복종하며, 탄환 하나 허투루 쓰지 않는다고.\\n\\n\"엄지..? 괜찮은 패밀리 같아보이는군\"",
      "The report is in: strict discipline, absolute obedience, not a single bullet wasted.\\n\\n\"The Thumb..? Looks like a decent family\""),
     [("패밀리로 받아들인다", "Welcome them as a family", [FLAG("thumb_accepted"), EV(37, 3)], 50),
      ("다른 패밀리를 알아본다", "Look for another family", [], 50)])
C.ev(37, ("발렌치나", "Valencina"),
     ("엄지에서 보낸 지휘관이 회의실 문을 걷어차고 들어왔다. 그녀는 아무에게도 고개를 숙이지 않았다.\\n\\n\"지긋지긋해, 너도 패밀리도, 모두 다!!!\"",
      "The commander sent by the Thumb kicks the meeting-room door open. She bows to no one.\\n\\n\"I'm sick of it. You, the family, all of it!!!\""),
     [("...잘 부탁한다, 발렌치나.", "...Welcome aboard, Valencina.", ["recruit_character = TU_SIR_valencina", "army_experience = 25"], 1)],
     picture="GFX_report_event_generic_battle")
for sid in ("bellone_rebuild", "gambino_legion", "saluzzo_keys"):
    next(x for x in C.focuses if x["id"] == "TU_SIR_" + sid)["reward"].append(EV(35, 10))

if __name__ == "__main__":
    C.write()
