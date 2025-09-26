#!/usr/bin/env python3
"""
Tests for CustomToolsPlugin commands (fs.*) and SandboxExecutor ToolRunner methods.
This follows the project's existing test style (async script with prints) and
includes clear comments for easy debugging as required by the Autonomes programmer project.
"""

import asyncio
import sys
import json
from pathlib import Path
from tempfile import TemporaryDirectory

# Ensure src package is importable when running from project root
sys.path.insert(0, str(Path(__file__).parent))

from src.core import Config, SakanaAssistant


async def test_custom_tools():
    print("🧪 Testing CustomToolsPlugin and ToolRunner fs.* methods")
    print("=" * 60)

    # Create config and use mock LLM to avoid heavy operations
    config = Config()
    config.llm_provider = "mock"

    # Initialize assistant (loads plugins and sandbox executor)
    assistant = SakanaAssistant(config)
    await assistant.initialize()
    print("✅ Assistant initialized with plugins and sandbox")

    # Collect available commands and ensure fs.* commands are registered
    available = assistant.plugin_manager.get_available_commands()
    commands = sorted({c['command'] for c in available})
    expected = {"fs.ls", "fs.cat", "fs.write", "fs.mkdir", "fs.find"}
    missing = expected - set(commands)
    if missing:
        raise RuntimeError(f"Missing expected fs.* commands: {missing}. Available: {commands}")
    print("✅ CustomToolsPlugin commands registered:", ", ".join(sorted(expected)))

    # Create a temporary workspace for file system operations
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        subdir = tmp_path / "subdir"
        file_path = subdir / "hello.txt"

        # Use plugin manager to route fs.mkdir
        resp = await assistant.plugin_manager.handle_command(f"fs.mkdir {subdir}", context={})
        if not resp or resp.get("type") != "success" or not subdir.exists():
            raise RuntimeError(f"fs.mkdir failed: resp={resp}")
        print(f"✅ fs.mkdir created: {subdir}")

        # Use plugin manager to route fs.write
        content = "hello world"
        resp = await assistant.plugin_manager.handle_command(f"fs.write {file_path} {content}", context={})
        if not resp or resp.get("type") != "success" or not file_path.exists():
            raise RuntimeError(f"fs.write failed: resp={resp}")
        disk_data = file_path.read_text(encoding="utf-8")
        if disk_data != content:
            raise RuntimeError(f"fs.write content mismatch: expected='{content}', got='{disk_data}'")
        print(f"✅ fs.write wrote {len(content)} bytes to: {file_path}")

        # Use plugin manager to route fs.cat
        resp = await assistant.plugin_manager.handle_command(f"fs.cat {file_path}", context={})
        if not resp or resp.get("type") != "file_content" or resp.get("content") != content:
            raise RuntimeError(f"fs.cat failed or content mismatch: resp={resp}")
        print("✅ fs.cat returned expected content")

        # Use plugin manager to route fs.ls and verify the file is listed
        resp = await assistant.plugin_manager.handle_command(f"fs.ls {subdir}", context={})
        if not resp or resp.get("type") != "file_list":
            raise RuntimeError(f"fs.ls failed: resp={resp}")
        try:
            listing = json.loads(resp.get("content") or "[]")
        except Exception as e:
            raise RuntimeError(f"fs.ls returned non-JSON content: {e}; content={resp.get('content')}")
        names = {item.get("name") for item in listing if isinstance(item, dict)}
        if "hello.txt" not in names:
            raise RuntimeError(f"fs.ls did not include 'hello.txt': names={names}")
        print("✅ fs.ls listed expected entries")

        # Use plugin manager to route fs.find
        resp = await assistant.plugin_manager.handle_command(f"fs.find *.txt {tmp_path}", context={})
        if not resp or resp.get("type") != "file_list":
            raise RuntimeError(f"fs.find failed: resp={resp}")
        found_text = resp.get("content") or ""
        if str(file_path) not in found_text:
            raise RuntimeError(f"fs.find did not include target file; content={found_text}")
        print("✅ fs.find located the expected file")

        # Verify tool telemetry metrics were updated by CustomToolsPlugin
        tm = assistant.metrics.get("tool_metrics", {}).get("tools", {})
        # We expect at least these tools to have been invoked
        for t in ["fs.mkdir", "fs.write", "fs.cat", "fs.ls", "fs.find"]:
            rec = tm.get(t)
            if not rec or rec.get("calls", 0) < 1:
                raise RuntimeError(f"Telemetry missing or not updated for {t}: {rec}")
        print("✅ Tool telemetry updated for fs.* commands")

        # Now test ToolRunner methods directly on the SandboxExecutor
        # run_fs_ls
        res = await assistant.sandbox_executor.run_fs_ls(str(subdir))
        if not res.get("success") or res.get("tool") != "fs.ls":
            raise RuntimeError(f"run_fs_ls failed: {res}")
        if "latency_ms" not in (res.get("metadata") or {}):
            raise RuntimeError(f"run_fs_ls missing latency metadata: {res}")
        print("✅ run_fs_ls returned success with latency metadata")

        # run_fs_cat
        res = await assistant.sandbox_executor.run_fs_cat(str(file_path))
        if not res.get("success") or res.get("tool") != "fs.cat" or res.get("content") != content:
            raise RuntimeError(f"run_fs_cat failed or content mismatch: {res}")
        print("✅ run_fs_cat returned expected content")

        # run_fs_write (overwrite file)
        new_content = "updated"
        res = await assistant.sandbox_executor.run_fs_write(str(file_path), new_content)
        if not res.get("success") or res.get("tool") != "fs.write":
            raise RuntimeError(f"run_fs_write failed: {res}")
        on_disk = file_path.read_text(encoding="utf-8")
        if on_disk != new_content:
            raise RuntimeError(f"run_fs_write did not update content: '{on_disk}' != '{new_content}'")
        print("✅ run_fs_write overwrote file successfully")

        # run_fs_mkdir (create nested dir)
        nested_dir = tmp_path / "a" / "b" / "c"
        res = await assistant.sandbox_executor.run_fs_mkdir(str(nested_dir))
        if not res.get("success") or res.get("tool") != "fs.mkdir" or not nested_dir.exists():
            raise RuntimeError(f"run_fs_mkdir failed: {res}")
        print("✅ run_fs_mkdir created nested directories")

        # run_fs_find
        res = await assistant.sandbox_executor.run_fs_find("*.txt", root=str(tmp_path))
        if not res.get("success") or res.get("tool") != "fs.find":
            raise RuntimeError(f"run_fs_find failed: {res}")
        items = res.get("content") or []
        if str(file_path) not in items:
            raise RuntimeError(f"run_fs_find did not include target file: {items}")
        print("✅ run_fs_find found expected file in results")

    # Shutdown assistant to persist any metrics and cleanup
    await assistant.shutdown()
    print("\n✅ CustomToolsPlugin and ToolRunner tests completed successfully!\n")


if __name__ == "__main__":
    asyncio.run(test_custom_tools())