import logging

from django.core.files.storage import default_storage
from django.db import transaction

from apps.ai_assistant.embedding import (
    EmbeddingServiceUnavailable,
    embed_texts,
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


def _store_result(*, document_id, chunks, batch, status):
    with transaction.atomic():
        document = Document.objects.select_for_update().filter(pk=document_id).first()
        if (
            document is None
            or document.lifecycle_status == DocumentLifecycleStatus.DELETED
        ):
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
        document.save(update_fields=["processing_status"])
        return document


def process_document(*, document_id):
    """Extract, chunk, and embed a stored document; retries replace derived rows."""
    document = Document.objects.filter(pk=document_id).first()
    if document is None or document.lifecycle_status == DocumentLifecycleStatus.DELETED:
        return None
    if document.processing_status == DocumentProcessingStatus.READY:
        return document

    Document.objects.filter(pk=document_id).update(
        processing_status=DocumentProcessingStatus.PROCESSING
    )
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
            chunks=[],
            batch=None,
            status=DocumentProcessingStatus.UNSUPPORTED,
        )
    except Exception as exc:
        logger.warning("Document extraction failed (%s).", type(exc).__name__)
        return _store_result(
            document_id=document_id,
            chunks=[],
            batch=None,
            status=DocumentProcessingStatus.FAILED,
        )

    try:
        batch = embed_texts(
            [chunk.content for chunk in chunks],
            task_key="document_embedding",
        )
        validate_embedding_batch(batch, expected_count=len(chunks))
    except EmbeddingServiceUnavailable:
        return _store_result(
            document_id=document_id,
            chunks=chunks,
            batch=None,
            status=DocumentProcessingStatus.FAILED,
        )
    except Exception as exc:
        logger.warning("Document embedding failed (%s).", type(exc).__name__)
        return _store_result(
            document_id=document_id,
            chunks=chunks,
            batch=None,
            status=DocumentProcessingStatus.FAILED,
        )

    return _store_result(
        document_id=document_id,
        chunks=chunks,
        batch=batch,
        status=DocumentProcessingStatus.READY,
    )
