#!/usr/bin/env python3
"""Reference checker for the Terra Universalis mod (stdlib only, Python 3.10).

Usage:
    python -I tools/check_refs.py [--mod DIR] [--vanilla DIR] [--list-known]

What it checks (best effort):
  - effect and trigger names used in the mod's script files, against the vanilla
    documentation (documentation/effects_documentation.md, triggers_documentation.md)
  - modifier names used inside modifier blocks, against modifiers_documentation.md
  - GFX_ sprite names, against the vanilla interface/*.gfx files and the mod's own
    interface/*.gfx files (if any)
  - names defined inside the mod (block definitions such as focus, idea, decision,
    scripted effect/trigger names) count as known, so the mod's own items pass

Keys that are plain data fields (cost, icon, allowed, days, ...) are whitelisted.
Anything else that is not found is printed as UNKNOWN with file:line, so a few
false positives are expected. Fix real typos; whitelist harmless data keys in DATA.

Scanned mod folders: common/, events/, history/, tools/mapgen/country_history/.
"""

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DEFAULT_MOD = PROJECT / "terra_universalis"
DEFAULT_VANILLA = Path(r"G:\SteamLibrary\steamapps\common\Hearts of Iron IV")
EXTRA_SCAN = [PROJECT / "tools" / "mapgen" / "country_history"]

HEADING_RE = re.compile(r"^## ([A-Za-z_][A-Za-z0-9_]*)\s*$", re.M)
GFX_DEF_RE = re.compile(r'name\s*=\s*"?(GFX_[A-Za-z0-9_]+)"?')
TAG_RE = re.compile(r"^[A-Z][A-Z0-9]{1,3}$")

TOKEN_RE = re.compile(r'''
    (?P<ws>\s+)
  | (?P<comment>\#[^\n]*)
  | (?P<str>"(?:[^"\\\n]|\\.)*")
  | (?P<op><=|>=|!=|=|<|>|\{|\})
  | (?P<word>[^\s{}=<>"#]+)
''', re.X)

# Control flow and structure words (not effects or triggers).
STRUCTURAL = {
    "if", "else", "else_if", "limit", "AND", "OR", "NOT", "NAND", "NOR",
    "modifier", "add", "original_tag", "factor", "value", "var", "compare",
    "flag", "days", "hours", "months", "years", "tooltip", "target", "type",
    "level", "idea", "id", "name", "effect", "immediate", "option", "hidden",
    "is_triggered_only", "title", "desc", "picture", "add_namespace",
    "civilian_intel", "army_intel", "navy_intel", "airforce_intel",
    "set_default", "set_value", "tooltip_side", "owner", "count", "division",
    "prioritize_location", "start_experience_factor", "instant_build", "province",
}

# Data fields of focus, decision, idea, BoP, character, history, unit and event blocks.
DATA = {
    # common
    "icon", "picture", "cost", "x", "y", "prerequisite", "mutually_exclusive",
    "relative_position_id", "completion_reward", "completion_reward_joint_originator",
    "default", "country", "focus", "focus_tree", "allowed", "visible", "available",
    "complete_effect", "remove_effect", "ai_will_do", "fire_only_once", "days_re_enable",
    "days_remove", "priority", "bypass", "cancel_if_invalid", "continue_if_invalid",
    "available_if_capitulated", "search_filters", "text_icon", "allowed_is_joint",
    "allow_branch", "on_activate", "on_deactivate", "enable", "remove_trigger",
    "attacker_modifier", "on_add", "on_remove", "effect", "trigger",
    # bop
    "initial_value", "left_side", "right_side", "decision_category", "side", "range", "min", "max",
    # characters and leaders
    "characters", "portraits", "civilian", "army", "navy", "large", "small", "political",
    "country_leader", "ideology", "expire", "traits", "advisor", "slot", "idea_token",
    "ledger", "instance", "ideas",
    # history
    "set_politics", "ruling_party", "last_election", "election_frequency", "elections_allowed",
    "set_popularities", "recruit_character", "oob", "add_ideas", "set_power_balance",
    "capital", "set_research_slots", "set_state_category",
    # units
    "division_template", "regiments", "support", "division_names_group",
    "start_experience_factor", "start_equipment_factor",
    # on_actions
    "on_startup", "on_monthly", "on_daily", "on_yearly",
    # events
    "add_namespace",
    # misc / arbitrary sort keys
    "elite", "equipment", "amount", "producer", "custom_cost_trigger",
    "base", "bonus", "category", "building", "buildings", "air_base", "arms_factory",
    "history", "bookmark", "bookmarks", "callsigns", "color_ui", "continents", "areas",
    "complete_tooltip", "allowed_civil_war", "ahead_reduction", "attack_skill",
    "can_use", "can_create_factions", "can_send_volunteers", "can_use_kamikaze_pilots",
    "pick_best_tech", "unit_leader", "corps_commander", "skill", "generic",
    "color", "graphical_culture", "graphical_culture_2d",
}

# Blocks whose child keys are names being defined (e.g. characters = { TUA_leader = { } }).
DEF_PARENTS = {"characters"}

# Blocks that hold AI or scoring triggers; a modifier block inside them is a trigger list.
AI_CONTEXTS = {"ai_will_do", "ai_strategy", "country_score", "scorer", "base"}

# Keys whose child keys are variable names, not effects.
VAR_CONTEXT = {
    "set_variable", "add_to_variable", "subtract_from_variable", "multiply_variable",
    "divide_variable", "modulo_variable", "clamp_variable", "round_variable",
    "randomize_variable", "set_variable_to_random", "clear_variable", "check_variable",
    "set_temp_variable", "add_to_temp_variable", "subtract_from_temp_variable",
    "multiply_temp_variable", "divide_temp_variable", "modulo_temp_variable",
    "round_temp_variable", "clamp_temp_variable", "set_temp_variable_to_random",
    "randomize_temp_variable",
}

# Keys whose child keys are names or values, not effects.
LIST_CONTEXT = {"regiments", "support", "set_popularities", "traits", "portraits", "division"}

SCOPE_NAMES = {"capital_scope", "ROOT", "THIS", "FROM", "PREV", "OWNER", "CONTROLLER",
               "OCCUPIED", "CAPITAL", "overlord", "owner", "controller", "event_target"}

ITER_PREFIXES = ("every_", "random_", "ordered_", "any_", "all_", "every_other_")

DYN_SKIP = {"enable", "remove_trigger", "icon", "attacker_modifier", "on_add", "on_remove"}


def read_names(md_path):
    if not md_path.is_file():
        return set()
    text = md_path.read_text(encoding="utf-8", errors="replace")
    return set(HEADING_RE.findall(text))


def read_gfx_names(vanilla_or_mod_root):
    names = set()
    interface = vanilla_or_mod_root / "interface"
    if interface.is_dir():
        for gfx in interface.glob("*.gfx"):
            names.update(GFX_DEF_RE.findall(gfx.read_text(encoding="utf-8", errors="replace")))
    return names


def tokenize(text):
    toks = []
    line = 1
    for m in TOKEN_RE.finditer(text):
        kind = m.lastgroup
        val = m.group(kind)
        if kind == "ws":
            line += val.count("\n")
            continue
        if kind == "comment":
            continue
        toks.append((kind, val, line))
        line += val.count("\n")
    return toks


class Walker:
    """Walks a token list and calls back for block keys, leaf key/values and bare words."""

    def __init__(self, on_block, on_leaf, on_bare):
        self.on_block = on_block
        self.on_leaf = on_leaf
        self.on_bare = on_bare

    def run(self, toks, path):
        stack = []
        i = 0
        n = len(toks)
        while i < n:
            kind, val, line = toks[i]
            if kind == "op" and val == "}":
                if stack:
                    stack.pop()
                i += 1
                continue
            if kind == "op" and val == "{":
                stack.append(None)
                i += 1
                continue
            if kind in ("word", "str"):
                key = val.strip('"') if kind == "str" else val
                nxt = toks[i + 1] if i + 1 < n else None
                if nxt and nxt[0] == "op" and nxt[1] in ("=", "<", ">", "<=", ">=", "!="):
                    op = nxt[1]
                    after = toks[i + 2] if i + 2 < n else None
                    if after and after[0] == "op" and after[1] == "{" and op == "=":
                        self.on_block(key, list(stack), path, line)
                        stack.append(key)
                        i += 3
                        continue
                    if after and after[0] in ("word", "str"):
                        self.on_leaf(key, after[1].strip('"'), list(stack), path, line)
                        i += 3
                        continue
                    i += 2
                    continue
                self.on_bare(key, list(stack), path, line)
                i += 1
                continue
            i += 1


def iter_script_files(mod_root):
    seen = set()
    for sub in ("common", "events", "history"):
        base = mod_root / sub
        if base.is_dir():
            for p in sorted(base.rglob("*.txt")):
                seen.add(p)
    for extra in EXTRA_SCAN:
        if extra.is_dir():
            for p in sorted(extra.glob("*.txt")):
                seen.add(p)
    return sorted(seen)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Terra Universalis reference checker")
    ap.add_argument("--mod", default=str(DEFAULT_MOD), help="mod folder (terra_universalis)")
    ap.add_argument("--vanilla", default=str(DEFAULT_VANILLA), help="vanilla HOI4 folder")
    ap.add_argument("--list-known", action="store_true", help="also list the mod-defined names")
    ap.add_argument("--only", action="append", default=[],
                    help="only check files whose name contains this text (case-insensitive); repeatable")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    mod_root = Path(args.mod).resolve()
    vanilla = Path(args.vanilla)
    doc = vanilla / "documentation"
    if not mod_root.is_dir():
        print(f"ERROR mod folder not found: {mod_root}")
        return 1
    if not doc.is_dir():
        print(f"ERROR vanilla documentation not found: {doc}")
        return 1

    effects = read_names(doc / "effects_documentation.md")
    triggers = read_names(doc / "triggers_documentation.md")
    modifiers = read_names(doc / "modifiers_documentation.md")
    vanilla_gfx = read_gfx_names(vanilla)
    mod_gfx = read_gfx_names(mod_root)
    print(f"docs: effects={len(effects)} triggers={len(triggers)} modifiers={len(modifiers)} "
          f"vanilla_gfx={len(vanilla_gfx)}")

    all_files = iter_script_files(mod_root)
    files = all_files
    if args.only:
        needles = [s.lower() for s in args.only]
        files = [f for f in all_files if any(n in f.name.lower() for n in needles)]
        print(f"filter: {len(files)} files match {args.only} (definitions read from all {len(all_files)})")
    texts = {}
    trees = {}
    for path in all_files:
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig", errors="replace")
        texts[path] = text
        trees[path] = tokenize(text)

    # Pass 1: names defined inside the mod. A block key counts as a definition when it is
    # top-level or carries the mod prefix (TU_ / tu_). Other block keys are checked as usual,
    # so a misspelled effect used as a block (e.g. add_intell = { }) is still reported.
    defined = set()

    def note_definition(key, stack, path, line):
        if not stack or key.startswith(("TU_", "tu_")) or (stack[-1] in DEF_PARENTS):
            defined.add(key)

    pass1 = Walker(note_definition, lambda *a: None, lambda *a: None)
    for path in all_files:
        pass1.run(trees[path], path)
    defined -= {"", None}

    used_effects = Counter()
    used_triggers = Counter()
    used_modifiers = Counter()
    used_gfx = Counter()
    unknown = []  # (rel_path, line, key, context)
    rel = lambda p: p.relative_to(mod_root.parent).as_posix()

    def in_modifier_block(stack):
        """True when the nearest 'modifier' block is a stat modifier list (not an AI/score trigger list)."""
        if "modifier" not in stack:
            return False
        idx = len(stack) - 1 - stack[::-1].index("modifier")
        owner = stack[idx - 1] if idx > 0 else None
        return owner not in AI_CONTEXTS

    def check_gfx(name, path, line):
        used_gfx[name] += 1
        if name not in vanilla_gfx and name not in mod_gfx:
            unknown.append((rel(path), line, name, "GFX not defined in vanilla interface/*.gfx"))

    def classify(key, stack, path, line):
        if key.startswith("GFX_"):
            check_gfx(key, path, line)
            return
        parent = stack[-1] if stack else None
        if parent in VAR_CONTEXT or parent in LIST_CONTEXT:
            return
        if key in STRUCTURAL or key in DATA or key in SCOPE_NAMES:
            return
        if TAG_RE.match(key) or ":" in key or key.startswith(ITER_PREFIXES):
            return
        ctx = " > ".join(s for s in stack if s) or "(top)"
        if in_modifier_block(stack) or (
                "dynamic_modifiers" in path.parts and len(stack) == 1 and key not in DYN_SKIP):
            if key in modifiers:
                used_modifiers[key] += 1
            elif key in defined:
                return
            else:
                unknown.append((rel(path), line, key, "modifier not in modifiers_documentation: " + ctx))
            return
        if key in effects:
            used_effects[key] += 1
            return
        if key in triggers:
            used_triggers[key] += 1
            return
        if key in defined:
            return
        unknown.append((rel(path), line, key, ctx))

    def on_block(key, stack, path, line):
        if key.startswith("GFX_"):
            check_gfx(key, path, line)
            return
        classify(key, stack, path, line)

    def on_leaf(key, value, stack, path, line):
        classify(key, stack, path, line)
        if value.startswith("GFX_"):
            check_gfx(value, path, line)

    def on_bare(word, stack, path, line):
        if word.startswith("GFX_"):
            check_gfx(word, path, line)

    pass2 = Walker(on_block, on_leaf, on_bare)
    for path in files:
        pass2.run(trees[path], path)

    def show(title, counter):
        print(f"== {title} ({len(counter)} distinct, {sum(counter.values())} uses)")
        for name in sorted(counter):
            print(f"   {name} x{counter[name]}")

    show("effects used", used_effects)
    show("triggers used", used_triggers)
    show("modifiers used", used_modifiers)
    show("GFX used", used_gfx)
    if args.list_known:
        print(f"== mod-defined names ({len(defined)})")
        print("   " + ", ".join(sorted(defined)))

    # Unknown names are grouped so that each one is shown once with its locations.
    grouped = defaultdict(list)
    for rel_path, line, key, ctx in unknown:
        grouped[(key, ctx)].append(f"{rel_path}:{line}")
    print(f"== UNKNOWN ({len(grouped)} distinct)")
    for (key, ctx), where in sorted(grouped.items(), key=lambda kv: kv[0][0]):
        print(f"   {key}  [{ctx}]  at {', '.join(where[:4])}"
              + (f" (+{len(where) - 4} more)" if len(where) > 4 else ""))
    print(f"CHECK_REFS files={len(files)} effects={len(used_effects)} triggers={len(used_triggers)} "
          f"modifiers={len(used_modifiers)} gfx={len(used_gfx)} unknown={len(grouped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
