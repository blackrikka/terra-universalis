#!/usr/bin/env python3
"""바닐라 국가·주 참조 정리 (C.3). 재실행해도 안전하다 (같은 결과를 다시 쓴다).

사용법 (python -I):
    python -I tools/vanilla_cleanup.py
    python -I tools/vanilla_cleanup.py --dry-run

하는 일:
  1. descriptor 두 곳(프로젝트 descriptor.mod, Documents의 terra_universalis.mod)에 replace_path를 추가한다.
     기존 줄은 그대로 두고, 없는 줄만 마지막 replace_path 뒤에 넣는다. path= 줄은 맨 끝에 남는다.
  2. 바닐라 common/national_focus/generic.txt를 모드에 복사한다 (BOM 제거, ASCII인 경우에만 그대로 씀).
  3. 바닐라 common/ideas 가운데 국가 전용 파일을 같은 이름의 빈 파일(ideas = { })로 덮어쓴다.
     분류: (a) 파일명 앞부분이 바닐라 국가 태그인 경우, (b) 파일 안의 아이디어 id 대부분이 바닐라 태그 접두사(XXX_)인 경우.
     법률·정신 파일(_로 시작, zzz_, 일반 이름)은 남긴다. 목록과 분류 이유를 출력한다.
  4. common/units/names_divisions/tu_names_divisions.txt에 모든 태그가 쓸 수 있는 기본 사단 이름 그룹(TU_DIVNAMES_FALLBACK)을 만든다.
  5. 바닐라 tutorial/tutorial.txt의 province/state id를 모드 맵의 id(1053 / 215)로 바꿔 terra_universalis/tutorial/tutorial.txt에 쓴다.

바닐라 폴더는 읽기만 한다. Documents 쪽에서는 terra_universalis.mod 한 파일만 건드린다.
"""

import argparse
import codecs
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
VANILLA_DIR = Path(r"G:\SteamLibrary\steamapps\common\Hearts of Iron IV")
MOD_DIR = PROJECT_DIR / "terra_universalis"
PROJECT_DESCRIPTOR = MOD_DIR / "descriptor.mod"
DOCS_DESCRIPTOR = Path(r"C:\Users\huand\Documents\Paradox Interactive\Hearts of Iron IV\mod\terra_universalis.mod")

REPLACE_PATHS = [
    "common/national_focus",
    "events",
    "common/decisions",
    "common/decisions/categories",
    "common/ai_strategy",
    "common/ai_strategy_plans",
    "common/ai_focuses",
    "common/on_actions",
    "common/bop",
    "common/scripted_guis",
    "common/operations",
    "common/units/names",
    "common/units/names_divisions",
    "common/units/names_ships",
    "common/units/names_railway_guns",
    "common/units/codenames_operatives",
    "common/intelligence_agencies",
    "common/technology_sharing",
    "common/military_industrial_organization/organizations",
    "common/peace_conference/ai_peace",
    "common/ai_peace",
    "history/general",
]

BLANK_RAID_FILES = [
    "common/raids/air_raids_custom.txt",
    "common/raids/land_infiltration_custom.txt",
    "common/raids/paratrooper_raids_custom.txt",
    "common/raids/naval_commando_raids.txt",
]
RAID_ID_RE = re.compile(r"^\s*(province|state)\s*=\s*\{?\s*\d", re.M)

TUTORIAL_FILE = "tutorial/tutorial.txt"
TUTORIAL_PROVINCE = 1053
TUTORIAL_STATE = 215
TUTORIAL_PROVINCE_KEYS = ("target", "direction_pointer")
TUTORIAL_STATE_KEYS = ("state",)
TUTORIAL_LIST_RE = re.compile(r"^(\s*)(highlight_provinces|highlight_states_trigger)(\s*=\s*\{)([^}]*)(\})")
TUTORIAL_INT_RE = re.compile(r"^(\s*)([A-Za-z_]\w*)(\s*=\s*)(\d+)\b")
TUTORIAL_BIG_INT_RE = re.compile(r"(?<![\w])\d+(?![\w])")

FALLBACK_GROUP = "TU_DIVNAMES_FALLBACK"
FALLBACK_TYPES = [
    "infantry", "cavalry", "motorized", "mechanized", "light_armor", "medium_armor",
    "heavy_armor", "modern_armor", "paratrooper", "marine", "mountaineers",
]

TAG_KEY_RE = re.compile(r"^\s*([A-Z][A-Z0-9]{1,3})\s*=", re.M)
IDEA_ID_RE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=\s*\{", re.M)
REPLACE_RE = re.compile(r'^\s*replace_path\s*=\s*"([^"]+)"')
# 아이디어 블록이 아닌 구조 키 (분류 비율 계산에서 뺀다)
STRUCTURAL = {
    "ideas", "country", "economy", "hidden_ideas", "allowed", "allowed_civil_war", "available",
    "visible", "modifier", "ai_will_do", "cancel", "on_add", "on_remove", "picture", "removal_cost",
    "on_activate", "on_deactivate", "bonus", "equipment_bonus", "hidden_modifier", "base", "factor",
    "trigger", "limit", "ledger", "aircraft_manufacturer", "designer", "law", "academy_spirit",
    "naval_manufacturer", "industrial_manufacturer", "army_spirit", "navy_spirit", "air_spirit",
    "targeted_modifier", "research_bonus", "cost", "modifiers",
}


def read_text(path):
    raw = path.read_bytes()
    return raw.decode("utf-8-sig")


def load_vanilla_tags(vanilla):
    text = read_text(vanilla / "common" / "country_tags" / "00_countries.txt")
    tags = set(TAG_KEY_RE.findall(text))
    if not tags:
        raise SystemExit("바닐라 국가 태그를 읽지 못함: common/country_tags/00_countries.txt")
    return tags


def classify_idea_file(stem, text, tags):
    """(분류, 이유) 또는 (None, 이유). 분류는 'name' 또는 'content'."""
    if stem.startswith("_") or stem.lower().startswith("zzz"):
        return None, "일반 법률/정신 파일 (이름 규칙)"
    prefix = re.split(r"[_.]", stem)[0].upper()
    if prefix in tags:
        return "name", "파일명 접두사 %s가 바닐라 국가 태그" % prefix
    ids = [i for i in IDEA_ID_RE.findall(text) if i not in STRUCTURAL]
    tagged = [i for i in ids if "_" in i and i.split("_")[0].upper() in tags]
    # 구조 키를 뺀 아이디어 중 4분의 1 이상이 태그 접두사(XXX_)면 국가 전용으로 본다 (경계 사례는 보고서에 적는다)
    if tagged and len(tagged) * 4 >= len(ids):
        return "content", "아이디어 %d개 중 %d개가 바닐라 태그 접두사" % (len(ids), len(tagged))
    return None, "국가 전용 아님 (태그 접두사 아이디어 %d/%d)" % (len(tagged), len(ids))


def ensure_replace_paths(descriptor, wanted, dry_run):
    if not descriptor.is_file():
        raise SystemExit("descriptor 없음: %s" % descriptor)
    raw = descriptor.read_bytes()
    has_bom = raw.startswith(codecs.BOM_UTF8)
    text = raw[len(codecs.BOM_UTF8):].decode("utf-8") if has_bom else raw.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    existing = {m.group(1) for ln in lines for m in [REPLACE_RE.match(ln)] if m}
    missing = [p for p in wanted if p not in existing]
    if not missing:
        print("descriptor 변경 없음 (replace_path 모두 있음): %s" % descriptor)
        return
    last = max((i for i, ln in enumerate(lines) if REPLACE_RE.match(ln)), default=len(lines) - 1)
    new_lines = [('replace_path="%s"' % p) for p in missing]
    out = lines[:last + 1] + new_lines + lines[last + 1:]
    body = newline.join(out) + newline
    data = (codecs.BOM_UTF8 if has_bom else b"") + body.encode("utf-8")
    if not dry_run:
        descriptor.write_bytes(data)
    print("descriptor %s: %s replace_path 추가%s" % (descriptor, len(missing), " (dry-run)" if dry_run else ""))
    for p in missing:
        print("  + replace_path=\"%s\"" % p)


def copy_generic_focus(vanilla, mod, dry_run):
    src = vanilla / "common" / "national_focus" / "generic.txt"
    dst = mod / "common" / "national_focus" / "generic.txt"
    text = read_text(src)
    if text.isascii():
        data = text.encode("ascii")
        note = "ASCII"
    else:
        data = text.encode("utf-8")
        note = "비ASCII 문자 있음 (확인 필요)"
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
    print("복사: %s -> %s (%s, %d bytes)%s" % (src.name, dst, note, len(data), " (dry-run)" if dry_run else ""))


def blank_country_ideas(vanilla, mod, tags, dry_run):
    src_dir = vanilla / "common" / "ideas"
    dst_dir = mod / "common" / "ideas"
    blanked = []
    kept = []
    for path in sorted(src_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() != ".txt":
            continue
        cls, reason = classify_idea_file(path.stem, read_text(path), tags)
        if cls is None:
            kept.append((path.name, reason))
            continue
        blanked.append((path.name, cls, reason))
        if not dry_run:
            dst_dir.mkdir(parents=True, exist_ok=True)
            (dst_dir / path.name).write_bytes(b"ideas = {\n}\n")
    print("빈 덮어쓰기 아이디어 파일 %d개%s:" % (len(blanked), " (dry-run)" if dry_run else ""))
    for name, cls, reason in blanked:
        print("  BLANK common/ideas/%s  [%s] %s" % (name, cls, reason))
    print("남긴 아이디어 파일 %d개 (법률/공용 등):" % len(kept))
    for name, reason in kept:
        print("  KEEP  common/ideas/%s  %s" % (name, reason))


def write_fallback_names(mod, dry_run):
    dst = mod / "common" / "units" / "names_divisions" / "tu_names_divisions.txt"
    lines = [
        "# TU fallback division name group. Used by every tag because the vanilla common/units/names_divisions",
        "# folder is replaced. No for_countries, so all countries can use it. Names come from fallback_name.",
        "%s = {" % FALLBACK_GROUP,
        '\tname = "TU fallback division names"',
        "",
        "\tcan_use = { always = yes }",
        "",
        "\tdivision_types = { %s }" % " ".join('"%s"' % t for t in FALLBACK_TYPES),
        "",
        '\tfallback_name = "%d. Division"',
        "}",
        "",
    ]
    text = "\n".join(lines)
    text.encode("ascii")
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(text.encode("ascii"))
    print("작성: %s (%s)%s" % (dst, FALLBACK_GROUP, " (dry-run)" if dry_run else ""))


def blank_raid_files(mod, dry_run):
    text = "\n".join([
        "# Terra Universalis: blanked. Vanilla raid targets point at vanilla-map province ids.",
        "types = {",
        "}",
        "",
    ])
    data = text.encode("ascii")
    for rel in BLANK_RAID_FILES:
        dst = mod / rel
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
        print("작성: %s (blank raid file)%s" % (dst, " (dry-run)" if dry_run else ""))


def report_hardcoded_raid_ids(vanilla, mod):
    for path in sorted((vanilla / "common" / "raids").glob("*.txt")):
        if not path.is_file():
            continue
        if (mod / "common" / "raids" / path.name).is_file():
            continue
        count = len(RAID_ID_RE.findall(read_text(path)))
        if count:
            print("WARNING: common/raids/%s has %d hard-coded province/state id line(s) and no mod override" % (path.name, count))


def check_tutorial_targets(mod):
    csv_path = mod / "map" / "definition.csv"
    rows = [ln.split(";") for ln in csv_path.read_bytes().decode("latin-1").splitlines()]
    prov = [r for r in rows if r and r[0].strip() == str(TUTORIAL_PROVINCE)]
    if not prov or len(prov[0]) < 5 or prov[0][4].strip() != "land":
        raise SystemExit("tutorial remap 중단: province %d 가 land 행이 아님 (%s)" % (TUTORIAL_PROVINCE, csv_path))
    state_files = sorted((mod / "history" / "states").glob("%d-*.txt" % TUTORIAL_STATE))
    if not state_files:
        raise SystemExit("tutorial remap 중단: state %d 파일을 찾지 못함" % TUTORIAL_STATE)
    for path in state_files:
        text = "\n".join(ln.partition("#")[0] for ln in path.read_bytes().decode("latin-1").splitlines())
        for m in re.finditer(r"provinces\s*=\s*\{([^}]*)\}", text):
            if TUTORIAL_PROVINCE in {int(x) for x in re.findall(r"\d+", m.group(1))}:
                return
    raise SystemExit("tutorial remap 중단: province %d 가 state %d 의 provinces 에 없음" % (TUTORIAL_PROVINCE, TUTORIAL_STATE))


def tutorial_rule(key):
    """(바꿀 id, 방식) 또는 (None, None). 방식은 'exact'(정해진 키) 또는 'name'(키 이름에 단어가 들어간 경우)."""
    if key in TUTORIAL_STATE_KEYS:
        return TUTORIAL_STATE, "exact"
    if key in TUTORIAL_PROVINCE_KEYS:
        return TUTORIAL_PROVINCE, "exact"
    low = key.lower()
    if "province" in low or "target" in low or "pointer" in low:
        return TUTORIAL_PROVINCE, "name"
    if "state" in low:
        return TUTORIAL_STATE, "name"
    return None, None


def remap_tutorial_code(code):
    """주석을 뺀 한 줄 -> (새 코드, 방식). 방식은 None(안 바뀜), 'exact', 'name'."""
    m = TUTORIAL_LIST_RE.match(code)
    if m:
        key = m.group(2)
        new_id = TUTORIAL_PROVINCE if key == "highlight_provinces" else TUTORIAL_STATE
        inner = re.sub(r"\d+", str(new_id), m.group(4))
        return m.group(1) + key + m.group(3) + inner + m.group(5) + code[m.end():], "exact"
    m = TUTORIAL_INT_RE.match(code)
    if m:
        key = m.group(2)
        new_id, how = tutorial_rule(key)
        if new_id is None:
            return code, None
        return m.group(1) + key + m.group(3) + str(new_id) + code[m.end():], how
    return code, None


def remap_tutorial(vanilla, mod, dry_run):
    check_tutorial_targets(mod)
    src = vanilla / TUTORIAL_FILE
    dst = mod / TUTORIAL_FILE
    text = src.read_bytes().decode("latin-1")
    out = []
    changed = []
    warnings = []
    for no, line in enumerate(text.splitlines(keepends=True), 1):
        body = line.rstrip("\r\n")
        eol = line[len(body):]
        code = body.partition("#")[0]
        new_code, how = remap_tutorial_code(code)
        if how is not None:
            new_body = new_code.rstrip()
            changed.append((no, body, new_body))
            body = new_body
            if how == "name":
                print("NOTE tutorial: line %d: 키 이름 규칙으로 바꿈: %s" % (no, body.strip()))
        out.append(body + eol)
        # 바꾼 뒤 남은 값 점검 (주석 뺀 코드 기준)
        check_code = body.partition("#")[0]
        remaining_big = [int(x) for x in TUTORIAL_BIG_INT_RE.findall(check_code) if int(x) >= 1000 and int(x) != TUTORIAL_PROVINCE]
        unhandled_int = how is None and TUTORIAL_INT_RE.match(check_code) is not None
        if remaining_big or unhandled_int:
            warnings.append((no, body.strip()))
    for no, old, new in changed:
        print("  line %d: %s -> %s" % (no, old.strip(), new.strip()))
    for no, text_line in warnings:
        print("WARNING tutorial: line %d: %s" % (no, text_line))
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes("".join(out).encode("latin-1"))
    print("튜토리얼 리맵: %d줄 변경, 경고 %d개 -> %s%s" % (len(changed), len(warnings), dst, " (dry-run)" if dry_run else ""))


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="바닐라 참조 정리 (C.3)")
    parser.add_argument("--vanilla", default=str(VANILLA_DIR), help="바닐라 설치 경로 (읽기 전용)")
    parser.add_argument("--mod", default=str(MOD_DIR), help="모드 폴더")
    parser.add_argument("--docs-descriptor", default=str(DOCS_DESCRIPTOR), help="Documents의 .mod 파일")
    parser.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 할 일만 출력")
    args = parser.parse_args(argv)

    vanilla = Path(args.vanilla)
    mod = Path(args.mod)
    if not (vanilla / "common").is_dir():
        raise SystemExit("바닐라 common 폴더가 없음: %s" % vanilla)

    print("== descriptor replace_path ==")
    ensure_replace_paths(PROJECT_DESCRIPTOR, REPLACE_PATHS, args.dry_run)
    ensure_replace_paths(Path(args.docs_descriptor), REPLACE_PATHS, args.dry_run)

    print("== generic focus tree ==")
    copy_generic_focus(vanilla, mod, args.dry_run)
    if not args.dry_run:
        # 바닐라 사본에는 continuous_focus_position 이 없어 지속적 중점 패널이 트리를 가린다 (린트 C5)
        sys.path.insert(0, str(Path(__file__).resolve().parent / "focusgen"))
        import place_continuous
        place_continuous.place_file(mod / "common" / "national_focus" / "generic.txt")

    print("== country ideas blanking ==")
    tags = load_vanilla_tags(vanilla)
    blank_country_ideas(vanilla, mod, tags, args.dry_run)

    print("== fallback division names ==")
    write_fallback_names(mod, args.dry_run)

    print("== raid files blanking ==")
    blank_raid_files(mod, args.dry_run)
    report_hardcoded_raid_ids(vanilla, mod)

    print("== tutorial remap ==")
    remap_tutorial(vanilla, mod, args.dry_run)

    print("VANILLA_CLEANUP ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
