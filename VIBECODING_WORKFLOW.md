# VibeCoding 5-Instance Workflow Guide

Working alone with 5 Claude Code instances across VibeMind submodules.

## Instance Assignments

| Instance | Submodule | Focus | Claude's Role |
|----------|-----------|-------|---------------|
| **1️⃣** | VibeMind Root | Integration coordination | Cross-submodule architecture, docs updates, submodule reference management |
| **2️⃣** | sakana-desktop-assistant | AI Core development | MCP agents, learning systems, Sakana-specific features |
| **3️⃣** | the_brain | Cognitive architecture | ATM-R, predictive coding, cognitive systems |
| **4️⃣** | MoireTracker | Desktop automation | C++ automation, Windows IPC, screen capture |
| **5️⃣** | electron | Voice UI | React UI, voice recognition, Electron app |

## Quick Launch

**Windows:**
```powershell
.\launch_vibecoding.ps1
```

**Unix/macOS:**
```bash
./launch_vibecoding.sh
```

## Typical Workflows

### Workflow 1: Cross-Submodule Feature (e.g., Cognitive Routing)

**Step 1: Plan in Instance 1 (VibeMind Root)**
```
Task: Plan cognitive routing integration
- Review docs/TAHLAMUS_INTEGRATION_PLAN.md
- Create integration architecture diagram
- Define interface between Sakana and The Brain
```

**Step 2: Implement in Instance 3 (The Brain)**
```
Task: Add Sakana integration hooks to ATM-R
- Create new API in core/thalamo_pc_adaptive.py
- Add Sakana-specific configuration
- Write integration tests
- Commit and push: git push origin feature/sakana-integration
```

**Step 3: Implement in Instance 2 (Sakana)**
```
Task: Use The Brain's ATM-R in Sakana
- Create src/core/cognitive_routing.py
- Import from the_brain via Python path manipulation
- Integrate with existing MCP agents
- Commit and push: git push origin feature/cognitive-routing
```

**Step 4: Update in Instance 1 (VibeMind Root)**
```
Task: Update submodule references
- git add the_brain sakana-desktop-assistant
- git commit -m "Update submodules for cognitive routing"
- Update docs/TAHLAMUS_INTEGRATION_PLAN.md with progress
```

### Workflow 2: Parallel Independent Development

**Instance 2 (Sakana):** New MCP agent development
**Instance 3 (The Brain):** Performance optimization
**Instance 4 (MoireTracker):** Bug fix
**Instance 5 (Electron):** UI enhancement
**Instance 1 (Root):** Monitor and coordinate

### Workflow 3: Desktop Automation Integration

**Instance 4 (MoireTracker):**
- Implement shared memory IPC API
- Create automation task protocol

**Instance 2 (Sakana):**
- Create MoireTracker client in src/automation/
- Add MCP agent for desktop control

**Instance 1 (Root):**
- Update docs/MOIRE_INTEGRATION_PLAN.md
- Coordinate interface design

## Communication Between Instances

Since you're working alone, use **Instance 1 as your coordination hub**:

### Pattern: Message Passing

**In Instance 1 (Root), create integration notes:**
```markdown
## Active Work (2025-10-24)

### Instance 2 (Sakana)
- Working on: MCP Memory agent optimization
- Blocked by: Need the_brain API update
- Next: Integrate new ATM-R routing once Instance 3 completes

### Instance 3 (The Brain)
- Working on: Add async routing support
- Status: 80% complete
- Next: Commit and notify Instance 2

### Instance 4 (MoireTracker)
- Working on: Screen capture performance
- Status: Testing

### Instance 5 (Electron)
- Working on: Voice command routing
- Waiting for: Sakana API changes
```

## Git Workflow for 5 Instances

### Branching Strategy

```
Instance 1 (Root): main branch (integration)
Instance 2 (Sakana): feature/your-feature-name
Instance 3 (The Brain): feature/your-feature-name
Instance 4 (MoireTracker): feature/your-feature-name
Instance 5 (Electron): feature/your-feature-name
```

### Syncing Pattern

**Every 30-60 minutes, in Instance 1:**
```bash
# Check status of all submodules
git submodule foreach 'echo "=== $name ===" && git status --short'

# Pull latest from each
git submodule foreach 'git pull origin main --rebase'

# Update VibeMind references
git add -u
git commit -m "Sync submodule references"
```

## Daily Workflow

### Morning Setup (5-10 minutes)

1. Launch all 5 instances: `./launch_vibecoding.ps1`
2. In **Instance 1**, review active work status
3. In each submodule instance, pull latest: `git pull origin main`
4. Plan the day's work across instances

### During Development

- **Instance 1**: Keep open for coordination, documentation, cross-cutting decisions
- **Instances 2-5**: Focus on specific submodule work
- **Switch context** every 30-60 minutes to avoid mental fatigue
- **Commit frequently** in submodules (every feature/fix)

### End of Day (5-10 minutes)

1. In **each submodule instance (2-5)**: Commit and push work
2. In **Instance 1**: Update submodule references
3. In **Instance 1**: Update work status notes
4. Close all instances

## Advanced: Instance Handoff Pattern

When work in one instance depends on another:

**Instance 3 (The Brain) completes a feature:**
```bash
git add .
git commit -m "Add async routing API for Sakana integration"
git push origin feature/async-routing

# Leave a note in the_brain/INTEGRATION_STATUS.md
echo "✅ Async routing API complete - ready for Sakana integration" >> INTEGRATION_STATUS.md
```

**Switch to Instance 2 (Sakana):**
```bash
cd the_brain
git pull origin feature/async-routing
cd ..

# Now use the new API
# ... implement integration ...
```

**Back to Instance 1 (Root):**
```bash
# Update submodule reference to new the_brain commit
cd the_brain
git checkout feature/async-routing
cd ..
git add the_brain
git commit -m "Update the_brain to feature/async-routing for Sakana integration"
```

## Tips for Solo 5-Instance Development

1. **Use Instance 1 as your scratchpad**: Keep notes, todo lists, architecture diagrams
2. **Name your windows clearly**: "VibeMind-Root", "VibeMind-Sakana", "VibeMind-Brain", etc.
3. **Color-code or number your IDE windows**: Use VS Code themes or window labels
4. **Take breaks between context switches**: 2-3 minutes to clear your head
5. **Don't work in all 5 simultaneously**: Focus on 2-3 at a time
6. **Use Instance 1 for big-picture thinking**: Step back and review architecture
7. **Commit early, commit often**: Each instance should commit independently

## Keyboard Shortcuts for Instance Switching

**Windows:**
- Alt+Tab: Switch between instances
- Win+1, Win+2, etc.: Direct instance selection (if pinned to taskbar)

**macOS:**
- Cmd+Tab: Switch between instances
- Cmd+`: Switch between windows of same app

**Linux:**
- Alt+Tab or Super+Tab: Switch between instances

## Instance Health Check

Run this in **Instance 1** periodically:

```bash
# Check git status in all submodules
git submodule foreach 'git status'

# Check for uncommitted work
git submodule foreach 'git diff --stat'

# Check current branches
git submodule foreach 'git branch --show-current'
```

## Emergency: Instance Lost/Crashed

All work is saved in submodule commits. If an instance crashes:

1. Reopen that submodule: `code <submodule-path>`
2. Check git status: `git status`
3. Recover uncommitted work if needed: `git stash` or check IDE auto-save
4. Continue working

## Example: Full-Stack Feature Implementation

**Feature: Voice-Activated Desktop Automation**

**Instance 5 (Electron):** Voice recognition and command parsing
↓
**Instance 2 (Sakana):** Command routing and orchestration
↓
**Instance 3 (The Brain):** Cognitive decision making
↓
**Instance 4 (MoireTracker):** Desktop automation execution
↓
**Instance 1 (Root):** Integration documentation and testing

Work on each layer in sequence, testing integration points as you go.

---

**Remember:** The goal is **organized parallelism**, not chaos. Use Instance 1 as your north star for coordination!
