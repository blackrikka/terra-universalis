#!/usr/bin/env python3
"""테라 자원 이름 (사양서 57).

바닐라 자원 키는 그대로 두고 화면에 보이는 이름만 바꾼다:
    oil 오리지늄 / steel 오리론 / rubber 폴리에스테르 / aluminium 아케톤 / tungsten 망간 / chromium 장치
1) localisation/<언어>/replace/tu_resources_l_<언어>.yml  자원 이름
2) 다른 로컬라이제이션 문장 안의 옛 자원 이름(석유, 철강, Steel ...)을 새 이름으로 바꾼다.
   생성기(focusgen, techgen 등)를 다시 돌리면 옛 이름이 돌아오므로 그 뒤에 이 도구도 다시 돌린다 (다시 돌려도 같다).

사용법 (python -I):  python -I tools/resource_names.py
"""

import re
import sys
from pathlib import Path

LOC = Path(__file__).resolve().parents[1] / "terra_universalis" / "localisation"
NAMES = {
    "korean": {"oil": "오리지늄", "steel": "오리론", "rubber": "폴리에스테르", "aluminium": "아케톤", "tungsten": "망간", "chromium": "장치"},
    "english": {"oil": "Originium", "steel": "Oriron", "rubber": "Polyester", "aluminium": "Aketon", "tungsten": "Manganese", "chromium": "Device"},
}
# 한국어: 순서대로 (긴 것 먼저). 강철은 자원을 뜻할 때만 (강철 갑주·강철 석궁 같은 이름은 그대로)
KO = [("텅스텐 2(오리지늄 대용)", "오리지늄 2"), ("석유가", "오리지늄이"), ("석유", "오리지늄"),
      ("합성 고무", "합성 폴리에스테르"), (re.compile(r"고무(?![한하시되])"), "폴리에스테르"),
      ("철강", "오리론"), ("텅스텐", "망간"), ("크롬", "장치"), ("알루미늄", "아케톤"),
      ("강철 광상", "오리론 광상"), ("강철을 얻는다", "오리론을 얻는다"), ("강철 수출", "오리론 수출"),
      ("강철 비축", "오리론 비축"), ("강철 자원", "오리론 자원"), ("강철이 나온다", "오리론이 나온다")]
EN = [(r"\bOil\b", "Originium"), (r"\boil\b", "originium"), (r"\bRubber\b", "Polyester"), (r"\brubber\b", "polyester"),
      (r"\bTungsten\b", "Manganese"), (r"\btungsten\b", "manganese"), (r"\bChromium\b", "Device"), (r"\bchromium\b", "device"),
      (r"\bAluminium\b", "Aketon"), (r"\baluminium\b", "aketon"), (r"\bSteel\b", "Oriron"), (r"\bsteel\b", "oriron")]
EN_KEEP_KEY = re.compile(r"armour|standards|infantry_weapons2|ev\.7|olive|serpent_march")
LINE = re.compile(r'(\s*[\w.\-]+:\d*\s*")(.*)("\s*(#.*)?)$')


def fix_value(lang, v):
    if lang == "korean":
        for a, b in KO:
            v = a.sub(b, v) if hasattr(a, "sub") else v.replace(a, b)
    else:
        for a, b in EN:
            v = re.sub(a, b, v)
    return v


def main():
    n = 0
    for lang in NAMES:
        for f in sorted((LOC / lang).rglob("*.yml")):
            if f.name.startswith("tu_resources_"):
                continue
            raw = f.read_text(encoding="utf-8-sig")
            out = []
            for line in raw.split("\n"):
                m = LINE.match(line)
                if m and not (lang == "english" and EN_KEEP_KEY.search(line.split(":")[0])):
                    v = fix_value(lang, m.group(2))
                    if v != m.group(2):
                        n += 1
                        line = m.group(1) + v + m.group(3)
                out.append(line)
            new = "\n".join(out)
            if new != raw:
                f.write_text("﻿" + new, encoding="utf-8")
        lines = ["l_%s:" % lang, " # 사양서 57: 테라 전략 자원 (내부 키는 바닐라, tools/resource_names.py)"]
        for k, v in NAMES[lang].items():
            for key in (k, k.upper(), "PRODUCTION_MATERIAL_%s" % k.upper(), "%s_resource" % k):
                lines.append(' %s:0 "%s"' % (key, v))
        (LOC / lang / "replace" / ("tu_resources_l_%s.yml" % lang)).write_text("﻿" + "\n".join(lines) + "\n", encoding="utf-8")
    print("RESOURCE_NAMES lines=%d" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
