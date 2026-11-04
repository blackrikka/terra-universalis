#!/usr/bin/env python3
"""중점 훅 (사양서 23): 합친 중점 파일의 completion_reward 끝에 지도자 교체 · 국호 변경을 넣는다.
데이터는 tools/chargen/data.py 의 hooks. merge_focus.py 가 합친 뒤(자동 배치 전에) 부른다.

    ("leader", 캐릭터, 이념)          recruit_character + promote_character
    ("leader_existing", 캐릭터 id, 이념)  이미 정의된 캐릭터 (예: 테레시스)
    ("name", 키, …)                    set_cosmetic_tag = TU_<TAG>_<키>
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "chargen"))
from data import COUNTRIES  # noqa: E402


def lines_for(tag, actions):
    out = []
    for a in actions:
        if a[0] in ("leader", "leader_existing"):
            c = a[1] if a[0] == "leader_existing" else "TU_%s_%s" % (tag, a[1])
            out += ["recruit_character = %s" % c,
                    "promote_character = {\n\tcharacter = %s\n\tideology = %s\n}" % (c, a[2])]
        elif a[0] == "name":
            out.append("set_cosmetic_tag = TU_%s_%s" % (tag, a[1]))
    return out


def apply(path, tag):
    d = COUNTRIES.get(tag)
    if not d or not d["hooks"]:
        return 0, []
    text = Path(path).read_text(encoding="utf-8")
    done, missing = 0, []
    for sid, actions in d["hooks"].items():
        fid = "TU_%s_%s" % (tag, sid)
        m = re.search(r"\n\tfocus = \{\r?\n\t\tid = %s\r?\n" % re.escape(fid), text)
        if not m:
            missing.append(fid)
            continue
        i = text.find("completion_reward = {", m.end())
        j, depth = text.index("{", i), 0
        k = j
        while True:
            if text[k] == "{":
                depth += 1
            elif text[k] == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        nl = "\r\n" if "\r\n" in text[i:k] else "\n"
        add = "".join(nl + "\t\t\t" + l.replace("\n", nl + "\t\t\t") for l in lines_for(tag, actions))
        body = text[j + 1:k].rstrip()
        text = text[:j + 1] + body + nl + "\t\t\t# spec 23 hooks" + add + nl + "\t\t" + text[k:]
        done += 1
    Path(path).write_text(text, encoding="utf-8", newline="")
    return done, missing
