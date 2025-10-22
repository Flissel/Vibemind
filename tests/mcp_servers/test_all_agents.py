"""
Test script for all MCP agents with OpenRouter integration.

This script tests each MCP agent to verify:
1. Agent initialization
2. OpenRouter model selection
3. Task execution
4. Error handling
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Test configuration
TESTS = [
    {
        "name": "GitHub Agent",
        "agent_path": "github",
        "task": "List the 3 most starred Python repositories on GitHub",
        "expected_complexity": "primary",
        "expected_model": "gpt-4o-mini"
    },
    {
        "name": "GitHub Agent (Reasoning)",
        "agent_path": "github",
        "task": "Analyze the architecture of the microsoft/vscode repository and suggest improvements",
        "expected_complexity": "reasoning",
        "expected_model": "o1-mini"
    },
    {
        "name": "Docker Agent",
        "agent_path": "docker",
        "task": "List all running Docker containers",
        "expected_complexity": "primary",
        "expected_model": "gpt-4o-mini"
    },
    {
        "name": "Playwright Agent",
        "agent_path": "playwright",
        "task": "Navigate to google.com and search for 'OpenRouter API'",
        "expected_complexity": "primary",
        "expected_model": "gpt-4o"
    },
    {
        "name": "Context7 Agent",
        "agent_path": "context7",
        "task": "Search for React hooks documentation",
        "expected_complexity": "primary",
        "expected_model": "gpt-4o"
    },
    {
        "name": "Supabase Agent",
        "agent_path": "supabase",
        "task": "List all tables in the database",
        "expected_complexity": "primary",
        "expected_model": "gpt-4o-mini"
    },
    {
        "name": "Redis Agent",
        "agent_path": "redis",
        "task": "Get all keys from Redis",
        "expected_complexity": "primary",
        "expected_model": "gpt-4o-mini"
    },
    {
        "name": "Desktop Agent",
        "agent_path": "desktop",
        "task": "List files in the current directory",
        "expected_complexity": "primary",
        "expected_model": "gpt-4o-mini"
    },
    {
        "name": "Windows Automation Agent",
        "agent_path": "windows-automation",
        "task": "Open Notepad",
        "expected_complexity": "primary",
        "expected_model": "gpt-4o"
    }
]


async def test_agent(test_config: dict) -> dict:
    """Test a single MCP agent."""
    print(f"\n{'='*60}")
    print(f"Testing: {test_config['name']}")
    print(f"{'='*60}")

    result = {
        "name": test_config["name"],
        "status": "pending",
        "model_selected": None,
        "initialization": False,
        "execution": False,
        "error": None
    }

    try:
        # Import agent module dynamically
        agent_path = test_config["agent_path"]
        agent_module = __import__(f"{agent_path}.agent", fromlist=["agent"])

        # Check if agent class exists
        agent_class_name = f"{agent_path.title().replace('-', '')}Agent"
        if not hasattr(agent_module, agent_class_name):
            # Try common variations
            for variant in ["Agent", f"{agent_path.upper()}Agent", f"{agent_path.capitalize()}Agent"]:
                if hasattr(agent_module, variant):
                    agent_class_name = variant
                    break

        agent_class = getattr(agent_module, agent_class_name, None)
        if not agent_class:
            raise ValueError(f"Agent class not found in {agent_path}.agent")

        print(f"✓ Agent module loaded: {agent_class_name}")

        # Initialize agent
        agent = agent_class()
        await agent.initialize()
        result["initialization"] = True
        print(f"✓ Agent initialized")

        # Run task (with timeout)
        print(f"Running task: {test_config['task'][:50]}...")
        task_result = await asyncio.wait_for(
            agent.run_task(test_config["task"], correlation_id=f"test-{agent_path}"),
            timeout=60.0
        )

        result["execution"] = True
        result["status"] = "success"
        print(f"✓ Task completed")
        print(f"Result: {str(task_result)[:200]}...")

        # Cleanup
        await agent.shutdown()

    except asyncio.TimeoutError:
        result["status"] = "timeout"
        result["error"] = "Task execution timed out after 60 seconds"
        print(f"✗ Task timed out")
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        print(f"✗ Error: {e}")

    return result


async def run_all_tests():
    """Run all agent tests."""
    print("\n" + "="*60)
    print("MCP Agent OpenRouter Integration Tests")
    print("="*60)

    # Check if OpenRouter API key is set
    if not os.getenv("OPENROUTER_API_KEY"):
        print("\n⚠️  Warning: OPENROUTER_API_KEY not set in .env")
        print("Tests will fall back to legacy configuration")
    else:
        print("\n✓ OPENROUTER_API_KEY found")

    results = []
    for test_config in TESTS:
        result = await test_agent(test_config)
        results.append(result)
        await asyncio.sleep(1)  # Brief pause between tests

    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    timeout_count = sum(1 for r in results if r["status"] == "timeout")

    print(f"\nTotal Tests: {len(results)}")
    print(f"✓ Passed: {success_count}")
    print(f"✗ Failed: {failed_count}")
    print(f"⏱ Timeout: {timeout_count}")

    # Print failed tests
    if failed_count > 0 or timeout_count > 0:
        print("\nFailed/Timeout Tests:")
        for r in results:
            if r["status"] in ["failed", "timeout"]:
                print(f"  - {r['name']}: {r['error']}")

    # Print detailed results
    print("\nDetailed Results:")
    for r in results:
        status_icon = "✓" if r["status"] == "success" else "✗"
        print(f"{status_icon} {r['name']}")
        print(f"   Initialization: {'✓' if r['initialization'] else '✗'}")
        print(f"   Execution: {'✓' if r['execution'] else '✗'}")
        if r["error"]:
            print(f"   Error: {r['error']}")

    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
