# RAG Service How-It-Works Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `rag-service-how-it-works.html`, a standalone page documenting the RAG microservice's development history and current architecture, matching the visual design of the existing `ml-service-how-it-works.html`.

**Architecture:** Single self-contained HTML file (inline CSS + inline SVG diagrams + a small vanilla-JS theme toggle, no build step, no external dependencies), built incrementally: skeleton+hero first, then one `<section>` per pipeline stage inserted before a fixed `<footer>` anchor, then a final QA pass.

**Tech Stack:** Plain HTML5 + CSS custom properties + inline SVG. Verification uses Python 3 + BeautifulSoup4 (`bs4`, already installed, version 4.14.2 confirmed) run via one-liners — no test framework needed since there is no application logic, only markup content whose correctness means "the right facts, in the right structure."

## Global Constraints

- File lives at repo root: `C:\Users\Admin\Downloads\EAM\EAMSagemCom\rag-service-how-it-works.html` (sibling to the existing `ml-service-how-it-works.html`), per spec — standalone artifact, **not** touched into the rapport in this plan.
- Visual design must reuse `ml-service-how-it-works.html`'s CSS custom properties and component classes verbatim — no new design tokens (per spec "Visual design" section).
- Every fact (date, model name, number, config value) must trace to the spec's "Verified chronology" table or "Source of truth" file list — no invented numbers, no fabricated benchmark/accuracy figures (per spec "Out of scope").
- No full function bodies reproduced from the codebase — only the specific config values/numbers that matter (per spec "Out of scope").
- Nav links target section ids that must exist by the time the page is complete; Task 9 verifies every `href="#x"` in nav has a matching `id="x"`.

---

## File Structure

One file, built incrementally:

- `rag-service-how-it-works.html` — created in Task 1 with the full page skeleton (doctype, head, CSS, nav, hero, empty gap, `<footer>` + theme-toggle `<script>`, closing tags). Tasks 2–8 each insert one `<section>` immediately before the `<footer>` tag via a targeted edit. Task 9 does no content insertion — QA only.

No other files are created or modified.

---

### Task 1: Page skeleton, design system, hero

**Files:**
- Create: `rag-service-how-it-works.html`

**Interfaces:**
- Produces: the CSS custom properties and component classes (`.hero`, `.stat-row`/`.stat-cell`, `.section-header`/`.step-tag`, `.card`/`.card-grid`/`.card-grid-2`/`.card-grid-3`, `.model-grid`/`.model-card` (renamed conceptually but class kept for style reuse), `.flow-steps`/`.flow-step`, `.code-block`, `.callout`/`.callout.warn`/`.callout.ok`, `.truth-table`/`.truth-wrap`, `.pipeline-wrap`, `.arch-wrap`, `.dst-grid`, footer, `toggleTheme()` script) that every later task's markup relies on. Produces the `<footer>` anchor string `<footer>` that Tasks 2–8 insert before.

- [ ] **Step 1: Write the full skeleton file**

Create `rag-service-how-it-works.html` with this exact content (CSS and JS reused verbatim from `ml-service-how-it-works.html`'s design system; only the `<title>`, nav-brand suffix, nav links, hero copy/stats, footer tech line, and section-specific content differ):

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EAM RAG Service — How It Works</title>
<style>
/* ─── TOKENS ─────────────────────────────────────────── */
:root {
  --bg:        #EEF2F7;
  --surface:   #FFFFFF;
  --card:      #F6F9FC;
  --border:    #C8D5E2;
  --border2:   #D8E4EE;
  --text:      #1A2232;
  --muted:     #4E6880;
  --faint:     #8FA5B8;
  --accent:    #E09500;
  --accent-hi: #F0A500;
  --accent-lo: #C47800;
  --ok:        #16A34A;
  --warn:      #D97706;
  --crit:      #DC2626;
  --info:      #2563EB;
  --tag-bg:    #E8EFF7;
  --code-bg:   #F0F4F8;
  --mono:      'Courier New', 'Lucida Console', monospace;
  --sans:      system-ui, -apple-system, 'Segoe UI', sans-serif;
  --r:         8px;
  --r2:        14px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg:        #0B1018;
    --surface:   #131923;
    --card:      #1A2332;
    --border:    #1E3050;
    --border2:   #162540;
    --text:      #C8D8E8;
    --muted:     #5A7090;
    --faint:     #334860;
    --accent:    #F0A500;
    --accent-hi: #FFB820;
    --accent-lo: #C47800;
    --ok:        #22C55E;
    --warn:      #F59E0B;
    --crit:      #EF4444;
    --info:      #60A5FA;
    --tag-bg:    #162540;
    --code-bg:   #0E1520;
  }
}
:root[data-theme="light"] {
  --bg:#EEF2F7; --surface:#FFFFFF; --card:#F6F9FC; --border:#C8D5E2;
  --border2:#D8E4EE; --text:#1A2232; --muted:#4E6880; --faint:#8FA5B8;
  --accent:#E09500; --accent-hi:#F0A500; --accent-lo:#C47800;
  --ok:#16A34A; --warn:#D97706; --crit:#DC2626; --info:#2563EB;
  --tag-bg:#E8EFF7; --code-bg:#F0F4F8;
}
:root[data-theme="dark"] {
  --bg:#0B1018; --surface:#131923; --card:#1A2332; --border:#1E3050;
  --border2:#162540; --text:#C8D8E8; --muted:#5A7090; --faint:#334860;
  --accent:#F0A500; --accent-hi:#FFB820; --accent-lo:#C47800;
  --ok:#22C55E; --warn:#F59E0B; --crit:#EF4444; --info:#60A5FA;
  --tag-bg:#162540; --code-bg:#0E1520;
}

/* ─── RESET ──────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  font-family: var(--sans);
  background: var(--bg);
  color: var(--text);
  line-height: 1.65;
  font-size: 16px;
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}

/* ─── TYPOGRAPHY ─────────────────────────────────────── */
h1,h2,h3,h4 { text-wrap: balance; font-family: var(--mono); }
h1 { font-size: clamp(2rem, 5vw, 3.4rem); font-weight: 700; letter-spacing: -0.02em; line-height: 1.1; }
h2 { font-size: clamp(1.2rem, 3vw, 1.8rem); font-weight: 700; letter-spacing: -0.01em; line-height: 1.25; }
h3 { font-size: 1.1rem; font-weight: 700; letter-spacing: 0; }
h4 { font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); }
p { max-width: 68ch; }
a { color: var(--accent); text-decoration: none; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }

/* ─── LAYOUT SHELL ───────────────────────────────────── */
.page-wrap { max-width: 1080px; margin: 0 auto; padding: 0 24px; }
section { padding: 72px 0; }
section + section { border-top: 1px solid var(--border); }

/* ─── NAV ────────────────────────────────────────────── */
nav {
  position: sticky; top: 0; z-index: 100;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(12px);
}
.nav-inner {
  max-width: 1080px; margin: 0 auto; padding: 0 24px;
  display: flex; align-items: center; justify-content: space-between;
  height: 52px; gap: 24px;
}
.nav-brand { font-family: var(--mono); font-weight: 700; font-size: 0.85rem; color: var(--text); letter-spacing: 0.04em; }
.nav-brand span { color: var(--accent); }
.nav-links { display: flex; gap: 20px; list-style: none; }
.nav-links a { font-size: 0.78rem; color: var(--muted); letter-spacing: 0.05em; text-transform: uppercase; transition: color 0.15s; }
.nav-links a:hover { color: var(--accent); }
.theme-btn {
  background: var(--tag-bg); border: 1px solid var(--border); border-radius: 6px;
  color: var(--muted); font-size: 0.8rem; cursor: pointer; padding: 4px 10px;
  font-family: var(--mono); transition: color 0.15s, border-color 0.15s;
}
.theme-btn:hover { color: var(--accent); border-color: var(--accent); }

/* ─── HERO ───────────────────────────────────────────── */
.hero {
  padding: 80px 0 64px;
  background: var(--surface);
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute; inset: 0;
  background: repeating-linear-gradient(
    to bottom,
    transparent 0px,
    transparent 3px,
    rgba(0,0,0,0.018) 3px,
    rgba(0,0,0,0.018) 4px
  );
  pointer-events: none;
}
:root[data-theme="dark"] .hero::before,
@media (prefers-color-scheme: dark) { .hero::before {
  background: repeating-linear-gradient(
    to bottom, transparent 0px, transparent 3px,
    rgba(255,255,255,0.012) 3px, rgba(255,255,255,0.012) 4px
  );
}}
.hero-eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  font-family: var(--mono); font-size: 0.72rem; text-transform: uppercase;
  letter-spacing: 0.14em; color: var(--accent); margin-bottom: 28px;
}
.hero-eyebrow::before {
  content: ''; display: block; width: 28px; height: 1px; background: var(--accent);
}
.hero h1 { color: var(--text); margin-bottom: 24px; }
.hero h1 em { font-style: normal; color: var(--accent); }
.hero-sub {
  font-size: 1.1rem; color: var(--muted); max-width: 54ch; margin-bottom: 52px; line-height: 1.7;
}
.stat-row {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1px; background: var(--border); border: 1px solid var(--border);
  border-radius: var(--r2); overflow: hidden; max-width: 680px;
}
.stat-cell {
  background: var(--card); padding: 20px 24px;
  display: flex; flex-direction: column; gap: 4px;
}
.stat-num {
  font-family: var(--mono); font-size: 2rem; font-weight: 700;
  color: var(--accent); letter-spacing: -0.02em; line-height: 1;
  font-variant-numeric: tabular-nums;
}
.stat-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); }

/* ─── SECTION HEADER ─────────────────────────────────── */
.section-header { margin-bottom: 40px; }
.step-tag {
  display: inline-block;
  font-family: var(--mono); font-size: 0.7rem; text-transform: uppercase;
  letter-spacing: 0.12em; color: var(--accent);
  border: 1px solid var(--accent-lo); border-radius: 4px;
  padding: 3px 10px; margin-bottom: 16px;
  background: color-mix(in srgb, var(--accent) 8%, transparent);
}
.section-header h2 { margin-bottom: 12px; }
.section-header p { color: var(--muted); font-size: 1.0rem; }

/* ─── CARDS ──────────────────────────────────────────── */
.card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r2); padding: 24px; position: relative;
}
.card-grid { display: grid; gap: 16px; }
.card-grid-2 { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
.card-grid-3 { grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
.card h3 { margin-bottom: 8px; }
.card p { font-size: 0.9rem; color: var(--muted); }

/* ─── PIPELINE-STAGE CARDS (reuses ml page's .model-card styling) ──── */
.model-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.model-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r2); padding: 20px 22px;
  border-left: 3px solid var(--border);
  transition: border-color 0.2s, transform 0.15s;
}
.model-card:hover { border-left-color: var(--accent); transform: translateY(-1px); }
.model-id {
  font-family: var(--mono); font-size: 0.68rem; text-transform: uppercase;
  letter-spacing: 0.14em; color: var(--muted); margin-bottom: 6px; display: block;
}
.model-name { font-family: var(--mono); font-size: 1.0rem; font-weight: 700; color: var(--text); margin-bottom: 10px; }
.model-desc { font-size: 0.85rem; color: var(--muted); line-height: 1.55; margin-bottom: 14px; }
.model-algo {
  display: inline-block; font-family: var(--mono); font-size: 0.72rem;
  background: var(--tag-bg); border: 1px solid var(--border);
  border-radius: 4px; padding: 2px 8px; color: var(--faint);
}
.badge {
  display: inline-block; font-size: 0.68rem; font-family: var(--mono);
  text-transform: uppercase; letter-spacing: 0.08em;
  padding: 2px 8px; border-radius: 4px; font-weight: 600;
}
.badge-warn { background: color-mix(in srgb, var(--warn) 15%, transparent); color: var(--warn); }
.badge-ok   { background: color-mix(in srgb, var(--ok)   15%, transparent); color: var(--ok); }
.badge-info { background: color-mix(in srgb, var(--info)  15%, transparent); color: var(--info); }
.badge-crit { background: color-mix(in srgb, var(--crit)  15%, transparent); color: var(--crit); }

/* ─── PIPELINE DIAGRAM ───────────────────────────────── */
.pipeline-wrap { overflow-x: auto; padding: 8px 0; }
.pipeline-wrap svg { max-width: 100%; height: auto; display: block; margin: 0 auto; }

/* ─── CODE / TERMINAL ────────────────────────────────── */
.code-block {
  background: var(--code-bg); border: 1px solid var(--border);
  border-radius: var(--r); padding: 20px 24px; overflow-x: auto;
  font-family: var(--mono); font-size: 0.82rem; line-height: 1.7;
  color: var(--muted);
}
.code-block .kw  { color: var(--accent); }
.code-block .cm  { color: var(--faint); font-style: italic; }
.code-block .st  { color: var(--ok); }
.code-block .nb  { color: var(--info); }

/* ─── DST-STYLE TWO-COLUMN GRID (reused for reliability postures) ── */
.dst-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
@media (max-width: 640px) { .dst-grid { grid-template-columns: 1fr; } }

/* ─── FLOW STEPS ─────────────────────────────────────── */
.flow-steps { display: flex; flex-direction: column; gap: 0; }
.flow-step {
  display: grid; grid-template-columns: 52px 1fr; gap: 20px;
  padding: 24px 0;
  position: relative;
}
.flow-step + .flow-step { border-top: 1px solid var(--border2); }
.flow-num {
  font-family: var(--mono); font-size: 1.5rem; font-weight: 700;
  color: var(--faint); line-height: 1;
  padding-top: 4px;
}
.flow-body h3 { margin-bottom: 8px; }
.flow-body p  { font-size: 0.9rem; color: var(--muted); }

/* ─── TRUTH TABLE ────────────────────────────────────── */
.truth-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.truth-table th {
  text-align: left; padding: 10px 14px;
  font-family: var(--mono); font-size: 0.7rem; text-transform: uppercase;
  letter-spacing: 0.1em; color: var(--muted);
  border-bottom: 1px solid var(--border);
  background: var(--card);
}
.truth-table td {
  padding: 11px 14px; border-bottom: 1px solid var(--border2);
  vertical-align: middle;
}
.truth-table tr:last-child td { border-bottom: none; }
.truth-table td:first-child { font-family: var(--mono); font-weight: 700; font-size: 0.8rem; }
.truth-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: var(--r2); }

/* ─── ARCHITECTURE DIAGRAM ───────────────────────────── */
.arch-wrap { overflow-x: auto; }

/* ─── CALLOUT ────────────────────────────────────────── */
.callout {
  border: 1px solid var(--border); border-left: 3px solid var(--accent);
  background: color-mix(in srgb, var(--accent) 5%, var(--surface));
  border-radius: var(--r); padding: 18px 22px;
}
.callout.warn {
  border-left-color: var(--warn);
  background: color-mix(in srgb, var(--warn) 5%, var(--surface));
}
.callout.ok {
  border-left-color: var(--ok);
  background: color-mix(in srgb, var(--ok) 5%, var(--surface));
}
.callout h4 { color: var(--text); margin-bottom: 6px; text-transform: none; letter-spacing: 0; font-size: 0.9rem; font-weight: 700; }
.callout p  { font-size: 0.88rem; color: var(--muted); }

/* ─── FOOTER ─────────────────────────────────────────── */
footer {
  background: var(--surface); border-top: 1px solid var(--border);
  padding: 36px 24px; text-align: center;
  font-size: 0.8rem; color: var(--faint); font-family: var(--mono);
}
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <div class="nav-inner">
    <span class="nav-brand">EAM <span>//</span> RAG Service</span>
    <ul class="nav-links">
      <li><a href="#problem">Problem</a></li>
      <li><a href="#ingestion">Ingestion</a></li>
      <li><a href="#storage">Storage</a></li>
      <li><a href="#retrieval">Retrieval</a></li>
      <li><a href="#bridge">Bridge</a></li>
      <li><a href="#architecture">Architecture</a></li>
      <li><a href="#timeline">Timeline</a></li>
    </ul>
    <button class="theme-btn" onclick="toggleTheme()" aria-label="Toggle theme">◑</button>
  </div>
</nav>

<!-- HERO -->
<div class="hero" id="top">
  <div class="page-wrap">
    <div class="hero-eyebrow">Retrieval-Augmented Generation</div>
    <h1>From <em>uploaded document</em> to<br>grounded answer</h1>
    <p class="hero-sub">
      How the EAM RAG microservice ingests technical documentation, retrieves it with
      hybrid vector + keyword search, reranks it for relevance, and blends it with a
      machine's live health data before a single word reaches the chat — plus the
      real, dated history of how it got there.
    </p>
    <div class="stat-row">
      <div class="stat-cell">
        <span class="stat-num">12</span>
        <span class="stat-label">File formats ingested</span>
      </div>
      <div class="stat-cell">
        <span class="stat-num">4</span>
        <span class="stat-label">Retrieval stages</span>
      </div>
      <div class="stat-cell">
        <span class="stat-num">7</span>
        <span class="stat-label">Development phases</span>
      </div>
      <div class="stat-cell">
        <span class="stat-num">1</span>
        <span class="stat-label">Isolated microservice</span>
      </div>
    </div>
  </div>
</div>

<footer>
  <div>EAM SagemCom — RAG Service Documentation &nbsp;·&nbsp; PFE 2025–2026</div>
  <div style="margin-top:6px;opacity:0.6">FastAPI · pgvector · Postgres FTS · BGE-M3 · BGE-Reranker-v2-M3 · MinIO · Groq</div>
</footer>

<script>
function toggleTheme() {
  const root = document.documentElement;
  const current = root.getAttribute('data-theme');
  const sys = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  if (!current) {
    root.setAttribute('data-theme', sys === 'dark' ? 'light' : 'dark');
  } else if (current === 'dark') {
    root.setAttribute('data-theme', 'light');
  } else {
    root.setAttribute('data-theme', 'dark');
  }
}
</script>
</body>
</html>
```

- [ ] **Step 2: Verify the skeleton is well-formed and has the expected anchors**

Run:
```bash
python -c "
from bs4 import BeautifulSoup
html = open('rag-service-how-it-works.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')
assert soup.title.text == 'EAM RAG Service — How It Works'
assert soup.find('footer') is not None
assert soup.find('script') is not None
nav_hrefs = [a['href'].lstrip('#') for a in soup.select('.nav-links a')]
assert nav_hrefs == ['problem','ingestion','storage','retrieval','bridge','architecture','timeline'], nav_hrefs
stats = [s.text for s in soup.select('.stat-num')]
assert stats == ['12','4','7','1'], stats
print('OK skeleton valid, 7 nav links, 4 stats')
"
```
Expected output: `OK skeleton valid, 7 nav links, 4 stats`

- [ ] **Step 3: Commit**

```bash
git add rag-service-how-it-works.html
git commit -m "docs: scaffold rag-service-how-it-works.html skeleton + hero"
```

---

### Task 2: Problem section

**Files:**
- Modify: `rag-service-how-it-works.html` (insert before `<footer>`)

**Interfaces:**
- Consumes: `.page-wrap`, `.section-header`, `.step-tag`, `.card-grid-3`, `.card`, `.callout` classes from Task 1.
- Produces: `<section id="problem">` for nav to link to (already wired in Task 1's nav).

- [ ] **Step 1: Insert the Problem section**

Edit `rag-service-how-it-works.html`: replace the `<footer>` line with the section below followed by `<footer>` (i.e. insert immediately before the existing `<footer>` tag):

```html
<!-- 1. THE PROBLEM -->
<section id="problem">
  <div class="page-wrap">
    <div class="section-header">
      <div class="step-tag">Step 01 — Problem Definition</div>
      <h2>Why not just let the LLM answer from memory?</h2>
      <p>A general-purpose language model has never read Sagemcom's maintenance manuals, safety procedures, or machine data sheets. Asked a specific technical question, it will either refuse or — worse — invent a plausible-sounding but wrong answer.</p>
    </div>

    <div class="card-grid card-grid-3" style="margin-bottom:36px">
      <div class="card">
        <h4>No grounding</h4>
        <h3 style="color:var(--crit);font-family:var(--mono);font-size:1.5rem;margin-bottom:8px">Hallucinate</h3>
        <p>The model answers from its training data alone. Confident-sounding, but nothing ties the answer to this plant's actual documentation.</p>
      </div>
      <div class="card">
        <h4>Manual search only</h4>
        <h3 style="color:var(--warn);font-family:var(--mono);font-size:1.5rem;margin-bottom:8px">Ctrl+F</h3>
        <p>A technician opens a PDF and searches for keywords. Works if you know the exact term used in the manual — fails on paraphrased questions.</p>
      </div>
      <div class="card" style="border-color:var(--accent)">
        <h4>Retrieval-Augmented Generation ← our goal</h4>
        <h3 style="color:var(--accent);font-family:var(--mono);font-size:1.5rem;margin-bottom:8px">Retrieve, then generate</h3>
        <p>Find the actual relevant passages first, hand them to the LLM as context, and let it answer from real text — not memory.</p>
      </div>
    </div>

    <div class="callout">
      <h4>The core question the RAG service answers</h4>
      <p>Given a technician's question, <strong>what's the most relevant passage from real documentation, combined with what this specific machine is doing right now?</strong></p>
    </div>
  </div>
</section>

<footer>
```

- [ ] **Step 2: Verify the section was inserted correctly**

Run:
```bash
python -c "
from bs4 import BeautifulSoup
html = open('rag-service-how-it-works.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')
sec = soup.find('section', id='problem')
assert sec is not None
assert 'Why not just let the LLM answer from memory?' in sec.text
assert len(sec.select('.card-grid-3 .card')) == 3
assert soup.find('footer') is not None, 'footer must still exist after insertion'
print('OK problem section present, 3 cards, footer intact')
"
```
Expected output: `OK problem section present, 3 cards, footer intact`

- [ ] **Step 3: Commit**

```bash
git add rag-service-how-it-works.html
git commit -m "docs: add Problem section to rag-service-how-it-works.html"
```

---

### Task 3: Ingestion pipeline section

**Files:**
- Modify: `rag-service-how-it-works.html` (insert before `<footer>`)

**Interfaces:**
- Consumes: `.flow-steps`/`.flow-step`, `.callout` classes from Task 1.
- Produces: `<section id="ingestion">`.

- [ ] **Step 1: Insert the Ingestion section**

Edit `rag-service-how-it-works.html`: insert immediately before `<footer>`:

```html
<!-- 2. INGESTION PIPELINE -->
<section id="ingestion">
  <div class="page-wrap">
    <div class="section-header">
      <div class="step-tag">Step 02 — Document Ingestion</div>
      <h2>From uploaded file to searchable vectors</h2>
      <p>Every document — PDF, scanned image, Word doc, spreadsheet, or web page — goes through the same six-stage pipeline before a single question can retrieve it.</p>
    </div>

    <div class="flow-steps" style="margin-bottom:36px">
      <div class="flow-step">
        <div class="flow-num">1</div>
        <div class="flow-body">
          <h3>Format detection</h3>
          <p>12 extensions accepted: <code>.pdf .txt .png .jpg .jpeg .tiff .tif .bmp .webp .docx .xlsx .html .htm</code>. Anything else is rejected before any processing starts (max 50MB per file).</p>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-num">2</div>
        <div class="flow-body">
          <h3>Text extraction, with OCR fallback</h3>
          <p>PDFs try their native text layer first (fast, exact). Any page that yields 10 characters or fewer falls back to OCR — the page is rendered to an image at 3× zoom and read with Tesseract (French + English). Pure images and scanned PDFs go straight through OCR.</p>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-num">3</div>
        <div class="flow-body">
          <h3>Duplicate detection</h3>
          <p>A SHA-256 hash of the raw file bytes is checked against every previously ingested document <em>before</em> extraction runs. An exact repeat returns the existing document's id instead of re-processing — the API responds <code>409 Conflict</code>.</p>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-num">4</div>
        <div class="flow-body">
          <h3>Sentence-aware chunking</h3>
          <p>Text is split on sentence boundaries first, then accumulated into chunks of up to 200 words. Each new chunk keeps the last 20 words of the previous one as overlap, so an idea split across a chunk boundary isn't lost. Fragments under 20 characters are discarded.</p>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-num">5</div>
        <div class="flow-body">
          <h3>Batch embedding</h3>
          <p>Every chunk is embedded with <code>BAAI/bge-m3</code> (1024 dimensions, normalized), 32 chunks per batch, running in a thread-pool executor so it never blocks the async server.</p>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-num">6</div>
        <div class="flow-body">
          <h3>pgvector storage</h3>
          <p>Each chunk is inserted into <code>doc_chunks</code> with its embedding cast to <code>vector(1024)</code>, plus metadata (page number, filename, doc type, linked machine id) as JSON. The document's <code>chunk_count</code> is updated and the retrieval cache is invalidated.</p>
        </div>
      </div>
    </div>

    <div class="callout">
      <h4>Where this started</h4>
      <p><strong>2026-05-11</strong> — born supporting PDF and TXT only, no OCR, no dedup. <strong>2026-05-31</strong> — OCR fallback added, so scanned and image-only PDFs stopped silently producing zero chunks. <strong>2026-06-11</strong> — DOCX, XLSX, and HTML support, plus SHA-256 dedup and document versioning, arrived together.</p>
    </div>
  </div>
</section>

<footer>
```

- [ ] **Step 2: Verify**

Run:
```bash
python -c "
from bs4 import BeautifulSoup
html = open('rag-service-how-it-works.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')
sec = soup.find('section', id='ingestion')
assert sec is not None
steps = sec.select('.flow-step')
assert len(steps) == 6, len(steps)
assert 'bge-m3' in sec.text.lower()
assert '2026-05-11' in sec.text and '2026-05-31' in sec.text and '2026-06-11' in sec.text
assert soup.find('footer') is not None
print('OK ingestion section present, 6 flow steps, dates verified')
"
```
Expected output: `OK ingestion section present, 6 flow steps, dates verified`

- [ ] **Step 3: Commit**

```bash
git add rag-service-how-it-works.html
git commit -m "docs: add Ingestion pipeline section to rag-service-how-it-works.html"
```

---

### Task 4: Storage & document lifecycle section

**Files:**
- Modify: `rag-service-how-it-works.html` (insert before `<footer>`)

**Interfaces:**
- Consumes: `.card-grid-2`, `.card`, `.callout` classes from Task 1.
- Produces: `<section id="storage">`.

- [ ] **Step 1: Insert the Storage section**

Edit `rag-service-how-it-works.html`: insert immediately before `<footer>`:

```html
<!-- 3. STORAGE & DOCUMENT LIFECYCLE -->
<section id="storage">
  <div class="page-wrap">
    <div class="section-header">
      <div class="step-tag">Step 03 — Storage &amp; Document Lifecycle</div>
      <h2>Where the files themselves live</h2>
      <p>Chunks and embeddings live in Postgres, but the original files — the ones a technician might want to download and read in full — are stored separately.</p>
    </div>

    <div class="card-grid card-grid-2" style="margin-bottom:36px">
      <div class="card">
        <h4>Object storage</h4>
        <h3 style="margin-bottom:8px">MinIO — <code>rag-docs</code> bucket</h3>
        <p style="margin-bottom:16px">S3-compatible, self-hosted. Every uploaded file is stored here alongside its Postgres record. A two-way sync also picks up files dropped directly into the bucket and ingests them automatically.</p>
      </div>
      <div class="card">
        <h4>Admin document management</h4>
        <h3 style="margin-bottom:8px">Bulk import, replace, download</h3>
        <p style="margin-bottom:16px">Up to 4 files uploaded concurrently, 50 per batch. Replacing a document increments its version and re-ingests it (old chunks deleted first). Downloads use presigned URLs. Write access is ADMIN-only; Head Technicians and Technicians have read-only access.</p>
      </div>
    </div>

    <div class="callout">
      <h4>Where this started</h4>
      <p><strong>2026-05-12</strong> — the document-management page and a chat upload button shipped first, before S3 was even involved. <strong>2026-05-31</strong> — files moved into MinIO's <code>rag-docs</code> bucket, S3-backed, with two-way sync. <strong>2026-06-11</strong> — version increment on replace, so a re-uploaded document doesn't silently lose its history.</p>
    </div>
  </div>
</section>

<footer>
```

- [ ] **Step 2: Verify**

Run:
```bash
python -c "
from bs4 import BeautifulSoup
html = open('rag-service-how-it-works.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')
sec = soup.find('section', id='storage')
assert sec is not None
assert 'rag-docs' in sec.text
assert 'MinIO' in sec.text
assert '2026-05-12' in sec.text and '2026-05-31' in sec.text and '2026-06-11' in sec.text
assert soup.find('footer') is not None
print('OK storage section present, MinIO + dates verified')
"
```
Expected output: `OK storage section present, MinIO + dates verified`

- [ ] **Step 3: Commit**

```bash
git add rag-service-how-it-works.html
git commit -m "docs: add Storage and document lifecycle section to rag-service-how-it-works.html"
```

---

### Task 5: Retrieval pipeline section

**Files:**
- Modify: `rag-service-how-it-works.html` (insert before `<footer>`)

**Interfaces:**
- Consumes: `.flow-steps`/`.flow-step`, `.callout` classes from Task 1.
- Produces: `<section id="retrieval">`.

- [ ] **Step 1: Insert the Retrieval section**

Edit `rag-service-how-it-works.html`: insert immediately before `<footer>`:

```html
<!-- 4. HYBRID RETRIEVAL -->
<section id="retrieval">
  <div class="page-wrap">
    <div class="section-header">
      <div class="step-tag">Step 04 — Hybrid Retrieval</div>
      <h2>Two search engines racing, then merged</h2>
      <p>A single query triggers a meaning-based search and a keyword-based search in parallel, fuses the two ranked lists, then re-scores the survivors with a slower, more accurate model.</p>
    </div>

    <div class="flow-steps" style="margin-bottom:36px">
      <div class="flow-step">
        <div class="flow-num">1</div>
        <div class="flow-body">
          <h3>Query embedding</h3>
          <p>The question is embedded with the same <code>BAAI/bge-m3</code> model used at ingestion time. Identical questions asked twice skip recomputation via a 1-hour in-memory cache.</p>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-num">2</div>
        <div class="flow-body">
          <h3>Vector branch</h3>
          <p>Postgres computes cosine distance between the query embedding and every chunk's <code>vector(1024)</code> column via pgvector's <code>&lt;=&gt;</code> operator, gated by a similarity threshold, overfetching the top 30 candidates.</p>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-num">3</div>
        <div class="flow-body">
          <h3>Keyword branch</h3>
          <p>Postgres full-text search over two generated <code>tsvector</code> columns (French and English), ranked by <code>GREATEST(rank_fr, rank_en)</code>. This branch is deliberately <strong>fail-loud</strong>: a broken keyword index raises an error instead of silently falling back to vector-only.</p>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-num">4</div>
        <div class="flow-body">
          <h3>Reciprocal Rank Fusion</h3>
          <p>The two ranked lists are merged: each chunk's fused score is the sum of <code>1 / (60 + rank)</code> across whichever list(s) it appears in. Duplicates are collapsed by chunk id, ties broken by vector similarity, and the merged list trimmed to 30.</p>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-num">5</div>
        <div class="flow-body">
          <h3>Cross-encoder rerank</h3>
          <p><code>BAAI/bge-reranker-v2-m3</code> scores each (query, chunk) pair jointly — slower than the bi-encoder, but far more accurate, which is affordable because only the fused candidate set is scored. If the reranker itself fails, retrieval falls back gracefully to the pre-rerank fused order rather than erroring out.</p>
        </div>
      </div>
    </div>

    <div class="callout">
      <h4>Where this started</h4>
      <p><strong>2026-05-11</strong> — vector-only at birth. <strong>2026-06-06</strong> — hybrid retrieval and Reciprocal Rank Fusion added, so keyword-exact matches (part numbers, error codes) stopped losing to semantically-similar-but-wrong chunks. <strong>2026-06-12</strong> — the cross-encoder reranker arrived last, tightening the final ranking. Retrieval results themselves are cached for 5 minutes per (query, machine, top-k, threshold, hybrid-on) combination, and invalidated on every ingest or delete.</p>
    </div>
  </div>
</section>

<footer>
```

- [ ] **Step 2: Verify**

Run:
```bash
python -c "
from bs4 import BeautifulSoup
html = open('rag-service-how-it-works.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')
sec = soup.find('section', id='retrieval')
assert sec is not None
steps = sec.select('.flow-step')
assert len(steps) == 5, len(steps)
assert 'Reciprocal Rank Fusion' in sec.text
assert 'bge-reranker-v2-m3' in sec.text.lower()
assert '2026-05-11' in sec.text and '2026-06-06' in sec.text and '2026-06-12' in sec.text
assert soup.find('footer') is not None
print('OK retrieval section present, 5 flow steps, dates verified')
"
```
Expected output: `OK retrieval section present, 5 flow steps, dates verified`

- [ ] **Step 3: Commit**

```bash
git add rag-service-how-it-works.html
git commit -m "docs: add Hybrid retrieval section to rag-service-how-it-works.html"
```

---

### Task 6: Reliability-posture callout section

**Files:**
- Modify: `rag-service-how-it-works.html` (insert before `<footer>`)

**Interfaces:**
- Consumes: `.dst-grid`, `.callout.warn` classes from Task 1.
- Produces: `<section id="reliability">` (not in nav — reachable by scroll only, matches spec's "condensed to major anchors").

- [ ] **Step 1: Insert the reliability-posture section**

Edit `rag-service-how-it-works.html`: insert immediately before `<footer>`:

```html
<!-- 5. RELIABILITY POSTURES -->
<section id="reliability">
  <div class="page-wrap">
    <div class="section-header">
      <div class="step-tag">Step 05 — Two Different Reliability Postures</div>
      <h2>Fail loud here, fail soft there</h2>
      <p>The same service behaves differently depending on how close the failure is to a human who can fix it versus a human who's just trying to get an answer.</p>
    </div>

    <div class="dst-grid" style="margin-bottom:24px">
      <div class="card">
        <h4 style="color:var(--crit)">Inside the RAG service</h4>
        <h3 style="margin-bottom:8px">Fail loud</h3>
        <p>If the keyword-search branch hits a SQL error, it propagates all the way to an HTTP 500 — there is no silent fallback to vector-only results. A broken full-text index needs to be visible in logs and alerts, not quietly masked by a degraded-but-passing response.</p>
      </div>
      <div class="card">
        <h4 style="color:var(--ok)">From the chat's point of view</h4>
        <h3 style="margin-bottom:8px">Fail soft</h3>
        <p>If the whole RAG call fails, the chat bridge continues with an empty chunk list. If the ML microservice is down, the machine snapshot is simply <code>None</code>. Either way, the assistant still answers — just without that particular piece of context.</p>
      </div>
    </div>

    <div class="callout warn">
      <h4>This is not a contradiction</h4>
      <p>Fail loud applies at the layer close to the bug, where an operator can act on it. Fail soft applies at the layer close to the user, where a documentation-search outage should never take down the whole conversational assistant.</p>
    </div>
  </div>
</section>

<footer>
```

- [ ] **Step 2: Verify**

Run:
```bash
python -c "
from bs4 import BeautifulSoup
html = open('rag-service-how-it-works.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')
sec = soup.find('section', id='reliability')
assert sec is not None
assert 'Fail loud' in sec.text and 'Fail soft' in sec.text
assert len(sec.select('.dst-grid .card')) == 2
assert soup.find('footer') is not None
print('OK reliability section present, 2 posture cards')
"
```
Expected output: `OK reliability section present, 2 posture cards`

- [ ] **Step 3: Commit**

```bash
git add rag-service-how-it-works.html
git commit -m "docs: add reliability-postures section to rag-service-how-it-works.html"
```

---

### Task 7: ML-RAG bridge section

**Files:**
- Modify: `rag-service-how-it-works.html` (insert before `<footer>`)

**Interfaces:**
- Consumes: `.flow-steps`/`.flow-step`, `.callout.ok` classes from Task 1.
- Produces: `<section id="bridge">`.

- [ ] **Step 1: Insert the ML-RAG bridge section**

Edit `rag-service-how-it-works.html`: insert immediately before `<footer>`:

```html
<!-- 6. ML-RAG BRIDGE -->
<section id="bridge">
  <div class="page-wrap">
    <div class="section-header">
      <div class="step-tag">Step 06 — ML-RAG Bridge</div>
      <h2>Documentation and live machine state, merged before the LLM sees either</h2>
      <p>When a chat message is scoped to a specific machine, the backend doesn't choose between "search the docs" and "check the sensors" — it does both, at the same time.</p>
    </div>

    <div class="flow-steps" style="margin-bottom:36px">
      <div class="flow-step">
        <div class="flow-num">1</div>
        <div class="flow-body">
          <h3>Parallel fetch</h3>
          <p>RAG chunks (top 8, similarity threshold 0.30) and the machine's live ML snapshot are fetched concurrently with <code>asyncio.gather</code> — neither one waits for the other.</p>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-num">2</div>
        <div class="flow-body">
          <h3>Two separate context turns</h3>
          <p>Documentation and machine state are injected as two distinct user/assistant turn pairs, not merged into one blob — a <code>[BASE DOCUMENTAIRE]</code> turn for the retrieved passages, then a live-ML turn for the current sensor readings and health verdict.</p>
        </div>
      </div>
      <div class="flow-step">
        <div class="flow-num">3</div>
        <div class="flow-body">
          <h3>Auditable response</h3>
          <p>The chat response carries an <code>ml_context_used: bool</code> flag, so it's always possible to tell, after the fact, whether live machine data actually made it into a given answer.</p>
        </div>
      </div>
    </div>

    <div class="callout ok">
      <h4>Reused, not rebuilt</h4>
      <p>The ML snapshot is built by calling the exact same <code>get_unified_health</code> route function the frontend's ML Intelligence tab calls. One source of truth — the chat assistant and the dashboard can never disagree about a machine's health.</p>
    </div>

    <p style="margin-top:24px;font-size:0.9rem;color:var(--muted)"><strong>2026-06-12</strong> — shipped the same day as the cross-encoder reranker.</p>
  </div>
</section>

<footer>
```

- [ ] **Step 2: Verify**

Run:
```bash
python -c "
from bs4 import BeautifulSoup
html = open('rag-service-how-it-works.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')
sec = soup.find('section', id='bridge')
assert sec is not None
assert 'asyncio.gather' in sec.text
assert 'ml_context_used' in sec.text
assert 'get_unified_health' in sec.text
assert '2026-06-12' in sec.text
assert soup.find('footer') is not None
print('OK bridge section present, key facts verified')
"
```
Expected output: `OK bridge section present, key facts verified`

- [ ] **Step 3: Commit**

```bash
git add rag-service-how-it-works.html
git commit -m "docs: add ML-RAG bridge section to rag-service-how-it-works.html"
```

---

### Task 8: Full architecture diagram section

**Files:**
- Modify: `rag-service-how-it-works.html` (insert before `<footer>`)

**Interfaces:**
- Consumes: `.arch-wrap` class from Task 1.
- Produces: `<section id="architecture">` containing one inline SVG with `id="arch-svg"` covering the complete ingestion + retrieval flow through shared infrastructure.

**Deviation from plan (executed version):** the SVG below was built as drafted, but user review during execution found the 17-label, dual-color-path, nested-cluster version too complex to read. It was replaced with a simplified 6-box linear flow (USER → BACKEND → RAG SERVICE → POSTGRES, with GROQ LLM and MINIO branching off) using a single arrow color. The verification steps' expected label set changed accordingly to `['USER','BACKEND','RAG SERVICE','POSTGRES','MINIO','GROQ LLM']` (6 labels, not 17). The code block below is kept for historical record of what was originally planned; the shipped file has the simplified version.

This is the most visually complex task. Build it, then **render and visually check it — do not assume the coordinates are right on the first try** (this is normal SVG-authoring practice; the equivalent diagram in `ml-service-how-it-works.html` and the rapport's `wave2_benchmarks.png` figure both needed one round of spacing fixes after the first render).

- [ ] **Step 1: Insert the architecture section with its SVG**

Edit `rag-service-how-it-works.html`: insert immediately before `<footer>`:

```html
<!-- 7. FULL ARCHITECTURE -->
<section id="architecture">
  <div class="page-wrap">
    <div class="section-header">
      <div class="step-tag">Step 07 — Full Architecture</div>
      <h2>Everything, in one picture: upload to answer</h2>
      <p>Two paths through the same set of services. <span style="color:#2563EB;font-weight:700">Blue</span> is the ingestion path (a document becoming vectors). <span style="color:#F0A500;font-weight:700">Orange</span> is the retrieval path (a question becoming an answer). Both pass through the embedder and the Postgres/pgvector store — that's where they actually intersect in the real system.</p>
    </div>

    <div class="arch-wrap">
      <svg id="arch-svg" viewBox="0 0 1000 640" xmlns="http://www.w3.org/2000/svg" style="width:100%;min-width:720px">
        <defs>
          <marker id="a-blue" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#2563EB" opacity="0.8"/>
          </marker>
          <marker id="a-orange" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#F0A500" opacity="0.8"/>
          </marker>
        </defs>

        <!-- Frontend -->
        <rect x="20" y="20" width="160" height="56" rx="8" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4"/>
        <text x="100" y="44" text-anchor="middle" font-family="Courier New,monospace" font-size="10" fill="currentColor" opacity="0.8" font-weight="700">CHAT UI</text>
        <text x="100" y="60" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.5">machine-scoped question</text>

        <rect x="20" y="90" width="160" height="56" rx="8" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4"/>
        <text x="100" y="114" text-anchor="middle" font-family="Courier New,monospace" font-size="10" fill="currentColor" opacity="0.8" font-weight="700">ADMIN DOC UI</text>
        <text x="100" y="130" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.5">bulk upload / replace</text>

        <!-- Backend cluster -->
        <rect x="230" y="10" width="220" height="220" rx="8" fill="none" stroke="#F0A500" stroke-width="1.5" opacity="0.6"/>
        <text x="340" y="30" text-anchor="middle" font-family="Courier New,monospace" font-size="10" fill="#F0A500" font-weight="700">FASTAPI BACKEND</text>

        <rect x="242" y="42" width="196" height="26" rx="4" fill="none" stroke="currentColor" stroke-width="1" opacity="0.25"/>
        <text x="340" y="59" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.65">chat.py (/ai/chat)</text>

        <rect x="242" y="72" width="196" height="26" rx="4" fill="none" stroke="currentColor" stroke-width="1" opacity="0.25"/>
        <text x="340" y="89" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.65">rag_client.py</text>

        <rect x="242" y="102" width="196" height="26" rx="4" fill="none" stroke="currentColor" stroke-width="1" opacity="0.25"/>
        <text x="340" y="119" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.65">chat_context.py</text>

        <rect x="242" y="132" width="196" height="26" rx="4" fill="none" stroke="currentColor" stroke-width="1" opacity="0.25"/>
        <text x="340" y="149" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.65">rag_docs.py</text>

        <rect x="242" y="162" width="196" height="26" rx="4" fill="none" stroke="currentColor" stroke-width="1" opacity="0.25"/>
        <text x="340" y="179" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.65">rag_storage.py</text>

        <rect x="242" y="192" width="196" height="26" rx="4" fill="none" stroke="currentColor" stroke-width="1" opacity="0.25"/>
        <text x="340" y="209" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.65">core/groq_client.py</text>

        <!-- Frontend -> Backend arrows -->
        <line x1="180" y1="48" x2="228" y2="90" stroke="#F0A500" stroke-width="1.5" opacity="0.7" marker-end="url(#a-orange)"/>
        <line x1="180" y1="118" x2="228" y2="130" stroke="#2563EB" stroke-width="1.5" opacity="0.7" marker-end="url(#a-blue)"/>

        <!-- RAG microservice cluster -->
        <rect x="490" y="10" width="230" height="220" rx="8" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.45"/>
        <text x="605" y="30" text-anchor="middle" font-family="Courier New,monospace" font-size="10" fill="currentColor" opacity="0.8" font-weight="700">RAG MICROSERVICE</text>

        <rect x="502" y="42" width="206" height="26" rx="4" fill="none" stroke="#2563EB" stroke-width="1" opacity="0.5"/>
        <text x="605" y="59" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="#2563EB" opacity="0.85">ingestor.py</text>

        <rect x="502" y="72" width="206" height="26" rx="4" fill="none" stroke="currentColor" stroke-width="1" opacity="0.35"/>
        <text x="605" y="89" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.7">embedder.py (BGE-M3)</text>

        <rect x="502" y="102" width="206" height="26" rx="4" fill="none" stroke="#F0A500" stroke-width="1" opacity="0.5"/>
        <text x="605" y="119" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="#F0A500" opacity="0.85">retriever.py</text>

        <rect x="502" y="132" width="206" height="26" rx="4" fill="none" stroke="#F0A500" stroke-width="1" opacity="0.5"/>
        <text x="605" y="149" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="#F0A500" opacity="0.85">hybrid.py (FTS + RRF)</text>

        <rect x="502" y="162" width="206" height="26" rx="4" fill="none" stroke="#F0A500" stroke-width="1" opacity="0.5"/>
        <text x="605" y="179" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="#F0A500" opacity="0.85">reranker.py (BGE-reranker-v2-m3)</text>

        <!-- Backend -> RAG microservice -->
        <line x1="438" y1="55" x2="500" y2="55" stroke="#2563EB" stroke-width="1.5" opacity="0.7" marker-end="url(#a-blue)"/>
        <line x1="438" y1="85" x2="500" y2="115" stroke="#F0A500" stroke-width="1.5" opacity="0.7" marker-end="url(#a-orange)"/>

        <!-- Ingestion internal: ingestor -> embedder -->
        <line x1="605" y1="68" x2="605" y2="72" stroke="#2563EB" stroke-width="1.5" opacity="0.7" marker-end="url(#a-blue)"/>
        <!-- Retrieval internal: retriever -> hybrid + embedder (query embed) -->
        <line x1="605" y1="98" x2="605" y2="102" stroke="#F0A500" stroke-width="1.5" opacity="0.7" marker-end="url(#a-orange)"/>
        <line x1="605" y1="158" x2="605" y2="162" stroke="#F0A500" stroke-width="1.5" opacity="0.7" marker-end="url(#a-orange)"/>

        <!-- Storage row -->
        <rect x="490" y="270" width="230" height="80" rx="8" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4"/>
        <text x="605" y="294" text-anchor="middle" font-family="Courier New,monospace" font-size="10" fill="currentColor" opacity="0.75" font-weight="700">POSTGRESQL + PGVECTOR</text>
        <text x="605" y="312" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.5">documents · doc_chunks</text>
        <text x="605" y="326" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.5">embedding vector(1024)</text>
        <text x="605" y="340" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.5">content_tsv_fr · content_tsv_en</text>

        <rect x="230" y="270" width="200" height="80" rx="8" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4"/>
        <text x="330" y="294" text-anchor="middle" font-family="Courier New,monospace" font-size="10" fill="currentColor" opacity="0.75" font-weight="700">MINIO (S3)</text>
        <text x="330" y="312" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.5">rag-docs bucket</text>
        <text x="330" y="326" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="currentColor" opacity="0.5">original files, two-way sync</text>

        <!-- embedder -> pgvector (both flows write/read here) -->
        <line x1="605" y1="98" x2="605" y2="270" stroke="#2563EB" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.5" marker-end="url(#a-blue)"/>
        <line x1="640" y1="188" x2="640" y2="270" stroke="#F0A500" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.5" marker-end="url(#a-orange)"/>
        <!-- rag_docs.py / rag_storage.py -> MinIO -->
        <line x1="330" y1="230" x2="330" y2="268" stroke="#2563EB" stroke-width="1.5" opacity="0.6" marker-end="url(#a-blue)"/>

        <!-- Reranked chunks back to backend -->
        <line x1="502" y1="175" x2="452" y2="118" stroke="#F0A500" stroke-width="1.5" opacity="0.7" marker-end="url(#a-orange)"/>

        <!-- Backend -> Groq LLM -->
        <rect x="760" y="90" width="200" height="60" rx="8" fill="none" stroke="#F0A500" stroke-width="2" opacity="0.9"/>
        <text x="860" y="115" text-anchor="middle" font-family="Courier New,monospace" font-size="10" fill="#F0A500" font-weight="700">GROQ LLM</text>
        <text x="860" y="132" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="#F0A500" opacity="0.75">docs + ML snapshot merged</text>
        <line x1="440" y1="100" x2="758" y2="115" stroke="#F0A500" stroke-width="1.5" opacity="0.7" marker-end="url(#a-orange)"/>

        <!-- Groq -> back to Chat UI -->
        <path d="M 860 150 C 860 480, 100 480, 100 148" fill="none" stroke="#F0A500" stroke-width="1.5" stroke-dasharray="2,3" opacity="0.55" marker-end="url(#a-orange)"/>
        <text x="480" y="500" text-anchor="middle" font-family="Courier New,monospace" font-size="8.5" fill="#F0A500" opacity="0.6">answer, grounded in retrieved chunks + live machine state</text>

        <!-- Legend -->
        <rect x="20" y="560" width="960" height="60" rx="8" fill="none" stroke="currentColor" stroke-width="1" opacity="0.2"/>
        <line x1="40" y1="580" x2="80" y2="580" stroke="#2563EB" stroke-width="2"/>
        <text x="88" y="584" font-family="Courier New,monospace" font-size="9" fill="currentColor" opacity="0.7">Ingestion path — document → chunks → vectors → pgvector</text>
        <line x1="40" y1="602" x2="80" y2="602" stroke="#F0A500" stroke-width="2"/>
        <text x="88" y="606" font-family="Courier New,monospace" font-size="9" fill="currentColor" opacity="0.7">Retrieval path — question → hybrid search → rerank → LLM → answer</text>
      </svg>
    </div>
  </div>
</section>

<footer>
```

- [ ] **Step 2: Verify the SVG is well-formed and contains every expected label**

Run:
```bash
python -c "
from bs4 import BeautifulSoup
html = open('rag-service-how-it-works.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html-parser' if False else 'html.parser')
sec = soup.find('section', id='architecture')
assert sec is not None
svg = sec.find('svg', id='arch-svg')
assert svg is not None
labels = ['CHAT UI','ADMIN DOC UI','FASTAPI BACKEND','chat.py','rag_client.py','chat_context.py',
          'rag_docs.py','rag_storage.py','RAG MICROSERVICE','ingestor.py','embedder.py','retriever.py',
          'hybrid.py','reranker.py','POSTGRESQL','MINIO','GROQ LLM']
text = svg.get_text()
missing = [l for l in labels if l not in text]
assert not missing, f'missing labels: {missing}'
print('OK architecture svg present, all', len(labels), 'labels found')
"
```
Expected output: `OK architecture svg present, all 17 labels found`

- [ ] **Step 3: Render in the browser and visually check for overlap**

Use the Browser tool (`preview_start` with the file's local path, or `navigate` to the `file://` URL of `rag-service-how-it-works.html`), scroll to `#architecture`, and take a screenshot. Check specifically:
- No box label text overflows its own box outline.
- No two boxes visually overlap.
- All arrows visibly connect to a box edge, not floating in empty space or crossing through unrelated box interiors.
- The dashed curved path from Groq back to Chat UI doesn't cross through the storage row boxes.

If any of these fail, adjust the offending element's `x`/`y`/`width`/`height` (or the path's control points for the curve) directly in the SVG and re-render until clean — this is expected, iterative SVG work, exactly as was done for `figures/wave2_benchmarks.png` in the rapport earlier in this project.

- [ ] **Step 4: Commit**

```bash
git add rag-service-how-it-works.html
git commit -m "docs: add full architecture diagram section to rag-service-how-it-works.html"
```

---

### Task 9: Timeline recap strip + final QA

**Files:**
- Modify: `rag-service-how-it-works.html` (insert before `<footer>`)

**Interfaces:**
- Consumes: `.pipeline-wrap` class from Task 1; all section ids produced by Tasks 2–8.
- Produces: `<section id="timeline">`. No further sections after this task — it is the last content insertion, followed by full-page QA.

- [ ] **Step 1: Insert the Timeline recap section**

Edit `rag-service-how-it-works.html`: insert immediately before `<footer>`:

```html
<!-- 8. TIMELINE RECAP -->
<section id="timeline" style="background:var(--surface)">
  <div class="page-wrap">
    <div class="section-header">
      <div class="step-tag">Summary</div>
      <h2>Seven phases, in order</h2>
    </div>

    <div class="pipeline-wrap">
      <svg viewBox="0 0 980 120" xmlns="http://www.w3.org/2000/svg" style="width:100%;min-width:640px">
        <defs>
          <marker id="t-arr" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L7,3 z" fill="#F0A500" opacity="0.7"/>
          </marker>
        </defs>

        <rect x="0" y="30" width="120" height="60" rx="8" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        <text x="60" y="52" text-anchor="middle" font-family="Courier New,monospace" font-size="8" fill="currentColor" opacity="0.55" font-weight="700">05-11</text>
        <text x="60" y="66" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="currentColor" opacity="0.45">Born</text>
        <text x="60" y="78" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="currentColor" opacity="0.45">vector-only</text>

        <line x1="120" y1="60" x2="138" y2="60" stroke="#F0A500" stroke-width="1.5" opacity="0.6" marker-end="url(#t-arr)"/>

        <rect x="140" y="30" width="120" height="60" rx="8" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        <text x="200" y="52" text-anchor="middle" font-family="Courier New,monospace" font-size="8" fill="currentColor" opacity="0.55" font-weight="700">05-12</text>
        <text x="200" y="66" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="currentColor" opacity="0.45">Admin UI</text>
        <text x="200" y="78" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="currentColor" opacity="0.45">+ chat upload</text>

        <line x1="260" y1="60" x2="278" y2="60" stroke="#F0A500" stroke-width="1.5" opacity="0.6" marker-end="url(#t-arr)"/>

        <rect x="280" y="30" width="120" height="60" rx="8" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        <text x="340" y="52" text-anchor="middle" font-family="Courier New,monospace" font-size="8" fill="currentColor" opacity="0.55" font-weight="700">05-31</text>
        <text x="340" y="66" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="currentColor" opacity="0.45">S3 + OCR</text>
        <text x="340" y="78" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="currentColor" opacity="0.45">two-way sync</text>

        <line x1="400" y1="60" x2="418" y2="60" stroke="#F0A500" stroke-width="1.5" opacity="0.6" marker-end="url(#t-arr)"/>

        <rect x="420" y="30" width="120" height="60" rx="8" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        <text x="480" y="52" text-anchor="middle" font-family="Courier New,monospace" font-size="8" fill="currentColor" opacity="0.55" font-weight="700">06-01</text>
        <text x="480" y="66" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="currentColor" opacity="0.45">Caching</text>
        <text x="480" y="78" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="currentColor" opacity="0.45">+ BGE-M3</text>

        <line x1="540" y1="60" x2="558" y2="60" stroke="#F0A500" stroke-width="1.5" opacity="0.6" marker-end="url(#t-arr)"/>

        <rect x="560" y="30" width="120" height="60" rx="8" fill="none" stroke="#F0A500" stroke-width="1.5" opacity="0.7"/>
        <text x="620" y="52" text-anchor="middle" font-family="Courier New,monospace" font-size="8" fill="#F0A500" font-weight="700">06-06</text>
        <text x="620" y="66" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="#F0A500" opacity="0.85">Hybrid + RRF</text>
        <text x="620" y="78" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="#F0A500" opacity="0.85">Phase 13.2</text>

        <line x1="680" y1="60" x2="698" y2="60" stroke="#F0A500" stroke-width="1.5" opacity="0.6" marker-end="url(#t-arr)"/>

        <rect x="700" y="30" width="120" height="60" rx="8" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3"/>
        <text x="760" y="52" text-anchor="middle" font-family="Courier New,monospace" font-size="8" fill="currentColor" opacity="0.55" font-weight="700">06-11</text>
        <text x="760" y="66" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="currentColor" opacity="0.45">Dedup</text>
        <text x="760" y="78" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="currentColor" opacity="0.45">+ versioning</text>

        <line x1="820" y1="60" x2="838" y2="60" stroke="#F0A500" stroke-width="1.5" opacity="0.6" marker-end="url(#t-arr)"/>

        <rect x="840" y="30" width="140" height="60" rx="8" fill="none" stroke="#F0A500" stroke-width="1.5" opacity="0.7"/>
        <text x="910" y="52" text-anchor="middle" font-family="Courier New,monospace" font-size="8" fill="#F0A500" font-weight="700">06-12</text>
        <text x="910" y="66" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="#F0A500" opacity="0.85">Reranker</text>
        <text x="910" y="78" text-anchor="middle" font-family="Courier New,monospace" font-size="7.5" fill="#F0A500" opacity="0.85">+ ML bridge</text>
      </svg>
    </div>

    <div style="margin-top:36px;display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px">
      <div class="callout">
        <h4>What the RAG service does today</h4>
        <p>Ingests 12 file formats with OCR fallback, deduplicates by content hash, retrieves via hybrid vector+keyword search fused with RRF, reranks with a cross-encoder, and merges the result with live machine health data before the LLM ever sees the question.</p>
      </div>
      <div class="callout ok">
        <h4>What's deliberate about its design</h4>
        <p>Two different reliability postures by layer (fail loud in the keyword branch, fail soft from the chat's perspective), and a single source of truth for machine health shared between chat and dashboard.</p>
      </div>
      <div class="callout warn">
        <h4>What comes next</h4>
        <p>Further retrieval-quality work is tracked separately from this walkthrough — this page describes the mechanism as built, not a roadmap.</p>
      </div>
    </div>
  </div>
</section>

<footer>
```

- [ ] **Step 2: Verify the Timeline section**

Run:
```bash
python -c "
from bs4 import BeautifulSoup
html = open('rag-service-how-it-works.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')
sec = soup.find('section', id='timeline')
assert sec is not None
for d in ['05-11','05-12','05-31','06-01','06-06','06-11','06-12']:
    assert d in sec.text, f'missing {d}'
assert len(sec.select('.callout')) == 3
assert soup.find('footer') is not None
print('OK timeline section present, all 7 phase dates found, 3 closing callouts')
"
```
Expected output: `OK timeline section present, all 7 phase dates found, 3 closing callouts`

- [ ] **Step 3: Commit the timeline section**

```bash
git add rag-service-how-it-works.html
git commit -m "docs: add timeline recap section to rag-service-how-it-works.html"
```

- [ ] **Step 4: Full-page structural QA — nav/id consistency**

Run:
```bash
python -c "
from bs4 import BeautifulSoup
html = open('rag-service-how-it-works.html', encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')

nav_targets = set(a['href'].lstrip('#') for a in soup.select('.nav-links a'))
section_ids = set(s['id'] for s in soup.find_all('section') if s.get('id'))
missing = nav_targets - section_ids
assert not missing, f'nav links with no matching section id: {missing}'

expected_sections = {'problem','ingestion','storage','retrieval','reliability','bridge','architecture','timeline'}
assert section_ids == expected_sections, f'section id mismatch: {section_ids} vs {expected_sections}'

assert len(soup.find_all('footer')) == 1, 'footer must appear exactly once'
assert len(soup.find_all('script')) == 1, 'theme script must appear exactly once'
print('OK all nav links resolve, exactly 8 sections present, single footer/script')
"
```
Expected output: `OK all nav links resolve, exactly 8 sections present, single footer/script`

- [ ] **Step 5: Full-page fact QA against the spec's chronology table**

Run:
```bash
python -c "
html = open('rag-service-how-it-works.html', encoding='utf-8').read()
required_dates = ['2026-05-11','2026-05-12','2026-05-31','2026-06-01','2026-06-06','2026-06-11','2026-06-12']
missing_dates = [d for d in required_dates if d not in html]
assert not missing_dates, f'missing dates: {missing_dates}'

required_facts = [
    'BAAI/bge-m3', 'bge-reranker-v2-m3', 'Reciprocal Rank Fusion',
    'rag-docs', 'MinIO', 'pgvector', 'asyncio.gather', 'ml_context_used',
    'SHA-256', 'tsvector',
]
missing_facts = [f for f in required_facts if f.lower() not in html.lower()]
assert not missing_facts, f'missing facts: {missing_facts}'
print('OK all 7 chronology dates and all', len(required_facts), 'key facts present')
"
```
Expected output: `OK all 7 chronology dates and all 10 key facts present`

- [ ] **Step 6: Visual QA in the browser — light and dark**

Use the Browser tool: open `rag-service-how-it-works.html` (via `preview_start`/`navigate` to its `file://` path), scroll through every section top to bottom, screenshot. Click the theme toggle button (`◑`), scroll through again, screenshot. Confirm for both themes:
- Text is readable against its background everywhere (no dark-on-dark or light-on-light regions).
- The architecture diagram's box borders and text remain legible (SVG uses `currentColor` for most strokes/text so it should adapt automatically — verify it actually does).
- No horizontal scrollbar appears on the page body itself (only the `.arch-wrap`/`.pipeline-wrap` containers may scroll horizontally at narrow widths).
- Nav stays sticky and readable while scrolling.

If anything reads poorly in dark mode specifically, it's almost always a hardcoded light-mode-only color that should have used a CSS variable or `currentColor` instead — fix at the source rather than adding a dark-mode-only override.

- [ ] **Step 7: Final commit**

```bash
git add rag-service-how-it-works.html
git commit -m "docs: finish rag-service-how-it-works.html — QA pass complete"
```

---

## Self-Review

**Spec coverage:**
- Hero ✓ (Task 1) · Problem ✓ (Task 2) · Ingestion + history callouts ✓ (Task 3) · Storage & lifecycle + history ✓ (Task 4) · Retrieval + history ✓ (Task 5) · Fail-loud/fail-soft callout ✓ (Task 6) · ML-RAG bridge ✓ (Task 7) · Full architecture diagram ✓ (Task 8) · Timeline recap strip ✓ (Task 9) · Footer ✓ (Task 1) · Same visual design system, no new tokens ✓ (Task 1 reuses `ml-service-how-it-works.html`'s CSS verbatim) · No fabricated benchmarks ✓ (no accuracy/precision numbers appear anywhere in the plan's content) · Standalone, not touched into rapport ✓ (plan never edits any `rapport/` file).

**Placeholder scan:** No TBD/TODO in any task. Every code step contains complete, literal HTML. Every verification step is a runnable command with a stated expected output.

**Type consistency:** Section ids used consistently: `problem`, `ingestion`, `storage`, `retrieval`, `reliability`, `bridge`, `architecture`, `timeline` — same 8 ids referenced from Task 1's nav (7 linked + `reliability` intentionally unlinked per spec) through to Task 9's final consistency check. Class names (`.flow-steps`, `.card-grid-3`, `.callout`, `.dst-grid`, `.arch-wrap`, `.pipeline-wrap`) are defined once in Task 1 and only ever consumed, never redefined, in later tasks.
