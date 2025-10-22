"""POST route handlers for the GUI web interface.

This module handles all POST HTTP requests including:
- Chat/message processing
- Tool execution
- Session management
- Delegation
"""

import asyncio
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def do_POST(self):  # noqa: N802
    """Handle POST requests."""
    logger.info(f"[POST] Request received: path={self.path}")
    try:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        data = json.loads(raw.decode("utf-8")) if raw else {}
        logger.info(f"[POST] Data parsed successfully: {data}")
    except Exception as e:
        logger.error(f"[POST] JSON parse error: {e}")
        self._json(400, {"error": "Invalid JSON"})
        return

    # --- Chat endpoint ---
    if self.path == "/api/chat":
        try:
            text = (data.get("input") or "").strip()
            if not text:
                self._json(400, {"error": "'input' is required"})
                return
            # Lazy import to avoid circulars
            from ...core.orchestrator import Orchestrator
            from ...core.mcp_contracts import JobEnqueuedEvent
            # Ensure orchestrator exists
            orchestrator = getattr(self.server.assistant, 'orchestrator', None)
            if orchestrator is None:
                try:
                    orchestrator = Orchestrator()
                    setattr(self.server.assistant, 'orchestrator', orchestrator)
                except Exception:
                    orchestrator = Orchestrator()
            # Infer job spec
            params = data.get('params') if isinstance(data, dict) else None
            job = orchestrator.infer_job(text, params)
            # Verify TaskQueue
            tq = getattr(self.server, 'task_queue', None)
            if tq is None:
                self._json(500, {"error": "TaskQueue not initialized"})
                return
            job = tq.put(job)
            # Broadcast event
            try:
                enq = JobEnqueuedEvent(
                    correlation_id=job.correlation_id,
                    job_id=job.job_id,
                    server_target=job.server_target,
                    task=job.task,
                )
                self.server.broadcast_event('mcp.job.enqueued', enq.to_dict())
            except Exception:
                pass
            self._json(200, {"success": True, "job": job.to_dict(), "queued": getattr(tq, 'size', 0)})
        except Exception as e:
            self._json(500, {"error": f"Chat enqueue failed: {e}"})
        return

    # --- Message endpoint ---
    if self.path == "/api/message":
        text = (data.get("input") or "").strip()
        if not text:
            self._json(400, {"error": "'input' is required"})
            return
        try:
            coro = self.server.assistant.process_request(text)
            fut = asyncio.run_coroutine_threadsafe(coro, self.server.loop)
            result = fut.result(timeout=300)
            self._json(200, result)
        except Exception as e:
            self._json(500, {"error": f"Processing failed: {e}"})
        return

    # --- Delegation endpoint ---
    if self.path == "/api/delegate":
        goal = (data.get("goal") or "").strip()
        if not goal:
            self._json(400, {"error": "'goal' is required"})
            return
        try:
            from ...delegation.delegation_entry import run_delegation
            coro = run_delegation(goal)
            fut = asyncio.run_coroutine_threadsafe(coro, self.server.loop)
            result = fut.result(timeout=600)
            self._json(200, result)
        except Exception as e:
            self._json(500, {"error": f"Delegation failed: {e}"})
        return

    # --- Tool endpoint ---
    if self.path == "/api/tool":
        command = (data.get("command") or "").strip()
        if not command:
            self._json(400, {"error": "'command' is required"})
            return
        try:
            context: Dict[str, Any] = {"source": "gui_tool"}
            coro = self.server.assistant.plugin_manager.handle_command(command, context)
            fut = asyncio.run_coroutine_threadsafe(coro, self.server.loop)
            resp = fut.result(timeout=60)
            if not resp:
                self._json(404, {"success": False, "error": "Unknown or unsupported command"})
                return
            # Verification for util.print
            verification = None
            try:
                parts = command.split()
                if parts and parts[0].lower() == 'util.print':
                    expected = ' '.join(parts[1:])
                    actual = resp.get('content') if isinstance(resp, dict) else None
                    verification = {
                        'expected': expected,
                        'actual': actual,
                        'matches': (isinstance(actual, str) and actual == expected)
                    }
                    if hasattr(self.server.assistant, 'memory_manager') and self.server.assistant.memory_manager:
                        vcoro = self.server.assistant.memory_manager.detect_pattern('tool_usage', {
                            'command': 'util.print',
                            'verified': bool(verification['matches']),
                            'expected_len': len(expected),
                            'actual_len': len(actual or ''),
                            'timestamp': __import__('datetime').datetime.now().isoformat(),
                            'source': 'gui',
                        })
                        asyncio.run_coroutine_threadsafe(vcoro, self.server.loop)
            except Exception:
                pass
            self._json(200, {"success": True, "response": resp, "verification": verification})
        except Exception as e:
            self._json(500, {"success": False, "error": f"Tool execution failed: {e}"})
        return

    # --- GUI event broadcast ---
    if self.path == "/api/gui_event":
        event_name = (data.get("event") or "").strip()
        if not event_name:
            self._json(400, {"error": "'event' is required"})
            return
        event_data = data.get("data") if isinstance(data, dict) else None
        try:
            self.server.broadcast_event(event_name, event_data)
            self._json(200, {"success": True, "event": event_name})
        except Exception as e:
            self._json(500, {"success": False, "error": f"Failed to broadcast event: {e}"})
        return

    # --- Playwright session control ---
    if self.path == "/api/playwright/session/attach":
        try:
            host = (data.get("host") or "").strip()
            port = data.get("port")
            session_id = (data.get("session_id") or "").strip() or getattr(self.server, '_playwright_session_id', None)
            if not host:
                self._json(400, {"success": False, "error": "'host' is required"})
                return
            try:
                port = int(port)
            except Exception:
                self._json(400, {"success": False, "error": "'port' must be an integer"})
                return
            res = self.server.set_playwright_session_upstream(str(session_id or ''), host, port)
            self._json(200, res)
        except Exception as e:
            self._json(500, {"success": False, "error": f"Attach failed: {e}"})
        return

    if self.path == "/api/playwright/session/spawn":
        try:
            session_id = (data.get("session_id") or "").strip() or None
            ui_host = (data.get("ui_host") or "").strip() or None
            ui_port = data.get("ui_port")
            keepalive = data.get("keepalive")
            if ui_port is not None:
                try:
                    ui_port = int(ui_port)
                except Exception:
                    self._json(400, {"success": False, "error": "'ui_port' must be an integer"})
                    return
            if keepalive is None:
                keepalive = True
            else:
                keepalive = bool(keepalive)
            res = self.server.spawn_playwright_session_agent(session_id=session_id, ui_host=ui_host, ui_port=ui_port, keepalive=keepalive)
            self._json(200, res)
        except Exception as e:
            self._json(500, {"success": False, "error": f"Spawn failed: {e}"})
        return

    if self.path == "/api/playwright/session/stop":
        try:
            res = self.server.stop_playwright_session_agent()
            self._json(200, res)
        except Exception as e:
            self._json(500, {"success": False, "error": f"Stop failed: {e}"})
        return

    # --- Multi-session management ---
    if self.path == "/api/sessions":
        try:
            # ========== DIAGNOSTIC LOGGING: Session Creation ==========
            logger.error("=" * 80)
            logger.error("[SESSION CREATE] POST /api/sessions - DIAGNOSTIC MODE")
            logger.error("=" * 80)
            
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

            task = (data.get("task") or "").strip()  # Get task from request
            target_tool = (data.get("target_tool") or "").strip()  # Get target_tool from request
            
            logger.error(f"[SESSION CREATE] Request data:")
            logger.error(f"  name: {name}")
            logger.error(f"  model: {model}")
            logger.error(f"  tools: {tools}")
            logger.error(f"  task: {task}")
            logger.error(f"  target_tool: {target_tool}")
            
            if not name:
                logger.error(f"[SESSION CREATE] ✗ ERROR: name is required")
                self._json(400, {"success": False, "error": "'name' is required"})
                return
            
            # Check MCPSessionManager state
            logger.error(f"[SESSION CREATE] Server state:")
            logger.error(f"  server has _mcp_manager: {hasattr(self.server, '_mcp_manager')}")
            logger.error(f"  server has create_playwright_session: {hasattr(self.server, 'create_playwright_session')}")
            
            if hasattr(self.server, '_mcp_manager'):
                logger.error(f"  _mcp_manager._sessions count BEFORE: {len(self.server._mcp_manager._sessions)}")
                logger.error(f"  _mcp_manager._sessions keys BEFORE: {list(self.server._mcp_manager._sessions.keys())}")
            
            # Call session creation
            logger.error(f"[SESSION CREATE] Calling create_playwright_session...")
            result = self.server.create_playwright_session(
                name=name, 
                model=model, 
                tools=tools,
                task=task if task else None,
                target_tool=target_tool if target_tool else None
            )
            
            logger.error(f"[SESSION CREATE] Result:")
            logger.error(f"  success: {result.get('success')}")
            logger.error(f"  session_id: {result.get('session', {}).get('session_id')}")
            
            if hasattr(self.server, '_mcp_manager'):
                logger.error(f"  _mcp_manager._sessions count AFTER: {len(self.server._mcp_manager._sessions)}")
                logger.error(f"  _mcp_manager._sessions keys AFTER: {list(self.server._mcp_manager._sessions.keys())}")
                
                # Verify session is in storage
                if result.get('success'):
                    session_id = result.get('session', {}).get('session_id')
                    if session_id:
                        session_exists = session_id in self.server._mcp_manager._sessions
                        logger.error(f"  ✓ VERIFICATION: Session {session_id} in storage: {session_exists}")
                        if session_exists:
                            stored_session = self.server._mcp_manager._sessions[session_id]
                            logger.error(f"  Stored session data: {stored_session}")
            
            logger.error("=" * 80)
            
            self._json(200, result)
        except Exception as e:
            logger.error(f"[SESSION CREATE] ✗ EXCEPTION: {type(e).__name__}: {e}", exc_info=True)
            self._json(500, {"success": False, "error": f"Failed to create session: {e}"})
        return

    # Session-specific operations
    if self.path.startswith("/api/sessions/") and self.path.endswith("/start"):
        try:
            session_id = self.path.split("/")[3]
            
            # ========== DIAGNOSTIC LOGGING: Session Start ==========
            logger.error("=" * 80)
            logger.error(f"[SESSION START] POST /api/sessions/{session_id}/start")
            logger.error("=" * 80)
            
            # Get session to determine tool type
            if hasattr(self.server, '_mcp_manager'):
                session = self.server._mcp_manager.get_session(session_id)
                if session:
                    logger.error(f"[SESSION START] Session found:")
                    logger.error(f"  tool: {session.get('tool')}")
                    logger.error(f"  name: {session.get('name')}")
                    logger.error(f"  task: {session.get('task')}")
                else:
                    logger.error(f"[SESSION START] ✗ Session {session_id} not found!")
            
            # Use new method that determines tool from session
            logger.error(f"[SESSION START] Calling start_session_by_id()...")
            result = self.server.start_session_by_id(session_id)
            
            logger.error(f"[SESSION START] Result: {result.get('success')}, tool: {result.get('tool')}")
            logger.error("=" * 80)
            
            self._json(200, result)
        except Exception as e:
            logger.error(f"[SESSION START] ✗ EXCEPTION: {type(e).__name__}: {e}", exc_info=True)
            self._json(500, {"success": False, "error": f"Failed to start session: {e}"})
        return

    if self.path.startswith("/api/sessions/") and self.path.endswith("/stop"):
        try:
            session_id = self.path.split("/")[3]
            result = self.server.stop_playwright_session_by_id(session_id)
            self._json(200, result)
        except Exception as e:
            self._json(500, {"success": False, "error": f"Failed to stop session: {e}"})
        return

    if self.path.startswith("/api/sessions/") and self.path.endswith("/delete"):
        try:
            session_id = self.path.split("/")[3]
            logger.error(f"[DEBUG DELETE] Attempting to delete session: {session_id}")
            logger.error(f"[DEBUG DELETE] Server has _mcp_manager? {hasattr(self.server, '_mcp_manager')}")
            logger.error(f"[DEBUG DELETE] Server has delete_playwright_session_by_id? {hasattr(self.server, 'delete_playwright_session_by_id')}")
            
            result = self.server.delete_playwright_session_by_id(session_id)
            logger.error(f"[DEBUG DELETE] Delete result: {result}")
            self._json(200, result)
        except Exception as e:
            logger.error(f"[DEBUG DELETE] Exception during delete: {e}", exc_info=True)
            self._json(500, {"success": False, "error": f"Failed to delete session: {e}"})
        return

    # Frontend compatibility
    if self.path.startswith("/api/playwright/session/") and "/spawn" in self.path:
        try:
            session_id = self.path.split("/")[4]
            ui_host = (data.get("ui_host") or "").strip() or None
            ui_port = data.get("ui_port")
            keepalive = data.get("keepalive", True)
            
            if ui_port is not None:
                try:
                    ui_port = int(ui_port)
                except Exception:
                    self._json(400, {"success": False, "error": "'ui_port' must be an integer"})
                    return
            
            res = self.server.spawn_playwright_session_by_id(session_id, ui_host=ui_host, ui_port=ui_port, keepalive=bool(keepalive))
            self._json(200, res)
        except Exception as e:
            self._json(500, {"success": False, "error": f"Failed to spawn session: {e}"})
        return

    if self.path.startswith("/api/playwright/session/") and "/stop" in self.path:
        try:
            session_id = self.path.split("/")[4]
            res = self.server.stop_playwright_session_by_id(session_id)
            self._json(200, res)
        except Exception as e:
            self._json(500, {"success": False, "error": f"Failed to stop session: {e}"})
        return

    # --- User clarification endpoint ---
    # POST /api/mcp/sessions/{session_id}/clarification
    if self.path.startswith("/api/mcp/sessions/") and self.path.endswith("/clarification"):
        logger.error("=" * 80)
        logger.error(f"[CLARIFICATION] ✅ Received clarification submission")
        logger.error(f"[CLARIFICATION] Path: {self.path}")
        logger.error(f"[CLARIFICATION] Raw data: {data}")
        logger.error(f"[CLARIFICATION] Data type: {type(data)}")
        try:
            session_id = self.path.split("/")[4]
            answer = data.get("answer", "")
            correlation_id = data.get("correlation_id", session_id)
            tool = data.get("tool", "unknown")

            logger.error(f"[CLARIFICATION] Extracted values:")
            logger.error(f"  session_id: {session_id}")
            logger.error(f"  answer: '{answer}' (len={len(answer)}, type={type(answer)})")
            logger.error(f"  correlation_id: {correlation_id}")
            logger.error(f"  tool: {tool}")

            # Get session to find event port
            session = self.server._mcp_manager.get_session(session_id)
            if not session:
                logger.error(f"[CLARIFICATION] ✗ Session {session_id} not found!")
                self._json(404, {"error": f"Session {session_id} not found"})
                return

            logger.error(f"[CLARIFICATION] Session found: tool={session.get('tool')}, name={session.get('name')}")

            session_host = session.get("host", "127.0.0.1")
            session_port = session.get("port")

            if not session_port:
                logger.error(f"[CLARIFICATION] ✗ Session has no event port!")
                self._json(404, {"error": f"Session has no event port"})
                return

            logger.error(f"[CLARIFICATION] Session event: {session_host}:{session_port}")

            # Write answer to file for agent polling (file-based communication)
            import os
            from pathlib import Path

            try:
                # Determine response file path (same as agent polling location)
                base_dir = Path(__file__).resolve().parents[3]  # Navigate up to project root
                tmp_dir = base_dir / "data" / "tmp"
                tmp_dir.mkdir(parents=True, exist_ok=True)

                # Use correlation_id for file name (agent polls this file)
                response_file = tmp_dir / f"clarification_{correlation_id}.txt"

                logger.error(f"[CLARIFICATION] Writing to file: {response_file}")
                logger.error(f"[CLARIFICATION] Answer content: '{answer}'")

                # Write user's answer to file
                response_file.write_text(answer, encoding='utf-8')

                # Verify file was written
                if response_file.exists():
                    written_content = response_file.read_text(encoding='utf-8')
                    logger.error(f"[CLARIFICATION] ✅ File written successfully!")
                    logger.error(f"[CLARIFICATION] File size: {response_file.stat().st_size} bytes")
                    logger.error(f"[CLARIFICATION] Verification read: '{written_content}'")
                else:
                    logger.error(f"[CLARIFICATION] ✗ File doesn't exist after write!")

                # Agent will poll and read this file, then broadcast completion
                response_payload = {"success": True, "message": "Answer delivered to file", "file": str(response_file)}
                logger.error(f"[CLARIFICATION] Sending response: {response_payload}")
                self._json(200, response_payload)
                logger.error(f"[CLARIFICATION] ✅ Response sent successfully")
            except Exception as e:
                logger.error(f"[CLARIFICATION] ✗ Failed to write answer file: {e}", exc_info=True)
                self._json(500, {"success": False, "error": f"File write failed: {e}"})

        except Exception as e:
            logger.error(f"[CLARIFICATION] ✗ Endpoint error: {e}", exc_info=True)
            self._json(500, {"success": False, "error": str(e)})

        logger.error("=" * 80)
        return

    # --- User clarification skip endpoint ---
    # POST /api/mcp/sessions/{session_id}/clarification/skip
    if self.path.startswith("/api/mcp/sessions/") and self.path.endswith("/clarification/skip"):
        logger.error("=" * 80)
        logger.error(f"[CLARIFICATION SKIP] ⏭️ Received skip request")
        logger.error(f"[CLARIFICATION SKIP] Path: {self.path}")
        logger.error(f"[CLARIFICATION SKIP] Data: {data}")
        try:
            session_id = self.path.split("/")[4]
            correlation_id = data.get("correlation_id", session_id)
            tool = data.get("tool", "unknown")

            logger.error(f"[CLARIFICATION SKIP] Extracted values:")
            logger.error(f"  session_id: {session_id}")
            logger.error(f"  correlation_id: {correlation_id}")
            logger.error(f"  tool: {tool}")

            # Write skip file for agent polling (file-based communication)
            from pathlib import Path

            try:
                # Determine skip file path
                base_dir = Path(__file__).resolve().parents[3]  # Navigate up to project root
                tmp_dir = base_dir / "data" / "tmp"
                tmp_dir.mkdir(parents=True, exist_ok=True)

                # Write skip signal file
                skip_file = tmp_dir / f"skip_{correlation_id}.txt"

                logger.error(f"[CLARIFICATION SKIP] Writing to file: {skip_file}")
                skip_file.write_text("skip", encoding='utf-8')

                # Verify file was written
                if skip_file.exists():
                    logger.error(f"[CLARIFICATION SKIP] ✅ Skip file written successfully!")
                    logger.error(f"[CLARIFICATION SKIP] File size: {skip_file.stat().st_size} bytes")
                else:
                    logger.error(f"[CLARIFICATION SKIP] ✗ File doesn't exist after write!")

                # Agent will poll and read this file, then broadcast completion
                response_payload = {"success": True, "message": "Skip signal sent", "file": str(skip_file)}
                logger.error(f"[CLARIFICATION SKIP] Sending response: {response_payload}")
                self._json(200, response_payload)
                logger.error(f"[CLARIFICATION SKIP] ✅ Response sent successfully")
            except Exception as e:
                logger.error(f"[CLARIFICATION SKIP] ✗ Failed to write skip file: {e}", exc_info=True)
                self._json(500, {"success": False, "error": f"File write failed: {e}"})

        except Exception as e:
            logger.error(f"[CLARIFICATION SKIP] ✗ Endpoint error: {e}", exc_info=True)
            self._json(500, {"success": False, "error": str(e)})

        logger.error("=" * 80)
        return

    self._json(404, {"error": "Not found"})