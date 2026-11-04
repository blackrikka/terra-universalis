#!/usr/bin/env python3
"""중점 이름(영어)에 맞는 보상 만들기 — 모든 국가 트리가 함께 쓴다 (사양서 16).

theme_of(name_en)          -> 테마 이름 (아래 THEMES 순서대로 처음 맞는 것, 없으면 politics)
reward_lines(theme, fid, cost) -> completion_reward에 넣을 줄 목록 (탭 없음)
idea_modifiers(theme)      -> 갈래 끝 국민정신용 모디파이어 dict

보상 크기는 중점 cost로 정한다: 5 이하 = 작음, 10 = 보통, 15 이상 = 큼.
연구 보너스 이름(name)은 중점 id를 쓴다 (툴팁에 중점 이름이 나온다).
교리는 바닐라 1.19처럼 add_doctrine_cost_reduction, 장비는 add_tech_bonus.
"""

import re

# 군함·조선소·해군기지 중점 (해군 기능을 없앴으므로 트리에서 지운다: content_lib.py, drop_focuses.py).
WARSHIP_RE = (r"^(?!.*airship).*(?:naval|\bnavy|fleet|warship|battleship|cruiser|destroyer|submarine|carrier|torpedo|depth charge|gunboat|"
              r"trireme|galley|dockyard|shipyard|shipbuild|shipwright|marine corps|amphib|landing force|landing corps|"
              r"anti-submarine|merchant marine|ironclad|wolfpack)")
# 지우지 않는 태그 (로도스 아일랜드: 육상함의 도크·수송대)
WARSHIP_KEEP_TAGS = {"RHO"}


def is_warship(name_en, tag=None):
    return tag not in WARSHIP_KEEP_TAGS and re.search(WARSHIP_RE, name_en or "", re.I) is not None


# (테마, 영어 이름 정규식). 위에서부터 처음 맞는 테마를 쓴다.
THEMES = [
    ("mobile_city", r"mobile cit|landship|nomadic|moving cit"),
    ("armor", r"armou?r|tank|panzer|heavy assault"),
    ("coastal_fort", r"coastal fort|coastal defen|harbou?r fort|island fortress|tidal barrier|sea wall|port fort"),
    ("rail", r"^(?!.*(sabotage|guard|battery|fortress)).*(\brail|railway|\bgauge\b|\btracks?\b)"),
    ("mobile", r"mobile|mobility|motori[sz]|mechani[sz]|truck|blitz|cavalry|raid|rapid|express|lightning|manoeuvre|maneuver|pursuit"),
    ("air", r"\bair|airfield|fighter|bomber|\bsky|wing|flight|drone|aviat"),
    ("warship", WARSHIP_RE),
    ("harbour", r"harbou?r|\bports?\b|strait|coast|\bseas?\b|ocean|tide|(?<!rhodes )island|aegir|lighthouse|deep.sea|maritime|shipping|sea lane|anchorage|\bdocks?\b|fishing|black ships"),
    ("artillery", r"artiller|siege|cannon|\bguns?\b|battery|bombard|mortar"),
    ("infantry_weapons", r"\barms\b|rifle|weapon|arsenal|forge|steel|\biron|smith|blade|sword|munition|equipment|firearm|crossbow|bow"),
    ("fort", r"^(?!.*shield wall).*(fortress|\bforts?\b|fortif|\bwalls?\b|bastion|bulwark|stronghold|citadel|bunker|entrench|trench|barrier|rampart|redoubt|defen[cs]e line)"),
    ("doctrine", r"doctrine|tactic|training|drill|academy|staff|command|officer|war college|strateg|general|knight|tournament|duel|martial|elite|veteran"),
    ("defense", r"defen[cs]e|border|garrison|\bline|shield|frontier|watchtower|watchpost|patrol|interceptor|warden|\bgate"),
    ("war", r"sabotage|war plan|\bplans?\b|operation|offensive|campaign|invasion|conquest|occup|\bmarch|assault|\bfront\b|frontline|breakthrough|advance|expedition|sortie|strike|victory|rescue|evacuat|guerr|resistance|total war|war council|\bjump|mobilis|mobiliz|war drum|charge|reclaim"),
    ("medical", r"medic|oripathy|infect|quarantine|suppressant|relief|doctor|hospital|health|refugee|cure|clinic|heal|housing|sanitation|grain|water|dormitor|shelter|citizen|petition|civilian district|welfare|aid to"),
    ("research", r"research|\barts\b|originium|scien|laborator|institute|school|universit|archive|records|engineer|design|babel|prts|rhine|knowledge|librar|scholar|philosoph|music|observator|study|studies|education|teacher|serum|ethics|patent|blueprint|relic|ancient"),
    ("intel", r"intelligen|secret|shadow|\bspy|agent|scout|reconnais|police|security|surveil|informant|cipher|inquisit|sensor|signal|beacon|cells|hideout|cache|smuggl"),
    ("manpower", r"levy|levies|conscri|militia|volunteer|recruit|mobili[sz]ation|draft|regiment|reserve|corps|legion|division|squad|guard|mercenar|warrior|soldier|army|tribe|clan|hunt"),
    ("industry", r"industr|factor|production|works|workshop|mining|\bmine|resource|steam|\brail|road|canal|grid|network|infrastructure|construct|engine|plant|complex|\bhub|route|transit|logistic|supply|depot|survey|build|rebuild|reconstruct|harvest|farm|agricult|\bore\b|quarry|labou?r|foundr|coal|\boil\b|fuel|smelt|furnace|lumber|timber|textile|chemic|refiner|\bfields?\b|reactor|track|gauge|planning|hangar|warehouse|district|full power|anchorage"),
    ("trade", r"trade|market|merchant|\bbank|\btax|treasur|\bfund|loan|debt|tariff|export|econom|monopol|cartel|brokerage|caravan|commerce|guild|money|financ|ledger|quota|consumer|gold|lmd|contract|compan|family|families|currency|bond|vault|budget|hedg|requisition|tribute|import|hire|broker"),
    ("diplomacy", r"envoy|pact|treat|accord|talks|diplomat|allian|allies|summit|embass|relation|guarantee|coalition|union|aggression|contact|exchange|friendship|federation|neutral|independen|reconcil|delegation|liaison|channel|arbitration"),
    ("propaganda", r"propaganda|broadcast|festival|rally|morale|pride|loyal|oath|pledge|unity|unified|people|nation|patriot|faith|church|pilgrim|saint|sankta|holy|prayer|forest|spirit|bloodline|rite|shrine|awaken|chorus|address|voice|speaking|jubilee|banner|standard"),
]
THEMES = [(t, re.compile(p, re.I)) for t, p in THEMES]

FOCUS_ICON = {
    "mobile_city": "GFX_goal_generic_construct_infrastructure",
    "armor": "GFX_goal_generic_army_tanks",
    "mobile": "GFX_goal_generic_army_motorized",
    "air": "GFX_goal_generic_air_doctrine",
    "warship": "GFX_goal_generic_trade",
    "harbour": "GFX_goal_generic_trade",
    "artillery": "GFX_goal_generic_army_artillery",
    "infantry_weapons": "GFX_goal_generic_small_arms",
    "doctrine": "GFX_goal_generic_army_doctrines",
    "fort": "GFX_goal_generic_defence",
    "coastal_fort": "GFX_goal_generic_defence",
    "defense": "GFX_goal_generic_defence",
    "rail": "GFX_goal_generic_construct_infrastructure",
    "medical": "GFX_goal_generic_consumer_goods",
    "research": "GFX_focus_research",
    "intel": "GFX_goal_generic_intelligence_exchange",
    "manpower": "GFX_goal_generic_allies_build_infantry",
    "industry": "GFX_goal_generic_production",
    "trade": "GFX_goal_generic_trade",
    "diplomacy": "GFX_goal_generic_improve_relations",
    "propaganda": "GFX_goal_generic_propaganda",
    "war": "GFX_goal_generic_occupy_start_war",
    "politics": "GFX_goal_generic_political_pressure",
}


def theme_of(name_en):
    for t, rx in THEMES:
        if rx.search(name_en or ""):
            return t
    return "politics"


def _scale(cost):
    if cost <= 5:
        return 0
    if cost >= 15:
        return 2
    return 1


def _tech(fid, cats, s):
    bonus = ("0.5", "0.75", "1.0")[s]
    return "add_tech_bonus = { name = %s bonus = %s uses = 1 %s }" % (
        fid, bonus, " ".join("category = %s" % c for c in cats))


def _doc(fid, cat, s):
    red = ("0.25", "0.4", "0.5")[s]
    return "add_doctrine_cost_reduction = { name = %s cost_reduction = %s uses = 1 category = %s }" % (fid, red, cat)


def reward_lines(theme, fid, cost):
    s = _scale(cost)
    xp = (15, 25, 40)[s]
    pp = (35, 60, 100)[s]
    mp = (5000, 10000, 20000)[s]
    st = ("0.02", "0.03", "0.05")[s]
    if theme == "mobile_city":
        return [_tech(fid, ["construction_tech"], s), _tech(fid, ["motorized_equipment"], s)]
    if theme == "armor":
        return [_tech(fid, ["armor"], s), _doc(fid, "land_doctrine", s)]
    if theme == "mobile":
        return [_tech(fid, ["motorized_equipment"], s), _doc(fid, "land_doctrine", s)]
    if theme == "air":
        return [_tech(fid, ["light_fighter", "tactical_bomber"], s), _doc(fid, "air_doctrine", s),
                "air_experience = %d" % xp]
    if theme in ("harbour", "warship"):
        return ["add_political_power = %d" % pp, _tech(fid, ["industry"], s)]
    if theme == "artillery":
        return [_tech(fid, ["artillery"], s), "army_experience = %d" % xp]
    if theme == "infantry_weapons":
        return [_tech(fid, ["infantry_weapons"], s), "army_experience = %d" % xp]
    if theme == "doctrine":
        return [_doc(fid, "land_doctrine", s), "army_experience = %d" % xp]
    if theme == "rail":
        return ["TU_build_railway = yes"] * (2 if s == 2 else 1)
    if theme == "fort":
        return ["TU_build_forts_%d = yes" % (s + 1)]
    if theme == "coastal_fort":
        return ["TU_build_coastal_forts_%d = yes" % (s + 1)]
    if theme == "defense":
        return [_tech(fid, ["construction_tech"], s), "army_experience = %d" % xp]
    if theme == "war":
        return ["army_experience = %d" % xp, "add_war_support = %s" % st, _doc(fid, "land_doctrine", s)]
    if theme == "medical":
        return ["add_stability = %s" % st, "add_manpower = %d" % mp]
    if theme == "research":
        return [_tech(fid, ["electronics", "industry"], s)]
    if theme == "intel":
        return [_tech(fid, ["radar_tech", "electronics"], s), "add_stability = %s" % st]
    if theme == "manpower":
        return ["add_manpower = %d" % mp, "army_experience = %d" % xp]
    if theme == "industry":
        return [_tech(fid, ["industry", "construction_tech"], s)]
    if theme == "trade":
        return ["add_political_power = %d" % pp, _tech(fid, ["industry"], s)]
    if theme == "diplomacy":
        return ["add_political_power = %d" % pp, "add_stability = %s" % st]
    if theme == "propaganda":
        return ["add_war_support = %s" % st, "add_stability = %s" % st]
    return ["add_political_power = %d" % pp, "add_stability = %s" % st]


IDEA_MODS = {
    "mobile_city": {"production_speed_infrastructure_factor": 0.1, "production_speed_buildings_factor": 0.05},
    "armor": {"army_armor_attack_factor": 0.05, "army_org_factor": 0.03},
    "mobile": {"army_speed_factor": 0.05, "army_org_factor": 0.03},
    "air": {"air_superiority_efficiency": 0.05, "air_attack_factor": 0.05},
    "warship": {"political_power_gain": 0.05, "consumer_goods_factor": -0.02},
    "harbour": {"political_power_gain": 0.05, "consumer_goods_factor": -0.02},
    "artillery": {"army_attack_factor": 0.05},
    "infantry_weapons": {"army_attack_factor": 0.03, "army_defence_factor": 0.03},
    "doctrine": {"experience_gain_army_factor": 0.1, "army_org_factor": 0.03},
    "fort": {"army_defence_factor": 0.05, "max_dig_in": 1},
    "coastal_fort": {"army_defence_factor": 0.05, "coastal_bunker_effectiveness_factor": 0.1},
    "defense": {"army_defence_factor": 0.05, "max_dig_in": 1},
    "rail": {"production_speed_infrastructure_factor": 0.1, "production_speed_rail_way_factor": 0.15},
    "medical": {"stability_factor": 0.05, "monthly_population": 0.1},
    "research": {"research_speed_factor": 0.05},
    "intel": {"stability_factor": 0.05, "political_power_gain": 0.05},
    "manpower": {"conscription_factor": 0.05},
    "industry": {"production_factory_max_efficiency_factor": 0.05, "production_speed_buildings_factor": 0.05},
    "trade": {"political_power_gain": 0.1, "consumer_goods_factor": -0.02},
    "diplomacy": {"political_power_gain": 0.1, "stability_factor": 0.03},
    "propaganda": {"war_support_factor": 0.05, "stability_factor": 0.03},
    "war": {"army_attack_factor": 0.05, "war_support_factor": 0.05},
    "politics": {"political_power_gain": 0.1, "stability_factor": 0.03},
}

IDEA_PICTURE = {
    "mobile_city": "generic_railroads", "armor": "generic_armor", "mobile": "generic_army_europe_1",
    "air": "generic_air_bonus", "warship": "generic_economic_increase", "harbour": "generic_economic_increase", "artillery": "generic_artillery_regiments",
    "infantry_weapons": "generic_infantry_bonus", "doctrine": "generic_army_war_college",
    "fort": "generic_fortify_the_borders", "coastal_fort": "generic_fortify_the_borders",
    "defense": "generic_fortify_the_borders", "rail": "generic_railroads", "medical": "generic_morale_bonus", "research": "generic_research_bonus",
    "intel": "generic_intel_bonus", "manpower": "generic_manpower_bonus", "industry": "generic_production_bonus",
    "trade": "generic_economic_increase", "diplomacy": "generic_flexible_foreign_policy",
    "propaganda": "generic_morale_bonus", "war": "generic_war_preparation", "politics": "generic_central_management",
}


def idea_modifiers(theme):
    return IDEA_MODS.get(theme, IDEA_MODS["politics"])
