import json
import os

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from ..embedding import EMBEDDING_DIMENSIONS
from ..models import AICapability


class ProviderCallError(Exception):
    def __init__(
        self,
        code: str,
        *,
        retryable: bool = False,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        actual_model: str | None = None,
    ):
        self.code = code
        self.retryable = retryable
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.actual_model = actual_model
        super().__init__(code)


def _client(timeout_seconds: int):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ProviderCallError("provider_credentials_missing")
    return OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=0)


def _normalize_error(error):
    if isinstance(error, AuthenticationError):
        return ProviderCallError("provider_authentication_failed")
    if isinstance(error, PermissionDeniedError):
        return ProviderCallError("provider_access_denied")
    if isinstance(error, RateLimitError):
        return ProviderCallError("provider_rate_limited", retryable=True)
    if isinstance(error, (APITimeoutError, APIConnectionError)):
        return ProviderCallError("provider_unavailable", retryable=True)
    if isinstance(error, InternalServerError):
        return ProviderCallError("provider_server_error", retryable=True)
    if isinstance(error, APIStatusError):
        if error.status_code == 404:
            return ProviderCallError("provider_model_unavailable")
        if error.status_code == 408:
            return ProviderCallError("provider_timeout", retryable=True)
        if error.status_code >= 500:
            return ProviderCallError("provider_server_error", retryable=True)
        return ProviderCallError("provider_request_rejected")
    return ProviderCallError("provider_response_invalid")


class OpenAIAdapter:
    provider_key = "openai"
    capabilities = frozenset(
        {
            AICapability.TEXT_GENERATION,
            AICapability.EMBEDDINGS,
            AICapability.RERANKING,
        }
    )

    _RERANK_SCHEMA = {
        "type": "object",
        "properties": {
            "ranked_candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer", "minimum": 0},
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["index", "score"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["ranked_candidates"],
        "additionalProperties": False,
    }

    @staticmethod
    def _response_usage(response, *, profile):
        usage = getattr(response, "usage", None)
        try:
            actual_model = getattr(response, "model", None) or profile.model_name
        except Exception:
            actual_model = profile.model_name
        return {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "actual_model": actual_model,
        }

    @staticmethod
    def _embedding_response_usage(response, *, profile):
        usage = getattr(response, "usage", None)
        try:
            actual_model = getattr(response, "model", None) or profile.model_name
        except Exception:
            actual_model = profile.model_name
        return {
            "input_tokens": getattr(usage, "prompt_tokens", None),
            "actual_model": actual_model,
        }

    def generate(self, *, profile, request):
        response_usage = None
        try:
            client = _client(int(profile.parameters.get("timeout_seconds", 30)))
            max_output_tokens = int(profile.parameters.get("max_output_tokens", 1024))
            kwargs = {
                "model": profile.model_name,
                "input": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_input},
                ],
                "max_output_tokens": max_output_tokens,
            }
            reasoning_effort = profile.parameters.get("reasoning_effort")
            if reasoning_effort:
                kwargs["reasoning"] = {"effort": reasoning_effort}
            if request.response_schema is not None:
                kwargs["text"] = {
                    "format": {
                        "type": "json_schema",
                        "name": "projectbridge_response",
                        "strict": True,
                        "schema": request.response_schema,
                    }
                }
            response = client.responses.create(**kwargs)
            response_usage = self._response_usage(response, profile=profile)
            output_text = response.output_text
            if not isinstance(output_text, str) or not output_text.strip():
                raise ProviderCallError("provider_response_invalid", **response_usage)
            return {
                "text": output_text,
                **response_usage,
            }
        except ProviderCallError:
            raise
        except Exception as exc:
            normalized = _normalize_error(exc)
            if response_usage is not None:
                raise ProviderCallError(
                    normalized.code,
                    retryable=normalized.retryable,
                    **response_usage,
                ) from None
            raise normalized from None

    def embed(self, *, profile, texts):
        if profile.parameters.get("dimensions", EMBEDDING_DIMENSIONS) != (
            EMBEDDING_DIMENSIONS
        ):
            raise ProviderCallError("embedding_dimensions_unsupported")
        if not texts or len(texts) > 2048:
            raise ProviderCallError("embedding_batch_invalid")
        response_usage = None
        try:
            client = _client(int(profile.parameters.get("timeout_seconds", 30)))
            response = client.embeddings.create(
                model=profile.model_name,
                input=texts,
                dimensions=EMBEDDING_DIMENSIONS,
                encoding_format="float",
            )
            response_usage = self._embedding_response_usage(response, profile=profile)
            try:
                vectors = [None] * len(texts)
                for row in response.data:
                    vectors[row.index] = list(row.embedding)
                if any(vector is None for vector in vectors):
                    raise ProviderCallError(
                        "provider_response_invalid", **response_usage
                    )
            except ProviderCallError:
                raise
            except Exception:
                raise ProviderCallError(
                    "provider_response_invalid", **response_usage
                ) from None
            return {
                "vectors": vectors,
                **response_usage,
            }
        except ProviderCallError:
            raise
        except Exception as exc:
            normalized = _normalize_error(exc)
            if response_usage is not None:
                raise ProviderCallError(
                    normalized.code,
                    retryable=normalized.retryable,
                    **response_usage,
                ) from None
            raise normalized from None

    def rerank(self, *, profile, query, candidates):
        if not candidates or len(candidates) > int(
            profile.parameters.get("max_candidates", 100)
        ):
            raise ProviderCallError("rerank_candidate_count_invalid")
        payload = json.dumps(
            {"query": query, "candidates": candidates},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        response_usage = None
        try:
            client = _client(int(profile.parameters.get("timeout_seconds", 45)))
            response = client.responses.create(
                model=profile.model_name,
                instructions=(
                    "Score every candidate for relevance to the query. Return each "
                    "original index exactly once and assign a numeric score from 0 "
                    "to 1, where higher means more relevant. Do not write an answer "
                    "to the query."
                ),
                input=payload,
                max_output_tokens=int(
                    profile.parameters.get("max_output_tokens", 4096)
                ),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "projectbridge_rerank_response",
                        "strict": True,
                        "schema": self._RERANK_SCHEMA,
                    }
                },
            )
            response_usage = self._response_usage(response, profile=profile)
            try:
                parsed = json.loads(response.output_text)
            except Exception:
                raise ProviderCallError(
                    "provider_response_invalid", **response_usage
                ) from None
            if not isinstance(parsed, dict) or not isinstance(
                parsed.get("ranked_candidates"), list
            ):
                raise ProviderCallError("provider_response_invalid", **response_usage)
            return {
                "ranked_candidates": parsed["ranked_candidates"],
                **response_usage,
            }
        except ProviderCallError:
            raise
        except Exception as exc:
            normalized = _normalize_error(exc)
            if response_usage is not None:
                raise ProviderCallError(
                    normalized.code,
                    retryable=normalized.retryable,
                    **response_usage,
                ) from None
            raise normalized from None
