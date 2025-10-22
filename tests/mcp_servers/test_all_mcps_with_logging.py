#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive MCP Agent Testing with Detailed Logging

This script:
1. Executes specific tasks for each of the 18 MCP agents
2. Monitors event streams in real-time
3. Produces timestamped session logs
4. Generates detailed test reports (JSON + human-readable)
5. Validates task completion and success/failure states
"""

import asyncio
import aiohttp
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from test_mcp_agent_tasks import MCP_AGENT_TASKS, ACTIVE_MCPS, validate_task_result

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:8765"
DEFAULT_MODEL = "openai/gpt-4o-mini"
EVENT_STREAM_TIMEOUT = 60  # Maximum seconds to wait for task completion
RESULTS_DIR = Path("data/test_results")

# Ensure results directory exists
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class TestResult:
    """Container for test execution results"""
    def __init__(self, tool: str, task: str):
        self.tool = tool
        self.task = task
        self.session_id: Optional[str] = None
        self.status: str = "UNKNOWN"  # PASSED, FAILED, ERROR, TIMEOUT
        self.start_time: float = 0
        self.end_time: float = 0
        self.duration: float = 0
        self.error_message: Optional[str] = None
        self.session_log_path: Optional[str] = None
        self.events_captured: List[Dict] = []
        self.result_text: str = ""
        self.validation_matched: List[str] = []
        self.validation_missing: List[str] = []

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "tool": self.tool,
            "task": self.task,
            "session_id": self.session_id,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "error_message": self.error_message,
            "session_log_path": self.session_log_path,
            "events_count": len(self.events_captured),
            "result_text": self.result_text[:500],  # Truncate for JSON
            "validation_matched": self.validation_matched,
            "validation_missing": self.validation_missing
        }


async def create_session(tool: str, task: str, session: aiohttp.ClientSession) -> Optional[str]:
    """Create a new MCP session for the given tool.

    Args:
        tool: MCP tool name
        task: Task description to execute
        session: aiohttp session

    Returns:
        Session ID if successful, None otherwise
    """
    try:
        payload = {
            "tools": [tool],
            "target_tool": tool,
            "name": f"test-{tool}-{int(time.time())}",
            "model": DEFAULT_MODEL,
            "task": task
        }

        async with session.post(f"{API_BASE}/api/sessions", json=payload, timeout=10) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get('success') and 'session' in data:
                    return data['session']['session_id']
    except Exception as e:
        print(f"  [ERROR] Failed to create session: {e}")
    return None


async def start_agent(session_id: str, session: aiohttp.ClientSession) -> bool:
    """Start the agent for the given session.

    Args:
        session_id: Session identifier
        session: aiohttp session

    Returns:
        True if started successfully
    """
    try:
        async with session.post(f"{API_BASE}/api/sessions/{session_id}/start", timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


async def monitor_event_stream(
    session_id: str,
    tool: str,
    session: aiohttp.ClientSession,
    test_result: TestResult
) -> bool:
    """Monitor the event stream and collect events until completion.

    Args:
        session_id: Session identifier
        tool: MCP tool name
        session: aiohttp session
        test_result: TestResult object to populate

    Returns:
        True if task completed successfully
    """
    url = f"{API_BASE}/api/mcp/{tool}/sessions/{session_id}/events"

    try:
        # Wait for agent initialization
        await asyncio.sleep(3)

        timeout_obj = aiohttp.ClientTimeout(total=EVENT_STREAM_TIMEOUT)
        async with session.get(url, timeout=timeout_obj) as resp:
            if resp.status != 200:
                test_result.error_message = f"Event stream returned {resp.status}"
                return False

            print(f"  [INFO] Monitoring event stream...")
            task_complete = False
            error_encountered = False
            result_texts = []

            start_monitor = time.time()

            async for line in resp.content:
                # Check for timeout
                if time.time() - start_monitor > EVENT_STREAM_TIMEOUT:
                    test_result.error_message = "Event stream timeout"
                    test_result.status = "TIMEOUT"
                    return False

                line_str = line.decode('utf-8').strip()
                if line_str.startswith('data:'):
                    try:
                        event_data = json.loads(line_str[5:].strip())
                        test_result.events_captured.append(event_data)

                        event_type = event_data.get('type', '')

                        # Log event with timestamp
                        timestamp = datetime.fromtimestamp(event_data.get('timestamp', time.time()))
                        print(f"    [{timestamp.strftime('%H:%M:%S')}] {event_type}")

                        # Capture result text from various event types
                        if 'message' in event_data:
                            result_texts.append(str(event_data['message']))
                        if 'result' in event_data:
                            result_texts.append(str(event_data['result']))
                        if 'content' in event_data:
                            result_texts.append(str(event_data['content']))

                        # Check for completion or error
                        if 'TASK_COMPLETE' in event_type or 'task.complete' in event_type:
                            task_complete = True
                            print(f"  [SUCCESS] Task completed")
                            break
                        elif 'ERROR' in event_type or 'error' in event_type.lower():
                            error_encountered = True
                            error_msg = event_data.get('error', event_data.get('message', 'Unknown error'))
                            test_result.error_message = str(error_msg)
                            print(f"  [ERROR] Agent error: {error_msg}")

                    except json.JSONDecodeError:
                        continue

            # Compile result text
            test_result.result_text = " ".join(result_texts)

            # Determine success
            if task_complete:
                return True
            elif error_encountered:
                test_result.status = "ERROR"
                return False
            else:
                # Got some events but no explicit completion
                return len(test_result.events_captured) > 0

    except asyncio.TimeoutError:
        test_result.error_message = "Event stream connection timeout"
        test_result.status = "TIMEOUT"
        return False
    except Exception as e:
        test_result.error_message = f"Event stream error: {str(e)}"
        test_result.status = "ERROR"
        return False


async def cleanup_session(session_id: str, session: aiohttp.ClientSession):
    """Stop and delete the test session.

    Args:
        session_id: Session identifier
        session: aiohttp session
    """
    try:
        async with session.post(f"{API_BASE}/api/sessions/{session_id}/stop", timeout=5) as resp:
            pass
        await asyncio.sleep(1)
        async with session.delete(f"{API_BASE}/api/sessions/{session_id}", timeout=5) as resp:
            pass
    except Exception:
        pass  # Ignore cleanup errors


async def test_mcp_tool(tool: str, session: aiohttp.ClientSession) -> TestResult:
    """Execute a test for a single MCP tool.

    Args:
        tool: MCP tool name
        session: aiohttp session

    Returns:
        TestResult object with execution details
    """
    task_def = MCP_AGENT_TASKS[tool]
    task_desc = task_def['task']

    test_result = TestResult(tool, task_desc)
    test_result.start_time = time.time()

    print(f"\n{'='*70}")
    print(f"[{tool.upper()}]")
    print(f"  Task: {task_desc}")
    print(f"{'='*70}")

    try:
        # Step 1: Create session
        print(f"  [1/3] Creating session...")
        session_id = await create_session(tool, task_desc, session)
        if not session_id:
            test_result.status = "FAILED"
            test_result.error_message = "Failed to create session"
            return test_result

        test_result.session_id = session_id
        test_result.session_log_path = f"data/logs/sessions/{session_id}.log"
        print(f"  [OK] Session created: {session_id}")

        # Step 2: Start agent
        print(f"  [2/3] Starting agent...")
        if not await start_agent(session_id, session):
            test_result.status = "FAILED"
            test_result.error_message = "Failed to start agent"
            return test_result
        print(f"  [OK] Agent started")

        # Step 3: Monitor event stream
        print(f"  [3/3] Monitoring task execution...")
        success = await monitor_event_stream(session_id, tool, session, test_result)

        if success:
            # Validate result against expected keywords
            is_valid, matched, missing = validate_task_result(tool, test_result.result_text)
            test_result.validation_matched = matched
            test_result.validation_missing = missing

            if is_valid:
                test_result.status = "PASSED"
                print(f"  [PASSED] Task completed successfully")
                print(f"  [VALIDATION] Matched keywords: {', '.join(matched)}")
            else:
                test_result.status = "FAILED"
                test_result.error_message = f"Validation failed - no expected keywords found"
                print(f"  [FAILED] Validation failed")
                print(f"  [VALIDATION] Missing keywords: {', '.join(missing)}")
        else:
            if test_result.status == "UNKNOWN":
                test_result.status = "FAILED"
            print(f"  [FAILED] Task did not complete successfully")

    except Exception as e:
        test_result.status = "ERROR"
        error_str = str(e).encode('ascii', errors='replace').decode('ascii')
        test_result.error_message = f"Unexpected error: {error_str}"
        print(f"  [ERROR] Unexpected error: {error_str}")

    finally:
        test_result.end_time = time.time()
        test_result.duration = test_result.end_time - test_result.start_time

        # Cleanup
        if test_result.session_id:
            await cleanup_session(test_result.session_id, session)

    return test_result


def generate_reports(results: List[TestResult]):
    """Generate JSON and text test reports.

    Args:
        results: List of TestResult objects
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Calculate statistics
    total = len(results)
    passed = sum(1 for r in results if r.status == "PASSED")
    failed = sum(1 for r in results if r.status == "FAILED")
    errors = sum(1 for r in results if r.status == "ERROR")
    timeouts = sum(1 for r in results if r.status == "TIMEOUT")
    total_duration = sum(r.duration for r in results)

    # Generate JSON report
    json_report = {
        "generated_at": timestamp,
        "summary": {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "timeouts": timeouts,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%",
            "total_duration": f"{total_duration:.1f}s"
        },
        "results": [r.to_dict() for r in results]
    }

    json_path = RESULTS_DIR / f"test_results_{timestamp}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False)

    # Generate text report
    text_path = RESULTS_DIR / f"test_results_{timestamp}.txt"
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("MCP AGENT TASK EXECUTION REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

        for idx, result in enumerate(results, 1):
            status_symbol = "[PASS]" if result.status == "PASSED" else "[FAIL]"
            f.write(f"[{idx}/{total}] {result.tool.upper()}\n")
            f.write(f"  Task: {result.task}\n")
            f.write(f"  Status: {result.status} {status_symbol}\n")
            if result.start_time > 0:
                f.write(f"  Timestamp: {datetime.fromtimestamp(result.start_time).strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"  Duration: {result.duration:.1f}s\n")
            f.write(f"  Events Captured: {len(result.events_captured)}\n")

            if result.validation_matched:
                f.write(f"  Matched Keywords: {', '.join(result.validation_matched)}\n")
            if result.validation_missing:
                f.write(f"  Missing Keywords: {', '.join(result.validation_missing)}\n")

            if result.error_message:
                f.write(f"  Error: {result.error_message}\n")
            if result.session_log_path:
                f.write(f"  Session Log: {result.session_log_path}\n")
            f.write("\n")

        f.write("=" * 70 + "\n")
        f.write("SUMMARY\n")
        f.write("=" * 70 + "\n")
        f.write(f"Total Tests: {total}\n")
        f.write(f"Passed: {passed}\n")
        f.write(f"Failed: {failed}\n")
        f.write(f"Errors: {errors}\n")
        f.write(f"Timeouts: {timeouts}\n")
        f.write(f"Success Rate: {(passed/total*100):.1f}%\n" if total > 0 else "Success Rate: 0%\n")
        f.write(f"Total Duration: {total_duration:.1f}s\n")
        f.write("=" * 70 + "\n")

    return json_path, text_path


async def main():
    """Main test execution"""
    print("=" * 70)
    print("MCP AGENT COMPREHENSIVE TESTING")
    print("=" * 70)
    print(f"Testing {len(ACTIVE_MCPS)} MCP agents with task execution and logging")
    print(f"API Base: {API_BASE}")
    print(f"Model: {DEFAULT_MODEL}")
    print(f"Results Directory: {RESULTS_DIR}")
    print("=" * 70)

    results = []

    async with aiohttp.ClientSession() as session:
        for tool in ACTIVE_MCPS:
            result = await test_mcp_tool(tool, session)
            results.append(result)

            # Brief pause between tests
            await asyncio.sleep(2)

    # Generate reports
    print("\n" + "=" * 70)
    print("GENERATING REPORTS")
    print("=" * 70)

    json_path, text_path = generate_reports(results)

    print(f"\n[REPORTS GENERATED]")
    print(f"  JSON Report: {json_path}")
    print(f"  Text Report: {text_path}")

    # Print summary to console
    passed = sum(1 for r in results if r.status == "PASSED")
    failed = len(results) - passed

    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed} ({passed/len(results)*100:.1f}%)")
    print(f"Failed: {failed} ({failed/len(results)*100:.1f}%)")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
