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

**Structure observations (input to the Milestone 2 chunking decision):**
- The corpus has two distinct shapes: **Reddit Q&A threads** (an OP question followed by independent comments, most 50–250 words, where each comment is a self-contained answer) and **long-form articles** (700–1,200-word essays where advice is spread across paragraphs).
- In threads, key facts concentrate in a single comment — e.g., the R&DE theme-house rule lives entirely in one comment — so chunking should avoid splitting individual comments.
- Document lengths vary widely: from ~120 words (doc 08) to ~1,200 words (docs 07, 11).

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**

**Overlap:**

**Reasoning:**

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**

**Top-k:**

**Production tradeoff reflection:**

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

1.

2.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
