"""
Loads movies_clean.csv and builds both the minsearch (TF-IDF) and FAISS
(vector) indexes. Indexes are built once at import and reused across requests.
"""

import os
import numpy as np
import pandas as pd
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

from movie_assistant.minsearch import Index

DATA_PATH = Path(__file__).parent.parent / "data" / "movies_clean.csv"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

TEXT_FIELDS = ["title", "overview", "genres", "keywords", "tagline"]
KEYWORD_FIELDS = ["release_year", "vote_bucket"]
BOOST = {"title": 1.0, "keywords": 2.0, "overview": 2.0, "tagline": 0.5, "genres": 0.5}

_records: list[dict] = []
_minsearch_index: Index | None = None
_faiss_index: faiss.IndexFlatIP | None = None
_embedder: SentenceTransformer | None = None
_faiss_ids: list[str] = []  # parallel list of movie ids for FAISS results


def _load():
    global _records, _minsearch_index, _faiss_index, _embedder, _faiss_ids

    df = pd.read_csv(DATA_PATH)
    _records = df.to_dict("records")

    _minsearch_index = Index(text_fields=TEXT_FIELDS, keyword_fields=KEYWORD_FIELDS)
    _minsearch_index.fit(_records)

    _embedder = SentenceTransformer(EMBEDDING_MODEL)
    texts = [
        f"{r.get('title','')} {r.get('genres','')} {r.get('keywords','')} {r.get('overview','')}"
        for r in _records
    ]
    embeddings = _embedder.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    dim = embeddings.shape[1]
    _faiss_index = faiss.IndexFlatIP(dim)
    _faiss_index.add(embeddings.astype(np.float32))
    _faiss_ids = [str(r["id"]) for r in _records]


def search_minsearch(query: str, filter_dict: dict | None = None, num_results: int = 10, boost: dict | None = None) -> list[dict]:
    return _minsearch_index.search(query, filter_dict=filter_dict, boost_dict=boost or BOOST, num_results=num_results)


def search_faiss(query: str, num_results: int = 10) -> list[dict]:
    q_vec = _embedder.encode([query], normalize_embeddings=True).astype(np.float32)
    _, indices = _faiss_index.search(q_vec, num_results)
    return [_records[i] for i in indices[0] if i < len(_records)]


def search_rrf(query: str, num_results: int = 10, k: int = 60) -> list[dict]:
    ms_results = search_minsearch(query, num_results=num_results * 2)
    faiss_results = search_faiss(query, num_results=num_results * 2)

    scores: dict[str, float] = {}
    id_to_record: dict[str, dict] = {}

    for rank, r in enumerate(ms_results):
        rid = str(r["id"])
        scores[rid] = scores.get(rid, 0) + 1 / (k + rank + 1)
        id_to_record[rid] = r

    for rank, r in enumerate(faiss_results):
        rid = str(r["id"])
        scores[rid] = scores.get(rid, 0) + 1 / (k + rank + 1)
        id_to_record[rid] = r

    sorted_ids = sorted(scores, key=lambda x: -scores[x])
    return [id_to_record[rid] for rid in sorted_ids[:num_results]]


# Build indexes at import time
_load()
