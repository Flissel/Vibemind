"""
Test remaining MCP agents for SESSION_ANNOUNCE pattern
"""
import sys
import subprocess
import time
import re
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Agents to test
AGENTS_TO_TEST = [
    ("desktop", "List running processes"),
    ("brave-search", "Search for Python tutorials"),
    ("filesystem", "List files in current directory"),
    ("redis", "Get server info")
]

def test_agent(agent_name, task):
    """Test a single agent for SESSION_ANNOUNCE"""
    print(f"\n{'='*80}")
    print(f"Testing: {agent_name}")
    print(f"Task: {task}")
    print(f"{'='*80}")

    # Path to agent
    agent_path = Path(f"src/MCP PLUGINS/servers/{agent_name}/agent.py")
    if not agent_path.exists():
        print(f"❌ Agent not found: {agent_path}")
        return False

    # Generate session ID
    import secrets
    import base64
    session_id = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode('utf-8').rstrip('=')

    # Run agent
    cmd = [
        sys.executable,
        str(agent_path),
        f"--session-id={session_id}",
        f"--task={task}"
    ]

    print(f"Command: {' '.join(cmd)}")
    print(f"Starting agent...")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )

        # Read output for 10 seconds looking for SESSION_ANNOUNCE
        start_time = time.time()
        session_announce_found = False
        host = None
        port = None

        while time.time() - start_time < 10:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    print(f"❌ Agent exited early with code {proc.returncode}")
                    break
                time.sleep(0.1)
                continue

            print(f"  {line.rstrip()}")

            # Check for SESSION_ANNOUNCE
            if "SESSION_ANNOUNCE" in line:
                match = re.search(r'SESSION_ANNOUNCE\s+(\{.*\})', line)
                if match:
                    import json
                    try:
                        data = json.loads(match.group(1))
                        session_announce_found = True
                        host = data.get('host')
                        port = data.get('port')
                        print(f"\n✅ SESSION_ANNOUNCE DETECTED!")
                        print(f"   Host: {host}")
                        print(f"   Port: {port}")
                        break
                    except json.JSONDecodeError as e:
                        print(f"⚠️  SESSION_ANNOUNCE found but JSON parse failed: {e}")

        # Kill process
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except:
            proc.kill()

        if session_announce_found:
            print(f"\n✅ {agent_name}: SUCCESS - SESSION_ANNOUNCE working")
            return True
        else:
            print(f"\n❌ {agent_name}: FAILED - No SESSION_ANNOUNCE detected in 10 seconds")
            return False

    except Exception as e:
        print(f"❌ Error testing {agent_name}: {e}")
        return False

def main():
    """Run all agent tests"""
    print("SESSION_ANNOUNCE Verification - Remaining Agents")
    print("=" * 80)

    results = {}
    for agent_name, task in AGENTS_TO_TEST:
        results[agent_name] = test_agent(agent_name, task)
        time.sleep(2)  # Brief pause between tests

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for agent, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {agent}")

    success_count = sum(1 for s in results.values() if s)
    print(f"\nPassed: {success_count}/{len(results)}")

if __name__ == "__main__":
    main()
