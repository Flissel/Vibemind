#!/bin/bash
# VibeMind 5-Instance VibeCoding Launcher
# Launch 5 Claude Code instances for simultaneous development

VIBEMIND_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Launching VibeMind 5-Instance VibeCoding Setup..."

# Instance 1: VibeMind Root (Integration & Coordination)
echo -e "\n[1/5] Launching VibeMind Root (Integration)..."
code "$VIBEMIND_ROOT" &
sleep 2

# Instance 2: Sakana Desktop Assistant (AI Core)
echo "[2/5] Launching Sakana Desktop Assistant..."
code "$VIBEMIND_ROOT/sakana-desktop-assistant" &
sleep 2

# Instance 3: The Brain (Cognitive Architecture)
echo "[3/5] Launching The Brain (ATM-R)..."
code "$VIBEMIND_ROOT/the_brain" &
sleep 2

# Instance 4: MoireTracker (Desktop Automation)
echo "[4/5] Launching MoireTracker..."
code "$VIBEMIND_ROOT/MoireTracker" &
sleep 2

# Instance 5: Electron + Voice Dialog (UI Layer)
echo "[5/5] Launching Electron Voice UI..."
code "$VIBEMIND_ROOT/electron" &
sleep 1

echo -e "\n✅ All 5 VibeCoding instances launched!"
echo -e "\nInstance Assignments:"
echo "  1️⃣  VibeMind Root      → Integration, docs, submodule coordination"
echo "  2️⃣  Sakana            → AI core, MCP agents, learning systems"
echo "  3️⃣  The Brain         → ATM-R cognitive architecture"
echo "  4️⃣  MoireTracker      → C++ desktop automation engine"
echo "  5️⃣  Electron          → Voice UI and dialog orchestration"
echo -e "\n💡 Tip: Keep Instance 1 for cross-submodule coordination"
