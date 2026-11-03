#!/usr/bin/env python3
"""국가 콘텐츠 구현 시안 렌더러 (게임 없이 확인용).

사용법:
    python3 tools/focusgen/render_preview.py --tag KAZ --out <폴더>        # HTML + PNG (Python Playwright 필요; 없으면 --no-png 후 브라우저로 열기)
    python3 tools/focusgen/render_preview.py --all --out <폴더>

그리는 것:
  - 중점 트리: national_focus/tu_<tag>.txt 의 x/y 그대로 (선행 = 실선, 양자택일 = 붉은 점선),
    정치 중점은 파랑, 산업 중점은 주황, 국민정신을 주는 중점은 굵은 테두리.
  - 장치 설명: tools/focusgen/content/<tag>.py 머리말의 "장치" 부분.
  - 디시전 분류와 디시전 이름, 이벤트 제목 (한국어 로컬라이제이션).
"""

import argparse
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MOD = REPO / "terra_universalis"


def load_loc():
    loc = {}
    for f in (MOD / "localisation" / "korean").rglob("*.yml"):
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r'\s(\S+?):\d*\s+"(.*)"', line)
            if m:
                loc[m.group(1)] = m.group(2).replace('\\"', '"')
    return loc


def strip_colour(s):
    return re.sub(r"§.", "", s)


def parse_focuses(tag):
    text = (MOD / "common" / "national_focus" / ("tu_%s.txt" % tag.lower())).read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"\n\tfocus = \{\n(.*?)\n\t\}\n", text, re.S):
        b = m.group(1)
        fid = re.search(r"\bid = (\S+)", b).group(1)
        x = int(re.search(r"\n\t\tx = (-?\d+)", b).group(1))
        y = int(re.search(r"\n\t\ty = (-?\d+)", b).group(1))
        pre = [re.findall(r"focus = (\S+)", g) for g in re.findall(r"prerequisite = \{([^}]*)\}", b)]
        me = re.findall(r"focus = (\S+)", " ".join(re.findall(r"mutually_exclusive = \{([^}]*)\}", b)))
        out.append(dict(id=fid, x=x, y=y, pre=pre, me=me, industry="FOCUS_FILTER_INDUSTRY" in b,
                        idea=bool(re.search(r"add_ideas|swap_ideas", b)), hidden="allow_branch" in b))
    return out


def parse_decisions(tag, loc):
    cats = []
    p = MOD / "common" / "decisions" / ("tu_%s_decisions.txt" % tag.lower())
    if not p.exists():
        return cats
    text = p.read_text(encoding="utf-8")
    for m in re.finditer(r"^(TU_\w+_category) = \{\n(.*?)^\}", text, re.S | re.M):
        names = re.findall(r"^\t(TU_\w+) = \{", m.group(2), re.M)
        cats.append((loc.get(m.group(1), m.group(1)), [strip_colour(loc.get(n, n)) for n in names]))
    return cats


def parse_events(tag, loc):
    p = MOD / "events" / ("tu_%s_events.txt" % tag.lower())
    if not p.exists():
        return []
    ids = re.findall(r"\n\tid = (tu_\w+\.\d+)", "\n" + p.read_text(encoding="utf-8"))
    return [(i, loc.get(i + ".t", i)) for i in ids]


def mechanics_text(tag):
    p = HERE / "content" / ("%s.py" % tag.lower())
    if not p.exists():
        return ""
    doc = re.search(r'"""(.*?)"""', p.read_text(encoding="utf-8"), re.S).group(1)
    m = re.search(r"장치\n(.*?)\n\n실행", doc, re.S)
    return (m.group(1) if m else doc).strip()


def build_html(tag, loc):
    fs = parse_focuses(tag)
    by = {f["id"]: f for f in fs}
    minx = min(f["x"] for f in fs)
    maxx = max(f["x"] for f in fs)
    maxy = max(f["y"] for f in fs)
    UX, UY, BW, BH, PAD = 92, 96, 86, 52, 30
    W = (maxx - minx + 1) * UX + PAD * 2
    H = (maxy + 1) * UY + PAD * 2

    def cx(f):
        return PAD + (f["x"] - minx) * UX + UX / 2

    def cy(f):
        return PAD + f["y"] * UY + BH / 2

    lines = []
    for f in fs:
        for g in f["pre"]:
            for p in g:
                if p in by:
                    q = by[p]
                    dash = ' stroke-dasharray="5,4"' if len(g) > 1 else ""
                    lines.append('<path d="M%.0f %.0f V%.0f H%.0f V%.0f" stroke="#c9b98f" stroke-width="2" fill="none"%s/>' % (
                        cx(q), cy(q) + BH / 2, cy(q) + BH / 2 + 14, cx(f), cy(f) - BH / 2, dash))
        for o in f["me"]:
            if o in by and f["id"] < o:
                q = by[o]
                lines.append('<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="#d04a3a" stroke-width="2" stroke-dasharray="4,3"/>' % (
                    cx(f), cy(f), cx(q), cy(q)))
    boxes = []
    for f in fs:
        name = html.escape(strip_colour(loc.get(f["id"], f["id"])))
        cls = "ind" if f["industry"] else "pol"
        if f["idea"]:
            cls += " idea"
        if f["hidden"]:
            cls += " hid"
        boxes.append('<div class="f %s" style="left:%dpx;top:%dpx">%s</div>' % (
            cls, cx(f) - BW / 2, cy(f) - BH / 2, name))

    dec = parse_decisions(tag, loc)
    evs = parse_events(tag, loc)
    mech = html.escape(mechanics_text(tag))
    name = loc.get(tag, tag)
    dec_html = "".join('<div class="cat"><b>%s</b><ul>%s</ul></div>' % (html.escape(c), "".join("<li>%s</li>" % html.escape(n) for n in ns))
                       for c, ns in dec)
    ev_html = "<ul>%s</ul>" % "".join("<li><span>%s</span> %s</li>" % (html.escape(i.split(".")[-1]), html.escape(t)) for i, t in evs)
    n_dec = sum(len(ns) for _, ns in dec)
    return """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#1b1a17;color:#e8e2d0;font-family:'WenQuanYi Zen Hei',sans-serif}
header{padding:18px 28px;border-bottom:2px solid #5b5240;background:#24221d}
h1{margin:0 0 6px;font-size:30px}.stats{color:#c9b98f;font-size:16px}
.top{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:18px;padding:18px 28px}
.panel{background:#26241f;border:1px solid #4a4335;border-radius:6px;padding:12px 16px;font-size:13px}
.panel h2{font-size:16px;margin:0 0 8px;color:#e6c66a}
pre{white-space:pre-wrap;font-family:inherit;margin:0;line-height:1.5}
ul{margin:4px 0 8px 18px;padding:0}li{margin:1px 0}.cat b{color:#9fc5e8}
li span{display:inline-block;min-width:22px;color:#888}
.tree{position:relative;margin:10px 28px 28px;background:#211f1b;border:1px solid #4a4335;border-radius:6px}
.f{position:absolute;width:86px;height:52px;box-sizing:border-box;border-radius:5px;font-size:11px;line-height:13px;
display:flex;align-items:center;justify-content:center;text-align:center;padding:2px 3px;overflow:hidden}
.pol{background:#2b3f57;border:1px solid #6d8fb5}.ind{background:#5a4220;border:1px solid #c79a4d}
.idea{border-width:3px;border-color:#e6c66a}.hid{opacity:.75;border-style:dashed}
.legend{font-size:12px;color:#aaa;padding:0 28px}.legend i{display:inline-block;width:14px;height:10px;margin:0 4px 0 12px;vertical-align:middle}
</style></head><body>
<header><h1>%s (%s) 구현 시안</h1><div class="stats">중점 %d · 디시전 %d · 이벤트 %d</div></header>
<div class="top"><div class="panel"><h2>고유 장치</h2><pre>%s</pre></div>
<div class="panel"><h2>디시전</h2>%s</div><div class="panel"><h2>이벤트</h2>%s</div></div>
<div class="legend"><i style="background:#2b3f57"></i>정치·군사 중점<i style="background:#5a4220"></i>경제 중점(건설)
<i style="border:3px solid #e6c66a"></i>국민정신 획득<i style="background:#d04a3a;height:3px"></i>양자택일 (붉은 점선)
<i style="background:#c9b98f;height:3px"></i>선행 (점선 = 둘 중 하나)</div>
<div class="tree" style="width:%dpx;height:%dpx"><svg width="%d" height="%d" style="position:absolute;left:0;top:0">%s</svg>%s</div>
</body></html>""" % (html.escape(name), tag, len(fs), n_dec, len(evs), mech, dec_html, ev_html, W, H, W, H, "".join(lines), "".join(boxes))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-png", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tags = sorted(p.stem.upper() for p in (HERE / "content").glob("*.py")) if a.all else [a.tag.upper()]
    loc = load_loc()
    pages = []
    for t in tags:
        p = out / ("preview_%s.html" % t)
        p.write_text(build_html(t, loc), encoding="utf-8")
        pages.append((t, p))
        print("HTML", p)
    if a.no_png:
        return 0
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1600, "height": 900})
        for t, p in pages:
            pg.goto(p.as_uri())
            pg.wait_for_timeout(300)
            png = out / ("preview_%s.png" % t)
            pg.screenshot(path=str(png), full_page=True)
            print("PNG", png)
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
