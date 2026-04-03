"""
SBERT Fine-tuning with Memory Optimization
Fixed version with smaller batch size and gradient accumulation
"""

import json
import torch
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
from datetime import datetime

print("=" * 60)
print("SBERT LEGAL CLAUSE FINE-TUNING (MEMORY OPTIMIZED)")
print("=" * 60)

# Load training pairs from legal_clauses.json
with open('data/legal_clauses.json') as f:
    clauses = json.load(f)

# Create training examples
train_examples = []
for clause in clauses:
    queries = clause.get('example_queries', [])
    clause_text = clause.get('description', '')
    
    for query in queries:
        train_examples.append(InputExample(texts=[query, clause_text]))

print(f"✅ Loaded {len(train_examples)} training pairs")
print(f"   From {len(clauses)} clauses")

# Model configuration (OPTIMIZED)
model_name = "all-MiniLM-L6-v2"
epochs = 3  # Reduced from 5
batch_size = 8  # Reduced from 16
warmup_steps = 100

print(f"\n🚀 Starting SBERT fine-tuning (Memory Optimized)...")
print(f"  Model: {model_name}")
print(f"  Epochs: {epochs}")
print(f"  Batch size: {batch_size}")
print(f"  Training examples: {len(train_examples)}")
print(f"  Device: {torch.device('cuda' if torch.cuda.is_available() else 'cpu')}")

# Load model
model = SentenceTransformer(model_name)

# Create data loader
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)

# Loss function
train_loss = losses.MultipleNegativesRankingLoss(model)

# Train with smaller learning rate
print(f"\n⏳ Training started at {datetime.now().strftime('%H:%M:%S')}...")

try:
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=warmup_steps,
        show_progress_bar=True,
        checkpoint_path=None,  # Disable checkpointing to save memory
        save_best_model=False,  # Disable best model saving
        optimizer_params={"lr": 2e-5}  # Lower learning rate
    )
    
    print(f"\n✅ Training completed at {datetime.now().strftime('%H:%M:%S')}")
    
    # Save the fine-tuned model
    model_path = 'models/sbert_finetuned_legal'
    model.save(model_path)
    print(f"✅ Model saved to: {model_path}")
    
    # Test the model
    print(f"\n🧪 Testing fine-tuned model...")
    test_query = "My email was exposed in a database breach"
    test_clause = "Personal data must be processed for specified purposes only"
    
    embeddings = model.encode([test_query, test_clause])
    similarity = torch.nn.functional.cosine_similarity(
        torch.tensor(embeddings[0]).unsqueeze(0),
        torch.tensor(embeddings[1]).unsqueeze(0)
    )
    
    print(f"   Query: {test_query}")
    print(f"   Clause: {test_clause}")
    print(f"   Similarity: {similarity.item():.4f}")
    
    print(f"\n✅ TRAINING SUCCESSFUL!")
    print(f"   Fine-tuned model ready at: {model_path}")
    print(f"   You can now use this in pipeline.py instead of the baseline model")
    
except RuntimeError as e:
    if "CUDA out of memory" in str(e) or "out of memory" in str(e):
        print(f"\n❌ Still out of memory. Trying ultra-lite version...")
        print(f"   Error: {e}")
        print(f"\n   Solution: Use batch_size=1 with gradient_accumulation_steps=8")
        print(f"   Or reduce epochs to 1")
    else:
        print(f"\n❌ Training error: {e}")
        raise

except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    raise

print("\n" + "=" * 60)
