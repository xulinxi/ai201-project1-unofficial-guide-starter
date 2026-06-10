"""Grounded generation for The Unofficial Guide (stage 5 of the architecture).

ask(question) runs the full query flow from planning.md:
- retrieve(question) pulls the top-k chunks from ChromaDB
- if the best cosine distance is above DISTANCE_THRESHOLD, decline without
  calling the LLM at all (out-of-scope guard, Anticipated Challenge #5)
- otherwise Groq llama-3.3-70b-versatile answers from the retrieved excerpts
  only, citing source title + date per claim and presenting disagreement
  between commenters as disagreement (Anticipated Challenges #3-4)
- the source list is built programmatically from the retrieved chunks, never
  left to the LLM

Run `python query.py` for an interactive CLI loop (empty line or Ctrl-D
exits), or `python query.py --test` to run the evaluation-plan queries.
"""

import os
import sys

from dotenv import load_dotenv
from groq import Groq

from retrieval import TEST_QUERIES, retrieve

GROQ_MODEL = "llama-3.3-70b-versatile"
TEMPERATURE = 0.2

# Milestone 4 measurements: best distances for in-scope eval queries were
# 0.171-0.470; the out-of-scope query's best was 0.542. 0.5 splits them.
DISTANCE_THRESHOLD = 0.5

DECLINE_MESSAGE = "I don't have enough information on that in my documents."

SYSTEM_PROMPT = f"""\
You are The Unofficial Guide, a Q&A assistant for incoming Stanford freshmen.
Your ONLY source of knowledge is the document excerpts provided in each user
message. They come from Reddit threads and Stanford Daily articles written
between 2013 and 2021.

Hard rules:
1. Answer using ONLY the information in the provided excerpts. Never use your
   general knowledge about Stanford or anything else, even to fill small gaps.
2. If the excerpts do not contain enough information to answer the question,
   reply exactly: "{DECLINE_MESSAGE}" Do not guess or give generic advice.
3. Cite a source for every claim, using the document title and date from the
   excerpt label, e.g. (source: Dorm Review: Mirrielees, 2021-04-12).
4. The excerpts are student opinions and they disagree with each other. When
   they conflict, present the disagreement with attribution ("some students
   say X, others counter Y") instead of picking one side as fact.
5. These sources are from 2013-2021, so prices and policies may be outdated.
   Phrase time-sensitive facts with their source dates ("as of 2014, ...").
"""

_client = None


def get_client():
    load_dotenv()
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            sys.exit("GROQ_API_KEY not set — copy .env.example to .env")
        _client = Groq(api_key=api_key)
    return _client


def format_context(hits):
    """Label each retrieved chunk so the LLM can cite title + date."""
    blocks = []
    for i, hit in enumerate(hits, start=1):
        meta = hit["metadata"]
        blocks.append(
            f"[Document {i}: {meta['title']} ({meta['fetched']}), "
            f"file: {meta['file']}]\n{hit['text']}"
        )
    return "\n\n".join(blocks)


def format_sources(hits):
    """Unique source attributions in rank order, built from metadata."""
    sources = []
    for hit in hits:
        meta = hit["metadata"]
        label = f"{meta['title']} ({meta['file']}, fetched {meta['fetched']})"
        if label not in sources:
            sources.append(label)
    return sources


def ask(question, k=5):
    """Full query flow. Returns {answer, sources, grounded}."""
    hits = retrieve(question, k)

    if not hits or hits[0]["distance"] > DISTANCE_THRESHOLD:
        return {"answer": DECLINE_MESSAGE, "sources": [], "grounded": False}

    user_message = (
        f"Document excerpts:\n\n{format_context(hits)}\n\n"
        f"Question: {question}"
    )
    response = get_client().chat.completions.create(
        model=GROQ_MODEL,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    answer = response.choices[0].message.content.strip()

    # the model may still decline (rule 2); don't attribute sources to that
    if DECLINE_MESSAGE in answer:
        return {"answer": DECLINE_MESSAGE, "sources": [], "grounded": False}

    return {"answer": answer, "sources": format_sources(hits), "grounded": True}


def print_result(result):
    print(result["answer"])
    if result["sources"]:
        print("\nSources:")
        for source in result["sources"]:
            print(f"  • {source}")
    print()


def _test():
    for label, question in TEST_QUERIES:
        print("=" * 72)
        print(f"{label}: {question}\n")
        print_result(ask(question))


def _cli():
    print("The Unofficial Guide — ask about frosh life at Stanford "
          "(empty line to quit)\n")
    while True:
        try:
            question = input("? ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            break
        print()
        print_result(ask(question))


if __name__ == "__main__":
    _test() if "--test" in sys.argv else _cli()
