# 사양서 21 — 연구 화면 GUI, 작은 오류 2건

> 작성·구현: 2026-11-04 (PC 확인 7cd6e54: 크래시 해결 → 남은 기술 화면 문제)

## 1. 연구 화면 (`tools/techgen/build_techgui.py`, build_techs.py 가 부름)
- 문제: 기술은 "갈래 뿌리 기술_tree" 그리드박스에 놓이는데 바닐라 GUI 를 그대로 써서,
  테라 고유 갈래 29개 기술이 "Found no grid box" (오리지늄·광석병 탭 빈 화면, 굴착·암호 줄기 없음),
  요새 줄기가 바닐라 칸(원자력 연구)에 표시, 연도 눈금·칸 제목·탭 아이콘이 바닐라 그대로였다.
- 이제 모드가 `interface/countrytechtreeview.gui` 를 생성한다.
  - 기술 폴더 컨테이너 11개(숨긴 nsb/bba 포함)를 새로 만든다. 갈래 뿌리 25개마다 `<뿌리>_tree` 그리드박스, 칸 70x70, UPPER_LEFT, 모두 같은 원점.
  - 기술 좌표: 폴더마다 쓰는 열을 차례로 번호 매겨 3칸 간격(큰 기술 상자 183px 가 겹치지 않음), 시대마다 2칸.
  - 왼쪽에 테라력 연도 눈금(`TU_TECH_YEAR_1090`~`1112`), 위에 갈래 제목(`TU_TECHCOL_<폴더>_<열>` = 갈래 첫 기술 이름).
  - 바닐라 배경 그림(연도·선이 박힌 그림)은 쓰지 않는다. 기술 사이 선은 엔진이 칸을 따라 그린다.
  - 탭 아이콘: 오리지늄 공학 = 산업 탭 그림, 광석병 의학 = 지원 탭 그림.
  - 공통 틀(탭 버튼, 정보 창, 기술 상자 틀, 선 그림)은 기준 파일에서 가져온다:
    `reference/vanilla/interface/countrytechtreeview.gui` 가 있으면 그것, 없으면 `tools/techgen/base/countrytechtreeview_base.gui`
    (1.19.4 대응 Kaiserreich 파일 = 바닐라 파생). 바닐라 파일을 넣고 build_techs.py 를 다시 돌리면 그쪽을 쓴다.
- 생성 때 모든 기술의 뿌리 그리드박스가 같은 폴더에 있는지 검사했다 (빠진 것 0).

## 2. 작은 오류
- `tu_yan_sibling_decisions.txt`: available 안 all_country 의 limit → `OR = { NOT = { 형제 세력 } AND = { 해방됨, 속국 아님, 전쟁 아님 } }`.
- `tu_ideologies.txt`: 없는 모디파이어 take_states_cost_factor 2줄 삭제.

## 3. PC에서 확인
- error.log 의 "Found no grid box" 0건, 각 탭에서 기술 위치·선·연도 눈금·갈래 제목.
- 기준 파일 쪽 틀 때문에 생기는 sprite 경고가 있으면 알려 주기 (바닐라 파일을 넣으면 사라진다).
