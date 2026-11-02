#!/usr/bin/env python3
"""countries.json + tools/mapgen/out/state_index.json -> 국가 정의, 북마크, 날짜 defines, 깃발, 로컬라이제이션.

사용법 (python -I):
    python -I tools/mapgen/build_countries.py --countries tools/mapgen/test/countries.json --mod terra_universalis

입력: mapgen.py가 만든 out/state_index.json (주 목록, capital_state). 바닐라 zz_dynamic_countries.txt는 복사만 한다.
"""

import argparse
import json
import re
import shutil
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

MAPGEN_DIR = Path(__file__).resolve().parent
PROJECT_DIR = MAPGEN_DIR.parent.parent
OUT_DIR = MAPGEN_DIR / "out"
REF_FLAG_DIR = PROJECT_DIR / "reference" / "flags"   # <TAG>.png = 공식 엠블럼 (있으면 실제 깃발을 합성)
VANILLA_DIR = Path(r"G:\SteamLibrary\steamapps\common\Hearts of Iron IV")
DEFAULT_MOD = "terra_universalis"
START_DATE = "1097.1.1.12"
END_DATE = "1120.1.1.1"
TAG_RE = re.compile(r"^[A-Z][A-Z0-9]{2}$")
FLAG_SIZES = [("gfx/flags/%s.tga", (82, 52)), ("gfx/flags/medium/%s.tga", (41, 26)),
              ("gfx/flags/small/%s.tga", (10, 7))]


class BuildError(Exception):
    pass


def resolve_input(p):
    path = Path(p)
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    return (PROJECT_DIR / path).resolve()


def resolve_mod(p):
    path = Path(p)
    if path.is_absolute():
        return path
    cand = PROJECT_DIR / path
    if cand.is_dir():
        return cand.resolve()
    return path.resolve()


def write_ascii(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("ascii"))


def write_utf8_bom(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(("\n".join(lines) + "\n").encode("utf-8-sig"))


def load_countries(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise BuildError("countries.json: 빈 목록")
    seen = set()
    out = []
    for c in data:
        for key in ("tag", "name_ko", "name_en", "adj_ko", "adj_en", "color"):
            if key not in c:
                raise BuildError("countries.json: %s 누락 (%s)" % (key, c.get("tag")))
        tag = c["tag"]
        if not TAG_RE.match(tag):
            raise BuildError("태그 형식 오류: %s (대문자 3글자)" % tag)
        if tag in seen:
            raise BuildError("태그 중복: %s" % tag)
        seen.add(tag)
        color = [int(v) for v in c["color"]]
        if len(color) != 3 or any(v < 0 or v > 255 for v in color):
            raise BuildError("색 오류: %s" % tag)
        out.append(dict(c, color=color))
    return out


def load_index():
    path = OUT_DIR / "state_index.json"
    if not path.is_file():
        raise BuildError("out/state_index.json 없음: mapgen.py를 먼저 실행하세요")
    return json.loads(path.read_text(encoding="ascii"))


def write_tga(path, w, h, rgb):
    """32bit 비압축 TGA, 단색 (BGRA, 원점 왼쪽 위)."""
    r, g, b = rgb
    header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x08)
    px = np.empty((h, w, 4), np.uint8)
    px[:, :, 0] = b
    px[:, :, 1] = g
    px[:, :, 2] = r
    px[:, :, 3] = 255
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + px.tobytes())


def clean_country_outputs(mod, countries):
    """생성 전에 이 도구가 만드는 국가 출력 중 현재 목록에 없는 태그의 파일을 비운다 (1a 사양 16항과 같은 방식).
    history/countries는 전부 이 도구 소유. custom_characters 국가의 common/characters 파일은 건드리지 않는다 (B·C 소유)."""
    tags = {c["tag"] for c in countries}
    custom = {c["tag"] for c in countries if c.get("custom_characters")}
    for f in (mod / "history" / "countries").glob("*.txt"):
        f.unlink()
    for f in (mod / "common" / "countries").glob("*.txt"):
        if re.fullmatch(r"[A-Z]{3}", f.stem) and f.stem not in tags:
            f.unlink()
    for f in (mod / "common" / "characters").glob("*.txt"):
        if re.fullmatch(r"[A-Z]{3}", f.stem) and f.stem not in tags and f.stem not in custom:
            f.unlink()
    for sub in ("", "medium", "small"):
        for f in (mod / "gfx" / "flags" / sub).glob("*.tga") if sub else (mod / "gfx" / "flags").glob("*.tga"):
            if f.stem not in tags:
                f.unlink()


def write_owner_preview(mod, countries, index):
    """tools/mapgen/out/preview_owner.png: 프로빈스마다 소유국 색 (바다·호수는 따로, 지도 크기의 1/4)."""
    W, H = index["map_size"]
    lines = (mod / "map" / "definition.csv").read_text(encoding="ascii").splitlines()[1:]
    ids = np.array([int(ln.split(";")[0]) for ln in lines], np.int64)
    codes = np.array([(int(ln.split(";")[1]) << 16) | (int(ln.split(";")[2]) << 8) | int(ln.split(";")[3])
                      for ln in lines], np.int64)
    types = [ln.split(";")[4] for ln in lines]
    n = len(countries)
    lut = np.zeros((n + 3, 3), np.uint8)
    lut[0] = (60, 60, 60)                       # 소유국 없음
    for i, c in enumerate(countries):
        lut[i + 1] = c["color"]
    lut[n + 1] = (25, 50, 90)                   # 바다
    lut[n + 2] = (70, 130, 190)                 # 호수
    tag_index = {c["tag"]: i + 1 for i, c in enumerate(countries)}
    code_of = np.zeros(int(ids.max()) + 1, np.int32)
    for k, t in enumerate(types):
        code_of[ids[k]] = n + 1 if t == "sea" else (n + 2 if t == "lake" else 0)
    for st in index["states"]:
        for p in st["provinces"]:
            code_of[p] = tag_index.get(st["owner"], 0)
    rgb = np.asarray(Image.open(mod / "map" / "provinces.bmp").convert("RGB")).astype(np.int64)
    pc = (rgb[:, :, 0] << 16) | (rgb[:, :, 1] << 8) | rgb[:, :, 2]
    order = np.argsort(codes)
    ks = codes[order]
    pos = np.clip(np.searchsorted(ks, pc), 0, len(ks) - 1)
    pid = ids[order[pos]]
    img = lut[code_of[pid]]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img).resize((W // 4, H // 4), Image.NEAREST).save(OUT_DIR / "preview_owner.png")
    print("preview_owner.png written")


SHAPES = ("circle", "diamond", "cross")


def flag_rgb(w, h, c):
    """단순 절차 깃발: 국가 색 바탕 + 대비색 가로 띠 1개 + 태그 해시로 고른 도형 1개 (원/마름모/십자).
    공식 로고는 따라 그리지 않는다."""
    r, g, b = c["color"]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    contrast = (255, 255, 255) if lum < 128 else (0, 0, 0)
    px = np.empty((h, w, 3), np.uint8)
    px[:, :] = (r, g, b)
    band = max(1, h // 6)
    y0 = (h - band) // 2
    px[y0:y0 + band, :] = contrast
    shape = SHAPES[sum(ord(ch) for ch in c["tag"]) % len(SHAPES)]
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    rad = min(w, h) * 0.3
    dy = np.abs(yy - cy)
    dx = np.abs(xx - cx)
    if shape == "circle":
        mask = dy ** 2 + dx ** 2 <= rad ** 2
    elif shape == "diamond":
        mask = dy + dx <= rad
    else:
        t = rad / 4.0
        mask = ((dx <= t) & (dy <= rad)) | ((dy <= t) & (dx <= rad))
    px[mask] = contrast
    return px


EMBLEM_W_FRAC = 0.60       # 엠블럼은 깃발 폭의 60% 이하
EMBLEM_H_FRAC = 0.84       # 엠블럼은 깃발 높이의 84% 이하
MONO_SAT_MAX = 24          # max(R,G,B)-min(R,G,B) 미만이면 무채색 픽셀
MONO_MIN_FRAC = 0.95       # 불투명 픽셀의 이 비율 이상이 무채색이면 단색 엠블럼
MIN_CONTRAST = 3.0         # 색 엠블럼과 바탕의 WCAG 대비 하한 (미달이면 1px 어두운 외곽선)
DARK_TONE = (30, 30, 30)


def rel_luminance(rgb):
    """WCAG 상대 휘도 (0..1)."""
    def lin(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(l1, l2):
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def emblem_flag_rgb(w, h, c, emblem_path):
    """공식 엠블럼(PNG) 합성 깃발: 국가 색 바탕 + 엠블럼 (트림, LANCZOS 축소, 중앙). 반환은 (h, w, 3) uint8."""
    bg = tuple(c["color"])
    bg_lum = rel_luminance(bg)
    src = Image.open(emblem_path).convert("RGBA")
    arr = np.asarray(src).astype(np.float32)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    op = alpha > 128
    if not op.any():
        raise BuildError("엠블럼이 비어 있음: %s" % emblem_path.name)
    sat = rgb.max(2) - rgb.min(2)
    mono = (sat[op] < MONO_SAT_MAX).mean() >= MONO_MIN_FRAC
    if mono:
        # 단색: 배경이 밝으면 어두운 색, 어두우면 흰색. 엠블럼 안의 짙은 부분(예: RHO 성 그림)은 배경이 비치도록 뺀다
        lum = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]) / 255.0
        knock = np.clip((lum - 0.3) / 0.4, 0.0, 1.0)
        tone = DARK_TONE if bg_lum > 0.5 else (255, 255, 255)
        out = np.empty_like(arr)
        out[:, :, :3] = tone
        out[:, :, 3] = alpha * knock
        src = Image.fromarray(np.round(out).astype(np.uint8), "RGBA")
    emblem = src.crop(src.getchannel("A").getbbox())
    max_w = int(w * EMBLEM_W_FRAC)
    max_h = int(round(h * EMBLEM_H_FRAC))
    scale = min(max_w / float(emblem.width), max_h / float(emblem.height))
    tw = max(1, int(round(emblem.width * scale)))
    th = max(1, int(round(emblem.height * scale)))
    small = emblem.resize((tw, th), Image.LANCZOS)
    if not mono:
        ea = np.asarray(small).astype(np.float32)
        m = ea[:, :, 3] > 128
        if m.any() and contrast_ratio(rel_luminance(ea[m][:, :3].mean(0)), bg_lum) < MIN_CONTRAST:
            small = add_outline(small)
    canvas = Image.new("RGBA", (w, h), bg + (255,))
    if w >= 40:
        edge = tuple(int(v * 0.65) for v in bg) + (255,)
        ImageDraw.Draw(canvas).rectangle([0, 0, w - 1, h - 1], outline=edge)
    x = (w - small.width) // 2
    y = (h - small.height) // 2
    canvas.alpha_composite(small, dest=(x, y))
    return np.asarray(canvas.convert("RGB"))


def add_outline(im):
    """RGBA 엠블럼 둘레에 1px 어두운 외곽선을 붙인다 (대비가 낮은 색 엠블럼용)."""
    pad = Image.new("RGBA", (im.width + 2, im.height + 2), (0, 0, 0, 0))
    a = Image.new("L", pad.size, 0)
    a.paste(im.getchannel("A"), (1, 1))
    dark = Image.new("RGBA", pad.size, (20, 20, 20, 0))
    dark.putalpha(a.filter(ImageFilter.MaxFilter(3)))
    pad.alpha_composite(dark)
    pad.alpha_composite(im, dest=(1, 1))
    return pad


def flag_pixels(w, h, c):
    """reference/flags/<TAG>.png가 있으면 공식 엠블럼 깃발, 없으면 기존 절차 깃발."""
    emblem = REF_FLAG_DIR / ("%s.png" % c["tag"])
    if emblem.is_file():
        return emblem_flag_rgb(w, h, c, emblem)
    return flag_rgb(w, h, c)


def write_flag(path, w, h, c):
    px = flag_pixels(w, h, c)
    bgra = np.empty((h, w, 4), np.uint8)
    bgra[:, :, 0] = px[:, :, 2]
    bgra[:, :, 1] = px[:, :, 1]
    bgra[:, :, 2] = px[:, :, 0]
    bgra[:, :, 3] = 255
    # HOI4 는 TGA 원점 비트를 무시하고 아래쪽부터 읽는다: 원점 왼쪽 아래(0x08)로 행을 뒤집어 쓴다
    header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x08)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + np.ascontiguousarray(bgra[::-1]).tobytes())


DYN_REF_RE = re.compile(r'^\s*([A-Za-z0-9_]+)\s*=\s*"(countries/[^"]+)"', re.M)
TOP_BLOCK_RE = re.compile(r"^([A-Za-z0-9_]+)\s*=\s*\{")


def dynamic_refs(text):
    """zz_dynamic_countries.txt의 (태그, 'countries/XXX.txt') 목록."""
    return DYN_REF_RE.findall(text)


def vanilla_color_blocks(text, tags):
    """colors.txt의 최상위 'TAG = { ... }' 블록 중 tags에 속한 것을 {태그: 줄 목록}으로 돌려준다."""
    lines = text.splitlines()
    found = {}
    i = 0
    while i < len(lines):
        m = TOP_BLOCK_RE.match(lines[i])
        if not m:
            i += 1
            continue
        depth = 0
        j = i
        block = []
        while j < len(lines):
            block.append(lines[j])
            depth += lines[j].count("{") - lines[j].count("}")
            if depth <= 0:
                break
            j += 1
        if m.group(1) in tags:
            found[m.group(1)] = block
        i = j + 1
    return found


NAME_MIN = 20          # 태그마다 이름 목록 최소 개수
LEADER_GFX = "GFX_Portrait_Europe_Generic_1"
LEADER_EXPIRE = "1200.1.1.1"
DYNAMIC_CAPITAL_NAME = "chernobog"   # dynamic 국가(REU)의 수도 지정용 이름 있는 주 (주는 소유하지 않는다)


def block_end(lines, i):
    """lines[i]에서 시작한 중괄호 블록이 닫히는 줄 번호."""
    depth = 0
    for j in range(i, len(lines)):
        depth += lines[j].count("{") - lines[j].count("}")
        if depth <= 0:
            return j
    raise BuildError("닫히지 않은 블록 (줄 %d)" % (i + 1))


def europe_bodies(text):
    """최상위 'continent = { name = europe ... }' 블록들의 본문 줄 (name 줄 제외)."""
    lines = text.splitlines()
    bodies = []
    i = 0
    while i < len(lines):
        if re.match(r"^\s*continent\s*=\s*\{", lines[i]):
            j = block_end(lines, i)
            inner = lines[i + 1:j]
            if any(x.strip() == "name = europe" for x in inner):
                bodies.extend(x for x in inner if x.strip() != "name = europe")
            i = j + 1
        else:
            i += 1
    return bodies


def quoted_lines(values, indent, per_line=8):
    out = []
    for i in range(0, len(values), per_line):
        chunk = values[i:i + per_line]
        out.append(indent + " ".join('"%s"' % v for v in chunk))
    return out


def names_block(tag, names):
    """common/names 형식: TAG = { male = { names = {..} } female = { names = {..} } surnames = {..} callsigns = {..} }"""
    L = ["%s = {" % tag, "\tmale = {", "\t\tnames = {"]
    L += quoted_lines(names["male"], "\t\t\t")
    L += ["\t\t}", "\t}", "\tfemale = {", "\t\tnames = {"]
    L += quoted_lines(names["female"], "\t\t\t")
    L += ["\t\t}", "\t}", "\tsurnames = {"]
    L += quoted_lines(names["surnames"], "\t\t")
    L += ["\t}", "\tcallsigns = {"]
    L += quoted_lines(names["callsigns"], "\t\t")
    L += ["\t}", "}"]
    return L


def tag_names(c):
    """countries.json의 선택 필드 names가 있으면 그 값, 없는 항목은 ASCII 임시 이름 (각 NAME_MIN개 이상)."""
    given = c.get("names", {})
    tag = c["tag"]
    gen = {
        "male": ["%s Male %02d" % (tag, i) for i in range(1, NAME_MIN + 1)],
        "female": ["%s Female %02d" % (tag, i) for i in range(1, NAME_MIN + 1)],
        "surnames": ["%s Surname %02d" % (tag, i) for i in range(1, NAME_MIN + 1)],
        "callsigns": ["%s Callsign %02d" % (tag, i) for i in range(1, NAME_MIN + 1)],
    }
    out = {}
    for key, default in gen.items():
        vals = list(given.get(key, [])) or default
        if len(vals) < NAME_MIN:
            raise BuildError("국가 %s: names.%s가 %d개 (최소 %d)" % (tag, key, len(vals), NAME_MIN))
        out[key] = [str(v) for v in vals]
    return out


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="국가/북마크/깃발/로컬라이제이션 생성")
    parser.add_argument("--countries", required=True, help="countries.json")
    parser.add_argument("--mod", default=DEFAULT_MOD)
    parser.add_argument("--vanilla", default=str(VANILLA_DIR), help="바닐라 설치 경로 (읽기 전용)")
    args = parser.parse_args(argv)

    vanilla = Path(args.vanilla)
    mod = resolve_mod(args.mod)
    countries = load_countries(resolve_input(args.countries))
    index = load_index()
    capital_state = index["capital_state"]
    state_owners = {st["owner"] for st in index["states"]}
    state_ids = {st["id"] for st in index["states"]}

    # 수도 id: 일반 국가는 index의 수도 주. dynamic 국가(시작 주 없음)는 이름 있는 주(DYNAMIC_CAPITAL_NAME)의 id
    capital_of = {}
    for c in countries:
        tag = c["tag"]
        if c.get("dynamic"):
            if tag in state_owners:
                raise BuildError("dynamic 국가 %s에 시작 주가 있음" % tag)
            named_path = OUT_DIR / "named_states.json"
            named = {e["name"]: e["state"] for e in json.loads(named_path.read_text(encoding="ascii"))["named"]}
            if DYNAMIC_CAPITAL_NAME not in named:
                raise BuildError("dynamic 국가 %s: 수도용 이름 있는 주 %s 없음" % (tag, DYNAMIC_CAPITAL_NAME))
            capital_of[tag] = named[DYNAMIC_CAPITAL_NAME]
            continue
        if tag not in capital_state:
            raise BuildError("국가 %s: land 주가 없어 수도를 정할 수 없음" % tag)
        if capital_state[tag] not in state_ids:
            raise BuildError("국가 %s: 수도 주 %s가 주 목록에 없음" % (tag, capital_state[tag]))
        capital_of[tag] = capital_state[tag]
    unknown = sorted(state_owners - {c["tag"] for c in countries})
    if unknown:
        raise BuildError("주 소유국이 countries.json에 없음: %s" % ", ".join(unknown))

    clean_country_outputs(mod, countries)

    # common/country_tags
    tags_lines =['%s = "countries/%s.txt"' % (c["tag"], c["tag"]) for c in countries]
    write_ascii(mod / "common" / "country_tags" / "00_countries.txt", "\n".join(tags_lines) + "\n")
    src_dyn = vanilla / "common" / "country_tags" / "zz_dynamic_countries.txt"
    dst_dyn = mod / "common" / "country_tags" / "zz_dynamic_countries.txt"
    dst_dyn.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_dyn, dst_dyn)
    # replace_path="common/countries"가 바닐라 국가 파일을 지우므로, zz가 참조하는 바닐라 국가 파일을 같은 경로로 복사한다
    dyn = dynamic_refs(src_dyn.read_bytes().decode("utf-8-sig"))
    if not dyn:
        raise BuildError("zz_dynamic_countries.txt에서 참조를 찾지 못함")
    for rel in sorted({path for _, path in dyn}):
        src = vanilla / "common" / rel
        if not src.is_file():
            raise BuildError("바닐라 동적 국가 파일 없음: %s" % rel)
        dst = mod / "common" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

    # common/countries
    color_lines = []
    for c in countries:
        tag = c["tag"]
        r, g, b = c["color"]
        text = ("graphical_culture = western_european_gfx\n"
                "graphical_culture_2d = western_european_2d\n"
                "color = rgb { %d %d %d }\n" % (r, g, b))
        write_ascii(mod / "common" / "countries" / ("%s.txt" % tag), text)
        color_lines.append("%s = { color = rgb { %d %d %d } color_ui = rgb { %d %d %d } }"
                           % (tag, r, g, b, r, g, b))
    # 동적(D-) 태그의 바닐라 색 항목을 그대로 덧붙인다 (바닐라에 있는 태그만)
    dyn_tags = sorted({tag for tag, _ in dyn})
    vanilla_colors = (vanilla / "common" / "countries" / "colors.txt").read_text(encoding="utf-8-sig")
    blocks = vanilla_color_blocks(vanilla_colors, set(dyn_tags))
    extra = []
    for tag in dyn_tags:
        if tag in blocks:
            extra.extend(blocks[tag])
    if extra:
        color_lines += [""] + extra
    write_ascii(mod / "common" / "countries" / "colors.txt", "\n".join(color_lines) + "\n")

    # portraits: 바닐라 europe 블록 두 개(00_portraits, 998_scientist)를 합쳐 continent = terra 하나로 만든다
    body = []
    for rel in ("portraits/00_portraits.txt", "portraits/998_scientist_portraits.txt"):
        src = vanilla / rel
        body += europe_bodies(src.read_text(encoding="utf-8-sig"))
    if not body:
        raise BuildError("바닐라 europe 초상화 블록을 찾지 못함")
    write_ascii(mod / "portraits" / "tu_portraits.txt",
                "\n".join(["continent = {", "\tname = terra"] + body + ["}"]) + "\n")

    # common/names: 태그마다 male/female 이름, 성, 콜사인 (ASCII 임시 이름 또는 countries.json의 names)
    name_lines = []
    for c in countries:
        name_lines += names_block(c["tag"], tag_names(c)) + [""]
    write_ascii(mod / "common" / "names" / "tu_names.txt", "\n".join(name_lines))

    # common/characters: 국가 지도자 (GFX는 바닐라 interface에 정의된 것). custom_characters 국가는 건너뜀 (연결 규약 4)
    for c in countries:
        if c.get("custom_characters"):
            continue
        t = c["tag"]
        leader = [
            "characters = {",
            "\t%s_leader = {" % t,
            "\t\tname = %s_leader" % t,
            '\t\tportraits = { civilian = { large = "%s" } }' % LEADER_GFX,
            "\t\tcountry_leader = { ideology = despotism expire = \"%s\" id = -1 }" % LEADER_EXPIRE,
            "\t}",
            "}",
        ]
        write_ascii(mod / "common" / "characters" / ("%s.txt" % t), "\n".join(leader) + "\n")

    # history/countries: 기본 줄 + (custom_characters가 아니면 지도자) + tools/mapgen/country_history/<TAG>.txt 내용 그대로
    for c in countries:
        tag = c["tag"]
        lines = [
            "capital = %d" % capital_of[tag],
            "set_research_slots = 3",
            'set_politics = { ruling_party = neutrality last_election = "1096.1.1" '
            'election_frequency = 48 elections_allowed = no }',
            "set_popularities = { neutrality = 100 }",
        ]
        if not c.get("custom_characters"):
            lines.append("recruit_character = %s_leader" % tag)
        text = "\n".join(lines) + "\n"
        snippet_path = MAPGEN_DIR / "country_history" / ("%s.txt" % tag)
        if snippet_path.is_file():
            snippet = snippet_path.read_bytes().decode("utf-8-sig")
            text += snippet if snippet.endswith("\n") else snippet + "\n"
            print("country_history snippet appended: %s" % tag)
        write_ascii(mod / "history" / "countries" / ("%s - %s.txt" % (tag, c["name_en"])), text)

    # common/bookmarks
    bm = ["bookmarks = {", "\tbookmark = {",
          '\t\tname = "TU_BOOKMARK_1097_NAME"',
          '\t\tdesc = "TU_BOOKMARK_1097_DESC"',
          "\t\tdate = 1097.1.1.12",
          '\t\tpicture = "GFX_select_date_1936"',
          '\t\tdefault_country = "%s"' % ("RHO" if any(c["tag"] == "RHO" for c in countries) else countries[0]["tag"]),
          "\t\tdefault = yes",
          ""]
    for c in countries:
        if c.get("dynamic") or c.get("filler"):
            continue    # 시작 주가 없는 동적 국가, 무주지(filler) 태그는 국가 선택 화면에 넣지 않는다
        bm.append('\t\t%s = { history = "OVERVIEW_%s" ideology = neutrality }' % (c["tag"], c["tag"]))
    bm += ["\t}", "}"]
    write_ascii(mod / "common" / "bookmarks" / "tu_bookmarks.txt", "\n".join(bm) + "\n")

    # common/defines
    write_ascii(mod / "common" / "defines" / "tu_defines.lua",
                'NDefines.NGame.START_DATE = "%s"\nNDefines.NGame.END_DATE = "%s"\n' % (START_DATE, END_DATE))

    # 깃발
    for c in countries:
        for pattern, (w, h) in FLAG_SIZES:
            write_flag(mod / (pattern % c["tag"]), w, h, c)
    n_emblem = sum(1 for c in countries if (REF_FLAG_DIR / ("%s.png" % c["tag"])).is_file())
    print("flags: emblem=%d fallback=%d" % (n_emblem, len(countries) - n_emblem))

    # 로컬라이제이션
    ko = []
    en = []
    for c in countries:
        t = c["tag"]
        ko += [(t, c["name_ko"]), (t + "_DEF", c["name_ko"]), (t + "_ADJ", c["adj_ko"]),
               (t + "_neutrality", c["name_ko"]), (t + "_neutrality_DEF", c["name_ko"]),
               (t + "_neutrality_ADJ", c["adj_ko"])]
        en += [(t, c["name_en"]), (t + "_DEF", "the " + c["name_en"]), (t + "_ADJ", c["adj_en"]),
               (t + "_neutrality", c["name_en"]), (t + "_neutrality_DEF", "the " + c["name_en"]),
               (t + "_neutrality_ADJ", c["adj_en"])]
        ko.append(("OVERVIEW_%s" % t, "%s 개요" % c["name_ko"]))
        en.append(("OVERVIEW_%s" % t, "%s Overview" % c["name_en"]))
        if not c.get("custom_characters"):
            ko.append(("%s_leader" % t, "%s 지도자" % c["name_ko"]))
            en.append(("%s_leader" % t, "%s Leader" % c["name_en"]))
    ko += [("TU_BOOKMARK_1097_NAME", "테라력 1097년"),
           ("TU_BOOKMARK_1097_DESC", "테라력 1097년, 테스트 지도로 시작합니다.")]
    en += [("TU_BOOKMARK_1097_NAME", "Terra Year 1097"),
           ("TU_BOOKMARK_1097_DESC", "Terra Year 1097, starting on the test map.")]
    for folder, lang, items, head in (("korean", "korean", ko, "l_korean:"),
                                      ("english", "english", en, "l_english:")):
        lines = [head] + [' %s:0 "%s"' % (k, v) for k, v in items]
        write_utf8_bom(mod / "localisation" / folder / ("tu_countries_l_%s.yml" % lang), lines)

    write_owner_preview(mod, countries, index)
    print("countries: %s" % ", ".join(c["tag"] for c in countries))
    print("capital_state: %s" % json.dumps({c["tag"]: capital_of[c["tag"]] for c in countries}))
    print("BUILD_COUNTRIES ok mod=%s" % mod)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BuildError as exc:
        print("BUILD_COUNTRIES ERROR: %s" % exc)
        sys.exit(1)
