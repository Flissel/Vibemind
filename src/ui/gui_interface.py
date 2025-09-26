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

    def broadcast_reload(self):
        """Notify all connected SSE clients to reload the page."""
        # Copy to avoid mutation during iteration
        for q in list(self.sse_queues):
            try:
                q.put_nowait('reload')
            except Exception:
                # If a queue is full or broken, ignore; client will reconnect
                pass
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
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/":
            body = self.INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Server-Sent Events endpoint for auto-reload notifications
        if self.path == "/events":
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                q: queue.Queue = queue.Queue()
                # Register client queue
                self.server.sse_queues.append(q)  # type: ignore[attr-defined]
                # Send initial comment to open stream
                try:
                    self.wfile.write(b":connected\n\n")
                    self.wfile.flush()
                except Exception:
                    # Client disconnected immediately
                    return
                # Stream loop: wait for messages or send keepalives
                while True:
                    try:
                        msg = q.get(timeout=15)
                        if msg == 'reload':
                            payload = b"event: reload\ndata: now\n\n"
                        else:
                            payload = ("data: " + str(msg) + "\n\n").encode('utf-8')
                        self.wfile.write(payload)
                        self.wfile.flush()
                    except queue.Empty:
                        # Periodic keepalive comment to prevent timeouts
                        try:
                            self.wfile.write(b":keepalive\n\n")
                            self.wfile.flush()
                        except Exception:
                            break
                    except Exception:
                        break
            finally:
                # Unregister client queue on disconnect
                try:
                    self.server.sse_queues.remove(q)  # type: ignore[attr-defined]
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
        """Run loop for GUI.
        Keeps the coroutine alive while background threads serve HTTP and events.
        """
        # Simple cooperative sleep loop; shutdown() will flip _running to False
        while self._running:
            try:
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception:
                # Do not crash the loop on minor errors
                pass

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

        # Stop filesystem watcher
        try:
            if self._observer:
                self._observer.stop()
                self._observer.join(timeout=2)
        except Exception:
            pass
        finally:
            self._observer = None

        # Stop background asyncio loop
        try:
            if self.loop:
                self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception:
            pass
        finally:
            try:
                if self._loop_thread:
                    self._loop_thread.join(timeout=3)
            except Exception:
                pass
            self.loop = None
            self._loop_thread = None

        # Flip running flag so run() exits
        self._running = False

    def _build_index_html(self) -> str:
        """Construct inline HTML for the GUI.
        Includes:
        - Minimal chat input and output area
        - SSE connection to /events for hot-reload
        - Buttons to list plugins and send messages
        """
        # NOTE: Keep dependencies minimal; no external assets for portability.
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Sakana Desktop Assistant</title>
<style>
  body {{ font-family: system-ui, Arial, sans-serif; margin: 0; background: #0b1f2a; color: #e6f1ff; }}
  header {{ padding: 16px 20px; background: #0f2b3a; border-bottom: 1px solid #163a4d; }}
  h1 {{ margin: 0; font-size: 18px; }}
  main {{ padding: 16px 20px; }}
  .row {{ display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }}
  input[type=text] {{ flex: 1; padding: 10px; border-radius: 6px; border: 1px solid #28536b; background: #0c2230; color: #e6f1ff; }}
  button {{ padding: 10px 14px; border-radius: 6px; border: 1px solid #28536b; background: #133349; color: #e6f1ff; cursor: pointer; }}
  button.active {{ background: #1a4a65; }}
  button:hover {{ background: #16425a; }}
  pre {{ background: #0c2230; padding: 12px; border-radius: 8px; border: 1px solid #28536b; white-space: pre-wrap; }}
  .status {{ font-size: 12px; opacity: 0.8; }}
</style>
</head>
<body>
<header>
  <h1>🐟 Sakana Desktop Assistant</h1>
  <div class="status">GUI connected to http://{self.host}:{self.port}</div>
</header>
<main>
  <div class="row">
    <input id="chat-input" type="text" placeholder="Type a message…" />
    <button id="send-btn">Send</button>
  </div>
  <div id="chat-log"></div>
  <nav>
    <button id="tab-chat" class="active">Chat</button>
    <button id="tab-playwright">Playwright</button>
  </nav>
  <div id="content-chat"></div>
  <div id="content-playwright" style="display:none;">
    <iframe id="playwright-frame" src="/mcp/playwright" style="width:100%; height:70vh; border:none;"></iframe>
  </div>
</main>
<script>
  document.getElementById('tab-chat').onclick = () => {{
    document.getElementById('content-chat').style.display = '';
    document.getElementById('content-playwright').style.display = 'none';
    document.getElementById('tab-chat').classList.add('active');
    document.getElementById('tab-playwright').classList.remove('active');
  }};
  document.getElementById('tab-playwright').onclick = () => {{
    document.getElementById('content-chat').style.display = 'none';
    document.getElementById('content-playwright').style.display = '';
    document.getElementById('tab-chat').classList.remove('active');
    document.getElementById('tab-playwright').classList.add('active');
  }};

// --- Simple helper for JSON POST ---
async function postJSON(path, payload) {{
  const res = await fetch(path, {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(payload) }});
  return await res.json();
}}

// --- Handle Send ---
const msg = document.getElementById('msg');
const out = document.getElementById('out');
const send = document.getElementById('send');
send.addEventListener('click', async () => {{
  const text = msg.value.trim();
  if (!text) return;
  out.textContent = 'Thinking...';
  try {{
    const r = await postJSON('/api/message', {{ input: text }});
    out.textContent = JSON.stringify(r, null, 2);
  }} catch (e) {{
    out.textContent = 'Error: ' + e;
  }}
}});

// --- List Plugins ---
const btnPlugins = document.getElementById('plugins');
btnPlugins.addEventListener('click', async () => {{
  out.textContent = 'Loading plugins...';
  try {{
    const r = await fetch('/api/plugins');
    const j = await r.json();
    out.textContent = JSON.stringify(j, null, 2);
  }} catch (e) {{
    out.textContent = 'Error: ' + e;
  }}
}});

// --- SSE Reload ---
try {{
  const es = new EventSource('/events');
  es.addEventListener('reload', () => {{ location.reload(); }});
}} catch (e) {{ /* SSE may not be available; ignore */ }}
</script>
</body>
</html>
"""