// ... existing code ...
# MCP Session Refactoring - Detaillierte Analyse

**Datum:** 2025-10-02  
**Ziel:** Generalisierung des Session-Managements von Playwright-only zu Multi-Tool MCP-Support  
**Status:** Phase 1 - Analyse & Vorbereitung

---

## 📊 Datei-Übersicht

- **Datei:** `src/ui/gui_interface.py`
- **Größe:** 3030 Zeilen, 147.4 KB
- **Backup:** `src/ui/gui_interface.py.backup` ✅
- **Hauptklassen:** 
  - `_AssistantHTTPServer` (Zeile 200-817)
  - `_GUIRequestHandler` (Zeile 857-2458)
  - `GUIInterface` (Zeile 2461-3030)

---

## 🔍 Identifizierte Playwright-spezifische Methoden

### In `_AssistantHTTPServer`:

| Methode | Zeilen | Funktion | Refactoring-Bedarf |
|---------|--------|----------|-------------------|
| `set_playwright_session_upstream()` | 311-340 | Legacy single-session upstream | → `set_mcp_session_upstream()` |
| `get_playwright_session_status()` | 342-366 | Legacy single-session status | → `get_mcp_session_status()` |
| `stop_playwright_session_agent()` | 368-407 | Legacy single-session stop | → `stop_mcp_session_agent()` |
| `spawn_playwright_session_agent()` | 409-497 | **KRITISCH**: Spawn mit SESSION_ANNOUNCE | → `spawn_mcp_session_agent(tool, ...)` |
| `start_playwright_session_agent()` | 500-501 | Backward-compat alias | Behalten als Wrapper |
| `create_playwright_session()` | 504-553 | Multi-session: Create entry | → `create_mcp_session(tool, ...)` |
| `get_playwright_session_status_by_id()` | 555-584 | Multi-session: Get status | → `get_mcp_session_status_by_id()` |
| `spawn_playwright_session_by_id()` | 586-616 | Multi-session: Spawn agent | → `spawn_mcp_session_by_id()` |
| `stop_playwright_session_by_id()` | 618-662 | Multi-session: Stop agent | → `stop_mcp_session_by_id()` |
| `start_playwright_session_by_id()` | 664-709 | Multi-session: Start agent | → `start_mcp_session_by_id()` |
| `delete_playwright_session_by_id()` | 711-733 | Multi-session: Delete session | → `delete_mcp_session_by_id()` |
| `set_playwright_session_upstream_by_id()` | 735-759 | Multi-session: Set upstream | → `set_mcp_session_upstream_by_id()` |
| `get_all_playwright_sessions()` | 761-793 | Multi-session: List all | → `get_all_mcp_sessions()` |
| `delete_playwright_session()` | 795-817 | Duplicate of `delete_by_id` | Entfernen (Deduplizierung) |

### Session Dictionary (Zeile 223-224):

```python
# AKTUELL (Playwright-only):
self._playwright_sessions: Dict[str, Dict[str, Any]] = {}
self._playwright_sessions_lock = threading.Lock()

# ZIEL (Multi-Tool):
self._mcp_sessions: Dict[str, Dict[str, Any]] = {}
self._mcp_sessions_lock = threading.Lock()
```

---

## 🗺️ Tool-Agent-Pfade Mapping

### Verfügbare MCP-Tools:

| Tool | Agent-Pfad | Status | Event-Support | UI-Support |
|------|-----------|--------|---------------|-----------|
| **github** | `MCP PLUGINS/servers/github/agent.py` | ✅ Vorhanden | ✅ EventServer + .event_port | ❌ Kein public/ |
| **docker** | `MCP PLUGINS/servers/docker/agent.py` | ✅ Vorhanden | 🔍 Zu prüfen | 🔍 Zu prüfen |
| **desktop** | `MCP PLUGINS/servers/desktop/agent.py` | ✅ Vorhanden | 🔍 Zu prüfen | 🔍 Zu prüfen |
| **playwright** | `MCP PLUGINS/servers/playwright/agent.py` | ✅ Vorhanden | ✅ EventServer + .event_port | ✅ public/ |
| **context7** | `MCP PLUGINS/servers/context7/` | ✅ Vorhanden | 🔍 Zu prüfen | 🔍 Zu prüfen |
| **redis** | `MCP PLUGINS/servers/redis/` | ✅ Vorhanden | 🔍 Zu prüfen | 🔍 Zu prüfen |
| **supabase** | `MCP PLUGINS/servers/supabase/` | ✅ Vorhanden | 🔍 Zu prüfen | 🔍 Zu prüfen |
| **cloudflare** | `MCP PLUGINS/servers/cloudflare/` | ✅ Vorhanden | 🔍 Zu prüfen | 🔍 Zu prüfen |
| **travliy** | `MCP PLUGINS/servers/travliy/` | ✅ Vorhanden | 🔍 Zu prüfen | 🔍 Zu prüfen |
| **windows-automation** | `MCP PLUGINS/servers/windows-automation/` | ✅ Vorhanden | 🔍 Zu prüfen | 🔍 Zu prüfen |

### Agent-Pfad Konstanten (Zu implementieren):

```python
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
```

---

## 🏗️ Session-Schema Dokumentation

### Aktuelles Playwright-Session-Schema:

```python
{
    'session_id': str,           # UUID
    'name': str,                 # User-friendly name
    'model': str,                # LLM model (default: 'gpt-4')
    'tools': list,               # Tools list (default: ['playwright'])
    'status': str,               # 'stopped' | 'starting' | 'running'
    'connected': bool,           # Upstream connection status
    'host': str | None,          # Upstream EventServer host
    'port': int | None,          # Upstream EventServer port
    'agent_proc': subprocess.Popen | None,  # Agent process
    'agent_pid': int | None,     # Agent PID
    'agent_running': bool,       # Process running status
    'created_at': float,         # Unix timestamp
}
```

### Geplantes Multi-Tool MCP-Session-Schema:

```python
{
    # --- Basis-Felder (alle Tools) ---
    'session_id': str,           # UUID (cryptographically secure)
    'tool': str,                 # 'github' | 'docker' | 'playwright' | ...
    'name': str,                 # User-friendly name
    'model': str,                # LLM model (tool-specific default)
    'status': str,               # 'stopped' | 'starting' | 'running' | 'error'
    'created_at': float,         # Unix timestamp
    'updated_at': float,         # Last status update
    
    # --- EventServer-Felder (wenn Tool EventServer unterstützt) ---
    'connected': bool,           # Upstream connection status
    'host': str | None,          # Upstream EventServer host
    'port': int | None,          # Upstream EventServer port
    'event_port_file': str | None,  # Path zu .event_port Datei
    
    # --- Prozess-Management-Felder ---
    'agent_proc': subprocess.Popen | None,  # Agent process
    'agent_pid': int | None,     # Agent PID
    'agent_running': bool,       # Process running status
    'agent_start_time': float | None,  # Process start timestamp
    'agent_cmd': list | None,    # Full command used to spawn agent
    
    # --- Tool-spezifische Felder ---
    'tools': list | None,        # Für multi-tool agents (z.B. Playwright)
    'config': dict | None,       # Tool-spezifische Konfiguration
    'metadata': dict | None,     # Zusätzliche Metadaten
    
    # --- Health & Monitoring ---
    'last_heartbeat': float | None,  # Last health check timestamp
    'error_count': int,          # Consecutive error count
    'last_error': str | None,    # Last error message
}
```

---

## 🔗 Abhängigkeiten-Graph

### Methodenaufruf-Hierarchie:

```
spawn_mcp_session_agent() [NEUE GENERIC]
  ├─> Validiert tool-Parameter
  ├─> Löst Agent-Pfad aus MCP_TOOL_AGENT_PATHS auf
  ├─> Baut tool-spezifische Args (--session-id, --ui-host, etc.)
  ├─> subprocess.Popen() mit stdout-Reader
  ├─> Parst SESSION_ANNOUNCE aus Agent-Output
  ├─> Liest .event_port Datei (falls vorhanden)
  └─> Ruft set_mcp_session_upstream_by_id() auf

spawn_playwright_session_agent() [WRAPPER für Backward-Compat]
  └─> spawn_mcp_session_agent('playwright', ...)

create_mcp_session(tool, name, model, ...) [NEUE GENERIC]
  ├─> Generiert cryptographically secure session_id
  ├─> Erstellt Session-Entry im _mcp_sessions Dict
  ├─> Broadcast SSE: 'mcp.session.created'
  └─> Return session_id

start_mcp_session_by_id(session_id) [NEUE GENERIC]
  ├─> Validiert session_id in _mcp_sessions
  ├─> Liest 'tool' aus Session-Entry
  ├─> Ruft spawn_mcp_session_agent(tool, session_id) auf
  ├─> Updated Session-Status: 'starting' → 'running'
  └─> Broadcast SSE: 'mcp.session.started'

stop_mcp_session_by_id(session_id) [NEUE GENERIC]
  ├─> Validiert session_id in _mcp_sessions
  ├─> proc.terminate() / proc.kill()
  ├─> Updated Session-Status: 'stopped'
  └─> Broadcast SSE: 'mcp.session.stopped'

delete_mcp_session_by_id(session_id) [NEUE GENERIC]
  ├─> Ruft stop_mcp_session_by_id() auf (falls running)
  ├─> Entfernt Entry aus _mcp_sessions Dict
  └─> Broadcast SSE: 'mcp.session.deleted'
```

---

## 🌐 API-Endpoints Mapping

### Bestehende Playwright-Endpoints (Backward-Compat):

```
GET  /api/playwright/session/status
POST /api/playwright/session/spawn
POST /api/playwright/session/attach
POST /api/playwright/session/start
POST /api/playwright/session/stop

GET  /api/sessions  (aktuell nur Playwright)
POST /api/sessions  (aktuell nur Playwright)
GET  /api/sessions/{id}/status
POST /api/sessions/{id}/start
POST /api/sessions/{id}/stop
DELETE /api/sessions/{id}

GET  /mcp/playwright/events (SSE)
GET  /mcp/playwright/events.json
GET  /mcp/playwright/preview.png
GET  /mcp/playwright/health
GET  /mcp/playwright/session/{id}/* (Static files + Proxies)
```

### Geplante Generische MCP-Endpoints:

```
# --- Generic Session Management ---
POST   /api/mcp/sessions
       Body: {tool, name, model, config}
       → create_mcp_session()

GET    /api/mcp/sessions
       → get_all_mcp_sessions()

GET    /api/mcp/sessions/{session_id}
       → get_mcp_session_by_id()

GET    /api/mcp/sessions/{session_id}/status
       → get_mcp_session_status_by_id()

POST   /api/mcp/sessions/{session_id}/start
       → start_mcp_session_by_id()

POST   /api/mcp/sessions/{session_id}/stop
       → stop_mcp_session_by_id()

DELETE /api/mcp/sessions/{session_id}
       → delete_mcp_session_by_id()

POST   /api/mcp/sessions/{session_id}/attach
       Body: {host, port}
       → set_mcp_session_upstream_by_id()

# --- Tool-specific Shortcuts ---
POST /api/{tool}/sessions
     → create_mcp_session(tool='{tool}', ...)

# --- Generic Event Proxies ---
GET /mcp/{tool}/session/{id}/events (SSE)
GET /mcp/{tool}/session/{id}/events.json
GET /mcp/{tool}/session/{id}/health
GET /mcp/{tool}/session/{id}/* (Static files for tool UI)
```

---

## 📝 SESSION_ANNOUNCE Parsing

### Aktuelles Format (Playwright + GitHub):

```python
# Agent stdout: "SESSION_ANNOUNCE {json}"
SESSION_ANNOUNCE {"session_id": "abc-123", "host": "127.0.0.1", "port": 8787}
```

### Generalisiertes Parsing (Zeile 460-480 in spawn_playwright_session_agent):

```python
if ln.startswith('SESSION_ANNOUNCE '):
    try:
        payload = json.loads(ln[len('SESSION_ANNOUNCE '):])
    except Exception:
        payload = {}
    
    host = str(payload.get('host') or os.getenv('MCP_UI_HOST', '127.0.0.1'))
    port = int(payload.get('port') or int(os.getenv('MCP_UI_PORT', '8787')))
    sid2 = str(payload.get('session_id') or sid)
    
    # Attach upstream für EventServer
    self.set_mcp_session_upstream_by_id(sid2, host, port)
```

### Event-Port Discovery (.event_port Datei):

```python
# GitHub Agent schreibt: data/tmp/.event_port (Zeile 678-686 in github/agent.py)
event_port_path = TMP_DIR / '.event_port'
event_port_path.write_text(str(event_port))

# Backend sollte .event_port alternativ lesen, falls SESSION_ANNOUNCE fehlt
```

---

## 🚀 Refactoring-Strategie

### Phase 2-4: Core Refactoring (Höchste Priorität)

1. **Dictionary-Umbenennung** (Phase 2)
   - `_playwright_sessions` → `_mcp_sessions`
   - Alle Referenzen aktualisieren (~50 Stellen)
   - Tool-Feld zu Schema hinzufügen

2. **Generische Spawn-Methode** (Phase 3)
   - `spawn_mcp_session_agent(tool, session_id, **kwargs)`
   - Tool-zu-Pfad Mapping
   - SESSION_ANNOUNCE für alle Tools
   - .event_port Discovery

3. **Methoden-Generalisierung** (Phase 4)
   - Alle `_playwright_*` Methoden zu `_mcp_*`
   - Backward-Compat Wrapper behalten
   - Tool-Parameter zu allen Methoden

### Phase 5-7: API & Routing (Mittlere Priorität)

4. **API-Endpoints** (Phase 5-6)
   - `/api/mcp/sessions/*` für alle Tools
   - Tool-spezifische Shortcuts: `/api/{tool}/sessions`
   - Backward-Compat für `/api/playwright/*`

5. **Event-Proxies** (Phase 7)
   - `/mcp/{tool}/session/{id}/events` (SSE)
   - `/mcp/{tool}/session/{id}/events.json` (Polling)
   - Tool-spezifische Port-Discovery

### Phase 8-13: Tool-Specific & Features (GitHub-Focus)

6. **GitHub Integration** (Phase 8)
   - Agent-Pfad verifizieren
   - user.clarification.request Events
   - Clarification File-Handling

7. **Event-Broadcasting** (Phase 9)
   - SSE Events für alle Lifecycle-Events
   - Tool-Info in Events
   - correlation_id Handling

8. **Static Asset Serving** (Phase 10)
   - Generisches `/mcp/{tool}/session/{id}/*`
   - Public-Dir pro Tool
   - SPA Fallback

---

## ⚠️ Kritische Punkte

### Race Conditions:

1. **Session State Updates**
   - Alle Zugriffe auf `_mcp_sessions` MÜSSEN `_mcp_sessions_lock` verwenden
   - proc.poll() kann Race Conditions haben → in Lock wrappen

2. **Process Spawn vs. SESSION_ANNOUNCE**
   - Timeout für SESSION_ANNOUNCE: 5-10 Sekunden
   - Fallback zu .event_port Datei-Read

3. **Clarification File I/O** (Phase 13)
   - Atomic writes mit temp-file + rename
   - Proper cleanup von alten Files

### Backward Compatibility:

- **ALLE** bestehenden `/api/playwright/*` und `/api/sessions/*` Endpoints MÜSSEN funktionieren
- Playwright-spezifische Methoden als Wrapper behalten
- E2E-Tests für Regression

### Security:

- Session ID: Verwende `secrets.token_urlsafe()` statt `str(uuid.uuid4())`
- Path Traversal: Validiere alle file-paths bei Static-Serving
- Rate-Limiting: Max 10 Sessions pro User/IP (Phase 12)

---

## 📊 Geschätzte Code-Änderungen

| Phase | Zeilen Geändert | Zeilen Neu | Zeilen Entfernt | Risiko |
|-------|-----------------|------------|-----------------|--------|
| Phase 2 | ~100 | 0 | 0 | Niedrig |
| Phase 3 | 0 | ~200 | 0 | Mittel |
| Phase 4 | ~300 | ~100 | 0 | Mittel |
| Phase 5-6 | ~200 | ~400 | 0 | Hoch |
| Phase 7 | ~150 | ~300 | 0 | Hoch |
| Phase 8 | ~50 | ~150 | 0 | Mittel |
| **GESAMT** | ~800 | ~1150 | 0 | - |

**Neue Dateigröße:** ~4180 Zeilen (statt 3030)

---

## ✅ Phase 1 Checkliste

- [x] Backup erstellt: `gui_interface.py.backup`
- [x] Alle Playwright-Methoden identifiziert (14 Methoden)
- [x] Tool-Agent-Pfade dokumentiert (10 Tools)
- [x] Abhängigkeiten kartiert (Methoden-Graph)
- [x] Session-Schema dokumentiert (Aktuell + Geplant)
- [x] API-Endpoints gemapped (Aktuell + Geplant)
- [x] SESSION_ANNOUNCE Parsing analysiert
- [x] Event-Port Discovery dokumentiert
- [x] Refactoring-Strategie definiert (25 Phasen)
- [x] Kritische Punkte identifiziert
- [x] Code-Änderungs-Schätzung

---

**Nächster Schritt:** Phase 2 - Session Dictionary Refactoring beginnen