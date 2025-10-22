"""MCP Playwright proxy handlers.

This module handles proxying requests to MCP tool servers,
particularly for Playwright browser automation.
"""

import http.client
import json
import logging
import os
import pathlib
import time
import urllib.request
import urllib.error
from pathlib import Path
from mimetypes import guess_type
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


def handle_mcp_playwright_proxy(handler) -> bool:
    """Handle MCP Playwright proxy routes. Returns True if handled, False otherwise."""

    # Generic MCP tool event proxy - /mcp/{tool}/events
    if handler.path.startswith("/mcp/") and handler.path.endswith("/events"):
        parts = handler.path.split("/")
        if len(parts) >= 4:
            tool = parts[2]  # Extract tool name (github, docker, etc.)
            _handle_generic_tool_sse_proxy(handler, tool)
            return True

    # Legacy proxy routes
    if handler.path == "/mcp/playwright/events":
        _handle_playwright_sse_proxy(handler)
        return True
    
    if handler.path.startswith("/mcp/playwright/events.json"):
        _handle_playwright_events_json_proxy(handler)
        return True
    
    if handler.path == "/mcp/playwright/health":
        _handle_playwright_health_proxy(handler)
        return True
    
    if handler.path.startswith("/mcp/playwright/preview.png"):
        _handle_playwright_preview_proxy(handler)
        return True
    
    # Session-scoped routes
    if handler.path == "/mcp/playwright/session/sse":
        _handle_session_sse_proxy(handler)
        return True
    
    if handler.path.startswith("/mcp/playwright/session/events.json"):
        _handle_session_events_json_proxy(handler)
        return True
    
    if handler.path.startswith("/mcp/playwright/session/preview.png"):
        _handle_session_preview_proxy(handler)
        return True
    
    if handler.path == "/mcp/playwright/session/health":
        _handle_session_health_proxy(handler)
        return True
    
    # Session-specific MCP routes
    if handler.path.startswith("/mcp/playwright/session/"):
        return _handle_session_specific_routes(handler)
    
    # Frontend iframe compatibility
    if handler.path.startswith("/mcp/playwright/") and not handler.path.startswith("/mcp/playwright/session/"):
        return _handle_frontend_compatibility(handler)
    
    if handler.path.startswith("/mcp/playwright"):
        return _handle_static_files(handler)
    
    return False


def _handle_generic_tool_sse_proxy(handler, tool: str):
    """Proxy SSE events from any MCP tool's EventServer.

    Args:
        handler: HTTP request handler
        tool: Tool name (github, docker, playwright, etc.)
    """
    try:
        # Find a running session for this tool to get event port
        sessions_result = handler.server.get_all_mcp_sessions(tool_filter=tool)
        if not sessions_result.get('success', False):
            handler._json(500, {"error": f"Failed to get {tool} sessions"})
            return

        sessions = sessions_result.get('sessions', [])
        running_session = next((s for s in sessions if s.get('status') == 'running'), None)

        if not running_session:
            handler._json(404, {"error": f"No running {tool} session found"})
            return

        session_host = running_session.get('host', '127.0.0.1')
        session_port = running_session.get('port')

        if not session_port:
            handler._json(404, {"error": f"{tool} session has no event port"})
            return

        # Proxy SSE from the tool's event server
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("Connection", "keep-alive")
        handler.end_headers()

        try:
            conn = http.client.HTTPConnection(session_host, session_port, timeout=10)
            conn.request("GET", "/events", headers={
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            })
            resp = conn.getresponse()
            if resp.status != 200:
                try:
                    handler.wfile.write(f"data: Proxy upstream error HTTP {resp.status}\n\n".encode("utf-8"))
                    handler.wfile.flush()
                except Exception:
                    pass
                return

            try:
                handler.wfile.write(b":proxy-connected\n\n"); handler.wfile.flush()
            except Exception:
                pass

            while True:
                try:
                    chunk = resp.read(1024)
                    if not chunk:
                        break
                    handler.wfile.write(chunk)
                    try:
                        handler.wfile.flush()
                    except (ConnectionAbortedError, BrokenPipeError):
                        break
                    except Exception:
                        pass
                except (ConnectionAbortedError, BrokenPipeError):
                    break
                except Exception:
                    break
        except Exception:
            pass
        finally:
            try:
                resp.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
        return
    except Exception as e:
        logger.error(f"Generic tool SSE proxy error for {tool}: {e}")
        return


def _handle_playwright_sse_proxy(handler):
    """Proxy SSE events from Playwright EventServer."""
    try:
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("Connection", "keep-alive")
        handler.end_headers()
        
        session_host = getattr(handler.server, '_playwright_event_host', None) or os.getenv("MCP_UI_HOST", "127.0.0.1")
        try:
            session_port = int(getattr(handler.server, '_playwright_event_port', None) or int(os.getenv("MCP_UI_PORT", "8787")))
        except Exception:
            session_port = 8787
        
        try:
            conn = http.client.HTTPConnection(session_host, session_port, timeout=10)
            conn.request("GET", "/events", headers={
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            })
            resp = conn.getresponse()
            if resp.status != 200:
                try:
                    handler.wfile.write(f"data: Proxy upstream error HTTP {resp.status}\n\n".encode("utf-8"))
                    handler.wfile.flush()
                except Exception:
                    pass
                return
            
            try:
                handler.wfile.write(b":proxy-connected\n\n"); handler.wfile.flush()
            except Exception:
                pass
            
            while True:
                try:
                    chunk = resp.read(1024)
                    if not chunk:
                        break
                    handler.wfile.write(chunk)
                    try:
                        handler.wfile.flush()
                    except (ConnectionAbortedError, BrokenPipeError):
                        break
                    except Exception:
                        pass
                except (ConnectionAbortedError, BrokenPipeError):
                    break
                except Exception:
                    break
        except Exception:
            pass
        finally:
            try:
                resp.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
        return
    except Exception:
        return


def _handle_playwright_events_json_proxy(handler):
    """Proxy JSON event polling to Playwright EventServer."""
    try:
        session_host = getattr(handler.server, '_playwright_event_host', None) or os.getenv("MCP_UI_HOST", "127.0.0.1")
        try:
            session_port = int(getattr(handler.server, '_playwright_event_port', None) or int(os.getenv("MCP_UI_PORT", "8787")))
        except Exception:
            session_port = 8787
        
        upstream_path = "/events.json"
        try:
            upstream_path += ("?" + urlparse(handler.path).query)
        except Exception:
            pass
        
        url = f"http://{session_host}:{session_port}{upstream_path}"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with handler._fetch_with_backoff(req, timeout=2.5, attempts=4, base_delay=0.25) as r:
                body = r.read()
                ctype = r.headers.get("Content-Type", "application/json; charset=utf-8")
                status = getattr(r, "status", 200)
                handler.send_response(status)
                handler.send_header("Content-Type", ctype)
                handler.send_header("Cache-Control", "no-store")
                handler.send_header("Content-Length", str(len(body)))
                handler.end_headers()
                try:
                    handler.wfile.write(body)
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
                handler.send_response(getattr(e, "code", 500))
                handler.send_header("Content-Type", ctype)
                handler.send_header("Cache-Control", "no-store")
                handler.send_header("Content-Length", str(len(err_body)))
                handler.end_headers()
                try:
                    if err_body:
                        handler.wfile.write(err_body)
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
                handler._json(502, {"error": f"Upstream failed: {e}"})
            except Exception:
                pass
            return
    except Exception as e:
        handler._json(500, {"error": f"Proxy error: {e}"})


def _handle_playwright_health_proxy(handler):
    """Proxy health check to Playwright EventServer."""
    try:
        session_host = getattr(handler.server, '_playwright_event_host', None) or os.getenv("MCP_UI_HOST", "127.0.0.1")
        try:
            session_port = int(getattr(handler.server, '_playwright_event_port', None) or int(os.getenv("MCP_UI_PORT", "8787")))
        except Exception:
            session_port = 8787
        
        url = f"http://{session_host}:{session_port}/health"
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"Accept": "text/plain, application/json;q=0.9, */*;q=0.8"})
            with handler._fetch_with_backoff(req, timeout=1.5, attempts=3, base_delay=0.2) as r:
                _ = r.read()
                latency_ms = int(max(0, (time.time() - t0) * 1000))
                prev = getattr(handler.server, "_mcp_playwright_up_since_ts", None)
                if prev is None:
                    try:
                        setattr(handler.server, "_mcp_playwright_up_since_ts", time.time())
                        prev = getattr(handler.server, "_mcp_playwright_up_since_ts", None)
                    except Exception:
                        prev = time.time()
                try:
                    since_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(prev) if prev else time.time()))
                except Exception:
                    since_iso = None
                handler._json(200, {"available": True, "latency_ms": latency_ms, "since": since_iso})
                return
        except urllib.error.HTTPError as e:
            latency_ms = int(max(0, (time.time() - t0) * 1000))
            try:
                setattr(handler.server, "_mcp_playwright_up_since_ts", None)
            except Exception:
                pass
            try:
                err_body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
            except Exception:
                err_body = ""
            handler._json(getattr(e, "code", 502), {"available": False, "latency_ms": latency_ms, "error": err_body or f"HTTP {getattr(e, 'code', 500)}"})
            return
        except Exception as e:
            latency_ms = int(max(0, (time.time() - t0) * 1000))
            try:
                setattr(handler.server, "_mcp_playwright_up_since_ts", None)
            except Exception:
                pass
            handler._json(502, {"available": False, "latency_ms": latency_ms, "error": str(e)})
            return
    except Exception as e:
        handler._json(500, {"available": False, "error": f"Proxy error: {e}"})
        return


def _handle_playwright_preview_proxy(handler):
    """Proxy preview image from Playwright EventServer."""
    try:
        host = os.getenv("MCP_UI_HOST", "127.0.0.1")
        try:
            port = int(os.getenv("MCP_UI_PORT", "8787"))
        except Exception:
            port = 8787
        
        parsed = urlparse(handler.path)
        upstream_path = "/preview.png"
        if parsed.query:
            upstream_path += ("?" + parsed.query)
        url = f"http://{host}:{port}{upstream_path}"
        
        try:
            req = urllib.request.Request(url, headers={"Accept": "image/png, */*"})
            with handler._fetch_with_backoff(req, timeout=2.0, attempts=4, base_delay=0.25) as r:
                body = r.read()
                ctype = r.headers.get("Content-Type", "image/png")
                status = getattr(r, "status", 200)
                handler.send_response(status)
                handler.send_header("Content-Type", ctype)
                handler.send_header("Cache-Control", "no-store")
                handler.send_header("Content-Length", str(len(body)))
                handler.end_headers()
                try:
                    handler.wfile.write(body)
                except (ConnectionAbortedError, BrokenPipeError):
                    return
                except Exception:
                    return
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read() if hasattr(e, "read") else b""
            except Exception:
                err_body = b""
            ctype = e.headers.get("Content-Type", "application/json; charset=utf-8") if hasattr(e, "headers") else "application/octet-stream"
            try:
                handler.send_response(getattr(e, "code", 500))
                handler.send_header("Content-Type", ctype)
                handler.send_header("Cache-Control", "no-store")
                handler.send_header("Content-Length", str(len(err_body)))
                handler.end_headers()
                try:
                    if err_body:
                        handler.wfile.write(err_body)
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
                handler._json(502, {"error": f"Upstream failed: {e}"})
            except Exception:
                pass
            return
    except Exception as e:
        try:
            handler._json(502, {"error": f"Proxy error: {e}"})
        except Exception:
            pass
        return


def _handle_session_sse_proxy(handler):
    """Proxy session-scoped SSE events."""
    _handle_playwright_sse_proxy(handler)


def _handle_session_events_json_proxy(handler):
    """Proxy session-scoped JSON events."""
    _handle_playwright_events_json_proxy(handler)


def _handle_session_preview_proxy(handler):
    """Proxy session-scoped preview image."""
    _handle_playwright_preview_proxy(handler)


def _handle_session_health_proxy(handler):
    """Proxy session-scoped health check."""
    try:
        session_host = getattr(handler.server, '_playwright_event_host', None) or os.getenv("MCP_UI_HOST", "127.0.0.1")
        session_port = getattr(handler.server, '_playwright_event_port', None) or int(os.getenv("MCP_UI_PORT", "8787"))
        url = f"http://{session_host}:{session_port}/health"
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"Accept": "text/plain, application/json;q=0.9, */*;q=0.8"})
            with handler._fetch_with_backoff(req, timeout=1.5, attempts=3, base_delay=0.2) as r:
                _ = r.read()
                latency_ms = int(max(0, (time.time() - t0) * 1000))
                session_id = getattr(handler.server, '_playwright_session_id', None)
                handler._json(200, {
                    "available": True, 
                    "latency_ms": latency_ms, 
                    "session_id": session_id,
                    "host": session_host,
                    "port": session_port,
                })
                return
        except urllib.error.HTTPError as e:
            latency_ms = int(max(0, (time.time() - t0) * 1000))
            try:
                err_body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
            except Exception:
                err_body = ""
            session_id = getattr(handler.server, '_playwright_session_id', None)
            handler._json(getattr(e, "code", 502), {
                "available": False, 
                "latency_ms": latency_ms, 
                "error": err_body or f"HTTP {getattr(e, 'code', 500)}",
                "session_id": session_id,
                "host": session_host,
                "port": session_port,
            })
            return
        except Exception as e:
            latency_ms = int(max(0, (time.time() - t0) * 1000))
            session_id = getattr(handler.server, '_playwright_session_id', None)
            handler._json(502, {
                "available": False, 
                "latency_ms": latency_ms, 
                "error": str(e),
                "session_id": session_id,
                "host": session_host,
                "port": session_port,
            })
            return
    except Exception as e:
        handler._json(500, {"available": False, "error": f"Session proxy error: {e}"})
        return


def _handle_session_specific_routes(handler) -> bool:
    """Handle session-specific MCP routes. Returns True if handled."""
    path_parts = handler.path.split("/")
    if len(path_parts) < 5:
        handler.send_error(404)
        return True
    
    session_id = path_parts[4]
    remaining_path = "/" + "/".join(path_parts[5:]) if len(path_parts) > 5 else "/"
    
    # Guard for static directories
    static_dirs = {"public", "assets", "static", "css", "js", "images", "img"}
    if session_id in static_dirs:
        return _serve_static_asset(handler, session_id, remaining_path)
    
    # Get session configuration
    try:
        sessions_result = handler.server.get_all_playwright_sessions()
        if not sessions_result.get('success', False):
            handler._json(500, {"error": f"Failed to get sessions: {sessions_result.get('error', 'Unknown error')}"})
            return True
        
        sessions = sessions_result.get('sessions', [])
        session = next((s for s in sessions if s["session_id"] == session_id), None)
        
        if not session or session["status"] != "running":
            handler._json(404, {"error": f"Session {session_id} not found or not running"})
            return True
        
        session_host = session.get("host", "127.0.0.1")
        session_port = session.get("port", 8787)
        
        # Handle different request types
        if remaining_path == "/" or remaining_path == "/index.html":
            remaining_path = "/index.html"
        
        if remaining_path.startswith("/events"):
            return _proxy_session_sse(handler, session_host, session_port, remaining_path)
        elif remaining_path.endswith(".json") or remaining_path.startswith("/preview.png") or remaining_path.startswith("/health"):
            return _proxy_session_request(handler, session_host, session_port, remaining_path)
        else:
            return _serve_session_static(handler, remaining_path)
    except Exception as e:
        handler._json(500, {"error": f"Session proxy error: {e}"})
        return True


def _serve_static_asset(handler, session_id, remaining_path) -> bool:
    """Serve static assets from Playwright public directory."""
    public_dir = pathlib.Path(__file__).parent.parent.parent / "MCP PLUGINS" / "servers" / "playwright" / "public"
    normalized = remaining_path.lstrip("/")
    if normalized.startswith("public/"):
        normalized = normalized[len("public/"):]
    file_path = public_dir / normalized
    if file_path.is_file():
        ctype = guess_type(str(file_path))[0] or "application/octet-stream"
        data = file_path.read_bytes()
        handler.send_response(200)
        handler.send_header("Content-Type", ctype)
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)
        return True
    else:
        if not normalized.endswith(".js") and not normalized.endswith(".css"):
            index_path = public_dir / "index.html"
            if index_path.is_file():
                data = index_path.read_bytes()
                handler.send_response(200)
                handler.send_header("Content-Type", "text/html; charset=utf-8")
                handler.send_header("Content-Length", str(len(data)))
                handler.end_headers()
                handler.wfile.write(data)
                return True
        handler.send_error(404, f"File not found: /{normalized}")
        return True


def _proxy_session_sse(handler, session_host, session_port, remaining_path) -> bool:
    """Proxy SSE events for a specific session."""
    try:
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("Connection", "keep-alive")
        handler.end_headers()
        
        conn = http.client.HTTPConnection(session_host, session_port, timeout=10)
        conn.request("GET", remaining_path, headers={
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        })
        resp = conn.getresponse()
        
        if resp.status == 200:
            while True:
                try:
                    chunk = resp.read(1024)
                    if not chunk:
                        break
                    handler.wfile.write(chunk)
                    handler.wfile.flush()
                except (ConnectionAbortedError, BrokenPipeError):
                    break
                except Exception:
                    break
        
        resp.close()
        conn.close()
    except Exception:
        pass
    return True


def _proxy_session_request(handler, session_host, session_port, remaining_path) -> bool:
    """Proxy regular HTTP requests for a specific session."""
    try:
        upstream_path = remaining_path
        try:
            parsed = urlparse(handler.path)
            if parsed.query:
                upstream_path += ("?" + parsed.query)
        except Exception:
            pass
        
        url = f"http://{session_host}:{session_port}{upstream_path}"
        req = urllib.request.Request(url)
        
        with handler._fetch_with_backoff(req, timeout=2.5, attempts=4, base_delay=0.25) as r:
            body = r.read()
            ctype = r.headers.get("Content-Type", "application/octet-stream")
            status = getattr(r, "status", 200)
            handler.send_response(status)
            handler.send_header("Content-Type", ctype)
            handler.send_header("Cache-Control", "no-store")
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            handler.wfile.write(body)
        return True
    except Exception as e:
        handler._json(502, {"error": f"Session proxy failed: {e}"})
        return True


def _serve_session_static(handler, remaining_path) -> bool:
    """Serve static files from Playwright public directory."""
    public_dir = pathlib.Path(__file__).parent.parent.parent / "MCP PLUGINS" / "servers" / "playwright" / "public"
    
    normalized = remaining_path.lstrip("/")
    if normalized.startswith("public/"):
        remaining_path = "/" + normalized[len("public/"):]
    
    file_path = public_dir / remaining_path.lstrip("/")
    
    if remaining_path.lstrip("/") == "app.js":
        app_js_path = public_dir / "app.js"
        if app_js_path.is_file():
            data = app_js_path.read_bytes()
            handler.send_response(200)
            handler.send_header("Content-Type", "application/javascript; charset=utf-8")
            handler.send_header("Content-Length", str(len(data)))
            handler.end_headers()
            handler.wfile.write(data)
            return True
        else:
            handler.send_error(404, "app.js not found")
            return True
    
    if file_path.is_file():
        ctype = guess_type(str(file_path))[0] or "application/octet-stream"
        data = file_path.read_bytes()
        handler.send_response(200)
        handler.send_header("Content-Type", ctype)
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)
        return True
    else:
        if not remaining_path.endswith(".js") and not remaining_path.endswith(".css"):
            index_path = public_dir / "index.html"
            if index_path.is_file():
                data = index_path.read_bytes()
                handler.send_response(200)
                handler.send_header("Content-Type", "text/html; charset=utf-8")
                handler.send_header("Content-Length", str(len(data)))
                handler.end_headers()
                handler.wfile.write(data)
                return True
        else:
            handler.send_error(404, f"File not found: {remaining_path}")
            return True


def _handle_frontend_compatibility(handler) -> bool:
    """Handle frontend iframe compatibility redirects."""
    path_parts = handler.path.split("/")
    if len(path_parts) >= 4 and path_parts[3]:
        session_id = path_parts[3]
        static_dirs = {"public", "assets", "static", "css", "js", "images", "img"}
        if "." not in session_id and session_id not in static_dirs:
            redirect_path = f"/mcp/playwright/session/{session_id}"
            handler.send_response(302)
            handler.send_header("Location", redirect_path)
            handler.end_headers()
            return True
    return False


def _handle_static_files(handler) -> bool:
    """Handle static file serving from Playwright public directory."""
    rel = handler.path[len("/mcp/playwright"):]
    if not rel or rel == "/":
        rel = "/index.html"
    public_dir = Path(__file__).parent.parent.parent / "MCP PLUGINS" / "servers" / "playwright" / "public"
    file_path = public_dir / rel.lstrip("/")
    if file_path.is_file():
        ctype = guess_type(str(file_path))[0] or "application/octet-stream"
        data = file_path.read_bytes()
        handler.send_response(200)
        handler.send_header("Content-Type", ctype)
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)
        return True
    handler.send_error(404)
    return True