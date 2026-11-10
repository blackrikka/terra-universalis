#!/usr/bin/env python3
"""병종 이름: 명일방주 포지션(큰 병종)과 세부 분류(세부 병종) (사양서 73, 예전 사양서 60 을 대체).

포지션 8개는 Arknights Terra Wiki (arknights.wiki.gg/wiki/Class), 세부 분류의 한국어 이름은 나무위키
'명일방주/포지션' 문서의 표기를 따른다. 사용자가 배정표를 확인했다 (2026-11-10).

    이름 형식   <포지션> <세부 분류> 대대 / 중대      캐스터·메딕은 세부 분류 이름에 포지션이 들어 있어 한 번만 쓴다
    쓰는 파일   localisation/<언어>/replace/tu_units_l_<언어>.yml  (바닐라 병종 이름을 덮어쓴다)
    CLASS_OF    병종 -> 포지션 (tools/unit_icons.py 가 포지션 아이콘을 고를 때 쓴다)

사용법 (python -I):  python -I tools/unit_names.py
"""

import sys
from pathlib import Path

LOC = Path(__file__).resolve().parents[1] / "terra_universalis" / "localisation"
CLASS = {"vanguard": ("뱅가드", "Vanguard"), "guard": ("가드", "Guard"), "defender": ("디펜더", "Defender"),
         "sniper": ("스나이퍼", "Sniper"), "caster": ("캐스터", "Caster"), "medic": ("메딕", "Medic"),
         "supporter": ("서포터", "Supporter"), "specialist": ("스페셜리스트", "Specialist")}
BN, CO, SUP, MOT = ("대대", "Battalion"), ("중대", "Company"), ("지원 중대", "Support Company"), ("기동 대대", "Mobile Battalion")
# 병종: (포지션, 세부 분류 한, 영, 단위, 설명 한, 영)
UNITS = {
    "cavalry": ("vanguard", "돌격수", "Charger", BN,
                "말을 타고 먼저 달려들어 적진을 흔드는 뱅가드입니다.", "Vanguards who ride in first and shake the enemy line."),
    "motorized": ("vanguard", "척후병", "Pioneer", BN,
                  "차량으로 먼저 도착해 전선을 선점하는 뱅가드입니다.", "Vanguards who arrive first by vehicle and take the line before the enemy does."),
    "mechanized": ("vanguard", "기수", "Standard Bearer", BN,
                   "장갑 차량으로 포화 속에서도 깃발을 세워 전선을 붙듭니다.", "Carried by armoured vehicles, they plant the standard and hold the line under fire."),
    "recon": ("vanguard", "에이전트", "Agent", CO,
              "앞서 나가 지형과 적의 움직임을 살피고, 부대가 주도권을 잡을 길을 엽니다.",
              "Scouts ahead to read the ground and the enemy, opening the way for the division to take the initiative."),
    "mot_recon": ("vanguard", "전술가", "Tactician", CO,
                  "차량으로 빠르게 움직이며 전선을 먼저 차지할 자리를 찾고 증원을 부릅니다.",
                  "Moves fast by vehicle to find the ground the line should seize first, and calls in reinforcements."),
    "infantry": ("guard", "드레드노트", "Dreadnought", BN,
                 "전선에서 맞서 싸우는 주력 오퍼레이터 부대입니다.", "The main body of operators who meet the enemy on the line."),
    "mountaineers": ("guard", "소드마스터", "Swordmaster", BN,
                     "험한 지형에서 싸우도록 훈련받은 정예 가드입니다.", "Elite Guards trained to fight in rough country."),
    "light_armor": ("defender", "프로텍터", "Protector", BN,
                    "가벼운 장갑을 두른 디펜더입니다. 빠르지만 오래 버티지는 못합니다.", "Defenders in light armour. Quick, but they cannot hold for long."),
    "medium_armor": ("defender", "저거너트", "Juggernaut", BN,
                     "두꺼운 장갑으로 전선을 받아 내는 디펜더 주력입니다.", "The main Defender force, holding the line behind heavy plating."),
    "heavy_armor": ("defender", "포트리스", "Fortress", BN,
                    "가장 두꺼운 장갑을 두르고 멀리서 포격하는 디펜더입니다. 느리지만 쉽게 뚫리지 않습니다.",
                    "Defenders in the thickest armour who bombard from afar. Slow, and very hard to break."),
    "artillery_brigade": ("sniper", "포격사수", "Artilleryman", BN,
                          "멀리서 넓은 범위를 포격합니다.", "Bombards a wide area from afar."),
    "artillery": ("sniper", "포격사수", "Artilleryman", SUP, "사단을 포격으로 지원합니다.", "Supports the division with bombardment."),
    "mot_artillery_brigade": ("sniper", "포격사수", "Artilleryman", MOT,
                              "차량으로 포를 끌어 빠르게 자리를 옮깁니다.", "Tows its guns by vehicle to shift position quickly."),
    "anti_air_brigade": ("sniper", "명사수", "Marksman", BN, "하늘의 적을 먼저 노립니다.", "Aims at enemies in the air first."),
    "anti_air": ("sniper", "명사수", "Marksman", SUP, "사단 위의 하늘을 지킵니다.", "Guards the sky above the division."),
    "mot_anti_air_brigade": ("sniper", "명사수", "Marksman", MOT, "차량으로 움직이며 하늘의 적을 노립니다.", "Moves by vehicle and aims at enemies in the air."),
    "anti_tank_brigade": ("caster", "코어 캐스터", "Core Caster", BN,
                          "아츠로 장갑을 꿰뚫습니다.", "Pierces armour with Arts."),
    "anti_tank": ("caster", "코어 캐스터", "Core Caster", SUP, "아츠로 사단 앞의 장갑을 꿰뚫습니다.", "Pierces the armour in front of the division with Arts."),
    "mot_anti_tank_brigade": ("caster", "코어 캐스터", "Core Caster", MOT, "차량으로 움직이며 아츠로 장갑을 꿰뚫습니다.", "Moves by vehicle and pierces armour with Arts."),
    "tu_arts_caster": ("caster", "스플래시 캐스터", "Splash Caster", BN,
                       "오리지늄 아츠로 장갑을 꿰뚫고 보병까지 휩쓰는 술사 부대입니다. 일반 캐스터보다 폭이 넓고 훈련이 오래 걸립니다.",
                       "Casters whose Originium Arts pierce armour and sweep infantry alike. Wider than regular Casters and slower to train."),
    "rocket_artillery_brigade": ("caster", "블래스트 캐스터", "Blast Caster", BN,
                                 "긴 직선 범위를 아츠 로켓으로 휩씁니다.", "Sweeps a long line with Arts rockets."),
    "rocket_artillery": ("caster", "블래스트 캐스터", "Blast Caster", SUP, "아츠 로켓으로 사단을 지원합니다.", "Supports the division with Arts rockets."),
    "field_hospital": ("medic", "멀티 타겟 메딕", "Multi-target Medic", CO,
                       "쓰러진 병사 여럿을 한꺼번에 치료해 전선으로 돌려보냅니다.", "Treats many of the fallen at once and sends them back to the line."),
    "signal_company": ("supporter", "음유시인", "Bard", CO,
                       "부대 안의 연락을 맡아 사기를 북돋우고 작전 계획을 앞당깁니다.", "Keeps the division in contact, lifts its spirits and speeds up its plans."),
    "maintenance_company": ("supporter", "기능공", "Artificer", CO,
                            "장비를 고치고 지원 장치를 다룹니다.", "Repairs equipment and handles support devices."),
    "paratrooper": ("specialist", "처형자", "Executor", BN,
                    "적의 후방으로 침투해 전선을 흔들고 빠르게 다시 투입됩니다.", "Slips behind enemy lines, shakes the front and redeploys fast."),
    "military_police": ("specialist", "매복자", "Ambusher", CO,
                        "점령지를 안정시키고 후방의 위협을 찾아냅니다.", "Keeps occupied ground quiet and hunts threats in the rear."),
    "engineer": ("specialist", "함정술사", "Trapmaster", CO,
                 "함정과 진지를 만들어 부대가 버티도록 돕습니다.", "Builds traps and works so the division can hold."),
    "logistics_company": ("specialist", "상인", "Merchant", CO,
                          "물자를 구해 나누어 보급 소모를 줄입니다.", "Finds and distributes materiel to reduce supply use."),
}
CLASS_OF = {u: v[0] for u, v in UNITS.items()}
# 지원 중대 rocket_artillery 는 기술 rocket_artillery ("아츠 로켓")와 이름 키가 같다. 이름을 따로 줄 수 없어 쓰지 않는다
# (게임에서는 기술과 지원 중대가 모두 "아츠 로켓"으로 보인다). 포지션 아이콘은 캐스터를 쓴다.
SHARED_KEY = {"rocket_artillery"}
# 바다를 못 써서 연구할 수 없는 병종: 예전 이름을 그대로 둔다
EXTRA = {"korean": [(" marine", "상륙 가드 대대"), (" marine_desc", "물을 건너 해안을 빼앗도록 훈련받은 가드 부대입니다.")],
         "english": [(" marine", "Landing Guard Battalion"), (" marine_desc", "Guards trained to cross water and take a shore.")]}


def name(unit, lang):
    cls, bko, ben, kind, _, _ = UNITS[unit]
    i = 0 if lang == "korean" else 1
    branch = (bko, ben)[i]
    head = "" if cls in ("caster", "medic") else CLASS[cls][i] + " "
    return "%s%s %s" % (head, branch, kind[i])


def main():
    for lang in ("korean", "english"):
        lines = ["l_%s:" % lang, " # generated by tools/unit_names.py (spec 73)"]
        for unit, v in UNITS.items():
            if unit in SHARED_KEY:
                continue
            lines.append(' %s:0 "%s"' % (unit, name(unit, lang)))
            lines.append(' %s_desc:0 "%s"' % (unit, v[4] if lang == "korean" else v[5]))
        lines += ['%s:0 "%s"' % kv for kv in EXTRA[lang]]
        (LOC / lang / "replace" / ("tu_units_l_%s.yml" % lang)).write_bytes(("\n".join(lines) + "\n").encode("utf-8-sig"))
    print("UNIT_NAMES units=%d" % len(UNITS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
