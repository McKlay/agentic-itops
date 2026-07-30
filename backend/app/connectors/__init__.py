from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.connectors.azure_openai import AzureOpenAIConnector
from app.connectors.azure_search import AzureSearchConnector
from app.connectors.servicenow import ServiceNowConnector
from app.connectors.teams import TeamsConnector
from app.store.base import DomainStoreInterface


@dataclass
class ConnectorBundle:
    """All connectors bundled for injection into app.state and services."""

    servicenow: ServiceNowConnector
    azure_openai: AzureOpenAIConnector
    azure_search: AzureSearchConnector
    teams: TeamsConnector


def build_connectors(settings: Settings, store: DomainStoreInterface) -> ConnectorBundle:
    """Instantiate and return all connectors.

    Each connector self-configures based on env vars — no live calls are made here.
    Health status is reported by ``GET /healthz`` once the app is running.

    ``store`` is accepted for forward-compatibility (e.g. ``TeamsConnector`` may call
    ``store.log_event()`` in a future iteration when constructing fallback audit entries).
    """
    return ConnectorBundle(
        servicenow=ServiceNowConnector(settings),
        azure_openai=AzureOpenAIConnector(settings),
        azure_search=AzureSearchConnector(settings),
        teams=TeamsConnector(settings),
    )
