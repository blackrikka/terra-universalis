#!/usr/bin/env python3
"""reference/portraits 의 공식 아트 -> 모드 지도자 초상화 (큰 것 156x210, 작은 것 65x67) + interface/tu_portraits.gfx.

사용법 (python -I):
    python -I tools/portraits/build_portraits.py [--sheet <대조표 png 경로>]

입력: reference/portraits/<key>.png (RGBA, 투명 배경), tools/portraits/crops.json (키별 얼굴 중심, 300px 타일 대비 비율)
출력:
    terra_universalis/gfx/leaders/TU/<key>.tga                 큰 초상화 156x210 (바닐라 gfx/leaders 와 같은 규격)
    terra_universalis/gfx/interface/ideas/TU/<key>_small.tga   작은 초상화 65x67 (바닐라 gfx/interface/ideas 와 같은 규격)
    terra_universalis/interface/tu_portraits.gfx               GFX_TU_portrait_<key>, GFX_TU_portrait_<key>_small 스프라이트 정의
"""

import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
REF_DIR = PROJECT_DIR / "reference" / "portraits"
CROPS_PATH = PROJECT_DIR / "tools" / "portraits" / "crops.json"
MOD_DIR = PROJECT_DIR / "terra_universalis"
LARGE_DIR = MOD_DIR / "gfx" / "leaders" / "TU"
SMALL_DIR = MOD_DIR / "gfx" / "interface" / "ideas" / "TU"
GFX_PATH = MOD_DIR / "interface" / "tu_portraits.gfx"

T = 300                       # 대비 타일 한 변
LARGE_SIZE = (156, 210)       # 큰 초상화 (w, h)
SMALL_SIZE = (65, 67)         # 작은 초상화 / 고문 아이콘 (w, h)
SMALL_SCALE = 0.62            # 작은 정사각 크롭 한 변 = 0.62 * cw
GRAD_TOP = (70, 72, 82)       # 배경 그라데이션 위쪽
GRAD_BOTTOM = (35, 36, 42)    # 배경 그라데이션 아래쪽


def gradient(w, h):
    """세로 그라데이션 불투명 RGBA 배경."""
    t = np.linspace(0.0, 1.0, h)[:, None]
    rgb = np.array(GRAD_TOP, float) * (1 - t) + np.array(GRAD_BOTTOM, float) * t   # (h, 3)
    arr = np.empty((h, w, 3), np.uint8)
    arr[:] = np.round(rgb)[:, None, :].astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def composite_opaque(layer):
    """투명 배경 레이어를 그라데이션 위에 합성해 불투명 RGB로 만든다."""
    bg = gradient(*layer.size)
    return Image.alpha_composite(bg, layer).convert("RGB")


def face_geometry(im, fx, fy):
    """트리밍된 아트 im 과 얼굴 중심 비율 (fx, fy)로 얼굴 좌표와 큰 크롭 박스를 구한다."""
    w, h = im.size
    s = min(T / w, T / h)
    ox = (T - w * s) / 2
    oy = (T - h * s) / 2
    hx = (fx * T - ox) / s
    hy = (fy * T - oy) / s
    ch = 0.30 * max(h, w)
    cw = ch * LARGE_SIZE[0] / LARGE_SIZE[1]
    box = (int(hx - cw / 2), int(hy - 0.30 * ch), int(hx - cw / 2 + cw), int(hy - 0.30 * ch + ch))
    return hx, hy, cw, box


def render(key, fx, fy):
    """키 하나의 큰 초상화와 작은 초상화 (둘 다 불투명 RGB)를 만든다."""
    im = Image.open(REF_DIR / ("%s.png" % key)).convert("RGBA")
    im = im.crop(im.getbbox())
    hx, hy, cw, box = face_geometry(im, fx, fy)
    large = composite_opaque(im.crop(box).resize(LARGE_SIZE, Image.Resampling.LANCZOS))
    side = SMALL_SCALE * cw
    top = hy - 0.08 * side          # crops.json 의 얼굴 좌표가 이마·머리 쪽이라, 작은 아이콘은 그보다 아래를 담는다
    sbox = (int(hx - side / 2), int(top), int(hx - side / 2 + side), int(top + side))
    small = composite_opaque(im.crop(sbox).resize(SMALL_SIZE, Image.Resampling.LANCZOS))
    return large, small


def write_tga(path, img):
    """32bit 비압축 TGA (BGRA, 원점 왼쪽 아래). build_countries.py write_tga 와 같은 방식."""
    w, h = img.size
    rgba = np.asarray(img.convert("RGBA"), dtype=np.uint8)
    bgra = np.ascontiguousarray(rgba[:, :, [2, 1, 0, 3]])
    # HOI4 는 TGA 원점 비트를 무시하고 아래쪽부터 읽는다 (국기가 뒤집혀 나왔음): 원점 왼쪽 아래(0x08)로 행을 뒤집어 쓴다
    header = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x08)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + np.ascontiguousarray(bgra[::-1]).tobytes())


def write_gfx(keys):
    """interface/tu_portraits.gfx: 키마다 큰 것과 _small 스프라이트 두 개."""
    lines = ["spriteTypes = {"]
    for key in keys:
        lines += [
            "\tspriteType = {",
            '\t\tname = "GFX_TU_portrait_%s"' % key,
            '\t\ttexturefile = "gfx/leaders/TU/%s.tga"' % key,
            "\t}",
            "\tspriteType = {",
            '\t\tname = "GFX_TU_portrait_%s_small"' % key,
            '\t\ttexturefile = "gfx/interface/ideas/TU/%s_small.tga"' % key,
            "\t}",
        ]
    lines.append("}")
    GFX_PATH.parent.mkdir(parents=True, exist_ok=True)
    GFX_PATH.write_text("\n".join(lines) + "\n", encoding="ascii")


def contact_sheet(items, path):
    """키, 큰 초상화, 작은 초상화 목록을 한 장의 대조표 png로 만든다."""
    cols = 5
    cell_w, cell_h = 250, 250
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (20, 20, 24))
    draw = ImageDraw.Draw(sheet)
    for i, (key, large, small) in enumerate(items):
        x0 = (i % cols) * cell_w
        y0 = (i // cols) * cell_h
        sheet.paste(large, (x0 + 8, y0 + 8))
        sheet.paste(small, (x0 + 176, y0 + 8))
        draw.text((x0 + 8, y0 + 8 + LARGE_SIZE[1] + 8), "%s  (large | small)" % key, fill=(230, 230, 230))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="지도자 초상화 생성 (공식 아트 기반)")
    parser.add_argument("--sheet", help="생성된 큰/작은 초상화 대조표 png 저장 경로 (선택)")
    args = parser.parse_args(argv)

    crops = json.loads(CROPS_PATH.read_text(encoding="utf-8"))
    crops.pop("_note", None)
    keys = sorted(crops)
    items = []
    for key in keys:
        if not (REF_DIR / ("%s.png" % key)).is_file():
            raise SystemExit("reference 아트 없음: %s" % key)
        fx, fy = crops[key]
        large, small = render(key, fx, fy)
        write_tga(LARGE_DIR / ("%s.tga" % key), large)
        write_tga(SMALL_DIR / ("%s_small.tga" % key), small)
        items.append((key, large, small))
        print("rendered %s" % key)
    write_gfx(keys)
    if args.sheet:
        contact_sheet(items, Path(args.sheet))
        print("sheet: %s" % args.sheet)
    print("BUILD_PORTRAITS ok keys=%d large=%s small=%s gfx=%s" % (len(keys), LARGE_DIR, SMALL_DIR, GFX_PATH))
    return 0


if __name__ == "__main__":
    sys.exit(main())
