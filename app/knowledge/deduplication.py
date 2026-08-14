"""
Deduplication and vector similarity utility.
Prevents duplicate knowledge items from being repeatedly indexed into the database.
"""
import math
from typing import List, Optional
from app.config import settings


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a, b in zip(vec1, vec2)))
    norm_b = math.sqrt(sum(b * b for a, b in zip(vec1, vec2)))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def is_duplicate(
    new_embedding: List[float],
    existing_embeddings: List[List[float]],
    threshold: Optional[float] = None
) -> bool:
    """Checks if new embedding is too close to any existing embedding."""
    limit = threshold or settings.dedup_threshold
    for existing in existing_embeddings:
        sim = cosine_similarity(new_embedding, existing)
        if sim >= limit:
            return True
    return False
