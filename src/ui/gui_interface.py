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
from logging.handlers import RotatingFileHandler
import threading
import os
import time
import queue
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Tuple
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import pathlib
from mimetypes import guess_type
import urllib.request
import urllib.parse
from urllib.parse import urlparse, parse_qs
import subprocess
import sys

logger = logging.getLogger(__name__)

# Data directory configuration - will be set by main.py
DATA_DIR = None
LOGS_DIR = None
SESSIONS_DIR = None
TMP_DIR = None

# MCP Tool Agent Paths - Maps tool names to their agent script paths
MCP_TOOL_AGENT_PATHS = {
    'github': 'MCP PLUGINS/servers/github/agent.py',
    'docker': 'MCP PLUGINS/servers/docker/agent.py',
    'desktop': 'MCP PLUGINS/servers/desktop/agent.py',
    'playwright': 'MCP PLUGINS/servers/playwright/agent.py',
    'context7': 'MCP PLUGINS/servers/context7/agent.py',
    'redis': 'MCP PLUGINS/servers/redis/agent.py',
    'supabase': 'MCP PLUGINS/servers/supabase/agent.py',
    'cloudflare': 'MCP PLUGINS/servers/cloudflare/agent.py',
    'travliy': 'MCP PLUGINS/servers/travliy/agent.py',
    'windows-automation': 'MCP PLUGINS/servers/windows-automation/agent.py',
}



def set_data_directories(data_dir, logs_dir, sessions_dir, tmp_dir):
    """Set the data directory paths for use by GUI components."""
    global DATA_DIR, LOGS_DIR, SESSIONS_DIR, TMP_DIR
    DATA_DIR = data_dir
    LOGS_DIR = logs_dir
    SESSIONS_DIR = sessions_dir
    TMP_DIR = tmp_dir


def setup_session_logging(session_id: str) -> logging.Logger:
    """Setup per-session logging under data/logs/sessions/"""
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
    
    # Create rotating file handler for this session
    session_log_file = session_logs_dir / f'{session_id}.log'
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


class _AssistantHTTPServer(ThreadingHTTPServer):
    """HTTP server that holds references to assistant and its event loop."""

    def __init__(self, server_address: Tuple[str, int], RequestHandlerClass, assistant, loop: asyncio.AbstractEventLoop, react_ui_enabled: bool = False, react_ui_dist_dir: Path | None = None):
        super().__init__(server_address, RequestHandlerClass)
        self.assistant = assistant
        self.loop = loop
        # React UI configuration passed from GUIInterface
        self._react_ui_enabled = react_ui_enabled
        self._react_ui_dist_dir = react_ui_dist_dir
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
        
        # --- NEW: Multi-session MCP management (supports all tools: github, docker, playwright, etc.) ---
        # Track multiple independent MCP tool sessions for easy debug
        self._mcp_sessions: Dict[str, Dict[str, Any]] = {}
        self._mcp_sessions_lock = threading.Lock()
        
        # --- LEGACY: Single session support for backward compatibility ---
        # Attach this GUI to a running Playwright EventServer for a specific session.
        # Clear comments for easy debug; enables dynamic session switching.
        self._playwright_event_host: str | None = None
        self._playwright_event_port: int | None = None
        self._playwright_session_id: str | None = None
        self._playwright_agent_proc: subprocess.Popen | None = None  # type: ignore[assignment]
        self._playwright_connected: bool = False



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

    # --- NEW: Playwright session management helpers ---
    def set_playwright_session_upstream(self, session_id: str, host: str, port: int) -> Dict[str, Any]:
        """Attach this GUI to a specific Playwright EventServer instance.
        Clear comments for easy debug; updates upstream host/port/session and broadcasts attach event.
        """
        try:
            self._playwright_session_id = str(session_id)
            self._playwright_event_host = str(host)
            self._playwright_event_port = int(port)
            self._playwright_connected = True
            
            # Setup per-session logging
            session_logger = setup_session_logging(session_id)
            session_logger.info(f"Playwright session attached: {session_id} at {host}:{port}")
            
            self.broadcast_event('playwright.session.attached', {
                'session_id': self._playwright_session_id,
                'host': self._playwright_event_host,
                'port': self._playwright_event_port,
            })
            return {
                'success': True,
                'connected': self._playwright_connected,
                'session_id': self._playwright_session_id,
                'host': self._playwright_event_host,
                'port': self._playwright_event_port,
            }
        except Exception as e:
            logger.error(f"Failed to attach Playwright session {session_id}: {e}")
            self._playwright_connected = False
            return {'success': False, 'error': f'Attach failed: {e}'}

    def get_playwright_session_status(self) -> Dict[str, Any]:
        """Return session connection and agent process status for observability."""
        try:
            # Setup session logging if we have a session ID
            session_logger = logger
            if hasattr(self, '_playwright_session_id') and self._playwright_session_id:
                session_logger = setup_session_logging(self._playwright_session_id)
            
            proc = getattr(self, '_playwright_agent_proc', None)
            running = bool(proc and (proc.poll() is None))
            
            status = {
                'connected': bool(self._playwright_connected),
                'session_id': self._playwright_session_id,
                'host': self._playwright_event_host,
                'port': self._playwright_event_port,
                'agent_pid': (proc.pid if proc else None),
                'agent_running': running,
            }
            
            session_logger.debug(f"Playwright session status check: {status}")
            return status
        except Exception as e:
            logger.error(f"Error getting Playwright session status: {e}")
            return {'connected': False, 'error': str(e)}

    def stop_playwright_session_agent(self) -> Dict[str, Any]:
        """Stop the spawned Playwright agent process and detach upstream."""
        try:
            # Setup session logging if we have a session ID
            session_logger = logger
            if hasattr(self, '_playwright_session_id') and self._playwright_session_id:
                session_logger = setup_session_logging(self._playwright_session_id)
            
            proc = getattr(self, '_playwright_agent_proc', None)
            if proc and (proc.poll() is None):
                session_logger.info(f"Stopping Playwright agent process (PID: {proc.pid})")
                try:
                    proc.terminate()
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
            # Clear state
            self._playwright_agent_proc = None
            was_session = self._playwright_session_id
            self._playwright_connected = False
            
            session_logger.info(f"Playwright session stopped: {was_session}")
            self.broadcast_event('playwright.session.detached', {
                'session_id': was_session,
            })
            # Do not clear host/port to allow UI to see last-known upstream
            return {
                'success': True,
                'stopped': True,
                'session_id': was_session,
            }
        except Exception as e:
            logger.error(f"Error stopping Playwright session: {e}")
            return {'success': False, 'error': f'Stop failed: {e}'}

    def spawn_playwright_session_agent(self, session_id: str | None = None, ui_host: str | None = None, ui_port: int | None = None, keepalive: bool = True) -> Dict[str, Any]:    
        """Spawn Playwright agent subprocess (wrapper for spawn_mcp_session_agent).
        
        BACKWARD COMPATIBILITY: Delegates to spawn_mcp_session_agent('playwright', ...).
        """
        return self.spawn_mcp_session_agent('playwright', session_id, ui_host, ui_port, keepalive)

    def stop_playwright_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """Stop Playwright agent for a specific session.
        
        NOTE: Works with any tool session (github, docker, playwright, etc.) via _mcp_sessions."""
        try:
            with self._mcp_sessions_lock:
                if session_id not in self._mcp_sessions:
                    return {'success': False, 'error': f'Session {session_id} not found'}
                
                session = self._mcp_sessions[session_id]
                proc = session.get('agent_proc')
                
                if not proc or proc.poll() is not None:
                    return {'success': False, 'error': f'Session {session_id} not running'}
                
                session_logger = setup_session_logging(session_id)
                session_logger.info(f"Stopping Playwright agent for session {session_id} (PID: {proc.pid})")
                
                try:
                    proc.terminate()
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
                
                # Update session state for easy debug
                session['agent_proc'] = None
                session['agent_pid'] = None
                session['agent_running'] = False
                session['connected'] = False
                session['status'] = 'stopped'
                
                session_logger.info(f"Stopped Playwright agent for session {session_id}")
                
                self.broadcast_event('playwright.session.stopped', {
                    'session_id': session_id,
                })
                
                return {'success': True, 'session_id': session_id}
        except Exception as e:
            logger.error(f"Failed to stop session {session_id}: {e}")
            return {'success': False, 'error': f'Stop failed: {e}'}

    def start_playwright_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """Start Playwright agent for a specific session.
        
        NOTE: Works with any tool session (github, docker, playwright, etc.) via _mcp_sessions."""
        try:
            with self._mcp_sessions_lock:
                if session_id not in self._mcp_sessions:
                    return {'success': False, 'error': f'Session {session_id} not found'}
                
                session = self._mcp_sessions[session_id]
                
                # Check if already running for easy debug
                proc = session.get('agent_proc')
                if proc and (proc.poll() is None):
                    return {'success': False, 'error': f'Session {session_id} already running'}
                
                # Update status to starting
                session['status'] = 'starting'
            
            # Use existing spawn method but track in session
            result = self.spawn_playwright_session_agent(session_id)
            
            if result.get('success'):
                with self._mcp_sessions_lock:
                    session = self._mcp_sessions[session_id]
                    session['agent_proc'] = self._playwright_agent_proc
                    session['agent_pid'] = result.get('pid')
                    session['agent_running'] = True
                    session['status'] = 'running'
                    
                    session_logger = setup_session_logging(session_id)
                    session_logger.info(f"Started Playwright agent for session {session_id}")
                    
                    self.broadcast_event('playwright.session.started', {
                        'session_id': session_id,
                    })
            else:
                with self._mcp_sessions_lock:
                    session = self._mcp_sessions[session_id]
                    session['status'] = 'stopped'
            
            return result
        except Exception as e:
            logger.error(f"Failed to start session {session_id}: {e}")
            with self._mcp_sessions_lock:
                if session_id in self._mcp_sessions:
                    self._mcp_sessions[session_id]['status'] = 'stopped'
            return {'success': False, 'error': f'Start failed: {e}'}

    def delete_playwright_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """Delete a specific Playwright session (stops agent if running).
        
        NOTE: Works with any tool session (github, docker, playwright, etc.) via _mcp_sessions."""
        try:
            # First stop the session if running
            stop_result = self.stop_playwright_session_by_id(session_id)
            
            with self._mcp_sessions_lock:
                if session_id not in self._mcp_sessions:
                    return {'success': False, 'error': f'Session {session_id} not found'}
                
                del self._mcp_sessions[session_id]
                
                session_logger = setup_session_logging(session_id)
                session_logger.info(f"Deleted Playwright session: {session_id}")
                
                self.broadcast_event('playwright.session.deleted', {
                    'session_id': session_id,
                })
                
                return {'success': True, 'session_id': session_id}
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return {'success': False, 'error': f'Delete failed: {e}'}

    def set_playwright_session_upstream_by_id(self, session_id: str, host: str, port: int) -> Dict[str, Any]:
        """Set upstream connection for a specific session.
        
        NOTE: Works with any tool session (github, docker, playwright, etc.) via _mcp_sessions."""
        try:
            with self._mcp_sessions_lock:
                if session_id not in self._mcp_sessions:
                    return {'success': False, 'error': f'Session {session_id} not found'}
                
                session = self._mcp_sessions[session_id]
                session['host'] = str(host)
                session['port'] = int(port)
                session['connected'] = True
                
                session_logger = setup_session_logging(session_id)
                session_logger.info(f"Set upstream for session {session_id}: {host}:{port}")
                
                self.broadcast_event('playwright.session.upstream_set', {
                    'session_id': session_id,
                    'host': host,
                    'port': port,
                })
                
                return {'success': True, 'session_id': session_id, 'host': host, 'port': port}
        except Exception as e:
            logger.error(f"Failed to set upstream for session {session_id}: {e}")
            return {'success': False, 'error': f'Set upstream failed: {e}'}

    def get_all_playwright_sessions(self) -> Dict[str, Any]:
        """Get status of all Playwright sessions (wrapper for get_all_mcp_sessions).
        
        BACKWARD COMPATIBILITY: Delegates to get_all_mcp_sessions(tool_filter='playwright').
        """
        return self.get_all_mcp_sessions(tool_filter='playwright')

    def delete_playwright_session(self, session_id: str) -> Dict[str, Any]:
        """Delete a Playwright session (stops agent if running)."""
        try:
            # First stop the session if running
            stop_result = self.stop_playwright_session_by_id(session_id)
            
            with self._mcp_sessions_lock:
                if session_id not in self._mcp_sessions:
                    return {'success': False, 'error': f'Session {session_id} not found'}
                
                del self._mcp_sessions[session_id]
                
                session_logger = setup_session_logging(session_id)
                session_logger.info(f"Deleted Playwright session: {session_id}")
                
                self.broadcast_event('playwright.session.deleted', {
                    'session_id': session_id,
                })
                
                return {'success': True, 'session_id': session_id}
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return {'success': False, 'error': f'Delete failed: {e}'}

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

    # --- NEW: Suppress benign client disconnect errors at server level ---
    def handle_error(self, request, client_address):
        try:
            exc_type, exc_value, _ = sys.exc_info()
            if exc_type in (ConnectionAbortedError, BrokenPipeError):
                try:
                    logger.debug("GUI HTTP: suppressed client disconnect from %s: %s", client_address, exc_value)
                except Exception:
                    pass
                return
        except Exception:
            pass
        # Fallback to default behavior
        try:
            return super().handle_error(request, client_address)
        except Exception:
            pass

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
        import logging
        logging.error(f"[DEBUG] *** do_GET called for path: {self.path} ***")
        # --- NEW: Serve React SPA (static assets + index.html fallback) when enabled ---
        try:
            srv = getattr(self, 'server', None)
            react_enabled = bool(getattr(srv, '_react_ui_enabled', False))
            dist_dir = getattr(srv, '_react_ui_dist_dir', None)
        except Exception:
            react_enabled = False
            dist_dir = None
        # Use path without query string to ensure root routing works reliably
        # e.g., "/?foo=bar" should be treated as "/"
        # IMPORTANT: avoid referencing 'urllib' here because later in-function
        # imports like `import urllib.request` make 'urllib' a local symbol,
        # causing UnboundLocalError if used before those imports.
        # Parse the path manually to strip the query string without imports.
        clean_path = (self.path.split("?", 1)[0] if self.path else "/")
        if react_enabled and dist_dir:
            try:
                dist_root = pathlib.Path(dist_dir).resolve()
                req_path = clean_path or '/'
                # Allow API and special endpoints to bypass SPA handling
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
                    # Try to serve static asset from dist
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
                    # SPA fallback: serve index.html for client-side routing
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
                # If anything goes wrong, continue to legacy inline handler
                pass
        # FINAL SPA FALLBACK when enabled: always serve index.html for non-API paths
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
        # Legacy inline UI only when React is disabled
        if not react_enabled and clean_path == "/":
            body = (self.INDEX_HTML or "<html><body><h1>GUI</h1><p>Initialization fallback.</p></body></html>").encode("utf-8")  # Safe fallback if INDEX_HTML is None
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except Exception:
                pass
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
                            except (ConnectionAbortedError, BrokenPipeError):
                                # Client disconnected; stop streaming to avoid noisy server errors
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
                            # Client disconnected; stop streaming loop cleanly
                            break
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
                # Resolve target host/port using session-scoped upstream when available; fallback to legacy env
                session_host = getattr(self.server, '_playwright_event_host', None) or os.getenv("MCP_UI_HOST", "127.0.0.1")
                try:
                    session_port = int(getattr(self.server, '_playwright_event_port', None) or int(os.getenv("MCP_UI_PORT", "8787")))
                except Exception:
                    session_port = 8787
                # Stream from Playwright server and pipe through to client
                try:
                    import http.client
                    conn = http.client.HTTPConnection(session_host, session_port, timeout=10)
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
                            except (ConnectionAbortedError, BrokenPipeError):
                                # Client disconnected; stop forwarding
                                break
                            except Exception:
                                # Ignore non-fatal flush errors
                                pass
                        except (ConnectionAbortedError, BrokenPipeError):
                            break
                        except Exception:
                            break
                except Exception:
                    # Upstream proxy stream error; ignore and proceed to cleanup
                    pass
                finally:
                    # Always close upstream response/connection
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
                # Resolve target host/port using session-scoped upstream when available; fallback to legacy env
                session_host = getattr(self.server, '_playwright_event_host', None) or os.getenv("MCP_UI_HOST", "127.0.0.1")
                try:
                    session_port = int(getattr(self.server, '_playwright_event_port', None) or int(os.getenv("MCP_UI_PORT", "8787")))
                except Exception:
                    session_port = 8787
                # --- DEPRECATION NOTICE: legacy env-based upstream ---
                try:
                    env_used = ('MCP_UI_HOST' in os.environ) or ('MCP_UI_PORT' in os.environ)
                    if env_used and not getattr(self.server, '_mcp_playwright_legacy_env_warned', False):  # type: ignore[attr-defined]
                        try:
                            setattr(self.server, '_mcp_playwright_legacy_env_warned', True)  # type: ignore[attr-defined]
                        except Exception:
                            pass
                        try:
                            sid = getattr(self.server, '_playwright_session_id', None)  # type: ignore[attr-defined]
                            self.broadcast_event('playwright.session.log', {
                                'session_id': sid,
                                'line': '[DEPRECATED] Legacy /mcp/playwright/* using MCP_UI_HOST/MCP_UI_PORT. Migrate to /api/playwright/session/attach and /mcp/playwright/session/*.'
                            })
                        except Exception:
                            pass
                        try:
                            logger.warning(
                                "DEPRECATED: Environment-based legacy Playwright proxy in use (MCP_UI_HOST=%s, MCP_UI_PORT=%s). Use session-scoped routes.",
                                os.getenv("MCP_UI_HOST"), os.getenv("MCP_UI_PORT"))
                        except Exception:
                            pass
                except Exception:
                    pass
                # Preserve query string
                upstream_path = "/events.json"
                try:
                    if urlparse:
                        upstream_path += ("?" + urlparse(self.path).query)
                except Exception:
                    pass
                url = f"http://{session_host}:{session_port}{upstream_path}"
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
                # Resolve target host/port using session-scoped upstream when available; fallback to legacy env
                session_host = getattr(self.server, '_playwright_event_host', None) or os.getenv("MCP_UI_HOST", "127.0.0.1")
                try:
                    session_port = int(getattr(self.server, '_playwright_event_port', None) or int(os.getenv("MCP_UI_PORT", "8787")))
                except Exception:
                    session_port = 8787
                # --- DEPRECATION NOTICE: legacy env-based upstream ---
                try:
                    env_used = ('MCP_UI_HOST' in os.environ) or ('MCP_UI_PORT' in os.environ)
                    if env_used and not getattr(self.server, '_mcp_playwright_legacy_env_warned', False):  # type: ignore[attr-defined]
                        try:
                            setattr(self.server, '_mcp_playwright_legacy_env_warned', True)  # type: ignore[attr-defined]
                        except Exception:
                            pass
                        try:
                            sid = getattr(self.server, '_playwright_session_id', None)  # type: ignore[attr-defined]
                            self.broadcast_event('playwright.session.log', {
                                'session_id': sid,
                                'line': '[DEPRECATED] Legacy /mcp/playwright/* using MCP_UI_HOST/MCP_UI_PORT. Migrate to /api/playwright/session/attach and /mcp/playwright/session/*.'
                            })
                        except Exception:
                            pass
                        try:
                            logger.warning(
                                "DEPRECATED: Environment-based legacy Playwright proxy in use (MCP_UI_HOST=%s, MCP_UI_PORT=%s). Use session-scoped routes.",
                                os.getenv("MCP_UI_HOST"), os.getenv("MCP_UI_PORT"))
                        except Exception:
                            pass
                except Exception:
                    pass
                url = f"http://{session_host}:{session_port}/health"
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
                # --- DEPRECATION NOTICE: legacy env-based upstream ---
                try:
                    env_used = ('MCP_UI_HOST' in os.environ) or ('MCP_UI_PORT' in os.environ)
                    if env_used and not getattr(self.server, '_mcp_playwright_legacy_env_warned', False):  # type: ignore[attr-defined]
                        try:
                            setattr(self.server, '_mcp_playwright_legacy_env_warned', True)  # type: ignore[attr-defined]
                        except Exception:
                            pass
                        try:
                            sid = getattr(self.server, '_playwright_session_id', None)  # type: ignore[attr-defined]
                            self.broadcast_event('playwright.session.log', {
                                'session_id': sid,
                                'line': '[DEPRECATED] Legacy /mcp/playwright/* using MCP_UI_HOST/MCP_UI_PORT. Migrate to /api/playwright/session/attach and /mcp/playwright/session/*.'
                            })
                        except Exception:
                            pass
                        try:
                            logger.warning(
                                "DEPRECATED: Environment-based legacy Playwright proxy in use (MCP_UI_HOST=%s, MCP_UI_PORT=%s). Use session-scoped routes.",
                                os.getenv("MCP_UI_HOST"), os.getenv("MCP_UI_PORT"))
                        except Exception:
                            pass
                except Exception:
                    pass
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

        # --- NEW: Session-scoped Playwright proxy routes under /mcp/playwright/session ---
        # These routes use session-specific host/port from _AssistantHTTPServer state instead of env vars.
        # Clear comments for easy debug; enables session switching without env changes.
        if self.path == "/mcp/playwright/session/sse":
            try:
                # Prepare response headers for SSE
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                # Use session-scoped host/port with fallback to env
                session_host = getattr(self.server, '_playwright_event_host', None) or os.getenv("MCP_UI_HOST", "127.0.0.1")
                session_port = getattr(self.server, '_playwright_event_port', None) or int(os.getenv("MCP_UI_PORT", "8787"))
                # Stream from session Playwright server and pipe through to client
                try:
                    import http.client
                    conn = http.client.HTTPConnection(session_host, session_port, timeout=10)
                    conn.request("GET", "/events", headers={
                        "Accept": "text/event-stream",
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                    })
                    resp = conn.getresponse()
                    if resp.status != 200:
                        try:
                            self.wfile.write(f"data: Session proxy upstream error HTTP {resp.status}\n\n".encode("utf-8"))
                            self.wfile.flush()
                        except Exception:
                            pass
                        return
                    # Write an initial connected comment with session ID
                    session_id = getattr(self.server, '_playwright_session_id', 'unknown')
                    try:
                        self.wfile.write(f":session-proxy-connected session_id={session_id}\n\n".encode("utf-8"))
                        self.wfile.flush()
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
                            except (ConnectionAbortedError, BrokenPipeError):
                                # Client disconnected; stop forwarding
                                break
                            except Exception:
                                # Ignore non-fatal flush errors
                                pass
                        except (ConnectionAbortedError, BrokenPipeError):
                            break
                        except Exception:
                            break
                except Exception:
                    # Upstream proxy stream error; ignore and proceed to cleanup
                    pass
                finally:
                    # Always close upstream response/connection
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
                # On header write failure, just return
                return

        if self.path.startswith("/mcp/playwright/session/events.json"):
            try:
                # Proxy JSON polling to session Playwright EventServer with backoff
                try:
                    from urllib.parse import urlparse
                    import urllib.request, urllib.error
                except Exception:
                    urlparse = None  # type: ignore
                session_host = getattr(self.server, '_playwright_event_host', None) or os.getenv("MCP_UI_HOST", "127.0.0.1")
                session_port = getattr(self.server, '_playwright_event_port', None) or int(os.getenv("MCP_UI_PORT", "8787"))
                # Preserve query string
                upstream_path = "/events.json"
                try:
                    if urlparse:
                        upstream_path += ("?" + urlparse(self.path).query)
                except Exception:
                    pass
                url = f"http://{session_host}:{session_port}{upstream_path}"
                try:
                    req = urllib.request.Request(url, headers={"Accept": "application/json"})
                    # Use the same retry/backoff strategy for resilience
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
                    # Forward upstream HTTP error code and body
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
                        self._json(502, {"error": f"Session upstream failed: {e}"})
                    except Exception:
                        pass
                    return
            except Exception as e:
                self._json(500, {"error": f"Session proxy error: {e}"})
            return

        if self.path.startswith("/mcp/playwright/session/preview.png"):
            try:
                # Proxy latest preview PNG from session Playwright server
                import urllib.request, urllib.error
                from urllib.parse import urlparse
                session_host = getattr(self.server, '_playwright_event_host', None) or os.getenv("MCP_UI_HOST", "127.0.0.1")
                session_port = getattr(self.server, '_playwright_event_port', None) or int(os.getenv("MCP_UI_PORT", "8787"))
                # Preserve original query string from client request
                parsed = urlparse(self.path)
                upstream_path = "/preview.png"
                if parsed.query:
                    upstream_path += ("?" + parsed.query)
                url = f"http://{session_host}:{session_port}{upstream_path}"
                try:
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
                    # Forward upstream HTTP error code and body (e.g., 404)
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
                        self._json(502, {"error": f"Session upstream failed: {e}"})
                    except Exception:
                        pass
                    return
            except Exception as e:
                try:
                    self._json(502, {"error": f"Session proxy error: {e}"})
                except Exception:
                    pass
                return

        if self.path == "/mcp/playwright/session/health":
            try:
                import urllib.request, urllib.error
                session_host = getattr(self.server, '_playwright_event_host', None) or os.getenv("MCP_UI_HOST", "127.0.0.1")
                session_port = getattr(self.server, '_playwright_event_port', None) or int(os.getenv("MCP_UI_PORT", "8787"))
                url = f"http://{session_host}:{session_port}/health"
                t0 = time.time()
                try:
                    req = urllib.request.Request(url, headers={"Accept": "text/plain, application/json;q=0.9, */*;q=0.8"})
                    with self._fetch_with_backoff(req, timeout=1.5, attempts=3, base_delay=0.2) as r:
                        _ = r.read()  # upstream usually returns "ok"; content is not needed
                        latency_ms = int(max(0, (time.time() - t0) * 1000))
                        session_id = getattr(self.server, '_playwright_session_id', None)
                        self._json(200, {
                            "available": True, 
                            "latency_ms": latency_ms, 
                            "session_id": session_id,
                            "host": session_host,
                            "port": session_port,
                        })
                        return
                except urllib.error.HTTPError as e:
                    # Forward upstream HTTP error as unavailable with same status code
                    latency_ms = int(max(0, (time.time() - t0) * 1000))
                    try:
                        err_body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
                    except Exception:
                        err_body = ""
                    session_id = getattr(self.server, '_playwright_session_id', None)
                    self._json(getattr(e, "code", 502), {
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
                    session_id = getattr(self.server, '_playwright_session_id', None)
                    self._json(502, {
                        "available": False, 
                        "latency_ms": latency_ms, 
                        "error": str(e),
                        "session_id": session_id,
                        "host": session_host,
                        "port": session_port,
                    })
                    return
            except Exception as e:
                self._json(500, {"available": False, "error": f"Session proxy error: {e}"})
                return

        # --- NEW: Session status endpoint for UI observability ---
        if self.path == "/api/playwright/session/status":
            try:
                status = self.server.get_playwright_session_status()  # type: ignore[attr-defined]
                self._json(200, status)
            except Exception as e:
                self._json(500, {"error": f"Status check failed: {e}"})
            return

        # --- NEW: Multi-session API endpoints ---
        if self.path == "/api/sessions":
            try:
                sessions_result = self.server.get_all_playwright_sessions()  # type: ignore[attr-defined]
                # Extract sessions array from the result
                if isinstance(sessions_result, dict) and sessions_result.get('success') and 'sessions' in sessions_result:
                    sessions = sessions_result['sessions']
                else:
                    sessions = []
                    if isinstance(sessions_result, dict) and 'error' in sessions_result:
                        logger.error(f"Failed to get sessions: {sessions_result['error']}")
                self._json(200, {"sessions": sessions})
            except Exception as e:
                # Return empty sessions array on error to maintain frontend compatibility
                logger.error(f"Exception getting sessions: {e}")
                self._json(200, {"sessions": [], "error": f"Failed to get sessions: {e}"})
            return

        # Session-specific status endpoint
        if self.path.startswith("/api/sessions/") and self.path.endswith("/status"):
            try:
                session_id = self.path.split("/")[3]  # Extract session_id from path
                status = self.server.get_playwright_session_status_by_id(session_id)  # type: ignore[attr-defined]
                self._json(200, status)
            except Exception as e:
                self._json(500, {"error": f"Status check failed: {e}"})
            return

        # --- Frontend compatibility endpoints ---
        if self.path.startswith("/api/playwright/session/") and self.path.endswith("/status"):
            # Frontend compatibility: /api/playwright/session/{session_id}/status
            try:
                session_id = self.path.split("/")[4]  # Extract session_id from path
                status = self.server.get_playwright_session_status_by_id(session_id)  # type: ignore[attr-defined]
                self._json(200, status)
            except Exception as e:
                self._json(500, {"error": f"Status check failed: {e}"})
            return

        # --- NEW: Session-specific MCP Playwright proxy endpoints ---
        if self.path.startswith("/mcp/playwright/session/"):
            # Extract session_id from path: /mcp/playwright/session/{session_id}/...
            path_parts = self.path.split("/")
            if len(path_parts) >= 5:
                session_id = path_parts[4]
                remaining_path = "/" + "/".join(path_parts[5:]) if len(path_parts) > 5 else "/"
                print(f"[DEBUG] Session path: {self.path}, session_id: {session_id}, remaining_path: {remaining_path}")
                
                # Guard: if session_id looks like a static directory (e.g., 'public'),
                # serve from the Playwright public assets directly and bypass session lookup.
                static_dirs = {"public", "assets", "static", "css", "js", "images", "img"}
                if session_id in static_dirs:
                    # Use module-level imports to avoid local shadowing
                    public_dir = pathlib.Path(__file__).parent.parent / "MCP PLUGINS" / "servers" / "playwright" / "public"
                    logging.error(f"[DEBUG] Static-dir session_id '{session_id}' detected; serving static asset: remaining_path={remaining_path}")
                    normalized = remaining_path.lstrip("/")
                    if normalized.startswith("public/"):
                        normalized = normalized[len("public/"):]
                    file_path = public_dir / normalized
                    if file_path.is_file():
                        ctype = guess_type(str(file_path))[0] or "application/octet-stream"
                        data = file_path.read_bytes()
                        self.send_response(200)
                        self.send_header("Content-Type", ctype)
                        self.send_header("Content-Length", str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)
                        return
                    else:
                        # SPA fallback only for non-JS/CSS assets
                        if not normalized.endswith(".js") and not normalized.endswith(".css"):
                            index_path = public_dir / "index.html"
                            if index_path.is_file():
                                data = index_path.read_bytes()
                                self.send_response(200)
                                self.send_header("Content-Type", "text/html; charset=utf-8")
                                self.send_header("Content-Length", str(len(data)))
                                self.end_headers()
                                self.wfile.write(data)
                                return
                        self.send_error(404, f"File not found: /{normalized}")
                        return

                # Get session-specific upstream configuration
                try:
                    sessions_result = self.server.get_all_playwright_sessions()  # type: ignore[attr-defined]
                    if not sessions_result.get('success', False):
                        self._json(500, {"error": f"Failed to get sessions: {sessions_result.get('error', 'Unknown error')}"})
                        return
                    
                    sessions = sessions_result.get('sessions', [])
                    session = next((s for s in sessions if s["session_id"] == session_id), None)
                    
                    if not session or session["status"] != "running":
                        self._json(404, {"error": f"Session {session_id} not found or not running"})
                        return
                    
                    session_host = session.get("host", "127.0.0.1")
                    session_port = session.get("port", 8787)
                    
                    # Proxy the request to the session-specific Playwright server
                    if remaining_path == "/" or remaining_path == "/index.html":
                        remaining_path = "/index.html"
                    
                    # Handle static files and proxy requests
                    if remaining_path.startswith("/events"):
                        # Proxy SSE events
                        try:
                            self.send_response(200)
                            self.send_header("Content-Type", "text/event-stream")
                            self.send_header("Cache-Control", "no-cache")
                            self.send_header("Connection", "keep-alive")
                            self.end_headers()
                            
                            import http.client
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
                                        self.wfile.write(chunk)
                                        self.wfile.flush()
                                    except (ConnectionAbortedError, BrokenPipeError):
                                        break
                                    except Exception:
                                        break
                            
                            resp.close()
                            conn.close()
                        except Exception:
                            pass
                        return
                    
                    elif remaining_path.endswith(".json") or remaining_path.startswith("/preview.png") or remaining_path.startswith("/health"):
                        # Proxy JSON/PNG/health requests
                        try:
                            import urllib.request, urllib.error
                            from urllib.parse import urlparse
                            
                            # Preserve query string
                            upstream_path = remaining_path
                            try:
                                parsed = urlparse(self.path)
                                if parsed.query:
                                    upstream_path += ("?" + parsed.query)
                            except Exception:
                                pass
                            
                            url = f"http://{session_host}:{session_port}{upstream_path}"
                            req = urllib.request.Request(url)
                            
                            with self._fetch_with_backoff(req, timeout=2.5, attempts=4, base_delay=0.25) as r:
                                body = r.read()
                                ctype = r.headers.get("Content-Type", "application/octet-stream")
                                status = getattr(r, "status", 200)
                                self.send_response(status)
                                self.send_header("Content-Type", ctype)
                                self.send_header("Cache-Control", "no-store")
                                self.send_header("Content-Length", str(len(body)))
                                self.end_headers()
                                self.wfile.write(body)
                            return
                        except Exception as e:
                            self._json(502, {"error": f"Session proxy failed: {e}"})
                            return
                    
                    else:
                        # Serve static files from public directory
                        public_dir = pathlib.Path(__file__).parent.parent / "MCP PLUGINS" / "servers" / "playwright" / "public"
                        logging.error(f"[STATIC FILE HANDLER] Serving static file, original remaining_path: {remaining_path}")
                        print(f"[STATIC FILE HANDLER] Serving static file, original remaining_path: {remaining_path}")
                        
                        # Normalize any /public/* path when serving from session context
                        # Example: /mcp/playwright/session/<id>/public/app.js -> /mcp/playwright/session/<id>/app.js
                        normalized = remaining_path.lstrip("/")
                        if normalized.startswith("public/"):
                            remaining_path = "/" + normalized[len("public/"):]
                            logging.error(f"[DEBUG] Rewrote /public/* to {remaining_path} for session {session_id}")
                        
                        file_path = public_dir / remaining_path.lstrip("/")
                        logging.error(f"[DEBUG] Final file_path: {file_path}, exists: {file_path.is_file()}")
                        
                        # Special handling for app.js - ensure it's served with correct content type
                        if remaining_path.lstrip("/") == "app.js":
                            app_js_path = public_dir / "app.js"
                            logging.error(f"[DEBUG] Handling app.js, path: {app_js_path}, exists: {app_js_path.is_file()}")
                            if app_js_path.is_file():
                                data = app_js_path.read_bytes()
                                self.send_response(200)
                                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                                self.send_header("Content-Length", str(len(data)))
                                self.end_headers()
                                self.wfile.write(data)
                                logging.error(f"[DEBUG] Successfully served app.js for session {session_id}")
                                return
                            else:
                                # If app.js doesn't exist, return 404 instead of fallback
                                logging.error(f"[DEBUG] app.js not found at {app_js_path}")
                                self.send_error(404, "app.js not found")
                                return
                        
                        if file_path.is_file():
                            ctype = guess_type(str(file_path))[0] or "application/octet-stream"
                            data = file_path.read_bytes()
                            self.send_response(200)
                            self.send_header("Content-Type", ctype)
                            self.send_header("Content-Length", str(len(data)))
                            self.end_headers()
                            self.wfile.write(data)
                            return
                        else:
                            # Only fallback to index.html for non-JS files (SPA routing)
                            if not remaining_path.endswith(".js") and not remaining_path.endswith(".css"):
                                index_path = public_dir / "index.html"
                                if index_path.is_file():
                                    data = index_path.read_bytes()
                                    self.send_response(200)
                                    self.send_header("Content-Type", "text/html; charset=utf-8")
                                    self.send_header("Content-Length", str(len(data)))
                                    self.end_headers()
                                    self.wfile.write(data)
                                    return
                            else:
                                # For JS/CSS files, return 404 instead of fallback
                                self.send_error(404, f"File not found: {remaining_path}")
                                return
                
                except Exception as e:
                    self._json(500, {"error": f"Session proxy error: {e}"})
                    return
            
            self.send_error(404)
            return

        # --- Frontend iframe source compatibility ---
        # Handle /mcp/playwright/{session_id} -> redirect to /mcp/playwright/session/{session_id}
        # But exclude static files (with extensions) and static directories from this redirect
        if self.path.startswith("/mcp/playwright/") and not self.path.startswith("/mcp/playwright/session/"):
            # Extract session_id from path like /mcp/playwright/{session_id}
            path_parts = self.path.split("/")
            if len(path_parts) >= 4 and path_parts[3]:  # /mcp/playwright/{session_id}
                session_id = path_parts[3]
                # Don't redirect if this looks like a static file (has an extension) or static directory
                static_dirs = {"public", "assets", "static", "css", "js", "images", "img"}
                if "." not in session_id and session_id not in static_dirs:
                    # Redirect to the correct session-specific path
                    redirect_path = f"/mcp/playwright/session/{session_id}"
                    self.send_response(302)
                    self.send_header("Location", redirect_path)
                    self.end_headers()
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
                # No JavaScript rewriting needed - app.js already has correct paths
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

        if self.path == "/api/playwright/session/start":
            try:
                res = self.server.start_playwright_session_agent()  # type: ignore[attr-defined]
                self._json(200, res)
            except Exception as e:
                self._json(500, {"success": False, "error": f"Spawn failed: {e}"})
            return

        if self.path == "/api/playwright/session/stop":
            try:
                res = self.server.stop_playwright_session_agent()  # type: ignore[attr-defined]
                self._json(200, res)
            except Exception as e:
                self._json(500, {"success": False, "error": f"Stop failed: {e}"})
            return

        # --- NEW: Multi-session management endpoints ---
        if self.path == "/api/sessions":
            # Create new session
            try:
                name = (data.get("name") or "").strip()
                model = (data.get("model") or "gpt-4").strip()
                tools = data.get("tools") or ["playwright"]
                
                if not name:
                    self._json(400, {"success": False, "error": "'name' is required"})
                    return
                
                session = self.server.create_playwright_session(name, model, tools)  # type: ignore[attr-defined]
                self._json(200, {"success": True, "session": session})
            except Exception as e:
                self._json(500, {"success": False, "error": f"Failed to create session: {e}"})
            return

        # Session-specific operations
        if self.path.startswith("/api/sessions/"):
            path_parts = self.path.split("/")
            if len(path_parts) >= 4:
                session_id = path_parts[3]
                operation = path_parts[4] if len(path_parts) > 4 else None
                
                if operation == "start":
                    try:
                        ui_host = (data.get("ui_host") or "").strip() or None
                        ui_port = data.get("ui_port")
                        keepalive = data.get("keepalive", True)
                        
                        if ui_port is not None:
                            try:
                                ui_port = int(ui_port)
                            except Exception:
                                self._json(400, {"success": False, "error": "'ui_port' must be an integer"})
                                return
                        
                        res = self.server.spawn_playwright_session_by_id(session_id, ui_host=ui_host, ui_port=ui_port, keepalive=bool(keepalive))  # type: ignore[attr-defined]
                        self._json(200, res)
                    except Exception as e:
                        self._json(500, {"success": False, "error": f"Failed to start session: {e}"})
                    return
                
                elif operation == "stop":
                    try:
                        res = self.server.stop_playwright_session_by_id(session_id)  # type: ignore[attr-defined]
                        self._json(200, res)
                    except Exception as e:
                        self._json(500, {"success": False, "error": f"Failed to stop session: {e}"})
                    return
                
                elif operation == "delete":
                    try:
                        res = self.server.delete_playwright_session(session_id)  # type: ignore[attr-defined]
                        self._json(200, res)
                    except Exception as e:
                        self._json(500, {"success": False, "error": f"Failed to delete session: {e}"})
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

        # --- NEW: Playwright session control endpoints (POST) ---
        if self.path == "/api/playwright/session/attach":
            # Expected payload: { session_id?, host, port }
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
                res = self.server.set_playwright_session_upstream(str(session_id or ''), host, port)  # type: ignore[attr-defined]
                self._json(200, res)
            except Exception as e:
                self._json(500, {"success": False, "error": f"Attach failed: {e}"})
            return

        if self.path == "/api/playwright/session/spawn":
            # Expected payload: { session_id?, ui_host?, ui_port?, keepalive? }
            try:
                session_id = (data.get("session_id") or "").strip() or None
                ui_host = (data.get("ui_host") or "").strip() or None
                ui_port = data.get("ui_port")
                keepalive = data.get("keepalive")
                # Normalize types
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
                res = self.server.spawn_playwright_session_agent(session_id=session_id, ui_host=ui_host, ui_port=ui_port, keepalive=keepalive)  # type: ignore[attr-defined]
                self._json(200, res)
            except Exception as e:
                self._json(500, {"success": False, "error": f"Spawn failed: {e}"})
            return

        if self.path == "/api/playwright/session/stop":
            try:
                res = self.server.stop_playwright_session_agent()  # type: ignore[attr-defined]
                self._json(200, res)
            except Exception as e:
                self._json(500, {"success": False, "error": f"Stop failed: {e}"})
            return

        # --- NEW: Multi-session management endpoints ---
        if self.path == "/api/sessions":
            # Create new session
            try:
                name = (data.get("name") or "").strip()
                model = (data.get("model") or "gpt-4").strip()
                tools = data.get("tools", ["playwright"])
                
                if not name:
                    self._json(400, {"success": False, "error": "'name' is required"})
                    return
                
                # Create session via server method
                result = self.server.create_playwright_session(name=name, model=model, tools=tools)  # type: ignore[attr-defined]
                self._json(200, result)
            except Exception as e:
                self._json(500, {"success": False, "error": f"Failed to create session: {e}"})
            return

        # Session-specific management endpoints
        if self.path.startswith("/api/sessions/") and self.path.endswith("/start"):
            try:
                session_id = self.path.split("/")[3]  # Extract session_id from path
                result = self.server.start_playwright_session_by_id(session_id)  # type: ignore[attr-defined]
                self._json(200, result)
            except Exception as e:
                self._json(500, {"success": False, "error": f"Failed to start session: {e}"})
            return

        if self.path.startswith("/api/sessions/") and self.path.endswith("/stop"):
            try:
                session_id = self.path.split("/")[3]  # Extract session_id from path
                result = self.server.stop_playwright_session_by_id(session_id)  # type: ignore[attr-defined]
                self._json(200, result)
            except Exception as e:
                self._json(500, {"success": False, "error": f"Failed to stop session: {e}"})
            return

        if self.path.startswith("/api/sessions/") and self.path.endswith("/delete"):
            try:
                session_id = self.path.split("/")[3]  # Extract session_id from path
                result = self.server.delete_playwright_session_by_id(session_id)  # type: ignore[attr-defined]
                self._json(200, result)
            except Exception as e:
                self._json(500, {"success": False, "error": f"Failed to delete session: {e}"})
            return

        # --- Frontend compatibility endpoints for session-specific operations ---
        if self.path.startswith("/api/playwright/session/") and "/spawn" in self.path:
            # Frontend compatibility: /api/playwright/session/{session_id}/spawn
            try:
                session_id = self.path.split("/")[4]  # Extract session_id from path
                ui_host = (data.get("ui_host") or "").strip() or None
                ui_port = data.get("ui_port")
                keepalive = data.get("keepalive", True)
                
                if ui_port is not None:
                    try:
                        ui_port = int(ui_port)
                    except Exception:
                        self._json(400, {"success": False, "error": "'ui_port' must be an integer"})
                        return
                
                res = self.server.spawn_playwright_session_by_id(session_id, ui_host=ui_host, ui_port=ui_port, keepalive=bool(keepalive))  # type: ignore[attr-defined]
                self._json(200, res)
            except Exception as e:
                self._json(500, {"success": False, "error": f"Failed to spawn session: {e}"})
            return

        if self.path.startswith("/api/playwright/session/") and "/stop" in self.path:
            # Frontend compatibility: /api/playwright/session/{session_id}/stop
            try:
                session_id = self.path.split("/")[4]  # Extract session_id from path
                res = self.server.stop_playwright_session_by_id(session_id)  # type: ignore[attr-defined]
                self._json(200, res)
            except Exception as e:
                self._json(500, {"success": False, "error": f"Failed to stop session: {e}"})
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
        
        # --- React UI serving configuration (for migration) ---
        # Clear comments for easy debug; enables serving the React webapp instead of inline HTML
        try:
            cfg = getattr(self.assistant, 'config', None)
            print(f"DEBUG: Assistant config object: {cfg}")
            print(f"DEBUG: Config type: {type(cfg)}")
            if cfg:
                print(f"DEBUG: Config attributes: {dir(cfg)}")
                raw_enabled = getattr(cfg, 'react_ui_enabled', False)
                print(f"DEBUG: Raw react_ui_enabled value: {raw_enabled}, type: {type(raw_enabled)}")
            self._react_ui_enabled = bool(getattr(cfg, 'react_ui_enabled', False))
            dist_dir = getattr(cfg, 'react_ui_dist_dir', None)
            print(f"DEBUG: React UI config - enabled: {self._react_ui_enabled}, dist_dir: {dist_dir}")
            if dist_dir:
                try:
                    self._react_ui_dist_dir = Path(dist_dir)
                except Exception:
                    self._react_ui_dist_dir = None
            else:
                try:
                    self._react_ui_dist_dir = Path(__file__).resolve().parents[1] / 'ui' / 'webapp' / 'dist'
                except Exception:
                    self._react_ui_dist_dir = None
            print(f"DEBUG: React UI dist_dir resolved to: {self._react_ui_dist_dir}")
        except Exception as e:
            # Safe defaults if config access fails
            print(f"DEBUG: React UI config access failed: {e}")
            self._react_ui_enabled = False
            self._react_ui_dist_dir = None
        
        # Disable React UI if dist directory doesn't exist
        if self._react_ui_dist_dir and not self._react_ui_dist_dir.exists():
            print(f"DEBUG: React UI disabled - dist directory doesn't exist: {self._react_ui_dist_dir}")
            self._react_ui_enabled = False
        
        print(f"DEBUG: Final React UI state - enabled: {self._react_ui_enabled}, dist_dir: {self._react_ui_dist_dir}")
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
                self._httpd = _AssistantHTTPServer((bind_host, bind_port), _GUIRequestHandler, self.assistant, self.loop, self._react_ui_enabled, self._react_ui_dist_dir)  # type: ignore[arg-type]
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
  </nav>
  <div id="content-chat"></div>
</main>
<script>
  // --- Tabs ---
  document.getElementById('tab-chat').onclick = () => {
    document.getElementById('content-chat').style.display = '';
    document.getElementById('tab-chat').classList.add('active');
    // No live preview polling anymore; simply switch tabs
  };

  // Helper to programmatically switch to the Playwright tab
  function openPlaywrightTab() {
    // Playwright tab removed; this function intentionally does nothing.
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
          // Spezialfall: MCPTools -> Playwright Integration über GUI-Session-APIs
          // Statt eines generischen /api/tool-Usage-Calls wollen wir die vorhandene
          // Playwright-Session im GUI starten/attachen und die UI öffnen. Dies beseitigt
          // den hängenden "Loading usage..."-Zustand.
          const cmdLower = (cmd || '').toLowerCase();
          if (cmdLower === 'playwright') {
            try {
              usageBox.textContent = 'Loading usage...';
              // 1) Status der Session abfragen
              let status = {};
              try {
                const rs = await fetch('/api/playwright/session/status');
                status = await rs.json();
              } catch(e) {
                // Status kann fehlen, wir fahren fort und versuchen zu spawnen
                status = { connected: false };
              }

              // 2) Falls nicht verbunden, Playwright-Agent spawnen (mit Defaults)
              if (!status || !status.connected) {
                try {
                  const spawnRes = await postJSON('/api/playwright/session/spawn', {});
                  // Spawn löst Events aus; wir öffnen proaktiv den Tab für bessere UX
                  try { openPlaywrightTab(); } catch(_e) {}
                  // Aktualisierten Status erneut abfragen
                  try {
                    const rs2 = await fetch('/api/playwright/session/status');
                    status = await rs2.json();
                  } catch(_e) {}
                  // Log freundliche Anzeige für Debug
                  appendLog('[INFO] Playwright session spawn requested via MCPTools card');
                } catch(e) {
                  usageBox.textContent = 'Error spawning Playwright: ' + e;
                  return;
                }
              } else {
                // Bereits verbunden: Tab öffnen für schnellen Zugriff
                try { openPlaywrightTab(); } catch(_e) {}
              }

              // 3) Usage/Status-Box rendern mit Einfügen-Button (Template)
              const connected = !!(status && status.connected);
              const sid = (status && status.session_id) ? String(status.session_id) : '';
              const host = (status && status.host) ? String(status.host) : '';
              const port = (status && status.port != null) ? String(status.port) : '';
              const summary = connected
                ? `Session connected (id=${escapeHtml(sid)} @ ${escapeHtml(host)}:${escapeHtml(port)})`
                : 'Session not connected';
              const usageText = [
                'Usage: playwright start | playwright status | playwright stop',
                summary
              ].join('\n');
              const insertBtn = '<div style="margin-top:6px;"><button id="ins-' + p.name + '-' + cmd + '">Insert template into chat</button></div>';
            usageBox.innerHTML = '<div><strong>Playwright (MCPTools)</strong></div>'
              + '<div style="margin-top:4px;"><code>' + escapeHtml(usageText) + '</code></div>'
              + insertBtn;
            const ins = usageBox.querySelector('#ins-' + CSS.escape(p.name) + '-' + CSS.escape(cmd));
              if (ins) ins.addEventListener('click', () => {
                // Einfaches Template ins Chatfeld einsetzen
                let template = 'playwright status';
                msg.value = template; msg.focus();
              });
              return; // WICHTIG: Spezialbehandlung beendet die Standard-Usage-Logik
            } catch (e) {
              usageBox.textContent = 'Error: ' + e;
              return;
            }
          }

          // Standardpfad: generische Usage-Abfrage über /api/tool
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