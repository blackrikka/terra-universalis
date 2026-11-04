#!/usr/bin/env python3
"""TerraEditor.exe 를 만든다 (PyInstaller, 파이썬 없는 PC 에서도 실행됨).

    python -I tools/editor/build_exe.py

결과: tools/editor/dist/TerraEditor.exe (git 에는 올리지 않음).
exe 는 자기 위치에서 위로 올라가며 저장소를 찾으므로 dist 에 그대로 두거나 저장소 안 아무 곳에 두면 되고,
다른 곳에 두면 처음 켤 때 저장소 폴더를 한 번 물어본다.
"""

import math
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent


def png(size, pixel):
    rows = b"".join(b"\0" + b"".join(bytes(pixel(x, y, size)) for x in range(size)) for y in range(size))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def inside(px, py):
    """0..1 좌표: 0 = 바깥, 1 = 배경, 2 = 금색 육각 테두리, 3 = 글자 T."""
    r = 0.16
    qx, qy = max(abs(px - .5) - (.5 - r), 0), max(abs(py - .5) - (.5 - r), 0)
    if qx * qx + qy * qy > r * r:
        return 0
    dx, dy = px - .5, py - .5
    ang = math.atan2(dy, dx) + math.pi / 6
    sector = math.pi / 3
    a = (ang % sector) - sector / 2
    dist = math.hypot(dx, dy) * math.cos(a)       # 육각형 거리 (꼭짓점이 위아래)
    if .3 < dist < .38:
        return 2
    if (.32 < px < .68 and .3 < py < .39) or (.455 < px < .545 and .3 < py < .71):
        return 3
    return 1


COLORS = {0: (0, 0, 0, 0), 1: (30, 33, 41, 255), 2: (212, 167, 60, 255), 3: (228, 230, 235, 255)}


def pixel(x, y, size, n=4):
    acc = [0, 0, 0, 0]
    for i in range(n):
        for j in range(n):
            c = COLORS[inside((x + (i + .5) / n) / size, (y + (j + .5) / n) / size)]
            for k in range(3):
                acc[k] += c[k] * c[3]
            acc[3] += c[3]
    if acc[3] == 0:
        return (0, 0, 0, 0)
    return tuple(min(255, round(acc[k] / acc[3])) for k in range(3)) + (round(acc[3] / (n * n)),)


def make_icons(out_ico, out_png):
    sizes = [16, 32, 48, 256]
    imgs = [png(s, pixel) for s in sizes]
    head = struct.pack("<HHH", 0, 1, len(sizes))
    off = 6 + 16 * len(sizes)
    dirs = b""
    for s, data in zip(sizes, imgs):
        dirs += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(data), off)
        off += len(data)
    out_ico.write_bytes(head + dirs + b"".join(imgs))
    out_png.write_bytes(png(64, pixel))


def main():
    if subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], capture_output=True).returncode:
        print("PyInstaller 설치 중…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "pyinstaller"])
    ico = HERE / "icon.ico"
    make_icons(ico, HERE / "static" / "icon.png")
    work = Path(tempfile.mkdtemp(prefix="tu_editor_build_"))
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
           "--name", "TerraEditor", "--icon", str(ico),
           "--add-data", "%s;static" % (HERE / "static"),
           "--paths", str(HERE),
           "--distpath", str(HERE / "dist"), "--workpath", str(work / "build"), "--specpath", str(work),
           str(HERE / "app.py")]
    subprocess.check_call(cmd)
    print("\n완성:", HERE / "dist" / "TerraEditor.exe")


if __name__ == "__main__":
    main()
