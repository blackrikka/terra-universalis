#!/usr/bin/env python3
"""테라 지도 한 번에 빌드: 마스크 추출 -> mapgen -> build_countries -> validate -> tu_lint (-> check_refs가 있으면).

사용법 (python -I):
    python -I tools/mapgen/terra/build_terra.py [--mod terra_universalis]

각 단계는 python -I 자식 프로세스로 실행하고, 단계마다 걸린 시간을 보고한다. 하나라도 실패하면 1로 끝난다.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAPGEN = HERE.parent
PROJECT = MAPGEN.parent.parent
TERRA_REGIONS = HERE / "regions.png"
TERRA_CONFIG = HERE / "regions.json"
TERRA_COUNTRIES = HERE / "countries.json"
LINT = PROJECT / "tools" / "lint" / "tu_lint.py"
CHECK_REFS = PROJECT / "tools" / "check_refs.py"


def run(label, cmd):
    print("=== %s" % label, flush=True)
    print("    " + " ".join(str(c) for c in cmd), flush=True)
    t0 = time.time()
    proc = subprocess.run([sys.executable, "-I"] + [str(c) for c in cmd], cwd=str(PROJECT))
    dt = time.time() - t0
    print("    [%s] exit=%d time=%.1fs" % (label, proc.returncode, dt), flush=True)
    return proc.returncode, dt


def main(argv=None):
    ap = argparse.ArgumentParser(description="테라 지도 한 번에 빌드")
    ap.add_argument("--mod", default="terra_universalis")
    ap.add_argument("--vanilla", default=None, help="바닐라 설치 경로 (없으면 각 도구의 기본값). 대체 폴더는 make_vanilla_shim.py")
    ap.add_argument("--skip-check-refs", action="store_true", help="check_refs 생략 (바닐라 documentation 폴더가 없을 때)")
    ap.add_argument("--skip-extract", action="store_true", help="regions.png/json이 이미 있으면 마스크 추출을 건너뜀")
    args = ap.parse_args(argv)

    van = ["--vanilla", args.vanilla] if args.vanilla else []
    steps = []
    t_all = time.time()
    if not args.skip_extract:
        steps.append(("extract_masks", [HERE / "extract_masks.py"]))
    steps.append(("mapgen", [MAPGEN / "mapgen.py", "--regions", TERRA_REGIONS, "--config", TERRA_CONFIG,
                             "--mod", args.mod] + van))
    steps.append(("build_countries", [MAPGEN / "build_countries.py", "--countries", TERRA_COUNTRIES,
                                      "--mod", args.mod] + van))
    steps.append(("validate_map", [MAPGEN / "validate_map.py", "--mod", args.mod,
                                   "--countries", TERRA_COUNTRIES] + van))
    steps.append(("tu_lint", [LINT]))
    if CHECK_REFS.is_file() and not args.skip_check_refs:
        steps.append(("check_refs", [CHECK_REFS]))

    results = []
    failed = None
    for label, cmd in steps:
        rc, dt = run(label, cmd)
        results.append((label, rc, dt))
        if rc != 0:
            failed = label
            break
    total = time.time() - t_all
    print("=== summary", flush=True)
    for label, rc, dt in results:
        print("    %-16s exit=%d  %.1fs" % (label, rc, dt), flush=True)
    print("    total %.1fs (limit 600s)" % total, flush=True)
    if failed:
        print("BUILD_TERRA FAIL at %s" % failed, flush=True)
        return 1
    print("BUILD_TERRA ok", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
