# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**VibeMind** is an **integration repository** that combines five specialized submodules into a unified desktop AI ecosystem:

1. **sakana-desktop-assistant/** - Self-learning AI core with 18 MCP agents
2. **the_brain/** - ATM-R cognitive architecture (Tahlamus)
3. **MoireTracker/** - Desktop automation engine (C++, Windows IPC)
4. **electron/** - Voice UI (React 19 + Electron)
5. **voice_dialog/** - Multi-agent orchestration

**Important**: VibeMind itself contains **minimal code** - it's a meta-repository for managing submodule integration. Most development happens within the individual submodules.

## Repository Structure

```
VibeMind/                    # Integration repository (THIS REPO)
├── .gitmodules             # Submodule configuration
├── docs/                   # Ecosystem-wide documentation (5 files)
│   ├── FULL_ECOSYSTEM_ARCHITECTURE.md
│   ├── TAHLAMUS_INTEGRATION_PLAN.md
│   ├── MOIRE_INTEGRATION_PLAN.md
│   ├── MOIRE_DEPENDENCY_ANALYSIS.md
│   └── MOIRE_IMPLEMENTATION_KICKOFF.md
│
├── sakana-desktop-assistant/  # Submodule: AI assistant core
│   ├── src/                   # Python source code
│   ├── tests/                 # Test suite
│   ├── data/                  # Runtime data
│   ├── config.yaml           # Configuration
│   └── requirements.txt      # Dependencies
│
├── the_brain/                # Submodule: ATM-R cognitive architecture
│   ├── core/                 # Cognitive systems
│   ├── demos/                # Demo scripts
│   ├── configs/              # YAML configs
│   └── requirements.txt      # Dependencies
│
├── MoireTracker/             # Submodule: Desktop automation (C++)
│   ├── src/                  # C++ source
│   └── build/                # Compiled binaries
│
├── electron/                 # Submodule: Voice UI
│   ├── src/                  # React 19 source
│   └── package.json          # NPM dependencies
│
└── voice_dialog/             # Submodule: Multi-agent orchestration
    └── src/                  # Dialog management
```

## Submodule Management

### Initial Setup

```bash
# Clone with all submodules
git clone --recursive https://github.com/Flissel/VibeMind.git

# Or initialize submodules after cloning
git submodule update --init --recursive
```

### Updating Submodules

```bash
# Update all submodules to latest
git submodule update --remote --merge

# Update specific submodule
cd sakana-desktop-assistant
git pull origin main
cd ..
git add sakana-desktop-assistant
git commit -m "Update Sakana to latest"
```

### Adding New Submodule

```bash
git submodule add <repository-url> <directory-name>
git submodule update --init --recursive
```

## Development Commands

### Sakana Desktop Assistant

```bash
cd sakana-desktop-assistant

# Setup
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix
pip install -r requirements.txt

# Run
python src/main.py

# With options
python src/main.py --no-gui          # CLI only
python src/main.py --learning off    # Disable learning
python src/main.py --config custom.yaml

# Test
pytest
pytest --cov=src tests/

# Web UI development
cd src/ui/webapp
npm run dev      # Dev server with hot reload
npm run build    # Production build
```

### The Brain (ATM-R)

```bash
cd the_brain

# Setup (using uv - faster than pip)
uv venv .venv
.venv\Scripts\activate
uv pip install -r requirements.txt

# Or with pip
pip install -r requirements.txt

# Run demos
python scripts/run_demo.py --steps 200 --plot
python scripts/run_demo.py --adaptive --scenario threat

# Notebooks
jupyter notebook notebooks/02_multimodal_demo.ipynb

# CTM reasoning
python examples/ctm_reasoning_demo.py --task spatial
```

### MoireTracker

```bash
cd MoireTracker
# C++ compilation - see MoireTracker/README.md for build instructions
# Requires Visual Studio Build Tools on Windows
```

### Electron Voice UI

```bash
cd electron
npm install
npm run dev      # Development mode
npm run build    # Production build
```

### Voice Dialog

```bash
cd voice_dialog
# See voice_dialog/README.md for setup
```

## Integration Patterns

### Pattern 1: The Brain → Sakana Integration

Sakana can import and use The Brain's ATM-R cognitive architecture:

```python
# From Sakana code (e.g., sakana-desktop-assistant/src/core/cognitive_routing.py)
import sys
from pathlib import Path

# Add the_brain to Python path
VIBEMIND_ROOT = Path(__file__).parent.parent.parent  # Navigate to VibeMind root
sys.path.insert(0, str(VIBEMIND_ROOT / "the_brain"))

# Import ATM-R components
from core.thalamo_pc_adaptive import ThalamoPC6Adaptive
from core.predictive_coding import PredictiveCoding
from core.attention_mechanisms import AttentionMechanism

# Use in Sakana
atmr = ThalamoPC6Adaptive(
    lr_input=0.001,
    lr_generative=0.01,
    target_entropy=1.5
)

# Route multimodal input
x_multimodal = {
    'vision': vision_features,
    'audio': audio_features,
    'threat': threat_signal
}
out = atmr.step(x_multimodal, adapt=True)
routed_output = out['y']
```

### Pattern 2: MoireTracker → Sakana Integration (Planned)

Desktop automation capabilities for Sakana agents:

```python
# Shared memory IPC pattern (planned)
from moire_ipc import MoireClient

client = MoireClient()
client.connect()

# Delegate automation task
task = client.create_task("click", x=100, y=200)
result = client.execute(task)
```

### Pattern 3: Voice Pipeline (Planned)

Full voice-to-action pipeline:

```
Voice Input → Electron UI
    ↓
Voice Dialog (processing)
    ↓
Sakana Desktop Assistant (task execution)
    ↓
The Brain (cognitive routing)
    ↓
MoireTracker (automation if needed)
    ↓
Voice UI Feedback
```

## Key Files in VibeMind Root

- **README.md** - Ecosystem overview and quick start
- **CLAUDE.md** - This file (development guide)
- **CONTRIBUTING.md** - Contribution guidelines
- **.gitmodules** - Submodule configuration
- **docs/** - Ecosystem-wide architecture documentation

## Submodule-Specific Documentation

Each submodule has its own comprehensive documentation:

- **sakana-desktop-assistant/CLAUDE.md** - Sakana development guide (MCP agents, learning systems, GUI)
- **the_brain/README.md** - ATM-R architecture, usage, and API reference
- **MoireTracker/README.md** - C++ build instructions and automation API
- **electron/README.md** - Voice UI development and React components
- **voice_dialog/README.md** - Dialog orchestration patterns

## When Working on Specific Components

### For Sakana Development
→ Read [sakana-desktop-assistant/CLAUDE.md](sakana-desktop-assistant/CLAUDE.md)
- 18 MCP server agents (GitHub, Docker, Playwright, Desktop, Memory, etc.)
- Evolutionary learning systems
- React web GUI with session management
- Memory and pattern recognition

### For Cognitive Architecture
→ Read [the_brain/README.md](the_brain/README.md)
- ATM-R (Adaptive Thalamic Multimodal Routing)
- 6 modality channels: vision, audio, touch, taste, vestibular, threat
- Predictive coding and adaptive gating
- CTM (Continuous Thinking Models) integration
- PyTorch, JAX, C++ wrappers

### For Desktop Automation
→ Read [MoireTracker/README.md](MoireTracker/README.md)
- C++ high-performance automation
- Windows shared memory IPC
- Mouse/keyboard control
- Screen capture

### For Voice Interface
→ Read [electron/README.md](electron/README.md)
- React 19 + Electron architecture
- Voice recognition integration
- UI components and styling

### For Dialog Orchestration
→ Read [voice_dialog/README.md](voice_dialog/README.md)
- Multi-agent coordination
- Dialog state management
- Voice command routing

## Integration Roadmap

### Phase 1: Submodule Setup ✅
- [x] Initialize all five submodules
- [x] Document ecosystem architecture
- [x] Add The Brain (ATM-R) submodule

### Phase 2: The Brain Integration (Current)
- [ ] Implement cognitive routing in Sakana
- [ ] Add multimodal sensory processing to Sakana agents
- [ ] Integrate predictive coding for learning systems
- [ ] Create bridge module in Sakana for ATM-R

### Phase 3: Desktop Automation
- [ ] Implement MoireTracker shared memory IPC
- [ ] Create automation task API in Sakana
- [ ] Add screen analysis capabilities
- [ ] Integrate desktop control with MCP agents

### Phase 4: Voice Pipeline
- [ ] Connect Electron UI to Voice Dialog
- [ ] Route voice commands to Sakana
- [ ] Implement cognitive routing via The Brain
- [ ] Add voice feedback loop

## Important Notes

1. **VibeMind root has minimal code** - it's primarily for managing submodule integration and ecosystem documentation

2. **Always work in submodules** - when asked to modify code, navigate to the appropriate submodule first

3. **Submodule commits are independent** - changes in submodules need to be committed both in the submodule AND in VibeMind root (to update the submodule reference)

4. **Documentation split**:
   - **Ecosystem-wide docs**: VibeMind/docs/
   - **Component-specific docs**: Inside each submodule

5. **Dependencies are per-submodule** - each submodule has its own requirements.txt / package.json

6. **Integration code goes in submodules** - for example, The Brain integration code should be added to sakana-desktop-assistant/src/, not in VibeMind root

## Common Tasks

### Task: Update Sakana to use The Brain
1. Navigate to `sakana-desktop-assistant/`
2. Create integration module (e.g., `src/core/cognitive_routing.py`)
3. Add Python path manipulation to import from `the_brain/`
4. Implement ATM-R usage
5. Commit in Sakana submodule
6. Update VibeMind submodule reference

### Task: Add Ecosystem Documentation
1. Create markdown file in VibeMind `docs/`
2. Document cross-submodule architecture
3. Link to submodule-specific docs
4. Commit in VibeMind root

### Task: Update Submodule to Latest
```bash
cd <submodule-name>
git pull origin main
cd ..
git add <submodule-name>
git commit -m "Update <submodule> to latest"
```

## Architecture Principles

1. **Separation of Concerns** - Each submodule is independently developable
2. **Minimal Coupling** - Integration happens through well-defined interfaces
3. **Documentation Hierarchy** - Ecosystem docs in VibeMind, component docs in submodules
4. **Independent Versioning** - Submodules can evolve at different paces
5. **Clear Integration Points** - Document cross-submodule dependencies explicitly

## Getting Help

- **VibeMind ecosystem**: See [docs/FULL_ECOSYSTEM_ARCHITECTURE.md](docs/FULL_ECOSYSTEM_ARCHITECTURE.md)
- **Sakana development**: See [sakana-desktop-assistant/CLAUDE.md](sakana-desktop-assistant/CLAUDE.md)
- **The Brain API**: See [the_brain/README.md](the_brain/README.md)
- **Integration plans**: See [docs/TAHLAMUS_INTEGRATION_PLAN.md](docs/TAHLAMUS_INTEGRATION_PLAN.md)
