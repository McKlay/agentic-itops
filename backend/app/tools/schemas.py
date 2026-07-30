from __future__ import annotations

# ---------------------------------------------------------------------------
# OpenAI function-call schemas for all registered tools.
#
# Format: {"type": "function", "function": {name, description, parameters}}
# Agents pass a subset of these to chat_completion(tools=[...]).
# ---------------------------------------------------------------------------

HYBRID_SEARCH_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "hybrid_search",
        "description": (
            "Search the IT Operations knowledge base using hybrid BM25 keyword "
            "+ vector semantic search. Returns ranked articles with citations. "
            "Use this to find relevant runbooks, procedures, and known-error workarounds."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query describing the issue or topic.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Default is 5.",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}

GET_ARTICLE_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "get_article",
        "description": (
            "Retrieve the full text of a knowledge base article chunk by its chunk_id. "
            "Use after hybrid_search when you need the complete chunk content."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "article_id": {
                    "type": "string",
                    "description": "chunk_id from a hybrid_search result (e.g. ka_0001_chunk_0).",
                },
            },
            "required": ["article_id"],
        },
    },
}

LOOKUP_INCIDENT_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "lookup_incident",
        "description": (
            "Look up a ServiceNow incident by its number or sys_id. "
            "Returns incident fields: state, priority, description, assignment group, etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "Incident number (e.g. INC0012345) or ServiceNow sys_id.",
                },
            },
            "required": ["incident_id"],
        },
    },
}

CREATE_INCIDENT_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "create_incident",
        "description": (
            "Create a new ServiceNow incident record. "
            "REQUIRES prior human approval — do not call without an approved ApprovalTask."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "short_description": {
                    "type": "string",
                    "description": "One-line incident summary (≤160 chars).",
                },
                "description": {
                    "type": "string",
                    "description": "Detailed incident description.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["1", "2", "3", "4", "5"],
                    "description": "1=Critical, 2=High, 3=Moderate, 4=Low, 5=Planning.",
                },
                "category": {"type": "string", "description": "Incident category."},
                "assignment_group": {
                    "type": "string",
                    "description": "Assignment group name in ServiceNow.",
                },
            },
            "required": ["short_description", "priority"],
        },
    },
}

UPDATE_INCIDENT_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "update_incident",
        "description": (
            "Update fields on an existing ServiceNow incident. "
            "REQUIRES prior human approval — do not call without an approved ApprovalTask."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sys_id": {
                    "type": "string",
                    "description": "ServiceNow sys_id of the incident to update.",
                },
                "fields": {
                    "type": "object",
                    "description": (
                        "Key-value pairs of incident fields to update "
                        "(e.g. {\"state\": \"resolved\", \"close_notes\": \"...\"})."
                    ),
                },
            },
            "required": ["sys_id", "fields"],
        },
    },
}

GET_SIGNALS_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "get_signals",
        "description": (
            "Query active monitoring alerts and signals from Application Insights / "
            "Azure Monitor. Returns recent alert events for a given resource or service."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "description": "Azure resource name or service identifier to query.",
                },
                "minutes": {
                    "type": "integer",
                    "description": "Look-back window in minutes. Default is 60.",
                    "default": 60,
                },
            },
            "required": ["resource"],
        },
    },
}

GET_METRICS_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "get_metrics",
        "description": (
            "Retrieve performance metrics (CPU, memory, latency, error rate) "
            "for a specified resource over a given time window."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "description": "Azure resource name or service identifier.",
                },
                "metric_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of metric names to retrieve (e.g. [\"cpu_percent\", \"latency_ms\"]).",
                },
                "minutes": {
                    "type": "integer",
                    "description": "Look-back window in minutes. Default is 60.",
                    "default": 60,
                },
            },
            "required": ["resource", "metric_names"],
        },
    },
}

SEND_TEAMS_NOTIFICATION_SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "send_teams_notification",
        "description": (
            "Send an Adaptive Card notification to the configured Microsoft Teams channel "
            "via Incoming Webhook. Use to alert the operations team about critical incidents "
            "or completed agent actions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Card title / headline.",
                },
                "body": {
                    "type": "string",
                    "description": "Card body text.",
                },
                "action_url": {
                    "type": "string",
                    "description": "Optional URL for the 'View' action button (e.g. ServiceNow incident link).",
                },
            },
            "required": ["title", "body"],
        },
    },
}

# Convenience mapping — all schemas indexed by tool name
ALL_SCHEMAS: dict[str, dict] = {
    "hybrid_search": HYBRID_SEARCH_SCHEMA,
    "get_article": GET_ARTICLE_SCHEMA,
    "lookup_incident": LOOKUP_INCIDENT_SCHEMA,
    "create_incident": CREATE_INCIDENT_SCHEMA,
    "update_incident": UPDATE_INCIDENT_SCHEMA,
    "get_signals": GET_SIGNALS_SCHEMA,
    "get_metrics": GET_METRICS_SCHEMA,
    "send_teams_notification": SEND_TEAMS_NOTIFICATION_SCHEMA,
}
