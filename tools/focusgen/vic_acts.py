#!/usr/bin/env python3
"""빅토리아 1막 · 2막 (사양서 80). 한 번 돌리면 조각 파일을 쓰고 기존 조각을 고친다 (이미 돌렸으면 새 조각만 다시 쓴다).

1막 '공석인 옥좌와 붉은 안개' (약 1년~1년 반): 의회의 긴급 소집 -> (공작군 동원령 | 자구군 비밀 접촉 | 웰링턴 회유 : 택일) -> 후속 3개씩
   -> 론디니움 포위망 -> 파편 저지 작전 -> 사변의 종결. 종결 이벤트 tu_vic_ev.41 이 세력 영향력과 결과로 2막 루트를 정한다.
2막 5루트: 대공 의회(캐스터) / 아슬란 복위(모범군) / 더블린·타라(드라코) / 비나·자구군(개혁) / 카즈델 강탈(파편이 발동했을 때).
   앞의 넷은 기존 노선 중점 (사양서 79), 카즈델 강탈은 새로 만든다 (TU_VIC_kz_*). 모든 루트 중점은 allow_branch = TU_VIC_route_<duk|asl|drc|par|kzd>.

만드는 것: tools/focusgen/vic/p0_act1.txt, p4_extra.txt (중점), common/ideas/tu_vic_act_ideas.txt, scripted_effects, events 41,
          localisation/*/tu_vic_act_l_*.yml. 고치는 것: p0_existing 의 대공 회의 소집·루트 머리의 선행 중점, 이름 문구.
사용법 (python -I):  python -I tools/focusgen/vic_acts.py   그다음  python -I tools/focusgen/merge_focus.py --tag VIC
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MOD = REPO / "terra_universalis"
P = "TU_VIC_"
ROUTE_KO = {"TU_VIC_duk_route": "철혈의 대공 의회", "TU_VIC_asl_route": "아슬란의 새벽", "TU_VIC_drc_route": "자줏빛 불꽃", "TU_VIC_par_route": "자구군 혁명",
            "TU_VIC_siege_leader": "비나 빅토리아 (시즈)", "TU_VIC_dukes_council": "캐스터 공작", "TU_VIC_draco_leader": "에블라나",
            "TU_VIC_dublinn_leader": "웰링턴", "TU_VIC_parliament_leader": "클로비시아"}
ROUTE_EN = {"TU_VIC_duk_route": "The Iron-Blood Ducal Council", "TU_VIC_asl_route": "The Dawn of Aslan", "TU_VIC_drc_route": "The Purple Flame",
            "TU_VIC_par_route": "Revolution of the Self-Salvation Corps", "TU_VIC_siege_leader": "Vina Victoria (Siege)", "TU_VIC_dukes_council": "Duke Caster",
            "TU_VIC_draco_leader": "Eblana", "TU_VIC_dublinn_leader": "Wellington", "TU_VIC_parliament_leader": "Clovisia"}


def INF(d, n):
    return "add_to_variable = { TU_VIC_influence_%s = %d }" % (d, n)


def LOY(d, n):
    return "add_to_variable = { TU_VIC_loyalty_%s = %d }" % (d, n)


SLOW = "TU_VIC_shard_slow = yes"
# id, 한국어, 영어, 설명 ko, en, 비용, 선행(목록 또는 [[OR 묶음]]), 택일, 효과, 아이콘, available
ACT1 = [
    ("a1_glasgow", "글래스고 거점 확보", "Secure Glasgow", "새 수도 글래스고의 거리와 항만을 단단히 쥔다. 왕당 공작들의 영향력이 오른다.",
     "Secure the streets and docks of the new capital. Royalist dukes gain influence.", 5, ["dukes_summit"], [],
     [INF("normandy", 12), INF("fife", 12), "TU_build_infrastructure = yes", "army_experience = 15"], "GFX_goal_generic_construct_infrastructure", []),
    ("a1_royal_guard", "왕실 근위대 유산", "Legacy of the Royal Guard", "옛 근위대의 이름으로 충성을 모은다. 왕당 공작들의 영향력이 크게 오른다.",
     "Rally loyalty in the name of the old Royal Guard. Royalist dukes gain much influence.", 5, ["a1_glasgow"], [],
     [INF("normandy", 12), INF("fife", 12), "add_manpower = 8000", "add_stability = 0.02"], "GFX_goal_generic_army_tanks", []),
    ("a1_mobilize", "공작군 동원령", "Ducal Levy", "공작들의 영지군을 끌어모은다. 귀족 세력(캐스터·애버콘)이 힘을 얻고, 웰링턴이 소외된다. (자구군 접촉·웰링턴 회유와 택일)",
     "Call up the ducal estate armies. The nobles (Caster, Abercorn) gain power; Wellington is sidelined. (Exclusive with the other two)", 10,
     ["dukes_summit"], ["a1_selfsalv", "a1_wellington"],
     [INF("caster", 15), INF("abercorn", 10), LOY("caster", 6), LOY("wellington", -6), "add_manpower = 20000", "army_experience = 25"],
     "GFX_goal_generic_major_war", []),
    ("a1_selfsalv", "자구군 비밀 접촉", "Secret Contact with the Self-Salvation Corps", "론디니움 안의 자구군과 선을 댄다. 개혁 세력(스태퍼드·고도딘)이 힘을 얻고 파편이 늦춰진다.",
     "Reach the Self-Salvation Corps inside Londinium. Reformists (Stafford, Godolphin) gain power and the Shard slows.", 10,
     ["dukes_summit"], ["a1_mobilize", "a1_wellington"],
     [INF("stafford", 15), INF("godolphin", 12), LOY("stafford", 6), SLOW, "add_political_power = 50"], "GFX_goal_generic_secret_weapon", []),
    ("a1_wellington", "웰링턴 회유", "Win Over Wellington", "웰링턴 공작을 회유해 군부를 묶는다. 타라 동조 세력(웰링턴·윈더미어)이 힘을 얻고 캐스터가 반발한다.",
     "Win over Duke Wellington and bind the military. The Tara-leaning (Wellington, Windermere) gain power; Caster takes offence.", 10,
     ["dukes_summit"], ["a1_mobilize", "a1_selfsalv"],
     [INF("wellington", 15), INF("windermere", 10), LOY("wellington", 12), LOY("caster", -8), "army_experience = 25"], "GFX_goal_generic_small_arms", []),
    # 귀족
    ("a1_noble_levy", "영지 징집령", "Estate Conscription", "영지마다 장정을 뽑는다. 병력이 늘지만 안정도가 조금 깎인다.", "Draft men from every estate. Manpower rises but stability dips.", 10,
     ["a1_mobilize"], [], ["add_manpower = 30000", "add_stability = -0.03"], "GFX_goal_generic_army_tanks", []),
    ("a1_noble_council", "귀족 의회 장악", "Seize the Noble Council", "귀족 의회의 표를 묶는다. 캐스터·애버콘의 영향력이 오르고 정치력을 얻는다.", "Bind the votes of the noble council. Caster and Abercorn gain influence and political power.", 10,
     ["a1_mobilize"], [], [INF("caster", 10), INF("abercorn", 10), "add_political_power = 50"], "GFX_goal_generic_political_pressure", []),
    ("a1_noble_army", "공작군 편제", "Ducal Army Organisation", "영지군을 한 지휘 아래 묶는다. 경험치와 보병 연구 보너스를 얻는다.", "Bring the estate armies under one command. Gain experience and an infantry research bonus.", 10,
     ["a1_mobilize"], [], ["army_experience = 40", "add_tech_bonus = { name = TU_VIC_a1_noble_army bonus = 0.75 uses = 1 category = infantry_weapons }"], "GFX_goal_generic_small_arms", []),
    # 개혁·자구군
    ("a1_reform_press", "지하 인쇄소", "Underground Presses", "론디니움에서 새어 나온 소식을 찍어 퍼뜨린다. 스태퍼드의 영향력이 오르고 안정도가 오른다.", "Print and spread word that leaks from Londinium. Stafford gains influence; stability rises.", 10,
     ["a1_selfsalv"], [], [INF("stafford", 10), "add_stability = 0.03", "add_political_power = 25"], "GFX_goal_generic_propaganda", []),
    ("a1_reform_rhodes", "로도스 침투조 연락", "Contact the Rhodes Island Team", "로도스 아일랜드 침투조와 연락선을 만든다. 파편이 늦춰진다.", "Open a line to the Rhodes Island infiltration team. The Shard slows.", 10,
     ["a1_selfsalv"], [], [SLOW, SLOW, "if = { limit = { country_exists = RHO } RHO = { add_opinion_modifier = { target = VIC modifier = TU_dip_trade } } }"], "GFX_goal_generic_secret_weapon", []),
    ("a1_reform_militia", "시민 무장", "Arm the Citizens", "시민들에게 소총을 나눠 준다. 인력과 보병 장비를 얻는다.", "Hand out rifles to citizens. Gain manpower and infantry equipment.", 10,
     ["a1_selfsalv"], [], ["add_manpower = 20000", "add_equipment_to_stockpile = { type = infantry_equipment amount = 1000 producer = VIC }", INF("godolphin", 10)], "GFX_goal_generic_small_arms", []),
    # 타라
    ("a1_tara_envoy", "타라 밀사", "Envoy from Tara", "더블린의 타라 세력과 밀사를 주고받는다. 웰링턴과 윈더미어의 영향력이 오른다.", "Exchange envoys with the Tara faction in Dublinn. Wellington and Windermere gain influence.", 10,
     ["a1_wellington"], [], [INF("wellington", 10), INF("windermere", 8), "add_political_power = 25"], "GFX_goal_generic_political_pressure", []),
    ("a1_tara_ls", "육상전함 정비", "Overhaul the Land Battleships", "웰링턴의 육상전함을 정비한다. 포병 연구 보너스와 웰링턴 충성도.", "Overhaul Wellington's land battleships. An artillery research bonus and Wellington loyalty.", 10,
     ["a1_wellington"], [], [LOY("wellington", 6), "add_tech_bonus = { name = TU_VIC_a1_tara_ls bonus = 0.75 uses = 1 category = artillery }"], "GFX_goal_generic_army_tanks", []),
    ("a1_tara_junta", "군부 결속", "Bind the Military", "군부 공작들을 한 편으로 묶는다. 윈더미어 충성도와 육군 경험치.", "Bind the military dukes together. Windermere loyalty and army experience.", 10,
     ["a1_wellington"], [], [LOY("windermere", 10), "army_experience = 40"], "GFX_goal_generic_major_war", []),
    # 합류
    ("a1_siege", "론디니움 포위망 구축", "Encircle Londinium", "론디니움 둘레에 요새와 보급선을 쌓는다. 어느 쪽에 비중을 두었든 이어서 할 수 있다.",
     "Raise forts and supply lines around Londinium. Open to whichever emphasis you chose.", 10,
     [["a1_noble_council", "a1_reform_rhodes", "a1_tara_envoy"]], [], ["TU_build_forts_2 = yes", "army_experience = 25", "add_command_power = 10", "117 = { add_claim_by = VIC }"],
     "GFX_goal_generic_construct_infrastructure", []),
    ("a1_shard_stop", "파편 저지 작전", "Operation: Halt the Shard", "론디니움 탈환 작전을 연다. 카즈델을 상대로 영유권 전쟁 목표를 얻고 파편을 늦춘다.",
     "Launch the operation to retake Londinium. Gain a claim war goal against Kazdel and slow the Shard.", 10, ["a1_siege"], [],
     [SLOW, SLOW, "army_experience = 25", "if = { limit = { country_exists = KZD } create_wargoal = { type = take_claimed_state target = KZD } }"],
     "GFX_goal_generic_major_war", []),
    ("a1_end", "사변의 종결", "End of the Londinium Incident", "론디니움을 되찾았거나 파편이 발동한 뒤에 찍을 수 있다. 세력 균형이 2막의 정치 루트를 정한다.",
     "Available once Londinium is retaken or the Shard has fired. The balance of factions decides the route of Act 2.", 5, ["a1_shard_stop"], [],
     ["remove_ideas = TU_VIC_red_fog", "country_event = { id = tu_vic_ev.41 }"], "GFX_goal_generic_neutrality_focus",
     ["OR = { controls_state = 117 has_country_flag = TU_VIC_shard_fired }"]),
]

# 카즈델 강탈 루트 (배드엔딩 분기에서 되살아나는 길)
KZ = [
    ("kz_head", "살카즈의 용광로", "The Sarkaz Crucible", "파편이 깨어난 빅토리아는 살카즈의 용광로가 된다. 테레시스가 '보호'를 대가로 공업을 요구하고, 고해신부가 빅토리아의 얼굴이 된다. 서명하면 카즈델의 보호국이 된다.",
     "With the Shard awake, Victoria becomes a Sarkaz crucible. Theresis demands industry in return for 'protection' and the Confessor becomes the face of Victoria. Signing makes Victoria a Kazdel protectorate.", 5, ["a1_end"],
     ["KZD = { puppet = VIC }", "add_ideas = TU_VIC_kz_extortion", "set_country_flag = TU_VIC_kz_signed",
      "recruit_character = TU_VIC_confessor_leader", "promote_character = { character = TU_VIC_confessor_leader ideology = fascism_ideology }"]),
    ("kz_levy", "공업 징발", "Industrial Levy", "카즈델이 공장 가동분을 징발해 간다. 대신 정치력을 얻는다.", "Kazdel seizes part of the factory output. In return, political power.", 10, ["kz_head"], ["add_political_power = 100"]),
    ("kz_governor", "총독부 협력", "Cooperate with the Governorate", "총독부에 협력해 숨 돌릴 틈을 번다. 안정도가 오르지만 저항이 식는다.", "Cooperate with the governorate to buy breathing space. Stability rises, resistance cools.", 10, ["kz_levy"],
     ["add_stability = 0.05", "add_political_power = 75"]),
    ("kz_dukes", "공작령 보장", "Guarantee the Ducal Estates", "공작들의 영지를 보장하고 충성을 산다. 모든 공작의 충성도가 오른다.", "Guarantee the ducal estates and buy loyalty. Every duke's loyalty rises.", 10, ["kz_governor"],
     [LOY("caster", 8), LOY("wellington", 8), LOY("windermere", 8), LOY("godolphin", 8), LOY("normandy", 8), LOY("abercorn", 8), LOY("stafford", 8), LOY("fife", 8)]),
    ("kz_resist", "지하 저항망", "Underground Resistance", "징발 속에서 지하 저항망을 짠다. 인력과 육군 경험치.", "Weave an underground resistance under the levy. Manpower and army experience.", 10, ["kz_levy"],
     ["add_manpower = 30000", "army_experience = 40"]),
    ("kz_arms", "비밀 무기고", "Secret Arsenals", "징발에서 빼돌린 무기를 숨긴다. 보병 장비와 군수 공장.", "Hide weapons diverted from the levy. Infantry equipment and a military factory.", 10, ["kz_resist"],
     ["add_equipment_to_stockpile = { type = infantry_equipment amount = 3000 producer = VIC }", "TU_build_mil_factory = yes"]),
    ("kz_strikes", "공장 파업 조직", "Organise Factory Strikes", "공장마다 파업을 조직해 징발을 늦춘다. 공작들의 불만이 영지마다 번진다.", "Organise strikes factory by factory to slow the levy.", 10, ["kz_resist"],
     ["add_political_power = 50", "TU_build_civ_factory = yes"]),
    ("kz_shard", "파편 해체 공작", "Dismantle the Shard", "자구군과 로도스의 도움으로 파편을 해체한다. 재앙 국민정신이 사라진다.", "With the Self-Salvation Corps and Rhodes Island, dismantle the Shard. The calamity spirit is lifted.", 15,
     ["kz_arms", "kz_strikes"], ["remove_ideas = TU_VIC_shard_aftermath", "add_stability = 0.05"]),
    ("kz_uprising", "독립 봉기", "Uprising for Independence", "모든 것을 걸고 봉기한다. 카즈델의 보호국에서 벗어난다.", "Rise up with everything at stake. Victoria breaks free of its Kazdel protector.", 15, ["kz_shard"],
     ["if = { limit = { country_exists = KZD } KZD = { end_puppet = VIC } }", "army_experience = 50", "add_war_support = 0.10"]),
    ("kz_free", "자유 빅토리아", "A Free Victoria", "강탈은 끝났다. 징발 국민정신이 사라지고 공업이 돌아온다.", "The extortion is over. The levy lifts and industry returns.", 15, ["kz_uprising"],
     ["remove_ideas = TU_VIC_kz_extortion", "TU_build_civ_factory = yes", "TU_build_civ_factory = yes", "add_stability = 0.10"]),
]


def focus_text(fid, icon, pre, me, cost, effects, available=(), route=None, ai=1):
    out = ["\tfocus = {", "\t\tid = %s%s" % (P, fid), "\t\ticon = %s" % icon]
    for g in pre:
        g = g if isinstance(g, list) else [g]
        out.append("\t\tprerequisite = { %s }" % " ".join("focus = %s%s" % (P, x) for x in g))
    if me:
        out.append("\t\tmutually_exclusive = { %s }" % " ".join("focus = %s%s" % (P, x) for x in me))
    out += ["\t\tx = 0", "\t\ty = 0", "\t\tcost = %d" % cost]
    if route:
        out += ["\t\tallow_branch = {", "\t\t\thas_country_flag = TU_VIC_route_%s" % route, "\t\t}"]
    out += ["", "\t\tsearch_filters = { FOCUS_FILTER_POLITICAL }", ""]
    if available:
        out += ["\t\tavailable = {"] + ["\t\t\t%s" % a for a in available] + ["\t\t}", ""]
    out += ["\t\tai_will_do = {", "\t\t\tbase = %d" % ai, "\t\t}", "", "\t\tcompletion_reward = {"] + ["\t\t\t%s" % e for e in effects] + ["\t\t}", "\t}", ""]
    return "\n".join(out)


def write_parts():
    a1 = "".join(focus_text(i, ic, pre, me, c, eff, av) for i, _, _, _, _, c, pre, me, eff, ic, av in ACT1)
    (HERE / "vic" / "p0_act1.txt").write_text(a1, encoding="utf-8")
    kz = "".join(focus_text(i, "GFX_goal_generic_neutrality_focus" if n == 0 else "GFX_goal_generic_secret_weapon", pre, [], c, eff, route="kzd")
                 for n, (i, _, _, _, _, c, pre, eff) in enumerate(KZ))
    # 아슬란 노선의 모범군 편제 (특수 프로젝트 해금)
    kz += focus_text("asl_exemplars", "GFX_goal_generic_army_tanks", ["asl_royal_army"], [], 15,
                     ["set_country_flag = TU_VIC_exemplars_unlocked", "army_experience = 30", "add_stability = 0.03"], route="asl")
    (HERE / "vic" / "p4_extra.txt").write_text(kz, encoding="utf-8")


def loc():
    ko = ["l_korean:", " # generated by tools/focusgen/vic_acts.py (spec 80)"]
    en = ["l_english:", " # generated by tools/focusgen/vic_acts.py (spec 80)"]
    for i, k, e, dk, de, *_ in ACT1:
        ko += [' %s%s:0 "%s"' % (P, i, k), ' %s%s_desc:0 "%s"' % (P, i, dk)]
        en += [' %s%s:0 "%s"' % (P, i, e), ' %s%s_desc:0 "%s"' % (P, i, de)]
    for i, k, e, dk, de, *_ in KZ:
        ko += [' %s%s:0 "%s"' % (P, i, k), ' %s%s_desc:0 "%s"' % (P, i, dk)]
        en += [' %s%s:0 "%s"' % (P, i, e), ' %s%s_desc:0 "%s"' % (P, i, de)]
    ko += [' TU_VIC_confessor_leader:0 "고해신부"', ' TU_VIC_reed_leader:0 "리드"', ' TU_VIC_faust_commander:0 "파이스트"',
           ' TU_VIC_asl_exemplars:0 "모범군 개편"', ' TU_VIC_asl_exemplars_desc:0 "아슬란 복위군의 정예를 \'모범군\'으로 개편한다. \'특수 프로젝트\'에서 모범군 사단을 세울 수 있다."',
           ' TU_VIC_red_fog:0 "붉은 안개"', ' TU_VIC_red_fog_desc:0 "론디니움 하늘의 붉은 안개 아래 왕좌는 비어 있고, 사람들은 불안해한다. 안정도 -5%, 정치력 -10%, 전쟁 지지 -5%. 사변이 끝나면 걷힌다."',
           ' TU_VIC_kz_extortion:0 "카즈델의 강탈"', ' TU_VIC_kz_extortion_desc:0 "카즈델이 보호를 대가로 공업을 징발한다. 공장 출력 -25%, 안정도 -10%."',
           ' tu_vic_ev.41.t:0 "론디니움 사변의 끝"', ' tu_vic_ev.41.d:0 "사변은 끝났다. 어느 공작 세력이 가장 큰 힘을 얻었느냐가 빅토리아의 다음 길을 정한다. 한 세력의 영향력이 §Y80§! 이상이면 그 루트를 고를 수 있다.\\n\\n귀족 %s · 왕당 %s · 타라 %s · 개혁 %s"',
           ' tu_vic_ev.41.a:0 "철혈의 대공 의회. (캐스터 공작)"', ' tu_vic_ev.41.b:0 "아슬란의 새벽. (비나 빅토리아)"',
           ' tu_vic_ev.41.c:0 "자줏빛 불꽃. (에블라나 / 웰링턴)"', ' tu_vic_ev.41.e:0 "자구군 혁명. (클로비시아 / 파이스트)"',
           ' tu_vic_ev.41.f:0 "가장 큰 세력을 따른다."', ' tu_vic_ev.41.g:0 "살카즈의 용광로. (테레시스 / 고해신부)"']
    en += [' TU_VIC_confessor_leader:0 "The Confessor"', ' TU_VIC_reed_leader:0 "Reed"', ' TU_VIC_faust_commander:0 "Faust"',
           ' TU_VIC_asl_exemplars:0 "Reform into the Exemplars"', ' TU_VIC_asl_exemplars_desc:0 "Reorganise the elite of the Aslan restoration army as the Exemplars. Exemplar divisions can be raised from Special Projects."',
           ' TU_VIC_red_fog:0 "The Red Fog"', ' TU_VIC_red_fog_desc:0 "Under the red fog over Londinium the throne is empty and people are uneasy. Stability -5%, political power -10%, war support -5%. It lifts when the Incident ends."',
           ' TU_VIC_kz_extortion:0 "Kazdel\'s Extortion"', ' TU_VIC_kz_extortion_desc:0 "Kazdel levies industry in return for protection. Factory output -25%, stability -10%."',
           ' tu_vic_ev.41.t:0 "The End of the Londinium Incident"', ' tu_vic_ev.41.d:0 "The Incident is over. Which ducal faction gained the most power decides Victoria\'s next road. A faction with §Y80§! or more influence can choose its route.\\n\\nNobles %s · Royalists %s · Tara %s · Reformists %s"',
           ' tu_vic_ev.41.a:0 "The Iron-Blood Ducal Council. (Duke Caster)"', ' tu_vic_ev.41.b:0 "The Dawn of Aslan. (Vina Victoria)"',
           ' tu_vic_ev.41.c:0 "The Purple Flame. (Eblana / Wellington)"', ' tu_vic_ev.41.e:0 "Revolution of the Self-Salvation Corps. (Clovisia / Faust)"',
           ' tu_vic_ev.41.f:0 "Follow the strongest faction."', ' tu_vic_ev.41.g:0 "The Sarkaz Crucible. (Theresis / the Confessor)"']
    # 이벤트 본문의 수치는 변수 표기로
    ko = [l.replace("귀족 %s · 왕당 %s · 타라 %s · 개혁 %s", "귀족 [?TU_VIC_f_noble|0] · 왕당 [?TU_VIC_f_royal|0] · 타라 [?TU_VIC_f_tara|0] · 개혁 [?TU_VIC_f_reform|0]") for l in ko]
    en = [l.replace("Nobles %s · Royalists %s · Tara %s · Reformists %s", "Nobles [?TU_VIC_f_noble|0] · Royalists [?TU_VIC_f_royal|0] · Tara [?TU_VIC_f_tara|0] · Reformists [?TU_VIC_f_reform|0]") for l in en]
    (MOD / "localisation" / "korean" / "tu_vic_act_l_korean.yml").write_bytes(("\n".join(ko) + "\n").encode("utf-8-sig"))
    (MOD / "localisation" / "english" / "tu_vic_act_l_english.yml").write_bytes(("\n".join(en) + "\n").encode("utf-8-sig"))


def game_files():
    (MOD / "common" / "ideas" / "tu_vic_act_ideas.txt").write_text("""# generated by tools/focusgen/vic_acts.py (spec 80)
ideas = {
	country = {
		TU_VIC_red_fog = {
			picture = generic_fortify_the_borders
			allowed = { always = no }
			allowed_civil_war = { always = yes }
			removal_cost = -1
			modifier = {
				stability_factor = -0.05
				political_power_gain = -0.10
				war_support_factor = -0.05
			}
		}
		TU_VIC_kz_extortion = {
			picture = generic_fortify_the_borders
			allowed = { always = no }
			allowed_civil_war = { always = yes }
			removal_cost = -1
			modifier = {
				industrial_capacity_factory = -0.25
				stability_factor = -0.10
			}
		}
	}
}
""", encoding="utf-8")
    (MOD / "common" / "scripted_effects" / "tu_vic_act_effects.txt").write_text("""# generated by tools/focusgen/vic_acts.py (spec 80)
# 공작 세력의 영향력 합 (귀족 = 캐스터+애버콘, 왕당 = 노르망디+파이프, 타라 = 웰링턴+윈더미어, 개혁 = 스태퍼드+고도딘)
TU_VIC_calc_factions = {
	set_variable = { TU_VIC_f_noble = TU_VIC_influence_caster }
	add_to_variable = { TU_VIC_f_noble = TU_VIC_influence_abercorn }
	set_variable = { TU_VIC_f_royal = TU_VIC_influence_normandy }
	add_to_variable = { TU_VIC_f_royal = TU_VIC_influence_fife }
	set_variable = { TU_VIC_f_tara = TU_VIC_influence_wellington }
	add_to_variable = { TU_VIC_f_tara = TU_VIC_influence_windermere }
	set_variable = { TU_VIC_f_reform = TU_VIC_influence_stafford }
	add_to_variable = { TU_VIC_f_reform = TU_VIC_influence_godolphin }
}

# 가장 큰 세력을 따른다 (기본 선택)
TU_VIC_pick_strongest = {
	TU_VIC_calc_factions = yes
	set_variable = { TU_VIC_f_best = TU_VIC_f_noble }
	set_country_flag = TU_VIC_route_duk
	if = {
		limit = { check_variable = { TU_VIC_f_royal > TU_VIC_f_best } }
		set_variable = { TU_VIC_f_best = TU_VIC_f_royal }
		clr_country_flag = TU_VIC_route_duk
		set_country_flag = TU_VIC_route_asl
	}
	if = {
		limit = { check_variable = { TU_VIC_f_tara > TU_VIC_f_best } }
		set_variable = { TU_VIC_f_best = TU_VIC_f_tara }
		clr_country_flag = TU_VIC_route_duk
		clr_country_flag = TU_VIC_route_asl
		set_country_flag = TU_VIC_route_drc
	}
	if = {
		limit = { check_variable = { TU_VIC_f_reform > TU_VIC_f_best } }
		clr_country_flag = TU_VIC_route_duk
		clr_country_flag = TU_VIC_route_asl
		clr_country_flag = TU_VIC_route_drc
		set_country_flag = TU_VIC_route_par
	}
}
""", encoding="utf-8")
    opts = []
    spec = [("a", "route_duk", "f_noble", 25), ("b", "route_asl", "f_royal", 25), ("c", "route_drc", "f_tara", 20), ("e", "route_par", "f_reform", 30)]
    for key, flag, var, ai in spec:
        opts.append("""	option = {
		name = tu_vic_ev.41.%s
		trigger = {
			NOT = { has_country_flag = TU_VIC_shard_fired }
			check_variable = { TU_VIC_%s > 79 }
		}
		ai_chance = { factor = %d }
		set_country_flag = TU_VIC_%s
		mark_focus_tree_layout_dirty = yes
	}
""" % (key, var, ai, flag))
    opts.append("""	option = {
		name = tu_vic_ev.41.f
		trigger = { NOT = { has_country_flag = TU_VIC_shard_fired } }
		ai_chance = { factor = 10 }
		TU_VIC_pick_strongest = yes
		mark_focus_tree_layout_dirty = yes
	}

	option = {
		name = tu_vic_ev.41.g
		trigger = { has_country_flag = TU_VIC_shard_fired }
		ai_chance = { factor = 100 }
		set_country_flag = TU_VIC_route_kzd
		mark_focus_tree_layout_dirty = yes
	}
""")
    ev = (MOD / "events" / "tu_vic_events.txt")
    t = ev.read_text(encoding="utf-8-sig")
    t = re.sub(r"\n# 41\. Focus TU_VIC_a1_end.*", "", t, flags=re.S)
    t = t.rstrip("\n") + """

# 41. Focus TU_VIC_a1_end: the end of the Londinium Incident decides the route of Act 2 (spec 80).
country_event = {
	id = tu_vic_ev.41
	title = tu_vic_ev.41.t
	desc = tu_vic_ev.41.d
	picture = GFX_report_event_generic_conference
	is_triggered_only = yes

	immediate = { TU_VIC_calc_factions = yes }

""" + "\n".join(opts) + "}\n"
    ev.write_text(t, encoding="utf-8")


def patch_existing():
    p0 = HERE / "vic" / "p0_existing.txt"
    s = p0.read_text(encoding="utf-8")

    def block_span(s, fid):
        m = re.search(r"\n\tfocus = \{\n\t\tid = %s%s\n" % (P, fid), s)
        e = s.index("\n\t}\n", m.end()) + 4
        return m.start(), e

    a, e = block_span(s, "dukes_summit")
    b = s[a:e]
    if "tu_vic_ev.40" in b or "TU_VIC_red_fog" not in b:
        b = b.replace("country_event = { id = tu_vic_ev.40 }", "")
        b = re.sub(r"(completion_reward = \{)", r"\1\n\t\t\tadd_ideas = TU_VIC_red_fog\n\t\t\tset_country_flag = TU_VIC_act1_started", b, count=1)
        s = s[:a] + b + s[e:]
        p0.write_text(s, encoding="utf-8")
    # 루트 머리의 선행 중점: 사변의 종결
    for part in ("p0_existing", "p1_politics"):
        f = HERE / "vic" / (part + ".txt")
        t = f.read_text(encoding="utf-8")
        n = t
        for head in ("duk_route", "glasgow_return", "dublinn_uprising", "par_route"):
            n = re.sub(r"(\tid = %s%s\n(?:(?!\n\t\}).)*?prerequisite = \{ focus = )%sdukes_summit( \})" % (P, head, P), r"\g<1>%sa1_end\2" % P, n, flags=re.S)
        if n != t:
            f.write_text(n, encoding="utf-8")
    # 이름 문구
    for lang in ("korean", "english"):
        for f in (MOD / "localisation" / lang).glob("*.yml"):
            t = f.read_text(encoding="utf-8-sig")
            n = t
            if lang == "korean":
                n = n.replace(' TU_VIC_crown_focus:0 "왕위 공석"', ' TU_VIC_crown_focus:0 "공석인 옥좌와 붉은 안개"')
                n = n.replace(' TU_VIC_dukes_summit:0 "대공 회의 소집"', ' TU_VIC_dukes_summit:0 "의회의 긴급 소집"')
                for k, v in ROUTE_KO.items():
                    n = re.sub(r'^ %s:0 ".*"$' % k, ' %s:0 "%s"' % (k, v), n, flags=re.M)
            else:
                for k, v in ROUTE_EN.items():
                    n = re.sub(r'^ %s:0 ".*"$' % k, ' %s:0 "%s"' % (k, v), n, flags=re.M)
                n = n.replace(' TU_VIC_crown_focus:0 "Empty Throne"', ' TU_VIC_crown_focus:0 "The Empty Throne and the Red Fog"')
                n = n.replace(' TU_VIC_dukes_summit:0 "Ducal Summit"', ' TU_VIC_dukes_summit:0 "Emergency Session of Parliament"')
            n = re.sub(r'(^ TU_VIC_dukes_summit_desc:0 ).*$', lambda m: m.group(1) + '"론디니움이 카즈델에 넘어간 지금, 대공들을 글래스고에 불러 모아 의회를 연다."' if lang == "korean" else m.group(1) + '"With Londinium lost to Kazdel, summon the dukes to Glasgow and open the council."', n, flags=re.M)
            if n != t:
                f.write_text("﻿" + n, encoding="utf-8")


def main():
    patch_existing()
    write_parts()
    loc()
    game_files()
    print("VIC_ACTS act1=%d kazdel=%d" % (len(ACT1), len(KZ)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
