"""Quick test for windows-core and youtube"""
import sys
import subprocess
import time
import re
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

AGENTS = [
    ("windows-core", "List directory contents"),
    ("youtube", "Get video information")
]

for agent_name, task in AGENTS:
    print(f"\n{'='*80}")
    print(f"Testing: {agent_name}")
    print(f"{'='*80}")

    agent_path = Path(f"src/MCP PLUGINS/servers/{agent_name}/agent.py")

    import secrets, base64
    session_id = base64.urlsafe_b64encode(secrets.token_bytes(16)).decode('utf-8').rstrip('=')

    cmd = [sys.executable, str(agent_path), f"--session-id={session_id}", f"--task={task}"]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1
    )

    start_time = time.time()
    found = False

    while time.time() - start_time < 15:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                print(f"X Agent exited with code {proc.returncode}")
                break
            time.sleep(0.1)
            continue

        print(f"  {line.rstrip()}")

        if "SESSION_ANNOUNCE" in line:
            match = re.search(r'SESSION_ANNOUNCE\s+(\{.*\})', line)
            if match:
                import json
                try:
                    data = json.loads(match.group(1))
                    print(f"\n>>> SUCCESS: {agent_name} - SESSION_ANNOUNCE working")
                    print(f"   Host: {data.get('host')}, Port: {data.get('port')}")
                    found = True
                    break
                except:
                    pass

    try:
        proc.terminate()
        proc.wait(timeout=2)
    except:
        proc.kill()

    if not found:
        print(f"\nX FAILED: {agent_name}")

print("\nDone!")
