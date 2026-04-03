#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Debug the incident classification and law mapping
"""

import sys
import io

# Fix encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from modules.incident_classifier import IncidentClassifier
from modules.incident_law_mapper import get_incident_law_mapper

classifier = IncidentClassifier()
mapper = get_incident_law_mapper()

test_cases = [
    ("Harassment Case", "Receiving threatening calls and messages from unknown number"),
    ("Account Takeover", "My email account was hacked and attacker has full access"),
]

print("Testing Incident Classification and Law Mapping:")
print("=" * 80)

for title, text in test_cases:
    print(f"\n{title}:")
    print(f"  Input: {text[:60]}...")
    
    # Classify
    result = classifier.classify(text)
    incident_type = result.get("predicted_class", "UNKNOWN")
    confidence = result.get("confidence", 0.0)
    
    print(f"  Classification: {incident_type} (confidence: {confidence:.2f})")
    
    # Get expected laws
    laws = mapper.get_expected_laws(incident_type)
    print(f"  Expected Laws: {laws}")
    
    # Show mapping summary
    print(f"  Mapping Summary:")
    print(f"    {mapper.summarize_mapping(incident_type)}")

print("\n" + "=" * 80)
