#!/usr/bin/env python3
"""비압축 32bit DDS 쓰기 (사양서 0절 헤더 사양: BGRA, pitch = w*4, mipmap 1, 비트마스크 R/G/B/A).

사용법: from dds import write_dds, build_header  (python -I로 실행하는 스크립트에서 import)
"""

import struct

import numpy as np

DDS_MAGIC = b"DDS "
DDSD_FLAGS = 0x100F          # CAPS | HEIGHT | WIDTH | PITCH | PIXELFORMAT
DDPF_FLAGS = 0x41            # RGB | ALPHAPIXELS
DDSCAPS_TEXTURE = 0x1000
HEADER_SIZE = 128            # 매직 4 + 헤더 124


def build_header(width, height):
    """w x h 비압축 BGRA DDS 헤더(128바이트)를 만든다."""
    hdr = DDS_MAGIC
    # dwSize, dwFlags, dwHeight, dwWidth, dwPitchOrLinearSize, dwDepth, dwMipMapCount
    hdr += struct.pack("<7I", 124, DDSD_FLAGS, height, width, width * 4, 0, 1)
    hdr += b"\x00" * 44      # dwReserved1[11]
    # DDS_PIXELFORMAT: dwSize, dwFlags, dwFourCC, dwRGBBitCount, R, G, B, A 마스크
    hdr += struct.pack("<8I", 32, DDPF_FLAGS, 0, 32,
                       0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    # dwCaps, dwCaps2, dwCaps3, dwCaps4, dwReserved2
    hdr += struct.pack("<5I", DDSCAPS_TEXTURE, 0, 0, 0, 0)
    assert len(hdr) == HEADER_SIZE
    return hdr


def write_dds(path, rgba):
    """rgba: (h, w, 4) uint8 배열. 행은 위에서 아래로 저장한다."""
    arr = np.asarray(rgba, dtype=np.uint8)
    if arr.ndim != 3 or arr.shape[2] != 4:
        raise ValueError("write_dds expects an (h, w, 4) array")
    h, w = arr.shape[0], arr.shape[1]
    bgra = np.ascontiguousarray(arr[:, :, [2, 1, 0, 3]])
    with open(path, "wb") as f:
        f.write(build_header(w, h))
        f.write(bgra.tobytes())
