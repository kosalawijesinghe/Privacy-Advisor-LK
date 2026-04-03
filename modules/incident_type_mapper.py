"""
Incident Type Classifier Fix - Mapping Layer
==============================================
Maps training data incident types to pipeline incident types.
Fixes the mismatch between training data and pipeline classifications.

Training data types: personal_data_breach, unauthorized_access, telecommunications, etc.
Pipeline types: DATA_EXPOSURE, ACCOUNT_TAKEOVER, IDENTITY_THEFT, etc.
"""

from typing import Dict, Optional


class IncidentTypeMapper:
    """Convert between training data and pipeline incident types."""

    # Training data types → Pipeline types
    TRAINING_TO_PIPELINE = {
        "personal_data_breach": "DATA_EXPOSURE",
        "unauthorized_access": "ACCOUNT_TAKEOVER",
        "telecommunications": "HARASSMENT",  # Telecom harassment
        "electronic_transactions": "ACCOUNT_TAKEOVER",
        "right_to_information": "DOXXING",  # Information disclosure
        "harassment": "HARASSMENT",
    }

    # Reverse mapping
    PIPELINE_TO_TRAINING = {v: k for k, v in TRAINING_TO_PIPELINE.items()}

    @staticmethod
    def to_pipeline(training_type: str) -> str:
        """Convert training type to pipeline type."""
        training_type = training_type.lower().strip() if training_type else ""
        return (
            IncidentTypeMapper.TRAINING_TO_PIPELINE.get(training_type, training_type)
            or "UNKNOWN"
        )

    @staticmethod
    def to_training(pipeline_type: str) -> str:
        """Convert pipeline type to training type."""
        pipeline_type = pipeline_type.upper().strip() if pipeline_type else ""
        return (
            IncidentTypeMapper.PIPELINE_TO_TRAINING.get(pipeline_type, pipeline_type)
            or "unknown"
        )

    @staticmethod
    def normalize(incident_type: str) -> str:
        """Normalize to standardized pipeline type, trying both directions."""
        if not incident_type:
            return "UNKNOWN"

        incident_type = incident_type.strip()

        # Try as training type first
        if incident_type.lower() in IncidentTypeMapper.TRAINING_TO_PIPELINE:
            return IncidentTypeMapper.to_pipeline(incident_type)

        # Try as pipeline type
        if incident_type.upper() in IncidentTypeMapper.PIPELINE_TO_TRAINING:
            return incident_type.upper()

        # Return as-is if unknown
        return incident_type.upper()
