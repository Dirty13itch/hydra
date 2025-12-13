#!/usr/bin/env python3
"""Patch script to fix GPU metrics collection in MCP server.

The issue: MCP queries 'nvidia_gpu_utilization' but DCGM exports 'DCGM_FI_DEV_GPU_UTIL'
This patch updates the gpu_status endpoint to use correct DCGM metric names.
"""

# New GPU status endpoint code that uses DCGM metrics
GPU_STATUS_CODE = '''
# =============================================================================
# GPU Status Endpoint (DCGM Metrics)
# =============================================================================

@app.get("/gpu/status")
async def gpu_status():
    """Get GPU metrics from Prometheus (DCGM exporter)"""
    gpus = []

    try:
        # Query GPU utilization from DCGM
        r = await client.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": "DCGM_FI_DEV_GPU_UTIL"}
        )
        if r.status_code == 200:
            data = r.json()
            results = data.get("data", {}).get("result", [])

            for item in results:
                metric = item.get("metric", {})
                value = item.get("value", [0, "0"])

                gpu = {
                    "index": metric.get("gpu", ""),
                    "name": metric.get("modelName", "Unknown GPU"),
                    "node": metric.get("node", metric.get("instance", "unknown")),
                    "uuid": metric.get("UUID", ""),
                    "utilization": float(value[1]) if len(value) > 1 else 0,
                }
                gpus.append(gpu)

        # Enrich with temperature
        r = await client.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": "DCGM_FI_DEV_GPU_TEMP"}
        )
        if r.status_code == 200:
            data = r.json()
            for item in data.get("data", {}).get("result", []):
                metric = item.get("metric", {})
                value = item.get("value", [0, "0"])
                gpu_id = metric.get("gpu", "")

                for gpu in gpus:
                    if gpu["index"] == gpu_id:
                        gpu["temperature"] = float(value[1]) if len(value) > 1 else 0
                        break

        # Enrich with memory usage
        r = await client.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": "DCGM_FI_DEV_FB_USED"}
        )
        if r.status_code == 200:
            data = r.json()
            for item in data.get("data", {}).get("result", []):
                metric = item.get("metric", {})
                value = item.get("value", [0, "0"])
                gpu_id = metric.get("gpu", "")

                for gpu in gpus:
                    if gpu["index"] == gpu_id:
                        gpu["memory_used_mb"] = float(value[1]) if len(value) > 1 else 0
                        break

        # Enrich with power usage
        r = await client.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": "DCGM_FI_DEV_POWER_USAGE"}
        )
        if r.status_code == 200:
            data = r.json()
            for item in data.get("data", {}).get("result", []):
                metric = item.get("metric", {})
                value = item.get("value", [0, "0"])
                gpu_id = metric.get("gpu", "")

                for gpu in gpus:
                    if gpu["index"] == gpu_id:
                        gpu["power_watts"] = float(value[1]) if len(value) > 1 else 0
                        break

    except Exception as e:
        return {"gpus": [], "error": str(e)}

    add_audit_entry("gpu_status", {"gpu_count": len(gpus)}, "success", "monitoring")
    return {"gpus": gpus}
'''

# Read the current server file
with open("/app/mcp_server.py", "r") as f:
    content = f.read()

# Check if already patched
if "DCGM_FI_DEV_GPU_UTIL" in content:
    print("GPU metrics already using DCGM - no patch needed")
    exit(0)

# Find and replace the old gpu_status function
import re

# Pattern to match the old gpu_status function
old_pattern = r'@app\.get\("/gpu/status"\)\s*\nasync def gpu_status\(\):.*?(?=\n@app\.|# =====|\nif __name__|$)'

# Check if we can find the old function
if re.search(old_pattern, content, re.DOTALL):
    content = re.sub(old_pattern, GPU_STATUS_CODE.strip() + "\n\n", content, flags=re.DOTALL)
    print("Replaced existing gpu_status function with DCGM version")
else:
    # If pattern not found, try to insert before WebSocket or main
    insert_markers = [
        "# =============================================================================\n# WebSocket",
        'if __name__ == "__main__":'
    ]

    inserted = False
    for marker in insert_markers:
        pos = content.find(marker)
        if pos > 0:
            content = content[:pos] + GPU_STATUS_CODE + "\n\n" + content[pos:]
            print(f"Inserted GPU status code before: {marker[:40]}...")
            inserted = True
            break

    if not inserted:
        print("Could not find insertion point for GPU status code")
        exit(1)

# Write the updated file
with open("/app/mcp_server.py", "w") as f:
    f.write(content)

print("GPU metrics patch applied successfully")
print(f"File size: {len(content)} bytes")
