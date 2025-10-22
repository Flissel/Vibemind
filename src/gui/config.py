"""GUI configuration and utility functions.

This module contains global configuration variables and helper functions
for the GUI web interface.
"""

import logging
from logging.handlers import RotatingFileHandler
from typing import Any, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# Data directory configuration - will be set by main.py
DATA_DIR = None
LOGS_DIR = None
SESSIONS_DIR = None
TMP_DIR = None

# MCP Tool Agent Paths - Dynamically discovered from servers.json and filesystem
# NOTE: Only tools with Society of Mind agents need entries here
# Pure MCP servers (windows-core, time, etc.) are called directly via stdio
MCP_TOOL_AGENT_PATHS = {}


def _discover_mcp_agents():
    """Dynamically discover MCP agents from the servers directory.

    Scans src/MCP PLUGINS/servers/ for subdirectories containing agent.py files
    and automatically registers them in MCP_TOOL_AGENT_PATHS.

    This eliminates the need to manually update this file when adding new MCP servers.
    """
    import os
    from pathlib import Path

    # Find the project root
    # This file is at: src/gui/config.py
    # Project root is 2 levels up
    project_root = Path(__file__).resolve().parent.parent.parent
    servers_dir = project_root / "src" / "MCP PLUGINS" / "servers"

    if not servers_dir.exists():
        logger.warning(f"MCP servers directory not found: {servers_dir}")
        return

    # Scan for agent.py files in subdirectories
    for tool_dir in servers_dir.iterdir():
        if not tool_dir.is_dir():
            continue

        agent_file = tool_dir / "agent.py"
        if agent_file.exists():
            tool_name = tool_dir.name
            # Store relative path from project root
            relative_path = f"MCP PLUGINS/servers/{tool_name}/agent.py"
            MCP_TOOL_AGENT_PATHS[tool_name] = relative_path
            logger.debug(f"Discovered MCP agent: {tool_name} -> {relative_path}")

    logger.info(f"Discovered {len(MCP_TOOL_AGENT_PATHS)} MCP agents: {list(MCP_TOOL_AGENT_PATHS.keys())}")


# Auto-discover agents on module load
_discover_mcp_agents()


def get_mcp_server_metadata():
    """Load MCP server metadata from servers.json.

    Returns:
        Dict mapping tool names to their server configuration (description, active status, etc.)
    """
    from pathlib import Path
    import json

    # Find the project root (2 levels up from this file)
    project_root = Path(__file__).resolve().parent.parent.parent
    servers_json = project_root / "src" / "MCP PLUGINS" / "servers" / "servers.json"

    if not servers_json.exists():
        logger.warning(f"servers.json not found: {servers_json}")
        return {}

    try:
        with open(servers_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            servers = data.get("servers", [])

            metadata = {}
            for server in servers:
                name = server.get("name")
                if name:
                    metadata[name] = {
                        "active": server.get("active", False),
                        "description": server.get("description", ""),
                        "type": server.get("type", "stdio"),
                        "has_agent": name in MCP_TOOL_AGENT_PATHS,
                    }

            logger.info(f"Loaded metadata for {len(metadata)} MCP servers")
            return metadata

    except Exception as e:
        logger.error(f"Error loading servers.json: {e}")
        return {}


def set_data_directories(data_dir, logs_dir, sessions_dir, tmp_dir):
    """Set the data directory paths for use by GUI components."""
    global DATA_DIR, LOGS_DIR, SESSIONS_DIR, TMP_DIR
    DATA_DIR = data_dir
    LOGS_DIR = logs_dir
    SESSIONS_DIR = sessions_dir
    TMP_DIR = tmp_dir


def setup_session_logging(session_id: str, tool: str = None) -> logging.Logger:
    """Setup per-session logging under data/logs/sessions/

    Args:
        session_id: Unique session identifier
        tool: MCP tool name (e.g., 'time', 'github', 'playwright')

    Log file format: {tool}_{timestamp}_{session_id}.log
    Example: time_20251008_182659_thZBO68sMCuDI3X4QzxM0g.log
    """
    if not LOGS_DIR:
        # Fallback if not configured
        return logger

    session_logs_dir = LOGS_DIR / 'sessions'
    session_logs_dir.mkdir(parents=True, exist_ok=True)

    # Create session-specific logger
    session_logger = logging.getLogger(f'gui.session.{session_id}')

    # Avoid duplicate handlers
    if session_logger.handlers:
        return session_logger

    # Create log filename with tool name and timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if tool:
        log_filename = f'{tool}_{timestamp}_{session_id}.log'
    else:
        log_filename = f'{timestamp}_{session_id}.log'

    session_log_file = session_logs_dir / log_filename
    file_handler = RotatingFileHandler(
        session_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB per session log
        backupCount=5,
        encoding='utf-8'
    )
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    session_logger.addHandler(file_handler)
    session_logger.setLevel(logging.INFO)
    
    return session_logger


async def _gather_learning_insights(assistant) -> Dict[str, Any]:
    """Collect learning-related insights from the assistant and subsystems."""
    insights: Dict[str, Any] = {
        "metrics": {},
        "reinforcement": None,
        "file_discovery": None,
        "project_report": None,
        "patterns": [],
        "top_tools": [],
        "conversation_preview": [],
        "plugins": [],
    }
    try:
        metrics = getattr(assistant, "metrics", {}) or {}
        insights["metrics"] = metrics
        # Top tools summary
        tb = (metrics.get("tool_metrics") or {})
        tools = (tb.get("tools") or {})
        top = []
        for name, rec in tools.items():
            calls = rec.get("calls", 0) or 0
            succ = rec.get("successes", 0) or 0
            total_lat = rec.get("total_latency_ms", 0) or 0
            success_rate = (succ / calls * 100.0) if calls > 0 else 0.0
            avg_latency = (total_lat / calls) if calls > 0 else 0
            top.append({
                "name": name,
                "calls": calls,
                "success_rate": round(success_rate, 1),
                "avg_latency_ms": int(avg_latency),
            })
        top.sort(key=lambda x: x["calls"], reverse=True)
        insights["top_tools"] = top[:8]
    except Exception:
        pass

    # RL stats (if available)
    try:
        if hasattr(assistant, "reinforcement_learner") and assistant.reinforcement_learner:
            insights["reinforcement"] = assistant.reinforcement_learner.get_policy_stats()
    except Exception:
        pass

    # File discovery summary
    try:
        if hasattr(assistant, "file_discovery_learner") and assistant.file_discovery_learner:
            insights["file_discovery"] = assistant.file_discovery_learner.get_learned_summary()
    except Exception:
        pass

    # Project discovery report (text or dict)
    try:
        if hasattr(assistant, "project_discovery_learner") and assistant.project_discovery_learner:
            report = assistant.project_discovery_learner.get_project_report()
            insights["project_report"] = report
    except Exception:
        pass

    # Learned patterns from memory
    try:
        if hasattr(assistant, "memory_manager") and assistant.memory_manager:
            pats = await assistant.memory_manager.get_patterns(min_confidence=0.4)
            # Trim and normalize
            insights["patterns"] = [
                {
                    "id": p.get("id"),
                    "type": p.get("pattern_type"),
                    "data": p.get("pattern_data"),
                    "frequency": p.get("frequency"),
                    "confidence": p.get("confidence"),
                    "last_seen": p.get("last_seen"),
                }
                for p in (pats or [])
            ][:10]
    except Exception:
        pass

    # Recent conversation preview (last 5 exchanges)
    try:
        hist = getattr(assistant, "conversation_history", []) or []
        insights["conversation_preview"] = hist[-5:]
    except Exception:
        pass

    # Plugin info
    try:
        if hasattr(assistant, "plugin_manager") and assistant.plugin_manager:
            info = assistant.plugin_manager.get_plugin_info()
            # Normalize dict -> list
            if isinstance(info, dict):
                plugins = []
                for name, meta in info.items():
                    plugins.append({
                        "name": name,
                        "description": (meta or {}).get("description"),
                        "commands": sorted((meta or {}).get("commands", [])),
                    })
                insights["plugins"] = plugins
            elif isinstance(info, list):
                insights["plugins"] = info
    except Exception:
        pass

    return insights