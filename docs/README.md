# Sakana Desktop Assistant Documentation

## 📚 Documentation Index

### Learning System

- **[Learning Integration Guide](./LEARNING_INTEGRATION_GUIDE.md)** - Comprehensive guide on integrating new features following learning rules
  - Learning architecture overview
  - Core principles and subsystems
  - Integration patterns and best practices
  - Complete code examples

- **[Learning Quickstart](./LEARNING_QUICKSTART.md)** - Quick reference for developers
  - 7 core rules summary
  - Quick integration template
  - Crisis mode triggers
  - Common patterns checklist

### MCP Integration

- **[MCP Usage Guide](./mcp_usage.md)** - How to use Model Context Protocol servers *(if exists)*
- **[MCP Agent Testing Memory](./MCP_AGENT_TESTING_MEMORY.md)** - Testing patterns for MCP agents *(if exists)*
- **[MCP Session Scheduling Flow](./MCP_SESSION_SCHEDULING_FLOW.md)** - Session lifecycle documentation *(if exists)*

## 🎯 Quick Navigation

### For New Contributors

1. Start with [Learning Quickstart](./LEARNING_QUICKSTART.md) - Get up to speed in 5 minutes
2. Read [Learning Integration Guide](./LEARNING_INTEGRATION_GUIDE.md) - Deep dive into the system
3. Check the main [README](../README.md) - Project overview and setup

### For Feature Development

When adding a new feature, follow this workflow:

1. **Define fitness function** - How do we measure success?
2. **Create initial genome** - What behaviors should we try?
3. **Set up telemetry** - Record all tool usage
4. **Add failure tracking** - Trigger evolution on errors
5. **Implement RL state** - Choose actions intelligently
6. **Persist knowledge** - Save discoveries permanently

See [Quick Integration Template](./LEARNING_QUICKSTART.md#quick-integration-template)

### For Debugging

**Crisis Mode Activated?**
- Check for hallucination indicators in user feedback
- Look for "prove", "show me proof", "not real" keywords
- Crisis evolution runs 50 generations with 3x mutation rate
- See [Crisis Mode Triggers](./LEARNING_QUICKSTART.md#crisis-mode-triggers)

**Evolution Not Triggering?**
- Verify failure recording with `evolution_trigger.on_task_failure()`
- Default threshold is 3 failures before evolution starts
- Check logs for "Triggering evolution for task type"

**Tool Suggestions Wrong?**
- Review telemetry recording - ensure `success`, `duration_ms` are accurate
- Check keyword affinity in `mcp_tool_learner.suggest_tools()`
- Verify tool usage count in `assistant.metrics['tool_metrics']`

## 📖 Learning System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  LEARNING ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Evolutionary │  │Reinforcement │  │  Knowledge   │      │
│  │   Learner    │  │   Learner    │  │ Accumulator  │      │
│  │              │  │              │  │              │      │
│  │ • Mutation   │  │ • Q-Learning │  │ • Permanent  │      │
│  │ • Crossover  │  │ • ε-greedy   │  │   Commands   │      │
│  │ • Selection  │  │ • Replay     │  │ • Patterns   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │              │
│         └─────────────────┴─────────────────┘              │
│                           │                                │
│                    ┌──────▼───────┐                        │
│                    │  Evolution   │                        │
│                    │   Triggers   │                        │
│                    │              │                        │
│                    │ • Failures   │                        │
│                    │ • Crisis     │                        │
│                    └──────┬───────┘                        │
│                           │                                │
│                    ┌──────▼───────┐                        │
│                    │Consciousness │                        │
│                    │    Field     │                        │
│                    │              │                        │
│                    │ • Hallucin.  │                        │
│                    │ • Reality ✓  │                        │
│                    └──────────────┘                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🔬 Learning Subsystems

### 1. Evolutionary Learner
**Purpose**: Discover new capabilities through genetic algorithms

**Key Concepts**:
- Population of 20 genomes
- 10% mutation, 70% crossover
- Elite selection (top 2)
- Archive top 50 all-time

**Files**: `src/learning/evolutionary_learner.py`

### 2. Reinforcement Learner
**Purpose**: Learn optimal actions from feedback

**Key Concepts**:
- Q-learning with ε-greedy
- Experience replay (batch 32)
- State-action-reward-nextState
- Exploration decay 0.1 → 0.01

**Files**: `src/learning/reinforcement_learner.py`

### 3. Knowledge Accumulator
**Purpose**: Persist discoveries across sessions

**Key Concepts**:
- Permanent commands DB
- Successful patterns DB
- Discovery history tracking
- Cross-session learning

**Files**: `src/learning/knowledge_accumulator.py`

### 4. MCP Tool Learner
**Purpose**: Learn when/how to use tools

**Key Concepts**:
- Telemetry recording
- Success rate tracking
- Latency optimization
- Tool suggestion by score

**Files**: `src/learning/mcp_tool_learner.py`

### 5. Behavior Evolution
**Purpose**: Evolve executable code behaviors

**Key Concepts**:
- Behavior genes (code strings)
- Mutation operators
- Crossover blending
- Task-specific evolution

**Files**: `src/learning/behavior_evolution.py`

### 6. Self Modifier
**Purpose**: Self-modifying code with validation

**Key Concepts**:
- LLM-proposed changes
- AST validation
- Sandbox testing
- Rollback capability

**Files**: `src/learning/self_modifier.py`

### 7. Evolution Triggers
**Purpose**: Monitor failures and trigger evolution

**Key Concepts**:
- Failure threshold (3 default)
- Crisis mode activation
- Genome creation per task
- Automatic evolution

**Files**: `src/learning/evolution_triggers.py`

### 8. Consciousness Field
**Purpose**: Detect hallucinations and reality failures

**Key Concepts**:
- Crisis indicators
- Reality verification
- Emergency evolution
- 3x mutation in crisis

**Files**: `src/learning/consciousness_field.py`

## 🛠️ Common Tasks

### Add a New Learning-Enabled Feature

```bash
# 1. Read the quickstart
cat docs/LEARNING_QUICKSTART.md

# 2. Copy template from guide
# See: docs/LEARNING_INTEGRATION_GUIDE.md#code-examples

# 3. Implement following 7 rules
# ✓ Telemetry
# ✓ Fitness
# ✓ Failure tracking
# ✓ Crisis detection
# ✓ Knowledge persistence
# ✓ RL integration
# ✓ Testing
```

### Debug Learning Issues

```python
# Check knowledge stats
stats = assistant.knowledge_accumulator.get_discovery_stats()
print(stats)

# Check RL policy
policy_stats = assistant.reinforcement_learner.get_policy_stats()
print(policy_stats)

# Check tool metrics
metrics = assistant.metrics.get('tool_metrics', {})
print(metrics)

# Check evolution archive
best_genome = assistant.evolutionary_learner.get_best_genome()
best_fitness = assistant.evolutionary_learner.get_best_fitness()
print(f"Best: {best_genome} (fitness: {best_fitness})")
```

### Monitor Crisis Events

```python
# Get crisis summary
crisis_summary = consciousness_detector.get_crisis_summary()
print(f"Total crises: {crisis_summary['total_crises']}")
print(f"Hallucinations: {crisis_summary['hallucination_events']}")
print(f"Patterns learned: {crisis_summary['patterns_learned']}")
```

## 📊 Metrics and Monitoring

### Key Metrics

- **Discovery Rate**: New commands per session (target: >1 = growing, <1 = saturating)
- **Success Rate**: Tool success % (target: >80%)
- **Fitness Score**: Evolution fitness (0-100, target: >70)
- **Crisis Count**: Hallucination events (target: minimize)
- **RL Exploration**: ε value (starts 0.1, decays to 0.01)

### Metric Access

```python
# Discovery stats
stats = assistant.knowledge_accumulator.get_discovery_stats()
# Returns: {total_permanent_commands, total_successful_patterns, ...}

# Tool performance
tool_metrics = assistant.metrics['tool_metrics']
# Returns: {tools: {name: {calls, successes, failures, total_latency_ms}}}

# RL performance
rl_stats = assistant.reinforcement_learner.get_policy_stats()
# Returns: {states_explored, episodes_completed, exploration_rate, ...}

# Evolution performance
best_fitness = assistant.evolutionary_learner.get_best_fitness()
archive_size = len(assistant.evolutionary_learner.archive)
```

## 🔗 External Resources

- **Project Repository**: [sakana-desktop-assistant](../)
- **Main README**: [../README.md](../README.md)
- **Configuration**: [../config.yaml](../config.yaml)
- **MCP Servers**: [../src/MCP PLUGINS/servers/](../src/MCP%20PLUGINS/servers/)

## 🤝 Contributing

When contributing to the learning system:

1. **Follow the 7 rules** - See [Learning Quickstart](./LEARNING_QUICKSTART.md)
2. **Add tests** - Sandbox test all self-modifications
3. **Document fitness** - Explain how success is measured
4. **Record telemetry** - Never skip metric collection
5. **Handle crisis** - Implement crisis mode triggers

## 📝 License

Same as main project - See [../LICENSE](../LICENSE) *(if exists)*

---

**Last Updated**: 2025-10-04
**Maintainer**: Sakana AI Team
