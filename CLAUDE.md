# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sakana Desktop Assistant is a self-learning AI assistant inspired by Sakana AI's evolutionary algorithms. It combines LLM integration, memory systems, pattern recognition, and sandboxed code execution with a web-based GUI built on React.

## Development Commands

### Python Backend

**Run the assistant:**
```bash
python src/main.py
```

**Run with specific options:**
```bash
# Disable GUI (CLI only)
python src/main.py --no-gui

# Disable learning
python src/main.py --learning off

# Custom config
python src/main.py --config path/to/config.yaml
```

**Quick start script (Unix):**
```bash
./run.sh
```

**Run tests:**
```bash
pytest

# Run specific test file
pytest tests/test_filename.py

# Run with coverage
pytest --cov=src tests/

# Run E2E tests (requires frontend build and backend running)
npx playwright test tests/e2e/
```

### React Web UI

The React web UI is located in `src/ui/webapp/`.

**Development server (with API proxy):**
```bash
cd src/ui/webapp
npm run dev
```

**Build for production:**
```bash
cd src/ui/webapp
npm run build
```

The built assets go to `src/ui/webapp/dist/` and are served by the Python backend when `react_ui_enabled: true` in config.yaml.

**Restart workflow after frontend changes:**
If you change the frontend, rebuild it and restart the backend by killing the Python process and starting it again.

### MCP Tools (Windows)

**Install Playwright MCP dependencies:**
```bash
cd "src/MCP PLUGINS/servers/playwright"
npm install
npx playwright install
```

**Test MCP agents:**
```bash
# Test all agents
python "src/MCP PLUGINS/servers/test_all_agents.py"

# Test specific agent
python "src/MCP PLUGINS/servers/test_agents_execution.py"

# PowerShell quick test
.\src\MCP PLUGINS\servers\test_agents_api.ps1
```

## Architecture

### Backend Structure

- **`src/core/`** - Core assistant logic
  - `assistant.py`: Main `SakanaAssistant` class orchestrating all subsystems
  - `config.py`: Configuration management (loads from `config.yaml`)
  - `llm_interface.py`: LLM provider abstraction (local, OpenAI, Anthropic)
  - `orchestrator.py`: Task orchestration
  - `task_queue.py`: Async task queue
  - `mcp_contracts.py`: MCP (Model Context Protocol) contracts

- **`src/memory/`** - Memory and pattern recognition
  - SQLite-based short-term and long-term memory
  - Pattern detection from user behavior

- **`src/learning/`** - Self-learning systems
  - `EvolutionaryLearner`: Darwin-Gödel Machine inspired evolution
  - `ReinforcementLearner`: Learning from user feedback
  - `SelfModifier`: Code self-modification capabilities
  - `FileDiscoveryLearner`: Environment discovery
  - `project_discovery.py`: Project structure discovery

- **`src/execution/`** - Sandboxed code execution
  - Secure environment for running generated code

- **`src/plugins/`** - Plugin system
  - `plugin_manager.py`: Plugin lifecycle management
  - `builtin_plugins.py`: Built-in plugins (file ops, web search, tasks, etc.)

- **`src/delegation/`** - Task delegation system
  - `delegation_entry.py`: Entry point for delegated tasks

- **`src/gui/`** - Modular GUI server (refactored from monolithic 2824-line file)
  - `interface.py`: `GUIInterface` main class
  - `server.py`: `AssistantHTTPServer` with multi-tool session management
  - `config.py`: Global configuration, session logging, MCP tool paths
  - `watcher.py`: File system watcher for auto-reload
  - `handlers/`: HTTP request handlers (base, GET routes, POST routes, MCP proxy)

- **`src/ui/`** - UI support modules
  - `mcp_session_manager.py`: Centralized MCP session lifecycle management
  - `session_api.py`: Session management API handlers
  - `spa_serving.py`: SPA static file serving
  - `sse_broker.py`: Server-Sent Events for live updates
  - `playwright_proxy.py`: Playwright agent viewer proxy

### Frontend Structure

- **`src/ui/webapp/src/`** - React SPA
  - `routes.tsx`: Main routing and page components (TanStack Router)
  - `main.tsx`: App entry point
  - `components/`: Reusable React components
  - `hooks/`: Custom React hooks

### Data Directory (`data/`)

All runtime data goes under `data/` (configurable via `DATA_DIR` env var):
- `data/logs/`: Application logs (rotating file handler)
- `data/logs/sessions/`: Per-session logs
- `data/sessions/`: Session state
- `data/tmp/`: Temporary files (includes session PID files)
- `data/cache/`: File and project discovery cache
- `data/evolution_archive.json`: Evolutionary learning archive
- `data/modifications/`: Self-modification history
- `data/metrics.json`: Tool usage telemetry and learning data

### Configuration

Main config is `config.yaml` in the project root. Key settings:
- `enable_gui`: Enable web GUI (default: true)
- `react_ui_enabled`: Use React SPA frontend (default: true)
- `react_ui_dist_dir`: Path to built React assets
- `llm_provider`: "local", "openai", "anthropic", or "openrouter"
- `model_name`: Model to use (e.g., "gpt-4o-mini")
- `sandbox_enabled`: Enable sandboxed execution (default: true)
- `learning_rate`, `evolution_generations`, `population_size`, `mutation_rate`: Learning parameters

**OpenRouter Integration:**
The system supports OpenRouter for intelligent model routing with two modes:
- **Dev mode** (`openrouter.mode: "dev"`): Fixed models for fast development (gpt-4o, claude-sonnet-4.0)
- **Prod mode** (`openrouter.mode: "prod"`): Adaptive model selection based on task complexity
  - Primary model for most tasks (claude-3.5-haiku)
  - Complex tasks use claude-3.5-sonnet
  - Reasoning tasks use o1-mini
  - Per-MCP-tool model overrides (e.g., GitHub → claude-3.5-sonnet)

**Environment Variables:**
Create a `.env` file from `.env.example` with:
- `OPENROUTER_API_KEY`: OpenRouter API key
- `GITHUB_PERSONAL_ACCESS_TOKEN`: GitHub MCP server
- `BRAVE_API_KEY`: Brave Search MCP server
- `TAVILY_API_KEY`: Tavily Search MCP server
- `REDIS_URL`: Redis MCP server connection
- `N8N_API_URL`, `N8N_API_KEY`: n8n workflow automation
- `SAKANA_VENV_PYTHON`: Path to venv Python (auto-set by main.py)

### Web GUI Architecture

The web GUI is a hybrid system:
1. **Python HTTP Server** (`src/gui/`): Modular server with session management
2. **React Frontend** (`src/ui/webapp/`): Built with Vite, uses TanStack Router
3. **API Endpoints** (under `/api/`):
   - `GET /api/plugins`: List available plugins
   - `POST /api/message`: Send message to assistant
   - `POST /api/delegate`: Run delegation task
   - `GET /api/session`: Session metadata
   - `GET /api/sessions`: Get all MCP sessions
   - `POST /api/sessions`: Create new MCP session
   - `GET /api/sessions/{id}`: Get session status
   - `POST /api/sessions/{id}/start`: Start session agent
   - `POST /api/sessions/{id}/stop`: Stop session agent
   - `DELETE /api/sessions/{id}`: Delete session
   - `GET /api/mcp/{tool}/sessions/{id}/events`: Proxy to agent event stream
4. **SSE** (`/api/events`): Server-Sent Events for live updates

During development, run `npm run dev` in `src/ui/webapp/` to use Vite's dev server with hot reload. Vite proxies `/api` and `/mcp` requests to the Python backend on port 8765.

For production, build with `npm run build` and the Python server serves the static files from `dist/`.

## Key Concepts

### Self-Learning Loop

The assistant uses multiple learning mechanisms:
1. **Memory System**: Stores interactions, learns patterns
2. **Evolutionary Learning**: Evolves behavior through genetic algorithms
3. **Reinforcement Learning**: Adapts based on user feedback
4. **File/Project Discovery**: Learns about the environment and available projects
5. **Self-Modification**: Can generate and apply code changes to itself (when enabled)
6. **Tool Telemetry**: Records tool usage, success rates, and latency to bias toward effective tools

### Plugin System

Plugins extend the assistant's capabilities. Built-in plugins include:
- File operations (read, write, search)
- Web search
- Task management
- Code generation and execution

Custom plugins can be added to `plugins/` directory or configured via MCP servers in `src/MCP PLUGINS/servers/`.

### MCP Server Integration

MCP (Model Context Protocol) servers provide external capabilities. Active servers include:
- **Playwright** - Browser automation with Edge/Chrome
- **GitHub** - Repository management, issues, PRs (requires GITHUB_PERSONAL_ACCESS_TOKEN)
- **Docker** - Container operations, compose, logs
- **Desktop** - Terminal control, file ops, process management (@wonderwhy-er/desktop-commander)
- **Context7** - Up-to-date code docs and examples
- **Redis** - Key-value store, caching, vector search (requires REDIS_URL)
- **Windows Core** - 25 essential tools for file operations, process management, and system information
- **Supabase** - PostgreSQL, auth, storage, real-time
- **Time** - Time operations, timezone conversions
- **TaskManager** - Task tracking with JSON storage
- **Memory** - Knowledge graph management with entities and relations
- **Filesystem** - File and directory operations with configurable allowed directories
- **Brave Search** - Web search with privacy-focused Brave API (requires BRAVE_API_KEY)
- **Fetch** - HTTP requests and web content retrieval
- **YouTube** - Video transcript and caption fetching
- **n8n** - Workflow automation, node documentation, and n8n API integration (optional N8N_API_URL, N8N_API_KEY)
- **Sequential Thinking** - Dynamic problem-solving through structured thought sequences with step-by-step reasoning
- **Tavily** - Real-time web search, data extraction, website mapping, and web crawling (requires TAVILY_API_KEY)

**MCP Session Architecture:**
- Each MCP tool runs as an agent process spawned via `MCPSessionManager` (`src/ui/mcp_session_manager.py`)
- Agent scripts are in `src/MCP PLUGINS/servers/{tool}/agent.py`
- Sessions are tracked with unique IDs, status, event ports, and PIDs
- Generic session management pattern: `spawn_agent(tool, ...)` supports all tools via `MCP_TOOL_AGENT_PATHS` constant
- Event streaming: Agents communicate via Server-Sent Events (SSE) on dynamic ports
- Tool-agnostic methods: `create_session()`, `get_all_sessions()`, `stop_agent()`, etc.

**Session Lifecycle:**
1. **Create**: `create_session(tool, name, model)` → generates session_id, stores in `_sessions` dict
2. **Spawn**: `spawn_agent(tool, session_id)` → starts Python subprocess, tracks PID
3. **Connect**: Agent announces via `SESSION_ANNOUNCE` → updates host/port in session
4. **Terminate**: `stop_agent(session_id)` → calls `proc.terminate()`, fallback to `proc.kill()`
5. **Delete**: `delete_session(session_id)` → stops agent, removes from dict

**Termination Process** (Platform-specific planned enhancements in `docs/TASKKILL_TERMINATION_IMPLEMENTATION.md`):
- Windows: `taskkill /PID {pid} /T /F` (kills process tree)
- Unix: `kill -TERM {pid}` → `kill -KILL {pid}` fallback
- PID persistence to file for recovery after crashes
- Force-kill fallback if graceful termination fails

**Configuration:**
- Server definitions: `src/MCP PLUGINS/servers/servers.json`
- Credentials: `src/MCP PLUGINS/servers/secrets.json` (gitignored)
- Environment variables in servers.json use `"env:VAR_NAME"` notation

**Naming Convention:**
Session management functions use `mcp_*` naming (e.g., `create_mcp_session()`, `get_all_mcp_sessions()`, `stop_mcp_session_by_id()`) to accurately reflect that they handle **all MCP tools** (GitHub, Docker, Playwright, Desktop, etc.). Deprecated `playwright_*` wrapper methods exist for backward compatibility but emit deprecation warnings.

### Sandboxed Execution

When `sandbox_enabled: true`, all code execution happens in isolated environments using Docker and microsandbox. This ensures safety when the assistant generates and runs code.

## Important Files

- `src/main.py`: Application entry point, sets up logging and data directories
- `src/core/assistant.py`: Main assistant orchestrator
- `src/gui/interface.py`: Web GUI server implementation
- `src/ui/mcp_session_manager.py`: Centralized MCP session management
- `config.yaml`: Primary configuration file
- `requirements.txt`: Python dependencies
- `src/ui/webapp/package.json`: Frontend dependencies

## Testing

Tests are in `tests/` directory. The project uses pytest with async support:
- `pytest.ini` configures `asyncio_mode = auto`
- Use `pytest-asyncio` for async test functions
- Use `pytest-cov` for coverage reports

## Dependencies

### Python (requirements.txt)
- Core: aiofiles, asyncio, python-dotenv
- LLM: openai, llama-cpp-python, transformers, torch
- Memory: sqlalchemy, aiosqlite
- NLP: spacy, scikit-learn, numpy, pandas
- Sandbox: docker, microsandbox
- Utils: requests, pyyaml, watchdog, apscheduler
- Testing: pytest, pytest-asyncio, pytest-cov

### Frontend (src/ui/webapp/package.json)
- React 18
- TanStack Router for routing
- Vite for build tooling
- TypeScript

## Development Notes

- The assistant initializes subsystems asynchronously in `SakanaAssistant.initialize()`
- File discovery and project discovery run in background tasks
- The GUI interface uses `ThreadingHTTPServer` to handle concurrent requests
- Session data and logs are stored under `data/` for easy cleanup and backup
- The React UI uses TanStack Router's file-based routing convention
- MCP sessions visible at http://127.0.0.1:8765/sessions (shows all tool sessions: Playwright, GitHub, Docker, etc.)
- Each session gets its own logger in `data/logs/sessions/{session_id}.log`
- When you change the frontend, rebuild it (`npm run build`) and restart the backend by killing the Python process and starting it again
- The project is Windows-first with PowerShell scripts in `src/MCP PLUGINS/servers/`

## Platform-Specific Commands

### Windows
```powershell
# Activate venv
.venv\Scripts\Activate.ps1

# Test MCP agents
.\src\MCP` PLUGINS\servers\test_agents_api.ps1

# Kill backend process
taskkill /F /IM python.exe
```

### Unix/macOS
```bash
# Activate venv
source venv/bin/activate

# Quick start
./run.sh
```