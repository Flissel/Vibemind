"""
Test the remaining 5 agents that haven't been verified yet:
tavily, n8n, windows-core, youtube, fetch
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
    ("tavily", "Search for Python tutorials"),
    ("n8n", "Show workflow information"),
    ("windows-core", "List directory contents"),
    ("youtube", "Get video information"),
    ("fetch", "Fetch web page content")
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
        print(f"X Agent not found: {agent_path}")
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

        # Read output for 15 seconds looking for SESSION_ANNOUNCE
        start_time = time.time()
        session_announce_found = False
        host = None
        port = None
        lines_read = 0

        while time.time() - start_time < 15:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    print(f"X Agent exited early with code {proc.returncode}")
                    break
                time.sleep(0.1)
                continue

            lines_read += 1
            if lines_read <= 50:  # Only print first 50 lines
                print(f"  {line.rstrip()}")
            elif lines_read == 51:
                print(f"  ... (truncating output)")

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
                        print(f"\n>>> SESSION_ANNOUNCE DETECTED!")
                        print(f"   Host: {host}")
                        print(f"   Port: {port}")
                        break
                    except json.JSONDecodeError as e:
                        print(f"!  SESSION_ANNOUNCE found but JSON parse failed: {e}")

        # Kill process
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except:
            proc.kill()

        if session_announce_found:
            print(f"\n>>> SUCCESS: {agent_name} - SESSION_ANNOUNCE working")
            return True
        else:
            print(f"\nX FAILED: {agent_name} - No SESSION_ANNOUNCE detected in 15 seconds")
            return False

    except Exception as e:
        print(f"X Error testing {agent_name}: {e}")
        return False

def main():
    """Run all agent tests"""
    print("=" * 80)
    print("SESSION_ANNOUNCE Verification - Remaining 5 Agents")
    print("=" * 80)
    print("Testing: tavily, n8n, windows-core, youtube, fetch")
    print("These agents have not been verified yet")
    print("=" * 80)

    results = {}
    for agent_name, task in AGENTS_TO_TEST:
        results[agent_name] = test_agent(agent_name, task)
        time.sleep(2)  # Brief pause between tests

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY - Remaining Agents Verification")
    print("=" * 80)
    for agent, success in results.items():
        status = ">>> SUCCESS" if success else "X FAILED"
        print(f"{status}: {agent}")

    success_count = sum(1 for s in results.values() if s)
    print(f"\nPassed: {success_count}/{len(results)}")

    if success_count == len(results):
        print("\n>>> All remaining agents are working!")
    else:
        print(f"\n! {len(results) - success_count} agent(s) need fixes")

if __name__ == "__main__":
    main()
