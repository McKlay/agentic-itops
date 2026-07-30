from __future__ import annotations

import logging

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.config import Settings

logger = logging.getLogger(__name__)

# Module-level singleton — shared across all graph invocations within this process.
# Replaced by the Redis saver when REDIS_URL is configured (see get_checkpointer).
_GLOBAL_CHECKPOINTER: BaseCheckpointSaver = MemorySaver()


async def get_checkpointer(settings: Settings) -> BaseCheckpointSaver:
    """Resolve the conversation checkpointer using the priority cascade.

    Priority:
    1. **Redis** (``AsyncRedisSaver``) — if ``REDIS_URL`` is set and reachable.
       Backed by Azure Cache for Redis in production.  Provides durable,
       cross-process conversation checkpointing.
    2. **MemorySaver** fallback — in-process dict store, zero dependencies.
       Suitable for POC / local development.  State is lost on process restart.

    The resolved saver is returned (not the global singleton) so callers can
    pass it directly to ``graph.compile(checkpointer=...)``.
    """
    global _GLOBAL_CHECKPOINTER  # noqa: PLW0603

    if settings.redis_url:
        try:
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver  # type: ignore[import]

            saver: BaseCheckpointSaver = AsyncRedisSaver.from_conn_string(settings.redis_url)
            await saver.setup()  # type: ignore[attr-defined]
            logger.info("Checkpointer: AsyncRedisSaver (Azure Cache for Redis)")
            _GLOBAL_CHECKPOINTER = saver
            return saver
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Redis checkpointer unavailable (%s). Falling back to MemorySaver.", exc
            )

    logger.info("Checkpointer: MemorySaver (in-process fallback)")
    return _GLOBAL_CHECKPOINTER
