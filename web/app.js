'use strict';

// ── Modes ────────────────────────────────────────────────────────────────
const MODE = {
  ORDER: 'order', REV: 'reverse', RANDOM: 'random',
  WRONG: 'wrong', SLOW: 'slow', STATS: 'stats', LOG: 'log',
};
const MODE_LABELS = {
  order: 'In Order', reverse: 'Reverse', random: 'Random',
  wrong: 'Most Wrong', slow: 'Slowest',
};
const CARD_MODES = new Set([MODE.ORDER, MODE.REV, MODE.RANDOM, MODE.WRONG, MODE.SLOW]);

// ── State ────────────────────────────────────────────────────────────────
const state = {
  words: {}, major: [], stats: {}, log: [],
  nums: [],            // ['00'..'99']
  mode: MODE.ORDER,
  deck: [],
  index: 0,
  flipped: false,
  inverse: false,
  sessionCorrect: 0,
  sessionWrong: 0,
  marks: {},           // index -> 'correct' | 'wrong'
  shownAt: {},         // index -> performance.now() (ms)
  elapsed: 0,          // seconds
  timerRunning: false,
  timerId: null,
  focusLostAt: null,
  imageCache: {},      // num -> dataURI | null | undefined(pending)
};

// ── DOM ──────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const el = {
  modes: $('modes'),
  inverse: $('btn-inverse'),
  major: $('btn-major'),
  card: $('card'),
  number: $('card-number'),
  word: $('card-word'),
  image: $('card-image'),
  stats: $('stats'),
  log: $('log'),
  chartWrong: $('chart-wrong'),
  chartTime: $('chart-time'),
  progress: $('progress'),
  timer: $('timer'),
  session: $('session'),
  hint: $('hint'),
  modal: $('major-modal'),
  majorRows: $('major-rows'),
  majorClose: $('major-close'),
  tooltip: $('tooltip'),
};

// ── Bootstrap ──────────────────────────────────────────────────────────────
window.addEventListener('pywebviewready', async () => {
  const data = await window.pywebview.api.bootstrap();
  state.words = data.words;
  state.major = data.major;
  state.stats = data.stats;
  state.log = data.log;
  // Build 00..99 explicitly: JS reorders integer-like object keys ('10'..'99')
  // ahead of non-canonical ones ('00'..'09'), so Object.keys() is unreliable.
  state.nums = Array.from({ length: 100 }, (_, i) => String(i).padStart(2, '0'));

  buildMajorModal();
  wireEvents();
  setMode(MODE.ORDER);
});

// ── Mode / deck ────────────────────────────────────────────────────────────
function setMode(mode) {
  state.mode = mode;
  for (const btn of el.modes.querySelectorAll('.mode-btn')) {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  }

  el.card.classList.add('hidden');
  el.stats.classList.add('hidden');
  el.log.classList.add('hidden');

  if (mode === MODE.STATS) {
    el.stats.classList.remove('hidden');
    el.stats.classList.add('flex');
    renderCharts();
    el.progress.textContent = '';
    el.timer.textContent = '';
    el.session.textContent = '';
    el.hint.textContent = 'Hover a bar for details';
  } else if (mode === MODE.LOG) {
    el.log.classList.remove('hidden');
    renderLog();
    el.progress.textContent = '';
    el.timer.textContent = '';
    el.session.textContent = '';
    el.hint.textContent = '';
  } else {
    el.card.classList.remove('hidden');
    el.card.classList.add('flex');
    state.sessionCorrect = 0;
    state.sessionWrong = 0;
    state.marks = {};
    resetTimer();
    buildDeck();
    showCard();
  }
}

function buildDeck() {
  const keys = state.nums;
  switch (state.mode) {
    case MODE.ORDER:  state.deck = keys.slice(); break;
    case MODE.REV:    state.deck = keys.slice().reverse(); break;
    case MODE.RANDOM: state.deck = shuffle(keys.slice()); break;
    case MODE.WRONG:  state.deck = keys.slice().sort((a, b) => wrongPct(b) - wrongPct(a)); break;
    case MODE.SLOW:   state.deck = keys.slice().sort((a, b) => avgTime(b) - avgTime(a)); break;
    default:          state.deck = keys.slice();
  }
  state.index = 0;
  state.flipped = false;
  state.marks = {};
  state.shownAt = {};
}

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function wrongPct(num) {
  const s = state.stats[num];
  const total = s.correct + s.wrong;
  return total ? s.wrong / total : 0;
}

function avgTime(num) {
  const s = state.stats[num];
  const tc = s.time_count || 0;
  return tc ? (s.total_time || 0) / tc : 0;
}

// ── Card display ─────────────────────────────────────────────────────────
let viewToken = 0;          // bumped on every face change; cancels stale image reveals
const imagePromises = {};   // num -> in-flight fetch promise (dedupes prefetch + reveal)

function showNumberSide(num) {
  viewToken++;
  el.number.style.fontSize = '90px';
  el.number.textContent = num;
  el.number.classList.remove('hidden');
  el.word.classList.add('hidden');
  el.image.classList.add('hidden');
}

function showWordSide(num) {
  const token = ++viewToken;
  el.number.classList.add('hidden');
  el.word.textContent = state.words[num];
  // Reveal the word and its image together: keep both hidden until the image
  // is fetched AND decoded, then show them in the same frame.
  el.word.classList.add('hidden');
  el.image.classList.add('hidden');
  loadImage(num).then((uri) => {
    if (token !== viewToken) return;   // flipped or navigated away meanwhile
    if (uri) {
      el.image.src = uri;
      el.image.classList.remove('hidden');
    } else {
      el.image.removeAttribute('src');
    }
    el.word.classList.remove('hidden');
  });
}

// Fetch (once) and pre-decode a card image. Resolves to a data URI or null.
// Pre-decoding means the bitmap is ready to paint the instant we un-hide it.
function loadImage(num) {
  if (num in state.imageCache) return Promise.resolve(state.imageCache[num]);
  if (num in imagePromises) return imagePromises[num];
  const p = window.pywebview.api.image(num)
    .then(async (uri) => {
      if (uri) {
        // If the bytes won't decode (corrupt/truncated webp), treat as no image.
        try { const im = new Image(); im.src = uri; await im.decode(); }
        catch (_) { uri = null; }
      }
      return uri;
    })
    .catch(() => null)   // bridge/backend error → no image (never leave the card blank)
    .then((uri) => {
      state.imageCache[num] = uri;
      delete imagePromises[num];
      return uri;
    });
  imagePromises[num] = p;
  return p;
}

function cardStyle(mark) {
  el.card.dataset.state = mark || 'neutral';
}

function showCard() {
  if (state.index >= state.deck.length) {
    showComplete();
    return;
  }
  const num = state.deck[state.index];
  state.flipped = false;

  // Prefetch this card's image (and the next) so flipping/navigating is instant.
  loadImage(num);
  if (state.index + 1 < state.deck.length) loadImage(state.deck[state.index + 1]);

  if (!(state.index in state.shownAt)) {
    state.shownAt[state.index] = performance.now();
  }

  cardStyle(state.marks[state.index]);

  if (state.inverse) showWordSide(num);
  else showNumberSide(num);

  el.progress.textContent = `Card ${state.index + 1} / ${state.deck.length}`;
  updateSessionLabel();
  el.hint.textContent = '← → navigate     Space = flip     Enter = ✓     Delete = ✗';
}

function flipCard() {
  if (state.index >= state.deck.length) return;
  const num = state.deck[state.index];
  state.flipped = !state.flipped;
  const showWord = state.flipped !== state.inverse; // XOR
  if (showWord) showWordSide(num);
  else showNumberSide(num);
}

function mark(result) {
  if (state.index >= state.deck.length) return;
  const idx = state.index;
  const num = state.deck[idx];
  const prev = state.marks[idx] ?? null;

  let cardTime = null;
  const shownAt = state.shownAt[idx];
  if (shownAt !== undefined && prev === null) {
    cardTime = (performance.now() - shownAt) / 1000;
  }
  delete state.shownAt[idx];

  if (prev !== result) {
    if (prev === 'correct') state.sessionCorrect--;
    else if (prev === 'wrong') state.sessionWrong--;
    if (result === 'correct') state.sessionCorrect++;
    else state.sessionWrong++;
    state.marks[idx] = result;
  }

  // Apply the same change to the in-memory stats synchronously, mirroring the
  // backend, so charts and WRONG/SLOW ordering can't read a stale snapshot.
  // (The bridge call below is async and may resolve out of order.)
  const s = state.stats[num];
  if (cardTime !== null && prev === null) {
    s.total_time = (s.total_time || 0) + Math.min(cardTime, 15.0);
    s.time_count = (s.time_count || 0) + 1;
  }
  if (prev !== result) {
    if (prev === 'correct') s.correct = Math.max(0, s.correct - 1);
    else if (prev === 'wrong') s.wrong = Math.max(0, s.wrong - 1);
    s[result] += 1;
  }

  // Persist to disk (fire-and-forget; in-memory stats are already up to date).
  window.pywebview.api.record_mark(num, result, prev, cardTime).catch(() => {});

  startTimer();
  state.index++;
  showCard();
}

function showComplete() {
  stopTimer();
  if (state.timerRunning) {
    const entry = {
      timestamp: new Date().toISOString(),
      mode: state.mode,
      inverse: state.inverse,
      correct: state.sessionCorrect,
      wrong: state.sessionWrong,
      elapsed: state.elapsed,
    };
    window.pywebview.api.finish_session(entry).then((log) => { state.log = log; });
    state.timerRunning = false;   // a re-entered Done screen must not re-log this run
  }
  cardStyle(null);
  el.number.style.fontSize = '48px';
  el.number.textContent = 'Done!';
  el.number.classList.remove('hidden');
  el.word.classList.add('hidden');
  el.image.classList.add('hidden');
  el.progress.textContent = '';
  updateSessionLabel();
  const total = state.sessionCorrect + state.sessionWrong;
  const pct = total ? Math.round((100 * state.sessionCorrect) / total) : 0;
  el.hint.textContent = `${pct}% correct this session — pick a mode to restart`;
}

function updateSessionLabel() {
  el.session.textContent = `Correct: ${state.sessionCorrect}   Wrong: ${state.sessionWrong}`;
}

// ── Navigation ─────────────────────────────────────────────────────────────
function navPrev() {
  if (state.index > 0) { state.index--; showCard(); }
}
function navNext() {
  if (state.index < state.deck.length) { state.index++; showCard(); }
}

// ── Inverse toggle ───────────────────────────────────────────────────────
function toggleInverse() {
  state.inverse = !state.inverse;
  el.inverse.classList.toggle('active', state.inverse);
  if (CARD_MODES.has(state.mode)) {
    resetTimer();
    state.sessionCorrect = 0;
    state.sessionWrong = 0;
    state.marks = {};
    buildDeck();
    showCard();
  }
}

// ── Timer ────────────────────────────────────────────────────────────────
function tick() {
  state.elapsed++;
  const m = Math.floor(state.elapsed / 60);
  const s = state.elapsed % 60;
  el.timer.textContent = `  ${m}:${String(s).padStart(2, '0')}`;
}
function startTimer() {
  if (!state.timerRunning) {
    state.timerRunning = true;
    state.timerId = setInterval(tick, 1000);
  }
}
function stopTimer() {
  if (state.timerId) clearInterval(state.timerId);
  state.timerId = null;
}
function resetTimer() {
  stopTimer();
  state.timerRunning = false;
  state.elapsed = 0;
  el.timer.textContent = '';
}

// ── Focus tracking (compensate timing for time spent away) ─────────────────
function onBlur() {
  if (state.focusLostAt === null) state.focusLostAt = performance.now();
}
function onFocus() {
  if (state.focusLostAt !== null) {
    const pause = performance.now() - state.focusLostAt;
    for (const k in state.shownAt) state.shownAt[k] += pause;
    state.focusLostAt = null;
  }
}

// ── Major System modal ─────────────────────────────────────────────────────
function buildMajorModal() {
  el.majorRows.innerHTML = state.major
    .map(([digit, sounds]) =>
      `<div class="major-row"><span class="digit">${digit}</span>` +
      `<span class="arrow">→</span><span>${sounds}</span></div>`)
    .join('');
}
function showMajor() { el.modal.classList.remove('hidden'); el.modal.classList.add('flex'); }
function hideMajor() { el.modal.classList.add('hidden'); el.modal.classList.remove('flex'); }

// ── Log view ───────────────────────────────────────────────────────────────
function renderLog() {
  if (!state.log.length) {
    el.log.innerHTML = `<p class="empty">No completed runs yet.</p>`;
    return;
  }
  const rows = state.log.slice().reverse().map((e) => {
    const dt = new Date(e.timestamp);
    const date = dt.toLocaleString('en-US', {
      month: 'short', day: '2-digit', year: 'numeric',
      hour: 'numeric', minute: '2-digit', hour12: true,
    });
    let mode = MODE_LABELS[e.mode] || e.mode;
    if (e.inverse) mode += ' (Inv)';
    const total = e.correct + e.wrong;
    const pct = total ? Math.round((100 * e.correct) / total) : 0;
    const m = Math.floor(e.elapsed / 60);
    const s = e.elapsed % 60;
    const time = `${m}:${String(s).padStart(2, '0')}`;
    const color = pct >= 80 ? 'var(--good)' : pct < 50 ? 'var(--bad)' : '#b07a1e';
    return `<tr>
      <td style="color:var(--ink-soft)">${date}</td>
      <td>${mode}</td>
      <td style="color:var(--good)">✓ ${e.correct}</td>
      <td style="color:var(--bad)">✗ ${e.wrong}</td>
      <td style="color:${color};font-weight:600">${pct}%</td>
      <td style="color:var(--ink-soft)">⏱ ${time}</td>
    </tr>`;
  }).join('');

  el.log.innerHTML = `<table>
    <thead><tr>
      <th>Date</th><th>Mode</th><th>Correct</th><th>Wrong</th><th>Score</th><th>Time</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
}

// ── Charts ───────────────────────────────────────────────────────────────
const MARGIN = { l: 44, r: 12, t: 12, b: 34 };
const CHART_COLORS = {
  grid: '#e3ddcf', label: '#a39d8e', axis: '#bdb6a6',
};

function setupCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.round(rect.width * dpr));
  canvas.height = Math.max(1, Math.round(rect.height * dpr));
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w: rect.width, h: rect.height };
}

function drawChart(canvas, { value, color, yLabel, skipZero }) {
  const { ctx, w, h } = setupCanvas(canvas);
  const cw = w - MARGIN.l - MARGIN.r;
  const ch = h - MARGIN.t - MARGIN.b;

  ctx.clearRect(0, 0, w, h);   // transparent → panel background shows through

  // Grid + Y labels
  ctx.font = "11px 'Hanken Grotesk', sans-serif";
  ctx.textBaseline = 'middle';
  for (const frac of [0, 0.25, 0.5, 0.75, 1]) {
    const y = Math.round(MARGIN.t + ch - frac * ch);
    ctx.strokeStyle = CHART_COLORS.grid;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(MARGIN.l, y + 0.5);
    ctx.lineTo(MARGIN.l + cw, y + 0.5);
    ctx.stroke();
    ctx.fillStyle = CHART_COLORS.label;
    ctx.textAlign = 'right';
    ctx.fillText(yLabel(frac), MARGIN.l - 7, y);
  }

  // Bars
  const bw = cw / 100;
  for (let i = 0; i < 100; i++) {
    const num = String(i).padStart(2, '0');
    const v = value(num);          // 0..1 of chart height
    if (skipZero && v === 0) continue;
    const bh = Math.round(v * ch);
    const x = Math.round(MARGIN.l + i * bw);
    const y = Math.round(MARGIN.t + ch - bh);
    ctx.fillStyle = color(num);
    ctx.fillRect(x + 1, y, Math.max(1, Math.round(bw) - 1), bh);
  }

  // X labels every 10
  ctx.fillStyle = CHART_COLORS.label;
  ctx.font = "10px 'Hanken Grotesk', sans-serif";
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  for (let i = 0; i < 100; i += 10) {
    const x = MARGIN.l + (i + 0.5) * bw;
    ctx.fillText(String(i).padStart(2, '0'), x, MARGIN.t + ch + 7);
  }

  // Axes
  ctx.strokeStyle = CHART_COLORS.axis;
  ctx.beginPath();
  ctx.moveTo(MARGIN.l + 0.5, MARGIN.t);
  ctx.lineTo(MARGIN.l + 0.5, MARGIN.t + ch);
  ctx.lineTo(MARGIN.l + cw, MARGIN.t + ch + 0.5);
  ctx.stroke();
}

function timeCeiling() {
  let max = 0;
  for (let i = 0; i < 100; i++) max = Math.max(max, avgTime(String(i).padStart(2, '0')));
  for (const nice of [3, 5, 8, 10, 15]) if (max <= nice) return nice;
  return Math.max(Math.floor(max) + 1, 1);
}

function renderCharts() {
  // wrong %: muted green (low) → muted red (high), matching --good/--bad
  drawChart(el.chartWrong, {
    value: (num) => wrongPct(num),
    yLabel: (frac) => `${frac * 100}%`,
    color: (num) => {
      const p = wrongPct(num);
      return `rgb(${Math.round(63 + 115 * p)}, ${Math.round(122 - 63 * p)}, ${Math.round(87 - 28 * p)})`;
    },
  });

  // response time: light slate (fast) → deep steel (slow)
  const ceiling = timeCeiling();
  drawChart(el.chartTime, {
    value: (num) => avgTime(num) / ceiling,
    yLabel: (frac) => `${Math.round(ceiling * frac)}s`,
    skipZero: true,
    color: (num) => {
      const i = Math.min(avgTime(num) / ceiling, 1);
      return `rgb(${Math.round(210 - 163 * i)}, ${Math.round(216 - 137 * i)}, ${Math.round(224 - 105 * i)})`;
    },
  });
}

function chartTooltip(canvas, ev, describe) {
  const rect = canvas.getBoundingClientRect();
  const cw = rect.width - MARGIN.l - MARGIN.r;
  const x = ev.clientX - rect.left;
  if (x < MARGIN.l || x > MARGIN.l + cw) { el.tooltip.classList.add('hidden'); return; }
  const i = Math.max(0, Math.min(99, Math.floor((x - MARGIN.l) / (cw / 100))));
  const num = String(i).padStart(2, '0');
  el.tooltip.textContent = describe(num);
  el.tooltip.style.left = `${ev.clientX + 12}px`;
  el.tooltip.style.top = `${ev.clientY + 12}px`;
  el.tooltip.classList.remove('hidden');
}

// ── Events ───────────────────────────────────────────────────────────────
function wireEvents() {
  el.modes.addEventListener('click', (e) => {
    const btn = e.target.closest('.mode-btn');
    if (btn) setMode(btn.dataset.mode);
  });
  el.inverse.addEventListener('click', toggleInverse);
  el.major.addEventListener('click', showMajor);
  el.majorClose.addEventListener('click', hideMajor);
  el.modal.addEventListener('click', (e) => { if (e.target === el.modal) hideMajor(); });

  document.addEventListener('keydown', (e) => {
    if (!el.modal.classList.contains('hidden')) {
      if (e.key === 'Escape') hideMajor();
      return;
    }
    if (!CARD_MODES.has(state.mode)) return;
    switch (e.key) {
      case ' ':         e.preventDefault(); flipCard(); break;
      case 'Enter':     e.preventDefault(); mark('correct'); break;
      case 'Delete':
      case 'Backspace': e.preventDefault(); mark('wrong'); break;
      case 'ArrowLeft':  e.preventDefault(); navPrev(); break;
      case 'ArrowRight': e.preventDefault(); navNext(); break;
    }
  });

  window.addEventListener('blur', onBlur);
  window.addEventListener('focus', onFocus);
  window.addEventListener('resize', () => { if (state.mode === MODE.STATS) renderCharts(); });

  el.chartWrong.addEventListener('mousemove', (ev) => chartTooltip(el.chartWrong, ev, (num) => {
    const s = state.stats[num];
    const total = s.correct + s.wrong;
    return `${num} ${state.words[num]}: ${Math.round(wrongPct(num) * 100)}% wrong (${s.wrong}/${total})`;
  }));
  el.chartTime.addEventListener('mousemove', (ev) => chartTooltip(el.chartTime, ev, (num) => {
    const s = state.stats[num];
    const tc = s.time_count || 0;
    return tc ? `${num} ${state.words[num]}: ${avgTime(num).toFixed(1)}s avg (${tc} timed)`
              : `${num} ${state.words[num]}: no data yet`;
  }));
  for (const c of [el.chartWrong, el.chartTime]) {
    c.addEventListener('mouseleave', () => el.tooltip.classList.add('hidden'));
  }
}
