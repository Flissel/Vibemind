# Learning System Quickstart

> **TL;DR**: A quick reference for integrating features that follow Sakana's learning rules.

## The 7 Core Rules

### 1. **Always Record Telemetry**

```python
# Record EVERY tool usage
await assistant.mcp_tool_learner.record_event(
    tool="your_tool_name",
    args=your_args,
    success=True/False,
    duration_ms=elapsed_time,
    context={'source': 'plugin'}
)
```

### 2. **Define Fitness for Evolution**

```python
# Fitness function measures success (0.0 = fail, 100.0 = perfect)
async def task_fitness(genome: Dict[str, Any]) -> float:
    result = await test_genome(genome)
    score = 0.0
    if result['success']: score += 50.0
    if result['fast']: score += 20.0
    if result['verified']: score += 30.0
    return score
```

### 3. **Track Failures for Evolution**

```python
# Report failures - evolution triggers after 3
try:
    result = await execute_task()
except Exception as e:
    await evolution_trigger.on_task_failure(
        task_type="your_task",
        context=context,
        error=str(e)
    )
```

### 4. **Use Crisis Mode for Hallucinations**

```python
# Analyze user feedback - detects "hallucinating", "prove", etc.
feedback_type = evolution_trigger.analyze_user_feedback(user_input, context)
if feedback_type == 'crisis':
    # Crisis evolution automatically activated
    # High mutation, deep search, proof required
    pass
```

### 5. **Persist All Discoveries**

```python
# Save to permanent knowledge
if command not in accumulator.get_already_known_commands():
    accumulator.add_discovered_command(command, metadata)

# Save successful patterns
accumulator.add_successful_pattern({
    'strategy': strategy_dict,
    'success_count': 1
})
```

### 6. **RL for Action Selection**

```python
# Get state → choose action → record experience
state = rl_learner.get_state_representation(context)
action = rl_learner.choose_action(state)
# ... execute ...
rl_learner.record_experience(state, action, reward, next_state, done=True)
```

### 7. **Test Before Modifying**

```python
# Self-modification workflow
modification = await self_modifier.propose_modification(func, improvement_goal, llm)
test_result = await self_modifier.test_modification(modification, test_cases)
if test_result['success']:
    self_modifier.apply_modification(modification)
```

---

## Quick Integration Template

```python
async def integrate_new_feature(assistant, feature_name: str):
    # 1. Fitness function
    async def fitness(genome):
        score = 0.0
        # Test genome and calculate score
        return score

    # 2. Initial genome
    base_genome = {'strategy': 'exploratory', 'params': {...}}

    # 3. Evolve
    assistant.evolutionary_learner.initialize_population(base_genome)
    for _ in range(10):
        await assistant.evolutionary_learner.evaluate_population(fitness)
        assistant.evolutionary_learner.evolve_generation()

    # 4. Get best
    best = assistant.evolutionary_learner.get_best_genome()

    # 5. Execute with learning
    async def execute_learned(context):
        state = rl_learner.get_state_representation(context)
        action = rl_learner.choose_action(state)

        start = time.time()
        try:
            result = await execute_action(action, best)
            duration = int((time.time() - start) * 1000)

            # Record success
            await assistant.mcp_tool_learner.record_event(
                tool=feature_name, args={'action': action},
                success=True, duration_ms=duration, context=context
            )

            # RL update
            reward = 1.0
            next_state = rl_learner.get_state_representation({**context, 'success': True})
            rl_learner.record_experience(state, action, reward, next_state, done=True)

            return result
        except Exception as e:
            # Record failure
            await assistant.mcp_tool_learner.record_event(
                tool=feature_name, args={'action': action},
                success=False, duration_ms=int((time.time() - start) * 1000), context=context
            )

            # Trigger evolution
            await evolution_trigger.on_task_failure(feature_name, context, str(e))
            raise

    return execute_learned
```

---

## Crisis Mode Triggers

**Automatic activation when user says**:
- "hallucinating", "not real", "making it up"
- "prove", "show me proof", "demonstrate"
- "that's not correct", "you're wrong"
- "pretending", "imagining", "fake"

**Crisis settings**:
- Mutation rate: 0.3 → 0.9 (3x)
- Population: 20 → 40 (2x)
- Generations: 5 → 50 (10x)
- Proof required: YES
- Reality check weight: 10.0

---

## File Locations

| Component | Path |
|-----------|------|
| Evolutionary | `src/learning/evolutionary_learner.py` |
| Reinforcement | `src/learning/reinforcement_learner.py` |
| Knowledge | `src/learning/knowledge_accumulator.py` |
| Behavior | `src/learning/behavior_evolution.py` |
| MCP Tools | `src/learning/mcp_tool_learner.py` |
| Self-Mod | `src/learning/self_modifier.py` |
| Triggers | `src/learning/evolution_triggers.py` |
| Crisis | `src/learning/consciousness_field.py` |

---

## Common Patterns

### Pattern: Add Tool with Learning

```python
async def use_tool_with_learning(tool_name, args):
    start = time.time()
    try:
        result = await tool_func(args)
        await mcp_learner.record_event(
            tool=tool_name, args=args, success=True,
            duration_ms=int((time.time()-start)*1000), context={}
        )
        return result
    except Exception as e:
        await mcp_learner.record_event(
            tool=tool_name, args=args, success=False,
            duration_ms=int((time.time()-start)*1000), context={'error': str(e)}
        )
        raise
```

### Pattern: Get Tool Suggestions

```python
suggestions = mcp_learner.suggest_tools(task_hint="search code", top_k=3)
# Use top: suggestions[0]['name']
```

### Pattern: Evolve Behavior

```python
# Define genome
genome = {'approach': 'smart', 'exploration': 0.5}

# Fitness
async def fit(g): return await test(g)

# Evolve
learner.initialize_population(genome)
for _ in range(10):
    await learner.evaluate_population(fit)
    learner.evolve_generation()

# Apply
best = learner.get_best_genome()
```

---

## Checklist for New Features

- [ ] Telemetry recording (success/failure/duration)
- [ ] Fitness function defined
- [ ] RL state representation
- [ ] Failure → evolution trigger
- [ ] Crisis detection keywords
- [ ] Knowledge persistence
- [ ] Async throughout
- [ ] Genome-based behavior

---

**See Also**: [Full Learning Integration Guide](./LEARNING_INTEGRATION_GUIDE.md)
