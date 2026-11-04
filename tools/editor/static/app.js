"use strict";
// Terra Universalis 편집기 화면. 서버(server.py)가 게임 파일을 읽고 쓰고, 여기서는 항목을 고친 사본(work)을 들고 있다가
// 저장할 때 바뀐 것만 보낸다.

const $ = (s) => document.querySelector(s);
const el = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) e.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kids.flat()) if (k !== null && k !== undefined && k !== false) e.append(k);
  return e;
};
const SVG = "http://www.w3.org/2000/svg";
const sv = (tag, attrs = {}) => {
  const e = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
};

async function api(path, body) {
  const opt = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  const j = await r.json();
  if (j && j.error) throw new Error(j.error);
  return j;
}

function toast(msg, cls = "") {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast " + cls;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.add("hidden"), cls === "err" ? 7000 : 3000);
}

// ------------------------------------------------------------------ 종류별 화면 정의

const BLOCK = "block", SCALAR = "scalar";
const SCHEMA = {
  focus: [
    { k: "id", t: SCALAR, label: "ID" },
    { k: "icon", t: SCALAR, label: "아이콘 (GFX)" },
    { row: [{ k: "x", t: SCALAR, label: "x" }, { k: "y", t: SCALAR, label: "y" }, { k: "cost", t: SCALAR, label: "기간 (×7일)" }] },
    { k: "relative_position_id", t: SCALAR, label: "상대 위치 기준 중점" },
    { k: "prerequisite", t: "prereq", label: "선행 중점 (한 줄 = 모두 필요, 줄 안의 여러 ID = 그중 하나)" },
    { k: "mutually_exclusive", t: "mutex", label: "상호 배타 중점 (공백으로 구분)" },
    { k: "available", t: BLOCK, label: "선택 조건 (available)" },
    { k: "bypass", t: BLOCK, label: "건너뛰기 조건 (bypass)" },
    { k: "select_effect", t: BLOCK, label: "선택할 때 효과 (select_effect)" },
    { k: "completion_reward", t: BLOCK, label: "완료 효과 (completion_reward)", open: true },
    { k: "ai_will_do", t: BLOCK, label: "AI 가중치 (ai_will_do)" },
    { k: "search_filters", t: BLOCK, label: "검색 필터" },
  ],
  decision: [
    { k: "icon", t: SCALAR, label: "아이콘 (GFX)" },
    { row: [{ k: "cost", t: SCALAR, label: "정치력" }, { k: "days_remove", t: SCALAR, label: "진행 일수" }, { k: "days_re_enable", t: SCALAR, label: "재사용 대기" }] },
    { row: [{ k: "fire_only_once", t: SCALAR, label: "한 번만 (yes/no)" }, { k: "state_target", t: SCALAR, label: "주 대상 (yes)" }, { k: "priority", t: SCALAR, label: "우선순위" }] },
    { k: "allowed", t: BLOCK, label: "허용 (allowed, 게임 시작 때 한 번)" },
    { k: "visible", t: BLOCK, label: "보이는 조건 (visible)" },
    { k: "available", t: BLOCK, label: "사용 조건 (available)" },
    { k: "target_trigger", t: BLOCK, label: "대상 조건 (target_trigger)" },
    { k: "complete_effect", t: BLOCK, label: "실행 효과 (complete_effect)", open: true },
    { k: "remove_effect", t: BLOCK, label: "끝날 때 효과 (remove_effect)" },
    { k: "ai_will_do", t: BLOCK, label: "AI 가중치 (ai_will_do)" },
  ],
  category: [
    { k: "icon", t: SCALAR, label: "아이콘 (GFX)" },
    { row: [{ k: "picture", t: SCALAR, label: "그림" }, { k: "priority", t: SCALAR, label: "우선순위" }] },
    { k: "allowed", t: BLOCK, label: "허용 (allowed)" },
    { k: "visible", t: BLOCK, label: "보이는 조건 (visible)" },
    { k: "available", t: BLOCK, label: "사용 조건 (available)" },
  ],
  idea: [
    { k: "picture", t: SCALAR, label: "그림 (picture)" },
    { k: "allowed", t: BLOCK, label: "허용 (allowed)" },
    { k: "allowed_civil_war", t: BLOCK, label: "내전 때 유지 (allowed_civil_war)" },
    { k: "available", t: BLOCK, label: "사용 조건 (available)" },
    { k: "modifier", t: BLOCK, label: "모디파이어 (modifier)", open: true },
    { k: "targeted_modifier", t: BLOCK, label: "대상 모디파이어 (targeted_modifier)" },
    { k: "research_bonus", t: BLOCK, label: "연구 보너스" },
    { k: "equipment_bonus", t: BLOCK, label: "장비 보너스" },
    { k: "on_add", t: BLOCK, label: "추가될 때 효과 (on_add)" },
    { k: "on_remove", t: BLOCK, label: "제거될 때 효과 (on_remove)" },
    { k: "cancel", t: BLOCK, label: "자동 제거 조건 (cancel)" },
  ],
  character: [
    { k: "name", t: SCALAR, label: "이름 키 (name)" },
    { k: "portraits", t: BLOCK, label: "초상화 (portraits)", open: true },
    { k: "country_leader", t: BLOCK, label: "국가 지도자 역할", multi: true },
    { k: "corps_commander", t: BLOCK, label: "장군 (군단장) 역할" },
    { k: "field_marshal", t: BLOCK, label: "원수 역할" },
    { k: "navy_leader", t: BLOCK, label: "제독 역할" },
    { k: "advisor", t: BLOCK, label: "고문 역할", multi: true },
  ],
  event: [
    { k: "id", t: SCALAR, label: "ID" },
    { row: [{ k: "title", t: SCALAR, label: "제목 키" }, { k: "desc", t: SCALAR, label: "설명 키" }] },
    { k: "picture", t: SCALAR, label: "그림 (GFX)" },
    { row: [{ k: "is_triggered_only", t: SCALAR, label: "호출 전용 (yes)" }, { k: "fire_only_once", t: SCALAR, label: "한 번만" }, { k: "hidden", t: SCALAR, label: "숨김" }] },
    { k: "trigger", t: BLOCK, label: "발생 조건 (trigger)" },
    { k: "mean_time_to_happen", t: BLOCK, label: "평균 발생 시간" },
    { k: "immediate", t: BLOCK, label: "즉시 효과 (immediate)" },
    { k: "option", t: BLOCK, label: "선택지", multi: true, open: true },
  ],
};

const ROLE_TEMPLATES = {
  country_leader: 'ideology = despotism\nexpire = "1200.1.1.1"\nid = -1',
  corps_commander: "traits = { }\nskill = 3\nattack_skill = 3\ndefense_skill = 3\nplanning_skill = 3\nlogistics_skill = 3\nlegacy_id = -1",
  field_marshal: "traits = { }\nskill = 3\nattack_skill = 3\ndefense_skill = 3\nplanning_skill = 3\nlogistics_skill = 3\nlegacy_id = -1",
  navy_leader: "traits = { }\nskill = 3\nattack_skill = 3\ndefense_skill = 3\nmaneuvering_skill = 3\ncoordination_skill = 3\nlegacy_id = -1",
};

// ------------------------------------------------------------------ 상태

const S = {
  kinds: {}, kind: "focus", files: [], file: null,
  work: [],          // [{loc, key, parent, children, orig, isNew, deleted}]
  sel: null,         // 선택한 항목
  loc: {}, locOrig: {}, // 로컬라이제이션 {키: {ko, en}}
  filter: "", lastTA: null, seq: 0,
  view: { x: 60, y: 80, k: 1 },
};

const clone = (o) => JSON.parse(JSON.stringify(o));
const snap = (ent) => JSON.stringify({ key: ent.key, parent: ent.parent, children: ent.children });
const isChanged = (ent) => ent.isNew || ent.deleted || snap(ent) !== ent.orig;
const locChanged = () => Object.keys(S.loc).some((k) => ["ko", "en"].some((l) => (S.loc[k][l] || "") !== (S.locOrig[k]?.[l] || "")));
const anyDirty = () => S.work.some(isChanged) || locChanged();

function child(ent, key) { return ent.children.find((c) => c.key === key); }
function scalar(ent, key) { const c = child(ent, key); return c && c.kind === SCALAR ? c.value : ""; }
function unq(v) { return (v || "").replace(/^"(.*)"$/, "$1"); }

function setScalar(ent, key, value) {
  const i = ent.children.findIndex((c) => c.key === key);
  value = value.trim();
  if (!value) { if (i >= 0) ent.children.splice(i, 1); }
  else if (i >= 0) { ent.children[i].value = value; ent.children[i].kind = SCALAR; }
  else ent.children.push({ i: null, key, op: "=", kind: SCALAR, value });
  touched(ent);
}

function setBlocks(ent, key, values) {
  // key 를 가진 항목들을 values 목록으로 바꾼다. 원래 자리(i)는 앞에서부터 다시 쓴다.
  const old = ent.children.filter((c) => c.key === key);
  const rest = ent.children.filter((c) => c.key !== key);
  const firstPos = ent.children.findIndex((c) => c.key === key);
  const made = values.map((v, n) => (old[n] ? { ...old[n], kind: BLOCK, value: v } : { i: null, key, op: "=", kind: BLOCK, value: v }));
  if (firstPos >= 0) rest.splice(Math.min(firstPos, rest.length), 0, ...made);
  else rest.push(...made);
  ent.children = rest;
  touched(ent);
}

function tagOfFile() {
  const base = (S.file?.path || "").split("/").pop().replace(/\.txt$/, "");
  const m = base.match(/^tu_([a-z]{3})(?:_|$)/i) || base.match(/^([A-Z]{3})$/);
  return m ? m[1].toUpperCase() : "TAG";
}

function locOf(ent) {
  const k = S.kind;
  if (k === "focus") return "focus:" + scalar(ent, "id");
  if (k === "decision") return `decision:${ent.parent}/${ent.key}`;
  if (k === "category") return "category:" + ent.key;
  if (k === "idea") return `idea:${ent.parent}/${ent.key}`;
  if (k === "character") return "character:" + ent.key;
  if (k === "event") return "event:" + scalar(ent, "id");
  return ent.loc;
}

function locKeys(ent) {
  const k = S.kind;
  if (k === "focus") { const id = scalar(ent, "id"); return id ? [id, id + "_desc"] : []; }
  if (k === "character") return [unq(scalar(ent, "name")) || ent.key];
  if (k === "event") {
    const keys = [unq(scalar(ent, "title")), unq(scalar(ent, "desc"))];
    for (const o of ent.children.filter((c) => c.key === "option" && c.kind === BLOCK)) {
      const m = o.value.match(/(?:^|\s)name\s*=\s*("?[^\s"}]+"?)/);
      if (m) keys.push(unq(m[1]));
    }
    return keys.filter(Boolean);
  }
  return [ent.key, ent.key + "_desc"];
}

function title(ent) {
  const k = locKeys(ent)[0];
  return (k && S.loc[k]?.ko) || "";
}

// ------------------------------------------------------------------ 불러오기

async function init() {
  const k = await api("/api/kinds");
  S.kinds = k.kinds;
  S.game = k.game;
  const nav = $("#kinds");
  for (const [id, label] of Object.entries(S.kinds)) {
    nav.append(el("button", { "data-kind": id, onclick: () => switchKind(id) }, label));
  }
  $("#file").addEventListener("change", (e) => openFile(e.target.value));
  $("#filter").addEventListener("input", (e) => { S.filter = e.target.value.toLowerCase(); renderList(); });
  $("#btn-new").addEventListener("click", newEntity);
  $("#btn-save").addEventListener("click", saveAll);
  $("#btn-revert").addEventListener("click", () => { if (!anyDirty() || confirm("고친 내용을 모두 버릴까요?")) openFile(S.file.path, true); });
  $("#btn-docs").addEventListener("click", openDocs);
  $("#btn-check").addEventListener("click", runCheck);
  $("#btn-git").addEventListener("click", () => openGit(true));
  $("#drawer-close").addEventListener("click", () => $("#drawer").classList.add("hidden"));
  $("#tree-fit").addEventListener("click", fitTree);
  document.addEventListener("focusin", (e) => { if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") S.lastTA = e.target; });
  document.addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); saveAll(); } });
  window.addEventListener("beforeunload", (e) => { if (anyDirty()) { e.preventDefault(); e.returnValue = ""; } });
  const cid = Math.random().toString(36).slice(2, 10);         // exe 실행기: 창이 살아 있다는 신호
  window.addEventListener("pagehide", () => navigator.sendBeacon("/api/bye", JSON.stringify({ id: cid })));
  const ping = () => fetch("/api/ping?id=" + cid).catch(() => {});
  ping(); setInterval(ping, 5000);
  setupTree();
  const saved = (() => { try { return JSON.parse(localStorage.getItem("tu-editor") || "{}"); } catch { return {}; } })();
  const q = new URLSearchParams(location.search);       // ?kind=focus&path=...&sel=focus:ID 로 바로 열기
  const kind = q.get("kind") || saved.kind;
  await switchKind(kind && S.kinds[kind] ? kind : "focus", q.get("path") || saved.path);
  const want = q.get("sel");
  const ent = want && S.work.find((e) => e.loc === want);
  if (ent) select(ent);
  if (q.get("panel") === "git") openGit(false);
}

function remember() {
  try { localStorage.setItem("tu-editor", JSON.stringify({ kind: S.kind, path: S.file?.path })); } catch { /* 없어도 됨 */ }
}

async function switchKind(kind, path) {
  if (anyDirty() && !confirm("저장하지 않은 내용이 있습니다. 버리고 넘어갈까요?")) return;
  S.kind = kind;
  for (const b of document.querySelectorAll("#kinds button")) b.classList.toggle("on", b.dataset.kind === kind);
  S.files = await api("/api/files?kind=" + kind);
  const sel = $("#file");
  sel.innerHTML = "";
  for (const f of S.files) {
    const name = f.path.split("/").pop();
    sel.append(el("option", { value: f.path }, `${name}  (${f.count})${f.generated ? "  · 생성됨" : ""}${f.error ? "  · 오류" : ""}`));
  }
  const pick = S.files.find((f) => f.path === path) || S.files[0];
  if (pick) { sel.value = pick.path; await openFile(pick.path, true); }
  else { S.file = null; S.work = []; renderAll(); }
}

async function openFile(path, force) {
  if (!force && anyDirty() && !confirm("저장하지 않은 내용이 있습니다. 버리고 넘어갈까요?")) { $("#file").value = S.file.path; return; }
  const f = await api(`/api/file?kind=${S.kind}&path=${encodeURIComponent(path)}`);
  applyFile(f);
  S.sel = null;
  S.loc = {}; S.locOrig = {};
  await loadLoc(S.work.flatMap((e) => locKeys(e).slice(0, 1)));
  remember();
  renderAll();
  if (S.kind === "focus") fitTree();
}

function applyFile(f) {
  S.file = f;
  S.work = f.entities.map((e) => {
    const w = { loc: e.loc, key: e.key, parent: e.parent, line: e.line, children: clone(e.children), isNew: false, deleted: false };
    w.orig = snap(w);
    return w;
  });
  const info = $("#file-info");
  info.textContent = `${f.path} · ${f.entities.length}개`;
  const b = $("#banner");
  if (f.error) { b.textContent = "파일을 읽을 수 없습니다: " + f.error; b.className = "banner err"; }
  else if (f.generated) {
    b.textContent = "이 파일은 생성 도구가 만든 파일입니다. 생성 도구(tools/focusgen 등)를 다시 돌리면 여기서 고친 내용이 덮어써집니다.";
    b.className = "banner";
  } else b.className = "banner hidden";
}

async function loadLoc(keys) {
  keys = [...new Set(keys.filter((k) => k && !(k in S.loc)))];
  for (let i = 0; i < keys.length; i += 120) {
    const part = keys.slice(i, i + 120);
    const r = await api("/api/loc?keys=" + encodeURIComponent(part.join(",")));
    for (const [k, v] of Object.entries(r)) {
      S.loc[k] = { ko: v.ko || "", en: v.en || "" };
      S.locOrig[k] = { ko: v.ko || "", en: v.en || "" };
    }
  }
}

// ------------------------------------------------------------------ 목록

function renderAll() {
  const tree = S.kind === "focus";
  $("#tree-wrap").classList.toggle("hidden", !tree);
  $("#main").classList.toggle("with-tree", tree);
  renderList();
  renderEditor();
  if (tree) renderTree();
  updateDirty();
}

function renderList() {
  const ul = $("#list");
  ul.innerHTML = "";
  let lastParent = null;
  const showGroups = ["decision", "idea"].includes(S.kind);
  for (const ent of S.work) {
    const id = S.kind === "focus" || S.kind === "event" ? scalar(ent, "id") : ent.key;
    const name = title(ent);
    const hay = (id + " " + name + " " + ent.parent).toLowerCase();
    if (S.filter && !hay.includes(S.filter)) continue;
    if (showGroups && ent.parent !== lastParent) {
      ul.append(el("li", { class: "group" }, ent.parent || "(분류 없음)"));
      lastParent = ent.parent;
    }
    const roles = S.kind === "character" ? ["country_leader", "corps_commander", "field_marshal", "navy_leader", "advisor"]
      .filter((r) => child(ent, r)).map((r) => el("span", { class: "chip role" }, { country_leader: "지도자", corps_commander: "장군", field_marshal: "원수", navy_leader: "제독", advisor: "고문" }[r])) : [];
    const li = el("li", {
      class: [ent === S.sel ? "sel" : "", isChanged(ent) ? "changed" : "", ent.deleted ? "del" : ""].join(" "),
      onclick: () => select(ent),
    }, el("span", { class: "n" }, name || id, ...roles), el("span", { class: "k" }, id));
    ent._li = li;
    ul.append(li);
  }
}

function select(ent) {
  S.sel = ent;
  for (const li of document.querySelectorAll("#list li")) li.classList.remove("sel");
  if (ent._li) { ent._li.classList.add("sel"); ent._li.scrollIntoView({ block: "nearest" }); }
  loadLoc(locKeys(ent)).then(renderEditor);
  if (S.kind === "focus") renderTree();
}

function touched(ent) {
  if (ent._li) {
    ent._li.classList.toggle("changed", isChanged(ent));
    const n = ent._li.querySelector(".n");
    if (n && n.firstChild && n.firstChild.nodeType === 3) n.firstChild.textContent = title(ent) || (S.kind === "focus" || S.kind === "event" ? scalar(ent, "id") : ent.key);
  }
  if (S.kind === "focus") scheduleTree();
  updateDirty();
}

function updateDirty() { $("#dirty").classList.toggle("hidden", !anyDirty()); }

// ------------------------------------------------------------------ 편집 화면

function renderEditor() {
  const box = $("#editor");
  box.innerHTML = "";
  const ent = S.sel;
  if (!S.file) { box.append(el("div", { class: "empty" }, "파일이 없습니다.")); return; }
  if (!ent) {
    box.append(el("div", { class: "empty" }, S.kind === "focus" ? "트리나 왼쪽 목록에서 중점을 고르세요." : "왼쪽 목록에서 항목을 고르세요.",
      el("br"), el("br"), el("span", {}, "새 항목은 왼쪽 위 ＋ 새로 버튼으로 만듭니다.")));
    return;
  }
  const keyEditable = !["focus", "event"].includes(S.kind);
  const shown = S.kind === "focus" || S.kind === "event" ? scalar(ent, "id") : ent.key;
  box.append(el("h2", {}, title(ent) || shown));
  box.append(el("div", { class: "sub" },
    `${S.file.path}${ent.line ? " · " + ent.line + "줄" : ""}${ent.parent ? " · " + ent.parent : ""}`,
    ent.isNew ? el("span", { class: "chip gen" }, "새 항목") : null,
    ent.deleted ? el("span", { class: "chip gen" }, "삭제 예정") : null));

  if (keyEditable) {
    box.append(field("키 (이름)", el("input", { type: "text", value: ent.key, onchange: (e) => { ent.key = e.target.value.trim() || ent.key; touched(ent); } }), ent.isNew ? null : "바꾸면 이 키를 쓰는 다른 곳도 직접 고쳐야 합니다"));
  }

  // 로컬라이제이션
  const keys = locKeys(ent);
  if (keys.length) {
    box.append(el("h3", {}, "표시 글자 (로컬라이제이션)"));
    for (const k of keys) {
      if (!S.loc[k]) { S.loc[k] = { ko: "", en: "" }; S.locOrig[k] = { ko: "", en: "" }; }
      const long = /_desc$|\.d$|desc/.test(k);
      const mk = (lang) => {
        const a = { value: S.loc[k][lang], oninput: (e) => { S.loc[k][lang] = e.target.value; updateDirty(); if (k === keys[0] && lang === "ko") touched(ent); } };
        return long ? el("textarea", { rows: 3, class: "text", ...a }, S.loc[k][lang]) : el("input", { type: "text", ...a });
      };
      box.append(el("div", { class: "grid2" }, field(`한국어 · ${k}`, mk("ko")), field(`English · ${k}`, mk("en"))));
    }
  }

  // 정의된 항목
  const spec = SCHEMA[S.kind] || [];
  const known = new Set();
  box.append(el("h3", {}, "내용"));
  for (const s of spec) {
    if (s.row) {
      s.row.forEach((r) => known.add(r.k));
      box.append(el("div", { class: s.row.length === 3 ? "grid3" : "grid2" }, ...s.row.map((r) => specField(ent, r))));
    } else {
      known.add(s.k);
      box.append(specField(ent, s));
    }
  }
  if (S.kind === "character") box.append(roleButtons(ent));

  // 그 밖의 항목
  const other = ent.children.filter((c) => !known.has(c.key));
  if (other.length) box.append(el("h3", {}, "그 밖의 항목"));
  for (const c of other) {
    if (c.kind === "bare") { box.append(field("(키 없는 값)", el("pre", { class: "out" }, c.value))); continue; }
    const del = el("button", { class: "small danger", onclick: () => { ent.children.splice(ent.children.indexOf(c), 1); touched(ent); renderEditor(); } }, "삭제");
    const input = c.kind === BLOCK
      ? el("textarea", { rows: rowsFor(c.value), oninput: (e) => { c.value = e.target.value; touched(ent); } }, c.value)
      : el("input", { type: "text", value: c.value, oninput: (e) => { c.value = e.target.value; touched(ent); } });
    box.append(field(c.key + (c.op && c.op !== "=" ? " " + c.op : ""), input, null, del));
  }

  // 항목 추가
  const nk = el("input", { type: "text", placeholder: "키 (예: cancel_if_invalid)" });
  const nt = el("select", {}, el("option", { value: BLOCK }, "블록 { }"), el("option", { value: SCALAR }, "값"));
  box.append(el("h3", {}, "항목 추가"));
  box.append(el("div", { class: "row" }, nk, nt, el("button", {
    onclick: () => {
      const key = nk.value.trim();
      if (!/^[\w.@:\-]+$/.test(key)) { toast("키 이름이 올바르지 않습니다", "err"); return; }
      ent.children.push({ i: null, key, op: "=", kind: nt.value, value: nt.value === BLOCK ? "" : "yes" });
      touched(ent); renderEditor();
    },
  }, "추가")));

  const actions = el("div", { class: "actions" });
  if (ent.deleted) actions.append(el("button", { onclick: () => { ent.deleted = false; touched(ent); renderList(); renderEditor(); } }, "삭제 취소"));
  else actions.append(el("button", { class: "danger", onclick: () => { if (ent.isNew) { S.work.splice(S.work.indexOf(ent), 1); S.sel = null; renderAll(); } else { ent.deleted = true; touched(ent); renderList(); renderEditor(); } } }, "이 항목 삭제"));
  if (S.kind === "character" && /^[A-Z]{3}$/.test(tagOfFile())) {
    actions.append(el("button", { onclick: () => recruit(ent) }, `국가 기록에 영입 추가 (${tagOfFile()})`));
  }
  if (S.kind === "focus") actions.append(el("button", { onclick: () => newEntity(ent) }, "이 중점 아래에 새 중점"));
  box.append(actions);
}

function rowsFor(v) { return Math.min(Math.max((v || "").split("\n").length + 1, 3), 24); }

function field(label, input, note, extra) {
  return el("div", { class: "field" }, el("label", {}, el("span", {}, label), extra || null), input, note ? el("div", { class: "sub" }, note) : null);
}

function specField(ent, s) {
  const lab = el("span", {}, s.label, " ", el("code", {}, s.k));
  if (s.t === SCALAR) {
    return el("div", { class: "field" }, el("label", {}, lab),
      el("input", { type: "text", value: scalar(ent, s.k), oninput: (e) => setScalar(ent, s.k, e.target.value) }));
  }
  if (s.t === "prereq") {
    const lines = ent.children.filter((c) => c.key === "prerequisite").map((c) => [...c.value.matchAll(/focus\s*=\s*([^\s}]+)/g)].map((m) => m[1]).join(" "));
    return el("div", { class: "field" }, el("label", {}, lab), el("textarea", {
      rows: Math.max(2, lines.length + 1),
      oninput: (e) => setBlocks(ent, "prerequisite", e.target.value.split("\n").map((l) => l.trim()).filter(Boolean)
        .map((l) => l.split(/[\s|,]+/).filter(Boolean).map((id) => "focus = " + id).join(" "))),
    }, lines.join("\n")));
  }
  if (s.t === "mutex") {
    const c = child(ent, "mutually_exclusive");
    const ids = c ? [...c.value.matchAll(/focus\s*=\s*([^\s}]+)/g)].map((m) => m[1]).join(" ") : "";
    return el("div", { class: "field" }, el("label", {}, lab), el("input", {
      type: "text", value: ids,
      oninput: (e) => { const v = e.target.value.split(/[\s|,]+/).filter(Boolean); setBlocks(ent, "mutually_exclusive", v.length ? [v.map((id) => "focus = " + id).join(" ")] : []); },
    }));
  }
  // 블록
  const items = ent.children.filter((c) => c.key === s.k);
  const wrap = el("div", { class: "field" });
  const add = el("button", { class: "small", onclick: () => {
    const tpl = S.kind === "character" ? (ROLE_TEMPLATES[s.k] || "") : (s.k === "option" ? "name = " + newOptionKey(ent) : "");
    ent.children.push({ i: null, key: s.k, op: "=", kind: BLOCK, value: tpl });
    touched(ent); renderEditor();
  } }, items.length && s.multi ? "＋ 하나 더" : "＋ 추가");
  if (!items.length) {
    wrap.append(el("label", {}, lab, add));
    return wrap;
  }
  items.forEach((c, n) => {
    const del = el("button", { class: "small danger", onclick: () => { ent.children.splice(ent.children.indexOf(c), 1); touched(ent); renderEditor(); } }, "삭제");
    wrap.append(el("label", {}, el("span", {}, s.label + (items.length > 1 ? ` ${n + 1}` : ""), " ", el("code", {}, s.k)), el("span", {}, del, " ", n === items.length - 1 && s.multi ? add : null)));
    wrap.append(el("textarea", { rows: s.open ? Math.max(rowsFor(c.value), 6) : rowsFor(c.value), oninput: (e) => { c.value = e.target.value; touched(ent); } }, c.value));
  });
  return wrap;
}

function newOptionKey(ent) {
  const id = scalar(ent, "id") || "event";
  const n = ent.children.filter((c) => c.key === "option").length;
  return `${id}.${"abcdefgh"[n] || n}`;
}

function roleButtons(ent) {
  const row = el("div", { class: "addrow" });
  const tag = tagOfFile();
  const roles = [
    ["country_leader", "＋ 국가 지도자"], ["corps_commander", "＋ 장군"], ["field_marshal", "＋ 원수"], ["navy_leader", "＋ 제독"], ["advisor", "＋ 고문"],
  ];
  for (const [r, label] of roles) {
    if (!["country_leader", "advisor"].includes(r) && child(ent, r)) continue;
    row.append(el("button", { onclick: () => {
      const tpl = r === "advisor"
        ? `slot = political_advisor\nidea_token = ${ent.key}\nledger = civilian\ncost = 150\nallowed = { original_tag = ${tag} }\ntraits = { }`
        : ROLE_TEMPLATES[r];
      ent.children.push({ i: null, key: r, op: "=", kind: BLOCK, value: tpl });
      if (["corps_commander", "field_marshal", "navy_leader"].includes(r)) {
        const p = child(ent, "portraits");
        if (p && !/army\s*=|navy\s*=/.test(p.value)) p.value += "\narmy = { large = \"GFX_Portrait_Europe_Generic_land_1\" small = \"GFX_Portrait_Europe_Generic_land_1\" }";
      }
      touched(ent); renderEditor();
    } }, label));
  }
  return row;
}

// ------------------------------------------------------------------ 새 항목

function newEntity(below) {
  if (!S.file) return;
  const kind = S.kind, tag = tagOfFile(), pre = "TU_" + tag;
  let key, parent = "", children = [];
  const C = (key, value, kind = SCALAR) => ({ i: null, key, op: "=", kind, value });
  if (kind === "focus") {
    const id = prompt("새 중점 ID", pre + "_new_focus");
    if (!id) return;
    if (S.work.some((e) => scalar(e, "id") === id)) { toast("이미 있는 ID입니다", "err"); return; }
    const base = below && below.children ? below : S.sel;
    let x = 0, y = 0;
    if (base) { const p = absPos()[scalar(base, "id")]; if (p) { x = p.x; y = p.y + 1; } }
    key = "focus"; parent = S.file.parents[0] || "";
    children = [C("id", id), C("icon", "GFX_goal_generic_political_pressure")];
    if (base) children.push(C("prerequisite", "focus = " + scalar(base, "id"), BLOCK));
    children.push(C("x", String(x)), C("y", String(y)), C("cost", "10"), C("search_filters", "FOCUS_FILTER_POLITICAL", BLOCK),
      C("ai_will_do", "base = 1", BLOCK), C("completion_reward", "", BLOCK));
  } else if (kind === "decision") {
    parent = prompt("넣을 디시전 분류 (없으면 새로 만듭니다)", (S.sel && S.sel.parent) || S.file.parents[0] || pre + "_category");
    if (!parent) return;
    key = prompt("새 디시전 이름", pre + "_new_decision");
    if (!key) return;
    children = [C("icon", "GFX_decision_generic_political_discourse"), C("allowed", "original_tag = " + tag, BLOCK), C("available", "", BLOCK),
      C("cost", "50"), C("fire_only_once", "yes"), C("complete_effect", "", BLOCK), C("ai_will_do", "base = 1", BLOCK)];
  } else if (kind === "category") {
    key = prompt("새 디시전 분류 이름", pre + "_new_category");
    if (!key) return;
    children = [C("icon", "GFX_decision_category_generic_political_actions"), C("allowed", "original_tag = " + tag, BLOCK), C("priority", "100")];
  } else if (kind === "idea") {
    parent = prompt("국민정신 칸 (country = 일반 국민정신)", (S.sel && S.sel.parent) || "country");
    if (!parent) return;
    key = prompt("새 국민정신 이름", pre + "_new_spirit");
    if (!key) return;
    children = [C("picture", "generic_political_support"), C("allowed", "original_tag = " + tag, BLOCK), C("modifier", "political_power_gain = 0.1", BLOCK)];
  } else if (kind === "character") {
    if (!S.file.parents.includes("characters")) { toast("이 파일에는 characters = { } 블록이 없습니다", "err"); return; }
    key = prompt("새 캐릭터 키 (지도자·장군 공통)", pre + "_new_character");
    if (!key) return;
    parent = "characters";
    children = [C("name", key), C("portraits", 'civilian = { large = "GFX_Portrait_Europe_Generic_1" }', BLOCK)];
  } else if (kind === "event") {
    const ids = S.work.map((e) => scalar(e, "id")).filter(Boolean);
    const ns = ids.length ? ids[0].split(".")[0] : tag.toLowerCase() + "_ev";
    const next = Math.max(0, ...ids.filter((i) => i.startsWith(ns + ".")).map((i) => parseInt(i.split(".")[1], 10) || 0)) + 1;
    const id = prompt("새 이벤트 ID", `${ns}.${next}`);
    if (!id) return;
    key = "country_event";
    children = [C("id", id), C("title", id + ".t"), C("desc", id + ".d"), C("picture", "GFX_report_event_generic_read_write"),
      C("is_triggered_only", "yes"), C("option", "name = " + id + ".a", BLOCK)];
  }
  if (S.work.some((e) => !e.deleted && e.key === key && e.parent === parent && !["focus", "event"].includes(kind))) { toast("이미 있는 이름입니다", "err"); return; }
  const ent = { loc: "new:" + (++S.seq), key, parent, children, isNew: true, deleted: false };
  ent.orig = "";
  S.work.push(ent);
  for (const k of locKeys(ent)) { S.loc[k] = S.loc[k] || { ko: "", en: "" }; S.locOrig[k] = S.locOrig[k] || { ko: "", en: "" }; }
  renderList();
  select(ent);
  updateDirty();
}

// ------------------------------------------------------------------ 저장

async function saveAll() {
  if (!S.file) return;
  const changes = [];
  for (const ent of S.work) {
    if (ent.isNew && !ent.deleted) changes.push({ op: "create", parent: ent.parent, key: ent.key, children: ent.children.map(({ i, ...c }) => c) });
    else if (!ent.isNew && ent.deleted) changes.push({ op: "delete", loc: ent.loc });
    else if (!ent.isNew && isChanged(ent)) changes.push({ op: "edit", loc: ent.loc, key: ent.key, children: ent.children });
  }
  const items = [];
  for (const [k, v] of Object.entries(S.loc)) {
    for (const lang of ["ko", "en"]) {
      if ((v[lang] || "") !== (S.locOrig[k]?.[lang] || "")) items.push({ key: k, lang, value: v[lang] || "" });
    }
  }
  if (!changes.length && !items.length) { toast("바뀐 내용이 없습니다"); return; }
  const selLoc = S.sel ? locOf(S.sel) : null;
  try {
    if (changes.length) {
      const f = await api("/api/save", { kind: S.kind, path: S.file.path, hash: S.file.hash, changes });
      applyFile(f);
    }
    if (items.length) {
      await api("/api/loc", { items });
      for (const it of items) S.locOrig[it.key] = { ...(S.locOrig[it.key] || {}), [it.lang]: it.value };
    }
    S.sel = S.work.find((e) => e.loc === selLoc) || null;
    renderAll();
    toast(`저장했습니다 (항목 ${changes.length}개, 글자 ${items.length}개)`, "ok");
  } catch (e) {
    toast("저장 실패: " + e.message, "err");
  }
}

async function recruit(ent) {
  try {
    const r = await api("/api/recruit", { tag: tagOfFile(), name: ent.key });
    toast(r.message, "ok");
  } catch (e) { toast(e.message, "err"); }
}

// ------------------------------------------------------------------ 중점 트리

const UX = 62, UY = 110, NW = 116, NH = 50;

function absPos() {
  const byId = {};
  for (const e of S.work) if (!e.deleted) byId[scalar(e, "id")] = e;
  const memo = {};
  const pos = (id, depth) => {
    if (memo[id]) return memo[id];
    const e = byId[id];
    if (!e) return null;
    let x = parseFloat(scalar(e, "x")) || 0, y = parseFloat(scalar(e, "y")) || 0;
    const rel = scalar(e, "relative_position_id");
    if (rel && depth < 60) { const p = pos(rel, depth + 1); if (p) { x += p.x; y += p.y; } }
    return (memo[id] = { x, y });
  };
  const out = {};
  for (const id of Object.keys(byId)) out[id] = pos(id, 0);
  return out;
}

let treeTimer = null;
function scheduleTree() { clearTimeout(treeTimer); treeTimer = setTimeout(renderTree, 120); }

function renderTree() {
  const g = $("#tree-g");
  g.innerHTML = "";
  if (S.kind !== "focus") return;
  const P = absPos();
  const center = (id) => { const p = P[id]; return p ? [p.x * UX, p.y * UY] : null; };
  const links = sv("g"), nodes = sv("g");
  g.append(links, nodes);
  const mx = new Set();
  for (const e of S.work) {
    if (e.deleted) continue;
    const id = scalar(e, "id");
    const c = center(id);
    if (!c) continue;
    for (const pr of e.children.filter((ch) => ch.key === "prerequisite")) {
      const ids = [...pr.value.matchAll(/focus\s*=\s*([^\s}]+)/g)].map((m) => m[1]);
      for (const pid of ids) {
        const p = center(pid);
        if (!p) continue;
        const midY = c[1] - UY / 2 + 6;
        links.append(sv("path", { d: `M${p[0]},${p[1] + NH / 2} V${midY} H${c[0]} V${c[1] - NH / 2}`, class: "link" + (ids.length > 1 ? " or" : "") }));
      }
    }
    const m = child(e, "mutually_exclusive");
    if (m) {
      for (const [, oid] of m.value.matchAll(/focus\s*=\s*([^\s}]+)/g)) {
        const pair = [id, oid].sort().join("|");
        const o = center(oid);
        if (!o || mx.has(pair)) continue;
        mx.add(pair);
        links.append(sv("line", { x1: c[0], y1: c[1], x2: o[0], y2: o[1], class: "link mx" }));
      }
    }
  }
  for (const e of S.work) {
    if (e.deleted) continue;
    const id = scalar(e, "id");
    const c = center(id);
    if (!c) continue;
    const node = sv("g", { class: "fnode" + (e === S.sel ? " sel" : "") + (isChanged(e) ? " changed" : ""), transform: `translate(${c[0] - NW / 2},${c[1] - NH / 2})` });
    node.append(sv("rect", { width: NW, height: NH }));
    const name = title(e) || id;
    const lines = wrap(name, 11);
    lines.slice(0, 2).forEach((l, n) => { const t = sv("text", { x: NW / 2, y: 17 + n * 13, "text-anchor": "middle" }); t.textContent = l; node.append(t); });
    const t = sv("text", { x: NW / 2, y: NH - 6, "text-anchor": "middle", class: "id" });
    t.textContent = id.length > 22 ? id.slice(0, 21) + "…" : id;
    node.append(t);
    const tip = sv("title"); tip.textContent = `${name}\n${id}`; node.append(tip);
    node.addEventListener("pointerdown", (ev) => startDrag(ev, e, node, c));
    nodes.append(node);
  }
  applyView();
}

function wrap(s, n) {
  const out = [];
  let cur = "";
  for (const w of s.split(/\s+/)) {
    if ((cur + " " + w).trim().length > n && cur) { out.push(cur); cur = w; }
    else cur = (cur + " " + w).trim();
  }
  if (cur) out.push(cur);
  if (out.length > 2) out[1] = out[1].slice(0, n - 1) + "…";
  return out;
}

function applyView() { $("#tree-g").setAttribute("transform", `translate(${S.view.x},${S.view.y}) scale(${S.view.k})`); }

function fitTree() {
  const P = Object.values(absPos()).filter(Boolean);
  const svg = $("#tree");
  if (!P.length || !svg.clientWidth) return;
  const xs = P.map((p) => p.x * UX), ys = P.map((p) => p.y * UY);
  const minX = Math.min(...xs) - NW, maxX = Math.max(...xs) + NW, minY = Math.min(...ys) - NH, maxY = Math.max(...ys) + NH;
  const k = Math.min(1.2, Math.max(0.12, Math.min(svg.clientWidth / (maxX - minX), (svg.clientHeight - 110) / (maxY - minY))));
  S.view = { k, x: (svg.clientWidth - (maxX - minX) * k) / 2 - minX * k, y: 90 - minY * k };
  applyView();
}

function setupTree() {
  const svg = $("#tree");
  let pan = null;
  svg.addEventListener("pointerdown", (e) => {
    if (e.target.closest(".fnode")) return;
    pan = { x: e.clientX, y: e.clientY, vx: S.view.x, vy: S.view.y };
    svg.classList.add("panning");
    svg.setPointerCapture(e.pointerId);
  });
  svg.addEventListener("pointermove", (e) => {
    if (!pan) return;
    S.view.x = pan.vx + e.clientX - pan.x;
    S.view.y = pan.vy + e.clientY - pan.y;
    applyView();
  });
  const end = () => { pan = null; svg.classList.remove("panning"); };
  svg.addEventListener("pointerup", end);
  svg.addEventListener("pointercancel", end);
  svg.addEventListener("wheel", (e) => {
    e.preventDefault();
    const r = svg.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    const k2 = Math.min(2.5, Math.max(0.08, S.view.k * (e.deltaY < 0 ? 1.12 : 1 / 1.12)));
    S.view.x = mx - (mx - S.view.x) * (k2 / S.view.k);
    S.view.y = my - (my - S.view.y) * (k2 / S.view.k);
    S.view.k = k2;
    applyView();
  }, { passive: false });
}

function startDrag(ev, ent, node, c) {
  ev.stopPropagation();
  const sx = ev.clientX, sy = ev.clientY;
  let dx = 0, dy = 0, moved = false;
  node.setPointerCapture(ev.pointerId);
  const move = (e) => {
    const gx = Math.round((e.clientX - sx) / (UX * S.view.k)), gy = Math.round((e.clientY - sy) / (UY * S.view.k));
    if (Math.abs(e.clientX - sx) + Math.abs(e.clientY - sy) > 4) moved = true;
    if (gx !== dx || gy !== dy) {
      dx = gx; dy = gy;
      node.setAttribute("transform", `translate(${c[0] + dx * UX - NW / 2},${c[1] + dy * UY - NH / 2})`);
    }
  };
  const up = () => {
    node.removeEventListener("pointermove", move);
    node.removeEventListener("pointerup", up);
    if (moved && (dx || dy)) {
      setScalar(ent, "x", String((parseFloat(scalar(ent, "x")) || 0) + dx));
      setScalar(ent, "y", String((parseFloat(scalar(ent, "y")) || 0) + dy));
      S.sel = ent;
      renderList(); renderEditor(); renderTree();
    } else if (!moved) select(ent);
    else renderTree();
  };
  node.addEventListener("pointermove", move);
  node.addEventListener("pointerup", up);
}

// ------------------------------------------------------------------ 사전·검사

function openDocs() {
  const d = $("#drawer");
  d.classList.remove("hidden", "wide");
  $("#drawer-title").textContent = "효과·조건·모디파이어 사전";
  const body = $("#drawer-body");
  body.innerHTML = "";
  if (!S.game) { body.append(el("p", {}, "HOI4 설치 폴더를 찾지 못했습니다. 환경변수 TU_HOI4_DIR 에 게임 폴더를 넣고 편집기를 다시 켜 주세요.")); return; }
  const kind = el("select", {}, el("option", { value: "effects" }, "효과 (effect)"), el("option", { value: "triggers" }, "조건 (trigger)"), el("option", { value: "modifiers" }, "모디파이어"));
  const q = el("input", { type: "search", placeholder: "이름 검색 (예: add_political)" });
  const res = el("div");
  const run = async () => {
    const hits = await api(`/api/docs?kind=${kind.value}&q=${encodeURIComponent(q.value.trim())}`);
    res.innerHTML = "";
    if (!hits.length) res.append(el("p", { class: "sub" }, "결과 없음"));
    for (const h of hits) {
      res.append(el("div", { class: "doc" },
        el("div", { class: "name", title: "클릭하면 마지막으로 고르던 입력칸에 넣습니다", onclick: () => insertText(h.name) }, h.name),
        el("pre", {}, h.body)));
    }
  };
  let t = null;
  q.addEventListener("input", () => { clearTimeout(t); t = setTimeout(run, 180); });
  kind.addEventListener("change", run);
  body.append(el("div", { class: "row" }, kind, q), el("p", { class: "sub" }, "이름을 누르면 편집 중인 칸의 커서 자리에 들어갑니다."), res);
  q.focus();
  run();
}

function insertText(s) {
  const t = S.lastTA;
  if (!t || !document.body.contains(t)) { navigator.clipboard?.writeText(s); toast("복사했습니다: " + s); return; }
  const a = t.selectionStart ?? t.value.length, b = t.selectionEnd ?? a;
  t.value = t.value.slice(0, a) + s + t.value.slice(b);
  t.selectionStart = t.selectionEnd = a + s.length;
  t.dispatchEvent(new Event("input"));
  t.focus();
}

async function runCheck() {
  const d = $("#drawer");
  d.classList.remove("hidden", "wide");
  $("#drawer-title").textContent = "검사 (tu_lint, check_refs)";
  const body = $("#drawer-body");
  body.innerHTML = "";
  body.append(el("p", { class: "sub" }, "검사 중… (30초쯤 걸릴 수 있습니다)"));
  try {
    const r = await api("/api/check", {});
    body.innerHTML = "";
    body.append(el("pre", { class: "out" }, r.output));
  } catch (e) { body.innerHTML = ""; body.append(el("pre", { class: "out" }, e.message)); }
}

// ------------------------------------------------------------------ GitHub (받기·커밋·업로드)

const G = { st: null, out: "", diffPath: null, diff: "", busy: false, msg: "", target: null, newBranch: "", picked: new Set(), known: new Set(), pr: null };
const isMain = (b) => b === "main" || b === "master";

function today() {
  const d = new Date();
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
}

async function openGit(fetchRemote) {
  $("#drawer").classList.remove("hidden");
  $("#drawer").classList.add("wide");
  $("#drawer-title").textContent = "GitHub";
  if (!G.st) renderGit("불러오는 중…");
  try {
    G.st = await api("/api/git/status" + (fetchRemote ? "?fetch=1" : ""));
    // 새로 보이는 파일은 골라 두고, 사용자가 뺀 파일은 계속 뺀 채로 둔다
    const paths = G.st.files.map((f) => f.path);
    G.picked = new Set(paths.filter((p) => G.picked.has(p) || !G.known.has(p)));
    G.known = new Set(paths);
    if (!G.target) G.target = isMain(G.st.branch) ? "new" : "current";
    if (!G.newBranch) G.newBranch = `editor/${(G.st.user || "me").replace(/[^A-Za-z0-9_-]/g, "") || "me"}-${today()}`;
    if (G.st.note) G.out = G.st.note;
  } catch (e) { G.out = e.message; }
  renderGit();
}

async function gitDo(label, fn, { needClean = false, reload = false } = {}) {
  if (G.busy) return;
  if (needClean && anyDirty()) { toast("편집기에 저장하지 않은 내용이 있습니다. 먼저 저장해 주세요.", "err"); return; }
  G.busy = true; G.out = label + " 중… (로그인 창이 뜨면 로그인해 주세요)"; renderGit();
  try {
    G.out = await fn();
    toast(label + " 완료", "ok");
  } catch (e) { G.out = e.message; toast(label + " 실패", "err"); }
  G.busy = false;
  if (reload && S.kind) { try { await switchKind(S.kind, S.file?.path); } catch { /* 파일이 없어졌을 수 있음 */ } }
  await openGit(false);
}

function renderGit(loading) {
  const body = $("#drawer-body");
  body.innerHTML = "";
  const st = G.st;
  if (!st) { body.append(el("p", { class: "sub" }, loading || G.out || "")); return; }
  const dis = G.busy || undefined;

  // 브랜치·동기화
  const sel = el("select", { disabled: dis, onchange: (e) => {
    const b = e.target.value;
    gitDo(`'${b}' 브랜치로 바꾸기`, async () => (await api("/api/git/switch", { branch: b })).output || `${b} 로 바꿈`, { needClean: true, reload: true });
  } }, st.branches.map((b) => el("option", { value: b, selected: b === st.branch || undefined }, b)));
  let sync = "GitHub 브랜치와 아직 연결 안 됨 (처음 업로드하면 연결됩니다)";
  if (st.upstream) {
    sync = st.ahead || st.behind
      ? [st.ahead ? `올릴 커밋 ${st.ahead}개` : "", st.behind ? `받을 커밋 ${st.behind}개` : ""].filter(Boolean).join(" · ")
      : "GitHub 와 같은 상태";
  }
  body.append(
    el("div", { class: "git-row" }, el("span", { class: "sub" }, "브랜치"), sel,
      el("button", { class: "small", disabled: dis, title: "GitHub 의 새 커밋을 확인", onclick: () => openGit(true) }, "새로 확인"),
      el("button", { class: "small", disabled: dis, onclick: () => gitDo("최신 받기", async () => (await api("/api/git/pull", {})).output, { needClean: true, reload: true }) }, "최신 받기")),
    el("p", { class: "sub" }, `${sync}${st.user ? " · 커밋 이름: " + st.user : ""}`));

  // 바뀐 파일
  body.append(el("h3", {}, `바뀐 파일 (${st.files.length})`));
  if (!st.files.length) body.append(el("p", { class: "sub" }, "커밋할 변경이 없습니다."));
  else {
    const all = el("input", { type: "checkbox", checked: G.picked.size === st.files.length || undefined, onchange: (e) => {
      G.picked = new Set(e.target.checked ? st.files.map((f) => f.path) : []); renderGit();
    } });
    body.append(el("label", { class: "git-file all" }, all, "모두 고르기"));
    const list = el("div", { class: "git-files" });
    for (const f of st.files) {
      const cb = el("input", { type: "checkbox", checked: G.picked.has(f.path) || undefined, onchange: (e) => {
        if (e.target.checked) G.picked.add(f.path); else G.picked.delete(f.path);
      } });
      list.append(el("div", { class: "git-file" + (G.diffPath === f.path ? " on" : "") }, cb,
        el("span", { class: "chip" }, f.label),
        el("span", { class: "path", title: "누르면 바뀐 내용을 봅니다", onclick: async () => {
          if (G.diffPath === f.path) { G.diffPath = null; renderGit(); return; }
          G.diffPath = f.path; G.diff = "불러오는 중…"; renderGit();
          try { G.diff = (await api("/api/git/diff?path=" + encodeURIComponent(f.path))).diff; } catch (e) { G.diff = e.message; }
          renderGit();
        } }, f.path)));
      if (G.diffPath === f.path) list.append(diffView(G.diff));
    }
    body.append(list);
  }

  // 커밋·업로드
  const msg = el("textarea", { class: "text", rows: 3, placeholder: "무엇을 바꿨는지 한 줄로 (예: 카즈델 중점 위치 정리)", oninput: (e) => { G.msg = e.target.value; } });
  msg.value = G.msg;
  const radio = (v, text) => el("label", { class: "git-radio" },
    el("input", { type: "radio", name: "git-target", checked: G.target === v || undefined, onchange: () => { G.target = v; renderGit(); } }), text);
  const nb = el("input", { type: "text", value: G.newBranch, disabled: G.target !== "new" || undefined, oninput: (e) => { G.newBranch = e.target.value.trim(); } });
  body.append(el("h3", {}, "커밋하고 올리기"), field("커밋 메시지", msg),
    el("div", { class: "field" },
      radio("new", "새 브랜치로 올리기" + (isMain(st.branch) ? " (추천: GitHub 에서 PR 로 합칩니다)" : "")), nb,
      radio("current", `지금 브랜치(${st.branch})에 바로 올리기`)));

  const doCommit = async () => {
    if (!G.picked.size) throw new Error("커밋할 파일을 고르세요.");
    if (!G.msg.trim()) throw new Error("커밋 메시지를 적어 주세요.");
    let out = "";
    if (G.target === "new" && G.newBranch !== st.branch) {
      if (!G.newBranch) throw new Error("새 브랜치 이름을 적어 주세요.");
      out += ((await api("/api/git/switch", { branch: G.newBranch, create: true })).output || "") + "\n";
      G.target = "current";
    }
    out += (await api("/api/git/commit", { paths: [...G.picked], message: G.msg })).output;
    G.msg = "";
    return out.trim();
  };
  const doPush = async () => {
    const r = await api("/api/git/push", {});
    G.pr = r.pr;
    return r.output + (r.pr ? "\n\nPR 만들기: " + r.pr : "");
  };
  const needFiles = () => { if (!st.files.length) { toast("커밋할 변경이 없습니다.", "err"); return false; } return true; };
  body.append(el("div", { class: "actions" },
    el("button", { class: "primary", disabled: dis, onclick: () => needFiles() && gitDo("커밋하고 업로드", async () => (await doCommit()) + "\n\n" + (await doPush()), { needClean: true }) }, "커밋하고 업로드"),
    el("button", { disabled: dis, onclick: () => needFiles() && gitDo("커밋", doCommit, { needClean: true }) }, "커밋만"),
    el("button", { disabled: dis, onclick: () => gitDo("업로드", doPush) }, "업로드만"),
    G.pr ? el("button", { onclick: () => window.open(G.pr, "_blank") }, "PR 만들기 (GitHub 열기)") : null));
  body.append(el("p", { class: "sub" }, "처음 업로드할 때 GitHub 로그인 창이 뜹니다. 한 번 로그인하면 다음부터는 바로 올라갑니다."));

  if (G.out) body.append(el("pre", { class: "out git-out" }, G.out));

  body.append(el("h3", {}, "최근 커밋"));
  for (const c of st.commits) {
    body.append(el("div", { class: "git-commit" }, el("code", {}, c.hash), " ", c.subject, el("span", { class: "sub" }, ` — ${c.author}, ${c.when}`)));
  }
  if (st.web) body.append(el("p", {}, el("a", { href: st.web, target: "_blank" }, st.web)));
}

function diffView(text) {
  const pre = el("pre", { class: "diff" });
  for (const line of text.split("\n")) {
    const c = line.startsWith("+") && !line.startsWith("+++") ? "add"
      : line.startsWith("-") && !line.startsWith("---") ? "del"
      : line.startsWith("@@") ? "hunk" : "";
    pre.append(el("span", { class: c }, line + "\n"));
  }
  return pre;
}

init().catch((e) => toast("시작 실패: " + e.message, "err"));
