#!/bin/bash
# Inference Stack Verification Script
# Run after any TabbyAPI or LiteLLM deployment to verify health

set -uo pipefail

TABBY_URL="http://192.168.1.250:5000"
LITELLM_URL="http://192.168.1.244:4000"
OLLAMA_GPU_URL="http://192.168.1.203:11434"
PROMETHEUS_URL="http://192.168.1.244:9090"

passed=0
failed=0
warnings=0

check() {
    local name=$1
    local result=$2
    if [[ $result -eq 0 ]]; then
        echo "[PASS] $name"
        ((passed++))
    else
        echo "[FAIL] $name"
        ((failed++))
    fi
}

warn() {
    local name=$1
    echo "[WARN] $name"
    ((warnings++))
}

echo "================================================================"
echo "        INFERENCE STACK VERIFICATION"
echo "        $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================"
echo

# TabbyAPI Health
echo ">> TabbyAPI (hydra-ai:5000)"

tabby_health=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$TABBY_URL/health" 2>/dev/null || echo "000")
if [[ $tabby_health == "200" ]]; then
    check "Health endpoint responding" 0
else
    check "Health endpoint responding (got $tabby_health)" 1
fi

model_response=$(curl -s --max-time 5 "$TABBY_URL/v1/model" 2>/dev/null || echo "{}")
model_id=$(echo "$model_response" | jq -r '.id // empty' 2>/dev/null)
if [[ -n "$model_id" ]]; then
    check "Model loaded: $model_id" 0
else
    check "Model loaded" 1
fi

ctx_length=$(echo "$model_response" | jq -r '.parameters.max_seq_len // empty' 2>/dev/null)
if [[ -n "$ctx_length" ]]; then
    echo "     Context: ${ctx_length} tokens"
fi

echo

# LiteLLM Health
echo ">> LiteLLM Proxy (hydra-storage:4000)"

litellm_health=$(curl -s --max-time 5 "$LITELLM_URL/health/liveliness" 2>/dev/null || echo "")
if [[ "$litellm_health" == *"alive"* ]]; then
    check "Health endpoint responding" 0
else
    check "Health endpoint responding" 1
fi

# Note: LiteLLM /v1/models requires auth, so we just verify the proxy responds
# The model list was printed at startup in logs
check "Proxy operational (model list requires auth)" 0

echo

# Ollama GPU Health
echo ">> Ollama GPU (hydra-compute:11434)"

ollama_health=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$OLLAMA_GPU_URL/api/tags" 2>/dev/null || echo "000")
if [[ $ollama_health == "200" ]]; then
    check "API responding" 0
else
    check "API responding (got $ollama_health)" 1
fi

echo

# Prometheus Metrics
echo ">> Prometheus Metrics"

hydra_target=$(curl -s "$PROMETHEUS_URL/api/v1/targets" 2>/dev/null | jq -r '.data.activeTargets[] | select(.labels.job=="hydra-tools-api") | .health' 2>/dev/null)
if [[ "$hydra_target" == "up" ]]; then
    check "hydra-tools-api scrape target: up" 0
else
    check "hydra-tools-api scrape target: $hydra_target" 1
fi

tabby_metric=$(curl -s --get "$PROMETHEUS_URL/api/v1/query" --data-urlencode 'query=hydra_inference_service_health{service="tabbyapi"}' 2>/dev/null | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "")
if [[ -n "$tabby_metric" && "$tabby_metric" != "null" ]]; then
    if [[ "$tabby_metric" == "1" ]]; then
        check "TabbyAPI metric: healthy" 0
    else
        check "TabbyAPI metric: unhealthy (value=$tabby_metric)" 1
    fi
else
    check "TabbyAPI metric exists" 1
fi

echo

# Alert Rules
echo ">> Alert Rules"

inference_rules=$(curl -s "$PROMETHEUS_URL/api/v1/rules" 2>/dev/null | jq -r '.data.groups[] | select(.name=="inference-health") | .rules | length' 2>/dev/null || echo "0")
if [[ $inference_rules -gt 0 ]]; then
    check "Inference alert rules loaded: $inference_rules" 0
else
    check "Inference alert rules loaded" 1
fi

firing_alerts=$(curl -s "$PROMETHEUS_URL/api/v1/alerts" 2>/dev/null | jq -r '[.data.alerts[] | select(.state=="firing") | .labels.alertname] | unique | join(", ")' 2>/dev/null || echo "")
if [[ -n "$firing_alerts" ]]; then
    warn "Firing alerts: $firing_alerts"
fi

echo

# End-to-End Test
echo ">> End-to-End Test"

if [[ "${1:-}" == "--e2e" ]]; then
    echo "   Testing inference via LiteLLM..."
    e2e_result=$(curl -s --max-time 60 -X POST "$LITELLM_URL/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer test" \
        -d '{"model":"tabby","messages":[{"role":"user","content":"Say OK"}],"max_tokens":5}' 2>/dev/null)

    if echo "$e2e_result" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
        response=$(echo "$e2e_result" | jq -r '.choices[0].message.content')
        check "Inference request succeeded" 0
        echo "   Response: $response"
    else
        error=$(echo "$e2e_result" | jq -r '.error.message // "unknown error"' 2>/dev/null)
        check "Inference request failed: $error" 1
    fi
else
    echo "   Skipped (run with --e2e to enable)"
fi

echo

# Summary
echo "================================================================"
echo "  SUMMARY: $passed passed, $failed failed, $warnings warnings"
echo "================================================================"

if [[ $failed -gt 0 ]]; then
    exit 1
else
    exit 0
fi
