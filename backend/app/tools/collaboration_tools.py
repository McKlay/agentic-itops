from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.connectors.teams import TeamsConnector

logger = logging.getLogger(__name__)


def make_collaboration_tools(teams: "TeamsConnector"):
    """Return a ``send_teams_notification`` handler closure bound to ``teams``."""

    async def send_teams_notification(
        title: str,
        body: str,
        action_url: str | None = None,
    ) -> dict[str, Any]:
        """Send an Adaptive Card notification to the configured Teams channel.

        Returns a result dict with ``sent: bool`` and ``title``.
        Falls back to logger-only when TEAMS_WEBHOOK_URL is not configured.
        """
        logger.debug("send_teams_notification title=%r", title)
        sent = await teams.send_card(title=title, body=body, action_url=action_url)
        return {"sent": sent, "title": title}

    return send_teams_notification
