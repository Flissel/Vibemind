#!/bin/bash
# Clear Sakana cache to force rediscovery

echo "🧹 Clearing Sakana cache..."

# Remove default cache locations
rm -rf ~/.sakana/cache/*
rm -rf data/cache/*

echo "✓ Cache cleared. Commands will be rediscovered on next run."
echo ""
echo "Note: Permanent knowledge in ~/.sakana/knowledge is preserved."
echo "      The system will skip commands it already knows from past sessions."
echo "      Only truly new commands will be discovered."
echo ""
echo "To view accumulated knowledge: ./knowledge_report.py"