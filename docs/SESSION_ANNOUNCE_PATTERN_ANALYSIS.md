# SESSION_ANNOUNCE Pattern Analysis

**Date:** 2025-10-09
**Purpose:** Understand why GitHub and Playwright agents connect successfully while others don't

## Executive Summary

**Working agents** (GitHub, Playwright, Time, CONTEXT7-fixed) all implement the **SESSION_ANNOUNCE pattern** which consists of:

1. **EventServer initialization** with session_id and tool_name
2. **Dynamic port assignment** (port=0) via `start_ui_server()`
3. **SESSION_ANNOUNCE print statement** to stdout
4. **Event broadcasting** throughout agent execution
5. **Final result events** for modal display

**Non-working agents** (10+ agents) are missing this pattern, so the backend never learns their event server ports and the frontend can't connect.

---

## Pattern Components

### 1. EventServer Initialization (Early in Agent Lifecycle)

**GitHub** ([src/MCP PLUGINS/servers/github/agent.py](src/MCP PLUGINS/servers/github/agent.py:184-185)):
```python
# Start UI early using shared EventServer
event_server = EventServer()
```

**Playwright** ([src/MCP PLUGINS/servers/playwright/agent.py](src/MCP PLUGINS/servers/playwright/agent.py:760)):
```python
# Start UI early using new EventServer/start_ui_server
event_server = EventServer()
```

**Time** ([src/MCP PLUGINS/servers/time/agent.py](src/MCP PLUGINS/servers/time/agent.py:44)):
```python
logger = setup_logging(f"time_agent_{config.session_id}")
event_server = EventServer(session_id=config.session_id, tool_name="time")
```

**Key Difference:** Time agent passes `session_id` and `tool_name` to EventServer constructor for automatic session logging integration.

---

### 2. Dynamic Port Assignment via start_ui_server()

**GitHub** ([src/MCP PLUGINS/servers/github/agent.py](src/MCP PLUGINS/servers/github/agent.py:191-195)):
```python
# Start UI with GitHub branding and dynamic port (0 = OS assigns free port)
httpd, thread, bound_host, bound_port = start_github_ui_server(
    event_server,
    host="127.0.0.1",
    port=0  # Dynamic port assignment
)
```

**Playwright** ([src/MCP PLUGINS/servers/playwright/agent.py](src/MCP PLUGINS/servers/playwright/agent.py:771)):
```python
httpd, t, bound_host, bound_port = start_ui_server(event_server, ui_bind_host, ui_bind_port)
```

**Time** ([src/MCP PLUGINS/servers/time/agent.py](src/MCP PLUGINS/servers/time/agent.py:48-53)):
```python
# Start the UI server with event broadcasting
httpd, thread, host, port = start_ui_server(
    event_server,
    host="127.0.0.1",
    port=0,  # Dynamic port assignment
    tool_name="time"
)
```

**Why port=0?**
- Prevents port conflicts when running multiple MCP sessions simultaneously
- OS automatically assigns a free port
- Port is captured in `bound_port` variable for announcement

---

### 3. SESSION_ANNOUNCE Print Statement (Critical!)

**GitHub** ([src/MCP PLUGINS/servers/github/agent.py](src/MCP PLUGINS/servers/github/agent.py:212-219)):
```python
# SESSION_ANNOUNCE for MCPSessionManager - critical for upstream integration
try:
    print("SESSION_ANNOUNCE " + json.dumps({
        "session_id": session_id,
        "ui_url": preview_url,
        "host": bound_host,
        "port": bound_port,
    }))
except Exception:
    print(f"Preview: {preview_url}")
```

**Playwright** ([src/MCP PLUGINS/servers/playwright/agent.py](src/MCP PLUGINS/servers/playwright/agent.py:788-795)):
```python
# One-line announce for orchestrators to parse easily
try:
    print("SESSION_ANNOUNCE " + json.dumps({
        "session_id": session_id,
        "ui_url": preview_url,
        "host": bound_host,
        "port": bound_port,
    }))
except Exception:
    print(f"Preview: {preview_url}")
```

**Time** ([src/MCP PLUGINS/servers/time/agent.py](src/MCP PLUGINS/servers/time/agent.py:57-63)):
```python
# Announce session (print to stdout for session manager to capture)
announce_data = {
    "session_id": session_id,
    "host": host,
    "port": port,
    "ui_url": f"http://{host}:{port}/"
}
print(f"SESSION_ANNOUNCE {json.dumps(announce_data)}", flush=True)
```

**Why this works:**
- Backend's `MCPSessionManager.spawn_agent()` captures subprocess stdout
- Parses `SESSION_ANNOUNCE` line to extract host/port
- Updates session dictionary with event server endpoint
- Frontend can now connect to `http://{host}:{port}/events` for SSE stream

---

### 4. Event Broadcasting Throughout Execution

**GitHub** ([src/MCP PLUGINS/servers/github/agent.py](src/MCP PLUGINS/servers/github/agent.py:509-573)):
```python
# Broadcast to GUI
if event_server:
    event_server.broadcast("agent.message", {
        "agent": "GitHubOperator",
        "role": "operator",
        "content": content,
        "icon": "🔧"
    })
```

**Playwright** ([src/MCP PLUGINS/servers/playwright/agent.py](src/MCP PLUGINS/servers/playwright/agent.py:951-954)):
```python
# Extract and broadcast message content
if hasattr(message, 'content'):
    content = message.content
    if isinstance(content, str):
        event_server.broadcast("chunk", {"text": content})
```

**Time** ([src/MCP PLUGINS/servers/time/agent.py](src/MCP PLUGINS/servers/time/agent.py:91-92)):
```python
# Send running status
event_server.broadcast("log", f"Starting task: {config.task}")
event_server.broadcast("status", SESSION_STATE_RUNNING)
```

**Event Types Used:**
- `session.started` - Initial session info
- `agent.message` - Agent dialogue (Society of Mind)
- `tool.call` - Tool execution events
- `chunk` / `content` - LLM streaming responses
- `status` - Status updates
- `error` - Error messages
- `session.completed` - Final completion event
- `agent.completion` - Final result for modal display

---

### 5. Final Result Events (For Modal Display)

**GitHub** ([src/MCP PLUGINS/servers/github/agent.py](src/MCP PLUGINS/servers/github/agent.py:606-615)):
```python
# Send final result event for modal display
event_server.broadcast("agent.completion", {
    "status": "success",
    "content": final_content,
    "tool": "github",
    "timestamp": time.time(),
    "metadata": {
        "message_count": len(messages),
        "nested_som": git_server_params is not None
    }
})
```

**Playwright** ([src/MCP PLUGINS/servers/playwright/agent.py](src/MCP PLUGINS/servers/playwright/agent.py:969-975)):
```python
# Send final result event for modal display (Playwright uses iframe viewer, but we add this for consistency)
try:
    event_server.broadcast("agent.completion", {
        "status": "success",
        "content": "Browser automation task completed successfully",
        "tool": "playwright",
        "timestamp": time.time()
    })
except Exception:
    pass
```

**Time** ([src/MCP PLUGINS/servers/time/agent.py](src/MCP PLUGINS/servers/time/agent.py:103-108)):
```python
# Send final result event for modal display
event_server.broadcast("agent.completion", {
    "status": "success",
    "content": result_text,
    "tool": "time",
    "timestamp": time.time()
})
```

**Modal Display Structure:**
```typescript
interface AgentCompletion {
  status: "success" | "error";
  content: string;           // Final response text
  tool: string;              // Tool identifier (github, playwright, time, etc.)
  timestamp: number;         // Unix timestamp
  metadata?: Record<string, any>;  // Optional additional info
}
```

---

## Session Logging Integration

**New Pattern (Time agent):** EventServer automatically logs all events to session files when initialized with `session_id` and `tool_name`.

**EventServer Constructor** ([src/MCP PLUGINS/servers/shared/event_server.py](src/MCP PLUGINS/servers/shared/event_server.py)):
```python
def __init__(self, session_id: Optional[str] = None, tool_name: Optional[str] = None):
    # Session identification (for Society of Mind agents)
    self.session_id = session_id
    self.tool_name = tool_name
    # ... existing code ...

    # Session logging setup
    self._session_logger: Optional[Any] = None
    if session_id and tool_name:
        self._setup_session_logger()
```

**Log File Naming:** `{tool}_{timestamp}_{session_id}.log`
**Example:** `time_20251008_233255_KRwDBSZsAxlPP5DNadtyug.log`

**Automatic Event Logging:**
```python
def broadcast(self, type_: str, value: Any) -> None:
    # ... normalize values ...

    # Log to session file
    self._log_to_session(type_, value_out if type_ in text_types else value)

    # ... rest of broadcast logic
```

---

## Backend Integration (MCPSessionManager)

**Session Manager** ([src/ui/mcp_session_manager.py](src/ui/mcp_session_manager.py)):
```python
def spawn_agent(self, tool: str, session_id: str, config: dict) -> subprocess.Popen:
    # ... setup ...

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    # Read stdout for SESSION_ANNOUNCE
    for line in proc.stdout:
        if line.startswith("SESSION_ANNOUNCE"):
            announce_json = line.replace("SESSION_ANNOUNCE", "").strip()
            announce_data = json.loads(announce_json)

            # Update session with event server endpoint
            self._sessions[session_id].update({
                "host": announce_data["host"],
                "port": announce_data["port"],
                "ui_url": announce_data["ui_url"]
            })
            break
```

**Frontend Connection** ([src/ui/webapp/src/components/MCPToolViewer.tsx](src/ui/webapp/src/components/MCPToolViewer.tsx)):
```typescript
useEffect(() => {
  if (session?.host && session?.port) {
    const eventSource = new EventSource(
      `http://${session.host}:${session.port}/events`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Handle events...
    };
  }
}, [session]);
```

---

## Configuration Files

### servers.json

**GitHub Entry:**
```json
{
  "name": "github",
  "active": true,
  "type": "stdio",
  "command": "npx",
  "args": ["--yes", "@modelcontextprotocol/server-github"],
  "env_vars": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "env:GITHUB_PERSONAL_ACCESS_TOKEN"
  }
}
```

**Playwright Entry:**
```json
{
  "name": "playwright",
  "active": true,
  "type": "stdio",
  "command": "npx",
  "args": ["--yes", "@playwright/mcp@latest", "--browser", "msedge"],
  "read_timeout_seconds": 120
}
```

**Time Entry:**
```json
{
  "name": "time",
  "active": true,
  "type": "stdio",
  "command": "python",
  "args": ["-m", "mcp_server_time"],
  "env_vars": {}
}
```

### Environment Variables

**Required:**
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` - LLM API access
- Tool-specific credentials (e.g., `GITHUB_PERSONAL_ACCESS_TOKEN`)

**Optional:**
- `SAKANA_VENV_PYTHON` - Path to venv Python executable
- `MCP_UI_HOST` - UI server bind host (default: 127.0.0.1)
- `MCP_UI_PORT` - UI server bind port (default: 0 for dynamic)
- `MCP_SESSION_ID` - Session identifier override

---

## Why Other Agents Don't Connect

**Agents WITHOUT SESSION_ANNOUNCE:**
1. docker
2. desktop
3. filesystem
4. memory
5. redis
6. supabase
7. brave-search
8. youtube
9. windows-core
10. dev/mcp-gateway

**Problem Flow:**
1. Backend spawns agent subprocess
2. Agent starts but never prints SESSION_ANNOUNCE
3. Backend's `spawn_agent()` times out waiting for announcement
4. Session remains with `host=None`, `port=None`
5. Frontend tries to connect but has no endpoint
6. UI shows "Connecting..." forever with "No events yet... Waiting for activity"

---

## Implementation Checklist (For Fixing Other Agents)

### ✅ Step 1: Import EventServer
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from event_server import EventServer, start_ui_server
from constants import *
from model_utils import get_model_client
from logging_utils import setup_logging
```

### ✅ Step 2: Initialize EventServer with Session Logging
```python
async def run_agent(config: AgentConfig):
    logger = setup_logging(f"{tool}_agent_{config.session_id}")
    event_server = EventServer(session_id=config.session_id, tool_name="{tool}")
```

### ✅ Step 3: Start UI Server with Dynamic Port
```python
httpd, thread, host, port = start_ui_server(
    event_server,
    host="127.0.0.1",
    port=0,  # Dynamic port assignment
    tool_name="{tool}"
)
```

### ✅ Step 4: Print SESSION_ANNOUNCE
```python
announce_data = {
    "session_id": config.session_id,
    "host": host,
    "port": port,
    "ui_url": f"http://{host}:{port}/"
}
print(f"SESSION_ANNOUNCE {json.dumps(announce_data)}", flush=True)
event_server.broadcast("session.started", announce_data)
```

### ✅ Step 5: Broadcast Events During Execution
```python
# Status updates
event_server.broadcast("log", f"Starting task: {config.task}")
event_server.broadcast("status", SESSION_STATE_RUNNING)

# Agent dialogue (Society of Mind)
event_server.broadcast("agent.message", {
    "agent": "AgentName",
    "role": "operator",
    "content": message_content,
    "icon": "🔧"
})

# Tool calls
event_server.broadcast("tool.call", {
    "tool": tool_name,
    "icon": "🛠️"
})
```

### ✅ Step 6: Send Final Result Event
```python
# Send final result event for modal display
event_server.broadcast("agent.completion", {
    "status": "success",
    "content": final_content,
    "tool": "{tool}",
    "timestamp": time.time(),
    "metadata": {"message_count": len(messages)}
})
```

### ✅ Step 7: Cleanup and Shutdown
```python
finally:
    # Keep server running briefly so events can be consumed
    await asyncio.sleep(2)
    httpd.shutdown()
```

---

## Testing Verification

**Test Command:**
```bash
python "src/MCP PLUGINS/servers/{tool}/agent.py" --session-id test123 --task "Test task"
```

**Expected Output:**
```
SESSION_ANNOUNCE {"session_id": "test123", "host": "127.0.0.1", "port": 54321, "ui_url": "http://127.0.0.1:54321/"}
```

**Backend Verification:**
```bash
curl -s "http://127.0.0.1:8765/api/sessions"
```

Should show session with `host` and `port` populated.

**Frontend Verification:**
```
http://127.0.0.1:8765/
# Click tool card → should show "Connected" badge, not "Connecting..."
```

---

## Key Takeaways

1. **SESSION_ANNOUNCE is the critical integration point** between agent subprocesses and backend session management
2. **Dynamic port assignment (port=0)** prevents conflicts and allows multiple concurrent sessions
3. **EventServer with session_id/tool_name** enables automatic session logging with proper naming format
4. **Event broadcasting** provides live updates to React frontend via SSE
5. **Final result events** power the modal display system for all MCP tools
6. **Pattern consistency** across all agents ensures reliable connectivity and debugging

---

## Next Steps

**Priority 1:** Fix remaining 10 agents using this pattern
**Priority 2:** Create automated test suite to verify SESSION_ANNOUNCE compliance
**Priority 3:** Document agent development guide with this pattern as standard

**Documentation References:**
- [SESSION_ANNOUNCE_IMPLEMENTATION_TODO.md](SESSION_ANNOUNCE_IMPLEMENTATION_TODO.md)
- [MCP_SESSION_ANNOUNCE_STATUS.md](MCP_SESSION_ANNOUNCE_STATUS.md)
- [GITHUB_SESSION_TERMINATION_ANALYSIS.md](GITHUB_SESSION_TERMINATION_ANALYSIS.md)
