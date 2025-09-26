import asyncio
import sys
from typing import Optional
import json
from datetime import datetime
try:
    import readline  # For better input handling (Unix/Linux)
except ImportError:
    # readline is not available on Windows by default, but that's okay
    pass

class CLIInterface:
    """Command line interface for the assistant"""
    
    def __init__(self, assistant):
        self.assistant = assistant
        self.running = False
        self.commands = {
            '/help': self.show_help,
            '/exit': self.exit_command,
            '/quit': self.exit_command,
            '/plugins': self.show_plugins,
            '/stats': self.show_stats,
            '/history': self.show_history,
            '/clear': self.clear_screen,
            '/save': self.save_conversation,
            '/feedback': self.provide_feedback,
            '/run': self.run_plugin_command,
        }
    
    async def initialize(self):
        """Initialize the CLI interface"""
        
        # Setup readline for better input (if available)
        try:
            readline.parse_and_bind('tab: complete')
            readline.set_completer(self.completer)
        except NameError:
            # readline not available (e.g., on Windows)
            pass
    
    def completer(self, text, state):
        """Tab completion for commands"""
        
        options = [cmd for cmd in self.commands if cmd.startswith(text)]
        
        if state < len(options):
            return options[state]
        return None
    
    async def run(self):
        """Run the CLI interface"""
        
        self.running = True
        
        while self.running:
            try:
                # Get user input
                user_input = await self.get_input()
                
                if not user_input:
                    continue
                
                # Check for commands
                if user_input.startswith('/'):
                    await self.handle_command(user_input)
                else:
                    # Process with assistant
                    await self.process_input(user_input)
                
            except EOFError:
                # Handle Ctrl+D
                await self.exit_command()
            except KeyboardInterrupt:
                # Handle Ctrl+C
                print("\nUse /exit to quit")
                continue
            except Exception as e:
                print(f"\nError: {e}")
                continue
    
    async def get_input(self) -> str:
        """Get input from user"""
        
        # Run input in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: input("\n> ").strip())
    
    async def handle_command(self, command: str):
        """Handle special commands"""
        
        parts = command.split()
        cmd = parts[0].lower()
        
        # Special-case: /delegate supports an inline natural-language goal
        if cmd == '/delegate':
            goal = command[len('/delegate'):].strip()
            if not goal:
                print("Usage: /delegate <goal>")
                print("Example: /delegate create docs/dev folder and scaffold agents")
            else:
                try:
                    from ..delegation.delegation_entry import run_delegation
                    result = await run_delegation(goal)
                    print(f"\n🧭 Delegation engine: {result.get('engine')}")
                    steps = result.get('transcript', [])
                    print(f"📝 Executed {len(steps)} step(s)")
                    for i, entry in enumerate(steps, 1):
                        # Normalize transcript entry to a common dict shape for safe printing
                        # - If entry is a raw string, wrap it as an info message
                        # - If entry is a dict without 'input'/'result' (e.g., command-style), map to friendly fields
                        if isinstance(entry, str):
                            entry = {
                                'input': '',
                                'result': {'type': 'info', 'content': entry}
                            }
                        elif isinstance(entry, dict) and ('input' not in entry or 'result' not in entry):
                            pretty_input = (f"{entry.get('command', '')} {entry.get('args', '')}").strip()
                            entry = {
                                'input': pretty_input,
                                'result': {
                                    'type': entry.get('status', 'info'),
                                    'content': entry.get('message') or entry.get('output') or entry.get('content') or ''
                                }
                            }
                        
                        inp = entry.get('input', '')
                        res = entry.get('result', {})
                        rtype = (res.get('type') or 'info') if isinstance(res, dict) else 'info'
                        snippet = ''
                        if isinstance(res, dict):
                            raw = res.get('content', '')
                            snippet = raw[:120] if isinstance(raw, str) else str(raw)[:120]
                        print(f"  {i}. {inp} -> {rtype}: {snippet}")
                except Exception as e:
                    print(f"Delegation failed: {e}")
            return
        
        if cmd in self.commands:
            handler = self.commands[cmd]
            await handler()
        else:
            print(f"Unknown command: {cmd}")
            print("Type /help for available commands")
    
    async def process_input(self, user_input: str):
        """Process user input through assistant"""
        
        print("\n🤔 Thinking...")
        
        # Process request
        start_time = datetime.now()
        result = await self.assistant.process_request(user_input)
        
        if result['success']:
            response = result['response']
            
            # Display response
            print("\n" + "-"*60)
            
            # Format based on response type
            if response['type'] == 'code':
                print("💻 Code:")
                print(response['content'])
            elif response['type'] == 'error':
                print("❌ Error:")
                print(response['content'])
            else:
                print("🐟 Sakana:")
                print(response['content'])
            
            # Show execution result if any
            if 'execution_result' in response:
                exec_result = response['execution_result']
                if exec_result['success']:
                    print("\n✅ Execution Output:")
                    print(exec_result['output'])
                else:
                    print("\n❌ Execution Error:")
                    print(exec_result['error'])
            
            print("-"*60)
            
            # Show response time
            print(f"\n⏱️  Response time: {result['response_time']:.2f}s")
            
            # Check for learning
            if result.get('memories_used', 0) > 0:
                print(f"🧠 Used {result['memories_used']} memories")
        else:
            print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
    
    async def show_help(self):
        """Show help information"""
        
        print("\n📚 Available Commands:")
        print("-" * 40)
        print("/help      - Show this help message")
        print("/plugins   - List loaded plugins")
        print("/stats     - Show learning statistics")
        print("/history   - Show conversation history")
        print("/clear     - Clear the screen")
        print("/save      - Save conversation to file")
        print("/feedback  - Provide feedback on responses")
        print("/delegate  - Run delegation planner for a natural-language goal")
        print("/run <cmd> - Run a plugin command explicitly (e.g., /run fs.ls .)")
        print("/exit      - Exit the assistant")
        print("\n💡 Tips:")
        print("- The assistant learns from your interactions")
        print("- It can execute code in a safe sandbox")
        print("- Use natural language for requests")
        print("- Provide feedback to improve responses")
    
    async def show_plugins(self):
        """Show loaded plugins"""
        
        if hasattr(self.assistant, 'plugin_manager'):
            plugins = self.assistant.plugin_manager.get_plugin_info()
            
            print("\n🔌 Loaded Plugins:")
            print("-" * 40)
            
            for plugin in plugins:
                print(f"\n{plugin['name']} v{plugin['version']}")
                print(f"  {plugin['description']}")
                print(f"  Commands: {', '.join(plugin['commands'])}")
        else:
            print("No plugin system available")
    
    async def show_stats(self):
        """Show learning statistics"""
        
        stats = self.assistant.metrics
        
        print("\n📊 Learning Statistics:")
        print("-" * 40)
        print(f"Requests handled: {stats['requests_handled']}")
        print(f"Successful completions: {stats['successful_completions']}")
        print(f"Errors: {stats['errors']}")
        print(f"Average response time: {stats['average_response_time']:.2f}s")
        print(f"Patterns learned: {stats['patterns_learned']}")
        print(f"Self-improvements: {stats['self_improvements']}")
        
        # Show RL stats if available
        if hasattr(self.assistant, 'reinforcement_learner'):
            rl_stats = self.assistant.reinforcement_learner.get_policy_stats()
            print(f"\n🧠 Reinforcement Learning:")
            print(f"States explored: {rl_stats['states_explored']}")
            print(f"Episodes completed: {rl_stats['episodes_completed']}")
            print(f"Exploration rate: {rl_stats['exploration_rate']:.3f}")
        
        # Show Tool metrics if available
        try:
            tool_bucket = stats.get('tool_metrics') or {}
            tools = tool_bucket.get('tools') or {}
            if tools:
                print("\n🛠️ Tool Usage Metrics:")
                print("Tool                Calls   Success%   Avg Latency (ms)")
                print("-" * 60)
                for name, rec in sorted(tools.items()):
                    calls = rec.get('calls', 0) or 0
                    succ = rec.get('successes', 0) or 0
                    total_lat = rec.get('total_latency_ms', 0) or 0
                    success_rate = (succ / calls * 100.0) if calls > 0 else 0.0
                    avg_latency = (total_lat / calls) if calls > 0 else 0
                    print(f"{name:<20} {calls:>6}   {success_rate:>7.1f}%   {int(avg_latency):>8}")
                if tool_bucket.get('last_updated'):
                    print(f"Last updated: {tool_bucket['last_updated']}")
        except Exception:
            pass
    
    async def show_history(self):
        """Show conversation history"""
        
        history = self.assistant.conversation_history[-10:]  # Last 10 exchanges
        
        print("\n📜 Recent Conversation History:")
        print("-" * 60)
        
        for i, exchange in enumerate(history, 1):
            timestamp = exchange.get('timestamp', 'Unknown')
            print(f"\n[{i}] {timestamp}")
            print(f"You: {exchange['user']}")
            print(f"Sakana: {exchange['assistant']['content'][:100]}...")
    
    async def clear_screen(self):
        """Clear the screen"""
        
        print("\033[2J\033[H")  # ANSI escape codes
        print("🐟 Sakana Desktop Assistant")
        print("="*60)
    
    async def save_conversation(self):
        """Save conversation to file"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sakana_conversation_{timestamp}.json"
        
        conversation_data = {
            'timestamp': datetime.now().isoformat(),
            'history': self.assistant.conversation_history,
            'stats': self.assistant.metrics
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(conversation_data, f, indent=2)
            
            print(f"\n✅ Conversation saved to: {filename}")
        except Exception as e:
            print(f"\n❌ Error saving conversation: {e}")
    
    async def provide_feedback(self):
        """Provide feedback on the last response"""
        
        print("\n💭 How was my last response?")
        print("1. 👍 Great")
        print("2. 👌 Good")
        print("3. 😐 Okay")
        print("4. 👎 Poor")
        print("5. ❌ Cancel")
        
        try:
            choice = await self.get_input()
            
            if choice in ['1', '2', '3', '4']:
                feedback = {
                    '1': {'user_satisfied': True, 'rating': 5},
                    '2': {'user_satisfied': True, 'rating': 4},
                    '3': {'user_satisfied': False, 'rating': 3},
                    '4': {'user_frustrated': True, 'rating': 2}
                }[choice]
                
                # Send feedback to learning system
                if hasattr(self.assistant, 'reinforcement_learner'):
                    reward = self.assistant.reinforcement_learner.calculate_reward(feedback)
                    print(f"\n✅ Thank you! Your feedback helps me learn (reward: {reward:.2f})")
                else:
                    print("\n✅ Thank you for your feedback!")
            
        except Exception as e:
            print(f"\n❌ Error processing feedback: {e}")
    
    async def exit_command(self):
        """Exit the assistant"""
        
        print("\n👋 Goodbye! Thanks for using Sakana Desktop Assistant.")
        self.running = False
    
    async def shutdown(self):
        """Shutdown the interface"""
        
        self.running = False


    async def run_plugin_command(self):
        """Forward an explicit plugin command entered as '/run <command ...>'
        This allows users who prefer slash commands to invoke tools directly.
        """
        try:
            # Read the full line from stdin buffer already captured in handle_command
            # Since handle_command only passes the command token, re-prompt for the rest here
            print("Enter plugin command (example: fs.ls .):")
            full = await self.get_input()
            user_input = full.strip()
            if not user_input:
                print("Usage: /run <plugin command>\nExample: /run fs.ls .")
                return
            
            # Build a minimal context (no additional memories) for deterministic tool execution
            context = self.assistant._build_context(user_input, [])  # Internal but stable; used for consistent tool context
            result = await self.assistant.plugin_manager.handle_command(user_input, context)
            if not result:
                print("No plugin handled that command. Use /plugins to see available commands.")
                return
            
            # Print result consistently with normal responses
            print("\n" + "-"*60)
            rtype = result.get('type', 'info') if isinstance(result, dict) else 'info'
            content = result.get('content') if isinstance(result, dict) else str(result)
            if rtype == 'error':
                print("❌ Error:")
            elif rtype == 'code':
                print("💻 Code:")
            else:
                print("🔧 Tool Result:")
            print(content)
            
            # Show execution_result if provided
            if isinstance(result, dict) and 'execution_result' in result:
                exec_result = result['execution_result']
                if exec_result.get('success'):
                    print("\n✅ Execution Output:")
                    print(exec_result.get('output', ''))
                else:
                    print("\n❌ Execution Error:")
                    print(exec_result.get('error', ''))
            print("-"*60)
        except Exception as e:
            print(f"Error running plugin command: {e}")