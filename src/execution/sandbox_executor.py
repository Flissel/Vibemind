import asyncio
import json
import os
import platform
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

class SandboxExecutor:
    """Execute code in a restricted environment using subprocess or Docker"""
    
    def __init__(self, max_execution_time: int = 10):
        self.max_execution_time = max_execution_time
        self.sandbox_dir = Path(tempfile.gettempdir()) / "sakana_sandbox"
        self.execution_history = []
    
    async def initialize(self):
        """Initialize sandbox environment"""
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        (self.sandbox_dir / "scripts").mkdir(parents=True, exist_ok=True)
        (self.sandbox_dir / "outputs").mkdir(parents=True, exist_ok=True)
        logger.info(f"Sandbox initialized at {self.sandbox_dir}")
    
    async def execute(self, code: str, language: str = 'python', environment: Optional[Dict[str, str]] = None, files: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Execute code in the sandbox using subprocess or Docker"""
        
        # Use subprocess for Python code, Docker for others
        if language == 'python':
            return await self._execute_subprocess(code, language, environment, files, execution_id=f"exec_{len(self.execution_history)+1}")
        else:
            return await self._execute_docker(code, language, environment, files, execution_id=f"exec_{len(self.execution_history)+1}")
    
    async def _execute_subprocess(self, code: str, language: str, environment: Optional[Dict[str, str]], files: Optional[Dict[str, str]], execution_id: str) -> Dict[str, Any]:
        """Execute code using subprocess (safe mode for Python)"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=self.sandbox_dir / "scripts") as f:
            f.write(code)
            script_path = f.name
        
        cmd = [sys.executable, script_path] if language == 'python' else [language, script_path]
        env = os.environ.copy()
        if environment:
            env.update(environment)
        
        start_time = datetime.now()
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.max_execution_time)
            execution_time = (datetime.now() - start_time).total_seconds()
            result = {
                'success': process.returncode == 0,
                'output': stdout.decode('utf-8', errors='replace'),
                'error': stderr.decode('utf-8', errors='replace'),
                'return_code': process.returncode,
                'execution_time': execution_time,
                'execution_id': execution_id
            }
        except asyncio.TimeoutError:
            result = {
                'success': False,
                'error': f"Execution timeout ({self.max_execution_time}s)",
                'output': '',
                'execution_time': self.max_execution_time,
                'execution_id': execution_id
            }
        finally:
            try:
                os.unlink(script_path)
            except Exception:
                pass
        
        # Save to history
        self.execution_history.append(result)
        return result
    
    async def _execute_docker(self, code: str, language: str, environment: Optional[Dict[str, str]], files: Optional[Dict[str, str]], execution_id: str) -> Dict[str, Any]:
        """Execute code in Docker container"""
        
        # Docker images for different languages
        images = {
            'python': 'python:3.11-slim',
            'javascript': 'node:18-slim',
            'bash': 'alpine:latest'
        }
        
        if language not in images:
            return await self._execute_subprocess(code, language, environment, files, execution_id)
        
        with tempfile.TemporaryDirectory(dir=self.sandbox_dir / "scripts") as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Write script
            script_name = {
                'python': 'script.py',
                'javascript': 'script.js',
                'bash': 'script.sh'
            }[language]
            
            script_file = tmpdir_path / script_name
            with open(script_file, 'w') as f:
                f.write(code)
            
            # Write additional files
            if files:
                for filename, content in files.items():
                    file_path = tmpdir_path / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'w') as f:
                        f.write(content)
            
            # Docker command
            docker_cmd = [
                'docker', 'run',
                '--rm',  # Remove container after execution
                '--network', 'none',  # No network access
                '--memory', '512m',  # Memory limit
                '--cpus', '0.5',  # CPU limit
                '-v', f'{tmpdir_path}:/workspace:ro',  # Mount as read-only
                '-w', '/workspace'
            ]
            
            # Add environment variables
            if environment:
                for key, value in environment.items():
                    docker_cmd.extend(['-e', f'{key}={value}'])
            
            # Add image and command
            docker_cmd.append(images[language])
            
            if language == 'python':
                docker_cmd.extend(['python', f'/workspace/{script_name}'])
            elif language == 'javascript':
                docker_cmd.extend(['node', f'/workspace/{script_name}'])
            elif language == 'bash':
                docker_cmd.extend(['sh', f'/workspace/{script_name}'])
            
            # Execute
            start_time = datetime.now()
            
            try:
                process = await asyncio.create_subprocess_exec(
                    *docker_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.max_execution_time + 5  # Extra time for Docker overhead
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return {
                    'success': process.returncode == 0,
                    'output': stdout.decode('utf-8', errors='replace'),
                    'error': stderr.decode('utf-8', errors='replace'),
                    'return_code': process.returncode,
                    'execution_time': execution_time,
                    'execution_id': execution_id
                }
                
            except asyncio.TimeoutError:
                # Kill the Docker container
                try:
                    kill_cmd = ['docker', 'kill', execution_id]
                    await asyncio.create_subprocess_exec(*kill_cmd)
                except:
                    pass
                
                return {
                    'success': False,
                    'error': f"Docker execution timeout ({self.max_execution_time}s)",
                    'output': '',
                    'execution_time': self.max_execution_time
                }
    
    async def execute_safe_function(self, function_code: str, function_name: str, args: List[Any] = None, kwargs: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a function with arguments in sandbox"""
        
        args = args or []
        kwargs = kwargs or {}
        
        # Create execution code
        execution_code = f"""
import json
import sys

# Function definition
{function_code}

# Execute function
try:
    args = {json.dumps(args)}
    kwargs = {json.dumps(kwargs)}
    result = {function_name}(*args, **kwargs)
    
    # Output result as JSON
    print(json.dumps({{'success': True, 'result': result}}))
except Exception as e:
    print(json.dumps({{'success': False, 'error': str(e)}}))
"""
        
        # Execute in sandbox
        result = await self.execute(execution_code, 'python')
        
        if result['success'] and result['output']:
            try:
                output_data = json.loads(result['output'].strip())
                return output_data
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': 'Failed to parse function output',
                    'raw_output': result['output']
                }
        else:
            return result
    
    # ------------------ Tool Runner Additions ------------------
    def _tool_response(self, *, tool: str, ok: bool, content: Any = None, error: Optional[str] = None, meta: Optional[Dict[str, Any]] = None, started_at: Optional[datetime] = None, finished_at: Optional[datetime] = None) -> Dict[str, Any]:
        """Build a standardized tool response envelope for telemetry & planning."""
        meta = meta or {}
        if started_at and finished_at:
            meta = {**meta, 'latency_ms': int((finished_at - started_at).total_seconds() * 1000)}
        return {
            'tool': tool,
            'success': ok,
            'content': content,
            'error': error,
            'metadata': meta
        }
    
    async def run_fs_ls(self, path: str) -> Dict[str, Any]:
        """List directory contents with Python first, sandboxed fallback."""
        start = datetime.now()
        try:
            p = Path(path) if path else Path.cwd()
            if not p.exists():
                return self._tool_response(tool='fs.ls', ok=False, error=f"Path not found: {p}", started_at=start, finished_at=datetime.now())
            items = []
            for it in p.iterdir():
                try:
                    stat = it.stat()
                    items.append({
                        'name': it.name,
                        'type': 'dir' if it.is_dir() else 'file',
                        'size': stat.st_size if it.is_file() else 0,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                except Exception as e:
                    items.append({'name': it.name, 'type': 'unknown', 'error': str(e)})
            return self._tool_response(tool='fs.ls', ok=True, content=items, meta={'path': str(p)}, started_at=start, finished_at=datetime.now())
        except Exception as e:
            # Fallback via sandboxed Python snippet
            code = f"""
import os, json, pathlib, time
_path = {path!r}
p = pathlib.Path(_path) if _path else pathlib.Path.cwd()
if not p.exists():
    print(json.dumps({'success': False, 'error': f'Path not found: {str(p)}'}))
else:
    out=[]
    for it in p.iterdir():
        try:
            st = it.stat()
            out.append({'name': it.name, 'type': 'dir' if it.is_dir() else 'file', 'size': st.st_size if it.is_file() else 0, 'modified': __import__('datetime').datetime.fromtimestamp(st.st_mtime).isoformat()})
        except Exception as ex:
            out.append({'name': it.name, 'type': 'unknown', 'error': str(ex)})
    print(json.dumps({'success': True, 'result': out}))
"""
            finished = datetime.now()
            res = await self.execute(code, 'python')
            ok = res.get('success') and res.get('output')
            payload = None
            err = res.get('error')
            if ok:
                try:
                    j = json.loads(res['output'].strip())
                    ok = j.get('success', False)
                    payload = j.get('result')
                    err = j.get('error')
                except Exception as parse_e:
                    ok = False
                    err = f"Parse error: {parse_e}"
            return self._tool_response(tool='fs.ls', ok=bool(ok), content=payload, error=err, meta={'path': path}, started_at=start, finished_at=finished)
    
    async def run_fs_cat(self, path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """Read a file with safe size handling."""
        start = datetime.now()
        try:
            p = Path(path)
            if not p.exists() or not p.is_file():
                return self._tool_response(tool='fs.cat', ok=False, error=f"File not found: {p}", started_at=start, finished_at=datetime.now())
            data = p.read_text(encoding=encoding, errors='replace')
            meta = {'path': str(p), 'size': len(data)}
            # Limit content to avoid flooding
            content = data if len(data) <= 200_000 else data[:200_000]
            return self._tool_response(tool='fs.cat', ok=True, content=content, meta=meta, started_at=start, finished_at=datetime.now())
        except Exception as e:
            return self._tool_response(tool='fs.cat', ok=False, error=str(e), meta={'path': path}, started_at=start, finished_at=datetime.now())
    
    async def run_fs_write(self, path: str, content: str, encoding: str = 'utf-8', overwrite: bool = True) -> Dict[str, Any]:
        """Write text content to a file with optional overwrite."""
        start = datetime.now()
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.exists() and not overwrite:
                return self._tool_response(tool='fs.write', ok=False, error=f"File exists: {p}")
            p.write_text(content, encoding=encoding)
            return self._tool_response(tool='fs.write', ok=True, meta={'path': str(p), 'bytes': len(content)}, started_at=start, finished_at=datetime.now())
        except Exception as e:
            return self._tool_response(tool='fs.write', ok=False, error=str(e), meta={'path': path}, started_at=start, finished_at=datetime.now())
    
    async def run_fs_mkdir(self, path: str, exist_ok: bool = True) -> Dict[str, Any]:
        """Create a directory path recursively."""
        start = datetime.now()
        try:
            p = Path(path)
            p.mkdir(parents=True, exist_ok=exist_ok)
            return self._tool_response(tool='fs.mkdir', ok=True, meta={'path': str(p)}, started_at=start, finished_at=datetime.now())
        except Exception as e:
            return self._tool_response(tool='fs.mkdir', ok=False, error=str(e), meta={'path': path}, started_at=start, finished_at=datetime.now())
    
    async def run_fs_find(self, pattern: str, root: Optional[str] = None, limit: int = 200) -> Dict[str, Any]:
        """Find files by glob pattern under root."""
        start = datetime.now()
        try:
            base = Path(root) if root else Path.cwd()
            matches = []
            for m in base.rglob(pattern):
                matches.append(str(m))
                if len(matches) >= limit:
                    break
            return self._tool_response(tool='fs.find', ok=True, content=matches, meta={'root': str(base), 'pattern': pattern, 'count': len(matches)}, started_at=start, finished_at=datetime.now())
        except Exception as e:
            return self._tool_response(tool='fs.find', ok=False, error=str(e), meta={'root': root, 'pattern': pattern}, started_at=start, finished_at=datetime.now())

    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return the most recent execution records (for observability)."""
        return self.execution_history[-limit:]

    async def cleanup(self):
        """Clean up sandbox resources (retain behavior expected by assistant)."""
        try:
            outputs_dir = self.sandbox_dir / "outputs"
            if outputs_dir.exists():
                for file in outputs_dir.iterdir():
                    if file.is_file():
                        age = datetime.now().timestamp() - file.stat().st_mtime
                        if age > 86400:  # 24 hours
                            file.unlink()
        except Exception as e:
            logger.warning(f"Sandbox cleanup encountered an issue: {e}")
        logger.info("Sandbox cleanup completed")