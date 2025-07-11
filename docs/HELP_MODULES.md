# Sakana Desktop Assistant - Help Modules

## 🌊 Core Concepts

### What is Self-Evolution?
The Sakana Desktop Assistant uses evolutionary algorithms inspired by natural selection to develop new capabilities. Unlike traditional assistants with pre-programmed abilities, Sakana discovers and evolves its own solutions through experimentation.

### The Sakana Philosophy
- **Zero Initial Knowledge**: The system starts without knowing commands or file structures
- **Discovery Through Exploration**: Actively tests possibilities to learn what works
- **Evolution Through Success**: Successful strategies survive and improve
- **Continuous Learning**: Every interaction makes the system smarter

## 🚀 Getting Started

### First Run Experience
When you first run Sakana, you'll notice it takes time to initialize. This is because it's:
1. **Discovering Commands** - Testing which commands exist on your system
2. **Learning Paths** - Understanding your file system structure
3. **Building Memory** - Creating its knowledge database
4. **Evolving Strategies** - Developing initial approaches to tasks

**Expected startup time**: 2-5 minutes on first run (faster on subsequent runs)

### Understanding the Logs
```
INFO - Discovered command: find     # Found a working command
INFO - Generation 0 - Best fitness  # Evolution in progress
INFO - Recorded successful pattern  # Learned something new
```

## 📚 Module Documentation

### 1. File Discovery Module
**Purpose**: Learn to find files without pre-programmed knowledge

**How it works**:
- Generates potential command names (find, search, locate, etc.)
- Tests each to see if it exists
- Evolves search strategies through genetic algorithms
- Remembers successful patterns

**Example Evolution**:
```
Generation 0: Tries "find filename"
Generation 1: Discovers "find . -name filename"
Generation 2: Learns "find / -name filename 2>/dev/null"
```

### 2. Evolution Triggers Module
**Purpose**: Detect when to trigger self-improvement

**Triggers include**:
- Task failures (3+ similar failures)
- User negative feedback ("that's wrong", "not correct")
- Performance degradation
- New task types

### 3. Behavior Evolution Module
**Purpose**: Evolve actual behaviors, not just parameters

**Evolution methods**:
- **Mutation**: Random changes to behavior code
- **Crossover**: Combining successful behaviors
- **Selection**: Keeping behaviors that work
- **Innovation**: Discovering entirely new approaches

### 4. Memory Management
**Purpose**: Remember and learn from experiences

**Storage includes**:
- Successful command patterns
- User preferences and patterns
- Evolution history
- Discovered capabilities

## 🔧 User Guide

### Basic Commands
While Sakana discovers its own commands, you can ask it to:
- Find files: "find document.txt on my computer"
- Summarize documents: "read and summarize file.txt"
- Execute commands: "list files in current directory"
- Learn new tasks: "teach yourself how to..."

### Helping Sakana Learn
You can accelerate learning by:
1. **Providing feedback**: "yes, that's correct" or "no, try again"
2. **Being patient**: Let it complete its discovery process
3. **Trying variations**: Different phrasings help it learn patterns
4. **Reporting successes**: Positive feedback strengthens good behaviors

### Understanding Failures
When Sakana fails, it's learning:
- Each failure provides data for evolution
- Multiple failures trigger adaptation
- The system literally evolves new approaches

## 🧬 Technical Details

### Evolutionary Algorithm
```
1. Initialize population with random strategies
2. Test each strategy (fitness evaluation)
3. Select best performers
4. Create offspring through mutation/crossover
5. Replace worst performers
6. Repeat until success
```

### Fitness Functions
Success is measured by:
- Task completion (highest weight)
- Speed of execution
- Resource efficiency
- User satisfaction

### Memory Architecture
```
SQLite Database:
├── memories (short/long term)
├── patterns (detected behaviors)
├── evolution_history
└── user_preferences

JSON Archives:
├── evolution_archive.json (best genomes)
├── successful_patterns.json
└── discovered_commands.json
```

## 🤝 Contributing

### Adding New Learning Modules
1. Inherit from base learner class
2. Define discovery mechanism
3. Implement evolution strategy
4. Add fitness evaluation
5. Integrate with triggers

### Improving Evolution
- Enhance mutation strategies
- Add new crossover methods
- Improve fitness functions
- Optimize selection pressure

## 📊 Performance Expectations

### Learning Curves
- **Command Discovery**: 2-5 minutes initial, instant after
- **File Finding**: 3-5 attempts to optimize
- **New Tasks**: 5-10 generations typical
- **Complex Behaviors**: May take 20+ generations

### Resource Usage
- **Memory**: ~50MB for knowledge base
- **CPU**: Moderate during evolution
- **Disk**: Minimal (logs and memory)

## 🐛 Troubleshooting

### Slow Startup
- Normal on first run (discovering commands)
- Check logs for progress
- Ensure write permissions for data directory

### Evolution Not Progressing
- Check fitness function returns positive values
- Verify mutation rate (0.2-0.5 recommended)
- Ensure population diversity

### Commands Not Found
- Let discovery complete (can take minutes)
- Check system PATH
- Verify command availability

## 🎯 Future Modules

### Planned Capabilities
1. **Code Understanding** - Learn to read and modify code
2. **System Optimization** - Evolve performance improvements
3. **Language Learning** - Adapt to user communication style
4. **Tool Creation** - Generate new tools as needed

### Research Areas
- Multi-objective evolution
- Cooperative co-evolution
- Neural architecture search
- Meta-learning integration

## 📖 References

### Sakana AI Papers
- "The Sakana Model: Evolutionary Approaches to AI"
- "Darwin-Gödel Machine: Self-Modifying AI Systems"
- "Emergent Capabilities Through Natural Selection"

### Related Work
- Genetic Programming (Koza)
- Evolutionary Strategies (Rechenberg)
- Artificial Life (Langton)
- Open-Ended Evolution (Stanley)

---

*"Intelligence should emerge, not be engineered"* - Sakana AI Philosophy