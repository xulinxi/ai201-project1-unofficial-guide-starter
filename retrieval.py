"""Embedding + vector store + retrieval for The Unofficial Guide.

Implements the Retrieval Approach in planning.md (stages 3-4 of the
architecture diagram):
- embeds every chunk from ingest.chunk_documents() with all-MiniLM-L6-v2
  (sentence-transformers, local, 384 dims)
- stores vectors + chunk text + source metadata in a persistent ChromaDB
  collection (./chroma_db, gitignored) using cosine distance
- retrieve(query, k=5) embeds the query with the SAME model and returns the
  top-k chunks with their sources and distance scores

Run `python3 retrieval.py` to (re)build the index and test retrieval against
evaluation-plan queries. Distance = 1 - cosine similarity: lower is better,
<0.5 is a solid match (Milestone 4 checkpoint).
"""

import chromadb
from sentence_transformers import SentenceTransformer

from ingest import chunk_documents

EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # see planning.md Retrieval Approach
COLLECTION = "unofficial_guide"
CHROMA_DIR = "chroma_db"
TOP_K = 5

_model = None


def get_model():
    """Load the embedding model once (downloads ~80 MB on first run)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"}
    )


def build_index():
    """Embed all chunks and store them in ChromaDB. Idempotent: rebuilds."""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass  # first run: nothing to delete
    collection = client.create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"}
    )

    chunks = chunk_documents()
    embeddings = get_model().encode(
        [c["text"] for c in chunks], normalize_embeddings=True
    )
    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings.tolist(),
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )
    return collection


def retrieve(query, k=TOP_K):
    """Return the top-k chunks for `query`: [{id, text, metadata, distance}]."""
    collection = get_collection()
    query_embedding = get_model().encode([query], normalize_embeddings=True)
    result = collection.query(
        query_embeddings=query_embedding.tolist(), n_results=k
    )
    return [
        {
            "id": result["ids"][0][i],
            "text": result["documents"][0][i],
            "metadata": result["metadatas"][0][i],
            "distance": result["distances"][0][i],
        }
        for i in range(len(result["ids"][0]))
    ]


# evaluation-plan queries (planning.md) + one deliberately out-of-scope query
TEST_QUERIES = [
    ("Q1", "If I'm randomly assigned to a theme house in the housing draw, "
           "do I have to participate in the theme programming?"),
    ("Q2", "Can I use a meal swipe at one dining hall and then eat at a "
           "different dining hall in the same meal period?"),
    ("Q3", "What kind of bike lock do students recommend, and can I keep an "
           "e-bike in my dorm room?"),
    ("Q4", "Is living in Mirrielees a good way to get off the meal plan, and "
           "what are the downsides?"),
    ("Q5", "How many units or hard classes should a freshman take per "
           "quarter?"),
    ("OOS", "How do I apply for financial aid at Stanford?"),  # not in corpus
]


def _test():
    n = build_index().count()
    print(f"Indexed {n} chunks into ChromaDB ({CHROMA_DIR}/, cosine space)\n")

    for label, query in TEST_QUERIES:
        print("=" * 72)
        print(f"{label}: {query}")
        for rank, hit in enumerate(retrieve(query), start=1):
            meta = hit["metadata"]
            preview = " ".join(hit["text"].split())[:140]
            print(f"  {rank}. [{hit['distance']:.3f}] {hit['id']} "
                  f"({meta['file']})")
            print(f"     {preview}…")
        print()


if __name__ == "__main__":
    _test()
