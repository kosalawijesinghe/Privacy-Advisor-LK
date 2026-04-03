#!/usr/bin/env python
# Check law_code field
from modules.legal_knowledge_base import LegalKnowledgeBase

kb = LegalKnowledgeBase()
clauses = kb.clauses[:10]

print("Law Code Analysis:")
print("=" * 80)
for clause in clauses:
    law_name = clause.get('law_name', '')
    law_code = clause.get('law_code', '')
    print(f"Name: {law_name[:40]:<40} | Code: {law_code}")

# Create mapping from law codes
law_codes = set()
for clause in kb.clauses:
    law_codes.add(clause.get('law_code', ''))

print("\nUnique Law Codes:")
for code in sorted(law_codes):
    print(f"  {code}")
