"""HTTP Server for the GUI web interface.

This module provides the AssistantHTTPServer class which manages:
- HTTP connections
- SSE (Server-Sent Events) for real-time updates
- Multi-session MCP tool management
- Event broadcasting to connected clients
"""

import asyncio
import json
import logging
import queue
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from typing import Any, Dict, Tuple
from pathlib import Path

from .config import setup_session_logging

logger = logging.getLogger(__name__)


class AssistantHTTPServer(ThreadingHTTPServer):
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
        self.sse_queues: list[queue.Queue] = []
        # --- NEW: Event buffer for JSON polling fallback (/events.json)
        # Clear comments for easy debug; seq increases monotonically across events
        self._events_lock = threading.Lock()
        self._event_seq: int = 0
        self._event_buffer: list[str] = []  # store JSON strings to avoid re-encoding later
        self._event_buffer_max: int = 1000  # cap to prevent unbounded growth
        
        # --- NEW: Multi-session MCP management (supports all tools: github, docker, playwright, etc.) ---
        # Use MCPSessionManager for centralized session management
        from src.ui.mcp_session_manager import MCPSessionManager
        self._mcp_manager = MCPSessionManager(event_broadcaster=self.broadcast_event)
        
        # Legacy: Direct access to sessions dict for backward compatibility
        self._mcp_sessions = self._mcp_manager._sessions
        self._mcp_sessions_lock = self._mcp_manager._sessions_lock
        
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

    def get_mcp_session_status(self) -> Dict[str, Any]:
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

    def stop_mcp_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """Stop MCP agent for a specific session.

        Delegates to MCPSessionManager.stop_agent() which uses platform-specific
        termination (Windows: taskkill /T /F, Unix: kill signals).

        NOTE: Works with any tool session (github, docker, playwright, etc.) via _mcp_sessions."""
        return self._mcp_manager.stop_agent(session_id)

    def start_mcp_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """Start MCP agent for a specific session.

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

    def delete_mcp_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """Delete a specific MCP session (stops agent if running).

        NOTE: Works with any tool session (github, docker, playwright, etc.) via _mcp_sessions."""
        try:
            # First stop the session if running
            stop_result = self.stop_mcp_session_by_id(session_id)
            
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

    # Delegate to MCPSessionManager for session operations
    def spawn_mcp_session_agent(self, tool: str, session_id: str | None = None, ui_host: str | None = None, ui_port: int | None = None, keepalive: bool = True) -> Dict[str, Any]:
        """Spawn MCP session agent - delegates to MCPSessionManager."""
        result = self._mcp_manager.spawn_agent(tool, session_id, ui_host, ui_port, keepalive)
        # Update legacy single session tracking for Playwright backward compatibility
        if tool == 'playwright' and result.get('success'):
            self._playwright_agent_proc = self._mcp_manager._sessions.get(result['session_id'], {}).get('agent_proc')
            self._playwright_session_id = result['session_id']
        return result

    def get_all_mcp_sessions(self, tool_filter: str | None = None) -> Dict[str, Any]:
        """Get all MCP sessions - delegates to MCPSessionManager."""
        return self._mcp_manager.get_all_sessions(tool_filter)

    def create_mcp_session(self, name: str, model: str, tools: list, task: str | None = None, target_tool: str | None = None) -> Dict[str, Any]:
        """Create MCP session - delegates to MCPSessionManager."""
        # Extract first tool from tools list, default to playwright
        tool = tools[0] if tools else 'playwright'
        
        # If target_tool is not specified, use the tool from tools list
        if not target_tool:
            target_tool = tool
        
        # Create config with optional task
        config = {}
        if task:
            config['task'] = task
        if target_tool:
            config['target_tool'] = target_tool
        
        return self._mcp_manager.create_session(tool, name, model, config)

    def spawn_mcp_session_by_id(self, session_id: str, ui_host: str | None = None, ui_port: int | None = None, keepalive: bool = True) -> Dict[str, Any]:
        """Spawn MCP session by ID - delegates to MCPSessionManager."""
        # Get the session to determine which tool to spawn
        session = self._mcp_manager.get_session(session_id)
        if not session:
            return {'success': False, 'error': f'Session {session_id} not found'}

        tool = session.get('tool', 'playwright')  # Get actual tool, fallback to playwright
        result = self._mcp_manager.spawn_agent(tool, session_id, ui_host, ui_port, keepalive)

        # Update legacy tracking for playwright sessions
        if result.get('success') and tool == 'playwright':
            self._playwright_agent_proc = self._mcp_manager._sessions.get(session_id, {}).get('agent_proc')
            self._playwright_session_id = session_id
        return result

    def get_mcp_session_status_by_id(self, session_id: str) -> Dict[str, Any]:
        """Get MCP session status by ID."""
        session = self._mcp_manager.get_session(session_id)
        if not session:
            return {'success': False, 'error': f'Session {session_id} not found'}
        
        proc = session.get('agent_proc')
        running = bool(proc and proc.poll() is None)
        
        return {
            'success': True,
            'connected': session.get('connected', False),
            'session_id': session_id,
            'tool': session.get('tool', 'unknown'),
            'name': session.get('name', f'Session {session_id[:8]}'),
            'status': session.get('status', 'stopped'),
            'host': session.get('host'),
            'port': session.get('port'),
            'agent_pid': session.get('agent_pid'),
            'agent_running': running,
        }

    def start_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """Start agent for a session with automatic tool detection.

        Wrapper for MCPSessionManager.start_session_by_id() that reads
        the tool type from session storage and spawns the correct agent.

        Args:
            session_id: Session identifier

        Returns:
            Dict with success status or error
        """
        return self._mcp_manager.start_session_by_id(session_id)

    # ========== DEPRECATED: Backward compatibility wrappers ==========
    # These methods maintain the old "playwright" naming for backward compatibility.
    # All new code should use the mcp_* equivalents above.

    def get_playwright_session_status(self) -> Dict[str, Any]:
        """DEPRECATED: Use get_mcp_session_status() instead."""
        import warnings
        warnings.warn("get_playwright_session_status() is deprecated, use get_mcp_session_status()", DeprecationWarning, stacklevel=2)
        return self.get_mcp_session_status()

    def create_playwright_session(self, name: str, model: str, tools: list, task: str | None = None, target_tool: str | None = None, system: str | None = None) -> Dict[str, Any]:
        """DEPRECATED: Use create_mcp_session() instead."""
        import warnings
        warnings.warn("create_playwright_session() is deprecated, use create_mcp_session()", DeprecationWarning, stacklevel=2)
        return self.create_mcp_session(name, model, tools, task, target_tool)

    def stop_playwright_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """DEPRECATED: Use stop_mcp_session_by_id() instead."""
        import warnings
        warnings.warn("stop_playwright_session_by_id() is deprecated, use stop_mcp_session_by_id()", DeprecationWarning, stacklevel=2)
        return self.stop_mcp_session_by_id(session_id)

    def start_playwright_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """DEPRECATED: Use start_mcp_session_by_id() instead."""
        import warnings
        warnings.warn("start_playwright_session_by_id() is deprecated, use start_mcp_session_by_id()", DeprecationWarning, stacklevel=2)
        return self.start_mcp_session_by_id(session_id)

    def delete_playwright_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """DEPRECATED: Use delete_mcp_session_by_id() instead."""
        import warnings
        warnings.warn("delete_playwright_session_by_id() is deprecated, use delete_mcp_session_by_id()", DeprecationWarning, stacklevel=2)
        return self.delete_mcp_session_by_id(session_id)

    def spawn_playwright_session_by_id(self, session_id: str, ui_host: str | None = None, ui_port: int | None = None, keepalive: bool = True) -> Dict[str, Any]:
        """DEPRECATED: Use spawn_mcp_session_by_id() instead."""
        import warnings
        warnings.warn("spawn_playwright_session_by_id() is deprecated, use spawn_mcp_session_by_id()", DeprecationWarning, stacklevel=2)
        return self.spawn_mcp_session_by_id(session_id, ui_host, ui_port, keepalive)

    def get_playwright_session_status_by_id(self, session_id: str) -> Dict[str, Any]:
        """DEPRECATED: Use get_mcp_session_status_by_id() instead."""
        import warnings
        warnings.warn("get_playwright_session_status_by_id() is deprecated, use get_mcp_session_status_by_id()", DeprecationWarning, stacklevel=2)
        return self.get_mcp_session_status_by_id(session_id)

    def get_all_playwright_sessions(self) -> Dict[str, Any]:
        """DEPRECATED: Use get_all_mcp_sessions() instead."""
        import warnings
        warnings.warn("get_all_playwright_sessions() is deprecated, use get_all_mcp_sessions()", DeprecationWarning, stacklevel=2)
        return self.get_all_mcp_sessions()