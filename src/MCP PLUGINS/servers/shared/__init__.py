# -*- coding: utf-8 -*-
"""
Shared utilities for MCP server plugins.

This module provides common functionality used by all MCP server plugins:
- Event broadcasting (EventServer)
- UI server management (start_ui_server)
- Utility functions (load_prompt_from_module)
"""

# Use absolute imports since this directory is added to sys.path
# NO constants import to avoid name collision with plugin-level constants.py
from event_server import EventServer, UIHandler, start_ui_server
from utils import load_prompt_from_module

__all__ = [
    'EventServer',
    'UIHandler',
    'start_ui_server',
    'load_prompt_from_module',
]