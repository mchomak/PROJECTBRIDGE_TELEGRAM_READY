import math
from dataclasses import dataclass

from django.conf import settings
from django.utils.module_loading import import_string

EMBEDDING_DIMENSIONS = 1536


class EmbeddingServiceUnavailable(Exception):
    """No configured AI Router can serve the requested embedding task."""


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    profile_key: str
    profile_version: int
    model_name: str


def validate_embedding_batch(batch: EmbeddingBatch, *, expected_count: int) -> None:
    if not isinstance(batch, EmbeddingBatch):
        raise ValueError("Embedding service returned an invalid batch.")
    if not batch.profile_key or len(batch.profile_key) > 64:
        raise ValueError("Embedding service returned an invalid profile key.")
    if (
        isinstance(batch.profile_version, bool)
        or not isinstance(batch.profile_version, int)
        or batch.profile_version < 1
    ):
        raise ValueError("Embedding service returned an invalid profile version.")
    if not batch.model_name or len(batch.model_name) > 128:
        raise ValueError("Embedding service returned an invalid model name.")
    if len(batch.vectors) != expected_count:
        raise ValueError("Embedding service returned the wrong vector count.")
    for vector in batch.vectors:
        if (
            len(vector) != EMBEDDING_DIMENSIONS
            or any(
                not isinstance(value, int | float) or not math.isfinite(value)
                for value in vector
            )
            or not any(vector)
        ):
            raise ValueError("Embedding service returned an incompatible vector.")


def embed_texts(
    texts: list[str],
    *,
    task_key: str = "document_embedding",
) -> EmbeddingBatch:
    """Delegate embedding to the configured AI Router capability boundary."""
    service_path = getattr(settings, "AI_EMBEDDING_SERVICE", "")
    if not service_path:
        raise EmbeddingServiceUnavailable(
            "No embedding router is configured for this environment."
        )

    service = import_string(service_path)
    result = service(texts, task_key=task_key)
    if not isinstance(result, EmbeddingBatch):
        raise TypeError("The embedding service must return an EmbeddingBatch.")
    return result
