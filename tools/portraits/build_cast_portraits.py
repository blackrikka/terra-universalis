#!/usr/bin/env python3
"""명일방주 공식 일러스트 → 지도자·장군·원수 초상화 (사양서 39).

사용법 (python -I):
    python -I tools/portraits/build_cast_portraits.py [--art-dir ../terrauniverse] [--sheet <대조표.png>]
    그다음 python -I tools/chargen/build_characters.py  (캐릭터 파일의 portraits 를 바꾼다)

입력
    tools/portraits/cast_portraits.json   캐릭터 id -> 일러스트 파일 이름 (blackrikka/Terrauniverse 저장소)
    tools/portraits/cast_faces.json       일러스트 -> [얼굴 중심 x, 얼굴 중심 y, 얼굴 크기] (일러스트 불투명 영역 대비 비율)
                                          애니메이션 얼굴 검출(lbpcascade_animeface)로 구하고 대조표를 보며 손으로 고쳤다.
출력
    terra_universalis/gfx/leaders/TU/ak/<key>.tga               큰 초상화 156x210
    terra_universalis/gfx/interface/ideas/TU/ak/<key>_small.tga 작은 초상화 65x67
    terra_universalis/interface/tu_cast_portraits.gfx          GFX_TU_ak_<key>, GFX_TU_ak_<key>_small
<key> 는 일러스트마다 ak0, ak1, ... 가 아니라 캐릭터 id 와 무관한 일러스트 이름의 ASCII 해시다 (같은 그림은 한 번만 만든다).
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_portraits import composite_opaque, write_tga, LARGE_SIZE, SMALL_SIZE  # noqa: E402

PROJECT = HERE.parents[1]
MOD = PROJECT / "terra_universalis"
LARGE_DIR = MOD / "gfx" / "leaders" / "TU" / "ak"
SMALL_DIR = MOD / "gfx" / "interface" / "ideas" / "TU" / "ak"
GFX_PATH = MOD / "interface" / "tu_cast_portraits.gfx"
CAST = HERE / "cast_portraits.json"
FACES = HERE / "cast_faces.json"

HEAD_TO_CROP = 3.0      # 큰 초상화 세로 = 얼굴 크기 x 이 값 (머리와 어깨)
FACE_Y = 0.36           # 큰 초상화에서 얼굴 중심의 세로 위치
SMALL_OF_LARGE = 0.78   # 작은 초상화 한 변 = 큰 초상화 너비 x 이 값 (얼굴 중심 기준)


def key_of(art):
    return "ak_" + hashlib.md5(art.encode("utf-8")).hexdigest()[:10]


def sprite(art):
    return "GFX_TU_%s" % key_of(art)


def crop_box(cx, cy, w, h):
    return (int(round(cx - w / 2)), int(round(cy - h / 2)), int(round(cx + w / 2)), int(round(cy + h / 2)))


def render(path, face):
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.getbbox())
    w, h = im.size
    fx, fy, fs = face
    hx, hy, F = fx * w, fy * h, fs * h
    ch = F * HEAD_TO_CROP
    cw = ch * LARGE_SIZE[0] / LARGE_SIZE[1]
    top = hy - FACE_Y * ch
    pad = int(max(ch, cw))
    canvas = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(im, (pad, pad))
    lbox = (int(hx - cw / 2) + pad, int(top) + pad, int(hx + cw / 2) + pad, int(top + ch) + pad)
    big = canvas.crop(lbox).resize((LARGE_SIZE[0] * 4, LARGE_SIZE[1] * 4), Image.Resampling.LANCZOS)
    large = composite_opaque(big.resize(LARGE_SIZE, Image.Resampling.LANCZOS))
    # 작은 초상화(참모·장군 칸 65x67)는 큰 초상화의 얼굴 부분에서 자른다: 큰 초상화와 틀이 항상 같다
    # (사용자 보고: 따로 계산하던 때 글래디아는 모자만, 울피아누스는 얼굴이 잘려 나왔다)
    W4, H4 = big.size
    side = W4 * SMALL_OF_LARGE
    cy = H4 * FACE_Y
    sbox = (int(W4 / 2 - side / 2), int(cy - 0.45 * side), int(W4 / 2 + side / 2), int(cy + 0.55 * side))
    small = composite_opaque(big.crop(sbox).resize(SMALL_SIZE, Image.Resampling.LANCZOS))
    return large, small


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--art-dir", default=str(PROJECT.parent / "terrauniverse"))
    ap.add_argument("--sheet")
    a = ap.parse_args(argv)
    art_dir = Path(a.art_dir)
    cast = json.loads(CAST.read_text(encoding="utf-8"))["cast"]
    faces = json.loads(FACES.read_text(encoding="utf-8"))
    faces.pop("_note", None)
    arts = sorted(set(cast.values()))
    missing = [x for x in arts if x not in faces]
    if missing:
        raise SystemExit("얼굴 위치 없음: %s" % missing)
    items = []
    lines = ["spriteTypes = {"]
    for art in arts:
        large, small = render(art_dir / art, faces[art])
        k = key_of(art)
        write_tga(LARGE_DIR / ("%s.tga" % k), large)
        write_tga(SMALL_DIR / ("%s_small.tga" % k), small)
        lines += ["\tspriteType = {", '\t\tname = "%s"' % sprite(art), '\t\ttexturefile = "gfx/leaders/TU/ak/%s.tga"' % k, "\t}",
                  "\tspriteType = {", '\t\tname = "%s_small"' % sprite(art),
                  '\t\ttexturefile = "gfx/interface/ideas/TU/ak/%s_small.tga"' % k, "\t}"]
        items.append((art, large, small))
    lines.append("}")
    GFX_PATH.write_text("\n".join(lines) + "\n", encoding="ascii")
    if a.sheet:
        cols, cw, chh = 6, 240, 250
        rows = (len(items) + cols - 1) // cols
        sh = Image.new("RGB", (cols * cw, rows * chh), (20, 20, 24))
        d = ImageDraw.Draw(sh)
        for i, (art, large, small) in enumerate(items):
            x0, y0 = (i % cols) * cw, (i // cols) * chh
            sh.paste(large, (x0 + 4, y0 + 4))
            sh.paste(small, (x0 + 166, y0 + 4))
            d.text((x0 + 166, y0 + 80), "#%d" % i, fill=(255, 255, 0))
        sh.save(a.sheet)
    print("CAST_PORTRAITS arts=%d characters=%d" % (len(arts), len(cast)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
