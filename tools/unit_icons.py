#!/usr/bin/env python3
"""병종 아이콘: 명일방주 세부 분류 아이콘을 게임 병종 아이콘으로 (사양서 74).

원본   reference/branch_icons/<포지션>/<세부 분류>.png   Arknights Terra Wiki (arknights.wiki.gg) 의 Class 문서 그림.
       흰 아이콘에 투명 배경. `_<포지션>.png` 는 포지션 아이콘.
짝     tools/unit_names.py 의 UNITS (병종 -> 포지션, 세부 분류). 같은 세부 분류의 대대·지원 중대·기동 대대는 같은 아이콘.

게임은 병종마다 스프라이트 세 개를 쓴다 (이름은 고정):
    GFX_unit_<병종>_icon_medium        사단 편성 화면   (바닐라: gfx/interface/counters/divisions_large/unit_infantry_icon.dds, 2프레임)
    GFX_unit_<병종>_icon_medium_white  지도 위 카운터   (바닐라: gfx/interface/counters/divisions_small/onmap_unit_infantry_icon.dds, 2프레임)
    GFX_unit_<병종>_icon_small         글 속 아이콘     (바닐라: gfx/texticons/unit_infantry_icon_small.dds)
크기와 프레임 배치가 바닐라와 같아야 화면에서 어긋나지 않는다. 그래서 바닐라 견본 세 개를 reference/vanilla_icons/ 에 두고
(사용자가 올린 파일) 거기서 크기·프레임 수·프레임별 색을 읽어 같은 모양으로 만든다. 견본이 없으면 아무것도 쓰지 않는다.

출력   terra_universalis/gfx/interface/tu_units/<세부 분류>_{medium,white,small}.tga
       terra_universalis/interface/tu_unit_icons.gfx   (병종마다 스프라이트 세 개. 바닐라 정의를 같은 이름으로 덮어쓴다)
사용법 (python -I):  python -I tools/unit_icons.py [--samples <폴더>] [--sheet <미리보기.png>]
"""

import argparse
import re
import sys
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "terra_universalis"
SRC = REPO / "reference" / "branch_icons"
SAMPLES = REPO / "reference" / "vanilla_icons"
OUT = MOD / "gfx" / "interface" / "tu_units"
GFX = MOD / "interface" / "tu_unit_icons.gfx"
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "tools" / "portraits"))
import unit_names  # noqa: E402

# 견본: (종류, 파일 이름 줄기). 세 그림 모두 2프레임이다: 왼쪽 = 그림 아이콘 (바닐라는 철모), 오른쪽 = NATO 기호 (밝은 네모에 X).
# 플레이어가 설정에서 고른 쪽이 보인다. 우리 것: 왼쪽 = 흰 세부 분류 아이콘 (어두운 테두리), 오른쪽 = 같은 네모 안에 검은 아이콘.
KINDS = [("medium", "unit_infantry_icon"), ("white", "onmap_unit_infantry_icon"), ("small", "unit_infantry_icon_small")]
FRAMES = 2
SPRITE = {"medium": "GFX_unit_%s_icon_medium", "white": "GFX_unit_%s_icon_medium_white", "small": "GFX_unit_%s_icon_small"}
GROW = 1.3          # 그림 아이콘은 바닐라 철모가 차지한 칸보다 이만큼 크게 (가는 선 아이콘이라 작으면 안 보인다)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def icon_of(unit):
    cls, _, ben, _, _, _ = unit_names.UNITS[unit]
    p = SRC / cls / ("%s.png" % slug(ben))
    if not p.is_file():
        raise SystemExit("아이콘 없음: %s (%s)" % (p.relative_to(REPO), unit))
    return p


def find_sample(folder, stem):
    for ext in (".dds", ".tga", ".png"):
        p = Path(folder) / (stem + ext)
        if p.is_file():
            return p
    return None


def bbox_alpha(im, level):
    return im.split()[3].point(lambda v: 255 if v > level else 0).getbbox()


def read_sample(sample):
    """견본에서: 프레임 크기, 그림 아이콘이 놓일 칸, X 를 지운 NATO 네모와 그 안쪽 칸."""
    im = Image.open(sample).convert("RGBA")
    fw, fh = im.width // FRAMES, im.height
    f1 = im.crop((0, 0, fw, fh))
    f2 = im.crop((fw, 0, 2 * fw, fh))
    x0, y0, x1, y1 = bbox_alpha(f1, 40)                 # 철모 (그림자 포함)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = min((x1 - x0) * GROW * 1.1, fw - 2), min((y1 - y0) * GROW, fh)
    pic = (cx - w / 2, max(0, min(cy - h / 2, fh - h)), w, h)
    bx0, by0, bx1, by1 = bbox_alpha(f2, 200)            # NATO 네모 (검은 테두리 포함, 오른쪽·아래는 닫힌 좌표)
    box = f2.copy()
    px = box.load()
    inner = (bx0 + 1, by0 + 1, bx1 - 1, by1 - 1)        # 테두리 안쪽
    for y in range(inner[1], inner[3]):
        row = [px[x, y] for x in range(inner[0], inner[2])]
        light = max(row, key=lambda c: c[0] + c[1] + c[2])      # 그 줄에서 가장 밝은 점 = X 선이 없는 바탕
        for x in range(inner[0], inner[2]):
            px[x, y] = light
    return dict(size=(fw, fh), pic=pic, box=box, inner=inner)


def fit(src, w, h):
    scale = min(w / src.width, h / src.height)
    return src.resize((max(1, round(src.width * scale)), max(1, round(src.height * scale))), Image.Resampling.LANCZOS)


def render(icon_path, spec):
    from PIL import ImageFilter
    fw, fh = spec["size"]
    src = Image.open(icon_path).convert("RGBA")
    src = src.crop(src.getbbox())
    sheet = Image.new("RGBA", (fw * FRAMES, fh), (0, 0, 0, 0))
    small = fh < 20
    boost = 1.7 if small else 1.25                      # 줄이면 가는 선이 흐려지므로 진하게
    # 왼쪽: 흰 아이콘 + 어두운 테두리
    px, py, pw, ph = spec["pic"]
    ic = fit(src, pw, ph)
    alpha = ic.split()[3].point(lambda v: min(255, int(v * boost)))
    canvas = Image.new("L", (fw, fh), 0)
    canvas.paste(alpha, (int(round(px + (pw - ic.width) / 2)), int(round(py + (ph - ic.height) / 2))))
    edge = canvas.filter(ImageFilter.MaxFilter(3)).point(lambda v: int(v * (0.55 if small else 0.75)))
    left = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    left.paste(Image.new("RGBA", (fw, fh), (15, 15, 15, 255)), (0, 0), edge)
    left.paste(Image.new("RGBA", (fw, fh), (255, 255, 255, 255)), (0, 0), canvas)
    sheet.alpha_composite(left, (0, 0))
    # 오른쪽: NATO 네모 안에 검은 아이콘
    right = spec["box"].copy()
    ix0, iy0, ix1, iy1 = spec["inner"]
    pad = 0 if small else 2
    ic2 = fit(src, ix1 - ix0 - 2 * pad, iy1 - iy0 - 2 * pad)
    a2 = ic2.split()[3].point(lambda v: min(255, int(v * boost)))
    ink = Image.new("RGBA", ic2.size, (10, 10, 10, 255))
    right.paste(ink, (ix0 + (ix1 - ix0 - ic2.width) // 2, iy0 + (iy1 - iy0 - ic2.height) // 2), a2)
    sheet.alpha_composite(right, (fw, 0))
    return sheet


def write_tga(path, im):
    """32비트 무압축 TGA (왼쪽 위 원점)."""
    im = im.convert("RGBA")
    w, h = im.size
    head = bytes([0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, w & 255, w >> 8, h & 255, h >> 8, 32, 0x28])
    r, g, b, a = im.split()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(head + Image.merge("RGBA", (b, g, r, a)).tobytes())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default=str(SAMPLES))
    ap.add_argument("--sheet")
    a = ap.parse_args(argv)
    units = sorted(unit_names.UNITS)
    for u in units:
        icon_of(u)                                    # 원본이 다 있는지 먼저 확인
    found = {k: find_sample(a.samples, stem) for k, stem in KINDS}
    if not all(found.values()):
        print("UNIT_ICONS 견본 없음 (아무것도 쓰지 않음). %s 에 넣을 것:" % Path(a.samples))
        for k, stem in KINDS:
            print("  %s.dds  %s" % (stem, "있음" if found[k] else "없음"))
        return 2
    spec = {k: read_sample(found[k]) for k, _ in KINDS}
    lines = ["# generated by tools/unit_icons.py (spec 74): Arknights branch icons as sub-unit icons", "spriteTypes = {"]
    done = {}
    for u in units:
        src = icon_of(u)
        key = src.stem
        if key not in done:
            for k, _ in KINDS:
                write_tga(OUT / ("%s_%s.tga" % (key, k)), render(src, spec[k]))
            done[key] = src
        for k, _ in KINDS:
            lines.append('\tspriteType = { name = "%s" textureFile = "gfx/interface/tu_units/%s_%s.tga" noOfFrames = %d }' % (
                SPRITE[k] % u, key, k, FRAMES))
    lines.append("}")
    GFX.write_text("\n".join(lines) + "\n", encoding="ascii")
    old = MOD / "interface" / "tu_units.gfx"          # unit_roles.py 가 아츠 캐스터에 빌려 주던 대전차 아이콘
    if old.is_file():
        old.unlink()
    if a.sheet:
        zoom, cols = 4, 4
        keys = sorted(done)
        cw = (spec["medium"]["size"][0] * 2 + spec["white"]["size"][0] * 2 + spec["small"]["size"][0] * 2 + 30) * zoom
        chh = (spec["medium"]["size"][1] + 8) * zoom
        sh = Image.new("RGBA", (cw * cols, chh * ((len(keys) + cols - 1) // cols)), (58, 66, 58, 255))
        for i, key in enumerate(keys):
            x, y = (i % cols) * cw + 8, (i // cols) * chh + 8
            for k, _ in KINDS:
                im = Image.open(OUT / ("%s_%s.tga" % (key, k))).convert("RGBA")
                im = im.resize((im.width * zoom, im.height * zoom), Image.Resampling.NEAREST)
                sh.alpha_composite(im, (x, y))
                x += im.width + 8 * zoom
        sh.convert("RGB").save(a.sheet)
    print("UNIT_ICONS units=%d textures=%d sizes=%s" % (len(units), len(done) * 3, {k: spec[k]["size"] for k in spec}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
