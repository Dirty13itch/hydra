#!/usr/bin/env python3
"""Test script for ComfyUI MCP server functions."""

import sys
sys.path.insert(0, '/mnt/user/appdata/hydra-dev/mcp-servers/comfyui')

from server import get_queue_status, get_history, get_system_stats
import json

print("Testing ComfyUI MCP Server...")
print("=" * 50)

print("\n1. Queue Status:")
result = get_queue_status()
print(json.dumps(result, indent=2))

print("\n2. System Stats:")
result = get_system_stats()
print(json.dumps(result, indent=2))

print("\n3. History (last 3):")
result = get_history(3)
print(json.dumps(result, indent=2))

print("\n" + "=" * 50)
print("All tests completed!")
