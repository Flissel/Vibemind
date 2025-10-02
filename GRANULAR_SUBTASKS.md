# Granulare Sub-Tasks: GitHub User Clarification Modal Integration

**Basis:** [`MANUAL_REFACTORING_GUIDE.md`](MANUAL_REFACTORING_GUIDE.md)  
**Ziel:** Vollständige Implementierung mit testbaren Arbeitseinheiten  
**Datei:** [`src/ui/gui_interface.py`](src/ui/gui_interface.py) (aktuell 2934 Zeilen nach Sub-Task 1.1)

---

## 🎯 Granulare Sub-Task Breakdown

### ✅ Sub-Task 1.1: spawn_mcp_session_agent() - Core Implementation (COMPLETE)

**Status:** ✅ Abgeschlossen  
**Zeilen:** 431-540  
**Commit:** Ausstehend

**Input:**
- [`spawn_playwright_session_agent()`](src/ui/gui_interface.py:424) Wrapper vorhanden
- [`MCP_TOOL_AGENT_PATHS`](src/ui/gui_interface.py:48) Konstante verfügbar

**Output:**
- [`spawn_mcp_session_agent(tool, session_id, ...)`](src/ui/gui_interface.py:431) Methode
- 110 Zeilen Code

**Implementierte Features:**
1. ✅ Tool-Validierung gegen MCP_TOOL_AGENT_PATHS
2. ✅ Secure Session ID via `secrets.token_urlsafe(16)`
3. ✅ subprocess.Popen mit stdout reader Thread
4. ✅ SESSION_ANNOUNCE JSON Parsing
5. ✅ .event_port File Discovery (GitHub-ready)
6. ✅ Tool-spezifische Events: `{tool}.session.started`, `{tool}.session.log`

**Test:** `python -m py_compile src/ui/gui_interface.py` → Exit 0 ✅

---

### ⏳ Sub-Task 2.1: create_mcp_session() - Session Creation

**Status:** ⏳ In Progress (Sub-Task erstellt, Fehler beim Einfügen)  
**Zeilen:** Nach 610 einfügen  
**Geschätzt:** +40 Zeilen

**Input:**
- [`_mcp_sessions`](src/ui/gui_interface.py:238) Dictionary
- [`MCP_TOOL_AGENT_PATHS`](src/ui/gui_interface.py:48) für Validierung
- MANUAL_REFACTORING_GUIDE.md Schritt 2

**Aktion:**
Nach Zeile 610 (vor `class _ReloadEventHandler`) einfügen:

```python
def create_mcp_session(self, tool: str, name: str, model: str = "gpt-4", config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Create MCP session for any tool."""
    # [40 Zeilen Code aus Guide]
```

**Output:**
- Methode bei Zeile ~611-650
- Session-Entry in `_mcp_sessions` mit 12 Feldern
- SSE Event: `'mcp.session.created'`

**Prüfkriterien:**
1. ✅ Tool in MCP_TOOL_AGENT_PATHS validiert
2. ✅ Session ID: `secrets.token_urlsafe(16)`
3. ✅ Thread-Safety: `with self._mcp_sessions_lock:`
4. ✅ Session Structure: session_id, tool, name, model, status, connected, host, port, agent_proc, agent_pid, agent_running, created_at, config
5. ✅ Event gebroadcastet mit tool, name, session_id
6. ✅ Returns {'success': True, 'session': {...}}

**Test:**
```bash
python -m py_compile src/ui/gui_interface.py && echo "Syntax OK"
```

---

### ⏳ Sub-Task 2.2: get_all_mcp_sessions() - Session Retrieval

**Status:** Pending  
**Zeilen:** Nach create_mcp_session() (~651)  
**Geschätzt:** +25 Zeilen

**Input:**
- [`_mcp_sessions`](src/ui/gui_interface.py:238) Dictionary populated
- tool_filter Parameter (optional)

**Aktion:**
Nach create_mcp_session() einfügen:

```python
def get_all_mcp_sessions(self, tool_filter: str | None = None) -> Dict[str, Any]:
    """Get all MCP sessions, optionally filtered by tool."""
    # [25 Zeilen aus Guide]
```

**Output:**
- Methode bei ~Zeile 651-675
- Returns sessions array

**Prüfkriterien:**
1. ✅ tool_filter=None → alle Sessions
2. ✅ tool_filter='github' → nur GitHub Sessions
3. ✅ proc.poll() wird geprüft für running status
4. ✅ Thread-Safety via Lock
5. ✅ Sessions enthalten: session_id, tool, name, model, status, connected, host, port, agent_running, created_at

**Test:**
```python
# In Python REPL:
server.create_mcp_session('github', 'Test')
result = server.get_all_mcp_sessions()
assert result['success'] == True
assert len(result['sessions']) > 0
assert result['sessions'][0]['tool'] == 'github'
```

---

### Sub-Task 3.1: POST /api/mcp/sessions Endpoint

**Status:** Pending  
**Zeilen:** In do_POST(), vor Zeile 2252  
**Geschätzt:** +20 Zeilen

**Input:**
- Request body: `{"tool": "github", "name": "My Session", "model": "gpt-4"}`
- `create_mcp_session()` Methode verfügbar

**Aktion:**
In `do_POST()`, vor Zeile 2252 (finaler 404) einfügen:

```python
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
```

**Output:**
- HTTP 200: `{"success": true, "session": {"session_id": "...", "tool": "github", ...}}`
- HTTP 400: Wenn tool oder name fehlt
- HTTP 500: Bei Server-Fehlern

**Prüfkriterien:**
1. ✅ Validiert tool + name Parameter
2. ✅ Ruft create_mcp_session() auf
3. ✅ Returns JSON mit session_id
4. ✅ Error-Handling für ungültige Tools

**Test:**
```bash
curl -X POST http://localhost:8765/api/mcp/sessions \
  -H "Content-Type: application/json" \
  -d '{"tool":"github","name":"Test Session"}'
  
# Expected: {"success":true,"session":{"session_id":"...","tool":"github",...}}
```

---

### Sub-Task 3.2: POST /api/github/sessions Shortcut

**Status:** Pending  
**Zeilen:** Nach Sub-Task 3.1  
**Geschätzt:** +15 Zeilen

**Input:**
- Request body: `{"name": "My GitHub Session"}`
- Keine `tool` nötig (implizit 'github')

**Aktion:**
Nach POST /api/mcp/sessions einfügen:

```python
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
```

**Output:**
- HTTP 200: Session mit tool='github'

**Prüfkriterien:**
1. ✅ Tool automatisch 'github'
2. ✅ Nur 'name' erforderlich
3. ✅ Model optional (default: gpt-4)

**Test:**
```bash
curl -X POST http://localhost:8765/api/github/sessions \
  -H "Content-Type: application/json" \
  -d '{"name":"Quick GitHub Session"}'
```

---

### Sub-Task 3.3: POST /api/docker/sessions + desktop/sessions Shortcuts

**Status:** Pending  
**Zeilen:** Nach Sub-Task 3.2  
**Geschätzt:** +30 Zeilen (2x 15)

**Input:**
- Gleiche Pattern wie github/sessions
- Tools: 'docker', 'desktop'

**Aktion:**
Dupliziere Pattern für docker und desktop

**Prüfkriterien:**
1. ✅ /api/docker/sessions → tool='docker'
2. ✅ /api/desktop/sessions → tool='desktop'
3. ✅ Konsistentes Error-Handling

---

### Sub-Task 4.1: GET /api/sessions Aktualisieren

**Status:** Pending  
**Zeilen:** 1590-1605 ERSETZEN  
**Geschätzt:** -5 Zeilen (Vereinfachung)

**Input:**
- Aktuelle Zeile 1592: `sessions_result = self.server.get_all_playwright_sessions()`

**Aktion:**
ERSETZE Zeile 1592:
```python
# ALT:
sessions_result = self.server.get_all_playwright_sessions()

# NEU:
sessions_result = self.server.get_all_mcp_sessions()  # Phase 5: ALL tools
```

**Output:**
- GET /api/sessions returned jetzt ALLE Tools (github, docker, playwright, etc.)

**Prüfkriterien:**
1. ✅ Kein tool_filter → alle Sessions
2. ✅ Sessions array enthält gemischte Tools
3. ✅ Backward-Compat: Playwright-Sessions weiterhin enthalten

**Test:**
```bash
curl http://localhost:8765/api/sessions
# Expected: {"sessions":[{"tool":"github",...},{"tool":"playwright",...}]}
```

---

### Sub-Task 5.1: Generic Event Proxy /mcp/{tool}/session/{id}/*

**Status:** Pending  
**Zeilen:** In do_GET(), vor Zeile 1975  
**Geschätzt:** +60 Zeilen

**Input:**
- Path pattern: `/mcp/github/session/xyz123/events`
- Session muss host/port haben

**Aktion:**
Vor Zeile 1975 einfügen: Generic tool proxy handler

**Output:**
- SSE Proxy für `/mcp/{tool}/session/{id}/events`
- JSON Proxy für `/mcp/{tool}/session/{id}/events.json`
- Health Proxy für `/mcp/{tool}/session/{id}/health`

**Prüfkriterien:**
1. ✅ Path-Parsing: tool, session_id, endpoint extrahiert
2. ✅ Session-Lookup in _mcp_sessions
3. ✅ Upstream host/port aus Session
4. ✅ http.client.HTTPConnection für SSE
5. ✅ urllib für JSON/Health
6. ✅ Error: 404 wenn Session nicht gefunden

**Test:**
```bash
# Voraussetzung: GitHub session created + started
curl http://localhost:8765/mcp/github/session/{session_id}/events
# Expected: SSE stream mit user.clarification.request events
```

---

### Sub-Task 6.1: handle_user_clarification_response() Methode

**Status:** Pending  
**Zeilen:** Nach get_all_mcp_sessions() (~676)  
**Geschätzt:** +15 Zeilen

**Input:**
- correlation_id: String
- response: User's answer String
- TMP_DIR global variable

**Aktion:**
```python
def handle_user_clarification_response(self, correlation_id: str, response: str) -> Dict[str, Any]:
    """Handle user response to clarification request (für GitHub Agent)."""
    try:
        if not TMP_DIR:
            return {'success': False, 'error': 'TMP_DIR not configured'}
        response_file = TMP_DIR / f'clarification_{correlation_id}.txt'
        response_file.write_text(response, encoding='utf-8')
        logger.info(f"Clarification response written: {correlation_id}")
        return {'success': True, 'file': str(response_file)}
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

**Output:**
- File: `data/tmp/clarification_{correlation_id}.txt`
- Content: User's response text

**Prüfkriterien:**
1. ✅ Atomic write (keine Race Conditions)
2. ✅ UTF-8 encoding
3. ✅ File-Path korrekt: TMP_DIR/clarification_{correlation_id}.txt
4. ✅ Returns success status

**Test:**
```python
result = server.handle_user_clarification_response('test123', 'User/Repo123')
assert result['success'] == True
assert Path(result['file']).exists()
assert Path(result['file']).read_text() == 'User/Repo123'
```

---

### Sub-Task 7.1: POST /api/mcp/clarification Endpoint

**Status:** Pending  
**Zeilen:** In do_POST(), nach Sub-Task 3.x  
**Geschätzt:** +18 Zeilen

**Input:**
- Request body: `{"correlation_id": "xyz", "response": "User answer"}`
- `handle_user_clarification_response()` Methode

**Aktion:**
```python
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

**Output:**
- HTTP 200: `{"success": true, "file": "data/tmp/clarification_xyz.txt"}`

**Prüfkriterien:**
1. ✅ Validiert correlation_id + response
2. ✅ Ruft handle_user_clarification_response() auf
3. ✅ Returns file path
4. ✅ GitHub Agent kann File lesen

**Test:**
```bash
curl -X POST http://localhost:8765/api/mcp/clarification \
  -H "Content-Type: application/json" \
  -d '{"correlation_id":"test123","response":"UserName/RepoName"}'
  
# Expected: {"success":true,"file":"...clarification_test123.txt"}
# Verify: ls data/tmp/clarification_test123.txt
```

---

### Sub-Task 8.1: GitHub Agent Spawn Integration Test

**Status:** Pending  
**Abhängigkeiten:** Sub-Tasks 1-3 complete  
**Geschätzt:** 15 Min Testing

**Input:**
- Alle Backend-Methoden implementiert
- GitHub Agent existiert: [`src/MCP PLUGINS/servers/github/agent.py`](src/MCP PLUGINS/servers/github/agent.py)

**Aktion:**
1. Create GitHub session via API
2. Start session via API  
3. Verify EventServer started
4. Check .event_port file created

**Test-Sequenz:**
```bash
# 1. Create
SESSION_JSON=$(curl -s -X POST http://localhost:8765/api/github/sessions \
  -H "Content-Type: application/json" \
  -d '{"name":"Test GitHub"}')
SESSION_ID=$(echo $SESSION_JSON | jq -r '.session.session_id')
echo "Created: $SESSION_ID"

# 2. Start
curl -X POST http://localhost:8765/api/sessions/$SESSION_ID/start

# 3. Warte 2 Sekunden
sleep 2

# 4. Check .event_port
cat data/tmp/.event_port
# Expected: Port-Nummer (z.B. 8787)

# 5. Check EventServer
curl http://127.0.0.1:$(cat data/tmp/.event_port)/health
# Expected: "ok"
```

**Prüfkriterien:**
1. ✅ GitHub Agent Prozess läuft (ps | grep github/agent.py)
2. ✅ .event_port File existiert
3. ✅ EventServer antwortet auf /health
4. ✅ Logs in data/logs/sessions/{session_id}.log

---

### Sub-Task 9.1: Frontend Event-Routing Verify

**Status:** Pending  
**Abhängigkeiten:** Sub-Task 5.1, 8.1  
**Geschätzt:** 10 Min Testing

**Input:**
- Running GitHub session
- Frontend MCPSessionViewer open

**Aktion:**
1. Frontend verbindet zu `/mcp/github/session/{id}/events`
2. Trigger user.clarification.request im Agent
3. Verify Modal öffnet

**Test:**
- Browser DevTools → Network tab
- EventSource connection zu `/mcp/github/session/...`
- Expect: `event: user.clarification.request`

**Prüfkriterien:**
1. ✅ EventSource connected
2. ✅ Events durchgeleitet (backend → frontend)
3. ✅ Modal erscheint bei user.clarification.request
4. ✅ correlation_id korrekt übertragen

---

### Sub-Task 10.1: User Clarification Response Flow

**Status:** Pending  
**Abhängigkeiten:** Sub-Task 6-9 complete  
**Geschätzt:** 10 Min Testing

**Input:**
- Modal zeigt Frage an
- User gibt Antwort ein

**Aktion:**
1. User tippt Antwort in Modal
2. Frontend sendet POST /api/mcp/clarification
3. Backend schreibt File
4. GitHub Agent pollt File
5. Agent liest response und fährt fort

**Test:**
Full End-to-End:
```
1. GitHub Agent fragt: "Welcher Repository?"
2. Frontend zeigt Modal mit Frage
3. User tippt: "Flissel/Vibemind"
4. Frontend: POST /api/mcp/clarification {correlation_id, response}
5. Backend: Write data/tmp/clarification_{id}.txt
6. Agent: Poll → Read → Process
7. Agent: Fährt mit Task fort
```

**Prüfkriterien:**
1. ✅ File wird geschrieben
2. ✅ Agent liest File innerhalb 5 Sekunden
3. ✅ Agent-Logs zeigen: "📝 Received user answer: Flissel/Vibemind"
4. ✅ Modal schließt automatisch
5. ✅ Agent completed Task ohne Loop

---

## 📊 Zusammenfassung

**Total Sub-Tasks:** 10  
**Completed:** 1 (Sub-Task 1.1) ✅  
**In Progress:** 1 (Sub-Task 2.1) ⏳  
**Pending:** 8

**Geschätzte Implementierungszeit:**
- Sub-Tasks 2-7: 30-45 Min (Code-Einfügungen)
- Sub-Tasks 8-10: 30-45 Min (Testing & Debugging)
- **Total:** 1-1.5 Stunden

**Nächster Schritt:** Sub-Task 2.1 abschließen (create_mcp_session einfügen)