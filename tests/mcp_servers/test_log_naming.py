#!/usr/bin/env python3
"""Test log file naming for all MCP tools"""
import requests
import json
import time

# Read servers config
with open('servers.json') as f:
    servers_data = json.load(f)

backend_url = 'http://127.0.0.1:8765'
tools = [s['name'] for s in servers_data['servers'] if s.get('active', False)]

print(f'Testing log naming for {len(tools)} MCP tools...\n')

created_sessions = []

for tool in tools:
    try:
        # Create session
        resp = requests.post(f'{backend_url}/api/sessions',
            json={'tool': tool, 'name': f'test-{tool}'},
            timeout=5)

        if resp.status_code == 200:
            data = resp.json()
            session_id = data.get('session_id')
            created_sessions.append((tool, session_id))
            print(f'[OK] {tool:20s} session: {session_id}')
        else:
            print(f'[FAIL] {tool:20s} failed: {resp.status_code}')
    except Exception as e:
        print(f'[ERROR] {tool:20s} error: {e}')

print(f'\nCreated {len(created_sessions)} sessions. Checking log files...\n')

# Check log files
import os
log_dir = '../../../data/logs/sessions'
log_files = sorted(os.listdir(log_dir))

print('Log files created:')
for f in log_files:
    if f.endswith('.log'):
        # Parse filename to check format
        parts = f.replace('.log', '').split('_')
        if len(parts) >= 3:
            tool_name = parts[0]
            timestamp = f'{parts[1]}_{parts[2]}'
            session_id = '_'.join(parts[3:])
            print(f'  [OK] {tool_name:15s} {timestamp} {session_id}')
        else:
            print(f'  [OLD FORMAT] {f}')

print(f'\nTotal log files: {len([f for f in log_files if f.endswith(".log")])}')
print(f'Expected: {len(created_sessions)}')

# Cleanup
print('\nCleaning up sessions...')
for tool, session_id in created_sessions:
    try:
        requests.delete(f'{backend_url}/api/sessions/{session_id}', timeout=2)
    except:
        pass
print('Done!')
