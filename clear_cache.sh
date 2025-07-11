#!/bin/bash
# Clear Sakana cache to force rediscovery

echo "🧹 Clearing Sakana cache..."

# Remove default cache locations
rm -rf ~/.sakana/cache/*
rm -rf data/cache/*

echo "✓ Cache cleared. Commands will be rediscovered on next run."
echo ""
echo "Note: First run after clearing cache will take 2-3 minutes"
echo "      as the system rediscovers available commands."