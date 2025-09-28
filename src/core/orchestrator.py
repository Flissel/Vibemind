"""LLM Orchestrator stub that infers MCP job specs.

Phase 1: simple heuristic routing based on keywords. Future versions can
use the LLM to structure tasks and choose servers. Keeps compatibility with
SakanaAssistant and GUIInterface.
"""
from __future__ import annotations

from typing import Dict, Any

from .mcp_contracts import MCPJobSpec, make_job_id, make_correlation_id


class Orchestrator:
    """Produce MCPJobSpec from a user query.

    In Phase 1, we use a minimal heuristic:
      - if the text hints at browser/web/page/site -> target 'playwright'
      - else target 'playwright' by default (since it's the primary agent)
    """

    def infer_job(self, user_text: str, params: Dict[str, Any] | None = None) -> MCPJobSpec:
        params = params or {}
        text = (user_text or "").lower()
        target = "playwright"
        tokens = ["browser", "web", "page", "site", "click", "navigate", "url", "screenshot", "dom"]
        if any(t in text for t in tokens):
            target = "playwright"
        # Assign IDs
        job_id = make_job_id()
        corr = make_correlation_id()
        return MCPJobSpec(
            job_id=job_id,
            correlation_id=corr,
            server_target=target,
            task=user_text,
            params=params,
        )