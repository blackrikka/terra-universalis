#!/usr/bin/env python3
"""테라 연구 화면 GUI 생성 (사양서 21). build_techs.py 가 부른다.

    interface/countrytechtreeview.gui  (바닐라 같은 이름 덮어쓰기)

- 공통 틀(탭 버튼, 정보 창, 기술 상자 틀, 선 그림 등)은 기준 파일에서 그대로 가져온다:
    reference/vanilla/interface/countrytechtreeview.gui 가 있으면 그것, 없으면 tools/techgen/base/countrytechtreeview_base.gui
    (base 는 1.19.4 대응 공개 모드 Kaiserreich 의 파일 = 바닐라 파생. 바닐라 파일을 넣으면 그쪽을 쓴다.)
- 기술 폴더 컨테이너(infantry_folder … electronics_folder)는 새로 만든다:
    갈래 뿌리 기술마다 "<뿌리>_tree" 그리드박스 (모두 같은 원점 → 기술 좌표가 곧 폴더 좌표), 칸 70x70, UPPER_LEFT.
    왼쪽에 테라력 연도 눈금, 위에 갈래 제목 (로컬라이제이션 키 TU_TECH_YEAR_<연도>, TU_TECHCOL_<폴더>_<열>).
    바닐라 배경 그림(연도·선이 박힌 그림)은 쓰지 않는다.
- 탭 아이콘: 오리지늄 공학 = 산업 탭 그림, 광석병 의학 = 지원 탭 그림 (닻 그림 대신).
"""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MOD = REPO / "terra_universalis"
SLOT = 70
GX, GY = 110, 110          # 그리드 원점 (폴더 안)
COL = 3                    # 열 간격 (칸)
TAB_ICON = {"mtgnavalfolder_tab": "GFX_industry_folder_tab", "mtgnavalsupportfolder_tab": "GFX_support_folder_tab"}


def base_path():
    v = REPO / "reference" / "vanilla" / "interface" / "countrytechtreeview.gui"
    return v if v.is_file() else HERE / "base" / "countrytechtreeview_base.gui"


def child_blocks(s, start, end):
    """start..end 사이 직속 블록: (머리말, 여는 괄호 위치, 닫는 괄호 위치)"""
    out, depth, i, hdr_start, a = [], 0, start, start, None
    while i < end:
        c = s[i]
        if c == "#":
            j = s.find("\n", i)
            i = end if j < 0 else j
            continue
        if c == '"':
            i = s.find('"', i + 1) + 1
            continue
        if c == "{":
            if depth == 0:
                a = i
                hdr_start = s.rfind("\n", 0, i) + 1
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                out.append((s[hdr_start:a].strip(), hdr_start, a, i))
        i += 1
    return out


def name_of(s, a, b):
    m = re.search(r'name\s*=\s*"([^"]+)"', s[a:b])
    return m.group(1) if m else None


def folder_container(name, techs, era_rows, col_titles):
    """techs: [(id, x, y)] (이미 GUI 칸 좌표). era_rows: [(row, year)]."""
    ncols = (max((x for _, x, _ in techs), default=0) // COL) + 1
    width = GX + ncols * COL * SLOT + 200
    height = GY + (max((r for r, _ in era_rows), default=12) + 2) * SLOT + 80
    L = []
    for row, year in era_rows:
        L.append("""				instantTextBoxType = {
					name = "tu_year_%d"
					position = { x = 8 y = %d }
					font = "hoi_20bs"
					borderSize = { x = 0 y = 0 }
					text = "TU_TECH_YEAR_%d"
					maxWidth = 80
					maxHeight = 24
					format = left
					Orientation = "UPPER_LEFT"
				}""" % (year, GY + row * SLOT + 22, year))
    for idx in range(ncols):
        if (name, idx) in col_titles:
            L.append("""				instantTextBoxType = {
					name = "tu_col_%d"
					position = { x = %d y = 40 }
					font = "hoi_20bs"
					borderSize = { x = 0 y = 0 }
					text = "TU_TECHCOL_%s_%d"
					maxWidth = 200
					maxHeight = 24
					format = left
					Orientation = "UPPER_LEFT"
				}""" % (idx, GX + idx * COL * SLOT - 50, name.upper(), idx))
    roots = sorted({r for r in col_titles.get(("roots", name), [])})
    grids = "\n".join("""			gridboxtype = {
				name = "%s_tree"
				position = { x = %d y = %d }
				slotsize = { width = %d height = %d }
				format = "UPPER_LEFT"
			}""" % (r, GX, GY, SLOT, SLOT) for r in roots)
    return """containerWindowType = {
			name = "%s"
			position = { x=0 y=47 }
			size = { width = 100%%%% height = 100%%%% }
			margin = { top = 13 left = 13 bottom = 24 right = 25 }
			drag_scroll = { left middle }
			verticalScrollbar = "right_vertical_slider"
			horizontalScrollbar = "bottom_horizontal_slider"
			scroll_wheel_factor = 40

			background = {
				name = "Background"
				quadTextureSprite ="GFX_tiled_window_2b_border"
			}

			containerWindowType = {
				name = "size_filler"
				position = { x=0 y=0 }
				size = {
					width = %d height = %d
					min = { width = 100%%%% height = 100%%%% }
				}
				clipping = no

%s
			}

%s
		}""" % (name, width, height, "\n\n".join(L), grids)


def build(TECHS, ERA, folders, all_folders, col_names):
    """TECHS: build_techs 의 기술 목록 (x 는 이미 GUI 칸 좌표로 바뀐 것). folders: 기술이 있는 폴더.
    col_names: {(folder, idx): (ko, en)}. 반환: 로컬라이제이션 (ko 목록, en 목록)."""
    s = base_path().read_text(encoding="utf-8-sig")
    top = child_blocks(s, s.index("{") + 1, s.rindex("}"))
    view = next(b for b in top if name_of(s, b[2], b[3]) == "countrytechtreeview")
    _, vh, va, vb = view
    leads = {n for t in TECHS for n in t["leads"]}
    titles = dict(col_names)
    for f in all_folders:
        titles[("roots", f)] = [t["id"] for t in TECHS if t["folder"] == f and t["id"] not in leads]
    era_rows = sorted({(row, year) for year, row in ERA.values()})
    inner = s[va + 1:vb]
    out, pos = [], 0
    for hdr, h0, a, b in child_blocks(inner, 0, len(inner)):
        nm = name_of(inner, a, b)
        if nm in all_folders:
            techs = [(t["id"], t["x"], ERA[t["era"]][1]) for t in TECHS if t["folder"] == nm]
            out.append(inner[pos:h0])
            out.append("\t\t" + folder_container(nm, techs, era_rows if techs else [], titles))
            pos = b + 1
    out.append(inner[pos:])
    new_inner = "".join(out)
    for tab, icon in TAB_ICON.items():
        new_inner = re.sub(r'(name\s*=\s*"%s"(?:(?!quadTextureSprite).)*?quadTextureSprite\s*=\s*)"[^"]+"' % tab,
                           r'\1"%s"' % icon, new_inner, count=1, flags=re.S)
    gui = s[:va + 1] + new_inner + s[vb:]
    head = ("# Terra Universalis research screen (tools/techgen/build_techgui.py). Folder containers are generated;\n"
            "# the common frame comes from %s.\n" % base_path().relative_to(REPO))
    (MOD / "interface").mkdir(exist_ok=True)
    (MOD / "interface" / "countrytechtreeview.gui").write_text(head + gui, encoding="utf-8")
    assert gui.count("{") == gui.count("}")
    ko, en = [], []
    for year, _ in ERA.values():
        ko.append(("TU_TECH_YEAR_%d" % year, str(year)))
        en.append(("TU_TECH_YEAR_%d" % year, str(year)))
    for (f, idx), (k, e) in col_names.items():
        ko.append(("TU_TECHCOL_%s_%d" % (f.upper(), idx), k))
        en.append(("TU_TECHCOL_%s_%d" % (f.upper(), idx), e))
    return ko, en
