from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import Settings
from app.connectors.base import ConnectorBase, ConnectorHealth

# Adaptive Card v1.4 template
_CARD_SCHEMA = "http://adaptivecards.io/schemas/adaptive-card.json"
_CARD_VERSION = "1.4"


class TeamsConnector(ConnectorBase):
    """Microsoft Teams Incoming Webhook connector — Adaptive Card v1.4.

    Fallback: logs the notification event to the Python logger (and expects
    the caller to separately call ``store.log_event()`` for auditability).
    Activate: set ``TEAMS_WEBHOOK_URL`` in .env.
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._webhook_url = settings.teams_webhook_url or ""

        if self._webhook_url:
            self._live = True
            self.logger.info("TeamsConnector live — webhook configured")
        else:
            self.logger.warning(
                "TeamsConnector offline — TEAMS_WEBHOOK_URL not set. "
                "Notifications will be logged only."
            )

    async def send_card(
        self,
        title: str,
        body: str,
        action_url: str | None = None,
        action_label: str = "View in ServiceNow",
    ) -> bool:
        """Post an Adaptive Card to the Teams channel.

        Returns ``True`` on success, ``False`` in fallback mode.
        """
        if not self._require_live("send_card"):
            self.logger.info(
                "Teams notification (fallback — not sent): title=%r", title
            )
            return False

        card_payload = self._build_card(title, body, action_url, action_label)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._webhook_url,
                json=card_payload,
                timeout=10,
            )
            resp.raise_for_status()
        self.logger.info("Teams notification sent: title=%r", title)
        return True

    def _build_card(
        self,
        title: str,
        body: str,
        action_url: str | None,
        action_label: str,
    ) -> dict[str, Any]:
        """Build a minimal Adaptive Card v1.4 payload."""
        body_blocks: list[dict[str, Any]] = [
            {"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": title},
            {"type": "TextBlock", "wrap": True, "text": body},
        ]
        actions: list[dict[str, Any]] = []
        if action_url:
            actions.append(
                {"type": "Action.OpenUrl", "title": action_label, "url": action_url}
            )

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": _CARD_SCHEMA,
                        "type": "AdaptiveCard",
                        "version": _CARD_VERSION,
                        "body": body_blocks,
                        "actions": actions,
                    },
                }
            ],
        }

    async def health_check(self) -> ConnectorHealth:
        if not self._live:
            return ConnectorHealth(
                name="teams",
                connected=False,
                source="fallback",
                error="Not configured",
            )
        # Teams webhooks have no status endpoint — treat presence of URL as healthy
        return ConnectorHealth(name="teams", connected=True, source="live", latency_ms=0)
