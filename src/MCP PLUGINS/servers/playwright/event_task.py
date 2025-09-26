# -*- coding: utf-8 -*-
"""
event_task.py
Event broadcasting server and UI handler extracted from agent.py for reuse.
Provides: EventServer, UIHandler, start_ui_server, and helper tasks.
Clear comments for easy debug; naming aligned with other agents.
"""
import base64
import json
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from threading import Thread, Lock
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Allow running as a standalone module or as part of the package
try:
    from .constants import DEFAULT_UI_HOST, DEFAULT_UI_PORT  # type: ignore
except Exception:
    # Fallback for running this file or importing as a sibling module
    from constants import DEFAULT_UI_HOST, DEFAULT_UI_PORT  # type: ignore

# ---------- EventServer ----------

@dataclass
class Event:
    type: str
    value: Any


class EventServer:
    """Minimal event broadcast server with SSE endpoint and image cache.

    Compatible with legacy agent expectations by exposing simple state fields.
    """

    def __init__(self):
        # Last N events for late subscribers
        self._buffer: List[Event] = []
        self._max_buffer = 200
        self._clients: List = []  # list of wfile objects
        self._latest_preview_png_b64: Optional[str] = None
        self._lock = Lock()
        # --- Compatibility state (used by legacy agent code) ---
        self.browser_open_last_state: Optional[bool] = None
        self.screenshot_skip_last_log_ts: float = 0.0
        self.last_image_ts: float = 0.0
        self.last_source: Optional[str] = None
        self.last_open_signal_ts: float = 0.0

    def broadcast(self, type_: str, value: Any) -> None:
        """Broadcast an event to all connected clients and buffer it (synchronous).
        Uses a simple lock for thread-safety.
        """
        # Normalize text-centric event values to strings to avoid "[object Object]" in UI
        text_types = {"log", "tool", "think", "error", "url", "replace_last"}
        try:
            value_out = value
            if type_ in text_types and not isinstance(value_out, str):
                if isinstance(value_out, (dict, list)):
                    value_out = json.dumps(value_out, ensure_ascii=False)
                else:
                    value_out = str(value_out)
        except Exception:
            value_out = str(value)

        evt = Event(type=type_, value=value_out)
        with self._lock:
            self._buffer.append(evt)
            if len(self._buffer) > self._max_buffer:
                self._buffer = self._buffer[-self._max_buffer :]
            # write to all clients; drop broken ones
            stale = []
            payload = f"data: {json.dumps({'type': type_, 'value': value_out}, ensure_ascii=False)}\n\n".encode("utf-8")
            for w in list(self._clients):
                try:
                    w.write(payload)
                    w.flush()
                except Exception:
                    stale.append(w)
            # cleanup stale
            for s in stale:
                try:
                    self._clients.remove(s)
                except ValueError:
                    pass

    def set_preview_png(self, png_b64: str) -> None:
        self._latest_preview_png_b64 = png_b64

    def get_preview_png(self) -> Optional[str]:
        return self._latest_preview_png_b64

    def set_channel_image(self, img_bytes: bytes, mime: str = "image/png", channel: str = "default") -> None:
        """Compatibility shim for legacy agent: store preview from raw bytes."""
        try:
            self._latest_preview_png_b64 = base64.b64encode(img_bytes).decode("ascii")
        except Exception:
            # Keep previous preview if conversion fails
            pass

    def _register_client(self, wfile) -> None:
        self._clients.append(wfile)


# ---------- UI Handler ----------

class UIHandler(BaseHTTPRequestHandler):
    server_version = "MCPPlaywrightUI/1.0"

    # injected at wiring time
    event_server: EventServer = None  # type: ignore

    def _set_headers(self, code: int = 200, content_type: str = "text/html; charset=utf-8") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        # Parse the URL to ignore query strings for route matching
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            return self._serve_index()
        if path == "/events":
            return self._serve_events()
        if path == "/preview.png":
            return self._serve_preview_png()
        if path == "/health":
            # simple health check used by tooling; 200 if server alive
            self._set_headers(200, "text/plain")
            try:
                self.wfile.write(b"ok")
            except Exception:
                # Client might have closed the connection prematurely; ignore
                pass
            return
        self._set_headers(404, "text/plain")
        try:
            self.wfile.write(b"Not Found")
        except Exception:
            # Client might have closed the connection; avoid noisy stack traces
            pass

    def _serve_index(self) -> None:
        self._set_headers(200, "text/html; charset=utf-8")
        html = """
<!doctype html>
<html><head><meta charset="utf-8"/><title>MCP Live Viewer</title>
<style>
body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 0; background: #0b1020; color: #f1f5f9; }
#header { display:flex; gap:12px; align-items:center; padding: 10px 14px; background:#111827; border-bottom:1px solid #1f2937; }
.badge { font-size:12px; background:#10b981; color:#052e2b; padding:2px 6px; border-radius: 999px; }
#stream { white-space: pre-wrap; padding: 12px; line-height:1.45; }
#previewWrap { position: fixed; right: 10px; top: 56px; width: 400px; background:#0f172a; border:1px solid #1f2937; border-radius:8px; overflow:hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.35); }
#previewWrap header{ display:flex; justify-content:space-between; align-items:center; padding:6px 8px; background:#0b1220; color:#93c5fd; font-size: 12px; }
#preview { width: 100%; display:block; }
.label{ opacity:.6; margin-right:6px; }
.tool{ color:#60a5fa; }
.think{ color:#a78bfa; background:rgba(167,139,250,.08); border-left:3px solid #a78bfa; padding-left:8px; margin:6px 0; }
.err{ color:#fca5a5; }
</style>
</head>
<body>
<div id="header"><span class="badge">MCP</span><strong>Playwright Agent</strong></div>
<div id="stream"></div>
<div id="previewWrap"><header><span>Browser Preview</span><small id="url"></small></header><img id="preview" src="/preview.png"/></div>
<script>
const streamEl = document.getElementById('stream');
const urlEl = document.getElementById('url');

function append(text, cls){
  const div = document.createElement('div');
  if(cls) div.className = cls;
  try{
    if (text && typeof text === 'object') {
      div.textContent = JSON.stringify(text);
    } else {
      div.textContent = String(text || '');
    }
  }catch(_e){ div.textContent = String(text || ''); }
  streamEl.appendChild(div);
  window.scrollTo(0, document.body.scrollHeight);
}

function connect(){
  const es = new EventSource('/events');
  es.onmessage = (e) => {
    try{
      const evt = JSON.parse(e.data);
      const v = evt.value;
      const valStr = (v && typeof v === 'object') ? JSON.stringify(v) : String(v || '');
      if(evt.type === 'log') append(valStr, '');
      if(evt.type === 'tool') append('TOOL: '+valStr, 'tool');
      if(evt.type === 'think') append(valStr, 'think');
      if(evt.type === 'error') append('ERROR: '+valStr, 'err');
      if(evt.type === 'url') urlEl.textContent = valStr;
      if(evt.type === 'replace_last') {
         streamEl.lastChild && (streamEl.lastChild.textContent = valStr);
      }
    }catch(err){ console.error(err); }
  };
  es.onerror = () => setTimeout(()=>{ es.close(); connect(); }, 1500);
}

connect();
setInterval(()=>{ const img=document.getElementById('preview'); img.src='/preview.png?'+Date.now(); }, 2000);
</script>
</body></html>
"""
        try:
            self.wfile.write(html.encode("utf-8"))
        except Exception:
            # Client disconnected mid-write; ignore to avoid noisy logs
            pass

    def _serve_events(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        # register client and replay buffer
        self.event_server._register_client(self.wfile)

    def _serve_preview_png(self) -> None:
        png_b64 = self.event_server.get_preview_png()
        if not png_b64:
            self._set_headers(404, "text/plain")
            try:
                self.wfile.write(b"No preview yet")
            except Exception:
                # Client might have closed the connection; ignore
                pass
            return
        try:
            raw = base64.b64decode(png_b64)
        except Exception:
            self._set_headers(500, "text/plain")
            try:
                self.wfile.write(b"Invalid preview data")
            except Exception:
                pass
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except Exception:
            # Client disconnected while reading image; ignore
            pass


# ---------- Orchestration helpers ----------

def start_ui_server(event_server: EventServer, host: str = DEFAULT_UI_HOST, port: int = DEFAULT_UI_PORT) -> Tuple[HTTPServer, Thread]:
    """Start the lightweight UI server in a thread and return (server, thread).
    NOTE: Use ThreadingHTTPServer so long-lived SSE (/events) won't block other routes like /preview.png.
    """
    class _Handler(UIHandler):
        pass
    _Handler.event_server = event_server  # inject instance

    # Switch to ThreadingHTTPServer for concurrent handling of /events and /preview.png
    httpd = ThreadingHTTPServer((host, port), _Handler)
    t = Thread(target=httpd.serve_forever, name="mcp-ui", daemon=True)
    t.start()
    return httpd, t


async def stream_think(event_server: EventServer, text: str) -> None:
    """Emit think blocks line by line (for stream-safe rendering)."""
    for line in text.splitlines():
        event_server.broadcast("think", line)


async def update_preview(event_server: EventServer, png_b64: str, url: Optional[str] = None) -> None:
    event_server.set_preview_png(png_b64)
    if url:
        event_server.broadcast("url", url)