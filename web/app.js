"use strict";
/* Static quiz player for the boat-permit question bank.
 * No dependencies. Loads the per-language bank (questions.<lang>.json, falling
 * back to French) plus the exam config from its meta, runs a chronometered mock
 * exam or a free-practice mode, scores point-based (all-or-nothing per question,
 * mirroring src/questions/schema.score), and shows a source-cited correction.
 * Figures render in a fixed-size box (style.css) so resolution/crop can't leak
 * the answer. UI strings + theme labels come from i18n.js. */

const $ = (id) => document.getElementById(id);
const screens = ["start", "quiz", "results"];
function show(name) {
  screens.forEach((s) => $("screen-" + s).classList.toggle("hidden", s !== name));
}

let LANG = DEFAULT_LANG;   // active UI language (from i18n.js)
let BANK = [];             // all questions for the active content language
let CFG = {};              // exam config from meta
let META = {};             // raw meta of the loaded bank
let MANIFEST = {};         // languages.json (per-language counts + Anki downloads)
let FELL_BACK = false;     // true when UI lang has no native bank (showing FR)
let UNOFFICIAL = false;    // true when the loaded bank is an unofficial translation
let SELECTED = null;       // Set of chosen domain (theme) ids, null = all present
let state = null;          // current run

const T = (key, vars) => t(LANG, key, vars);

/* Try the requested language's bank, then the French canonical files. Returns
 * the parsed payload and records whether we fell back. */
async function fetchBank(lang) {
  const candidates = lang === DEFAULT_LANG
    ? ["questions.fr.json", "questions.json"]
    : [`questions.${lang}.json`, "questions.fr.json", "questions.json"];
  for (const url of candidates) {
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (!r.ok) continue;
      const data = await r.json();
      if ((data.questions || []).length === 0) continue;
      FELL_BACK = url === "questions.json" || url === "questions.fr.json"
        ? lang !== DEFAULT_LANG && (data.meta || {}).lang !== lang
        : false;
      return data;
    } catch (e) { /* try next */ }
  }
  return null;
}

/* The build manifest (languages.json) carries per-language Anki download links.
 * Optional: the player still works if it's missing (downloads just hide). */
async function loadManifest() {
  try {
    const r = await fetch("languages.json", { cache: "no-store" });
    if (r.ok) MANIFEST = await r.json();
  } catch (e) { MANIFEST = {}; }
}

async function loadContent() {
  FELL_BACK = false; UNOFFICIAL = false;
  const data = await fetchBank(LANG);
  if (!data) { BANK = []; META = {}; return false; }
  BANK = data.questions || [];
  META = data.meta || {};
  UNOFFICIAL = String(META.unofficial || "") === "true" || META.unofficial === true;
  CFG = {
    questions: +META.exam_questions || 60,
    totalPoints: +META.total_points || 180,
    pointsPer: +META.points_per_question || 3,
    passPoints: +META.pass_points || 165,
    timeLimitMin: +META.time_limit_min || 50,
    scoring: META.scoring || "all_or_nothing",
    canton: META.canton || "VD/Léman",
  };
  return true;
}

/* Build the language switcher; clicking re-loads content + re-renders. */
function renderLangbar() {
  $("langbar").innerHTML = LANGS.map((l) =>
    `<button class="langbtn ${l === LANG ? "on" : ""}" data-lang="${l}"
       aria-pressed="${l === LANG}">${LANG_NAMES[l]}</button>`).join("");
  $("langbar").querySelectorAll(".langbtn").forEach((b) => {
    b.onclick = () => setLang(b.dataset.lang);
  });
}

async function setLang(lang) {
  LANG = LANGS.includes(lang) ? lang : DEFAULT_LANG;
  try { localStorage.setItem("lang", LANG); } catch (e) { /* private mode */ }
  document.documentElement.lang = LANG;
  document.title = T("pageTitle");
  renderLangbar();
  applyStaticStrings();
  await loadContent();
  restoreDomains();
  renderStart();
  show("start");
}

/* Fill the non-question UI chrome from the translation table. */
function applyStaticStrings() {
  $("t-h1").textContent = T("h1");
  $("t-subtitle").textContent = T("subtitle");
  $("loop-proof").innerHTML = T("demoBanner");
  $("btn-exam").textContent = T("btnExam");
  $("btn-practice").textContent = T("btnPractice");
  $("t-sourcenote").textContent = T("sourceNote");
  $("t-resulttitle").textContent = T("resultTitle");
  $("btn-restart").textContent = T("btnRestart");
  $("t-correction").textContent = T("detailedCorrection");
  $("t-foottagline").textContent = T("footTagline");
}

/* Themes present in the loaded bank, in the canonical exam order, with counts. */
function domainsPresent() {
  const order = Object.keys(THEME_LABELS[DEFAULT_LANG]);
  const count = {};
  for (const q of BANK) count[q.theme] = (count[q.theme] || 0) + 1;
  const present = Object.keys(count);
  present.sort((a, b) => order.indexOf(a) - order.indexOf(b));
  return present.map((t) => ({ theme: t, n: count[t] }));
}

/* The active domain filter: the chosen set, or every present domain by default. */
function activeDomains() {
  const present = domainsPresent().map((d) => d.theme);
  if (!SELECTED) return present;
  const chosen = present.filter((t) => SELECTED.has(t));
  return chosen.length ? chosen : present;
}

function bankForRun() {
  const dom = new Set(activeDomains());
  return BANK.filter((q) => dom.has(q.theme));
}

function toggleDomain(theme) {
  const present = domainsPresent().map((d) => d.theme);
  if (!SELECTED) SELECTED = new Set(present);        // first click: start from all
  SELECTED.has(theme) ? SELECTED.delete(theme) : SELECTED.add(theme);
  if (SELECTED.size === 0) SELECTED.add(theme);      // never allow an empty set
  try { localStorage.setItem("domains", JSON.stringify([...SELECTED])); } catch (e) {}
  renderStart();
}

/* Restore a saved domain selection, dropping any theme absent from this bank. */
function restoreDomains() {
  try {
    const saved = JSON.parse(localStorage.getItem("domains") || "null");
    if (Array.isArray(saved)) {
      const present = new Set(domainsPresent().map((d) => d.theme));
      const keep = saved.filter((t) => present.has(t));
      SELECTED = keep.length ? new Set(keep) : null;
    }
  } catch (e) { SELECTED = null; }
}

function renderDomains() {
  const box = $("domains");
  if (!box) return;
  const dom = domainsPresent();
  if (dom.length <= 1) { box.innerHTML = ""; return; }   // nothing to choose
  const sel = new Set(activeDomains());
  const all = sel.size === dom.length;
  $("t-domains").textContent = T("chooseDomains");
  // "Select all" appears only while a subset is active (an empty set is forbidden,
  // so there's no meaningful "deselect all" state).
  box.innerHTML = dom.map((d) => {
    const on = sel.has(d.theme);
    return `<button class="chip ${on ? "on" : ""}" data-theme="${d.theme}"
      aria-pressed="${on}">${escapeHtml(themeLabel(LANG, d.theme))}
      <span class="chipn">${d.n}</span></button>`;
  }).join("") +
    (all ? "" : `<button class="chip allbtn" data-all="1">${T("domainAll")}</button>`);
  box.querySelectorAll(".chip").forEach((b) => {
    b.onclick = () => {
      if (b.dataset.all) {
        SELECTED = null;                         // null = every present domain
        try { localStorage.removeItem("domains"); } catch (e) {}
        renderStart();
      } else { toggleDomain(b.dataset.theme); }
    };
  });
}

/* Offline-study downloads for this language: the prebuilt Anki deck (+ editable
 * TSV) and the Moodle GIFT file. Hidden entirely if the manifest has neither. */
function renderAnki() {
  const box = $("anki-dl");
  if (!box) return;
  const a = (MANIFEST.anki || {})[LANG];
  const g = (MANIFEST.gift || {})[LANG];
  if (!a && !g) { box.classList.add("hidden"); box.innerHTML = ""; return; }
  box.classList.remove("hidden");
  const anki = a
    ? `<a class="dlbtn" href="${a.apkg}" download>${T("ankiApkg", { n: a.count })}</a>
       <a class="dlbtn ghost" href="${a.tsv}" download>${T("ankiTsv")}</a>` : "";
  const gift = g
    ? `<a class="dlbtn ghost" href="${g.gift}" download>${T("giftBtn")}</a>` : "";
  box.innerHTML = `<span class="anki-label">${T("ankiTitle")}</span>
    ${anki}${gift}
    <span class="fine">${T("ankiHint")}</span>`;
}

function renderStart() {
  const note = $("fallback-note");
  if (UNOFFICIAL) {
    note.innerHTML = T("unofficialBanner");
    note.classList.remove("hidden");
  } else if (FELL_BACK) {
    note.innerHTML = T("fallbackBanner", { lang: LANG_NAMES[LANG] });
    note.classList.remove("hidden");
  } else {
    note.classList.add("hidden");
  }

  if (BANK.length === 0) {
    $("config-summary").innerHTML = T("loadError");
    $("btn-exam").disabled = $("btn-practice").disabled = true;
    return;
  }
  $("btn-exam").disabled = $("btn-practice").disabled = false;

  renderDomains();
  renderAnki();

  const avail = bankForRun().length;          // questions in the chosen domains
  const examN = Math.min(CFG.questions, avail);
  const partial = examN < CFG.questions
    ? " " + T("cfgPartial", { target: CFG.questions }) : "";
  $("config-summary").innerHTML = `
    <div><b>${T("cfgQuestions")}</b> ${examN}${partial}</div>
    <div><b>${T("cfgDuration")}</b> ${CFG.timeLimitMin} ${T("minUnit")}</div>
    <div><b>${T("cfgSuccess")}</b> ${CFG.passPoints}/${CFG.totalPoints} ${T("points")}</div>
    <div><b>${T("cfgScale")}</b> ${T("ptsPerQuestion", { n: CFG.pointsPer })} · ${escapeHtml(CFG.canton)}</div>
    <div><b>${T("cfgAvailable")}</b> ${T("availableQuestions", { n: avail })}</div>`;
  $("meta-foot").textContent =
    `${META.generated || ""} · KB ${META.kb_version || ""} · ${T("availableQuestions", { n: BANK.length })}`;

  $("btn-exam").onclick = () => startRun("exam");
  $("btn-practice").onclick = () => startRun("practice");
  $("btn-restart").onclick = () => show("start");
  $("btn-action").onclick = onAction;
}

async function boot() {
  LANG = detectLang();
  document.documentElement.lang = LANG;
  document.title = T("pageTitle");
  document.addEventListener("keydown", onKeydown);
  renderLangbar();
  applyStaticStrings();
  await loadManifest();
  await loadContent();
  restoreDomains();
  renderStart();
  show("start");
}

/* Theme-balanced draw: round-robin across themes (shuffled within each) so the
 * exam isn't dominated by whichever theme is largest. Degenerates gracefully
 * when only one or two themes are present. */
function drawBalanced(questions, n) {
  const byTheme = {};
  for (const q of questions) (byTheme[q.theme] ||= []).push(q);
  for (const tk in byTheme) shuffle(byTheme[tk]);
  const themes = Object.keys(byTheme);
  const out = [];
  let progress = true;
  while (out.length < n && progress) {
    progress = false;
    for (const tk of themes) {
      if (byTheme[tk].length) { out.push(byTheme[tk].pop()); progress = true; }
      if (out.length >= n) break;
    }
  }
  return shuffle(out);
}

function startRun(mode) {
  const pool = bankForRun();
  const n = Math.min(CFG.questions, pool.length);
  const questions = mode === "practice" ? shuffle(pool.slice()) : drawBalanced(pool.slice(), n);
  state = {
    mode, questions, i: 0,
    answers: {},               // id -> array of selected indices
    revealed: false,
    startedAt: Date.now(),
    deadline: mode === "exam" ? Date.now() + CFG.timeLimitMin * 60000 : null,
  };
  $("timer").classList.toggle("hidden", mode !== "exam");
  if (mode === "exam") tick();
  show("quiz");
  renderQuestion();
}

function renderQuestion() {
  const q = state.questions[state.i];
  const total = state.questions.length;
  $("progress").textContent = T("progress", { i: state.i + 1, n: total }) +
    "  ·  " + themeLabel(LANG, q.theme);
  const sel = new Set(state.answers[q.id] || []);

  const fig = q.image
    ? `<div class="figure"><img src="${q.image}" alt="${escapeHtml(T("altSignal"))}"></div>` : "";
  const choices = q.choices.map((c, idx) => {
    const body = c.image
      ? `<div class="figure" style="height:120px"><img src="${c.image}" alt=""></div>`
      : escapeHtml(c.text);
    // The digit badge doubles as the keyboard shortcut hint (press 1/2/3…).
    return `<label class="choice" data-idx="${idx}">
      <span class="keyhint">${idx + 1}</span>
      <input type="checkbox" ${sel.has(idx) ? "checked" : ""}> <span>${body}</span>
    </label>`;
  }).join("");

  $("question").innerHTML = `${fig}
    <div class="stem">${escapeHtml(q.stem)}</div>
    <div class="hint">${escapeHtml(T("multiHint"))} ${escapeHtml(T("kbdHint"))}</div>
    <div id="choices">${choices}</div>
    <div id="explain-slot"></div>`;

  state.revealed = false;
  $("question").querySelectorAll(".choice").forEach((el) => {
    el.querySelector("input").onchange = (ev) =>
      applySelection(q, +el.dataset.idx, ev.target.checked);
  });

  const last = state.i === total - 1;
  if (state.mode === "practice") {
    setAction(T("btnValidate"));
  } else {
    setAction(last ? T("btnFinish") : T("btnNext"));
  }
}

/* Update the selected-index list + the checkbox for one choice. Shared by the
 * checkbox onchange and the digit-key shortcut so they can't drift. */
function applySelection(q, idx, checked) {
  const a = (state.answers[q.id] ||= []);
  const pos = a.indexOf(idx);
  if (checked && pos < 0) a.push(idx);
  if (!checked && pos >= 0) a.splice(pos, 1);
}

/* Toggle a choice by index from the keyboard (no-op once answers are revealed). */
function toggleChoice(idx) {
  if (!state || state.revealed) return;
  const q = state.questions[state.i];
  if (idx < 0 || idx >= q.choices.length) return;
  const el = $("question").querySelector(`.choice[data-idx="${idx}"]`);
  if (!el) return;
  const input = el.querySelector("input");
  input.checked = !input.checked;
  applySelection(q, idx, input.checked);
}

/* Quiz keyboard shortcuts: digit 1-9 toggles a choice, Enter validates/advances
 * (the same as clicking the action button). Inactive outside the quiz screen. */
function onKeydown(e) {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (!state || $("screen-quiz").classList.contains("hidden")) return;
  if (e.key === "Enter") {
    if (e.target && e.target.tagName === "BUTTON") return;  // let the button's own click fire
    e.preventDefault();
    onAction();
  } else if (/^[1-9]$/.test(e.key)) {
    e.preventDefault();
    toggleChoice(+e.key - 1);
  }
}

function onAction() {
  const q = state.questions[state.i];
  if (state.mode === "practice" && !state.revealed) {
    revealAnswer(q);
    state.revealed = true;
    setAction(state.i === state.questions.length - 1 ? T("btnSeeResult") : T("btnNext"));
    return;
  }
  if (state.i < state.questions.length - 1) {
    state.i++;
    renderQuestion();
  } else {
    finish();
  }
}

function revealAnswer(q) {
  const sel = new Set(state.answers[q.id] || []);
  const correct = new Set(q.correct || []);
  $("question").querySelectorAll(".choice").forEach((el) => {
    const idx = +el.dataset.idx;
    el.classList.add("locked");
    el.querySelector("input").disabled = true;
    if (correct.has(idx)) el.classList.add("correct");
    else if (sel.has(idx)) el.classList.add("wrong");
  });
  $("explain-slot").innerHTML = explainHtml(q);
}

function explainHtml(q) {
  const p = q.provenance || {};
  const asof = p.as_of ? " " + T("stateOf", { date: escapeHtml(p.as_of) }) : "";
  const src = p.url
    ? `<a href="${p.url}" target="_blank" rel="noopener">${escapeHtml(p.ref || p.source)}</a>`
    : escapeHtml(p.ref || p.source || "");
  return `<div class="explain">${escapeHtml(q.explanation || "")}
    <div class="src">${escapeHtml(T("sourceLabel"))}&nbsp;: ${src} — ${escapeHtml(p.source || "")}${asof}</div></div>`;
}

/* all-or-nothing: full points iff the selected set equals the correct set. */
function scoreQuestion(q) {
  const sel = new Set(state.answers[q.id] || []);
  const cor = new Set(q.correct || []);
  const exact = sel.size === cor.size && [...cor].every((i) => sel.has(i));
  return exact ? (q.points || CFG.pointsPer) : 0;
}

function finish() {
  let earned = 0, total = 0;
  for (const q of state.questions) { earned += scoreQuestion(q); total += (q.points || CFG.pointsPer); }
  const passMark = state.mode === "exam"
    ? CFG.passPoints
    : Math.round((CFG.passPoints / CFG.totalPoints) * total);
  const passed = earned >= passMark;
  const mins = Math.round((Date.now() - state.startedAt) / 60000);

  $("score").innerHTML = `
    <div class="badge ${passed ? "pass" : "fail"}">${passed ? T("passed") : T("failed")}</div>
    <div class="scoreline">${T("scoreLine", { earned: `<b>${earned}</b>`, total, pass: passMark })}</div>
    <div class="scoreline">${escapeHtml(T("faultPoints"))} <b>${total - earned}</b></div>
    <div class="scoreline">${escapeHtml(T("duration"))} ${mins} ${T("minUnit")}</div>
    ${state.questions.length < CFG.questions
      ? `<p class="fine">${T("partialExam", { n: state.questions.length, target: CFG.questions })}</p>` : ""}`;

  $("breakdown").innerHTML = domainBreakdownHtml();
  $("review").innerHTML = state.questions.map((q, n) => reviewItem(q, n)).join("");
  $("timer").classList.add("hidden");
  show("results");
}

/* Score per domain (theme) for the just-finished run: correct/total questions
 * plus a little bar, in the canonical theme order. Always shown, even for a
 * single-domain run, so the learner sees where they stand by topic. */
function domainBreakdownHtml() {
  const order = Object.keys(THEME_LABELS[DEFAULT_LANG]);
  const by = {};
  for (const q of state.questions) {
    const b = (by[q.theme] ||= { ok: 0, n: 0 });
    b.n++; if (scoreQuestion(q) > 0) b.ok++;
  }
  const rows = Object.keys(by)
    .sort((a, b) => order.indexOf(a) - order.indexOf(b))
    .map((t) => {
      const { ok, n } = by[t];
      const pct = Math.round((ok / n) * 100);
      return `<div class="dom-row">
        <span class="dom-name">${escapeHtml(themeLabel(LANG, t))}</span>
        <span class="dom-bar"><i style="width:${pct}%"></i></span>
        <span class="dom-score">${ok}/${n}</span></div>`;
    }).join("");
  return `<h3 class="dom-h">${T("byDomain")}</h3>${rows}`;
}

function reviewItem(q, n) {
  const sel = new Set(state.answers[q.id] || []);
  const ok = scoreQuestion(q) > 0;
  const opts = q.choices.map((c, idx) => {
    const isC = (q.correct || []).includes(idx);
    const cls = isC ? "c" : (sel.has(idx) ? "x" : "");
    const tag = isC ? " ✓" : (sel.has(idx) ? " ✗ " + T("yourChoice") : "");
    return `<li class="${cls}">${escapeHtml(c.text || T("figureTag"))}${tag}</li>`;
  }).join("");
  return `<div class="review-item">
    <span class="mark ${ok ? "ok" : "no"}">${ok ? "✓" : "✗"}</span>
    <div class="q">${n + 1}. ${escapeHtml(q.stem)}</div>
    <ul>${opts}</ul>${explainHtml(q)}</div>`;
}

function tick() {
  if (!state || state.mode !== "exam" || !state.deadline) return;
  const left = Math.max(0, state.deadline - Date.now());
  const s = Math.floor(left / 1000);
  const el = $("timer");
  el.textContent = `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  el.classList.toggle("low", s <= 300);
  if (left <= 0) { finish(); return; }
  if (!$("screen-results").classList.contains("hidden")) return;
  setTimeout(tick, 1000);
}

function setAction(label) { $("btn-action").textContent = label; }
function shuffle(a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

boot();
