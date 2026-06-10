"""Document ingestion and chunking pipeline for The Unofficial Guide.

Implements the Chunking Strategy in planning.md:
- Reddit threads: one chunk per comment (split on [score N] markers), OP as its
  own chunk, thread title prepended to every chunk. Comments under MIN_CHUNK
  chars merge with the previous comment; texts over MAX_CHUNK chars split at
  paragraph breaks with a sentence (~OVERLAP chars) of overlap.
- Stanford Daily articles: paragraphs packed greedily into windows of at most
  MAX_CHUNK chars, with the previous window's last sentence as overlap.
- [score N] markers are stripped from chunk text and stored as `score`
  metadata; every chunk carries source title, URL, type, fetch date, and file.

Stdlib only. Run `python3 ingest.py` for the inspection report.
"""

import random
import re
import statistics
import sys
from pathlib import Path

DOCUMENTS_DIR = Path(__file__).parent / "documents"

MIN_CHUNK = 150    # comments shorter than this merge with a neighbor
MAX_CHUNK = 1000   # set by all-MiniLM-L6-v2's 256-token input limit
OVERLAP = 100      # approx chars of sentence overlap across forced splits

HEADER_FIELDS = ("Title", "Source", "Type", "Fetched")
COMMENT_MARKER = re.compile(r"^\[score (-?\d+)\]\s*", re.MULTILINE)
HTML_ENTITY = re.compile(r"&(?:[a-zA-Z]+|#x?\d+);")


def load_documents(directory=DOCUMENTS_DIR):
    """Parse every documents/*.txt into {meta fields, doc_type, body}."""
    documents = []
    paths = sorted(Path(directory).glob("*.txt"))
    if not paths:
        sys.exit(f"No .txt documents found in {directory}")
    for path in paths:
        raw = path.read_text(encoding="utf-8")
        header_text, sep, body = raw.partition("\n---\n")
        if not sep:
            sys.exit(f"{path.name}: missing '---' header separator")

        meta = {}
        for line in header_text.splitlines():
            key, _, value = line.partition(":")
            if key.strip() in HEADER_FIELDS:
                meta[key.strip().lower()] = value.strip()
        missing = [f for f in HEADER_FIELDS if f.lower() not in meta]
        if missing:
            sys.exit(f"{path.name}: header missing field(s) {missing}")

        body = body.strip()
        if not body:
            sys.exit(f"{path.name}: empty body")
        entities = HTML_ENTITY.findall(body)
        if entities:
            sys.exit(f"{path.name}: leftover HTML entities {entities[:5]}")

        documents.append({
            "file": path.name,
            "title": meta["title"],
            "url": meta["source"],
            "fetched": meta["fetched"],
            "doc_type": "reddit" if "Reddit" in meta["type"] else "article",
            "body": body,
        })
    return documents


def _last_sentence(text, limit=2 * OVERLAP):
    """Return the final sentence of `text` (capped at `limit` chars)."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    tail = sentences[-1]
    return tail if len(tail) <= limit else tail[-limit:]


def _split_long(text):
    """Split text over MAX_CHUNK at paragraph breaks, with sentence overlap."""
    if len(text) <= MAX_CHUNK:
        return [text]
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces, current = [], ""
    for para in paragraphs:
        # paragraph alone too long: fall back to sentence packing
        while len(para) > MAX_CHUNK:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            head, rest = "", ""
            for s in sentences:
                if head and len(head) + len(s) + 1 > MAX_CHUNK:
                    rest = para[len(head):].strip()
                    break
                head = f"{head} {s}".strip() if head else s
            pieces.append(head)
            para = f"{_last_sentence(head)} {rest}".strip()
        if current and len(current) + len(para) + 2 > MAX_CHUNK:
            pieces.append(current)
            current = f"{_last_sentence(current)}\n\n{para}"
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        pieces.append(current)
    return pieces


def _chunk_reddit(doc):
    """OP chunk + one chunk per comment; merge tiny, split oversized."""
    op_match = re.search(
        r"ORIGINAL POST:\n(.*?)\n\s*COMMENTS:", doc["body"], re.DOTALL
    )
    if not op_match:
        sys.exit(f"{doc['file']}: missing ORIGINAL POST/COMMENTS structure")
    op_text = op_match.group(1).strip()
    comments_blob = doc["body"][op_match.end():]

    # re.split with the capturing group yields [pre, score1, text1, score2, ...]
    parts = COMMENT_MARKER.split(comments_blob)
    comments = []  # (score, text)
    for i in range(1, len(parts), 2):
        text = parts[i + 1].strip()
        if text:
            comments.append((int(parts[i]), text))

    # merge comments under MIN_CHUNK into the previous comment
    merged = []
    for score, text in comments:
        if merged and len(text) < MIN_CHUNK:
            prev_score, prev_text = merged[-1]
            merged[-1] = (prev_score, f"{prev_text}\n\n{text}")
        elif not merged and len(text) < MIN_CHUNK and len(comments) > 1:
            merged.append((score, text))  # hold; next comment joins it
            continue
        else:
            merged.append((score, text))
    # second pass: a held-tiny first comment joins the one after it
    if len(merged) > 1 and len(merged[0][1]) < MIN_CHUNK:
        s0, t0 = merged.pop(0)
        s1, t1 = merged[0]
        merged[0] = (s1, f"{t0}\n\n{t1}")

    units = [("op", None, op_text)] + [("comment", s, t) for s, t in merged]
    chunks = []
    for part, score, text in units:
        for piece in _split_long(text):
            chunks.append({
                "text": f"{doc['title']} — {piece}",
                "part": part,
                "score": score,
            })
    return chunks


def _chunk_article(doc):
    """Pack paragraphs into windows of at most MAX_CHUNK chars, with overlap."""
    pieces = _split_long(doc["body"])
    return [{"text": p, "part": "article", "score": None} for p in pieces]


def chunk_documents(directory=DOCUMENTS_DIR):
    """Load every document and return the full list of chunk records."""
    all_chunks = []
    for doc in load_documents(directory):
        chunker = _chunk_reddit if doc["doc_type"] == "reddit" else _chunk_article
        for n, chunk in enumerate(chunker(doc), start=1):
            record = {
                "id": f"{Path(doc['file']).stem}-c{n:02d}",
                "text": chunk["text"],
                "metadata": {
                    "title": doc["title"],
                    "url": doc["url"],
                    "type": doc["doc_type"],
                    "part": chunk["part"],
                    "fetched": doc["fetched"],
                    "file": doc["file"],
                },
            }
            if chunk["score"] is not None:
                record["metadata"]["score"] = chunk["score"]
            all_chunks.append(record)
    return all_chunks


def _report():
    docs = load_documents()
    chunks = chunk_documents()

    print(f"Documents loaded: {len(docs)}")
    print(f"Total chunks:     {len(chunks)}\n")

    print(f"{'file':<38} {'raw comments':>12} {'chunks':>7}")
    for doc in docs:
        raw_comments = len(COMMENT_MARKER.findall(doc["body"]))
        n = sum(1 for c in chunks if c["metadata"]["file"] == doc["file"])
        print(f"{doc['file']:<38} {raw_comments:>12} {n:>7}")

    lengths = [len(c["text"]) for c in chunks]
    print(f"\nChunk length (chars): min {min(lengths)}, "
          f"median {int(statistics.median(lengths))}, max {max(lengths)}")

    empty = [c["id"] for c in chunks if not c["text"].strip()]
    short = [c["id"] for c in chunks if len(c["text"]) < MIN_CHUNK]
    # title prepend may push slightly past MAX_CHUNK; flag only real outliers
    long_ = [c["id"] for c in chunks if len(c["text"]) > MAX_CHUNK + 150]
    leaked = [c["id"] for c in chunks
              if "[score" in c["text"] or "Fetched:" in c["text"]]
    print(f"Empty: {empty or 'none'} | under {MIN_CHUNK}: {short or 'none'} | "
          f"over {MAX_CHUNK}+150: {long_ or 'none'} | marker leaks: {leaked or 'none'}")

    print("\n" + "=" * 72)
    print("5 RANDOM CHUNKS (seed 42) — checkpoint: each must stand on its own")
    print("=" * 72)
    rng = random.Random(42)
    for c in rng.sample(chunks, 5):
        meta = c["metadata"]
        score = f", score {meta['score']}" if "score" in meta else ""
        print(f"\n--- {c['id']} ({meta['part']}{score}) "
              f"[{len(c['text'])} chars] {meta['file']}")
        print(c["text"])


if __name__ == "__main__":
    _report()
