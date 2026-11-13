import json
import re
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from config.asgi import application


class DeterministicProvider:
    capabilities = frozenset({"text_generation", "embeddings", "reranking"})

    def __init__(self):
        self.analysis_contexts = []

    def generate(self, *, profile, request):
        if request.response_schema is not None:
            context = json.loads(request.user_input)
            self.analysis_contexts.append(context)
            document_evidence = next(
                (
                    row
                    for row in context["evidence"]
                    if row["source_type"] == "document_chunk"
                ),
                None,
            )
            result = {"proposals": []}
            if document_evidence is not None:
                result["proposals"].append(
                    {
                        "proposal_type": "requirement_create",
                        "title": "Add account recovery",
                        "description": "Let customers recover access securely.",
                        "rationale": "The shared document describes this workflow.",
                        "payload": {
                            "title": "Add account recovery",
                            "description": "Let customers recover access securely.",
                            "question": "",
                        },
                        "evidence_refs": [
                            {
                                "source_type": "document_chunk",
                                "source_id": document_evidence["source_id"],
                            }
                        ],
                    }
                )
            text = json.dumps(result)
        else:
            text = (
                "# Support portal MVP\n\nProvide account recovery and support requests."
            )
        return {
            "text": text,
            "input_tokens": 90,
            "output_tokens": 32,
            "actual_model": profile.model_name,
        }

    def embed(self, *, profile, texts):
        return {
            "vectors": [[1.0, *([0.0] * 1535)] for _ in texts],
            "input_tokens": max(1, len(texts) * 8),
            "output_tokens": 0,
            "actual_model": profile.model_name,
        }

    def rerank(self, *, profile, query, candidates):
        return {
            "ranked_candidates": [
                {"index": index, "score": float(len(candidates) - index)}
                for index in range(len(candidates))
            ],
            "input_tokens": max(1, len(query) + sum(map(len, candidates))),
            "output_tokens": 0,
            "actual_model": profile.model_name,
        }


def _configure_stage13_fake_ai_profiles():
    """Provide test router config even after transactional tests flush seed rows."""
    from apps.ai_assistant.models import AIModelProfile, AITask

    profile_configs = {
        AITask.DOCUMENT_EMBEDDING: (
            "stage13-document-embedding",
            "text-embedding-3-small",
            ["embeddings"],
            {
                "dimensions": 1536,
                "input_usd_per_million_tokens": "0",
                "output_usd_per_million_tokens": "0",
                "max_input_bytes": 100_000,
                "max_output_tokens": 0,
                "timeout_seconds": 30,
                "max_request_cost_usd": "1",
                "daily_budget_usd": "10",
            },
        ),
        AITask.CONTRADICTION_DETECTION: (
            "stage13-contradiction-analysis",
            "gpt-6-luna",
            ["text_generation"],
            {
                "input_usd_per_million_tokens": "0",
                "output_usd_per_million_tokens": "0",
                "max_input_bytes": 100_000,
                "max_output_tokens": 2048,
                "timeout_seconds": 30,
                "max_request_cost_usd": "1",
                "daily_budget_usd": "10",
            },
        ),
        AITask.SPECIFICATION_GENERATION: (
            "stage13-specification-generation",
            "gpt-6-luna",
            ["text_generation"],
            {
                "input_usd_per_million_tokens": "0",
                "output_usd_per_million_tokens": "0",
                "max_input_bytes": 100_000,
                "max_output_tokens": 2048,
                "timeout_seconds": 30,
                "max_request_cost_usd": "1",
                "daily_budget_usd": "10",
            },
        ),
    }
    for task_key, (
        profile_key,
        model_name,
        capabilities,
        parameters,
    ) in profile_configs.items():
        profile = AIModelProfile.objects.filter(
            task_key=task_key, is_default=True
        ).first()
        if profile is None:
            profile = AIModelProfile.objects.filter(task_key=task_key).first()
        if profile is None:
            profile = AIModelProfile(profile_key=profile_key, task_key=task_key)
        AIModelProfile.objects.filter(task_key=task_key, is_default=True).exclude(
            pk=profile.pk
        ).update(is_default=False)
        profile.provider_key = "openai"
        profile.model_name = model_name
        profile.capabilities = capabilities
        profile.parameters = parameters
        profile.fallback_profile = None
        profile.is_default = True
        profile.is_enabled = True
        profile.save()


def _csrf(client):
    response = client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    return response.data["csrf_token"]


def _post(client, path, data=None, **headers):
    return client.post(
        path,
        {} if data is None else data,
        format="json",
        HTTP_X_CSRFTOKEN=_csrf(client),
        **headers,
    )


def _get(client, path):
    return client.get(path)


def _patch(client, path, data):
    return client.patch(
        path,
        data,
        format="json",
        HTTP_X_CSRFTOKEN=_csrf(client),
    )


def _register_verify_login(client, email):
    password = "A safe project password 2026!"
    registered = _post(
        client,
        "/api/v1/auth/register/",
        {"email": email, "password": password},
    )
    assert registered.status_code == 201
    token = re.search(r"#token=([A-Za-z0-9_-]+)", mail.outbox[-1].body).group(1)
    verified = _post(
        client,
        "/api/v1/auth/email-verification/confirm/",
        {"token": token},
    )
    assert verified.status_code == 200
    assert verified.data["email_verified"] is True
    logged_in = _post(
        client,
        "/api/v1/auth/login/",
        {"email": email, "password": password},
    )
    assert logged_in.status_code == 200
    assert client.cookies[settings.SESSION_COOKIE_NAME].value
    return client


def _websocket_headers(client):
    cookie = client.cookies[settings.SESSION_COOKIE_NAME].value
    return [
        (b"origin", settings.FRONTEND_BASE_URL.encode()),
        (
            b"cookie",
            f"{settings.SESSION_COOKIE_NAME}={cookie}".encode(),
        ),
    ]


@pytest.mark.django_db(transaction=True)
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    FRONTEND_BASE_URL="http://localhost:5173",
)
def test_stage13_two_member_workflow_through_public_apis_and_real_sessions(
    settings, tmp_path, monkeypatch
):
    from apps.ai_assistant import router
    from apps.ai_assistant import tasks as ai_tasks
    from apps.chat.models import Message
    from apps.documents import services as document_services
    from apps.documents import tasks as document_tasks
    from apps.documents.models import Document, DocumentChunk, DocumentLifecycleRequest
    from apps.projects.models import Project
    from apps.specifications import tasks as specification_tasks

    settings.MEDIA_ROOT = tmp_path
    _configure_stage13_fake_ai_profiles()
    mail.outbox.clear()
    executor_client = _register_verify_login(
        APIClient(enforce_csrf_checks=True), "stage13-executor@example.com"
    )
    customer_client = _register_verify_login(
        APIClient(enforce_csrf_checks=True), "stage13-customer@example.com"
    )

    created_project = _post(
        executor_client,
        "/api/v1/projects/",
        {"name": "Stage 13 support portal", "project_type": "website"},
    )
    assert created_project.status_code == 201
    project_id = created_project.data["id"]

    invited = _post(
        executor_client,
        f"/api/v1/projects/{project_id}/invitations/",
        {"invited_email": "stage13-customer@example.com"},
    )
    assert invited.status_code == 201
    invitation_token = re.search(
        r"/invite/#token=([A-Za-z0-9_-]+)", mail.outbox[-1].body
    ).group(1)
    preview = _post(
        customer_client,
        "/api/v1/invitations/preview/",
        {"token": invitation_token},
    )
    assert preview.status_code == 200
    assert preview.data["project_name"] == "Stage 13 support portal"
    accepted = _post(
        customer_client,
        "/api/v1/invitations/accept/",
        {"token": invitation_token},
    )
    assert accepted.status_code == 200
    assert accepted.data["project_id"] == project_id
    assert (
        _get(executor_client, f"/api/v1/projects/{project_id}/").data["status"]
        == "active"
    )

    submission = _post(
        customer_client,
        f"/api/v1/projects/{project_id}/questionnaire/submissions/",
    )
    assert submission.status_code == 201
    submission_id = submission.data["id"]
    answers = {
        "goal": "Launch a self-service support portal",
        "target_audience": "Returning customers",
        "expected_result": "Reduce routine support requests",
        "functional_scope": "Customer accounts and support requests",
        "has_integrations": False,
        "integrations": [],
        "constraints": "Keep the existing sign-in flow",
        "deadline": "2027-03-01",
        "has_existing_site": False,
    }
    saved_answers = _patch(
        customer_client,
        f"/api/v1/questionnaire/submissions/{submission_id}/answers/",
        {"answers": answers},
    )
    assert saved_answers.status_code == 200
    submitted = _post(
        customer_client,
        f"/api/v1/questionnaire/submissions/{submission_id}/submit/",
    )
    assert submitted.status_code == 200
    assert submitted.data["status"] == "submitted"
    passport = _get(executor_client, f"/api/v1/projects/{project_id}/passport/")
    assert passport.status_code == 200
    assert passport.data["goal"] == answers["goal"]

    stage = _post(
        executor_client,
        f"/api/v1/projects/{project_id}/stages/",
        {"name": "Discovery", "description": "Confirm shared scope"},
    )
    requirement = _post(
        executor_client,
        f"/api/v1/projects/{project_id}/requirements/",
        {"title": "Support account recovery"},
    )
    assert stage.status_code == 201
    assert requirement.status_code == 201
    state_url = f"/api/v1/projects/{project_id}/state/"
    customer_state = _get(customer_client, state_url)
    assert customer_state.status_code == 200
    assert customer_state.data["counts"]["stages"] == 1
    assert customer_state.data["counts"]["requirements"] == 1
    assert not any("percent" in key.lower() for key in customer_state.data)
    customer_write = _post(
        customer_client,
        f"/api/v1/projects/{project_id}/stages/",
        {"name": "Unauthorized stage"},
    )
    assert customer_write.status_code == 403
    assert customer_write.data["request_id"]

    foreign_project = _post(
        executor_client,
        "/api/v1/projects/",
        {"name": "Unrelated project", "project_type": "other"},
    )
    assert foreign_project.status_code == 201
    foreign_project_id = foreign_project.data["id"]
    customer_socket = WebsocketCommunicator(
        application,
        f"/ws/v1/projects/{project_id}/chat/",
        headers=_websocket_headers(customer_client),
    )
    foreign_socket = WebsocketCommunicator(
        application,
        f"/ws/v1/projects/{foreign_project_id}/chat/",
        headers=_websocket_headers(customer_client),
    )
    sent_message_id = str(uuid4())

    async def verify_chat_session_and_project_isolation():
        connected, _ = await customer_socket.connect()
        assert connected is True
        foreign_connected, _ = await foreign_socket.connect()
        assert foreign_connected is False
        sent = await sync_to_async(_post, thread_sensitive=True)(
            executor_client,
            f"/api/v1/projects/{project_id}/messages/",
            {
                "client_message_id": sent_message_id,
                "content": "The shared scope is ready for review.",
            },
        )
        assert sent.status_code == 201
        event = await customer_socket.receive_json_from(timeout=5)
        assert event["type"] == "message.created"
        assert event["message"]["client_message_id"] == sent_message_id
        await customer_socket.disconnect()
        return sent.data

    first_message = async_to_sync(verify_chat_session_and_project_isolation)()
    customer_reply = _post(
        customer_client,
        f"/api/v1/projects/{project_id}/messages/",
        {
            "client_message_id": str(uuid4()),
            "content": "I confirm the shared scope.",
        },
    )
    history = _get(customer_client, f"/api/v1/projects/{project_id}/messages/")
    assert customer_reply.status_code == 201
    assert history.status_code == 200
    assert {row["id"] for row in history.data["results"]} >= {
        first_message["id"],
        customer_reply.data["id"],
    }
    assert Message.objects.filter(project_id=project_id).count() == 2

    provider = DeterministicProvider()
    monkeypatch.setattr(router, "_adapter_for", lambda _provider_key: provider)
    document_publications = []
    monkeypatch.setattr(
        document_tasks.process_project_document,
        "apply_async",
        lambda *, args, task_id: document_publications.append((args, task_id)),
    )
    uploaded_bytes = b"# Support scope\nShared account and request workflows.\n"
    uploaded = executor_client.post(
        f"/api/v1/projects/{project_id}/documents/",
        {
            "file": SimpleUploadedFile(
                "support-scope.md", uploaded_bytes, content_type="text/markdown"
            )
        },
        format="multipart",
        HTTP_X_CSRFTOKEN=_csrf(executor_client),
    )
    assert uploaded.status_code == 201
    document_id = uploaded.data["id"]
    assert uploaded.data["processing_status"] == "queued"
    assert len(document_publications) == 1
    processed = document_tasks.process_project_document.run(document_id, 0)
    assert processed == "ready"
    customer_documents = _get(
        customer_client, f"/api/v1/projects/{project_id}/documents/"
    )
    assert customer_documents.status_code == 200
    assert customer_documents.data["results"][0]["id"] == document_id
    downloaded = _get(customer_client, f"/api/v1/documents/{document_id}/download/")
    assert downloaded.status_code == 200
    assert b"".join(downloaded.streaming_content) == uploaded_bytes

    analysis_publications = []
    monkeypatch.setattr(
        ai_tasks.analyze_project,
        "apply_async",
        lambda *, args, task_id: analysis_publications.append((args, task_id)),
    )
    private_history = _get(
        customer_client, f"/api/v1/projects/{project_id}/ai/analyses/"
    )
    assert private_history.status_code == 403
    analysis_request = _post(
        executor_client,
        f"/api/v1/projects/{project_id}/ai/analyses/",
        {},
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    assert analysis_request.status_code == 202
    assert len(analysis_publications) == 1
    hidden_request = _get(
        customer_client,
        f"/api/v1/projects/{project_id}/ai/analyses/{analysis_request.data['id']}/",
    )
    assert hidden_request.status_code == 403
    assert ai_tasks.analyze_project.run(*analysis_publications[0][0]) == "succeeded"
    proposals = _get(executor_client, f"/api/v1/projects/{project_id}/ai/proposals/")
    assert proposals.status_code == 200
    assert proposals.data["count"] == 1
    proposal = proposals.data["results"][0]
    proposal_id = proposal["id"]
    retrieved_chunk = next(
        row
        for row in provider.analysis_contexts[0]["evidence"]
        if row["source_type"] == "document_chunk"
    )
    retrieved_document_chunk = DocumentChunk.objects.get(
        pk=retrieved_chunk["source_id"], document_id=document_id
    )
    assert "Shared account and request workflows." in retrieved_document_chunk.content
    assert any(
        evidence["source_type"] == "document_chunk"
        and evidence["source_id"] == retrieved_chunk["source_id"]
        for evidence in proposal["evidence"]
    )
    assert "Shared account and request workflows." in next(
        evidence["excerpt"]
        for evidence in proposal["evidence"]
        if evidence["source_type"] == "document_chunk"
    )
    assert (
        _get(
            customer_client, f"/api/v1/projects/{project_id}/ai/proposals/"
        ).status_code
        == 403
    )
    assert (
        _post(
            customer_client, f"/api/v1/ai/proposals/{proposal_id}/accept/"
        ).status_code
        == 403
    )
    before_review = _get(
        customer_client, f"/api/v1/projects/{project_id}/requirements/"
    )
    assert before_review.status_code == 200
    assert all(
        row["title"] != "Add account recovery" for row in before_review.data["results"]
    )
    accepted_proposal = _post(
        executor_client, f"/api/v1/ai/proposals/{proposal_id}/accept/"
    )
    assert accepted_proposal.status_code == 200
    assert accepted_proposal.data["status"] == "applied"
    after_review = _get(customer_client, f"/api/v1/projects/{project_id}/requirements/")
    assert any(
        row["title"] == "Add account recovery" for row in after_review.data["results"]
    )

    archive_request = _post(
        executor_client,
        f"/api/v1/documents/{document_id}/lifecycle-requests/",
        {"action": "archive"},
    )
    assert archive_request.status_code == 201
    archive_approved = _post(
        customer_client,
        f"/api/v1/document-lifecycle-requests/{archive_request.data['id']}/approve/",
    )
    assert archive_approved.status_code == 200
    assert (
        _get(executor_client, f"/api/v1/documents/{document_id}/").data[
            "lifecycle_status"
        ]
        == "archived"
    )
    assert DocumentChunk.objects.filter(document_id=document_id).exists()
    archived_analysis_request = _post(
        executor_client,
        f"/api/v1/projects/{project_id}/ai/analyses/",
        {},
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    assert archived_analysis_request.status_code == 202
    assert len(analysis_publications) == 2
    assert ai_tasks.analyze_project.run(*analysis_publications[1][0]) == "succeeded"
    archived_analysis = _get(
        executor_client,
        f"/api/v1/projects/{project_id}/ai/analyses/{archived_analysis_request.data['id']}/",
    )
    assert archived_analysis.status_code == 200
    assert archived_analysis.data["status"] == "succeeded"
    assert archived_analysis.data["result_count"] == 0
    assert not any(
        row["source_type"] == "document_chunk"
        for row in provider.analysis_contexts[1]["evidence"]
    )
    assert (
        _get(executor_client, f"/api/v1/projects/{project_id}/ai/proposals/").data[
            "count"
        ]
        == 1
    )
    restored = _post(executor_client, f"/api/v1/documents/{document_id}/restore/")
    assert restored.status_code == 200
    assert restored.data["lifecycle_status"] == "active"

    archive_again = _post(
        executor_client,
        f"/api/v1/documents/{document_id}/lifecycle-requests/",
        {"action": "archive"},
    )
    assert archive_again.status_code == 201
    assert (
        _post(
            customer_client,
            f"/api/v1/document-lifecycle-requests/{archive_again.data['id']}/approve/",
        ).status_code
        == 200
    )
    deletion_request = _post(
        customer_client,
        f"/api/v1/documents/{document_id}/lifecycle-requests/",
        {"action": "permanent_delete"},
    )
    assert deletion_request.status_code == 201
    deletion_approved = _post(
        executor_client,
        f"/api/v1/document-lifecycle-requests/{deletion_request.data['id']}/approve/",
    )
    assert deletion_approved.status_code == 200
    deletion_after = datetime.fromisoformat(
        deletion_approved.data["deletion_after"].replace("Z", "+00:00")
    )
    with monkeypatch.context() as patcher:
        patcher.setattr(
            document_services.timezone,
            "now",
            lambda: deletion_after + timedelta(seconds=1),
        )
        assert document_tasks.process_expired_document_deletions.run() == 1
    assert _get(customer_client, f"/api/v1/documents/{document_id}/").status_code == 404
    assert (
        _get(executor_client, f"/api/v1/documents/{document_id}/download/").status_code
        == 404
    )
    assert Document.objects.get(pk=document_id).lifecycle_status == "deleted"
    assert (
        DocumentLifecycleRequest.objects.get(pk=deletion_request.data["id"]).status
        == "completed"
    )

    specification_publications = []
    monkeypatch.setattr(
        specification_tasks.generate_specification,
        "apply_async",
        lambda *, args, task_id: specification_publications.append((args, task_id)),
    )
    generated = _post(
        executor_client,
        f"/api/v1/projects/{project_id}/specification/generate/",
        {},
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    assert generated.status_code == 202
    assert len(specification_publications) == 1
    assert (
        _post(
            customer_client,
            f"/api/v1/projects/{project_id}/specification/generate/",
            {},
            HTTP_IDEMPOTENCY_KEY=str(uuid4()),
        ).status_code
        == 403
    )
    assert (
        specification_tasks.generate_specification.run(
            *specification_publications[0][0]
        )
        == "succeeded"
    )
    executor_specification = _get(
        executor_client, f"/api/v1/projects/{project_id}/specification/"
    )
    customer_specification = _get(
        customer_client, f"/api/v1/projects/{project_id}/specification/"
    )
    assert executor_specification.status_code == 200
    assert customer_specification.status_code == 200
    assert "account recovery" in executor_specification.data["content"].lower()
    assert customer_specification.data["generation"] is None
    assert (
        _patch(
            customer_client,
            f"/api/v1/projects/{project_id}/specification/",
            {"content": "Unauthorized", "version": 2},
        ).status_code
        == 403
    )

    completed = _post(executor_client, f"/api/v1/projects/{project_id}/complete/")
    assert completed.status_code == 200
    assert completed.data["status"] == "completed"
    archived_project = _post(executor_client, f"/api/v1/projects/{project_id}/archive/")
    assert archived_project.status_code == 200
    restored_project = _post(executor_client, f"/api/v1/projects/{project_id}/restore/")
    assert restored_project.status_code == 200
    assert restored_project.data["status"] == "completed"
    reopened = _post(executor_client, f"/api/v1/projects/{project_id}/reopen/")
    assert reopened.status_code == 200
    assert reopened.data["status"] == "active"

    assert (
        _get(executor_client, f"/api/v1/projects/{project_id}/").data["status"]
        == "active"
    )
    assert Project.objects.get(pk=project_id).memberships.count() == 2
