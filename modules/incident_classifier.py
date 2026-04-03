"""
Incident Type Classification Layer
====================================
Classifies privacy incidents into categories before clause retrieval,
using TF-IDF + Logistic Regression with fallback to rule-based classification.

Training data: data/training_data.json  (30 labeled samples per class, 210 total)

Incident types:
  DATA_EXPOSURE, IDENTITY_THEFT, IMPERSONATION, DOXXING,
  HARASSMENT, ACCOUNT_TAKEOVER, IMAGE_ABUSE

Output: incident_type, incident_confidence, all_scores, cv_accuracy

OPTIMIZATION: Trained model is cached to disk with training data hash verification.
On subsequent startup, loads cached model and skips 5-fold CV (~7s faster).
"""

import hashlib
import json
import os
import pickle
from typing import Dict, List, Optional

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    from sklearn.pipeline import Pipeline as SKPipeline
    import numpy as np
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False


_TRAINING_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "training_data.json"
)

_MODEL_CACHE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "model_cache")
)
_MODEL_CACHE_PATH = os.path.join(_MODEL_CACHE_DIR, "incident_classifier.pkl")
_CACHE_META_PATH = os.path.join(_MODEL_CACHE_DIR, "incident_classifier_meta.json")


def _load_training_data() -> List[Dict]:
    """Load labeled training samples from data/training_data.json."""
    path = os.path.abspath(_TRAINING_DATA_PATH)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# â”€â”€ Mapping from incident_type to scenario_key for pipeline integration â”€â”€â”€â”€â”€â”€
INCIDENT_TO_SCENARIO: Dict[str, str] = {
    "DATA_EXPOSURE":    "DATA_EXPOSURE",
    "IDENTITY_THEFT":   "IDENTITY_THEFT",
    "IMPERSONATION":    "IDENTITY_IMPERSONATION",
    "DOXXING":          "DOXXING",
    "HARASSMENT":       "HARASSMENT",
    "ACCOUNT_TAKEOVER": "ACCOUNT_TAKEOVER",
    "IMAGE_ABUSE":      "IMAGE_ABUSE",
}

# â”€â”€ Rule-based fallback keywords â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_KEYWORD_RULES: Dict[str, List[str]] = {
    "IDENTITY_THEFT":   ["identity theft", "stolen identity", "NIC used", "fraudulent", "credit fraud", "loan fraud"],
    "IMPERSONATION":    ["fake profile", "impersonat", "pretend", "posing as", "fake account"],
    "DOXXING":          ["doxx", "address posted", "address shared", "personal details published"],
    "HARASSMENT":       ["harass", "threaten", "stalk", "bully", "intimidat", "blackmail"],
    "IMAGE_ABUSE":      ["non consensual image", "intimate image", "deepfake", "revenge porn", "morphed image", "nude"],
    "ACCOUNT_TAKEOVER": ["hack", "unauthorized access", "account taken", "password stolen", "locked out", "hijack"],
    "DATA_EXPOSURE":    ["leak", "breach", "exposed", "data dump", "publicly accessible"],
}


class IncidentClassifier:
    """
    Classifies incidents using TF-IDF + Logistic Regression trained on
    data/training_data.json, with rule-based fallback when sklearn is
    unavailable.

    OPTIMIZATION: Trained model is cached to disk with training data hash.
    Avoids re-running 5-fold CV on every startup.

    Attributes
    ----------
    cv_accuracy : float | None
        Mean 5-fold cross-validation accuracy on the training corpus.
    n_classes : int
        Number of incident classes the model was trained on.
    n_samples : int
        Total number of training samples loaded from JSON.
    """

    def __init__(self):
        self._model = None
        self._is_trained = False
        self.cv_accuracy: Optional[float] = None
        self.n_classes: int = 0
        self.n_samples: int = 0
        if _HAS_SKLEARN:
            self._train()

    @staticmethod
    def _hash_training_data() -> str:
        """Generate SHA256 hash of training data for cache validation."""
        try:
            with open(os.path.abspath(_TRAINING_DATA_PATH), "r", encoding="utf-8") as f:
                data = f.read()
            return hashlib.sha256(data.encode()).hexdigest()
        except Exception:
            return ""

    def _load_cached_model(self) -> bool:
        """Load model from cache if it exists and training data hasn't changed."""
        if not os.path.exists(_MODEL_CACHE_PATH) or not os.path.exists(_CACHE_META_PATH):
            return False
        
        try:
            with open(_CACHE_META_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
            
            current_hash = self._hash_training_data()
            if meta.get("data_hash") != current_hash:
                return False  # Training data changed, need to retrain
            
            with open(_MODEL_CACHE_PATH, "rb") as f:
                cached_data = pickle.load(f)
            
            self._model = cached_data.get("model")
            self.cv_accuracy = cached_data.get("cv_accuracy")
            self.n_classes = cached_data.get("n_classes")
            self.n_samples = cached_data.get("n_samples")
            self._is_trained = self._model is not None
            
            if self._is_trained:
                print(
                    f"[IncidentClassifier] Loaded cached model (CV accuracy: {self.cv_accuracy:.3f}, "
                    f"n={self.n_samples} samples, {self.n_classes} classes)"
                )
            return self._is_trained
        except Exception:
            return False

    def _save_model(self):
        """Save trained model to cache for faster startup on next run."""
        try:
            os.makedirs(_MODEL_CACHE_DIR, exist_ok=True)
            
            with open(_MODEL_CACHE_PATH, "wb") as f:
                pickle.dump({
                    "model": self._model,
                    "cv_accuracy": self.cv_accuracy,
                    "n_classes": self.n_classes,
                    "n_samples": self.n_samples,
                }, f)
            
            with open(_CACHE_META_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "data_hash": self._hash_training_data(),
                }, f)
        except Exception:
            pass  # Silently fail on cache save

    def _train(self):
        """Load training_data.json, fit TF-IDF + LR pipeline, compute CV accuracy.
        
        OPTIMIZATION: First attempts to load cached model. If cache is valid,
        skips CV and returns immediately (~7s faster). Only runs CV if training
        data has changed or cache is missing.
        """
        # Try to load cached model first
        if self._load_cached_model():
            return
        
        records = _load_training_data()
        texts  = [r.get("description") or r.get("text") for r in records]
        labels = [r.get("incident_type") or r.get("label") for r in records]
        
        # Filter out records with missing text or labels
        texts, labels = zip(*[(t, l) for t, l in zip(texts, labels) if t and l])
        texts, labels = list(texts), list(labels)

        self.n_samples = len(texts)
        self.n_classes = len(set(labels))

        self._model = SKPipeline([
            ("tfidf", TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                stop_words="english",
            )),
            ("clf", LogisticRegression(
                max_iter=1000,
                C=1.0,
                class_weight='balanced',
                random_state=42,
            )),
        ])

        # Stratified 5-fold cross-validation (maintains class distribution in each fold)
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(self._model, texts, labels, cv=skf, scoring="accuracy")
        self.cv_accuracy = round(float(np.mean(cv_scores)), 4)

        print(
            f"[IncidentClassifier] CV accuracy: {self.cv_accuracy:.3f} "
            f"\u00b1 {np.std(cv_scores):.3f}  "
            f"(n={self.n_samples} samples, {self.n_classes} classes)"
        )

        # Final fit on full dataset
        self._model.fit(texts, labels)
        self._is_trained = True
        
        # Save to cache for next startup
        self._save_model()

    def classify(
        self,
        text: str,
        tags: Optional[List[str]] = None,
    ) -> Dict:
        """
        Classify the incident type from text and optional tags.

        Returns
        -------
        dict with keys:
            incident_type       : str
            incident_confidence : float (0-1)
            all_scores          : dict[str, float]  probability per class
            cv_accuracy         : float | None      training CV accuracy
        """
        if not text or not text.strip():
            return self._from_tags(tags or [])

        input_text = text.strip()
        if tags:
            input_text = f"{input_text} {' '.join(tags)}"

        if self._is_trained and self._model is not None:
            return self._ml_classify(input_text)

        return self._rule_classify(input_text, tags)

    def _ml_classify(self, text: str) -> Dict:
        """Use the trained ML model for classification."""
        probas  = self._model.predict_proba([text])[0]
        classes = self._model.classes_
        scores  = {cls: float(prob) for cls, prob in zip(classes, probas)}
        best_idx = int(np.argmax(probas))
        return {
            "incident_type":       classes[best_idx],
            "incident_confidence": round(float(probas[best_idx]), 4),
            "all_scores":          {k: round(v, 4) for k, v in scores.items()},
            "cv_accuracy":         self.cv_accuracy,
        }

    def _rule_classify(self, text: str, tags: Optional[List[str]] = None) -> Dict:
        """Rule-based fallback using keyword matching."""
        text_lower = text.lower()
        scores: Dict[str, float] = {}

        for incident_type, keywords in _KEYWORD_RULES.items():
            matches = sum(1 for kw in keywords if kw.lower() in text_lower)
            scores[incident_type] = matches / max(len(keywords), 1)

        if not any(scores.values()):
            return self._from_tags(tags or [])

        best_type  = max(scores, key=scores.get)
        best_score = scores[best_type]
        return {
            "incident_type":       best_type,
            "incident_confidence": round(min(1.0, best_score * 1.5), 4),
            "all_scores":          {k: round(v, 4) for k, v in scores.items()},
            "cv_accuracy":         None,
        }

    def _from_tags(self, tags: List[str]) -> Dict:
        """Classify based solely on tags when no text is available."""
        tag_set = set(tags)
        if "impersonate" in tag_set:
            return {"incident_type": "IMPERSONATION",    "incident_confidence": 0.75, "all_scores": {}, "cv_accuracy": None}
        if "img_exposed" in tag_set:
            return {"incident_type": "IMAGE_ABUSE",      "incident_confidence": 0.65, "all_scores": {}, "cv_accuracy": None}
        if tag_set & {"username", "email"} and tag_set & {"phone"}:
            return {"incident_type": "ACCOUNT_TAKEOVER", "incident_confidence": 0.55, "all_scores": {}, "cv_accuracy": None}
        if "id" in tag_set:
            return {"incident_type": "IDENTITY_THEFT",   "incident_confidence": 0.55, "all_scores": {}, "cv_accuracy": None}
        if tag_set & {"addr", "location"} and tag_set & {"name", "phone"}:
            return {"incident_type": "DOXXING",           "incident_confidence": 0.50, "all_scores": {}, "cv_accuracy": None}
        return     {"incident_type": "DATA_EXPOSURE",    "incident_confidence": 0.40, "all_scores": {}, "cv_accuracy": None}
