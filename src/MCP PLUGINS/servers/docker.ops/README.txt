MCPTools Scaffold: docker.ops

Purpose: Placeholder for Docker operational MCP server/tool (container lifecycle, images, networks, volumes).
Status: scaffold only (no transport/runtime implementation yet)

Notes:
- Intended to expose operational Docker commands via MCP.
- Configure via env/config.yaml. Do not commit secrets.
- Add an inactive servers.json entry when implementing.