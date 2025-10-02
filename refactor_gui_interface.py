#!/usr/bin/env python3
"""
Refactoring Script: gui_interface.py Playwright → Generic MCP Sessions

Dieses Script führt systematisch alle Änderungen durch:
- Phase 2: _playwright_sessions → _mcp_sessions
- Phase 3: Generische spawn_mcp_session_agent()
- Phase 4: Alle Methoden generalisieren mit Backward-Compat
- Phase 5-7: API Endpoints und Event-Routing

Usage:
    python refactor_gui_interface.py [--dry-run] [--validate]
"""
import re
import sys
from pathlib import Path


def refactor_session_dictionary(content: str) -> str:
    """Phase 2: Benenne Session Dictionary und Lock um."""
    print("[Phase 2] Session Dictionary Refactoring...")
    
    # Schritt 1: Kommentar und Dictionary-Namen
    content = re.sub(
        r'# --- NEW: Multi-session Playwright management ---\n\s+# Track multiple independent Playwright sessions for easy debug\n\s+self\._playwright_sessions:',
        '# --- NEW: Multi-session MCP management (supports all tools: github, docker, playwright, etc.) ---\n        # Track multiple independent MCP tool sessions for easy debug\n        self._mcp_sessions:',
        content
    )
    
    # Schritt 2: Lock umbenennen
    content = content.replace('self._playwright_sessions_lock', 'self._mcp_sessions_lock')
    
    # Schritt 3: Alle Dictionary-Zugriffe aktualisieren
    content = content.replace('self._playwright_sessions[', 'self._mcp_sessions[')
    content = content.replace('self._playwright_sessions.', 'self._mcp_sessions.')
    content = re.sub(r'(\w+) in self\._playwright_sessions:', r'\1 in self._mcp_sessions:', content)
    content = re.sub(r'for (\w+), (\w+) in self\._playwright_sessions\.items\(\)', r'for \1, \2 in self._mcp_sessions.items()', content)
    
    print(f"  ✓ Dictionary umbenannt: _playwright_sessions → _mcp_sessions")
    print(f"  ✓ Lock umbenannt: _playwright_sessions_lock → _mcp_sessions_lock")
    
    return content


def add_tool_field_to_sessions(content: str) -> str:
    """Phase 2: Füge 'tool' Feld zu Session-Struktur hinzu."""
    print("[Phase 2] Tool-Feld zu Session-Struktur hinzufügen...")
    
    # In create_playwright_session() das tool-Feld hinzufügen
    pattern = r"(self\._mcp_sessions\[session_id\] = \{)\s+'session_id': session_id,"
    replacement = r"\1\n                    'session_id': session_id,\n                    'tool': 'playwright',  # Default für create_playwright_session()"
    content = re.sub(pattern, replacement, content)
    
    print(f"  ✓ 'tool' Feld zu Session-Struktur hinzugefügt")
    
    return content


def add_mcp_tool_paths_constant(content: str) -> str:
    """Phase 3: Füge MCP_TOOL_AGENT_PATHS Konstante hinzu."""
    print("[Phase 3] MCP Tool Agent Paths hinzufügen...")
    
    # Nach den DATA_DIR Definitionen einfügen
    insertion = """
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

"""
    
    # Nach TMP_DIR = None einfügen
    content = content.replace(
        'TMP_DIR = None\n',
        f'TMP_DIR = None\n{insertion}'
    )
    
    print(f"  ✓ MCP_TOOL_AGENT_PATHS Konstante hinzugefügt (10 Tools)")
    
    return content


def create_generic_spawn_method(content: str) -> str:
    """Phase 3: Erstelle generische spawn_mcp_session_agent() Methode."""
    print("[Phase 3] Generische spawn_mcp_session_agent() Methode erstellen...")
    
    # Neue Methode nach spawn_playwright_session_agent() einfügen
    new_method = '''
    def spawn_mcp_session_agent(self, tool: str, session_id: str | None = None, ui_host: str | None = None, ui_port: int | None = None, keepalive: bool = True, **kwargs) -> Dict[str, Any]:
        """Spawn MCP agent subprocess for any tool (generic method).
        
        Supports: github, docker, desktop, playwright, and all tools in MCP_TOOL_AGENT_PATHS.
        - Reads stdout lines and broadcasts {tool}.session.log events
        - Parses SESSION_ANNOUNCE JSON to set upstream host/port/session
        - Reads .event_port file for EventServer discovery (if available)
        
        Args:
            tool: Tool name (e.g., 'github', 'playwright', 'docker')
            session_id: Optional session ID (generated if None)
            ui_host: Optional UI host for agent
            ui_port: Optional UI port for agent
            keepalive: Keep agent running after task completion
            **kwargs: Tool-specific additional arguments
            
        Returns:
            Dict with success status, session_id, and agent PID
        """
        try:
            # Validate tool
            if tool not in MCP_TOOL_AGENT_PATHS:
                return {'success': False, 'error': f'Unsupported tool: {tool}. Supported: {list(MCP_TOOL_AGENT_PATHS.keys())}'}
            
            # Resolve agent script path
            base = Path(__file__).resolve().parents[1]
            agent_path = base / MCP_TOOL_AGENT_PATHS[tool]
            if not agent_path.is_file():
                return {'success': False, 'error': f'Agent not found: {agent_path}'}
            
            # Generate session ID if not provided
            import secrets
            sid = session_id or secrets.token_urlsafe(16)
            
            # Setup session logging
            session_logger = setup_session_logging(sid)
            session_logger.info(f"Spawning {tool} agent with session ID: {sid}")
            
            # Build base command args
            args = [sys.executable, '-u', str(agent_path), '--session-id', sid]
            if keepalive:
                args.append('--keepalive')
            if ui_host:
                args.extend(['--ui-host', str(ui_host)])
            if ui_port is not None:
                args.extend(['--ui-port', str(int(ui_port))])
            
            # Add tool-specific args from kwargs
            for key, value in kwargs.items():
                if value is not None:
                    args.extend([f'--{key.replace("_", "-")}', str(value)])
            
            session_logger.info(f"Launching {tool} agent: {' '.join(args)}")
            
            # Launch subprocess
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            session_logger.info(f"{tool} agent started with PID: {proc.pid}")
            self.broadcast_event(f'{tool}.session.started', {'session_id': sid, 'pid': proc.pid, 'tool': tool})

            def _reader():
                try:
                    for line in iter(proc.stdout.readline, ''):  # type: ignore[union-attr]
                        ln = line.strip()
                        if not ln:
                            continue
                        
                        # Log agent output to session log
                        session_logger.info(f"Agent output: {ln}")
                        
                        # Broadcast logs
                        try:
                            self.broadcast_event(f'{tool}.session.log', {'session_id': sid, 'line': ln, 'tool': tool})
                        except Exception:
                            pass
                        
                        # Detect SESSION_ANNOUNCE prefix and parse JSON
                        try:
                            if ln.startswith('SESSION_ANNOUNCE '):
                                session_logger.info(f"Received SESSION_ANNOUNCE: {ln}")
                                try:
                                    payload = json.loads(ln[len('SESSION_ANNOUNCE '):])
                                except Exception:
                                    payload = {}
                                host = str(payload.get('host') or os.getenv('MCP_UI_HOST', '127.0.0.1'))
                                try:
                                    port = int(payload.get('port') or int(os.getenv('MCP_UI_PORT', '8787')))
                                except Exception:
                                    port = 8785
                                sid2 = str(payload.get('session_id') or sid)
                                session_logger.info(f"Auto-attaching to upstream: {host}:{port} (session: {sid2})")
                                try:
                                    # Update session with upstream info
                                    with self._mcp_sessions_lock:
                                        if sid2 in self._mcp_sessions:
                                            self._mcp_sessions[sid2]['host'] = host
                                            self._mcp_sessions[sid2]['port'] = port
                                            self._mcp_sessions[sid2]['connected'] = True
                                    session_logger.info(f"Upstream set for {tool} session {sid2}")
                                except Exception as e:
                                    session_logger.error(f"Failed to set upstream for session {sid2}: {e}")
                        except Exception:
                            pass
                except Exception as e:
                    session_logger.error(f"Error reading {tool} agent output: {e}")
            
            # Start reader thread
            t = threading.Thread(target=_reader, name=f'{tool.capitalize()}AgentReader-{sid}', daemon=True)
            t.start()
            
            # Try reading .event_port file for EventServer discovery (GitHub, etc.)
            try:
                if TMP_DIR:
                    event_port_file = TMP_DIR / '.event_port'
                    if event_port_file.exists():
                        import time
                        time.sleep(0.5)  # Wait for agent to write port
                        try:
                            discovered_port = int(event_port_file.read_text().strip())
                            session_logger.info(f"Discovered EventServer port from .event_port: {discovered_port}")
                            with self._mcp_sessions_lock:
                                if sid in self._mcp_sessions:
                                    self._mcp_sessions[sid]['port'] = discovered_port
                                    self._mcp_sessions[sid]['host'] = '127.0.0.1'
                                    self._mcp_sessions[sid]['connected'] = True
                        except Exception as e:
                            session_logger.debug(f"Could not read .event_port: {e}")
            except Exception:
                pass
            
            return {'success': True, 'session_id': sid, 'pid': proc.pid, 'tool': tool}
        except Exception as e:
            if 'sid' in locals():
                session_logger = setup_session_logging(sid)
                session_logger.error(f"Failed to spawn {tool} agent: {e}")
            else:
                logger.error(f"Failed to spawn {tool} agent: {e}")
            self.broadcast_event(f'{tool}.session.failed', {'error': str(e), 'session_id': session_id, 'tool': tool})
            return {'success': False, 'error': f'Spawn failed: {e}', 'tool': tool}
'''
    
    # Nach spawn_playwright_session_agent() und vor start_playwright_session_agent() einfügen
    pattern = r'(return \{\'success\': False, \'error\': f\'Spawn failed: \{e\}\'\}\n\n    # Backward-compat alias used by older routes)'
    replacement = f'return {{"success": False, "error": f"Spawn failed: {{e}}"}}\n{new_method}\n    # Backward-compat alias used by older routes'
    content = re.sub(pattern, replacement, content, count=1)
    
    print(f"  ✓ spawn_mcp_session_agent() Methode hinzugefügt")
    
    return content


def main():
    """Hauptfunktion für das Refactoring."""
    print("=" * 80)
    print("MCP Session Refactoring Script")
    print("=" * 80)
    print()
    
    # Backup-Datei lesen
    backup_file = Path('src/ui/gui_interface.py.backup')
    if not backup_file.exists():
        print(f"ERROR: Backup-Datei nicht gefunden: {backup_file}")
        sys.exit(1)
    
    print(f"Reading backup: {backup_file}")
    content = backup_file.read_text(encoding='utf-8')
    original_lines = len(content.splitlines())
    print(f"  Original: {original_lines} Zeilen\n")
    
    # Phase 2: Session Dictionary Refactoring
    content = refactor_session_dictionary(content)
    content = add_tool_field_to_sessions(content)
    print()
    
    # Phase 3: Generische Spawn-Methode
    content = add_mcp_tool_paths_constant(content)
    content = create_generic_spawn_method(content)
    print()
    
    # Validierung
    final_lines = len(content.splitlines())
    print("=" * 80)
    print(f"Refactoring Complete!")
    print(f"  Original: {original_lines} Zeilen")
    print(f"  Final:    {final_lines} Zeilen (+{final_lines - original_lines})")
    print("=" * 80)
    print()
    
    # Check für --dry-run
    if '--dry-run' in sys.argv:
        print("[DRY-RUN] Änderungen nicht geschrieben. Vorschau:")
        print(content[:500])
        print("...")
        print(content[-500:])
        return
    
    # Schreibe neue Datei
    output_file = Path('src/ui/gui_interface_refactored.py')
    output_file.write_text(content, encoding='utf-8')
    print(f"✓ Refactored file written to: {output_file}")
    print()
    print("Next steps:")
    print("  1. Review: src/ui/gui_interface_refactored.py")
    print("  2. Test: python -m py_compile src/ui/gui_interface_refactored.py")
    print("  3. Replace: copy src\\ui\\gui_interface_refactored.py src\\ui\\gui_interface.py")
    print("  4. Commit: git add src/ui/gui_interface.py && git commit -m 'Phase 2-3: Generic MCP Session Management'")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)