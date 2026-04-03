"""
Fine-tune SBERT on legal clause query-clause pairs using sentence-transformers.
Training approach: Contrastive learning with in-batch negatives.
"""

import json
import sys
import torch
from sentence_transformers import SentenceTransformer, InputExample, losses, models
from torch.utils.data import DataLoader
from pathlib import Path
import numpy as np

def load_training_pairs():
    """Load (query, clause) pairs from training_pairs.json"""
    with open('data/training_pairs.json', 'r') as f:
        pairs = json.load(f)
    
    print(f"✅ Loaded {len(pairs)} training pairs")
    return pairs

def create_training_examples(pairs):
    """Convert pairs to InputExample format for sentence-transformers"""
    examples = []
    
    for pair in pairs:
        examples.append(InputExample(
            texts=[pair['query'], pair['clause']]
        ))
    
    print(f"✅ Created {len(examples)} training examples")
    return examples

def fine_tune_sbert(examples, model_name='all-MiniLM-L6-v2', epochs=5, batch_size=16, warmup_steps=100):
    """Fine-tune SBERT on query-clause pairs"""
    
    print(f"\n🚀 Starting SBERT fine-tuning...")
    print(f"  Model: {model_name}")
    print(f"  Epochs: {epochs}")
    print(f"  Batch size: {batch_size}")
    print(f"  Training examples: {len(examples)}")
    
    # Load pre-trained model
    model = SentenceTransformer(model_name)
    
    # Use contrastive loss (works well for sentence pair tasks)
    train_loss = losses.MultipleNegativesRankingLoss(model)
    
    # Create DataLoader
    train_dataloader = DataLoader(examples, shuffle=True, batch_size=batch_size)
    
    # Fine-tune
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=warmup_steps,
        show_progress_bar=True,
        checkpoint_path='models/sbert_checkpoints',
        checkpoint_save_steps=len(train_dataloader),  # Save after each epoch
        checkpoint_save_total_limit=3
    )
    
    print(f"\n✅ Fine-tuning complete!")
    
    # Save the trained model
    output_path = 'models/sbert_legal_finetuned'
    model.save(output_path)
    print(f"✅ Model saved to {output_path}")
    
    return model

def evaluate_model(model, test_pairs=None):
    """Quick evaluation: encode and measure similarity for sample pairs"""
    
    if test_pairs is None:
        # Use first 5 pairs for quick eval
        with open('data/training_pairs.json', 'r') as f:
            all_pairs = json.load(f)
        test_pairs = all_pairs[:5]
    
    print(f"\n📊 Quick evaluation on {len(test_pairs)} sample pairs:")
    
    similarities = []
    for i, pair in enumerate(test_pairs):
        query_embed = model.encode(pair['query'], convert_to_tensor=True)
        clause_embed = model.encode(pair['clause'], convert_to_tensor=True)
        
        # Compute cosine similarity
        similarity = torch.nn.functional.cosine_similarity(
            query_embed.unsqueeze(0), 
            clause_embed.unsqueeze(0)
        ).item()
        
        similarities.append(similarity)
        print(f"  Pair {i+1}: {similarity:.4f} | Query: {pair['query'][:50]}...")
    
    avg_similarity = np.mean(similarities)
    print(f"\n  Average similarity: {avg_similarity:.4f}")
    
    return avg_similarity

if __name__ == '__main__':
    print("="*60)
    print("SBERT LEGAL CLAUSE FINE-TUNING")
    print("="*60)
    
    # Load training data
    pairs = load_training_pairs()
    examples = create_training_examples(pairs)
    
    # Fine-tune model
    model = fine_tune_sbert(
        examples,
        model_name='all-MiniLM-L6-v2',
        epochs=5,
        batch_size=16,
        warmup_steps=100
    )
    
    # Quick evaluation
    evaluate_model(model)
    
    print("\n" + "="*60)
    print("✅ Training complete! Model ready for inference.")
    print("="*60)
