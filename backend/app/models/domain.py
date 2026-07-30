from __future__ import annotations

from pydantic import BaseModel, Field


class IncidentRecord(BaseModel):
    """ServiceNow incident representation."""

    incident_id: str                                   # INC prefix
    sys_id: str = ""                                   # ServiceNow sys_id
    number: str = ""                                   # e.g. INC0001234
    short_description: str = ""
    description: str = ""
    state: str = "new"                                 # new | in_progress | resolved | closed
    priority: str = "3"                                # 1-critical … 5-planning
    category: str = ""
    assigned_to: str = ""
    assignment_group: str = ""
    caller_id: str = ""
    opened_at: str = ""
    resolved_at: str = ""
    close_notes: str = ""
    snow_url: str = ""                                 # direct browser link


class ProblemRecord(BaseModel):
    """ServiceNow problem representation."""

    problem_id: str                                    # PRB prefix
    sys_id: str = ""
    number: str = ""
    short_description: str = ""
    description: str = ""
    state: str = "open"                                # open | in_progress | resolved | closed
    known_error: bool = False
    root_cause: str = ""
    workaround: str = ""
    opened_at: str = ""
    snow_url: str = ""


class ChangeRecord(BaseModel):
    """ServiceNow change request."""

    change_id: str                                     # CHG prefix
    sys_id: str = ""
    number: str = ""
    short_description: str = ""
    description: str = ""
    state: str = "new"                                 # new | assess | authorize | implement | review | closed
    type: str = "normal"                               # normal | standard | emergency
    risk: str = "moderate"                             # low | moderate | high
    start_date: str = ""
    end_date: str = ""
    assigned_to: str = ""
    assignment_group: str = ""
    snow_url: str = ""


class KnowledgeArticle(BaseModel):
    """Knowledge base article — sourced from Azure AI Search / ServiceNow KB."""

    article_id: str                                    # ka_ prefix
    sys_id: str = ""
    number: str = ""                                   # e.g. KB0001234
    title: str = ""
    text: str = ""
    category: str = ""
    author: str = ""
    published_at: str = ""
    workflow_state: str = "review"                     # review | published | retired
    search_score: float | None = None                  # Azure AI Search @search.score
    snow_url: str = ""
