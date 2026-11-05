# Terra Universalis

명일방주(Arknights)의 테라 대륙을 무대로 한 Hearts of Iron IV 총변환 모드입니다. 로도스 아일랜드를 중심으로 테라력 1097년에 시작합니다.

- 게임 버전: HOI4 1.19.x (기본 게임 기능 위주, DLC 기능은 분기 처리)
- 언어: 한국어 · 영어

## 내용
- **테라 커스텀 지도**: 3072×4096, 헥스 프로빈스 약 10,700개(육지 4,500·바다 5,900·호수 240), 주 621개, 국가 20개 + 무주지 중립 태그 (참고 지도에서 자동 생성)
  - 해안선·지형: `reference/Terra_world_map_redrawn_v.3.png`, 국가 영토: `reference/Terra_hex_map_fandom.png`(헥스 지도)
  - 프로빈스는 헥스 지도의 헥스 1칸 = 1개 (해안·호숫가만 실제 해안선에 잘림)
  - 어느 나라에도 속하지 않은 회색 땅은 통행 불가, 중립 태그 `WLD`(무주지) 소유
  - 모든 나라가 육지로 이어지도록 짧은 통로(헥스 1~3칸) 10개를 국가 땅으로 열었다
- **7개국 상세 구현**: 로도스 아일랜드, 우르수스, 빅토리아, 염국, 카즈델, 용문, 리유니온 — 국가당 100~400개 중점, 국가 디시전, 국가 이벤트
- **디시전 중심 외교**: 공통 외교 디시전(사절단·무역·문화 교류·방위 동맹·공작·국정 운영), 중점으로 해금
- **체르노보그 사태**: 리유니온 등장 → 용문 국지전 이벤트 체인
- 국기·초상화: 명일방주 공식 문장과 일러스트 (개인용)

## 폴더
| 폴더 | 내용 |
|---|---|
| `terra_universalis/` | 모드 본체 (게임이 읽는 폴더) |
| `tools/` | 생성·검사 도구 (지도 생성, 중점 트리 합치기·자동 배치, 국기·초상화 빌드, 린트), 모드 편집기(`tools/editor/`) |
| `docs/` | 기획서와 단계별 사양서 |
| `reference/` | 참고 지도, 국가 문장, 캐릭터 일러스트 원본 |

## 설치
1. `Documents/Paradox Interactive/Hearts of Iron IV/mod/terra_universalis.mod` 파일을 만들고, `path`가 이 저장소의 `terra_universalis` 폴더를 가리키게 합니다.
2. Paradox 런처에서 이 모드만 넣은 플레이셋을 만들어 실행합니다 (지도와 국가를 모두 바꾸므로 다른 모드와 함께 쓰지 않습니다).

## 빌드
```
python -I tools/mapgen/terra/build_terra.py      # 지도·주·국가·국기 생성
python -I tools/vanilla_cleanup.py               # 바닐라 정리(튜토리얼·습격 덮어쓰기 등)
python -I tools/focusgen/merge_focus.py --tag VIC   # 중점 트리 조각 합치기 + 자동 배치 (태그별)
python -I tools/portraits/build_portraits.py     # 초상화
python -I tools/gauges/build_gauges.py           # 디시전 탭의 수치 막대 (변수 범위·기준값이 바뀌면 다시 실행)
python -I tools/lint/tu_lint.py                  # 정적 검사
python -I tools/editor/server.py                 # 모드 편집기 (브라우저에서 중점·디시전·국민정신·캐릭터·이벤트 편집)
```

바닐라 HOI4가 설치되지 않은 환경(클라우드 세션 등)에서는 지도를 다시 만들기 전에 대체 폴더를 만들어 씁니다.
```
python -I tools/mapgen/make_vanilla_shim.py --out <임시 폴더>
python -I tools/mapgen/terra/build_terra.py --vanilla <임시 폴더> --skip-check-refs
```

## 저작권
명일방주의 세계관·캐릭터·문장·일러스트의 저작권은 Hypergryph / Yostar에 있습니다. 이 저장소는 개인 비영리 팬 작업입니다.
