# The Unofficial Guide — Project 1

A RAG system that makes unofficial Stanford student knowledge searchable: ask a plain-language question, get a grounded answer with source citations drawn from r/stanford threads and Stanford Daily articles.

**Run it:** `source .venv/bin/activate && pip install -r requirements.txt`, put your Groq key in `.env`, then `python retrieval.py` (build index) → `python app.py` (web UI) or `python query.py` (CLI).

---

## Domain

**Campus survival guide for Stanford University.** This system makes searchable the unofficial, experience-based knowledge Stanford students share with each other: how the housing draw actually works, whether the meal plan beats buying groceries, how to keep a bike from getting stolen, how many hard classes a freshman can realistically stack, and what campus culture actually feels like. None of this lives in official channels — Stanford's R&DE and registrar pages describe policies, not lived experience, cost math, or candid dorm reviews — so the real answers are scattered across r/stanford threads and student newspaper columns that are hard to find and disappear into feed history.

---

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | "Throw down any advice for incoming freshmen" | Reddit thread (r/stanford) | https://www.reddit.com/r/stanford/comments/1kpj9n5/ → `documents/01-frosh-advice-thread.txt` |
| 2 | "any advice for incoming freshman" | Reddit thread (r/stanford) | https://www.reddit.com/r/stanford/comments/1hkh40s/ → `documents/02-incoming-freshman-advice.txt` |
| 3 | "How would you describe Stanford students and the Stanford vibe?" | Reddit thread (r/stanford) | https://www.reddit.com/r/stanford/comments/1k632oh/ → `documents/03-stanford-vibe-and-culture.txt` |
| 4 | "Which is better: on-campus or off-campus accommodation?" | Reddit thread (r/stanford) | https://www.reddit.com/r/stanford/comments/1k4ypka/ → `documents/04-on-vs-off-campus-housing.txt` |
| 5 | "Mirrielees: pros, cons, how to live there next year" | Reddit thread (r/stanford) | https://www.reddit.com/r/stanford/comments/1b6i14k/ → `documents/05-mirrielees-dorm-review.txt` |
| 6 | "Randomly assigned to theme house in housing draw" | Reddit thread (r/stanford) | https://www.reddit.com/r/stanford/comments/ovgzlv/ → `documents/06-housing-draw-theme-house.txt` |
| 7 | "Opinions on meal plan vs buying groceries for grad students" | Reddit thread (r/stanford) | https://www.reddit.com/r/stanford/comments/1etuyis/ → `documents/07-meal-plan-vs-groceries.txt` |
| 8 | "Use meal plan swipe in one dining hall but go to another?" | Reddit thread (r/stanford) | https://www.reddit.com/r/stanford/comments/1j30bzv/ → `documents/08-dining-hall-swipes.txt` |
| 9 | "Best way to keep your bike safe?" | Reddit thread (r/stanford) | https://www.reddit.com/r/stanford/comments/1kc0zfk/ → `documents/09-bike-theft-prevention.txt` |
| 10 | "Practical Course Planning Advice for QR Track (Math + CS)" | Reddit thread (r/stanford) | https://www.reddit.com/r/stanford/comments/1kgznfz/ → `documents/10-course-planning-math-cs.txt` |
| 11 | "What I wish I knew…" (Katie Kramon, 2013) | Stanford Daily article | https://stanforddaily.com/2013/09/16/what-i-wish-i-knew/ → `documents/11-daily-what-i-wish-i-knew.txt` |
| 12 | "Top 5 tips for freshmen" (Sophia Dao, 2014) | Stanford Daily article | https://stanforddaily.com/2014/09/20/top-5-tips-for-freshmen/ → `documents/12-daily-top-5-frosh-tips.txt` |

**How the documents were collected:** Direct Reddit access (including `.json` endpoints) is blocked (HTTP 403) from this environment, so r/stanford threads were retrieved through the pullpush.io archive API (submission text plus comments per thread). Stanford Daily articles were fetched directly. Raw content was cleaned by hand: duplicate archive snapshots deduplicated, deleted/bot/noise comments removed, HTML entities fixed, and site navigation/footer text stripped. Each document is stored as plain text with a uniform metadata header (Title / Source URL / Type / Fetched date) to support source attribution downstream.

---

## Chunking Strategy

**Chunk size:** Variable, 150–1,000 characters, with boundaries that follow document structure rather than a character counter. Reddit threads (docs 01–10) get one chunk per comment, split on the `[score N]` markers; the OP is its own chunk; the thread title is prepended to every chunk so a lone comment keeps its context. Comments under 150 chars merge into the previous comment; comments over 1,000 chars split at paragraph breaks. Stanford Daily articles (docs 11–12) are packed paragraph-by-paragraph into windows of at most 1,000 chars. The 1,000 cap is set by the embedding model: all-MiniLM-L6-v2 truncates input at 256 tokens (≈1,000–1,200 chars), so longer chunks would be silently cut off before embedding.

**Overlap:** 0 between comment chunks — each comment is a self-contained answer by one author, so nothing meaningful spans the boundary and overlap would only fill top-k slots with near-duplicates. ~100 characters (the previous piece's closing sentence) only where cuts are genuinely arbitrary: inside oversized comments that had to be split, and between article paragraph windows.

**Why these choices fit your documents:** The key facts in this corpus concentrate in single comments — the R&DE theme-house rule (~430 chars), the 4-point bike-theft answer (~1,100 chars) — and those are exactly what the evaluation questions depend on. A fixed split (e.g., 500 chars / 200 overlap) would carve them into fragments, separating claims from justifications and stranding pronouns from their referents ("It's $90/year…" with "Safeway delivery plan" in the previous chunk). Comment-level chunks keep each answer intact, keep each embedding focused on one opinion, and match the attribution unit: one chunk = one commenter = one citation.

**Preprocessing:** Cleaning happened at collection time (deleted/bot comments removed, duplicate archive snapshots deduplicated, HTML entities fixed, nav/footer text stripped); the loader (`ingest.py`) then *verifies* rather than transforms — it hard-fails on missing header fields, empty bodies, or leftover HTML entities. The metadata header is split off before chunking, and `[score N]` markers are stripped from chunk text and stored as `score` metadata.

**Final chunk count:** **81** across 12 documents (predicted 75–90 in planning.md). Lengths: min 187 / median 523 / max 1,067 chars — the max slightly exceeds 1,000 because the title is prepended after the size rules apply. Verified by `python ingest.py`: no empty chunks, no leaked markers, deterministic output.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via sentence-transformers — 384 dimensions, 256-token input limit, runs locally with no API key. Three corpus-grounded reasons: (1) the chunking cap was chosen to fit inside its input window, so nothing is silently truncated; (2) it's tuned for short-sentence similarity over general web English, which matches both sides of this search problem — short user questions against short, informal, slang-heavy comments; (3) at 81 chunks, benchmark differences between embedding models aren't observable — retrieval failures here come from chunking and query phrasing, not embedding quality. Runner-up considered: `BAAI/bge-small-en-v1.5` (better MTEB scores, 512-token window, asymmetric-search tuning) — rejected for the first build because it requires a special query prefix that silently degrades retrieval if forgotten.

**Production tradeoff reflection:** At real scale with no cost constraint the criteria shift. *Context length:* a longer-window model (`bge-small-en-v1.5` at 512 tokens, `nomic-embed-text-v1.5` at 8,192) frees chunking to follow document structure alone — I'd switch to bge-small and accept the query-prefix requirement. *Multilingual support:* many Stanford grad students are international; a multilingual model (e.g., `multilingual-e5`) would let users query in their own language against English documents. *Identifier-heavy text:* semantic models fuzz exact tokens like "MATH 61CM" or "Mirrielees" — in production I'd add keyword (BM25) hybrid search rather than rely on embeddings alone. *Local vs. API-hosted:* hosted embeddings (OpenAI, Voyage) offer higher quality with zero ops burden, traded against per-query latency, per-token cost, and student-generated content leaving my infrastructure.

---

## Grounded Generation

**System prompt grounding instruction:** The system prompt (in `query.py`) sets five hard rules; the core grounding ones verbatim:

> 1. Answer using ONLY the information in the provided excerpts. Never use your general knowledge about Stanford or anything else, even to fill small gaps.
> 2. If the excerpts do not contain enough information to answer the question, reply exactly: "I don't have enough information on that in my documents." Do not guess or give generic advice.
> 4. The excerpts are student opinions and they disagree with each other. When they conflict, present the disagreement with attribution ("some students say X, others counter Y") instead of picking one side as fact.

**Structural mechanisms beyond the prompt:** (1) *A retrieval-distance guard runs before the LLM is ever called* — if the best chunk's cosine distance exceeds 0.5 (calibrated in Milestone 4: in-scope queries score 0.171–0.470, the out-of-scope test query 0.542), `ask()` returns the decline message without a generation step, so the model can't hallucinate about topics the corpus doesn't cover. (2) Retrieved chunks are passed as labeled excerpts (`[Document 1: <title> (<date>), file: <name>]`) so citations reference real labels rather than model memory. (3) Temperature is 0.2 to keep the model close to the provided text. (4) If the model itself declines (rule 2), the code strips the source list so a refusal is never decorated with citations.

**How source attribution is surfaced in the response:** Twice, independently. Inline, the model cites the document title and date per claim, e.g. *"(source: Best way to keep your bike safe?, 2026-06-09)"*. Then a **Sources** list is appended *programmatically* from the retrieved chunks' metadata (title, file, fetch date) — built by code, not the LLM, so even if the model mis-cites inline, the true provenance of the context is always shown. Both the CLI (`python query.py`) and the Gradio UI (`python app.py`) display it.

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | If I'm randomly assigned to a theme house in the housing draw, do I have to participate in the theme programming? | No — per R&DE, theme-community assignees aren't required to participate (co-op assignees do have cooking/cleaning duties) | Quoted the R&DE rule correctly (not required), added the upperclassman nuance that you'll probably join a few events for fun anyway; did not mention the co-op exception (not asked) | Relevant — top 3 hits all from doc 06 (best distance 0.172); ranks 4–5 off-topic but ignored | Accurate |
| 2 | Can I use a meal swipe at one dining hall and then eat at a different one in the same meal period? | No — the system can tell and you run out of swipes; reportedly refundable if you swiped in but took nothing | Both facts present: they can tell / you run out of swipes for the period, plus the swipe-in-refund report | Relevant — doc 08's answer chunk rank 1 (0.207) | Accurate |
| 3 | What bike lock do students recommend, and can I keep an e-bike in my dorm? | U-lock or heavy chain through the rack; AirTag; e-bikes prohibited inside residences (battery fire risk), some bring just the battery in | U-lock + Kryptonite chain + hub-motor chain trick; policy prohibition stated with the fire reason; battery-inside compromise and the rule-breakers both presented as disagreement | Relevant — all 5 hits from doc 09 (best 0.269) | Accurate |
| 4 | Is Mirrielees a good way to get off the meal plan, and what are the downsides? | Yes (main undergrad option, big fridges) but one-room doubles unless senior, worst layouts on campus, hot rooms | Yes + downsides (bunking layouts, heat with no control) + fridge upside; did not surface the one-room-doubles-unless-senior detail | Relevant — doc 05 ranks 1–2 (best 0.171) | Accurate (minor omission) |
| 5 | How many units or hard classes should a freshman take per quarter? | ~15 units fall quarter, max ~2 difficult/STEM classes — don't fall into "20 units of STEM" culture | Got "limit to 2 difficult classes" and the 61CM workload warning, but explicitly said there's "no specific consensus on the exact number of units" — missing the "keep fall quarter to 15 units" advice that exists in doc 01 | Partially relevant — the chunk containing "15 units" never made top-5 (see Failure Case) | Partially accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

**Out-of-scope control question** (not in the 5, added per Anticipated Challenge #5): *"How do I apply for financial aid at Stanford?"* — best retrieval distance 0.542 exceeded the 0.5 threshold, so the system declined with "I don't have enough information on that in my documents" without calling the LLM. Correct behavior.

**Known citation quirk:** inline citations show the *fetch* date (2026-06-09) rather than each thread's original posting date, because pullpush.io archive metadata is what the pipeline carries. The dates shown are honest but overstate freshness for the older threads (2021) — a real limitation worth fixing by carrying the thread's created date through the metadata.

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:** Q5 — "How many units or hard classes should a freshman take per quarter?"

**What the system returned:** A partially correct answer: it found "limit yourself to 2 difficult classes per quarter" and the 61CM workload warning, but explicitly claimed there is "no specific consensus on the exact number of units" — even though doc 01 contains a score-6 comment saying outright "Keep fall quarter to 15 units." The expected answer's most concrete number never appeared.

**Root cause (tied to a specific pipeline stage):** An embedding-stage dilution failure inside a single chunk. The "15 units" advice lives at the tail of a multi-topic comment whose first 80% is about something else entirely: *"Get in great shape; learn how to use a CNC machine; how to use an old fashioned lathe and milling machine; be sure to know how to handle drinking; get comfortable with four mile runs and gym workouts. Narrow down where you want to get an internship. Keep fall quarter to 15 units."* One chunk gets one 384-dim vector, and that vector is an average of everything in the chunk — here it's dominated by fitness/machine-shop/drinking signal, so the units query ranked it below the top-5 cutoff (the Milestone 4 test shows ranks 1–5 going to other chunks, the weakest at 0.585). Notably, this is *not* a chunk-boundary failure my chunking strategy could prevent: the comment is a single author's single answer, so comment-level chunking correctly kept it whole — the problem is that the author changed topics mid-comment.

**What you would change to fix it:** Two complementary fixes. (1) Hybrid keyword search (the BM25 stretch feature): the chunk literally contains the query word "units," so exact-term matching would surface it instantly — this failure is the textbook case semantic-only retrieval misses. (2) For listicle-style multi-topic comments, split on sentence boundaries when a chunk's sentences are semantically dissimilar from each other (or simply raise k from 5 to 8 on this small corpus, at the cost of more off-topic context for the LLM).

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:** The spec turned verification from an afterthought into a checklist. Because planning.md named concrete, pre-measured targets — the R&DE quote (~430 chars) must survive in one chunk, the 2,400-char cheating comment must split at paragraph breaks, the total should land in 75–90 chunks — every pipeline stage had pass/fail tests before its code existed. The same pattern paid off in Milestone 4: the evaluation questions written in Milestone 2 doubled as retrieval tests run *before* generation was wired in, which is how the 0.5 distance threshold got calibrated against a measured gap (0.470 in-scope vs 0.542 out-of-scope) instead of guessed.

**One way your implementation diverged from the spec, and why:** The spec said chunks are "bounded between 150 and 1,000 characters," but the implementation applies those bounds to the comment text *before* prepending the thread title, so the largest final chunk is 1,067 chars. This was deliberate: the title is retrieval context, not content, and trimming content to make room for it would have cut real information — while 1,067 chars still fits MiniLM's ~256-token window. A second small divergence: the spec didn't say where `[score N]` markers should go; the implementation strips them from chunk text into metadata, keeping embeddings clean prose while preserving the credibility signal for future ranking or filtering.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1 — chunking parameters**

- *What I gave the AI:* My proposed chunking parameters — 500-character chunks with 200-character overlap, "to fit comment size" — together with the corpus structure notes from planning.md.
- *What it produced:* An analysis showing those numbers don't fit my own documents: 500 chars would carve the comments my eval questions depend on into 2–5 fragments each (the 2,400-char cheating warning, the 1,100-char bike answer), and 200/500 = 40% overlap would bloat the index ~1.7× with near-duplicates. It proposed structure-aware chunking instead: one chunk per comment, size bounds only for outliers, zero overlap across comment boundaries.
- *What I changed or overrode:* I dropped my fixed-size plan and adopted the structure-aware spec, but required the reasoning to be written into planning.md *before* any implementation, and later tightened the cap from 1,500 to 1,000 chars when the embedding model's 256-token limit made longer chunks pointless.

**Instance 2 — milestone scope control**

- *What I gave the AI:* The Milestone 1 instructions (choose domain, collect documents) and a request to plan the work.
- *What it produced:* A plan that jumped ahead — it included writing `ingest.py` fetch-pipeline code during Milestone 1.
- *What I changed or overrode:* I rejected the plan and quoted the milestone text back ("Before touching any code…"); the revised plan collected documents as hand-cleaned text files with no code, and the ingestion script was deferred to Milestone 3 where it belongs. The AI also hit a real obstacle worth recording: direct Reddit access returns HTTP 403 from my machine, and it found the pullpush.io archive API as the workaround — which then became the documented collection method.

**Instance 3 — embedding/retrieval code**

- *What I gave the AI:* The Retrieval Approach section of planning.md (model, top-k=5, reasoning) and the chunk format from `ingest.py`.
- *What it produced:* `retrieval.py` — including one detail I hadn't specified: it configured the ChromaDB collection with `hnsw:space: cosine`, overriding ChromaDB's default squared-L2 distance, and explained that without this the milestone's "distance < 0.5" guidance wouldn't be on the right scale.
- *What I changed or overrode:* I had it walk through the `collection.add()` parallel-lists API and the cosine-vs-L2 choice until I could explain them myself, then verified the threshold empirically by running all 5 eval queries plus an out-of-scope control before accepting the 0.5 cutoff into `query.py`.
