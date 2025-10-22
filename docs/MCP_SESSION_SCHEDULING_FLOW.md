# MCP Agent Session Scheduling Flow

## Übersicht

Dieses Dokument beschreibt, wie MCP Agent Sessions vom GUI aus gestartet und verwaltet werden.

---

## Session Lifecycle

### 1. Session Creation (POST `/api/sessions`)

**Handler**: `session_api.py` → `handle_create_session()`
**Backend**: `gui_interface.py` → `create_playwright_session()`

```python
# Ablauf:
1. User erstellt Session via GUI/API mit:
   - name: Session name
   - model: "gpt-4" (wird später von model_init überschrieben)
   - tools: ["github", "docker", etc.]
   - task: Optional task description
   - target_tool: Wird automatisch von tools[0] gesetzt

2. Backend generiert UUID für session_id

3. Session State wird initialisiert:
   {
     'session_id': uuid,
     'name': name,
     'model': model,
     'tools': tools,
     'task': task,
     'target_tool': target_tool,
     'status': 'stopped',
     'agent_proc': None,
     'agent_pid': None,
     'connected': False,
     'host': None,
     'port': None,
     'event_port': None
   }

4. Session wird in self._playwright_sessions gespeichert
   (Diese Dict enthält ALLE agent sessions, nicht nur Playwright!)
```

**API Response**:
```json
{
  "success": true,
  "session": {
    "session_id": "abc-123",
    "name": "my-session",
    "model": "gpt-4",
    "tools": ["github"],
    "status": "stopped"
  }
}
```

---

### 2. Session Start (POST `/api/sessions/{session_id}/start`)

**Handler**: `session_api.py` → `handle_start_session()`
**Backend**: `gui_interface.py` → `start_playwright_session_by_id()`

Dieser Schritt startet den MCP Agent als Subprocess.

#### 2.1 Bestimme target_tool

```python
# Aus session state:
target_tool = session.get('target_tool') or session['tools'][0]
```

#### 2.2 Wähle Agent Script

Das System mappt `target_tool` zu einem Agent Script:

```python
# Beispiele:
"github"     → "src/MCP PLUGINS/servers/github/agent.py"
"docker"     → "src/MCP PLUGINS/servers/docker/agent.py"
"playwright" → "src/MCP PLUGINS/servers/playwright/agent.py"
```

#### 2.3 Spawn Agent Subprocess

**Funktion**: `spawn_mcp_agent_session()`

```python
# Agent Prozess wird gestartet mit:
cmd = [
    python_exe,
    agent_path,
    '--session-id', session_id,
    '--task', task  # WICHTIG: Task wird hier übergeben!
]

# Subprocess creation:
proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
    creationflags=subprocess.CREATE_NO_WINDOW  # Windows
)
```

#### 2.4 Event Port Discovery

Nach dem Start liest das System den Event Port vom Agent:

```python
# Agent schreibt Port in .event_port Datei:
"{agent_dir}/.event_port"

# GUI liest diese Datei und speichert:
session['event_port'] = port
session['event_host'] = '127.0.0.1'
```

**API Response**:
```json
{
  "success": true,
  "session_id": "abc-123",
  "pid": 12345,
  "event_port": 46677
}
```

---

## Agent-Side: Was passiert im Agent?

### 1. Agent Initialization

```python
# In agent.py (z.B. github/agent.py):

class GitHubAgent:
    async def initialize(self):
        # 1. Event Server starten
        self.event_server = EventServer()
        httpd, thread, host, port = start_event_server(...)

        # 2. Port schreiben für GUI Discovery
        port_file = os.path.join(BASE_DIR, ".event_port")
        with open(port_file, 'w') as f:
            f.write(str(port))

        # 3. Model Client initialisieren (OHNE Task)
        self.model_client = init_model_client()  # Keine task hier!

        # 4. MCP Workbench setup
        # ...
```

### 2. Task Execution mit Task-Aware Model Selection

```python
async def run_task(self, task: str, correlation_id: str = None):
    # WICHTIG: Hier wird task-aware model client erstellt!
    task_aware_client = init_model_client(task)  # <-- Task übergeben!

    # Agents mit diesem Client erstellen:
    github_operator = AssistantAgent(
        "GitHubOperator",
        model_client=task_aware_client,  # <-- Verwendet OpenRouter!
        workbench=mcp,
        system_message=operator_prompt
    )

    qa_validator = AssistantAgent(
        "QAValidator",
        model_client=task_aware_client,  # <-- Verwendet OpenRouter!
        system_message=qa_prompt
    )

    som_agent = SocietyOfMindAgent(
        "github_society_of_mind",
        team=inner_team,
        model_client=task_aware_client  # <-- Verwendet OpenRouter!
    )
```

---

## Model Selection Flow

### Phase 1: Initialization (Kein Task)

```python
# Beim Agent Start:
init_model_client()  # Keine task
  → shared_init_model_client("github", "")
    → get_model_for_mcp("github", "")
      → task = "" → complexity = "primary"
      → Wählt: gpt-4o-mini (primary model)
```

**Log Output**:
```
[OpenRouter] Using model: gpt-4o-mini for github
```

### Phase 2: Task Execution (Mit Task)

```python
# Bei run_task():
init_model_client(task="Search for the top 3 most starred Python repositories")
  → shared_init_model_client("github", task)
    → get_model_for_mcp("github", task)
      → should_use_reasoning(task)  # Check keywords
      → task enthält kein "analyze", "design", etc.
      → complexity = "primary"
      → Wählt: gpt-4o-mini
```

**Log Output**:
```
[OpenRouter] Using model: gpt-4o-mini for github
[OpenRouter] Task: Search for the top 3 most starred Python repositories
```

### Phase 3: Reasoning Task

```python
# Bei run_task():
init_model_client(task="Analyze the architecture of tensorflow repository")
  → shared_init_model_client("github", task)
    → get_model_for_mcp("github", task)
      → should_use_reasoning(task)  # Check keywords
      → task enthält "analyze" und "architecture"
      → complexity = "reasoning"
      → Wählt: o1-mini (reasoning model)
```

**Log Output**:
```
[OpenRouter] Using model: o1-mini for github
[OpenRouter] Task: Analyze the architecture of tensorflow repository
```

---

## Event Streaming

### Event Server (Agent-Side)

```python
# Im Agent:
class EventServer:
    def broadcast(self, event_type: str, payload: dict):
        # Broadcasts event to all connected clients
        event = {
            'timestamp': timestamp,
            'type': event_type,
            'payload': payload
        }
        # Adds to event queue
```

### Event Consumer (GUI-Side)

```python
# GUI holt Events via:
GET /api/mcp/{tool}/sessions/{session_id}/events

# Returns:
{
  "events": [
    {
      "timestamp": "2025-10-02T08:55:21.221215",
      "type": "log",
      "payload": {
        "tool": "github",
        "message": "[OpenRouter] Using model: gpt-4o-mini for github"
      }
    },
    ...
  ]
}
```

---

## Session State Management

### In-Memory Storage

```python
# gui_interface.py:
self._playwright_sessions = {}  # Alle MCP agent sessions
self._mcp_sessions = {}         # Alias für dieselbe Dict

# Session Lock für Thread-Safety:
self._playwright_sessions_lock = threading.Lock()
```

### Session State Fields

```python
{
  # Identity
  'session_id': str,
  'name': str,

  # Configuration
  'model': str,          # Initial model (wird von model_init überschrieben)
  'tools': list,         # ["github", "docker", ...]
  'target_tool': str,    # Primärer tool für diese session
  'task': str,           # Task description
  'system': str,         # Optional system prompt

  # Process State
  'status': str,         # "stopped", "running"
  'agent_proc': Popen,   # Subprocess object
  'agent_pid': int,      # Process ID
  'agent_running': bool, # Is process alive?

  # Connection State
  'connected': bool,     # Playwright-specific
  'host': str,           # Playwright event server host
  'port': int,           # Playwright event server port
  'event_port': int,     # Agent event server port
  'event_host': str,     # Agent event server host (always 127.0.0.1)

  # Timing
  'created_at': float,   # timestamp
  'started_at': float,   # timestamp
  'stopped_at': float,   # timestamp
  'duration_ms': int     # Duration in milliseconds
}
```

---

## API Endpoints

### Session Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions` | GET | List all sessions |
| `/api/sessions` | POST | Create new session |
| `/api/sessions/{id}` | GET | Get session status |
| `/api/sessions/{id}/start` | POST | Start session agent |
| `/api/sessions/{id}/stop` | POST | Stop session agent |
| `/api/sessions/{id}/delete` | DELETE | Delete session |

### Event Streaming

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mcp/{tool}/sessions/{id}/events` | GET | Get session events |

---

## Wichtige Code-Pfade

### Session Creation Flow

```
GUI Frontend (routes.tsx)
  ↓ POST /api/sessions
session_api.py → handle_create_session()
  ↓
gui_interface.py → create_playwright_session()
  ↓
self._playwright_sessions[session_id] = { ... }
```

### Session Start Flow

```
GUI Frontend
  ↓ POST /api/sessions/{id}/start
session_api.py → handle_start_session()
  ↓
gui_interface.py → start_playwright_session_by_id()
  ↓
gui_interface.py → spawn_mcp_agent_session()
  ↓
subprocess.Popen([python, agent.py, --session-id, --task])
  ↓
Agent: initialize() → create event server, write .event_port
  ↓
Agent: run_task(task) → init_model_client(task) → OpenRouter!
```

---

## Debugging Tips

### 1. Check Session State

```python
# In GUI:
with self._playwright_sessions_lock:
    session = self._playwright_sessions.get(session_id)
    print(session)
```

### 2. Check Agent Logs

```bash
# Session-specific logs:
data/logs/sessions/{session_id}.log
```

### 3. Check Event Port

```bash
# Agent writes port here:
cat "src/MCP PLUGINS/servers/{tool}/.event_port"
```

### 4. Monitor Events

```bash
# Get events via API:
curl http://localhost:8765/api/mcp/github/sessions/{session_id}/events
```

---

## Known Issues

### 1. Playwright Agent Not Using OpenRouter

**Symptom**: Playwright test returns 0 events, doesn't use OpenRouter.

**Possible Causes**:
- Agent not starting properly
- Event server initialization failure
- Different agent architecture (not using Society of Mind)

**Investigation**:
- Check `playwright/agent.py` structure
- Compare with `github/agent.py` pattern
- Verify event_broadcaster import and usage

### 2. Reasoning Models Not Selected

**Symptom**: Tasks with "analyze", "design" keywords still use `gpt-4o-mini` instead of `o1-mini`.

**Root Cause**: Tests capture initialization logs (without task), not task-aware logs.

**Solution**: Wait longer for task execution before capturing events.

---

## Memory Notes

**Key Takeaways**:

1. ✅ **Session Creation ≠ Agent Start**
   - `/api/sessions` POST creates session metadata
   - `/api/sessions/{id}/start` POST spawns agent subprocess

2. ✅ **Task-Aware Model Selection**
   - `init_model_client()` called TWICE:
     - Once during initialization (no task)
     - Once in `run_task()` (with task) ← OpenRouter routing happens here!

3. ✅ **Event Discovery via .event_port File**
   - Agent writes port to `{agent_dir}/.event_port`
   - GUI reads this file to discover event endpoint

4. ✅ **All Agents Use Same Pattern**
   - `create_session` → `start_session` → spawn subprocess → run_task
   - Works for: github, docker, supabase, redis, desktop, etc.

5. ⚠️ **Playwright Special Case**
   - Has additional `spawn_playwright_session_agent()` method
   - May have different initialization pattern
   - Needs investigation

---

## Next Steps

1. **Debug Playwright Agent**
   - Check why it returns 0 events
   - Verify shared model_init integration
   - Test manually with simple task

2. **Improve Test Coverage**
   - Add test delays to capture task-aware logs
   - Verify reasoning model selection
   - Test all agents with real connections (Docker, Redis, etc.)

3. **Documentation**
   - Add architecture diagrams
   - Document model selection strategies per agent
   - Create troubleshooting guide
