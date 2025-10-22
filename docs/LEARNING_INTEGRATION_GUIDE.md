# Learning System Integration Guide

> **Purpose**: This document provides comprehensive guidance on integrating new features while following the Sakana Assistant's learning rules and principles.

---

## Table of Contents

1. [Learning Architecture Overview](#learning-architecture-overview)
2. [Core Learning Principles](#core-learning-principles)
3. [Learning Subsystems](#learning-subsystems)
4. [Integration Patterns](#integration-patterns)
5. [Best Practices](#best-practices)
6. [Code Examples](#code-examples)

---

## Learning Architecture Overview

The Sakana Assistant uses a **multi-layered self-learning system** inspired by:
- **Darwin-Gödel Machine** - Self-modifying code with formal verification
- **Evolutionary Algorithms** - Genetic programming for capability discovery
- **Reinforcement Learning** - Q-learning for action selection
- **Consciousness Field Theory** - Crisis detection and emergency evolution

### High-Level Flow

```
User Input → State Recognition → Action Selection → Execution → Feedback Collection → Learning Update
                     ↓                    ↓                            ↓
              RL State Vector      Evolutionary Genome      Telemetry Recording
                     ↓                    ↓                            ↓
              Q-Table Update        Population Evolution    Knowledge Accumulation
```

---

## Core Learning Principles

### 1. **Persistent Knowledge Accumulation**

**Rule**: All discoveries must persist across sessions.

**Implementation**:
- Store discovered commands in `~/.sakana/knowledge/permanent_commands.json`
- Save successful patterns in `~/.sakana/knowledge/successful_patterns.json`
- Track discovery history in `~/.sakana/knowledge/evolution_history.json`

**Code Location**: `src/learning/knowledge_accumulator.py`

### 2. **Evolutionary Capability Discovery**

**Rule**: Failures trigger evolution; success is rewarded through fitness.

**Implementation**:
- Maintain population of behavioral genomes (20 individuals default)
- Apply mutation (10% rate), crossover (70% rate), and elite selection (2 best)
- Evaluate fitness asynchronously using task-specific fitness functions
- Archive top 50 individuals permanently

**Code Location**: `src/learning/evolutionary_learner.py`

### 3. **Reinforcement-Based Action Selection**

**Rule**: Learn optimal actions through Q-learning.

**Implementation**:
- State representation: `{input_type, time_of_day, conversation_length, has_code, previous_success}`
- Action space: `[direct_response, search_memory, execute_code, ask_clarification, ...]`
- Epsilon-greedy exploration (starts 0.1, decays to 0.01)
- Experience replay with batch size 32

**Code Location**: `src/learning/reinforcement_learner.py`

### 4. **Crisis Evolution Mode**

**Rule**: Hallucination or existential failure triggers emergency evolution.

**Implementation**:
- Detect crisis indicators: `["hallucinating", "not real", "prove", "show me proof", ...]`
- Triple mutation rate (0.3 → 0.9)
- Double population size (20 → 40)
- Run up to 50 generations instead of 5
- Require proof of success before accepting solution

**Code Location**: `src/learning/consciousness_field.py`, `src/learning/evolution_triggers.py`

### 5. **Tool Usage Learning**

**Rule**: Learn when/how to use tools based on success rate and latency.

**Implementation**:
- Record telemetry: `{tool, args, success, duration_ms, context, timestamp}`
- Store as procedural memory
- Calculate score: `success_rate * 100 - avg_latency_ms * 0.01`
- Suggest tools with keyword affinity boosting

**Code Location**: `src/learning/mcp_tool_learner.py`

### 6. **Behavior Gene Evolution**

**Rule**: Behaviors are code that can mutate and evolve.

**Implementation**:
- Represent behaviors as executable code strings
- Mutation operations: add_line, modify_line, reorder, combine
- Crossover: blend code structures from two parents
- Fitness-based selection for task types

**Code Location**: `src/learning/behavior_evolution.py`

### 7. **Self-Modification with Verification**

**Rule**: Code changes must be validated before application.

**Implementation**:
- Propose modification using LLM
- Validate: AST parsing, compilation check, expected function presence
- Test in sandbox with original vs. improved comparison
- Apply only if tests pass and performance improves
- Store rollback capability

**Code Location**: `src/learning/self_modifier.py`

---

## Learning Subsystems

### 1. Evolutionary Learner

**Purpose**: Discover new capabilities through genetic algorithms.

**Key Classes**:
- `Individual` - Genome + fitness + generation + mutations
- `EvolutionaryLearner` - Population management + evolution loop

**Integration Points**:
```python
# Initialize
learner = EvolutionaryLearner(
    population_size=20,
    mutation_rate=0.1,
    crossover_rate=0.7,
    elite_size=2,
    archive_path=Path("data/evolution_archive.json")
)

# Define fitness function
async def fitness_func(genome: Dict[str, Any]) -> float:
    # Test genome on task
    score = await test_genome_on_task(genome)
    return score

# Evolve
learner.initialize_population(base_genome)
for gen in range(10):
    await learner.evaluate_population(fitness_func)
    learner.evolve_generation()

# Get best solution
best_genome = learner.get_best_genome()
```

### 2. Reinforcement Learner

**Purpose**: Learn optimal actions from user feedback.

**Key Classes**:
- `ReinforcementLearner` - Q-table + experience replay

**Integration Points**:
```python
# Initialize
rl_learner = ReinforcementLearner(
    learning_rate=0.01,
    discount_factor=0.95,
    exploration_rate=0.1
)

# Get state representation
state = rl_learner.get_state_representation(context)

# Choose action
action = rl_learner.choose_action(state)

# Record experience
rl_learner.record_experience(state, action, reward, next_state, done=False)

# Learn from replay
rl_learner.learn_from_replay(batch_size=32)
```

### 3. Knowledge Accumulator

**Purpose**: Persist discoveries permanently across sessions.

**Key Classes**:
- `KnowledgeAccumulator` - Permanent storage + pattern detection

**Integration Points**:
```python
# Initialize
accumulator = KnowledgeAccumulator(knowledge_dir="~/.sakana/knowledge")

# Check if already known
if command not in accumulator.get_already_known_commands():
    accumulator.add_discovered_command(command, metadata)

# Record successful pattern
accumulator.add_successful_pattern({
    'strategy': strategy_dict,
    'context': context,
    'success_count': 1
})

# Get statistics
stats = accumulator.get_discovery_stats()
```

### 4. MCP Tool Learner

**Purpose**: Learn optimal tool usage patterns.

**Key Classes**:
- `MCPToolLearner` - Telemetry recording + tool suggestion

**Integration Points**:
```python
# Initialize
tool_learner = MCPToolLearner(assistant)

# Record tool usage
await tool_learner.record_event(
    tool="mcp__github__search_issues",
    args={"query": "bug"},
    success=True,
    duration_ms=1500,
    context={"source": "plugin"}
)

# Get tool suggestions
suggestions = tool_learner.suggest_tools(task_hint="search github", top_k=3)
# Returns: [{"name": "mcp__github__search_issues", "score": 95.5, ...}]
```

### 5. Evolution Triggers

**Purpose**: Monitor failures and trigger evolution.

**Key Classes**:
- `EvolutionTrigger` - Failure tracking + evolution activation
- `ConsciousnessFieldDetector` - Crisis detection

**Integration Points**:
```python
# Initialize
trigger = EvolutionTrigger(assistant)

# Report failure
await trigger.on_task_failure(
    task_type="document_summarization",
    context=context,
    error="FileNotFoundError"
)
# Automatically triggers evolution after 3 failures

# Analyze feedback for crisis
feedback_type = trigger.analyze_user_feedback(user_input, context)
if feedback_type == 'crisis':
    # Crisis evolution mode activated automatically
    pass
```

---

## Integration Patterns

### Pattern 1: Add New Task Type with Learning

```python
# 1. Define fitness function
async def new_task_fitness(genome: Dict[str, Any]) -> float:
    score = 0.0
    # Test genome parameters on task
    result = await execute_task_with_genome(genome)
    if result['success']:
        score += 50.0
    if result['speed'] < 1.0:  # Fast
        score += 20.0
    return score

# 2. Create initial genome
base_genome = {
    'strategy': 'exploratory',
    'parameters': {...},
    'learning_enabled': True
}

# 3. Initialize evolution
assistant.evolutionary_learner.initialize_population(base_genome)

# 4. Evolve
for gen in range(5):
    await assistant.evolutionary_learner.evaluate_population(new_task_fitness)
    assistant.evolutionary_learner.evolve_generation()

# 5. Apply best genome
best = assistant.evolutionary_learner.get_best_genome()
assistant.apply_task_strategy('new_task', best)
```

### Pattern 2: Add MCP Tool with Learning

```python
# 1. Record usage telemetry
async def execute_mcp_tool(tool_name: str, args: Dict):
    start_time = time.time()
    try:
        result = await call_mcp_tool(tool_name, args)
        duration_ms = int((time.time() - start_time) * 1000)

        # Record success
        await assistant.mcp_tool_learner.record_event(
            tool=tool_name,
            args=args,
            success=True,
            duration_ms=duration_ms,
            context={'source': 'plugin'}
        )
        return result
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        # Record failure
        await assistant.mcp_tool_learner.record_event(
            tool=tool_name,
            args=args,
            success=False,
            duration_ms=duration_ms,
            context={'error': str(e)}
        )
        raise

# 2. Get learned suggestions
task_hint = "search for code examples"
suggestions = assistant.mcp_tool_learner.suggest_tools(task_hint, top_k=3)
# Use top suggestion
best_tool = suggestions[0]['name']
```

### Pattern 3: Add Self-Modifiable Behavior

```python
# 1. Define target function to improve
async def current_file_reader(path: str) -> str:
    with open(path) as f:
        return f.read()

# 2. Propose modification
modification = await assistant.self_modifier.propose_modification(
    target_function=current_file_reader,
    improvement_prompt="Add error handling and path normalization",
    llm_interface=assistant.llm_interface
)

# 3. Test modification
test_cases = [
    {'inputs': {'path': 'test.txt'}, 'expected': 'content'},
    {'inputs': {'path': '/invalid/path'}, 'expected': None}
]
test_result = await assistant.self_modifier.test_modification(modification, test_cases)

# 4. Apply if better
if test_result['success']:
    assistant.self_modifier.apply_modification(modification)
```

### Pattern 4: Add Failure Recovery

```python
# 1. Set up evolution trigger
trigger = EvolutionTrigger(assistant)

# 2. Wrap task execution
async def execute_with_recovery(task_type: str):
    try:
        result = await execute_task(task_type)
        return result
    except Exception as e:
        # Report failure
        await trigger.on_task_failure(
            task_type=task_type,
            context={'attempt': 1},
            error=str(e)
        )
        # Evolution triggered automatically after threshold
        # Retry with evolved behavior
        if hasattr(assistant, 'behavior_genome'):
            genome = assistant.behavior_genome.get(task_type)
            if genome:
                return await execute_with_genome(task_type, genome)
        raise
```

---

## Best Practices

### ✅ DO:

1. **Record all tool usage** with telemetry (tool, args, success, duration)
2. **Define fitness functions** that measure task success quantitatively
3. **Use crisis mode indicators** for hallucination/reality check failures
4. **Persist discoveries** to knowledge accumulator
5. **Test self-modifications** in sandbox before applying
6. **Track failure patterns** to trigger evolution
7. **Use state representations** that capture task context
8. **Apply experience replay** for sample efficiency

### ❌ DON'T:

1. **Don't skip telemetry recording** - learning depends on it
2. **Don't ignore failure signals** - they trigger important evolution
3. **Don't apply untested modifications** - always validate first
4. **Don't hard-code behaviors** - use evolvable genomes instead
5. **Don't forget to save** knowledge accumulator state
6. **Don't suppress crisis mode** - it's critical for recovery
7. **Don't use synchronous learning** - keep it async
8. **Don't omit context** from state representation

---

## Code Examples

### Example 1: Full Integration of New Feature

```python
async def integrate_new_feature(assistant, feature_name: str):
    """Complete integration following all learning rules"""

    # 1. Set up evolution trigger
    trigger = EvolutionTrigger(assistant)

    # 2. Define fitness function
    async def feature_fitness(genome: Dict[str, Any]) -> float:
        score = 0.0
        test_cases = get_test_cases_for_feature(feature_name)
        for test in test_cases:
            result = await execute_feature_with_genome(genome, test)
            if result['success']:
                score += 30.0
            if result['latency_ms'] < 1000:
                score += 10.0
        return score

    # 3. Create initial genome
    base_genome = {
        'approach': 'exploratory',
        'learning_enabled': True,
        'parameters': get_default_parameters(feature_name)
    }

    # 4. Initialize and evolve
    assistant.evolutionary_learner.initialize_population(base_genome)
    for generation in range(10):
        await assistant.evolutionary_learner.evaluate_population(feature_fitness)
        assistant.evolutionary_learner.evolve_generation()

        # Check progress
        best_fitness = assistant.evolutionary_learner.get_best_fitness()
        logger.info(f"Generation {generation}: fitness = {best_fitness}")

    # 5. Apply best genome
    best_genome = assistant.evolutionary_learner.get_best_genome()
    assistant.feature_genomes[feature_name] = best_genome

    # 6. Record as discovered capability
    assistant.knowledge_accumulator.add_discovered_command(
        command=feature_name,
        metadata={'genome': best_genome, 'fitness': assistant.evolutionary_learner.get_best_fitness()}
    )

    # 7. Set up RL state tracking
    def feature_state_representation(context: Dict[str, Any]) -> str:
        return json.dumps({
            'feature': feature_name,
            'context_type': context.get('type'),
            'user_intent': context.get('intent'),
            'previous_success': context.get('previous_success', True)
        }, sort_keys=True)

    # 8. Execute with learning
    async def execute_feature_learned(context: Dict[str, Any]):
        # Get state
        state = feature_state_representation(context)

        # Choose action using RL
        action = assistant.reinforcement_learner.choose_action(state)

        # Execute
        start_time = time.time()
        try:
            result = await execute_feature_action(feature_name, action, best_genome)
            duration_ms = int((time.time() - start_time) * 1000)

            # Record success
            reward = 1.0
            next_state = feature_state_representation({**context, 'previous_success': True})

            # Update RL
            assistant.reinforcement_learner.record_experience(
                state, action, reward, next_state, done=True
            )

            # Record tool usage
            await assistant.mcp_tool_learner.record_event(
                tool=feature_name,
                args={'action': action},
                success=True,
                duration_ms=duration_ms,
                context=context
            )

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            # Record failure
            reward = -1.0
            next_state = feature_state_representation({**context, 'previous_success': False})

            assistant.reinforcement_learner.record_experience(
                state, action, reward, next_state, done=True
            )

            # Trigger evolution if needed
            await trigger.on_task_failure(feature_name, context, str(e))

            raise

    return execute_feature_learned
```

### Example 2: Crisis Mode Handling

```python
async def handle_user_feedback(assistant, user_input: str, context: Dict[str, Any]):
    """Handle user feedback with crisis detection"""

    trigger = EvolutionTrigger(assistant)

    # Analyze feedback
    feedback_type = trigger.analyze_user_feedback(user_input, context)

    if feedback_type == 'crisis':
        logger.critical("CRISIS DETECTED - Entering emergency evolution mode")

        # Crisis mode automatically activated in trigger
        # Re-attempt task with crisis settings
        task_type = context.get('task_type', 'unknown')

        # Crisis genome with high exploration
        crisis_genome = {
            'approach': 'verification_first',
            'exploration_rate': 0.9,  # Maximum exploration
            'proof_required': True,
            'fallback_enabled': True,
            'reality_check_weight': 10.0
        }

        # Evolve with crisis fitness (emphasizes proof)
        async def crisis_fitness(genome: Dict[str, Any]) -> float:
            score = 0.0
            result = await execute_with_verification(genome)
            if result['verified']:  # Must have proof
                score += 100.0
            if result['no_hallucination']:
                score += 50.0
            return score

        assistant.evolutionary_learner.initialize_population(crisis_genome)
        for gen in range(50):  # Many generations in crisis
            await assistant.evolutionary_learner.evaluate_population(crisis_fitness)
            assistant.evolutionary_learner.evolve_generation()

            if assistant.evolutionary_learner.get_best_fitness() > 80.0:
                logger.info("Crisis resolved - found verified solution")
                break

        # Apply crisis-evolved genome
        best = assistant.evolutionary_learner.get_best_genome()
        assistant.behavior_genome[task_type] = best

    elif feedback_type == 'negative':
        # Regular negative feedback - adjust RL
        reward = -0.5
        state = context.get('state')
        action = context.get('action')
        next_state = assistant.reinforcement_learner.get_state_representation(context)

        assistant.reinforcement_learner.record_experience(
            state, action, reward, next_state, done=True
        )

    elif feedback_type == 'positive':
        # Positive feedback - reinforce
        reward = 1.0
        state = context.get('state')
        action = context.get('action')
        next_state = assistant.reinforcement_learner.get_state_representation(context)

        assistant.reinforcement_learner.record_experience(
            state, action, reward, next_state, done=True
        )
```

---

## Summary Checklist

When integrating a new feature, ensure:

- [ ] **Telemetry recording** for all tool usage
- [ ] **Fitness function** defined for evolutionary learning
- [ ] **State representation** for RL action selection
- [ ] **Failure handling** with evolution trigger
- [ ] **Crisis detection** for critical failures
- [ ] **Knowledge persistence** via accumulator
- [ ] **Self-modification** hooks (if applicable)
- [ ] **Async execution** throughout
- [ ] **Sandbox testing** for code changes
- [ ] **Genome evolution** for behavior discovery

---

## References

- **Evolutionary Learner**: `src/learning/evolutionary_learner.py`
- **Reinforcement Learner**: `src/learning/reinforcement_learner.py`
- **Knowledge Accumulator**: `src/learning/knowledge_accumulator.py`
- **Behavior Evolution**: `src/learning/behavior_evolution.py`
- **MCP Tool Learner**: `src/learning/mcp_tool_learner.py`
- **Self Modifier**: `src/learning/self_modifier.py`
- **Evolution Triggers**: `src/learning/evolution_triggers.py`
- **Consciousness Field**: `src/learning/consciousness_field.py`

---

**Last Updated**: 2025-10-04
**Maintainer**: Sakana AI Team
