"""
Comprehensive MCP Agent Execution Test Suite

This script executes real tasks on each MCP agent to verify:
1. OpenRouter integration
2. Model selection
3. Task execution
4. Result generation

Each agent is tested with a task specific to its MCP capabilities.
"""
import asyncio
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(env_path)

# Test configuration with real tasks for each agent
AGENT_TESTS = [
    {
        "name": "GitHub",
        "agent": "github",
        "tasks": [
            {
                "description": "List popular Python repositories",
                "task": "Search for the top 3 most starred Python repositories on GitHub",
                "expected_model": "gpt-4o-mini",
                "timeout": 30
            },
            {
                "description": "Analyze repository structure (reasoning)",
                "task": "Analyze the architecture of the tensorflow/tensorflow repository",
                "expected_model": "o1-mini",
                "timeout": 60
            }
        ]
    },
    {
        "name": "Docker",
        "agent": "docker",
        "tasks": [
            {
                "description": "List running containers",
                "task": "List all Docker containers currently running on the system",
                "expected_model": "gpt-4o-mini",
                "timeout": 30
            },
            {
                "description": "Design container orchestration (reasoning)",
                "task": "Design a Docker Compose setup for a microservices architecture with Redis, PostgreSQL, and a Node.js API",
                "expected_model": "o1-mini",
                "timeout": 60
            }
        ]
    },
    {
        "name": "Playwright",
        "agent": "playwright",
        "tasks": [
            {
                "description": "Navigate to website",
                "task": "Navigate to https://example.com and capture a screenshot",
                "expected_model": "gpt-4o",
                "timeout": 45
            }
        ]
    },
    {
        "name": "Context7",
        "agent": "context7",
        "tasks": [
            {
                "description": "Search documentation",
                "task": "Search for React hooks documentation and summarize useState",
                "expected_model": "gpt-4o",
                "timeout": 30
            }
        ]
    },
    {
        "name": "Supabase",
        "agent": "supabase",
        "tasks": [
            {
                "description": "List database tables",
                "task": "List all tables in the Supabase database",
                "expected_model": "gpt-4o-mini",
                "timeout": 30
            },
            {
                "description": "Design database schema (reasoning)",
                "task": "Design a database schema for a multi-tenant SaaS application with user authentication, subscriptions, and audit logs",
                "expected_model": "o1-mini",
                "timeout": 60
            }
        ]
    },
    {
        "name": "Redis",
        "agent": "redis",
        "tasks": [
            {
                "description": "Get Redis info",
                "task": "Get Redis server information and list all keys",
                "expected_model": "gpt-4o-mini",
                "timeout": 30
            }
        ]
    },
    {
        "name": "Desktop",
        "agent": "desktop",
        "tasks": [
            {
                "description": "List files in current directory",
                "task": "List all Python files in the current directory",
                "expected_model": "gpt-4o-mini",
                "timeout": 30
            }
        ]
    },
    {
        "name": "Windows Automation",
        "agent": "windows-automation",
        "tasks": [
            {
                "description": "Get system information",
                "task": "Get Windows system information including OS version and hostname",
                "expected_model": "gpt-4o",
                "timeout": 30
            }
        ]
    }
]


class TestRunner:
    """Test runner for MCP agents via REST API."""

    def __init__(self, api_base="http://127.0.0.1:8765/api"):
        self.api_base = api_base
        self.results = []

    async def create_session(self, agent: str, task: str) -> Dict[str, Any]:
        """Create a test session via REST API."""
        import aiohttp

        payload = {
            "name": f"test-{agent}-{int(time.time())}",
            "model": "gpt-4",
            "tools": [agent],
            "task": task
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/sessions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("session", {})
                else:
                    raise Exception(f"Failed to create session: {response.status}")

    async def start_session(self, session_id: str) -> Dict[str, Any]:
        """Start a session."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/sessions/{session_id}/start",
                json={},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to start session: {response.status}")

    async def get_events(self, agent: str, session_id: str) -> Dict[str, Any]:
        """Get session events."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_base}/mcp/{agent}/sessions/{session_id}/events"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to get events: {response.status}")

    async def run_test(self, agent_name: str, agent: str, test: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case."""
        print(f"\n{'='*70}")
        print(f"Testing: {agent_name} - {test['description']}")
        print(f"{'='*70}")
        print(f"Task: {test['task']}")
        print(f"Expected model: {test['expected_model']}")
        print(f"Timeout: {test['timeout']}s")

        result = {
            "agent": agent_name,
            "description": test['description'],
            "task": test['task'],
            "expected_model": test['expected_model'],
            "status": "pending",
            "actual_model": None,
            "openrouter_used": False,
            "error": None,
            "execution_time": 0
        }

        start_time = time.time()

        try:
            # Create session
            print("\n1. Creating session...")
            session_data = await self.create_session(agent, test['task'])
            session_id = session_data.get("session_id")

            if not session_id:
                raise Exception("No session ID returned")

            print(f"   [OK] Session created: {session_id}")

            # Start session
            print("2. Starting session...")
            start_result = await self.start_session(session_id)
            pid = start_result.get("pid")

            if not pid:
                raise Exception("No PID returned")

            print(f"   [OK] Session started (PID: {pid})")

            # Wait for execution
            print(f"3. Waiting {test['timeout']}s for task execution...")
            await asyncio.sleep(min(test['timeout'], 15))  # Cap wait time

            # Get events
            print("4. Fetching events...")
            events_data = await self.get_events(agent, session_id)
            events = events_data.get("events", [])

            print(f"   [OK] Retrieved {len(events)} events")

            # Analyze events
            openrouter_logs = [e for e in events if "OpenRouter" in str(e.get("payload", {}).get("message", ""))]
            error_events = [e for e in events if e.get("type") == "error"]

            if openrouter_logs:
                result["openrouter_used"] = True
                # Extract model from log
                for log in openrouter_logs:
                    msg = log.get("payload", {}).get("message", "")
                    if "Using model:" in msg:
                        model = msg.split("Using model:")[-1].split("for")[0].strip()
                        result["actual_model"] = model
                        print(f"\n   [OK] OpenRouter used: {model}")
                        break

            if error_events:
                error_count = len(error_events)
                print(f"\n   [WARN] {error_count} errors detected")
                result["error"] = f"{error_count} errors during execution"

            # Check if model matches expectation
            if result["actual_model"] == test["expected_model"]:
                print(f"   [OK] Correct model selected!")
                result["status"] = "success"
            elif result["actual_model"]:
                print(f"   [WARN] Different model: {result['actual_model']} (expected: {test['expected_model']})")
                result["status"] = "partial"
            else:
                print(f"   [WARN] OpenRouter not detected (legacy fallback)")
                result["status"] = "fallback"

            result["execution_time"] = time.time() - start_time

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            result["execution_time"] = time.time() - start_time
            print(f"\n   [FAIL] Test failed: {e}")

        return result

    async def run_all_tests(self):
        """Run all agent tests."""
        print("\n" + "="*70)
        print("MCP Agent Comprehensive Execution Test Suite")
        print("="*70)

        # Check OpenRouter API key
        if not os.getenv("OPENROUTER_API_KEY"):
            print("\n[WARNING] OPENROUTER_API_KEY not set in .env")
            print("Tests will fall back to legacy configuration")
        else:
            print("\n[OK] OPENROUTER_API_KEY configured")

        # Run all tests
        for agent_config in AGENT_TESTS:
            agent_name = agent_config["name"]
            agent = agent_config["agent"]
            tasks = agent_config["tasks"]

            for test in tasks:
                result = await self.run_test(agent_name, agent, test)
                self.results.append(result)
                await asyncio.sleep(2)  # Brief pause between tests

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*70)
        print("Test Summary")
        print("="*70)

        total = len(self.results)
        success = sum(1 for r in self.results if r["status"] == "success")
        partial = sum(1 for r in self.results if r["status"] == "partial")
        fallback = sum(1 for r in self.results if r["status"] == "fallback")
        failed = sum(1 for r in self.results if r["status"] == "failed")

        print(f"\nTotal Tests: {total}")
        print(f"[PASS] Success (correct model): {success}")
        print(f"[WARN] Partial (different model): {partial}")
        print(f"[WARN] Fallback (legacy config): {fallback}")
        print(f"[FAIL] Failed: {failed}")

        # OpenRouter usage
        openrouter_count = sum(1 for r in self.results if r["openrouter_used"])
        print(f"\nOpenRouter Integration: {openrouter_count}/{total} tests")

        # Detailed results
        print("\n" + "="*70)
        print("Detailed Results")
        print("="*70)

        for r in self.results:
            status_icon = {
                "success": "[PASS]",
                "partial": "[WARN]",
                "fallback": "[WARN]",
                "failed": "[FAIL]"
            }.get(r["status"], "[?]")

            print(f"\n{status_icon} {r['agent']} - {r['description']}")
            print(f"   Expected: {r['expected_model']}")
            print(f"   Actual: {r['actual_model'] or 'N/A'}")
            print(f"   OpenRouter: {'Yes' if r['openrouter_used'] else 'No'}")
            print(f"   Time: {r['execution_time']:.2f}s")
            if r['error']:
                print(f"   Error: {r['error']}")

        # Save results to JSON
        output_file = "test_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                "summary": {
                    "total": total,
                    "success": success,
                    "partial": partial,
                    "fallback": fallback,
                    "failed": failed,
                    "openrouter_used": openrouter_count
                },
                "results": self.results
            }, f, indent=2)

        print(f"\n[OK] Detailed results saved to: {output_file}")


async def main():
    """Main entry point."""
    try:
        # Check if aiohttp is available
        import aiohttp
    except ImportError:
        print("Error: aiohttp required. Install with: pip install aiohttp")
        return 1

    runner = TestRunner()
    await runner.run_all_tests()

    # Exit code based on results
    failed_count = sum(1 for r in runner.results if r["status"] == "failed")
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
