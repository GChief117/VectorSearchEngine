#!/usr/bin/env python3
"""Script to regenerate embeddings.json from sentences.txt"""
import json
import hashlib
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
SENTENCES_FILE = ROOT_DIR / "data" / "sentences.txt"
EMBEDDINGS_FILE = ROOT_DIR / "src" / "data" / "embeddings.json"

def generate_id(text: str) -> str:
    """Generate SHA256 hash ID for text."""
    return hashlib.sha256(text.encode()).hexdigest()

def main():
    print("Loading sentence transformer model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print(f"Reading sentences from {SENTENCES_FILE}")
    with open(SENTENCES_FILE, 'r') as f:
        sentences = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(sentences)} sentences")
    
    # Generate embeddings
    embeddings_data = []
    for i, sentence in enumerate(sentences):
        print(f"[{i+1}/{len(sentences)}] Embedding: {sentence[:50]}...")
        
        # Generate embedding
        embedding = model.encode(sentence).tolist()
        
        # Create record
        record = {
            "ID": generate_id(sentence),
            "Text": sentence,
            "Embeddings": embedding
        }
        embeddings_data.append(record)
    
    # Save to JSON
    print(f"Saving to {EMBEDDINGS_FILE}")
    EMBEDDINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(EMBEDDINGS_FILE, 'w') as f:
        json.dump(embeddings_data, f, indent=2)
    
    print(f"Done! Saved {len(embeddings_data)} embeddings")

if __name__ == "__main__":
    main()