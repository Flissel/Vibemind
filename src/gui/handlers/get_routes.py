"""GET route handlers for the GUI web interface.

This module handles all GET HTTP requests including:
- React SPA serving
- SSE events
- MCP tool proxy endpoints
- API endpoints
"""

import asyncio
import json
import logging
import os
import pathlib
import queue
import time
import urllib.request
import urllib.error
from pathlib import Path
from mimetypes import guess_type
from urllib.parse import urlparse, parse_qs
import http.client

from ..config import _gather_learning_insights

logger = logging.getLogger(__name__)


def do_GET(self):  # noqa: N802
    """Handle GET requests."""
    print(f"[DEBUG] *** do_GET called for path: {self.path} ***", flush=True)
    logging.error(f"[DEBUG] *** do_GET called for path: {self.path} ***")
    
    # Get server configuration
    try:
        srv = getattr(self, 'server', None)
        react_enabled = bool(getattr(srv, '_react_ui_enabled', False))
        dist_dir = getattr(srv, '_react_ui_dist_dir', None)
    except Exception:
        react_enabled = False
        dist_dir = None
    
    # Parse path without query string
    clean_path = (self.path.split("?", 1)[0] if self.path else "/")
    
    # --- React SPA serving when enabled ---
    if react_enabled and dist_dir:
        try:
            dist_root = pathlib.Path(dist_dir).resolve()
            req_path = clean_path or '/'
            
            def _is_api_path(p: str) -> bool:
                return p.startswith('/api/') or p.startswith('/events') or p.startswith('/mcp/')
            
            if req_path == '/' or req_path.startswith('/index.html'):
                index_fp = dist_root / 'index.html'
                if index_fp.is_file():
                    body = index_fp.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    try:
                        self.wfile.write(body)
                    except Exception:
                        pass
                    return
            elif not _is_api_path(req_path):
                # Try to serve static asset
                rel = req_path.lstrip('/')
                try:
                    fs_path = (dist_root / rel).resolve()
                    if str(fs_path).startswith(str(dist_root)) and fs_path.is_file():
                        body = fs_path.read_bytes()
                        ctype = guess_type(str(fs_path))[0] or "application/octet-stream"
                        self.send_response(200)
                        self.send_header("Content-Type", ctype)
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        try:
                            self.wfile.write(body)
                        except Exception:
                            pass
                        return
                except Exception:
                    pass
                # SPA fallback
                index_fp = dist_root / 'index.html'
                if index_fp.is_file():
                    body = index_fp.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    try:
                        self.wfile.write(body)
                    except Exception:
                        pass
                    return
        except Exception:
            pass
    
    # Final SPA fallback
    if react_enabled and dist_dir:
        dist_root = pathlib.Path(dist_dir).resolve()
        req_path = clean_path or '/'
        def _is_api_path(p: str) -> bool:
            return p.startswith('/api/') or p.startswith('/events') or p.startswith('/mcp/')
        if not _is_api_path(req_path):
            index_fp = dist_root / 'index.html'
            if index_fp.is_file():
                body = index_fp.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except Exception:
                    pass
                return
    
    # Legacy inline UI
    if not react_enabled and clean_path == "/":
        body = (self.INDEX_HTML or "<html><body><h1>GUI</h1><p>Initialization fallback.</p></body></html>").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass
        return

    # --- Health check ---
    if self.path == "/health":
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b"ok")
        except Exception:
            pass
        return

    # --- SSE events ---
    if self.path == "/events":
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            q = queue.Queue(maxsize=100)
            self.server.sse_queues.append(q)
            try:
                self.wfile.write(b":connected\n\n"); self.wfile.flush()
            except Exception:
                pass
            try:
                while True:
                    try:
                        item = q.get(timeout=30.0)
                    except Exception:
                        try:
                            self.wfile.write(b":heartbeat\n\n"); self.wfile.flush()
                        except (ConnectionAbortedError, BrokenPipeError):
                            break
                        except Exception:
                            break
                        continue
                    try:
                        if isinstance(item, str):
                            if item == 'reload':
                                self.wfile.write(b"event: reload\n")
                                self.wfile.write(b"data: {}\n\n")
                            else:
                                self.wfile.write(b"data: " + json.dumps({"message": item}).encode("utf-8") + b"\n\n")
                            self.wfile.flush()
                        elif isinstance(item, dict):
                            ev = item.get("__sse_event__") or "message"
                            data = item.get("data") or {}
                            self.wfile.write(b"event: " + str(ev).encode("utf-8") + b"\n")
                            self.wfile.write(b"data: " + json.dumps(data).encode("utf-8") + b"\n\n")
                            self.wfile.flush()
                        else:
                            self.wfile.write(b":unknown\n\n"); self.wfile.flush()
                    except (ConnectionAbortedError, BrokenPipeError):
                        break
                    except Exception:
                        break
            finally:
                try:
                    self.server.sse_queues.remove(q)
                except Exception:
                    pass
        except Exception:
            try:
                self._json(500, {"error": "SSE stream failed"})
            except Exception:
                pass
        return

    # --- JSON polling fallback ---
    if self.path.startswith("/events.json"):
        try:
            since = 0
            try:
                qs = parse_qs(urlparse(self.path).query)
                since = int((qs.get("since") or ["0"])[0])
            except Exception:
                since = 0
            items, latest = self.server._get_events_since(since)
            self._json(200, {"items": items, "since": latest})
        except Exception as e:
            self._json(500, {"error": f"Failed to get events: {e}"})
        return

    # --- API endpoints ---
    if self.path == "/api/plugins":
        try:
            info = self.server.assistant.plugin_manager.get_plugin_info()
            plugins = []
            if isinstance(info, dict):
                for name, meta in info.items():
                    plugins.append({
                        "name": name,
                        "description": meta.get("description"),
                        "commands": sorted(meta.get("commands", [])),
                    })
            elif isinstance(info, list):
                plugins = info
            self._json(200, {"plugins": plugins})
        except Exception as e:
            self._json(500, {"error": f"Failed to get plugins: {e}"})
        return

    if self.path == "/api/learning":
        try:
            coro = _gather_learning_insights(self.server.assistant)
            fut = asyncio.run_coroutine_threadsafe(coro, self.server.loop)
            result = fut.result(timeout=30)
            self._json(200, result)
        except Exception as e:
            self._json(500, {"error": f"Failed to gather insights: {e}"})
        return

    if self.path == "/api/models/available":
        logger.error("[DEBUG] /api/models/available route HIT!")
        from src.ui.session_api import handle_get_available_models
        try:
            handle_get_available_models(self)
        except Exception as e:
            logger.error(f"[DEBUG] Error in handle_get_available_models: {e}", exc_info=True)
            self._json(500, {"error": str(e)})
        return

    if self.path == "/api/mcp/tools":
        from src.ui.session_api import handle_get_available_tools
        try:
            handle_get_available_tools(self)
        except Exception as e:
            self._json(500, {"error": str(e)})
        return

    if self.path == "/api/playwright/session/start":
        try:
            res = self.server.start_playwright_session_agent()
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

    if self.path == "/api/playwright/session/status":
        try:
            status = self.server.get_playwright_session_status()
            self._json(200, status)
        except Exception as e:
            self._json(500, {"error": f"Status check failed: {e}"})
        return

    # --- Session management (supports multiple sessions) ---
    if self.path == "/api/sessions":
        try:
            # ========== DIAGNOSTIC LOGGING: Session Retrieval ==========
            logger.error("=" * 80)
            logger.error("[SESSION GET] GET /api/sessions - DIAGNOSTIC MODE")
            logger.error("=" * 80)
            
            logger.error(f"[SESSION GET] Server state:")
            logger.error(f"  server has _mcp_manager: {hasattr(self.server, '_mcp_manager')}")
            logger.error(f"  server has get_all_mcp_sessions: {hasattr(self.server, 'get_all_mcp_sessions')}")
            
            if hasattr(self.server, '_mcp_manager'):
                logger.error(f"  _mcp_manager type: {type(self.server._mcp_manager)}")
                logger.error(f"  _mcp_manager._sessions type: {type(self.server._mcp_manager._sessions)}")
                logger.error(f"  _mcp_manager._sessions count: {len(self.server._mcp_manager._sessions)}")
                logger.error(f"  _mcp_manager._sessions keys: {list(self.server._mcp_manager._sessions.keys())}")
                
                # Show detailed session data
                for sid, sess in self.server._mcp_manager._sessions.items():
                    logger.error(f"  Session {sid}:")
                    logger.error(f"    tool: {sess.get('tool')}")
                    logger.error(f"    name: {sess.get('name')}")
                    logger.error(f"    status: {sess.get('status')}")
            
            logger.error(f"[SESSION GET] Calling get_all_mcp_sessions() WITHOUT filter...")
            result = self.server.get_all_mcp_sessions()  # No tool_filter = returns ALL
            
            logger.error(f"[SESSION GET] Result:")
            logger.error(f"  success: {result.get('success')}")
            logger.error(f"  sessions count: {len(result.get('sessions', []))}")
            logger.error(f"  session tools: {[s.get('tool') for s in result.get('sessions', [])]}")
            
            logger.error("=" * 80)
            
            self._json(200, result)
        except Exception as e:
            logger.error(f"[SESSION GET] ✗ EXCEPTION: {type(e).__name__}: {e}", exc_info=True)
            self._json(500, {"success": False, "error": str(e)})
        return

    # Session-specific status endpoint
    if self.path.startswith("/api/sessions/") and self.path.endswith("/status"):
        try:
            session_id = self.path.split("/")[3]
            status = self.server.get_playwright_session_status_by_id(session_id)
            self._json(200, status)
        except Exception as e:
            self._json(500, {"error": f"Status check failed: {e}"})
        return

    # Session logs endpoint
    if self.path.startswith("/api/sessions/") and self.path.endswith("/logs"):
        try:
            session_id = self.path.split("/")[3]

            # Get log file path from data/logs/sessions/
            from ..config import DATA_DIR
            import glob
            log_dir = Path(DATA_DIR) / "logs" / "sessions"

            # Find log file with new naming format: {tool}_{timestamp}_{session_id}.log
            # or fallback to old format: {session_id}.log
            log_file = None

            # Try new format first (search for files ending with session_id.log)
            pattern = str(log_dir / f"*_{session_id}.log")
            matching_files = glob.glob(pattern)
            if matching_files:
                # Get most recent file if multiple matches
                log_file = Path(max(matching_files, key=os.path.getmtime))
            else:
                # Fallback to old format
                old_format = log_dir / f"{session_id}.log"
                if old_format.exists():
                    log_file = old_format

            if not log_file or not log_file.exists():
                self._json(404, {"error": f"Log file not found for session {session_id}"})
                return

            # Read last 200 lines (or full file if smaller)
            try:
                lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
                # Return last 200 lines
                last_lines = lines[-200:] if len(lines) > 200 else lines
                self._json(200, {
                    "session_id": session_id,
                    "log_file": log_file.name,
                    "lines": last_lines,
                    "total_lines": len(lines),
                    "showing_lines": len(last_lines)
                })
            except Exception as e:
                self._json(500, {"error": f"Failed to read log file: {e}"})
        except Exception as e:
            self._json(500, {"error": f"Failed to get logs: {e}"})
        return

    # Frontend compatibility
    if self.path.startswith("/api/playwright/session/") and self.path.endswith("/status"):
        try:
            session_id = self.path.split("/")[4]
            status = self.server.get_playwright_session_status_by_id(session_id)
            self._json(200, status)
        except Exception as e:
            self._json(500, {"error": f"Status check failed: {e}"})
        return

    # --- NEW: Generic MCP tool session events endpoint ---
    # Frontend calls /api/mcp/{tool}/sessions/{session_id}/events
    if self.path.startswith("/api/mcp/") and "/sessions/" in self.path and self.path.endswith("/events"):
        try:
            # Parse: /api/mcp/{tool}/sessions/{session_id}/events
            parts = self.path.split("/")
            if len(parts) >= 6:
                tool = parts[3]  # Extract tool name
                session_id = parts[5]  # Extract session_id
                
                # Get session to verify it exists and get the actual tool
                session = self.server._mcp_manager.get_session(session_id)
                if not session:
                    self._json(404, {"error": f"Session {session_id} not found"})
                    return
                
                # Use the actual tool from session, not from URL (URL might have "unknown")
                actual_tool = session.get("tool", "playwright")
                
                # Forward to the tool-specific event endpoint
                # For now, proxy to Playwright-style /mcp/playwright/session/{id}/events.json with polling
                if actual_tool == "playwright":
                    # Redirect to existing Playwright proxy
                    redirect_path = f"/mcp/playwright/session/{session_id}/events.json"
                    # Parse query string for 'since' parameter
                    try:
                        qs = parse_qs(urlparse(self.path).query)
                        since = qs.get("since", ["0"])[0]
                        redirect_path += f"?since={since}"
                    except Exception:
                        pass
                    
                    # Proxy the request
                    try:
                        session_host = session.get("host", "127.0.0.1")
                        session_port = session.get("port", 8787)
                        
                        if not session_host or not session_port:
                            self._json(404, {"error": f"Session {session_id} not connected to upstream"})
                            return
                        
                        import urllib.request, urllib.error
                        url = f"http://{session_host}:{session_port}/events.json"
                        # Add query string
                        try:
                            qs = parse_qs(urlparse(self.path).query)
                            since = qs.get("since", ["0"])[0]
                            url += f"?since={since}"
                        except Exception:
                            pass
                        
                        req = urllib.request.Request(url, headers={"Accept": "application/json"})
                        with self._fetch_with_backoff(req, timeout=2.5, attempts=4, base_delay=0.25) as r:
                            body = r.read()
                            ctype = r.headers.get("Content-Type", "application/json; charset=utf-8")
                            status_code = getattr(r, "status", 200)
                            self.send_response(status_code)
                            self.send_header("Content-Type", ctype)
                            self.send_header("Cache-Control", "no-store")
                            self.send_header("Content-Length", str(len(body)))
                            self.end_headers()
                            try:
                                self.wfile.write(body)
                            except (ConnectionAbortedError, BrokenPipeError):
                                return
                            except Exception:
                                return
                            return
                    except urllib.error.HTTPError as e:
                        try:
                            err_body = e.read() if hasattr(e, "read") else b""
                        except Exception:
                            err_body = b""
                        ctype = e.headers.get("Content-Type", "application/json; charset=utf-8") if hasattr(e, "headers") else "application/json; charset=utf-8"
                        try:
                            self.send_response(getattr(e, "code", 500))
                            self.send_header("Content-Type", ctype)
                            self.send_header("Cache-Control", "no-store")
                            self.send_header("Content-Length", str(len(err_body)))
                            self.end_headers()
                            try:
                                if err_body:
                                    self.wfile.write(err_body)
                            except (ConnectionAbortedError, BrokenPipeError):
                                return
                            except Exception:
                                return
                        except (ConnectionAbortedError, BrokenPipeError):
                            return
                        except Exception:
                            return
                        return
                    except Exception as e:
                        try:
                            self._json(502, {"error": f"Upstream failed: {e}"})
                        except Exception:
                            pass
                        return
                else:
                    # For other tools, return empty events for now
                    self._json(200, {"items": [], "since": 0})
                    return
        except Exception as e:
            self._json(500, {"error": f"Failed to get events: {e}"})
        return

    # Import MCP proxy handler
    from .mcp_proxy import handle_mcp_playwright_proxy
    if handle_mcp_playwright_proxy(self):
        return

    self._json(404, {"error": "Not found"})
