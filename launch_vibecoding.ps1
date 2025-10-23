# VibeMind 5-Instance VibeCoding Launcher
# Launch 5 Claude Code instances for simultaneous development

$VIBEMIND_ROOT = $PSScriptRoot

Write-Host "🚀 Launching VibeMind 5-Instance VibeCoding Setup..." -ForegroundColor Cyan

# Instance 1: VibeMind Root (Integration & Coordination)
Write-Host "`n[1/5] Launching VibeMind Root (Integration)..." -ForegroundColor Green
Start-Process code -ArgumentList "$VIBEMIND_ROOT"
Start-Sleep -Seconds 2

# Instance 2: Sakana Desktop Assistant (AI Core)
Write-Host "[2/5] Launching Sakana Desktop Assistant..." -ForegroundColor Green
Start-Process code -ArgumentList "$VIBEMIND_ROOT\sakana-desktop-assistant"
Start-Sleep -Seconds 2

# Instance 3: The Brain (Cognitive Architecture)
Write-Host "[3/5] Launching The Brain (ATM-R)..." -ForegroundColor Green
Start-Process code -ArgumentList "$VIBEMIND_ROOT\the_brain"
Start-Sleep -Seconds 2

# Instance 4: MoireTracker (Desktop Automation)
Write-Host "[4/5] Launching MoireTracker..." -ForegroundColor Green
Start-Process code -ArgumentList "$VIBEMIND_ROOT\MoireTracker"
Start-Sleep -Seconds 2

# Instance 5: Electron + Voice Dialog (UI Layer)
Write-Host "[5/5] Launching Electron Voice UI..." -ForegroundColor Green
Start-Process code -ArgumentList "$VIBEMIND_ROOT\electron"
Start-Sleep -Seconds 1

Write-Host "`n✅ All 5 VibeCoding instances launched!" -ForegroundColor Cyan
Write-Host "`nInstance Assignments:" -ForegroundColor Yellow
Write-Host "  1️⃣  VibeMind Root      → Integration, docs, submodule coordination"
Write-Host "  2️⃣  Sakana            → AI core, MCP agents, learning systems"
Write-Host "  3️⃣  The Brain         → ATM-R cognitive architecture"
Write-Host "  4️⃣  MoireTracker      → C++ desktop automation engine"
Write-Host "  5️⃣  Electron          → Voice UI and dialog orchestration"
Write-Host "`n💡 Tip: Keep Instance 1 for cross-submodule coordination" -ForegroundColor Gray
