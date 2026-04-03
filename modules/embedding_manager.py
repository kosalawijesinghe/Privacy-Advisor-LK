"""
Embedding Manager — Cache + Multi-Embedding Index
====================================================
Combines embedding caching (LRU + disk persistence) with
multi-embedding clause representations (title/summary/full-text)
for fast, accurate semantic retrieval.

Classes:
  EmbeddingCache            — LRU in-memory cache for embedding vectors
  PrecomputedEmbeddingStore — Disk-persistent clause embeddings
  MultiEmbeddingIndex       — Triple-embedding clause representation
"""

import hashlib
import os
from collections import OrderedDict
from typing import Any, Dict, List, Optional

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None
    _HAS_NUMPY = False

_DEFAULT_CACHE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "embedding_cache")
)


# ── LRU Embedding Cache ─────────────────────────────────────────────────────

class EmbeddingCache:
    """LRU cache for embedding vectors keyed by text hash."""

    def __init__(self, max_size: int = 256):
        self._max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _hash_key(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def get(self, text: str) -> Optional[Any]:
        key = self._hash_key(text)
        if key in self._cache:
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def put(self, text: str, embedding: Any):
        key = self._hash_key(text)
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            self._cache[key] = embedding

    def clear(self):
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> Dict:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(total, 1), 3),
        }


# ── Precomputed Embedding Store (disk-persistent) ───────────────────────────

class PrecomputedEmbeddingStore:
    """
    Wraps a SemanticVectorizer, caches corpus embeddings in memory,
    and persists them to disk as .npy files.
    """

    def __init__(self, vectorizer):
        self._vec = vectorizer
        self._corpus_embeddings = None
        self._clause_list = None
        self._corpus_texts = None
        self._query_cache = EmbeddingCache(max_size=256)
        self._built = False

    def build(self, clauses=None):
        corpus_texts, clause_list = self._vec.build_clause_corpus(clauses)
        self._clause_list = clause_list
        self._corpus_texts = corpus_texts
        self._corpus_embeddings = self._vec.encode_corpus(corpus_texts)
        self._built = True

    def save(self, cache_dir: str = _DEFAULT_CACHE_DIR) -> bool:
        if not self._built or not _HAS_NUMPY:
            return False
        try:
            os.makedirs(cache_dir, exist_ok=True)
            np.save(
                os.path.join(cache_dir, "corpus_embeddings.npy"),
                self._corpus_embeddings,
            )
            np.save(
                os.path.join(cache_dir, "corpus_texts.npy"),
                np.array(self._corpus_texts, dtype=object),
            )
            return True
        except Exception:
            return False

    def load(self, clauses, cache_dir: str = _DEFAULT_CACHE_DIR) -> bool:
        if not _HAS_NUMPY:
            return False
        emb_path = os.path.join(cache_dir, "corpus_embeddings.npy")
        text_path = os.path.join(cache_dir, "corpus_texts.npy")
        if not (os.path.exists(emb_path) and os.path.exists(text_path)):
            return False
        try:
            embeddings = np.load(emb_path, allow_pickle=False, mmap_mode="r")
            texts_arr = np.load(text_path, allow_pickle=True)
            corpus_texts = list(texts_arr)

            _, clause_list = self._vec.build_clause_corpus(clauses)
            if len(clause_list) != embeddings.shape[0]:
                return False

            self._corpus_embeddings = embeddings
            self._corpus_texts = corpus_texts
            self._clause_list = clause_list
            self._built = True
            return True
        except Exception:
            return False

    @property
    def is_built(self) -> bool:
        return self._built

    def encode_query_cached(self, text: str) -> Any:
        cached = self._query_cache.get(text)
        if cached is not None:
            return cached
        embedding = self._vec.encode_query(text)
        self._query_cache.put(text, embedding)
        return embedding

    def get_corpus_embeddings(self):
        return self._corpus_embeddings


# ── Multi-Embedding Clause Index ────────────────────────────────────────────

class MultiEmbeddingIndex:
    """
    Each clause gets three embeddings (title/summary/full-text).
    Combined similarity scores improve retrieval accuracy.
    """

    WEIGHTS = {"title": 0.25, "summary": 0.40, "full": 0.35}

    def __init__(self, vectorizer):
        self._vec = vectorizer
        self._title_embeddings = None
        self._summary_embeddings = None
        self._full_embeddings = None
        self._clauses: Optional[List[Dict]] = None
        self._title_texts: Optional[List[str]] = None
        self._summary_texts: Optional[List[str]] = None
        self._full_texts: Optional[List[str]] = None
        self._built = False

    def build(self, clauses: List[Dict]):
        self._clauses = clauses

        self._title_texts = [
            c.get("title", "") or f"{c.get('law_code', '')} {c.get('section', '')}"
            for c in clauses
        ]
        self._summary_texts = [
            " ".join(filter(None, [
                c.get("description", ""),
                c.get("explanation", ""),
            ])).strip() or c.get("title", "")
            for c in clauses
        ]
        self._full_texts = [
            " ".join(filter(None, [
                c.get("title", ""),
                c.get("description", ""),
                c.get("explanation", ""),
                c.get("full_text", ""),
            ])).strip() or f"{c.get('law_code', '')} {c.get('section', '')}"
            for c in clauses
        ]

        self._title_embeddings = self._vec.encode_corpus(self._title_texts)
        self._summary_embeddings = self._vec.encode_corpus(self._summary_texts)
        self._full_embeddings = self._vec.encode_corpus(self._full_texts)
        self._built = True

    def save(self, cache_dir: str = _DEFAULT_CACHE_DIR) -> bool:
        if not self._built or not _HAS_NUMPY:
            return False
        try:
            os.makedirs(cache_dir, exist_ok=True)
            np.save(os.path.join(cache_dir, "multi_title.npy"), self._title_embeddings)
            np.save(os.path.join(cache_dir, "multi_summary.npy"), self._summary_embeddings)
            np.save(os.path.join(cache_dir, "multi_full.npy"), self._full_embeddings)
            return True
        except Exception:
            return False

    def load(self, clauses: List[Dict], cache_dir: str = _DEFAULT_CACHE_DIR) -> bool:
        if not _HAS_NUMPY:
            return False
        title_path = os.path.join(cache_dir, "multi_title.npy")
        summary_path = os.path.join(cache_dir, "multi_summary.npy")
        full_path = os.path.join(cache_dir, "multi_full.npy")
        if not (os.path.exists(title_path) and os.path.exists(summary_path) and os.path.exists(full_path)):
            return False
        try:
            title_emb = np.load(title_path, allow_pickle=False, mmap_mode="r")
            summary_emb = np.load(summary_path, allow_pickle=False, mmap_mode="r")
            full_emb = np.load(full_path, allow_pickle=False, mmap_mode="r")

            if len(clauses) != title_emb.shape[0]:
                return False

            self._clauses = clauses
            self._title_texts = [
                c.get("title", "") or f"{c.get('law_code', '')} {c.get('section', '')}"
                for c in clauses
            ]
            self._summary_texts = [
                " ".join(filter(None, [
                    c.get("description", ""),
                    c.get("explanation", ""),
                ])).strip() or c.get("title", "")
                for c in clauses
            ]
            self._full_texts = [
                " ".join(filter(None, [
                    c.get("title", ""),
                    c.get("description", ""),
                    c.get("explanation", ""),
                    c.get("full_text", ""),
                ])).strip() or f"{c.get('law_code', '')} {c.get('section', '')}"
                for c in clauses
            ]
            self._title_embeddings = title_emb
            self._summary_embeddings = summary_emb
            self._full_embeddings = full_emb
            self._built = True
            return True
        except Exception:
            return False

    @property
    def is_built(self) -> bool:
        return self._built

    def query(self, text: str) -> List[float]:
        """Compute combined multi-embedding similarity scores for a query."""
        if not self._built:
            return []

        query_vec = self._vec.encode_query(text)

        title_scores = self._vec.cosine_scores(
            query_vec, self._title_embeddings,
            query_text=text, corpus_texts=self._title_texts,
        )
        summary_scores = self._vec.cosine_scores(
            query_vec, self._summary_embeddings,
            query_text=text, corpus_texts=self._summary_texts,
        )
        full_scores = self._vec.cosine_scores(
            query_vec, self._full_embeddings,
            query_text=text, corpus_texts=self._full_texts,
        )

        w = self.WEIGHTS
        combined = []
        for t, s, f in zip(title_scores, summary_scores, full_scores):
            score = w["title"] * t + w["summary"] * s + w["full"] * f
            combined.append(round(max(0.0, min(1.0, score)), 4))
        return combined
