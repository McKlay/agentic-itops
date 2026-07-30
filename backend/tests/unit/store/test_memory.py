from __future__ import annotations

"""Unit tests — InMemoryStore CRUD operations."""

import pytest
import pytest_asyncio

from app.models.chat import MessageRecord, OperationalThread
from app.store.memory import InMemoryStore


@pytest_asyncio.fixture()
async def store() -> InMemoryStore:
    s = InMemoryStore()
    await s.seed()
    return s


@pytest.mark.asyncio
async def test_seed_populates_incidents(store: InMemoryStore) -> None:
    """Seeded store contains demo incidents."""
    incidents = await store.list_incidents()
    assert len(incidents) >= 3


@pytest.mark.asyncio
async def test_seed_populates_knowledge_articles(store: InMemoryStore) -> None:
    """Seeded store contains demo knowledge articles."""
    assert len(store._knowledge) >= 3


@pytest.mark.asyncio
async def test_add_and_get_thread(store: InMemoryStore) -> None:
    """Threads can be added and retrieved."""
    thread = OperationalThread(
        thread_id="thr_test_store",
        user_id="test@test.com",
        title="Test thread",
    )
    await store.add_thread(thread)
    result = await store.get_thread("thr_test_store")
    assert result is not None
    assert result.thread_id == "thr_test_store"


@pytest.mark.asyncio
async def test_add_and_get_messages(store: InMemoryStore) -> None:
    """Messages can be added and retrieved for a thread."""
    msg = MessageRecord(
        message_id="msg_test_001",
        thread_id="thr_demo_001",
        role="user",
        content="Hello, world!",
    )
    await store.add_message(msg)
    messages = await store.get_messages("thr_demo_001")
    assert any(m.message_id == "msg_test_001" for m in messages)


@pytest.mark.asyncio
async def test_get_nonexistent_thread(store: InMemoryStore) -> None:
    """Getting a non-existent thread returns None."""
    result = await store.get_thread("thr_nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_audit_log_grows(store: InMemoryStore) -> None:
    """Adding a thread creates an audit event."""
    initial_count = len(store._audit)
    thread = OperationalThread(
        thread_id="thr_audit_test",
        user_id="auditor@test.com",
    )
    await store.add_thread(thread)
    assert len(store._audit) > initial_count
