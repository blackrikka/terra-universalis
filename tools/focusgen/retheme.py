#!/usr/bin/env python3
"""기존 중점 트리 조각의 보상을 중점 이름에 맞게 바꾼다 (사양서 16).

사용법 (python -I):
    python -I tools/focusgen/retheme.py [--tag YAN] [--dry]

completion_reward의 맨 위 단계 문장 중 '일반 보상'(정치력·안정도·전쟁 지지·경험치·인력·연구 보너스·교리 할인)을 지우고,
중점 영어 이름에서 정한 테마 보상(theme_effects.py)을 넣는다. 그 밖의 문장(깃발, 이벤트, 이념, 인물, 국민정신,
건설 TU_build_*, if 블록 등)은 그대로 둔다. 같은 중점을 다시 돌려도 결과가 같다.
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from theme_effects import theme_of, reward_lines  # noqa: E402

REPO = HERE.parents[1]
LOC_EN = REPO / "terra_universalis" / "localisation" / "english"
# 사용자가 효과를 직접 정한 중점: 다시 쓰지 않는다
PRESERVE = {"TU_YAN_p1_throne_root", "TU_YAN_p1_depose_root"}
GENERIC = {"add_political_power", "add_stability", "add_war_support", "army_experience", "navy_experience",
           "air_experience", "add_manpower", "add_tech_bonus", "add_doctrine_cost_reduction"}


def load_loc():
    loc = {}
    for f in LOC_EN.rglob("*.yml"):
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r'\s(\S+?):\d*\s+"(.*)"', line)
            if m:
                loc[m.group(1)] = m.group(2)
    return loc


def split_statements(body):
    """중괄호 깊이 0의 문장 목록 [(key, text)]. 주석은 (None, text)."""
    out = []
    i, n = 0, len(body)
    while i < n:
        while i < n and body[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        if body[i] == "#":
            j = body.find("\n", i)
            j = n if j < 0 else j
            out.append((None, body[i:j]))
            i = j
            continue
        m = re.compile(r"([^\s=#{}]+)\s*=\s*").match(body, i)
        if not m:
            raise ValueError("parse error near: %r" % body[i:i + 60])
        key = m.group(1)
        j = m.end()
        if body[j] == "{":
            d = 0
            k = j
            while True:
                if body[k] == "{":
                    d += 1
                elif body[k] == "}":
                    d -= 1
                    if d == 0:
                        break
                k += 1
            end = k + 1
        elif body[j] == '"':
            end = body.index('"', j + 1) + 1
        else:
            mm = re.compile(r"[^\s{}#]+").match(body, j)
            end = mm.end()
        out.append((key, body[i:end]))
        i = end
    return out


def rewrite_block(block, loc, stats):
    fid = re.search(r"\n\t\tid = (\S+)", block).group(1)
    if fid in PRESERVE:
        return block
    cm = re.search(r"\n\t\tcost = (\d+)", block)
    cost = int(cm.group(1)) if cm else 10
    i = block.find("\t\tcompletion_reward = {")
    if i < 0:
        return block
    j = block.index("{", i)
    d = 0
    k = j
    while True:
        if block[k] == "{":
            d += 1
        elif block[k] == "}":
            d -= 1
            if d == 0:
                break
        k += 1
    body = block[j + 1:k]
    stmts = split_statements(body)
    keep = [t for key, t in stmts if key not in GENERIC]
    theme = theme_of(loc.get(fid, ""))
    stats[theme] += 1
    new = keep + reward_lines(theme, fid, cost)
    # 여러 줄 문장은 원래 들여쓰기를 그대로 가지고 있다 (첫 줄만 앞 공백이 빠짐)
    new_body = "\n" + "".join("\t\t\t%s\n" % x.rstrip() for x in new) + "\t\t"
    return block[:j + 1] + new_body + block[k:]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args(argv)
    loc = load_loc()
    stats = Counter()
    folders = [HERE / args.tag.lower()] if args.tag else sorted(p for p in HERE.iterdir() if p.is_dir() and not p.name.startswith("_"))
    n = 0
    for folder in folders:
        for f in sorted(folder.glob("*.txt")):
            if f.name == "_header.txt":
                continue
            s = f.read_text(encoding="utf-8")
            parts = re.split(r"(?=\n\tfocus = \{\n)", s)
            out = [parts[0]] + [rewrite_block(b, loc, stats) for b in parts[1:]]
            n += len(parts) - 1
            if not args.dry:
                f.write_text("".join(out), encoding="utf-8")
    print("RETHEME focuses=%d %s" % (n, dict(stats.most_common())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
