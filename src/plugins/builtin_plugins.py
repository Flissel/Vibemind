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
    
    async def initialize(self, assistant):
        # Store assistant so we can use config, metrics, memory_manager
        self.assistant = assistant
        # Register placeholder commands to mirror other plugins' structure
        self.register_command("travliy.search", self.travliy_search)
        self.register_command("desktop.cmd", self.desktop_cmd)
        self.register_command("ctx7.search", self.ctx7_search)

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