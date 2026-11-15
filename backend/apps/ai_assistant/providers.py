from dataclasses import dataclass

from .models import AICapability


@dataclass(frozen=True)
class ProviderCapabilities:
    capabilities: frozenset[str]


PROVIDER_CAPABILITIES = {
    "openai": ProviderCapabilities(
        capabilities=frozenset(
            {
                AICapability.TEXT_GENERATION,
                AICapability.EMBEDDINGS,
                AICapability.RERANKING,
            }
        )
    ),
    "deepseek": ProviderCapabilities(
        capabilities=frozenset(
            {
                AICapability.TEXT_GENERATION,
                AICapability.RERANKING,
            }
        )
    ),
}


def get_provider_capabilities(provider_key: str) -> ProviderCapabilities | None:
    return PROVIDER_CAPABILITIES.get(provider_key)
