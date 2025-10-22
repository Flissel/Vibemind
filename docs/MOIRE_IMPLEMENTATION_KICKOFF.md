# MOIRE Integration - Implementation Kickoff
**Date:** 2025-10-22
**Branch:** `feature/moire-integration`
**Status:** Ready to implement

---

## ✅ Prerequisites Verified

### MoireTracker Status
- **Location:** `C:/Users/User/Desktop/Moire/`
- **Executable:** `build/Release/MoireTracker.exe` (1.8MB, Oct 22 01:34)
- **Python Client:** `C:/Users/User/Desktop/voice_dialog/python/tools/moire_client.py`
- **AutoGen Integration:** `moire_agent_toolkit.py` with complete tool suite
- **Status:** ✅ **READY TO USE**

### Available MoireTracker Capabilities
From `moire_agent_toolkit.py`, the client provides:

#### Visual Perception
- `scan_desktop()` - OCR scan of entire screen
- `find_text(search_text)` - Locate specific text
- `find_element(text)` - Find UI element with coordinates
- `verify_text_visible(text)` - Check if text is on screen

#### Window Management
- `get_active_window()` - Get current window title
- `focus_window(title)` - Bring window to front
- `close_window(title)` - Close application
- `click_at(x, y)` - Click coordinates

#### Input Control
- `type_text(text)` - Keyboard input
- `press_keys(keys)` - Key combinations (Ctrl+C, etc.)

---

## 🎯 Implementation Strategy: **Vertical Slice**

We'll build **end-to-end for ONE simple task** to prove the concept, then expand.

### Chosen Task: **"Open Excel with Blank Workbook"**

**Why this task?**
- Simple enough to implement quickly (1-2 weeks)
- Complex enough to test all integration points
- Real-world use case with clear success criteria
- Can expand to full Excel automation later

### Success Criteria
1. ✅ Observe user manually opening Excel 3 times
2. ✅ Detect the pattern automatically
3. ✅ Create automation genome (launch method, timing, verification)
4. ✅ Execute autonomously with >90% success rate
5. ✅ Faster than manual execution

---

## 📋 Phase 1: Basic Observation (Week 1)

### Goal
System can observe and store desktop interactions

### Tasks

#### 1.1 Copy MoireTracker Client
```bash
# Copy Python client to Sakana
cp "C:/Users/User/Desktop/voice_dialog/python/tools/moire_client.py" \
   "src/plugins/moire_client.py"

# Copy toolkit (optional, for reference)
cp "C:/Users/User/Desktop/Moire/moire_agent_toolkit.py" \
   "docs/reference/moire_agent_toolkit.py"
```

#### 1.2 Create DesktopObserverPlugin
**File:** `src/plugins/desktop_observer.py`

```python
class DesktopObserverPlugin:
    """Observes desktop activity via MoireTracker"""

    def __init__(self, moire_client, memory_manager):
        self.moire = moire_client
        self.memory = memory_manager
        self.observation_buffer = []
        self.enabled = False

    async def start_observing(self):
        """Begin continuous observation"""
        self.enabled = True
        asyncio.create_task(self._observe_loop())

    async def _observe_loop(self):
        """Main observation loop - 10 Hz"""
        while self.enabled:
            try:
                # Scan desktop
                elements = self.moire.scan_desktop()
                active_window = self.moire.get_active_window()

                # Create observation record
                observation = {
                    "timestamp": datetime.now().isoformat(),
                    "screen_elements": elements,
                    "active_window": active_window,
                    "event_type": "scan"
                }

                self.observation_buffer.append(observation)

                # Process batch every 10 observations
                if len(self.observation_buffer) >= 10:
                    await self._process_batch()

            except Exception as e:
                logger.error(f"Observation error: {e}")

            await asyncio.sleep(0.1)  # 10 Hz

    async def _process_batch(self):
        """Store batch in memory"""
        for obs in self.observation_buffer:
            memory = Memory(
                type=MemoryType.SHORT_TERM,
                content=json.dumps(obs),
                context={"type": "desktop_observation"}
            )
            await self.memory.store_memory(memory)

        self.observation_buffer.clear()
```

#### 1.3 Test Basic Observation
**File:** `tests/mcp_servers/test_desktop_observer.py`

```python
async def test_moire_connection():
    """Test connection to MoireTracker"""
    client = MoireTrackerClient()
    client.connect()

    # Test OCR scan
    elements = client.scan_desktop()
    assert len(elements) > 0

    client.disconnect()

async def test_observation_storage():
    """Test storing observations in memory"""
    # Initialize
    memory = MemoryManager(db_path=":memory:")
    await memory.initialize()

    moire = MoireTrackerClient()
    moire.connect()

    observer = DesktopObserverPlugin(moire, memory)

    # Observe for 5 seconds
    await observer.start_observing()
    await asyncio.sleep(5)
    observer.enabled = False

    # Verify stored
    memories = await memory.retrieve_memories(limit=100)
    desktop_obs = [m for m in memories if m.context.get("type") == "desktop_observation"]

    assert len(desktop_obs) > 0
    print(f"Stored {len(desktop_obs)} observations")
```

### Deliverable
- ✅ MoireTracker client integrated
- ✅ DesktopObserverPlugin working
- ✅ Observations stored in memory
- ✅ Test passes

---

## 📋 Phase 2: Pattern Detection (Week 2)

### Goal
Detect "Open Excel" pattern from observations

### Tasks

#### 2.1 Extend UIPatternDetector
**File:** `src/learning/ui_pattern_detector.py`

```python
class UIPatternDetector(PatternDetector):
    """Detects UI interaction patterns from observations"""

    async def detect_excel_launch_pattern(self):
        """Detect Excel opening sequence"""

        # Get observations
        observations = await self.memory_manager.retrieve_memories(
            query="desktop_observation",
            limit=1000
        )

        # Find sequences where Excel appears
        excel_sequences = []
        for i, obs in enumerate(observations):
            data = json.loads(obs.content)
            if "Excel" in data.get("active_window", ""):
                # Track previous 5 observations
                sequence = observations[max(0, i-5):i+1]
                excel_sequences.append(sequence)

        # Find common patterns
        if len(excel_sequences) >= 3:
            # Analyze what happened before Excel opened
            pattern = self._analyze_launch_sequence(excel_sequences)
            return pattern

        return None

    def _analyze_launch_sequence(self, sequences):
        """Extract common launch method"""

        # Check if user clicked Start menu, taskbar, or used search
        launch_methods = []
        for seq in sequences:
            # Look at observations before Excel appeared
            for obs in seq[:-1]:
                data = json.loads(obs.content)
                elements = data.get("screen_elements", [])

                # Check what was clicked
                if any("Start" in e.get("text", "") for e in elements):
                    launch_methods.append("start_menu")
                elif any("Excel" in e.get("text", "") for e in elements):
                    launch_methods.append("taskbar_icon")

        # Most common method
        most_common = max(set(launch_methods), key=launch_methods.count)

        return UIPattern(
            application="Excel",
            task_description="Open Excel with blank workbook",
            launch_method=most_common,
            frequency=len(sequences),
            automation_potential=0.95
        )
```

#### 2.2 Create Initial Genome
**File:** `src/learning/desktop_automation_genome.py`

```python
@dataclass
class DesktopAutomationGenome:
    """Evolvable automation strategy"""

    task_id: str
    application: str
    launch_method: str  # "start_menu", "taskbar_icon", "keyboard"
    launch_target: str  # "Excel", "Microsoft Excel"
    wait_times: List[float]  # [3.0, 1.0, 0.5]
    verification_method: str  # "window_title", "ocr"
    success_indicators: List[str]  # ["Excel", "Book1"]

    fitness: float = 0.0
    success_rate: float = 0.0
    avg_execution_time: float = 0.0

    def calculate_fitness(self) -> float:
        """Fitness = success + speed + reliability"""
        return (
            self.success_rate * 0.6 +
            (1.0 / max(self.avg_execution_time, 0.1)) * 0.3 +
            0.1  # Baseline
        )
```

### Deliverable
- ✅ Detect Excel launch pattern after 3 repetitions
- ✅ Create initial genome with launch method
- ✅ Test pattern detection

---

## 📋 Phase 3: Autonomous Execution (Week 3)

### Goal
Execute "Open Excel" autonomously

### Tasks

#### 3.1 Create AutomationExecutor
**File:** `src/execution/automation_executor.py`

```python
class AutomationExecutor:
    """Executes desktop automation strategies"""

    def __init__(self, moire_client):
        self.moire = moire_client

    async def execute_genome(self, genome: DesktopAutomationGenome):
        """Execute automation strategy"""

        start_time = time.time()

        try:
            # Step 1: Launch Excel
            if genome.launch_method == "taskbar_icon":
                # Find Excel icon
                result = self.moire.find_text("Excel")
                if "FOUND" in result:
                    # Extract coordinates
                    x, y = self._parse_coordinates(result)
                    self.moire.click_at(x, y)
                else:
                    return ExecutionResult(success=False, reason="icon_not_found")

            elif genome.launch_method == "start_menu":
                # Open Start menu
                self.moire.press_keys("win")
                await asyncio.sleep(0.5)

                # Type Excel
                self.moire.type_text("Excel")
                await asyncio.sleep(0.5)

                # Press Enter
                self.moire.press_keys("enter")

            # Step 2: Wait for launch
            await asyncio.sleep(genome.wait_times[0])

            # Step 3: Verify Excel opened
            if genome.verification_method == "window_title":
                window = self.moire.get_active_window()
                if "Excel" not in window:
                    return ExecutionResult(success=False, reason="verification_failed")

            # Success!
            execution_time = time.time() - start_time

            # Update genome metrics
            genome.success_rate = genome.success_rate * 0.9 + 1.0 * 0.1
            genome.avg_execution_time = (
                genome.avg_execution_time * 0.9 + execution_time * 0.1
            )
            genome.fitness = genome.calculate_fitness()

            return ExecutionResult(
                success=True,
                execution_time=execution_time
            )

        except Exception as e:
            return ExecutionResult(success=False, reason=str(e))
```

### Deliverable
- ✅ Execute "Open Excel" autonomously
- ✅ >90% success rate
- ✅ Faster than manual (< 5 seconds)

---

## 📋 Phase 4: Evolution (Week 4)

### Goal
Optimize strategy through genetic algorithms

### Tasks

#### 4.1 Integrate with EvolutionaryLearner
```python
# Create population
base_genome = DesktopAutomationGenome(
    task_id="open_excel",
    application="Excel",
    launch_method="taskbar_icon",
    launch_target="Excel",
    wait_times=[3.0, 1.0, 0.5],
    verification_method="window_title",
    success_indicators=["Excel", "Book1"]
)

# Initialize population
learner.initialize_population(base_genome)

# Evolve for 10 generations
for gen in range(10):
    # Test each genome
    await learner.evaluate_population(fitness_function)

    # Breed next generation
    learner.evolve_generation()

# Get best strategy
best_genome = learner.get_best_genome()
print(f"Best fitness: {best_genome.fitness}")
print(f"Launch method: {best_genome.launch_method}")
print(f"Avg time: {best_genome.avg_execution_time}s")
```

### Deliverable
- ✅ Evolution improves fitness by >20%
- ✅ Best strategy has >95% success rate
- ✅ Execution time reduced by >15%

---

## 🗂️ Database Schema

### New Tables

```sql
CREATE TABLE ui_patterns (
    pattern_id TEXT PRIMARY KEY,
    application TEXT NOT NULL,
    task_description TEXT,
    action_sequence JSON,
    frequency INTEGER,
    automation_potential REAL,
    created_at TIMESTAMP,
    last_observed TIMESTAMP,
    status TEXT  -- "observed", "suggested", "automated"
);

CREATE TABLE automation_genomes (
    genome_id TEXT PRIMARY KEY,
    task_id TEXT,
    application TEXT,
    genome_json JSON,
    fitness REAL,
    generation INTEGER,
    created_at TIMESTAMP,
    execution_count INTEGER,
    success_count INTEGER
);
```

---

## 📦 File Structure

```
src/
├── plugins/
│   ├── moire_client.py         # NEW: MoireTracker Python client
│   └── desktop_observer.py     # NEW: Desktop observation plugin
├── learning/
│   ├── ui_pattern_detector.py  # NEW: UI pattern detection
│   └── desktop_automation_genome.py  # NEW: Genome for desktop automation
├── execution/
│   └── automation_executor.py  # NEW: Execute automation strategies
└── memory/
    └── pattern_detector.py      # EXTENDED: Add UI patterns

tests/
└── mcp_servers/
    ├── test_desktop_observer.py   # NEW: Observer tests
    ├── test_ui_pattern_detector.py  # NEW: Pattern detection tests
    └── test_automation_executor.py  # NEW: Execution tests

docs/
├── MOIRE_INTEGRATION_PLAN.md        # EXISTING: Full plan
└── MOIRE_IMPLEMENTATION_KICKOFF.md  # NEW: This file
```

---

## ⏱️ Timeline

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1 | Observation | Desktop observer working, storing observations |
| 2 | Pattern Detection | Detect "Open Excel" pattern, create genome |
| 3 | Execution | Execute autonomously, >90% success |
| 4 | Evolution | Evolve strategy, improve by >20% |

---

## 🚀 Next Steps

1. **Copy MoireTracker client** to Sakana
2. **Create DesktopObserverPlugin** skeleton
3. **Write test** for basic observation
4. **Run test** and verify OCR working

**Ready to start?** Let's begin with Phase 1!

---

## 📚 References

- MoireTracker: `C:/Users/User/Desktop/Moire/`
- Python Client: `C:/Users/User/Desktop/voice_dialog/python/tools/moire_client.py`
- Toolkit: `C:/Users/User/Desktop/Moire/moire_agent_toolkit.py`
- Integration Plan: `docs/MOIRE_INTEGRATION_PLAN.md`
- Learning Quickstart: `docs/LEARNING_QUICKSTART.md`
