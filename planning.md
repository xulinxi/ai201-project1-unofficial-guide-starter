# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

**Campus survival guide for Stanford University.** This system makes searchable the unofficial, experience-based knowledge Stanford students share with each other: how the housing draw actually works, whether the meal plan beats buying groceries, how to keep a bike from getting stolen, how many hard classes a freshman can realistically stack, and what campus culture actually feels like. None of this lives in official channels — Stanford's R&DE and registrar pages describe policies, not lived experience, cost math, or candid dorm reviews — so the real answers are scattered across r/stanford threads and student newspaper columns that are hard to find and disappear into feed history.

---

## Documents

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | r/stanford thread: "Throw down any advice for incoming freshmen" | General frosh advice: unit loads, cheating culture, SPOT trips, summer prep | https://www.reddit.com/r/stanford/comments/1kpj9n5/ → `documents/01-frosh-advice-thread.txt` |
| 2 | r/stanford thread: "any advice for incoming freshman" | Making friends, TA types, not overcommitting | https://www.reddit.com/r/stanford/comments/1hkh40s/ → `documents/02-incoming-freshman-advice.txt` |
| 3 | r/stanford thread: "How would you describe Stanford students and the Stanford vibe?" | Campus culture, collaboration vs. competition, the Stanford bubble | https://www.reddit.com/r/stanford/comments/1k632oh/ → `documents/03-stanford-vibe-and-culture.txt` |
| 4 | r/stanford thread: "Which is better: on-campus or off-campus accommodation?" | Grad housing tradeoffs, Bay Area rent reality, TA-ship logistics | https://www.reddit.com/r/stanford/comments/1k4ypka/ → `documents/04-on-vs-off-campus-housing.txt` |
| 5 | r/stanford thread: "Mirrielees: pros, cons, how to live there next year" | Candid dorm review: room layouts, heat, getting off the meal plan | https://www.reddit.com/r/stanford/comments/1b6i14k/ → `documents/05-mirrielees-dorm-review.txt` |
| 6 | r/stanford thread: "Randomly assigned to theme house in housing draw" | How theme-house assignment works; R&DE participation rules | https://www.reddit.com/r/stanford/comments/ovgzlv/ → `documents/06-housing-draw-theme-house.txt` |
| 7 | r/stanford thread: "Opinions on meal plan vs buying groceries for grad students" | Meal plan vs. cooking cost math, grocery logistics without a car | https://www.reddit.com/r/stanford/comments/1etuyis/ → `documents/07-meal-plan-vs-groceries.txt` |
| 8 | r/stanford thread: "Use meal plan swipe in one dining hall but go to another?" | Dining hall swipe mechanics | https://www.reddit.com/r/stanford/comments/1j30bzv/ → `documents/08-dining-hall-swipes.txt` |
| 9 | r/stanford thread: "Best way to keep your bike safe?" | Bike theft prevention, locks, AirTags, e-bike dorm policy | https://www.reddit.com/r/stanford/comments/1kc0zfk/ → `documents/09-bike-theft-prevention.txt` |
| 10 | r/stanford thread: "Practical Course Planning Advice for QR Track (Math + CS)" | Course sequencing, 60-series workload debate, realistic unit loads | https://www.reddit.com/r/stanford/comments/1kgznfz/ → `documents/10-course-planning-math-cs.txt` |
| 11 | Stanford Daily: "What I wish I knew…" (opinion, 2013) | Long-form upperclassman advice: classes, friendships, expectations | https://stanforddaily.com/2013/09/16/what-i-wish-i-knew/ → `documents/11-daily-what-i-wish-i-knew.txt` |
| 12 | Stanford Daily: "Top 5 tips for freshmen" (2014) | Health resources, activities fair, campus traditions | https://stanforddaily.com/2014/09/20/top-5-tips-for-freshmen/ → `documents/12-daily-top-5-frosh-tips.txt` |

**Collection notes:** Direct Reddit access (including `.json` endpoints) returns 403 from this environment; threads were retrieved through the pullpush.io archive API (submission + comments per thread), then cleaned by hand: duplicate archive snapshots deduplicated, deleted/bot/noise comments dropped, HTML entities fixed. Stanford Daily articles were fetched directly and stripped of navigation/footer text. Each file carries a uniform metadata header (Title / Source / Type / Fetched) so source attribution survives into chunking.

**Structure observations (input to the chunking decision):**
- The corpus has two distinct shapes: **Reddit Q&A threads** (an OP question followed by independent comments, most 50–250 words, where each comment is a self-contained answer) and **long-form articles** (700–1,200-word essays where advice is spread across paragraphs).
- In threads, key facts concentrate in a single comment — e.g., the R&DE theme-house rule lives entirely in one comment — so chunking should avoid splitting individual comments.
- Document lengths vary widely: from ~120 words (doc 08) to ~1,200 words (docs 07, 11).

---

## Chunking Strategy

**Approach: structure-aware chunking — boundaries follow the document's own units (Reddit comments, article paragraphs); size limits only handle outliers.**

**Chunk size:** Variable, bounded between 150 and 1,000 characters. (The 1,000-character cap is set by the embedding model: all-MiniLM-L6-v2 truncates input at 256 tokens ≈ 1,000–1,200 characters, so anything longer would be silently cut off before embedding — see Retrieval Approach.)
- *Reddit threads (docs 01–10):* one chunk per comment, split on the `[score N]` comment markers. The thread title is prepended to every chunk so a lone comment keeps its context (e.g., "Best way to keep your bike safe? — Use a U-lock…"). The OP post is its own chunk. Comments under ~150 characters are merged with a neighboring comment; comments over ~1,000 characters (e.g., the 2,400-character cheating warning in doc 01) are split at paragraph breaks.
- *Stanford Daily articles (docs 11–12):* paragraphs grouped into chunks of ~800–1,000 characters.

**Overlap:**
- *Reddit comment chunks:* **0 characters.** Each comment is a self-contained answer by a single author; nothing meaningful spans from one commenter's answer into the next person's, so there is nothing for overlap to repair. Overlap here would only bloat the index and fill top-k slots with near-duplicates.
- *Splits inside oversized comments and article paragraph groups:* **~100 characters (one sentence / one paragraph)**, because there the boundaries are arbitrary and a fact (claim + justification) can genuinely span the cut.

**Reasoning:** The corpus has two shapes with different needs. In the threads, key facts concentrate in single comments — the R&DE theme-house rule (doc 06, ~430 chars), the 4-point bike-theft answer (doc 09, ~1,100 chars), the housing cost breakdown (doc 04, ~1,600 chars) — and these are exactly what the evaluation questions depend on. A fixed split (e.g., 500 chars / 200 overlap) would carve each of them into 2–5 fragments, separating claims from their justifications and leaving pronoun-orphan chunks ("It's $90/year…" with "Safeway delivery" stranded in the previous chunk). Comment-level chunks keep each answer intact, keep the embedding focused on one opinion, and match the natural attribution unit (one chunk = one commenter = one citation). The long-form Daily essays are the opposite case — advice flows continuously across paragraphs — so they get conventional paragraph-window chunking with overlap. Failure signals to watch in evaluation: if retrieval returns fragments that need their neighbors to make sense, chunks are too small; if retrieved chunks match the query topic but bury the relevant sentence among unrelated opinions, chunks are too large.

**Final chunk count:** **81** across 12 documents (predicted ~75–90). Per `python3 ingest.py`: lengths min 187 / median 523 / max 1,067 characters (the max slightly exceeds 1,000 only because the thread title is prepended after the size rules apply — still within MiniLM's ~256-token window). No empty chunks, none under 150 chars after merging, no `[score N]` markers or header metadata leaked into chunk text.

---

## Retrieval Approach
<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** `all-MiniLM-L6-v2` via sentence-transformers (384 dimensions, 256-token input limit, runs locally with no API key).

Why this model fits this corpus:
- *Input limit matches the chunking strategy:* the 1,000-character chunk cap was chosen so every chunk fits inside the model's 256-token window without silent truncation.
- *Right register of text:* it's trained on general web English and tuned for short-sentence similarity — which matches both sides of this search problem (short user questions against short, informal, opinionated comments full of slang like "frosh" and "the draw").
- *Right scale:* with only ~75–90 chunks, benchmark differences between models won't be observable; retrieval failures here will come from chunking or query phrasing, not embedding quality. A small, fast, zero-setup model is the appropriate tool.

Runner-up considered: `BAAI/bge-small-en-v1.5` — same size and dimensions, better retrieval benchmarks (MTEB ~62 vs ~56), a 512-token window that would have allowed 1,500-character chunks, and asymmetric-search tuning that matches the short-query → longer-passage pattern. Rejected for the first build because it requires a special query prefix ("Represent this sentence for searching relevant passages: …") that silently degrades retrieval if forgotten — an avoidable failure mode in a first RAG system — and because MiniLM is the course-standard stack with far more debugging references.

**Distance threshold (calibrated in Milestone 4):** cosine distance **0.5** for the "not covered in my documents" guard. Measured on the real index: every evaluation query's best hit scores below 0.5 (range 0.171–0.470), while the deliberately out-of-scope query ("how do I apply for financial aid?") bottoms out at 0.542 — so 0.5 cleanly separates answerable from unanswerable on this corpus.

**Top-k:** 5. The corpus is ~75–90 chunks, so k=5 retrieves the top ~6% — enough to give the LLM multiple independent opinions for subjective questions (e.g., meal plan vs. groceries, where the good answer synthesizes several commenters), while small enough that off-topic chunks don't crowd the context and invite the model to answer from the wrong source. Too few (k=1–2) would break exactly the multi-opinion questions; too many (k=10+, an eighth of the index) would routinely pull in irrelevant chunks because there simply aren't 10 relevant ones for most queries.

**Production tradeoff reflection:** If this served real users at scale and cost weren't a constraint, the criteria would shift:
- *Context length* — chunks wouldn't need to bend to a 256-token limit; a long-context model (`bge-small-en-v1.5` at 512 tokens, `nomic-embed-text-v1.5` at 8,192) lets chunking follow document structure alone. I'd switch to bge-small for its longer window and asymmetric-search tuning, accepting the query-prefix requirement.
- *Multilingual support* — many Stanford grad students are international; a multilingual model (e.g., `multilingual-e5`) would let users query in their own language against English documents.
- *Identifier-heavy text* — semantic models fuzz exact tokens like "MATH 61CM" or "Mirrielees"; in production I'd add keyword (BM25) hybrid search rather than rely on embeddings alone.
- *Local vs. API* — hosted embeddings (OpenAI, Voyage) offer higher quality with zero ops burden, traded against per-token cost, latency on every query, and student-generated content leaving your infrastructure.

---


## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | If I'm randomly assigned to a theme house in the housing draw, do I have to participate in the theme programming? | No — per R&DE, students assigned to academic or ethnic theme communities through the draw are not required to take part in theme programming. (Exception: students assigned to co-ops must do house cooking/cleaning duties.) |
| 2 | Can I use a meal swipe at one dining hall and then eat at a different dining hall in the same meal period? | No — the system can tell and you run out of swipes for that period, though students report you can request a refund if you swiped in but took nothing. |
| 3 | What kind of bike lock do students recommend, and can I keep an e-bike in my dorm room? | A U-lock (or heavy Kryptonite chain) locked through the rack; avoid leaving the bike near public roads overnight and hide an AirTag. E-bikes are prohibited inside university residences (battery fire risk), though some students bring just the battery inside. |
| 4 | Is living in Mirrielees a good way to get off the meal plan, and what are the downsides? | Yes, it's the main undergrad option for getting off the meal plan (and you get big fridges/kitchens), but expect one-room doubles unless you're a senior, some of the worst room layouts on campus, and rooms that get uncomfortably hot. |
| 5 | How many units or hard classes should a freshman take per quarter? | Keep fall quarter around 15 units and limit yourself to ~2 difficult/STEM classes per quarter — don't fall into the "20 units of STEM" culture; problem sets are extremely time-consuming. |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->
     
1. **Document format fragility (ingestion/chunking).** The chunker depends entirely on hand-made conventions in the document files: the `---` line separating the metadata header from the body, the `[score N]` markers separating comments, and the `ORIGINAL POST:` / `COMMENTS:` labels. Any file that deviates — a missing marker, a `[score N]`-like string inside quoted text, a future document added without the same formatting — will mis-split silently: two commenters fused into one chunk, or header metadata embedded as content. *Mitigation:* after chunking, print every chunk with its source and eyeball the boundaries; assert chunk counts per document match the expected comment counts.

2. **The zero-overlap bet fails on reply chains (chunking).** Zero overlap between comment chunks assumes every comment is self-contained, but some comments are *replies* that only make sense with their parent. In doc 09, "Nah still don't care lol. About 1 in 30,000 e-bikes spontaneously ignite…" is rebutting a safety argument that lives in a different chunk; in doc 02, "Which one do you prefer: TAs that give answers or help you understand?" is a follow-up question with no standalone meaning. Retrieved alone, these chunks could mislead the LLM about what was claimed. *Mitigation:* the title-prepending helps; if evaluation surfaces this, attach parent-comment snippets as chunk metadata rather than adding blanket overlap.

3. **Contradictory opinions across chunks (generation).** The corpus deliberately contains disagreement — "Get a meal plan! It's cheaper" vs. "Dining hall food is absolute dogshit and expensive," or the 60-series "huge time sink" vs. "fav classes of my undergrad" debate in doc 10. If top-k returns both sides, the LLM might arbitrarily pick one and state it as fact. The system prompt must instruct it to present disagreement as disagreement, with attribution ("some students say X, others counter Y").

4. **Stale facts answered confidently (corpus limitation).** The Daily articles are from 2013–2014 and one housing thread is from 2021; prices ($12 meal blocks, $90/year Safeway delivery), policies, and club counts have certainly changed. Retrieval has no notion of freshness, so the system will cite a 2013 fact as if current. *Mitigation:* the Fetched/source dates are in every file header — surface them in citations so answers carry their age.

5. **Out-of-scope queries still retrieve something (retrieval).** Vector search always returns the top-5 nearest chunks, even when nearest is not *near* — a question about financial aid or parking permits (not in the corpus) will still pull five loosely related chunks, inviting a confident answer from the wrong material. *Mitigation:* check the similarity score of the best hit and have the system answer "my documents don't cover this" below a threshold; include one out-of-scope question in the evaluation set to test this.

6. **Exact identifiers get fuzzed by semantic search (retrieval).** Embeddings blur near-identical tokens: "MATH 51" vs. "MATH 61CM," "Mirrielees" vs. other dorm names, "Arrillaga" (a gym *and* a dining hall). A query about one specific course or building can retrieve chunks about a sibling identifier with high similarity. This is the strongest argument for the hybrid BM25 stretch feature, which matches identifiers exactly.

---

## Architecture

The pipeline is two flows sharing one vector store: an **indexing flow** that runs once (and re-runs only when documents change), and a **query flow** that runs per question. ChromaDB is the seam between them.

```
INDEXING FLOW (run once, offline)

 documents/*.txt           ①  DOCUMENT INGESTION         ②  CHUNKING
┌──────────────────┐      ┌───────────────────────┐     ┌─────────────────────────────┐
│ 12 files:        │      │ load_documents()      │     │ chunk_text()                │
│ 10 Reddit threads│ ───▶ │ parse metadata header │ ──▶ │ threads: 1 chunk/comment,   │
│  2 Daily articles│      │ + body                │     │   title prepended           │
│ (plain text +    │      │ [Python, stdlib]      │     │ articles: paragraph windows │
│  metadata header)│      └───────────────────────┘     │ 150–1,000 chars, ~75–90     │
└──────────────────┘                                    │ chunks + source metadata    │
                                                        └──────────────┬──────────────┘
                                                                       ▼
                            ③  EMBEDDING + VECTOR STORE
                           ┌────────────────────────────────────────────┐
                           │ all-MiniLM-L6-v2 (sentence-transformers)   │
                           │ chunk text → 384-dim vector                │
                           │ vectors + text + metadata stored in        │
                           │ ChromaDB (local, persistent ./chroma_db)   │
                           └────────────────────┬───────────────────────┘
                                                │
QUERY FLOW (per question)                       │ same collection
                                                ▼
 ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────────────┐
 │ user question│    │ embed query with │    │ ④  RETRIEVAL                │
 │ via CLI      │ ─▶ │ the SAME model   │ ─▶ │ ChromaDB similarity search  │
 │ (query.py)   │    │ all-MiniLM-L6-v2 │    │ top-k = 5 chunks + scores   │
 └──────────────┘    └──────────────────┘    │ low best-score → "not       │
                                             │ covered in my documents"    │
                                             └──────────────┬──────────────┘
                                                            ▼
                           ┌────────────────────────────────────────────┐
                           │ ⑤  GENERATION                              │
                           │ Groq API: llama-3.3-70b-versatile          │
                           │ system prompt: answer ONLY from retrieved  │
                           │ chunks; cite source (title + date) per     │
                           │ claim; present disagreement as such        │
                           └────────────────────┬───────────────────────┘
                                                ▼
                                   answer with source attribution
```

Two constraints the diagram encodes:
- **One embedding model on both sides.** Queries and chunks must be embedded by the same model (`all-MiniLM-L6-v2`) or similarity search is meaningless — the model choice is a single decision shared by stages ③ and ④.
- **Metadata rides the whole pipeline.** Source title/URL/date flow from file headers (①) → chunk metadata (②) → ChromaDB fields (③) → retrieved results (④) → citations (⑤). Any stage that drops it breaks source attribution at the end.

---

## AI Tool Plan

I plan to use AI (Claude Code) for every implementation stage of the pipeline, directed by the sections of this planning.md. For each stage: what I'll give it as input, what I expect it to produce, and how I'll verify the output against this spec.

**Milestone 3 — Ingestion and chunking:**
- *Input:* the Documents section (file paths, the metadata-header format) and the full Chunking Strategy section, plus Anticipated Challenge #1 (format fragility).
- *Expected output:* `ingest.py` with `load_documents()` (parse each `documents/*.txt` into header metadata + body) and `chunk_text()` implementing the spec exactly — split threads on `[score N]` markers, prepend thread titles, OP as its own chunk, merge <150-char comments, split >1,000-char comments at paragraph breaks with ~100-char overlap, paragraph-window chunks for the two articles. Each chunk carries metadata: source title, URL, type, fetch date.
- *Verification:* print every chunk with its source and eyeball boundaries against the original files (no fused commenters, no split-up R&DE quote in doc 06, no header text in bodies); check the final chunk count lands in the predicted ~75–90 range; record the actual count in Chunking Strategy.

**Milestone 4 — Embedding and retrieval:**
- *Input:* the Retrieval Approach section (model name, top-k = 5, and the reasoning) and the chunk format from Milestone 3.
- *Expected output:* code that embeds all chunks with `all-MiniLM-L6-v2` (sentence-transformers), stores them with metadata in a local ChromaDB collection, and a `retrieve(query, k=5)` function returning chunks with their sources and similarity scores.
- *Verification:* before any generation exists, run the 5 evaluation questions through `retrieve()` and check the expected source document appears in the top-5 for each (e.g., Q1 must surface doc 06's R&DE comment). Also run one out-of-scope query ("how do I apply for financial aid?") and look at the similarity scores to pick the "don't answer" threshold from Anticipated Challenge #5.
- *Note:* if I lower or raise the chunk cap after seeing real retrieval results, update Chunking Strategy and Retrieval Approach here first, then regenerate.

**Milestone 5 — Generation and interface:**
- *Input:* the Domain section, Anticipated Challenges #3–5 (contradictory opinions, stale facts, out-of-scope queries), and the project requirement that answers be grounded with source attribution.
- *Expected output:* a `generate(query)` function calling Groq `llama-3.3-70b-versatile` with a system prompt that (a) restricts answers to the retrieved chunks only, (b) requires a source citation (document title + date) for every claim, (c) presents disagreement between commenters as disagreement, and (d) declines when the best similarity score is below the threshold from Milestone 4. Plus a simple CLI loop (`python query.py`) as the query interface.
- *Verification:* ask a question whose answer I know is *not* in the corpus and confirm it declines rather than answers; ask the meal-plan question and confirm both sides of the disagreement appear with attribution; confirm every response names its source documents.

**Evaluation report:**
- *Input:* the Evaluation Plan table (5 questions + expected answers).
- *Expected output:* AI helps script the run (each question → retrieved chunks + response, recorded into the README table) — but the accuracy judgments (Relevant/Partially/Off-target, Accurate/Partially/Inaccurate) and the failure-case analysis I write myself, since honest grading of my own system is the point of the exercise.

Throughout: every AI-generated piece gets logged for the README's AI Usage section — what I gave it, what it produced, and what I changed or overrode.
