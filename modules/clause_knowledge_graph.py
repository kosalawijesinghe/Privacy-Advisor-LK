"""
Clause Knowledge Graph
========================
Legal relationship graph between clauses for enhanced reasoning.

Relationship types:
  - related_to         : clauses addressing similar legal concepts
  - supports           : clause provides supporting/complementary provisions
  - extends            : clause extends or strengthens another
  - cross_law_reference: clause references provisions in a different act

During result generation, the graph provides:
  - Primary clause (directly matched)
  - Supporting clauses (via 'supports' or 'extends' edges)
  - Related clauses (via 'related_to' or 'cross_law_reference' edges)
"""

from typing import Dict, List, Optional, Tuple


# Type alias for clause keys: "LAW_CODE:Section"
ClauseKey = str

# Relationship types
RELATED_TO = "related_to"
SUPPORTS = "supports"
EXTENDS = "extends"
CROSS_LAW_REF = "cross_law_reference"


# ── Graph edges: (source_clause, target_clause, relationship_type) ───────────
_GRAPH_EDGES: List[Tuple[ClauseKey, ClauseKey, str]] = [
    # PDPA internal relationships
    ("PDPA:6(1)a)", "PDPA:6(1)b)", RELATED_TO),
    ("PDPA:6(1)a)", "PDPA:6(1)c)", RELATED_TO),
    ("PDPA:6(1)b)", "PDPA:6(1)c)", RELATED_TO),
    ("PDPA:7(a)", "PDPA:7(b)", RELATED_TO),
    ("PDPA:7(a)", "PDPA:7(c)", RELATED_TO),
    ("PDPA:7(b)", "PDPA:7(c)", RELATED_TO),
    ("PDPA:10(a)", "PDPA:10(b)", SUPPORTS),
    ("PDPA:10(b)", "PDPA:10(a)", SUPPORTS),
    ("PDPA:11(a)", "PDPA:11(b)", RELATED_TO),
    ("PDPA:12(1)(a)", "PDPA:12(1)(b)", RELATED_TO),
    ("PDPA:12(1)(a)", "PDPA:12(1)(c)", RELATED_TO),
    ("PDPA:12(1)(a)", "PDPA:12(1)(f)", SUPPORTS),
    ("PDPA:13(1)", "PDPA:14(1)", SUPPORTS),
    ("PDPA:14(1)", "PDPA:14(2)", EXTENDS),
    ("PDPA:16(a)", "PDPA:16(b)", RELATED_TO),
    ("PDPA:16(a)", "PDPA:16(c)", RELATED_TO),
    ("PDPA:16(b)", "PDPA:16(c)", RELATED_TO),
    ("PDPA:9", "PDPA:16(a)", SUPPORTS),
    ("PDPA:6(1)a)", "PDPA:7(a)", EXTENDS),

    # OSA internal relationships
    ("OSA:18(a)", "OSA:18(b)", RELATED_TO),
    ("OSA:18(a)", "OSA:18(c)", RELATED_TO),
    ("OSA:18(b)", "OSA:18(c)", RELATED_TO),
    ("OSA:18(a)", "OSA:20(1)", SUPPORTS),
    ("OSA:19", "OSA:20(1)", SUPPORTS),

    # CCA internal relationships
    ("CCA:3(a)", "CCA:3(b)", RELATED_TO),
    ("CCA:4(a)", "CCA:4(b)", RELATED_TO),
    ("CCA:3(a)", "CCA:4(a)", EXTENDS),
    ("CCA:3(b)", "CCA:4(b)", EXTENDS),
    ("CCA:7(a)", "CCA:7(b)", RELATED_TO),
    ("CCA:7(a)", "CCA:7(c)", RELATED_TO),
    ("CCA:7(b)", "CCA:7(c)", RELATED_TO),
    ("CCA:5", "CCA:3(a)", SUPPORTS),
    ("CCA:10", "CCA:3(a)", SUPPORTS),

    # ETA internal relationships
    ("ETA:12(1)(a)", "ETA:12(1)(b)", RELATED_TO),
    ("ETA:12(1)(a)", "ETA:12(1)(c)", RELATED_TO),
    ("ETA:12(2)(a)", "ETA:12(2)(b)", RELATED_TO),
    ("ETA:7(a)", "ETA:7(b)(ii)", RELATED_TO),
    ("ETA:12(1)(a)", "ETA:12(2)(a)", SUPPORTS),

    # TCA internal relationships
    ("TCA:46B", "TCA:46C", RELATED_TO),
    ("TCA:49(c)", "TCA:52(a)", SUPPORTS),
    ("TCA:52(a)", "TCA:52(d)", EXTENDS),

    # Cross-law references: PDPA ↔ CCA
    ("PDPA:10(a)", "CCA:7(a)", CROSS_LAW_REF),
    ("PDPA:10(b)", "CCA:3(a)", CROSS_LAW_REF),
    ("PDPA:10(a)", "CCA:3(b)", CROSS_LAW_REF),

    # Cross-law references: OSA ↔ CCA
    ("OSA:18(a)", "CCA:4(a)", CROSS_LAW_REF),
    ("OSA:18(b)", "CCA:4(b)", CROSS_LAW_REF),
    ("OSA:20(1)", "CCA:7(a)", CROSS_LAW_REF),

    # Cross-law references: OSA ↔ PDPA
    ("OSA:20(1)", "PDPA:16(a)", CROSS_LAW_REF),
    ("OSA:18(a)", "PDPA:10(a)", CROSS_LAW_REF),
    ("OSA:19", "PDPA:16(a)", CROSS_LAW_REF),

    # Cross-law references: CCA ↔ ETA
    ("CCA:3(a)", "ETA:12(1)(a)", CROSS_LAW_REF),
    ("CCA:4(a)", "ETA:7(a)", CROSS_LAW_REF),

    # Cross-law references: PDPA ↔ RTI
    ("PDPA:13(1)", "RTI:5(1)(a)", CROSS_LAW_REF),

    # Cross-law references: TCA ↔ OSA
    ("TCA:46B", "OSA:18(a)", CROSS_LAW_REF),
    ("TCA:46C", "OSA:18(b)", CROSS_LAW_REF),

    # Cross-law references: TCA ↔ CCA
    ("TCA:52(a)", "CCA:3(a)", CROSS_LAW_REF),
    ("TCA:52(d)", "CCA:4(a)", CROSS_LAW_REF),
]


class ClauseKnowledgeGraph:
    """
    Knowledge graph of legal clause relationships.
    Provides traversal to find supporting and related clauses.
    """

    def __init__(self):
        # Adjacency list: clause_key → list of (target_key, relationship)
        self._adjacency: Dict[ClauseKey, List[Tuple[ClauseKey, str]]] = {}
        self._build_graph()

    def _build_graph(self):
        """Build adjacency list from edge definitions."""
        for source, target, rel_type in _GRAPH_EDGES:
            self._adjacency.setdefault(source, []).append((target, rel_type))
            # Bidirectional for related_to
            if rel_type == RELATED_TO:
                self._adjacency.setdefault(target, []).append((source, rel_type))

    def get_neighbors(
        self,
        clause_key: ClauseKey,
        relationship: Optional[str] = None,
    ) -> List[Tuple[ClauseKey, str]]:
        """
        Get all neighbors of a clause.

        Parameters
        ----------
        clause_key : str
            Key in format "LAW_CODE:Section"
        relationship : str, optional
            Filter by relationship type. If None, return all.

        Returns
        -------
        list of (clause_key, relationship_type)
        """
        neighbors = self._adjacency.get(clause_key, [])
        if relationship:
            return [(k, r) for k, r in neighbors if r == relationship]
        return neighbors

    def get_supporting_clauses(self, clause_key: ClauseKey) -> List[ClauseKey]:
        """Get clauses that support or extend this clause."""
        result = []
        for target, rel in self._adjacency.get(clause_key, []):
            if rel in (SUPPORTS, EXTENDS):
                result.append(target)
        return result

    def get_related_clauses(self, clause_key: ClauseKey) -> List[ClauseKey]:
        """Get clauses related to this clause (any relationship)."""
        return [target for target, _ in self._adjacency.get(clause_key, [])]

    def get_cross_references(self, clause_key: ClauseKey) -> List[ClauseKey]:
        """Get cross-law references from this clause."""
        return [
            target for target, rel in self._adjacency.get(clause_key, [])
            if rel == CROSS_LAW_REF
        ]

    def expand_clauses(
        self,
        primary_clause_keys: List[ClauseKey],
        all_clauses: List[Dict],
        max_supporting: int = 5,
        max_related: int = 3,
    ) -> Dict:
        """
        Expand a set of primary clauses using the knowledge graph.

        Parameters
        ----------
        primary_clause_keys : list[str]
            Keys of the primary/matched clauses.
        all_clauses : list[dict]
            Full clause database for lookups.
        max_supporting : int
            Max supporting clauses to include.
        max_related : int
            Max related clauses to include.

        Returns
        -------
        dict with keys:
            supporting_clauses : list[dict]  — clauses that support the primaries
            related_clauses    : list[dict]  — clauses related to the primaries
            graph_edges        : list[dict]  — relationships used in expansion
        """
        # Build clause lookup
        clause_lookup: Dict[str, Dict] = {}
        for c in all_clauses:
            key = f"{c.get('law_code', '')}:{c.get('section', '')}"
            clause_lookup[key] = c

        primary_set = set(primary_clause_keys)
        supporting_keys: List[ClauseKey] = []
        related_keys: List[ClauseKey] = []
        graph_edges: List[Dict] = []

        for pk in primary_clause_keys:
            for target, rel in self._adjacency.get(pk, []):
                if target in primary_set:
                    continue  # Skip if already a primary clause

                edge = {
                    "source": pk,
                    "target": target,
                    "relationship": rel,
                }

                if rel in (SUPPORTS, EXTENDS):
                    if target not in supporting_keys:
                        supporting_keys.append(target)
                        graph_edges.append(edge)
                else:
                    if target not in related_keys:
                        related_keys.append(target)
                        graph_edges.append(edge)

        # Resolve keys to clause dicts
        supporting_clauses = []
        for key in supporting_keys[:max_supporting]:
            clause = clause_lookup.get(key)
            if clause:
                supporting_clauses.append({
                    **clause,
                    "graph_role": "supporting",
                    "graph_source": next(
                        (e["source"] for e in graph_edges if e["target"] == key),
                        None,
                    ),
                })

        related_clauses = []
        seen_related = set(k for k in supporting_keys)
        for key in related_keys[:max_related]:
            if key in seen_related:
                continue
            clause = clause_lookup.get(key)
            if clause:
                related_clauses.append({
                    **clause,
                    "graph_role": "related",
                    "graph_source": next(
                        (e["source"] for e in graph_edges if e["target"] == key),
                        None,
                    ),
                })

        return {
            "supporting_clauses": supporting_clauses,
            "related_clauses": related_clauses,
            "graph_edges": graph_edges,
        }

    def get_relationship_summary(self, clause_key: ClauseKey) -> str:
        """Get a human-readable summary of a clause's relationships."""
        neighbors = self._adjacency.get(clause_key, [])
        if not neighbors:
            return "No known relationships."

        parts = []
        for target, rel in neighbors:
            rel_label = rel.replace("_", " ")
            parts.append(f"{rel_label} → {target}")
        return "; ".join(parts)
