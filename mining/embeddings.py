"""
Embedding generator and vector utilities for Chanakya Research Commons.
Uses SentenceTransformers (all-MiniLM-L6-v2) to generate 384-dimensional dense vectors.
Loads from local cache first for speed, downloads once if not yet cached, and
provides a deterministic fallback if offline without cache.
"""

import os
import json
import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

_MODEL = None


def get_embedding_model():
    """Lazy load SentenceTransformer model (uses local cache first, downloads once if needed)."""
    global _MODEL
    if _MODEL is None:
        model_name = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
        try:
            import torch
            torch.set_num_threads(1)
        except Exception:
            pass
        try:
            from sentence_transformers import SentenceTransformer
            try:
                _MODEL = SentenceTransformer(model_name, local_files_only=True)
            except Exception:
                _MODEL = SentenceTransformer(model_name)
        except Exception as e:
            print(f"[WARN] Could not load sentence-transformers: {e}. Using deterministic fallback.")
            _MODEL = "FALLBACK"
    return _MODEL


def generate_embedding(text):
    """
    Generate normalized 384-dimensional embedding for text.
    Returns python list of 384 floats.
    """
    if not text:
        return [0.0] * 384

    model = get_embedding_model()
    if model != "FALLBACK":
        try:
            vec = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
            return vec.tolist()
        except Exception as e:
            print(f"[WARN] Error encoding text with model: {e}")

    # Deterministic fallback hashing to 384-dim pseudo-vector
    import hashlib
    np.random.seed(int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16) % (2**32))
    vec = np.random.randn(384)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def generate_embeddings_batch(texts, batch_size=32):
    """
    Generate embeddings for a list of texts in batches.
    """
    if not texts:
        return []

    model = get_embedding_model()
    if model != "FALLBACK":
        try:
            vecs = model.encode(texts, batch_size=batch_size, convert_to_numpy=True, normalize_embeddings=True)
            return [v.tolist() for v in vecs]
        except Exception as e:
            print(f"[WARN] Batch encode error: {e}")

    return [generate_embedding(t) for t in texts]


def cosine_similarity(v1, v2):
    """Compute cosine similarity between two float vectors."""
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
