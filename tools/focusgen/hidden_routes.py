#!/usr/bin/env python3
"""숨은 루트 8개 (사양서 30). 이벤트(또는 기존 깃발)로 열리는 숨은 갈래 + 결말.

사용법:  python -I tools/focusgen/hidden_routes.py   (그다음 merge_focus --tag … 와 chargen 의 build_characters)

만드는 파일
    tools/focusgen/<tag>/p9_hidden.txt          숨은 갈래 (allow_branch = 루트 깃발). content_lib 는 p9_ 조각을 지우지 않는다.
    events/tu_hidden_events.txt                 루트를 여는 이벤트 (네임스페이스 tu_hidden)
    common/ideas/tu_hidden_ideas.txt            루트 국민정신 (중간 · 최종)
    localisation/{korean,english}/tu_hidden_l_*.yml
결말의 국호 · 나라 색 · 지도자 · 다른 결말과의 양자택일은 tools/chargen/data.py 의 hooks / COSMETIC_COLORS 가 넣는다.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[1] / "terra_universalis"

# 루트: tag, flag(접미사), event(없으면 None), ideas, focuses, root(첫 중점의 선행)
# focus: (id 접미사, 한국어, 영어, [선행 접미사], 비용, [보상], (설명 ko, en))
ROUTES = [
    dict(tag="URS", key="serpent", root=None,
         event=dict(n=1, title=("검은 뱀", "The Black Serpent"),
                    desc=("체르노보그가 불탄 뒤, 궁정의 그림자 속에서 오래된 무언가가 눈을 떴다. 황제의 목소리가 낯설어졌다.",
                          "After Chernobog burned, something ancient woke in the shadows of the court. The Emperor's voice has become strange."),
                    trigger=["original_tag = URS", "has_global_flag = TU_chernobog_incident_started", "country_exists = REU"],
                    mtth=120, ai=20,
                    accept=("그림자에 몸을 맡긴다", "Yield to the shadow"),
                    decline=("황제는 황제다", "The Emperor is the Emperor"),
                    effects=["recruit_character = TU_URS_kashchey",
                             "promote_character = {\n\tcharacter = TU_URS_kashchey\n\tideology = despotism\n}",
                             "add_ideas = TU_URS_serpent_shadow"]),
         ideas=[("serpent_shadow", "검은 뱀의 그림자", "Shadow of the Black Serpent",
                 {"army_attack_factor": 0.10, "war_support_factor": 0.10, "political_power_factor": 0.10, "stability_factor": -0.10}),
                ("serpent_empire", "검은 뱀의 제국", "Empire of the Black Serpent",
                 {"army_attack_factor": 0.25, "army_org_factor": 0.20, "conscription_factor": 0.15, "war_support_factor": 0.30,
                  "political_power_factor": 0.20, "production_factory_max_efficiency_factor": 0.10, "stability_factor": -0.05})],
         focuses=[
             ("serpent_whispers", "궁정의 속삭임", "Whispers in the Court", [], 5, ["add_political_power = 75"],
              ("황제의 칙령에 낯선 문장이 섞이기 시작했다.", "Strange phrases begin to appear in the Emperor's edicts.")),
             ("serpent_purge", "옛 신하의 숙청", "Purge the Old Ministers", ["serpent_whispers"], 10, ["add_stability = 0.05", "add_political_power = 50"], None),
             ("serpent_guard", "검은 근위대", "The Black Guard", ["serpent_whispers"], 10, ["army_experience = 40", "add_manpower = 20000"], None),
             ("serpent_infected_army", "감염자 징집", "Conscript the Infected", ["serpent_guard"], 10, ["add_manpower = 50000", "add_stability = -0.05"], None),
             ("serpent_arts", "고대의 아츠", "Ancient Arts", ["serpent_purge"], 10,
              ["add_tech_bonus = { name = TU_URS_serpent_arts bonus = 1.0 uses = 2 category = tu_originium_tech category = infantry_weapons }"], None),
             ("serpent_war_machine", "전쟁 기계", "The War Machine", ["serpent_infected_army", "serpent_arts"], 10,
              ["TU_build_mil_factory = yes", "TU_build_mil_factory = yes", "TU_build_mil_factory = yes"], None),
             ("serpent_crush", "봉기를 짓밟다", "Crush the Uprising", ["serpent_war_machine"], 10,
              ["if = {\n\tlimit = { country_exists = REU }\n\tcreate_wargoal = { type = annex_everything target = REU }\n}", "army_experience = 50"], None),
             ("serpent_finale", "검은 뱀의 제국", "Empire of the Black Serpent", ["serpent_crush"], 20,
              ["swap_ideas = { remove_idea = TU_URS_serpent_shadow add_idea = TU_URS_serpent_empire }", "add_political_power = 200"],
              ("황제의 이름은 남았지만, 제국을 움직이는 것은 검은 뱀이다. (국호·색 변경)",
               "The Emperor's name remains, but it is the Black Serpent that moves the empire. (Name and colour change)")),
         ]),
    dict(tag="REU", key="patriot", root="TU_REU_uprising",
         event=dict(n=2, title=("늙은 병사의 결단", "The Old Soldier's Decision"),
                    desc=("탈룰라의 명령은 점점 잔혹해졌다. 패트리어트는 오랫동안 침묵했지만, 오늘은 창을 들고 그녀 앞에 섰다.",
                          "Talulah's orders grew ever crueller. The Patriot was silent for a long time, but today he stands before her, spear in hand."),
                    trigger=["original_tag = REU", "has_global_flag = TU_chernobog_incident_started"], mtth=150, ai=30,
                    accept=("늙은 병사를 따른다", "Follow the old soldier"), decline=("탈룰라를 따른다", "Follow Talulah"),
                    effects=["recruit_character = TU_REU_patriot_leader",
                             "promote_character = {\n\tcharacter = TU_REU_patriot_leader\n\tideology = marxism\n}",
                             "add_ideas = TU_REU_patriot_oath"]),
         ideas=[("patriot_oath", "늙은 병사의 맹세", "The Old Soldier's Oath",
                 {"army_defence_factor": 0.10, "army_org_factor": 0.10, "stability_factor": 0.05}),
                ("infected_republic", "감염자 공화국", "Republic of the Infected",
                 {"army_defence_factor": 0.20, "army_attack_factor": 0.15, "army_org_factor": 0.20, "stability_factor": 0.15,
                  "conscription_factor": 0.15, "monthly_population": 0.20, "war_support_factor": 0.20})],
         focuses=[
             ("patriot_spear", "늙은 창", "The Old Spear", [], 5, ["add_stability = 0.05", "army_experience = 25"],
              ("싸움은 복수가 아니라 살아남기 위한 것이어야 한다.", "The fight must be for survival, not revenge.")),
             ("patriot_discipline", "군율 회복", "Restore Discipline", ["patriot_spear"], 10, ["add_stability = 0.05", "add_war_support = 0.05"], None),
             ("patriot_shield_guard", "방패 근위대", "Shield Guard Battalions", ["patriot_spear"], 10, ["army_experience = 30", "add_manpower = 15000"], None),
             ("patriot_refuge", "피난민 보호", "Protect the Refugees", ["patriot_discipline"], 10, ["add_manpower = 20000", "add_stability = 0.05"], None),
             ("patriot_north", "북방 해방", "Liberate the North", ["patriot_shield_guard"], 10,
              ["if = {\n\tlimit = { country_exists = URS }\n\tcreate_wargoal = { type = annex_everything target = URS }\n}"], None),
             ("patriot_councils", "감염자 평의회", "Councils of the Infected", ["patriot_refuge"], 10, ["add_political_power = 100"], None),
             ("patriot_charter", "공화국 헌장", "Republican Charter", ["patriot_councils", "patriot_north"], 15, ["add_stability = 0.10"], None),
             ("patriot_finale", "감염자 공화국", "Republic of the Infected", ["patriot_charter"], 20,
              ["swap_ideas = { remove_idea = TU_REU_patriot_oath add_idea = TU_REU_infected_republic }", "add_political_power = 150"],
              ("감염자도 시민인 나라. 늙은 병사가 마지막으로 지킨 꿈. (국호·색 변경)",
               "A nation where the infected are citizens. The last dream the old soldier defended. (Name and colour change)")),
         ]),
    dict(tag="KZD", key="babel", root="TU_KZD_military_commission_focus",
         event=dict(n=3, title=("바벨의 유산", "The Legacy of Babel"),
                    desc=("로도스 아일랜드에서 온 편지에는 오래전 바벨의 문장이 찍혀 있었다. 왕관 없이 살카즈를 하나로 묶을 길이 있다고.",
                          "A letter from Rhodes Island bears the old seal of Babel. There may be a way to unite the Sarkaz without a crown."),
                    trigger=["original_tag = KZD", "country_exists = RHO", "NOT = { has_completed_focus = TU_KZD_theresis_throne }",
                             "date > 1098.1.1"], mtth=200, ai=20,
                    accept=("바벨의 길을 걷는다", "Walk the path of Babel"), decline=("살카즈에게는 왕이 필요하다", "The Sarkaz need a king"),
                    effects=["recruit_character = TU_KZD_babel_assembly",
                             "promote_character = {\n\tcharacter = TU_KZD_babel_assembly\n\tideology = oligarchism\n}",
                             "add_ideas = TU_KZD_babel_hope"]),
         ideas=[("babel_hope", "바벨의 희망", "Hope of Babel", {"stability_factor": 0.10, "research_speed_factor": 0.05}),
                ("new_babel", "새 바벨", "New Babel",
                 {"stability_factor": 0.20, "research_speed_factor": 0.15, "political_power_factor": 0.20, "army_org_factor": 0.15,
                  "army_defence_factor": 0.15, "monthly_population": 0.15, "production_factory_max_efficiency_factor": 0.10})],
         focuses=[
             ("babel_letter", "바벨의 편지", "Letter from Babel", [], 5, ["add_political_power = 75"], None),
             ("babel_no_crown", "왕관을 거부하다", "Refuse the Crown", ["babel_letter"], 10, ["add_stability = 0.10"], None),
             ("babel_rhodes", "로도스 아일랜드와의 동맹", "Alliance with Rhodes Island", ["babel_letter"], 10,
              ["if = {\n\tlimit = { country_exists = RHO }\n\tRHO = { add_opinion_modifier = { target = ROOT modifier = TU_hidden_friendship } }\n}",
               "add_political_power = 50"], None),
             ("babel_clinics", "광석병 진료소", "Oripathy Clinics", ["babel_rhodes"], 10, ["add_stability = 0.05", "add_manpower = 15000"], None),
             ("babel_scholars", "살카즈 학자들", "Sarkaz Scholars", ["babel_no_crown"], 10,
              ["add_tech_bonus = { name = TU_KZD_babel_scholars bonus = 1.0 uses = 2 category = tu_originium_tech category = electronics }"], None),
             ("babel_peace", "부족 간 화해", "Peace Between the Tribes", ["babel_no_crown"], 10, ["add_stability = 0.05", "add_war_support = 0.05"], None),
             ("babel_homeland", "살카즈의 고향", "A Homeland for the Sarkaz", ["babel_clinics", "babel_scholars", "babel_peace"], 15,
              ["TU_build_civ_factory = yes", "TU_build_civ_factory = yes"], None),
             ("babel_finale", "새 바벨", "New Babel", ["babel_homeland"], 20,
              ["swap_ideas = { remove_idea = TU_KZD_babel_hope add_idea = TU_KZD_new_babel }", "add_political_power = 150"],
              ("테레사가 꿈꾸었던 바벨이 다시 선다. 왕관 없는 살카즈의 나라. (국호·색 변경)",
               "The Babel Theresa dreamed of stands again: a Sarkaz nation without a crown. (Name and colour change)")),
         ]),
    dict(tag="SAM", key="forest", root="TU_SAM_root",
         event=dict(n=4, title=("숲이 깨어날 때", "When the Forest Wakes"),
                    desc=("나무들이 밤새 움직였다. 아침이 되자 마을과 마을 사이의 길이 사라져 있었다. 숲이 무언가를 원한다.",
                          "The trees moved during the night. By morning the paths between villages were gone. The forest wants something."),
                    trigger=["original_tag = SAM", "OR = {\n\tcheck_variable = { TU_SAM_grace < 15 }\n\tcheck_variable = { TU_SAM_pacts > 1 }\n}"],
                    mtth=60, ai=30,
                    accept=("숲의 뜻에 따른다", "Follow the will of the forest"), decline=("사람의 길을 지킨다", "Keep to the ways of people"),
                    effects=["recruit_character = TU_SAM_forest_will",
                             "promote_character = {\n\tcharacter = TU_SAM_forest_will\n\tideology = despotism\n}",
                             "add_ideas = TU_SAM_waking_forest"]),
         ideas=[("waking_forest", "깨어나는 숲", "The Waking Forest", {"army_defence_factor": 0.15, "attrition": -0.10, "stability_factor": -0.05}),
                ("living_forest", "살아 있는 숲", "The Living Forest",
                 {"army_defence_factor": 0.30, "army_attack_factor": 0.15, "army_org_factor": 0.20, "attrition": -0.30,
                  "stability_factor": 0.15, "war_support_factor": 0.20, "monthly_population": 0.15, "conscription_factor": 0.10})],
         focuses=[
             ("forest_roots", "뿌리의 목소리", "Voice of the Roots", [], 5, ["add_stability = 0.05"], None),
             ("forest_paths", "사라진 길", "The Vanished Paths", ["forest_roots"], 10, ["army_experience = 30"], None),
             ("forest_spirits", "정령들의 회합", "Gathering of the Spirits", ["forest_roots"], 10, ["add_political_power = 75"], None),
             ("forest_walls", "가시나무 장벽", "Thornwood Walls", ["forest_paths"], 10, ["TU_build_forts_2 = yes"], None),
             ("forest_hunters", "숲의 사냥꾼", "Hunters of the Forest", ["forest_paths"], 10, ["add_manpower = 15000", "army_experience = 25"], None),
             ("forest_tree_arts", "나무의 아츠", "Arts of the Trees", ["forest_spirits"], 10,
              ["add_tech_bonus = { name = TU_SAM_forest_tree_arts bonus = 1.0 uses = 2 category = tu_originium_tech category = tu_oripathy_tech }"], None),
             ("forest_spread", "숲의 확장", "The Forest Spreads", ["forest_walls", "forest_hunters", "forest_tree_arts"], 15,
              ["every_neighbor_country = {\n\tlimit = { NOT = { is_in_faction_with = ROOT } }\n\tcapital_scope = { add_claim_by = ROOT }\n}", "add_war_support = 0.10"], None),
             ("forest_finale", "살아 있는 숲", "The Living Forest", ["forest_spread"], 20,
              ["swap_ideas = { remove_idea = TU_SAM_waking_forest add_idea = TU_SAM_living_forest }", "add_political_power = 150"],
              ("사미는 더 이상 숲속의 나라가 아니다. 숲 그 자체다. (국호·색 변경)",
               "Sami is no longer a nation in the forest. It is the forest. (Name and colour change)")),
         ]),
    dict(tag="COL", key="rhine", root="TU_COL_root",
         event=dict(n=5, title=("라인 생명의 제안", "Rhine Lab's Proposal"),
                    desc=("라인 생명 이사회가 대통령에게 보고서를 올렸다. 국가 운영 전체를 연구소의 방식으로 바꾸자는 내용이었다.",
                          "The Rhine Lab board sent the President a report: run the whole nation the way the laboratory is run."),
                    trigger=["original_tag = COL", "check_variable = { TU_COL_science > 179 }"], mtth=60, ai=30,
                    accept=("제안을 받아들인다", "Accept the proposal"), decline=("연구소는 연구소일 뿐이다", "A laboratory is only a laboratory"),
                    effects=["recruit_character = TU_COL_kristen",
                             "promote_character = {\n\tcharacter = TU_COL_kristen\n\tideology = oligarchism\n}",
                             "add_ideas = TU_COL_rhine_directorate"]),
         ideas=[("rhine_directorate", "라인 생명 이사회", "Rhine Lab Directorate", {"research_speed_factor": 0.10, "stability_factor": -0.05}),
                ("rhine_republic", "라인 공화국", "The Rhine Republic",
                 {"research_speed_factor": 0.25, "production_factory_max_efficiency_factor": 0.15, "industrial_capacity_factory": 0.15,
                  "army_attack_factor": 0.10, "air_attack_factor": 0.15, "political_power_factor": 0.15, "stability_factor": 0.05})],
         focuses=[
             ("rhine_directive", "연구 지침", "Research Directive", [], 5, ["add_political_power = 50"], None),
             ("rhine_departments", "부서별 국가 운영", "Government by Departments", ["rhine_directive"], 10, ["add_stability = 0.05"], None),
             ("rhine_defense_dept", "방위과 확대", "Expand the Defence Department", ["rhine_directive"], 10, ["army_experience = 30"], None),
             ("rhine_ecology", "생태과의 실험", "Ecology Department Experiments", ["rhine_departments"], 10,
              ["add_tech_bonus = { name = TU_COL_rhine_ecology bonus = 1.0 uses = 2 category = tu_oripathy_tech category = industry }"], None),
             ("rhine_engineering", "공학과 프로젝트", "Engineering Department Projects", ["rhine_defense_dept"], 10,
              ["TU_build_civ_factory = yes", "TU_build_mil_factory = yes"], None),
             ("rhine_ferns", "페르난도 계획", "Project Fernando", ["rhine_engineering"], 10,
              ["add_tech_bonus = { name = TU_COL_rhine_ferns bonus = 1.0 uses = 2 category = armor category = air_equipment }"], None),
             ("rhine_total_research", "총력 연구 체제", "Total Research State", ["rhine_ecology", "rhine_ferns"], 15, ["add_research_slot = 1"], None),
             ("rhine_finale", "라인 공화국", "The Rhine Republic", ["rhine_total_research"], 20,
              ["swap_ideas = { remove_idea = TU_COL_rhine_directorate add_idea = TU_COL_rhine_republic }", "add_political_power = 150"],
              ("컬럼비아는 하나의 거대한 연구소가 된다. (국호·색 변경)", "Columbia becomes one vast laboratory. (Name and colour change)")),
         ]),
    dict(tag="KJE", key="frozen", root="TU_KJE_root",
         event=dict(n=6, title=("설산의 침묵", "Silence of the Snow Mountains"),
                    desc=("세 가문의 다툼은 끝나지 않았고, 장로들은 결국 산문을 닫기로 했다. 바깥 세상은 잊혀질 것이다.",
                          "The quarrel of the three houses never ended, and the elders have decided to close the mountain gates. The outside world will be forgotten."),
                    trigger=["original_tag = KJE", "check_variable = { TU_KJE_modern < 15 }", "date > 1098.1.1"], mtth=120, ai=30,
                    accept=("산문을 닫는다", "Close the gates"), decline=("세상과 이어져 있어야 한다", "We must stay connected to the world"),
                    effects=["add_ideas = TU_KJE_closed_gates"]),
         ideas=[("closed_gates", "닫힌 산문", "Closed Mountain Gates", {"army_defence_factor": 0.15, "stability_factor": 0.10, "consumer_goods_factor": 0.03}),
                ("frozen_kingdom", "얼어붙은 왕국", "The Frozen Kingdom",
                 {"army_defence_factor": 0.40, "army_org_factor": 0.20, "attrition": -0.30, "stability_factor": 0.25,
                  "war_support_factor": 0.15, "max_dig_in": 3, "army_attack_factor": -0.10})],
         focuses=[
             ("frozen_gates", "산문 봉쇄", "Seal the Gates", [], 5, ["add_stability = 0.05"], None),
             ("frozen_passes", "산길 매몰", "Bury the Passes", ["frozen_gates"], 10, ["TU_build_forts_2 = yes"], None),
             ("frozen_granaries", "만년 곡창", "Granaries for Ages", ["frozen_gates"], 10, ["add_stability = 0.05", "add_manpower = 10000"], None),
             ("frozen_ice_forts", "빙벽 요새", "Ice-Wall Fortresses", ["frozen_passes"], 10, ["TU_build_forts_3 = yes"], None),
             ("frozen_saintess", "성녀의 침묵 서약", "The Saintess's Vow of Silence", ["frozen_granaries"], 10, ["add_political_power = 100"], None),
             ("frozen_guardians", "설산 수호대", "Guardians of the Snow", ["frozen_ice_forts"], 10, ["army_experience = 40", "add_manpower = 15000"], None),
             ("frozen_eternal_winter", "영원한 겨울", "Eternal Winter", ["frozen_guardians", "frozen_saintess"], 15, ["add_war_support = 0.10"], None),
             ("frozen_finale", "얼어붙은 왕국", "The Frozen Kingdom", ["frozen_eternal_winter"], 20,
              ["swap_ideas = { remove_idea = TU_KJE_closed_gates add_idea = TU_KJE_frozen_kingdom }", "add_political_power = 150"],
              ("누구도 들어올 수 없고, 누구도 나가지 않는다. (국호·색 변경, 방어는 극대화되지만 공격은 약해진다)",
               "None may enter, none will leave. (Name and colour change; defence maximised, attack weakened)")),
         ]),
    dict(tag="LGM", key="guard_state", root="TU_LGM_guard_regency",
         event=dict(n=7, title=("웨이옌우의 마지막 결정", "Wei Yenwu's Final Decision"),
                    desc=("섭정 체제가 자리를 잡자 웨이옌우가 천을 불렀다. '용문은 이제 네 것이다. 근위국의 방식으로 지켜라.'",
                          "Once the regency was in place, Wei Yenwu summoned Ch'en. 'Lungmen is yours now. Guard it the Guard Department's way.'"),
                    trigger=["original_tag = LGM", "has_completed_focus = TU_LGM_guard_regency"], mtth=90, ai=50,
                    accept=("근위국 정부를 세운다", "Found the Guard Government"), decline=("섭정으로 충분하다", "The regency is enough"),
                    effects=["add_ideas = TU_LGM_guard_mandate"]),
         ideas=[("guard_mandate", "근위국의 위임", "Mandate of the Guard", {"army_org_factor": 0.10, "stability_factor": 0.05}),
                ("guard_state", "용문 근위국", "The Lungmen Guard State",
                 {"army_attack_factor": 0.20, "army_defence_factor": 0.20, "army_org_factor": 0.20, "stability_factor": 0.15,
                  "political_power_factor": 0.15, "consumer_goods_factor": -0.05, "industrial_capacity_factory": 0.10})],
         focuses=[
             ("guard_mandate_focus", "근위국의 위임", "Mandate of the Guard", [], 5, ["add_political_power = 75"], None),
             ("guard_hoshiguma", "호시구마의 방패", "Hoshiguma's Shield", ["guard_mandate_focus"], 10, ["army_experience = 30"], None),
             ("guard_swire", "스와이어의 경찰 개혁", "Swire's Police Reform", ["guard_mandate_focus"], 10, ["add_stability = 0.05"], None),
             ("guard_red_sword", "적소의 검", "Blade of Chi Xiao", ["guard_hoshiguma"], 10,
              ["add_doctrine_cost_reduction = { name = TU_LGM_guard_red_sword cost_reduction = 0.5 uses = 2 category = land_doctrine }"], None),
             ("guard_city_core", "도시 핵심 방어", "Defend the City Core", ["guard_hoshiguma"], 10, ["TU_build_forts_2 = yes"], None),
             ("guard_trade_law", "근위국 무역법", "Guard Trade Law", ["guard_swire"], 10, ["TU_build_civ_factory = yes"], None),
             ("guard_lungmen_army", "용문 방위군", "Lungmen Defence Army", ["guard_red_sword", "guard_city_core", "guard_trade_law"], 15,
              ["add_manpower = 20000", "army_experience = 50"], None),
             ("guard_finale", "용문 근위국", "The Lungmen Guard State", ["guard_lungmen_army"], 20,
              ["swap_ideas = { remove_idea = TU_LGM_guard_mandate add_idea = TU_LGM_guard_state }", "add_political_power = 150"],
              ("용문은 근위국의 도시다. (국호·색 변경)", "Lungmen is the Guard Department's city. (Name and colour change)")),
         ]),
    dict(tag="YAN", key="sui_dream", root="TU_YAN_p1_ruin_devour", flag_override="TU_YAN_ruler_sui_true", event=None,
         ideas=[("sui_dream", "세의 꿈", "The Dream of Sui",
                 {"army_attack_factor": 0.25, "army_defence_factor": 0.20, "army_org_factor": 0.20, "research_speed_factor": 0.15,
                  "political_power_factor": 0.20, "war_support_factor": 0.30, "stability_factor": 0.15,
                  "production_factory_max_efficiency_factor": 0.15})],
         focuses=[
             ("sui_dream_names", "열두 이름의 귀환", "Return of the Twelve Names", [], 10, ["add_political_power = 100"],
              ("형제들의 이름이 다시 하나의 몸으로 돌아온다.", "The siblings' names return to a single body.")),
             ("sui_dream_mountains", "산과 강을 삼키다", "Swallow Mountains and Rivers", ["sui_dream_names"], 10,
              ["every_neighbor_country = {\n\tlimit = { NOT = { is_in_faction_with = ROOT } }\n\tROOT = { create_wargoal = { type = annex_everything target = PREV } }\n}"], None),
             ("sui_dream_dragon_court", "용의 조정", "Court of the Dragon", ["sui_dream_names"], 10, ["add_stability = 0.10"], None),
             ("sui_dream_legions", "꿈의 군세", "Legions of the Dream", ["sui_dream_mountains"], 10, ["add_manpower = 50000", "army_experience = 50"], None),
             ("sui_dream_arts", "세의 아츠", "Arts of Sui", ["sui_dream_dragon_court"], 10,
              ["add_tech_bonus = { name = TU_YAN_sui_dream_arts bonus = 1.0 uses = 3 category = tu_originium_tech category = infantry_weapons category = artillery }"], None),
             ("sui_dream_finale", "세", "Sui", ["sui_dream_legions", "sui_dream_arts"], 20,
              ["add_ideas = TU_YAN_sui_dream", "add_political_power = 200"],
              ("대지는 꿈을 꾸고, 그 꿈의 이름은 세(歲)다. (국호·색 변경)", "The land dreams, and the name of that dream is Sui. (Name and colour change)")),
         ]),
]


def main():
    ev_out = ["add_namespace = tu_hidden", "# Generated by tools/focusgen/hidden_routes.py (spec 30). Events that open the hidden routes.", ""]
    idea_blocks = []
    ko, en = [], []
    for r in ROUTES:
        tag, key = r["tag"], r["key"]
        flag = r.get("flag_override") or "TU_%s_%s_route" % (tag, key)
        blocks = []
        for i, (sid, fko, fen, pre, cost, rw, desc) in enumerate(r["focuses"]):
            fid = "TU_%s_%s" % (tag, sid)
            pres = ["TU_%s_%s" % (tag, p) for p in pre] or ([r["root"]] if r["root"] else [])
            ptxt = "".join("\t\tprerequisite = { focus = %s }\n" % p for p in pres)
            body = "\n".join("\t\t\t" + l.replace("\n", "\n\t\t\t") for l in rw)
            blocks.append("\tfocus = {\n\t\tid = %s\n%s\t\ticon = GFX_goal_generic_secret_weapon\n\t\tx = %d\n\t\ty = 0\n\t\tcost = %d\n\n"
                          "\t\tsearch_filters = { FOCUS_FILTER_POLITICAL }\n\n\t\tallow_branch = {\n\t\t\thas_country_flag = %s\n\t\t}\n"
                          "%s\n\t\tai_will_do = {\n\t\t\tbase = 1\n\t\t}\n\n\t\tcompletion_reward = {\n%s\n\t\t}\n\t}\n"
                          % (fid, ptxt, 202 + 2 * i, cost, flag,
                             ("\n\t\tavailable = {\n\t\t\thas_country_flag = %s\n\t\t}\n" % flag) if i == 0 else "", body))
            ko += [(fid, fko), (fid + "_desc", desc[0] if desc else "")]
            en += [(fid, fen), (fid + "_desc", desc[1] if desc else "")]
        (HERE / tag.lower() / "p9_hidden.txt").write_text(
            "\t#### %s hidden route (tools/focusgen/hidden_routes.py, spec 30) ####\n\n" % tag + "\n".join(blocks), encoding="utf-8")
        for iid, iko, ien, mods in r["ideas"]:
            full = "TU_%s_%s" % (tag, iid)
            idea_blocks.append("\t\t%s = {\n\t\t\tpicture = generic_morale_bonus\n\t\t\tallowed = { original_tag = %s }\n"
                               "\t\t\tallowed_civil_war = { always = yes }\n\t\t\tmodifier = {\n%s\n\t\t\t}\n\t\t}"
                               % (full, tag, "\n".join("\t\t\t\t%s = %s" % kv for kv in mods.items())))
            ko.append((full, iko))
            en.append((full, ien))
        e = r["event"]
        if e:
            eid = "tu_hidden.%d" % e["n"]
            trig = "\n".join("\t\t" + t.replace("\n", "\n\t\t") for t in e["trigger"])
            eff = "\n".join("\t\t" + t.replace("\n", "\n\t\t") for t in e["effects"])
            ev_out.append("""country_event = {
	id = %s
	title = %s.t
	desc = %s.d
	picture = GFX_report_event_generic_read_write
	fire_only_once = yes

	trigger = {
%s
		NOT = { has_country_flag = %s }
	}

	mean_time_to_happen = {
		days = %d
	}

	option = {
		name = %s.a
		ai_chance = { factor = %d }
		set_country_flag = %s
%s
		mark_focus_tree_layout_dirty = yes
	}

	option = {
		name = %s.b
		ai_chance = { factor = %d }
	}
}
""" % (eid, eid, eid, trig, flag, e["mtth"], eid, e["ai"], flag, eff, eid, 100 - e["ai"]))
            ko += [(eid + ".t", e["title"][0]), (eid + ".d", e["desc"][0]), (eid + ".a", e["accept"][0]), (eid + ".b", e["decline"][0])]
            en += [(eid + ".t", e["title"][1]), (eid + ".d", e["desc"][1]), (eid + ".a", e["accept"][1]), (eid + ".b", e["decline"][1])]
    (MOD / "events" / "tu_hidden_events.txt").write_text("\n".join(ev_out), encoding="utf-8")
    import sys
    sys.path.insert(0, str(HERE.parent))
    import ruling_party  # 사양서 50
    ruling_party.fix_file(MOD / "events" / "tu_hidden_events.txt")
    (MOD / "common" / "ideas" / "tu_hidden_ideas.txt").write_text(
        "# Generated by tools/focusgen/hidden_routes.py (spec 30)\nideas = {\n\tcountry = {\n%s\n\t}\n}\n" % "\n\n".join(idea_blocks),
        encoding="utf-8")
    (MOD / "common" / "opinion_modifiers").mkdir(exist_ok=True)
    (MOD / "common" / "opinion_modifiers" / "tu_hidden_opinion.txt").write_text(
        "opinion_modifiers = {\n\tTU_hidden_friendship = {\n\t\tvalue = 50\n\t}\n}\n", encoding="utf-8")
    ko.append(("TU_hidden_friendship", "바벨의 친구"))
    en.append(("TU_hidden_friendship", "Friends of Babel"))
    for lang, items in (("korean", ko), ("english", en)):
        body = "l_%s:\n" % lang + "".join(' %s:0 "%s"\n' % (k, v.replace('"', '\\"')) for k, v in items)
        (MOD / "localisation" / lang / ("tu_hidden_l_%s.yml" % lang)).write_bytes(("\ufeff" + body).encode("utf-8"))
    for p in [MOD / "events" / "tu_hidden_events.txt", MOD / "common" / "ideas" / "tu_hidden_ideas.txt"] + \
            [HERE / r["tag"].lower() / "p9_hidden.txt" for r in ROUTES]:
        s = p.read_text(encoding="utf-8")
        assert s.count("{") == s.count("}") and all(ord(c) < 128 for c in s), p
    print("HIDDEN routes=%d focuses=%d" % (len(ROUTES), sum(len(r["focuses"]) for r in ROUTES)))


if __name__ == "__main__":
    main()
