# -*- coding: utf-8 -*-
"""
constants.py
Centralized constants and default configuration for the Playwright MCP agent.
This module ensures directories exist and default prompt/config files are initialized.

NOTE: Keep names consistent with other agents. Clear comments for easy debug.
"""
import os
import json

# UI server defaults (badge consistent across agents)
DEFAULT_UI_HOST: str = "127.0.0.1"
DEFAULT_UI_PORT: int = int(os.getenv("MCP_UI_PORT", "8787"))

# Path layout (relative to this server directory)
BASE_DIR: str = os.path.dirname(__file__)  # .../servers/playwright
SERVERS_DIR: str = os.path.dirname(BASE_DIR)  # .../servers
PLUGINS_DIR: str = os.path.dirname(SERVERS_DIR)  # .../MCP PLUGINS
MODELS_DIR: str = os.path.join(PLUGINS_DIR, "models")

# File paths
SYSTEM_PROMPT_PATH: str = os.path.join(BASE_DIR, "system_prompt.txt")
TASK_PROMPT_PATH: str = os.path.join(BASE_DIR, "task_prompt.txt")
SERVERS_CONFIG_PATH: str = os.path.join(SERVERS_DIR, "servers.json")
MODEL_CONFIG_PATH: str = os.path.join(MODELS_DIR, "model.json")

# Default prompts and configs
DEFAULT_SYSTEM_PROMPT: str = (
    "You are an AutoGen Assistant wired to an MCP server.\n"
    "Follow the TOOL USAGE contract strictly and call only the exposed tool names.\n"
    "Dynamic event hint: {MCP_EVENT}.\n"
    "Keep tool calls minimal; if blocked by bot checks or CAPTCHAs, switch sources.\n"
)

DEFAULT_TASK_PROMPT: str = (
    "Use the available tools to accomplish the goal and stream your progress.\n"
    "For Playwright, prefer safe sources (e.g., Wikipedia) and extract minimal text/HTML.\n"
)

DEFAULT_SERVERS_JSON = {
    "servers": [
        {
            "name": "playwright",
            "active": True,
            "type": "stdio",
            "command": "npx",
            "args": ["--yes", "@playwright/mcp@latest", "--headless"],
            "read_timeout_seconds": 120,
        }
    ]
}

DEFAULT_MODEL_JSON = {
    "model": os.getenv("OPENAI_MODEL")
    or os.getenv("MODEL")
    or ("llama3.1" if os.getenv("OPENAI_BASE_URL") else "gpt-4o"),
    "base_url": os.getenv("OPENAI_BASE_URL"),
    "api_key_env": "OPENAI_API_KEY",
}

# Ensure directory structure exists (idempotent)
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(SERVERS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# Initialize default prompt/config files if missing (idempotent)
if not os.path.exists(SYSTEM_PROMPT_PATH):
    with open(SYSTEM_PROMPT_PATH, "w", encoding="utf-8") as f:
        f.write(DEFAULT_SYSTEM_PROMPT)

if not os.path.exists(TASK_PROMPT_PATH):
    with open(TASK_PROMPT_PATH, "w", encoding="utf-8") as f:
        f.write(DEFAULT_TASK_PROMPT)

if not os.path.exists(SERVERS_CONFIG_PATH):
    with open(SERVERS_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_SERVERS_JSON, f, indent=2)

if not os.path.exists(MODEL_CONFIG_PATH):
    with open(MODEL_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_MODEL_JSON, f, indent=2)