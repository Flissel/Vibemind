#!/usr/bin/env python3
"""
Test script for Time and Fetch MCP agents
Verifies that both agents have correct file structure and can be imported
"""
import os
import sys
from pathlib import Path

def test_agent_structure(agent_name: str) -> tuple[bool, list[str]]:
    """Test that an agent has the required file structure.

    Args:
        agent_name: Name of the agent directory (e.g., 'time', 'fetch')

    Returns:
        Tuple of (success: bool, errors: list[str])
    """
    errors = []
    base_dir = Path(__file__).parent / agent_name

    if not base_dir.exists():
        errors.append(f"Directory not found: {base_dir}")
        return False, errors

    # Check required files
    required_files = [
        'agent.py',
        f'{agent_name}_constants.py',
        'event_task.py',
        'user_interaction_utils.py'
    ]

    for file in required_files:
        file_path = base_dir / file
        if not file_path.exists():
            errors.append(f"Missing file: {file}")
        else:
            # Try to compile the file to check for syntax errors
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), str(file_path), 'exec')
            except SyntaxError as e:
                errors.append(f"Syntax error in {file}: {e}")

    return len(errors) == 0, errors


def test_servers_json_entry(agent_name: str) -> tuple[bool, list[str]]:
    """Test that the agent is registered in servers.json.

    Args:
        agent_name: Name of the agent (e.g., 'time', 'fetch')

    Returns:
        Tuple of (success: bool, errors: list[str])
    """
    errors = []
    servers_json_path = Path(__file__).parent / "servers.json"

    if not servers_json_path.exists():
        errors.append("servers.json not found")
        return False, errors

    try:
        import json
        with open(servers_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Find the agent entry
        found = False
        for server in data.get("servers", []):
            if server.get("name") == agent_name:
                found = True
                if not server.get("active", False):
                    errors.append(f"{agent_name} is marked as inactive in servers.json")
                break

        if not found:
            errors.append(f"{agent_name} not found in servers.json")

    except Exception as e:
        errors.append(f"Error reading servers.json: {e}")

    return len(errors) == 0, errors


def test_dynamic_discovery(agent_name: str) -> tuple[bool, list[str]]:
    """Test that the agent is discoverable by the dynamic discovery system.

    Args:
        agent_name: Name of the agent (e.g., 'time', 'fetch')

    Returns:
        Tuple of (success: bool, errors: list[str])
    """
    errors = []
    agent_path = Path(__file__).parent / agent_name / "agent.py"

    if not agent_path.exists():
        errors.append(f"agent.py not found for dynamic discovery")
        return False, errors

    # Verify the agent.py has the expected structure
    try:
        with open(agent_path, 'r', encoding='utf-8') as f:
            content = f.read()

            # Check for required imports and classes
            required_patterns = [
                'import asyncio',
                'from autogen_ext',
                'async def main():',
                'asyncio.run(main())'
            ]

            for pattern in required_patterns:
                if pattern not in content:
                    errors.append(f"Missing pattern in agent.py: {pattern}")

    except Exception as e:
        errors.append(f"Error reading agent.py: {e}")

    return len(errors) == 0, errors


def main():
    """Run all tests for Time and Fetch agents."""
    print("=" * 60)
    print("Testing Time and Fetch MCP Agents")
    print("=" * 60)

    agents_to_test = ['time', 'fetch']
    all_passed = True

    for agent_name in agents_to_test:
        print(f"\n[{agent_name.upper()}] Testing agent structure...")

        # Test 1: File structure
        success, errors = test_agent_structure(agent_name)
        if success:
            print(f"  [OK] File structure complete")
        else:
            print(f"  [FAIL] File structure errors:")
            for error in errors:
                print(f"    - {error}")
            all_passed = False

        # Test 2: servers.json registration
        success, errors = test_servers_json_entry(agent_name)
        if success:
            print(f"  [OK] Registered in servers.json")
        else:
            print(f"  [FAIL] servers.json errors:")
            for error in errors:
                print(f"    - {error}")
            all_passed = False

        # Test 3: Dynamic discovery compatibility
        success, errors = test_dynamic_discovery(agent_name)
        if success:
            print(f"  [OK] Dynamic discovery compatible")
        else:
            print(f"  [FAIL] Dynamic discovery errors:")
            for error in errors:
                print(f"    - {error}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("All tests PASSED - Time and Fetch agents ready!")
        print("=" * 60)
        return 0
    else:
        print("Some tests FAILED - see errors above")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
