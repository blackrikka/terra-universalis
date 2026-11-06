#!/usr/bin/env python3
"""국가별 고유 콘텐츠(중점·국민정신·디시전·이벤트·세력 균형·로컬라이제이션) 생성 틀 (사양서 17).

국가마다 tools/focusgen/content/<tag>.py 에 데이터를 쓰고, 이 모듈의 Country 로 파일을 만든다.
    python -I tools/focusgen/content/kaz.py
    python -I tools/focusgen/merge_focus.py --tag KAZ

만드는 파일 (<tag> = 소문자 태그):
    tools/focusgen/<tag>/_header.txt, p1_all.txt               (merge_focus 가 national_focus 로 합침)
    terra_universalis/common/ideas/tu_<tag>_ideas.txt
    terra_universalis/common/decisions/tu_<tag>_decisions.txt, categories/tu_<tag>_categories.txt
    terra_universalis/events/tu_<tag>_events.txt
    terra_universalis/common/bop/tu_<tag>_bop.txt              (세력 균형을 쓸 때)
    terra_universalis/common/scripted_effects/tu_<tag>_effects.txt (있을 때)
    terra_universalis/common/on_actions/tu_<tag>_on_actions.txt (있을 때)
    terra_universalis/localisation/{korean,english}/tu_<tag>_l_<lang>.yml
    tools/mapgen/country_history/<TAG>.txt                      (시작 상태: 세력 균형, 변수 등)

중점 보상: reward 를 주면 그 줄들 + (theme=True 이면) 이름 테마 보상. reward 가 없으면 테마 보상만.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ruling_party as _ruling_party  # noqa: E402  (사양서 50)
from theme_effects import theme_of, reward_lines, FOCUS_ICON, is_warship  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gauges"))
from countries import PANEL_TABS, status_ui  # noqa: E402  (수치 패널을 놓는 탭, tools/gauges/countries.py)
import focus_drop  # noqa: E402

REPO = HERE.parents[1]
MOD = REPO / "terra_universalis"


def ind(lines, n):
    """여러 줄 문자열/목록을 탭 n개로 들여쓴다."""
    if isinstance(lines, str):
        lines = lines.split("\n")
    out = []
    for block in lines:
        if block == "":          # 빈 효과 (예: 없어진 세력 균형) 는 건너뛴다
            continue
        for l in block.split("\n"):
            out.append("\t" * n + l if l.strip() else "")
    return "\n".join(out)


class Country:
    def __init__(self, tag, name_ko, name_en):
        self.tag = tag
        self.low = tag.lower()
        self.name_ko, self.name_en = name_ko, name_en
        self.focuses = []
        self.ideas = []
        self.categories = []
        self.decisions = {}
        self.events = []
        self.ko, self.en = {}, {}
        self.effects = []
        self.triggers = []
        self.on_actions = []
        self.bop = None
        self.history = []
        self.root = None

    # ---------- 로컬라이제이션
    def loc(self, key, ko, en):
        self.ko[key] = ko
        self.en[key] = en

    # ---------- 중점
    def f(self, sid, ko, en, pre=(), me=(), cost=10, reward=None, theme=True, available=(), bypass=(),
          desc=("", ""), icon=None, filt=None, ai=1, allow_branch=(), econ=False):
        fid = "TU_%s_%s" % (self.tag, sid)
        rw = list(reward or [])
        if theme or reward is None:
            rw += reward_lines(theme_of(en), fid, cost)
        if econ and not (theme_of(en) == "rail" and "TU_build_infrastructure" in str(econ)):
            rw.append(econ if isinstance(econ, str) else "TU_build_civ_factory = yes")
        pre = [[("TU_%s_%s" % (self.tag, x)) if not x.startswith("TU_") else x for x in
                (g if isinstance(g, (list, tuple)) else [g])] for g in pre]
        me = [("TU_%s_%s" % (self.tag, x)) if not x.startswith("TU_") else x for x in me]
        if icon is None:
            icon = FOCUS_ICON.get(theme_of(en), FOCUS_ICON["politics"])
        if filt is None:
            filt = "FOCUS_FILTER_INDUSTRY" if econ else "FOCUS_FILTER_POLITICAL"
        self.focuses.append(dict(id=fid, icon=icon, pre=pre, me=me, cost=cost, reward=rw, available=list(available),
                                 bypass=list(bypass), filt=filt, ai=ai, allow_branch=list(allow_branch)))
        self.loc(fid, ko, en)
        self.loc(fid + "_desc", desc[0], desc[1])
        if self.root is None:
            self.root = fid
        return fid

    # ---------- 국민정신
    def idea(self, sid, ko, en, mods, pic="generic_central_management", desc=("", ""), extra=""):
        iid = "TU_%s_%s" % (self.tag, sid)
        self.ideas.append((iid, pic, mods, extra))
        self.loc(iid, ko, en)
        self.loc(iid + "_desc", desc[0], desc[1])
        return iid

    # ---------- 디시전
    def category(self, sid, ko, en, desc=("", ""), icon="GFX_decision_category_generic_political_actions",
                 visible=()):
        cid = "TU_%s_%s_category" % (self.tag, sid)
        self.categories.append((cid, icon, list(visible)))
        self.decisions[cid] = []
        self.loc(cid, ko, en)
        self.loc(cid + "_desc", desc[0], desc[1])
        return cid

    def d(self, cat, sid, ko, en, effect, cost=25, visible=(), available=(), desc=("", ""),
          icon="GFX_decision_generic_political_discourse", once=True, days_re_enable=None, ai=1,
          days_remove=None, remove_effect=None, target=None, state_target=False, modifier=None, mission=None,
          map_only=False):
        """target = FROM(대상) 조건. state_target=True 면 주 대상 디시전: 조건에 맞는 주마다 하나씩 생기고,
        디시전 탭을 열면 지도에서 그 주 위에 버튼이 뜬다 (효과 안에서 FROM = 그 주).
        map_only=True 면 탭 목록에는 안 나오고 지도 버튼으로만 뜬다.
        modifier = days_remove 동안 걸리는 모디파이어 {키: 값} (예: civilian_factory_use).
        mission = 시간제한 미션 {"days": 일수, "timeout": [효과], "cancel": [조건], "good": False}.
          activation 은 막아 두므로 효과에서 activate_mission / activate_targeted_decision 으로 켠다. cost=None 이면 비용 줄을 쓰지 않는다."""
        did = "TU_%s_%s" % (self.tag, sid)
        self.decisions[cat].append(dict(id=did, icon=icon, effect=list(effect), cost=cost, visible=list(visible),
                                        available=list(available), once=once, days_re_enable=days_re_enable,
                                        ai=ai, days_remove=days_remove, remove_effect=remove_effect,
                                        target=target, state_target=state_target, modifier=modifier, mission=mission,
                                        map_only=map_only))
        self.loc(did, ko, en)
        self.loc(did + "_desc", desc[0], desc[1])
        return did

    # ---------- 이벤트
    def ev(self, n, title, desc, options, picture="GFX_report_event_generic_read_write", news=False,
           trigger=None, mtth=None, immediate=None, fire_once=True):
        """options: [(ko, en, [effects], ai_factor)]"""
        eid = "tu_%s_ev.%d" % (self.low, n)
        self.events.append(dict(id=eid, picture=picture, news=news, options=options, trigger=trigger,
                                mtth=mtth, immediate=immediate, fire_once=fire_once))
        self.loc(eid + ".t", title[0], title[1])
        self.loc(eid + ".d", desc[0], desc[1])
        for i, o in enumerate(options):
            self.loc("%s.%s" % (eid, "abcdefgh"[i]), o[0], o[1])
        return eid

    # ---------- 세력 균형
    def set_bop(self, left, right, initial, left_ranges, right_ranges):
        """left/right = (sid, ko, en, icon). ranges = [(min, max, {modifier})] 크기 순."""
        """세력 균형(힘의 균형)은 모드 전체에서 없앴다 (사양서 34). 호출해도 아무것도 만들지 않는다."""
        return "TU_%s_bop" % self.tag

    # ---------- 쓰기
    def _focus_text(self, f):
        pre = "".join("\t\tprerequisite = { %s }\n" % " ".join("focus = %s" % x for x in g) for g in f["pre"])
        me = "\t\tmutually_exclusive = { %s }\n" % " ".join("focus = %s" % x for x in f["me"]) if f["me"] else ""
        out = "\tfocus = {\n\t\tid = %s\n\t\ticon = %s\n%s%s\t\tx = 0\n\t\ty = 0\n\t\tcost = %d\n\n" % (
            f["id"], f["icon"], pre, me, f["cost"])
        out += "\t\tsearch_filters = { %s }\n" % f["filt"]
        for key in ("allow_branch", "available", "bypass"):
            if f[key]:
                out += "\n\t\t%s = {\n%s\n\t\t}\n" % (key, ind(f[key], 3))
        out += "\n\t\tai_will_do = {\n\t\t\tbase = %s\n\t\t}\n" % f["ai"]
        out += "\n\t\tcompletion_reward = {\n%s\n\t\t}\n\t}\n\n" % ind(f["reward"], 3)
        return out

    def _drop_warships(self):
        """군함·조선소·해군기지 중점을 지우고 앞뒤를 잇는다 (사양서 18). 반환: {지운 id: 대신할 조상}."""
        removed = {f["id"] for f in self.focuses if is_warship(self.en.get(f["id"], ""), self.tag)}
        if not removed:
            return {}
        nodes = {f["id"]: {"pre": f["pre"], "me": f["me"]} for f in self.focuses}
        new, anc = focus_drop.drop(nodes, removed)
        self.focuses = [f for f in self.focuses if f["id"] not in removed]
        for f in self.focuses:
            f["pre"], f["me"] = new[f["id"]]["pre"], new[f["id"]]["me"]
            for key in ("available", "bypass", "allow_branch", "reward"):
                f[key] = [focus_drop.fix_refs(x, anc) for x in f[key]]
        for fid in removed:
            for k in (fid, fid + "_desc"):
                self.ko.pop(k, None)
                self.en.pop(k, None)
        return anc

    def write(self):
        t, low = self.tag, self.low
        anc = self._drop_warships()
        folder = HERE / low
        folder.mkdir(exist_ok=True)
        (folder / "_header.txt").write_text("""focus_tree = {
	id = TU_%s_focus
	continuous_focus_position = { x = 50 y = 1500 }

	country = {
		factor = 0
		modifier = {
			add = 10
			original_tag = %s
		}
	}

	reset_on_civilwar = no

	initial_show_position = {
		focus = %s
	}
""" % (t, t, self.root), encoding="utf-8")
        body = "\t#### %s (generated by tools/focusgen/content/%s.py) ####\n\n" % (t, low)
        body += "".join(self._focus_text(f) for f in self.focuses)
        (folder / "p1_all.txt").write_text(body.rstrip("\n") + "\n", encoding="utf-8")
        for old in folder.glob("*.txt"):
            if old.name not in ("_header.txt", "p1_all.txt") and not old.name.startswith("p9_"):   # p9_: hidden_routes.py
                old.unlink()
        self.loc("TU_%s_focus" % t, "%s 중점" % self.name_ko, "%s Focus" % self.name_en)

        # ideas
        blocks = []
        for iid, pic, mods, extra in self.ideas:
            m = ind(["%s = %s" % kv for kv in mods.items()], 4)
            blocks.append("\t\t%s = {\n\t\t\tpicture = %s\n\n\t\t\tallowed = {\n\t\t\t\toriginal_tag = %s\n\t\t\t}\n%s"
                          "\n\t\t\tmodifier = {\n%s\n\t\t\t}\n\t\t}\n" % (iid, pic, t, extra, m))
        (MOD / ("common/ideas/tu_%s_ideas.txt" % low)).write_text(
            "ideas = {\n\n\tcountry = {\n\n" + "\n".join(blocks) + "\t}\n}\n", encoding="utf-8")
        old = MOD / ("common/ideas/tu_%s_concept_ideas.txt" % low)
        if old.exists():
            old.unlink()

        # decisions
        if self.categories:
            cats = []
            for cid, icon, vis in self.categories:
                v = "\n\tvisible = {\n%s\n\t}\n" % ind(vis, 2) if vis else ""
                g = ""
                if cid in PANEL_TABS:
                    # 수치 패널이 있는 탭은 항상 보인다 (사양서 39). 탭의 조건은 안의 디시전이 물려받는다
                    g = "\tscripted_gui = %s\n\tvisible_when_empty = yes\n" % status_ui(cid)
                    v = ""
                    for d in self.decisions[cid]:
                        d["visible"] = list(vis) + d["visible"]
                cats.append("%s = {\n\ticon = %s\n%s\n\tallowed = {\n\t\toriginal_tag = %s\n\t}\n%s\n\tpriority = 100\n}\n"
                            % (cid, icon, g, t, v))
            (MOD / ("common/decisions/categories/tu_%s_categories.txt" % low)).write_text("\n".join(cats), encoding="utf-8")
            out = []
            for cid, _, _ in self.categories:
                out.append("%s = {\n" % cid)
                for d in self.decisions[cid]:
                    s = "\t%s = {\n\t\ticon = %s\n\n\t\tallowed = {\n\t\t\toriginal_tag = %s\n\t\t}\n" % (d["id"], d["icon"], t)
                    if d["state_target"]:
                        s += "\n\t\tstate_target = yes\n\t\ton_map_mode = %s\n" % ("map_only" if d["map_only"] else "map_and_decisions_view")
                    if d["target"]:
                        s += "\n\t\ttarget_trigger = {\n\t\t\tFROM = {\n%s\n\t\t\t}\n\t\t}\n" % ind(d["target"], 4)
                    m = d["mission"]
                    if m:
                        s += "\n\t\tactivation = {\n\t\t\talways = no\n\t\t}\n"
                    for key in ("visible", "available"):
                        if d[key]:
                            s += "\n\t\t%s = {\n%s\n\t\t}\n" % (key, ind(d[key], 3))
                        elif key == "available" and m:
                            s += "\n\t\tavailable = {\n\t\t\talways = no\n\t\t}\n"
                    s += "\n"
                    if d["cost"] is not None:
                        s += "\t\tcost = %d\n" % d["cost"]
                    if m:
                        s += "\t\tdays_mission_timeout = %d\n\t\tis_good = %s\n" % (m["days"], "yes" if m.get("good") else "no")
                    s += "\t\tfire_only_once = %s\n" % ("yes" if d["once"] else "no") if d["once"] or m else ""
                    if d["days_re_enable"]:
                        s += "\t\tdays_re_enable = %d\n" % d["days_re_enable"]
                    if d["days_remove"]:
                        s += "\t\tdays_remove = %d\n" % d["days_remove"]
                    if d["modifier"]:
                        s += "\n\t\tmodifier = {\n%s\n\t\t}\n" % ind(["%s = %s" % kv for kv in d["modifier"].items()], 3)
                    if m and m.get("cancel"):
                        s += "\n\t\tcancel_trigger = {\n%s\n\t\t}\n" % ind(m["cancel"], 3)
                    if m and m.get("timeout"):
                        s += "\n\t\ttimeout_effect = {\n%s\n\t\t}\n" % ind(m["timeout"], 3)
                    if d["effect"]:
                        s += "\n\t\tcomplete_effect = {\n%s\n\t\t}\n" % ind(d["effect"], 3)
                    if d["remove_effect"]:
                        s += "\n\t\tremove_effect = {\n%s\n\t\t}\n" % ind(d["remove_effect"], 3)
                    s += "\n\t\tai_will_do = {\n\t\t\tbase = %s\n\t\t}\n\t}\n\n" % d["ai"]
                    out.append(s)
                out.append("}\n\n")
            (MOD / ("common/decisions/tu_%s_decisions.txt" % low)).write_text("".join(out).rstrip("\n") + "\n", encoding="utf-8")
            _ruling_party.fix_file(MOD / ("common/decisions/tu_%s_decisions.txt" % low))

        # events
        if self.events:
            out = ["add_namespace = tu_%s_ev\n\n" % low]
            for e in self.events:
                kind = "news_event" if e["news"] else "country_event"
                s = "%s = {\n\tid = %s\n\ttitle = %s.t\n\tdesc = %s.d\n\tpicture = %s\n" % (kind, e["id"], e["id"], e["id"], e["picture"])
                if e["news"]:
                    s += "\tmajor = yes\n"
                if e["trigger"]:
                    s += "\n\ttrigger = {\n%s\n\t}\n" % ind(e["trigger"], 2)
                    if e["fire_once"]:
                        s += "\tfire_only_once = yes\n"
                    s += "\n\tmean_time_to_happen = {\n\t\tdays = %d\n\t}\n" % (e["mtth"] or 60)
                else:
                    s += "\tis_triggered_only = yes\n"
                if e["immediate"]:
                    s += "\n\timmediate = {\n%s\n\t}\n" % ind(e["immediate"], 2)
                for i, (_, _, eff, ai) in enumerate(e["options"]):
                    s += "\n\toption = {\n\t\tname = %s.%s\n\t\tai_chance = {\n\t\t\tfactor = %d\n\t\t}\n" % (e["id"], "abcdefgh"[i], ai)
                    if eff:
                        s += ind(eff, 2) + "\n"
                    s += "\t}\n"
                s += "}\n\n"
                out.append(s)
            (MOD / ("events/tu_%s_events.txt" % low)).write_text("".join(out).rstrip("\n") + "\n", encoding="utf-8")
            _ruling_party.fix_file(MOD / ("events/tu_%s_events.txt" % low))

        # bop
        if self.bop:
            b = self.bop
            bid = "TU_%s_bop" % t

            def side(sd, ranges, sign):
                sid, ko, en, icon = sd
                self.loc("TU_%s_bop_%s" % (t, sid), ko, en)
                s = "\tside = {\n\t\tid = TU_%s_bop_%s\n\t\ticon = %s\n" % (t, sid, icon)
                for k, rng in enumerate(ranges):
                    lo, hi, mods = rng[:3]
                    flag = rng[3] if len(rng) > 3 else None     # 이 단계가 켜져 있는 동안 세울 국가 깃발
                    rid = "TU_%s_bop_%s_r%d" % (t, sid, k + 1)
                    mn, mx = (-hi, -lo) if sign < 0 else (lo, hi)
                    self.loc(rid, "%s %d단계" % (ko, k + 1), "%s %d" % (en, k + 1))
                    on = "\t\t\t\tset_country_flag = %s\n" % flag if flag else ""
                    off = "\t\t\t\tclr_country_flag = %s\n" % flag if flag else ""
                    s += "\n\t\trange = {\n\t\t\tid = %s\n\t\t\tmin = %s\n\t\t\tmax = %s\n\t\t\tmodifier = {\n%s\n\t\t\t}\n" \
                         "\t\t\ton_activate = {\n%s\t\t\t}\n\t\t\ton_deactivate = {\n%s\t\t\t}\n\t\t}\n" % (
                             rid, mn, mx, ind(["%s = %s" % kv for kv in mods.items()], 4), on, off)
                return s + "\t}\n"
            txt = "%s = {\n\tinitial_value = %s\n\tleft_side = TU_%s_bop_%s\n\tright_side = TU_%s_bop_%s\n\n" % (
                bid, b["initial"], t, b["left"][0], t, b["right"][0])
            txt += side(b["left"], b["lr"], -1) + "\n" + side(b["right"], b["rr"], 1) + "}\n"
            (MOD / ("common/bop/tu_%s_bop.txt" % low)).write_text(txt, encoding="utf-8")

        if self.effects:
            (MOD / ("common/scripted_effects/tu_%s_effects.txt" % low)).write_text("\n\n".join(self.effects) + "\n", encoding="utf-8")
            import templates as _templates  # 기본 편제 통일 (사양서 52)
            _templates.apply_file(MOD / ("common/scripted_effects/tu_%s_effects.txt" % low))
        if self.triggers:
            (MOD / ("common/scripted_triggers/tu_%s_triggers.txt" % low)).write_text("\n\n".join(self.triggers) + "\n", encoding="utf-8")
        if self.on_actions:
            (MOD / ("common/on_actions/tu_%s_on_actions.txt" % low)).write_text(
                "on_actions = {\n%s\n}\n" % ind(self.on_actions, 1), encoding="utf-8")
        if self.history:
            (REPO / ("tools/mapgen/country_history/%s.txt" % t)).write_text(
                "# %s: appended to history/countries by build_countries.py (generated by tools/focusgen/content/%s.py)\n"
                % (t, low) + "\n".join(self.history) + "\n", encoding="utf-8")

        # 지운 중점을 가리키던 조건을 남는 조상으로 바꾼다
        if anc:
            for rel in ("common/decisions/tu_%s_decisions.txt", "events/tu_%s_events.txt",
                        "common/scripted_effects/tu_%s_effects.txt", "common/on_actions/tu_%s_on_actions.txt",
                        "common/ideas/tu_%s_ideas.txt"):
                fp = MOD / (rel % low)
                if fp.exists():
                    fp.write_text(focus_drop.fix_refs(fp.read_text(encoding="utf-8"), anc), encoding="utf-8")
            print("  dropped warship focuses: %d" % len(anc))

        # localisation
        for lang, items in (("korean", self.ko), ("english", self.en)):
            lines = ["l_%s:" % lang] + [' %s:0 "%s"' % (k, v.replace('"', '\\"').replace("\n", "\\n")) for k, v in items.items()]
            (MOD / "localisation" / lang / ("tu_%s_l_%s.yml" % (low, lang))).write_bytes(
                ("\n".join(lines) + "\n").encode("utf-8-sig"))
            old = MOD / "localisation" / lang / ("tu_%s_concept_l_%s.yml" % (low, lang))
            if old.exists():
                old.unlink()
        print("CONTENT %s focuses=%d ideas=%d decisions=%d events=%d" % (
            t, len(self.focuses), len(self.ideas), sum(len(v) for v in self.decisions.values()), len(self.events)))
