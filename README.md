# VibeMind Desktop AI Ecosystem

**Integration repository** for a complete desktop AI system combining self-learning AI, cognitive architecture, desktop automation, and voice interfaces.

## 🌐 Architecture Overview

VibeMind is a **meta-repository** that integrates five specialized submodules:

```
VibeMind/                          # THIS REPO (integration layer)
├── sakana-desktop-assistant/      # Self-learning AI core with MCP agents
├── the_brain/                     # ATM-R cognitive architecture (Tahlamus)
├── MoireTracker/                  # Desktop automation engine (C++, Windows IPC)
├── electron/                      # Voice UI (React 19 + Electron)
└── voice_dialog/                  # Multi-agent orchestration
```

## 🎯 Purpose

VibeMind is an **integration repository** that:
- Combines independent AI components into a unified ecosystem
- Provides cross-submodule integration patterns
- Documents ecosystem-wide architecture
- Manages submodule versioning and dependencies

**This repo contains minimal integration code** - most functionality lives in the submodules.

## 🚀 Quick Start

### Clone with Submodules

```bash
# Clone with all submodules
git clone --recursive https://github.com/Flissel/VibeMind.git
cd VibeMind

# Or if already cloned, initialize submodules
git submodule update --init --recursive
```

### Individual Submodule Setup

Each submodule has its own setup. See their respective READMEs:

**1. Sakana Desktop Assistant** (`sakana-desktop-assistant/`)
```bash
cd sakana-desktop-assistant
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix
pip install -r requirements.txt
python src/main.py
```

**2. The Brain (ATM-R)** (`the_brain/`)
```bash
cd the_brain
uv venv .venv
.venv\Scripts\activate
uv pip install -r requirements.txt
# See the_brain/README.md for usage
```

**3. MoireTracker** (`MoireTracker/`)
```bash
cd MoireTracker
# C++ compilation required - see MoireTracker/README.md
```

**4. Electron Voice UI** (`electron/`)
```bash
cd electron
npm install
npm run dev
```

**5. Voice Dialog** (`voice_dialog/`)
```bash
cd voice_dialog
# See voice_dialog/README.md for setup
```

## 📚 Submodule Descriptions

### Sakana Desktop Assistant
Self-learning AI assistant with:
- 18 MCP (Model Context Protocol) server agents
- Evolutionary learning systems
- Memory and pattern recognition
- React web GUI with session management
- Sandboxed code execution

**Repository**: https://github.com/Flissel/sakana-desktop-assistant-

### The Brain (ATM-R)
Adaptive Thalamic Multimodal Routing - biologically-inspired cognitive architecture:
- 6 modality channels (vision, audio, touch, taste, vestibular, threat)
- Predictive coding and adaptive gating
- CTM (Continuous Thinking Models) integration
- PyTorch, JAX, and C++ acceleration support

**Repository**: https://github.com/Flissel/the_brain

### MoireTracker
Desktop automation engine:
- C++ core for high-performance automation
- Windows shared memory IPC
- Mouse/keyboard tracking and control
- Screen capture and analysis

**Repository**: https://github.com/Flissel/MoireTracker

### Electron Voice UI
Modern voice interface:
- React 19 with Electron
- Real-time voice recognition
- Visual feedback and controls
- Cross-platform desktop app

**Repository**: https://github.com/Flissel/VibeMind-Electron

### Voice Dialog
Multi-agent orchestration:
- Voice-driven agent coordination
- Dialog state management
- Integration layer for voice commands

**Repository**: https://github.com/Flissel/VibeMind-VoiceDialog

## 🔗 Integration Points

VibeMind provides cross-submodule integration through:

### 1. The Brain → Sakana Integration
Sakana can leverage The Brain's ATM-R cognitive architecture:

```python
# From Sakana code:
import sys
from pathlib import Path

# Add the_brain to Python path
VIBEMIND_ROOT = Path(__file__).parent.parent.parent  # Adjust as needed
sys.path.insert(0, str(VIBEMIND_ROOT / "the_brain"))

# Import ATM-R components
from core.thalamo_pc_adaptive import ThalamoPC6Adaptive
from core.predictive_coding import PredictiveCoding
```

### 2. MoireTracker → Sakana Integration
Desktop automation capabilities for Sakana agents (planned):
- Shared memory communication
- Automation task delegation
- Screen analysis for AI decisions

### 3. Voice UI Integration
Electron + Voice Dialog + Sakana pipeline (planned):
- Voice commands → Voice Dialog processing
- Voice Dialog → Sakana task execution
- Sakana → The Brain cognitive routing
- Results → Voice UI feedback

## 📖 Documentation

Ecosystem-wide documentation is in `docs/`:
- [FULL_ECOSYSTEM_ARCHITECTURE.md](docs/FULL_ECOSYSTEM_ARCHITECTURE.md) - Complete system overview
- [TAHLAMUS_INTEGRATION_PLAN.md](docs/TAHLAMUS_INTEGRATION_PLAN.md) - The Brain integration roadmap
- [MOIRE_INTEGRATION_PLAN.md](docs/MOIRE_INTEGRATION_PLAN.md) - Desktop automation integration
- [MOIRE_DEPENDENCY_ANALYSIS.md](docs/MOIRE_DEPENDENCY_ANALYSIS.md) - MoireTracker technical analysis
- [MOIRE_IMPLEMENTATION_KICKOFF.md](docs/MOIRE_IMPLEMENTATION_KICKOFF.md) - Implementation details

Submodule-specific docs are in their respective repositories.

## 🔧 Development Workflow

### Update All Submodules
```bash
git submodule update --remote --merge
```

### Update Specific Submodule
```bash
cd sakana-desktop-assistant
git pull origin main
cd ..
git add sakana-desktop-assistant
git commit -m "Update Sakana submodule"
```

### Add New Submodule
```bash
git submodule add <repository-url> <path>
git submodule update --init --recursive
```

## 🎯 Roadmap

### Phase 1: Submodule Integration ✅
- [x] Initialize all submodules
- [x] Document integration architecture
- [x] Add The Brain (ATM-R) submodule

### Phase 2: The Brain Integration (In Progress)
- [ ] Implement cognitive routing in Sakana
- [ ] Add multimodal sensory processing
- [ ] Integrate predictive coding

### Phase 3: Desktop Automation
- [ ] MoireTracker shared memory integration
- [ ] Automation task API
- [ ] Screen analysis for AI

### Phase 4: Voice Pipeline
- [ ] Voice command routing
- [ ] Multi-agent orchestration
- [ ] End-to-end voice workflow

## 📝 Contributing

When contributing to VibeMind:
1. Identify which submodule needs changes
2. Make changes in the submodule repository
3. Update VibeMind submodule reference
4. Update integration documentation if needed

For submodule-specific contributions, see their respective CONTRIBUTING.md files.

## 📄 License

Each submodule has its own license. See individual repositories for details.

## 🔗 Links

- **VibeMind**: https://github.com/Flissel/VibeMind
- **Sakana**: https://github.com/Flissel/sakana-desktop-assistant-
- **The Brain**: https://github.com/Flissel/the_brain
- **MoireTracker**: https://github.com/Flissel/MoireTracker
- **Electron**: https://github.com/Flissel/VibeMind-Electron
- **Voice Dialog**: https://github.com/Flissel/VibeMind-VoiceDialog
