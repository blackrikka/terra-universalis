#!/usr/bin/env python3
"""참고 지도(reference/Terra_world_map_redrawn_v.3.png)에서 테라 지역 마스크를 뽑는다.

사용법 (python -I):
    python -I tools/mapgen/terra/extract_masks.py [--reference <png>] [--out-dir tools/mapgen/terra]

처리: 참고 지도 원본 해상도(2756x3637)에서 바다·호수·국가 영역·황무지·지형을 나눈 뒤,
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
SEED = 1097

GAME_W, GAME_H = 3072, 4096
PAD = 21                     # 위아래 바다 패딩 (게임 px)
REF_PER_SMALL = 2.756        # 소좌표 -> 참고 px
GAME_ROWS = GAME_H - 2 * PAD  # 참고 지도가 차지하는 게임 행 수 (4054)

# 크기와 속성 (A.6)
SIZES = {
    "land": (900, 6),
    "wasteland": (2500, 6),
    "impassable": (12000, 8),
    "lake": (6000, None),
    "sea": (20000, None),
}
STRATEGIC_LAND_STATES = 8
STRATEGIC_SEA_PROVINCES = 10
WASTE_DIST_SMALL = 20.0      # 황무지 최대 거리 (소좌표)

LAKE_SEEDS = [(430, 780), (395, 465), (520, 435), (250, 320), (380, 345), (450, 315), (540, 295),
              (480, 355), (570, 175), (145, 865), (265, 985)]
FORCED_SEA = [((550, 1075), (595, 1125)), ((605, 1200), (955, 1275)),
              ((600, 1080), (700, 1120))]   # 남쪽 바다의 "ÆGIR" 글씨 상자 (작은 육지 조각 방지)
FORCED_SEA_MARGIN = 30       # 강제 바다 상자를 이 참고 px만큼 넓힌 범위 (belt-and-braces 규칙)
SMALL_LAND_MAX = 2000        # 이 참고 px 미만 육지 성분만 대상

# 국가 영역 (소좌표 다각형). 겹치면 목록에서 먼저 나온 국가가 가진다.
COUNTRY_POLYS = [
    ("URS", [(350, 488), (400, 470), (470, 462), (560, 445), (620, 432), (690, 440), (705, 470), (700, 520),
             (660, 545), (630, 575), (590, 580), (560, 590), (520, 580), (470, 560), (450, 535), (400, 525),
             (355, 505)]),
    ("KZD", [(575, 592), (635, 585), (668, 595), (672, 630), (640, 650), (600, 645), (585, 620)]),
    ("KAZ", [(380, 530), (460, 530), (462, 595), (380, 595)]),
    ("LEI", [(470, 605), (575, 605), (578, 652), (470, 660)]),
    ("VIC", [(370, 605), (468, 605), (470, 660), (510, 665), (510, 700), (370, 700)]),
    ("SIR", [(520, 625), (584, 625), (584, 670), (520, 670)]),
    ("LAT", [(512, 703), (548, 703), (548, 742), (512, 742)]),
    ("IBE", [(480, 760), (600, 765), (600, 880), (480, 880)]),
    ("RIM", [(605, 680), (700, 680), (700, 790), (605, 790)]),
    ("YAN", [(670, 510), (760, 505), (800, 520), (870, 540), (870, 600), (820, 650), (720, 655), (680, 640),
             (675, 600)]),
    ("HIG", [(755, 462), (808, 462), (808, 520), (755, 520)]),
    ("COL", [(245, 535), (350, 535), (350, 680), (245, 680)]),
    ("BOL", [(140, 540), (245, 540), (245, 645), (140, 645)]),
    ("SAM", [(322, 468), (392, 468), (392, 502), (322, 502)]),
    ("KJE", [(340, 615), (372, 615), (372, 650), (340, 650)]),
    ("MIN", [(296, 715), (326, 715), (326, 745), (296, 745)]),
    ("SAR", [(90, 700), (380, 700), (380, 870), (90, 870)]),
]
FOEHN = [(90, 860), (470, 860), (480, 960), (90, 960)]
CRAYAK = [(330, 590), (375, 590), (372, 700), (335, 700)]
NORTH_Y_SMALL = 455          # 이 소좌표 y 미만 비국가 육지 -> 통행 불가 (인피 빙원 북부 / 미지 영역)

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


def classify(ref_rgb, ref_h, ref_w, log):
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

    # 국가 영역 (육지와 교집합, 먼저 나온 국가 우선)
    owner = np.full((ref_h, ref_w), -1, np.int16)
    land = kind == K_LAND
    for idx, (tag, poly) in enumerate(COUNTRY_POLYS):
        m = polygon_mask((ref_h, ref_w), poly) & land & (owner < 0)
        owner[m] = idx
    country = owner >= 0

    yy, xx = np.mgrid[0:ref_h, 0:ref_w]
    y_small = yy / REF_PER_SMALL

    # 통행 불가 고정 구역 (국가 영역이 아닌 육지)
    north = land & ~country & (y_small < NORTH_Y_SMALL)
    foehn = polygon_mask((ref_h, ref_w), FOEHN) & land & ~country & ~north
    fixed_zone = north | foehn

    # 나머지 육지: 가장 가까운 국가 영역까지 거리로 황무지 / 통행 불가
    dist, (iy, ix) = ndimage.distance_transform_edt(~country, return_indices=True)
    near_owner = owner[iy, ix]               # 가장 가까운 국가 (모든 픽셀)
    leftover = land & ~country & ~fixed_zone
    waste_limit = WASTE_DIST_SMALL * REF_PER_SMALL
    kind[leftover & (dist <= waste_limit)] = K_WASTE
    kind[leftover & (dist > waste_limit)] = K_IMP
    kind[fixed_zone] = K_IMP
    log["waste_dist_limit_ref_px"] = round(waste_limit, 2)

    # 소유국: 국가 영역은 자기 국가, 나머지 육지는 가장 가까운 국가
    final_owner = np.where(country, owner, near_owner).astype(np.int16)
    final_owner[~land] = -1

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
    terrain[north] = 4                                          # 통행 불가 고정 구역 terrain 우선
    terrain[foehn] = 3

    # 호수·바다는 지형 값 무관 (0)
    terrain[~land] = 0
    return kind, final_owner, terrain, near_owner, dist


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
    ap.add_argument("--out-dir", default=str(HERE))
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ref = np.asarray(Image.open(args.reference).convert("RGB"))
    ref_h, ref_w = ref.shape[:2]
    log = {"reference_size": [ref_w, ref_h]}
    print("reference %dx%d" % (ref_w, ref_h))
    kind, owner, terrain, near_owner, dist = classify(ref, ref_h, ref_w, log)

    # 이름 있는 주·정박지 점 해석 (통행 가능으로 옮김)
    named_out = []
    for item in NAMED:
        rx, ry, moved = resolve_point(item["small"], kind, ref_h, ref_w, item["name"])
        gx, gy = ref_to_game(rx, ry, ref_h, ref_w)
        d = {k: v for k, v in item.items() if k != "small"}
        d.update({"x": gx, "y": gy, "moved": moved, "ref": [rx, ry]})
        named_out.append(d)
    anchors_out = []
    for item in ANCHORS:
        rx, ry, moved = resolve_point(item["small"], kind, ref_h, ref_w, item["key"])
        gx, gy = ref_to_game(rx, ry, ref_h, ref_w)
        d = {k: v for k, v in item.items() if k != "small"}
        # 반환 대상: rho_start는 가장 가까운 국가 영역의 태그, 나머지는 원주인(host)
        if item["key"] == "rho_start":
            d["return"] = COUNTRY_POLYS[int(near_owner[ry, rx])][0]
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
            owner_tag = COUNTRY_POLYS[o][0] if o >= 0 else "NONE"
            terr = TERRAIN_NAMES[t]
            rid = "%s_%s_%s" % (kname, owner_tag, terr)
        per_kind[kname] = per_kind.get(kname, 0) + 1
        entry = {"color": list(colors[i]), "id": rid, "kind": kname}
        if kname in ("sea", "lake"):
            entry["prov_size"] = SIZES[kname][0]
        else:
            if owner_tag is None or owner_tag == "NONE":
                raise SystemExit("owner missing for region %s" % rid)
            entry["owner"] = owner_tag
            entry["terrain"] = terr
            entry["prov_size"], entry["state_size"] = SIZES[kname]
        regions.append(entry)

    config = {
        "map_size": [GAME_W, GAME_H],
        "regions": regions,
        "named_states": named_out,
        "anchors": anchors_out,
        "strategic_land_states": STRATEGIC_LAND_STATES,
        "strategic_sea_provinces": STRATEGIC_SEA_PROVINCES,
        "source": {"reference": str(Path(args.reference).name), "pad": PAD},
    }
    (out_dir / "regions.json").write_text(json.dumps(config, indent=1, ensure_ascii=True) + "\n", encoding="ascii")

    stats = {"kinds_ref_px": {KIND_NAMES[k]: int((kind == k).sum()) for k in KIND_NAMES},
             "regions_by_kind": per_kind, "regions": len(regions)}
    print(json.dumps({"stats": stats, "log": log}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
