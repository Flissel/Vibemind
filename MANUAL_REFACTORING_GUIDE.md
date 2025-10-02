# Manual Refactoring Guide: gui_interface.py → Generic MCP Sessions

**Ziel:** GitHub User Clarification Modal zum Laufen bringen  
**Status:** Phase 1-4 teilweise, Phase 5-8 fehlend  
**Aktuelle Datei:** 2824 Zeilen (Commit 3e28019)

---

## 📋 Schritt-für-Schritt-Anleitung

### ✅ Bereits erledigt (Git Commit 3e28019):
- [`_mcp_sessions`](src/ui/gui_interface.py:238) Dictionary ✅
- [`MCP_TOOL_AGENT_PATHS`](src/ui/gui_interface.py:47) Konstante ✅
- [`spawn_playwright_session_agent()`](src/ui/gui_interface.py:424) Wrapper ✅

### 🔧 Noch zu implementieren:

---

## Schritt 1: spawn_mcp_session_agent() hinzufügen

**Position:** Nach Zeile 429 (direkt nach spawn_playwright_session_agent() Wrapper)  
**File:** `src/ui/gui_interface.py`

**Einfügen:**

```python
    def spawn_mcp_session_agent(self, tool: str, session_id: str | None = None, ui_host: str | None = None, ui_port: int | None = None, keepalive: bool = True, **kwargs) -> Dict[str, Any]:
        """Spawn MCP agent subprocess for any tool (generic method).
        
        Args:
            tool: Tool name ('github', 'docker', 'playwright', etc.)
            session_id: Optional session ID (generated if None)
            ui_host/ui_port: UI server coordinates
            keepalive: Keep agent running after task
            **kwargs: Tool-specific args
        """
        try:
            # Validate tool
            if tool not in MCP_TOOL_AGENT_PATHS:
                return {'success': False, 'error': f'Unsupported tool: {tool}. Supported: {list(MCP_TOOL_AGENT_PATHS.keys())}'}
            
            # Resolve agent path
            base = Path(__file__).resolve().parents[1]
            agent_path = base / MCP_TOOL_AGENT_PATHS[tool]
            if not agent_path.is_file():
                return {'success': False, 'error': f'Agent not found: {agent_path}'}
            
            # Generate secure session ID
            import secrets
            sid = session_id or secrets.token_urlsafe(16)
            session_logger = setup_session_logging(sid)
            session_logger.info(f"Spawning {tool} agent: {sid}")
            
            # Build command
            args = [sys.executable, '-u', str(agent_path), '--session-id', sid]
            if keepalive:
                args.append('--keepalive')
            if ui_host:
                args.extend(['--ui-host', str(ui_host)])
            if ui_port:
                args.extend(['--ui-port', str(int(ui_port))])
            
            # Tool-specific args
            for key, value in kwargs.items():
                if value is not None:
                    args.extend([f'--{key.replace("_", "-")}', str(value)])
            
            # Spawn process
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            session_logger.info(f"{tool} agent started (PID: {proc.pid})")
            self.broadcast_event(f'{tool}.session.started', {'session_id': sid, 'pid': proc.pid, 'tool': tool})
            
            # Stdout reader thread
            def _reader():
                try:
                    for line in iter(proc.stdout.readline, ''):
                        ln = line.strip()
                        if not ln:
                            continue
                        session_logger.info(f"Agent: {ln}")
                        self.broadcast_event(f'{tool}.session.log', {'session_id': sid, 'line': ln, 'tool': tool})
                        
                        # Parse SESSION_ANNOUNCE
                        if ln.startswith('SESSION_ANNOUNCE '):
                            try:
                                payload = json.loads(ln[17:])
                                host = str(payload.get('host', '127.0.0.1'))
                                port = int(payload.get('port', 8787))
                                with self._mcp_sessions_lock:
                                    if sid in self._mcp_sessions:
                                        self._mcp_sessions[sid].update({'host': host, 'port': port, 'connected': True})
                                session_logger.info(f"Upstream: {host}:{port}")
                            except Exception as e:
                                session_logger.error(f"SESSION_ANNOUNCE parse failed: {e}")
                except Exception as e:
                    session_logger.error(f"Reader error: {e}")
            
            threading.Thread(target=_reader, name=f'{tool}Reader-{sid}', daemon=True).start()
            
            # Try .event_port discovery (GitHub)
            try:
                if TMP_DIR:
                    event_port_file = TMP_DIR / '.event_port'
                    if event_port_file.exists():
                        time.sleep(0.5)
                        port_discovered = int(event_port_file.read_text().strip())
                        with self._mcp_sessions_lock:
                            if sid in self._mcp_sessions:
                                self._mcp_sessions[sid].update({'host': '127.0.0.1', 'port': port_discovered, 'connected': True})
                        session_logger.info(f"Port from .event_port: {port_discovered}")
            except Exception:
                pass
            
            return {'success': True, 'session_id': sid, 'pid': proc.pid, 'tool': tool}
        except Exception as e:
            logger.error(f"Spawn {tool} failed: {e}")
            return {'success': False, 'error': str(e), 'tool': tool}

```

---

## Schritt 2: create_mcp_session() + get_all_mcp_sessions() hinzufügen

**Position:** Nach Zeile 611 (direkt vor `class _ReloadEventHandler`)

**Einfügen:**

```python
    def create_mcp_session(self, tool: str, name: str, model: str = "gpt-4", config: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Create MCP session for any tool."""
        try:
            if tool not in MCP_TOOL_AGENT_PATHS:
                return {'success': False, 'error': f'Unsupported tool: {tool}'}
            
            import secrets
            session_id = secrets.token_urlsafe(16)
            
            with self._mcp_sessions_lock:
                self._mcp_sessions[session_id] = {
                    'session_id': session_id,
                    'tool': tool,
                    'name': name,
                    'model': model,
                    'status': 'stopped',
                    'connected': False,
                    'host': None,
                    'port': None,
                    'agent_proc': None,
                    'agent_pid': None,
                    'agent_running': False,
                    'created_at': time.time(),
                    'config': config or {},
                }
                
                setup_session_logging(session_id).info(f"Created {tool} session: {name}")
                self.broadcast_event('mcp.session.created', {'session_id': session_id, 'tool': tool, 'name': name})
                
                return {
                    'success': True,
                    'session': {
                        'session_id': session_id,
                        'tool': tool,
                        'name': name,
                        'status': 'stopped'
                    }
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_all_mcp_sessions(self, tool_filter: str | None = None) -> Dict[str, Any]:
        """Get all MCP sessions, optionally filtered by tool."""
        try:
            with self._mcp_sessions_lock:
                sessions = []
                for sid, sess in self._mcp_sessions.items():
                    if tool_filter and sess.get('tool') != tool_filter:
                        continue
                    
                    proc = sess.get('agent_proc')
                    running = bool(proc and proc.poll() is None)
                    
                    sessions.append({
                        'session_id': sid,
                        'tool': sess.get('tool', 'unknown'),
                        'name': sess.get('name', f'Session {sid[:8]}'),
                        'model': sess.get('model', 'gpt-4'),
                        'status': sess.get('status', 'stopped'),
                        'connected': sess.get('connected', False),
                        'host': sess.get('host'),
                        'port': sess.get('port'),
                        'agent_running': running,
                        'created_at': sess.get('created_at'),
                    })
                
                return {'success': True, 'sessions': sessions}
        except Exception as e:
            return {'success': False, 'error': str(e)}

```

---

## Schritt 3: API Endpoint POST /api/mcp/sessions

**Position:** In `do_POST()`, vor Zeile 2252 (vor finalem 404)

**Einfügen:**

```python
        # --- Phase 5-6: Generic MCP session creation ---
        if self.path == "/api/mcp/sessions":
            try:
                tool = (data.get("tool") or "").strip()
                name = (data.get("name") or "").strip()
                model = (data.get("model") or "gpt-4").strip()
                
                if not tool:
                    self._json(400, {"success": False, "error": "'tool' is required"})
                    return
                if not name:
                    self._json(400, {"success": False, "error": "'name' is required"})
                    return
                
                result = self.server.create_mcp_session(tool=tool, name=name, model=model)
                self._json(200, result)
            except Exception as e:
                self._json(500, {"success": False, "error": f"Failed to create session: {e}"})
            return
        
        # Tool-specific shortcuts
        if self.path == "/api/github/sessions":
            try:
                name = (data.get("name") or "").strip()
                if not name:
                    self._json(400, {"success": False, "error": "'name' is required"})
                    return
                result = self.server.create_mcp_session(tool='github', name=name, model=data.get("model", "gpt-4"))
                self._json(200, result)
            except Exception as e:
                self._json(500, {"success": False, "error": str(e)})
            return
        
        if self.path == "/api/docker/sessions":
            try:
                name = (data.get("name") or "").strip()
                if not name:
                    self._json(400, {"success": False, "error": "'name' is required"})
                    return
                result = self.server.create_mcp_session(tool='docker', name=name, model=data.get("model", "gpt-4"))
                self._json(200, result)
            except Exception as e:
                self._json(500, {"success": False, "error": str(e)})
            return

```

---

## Schritt 4: API Endpoint GET /api/mcp/sessions

**Position:** In `do_GET()`, Zeile 1590-1605 **ERSETZEN**

**Aktuell (Zeile 1590-1605):**
```python
        if self.path == "/api/sessions":
            try:
                sessions_result = self.server.get_all_playwright_sessions()
                # ...
```

**Ersetzen durch:**
```python
        if self.path == "/api/sessions":
            try:
                sessions_result = self.server.get_all_mcp_sessions()  # Phase 5: ALL tools
                # Extract sessions array from the result
                if isinstance(sessions_result, dict) and sessions_result.get('success') and 'sessions' in sessions_result:
                    sessions = sessions_result['sessions']
                else:
                    sessions = []
                self._json(200, {"sessions": sessions})
            except Exception as e:
                self._json(200, {"sessions": [], "error": f"Failed: {e}"})
            return
```

---

## Schritt 5: Event-Proxy für GitHub - GET /mcp/github/session/{id}/events

**Position:** In `do_GET()`, vor Zeile 1975 (vor finalem 404)

**Einfügen:**

```python
        # --- Phase 7: Generic tool event proxies /mcp/{tool}/session/{id}/* ---
        if self.path.startswith("/mcp/") and "/session/" in self.path:
            # Parse: /mcp/{tool}/session/{session_id}/{endpoint}
            parts = self.path.split("/")
            if len(parts) >= 5 and parts[1] == "mcp" and parts[3] == "session":
                tool_name = parts[2]  # github, docker, etc.
                session_id = parts[4]
                endpoint = "/" + "/".join(parts[5:]) if len(parts) > 5 else "/"
                
                # Get session to find upstream host/port
                try:
                    with self.server._mcp_sessions_lock:
                        if session_id not in self.server._mcp_sessions:
                            self._json(404, {"error": f"Session {session_id} not found"})
                            return
                        session = self.server._mcp_sessions[session_id]
                        upstream_host = session.get('host', '127.0.0.1')
                        upstream_port = session.get('port', 8787)
                    
                    # Proxy SSE events
                    if endpoint == "/events" or endpoint.startswith("/events"):
                        import http.client
                        conn = http.client.HTTPConnection(upstream_host, upstream_port, timeout=10)
                        conn.request("GET", endpoint, headers={"Accept": "text/event-stream"})
                        resp = conn.getresponse()
                        
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.send_header("Cache-Control", "no-cache")
                        self.end_headers()
                        
                        while True:
                            chunk = resp.read(1024)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            self.wfile.flush()
                        return
                    
                    # Proxy JSON/health
                    elif endpoint.endswith(".json") or endpoint == "/health":
                        import urllib.request
                        url = f"http://{upstream_host}:{upstream_port}{endpoint}"
                        req = urllib.request.Request(url)
                        with self._fetch_with_backoff(req, timeout=2.5) as r:
                            body = r.read()
                            self.send_response(200)
                            self.send_header("Content-Type", r.headers.get("Content-Type", "application/json"))
                            self.send_header("Content-Length", str(len(body)))
                            self.end_headers()
                            self.wfile.write(body)
                        return
                
                except Exception as e:
                    self._json(502, {"error": f"Proxy failed: {e}"})
                    return

```

---

## Schritt 6: GitHub Clarification File Handling

**Position:** Nach allen Methoden in `_AssistantHTTPServer`, vor `class _ReloadEventHandler`

**Einfügen:**

```python
    def handle_user_clarification_response(self, correlation_id: str, response: str) -> Dict[str, Any]:
        """Handle user response to clarification request (für GitHub Agent)."""
        try:
            if not TMP_DIR:
                return {'success': False, 'error': 'TMP_DIR not configured'}
            
            # Write atomic
            response_file = TMP_DIR / f'clarification_{correlation_id}.txt'
            response_file.write_text(response, encoding='utf-8')
            
            logger.info(f"Clarification response written: {correlation_id}")
            return {'success': True, 'file': str(response_file)}
        except Exception as e:
            logger.error(f"Failed to write clarification: {e}")
            return {'success': False, 'error': str(e)}

```

---

## Schritt 7: API Endpoint POST /api/mcp/clarification

**Position:** In `do_POST()`, vor Zeile 2252

**Einfügen:**

```python
        # --- Phase 8: GitHub User Clarification Response ---
        if self.path == "/api/mcp/clarification":
            try:
                correlation_id = (data.get("correlation_id") or "").strip()
                response = (data.get("response") or "").strip()
                
                if not correlation_id:
                    self._json(400, {"success": False, "error": "'correlation_id' required"})
                    return
                if not response:
                    self._json(400, {"success": False, "error": "'response' required"})
                    return
                
                result = self.server.handle_user_clarification_response(correlation_id, response)
                self._json(200, result)
            except Exception as e:
                self._json(500, {"success": False, "error": str(e)})
            return

```

---

## Schritt 8: Teste GitHub Agent Spawn

**Terminal-Befehl:**

```bash
# Test 1: Create GitHub session
curl -X POST http://localhost:8765/api/mcp/sessions \
  -H "Content-Type: application/json" \
  -d '{"tool":"github","name":"Test GitHub Session","model":"gpt-4"}'

# Response: {"success":true,"session":{"session_id":"xyz...","tool":"github",...}}

# Test 2: Start session (mit session_id aus Test 1)
curl -X POST http://localhost:8765/api/sessions/xyz.../start

# Test 3: Check events (SSE)
curl http://localhost:8765/mcp/github/session/xyz.../events

# Erwartung: user.clarification.request Events erscheinen!
```

---

## Schritt 9: Frontend Clarification Response

**Position:** In `do_POST()`, die Clarification-Response bereits in Schritt 7 hinzugefügt

**Frontend Code (bereits in MCPSessionViewer.tsx):**

```typescript
// Modal sendet User-Antwort:
const response = await fetch('/api/mcp/clarification', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    correlation_id: clarificationData.correlation_id,
    response: userInput
  })
});
```

---

## Schritt 10: End-to-End Test

**Test-Szenario:**

1. Frontend öffnet GitHub Tool → MCPSessionViewer
2. MCPSessionViewer created Session via `POST /api/github/sessions`
3. Startet Session via `POST /api/sessions/{id}/start`
4. EventSource connected zu `/mcp/github/session/{id}/events`
5. GitHub Agent generiert `user.clarification.request`
6. Frontend zeigt Modal
7. User gibt Antwort ein
8. Frontend sendet `POST /api/mcp/clarification`
9. GitHub Agent liest File und fährt fort

---

## 🚀 Ausführung

**Jetzt kannst du:**

**Option A:** Schritte 1-7 manuell durchführen (Copy-Paste in VSCode)

**Option B:** Ich führe mit Orchestrator-Mode aus (erstelle Sub-Task für jeden Schritt)

**Option C:** Ich implementiere Schritt für Schritt in dieser Session

**Welche Option?**