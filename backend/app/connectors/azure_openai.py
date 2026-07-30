from __future__ import annotations

import time
from typing import Any

from openai import AsyncAzureOpenAI

from app.config import Settings
from app.connectors.base import ConnectorBase, ConnectorHealth

# Embedding dimension for text-embedding-3-small (ka-embedding-model)
_EMBEDDING_DIM = 1536

# Fallback stub response returned when the connector is offline
_FALLBACK_RESPONSE_TEXT = (
    "I'm currently operating in offline mode. "
    "Please ensure AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are configured."
)


class _FallbackChoice:
    """Mimics openai.types.chat.ChatCompletionMessage enough for agent parsing."""

    class _Message:
        def __init__(self, content: str) -> None:
            self.content = content
            self.tool_calls: list = []
            self.role = "assistant"

    def __init__(self, content: str) -> None:
        self.message = self._Message(content)
        self.finish_reason = "stop"


class _FallbackCompletion:
    def __init__(self, text: str) -> None:
        self.choices = [_FallbackChoice(text)]
        self.model = "fallback"


class AzureOpenAIConnector(ConnectorBase):
    """Azure OpenAI connector for chat completions and embeddings.

    Chat model:      ``gpt-4.1``          (deployment: gpt-4.1)
    Embedding model: ``ka-embedding-model`` (backed by text-embedding-3-small, 1536-dim)

    Temperature conventions:
    - 0.2 — structured agent outputs (supervisor, critic, knowledge synthesis)
    - 0.7 — conversational / general_chat responses
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._client: AsyncAzureOpenAI | None = None

        if settings.azure_openai_endpoint and settings.azure_openai_api_key:
            self._client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
            self._live = True
            self.logger.info(
                "AzureOpenAIConnector live — endpoint=%s deployment=%s",
                settings.azure_openai_endpoint,
                settings.azure_openai_chat_deployment,
            )
        else:
            self.logger.warning(
                "AzureOpenAIConnector offline — AZURE_OPENAI_ENDPOINT or "
                "AZURE_OPENAI_API_KEY not set. Using fallback responses."
            )

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
    ) -> Any:
        """Call the chat completions endpoint.

        Returns an ``openai.types.chat.ChatCompletion``-compatible object.
        Falls back to a stub response when ``_live=False``.
        """
        if not self._require_live("chat_completion"):
            return _FallbackCompletion(_FALLBACK_RESPONSE_TEXT)

        assert self._client is not None
        kwargs: dict[str, Any] = dict(
            model=self._settings.azure_openai_chat_deployment,
            messages=messages,
            temperature=temperature,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return await self._client.chat.completions.create(**kwargs)

    async def embed(self, text: str) -> list[float]:
        """Return the embedding vector for *text*.

        Falls back to a zero vector of dimension 1536 when ``_live=False``.
        """
        if not self._require_live("embed"):
            return [0.0] * _EMBEDDING_DIM

        assert self._client is not None
        response = await self._client.embeddings.create(
            input=text,
            model=self._settings.azure_openai_embedding_deployment,
        )
        return response.data[0].embedding

    async def health_check(self) -> ConnectorHealth:
        if not self._live:
            return ConnectorHealth(
                name="azure_openai",
                connected=False,
                source="fallback",
                error="Not configured",
            )
        start = time.perf_counter()
        try:
            # Lightweight probe — embed a short string
            assert self._client is not None
            await self._client.embeddings.create(
                input="ping",
                model=self._settings.azure_openai_embedding_deployment,
            )
            latency = int((time.perf_counter() - start) * 1000)
            return ConnectorHealth(
                name="azure_openai", connected=True, source="live", latency_ms=latency
            )
        except Exception as exc:  # noqa: BLE001
            return ConnectorHealth(
                name="azure_openai",
                connected=False,
                source="fallback",
                error=str(exc),
            )
