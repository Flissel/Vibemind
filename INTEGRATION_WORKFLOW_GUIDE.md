# VibeMind Integration Workflow Guide

**How to systematically approach cross-submodule integration tasks**

---

## Table of Contents

1. [Understanding Integration Complexity](#1-understanding-integration-complexity)
2. [The Integration Decision Tree](#2-the-integration-decision-tree)
3. [Five-Phase Integration Methodology](#3-five-phase-integration-methodology)
4. [Instance Orchestration Patterns](#4-instance-orchestration-patterns)
5. [Concrete Examples](#5-concrete-examples)
6. [Common Pitfalls & Solutions](#6-common-pitfalls--solutions)
7. [Integration Checklist](#7-integration-checklist)

---

## 1. Understanding Integration Complexity

### Integration Types

VibeMind has **5 submodules** that can be connected in various ways:

```
        ┌─────────────────┐
        │  VibeMind Root  │  ← Integration coordination
        │   (Instance 1)  │
        └────────┬────────┘
                 │
    ┌────────────┼────────────┬──────────┬──────────┐
    │            │            │          │          │
┌───▼───┐    ┌──▼───┐    ┌───▼───┐  ┌──▼───┐  ┌───▼────┐
│Sakana │    │Brain │    │ Moire │  │Electron│ │Voice   │
│  (2)  │    │ (3)  │    │  (4)  │  │  (5)  │  │Dialog  │
└───────┘    └──────┘    └───────┘  └────────┘  └────────┘
```

**Integration Complexity Levels:**

| Level | Description | Example | Time Estimate |
|-------|-------------|---------|---------------|
| **Simple** | Single direction, clear API | voice_dialog → electron (use C++ library) | 2-4 hours |
| **Medium** | Bidirectional, some shared state | sakana ↔ the_brain (cognitive routing) | 1-2 days |
| **Complex** | Multi-component, pipeline | voice → electron → sakana → brain → moire | 1-2 weeks |

### Questions to Ask First

Before starting ANY integration, answer these:

1. **What is the data flow?**
   - Which component initiates?
   - What data moves between them?
   - Is it one-way or bidirectional?

2. **What technology barriers exist?**
   - Different languages? (Python ↔ C++ ↔ TypeScript)
   - Different processes? (IPC needed?)
   - Different machines? (Network communication?)

3. **What's the interface?**
   - Function calls? (Python imports)
   - IPC? (Shared memory, sockets)
   - REST API? (HTTP endpoints)
   - WebSockets? (Real-time streaming)

4. **What testing is needed?**
   - Unit tests per component
   - Integration tests across boundary
   - End-to-end tests
   - Performance tests

---

## 2. The Integration Decision Tree

Use this flowchart to decide your approach:

```
START: "I want to connect X to Y"
│
├─ Q1: Are both components in same language?
│  ├─ YES → ✅ Direct imports/function calls
│  │         Go to: Pattern A (Sequential Implementation)
│  │
│  └─ NO → Continue to Q2
│
├─ Q2: Are both in same process?
│  ├─ YES → Use language bindings (pybind11, N-API)
│  │         Go to: Pattern B (Parallel Development)
│  │
│  └─ NO → Continue to Q3
│
├─ Q3: Need real-time communication?
│  ├─ YES → Use WebSockets or shared memory
│  │         Go to: Pattern C (Test-Driven Integration)
│  │
│  └─ NO → Use REST API or message queue
│            Go to: Pattern D (Spike & Stabilize)
```

### Which Pattern to Use?

| Pattern | Best For | Time Cost | Risk |
|---------|----------|-----------|------|
| **A: Sequential** | Simple, clear dependencies | Low | Low |
| **B: Parallel** | Independent components, clear interface | Medium | Medium |
| **C: Test-Driven** | Critical integrations, unclear requirements | High | Low |
| **D: Spike & Stabilize** | Experimental, learning phase | Low→High | High→Low |

---

## 3. Five-Phase Integration Methodology

### Phase 1: RESEARCH (Instance 1 leads)

**Goal**: Understand both components and plan the integration

**Steps:**

1. **Read Documentation**
   ```
   Instance 1: "Read all relevant docs and create integration overview"

   For sakana→the_brain integration:
   - Read: sakana-desktop-assistant/CLAUDE.md
   - Read: the_brain/README.md
   - Read: the_brain/demos/*.py (usage examples)
   - Read: VibeMind/docs/TAHLAMUS_INTEGRATION_PLAN.md
   ```

2. **Identify Touch Points**
   ```
   Instance 1: "Find all files that will need changes"

   Use: Glob, Grep, and exploration
   Create: VibeMind/docs/INTEGRATION_TOUCH_POINTS.md
   ```

3. **Create Integration Plan**
   ```markdown
   ## Integration Plan: Sakana → The Brain

   ### Components Involved
   - **Source**: sakana-desktop-assistant/src/core/orchestrator.py
   - **Target**: the_brain/core/thalamo_pc_adaptive.py
   - **Interface**: Python path imports

   ### Data Flow
   1. Sakana receives user task
   2. Sakana extracts task features (complexity, domain, urgency)
   3. Sakana calls The Brain's ATM-R for routing decision
   4. ATM-R returns optimal agent/modality assignment
   5. Sakana executes using routed agent

   ### Technical Approach
   - Add the_brain to Python path in Sakana
   - Create wrapper: sakana/src/core/cognitive_routing.py
   - Define clean interface (no tight coupling)

   ### Testing Strategy
   - Unit tests: sakana/tests/test_cognitive_routing.py
   - Integration tests: Test actual ATM-R calls
   - Performance tests: Latency under 100ms
   ```

4. **Define Clear Interface**
   ```python
   # Document this in VibeMind/docs/INTEGRATION_INTERFACES.md

   ## Sakana → The Brain Interface

   ### Function Signature
   ```python
   def route_task_decision(
       task_description: str,
       complexity: int,  # 1-10
       domain: str,      # "code", "research", "automation"
       urgency: str      # "low", "medium", "high"
   ) -> dict:
       """
       Returns: {
           "agent": "github" | "playwright" | "docker" | ...,
           "confidence": float,  # 0.0-1.0
           "reasoning": str
       }
       """
   ```
   ```

**Instance 1 Deliverable**: `VibeMind/docs/INTEGRATION_PLAN_[X_TO_Y].md`

### Phase 2: DESIGN (All instances contribute)

**Goal**: Design the interface and implementation approach

**Pattern: Broadcast Discussion**

```
Instance 1: "Everyone read INTEGRATION_PLAN_SAKANA_TO_BRAIN.md
and suggest improvements from your submodule's perspective"

Instance 2 (Sakana):
"The interface looks good. I'd add a `context` field for conversation history.
Also, we should cache ATM-R decisions to avoid repeated calls."

Instance 3 (The Brain):
"ATM-R can handle the input format. Suggest adding `user_preferences`
field so we can personalize routing over time."

Instance 4 (Moire):
"Not affected by this integration, but FYI: if routing includes desktop
automation tasks, I'll need task format documentation."

Instance 5 (Electron):
"Will the UI need to show routing decisions? Should I add a debug panel?"
```

**Instance 1 Action**: Consolidate feedback, update plan

### Phase 3: IMPLEMENT (Parallel or Sequential)

**Choose your pattern** (see Section 4 for details)

**Sequential Example** (sakana→the_brain):

```
Step 1: Instance 3 (The Brain)
→ Create: the_brain/api/sakana_routing.py
→ Expose: Simple function wrapping ATM-R
→ Test: the_brain/tests/test_sakana_routing.py
→ Commit: "feat: Add Sakana routing API"

Step 2: Instance 2 (Sakana)
→ Create: sakana/src/core/cognitive_routing.py
→ Import: from the_brain via Python path
→ Integrate: with existing orchestrator
→ Test: sakana/tests/test_cognitive_routing.py
→ Commit: "feat: Integrate The Brain cognitive routing"

Step 3: Instance 1 (Root)
→ Update: Submodule references
→ Test: Integration tests
→ Document: Update INTEGRATION_PLAN with results
→ Commit: "integrate: Connect Sakana and The Brain"
```

**Parallel Example** (voice_dialog→electron):

```
Time 0:00 - Assign both instances simultaneously

Instance 5 (Electron):
"Create a C++/OpenGL loader that can use voice_dialog's visual_sim_core.
File: electron/src/native/VoiceDialogBridge.cpp
Expose to React via N-API bindings."

Instance 3 (voice_dialog):
"Ensure visual_sim_core.pyd can be imported standalone.
Create example: voice_dialog/examples/electron_integration.py
Document the API in voice_dialog/API.md"

Time 1:00 - Integration Point

Instance 1:
"Both are ready. Instance 5, now link against voice_dialog's built library.
Test end-to-end rendering."
```

### Phase 4: TEST (Critical!)

**Three Testing Levels:**

1. **Unit Tests** (Each instance tests their own code)
   ```
   Instance 2: "Run pytest on cognitive_routing.py"
   Instance 3: "Run pytest on sakana_routing.py"
   ```

2. **Integration Tests** (Cross-boundary tests)
   ```
   Instance 1: "Create integration test that calls Sakana → Brain → verify result"

   Location: VibeMind/tests/integration/test_sakana_brain_integration.py
   ```

3. **End-to-End Tests** (Full pipeline)
   ```
   Instance 1: "User says 'create a GitHub PR' → test full flow → verify PR created"
   ```

**Testing Checklist:**
- [ ] Unit tests pass in both submodules
- [ ] Integration test passes
- [ ] No performance regression (latency, memory)
- [ ] Error handling works (what if Brain is unavailable?)
- [ ] Edge cases covered (empty input, invalid data, etc.)

### Phase 5: DOCUMENT & MAINTAIN

**Documentation Updates:**

```
Instance 1 creates/updates:

1. VibeMind/docs/INTEGRATION_PLAN_[X_TO_Y].md
   → Add "Implementation Results" section

2. VibeMind/README.md
   → Update "Integration Points" section

3. Submodule CLAUDE.md files
   → sakana-desktop-assistant/CLAUDE.md: Add Brain integration notes
   → the_brain/README.md: Add Sakana integration notes

4. API Documentation
   → VibeMind/docs/API_REFERENCE.md
   → Document the new cross-submodule functions
```

**Maintenance Plan:**

```markdown
## Integration Maintenance: Sakana ↔ The Brain

### Versioning
- Sakana depends on The Brain v0.2.0+
- Breaking changes require coordination

### Monitoring
- Log all cognitive routing calls
- Track decision accuracy over time
- Alert if latency exceeds 100ms

### Future Enhancements
- [ ] Add caching layer
- [ ] Support async routing
- [ ] Add routing metrics dashboard
```

---

## 4. Instance Orchestration Patterns

### Pattern A: Sequential Implementation

**When to use:**
- Clear dependency order (X must be done before Y)
- Learning as you go
- Critical path integrations

**Instance Flow:**

```
Time 0:00
└─ Instance 1: Research and planning (30 min)

Time 0:30
└─ Instance 3: Implement provider (Brain API) (1 hour)

Time 1:30
└─ Instance 2: Implement consumer (Sakana integration) (1 hour)

Time 2:30
└─ Instance 1: Integration testing (30 min)

Total: 3 hours
```

**Pros:**
- Low risk (validate each step)
- Easy to debug
- Learn interface as you go

**Cons:**
- Slower (sequential, not parallel)
- Idle instances (waste resources)

### Pattern B: Parallel Development

**When to use:**
- Interface is well-defined
- Both teams can work independently
- Time is critical

**Instance Flow:**

```
Time 0:00 - Both start simultaneously
├─ Instance 3: Implement Brain API (1 hour)
└─ Instance 2: Implement Sakana integration (1 hour)
    (Mocks Brain API initially)

Time 1:00 - Integration
└─ Instance 1: Replace mocks with real Brain API
   Test integration (30 min)

Total: 1.5 hours
```

**Coordination via Instance 1:**

```markdown
## Integration Coordination Notes (Updated every 15 min)

### Time 0:00 - Start
- Instance 3: Building Brain routing API
- Instance 2: Building Sakana wrapper (using mock)
- Mock interface: { agent: str, confidence: float }

### Time 0:30 - Status Check
- Instance 3: API 60% complete, on track
- Instance 2: Wrapper complete, tests passing with mock

### Time 1:00 - Integration
- Instance 3: API complete, published to feature branch
- Instance 2: Switching from mock to real API
- Instance 1: Running integration tests
```

**Pros:**
- Fast (parallel work)
- Efficient (all instances active)

**Cons:**
- Requires clear interface upfront
- Risk of rework if interface changes
- More coordination overhead

### Pattern C: Test-Driven Integration

**When to use:**
- Integration is critical (can't fail)
- Requirements are somewhat unclear
- Want maximum confidence

**Instance Flow:**

```
Time 0:00 - Write Tests First
└─ Instance 1: Define integration contract
   Create: tests/integration/test_sakana_brain.py
   (Tests WILL fail initially - that's expected!)

Time 0:30 - Implement in Parallel
├─ Instance 3: Implement Brain API to pass tests
└─ Instance 2: Implement Sakana wrapper to pass tests

Time 2:00 - Verify
└─ Instance 1: All tests pass? ✅ Integration complete!
```

**Example Integration Test:**

```python
# VibeMind/tests/integration/test_sakana_brain.py

def test_cognitive_routing_for_github_task():
    """Test that Brain routes GitHub tasks to GitHub agent"""
    # Setup
    task = "Create a PR for feature branch"

    # Call integration
    from sakana.core.cognitive_routing import route_task
    result = route_task(
        description=task,
        complexity=5,
        domain="code",
        urgency="medium"
    )

    # Verify
    assert result["agent"] == "github"
    assert result["confidence"] > 0.7
    assert "pull request" in result["reasoning"].lower()


def test_cognitive_routing_fallback_on_failure():
    """Test graceful degradation if Brain is unavailable"""
    # Simulate Brain failure
    with mock_brain_unavailable():
        result = route_task(description="test task")

    # Should fall back to default routing
    assert result["agent"] == "default"
    assert "fallback" in result["reasoning"]
```

**Pros:**
- High confidence (tests define success)
- Clear contract
- Regression prevention

**Cons:**
- Slower startup (write tests first)
- Requires good test design skills

### Pattern D: Spike & Stabilize

**When to use:**
- Exploratory integration
- Unclear if it's even possible
- Learning new technology

**Two Phases:**

**Phase 1: Spike (Quick & Dirty)**

```
Time 0:00
└─ Instance 2: "Create a hacky proof-of-concept that calls Brain from Sakana"
   → Allow: Hardcoded paths, ugly code, no tests
   → Goal: Prove it works
   → Time: 30 minutes MAX
```

**Phase 2: Stabilize (Clean Implementation)**

```
Time 0:30
└─ Instance 1: "Review the spike. What did we learn?"
   → Create proper integration plan
   → Then use Pattern A, B, or C for real implementation
```

**Pros:**
- Fast feedback (is this even possible?)
- Low risk (throw away spike code)
- Learn before committing

**Cons:**
- Temptation to keep spike code
- Extra work (code twice)

---

## 5. Concrete Examples

### Example 1: voice_dialog → electron (Visual Enhancement)

**Goal**: Use voice_dialog's C++/OpenGL particle system in Electron for better performance

**Complexity**: Simple
**Pattern**: Sequential Implementation
**Time**: 2-4 hours

#### Research Phase

**Instance 1: Understand the components**

```
"Read voice_dialog/README.md and electron/ai-desktop-automation/README.md.
Create integration plan."
```

**Key Findings:**
- voice_dialog: C++ with pybind11, builds to `visual_sim_core.pyd` (Windows)
- electron: React + Electron, currently uses Canvas 2D (200 particles)
- Integration: Need N-API bridge from Electron to C++ library

#### Implementation Phase

**Step 1: Instance 3 (voice_dialog) - Prepare Library**

```
Task: "Ensure voice_dialog can be used standalone"

Files to check/create:
- voice_dialog/python/visual_sim_core.pyd (ensure it exists)
- voice_dialog/examples/standalone_demo.py (create example)
- voice_dialog/API.md (document the API)

Python API example:
```python
import visual_sim_core

# Create simulation
sim = visual_sim_core.VoiceSimulation(width=800, height=600)

# Update with audio data
sim.update_audio(
    bass=0.7,      # 0.0-1.0
    mid=0.5,
    treble=0.3,
    beat_detected=True
)

# Render frame (returns image buffer)
frame = sim.render()
```

Commit: "docs: Add standalone API documentation for Electron integration"
```

**Step 2: Instance 5 (Electron) - Create Bridge**

```
Task: "Create N-API bridge to load voice_dialog's C++ library"

New files:
- electron/src/native/VoiceDialogBridge.cpp
- electron/src/native/binding.gyp
- electron/src/components/VoiceDialogVisualizer.tsx

Approach:
1. Use N-API to wrap visual_sim_core C++ library
2. Expose to JavaScript via require('voice-dialog-bridge')
3. Stream audio data from React to native module
4. Render frames to Canvas or Electron BrowserWindow

Implementation:
```cpp
// VoiceDialogBridge.cpp
#include <napi.h>
#include "visual_sim_core.h"  // From voice_dialog

Napi::Value UpdateAudio(const Napi::CallbackInfo& info) {
    Napi::Env env = info.Env();

    // Extract audio data from JavaScript
    double bass = info[0].As<Napi::Number>().DoubleValue();
    double mid = info[1].As<Napi::Number>().DoubleValue();
    double treble = info[2].As<Napi::Number>().DoubleValue();

    // Call voice_dialog C++ library
    VoiceSimulation* sim = GetSimulation();
    sim->update_audio(bass, mid, treble, false);

    return env.Null();
}
```

```typescript
// VoiceDialogVisualizer.tsx
import { useEffect, useRef } from 'react';
const voiceDialog = require('voice-dialog-bridge');

export function VoiceDialogVisualizer() {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        // Get audio data from microphone
        const analyser = setupAudioAnalyser();

        function animate() {
            const audio = analyseAudio(analyser);

            // Send to C++ backend
            voiceDialog.updateAudio(
                audio.bass,
                audio.mid,
                audio.treble
            );

            // Render (C++ library renders to window directly,
            // or we get frame buffer back)
            requestAnimationFrame(animate);
        }

        animate();
    }, []);

    return <canvas ref={canvasRef} />;
}
```

Commit: "feat: Integrate voice_dialog C++ visualization"
```

**Step 3: Instance 1 (Root) - Integration**

```
Task: "Update submodule references and test integration"

1. Update voice_dialog submodule reference
   cd voice_dialog && git pull origin main && cd ..
   git add voice_dialog

2. Update electron submodule reference
   cd electron && git pull origin feature/voice-dialog-integration && cd ..
   git add electron

3. Test end-to-end
   - Launch electron app
   - Enable voice input
   - Verify smooth particle rendering (60 FPS)

4. Document
   Update: VibeMind/README.md
   Add: VibeMind/docs/VOICE_DIALOG_ELECTRON_INTEGRATION.md

Commit: "integrate: Connect voice_dialog visualization to Electron UI"
```

#### Testing

```
Instance 5: "Run Electron app and verify:"
- [ ] Particles render at 60 FPS (check DevTools)
- [ ] Audio reactivity works (bass → blue, treble → red)
- [ ] No memory leaks (monitor over 5 minutes)
- [ ] Beat detection pulses work
```

### Example 2: sakana → the_brain (Cognitive Routing)

**Goal**: Use The Brain's ATM-R to route Sakana's tasks to optimal agents

**Complexity**: Medium
**Pattern**: Test-Driven Integration
**Time**: 1-2 days

#### Research Phase

**Instance 1: Study both systems**

```
"Read sakana-desktop-assistant/src/core/orchestrator.py
and the_brain/core/thalamo_pc_adaptive.py.
Understand current task routing in Sakana and how ATM-R works."
```

**Key Findings:**

```markdown
## Current Sakana Routing
- Simple keyword-based routing: "github" → GitHub agent
- No learning or adaptation
- File: src/core/orchestrator.py:route_to_agent()

## The Brain's ATM-R
- 6 modality channels (vision, audio, touch, taste, vestibular, threat)
- Adaptive gating (learns routing over time)
- Predictive coding for online learning
- File: core/thalamo_pc_adaptive.py:ThalamoPC6Adaptive

## Integration Approach
- Create new "task" modality in ATM-R (or map to existing)
- Sakana provides task embeddings (complexity, domain, urgency)
- ATM-R returns routing decision
- Sakana learns from success/failure feedback
```

#### Design Phase

**Instance 1: Define Interface**

```markdown
## Interface Design: Sakana ↔ The Brain

### Input to ATM-R
```python
task_features = {
    "embedding": np.array([...]),  # 64-dim task embedding
    "complexity": 7,                # 1-10 scale
    "domain": "code",               # "code", "research", "automation", etc.
    "urgency": 0.8,                 # 0.0-1.0 scale
    "context": {                    # Optional context
        "recent_failures": ["github_timeout"],
        "user_preference": "fast"
    }
}
```

### Output from ATM-R
```python
routing_decision = {
    "agent": "playwright",          # Agent to use
    "confidence": 0.85,             # 0.0-1.0
    "modality_scores": {            # Why this agent?
        "vision": 0.3,
        "audio": 0.1,
        "code": 0.9,  # Custom modality
        # ...
    },
    "reasoning": "High code complexity suggests browser automation"
}
```

### Feedback Loop
```python
# After task completion
feedback = {
    "task_id": "abc123",
    "success": True,
    "duration": 45.2,  # seconds
    "quality": 0.9     # 0.0-1.0 (user satisfaction)
}
atmr.update(feedback)  # Reinforcement learning
```
```

#### Test-Driven Implementation

**Step 1: Instance 1 (Root) - Write Integration Tests**

```python
# VibeMind/tests/integration/test_sakana_brain_routing.py

import pytest
import numpy as np


class TestCognitiveRouting:
    """Integration tests for Sakana ↔ The Brain routing"""

    def test_github_task_routing(self):
        """Verify Brain routes GitHub tasks correctly"""
        from sakana.core.cognitive_routing import CognitiveRouter

        router = CognitiveRouter()

        # Simulate GitHub task
        decision = router.route_task(
            description="Create a PR for feature branch",
            complexity=5,
            domain="code",
            urgency=0.6
        )

        assert decision["agent"] == "github"
        assert decision["confidence"] > 0.7

    def test_research_task_routing(self):
        """Verify Brain routes research tasks correctly"""
        router = CognitiveRouter()

        decision = router.route_task(
            description="Find papers on reinforcement learning",
            complexity=3,
            domain="research",
            urgency=0.3
        )

        assert decision["agent"] in ["brave_search", "tavily", "fetch"]

    def test_fallback_on_brain_failure(self):
        """Verify graceful degradation if Brain unavailable"""
        router = CognitiveRouter()

        # Simulate Brain unavailable
        with mock.patch('the_brain.core.thalamo_pc_adaptive.ThalamoPC6Adaptive') as mock_brain:
            mock_brain.side_effect = ConnectionError()

            decision = router.route_task(
                description="test task",
                complexity=5,
                domain="code"
            )

            # Should fall back to keyword routing
            assert decision["agent"] is not None
            assert decision["fallback"] == True
```

**Step 2: Instance 3 (The Brain) - Implement Routing API**

```python
# the_brain/api/sakana_routing.py

"""
Sakana integration API for ATM-R cognitive routing.
"""

import numpy as np
from core.thalamo_pc_adaptive import ThalamoPC6Adaptive
from core.predictive_coding import PredictiveCoding


class SakanaRouter:
    """Routes Sakana tasks using ATM-R cognitive architecture"""

    def __init__(self):
        # Initialize ATM-R with 7 modalities (6 standard + 1 task)
        self.atmr = ThalamoPC6Adaptive(
            n_modalities=7,  # vision, audio, touch, taste, vestibular, threat, TASK
            hidden_dim=128,
            output_dim=32
        )

        # Map task domains to modality indices
        self.domain_to_modality = {
            "code": 6,       # Task modality
            "research": 0,   # Vision (reading)
            "automation": 2, # Touch (interaction)
            "data": 1,       # Audio (patterns)
        }

        # Agent mapping
        self.agents = [
            "github", "docker", "playwright", "desktop",
            "memory", "brave_search", "tavily", "fetch",
            "youtube", "n8n", "filesystem", "sequential_thinking"
        ]

    def route_task(
        self,
        description: str,
        complexity: int,
        domain: str,
        urgency: float,
        context: dict = None
    ) -> dict:
        """
        Route a task to the optimal agent using ATM-R.

        Args:
            description: Task description text
            complexity: Task complexity (1-10)
            domain: Task domain ("code", "research", "automation", "data")
            urgency: Urgency score (0.0-1.0)
            context: Optional context (recent failures, user prefs)

        Returns:
            {
                "agent": str,
                "confidence": float,
                "modality_scores": dict,
                "reasoning": str
            }
        """
        # Create task embedding
        embedding = self._create_embedding(description, complexity, domain, urgency)

        # Run through ATM-R
        modality_idx = self.domain_to_modality.get(domain, 6)
        result = self.atmr.step(
            x=embedding,
            modality_idx=modality_idx,
            threat_present=(urgency > 0.8)  # High urgency = threat
        )

        # Decode routing decision
        agent_idx = np.argmax(result['y'])
        agent = self.agents[agent_idx]
        confidence = float(result['y'][agent_idx])

        # Generate reasoning
        reasoning = self._generate_reasoning(
            agent, modality_idx, result['gate_activations']
        )

        return {
            "agent": agent,
            "confidence": confidence,
            "modality_scores": {
                f"modality_{i}": float(result['gate_activations'][i])
                for i in range(7)
            },
            "reasoning": reasoning
        }

    def update_from_feedback(self, task_id: str, feedback: dict):
        """
        Update ATM-R based on task outcome.

        Args:
            task_id: Task identifier
            feedback: {
                "success": bool,
                "duration": float,
                "quality": float
            }
        """
        # Use predictive coding for online learning
        # This adjusts gating weights based on outcome
        reward = feedback["quality"] if feedback["success"] else -0.5
        self.atmr.update_gates(reward)

    def _create_embedding(self, description, complexity, domain, urgency):
        """Create 64-dim task embedding"""
        # Simplified - real implementation would use BERT or similar
        # For now, create feature vector
        embedding = np.zeros(64)
        embedding[0] = complexity / 10.0
        embedding[1] = urgency
        embedding[2] = len(description) / 100.0
        # ... more features ...
        return embedding

    def _generate_reasoning(self, agent, modality_idx, gate_activations):
        """Generate human-readable reasoning"""
        dominant_modality = np.argmax(gate_activations)
        modality_names = ["vision", "audio", "touch", "taste", "vestibular", "threat", "task"]

        return (
            f"Routing to {agent} agent based on dominant "
            f"{modality_names[dominant_modality]} modality activation "
            f"({gate_activations[dominant_modality]:.2f})"
        )
```

**Test in Brain submodule:**

```python
# the_brain/tests/test_sakana_routing.py

def test_sakana_router_initialization():
    """Test router initializes correctly"""
    from api.sakana_routing import SakanaRouter

    router = SakanaRouter()
    assert router.atmr is not None
    assert len(router.agents) > 0


def test_route_github_task():
    """Test routing of GitHub task"""
    from api.sakana_routing import SakanaRouter

    router = SakanaRouter()
    result = router.route_task(
        description="Create a pull request",
        complexity=5,
        domain="code",
        urgency=0.6
    )

    assert "agent" in result
    assert result["confidence"] > 0.0
```

**Commit:**
```bash
cd the_brain
git add api/sakana_routing.py tests/test_sakana_routing.py
git commit -m "feat: Add Sakana task routing API using ATM-R"
git push origin feature/sakana-routing
```

**Step 3: Instance 2 (Sakana) - Implement Integration**

```python
# sakana-desktop-assistant/src/core/cognitive_routing.py

"""
Cognitive routing using The Brain's ATM-R architecture.
"""

import sys
from pathlib import Path
import logging

# Add the_brain to Python path
VIBEMIND_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(VIBEMIND_ROOT / "the_brain"))

try:
    from api.sakana_routing import SakanaRouter
    BRAIN_AVAILABLE = True
except ImportError:
    BRAIN_AVAILABLE = False
    logging.warning("The Brain not available, falling back to keyword routing")


class CognitiveRouter:
    """Routes tasks using cognitive architecture or fallback to keywords"""

    def __init__(self):
        if BRAIN_AVAILABLE:
            self.router = SakanaRouter()
            self.mode = "cognitive"
        else:
            self.router = None
            self.mode = "keyword"

    def route_task(
        self,
        description: str,
        complexity: int = 5,
        domain: str = "code",
        urgency: float = 0.5
    ) -> dict:
        """
        Route a task to the optimal agent.

        Returns:
            {
                "agent": str,
                "confidence": float,
                "reasoning": str,
                "fallback": bool
            }
        """
        if self.mode == "cognitive" and self.router:
            try:
                result = self.router.route_task(
                    description, complexity, domain, urgency
                )
                result["fallback"] = False
                return result
            except Exception as e:
                logging.error(f"Cognitive routing failed: {e}")
                # Fall through to keyword routing

        # Fallback: Simple keyword routing
        return self._keyword_route(description)

    def _keyword_route(self, description: str) -> dict:
        """Simple keyword-based routing (fallback)"""
        desc_lower = description.lower()

        # Simple rules
        if any(word in desc_lower for word in ["pr", "pull request", "commit", "github"]):
            agent = "github"
        elif any(word in desc_lower for word in ["browser", "web", "click", "navigate"]):
            agent = "playwright"
        elif any(word in desc_lower for word in ["docker", "container", "build"]):
            agent = "docker"
        elif any(word in desc_lower for word in ["search", "find", "look up"]):
            agent = "brave_search"
        else:
            agent = "default"

        return {
            "agent": agent,
            "confidence": 0.5,
            "reasoning": f"Keyword matching (fallback mode)",
            "fallback": True
        }

    def provide_feedback(self, task_id: str, success: bool, quality: float = 0.5):
        """Provide feedback for learning"""
        if self.mode == "cognitive" and self.router:
            self.router.update_from_feedback(
                task_id,
                {
                    "success": success,
                    "quality": quality,
                    "duration": 0.0  # TODO: track duration
                }
            )
```

**Integrate with existing orchestrator:**

```python
# sakana-desktop-assistant/src/core/orchestrator.py

from .cognitive_routing import CognitiveRouter

class TaskOrchestrator:
    def __init__(self):
        self.cognitive_router = CognitiveRouter()
        # ... existing code ...

    async def execute_task(self, task_description: str):
        """Execute a task using cognitive routing"""

        # Get routing decision from The Brain
        routing = self.cognitive_router.route_task(
            description=task_description,
            complexity=self._estimate_complexity(task_description),
            domain=self._classify_domain(task_description)
        )

        logging.info(f"Cognitive routing: {routing['agent']} (confidence: {routing['confidence']:.2f})")
        logging.info(f"Reasoning: {routing['reasoning']}")

        # Execute with selected agent
        agent = self.agents[routing["agent"]]
        result = await agent.execute(task_description)

        # Provide feedback to The Brain
        self.cognitive_router.provide_feedback(
            task_id=result.task_id,
            success=result.success,
            quality=result.quality_score
        )

        return result
```

**Test in Sakana submodule:**

```python
# sakana-desktop-assistant/tests/test_cognitive_routing.py

def test_cognitive_router_import():
    """Test that cognitive router imports correctly"""
    from src.core.cognitive_routing import CognitiveRouter

    router = CognitiveRouter()
    assert router is not None


def test_route_task_with_brain():
    """Test routing with The Brain available"""
    from src.core.cognitive_routing import CognitiveRouter, BRAIN_AVAILABLE

    if not BRAIN_AVAILABLE:
        pytest.skip("The Brain not available")

    router = CognitiveRouter()
    result = router.route_task("Create a GitHub PR", complexity=5, domain="code")

    assert result["agent"] is not None
    assert result["fallback"] == False


def test_route_task_fallback():
    """Test fallback routing when Brain unavailable"""
    from src.core.cognitive_routing import CognitiveRouter

    router = CognitiveRouter()
    router.mode = "keyword"  # Force keyword mode

    result = router.route_task("Create a GitHub PR")

    assert result["agent"] == "github"
    assert result["fallback"] == True
```

**Commit:**
```bash
cd sakana-desktop-assistant
git add src/core/cognitive_routing.py src/core/orchestrator.py tests/test_cognitive_routing.py
git commit -m "feat: Integrate The Brain cognitive routing into task orchestration"
git push origin feature/cognitive-routing
```

**Step 4: Instance 1 (Root) - Integration Testing**

```python
# VibeMind/tests/integration/test_sakana_brain_routing.py
# (Tests we wrote earlier should now pass!)

pytest tests/integration/test_sakana_brain_routing.py -v
```

**Expected output:**
```
test_github_task_routing PASSED
test_research_task_routing PASSED
test_fallback_on_brain_failure PASSED
```

**Update submodule references:**
```bash
cd the_brain
git checkout feature/sakana-routing
cd ..

cd sakana-desktop-assistant
git checkout feature/cognitive-routing
cd ..

git add the_brain sakana-desktop-assistant
git commit -m "integrate: Connect Sakana orchestrator with The Brain cognitive routing"
```

**Document:**
```markdown
# VibeMind/docs/SAKANA_BRAIN_INTEGRATION.md

## Sakana ↔ The Brain Integration

### Overview
Sakana now uses The Brain's ATM-R cognitive architecture for intelligent task routing.

### How It Works
1. User requests a task in Sakana
2. Sakana extracts task features (complexity, domain, urgency)
3. Sakana calls The Brain's SakanaRouter API
4. ATM-R processes features through 7 modality channels
5. ATM-R returns routing decision with confidence score
6. Sakana executes task with selected agent
7. Sakana provides feedback to The Brain for online learning

### Benefits
- Adaptive routing (learns from successes/failures)
- Context-aware decisions (urgency, user preferences)
- Graceful fallback (keyword routing if Brain unavailable)

### Performance
- Routing latency: ~50ms (acceptable for interactive use)
- Accuracy: Improves over time with feedback loop
- Memory: +100MB for ATM-R model (acceptable)

### Monitoring
Check routing decisions in logs:
```
tail -f sakana-desktop-assistant/data/logs/sakana.log | grep "Cognitive routing"
```

### Future Enhancements
- [ ] Add caching for repeated tasks
- [ ] Support async routing for long-running tasks
- [ ] Add routing metrics dashboard in Sakana UI
- [ ] Fine-tune ATM-R on Sakana's specific task distribution
```

---

## 6. Common Pitfalls & Solutions

### Pitfall 1: Forgetting to Update Submodule References

**Problem:**
```
Instance 2: *commits changes in sakana*
Instance 1: *runs integration test*
→ Test fails: "Old version of Sakana, doesn't have cognitive_routing.py!"
```

**Why it happens:**
VibeMind Root still points to old commit hash of sakana submodule.

**Solution:**
```bash
# After ANY commit in a submodule, update the root:
cd VibeMind
git add sakana-desktop-assistant  # Updates submodule reference
git commit -m "update: Sakana submodule (cognitive routing feature)"
```

**Best Practice:**
```
Instance 1 checklist:
- [ ] Instance 2 committed in sakana? → Update sakana ref in root
- [ ] Instance 3 committed in the_brain? → Update the_brain ref in root
- [ ] Both refs updated? → Run integration test
```

### Pitfall 2: Python Path Issues

**Problem:**
```python
# In Sakana
from the_brain.api.sakana_routing import SakanaRouter
→ ImportError: No module named 'the_brain'
```

**Why it happens:**
the_brain is not in Python's search path.

**Solutions:**

**Option A: Dynamic Path Manipulation (Recommended)**
```python
import sys
from pathlib import Path

# Calculate relative path to the_brain
VIBEMIND_ROOT = Path(__file__).parent.parent.parent  # From sakana/src/core/
sys.path.insert(0, str(VIBEMIND_ROOT / "the_brain"))

from api.sakana_routing import SakanaRouter  # Now works!
```

**Option B: PYTHONPATH Environment Variable**
```bash
# In sakana/.env or when running
export PYTHONPATH="${PYTHONPATH}:/path/to/VibeMind/the_brain"
python src/main.py
```

**Option C: Install as Package (Development Mode)**
```bash
cd the_brain
pip install -e .  # Install in editable mode

# Now can import anywhere
from the_brain.api.sakana_routing import SakanaRouter
```

### Pitfall 3: Circular Dependencies

**Problem:**
```
the_brain imports from sakana
sakana imports from the_brain
→ Circular import error!
```

**Why it happens:**
Poor interface design creating tight coupling.

**Solutions:**

**Option A: Dependency Inversion (Best)**
```
Create shared interface definition:

VibeMind/
├── interfaces/
│   └── task_routing.py  ← Shared interface

the_brain implements interface
sakana uses interface (doesn't directly import the_brain)
```

**Option B: One-Way Dependency**
```
✅ GOOD:  sakana → the_brain (Sakana depends on Brain)
❌ BAD:   the_brain → sakana (creates cycle)

Rule: Lower-level components (Brain) should NOT import higher-level (Sakana)
```

**Option C: Event-Based Communication**
```
Instead of direct imports, use events:

sakana publishes "task_received" event
the_brain listens and responds with "routing_decision" event
→ No direct coupling!
```

### Pitfall 4: Version Mismatch

**Problem:**
```
Sakana expects Brain API v2
Root points to Brain commit with API v1
→ Integration breaks!
```

**Why it happens:**
Submodule references not synchronized.

**Solution: Version Pinning**

```markdown
# VibeMind/docs/VERSION_COMPATIBILITY.md

## Submodule Version Requirements

| VibeMind Root | Sakana | The Brain | MoireTracker | Electron |
|---------------|--------|-----------|--------------|----------|
| v0.3.0        | v0.5.0+ | v0.2.0+  | v1.1.0+      | v0.4.0+  |
| v0.2.0        | v0.4.0+ | v0.1.0+  | v1.0.0+      | v0.3.0+  |

### Breaking Changes Log

**The Brain v0.2.0 → v0.3.0**
- BREAKING: SakanaRouter API signature changed
- Migration: Update sakana/src/core/cognitive_routing.py
```

**Best Practice:**
```bash
# In the_brain/api/sakana_routing.py
__version__ = "0.2.0"
__min_sakana_version__ = "0.5.0"

# Sakana checks version on import
from the_brain.api import sakana_routing
if sakana_routing.__version__ < "0.2.0":
    raise ValueError(f"The Brain API v0.2.0+ required, found {sakana_routing.__version__}")
```

### Pitfall 5: Testing Only Happy Path

**Problem:**
```
Integration test only tests when everything works.
In production: Brain is down → Sakana crashes!
```

**Solution: Test Failure Modes**

```python
# VibeMind/tests/integration/test_sakana_brain_routing.py

def test_brain_unavailable_fallback():
    """Test graceful degradation when Brain is down"""
    # Simulate Brain unavailable
    with mock.patch('the_brain.api.sakana_routing.SakanaRouter') as mock_brain:
        mock_brain.side_effect = ConnectionError("Brain service unavailable")

        router = CognitiveRouter()
        result = router.route_task("test task")

        # Should fall back to keyword routing
        assert result["fallback"] == True
        assert result["agent"] is not None  # Still routes!


def test_brain_timeout():
    """Test handling of Brain timeout"""
    with mock.patch('the_brain.api.sakana_routing.SakanaRouter.route_task') as mock_route:
        mock_route.side_effect = TimeoutError()

        router = CognitiveRouter()
        result = router.route_task("test task", timeout=1.0)

        # Should timeout gracefully
        assert result["fallback"] == True


def test_brain_invalid_response():
    """Test handling of malformed Brain response"""
    with mock.patch('the_brain.api.sakana_routing.SakanaRouter.route_task') as mock_route:
        mock_route.return_value = {"invalid": "response"}  # Missing 'agent' field

        router = CognitiveRouter()
        result = router.route_task("test task")

        # Should detect invalid response and fallback
        assert result["fallback"] == True
```

### Pitfall 6: Ignoring Performance

**Problem:**
```
Integration works but is slow:
User: "Create a PR"
→ 5 seconds later... PR created
→ User frustrated!
```

**Solution: Measure and Optimize**

```python
# Add performance monitoring
import time
import logging

def route_task(self, description, **kwargs):
    start = time.time()

    result = self.router.route_task(description, **kwargs)

    latency = time.time() - start
    logging.info(f"Routing latency: {latency*1000:.1f}ms")

    if latency > 0.1:  # 100ms threshold
        logging.warning(f"Slow routing detected: {latency*1000:.1f}ms")

    return result
```

**Optimization strategies:**
- Cache repeated routing decisions
- Use async/await for parallel operations
- Lazy-load models (don't load until first use)
- Consider response time SLAs (e.g., <100ms)

---

## 7. Integration Checklist

Use this checklist for ANY integration task:

### Pre-Integration

- [ ] **Research Phase Complete**
  - [ ] Read both submodules' READMEs
  - [ ] Understand existing architecture
  - [ ] Identify all files that need changes
  - [ ] Check for existing integration patterns

- [ ] **Integration Plan Created**
  - [ ] Data flow documented (A → B or A ↔ B?)
  - [ ] Interface defined (function signatures, data formats)
  - [ ] Technology barriers identified (Python ↔ C++, IPC needed?)
  - [ ] Testing strategy planned
  - [ ] Time estimate made

- [ ] **Pattern Selected**
  - [ ] Sequential, Parallel, Test-Driven, or Spike?
  - [ ] Rationale documented
  - [ ] Instance assignments made

### During Integration

- [ ] **Implementation**
  - [ ] Tests written (if using Test-Driven)
  - [ ] Provider component implemented (e.g., Brain API)
  - [ ] Consumer component implemented (e.g., Sakana wrapper)
  - [ ] Error handling added (fallback logic)
  - [ ] Performance monitoring added

- [ ] **Submodule Commits**
  - [ ] Provider submodule: committed and pushed
  - [ ] Consumer submodule: committed and pushed
  - [ ] Root: submodule references updated

- [ ] **Testing**
  - [ ] Unit tests pass (both submodules)
  - [ ] Integration tests pass
  - [ ] Failure modes tested (unavailable, timeout, invalid response)
  - [ ] Performance acceptable (latency, memory)

### Post-Integration

- [ ] **Documentation**
  - [ ] Integration plan updated with results
  - [ ] VibeMind/README.md updated
  - [ ] Submodule CLAUDE.md files updated
  - [ ] API documentation created/updated

- [ ] **Maintenance Plan**
  - [ ] Version compatibility documented
  - [ ] Monitoring strategy defined
  - [ ] Future enhancements listed

- [ ] **Knowledge Sharing**
  - [ ] Lessons learned documented
  - [ ] Common issues added to troubleshooting guide
  - [ ] Example code provided for future integrations

---

## Quick Decision Guide

**"I want to connect X to Y, what do I do?"**

### Step 1: Answer These Questions

1. **Same language?**
   - YES → Direct imports (easy)
   - NO → Need bridge (harder)

2. **Same process?**
   - YES → Function calls (fast)
   - NO → IPC/network (slower)

3. **Time sensitive?**
   - YES → Use Parallel pattern
   - NO → Use Sequential pattern

4. **Critical/risky?**
   - YES → Use Test-Driven pattern
   - NO → Use Sequential or Spike pattern

### Step 2: Follow the Pattern

- **Sequential**: Instance 3 → Instance 2 → Instance 1 (safe, slower)
- **Parallel**: Instance 2 & 3 simultaneously → Instance 1 (fast, needs coordination)
- **Test-Driven**: Instance 1 (tests) → Instances 2 & 3 (impl) → Instance 1 (verify)
- **Spike**: Instance 2 (quick hack) → Instance 1 (review) → Proper implementation

### Step 3: Use the Checklist

Follow the [Integration Checklist](#7-integration-checklist) above.

---

## Summary

Working on a big project like VibeMind is about **systematic methodology**:

1. **Always start with research** (Instance 1 leads)
2. **Define clear interfaces** (no tight coupling!)
3. **Choose the right orchestration pattern** (sequential vs parallel vs test-driven)
4. **Test failure modes** (not just happy path!)
5. **Document as you go** (future you will thank present you)
6. **Update submodule refs** (after EVERY commit!)

With 5 Claude instances, you can work much faster than traditional development:
- **Research in parallel** (all instances explore)
- **Implement in parallel** (with clear coordination)
- **Test continuously** (Instance 1 orchestrates)

The key is **orchestration**, not just parallel coding. You're the conductor of a 5-piece orchestra! 🎼

---

**Related Documentation:**
- [VIBECODING_WORKFLOW.md](VIBECODING_WORKFLOW.md) - Daily 5-instance workflow
- [PARALLEL_VIBECODING.md](PARALLEL_VIBECODING.md) - Orchestration mental model
- [VIBEMIND_CLAUDE_CODE_BEST_PRACTICES.md](VIBEMIND_CLAUDE_CODE_BEST_PRACTICES.md) - Claude Code best practices
- [docs/FULL_ECOSYSTEM_ARCHITECTURE.md](docs/FULL_ECOSYSTEM_ARCHITECTURE.md) - Complete system architecture
