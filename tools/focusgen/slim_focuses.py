#!/usr/bin/env python3
"""큰 중점 트리 줄이기: 사슬 중간의 일반 중점을 부모 중점에 합친다 (사양서 35).

사용법 (python -I):
    python -I tools/focusgen/slim_focuses.py --tag URS --target 220 [--dry]
    그다음 python -I tools/focusgen/merge_focus.py --tag URS

합칠 수 있는 중점 (일반 중점)
- 숨은 루트(p9_) 조각이 아니고, 뿌리가 아니다.
- 보상이 국민정신·깃발·이벤트·캐릭터·국호·변수·전쟁·영토·디시전 같은 특별 효과 없이,
  정치력·안정도·연구 보너스·교리·건설(TU_build_*)·인력 같은 일반 효과뿐이다.
- available / bypass / allow_branch / mutually_exclusive / select_effect 가 없다 (노선 분기가 아님).
- 모드 다른 파일(디시전·이벤트·GUI·history)과 캐릭터 훅이 id 를 쓰지 않고, 다른 중점이 조건으로 쓰지 않는다.
- prerequisite 가 정확히 하나(부모 P 하나)이고, 같은 조각 파일 안에 있는 P 도 남는다.
합치기
- X 의 보상 줄을 P 의 보상 끝에 붙인다 (연구 보너스·교리의 name = X 는 name = P 로).
- P 의 비용 += X 비용의 절반 (반올림, 최대 20). 부모 하나는 자식 하나만 받는다 (한 라운드).
- X 의 자식은 P 를 prerequisite 로 갖는다 (focus_drop.drop). X 의 로컬라이제이션 줄을 지운다.
목표 수(--target)에 닿을 때까지 라운드를 반복한다 (라운드마다 다시 분류).
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "chargen"))
import focus_drop  # noqa: E402

REPO = HERE.parents[1]
MOD = REPO / "terra_universalis"
BLOCK_RE = re.compile(r"(?=\n\tfocus = \{\n)")
SPECIAL = re.compile(
    r"\b(add_ideas|swap_ideas|remove_ideas|add_timed_idea|set_country_flag|clr_country_flag|country_event|news_event|"
    r"set_cosmetic_tag|promote_character|recruit_character|add_research_slot|set_politics|create_wargoal|annex_country|"
    r"add_state_core|transfer_state|set_variable|add_to_variable|subtract_from_variable|activate_decision|unlock_decision|"
    r"load_oob|create_faction|puppet|set_global_flag|add_state_claim|declare_war_on|activate_mission|set_party_name|"
    r"retire_character|kill_country_leader|set_capital|release|add_opinion_modifier|give_military_access|diplomatic_relation|"
    r"start_civil_war|set_rule|create_country_leader|add_country_leader_trait|TU_(?!build_)\w+ = yes|change_tag|inherit|"
    r"hidden_effect|custom_effect_tooltip|effect_tooltip|add_relation_modifier|add_named_threat|set_autonomy|"
    r"add_equipment_to_stockpile|create_unit|division_template|set_technology|add_ace|add_offsite|every_|random_|if = )")
STRUCT = re.compile(r"\n\t\t(available|bypass|allow_branch|mutually_exclusive|select_effect|will_lead_to_war_with|"
                    r"cancel_if_invalid|continue_if_invalid)\s*=")
MAX_COST = 20


def reward_of(b):
    m = re.search(r"\n\t\tcompletion_reward = \{\n(.*?)\n\t\t\}\n", b, re.S)
    return m


def load(tag):
    folder = HERE / tag.lower()
    files = {f: f.read_text(encoding="utf-8") for f in sorted(folder.glob("*.txt")) if f.name != "_header.txt"}
    blocks = {}
    for f, text in files.items():
        for b in BLOCK_RE.split(text)[1:]:
            fid = re.search(r"\n\t\tid = (\S+)", b).group(1)
            blocks[fid] = (f, b)
    return files, blocks


def outside_refs(tag):
    txt = []
    own = "tu_%s.txt" % tag.lower()
    for p in list((MOD / "common").rglob("*.txt")) + list((MOD / "events").rglob("*.txt")) + \
            list((MOD / "interface").rglob("*.gui")) + list((MOD / "history").rglob("*.txt")):
        if p.name == own and p.parent.name == "national_focus":
            continue
        txt.append(p.read_text(encoding="utf-8-sig", errors="replace"))
    return "\n".join(txt)


def candidates(tag, blocks, big, hook_sids):
    pre_of, strip = {}, {}
    for fid, (f, b) in blocks.items():
        pre_of[fid] = [re.findall(r"focus = (\S+)", g) for g in re.findall(r"\n\t\tprerequisite = \{([^}\n]*)\}", b)]
        strip[fid] = re.sub(r"\n\t\t(prerequisite|mutually_exclusive|id|relative_position_id) = [^\n]*", "", b)
    joined = "\n".join(strip.values())
    pfx = "TU_%s_" % tag
    out = []
    for fid, (f, b) in blocks.items():
        if f.name.startswith("p9") or len(pre_of[fid]) != 1 or len(pre_of[fid][0]) != 1:
            continue
        parent = pre_of[fid][0][0]
        if parent not in blocks or blocks[parent][0] != f:
            continue
        m = reward_of(b)
        if not m or SPECIAL.search(m.group(1)) or STRUCT.search(b):
            continue
        sid = fid[len(pfx):] if fid.startswith(pfx) else fid
        if sid in hook_sids or re.search(r"\b%s\b" % re.escape(fid), big):
            continue
        if len(re.findall(r"\b%s\b" % re.escape(fid), joined)) > len(re.findall(r"\b%s\b" % re.escape(fid), strip[fid])):
            continue
        if not reward_of(blocks[parent][1]):
            continue
        out.append((fid, parent))
    return out, pre_of


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--target", type=int, required=True)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    tag = a.tag.upper()
    import data
    hook_sids = set(data.COUNTRIES.get(tag, {}).get("hooks", {}).keys())
    big = outside_refs(tag)
    files, blocks = load(tag)
    start = len(blocks)
    removed_all = set()
    rnd = 0
    while len(blocks) > a.target:
        rnd += 1
        cands, pre_of = candidates(tag, blocks, big, hook_sids)
        used_parent, take = set(), []
        need = len(blocks) - a.target
        for fid, parent in sorted(cands, key=lambda t: (str(blocks[t[0]][0].name), t[0])):
            if len(take) >= need:
                break
            if parent in used_parent or parent in {x for x, _ in take} or fid in used_parent:
                continue
            used_parent.add(parent)
            take.append((fid, parent))
        if not take:
            break
        removed = {fid for fid, _ in take}
        # 보상·비용을 부모에 합친다
        for fid, parent in take:
            f, b = blocks[fid]
            pf, pb = blocks[parent]
            rw = reward_of(b).group(1)
            rw = re.sub(r"\bname = %s\b" % re.escape(fid), "name = %s" % parent, rw)
            pm = reward_of(pb)
            pb = pb[:pm.end(1)] + "\n" + rw + pb[pm.end(1):]
            xc = int(float(re.search(r"\n\t\tcost = ([\d.]+)", b).group(1)))
            pc = int(float(re.search(r"\n\t\tcost = ([\d.]+)", pb).group(1)))
            pb = re.sub(r"(\n\t\tcost = )[\d.]+", lambda m: m.group(1) + str(min(MAX_COST, pc + (xc + 1) // 2)), pb, count=1)
            blocks[parent] = (pf, pb)
        nodes = {}
        for fid, (f, b) in blocks.items():
            me = re.findall(r"focus = (\S+)", " ".join(re.findall(r"\n\t\tmutually_exclusive = \{([^}\n]*)\}", b)))
            nodes[fid] = {"pre": pre_of[fid], "me": me}
        new, anc = focus_drop.drop(nodes, removed)
        nb = {}
        for fid, (f, b) in blocks.items():
            if fid in removed:
                continue
            if any(p in removed for g in pre_of[fid] for p in g):
                b = re.sub(r"\n\t\tprerequisite = \{[^}\n]*\}", "", b)
                lines = "".join("\n\t\tprerequisite = { %s }" % " ".join("focus = %s" % x for x in g) for g in new[fid]["pre"])
                b = re.sub(r"(\n\t\tid = \S+)", lambda m: m.group(1) + lines, b, count=1)
                # relative_position_id 가 지운 중점이면 부모로
            for x in removed:
                b = re.sub(r"(relative_position_id = )%s\b" % re.escape(x), lambda m: m.group(1) + anc[x], b) if anc.get(x) else b
            nb[fid] = (f, b)
        blocks = nb
        removed_all |= removed
        print("라운드 %d: 합침 %d → %d개" % (rnd, len(removed), len(blocks)))
    print("SLIM %s: %d → %d (합침 %d)" % (tag, start, len(blocks), len(removed_all)))
    if a.dry or not removed_all:
        return 0

    for f, text in files.items():
        head = BLOCK_RE.split(text)[0]
        # 원래 순서를 지킨다
        order = [re.search(r"\n\t\tid = (\S+)", b).group(1) for b in BLOCK_RE.split(text)[1:]]
        body = "".join(blocks[o][1] for o in order if o in blocks)
        f.write_text(head + body, encoding="utf-8")
    for p in (MOD / "localisation").rglob("*.yml"):
        raw = p.read_bytes()
        s = raw.decode("utf-8-sig")
        keep = [l for l in s.split("\n")
                if not ((m := re.match(r"\s(\S+?)(?:_desc)?:", l)) and m.group(1) in removed_all)]
        if len(keep) != len(s.split("\n")):
            p.write_bytes((("﻿" if raw.startswith(b"\xef\xbb\xbf") else "") + "\n".join(keep)).encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
