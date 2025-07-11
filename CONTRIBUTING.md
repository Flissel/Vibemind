# Contributing to Sakana Desktop Assistant

## 🌊 Welcome Contributors!

Sakana Desktop Assistant is an open-source project exploring self-evolving AI through natural selection. We welcome contributions that enhance the system's ability to discover and evolve new capabilities.

## 🧬 Core Philosophy

Before contributing, understand our core principles:

1. **Self-Discovery Over Programming**: We prefer systems that learn capabilities rather than having them hard-coded
2. **Evolution Over Engineering**: Solutions should emerge through natural selection
3. **Learning From Failure**: Errors are opportunities for adaptation
4. **Minimal Assumptions**: Start with less knowledge, discover more

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Understanding of evolutionary algorithms
- Familiarity with async Python
- Patience for watching systems learn

### Setup Development Environment
```bash
git clone https://github.com/nickinper/sakana-desktop-assistant.git
cd sakana-desktop-assistant
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development tools
```

### Understanding the Architecture
```
src/
├── core/           # Core assistant logic
├── learning/       # Evolution and self-modification modules
├── memory/         # Pattern detection and storage
├── plugins/        # Discoverable capabilities
└── execution/      # Safe code execution environment
```

## 🔧 Areas for Contribution

### 1. Evolution Mechanisms
- New mutation strategies
- Crossover algorithms
- Fitness function improvements
- Population management

### 2. Learning Modules
- New domains for self-learning (network, audio, etc.)
- Meta-learning capabilities
- Transfer learning between tasks
- Multi-objective optimization

### 3. Memory Systems
- Improved pattern detection
- Long-term memory optimization
- Forgetting mechanisms
- Memory compression

### 4. Self-Discovery
- New exploration strategies
- Command discovery improvements
- Environment mapping
- Capability detection

## 📝 Contribution Guidelines

### Code Style
- Follow PEP 8
- Use type hints
- Document evolutionary strategies
- Include docstrings explaining "why" not just "what"

### Testing Philosophy
- Test that evolution works, not specific outcomes
- Verify learning improves over time
- Ensure fitness functions are meaningful
- Test failure recovery

### Example: Adding a New Learner
```python
class YourDiscoveryLearner:
    """Discovers capabilities in a new domain through evolution"""
    
    def __init__(self):
        # Start with NO hardcoded knowledge
        self.discovered_capabilities = {}
        self.population = []
        
    async def discover_through_evolution(self):
        """Let the system discover capabilities"""
        # Generate random attempts
        # Test what works
        # Evolve successful strategies
        # Remember what was learned
```

## 🧪 Testing Your Changes

### Unit Tests
```bash
python -m pytest tests/unit/
```

### Evolution Tests
```bash
python -m pytest tests/evolution/ -v
# These test learning over time, may take longer
```

### Integration Tests
```bash
python tests/test_full_evolution.py
# Watch the system evolve from scratch
```

## 📊 Performance Considerations

When contributing, consider:
- Evolution speed vs. solution quality
- Memory usage during learning
- CPU usage during population evaluation
- Startup time impact

## 🐛 Reporting Issues

### Good Issue Reports Include
- What you expected to happen
- What actually happened
- Logs showing evolution attempts
- Your system configuration
- Minimal reproduction steps

### Example Issue
```
Title: Evolution gets stuck on file finding after 10 generations

Description:
When asking to find files with spaces in names, evolution reaches
Generation 10 but fitness plateaus at 45.2.

Logs:
Generation 8 - Best fitness: 45.2
Generation 9 - Best fitness: 45.2
Generation 10 - Best fitness: 45.2

Expected: Fitness should improve or strategy should adapt
```

## 🎯 Pull Request Process

1. **Branch Naming**: `feature/evolution-improvement` or `fix/learning-memory-leak`
2. **Commits**: Clear messages explaining the evolutionary improvement
3. **Documentation**: Update help modules if adding new learning capabilities
4. **Tests**: Include tests that verify learning, not just function
5. **Review**: Be patient, we test how changes affect evolution over time

### PR Template
```markdown
## What This Evolves
Brief description of what new capabilities can emerge

## Evolution Strategy
How the system discovers/learns this capability

## Testing Evolution
How to verify the system successfully evolves this

## Performance Impact
Startup time, evolution speed, memory usage
```

## 🧬 Advanced Contributions

### Meta-Evolution
Help the system evolve its own evolution strategies:
- Self-modifying mutation rates
- Adaptive population sizes
- Dynamic fitness functions
- Evolutionary strategy evolution

### Cross-Domain Learning
Enable learning transfer between domains:
- File operations → Network operations
- Command discovery → API discovery
- Pattern detection → Behavior prediction

## 🤝 Community

### Communication Channels
- GitHub Issues: Bug reports and feature discussions
- Discussions: Architecture and philosophy
- Pull Requests: Code contributions

### Code of Conduct
- Respect the evolutionary process
- Value emergence over engineering
- Share discoveries openly
- Help others understand evolution

## 📚 Resources

### Recommended Reading
- "Evolutionary Computation" by De Jong
- "Introduction to Evolutionary Computing" by Eiben & Smith
- Sakana AI publications on self-modifying systems
- Papers on open-ended evolution

### Understanding the Codebase
1. Start with `src/learning/file_discovery.py` - see evolution in action
2. Study `src/learning/evolution_triggers.py` - understand when evolution happens
3. Explore `src/core/assistant.py` - see how components integrate

## 🙏 Recognition

Contributors who help the system evolve new capabilities will be recognized in:
- CONTRIBUTORS.md
- Release notes
- Evolution history logs

## 💡 Innovation Encouraged

We especially welcome contributions that:
- Enable completely new forms of self-discovery
- Reduce hardcoded knowledge further
- Improve evolution speed dramatically
- Allow cross-domain capability transfer
- Enable the system to modify its own architecture

Remember: The best contribution might be one that helps Sakana contribute to itself!

---

*"The code that learns to code itself"* - The Sakana Way