import logging
from datetime import timedelta

from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from apps.ai_assistant.embedding import (
    EMBEDDING_MAX_BATCH_SIZE,
    EMBEDDING_MAX_INPUT_TOKENS_PER_TEXT,
    EMBEDDING_SAFE_REQUEST_BYTES,
    EmbeddingBatch,
    EmbeddingServiceUnavailable,
    embed_texts,
    get_embedding_input_byte_limit,
    validate_embedding_batch,
)

from .chunking import chunk_segments
from .extraction import NoExtractableTextError, extract_segments
from .models import (
    Document,
    DocumentChunk,
    DocumentEmbedding,
    DocumentLifecycleStatus,
    DocumentProcessingStatus,
)

logger = logging.getLogger(__name__)


class EmbeddingSpaceChangedError(Exception):
    """Sub-batch replies cannot be stored together in different vector spaces."""


DOCUMENT_PROCESSING_LEASE = timedelta(minutes=6)


def _embed_chunks(*, chunks, project_id):
    if not chunks:
        raise ValueError("A document must contain at least one chunk to embed.")
    batch_byte_limit = min(
        get_embedding_input_byte_limit(task_key="document_embedding"),
        EMBEDDING_SAFE_REQUEST_BYTES,
    )
    if batch_byte_limit < 1:
        raise ValueError("The configured embedding request byte limit is invalid.")

    vectors = []
    identity = None
    pending_texts = []
    pending_bytes = 0

    def submit_batch():
        nonlocal identity, pending_bytes
        batch = embed_texts(
            pending_texts,
            task_key="document_embedding",
            project_id=project_id,
        )
        validate_embedding_batch(batch, expected_count=len(pending_texts))
        batch_identity = (
            batch.profile_key,
            batch.profile_version,
            batch.model_name,
        )
        if identity is not None and batch_identity != identity:
            raise EmbeddingSpaceChangedError
        identity = batch_identity
        vectors.extend(batch.vectors)
        pending_texts.clear()
        pending_bytes = 0

    for chunk in chunks:
        text = chunk.content
        text_bytes = len(text.encode("utf-8"))
        if (
            text_bytes > EMBEDDING_MAX_INPUT_TOKENS_PER_TEXT
            or text_bytes > batch_byte_limit
        ):
            raise ValueError("A document chunk exceeds the embedding input limit.")
        if pending_texts and (
            len(pending_texts) >= EMBEDDING_MAX_BATCH_SIZE
            or pending_bytes + text_bytes > batch_byte_limit
        ):
            submit_batch()
        pending_texts.append(text)
        pending_bytes += text_bytes

    if pending_texts:
        submit_batch()

    return EmbeddingBatch(
        vectors=vectors,
        profile_key=identity[0],
        profile_version=identity[1],
        model_name=identity[2],
    )


def _claim_document_attempt(*, document_id, force_reindex, expected_generation=None):
    now = timezone.now()
    with transaction.atomic():
        document = Document.objects.select_for_update().filter(pk=document_id).first()
        if document is None or document.lifecycle_status not in (
            DocumentLifecycleStatus.ACTIVE,
            DocumentLifecycleStatus.ARCHIVED,
        ):
            return None, None
        if (
            expected_generation is not None
            and document.processing_generation != expected_generation
        ):
            return document, None
        if (
            document.processing_status == DocumentProcessingStatus.READY
            and not force_reindex
        ):
            return document, None
        if (
            document.processing_status == DocumentProcessingStatus.PROCESSING
            and document.processing_lease_expires_at is not None
            and document.processing_lease_expires_at > now
            and not force_reindex
        ):
            return document, None
        document.processing_generation += 1
        document.processing_status = DocumentProcessingStatus.PROCESSING
        document.processing_dispatch_attempts = 0
        document.processing_lease_expires_at = now + DOCUMENT_PROCESSING_LEASE
        document.processing_dispatch_lease_expires_at = None
        document.processing_dispatch_successful_at = (
            document.processing_dispatch_successful_at or now
        )
        document.processing_dispatch_failures = 0
        document.processing_dispatch_error_code = ""
        document.save(
            update_fields=(
                "processing_generation",
                "processing_status",
                "processing_dispatch_attempts",
                "processing_lease_expires_at",
                "processing_dispatch_lease_expires_at",
                "processing_dispatch_successful_at",
                "processing_dispatch_failures",
                "processing_dispatch_error_code",
            )
        )
        return document, document.processing_generation


def _store_result(*, document_id, processing_generation, chunks, batch, status):
    with transaction.atomic():
        document = Document.objects.select_for_update().filter(pk=document_id).first()
        if (
            document is None
            or document.lifecycle_status == DocumentLifecycleStatus.DELETED
        ):
            return document
        if document.processing_generation != processing_generation:
            return document
        if document.lifecycle_status not in (
            DocumentLifecycleStatus.ACTIVE,
            DocumentLifecycleStatus.ARCHIVED,
        ):
            if document.processing_status == DocumentProcessingStatus.PROCESSING:
                document.processing_status = DocumentProcessingStatus.QUEUED
                document.processing_dispatch_attempts = 0
                document.processing_dispatch_failures = 0
                document.processing_dispatch_error_code = ""
                document.processing_dispatch_successful_at = None
                document.processing_dispatch_lease_expires_at = None
                document.processing_lease_expires_at = None
                document.save(
                    update_fields=(
                        "processing_status",
                        "processing_dispatch_attempts",
                        "processing_dispatch_failures",
                        "processing_dispatch_error_code",
                        "processing_dispatch_successful_at",
                        "processing_dispatch_lease_expires_at",
                        "processing_lease_expires_at",
                    )
                )
            return document

        document.chunks.all().delete()
        chunk_rows = [
            DocumentChunk(
                document=document,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                metadata=chunk.metadata,
            )
            for chunk in chunks
        ]
        DocumentChunk.objects.bulk_create(chunk_rows)

        if batch is not None:
            saved_chunks = list(
                DocumentChunk.objects.filter(document=document).order_by("chunk_index")
            )
            DocumentEmbedding.objects.bulk_create(
                [
                    DocumentEmbedding(
                        chunk=chunk,
                        embedding_profile_key=batch.profile_key,
                        embedding_profile_version=batch.profile_version,
                        model_name=batch.model_name,
                        embedding=vector,
                    )
                    for chunk, vector in zip(saved_chunks, batch.vectors, strict=True)
                ]
            )

        document.processing_status = status
        document.processing_dispatch_attempts = 0
        document.processing_dispatch_failures = 0
        document.processing_dispatch_error_code = ""
        document.processing_dispatch_successful_at = None
        document.processing_dispatch_lease_expires_at = None
        document.processing_lease_expires_at = None
        document.save(
            update_fields=(
                "processing_status",
                "processing_dispatch_attempts",
                "processing_dispatch_failures",
                "processing_dispatch_error_code",
                "processing_dispatch_successful_at",
                "processing_dispatch_lease_expires_at",
                "processing_lease_expires_at",
            )
        )
        return document


def process_document(*, document_id, force_reindex=False, expected_generation=None):
    """Extract, chunk, and embed a stored document; fence stale retries."""
    document, processing_generation = _claim_document_attempt(
        document_id=document_id,
        force_reindex=force_reindex,
        expected_generation=expected_generation,
    )
    if document is None or processing_generation is None:
        return document
    try:
        with default_storage.open(document.storage_key, "rb") as source:
            contents = source.read()
        segments = extract_segments(
            filename=document.original_filename, contents=contents
        )
        chunks = chunk_segments(segments)
    except NoExtractableTextError:
        return _store_result(
            document_id=document_id,
            processing_generation=processing_generation,
            chunks=[],
            batch=None,
            status=DocumentProcessingStatus.UNSUPPORTED,
        )
    except Exception as exc:
        logger.warning("Document extraction failed (%s).", type(exc).__name__)
        return _store_result(
            document_id=document_id,
            processing_generation=processing_generation,
            chunks=[],
            batch=None,
            status=DocumentProcessingStatus.FAILED,
        )

    try:
        batch = _embed_chunks(chunks=chunks, project_id=document.project_id)
    except EmbeddingServiceUnavailable:
        return _store_result(
            document_id=document_id,
            processing_generation=processing_generation,
            chunks=chunks,
            batch=None,
            status=DocumentProcessingStatus.FAILED,
        )
    except Exception as exc:
        logger.warning("Document embedding failed (%s).", type(exc).__name__)
        return _store_result(
            document_id=document_id,
            processing_generation=processing_generation,
            chunks=chunks,
            batch=None,
            status=DocumentProcessingStatus.FAILED,
        )

    return _store_result(
        document_id=document_id,
        processing_generation=processing_generation,
        chunks=chunks,
        batch=batch,
        status=DocumentProcessingStatus.READY,
    )
