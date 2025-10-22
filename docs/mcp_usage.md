# MCP Tools Usage Guide (Windows-friendly)

This guide shows how to use the MCP tools in this project, with a focus on the Playwright server, telemetry, and how the assistant learns when to use tools.

## Prerequisites

- Windows 10/11 with PowerShell
- Python 3.10+
- Node.js 18+ (for Playwright MCP server)
- Recommended: Git installed

## Install dependencies

1) Python deps:

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Playwright MCP server deps:

```
cd "src/MCP PLUGINS/servers/playwright"
npm install
npx playwright install
```

## Configure MCP servers

- Edit `src/MCP PLUGINS/servers/playwright/config.json` (if present) to set browser type, headless mode, and any timeouts.
- Ensure any custom prompts/config live under `src/MCP PLUGINS/servers/playwright/prompts/`.

## Start the assistant and UI

From repo root:

```
.venv\Scripts\Activate.ps1
python -m src.app
```

Open the UI (if served) at the URL printed in console. The Learning section will show `Top Tools` metrics and recent `Conversation Preview`.

## Using MCP tools via commands

- `travliy.search <query>`: scaffolds a search tool call.
- `desktop.cmd <action...>`: scaffolds a desktop command action.
- `ctx7.search <query>`: scaffolds a Context7 search.
- Dynamically discovered MCP tools are registered automatically; use `/help` or the Commands panel to find them.

Example:

```
travliy.search flights from NYC to SFO next week
```

## Telemetry and Learning

- Every tool call records outcome and latency to `assistant.metrics.tool_metrics` and `data/metrics.json`.
- The `MCPToolLearner` persists tool usage events to memory and maintains per-tool success, latency, and recentness.
- During planning, the assistant biases toward tools that match the goal text and have high success rate and low latency.
- You can see the impact in the UI’s Learning view under `Top Tools`.

## Playwright workflows

- Tools can start browser sessions, capture screenshots, and provide preview URLs.
- When the UI detects a preview URL, it shows it; you can click to open.
- For long-running sessions, use headless mode for stability; adjust timeouts in the server config.

## Troubleshooting

- If tools don’t appear: check `src/plugins/builtin_plugins.py` dynamic registration and ensure server directories exist.
- If telemetry doesn’t update: verify `data/metrics.json` is writable and look at logs for exceptions in plugin handlers.
- If Playwright fails: run `npx playwright doctor` in the server directory.

## Best practices

- Keep tool args minimal and explicit; avoid overly long commands.
- Prefer tools with proven success/latency in `Top Tools` when possible.
- Periodically clear or archive metrics if `data/metrics.json` grows large.