"use strict";
/* Static quiz player for the boat-permit question bank.
 * No dependencies. Loads questions.json (bank + exam config from its meta),
 * runs a chronometered mock exam or a free-practice mode, scores point-based
 * (all-or-nothing per question, mirroring src/questions/schema.score), and shows
 * a source-cited correction. Figures render in a fixed-size box (style.css) so
 * resolution/crop can't leak the answer. */

const THEME_LABELS = {
  definitions: "Définitions",
  meteorologie: "Météorologie",
  lois: "Lois sur la navigation",
  signalisation: "Signalisation et signaux acoustiques",
  matelotage: "Matelotage",
  eaux_frontalieres: "Eaux frontalières",
};

const $ = (id) => document.getElementById(id);
const screens = ["start", "quiz", "results"];
function show(name) {
  screens.forEach((s) => $("screen-" + s).classList.toggle("hidden", s !== name));
}

let BANK = [];      // all questions
let CFG = {};       // exam config from meta
let state = null;   // current run

async function boot() {
  let data;
  try {
    data = await (await fetch("questions.json", { cache: "no-store" })).json();
  } catch (e) {
    $("config-summary").innerHTML =
      "<b>Impossible de charger les questions.</b> Lancez d’abord " +
      "<code>python run.py questions &amp;&amp; python run.py web</code>, puis servez le dossier.";
    return;
  }
  BANK = data.questions || [];
  const m = data.meta || {};
  CFG = {
    questions: +m.exam_questions || 60,
    totalPoints: +m.total_points || 180,
    pointsPer: +m.points_per_question || 3,
    passPoints: +m.pass_points || 165,
    timeLimitMin: +m.time_limit_min || 50,
    scoring: m.scoring || "all_or_nothing",
    canton: m.canton || "VD/Léman",
  };
  const avail = BANK.length;
  const examN = Math.min(CFG.questions, avail);
  $("config-summary").innerHTML = `
    <div><b>Questions</b> ${examN}${examN < CFG.questions ? ` (sur ${CFG.questions} visés — banque en cours de constitution)` : ""}</div>
    <div><b>Durée</b> ${CFG.timeLimitMin} min</div>
    <div><b>Réussite</b> ${CFG.passPoints}/${CFG.totalPoints} points</div>
    <div><b>Barème</b> ${CFG.pointsPer} pts/question · ${CFG.canton}</div>
    <div><b>Disponibles</b> ${avail} questions</div>`;
  $("meta-foot").textContent =
    `banque ${m.generated || ""} · KB ${m.kb_version || ""} · ${avail} questions`;

  $("btn-exam").onclick = () => startRun("exam");
  $("btn-practice").onclick = () => startRun("practice");
  $("btn-restart").onclick = () => show("start");
  $("btn-action").onclick = onAction;
  show("start");
}

/* Theme-balanced draw: round-robin across themes (shuffled within each) so the
 * exam isn't dominated by whichever theme is largest. Degenerates gracefully
 * when only one or two themes are present. */
function drawBalanced(questions, n) {
  const byTheme = {};
  for (const q of questions) (byTheme[q.theme] ||= []).push(q);
  for (const t in byTheme) shuffle(byTheme[t]);
  const themes = Object.keys(byTheme);
  const out = [];
  let progress = true;
  while (out.length < n && progress) {
    progress = false;
    for (const t of themes) {
      if (byTheme[t].length) { out.push(byTheme[t].pop()); progress = true; }
      if (out.length >= n) break;
    }
  }
  return shuffle(out);
}

function startRun(mode) {
  const n = Math.min(CFG.questions, BANK.length);
  const questions = mode === "practice" ? shuffle(BANK.slice()) : drawBalanced(BANK.slice(), n);
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
  $("progress").textContent = `Question ${state.i + 1} / ${total}` +
    `  ·  ${THEME_LABELS[q.theme] || q.theme}`;
  const sel = new Set(state.answers[q.id] || []);
  const multi = (q.correct || []).length > 1;

  const fig = q.image
    ? `<div class="figure"><img src="${q.image}" alt="signal à identifier"></div>` : "";
  const choices = q.choices.map((c, idx) => {
    const body = c.image
      ? `<div class="figure" style="height:120px"><img src="${c.image}" alt=""></div>`
      : escapeHtml(c.text);
    return `<label class="choice" data-idx="${idx}">
      <input type="checkbox" ${sel.has(idx) ? "checked" : ""}> <span>${body}</span>
    </label>`;
  }).join("");

  $("question").innerHTML = `${fig}
    <div class="stem">${escapeHtml(q.stem)}</div>
    <div class="hint">Une ou deux réponses peuvent être correctes.</div>
    <div id="choices">${choices}</div>
    <div id="explain-slot"></div>`;

  state.revealed = false;
  $("question").querySelectorAll(".choice").forEach((el) => {
    el.querySelector("input").onchange = (ev) => {
      const idx = +el.dataset.idx;
      const a = (state.answers[q.id] ||= []);
      const pos = a.indexOf(idx);
      if (ev.target.checked && pos < 0) a.push(idx);
      if (!ev.target.checked && pos >= 0) a.splice(pos, 1);
    };
  });

  const last = state.i === total - 1;
  if (state.mode === "practice") {
    setAction("Valider");
  } else {
    setAction(last ? "Terminer" : "Suivante");
  }
}

function onAction() {
  const q = state.questions[state.i];
  if (state.mode === "practice" && !state.revealed) {
    revealAnswer(q);
    state.revealed = true;
    setAction(state.i === state.questions.length - 1 ? "Voir le résultat" : "Suivante");
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
  const asof = p.as_of ? ` (état ${p.as_of})` : "";
  const src = p.url
    ? `<a href="${p.url}" target="_blank" rel="noopener">${escapeHtml(p.ref || p.source)}</a>`
    : escapeHtml(p.ref || p.source || "");
  return `<div class="explain">${escapeHtml(q.explanation || "")}
    <div class="src">Source&nbsp;: ${src} — ${escapeHtml(p.source || "")}${asof}</div></div>`;
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
    <div class="badge ${passed ? "pass" : "fail"}">${passed ? "Réussi" : "Échoué"}</div>
    <div class="scoreline"><b>${earned}</b> / ${total} points
      (seuil ${passMark})</div>
    <div class="scoreline">Points de faute&nbsp;: <b>${total - earned}</b></div>
    <div class="scoreline">Durée&nbsp;: ${mins} min</div>
    ${state.questions.length < CFG.questions
      ? `<p class="fine">Examen partiel&nbsp;: ${state.questions.length} questions
         disponibles sur ${CFG.questions}. Score indicatif.</p>` : ""}`;

  $("review").innerHTML = state.questions.map((q, n) => reviewItem(q, n)).join("");
  $("timer").classList.add("hidden");
  show("results");
}

function reviewItem(q, n) {
  const sel = new Set(state.answers[q.id] || []);
  const ok = scoreQuestion(q) > 0;
  const opts = q.choices.map((c, idx) => {
    const isC = (q.correct || []).includes(idx);
    const cls = isC ? "c" : (sel.has(idx) ? "x" : "");
    const tag = isC ? " ✓" : (sel.has(idx) ? " ✗ (votre choix)" : "");
    return `<li class="${cls}">${escapeHtml(c.text || "[figure]")}${tag}</li>`;
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
