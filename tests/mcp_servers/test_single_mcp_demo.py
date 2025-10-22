#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick demo of single MCP agent testing with logging

This demonstrates how the comprehensive test system works by testing just one agent.
"""

import asyncio
import aiohttp
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from test_mcp_agent_tasks import MCP_AGENT_TASKS

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:8765"
DEMO_TOOL = "time"  # Simple and fast tool for demo


async def test_demo():
    """Run a quick demo test of the time MCP agent"""

    task_def = MCP_AGENT_TASKS[DEMO_TOOL]
    task_desc = task_def['task']

    print("=" * 70)
    print("MCP AGENT TESTING DEMO")
    print("=" * 70)
    print(f"Tool: {DEMO_TOOL}")
    print(f"Task: {task_desc}")
    print("=" * 70)

    async with aiohttp.ClientSession() as session:
        # Step 1: Create session
        print("\n[1/4] Creating session...")
        payload = {
            "tools": [DEMO_TOOL],
            "target_tool": DEMO_TOOL,
            "name": f"demo-{DEMO_TOOL}-{int(time.time())}",
            "model": "openai/gpt-4o-mini",
            "task": task_desc
        }

        try:
            async with session.post(f"{API_BASE}/api/sessions", json=payload, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    session_id = data['session']['session_id']
                    print(f"[OK] Session created: {session_id}")
                    print(f"  Session log: data/logs/sessions/{session_id}.log")
                else:
                    print(f"[FAIL] Failed to create session: {resp.status}")
                    return
        except Exception as e:
            print(f"[ERROR] {e}")
            return

        # Step 2: Start agent
        print("\n[2/4] Starting agent...")
        try:
            async with session.post(f"{API_BASE}/api/sessions/{session_id}/start", timeout=10) as resp:
                if resp.status == 200:
                    print("[OK] Agent started")
                else:
                    print(f"[FAIL] Failed to start agent: {resp.status}")
                    return
        except Exception as e:
            print(f"[ERROR] {e}")
            return

        # Step 3: Monitor event stream
        print("\n[3/4] Monitoring event stream...")
        await asyncio.sleep(3)  # Wait for initialization

        url = f"{API_BASE}/api/mcp/{DEMO_TOOL}/sessions/{session_id}/events"
        events_captured = []
        result_texts = []

        try:
            timeout_obj = aiohttp.ClientTimeout(total=30)
            async with session.get(url, timeout=timeout_obj) as resp:
                if resp.status != 200:
                    print(f"[FAIL] Event stream failed: {resp.status}")
                    return

                print("[OK] Event stream connected")
                print("\nEvents received:")

                start_time = time.time()
                async for line in resp.content:
                    if time.time() - start_time > 20:  # 20 second max
                        break

                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data:'):
                        try:
                            event_data = json.loads(line_str[5:].strip())
                            events_captured.append(event_data)

                            event_type = event_data.get('type', '')
                            timestamp = datetime.fromtimestamp(event_data.get('timestamp', time.time()))

                            print(f"  [{timestamp.strftime('%H:%M:%S')}] {event_type}")

                            # Capture result text
                            if 'message' in event_data:
                                result_texts.append(str(event_data['message']))
                            if 'result' in event_data:
                                result_texts.append(str(event_data['result']))

                            # Check for completion
                            if 'COMPLETE' in event_type or 'complete' in event_type:
                                print("\n[SUCCESS] Task completed!")
                                break

                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            print(f"[ERROR] Event stream error: {e}")

        # Step 4: Summary
        print("\n[4/4] Test Summary")
        print("=" * 70)
        print(f"Total events captured: {len(events_captured)}")
        print(f"Session ID: {session_id}")
        print(f"Session log: data/logs/sessions/{session_id}.log")

        if result_texts:
            print(f"\nResult preview:")
            print(" ", " ".join(result_texts)[:200])

        # Cleanup
        print("\nCleaning up...")
        try:
            async with session.post(f"{API_BASE}/api/sessions/{session_id}/stop", timeout=5) as resp:
                pass
            await asyncio.sleep(1)
            async with session.delete(f"{API_BASE}/api/sessions/{session_id}", timeout=5) as resp:
                pass
            print("[OK] Cleanup complete")
        except:
            pass

        print("\n" + "=" * 70)
        print("DEMO COMPLETE")
        print("=" * 70)
        print("\nFor full testing of all 18 MCP agents, run:")
        print("  python test_all_mcps_with_logging.py")


if __name__ == "__main__":
    asyncio.run(test_demo())
