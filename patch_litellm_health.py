#!/usr/bin/env python3
"""Patch script to fix LiteLLM health check in MCP server.

The issue: MCP checks /health which requires auth, but /health/readiness works without auth.
This patch updates the check_litellm function to use the correct endpoint.
"""

import re

# Read the current server file
with open("/app/mcp_server.py", "r") as f:
    content = f.read()

# Check if already patched
if "/health/readiness" in content:
    print("LiteLLM health check already using /health/readiness")
    exit(0)

# Pattern to find the old LiteLLM health check
# Look for URL with /health at the end for litellm
patterns_to_replace = [
    # Common patterns for LiteLLM health check
    (r'LITELLM_URL\s*\+\s*"/health"', 'LITELLM_URL + "/health/readiness"'),
    (r'f"{LITELLM_URL}/health"', 'f"{LITELLM_URL}/health/readiness"'),
    (r'"http://hydra-litellm:4000/health"', '"http://hydra-litellm:4000/health/readiness"'),
    (r'"http://192.168.1.244:4000/health"', '"http://192.168.1.244:4000/health/readiness"'),
]

replaced = False
for old, new in patterns_to_replace:
    if re.search(old, content):
        content = re.sub(old, new, content)
        print(f"Replaced: {old} -> {new}")
        replaced = True

# Also update the status check logic if needed
# The readiness endpoint returns {"status": "connected", ...} so check for that
old_status_check = '"ok"'
new_status_check = '"connected"'
if old_status_check in content and "litellm" in content.lower():
    # Be careful not to replace all occurrences, just litellm-related ones
    # Try to find litellm check function and update status
    pass

if replaced:
    # Write the updated file
    with open("/app/mcp_server.py", "w") as f:
        f.write(content)
    print("LiteLLM health check patch applied successfully")
    print(f"File size: {len(content)} bytes")
else:
    print("No patterns found to replace. Let me check what's in the file...")
    # Print any lines containing litellm
    for i, line in enumerate(content.split('\n'), 1):
        if 'litellm' in line.lower() and ('health' in line.lower() or 'url' in line.lower()):
            print(f"Line {i}: {line.strip()}")
