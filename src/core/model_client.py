# -*- coding: utf-8 -*-
"""
core/model_client.py
Shared ModelClient for use across multiple servers.

- Clear comments for easy debugging
- Consistent naming & code style with other agents
- Minimal dependencies; reads from a JSON config path if provided, else environment
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


class ModelClient:
    """Adapter for model client configuration used by agents.

    Attributes:
    - model: str -> model name (e.g., "gpt-4o" or "llama3.1")
    - base_url: Optional[str] -> custom base URL for the provider (for local/OpenAI-compatible backends)
    - api_key_env: Optional[str] -> environment variable name containing the API key (default: "OPENAI_API_KEY")
    - api_key: Optional[str] -> resolved API key value from env (not stored/committed anywhere)
    """

    def __init__(self, model: str, base_url: Optional[str] = None, api_key_env: Optional[str] = None):
        self.model = model
        self.base_url = base_url
        self.api_key_env = api_key_env
        # Resolve API key from environment at runtime only
        self.api_key = os.getenv(api_key_env) if api_key_env else None

    def as_dict(self) -> Dict[str, Any]:
        """Return a debug-friendly dict (does not expose key value)."""
        return {
            "model": self.model,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
            "has_api_key": bool(self.api_key),
        }


def _load_json(path: str) -> Dict[str, Any]:
    """Load JSON config from path; return empty dict if missing/invalid."""
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def init_model_client(config_path: Optional[str] = None, defaults_config: Optional[Dict[str, Any]] = None) -> ModelClient:
    """Create a ModelClient from a shared, reusable location.

    Priority of values:
    1. JSON at config_path (if provided and exists)
    2. defaults_config dict (if provided)
    3. Environment variables
       - OPENAI_MODEL or MODEL for model name
       - OPENAI_BASE_URL for base_url
       - OPENAI_API_KEY for api_key_env (name only)
    4. Hard-coded conservative defaults

    This keeps the initialization logic centralized so multiple servers can reuse it.
    """
    cfg: Dict[str, Any] = {}
    if config_path:
        cfg = _load_json(config_path)
    elif defaults_config:
        cfg = dict(defaults_config or {})

    # Resolve model name: prefer explicit config -> env -> default
    model = (
        cfg.get("model")
        or os.getenv("OPENAI_MODEL")
        or os.getenv("MODEL")
        or "gpt-4o"
    )

    # Resolve base URL (used by local/OpenAI-compatible backends)
    base_url = cfg.get("base_url") or os.getenv("OPENAI_BASE_URL")

    # Resolve API key env var name
    api_key_env = cfg.get("api_key_env") or "OPENAI_API_KEY"

    # Construct the client (API key is resolved lazily in the instance)
    return ModelClient(model=model, base_url=base_url, api_key_env=api_key_env)