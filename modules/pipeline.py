"""
Pipeline Orchestrator
======================
Connects all modules into a semantic-driven analysis pipeline.
Uses embedding-based retrieval and cross-encoder re-ranking for clause matching.

Flow:
  User Input
    → Input Validation
    → Incident Classification
    → Scenario Builder
    → Severity Analysis (with PII risk weighting)
    → Multi-Embedding Retrieval + Cross-Encoder Re-Ranking
    → Semantic Relevance Scoring
    → Semantic Applicability Validation
    → Confidence Calibration
    → Clause Filtering
    → Knowledge Graph Expansion
    → Explanation Generator
    → Recommendation Engine
    → Compliance Alert
"""

from typing import Dict, List
import threading

from modules.input_validator import InputValidator
from modules.scenario_builder import ScenarioBuilder
from modules.severity_analyzer import SeverityAnalyzer
from modules.legal_knowledge_base import LegalKnowledgeBase
from modules.relevance_scorer import RelevanceScorer, ConfidenceCalibrator
from modules.clause_filter import ClauseFilter
from modules.explanation_generator import ExplanationGenerator
from modules.recommendation_engine import RecommendationEngine
from modules.system_logger import SystemLogger
from modules.semantic_vectorizer import SemanticVectorizer
from modules.incident_classifier import IncidentClassifier, INCIDENT_TO_SCENARIO
from modules.two_stage_retriever import TwoStageRetriever, CrossEncoderReranker
from modules.clause_knowledge_graph import ClauseKnowledgeGraph
from modules.embedding_manager import MultiEmbeddingIndex, PrecomputedEmbeddingStore
from modules.pii_risk_weighter import PIIRiskWeighter
from modules.legal_reasoning_validator import LegalReasoningValidator
from modules.incident_law_mapper import get_incident_law_mapper
from modules.incident_type_mapper import IncidentTypeMapper  # ✅ Fix incident classifier
from modules.keyword_clause_booster import KeywordClauseBooster  # ✅ Keyword-based boosting
from modules.ensemble_retriever import EnsembleRetriever  # ✅ Ensemble retrieval

try:
    from modules.compliance_alert import ComplianceAlert as _ComplianceAlert
except Exception:
    _ComplianceAlert = None




class Pipeline:
    """
    End-to-end analysis pipeline.
    Call ``run()`` with raw user inputs and receive a complete result dict.
    """

    def __init__(self):
        # Shared vectorizer instance (loaded once)
        self._vectorizer = SemanticVectorizer()
        self._knowledge_base = LegalKnowledgeBase()

        # ── Core modules ──
        self.validator = InputValidator()
        self.scenario_builder = ScenarioBuilder()
        self.severity_analyzer = SeverityAnalyzer()
        self.relevance_scorer = RelevanceScorer()
        self.clause_filter = ClauseFilter()
        self.explanation_generator = ExplanationGenerator()
        self.recommendation_engine = RecommendationEngine()
        self.logger = SystemLogger()

        # ── Semantic & classification modules ──
        self.incident_classifier = IncidentClassifier()
        self.multi_embedding = MultiEmbeddingIndex(self._vectorizer)
        self.cross_encoder = CrossEncoderReranker(vectorizer=self._vectorizer)
        self.two_stage_retriever = TwoStageRetriever(
            vectorizer=self._vectorizer,
            knowledge_base=self._knowledge_base,
            multi_embedding_index=self.multi_embedding,
            cross_encoder_reranker=self.cross_encoder,
        )
        self.knowledge_graph = ClauseKnowledgeGraph()
        self.pii_risk_weighter = PIIRiskWeighter()
        self.reasoning_validator = LegalReasoningValidator()
        self.incident_law_mapper = get_incident_law_mapper()  # ✅ For incident-specific law boosting
        self.incident_type_mapper = IncidentTypeMapper()  # ✅ Fix incident classifier mismatch
        self.keyword_booster = KeywordClauseBooster()  # ✅ Keyword-based clause boosting
        self.ensemble_retriever = EnsembleRetriever(self._vectorizer)  # ✅ Ensemble retrieval
        self.confidence_calibrator = ConfidenceCalibrator()
        self.embedding_store = PrecomputedEmbeddingStore(self._vectorizer)
        self._embeddings_ready = False
        self._embeddings_building = False
        self._embeddings_lock = threading.Lock()
        self._embeddings_event = threading.Event()
        self._try_load_embeddings()
        self._start_embedding_build()

        # ── Optional enhancement modules (graceful fallback) ──
        self.alert_generator = None

        if _ComplianceAlert is not None:
            try:
                self.alert_generator = _ComplianceAlert()
            except Exception:
                self.alert_generator = None

    def _try_load_embeddings(self):
        """Try to load cached embeddings without blocking startup."""
        try:
            clauses = self._knowledge_base.clauses
            loaded_store = self.embedding_store.load(clauses)
            loaded_multi = self.multi_embedding.load(clauses)
            self._embeddings_ready = loaded_store and loaded_multi
            if self._embeddings_ready:
                self._embeddings_event.set()
        except Exception:
            self._embeddings_ready = False

    def _start_embedding_build(self):
        """Warm embeddings in the background if cache is missing."""
        if self._embeddings_ready:
            return
        with self._embeddings_lock:
            if self._embeddings_building or self._embeddings_ready:
                return
            self._embeddings_building = True

        def _worker():
            try:
                self._build_embeddings()
            finally:
                self._embeddings_event.set()
                with self._embeddings_lock:
                    self._embeddings_building = False

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def _build_embeddings(self):
        """Build and cache embeddings (called by background worker or on demand)."""
        try:
            clauses = self._knowledge_base.clauses
            if not self.embedding_store.load(clauses):
                self.embedding_store.build(clauses)
                self.embedding_store.save()
            if not self.multi_embedding.load(clauses):
                self.multi_embedding.build(clauses)
                self.multi_embedding.save()
            self._embeddings_ready = True
        except Exception:
            self._embeddings_ready = False

    def _ensure_embeddings(self):
        """Build and cache embeddings on first use if not already ready."""
        if self._embeddings_ready:
            return
        if self._embeddings_building:
            self._embeddings_event.wait()
            return
        self._build_embeddings()

    @property
    def model_name(self) -> str:
        return self._vectorizer.model_name

    def run(
        self,
        tags: List[str],
        impersonate: bool = False,
        img_exposed: bool = False,
        platform: str = "",
        description: str = "",
    ) -> Dict:
        """
        Execute the full analysis pipeline.

        Pipeline Flow:
          1. Input Validation
          2. Incident Classification
          3. Scenario Builder
          4. Severity Analysis (with PII risk weighting)
          5. Multi-Embedding Retrieval + Cross-Encoder Re-Ranking
          6. Semantic Relevance Scoring
          7. Semantic Applicability Validation
          8. Confidence Calibration
          9. Clause Filtering
          10. Knowledge Graph Expansion
          11. Explanation Generation
          12. Recommendation Engine
          13. Logging + Compliance Alert

        Returns
        -------
        dict with keys:
            valid, warnings, validated_input, scenario, severity,
            matched_clauses, supporting_clauses, related_clauses,
            clauses_by_law, recommendations, model_name, scenario_key,
            detected_scenarios, incident_classification, pii_risk,
            compliance_alert
        """
        # ══════════════════════════════════════════════════════════════════
        # STEP 1: Input Validation
        # ══════════════════════════════════════════════════════════════════
        validated = self.validator.validate(
            tags=list(tags),
            impersonate=impersonate,
            img_exposed=img_exposed,
            platform=platform,
        )

        _empty_result = {
            "valid": False,
            "warnings": validated["warnings"],
            "validated_input": validated,
            "scenario": {},
            "severity": {"score": 0, "level": "Low", "color": "#22c55e", "contributors": []},
            "matched_clauses": [],
            "supporting_clauses": [],
            "related_clauses": [],
            "clauses_by_law": {},
            "recommendations": [],
            "model_name": self.model_name,
            "scenario_key": "DATA_EXPOSURE",
            "detected_scenarios": [],
            "incident_classification": {},
            "pii_risk": {},
            "compliance_alert": {},
        }

        if not validated["is_valid"]:
            return _empty_result

        # ══════════════════════════════════════════════════════════════════
        # STEP 2: Incident Classification
        # ══════════════════════════════════════════════════════════════════
        incident_classification = self.incident_classifier.classify(
            text=description,
            tags=validated["normalized_tags"],
        )
        incident_type = incident_classification.get("incident_type", "DATA_EXPOSURE")
        
        # ✅ IMPROVEMENT 1: Normalize incident type (fix classifier mismatch)
        incident_type = self.incident_type_mapper.normalize(incident_type)

        # ══════════════════════════════════════════════════════════════════
        # STEP 3: Scenario Builder
        # ══════════════════════════════════════════════════════════════════
        scenario = self.scenario_builder.build_scenario(validated, user_description=description)
        detected_scenarios = scenario.get("detected_scenarios", [])

        # Enrich detected scenarios with incident classification
        mapped_scenario = INCIDENT_TO_SCENARIO.get(incident_type)
        if mapped_scenario:
            inc_conf = incident_classification.get("incident_confidence", 0.5)
            # The ML classifier analyzes the description text, so give it
            # priority over tag-based rules when confidence is reasonable.
            classifier_confidence = max(inc_conf, 0.80)
            existing = [s for s in detected_scenarios if s["key"] == mapped_scenario]
            if existing:
                # Upgrade confidence if the classifier is more confident
                existing[0]["confidence"] = max(existing[0]["confidence"], classifier_confidence)
            else:
                detected_scenarios.append({
                    "key": mapped_scenario,
                    "confidence": classifier_confidence,
                })

        # Also add runner-up classifications so their expert clauses
        # are considered even when the top-1 prediction is wrong.
        all_scores = incident_classification.get("all_scores", {})
        top_score = max(all_scores.values()) if all_scores else 0
        _existing_keys = {s["key"] for s in detected_scenarios}
        for itype_str, score in all_scores.items():
            if score >= top_score * 0.50:
                alt_scenario = INCIDENT_TO_SCENARIO.get(str(itype_str))
                if alt_scenario and alt_scenario not in _existing_keys:
                    detected_scenarios.append({
                        "key": alt_scenario,
                        "confidence": float(score),
                    })
                    _existing_keys.add(alt_scenario)

        detected_scenarios.sort(key=lambda s: s["confidence"], reverse=True)

        scenario_key = detected_scenarios[0]["key"]
        all_scenario_keys = [s["key"] for s in detected_scenarios]

        # ══════════════════════════════════════════════════════════════════
        # STEP 4: Severity Analysis (with PII risk weighting)
        # ══════════════════════════════════════════════════════════════════
        severity = self.severity_analyzer.analyze(validated)
        pii_risk = self.pii_risk_weighter.compute_aggregate_risk(validated["normalized_tags"])

        # Apply PII risk to severity
        severity["score"] = self.pii_risk_weighter.apply_to_severity(
            severity["score"], validated["normalized_tags"]
        )
        severity["normalized"] = round(severity["score"] / 100.0, 2)
        severity["pii_risk"] = pii_risk

        # ══════════════════════════════════════════════════════════════════
        # STEP 5: Multi-Embedding Retrieval + Cross-Encoder Re-Ranking
        # ══════════════════════════════════════════════════════════════════
        self._ensure_embeddings()
        two_stage_results = self.two_stage_retriever.retrieve(
            scenario_description=scenario["scenario_description"],
            user_tags=validated["normalized_tags"],
            incident_type=incident_type,
            scenario_keys=all_scenario_keys,
        )

        # ══════════════════════════════════════════════════════════════════
        # STEP 6: Semantic Relevance Scoring
        # ══════════════════════════════════════════════════════════════════
        scored = self.relevance_scorer.score(
            two_stage_results,
            scenario_key=scenario_key,
            severity_score=severity.get("normalized", 0.0),
            user_tags=validated["normalized_tags"],
            all_scenario_keys=all_scenario_keys,
        )

        # Apply PII risk boost to clause ranking
        for clause in scored:
            pii_boost = self.pii_risk_weighter.get_clause_ranking_boost(
                clause, validated["normalized_tags"]
            )
            clause["relevance_score"] = min(1.0, clause["relevance_score"] + pii_boost)
        
        # ✅ IMPROVEMENT 2: Apply keyword-based clause boosting
        scored = self.keyword_booster.boost_clauses_by_keywords(
            scored, scenario["scenario_description"]
        )
        scored = self.keyword_booster.boost_for_incident_type(
            scored, incident_type
        )

        # ✅ IMPROVEMENT 3: Optional - Try ensemble retrieval for additional candidates
        try:
            ensemble_results = self.ensemble_retriever.ensemble_retrieve(
                scenario_text=scenario["scenario_description"],
                clauses=self._knowledge_base.clauses,
                user_tags=validated["normalized_tags"],
                top_k=5,
            )
            # Add ensemble results to scored list (avoiding duplicates)
            ensemble_ids = {e.get("id") for e in ensemble_results}
            scored_ids = {s.get("id") for s in scored}
            for ensemble_clause in ensemble_results:
                if ensemble_clause.get("id") not in scored_ids:
                    ensemble_clause["relevance_score"] = ensemble_clause.get("ensemble_score", 0.5) * 0.8
                    scored.append(ensemble_clause)
            # Re-sort after adding ensemble results
            scored.sort(key=lambda r: r["relevance_score"], reverse=True)
        except Exception:
            pass  # Ensemble is optional enhancement, don't break pipeline

        # ══════════════════════════════════════════════════════════════════
        # STEP 7: Semantic Applicability Validation
        # ══════════════════════════════════════════════════════════════════
        validated_clauses = self.reasoning_validator.validate(
            clauses=scored,
            scenario_text=scenario["scenario_description"],
            scenario_key=scenario_key,
            user_tags=validated["normalized_tags"],
        )

        # Filter out weak clauses (keep Direct and Partial)
        all_validated = validated_clauses
        validated_clauses = self.reasoning_validator.filter_weak_clauses(
            all_validated, min_applicability="Partial"
        )

        # Rescue PRIMARY clauses that the weak-filter removed —
        # they are expert-mapped and must reach the clause filter.
        from modules.relevance_matrix import PRIMARY as _PRI, clause_key as _ck
        _retained = {_ck(c.get("law_code", ""), c.get("section", ""))
                     for c in validated_clauses}
        _expert_pri: set = set()
        for _sk in all_scenario_keys:
            _expert_pri |= _PRI.get(_sk, frozenset())
        for c in all_validated:
            ck = _ck(c.get("law_code", ""), c.get("section", ""))
            if ck not in _retained and ck in _expert_pri:
                validated_clauses.append(c)
                _retained.add(ck)

        # ══════════════════════════════════════════════════════════════════
        # STEP 8: Confidence Calibration
        # ══════════════════════════════════════════════════════════════════
        calibrated = self.confidence_calibrator.calibrate(
            clauses=validated_clauses,
            user_tags=validated["normalized_tags"],
            incident_type=incident_type,
        )

        # ══════════════════════════════════════════════════════════════════
        # STEP 9: Clause Filtering
        # ══════════════════════════════════════════════════════════════════
        filtered = self.clause_filter.filter(
            calibrated,
            user_tags=validated["normalized_tags"],
            scenario_key=scenario_key,
            n_scenarios=len(detected_scenarios),
            severity_level=severity["level"],
            all_scenario_keys=all_scenario_keys,
        )

        # ══════════════════════════════════════════════════════════════════
        # STEP 10: Clause Knowledge Graph Expansion
        # ══════════════════════════════════════════════════════════════════
        primary_keys = [
            f"{c.get('law_code', '')}:{c.get('section', '')}"
            for c in filtered
        ]
        graph_expansion = self.knowledge_graph.expand_clauses(
            primary_clause_keys=primary_keys,
            all_clauses=self._knowledge_base.clauses,
        )
        supporting_clauses = graph_expansion.get("supporting_clauses", [])
        related_clauses = graph_expansion.get("related_clauses", [])

        # ══════════════════════════════════════════════════════════════════
        # STEP 11: Explanation Generation
        # ══════════════════════════════════════════════════════════════════
        explained = self.explanation_generator.generate(
            filtered,
            user_tags=validated["normalized_tags"],
            scenario_key=scenario_key,
            impersonate=validated["impersonate"],
            img_exposed=validated["img_exposed"],
        )

        # ══════════════════════════════════════════════════════════════════
        # STEP 12: Recommendations
        # ══════════════════════════════════════════════════════════════════
        recommendations = self.recommendation_engine.generate(
            validated_input=validated,
            scenario_key=scenario_key,
            severity_level=severity["level"],
            matched_clauses=explained,
        )

        # Escalate recommendation priorities based on PII risk
        if self.pii_risk_weighter.get_recommendation_priority_boost(
            validated["normalized_tags"]
        ) == "ESCALATE":
            _PRIORITY_UP = {"HIGH": "URGENT", "MEDIUM": "HIGH", "LOW": "MEDIUM"}
            for rec in recommendations:
                rec["priority"] = _PRIORITY_UP.get(rec["priority"], rec["priority"])

        # ══════════════════════════════════════════════════════════════════
        # STEP 13: Logging + Compliance Alert
        # ══════════════════════════════════════════════════════════════════
        self.logger.log_analysis(
            validated_input=validated,
            scenario=scenario,
            severity=severity,
            matched_clauses=explained,
            model_name=self.model_name,
            recommendations=recommendations,
        )

        # ── Compliance Alert ──
        compliance_alert = {}
        if self.alert_generator:
            try:
                _partial = {
                    "valid": True,
                    "severity": severity,
                    "matched_clauses": explained,
                    "recommendations": recommendations,
                    "detected_scenarios": detected_scenarios,
                    "validated_input": validated,
                }
                compliance_alert = self.alert_generator.generate(_partial)
            except Exception:
                pass

        # ── Group by law ──
        clauses_by_law = self.clause_filter.group_by_law(explained)

        return {
            "valid": True,
            "warnings": validated["warnings"],
            "validated_input": validated,
            "scenario": scenario,
            "severity": severity,
            "matched_clauses": explained,
            "supporting_clauses": supporting_clauses,
            "related_clauses": related_clauses,
            "clauses_by_law": clauses_by_law,
            "recommendations": recommendations,
            "model_name": self.model_name,
            "scenario_key": scenario_key,
            "detected_scenarios": detected_scenarios,
            "incident_classification": incident_classification,
            "pii_risk": pii_risk,
            "compliance_alert": compliance_alert,
        }


