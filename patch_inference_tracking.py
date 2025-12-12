#!/usr/bin/env python3
"""Patch script to add enhanced inference request tracking to MCP server.

This adds:
- Request latency tracking
- Token counting from LiteLLM response
- Prometheus metrics for inference requests
- Inference statistics endpoint
"""

# New imports and metrics tracking code
IMPORTS_ADDITION = '''
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
'''

INFERENCE_METRICS_CODE = '''
# =============================================================================
# Inference Metrics and Statistics
# =============================================================================

# Prometheus metrics for inference
inference_requests_total = Counter(
    'hydra_inference_requests_total',
    'Total inference requests',
    ['model', 'status']
)

inference_latency_seconds = Histogram(
    'hydra_inference_latency_seconds',
    'Inference request latency in seconds',
    ['model'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
)

inference_tokens_total = Counter(
    'hydra_inference_tokens_total',
    'Total tokens processed',
    ['model', 'type']  # type: input or output
)

active_inference_requests = Gauge(
    'hydra_active_inference_requests',
    'Currently active inference requests'
)

# In-memory inference statistics
inference_stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_latency_seconds": 0.0,
    "requests_by_model": {},
    "recent_requests": []  # Last 100 requests
}
MAX_RECENT_REQUESTS = 100
'''

ENHANCED_COMPLETE_ENDPOINT = '''
@app.post("/inference/complete")
async def complete(prompt: str, model: str = "hydra-70b", max_tokens: int = 500, request: Request = None):
    """Generate completion via LiteLLM with enhanced tracking"""
    ip = request.client.host if request and request.client else "unknown"

    if not check_rate_limit(ip, "inference"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for inference")

    start_time = time.time()
    active_inference_requests.inc()
    inference_stats["total_requests"] += 1

    # Initialize model stats if needed
    if model not in inference_stats["requests_by_model"]:
        inference_stats["requests_by_model"][model] = {
            "count": 0, "success": 0, "failed": 0,
            "total_latency": 0, "input_tokens": 0, "output_tokens": 0
        }

    inference_stats["requests_by_model"][model]["count"] += 1

    request_record = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "prompt_length": len(prompt),
        "ip": ip,
        "status": "pending"
    }

    try:
        headers = {
            "Authorization": f"Bearer {LITELLM_KEY}",
            "Content-Type": "application/json"
        }
        r = await client.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            },
            timeout=120.0
        )

        latency = time.time() - start_time
        result = r.json()

        # Extract token usage from LiteLLM response
        usage = result.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # Update Prometheus metrics
        inference_requests_total.labels(model=model, status="success").inc()
        inference_latency_seconds.labels(model=model).observe(latency)
        inference_tokens_total.labels(model=model, type="input").inc(input_tokens)
        inference_tokens_total.labels(model=model, type="output").inc(output_tokens)

        # Update in-memory stats
        inference_stats["successful_requests"] += 1
        inference_stats["total_input_tokens"] += input_tokens
        inference_stats["total_output_tokens"] += output_tokens
        inference_stats["total_latency_seconds"] += latency
        inference_stats["requests_by_model"][model]["success"] += 1
        inference_stats["requests_by_model"][model]["total_latency"] += latency
        inference_stats["requests_by_model"][model]["input_tokens"] += input_tokens
        inference_stats["requests_by_model"][model]["output_tokens"] += output_tokens

        # Update request record
        request_record.update({
            "status": "success",
            "latency_seconds": round(latency, 3),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        })

        add_audit_entry("inference", {
            "model": model,
            "prompt_length": len(prompt),
            "latency_seconds": round(latency, 3),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }, "success", ip)

        return result

    except Exception as e:
        latency = time.time() - start_time
        inference_requests_total.labels(model=model, status="error").inc()
        inference_latency_seconds.labels(model=model).observe(latency)

        inference_stats["failed_requests"] += 1
        inference_stats["requests_by_model"][model]["failed"] += 1

        request_record.update({
            "status": "error",
            "latency_seconds": round(latency, 3),
            "error": str(e)
        })

        add_audit_entry("inference", {
            "model": model,
            "prompt_length": len(prompt),
            "latency_seconds": round(latency, 3),
            "error": str(e)
        }, "error", ip)

        return {"error": str(e)}

    finally:
        active_inference_requests.dec()

        # Add to recent requests
        inference_stats["recent_requests"].append(request_record)
        if len(inference_stats["recent_requests"]) > MAX_RECENT_REQUESTS:
            inference_stats["recent_requests"].pop(0)


@app.get("/inference/stats")
async def get_inference_stats():
    """Get inference request statistics"""
    total = inference_stats["total_requests"]
    avg_latency = (inference_stats["total_latency_seconds"] / total) if total > 0 else 0

    return {
        "total_requests": total,
        "successful_requests": inference_stats["successful_requests"],
        "failed_requests": inference_stats["failed_requests"],
        "success_rate": round(inference_stats["successful_requests"] / total * 100, 1) if total > 0 else 0,
        "total_input_tokens": inference_stats["total_input_tokens"],
        "total_output_tokens": inference_stats["total_output_tokens"],
        "average_latency_seconds": round(avg_latency, 3),
        "requests_by_model": inference_stats["requests_by_model"],
        "recent_requests": inference_stats["recent_requests"][-20:]  # Last 20
    }


@app.get("/metrics")
async def prometheus_metrics():
    """Expose Prometheus metrics endpoint"""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
'''

import re

# Read the current server file
with open("/app/mcp_server.py", "r") as f:
    content = f.read()

# Check if already patched
if "inference_requests_total" in content:
    print("Inference tracking already enhanced - no patch needed")
    exit(0)

# Add prometheus imports if not present
if "prometheus_client" not in content:
    # Add import after existing imports
    import_pos = content.find("from collections import")
    if import_pos > 0:
        end_of_line = content.find("\n", import_pos)
        content = content[:end_of_line+1] + IMPORTS_ADDITION + content[end_of_line+1:]
        print("Added prometheus_client import")

# Add metrics code after the safety layer section
safety_marker = "PROTECTED_CONTAINERS = {"
safety_pos = content.find(safety_marker)
if safety_pos > 0:
    # Find end of PROTECTED_CONTAINERS set
    end_pos = content.find("}", safety_pos)
    insert_pos = content.find("\n", end_pos) + 1
    content = content[:insert_pos] + INFERENCE_METRICS_CODE + "\n" + content[insert_pos:]
    print("Added inference metrics code")

# Replace the existing /inference/complete endpoint
old_complete_pattern = r'@app\.post\("/inference/complete"\)\nasync def complete\([^)]+\):.*?(?=\n@app\.|# ====|$)'
if re.search(old_complete_pattern, content, re.DOTALL):
    content = re.sub(old_complete_pattern, ENHANCED_COMPLETE_ENDPOINT.strip() + "\n\n", content, flags=re.DOTALL)
    print("Replaced /inference/complete endpoint with enhanced version")
else:
    # If pattern not found, try inserting before a marker
    marker = "# =============================================================================\n# Audit and Admin"
    pos = content.find(marker)
    if pos > 0:
        content = content[:pos] + ENHANCED_COMPLETE_ENDPOINT + "\n\n" + content[pos:]
        print("Inserted enhanced inference endpoints before Audit section")

# Write the updated file
with open("/app/mcp_server.py", "w") as f:
    f.write(content)

print("Inference tracking patch applied successfully")
print(f"File size: {len(content)} bytes")
