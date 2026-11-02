#!/usr/bin/env python3
"""참고 지도 두 장에서 테라 지역 마스크를 뽑는다.
  - reference/Terra_world_map_redrawn_v.3.png: 해안선·호수·지형 (원본 해상도가 높음)
  - reference/Terra_hex_map_fandom.png: 국가 영역 (색칠된 헥스). 회색 땅은 통행 불가 + 중립 태그 WLD 소유

사용법 (python -I):
    python -I tools/mapgen/terra/extract_masks.py [--reference <png>] [--out-dir tools/mapgen/terra]

처리: 참고 지도 원본 해상도(2756x3637)에서 바다·호수·지형을 나누고, 헥스 지도를 HEX_AFFINE으로 겹쳐 국가 영역을 정한 뒤,
게임 해상도 3072x4096으로 최근접 리샘플한다 (위아래 21px 바다 패딩).
출력: regions.png (지역 색 마스크, RGB), regions.json (1a 형식 + named_states + anchors).
  - 지역 하나 = (종류, 소유국, 지형) 조합 하나. 1a 생성기가 그대로 쓴다.

좌표: 소좌표 = 참고 지도를 1000x1320으로 줄인 좌표. 참고 px = 소좌표 x 2.756.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent.parent
DEFAULT_REF = PROJECT / "reference" / "Terra_world_map_redrawn_v.3.png"
DEFAULT_HEX = PROJECT / "reference" / "Terra_hex_map_fandom.png"
SEED = 1097

GAME_W, GAME_H = 3072, 4096
PAD = 21                     # 위아래 바다 패딩 (게임 px)
REF_PER_SMALL = 2.756        # 소좌표 -> 참고 px
GAME_ROWS = GAME_H - 2 * PAD  # 참고 지도가 차지하는 게임 행 수 (4054)

# 크기와 속성 (A.6). 프로빈스 = 헥스 1칸이므로 prov_size는 헥스 면적(실행 중 계산)으로 덮어쓴다. 두 번째 값 = 주 하나의 프로빈스 수
SIZES = {
    "land": (900, 6),
    "wasteland": (2500, 6),
    "impassable": (12000, 30),
    "lake": (6000, None),
    "sea": (20000, None),
}
STRATEGIC_LAND_STATES = 8
STRATEGIC_SEA_PROVINCES = 120
# 헥스 프로빈스 격자: 헥스 지도의 헥스 격자 (위가 뾰족한 육각형, 짝수 행 기준, 홀수 행은 가로 반 칸 밀림).
# (가로 간격, 행 간격, 0행 0열 중심 x, y) — 헥스 지도 좌표. 헥스 사이 밝은 틈을 기준으로 맞춘 값.
HEX_LATTICE = (9.846, 8.525, 2.3, 6.5)

LAKE_SEEDS = [(430, 780), (395, 465), (520, 435), (250, 320), (380, 345), (450, 315), (540, 295),
              (480, 355), (570, 175), (145, 865), (265, 985)]
FORCED_SEA = [((550, 1075), (595, 1125)), ((605, 1200), (955, 1275)),
              ((600, 1080), (700, 1120))]   # 남쪽 바다의 "ÆGIR" 글씨 상자 (작은 육지 조각 방지)
FORCED_SEA_MARGIN = 30       # 강제 바다 상자를 이 참고 px만큼 넓힌 범위 (belt-and-braces 규칙)
SMALL_LAND_MAX = 2000        # 이 참고 px 미만 육지 성분만 대상

# 국가 영역: 헥스 지도(reference/Terra_hex_map_fandom.png, 821x1024, Arknights Fandom Wiki 재작도)의 색칠된 헥스.
# (태그, 기준색, 허용 상자 x0,y0,x1,y1 — 헥스 지도 좌표). 같은 태그가 여러 줄이면 합친다. 겹치면 먼저 나온 줄 우선.
HEX_COUNTRIES = [
    ("URS", (208, 56, 56), (290, 330, 620, 475)),
    ("KAZ", (85, 180, 115), (320, 420, 420, 495)),
    ("SAM", (177, 126, 205), (285, 365, 345, 405)),
    ("HIG", (100, 85, 170), (615, 370, 675, 425)),
    ("YAN", (210, 194, 80), (530, 395, 725, 535)),
    ("COL", (55, 65, 140), (160, 415, 325, 565)),
    ("BOL", (60, 195, 195), (125, 415, 235, 535)),
    ("KJE", (186, 182, 183), (305, 488, 330, 515)),
    ("VIC", (110, 106, 235), (315, 478, 452, 625)),
    ("VIC", (104, 114, 167), (322, 585, 345, 608)),   # 시에스타 헥스 -> 빅토리아
    ("LEI", (82, 116, 107), (375, 478, 485, 565)),
    ("SIR", (193, 172, 120), (448, 498, 512, 565)),
    ("KZD", (128, 151, 190), (533, 493, 553, 513)),
    ("LAT", (239, 227, 152), (432, 568, 472, 608)),
    ("MIN", (252, 187, 86), (258, 568, 292, 602)),
    ("RIM", (150, 45, 100), (495, 535, 605, 645)),
    ("SAR", (200, 178, 92), (100, 545, 365, 705)),
    ("IBE", (158, 174, 100), (378, 605, 492, 712)),
]
# 국가가 아닌 색 (회색 땅, 빙원 흰색·회색 테두리, 미지 영역, 푀엔, 바다, 배경, 글자)
HEX_OTHER = [(179, 199, 211), (176, 192, 208), (250, 250, 250), (225, 225, 225), (120, 120, 120), (30, 45, 60),
             (118, 106, 96), (40, 120, 184), (64, 136, 192), (24, 80, 120), (64, 88, 88), (255, 255, 255),
             (200, 200, 200)]
HEX_MAX_DIST = 60
# 참고 지도 -> 헥스 지도 정렬 (육지 마스크 IoU 최대화로 맞춘 값, IoU 0.80): hx = A*(rx/4) + C, hy = D*(ry/4) + E
HEX_AFFINE = (1.17865311, 29.84403986, 1.12073822, 22.01772409)
HEX_COAST_GROW_REF = 26      # 헥스 지도에서는 바다인데 참고 지도에서는 육지인 곳: 이 거리(참고 px, 약 헥스 1칸) 안이면 가까운 국가
KZD_GROW_REF = 34            # 카즈델은 헥스 1칸뿐이라 수도·정박지 두 주가 들어가도록 이만큼 넓힌다 (참고 px)
SMALL_GAP_REF = 1200         # 국가에 닿은 회색 조각이 이보다 작으면(참고 px, 헥스 약 2칸) 그 국가 땅으로
CORRIDOR_MIN_LAND = 0.6      # 통로로 쓸 칸은 육지가 칸 면적의 이 비율 이상
IMP_TERRAIN_OPEN = 4         # 통행 불가 지역 지형 조각 정리 (참고 px, 이보다 가는 띠는 이웃 지형으로)
FILLER_TAG = "WLD"           # 회색 땅(어느 나라도 아닌 땅) = 통행 불가, 이 중립 태그 소유
FILLER_CAPITAL_ISLAND = (513, 959)   # 무주지 수도: 어느 나라와도 붙지 않은 남쪽 외딴 섬 (소좌표). 이 섬만 통행 가능
COUNTRY_TAGS = []
for _t, _c, _b in HEX_COUNTRIES:
    if _t not in COUNTRY_TAGS:
        COUNTRY_TAGS.append(_t)
OWNER_TAGS = COUNTRY_TAGS + [FILLER_TAG]
CRAYAK = [(330, 590), (375, 590), (372, 700), (335, 700)]   # 크제라그 산맥 지형 (소좌표)
HEX_ICE_MAX_Y = 385          # 헥스 지도에서 이 y 미만의 흰색·회색 헥스만 빙원/미지 영역 (그 아래 흰색은 글자·문장)
HEX_LABEL_ABSORB = 4         # 국가 헥스 위의 흰 글자·문장: 이 거리(헥스 지도 px) 안이면 가까운 국가로 채운다

# 정박지·이름 있는 주 (소좌표). host = 정박지 소유국. return = 돌려줄 국가 (rho_start는 가장 가까운 국가로 계산)
NAMED = [
    {"name": "urs_capital", "small": (520, 500), "owner": "URS", "category": "town", "manpower": 50000,
     "infrastructure": 2, "capital_of": "URS"},
    {"name": "chernobog", "small": (620, 565), "owner": "URS", "category": "town", "manpower": 50000,
     "infrastructure": 2, "victory_points": 10},
    {"name": "kzd_capital", "small": (628, 615), "owner": "KZD", "category": "town", "manpower": 50000,
     "infrastructure": 2, "capital_of": "KZD"},
    # 용문 (LGM, 다각형 없는 국가의 수도 주). 염국 주 190의 프로빈스 948을 떼어 낸다. append_id: 기존 주 id를 바꾸지 않도록
    # 소속 주 분할은 그대로 두고 이 주만 기존 최대 id + 1을 받는다 (mapgen.py). 소좌표는 게임 좌표 (2130, 1880)에 해당.
    {"name": "lungmen", "small": (693.4, 605.2), "owner": "LGM", "category": "city", "manpower": 60000,
     "infrastructure": 4, "capital_of": "LGM", "victory_points": 15, "append_id": True},
]
ANCHORS = [
    {"key": "rho_start", "small": (700, 560), "host": "RHO", "return": None, "capital_of": "RHO",
     "aliases": ["rho_start"]},
    {"key": "victoria", "small": (470, 655), "host": "VIC"},
    {"key": "columbia", "small": (300, 600), "host": "COL"},
    {"key": "yan", "small": (720, 610), "host": "YAN"},
    {"key": "kazimierz", "small": (420, 560), "host": "KAZ"},
    {"key": "sargon", "small": (250, 780), "host": "SAR"},
    {"key": "iberia", "small": (540, 800), "host": "IBE"},
    {"key": "rim", "small": (650, 720), "host": "RIM"},
    {"key": "kazdel", "small": (650, 600), "host": "KZD"},
    {"key": "ursus", "small": (560, 560), "host": "URS"},
]

# 지형 코드
TERRAIN_NAMES = ["plains", "forest", "jungle", "desert", "snow_plains", "mountain"]
# 종류 코드 (픽셀 단위)
K_LAND, K_WASTE, K_IMP, K_LAKE, K_SEA = 0, 1, 2, 3, 4
KIND_NAMES = {K_LAND: "land", K_WASTE: "wasteland", K_IMP: "impassable", K_LAKE: "lake", K_SEA: "sea"}


def small_to_ref(p):
    return (p[0] * REF_PER_SMALL, p[1] * REF_PER_SMALL)


def polygon_mask(shape, pts_small):
    im = Image.new("L", (shape[1], shape[0]), 0)
    ImageDraw.Draw(im).polygon([small_to_ref(p) for p in pts_small], fill=1)
    return np.asarray(im).astype(bool)


def ref_to_game(rx, ry, ref_h, ref_w):
    """참고 px(중심) -> 게임 px."""
    gx = int((rx + 0.5) * GAME_W / ref_w)
    gy = int((ry + 0.5) * GAME_ROWS / ref_h) + PAD
    return min(max(gx, 0), GAME_W - 1), min(max(gy, 0), GAME_H - 1)


def classify(ref_rgb, hex_rgb, ref_h, ref_w, log):
    r = ref_rgb[..., 0].astype(np.int32)
    g = ref_rgb[..., 1].astype(np.int32)
    b = ref_rgb[..., 2].astype(np.int32)
    lum = (r + g + b) / 3.0

    # 1. 바다 후보
    sea_raw = ((b - r > 12) & (lum < 120)) | ((np.abs(r - 65) < 12) & (np.abs(g - 80) < 12) & (np.abs(b - 81) < 12))
    sea_raw = ndimage.binary_opening(sea_raw, iterations=2)

    # 2. 강제 바다 사각형
    for (x0, y0), (x1, y1) in FORCED_SEA:
        sea_raw[int(round(y0 * REF_PER_SMALL)):int(round(y1 * REF_PER_SMALL)) + 1,
                int(round(x0 * REF_PER_SMALL)):int(round(x1 * REF_PER_SMALL)) + 1] = True

    # 3. 테두리에 닿는 바다 성분 = 바다, 나머지 내륙 물
    lab, n = ndimage.label(sea_raw)
    border_labels = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist()) - {0}
    border_sea = np.isin(lab, list(border_labels))
    inland = sea_raw & ~border_sea
    log["water_components"] = int(n)
    log["border_sea_components"] = len(border_labels)

    # 4. 호수: 내륙 물 성분 중 호수 씨앗을 포함하는 것만
    inland_lab, _ = ndimage.label(inland)
    lake = np.zeros_like(inland)
    seed_report = []
    for sx, sy in LAKE_SEEDS:
        rx, ry = int(round(sx * REF_PER_SMALL)), int(round(sy * REF_PER_SMALL))
        if inland_lab[ry, rx] > 0:
            lake |= inland_lab == inland_lab[ry, rx]
            seed_report.append((sx, sy, "lake"))
        elif border_sea[ry, rx]:
            seed_report.append((sx, sy, "sea-border"))
        else:
            seed_report.append((sx, sy, "land"))
    log["lake_seeds"] = seed_report

    kind = np.full((ref_h, ref_w), K_LAND, np.int8)
    kind[border_sea] = K_SEA
    kind[lake] = K_LAKE

    # 2b. 강제 바다 상자 (확장 30px) 안에 있는 작은 육지 조각을 바다로 (본대륙과 떨어진, 2000 ref px 미만 성분)
    land_lab, n_land = ndimage.label(kind == K_LAND)
    fixed_islets = []
    if n_land:
        land_sizes = np.bincount(land_lab.ravel())
        land_sizes[0] = 0
        main_id = int(np.argmax(land_sizes))
        zone = np.zeros((ref_h, ref_w), bool)
        for (x0, y0), (x1, y1) in FORCED_SEA:
            rx0 = int(round(x0 * REF_PER_SMALL)) - FORCED_SEA_MARGIN
            rx1 = int(round(x1 * REF_PER_SMALL)) + FORCED_SEA_MARGIN
            ry0 = int(round(y0 * REF_PER_SMALL)) - FORCED_SEA_MARGIN
            ry1 = int(round(y1 * REF_PER_SMALL)) + FORCED_SEA_MARGIN
            zone[max(ry0, 0):min(ry1, ref_h) + 1, max(rx0, 0):min(rx1, ref_w) + 1] = True
        land_slices = ndimage.find_objects(land_lab)
        for cid in range(1, n_land + 1):
            if cid == main_id or land_sizes[cid] >= SMALL_LAND_MAX:
                continue
            sl = land_slices[cid - 1]
            comp = land_lab[sl] == cid
            if not zone[sl][comp].all():
                continue
            kv = kind[sl]
            kv[comp] = K_SEA
            fixed_islets.append([int(sl[0].start), int(sl[1].start), int(land_sizes[cid])])
    log["islets_to_sea"] = fixed_islets

    # 5. 64px 미만 육지·호수 조각 정리는 mapgen(게임 해상도)에서 한다 (1a 마스크 정리와 같음)

    # 국가 영역: 헥스 지도를 참고 지도 좌표로 옮긴다 (육지와 교집합)
    land = kind == K_LAND
    hex_own, hex_cls = hex_maps(hex_rgb)
    hh, hw = hex_own.shape
    A, C, D, E = HEX_AFFINE
    hx = np.clip(np.round(A * (np.arange(ref_w) / 4.0) + C).astype(np.int64), 0, hw - 1)
    hy = np.clip(np.round(D * (np.arange(ref_h) / 4.0) + E).astype(np.int64), 0, hh - 1)
    owner = hex_own[np.ix_(hy, hx)].astype(np.int16)
    cls = hex_cls[np.ix_(hy, hx)]
    owner[~land] = -1
    # 카즈델 넓히기 (헥스 1칸 -> 수도·정박지)
    kzd = COUNTRY_TAGS.index("KZD")
    kzd_d = ndimage.distance_transform_edt(owner != kzd)
    owner[land & (kzd_d <= KZD_GROW_REF) & (owner < 0)] = kzd
    # 해안선 차이: 헥스 지도에선 바다인 육지가 국가 가까이 있으면 그 국가
    country = owner >= 0
    dist, (iy, ix) = ndimage.distance_transform_edt(~country, return_indices=True)
    near_owner = owner[iy, ix]
    grow = land & ~country & (cls == HC_SEA) & (dist <= HEX_COAST_GROW_REF)
    owner[grow] = near_owner[grow]
    log["coast_grow_ref_px"] = int(grow.sum())
    # 작은 회색 조각 (헥스 사이 틈·구멍): 국가에 붙어 있으면 가장 가까운 국가로 (작은 통행 불가 주 방지)
    country = owner >= 0
    dist, (iy, ix) = ndimage.distance_transform_edt(~country, return_indices=True)
    near_owner = owner[iy, ix]
    rest_lab, n_rest = ndimage.label(land & ~country)
    if n_rest:
        rsz = np.bincount(rest_lab.ravel())
        rsz[0] = 0
        rmin = ndimage.minimum(dist, rest_lab, np.arange(n_rest + 1))
        small_ids = np.nonzero((rsz < SMALL_GAP_REF) & (np.asarray(rmin) <= 1.5))[0]
        small_ids = small_ids[small_ids > 0]
        gap = np.isin(rest_lab, small_ids)
        owner[gap] = near_owner[gap]
        log["small_gaps_filled"] = [int(len(small_ids)), int(gap.sum())]
    country = owner >= 0
    dist, (iy, ix) = ndimage.distance_transform_edt(~country, return_indices=True)
    near_owner = owner[iy, ix]               # 가장 가까운 국가 (모든 픽셀)

    yy, xx = np.mgrid[0:ref_h, 0:ref_w]
    y_small = yy / REF_PER_SMALL

    # 나머지 육지(회색 땅·빙원·미지 영역·푀엔) = 통행 불가, 중립 태그 소유
    rest = land & ~country
    kind[rest] = K_IMP
    north = rest & ((cls == HC_ICE) | ((cls == HC_SEA) & (hy[:, None] < HEX_ICE_MAX_Y)))   # 미지 영역 테두리 포함
    foehn = rest & (cls == HC_FOEHN) & ~north
    # 무주지 수도 섬: 통행 가능 육지로 (HOI4는 수도가 통행 불가 주면 곤란)
    island_lab, _ = ndimage.label(land)
    fx, fy = small_to_ref(FILLER_CAPITAL_ISLAND)
    island_id = island_lab[int(round(fy)), int(round(fx))]
    if island_id == 0:
        raise SystemExit("FILLER_CAPITAL_ISLAND가 육지가 아님")
    island = (island_lab == island_id) & rest
    if island.sum() > 20000:
        raise SystemExit("FILLER_CAPITAL_ISLAND가 본대륙에 붙어 있음")
    kind[island] = K_LAND
    log["filler_island_ref_px"] = int(island.sum())
    final_owner = np.where(country, owner, OWNER_TAGS.index(FILLER_TAG)).astype(np.int16)
    final_owner[~land] = -1
    log["owner_ref_px"] = {t: int((final_owner == i).sum()) for i, t in enumerate(OWNER_TAGS)}

    # 지형 (A.5): 흐린 뒤 분류
    blur = ndimage.gaussian_filter(ref_rgb.astype(np.float64), sigma=(12, 12, 0))
    br, bg, bb = blur[..., 0], blur[..., 1], blur[..., 2]
    blum = (br + bg + bb) / 3.0
    mx = np.maximum(np.maximum(br, bg), bb)
    mn = np.minimum(np.minimum(br, bg), bb)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-9), 0.0)
    snow_c = (blum > 205) & (sat < 0.12)
    forest_c = (bg > br + 5) & (bg > bb)
    desert_c = (br > bg + 25) & (br > bb + 50)
    terrain = np.zeros((ref_h, ref_w), np.int8)               # 0 plains
    terrain[snow_c] = np.where(y_small[snow_c] < 520, 4, 0)    # snow_plains 또는 plains
    fc = forest_c & ~snow_c
    terrain[fc] = np.where(y_small[fc] > 690, 2, 1)             # jungle 또는 forest
    dc = desert_c & ~snow_c & ~forest_c
    terrain[dc] = 3
    terrain[polygon_mask((ref_h, ref_w), CRAYAK) & land] = 5    # 크제라그 산맥
    terrain[north] = 4                                          # 빙원·미지 영역 = 눈
    terrain[foehn] = 3

    # 통행 불가 지역의 가는 지형 띠 정리: 폭이 좁은 지형 조각은 가장 가까운 넓은 지형으로 (X-교차 방지)
    imp = kind == K_IMP
    t_open = np.full(terrain.shape, -1, np.int8)
    for t in range(len(TERRAIN_NAMES)):
        m = ndimage.binary_opening((terrain == t) & imp, iterations=IMP_TERRAIN_OPEN)
        t_open[m] = t
    if (t_open >= 0).any():
        _, (iy, ix) = ndimage.distance_transform_edt(t_open < 0, return_indices=True)
        fix = imp & (t_open < 0)
        terrain[fix] = t_open[iy, ix][fix]
        log["imp_terrain_smoothed_ref_px"] = int(fix.sum())

    # 호수·바다는 지형 값 무관 (0)
    terrain[~land] = 0
    return kind, final_owner, terrain, near_owner, dist


HC_LAND, HC_SEA, HC_ICE, HC_FOEHN = 0, 1, 2, 3


def hex_maps(im):
    """헥스 지도 (HxWx3) -> (국가 인덱스 배열 [-1 = 없음], 종류 배열 HC_*)."""
    im = im.astype(np.int32)
    H, W, _ = im.shape
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    cls = np.full((H, W), HC_LAND, np.int8)
    bg = ((np.abs(r - 64) < 14) & (np.abs(g - 86) < 14) & (np.abs(b - 86) < 14)) | \
         ((np.abs(r - 56) < 10) & (np.abs(g - 72) < 10) & (np.abs(b - 80) < 10))
    sea = (b - r > 45) & (g - r > 30) & (r < 150)
    cls[ndimage.binary_opening(bg | sea, iterations=1)] = HC_SEA
    lum = im.sum(2) / 3.0
    ice = (lum > 235) | ((np.abs(r - g) < 10) & (np.abs(g - b) < 12) & (lum > 95) & (lum < 135)) | (lum < 60)
    ice = ndimage.binary_closing(ice, iterations=2) & (cls != HC_SEA)
    ice[HEX_ICE_MAX_Y:, :] = False
    cls[ice] = HC_ICE
    foehn = (np.abs(r - 118) < 22) & (np.abs(g - 106) < 22) & (np.abs(b - 96) < 22) & (r > b + 8)
    cls[ndimage.binary_closing(foehn, iterations=2) & (cls != HC_SEA)] = HC_FOEHN

    best = np.full((H, W), 1e9)
    own = np.full((H, W), -1, np.int16)
    oth = np.min([np.sqrt(((im - np.array(c)) ** 2).sum(2)) for c in HEX_OTHER], axis=0)
    for tag, col, (x0, y0, x1, y1) in HEX_COUNTRIES:
        d = np.full((H, W), 1e9)
        d[y0:y1, x0:x1] = np.sqrt(((im[y0:y1, x0:x1] - np.array(col)) ** 2).sum(2))
        ok = (d < best) & (d < oth) & (d < HEX_MAX_DIST)
        best[ok] = d[ok]
        own[ok] = COUNTRY_TAGS.index(tag)
    out = np.full((H, W), -1, np.int16)
    for i in range(len(COUNTRY_TAGS)):
        m = ndimage.binary_closing(own == i, structure=np.ones((3, 3)), iterations=2)
        m = ndimage.binary_fill_holes(m)
        if m.sum() > 200:
            m = ndimage.binary_opening(m, iterations=1)
        out[m & (out < 0)] = i
    # 흰 글자·문장 (빙원 밖) 이 국가에 붙어 있으면 그 국가
    mx, mn = im.max(2), im.min(2)
    label = (lum > 200) & (mx - mn < 40) & (cls != HC_SEA)
    label[:HEX_ICE_MAX_Y, :] = False
    label = ndimage.binary_dilation(label, iterations=1)
    d, (iy, ix) = ndimage.distance_transform_edt(out < 0, return_indices=True)
    take = label & (out < 0) & (d <= HEX_LABEL_ABSORB)
    out[take] = out[iy, ix][take]
    for i in range(len(COUNTRY_TAGS)):
        m = ndimage.binary_fill_holes(out == i)
        out[m & (out < 0)] = i
    cls[out >= 0] = HC_LAND
    return out, cls


def hex_cells(ref_h, ref_w):
    """게임 픽셀 (GAME_H x GAME_W) -> 헥스 칸 번호. 게임 -> 참고 -> 헥스 지도 좌표로 옮긴 뒤 가장 가까운 격자점."""
    w, rh, ox, oy = HEX_LATTICE
    A, C, D, E = HEX_AFFINE
    gx = np.arange(GAME_W, dtype=np.float64)
    gy = np.arange(GAME_H, dtype=np.float64)
    hx = A * (((gx + 0.5) * ref_w / GAME_W - 0.5) / 4.0) + C
    hy = D * (((gy - PAD + 0.5) * ref_h / GAME_ROWS - 0.5) / 4.0) + E
    HX = np.broadcast_to(hx[None, :], (GAME_H, GAME_W))
    HY = np.broadcast_to(hy[:, None], (GAME_H, GAME_W))
    r0 = np.floor((HY - oy) / rh).astype(np.int64)
    best_d = np.full((GAME_H, GAME_W), np.inf)
    best_r = np.zeros((GAME_H, GAME_W), np.int64)
    best_c = np.zeros((GAME_H, GAME_W), np.int64)
    for dr in (0, 1):
        r = r0 + dr
        off = (r % 2) * (w / 2.0)
        c = np.round((HX - ox - off) / w).astype(np.int64)
        d = (HX - (ox + off + c * w)) ** 2 + (HY - (oy + r * rh)) ** 2
        better = d < best_d
        best_d[better] = d[better]
        best_r[better] = r[better]
        best_c[better] = c[better]
    return ((best_r + 50) * 1000 + (best_c + 50)).astype(np.int64)


def hex_neighbors(cell):
    """헥스 칸 번호 -> 이웃 6칸 번호 (홀수 행이 가로 반 칸 오른쪽으로 밀린 격자)."""
    r, c = divmod(cell, 1000)
    if (r - 50) % 2 == 0:
        d = ((0, -1), (0, 1), (-1, -1), (-1, 0), (1, -1), (1, 0))
    else:
        d = ((0, -1), (0, 1), (-1, 0), (-1, 1), (1, 0), (1, 1))
    return [(r + dr) * 1000 + (c + dc) for dr, dc in d]


def connect_countries(cells, code_game, cu, maj, solid):
    """국가끼리 육지로 다 이어지게 한다 (국가 인접 그래프가 하나의 덩어리가 될 때까지).
    덩어리 사이 가장 짧은 무주지(통행 불가) 칸 길을 국가 땅으로 바꾸고, 길의 앞 절반은 출발 국가, 뒤 절반은 도착 국가가 갖는다.
    무주지 수도 섬(통행 가능 무주지)은 건드리지 않는다. 길과 양 끝 국가 칸은 육지가 넉넉한 칸(solid)만 쓴다
    (해안에 걸친 칸은 육지 조각이 끊어져 실제로 이어지지 않을 수 있음). 반환: 연 통로 목록."""
    from collections import deque
    filler = OWNER_TAGS.index(FILLER_TAG)
    code_of = dict(zip(cu.tolist(), maj.tolist()))

    def owner_of(code):
        return (code % 1000) // 10 - 1

    def is_country(cell):
        code = code_of.get(cell)
        return code is not None and code // 1000 == K_LAND and owner_of(code) != filler

    def is_waste(cell):
        code = code_of.get(cell)
        return code is not None and code // 1000 == K_IMP and owner_of(code) == filler

    tags_present = sorted({owner_of(c) for c in code_of.values() if c // 1000 == K_LAND and owner_of(c) != filler})
    corridors = []
    while True:
        # 국가 인접 그래프의 덩어리
        adj = {t: set() for t in tags_present}
        for cell, code in code_of.items():
            if not is_country(cell):
                continue
            a = owner_of(code)
            for nb in hex_neighbors(cell):
                if is_country(nb) and owner_of(code_of[nb]) != a:
                    adj[a].add(owner_of(code_of[nb]))
        group = {}
        for t in tags_present:
            if t in group:
                continue
            stack = [t]
            group[t] = t
            while stack:
                u = stack.pop()
                for v in adj[u]:
                    if v not in group:
                        group[v] = t
                        stack.append(v)
        roots = sorted(set(group.values()))
        if len(roots) == 1:
            return corridors
        # 가장 짧은 다리: 각 덩어리에서 무주지 칸으로 BFS, 다른 덩어리의 국가 칸에 닿으면 후보. 전체에서 가장 짧은 것 하나를 연다.
        best = None
        for root in roots:
            src = [cell for cell, code in code_of.items()
                   if is_country(cell) and group[owner_of(code)] == root and cell in solid]
            prev = {cell: None for cell in src}
            q = deque((cell, 0) for cell in src)
            found = None
            while q:
                u, du = q.popleft()
                if best is not None and du >= best[0]:
                    break
                for v in hex_neighbors(u):
                    if v in prev:
                        continue
                    if v not in solid:
                        continue
                    if is_country(v) and group[owner_of(code_of[v])] != root:
                        prev[v] = u
                        found = (du, v)
                        break
                    if is_waste(v):
                        prev[v] = u
                        q.append((v, du + 1))
                if found:
                    break
            if found and (best is None or found[0] < best[0]):
                path = []
                u = prev[found[1]]
                while prev[u] is not None:
                    path.append(u)
                    u = prev[u]
                path.reverse()                  # 출발 국가 쪽 -> 도착 국가 쪽 (무주지 칸만)
                best = (found[0], u, found[1], path)
        if best is None:
            raise SystemExit("국가 덩어리를 잇는 무주지 길이 없음: %s" % [OWNER_TAGS[r] for r in roots])
        _, a_cell, b_cell, path = best
        a, b = owner_of(code_of[a_cell]), owner_of(code_of[b_cell])
        half = (len(path) + 1) // 2
        for i, cell in enumerate(path):
            t = a if i < half else b
            terr = code_of[cell] % 10
            new = K_LAND * 1000 + (t + 1) * 10 + terr
            m = (cells == cell) & (code_game == code_of[cell])
            code_game[m] = new
            code_of[cell] = new
        corridors.append([OWNER_TAGS[a], OWNER_TAGS[b], len(path)])
        print("corridor %s - %s: %d cells" % (OWNER_TAGS[a], OWNER_TAGS[b], len(path)))


def resolve_owned(small, owner, idx, kind):
    """점을 참고 px로 바꾸고, 소유국 idx의 통행 가능 육지가 아니면 그 국가의 가장 가까운 육지로 옮긴다."""
    rx, ry = small_to_ref(small)
    rx, ry = int(round(rx)), int(round(ry))
    ok = (owner == idx) & ((kind == K_LAND) | (kind == K_WASTE))
    if not ok.any():
        raise SystemExit("국가 %s에 통행 가능한 육지가 없음" % OWNER_TAGS[idx])
    if ok[ry, rx]:
        return rx, ry, False
    _, (iy, ix) = ndimage.distance_transform_edt(~ok, return_indices=True)
    return int(ix[ry, rx]), int(iy[ry, rx]), True


def resolve_point(small, kind, ref_h, ref_w, log_name):
    """점을 참고 px로 바꾸고, 통행 불가/바다면 가장 가까운 통행 가능 육지로 옮긴다."""
    rx, ry = small_to_ref(small)
    rx, ry = int(round(rx)), int(round(ry))
    passable = (kind == K_LAND) | (kind == K_WASTE)
    if passable[ry, rx]:
        return rx, ry, False
    _, (iy, ix) = ndimage.distance_transform_edt(~passable, return_indices=True)
    return int(ix[ry, rx]), int(iy[ry, rx]), True


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="참고 지도 -> 테라 지역 마스크")
    ap.add_argument("--reference", default=str(DEFAULT_REF))
    ap.add_argument("--hex-map", default=str(DEFAULT_HEX))
    ap.add_argument("--out-dir", default=str(HERE))
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ref = np.asarray(Image.open(args.reference).convert("RGB"))
    ref_h, ref_w = ref.shape[:2]
    log = {"reference_size": [ref_w, ref_h]}
    print("reference %dx%d" % (ref_w, ref_h))
    hex_rgb = np.asarray(Image.open(args.hex_map).convert("RGB"))
    kind, owner, terrain, near_owner, dist = classify(ref, hex_rgb, ref_h, ref_w, log)

    # 이름 있는 주·정박지 점 해석 (통행 가능으로 옮김)
    named_out = []
    for item in NAMED:
        host = "YAN" if item.get("append_id") else item["owner"]   # 용문은 염국 주에서 떼어 낸다
        rx, ry, moved = resolve_owned(item["small"], owner, OWNER_TAGS.index(host), kind)
        gx, gy = ref_to_game(rx, ry, ref_h, ref_w)
        d = {k: v for k, v in item.items() if k != "small"}
        d.update({"x": gx, "y": gy, "moved": moved, "ref": [rx, ry]})
        named_out.append(d)
    anchors_out = []
    for item in ANCHORS:
        if item["host"] in COUNTRY_TAGS:
            rx, ry, moved = resolve_owned(item["small"], owner, OWNER_TAGS.index(item["host"]), kind)
        else:
            rx, ry, moved = resolve_point(item["small"], kind, ref_h, ref_w, item["key"])
        gx, gy = ref_to_game(rx, ry, ref_h, ref_w)
        d = {k: v for k, v in item.items() if k != "small"}
        # 반환 대상: rho_start는 가장 가까운 국가 영역의 태그, 나머지는 원주인(host)
        if item["key"] == "rho_start":
            d["return"] = OWNER_TAGS[int(near_owner[ry, rx])]
        else:
            d["return"] = item["host"]
        d.update({"x": gx, "y": gy, "moved": moved, "ref": [rx, ry]})
        anchors_out.append(d)
    log["moved_points"] = [d["name"] if "name" in d else d["key"] for d in named_out + anchors_out if d["moved"]]

    # 게임 해상도 최근접 리샘플: 위아래 PAD는 바다
    rows = np.arange(GAME_H)
    cols = np.arange(GAME_W)
    in_map = (rows >= PAD) & (rows < PAD + GAME_ROWS)
    ref_rows = np.clip(np.floor((rows - PAD + 0.5) * ref_h / GAME_ROWS).astype(np.int64), 0, ref_h - 1)
    ref_cols = np.clip(np.floor((cols + 0.5) * ref_w / GAME_W).astype(np.int64), 0, ref_w - 1)
    # 종류/소유국/지형을 하나의 지역 코드로 합친다
    code_ref = np.where(kind == K_SEA, 4000,
                np.where(kind == K_LAKE, 3000,
                         kind.astype(np.int32) * 1000 + (owner.astype(np.int32) + 1) * 10 + terrain.astype(np.int32)))
    code_game = code_ref[np.ix_(ref_rows, ref_cols)]
    code_game[~in_map, :] = 4000
    # 테두리 24px는 바다 (1a 규칙: 가장자리 육지 금지). 참고 지도에서 육지가 가장자리에 닿는 곳을 잘라낸다.
    margin = np.zeros((GAME_H, GAME_W), bool)
    margin[:24, :] = True
    margin[-24:, :] = True
    margin[:, :24] = True
    margin[:, -24:] = True
    cut = int(((code_game != 4000) & margin).sum())
    code_game[margin] = 4000
    log["margin_land_cut_px"] = cut
    # 헥스 프로빈스: 게임 픽셀마다 헥스 칸을 정하고, 칸 안의 육지는 다수결로 지역 하나 (나라·지형이 칸 단위가 된다).
    # 해안선·호수는 픽셀 단위 그대로 (해안 칸은 해안선에 잘린 육각형).
    cells = hex_cells(ref_h, ref_w)
    landpx = (code_game != 4000) & (code_game != 3000)
    cu, cinv = np.unique(cells[landpx], return_inverse=True)
    ku, kinv = np.unique(code_game[landpx], return_inverse=True)
    cnt = np.zeros((len(cu), len(ku)), np.int32)
    np.add.at(cnt, (cinv, kinv), 1)
    maj = ku[np.argmax(cnt, axis=1)]
    before = code_game[landpx]
    code_game[landpx] = maj[cinv]
    log["hex_cells_land"] = int(len(cu))
    log["hex_majority_changed_px"] = int((before != code_game[landpx]).sum())
    full_area = float(np.median(np.bincount(np.unique(cells, return_inverse=True)[1].ravel())))
    land_px = dict(zip(cu.tolist(), cnt.sum(axis=1).tolist()))
    solid = {c for c, n in land_px.items() if n >= CORRIDOR_MIN_LAND * full_area}
    log["land_corridors"] = connect_countries(cells, code_game, cu, maj, solid)
    cell_area = int(np.median(np.bincount(np.unique(cells, return_inverse=True)[1].ravel())))
    log["hex_cell_area_px"] = cell_area
    cid = cells.astype(np.uint32)
    Image.fromarray(np.stack([(cid >> 16) & 255, (cid >> 8) & 255, cid & 255], -1).astype(np.uint8)).save(
        out_dir / "hexcells.png")

    # 대각선으로만 닿는 같은 지역 (2x2에서 a==d, b!=a, c!=a, b!=c) 을 없앤다: b를 a로. 프로빈스 X-교차가 풀리지 않는 원인.
    diag_fixes = 0
    for _ in range(50):
        a, b, c, d = code_game[:-1, :-1], code_game[:-1, 1:], code_game[1:, :-1], code_game[1:, 1:]
        m1 = (a == d) & (b != a) & (c != a) & (b != c)
        m2 = (b == c) & (a != b) & (d != b) & (a != d)
        if not (m1.any() or m2.any()):
            break
        ys, xs = np.nonzero(m1)
        code_game[ys, xs + 1] = code_game[ys, xs]
        ys, xs = np.nonzero(m2 & ~m1)
        code_game[ys, xs] = code_game[ys, xs + 1]
        diag_fixes += int(m1.sum() + (m2 & ~m1).sum())
    log["diagonal_region_fixes"] = diag_fixes

    # 이름 있는 주·정박지 점을 칸 판정 뒤에 다시 놓는다: 소유국 육지 칸 안, 서로 다른 칸, 칸 중심에 가까운 픽셀
    taken = set()
    for d in named_out + anchors_out:
        if d.get("append_id"):
            tag = "YAN"
        elif "host" in d:
            tag = d["host"] if d["host"] in COUNTRY_TAGS else d["return"]
        else:
            tag = d["owner"]
        oi = OWNER_TAGS.index(tag)
        ok = (code_game // 1000 == K_LAND) & ((code_game % 1000) // 10 - 1 == oi) & (code_game < 3000)
        cand_cells = np.unique(cells[ok])
        cand_cells = [c for c in cand_cells.tolist() if c not in taken]
        if not cand_cells:
            raise SystemExit("%s: 국가 %s에 빈 육지 칸이 없음" % (d.get("name", d.get("key")), tag))
        ys, xs = np.nonzero(ok & np.isin(cells, cand_cells))
        cc = cells[ys, xs]
        order = np.argsort(cc, kind="stable")
        ys, xs, cc = ys[order], xs[order], cc[order]
        starts = np.r_[0, np.nonzero(np.diff(cc))[0] + 1]
        ends = np.r_[starts[1:], len(cc)]
        best = None
        for a0, a1 in zip(starts.tolist(), ends.tolist()):
            if a1 - a0 < 200:      # 해안에 잘린 작은 조각 칸은 피한다
                continue
            my, mx = ys[a0:a1].mean(), xs[a0:a1].mean()
            dist2 = (mx - d["x"]) ** 2 + (my - d["y"]) ** 2
            if best is None or dist2 < best[0]:
                k = int(np.argmin((xs[a0:a1] - mx) ** 2 + (ys[a0:a1] - my) ** 2)) + a0
                best = (dist2, int(cc[a0]), int(xs[k]), int(ys[k]))
        if best is None:
            raise SystemExit("%s: 국가 %s에 충분히 큰 칸이 없음" % (d.get("name", d.get("key")), tag))
        _, cell, nx, ny = best
        if (nx, ny) != (d["x"], d["y"]):
            d["moved"] = True
        d["x"], d["y"] = nx, ny
        taken.add(cell)
    log["moved_points"] = [d["name"] if "name" in d else d["key"] for d in named_out + anchors_out if d["moved"]]
    uniq, inv = np.unique(code_game, return_inverse=True)
    inv = inv.reshape(GAME_H, GAME_W)

    # 지역 목록 (코드 -> 정의)
    rng = np.random.default_rng(SEED)
    colors = []
    used = {(0, 0, 0)}
    for _ in range(len(uniq)):
        while True:
            c = tuple(int(v) for v in rng.integers(0, 256, 3))
            if c not in used:
                break
        used.add(c)
        colors.append(c)
    lut = np.array(colors, dtype=np.uint8)
    rgb = lut[inv]
    Image.fromarray(rgb).save(out_dir / "regions.png")

    regions = []
    per_kind = {}
    for i, code in enumerate(uniq.tolist()):
        if code == 4000:
            kname, owner_tag, terr = "sea", None, None
            rid = "sea"
        elif code == 3000:
            kname, owner_tag, terr = "lake", None, None
            rid = "lake"
        else:
            k = code // 1000
            o = (code % 1000) // 10 - 1
            t = code % 10
            kname = KIND_NAMES[k]
            owner_tag = OWNER_TAGS[o] if o >= 0 else "NONE"
            terr = TERRAIN_NAMES[t]
            rid = "%s_%s_%s" % (kname, owner_tag, terr)
        per_kind[kname] = per_kind.get(kname, 0) + 1
        entry = {"color": list(colors[i]), "id": rid, "kind": kname}
        if kname in ("sea", "lake"):
            entry["prov_size"] = cell_area
        else:
            if owner_tag is None or owner_tag == "NONE":
                raise SystemExit("owner missing for region %s" % rid)
            entry["owner"] = owner_tag
            entry["terrain"] = terr
            entry["prov_size"], entry["state_size"] = cell_area, SIZES[kname][1]
        regions.append(entry)

    config = {
        "map_size": [GAME_W, GAME_H],
        "regions": regions,
        "named_states": named_out,
        "anchors": anchors_out,
        "strategic_land_states": STRATEGIC_LAND_STATES,
        "strategic_sea_provinces": STRATEGIC_SEA_PROVINCES,
        "cells": "hexcells.png",
        "source": {"reference": str(Path(args.reference).name), "hex_map": str(Path(args.hex_map).name), "pad": PAD},
    }
    (out_dir / "regions.json").write_text(json.dumps(config, indent=1, ensure_ascii=True) + "\n", encoding="ascii")

    stats = {"kinds_ref_px": {KIND_NAMES[k]: int((kind == k).sum()) for k in KIND_NAMES},
             "regions_by_kind": per_kind, "regions": len(regions)}
    print(json.dumps({"stats": stats, "log": log}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
