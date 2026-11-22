#!/usr/bin/env python3
"""빅토리아: 8대 공작 의회와 '파편' 위기 (사양서 80).

공작  캐스터 웰링턴 윈더미어 고도딘 노르망디 애버콘 스태퍼드 파이프  (각자 충성도 0~100, 영향력 0~100)
      - 영지: 빅토리아 본토 주를 지도 위치로 8곳에 나눈다 (k-평균, 캐스터 = 수도 글래스고 쪽). 영지마다 인구 몫(share)이 있다.
      - 충성도 40 미만이면: 영지 몫만큼 공장 출력 감소 (몫 x 50%), 안정도 -2%, 그 공작의 정예 사단 소집 디시전 잠금.
      - 제로섬: '밀어주기'는 그 공작 충성도·영향력을 올리고 맞수의 것을 깎는다.
      - 정예 사단: 웰링턴 육상전함 사단, 윈더미어 전선 돌파군 (잠긴 편제, 시작 군대에 한 개씩).
파편  론디니움을 카즈델이 점거하는 동안 매달 5% 오르는 위기 타이머 (미션 600일 + 변수 TU_VIC_shard).
      자구군 지원 / 로도스 침투조 / 시설 파괴 공작으로 늦춘다. 론디니움을 되찾으면 멈춘다.
      100% 가 되면 '파편 발동': 재앙 국민정신 (조직력 -50% 등), 카즈델 강탈 루트가 열린다 (플래그 TU_VIC_shard_fired).
만드는 파일: common/scripted_effects/tu_vic_dukes_effects.txt, on_actions, dynamic_modifiers, ideas,
            decisions (+categories), events/tu_vic_dukes_events.txt, localisation/*/tu_vic_dukes_l_*.yml
사용법 (python -I):  python -I tools/vic_dukes.py    (그다음 tools/gauges/build_gauges.py)
"""

import itertools
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "terra_universalis"
sys.path.insert(0, str(REPO / "tools" / "mapgen"))
import tiers  # noqa: E402

LONDINIUM = 117
# id, 한, 영, (방향 x, y: 동쪽 +x, 남쪽 +y), 성향, 맞수, 시작 충성도, 영향력
DUKES = [
    ("caster", "캐스터", "Caster", (0, 0), "중앙집권·정치 공작", "wellington", 62, 50),
    ("wellington", "웰링턴", "Wellington", (1, 0.3), "타라 동조·군부", "caster", 48, 35),
    ("windermere", "윈더미어", "Windermere", (0.8, -0.7), "전선 돌파·군부", "godolphin", 52, 30),
    ("godolphin", "고도딘", "Godolphin", (-0.7, 0.7), "개혁·자구군 동조", "windermere", 45, 25),
    ("normandy", "노르망디", "Normandy", (0, 1), "왕당·해안 상업", "abercorn", 55, 25),
    ("abercorn", "애버콘", "Abercorn", (-0.7, -0.7), "귀족·영지 우선", "normandy", 50, 20),
    ("stafford", "스태퍼드", "Stafford", (-1, 0), "공업·개혁", "fife", 42, 20),
    ("fife", "파이프", "Fife", (0, -1), "왕당·북방", "stafford", 40, 15),
]
FACTION = {"noble": ["caster", "abercorn"], "tara": ["wellington", "windermere"], "reform": ["stafford", "godolphin"], "royal": ["normandy", "fife"]}
SHARD_MONTHLY, SHARD_DAYS = 5, 600
LOYAL_MIN = 40


def estates():
    """공작별 영지 주 번호 목록과 인구 몫."""
    st = tiers.load_states()
    G = tiers.province_geo()
    vic = sorted(s for s, d in st.items() if d["owner"] == "VIC" and not d["impassable"] and s != LONDINIUM)

    def c(s):
        _, x, y = G[st[s]["prov"]]
        return x, y
    cap = tiers.capitals()["VIC"]
    seeds = [cap]
    while len(seeds) < 8:                                  # 가장 먼 점 뽑기
        seeds.append(max(vic, key=lambda s: min((c(s)[0] - c(t)[0]) ** 2 + (c(s)[1] - c(t)[1]) ** 2 for t in seeds)))
    cent = [c(s) for s in seeds]
    for _ in range(30):
        groups = [[] for _ in cent]
        for s in vic:
            groups[min(range(8), key=lambda i: (c(s)[0] - cent[i][0]) ** 2 + (c(s)[1] - cent[i][1]) ** 2)].append(s)
        new = [(sum(c(s)[0] for s in g) / len(g), sum(c(s)[1] for s in g) / len(g)) if g else cent[i] for i, g in enumerate(groups)]
        if new == cent:
            break
        cent = new
    # 크기를 고르게: 가까운 쌍부터 채우되 영지마다 CAP 곳까지
    cap_n = math.ceil(len(vic) / 8)
    pairs = sorted(((c(s)[0] - cent[i][0]) ** 2 + (c(s)[1] - cent[i][1]) ** 2, s, i) for s in vic for i in range(8))
    groups, taken = [[] for _ in range(8)], set()
    for _, s, i in pairs:
        if s not in taken and len(groups[i]) < cap_n:
            groups[i].append(s)
            taken.add(s)
    cent = [(sum(c(s)[0] for s in g) / len(g), sum(c(s)[1] for s in g) / len(g)) for g in groups]
    cx = sum(x for x, _ in cent) / 8
    cy = sum(y for _, y in cent) / 8
    capi = next(i for i, g in enumerate(groups) if cap in g)
    others = [i for i in range(8) if i != capi]
    duke_others = [d for d in DUKES if d[0] != "caster"]

    def cost(perm):
        t = 0
        for i, d in zip(perm, duke_others):
            vx, vy = cent[i][0] - cx, cent[i][1] - cy
            n = math.hypot(vx, vy) or 1
            t -= (vx * d[3][0] + vy * d[3][1]) / (n * (math.hypot(*d[3]) or 1))
        return t
    best = min(itertools.permutations(others), key=cost)
    assign = {"caster": groups[capi]}
    for i, d in zip(best, duke_others):
        assign[d[0]] = groups[i]
    total = sum(st[s]["mp"] for s in vic)
    return {d: (sorted(g), sum(st[s]["mp"] for s in g) / total) for d, g in assign.items()}


def effects(est):
    L = []
    init = ["TU_VIC_dukes_init = {", "\t# 영지 주에 공작 표시 (state flag). 이 효과는 on_startup 에서 VIC = { ... } 로 부른다 (ROOT 를 쓰지 않는다)"]
    for d, ko, en, _, _, _, loy, inf in DUKES:
        for s in est[d][0]:
            init.append("\t%d = { set_state_flag = TU_VIC_duke_%s }" % (s, d))
        init += ["\tset_variable = { TU_VIC_loyalty_%s = %d }" % (d, loy), "\tset_variable = { TU_VIC_influence_%s = %d }" % (d, inf),
                 "\tset_variable = { TU_VIC_share_%s = %.4f }" % (d, est[d][1])]
    init += ["\tset_variable = { TU_VIC_shard = 0 }", "\tset_variable = { TU_VIC_duke_ind = 0 }", "\tset_variable = { TU_VIC_duke_stab = 0 }",
             "\tadd_dynamic_modifier = { modifier = TU_VIC_dukes_unrest }",
             "\tactivate_mission = TU_VIC_shard_mission", "}"]
    L.append("\n".join(init))
    # 매달
    m = ["TU_VIC_dukes_monthly = {",
         "\tset_variable = { TU_VIC_duke_ind = 0 }", "\tset_variable = { TU_VIC_duke_stab = 0 }"]
    for d, ko, en, _, _, rival, _, _ in DUKES:
        m += ["\tclamp_variable = { var = TU_VIC_loyalty_%s min = 0 max = 100 }" % d,
              "\tclamp_variable = { var = TU_VIC_influence_%s min = 0 max = 100 }" % d,
              "\t# 파편이 절반을 넘으면 공작들은 흔들린다",
              "\tif = { limit = { check_variable = { TU_VIC_shard > 49 } } add_to_variable = { TU_VIC_loyalty_%s = -1 } }" % d,
              "\tif = {", "\t\tlimit = { check_variable = { TU_VIC_loyalty_%s < %d } }" % (d, LOYAL_MIN),
              "\t\tadd_to_variable = { TU_VIC_duke_ind = %.4f }" % (-0.5 * est[d][1]),
              "\t\tadd_to_variable = { TU_VIC_duke_stab = -0.02 }",
              "\t\tif = { limit = { NOT = { has_country_flag = TU_VIC_warned_%s } } set_country_flag = TU_VIC_warned_%s country_event = { id = tu_vic_dukes.%d } }" % (
                  d, d, [x[0] for x in DUKES].index(d) + 1),
              "\t}", "\tif = { limit = { check_variable = { TU_VIC_loyalty_%s > 54 } } clr_country_flag = TU_VIC_warned_%s }" % (d, d)]
    m += ["\t# 파편 (론디니움을 되찾으면 멈춘다)",
          "\tif = {", "\t\tlimit = { NOT = { controls_state = %d } NOT = { has_country_flag = TU_VIC_shard_fired } }" % LONDINIUM,
          "\t\tadd_to_variable = { TU_VIC_shard = %d }" % SHARD_MONTHLY,
          "\t\tclamp_variable = { var = TU_VIC_shard min = 0 max = 100 }", "\t}", "}"]
    L.append("\n".join(m))
    # 밀어주기 / 달래기 / 파편 늦추기
    for d, ko, en, _, _, rival, _, _ in DUKES:
        L.append("""TU_VIC_support_%(d)s = {
	add_to_variable = { TU_VIC_loyalty_%(d)s = 12 }
	add_to_variable = { TU_VIC_influence_%(d)s = 8 }
	add_to_variable = { TU_VIC_loyalty_%(r)s = -8 }
	add_to_variable = { TU_VIC_influence_%(r)s = -5 }
}
TU_VIC_appease_%(d)s = {
	add_to_variable = { TU_VIC_loyalty_%(d)s = 6 }
}""" % dict(d=d, r=rival))
    L.append("""TU_VIC_shard_slow = {
	# 파편 활성도를 N% 늦추고 미션 시간을 6일 x N 만큼 늘린다 (600일 = 100%)
	add_to_variable = { TU_VIC_shard = -8 }
	clamp_variable = { var = TU_VIC_shard min = 0 max = 100 }
	add_days_mission_timeout = { decision = TU_VIC_shard_mission days = 48 }
}""")
    L.append("""TU_VIC_shard_fire = {
	set_country_flag = TU_VIC_shard_fired
	set_variable = { TU_VIC_shard = 100 }
	add_ideas = TU_VIC_shard_aftermath
	country_event = { id = tu_vic_shard.1 }
}""")
    return "\n\n".join(L) + "\n"


def decisions():
    cats = """# generated by tools/vic_dukes.py (spec 80)
TU_VIC_dukes_category = {
	icon = GFX_decision_category_generic_political_actions
	scripted_gui = TU_VIC_dukes_status_ui
	visible_when_empty = yes
	allowed = { original_tag = VIC }
	priority = 100
}

TU_VIC_shard_category = {
	icon = GFX_decision_category_generic_crisis
	scripted_gui = TU_VIC_shard_status_ui
	visible_when_empty = yes
	allowed = { original_tag = VIC }
	priority = 99
}
"""
    out = ["# generated by tools/vic_dukes.py (spec 80)", "TU_VIC_dukes_category = {"]
    for d, ko, en, _, trait, rival, _, _ in DUKES:
        out.append("""	TU_VIC_dec_support_%(d)s = {
		icon = GFX_decision_generic_political_discourse
		allowed = { original_tag = VIC }
		cost = 40
		days_re_enable = 90
		fire_only_once = no
		complete_effect = { TU_VIC_support_%(d)s = yes }
		ai_will_do = { base = 1 }
	}

	TU_VIC_dec_appease_%(d)s = {
		icon = GFX_decision_generic_fundraising
		allowed = { original_tag = VIC }
		visible = { check_variable = { TU_VIC_loyalty_%(d)s < 55 } }
		cost = 25
		days_re_enable = 60
		fire_only_once = no
		complete_effect = { TU_VIC_appease_%(d)s = yes }
		ai_will_do = { base = 2 }
	}
""" % dict(d=d))
    out.append("""	TU_VIC_dec_muster_wellington = {
		icon = GFX_decision_generic_military
		allowed = { original_tag = VIC }
		available = {
			check_variable = { TU_VIC_loyalty_wellington > %(m)d }
		}
		cost = 100
		days_re_enable = 365
		fire_only_once = no
		complete_effect = {
			capital_scope = { create_unit = { division = "division_template = \\"TU_VIC_wellington_ls\\" start_experience_factor = 0.5 start_equipment_factor = 1" owner = VIC count = 1 } }
		}
		ai_will_do = { base = 0 }
	}

	TU_VIC_dec_muster_windermere = {
		icon = GFX_decision_generic_military
		allowed = { original_tag = VIC }
		available = {
			check_variable = { TU_VIC_loyalty_windermere > %(m)d }
		}
		cost = 100
		days_re_enable = 365
		fire_only_once = no
		complete_effect = {
			capital_scope = { create_unit = { division = "division_template = \\"TU_VIC_windermere_bc\\" start_experience_factor = 0.5 start_equipment_factor = 1" owner = VIC count = 1 } }
		}
		ai_will_do = { base = 0 }
	}
}
""" % dict(m=LOYAL_MIN - 1))
    shard = """
TU_VIC_shard_category = {

	# 시간제한 미션: 600일 안에 론디니움을 되찾거나 파편을 늦춰야 한다. 변수 TU_VIC_shard 와 같이 움직인다.
	TU_VIC_shard_mission = {
		icon = GFX_decision_generic_air
		allowed = { original_tag = VIC }
		activation = { always = no }
		available = { always = no }
		days_mission_timeout = %(days)d
		is_good = no
		fire_only_once = yes
		cancel_trigger = { controls_state = %(lon)d }
		timeout_effect = { TU_VIC_shard_fire = yes }
		ai_will_do = { base = 0 }
	}

	TU_VIC_dec_shard_corps = {
		icon = GFX_decision_generic_intelligence_operation
		allowed = { original_tag = VIC }
		visible = { NOT = { controls_state = %(lon)d } NOT = { has_country_flag = TU_VIC_shard_fired } }
		available = {
			command_power > 19
			has_equipment = { infantry_equipment > 999 }
		}
		cost = 25
		days_re_enable = 60
		fire_only_once = no
		complete_effect = {
			add_command_power = -20
			add_equipment_to_stockpile = { type = infantry_equipment amount = -1000 }
			TU_VIC_shard_slow = yes
		}
		ai_will_do = { base = 3 }
	}

	TU_VIC_dec_shard_rhodes = {
		icon = GFX_decision_generic_operation
		allowed = { original_tag = VIC }
		visible = { NOT = { controls_state = %(lon)d } NOT = { has_country_flag = TU_VIC_shard_fired } country_exists = RHO }
		available = {
			country_exists = RHO
			NOT = { has_war_with = RHO }
			command_power > 9
		}
		cost = 75
		days_re_enable = 120
		fire_only_once = no
		complete_effect = {
			add_command_power = -10
			TU_VIC_shard_slow = yes
			TU_VIC_shard_slow = yes
			RHO = { add_opinion_modifier = { target = VIC modifier = TU_dip_trade } }
		}
		ai_will_do = { base = 2 }
	}

	TU_VIC_dec_shard_sabotage = {
		icon = GFX_decision_generic_police_action
		allowed = { original_tag = VIC }
		visible = { NOT = { controls_state = %(lon)d } NOT = { has_country_flag = TU_VIC_shard_fired } }
		available = { command_power > 39 check_variable = { TU_VIC_shard > 39 } }
		cost = 50
		days_re_enable = 180
		fire_only_once = no
		complete_effect = {
			add_command_power = -40
			add_stability = -0.02
			TU_VIC_shard_slow = yes
			TU_VIC_shard_slow = yes
			TU_VIC_shard_slow = yes
		}
		ai_will_do = { base = 1 }
	}
}
""" % dict(days=SHARD_DAYS, lon=LONDINIUM)
    return cats, "\n".join(out) + shard


def events():
    ev = ["add_namespace = tu_vic_dukes", "add_namespace = tu_vic_shard", "# generated by tools/vic_dukes.py (spec 80)"]
    for i, (d, ko, en, _, _, _, _, _) in enumerate(DUKES, 1):
        ev.append("""country_event = {
	id = tu_vic_dukes.%(i)d
	title = tu_vic_dukes.%(i)d.t
	desc = tu_vic_dukes.%(i)d.d
	picture = GFX_report_event_generic_conference
	is_triggered_only = yes

	option = {
		name = tu_vic_dukes.%(i)d.a
		ai_chance = { factor = 70 }
		add_political_power = -30
		TU_VIC_appease_%(d)s = yes
	}
	option = {
		name = tu_vic_dukes.%(i)d.b
		ai_chance = { factor = 30 }
		add_stability = -0.02
	}
}
""" % dict(i=i, d=d))
    ev.append("""country_event = {
	id = tu_vic_shard.1
	title = tu_vic_shard.1.t
	desc = tu_vic_shard.1.d
	picture = GFX_report_event_generic_battle
	is_triggered_only = yes

	option = {
		name = tu_vic_shard.1.a
		ai_chance = { factor = 1 }
	}
}
""")
    return "\n".join(ev)


def ideas_and_mods():
    ideas = """# generated by tools/vic_dukes.py (spec 80)
ideas = {
	country = {
		TU_VIC_shard_aftermath = {
			picture = generic_fortify_the_borders
			allowed = { always = no }
			allowed_civil_war = { always = yes }
			removal_cost = -1
			modifier = {
				army_org_factor = -0.5
				stability_factor = -0.15
				war_support_factor = -0.1
				production_speed_infrastructure_factor = -0.5
				supply_consumption_factor = 0.25
			}
		}
	}
}
"""
    dyn = """# generated by tools/vic_dukes.py (spec 80). Values come from country variables set in TU_VIC_dukes_monthly.
TU_VIC_dukes_unrest = {
	icon = GFX_modifiers_generic_military_plans
	enable = { check_variable = { TU_VIC_duke_ind < -0.0001 } }

	industrial_capacity_factory = TU_VIC_duke_ind
	stability_factor = TU_VIC_duke_stab
}
"""
    onact = """# generated by tools/vic_dukes.py (spec 80)
on_actions = {
	on_startup = {
		effect = {
			if = {
				limit = { country_exists = VIC }
				VIC = {
					TU_VIC_dukes_init = yes
					set_country_flag = TU_VIC_dukes_started
				}
			}
		}
	}
	on_monthly = {
		effect = {
			if = {
				limit = { original_tag = VIC has_country_flag = TU_VIC_dukes_started }
				TU_VIC_dukes_monthly = yes
			}
		}
	}
}
"""
    return ideas, dyn, onact


def loc(est):
    ko = ["l_korean:", " # generated by tools/vic_dukes.py (spec 80)",
          ' TU_VIC_dukes_category:0 "대공 의회"',
          ' TU_VIC_dukes_category_desc:0 "빅토리아 본토는 여덟 공작의 영지로 나뉘어 있다. 충성도가 §Y%d§! 아래로 떨어진 공작의 영지는 공장 출력이 몫만큼 줄고 안정도가 깎이며, 그 공작의 정예 사단을 소집할 수 없다. 한 공작을 밀어주면 맞수가 반발한다."' % LOYAL_MIN,
          ' TU_VIC_shard_category:0 "파편"',
          ' TU_VIC_shard_category_desc:0 "론디니움을 점거한 카즈델 군사위원회가 인공 재앙 병기 \'파편\'을 깨우고 있다. 활성도가 §R100%§!가 되면 동부 전선이 초토화되고 카즈델 강탈 루트가 열린다. 론디니움을 되찾으면 멈춘다."',
          ' TU_VIC_shard_mission:0 "파편 카운트다운"',
          ' TU_VIC_shard_mission_desc:0 "남은 날이 다하면 파편이 발동한다. 자구군 지원·로도스 침투조·시설 파괴 공작으로 늦출 수 있다. 론디니움을 되찾으면 취소된다."',
          ' TU_VIC_dec_shard_corps:0 "자구군 지원"', ' TU_VIC_dec_shard_corps_desc:0 "론디니움 안의 자구군에 지휘력 §Y20§!과 보병 장비 §Y1000§!개를 보낸다. 파편 활성도 -8%, 시간 +48일."',
          ' TU_VIC_dec_shard_rhodes:0 "로도스 침투조 지원"', ' TU_VIC_dec_shard_rhodes_desc:0 "로도스 아일랜드 침투조를 돕는다. 지휘력 §Y10§!. 파편 활성도 -16%."',
          ' TU_VIC_dec_shard_sabotage:0 "파편 시설 파괴 공작"', ' TU_VIC_dec_shard_sabotage_desc:0 "파편의 에너지 시설을 노린다. 지휘력 §Y40§!, 안정도 -2%. 파편 활성도 -24%. (활성도 40% 이상)"',
          ' TU_VIC_dec_muster_wellington:0 "웰링턴 육상전함 사단 소집"', ' TU_VIC_dec_muster_wellington_desc:0 "웰링턴 공작의 육상전함 사단 한 개를 수도에 세운다. (웰링턴 충성도 §Y%d§! 이상)"' % LOYAL_MIN,
          ' TU_VIC_dec_muster_windermere:0 "윈더미어 전선 돌파군 소집"', ' TU_VIC_dec_muster_windermere_desc:0 "윈더미어 공작의 전선 돌파군 한 개를 수도에 세운다. (윈더미어 충성도 §Y%d§! 이상)"' % LOYAL_MIN,
          ' TU_VIC_shard_aftermath:0 "파편의 재앙"',
          ' TU_VIC_shard_aftermath_desc:0 "파편이 깨어났다. 동부 전선의 인프라가 무너지고 군은 혼란에 빠졌다. 조직력 -50%, 안정도 -15%, 전쟁 지지 -10%."',
          ' TU_VIC_dukes_unrest:0 "공작들의 불만"', ' TU_VIC_dukes_unrest_desc:0 "충성을 잃은 공작의 영지에서 공장이 돌지 않는다."',
          ' tu_vic_shard.1.t:0 "파편 발동"',
          ' tu_vic_shard.1.d:0 "론디니움의 하늘이 붉게 물들었다. 카즈델 군사위원회가 \'파편\'을 깨웠고, 동부 전선에서 인프라가 차례로 무너진다. 군의 조직은 반으로 줄었다. 이제 카즈델은 빅토리아의 공업을 \'보호\'하겠다며 손을 내밀고 있다."',
          ' tu_vic_shard.1.a:0 "...늦었다."']
    en = ["l_english:", " # generated by tools/vic_dukes.py (spec 80)",
          ' TU_VIC_dukes_category:0 "Ducal Council"',
          ' TU_VIC_dukes_category_desc:0 "Victoria proper is split among eight ducal estates. A duke whose loyalty falls below §Y%d§! loses his estate\'s share of factory output, costs stability and cannot raise his elite division. Backing one duke angers his rival."' % LOYAL_MIN,
          ' TU_VIC_shard_category:0 "The Shard"',
          ' TU_VIC_shard_category_desc:0 "The Kazdel Military Commission holding Londinium is awakening the artificial calamity weapon, the Shard. At §R100%§! the eastern front is devastated and the Kazdel Extortion route opens. Retaking Londinium stops it."',
          ' TU_VIC_shard_mission:0 "Shard Countdown"',
          ' TU_VIC_shard_mission_desc:0 "When the days run out the Shard fires. Slow it with Self-Salvation Corps aid, Rhodes Island infiltrators or sabotage. Retaking Londinium cancels it."',
          ' TU_VIC_dec_shard_corps:0 "Aid the Self-Salvation Corps"', ' TU_VIC_dec_shard_corps_desc:0 "Send §Y20§! command power and §Y1000§! infantry equipment to the Corps inside Londinium. Shard -8%, +48 days."',
          ' TU_VIC_dec_shard_rhodes:0 "Support the Rhodes Island Team"', ' TU_VIC_dec_shard_rhodes_desc:0 "Back the Rhodes Island infiltrators. §Y10§! command power. Shard -16%."',
          ' TU_VIC_dec_shard_sabotage:0 "Sabotage the Shard"', ' TU_VIC_dec_shard_sabotage_desc:0 "Strike the Shard\'s power plants. §Y40§! command power, stability -2%. Shard -24%. (Shard 40%+)"',
          ' TU_VIC_dec_muster_wellington:0 "Raise Wellington\'s Land Battleship Division"', ' TU_VIC_dec_muster_wellington_desc:0 "Raise one land battleship division of Duke Wellington at the capital. (Wellington loyalty §Y%d§!+)"' % LOYAL_MIN,
          ' TU_VIC_dec_muster_windermere:0 "Raise Windermere\'s Breakthrough Corps"', ' TU_VIC_dec_muster_windermere_desc:0 "Raise one breakthrough corps of Duke Windermere at the capital. (Windermere loyalty §Y%d§!+)"' % LOYAL_MIN,
          ' TU_VIC_shard_aftermath:0 "Calamity of the Shard"',
          ' TU_VIC_shard_aftermath_desc:0 "The Shard has awakened. Infrastructure on the eastern front is collapsing and the army is in disarray. Organisation -50%, stability -15%, war support -10%."',
          ' TU_VIC_dukes_unrest:0 "Ducal Discontent"', ' TU_VIC_dukes_unrest_desc:0 "Factories on the estates of disloyal dukes stand idle."',
          ' tu_vic_shard.1.t:0 "The Shard Fires"',
          ' tu_vic_shard.1.d:0 "The sky over Londinium has turned red. The Kazdel Military Commission has woken the Shard, and the infrastructure of the eastern front is failing one stretch after another. The army\'s organisation has halved. Now Kazdel offers its hand to \'protect\' Victorian industry."',
          ' tu_vic_shard.1.a:0 "...Too late."']
    for i, (d, k, e, _, trait, rival, _, _) in enumerate(DUKES, 1):
        rk = next(x[1] for x in DUKES if x[0] == rival)
        re_ = next(x[2] for x in DUKES if x[0] == rival)
        pct = est[d][1] * 50
        ko += [' TU_VIC_dec_support_%s:0 "%s 공작 밀어주기"' % (d, k),
               ' TU_VIC_dec_support_%s_desc:0 "%s 공작(%s)의 충성도 +12, 영향력 +8. 맞수 %s 공작은 충성도 -8, 영향력 -5."' % (d, k, trait, rk),
               ' TU_VIC_dec_appease_%s:0 "%s 공작 달래기"' % (d, k),
               ' TU_VIC_dec_appease_%s_desc:0 "%s 공작의 충성도 +6. 충성도가 55 미만일 때만 보인다."' % (d, k),
               ' tu_vic_dukes.%d.t:0 "%s 공작의 불만"' % (i, k),
               ' tu_vic_dukes.%d.d:0 "%s 공작이 의회에 나오지 않고 영지의 문을 닫았다. 영지의 공장이 멈추고 있다. (영지 몫 %.0f%%, 공장 출력 -%.0f%%)"' % (i, k, est[d][1] * 100, pct),
               ' tu_vic_dukes.%d.a:0 "선물을 보내 달랜다."' % i, ' tu_vic_dukes.%d.b:0 "버틴다."' % i,
               ]
        en += [' TU_VIC_dec_support_%s:0 "Back Duke %s"' % (d, e),
               ' TU_VIC_dec_support_%s_desc:0 "Duke %s: loyalty +12, influence +8. His rival, Duke %s: loyalty -8, influence -5."' % (d, e, re_),
               ' TU_VIC_dec_appease_%s:0 "Appease Duke %s"' % (d, e),
               ' TU_VIC_dec_appease_%s_desc:0 "Duke %s loyalty +6. Shown only while his loyalty is below 55."' % (d, e),
               ' tu_vic_dukes.%d.t:0 "Duke %s Is Unhappy"' % (i, e),
               ' tu_vic_dukes.%d.d:0 "Duke %s has stopped attending the council and shut the gates of his estate. The factories there are going quiet. (Estate share %.0f%%, factory output -%.0f%%)"' % (i, e, est[d][1] * 100, pct),
               ' tu_vic_dukes.%d.a:0 "Send gifts to calm him."' % i, ' tu_vic_dukes.%d.b:0 "Hold firm."' % i]
    return "\n".join(ko) + "\n", "\n".join(en) + "\n"


def oob_templates():
    """시작 군대에 정예 사단 두 개와 그 편제 (잠긴 편제)."""
    p = MOD / "history" / "units" / "VIC_1097.txt"
    t = p.read_text(encoding="utf-8-sig")
    if "TU_VIC_wellington_ls" in t:
        return
    block = lambda name, grp: """
division_template = {
	name = "%s"
	division_names_group = TU_DIVNAMES_FALLBACK
	is_locked = yes

	regiments = {
		infantry = { x = 0 y = 0 }
	}
}
""" % name
    i = t.index("\nunits = {")
    p.write_text(t[:i] + block("TU_VIC_wellington_ls", 0) + block("TU_VIC_windermere_bc", 0) + t[i:], encoding="utf-8")
    sys.path.insert(0, str(REPO / "tools"))
    import templates
    templates.apply_file(p)                                    # 편성은 tools/templates.py 의 TEMPLATES


def main():
    est = estates()
    eff = effects(est)
    (MOD / "common" / "scripted_effects" / "tu_vic_dukes_effects.txt").write_text(eff, encoding="utf-8")
    ideas, dyn, onact = ideas_and_mods()
    (MOD / "common" / "ideas" / "tu_vic_dukes_ideas.txt").write_text(ideas, encoding="utf-8")
    (MOD / "common" / "dynamic_modifiers" / "tu_vic_dynamic_modifiers.txt").write_text(dyn, encoding="utf-8")
    (MOD / "common" / "on_actions" / "tu_vic_dukes_on_actions.txt").write_text(onact, encoding="utf-8")
    cats, decs = decisions()
    (MOD / "common" / "decisions" / "categories" / "tu_vic_dukes_categories.txt").write_text(cats, encoding="utf-8")
    (MOD / "common" / "decisions" / "tu_vic_dukes_decisions.txt").write_text(decs, encoding="utf-8")
    (MOD / "events" / "tu_vic_dukes_events.txt").write_text(events(), encoding="utf-8")
    ko, en = loc(est)
    (MOD / "localisation" / "korean" / "tu_vic_dukes_l_korean.yml").write_bytes(ko.encode("utf-8-sig"))
    (MOD / "localisation" / "english" / "tu_vic_dukes_l_english.yml").write_bytes(en.encode("utf-8-sig"))
    oob_templates()
    print("VIC_DUKES estates=%s" % {d: (len(s), round(sh, 3)) for d, (s, sh) in est.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
