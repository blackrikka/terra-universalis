#!/usr/bin/env python3
"""우르수스 중점 트리 조각 합치기. merge_focus.py --tag URS 의 얇은 래퍼 (검사 규칙과 출력은 merge_focus.py 에 있다).

사용법:
    python -I tools/focusgen/merge_urs.py                 # 전체 검사 후 tu_urs.txt 생성
    python -I tools/focusgen/merge_urs.py --check <part>  # <part> 조각만 검사 (파일을 쓰지 않음)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I 모드에서는 스크립트 폴더가 경로에 없다
import merge_focus  # noqa: E402

if __name__ == "__main__":
    sys.exit(merge_focus.main(["--tag", "URS", *sys.argv[1:]]))
