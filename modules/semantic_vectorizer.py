"""
Semantic Vectorization Module
==============================
Converts scenario narratives and legal clause texts into high-dimensional
embedding vectors for similarity-based retrieval.

Strategy:
  1. sbert_finetuned_legal  — fine-tuned on 1,885 legal query-clause pairs (NEW)
  2. all-MiniLM-L6-v2       — general-purpose SBERT fallback (proven 99.3% clause recall)
  3. TF-IDF                 — lightweight fallback requiring only scikit-learn
  4. Token overlap          — zero-dependency last resort

The module provides:
  - encode_query()    → vector for the synthesized scenario narrative
  - encode_corpus()   → matrix of vectors for all legal clause texts
  - cosine_scores()   → similarity scores between a query and corpus
"""

from typing import Any, List, Optional, Tuple
import os
import json

try:
    import numpy as np
except ImportError:
    np = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine
except ImportError:
    TfidfVectorizer = None
    sklearn_cosine = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


def _load_clauses() -> list:
    """Load legal_clauses.json once."""
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "legal_clauses.json")
    )
    for enc in ("utf-8-sig", "utf-8", "utf-16"):
        try:
            with open(path, "r", encoding=enc) as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (UnicodeDecodeError, UnicodeError):
            continue
    return []


class SemanticVectorizer:
    """
    Encodes text into embeddings and computes cosine similarity.
    Tries fine-tuned SBERT first, then baseline all-MiniLM-L6-v2, then TF-IDF, then token overlap.
    """

    _MODEL_CANDIDATES = [
        os.path.join(os.path.dirname(__file__), "..", "models", "sbert_finetuned_legal"),  # Fine-tuned: 3 epochs, 1,885 pairs (BEST: 70% law coverage)
        "all-MiniLM-L6-v2",   # Baseline SBERT — fallback with proven 99.3% clause recall
    ]

    def __init__(self):
        self._model = None
        self._model_name: Optional[str] = None
        self._loaded = False
        self._clause_cache: Optional[list] = None
        self._corpus_embeddings = None  # cached clause embeddings

    def _ensure_model(self):
        """Lazy-load the best available sentence-transformer model."""
        if self._loaded:
            return
        self._loaded = True

        if SentenceTransformer is None:
            return

        for name in self._MODEL_CANDIDATES:
            try:
                model_display_name = "sbert_finetuned_legal" if "sbert_finetuned_legal" in name else name
                print(f"   [LOAD] Trying model: {model_display_name}")
                
                self._model = SentenceTransformer(name)
                # Quick sanity check: encode a single test sentence
                test_result = self._model.encode(["test"], normalize_embeddings=True)
                self._model_name = name
                
                # Log success WITHOUT unicode characters
                print(f"   [OK] Loaded semantic model: {model_display_name} ({test_result.shape[1]}-dim)")
                return
            except (Exception, KeyboardInterrupt) as e:
                model_display_name = "sbert_finetuned_legal" if "sbert_finetuned_legal" in name else name
                print(f"   [FAIL] {model_display_name}: {type(e).__name__}")
                self._model = None
                continue

    @property
    def model_name(self) -> str:
        """Name of the active embedding model (for traceability)."""
        self._ensure_model()
        if self._model_name:
            return self._model_name
        if TfidfVectorizer is not None:
            return "TF-IDF"
        return "token-overlap"

    def encode_query(self, text: str) -> Any:
        """Return a vector for a single query string."""
        self._ensure_model()
        if self._model is not None and np is not None:
            return self._model.encode([text], normalize_embeddings=True)[0]
        # fallback: return raw text (handled in cosine_scores)
        return text

    def encode_corpus(self, texts: List[str]) -> Any:
        """Return a matrix of vectors for a list of documents."""
        self._ensure_model()
        if self._model is not None and np is not None:
            return self._model.encode(texts, normalize_embeddings=True)
        return texts

    def cosine_scores(self, query_vec, corpus_vecs, query_text: str = "", corpus_texts: List[str] = None) -> List[float]:
        """
        Compute cosine similarity between query and each corpus item.
        Handles all fallback tiers internally.
        """
        # Tier 1/2: SBERT embeddings (numpy arrays)
        if np is not None and hasattr(query_vec, "shape") and hasattr(corpus_vecs, "shape"):
            sims = np.dot(corpus_vecs, query_vec).tolist()
            return [float(max(0.0, min(1.0, s))) for s in sims]

        # Need raw texts for fallback tiers
        if corpus_texts is None:
            corpus_texts = corpus_vecs if isinstance(corpus_vecs, list) else []
        if not query_text:
            query_text = query_vec if isinstance(query_vec, str) else ""

        # Tier 3: TF-IDF
        if TfidfVectorizer is not None and sklearn_cosine is not None and corpus_texts:
            try:
                vec = TfidfVectorizer(stop_words="english")
                X = vec.fit_transform(corpus_texts + [query_text])
                cs = sklearn_cosine(X[:-1], X[-1:])
                return [float(max(0.0, min(1.0, s[0]))) for s in cs]
            except Exception:
                pass

        # Tier 4: Token overlap (Jaccard-like)
        q_tokens = set(query_text.lower().split())
        sims = []
        for doc in corpus_texts:
            d_tokens = set(doc.lower().split())
            union = q_tokens | d_tokens
            sims.append(len(q_tokens & d_tokens) / max(len(union), 1))
        return sims

    def build_clause_corpus(self, clauses: Optional[List[dict]] = None) -> Tuple[List[str], List[dict]]:
        """
        Build a text corpus from legal clauses JSON.
        Returns (corpus_texts, clause_list) where corpus_texts[i]
        corresponds to clause_list[i].
        """
        if clauses is None:
            if self._clause_cache is None:
                self._clause_cache = _load_clauses()
            clauses = self._clause_cache

        corpus: List[str] = []
        for c in clauses:
            text = " ".join([
                c.get("title", ""),
                c.get("description", ""),
                c.get("explanation", ""),
                c.get("full_text", ""),
            ]).strip()
            corpus.append(text or f"{c.get('law_code', '')} {c.get('section', '')}")
        return corpus, clauses

    def precompute_corpus_embeddings(self, clauses: Optional[List[dict]] = None):
        """
        Pre-encode all clause texts and cache the embeddings.
        Call once at startup for performance.
        """
        corpus_texts, clause_list = self.build_clause_corpus(clauses)
        self._clause_cache = clause_list
        self._corpus_embeddings = self.encode_corpus(corpus_texts)

    def get_cached_corpus(self) -> Tuple:
        """Return (corpus_embeddings, clause_list) — precompute if not done."""
        if self._corpus_embeddings is None or self._clause_cache is None:
            self.precompute_corpus_embeddings()
        corpus_texts, _ = self.build_clause_corpus(self._clause_cache)
        return self._corpus_embeddings, self._clause_cache, corpus_texts
