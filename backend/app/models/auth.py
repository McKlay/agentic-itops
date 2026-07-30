from __future__ import annotations

from pydantic import BaseModel, Field


class CurrentUser(BaseModel):
    """Authenticated user identity extracted from the Entra ID JWT."""

    user_id: str
    email: str
    name: str
    roles: list[str] = Field(default_factory=list)
