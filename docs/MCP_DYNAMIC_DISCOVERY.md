# MCP Dynamic Discovery System

## Overview

The Sakana Desktop Assistant now automatically discovers MCP (Model Context Protocol) agents from the filesystem, eliminating the need to manually update configuration files when adding new MCP servers.

## How It Works

### 1. Automatic Agent Discovery

**Location:** `src/gui/config.py`

The `_discover_mcp_agents()` function automatically scans `src/MCP PLUGINS/servers/` for subdirectories containing `agent.py` files and registers them in the `MCP_TOOL_AGENT_PATHS` dictionary.

```python
# Before: Manual hardcoded list
MCP_TOOL_AGENT_PATHS = {
    'github': 'MCP PLUGINS/servers/github/agent.py',
    'docker': 'MCP PLUGINS/servers/docker/agent.py',
    # ... more entries
}

# After: Dynamic auto-discovery
MCP_TOOL_AGENT_PATHS = {}
_discover_mcp_agents()  # Auto-populates on module load
```

### 2. Server Metadata Loading

**Function:** `get_mcp_server_metadata()`

Loads additional metadata from `servers.json` including:
- Active status (`active: true/false`)
- Description
- Server type (`stdio`, etc.)
- Whether the server has an agent.py file

### 3. API Integration

**Location:** `src/ui/session_api.py`

The `/api/mcp/tools` endpoint now returns enhanced tool information:

```json
{
  "tools": [
    {
      "name": "n8n",
      "description": "n8n MCP for workflow automation...",
      "has_agent": true,
      "type": "stdio"
    }
  ]
}
```

## Benefits

1. **Zero Configuration**: Add a new MCP server by just creating `agent.py` in a new directory
2. **Automatic Registration**: No need to edit `config.py` or other files
3. **Metadata Enrichment**: Automatically combines filesystem discovery with `servers.json` metadata
4. **Error Prevention**: Eliminates risk of forgetting to update configuration files

## Adding New MCP Servers

### Quick Start

1. Create directory: `src/MCP PLUGINS/servers/your-tool/`
2. Add `agent.py` with Society of Mind implementation
3. Add entry to `servers.json`:
   ```json
   {
     "name": "your-tool",
     "active": true,
     "type": "stdio",
     "command": "cmd.exe",
     "args": ["/c", "npx", "-y", "your-mcp-package"],
     "read_timeout_seconds": 120,
     "description": "Your tool description"
   }
   ```
4. Restart the assistant - your tool is automatically discovered!

### Required Files

**Minimum files for Society of Mind agent:**
```
your-tool/
├── agent.py                    # Main agent (required)
├── your_tool_constants.py      # Agent prompts
├── event_task.py               # UI server
└── user_interaction_utils.py   # User clarification tool
```

## Current Status

### Discovered Agents (15 total)

- brave-search
- context7
- desktop
- docker
- filesystem
- github
- memory
- **n8n** (newly added)
- playwright
- redis
- **sequential-thinking** (newly added)
- supabase
- **taskmanager** (newly added)
- windows-core
- youtube

### Recently Added Agents

1. **n8n** - Workflow automation and node documentation
2. **taskmanager** - Task tracking with approval workflows
3. **sequential-thinking** - Dynamic problem-solving with structured reasoning

## Testing

Run the test script to verify discovery:

```bash
python test_mcp_discovery.py
```

Expected output:
```
=== Dynamic MCP Discovery Test ===

Total agents discovered: 15
Active servers: 17
Servers with agents: 15

=== Newly Added Agents ===
  [OK] n8n: MCP PLUGINS/servers/n8n/agent.py
    - Active: True
    - Has Agent: True
  [OK] taskmanager: MCP PLUGINS/servers/taskmanager/agent.py
    - Active: True
    - Has Agent: True
  [OK] sequential-thinking: MCP PLUGINS/servers/sequential-thinking/agent.py
    - Active: True
    - Has Agent: True
```

## Technical Details

### Path Resolution

The discovery system resolves paths relative to the project root:
- `config.py` is at: `src/gui/config.py`
- Project root: `Path(__file__).resolve().parent.parent.parent`
- Servers directory: `{project_root}/src/MCP PLUGINS/servers/`

### Logging

Discovery events are logged at INFO level:
```
INFO: Discovered 15 MCP agents: ['brave-search', 'context7', ...]
INFO: Loaded metadata for 23 MCP servers
```

### Integration Points

1. **GUI Server**: Uses `MCP_TOOL_AGENT_PATHS` for session spawning
2. **Session Manager**: Validates tool names against `supported_tools`
3. **API Endpoints**: Enriches tool listings with metadata
4. **Documentation**: Auto-updated in CLAUDE.md

## Future Enhancements

Potential improvements:
- Hot-reload detection for new agents without restart
- Agent health checks and validation
- Dependency resolution between agents
- Version tracking for agents
- Agent capability introspection

## Migration Notes

### Before Dynamic Discovery

To add a new MCP agent, you had to:
1. Create agent files
2. Edit `src/gui/config.py` to add to `MCP_TOOL_AGENT_PATHS`
3. Edit `CLAUDE.md` to document the new agent
4. Risk of forgetting to update all locations

### After Dynamic Discovery

To add a new MCP agent, you only need to:
1. Create agent files in `src/MCP PLUGINS/servers/your-tool/`
2. Add entry to `servers.json`
3. Restart - everything else is automatic!

## Related Files

- `src/gui/config.py` - Discovery implementation
- `src/ui/session_api.py` - API integration
- `src/ui/mcp_session_manager.py` - Session lifecycle
- `src/MCP PLUGINS/servers/servers.json` - Server definitions
- `CLAUDE.md` - User-facing documentation
- `test_mcp_discovery.py` - Verification script
