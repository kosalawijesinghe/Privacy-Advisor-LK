# Privacy Compliance Advisor - Sri Lanka

A privacy risk advisor for Sri Lankan citizens that maps personal data exposures to applicable laws and provides actionable recommendations.

## Features
- **Severity Scoring:** Calculates a privacy risk score (0-100) based on exposed PII tags.
- **Legal Mapping:** Maps incidents to Sri Lankan laws — PDPA, CCA, OSA, ETA, TCA, RTI.
- **Recommendations:** Provides prioritised, actionable steps to mitigate risk.
- **Explainability:** Explains why each clause applies and which tags triggered it.
- **Tabbed UI:** Results split across Overview, Legal Clauses, Recommendations, and Details tabs.

## Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Application:**
   ```bash
   streamlit run app.py
   ```

## Modules
- `modules/pipeline.py`: 13-step end-to-end orchestrator.
- `modules/input_validator.py`: Validates and normalises user inputs.
- `modules/incident_classifier.py`: Incident type classification (TF-IDF + Logistic Regression).
- `modules/scenario_builder.py`: Detects incident scenarios and synthesises semantic scenario text.
- `modules/severity_analyzer.py`: Computes severity score (0-100).
- `modules/pii_risk_weighter.py`: PII-specific risk weighting applied to the severity score.
- `modules/semantic_vectorizer.py`: SBERT / TF-IDF / token-overlap embedding engine.
- `modules/embedding_manager.py`: Multi-model embedding index (`MultiEmbeddingIndex` + `PrecomputedEmbeddingStore`) with cosine retrieval and precomputed cache.
- `modules/two_stage_retriever.py`: Two-stage retriever — Stage 1: multi-embedding retrieval; Stage 2: `CrossEncoderReranker` re-ranking.
- `modules/relevance_scorer.py`: Multi-signal semantic relevance scoring and `ConfidenceCalibrator`.
- `modules/legal_reasoning_validator.py`: Semantic applicability validation (Direct / Partial / Weak).
- `modules/clause_filter.py`: Adaptive top-N clause filtering with semantic score gate and law-diversity preservation.
- `modules/clause_knowledge_graph.py`: Legal relationship graph for supporting/related clause expansion.
- `modules/relevance_matrix.py`: Tag-to-clause coverage index (used in UI Data Coverage tab).
- `modules/explanation_generator.py`: Generates clause-specific legal explanations.
- `modules/recommendation_engine.py`: Generates prioritised recommendations with inline explainability.
- `modules/legal_knowledge_base.py`: Loads and indexes legal clause data from JSON.
- `modules/compliance_alert.py`: Generates structured compliance alert payloads.
- `modules/system_logger.py`: Logs analysis sessions to `data/analysis_log.jsonl`.

## Data
- `data/legal_clauses.json`: **70 legal clauses** across 6 Sri Lankan acts — PDPA (31), ETA (11), TCA (11), CCA (9), OSA (6), RTI (2).
- `data/config.json`: Runtime configuration (weights, thresholds, top-N caps).
- `data/embedding_cache/`: Precomputed corpus embeddings; auto-rebuilt when clause count changes.
