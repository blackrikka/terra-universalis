#!/usr/bin/env python3
"""테라 연구 트리 + 오리지늄 시스템 생성기 (사양서 19).

사용법:  python -I tools/techgen/build_techs.py

바닐라 기술 파일은 descriptor.mod 의 replace_path="common/technologies" 로 모두 지우고, 여기서 새 트리를 쓴다.
- 장비·부대를 여는 기술은 바닐라 기술 id 를 다시 쓴다 (아이콘이 저절로 붙음). 이름·설명은 replace 로컬라이제이션으로 바꾼다.
- 테라 고유 기술(라테라노 총기, 오리지늄 공학, 광석병 의학)은 새 id. 아이콘은 interface/tu_technologies.gfx 에서 바닐라 그림을 빌린다.
- 연도는 테라력: 시대 E0~E6 = 1090, 1097, 1100, 1103, 1106, 1109, 1112 (게임 시작 1097).
  (예전에는 바닐라 1936년 기술이 그대로 남아 1097년 시작 기준 '839년 앞선 연구' 벌칙이 붙었다.)
- 해군 기술은 없다. 옛 해군 탭 두 개(mtgnavalfolder, mtgnavalsupportfolder)는 '오리지늄 공학'·'광석병 의학' 탭이 된다.
- 총기는 라테라노만: 라테라노 총기 갈래는 allow_branch = { original_tag = LAT }. 다른 나라 보병 장구는 석궁·도검·아츠 장구.

만드는 파일
    common/technologies/tu_<폴더>.txt, common/technology_tags/00_technology.txt (바닐라 같은 이름 덮어쓰기)
    common/buildings/tu_buildings.txt (오리지늄 정제소)
    interface/tu_technologies.gfx
    localisation/{korean,english}/tu_techs_l_*.yml, localisation/{korean,english}/replace/tu_techs_replace_l_*.yml
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MOD = REPO / "terra_universalis"

ERA = {0: (1090, 0), 1: (1097, 2), 2: (1100, 4), 3: (1103, 6), 4: (1106, 8), 5: (1109, 10), 6: (1112, 12)}
TECHS = []          # dict 목록
NEW_ICON = {}       # 새 기술 id -> 바닐라 텍스처 경로


def T(tid, folder, x, era, ko, en, cost=1.5, leads=(), eq=(), sub=(), bld=None, mods=None, unit=None, cats=(),
      ab=None, ai=1, desc=("", ""), xor=(), icon=None, vanilla=True):
    TECHS.append(dict(id=tid, folder=folder, x=x, era=era, ko=ko, en=en, cost=cost, leads=list(leads), eq=list(eq),
                      sub=list(sub), bld=bld, mods=mods or {}, unit=unit or {}, cats=list(cats), ab=ab, ai=ai,
                      desc=desc, xor=list(xor), vanilla=vanilla))
    if icon:
        NEW_ICON[tid] = "gfx/interface/technologies/%s.dds" % icon


INF = "infantry_folder"
SUP = "support_folder"
ART = "artillery_folder"
ARM = "armour_folder"
AIR = "air_techs_folder"
IND = "industry_folder"
ELE = "electronics_folder"
ORI = "mtgnavalfolder"
MED = "mtgnavalsupportfolder"
INFW = ("infantry_weapons",)

# ======================================================================== 보병 장구
T("infantry_weapons", INF, 0, 0, "석궁과 도검", "Crossbows and Blades", leads=["infantry_weapons1"],
  eq=["infantry_equipment_0"], sub=["infantry"], cats=INFW, ai=10,
  desc=("테라의 병사는 총 대신 석궁과 도검, 방패를 든다. 총은 라테라노 산크타만의 것이다.",
        "Terran soldiers carry crossbows, blades and shields instead of guns. Firearms belong to Laterano's Sankta alone."))
T("infantry_weapons1", INF, 0, 1, "제식 보병 장구", "Standard Infantry Kit", leads=["infantry_weapons2"],
  eq=["infantry_equipment_1"], cats=INFW, ai=10)
T("infantry_weapons2", INF, 0, 2, "강철 석궁", "Steel Crossbows", leads=["improved_infantry_weapons"],
  unit={"category_all_infantry": {"soft_attack": 0.05}}, cats=INFW, ai=5)
T("improved_infantry_weapons", INF, 0, 3, "원석 강화 장구", "Originium-Hardened Kit", cost=2,
  leads=["improved_infantry_weapons_2"], eq=["infantry_equipment_2"], cats=INFW, ai=8)
T("improved_infantry_weapons_2", INF, 0, 4, "아츠 보조 장구", "Arts-Assisted Kit", cost=2,
  leads=["advanced_infantry_weapons"], unit={"category_all_infantry": {"soft_attack": 0.05}}, cats=INFW, ai=4)
T("advanced_infantry_weapons", INF, 0, 5, "오리지늄 합금 장구", "Originium Alloy Kit", cost=2.5,
  leads=["advanced_infantry_weapons2"], eq=["infantry_equipment_3"], cats=INFW, ai=8)
T("advanced_infantry_weapons2", INF, 0, 6, "정예 보병 장구", "Elite Infantry Kit", cost=2.5,
  unit={"category_all_infantry": {"soft_attack": 0.05, "defense": 0.05}}, cats=INFW, ai=3)
# 라테라노 총기 (라테라노 전용)
LAT = "original_tag = LAT"
T("tu_lat_firearms_1", INF, 2, 1, "산크타 총기", "Sankta Firearms", leads=["tu_lat_firearms_2"], ab=LAT, vanilla=False,
  unit={"category_all_infantry": {"soft_attack": 0.10}}, cats=INFW + ("tu_lat_firearms_tech",), ai=20, icon="infantry_at",
  desc=("테라에서 총을 제대로 다루는 것은 헤일로와 날개를 가진 산크타뿐이다.",
        "In all of Terra, only the haloed, winged Sankta can truly wield firearms."))
T("tu_lat_firearms_2", INF, 2, 3, "자동 화기", "Automatic Firearms", cost=2, leads=["tu_lat_firearms_3"], ab=LAT,
  vanilla=False, unit={"category_all_infantry": {"soft_attack": 0.10, "hard_attack": 0.05}},
  cats=INFW + ("tu_lat_firearms_tech",), ai=15, icon="infantry_weapons2")
T("tu_lat_firearms_3", INF, 2, 5, "총기 교리 완성", "Perfected Gun Doctrine", cost=2.5, leads=["tu_lat_firearms_4"], ab=LAT,
  vanilla=False, unit={"category_all_infantry": {"soft_attack": 0.10, "breakthrough": 0.10}},
  cats=INFW + ("tu_lat_firearms_tech",), ai=10, icon="infantry_weapons3")
T("tu_lat_firearms_4", INF, 2, 6, "성유물 총기", "Relic Firearms", cost=3, ab=LAT, vanilla=False,
  unit={"category_all_infantry": {"soft_attack": 0.10, "hard_attack": 0.10}},
  cats=INFW + ("tu_lat_firearms_tech",), ai=8, icon="tech_special_forces")
# 기동 보병
T("tech_trucks", INF, 4, 1, "화물 차량", "Cargo Vehicles", leads=["motorised_infantry"], eq=["motorized_equipment_0"],
  sub=["mot_anti_tank_brigade", "mot_artillery_brigade", "mot_anti_air_brigade"], cats=["motorized_equipment"], ai=5)
T("motorised_infantry", INF, 4, 2, "차량화 보병", "Motorised Infantry", leads=["mechanised_infantry"],
  eq=["motorized_equipment_1"], sub=["motorized"], cats=["motorized_equipment"], ai=5)
T("mechanised_infantry", INF, 4, 4, "장갑 수송차", "Armoured Carriers", cost=2, leads=["mechanised_infantry2"],
  eq=["mechanized_equipment_1"], sub=["mechanized"], cats=["motorized_equipment", "cat_mechanized_equipment"], ai=4)
T("mechanised_infantry2", INF, 4, 5, "원석 엔진 수송차", "Originium-Engine Carriers", cost=2.5,
  leads=["mechanised_infantry3"], eq=["mechanized_equipment_2"], cats=["motorized_equipment", "cat_mechanized_equipment"], ai=3)
T("mechanised_infantry3", INF, 4, 6, "이동도시 강습차", "Mobile City Assault Carriers", cost=3, eq=["mechanized_equipment_3"],
  cats=["motorized_equipment", "cat_mechanized_equipment"], ai=2)
# 특수 보병
T("tech_mountaineers", INF, 6, 1, "산악 보병", "Mountain Infantry", leads=["tech_mountaineers2"], sub=["mountaineers"],
  cats=["infantry_tech", "mountaineers_tech"], ai=2)
T("tech_mountaineers2", INF, 6, 3, "설산 훈련", "Snow Peak Training", cost=2, leads=["tech_mountaineers3"],
  unit={"mountaineers": {"soft_attack": 0.10, "defense": 0.05}}, cats=["infantry_tech", "mountaineers_tech"], ai=1)
T("tech_mountaineers3", INF, 6, 5, "쉐라그 산악 전술", "Kjerag Mountain Tactics", cost=2.5,
  unit={"mountaineers": {"soft_attack": 0.10, "breakthrough": 0.10}}, cats=["infantry_tech", "mountaineers_tech"], ai=1)
T("paratroopers", INF, 8, 3, "비행선 강하 보병", "Airship Drop Infantry", cost=2, leads=["paratroopers2"], sub=["paratrooper"],
  cats=["infantry_tech", "para_tech"], ai=1)
T("paratroopers2", INF, 8, 5, "강하 전술", "Drop Tactics", cost=2.5, unit={"paratrooper": {"soft_attack": 0.10, "defense": 0.10}},
  cats=["infantry_tech", "para_tech"], ai=1)

# ======================================================================== 지원
T("tech_support", SUP, 6, 0, "지원 장비", "Support Equipment", eq=["support_equipment_1"], cats=["support_tech"], ai=10,
  leads=["tech_engineers", "tech_recon", "tech_military_police", "tech_field_hospital", "tech_maintenance_company",
         "tech_logistics_company", "tech_signal_company"])
for x, base, ko, en, sub, era0, ups in (
        (0, "tech_engineers", "공병", "Engineers", "engineer", 1, [({"engineer": {"entrenchment": 0.5}}, "참호 공병", "Trench Engineers"),
                                                                   ({"engineer": {"entrenchment": 0.5}}, "요새 공병", "Fortress Engineers")]),
        (2, "tech_recon", "정찰대", "Recon", "recon", 1, [({"recon": {"recon": 1}}, "원거리 정찰", "Long-Range Scouts"),
                                                         ({"recon": {"recon": 1}}, "아츠 감지", "Arts Detection")]),
        (4, "tech_military_police", "헌병", "Military Police", "military_police", 1,
         [({"military_police": {"suppression": 0.25}}, "치안대", "Security Corps")]),
        (6, "tech_field_hospital", "야전 의무대", "Field Medics", "field_hospital", 1,
         [({"field_hospital": {"max_organisation": 2}}, "아츠 치료사", "Arts Healers"),
          ({"field_hospital": {"max_organisation": 2}}, "후방 의료망", "Rear Medical Network")]),
        (8, "tech_maintenance_company", "정비대", "Maintenance Crews", "maintenance_company", 2,
         [({"maintenance_company": {"max_organisation": 2}}, "원석 장비 정비", "Originium Gear Upkeep")]),
        (10, "tech_logistics_company", "보급대", "Logistics Corps", "logistics_company", 2,
         [({"logistics_company": {"max_organisation": 2}}, "수송 행렬", "Supply Columns")]),
        (12, "tech_signal_company", "통신대", "Signal Corps", "signal_company", 2,
         [({"signal_company": {"max_organisation": 2}}, "아츠 통신", "Arts Signals")])):
    ids = [base] + ["%s%d" % (base, i + 2) for i in range(len(ups))]
    T(base, SUP, x, era0, ko, en, cost=1.25, leads=ids[1:2], sub=[sub] + (["mot_recon"] if sub == "recon" else []),
      cats=["support_tech"], ai=4)
    for i, (unit, uko, uen) in enumerate(ups):
        T(ids[i + 1], SUP, x, era0 + 2 * (i + 1), uko, uen, cost=1.5 + 0.5 * i, leads=ids[i + 2:i + 3], unit=unit,
          cats=["support_tech"], ai=2)
T("basic_train", SUP, 14, 0, "증기 기관차", "Steam Locomotives", leads=["wartime_train"], eq=["train_equipment_1"],
  cats=["train_tech"], ai=2)
T("wartime_train", SUP, 14, 3, "원석 기관차", "Originium Locomotives", cost=2, eq=["train_equipment_2"], cats=["train_tech"], ai=2)

# ======================================================================== 포병·공성
ARTC = ["artillery"]
T("gw_artillery", ART, 0, 0, "공성 노포", "Siege Bombards", leads=["interwar_artillery"], eq=["artillery_equipment_1"],
  sub=["artillery_brigade", "artillery"], cats=ARTC, ai=5)
T("interwar_artillery", ART, 0, 1, "개량 포가", "Improved Carriages", leads=["artillery1", "interwar_antitank", "interwar_antiair"],
  unit={"artillery_brigade": {"soft_attack": 0.10}, "artillery": {"soft_attack": 0.10}}, cats=ARTC, ai=4)
T("artillery1", ART, 0, 2, "원석 탄약 포", "Originium Shell Guns", cost=2, leads=["artillery2"], eq=["artillery_equipment_2"],
  cats=ARTC, ai=4)
T("artillery2", ART, 0, 3, "포병 관측", "Artillery Spotting", cost=2, leads=["artillery4", "rocket_artillery"],
  unit={"artillery_brigade": {"soft_attack": 0.10}, "artillery": {"soft_attack": 0.10}}, cats=ARTC, ai=3)
T("artillery4", ART, 0, 4, "중공성포", "Heavy Siege Guns", cost=2.5, leads=["artillery5"], eq=["artillery_equipment_3"],
  cats=ARTC, ai=3)
T("artillery5", ART, 0, 5, "아츠 유도 포격", "Arts-Guided Bombardment", cost=2.5,
  unit={"artillery_brigade": {"soft_attack": 0.10}, "artillery": {"soft_attack": 0.10}}, cats=ARTC, ai=2)
T("interwar_antitank", ART, 2, 2, "대장갑 노포", "Anti-Armour Bombards", leads=["antitank2"], eq=["anti_tank_equipment_1"],
  sub=["anti_tank_brigade", "anti_tank"], cats=["artillery", "cat_anti_tank"], ai=3)
T("antitank2", ART, 2, 4, "관통 탄두", "Piercing Warheads", cost=2, leads=["antitank5"], eq=["anti_tank_equipment_2"],
  cats=["artillery", "cat_anti_tank"], ai=2)
T("antitank5", ART, 2, 6, "원석 관통탄", "Originium Penetrators", cost=2.5, eq=["anti_tank_equipment_3"],
  cats=["artillery", "cat_anti_tank"], ai=2)
T("interwar_antiair", ART, 4, 2, "대공 노포", "Anti-Air Bombards", leads=["antiair2"], eq=["anti_air_equipment_1"],
  sub=["anti_air_brigade", "anti_air"], bld=("anti_air_building", 5), cats=["artillery", "cat_anti_air"], ai=3)
T("antiair2", ART, 4, 4, "대드론 사격", "Anti-Drone Fire", cost=2, leads=["antiair5"], eq=["anti_air_equipment_2"],
  cats=["artillery", "cat_anti_air"], ai=2)
T("antiair5", ART, 4, 6, "아츠 방공망", "Arts Air Shield", cost=2.5, eq=["anti_air_equipment_3"], cats=["artillery", "cat_anti_air"], ai=2)
T("rocket_artillery", ART, 6, 4, "아츠 로켓", "Arts Rockets", cost=2, leads=["rocket_artillery4"], eq=["rocket_artillery_equipment_1"],
  sub=["rocket_artillery_brigade", "rocket_artillery"], cats=["artillery", "mot_rockets"], ai=2)
T("rocket_artillery4", ART, 6, 6, "다연장 아츠 로켓", "Multiple Arts Rockets", cost=2.5, eq=["rocket_artillery_equipment_2"],
  cats=["artillery", "mot_rockets"], ai=2)

# ======================================================================== 장갑 차량
T("gwtank", ARM, 0, 1, "증기 장갑차", "Steam Armour", leads=["basic_light_tank", "basic_medium_tank"], eq=["gw_tank_equipment"],
  sub=["light_armor"], cats=["armor", "cat_light_armor"], ai=3)
T("basic_light_tank", ARM, 0, 2, "경장갑 차량", "Light Armoured Vehicles", cost=2, leads=["improved_light_tank"],
  eq=["light_tank_equipment_1"], sub=["light_armor"], cats=["armor", "cat_light_armor"], ai=3)
T("improved_light_tank", ARM, 0, 4, "원석 엔진 경장갑", "Originium-Engine Light Armour", cost=2.5, leads=["advanced_light_tank"],
  eq=["light_tank_equipment_2"], cats=["armor", "cat_light_armor"], ai=2)
T("advanced_light_tank", ARM, 0, 6, "고속 강습 차량", "Fast Assault Vehicles", cost=3, eq=["light_tank_equipment_3"],
  cats=["armor", "cat_light_armor"], ai=2)
T("basic_medium_tank", ARM, 2, 3, "중장갑 차량", "Medium Armoured Vehicles", cost=2.5, leads=["improved_medium_tank", "basic_heavy_tank"],
  eq=["medium_tank_equipment_1"], sub=["medium_armor"], cats=["armor", "cat_medium_armor"], ai=3)
T("improved_medium_tank", ARM, 2, 5, "우르수스식 장갑", "Ursine Armour", cost=3, leads=["advanced_medium_tank"],
  eq=["medium_tank_equipment_2"], cats=["armor", "cat_medium_armor"], ai=2)
T("advanced_medium_tank", ARM, 2, 6, "이동도시 호위 장갑", "Mobile City Escort Armour", cost=3.5, eq=["medium_tank_equipment_3"],
  cats=["armor", "cat_medium_armor"], ai=2)
T("basic_heavy_tank", ARM, 4, 4, "중전차", "Heavy Armour", cost=3, leads=["improved_heavy_tank"], eq=["heavy_tank_equipment_1"],
  sub=["heavy_armor"], cats=["armor", "cat_heavy_armor"], ai=1)
T("improved_heavy_tank", ARM, 4, 6, "육상 요새 차량", "Land Fortress Vehicles", cost=3.5, eq=["heavy_tank_equipment_2"],
  cats=["armor", "cat_heavy_armor"], ai=1)

# ======================================================================== 항공 (드론·비행선)
T("early_fighter", AIR, 0, 1, "정찰 드론", "Scout Drones", leads=["fighter1", "CAS1"], eq=["fighter_equipment_0"],
  cats=["air_equipment", "light_fighter"], ai=3)
T("fighter1", AIR, 0, 2, "요격 드론", "Interceptor Drones", cost=2, leads=["fighter2"], eq=["fighter_equipment_1"],
  cats=["air_equipment", "light_fighter"], ai=3)
T("fighter2", AIR, 0, 4, "원석 엔진 드론", "Originium-Engine Drones", cost=2.5, leads=["fighter3"], eq=["fighter_equipment_2"],
  cats=["air_equipment", "light_fighter"], ai=2)
T("fighter3", AIR, 0, 6, "아츠 제어 드론", "Arts-Controlled Drones", cost=3, eq=["fighter_equipment_3"],
  cats=["air_equipment", "light_fighter"], ai=2)
T("CAS1", AIR, 2, 3, "지상 공격 드론", "Ground-Attack Drones", cost=2, leads=["CAS2"], eq=["CAS_equipment_1"],
  cats=["air_equipment", "cas_bomber"], ai=2)
T("CAS2", AIR, 2, 5, "강습 드론", "Assault Drones", cost=2.5, eq=["CAS_equipment_2"], cats=["air_equipment", "cas_bomber"], ai=2)
T("early_bomber", AIR, 4, 1, "폭격 비행선", "Bomber Airships", leads=["tactical_bomber1", "strategic_bomber1"],
  eq=["tac_bomber_equipment_0"], cats=["air_equipment", "tactical_bomber"], ai=2)
T("tactical_bomber1", AIR, 4, 3, "전술 비행선", "Tactical Airships", cost=2, leads=["tactical_bomber2"], eq=["tac_bomber_equipment_1"],
  cats=["air_equipment", "tactical_bomber"], ai=2)
T("tactical_bomber2", AIR, 4, 5, "빅토리아식 비행선", "Victorian Airships", cost=2.5, eq=["tac_bomber_equipment_2"],
  cats=["air_equipment", "tactical_bomber"], ai=2)
T("strategic_bomber1", AIR, 6, 4, "대형 폭격선", "Heavy Bombardment Ships", cost=3, leads=["strategic_bomber2"],
  eq=["strat_bomber_equipment_1"], cats=["air_equipment", "cat_strategic_bomber"], ai=1)
T("strategic_bomber2", AIR, 6, 6, "공중 요새선", "Sky Fortress Ships", cost=3.5, eq=["strat_bomber_equipment_2"],
  cats=["air_equipment", "cat_strategic_bomber"], ai=1)
T("early_transport_plane", AIR, 8, 2, "수송 비행선", "Transport Airships", leads=["improved_transport_plane"],
  eq=["transport_plane_equipment_1"], cats=["air_equipment"], ai=1)
T("improved_transport_plane", AIR, 8, 5, "대형 수송선", "Heavy Transport Ships", cost=2.5, eq=["transport_plane_equipment_2"],
  cats=["air_equipment"], ai=1)

# ======================================================================== 산업
IC = ["industry", "cat_production"]
for i, (tid, ko, en, era) in enumerate((("basic_machine_tools", "기초 공작 기계", "Basic Machine Tools", 1),
                                        ("improved_machine_tools", "정밀 공작 기계", "Precision Machine Tools", 2),
                                        ("advanced_machine_tools", "원석 동력 공작 기계", "Originium-Powered Tools", 3),
                                        ("assembly_line_production", "조립 라인", "Assembly Lines", 5))):
    nxt = {0: ["improved_machine_tools", "concentrated_industry", "dispersed_industry"], 1: ["advanced_machine_tools"],
           2: ["assembly_line_production"], 3: []}[i]
    T(tid, IND, 0, era, ko, en, cost=1.5 + 0.5 * i, leads=nxt, mods={"production_factory_max_efficiency_factor": 0.10}, cats=IC, ai=20)
T("concentrated_industry", IND, 2, 2, "집중 공업", "Concentrated Industry", cost=2, leads=["concentrated_industry2"],
  xor=["dispersed_industry"], mods={"industrial_capacity_factory": 0.10}, cats=["industry", "concentrated_industry_category"], ai=10)
T("concentrated_industry2", IND, 2, 4, "공업 도시", "Industrial Cities", cost=2.5, xor=["dispersed_industry2"],
  mods={"industrial_capacity_factory": 0.10}, cats=["industry", "concentrated_industry_category"], ai=8)
T("dispersed_industry", IND, 3, 2, "분산 공업", "Dispersed Industry", cost=2, leads=["dispersed_industry2"],
  xor=["concentrated_industry"], mods={"industrial_capacity_factory": 0.05, "line_change_production_efficiency_factor": 0.15},
  cats=["industry", "dispersed_industry_category"], ai=10)
T("dispersed_industry2", IND, 3, 4, "이동도시 공방", "Mobile City Workshops", cost=2.5, xor=["concentrated_industry2"],
  mods={"industrial_capacity_factory": 0.05, "line_change_production_efficiency_factor": 0.15},
  cats=["industry", "dispersed_industry_category"], ai=8)
for i, era in enumerate((1, 2, 3, 4, 5)):
    T("construction%d" % (i + 1), IND, 5, era, ("건설 기법 %s" % "I II III IV V".split()[i]), ("Construction %s" % "I II III IV V".split()[i]),
      cost=1.5 + 0.25 * i, leads=["construction%d" % (i + 2)] if i < 4 else [],
      mods={"production_speed_buildings_factor": 0.10, "industry_repair_factor": 0.05}, cats=["industry", "construction_tech"], ai=10)
for i, era in enumerate((1, 3, 5)):
    T("excavation%d" % (i + 1), IND, 7, era, ("채굴 기법 %s" % "I II III".split()[i]), ("Excavation %s" % "I II III".split()[i]),
      cost=1.5 + 0.5 * i, leads=["excavation%d" % (i + 2)] if i < 2 else [], mods={"local_resources_factor": 0.05},
      cats=["industry", "excavation_tech"], ai=5)
T("fuel_silos", IND, 9, 1, "연료 저장소", "Fuel Silos", leads=["fuel_refining"], bld=("fuel_silo", 5), cats=["industry"], ai=3)
T("fuel_refining", IND, 9, 3, "연료 정제", "Fuel Refining", cost=2, leads=["synth_oil_experiments"], mods={"fuel_gain_factor": 0.10},
  cats=["industry"], ai=3)
T("synth_oil_experiments", IND, 9, 4, "합성 연료", "Synthetic Fuel", cost=2.5, leads=["rubber_processing"], bld=("synthetic_refinery", 3),
  cats=["industry", "synth_resources", "cat_synth_oil"], ai=3)
T("rubber_processing", IND, 9, 6, "합성 고무", "Synthetic Rubber", cost=2.5, mods={"local_resources_factor": 0.03},
  cats=["industry", "synth_resources", "cat_synth_rubber"], ai=2)

# ======================================================================== 전자·아츠 공학
T("electronic_mechanical_engineering", ELE, 0, 1, "전기 공학", "Electrical Engineering", leads=["radio", "mechanical_computing"],
  mods={"research_speed_factor": 0.03}, cats=["electronics"], ai=10)
T("radio", ELE, 0, 2, "무선 통신", "Radio", cost=2, leads=["improved_radio", "radio_detection"],
  mods={"coordination_bonus": 0.05, "land_reinforce_rate": 0.02}, cats=["electronics"], ai=4)
T("improved_radio", ELE, 0, 4, "아츠 중계 통신", "Arts Relay Signals", cost=2.5, leads=["advanced_radio"],
  mods={"coordination_bonus": 0.05, "land_reinforce_rate": 0.02}, cats=["electronics"], ai=3)
T("advanced_radio", ELE, 0, 6, "광역 통신망", "Wide-Area Signal Net", cost=3, mods={"coordination_bonus": 0.05, "land_reinforce_rate": 0.02},
  cats=["electronics"], ai=2)
T("mechanical_computing", ELE, 2, 2, "계산 기관", "Calculating Engines", cost=2, leads=["computing_machine"],
  mods={"research_speed_factor": 0.03}, cats=["electronics", "computing_tech"], ai=8)
T("computing_machine", ELE, 2, 4, "원석 연산기", "Originium Computers", cost=2.5, leads=["improved_computing_machine"],
  mods={"research_speed_factor": 0.03}, cats=["electronics", "computing_tech"], ai=6)
T("improved_computing_machine", ELE, 2, 6, "아츠 연산망", "Arts Computing Grid", cost=3, mods={"research_speed_factor": 0.04},
  cats=["electronics", "computing_tech"], ai=4)
T("radio_detection", ELE, 4, 3, "탐지 아츠", "Detection Arts", cost=2, leads=["centimetric_radar"], bld=("radar_station", 6),
  mods={"coordination_bonus": 0.03}, cats=["electronics", "radar_tech"], ai=2)
T("centimetric_radar", ELE, 4, 5, "광역 탐지망", "Wide Detection Net", cost=2.5, mods={"coordination_bonus": 0.05},
  cats=["electronics", "radar_tech"], ai=2)
T("basic_encryption", ELE, 6, 3, "암호 체계", "Ciphers", cost=2, leads=["improved_encryption"], mods={"encryption": 1},
  cats=["electronics", "encryption_tech"], ai=1)
T("improved_encryption", ELE, 6, 5, "아츠 암호", "Arts Ciphers", cost=2.5, mods={"encryption": 1}, cats=["electronics", "encryption_tech"], ai=1)
T("basic_decryption", ELE, 7, 3, "암호 해독", "Codebreaking", cost=2, leads=["improved_decryption"], mods={"decryption": 1},
  cats=["electronics", "decryption_tech"], ai=1)
T("improved_decryption", ELE, 7, 5, "해독 기관", "Decryption Engines", cost=2.5, mods={"decryption": 1}, cats=["electronics", "decryption_tech"], ai=1)
T("basic_fortification_tech", ELE, 9, 1, "축성술", "Fortification", leads=["land_fort_tech_1", "coastal_fort_tech_1"],
  mods={"bunker_max_level_terrain_limit": 1}, cats=["construction_tech", "cat_fortification"], ai=3)
T("land_fort_tech_1", ELE, 9, 3, "요새선", "Fortress Lines", cost=2, leads=["land_fort_tech_2"], mods={"bunker_max_level_terrain_limit": 1},
  cats=["construction_tech", "cat_fortification"], ai=2)
T("land_fort_tech_2", ELE, 9, 5, "원석 강화 요새", "Originium-Reinforced Forts", cost=2.5, mods={"bunker_max_level_terrain_limit": 1},
  cats=["construction_tech", "cat_fortification"], ai=2)
T("coastal_fort_tech_1", ELE, 10, 3, "해안 방벽", "Sea Walls", cost=2, mods={"coastal_bunker_max_level_terrain_limit": 1},
  cats=["construction_tech", "cat_fortification"], ai=2)

# ======================================================================== 오리지늄 공학 (옛 해군 탭)
ORIC = ["tu_originium_tech"]
T("tu_ori_refining_1", ORI, 0, 1, "원석 정제", "Originium Refining", leads=["tu_ori_refining_2", "tu_ori_engines", "tu_landship_1"],
  bld=("originium_refinery", 2), cats=ORIC + ["industry"], ai=15, vanilla=False, icon="synth_oil_experiments",
  desc=("원석은 테라 문명의 연료이자 재앙이다. 정제소를 지을 수 있다.", "Originium is both the fuel and the curse of Terran civilisation. Unlocks the Originium Refinery."))
T("tu_ori_refining_2", ORI, 0, 3, "고순도 정제", "High-Purity Refining", cost=2, leads=["tu_ori_refining_3"],
  bld=("originium_refinery", 4), cats=ORIC + ["industry"], ai=10, vanilla=False, icon="oil_processing")
T("tu_ori_refining_3", ORI, 0, 5, "원석 정제 단지", "Refinery Complexes", cost=2.5, bld=("originium_refinery", 6),
  cats=ORIC + ["industry"], ai=8, vanilla=False, icon="fuel_refining1")
T("tu_ori_engines", ORI, 2, 2, "원석 엔진", "Originium Engines", cost=2, leads=["tu_ori_engines_2"],
  mods={"fuel_gain_factor": 0.15, "army_fuel_consumption_factor": -0.05}, cats=ORIC, ai=6, vanilla=False, icon="jet_engines")
T("tu_ori_engines_2", ORI, 2, 4, "원석 동력로", "Originium Reactors", cost=2.5, leads=["tu_ori_mobile_cities"],
  mods={"industrial_capacity_factory": 0.05}, cats=ORIC + ["industry"], ai=6, vanilla=False, icon="nuclear_reactor")
T("tu_ori_mobile_cities", ORI, 2, 6, "이동도시 동력", "Mobile City Power", cost=3,
  mods={"production_speed_infrastructure_factor": 0.20, "production_speed_rail_way_factor": 0.20}, cats=ORIC, ai=4,
  vanilla=False, icon="basic_construction")
T("tu_arts_theory", ORI, 4, 1, "아츠 이론", "Arts Theory", leads=["tu_arts_units"], mods={"research_speed_factor": 0.02},
  cats=ORIC + ["electronics"], ai=8, vanilla=False, icon="atomic_research",
  desc=("원석을 매개로 한 아츠는 테라의 과학이자 무기다.", "Arts channelled through originium are both Terra's science and its weapon."))
T("tu_arts_units", ORI, 4, 3, "술사 부대 교리", "Caster Unit Doctrine", cost=2, leads=["tu_arts_amplifier"],
  unit={"category_all_infantry": {"soft_attack": 0.05}}, cats=ORIC, ai=6, vanilla=False, icon="night_vision")
T("tu_arts_amplifier", ORI, 4, 5, "아츠 증폭기", "Arts Amplifiers", cost=2.5,
  unit={"category_all_infantry": {"soft_attack": 0.05}, "artillery_brigade": {"soft_attack": 0.05}}, cats=ORIC, ai=4,
  vanilla=False, icon="experimental_rockets")
T("tu_ori_weapons", ORI, 6, 3, "원석 탄두", "Originium Warheads", cost=2, leads=["tu_ori_weapons_2"],
  unit={"artillery_brigade": {"soft_attack": 0.10}, "anti_tank_brigade": {"hard_attack": 0.10}}, cats=ORIC + ["artillery"], ai=4,
  vanilla=False, icon="infantry_at")
T("tu_ori_weapons_2", ORI, 6, 5, "원석 폭발 공학", "Originium Blast Engineering", cost=2.5,
  unit={"artillery_brigade": {"soft_attack": 0.10}, "anti_tank_brigade": {"hard_attack": 0.10}}, cats=ORIC + ["artillery"], ai=3,
  vanilla=False, icon="experimental_rockets")

# 육상함 (디시전 "육상함·이동도시" 를 연다: common/decisions/tu_landship_decisions.txt)
T("tu_landship_1", ORI, 8, 2, "육상함 설계", "Landship Design", cost=2, leads=["tu_landship_2"], cats=ORIC, ai=6, vanilla=False,
  icon="basic_construction", desc=("바다를 잃은 테라의 함대는 땅 위를 달린다. 경육상함 전대를 취역할 수 있다 (최대 2).",
                                    "Terra's fleets, denied the sea, sail over land. Allows Light Landship Squadrons (up to 2)."))
T("tu_landship_2", ORI, 8, 4, "중육상함", "Heavy Landships", cost=2.5, leads=["tu_landship_3"], cats=ORIC, ai=5, vanilla=False,
  mods={"army_fuel_consumption_factor": -0.05}, icon="jet_engines",
  desc=("중육상함 전대 (최대 4), 이동도시 이전 디시전.", "Heavy Landship Squadrons (up to 4) and the Relocate the Mobile City decision."))
T("tu_landship_3", ORI, 8, 6, "이동도시급 육상함", "City-Class Landships", cost=3, cats=ORIC, ai=4, vanilla=False,
  mods={"army_fuel_consumption_factor": -0.05}, icon="nuclear_reactor",
  desc=("도시 하나가 통째로 움직이는 거대 육상함 (최대 6).", "Colossal landships that carry a whole city (up to 6)."))

# ======================================================================== 광석병 의학 (옛 해군 지원 탭)
MEDC = ["tu_oripathy_tech"]
T("tu_oripathy_research", MED, 0, 1, "광석병 연구", "Oripathy Research", leads=["tu_suppressants", "tu_field_arts_medicine"],
  mods={"stability_factor": 0.02}, cats=MEDC, ai=8, vanilla=False, icon="tech_field_hospital",
  desc=("원석 결정이 몸을 잠식하는 불치병. 정제소가 늘수록 감염의 위험도 커진다.",
        "An incurable disease in which originium crystals consume the body. More refineries mean more risk of infection."))
T("tu_suppressants", MED, 0, 3, "억제제 생산", "Suppressant Production", cost=2, leads=["tu_infected_care"],
  mods={"stability_factor": 0.03, "monthly_population": 0.05}, cats=MEDC, ai=6, vanilla=False, icon="tech_field_hospital2")
T("tu_infected_care", MED, 0, 5, "감염자 치료 체계", "Infected Care System", cost=2.5, leads=["tu_oripathy_relief"],
  mods={"stability_factor": 0.03, "monthly_population": 0.10}, cats=MEDC, ai=4, vanilla=False, icon="rubber_processing")
T("tu_oripathy_relief", MED, 0, 6, "광석병 완화 요법", "Oripathy Relief Therapy", cost=3,
  mods={"stability_factor": 0.04, "conscription_factor": 0.03}, cats=MEDC, ai=3, vanilla=False, icon="improved_rubber_processing")
T("tu_field_arts_medicine", MED, 2, 2, "야전 아츠 치료", "Field Arts Medicine", cost=2, leads=["tu_combat_medics"],
  mods={"land_reinforce_rate": 0.02}, cats=MEDC, ai=4, vanilla=False, icon="tech_field_hospital")
T("tu_combat_medics", MED, 2, 4, "전투 의무관", "Combat Medics", cost=2.5, mods={"army_morale_factor": 0.05}, cats=MEDC, ai=3,
  vanilla=False, icon="tech_field_hospital2")
T("tu_catastrophe_forecast", MED, 4, 2, "천재 예보", "Catastrophe Forecasting", cost=2, leads=["tu_catastrophe_shelter"],
  mods={"industry_repair_factor": 0.10, "production_speed_buildings_factor": 0.05}, cats=MEDC, ai=4, vanilla=False,
  icon="mechanical_computing",
  desc=("천재(天災)는 원석 폭풍과 함께 도시를 덮친다. 천재 신사들의 예보가 피해를 줄인다.",
        "Catastrophes strike cities with originium storms. The forecasts of Catastrophe Messengers reduce the damage."))
T("tu_catastrophe_shelter", MED, 4, 4, "천재 대피망", "Catastrophe Shelters", cost=2.5,
  mods={"stability_factor": 0.03, "industry_air_damage_factor": -0.10}, cats=MEDC, ai=3, vanilla=False,
  icon="improved_computing_machine")


# ======================================================================== 쓰기
def unit_block(unit):
    out = []
    for u, stats in unit.items():
        out.append("\t\t%s = {\n%s\n\t\t}" % (u, "\n".join("\t\t\t%s = %s" % kv for kv in stats.items())))
    return out


def tech_text(t):
    year, row = ERA[t["era"]]
    L = []
    if t["ab"]:
        L.append("\t\tallow_branch = {\n\t\t\t%s\n\t\t}" % t["ab"])
    if t["eq"]:
        L.append("\t\tenable_equipments = {\n%s\n\t\t}" % "\n".join("\t\t\t" + e for e in t["eq"]))
    if t["sub"]:
        L.append("\t\tenable_subunits = {\n%s\n\t\t}" % "\n".join("\t\t\t" + s for s in t["sub"]))
    if t["bld"]:
        L.append("\t\tenable_building = {\n\t\t\tbuilding = %s\n\t\t\tlevel = %d\n\t\t}" % t["bld"])
    for k, v in t["mods"].items():
        L.append("\t\t%s = %s" % (k, v))
    L += unit_block(t["unit"])
    if t["xor"]:
        L.append("\t\txor = { %s }" % " ".join(t["xor"]))
    for n in t["leads"]:
        L.append("\t\tpath = {\n\t\t\tleads_to_tech = %s\n\t\t\tresearch_cost_coeff = 1\n\t\t}" % n)
    L.append("\t\tresearch_cost = %s" % t["cost"])
    L.append("\t\tstart_year = %d" % year)
    L.append("\t\tfolder = {\n\t\t\tname = %s\n\t\t\tposition = { x = %d y = %d }\n\t\t}" % (t["folder"], t["x"], row))
    L.append("\t\tcategories = {\n%s\n\t\t}" % "\n".join("\t\t\t" + c for c in t["cats"]))
    L.append("\t\tai_will_do = {\n\t\t\tfactor = %s\n\t\t}" % t["ai"])
    return "\t%s = {\n%s\n\t}\n" % (t["id"], "\n\n".join(L))


FILES = {INF: "infantry", SUP: "support", ART: "artillery", ARM: "armour", AIR: "air", IND: "industry", ELE: "electronics",
         ORI: "originium", MED: "oripathy"}
CATEGORIES_EXTRA = ["tu_originium_tech", "tu_oripathy_tech", "tu_lat_firearms_tech"]
# 바닐라 기술 분류 (다른 파일·모디파이어가 이름으로 부를 수 있어 모두 남긴다)
CATEGORIES_VANILLA = """light_air medium_air heavy_air armor cat_light_armor cat_medium_armor cat_heavy_armor artillery cat_anti_tank
cat_anti_air naval_air infantry_weapons motorized_equipment cat_mechanized_equipment naval_equipment rocketry nuclear industry
electronics cat_fortification land_doctrine air_doctrine naval_doctrine jet_technology light_fighter cat_heavy_fighter
tactical_bomber cat_strategic_bomber naval_bomber cas_bomber ship_modules_tech dd_tech ca_tech cv_tech bc_tech bb_tech ss_tech
tp_tech synth_resources encryption_tech decryption_tech computing_tech radar_tech infantry_tech marine_tech construction_tech
excavation_tech air_equipment night_vision mot_rockets support_tech para_tech engineers_tech recon_tech mountaineers_tech
rangers_tech_cat military_police_tech hospital_tech logistics_tech signal_company_tech maintenance_company_tech naval_mines
concentrated_industry_category dispersed_industry_category asw_tech naval_minesweeping naval_minelaying cat_scout_plane
train_tech cat_production cat_synth_rubber cat_synth_oil cat_armored_cars cat_special_forces_generic cat_torpedoes""".split()


def write_loc(path, lang, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "l_%s:\n" % lang + "".join(' %s:0 "%s"\n' % (k, v.replace('"', '\\"')) for k, v in items)
    path.write_bytes(("\ufeff" + body).encode("utf-8"))


def main():
    ids = [t["id"] for t in TECHS]
    assert len(ids) == len(set(ids)), "duplicate tech id"
    known = set(ids)
    seen = {}
    for t in TECHS:
        for n in t["leads"] + t["xor"]:
            assert n in known, (t["id"], n)
        key = (t["folder"], t["x"], ERA[t["era"]][1])
        assert key not in seen, ("position clash", t["id"], seen.get(key))
        seen[key] = t["id"]
        for c in t["cats"]:
            assert c in CATEGORIES_VANILLA or c in CATEGORIES_EXTRA, (t["id"], c)

    tdir = MOD / "common" / "technologies"
    tdir.mkdir(parents=True, exist_ok=True)
    for old in tdir.glob("*.txt"):
        old.unlink()
    for folder, name in FILES.items():
        body = "".join(tech_text(t) for t in TECHS if t["folder"] == folder)
        (tdir / ("tu_%s.txt" % name)).write_text(
            "# Generated by tools/techgen/build_techs.py. Do not edit by hand.\ntechnologies = {\n\n%s}\n" % body, encoding="utf-8")

    tags = MOD / "common" / "technology_tags"
    tags.mkdir(parents=True, exist_ok=True)
    (tags / "00_technology.txt").write_text("""# Terra Universalis: replaces the vanilla file of the same name (tools/techgen/build_techs.py).
# No naval research: the two old naval folders hold Originium Engineering and Oripathy Medicine.

technology_categories = {
%s
}

technology_folders = {
	infantry_folder = { ledger = army }
	support_folder = { ledger = army }
	armour_folder = { ledger = army }
	nsb_armour_folder = {
		ledger = army
		available = { always = no }
	}
	artillery_folder = { ledger = army }
	mtgnavalfolder = { ledger = civilian }
	mtgnavalsupportfolder = { ledger = civilian }
	air_techs_folder = { ledger = air }
	bba_air_techs_folder = {
		ledger = air
		available = { always = no }
	}
	electronics_folder = { ledger = civilian }
	industry_folder = { ledger = civilian }
	land_doctrine_folder = {
		ledger = army
		doctrine = yes
	}
	naval_doctrine_folder = {
		ledger = navy
		doctrine = yes
	}
	air_doctrine_folder = {
		ledger = air
		doctrine = yes
	}
	special_forces_doctrine_folder = {
		available = {
			OR = {
				has_dlc = "Arms Against Tyranny"
				has_dlc = "No Compromise, No Surrender"
			}
		}
		ledger = hidden
		doctrine = yes
	}
}
""" % "\n".join("\t" + c for c in CATEGORIES_VANILLA + CATEGORIES_EXTRA), encoding="utf-8")

    bdir = MOD / "common" / "buildings"
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / "tu_buildings.txt").write_text("""# Terra Universalis buildings (tools/techgen/build_techs.py). Added next to the vanilla buildings.
# Originium Refinery: replaces the dockyard as the 'third industry'. Every level helps research and industry
# but raises oripathy risk (stability). Unlocked by the Originium Engineering techs.

buildings = {
	originium_refinery = {
		base_cost = 7200
		icon_frame = 10
		value = 4
		show_on_map = 0
		hide_if_missing_tech = yes
		infrastructure_construction_effect = yes
		show_modifier = yes

		country_modifiers = {
			modifiers = {
				research_speed_factor = 0.004
				industrial_capacity_factory = 0.004
				fuel_gain_from_states = 1.0
				stability_factor = -0.004
			}
		}

		level_cap = {
			shares_slots = yes
			state_max = 6
		}
	}
}
""", encoding="utf-8")

    gfx = ["# Generated by tools/techgen/build_techs.py: icons for Terra-only techs (borrowed vanilla pictures).", "spriteTypes = {"]
    for tid, tex in NEW_ICON.items():
        for suffix in ("_medium", ""):
            gfx.append('\tspriteType = {\n\t\tname = "GFX_%s%s"\n\t\ttexturefile = "%s"\n\t}' % (tid, suffix, tex))
    gfx.append("}")
    (MOD / "interface" / "tu_technologies.gfx").write_text("\n".join(gfx) + "\n", encoding="utf-8")

    new_ko, new_en, rep_ko, rep_en = [], [], [], []
    for t in TECHS:
        (rep_ko if t["vanilla"] else new_ko).append((t["id"], t["ko"]))
        (rep_en if t["vanilla"] else new_en).append((t["id"], t["en"]))
        if t["desc"][0]:
            (rep_ko if t["vanilla"] else new_ko).append((t["id"] + "_desc", t["desc"][0]))
            (rep_en if t["vanilla"] else new_en).append((t["id"] + "_desc", t["desc"][1]))
    new_ko += [("originium_refinery", "오리지늄 정제소"), ("originium_refinery_plural", "오리지늄 정제소"),
               ("originium_refinery_desc", "원석을 정제해 연료와 연구 자원을 만든다. 단계마다 연구 속도 +0.4%, 공장 생산 +0.4%, 연료 +1, §R안정도 -0.4%§! (광석병 위험)."),
               ("tu_originium_tech", "오리지늄 공학"), ("tu_oripathy_tech", "광석병 의학"), ("tu_lat_firearms_tech", "라테라노 총기")]
    new_en += [("originium_refinery", "Originium Refinery"), ("originium_refinery_plural", "Originium Refineries"),
               ("originium_refinery_desc", "Refines originium into fuel and research material. Each level: research speed +0.4%, factory output +0.4%, fuel +1, §Rstability -0.4%§! (oripathy risk)."),
               ("tu_originium_tech", "Originium Engineering"), ("tu_oripathy_tech", "Oripathy Medicine"), ("tu_lat_firearms_tech", "Laterano Firearms")]
    folders = [("mtgnavalfolder", "오리지늄 공학", "Originium Engineering"), ("mtgnavalsupportfolder", "광석병 의학", "Oripathy Medicine"),
               ("infantry_folder", "보병 장구", "Infantry Kit"), ("artillery_folder", "포병·공성", "Artillery and Siege"),
               ("armour_folder", "장갑 차량", "Armoured Vehicles"), ("air_techs_folder", "드론·비행선", "Drones and Airships"),
               ("electronics_folder", "전기·아츠 공학", "Electrical and Arts Engineering")]
    equipment = [("infantry_equipment", "보병 장구", "Infantry Kit"), ("infantry_equipment_0", "석궁과 도검", "Crossbows and Blades"),
                 ("infantry_equipment_1", "제식 보병 장구", "Standard Infantry Kit"),
                 ("infantry_equipment_2", "원석 강화 장구", "Originium-Hardened Kit"),
                 ("infantry_equipment_3", "오리지늄 합금 장구", "Originium Alloy Kit")]
    for k, ko, en in folders + equipment:
        rep_ko.append((k, ko))
        rep_en.append((k, en))
    write_loc(MOD / "localisation/korean/tu_techs_l_korean.yml", "korean", new_ko)
    write_loc(MOD / "localisation/english/tu_techs_l_english.yml", "english", new_en)
    write_loc(MOD / "localisation/korean/replace/tu_techs_replace_l_korean.yml", "korean", rep_ko)
    write_loc(MOD / "localisation/english/replace/tu_techs_replace_l_english.yml", "english", rep_en)

    for p in list(tdir.glob("*.txt")) + [tags / "00_technology.txt", bdir / "tu_buildings.txt", MOD / "interface/tu_technologies.gfx"]:
        s = p.read_text(encoding="utf-8")
        assert s.count("{") == s.count("}"), p
        assert all(ord(c) < 128 for c in s), p
    print("TECHS %d (new %d) in %d folders, icons %d" % (len(TECHS), sum(not t["vanilla"] for t in TECHS), len(FILES), len(NEW_ICON)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
