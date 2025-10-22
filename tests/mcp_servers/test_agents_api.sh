#!/bin/bash
# Test script for all MCP agents via REST API
# This script creates sessions and tests each agent via the GUI API

API_BASE="http://127.0.0.1:8765/api"

echo "==========================================="
echo "MCP Agent OpenRouter Integration API Tests"
echo "==========================================="
echo ""

# Function to test an agent
test_agent() {
    local agent_name=$1
    local task=$2
    local expected_model=$3

    echo "Testing: $agent_name"
    echo "Task: $task"
    echo "Expected model: $expected_model"
    echo ""

    # Create session
    session_response=$(curl -s -X POST "$API_BASE/sessions" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"test-$agent_name\", \"model\": \"gpt-4\", \"tools\": [\"$agent_name\"], \"task\": \"$task\"}")

    session_id=$(echo $session_response | grep -oP '"session_id":\s*"\K[^"]+')

    if [ -z "$session_id" ]; then
        echo "✗ Failed to create session"
        echo "Response: $session_response"
        echo ""
        return 1
    fi

    echo "✓ Session created: $session_id"

    # Start session
    start_response=$(curl -s -X POST "$API_BASE/sessions/$session_id/start" \
        -H "Content-Type: application/json" \
        -d "{}")

    pid=$(echo $start_response | grep -oP '"pid":\s*\K[0-9]+')

    if [ -z "$pid" ]; then
        echo "✗ Failed to start session"
        echo "Response: $start_response"
        echo ""
        return 1
    fi

    echo "✓ Session started (PID: $pid)"

    # Wait for events
    sleep 5

    # Check events
    events_response=$(curl -s "$API_BASE/mcp/$agent_name/sessions/$session_id/events")

    # Check if OpenRouter model was used
    if echo "$events_response" | grep -q "OpenRouter.*Using model.*$expected_model"; then
        echo "✓ Correct model selected: $expected_model"
    elif echo "$events_response" | grep -q "OpenRouter"; then
        actual_model=$(echo "$events_response" | grep -oP 'Using model:\s*\K[^\s"]+' | head -1)
        echo "⚠ Different model used: $actual_model (expected: $expected_model)"
    else
        echo "⚠ OpenRouter not used (fallback to legacy)"
    fi

    # Check for errors
    error_count=$(echo "$events_response" | grep -c '"type": "error"')
    if [ "$error_count" -gt 0 ]; then
        echo "⚠ $error_count errors detected"
    fi

    echo ""
    return 0
}

# Test each agent
echo "1. GitHub Agent - Simple Task"
test_agent "github" "List popular Python repositories" "gpt-4o-mini"

echo "2. GitHub Agent - Reasoning Task"
test_agent "github" "Analyze the architecture of microsoft/vscode" "o1-mini"

echo "3. Docker Agent - Simple Task"
test_agent "docker" "List running containers" "gpt-4o-mini"

echo "4. Playwright Agent - Simple Task"
test_agent "playwright" "Navigate to google.com" "gpt-4o"

echo "5. Context7 Agent - Simple Task"
test_agent "context7" "Search for React documentation" "gpt-4o"

echo "6. Supabase Agent - Simple Task"
test_agent "supabase" "List all tables" "gpt-4o-mini"

echo "7. Redis Agent - Simple Task"
test_agent "redis" "Get all keys" "gpt-4o-mini"

echo "8. Desktop Agent - Simple Task"
test_agent "desktop" "List files in current directory" "gpt-4o-mini"

echo "9. Windows Automation Agent - Simple Task"
test_agent "windows-automation" "Open Notepad" "gpt-4o"

echo "==========================================="
echo "Tests Complete"
echo "==========================================="
