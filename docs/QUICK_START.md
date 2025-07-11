# Sakana Desktop Assistant - Quick Start Guide

## 🎯 What You're Seeing

When you run `./run.sh`, the assistant is literally teaching itself from scratch:

```
INFO - Discovered command: find    ← Found a command that exists!
INFO - Discovered command: grep    ← Another one!
INFO - Discovered valid path: /    ← Learning your file system!
```

**This is NOT pre-programmed knowledge** - it's discovering these through trial and error, just like a child learning to walk.

## ⏱️ First Run Timeline

1. **0-30 seconds**: Loading core systems
2. **30 seconds - 3 minutes**: Discovering commands (find, grep, ls, etc.)
3. **3-5 minutes**: Learning file paths and system structure
4. **5+ minutes**: Ready for interaction!

## 💡 Understanding the Philosophy

Traditional Assistant:
```
User: "Find file.txt"
Assistant: *uses pre-programmed find command*
```

Sakana Assistant:
```
User: "Find file.txt"
Assistant: *evolves a search strategy from scratch*
  - Generation 0: Tries random commands
  - Generation 1: Discovers "find" exists
  - Generation 2: Learns syntax "find -name"
  - Generation 3: Optimizes with path strategies
  - Success: Returns file location
```

## 🚀 Your First Commands

Once you see "Assistant ready!", try:

1. **Test File Finding** (it will evolve a solution):
   ```
   find test.txt on my computer
   ```

2. **Watch It Learn**:
   ```
   teach yourself how to list files
   ```

3. **Document Reading** (triggers evolution):
   ```
   read C:\Users\nicol\document.txt
   ```

## 🧠 Helping It Learn

**Positive Feedback** (strengthens behavior):
- "yes, that's correct"
- "good job"
- "exactly"

**Negative Feedback** (triggers evolution):
- "no, that's wrong"
- "try again"
- "not correct"

## 📈 What Happens Over Time

- **Day 1**: Discovers basic commands, learns your file structure
- **Week 1**: Optimizes common tasks, learns your patterns
- **Month 1**: Develops sophisticated strategies unique to your system
- **Ongoing**: Continuously evolves new capabilities as needed

## ⚡ Pro Tips

1. **Be Patient**: Evolution takes time but creates robust solutions
2. **Let It Fail**: Failures are learning opportunities
3. **Give Feedback**: Accelerates learning dramatically
4. **Try Variations**: Different phrasings help it generalize

## 🔍 Watch Evolution in Action

Look for these log messages:
```
Generation 0 - Best fitness: 10.5    ← Starting evolution
Generation 5 - Best fitness: 85.2    ← Getting better!
Recorded successful pattern          ← Learned something!
Applying evolved behavior            ← Using what it learned
```

## 🎓 The Magic

Unlike ChatGPT or Copilot, Sakana:
- Starts with ZERO knowledge of commands
- Discovers capabilities through experimentation
- Evolves solutions specific to YOUR system
- Gets better with every use
- Never forgets what works

Welcome to the future of self-evolving AI! 🐟✨