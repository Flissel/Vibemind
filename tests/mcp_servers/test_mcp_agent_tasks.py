#!/usr/bin/env python3
"""
MCP Agent Task Definitions

This module defines specific test tasks for each of the 18 active MCP agents.
Each task is designed to exercise the core functionality of the tool while
being simple enough to complete quickly and reliably.
"""

# Task definitions for all 18 active MCP agents
MCP_AGENT_TASKS = {
    "brave-search": {
        "task": "Search for 'Python programming tutorials' and return the top 3 results",
        "description": "Web search with Brave API",
        "expected_duration": 5,  # seconds
        "validation_keywords": ["python", "tutorial", "programming"]
    },

    "context7": {
        "task": "Get documentation for the React useState hook",
        "description": "Up-to-date code documentation retrieval",
        "expected_duration": 8,
        "validation_keywords": ["useState", "hook", "react"]
    },

    "desktop": {
        "task": "List files and directories in the current working directory",
        "description": "Desktop commander file operations",
        "expected_duration": 3,
        "validation_keywords": ["file", "directory", "list"]
    },

    "docker": {
        "task": "List all running Docker containers on the system",
        "description": "Docker container management",
        "expected_duration": 4,
        "validation_keywords": ["container", "docker", "running"]
    },

    "fetch": {
        "task": "Fetch the content from https://example.com and extract the page title",
        "description": "HTTP request and content retrieval",
        "expected_duration": 5,
        "validation_keywords": ["example", "domain", "title"]
    },

    "filesystem": {
        "task": "List all Python files in the project root directory",
        "description": "Filesystem operations with allowed directories",
        "expected_duration": 3,
        "validation_keywords": [".py", "file", "directory"]
    },

    "github": {
        "task": "Get information about the authenticated GitHub user",
        "description": "GitHub API user information",
        "expected_duration": 5,
        "validation_keywords": ["user", "github", "account"]
    },

    "memory": {
        "task": "Create a test entity named 'TestAgent' of type 'Software' with observation 'MCP testing entity'",
        "description": "Knowledge graph entity management",
        "expected_duration": 4,
        "validation_keywords": ["entity", "created", "knowledge"]
    },

    "n8n": {
        "task": "Get documentation for the n8n HTTP Request node",
        "description": "n8n workflow automation documentation",
        "expected_duration": 6,
        "validation_keywords": ["http", "request", "node"]
    },

    "playwright": {
        "task": "Navigate to https://example.com and take a screenshot",
        "description": "Browser automation with screenshots",
        "expected_duration": 12,
        "validation_keywords": ["navigate", "screenshot", "browser"]
    },

    "redis": {
        "task": "Ping the Redis server to verify connectivity",
        "description": "Redis key-value store operations",
        "expected_duration": 3,
        "validation_keywords": ["ping", "pong", "redis"]
    },

    "sequential-thinking": {
        "task": "Calculate the result of 15 multiplied by 23 using step-by-step reasoning",
        "description": "Structured problem-solving with reasoning",
        "expected_duration": 8,
        "validation_keywords": ["345", "multiply", "calculate"]
    },

    "supabase": {
        "task": "List all Supabase projects associated with the account",
        "description": "Supabase project management",
        "expected_duration": 5,
        "validation_keywords": ["project", "supabase", "list"]
    },

    "taskmanager": {
        "task": "Create a new task with title 'Test Task' and description 'MCP agent testing task'",
        "description": "Task creation and tracking",
        "expected_duration": 4,
        "validation_keywords": ["task", "created", "test"]
    },

    "tavily": {
        "task": "Search for 'latest AI developments 2025' using Tavily search",
        "description": "Real-time web search and data extraction",
        "expected_duration": 7,
        "validation_keywords": ["ai", "search", "result"]
    },

    "time": {
        "task": "Get the current time in UTC timezone and format it as ISO 8601",
        "description": "Time operations and timezone conversions",
        "expected_duration": 3,
        "validation_keywords": ["utc", "time", "iso"]
    },

    "windows-core": {
        "task": "Get detailed CPU information including cores and processor name",
        "description": "Windows system information retrieval",
        "expected_duration": 4,
        "validation_keywords": ["cpu", "processor", "core"]
    },

    "youtube": {
        "task": "Get the transcript for YouTube video ID 'dQw4w9WgXcQ' (first 100 characters)",
        "description": "YouTube transcript fetching",
        "expected_duration": 8,
        "validation_keywords": ["transcript", "youtube", "video"]
    }
}

# List of all active MCP tools (same order as tasks)
ACTIVE_MCPS = list(MCP_AGENT_TASKS.keys())

def get_task_for_tool(tool: str) -> dict:
    """Get the task definition for a specific tool.

    Args:
        tool: MCP tool name

    Returns:
        Task definition dict with task, description, expected_duration, and validation_keywords

    Raises:
        KeyError: If tool is not in the task definitions
    """
    if tool not in MCP_AGENT_TASKS:
        raise KeyError(f"No task definition found for tool: {tool}")
    return MCP_AGENT_TASKS[tool]

def get_all_tool_names() -> list:
    """Get list of all MCP tools with defined tasks.

    Returns:
        List of tool names
    """
    return ACTIVE_MCPS.copy()

def validate_task_result(tool: str, result_text: str) -> tuple:
    """Validate if a task result contains expected keywords.

    Args:
        tool: MCP tool name
        result_text: Text result from task execution

    Returns:
        Tuple of (is_valid: bool, matched_keywords: list, missing_keywords: list)
    """
    if tool not in MCP_AGENT_TASKS:
        return False, [], []

    task_def = MCP_AGENT_TASKS[tool]
    validation_keywords = task_def.get("validation_keywords", [])

    result_lower = result_text.lower()
    matched = []
    missing = []

    for keyword in validation_keywords:
        if keyword.lower() in result_lower:
            matched.append(keyword)
        else:
            missing.append(keyword)

    # Consider valid if at least 1 keyword matches (flexible validation)
    is_valid = len(matched) > 0

    return is_valid, matched, missing

if __name__ == "__main__":
    # Print all task definitions for review
    print("=" * 70)
    print("MCP AGENT TASK DEFINITIONS")
    print("=" * 70)
    print(f"\nTotal MCP Tools: {len(ACTIVE_MCPS)}\n")

    for idx, tool in enumerate(ACTIVE_MCPS, 1):
        task_def = MCP_AGENT_TASKS[tool]
        print(f"[{idx}/{len(ACTIVE_MCPS)}] {tool.upper()}")
        print(f"  Task: {task_def['task']}")
        print(f"  Description: {task_def['description']}")
        print(f"  Expected Duration: {task_def['expected_duration']}s")
        print(f"  Validation Keywords: {', '.join(task_def['validation_keywords'])}")
        print()
