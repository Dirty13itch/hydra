# Speculative Decoding Evaluation

## Overview

Speculative decoding uses a smaller "draft" model to predict multiple tokens, which are then verified in parallel by the main model. This can achieve **50-200% speedup** with no quality loss.

## Current State

| Component | Status |
|-----------|--------|
| ExLlamaV2 | Fully supported |
| TabbyAPI | Supported, not enabled |
| Main Model | Midnight-Miqu-70B-v1.5-exl2-2.5bpw |
| Draft Model | None configured |

## Recommended Configuration

### Draft Model Selection

For a 70B main model, optimal draft models:

| Draft Model | Size | Expected Speedup | VRAM Required |
|-------------|------|------------------|---------------|
| TinyLlama-1.1B | 1.1B | ~2x | ~2GB |
| Llama-3.2-1B | 1B | ~2x | ~2GB |
| Qwen2.5-0.5B | 0.5B | ~1.5x | ~1GB |
| Custom distilled | varies | ~2x+ | varies |

**Important**: Draft model must share same tokenizer/vocabulary as main model.

### TabbyAPI Configuration

To enable speculative decoding, update `/opt/tabbyapi/config.yml`:

```yaml
draft:
  draft_model_dir: /mnt/models
  draft_model_name: TinyLlama-1.1B-Chat-v1.0-exl2-4.0bpw
  # Number of tokens to speculate
  draft_rope_scale: 1
  draft_rope_alpha: 1
```

### Draft Model Installation

```bash
# SSH to hydra-ai
ssh typhon@192.168.1.250

# Download TinyLlama EXL2 draft model
cd /mnt/models
huggingface-cli download turboderp/TinyLlama-1.1B-Chat-v1.0-exl2-4.0bpw --local-dir TinyLlama-1.1B-Chat-v1.0-exl2-4.0bpw

# Or for Llama-3.2-1B (if using Llama-based main model)
# huggingface-cli download bartowski/Llama-3.2-1B-Instruct-exl2 --local-dir Llama-3.2-1B-Instruct-exl2
```

### VRAM Considerations

Current VRAM allocation:
- RTX 5090: 32GB
- RTX 4090: 24GB
- Total: 56GB

Model VRAM usage (2.5bpw 70B):
- Weights: ~22GB
- KV Cache (Q4, 16K ctx): ~4GB
- Overhead: ~2GB
- **Available for draft**: ~28GB

A 1.1B draft model adds ~2-3GB, well within headroom.

## Expected Performance

### Current (No Speculative Decoding)
- Tokens/sec: ~25-30 tok/s

### With Speculative Decoding (TinyLlama draft)
- Expected: ~45-60 tok/s (1.5-2x improvement)

## Risks and Considerations

1. **Tokenizer mismatch**: Draft model MUST share tokenizer with main model
   - Midnight-Miqu uses Mistral tokenizer
   - TinyLlama uses LLaMA tokenizer
   - **May need Mistral-based draft model instead**

2. **VRAM pressure**: Monitor with nvidia-smi during testing

3. **Latency variance**: First-token latency may increase slightly

## Alternative: N-gram Speculative Decoding

ExLlamaV2 also supports n-gram based speculation:
- No draft model needed
- Works by reusing cached ngrams from prompt
- Particularly effective for code completion tasks
- Enable via `ngram_decoding: true` in config

## Action Plan

1. **Phase 1**: Download Mistral-based draft model
2. **Phase 2**: Enable in config with conservative settings
3. **Phase 3**: Benchmark comparison (with/without speculation)
4. **Phase 4**: Tune speculation parameters for optimal throughput

## Resources

- [ExLlamaV2 GitHub](https://github.com/turboderp-org/exllamav2)
- [TabbyAPI Wiki](https://github.com/theroyallab/tabbyAPI/wiki)
- [Speculative Decoding Paper](https://arxiv.org/abs/2402.01528)
