#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Debug script to check incident classification accuracy
"""

import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from modules.pipeline import Pipeline

def test_incidents():
    """Test incident classification on 5 scenarios."""
    
    test_cases = [
        {
            "title": "Test 1: Database Breach",
            "description": "My email and phone number were exposed in a database breach. I'm concerned about identity theft and unauthorized access.",
            "expected": "DATA_EXPOSURE",
            "expected_laws": ["PDPA", "TCA", "CCA"],
        },
        {
            "title": "Test 2: Identity Impersonation",
            "description": "Someone created a fake profile using my photo and personal information online. They're impersonating me and contacting my friends.",
            "expected": "IMPERSONATION",
            "expected_laws": ["OSA", "CCA", "TCA"],
        },
        {
            "title": "Test 3: Identity Theft",
            "description": "My national ID number was used illegally to open accounts and make fraudulent transactions. My credit was damaged.",
            "expected": "IDENTITY_THEFT",
            "expected_laws": ["CCA", "PDPA", "TCA"],
        },
        {
            "title": "Test 4: Harassment",
            "description": "Receiving threatening calls and abusive messages from an unknown number. They're threatening violence and demanding money.",
            "expected": "HARASSMENT",
            "expected_laws": ["OSA", "TCA"],
        },
        {
            "title": "Test 5: Account Takeover",
            "description": "My email account was hacked and compromised. The attacker has access to all my accounts and personal data.",
            "expected": "ACCOUNT_TAKEOVER",
            "expected_laws": ["CCA", "ETA"],
        },
    ]
    
    print("=" * 80)
    print("INCIDENT CLASSIFICATION DEBUG")
    print("=" * 80)
    
    pipeline = Pipeline()
    
    for test in test_cases:
        print(f"\n{test['title']}")
        print("-" * 80)
        
        try:
            # Run just the classification step
            result = pipeline.run(test["description"])
            
            classified = result.get("incident_type", "UNKNOWN")
            clauses = result.get("matched_clauses", [])
            
            # Extract unique laws from clauses
            found_laws = set()
            for clause in clauses[:10]:  # Top 10 clauses
                law = clause.get("law_name", "").upper()
                if law:
                    found_laws.add(law)
            
            print(f"  Expected Classification: {test['expected']}")
            print(f"  Actual Classification:   {classified}")
            print(f"  Match: {'PASS' if classified == test['expected'] else 'FAIL'}")
            print()
            print(f"  Expected Laws: {test['expected_laws']}")
            print(f"  Found Laws:    {sorted(list(found_laws))}")
            print(f"  Coverage:      {len([l for l in test['expected_laws'] if l in found_laws])}/{len(test['expected_laws'])}")
            print()
            print(f"  Top 5 Clauses Retrieved:")
            for i, clause in enumerate(clauses[:5]):
                law = clause.get("law_name", "?").upper()
                score = clause.get("relevance_score", 0)
                section = clause.get("section", "?")
                print(f"    {i+1}. [{law}] {section} (score: {score:.3f})")
        
        except Exception as e:
            print(f"  ERROR: {e}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_incidents()
