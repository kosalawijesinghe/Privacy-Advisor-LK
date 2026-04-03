#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to check what clause structure looks like
"""

from modules.legal_knowledge_base import LegalKnowledgeBase

kb = LegalKnowledgeBase()
clauses = kb.clauses[:3]

print("Sample Clause Structure:")
print("=" * 80)
for clause in clauses:
    print(f"Keys: {clause.keys()}")
    print(f"Law Name: {clause.get('law_name', 'MISSING')}")
    print(f"To Upper: {clause.get('law_name', '').upper()}")
    print(f"Section: {clause.get('section', 'MISSING')}")
    print()
