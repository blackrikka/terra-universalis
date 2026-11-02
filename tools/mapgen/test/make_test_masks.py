#!/usr/bin/env python3
"""합성 테스트 마스크 생성 (512x768, 테두리 24px 바다).

사용법: python -I tools/mapgen/test/make_test_masks.py [--seed 1097]

생성물 (이 스크립트 폴더):
    regions.png      지역 색 마스크 (RGB)
    regions.json     지역 정의 (mapgen 입력)
    countries.json   테스트 국가 TUA, TUB (build_countries 입력)

구성: 노이즈 섞인 큰 대륙 1개(육지 약 45%) + 작은 섬 1개, 대륙 서쪽 TUA(plains, 북쪽 forest),
동쪽 TUB(hills, 남쪽 desert), 가운데 남북 산맥 impassable(TUA), 산맥 중간의 폭 40px 황무지 회랑 wasteland(TUB),
섬 TUB(jungle), 작은 호수 1개.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

W, H = 512, 768
TEST_DIR = Path(__file__).resolve().parent

REGIONS = [
    {"color": [0, 0, 128], "id": "sea", "kind": "sea", "prov_size": 3000},
    {"color": [40, 200, 200], "id": "lake_tua", "kind": "lake", "prov_size": 300},
    {"color": [200, 60, 60], "id": "tua_core", "kind": "land", "owner": "TUA",
     "terrain": "plains", "prov_size": 500, "state_size": 6},
    {"color": [120, 90, 60], "id": "tua_north", "kind": "land", "owner": "TUA",
     "terrain": "forest", "prov_size": 500, "state_size": 6},
    {"color": [150, 150, 150], "id": "waste_imp", "kind": "impassable", "owner": "TUA",
     "terrain": "mountain", "prov_size": 1500, "state_size": 4},
    {"color": [180, 160, 100], "id": "waste_pass", "kind": "wasteland", "owner": "TUB",
     "terrain": "desert", "prov_size": 700, "state_size": 5},
    {"color": [60, 90, 200], "id": "tub_core", "kind": "land", "owner": "TUB",
     "terrain": "hills", "prov_size": 500, "state_size": 6},
    {"color": [90, 140, 220], "id": "tub_south", "kind": "land", "owner": "TUB",
     "terrain": "desert", "prov_size": 500, "state_size": 6},
    {"color": [60, 200, 60], "id": "tub_island", "kind": "land", "owner": "TUB",
     "terrain": "jungle", "prov_size": 300, "state_size": 3},
]

COUNTRIES = [
    {"tag": "TUA", "name_ko": "테스트 서국", "name_en": "Test West", "adj_ko": "서국", "adj_en": "Western",
     "color": [200, 60, 60]},
    {"tag": "TUB", "name_ko": "테스트 동국", "name_en": "Test East", "adj_ko": "동국", "adj_en": "Eastern",
     "color": [60, 90, 200]},
]

# 산맥 / 회랑 / 섬 / 호수 위치
RIDGE_X0, RIDGE_X1 = 236, 276          # 남북 산맥 x 범위 (폭 40)
CORRIDOR_Y0, CORRIDOR_Y1 = 360, 400    # 회랑 y 범위 (폭 40)
NORTH_Y = 300                          # TUA 북쪽 forest 경계
SOUTH_Y = 520                          # TUB 남쪽 desert 경계


def make_continent(rng):
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy, a, b = 256.0, 384.0, 180.0, 330.0
    dist = np.sqrt(((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2)
    noise = ndimage.gaussian_filter(rng.standard_normal((H, W)), 28.0)
    noise = noise / noise.std() * 0.12
    field = dist + noise
    # 타원 안에서만 대륙을 잘라낸다. 전체 지도에 분위수를 쓰면 노이즈 때문에 테두리 24px 바로 위까지 번져 평평하게 잘린다.
    inside = dist <= 1.0
    thr = np.quantile(field[inside], 0.95)
    land = inside & (field <= thr)
    land = ndimage.binary_fill_holes(land)
    lab, n = ndimage.label(land)
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    land = lab == int(np.argmax(sizes))
    land[:24, :] = False
    land[-24:, :] = False
    land[:, :24] = False
    land[:, -24:] = False
    return land, yy, xx


def make_disc(yy, xx, cy, cx, ry, rx):
    return ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1.0


def main(argv=None):
    parser = argparse.ArgumentParser(description="합성 테스트 마스크 생성")
    parser.add_argument("--seed", type=int, default=1097)
    args = parser.parse_args(argv)
    rng = np.random.default_rng(args.seed)

    land, yy, xx = make_continent(rng)
    island = make_disc(yy, xx, 660, 440, 14, 14) & (~land)
    island[:24, :] = False
    island[-24:, :] = False
    island[:, :24] = False
    island[:, -24:] = False
    lake = make_disc(yy, xx, 430, 150, 10, 16) & land
    if lake.sum() < 64:
        raise SystemExit("lake too small")
    land = land & ~lake

    # 지역 색 채우기 (인덱스 = REGIONS 순서)
    region_of = {r["id"]: i for i, r in enumerate(REGIONS)}
    idx = np.full((H, W), region_of["sea"], dtype=np.int32)
    idx[lake] = region_of["lake_tua"]

    ridge = (xx >= RIDGE_X0) & (xx < RIDGE_X1)
    corridor = (yy >= CORRIDOR_Y0) & (yy < CORRIDOR_Y1)
    west = (xx < RIDGE_X0)
    east = (xx >= RIDGE_X1)

    main_land = land
    idx[main_land & west & (yy < NORTH_Y)] = region_of["tua_north"]
    idx[main_land & west & (yy >= NORTH_Y)] = region_of["tua_core"]
    idx[main_land & east & (yy >= SOUTH_Y)] = region_of["tub_south"]
    idx[main_land & east & (yy < SOUTH_Y)] = region_of["tub_core"]
    idx[main_land & ridge & corridor] = region_of["waste_pass"]
    idx[main_land & ridge & ~corridor] = region_of["waste_imp"]
    idx[island] = region_of["tub_island"]

    # 모든 육지·호수 지역을 대륙/섬 마스크 안으로 제한한다 (테두리 바다 보장)
    shape_mask = land | island | lake
    idx[~shape_mask] = region_of["sea"]
    assert not (shape_mask[:24].any() or shape_mask[-24:].any()
                or shape_mask[:, :24].any() or shape_mask[:, -24:].any()), "land inside 24px border"

    colors = np.array([r["color"] for r in REGIONS], dtype=np.uint8)
    rgb = colors[idx]
    out_dir = TEST_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb, "RGB").save(out_dir / "regions.png")

    config = {
        "map_size": [W, H],
        "regions": REGIONS,
        "strategic_land_states": 6,
        "strategic_sea_provinces": 8,
    }
    (out_dir / "regions.json").write_text(json.dumps(config, indent=2) + "\n", encoding="ascii")
    (out_dir / "countries.json").write_text(json.dumps(COUNTRIES, indent=2) + "\n", encoding="ascii")

    total = W * H
    print(f"land fraction {(land | island).sum() / total:.3f} (main {land.sum()}, island {island.sum()}, lake {lake.sum()})")
    for i, r in enumerate(REGIONS):
        print(f"  {r['id']:12s} {int((idx == i).sum()):7d} px")
    print("wrote", out_dir / "regions.png", out_dir / "regions.json", out_dir / "countries.json")


if __name__ == "__main__":
    main()
