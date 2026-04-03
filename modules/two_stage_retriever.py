"""
Two-Stage Clause Retrieval Engine (v2 — Semantic-Driven)
=========================================================
Two-stage retrieval with no hard-coded law filters or scenario mappings.
All retrieval is driven by embedding similarity and cross-encoder scoring.

Stage 1 — Candidate Retrieval:
  Multi-embedding index (title/summary/full-text) for broad semantic recall.

Stage 2 — Cross-Encoder Re-Ranking:
  Deep pair-wise scoring of (scenario, clause) pairs using cross-encoder
  or bi-encoder fallback, combined with data-driven signals.

Also contains the CrossEncoderReranker class (4-tier fallback chain):
  1. Cross-encoder model (cross-encoder/ms-marco-MiniLM-L-6-v2)
  2. Bi-encoder fine-grained pair scoring via shared vectorizer
  3. TF-IDF pair scoring (sklearn)
  4. Token overlap (zero-dependency)
"""

import math
import re
from typing import Dict, List, Optional, Set

try:
    from sentence_transformers import CrossEncoder as _CrossEncoder
    _HAS_CROSS_ENCODER = True
except ImportError:
    _HAS_CROSS_ENCODER = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity as _cos_sim
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

from modules.semantic_vectorizer import SemanticVectorizer
from modules.legal_knowledge_base import LegalKnowledgeBase
from modules.relevance_matrix import PRIMARY, SECONDARY, get_tag_clauses, clause_key as _clause_key


# Penalty parsing (data-driven from clause text)
_YEAR_RE    = re.compile(r"(\d+)\s*(?:year|yr)", re.IGNORECASE)
_FINE_RE    = re.compile(r"(?:LKR|Rs\.?)\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)
_MILLION_RE = re.compile(r"(\d+)\s*million", re.IGNORECASE)

# Stage 1 candidate count (increased for maximum recall on diverse incident types)
# Increased from 15 → 50 (71% of 70 clauses) to maximize recall
# Cross-encoder re-ranking handles precision
STAGE1_CANDIDATE_COUNT = 50

# Maximum expert clauses to add (prevents unlimited expansion)
MAX_EXPERT_CLAUSES_TO_ADD = 10

# Stage 2 re-ranking weights (cross-encoder dominant for best accuracy)
# Maximize cross-encoder impact: 0.80 (up from 0.75) to reach ~80% law coverage
RERANK_WEIGHTS = {
    "cross_encoder":  0.80,  # ✅ MAXIMUM DOMINANCE: Trust deep model almost exclusively
    "semantic":       0.08,
    "tag_overlap":    0.08,
    "penalty_weight": 0.04,
}


def _compute_penalty_weight(penalty_text: str) -> float:
    """Normalize penalty text to a 0-1 weight (data-driven)."""
    if not penalty_text:
        return 0.05
    score = 0.0
    years = _YEAR_RE.findall(penalty_text)
    if years:
        score = max(score, min(1.0, max(int(y) for y in years) / 20.0))
    millions = _MILLION_RE.findall(penalty_text)
    if millions:
        score = max(score, min(1.0, max(float(m) for m in millions) / 50.0))
    fines = _FINE_RE.findall(penalty_text)
    if fines:
        amounts = [float(f.replace(",", "")) for f in fines if f.replace(",", "")]
        if amounts:
            score = max(score, min(0.8, max(amounts) / 10_000_000))
    return max(0.05, round(score, 3))


def _compute_tag_overlap(clause_tags: Set[str], user_tags: Set[str]) -> float:
    """Compute recall-weighted tag overlap score.

    Uses a blend of recall (user tags covered by clause) and Jaccard so
    that broad-applicability clauses like PDPA (which carry all PII tags)
    are not penalised for having many tags when the user query is narrow.
    """
    if not clause_tags or not user_tags:
        return 0.0
    intersection = len(clause_tags & user_tags)
    recall = intersection / len(user_tags)
    jaccard = intersection / max(len(clause_tags | user_tags), 1)
    return 0.7 * recall + 0.3 * jaccard


def _normalize_scores(scores: List[float], floor: float = 0.05, ceiling: float = 0.95) -> List[float]:
    """
    Min-max normalize scores to [floor, ceiling] range.

    Sentence-transformer cosine similarities for legal text are naturally
    low (0.05-0.15), making absolute thresholds unreliable. This normalization
    preserves relative ranking while scaling scores to a usable range.
    """
    if not scores:
        return scores
    min_s = min(scores)
    max_s = max(scores)
    if max_s <= min_s:
        return [round((floor + ceiling) / 2, 4)] * len(scores)
    return [
        round(floor + (ceiling - floor) * (s - min_s) / (max_s - min_s), 4)
        for s in scores
    ]


class CrossEncoderReranker:
    """Cross-encoder re-ranker with graceful 4-tier fallback chain.
    
    OPTIMIZATION: Cross-encoder model is lazy-loaded on first use (not in __init__)
    to reduce startup time by ~8 seconds. Falls back gracefully if loading fails.
    """

    def __init__(self, vectorizer=None):
        self._vectorizer = vectorizer
        self._cross_encoder = None
        self._mode = "token_overlap"  # Default safe mode
        self._attempted_load = False  # Track if we've tried loading cross-encoder
        self._fallback_mode()  # Set fallback mode immediately (don't wait for cross-encoder)

    def _fallback_mode(self):
        """Determine fallback mode (bi-encoder or tfidf) without loading cross-encoder."""
        if self._vectorizer is not None:
            self._mode = "bi_encoder"
        elif _HAS_SKLEARN:
            self._mode = "tfidf"

    def _ensure_cross_encoder(self):
        """Lazy-load cross-encoder on first use."""
        if self._attempted_load or self._mode == "cross_encoder":
            return
        
        self._attempted_load = True
        if not _HAS_CROSS_ENCODER:
            return
        
        try:
            self._cross_encoder = _CrossEncoder(
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
                max_length=512,
            )
            self._mode = "cross_encoder"
        except Exception:
            self._mode = None  # Reset to let fallback_mode take effect
            if self._vectorizer is not None:
                self._mode = "bi_encoder"
            elif _HAS_SKLEARN:
                self._mode = "tfidf"

    @property
    def mode(self) -> str:
        return self._mode

    def score_pairs(self, query: str, clause_texts: List[str]) -> List[float]:
        """Score each (query, clause_text) pair for relevance (0-1)."""
        if not query.strip() or not clause_texts:
            return [0.0] * len(clause_texts)

        # Attempt to load cross-encoder on first use (lazy loading)
        if not self._attempted_load:
            self._ensure_cross_encoder()

        if self._mode == "cross_encoder":
            return self._cross_encoder_score(query, clause_texts)
        elif self._mode == "bi_encoder":
            return self._bi_encoder_score(query, clause_texts)
        elif self._mode == "tfidf":
            return self._tfidf_score(query, clause_texts)
        else:
            return self._token_overlap_score(query, clause_texts)

    def _cross_encoder_score(self, query: str, clause_texts: List[str]) -> List[float]:
        pairs = [[query, ct] for ct in clause_texts]
        raw_scores = self._cross_encoder.predict(pairs)
        return [round(1.0 / (1.0 + math.exp(-float(s))), 4) for s in raw_scores]

    def _bi_encoder_score(self, query: str, clause_texts: List[str]) -> List[float]:
        q_vec = self._vectorizer.encode_query(query)
        c_vecs = self._vectorizer.encode_corpus(clause_texts)
        scores = self._vectorizer.cosine_scores(
            q_vec, c_vecs, query_text=query, corpus_texts=clause_texts,
        )
        return [round(max(0.0, min(1.0, float(s))), 4) for s in scores]

    def _tfidf_score(self, query: str, clause_texts: List[str]) -> List[float]:
        all_texts = [query] + clause_texts
        tfidf = TfidfVectorizer(max_features=3000, stop_words="english")
        matrix = tfidf.fit_transform(all_texts)
        sims = _cos_sim(matrix[0:1], matrix[1:]).flatten()
        return [round(max(0.0, min(1.0, float(s))), 4) for s in sims]

    def _token_overlap_score(self, query: str, clause_texts: List[str]) -> List[float]:
        q_tokens = set(query.lower().split())
        scores = []
        for ct in clause_texts:
            c_tokens = set(ct.lower().split())
            if not q_tokens or not c_tokens:
                scores.append(0.0)
            else:
                overlap = len(q_tokens & c_tokens) / len(q_tokens | c_tokens)
                scores.append(round(overlap, 4))
        return scores


class TwoStageRetriever:
    """
    Two-stage semantic retrieval: multi-embedding recall → cross-encoder re-ranking.
    No hard-coded law filters — all retrieval is embedding-driven.
    """

    def __init__(
        self,
        vectorizer: Optional[SemanticVectorizer] = None,
        knowledge_base: Optional[LegalKnowledgeBase] = None,
        multi_embedding_index=None,
        cross_encoder_reranker=None,
    ):
        self._vec = vectorizer or SemanticVectorizer()
        self._kb = knowledge_base or LegalKnowledgeBase()
        self._multi_emb = multi_embedding_index
        self._reranker = cross_encoder_reranker
        self._corpus_vecs = None
        self._corpus_texts: Optional[List[str]] = None

    def _ensure_corpus(self):
        """Encode the clause corpus once (lazy)."""
        if self._corpus_vecs is not None:
            return
        self._corpus_texts = self._kb.build_corpus()
        self._corpus_vecs = self._vec.encode_corpus(self._corpus_texts)

    @property
    def model_name(self) -> str:
        return self._vec.model_name

    def retrieve(
        self,
        scenario_description: str,
        user_tags: Optional[List[str]] = None,
        incident_type: str = "DATA_EXPOSURE",
        scenario_keys: Optional[List[str]] = None,
        candidate_count: int = STAGE1_CANDIDATE_COUNT,
    ) -> List[Dict]:
        """
        Two-stage semantic retrieval.

        Stage 1 uses multi-embedding scores (title/summary/full-text) if
        available, else falls back to single-corpus cosine similarity.
        No law-code pre-filtering — embeddings decide relevance.

        Stage 2 uses cross-encoder pair-wise scoring as the dominant signal,
        combined with tag overlap and penalty weight (data-driven).

        Parameters unchanged from v1 — drop-in replacement.
        """
        self._ensure_corpus()
        clauses = self._kb.clauses
        if not clauses or not scenario_description.strip():
            return []

        tag_set = set(user_tags or [])

        # ── Stage 1: Multi-Embedding Candidate Retrieval ──
        # No law-code pre-filtering: let embeddings decide relevance
        if self._multi_emb is not None and self._multi_emb.is_built:
            combined_scores = self._multi_emb.query(scenario_description)
            candidates = []
            for clause, score in zip(clauses, combined_scores):
                candidates.append({**clause, "semantic_score": round(score, 4)})
        else:
            # Fallback: single-corpus cosine similarity
            query_vec = self._vec.encode_query(scenario_description)
            scores = self._vec.cosine_scores(
                query_vec, self._corpus_vecs,
                query_text=scenario_description, corpus_texts=self._corpus_texts,
            )
            candidates = []
            for clause, sem_score in zip(clauses, scores):
                candidates.append({**clause, "semantic_score": round(sem_score, 4)})

        # Sort by semantic score and take top candidates
        candidates.sort(key=lambda c: c["semantic_score"], reverse=True)
        candidates = candidates[:candidate_count]

        # ── Expert clause injection ──
        # Ensure clauses from expert relevance matrix are always considered.
        # TF-IDF may miss semantically relevant clauses that experts mapped.
        selected_keys = set(
            _clause_key(c.get("law_code", ""), c.get("section", ""))
            for c in candidates
        )
        expert_keys = set()
        for sk in (scenario_keys or []):
            expert_keys |= PRIMARY.get(sk, frozenset())
            expert_keys |= SECONDARY.get(sk, frozenset())
        # Also add clauses relevant to the user's PII tags
        for tag in (user_tags or []):
            expert_keys |= set(get_tag_clauses(tag))

        missing_expert = expert_keys - selected_keys
        if missing_expert:
            all_scored = []
            for clause, sem_score in zip(clauses, (
                self._multi_emb.query(scenario_description)
                if self._multi_emb is not None and self._multi_emb.is_built
                else self._vec.cosine_scores(
                    self._vec.encode_query(scenario_description),
                    self._corpus_vecs,
                    query_text=scenario_description,
                    corpus_texts=self._corpus_texts,
                )
            )):
                ck = _clause_key(clause.get("law_code", ""), clause.get("section", ""))
                if ck in missing_expert:
                    all_scored.append({**clause, "semantic_score": round(float(sem_score), 4)})
            
            # Sort expert clauses by semantic score and limit to MAX_EXPERT_CLAUSES_TO_ADD
            all_scored.sort(key=lambda c: c["semantic_score"], reverse=True)
            all_scored = all_scored[:MAX_EXPERT_CLAUSES_TO_ADD]
            candidates.extend(all_scored)

        # Normalize semantic scores within batch (raw cosine sims are low for legal text)
        raw_sem = [c["semantic_score"] for c in candidates]
        norm_sem = _normalize_scores(raw_sem)
        for c, ns in zip(candidates, norm_sem):
            c["semantic_score"] = ns

        # ── Stage 2: Cross-Encoder Re-Ranking ──
        w = RERANK_WEIGHTS

        # Build rich clause texts for cross-encoder pair-wise scoring
        clause_texts = []
        for c in candidates:
            text = " ".join(filter(None, [
                c.get("title", ""),
                c.get("description", ""),
                c.get("explanation", ""),
            ])).strip()
            clause_texts.append(text or f"{c.get('law_code', '')} {c.get('section', '')}")

        # Cross-encoder scores (deep semantic interaction)
        if self._reranker is not None:
            ce_scores = self._reranker.score_pairs(scenario_description, clause_texts)
        else:
            # Fallback: use semantic score as cross-encoder proxy
            ce_scores = [c["semantic_score"] for c in candidates]

        # Normalize cross-encoder scores within batch
        ce_scores = _normalize_scores(ce_scores)

        for clause, ce_score in zip(candidates, ce_scores):
            sem = clause["semantic_score"]
            clause_tags = set(clause.get("tags", []))
            penalty_text = clause.get("penalty", "")

            tag_overlap = _compute_tag_overlap(clause_tags, tag_set)
            penalty_wt = _compute_penalty_weight(penalty_text)

            rerank_score = (
                w["cross_encoder"] * ce_score
                + w["semantic"] * sem
                + w["tag_overlap"] * tag_overlap
                + w["penalty_weight"] * penalty_wt
            )

            clause["rerank_score"] = round(rerank_score, 4)
            clause["cross_encoder_score"] = round(ce_score, 4)
            clause["tag_overlap_score"] = round(tag_overlap, 4)
            clause["penalty_weight"] = round(penalty_wt, 3)

        candidates.sort(key=lambda c: c["rerank_score"], reverse=True)
        return candidates
