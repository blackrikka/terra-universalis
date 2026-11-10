#!/usr/bin/env python3
"""대국 트리(손으로 쓴 조각)의 무역 중점에 무역 보상을 더한다 (사양서 75).

소국 13개는 content/<tag>.py -> content_lib 가 theme_effects.reward_lines 로 보상을 만들므로 다시 생성하면 된다.
대국 7개(URS VIC YAN KZD RHO LGM REU)는 조각 파일이 원본이라, 테마가 trade 인 중점만 골라 고친다:
    교역·수출·시장 중점: theme_effects.trade_extras 의 줄 가운데 아직 없는 것을 completion_reward 끝에 더한다
    투자·차관 중점:      산업 연구 보너스(범주가 industry 하나뿐인 add_tech_bonus)를 영토 밖 민간 공장 +1 로 바꾼다
다른 문장은 건드리지 않는다. 다시 돌려도 같다. 그다음 merge_focus.py --tag <TAG>.

사용법 (python -I):  python -I tools/focusgen/trade_focuses.py [--dry]
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import theme_effects as T  # noqa: E402
from retheme import load_loc, split_statements  # noqa: E402

MAJORS = ["URS", "VIC", "YAN", "KZD", "RHO", "LGM", "REU"]


def norm(x):
    return re.sub(r"\s+", " ", x).strip()


def rewrite_block(block, loc, log):
    fid = re.search(r"\n\t\tid = (\S+)", block).group(1)
    name = loc.get(fid, "")
    if T.theme_of(name) != "trade":
        return block
    kind = T.trade_kind(name)
    if kind == "finance":
        return block
    cm = re.search(r"\n\t\tcost = (\d+)", block)
    cost = int(cm.group(1)) if cm else 10
    i = block.find("\t\tcompletion_reward = {")
    if i < 0:
        return block
    j = block.index("{", i)
    d, k = 0, j
    while True:
        d += (block[k] == "{") - (block[k] == "}")
        if d == 0:
            break
        k += 1
    stmts = [t for _, t in split_statements(block[j + 1:k])]
    have = {norm(t) for t in stmts}
    new = list(stmts)
    if kind == "invest":
        if norm(T.OFFSITE) not in have:
            new = [t for t in new if not re.fullmatch(r"add_tech_bonus = \{ name = \S+ bonus = \S+ uses = \d+ category = industry \}", norm(t))]
            new.append(T.OFFSITE)
    else:
        for line in T.trade_extras(name, fid, cost):
            if norm(line) not in have:
                new.append(line)
    if new == stmts:
        return block
    log.append((fid, name, kind, len(new) - len(stmts)))
    body = "\n" + "".join("\t\t\t%s\n" % x.rstrip() for x in new) + "\t\t"
    return block[:j + 1] + body + block[k:]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    loc = load_loc()
    total = 0
    for tag in MAJORS:
        log = []
        for f in sorted((HERE / tag.lower()).glob("*.txt")):
            if f.name == "_header.txt":
                continue
            s = f.read_text(encoding="utf-8")
            parts = re.split(r"(?=\n\tfocus = \{\n)", s)
            out = [parts[0]] + [rewrite_block(b, loc, log) for b in parts[1:]]
            if not a.dry and "".join(out) != s:
                f.write_text("".join(out), encoding="utf-8")
        total += len(log)
        print("%s: %d  %s" % (tag, len(log), ", ".join("%s(%s)" % (n, k) for _, n, k, _ in log[:8])))
    print("TRADE_FOCUSES changed=%d%s" % (total, " (dry)" if a.dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
