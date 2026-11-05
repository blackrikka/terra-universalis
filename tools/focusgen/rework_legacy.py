#!/usr/bin/env python3
"""기존(조각 파일) 트리에 갈래 더하기 (사양서 27): 용문 · 레유니온.

사용법:  python -I tools/focusgen/rework_legacy.py   (그다음 retheme.py --tag 와 merge_focus.py --tag)

tools/focusgen/<tag>/p2_rework.txt 와 localisation/{korean,english}/tu_<tag>_rework_l_*.yml 을 만든다.
보상은 retheme.py 가 영어 이름으로 테마 보상을 넣는다 (여기서는 건설·깃발 같은 고유 보상만).
형식: (id 접미사, 한국어, 영어, [선행 id 접미사 또는 전체 id], 비용, [고유 보상])
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[1] / "terra_universalis"

DATA = {
    "LGM": [
        # 근위국
        ("rw_guard_academy", "근위국 경찰 학교", "Guard Department Academy", ["guard_reform"], 10, []),
        ("rw_special_unit", "특수 작전 반", "Special Operations Unit", ["rw_guard_academy"], 10, []),
        ("rw_riot_shields", "진압 방패대", "Riot Shield Battalions", ["rw_guard_academy"], 10, []),
        ("rw_ch_en_command", "근위국 사령부", "Guard Department Command", ["rw_special_unit", "rw_riot_shields"], 15, []),
        # 이동도시
        ("rw_city_engines", "도시 기관부 정비", "City Engine Overhaul", ["urban_planning"], 10, ["TU_build_infrastructure = yes"]),
        ("rw_mobile_city", "용문 이동도시 개조", "Lungmen Mobile City Refit", ["rw_city_engines"], 15, []),
        ("rw_lower_ring", "하층 구역 재개발", "Lower Ring Redevelopment", ["urban_planning"], 10, ["TU_build_civ_factory = yes"]),
        ("rw_slum_clinics", "빈민가 진료소", "Slum Clinics Medical", ["rw_lower_ring"], 10, []),
        ("rw_infected_quarter", "감염자 구역 개선", "Infected Quarter Housing", ["rw_slum_clinics"], 10, []),
        # 무역
        ("rw_trade_offices", "상공회 무역 사무소", "Chamber of Commerce Offices", ["customs_union"], 10, []),
        ("rw_yan_market", "염국 내륙 시장", "Yan Inland Market Trade", ["rw_trade_offices"], 10, []),
        ("rw_originium_exchange", "원석 거래소", "Originium Exchange", ["rw_trade_offices"], 10, ["TU_build_civ_factory = yes"]),
        ("rw_free_trade_zone", "자유 무역 지대", "Free Trade Zone Market", ["rw_yan_market", "rw_originium_exchange"], 15, []),
        # 방어
        ("rw_city_walls", "외곽 성벽", "Outer City Walls", ["defence_plan"], 10, []),
        ("rw_artillery_towers", "포대 탑", "Artillery Towers", ["rw_city_walls"], 10, []),
        ("rw_drone_net", "도시 드론 방공망", "City Drone Air Defence", ["rw_city_walls"], 10, []),
        # 외교
        ("rw_penguin_logistics", "펭귄 로지스틱스 계약", "Penguin Logistics Contract", ["dip_relations"], 10, []),
        ("rw_rhodes_liaison", "로도스 아일랜드 연락소", "Rhodes Island Liaison Office", ["dip_relations"], 10, []),
        ("rw_neutral_city", "중립 도시 선언", "Neutral City Accord", ["rw_penguin_logistics", "rw_rhodes_liaison"], 15, []),
    ],
    "REU": [
        # 감염자 해방
        ("rw_infected_rally", "감염자 결집", "Infected Rally", ["militia_call"], 10, []),
        ("rw_liberate_camps", "수용소 해방", "Liberate the Camps", ["rw_infected_rally"], 10, ["add_manpower = 10000"]),
        ("rw_arts_squads", "술사 분대", "Caster Squads Training", ["rw_infected_rally"], 10, []),
        ("rw_crossbow_squads", "석궁 분대", "Crossbow Squads Weapons", ["rw_arts_squads"], 10, []),
        ("rw_infected_army", "감염자 해방군", "Infected Liberation Army", ["rw_liberate_camps", "rw_crossbow_squads"], 15, []),
        # 체르노보그
        ("rw_chernobog_factories", "체르노보그 공장 장악", "Seize the Chernobog Factories", ["chernobog_root"], 10, ["TU_build_mil_factory = yes"]),
        ("rw_chernobog_core", "도시 핵심부 확보", "Secure the City Core", ["rw_chernobog_factories"], 10, []),
        ("rw_mobile_fortress", "이동 요새 체르노보그", "Chernobog the Moving Fortress", ["rw_chernobog_core"], 15, []),
        # 사르카즈 용병
        ("rw_sarkaz_contracts", "살카즈 용병 계약", "Sarkaz Mercenary Contracts", ["black_serpent"], 10, []),
        ("rw_w_company", "W의 용병단", "W's Mercenary Company", ["rw_sarkaz_contracts"], 10, []),
        ("rw_sabotage_cells", "파괴 공작 세포", "Sabotage Cells", ["rw_sarkaz_contracts"], 10, []),
        # 눈 악마
        ("rw_snowdevils", "눈 악마 소대", "Snowdevil Squads Guard", ["frost_nova"], 10, []),
        ("rw_winter_warfare", "동계 전투 교리", "Winter Warfare Doctrine", ["rw_snowdevils"], 10, []),
        ("rw_frost_shelters", "동토 대피소", "Frost Shelters Housing", ["rw_snowdevils"], 10, []),
        # 외교·선전
        ("rw_underground_press", "지하 신문", "Underground Press Propaganda", ["dip_envoys"], 10, []),
        ("rw_infected_voice", "감염자의 목소리", "Voice of the Infected Broadcast", ["rw_underground_press"], 10, []),
        ("rw_ursus_infected", "우르수스 감염자 호소", "Appeal to Ursine Infected People", ["rw_infected_voice"], 10, []),
        ("rw_supply_caches", "보급 은닉처", "Hidden Supply Caches", ["dip_envoys"], 10, []),
    ],
}


def main():
    for tag, items in DATA.items():
        low = tag.lower()
        blocks = []
        for sid, ko, en, pre, cost, rw in items:
            fid = "TU_%s_%s" % (tag, sid)
            pres = "".join("\t\tprerequisite = { focus = %s }\n" % (p if p.startswith("TU_") else "TU_%s_%s" % (tag, p)) for p in pre)
            body = "\n".join("\t\t\t" + r for r in rw)
            blocks.append("\tfocus = {\n\t\tid = %s\n%s\t\ticon = GFX_goal_generic_political_pressure\n\t\tx = 0\n\t\ty = 0\n"
                          "\t\tcost = %d\n\n\t\tsearch_filters = { FOCUS_FILTER_POLITICAL }\n\n\t\tai_will_do = {\n\t\t\tbase = 1\n"
                          "\t\t}\n\n\t\tcompletion_reward = {\n%s\n\t\t}\n\t}\n" % (fid, pres, cost, body))
        (HERE / low / "p2_rework.txt").write_text(
            "\t#### %s rework (tools/focusgen/rework_legacy.py, spec 27) ####\n\n" % tag + "\n".join(blocks), encoding="utf-8")
        for lang, i in (("korean", 1), ("english", 2)):
            lines = ["l_%s:" % lang]
            for it in items:
                fid = "TU_%s_%s" % (tag, it[0])
                lines += [' %s:0 "%s"' % (fid, it[i]), ' %s_desc:0 ""' % fid]
            (MOD / "localisation" / lang / ("tu_%s_rework_l_%s.yml" % (low, lang))).write_bytes(
                ("﻿" + "\n".join(lines) + "\n").encode("utf-8"))
        print("REWORK %s +%d" % (tag, len(items)))


if __name__ == "__main__":
    main()
