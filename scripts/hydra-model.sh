#!/bin/bash
# Hydra Model Management Script
#
# Quick commands for managing LLM models on the Hydra cluster.
#
# Usage:
#   ./hydra-model.sh list          - List installed models
#   ./hydra-model.sh load <model>  - Load model in TabbyAPI
#   ./hydra-model.sh pull <repo>   - Download model from HuggingFace
#   ./hydra-model.sh status        - Show current model status

set -euo pipefail

# Configuration
TABBYAPI_HOST="192.168.1.250"
TABBYAPI_PORT="5000"
OLLAMA_HOST="192.168.1.203"
OLLAMA_PORT="11434"
MODEL_DIR="/mnt/user/models"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# List installed models
cmd_list() {
    local type="${1:-all}"

    echo "=== Hydra Model Inventory ==="
    echo

    if [[ "$type" == "all" || "$type" == "exl2" ]]; then
        echo "EXL2 Models (TabbyAPI):"
        echo "------------------------"
        if [[ -d "$MODEL_DIR/exl2" ]]; then
            for model in "$MODEL_DIR/exl2"/*/; do
                if [[ -d "$model" ]]; then
                    name=$(basename "$model")
                    size=$(du -sh "$model" 2>/dev/null | cut -f1)
                    echo "  $name ($size)"
                fi
            done
        else
            echo "  (none found)"
        fi
        echo
    fi

    if [[ "$type" == "all" || "$type" == "gguf" ]]; then
        echo "GGUF Models:"
        echo "------------"
        if [[ -d "$MODEL_DIR/gguf" ]]; then
            for model in "$MODEL_DIR/gguf"/*.gguf; do
                if [[ -f "$model" ]]; then
                    name=$(basename "$model")
                    size=$(du -sh "$model" 2>/dev/null | cut -f1)
                    echo "  $name ($size)"
                fi
            done
        else
            echo "  (none found)"
        fi
        echo
    fi

    if [[ "$type" == "all" || "$type" == "ollama" ]]; then
        echo "Ollama Models (hydra-compute):"
        echo "------------------------------"
        curl -s "http://$OLLAMA_HOST:$OLLAMA_PORT/api/tags" | \
            jq -r '.models[] | "  \(.name) (\(.size / 1073741824 | floor)GB)"' 2>/dev/null || \
            echo "  (Ollama not reachable)"
        echo
    fi
}

# Show current model status
cmd_status() {
    echo "=== Model Status ==="
    echo

    # TabbyAPI
    echo "TabbyAPI (hydra-ai:5000):"
    tabby_model=$(curl -s "http://$TABBYAPI_HOST:$TABBYAPI_PORT/v1/model" 2>/dev/null)
    if [[ -n "$tabby_model" ]]; then
        model_name=$(echo "$tabby_model" | jq -r '.model_name // "none"')
        context=$(echo "$tabby_model" | jq -r '.max_seq_len // "?"')
        log_success "Loaded: $model_name (context: $context)"
    else
        log_error "TabbyAPI not reachable"
    fi
    echo

    # Ollama
    echo "Ollama (hydra-compute:11434):"
    ollama_ps=$(curl -s "http://$OLLAMA_HOST:$OLLAMA_PORT/api/ps" 2>/dev/null)
    if [[ -n "$ollama_ps" ]]; then
        models=$(echo "$ollama_ps" | jq -r '.models[]?.name // empty')
        if [[ -n "$models" ]]; then
            echo "$models" | while read -r m; do
                log_success "Running: $m"
            done
        else
            log_warn "No models currently loaded"
        fi
    else
        log_error "Ollama not reachable"
    fi
    echo

    # GPU Memory
    echo "GPU Memory Usage:"
    echo "  hydra-ai:"
    ssh typhon@$TABBYAPI_HOST "nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader" 2>/dev/null | \
        while read -r line; do echo "    $line"; done || echo "    (unreachable)"

    echo "  hydra-compute:"
    ssh typhon@$OLLAMA_HOST "nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader" 2>/dev/null | \
        while read -r line; do echo "    $line"; done || echo "    (unreachable)"
}

# Load model in TabbyAPI
cmd_load() {
    local model="$1"

    if [[ -z "$model" ]]; then
        log_error "Model name required"
        echo "Usage: $0 load <model-name>"
        echo
        echo "Available models:"
        cmd_list exl2
        exit 1
    fi

    log_info "Loading model: $model"

    # Check if model exists
    if [[ ! -d "$MODEL_DIR/exl2/$model" ]]; then
        log_error "Model not found: $MODEL_DIR/exl2/$model"
        exit 1
    fi

    # Unload current model first
    log_info "Unloading current model..."
    curl -s -X POST "http://$TABBYAPI_HOST:$TABBYAPI_PORT/v1/model/unload" >/dev/null 2>&1 || true
    sleep 2

    # Load new model
    log_info "Loading $model..."
    response=$(curl -s -X POST "http://$TABBYAPI_HOST:$TABBYAPI_PORT/v1/model/load" \
        -H "Content-Type: application/json" \
        -d "{\"model_name\": \"$model\"}")

    if echo "$response" | jq -e '.model_name' >/dev/null 2>&1; then
        loaded=$(echo "$response" | jq -r '.model_name')
        log_success "Model loaded: $loaded"
    else
        log_error "Failed to load model"
        echo "$response" | jq . 2>/dev/null || echo "$response"
        exit 1
    fi
}

# Unload current model
cmd_unload() {
    log_info "Unloading current model..."
    curl -s -X POST "http://$TABBYAPI_HOST:$TABBYAPI_PORT/v1/model/unload"
    log_success "Model unloaded"
}

# Pull model from HuggingFace
cmd_pull() {
    local repo="$1"
    local quant="${2:-}"

    if [[ -z "$repo" ]]; then
        log_error "Repository required"
        echo "Usage: $0 pull <repo> [quantization]"
        echo "Example: $0 pull bartowski/Llama-3.1-70B-Instruct-exl2 4.0bpw"
        exit 1
    fi

    log_info "Downloading from: $repo"

    # Use huggingface-cli if available, otherwise fallback
    if command -v huggingface-cli &>/dev/null; then
        local revision="${quant:-main}"
        huggingface-cli download "$repo" --revision "$revision" --local-dir "$MODEL_DIR/exl2/$(basename "$repo")-$revision"
    else
        log_warn "huggingface-cli not found, using wget"
        echo "Install with: pip install huggingface_hub"
        exit 1
    fi
}

# Pull Ollama model
cmd_pull_ollama() {
    local model="$1"

    if [[ -z "$model" ]]; then
        log_error "Model name required"
        echo "Usage: $0 pull-ollama <model>"
        echo "Example: $0 pull-ollama qwen2.5:14b"
        exit 1
    fi

    log_info "Pulling Ollama model: $model"
    curl -X POST "http://$OLLAMA_HOST:$OLLAMA_PORT/api/pull" \
        -d "{\"name\": \"$model\"}" \
        --no-buffer
}

# Test inference
cmd_test() {
    local backend="${1:-tabby}"
    local prompt="${2:-Hello, how are you?}"

    if [[ "$backend" == "tabby" ]]; then
        log_info "Testing TabbyAPI..."
        response=$(curl -s "http://$TABBYAPI_HOST:$TABBYAPI_PORT/v1/chat/completions" \
            -H "Content-Type: application/json" \
            -d "{
                \"messages\": [{\"role\": \"user\", \"content\": \"$prompt\"}],
                \"max_tokens\": 50
            }")
        echo "$response" | jq -r '.choices[0].message.content // .error // .'
    elif [[ "$backend" == "ollama" ]]; then
        log_info "Testing Ollama..."
        response=$(curl -s "http://$OLLAMA_HOST:$OLLAMA_PORT/api/generate" \
            -d "{
                \"model\": \"qwen2.5:7b\",
                \"prompt\": \"$prompt\",
                \"stream\": false
            }")
        echo "$response" | jq -r '.response // .error // .'
    fi
}

# Main
main() {
    local cmd="${1:-help}"
    shift || true

    case "$cmd" in
        list|ls)
            cmd_list "$@"
            ;;
        status|st)
            cmd_status
            ;;
        load)
            cmd_load "$@"
            ;;
        unload)
            cmd_unload
            ;;
        pull|download)
            cmd_pull "$@"
            ;;
        pull-ollama)
            cmd_pull_ollama "$@"
            ;;
        test)
            cmd_test "$@"
            ;;
        help|-h|--help)
            echo "Hydra Model Manager"
            echo
            echo "Usage: $0 <command> [args]"
            echo
            echo "Commands:"
            echo "  list [type]     List installed models (exl2, gguf, ollama, all)"
            echo "  status          Show current model status and GPU memory"
            echo "  load <model>    Load model in TabbyAPI"
            echo "  unload          Unload current TabbyAPI model"
            echo "  pull <repo> [q] Download EXL2 model from HuggingFace"
            echo "  pull-ollama <m> Pull Ollama model"
            echo "  test [backend]  Test inference (tabby or ollama)"
            echo
            echo "Examples:"
            echo "  $0 list"
            echo "  $0 load Llama-3.1-70B-Instruct-exl2-4.0bpw"
            echo "  $0 pull bartowski/Qwen2.5-72B-Instruct-exl2 4.0bpw"
            echo "  $0 test tabby \"What is 2+2?\""
            ;;
        *)
            log_error "Unknown command: $cmd"
            main help
            exit 1
            ;;
    esac
}

main "$@"
