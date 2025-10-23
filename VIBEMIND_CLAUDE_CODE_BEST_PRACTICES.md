# VibeMind: Claude Code Best Practices

**Adapted from Anthropic's official Claude Code best practices for VibeMind's 5-submodule integration repository with parallel VibeCoding workflow.**

---

## 1. Customize Your Setup for VibeMind

### a. CLAUDE.md Files - Multi-Level Strategy

VibeMind uses a **hierarchical CLAUDE.md structure** across the integration repo and all submodules:

**✅ Root Level** (`VibeMind/CLAUDE.md`):
- Integration repository overview
- Submodule management commands
- Cross-submodule integration patterns
- 5-instance parallel VibeCoding workflow
- Ecosystem-wide conventions

**✅ Submodule Level** (Each submodule has its own):
- `sakana-desktop-assistant/CLAUDE.md` - AI core, MCP agents, learning systems
- `the_brain/README.md` - ATM-R cognitive architecture (uses README as primary doc)
- `MoireTracker/CLAUDE.md` - C++ automation, Windows IPC
- `electron/CLAUDE.md` - Voice UI, React components
- `voice_dialog/CLAUDE.md` - Multi-agent orchestration

**📝 CLAUDE.md Content Guidelines:**

```markdown
# Common Commands
- git submodule update --init --recursive: Initialize all submodules
- npm run dev: Start development server (for electron)
- pytest: Run tests (for sakana/the_brain)

# Code Style
- Python: PEP 8, use type hints
- TypeScript: Prettier formatting, strict mode
- C++: Follow Google C++ Style Guide

# Workflow
- IMPORTANT: Each submodule commits independently
- YOU MUST update VibeMind root submodule references after submodule commits
- Prefer feature branches over direct main commits

# Integration Patterns
- The Brain → Sakana: Use Python path imports (see integration/README.md)
- Never duplicate code between submodules and VibeMind root
```

**🔑 Key Practices:**
- Use `#` key to add content to CLAUDE.md while coding
- Run CLAUDE.md through prompt improver periodically
- Add emphasis with "IMPORTANT" or "YOU MUST" for critical instructions
- Keep concise and human-readable

### b. Tune CLAUDE.md Files Iteratively

**❌ Common Mistake:** Adding extensive content without testing effectiveness

**✅ Best Practice:**
1. Add content incrementally
2. Test if Claude follows the instructions
3. Refine with emphasis keywords if needed
4. Remove content that doesn't improve results

**Example Evolution:**

```markdown
# Iteration 1
- Commit changes in submodules before updating root

# Iteration 2 (after Claude forgot)
- IMPORTANT: Always commit in submodules first, then update root

# Iteration 3 (after still forgetting)
- YOU MUST commit changes in each submodule BEFORE updating VibeMind root
- Failure to do this will lose work! Follow this order: 1) cd submodule 2) git commit 3) cd .. 4) git add submodule
```

### c. Curate Allowed Tools for 5-Instance Workflow

**Recommended Allowlist for VibeMind:**

```json
// .claude/settings.json (check into git for team sharing)
{
  "allowedTools": [
    "Edit",                          // File editing
    "Bash(git commit:*)",           // Git commits
    "Bash(git add:*)",              // Git staging
    "Bash(git push:*)",             // Git push
    "Bash(git submodule:*)",        // Submodule management
    "Bash(npm run:*)",              // NPM commands
    "Bash(pytest:*)",               // Python tests
    "Bash(docker:*)",               // Docker operations
    "Bash(python:*)",               // Python execution
    "Bash(timeout:*)"               // Long-running commands
  ]
}
```

**Per-Instance Settings:**

Each of the 5 instances can have different allowlists:
- **Instance 1 (Root)**: Git submodule operations, cross-cutting commands
- **Instances 2-5 (Submodules)**: Submodule-specific tools

### d. Install gh CLI for GitHub Integration

```bash
# Windows (with winget)
winget install GitHub.cli

# Unix/macOS
brew install gh

# Authenticate
gh auth login
```

**VibeMind Usage:**
- Create PRs from any instance: `commit` or `pr`
- Fix PR comments: "fix comments on my PR and push"
- Triage issues across all submodules

---

## 2. Give Claude More Tools

### a. Bash Tools for Submodule Management

**Document these in VibeMind/CLAUDE.md:**

```markdown
# VibeMind-Specific Commands

## Submodule Sync
- sync_all: git submodule foreach 'git pull origin main'
- check_all: git submodule foreach 'git status'

## Launch 5 Instances
- Windows: .\launch_vibecoding.ps1
- Unix: ./launch_vibecoding.sh

## Cross-Submodule Status
- git submodule foreach 'echo "=== $name ===" && git status --short'
```

### b. MCP Tools (Sakana Submodule Specific)

VibeMind's Sakana submodule has **18 MCP servers**. When working in Instance 2:

**Recommended .mcp.json** (in `sakana-desktop-assistant/`):

```json
{
  "mcpServers": {
    "github": {
      "command": "node",
      "args": ["src/MCP PLUGINS/servers/github/agent.py"]
    },
    "playwright": {
      "command": "node",
      "args": ["src/MCP PLUGINS/servers/playwright/agent.py"]
    }
  }
}
```

**Tip:** Use `--mcp-debug` flag when testing MCP configurations

### c. Custom Slash Commands for VibeMind

**Location:** `.claude/commands/` (check into git)

**Example: `/fixsubmodule` command:**

`.claude/commands/fixsubmodule.md`:
```markdown
Please fix the submodule issue for: $ARGUMENTS

Follow these steps:
1. Check submodule status with `git submodule status`
2. Understand which submodule is broken
3. Run `git submodule update --init --recursive $ARGUMENTS`
4. Verify the fix with `git submodule status`
5. Report success or failure clearly
```

**Example: `/integrate` command:**

`.claude/commands/integrate.md`:
```markdown
Integration workflow for VibeMind ecosystem.

Steps:
1. Check all submodule statuses
2. Pull latest from each submodule
3. Run integration tests (if any)
4. Update VibeMind root submodule references
5. Create integration commit with summary
6. Push to remote if tests pass

Remember: This coordinates across ALL 5 submodules!
```

---

## 3. Common Workflows for VibeMind

### a. Explore, Plan, Code, Commit (Integration Pattern)

**VibeMind-Specific Adaptation:**

**Step 1: Explore (Use subagents for complex cross-submodule queries)**
```
"Read the_brain/core/thalamo_pc_adaptive.py and
sakana-desktop-assistant/src/core/llm_interface.py.
Don't write code yet, just understand how they could integrate.
Use subagents to verify details if needed."
```

**Step 2: Plan (Use extended thinking)**
```
"Think hard about how to integrate The Brain's ATM-R into Sakana.
Create a plan in VibeMind/docs/INTEGRATION_PLAN.md.
Consider: Python path imports, dependency management, API surface."
```

**Step 3: Code**
```
"Implement your plan. Work in sakana-desktop-assistant first,
then update the_brain if needed. Verify as you go."
```

**Step 4: Commit (Multi-level)**
```
"Commit changes in the_brain, then sakana-desktop-assistant,
then update VibeMind root submodule references."
```

### b. Test-Driven Development (TDD) for Integration

**Pattern for Cross-Submodule Features:**

**Step 1: Write Integration Tests**
```
"Write tests in sakana-desktop-assistant/tests/test_brain_integration.py
that test calling The Brain's ATM-R. Ensure they fail initially.
Do NOT write implementation yet."
```

**Step 2: Confirm Tests Fail**
```
"Run pytest and confirm all tests fail as expected.
Do NOT write implementation code yet."
```

**Step 3: Commit Tests**
```
"Commit the failing tests in sakana-desktop-assistant."
```

**Step 4: Implement Until Tests Pass**
```
"Write code in sakana-desktop-assistant/src/core/cognitive_routing.py
to make tests pass. Keep iterating until all tests pass.
Use subagents to verify you're not overfitting to tests."
```

**Step 5: Commit Implementation**
```
"Commit the implementation and update VibeMind root."
```

### c. Multi-Instance Code + Review Pattern

**Perfect for VibeMind's 5-Instance Setup:**

**Instance 2 (Sakana):**
```
"Implement cognitive routing feature in Sakana"
```

**Instance 1 (Root) - After Instance 2 finishes:**
```
"/clear
Review the cognitive routing implementation in sakana-desktop-assistant.
Check for: code style, edge cases, integration risks, performance."
```

**Instance 2 (Sakana) - After review:**
```
"Read the review feedback in [review file].
Address all concerns and update the implementation."
```

### d. Git Operations via Claude

**VibeMind-Specific Git Workflow:**

**Common Tasks:**
- "Write a commit message for these Sakana changes"
- "Search git history: when was The Brain submodule added?"
- "Create a PR for this feature branch"
- "Rebase my branch on main"
- "Update all submodule references"

**Example Session:**
```
User: "commit and pr"

Claude:
1. Checks git status and diff
2. Reviews recent commit history for style
3. Creates commit: "feat: Add ATM-R cognitive routing to Sakana..."
4. Pushes branch
5. Creates PR with summary and test plan
6. Returns PR URL
```

### e. Submodule-Aware Q&A

**When Onboarding to VibeMind:**

```
"How does The Brain integrate with Sakana?"
→ Claude searches both submodules and integration docs

"Where is desktop automation implemented?"
→ Claude finds MoireTracker C++ code

"How do I run the full stack?"
→ Claude reads docker-compose.yml and submodule docs
```

---

## 4. Optimize Your Workflow

### a. Be Specific in Instructions

**❌ Poor (Vague about submodule context):**
```
"Add ATM-R support"
```

**✅ Good (Specific about integration):**
```
"In sakana-desktop-assistant/src/core/, create cognitive_routing.py
that imports The Brain's ATM-R via Python path manipulation
(see VibeMind/README.md integration pattern).
Use ThalamoPC6Adaptive for decision routing.
Write tests in tests/test_cognitive_routing.py.
Avoid mocks - test actual ATM-R integration."
```

**❌ Poor (Unclear which submodule):**
```
"Fix the memory leak"
```

**✅ Good (Explicit submodule and context):**
```
"In MoireTracker (C++ submodule), investigate the memory leak
in screen_capture.cpp around line 145.
Check for missing delete/free calls.
Review the Windows IPC shared memory management."
```

### b. Give Claude Images

**VibeMind UI Development Pattern:**

**When working in Instance 5 (Electron):**

1. Paste design mock image
2. Reference existing component:
   ```
   "Look at electron/src/components/ExistingWidget.tsx
   for the pattern. Implement this design following the same pattern.
   Take screenshots with Puppeteer to compare."
   ```
3. Iterate until match

**Keyboard shortcut (macOS):**
- `Cmd+Ctrl+Shift+4` → screenshot to clipboard
- `Ctrl+V` to paste (note: NOT Cmd+V in Claude Code!)

### c. Mention Files with Tab-Completion

**VibeMind Multi-Submodule Context:**

Use tab-completion for cross-submodule file references:

```
"Update sak[TAB] → sakana-desktop-assistant/src/core/assistant.py
to use the_[TAB] → the_brain/core/thalamo_pc_adaptive.py
following the pattern in Vib[TAB] → VibeMind/README.md"
```

### d. Give Claude URLs

**VibeMind Documentation Pattern:**

```
"Read https://github.com/Flissel/the_brain/blob/main/README.md
and implement the ATM-R integration in Sakana.

Also read the local docs/TAHLAMUS_INTEGRATION_PLAN.md."
```

**Allowlist domains:**
```
/allowed-tools
→ Add: WebFetchTool(domain:docs.anthropic.com)
→ Add: WebFetchTool(domain:github.com)
```

### e. Course Correct Early and Often

**VibeMind Multi-Instance Pattern:**

**Tools for Course Correction:**
1. **Ask for a plan first:** "Think about integration before coding"
2. **Press Escape:** Interrupt if going wrong direction
3. **Double-tap Escape:** Jump back and edit previous prompt
4. **Ask to undo:** "Undo those changes and try a different approach"

**Example:**
```
User: "Integrate The Brain with Sakana"

Claude: *starts editing files*

User: [PRESS ESCAPE]

User: "Stop! First create a plan in docs/integration-plan.md.
Don't write code until I approve the plan."

Claude: "Creating plan..."
```

### f. Use /clear to Keep Context Focused

**VibeMind Instance Management:**

**When to use /clear:**
- After completing a task in one submodule, before switching to another
- When context fills with irrelevant file contents
- Between different phases (explore → plan → code)
- When switching between instances (Instance 2 → Instance 3)

**Pattern:**
```
Instance 2: "Implement feature X in Sakana" → Done
Instance 2: /clear
Instance 2: "Now review what we just did for errors"
```

### g. Use Checklists for Multi-Submodule Tasks

**Example: Submodule Update Checklist**

**Step 1: Create Checklist**
```
"Create SUBMODULE_UPDATE_CHECKLIST.md with all 5 submodules:
- [ ] sakana-desktop-assistant
- [ ] the_brain
- [ ] MoireTracker
- [ ] electron
- [ ] voice_dialog"
```

**Step 2: Execute Systematically**
```
"Go through the checklist one by one.
For each submodule: pull latest, run tests, check for conflicts.
Check off each as you complete it."
```

### h. Pass Data Into Claude

**VibeMind Patterns:**

**Method 1: Copy-paste logs**
```
User: [pastes error log]
"This error is from the Sakana backend. Debug it."
```

**Method 2: Pipe data**
```bash
cat sakana-desktop-assistant/data/logs/session.log | claude
```

**Method 3: Tell Claude to fetch**
```
"Read the latest log file in sakana-desktop-assistant/data/logs/
and analyze the errors"
```

**Method 4: Use URLs**
```
"Fetch https://github.com/Flissel/the_brain/issues/42
and implement the requested feature"
```

---

## 5. VibeMind-Specific: 5-Instance Parallel Workflow

### a. Launch Pattern

**Windows:**
```powershell
.\launch_vibecoding.ps1
```

**Unix:**
```bash
./launch_vibecoding.sh
```

**Manual Launch:**
```bash
# Terminal 1
cd VibeMind && code .

# Terminal 2
cd VibeMind/sakana-desktop-assistant && code .

# Terminal 3
cd VibeMind/the_brain && code .

# Terminal 4
cd VibeMind/MoireTracker && code .

# Terminal 5
cd VibeMind/electron && code .
```

### b. Orchestration Pattern

**See:** [PARALLEL_VIBECODING.md](PARALLEL_VIBECODING.md)

**15-Minute Cycle:**
```
00:00 - Assign tasks to all 5 instances
00:15 - Quick scan, assign next tasks to finished instances
00:30 - Quick scan, assign next tasks
00:45 - Quick scan, assign next tasks
01:00 - Integration checkpoint (Instance 1 coordinates)
01:05 - Assign next round to all 5
```

**Task Broadcast Example:**
```
Instance 1: "Document the voice automation architecture"
Instance 2: "Implement voice command routing in Sakana"
Instance 3: "Add voice intent classification to ATM-R"
Instance 4: "Create C++ voice action handlers"
Instance 5: "Build voice input UI component"
```

### c. Instance Communication via Shared Files

**Pattern: Coordination Notes**

**Instance 1 creates:** `COORDINATION.md`
```markdown
## From Instance 3 → Instance 2
The Brain async API is ready at the_brain/core/async_routing.py
See example: the_brain/examples/async_demo.py

## From Instance 2 → Instance 5
Sakana WebSocket updated: ws://localhost:8765/voice-commands
Protocol: sakana-desktop-assistant/docs/websocket-api.md
```

**Other instances read this file for coordination info.**

### d. Git Worktrees for Parallel Development

**VibeMind Pattern:**

```bash
# Main checkout
cd VibeMind/sakana-desktop-assistant

# Create worktrees for parallel work
git worktree add ../sakana-feature-a feature-a
git worktree add ../sakana-feature-b feature-b
git worktree add ../sakana-bugfix bugfix/crash

# Launch Claude in each
cd ../sakana-feature-a && claude  # Instance 2a
cd ../sakana-feature-b && claude  # Instance 2b
cd ../sakana-bugfix && claude     # Instance 2c
```

**Cleanup when done:**
```bash
git worktree remove ../sakana-feature-a
```

---

## 6. VibeMind-Specific: Headless Mode & Automation

### a. Automated Submodule Updates

**Script: `scripts/update-all-submodules.sh`**

```bash
#!/bin/bash
for submodule in sakana-desktop-assistant the_brain MoireTracker electron voice_dialog; do
  echo "Updating $submodule..."
  claude -p "Pull latest in $submodule, run tests, report status" \
    --allowed-tools "Bash(git:*)" "Bash(pytest:*)" "Bash(npm:*)"
done
```

### b. Integration Testing Automation

**CI/CD Pattern:**

```yaml
# .github/workflows/integration-test.yml
- name: Test Sakana + The Brain Integration
  run: |
    claude -p "Run integration tests in sakana-desktop-assistant/tests/test_brain_integration.py. Report results." \
      --dangerously-skip-permissions \
      --output-format stream-json
```

### c. Issue Triage Across Submodules

**GitHub Actions trigger:**

```bash
claude -p "Triage this issue: $ISSUE_URL.
Determine which submodule it affects (Sakana, Brain, Moire, Electron, Voice).
Add appropriate labels and assign to correct repo." \
  --allowed-tools "Bash(gh:*)"
```

---

## 7. VibeMind Best Practices Summary

### ✅ DO:

1. **Use hierarchical CLAUDE.md files** (root + each submodule)
2. **Launch all 5 instances for parallel work** (you're orchestrating, not coding)
3. **Commit in submodules FIRST, then update VibeMind root**
4. **Use Instance 1 (Root) as coordination hub**
5. **Be explicit about which submodule** in every instruction
6. **Use /clear between submodule context switches**
7. **Document cross-submodule patterns** in VibeMind/docs/
8. **Use custom slash commands** for repeated workflows
9. **Set up allowed tools** per instance for safety
10. **Use extended thinking** ("think hard") for integration decisions

### ❌ DON'T:

1. **Don't duplicate code** between submodules and root
2. **Don't commit in VibeMind root before submodules**
3. **Don't try to code in all 5 instances yourself** (orchestrate, don't code)
4. **Don't skip the planning phase** for cross-submodule features
5. **Don't use vague instructions** without specifying submodule
6. **Don't forget to update submodule references** in root
7. **Don't mix changes from multiple submodules** in one commit
8. **Don't work on overlapping files** across instances (causes conflicts)

---

## 8. Quick Reference Card

### Common VibeMind Commands

```bash
# Submodule Management
git submodule update --init --recursive  # Initialize all
git submodule foreach 'git status'       # Check all statuses
git submodule foreach 'git pull origin main'  # Update all

# Launch 5 Instances
.\launch_vibecoding.ps1     # Windows
./launch_vibecoding.sh      # Unix

# Cross-Submodule Search
git submodule foreach 'echo "=== $name ===" && git log -1'

# Commit Pattern
cd sakana-desktop-assistant && git commit && git push
cd .. && git add sakana-desktop-assistant && git commit
```

### Extended Thinking Triggers

- `"think"` - Basic extended thinking
- `"think hard"` - More thinking budget
- `"think harder"` - Even more budget
- `"ultrathink"` - Maximum thinking budget

**Use for:**
- Cross-submodule integration decisions
- Architecture planning
- Complex debugging

### Keyboard Shortcuts

- `Shift+Tab` - Toggle auto-accept mode
- `Escape` - Interrupt Claude (preserves context)
- `Escape Escape` - Jump back in history, edit prompt
- `#` - Add instruction to CLAUDE.md
- `Cmd+Ctrl+Shift+4` (macOS) - Screenshot to clipboard
- `Ctrl+V` - Paste into Claude (not Cmd+V)

---

## 9. Learning Resources

- **Official Claude Code Docs**: https://claude.ai/code
- **VibeMind Architecture**: [docs/FULL_ECOSYSTEM_ARCHITECTURE.md](docs/FULL_ECOSYSTEM_ARCHITECTURE.md)
- **Parallel VibeCoding**: [PARALLEL_VIBECODING.md](PARALLEL_VIBECODING.md)
- **Integration Patterns**: [README.md](README.md)
- **Tahlamus Integration**: [docs/TAHLAMUS_INTEGRATION_PLAN.md](docs/TAHLAMUS_INTEGRATION_PLAN.md)

---

**Adapted from:** "Claude Code: Best practices for agentic coding" by Anthropic (April 18, 2025)

**VibeMind-Specific Additions:** 5-instance orchestration, submodule management, integration patterns, cross-repository coordination

🤖 **Remember:** With 5 Claude instances, you're not a developer trying to code in 5 windows - you're a conductor orchestrating 5 expert AI developers! 🎼
