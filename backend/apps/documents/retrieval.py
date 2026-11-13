from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import ValidationError
from pgvector.django import CosineDistance

from apps.ai_assistant.embedding import embed_texts, validate_embedding_batch
from apps.projects.models import ProjectMember, ProjectMemberStatus

from .models import (
    DocumentEmbedding,
    DocumentLifecycleStatus,
    DocumentProcessingStatus,
)
from .services import DocumentNotFoundError

DEFAULT_RETRIEVAL_TOP_K = 5
MAX_RETRIEVAL_TOP_K = 20


@dataclass(frozen=True)
class DocumentEvidenceReference:
    document_id: UUID
    chunk_id: UUID
    filename: str
    chunk_index: int
    page_number: int | None
    source_location: dict[str, int]


@dataclass(frozen=True)
class RetrievedDocumentChunk:
    content: str
    evidence: DocumentEvidenceReference
    similarity: float


def retrieve_project_evidence(
    *, project_id, actor, query, top_k=DEFAULT_RETRIEVAL_TOP_K
):
    if not ProjectMember.objects.filter(
        project_id=project_id,
        user=actor,
        status=ProjectMemberStatus.ACTIVE,
    ).exists():
        raise DocumentNotFoundError
    if not isinstance(query, str) or not query.strip():
        raise ValidationError({"query": "A non-empty query is required."})
    if (
        isinstance(top_k, bool)
        or not isinstance(top_k, int)
        or not 1 <= top_k <= MAX_RETRIEVAL_TOP_K
    ):
        raise ValidationError({"top_k": "Top-k must be between 1 and 20."})

    query_batch = embed_texts([query], task_key="document_embedding")
    validate_embedding_batch(query_batch, expected_count=1)
    query_vector = query_batch.vectors[0]

    matches = (
        DocumentEmbedding.objects.filter(
            embedding_profile_key=query_batch.profile_key,
            embedding_profile_version=query_batch.profile_version,
            model_name=query_batch.model_name,
            chunk__document__project_id=project_id,
            chunk__document__processing_status=DocumentProcessingStatus.READY,
            chunk__document__lifecycle_status=DocumentLifecycleStatus.ACTIVE,
        )
        .select_related("chunk__document")
        .annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance", "chunk__document_id", "chunk__chunk_index")[:top_k]
    )
    return [
        RetrievedDocumentChunk(
            content=row.chunk.content,
            evidence=DocumentEvidenceReference(
                document_id=row.chunk.document_id,
                chunk_id=row.chunk_id,
                filename=row.chunk.document.original_filename,
                chunk_index=row.chunk.chunk_index,
                page_number=row.chunk.page_number,
                source_location=row.chunk.metadata,
            ),
            similarity=1.0 - float(row.distance),
        )
        for row in matches
    ]
