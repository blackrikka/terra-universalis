#!/usr/bin/env python3
"""시라쿠사(SIR) 중점·디시전·이벤트 (사양서 17, 다시 설계: 사양서 63).

구조 (중점 약 80개)
  뿌리 '늑대의 땅' -> 이벤트 tu_sir_ev.1 '시라쿠사의 갈림길'에서 정치 루트 다섯 중 하나를 고른다.
    벨로네(건설·산업, 지도자 벨로네) / 감비노(군사, 감비노 대부) / 살루초(돈·외교, 살루초 대부) /
    법(안정·연구, 페넌스) / 늑대(공격·정복, 라플란드 더 데카덴차)
    고르면 지도자가 바로 바뀌고 그 루트 갈래(9개)만 보인다 (allow_branch = TU_SIR_route_<key>). 다섯 갈래는 같은 자리에 겹친다
    (tools/focusgen/block_layout.py). 결말 중점에서 국호가 바뀐다 (tools/chargen/data.py 의 hooks).
  공통 갈래: 산업(14), 군사(13), 외교(5). 모든 효과는 중점에 직접 적혀 있다 (이름 테마 자동 보상 없음).
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
            "add_ideas = TU_SIR_%s_start" % key, "mark_focus_tree_layout_dirty = yes"]


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
R("bellone", "bellone_head", "벨로네의 시대", "The Bellone Era", ["root"], ["add_political_power = 75", FAMV("bellone", 10)], cost=5,
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

# ---- 감비노: 군사·동원
R("gambino", "gambino_head", "감비노의 시대", "The Gambino Era", ["root"], ["add_manpower = 10000", FAMV("gambino", 10)], cost=5,
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

# ---- 살루초: 돈·외교
R("saluzzo", "saluzzo_head", "살루초의 시대", "The Saluzzo Era", ["root"], ["add_political_power = 100", FAMV("saluzzo", 10)], cost=5,
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
C.d(cat_eco, "wolf_rite", "늑대의 의례 거행", "Hold the Wolf Rite", ["add_war_support = 0.05", "army_experience = 15"], cost=50,
    once=False, days_re_enable=240, visible=[HAS("rites")])
C.d(cat_eco, "olive_harvest", "올리브 수확 축제", "Olive Harvest Festival", ["add_stability = 0.03", "add_political_power = 25"], cost=25,
    once=False, days_re_enable=365, visible=["has_idea = TU_SIR_wine_and_olive"])
C.d(cat_eco, "found_league", "남부 연맹 결성", "Found the Southern League", ["create_faction = TU_SIR_league"], cost=50,
    visible=[HAS("league")], available=["is_in_faction = no"])
C.loc("TU_SIR_league", "남부 연맹", "Southern League")
C.d(cat_eco, "invite_league", "연맹 초청", "Invite to the League", ["add_to_faction = FROM"], cost=50, once=False, days_re_enable=90,
    visible=[HAS("league"), "is_faction_leader = yes"],
    target=["NOT = { tag = ROOT }", "is_in_faction = no", "NOT = { has_war_with = ROOT }", "OR = { tag = LAT tag = RIM tag = IBE tag = LEI }"])

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
     ("한때 패밀리의 후계자였던 텍사스가 고향을 찾았다. 그녀를 알아본 이들이 수군댄다.",
      "Texas, once heir to a family, has returned home. Those who recognise her whisper."),
     [("조용히 지나가게 한다.", "Let her pass quietly.", ["add_stability = 0.02"], 50),
      ("패밀리들이 그녀를 원한다.", "The families want her.", [FAMV("saluzzo", 5), "add_political_power = 25"], 50)],
     trigger=["original_tag = SIR", "has_completed_focus = TU_SIR_root"], mtth=400)
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
