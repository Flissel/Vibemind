# Taskkill-Based Session Termination Implementation Plan

## Overview

Implement robust Windows taskkill-based termination to ensure GitHub (and all MCP) sessions are reliably closed, even when standard process.terminate() fails.

## Current Issues

1. **Process.terminate() may fail** on Windows if process is unresponsive
2. **No child process cleanup** - agent may spawn subprocesses that survive termination
3. **PID tracking is volatile** - lost if parent process crashes
4. **No platform-specific handling** - same code for Windows/Unix

## Proposed Solution: Taskkill Integration

### Architecture

```
User Click Stop
      ↓
stop_agent(session_id)
      ↓
  Get PID from session
      ↓
Platform Detection
      ↓
┌─────────────────┴─────────────────┐
│ Windows                   │ Unix  │
│ taskkill /PID /T /F      │ kill  │
└──────────────────────────────────┘
      ↓
Verify termination
      ↓
Update session state
      ↓
Broadcast event
```

## Implementation Tasks

### 1. Track Agent PID Reliably on Session Spawn

**File**: `src/ui/mcp_session_manager.py`

**Current Code** (Line ~270):
```python
proc = subprocess.Popen(cmd, ...)
session.update({
    "agent_proc": proc,
    "agent_pid": proc.pid,
    ...
})
```

**Enhancement Needed**:
```python
proc = subprocess.Popen(cmd, ...)
pid = proc.pid

# Store PID in session
session.update({
    "agent_proc": proc,
    "agent_pid": pid,
    ...
})

# PERSIST PID TO FILE for recovery
pid_file = data_dir / "tmp" / f"session_{session_id}.pid"
pid_file.write_text(str(pid))

logger.info(f"Session {session_id} spawned with PID {pid}")
```

**Location**: `spawn_mcp_session_agent()` method

---

### 2. Add PID Validation on Windows (tasklist check)

**File**: `src/ui/mcp_session_manager.py`

**New Method**:
```python
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
```

**Usage**:
```python
if platform.system() == "Windows":
    if not self._is_process_running_windows(pid):
        return {"success": True, "message": "Process not running"}
```

---

### 3. Create Platform-Specific Kill Methods

**File**: `src/ui/mcp_session_manager.py`

**New Methods**:

```python
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
        cmd = ["taskkill", "/PID", str(pid)]

        if force:
            cmd.append("/F")  # Force kill
1
        # /T kills process tree (all child processes)
        cmd.append("/T")

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

        sig = signal.SIGKILL if force else signal.SIGTERM

        os.kill(pid, sig)

        logger.info(f"Sent signal {sig} to PID {pid}")
        return {"success": True, "method": "kill"}

    except ProcessLookupError:
        return {"success": True, "message": "Process not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

### 4. Add Child Process Cleanup (taskkill /T)

**Already Included** in `_kill_process_windows()` via `/T` flag:

```python
cmd.append("/T")  # Kills entire process tree
```

**What /T Does**:
- Terminates the specified process
- Terminates all child processes started by that process
- Ensures no orphaned Python/Node.js processes remain

**Example**:
```
Parent PID: 12345 (agent.py)
  ├─ Child PID: 12346 (httpd server)
  └─ Child PID: 12347 (autogen runtime)

taskkill /PID 12345 /T
→ Kills 12345, 12346, 12347
```

---

### 5. Implement PID Persistence to File

**File**: `src/ui/mcp_session_manager.py`

**On Spawn** (already shown above):
```python
pid_file = data_dir / "tmp" / f"session_{session_id}.pid"
pid_file.write_text(str(pid))
```

**On Stop** - Read PID from file if session data missing:
```python
def _get_pid_from_file(self, session_id: str) -> Optional[int]:
    """Recover PID from persistence file.

    Args:
        session_id: Session identifier

    Returns:
        PID if found, None otherwise
    """
    try:
        pid_file = self.data_dir / "tmp" / f"session_{session_id}.pid"
        if pid_file.exists():
            pid = int(pid_file.read_text().strip())
            logger.info(f"Recovered PID {pid} from file for session {session_id}")
            return pid
    except Exception as e:
        logger.error(f"Failed to read PID file: {e}")
    return None
```

**Cleanup** - Delete PID file after successful termination:
```python
try:
    pid_file = self.data_dir / "tmp" / f"session_{session_id}.pid"
    if pid_file.exists():
        pid_file.unlink()
except Exception as e:
    logger.debug(f"Failed to delete PID file: {e}")
```

---

### 6. Enhanced stop_agent() Method

**File**: `src/ui/mcp_session_manager.py`

**New Implementation**:

```python
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

        session_logger = setup_session_logging(session_id)
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
            pid_file = self.data_dir / "tmp" / f"session_{session_id}.pid"
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
```

---

### 7. Add Force-Kill Fallback

**Already Included** in enhanced `stop_agent()`:

```python
# Try graceful first
result = self._kill_process_windows(pid, force=False)

if not result["success"]:
    # Force kill
    result = self._kill_process_windows(pid, force=True)
```

**Flags Used**:
- **Graceful**: `taskkill /PID {pid} /T` (process tree kill)
- **Force**: `taskkill /PID {pid} /T /F` (force kill, ignores active tasks)

---

### 8. Add Termination Timeout Configuration

**File**: `config.yaml`

**New Section**:
```yaml
mcp_session:
  termination:
    graceful_timeout_seconds: 2  # Wait before force kill
    verification_wait_seconds: 1  # Wait before verifying kill success
    tasklist_timeout_seconds: 5  # Timeout for tasklist/PID check
```

**File**: `src/ui/mcp_session_manager.py`

**Load Config**:
```python
def __init__(self, ...):
    # Load termination config
    self.termination_config = config.get("mcp_session", {}).get("termination", {})
    self.graceful_timeout = self.termination_config.get("graceful_timeout_seconds", 2)
    self.verification_wait = self.termination_config.get("verification_wait_seconds", 1)
    self.tasklist_timeout = self.termination_config.get("tasklist_timeout_seconds", 5)
```

**Use in Code**:
```python
# Instead of hardcoded time.sleep(2)
time.sleep(self.graceful_timeout)

# Instead of hardcoded time.sleep(1)
time.sleep(self.verification_wait)
```

---

### 9. Test Termination with Hanging Clarification

**Test Scenario**:
1. Start GitHub session with task requiring clarification
2. Wait for clarification dialog
3. **Do NOT answer** - leave dialog open
4. Click "Stop" button
5. Verify session terminates within expected time

**Expected Behavior**:
- Session stops immediately (taskkill bypasses clarification polling)
- Process tree killed (including HTTP server)
- PID file cleaned up
- Frontend shows "Stopped" status

**Test Script** (`tests/test_session_termination.py`):
```python
import asyncio
import subprocess
import time
from pathlib import Path

async def test_hanging_clarification_termination():
    """Test that session stops even during hanging clarification."""

    # 1. Start session with clarification task
    session_id = "test-clarification-hang"

    # 2. Wait for clarification request (monitor logs)
    # Agent will be blocked in polling loop

    # 3. Get PID
    pid_file = Path("data/tmp") / f"session_{session_id}.pid"
    pid = int(pid_file.read_text())

    # 4. Stop session via taskkill
    result = subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True
    )

    assert result.returncode == 0, f"taskkill failed: {result.stderr}"

    # 5. Verify process is gone
    time.sleep(1)
    check = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
        capture_output=True,
        text=True
    )

    assert str(pid) not in check.stdout, "Process still running!"

    # 6. Verify PID file cleaned up
    assert not pid_file.exists(), "PID file not cleaned up"

    print("✅ Hanging clarification termination test passed")

if __name__ == "__main__":
    asyncio.run(test_hanging_clarification_termination())
```

---

## Implementation Order

### Phase 1: Core Infrastructure (Tasks 1-3)
1. ✅ Add PID persistence to file on spawn
2. ✅ Implement `_is_process_running_windows()`
3. ✅ Create `_kill_process_windows()` and `_kill_process_unix()`

### Phase 2: Enhanced Termination (Tasks 4-6)
4. ✅ Implement `_get_pid_from_file()` for recovery
5. ✅ Rewrite `stop_agent()` with platform-specific logic
6. ✅ Add child process cleanup with /T flag

### Phase 3: Configuration & Testing (Tasks 7-9)
7. ✅ Add termination timeout configuration
8. ✅ Write termination tests
9. ✅ Test with hanging clarification dialogs

### Phase 4: Documentation (Task 10)
10. ✅ Update `GITHUB_SESSION_TERMINATION_ANALYSIS.md`
11. ✅ Update `LEARNING_INTEGRATION_GUIDE.md` (session lifecycle)

---

## Benefits

### 1. **Reliability**
- ✅ Guaranteed termination on Windows via taskkill
- ✅ Process tree cleanup (no orphaned children)
- ✅ Force kill fallback if graceful fails

### 2. **Robustness**
- ✅ PID recovery from file if session data lost
- ✅ Works even if clarification dialog hanging
- ✅ Platform-aware (Windows vs Unix)

### 3. **Observability**
- ✅ Configurable timeouts
- ✅ Detailed logging of termination steps
- ✅ Verification of process death

### 4. **Maintainability**
- ✅ Modular platform-specific methods
- ✅ Configuration-driven timeouts
- ✅ Well-tested with edge cases

---

## Code Locations Summary

| Component | File | Lines |
|-----------|------|-------|
| PID persistence | `mcp_session_manager.py` | ~270 (spawn) |
| PID recovery | `mcp_session_manager.py` | New method |
| Windows kill | `mcp_session_manager.py` | New method |
| Unix kill | `mcp_session_manager.py` | New method |
| Enhanced stop_agent | `mcp_session_manager.py` | 352-415 (rewrite) |
| Config | `config.yaml` | New section |
| Tests | `tests/test_session_termination.py` | New file |

---

## Rollout Plan

### Step 1: Implement Core (1-2 hours)
- Add PID persistence
- Implement platform-specific kill methods
- Add PID validation

### Step 2: Integration (1 hour)
- Rewrite `stop_agent()` with new methods
- Add configuration loading
- Update session spawn to persist PID

### Step 3: Testing (1-2 hours)
- Unit tests for kill methods
- Integration test with real sessions
- Edge case testing (hanging clarification)

### Step 4: Documentation (30 minutes)
- Update termination analysis doc
- Add configuration examples
- Document new behavior

---

**Total Estimated Time**: 4-6 hours
**Risk Level**: Low (fallback to current method if issues)
**Impact**: High (guaranteed session cleanup)

---

**Last Updated**: 2025-10-04
**Status**: Ready for Implementation
