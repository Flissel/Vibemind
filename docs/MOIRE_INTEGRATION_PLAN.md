# MoireTracker + Sakana Integration Plan
## Universal Desktop Automation Learning System

**Version:** 1.0
**Date:** 2025-10-22
**Status:** Planning Phase

---

## Executive Summary

This document outlines the integration of **MoireTracker** (OCR-based desktop automation) with **Sakana Desktop Assistant** (evolutionary self-learning system) to create a **universal, zero-code desktop automation platform** that learns from user behavior.

### Core Vision
**"Show me once, I'll learn forever"** - A system that observes user interactions, learns optimal strategies through evolutionary algorithms, and autonomously reproduces tasks without hardcoded functions.

---

## Current State Analysis

### MoireTracker Capabilities (Moire Project)
- ✅ **Windows OCR** via Windows.Media.Ocr
- ✅ **Desktop scanning** with spatial octree indexing
- ✅ **Window control** (focus, click, keyboard input)
- ✅ **IPC communication** via Windows Shared Memory
- ✅ **AutoGen Core 0.4** agent integration
- ✅ **Claude Sonnet 4** LLM integration via OpenRouter

### Sakana Capabilities (Existing)
- ✅ **Evolutionary learning** (EvolutionaryLearner with Individual genomes)
- ✅ **Memory system** (SQLite with short/long-term memory)
- ✅ **Pattern detection** (PatternDetector from user behavior)
- ✅ **Plugin architecture** (PluginManager with extensible tools)
- ✅ **Self-modification** (SelfModifier for code evolution)
- ✅ **MCP tool learning** (MCPToolLearner for telemetry-driven selection)
- ✅ **Reinforcement learning** (ReinforcementLearner from feedback)

### Integration Gap
- ❌ **No visual perception** - Sakana can't "see" the desktop
- ❌ **No UI automation** - Sakana can't click buttons or type in apps
- ❌ **No spatial reasoning** - Sakana doesn't understand UI layouts
- ❌ **Manual tool creation** - Each app requires hardcoded functions

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER BEHAVIOR LAYER                       │
│            (User performs tasks naturally)                       │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PERCEPTION LAYER (NEW)                         │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  MoireTracker Desktop Observer                           │   │
│  │  • Continuous OCR scanning (10 Hz)                       │   │
│  │  • Window state tracking                                 │   │
│  │  • Mouse/keyboard event capture                          │   │
│  │  • UI element spatial indexing                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  Output: Structured observations with spatial + temporal data    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              PATTERN EXTRACTION LAYER (ENHANCED)                 │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Sakana PatternDetector (Extended)                       │   │
│  │  • Sequence pattern recognition                          │   │
│  │  • UI workflow extraction                                │   │
│  │  • Repetition detection                                  │   │
│  │  • Semantic understanding (via LLM)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  Output: Actionable workflow patterns                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                 KNOWLEDGE BASE (ENHANCED)                        │
│                                                                   │
│  ┌──────────────────┐  ┌────────────────┐  ┌─────────────────┐ │
│  │ Sakana Memory    │  │ UI Patterns DB │  │ App Profiles DB │ │
│  │ (SQLite)         │  │ (New)          │  │ (New)           │ │
│  │                  │  │                │  │                 │ │
│  │ • Long-term mem  │  │ • Workflows    │  │ • Applications  │ │
│  │ • Short-term mem │  │ • Strategies   │  │ • UI structures │ │
│  │ • Conversations  │  │ • Genomes      │  │ • Capabilities  │ │
│  └──────────────────┘  └────────────────┘  └─────────────────┘ │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│            EVOLUTIONARY OPTIMIZATION (EXISTING + NEW)            │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Sakana EvolutionaryLearner (Enhanced)                   │   │
│  │                                                           │   │
│  │  Genome Structure (NEW):                                 │   │
│  │  {                                                        │   │
│  │    "task_id": "open_excel_blank",                        │   │
│  │    "strategy": {                                          │   │
│  │      "launch_method": "click_taskbar",                   │   │
│  │      "navigation_style": "visual_search",                │   │
│  │      "wait_times": [3.0, 1.0, 0.5],                      │   │
│  │      "verification_points": ["window_title", "ocr"]      │   │
│  │    },                                                     │   │
│  │    "fitness": 0.95,                                       │   │
│  │    "execution_time": 3.2,                                 │   │
│  │    "success_rate": 0.98                                   │   │
│  │  }                                                        │   │
│  │                                                           │   │
│  │  Operations:                                              │   │
│  │  • Mutate strategies (timing, methods, paths)            │   │
│  │  • Crossover successful approaches                       │   │
│  │  • Selection based on fitness                            │   │
│  │  • Archive best performers                               │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  EXECUTION LAYER (NEW + EXISTING)                │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  AutoGen Multi-Agent System (Enhanced)                   │   │
│  │                                                           │   │
│  │  Agents:                                                  │   │
│  │  • Coordinator (Plans tasks)                             │   │
│  │  • Executor (Performs actions via MoireTracker)          │   │
│  │  • Verifier (Checks results via OCR)                     │   │
│  │  • Learner (Feeds back to evolutionary system)           │   │
│  │                                                           │   │
│  │  Tools (NEW):                                             │   │
│  │  • scan_desktop() - MoireTracker OCR                     │   │
│  │  • click_element(text) - Click UI element                │   │
│  │  • type_in_window(text) - Type text                      │   │
│  │  • press_keys(combo) - Keyboard shortcuts                │   │
│  │  • verify_state(expected) - Check current state          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Sakana SandboxExecutor (Existing)                       │   │
│  │  • Secure code execution                                 │   │
│  │  • Generated automation scripts                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FEEDBACK LOOP (ENHANCED)                      │
│                                                                   │
│  Metrics collected:                                              │
│  • Success/failure rate                                          │
│  • Execution time                                                │
│  • User corrections                                              │
│  • Error patterns                                                │
│  • OCR verification confidence                                   │
│                                                                   │
│  Feeds into: EvolutionaryLearner fitness calculation             │
└──────────────────────────────────────────────────────────────────┘
```

---

## Integration Components

### 1. Desktop Observer Plugin (NEW)
**File:** `src/plugins/desktop_observer.py`

**Responsibilities:**
- Continuously monitor desktop state via MoireTracker
- Capture user mouse/keyboard events
- Record screen state changes
- Detect application launches and window switches
- Store observations in structured format

**Integration Points:**
- Uses MoireTracker C++ service via Python client
- Stores observations in Sakana's memory system
- Triggers pattern detection on observation batches

**Implementation:**
```python
class DesktopObserverPlugin:
    """Observes desktop activity via MoireTracker"""

    def __init__(self, moire_client, memory_manager):
        self.moire = moire_client
        self.memory = memory_manager
        self.observation_buffer = []

    async def observe_continuously(self):
        """Main observation loop"""
        while self.enabled:
            # Scan desktop
            elements = self.moire.scan_desktop()
            active_window = self.get_active_window()

            # Detect user actions
            if event := self.detect_user_action():
                observation = {
                    "timestamp": datetime.now(),
                    "event_type": event.type,
                    "screen_state": elements,
                    "active_window": active_window,
                    "user_action": event.details
                }
                self.observation_buffer.append(observation)

            # Batch process every 100 observations
            if len(self.observation_buffer) >= 100:
                await self.process_observations()

            await asyncio.sleep(0.1)  # 10 Hz
```

---

### 2. UI Pattern Detector (ENHANCED)
**File:** `src/learning/ui_pattern_detector.py` (extends PatternDetector)

**Responsibilities:**
- Identify repeated UI interaction sequences
- Extract actionable workflows
- Recognize UI structure patterns (menus, ribbons, grids)
- Calculate automation potential

**Integration Points:**
- Extends Sakana's existing PatternDetector
- Uses LLM for semantic understanding
- Stores patterns in new UI Patterns DB

**Implementation:**
```python
class UIPatternDetector(PatternDetector):
    """Detects UI interaction patterns"""

    def detect_ui_patterns(self, observations: List[Dict]) -> List[Pattern]:
        """Find repeating UI sequences"""

        # Group by application
        by_app = self.group_by_application(observations)

        patterns = []
        for app, obs_list in by_app.items():
            # Find repeated sequences
            sequences = self.find_repeated_sequences(obs_list)

            for seq in sequences:
                if seq.repetitions >= 3:  # Repeated 3+ times
                    # Use LLM to understand semantic meaning
                    description = await self.llm.describe_workflow(seq)

                    pattern = UIPattern(
                        application=app,
                        sequence=seq,
                        description=description,
                        automation_potential=self.calculate_value(seq),
                        frequency=seq.repetitions
                    )
                    patterns.append(pattern)

        return patterns
```

---

### 3. Desktop Automation Genome (NEW)
**File:** `src/learning/desktop_automation_genome.py`

**Responsibilities:**
- Represent automation strategies as evolvable genomes
- Define mutation operators for UI workflows
- Implement crossover for strategy breeding
- Calculate fitness from execution metrics

**Genome Structure:**
```python
@dataclass
class DesktopAutomationGenome:
    """Evolvable automation strategy"""

    # Core strategy
    task_id: str
    application: str

    # Launch strategy
    launch_method: str  # "click_taskbar", "start_menu", "keyboard"
    launch_target: str  # "Excel icon", "Microsoft Excel"

    # Navigation strategy
    navigation_style: str  # "visual_search", "keyboard_nav", "menu_path"
    navigation_sequence: List[str]  # ["File", "New", "Blank"]

    # Timing strategy
    wait_times: List[float]  # Adaptive delays
    timeout: float

    # Verification strategy
    verification_method: str  # "ocr", "window_title", "both"
    success_indicators: List[str]

    # Fallback strategy
    fallback_chain: List[str]  # Alternative methods
    max_retries: int

    # Performance metrics
    fitness: float
    success_rate: float
    avg_execution_time: float
    reliability_score: float

    def mutate(self, mutation_rate=0.1) -> 'DesktopAutomationGenome':
        """Create variation of strategy"""
        new_genome = copy.deepcopy(self)

        if random() < mutation_rate:
            # Try faster timing
            new_genome.wait_times = [t * 0.9 for t in self.wait_times]

        if random() < mutation_rate:
            # Try different launch method
            alternatives = ["click_taskbar", "start_menu", "keyboard"]
            new_genome.launch_method = random.choice(alternatives)

        if random() < mutation_rate:
            # Try different navigation
            new_genome.navigation_style = random.choice([
                "visual_search", "keyboard_nav", "menu_path"
            ])

        return new_genome

    def calculate_fitness(self) -> float:
        """Fitness = success + speed + reliability"""
        return (
            self.success_rate * 0.6 +
            (1.0 / max(self.avg_execution_time, 0.1)) * 0.3 +
            self.reliability_score * 0.1
        )
```

---

### 4. Automation Executor Agent (NEW)
**File:** `src/execution/automation_executor.py`

**Responsibilities:**
- Execute learned automation strategies
- Use MoireTracker for visual perception and control
- Verify success at each step
- Record metrics for fitness calculation

**Integration Points:**
- Uses AutoGen Core for agent orchestration
- Calls MoireTracker via Python client
- Reports metrics to EvolutionaryLearner

**Implementation:**
```python
class AutomationExecutor:
    """Executes automation strategies"""

    def __init__(self, moire_client, evolutionary_learner):
        self.moire = moire_client
        self.evolution = evolutionary_learner

    async def execute_strategy(self, genome: DesktopAutomationGenome) -> ExecutionResult:
        """Execute automation with verification"""

        start_time = time.time()
        steps_completed = []

        try:
            # Step 1: Launch application
            if genome.launch_method == "click_taskbar":
                success = await self.click_taskbar_icon(genome.launch_target)
            elif genome.launch_method == "start_menu":
                success = await self.open_via_start_menu(genome.launch_target)
            else:
                success = await self.launch_via_keyboard(genome.launch_target)

            if not success:
                return ExecutionResult(success=False, reason="launch_failed")

            # Wait for launch
            await asyncio.sleep(genome.wait_times[0])

            # Step 2: Verify application opened
            if not await self.verify_app_open(genome.success_indicators):
                return ExecutionResult(success=False, reason="verification_failed")

            # Step 3: Execute navigation sequence
            for step in genome.navigation_sequence:
                if genome.navigation_style == "visual_search":
                    success = await self.click_by_ocr(step)
                elif genome.navigation_style == "keyboard_nav":
                    success = await self.navigate_by_keyboard(step)
                else:
                    success = await self.navigate_by_menu(step)

                if not success:
                    return ExecutionResult(success=False, reason=f"nav_failed_{step}")

                steps_completed.append(step)

            # Success!
            execution_time = time.time() - start_time

            # Update genome fitness
            genome.success_rate = (genome.success_rate * 0.9 + 1.0 * 0.1)
            genome.avg_execution_time = (
                genome.avg_execution_time * 0.9 + execution_time * 0.1
            )
            genome.fitness = genome.calculate_fitness()

            return ExecutionResult(
                success=True,
                execution_time=execution_time,
                steps_completed=steps_completed
            )

        except Exception as e:
            # Failure - penalize fitness
            genome.success_rate *= 0.9
            genome.fitness = genome.calculate_fitness()

            return ExecutionResult(success=False, reason=str(e))
```

---

## Database Schema Extensions

### New Table: `ui_patterns`
```sql
CREATE TABLE ui_patterns (
    pattern_id TEXT PRIMARY KEY,
    application TEXT NOT NULL,
    task_description TEXT,
    action_sequence JSON,  -- List of actions
    frequency INTEGER,     -- How often observed
    automation_potential REAL,
    created_at TIMESTAMP,
    last_observed TIMESTAMP,
    status TEXT  -- "observed", "suggested", "automated"
);
```

### New Table: `application_profiles`
```sql
CREATE TABLE application_profiles (
    app_id TEXT PRIMARY KEY,
    display_name TEXT,
    window_titles JSON,    -- List of known window titles
    identifying_text JSON, -- OCR markers (e.g., "AutoSave", "File")
    ui_structure JSON,     -- {"menu_bar": {...}, "ribbon": {...}}
    common_tasks JSON,     -- Task IDs
    learned_at TIMESTAMP,
    last_used TIMESTAMP
);
```

### New Table: `automation_genomes`
```sql
CREATE TABLE automation_genomes (
    genome_id TEXT PRIMARY KEY,
    task_id TEXT,
    application TEXT,
    genome_json JSON,  -- Full DesktopAutomationGenome
    fitness REAL,
    generation INTEGER,
    parent_ids JSON,
    mutations JSON,
    created_at TIMESTAMP,
    last_executed TIMESTAMP,
    execution_count INTEGER,
    success_count INTEGER
);
```

---

## Evolutionary Learning Flow

### 1. Observation Phase
```
User performs task manually
    ↓
DesktopObserverPlugin records:
  • Screen states (OCR)
  • Mouse clicks (x, y, target)
  • Keyboard input
  • Window changes
    ↓
Stored in memory with spatial + temporal data
```

### 2. Pattern Detection Phase
```
UIPatternDetector analyzes observations:
  • Groups by application
  • Finds repeated sequences (3+ times)
  • Extracts workflows
  • Uses LLM to understand semantics
    ↓
Creates UIPattern objects
    ↓
Stored in ui_patterns table
```

### 3. Genome Creation Phase
```
For each high-value pattern:
  Create initial DesktopAutomationGenome
    • Extract launch method from observations
    • Extract navigation sequence
    • Set default timing
    • Define verification points
    ↓
Add to EvolutionaryLearner population
    ↓
Store in automation_genomes table
```

### 4. Evolution Phase
```
EvolutionaryLearner.evolve():
  For each genome in population:
    • Execute strategy
    • Measure fitness
    ↓
  Select top performers
    ↓
  Create next generation:
    • Mutate (timing, methods, paths)
    • Crossover (combine successful strategies)
    ↓
  Test new strategies
    ↓
  Update fitness scores
    ↓
  Archive best performers
```

### 5. Autonomous Execution Phase
```
User requests: "Open Excel with blank workbook"
    ↓
System retrieves best genome for task
    ↓
AutomationExecutor.execute_strategy(genome)
    ↓
Success → Update fitness positively
Failure → Update fitness negatively, try alternative
    ↓
Record metrics for next evolution cycle
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
**Goal:** Basic observation and storage

- [ ] Create `DesktopObserverPlugin`
  - Connect to MoireTracker service
  - Implement observation loop
  - Store observations in memory

- [ ] Extend database schema
  - Add `ui_patterns` table
  - Add `application_profiles` table
  - Add `automation_genomes` table

- [ ] Test basic observation
  - Observe Excel opening manually
  - Verify data storage
  - Check OCR capture quality

**Deliverable:** System can observe and store user desktop interactions

---

### Phase 2: Pattern Recognition (Week 3-4)
**Goal:** Detect and understand patterns

- [ ] Create `UIPatternDetector`
  - Implement sequence detection
  - Add LLM-based semantic analysis
  - Calculate automation potential

- [ ] Create `DesktopAutomationGenome`
  - Define genome structure
  - Implement mutation operators
  - Add fitness calculation

- [ ] Test pattern detection
  - Perform repetitive Excel task
  - Verify pattern extraction
  - Review LLM descriptions

**Deliverable:** System can identify automatable patterns

---

### Phase 3: Evolution (Week 5-6)
**Goal:** Optimize strategies through evolution

- [ ] Integrate with `EvolutionaryLearner`
  - Adapt for desktop automation genomes
  - Implement desktop-specific mutations
  - Add crossover for UI strategies

- [ ] Create `AutomationExecutor`
  - Implement strategy execution
  - Add verification at each step
  - Record fitness metrics

- [ ] Test evolution
  - Create initial population from patterns
  - Run 10 generations
  - Compare fitness improvement

**Deliverable:** System evolves better automation strategies

---

### Phase 4: Autonomous Execution (Week 7-8)
**Goal:** Full autonomous task execution

- [ ] Create multi-agent system
  - Coordinator agent (plans)
  - Executor agent (performs via MoireTracker)
  - Verifier agent (checks via OCR)
  - Learner agent (feeds back metrics)

- [ ] Add fallback mechanisms
  - Try alternative strategies on failure
  - Request user demonstration if stuck
  - Learn from corrections

- [ ] End-to-end testing
  - "Open Excel blank workbook"
  - "Enter data into spreadsheet"
  - "Save file with custom name"

**Deliverable:** System autonomously executes learned tasks

---

### Phase 5: User Experience (Week 9-10)
**Goal:** Polish and integrate into Sakana UI

- [ ] Add learning mode UI
  - "Start Learning" button
  - Real-time observation feedback
  - Pattern suggestion notifications

- [ ] Add automation UI
  - List of learned tasks
  - Execute/Edit/Delete actions
  - Metrics dashboard

- [ ] Add suggestion system
  - Detect repetitive tasks
  - Offer automation proactively
  - "Would you like me to automate this?"

**Deliverable:** Polished user experience

---

## Configuration

### New config.yaml sections

```yaml
desktop_automation:
  enabled: true

  # MoireTracker connection
  moire_tracker:
    service_path: "C:/Users/User/Desktop/Moire/build/Release/MoireTracker.exe"
    ipc_timeout_ms: 5000
    max_retries: 3

  # Observation settings
  observation:
    enabled: true
    frequency_hz: 10  # 10 scans per second
    buffer_size: 1000
    private_applications:
      - "Password Manager"
      - "Banking"

  # Pattern detection
  patterns:
    min_repetitions: 3  # Suggest after 3 repetitions
    automation_threshold: 0.7  # Only suggest high-value (70%+)
    llm_analysis: true

  # Evolution
  evolution:
    population_size: 20
    generations_per_task: 10
    mutation_rate: 0.15
    selection_pressure: 0.7

  # Execution
  execution:
    verify_each_step: true
    max_retries: 2
    fallback_enabled: true
```

---

## Testing Strategy

### Unit Tests
- `test_desktop_observer.py`
- `test_ui_pattern_detector.py`
- `test_desktop_automation_genome.py`
- `test_automation_executor.py`

### Integration Tests
- `test_moire_sakana_integration.py`
- `test_observation_to_pattern.py`
- `test_pattern_to_execution.py`

### End-to-End Tests
- `test_excel_automation_e2e.py` - Full Excel workflow
- `test_learning_from_demonstration.py` - User demo → automation
- `test_evolution_improvement.py` - Verify fitness improvement

---

## Success Metrics

### Observation Phase
- ✅ Capture 95%+ of user actions
- ✅ OCR accuracy > 90%
- ✅ < 5% CPU overhead

### Pattern Detection Phase
- ✅ Detect 80%+ of repetitive tasks
- ✅ < 5% false positives
- ✅ Semantic descriptions match user intent

### Evolution Phase
- ✅ Fitness improvement > 20% over 10 generations
- ✅ Top strategy success rate > 95%
- ✅ Execution time reduction > 15%

### Autonomous Execution Phase
- ✅ Task success rate > 90%
- ✅ Faster than manual execution
- ✅ < 1 user correction per 10 executions

---

## Risk Mitigation

### Privacy Concerns
- **Risk:** Observing sensitive information
- **Mitigation:**
  - User-configurable private apps list
  - No observation of password fields
  - Local-only data storage
  - Clear data retention policy

### Performance Impact
- **Risk:** Background observation slows system
- **Mitigation:**
  - Async observation loop
  - Batch processing
  - Configurable frequency
  - CPU throttling

### False Positives
- **Risk:** Suggesting automation for non-repetitive tasks
- **Mitigation:**
  - Require 3+ repetitions
  - Calculate automation value
  - User approval before execution
  - Easy disable mechanism

### Evolution Divergence
- **Risk:** Mutations create broken strategies
- **Mitigation:**
  - Verify each generation
  - Keep archive of working strategies
  - Fallback to known-good approaches
  - User override always available

---

## Future Enhancements

### Phase 6: Multi-Application Workflows
- Chain tasks across multiple apps
- Example: "Get data from website → Paste in Excel → Email report"

### Phase 7: Natural Language Interface
- "Every Friday, generate weekly report"
- "When I receive email from Boss, create summary"

### Phase 8: Collaborative Learning
- Share anonymized patterns across users (opt-in)
- Community-voted best strategies
- Transfer learning from similar apps

### Phase 9: Predictive Automation
- Anticipate user needs
- "You usually do this now, should I start?"
- Proactive suggestions

---

## Conclusion

This integration combines:
- **MoireTracker's** visual perception and control capabilities
- **Sakana's** evolutionary learning and self-improvement systems
- **AutoGen's** multi-agent orchestration

To create a **universal desktop automation platform** that:
1. ✅ Learns by observing (no manual coding)
2. ✅ Evolves optimal strategies (genetic algorithms)
3. ✅ Executes autonomously (verified at each step)
4. ✅ Improves continuously (from every execution)

**Next Step:** Begin Phase 1 implementation of `DesktopObserverPlugin`

---

## References

- MoireTracker: `C:/Users/User/Desktop/Moire/`
- Sakana: `C:/Users/User/Desktop/sakana-desktop-assistant/`
- AutoGen Core 0.4: https://github.com/microsoft/autogen
- Evolutionary Algorithms: Sakana AI research papers

---

**Document Status:** Ready for review and implementation approval
