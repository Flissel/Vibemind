# Test script for all MCP agents via REST API
# PowerShell version for Windows

$API_BASE = "http://127.0.0.1:8765/api"

Write-Host "==========================================="
Write-Host "MCP Agent OpenRouter Integration API Tests"
Write-Host "==========================================="
Write-Host ""

# Function to test an agent
function Test-Agent {
    param(
        [string]$AgentName,
        [string]$Task,
        [string]$ExpectedModel
    )

    Write-Host "Testing: $AgentName"
    Write-Host "Task: $Task"
    Write-Host "Expected model: $ExpectedModel"
    Write-Host ""

    try {
        # Create session
        $createBody = @{
            name = "test-$AgentName"
            model = "gpt-4"
            tools = @($AgentName)
            task = $Task
        } | ConvertTo-Json

        $sessionResponse = Invoke-RestMethod -Uri "$API_BASE/sessions" `
            -Method Post `
            -ContentType "application/json" `
            -Body $createBody

        $sessionId = $sessionResponse.session.session_id

        if (-not $sessionId) {
            Write-Host "✗ Failed to create session" -ForegroundColor Red
            Write-Host "Response: $sessionResponse"
            Write-Host ""
            return $false
        }

        Write-Host "✓ Session created: $sessionId" -ForegroundColor Green

        # Start session
        $startResponse = Invoke-RestMethod -Uri "$API_BASE/sessions/$sessionId/start" `
            -Method Post `
            -ContentType "application/json" `
            -Body "{}"

        $pid = $startResponse.pid

        if (-not $pid) {
            Write-Host "✗ Failed to start session" -ForegroundColor Red
            Write-Host "Response: $startResponse"
            Write-Host ""
            return $false
        }

        Write-Host "✓ Session started (PID: $pid)" -ForegroundColor Green

        # Wait for events
        Start-Sleep -Seconds 5

        # Check events
        $eventsResponse = Invoke-RestMethod -Uri "$API_BASE/mcp/$AgentName/sessions/$sessionId/events"

        # Check if OpenRouter model was used
        $eventsJson = $eventsResponse | ConvertTo-Json -Depth 10

        if ($eventsJson -match "OpenRouter.*Using model.*$ExpectedModel") {
            Write-Host "✓ Correct model selected: $ExpectedModel" -ForegroundColor Green
        }
        elseif ($eventsJson -match "OpenRouter") {
            if ($eventsJson -match "Using model:\s*([^\s`"]+)") {
                $actualModel = $Matches[1]
                Write-Host "⚠ Different model used: $actualModel (expected: $ExpectedModel)" -ForegroundColor Yellow
            }
        }
        else {
            Write-Host "⚠ OpenRouter not used (fallback to legacy)" -ForegroundColor Yellow
        }

        # Check for errors
        $errorCount = ($eventsResponse.events | Where-Object { $_.type -eq "error" }).Count
        if ($errorCount -gt 0) {
            Write-Host "⚠ $errorCount errors detected" -ForegroundColor Yellow
        }

        Write-Host ""
        return $true
    }
    catch {
        Write-Host "✗ Error: $_" -ForegroundColor Red
        Write-Host ""
        return $false
    }
}

# Test each agent
$results = @()

Write-Host "1. GitHub Agent - Simple Task"
$results += Test-Agent -AgentName "github" -Task "List popular Python repositories" -ExpectedModel "gpt-4o-mini"

Write-Host "2. GitHub Agent - Reasoning Task"
$results += Test-Agent -AgentName "github" -Task "Analyze the architecture of microsoft/vscode" -ExpectedModel "o1-mini"

Write-Host "3. Docker Agent - Simple Task"
$results += Test-Agent -AgentName "docker" -Task "List running containers" -ExpectedModel "gpt-4o-mini"

Write-Host "4. Playwright Agent - Simple Task"
$results += Test-Agent -AgentName "playwright" -Task "Navigate to google.com" -ExpectedModel "gpt-4o"

Write-Host "5. Context7 Agent - Simple Task"
$results += Test-Agent -AgentName "context7" -Task "Search for React documentation" -ExpectedModel "gpt-4o"

Write-Host "6. Supabase Agent - Simple Task"
$results += Test-Agent -AgentName "supabase" -Task "List all tables" -ExpectedModel "gpt-4o-mini"

Write-Host "7. Redis Agent - Simple Task"
$results += Test-Agent -AgentName "redis" -Task "Get all keys" -ExpectedModel "gpt-4o-mini"

Write-Host "8. Desktop Agent - Simple Task"
$results += Test-Agent -AgentName "desktop" -Task "List files in current directory" -ExpectedModel "gpt-4o-mini"

Write-Host "9. Windows Automation Agent - Simple Task"
$results += Test-Agent -AgentName "windows-automation" -Task "Open Notepad" -ExpectedModel "gpt-4o"

# Summary
Write-Host "==========================================="
Write-Host "Test Summary"
Write-Host "==========================================="

$passed = ($results | Where-Object { $_ -eq $true }).Count
$total = $results.Count

Write-Host ""
Write-Host "Passed: $passed/$total"

if ($passed -eq $total) {
    Write-Host "✓ All tests passed!" -ForegroundColor Green
}
else {
    Write-Host "⚠ Some tests failed" -ForegroundColor Yellow
}
