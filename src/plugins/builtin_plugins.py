import os
import platform
import psutil
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import aiofiles

from .plugin_manager import Plugin
from ..execution import SandboxExecutor

class FileManagerPlugin(Plugin):
    """Plugin for file management operations"""
    
    def __init__(self):
        super().__init__()
        self.name = "FileManager"
        self.description = "File management operations"
        self.version = "1.0.0"
    
    async def initialize(self, assistant):
        """Initialize the plugin"""
        self.assistant = assistant
        self.register_command("ls", self.list_files)
        self.register_command("cat", self.read_file)
        self.register_command("mkdir", self.make_directory)
        self.register_command("find", self.find_files)
        # optional write command leveraging fs.write
        self.register_command("write", self.write_file)
    
    # metric update helper
    def _record_tool_metrics(self, tool_name: str, ok: bool, latency_ms: int = 0):
        try:
            bucket = self.assistant.metrics.get('tool_metrics', {})
            tools = bucket.setdefault('tools', {})
            rec = tools.setdefault(tool_name, {
                'calls': 0,
                'successes': 0,
                'failures': 0,
                'total_latency_ms': 0
            })
            rec['calls'] += 1
            if ok:
                rec['successes'] += 1
            else:
                rec['failures'] += 1
            rec['total_latency_ms'] += max(0, int(latency_ms))
            bucket['last_updated'] = datetime.now().isoformat()
            self.assistant.metrics['tool_metrics'] = bucket
            # Persist metrics to data/metrics.json for adaptive selector
            try:
                metrics_file = self.assistant.config.data_dir / "metrics.json"
                with open(metrics_file, 'w') as f:
                    json.dump(self.assistant.metrics, f, indent=2)
            except Exception:
                pass
        except Exception:
            pass
    
    async def handle_command(self, command: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle file management commands"""
        parts = command.strip().split()
        if not parts:
            return None
        cmd = parts[0].lower()
        if cmd in self.commands:
            handler = self.commands[cmd]
            return await handler(parts[1:] if len(parts) > 1 else [], context)
        return None
    
    async def list_files(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """List files in directory via sandbox ToolRunner"""
        target = args[0] if args else "."
        resp = await self.assistant.sandbox_executor.run_fs_ls(target)
        lat = (resp.get('metadata') or {}).get('latency_ms', 0)
        self._record_tool_metrics('fs.ls', resp.get('success', False), lat)
        if resp.get('success'):
            return {
                'content': json.dumps(resp.get('content', []), indent=2),
                'type': 'file_list',
                'metadata': {'path': target, 'count': len(resp.get('content') or [])}
            }
        return {'content': f"Error listing files: {resp.get('error')}", 'type': 'error'}
    
    async def read_file(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Read file via sandbox ToolRunner"""
        if not args:
            return {'content': 'Usage: cat <filename>', 'type': 'error'}
        resp = await self.assistant.sandbox_executor.run_fs_cat(args[0])
        lat = (resp.get('metadata') or {}).get('latency_ms', 0)
        self._record_tool_metrics('fs.cat', resp.get('success', False), lat)
        if resp.get('success'):
            content = resp.get('content') or ''
            return {'content': content, 'type': 'file_content', 'metadata': {'path': args[0], 'size': len(content)}}
        return {'content': f"Error reading file: {resp.get('error')}", 'type': 'error'}
    
    async def write_file(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Write file via sandbox ToolRunner: write <path> <content...>"""
        if not args:
            return {'content': 'Usage: write <path> <content...>', 'type': 'error'}
        path = args[0]
        content = ' '.join(args[1:]) if len(args) > 1 else ''
        resp = await self.assistant.sandbox_executor.run_fs_write(path, content)
        lat = (resp.get('metadata') or {}).get('latency_ms', 0)
        self._record_tool_metrics('fs.write', resp.get('success', False), lat)
        if resp.get('success'):
            return {'content': f"Wrote {len(content)} bytes to {path}", 'type': 'success'}
        return {'content': f"Error writing file: {resp.get('error')}", 'type': 'error'}
    
    async def make_directory(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create directory via sandbox ToolRunner"""
        if not args:
            return {'content': 'Usage: mkdir <directory>', 'type': 'error'}
        resp = await self.assistant.sandbox_executor.run_fs_mkdir(args[0])
        lat = (resp.get('metadata') or {}).get('latency_ms', 0)
        self._record_tool_metrics('fs.mkdir', resp.get('success', False), lat)
        if resp.get('success'):
            return {'content': f"Directory created: {args[0]}", 'type': 'success'}
        return {'content': f"Error creating directory: {resp.get('error')}", 'type': 'error'}
    
    async def find_files(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Find files via sandbox ToolRunner"""
        if not args:
            return {'content': 'Usage: find <pattern> [root]', 'type': 'error'}
        pattern = args[0]
        root = args[1] if len(args) > 1 else None
        resp = await self.assistant.sandbox_executor.run_fs_find(pattern, root)
        lat = (resp.get('metadata') or {}).get('latency_ms', 0)
        self._record_tool_metrics('fs.find', resp.get('success', False), lat)
        if resp.get('success'):
            items = resp.get('content') or []
            return {'content': '\n'.join(items[:100]), 'type': 'file_list', 'metadata': {'pattern': pattern, 'matches': len(items)}}
        return {'content': f"Error finding files: {resp.get('error')}", 'type': 'error'}
    
class WebSearchPlugin(Plugin):
    """Plugin for web search operations"""
    
    def __init__(self):
        super().__init__()
        self.name = "WebSearch"
        self.description = "Web search functionality"
        self.version = "1.0.0"
    
    async def initialize(self, assistant):
        """Initialize the plugin"""
        self.assistant = assistant
        self.register_command("search", self.web_search)
        self.register_command("google", self.google_search)
    
    async def handle_command(self, command: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle web search commands"""
        parts = command.strip().split(maxsplit=1)
        if not parts:
            return None
        cmd = parts[0].lower()
        if cmd in self.commands:
            query = parts[1] if len(parts) > 1 else ""
            handler = self.commands[cmd]
            return await handler(query, context)
        return None
    
    async def web_search(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform web search (placeholder)"""
        if not query:
            return {'content': 'Usage: search <query>', 'type': 'error'}
        return {
            'content': f"Searching for: {query}\n\n[Search results would appear here]",
            'type': 'search_results',
            'metadata': {'query': query}
        }
    
    async def google_search(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Google search shortcut"""
        return await self.web_search(query, context)

class TaskManagerPlugin(Plugin):
    """Plugin for task management"""
    
    def __init__(self):
        super().__init__()
        self.name = "TaskManager"
        self.description = "Task and todo management"
        self.version = "1.0.0"
        self.tasks: List[Dict[str, Any]] = []
    
    async def initialize(self, assistant):
        """Initialize the plugin"""
        self.assistant = assistant
        self.register_command("todo", self.manage_todos)
        self.register_command("task", self.manage_tasks)
    
    async def handle_command(self, command: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle task management commands"""
        parts = command.strip().split()
        if not parts:
            return None
        cmd = parts[0].lower()
        if cmd in self.commands:
            handler = self.commands[cmd]
            return await handler(parts[1:], context)
        return None
    
    async def manage_todos(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Manage todo items"""
        if not args:
            if not self.tasks:
                return {'content': 'No tasks found', 'type': 'info'}
            task_list = []
            for i, task in enumerate(self.tasks):
                status = "✓" if task.get('completed') else "○"
                task_list.append(f"{i+1}. {status} {task.get('description','')}")
            return {'content': '\n'.join(task_list), 'type': 'task_list'}
        action = args[0].lower()
        if action == 'add':
            description = ' '.join(args[1:])
            task = {
                'description': description,
                'completed': False,
                'created': datetime.now().isoformat()
            }
            self.tasks.append(task)
            return {'content': f"Task added: {description}", 'type': 'success'}
        elif action == 'complete' and len(args) > 1:
            try:
                task_num = int(args[1]) - 1
                if 0 <= task_num < len(self.tasks):
                    self.tasks[task_num]['completed'] = True
                    return {'content': f"Task completed: {self.tasks[task_num]['description']}", 'type': 'success'}
            except ValueError:
                pass
        return {'content': 'Usage: todo [add <description>|complete <number>]', 'type': 'info'}
    
    async def manage_tasks(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Alias for todo management"""
        return await self.manage_todos(args, context)

class SystemInfoPlugin(Plugin):
    """Plugin for system information"""
    
    def __init__(self):
        super().__init__()
        self.name = "SystemInfo"
        self.description = "System information and monitoring"
        self.version = "1.0.0"
    
    async def initialize(self, assistant):
        """Initialize the plugin"""
        self.assistant = assistant
        self.register_command("sysinfo", self.system_info)
        self.register_command("cpu", self.cpu_info)
        self.register_command("memory", self.memory_info)
        self.register_command("disk", self.disk_info)
    
    async def handle_command(self, command: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle system info commands"""
        
        parts = command.strip().split()
        if not parts:
            return None
        
        cmd = parts[0].lower()
        
        if cmd in self.commands:
            handler = self.commands[cmd]
            return await handler(context)
        
        return None
    
    async def system_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get system information"""
        
        info = {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_usage': psutil.disk_usage('/').percent
        }
        
        return {
            'content': json.dumps(info, indent=2),
            'type': 'system_info',
            'metadata': info
        }
    
    async def cpu_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get CPU information"""
        
        info = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'cpu_count': psutil.cpu_count(),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        }
        
        return {
            'content': f"CPU Usage: {info['cpu_percent']}%\nCores: {info['cpu_count']} physical, {info['cpu_count_logical']} logical",
            'type': 'cpu_info',
            'metadata': info
        }
    
    async def memory_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get memory information"""
        
        mem = psutil.virtual_memory()
        info = {
            'total': mem.total,
            'available': mem.available,
            'percent': mem.percent,
            'used': mem.used,
            'free': mem.free
        }
        
        return {
            'content': f"Memory: {mem.percent}% used\nTotal: {mem.total / 1024**3:.1f} GB\nAvailable: {mem.available / 1024**3:.1f} GB",
            'type': 'memory_info',
            'metadata': info
        }
    
    async def disk_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get disk information"""
        
        disk = psutil.disk_usage('/')
        info = {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': disk.percent
        }
        
        return {
            'content': f"Disk: {disk.percent}% used\nTotal: {disk.total / 1024**3:.1f} GB\nFree: {disk.free / 1024**3:.1f} GB",
            'type': 'disk_info',
            'metadata': info
        }

class CustomToolsPlugin(Plugin):
    """Expose sandbox ToolRunner tools directly under fs.* namespace"""

    def __init__(self):
        super().__init__()
        self.name = "CustomTools"
        self.description = "Direct access to sandboxed file system tools (fs.*)"
        self.version = "1.0.0"
    
    async def initialize(self, assistant):
        self.assistant = assistant
        # Register tool-style commands
        self.register_command("fs.ls", self.fs_ls)
        self.register_command("fs.cat", self.fs_cat)
        self.register_command("fs.write", self.fs_write)
        self.register_command("fs.mkdir", self.fs_mkdir)
        self.register_command("fs.find", self.fs_find)
        # Register simple utility commands
        self.register_command("util.print", self.util_print)
    
    def _record_tool_metrics(self, tool_name: str, ok: bool, latency_ms: int = 0):
        # Reuse same persistence strategy as FileManagerPlugin
        try:
            bucket = self.assistant.metrics.get('tool_metrics', {})
            tools = bucket.setdefault('tools', {})
            rec = tools.setdefault(tool_name, {
                'calls': 0,
                'successes': 0,
                'failures': 0,
                'total_latency_ms': 0
            })
            rec['calls'] += 1
            if ok:
                rec['successes'] += 1
            else:
                rec['failures'] += 1
            rec['total_latency_ms'] += max(0, int(latency_ms))
            bucket['last_updated'] = datetime.now().isoformat()
            self.assistant.metrics['tool_metrics'] = bucket
            try:
                metrics_file = self.assistant.config.data_dir / "metrics.json"
                with open(metrics_file, 'w') as f:
                    json.dump(self.assistant.metrics, f, indent=2)
            except Exception:
                pass
        except Exception:
            pass

    async def handle_command(self, command: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        parts = command.strip().split()
        if not parts:
            return None
        cmd = parts[0].lower()
        if cmd in self.commands:
            handler = self.commands[cmd]
            return await handler(parts[1:] if len(parts) > 1 else [], context)

    async def fs_ls(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        target = args[0] if args else "."
        resp = await self.assistant.sandbox_executor.run_fs_ls(target)
        lat = (resp.get('metadata') or {}).get('latency_ms', 0)
        self._record_tool_metrics('fs.ls', resp.get('success', False), lat)
        if resp.get('success'):
            return {'content': json.dumps(resp.get('content', []), indent=2), 'type': 'file_list', 'metadata': {'path': target}}
        return {'content': f"Error listing files: {resp.get('error')}", 'type': 'error'}

    async def fs_cat(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        if not args:
            return {'content': 'Usage: fs.cat <path>', 'type': 'error'}
        path = args[0]
        resp = await self.assistant.sandbox_executor.run_fs_cat(path)
        lat = (resp.get('metadata') or {}).get('latency_ms', 0)
        self._record_tool_metrics('fs.cat', resp.get('success', False), lat)
        if resp.get('success'):
            content = resp.get('content') or ''
            return {'content': content, 'type': 'file_content', 'metadata': {'path': path, 'size': len(content)}}
        return {'content': f"Error reading file: {resp.get('error')}", 'type': 'error'}

    async def fs_write(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        if not args:
            return {'content': 'Usage: fs.write <path> <content...>', 'type': 'error'}
        path = args[0]
        content = ' '.join(args[1:]) if len(args) > 1 else ''
        resp = await self.assistant.sandbox_executor.run_fs_write(path, content)
        lat = (resp.get('metadata') or {}).get('latency_ms', 0)
        self._record_tool_metrics('fs.write', resp.get('success', False), lat)
        if resp.get('success'):
            return {'content': f"Wrote {len(content)} bytes to {path}", 'type': 'success'}
        return {'content': f"Error writing file: {resp.get('error')}", 'type': 'error'}

    async def fs_mkdir(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        if not args:
            return {'content': 'Usage: fs.mkdir <dir>', 'type': 'error'}
        target = args[0]
        resp = await self.assistant.sandbox_executor.run_fs_mkdir(target)
        lat = (resp.get('metadata') or {}).get('latency_ms', 0)
        self._record_tool_metrics('fs.mkdir', resp.get('success', False), lat)
        if resp.get('success'):
            return {'content': f"Directory created: {target}", 'type': 'success'}
        return {'content': f"Error creating directory: {resp.get('error')}", 'type': 'error'}

    async def fs_find(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        if not args:
            return {'content': 'Usage: fs.find <pattern> [root]', 'type': 'error'}
        pattern = args[0]
        root = args[1] if len(args) > 1 else None
        resp = await self.assistant.sandbox_executor.run_fs_find(pattern, root)
        lat = (resp.get('metadata') or {}).get('latency_ms', 0)
        self._record_tool_metrics('fs.find', resp.get('success', False), lat)
        if resp.get('success'):
            items = resp.get('content') or []
            return {'content': '\n'.join(items[:100]), 'type': 'file_list', 'metadata': {'pattern': pattern, 'matches': len(items)}}
        return {'content': f"Error finding files: {resp.get('error')}", 'type': 'error'}

    async def util_print(self, args: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Print the provided text and return it back for verification.
        Usage: util.print <text...>
        """
        if not args:
            return {'content': 'Usage: util.print <text...>', 'type': 'error'}
        message = ' '.join(args)
        ok = True
        try:
            # Basic side-effect for debugging: print to stdout
            print(message)
            # Track in metrics
            self._record_tool_metrics('util.print', True, 0)
            # Record usage pattern for learning
            try:
                if getattr(self.assistant, 'memory_manager', None) is not None:
                    await self.assistant.memory_manager.detect_pattern('tool_usage', {
                        'tool': 'util.print',
                        'args': args,
                        'verified': True,
                        'source': 'plugin',
                        'timestamp': datetime.now().isoformat(),
                    })
            except Exception:
                pass
            return {'content': message, 'type': 'print_result', 'metadata': {'length': len(message)}}
        except Exception as e:
            ok = False
            self._record_tool_metrics('util.print', False, 0)
            try:
                if getattr(self.assistant, 'memory_manager', None) is not None:
                    await self.assistant.memory_manager.detect_pattern('tool_usage', {
                        'tool': 'util.print',
                        'args': args,
                        'verified': False,
                        'error': str(e),
                        'source': 'plugin',
                        'timestamp': datetime.now().isoformat(),
                    })
            except Exception:
                pass
            return {'content': f"Error printing: {e}", 'type': 'error'}

class MCPToolsPlugin(Plugin):
    """Scaffold plugin for MCP tool calls (Travliy, Desktop Commander, Context7)
    This integrates with the existing plugin framework, metrics, and memory system.
    Actual transport (e.g., WebSocket) is intentionally not implemented yet.
    """
    def __init__(self):
        super().__init__()
        self.name = "MCPTools"
        self.description = "Scaffold for MCP tool calls: travliy.search, desktop.cmd, ctx7.search"
        self.version = "0.1.0"
        # Keep an internal registry of dynamically discovered commands to avoid duplicates
        self._discovered_commands = set()
        # Cache of parsed servers.json for potential future transport use
        self._mcp_server_configs = {}
        # Track active servers by name for quick lookup
        self._active_server_names = set()

    async def initialize(self, assistant):
        # Store assistant so we can use config, metrics, memory_manager
        self.assistant = assistant
        # Register placeholder commands to mirror other plugins' structure
        self.register_command("travliy.search", self.travliy_search)
        self.register_command("desktop.cmd", self.desktop_cmd)
        self.register_command("ctx7.search", self.ctx7_search)
        # Dynamically discover additional MCP tool namespaces and register lightweight handlers
        try:
            await self._discover_and_register_mcp_tools()
        except Exception:
            # Defensive: do not break plugin init if discovery fails
            pass

    async def handle_command(self, command: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Dispatch MCP commands based on the first token."""
        parts = command.strip().split()
        if not parts:
            return None
        cmd = parts[0].lower()
        if cmd in self.commands:
            handler = self.commands[cmd]
            return await handler(parts[1:] if len(parts) > 1 else [], context)
        return None

    def _record_tool_metrics(self, tool_name: str, ok: bool, latency_ms: int = 0):
        # Follow the same metrics persistence pattern as other plugins
        try:
            bucket = self.assistant.metrics.get('tool_metrics', {})
            tools = bucket.setdefault('tools', {})
            rec = tools.setdefault(tool_name, {
                'calls': 0,
                'successes': 0,
                'failures': 0,
                'total_latency_ms': 0
            })
            rec['calls'] += 1
            if ok:
                rec['successes'] += 1
            else:
                rec['failures'] += 1
            rec['total_latency_ms'] += max(0, int(latency_ms))
            bucket['last_updated'] = datetime.now().isoformat()
            self.assistant.metrics['tool_metrics'] = bucket
            try:
                metrics_file = self.assistant.config.data_dir / "metrics.json"
                with open(metrics_file, 'w') as f:
                    json.dump(self.assistant.metrics, f, indent=2)
            except Exception:
                pass
        except Exception:
            pass

    async def _record_pattern(self, tool: str, args: Any, ok: bool, extra: Optional[Dict[str, Any]] = None):
        # Store usage patterns into memory for the learning system
        try:
            mm = getattr(self.assistant, 'memory_manager', None)
            if mm is None:
                return
            payload = {
                'tool': tool,
                'args': args,
                'success': ok,
                'timestamp': datetime.now().isoformat(),
                'source': 'plugin',
            }
            if extra:
                payload.update(extra)
            await mm.detect_pattern('tool_usage', payload)
        except Exception:
            pass

    # --- Dynamic MCP discovery helpers ----------------------------------------------------------
    async def _discover_and_register_mcp_tools(self):
        """Discover MCP tool namespaces from the on-disk scaffold and register handlers.
        
        Sources considered:
        - Folders under src/MCP PLUGINS/servers (e.g., travliy.search, desktop.cmd, ctx7.search)
        - servers.json for server runtime metadata (parsed and cached for future use)
        
        Notes:
        - This only wires lightweight scaffold handlers. Actual MCP transport is intentionally
          out of scope here and will be added later to call real servers.
        """
        # Resolve servers root path using the assistant's configured base_dir
        try:
            base_dir: Path = getattr(self.assistant.config, 'base_dir', None)
            if base_dir is None:
                # Fallback: infer from this file's location
                base_dir = Path(__file__).parent.parent
        except Exception:
            base_dir = Path(__file__).parent.parent
        servers_root = base_dir / 'src' / 'mcp plugins' / 'servers'

        # Parse servers.json if available (cache only; not used for filtering yet)
        servers_json = servers_root / 'servers.json'
        if servers_json.exists():
            try:
                with open(servers_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                servers_list = data.get('servers', []) or []
                for s in servers_list:
                    name = str(s.get('name', '')).strip()
                    if name:
                        self._mcp_server_configs[name] = s
                        # Maintain active set to enable subprocess smoke-run for these entries
                        if bool(s.get('active', True)):
                            self._active_server_names.add(name)
            except Exception:
                # Keep going even if JSON is malformed
                pass

        # Scan subdirectories to discover tool namespaces
        if servers_root.exists() and servers_root.is_dir():
            try:
                for child in servers_root.iterdir():
                    if not child.is_dir():
                        continue
                    cmd_name = child.name.strip()
                    # Skip obvious non-tools
                    if not cmd_name:
                        continue
                    # Avoid duplicate registration and avoid clobbering explicit handlers
                    if cmd_name in self.commands or cmd_name in self._discovered_commands:
                        continue
                    # Prefer recognizable namespaces like foo.bar, but also allow underscores
                    # to match existing folder naming. This scaffolds a generic handler.
                    self.register_command(cmd_name, self._make_dynamic_handler(cmd_name))
                    self._discovered_commands.add(cmd_name)
            except Exception:
                # Do not interrupt initialization due to discovery issues
                pass

    def _make_dynamic_handler(self, command_name: str):
        """Create a handler for a dynamically discovered MCP tool.
        If the command matches an active servers.json entry, run a safe subprocess smoke test.
        Otherwise, return the original scaffold response. Clear comments for easy debug.
        """
        async def _run_server_smoke(server_cfg: Dict[str, Any], user_args: Any) -> Dict[str, Any]:
            # Compose command list: base command + configured args + optional user args (strings only)
            try:
                base_cmd = str(server_cfg.get('command') or '').strip()
                cfg_args = server_cfg.get('args', []) or []
                timeout_sec = int(server_cfg.get('read_timeout_seconds', 120))
                if not base_cmd:
                    return {'content': 'Invalid servers.json: missing command', 'type': 'error'}

                # Normalize args to str list; append user tokens safely
                cmd: List[str] = [base_cmd] + [str(a) for a in cfg_args]
                extra: List[str] = []
                if isinstance(user_args, list):
                    # Only include alphanumeric/safe tokens to avoid injection; keep minimal
                    for tok in user_args:
                        try:
                            s = str(tok)
                            # Basic safety filter: allow flags/words, reject dangerous chars
                            if s and all(c.isalnum() or c in ['-', '_', '.', '/'] for c in s):
                                extra.append(s)
                        except Exception:
                            continue
                elif isinstance(user_args, str):
                    # Split on whitespace, apply same filter
                    for s in user_args.split():
                        if s and all(c.isalnum() or c in ['-', '_', '.', '/'] for c in s):
                            extra.append(s)
                # Final command
                cmd = cmd + extra

                # Async subprocess with bounded capture and safe teardown
                start_ts = datetime.now()
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                except Exception as e:
                    # Failed to start process (missing runtime, network issues, etc.)
                    return {
                        'content': f"Failed to start server '{server_cfg.get('name')}': {e}",
                        'type': 'error',
                        'metadata': {
                            'command': command_name,
                            'mode': 'subprocess_smoke',
                            'cmd': cmd,
                        }
                    }

                # Collect output for up to timeout_sec, then terminate
                max_bytes = 64 * 1024  # cap capture to 64KB to prevent memory blow
                captured_out: bytes = b''
                captured_err: bytes = b''

                async def _read_stream(reader: asyncio.StreamReader) -> bytes:
                    buf = b''
                    try:
                        while True:
                            chunk = await reader.read(4096)
                            if not chunk:
                                break
                            buf += chunk
                            if len(buf) >= max_bytes:
                                break
                    except Exception:
                        pass
                    return buf

                try:
                    # Wait a short grace period to let server bootstrap; then terminate
                    try:
                        await asyncio.wait_for(asyncio.sleep(min(2, max(0, timeout_sec // 10))), timeout=min(3, timeout_sec))
                    except Exception:
                        pass

                    # Concurrently read for the remaining time budget
                    read_budget = max(1, timeout_sec - 2)
                    try:
                        captured_out, captured_err = await asyncio.wait_for(
                            asyncio.gather(
                                _read_stream(proc.stdout),  # type: ignore[arg-type]
                                _read_stream(proc.stderr),  # type: ignore[arg-type]
                            ),
                            timeout=read_budget
                        )
                    except asyncio.TimeoutError:
                        # Reached read timeout; proceed to terminate
                        pass
                    except Exception:
                        pass

                    # Prepare metrics and response on success
                    end_ts = datetime.now()
                    dt_ms = int((end_ts - start_ts).total_seconds() * 1000)
                    self._record_tool_metrics(command_name, True, dt_ms)
                    await self._record_pattern(command_name, {'args': extra, 'cmd': cmd}, True, extra={'dynamic': True, 'mode': 'subprocess_smoke'})

                    # Prepare text output with truncation indicators
                    out_text = (captured_out or b'').decode('utf-8', errors='replace')
                    err_text = (captured_err or b'').decode('utf-8', errors='replace')
                    if len(out_text) > 4000:
                        out_text = out_text[:4000] + "\n... (truncated)"
                    if len(err_text) > 4000:
                        err_text = err_text[:4000] + "\n... (truncated)"

                    return {
                        'content': "\n".join([
                            f"[MCP subprocess] Ran: {' '.join(cmd)}",
                            "--- stdout ---",
                            out_text or "(no stdout)",
                            "--- stderr ---",
                            err_text or "(no stderr)",
                        ]),
                        'type': 'mcp_action',
                        'metadata': {
                            'command': command_name,
                            'cmd': cmd,
                            'mode': 'subprocess_smoke',
                            'timeout_sec': timeout_sec,
                            'duration_ms': dt_ms,
                        }
                    }
                except Exception as e:
                    # Fallback on any unexpected failure within smoke-run setup/teardown
                    try:
                        end_ts = datetime.now()
                        dt_ms = int((end_ts - start_ts).total_seconds() * 1000)
                    except Exception:
                        dt_ms = 0
                    self._record_tool_metrics(command_name, False, dt_ms)
                    try:
                        await self._record_pattern(command_name, {'args': user_args, 'error': str(e)}, False, extra={'dynamic': True, 'mode': 'subprocess_smoke'})
                    except Exception:
                        pass
                    return {
                        'content': f"Unexpected error during MCP subprocess smoke-run: {e}",
                        'type': 'error',
                        'metadata': {
                            'command': command_name,
                            'mode': 'subprocess_smoke',
                        }
                    }
                finally:
                    # Attempt graceful termination, then force kill if needed
                    try:
                        if proc.returncode is None:
                            proc.terminate()
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                    # Ensure process actually ends
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=5)
                    except Exception:
                        pass

            except Exception as e:
                # Outer safeguard for any unexpected errors in smoke-run orchestration.
                # Clear comments for easy debug and consistent metrics recording.
                try:
                    end_ts = datetime.now()
                    dt_ms = int((end_ts - start_ts).total_seconds() * 1000)  # type: ignore[name-defined]
                except Exception:
                    dt_ms = 0
                self._record_tool_metrics(command_name, False, dt_ms)
                try:
                    await self._record_pattern(
                        command_name,
                        {'args': user_args, 'error': str(e)},
                        False,
                        extra={'dynamic': True, 'mode': 'subprocess_smoke'}
                    )
                except Exception:
                    pass
                return {
                    'content': f"Unexpected outer error during MCP subprocess smoke-run: {e}",
                    'type': 'error',
                    'metadata': {'command': command_name, 'mode': 'subprocess_smoke'}
                }

        async def handler(args: Any, context: Dict[str, Any]) -> Dict[str, Any]:
            # If this command maps to an active server entry, attempt real subprocess smoke-run
            try:
                if command_name in self._active_server_names:
                    cfg = self._mcp_server_configs.get(command_name) or {}
                    return await _run_server_smoke(cfg, args)
            except Exception:
                # Fall back to scaffold on any unexpected error
                pass

            # Original scaffold behavior for non-active or unknown servers
            arg_str = ' '.join(args) if isinstance(args, list) else (args or '')
            meta = {
                'command': command_name,
                'args': args if isinstance(args, list) else [str(args)] if args else [],
                'mode': 'scaffold',
            }
            is_search = command_name.endswith('.search')
            try:
                self._record_tool_metrics(command_name, True, 0)
                await self._record_pattern(command_name, {'args': arg_str}, True, extra={'dynamic': True})
                return {
                    'content': f"[MCP scaffold] {command_name} would execute with: {arg_str}",
                    'type': 'search_results' if is_search else 'mcp_action',
                    'metadata': meta,
                }
            except Exception as e:
                self._record_tool_metrics(command_name, False, 0)
                await self._record_pattern(command_name, {'args': arg_str, 'error': str(e)}, False, extra={'dynamic': True})
                return {'content': f"Error executing {command_name}: {e}", 'type': 'error'}
        return handler

    async def travliy_search(self, args: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Placeholder for Travliy Search via MCP.
        Usage: travliy.search <query>
        """
        query = ' '.join(args) if isinstance(args, list) else (args or '')
        if not query:
            return {'content': 'Usage: travliy.search <query>', 'type': 'error'}
        # No network yet: echo back intent, integrate with memory/metrics
        self._record_tool_metrics('travliy.search', True, 0)
        await self._record_pattern('travliy.search', {'query': query}, True)
        return {
            'content': f"[MCP scaffold] Travliy would search for: {query}",
            'type': 'search_results',
            'metadata': {'query': query, 'mode': 'scaffold'}
        }
    
    async def desktop_cmd(self, args: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Placeholder for Desktop Commander via MCP.
        Usage: desktop.cmd <action...>
        """
        action = ' '.join(args) if isinstance(args, list) else (args or '')
        if not action:
            return {'content': 'Usage: desktop.cmd <action...>', 'type': 'error'}
        self._record_tool_metrics('desktop.cmd', True, 0)
        await self._record_pattern('desktop.cmd', {'action': action}, True)
        return {
            'content': f"[MCP scaffold] Desktop Commander would perform: {action}",
            'type': 'desktop_action',
            'metadata': {'action': action, 'mode': 'scaffold'}
        }
    
    async def ctx7_search(self, args: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Placeholder for Context7 integration via MCP.
        Usage: ctx7.search <query>
        """
        query = ' '.join(args) if isinstance(args, list) else (args or '')
        if not query:
            return {'content': 'Usage: ctx7.search <query>', 'type': 'error'}
        self._record_tool_metrics('ctx7.search', True, 0)
        await self._record_pattern('ctx7.search', {'query': query}, True)
        return {
            'content': f"[MCP scaffold] Context7 would search for: {query}",
            'type': 'search_results',
            'metadata': {'query': query, 'mode': 'scaffold'}
        }