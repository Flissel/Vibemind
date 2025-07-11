# Sakana Desktop Assistant

A self-learning desktop AI assistant that adapts to your needs and builds solutions autonomously, inspired by Sakana AI's cutting-edge self-learning methods.

## Features

- **Self-Learning**: Adapts to user patterns and preferences over time
- **Code Generation**: Can write and execute code in a sandboxed environment
- **Privacy-First**: All processing happens locally
- **Evolutionary Algorithms**: Self-improves through Darwin Gödel Machine-inspired mechanisms
- **Plugin Architecture**: Extensible system for adding new capabilities

## Architecture

- **Core Engine**: LLM integration with local models
- **Memory System**: SQLite-based short and long-term memory
- **Pattern Recognition**: Learns from user behavior
- **Sandboxed Execution**: Secure code execution environment
- **Self-Improvement Loop**: Evolutionary algorithms for continuous enhancement

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python src/main.py
```

## Security

- All code execution happens in sandboxed environments
- No data leaves your machine
- Audit logging for all operations