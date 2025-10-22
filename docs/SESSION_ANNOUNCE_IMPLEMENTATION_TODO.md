# SESSION_ANNOUNCE Implementation TODO

**Status**: 2/19 agents fixed (context7 + time completed in this session)
**Remaining**: 10 agents need SESSION_ANNOUNCE + final result events

## ✅ Completed (9 agents)

1. **fetch** - Already has SESSION_ANNOUNCE
2. **github** - Already has SESSION_ANNOUNCE + final result event (added in this session)
3. **n8n** - Already has SESSION_ANNOUNCE
4. **playwright** - Already has SESSION_ANNOUNCE + final result event (added in this session)
5. **sequential-thinking** - Already has SESSION_ANNOUNCE
6. **taskmanager** - Already has SESSION_ANNOUNCE
7. **tavily** - Already has SESSION_ANNOUNCE
8. **time** - Already has SESSION_ANNOUNCE + final result event (added in this session)
9. **context7** - ✅ **FIXED IN THIS SESSION** - SESSION_ANNOUNCE + final result event

## ❌ Remaining (10 agents)

### Priority 1 - Common Tools
1. **docker** - `src/MCP PLUGINS/servers/docker/agent.py`
2. **desktop** - `src/MCP PLUGINS/servers/desktop/agent.py`
3. **filesystem** - `src/MCP PLUGINS/servers/filesystem/agent.py`
4. **memory** - `src/MCP PLUGINS/servers/memory/agent.py`

### Priority 2 - Database/Storage
5. **redis** - `src/MCP PLUGINS/servers/redis/agent.py`
6. **supabase** - `src/MCP PLUGINS/servers/supabase/agent.py`

### Priority 3 - Search/Media
7. **brave-search** - `src/MCP PLUGINS/servers/brave-search/agent.py`
8. **youtube** - `src/MCP PLUGINS/servers/youtube/agent.py`

### Priority 4 - Specialized
9. **windows-core** - `src/MCP PLUGINS/servers/windows-core/agent.py`
10. **dev/mcp-gateway** - `src/MCP PLUGINS/servers/dev/mcp-gateway/agent.py`

## Implementation Checklist (Per Agent)

For each agent, apply these changes:

### 1. Add Imports
```python
import time
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from event_server import EventServer, start_ui_server
from logging_utils import setup_logging
```

### 2. Create Config Class
```python
class {Tool}AgentConfig(BaseModel):
    session_id: str
    name: str
    model: str
    task: str
```

### 3. Add SESSION_ANNOUNCE
```python
# Start the UI server with event broadcasting
httpd, thread, host, port = start_ui_server(
    event_server,
    host="127.0.0.1",
    port=0,  # Dynamic port assignment
    tool_name="{tool_name}"
)

# Announce session (print to stdout for session manager to capture)
announce_data = {
    "session_id": config.session_id,
    "host": host,
    "port": port,
    "ui_url": f"http://{host}:{port}/"
}
print(f"SESSION_ANNOUNCE {json.dumps(announce_data)}", flush=True)
event_server.broadcast("session.started", announce_data)
```

### 4. Add Event Broadcasting
```python
# Throughout agent execution
event_server.broadcast("log", "Message text")
event_server.broadcast("status", "running")
event_server.broadcast("agent.message", {"agent": "Name", "content": "..."})
event_server.broadcast("tool.call", {"tool": "tool_name"})
```

### 5. Add Final Result Event
```python
# At task completion
event_server.broadcast("agent.completion", {
    "status": "success",
    "content": final_content,
    "tool": "{tool_name}",
    "timestamp": time.time(),
    "metadata": {
        "message_count": len(messages)
    }
})

# On error
event_server.broadcast("agent.completion", {
    "status": "error",
    "content": "",
    "tool": "{tool_name}",
    "timestamp": time.time(),
    "error": str(e)
})
```

### 6. Update Main Function
```python
async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--session-id', required=False)
    parser.add_argument('--name', default='{tool}-session')
    parser.add_argument('--model', default='openai/gpt-4o-mini')
    parser.add_argument('--task', default='Default task')
    parser.add_argument('config_json', nargs='?')
    args = parser.parse_args()

    try:
        if args.config_json:
            config_dict = json.loads(args.config_json)
        elif args.session_id:
            config_dict = {
                'session_id': args.session_id,
                'name': args.name,
                'model': args.model,
                'task': args.task
            }
        else:
            print(json.dumps({"error": "Missing session config"}), file=sys.stderr)
            sys.exit(1)

        config = {Tool}AgentConfig(**config_dict)
        await run_{tool}_agent(config)

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
```

## Reference Implementation

See **context7/agent.py** (lines 213-427) for complete reference implementation with:
- EventServer initialization
- SESSION_ANNOUNCE
- Live event broadcasting
- Final result events
- Session logging integration
- Error handling

## Testing

After each agent is fixed:

```bash
# Create session
curl -X POST "http://127.0.0.1:8765/api/sessions" \
  -H "Content-Type: application/json" \
  -d '{"tool":"{tool}","name":"test","model":"openai/gpt-4o-mini","task":"test task"}'

# Check session status
curl -s "http://127.0.0.1:8765/api/sessions" | python -m json.tool

# Verify:
# - connected: true
# - host: "127.0.0.1"
# - port: <number>
# - React viewer connects successfully
# - Events stream in real-time
# - Final response modal works
```

## Backend Restart Required

After fixing agents, restart the backend:
```bash
# Kill all old backend processes
netstat -ano | findstr ":8765"  # Find PIDs
python -c "import os; os.kill(PID, 9)"  # Kill each

# Start new backend
python src/main.py
```

## Session Logs Verification

Check session logs to verify conversation logging works:
```bash
ls -lt data/logs/sessions/
tail -100 data/logs/sessions/{tool}_{timestamp}_{session_id}.log
```

Should contain:
- Agent messages
- Tool calls
- Status updates
- Final results

## Progress Tracking

Update this checklist as agents are fixed:
- [x] context7 - Fixed 2025-10-08
- [ ] docker
- [ ] desktop
- [ ] filesystem
- [ ] memory
- [ ] redis
- [ ] supabase
- [ ] brave-search
- [ ] youtube
- [ ] windows-core
- [ ] dev/mcp-gateway
