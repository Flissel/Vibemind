# GUI Module Architektur

## Überblick

Das GUI-Modul wurde von einer monolithischen 2824-Zeilen Datei in eine modulare Struktur mit klaren Verantwortlichkeiten aufgeteilt.

```
src/gui/
├── __init__.py                 # Hauptexporte: GUIInterface, set_data_directories
├── config.py                   # Globale Konfiguration & Hilfsfunktionen
├── watcher.py                  # File System Watcher für Auto-Reload
├── server.py                   # AssistantHTTPServer mit Session-Management
├── interface.py                # GUIInterface Hauptklasse
└── handlers/                   # HTTP Request Handler
    ├── __init__.py             # Handler-Exports
    ├── base.py                 # Basis Request Handler
    ├── get_routes.py           # GET HTTP Routen
    ├── post_routes.py          # POST HTTP Routen
    └── mcp_proxy.py            # MCP Tool Proxy Handler
```

## Modul-Abhängigkeiten

```
main.py
  └─> gui/interface.py (GUIInterface)
        ├─> gui/config.py (set_data_directories, _gather_learning_insights)
        ├─> gui/server.py (AssistantHTTPServer)
        │     ├─> gui/config.py (setup_session_logging)
        │     └─> ui/mcp_session_manager.py (MCPSessionManager)
        ├─> gui/watcher.py (ReloadEventHandler)
        └─> gui/handlers/base.py (GUIRequestHandler)
              ├─> gui/handlers/get_routes.py (do_GET)
              │     ├─> gui/config.py (_gather_learning_insights)
              │     └─> gui/handlers/mcp_proxy.py (handle_mcp_playwright_proxy)
              └─> gui/handlers/post_routes.py (do_POST)
```

## Datenfluss

### 1. Initialisierung
```python
main.py:
  from src.gui import GUIInterface, set_data_directories
  set_data_directories(DATA_DIR, LOGS_DIR, SESSIONS_DIR, TMP_DIR)
  interface = GUIInterface(assistant)
  await interface.initialize()
```

### 2. HTTP Request Handling
```
Browser Request
  ↓
AssistantHTTPServer (server.py)
  ↓
GUIRequestHandler (handlers/base.py)
  ↓
do_GET/do_POST (handlers/get_routes.py | handlers/post_routes.py)
  ↓
Response to Browser
```

### 3. Session Management
```
Browser: POST /api/sessions {"name": "...", "model": "...", "tools": ["playwright"]}
  ↓
post_routes.py: do_POST()
  ↓
server.py: create_playwright_session()
  ↓
mcp_session_manager.py: create_session()
  ↓
Response: {"success": true, "session": {...}}
```

### 4. Event Streaming
```
Browser: GET /api/mcp/{tool}/sessions/{id}/events?since=0
  ↓
get_routes.py: do_GET() - neue Route!
  ↓
server._mcp_manager.get_session(session_id)
  ↓
Proxy zu Playwright EventServer (127.0.0.1:port/events.json)
  ↓
Response: {"items": [...], "since": X}
```

## Wichtige Verbindungen

### config.py → Alle Module
- `DATA_DIR`, `LOGS_DIR`, `SESSIONS_DIR`, `TMP_DIR` globale Variablen
- `MCP_TOOL_AGENT_PATHS` Mapping
- `setup_session_logging()` für per-Session Logging
- `_gather_learning_insights()` für /api/learning Endpoint

### server.py → mcp_session_manager.py
```python
# server.py __init__:
from src.ui.mcp_session_manager import MCPSessionManager
self._mcp_manager = MCPSessionManager(event_broadcaster=self.broadcast_event)

# Delegationen:
def create_playwright_session(...):
    return self._mcp_manager.create_session(...)

def get_all_mcp_sessions(...):
    return self._mcp_manager.get_all_sessions(...)
```

### handlers/base.py → handlers/{get,post}_routes.py
```python
# base.py:
class GUIRequestHandler(BaseHTTPRequestHandler):
    # Hilfsmethoden: _json(), _fetch_with_backoff()
    
    # Import der Route-Handler:
    from .get_routes import do_GET
    from .post_routes import do_POST
```

## API-Endpunkte Übersicht

### GET Routen (get_routes.py)
- `/` → React SPA oder Legacy HTML
- `/health` → Health check
- `/events` → SSE Stream für GUI Events
- `/events.json` → JSON Polling Fallback
- `/api/plugins` → Liste aller Plugins
- `/api/learning` → Learning Insights
- `/api/sessions` → Liste aller MCP Sessions
- `/api/sessions/{id}/status` → Session Status
- `/api/mcp/{tool}/sessions/{id}/events` → **NEU!** Tool-spezifische Events
- `/mcp/playwright/...` → Playwright Proxy Routes

### POST Routen (post_routes.py)
- `/api/chat` → Chat Message mit Job-Queueing
- `/api/message` → Direkte Message Processing
- `/api/delegate` → Delegation Endpoint
- `/api/tool` → Tool Execution
- `/api/gui_event` → GUI Event Broadcasting
- `/api/sessions` → Session Creation
- `/api/sessions/{id}/start` → Start Session
- `/api/sessions/{id}/stop` → Stop Session
- `/api/sessions/{id}/delete` → Delete Session
- `/api/playwright/session/...` → Playwright-spezifische Session-Operationen

## Zusammenpassung

✅ **Alle Module sind korrekt miteinander verbunden**
✅ **Import-Pfade sind konsistent**
✅ **Datenfluss ist logisch**
✅ **Keine zirkulären Abhängigkeiten**
✅ **MCPSessionManager ist zentral integriert**

Die Architektur ist sauber und wartbar!