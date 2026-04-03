"""
Ensemble Retrieval Engine
=========================
Combines multiple retrieval methods for higher accuracy.

Strategy:
  1. SBERT semantic retrieval (50% weight)
  2. TF-IDF keyword matching (35% weight)
  3. Tag overlap matching (15% weight)
  
Three methods together catch more relevant clauses than any one alone.
"""

from typing import Dict, List, Set, Optional, Tuple
import re


class EnsembleRetriever:
    """Combines SBERT, TF-IDF, and tag-based retrieval."""

    def __init__(self, vectorizer=None):
        """Initialize with optional semantic vectorizer."""
        self._vectorizer = vectorizer
        self._tfidf_cache = {}

    def ensemble_retrieve(
        self,
        scenario_text: str,
        clauses: List[Dict],
        user_tags: Optional[List[str]] = None,
        top_k: int = 10,
    ) -> List[Dict]:
        """
        Retrieve clauses using ensemble of three methods.

        Returns top_k clauses scored by weighted combination:
          - SBERT semantic: 50%
          - TF-IDF keyword: 35%
          - Tag overlap: 15%
        """
        if not clauses:
            return []

        scores: Dict[int, Dict] = {}

        # Method 1: SBERT Semantic Retrieval (50%)
        if self._vectorizer:
            semantic_scores = self._semantic_scores(scenario_text, clauses)
            for idx, score in enumerate(semantic_scores):
                scores.setdefault(idx, {})["semantic"] = score

        # Method 2: TF-IDF Keyword Matching (35%)
        tfidf_scores = self._tfidf_scores(scenario_text, clauses)
        for idx, score in enumerate(tfidf_scores):
            scores.setdefault(idx, {})["tfidf"] = score

        # Method 3: Tag Overlap (15%)
        tag_scores = self._tag_overlap_scores(scenario_text, clauses, user_tags)
        for idx, score in enumerate(tag_scores):
            scores.setdefault(idx, {})["tag"] = score

        # Combine scores: weighted average
        combined_scores = []
        for idx, method_scores in scores.items():
            semantic = method_scores.get("semantic", 0.0) * 0.50
            tfidf = method_scores.get("tfidf", 0.0) * 0.35
            tag = method_scores.get("tag", 0.0) * 0.15

            combined = semantic + tfidf + tag

            combined_scores.append((idx, combined, method_scores))

        # Sort by combined score
        combined_scores.sort(key=lambda x: x[1], reverse=True)

        # Return top_k with metadata
        result = []
        for idx, combined_score, methods in combined_scores[:top_k]:
            clause = clauses[idx].copy()
            clause["ensemble_score"] = round(combined_score, 4)
            clause["ensemble_methods"] = {
                "semantic": round(methods.get("semantic", 0), 4),
                "tfidf": round(methods.get("tfidf", 0), 4),
                "tag": round(methods.get("tag", 0), 4),
            }
            result.append(clause)

        return result

    def _semantic_scores(self, query: str, clauses: List[Dict]) -> List[float]:
        """SBERT semantic similarity scores."""
        if not self._vectorizer:
            return [0.5] * len(clauses)

        try:
            query_embedding = self._vectorizer.encode_query(query)
            clause_texts = [c.get("description", "") for c in clauses]
            clause_embeddings = self._vectorizer.encode_corpus(clause_texts)

            scores = self._vectorizer.cosine_scores(
                query_embedding, clause_embeddings
            )
            # Normalize to 0-1
            return [(s + 1) / 2 for s in scores]
        except Exception:
            return [0.5] * len(clauses)

    def _tfidf_scores(self, query: str, clauses: List[Dict]) -> List[float]:
        """TF-IDF keyword matching scores."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            clause_texts = [
                " ".join([
                    c.get("title", ""),
                    c.get("description", ""),
                    " ".join(c.get("keywords", []) or []),
                ])
                for c in clauses
            ]

            if not clause_texts:
                return [0.5] * len(clauses)

            vectorizer = TfidfVectorizer(stop_words="english", max_features=100)
            tfidf_matrix = vectorizer.fit_transform([query] + clause_texts)

            query_tfidf = tfidf_matrix[0:1]
            clause_tfidf = tfidf_matrix[1:]

            similarities = cosine_similarity(query_tfidf, clause_tfidf)[0]
            return [max(0, min(1, s)) for s in similarities]

        except Exception:
            return [0.5] * len(clauses)

    def _tag_overlap_scores(
        self, query: str, clauses: List[Dict], user_tags: Optional[List[str]] = None
    ) -> List[float]:
        """Tag overlap matching scores."""
        query_tags = self._extract_tags(query)
        if user_tags:
            query_tags.update(t.lower().strip() for t in user_tags)

        scores = []
        for clause in clauses:
            clause_tags = set()
            clause_tags.update(t.lower().strip() for t in clause.get("tags", []) or [])
            clause_tags.update(t.lower().strip() for t in clause.get("keywords", []) or [])

            if not query_tags or not clause_tags:
                scores.append(0.2)  # Low baseline
                continue

            overlap = len(query_tags & clause_tags)
            max_set_size = max(len(query_tags), len(clause_tags))
            overlap_ratio = overlap / max_set_size if max_set_size > 0 else 0

            scores.append(overlap_ratio)

        return scores

    @staticmethod
    def _extract_tags(text: str) -> Set[str]:
        """Extract simple tags from text (word-based)."""
        if not text:
            return set()

        # Split into words, filter short words
        words = re.findall(r"\b\w{3,}\b", text.lower())
        return set(words)
