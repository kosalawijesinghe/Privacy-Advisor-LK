#!/usr/bin/env python
"""Profile initialization times for each major module."""

import time
import sys

print("Profiling module initialization...")
print("=" * 60)

start = time.time()
from modules.semantic_vectorizer import SemanticVectorizer
print(f"SemanticVectorizer import:        {time.time()-start:6.2f}s")

start = time.time()
from modules.incident_classifier import IncidentClassifier
print(f"IncidentClassifier import:        {time.time()-start:6.2f}s")

start = time.time()
ic = IncidentClassifier()
print(f"IncidentClassifier init:          {time.time()-start:6.2f}s")

start = time.time()
sv = SemanticVectorizer()
print(f"SemanticVectorizer init:          {time.time()-start:6.2f}s")

start = time.time()
from modules.two_stage_retriever import CrossEncoderReranker
print(f"CrossEncoderReranker import:      {time.time()-start:6.2f}s")

start = time.time()
cer = CrossEncoderReranker(vectorizer=sv)
print(f"CrossEncoderReranker init (lazy): {time.time()-start:6.2f}s")

start = time.time()
from modules.legal_knowledge_base import LegalKnowledgeBase
lkb = LegalKnowledgeBase()
print(f"LegalKnowledgeBase init:          {time.time()-start:6.2f}s")

start = time.time()
from modules.embedding_manager import MultiEmbeddingIndex
mei = MultiEmbeddingIndex(sv)
print(f"MultiEmbeddingIndex init:         {time.time()-start:6.2f}s")

start = time.time()
from modules.embedding_manager import PrecomputedEmbeddingStore
pes = PrecomputedEmbeddingStore(sv)
print(f"PrecomputedEmbeddingStore init:   {time.time()-start:6.2f}s")

print("=" * 60)

start = time.time()
from modules.pipeline import Pipeline
p = Pipeline()
print(f"Full Pipeline init:               {time.time()-start:6.2f}s")
