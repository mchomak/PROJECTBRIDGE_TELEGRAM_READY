from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TextGenerationRequest:
    system_prompt: str
    user_input: str
    prompt_version: str
    response_schema: dict | None = None


@dataclass(frozen=True)
class TextGenerationResponse:
    text: str
    parsed: dict | list | None
    provider_key: str
    model_name: str
    profile_key: str
    profile_version: int
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost: str | None


@dataclass(frozen=True)
class RerankedCandidate:
    index: int
    score: float


class TextGenerationCapability(Protocol):
    def generate(self, *, profile, request: TextGenerationRequest): ...


class EmbeddingCapability(Protocol):
    def embed(self, *, profile, texts: list[str]): ...


class RerankingCapability(Protocol):
    def rerank(self, *, profile, query: str, candidates: list[str]): ...
