from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- ServiceNow ---
    snow_instance_url: str = ""
    servicenow_username: str = ""
    servicenow_password: str = ""

    # --- Azure OpenAI ---
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_chat_deployment: str = "gpt-4.1"
    azure_openai_embedding_deployment: str = "ka-embedding-model"
    azure_openai_api_version: str = "2025-01-01-preview"

    # --- Azure AI Search ---
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index_name: str = "ka-vector"

    # --- Azure Blob Storage (KB source PDFs — SAS token generation) ---
    # Uncomment and configure when clickable KB source links are needed.
    # azure_storage_account_name: str = ""   # e.g. clstorageaikmka1
    # azure_storage_account_key: str = ""    # Storage account key
    # azure_storage_sas_ttl_hours: int = 2   # SAS URL validity window

    # --- Entra ID ---
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    auth_disabled: bool = False

    # --- Teams ---
    teams_webhook_url: str = ""

    # --- Memory Tier 1 (Redis checkpointer) ---
    redis_url: str = ""  # e.g. rediss://:password@host:6380/0

    # --- Memory Tier 3 (Domain Store) ---
    storage_backend: str = "memory"  # "memory" | "cosmos" | "azure_table"
    cosmos_connection_string: str = ""
    cosmos_database: str = "ai-ops-agent"
    azure_table_connection_string: str = ""

    # --- Application ---
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = {"env_file": ".env", "case_sensitive": False}
