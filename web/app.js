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
let CANTON = null;         // chosen canton code, null = the bank's build default
let PERMIT = null;         // chosen permit code (DE block exams), null = first listed
let POOL = "national";     // chosen question pool: "national" | "core"
let state = null;          // current run

const T = (key, vars) => t(LANG, key, vars);

/* --- Practice learning aids (recall-first, diagnostics, spacing, confidence) --
 * Everything here is client-side and offline: the toggles and the per-question
 * history live in localStorage. EXAM MODE IS UNTOUCHED — these only shape the
 * free-practice experience, so the timed mock keeps mirroring the real test. */
let PRACTICE = { recallFirst: false, confidence: false, spaced: false };
let HISTORY = {};          // qid -> {box, seen, ok, ko, last, hc}

function loadPractice() {
  try { PRACTICE = Object.assign(PRACTICE, JSON.parse(localStorage.getItem("practice") || "{}")); }
  catch (e) { /* keep defaults */ }
}
function togglePractice(key) {
  PRACTICE[key] = !PRACTICE[key];
  try { localStorage.setItem("practice", JSON.stringify(PRACTICE)); } catch (e) {}
  renderStudySettings();
}

function loadHistory() {
  try { HISTORY = JSON.parse(localStorage.getItem("history") || "{}") || {}; }
  catch (e) { HISTORY = {}; }
}
function saveHistory() {
  try { localStorage.setItem("history", JSON.stringify(HISTORY)); } catch (e) {}
}

/* Leitner schedule: a card sits in a box whose interval (days) grows as it's
 * answered right; a wrong answer drops it back to box 0 (daily). box index ->
 * days until due. */
const LEITNER_DAYS = [0, 1, 3, 7, 16, 35];
const DAY_MS = 86400000;

/* Fold one answered question into the history. `sure` flags a *confident* answer:
 * a confident-but-wrong card becomes a "leech" (hc) and jumps the review queue —
 * those are the dangerous-on-the-water errors and they stick once corrected. */
function recordResult(qid, correct, sure) {
  const h = HISTORY[qid] || { box: 0, seen: 0, ok: 0, ko: 0, last: 0, hc: false };
  h.seen++;
  if (correct) { h.ok++; h.box = Math.min(h.box + 1, LEITNER_DAYS.length - 1); h.hc = false; }
  else { h.ko++; h.box = 0; if (sure) h.hc = true; }
  h.last = Date.now();
  HISTORY[qid] = h;
}

/* Review urgency for spaced ordering. Higher = sooner. New cards sit mid-pack
 * (learn new material, but resurface confident errors first); not-yet-due cards
 * sink below new ones. */
function dueScore(q) {
  const h = HISTORY[q.id];
  if (!h || !h.seen) return 100;                       // never seen
  const overdueDays = (Date.now() - (h.last + LEITNER_DAYS[h.box] * DAY_MS)) / DAY_MS;
  let s = overdueDays >= 0 ? 200 + overdueDays : -50 + overdueDays;  // due rank above new
  if (h.hc) s += 1000;                                 // confident-wrong leech: first
  else if (h.box === 0 && h.ko) s += 60;               // recently wrong
  return s;
}

/* Spaced + interleaved practice order: rank the whole pool by urgency, then round-
 * robin across themes so consecutive questions rarely share a theme (interleaving
 * sharpens the signal discrimination this domain lives on). */
function drawSpaced(questions) {
  const ranked = questions.slice().sort((a, b) => dueScore(b) - dueScore(a));
  const byTheme = {};
  for (const q of ranked) (byTheme[q.theme] ||= []).push(q);   // preserves urgency order
  const themes = Object.keys(byTheme);
  const out = [];
  let progress = true;
  while (out.length < ranked.length && progress) {
    progress = false;
    for (const tk of themes) {
      if (byTheme[tk].length) { out.push(byTheme[tk].shift()); progress = true; }
    }
  }
  return out;
}

/* How many practice questions are due right now (drives the start-screen hint). */
function dueCount(questions) {
  let n = 0;
  for (const q of questions) if (dueScore(q) >= 100) n++;
  return n;
}

/* Country/option-specific chrome (title, subtitle, banners…) can override the
 * built-in Swiss UI strings via the bank meta (ui_* keys), so one shared player
 * serves Switzerland and France. Falls back to the i18n table when absent. */
const S = (metaKey, i18nKey, vars) => {
  const v = META && META[metaKey];
  if (v == null || v === "") return T(i18nKey, vars);
  let s = String(v);
  if (vars) for (const k in vars) s = s.replaceAll("{" + k + "}", vars[k]);
  return s;
};

/* Languages to offer: the manifest's `supported` list when present (so France
 * shows only FR/EN), else all four. */
function supportedLangs() {
  const s = (MANIFEST.supported || []).filter((l) => LANGS.includes(l));
  return s.length ? s : LANGS;
}

/* Try the requested language's bank, then the French canonical files. Returns
 * the parsed payload and records whether we fell back. */
async function loadDoc(paths) {
  // Return the first non-empty bank document among `paths`, or null.
  for (const url of paths) {
    if (!url) continue;
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (!r.ok) continue;
      const data = await r.json();
      if ((data.questions || []).length === 0) continue;
      return data;
    } catch (e) { /* try next */ }
  }
  return null;
}

async function fetchBank(lang) {
  // National pool: the per-language bank (falling back to FR/canonical). Common-core
  // pool: the harmonised, portable subset — composed from the per-base bundles
  // (universal seamanship + CEVNI inland + COLREGS maritime) the manifest lists,
  // each falling back through its own FR copy. Falls through to the national bank
  // if no core build is present, so the player always works.
  const national = lang === DEFAULT_LANG
    ? ["questions.fr.json", "questions.json"]
    : [`questions.${lang}.json`, "questions.fr.json", "questions.json"];

  if (POOL === "core") {
    const core = MANIFEST.core || {};
    // The harmonised core is track-specific: an inland permit studies universal +
    // CEVNI, a sea permit universal + COLREGS — never mix the two traffic codes.
    const wantBase = activeTrack() === "maritime" ? "colregs" : "cevni";
    const bases = Object.keys(core).filter((b) => b === "universal" || b === wantBase);
    const docs = [];
    for (const base of bases) {
      const entry = core[base] || {};
      const here = entry[lang] && entry[lang].path;
      const fr = entry[DEFAULT_LANG] && entry[DEFAULT_LANG].path;
      const doc = await loadDoc(lang === DEFAULT_LANG ? [here || fr] : [here, fr]);
      if (doc) docs.push(doc);
    }
    if (docs.length) {
      const seen = new Set();
      const merged = [];
      for (const d of docs) for (const q of (d.questions || [])) {
        if (!seen.has(q.id)) { seen.add(q.id); merged.push(q); }
      }
      // Language fallback is independent of the pool: we wanted `lang` but a base
      // bundle may have reported another language.
      FELL_BACK = lang !== DEFAULT_LANG && (docs[0].meta || {}).lang !== lang;
      return { meta: Object.assign({}, docs[0].meta || {}, { pool: "core" }),
               questions: merged };
    }
    // no core docs loaded → fall through to the national bank below
  }

  const data = await loadDoc(national);
  if (!data) return null;
  FELL_BACK = lang !== DEFAULT_LANG && (data.meta || {}).lang !== lang;
  return data;
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
    cantonCode: META.canton_code || (MANIFEST.canton_default || ""),
  };
  return true;
}

/* Build the language switcher; clicking re-loads content + re-renders. */
function renderLangbar() {
  $("langbar").innerHTML = supportedLangs().map((l) =>
    `<button class="langbtn ${l === LANG ? "on" : ""}" data-lang="${l}"
       aria-pressed="${l === LANG}">${LANG_NAMES[l]}</button>`).join("");
  $("langbar").querySelectorAll(".langbtn").forEach((b) => {
    b.onclick = () => setLang(b.dataset.lang);
  });
}

async function setLang(lang) {
  LANG = supportedLangs().includes(lang) ? lang : DEFAULT_LANG;
  try { localStorage.setItem("lang", LANG); } catch (e) { /* private mode */ }
  document.documentElement.lang = LANG;
  renderLangbar();
  await loadContent();                 // META (incl. ui_* chrome) ready after this
  document.title = S("ui_title", "pageTitle");
  applyStaticStrings();
  restoreDomains();
  restoreCanton();
  restorePermit();
  renderStart();
  show("start");
}

/* Fill the non-question UI chrome. Country/option-specific bits (title, subtitle,
 * banner, source note) come from the bank meta via S() when present, else i18n. */
function applyStaticStrings() {
  $("t-h1").textContent = S("ui_h1", "h1");
  $("t-subtitle").textContent = S("ui_subtitle", "subtitle");
  $("loop-proof").innerHTML = S("ui_demo", "demoBanner");
  $("btn-exam").textContent = T("btnExam");
  $("btn-practice").textContent = T("btnPractice");
  $("t-sourcenote").textContent = S("ui_sourcenote", "sourceNote");
  $("t-resulttitle").textContent = T("resultTitle");
  $("btn-restart").textContent = T("btnRestart");
  $("t-correction").textContent = T("detailedCorrection");
  $("t-foottagline").textContent = T("footTagline");
}

/* Study-only themes (e.g. CH `voile`): shown as a study domain for permits that
 * include them, but kept out of exam-mode draws (they aren't on the theory exam). */
function extensionThemes() {
  return new Set(Array.isArray(MANIFEST.extension_themes) ? MANIFEST.extension_themes : []);
}

/* The active permit's theme set, or null when permits don't scope themes (the DE
 * blocks permits and the no-permit France/INT players). cat-A → 6 core themes
 * (voile hidden); cat-D → +voile. */
function permitThemeSet() {
  const p = currentPermit();
  return p && Array.isArray(p.themes) ? new Set(p.themes) : null;
}

/* Themes present in the loaded bank, in the canonical exam order, with counts.
 * When the active permit scopes themes, the bank is narrowed to that set — so
 * cat-A never offers `voile` while cat-D does. */
function domainsPresent() {
  const order = Object.keys(THEME_LABELS[DEFAULT_LANG]);
  const scope = permitThemeSet();
  const count = {};
  for (const q of BANK) {
    if (scope && !scope.has(q.theme)) continue;
    count[q.theme] = (count[q.theme] || 0) + 1;
  }
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
  const ext = extensionThemes();
  const all = sel.size === dom.length;
  $("t-domains").textContent = T("chooseDomains");
  // "Select all" appears only while a subset is active (an empty set is forbidden,
  // so there's no meaningful "deselect all" state). A study-only theme (e.g. voile)
  // is flagged with a ✦ + tooltip: it's practice content, not part of the exam draw.
  box.innerHTML = dom.map((d) => {
    const on = sel.has(d.theme);
    const study = ext.has(d.theme);
    return `<button class="chip ${on ? "on" : ""}" data-theme="${d.theme}"
      aria-pressed="${on}"${study ? ` title="${escapeHtml(T("studyOnly"))}"` : ""}>${escapeHtml(themeLabel(LANG, d.theme))}${study ? " ✦" : ""}
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

/* Practice-learning toggles, built in JS and inserted into the start screen so no
 * per-country index.html needs to change. Each toggle persists in localStorage
 * and only affects free practice (labelled as such). */
function renderStudySettings() {
  let box = $("study-settings");
  if (!box) {
    const start = $("screen-start");
    const anchor = start.querySelector(".actions");
    if (!start || !anchor) return;
    box = document.createElement("div");
    box.id = "study-settings";
    box.className = "domains-block study-settings";
    start.insertBefore(box, anchor);
  }
  const opt = (key, label, hint) =>
    `<button class="toggle ${PRACTICE[key] ? "on" : ""}" data-key="${key}"
      aria-pressed="${PRACTICE[key]}" title="${escapeHtml(hint)}">
      <span class="tsw"></span>${escapeHtml(label)}</button>`;
  box.innerHTML =
    `<span class="domains-label">${escapeHtml(T("studySettings"))}</span>
     <div class="domains">
       ${opt("recallFirst", T("optRecall"), T("optRecallHint"))}
       ${opt("confidence", T("optConfidence"), T("optConfidenceHint"))}
       ${opt("spaced", T("optSpaced"), T("optSpacedHint"))}
     </div>
     <p class="fine">${escapeHtml(T("practiceOnly"))}</p>`;
  box.querySelectorAll(".toggle").forEach((b) => {
    b.onclick = () => togglePractice(b.dataset.key);
  });
}

/* --- Per-canton variance ----------------------------------------------------
 * The exam is intercantonally standardised (VKS): only the time limit varies by
 * canton. The build stamps a default; here the learner can pick their canton so
 * the timer matches. The list comes from the manifest (src/cantons.py). */
function cantonList() {
  return Array.isArray(MANIFEST.cantons) ? MANIFEST.cantons : [];
}

/* The effective canton: the user's pick, else the bank's build default, else the
 * manifest default. Returns the canton record, or null if no table is present. */
function currentCanton() {
  const list = cantonList();
  if (!list.length) return null;
  const want = CANTON || CFG.cantonCode || MANIFEST.canton_default;
  return list.find((c) => c.code === want) || list[0];
}

function examMinutes() {
  if (blocksMode()) {                       // German SBF: time is per permit
    const p = currentPermit();
    return (p && +p.time_limit_min) || CFG.timeLimitMin;
  }
  const c = currentCanton();
  return (c && +c.time_limit_min) || CFG.timeLimitMin;
}

function cantonLabel() {
  const c = currentCanton();
  return c ? `${c.name} (${c.code})` : CFG.canton;
}

function restoreCanton() {
  try {
    const saved = localStorage.getItem("canton");
    CANTON = saved && cantonList().some((c) => c.code === saved) ? saved : null;
  } catch (e) { CANTON = null; }
}

function selectCanton(code) {
  CANTON = code;
  try { localStorage.setItem("canton", code); } catch (e) { /* private mode */ }
  renderStart();
}

/* Single-select chips. Hidden when the manifest carries no canton table or only
 * one canton (nothing to choose). */
function renderCantons() {
  const box = $("cantons");
  if (!box) return;
  const list = cantonList();
  if (list.length <= 1) { box.innerHTML = ""; $("t-canton").textContent = ""; return; }
  const active = currentCanton();
  $("t-canton").textContent = T("chooseCanton");
  box.innerHTML = list.map((c) => {
    const on = active && c.code === active.code;
    return `<button class="chip ${on ? "on" : ""}" data-canton="${c.code}"
      aria-pressed="${on}" title="${escapeHtml(c.note || "")}">${escapeHtml(c.name)}
      <span class="chipn">${c.time_limit_min}′</span></button>`;
  }).join("");
  box.querySelectorAll(".chip").forEach((b) => {
    b.onclick = () => selectCanton(b.dataset.canton);
  });
}

/* --- Permit picker + block exams (German SBF) -------------------------------
 * Switzerland scores on points (all_or_nothing); Germany's SBF exam is
 * block-structured: a permit fixes the composition (e.g. 7 Basisfragen + 23
 * Spezifisch) and each block has its own pass minimum. The permit list + block
 * rules come from the manifest (run.py emits them from countries/de.py); when
 * present this picker reuses the canton slot, since a blocks-mode bank ships no
 * cantons. `MANIFEST.permits[i] = {code,label,questions,time_limit_min,
 * blocks:[{block,count,min_correct}], pass_total?}`. */
function permitList() {
  return Array.isArray(MANIFEST.permits) ? MANIFEST.permits : [];
}

/* Blocks mode is on only when the bank says so AND a permit table is present. */
function blocksMode() {
  return CFG.scoring === "blocks" && permitList().length > 0;
}

function currentPermit() {
  const list = permitList();
  if (!list.length) return null;
  return list.find((p) => p.code === PERMIT) || list[0];
}

/* The navigation track of the active permit: "maritime" (sea → COLREGS core) or
 * "inland" (→ CEVNI core). With no permit table the bundle may pin a
 * `default_track` in its manifest (the INT/COLREG player sets "maritime"); absent
 * that it falls back to inland (e.g. the Swiss player), keeping the core inland. */
function activeTrack() {
  const p = currentPermit();
  if (p) return p.track === "maritime" ? "maritime" : "inland";
  return MANIFEST.default_track === "maritime" ? "maritime" : "inland";
}

function restorePermit() {
  try {
    const saved = localStorage.getItem("permit");
    PERMIT = saved && permitList().some((p) => p.code === saved) ? saved : null;
  } catch (e) { PERMIT = null; }
}

function selectPermit(code) {
  PERMIT = code;
  try { localStorage.setItem("permit", code); } catch (e) { /* private mode */ }
  renderStart();
}

/* Single-select permit chips, rendered into the canton slot. */
function renderPermits() {
  const box = $("cantons");
  if (!box) return;
  const list = permitList();
  const active = currentPermit();
  $("t-canton").textContent = T("choosePermit");
  box.innerHTML = list.map((p) => {
    const on = active && p.code === active.code;
    const spec = (p.blocks || []).map((b) => b.count).reduce((a, b) => a + b, 0);
    return `<button class="chip ${on ? "on" : ""}" data-permit="${p.code}"
      aria-pressed="${on}">${escapeHtml(p.label)}
      <span class="chipn">${spec}</span></button>`;
  }).join("");
  box.querySelectorAll(".chip").forEach((b) => {
    b.onclick = () => selectPermit(b.dataset.permit);
  });
}

/* CH-style permit picker (point-scored banks). Distinct from renderPermits above,
 * which is the German blocks picker reusing the canton slot: Switzerland runs ONE
 * theory paper for every recreational category, so this picker lives in its OWN
 * slot alongside the canton picker and is informational — choosing cat-A vs cat-D
 * changes the named category + its threshold note, not the question pool (the two
 * pools coincide until the cat-D `voile` study theme is sourced). Labels/notes are
 * localised by code (i18n `permit_<code>` / `permitNote_<code>`), falling back to
 * the manifest's FR string when a key is absent. */
function permitLabel(p) {
  const k = "permit_" + p.code, s = T(k);
  return s === k ? (p.label || p.code) : s;
}
function permitNote(p) {
  const k = "permitNote_" + p.code, s = T(k);
  return s === k ? (p.note || "") : s;
}
function renderPermitPicker() {
  const box = $("permits"), label = $("t-permit"), noteEl = $("permit-note");
  if (!box) return;
  const list = permitList();
  // Blocks banks (DE) render permits into the canton slot; this slot stays empty.
  if (blocksMode() || list.length <= 1) {
    box.innerHTML = "";
    if (label) label.textContent = "";
    if (noteEl) noteEl.textContent = "";
    return;
  }
  const active = currentPermit();
  if (label) label.textContent = T("choosePermit");
  box.innerHTML = list.map((p) => {
    const on = active && p.code === active.code;
    return `<button class="chip ${on ? "on" : ""}" data-permit="${p.code}"
      aria-pressed="${on}" title="${escapeHtml(permitNote(p))}">${escapeHtml(permitLabel(p))}</button>`;
  }).join("");
  box.querySelectorAll(".chip").forEach((b) => {
    b.onclick = () => selectPermit(b.dataset.permit);
  });
  if (noteEl) noteEl.textContent = active ? permitNote(active) : "";
}

/* --- Question pool (national bank vs harmonised common core) ----------------
 * The common core is the cross-country/cross-track portable subset: universal
 * seamanship + the harmonised traffic code(s) (CEVNI inland, COLREGS at sea). The
 * national bank adds country-specific law. The build ships the core split by base
 * (questions.<base>.<lang>.json) and lists the bases in the manifest; the toggle
 * composes the available bases into one core pool. */
function poolAvailable() {
  return Object.keys((MANIFEST.core) || {}).length > 0;
}

function restorePool() {
  try {
    const saved = localStorage.getItem("pool");
    POOL = saved === "core" && poolAvailable() ? "core" : "national";
  } catch (e) { POOL = "national"; }
}

async function selectPool(p) {
  const want = p === "core" && poolAvailable() ? "core" : "national";
  if (want === POOL) return;
  POOL = want;
  try { localStorage.setItem("pool", POOL); } catch (e) { /* private mode */ }
  await loadContent();          // a different bundle: reload, then re-render
  restoreDomains();             // the themes present differ between pools
  renderStart();
  show("start");
}

/* Two chips (National ⟷ Common core). Hidden when no core bundle was built. */
function renderPools() {
  const box = $("pools");
  if (!box) return;
  const label = $("t-pool");
  if (!poolAvailable()) { box.innerHTML = ""; if (label) label.textContent = ""; return; }
  if (label) label.textContent = T("poolLabel");
  const opts = [["national", T("poolNational")], ["core", T("poolCore")]];
  box.innerHTML = opts.map(([code, name]) => {
    const on = POOL === code;
    return `<button class="chip ${on ? "on" : ""}" data-pool="${code}"
      aria-pressed="${on}" title="${escapeHtml(T("poolHint"))}">${escapeHtml(name)}</button>`;
  }).join("");
  box.querySelectorAll(".chip").forEach((b) => {
    b.onclick = () => selectPool(b.dataset.pool);
  });
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

  renderPools();
  renderDomains();
  if (blocksMode()) renderPermits(); else renderCantons();
  renderPermitPicker();                 // CH: own slot, no-op for DE/FR/INT
  renderStudySettings();                // practice-learning toggles
  renderAnki();

  const avail = bankForRun().length;          // questions in the chosen domains
  if (blocksMode()) {
    $("config-summary").innerHTML = blockConfigHtml(avail);
  } else {
    const examN = Math.min(CFG.questions, avail);
    const partial = examN < CFG.questions
      ? " " + T("cfgPartial", { target: CFG.questions }) : "";
    $("config-summary").innerHTML = `
      <div><b>${T("cfgQuestions")}</b> ${examN}${partial}</div>
      <div><b>${T("cfgDuration")}</b> ${examMinutes()} ${T("minUnit")}</div>
      <div><b>${T("cfgSuccess")}</b> ${CFG.passPoints}/${CFG.totalPoints} ${T("points")}</div>
      <div><b>${T("cfgScale")}</b> ${T("ptsPerQuestion", { n: CFG.pointsPer })} · ${escapeHtml(cantonLabel())}</div>
      <div><b>${T("cfgAvailable")}</b> ${T("availableQuestions", { n: avail })}</div>
      ${PRACTICE.spaced ? `<div><b>${T("cfgDue")}</b> ${T("dueQuestions", { n: dueCount(bankForRun()) })}</div>` : ""}`;
  }
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
  document.addEventListener("keydown", onKeydown);
  loadPractice();
  loadHistory();
  await loadManifest();
  restorePool();                        // POOL must be set before loadContent reads it
  // Clamp to a language this build actually offers (France ships only FR/EN).
  if (!supportedLangs().includes(LANG)) {
    LANG = supportedLangs().includes(MANIFEST.default) ? MANIFEST.default : supportedLangs()[0];
  }
  renderLangbar();
  await loadContent();
  document.title = S("ui_title", "pageTitle");
  applyStaticStrings();
  restoreDomains();
  restoreCanton();
  restorePermit();
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

/* German SBF exam draw: take each block's `count` random questions, so the paper
 * has the real composition (e.g. 7 Basisfragen + 23 Spezifisch). Spans all blocks
 * regardless of the practice domain filter — an exam is a full sitting. */
function drawByBlocks(permit) {
  const out = [];
  for (const b of (permit.blocks || [])) {
    const pool = shuffle(BANK.filter((q) => q.block === b.block));
    out.push(...pool.slice(0, b.count));
  }
  return shuffle(out);
}

function startRun(mode) {
  let questions;
  if (mode === "exam" && blocksMode()) {
    questions = drawByBlocks(currentPermit());
  } else {
    let pool = bankForRun();
    // An exam mirrors the official theory paper, which excludes study-only themes
    // (CH cat-D `voile` is practical prep, not theory) — drop them from the draw.
    if (mode === "exam") {
      const ext = extensionThemes();
      if (ext.size) pool = pool.filter((q) => !ext.has(q.theme));
    }
    const n = Math.min(CFG.questions, pool.length);
    questions = mode === "practice"
      ? (PRACTICE.spaced ? drawSpaced(pool.slice()) : shuffle(pool.slice()))
      : drawBalanced(pool.slice(), n);
  }
  state = {
    mode, questions, i: 0,
    answers: {},               // id -> array of selected indices
    committed: {},             // id -> true once options revealed (recall-first)
    confidence: {},            // id -> "sure" | "unsure" (confidence capture)
    revealed: false,
    startedAt: Date.now(),
    deadline: mode === "exam" ? Date.now() + examMinutes() * 60000 : null,
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

  // Recall-first (practice): keep the options veiled until the learner commits,
  // turning recognition into active recall (the generation effect). Confidence
  // capture rides alongside, feeding the hypercorrection queue.
  const practiceMode = state.mode === "practice";
  const gated = practiceMode && PRACTICE.recallFirst && !state.committed[q.id];
  const showConf = practiceMode && PRACTICE.confidence;

  $("question").innerHTML = `${fig}
    <div class="stem">${escapeHtml(q.stem)}</div>
    ${gated ? `<div class="recall-gate"><p>${escapeHtml(T("recallPrompt"))}</p>
      <textarea id="recall-jot" rows="2" placeholder="${escapeHtml(T("recallJot"))}"></textarea></div>` : ""}
    <div class="hint">${escapeHtml(S("ui_multihint", "multiHint"))} ${escapeHtml(T("kbdHint"))}</div>
    <div id="choices" class="${gated ? "veiled" : ""}">${choices}</div>
    ${showConf ? confidenceHtml(q) : ""}
    <div id="explain-slot"></div>`;

  state.revealed = false;
  $("question").querySelectorAll(".choice").forEach((el) => {
    el.querySelector("input").onchange = (ev) =>
      applySelection(q, +el.dataset.idx, ev.target.checked);
  });
  if (showConf) wireConfidence(q);

  const last = state.i === total - 1;
  if (gated) {
    setAction(T("recallReveal"));
  } else if (practiceMode) {
    setAction(T("btnValidate"));
  } else {
    setAction(last ? T("btnFinish") : T("btnNext"));
  }
}

/* Confidence picker (practice): a quick "sure / not sure" before validating.
 * Confident-but-wrong answers are flagged as leeches and resurface first. */
function confidenceHtml(q) {
  const c = state.confidence[q.id];
  const btn = (v, lbl) =>
    `<button type="button" class="conf ${c === v ? "on" : ""}" data-conf="${v}"
       aria-pressed="${c === v}">${escapeHtml(lbl)}</button>`;
  return `<div class="confidence"><span class="conf-q">${escapeHtml(T("confAsk"))}</span>
    ${btn("sure", T("confSure"))}${btn("unsure", T("confUnsure"))}</div>`;
}
function wireConfidence(q) {
  $("question").querySelectorAll(".conf").forEach((b) => {
    b.onclick = () => {
      if (state.revealed) return;
      state.confidence[q.id] = b.dataset.conf;
      $("question").querySelectorAll(".conf").forEach((x) => {
        const on = x.dataset.conf === b.dataset.conf;
        x.classList.toggle("on", on); x.setAttribute("aria-pressed", on);
      });
    };
  });
}

/* Reveal the options the learner committed to (recall-first), without scoring. */
function commitRecall(q) {
  state.committed[q.id] = true;
  const ch = $("choices");
  if (ch) ch.classList.remove("veiled");
  const gate = $("question").querySelector(".recall-gate");
  if (gate) gate.classList.add("done");
  setAction(T("btnValidate"));
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
  // No toggling while the options are still veiled behind the recall gate.
  if (state.mode === "practice" && PRACTICE.recallFirst && !state.committed[q.id]) return;
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
  // Recall-first: the first action reveals the options, not the answer.
  if (state.mode === "practice" && PRACTICE.recallFirst && !state.committed[q.id]) {
    commitRecall(q);
    return;
  }
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
  annotateChoices(q, sel, correct);
  $("question").querySelectorAll(".conf").forEach((b) => (b.disabled = true));
  // Learn from this answer: a confident-but-wrong pick becomes a leech (hc).
  recordResult(q.id, scoreQuestion(q) > 0, state.confidence[q.id] === "sure");
  saveHistory();
  $("explain-slot").innerHTML = diagnosticHtml(q, sel, correct) + explainHtml(q);
}

/* Diagnostic distractor feedback: attach each choice's authored rationale (why
 * that option is what it is) under the correct answer and any option the learner
 * picked. Figures ship a sourced pointer per distractor; prose may be empty, in
 * which case the chosen-vs-correct contrast below still teaches the difference. */
function annotateChoices(q, sel, correct) {
  $("question").querySelectorAll(".choice").forEach((el) => {
    const idx = +el.dataset.idx;
    const c = q.choices[idx] || {};
    const isC = correct.has(idx), picked = sel.has(idx);
    if (c.rationale && (isC || picked)) {
      const d = document.createElement("div");
      d.className = "choice-why " + (isC ? "ok" : "no");
      d.textContent = c.rationale;
      el.appendChild(d);
    }
  });
}

/* The "you chose X, the answer is Y" contrast — the highest-value, zero-data part
 * of diagnostic feedback. Only shown when the learner missed it. */
function diagnosticHtml(q, sel, correct) {
  if (!correct.size) return "";
  const wrong = [...sel].filter((i) => !correct.has(i));
  const missed = [...correct].filter((i) => !sel.has(i));
  if (!wrong.length && !missed.length) return "";          // fully correct
  const txt = (i) => "« " + escapeHtml((q.choices[i] || {}).text || T("figureTag")) + " »";
  const yours = wrong.length
    ? `<div><b>${escapeHtml(T("diagYouChose"))}</b> ${wrong.map(txt).join(", ")}</div>` : "";
  const good = `<div><b>${escapeHtml(T("diagCorrect"))}</b> ${[...correct].map(txt).join(", ")}</div>`;
  return `<div class="diag">${yours}${good}</div>`;
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
  if (blocksMode()) return finishBlocks();
  // Practice records each answer at reveal; an exam reveals nothing, so fold its
  // results into the spaced-repetition history here (confidence unknown → not hc).
  if (state.mode === "exam") {
    for (const q of state.questions) recordResult(q.id, scoreQuestion(q) > 0, false);
    saveHistory();
  }
  let earned = 0, total = 0;
  for (const q of state.questions) { earned += scoreQuestion(q); total += (q.points || CFG.pointsPer); }
  // The pass mark is the configured threshold for a full sitting, but scaled to
  // the points actually on the paper when fewer questions are available (a
  // domain-filtered practice, or a bank still smaller than the exam size — e.g.
  // France's growing seed). Otherwise a partial bank could never reach the
  // absolute threshold and would always "fail".
  const passMark = total >= CFG.totalPoints
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

/* German block label, e.g. "basis" -> "Basisfragen". Falls back to the id. */
function blockLabel(id) {
  const s = T("blk_" + id);
  return s === "blk_" + id ? id : s;
}

/* Start-screen config summary for a block exam: the permit, its composition and
 * the per-block pass minima (the real SBF rule), plus the timer. */
function blockConfigHtml(avail) {
  const p = currentPermit();
  const blocks = p.blocks || [];
  const total = blocks.reduce((a, b) => a + b.count, 0);
  const minima = blocks
    .map((b) => `${blockLabel(b.block)} ≥${b.min_correct}/${b.count}`).join(" · ");
  return `
    <div><b>${T("cfgPermit")}</b> ${escapeHtml(p.label)}</div>
    <div><b>${T("cfgQuestions")}</b> ${total}</div>
    <div><b>${T("cfgDuration")}</b> ${examMinutes()} ${T("minUnit")}</div>
    <div><b>${T("cfgSuccess")}</b> ${escapeHtml(minima)}</div>
    <div><b>${T("cfgAvailable")}</b> ${T("availableQuestions", { n: avail })}</div>`;
}

/* Block-based grading (mirrors src/questions/schema.grade_exam_blocks): count
 * exact-match correct per block; an exam passes iff every block clears its
 * minimum. Practice runs (no fixed composition) just show correct/total + the
 * by-domain breakdown, with no pass verdict. */
function finishBlocks() {
  const permit = currentPermit();
  const byBlock = {};
  let correct = 0;
  for (const q of state.questions) {
    const ok = scoreQuestion(q) > 0;
    const b = (byBlock[q.block] ||= { ok: 0, n: 0 });
    b.n++; if (ok) { b.ok++; correct++; }
    if (state.mode === "exam") recordResult(q.id, ok, false);  // practice records at reveal
  }
  if (state.mode === "exam") saveHistory();
  const mins = Math.round((Date.now() - state.startedAt) / 60000);

  let badge = "", rows = "";
  if (state.mode === "exam" && permit) {
    let passed = true;
    rows = (permit.blocks || []).map((bl) => {
      const got = (byBlock[bl.block] || { ok: 0 }).ok;
      const ok = got >= bl.min_correct;
      passed = passed && ok;
      return `<div class="scoreline">${escapeHtml(blockLabel(bl.block))}:
        <b>${got}/${bl.count}</b> ${T("blkMin", { n: bl.min_correct })} ${ok ? "✓" : "✗"}</div>`;
    }).join("");
    badge = `<div class="badge ${passed ? "pass" : "fail"}">${passed ? T("passed") : T("failed")}</div>`;
  }

  $("score").innerHTML = `${badge}
    <div class="scoreline">${T("scoreLineCount", { correct: `<b>${correct}</b>`, total: state.questions.length })}</div>
    ${rows}
    <div class="scoreline">${escapeHtml(T("duration"))} ${mins} ${T("minUnit")}</div>`;
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
    const picked = sel.has(idx);
    const cls = isC ? "c" : (picked ? "x" : "");
    const tag = isC ? " ✓" : (picked ? " ✗ " + T("yourChoice") : "");
    const why = c.rationale && (isC || picked)
      ? `<div class="choice-why ${isC ? "ok" : "no"}">${escapeHtml(c.rationale)}</div>` : "";
    return `<li class="${cls}">${escapeHtml(c.text || T("figureTag"))}${tag}${why}</li>`;
  }).join("");
  const h = HISTORY[q.id];
  const hc = h && h.hc ? `<div class="hc-flag">${escapeHtml(T("hcError"))}</div>` : "";
  return `<div class="review-item">
    <span class="mark ${ok ? "ok" : "no"}">${ok ? "✓" : "✗"}</span>
    <div class="q">${n + 1}. ${escapeHtml(q.stem)}</div>
    <ul>${opts}</ul>${hc}${explainHtml(q)}</div>`;
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
