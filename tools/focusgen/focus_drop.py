#!/usr/bin/env python3
"""중점 지우기 + 앞뒤 다시 잇기 (해군 기능 삭제, 사양서 18).

drop(nodes, removed)
    nodes   {id: {"pre": [[id, ...], ...], "me": [id, ...]}}  (pre = prerequisite 블록 목록, 블록 안은 OR)
    removed 지울 id 집합
    남는 중점의 prerequisite 에서 지운 중점을 뺀다. 블록이 비면 지운 중점의 prerequisite 를 대신 넣는다 (사슬이 이어지게).
    mutually_exclusive 에서도 뺀다. 반환: (새 nodes, 대신할 조상 {지운 id: 남는 조상 id 또는 None})
fix_refs(text, anc)
    has_completed_focus = <지운 id> 를 남는 조상으로 바꾼다 (조상이 없으면 always = yes).
"""

import re


def drop(nodes, removed):
    removed = set(removed)
    memo = {}

    def eff(fid, stack=()):
        """지운 중점 fid 대신 넣을 prerequisite 블록 목록 (남는 중점만)."""
        if fid in memo:
            return memo[fid]
        out = []
        for g in nodes[fid]["pre"]:
            out.extend(resolve(g, stack + (fid,)))
        memo[fid] = out
        return out

    def resolve(group, stack):
        keep = [x for x in group if x not in removed]
        if keep:
            return [keep]
        # 블록 전체가 지워짐: 첫 지운 중점의 prerequisite 를 대신 쓴다 (여러 개면 그 첫 블록들을 OR 로 합침)
        subs = [eff(x, stack) for x in group if x in nodes and x not in stack]
        subs = [s for s in subs if s]
        if not subs:
            return []
        if len(subs) == 1:
            return subs[0]
        merged = []
        for s in subs:
            for x in s[0]:
                if x not in merged:
                    merged.append(x)
        return [merged]

    new = {}
    for fid, n in nodes.items():
        if fid in removed:
            continue
        pre = []
        for g in n["pre"]:
            for r in resolve(g, (fid,)):
                if r not in pre:
                    pre.append(r)
        new[fid] = {"pre": pre, "me": [x for x in n["me"] if x not in removed]}
    anc = {}
    for fid in removed:
        if fid in nodes:
            e = eff(fid)
            anc[fid] = e[0][0] if e and e[0] else None
    return new, anc


def fix_refs(text, anc):
    if not anc:
        return text

    def rep(m):
        a = anc.get(m.group(1), "")
        if a == "":
            return m.group(0)
        return "has_completed_focus = %s" % a if a else "always = yes"

    return re.sub(r"has_completed_focus\s*=\s*([A-Za-z_]\w*)", rep, text)
