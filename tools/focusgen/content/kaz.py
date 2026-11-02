#!/usr/bin/env python3
"""카시미어(KAZ) 고유 콘텐츠 (사양서 17).

장치
  1. 세력 균형 "상업 연합회 대 기사의 명예" (TU_KAZ_bop): 왼쪽 = 연합회, 오른쪽 = 기사.
     2·3단계가 켜져 있는 동안 깃발 TU_KAZ_union_strong / TU_KAZ_knights_strong.
  2. 기사 명성 변수 TU_KAZ_fame (0~100): 메이저 기사 경기·기사 중점·디시전으로 오르고, 정예 기사 중점·디시전을 연다.
  3. 카시미어 메이저: 디시전으로 1년에 한 번 개최 → 개막·준결승·결승 이벤트 (우승자 유형에 따라 결과가 다름).
  4. 기사 계약: 유목 기사·기업 기사·용병을 디시전으로 고용, 기사를 외국에 파견해 정치력을 번다.
정치 결말 셋 (서로 배타): 주주의 나라(연합회) / 기사의 나라(기사) / 모두를 위한 기사도(감염자 기사).

실행: python -I tools/focusgen/content/kaz.py && python -I tools/focusgen/merge_focus.py --tag KAZ
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content_lib import Country  # noqa: E402

C = Country("KAZ", "카시미어", "Kazimierz")
BOP = "TU_KAZ_bop"


def U(v):   # 상업 연합회 쪽으로
    return "add_power_balance_value = { id = %s value = -%s }" % (BOP, v)


def K(v):   # 기사 쪽으로
    return "add_power_balance_value = { id = %s value = %s }" % (BOP, v)


def FAME(n):
    return "TU_KAZ_fame_%d = yes" % n


def FAME_AT_LEAST(n):
    return "check_variable = { TU_KAZ_fame > %d }" % (n - 1)


def FLAG(x):
    return "set_country_flag = TU_KAZ_%s" % x


def HAS(x):
    return "has_country_flag = TU_KAZ_%s" % x


def EV(n, days=0):
    return "country_event = { id = tu_kaz_ev.%d%s }" % (n, " days = %d" % days if days else "")


# ------------------------------------------------------------------ 시작 상태 · 세력 균형 · 명성
C.set_bop(("union", "상업 연합회", "Commercial Union", "GFX_bop_ITA_grand_council_side"),
          ("knights", "기사의 명예", "Knightly Honour", "GFX_bop_DEN_warfare_side"),
          -0.35,
          [(0, 0.3, {"production_speed_buildings_factor": 0.05, "political_power_gain": 0.05}),
           (0.3, 0.6, {"production_speed_buildings_factor": 0.1, "consumer_goods_factor": -0.03,
                       "stability_factor": -0.03}, "TU_KAZ_union_strong"),
           (0.6, 1, {"production_speed_buildings_factor": 0.15, "political_power_gain": 0.1,
                     "stability_factor": -0.08, "war_support_factor": -0.05}, "TU_KAZ_union_strong")],
          [(0, 0.3, {"army_org_factor": 0.03}),
           (0.3, 0.6, {"army_org_factor": 0.05, "war_support_factor": 0.05}, "TU_KAZ_knights_strong"),
           (0.6, 1, {"army_attack_factor": 0.08, "war_support_factor": 0.1, "political_power_gain": -0.1},
            "TU_KAZ_knights_strong")])
C.loc(BOP, "상업 연합회 대 기사의 명예", "Commercial Union vs Knightly Honour")
C.loc(BOP + "_desc", "카시미어는 기업이 기사를 후원하고 광고판에 세우는 나라가 되었다. 기사들은 잃어버린 명예를 되찾으려 한다.",
      "Kazimierz has become a land where corporations sponsor knights and put them on billboards. The knights want their lost honour back.")
C.history += ["set_variable = { TU_KAZ_fame = 10 }", "add_ideas = { TU_KAZ_union_grip TU_KAZ_fading_knighthood }"]

for n in (5, 10, 15, 20):
    C.effects.append("""TU_KAZ_fame_%d = {
	custom_effect_tooltip = TU_KAZ_fame_tt_%d
	hidden_effect = {
		add_to_variable = { TU_KAZ_fame = %d }
		clamp_variable = { var = TU_KAZ_fame min = 0 max = 100 }
	}
}""" % (n, n, n))
    C.loc("TU_KAZ_fame_tt_%d" % n, "§G기사 명성 +%d§!" % n, "§GKnight Fame +%d§!" % n)
C.loc("TU_KAZ_fame_req_tt", "기사 명성", "Knight Fame")

# ------------------------------------------------------------------ 국민정신
C.idea("union_grip", "연합회의 손아귀", "Grip of the Union",
       {"political_power_gain": -0.1, "production_speed_buildings_factor": 0.05, "stability_factor": -0.03},
       "generic_foreign_capital", ("상업 연합회가 의회와 언론과 기사를 쥐고 있다.", "The Commercial Union holds parliament, press and knights alike."))
C.idea("fading_knighthood", "저무는 기사도", "Fading Knighthood",
       {"army_org_factor": -0.05, "war_support_factor": -0.05}, "generic_army_problems",
       ("기사들은 광고 모델이 되었고, 옛 기사단은 이름만 남았다.", "Knights have become advertising models; the old orders survive only in name."))
C.idea("major_spirit", "메이저의 열기", "Fever of the Major",
       {"war_support_factor": 0.05, "experience_gain_army_factor": 0.05}, "generic_morale_bonus",
       ("해마다 열리는 기사 경기에 온 나라가 들썩인다.", "The whole nation is gripped by the annual knight tournament."))
C.idea("legendary_knights", "전설의 기사들", "Legendary Knights",
       {"war_support_factor": 0.08, "experience_gain_army_factor": 0.1, "army_morale_factor": 0.05}, "generic_army_war_college")
C.idea("union_monopoly", "독점 체제", "Monopoly System",
       {"production_speed_buildings_factor": 0.1, "political_power_gain": 0.05, "stability_factor": -0.05},
       "generic_foreign_capital")
C.idea("fair_market", "공정 시장", "Fair Market",
       {"consumer_goods_factor": -0.03, "stability_factor": 0.05}, "generic_economic_increase")
C.idea("shareholder_state", "주주의 나라", "Shareholder State",
       {"production_factory_max_efficiency_factor": 0.1, "political_power_gain": 0.15, "war_support_factor": -0.05},
       "generic_economic_increase")
C.idea("commercial_empire", "상업 제국", "Commercial Empire",
       {"production_factory_max_efficiency_factor": 0.1, "consumer_goods_factor": -0.05, "political_power_gain": 0.1},
       "generic_industrial_concern_1")
C.idea("knightly_code", "기사도 규범", "Knightly Code",
       {"army_org_factor": 0.05, "war_support_factor": 0.05}, "professional_officer_corps_spirit")
C.idea("knight_kingdom", "기사의 나라", "Kingdom of Knights",
       {"army_attack_factor": 0.08, "army_org_factor": 0.05, "war_support_factor": 0.1}, "generic_army_war_college")
C.idea("royal_knights", "왕립 기사단", "Royal Knight Orders",
       {"army_attack_factor": 0.05, "army_defence_factor": 0.05, "experience_gain_army_factor": 0.1},
       "generic_army_europe_1")
C.idea("knights_for_all", "모두를 위한 기사도", "Knighthood for All",
       {"stability_factor": 0.1, "conscription_factor": 0.05, "army_morale_factor": 0.05}, "generic_pp_unity_bonus",
       ("감염자도 기사가 될 수 있다. 기사도는 피와 원석이 아니라 마음에 있다.",
        "The infected may be knights too. Knighthood lies in the heart, not in blood or originium."))
C.idea("shining_knights", "빛나는 기사들", "Shining Knights",
       {"army_morale_factor": 0.08, "stability_factor": 0.05, "monthly_population": 0.1}, "generic_morale_bonus")
C.idea("oripathy_care", "광석병 진료망", "Oripathy Care Network",
       {"stability_factor": 0.05, "monthly_population": 0.1}, "generic_morale_bonus")
C.idea("kazimierz_lancers", "카시미어 창기병단", "Kazimierz Lancers",
       {"army_speed_factor": 0.05, "army_armor_attack_factor": 0.05, "army_org_factor": 0.05}, "generic_armor")
C.idea("defenders", "카시미어의 수호자", "Defenders of Kazimierz",
       {"army_defence_factor": 0.08, "max_dig_in": 1}, "generic_fortify_the_borders")
C.idea("economic_miracle", "카시미어 경제 기적", "Kazimierz Economic Miracle",
       {"production_factory_max_efficiency_factor": 0.08, "production_speed_buildings_factor": 0.1},
       "generic_production_bonus")
C.idea("neutral", "카시미어 중립", "Kazimierz Neutrality",
       {"stability_factor": 0.05, "political_power_gain": 0.05}, "generic_flexible_foreign_policy")
C.idea("anti_ursus", "반우르수스 연대", "Anti-Ursus Solidarity",
       {"war_support_factor": 0.08, "army_defence_factor": 0.05}, "generic_war_preparation")

# ------------------------------------------------------------------ 중점
f = C.f
f("root", "카시미어의 내일", "Tomorrow of Kazimierz", cost=5, theme=False,
  reward=["add_political_power = 50", EV(1)],
  desc=("기업의 깃발과 기사의 문장이 같은 거리에 걸려 있다. 카시미어는 어느 쪽으로 걸어갈 것인가?",
        "Corporate banners and knightly crests hang on the same streets. Which way will Kazimierz walk?"))

# A. 메이저
f("major_revival", "메이저의 부활", "Revival of the Major", pre=["root"], theme=False,
  reward=[FLAG("major_unlocked"), FAME(5), "add_war_support = 0.03"],
  desc=("카시미어 메이저 기사 경기를 다시 연다. '메이저' 디시전으로 해마다 경기를 열 수 있다.",
        "Bring back the Kazimierz Major. The tournament can be held every year through the Major decisions."))
f("grand_arena", "대경기장 건설", "Grand Arena Construction", pre=["major_revival"], econ=True,
  reward=[FAME(5)])
f("live_broadcast", "생중계 방송", "Live Broadcast of the Major", pre=["grand_arena"], theme=False,
  reward=[U("0.05"), "add_political_power = 60", FLAG("broadcast")],
  desc=("경기를 전국에 생중계한다. 광고 수익은 연합회로 흘러간다.", "Broadcast the matches nationwide. The advertising money flows to the Union."))
f("betting_industry", "베팅 산업", "Betting Industry", pre=["live_broadcast"],
  reward=[U("0.03")])
f("sponsorship_rules", "기업 후원 규정", "Corporate Sponsorship Rules", pre=["live_broadcast"], me=["free_entry"],
  theme=False, reward=[U("0.1"), "add_political_power = 75"],
  desc=("기업이 기사를 후원하고 이름을 붙일 수 있게 한다.", "Allow corporations to sponsor knights and put their names on them."))
f("free_entry", "기사 자율 출전", "Free Entry for Knights", pre=["live_broadcast"], me=["sponsorship_rules"],
  theme=False, reward=[K("0.1"), FAME(10)],
  desc=("후원 없이도 누구나 실력으로 출전할 수 있게 한다.", "Let anyone enter on merit alone, sponsor or not."))
f("major_annual", "메이저 정례화", "The Annual Major", pre=[["sponsorship_rules", "free_entry"]], theme=False,
  reward=["add_ideas = TU_KAZ_major_spirit", FLAG("major_annual"), FAME(5)],
  desc=("메이저를 국가 행사로 정례화한다. 메이저에서 얻는 기사 명성이 늘어난다.",
        "Make the Major a national institution. Fame gained at the Major increases."))
f("knight_scouting", "기사 스카우트망", "Knight Scouting Network", pre=["major_annual"])
f("hall_of_fame", "명예의 전당", "Hall of Fame", pre=["major_annual"], theme=False,
  reward=[FAME(15), "add_war_support = 0.05"])
f("international_major", "메이저의 국제화", "International Major Envoys", pre=["hall_of_fame"],
  reward=[FAME(5)])
f("champion_knights", "챔피언 기사단", "Champion Knight Order", pre=["hall_of_fame"], theme=False,
  available=[FAME_AT_LEAST(50)],
  reward=[FLAG("champions"), "army_experience = 40"],
  desc=("메이저 우승자들로 기사단을 꾸린다. '챔피언 기사단 소집' 디시전이 열린다. (기사 명성 50 이상)",
        "Form an order from Major champions. Unlocks the Summon the Champions decision. (Knight Fame 50+)"))
f("legendary_knights", "전설의 기사들", "Legendary Knights", pre=["champion_knights"], theme=False,
  available=[FAME_AT_LEAST(80)],
  reward=["swap_ideas = { remove_idea = TU_KAZ_major_spirit add_idea = TU_KAZ_legendary_knights }"],
  desc=("이름만으로 적을 물러서게 하는 기사들이 나타났다. (기사 명성 80 이상)",
        "Knights whose names alone make enemies falter. (Knight Fame 80+)"))

# B. 상업 연합회
f("union_council", "상업 연합회 이사회", "Commercial Union Council", pre=["root"], reward=[U("0.05")])
f("corporate_charter", "기업 헌장", "Corporate Charter", pre=["union_council"], reward=[U("0.05")])
f("ad_magnates", "광고 재벌", "Advertising Magnates", pre=["corporate_charter"], reward=[U("0.03")])
f("media_control", "언론 장악", "Media Broadcast Control", pre=["corporate_charter"], theme=False,
  reward=[U("0.05"), "add_stability = 0.03", EV(23, 10)])
f("stock_controls", "주가 관리", "Stock Market Controls", pre=["media_control"], reward=[U("0.03")])
f("knight_contracts", "기사 고용 계약제", "Knight Employment Contracts", pre=["media_control"], theme=False,
  reward=[U("0.05"), FLAG("corp_knights")],
  desc=("기업이 기사를 직원처럼 고용한다. '기업 기사 계약' 디시전이 열린다.",
        "Corporations hire knights like employees. Unlocks the Corporate Knight Contract decision."))
f("union_monopoly", "독점 체제", "Monopoly System", pre=["knight_contracts"], me=["fair_competition"], theme=False,
  reward=[U("0.1"), "swap_ideas = { remove_idea = TU_KAZ_union_grip add_idea = TU_KAZ_union_monopoly }"])
f("fair_competition", "공정 경쟁법", "Fair Competition Act", pre=["knight_contracts"], me=["union_monopoly"], theme=False,
  reward=[K("0.05"), "swap_ideas = { remove_idea = TU_KAZ_union_grip add_idea = TU_KAZ_fair_market }"])
f("shareholder_state", "주주의 나라", "The Shareholder State", pre=[["union_monopoly", "fair_competition"]],
  me=["knight_kingdom", "knights_for_all"], cost=15, theme=False,
  available=[HAS("union_strong")],
  reward=[FLAG("path_union"), "add_ideas = TU_KAZ_shareholder_state", "add_political_power = 100", EV(28)],
  desc=("카시미어는 하나의 거대한 회사가 된다. (상업 연합회 쪽 세력 균형 2단계 이상)",
        "Kazimierz becomes one great company. (Balance of power at Commercial Union stage 2 or more)"))
f("corporate_army", "기업 사병 통합", "Integrate the Corporate Militias", pre=["shareholder_state"])
f("security_companies", "보안 회사", "Security Companies", pre=["shareholder_state"])
f("export_knights", "기사 수출", "Knight Export Trade", pre=["corporate_army"])
f("overseas_branches", "해외 지사", "Overseas Branches", pre=["export_knights"])
f("commercial_empire", "상업 제국", "Commercial Empire", pre=["overseas_branches"], theme=False,
  reward=["add_ideas = TU_KAZ_commercial_empire", "add_political_power = 75"])

# C. 기사의 부활
f("knights_assoc", "기사 협회 재건", "Rebuild the Knights' Association", pre=["root"], reward=[K("0.05")])
f("restore_titles", "기사 작위 복원", "Restore Knightly Titles", pre=["knights_assoc"], theme=False,
  reward=[K("0.05"), FAME(5), "add_political_power = 40"])
f("knight_houses", "기사 가문 연합", "Alliance of Knightly Houses", pre=["restore_titles"], reward=[K("0.03")])
f("old_orders", "옛 기사단 소집", "Summon the Old Orders", pre=["restore_titles"], reward=[K("0.05")])
f("knight_training_fields", "기사 훈련장", "Knight Training Fields", pre=["old_orders"])
f("knight_code", "기사도 규범", "The Knightly Code", pre=["old_orders"], theme=False,
  reward=["swap_ideas = { remove_idea = TU_KAZ_fading_knighthood add_idea = TU_KAZ_knightly_code }", K("0.05")],
  desc=("광고판에서 내려와 다시 맹세를 세운다.", "Step down from the billboards and swear the old oaths again."))
f("honor_duels", "명예 결투 허용", "Legalise Honour Duels", pre=["knight_code"], me=["knight_courts"], theme=False,
  reward=[FAME(10), "add_war_support = 0.05", EV(24, 15)])
f("knight_courts", "기사 재판소", "Knightly Courts", pre=["knight_code"], me=["honor_duels"], theme=False,
  reward=[K("0.05"), "add_stability = 0.05"])
f("knight_kingdom", "기사의 나라", "Kingdom of Knights", pre=[["honor_duels", "knight_courts"]],
  me=["shareholder_state", "knights_for_all"], cost=15, theme=False,
  available=[HAS("knights_strong")],
  reward=[FLAG("path_knights"), "add_ideas = TU_KAZ_knight_kingdom", "add_political_power = 100", EV(29)],
  desc=("기사가 다시 카시미어를 이끈다. (기사 쪽 세력 균형 2단계 이상)",
        "Knights lead Kazimierz once more. (Balance of power at Knightly Honour stage 2 or more)"))
f("noble_estates", "기사 영지 회복", "Restore the Knightly Estates", pre=["knight_kingdom"])
f("chivalry_schools", "기사도 학교", "Chivalry Schools", pre=["knight_kingdom"])
f("restore_citadels", "성채 복원", "Restore the Citadels", pre=["noble_estates"])
f("royal_knights", "왕립 기사단", "Royal Knight Orders", pre=["restore_citadels"], theme=False,
  reward=["add_ideas = TU_KAZ_royal_knights", FAME(10)])

# D. 감염자 기사
f("infected_question", "감염자 기사 문제", "The Infected Knights Question", pre=["root"], theme=False,
  reward=["add_political_power = 30", EV(20)])
f("nearl_voice", "니어 가문의 목소리", "Voice of the Nearl Family", pre=["infected_question"], theme=False,
  reward=[FAME(5), EV(21, 7)])
f("infected_fund", "감염자 지원 기금", "Infected Relief Fund", pre=["nearl_voice"])
f("infected_rights", "감염자 출전권", "Infected Right to Compete", pre=["nearl_voice"], theme=False,
  reward=[FLAG("infected_entry"), FAME(5), "add_stability = -0.02"],
  desc=("감염자 기사도 메이저에 나갈 수 있게 한다. 감염자 우승자가 나올 수 있다.",
        "Let infected knights enter the Major. An infected champion becomes possible."))
f("oripathy_clinics", "광석병 진료소", "Oripathy Clinics", pre=["infected_rights"], theme=False,
  reward=["add_ideas = TU_KAZ_oripathy_care"])
f("suppressant_factory", "억제제 공장", "Suppressant Factory", pre=["oripathy_clinics"], econ=True)
f("equal_knighthood", "평등한 기사도", "Equal Knighthood", pre=["oripathy_clinics"], me=["separate_orders"],
  theme=False, reward=[FAME(10), "add_stability = -0.03", K("0.05")])
f("separate_orders", "감염자 기사단 분리", "Separate Infected Orders", pre=["oripathy_clinics"],
  me=["equal_knighthood"], theme=False, reward=["add_stability = 0.03", "add_manpower = 10000"])
f("knights_for_all", "모두를 위한 기사도", "Knighthood for All", pre=[["equal_knighthood", "separate_orders"]],
  me=["shareholder_state", "knight_kingdom"], cost=15, theme=False,
  available=["OR = {", "\t" + HAS("infected_champion"), "\t" + FAME_AT_LEAST(60), "}"],
  reward=[FLAG("path_infected"), "add_ideas = TU_KAZ_knights_for_all", EV(30)],
  desc=("감염자 기사가 메이저에서 우승했거나, 기사 명성이 60 이상이어야 한다.",
        "Requires an infected Major champion, or Knight Fame of 60 or more."))
f("blemishine_patrols", "블레미샤인 순찰대", "Blemishine's Patrols", pre=["knights_for_all"])
f("shining_knights", "빛나는 기사들", "Shining Knights", pre=["blemishine_patrols"], theme=False,
  reward=["add_ideas = TU_KAZ_shining_knights", FAME(10)])

# E. 기사단 군사
f("knight_academy", "기사 학교", "Knight Academy", pre=["root"])
f("cavalry_officers", "기병 사관", "Cavalry Officers", pre=["knight_academy"])
f("lance_charge", "창기병 돌격", "Lance Cavalry Charge", pre=["knight_academy"])
f("steel_armour", "강철 갑주", "Steel Armour Workshops", pre=["knight_academy"])
f("armour_forges", "갑주 대장간", "Armour Forges", pre=["steel_armour"])
f("armoured_knights", "기갑 기사", "Armoured Knights", pre=["lance_charge", "steel_armour"])
f("mobile_knights", "기동 기사 교리", "Mobile Knight Doctrine", pre=["armoured_knights"], me=["shield_wall"])
f("shield_wall", "방패벽 교리", "Shield Wall Defence Doctrine", pre=["armoured_knights"], me=["mobile_knights"])
f("plains_drills", "평원 기동 훈련", "Plains Mobility Drills", pre=[["mobile_knights", "shield_wall"]])
f("nomadic_knights", "유목 기사단 협약", "Nomadic Knights Pact", pre=[["mobile_knights", "shield_wall"]], theme=False,
  reward=[FLAG("nomads"), FAME(5)],
  desc=("평원을 떠도는 유목 기사들과 협약을 맺는다. '유목 기사단 계약' 디시전이 열린다.",
        "Make a pact with the knights who roam the plains. Unlocks the Nomadic Knight Contract decision."))
f("lightless_knights", "무광 기사단", "Elite Lightless Knights", pre=["nomadic_knights"], available=[FAME_AT_LEAST(40)],
  reward=[FAME(10)], desc=("이름을 숨긴 채 싸우는 기사들. (기사 명성 40 이상)", "Knights who fight without names. (Knight Fame 40+)"))
f("knight_artillery", "기사단 포병", "Knight Order Artillery", pre=["armoured_knights"])
f("knight_medics", "기사단 의무대", "Knight Order Medics", pre=["knight_artillery"])
f("truck_columns", "트럭 수송대", "Truck Transport Columns", pre=["knight_artillery"])
f("mechanised_lances", "기계화 창기병", "Mechanised Lancers", pre=["truck_columns"])
f("knight_tanks", "기사 전차", "Knight Tanks", pre=["mechanised_lances"])
f("heavy_knights", "중장 기사단", "Heavy Armour Knight Corps", pre=["knight_tanks"])
f("knight_staff", "기사 참모본부", "Knight General Staff", pre=["heavy_knights"])
f("air_knights", "하늘의 기사", "Knights of the Air", pre=["knight_staff"])
f("bomber_knights", "폭격 기사", "Bomber Knights", pre=["air_knights"])
f("kazimierz_lancers", "카시미어 창기병단", "Kazimierz Lancers", pre=["knight_staff"], theme=False,
  reward=["add_ideas = TU_KAZ_kazimierz_lancers", "army_experience = 50"])

# F. 국방과 용병
f("border_watch", "북부 국경 감시", "Northern Border Watch", pre=["root"])
f("ursus_threat", "우르수스의 위협", "Ursus Threat Assessment", pre=["border_watch"], theme=False,
  reward=["add_war_support = 0.05", EV(22, 5)])
f("border_forts", "국경 요새선", "Border Fortress Line", pre=["ursus_threat"])
f("trench_engineering", "참호 공학", "Trench Engineering", pre=["border_forts"])
f("merc_guild", "용병 길드 등록제", "Mercenary Guild Registry", pre=["ursus_threat"], theme=False,
  reward=[FLAG("mercs"), "add_manpower = 5000"],
  desc=("용병을 국가에 등록시킨다. '용병 고용' 디시전이 열린다.", "Register mercenaries with the state. Unlocks the Hire Mercenaries decision."))
f("merc_equipment", "용병 장비 규격", "Mercenary Equipment Standards", pre=["merc_guild"])
f("standing_army", "상비군 창설", "Found a Standing Army", pre=["merc_guild"], me=["merc_army"])
f("merc_army", "용병 의존", "Rely on Mercenary Regiments", pre=["merc_guild"], me=["standing_army"])
f("reserve_regiments", "예비군 연대", "Reserve Regiments", pre=[["standing_army", "merc_army"]])
f("border_scouts", "국경 정찰대", "Border Scouts", pre=["reserve_regiments"])
f("war_plan_ursus", "대우르수스 전쟁 계획", "Ursus War Plan", pre=["reserve_regiments"], theme=False,
  reward=[FLAG("ursus_plan"), "army_experience = 25"],
  desc=("우르수스에 대한 전쟁 명분 디시전이 열린다.", "Unlocks the decision to justify war on Ursus."))
f("northern_expedition", "북방 원정 준비", "Northern Expedition Preparations", pre=["war_plan_ursus"])
f("defenders", "카시미어의 수호자", "Defenders of Kazimierz", pre=["border_scouts", "border_forts"], theme=False,
  reward=["add_ideas = TU_KAZ_defenders"])

# G. 경제
f("corp_district", "기업 지구", "Corporate Industrial District", pre=["root"], econ=True)
f("rail_kaz", "카시미어 철도", "Kazimierz Rail Network", pre=["corp_district"], econ="TU_build_infrastructure = yes")
f("road_network", "도로망", "Road Network", pre=["rail_kaz"], econ="TU_build_infrastructure = yes")
f("steel_mills", "제철소", "Steel Mills", pre=["corp_district"], econ="TU_build_mil_factory = yes")
f("coal_mining", "탄광 개발", "Coal Mining", pre=["steel_mills"], econ=True)
f("consumer_goods", "소비재 산업", "Consumer Goods Industry", pre=["coal_mining"], me=["arms_industry"], econ=True)
f("arms_industry", "군수 산업", "Arms Industry", pre=["coal_mining"], me=["consumer_goods"], econ="TU_build_mil_factory = yes")
f("ad_industry", "광고 산업", "Advertising Industry", pre=[["consumer_goods", "arms_industry"]], econ=True,
  reward=[U("0.03")])
f("department_stores", "백화점", "Department Store Trade", pre=["ad_industry"], econ=True)
f("originium_grid", "원석 동력망", "Originium Power Grid", pre=["road_network"], econ="TU_build_infrastructure = yes")
f("industrial_labs", "공업 연구소", "Industrial Laboratories", pre=["originium_grid"])
f("research_parks", "연구 단지", "Research Parks", pre=["industrial_labs"], theme=False,
  reward=["add_research_slot = 1"], desc=("연구 슬롯 +1", "Research slot +1"))
f("mobile_city_refit", "이동 도시 개조", "Mobile City Refit", pre=["originium_grid"])
f("assembly_plants", "조립 공장", "Assembly Plants", pre=["department_stores"], econ="TU_build_mil_factory = yes")
f("transport_companies", "운송 회사", "Transport Companies", pre=["department_stores"])
f("trade_fairs", "국제 박람회", "International Trade Fairs", pre=["transport_companies"])
f("economic_miracle", "카시미어 경제 기적", "Kazimierz Economic Miracle", pre=["trade_fairs", "research_parks"],
  theme=False, reward=["add_ideas = TU_KAZ_economic_miracle", "TU_build_civ_factory = yes"], filt="FOCUS_FILTER_INDUSTRY")

# H. 외교
f("foreign_office", "외무국", "Foreign Office", pre=["root"])
f("leithanien_ties", "라이타니엔과의 교류", "Leithanien Exchange", pre=["foreign_office"], theme=False,
  reward=[FLAG("leithanien"), "add_political_power = 40"],
  desc=("'라이타니엔 아츠 교류' 디시전이 열린다.", "Unlocks the Leithanien Arts Exchange decision."))
f("siracusa_trade", "시라쿠사 교역", "Siracusa Trade Accord", pre=["foreign_office"])
f("victoria_trade", "빅토리아 교역", "Victoria Trade Accord", pre=["siracusa_trade"])
f("columbia_investment", "컬럼비아 투자 유치", "Columbian Investment Fund", pre=["victoria_trade"])
f("neutral_kaz", "중립 선언", "Declaration of Neutrality", pre=["leithanien_ties"], me=["anti_ursus"], theme=False,
  reward=["add_ideas = TU_KAZ_neutral"])
f("anti_ursus", "반우르수스 연대", "Anti-Ursus Coalition", pre=["leithanien_ties"], me=["neutral_kaz"], theme=False,
  reward=["add_ideas = TU_KAZ_anti_ursus", FLAG("league")],
  desc=("'카시미어 연맹 창설' 디시전이 열린다.", "Unlocks the Found the Kazimierz League decision."))
f("peace_network", "평화 조약망", "Peace Treaty Network", pre=["neutral_kaz"])

# 추가 중점 (각 갈래 보강)
f("merch_trade", "기사 굿즈 교역", "Knight Merchandise Trade", pre=["betting_industry"], reward=[FAME(5)])
f("rule_reform", "경기 규칙 개정", "Tournament Rule Reform", pre=["knight_scouting"], reward=[K("0.03")])
f("union_scholarships", "연합회 장학 연구", "Union Scholarship Research", pre=["stock_controls"])
f("corporate_police", "기업 경찰", "Corporate Police", pre=["security_companies"])
f("oath_ceremony", "기사 서약식", "Knightly Oath Ceremony", pre=["knight_houses"], reward=[K("0.03"), FAME(5)])
f("herald_office", "문장관 사무소", "Herald Office Records", pre=["chivalry_schools"])
f("oripathy_research", "광석병 치료 연구", "Oripathy Cure Research", pre=["infected_fund"])
f("infected_school", "감염자 기사 학교", "Infected Knight Academy", pre=["oripathy_research"])
f("cavalry_depots", "기병 보급소", "Cavalry Supply Depots", pre=["cavalry_officers"])
f("armoured_trains", "장갑 열차", "Armoured Trains", pre=["heavy_knights"])
f("anti_tank_defence", "대전차 방어선", "Anti-Tank Defence Line", pre=["trench_engineering"])
f("originium_refinery", "원석 정제소", "Originium Refinery", pre=["coal_mining"], econ=True)

# ------------------------------------------------------------------ 디시전
cat_major = C.category("major", "카시미어 메이저", "The Kazimierz Major",
                       ("해마다 열리는 기사 경기. 우승자에 따라 카시미어의 앞날이 흔들린다.",
                        "The annual knight tournament. Its champion can sway the future of Kazimierz."),
                       "GFX_decision_category_generic_political_actions", visible=[HAS("major_unlocked")])
C.d(cat_major, "host_major", "메이저 개최", "Host the Major",
    [FLAG("major_running"), EV(10)], cost=50, once=False, days_re_enable=365,
    visible=[HAS("major_unlocked")], available=["NOT = { %s }" % HAS("major_running")],
    desc=("올해의 카시미어 메이저를 연다. 개막, 준결승, 결승 이벤트가 이어진다.",
          "Open this year's Kazimierz Major. Opening, semi-final and final events follow."), icon="GFX_decision_generic_political_address")
C.d(cat_major, "sponsor_knight", "유망 기사 후원", "Sponsor a Promising Knight",
    [FAME(5), U("0.02")], cost=25, once=False, days_re_enable=90, visible=[HAS("major_unlocked")],
    desc=("기업 이름을 단 유망주를 후원한다.", "Sponsor a rising knight who wears a corporate name."))
C.d(cat_major, "broadcast_rights", "중계권 판매", "Sell Broadcast Rights",
    ["add_political_power = 60", U("0.05")], cost=0, once=False, days_re_enable=180, visible=[HAS("broadcast")],
    desc=("메이저 중계권을 기업에 판다.", "Sell the Major's broadcast rights to the corporations."), icon="GFX_decision_generic_fundraising")
C.d(cat_major, "crack_down_betting", "불법 도박 단속", "Crack Down on Illegal Betting",
    ["add_stability = 0.03", K("0.03")], cost=25, once=False, days_re_enable=180, visible=[HAS("major_unlocked")])
C.d(cat_major, "summon_champions", "챔피언 기사단 소집", "Summon the Champions",
    ["TU_KAZ_knight_template = yes",
     "capital_scope = { create_unit = { division = \"division_template = \\\"TU_KAZ_knights\\\" start_experience_factor = 0.6 start_equipment_factor = 1\" owner = KAZ count = 2 } }"],
    cost=75, once=False, days_re_enable=365, visible=[HAS("champions")], available=[FAME_AT_LEAST(50)],
    desc=("메이저 우승자들로 정예 기사 사단 2개를 꾸린다. (기사 명성 50 이상)",
          "Raise two elite knight divisions from Major champions. (Knight Fame 50+)"), icon="GFX_decision_generic_military")

cat_contract = C.category("contracts", "기사 계약", "Knight Contracts",
                          ("기사와 용병은 계약으로 움직인다.", "Knights and mercenaries move by contract."),
                          "GFX_decision_category_military_operation",
                          visible=["OR = {", "\t" + HAS("corp_knights"), "\t" + HAS("nomads"), "\t" + HAS("mercs"), "}"])
C.effects.append("""TU_KAZ_knight_template = {
	if = {
		limit = { NOT = { has_country_flag = TU_KAZ_knight_template_done } }
		set_country_flag = TU_KAZ_knight_template_done
		division_template = {
			name = "TU_KAZ_knights"
			is_locked = no
			priority = 2
			regiments = {
				cavalry = { x = 0 y = 0 }
				cavalry = { x = 0 y = 1 }
				cavalry = { x = 1 y = 0 }
				cavalry = { x = 1 y = 1 }
				infantry = { x = 2 y = 0 }
			}
		}
	}
}""")
UNIT = "capital_scope = { create_unit = { division = \"division_template = \\\"TU_KAZ_knights\\\" start_experience_factor = %s start_equipment_factor = 0.8\" owner = KAZ count = %d } }"
C.d(cat_contract, "hire_nomads", "유목 기사단 계약", "Nomadic Knight Contract",
    ["TU_KAZ_knight_template = yes", UNIT % ("0.4", 2), FAME(5)], cost=50, once=False, days_re_enable=180,
    visible=[HAS("nomads")], available=[FAME_AT_LEAST(20)],
    desc=("평원의 유목 기사 사단 2개와 계약한다. (기사 명성 20 이상)", "Contract two divisions of plains nomad knights. (Knight Fame 20+)"),
    icon="GFX_decision_generic_military")
C.d(cat_contract, "hire_corp_knights", "기업 기사 계약", "Corporate Knight Contract",
    ["TU_KAZ_knight_template = yes", UNIT % ("0.3", 3), U("0.05")], cost=75, once=False, days_re_enable=180,
    visible=[HAS("corp_knights")],
    desc=("기업 소속 기사 사단 3개를 빌린다. 연합회의 힘이 커진다.", "Lease three corporate knight divisions. The Union grows stronger."),
    icon="GFX_decision_generic_military")
C.d(cat_contract, "hire_mercs", "용병 고용", "Hire Mercenaries",
    ["add_manpower = 15000", "army_experience = 10"], cost=50, once=False, days_re_enable=120, visible=[HAS("mercs")],
    desc=("등록 용병을 정규군에 편입한다.", "Bring registered mercenaries into the army."))
C.d(cat_contract, "lease_knights", "기사 해외 파견", "Lease Knights Abroad",
    ["add_political_power = 75", "add_manpower = -5000", FAME(5)], cost=0, once=False, days_re_enable=180,
    visible=["OR = {", "\t" + HAS("corp_knights"), "\t" + HAS("nomads"), "}"],
    desc=("기사들을 외국의 경호·전쟁에 빌려주고 대가를 받는다.", "Lend knights to foreign wars and escorts for payment."))
C.d(cat_contract, "merc_arsenal", "용병 무기 조달", "Mercenary Arms Procurement",
    ["add_equipment_to_stockpile = { type = infantry_equipment amount = 1000 }"], cost=50, once=False,
    days_re_enable=180, visible=[HAS("mercs")])

cat_pol = C.category("politics", "연합회와 기사", "Union and Knights",
                     ("상업 연합회와 기사 사이에서 저울을 움직인다.", "Tip the scales between the Commercial Union and the knights."))
C.d(cat_pol, "union_lobby", "연합회 로비 수용", "Accept Union Lobbying",
    [U("0.1"), "add_political_power = 25"], cost=25, once=False, days_re_enable=120)
C.d(cat_pol, "knight_rally", "기사 집회 지원", "Support a Knights' Rally",
    [K("0.1"), FAME(5)], cost=50, once=False, days_re_enable=120)
C.d(cat_pol, "corporate_tax", "기업 감세 거래", "Corporate Tax Deal",
    ["add_political_power = 100", U("0.08"), "add_stability = -0.03"], cost=0, once=False, days_re_enable=240)
C.d(cat_pol, "knight_tribunal", "기사 재판 개정", "Convene a Knight Tribunal",
    ["add_stability = 0.05", K("0.05")], cost=50, once=False, days_re_enable=240)
C.d(cat_pol, "infected_campaign", "감염자 기사 캠페인", "Infected Knights Campaign",
    [FAME(10), "add_stability = -0.03"], cost=50, once=False, days_re_enable=180, visible=[HAS("infected_entry")])
C.d(cat_pol, "oripathy_relief", "광석병 구호", "Oripathy Relief",
    ["add_stability = 0.04", "add_manpower = 5000"], cost=50, once=False, days_re_enable=180,
    visible=["has_completed_focus = TU_KAZ_infected_question"])

cat_for = C.category("foreign", "카시미어 외교", "Kazimierz Foreign Affairs",
                     icon="GFX_decision_category_generic_foreign_policy",
                     visible=["OR = {", "\t" + HAS("ursus_plan"), "\t" + HAS("league"), "\t" + HAS("leithanien"), "}"])
C.d(cat_for, "justify_ursus", "우르수스 전쟁 명분", "Justify War on Ursus",
    ["create_wargoal = { type = take_state_focus target = URS }"], cost=75,
    visible=[HAS("ursus_plan"), "country_exists = URS"], available=["NOT = { has_war_with = URS }", "has_war_support > 0.3"],
    desc=("우르수스에 대한 전쟁 목표를 얻는다. (전쟁 지지 30% 이상)", "Gain a war goal against Ursus. (War support 30%+)"),
    icon="GFX_decision_generic_military")
C.d(cat_for, "found_league", "카시미어 연맹 창설", "Found the Kazimierz League",
    ["create_faction = TU_KAZ_league"], cost=50, visible=[HAS("league")], available=["is_in_faction = no"],
    icon="GFX_decision_generic_political_discourse")
C.loc("TU_KAZ_league", "카시미어 연맹", "Kazimierz League")
C.d(cat_for, "invite_league", "연맹 초청", "Invite to the League",
    ["add_to_faction = FROM"], cost=50, once=False, days_re_enable=90, visible=[HAS("league"), "is_faction_leader = yes"],
    target=["NOT = { tag = ROOT }", "is_in_faction = no", "NOT = { has_war_with = ROOT }",
            "OR = { tag = LEI tag = SIR tag = LAT tag = VIC tag = COL }"],
    desc=("라이타니엔·시라쿠사·라테라노·빅토리아·컬럼비아 중 한 나라를 연맹에 들인다.",
          "Bring Leithanien, Siracusa, Laterano, Victoria or Columbia into the League."))
C.d(cat_for, "leithanien_exchange", "라이타니엔 아츠 교류", "Leithanien Arts Exchange",
    ["add_tech_bonus = { name = TU_KAZ_leithanien_exchange bonus = 0.5 uses = 2 category = electronics category = industry }"],
    cost=50, visible=[HAS("leithanien"), "country_exists = LEI"], available=["NOT = { has_war_with = LEI }"])

# ------------------------------------------------------------------ 이벤트
C.ev(1, ("카시미어의 아침", "Morning in Kazimierz"),
     ("수도의 대형 전광판에는 기사 경기 광고와 새 음료 광고가 번갈아 뜬다. 옛 기사단의 문장은 기념품 가게에서 팔린다. 그래도 아직 맹세를 기억하는 기사들이 있다.",
      "The giant screens of the capital alternate between tournament ads and soft drink ads. Old order crests are sold in souvenir shops. Yet some knights still remember their oaths."),
     [("연합회가 이 나라를 굴린다.", "The Union keeps this country running.", [U("0.05")], 50),
      ("기사도는 아직 죽지 않았다.", "Knighthood is not dead yet.", [K("0.05")], 50)])
C.ev(10, ("메이저 개막", "The Major Opens"),
     ("대경기장이 관중으로 가득 찼다. 기업 로고를 단 기사와 낡은 갑옷의 기사가 같은 대진표에 올랐다. 이번 대회를 어떻게 꾸릴 것인가?",
      "The grand arena is packed. Knights wearing corporate logos and knights in worn armour share the same bracket. How shall this Major be run?"),
     [("후원 기업을 앞세운다.", "Put the sponsors front and centre.", [U("0.05"), "add_political_power = 40", EV(11, 20)], 50),
      ("기사의 명예를 앞세운다.", "Put the knights' honour first.", [K("0.05"), FAME(5), EV(11, 20)], 50)],
     picture="GFX_report_event_generic_rally")
C.ev(11, ("준결승의 파란", "Upset at the Semi-Finals"),
     ("준결승을 앞두고 문제가 터졌다. 한 우승 후보가 감염자라는 사실이 알려졌고, 다른 경기에는 승부 조작 의혹이 붙었다.",
      "Trouble erupts before the semi-finals. One favourite turns out to be infected, and another match is accused of being fixed."),
     [("감염자 기사의 출전을 허용한다.", "Let the infected knight compete.", [FAME(5), "add_stability = -0.02", FLAG("infected_entry_this_year"), EV(12, 10)], 30),
      ("규정대로 실격시킨다.", "Disqualify by the rules.", [U("0.03"), "add_stability = 0.02", EV(12, 10)], 40),
      ("승부 조작부터 파헤친다.", "Investigate the fixing first.", ["add_political_power = -25", K("0.05"), EV(12, 10)], 30)],
     picture="GFX_report_event_generic_rally")
C.ev(12, ("메이저 결승", "The Major Final"),
     ("결승이 끝났다. 수십만 관중이 새 챔피언의 이름을 외친다.",
      "The final is over. Hundreds of thousands chant the new champion's name."),
     [("기업 소속 기사가 우승했다.", "A corporate knight won.",
       ["trigger = { %s }" % HAS("winner_corp"), U("0.05"), "add_political_power = 50", FAME(5)], 1),
      ("떠돌이 기사가 우승했다.", "A wandering knight won.",
       ["trigger = { %s }" % HAS("winner_knight"), K("0.05"), FAME(10), "army_experience = 20"], 1),
      ("명문 기사 가문이 우승했다.", "A great knightly house won.",
       ["trigger = { %s }" % HAS("winner_noble"), K("0.08"), "add_war_support = 0.05", FAME(5)], 1),
      ("감염자 기사가 우승했다!", "An infected knight won!",
       ["trigger = { %s }" % HAS("winner_infected"), FLAG("infected_champion"), FAME(15), "add_stability = -0.03"], 1)],
     picture="GFX_report_event_generic_rally",
     immediate=["random_list = {",
                "\t35 = { %s }" % FLAG("winner_corp"),
                "\t30 = { %s }" % FLAG("winner_knight"),
                "\t20 = { %s }" % FLAG("winner_noble"),
                "\t15 = {",
                "\t\tmodifier = { factor = 0 NOT = { %s } NOT = { %s } }" % (HAS("infected_entry"), HAS("infected_entry_this_year")),
                "\t\t%s" % FLAG("winner_infected"),
                "\t}",
                "}",
                "if = { limit = { %s } %s }" % (HAS("major_annual"), FAME(5)),
                "clr_country_flag = TU_KAZ_major_running",
                "clr_country_flag = TU_KAZ_infected_entry_this_year",
                "hidden_effect = { country_event = { id = tu_kaz_ev.13 days = 1 } }"])
C.ev(13, ("메이저 이후", "After the Major"),
     ("축제가 끝나고 경기장의 조명이 꺼졌다. 다음 메이저는 일 년 뒤다.", "The festival ends and the arena lights go dark. The next Major is a year away."),
     [("내년을 기약한다.", "Until next year.", ["clr_country_flag = TU_KAZ_winner_corp", "clr_country_flag = TU_KAZ_winner_knight",
                                               "clr_country_flag = TU_KAZ_winner_noble", "clr_country_flag = TU_KAZ_winner_infected"], 1)])
C.ev(20, ("감염자 기사들의 시위", "The Infected Knights Protest"),
     ("감염자 기사들이 경기장 앞에 모였다. 그들은 '우리도 기사다'라고 적힌 깃발을 들었다.",
      "Infected knights gather before the arena, carrying banners that read 'We are knights too'."),
     [("그들의 목소리를 듣는다.", "Hear their voices.", [FAME(5), "add_stability = -0.02"], 50),
      ("해산시킨다.", "Disperse them.", ["add_stability = 0.02", U("0.03")], 50)])
C.ev(21, ("니어 가문의 청원", "Petition of the Nearl Family"),
     ("옛 기사 가문 니어의 기사가 의회에 청원서를 냈다. 감염 여부와 상관없이 기사의 자격을 인정해 달라는 내용이다.",
      "A knight of the old Nearl family petitions parliament: recognise a knight's worth regardless of infection."),
     [("청원을 받아들인다.", "Accept the petition.", [FAME(10), K("0.05")], 50),
      ("의회에서 계속 논의한다.", "Leave it to further debate.", ["add_political_power = 30"], 50)])
C.ev(22, ("북부 국경 사건", "Northern Border Incident"),
     ("우르수스 정찰대가 국경을 넘어왔다가 카시미어 기사와 충돌했다. 사상자가 났다.",
      "An Ursus patrol crossed the border and clashed with Kazimierz knights. There were casualties."),
     [("강하게 항의하고 경계를 높인다.", "Protest loudly and raise the alert.", ["add_war_support = 0.05", "army_experience = 10"], 60),
      ("조용히 덮는다.", "Hush it up.", ["add_stability = 0.02"], 40)],
     picture="GFX_report_event_generic_battle")
C.ev(23, ("조작된 뉴스", "Manufactured News"),
     ("연합회 소유 방송사들이 같은 날 같은 문장으로 정부를 칭찬하는 기사를 냈다. 시민들이 눈치채기 시작했다.",
      "Union-owned networks praised the government in identical words on the same day. Citizens are starting to notice."),
     [("문제없다.", "No problem here.", [U("0.03"), "add_stability = -0.02"], 50),
      ("방송사에 경고한다.", "Warn the networks.", [K("0.03"), "add_political_power = -20"], 50)])
C.ev(24, ("결투 끝의 죽음", "Death After a Duel"),
     ("명예 결투에서 젊은 기사가 목숨을 잃었다. 결투를 다시 금지하라는 여론이 일어났다.",
      "A young knight died in an honour duel. There are calls to ban duels again."),
     [("결투는 기사의 권리다.", "Duelling is a knight's right.", [FAME(5), "add_stability = -0.03"], 50),
      ("규칙을 엄격히 한다.", "Tighten the rules.", ["add_stability = 0.02"], 50)])
C.ev(25, ("기업 기사 스캔들", "Corporate Knight Scandal"),
     ("인기 기업 기사가 약물을 썼다는 폭로가 나왔다. 후원 기업은 모르는 일이라고 한다.",
      "A popular corporate knight is exposed for doping. The sponsor claims it knew nothing."),
     [("기업을 처벌한다.", "Punish the corporation.", [K("0.05"), "add_political_power = -25"], 50),
      ("기사 개인의 일탈로 처리한다.", "Call it one knight's misconduct.", [U("0.05"), "add_stability = -0.02"], 50)],
     trigger=["original_tag = KAZ", HAS("major_unlocked")], mtth=240)
C.ev(26, ("유목 기사단의 방문", "The Nomadic Knights Arrive"),
     ("평원을 떠도는 유목 기사단이 수도 근처에 천막을 쳤다. 그들은 일거리를 찾고 있다.",
      "A band of nomadic knights pitches tents near the capital. They are looking for work."),
     [("고용한다.", "Hire them.", ["add_manpower = 5000", FAME(5), "add_political_power = -25"], 50),
      ("떠나보낸다.", "Send them on.", ["add_political_power = 15"], 50)],
     trigger=["original_tag = KAZ", "has_completed_focus = TU_KAZ_knight_academy"], mtth=300)
C.ev(27, ("무광 기사의 귀환", "Return of a Lightless Knight"),
     ("이름 없는 기사가 메이저 예선에 나타나 모든 상대를 쓰러뜨리고 사라졌다. 그가 누구인지 아는 사람은 없다.",
      "A nameless knight appeared at the Major qualifiers, defeated every opponent and vanished. No one knows who it was."),
     [("전설이 돌아왔다.", "A legend returns.", [FAME(10), "add_war_support = 0.03"], 1)],
     trigger=["original_tag = KAZ", FAME_AT_LEAST(30)], mtth=360)
C.ev(28, ("주주의 나라", "The Shareholder State"),
     ("의회는 이제 주주총회처럼 열린다. 카시미어는 효율적인 나라가 되었다. 기사들은 계약서를 읽는다.",
      "Parliament now meets like a shareholders' meeting. Kazimierz has become efficient. The knights read their contracts."),
     [("이익이 곧 국익이다.", "Profit is the national interest.", ["add_political_power = 50"], 1)])
C.ev(29, ("기사의 나라", "Kingdom of Knights"),
     ("광고판이 내려가고 옛 기사단의 깃발이 다시 걸렸다. 기사들은 다시 맹세한다.",
      "The billboards come down and the old orders' banners rise again. The knights swear anew."),
     [("맹세를 지킨다.", "We keep our oaths.", [FAME(10)], 1)])
C.ev(30, ("모두를 위한 기사도", "Knighthood for All"),
     ("감염자 기사가 갑옷을 입고 수도를 행진했다. 시민들이 길을 비켜 경례했다.",
      "Infected knights marched through the capital in armour. Citizens stepped aside and saluted."),
     [("기사도는 마음에 있다.", "Knighthood lies in the heart.", ["add_stability = 0.05", FAME(10)], 1)])

if __name__ == "__main__":
    C.write()
