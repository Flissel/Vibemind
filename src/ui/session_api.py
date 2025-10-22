from typing import Any, Dict


def _json(handler: Any, status: int, body: Dict[str, Any]) -> None:
    try:
        handler._json(status, body)
    except Exception:
        # Fallback in case _json is unavailable
        import json as _jsonlib
        try:
            data = _jsonlib.dumps(body).encode("utf-8")
            handler.send_response(status)
            handler.send_header("Content-Type", "application/json; charset=utf-8")
            handler.send_header("Content-Length", str(len(data)))
            handler.end_headers()
            handler.wfile.write(data)
        except Exception:
            pass


def handle_global_session_status(handler: Any) -> None:
    try:
        status = handler.server.get_mcp_session_status()  # type: ignore[attr-defined]
        _json(handler, 200, status)
    except Exception as e:
        _json(handler, 500, {"error": f"Status check failed: {e}"})


def handle_get_sessions(handler: Any) -> None:
    try:
        result = handler.server.get_all_mcp_sessions()  # type: ignore[attr-defined]
        sessions = []
        if isinstance(result, dict) and result.get("success") and "sessions" in result:
            sessions = result["sessions"]
        _json(handler, 200, {"sessions": sessions})
    except Exception as e:
        _json(handler, 200, {"sessions": [], "error": f"Failed to get sessions: {e}"})


def handle_session_status(handler: Any, session_id: str) -> None:
    try:
        status = handler.server.get_mcp_session_status_by_id(session_id)  # type: ignore[attr-defined]
        _json(handler, 200, status)
    except Exception as e:
        _json(handler, 500, {"error": f"Status check failed: {e}"})


def handle_create_session(handler: Any, data: Dict[str, Any]) -> None:
    try:
        name = (data.get("name") or "").strip()
        model = (data.get("model") or "gpt-4").strip()

        # Support both "tool" (singular) and "tools" (plural) for backward compatibility
        tool = data.get("tool")
        tools = data.get("tools")

        if tool and isinstance(tool, str):
            # Single tool provided as string -> convert to list
            tools = [tool.strip()]
        elif tools and isinstance(tools, list):
            # Tools list provided -> use as is
            tools = tools
        else:
            # No tool specified -> default to playwright
            tools = ["playwright"]

        task = ((data.get("task") or "").strip() or None)
        system = ((data.get("system") or "").strip() or None)
        target_tool = ((data.get("target_tool") or "").strip() or None)

        if not name:
            _json(handler, 400, {"success": False, "error": "'name' is required"})
            return

        result = handler.server.create_mcp_session(name=name, model=model, tools=tools, task=task, target_tool=target_tool, system=system)  # type: ignore[attr-defined]
        _json(handler, 200, result)
    except Exception as e:
        _json(handler, 500, {"success": False, "error": f"Failed to create session: {e}"})


def handle_start_session(handler: Any, session_id: str) -> None:
    try:
        result = handler.server.start_mcp_session_by_id(session_id)  # type: ignore[attr-defined]
        _json(handler, 200, result)
    except Exception as e:
        _json(handler, 500, {"success": False, "error": f"Failed to start session: {e}"})


def handle_stop_session(handler: Any, session_id: str) -> None:
    try:
        result = handler.server.stop_mcp_session_by_id(session_id)  # type: ignore[attr-defined]
        _json(handler, 200, result)
    except Exception as e:
        _json(handler, 500, {"success": False, "error": f"Failed to stop session: {e}"})


def handle_delete_session(handler: Any, session_id: str) -> None:
    try:
        result = handler.server.delete_mcp_session_by_id(session_id)  # type: ignore[attr-defined]
        _json(handler, 200, result)
    except Exception as e:
        _json(handler, 500, {"success": False, "error": f"Failed to delete session: {e}"})


def handle_spawn_session(handler: Any, session_id: str, ui_host: str | None, ui_port: int | None, keepalive: bool = True) -> None:
    try:
        res = handler.server.spawn_mcp_session_by_id(session_id, ui_host=ui_host, ui_port=ui_port, keepalive=bool(keepalive))  # type: ignore[attr-defined]
        _json(handler, 200, res)
    except Exception as e:
        _json(handler, 500, {"success": False, "error": f"Failed to spawn session: {e}"})


def handle_get_available_models(handler: Any) -> None:
    """Get available model configurations from OpenRouter config."""
    try:
        import os
        import json

        # Load global OpenRouter configuration from environment variables
        mode = os.getenv("OPENROUTER_MODE", "prod")

        # Parse JSON configs from environment
        dev_models_json = os.getenv("OPENROUTER_DEV_MODELS", "{}")
        model_selection_json = os.getenv("OPENROUTER_MODEL_SELECTION", "{}")
        tool_models_json = os.getenv("OPENROUTER_TOOL_MODELS", "{}")

        dev_models = json.loads(dev_models_json)
        model_selection = json.loads(model_selection_json)
        tool_models = json.loads(tool_models_json)

        # Build response
        response = {
            "mode": mode,
            "dev_models": {
                "default": dev_models.get("default", "openai/gpt-4o"),
                "alternative": dev_models.get("alternative", "anthropic/claude-sonnet-4.0"),
                "use_adaptive": dev_models.get("use_adaptive", False)
            },
            "model_selection": {
                "primary": model_selection.get("primary", "anthropic/claude-3.5-haiku"),
                "complex": model_selection.get("complex", "anthropic/claude-3.5-sonnet"),
                "reasoning": model_selection.get("reasoning", "openai/o1-mini"),
                "fallback": model_selection.get("fallback", "openai/gpt-4o-mini")
            },
            "tool_models": tool_models,
            "available_models": []
        }

        # Build list of available models based on mode
        if mode == "dev":
            response["available_models"] = [
                {"id": dev_models.get("default", "openai/gpt-4o"), "name": "Dev Default (GPT-4o)", "type": "dev"},
                {"id": dev_models.get("alternative", "anthropic/claude-sonnet-4.0"), "name": "Dev Alternative (Claude Sonnet 4.0)", "type": "dev"}
            ]
        else:
            response["available_models"] = [
                {"id": model_selection.get("primary", "anthropic/claude-3.5-haiku"), "name": "Primary (Claude 3.5 Haiku)", "type": "primary"},
                {"id": model_selection.get("complex", "anthropic/claude-3.5-sonnet"), "name": "Complex (Claude 3.5 Sonnet)", "type": "complex"},
                {"id": model_selection.get("reasoning", "openai/o1-mini"), "name": "Reasoning (O1 Mini)", "type": "reasoning"},
                {"id": model_selection.get("fallback", "openai/gpt-4o-mini"), "name": "Fallback (GPT-4o Mini)", "type": "fallback"}
            ]

        # Add tool-specific models
        for tool, model_id in tool_models.items():
            response["available_models"].append({
                "id": model_id,
                "name": f"{tool.capitalize()} Tool Model",
                "type": f"tool_{tool}"
            })

        _json(handler, 200, response)
    except Exception as e:
        _json(handler, 500, {"error": f"Failed to get available models: {e}"})


def handle_get_available_tools(handler: Any) -> None:
    """Get list of available MCP tools from servers.json with agent discovery."""
    try:
        import json
        import os
        from pathlib import Path

        # Use dynamic discovery from gui.config
        try:
            from src.gui.config import MCP_TOOL_AGENT_PATHS, get_mcp_server_metadata
            metadata = get_mcp_server_metadata()
        except Exception as e:
            # Fallback to manual loading if imports fail
            metadata = {}

        # Load servers.json
        base_dir = Path(__file__).resolve().parent.parent
        servers_path = base_dir / "MCP PLUGINS" / "servers" / "servers.json"

        if not servers_path.exists():
            _json(handler, 200, {"tools": []})
            return

        with open(servers_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract active tools with enhanced metadata
        tools = []
        for server in data.get("servers", []):
            if server.get("active", True):
                tool_name = server["name"]
                tool_meta = metadata.get(tool_name, {})

                tools.append({
                    "name": tool_name,
                    "description": server.get("description", ""),
                    "has_agent": tool_meta.get("has_agent", False),
                    "type": server.get("type", "stdio"),
                })

        # Sort alphabetically by name
        tools.sort(key=lambda x: x["name"])

        _json(handler, 200, {"tools": tools})
    except Exception as e:
        _json(handler, 500, {"error": f"Failed to get available tools: {e}"})