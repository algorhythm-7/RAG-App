#!/usr/bin/env python3
"""Debug script to verify image and text embeddings."""

from src.components.embedding_generator import EmbeddingGenerator
from src.models import Passage
import numpy as np
from PIL import Image
import io

def test_embeddings():
    """Test text and image embeddings."""
    gen = EmbeddingGenerator()
    
    # Test 1: Text embeddings
    print("=" * 60)
    print("TEST 1: Text Embeddings")
    print("=" * 60)
    text_passages = [
        Passage(text="This is a circuit diagram for AC power", section="Test", document_id="test", passage_index=0, is_diagram=False),
        Passage(text="Engine coolant temperature sensor", section="Test", document_id="test", passage_index=1, is_diagram=False),
    ]
    text_embs = gen.embed_passages(text_passages)
    print(f"✓ Generated {len(text_embs)} text embeddings")
    print(f"  Embedding 0 shape: {len(text_embs[0])}, sample values: {text_embs[0][:5]}")
    print(f"  Embedding 1 shape: {len(text_embs[1])}, sample values: {text_embs[1][:5]}")
    
    # Test 2: Check if CLIP is detected
    print("\n" + "=" * 60)
    print("TEST 2: CLIP Model Detection")
    print("=" * 60)
    print(f"✓ Is CLIP model: {gen.is_clip}")
    print(f"  Model name: {gen.model.get_sentence_embedding_dimension()}-dim")
    
    # Test 3: Try image embedding (if possible)
    print("\n" + "=" * 60)
    print("TEST 3: Image Embeddings")
    print("=" * 60)
    try:
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes_io = io.BytesIO()
        img.save(img_bytes_io, format='PNG')
        img_bytes = img_bytes_io.getvalue()
        
        image_passages = [
            Passage(
                text="Red test image",
                section="Test",
                document_id="test",
                passage_index=0,
                image_bytes=img_bytes,
                is_diagram=True
            )
        ]
        
        img_embs = gen.embed_passages(image_passages)
        print(f"✓ Generated {len(img_embs)} image embeddings")
        print(f"  Embedding shape: {len(img_embs[0])}, sample values: {img_embs[0][:5]}")
    except Exception as e:
        print(f"✗ Image embedding failed: {e}")
    
    # Test 4: Similarity check
    print("\n" + "=" * 60)
    print("TEST 4: Embedding Similarity")
    print("=" * 60)
    from scipy.spatial.distance import cdist
    
    passages = [
        Passage(text="AC circuit diagram with resistor", section="", document_id="", passage_index=0, is_diagram=False),
        Passage(text="Fuel pump electrical system", section="", document_id="", passage_index=1, is_diagram=False),
    ]
    embs = gen.embed_passages(passages)
    
    # Calculate distance (lower = more similar)
    dist = cdist([embs[0]], [embs[1]], metric='euclidean')[0][0]
    sim = 1 / (1 + dist)  # FAISS similarity formula
    print(f"✓ Similarity between 'AC circuit' and 'Fuel pump': {sim:.4f}")
    print(f"  (>0.5 = related, <0.2 = unrelated)")

if __name__ == "__main__":
    test_embeddings()
