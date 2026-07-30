from __future__ import annotations

"""Unit tests — AzureOpenAIConnector fallback mode."""

import pytest

from app.config import Settings
from app.connectors.azure_openai import AzureOpenAIConnector, _EMBEDDING_DIM


@pytest.fixture()
def connector() -> AzureOpenAIConnector:
    conn = AzureOpenAIConnector(Settings(auth_disabled=True, storage_backend="memory"))
    conn._live = False
    conn._client = None
    return conn


@pytest.mark.asyncio
async def test_fallback_chat_completion(connector: AzureOpenAIConnector) -> None:
    """Offline LLM returns a fallback completion with the expected structure."""
    response = await connector.chat_completion(
        messages=[{"role": "user", "content": "hello"}],
    )
    assert hasattr(response, "choices")
    assert len(response.choices) == 1
    assert response.choices[0].message.content
    assert response.choices[0].finish_reason == "stop"


@pytest.mark.asyncio
async def test_fallback_embed(connector: AzureOpenAIConnector) -> None:
    """Offline embed returns a zero vector of the correct dimension."""
    vector = await connector.embed("test query")
    assert isinstance(vector, list)
    assert len(vector) == _EMBEDDING_DIM
    assert all(v == 0.0 for v in vector)
