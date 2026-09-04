# RAG Pipeline Explainer Widget (presentation Artifact)

Date: 2026-09-04
Status: Approved (brainstorming session)

## Purpose

The PFE technical defense presentation (`presentation/technical_defense_en_v7.pptx`) has no slide explaining the AI/RAG system — what it actually does and how. This delivers a standalone, animated, presentable visual (a published Artifact page, not a PPTX slide) that walks a jury through the full RAG pipeline end to end: document ingestion → question answering.

Distinct from the existing `rag-service-how-it-works.html` (repo root, spec at `docs/superpowers/specs/2026-07-23-rag-service-how-it-works-design.md`): that page is a deep technical reference (dev history, code-level detail, light/dark docs theme, for anyone reading it unsupervised). This widget is a **live-narration presentation aid** — conceptual labels only, animated one stage at a time, styled to match the app's actual "Assistant IA" visual identity so the jury sees the real product's look, not a generic diagram. The presenter (user) adds technical depth verbally; the widget does not surface model names, algorithm names, or parameters.

## Source of truth

All stages trace to the real implementation, read directly during this session:

- `app/rag-service/main.py` — service endpoints (`/ingest`, `/retrieve`, `/documents`, …)
- `app/rag-service/ingestor.py` — multi-format extraction (PDF native + OCR fallback, TXT, image OCR, DOCX, XLSX, HTML), sha256 dedup, sentence-aware chunking (200 words / 20-word overlap), batch embedding, pgvector insert
- `app/rag-service/embedder.py` — `BAAI/bge-m3` singleton, 1024-dim vectors, 1h TTL query cache
- `app/rag-service/retriever.py` — orchestrates vector + keyword branches in parallel, RRF fuse, rerank, 5min TTL result cache
- `app/rag-service/hybrid.py` — Postgres FTS (french+english `tsvector`) keyword branch, Reciprocal Rank Fusion (k=60, overfetch=30), fail-loud on BM25 errors
- `app/rag-service/reranker.py` — `BAAI/bge-reranker-v2-m3` cross-encoder, overfetch ×4 capped at 50
- `app/backend/modules/shared/routes/chat.py` — `/ai/chat`: RAG chunks + ML snapshot fetched in parallel (`asyncio.gather`) when `machine_id` present, injected into system prompt, Groq LLM call with tool-calling
- `app/backend/services/ai_prompts.py` — `build_rag_context()`, `build_full_system_prompt()` (French `[BASE DOCUMENTAIRE]` context block, instructs the LLM to cite the source filename)
- `app/frontend/src/modules/shared/ChatInterface.tsx` + `app/frontend/src/index.css` — the real "Assistant IA" visual language this widget's styling is drawn from

No fabricated metrics (no invented precision/recall numbers) — mechanism only, matching this project's standing rule against invented figures.

## Content — two-act animated timeline

Conceptual labels only. No model names, algorithm names, or config numbers appear in the widget itself.

**Act 1 — Building the Knowledge Base** *(offline, whenever an admin uploads a document)*
1. Upload documents — machine manuals, SOPs, reports (PDF/Word/Excel/scans)
2. Read every page — text extraction, OCR fallback for scanned pages
3. Split into smart passages — overlapping chunks so search can find the exact paragraph, not just "the whole manual"
4. Turn into meaning + store — each passage converted into a searchable representation, saved in the knowledge base

**Act 2 — Answering a Question** *(online, every chat message)*
5. Technician asks a question — in Assistant IA, optionally scoped to one machine
6. Search two ways at once — meaning-based search + keyword search, in parallel
7. Merge & double-check relevance — the two result lists are fused, then re-scored for true relevance
8. Ground with live machine health — current ML/sensor snapshot pulled in parallel (only when a machine is selected)
9. Generate a cited answer — the AI writes the answer from the real retrieved passages and names the source document

A visible "knowledge base" node sits between the two acts — the artifact ingestion writes into and retrieval reads from, making the offline/online relationship explicit without a second diagram.

## Visual design

Reuses the app's real premium gradient/glass tokens verbatim (from `index.css`), not an invented palette:

- Canvas: dark, `hsl(217 32% 9%)` background, card surfaces `hsl(217 28% 13%)`
- Gradient: `hsl(239 84% 67%)` (indigo) → `hsl(270 91% 65%)` (purple) → `hsl(339 90% 63%)` (rose) — same three-stop gradient as `.bg-gradient-premium`
- Glass cards: `white/[0.03–0.10]` fill, `backdrop-blur(12px)`, `white/[0.08–0.20]` border — same recipe as `.glass` / the chat bubble cards
- Accent glow: `#00fff2` cyan on the active/focused stage — the same accent `ChatInterface.tsx` uses for hover/active states
- Icon motifs: Bot / Sparkles style (lucide), matching the chat widget's own iconography
- Typography: same sans stack as the app; stage counter/act label in a mono face for a "system status" feel

Each stage is a glass card; the active stage in the sequence is lifted (scale + cyan glow), inactive stages sit dimmed. A thin flow-line connects stage to stage, with a small animated pulse traveling along it when advancing — visualizes "data moving through the pipeline" without literal jargon.

## Interaction

- Auto-play on load, advancing one stage at a time on a fixed interval
- Play/Pause control
- Next/Prev manual stepping (auto-play pauses on manual interaction)
- Stage counter ("3 / 9") and act label ("Building the Knowledge Base" / "Answering a Question") always visible
- Click any stage card directly to jump to it
- Keyboard: arrow keys step, space toggles play/pause (defense presenter may not want to fight a trackpad)

## Implementation

- Single self-contained HTML file, published as a Claude Artifact (per the approved format decision) — no dev server, no login, presentable full-screen in any browser during the defense
- Inline SVG/CSS/JS only; no external runtime libraries needed (pure CSS animation + a small vanilla-JS state machine for stage index / play-pause)
- No artifact runtime capabilities required (no persistence, no live data) — this is a static, self-narrated explainer, not a connected dashboard
- Responsive enough for a projector at 16:9, but this is a presentation aid driven from a laptop, not a phone — desktop-first sizing

## Out of scope

- No PPTX export/embedding — Artifact link only, per the approved format decision (revisit only if the user later asks for a PPTX slide instead)
- No hidden technical detail layer (the "conceptual, hover-for-technical" hybrid option was explicitly declined)
- No rapport (`.tex`) integration
- No new content beyond the two acts above — ingestion and query-answering are the full pipeline; document storage lifecycle (MinIO versioning, admin CRUD UI) and the ML-RAG bridge's reliability contract (fail-loud vs fail-soft) are implementation details covered by the existing `rag-service-how-it-works.html`, not this presentation widget
