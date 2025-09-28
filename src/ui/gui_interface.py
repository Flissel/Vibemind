"""GUI web interface for the assistant.

This launches a lightweight HTTP server that serves a minimal single-page UI
and JSON APIs for sending messages, listing plugins, and running delegation.

- GET /                -> HTML UI
- GET /api/plugins     -> JSON of plugin info (name, description, commands)
- POST /api/message    -> { input: str } -> assistant.process_request
- POST /api/delegate   -> { goal: str } -> delegation.run_delegation

Notes:
- We embed the UI directly as an inline HTML string to avoid extra assets.
- We run assistant async calls on a dedicated asyncio event loop thread.
- This mirrors CLIInterface's contract: initialize(), run(), shutdown().
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import os
import time
import queue
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Tuple
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from mimetypes import guess_type
import urllib.request
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


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


class _AssistantHTTPServer(ThreadingHTTPServer):
    """HTTP server that holds references to assistant and its event loop."""

    def __init__(self, server_address: Tuple[str, int], RequestHandlerClass, assistant, loop: asyncio.AbstractEventLoop):
        super().__init__(server_address, RequestHandlerClass)
        self.assistant = assistant
        self.loop = loop
        # Queues for Server-Sent Events clients to receive reload notifications
        # Using simple Queue per client to avoid locking complexity across threads
        #TODO : FUNGUS SIMULATIONS QUEUE use the formular to produce queue events based on knowlegde with is in the fungus search. (RAG-sytem)
        self.sse_queues: list[queue.Queue] = []
        # --- NEW: Event buffer for JSON polling fallback (/events.json)
        # Clear comments for easy debug; seq increases monotonically across events
        self._events_lock = threading.Lock()
        self._event_seq: int = 0
        self._event_buffer: list[str] = []  # store JSON strings to avoid re-encoding later
        self._event_buffer_max: int = 1000  # cap to prevent unbounded growth

    def broadcast_reload(self):
        """Notify all connected SSE clients to reload the page."""
        # Copy to avoid mutation during iteration
        for q in list(self.sse_queues):
            try:
                q.put_nowait('reload')
            except Exception:
                # If a queue is full or broken, ignore; client will reconnect
                pass

    # --- NEW: generic event broadcaster for structured SSE events ---
    def broadcast_event(self, event_name: str, data: Dict[str, Any] | None = None):
        """Broadcast a named SSE event with JSON data to all clients.
        UI listens via EventSource.addEventListener(event_name, handler).
        Also records a plain JSON message for polling fallback and onmessage consumers.
        """
        # Prepare payload for SSE named event
        payload = {"__sse_event__": str(event_name), "data": data or {}}
        for q in list(self.sse_queues):
            try:
                q.put_nowait(payload)
            except Exception:
                pass
        # Record plain message object for clients that use es.onmessage and for /events.json
        try:
            obj = data if isinstance(data, dict) else {"message": str(data) if data is not None else str(event_name)}
            self._record_event_object(obj)
        except Exception:
            # Never raise from broadcasting
            pass

    # --- NEW: record and retrieve events for JSON polling ---
    def _record_event_object(self, obj: Dict[str, Any]):
        """Attach sequence number and append to buffer. Thread-safe."""
        try:
            with self._events_lock:
                self._event_seq += 1
                obj["seq"] = self._event_seq
                # Encode once to JSON string; UI expects JSON objects per line
                data_json = json.dumps(obj)
                self._event_buffer.append(data_json)
                # Trim buffer if exceeding max
                if len(self._event_buffer) > self._event_buffer_max:
                    # drop oldest half to reduce churn
                    drop = len(self._event_buffer) - self._event_buffer_max
                    del self._event_buffer[:drop]
        except Exception:
            pass

    def _get_events_since(self, since: int) -> Tuple[list[str], int]:
        """Return buffered event JSON strings with seq > since and latest seq."""
        try:
            with self._events_lock:
                latest = self._event_seq
                if since <= 0:
                    # Return recent tail to avoid flooding
                    tail = self._event_buffer[-50:] if len(self._event_buffer) > 50 else list(self._event_buffer)
                    return tail, latest
                # Filter by parsing seq from JSON; keep efficient by simple scan
                # Note: storing seq inside JSON; we need to parse lightly
                items: list[str] = []
                for s in self._event_buffer:
                    try:
                        d = json.loads(s)
                        if int(d.get("seq") or 0) > since:
                            items.append(s)
                    except Exception:
                        # If malformed, include to avoid missing info
                        items.append(s)
                return items, latest
        except Exception:
            return [], 0

class _ReloadEventHandler(FileSystemEventHandler):
    """Watchdog handler that broadcasts reload events on file changes.

    Debounces rapid sequences of file events to avoid spamming the browser.
    """

    def __init__(self, server: _AssistantHTTPServer, watch_exts: set[str], debounce_ms: int = 400):
        super().__init__()
        self.server = server
        self.watch_exts = {ext.lower() for ext in (watch_exts or {'.py'})}
        self.debounce_ms = debounce_ms
        self._last_emit = 0.0

    def _maybe_emit(self, path: str):
        try:
            ext = os.path.splitext(path)[1].lower()
            if self.watch_exts and ext not in self.watch_exts:
                return
        except Exception:
            pass
        now = time.time()
        if (now - self._last_emit) * 1000.0 >= self.debounce_ms:
            self._last_emit = now
            try:
                self.server.broadcast_reload()
            except Exception:
                pass

    # Handle any FS event uniformly
    def on_any_event(self, event):
        try:
            if getattr(event, 'is_directory', False):
                return
            self._maybe_emit(getattr(event, 'src_path', '') or '')
        except Exception:
            pass


class _GUIRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the GUI web app and JSON APIs.

    Serves the single-page UI, SSE reload stream, and JSON endpoints
    for plugins, learning insights, message processing, delegation, and tools.
    """

    def log_message(self, format: str, *args) -> None:  # reduce console noise
        logger.debug("GUI HTTP: " + format, *args)

    def _json(self, status: int, data: Dict[str, Any]):
        # Robust JSON writer: tolerate client-aborted connections and serialization failures
        try:
            body = json.dumps(data).encode("utf-8")
        except Exception:
            try:
                body = json.dumps({"error": "serialization_failure", "repr": str(data)}).encode("utf-8")
            except Exception:
                body = b"{}"
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (ConnectionAbortedError, BrokenPipeError):
                # Client closed connection; suppress noisy errors
                return
            except Exception:
                # Unexpected write error; ignore to avoid cascading failures
                return
        except (ConnectionAbortedError, BrokenPipeError):
            # Client disconnected during header write; nothing to do
            return
        except Exception:
            # Unexpected header write error; suppress
            return
        # Note: intentionally no second write here; body is written once inside the protected block.

    # --- NEW: Robust upstream fetch with exponential backoff for transient errors ---
    # Clear comments for easy debug; matches naming conventions.
    from contextlib import contextmanager
    @contextmanager
    def _fetch_with_backoff(self, req, timeout: float = 5.0, attempts: int = 4, base_delay: float = 0.25, max_delay: float = 2.0):
        """
        Attempt to open the given urllib.request.Request with exponential backoff.
        - Retries only on transient network errors (URLError, timeouts, ConnectionReset)
        - Does NOT retry on upstream HTTP errors (HTTPError); those are raised for caller to forward
        - Yields a response object that is closed automatically on context exit
        """
        import urllib.request, urllib.error
        last_exc = None
        for i in range(int(max(1, attempts))):
            try:
                r = urllib.request.urlopen(req, timeout=timeout)
                try:
                    yield r
                finally:
                    try:
                        r.close()
                    except Exception:
                        pass
                return
            except urllib.error.HTTPError as e:
                # Do not retry on HTTP error; forward upstream status as-is
                raise
            except Exception as e:
                # Transient error: backoff and retry
                last_exc = e
                if i + 1 >= int(max(1, attempts)):
                    break
                try:
                    # Progressive delay: base * 2^i, capped to max_delay
                    delay = base_delay * (2 ** i)
                    if max_delay is not None:
                        delay = min(delay, max_delay)
                    time.sleep(delay)
                except Exception:
                    pass
        # Exhausted retries; raise last exception for caller
        if last_exc is not None:
            raise last_exc
        # Fallback: raise a generic error
        raise RuntimeError("Upstream fetch failed without specific exception")

    def do_GET(self):  # noqa: N802
        if self.path == "/":
            body = (self.INDEX_HTML or "<html><body><h1>GUI</h1><p>Initialization fallback.</p></body></html>").encode("utf-8")  # Safe fallback if INDEX_HTML is None
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # --- NEW: Health check endpoint for embedded viewers
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

        # Server-Sent Events endpoint for auto-reload notifications
        # --- Local SSE stream for reload and GUI events ---
        if self.path == "/events":
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                # Register client queue
                q = queue.Queue(maxsize=100)
                self.server.sse_queues.append(q)  # type: ignore[attr-defined]
                # Initial connected comment
                try:
                    self.wfile.write(b":connected\n\n"); self.wfile.flush()
                except Exception:
                    pass
                # Stream loop
                try:
                    while True:
                        try:
                            item = q.get(timeout=30.0)
                        except Exception:
                            # Heartbeat
                            try:
                                self.wfile.write(b":heartbeat\n\n"); self.wfile.flush()
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
                        except Exception:
                            break
                finally:
                    try:
                        self.server.sse_queues.remove(q)  # type: ignore[attr-defined]
                    except Exception:
                        pass
            except Exception:
                try:
                    self._json(500, {"error": "SSE stream failed"})
                except Exception:
                    pass
            return

        # --- NEW: JSON polling fallback for events (used by embedded viewer)
        if self.path.startswith("/events.json"):
            try:
                # Parse "since" query param
                since = 0
                try:
                    from urllib.parse import urlparse, parse_qs
                    qs = parse_qs(urlparse(self.path).query)
                    since = int((qs.get("since") or ["0"])[0])
                except Exception:
                    since = 0
                items, latest = self.server._get_events_since(since)  # type: ignore[attr-defined]
                self._json(200, {"items": items, "since": latest})
            except Exception as e:
                self._json(500, {"error": f"Failed to get events: {e}"})
            return

        # --- PROXY: Playwright UI SSE and JSON endpoints under /mcp/playwright ---
        # We forward to the Playwright EventServer (default 127.0.0.1:8787) so the embedded
        # viewer can receive real-time browser events and previews.
        # Clear comments for easy debug.
        if self.path == "/mcp/playwright/events":
            try:
                # Prepare response headers for SSE
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                # Resolve target host/port
                host = os.getenv("MCP_UI_HOST", "127.0.0.1")
                try:
                    port = int(os.getenv("MCP_UI_PORT", "8787"))
                except Exception:
                    port = 8787
                # Stream from Playwright server and pipe through to client
                try:
                    import http.client
                    conn = http.client.HTTPConnection(host, port, timeout=10)
                    conn.request("GET", "/events", headers={
                        "Accept": "text/event-stream",
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                    })
                    resp = conn.getresponse()
                    if resp.status != 200:
                        try:
                            self.wfile.write(f"data: Proxy upstream error HTTP {resp.status}\n\n".encode("utf-8"))
                            self.wfile.flush()
                        except Exception:
                            pass
                        return
                    # Write an initial connected comment
                    try:
                        self.wfile.write(b":proxy-connected\n\n"); self.wfile.flush()
                    except Exception:
                        pass
                    # Read small chunks and forward until upstream closes or client disconnects
                    while True:
                        try:
                            chunk = resp.read(1024)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            try:
                                self.wfile.flush()
                            except Exception:
                                pass
                        except Exception:
                            break
                except Exception as e:
                    try:
                        self.wfile.write(f"data: Proxy failed: {e}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except Exception:
                        pass
                return
            except Exception:
                # On header write failure, just return
                return
        
        if self.path.startswith("/mcp/playwright/events.json"):
            try:
                # Proxy JSON polling to Playwright EventServer with backoff and pass-through of HTTP errors
                try:
                    from urllib.parse import urlparse
                    import urllib.request, urllib.error
                except Exception:
                    urlparse = None  # type: ignore
                host = os.getenv("MCP_UI_HOST", "127.0.0.1")
                try:
                    port = int(os.getenv("MCP_UI_PORT", "8787"))
                except Exception:
                    port = 8787
                # Preserve query string
                upstream_path = "/events.json"
                try:
                    if urlparse:
                        upstream_path += ("?" + urlparse(self.path).query)
                except Exception:
                    pass
                url = f"http://{host}:{port}{upstream_path}"
                try:
                    req = urllib.request.Request(url, headers={"Accept": "application/json"})
                    # Use the same retry/backoff strategy as preview.png for resilience
                    with self._fetch_with_backoff(req, timeout=2.5, attempts=4, base_delay=0.25) as r:
                        body = r.read()
                        ctype = r.headers.get("Content-Type", "application/json; charset=utf-8")
                        status = getattr(r, "status", 200)
                        self.send_response(status)
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
                    # Forward upstream HTTP error code and body (e.g., 404) without converting to 502
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
            except Exception as e:
                self._json(500, {"error": f"Proxy error: {e}"})
            return
        
        # --- PROXY: Health endpoint for Playwright EventServer, surfaced as JSON with latency ---
        if self.path == "/mcp/playwright/health":
            try:
                import urllib.request, urllib.error
                host = os.getenv("MCP_UI_HOST", "127.0.0.1")
                try:
                    port = int(os.getenv("MCP_UI_PORT", "8787"))
                except Exception:
                    port = 8787
                url = f"http://{host}:{port}/health"
                t0 = time.time()
                try:
                    # Prefer plain text but accept JSON or anything
                    req = urllib.request.Request(url, headers={"Accept": "text/plain, application/json;q=0.9, */*;q=0.8"})
                    with self._fetch_with_backoff(req, timeout=1.5, attempts=3, base_delay=0.2) as r:
                        _ = r.read()  # upstream usually returns "ok"; content is not needed
                        latency_ms = int(max(0, (time.time() - t0) * 1000))
                        # Maintain an "up since" timestamp across successful checks
                        prev = getattr(self.server, "_mcp_playwright_up_since_ts", None)  # type: ignore[attr-defined]
                        if prev is None:
                            try:
                                setattr(self.server, "_mcp_playwright_up_since_ts", time.time())  # type: ignore[attr-defined]
                                prev = getattr(self.server, "_mcp_playwright_up_since_ts", None)  # type: ignore[attr-defined]
                            except Exception:
                                prev = time.time()
                        try:
                            since_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(prev) if prev else time.time()))
                        except Exception:
                            since_iso = None
                        self._json(200, {"available": True, "latency_ms": latency_ms, "since": since_iso})
                        return
                except urllib.error.HTTPError as e:
                    # Forward upstream HTTP error as unavailable with same status code
                    latency_ms = int(max(0, (time.time() - t0) * 1000))
                    try:
                        setattr(self.server, "_mcp_playwright_up_since_ts", None)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    try:
                        err_body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
                    except Exception:
                        err_body = ""
                    self._json(getattr(e, "code", 502), {"available": False, "latency_ms": latency_ms, "error": err_body or f"HTTP {getattr(e, 'code', 500)}"})
                    return
                except Exception as e:
                    latency_ms = int(max(0, (time.time() - t0) * 1000))
                    try:
                        setattr(self.server, "_mcp_playwright_up_since_ts", None)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    self._json(502, {"available": False, "latency_ms": latency_ms, "error": str(e)})
                    return
            except Exception as e:
                self._json(500, {"available": False, "error": f"Proxy error: {e}"})
                return
        
        if self.path.startswith("/mcp/playwright/preview.png"):
            try:
                # Proxy latest preview PNG from Playwright server
                # - Accept query params (e.g., cache-busting ts) and forward upstream
                # - Pass through upstream HTTP status codes (notably 404) instead of converting to 502
                import urllib.request, urllib.error
                from urllib.parse import urlparse
                host = os.getenv("MCP_UI_HOST", "127.0.0.1")
                try:
                    port = int(os.getenv("MCP_UI_PORT", "8787"))
                except Exception:
                    port = 8787
                # Preserve original query string from client request
                parsed = urlparse(self.path)
                upstream_path = "/preview.png"
                if parsed.query:
                    upstream_path += ("?" + parsed.query)
                url = f"http://{host}:{port}{upstream_path}"
                try:
                    # Prefer image content but accept anything the upstream returns
                    req = urllib.request.Request(url, headers={"Accept": "image/png, */*"})
                    with self._fetch_with_backoff(req, timeout=2.0, attempts=4, base_delay=0.25) as r:
                        body = r.read()
                        ctype = r.headers.get("Content-Type", "image/png")
                        status = getattr(r, "status", 200)
                        self.send_response(status)
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
                except urllib.error.HTTPError as e:
                    # Forward upstream HTTP error code and body (e.g., 404) without converting to 502
                    try:
                        err_body = e.read() if hasattr(e, "read") else b""
                    except Exception:
                        err_body = b""
                    ctype = e.headers.get("Content-Type", "application/json; charset=utf-8") if hasattr(e, "headers") else "application/octet-stream"
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

            except Exception as e:
                try:
                    self._json(502, {"error": f"Proxy error: {e}"})
                except Exception:
                    pass
                return

        if self.path.startswith("/mcp/playwright"):
            rel = self.path[len("/mcp/playwright"):]
            if not rel or rel == "/":
                rel = "/index.html"
            public_dir = Path(__file__).parent.parent / "MCP PLUGINS" / "servers" / "playwright" / "public"
            file_path = public_dir / rel.lstrip("/")
            if file_path.is_file():
                ctype = guess_type(str(file_path))[0] or "application/octet-stream"
                data = file_path.read_bytes()
                # For app.js, rewrite endpoints to use /mcp/playwright proxy paths
                try:
                    if file_path.name == "app.js":
                        s = data.decode("utf-8", errors="ignore")
                        s = s.replace("new EventSource('/events')", "new EventSource('/mcp/playwright/events')")
                        s = s.replace("'/events.json?since='", "'/mcp/playwright/events.json?since='")
                        s = s.replace("fetch('/health'", "fetch('/mcp/playwright/health'")
                        data = s.encode("utf-8")
                except Exception:
                    pass
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_error(404)
            return

        if self.path == "/api/plugins":
            try:
                info = self.server.assistant.plugin_manager.get_plugin_info()  # type: ignore[attr-defined]
                # Normalize to a list of plugin dicts
                plugins = []
                if isinstance(info, dict):
                    for name, meta in info.items():
                        plugins.append({
                            "name": name,
                            "description": meta.get("description"),
                            "commands": sorted(meta.get("commands", [])),
                        })
                elif isinstance(info, list):
                    # Already a list of dicts
                    plugins = info
                self._json(200, {"plugins": plugins})
            except Exception as e:
                self._json(500, {"error": f"Failed to get plugins: {e}"})
            return

        if self.path == "/api/learning":
            try:
                coro = _gather_learning_insights(self.server.assistant)  # type: ignore[attr-defined]
                fut = asyncio.run_coroutine_threadsafe(coro, self.server.loop)  # type: ignore[attr-defined]
                result = fut.result(timeout=30)
                self._json(200, result)
            except Exception as e:
                self._json(500, {"error": f"Failed to gather insights: {e}"})
            return

        self._json(404, {"error": "Not found"})

    def do_POST(self):  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            self._json(400, {"error": "Invalid JSON"})
            return

        # --- NEW: /api/chat -> infer MCP job and enqueue, broadcast SSE ---
        if self.path == "/api/chat":
            try:
                text = (data.get("input") or "").strip()
                if not text:
                    self._json(400, {"error": "'input' is required"})
                    return
                # Lazy import to avoid circulars and keep startup quick
                from ..core.orchestrator import Orchestrator
                from ..core.mcp_contracts import JobEnqueuedEvent
                # Ensure orchestrator exists on assistant
                orchestrator = getattr(self.server.assistant, 'orchestrator', None)  # type: ignore[attr-defined]
                if orchestrator is None:
                    try:
                        orchestrator = Orchestrator()
                        setattr(self.server.assistant, 'orchestrator', orchestrator)  # type: ignore[attr-defined]
                    except Exception:
                        orchestrator = Orchestrator()  # fallback
                # Infer job spec
                params = data.get('params') if isinstance(data, dict) else None
                job = orchestrator.infer_job(text, params)
                # Verify TaskQueue is available
                tq = getattr(self.server, 'task_queue', None)  # type: ignore[attr-defined]
                if tq is None:
                    self._json(500, {"error": "TaskQueue not initialized"})
                    return
                job = tq.put(job)
                # Broadcast enqueued event to UI for observability
                try:
                    enq = JobEnqueuedEvent(
                        correlation_id=job.correlation_id,
                        job_id=job.job_id,
                        server_target=job.server_target,
                        task=job.task,
                    )
                    self.server.broadcast_event('mcp.job.enqueued', enq.to_dict())  # type: ignore[attr-defined]
                except Exception:
                    # Non-fatal; queueing succeeded even if SSE failed
                    pass
                self._json(200, {"success": True, "job": job.to_dict(), "queued": getattr(tq, 'size', 0)})
            except Exception as e:
                self._json(500, {"error": f"Chat enqueue failed: {e}"})
            return

        if self.path == "/api/message":
            text = (data.get("input") or "").strip()
            if not text:
                self._json(400, {"error": "'input' is required"})
                return
            try:
                # Run assistant.process_request on the UI event loop
                coro = self.server.assistant.process_request(text)  # type: ignore[attr-defined]
                fut = asyncio.run_coroutine_threadsafe(coro, self.server.loop)  # type: ignore[attr-defined]
                result = fut.result(timeout=300)
                self._json(200, result)
            except Exception as e:
                self._json(500, {"error": f"Processing failed: {e}"})
            return

        if self.path == "/api/delegate":
            goal = (data.get("goal") or "").strip()
            if not goal:
                self._json(400, {"error": "'goal' is required"})
                return
            try:
                from ..delegation.delegation_entry import run_delegation
                coro = run_delegation(goal)
                fut = asyncio.run_coroutine_threadsafe(coro, self.server.loop)  # type: ignore[attr-defined]
                result = fut.result(timeout=600)
                self._json(200, result)
            except Exception as e:
                self._json(500, {"error": f"Delegation failed: {e}"})
            return

        # New tool calling endpoint: routes simple tool commands directly to plugin manager
        if self.path == "/api/tool":
            command = (data.get("command") or "").strip()
            if not command:
                self._json(400, {"error": "'command' is required"})
                return
            try:
                # Build minimal context; plugins can ignore or use it
                context: Dict[str, Any] = {"source": "gui_tool"}
                # Execute via plugin manager on assistant loop
                coro = self.server.assistant.plugin_manager.handle_command(command, context)  # type: ignore[attr-defined]
                fut = asyncio.run_coroutine_threadsafe(coro, self.server.loop)  # type: ignore[attr-defined]
                resp = fut.result(timeout=60)
                if not resp:
                    self._json(404, {"success": False, "error": "Unknown or unsupported command"})
                    return
                # Simple verification for util.print: echo should match input
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
                        # Record verification pattern to memory for learning
                        if hasattr(self.server.assistant, 'memory_manager') and self.server.assistant.memory_manager:  # type: ignore[attr-defined]
                            vcoro = self.server.assistant.memory_manager.detect_pattern('tool_usage', {  # type: ignore[attr-defined]
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

        # --- NEW: Broadcast arbitrary GUI events to connected clients ---
        if self.path == "/api/gui_event":
            event_name = (data.get("event") or "").strip()
            if not event_name:
                self._json(400, {"error": "'event' is required"})
                return
            event_data = data.get("data") if isinstance(data, dict) else None
            try:
                self.server.broadcast_event(event_name, event_data)  # type: ignore[attr-defined]
                self._json(200, {"success": True, "event": event_name})
            except Exception as e:
                self._json(500, {"success": False, "error": f"Failed to broadcast event: {e}"})
            return

        self._json(404, {"error": "Not found"})


class GUIInterface:
    """Graphical (web) interface that serves the minimal SPA and JSON APIs.

    Follows the same interface contract as CLIInterface with
    async initialize(), run(), and shutdown() methods.
    """

    def __init__(self, assistant, host: str = "127.0.0.1", port: int = 8765):
        # Keep references for request handlers and for main to log host/port
        self.assistant = assistant
        self.host = host
        self.port = port
        
        # HTTP server and threads
        self._httpd = None  # type: ignore[assignment]
        self._server_thread = None  # type: ignore[assignment]
        
        # Dedicated asyncio loop running in a background thread for async tasks
        self.loop = None  # type: ignore[assignment]
        self._loop_thread = None  # type: ignore[assignment]
        
        # Filesystem watcher for UI auto-reload
        self._observer = None  # type: ignore[assignment]

        # Control flag for run loop
        self._running = False
        # --- NEW: TaskQueue and Scheduler references ---
        self._task_queue = None  # type: ignore[assignment]
        self._scheduler = None  # type: ignore[assignment]

    async def initialize(self):
        """Initialize web server and background event loop."""
        # Start dedicated asyncio loop in a background thread
        loop_ready = threading.Event()

        def _loop_worker():
            # Create and run a dedicated event loop for GUI async tasks
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            self.loop = new_loop
            loop_ready.set()
            try:
                new_loop.run_forever()
            finally:
                try:
                    new_loop.run_until_complete(new_loop.shutdown_asyncgens())
                except Exception:
                    pass
                new_loop.close()

        self._loop_thread = threading.Thread(target=_loop_worker, name="GUIAsyncLoop", daemon=True)
        self._loop_thread.start()
        # Wait until loop is ready before starting HTTP server
        loop_ready.wait(timeout=5)

        # Build inline HTML for the GUI and assign to handler class
        try:
            _GUIRequestHandler.INDEX_HTML = self._build_index_html()
        except Exception:
            # If HTML assignment fails, ensure handler has a minimal fallback
            logger.exception("Failed to build INDEX_HTML; using minimal fallback UI")
            _GUIRequestHandler.INDEX_HTML = "<html><body><h1>GUI</h1><p>Initialization fallback.</p></body></html>"

        # Bind HTTP server; if port is busy, try a few subsequent ports
        bind_host = self.host
        bind_port = self.port
        last_err = None
        for attempt in range(0, 10):
            try:
                self._httpd = _AssistantHTTPServer((bind_host, bind_port), _GUIRequestHandler, self.assistant, self.loop)  # type: ignore[arg-type]
                break
            except OSError as e:
                last_err = e
                bind_port += 1  # try next port
        if self._httpd is None:
            # Could not bind to any port
            raise RuntimeError(f"Failed to start GUI server: {last_err}")

        # Update actual bound address for logging in main
        self.host, self.port = self._httpd.server_address  # type: ignore[assignment]

        # --- NEW: Attach Orchestrator, TaskQueue, and start Scheduler ---
        try:
            # Ensure assistant has an orchestrator in Phase 1
            from ..core.orchestrator import Orchestrator
            if not hasattr(self.assistant, 'orchestrator') or getattr(self.assistant, 'orchestrator') is None:
                setattr(self.assistant, 'orchestrator', Orchestrator())
        except Exception:
            logger.debug("Failed to attach Orchestrator; proceeding without it")
        try:
            # Create TaskQueue and expose on HTTP server for handlers
            from ..core.task_queue import TaskQueue
            self._task_queue = TaskQueue()
            setattr(self._httpd, 'task_queue', self._task_queue)
            # Scheduler runs in background thread, emitting SSE report events
            from ..execution.scheduler import Scheduler
            self._scheduler = Scheduler(queue=self._task_queue, emit=self._httpd.broadcast_event)
            self._scheduler.start()
            logger.info("Scheduler started for MCP jobs")
        except Exception as e:
            logger.debug(f"Scheduler setup failed: {e}")

        # Start HTTP server in its own thread
        def _serve():
            try:
                self._httpd.serve_forever(poll_interval=0.5)
            except Exception:
                # Server shut down or failed; no noisy logs needed here
                pass

        self._server_thread = threading.Thread(target=_serve, name="GUIHTTPServer", daemon=True)
        self._server_thread.start()
        self._running = True

        # Start file watcher to broadcast reload events on code changes
        try:
            exts = {'.py', '.js', '.css', '.html', '.json'}
            handler = _ReloadEventHandler(self._httpd, watch_exts=exts, debounce_ms=500)  # type: ignore[arg-type]
            observer = Observer()
            # Determine directories to watch
            watch_dirs = []
            try:
                cfg = getattr(self.assistant, 'config', None)
                if cfg:
                    # Watch source and plugins directories
                    watch_dirs.append(str(cfg.base_dir / 'src'))
                    watch_dirs.append(str(cfg.plugins_dir))
            except Exception:
                pass
            # Also watch the UI module directory as a fallback
            ui_dir = os.path.dirname(__file__)
            if ui_dir:
                watch_dirs.append(ui_dir)
            # Schedule watchers
            for d in watch_dirs:
                if d and os.path.isdir(d):
                    observer.schedule(handler, d, recursive=True)
            observer.daemon = True
            observer.start()
            self._observer = observer
            logger.info(f"Auto-reload watcher started for: {', '.join([d for d in watch_dirs if os.path.isdir(d)])}")
        except Exception as e:
            logger.debug(f"Auto-reload watcher not started: {e}")

        # GUI initialized successfully; HTTP server and watcher are running
        logger.info(f"GUI server started at http://{self.host}:{self.port}/")

    async def run(self):
        """Keep GUI server running asynchronously."""
        while self._running:
            await asyncio.sleep(1)

    async def shutdown(self):
        """Shutdown GUI server, file watcher, and background event loop."""
        # Stop HTTP server
        try:
            if self._httpd:
                self._httpd.shutdown()
                self._httpd.server_close()
        except Exception:
            pass
        finally:
            self._httpd = None
        # --- NEW: Stop Scheduler ---
        try:
            if self._scheduler:
                self._scheduler.stop()
        except Exception:
            pass
        finally:
            self._scheduler = None
            self._task_queue = None

    def _build_index_html(self) -> str:
        """Construct inline HTML for the GUI.
        Includes:
        - Minimal chat input and output area
        - SSE connection to /events for hot-reload
        - Buttons to list plugins and send messages
        """
        # Build HTML using string.Template to avoid f-string brace escaping issues
        from string import Template
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Sakana Desktop Assistant</title>
<style>
  body { font-family: system-ui, Arial, sans-serif; margin: 0; background: #0b1f2a; color: #e6f1ff; }
  header { padding: 16px 20px; background: #0f2b3a; border-bottom: 1px solid #163a4d; }
  h1 { margin: 0; font-size: 18px; }
  main { padding: 16px 20px; }
  .row { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
  input[type=text] { flex: 1; min-width: 240px; padding: 10px; border-radius: 6px; border: 1px solid #28536b; background: #0c2230; color: #e6f1ff; }
  button { padding: 10px 14px; border-radius: 6px; border: 1px solid #28536b; background: #133349; color: #e6f1ff; cursor: pointer; }
  button.active { background: #1a4a65; }
  button:hover { background: #16425a; }
  pre { background: #0c2230; padding: 12px; border-radius: 8px; border: 1px solid #28536b; white-space: pre-wrap; }
  .status { font-size: 12px; opacity: 0.8; }
  /* Debug UI styles */
  .muted { opacity: 0.8; font-size: 12px; }
  .plugin-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin-top: 8px; }
  .plugin-card { border: 1px solid #28536b; background: #0c2230; padding: 12px; border-radius: 8px; }
  .plugin-card h3 { margin: 0 0 8px; font-size: 15px; }
  .plugin-card p { margin: 0; font-size: 12px; color: #acd1ff; }
  .command-list { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
  .command-item { display: flex; gap: 8px; align-items: center; }
  .command-item code { background: #09202d; padding: 4px 6px; border-radius: 6px; border: 1px solid #1c4257; }
  .usage { background: #081b26; border: 1px dashed #28536b; padding: 8px; border-radius: 6px; color: #cfe7ff; }
</style>
</head>
<body>
<header>
  <h1>🐟 Sakana Desktop Assistant</h1>
  <div class="status">GUI connected to http://$HOST:$PORT</div>
</header>
<main>
  <div class="row">
    <input id="chat-input" type="text" placeholder="Type a message…" />
    <button id="send-btn">Send</button>
    <button id="plugins" title="List available plugins">Plugins</button>
    <button id="debug-toggle" title="Toggle debug view for plugin buttons">Debug: OFF</button>
  </div>
  <div class="row">
    <input id="tool-input" type="text" placeholder="Enter tool command, e.g. util.print hello" />
    <button id="run-tool" title="Run /api/tool command">Run Tool</button>
  </div>
  <div id="chat-log"></div>
  <nav>
    <button id="tab-chat" class="active">Chat</button>
    <button id="tab-playwright">Playwright</button>
  </nav>
  <div id="content-chat"></div>
  <div id="content-playwright" style="display:none;">
    <!-- Live Preview component for real-time debugging -->
    <section id="live-preview" style="margin: 10px 0;">
      <div style="display:flex; gap:12px; align-items:flex-start;">
        <div style="flex:1;">
          <img id="live-preview-img" src="" alt="Live Preview" style="width:100%; max-height:30vh; object-fit:contain; border:1px solid #ddd; border-radius:4px; background:#fafafa;" />
        </div>
        <div style="width:280px;">
          <div id="playwright-status" style="font-family: monospace; font-size: 12px; white-space: pre-line;">Status: initializing…</div>
          <button id="live-preview-toggle">Pause Preview</button>
        </div>
      </div>
    </section>
    <iframe id="playwright-frame" src="/mcp/playwright" style="width:100%; height:70vh; border:none;"></iframe>
  </div>
</main>
<script>
  // --- Tabs ---
  document.getElementById('tab-chat').onclick = () => {
    document.getElementById('content-chat').style.display = '';
    document.getElementById('content-playwright').style.display = 'none';
    document.getElementById('tab-chat').classList.add('active');
    document.getElementById('tab-playwright').classList.remove('active');
    try { stopLivePreviewPolling(); } catch(e){}
  };
  document.getElementById('tab-playwright').onclick = () => {
    document.getElementById('content-chat').style.display = 'none';
    document.getElementById('content-playwright').style.display = '';
    document.getElementById('tab-chat').classList.remove('active');
    document.getElementById('tab-playwright').classList.add('active');
    try { startLivePreviewPolling(); } catch(e){}
  };

  // Helper to programmatically switch to the Playwright tab
  function openPlaywrightTab() {
    // Use the same behavior as clicking the Playwright tab button to keep logic in one place
    const btn = document.getElementById('tab-playwright');
    if (btn && typeof btn.click === 'function') { btn.click(); return; }
    // Fallback in case click is unavailable
    try {
      document.getElementById('content-chat').style.display = 'none';
      document.getElementById('content-playwright').style.display = '';
      document.getElementById('tab-chat').classList.remove('active');
      document.getElementById('tab-playwright').classList.add('active');
      const frame = document.getElementById('playwright-frame');
      if (frame && frame.contentWindow) frame.contentWindow.focus();
    } catch(_e) {}
  }

  // --- JSON POST helper ---
  async function postJSON(path, payload) {
    const res = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    return await res.json();
  }

  // --- Chat send ---
  const msg = document.getElementById('chat-input');
  const out = document.getElementById('chat-log');
  const send = document.getElementById('send-btn');
  send.addEventListener('click', async () => {
    const text = msg.value.trim();
    if (!text) return;
    out.textContent = 'Thinking...';
    try {
      const r = await postJSON('/api/message', { input: text });
      out.textContent = JSON.stringify(r, null, 2);
    } catch (e) {
      out.textContent = 'Error: ' + e;
    }
  });

  // --- Debug toggle ---
  let debugEnabled = false;
  const btnDebug = document.getElementById('debug-toggle');
  if (btnDebug) {
    btnDebug.addEventListener('click', () => {
      debugEnabled = !debugEnabled;
      btnDebug.textContent = 'Debug: ' + (debugEnabled ? 'ON' : 'OFF');
      // Clear view when toggling on
      if (debugEnabled) { out.innerHTML = '<div class="muted">Debug mode enabled. Click Plugins to view button-based list.</div>'; }
      else { out.textContent = ''; }
    });
  }

  // --- Escape HTML utility ---
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Lightweight log appender for SSE updates
  function appendLog(text) {
    try {
      const ts = new Date().toLocaleTimeString();
      const line = `[${ts}] ${text}\n`;
      if (out) {
        out.textContent = (out.textContent || '') + line;
        out.scrollTop = out.scrollHeight || 0;
      }
    } catch(_e) {}
  }

  // --- Render plugin debug view ---
  function renderPluginsDebug(plugins) {
    const grid = document.createElement('div');
    grid.className = 'plugin-grid';
    plugins.forEach(p => {
      const card = document.createElement('div');
      card.className = 'plugin-card';
      card.innerHTML = `<h3>${escapeHtml(p.name)} <span class="muted">v${escapeHtml(p.version || '')}</span></h3>
        <p>${escapeHtml(p.description || '')}</p>
        <div class="command-list"></div>`;
      const cmdList = card.querySelector('.command-list');
      (p.commands || []).forEach(cmd => {
        const row = document.createElement('div');
        row.className = 'command-item';
        const btn = document.createElement('button');
        btn.textContent = cmd;
        btn.title = 'Show parameters/usage';
        const usageBox = document.createElement('div');
        usageBox.className = 'usage';
        usageBox.style.display = 'none';
        row.appendChild(btn);
        cmdList.appendChild(row);
        cmdList.appendChild(usageBox);
        btn.addEventListener('click', async () => {
          usageBox.style.display = '';
          usageBox.textContent = 'Loading usage...';
          try {
            // Call /api/tool with only the command; many plugins will return a Usage string
            const r = await postJSON('/api/tool', { command: cmd });
            let txt = '';
            if (r && r.response && typeof r.response === 'object') {
              txt = r.response.content || JSON.stringify(r.response);
            } else if (r && r.error) {
              txt = r.error;
            } else {
              txt = JSON.stringify(r);
            }
            // Provide quick insert into chat input
            const insertBtn = `<div style=\"margin-top:6px;\"><button id=\"ins-${p.name}-${cmd}\">Insert template into chat</button></div>`;
            usageBox.innerHTML = `<div><strong>Output/Usage</strong></div><div style=\"margin-top:4px;\"><code>${escapeHtml(txt)}</code></div>` + insertBtn;
            const ins = usageBox.querySelector(`#ins-${CSS.escape(p.name)}-${CSS.escape(cmd)}`);
            if (ins) ins.addEventListener('click', () => {
              // Try to extract usage template
              let template = txt;
              const m = /^Usage:\\s*(.*)$/im.exec(txt || '');
              if (m && m[1]) template = m[1].trim();
              // If template doesn't start with command name, prefix it
              if (template && !template.toLowerCase().startsWith(cmd.toLowerCase())) {
                template = `${cmd} ${template}`;
              }
              msg.value = template;
              // Focus chat area for quick send
              msg.focus();
            });
          } catch (e) {
            usageBox.textContent = 'Error: ' + e;
          }
        });
      });
      grid.appendChild(card);
    });
    out.innerHTML = '';
    out.appendChild(grid);
  }

  // --- Plugins button ---
  const btnPlugins = document.getElementById('plugins');
  if (btnPlugins) btnPlugins.addEventListener('click', async () => {
    if (!debugEnabled) {
      out.textContent = 'Loading plugins...';
      try {
        const r = await fetch('/api/plugins');
        const j = await r.json();
        out.textContent = JSON.stringify(j, null, 2);
      } catch (e) {
        out.textContent = 'Error: ' + e;
      }
      return;
    }
    // Debug view
    out.textContent = 'Loading plugins (debug)...';
    try {
      const r = await fetch('/api/plugins');
      const j = await r.json();
      const plugins = (j && j.plugins) ? j.plugins : [];
      renderPluginsDebug(plugins);
    } catch (e) {
      out.textContent = 'Error: ' + e;
    }
  });

  // --- Run Tool (/api/tool) ---
  const toolInput = document.getElementById('tool-input');
  const btnTool = document.getElementById('run-tool');
  if (btnTool && toolInput) btnTool.addEventListener('click', async () => {
    const cmd = toolInput.value.trim();
    if (!cmd) return;
    const prev = btnTool.textContent; btnTool.textContent = 'Running…'; btnTool.disabled = true;
    out.textContent = 'Running tool...';
    try {
      const r = await postJSON('/api/tool', { command: cmd });
      out.textContent = JSON.stringify(r, null, 2);
    } catch (e) {
      out.textContent = 'Error: ' + e;
    } finally {
      btnTool.textContent = prev; btnTool.disabled = false;
    }
  });

  // --- SSE Reload & GUI events ---
  try {
    const es = new EventSource('/events');
    es.addEventListener('reload', () => { location.reload(); });
    // Auto-switch to Playwright tab on external GUI event
    es.addEventListener('open_playwright', () => { try { openPlaywrightTab(); } catch(e){} });
    // MCP job lifecycle events
    es.addEventListener('mcp.job.enqueued', (ev) => {
      try {
        const d = ev && ev.data ? JSON.parse(ev.data) : {};
        appendLog(`[ENQUEUED] ${d.job_id || ''} -> ${d.server_target || ''}`);
      } catch(_e) {}
    });
    es.addEventListener('mcp.job.report', (ev) => {
      try {
        const d = ev && ev.data ? JSON.parse(ev.data) : {};
        const st = (d.state || '').toUpperCase();
        appendLog(`[${st}] job ${d.job_id || ''}: ${d.message || ''}`);
        if (debugEnabled && d.outputs) {
          appendLog('outputs: ' + JSON.stringify(d.outputs));
        }
      } catch(_e) {}
    });
  } catch (e) { /* SSE may not be available; ignore */ }

  // --- Listen for activity messages from Playwright iframe ---
  let _sawPlaywrightActivity = false;
  window.addEventListener('message', function(ev){
    try {
      const d = ev && ev.data;
      if (!_sawPlaywrightActivity && d && d.type === 'mcp_playwright_activity') {
        _sawPlaywrightActivity = true;
        openPlaywrightTab();
      }
    } catch(_e) {}
  });

  // --- NEW: Live Preview polling and health status (clear comments for easy debug) ---
  const previewImg = document.getElementById('live-preview-img');
  const statusEl = document.getElementById('playwright-status');
  const toggleBtn = document.getElementById('live-preview-toggle');
  let previewTimer = null;
  let healthTimer = null;
  let previewPaused = false;

  function setStatus(text) {
    try { statusEl.textContent = text; } catch(_e) {}
  }

  function pollPreviewOnce() {
    if (previewPaused) return;
    try {
      // Use cache-busting timestamp to force refresh
      previewImg.src = '/mcp/playwright/preview.png?ts=' + Date.now();
    } catch(_e) {}
  }

  async function checkHealthOnce() {
    try {
      const res = await fetch('/mcp/playwright/health', { cache: 'no-store' });
      const ok = res.ok;
      let j = null;
      try { j = await res.json(); } catch(_e) {}
      if (ok && j && j.available) {
        const ms = (j.latency_ms != null) ? (j.latency_ms + 'ms') : 'n/a';
        setStatus(`Status: available\nLatency: ${ms}\nSince: ${j.since ?? 'n/a'}`);
      } else {
        const code = res.status;
        const err = (j && (j.error || j.detail)) ? JSON.stringify(j.error || j.detail) : '';
        setStatus(`Status: unavailable (HTTP ${code})\n${err ? ('Error: ' + err) : ''}`);
      }
    } catch(e) {
      setStatus(`Status: unavailable\nError: ${e}`);
    }
  }

  function startLivePreviewPolling() {
    try { stopLivePreviewPolling(); } catch(_e) {}
    previewPaused = false;
    if (toggleBtn) { toggleBtn.textContent = 'Pause Preview'; }
    pollPreviewOnce();
    checkHealthOnce();
    previewTimer = setInterval(pollPreviewOnce, 1000);      // 1s image refresh for responsiveness
    healthTimer = setInterval(checkHealthOnce, 2000);       // 2s health check for status
  }

  function stopLivePreviewPolling() {
    previewPaused = true;
    if (toggleBtn) { toggleBtn.textContent = 'Resume Preview'; }
    try { if (previewTimer) { clearInterval(previewTimer); previewTimer = null; } } catch(_e) {}
    try { if (healthTimer) { clearInterval(healthTimer); healthTimer = null; } } catch(_e) {}
  }

  if (toggleBtn) toggleBtn.addEventListener('click', () => {
    if (previewPaused) startLivePreviewPolling(); else stopLivePreviewPolling();
  });

</script>
</body>
</html>
"""
        # Perform explicit replacements for $HOST and $PORT to avoid conflicts with JS `${...}` template literals.
        try:
            return html.replace("$HOST", str(self.host)).replace("$PORT", str(self.port))
        except Exception:
            # If substitution fails unexpectedly, log and return raw HTML for visibility instead of breaking the server.
            logger.exception("Failed to substitute HOST/PORT in INDEX_HTML; returning raw HTML")
            return html