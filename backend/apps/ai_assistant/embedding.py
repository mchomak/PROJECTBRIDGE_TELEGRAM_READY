import math
from dataclasses import dataclass

from django.conf import settings
from django.utils.module_loading import import_string

EMBEDDING_DIMENSIONS = 1536
EMBEDDING_MAX_BATCH_SIZE = 2048
EMBEDDING_MAX_INPUT_TOKENS_PER_TEXT = 8192
EMBEDDING_MAX_INPUT_TOKENS_PER_REQUEST = 300_000
# At most one token per UTF-8 byte, leaving room below the provider's token cap.
EMBEDDING_SAFE_REQUEST_BYTES = min(
    200_000,
    EMBEDDING_MAX_INPUT_TOKENS_PER_REQUEST - 1,
)


class EmbeddingServiceUnavailable(Exception):
    """No configured AI Router can serve the requested embedding task."""


@dataclass(frozen=True)
class EmbeddingBatch:
    """Vectors plus their stable, config-independent vector-space identity."""

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
    project_id=None,
) -> EmbeddingBatch:
    """Delegate embedding to the configured AI Router capability boundary."""
    service_path = getattr(settings, "AI_EMBEDDING_SERVICE", "")
    if not service_path:
        raise EmbeddingServiceUnavailable(
            "No embedding router is configured for this environment."
        )

    service = import_string(service_path)
    result = service(texts, task_key=task_key, project_id=project_id)
    if not isinstance(result, EmbeddingBatch):
        raise TypeError("The embedding service must return an EmbeddingBatch.")
    return result


def get_embedding_input_byte_limit(*, task_key="document_embedding"):
    """Return the router's effective input cap, bounded by the provider-safe cap."""
    service_path = getattr(settings, "AI_EMBEDDING_SERVICE", "")
    if not service_path:
        return EMBEDDING_SAFE_REQUEST_BYTES

    service = import_string(service_path)
    limit_reader = getattr(service, "embedding_input_byte_limit", None)
    if limit_reader is None:
        module_path, _separator, _service_name = service_path.rpartition(".")
        if module_path:
            module = import_string(module_path)
            limit_reader = getattr(module, "embedding_input_byte_limit", None)
    if limit_reader is None:
        return EMBEDDING_SAFE_REQUEST_BYTES
    limit = limit_reader(task_key=task_key)
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise EmbeddingServiceUnavailable(
            "The embedding router returned an invalid input byte limit."
        )
    return min(limit, EMBEDDING_SAFE_REQUEST_BYTES)
