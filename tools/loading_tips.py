#!/usr/bin/env python3
"""로딩 화면 대사 (사양서 26).

사용법:  python -I tools/loading_tips.py

로딩 화면은 LOADING_TIP_0, 1, 2 … 키를 무작위로 보여 준다. 바닐라 대사가 섞이지 않도록 LOADING_TIP_0 ~ 299 를
아래 TIPS 를 돌아가며 채워 replace 로컬라이제이션(한국어·영어)에 쓴다. 대사를 더하거나 고치려면 TIPS 만 고친다.
형식: (한국어 대사, 한국어 출처, 영어 대사, 영어 출처). 대사 안 줄바꿈은 \\n.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "terra_universalis"
COUNT = 300

TIPS = [
    ("내게는 고통밖에 없습니다.\\n그것 말고는 아무것도 바라지 않습니다.", "롤랑, 「고통을 사랑하기 위한 기도」",
     "I have nothing but pain.\\nI desire nothing else.", "Roland, 'A Prayer to Love Pain'"),
    ("감염자도 사람입니다. 그 당연한 말을 하기 위해, 우리는 얼마나 멀리 걸어야 할까요.", "아미야, 로도스 아일랜드",
     "The infected are people too. How far must we walk just to say something so obvious?", "Amiya, Rhodes Island"),
    ("희망은 약이 아니다. 하지만 약을 끝까지 만들게 하는 것은 희망이다.", "켈시",
     "Hope is not a cure. But hope is what makes us finish the cure.", "Kal'tsit"),
    ("얼음은 녹는다. 그러나 녹은 물이 어디로 흐를지는 우리가 정한다.", "프로스트노바",
     "Ice melts. But where the water flows is ours to decide.", "FrostNova"),
    ("용문은 누구의 편도 아니다. 용문은 용문의 편이다.", "웨이옌우",
     "Lungmen takes no one's side. Lungmen takes Lungmen's side.", "Wei Yenwu"),
    ("왕관은 무겁지 않다. 무거운 것은 그 아래에서 죽어 간 자들의 이름이다.", "테레시스",
     "The crown is not heavy. What is heavy are the names of those who died beneath it.", "Theresis"),
    ("기사의 명예는 광고판 위가 아니라 무너진 성벽 아래에서 빛난다.", "마거릿 니어",
     "A knight's honour shines not on a billboard, but beneath a fallen wall.", "Margaret Nearl"),
    ("바다는 아무것도 잊지 않아. 그러니까 박사도 나를 잊지 마.", "스카디",
     "The sea forgets nothing. So don't you forget me either, Doctor.", "Skadi"),
    ("천재는 예고 없이 오지 않는다. 다만 아무도 예보를 믿지 않을 뿐이다.", "천재 신사의 일지",
     "Catastrophes never come unannounced. It is only that no one believes the forecast.", "Journal of a Catastrophe Messenger"),
    ("원석은 도시를 움직이고, 사람을 멈추게 한다.", "림 빌리튼 광산 표어",
     "Originium moves cities and stops people.", "Rim Billiton mine slogan"),
    ("바다를 등진 나라는 있어도, 바다를 잊은 나라는 없다.", "이베리아 대심판소 기록",
     "A nation may turn its back on the sea, but none ever forgets it.", "Records of the Iberian Inquisition"),
    ("총을 쥐는 것은 손이지만, 방아쇠를 당기는 것은 헤일로다.", "라테라노 속담",
     "The hand holds the gun, but the halo pulls the trigger.", "Lateran proverb"),
    ("이동도시는 멈추는 순간 무덤이 된다.", "우르수스 황야 상인의 말",
     "A mobile city becomes a tomb the moment it stops.", "Saying of an Ursine wasteland trader"),
    ("책장을 넘기는 손이 떨린다면, 그건 아직 읽을 이유가 남아 있다는 뜻이다.", "도서관의 사서",
     "If your hand trembles as you turn the page, you still have a reason to read on.", "A librarian"),
    ("보급이 끊긴 기사는 그저 무거운 갑옷일 뿐이다.", "카시미어 참모 교범",
     "A knight cut off from supply is merely heavy armour.", "Kazimierz staff manual"),
    ("황야에서는 지도가 아니라 바람이 길을 알려 준다.", "사르곤 사막 기병의 격언",
     "In the wastes, it is the wind, not the map, that shows the way.", "Saying of the Sargon desert riders"),
]


def main():
    for lang, qi, si in (("korean", 0, 1), ("english", 2, 3)):
        lines = ["l_%s:" % lang]
        for n in range(COUNT):
            t = TIPS[n % len(TIPS)]
            text = "%s\\n- %s" % (t[qi], t[si])
            lines.append(' LOADING_TIP_%d:0 "%s"' % (n, text.replace('"', '\\"')))
        out = MOD / "localisation" / lang / "replace" / ("tu_loading_tips_l_%s.yml" % lang)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(("﻿" + "\n".join(lines) + "\n").encode("utf-8"))
    print("LOADING_TIPS %d keys from %d quotes" % (COUNT, len(TIPS)))


if __name__ == "__main__":
    main()
