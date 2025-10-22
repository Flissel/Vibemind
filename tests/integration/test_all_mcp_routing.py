"""Test MCP session routing and SESSION_ANNOUNCE pattern for all agents.

This script:
1. Creates a session for each MCP tool
2. Checks if the session was created with the correct tool (not defaulting to playwright)
3. Starts each session and waits for SESSION_ANNOUNCE
4. Collects session logs for verification
"""

import json
import requests
import sys
import time
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8765"
LOGS_DIR = Path("data/logs/sessions")

# Tools with SESSION_ANNOUNCE pattern implemented
TOOLS_TO_TEST = [
    "docker",
    "memory",
    "filesystem",
    "redis",
    "desktop",
    "context7",
    "brave-search",
    "tavily",
    "n8n",
    "github",
    "playwright",
    "time",
]

def create_session(tool, name, model="openai/gpt-4o-mini"):
    """Create a new session for the given tool."""
    url = f"{BASE_URL}/api/sessions"
    data = {
        "tool": tool,
        "name": name,
        "model": model
    }

    response = requests.post(url, json=data)
    return response.json()

def start_session(session_id):
    """Start the session agent."""
    url = f"{BASE_URL}/api/sessions/{session_id}/start"
    response = requests.post(url)
    return response.json()

def get_session_status(session_id):
    """Get session status."""
    url = f"{BASE_URL}/api/sessions/{session_id}"
    response = requests.get(url)
    return response.json()

def wait_for_session_announce(session_id, timeout=15):
    """Wait for SESSION_ANNOUNCE (host/port populated)."""
    start = time.time()
    while time.time() - start < timeout:
        status = get_session_status(session_id)
        if status.get("host") and status.get("port"):
            return True, status
        time.sleep(0.5)
    return False, status

def find_session_log(session_id):
    """Find the log file for a session."""
    if not LOGS_DIR.exists():
        return None

    for log_file in LOGS_DIR.glob(f"*_{session_id}.log"):
        return log_file
    return None

def test_tool(tool):
    """Test a single MCP tool."""
    print(f"\n{'='*80}")
    print(f"Testing {tool.upper()}")
    print(f"{'='*80}")

    # Step 1: Create session
    print(f"[1/4] Creating session...")
    result = create_session(tool, f"test-{tool}-routing")

    if not result.get("success"):
        print(f"  ✗ FAILED to create session: {result.get('error')}")
        return {"tool": tool, "status": "FAILED", "error": result.get("error")}

    session_id = result["session"]["session_id"]
    created_tool = result["session"]["tool"]

    if created_tool != tool:
        print(f"  ✗ ROUTING BUG: Expected tool='{tool}', got '{created_tool}'")
        return {
            "tool": tool,
            "status": "ROUTING_BUG",
            "expected": tool,
            "actual": created_tool,
            "session_id": session_id
        }

    print(f"  ✓ Session created: {session_id}")
    print(f"  ✓ Tool correctly routed: {created_tool}")

    # Step 2: Start session
    print(f"[2/4] Starting session agent...")
    start_result = start_session(session_id)

    if not start_result.get("success"):
        print(f"  ✗ FAILED to start agent: {start_result.get('error')}")
        return {
            "tool": tool,
            "status": "START_FAILED",
            "error": start_result.get("error"),
            "session_id": session_id
        }

    print(f"  ✓ Agent started (PID: {start_result.get('pid')})")

    # Step 3: Wait for SESSION_ANNOUNCE
    print(f"[3/4] Waiting for SESSION_ANNOUNCE...")
    announced, status = wait_for_session_announce(session_id)

    if not announced:
        print(f"  ✗ SESSION_ANNOUNCE timeout after 15s")
        print(f"     Status: {status}")
        return {
            "tool": tool,
            "status": "ANNOUNCE_TIMEOUT",
            "session_id": session_id,
            "final_status": status
        }

    print(f"  ✓ SESSION_ANNOUNCE received")
    print(f"     Host: {status.get('host')}")
    print(f"     Port: {status.get('port')}")
    print(f"     Connected: {status.get('connected')}")

    # Step 4: Find session log
    print(f"[4/4] Checking session log...")
    log_file = find_session_log(session_id)

    if not log_file:
        print(f"  ⚠ Log file not found for session {session_id}")
        log_status = "LOG_NOT_FOUND"
    else:
        print(f"  ✓ Log file: {log_file.name}")
        log_status = "LOG_FOUND"

    return {
        "tool": tool,
        "status": "SUCCESS",
        "session_id": session_id,
        "host": status.get("host"),
        "port": status.get("port"),
        "connected": status.get("connected"),
        "log_file": log_file.name if log_file else None,
        "log_status": log_status
    }

def main():
    """Run tests for all MCP tools."""
    print(f"\n{'='*80}")
    print(f"MCP ROUTING & SESSION_ANNOUNCE VERIFICATION")
    print(f"{'='*80}")
    print(f"Testing {len(TOOLS_TO_TEST)} MCP tools...")

    results = []

    for tool in TOOLS_TO_TEST:
        try:
            result = test_tool(tool)
            results.append(result)
            time.sleep(1)  # Brief pause between tests
        except Exception as e:
            print(f"\n  ✗ EXCEPTION: {type(e).__name__}: {e}")
            results.append({
                "tool": tool,
                "status": "EXCEPTION",
                "error": str(e)
            })

    # Summary
    print(f"\n\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")

    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    failed_count = len(results) - success_count

    print(f"Total: {len(results)} tools")
    print(f"Success: {success_count}")
    print(f"Failed: {failed_count}")

    if failed_count > 0:
        print(f"\nFailed tools:")
        for r in results:
            if r["status"] != "SUCCESS":
                print(f"  - {r['tool']}: {r['status']}")
                if "error" in r:
                    print(f"     Error: {r['error']}")

    # Save results to JSON
    output_file = Path("data/test_results/mcp_routing_verification.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "total": len(results),
            "success": success_count,
            "failed": failed_count,
            "results": results
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return success_count == len(results)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
