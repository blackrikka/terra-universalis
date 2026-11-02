#!/usr/bin/env python3
"""바닐라 HOI4 설치가 없는 환경(클라우드 세션 등)에서 지도 빌드를 돌리기 위한 '대체 바닐라 폴더'를 만든다.

사용법 (python -I):
    python -I tools/mapgen/make_vanilla_shim.py --out <폴더> [--mod terra_universalis]
    python -I tools/mapgen/terra/build_terra.py --vanilla <폴더>

mapgen / build_countries / validate_map이 바닐라에서 읽는 것은 대부분 이미 모드 산출물 안에 그대로 들어 있다.
이 도구는 반드시 '지도를 다시 만들기 전'의 모드 폴더(커밋된 상태)에서 실행해야 한다.

  바닐라 파일                                   대체 출처 (모드)
  map/{terrain,rivers,cities,trees}.bmp 팔레트   같은 이름의 모드 BMP (validate 16번이 팔레트 동일을 보장)
  map/terrain/colormap_rgb_cityemissivemask_a.dds 모드 colormap (지형 색표 = 지형 인덱스별 평균색이 그대로 나옴)
  map/terrain/colormap_water_0.dds, fow_*.dds    모드 파일 (한 가지 색으로 채워진 그림이라 평균이 같음)
  map/strategicregions/1-Southern England.txt     모드 전략 지역 파일의 weather 블록
  common/country_tags/zz_dynamic_countries.txt    모드의 같은 파일 + 그것이 참조하는 common/countries/*.txt
  common/countries/colors.txt                     모드 colors.txt (동적 태그 색 항목 포함)
  portraits/00_portraits.txt                      모드 tu_portraits.txt (continent 이름만 europe으로)
  interface/*.gfx                                 모드 캐릭터 파일에 쓰인 초상화 GFX 이름 목록
      -> validate 17번(초상화 GFX가 바닐라에 정의됐는지)은 이 모드에서 실질적으로 검사되지 않는다. 실제 PC에서 다시 확인할 것.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT = Path(__file__).resolve().parent.parent.parent


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="모드 산출물로 대체 바닐라 폴더 만들기")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mod", default="terra_universalis")
    args = ap.parse_args(argv)
    mod = PROJECT / args.mod
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)

    def copy(src_rel, dst_rel=None):
        dst = out / (dst_rel or src_rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(mod / src_rel, dst)

    for name in ("terrain.bmp", "rivers.bmp", "cities.bmp", "trees.bmp"):
        copy("map/" + name)

    # colormap: mapgen은 바닐라 terrain.bmp를 colormap 크기로 최근접 축소해 지형 인덱스별 평균색을 구한다.
    # 모드 colormap은 terrain[0::2, 0::2]의 색표 값이므로, 같은 표본 위치의 terrain을 '바닐라 terrain.bmp'로 둔다.
    terr = Image.open(mod / "map" / "terrain.bmp")
    t_half = np.asarray(terr)[0::2, 0::2]
    half = Image.fromarray(t_half, mode="P")
    half.putpalette(terr.getpalette())
    (out / "map").mkdir(parents=True, exist_ok=True)
    half.save(out / "map" / "terrain.bmp")
    for name in ("colormap_rgb_cityemissivemask_a.dds", "colormap_water_0.dds", "fow_rgb_waterspec_a.dds"):
        copy("map/terrain/" + name)

    # weather 블록 (모든 전략 지역이 같은 블록을 쓴다)
    strat = sorted((mod / "map" / "strategicregions").glob("*.txt"))[0]
    copy("map/strategicregions/" + strat.name, "map/strategicregions/1-Southern England.txt")

    # 동적 국가
    copy("common/country_tags/zz_dynamic_countries.txt")
    zz = (mod / "common" / "country_tags" / "zz_dynamic_countries.txt").read_bytes().decode("utf-8-sig")
    for rel in sorted(set(re.findall(r'"(countries/[^"]+)"', zz))):
        copy("common/" + rel)
    copy("common/countries/colors.txt")

    # 초상화
    pt = (mod / "portraits" / "tu_portraits.txt").read_text(encoding="utf-8-sig")
    (out / "portraits").mkdir(parents=True, exist_ok=True)
    (out / "portraits" / "00_portraits.txt").write_text(pt.replace("name = terra", "name = europe", 1), encoding="utf-8")
    (out / "portraits" / "998_scientist_portraits.txt").write_text("", encoding="utf-8")

    # 초상화 GFX 이름
    names = set()
    for f in (mod / "common" / "characters").glob("*.txt"):
        names.update(re.findall(r'\b(?:large|small)\s*=\s*"?([A-Za-z0-9_]+)"?', f.read_bytes().decode("utf-8-sig")))
    (out / "interface").mkdir(parents=True, exist_ok=True)
    (out / "interface" / "tu_shim.gfx").write_text(
        "spriteTypes = {\n" + "".join('\tspriteType = { name = "%s" texturefile = "x.dds" }\n' % n for n in sorted(names))
        + "}\n", encoding="utf-8")
    print("VANILLA_SHIM ok -> %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
