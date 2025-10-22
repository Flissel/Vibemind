# n8n MCP Setup Guide

**Date**: 2025-10-10
**Purpose**: Configure n8n MCP server for workflow automation in Sakana Desktop Assistant

---

## Overview

The n8n MCP server enables AI assistants to interact with n8n workflows, create automations, and manage n8n API operations. It uses the `n8n-mcp` npm package and requires a running n8n instance.

---

## Prerequisites

### 1. Node.js
- **Required Version**: Node.js v18.17.0+ (recommended), v20, or v22
- Check version: `node --version`

### 2. n8n Instance
You need a **running n8n instance** with API access. Choose one option:

#### Option A: Local n8n (Recommended for Development)
```bash
# Install n8n globally
npm install -g n8n

# Start n8n (will run on http://localhost:5678)
n8n start

# Or run with Docker
docker run -it --rm \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

#### Option B: n8n Cloud
- Sign up at https://n8n.io/
- Get your instance URL and API key from settings

#### Option C: Self-Hosted n8n
- Deploy n8n on your server following: https://docs.n8n.io/hosting/

---

## Configuration Steps

### Step 1: Get n8n API Key

#### For Local/Self-Hosted n8n:
1. Access n8n web UI (usually http://localhost:5678)
2. Go to **Settings** → **API**
3. Click **Create API Key**
4. Copy the generated API key

#### For n8n Cloud:
1. Log in to your n8n cloud instance
2. Go to **Settings** → **API Keys**
3. Create a new API key
4. Copy the key

### Step 2: Configure Environment Variables

Create or edit `.env` file in the project root:

```bash
# n8n MCP Configuration
N8N_API_URL=http://localhost:5678/api/v1
N8N_API_KEY=your_n8n_api_key_here

# Optional: Webhook authentication
N8N_WEBHOOK_USERNAME=your_webhook_username
N8N_WEBHOOK_PASSWORD=your_webhook_password
```

**For n8n Cloud**, replace with your cloud URL:
```bash
N8N_API_URL=https://your-instance.app.n8n.cloud/api/v1
N8N_API_KEY=your_cloud_api_key
```

### Step 3: Verify Configuration

The n8n MCP is already configured in `src/MCP PLUGINS/servers/servers.json`:

```json
{
  "name": "n8n",
  "active": true,
  "type": "stdio",
  "command": "C:\\Windows\\System32\\cmd.exe",
  "args": [
    "/c",
    "npx",
    "-y",
    "n8n-mcp"
  ],
  "read_timeout_seconds": 120,
  "env_vars": {
    "N8N_API_URL": "env:N8N_API_URL",
    "N8N_API_KEY": "env:N8N_API_KEY",
    "MCP_MODE": "stdio",
    "LOG_LEVEL": "error"
  },
  "description": "n8n MCP for workflow automation, node documentation, and n8n API integration"
}
```

### Step 4: Test the Connection

Create a test script:

```python
# test_n8n_mcp.py
import subprocess
import json
import sys

# Test if n8n MCP can be invoked
cmd = [
    sys.executable,
    "src/MCP PLUGINS/servers/n8n/agent.py",
    json.dumps({
        "session_id": "test-n8n-123",
        "name": "test-n8n",
        "model": "openai/gpt-4o-mini",
        "task": "List available workflows",
        "n8n_api_url": "http://localhost:5678/api/v1",
        "n8n_api_key": "your_api_key_here"
    })
]

proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

stdout, stderr = proc.communicate(timeout=30)
print("STDOUT:", stdout)
print("STDERR:", stderr)
print("Exit Code:", proc.returncode)
```

---

## n8n MCP Capabilities

Once configured, the n8n MCP provides:

### Workflow Management
- **List workflows**: Get all available workflows
- **Create workflow**: Build new automation workflows
- **Execute workflow**: Trigger workflow execution
- **Get workflow details**: Inspect workflow configuration

### Node Operations
- **List nodes**: Get available n8n node types (525+ nodes)
- **Node documentation**: Access node configuration and usage
- **Search nodes**: Find specific nodes by category

### API Integration
- **Webhooks**: Configure webhook triggers
- **Credentials**: Manage API credentials for integrations
- **Executions**: View and monitor workflow execution history

---

## Usage Examples

### Example 1: Create n8n Session via API

```bash
curl -X POST "http://127.0.0.1:8765/api/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "n8n",
    "name": "workflow-automation",
    "model": "openai/gpt-4o-mini",
    "task": "Create a workflow that monitors GitHub issues and sends Slack notifications"
  }'
```

### Example 2: Direct Agent Invocation

```bash
python "src/MCP PLUGINS/servers/n8n/agent.py" '{
  "session_id": "n8n-test-456",
  "name": "test-workflow",
  "model": "openai/gpt-4o-mini",
  "task": "List all active workflows",
  "n8n_api_url": "http://localhost:5678/api/v1",
  "n8n_api_key": "your_api_key"
}'
```

---

## Troubleshooting

### Error: "Expecting value: line 1 column 1"
**Cause**: Agent expects JSON config as first argument, not `--session-id` flags

**Fix**: Use JSON config format:
```bash
python agent.py '{"session_id":"...","name":"...","model":"...","task":"..."}'
```

### Error: "Connection refused" or "API unreachable"
**Cause**: n8n instance not running or wrong URL

**Fix**:
1. Start n8n: `n8n start` or `docker run -p 5678:5678 n8nio/n8n`
2. Verify URL: `curl http://localhost:5678/api/v1/workflows`
3. Check firewall settings

### Error: "Unauthorized" or "Invalid API key"
**Cause**: Wrong or missing API key

**Fix**:
1. Regenerate API key in n8n settings
2. Update `.env` file
3. Restart the application

### Error: "MCP_MODE not recognized"
**Cause**: Old version of n8n-mcp package

**Fix**:
```bash
# Clear npm cache and reinstall
npx clear-npx-cache
npx -y n8n-mcp@latest
```

---

## Architecture Notes

### n8n MCP vs Other MCP Agents

**Different Invocation Pattern**:
- Most MCP agents: `agent.py --session-id=... --task=...`
- n8n MCP: `agent.py '{"session_id":"...","task":"..."}'`

**SESSION_ANNOUNCE Implementation**:
```python
# n8n uses EventServer pattern
await self.event_server.send_event({
    "type": MCP_EVENT_SESSION_ANNOUNCE,
    "session_id": self.session_id,
    "host": "127.0.0.1",
    "port": self.event_port,
    "status": SESSION_STATE_CREATED,
    "timestamp": time.time()
})
```

This is **different from** the standard print-based pattern:
```python
# Standard pattern (used by Desktop, GitHub, etc.)
print(f"SESSION_ANNOUNCE {json.dumps(announce_data)}", flush=True)
```

### Integration with MCPSessionManager

To properly integrate n8n MCP with the backend, update `src/ui/mcp_session_manager.py`:

```python
def spawn_mcp_session_agent(self, tool: str, session_id: str, ...):
    # ...
    if tool in ['n8n', 'tavily']:
        # Use JSON config argument
        config_dict = {
            "session_id": session_id,
            "name": name or f"{tool}-session",
            "model": model or "openai/gpt-4o-mini",
            "task": task or "Default task",
        }

        # Add tool-specific config
        if tool == "n8n":
            config_dict["n8n_api_url"] = os.getenv("N8N_API_URL")
            config_dict["n8n_api_key"] = os.getenv("N8N_API_KEY")

        cmd = [python_exe, agent_path, json.dumps(config_dict)]
    else:
        # Use flags for other agents
        cmd = [python_exe, agent_path, f"--session-id={session_id}", ...]
```

---

## Example Workflows

### Workflow 1: GitHub Issue to Slack Notification
```
1. Webhook Trigger (GitHub issue created)
2. Filter issues by label
3. Format message
4. Send to Slack channel
```

### Workflow 2: Daily Report Generator
```
1. Scheduled trigger (daily 9 AM)
2. Fetch data from database
3. Generate summary report
4. Send email with report
```

### Workflow 3: AI Content Generator
```
1. Manual trigger
2. Call OpenAI API for content
3. Post-process result
4. Save to Google Docs
```

---

## Security Best Practices

1. **API Key Storage**: Store API keys in `.env`, never in code
2. **Network Security**: Use HTTPS for production n8n instances
3. **Access Control**: Limit API key permissions to required operations only
4. **Firewall**: Only expose n8n ports to trusted networks
5. **Regular Updates**: Keep n8n and n8n-mcp package updated

---

## Resources

### Official Documentation
- n8n Docs: https://docs.n8n.io/
- n8n MCP Integration: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcptrigger/
- n8n API Reference: https://docs.n8n.io/api/

### Community
- n8n Community Forum: https://community.n8n.io/
- MCP + n8n Tutorial: https://community.n8n.io/t/model-context-protocol-mcp-n8n-explained/96165

### GitHub
- n8n-mcp Package: https://github.com/nerding-io/n8n-nodes-mcp
- n8n MCP Server: https://github.com/leonardsellem/n8n-mcp-server

---

## Quick Start Checklist

- [ ] Install Node.js v18.17.0+
- [ ] Install and start n8n instance
- [ ] Create n8n API key
- [ ] Add `N8N_API_URL` and `N8N_API_KEY` to `.env`
- [ ] Verify n8n is accessible: `curl http://localhost:5678/api/v1/workflows`
- [ ] Test n8n MCP agent with JSON config
- [ ] Check SESSION_ANNOUNCE in logs
- [ ] Create first test workflow

---

**Status**: n8n MCP requires running n8n instance. SESSION_ANNOUNCE is correctly implemented via EventServer pattern.
