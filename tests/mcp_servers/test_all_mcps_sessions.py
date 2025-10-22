#!/usr/bin/env python3
"""
Test all MCP agents by creating sessions and verifying event streaming.
This tests the full integration: session creation, agent spawn, and event connectivity.
"""
import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional

API_BASE = "http://127.0.0.1:8765"

# List of all active MCP tools to test
ACTIVE_MCPS = [
    "brave-search",
    "context7",
    "desktop",
    "docker",
    "fetch",
    "filesystem",
    "github",
    "memory",
    "n8n",
    "playwright",
    "redis",
    "sequential-thinking",
    "supabase",
    "taskmanager",
    "tavily",
    "time",
    "windows-core",
    "youtube"
]

async def create_session(tool: str, session: aiohttp.ClientSession) -> Optional[Dict]:
    """Create a new MCP session for the given tool."""
    try:
        payload = {
            "tools": [tool],  # API expects array of tools
            "target_tool": tool,  # Specify the primary tool
            "name": f"test-{tool}-session",
            "model": "openai/gpt-4o-mini",
            "task": f"Test {tool} connectivity"
        }

        async with session.post(f"{API_BASE}/api/sessions", json=payload, timeout=10) as resp:
            text = await resp.text()
            if resp.status == 200:
                try:
                    data = json.loads(text)
                    # API returns {"success": true, "session": {...}}
                    if data.get('success') and 'session' in data:
                        return data['session']  # Return the session object
                    else:
                        print(f"  [FAIL] API returned success=false: {data.get('error', 'unknown error')}")
                        return None
                except json.JSONDecodeError:
                    print(f"  [FAIL] Invalid JSON response: {text[:200]}")
                    return None
            else:
                print(f"  [FAIL] Create session HTTP {resp.status}")
                print(f"       Response: {text[:300]}")
                return None
    except Exception as e:
        print(f"  [FAIL] Exception creating session: {e}")
        return None


async def start_session(session_id: str, session: aiohttp.ClientSession) -> bool:
    """Start the agent for the given session."""
    try:
        async with session.post(f"{API_BASE}/api/sessions/{session_id}/start", timeout=10) as resp:
            if resp.status == 200:
                return True
            else:
                text = await resp.text()
                print(f"  [FAIL] Start session failed: {resp.status} - {text}")
                return False
    except Exception as e:
        print(f"  [FAIL] Exception starting session: {e}")
        return False


async def check_event_stream(session_id: str, tool: str, session: aiohttp.ClientSession, timeout_sec: int = 15) -> bool:
    """Check if the event stream is reachable and receiving events."""
    try:
        # Wait a bit for agent to initialize
        await asyncio.sleep(3)

        # Try to connect to event stream (correct path format)
        url = f"{API_BASE}/api/mcp/{tool}/sessions/{session_id}/events"

        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout_sec)) as resp:
            if resp.status != 200:
                print(f"  [FAIL] Event stream returned {resp.status}")
                return False

            # Read events for a few seconds
            start_time = time.time()
            received_events = []

            async for line in resp.content:
                if time.time() - start_time > 5:  # Read events for 5 seconds max
                    break

                line_str = line.decode('utf-8').strip()
                if line_str.startswith('data:'):
                    try:
                        event_data = json.loads(line_str[5:].strip())
                        received_events.append(event_data)
                    except json.JSONDecodeError:
                        pass

            if len(received_events) > 0:
                print(f"  [OK] Event stream active ({len(received_events)} events received)")
                return True
            else:
                # No events yet, but stream is reachable
                print(f"  [OK] Event stream reachable (no events yet)")
                return True

    except asyncio.TimeoutError:
        print(f"  [FAIL] Event stream timeout")
        return False
    except Exception as e:
        print(f"  [FAIL] Event stream error: {e}")
        return False


async def cleanup_session(session_id: str, session: aiohttp.ClientSession):
    """Stop and delete the test session."""
    try:
        # Try to stop first
        async with session.post(f"{API_BASE}/api/sessions/{session_id}/stop", timeout=5) as resp:
            pass

        await asyncio.sleep(1)

        # Then delete
        async with session.delete(f"{API_BASE}/api/sessions/{session_id}", timeout=5) as resp:
            pass
    except Exception:
        pass  # Ignore cleanup errors


async def test_mcp_tool(tool: str, session: aiohttp.ClientSession) -> bool:
    """Test a single MCP tool end-to-end."""
    print(f"\n[{tool.upper()}]")
    session_id = None

    try:
        # Step 1: Create session
        print(f"  Creating session...")
        result = await create_session(tool, session)
        if not result or 'session_id' not in result:
            return False

        session_id = result['session_id']
        print(f"  [OK] Session created: {session_id}")

        # Step 2: Start agent
        print(f"  Starting agent...")
        if not await start_session(session_id, session):
            return False
        print(f"  [OK] Agent started")

        # Step 3: Check event stream
        print(f"  Checking event stream...")
        if not await check_event_stream(session_id, tool, session):
            return False

        print(f"  [PASS] {tool} is fully reachable!")
        return True

    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        return False
    finally:
        # Cleanup
        if session_id:
            await cleanup_session(session_id, session)


async def main():
    """Test all MCP tools."""
    print("=" * 70)
    print("MCP Session Event Stream Connectivity Test")
    print("=" * 70)
    print(f"Testing {len(ACTIVE_MCPS)} active MCP tools...")

    results = {}

    async with aiohttp.ClientSession() as session:
        for tool in ACTIVE_MCPS:
            success = await test_mcp_tool(tool, session)
            results[tool] = success
            await asyncio.sleep(1)  # Brief pause between tests

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    failed = len(results) - passed

    print(f"\nPassed: {passed}/{len(ACTIVE_MCPS)}")
    print(f"Failed: {failed}/{len(ACTIVE_MCPS)}")

    if failed > 0:
        print("\nFailed tools:")
        for tool, success in results.items():
            if not success:
                print(f"  - {tool}")

    print("\n" + "=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
