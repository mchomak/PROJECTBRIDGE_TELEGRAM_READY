import io
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from pypdf import PdfWriter


def _blank_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _text_pdf():
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=72, height=72)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 10 20 Td (Hello PDF) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_extract_text_file_preserves_source_offsets():
    from apps.documents.extraction import extract_segments

    segments = extract_segments(
        filename="brief.txt", contents=b"First line.\nSecond line."
    )

    assert [(segment.text, segment.location) for segment in segments] == [
        ("First line.\nSecond line.", {"start_char": 0, "end_char": 24})
    ]


@pytest.mark.parametrize(
    ("filename", "contents"),
    [("scan.pdf", _blank_pdf())],
)
def test_extraction_reports_files_without_searchable_text_as_unsupported(
    filename, contents
):
    from apps.documents.extraction import NoExtractableTextError, extract_segments

    with pytest.raises(NoExtractableTextError):
        extract_segments(filename=filename, contents=contents)


def test_malformed_pdf_is_reported_as_a_processing_error():
    from apps.documents.extraction import DocumentExtractionError, extract_segments

    with pytest.raises(DocumentExtractionError):
        extract_segments(filename="broken.pdf", contents=b"not a PDF")


def test_pdf_and_docx_extraction_preserve_page_and_paragraph_locations():
    from docx import Document as WordDocument

    from apps.documents.extraction import extract_segments

    word = WordDocument()
    word.add_paragraph("Hello DOCX")
    word_output = io.BytesIO()
    word.save(word_output)

    pdf_segments = extract_segments(filename="scope.pdf", contents=_text_pdf())
    docx_segments = extract_segments(
        filename="scope.docx",
        contents=word_output.getvalue(),
    )

    assert pdf_segments[0].text == "Hello PDF"
    assert pdf_segments[0].page_number == 1
    assert docx_segments[0].text == "Hello DOCX"
    assert docx_segments[0].location["paragraph"] == 0

    word.add_table(rows=1, cols=2).cell(0, 0).text = "Scope"
    word.tables[0].cell(0, 1).text = "Table requirement"
    word_output = io.BytesIO()
    word.save(word_output)
    table_segments = extract_segments(
        filename="table.docx",
        contents=word_output.getvalue(),
    )
    assert [segment.text for segment in table_segments] == [
        "Hello DOCX",
        "Scope",
        "Table requirement",
    ]
    assert table_segments[1].location["table_index"] == 0
    assert table_segments[1].location["row_index"] == 0


def test_parser_rejects_text_and_docx_expansion_over_configured_limits(monkeypatch):
    from docx import Document as WordDocument

    from apps.documents import extraction
    from apps.documents.extraction import DocumentExtractionError

    monkeypatch.setattr(extraction, "MAX_EXTRACTED_TEXT_CHARS", 3)
    with pytest.raises(DocumentExtractionError):
        extraction.extract_segments(filename="large.txt", contents=b"four")

    monkeypatch.setattr(extraction, "MAX_PDF_PAGES", 0)
    with pytest.raises(DocumentExtractionError):
        extraction.extract_segments(filename="too-many.pdf", contents=_blank_pdf())

    document = WordDocument()
    document.add_paragraph("small")
    output = io.BytesIO()
    document.save(output)
    from apps.documents import docx_safety

    monkeypatch.setattr(docx_safety, "MAX_DOCX_UNCOMPRESSED_BYTES", 0)
    with pytest.raises(DocumentExtractionError):
        extraction.extract_segments(
            filename="expanded.docx", contents=output.getvalue()
        )


@pytest.mark.parametrize(
    ("entry_count", "directory_size"),
    [
        (10_001, 0),
        (0, 2 * 1024 * 1024 + 1),
    ],
)
def test_docx_directory_limits_are_checked_before_zipfile_materializes_entries(
    monkeypatch, entry_count, directory_size
):
    import struct

    from apps.documents import docx_safety
    from apps.documents.docx_safety import DocxArchiveError

    eocd = struct.pack(
        "<4s4H2LH",
        b"PK\x05\x06",
        0,
        0,
        entry_count,
        entry_count,
        directory_size,
        0,
        0,
    )
    monkeypatch.setattr(
        docx_safety.zipfile,
        "ZipFile",
        lambda *_args, **_kwargs: pytest.fail("ZipFile was opened before preflight"),
    )

    with pytest.raises(DocxArchiveError):
        docx_safety.docx_archive_names(eocd)


def test_docx_actual_entry_count_is_bounded_before_zipfile_materializes_entries(
    monkeypatch,
):
    import struct

    from apps.documents import docx_safety
    from apps.documents.docx_safety import DocxArchiveError

    central_entry = b"PK\x01\x02" + bytes(42)
    entry_count = docx_safety.MAX_DOCX_ARCHIVE_ENTRIES + 1
    directory = central_entry * entry_count
    eocd = struct.pack(
        "<4s4H2LH",
        b"PK\x05\x06",
        0,
        0,
        1,
        1,
        len(directory),
        0,
        0,
    )
    monkeypatch.setattr(
        docx_safety.zipfile,
        "ZipFile",
        lambda *_args, **_kwargs: pytest.fail("ZipFile was opened before preflight"),
    )

    with pytest.raises(DocxArchiveError, match="too many"):
        docx_safety.docx_archive_names(directory + eocd)


def test_chunking_keeps_order_overlap_and_source_location():
    from apps.documents.chunking import chunk_segments
    from apps.documents.extraction import ExtractedSegment

    chunks = chunk_segments(
        [ExtractedSegment("abcdefghijklmnop", {"page": 3})],
        chunk_size=10,
        overlap=4,
    )

    assert [chunk.content for chunk in chunks] == ["abcdefghij", "ghijklmnop"]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert chunks[1].metadata == {"page": 3, "start_char": 6, "end_char": 16}


@override_settings(AI_EMBEDDING_SERVICE="")
def test_embedding_boundary_does_not_fake_search_ready_vectors():
    from apps.ai_assistant.embedding import EmbeddingServiceUnavailable, embed_texts

    with pytest.raises(EmbeddingServiceUnavailable):
        embed_texts(["Project requirement"], task_key="document_embedding")


@pytest.mark.django_db
def test_document_processing_stores_stable_chunks_and_is_idempotent(
    tmp_path, settings, monkeypatch
):
    from django.contrib.auth import get_user_model

    from apps.ai_assistant.embedding import EmbeddingBatch
    from apps.documents import processing
    from apps.documents.models import DocumentChunk, DocumentEmbedding
    from apps.documents.services import upload_document
    from apps.projects.services import create_project

    settings.MEDIA_ROOT = tmp_path
    actor = get_user_model().objects.create_user(email="processor@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Processing", "project_type": "website"},
    )
    source_text = "requirement " * 120
    document = upload_document(
        project_id=project.pk,
        actor=actor,
        file=SimpleUploadedFile("requirements.txt", source_text.encode()),
    )
    embedding_calls = []

    def fake_embed_texts(texts, *, task_key, project_id):
        embedding_calls.append((texts, task_key))
        vector = [1.0, *([0.0] * 1535)]
        return EmbeddingBatch(
            vectors=[vector for _ in texts],
            profile_key="document_embedding",
            profile_version=2,
            model_name="text-embedding-3-small",
        )

    monkeypatch.setattr(processing, "embed_texts", fake_embed_texts)
    first_result = processing.process_document(document_id=document.pk)
    first_chunk_ids = list(
        DocumentChunk.objects.filter(document=document).values_list("id", flat=True)
    )
    second_result = processing.process_document(document_id=document.pk)

    document.refresh_from_db()
    assert first_result.processing_status == "ready"
    assert second_result.processing_status == "ready"
    assert document.processing_status == "ready"
    assert DocumentChunk.objects.filter(document=document).count() == 2
    assert DocumentEmbedding.objects.filter(chunk__document=document).count() == 2
    assert (
        DocumentEmbedding.objects.filter(
            chunk__document=document,
            embedding_profile_version=2,
        ).count()
        == 2
    )
    assert (
        list(
            DocumentChunk.objects.filter(document=document).values_list("id", flat=True)
        )
        == first_chunk_ids
    )
    assert len(embedding_calls) == 1
    assert embedding_calls[0][1] == "document_embedding"


@pytest.mark.django_db
def test_ready_document_reindex_switches_vector_space_and_remains_retrievable(
    tmp_path, settings, monkeypatch
):
    from django.contrib.auth import get_user_model

    from apps.ai_assistant.embedding import EmbeddingBatch
    from apps.documents import processing, retrieval
    from apps.documents.models import DocumentEmbedding
    from apps.documents.services import upload_document
    from apps.projects.services import create_project

    settings.MEDIA_ROOT = tmp_path
    actor = get_user_model().objects.create_user(email="reindex@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Reindex", "project_type": "website"},
    )
    source = b"The site needs a contact form."
    document = upload_document(
        project_id=project.pk,
        actor=actor,
        file=SimpleUploadedFile("scope.txt", source),
    )
    old_batch = EmbeddingBatch(
        vectors=[[1.0, *([0.0] * 1535)]],
        profile_key="embed-old-space",
        profile_version=1,
        model_name="text-embedding-3-small",
    )
    new_batch = EmbeddingBatch(
        vectors=[[1.0, *([0.0] * 1535)]],
        profile_key="embed-new-space",
        profile_version=1,
        model_name="text-embedding-3-large",
    )
    active_batch = old_batch
    monkeypatch.setattr(
        processing,
        "embed_texts",
        lambda *_args, **_kwargs: active_batch,
    )
    original_storage_key = document.storage_key
    original_checksum = document.checksum_sha256

    first_result = processing.process_document(document_id=document.pk)
    monkeypatch.setattr(retrieval, "embed_texts", lambda *_args, **_kwargs: old_batch)
    assert (
        len(
            retrieval.retrieve_project_evidence(
                project_id=project.pk,
                actor=actor,
                query="contact form",
            )
        )
        == 1
    )

    active_batch = new_batch
    reindexed = processing.process_document(
        document_id=document.pk,
        force_reindex=True,
    )
    monkeypatch.setattr(retrieval, "embed_texts", lambda *_args, **_kwargs: new_batch)
    new_results = retrieval.retrieve_project_evidence(
        project_id=project.pk,
        actor=actor,
        query="contact form",
    )

    document.refresh_from_db()
    assert first_result.processing_status == "ready"
    assert reindexed.processing_status == "ready"
    assert document.processing_status == "ready"
    assert document.storage_key == original_storage_key
    assert document.checksum_sha256 == original_checksum
    assert (
        DocumentEmbedding.objects.filter(
            chunk__document=document,
            embedding_profile_key="embed-old-space",
        ).count()
        == 0
    )
    assert (
        DocumentEmbedding.objects.filter(
            chunk__document=document,
            embedding_profile_key="embed-new-space",
            model_name="text-embedding-3-large",
        ).count()
        == 1
    )
    assert new_results[0].content == "The site needs a contact form."
    monkeypatch.setattr(retrieval, "embed_texts", lambda *_args, **_kwargs: old_batch)
    assert (
        retrieval.retrieve_project_evidence(
            project_id=project.pk,
            actor=actor,
            query="contact form",
        )
        == []
    )


@pytest.mark.django_db
def test_reindex_command_queues_only_eligible_documents(monkeypatch):
    from io import StringIO
    from unittest.mock import patch
    from uuid import uuid4

    from django.contrib.auth import get_user_model
    from django.core.management import call_command

    from apps.documents import services
    from apps.documents.models import (
        Document,
        DocumentLifecycleStatus,
        DocumentProcessingStatus,
    )
    from apps.documents.tasks import reindex_project_document
    from apps.projects.services import create_project

    actor = get_user_model().objects.create_user(email="reindex-command@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Command reindex", "project_type": "website"},
    )

    eligible_ids = []
    statuses = [
        (DocumentLifecycleStatus.ACTIVE, DocumentProcessingStatus.QUEUED),
        (DocumentLifecycleStatus.ARCHIVED, DocumentProcessingStatus.READY),
        (DocumentLifecycleStatus.ARCHIVE_PENDING, DocumentProcessingStatus.READY),
        (DocumentLifecycleStatus.DELETION_PENDING, DocumentProcessingStatus.READY),
        (DocumentLifecycleStatus.DELETED, DocumentProcessingStatus.READY),
        (DocumentLifecycleStatus.ACTIVE, DocumentProcessingStatus.UNSUPPORTED),
    ]
    for lifecycle_status, processing_status in statuses:
        document = Document.objects.create(
            project=project,
            uploaded_by=project.created_by,
            original_filename="scope.txt",
            mime_type="text/plain",
            file_size=1,
            checksum_sha256="a" * 64,
            storage_key=f"documents/{uuid4()}",
            lifecycle_status=lifecycle_status,
            processing_status=processing_status,
        )
        if (
            lifecycle_status
            in (
                DocumentLifecycleStatus.ACTIVE,
                DocumentLifecycleStatus.ARCHIVED,
            )
            and processing_status != DocumentProcessingStatus.UNSUPPORTED
        ):
            eligible_ids.append(str(document.pk))

    monkeypatch.setattr(services.transaction, "on_commit", lambda callback: callback())
    output = StringIO()
    with patch.object(reindex_project_document, "delay") as enqueue:
        call_command(
            "reindex_document_embeddings",
            project_id=str(project.pk),
            stdout=output,
        )

    assert "Queued 2 eligible" in output.getvalue()
    assert [call.args[0] for call in enqueue.call_args_list] == sorted(eligible_ids)


@pytest.mark.django_db
def test_reindex_processing_skips_lifecycle_pending_documents(
    tmp_path, settings, monkeypatch
):
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.documents import processing
    from apps.documents.models import DocumentLifecycleStatus
    from apps.documents.services import upload_document
    from apps.projects.services import create_project

    settings.MEDIA_ROOT = tmp_path
    actor = get_user_model().objects.create_user(email="lifecycle-reindex@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Lifecycle reindex", "project_type": "website"},
    )
    document = upload_document(
        project_id=project.pk,
        actor=actor,
        file=SimpleUploadedFile("scope.txt", b"A real requirement."),
    )
    document.lifecycle_status = DocumentLifecycleStatus.DELETION_PENDING
    document.save(update_fields=["lifecycle_status"])
    monkeypatch.setattr(
        processing,
        "embed_texts",
        lambda *_args, **_kwargs: pytest.fail("Lifecycle-pending docs are excluded."),
    )

    result = processing.process_document(
        document_id=document.pk,
        force_reindex=True,
    )

    assert result is None


def test_reindex_task_retries_failed_document_processing(monkeypatch):
    from types import SimpleNamespace

    from celery.exceptions import Retry

    from apps.documents import tasks

    monkeypatch.setattr(
        tasks,
        "process_document",
        lambda **_kwargs: SimpleNamespace(processing_status="failed"),
    )

    with pytest.raises(Retry):
        tasks.reindex_project_document.run("document-id")

    assert tasks.reindex_project_document.max_retries == 3


@pytest.mark.django_db
def test_reindex_splits_large_utf8_document_by_count_and_configured_bytes(
    tmp_path, settings, monkeypatch
):
    from types import SimpleNamespace

    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.ai_assistant.embedding import EmbeddingBatch
    from apps.ai_assistant.models import AIModelProfile, AITask
    from apps.documents import processing
    from apps.documents.chunking import DocumentChunkInput
    from apps.documents.services import upload_document
    from apps.projects.services import create_project

    settings.MEDIA_ROOT = tmp_path
    actor = get_user_model().objects.create_user(email="large-reindex@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Large reindex", "project_type": "website"},
    )
    document = upload_document(
        project_id=project.pk,
        actor=actor,
        file=SimpleUploadedFile("large.txt", b"source"),
    )
    document.processing_status = "ready"
    document.save(update_fields=["processing_status"])
    profile = AIModelProfile.objects.get(
        task_key=AITask.DOCUMENT_EMBEDDING,
        is_default=True,
    )
    configured_limit = 150_000
    profile.parameters = {**profile.parameters, "max_input_bytes": configured_limit}
    profile.save()

    chunks = [
        DocumentChunkInput(
            chunk_index=index,
            content="Я🙂" * 500,
            page_number=None,
            metadata={},
        )
        for index in range(2049)
    ]
    monkeypatch.setattr(processing, "chunk_segments", lambda _segments: chunks)
    batches = []
    vector = [1.0, *([0.0] * 1535)]

    def fake_embed_texts(texts, *, task_key, project_id):
        batches.append((list(texts), task_key, project_id))
        return EmbeddingBatch(
            vectors=[vector] * len(texts),
            profile_key="embed-large-doc",
            profile_version=2,
            model_name="text-embedding-3-small",
        )

    monkeypatch.setattr(processing, "embed_texts", fake_embed_texts)
    stored = {}

    def capture_store_result(**kwargs):
        stored.update(kwargs)
        return SimpleNamespace(processing_status=kwargs["status"])

    monkeypatch.setattr(processing, "_store_result", capture_store_result)

    result = processing.process_document(
        document_id=document.pk,
        force_reindex=True,
    )

    assert result.processing_status == "ready"
    assert len(batches) > 1
    assert sum(len(batch[0]) for batch in batches) == 2049
    assert all(len(batch[0]) <= 2048 for batch in batches)
    assert all(
        sum(len(text.encode("utf-8")) for text in batch[0]) <= configured_limit
        for batch in batches
    )
    assert all(batch[1:] == ("document_embedding", project.pk) for batch in batches)
    assert len(stored["batch"].vectors) == 2049
    assert stored["batch"].profile_key == "embed-large-doc"
    assert stored["batch"].model_name == "text-embedding-3-small"


@pytest.mark.django_db
def test_reindex_fails_closed_if_sub_batches_change_vector_space(
    tmp_path, settings, monkeypatch
):
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.ai_assistant.embedding import EmbeddingBatch
    from apps.ai_assistant.models import AIModelProfile, AITask
    from apps.documents import processing
    from apps.documents.chunking import DocumentChunkInput
    from apps.documents.models import DocumentEmbedding
    from apps.documents.services import upload_document
    from apps.projects.services import create_project

    settings.MEDIA_ROOT = tmp_path
    actor = get_user_model().objects.create_user(email="mixed-reindex@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Mixed space reindex", "project_type": "website"},
    )
    document = upload_document(
        project_id=project.pk,
        actor=actor,
        file=SimpleUploadedFile("scope.txt", b"source"),
    )
    document.processing_status = "ready"
    document.save(update_fields=["processing_status"])
    profile = AIModelProfile.objects.get(
        task_key=AITask.DOCUMENT_EMBEDDING,
        is_default=True,
    )
    profile.parameters = {**profile.parameters, "max_input_bytes": 3}
    profile.save()
    chunks = [
        DocumentChunkInput(index, content, None, {})
        for index, content in enumerate(("abc", "def"))
    ]
    monkeypatch.setattr(processing, "chunk_segments", lambda _segments: chunks)
    calls = 0
    vector = [1.0, *([0.0] * 1535)]

    def change_space(texts, *, task_key, project_id):
        nonlocal calls
        calls += 1
        return EmbeddingBatch(
            vectors=[vector] * len(texts),
            profile_key=f"embed-space-{calls}",
            profile_version=1,
            model_name="text-embedding-3-small",
        )

    monkeypatch.setattr(processing, "embed_texts", change_space)
    result = processing.process_document(
        document_id=document.pk,
        force_reindex=True,
    )

    document.refresh_from_db()
    assert calls == 2
    assert result.processing_status == "failed"
    assert document.processing_status == "failed"
    assert not DocumentEmbedding.objects.filter(chunk__document=document).exists()


@pytest.mark.django_db(transaction=True)
def test_stale_processing_result_cannot_overwrite_newer_reindex(
    tmp_path, settings, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from hashlib import sha256
    from threading import Event, Lock
    from uuid import uuid4

    from django.contrib.auth import get_user_model
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    from django.db import close_old_connections, connection

    from apps.ai_assistant.embedding import EmbeddingBatch
    from apps.documents import processing, retrieval
    from apps.documents.models import Document, DocumentEmbedding
    from apps.projects.services import create_project

    assert connection.vendor == "postgresql"
    settings.MEDIA_ROOT = tmp_path
    actor = get_user_model().objects.create_user(email="fenced-reindex@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Fenced reindex", "project_type": "website"},
    )
    source = b"The newer reindex space must remain searchable."
    storage_key = default_storage.save(
        f"documents/{project.pk}/{uuid4()}",
        ContentFile(source),
    )
    document = Document.objects.create(
        project=project,
        uploaded_by=actor,
        original_filename="scope.txt",
        mime_type="text/plain",
        file_size=len(source),
        checksum_sha256=sha256(source).hexdigest(),
        storage_key=storage_key,
    )
    old_started = Event()
    release_old = Event()
    call_lock = Lock()
    calls = 0
    vector = [1.0, *([0.0] * 1535)]
    old_batch = EmbeddingBatch(
        vectors=[vector],
        profile_key="embed-stale-space",
        profile_version=1,
        model_name="text-embedding-3-small",
    )
    new_batch = EmbeddingBatch(
        vectors=[vector],
        profile_key="embed-current-space",
        profile_version=1,
        model_name="text-embedding-3-large",
    )

    def fake_embed_texts(texts, *, task_key, project_id):
        nonlocal calls
        with call_lock:
            calls += 1
            call_number = calls
        if call_number == 1:
            old_started.set()
            if not release_old.wait(timeout=10):
                raise TimeoutError("The stale embedding call was not released.")
            return old_batch
        return new_batch

    monkeypatch.setattr(processing, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(
        processing,
        "get_embedding_input_byte_limit",
        lambda **_kwargs: 200_000,
    )

    def run_normal_processing():
        close_old_connections()
        try:
            return processing.process_document(document_id=document.pk)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1) as executor:
        stale_future = executor.submit(run_normal_processing)
        assert old_started.wait(timeout=5)
        current_result = processing.process_document(
            document_id=document.pk,
            force_reindex=True,
        )
        release_old.set()
        stale_result = stale_future.result(timeout=10)

    document.refresh_from_db()
    assert current_result.processing_status == "ready"
    assert stale_result.processing_status == "ready"
    assert document.processing_generation == 2
    assert document.processing_status == "ready"
    assert (
        DocumentEmbedding.objects.filter(
            chunk__document=document,
            embedding_profile_key="embed-stale-space",
        ).count()
        == 0
    )
    assert (
        DocumentEmbedding.objects.filter(
            chunk__document=document,
            embedding_profile_key="embed-current-space",
            model_name="text-embedding-3-large",
        ).count()
        == 1
    )

    monkeypatch.setattr(retrieval, "embed_texts", lambda *_args, **_kwargs: new_batch)
    results = retrieval.retrieve_project_evidence(
        project_id=project.pk,
        actor=actor,
        query="current space",
    )
    assert results[0].content == "The newer reindex space must remain searchable."


@pytest.mark.django_db
def test_processing_without_router_keeps_document_unsearchable(
    tmp_path, settings, monkeypatch
):
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.ai_assistant.embedding import EmbeddingBatch, EmbeddingServiceUnavailable
    from apps.documents import processing
    from apps.documents.models import DocumentChunk, DocumentEmbedding
    from apps.documents.services import upload_document
    from apps.projects.services import create_project

    settings.MEDIA_ROOT = tmp_path
    actor = get_user_model().objects.create_user(email="unconfigured@example.com")
    project = create_project(
        actor=actor,
        data={"name": "No embedding route", "project_type": "website"},
    )
    document = upload_document(
        project_id=project.pk,
        actor=actor,
        file=SimpleUploadedFile("requirements.txt", b"A real requirement."),
    )

    def unavailable(*_args, **_kwargs):
        raise EmbeddingServiceUnavailable

    monkeypatch.setattr(processing, "embed_texts", unavailable)
    result = processing.process_document(document_id=document.pk)

    assert result.processing_status == "failed"
    assert DocumentChunk.objects.filter(document=document).count() == 1
    assert not DocumentEmbedding.objects.filter(chunk__document=document).exists()

    vector = [1.0, *([0.0] * 1535)]
    monkeypatch.setattr(
        processing,
        "embed_texts",
        lambda texts, **_kwargs: EmbeddingBatch(
            vectors=[vector for _ in texts],
            profile_key="document_embedding",
            profile_version=1,
            model_name="text-embedding-3-small",
        ),
    )
    retried = processing.process_document(document_id=document.pk)
    assert retried.processing_status == "ready"
    assert DocumentChunk.objects.filter(document=document).count() == 1
    assert DocumentEmbedding.objects.filter(chunk__document=document).count() == 1


@pytest.mark.django_db
def test_soft_timeout_marks_failed_and_lost_processing_attempt_can_be_retried(
    tmp_path, settings, monkeypatch
):
    from billiard.exceptions import SoftTimeLimitExceeded
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.ai_assistant.embedding import EmbeddingBatch
    from apps.documents import processing
    from apps.documents.models import Document, DocumentChunk, DocumentEmbedding
    from apps.documents.services import upload_document
    from apps.projects.services import create_project

    settings.MEDIA_ROOT = tmp_path
    actor = get_user_model().objects.create_user(email="timeout@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Timeout recovery", "project_type": "website"},
    )
    document = upload_document(
        project_id=project.pk,
        actor=actor,
        file=SimpleUploadedFile("scope.txt", b"One useful requirement."),
    )
    real_extractor = processing.extract_segments

    def time_out(*_args, **_kwargs):
        raise SoftTimeLimitExceeded

    monkeypatch.setattr(processing, "extract_segments", time_out)
    failed = processing.process_document(document_id=document.pk)
    assert failed.processing_status == "failed"
    assert not DocumentChunk.objects.filter(document=document).exists()

    document.processing_status = "processing"
    document.save(update_fields=["processing_status"])
    monkeypatch.setattr(processing, "extract_segments", real_extractor)
    vector = [1.0, *([0.0] * 1535)]
    monkeypatch.setattr(
        processing,
        "embed_texts",
        lambda texts, **_kwargs: EmbeddingBatch(
            vectors=[vector for _ in texts],
            profile_key="document_embedding",
            profile_version=1,
            model_name="text-embedding-3-small",
        ),
    )

    recovered = processing.process_document(document_id=document.pk)

    assert recovered.processing_status == "ready"
    assert Document.objects.get(pk=document.pk).processing_status == "ready"
    assert DocumentChunk.objects.filter(document=document).count() == 1
    assert DocumentEmbedding.objects.filter(chunk__document=document).count() == 1


@pytest.mark.django_db
def test_project_retrieval_returns_evidence_only_for_active_searchable_documents(
    tmp_path, settings, monkeypatch
):
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.ai_assistant.embedding import EmbeddingBatch
    from apps.documents import processing, retrieval
    from apps.documents.models import DocumentLifecycleStatus
    from apps.documents.services import upload_document
    from apps.projects.services import create_project

    settings.MEDIA_ROOT = tmp_path
    actor = get_user_model().objects.create_user(email="retrieval@example.com")
    project = create_project(
        actor=actor,
        data={"name": "Evidence", "project_type": "website"},
    )
    document = upload_document(
        project_id=project.pk,
        actor=actor,
        file=SimpleUploadedFile("scope.md", b"The site needs a contact form."),
    )
    vector = [1.0, *([0.0] * 1535)]
    batch = EmbeddingBatch(
        vectors=[vector],
        profile_key="document_embedding",
        profile_version=1,
        model_name="text-embedding-3-small",
    )
    monkeypatch.setattr(processing, "embed_texts", lambda *_args, **_kwargs: batch)
    processing.process_document(document_id=document.pk)
    monkeypatch.setattr(retrieval, "embed_texts", lambda *_args, **_kwargs: batch)

    results = retrieval.retrieve_project_evidence(
        project_id=project.pk,
        actor=actor,
        query="contact form",
    )

    assert len(results) == 1
    assert results[0].content == "The site needs a contact form."
    assert results[0].evidence.document_id == document.pk
    assert results[0].evidence.chunk_index == 0
    assert results[0].evidence.source_location == {"start_char": 0, "end_char": 30}
    wrong_version = EmbeddingBatch(
        vectors=[vector],
        profile_key="document_embedding",
        profile_version=2,
        model_name="text-embedding-3-small",
    )
    monkeypatch.setattr(
        retrieval,
        "embed_texts",
        lambda *_args, **_kwargs: wrong_version,
    )
    assert (
        retrieval.retrieve_project_evidence(
            project_id=project.pk,
            actor=actor,
            query="contact form",
        )
        == []
    )
    monkeypatch.setattr(retrieval, "embed_texts", lambda *_args, **_kwargs: batch)
    document.lifecycle_status = DocumentLifecycleStatus.ARCHIVE_PENDING
    document.save(update_fields=["lifecycle_status"])
    assert (
        retrieval.retrieve_project_evidence(
            project_id=project.pk,
            actor=actor,
            query="contact form",
        )
        == []
    )


@pytest.mark.django_db
def test_project_retrieval_hides_project_existence_from_nonmembers():
    from django.contrib.auth import get_user_model

    from apps.documents.retrieval import retrieve_project_evidence
    from apps.documents.services import DocumentNotFoundError
    from apps.projects.services import create_project

    owner = get_user_model().objects.create_user(email="evidence-owner@example.com")
    outsider = get_user_model().objects.create_user(
        email="evidence-outsider@example.com"
    )
    project = create_project(
        actor=owner,
        data={"name": "Private boundary", "project_type": "website"},
    )

    with pytest.raises(DocumentNotFoundError):
        retrieve_project_evidence(
            project_id=project.pk,
            actor=outsider,
            query="anything",
        )


@pytest.mark.django_db(transaction=True)
def test_upload_enqueues_processing_only_after_the_database_commit(tmp_path, settings):
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.db import transaction

    from apps.documents.services import upload_document
    from apps.projects.services import create_project

    settings.MEDIA_ROOT = tmp_path
    actor = get_user_model().objects.create_user(email="after-commit@example.com")
    project = create_project(
        actor=actor,
        data={"name": "After commit", "project_type": "website"},
    )

    with patch("apps.documents.tasks.process_project_document.delay") as queued:
        with transaction.atomic():
            document = upload_document(
                project_id=project.pk,
                actor=actor,
                file=SimpleUploadedFile("scope.txt", b"The work must persist."),
            )
            queued.assert_not_called()

        queued.assert_called_once_with(str(document.pk))
