"""MCP Session Manager for handling all MCP tool sessions.

This module provides a centralized session management system for MCP tools,
extracted from the _AssistantHTTPServer class to improve code organization
and eliminate duplication.
"""

from __future__ import annotations

import json
import logging
import secrets
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict

# Import required modules from the new modular GUI structure
from src.gui.config import (
    MCP_TOOL_AGENT_PATHS,
    TMP_DIR,
    setup_session_logging,
)

logger = logging.getLogger(__name__)


class MCPSessionManager:
    """Centralized manager for MCP tool sessions.

    Handles session creation, lifecycle management, agent spawning,
    and event broadcasting for all MCP tools.
    """

    def __init__(self, event_broadcaster: Callable[[str, Dict[str, Any] | None], None]):
        """Initialize the MCP Session Manager.

        Args:
            event_broadcaster: Function to broadcast events (e.g., server.broadcast_event)
        """
        self.event_broadcaster = event_broadcaster

        # Session storage - thread-safe dictionary of session data
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._sessions_lock = threading.Lock()

        # Supported MCP tools
        self.supported_tools = set(MCP_TOOL_AGENT_PATHS.keys())

    def create_session(self, tool: str, name: str, model: str = "gpt-4",
                      config: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Create a new MCP session.

        Args:
            tool: Name of the MCP tool
            name: Human-readable session name
            model: AI model to use
            config: Tool-specific configuration

        Returns:
            Dict with success status and session info or error
        """
        if tool not in self.supported_tools:
            return {"success": False, "error": f"Unsupported tool: {tool}"}

        session_id = secrets.token_urlsafe(16)

        with self._sessions_lock:
            self._sessions[session_id] = {
                "session_id": session_id,
                "tool": tool,
                "name": name,
                "model": model,
                "status": "stopped",
                "connected": False,
                "host": None,
                "port": None,
                "agent_proc": None,
                "agent_pid": None,
                "agent_running": False,
                "created_at": time.time(),
                "config": config or {},
                "task": config.get("task") if config else None,
                "target_tool": config.get("target_tool") if config else tool,
            }

        session_logger = setup_session_logging(session_id, tool)
        session_logger.info(f"Created {tool} session: {name}")

        # Broadcast session creation event
        self.event_broadcaster("mcp.session.created", {
            "session_id": session_id,
            "tool": tool,
            "name": name
        })

        return {
            "success": True,
            "session": {
                "session_id": session_id,
                "tool": tool,
                "tools": [tool],  # Add tools as array for frontend compatibility
                "target_tool": tool,  # Add target_tool for frontend compatibility
                "name": name,
                "model": model,
                "status": "stopped",
                "connected": False,
                "host": None,
                "port": None,
                "agent_running": False,
                "created_at": time.time(),
            }
        }

    def get_all_sessions(self, tool_filter: str | None = None) -> Dict[str, Any]:
        """Get all sessions, optionally filtered by tool.

        Args:
            tool_filter: Optional tool name to filter by

        Returns:
            Dict with success status and sessions list or error
        """
        try:
            with self._sessions_lock:
                sessions = []
                for sid, sess in self._sessions.items():
                    if tool_filter and sess.get("tool") != tool_filter:
                        continue

                    proc = sess.get("agent_proc")
                    running = bool(proc and proc.poll() is None)

                    # Auto-update status if process has exited
                    current_status = sess.get("status", "stopped")
                    if not running and current_status == "running":
                        # Process has exited, update status to completed
                        sess["status"] = "completed"
                        sess["agent_running"] = False
                        sess["stopped_at"] = time.time()
                        current_status = "completed"

                    # Ensure tools is always an array
                    tool = sess.get("tool", "unknown")
                    tools = sess.get("tools", [tool]) if sess.get("tools") else [tool]

                    sessions.append({
                        "session_id": sid,
                        "tool": tool,
                        "tools": tools,  # Always include tools as array
                        "target_tool": tool,  # Add target_tool for frontend compatibility
                        "name": sess.get("name", f"Session {sid[:8]}"),
                        "model": sess.get("model", "gpt-4"),
                        "status": current_status,
                        "connected": sess.get("connected", False),
                        "host": sess.get("host"),
                        "port": sess.get("port"),
                        "agent_running": running,
                        "created_at": sess.get("created_at"),
                        "task": sess.get("task"),  # Include task if present
                    })
                return {"success": True, "sessions": sessions}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_session(self, session_id: str) -> Dict[str, Any] | None:
        """Get a specific session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data dict or None if not found
        """
        with self._sessions_lock:
            return self._sessions.get(session_id)

    def spawn_agent(self, tool: str, session_id: str | None = None,
                   ui_host: str | None = None, ui_port: int | None = None,
                   keepalive: bool = False, **kwargs) -> Dict[str, Any]:
        """Spawn MCP agent subprocess for any tool.

        Args:
            tool: Name of the MCP tool to spawn
            session_id: Optional session ID, generated if not provided
            ui_host: Optional UI host for the agent to connect back to
            ui_port: Optional UI port for the agent to connect back to
            keepalive: Whether to keep the agent alive after initial run
            **kwargs: Tool-specific arguments passed to the agent

        Returns:
            Dict with success status, session_id, pid, and tool info or error message
        """
        if tool not in self.supported_tools:
            return {"success": False, "error": f"Unsupported tool: {tool}"}

        # Find or create session
        if session_id and session_id in self._sessions:
            sid = session_id
            # CRITICAL FIX: Read task from existing session config
            session = self._sessions[session_id]
            stored_task = session.get('task')
            if stored_task and 'task' not in kwargs:
                kwargs['task'] = stored_task
                logger.info(f"[TASK PROPAGATION] Using stored task from session config: {stored_task}")
        else:
            # Generate new session ID if not provided or doesn't exist
            sid = secrets.token_urlsafe(16)

        session_logger = setup_session_logging(sid)
        session_logger.info("=" * 80)
        session_logger.info(f"SPAWNING {tool.upper()} AGENT - DIAGNOSTIC MODE")
        session_logger.info("=" * 80)
        session_logger.info(f"Session ID: {sid}")
        session_logger.info(f"[TASK PROPAGATION] Task in kwargs: {kwargs.get('task', 'NOT SET')}")

        try:
            # Resolve agent path
            base = Path(__file__).resolve().parents[1]
            agent_path = base / MCP_TOOL_AGENT_PATHS[tool]
            
            # ========== DIAGNOSTIC LOGGING: Path Resolution ==========
            session_logger.info("Path Resolution Diagnostics:")
            session_logger.info(f"  Current file: {Path(__file__).resolve()}")
            session_logger.info(f"  Base path (parents[1]): {base}")
            session_logger.info(f"  MCP_TOOL_AGENT_PATHS[{tool}]: {MCP_TOOL_AGENT_PATHS[tool]}")
            session_logger.info(f"  Resolved agent path: {agent_path}")
            session_logger.info(f"  Agent exists: {agent_path.is_file()}")
            
            if not agent_path.is_file():
                session_logger.error(f"✗ CRITICAL: Agent file not found at: {agent_path}")
                session_logger.error(f"  Directory exists: {agent_path.parent.exists()}")
                if agent_path.parent.exists():
                    session_logger.error(f"  Directory contents: {list(agent_path.parent.iterdir())}")
                return {"success": False, "error": f"Agent not found: {agent_path}"}
            
            session_logger.info("✓ Agent file found")

            # ========== DIAGNOSTIC LOGGING: Python Executable ==========
            import os
            python_path = os.getenv('SAKANA_VENV_PYTHON')
            session_logger.info("Python Executable Diagnostics:")
            session_logger.info(f"  SAKANA_VENV_PYTHON env var: {python_path}")
            
            if not python_path:
                python_path = str(Path(__file__).resolve().parents[2] / ".venv" / "Scripts" / "python.exe")
                session_logger.info(f"  Using fallback path: {python_path}")
            
            python_exists = Path(python_path).exists()
            session_logger.info(f"  Python executable exists: {python_exists}")
            session_logger.info(f"  Python path: {python_path}")
            
            if not python_exists:
                session_logger.warning(f"✗ WARNING: Python executable not found at: {python_path}")
                session_logger.warning("  Trying system Python as fallback...")
                import sys
                python_path = sys.executable
                session_logger.info(f"  Using sys.executable: {python_path}")
            else:
                session_logger.info("✓ Python executable found")
            
            # Build command args
            # Use --session-id=VALUE format to handle IDs starting with hyphen
            args = [python_path, "-u", str(agent_path), f"--session-id={sid}"]

            if keepalive:
                args.append("--keepalive")
            if ui_host:
                args.extend(["--ui-host", str(ui_host)])
            if ui_port:
                args.extend(["--ui-port", str(int(ui_port))])

            # Add tool-specific arguments
            for key, value in kwargs.items():
                if value is not None:
                    args.extend([f"--{key.replace('_', '-')}", str(value)])

            # ========== DIAGNOSTIC LOGGING: Subprocess Command ==========
            session_logger.info("Subprocess Command:")
            session_logger.info(f"  Full command: {' '.join(args)}")
            session_logger.info(f"  Working directory: {Path.cwd()}")

            # Start subprocess
            session_logger.info("Starting subprocess...")
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',  # Force UTF-8 encoding on Windows
                errors='replace',  # Replace invalid chars instead of crashing
                bufsize=1
            )

            session_logger.info(f"✓ Subprocess started successfully")
            session_logger.info(f"  Process ID (PID): {proc.pid}")
            session_logger.info(f"  Return code (initial): {proc.poll()}")


            agent_thread = threading.Thread(
                target=self._agent_output_reader,
                args=(proc, sid, tool),
                name=f"{tool}Reader-{sid}",
                daemon=True
            )
            agent_thread.start()

            # Update session state
            with self._sessions_lock:
                if sid not in self._sessions:
                    self._sessions[sid] = {
                        "session_id": sid,
                        "tool": tool,
                        "status": "running",
                        "connected": False,
                        "host": None,
                        "port": None,
                        "agent_proc": proc,
                        "agent_pid": proc.pid,
                        "agent_running": True,
                        "created_at": time.time(),
                    }

                    # PERSIST PID TO FILE for crash recovery
                    try:
                        if TMP_DIR:
                            pid_file = TMP_DIR / f"session_{sid}.pid"
                            pid_file.write_text(str(proc.pid))
                            session_logger.info(f"PID {proc.pid} persisted to {pid_file}")
                    except Exception as e:
                        session_logger.error(f"Failed to persist PID: {e}")
                else:
                    self._sessions[sid].update({
                        "agent_proc": proc,
                        "agent_pid": proc.pid,
                        "agent_running": True,
                        "status": "running",
                    })

            # Broadcast event
            self.event_broadcaster(f"{tool}.session.started", {
                "session_id": sid,
                "pid": proc.pid,
                "tool": tool
            })

            # Try to discover port from .event_port file
            self._discover_event_port(sid)

            return {
                "success": True,
                "session_id": sid,
                "pid": proc.pid,
                "tool": tool
            }

        except Exception as e:
            logger.error(f"Spawn {tool} failed: {e}")
            return {"success": False, "error": str(e), "tool": tool}

    def _get_pid_from_file(self, session_id: str) -> int | None:
        """Recover PID from persistence file.

        Args:
            session_id: Session identifier

        Returns:
            PID if found, None otherwise
        """
        try:
            if TMP_DIR:
                pid_file = TMP_DIR / f"session_{session_id}.pid"
                if pid_file.exists():
                    pid = int(pid_file.read_text().strip())
                    logger.info(f"Recovered PID {pid} from file for session {session_id}")
                    return pid
        except Exception as e:
            logger.error(f"Failed to read PID file: {e}")
        return None

    def _is_process_running_windows(self, pid: int) -> bool:
        """Check if process is running on Windows using tasklist.

        Args:
            pid: Process ID to check

        Returns:
            bool: True if process exists and is running
        """
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # tasklist returns process info if running, "INFO: No tasks..." if not
            return str(pid) in result.stdout
        except Exception as e:
            logger.error(f"Error checking PID {pid}: {e}")
            return False

    def _kill_process_windows(self, pid: int, force: bool = False) -> Dict[str, Any]:
        """Kill process on Windows using taskkill.

        Args:
            pid: Process ID to kill
            force: Use /F flag for force kill

        Returns:
            Dict with success status
        """
        try:
            # Build taskkill command
            cmd = ["taskkill", "/PID", str(pid), "/T"]  # /T kills process tree

            if force:
                cmd.append("/F")  # Force kill

            logger.info(f"Executing: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info(f"Successfully killed PID {pid}")
                return {"success": True, "method": "taskkill"}
            else:
                logger.error(f"taskkill failed: {result.stderr}")
                return {"success": False, "error": result.stderr}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "taskkill timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _kill_process_unix(self, pid: int, force: bool = False) -> Dict[str, Any]:
        """Kill process on Unix using kill command.

        Args:
            pid: Process ID to kill
            force: Use SIGKILL instead of SIGTERM

        Returns:
            Dict with success status
        """
        try:
            import signal
            import os

            sig = signal.SIGKILL if force else signal.SIGTERM

            os.kill(pid, sig)

            logger.info(f"Sent signal {sig} to PID {pid}")
            return {"success": True, "method": "kill"}

        except ProcessLookupError:
            return {"success": True, "message": "Process not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_agent(self, session_id: str) -> Dict[str, Any]:
        """Stop agent for a specific session using platform-specific methods.

        Enhanced with:
        - Windows taskkill support
        - PID file recovery
        - Child process cleanup
        - Force kill fallback

        Args:
            session_id: Session identifier

        Returns:
            Dict with success status or error
        """
        with self._sessions_lock:
            if session_id not in self._sessions:
                return {"success": False, "error": f"Session {session_id} not found"}

            session = self._sessions[session_id]
            proc = session.get("agent_proc")
            pid = session.get("agent_pid")
            tool = session.get("tool")

            # Try to recover PID from file if not in session
            if not pid:
                pid = self._get_pid_from_file(session_id)

            # If no PID available, mark as stopped
            if not pid:
                session.update({
                    "agent_proc": None,
                    "agent_pid": None,
                    "agent_running": False,
                    "connected": False,
                    "status": "stopped",
                    "stopped_at": time.time(),
                })
                return {"success": True, "message": "No PID found, marked as stopped"}

            session_logger = setup_session_logging(session_id, tool)
            session_logger.info(f"Stopping agent for session {session_id} (PID: {pid})")

            # Platform-specific termination
            import platform

            if platform.system() == "Windows":
                # Windows: Use taskkill

                # 1. Try graceful kill first (without /F)
                result = self._kill_process_windows(pid, force=False)

                if not result["success"]:
                    session_logger.warning(f"Graceful taskkill failed: {result.get('error')}")

                    # 2. Wait 2 seconds
                    time.sleep(2)

                    # 3. Force kill with /F flag
                    session_logger.info("Attempting force kill with /F flag")
                    result = self._kill_process_windows(pid, force=True)

                    if not result["success"]:
                        session_logger.error(f"Force taskkill also failed: {result.get('error')}")

            else:
                # Unix: Use kill signals

                # 1. Try SIGTERM
                result = self._kill_process_unix(pid, force=False)

                if not result["success"]:
                    # 2. Wait 2 seconds
                    time.sleep(2)

                    # 3. Force kill with SIGKILL
                    result = self._kill_process_unix(pid, force=True)

            # 4. Verify termination (Windows only)
            if platform.system() == "Windows":
                time.sleep(1)  # Brief pause
                if self._is_process_running_windows(pid):
                    session_logger.error(f"Process {pid} still running after kill attempts")
                    return {"success": False, "error": "Process termination failed"}

            # 5. Update session state
            session.update({
                "agent_proc": None,
                "agent_pid": None,
                "agent_running": False,
                "connected": False,
                "status": "stopped",
                "stopped_at": time.time(),
            })

            # 6. Cleanup PID file
            try:
                if TMP_DIR:
                    pid_file = TMP_DIR / f"session_{session_id}.pid"
                    if pid_file.exists():
                        pid_file.unlink()
            except Exception as e:
                session_logger.debug(f"Failed to delete PID file: {e}")

            session_logger.info(f"Stopped agent for session {session_id}")

            # 7. Broadcast event
            self.event_broadcaster(f"{session.get('tool', 'unknown')}.session.stopped", {
                "session_id": session_id,
            })

            return {"success": True, "session_id": session_id, "method": result.get("method")}

    def delete_session(self, session_id: str) -> Dict[str, Any]:
        """Delete a session (stops agent if running).

        Args:
            session_id: Session identifier

        Returns:
            Dict with success status or error
        """
        # First stop the session if running
        stop_result = self.stop_agent(session_id)

        with self._sessions_lock:
            if session_id not in self._sessions:
                return {"success": False, "error": f"Session {session_id} not found"}

            tool = self._sessions[session_id].get("tool")
            del self._sessions[session_id]

            session_logger = setup_session_logging(session_id, tool)
            session_logger.info(f"Deleted session: {session_id}")

            # Broadcast event
            self.event_broadcaster("mcp.session.deleted", {
                "session_id": session_id,
            })

            return {"success": True, "session_id": session_id}

    def set_session_upstream(self, session_id: str, host: str, port: int) -> Dict[str, Any]:
        """Set upstream connection for a specific session.

        Args:
            session_id: Session identifier
            host: Upstream host
            port: Upstream port

        Returns:
            Dict with success status or error
        """
        with self._sessions_lock:
            if session_id not in self._sessions:
                return {"success": False, "error": f"Session {session_id} not found"}

            session = self._sessions[session_id]
            session["host"] = str(host)
            session["port"] = int(port)
            session["connected"] = True

            session_logger = setup_session_logging(session_id, session.get("tool"))
            session_logger.info(f"Set upstream for session {session_id}: {host}:{port}")

            # Broadcast event
            self.event_broadcaster(f"{session.get('tool', 'unknown')}.session.upstream_set", {
                "session_id": session_id,
                "host": host,
                "port": port,
            })

            return {"success": True, "session_id": session_id, "host": host, "port": port}

    def _agent_output_reader(self, proc: subprocess.Popen, session_id: str, tool: str):
        """Read agent subprocess output and handle events.

        Args:
            proc: Agent subprocess
            session_id: Session identifier
            tool: Tool name
        """
        session_logger = setup_session_logging(session_id, tool)
        session_logger.info("=" * 80)
        session_logger.info("AGENT OUTPUT READER STARTED - DIAGNOSTIC MODE")
        session_logger.info("=" * 80)
        session_logger.info(f"  Tool: {tool}")
        session_logger.info(f"  Session ID: {session_id}")
        session_logger.info(f"  PID: {proc.pid}")

        try:
            line_count = 0
            for line in iter(proc.stdout.readline, ""):
                ln = line.strip()
                if not ln:
                    continue

                line_count += 1
                session_logger.info(f"[Line {line_count}] {ln}")

                # Broadcast log event
                self.event_broadcaster(f"{tool}.session.log", {
                    "session_id": session_id,
                    "line": ln,
                    "tool": tool
                })

                # Handle SESSION_ANNOUNCE messages
                if ln.startswith("SESSION_ANNOUNCE "):
                    session_logger.info("=" * 80)
                    session_logger.info("SESSION_ANNOUNCE DETECTED!")
                    session_logger.info("=" * 80)
                    try:
                        json_str = ln[17:]
                        session_logger.info(f"  Raw JSON string: {json_str}")
                        
                        payload = json.loads(json_str)
                        session_logger.info(f"  Parsed payload: {payload}")
                        
                        host = str(payload.get("host", "127.0.0.1"))
                        port = int(payload.get("port", 8787))
                        ui_url = payload.get("ui_url", f"http://{host}:{port}")
                        
                        session_logger.info(f"  Extracted host: {host}")
                        session_logger.info(f"  Extracted port: {port}")
                        session_logger.info(f"  UI URL: {ui_url}")

                        with self._sessions_lock:
                            if session_id in self._sessions:
                                before_state = dict(self._sessions[session_id])
                                self._sessions[session_id].update({
                                    "host": host,
                                    "port": port,
                                    "connected": True
                                })
                                after_state = dict(self._sessions[session_id])
                                
                                session_logger.info("  Session state updated:")
                                session_logger.info(f"    Before: connected={before_state.get('connected')}, host={before_state.get('host')}, port={before_state.get('port')}")
                                session_logger.info(f"    After:  connected={after_state.get('connected')}, host={after_state.get('host')}, port={after_state.get('port')}")
                            else:
                                session_logger.warning(f"  ✗ WARNING: Session {session_id} not found in _sessions dict!")
                        
                        session_logger.info(f"✓ Upstream connection established: {host}:{port}")
                        session_logger.info("=" * 80)
                    except json.JSONDecodeError as e:
                        session_logger.error("=" * 80)
                        session_logger.error("✗ SESSION_ANNOUNCE JSON PARSE FAILED!")
                        session_logger.error(f"  Error: {e}")
                        session_logger.error(f"  Raw string: {ln[17:]}")
                        session_logger.error("=" * 80)
                    except Exception as e:
                        session_logger.error("=" * 80)
                        session_logger.error("✗ SESSION_ANNOUNCE PROCESSING FAILED!")
                        session_logger.error(f"  Error type: {type(e).__name__}")
                        session_logger.error(f"  Error: {e}")
                        session_logger.error("=" * 80)

        except Exception as e:
            session_logger.error("=" * 80)
            session_logger.error("✗ AGENT OUTPUT READER ERROR!")
            session_logger.error(f"  Error type: {type(e).__name__}")
            session_logger.error(f"  Error: {e}")
            session_logger.error(f"  Lines read before error: {line_count}")
            session_logger.error("=" * 80)
        finally:
            session_logger.info("=" * 80)
            session_logger.info("AGENT OUTPUT READER STOPPED")
            session_logger.info(f"  Total lines read: {line_count}")
            session_logger.info("=" * 80)

    def _discover_event_port(self, session_id: str):
        """Discover port from .event_port file if available.

        Args:
            session_id: Session identifier
        """
        try:
            if TMP_DIR:
                event_port_file = TMP_DIR / ".event_port"
                if event_port_file.exists():
                    time.sleep(0.5)  # Wait for file to be written
                    port_discovered = int(event_port_file.read_text().strip())

                    with self._sessions_lock:
                        tool = None
                        if session_id in self._sessions:
                            self._sessions[session_id].update({
                                "host": "127.0.0.1",
                                "port": port_discovered,
                                "connected": True
                            })
                            tool = self._sessions[session_id].get("tool")

                    session_logger = setup_session_logging(session_id, tool)
                    session_logger.info(f"Port from .event_port: {port_discovered}")
        except Exception as e:
            with self._sessions_lock:
                tool = self._sessions.get(session_id, {}).get("tool") if session_id in self._sessions else None
            session_logger = setup_session_logging(session_id, tool)
            session_logger.debug(f"Event port discovery failed: {e}")

    # Legacy compatibility methods for Playwright-specific operations
    def spawn_playwright_session_agent(self, session_id: str | None = None,
                                     ui_host: str | None = None, ui_port: int | None = None,
                                     keepalive: bool = True) -> Dict[str, Any]:
        """Spawn Playwright agent subprocess (legacy compatibility method)."""
        return self.spawn_agent('playwright', session_id, ui_host, ui_port, keepalive)

    def stop_playwright_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """Stop Playwright agent for a specific session (legacy compatibility method)."""
        return self.stop_agent(session_id)

    def start_playwright_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """Start Playwright agent for a specific session (legacy compatibility method)."""
        return self.spawn_agent('playwright', session_id)

    def start_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """Start agent for a specific session with correct tool type.
        
        This method reads the tool type from the session and spawns the appropriate agent.
        Replaces tool-specific start methods for multi-tool support.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict with success status or error
        """
        # Get tool from session for logging
        with self._sessions_lock:
            tool = self._sessions.get(session_id, {}).get("tool") if session_id in self._sessions else None

        session_logger = setup_session_logging(session_id, tool)
        session_logger.info("=" * 80)
        session_logger.info(f"[START SESSION] start_session_by_id({session_id})")
        session_logger.info("=" * 80)

        # Look up session to get tool type
        with self._sessions_lock:
            if session_id not in self._sessions:
                session_logger.error(f"✗ Session {session_id} not found in _sessions")
                return {"success": False, "error": f"Session {session_id} not found"}
            
            session = self._sessions[session_id]
            tool = session.get("tool")
            
            session_logger.info(f"  Session found:")
            session_logger.info(f"    tool: {tool}")
            session_logger.info(f"    name: {session.get('name')}")
            session_logger.info(f"    status: {session.get('status')}")
            
            if not tool:
                session_logger.error(f"✗ Session {session_id} has no tool specified")
                return {"success": False, "error": f"Session {session_id} has no tool"}
            
            # Check if already running
            proc = session.get('agent_proc')
            if proc and proc.poll() is None:
                session_logger.warning(f"⚠️  Session {session_id} already running")
                return {"success": False, "error": f"Session {session_id} already running"}
        
        # Spawn agent with correct tool type
        session_logger.info(f"✓ Spawning {tool} agent for session {session_id}")
        session_logger.info("=" * 80)
        
        return self.spawn_agent(tool, session_id)

    def delete_playwright_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """Delete a specific Playwright session (legacy compatibility method)."""
        return self.delete_session(session_id)

    def get_all_playwright_sessions(self) -> Dict[str, Any]:
        """Get status of all Playwright sessions (legacy compatibility method)."""
        return self.get_all_sessions(tool_filter='playwright')

    def delete_playwright_session(self, session_id: str) -> Dict[str, Any]:
        """Delete a Playwright session (legacy compatibility method)."""
        return self.delete_session(session_id)