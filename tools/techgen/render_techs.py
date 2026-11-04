#!/usr/bin/env python3
"""테라 연구 트리 시안 (HTML). 사용법: python3 tools/techgen/render_techs.py <out.html>"""

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_techs as B  # noqa: E402

NAMES = {B.INF: "보병 장구", B.SUP: "지원", B.ART: "포병·공성", B.ARM: "장갑 차량", B.AIR: "드론·비행선", B.IND: "산업",
         B.ELE: "전기·아츠 공학", B.ORI: "오리지늄 공학 (옛 해군)", B.MED: "광석병 의학 (옛 해군 지원)"}


def effect(t):
    out = []
    if t["eq"]:
        out.append("장비 " + ", ".join(t["eq"]))
    if t["sub"]:
        out.append("부대 " + ", ".join(t["sub"]))
    if t["bld"]:
        out.append("건물 %s %d" % t["bld"])
    out += ["%s %+g" % kv for kv in t["mods"].items()]
    for u, st in t["unit"].items():
        out.append("%s: %s" % (u, ", ".join("%s %+g" % kv for kv in st.items())))
    return "; ".join(out)


def main(out):
    UX, UY, BW, BH = 120, 52, 112, 46
    parts = []
    for folder, name in NAMES.items():
        ts = [t for t in B.TECHS if t["folder"] == folder]
        by = {t["id"]: t for t in ts}
        minx = min(t["x"] for t in ts)
        W = (max(t["x"] for t in ts) - minx + 1) * UX + 40
        H = 30 + 12 * UY // 2 + BH + 20

        def pos(t):
            return 20 + (t["x"] - minx) * UX, 30 + B.ERA[t["era"]][1] * UY // 2 * 1

        lines, boxes = [], []
        for t in ts:
            x, y = pos(t)
            for n in t["leads"]:
                if n in by:
                    x2, y2 = pos(by[n])
                    lines.append('<path d="M%d %d V%d H%d V%d" stroke="#c9b98f" fill="none" stroke-width="2"/>' % (
                        x + BW // 2, y + BH, y + BH + 6, x2 + BW // 2, y2))
            cls = "new" if not t["vanilla"] else ""
            if t["ab"]:
                cls += " lat"
            boxes.append('<div class="t %s" style="left:%dpx;top:%dpx" title="%s"><b>%s</b><i>%d · %s</i></div>' % (
                cls, x, y, html.escape(effect(t)), html.escape(t["ko"]), B.ERA[t["era"]][0], html.escape(effect(t))[:60]))
        eras = "".join('<div class="era" style="top:%dpx">%d</div>' % (30 + r * UY // 2, y) for e, (y, r) in B.ERA.items())
        parts.append('<h2>%s <small>%d개</small></h2><div class="f" style="width:%dpx;height:%dpx">%s<svg width="%d" height="%d">%s</svg>%s</div>'
                     % (name, len(ts), W + 50, H, eras, W + 50, H, "".join(lines), "".join(boxes)))
    Path(out).write_text("""<!doctype html><html><head><meta charset="utf-8"><style>
body{background:#1b1a17;color:#e8e2d0;font-family:'WenQuanYi Zen Hei',sans-serif;margin:20px}
h1{margin:0 0 4px}h2{margin:22px 0 6px;color:#e6c66a;font-size:20px}small{color:#999;font-size:13px}
.f{position:relative;background:#211f1b;border:1px solid #4a4335;border-radius:6px;display:inline-block}
svg{position:absolute;left:50px;top:0}.t{position:absolute;margin-left:50px;width:112px;height:46px;box-sizing:border-box;
background:#2b3f57;border:1px solid #6d8fb5;border-radius:4px;font-size:11px;line-height:12px;padding:2px 3px;overflow:hidden}
.t i{display:block;color:#aab;font-style:normal;font-size:9px}.new{background:#4a3a1c;border-color:#e6c66a}
.lat{background:#5a2a2a;border-color:#ff9a7a}.era{position:absolute;left:6px;color:#777;font-size:12px}
.legend span{display:inline-block;padding:2px 8px;margin-right:8px;border-radius:3px;font-size:12px}
</style></head><body><h1>테라 연구 트리 시안</h1>
<div class="legend"><span style="background:#2b3f57">기존 id 재활용(이름·효과 변경)</span><span style="background:#4a3a1c">테라 고유</span>
<span style="background:#5a2a2a">라테라노 전용 (총기)</span> 연도 = 테라력, 게임 시작 1097</div>%s</body></html>""" % "".join(parts),
                         encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
