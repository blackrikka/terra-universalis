#!/usr/bin/env python3
"""염국 쉐이 내전: 형제 집권 갈래 늘리기 (사양서 36).

사용법 (python -I):
    python -I tools/focusgen/yan_sui_rulers.py
    python -I tools/focusgen/merge_focus.py --tag YAN

형제 12명의 "<형제> 집권" 중점 아래 갈래를 6단으로 만든다.
    집권 → A1 → A2 (기존 두 중점: 이름은 그대로, 보상·설명을 형제에 맞게 바꾼다)
         → B → C1 / C2 (둘 중 하나, 상호 배타) → F (치세 강화: 치세 국민정신을 강화판 _2 로 바꾼다)
만드는 파일
    tools/focusgen/yan/p1s_sui_rulers.txt              새 중점 48개 (B, C1, C2, F)
    tools/focusgen/yan/p1_politics.txt                 기존 A1·A2 의 completion_reward 를 바꾼다
    common/ideas/tu_yan_sui_ruler_ideas.txt            강화판 치세 국민정신 12개
    localisation/{korean,english}/tu_yan_sui_rulers_l_*.yml   새 중점·국민정신 이름과 설명
    localisation/{korean,english}/tu_yan_sui_l_*.yml   기존 A1·A2 의 설명(비어 있던 것)과 이름 한 개(지에 항구 → 나루터)
다시 돌려도 결과가 같다.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MOD = REPO / "terra_universalis"
PART = HERE / "yan" / "p1s_sui_rulers.txt"
P1 = HERE / "yan" / "p1_politics.txt"
IDEAS = MOD / "common" / "ideas" / "tu_yan_sui_ruler_ideas.txt"
OLD_LOC = {"korean": MOD / "localisation" / "korean" / "tu_yan_sui_l_korean.yml",
           "english": MOD / "localisation" / "english" / "tu_yan_sui_l_english.yml"}
P = "TU_YAN_p1_"


def TB(name, cats, bonus=0.75):
    return "add_tech_bonus = { name = %s%s bonus = %s uses = 1 %s }" % (
        P, name, bonus, " ".join("category = %s" % c for c in cats))


def DCR(name, cat="land_doctrine", red=0.5):
    return "add_doctrine_cost_reduction = { name = %s%s cost_reduction = %s uses = 1 category = %s }" % (P, name, red, cat)


PP = "add_political_power = %d".__mod__
ST = "add_stability = %s".__mod__
WS = "add_war_support = %s".__mod__
XP = "army_experience = %d".__mod__
AXP = "air_experience = %d".__mod__
MP = "add_manpower = %d".__mod__
CIV, MIL, INF = "TU_build_civ_factory = yes", "TU_build_mil_factory = yes", "TU_build_infrastructure = yes"
FORT, RAIL = "TU_build_forts_2 = yes", "TU_build_railway = yes"

# 형제: (ko 이름, A1 id, A2 id, A1 (desc ko, en, 보상), A2 (...), [B, C1, C2, F], 강화 국민정신 (그림, {modifier}))
# B/C1/C2/F: (sid, ko, en, desc ko, desc en, icon, [보상])
BROTHERS = {
    "chongyue": ("총웨", "chongyue_way", "chongyue_duty",
        ("총웨가 무인의 도를 다시 세운다. 병사들은 싸우는 법보다 지키는 법을 먼저 배운다.",
         "Chongyue restores the way of the warrior. Soldiers learn to protect before they learn to fight.",
         [DCR("chongyue_way", red=0.4), XP(25)]),
        ("맏형은 떠난 동생들의 몫까지 짊어진다.", "The eldest carries the burden of the siblings who left.",
         [ST(0.05), WS(0.03)]),
        [("chongyue_halls", "무도관", "The Martial Halls", "성마다 무도관을 열어 젊은이들에게 창과 주먹을 가르친다.",
          "Open martial halls in every city to teach the young the spear and the fist.", "GFX_goal_generic_army_doctrines",
          [XP(30), MP(10000)]),
         ("chongyue_spear", "지키는 창", "The Guarding Spear", "창은 형제의 땅을 지키는 데만 쓴다.",
          "The spear is raised only to guard the siblings' land.", "GFX_goal_generic_defence",
          [FORT, DCR("chongyue_spear")]),
         ("chongyue_open_hand", "펼친 손바닥", "The Open Palm", "칼을 거두고 손을 내민다. 떠난 형제들도 돌아올 수 있다.",
          "Sheathe the blade and hold out a hand. Even the siblings who left may return.", "GFX_goal_generic_improve_relations",
          [ST(0.05), PP(100)]),
         ("chongyue_reign", "무(武)의 치세", "Reign of Martial Virtue", "총웨의 염국은 무예로 서고 무예로 지킨다.",
          "Chongyue's Yan stands by martial virtue and is guarded by it.", "GFX_goal_generic_special_forces", [])],
        ("generic_army_war_college", {"army_attack_factor": 0.12, "army_org_factor": 0.08, "army_morale_factor": 0.1})),
    "ling": ("링", "ling_poem", "ling_dream",
        ("링이 술잔을 들고 시를 읊으면 백성들이 따라 부른다.", "When Ling raises a cup and recites, the people sing along.",
         [PP(60), ST(0.03)]),
        ("링의 아츠가 꿈과 현실의 경계를 흐린다. 정원에 앉은 이들은 근심을 잊는다.",
         "Ling's Arts blur dream and waking. Those who sit in the garden forget their worries.",
         [ST(0.05), TB("ling_dream", ["tu_originium_tech"])]),
        [("ling_tavern", "천하의 주막", "Taverns of All Under Heaven", "곳곳의 주막이 소식과 민심이 모이는 곳이 된다.",
          "The taverns everywhere become places where news and public feeling gather.", "GFX_goal_generic_propaganda",
          [PP(80), WS(0.03)]),
         ("ling_wanderer", "떠도는 시인", "The Wandering Poet", "링이 직접 길을 떠나 마을마다 민심을 살핀다.",
          "Ling takes to the road and listens to every village.", "GFX_goal_generic_neutrality_focus", [ST(0.06), PP(40)]),
         ("ling_dream_army", "꿈속의 군세", "An Army in the Dream", "꿈의 정원에서 깨어난 이들이 링을 위해 싸우겠다고 나선다.",
          "Those who woke from the garden of dreams volunteer to fight for Ling.", "GFX_goal_generic_allies_build_infantry",
          [MP(20000), WS(0.04)]),
         ("ling_reign", "취선(醉仙)의 치세", "Reign of the Drunken Immortal", "술과 시와 꿈. 링의 염국은 느긋하지만 흔들리지 않는다.",
          "Wine, verse and dreams. Ling's Yan is unhurried but unshaken.", "GFX_goal_generic_national_unity", [])],
        ("generic_political_support", {"political_power_gain": 0.25, "stability_factor": 0.1, "war_support_factor": 0.05})),
    "wang": ("왕", "wang_stars", "wang_far",
        ("왕이 별을 읽어 때를 가늠한다.", "Wang reads the stars to judge the time.", [TB("wang_stars", ["electronics"]), PP(30)]),
        ("열 수 앞을 내다보는 형제는 서두르지 않는다.", "A sibling who sees ten moves ahead is never in a hurry.", [PP(50), XP(15)]),
        [("wang_board", "천하라는 바둑판", "The Board of All Under Heaven", "왕에게 천하는 한 판의 바둑이다.",
          "To Wang, all under heaven is a single game of go.", "GFX_goal_generic_intelligence_exchange",
          [TB("wang_board", ["industry", "construction_tech"])]),
         ("wang_academy", "관측소와 학당", "Observatories and Academies", "별을 보는 관측소 옆에 학당을 세운다.",
          "Build academies beside the observatories that watch the stars.", "GFX_goal_generic_scientific_exchange",
          [TB("wang_academy", ["tu_originium_tech", "electronics"])]),
         ("wang_records", "전장의 기보", "Records of the Battlefield", "지난 싸움을 바둑 기보처럼 한 수씩 되짚는다.",
          "Replay past battles move by move, like the record of a go game.", "GFX_goal_generic_army_doctrines",
          [DCR("wang_records"), XP(25)]),
         ("wang_reign", "국수(國手)의 치세", "Reign of the Grandmaster", "왕의 염국은 언제나 상대보다 한 수 앞에 있다.",
          "Wang's Yan is always one move ahead of its opponent.", "GFX_goal_generic_radar", [])],
        ("generic_research_bonus", {"research_speed_factor": 0.1, "planning_speed": 0.2, "max_planning": 0.05})),
    "dusk": ("더스크", "dusk_painting", "dusk_canvas",
        ("더스크의 그림 속에는 또 하나의 산하가 있다.", "Within Dusk's paintings lies another world of mountains and rivers.",
         [WS(0.03), PP(40)]),
        ("그림 속의 것들이 화폭 밖으로 걸어 나온다.", "The things in the paintings walk out of the canvas.", [MP(10000), ST(0.03)]),
        [("dusk_studio", "화방 선전국", "The Studio of Propaganda", "그림 한 장이 백 마디 말보다 멀리 간다.",
          "A single painting travels further than a hundred speeches.", "GFX_goal_generic_propaganda", [PP(60), WS(0.04)]),
         ("dusk_soldiers", "화중(畵中) 병사", "Painted Soldiers", "붓으로 그린 병사들이 전열에 선다.",
          "Soldiers drawn with the brush take their place in the line.", "GFX_goal_generic_allies_build_infantry",
          [MP(20000), XP(20)]),
         ("dusk_retreat", "그림 속 은거", "Retreat into the Painting", "싸움에 지친 이들이 그림 속 마을에서 쉬어 간다.",
          "Those weary of war rest for a while in a village inside the painting.", "GFX_goal_generic_neutrality_focus",
          [ST(0.08)]),
         ("dusk_reign", "화폭의 치세", "Reign of the Canvas", "더스크의 염국은 한 폭의 그림처럼 고요하고 단단하다.",
          "Dusk's Yan is as still and as solid as a painted scroll.", "GFX_goal_generic_national_unity", [])],
        ("generic_morale_bonus", {"research_speed_factor": 0.05, "stability_factor": 0.1, "army_defence_factor": 0.1,
                                  "war_support_factor": 0.05})),
    "shu": ("슈", "shu_fields", "shu_harvest",
        ("슈가 지나간 들판에는 곡식이 넘친다.", "Grain overflows in every field Shu has passed.", None),
        ("백성이 배불리 먹는 해에는 반란도 없다.", "In a year when the people eat their fill, there is no rebellion.",
         [ST(0.04), MP(10000)]),
        [("shu_canals", "관개 수로", "Irrigation Canals", "마른 땅까지 물길을 낸다.", "Dig channels out to the dry land.",
          "GFX_goal_generic_construct_infrastructure", [INF, ST(0.03)]),
         ("shu_farmer_soldiers", "둔전병", "Farmer-Soldiers", "평소에는 밭을 갈고 싸울 때는 창을 든다.",
          "They till the fields in peace and take up spears in war.", "GFX_goal_generic_allies_build_infantry", [MP(25000)]),
         ("shu_granaries", "곡창 비축", "Granary Reserves", "남는 곡식을 곡창에 쌓아 흉년을 대비한다.",
          "Store surplus grain in granaries against lean years.", "GFX_goal_generic_consumer_goods", [CIV, PP(50)]),
         ("shu_reign", "풍요의 치세", "Reign of Plenty", "슈의 염국에서는 굶는 이가 없다.",
          "No one goes hungry in Shu's Yan.", "GFX_goal_generic_national_unity", [])],
        ("generic_agrarian_society", {"monthly_population": 0.3, "stability_factor": 0.1, "consumer_goods_factor": -0.03})),
    "nian": ("니엔", "nian_forge", "nian_craft",
        ("니엔의 대장간은 밤에도 불이 꺼지지 않는다.", "Nian's forge burns through the night.", None),
        ("명장의 망치 아래에서 쇠가 무기가 된다.", "Under the master smith's hammer, iron becomes arms.", [MIL]),
        [("nian_alloys", "새 합금", "New Alloys", "니엔이 오리지늄을 섞은 새 합금을 두드려 낸다.",
          "Nian hammers out new alloys laced with originium.", "GFX_goal_generic_secret_weapon",
          [TB("nian_alloys", ["industry", "tu_originium_tech"])]),
         ("nian_arsenal", "무기 공방", "The Arsenal Workshops", "대장간을 무기 공방으로 넓힌다.",
          "Expand the forges into arsenal workshops.", "GFX_goal_generic_construct_mil_factory",
          [MIL, TB("nian_arsenal", ["artillery"])]),
         ("nian_modern", "근대 공장", "Modern Factories", "니엔은 낡은 것도 새것도 가리지 않는다. 공장을 세운다.",
          "Nian has no prejudice between old and new. Build factories.", "GFX_goal_generic_construct_civ_factory",
          [CIV, TB("nian_modern", ["construction_tech"])]),
         ("nian_reign", "불꽃의 치세", "Reign of the Forge Flame", "니엔의 염국은 망치 소리로 하루를 연다.",
          "Nian's Yan begins every day with the sound of hammers.", "GFX_goal_generic_production2", [])],
        ("generic_production_bonus", {"production_factory_max_efficiency_factor": 0.15, "industrial_capacity_factory": 0.1,
                                      "production_speed_arms_factory_factor": 0.1})),
    "jun": ("쥔", "jun_coin", "jun_merchant",
        ("쥔의 손을 거치면 돈이 돌기 시작한다.", "Money starts to move once it passes through Jun's hands.", None),
        ("상인들이 다닐 길을 열고 통행세를 낮춘다.", "Open roads for the merchants and lower the tolls.", None),
        [("jun_works", "공공 공사", "Public Works", "남는 돈으로 길과 공장을 짓는다.",
          "Spend the surplus on roads and factories.", "GFX_goal_generic_construction", [INF, CIV]),
         ("jun_canal", "대운하 보수", "Repair the Grand Canal", "남북을 잇는 대운하를 고치고 철도를 놓는다.",
          "Repair the Grand Canal between north and south and lay rail beside it.", "GFX_goal_generic_construct_infrastructure",
          [RAIL, PP(40)]),
         ("jun_tax", "세제 개혁", "Tax Reform", "복잡한 세금을 하나로 묶는다.", "Fold the tangle of taxes into one.",
          "GFX_goal_generic_trade", [PP(100)]),
         ("jun_reign", "번영의 치세", "Reign of Prosperity", "쥔의 염국은 시장의 소리로 가득하다.",
          "Jun's Yan is full of the noise of markets.", "GFX_goal_generic_positive_trade_relations", [])],
        ("generic_economic_increase", {"production_speed_buildings_factor": 0.2, "consumer_goods_factor": -0.06})),
    "jie": ("지에", "jie_tide", "jie_harbor",
        ("강물의 흐름을 읽듯 전장의 흐름을 읽는다.", "Read the flow of battle as one reads the flow of a river.", None),
        ("강을 건너는 나루터를 지켜 군대의 길을 연다.", "Guard the river ferries to keep the army's roads open.", None),
        [("jie_march", "질풍 행군", "Gale Marches", "지에의 군대는 하루에 남의 이틀 길을 간다.",
          "Jie's army covers two days' march in one.", "GFX_goal_generic_army_motorized", [XP(20), INF]),
         ("jie_mobile", "기동 사단", "Mobile Divisions", "빠른 부대를 모아 한 주먹으로 만든다.",
          "Gather the fast units into a single fist.", "GFX_goal_generic_army_motorized",
          [TB("jie_mobile", ["motorized_equipment"]), DCR("jie_mobile")]),
         ("jie_cities", "이동 도시 호위", "Escort the Mobile Cities", "움직이는 도시를 지키는 기갑 호위대를 만든다.",
          "Form armoured escorts for the moving cities.", "GFX_goal_generic_army_tanks",
          [TB("jie_cities", ["motorized_equipment", "armor"])]),
         ("jie_reign", "질풍의 치세", "Reign of the Gale", "지에의 염국은 멈추지 않는다.",
          "Jie's Yan never stands still.", "GFX_goal_generic_army_motorized", [])],
        ("generic_economic_increase", {"army_org_factor": 0.08, "army_speed_factor": 0.1, "breakthrough_factor": 0.08})),
    "ji": ("지", "ji_wind", "ji_cloud",
        ("바람을 타는 형제는 하늘을 두려워하지 않는다.", "A sibling who rides the wind does not fear the sky.",
         [TB("ji_wind", ["light_fighter"]), AXP(20)]),
        ("구름 위에서 보면 땅의 싸움이 한눈에 보인다.", "From above the clouds, the war on the ground is seen at a glance.",
         [AXP(25), PP(30)]),
        [("ji_airfields", "용의 비행장", "Dragon Airfields", "산마다 비행장을 닦는다.", "Level airfields on every mountain.",
          "GFX_goal_generic_build_airforce", [DCR("ji_airfields", "air_doctrine"), AXP(20)]),
         ("ji_fighters", "전투기 대대", "Fighter Wings", "하늘을 지키는 전투기를 늘린다.", "Expand the fighters that guard the sky.",
          "GFX_goal_generic_air_fighter", [TB("ji_fighters", ["light_fighter"], 1.0)]),
         ("ji_bombers", "폭격 대대", "Bomber Wings", "적의 진지를 위에서 부순다.", "Break enemy positions from above.",
          "GFX_goal_generic_build_airforce", [TB("ji_bombers", ["tactical_bomber"], 1.0)]),
         ("ji_reign", "창공의 치세", "Reign of the Open Sky", "지의 염국의 하늘에는 용의 날개만 난다.",
          "Only dragon wings fly in the sky over Ji's Yan.", "GFX_goal_generic_air_fighter", [])],
        ("generic_air_bonus", {"air_attack_factor": 0.12, "air_defence_factor": 0.1, "air_ace_generation_chance_factor": 0.25})),
    "yi": ("이", "yi_envoy", "yi_guests",
        ("이의 사신은 칼 대신 말을 들고 간다.", "Yi's envoys carry words instead of swords.", None),
        ("천하의 손님을 맞아 염국의 이름을 알린다.", "Welcome guests from all under heaven and spread Yan's name.", None),
        [("yi_talks", "형제 회담", "The Sibling Talks", "갈라선 형제들에게도 사신을 보낸다.",
          "Send envoys even to the siblings who broke away.", "GFX_goal_generic_improve_relations", [PP(75), ST(0.03)]),
         ("yi_horizontal", "연횡책", "The Horizontal Alliance", "강한 쪽과 손잡고 나머지를 하나씩 상대한다.",
          "Ally with the strong and deal with the rest one by one.", "GFX_goal_generic_military_deal", [WS(0.05), PP(40)]),
         ("yi_vertical", "합종책", "The Vertical Alliance", "약한 이들을 모아 강한 쪽에 맞선다.",
          "Gather the weak to stand against the strong.", "GFX_goal_generic_alliance", [ST(0.05), PP(40)]),
         ("yi_reign", "화친의 치세", "Reign of Concord", "이의 염국은 말로 이기고 말로 지킨다.",
          "Yi's Yan wins with words and holds with words.", "GFX_goal_generic_positive_trade_relations", [])],
        ("generic_flexible_foreign_policy", {"opinion_gain_monthly_factor": 0.5, "justify_war_goal_time": -0.2,
                                             "political_power_gain": 0.1})),
    "fang": ("팡", "fang_walls", "fang_stand",
        ("팡은 성벽을 쌓는 일을 누구에게도 맡기지 않는다.", "Fang trusts no one else to raise the walls.", None),
        ("한 발짝도 물러서지 않는다. 그것이 팡의 싸움이다.", "Not one step back. That is how Fang fights.",
         [DCR("fang_stand", red=0.4), WS(0.03)]),
        [("fang_passes", "철벽 관문", "Iron Gate Passes", "관문마다 성채를 다시 쌓는다.", "Rebuild the fortresses at every pass.",
          "GFX_goal_generic_fortify_city", [FORT, ST(0.03)]),
         ("fang_engineers", "참호 공병", "Trench Engineers", "공병이 참호와 진지를 판다.", "Engineers dig trenches and positions.",
          "GFX_goal_generic_defence", [TB("fang_engineers", ["construction_tech"]), XP(15)]),
         ("fang_militia", "수성 민병", "Militia of the Walls", "성 안의 백성이 모두 병사가 된다.",
          "Everyone within the walls becomes a soldier.", "GFX_goal_generic_allies_build_infantry", [MP(20000)]),
         ("fang_reign", "철옹성의 치세", "Reign of the Iron Fortress", "팡의 염국은 아무도 넘지 못한다.",
          "No one breaches Fang's Yan.", "GFX_goal_generic_fortify_city", [])],
        ("generic_fortify_the_borders", {"army_defence_factor": 0.18, "max_dig_in": 4})),
    "yu": ("위", "yu_kitchen", "yu_table",
        ("위의 주방은 전쟁 중에도 불이 꺼지지 않는다.", "Yu's kitchen fire does not go out even in war.", [INF, ST(0.03)]),
        ("위가 차린 식탁에는 누구나 앉을 수 있다.", "Anyone may sit at the table Yu has laid.", [ST(0.05), PP(40)]),
        [("yu_field_kitchens", "야전 주방", "Field Kitchens", "전선까지 따뜻한 밥을 나른다.", "Carry hot meals all the way to the front.",
          "GFX_goal_generic_consumer_goods", [XP(15), WS(0.03)]),
         ("yu_supply", "보급 대열", "Supply Columns", "수레와 트럭으로 끊기지 않는 보급선을 만든다.",
          "Build unbroken supply lines of carts and trucks.", "GFX_goal_generic_army_motorized",
          [TB("yu_supply", ["motorized_equipment"]), INF]),
         ("yu_feast", "백성의 잔칫상", "A Feast for the People", "온 나라에 잔칫상을 차린다.", "Lay out a feast across the whole land.",
          "GFX_goal_generic_national_unity", [ST(0.06), PP(50)]),
         ("yu_reign", "만찬의 치세", "Reign of the Banquet", "위의 염국에서는 병사도 백성도 배곯지 않는다.",
          "In Yu's Yan, neither soldier nor citizen goes hungry.", "GFX_goal_generic_consumer_goods", [])],
        ("generic_logistics", {"supply_consumption_factor": -0.2, "attrition": -0.15, "stability_factor": 0.05})),
}
RENAME = {"jie_harbor": ("나루터의 수호", "Guarding the Ferries")}


def focus(fid, pre, icon, cost, reward, me=None, pre_or=None):
    pre_line = "prerequisite = { %s }" % " ".join("focus = %s" % p for p in (pre_or or [pre]))
    me_line = "\n\t\tmutually_exclusive = { focus = %s }" % me if me else ""
    return ("\n\tfocus = {\n\t\tid = %s\n\t\t%s%s\n\t\ticon = %s\n\t\tx = 0\n\t\ty = 0\n\t\tcost = %d\n\n"
            "\t\tsearch_filters = { FOCUS_FILTER_POLITICAL }\n\n\t\tai_will_do = {\n\t\t\tbase = 1\n\t\t}\n\n"
            "\t\tcompletion_reward = {\n%s\n\t\t}\n\t}\n") % (
        fid, pre_line, me_line, icon, cost, "\n".join("\t\t\t" + r for r in reward))


def set_reward(text, fid, reward):
    m = re.search(r"(\n\t\tid = %s\n.*?\n\t\tcompletion_reward = \{\n)(.*?)(\n\t\t\}\n)" % re.escape(fid), text, re.S)
    assert m, fid
    return text[:m.start(2)] + "\n".join("\t\t\t" + r for r in reward) + text[m.end(2):]


def main():
    part = ["\t#### YAN sui rulers: B / C1|C2 / F under each sibling's rule branch (tools/focusgen/yan_sui_rulers.py, spec 36) ####\n"]
    ideas = ["ideas = {\n\n\tcountry = {\n"]
    loc = {"korean": [], "english": []}
    p1 = P1.read_text(encoding="utf-8")
    desc_fix = {}
    for b, (ko, a1, a2, A1, A2, (B, C1, C2, F), (pic, mods)) in BROTHERS.items():
        for sid, (dko, den, rw) in ((a1, A1), (a2, A2)):
            if rw:
                p1 = set_reward(p1, P + sid, rw)
            desc_fix[P + sid] = (dko, den)
        ids = {k: P + v[0] for k, v in zip("BCDF", (B, C1, C2, F))}
        part.append(focus(ids["B"], P + a2, B[5], 10, B[6]))
        part.append(focus(ids["C"], ids["B"], C1[5], 10, C1[6], me=ids["D"]))
        part.append(focus(ids["D"], ids["B"], C2[5], 10, C2[6], me=ids["C"]))
        idea = "TU_YAN_idea_rule_%s_2" % b
        old = "TU_YAN_idea_rule_%s" % b
        part.append(focus(ids["F"], None, F[5], 15,
                          ["if = { limit = { has_idea = %s } swap_ideas = { remove_idea = %s add_idea = %s } }" % (old, old, idea),
                           "else = { add_ideas = %s }" % idea, PP(50)], pre_or=[ids["C"], ids["D"]]))
        for item in (B, C1, C2, F):
            loc["korean"] += [(P + item[0], item[1]), (P + item[0] + "_desc", item[3])]
            loc["english"] += [(P + item[0], item[2]), (P + item[0] + "_desc", item[4])]
        loc["korean"] += [(idea, F[1]), (idea + "_desc", "%s의 치세가 무르익었다. %s" % (ko, F[3]))]
        loc["english"] += [(idea, F[2]), (idea + "_desc", F[4])]
        ideas.append("\n\t\t%s = {\n\t\t\tpicture = %s\n\n\t\t\tallowed = {\n\t\t\t\toriginal_tag = YAN\n\t\t\t}\n\n"
                     "\t\t\tallowed_civil_war = {\n\t\t\t\talways = yes\n\t\t\t}\n\n\t\t\tmodifier = {\n%s\n\t\t\t}\n\t\t}\n"
                     % (idea, pic, "\n".join("\t\t\t\t%s = %s" % kv for kv in mods.items())))
    ideas.append("\t}\n}\n")
    P1.write_text(p1, encoding="utf-8")
    PART.write_text("".join(part), encoding="utf-8")
    IDEAS.write_text("# Generated by tools/focusgen/yan_sui_rulers.py (spec 36)\n" + "".join(ideas), encoding="utf-8")
    for lang, items in loc.items():
        body = "l_%s:\n" % lang + "".join(' %s:0 "%s"\n' % (k, v.replace('"', '\\"')) for k, v in items)
        (MOD / "localisation" / lang / ("tu_yan_sui_rulers_l_%s.yml" % lang)).write_bytes(("\ufeff" + body).encode("utf-8"))
        # 기존 A1·A2 설명 / 이름
        f = OLD_LOC[lang]
        s = f.read_bytes().decode("utf-8-sig")
        li = 0 if lang == "korean" else 1
        for fid, d in desc_fix.items():
            s = re.sub(r'^( %s_desc:\d* ")[^"\n]*(")' % re.escape(fid), lambda m: m.group(1) + d[li] + m.group(2), s, flags=re.M)
        for sid, names in RENAME.items():
            s = re.sub(r'^( %s%s:\d* ")[^"\n]*(")' % (P, re.escape(sid)), lambda m: m.group(1) + names[li] + m.group(2), s, flags=re.M)
        f.write_bytes(("\ufeff" + s).encode("utf-8"))
    print("SUI_RULERS focuses=%d ideas=%d" % (4 * len(BROTHERS), len(BROTHERS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
