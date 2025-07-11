# Sakana Desktop Assistant - Quick Start Guide

## 🚀 Getting Started

### 1. Basic Setup

```bash
# Clone or navigate to the project
cd sakana-desktop-assistant

# Run the quick start script
./run.sh
```

### 2. Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the assistant
python src/main.py
```

## 🧠 Self-Learning Features

The assistant learns from your interactions through:

1. **Evolutionary Algorithms** - Optimizes behavior over time
2. **Pattern Recognition** - Learns your usage patterns
3. **Reinforcement Learning** - Improves from feedback
4. **Memory System** - Remembers past interactions

## 💬 Basic Commands

- **Natural Language**: Just type normally!
- `/help` - Show available commands
- `/plugins` - List loaded plugins
- `/stats` - View learning statistics
- `/feedback` - Rate responses to help learning

## 🔌 Built-in Plugins

### File Manager
- `ls [path]` - List files
- `cat <file>` - Read file
- `mkdir <dir>` - Create directory
- `find <pattern>` - Search files

### System Info
- `sysinfo` - System overview
- `cpu` - CPU usage
- `memory` - Memory usage
- `disk` - Disk usage

### Task Manager
- `todo` - List tasks
- `todo add <task>` - Add task
- `todo complete <num>` - Complete task

## 🛡️ Security

- All code runs in sandboxed environment
- No data leaves your machine
- Configurable permissions
- Audit logging enabled

## ⚙️ Configuration

Create a `config.yaml` file (see `config.example.yaml`):

```yaml
llm_provider: "local"  # or "openai"
model_name: "llama-3.2-3b"
sandbox_enabled: true
learning_rate: 0.01
```

## 🤖 Using Different LLMs

### Local Models (Default)
1. Download a GGUF model
2. Place in `models/` directory
3. Update `model_name` in config

### OpenAI
1. Set `OPENAI_API_KEY` environment variable
2. Set `llm_provider: "openai"` in config
3. Set `model_name: "gpt-4"` or preferred model

## 📈 Learning Progress

The assistant improves through:
- Pattern detection in your usage
- Evolutionary optimization
- Reinforcement from feedback
- Self-modification capabilities

View progress with `/stats` command.

## 🐛 Troubleshooting

### Common Issues

1. **No module found**: Run `pip install -r requirements.txt`
2. **Permission denied**: Run `chmod +x run.sh`
3. **Model not found**: Download a GGUF model to `models/`
4. **Memory errors**: Reduce `max_short_term_memory` in config

### Debug Mode

```bash
python src/main.py --learning off  # Disable learning
tail -f sakana_assistant.log      # View logs
```

## 🎯 Tips for Best Results

1. **Be consistent** - Use similar phrasing for similar tasks
2. **Provide feedback** - Use `/feedback` to rate responses
3. **Let it learn** - The more you use it, the better it gets
4. **Check patterns** - View `/stats` to see what it's learned

## 📚 Advanced Usage

### Creating Custom Plugins

1. Create a Python file in `plugins/`
2. Extend the `Plugin` base class
3. Register commands in `initialize()`
4. Restart the assistant

Example plugin:
```python
from plugins.plugin_manager import Plugin

class MyPlugin(Plugin):
    async def initialize(self, assistant):
        self.register_command("mycommand", self.my_handler)
    
    async def handle_command(self, command, context):
        # Handle the command
        pass
```

## 🔗 Next Steps

- Explore the codebase to understand the architecture
- Create custom plugins for your workflows
- Adjust learning parameters in config
- Contribute improvements back to the project!

Happy learning! 🐟