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

        # GitHub-related tokens
        github_tokens = ["github", "repository", "repo", "issue", "pr", "pull request",
                        "commit", "branch", "fork", "clone"]
        if any(t in text for t in github_tokens):
            target = "github"
        # Docker-related tokens
        elif any(t in text for t in ["docker", "container", "compose", "docker-compose",
                                      "image", "dockerfile", "pod"]):
            target = "docker"
        # Desktop Commander tokens
        elif any(t in text for t in ["terminal", "command", "shell", "execute", "process",
                                      "file system", "directory"]):
            target = "desktop"
        # Context7 tokens
        elif any(t in text for t in ["documentation", "docs", "api reference", "context7",
                                      "code example"]):
            target = "context7"
        # Redis tokens
        elif any(t in text for t in ["redis", "cache", "key-value", "kvstore",
                                      "vector search", "embedding"]):
            target = "redis"
        # Playwright-related tokens
        elif any(t in text for t in ["browser", "web", "page", "site", "click",
                                      "navigate", "url", "screenshot", "dom"]):
            target = "playwright"
        else:
            # Default to playwright for now
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