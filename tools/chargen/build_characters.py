#!/usr/bin/env python3
"""나라별 캐릭터 · 참모 특성 · 국호(코스메틱 태그) 생성 (사양서 23). 데이터는 data.py.

사용법:  python -I tools/chargen/build_characters.py   (그다음 merge_focus 로 중점에 훅을 넣고 build_countries 를 돌린다)

만드는 파일
    common/characters/<TAG>.txt            cast 나라 (일반 지도자 대신 전체)
    common/characters/TU_<TAG>_cast.txt    기존 대국 보강
    common/country_leader/tu_advisor_traits.txt
    tools/mapgen/char_history/<TAG>.txt    시작 영입 (build_countries 가 history 에 붙인다)
    gfx/flags/{,medium/,small/}TU_<TAG>_<KEY>.tga   국호 깃발 (원래 깃발 복사)
    localisation/{korean,english}/tu_cast_l_*.yml
    tools/mapgen/terra/countries.json 의 cast 표시
중점 훅(지도자 교체·국호)은 tools/focusgen/focus_hooks.py 가 merge_focus 때 넣는다.
"""

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from data import COUNTRIES, TRAITS, COSMETIC_COLORS  # noqa: E402
from leader_traits import LEADER_TRAITS, ASSIGN  # noqa: E402
import re  # noqa: E402

REPO = HERE.parents[1]
MOD = REPO / "terra_universalis"
IDEOLOGY_SUFFIXES = ["", "_neutrality", "_democratic", "_fascism", "_communism"]


def cid(tag, sid):
    return "TU_%s_%s" % (tag, sid)


def char_text(tag, sid, ko, en, roles, portrait):
    c = cid(tag, sid)
    L = ["\t%s = {" % c, "\t\tname = %s" % c]
    if portrait:
        L.append('\t\tportraits = {\n\t\t\tcivilian = { large = "%s" }\n\t\t\tarmy = { large = "%s" }\n\t\t}' % (portrait, portrait))
    for r in roles:
        if r[0] == "L":
            tr = "\n\t\t\ttraits = { %s }" % " ".join(ASSIGN[c]) if c in ASSIGN else ""
            L.append('\t\tcountry_leader = {\n\t\t\tideology = %s%s\n\t\t\texpire = "1200.1.1.1"\n\t\t\tid = -1\n\t\t}' % (r[1], tr))
        elif r[0] == "A":
            ledger = "\n\t\t\tledger = army" if r[1] in ("high_command", "theorist") else ""
            L.append("\t\tadvisor = {\n\t\t\tslot = %s\n\t\t\tidea_token = %s_adv%s\n\t\t\tallowed = {\n\t\t\t\toriginal_tag = %s\n\t\t\t}\n"
                     "\t\t\ttraits = { %s }\n\t\t\tcost = 150\n\t\t\tai_will_do = {\n\t\t\t\tfactor = 1\n\t\t\t}\n\t\t}"
                     % (r[1], c, ledger, tag, r[2]))
        elif r[0] in ("G", "M"):
            role = "corps_commander" if r[0] == "G" else "field_marshal"
            atk, dfn, pln, lg = r[1:5]
            L.append("\t\t%s = {\n\t\t\ttraits = { }\n\t\t\tskill = %d\n\t\t\tattack_skill = %d\n\t\t\tdefense_skill = %d\n"
                     "\t\t\tplanning_skill = %d\n\t\t\tlogistics_skill = %d\n\t\t\tlegacy_id = -1\n\t\t}"
                     % (role, max(1, round((atk + dfn + pln + lg) / 4)), atk, dfn, pln, lg))
    L.append("\t}")
    return "\n".join(L)


def patch_existing_leaders():
    """모든 캐릭터 파일에서 ASSIGN 에 있는 캐릭터의 country_leader 블록에 traits 를 넣는다 (있으면 바꾼다).
    반환: 찾은 캐릭터 id 집합."""
    found = set()
    for f in (MOD / "common" / "characters").glob("*.txt"):
        s = f.read_text(encoding="utf-8-sig")
        orig = s
        for cid_, traits in ASSIGN.items():
            m = re.search(r"\n\t%s = \{" % re.escape(cid_), s)
            if not m:
                continue
            found.add(cid_)
            i = s.find("country_leader", m.end())
            j = s.index("{", i)
            d, k = 0, j
            while True:
                d += {"{": 1, "}": -1}.get(s[k], 0)
                if d == 0:
                    break
                k += 1
            inner = re.sub(r"\s*traits\s*=\s*\{[^}]*\}", "", s[j + 1:k])
            inner = " traits = { %s }" % " ".join(traits) + inner
            s = s[:j + 1] + inner + s[k:]
        if s != orig:
            f.write_text(s, encoding="utf-8")
    return found


def apply_cast_portraits():
    """사양서 39: tools/portraits/cast_portraits.json 의 캐릭터에 명일방주 일러스트 초상화를 건다 (모든 캐릭터 파일).
    portraits 블록을 바꾸거나 name 줄 뒤에 넣는다. 반환: 바꾼 캐릭터 수."""
    sys.path.insert(0, str(REPO / "tools" / "portraits"))
    from build_cast_portraits import sprite  # noqa: E402
    cast = json.loads((REPO / "tools" / "portraits" / "cast_portraits.json").read_text(encoding="utf-8"))["cast"]
    done = set()
    for f in (MOD / "common" / "characters").glob("*.txt"):
        s = f.read_text(encoding="utf-8-sig")
        orig = s
        for cid_, art in cast.items():
            m = re.search(r"\n\t%s = \{\n\t\tname = \S+\n" % re.escape(cid_), s)
            if not m:
                continue
            g = sprite(art)
            block = ('\t\tportraits = {\n\t\t\tcivilian = { large = "%s" small = "%s_small" }\n'
                     '\t\t\tarmy = { large = "%s" small = "%s_small" }\n\t\t}\n' % (g, g, g, g))
            # 이 캐릭터 블록의 끝
            j, d = s.index("{", m.start()), 0
            k = j
            while True:
                d += {"{": 1, "}": -1}.get(s[k], 0)
                if d == 0:
                    break
                k += 1
            body = s[m.end():k]
            pm = re.search(r"\t\tportraits\s*=\s*\{", body)
            if pm:
                a = m.end() + pm.start()
                b, d = s.index("{", a), 0
                e = b
                while True:
                    d += {"{": 1, "}": -1}.get(s[e], 0)
                    if d == 0:
                        break
                    e += 1
                e += 1
                if s[e:e + 1] == "\n":
                    e += 1
                s = s[:a] + block + s[e:]
            else:
                s = s[:m.end()] + block + s[m.end():]
            done.add(cid_)
        if s != orig:
            f.write_text(s, encoding="utf-8")
    missing = sorted(set(cast) - done)
    assert not missing, "portraits: character not found %s" % missing
    return len(done)


def main():
    ko, en = [], []
    cj_path = REPO / "tools" / "mapgen" / "terra" / "countries.json"
    cj = json.loads(cj_path.read_text(encoding="utf-8"))
    hist_dir = REPO / "tools" / "mapgen" / "char_history"
    hist_dir.mkdir(exist_ok=True)
    nchar = 0
    for tag, d in COUNTRIES.items():
        body = "\n\n".join(char_text(tag, *ch) for ch in d["chars"])
        txt = "# Generated by tools/chargen/build_characters.py (spec 23)\ncharacters = {\n\n%s\n}\n" % body
        name = ("%s.txt" % tag) if d["cast"] else ("TU_%s_cast.txt" % tag)
        (MOD / "common" / "characters" / name).write_text(txt, encoding="utf-8")
        nchar += len(d["chars"])
        for sid, cko, cen, roles, _ in d["chars"]:
            ko.append((cid(tag, sid), cko))
            en.append((cid(tag, sid), cen))
        (hist_dir / ("%s.txt" % tag)).write_text(
            "# %s: characters (tools/chargen/build_characters.py)\n" % tag
            + "".join("recruit_character = %s\n" % cid(tag, s) for s in d["start"]), encoding="utf-8")
        for fsid, actions in d["hooks"].items():
            for a in actions:
                if a[0] != "name":
                    continue
                cos = "TU_%s_%s" % (tag, a[1])
                for suf in IDEOLOGY_SUFFIXES:
                    ko += [(cos + suf, a[2]), (cos + suf + "_DEF", a[2]), (cos + suf + "_ADJ", a[4])]
                    en += [(cos + suf, a[3]), (cos + suf + "_DEF", "the " + a[3]), (cos + suf + "_ADJ", a[5])]
                for sub in ("", "medium/", "small/"):
                    src = MOD / "gfx" / "flags" / ("%s%s.tga" % (sub, tag))
                    if src.is_file():
                        shutil.copyfile(src, MOD / "gfx" / "flags" / ("%s%s.tga" % (sub, cos)))
        for c in cj:
            if c["tag"] == tag and d["cast"]:
                c["cast"] = True
    cj_path.write_text(json.dumps(cj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 코스메틱 태그 나라 색 (국호가 바뀌면 지도 색도 바뀐다)
    cos = ["# Generated by tools/chargen/build_characters.py: map colours of cosmetic tags (spec 29)."]
    for key, (rgb, ui) in COSMETIC_COLORS.items():
        cos.append("%s = {\n\tcolor = rgb { %d %d %d }\n\tcolor_ui = rgb { %d %d %d }\n}" % ((key,) + tuple(rgb) + tuple(ui)))
    (MOD / "common" / "countries" / "cosmetic.txt").write_text("\n".join(cos) + "\n", encoding="utf-8")

    tl = ["# Terra advisor traits (tools/chargen/build_characters.py, spec 23)", "leader_traits = {"]
    for tid, (tko, ten, sprite, mods) in TRAITS.items():
        tl.append("\t%s = {\n\t\tsprite = %d\n\t\trandom = no\n%s\n\t\tai_will_do = { factor = 1 }\n\t}"
                  % (tid, sprite, "\n".join("\t\t%s = %s" % kv for kv in mods.items())))
        ko.append((tid, tko))
        en.append((tid, ten))
    tl.append("}")
    cl = MOD / "common" / "country_leader"
    cl.mkdir(exist_ok=True)
    (cl / "tu_advisor_traits.txt").write_text("\n".join(tl) + "\n", encoding="utf-8")

    # 국가 지도자 특성 (사양서 25)
    lt = ["# Terra country leader traits (tools/chargen/leader_traits.py, spec 25)", "leader_traits = {"]
    for tid, (tko, ten, mods) in LEADER_TRAITS.items():
        lt.append("\t%s = {\n\t\trandom = no\n%s\n\t\tai_will_do = { factor = 1 }\n\t}"
                  % (tid, "\n".join("\t\t%s = %s" % kv for kv in mods.items())))
        ko.append((tid, tko))
        en.append((tid, ten))
    lt.append("}")
    (cl / "tu_leader_traits.txt").write_text("\n".join(lt) + "\n", encoding="utf-8")
    patched = patch_existing_leaders()
    nport = apply_cast_portraits()

    for lang, items in (("korean", ko), ("english", en)):
        body = "l_%s:\n" % lang + "".join(' %s:0 "%s"\n' % (k, v.replace('"', '\\"')) for k, v in items)
        (MOD / "localisation" / lang / ("tu_cast_l_%s.yml" % lang)).write_bytes(("\ufeff" + body).encode("utf-8"))
    for p in list((MOD / "common" / "characters").glob("*.txt")) + [cl / "tu_advisor_traits.txt"]:
        s = p.read_text(encoding="utf-8-sig")
        assert s.count("{") == s.count("}"), p
    missing = [c for c in ASSIGN if c not in patched]
    assert not missing, "leader traits: character not found %s" % missing
    print("CAST countries=%d characters=%d advisor traits=%d leader traits=%d (assigned %d) portraits=%d"
          % (len(COUNTRIES), nchar, len(TRAITS), len(LEADER_TRAITS), len(ASSIGN), nport))
    return 0


if __name__ == "__main__":
    sys.exit(main())
