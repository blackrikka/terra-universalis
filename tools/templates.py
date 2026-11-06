#!/usr/bin/env python3
"""기본 편제(사단 틀) 통일 (사양서 44).

전투 폭을 네 단계로 맞춘다 (보병·기병·경전차 2, 포병 3):
    10폭  정예·특수 (근위대, 오퍼레이터, 심판관, 기사, 용병, 분파 근위대)
    20폭  주력 보병 (모든 나라의 기본 보병 사단)
    30폭  중육상함 전대 / 40폭 도시급 육상함
TEMPLATES: 이름 -> ([(연대 종류, 수), ...], [지원 중대, ...])
apply_text(text) 가 division_template 블록을 이름으로 찾아 regiments / support 를 바꾼다 (다시 돌려도 같다).
이름이 TU_<TAG>_line_infantry 인 틀은 LINE 을 쓴다 (tiers.py 가 만드는 나라별 기본 보병).

사용법 (모드 전체, python -I):  python -I tools/templates.py
tiers.py (history/units) 와 content_lib.py (나라별 효과 파일)도 쓰기 전에 부른다.
"""

import re
import sys
from pathlib import Path

WIDTH = {"infantry": 2, "cavalry": 2, "light_armor": 2, "artillery_brigade": 3, "motorized": 2}

LINE = ([("infantry", 7), ("artillery_brigade", 2)], ["engineer", "recon"])               # 20폭
TEMPLATES = {
    # 나라별 주력 보병 (손으로 만든 OOB) — 20폭
    "TU_URS_infantry": ([("infantry", 7), ("artillery_brigade", 2)], ["engineer", "artillery"]),
    "TU_VIC_line_infantry": ([("infantry", 7), ("artillery_brigade", 2)], ["engineer", "artillery"]),
    "TU_YAN_infantry": ([("infantry", 7), ("artillery_brigade", 2)], ["engineer", "recon"]),
    "TU_KZD_infantry": ([("infantry", 7), ("artillery_brigade", 2)], ["recon"]),
    # 정예 — 20폭
    "TU_URS_guard_division": ([("infantry", 4), ("cavalry", 2), ("light_armor", 1), ("artillery_brigade", 2)], ["engineer", "recon"]),
    "TU_KZD_elite_guard": ([("infantry", 5), ("cavalry", 2), ("artillery_brigade", 2)], ["recon"]),
    # 정예·특수 — 10폭
    "TU_VIC_steam_knight": ([("infantry", 2), ("light_armor", 3)], ["engineer"]),
    "TU_LGM_guard": ([("infantry", 5)], ["engineer"]),
    "TU_RHO_operator_squad": ([("infantry", 5)], ["recon"]),
    "TU_RHO_escort": ([("infantry", 5)], []),
    "TU_COL_blacksteel": ([("infantry", 5)], []),
    "TU_IBE_inquisitors": ([("infantry", 5)], []),
    "TU_KAZ_knights": ([("cavalry", 4), ("infantry", 1)], []),
    "TU_LAT_guard": ([("infantry", 5)], []),
    "TU_SAR_mercs": ([("infantry", 3), ("cavalry", 2)], []),
    "TU_YAN_faction_guard": ([("infantry", 5)], []),
    # 육상함 — 20 / 30 / 40폭
    "Light Landship Squadron": ([("infantry", 4), ("artillery_brigade", 4)], ["engineer", "recon"]),
    "Heavy Landship Squadron": ([("infantry", 6), ("artillery_brigade", 6)], ["engineer", "recon"]),
    "City-Class Landship": ([("infantry", 8), ("artillery_brigade", 8)], ["engineer", "recon", "artillery"]),
}
LINE_RE = re.compile(r"^TU_[A-Z]{3}_line_infantry$")


def width(regs):
    return sum(WIDTH[t] * n for t, n in regs)


def regiments_text(regs, ind):
    """종류마다 열을 따로, 한 열에 5개까지."""
    lines, x = [], 0
    for t, n in regs:
        for i in range(n):
            lines.append("%s%s = { x = %d y = %d }" % (ind, t, x + i // 5, i % 5))
        x += (n + 4) // 5
    return "\n".join(lines)


def support_text(sup, ind):
    return "\n".join("%s%s = { x = 0 y = %d }" % (ind, s, i) for i, s in enumerate(sup))


def _block(s, i):
    j = s.index("{", i)
    d, k = 0, j
    while True:
        d += {"{": 1, "}": -1}.get(s[k], 0)
        if d == 0:
            return j, k
        k += 1


def spec_for(name):
    if name in TEMPLATES:
        return TEMPLATES[name]
    if LINE_RE.match(name):
        return LINE
    return None


def apply_text(text):
    out, pos, n = [], 0, 0
    for m in re.finditer(r"division_template\s*=\s*\{", text):
        if m.start() < pos:
            continue
        j, k = _block(text, m.start())
        body = text[j + 1:k]
        nm = re.search(r'name\s*=\s*\\?"([^"\\]+)\\?"', body)
        spec = spec_for(nm.group(1)) if nm else None
        if not spec:
            continue
        regs, sup = spec
        new = body
        rm = re.search(r"\n([ \t]*)regiments\s*=\s*\{", new)
        if rm:
            a, b = _block(new, rm.start(1) + len(rm.group(1)))
            new = new[:a + 1] + "\n" + regiments_text(regs, rm.group(1) + "\t") + "\n" + rm.group(1) + new[b:]
        sm = re.search(r"\n([ \t]*)support\s*=\s*\{", new)
        if sm:
            a, b = _block(new, sm.start(1) + len(sm.group(1)))
            if sup:
                new = new[:a + 1] + "\n" + support_text(sup, sm.group(1) + "\t") + "\n" + sm.group(1) + new[b:]
            else:
                e = b + 1
                new = new[:sm.start()] + new[e:]
        elif sup and rm:
            a, b = _block(new, rm.start(1) + len(rm.group(1)))
            ind = rm.group(1)
            new = new[:b + 1] + "\n%ssupport = {\n%s\n%s}" % (ind, support_text(sup, ind + "\t"), ind) + new[b + 1:]
        if new != body:
            n += 1
        out.append(text[pos:j + 1])
        out.append(new)
        pos = k
    out.append(text[pos:])
    return "".join(out), n


def apply_file(path):
    p = Path(path)
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    s = raw.decode("utf-8-sig")
    crlf = "\r\n" in s
    t, n = apply_text(s.replace("\r\n", "\n"))
    if n:
        if crlf:
            t = t.replace("\n", "\r\n")
        p.write_bytes((("﻿" if bom else "") + t).encode("utf-8"))
    return n


def main():
    mod = Path(__file__).resolve().parents[1] / "terra_universalis"
    total = 0
    for p in sorted(list((mod / "history" / "units").glob("*.txt")) + list((mod / "common").rglob("*.txt"))):
        n = apply_file(p)
        if n:
            print("%2d %s" % (n, p.relative_to(mod)))
        total += n
    for name, (regs, _) in TEMPLATES.items():
        assert width(regs) in (10, 20, 30, 40), (name, width(regs))
    assert width(LINE[0]) == 20
    print("TEMPLATES changed=%d" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
