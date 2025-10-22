# GitHub Session Termination Analysis

## Overview

This document analyzes how GitHub (and other MCP tool) session termination is performed in the Sakana Desktop Assistant.

## Termination Flow

### 1. Frontend Trigger

**Location**: `src/ui/webapp/src/routes.tsx`

The user clicks "Stop" button which calls:

```typescript
// Line 75-82
async function stopSession(sessionId: string): Promise<{ success: boolean; error?: string }> {
  const res = await fetch(`/api/sessions/${sessionId}/stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  })
  return await res.json()
}
```

### 2. Backend HTTP Handler

**Location**: `src/gui/handlers/post_routes.py`

The POST request is handled by the backend:

```python
# Line 317-324
if self.path.startswith("/api/sessions/") and self.path.endswith("/stop"):
    try:
        session_id = self.path.split("/")[3]
        result = self.server.stop_playwright_session_by_id(session_id)
        self._json(200, result)
    except Exception as e:
        self._json(500, {"success": False, "error": f"Failed to stop session: {e}"})
    return
```

### 3. Session Manager Wrapper

**Location**: `src/ui/mcp_session_manager.py`

The `stop_playwright_session_by_id` is a backward-compatibility wrapper:

```python
# Line 608-610
def stop_playwright_session_by_id(self, session_id: str) -> Dict[str, Any]:
    """Stop Playwright agent for a specific session (legacy compatibility method)."""
    return self.stop_agent(session_id)
```

### 4. Core Termination Logic

**Location**: `src/ui/mcp_session_manager.py` (Lines 352-415)

The `stop_agent` method performs the actual termination:

```python
def stop_agent(self, session_id: str) -> Dict[str, Any]:
    """Stop agent for a specific session."""
    with self._sessions_lock:
        if session_id not in self._sessions:
            return {"success": False, "error": f"Session {session_id} not found"}

        session = self._sessions[session_id]
        proc = session.get("agent_proc")

        # If process is already gone, just update status
        if not proc or proc.poll() is not None:
            session.update({
                "agent_proc": None,
                "agent_pid": None,
                "agent_running": False,
                "connected": False,
                "status": "completed" if session.get("status") == "running" else "stopped",
                "stopped_at": time.time(),
            })
            return {"success": True, "message": "Session already stopped"}

        session_logger = setup_session_logging(session_id)
        session_logger.info(f"Stopping agent for session {session_id} (PID: {proc.pid})")

        try:
            # 1. GRACEFUL TERMINATION: Send SIGTERM
            proc.terminate()

            # 2. WAIT UP TO 5 SECONDS
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # 3. FORCE KILL: Send SIGKILL
                proc.kill()
                proc.wait()
        except Exception as e:
            session_logger.error(f"Error stopping process: {e}")
            try:
                proc.kill()
                proc.wait()
            except Exception:
                pass

        # 4. UPDATE SESSION STATE
        session.update({
            "agent_proc": None,
            "agent_pid": None,
            "agent_running": False,
            "connected": False,
            "status": "stopped",
            "stopped_at": time.time(),
        })

        session_logger.info(f"Stopped agent for session {session_id}")

        # 5. BROADCAST TERMINATION EVENT
        self.event_broadcaster(f"{session.get('tool', 'unknown')}.session.stopped", {
            "session_id": session_id,
        })

        return {"success": True, "session_id": session_id}
```

## Termination Sequence

### Step-by-Step Process

1. **Lock Acquisition**: `with self._sessions_lock:` - Ensures thread safety
2. **Session Validation**: Check if session exists
3. **Process Check**: Verify process is running (`proc.poll() is not None`)
4. **Graceful Shutdown**:
   - `proc.terminate()` - Sends SIGTERM signal
   - `proc.wait(timeout=5)` - Wait up to 5 seconds for clean exit
5. **Force Kill** (if timeout):
   - `proc.kill()` - Sends SIGKILL signal
   - `proc.wait()` - Wait for process death
6. **State Update**: Clear all process references and set status to "stopped"
7. **Event Broadcast**: Notify frontend via SSE
8. **Return Success**: Return `{"success": True, "session_id": session_id}`

## Agent-Side Behavior

### GitHub Agent Shutdown

**Location**: `src/MCP PLUGINS/servers/github/agent.py`

The GitHub agent has **keepalive mode** which affects shutdown:

```python
# Line 497-509
if keepalive:
    try:
        while True:
            await asyncio.sleep(3600)  # Keep alive forever
    except asyncio.CancelledError:
        pass  # Exit on cancellation
else:
    try:
        httpd.shutdown()  # Shutdown HTTP server
    except Exception:
        pass
    return
```

### Keepalive vs. Non-Keepalive

| Mode | Behavior | When Process Receives SIGTERM |
|------|----------|------------------------------|
| **keepalive=False** | Exits after task completion | Exits gracefully within 5s |
| **keepalive=True** | Runs indefinitely | Catches `asyncio.CancelledError` and exits |

## Potential Issues

### 1. **Hanging Clarification Dialog**

**Problem**: If user clarification is pending, the agent may block waiting for response file.

**Location**: `src/MCP PLUGINS/servers/github/user_interaction_utils.py` (Lines 86-164)

```python
# Agent polls for response file with 60s timeout
max_wait = 60  # 1 minute
while elapsed < max_wait:
    # Check for response or skip file
    if response_file.exists():
        # Read and process
        ...
    if skip_file.exists():
        # User skipped - exit
        ...
    await asyncio.sleep(poll_interval)
    elapsed += poll_interval
```

**Mitigation**:
- 60-second timeout prevents indefinite hanging
- Skip file mechanism allows cancellation
- SIGTERM during polling will still terminate within 5s

### 2. **HTTP Server Shutdown**

**Problem**: `httpd.shutdown()` may block if there are active connections.

**Solution**: Wrapped in try-except to ensure process exits even if shutdown fails.

### 3. **No Stop File Mechanism**

Unlike some other systems, GitHub session **does not use stop files** (`data/tmp/stop_{session_id}.txt`).

**Current Implementation**: Relies solely on process termination signals.

**Comparison with Playwright**: Playwright agent may have stop file polling (not confirmed in this analysis).

## Deletion vs. Stopping

### Delete Session

**Location**: `src/ui/mcp_session_manager.py` (Lines 417-443)

```python
def delete_session(self, session_id: str) -> Dict[str, Any]:
    """Delete a session (stops agent if running)."""
    # First stop the session if running
    stop_result = self.stop_agent(session_id)

    with self._sessions_lock:
        if session_id not in self._sessions:
            return {"success": False, "error": f"Session {session_id} not found"}

        # Remove from sessions dictionary
        del self._sessions[session_id]

        session_logger = setup_session_logging(session_id)
        session_logger.info(f"Deleted session: {session_id}")

        # Broadcast deletion event
        self.event_broadcaster("mcp.session.deleted", {
            "session_id": session_id,
        })

        return {"success": True, "session_id": session_id}
```

**Difference**:
- **Stop**: Process killed, session stays in `_sessions` with status "stopped"
- **Delete**: Process killed, session removed from `_sessions` entirely

## Event Broadcasting

### Events Emitted During Termination

1. **On Stop**:
   ```python
   self.event_broadcaster(f"{tool}.session.stopped", {
       "session_id": session_id,
   })
   ```

2. **On Delete**:
   ```python
   self.event_broadcaster("mcp.session.deleted", {
       "session_id": session_id,
   })
   ```

### Frontend Event Handling

**Location**: `src/ui/webapp/src/components/MCPSessionViewer.tsx`

The frontend listens for these events via SSE:

```typescript
// EventSource connection
const eventSource = new EventSource(`/mcp/${tool}/session/${sessionId}/events`)

eventSource.addEventListener('message', (event) => {
  const data = JSON.parse(event.data)
  const eventType = data.event

  if (eventType === 'session.stopped' || eventType === 'session.completed') {
    // Update UI to show session stopped
  }
})
```

## Timing Analysis

### Normal Termination (Graceful)

```
User Click → HTTP POST → stop_agent() → proc.terminate() → proc.wait(5s) → Event Broadcast → UI Update
Total: < 100ms (if agent responds quickly)
```

### Timeout Termination (Force Kill)

```
User Click → HTTP POST → stop_agent() → proc.terminate() → 5s timeout → proc.kill() → Event Broadcast
Total: ~5 seconds
```

### Already Stopped

```
User Click → HTTP POST → stop_agent() → Check proc.poll() → Return success
Total: < 50ms
```

## Recommendations

### 1. Add Stop File Mechanism (Optional)

**Proposal**: Implement stop file polling similar to clarification:

```python
# In agent main loop
stop_file = tmp_dir / f"stop_{session_id}.txt"
if stop_file.exists():
    stop_file.unlink()
    httpd.shutdown()
    return
```

**Benefits**:
- Faster graceful shutdown
- No need to wait for SIGTERM processing
- Consistent with clarification skip mechanism

### 2. Improve Keepalive Handling

**Current Issue**: Keepalive mode waits indefinitely, relying on SIGTERM.

**Proposal**: Check stop signal periodically:

```python
if keepalive:
    while True:
        # Check for stop signal
        if should_stop(session_id):
            break
        await asyncio.sleep(5)
    httpd.shutdown()
```

### 3. Add Shutdown Timeout Configuration

**Proposal**: Make the 5-second timeout configurable:

```python
# In config.yaml
mcp_session:
  shutdown_timeout_seconds: 5  # Default
```

## Summary

**GitHub session termination is performed through**:

1. **Process Signals**: SIGTERM → 5s wait → SIGKILL
2. **State Management**: Session status updated to "stopped"
3. **Event Broadcasting**: Frontend notified via SSE
4. **No Stop Files**: Unlike clarification, no file-based signaling

**Key Characteristics**:
- ✅ Thread-safe with lock
- ✅ Graceful termination with timeout
- ✅ Force kill fallback
- ✅ Event broadcasting
- ⚠️ Potential hanging during clarification (mitigated by 60s timeout)
- ⚠️ No explicit stop file mechanism

**Reliability**: **High** - Multiple fallback mechanisms ensure process termination.

---

**Last Updated**: 2025-10-04
**Analysis By**: Claude Code
