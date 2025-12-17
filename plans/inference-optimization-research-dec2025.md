# LLM INFERENCE OPTIMIZATION RESEARCH
## Bleeding-Edge Developments for Hydra Cluster
### December 2025 - Deep Dive Analysis

---

## EXECUTIVE SUMMARY

This research document catalogs the latest advances in LLM inference optimization as of December 2025, with specific focus on techniques applicable to Hydra's hardware configuration: RTX 5090 (32GB) + RTX 4090 (24GB) running 70B models via TabbyAPI/ExLlamaV2.

**Key Findings:**
1. **Theoretical Maximum Speedup:** 4.98x via combined speculative decoding + pipeline parallelism
2. **Production-Ready Techniques:** Achieve 2-2.7x speedup today with minimal implementation effort
3. **Hardware Utilization:** RTX 5090's 1.79 TB/s bandwidth enables 29% faster token generation than RTX 4090
4. **Memory Optimization:** KV cache compression can reduce VRAM usage by 30-70% while maintaining quality
5. **Quantization:** Mixed INT4-FP8 provides optimal balance for 70B models on 56GB total VRAM

**Implementation Priority:**
1. **HIGH - Immediate (Week 1):** EXL2 quantization optimization, KV cache configuration
2. **HIGH - Short-term (Weeks 2-4):** Speculative decoding with draft models, FlashAttention-3
3. **MEDIUM - Mid-term (Weeks 5-8):** Advanced KV cache compression, mixed-precision optimization
4. **EXPERIMENTAL - Long-term (Weeks 9-12):** Sparse attention, ExLlamaV3 migration

---

## 1. SPECULATIVE DECODING ADVANCES

### Overview

Speculative decoding uses a small "draft" model to propose tokens in parallel, then verifies them with the large target model. This exploits the fact that GPUs are memory-bandwidth limited during inference, allowing multiple token proposals to be verified simultaneously.

### Current State-of-the-Art (December 2025)

| Method | Speedup | Production Ready | Hardware Requirements |
|--------|---------|------------------|----------------------|
| **Basic Speculative Decoding** | 1.5-2x | ✅ Yes | Any GPU pair |
| **EAGLE-2** | ~2.3x | ✅ Yes | Draft head training required |
| **EAGLE-3** | 3-4x | ✅ Yes (NeurIPS '25) | Hopper+ recommended |
| **Medusa** | ~2x | ✅ Yes | Multiple prediction heads |
| **SpecPipe** | 4.98x | ⚠️ Research | Pipeline parallel setup |
| **Mirror-SD** | 2-3x | ⚠️ Research | Heterogeneous compute |
| **Mixture of Attentions** | 2.4x (9.5% > EAGLE-2) | ⚠️ Research | Custom architecture |

### EAGLE vs Medusa: Technical Comparison

**EAGLE Advantages:**
- Input includes sampled token embeddings → unique target for each input
- Better acceptance rates with proper draft model training
- EAGLE-2 uses dynamic draft tree structures (no additional training needed)
- EAGLE-3 predicts tokens directly (not features), supports multi-layer fusion

**Medusa Advantages:**
- Simpler implementation (just add prediction heads)
- No separate draft model needed
- Easier to integrate into existing systems

**Hydra Recommendation:** Start with EAGLE-2 for 2.3x speedup, migrate to EAGLE-3 when ExLlamaV2/V3 adds support.

### Draft Model Selection for 70B Models

For Llama 3.1/3.3-70B models, benchmark results show:

| Draft Model | Speedup | Notes |
|-------------|---------|-------|
| Llama 3.2-1B | **2.31x** | Smallest, best speedup |
| Llama 3.2-3B | 2.15x | Better quality, slightly slower |
| Llama 3.1-8B | 2.05x | Highest quality, lowest speedup |

**Key Insight:** The 1B draft model achieves the best speedup because verification is often the bottleneck. With a 3B draft model, verification is ~4x slower than generation for a 70B target.

### ExLlamaV2/TabbyAPI Integration Status

**Current Support (December 2025):**
- ✅ ExLlamaV2 supports speculative decoding via dynamic generator
- ✅ TabbyAPI exposes draft model configuration in `config_sample.yml`
- ✅ Supports FP16, Q8, Q6, Q4 cache modes for draft models
- ✅ Automatic GPU split for multi-GPU draft model distribution

**Configuration Example:**
```yaml
draft:
  draft_model_dir: models
  draft_model_name: "Llama-3.2-1B-Instruct-EXL2"
  draft_rope_scale: 1.0
  draft_rope_alpha: 1.0
  draft_cache_mode: "FP16"  # Use Q4 to save VRAM
```

**Expected Performance on Hydra:**
- Baseline: ~50-70 tokens/sec (70B model, RTX 5090+4090)
- With Llama 3.2-1B draft: **~115-160 tokens/sec** (2.3x speedup)
- VRAM overhead: ~2-4GB for draft model + cache

### Framework Support

**Amazon SageMaker:** EAGLE-based adaptive speculative decoding (production)
**vLLM:** Draft model speculative decoding, specialized accelerators (e.g., `ibm-ai-platform/llama3-70b-accelerator`)
**SGLang:** Recommended for EAGLE-3 training via SpecForge (July 2025)
**TensorRT-LLM:** Native speculative decoding support with CUDA optimization

---

## 2. ExLlamaV2 vs ExLlamaV3: CRITICAL ANALYSIS

### ExLlamaV2 (Current Production)

**Strengths:**
- ✅ Mature, battle-tested codebase (v0.3.2, mid-2025)
- ✅ Excellent EXL2 quantization (2.55 bpw for 70B on 24GB GPU)
- ✅ Tensor parallelism support (fall 2024 release, matured winter 2024)
- ✅ Multi-GPU with `--gpu_split auto` for automatic distribution
- ✅ TabbyAPI official backend with full feature support
- ✅ FlashAttention 2.5.7+ support with paged attention
- ✅ Dynamic batching, prompt caching, KV cache deduplication
- ✅ Speculative decoding via dynamic generator

**Limitations:**
- ⚠️ No native FlashAttention-3 support (stuck on FA2)
- ⚠️ Heterogeneous VRAM support unclear (manual `--gpu_split` required)
- ⚠️ No native FP8/FP4 quantization (EXL2 only)

### ExLlamaV3 (Early Preview - November 2025)

**Revolutionary Features:**
- ✅ **EXL3 quantization format** based on QTIP (Cornell RelaxML)
- ✅ Llama-3.1-70B coherent at **1.6 bpw** (vs 2.55 bpw in EXL2)
- ✅ 70B inference possible in **under 16GB VRAM** (3 bpw output layer, 4096-token cache)
- ✅ Modular architecture with pluggable components
- ✅ Registry-based architecture system for easier model support
- ✅ Marlin-inspired GEMM kernel for memory-bound latency optimization
- ✅ Tensor-parallel and expert-parallel inference designed from ground up
- ✅ CUDA 12.8 support, Python 3.10-3.13 compatibility
- ✅ TabbyAPI official backend (recommended)

**Critical Limitations (as of v0.0.15, November 2025):**
- ❌ Performance not yet optimized (especially Ampere GPUs)
- ❌ AMD ROCm not supported
- ❌ Requires FlashAttention-2 (FlashInfer migration planned)
- ❌ Missing features: LoRA support, constrained sampling
- ❌ Tensor parallelism designed but not fully implemented yet
- ❌ Early preview status - expect breaking changes

**HYDRA VERDICT:**
**DO NOT MIGRATE TO ExLlamaV3 YET.** Wait for:
1. Tensor parallelism full implementation
2. FlashAttention-3/FlashInfer support
3. Performance parity with ExLlamaV2 on Ampere+ GPUs
4. LoRA support (if needed for fine-tuning)

**Timeline Estimate:** ExLlamaV3 production-ready Q2-Q3 2026 (6-9 months)

**Action:** Monitor monthly, test in sandbox when v0.1.0+ releases.

---

## 3. KV CACHE OPTIMIZATION

### Background: The KV Cache Problem

During autoregressive generation, transformers must access cached key-value pairs from all previous tokens. This creates two bottlenecks:
1. **Memory Fragmentation:** Continuous allocation/deallocation wastes VRAM
2. **Memory Bandwidth:** Sequential access patterns are inefficient on GPUs

### Production-Ready Solutions (2025)

#### PagedAttention (vLLM)

**Concept:** Borrow OS virtual memory concepts - break KV cache into fixed-size blocks with mapping table.

**Benefits:**
- Near-zero memory fragmentation
- Efficient memory sharing between sequences
- Dynamic allocation only for active blocks

**Performance:** Standard baseline for modern inference engines.

**Hydra Status:** ExLlamaV2 supports paged attention via FlashAttention 2.5.7+

#### Priority-Based KV Cache Eviction (TensorRT-LLM, 2025)

**Innovation:** Allow users to specify priority and duration for token ranges.

**Results:** ~20% cache hit rate improvement in production workloads.

**Use Case:** Keep system prompts, conversation context high priority; transient tokens low priority.

#### SqueezeAttention (ICLR 2025)

**Innovation:** Layer-wise + sequence-wise optimization. Different layers get different cache budgets.

**Results:**
- 30-70% memory reduction
- Up to **2.2x throughput improvement**
- Minimal accuracy degradation

**Hydra Potential:** Could enable 70B models to fit comfortably in 56GB VRAM with larger context windows.

**Implementation Status:** Research code available, not yet in production engines.

### Advanced Compression Techniques

#### CacheGen + CacheBlend (2025)

**CacheGen (SIGCOMM '24):** Compress KV cache into compact bitstreams for faster transfer.
**CacheBlend (EuroSys '25 Best Paper):** Blend different KV caches for different chunks in RAG.

**Combined Results:** 3-10x latency reduction in multi-turn QA and RAG scenarios.

**LMCache:** Production library used by 9 industry companies, stores KV cache across GPU/CPU DRAM/disk/remote.

#### EMPIRIC & RocketKV

**Innovation:** Oracle-based study defining theoretical bounds for KV cache compression.

**Key Finding:** Analyze intrinsic patterns in attention heads to prune tokens without accuracy loss.

**Impact:** Clarifies which compression methods work and why.

#### Semantic Clustering with PagedAttention

**Concept:** Cluster semantically related tokens hierarchically, update dynamically.

**Results:** Higher cache hit rates, better CPU-GPU transfer efficiency, maintains quality at 50% memory budget.

### Quantized KV Cache

**TensorRT-LLM Support:** INT8 and FP8 KV cache quantization.

**Benefits:** ~2x memory reduction with minimal quality loss.

**Hydra Opportunity:** RTX 5090/4090 both have hardware FP8 support.

**Expected Impact:** 70B model context window could increase from ~8K to ~16K tokens at same VRAM usage.

### Hydra Implementation Recommendations

**Priority 1 (Immediate):**
1. Verify TabbyAPI uses FlashAttention 2.5.7+ (paged attention enabled)
2. Configure KV cache size limits in TabbyAPI config
3. Test FP8 KV cache if supported by ExLlamaV2

**Priority 2 (Short-term, Weeks 2-4):**
1. Monitor for SqueezeAttention integration into vLLM/ExLlamaV2
2. Experiment with different cache modes (FP16 vs Q8 vs Q4) for performance/quality tradeoffs
3. Benchmark context window size vs throughput

**Priority 3 (Mid-term, Weeks 5-8):**
1. Evaluate LMCache for cross-request KV cache sharing
2. Test CacheBlend patterns if deploying RAG workloads
3. Profile attention head sparsity patterns for custom optimization

---

## 4. TENSOR PARALLELISM FOR HETEROGENEOUS GPUs

### Challenge: RTX 5090 (32GB) + RTX 4090 (24GB)

Hydra has **asymmetric VRAM** (32GB + 24GB = 56GB total) and **asymmetric bandwidth** (1.79 TB/s + 1.01 TB/s).

### ExLlamaV2 Multi-GPU Support

**Current Capability:**
- ✅ Tensor parallelism since fall 2024
- ✅ `--gpu_split auto` for automatic layer distribution
- ✅ Manual `--gpu_split` for custom allocation

**Heterogeneous Support:**
- ⚠️ Not explicitly documented
- ⚠️ Manual tuning likely required
- ⚠️ Optimal split depends on model architecture

### Optimal GPU Split Strategy

**Naive Split (by VRAM):**
- 5090: 57% of layers (32/56)
- 4090: 43% of layers (24/56)

**Bandwidth-Aware Split (recommended):**
- 5090 handles more activations (higher bandwidth)
- 4090 handles more weights (sufficient VRAM)
- Balance cross-GPU communication

**Expected Configuration for 70B Model:**
```bash
# Approximate split (needs tuning)
--gpu_split 30,26  # 30GB on 5090, 26GB on 4090 (conservative)
```

**Why Conservative:** Leave headroom for:
- KV cache (grows with context length)
- Draft model (if using speculative decoding)
- Batch processing (if enabled)

### vLLM Hybrid Approach

**Architecture:** Tensor parallelism within nodes, pipeline parallelism across nodes.

**Hydra Applicability:** Single-node, so pure tensor parallelism.

### Performance Expectations

**Theoretical Bandwidth Limit:**
- Combined: 1.79 + 1.01 = **2.8 TB/s**
- Bottleneck: Cross-GPU communication via PCIe/NVLink

**Critical Question:** Are RTX 5090 and RTX 4090 on same PCIe bus or separate?
- Same bus: Better cross-GPU communication
- Separate: PCIe lanes may bottleneck

**Action Item:** Profile GPU-to-GPU transfer rates to validate tensor parallel efficiency.

### Benchmark Targets

**Single RTX 5090 (70B, 4-bit):**
- Memory bandwidth limited: ~50-70 tok/s
- RTX 5090 is ~29% faster than 4090 for token generation

**Expected Multi-GPU (5090+4090):**
- Linear scaling: ~90-110 tok/s (1.6x single GPU)
- With speculative decoding: ~200-250 tok/s (3.5-4.5x single GPU)

**Dual RTX 5090 Comparison:**
- Dual 5090 achieves ~27 tok/s for 70B models (from benchmark data)
- Hydra's asymmetric setup will be slightly slower, but more cost-effective

---

## 5. QUANTIZATION: STATE-OF-THE-ART

### The Quantization Landscape (December 2025)

| Method | Type | Bits | Quality | Speed | VRAM | Production |
|--------|------|------|---------|-------|------|------------|
| **EXL2** | Weight-only | 2-8 | Excellent | Fast | Efficient | ✅ ExLlamaV2 |
| **EXL3** | Weight-only | 1.6-8 | Outstanding | Fast | Very efficient | ⚠️ ExLlamaV3 only |
| **GPTQ** | Weight-only | 2-8 | Good | Fast | Efficient | ✅ Widespread |
| **AWQ** | Activation-aware | 3-4 | Excellent | **Fastest** | Efficient | ✅ Mobile/server |
| **QLoRA** | Fine-tuning | 4 | Excellent | Training-focused | Efficient | ✅ Training |
| **FireQ** | Mixed INT4-FP8 | INT4/FP8 | Excellent | **Very fast** | Efficient | ⚠️ Hopper GPUs |

### EXL2 (Current Hydra Standard)

**Capabilities:**
- 2.55 bits per weight for 70B models on 24GB GPU (with 2048 context)
- 13B models at 2.65 bpw within 8GB VRAM
- Mixing quantization levels within model for any average 2-8 bpw
- Based on GPTQ optimization method

**Hydra 70B Configuration:**
- Target: 3.5-4.5 bpw for quality/memory balance
- Expected size: ~28-36GB for weights
- Remaining: ~20-28GB for KV cache + overhead
- Context window: ~8K-12K tokens

### EXL3 (Future - ExLlamaV3)

**Revolutionary Advantage:**
- 1.6 bpw for coherent 70B output (vs 2.55 bpw in EXL2)
- Based on QTIP (Cornell RelaxML) - more aggressive compression
- 70B inference under 16GB VRAM possible

**Impact on Hydra:**
- Could enable dual 70B models simultaneously
- Or single 70B with massive context window (32K+ tokens)
- Or enable 405B models (quantized to ~50GB)

**Timeline:** Wait for ExLlamaV3 production readiness (Q2-Q3 2026)

### AWQ vs GPTQ: Technical Deep Dive

**GPTQ Approach:**
- Layer-wise Hessian-based optimization
- Minimize output error via second-order information
- One-shot weight quantization

**AWQ Approach:**
- Identify salient weights (< 1% of total) via activation analysis
- Keep salient weights in FP16
- Quantize rest to INT3/INT4
- Mixed precision per layer

**Performance Comparison:**
- AWQ: **1.45x faster** than GPTQ on mobile GPUs
- AWQ: Better perplexity (5.49 vs 5.69 on Llama-2-7B)
- AWQ: -1.27% average accuracy drop
- GPTQ: Slightly faster inference on server GPUs
- GPTQ: Lower memory usage (5.99GB vs 5.695GB - minimal difference)

**Hydra Recommendation:** Stick with EXL2 for now (best integration with ExLlamaV2), but monitor AWQ if switching inference engines.

### FireQ: Mixed INT4-FP8 Quantization

**Innovation (2025):**
- INT4 for linear layer weights
- FP8 for activations and queries
- INT4 for KV matrices in attention
- FP8 for RoPE (Rotary Position Embeddings) - critical for accuracy

**Performance on Hopper GPUs:**
- **1.68x faster** than QServe (Llama2-7B, batch 16)
- **1.24x faster** than TensorRT-LLM W4A8-FP
- **1.26x faster** than QServe on prefill (Llama3-8B, batch 16, seq 1024)
- **2.53x faster** than FP16 baseline for longer sequences (2048/4096 tokens)

**Hydra Challenge:**
- RTX 5090/4090 are **Blackwell** (consumer) / **Ada Lovelace** architecture, not Hopper
- FireQ optimized for Hopper Tensor Cores
- May not achieve same speedups on consumer GPUs

**Action:** Monitor for Blackwell-optimized kernels (RTX 50-series native optimization).

### Hardware-Specific Quantization Support

**RTX 5090 (Blackwell):**
- Native support: FP32, FP16, BF16, TF32, FP8, INT8, INT4, **FP6, FP4**
- **FP4 (NVFP4):** Doubles throughput over FP8
- **5th Gen Tensor Cores:** Enhanced FP8, BF16, new FP4 operations

**RTX 4090 (Ada Lovelace):**
- Native support: FP32, FP16, BF16, TF32, FP8, INT8
- **4th Gen Tensor Cores:** FP8 supported, but not FP4

**Implication:**
- RTX 5090 can leverage cutting-edge FP4 quantization
- Asymmetric precision across GPUs may cause inefficiencies
- Stick with FP8/INT8 for cross-GPU compatibility

### Quantization-Aware Training vs Post-Training Quantization

**Critical 2025 Research Finding:**
> "Techniques that quantize models downstream from training such as PTQ and QLoRA result in models that reason better on downstream tasks and result in better performance/memory trade-offs."

**Implication:**
- Post-training quantization (GPTQ, AWQ, EXL2) is **superior** for inference
- Quantization-aware training hurts reasoning performance on math benchmarks
- QLoRA (4-bit base + trainable adapters) is best for fine-tuning

**Hydra Strategy:**
- Use pre-quantized models from HuggingFace (EXL2 format)
- Avoid re-quantizing models yourself unless necessary
- If fine-tuning: Use QLoRA, then re-quantize with EXL2

### NVIDIA TensorRT Model Optimizer

**Features (2025):**
- Supports NVFP4, FP8, INT8
- SmoothQuant, AWQ, GPTQ integration
- PyTorch and HuggingFace export
- Compatible with vLLM, SGLang, TensorRT-LLM

**Hydra Relevance:**
- If switching from ExLlamaV2 to vLLM/TensorRT-LLM
- Enables easy export to multiple inference engines
- Not needed for current ExLlamaV2 workflow

---

## 6. FlashAttention-3 & FlashInfer

### FlashAttention Evolution

| Version | Release | Key Feature | Performance |
|---------|---------|-------------|-------------|
| **FA-1** | 2022 | Tiled attention, no HBM materialization | 2-4x faster |
| **FA-2** | 2023 | Improved parallelism, multi-head support | 2x faster than FA-1 |
| **FA-3** | 2024 | Overlapped softmax + matmul on Hopper | 1.5-2x faster than FA-2 |

**FA-3 Breakthrough:** Cleverly overlaps softmax computation with matrix multiplication on Hopper architecture's asynchronous pipelines.

### FlashInfer: The Next Generation

**What it is:** Kernel library for LLM serving, extends FA-2/FA-3 with production features.

**Key Innovations (FlashInfer 0.2, December 2024):**
1. **JIT Compilation System:** Custom attention variants compiled on-demand
2. **Sparse Attention:** 90% of dense kernel bandwidth with sparsity
3. **FA-3 Integration:** Zero code changes to upgrade from FA-2 to FA-3
4. **Vector-Sparse Attention:** Efficient handling of sparse patterns
5. **StreamK-like Optimization:** Variable length sequence handling

**Performance:**
- FA-3 backend **consistently outperforms** FA-2
- Decode attention faster than FlashAttention kernels (better tile sizes)
- All Llama model kernels JIT-compiled in **15 seconds** (server CPUs)

**Recent Updates (2025):**
- March 10: Sorting-free GPU kernels for LLM sampling
- March 1: Intra-kernel profiler for threadblock visualization

### ExLlamaV2/V3 Integration Status

**ExLlamaV2:**
- ✅ FlashAttention 2.5.7+ support
- ❌ No FlashAttention-3 (limited to FA-2)
- ❌ No FlashInfer

**ExLlamaV3:**
- ✅ Requires FlashAttention-2
- 🔄 FlashInfer migration **planned** (not yet implemented)
- ❌ No FA-3 yet

**Hydra Impact:**
- Current setup limited to FA-2 performance
- **1.5-2x speedup potential** when FA-3/FlashInfer supported
- Combined with speculative decoding: **3-5x total speedup** possible

### vLLM/SGLang Support

**vLLM:**
- ✅ FlashAttention-2 (default)
- ✅ FlashInfer support (optional, better performance)
- ⚠️ FlashAttention-3 on Hopper GPUs only

**SGLang:**
- ✅ FlashInfer native integration
- ✅ FA-3 backend available
- ✅ Consistently outperforms vLLM by ~10% (RadixAttention)

**Hydra Consideration:** If switching from TabbyAPI/ExLlamaV2, SGLang offers better performance with FlashInfer.

---

## 7. SPARSE ATTENTION & MIXTURE OF DEPTHS

### The Efficiency Opportunity

**Key Observation:** Not all tokens need full attention at every layer. Inner-layer embeddings change only marginally across adjacent layers.

**Opportunity:** Selectively skip computation for less important tokens/layers.

### Mixture of Depths (MoD)

**Concept:** Dynamically allocate computation only to relevant inputs.

**Mechanism:** Expert-choice routing on alternating layers - process important tokens, skip the rest.

**γ-MoD (ICLR 2025):**
- **51.6% FLOPs reduction**
- **31% training time reduction**
- **53.2% inference time reduction**
- Average performance decline: only **-1.5%**
- Applied to LLaVA-HR (multimodal LLM)

**Limitation:** Requires model architecture changes (not drop-in optimization).

### Mixture of Attention Spans (MoA)

**Concept:** Different attention heads use different sliding-window lengths.

**Innovation:** Automatically search for optimal window size per head/layer.

**Benefits:**
- Hardware-efficient (sliding windows avoid full attention materialization)
- Better than uniform sparse attention
- Tailored to each head's importance pattern

**Status:** Research stage, not yet in production engines.

### SeerAttention (2025)

**Innovation:** Learn block-level attention sparsity from the LLM itself.

**Mechanism:**
- Learnable gate (inspired by MoE) selectively activates attention blocks
- Block-sparse FlashAttention kernel for GPU efficiency
- Lightweight self-distillation training (only gate parameters)

**Performance:**
- Better accuracy than prior sparse methods
- Lower latency for long-context prefilling
- Works with block-sparse kernels (GPU-friendly)

**Status:** Research code available, not yet in TabbyAPI/ExLlamaV2.

### DTRNet: Dynamic Token Routing

**Finding:** Cosine similarity analysis shows tokens change minimally across adjacent layers.

**Implication:** Applying uniform attention to every token at every layer is wasteful.

**Approach:** Route tokens dynamically - some skip layers, others get full processing.

**Status:** Academic research, no production implementation.

### Native Sparse Attention (ACL 2025)

**Architecture:** Three parallel attention branches:
1. **Compressed Attention:** Coarse-grained patterns
2. **Selected Attention:** Important token blocks
3. **Sliding Attention:** Local context

**Critical Insight:** Block-wise selection is essential for GPU efficiency (continuous memory access).

**Status:** Published at ACL 2025, monitoring for framework integration.

### Hydra Assessment: Sparse Attention

**Current State:** All techniques are research-stage.

**Timeline to Production:** 12-18 months (Q2-Q3 2026)

**Expected Impact:**
- 30-50% latency reduction
- 50-70% FLOPs reduction
- Minimal quality loss (<2%)

**Action:** Monitor for integration into ExLlamaV3, vLLM, or SGLang.

**Priority:** **LOW** for now - focus on production-ready optimizations first.

---

## 8. PRODUCTION INFERENCE ENGINES COMPARISON

### The Contenders (December 2025)

| Engine | Throughput | Latency | Ease of Use | Hydra Compatibility |
|--------|------------|---------|-------------|---------------------|
| **ExLlamaV2 + TabbyAPI** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Current setup |
| **SGLang** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ Compatible |
| **vLLM** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Compatible |
| **LMDeploy** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⚠️ Focus on Chinese models |
| **TensorRT-LLM** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⚠️ Requires engine build |

### Benchmark Results (H100, Llama 3.1-8B, 1000 ShareGPT prompts)

| Engine | Throughput | Notes |
|--------|------------|-------|
| **SGLang** | 16,215 tok/s | Saturates H100 bandwidth |
| **LMDeploy** | 16,132 tok/s | Near-identical to SGLang |
| **vLLM (FlashInfer)** | 12,553 tok/s | 29% slower (Python overhead) |

**Key Finding:** Even with best kernels (FlashInfer), vLLM can't match C++-optimized SGLang/LMDeploy.

### Multi-Engine Benchmark (Qwen3-8B, 500 prompts)

| Engine | Time | Notes |
|--------|------|-------|
| **MAX** | 50.6s | Fastest |
| **SGLang** | 54.2s | 7% slower |
| **vLLM** | 58.9s | 16% slower |

### Concurrent Request Performance (Llama3-70B-FP8)

**SGLang:**
- Stable 30-31 tok/s across all concurrent requests
- Excellent for high-concurrency production

**vLLM:**
- Starts at 22 tok/s, drops to 16 tok/s with more requests
- Less suitable for high-concurrency scenarios

### When to Use Each Engine

**TabbyAPI + ExLlamaV2 (Current Hydra):**
- ✅ Best for: Quantized models (EXL2), ease of use, rapid prototyping
- ✅ Excellent quantization support (EXL2 format)
- ✅ Simple configuration, OpenAI-compatible API
- ⚠️ Slower than SGLang/LMDeploy on non-quantized models

**SGLang:**
- ✅ Best for: Multi-turn conversations, shared context (RadixAttention)
- ✅ ~10% faster than vLLM at same context loads
- ✅ Highest throughput in benchmarks
- ❌ Complex dependency management
- ❌ Requires specialized team for production deployment

**vLLM:**
- ✅ Best for: Rapid prototyping, heterogeneous GPU environments, max model coverage
- ✅ Largest ecosystem and community support
- ✅ Excellent for batch inference with predictable patterns
- ❌ Python overhead limits peak throughput

**LMDeploy:**
- ✅ Best for: Production deployments, peak throughput
- ✅ 99.5% of SGLang's performance with trivial installation
- ⚠️ Focus on Chinese LLM ecosystem
- ⚠️ Less community support in English

**TensorRT-LLM:**
- ✅ Best for: Absolute maximum performance, production at scale
- ✅ Native NVIDIA optimization, cutting-edge kernels
- ❌ Requires building TensorRT engines (complex workflow)
- ❌ Less flexible than Python-based engines

### Hydra Recommendation: Inference Engine Strategy

**Current (Phase 11+):**
- ✅ Keep TabbyAPI + ExLlamaV2 for primary inference
- Rationale: Excellent EXL2 support, proven stability, easy configuration

**Short-term (Weeks 2-4):**
- 🔄 Deploy **SGLang** in parallel for testing
- Test EAGLE-3 speculative decoding via SpecForge
- Benchmark SGLang vs ExLlamaV2 on Hydra hardware
- Compare multi-turn conversation performance (RadixAttention benefit)

**Mid-term (Weeks 5-8):**
- 📊 Choose primary engine based on benchmarks:
  - If quantization quality is paramount: **ExLlamaV2**
  - If throughput is paramount: **SGLang**
  - If ease of use is paramount: **vLLM**
- Deploy secondary engine for specific workloads (e.g., SGLang for chatbots, ExLlamaV2 for code generation)

**Long-term (Weeks 9-12):**
- 🔄 Re-evaluate when ExLlamaV3 reaches production (Q2-Q3 2026)
- Monitor LMDeploy if expanding to multi-language models
- Consider TensorRT-LLM if deploying commercial services at scale

---

## 9. HYDRA-SPECIFIC OPTIMIZATION ROADMAP

### Hardware Profile

**Node:** hydra-ai (192.168.1.250)
**GPUs:**
- RTX 5090: 32GB GDDR7, 1.79 TB/s, 21,760 CUDA cores, 680 5th-gen Tensor Cores
- RTX 4090: 24GB GDDR6X, 1.01 TB/s, 16,384 CUDA cores, 512 4th-gen Tensor Cores
**Total VRAM:** 56GB
**Asymmetric Bandwidth:** 1.77:1 ratio (5090:4090)
**Current Software:** TabbyAPI + ExLlamaV2
**Target Models:** 70B (primary), 405B (stretch goal)

### Theoretical Maximum Performance

**Baseline (Current, Conservative Estimate):**
- Single RTX 5090, 70B EXL2 (3.5 bpw), 8K context
- ~50-70 tokens/second

**Optimized Multi-GPU (Achievable Today):**
1. Tensor parallelism (5090+4090): **1.6x** → 80-112 tok/s
2. Speculative decoding (Llama 3.2-1B draft): **2.3x** → 184-258 tok/s
3. KV cache optimization (FP8 quantization): **1.1x** → 202-284 tok/s

**Total Achievable Speedup:** **3.5-4.5x** → **200-280 tokens/second**

**With Future Optimizations (6-12 months):**
1. FlashAttention-3: **1.5x** → 303-426 tok/s
2. Sparse attention (MoD/SeerAttention): **1.3x** → 394-554 tok/s
3. ExLlamaV3 EXL3 quantization: Enables larger context or 405B models

**Theoretical Maximum:** **~550 tok/s** for 70B models (7-10x current baseline)

### Implementation Roadmap: Priority Levels

---

### 🔴 PRIORITY 1: IMMEDIATE (Week 1)

**Goal:** Maximize current TabbyAPI + ExLlamaV2 setup without architectural changes.

#### Task 1.1: Optimize EXL2 Quantization
- **Action:** Download pre-quantized models at different bpw levels
- **Test Matrix:**
  - Llama-3.1-70B at 3.0, 3.5, 4.0, 4.5 bpw
  - Benchmark perplexity and throughput for each
  - Identify sweet spot for quality vs speed
- **Expected Outcome:** Find optimal quantization level (likely 3.5-4.0 bpw)
- **Time:** 4-6 hours

#### Task 1.2: Multi-GPU Configuration
- **Action:** Configure ExLlamaV2 tensor parallelism
  ```bash
  # Test different splits
  --gpu_split auto  # Baseline
  --gpu_split 30,26  # Conservative manual
  --gpu_split 32,24  # Aggressive (full VRAM)
  ```
- **Benchmark:** Measure tokens/second for each split
- **Expected Outcome:** 1.5-1.8x speedup over single GPU
- **Time:** 2-3 hours

#### Task 1.3: KV Cache Tuning
- **Action:** Verify FlashAttention 2.5.7+ in use, configure cache modes
  ```yaml
  # TabbyAPI config.yml
  max_seq_len: 8192  # Start conservative
  cache_mode: "FP16"  # Baseline
  # Test: "Q8", "Q6", "Q4" if supported
  ```
- **Benchmark:** Context window size vs throughput
- **Expected Outcome:** Determine max stable context length
- **Time:** 2 hours

#### Task 1.4: Baseline Performance Documentation
- **Action:** Create comprehensive benchmark suite
  - Single-turn inference (short prompts: 100-500 tokens)
  - Multi-turn conversations (accumulated context: 2K-8K tokens)
  - Long-context tasks (code analysis: 8K+ tokens)
- **Metrics:** Tokens/sec, TTFT (time to first token), latency per token
- **Output:** Baseline.md with all measurements
- **Time:** 3-4 hours

**Week 1 Total Time:** 11-15 hours
**Expected Baseline Improvement:** 1.5-2x (75-140 tok/s)

---

### 🟠 PRIORITY 2: SHORT-TERM (Weeks 2-4)

**Goal:** Implement production-ready advanced optimizations.

#### Task 2.1: Speculative Decoding with Draft Models
- **Action:** Deploy EAGLE-2 or Llama 3.2-1B draft model
  ```yaml
  # TabbyAPI config
  draft:
    draft_model_name: "Llama-3.2-1B-Instruct-EXL2"
    draft_cache_mode: "Q4"  # Minimize VRAM overhead
  ```
- **Benchmark:** Compare with/without draft model across task types
- **Expected Outcome:** 2.0-2.5x speedup (single-turn), 1.5-2.0x (multi-turn)
- **Time:** 6-8 hours (includes model download, config, testing)

#### Task 2.2: SGLang Parallel Deployment
- **Action:** Deploy SGLang on hydra-ai for A/B testing
  - Install via Docker or NixOS package
  - Load same 70B model as ExLlamaV2
  - Configure RadixAttention for multi-turn optimization
- **Benchmark:** Direct comparison with ExLlamaV2
  - Single-turn tasks
  - Multi-turn conversations (RadixAttention benefit)
  - Concurrent request handling
- **Expected Outcome:** Determine if SGLang outperforms ExLlamaV2 on Hydra hardware
- **Time:** 8-10 hours (includes setup, configuration, testing)

#### Task 2.3: Draft Model Training (Optional)
- **Action:** Train domain-specific 1B draft model for Hydra's common tasks
  - Collect corpus of Hydra's typical queries (code generation, analysis, planning)
  - Fine-tune Llama 3.2-1B on corpus using QLoRA
  - Quantize to EXL2 format
- **Expected Outcome:** Higher acceptance rate (25%+) for Hydra-specific tasks
- **Time:** 12-16 hours (includes data collection, training, validation)
- **Priority:** Optional - only if baseline draft model underperforms

#### Task 2.4: FlashAttention Version Audit
- **Action:** Verify exact FlashAttention version in ExLlamaV2
  ```python
  import flash_attn
  print(flash_attn.__version__)
  ```
- **Upgrade:** If not on latest FA-2 (2.5.7+), upgrade
- **Expected Outcome:** Ensure paged attention is active
- **Time:** 1-2 hours

**Weeks 2-4 Total Time:** 27-36 hours
**Expected Cumulative Improvement:** 3.0-4.0x baseline (150-280 tok/s)

---

### 🟡 PRIORITY 3: MID-TERM (Weeks 5-8)

**Goal:** Advanced memory optimization and inference engine evaluation.

#### Task 3.1: KV Cache Compression Experiments
- **Action:** Test advanced cache configurations
  - FP8 KV cache (if ExLlamaV2 supports)
  - INT8 KV cache quantization
  - Larger context windows (12K, 16K tokens)
- **Benchmark:** Quality vs memory tradeoff
- **Expected Outcome:** 1.5-2x context window increase or 10-15% speedup
- **Time:** 6-8 hours

#### Task 3.2: LMCache Integration (Optional)
- **Action:** Deploy LMCache for cross-request KV cache sharing
  - Install LMCache library
  - Configure multi-tier storage (GPU → CPU DRAM → Disk)
  - Test with RAG workloads or repeated queries
- **Use Case:** If deploying multi-user chatbot or RAG system
- **Expected Outcome:** 3-10x latency reduction for cache-hit scenarios
- **Time:** 8-10 hours
- **Priority:** Only if deploying shared inference service

#### Task 3.3: Inference Engine Bake-Off
- **Action:** Formal comparison: ExLlamaV2 vs SGLang vs vLLM
  - Same model, same hardware, same benchmark suite
  - Test quantized (EXL2) and non-quantized (FP16) variants
  - Document installation complexity, ease of configuration
- **Decision Point:** Choose primary inference engine for Hydra Phase 12+
- **Expected Outcome:** Data-driven engine selection
- **Time:** 10-12 hours

#### Task 3.4: Power Management Tuning
- **Action:** Optimize GPU power limits for sustained performance
  ```bash
  # Current limits (per GPU Power Limits rule)
  sudo nvidia-smi -pl 450  # RTX 5090
  sudo nvidia-smi -pl 300  # RTX 4090
  ```
- **Test:** Benchmark at different power levels (5090: 400W, 450W, 500W)
- **Expected Outcome:** Find optimal power/performance balance for 24/7 operation
- **Time:** 2-3 hours

**Weeks 5-8 Total Time:** 26-33 hours
**Expected Cumulative Improvement:** 3.5-4.5x baseline (175-315 tok/s)

---

### 🔵 PRIORITY 4: EXPERIMENTAL (Weeks 9-12)

**Goal:** Evaluate cutting-edge techniques and prepare for next-gen architecture.

#### Task 4.1: ExLlamaV3 Sandbox Testing
- **Action:** Deploy ExLlamaV3 in isolated environment
  - Test EXL3 quantization (1.6 bpw for 70B)
  - Benchmark against ExLlamaV2 EXL2
  - Evaluate stability, feature completeness
- **Decision Point:** Determine migration timeline
- **Expected Outcome:** Readiness assessment for production migration
- **Time:** 6-8 hours

#### Task 4.2: Sparse Attention Prototyping
- **Action:** If available, test SeerAttention or SqueezeAttention
  - Fork research repositories
  - Integrate with ExLlamaV2 or SGLang (if supported)
  - Benchmark long-context tasks (16K+ tokens)
- **Expected Outcome:** Validate sparse attention benefits on consumer GPUs
- **Time:** 10-12 hours
- **Priority:** Only if research code is accessible and documented

#### Task 4.3: 405B Model Feasibility Study
- **Action:** Attempt loading Llama 3.1-405B with aggressive quantization
  - ExLlamaV3 EXL3 format at 1.6-2.0 bpw (if available)
  - Distribute across 5090+4090 (56GB total)
  - Test basic inference (even if slow)
- **Expected Outcome:** Determine if 405B is viable on current hardware
- **Time:** 4-6 hours

#### Task 4.4: Future Architecture Planning
- **Action:** Document findings and plan Hydra Phase 12 inference architecture
  - Chosen inference engine (ExLlamaV2/V3, SGLang, vLLM)
  - Recommended quantization format and bpw
  - Speculative decoding configuration
  - KV cache optimization strategy
- **Output:** `docs/phase-12-inference-architecture.md`
- **Time:** 4-6 hours

**Weeks 9-12 Total Time:** 24-32 hours
**Expected Outcome:** Production-ready Phase 12 architecture plan

---

### Total Implementation Time Estimate: 88-116 hours (11-15 days of focused work)

---

## 10. SPECIFIC HYDRA CONFIGURATION RECOMMENDATIONS

### Immediate Configuration Changes (Week 1)

#### TabbyAPI `config.yml` Optimizations

```yaml
# ====================
# MODEL CONFIGURATION
# ====================
model:
  model_dir: models
  model_name: "Llama-3.1-70B-Instruct-EXL2-3.5bpw"  # Adjust bpw after testing

  # Multi-GPU tensor parallelism
  gpu_split_auto: true  # Start with auto, tune manually if needed
  # gpu_split: 30,26  # Uncomment for manual control (30GB on 5090, 26GB on 4090)

  # Context and cache
  max_seq_len: 8192  # Conservative start, increase after benchmarking
  cache_mode: "FP16"  # Test Q8, Q6, Q4 for memory savings

  # Rope scaling (if needed for longer context)
  rope_scale: 1.0
  rope_alpha: 1.0  # Adjust for context beyond training length

# ====================
# DRAFT MODEL (SPECULATIVE DECODING)
# ====================
draft:
  draft_model_dir: models
  draft_model_name: "Llama-3.2-1B-Instruct-EXL2"  # Enable after Week 2
  draft_rope_scale: 1.0
  draft_rope_alpha: 1.0
  draft_cache_mode: "Q4"  # Minimize VRAM overhead

# ====================
# PERFORMANCE TUNING
# ====================
# Enable if FlashAttention 2.5.7+ is installed
use_flash_attention: true

# Batch processing (if deploying multi-user)
# max_batch_size: 4  # Uncomment for concurrent requests

# Token streaming
stream: true
```

#### ExLlamaV2 Command-Line Configuration

```bash
#!/bin/bash
# Hydra inference optimization script

# Set GPU power limits (per GPU Power Limits rule)
sudo nvidia-smi -i 0 -pl 450  # RTX 5090
sudo nvidia-smi -i 1 -pl 300  # RTX 4090

# Launch TabbyAPI with optimized settings
cd /path/to/tabbyAPI
python main.py \
  --config config.yml \
  --verbose \
  --log-performance  # Enable performance logging
```

### GPU Monitoring Script

```bash
#!/bin/bash
# monitor_inference.sh - Track GPU utilization during inference

watch -n 1 'nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu,utilization.memory,power.draw,power.limit --format=csv,noheader,nounits'
```

**Expected Output (During Inference):**
```
0, NVIDIA GeForce RTX 5090, 30000, 32000, 95, 98, 420, 450
1, NVIDIA GeForce RTX 4090, 24000, 24000, 93, 97, 285, 300
```

**Healthy Indicators:**
- GPU utilization: 90%+ (memory-bound is expected)
- Memory utilization: 95%+ (using available VRAM efficiently)
- Power draw: Near limit (not thermal throttling)

---

## 11. BENCHMARKING & VALIDATION

### Benchmark Suite Design

#### 1. Single-Turn Inference (Batch Size = 1)

**Test Cases:**
```python
# Short prompt (100 tokens) → 500 token generation
prompt_short = "Write a Python function to calculate Fibonacci numbers."

# Medium prompt (500 tokens) → 1000 token generation
prompt_medium = "Analyze this codebase structure and suggest improvements: [500-token code snippet]"

# Long prompt (2000 tokens) → 500 token generation
prompt_long = "[Full Python module of 2000 tokens] Refactor this code for better performance."
```

**Metrics to Track:**
- **TTFT (Time To First Token):** <200ms target
- **Tokens/second (generation phase):** >200 tok/s target
- **Total latency:** End-to-end time
- **Memory usage:** Peak VRAM on each GPU

#### 2. Multi-Turn Conversations

**Test Case:**
```python
# Simulate 10-turn conversation, accumulating context
turns = [
    "What is the purpose of this function? [code snippet]",
    "How can we optimize its performance?",
    "Show me the refactored version.",
    "Add error handling to the refactored code.",
    # ... 6 more turns
]
```

**Metrics to Track:**
- **Latency degradation:** Should remain <10% increase by turn 10
- **KV cache growth:** Monitor VRAM usage per turn
- **Throughput stability:** Tokens/sec should remain consistent

#### 3. Long-Context Tasks

**Test Cases:**
```python
# Code analysis (8K token file)
prompt_code = "[Entire Python module] Identify all potential bugs."

# Document Q&A (12K token document)
prompt_document = "[Long technical document] Summarize the key findings."

# RAG simulation (16K combined context)
prompt_rag = "[Retrieved chunks: 8K tokens] [Query: 100 tokens] Answer based on context."
```

**Metrics to Track:**
- **Context window limit:** Maximum stable sequence length
- **Quality degradation:** Perplexity or manual evaluation beyond 8K tokens
- **Memory efficiency:** VRAM usage vs context length (should be sublinear with compression)

#### 4. Concurrent Requests (Multi-User Simulation)

**Test Setup:**
```python
# Launch N concurrent requests with varied lengths
concurrent_requests = [
    {"prompt_len": 100, "gen_len": 500},
    {"prompt_len": 500, "gen_len": 1000},
    {"prompt_len": 200, "gen_len": 300},
    # ... up to 8-16 concurrent
]
```

**Metrics to Track:**
- **Throughput degradation:** Tokens/sec with 1, 2, 4, 8 concurrent users
- **Latency fairness:** Standard deviation of response times
- **OOM threshold:** Maximum concurrent requests before out-of-memory

### Automated Benchmarking Tools

#### Use BentoML's llm-optimizer

```bash
# Install
pip install llm-optimizer

# Run comprehensive benchmark
llm-optimizer benchmark \
  --model "Llama-3.1-70B-Instruct-EXL2" \
  --endpoint "http://localhost:5000/v1" \
  --constraint "TTFT < 200ms" \
  --constraint "P99_ITL < 50ms" \
  --output hydra-benchmark-results.json
```

**Benefits:**
- Framework-agnostic (works with TabbyAPI, vLLM, SGLang)
- Supports constraint-based optimization
- Automated report generation

#### Custom Benchmark Script

```python
#!/usr/bin/env python3
# benchmark_hydra.py

import time
import requests
import statistics

def benchmark_inference(prompt, max_tokens=500, runs=5):
    results = {
        "ttft": [],
        "total_time": [],
        "tokens_per_second": []
    }

    for _ in range(runs):
        start = time.time()

        response = requests.post(
            "http://localhost:5000/v1/completions",
            json={
                "prompt": prompt,
                "max_tokens": max_tokens,
                "stream": False
            }
        )

        end = time.time()
        data = response.json()

        total_time = end - start
        tokens_generated = len(data["choices"][0]["text"].split())  # Approximate

        results["total_time"].append(total_time)
        results["tokens_per_second"].append(tokens_generated / total_time)

    return {
        "avg_time": statistics.mean(results["total_time"]),
        "avg_tok_per_sec": statistics.mean(results["tokens_per_second"]),
        "std_dev": statistics.stdev(results["total_time"])
    }

# Run benchmarks
prompts = {
    "short": "Write a Python function to sort a list.",
    "medium": "Analyze this codebase structure: [500-token code]",
    "long": "[2000-token module] Refactor for performance."
}

for name, prompt in prompts.items():
    print(f"\n=== Benchmark: {name} ===")
    results = benchmark_inference(prompt)
    print(f"Avg Time: {results['avg_time']:.2f}s")
    print(f"Avg Tok/s: {results['avg_tok_per_sec']:.2f}")
    print(f"Std Dev: {results['std_dev']:.2f}s")
```

### Performance Targets Summary

| Metric | Baseline | Target (Week 4) | Stretch (Week 12) |
|--------|----------|-----------------|-------------------|
| **Tokens/second** | 50-70 | 200-280 | 400-550 |
| **TTFT (Time to First Token)** | <500ms | <200ms | <100ms |
| **Max Context Window** | 8K | 12K | 16K+ |
| **Concurrent Users (stable)** | 1-2 | 4-8 | 8-16 |
| **VRAM Efficiency** | 90% | 95% | 98% |

---

## 12. MONITORING & OBSERVABILITY

### Integration with Existing Hydra Observability Stack

Hydra already has Prometheus + Grafana deployed (per `knowledge/observability.md`). Extend with inference-specific metrics.

#### Prometheus Metrics to Collect

```yaml
# Add to Prometheus scrape config
- job_name: 'tabbyapi'
  static_configs:
    - targets: ['192.168.1.250:5000']
  metrics_path: '/metrics'  # If TabbyAPI exposes Prometheus metrics
```

**Key Metrics:**
- `llm_inference_requests_total` (counter)
- `llm_inference_duration_seconds` (histogram)
- `llm_tokens_generated_total` (counter)
- `llm_tokens_per_second` (gauge)
- `llm_vram_usage_bytes` (gauge per GPU)
- `llm_kv_cache_size_bytes` (gauge)
- `llm_concurrent_requests` (gauge)

#### Grafana Dashboard: LLM Inference Performance

**Panels to Create:**

1. **Throughput Over Time**
   - Query: `rate(llm_tokens_generated_total[5m])`
   - Visualization: Time series line graph
   - Alert: Tokens/sec < 150 for 5 minutes

2. **Latency Distribution**
   - Query: `histogram_quantile(0.95, llm_inference_duration_seconds)`
   - Visualization: Heatmap
   - Alert: P95 latency > 5 seconds

3. **GPU Memory Utilization**
   - Query: `nvidia_gpu_memory_used_bytes / nvidia_gpu_memory_total_bytes * 100`
   - Visualization: Gauge (per GPU)
   - Alert: VRAM > 98% for 10 minutes (potential OOM)

4. **KV Cache Growth**
   - Query: `llm_kv_cache_size_bytes`
   - Visualization: Area graph
   - Alert: Sudden spikes (potential memory leak)

5. **Concurrent Request Queue**
   - Query: `llm_concurrent_requests`
   - Visualization: Time series
   - Alert: Queue > 16 requests (overload)

### Custom Logging Script

```python
#!/usr/bin/env python3
# log_inference_metrics.py - Custom logging for ExLlamaV2/TabbyAPI

import time
import subprocess
import json
import requests

def get_gpu_metrics():
    """Query nvidia-smi for GPU metrics"""
    result = subprocess.run([
        "nvidia-smi",
        "--query-gpu=index,memory.used,memory.total,utilization.gpu,power.draw",
        "--format=csv,noheader,nounits"
    ], capture_output=True, text=True)

    metrics = []
    for line in result.stdout.strip().split('\n'):
        idx, mem_used, mem_total, util, power = line.split(', ')
        metrics.append({
            "gpu_id": int(idx),
            "vram_used_mb": int(mem_used),
            "vram_total_mb": int(mem_total),
            "utilization_pct": int(util),
            "power_draw_w": float(power)
        })
    return metrics

def log_metrics():
    """Continuously log metrics to JSON file"""
    with open("/var/log/hydra/inference_metrics.jsonl", "a") as f:
        while True:
            timestamp = time.time()
            gpu_metrics = get_gpu_metrics()

            # Optionally query TabbyAPI for internal metrics
            # response = requests.get("http://localhost:5000/stats")
            # api_metrics = response.json()

            log_entry = {
                "timestamp": timestamp,
                "gpus": gpu_metrics,
                # **api_metrics
            }

            f.write(json.dumps(log_entry) + "\n")
            f.flush()

            time.sleep(5)  # Log every 5 seconds

if __name__ == "__main__":
    log_metrics()
```

**Deploy as systemd service:**
```bash
# /etc/systemd/system/inference-metrics-logger.service
[Unit]
Description=Hydra Inference Metrics Logger
After=network.target

[Service]
Type=simple
User=typhon
ExecStart=/usr/bin/python3 /path/to/log_inference_metrics.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 13. RISK ASSESSMENT & MITIGATION

### Critical Risks

#### Risk 1: Heterogeneous GPU Configuration Inefficiency

**Description:** RTX 5090 + RTX 4090 have different VRAM (32GB vs 24GB) and bandwidth (1.79 TB/s vs 1.01 TB/s). Tensor parallelism may not scale linearly.

**Probability:** Medium-High
**Impact:** 20-40% performance loss vs dual RTX 5090 setup

**Mitigation:**
1. Benchmark both automatic and manual GPU splits
2. Profile cross-GPU communication latency
3. Consider asymmetric workload distribution:
   - RTX 5090: Prefill phase (bandwidth-intensive)
   - RTX 4090: Decode phase (compute-intensive)
4. If severe inefficiency: Disable tensor parallelism, use 5090 as primary, 4090 for draft model

#### Risk 2: ExLlamaV2 Stagnation

**Description:** ExLlamaV3 is the future, but v2 may not receive FlashAttention-3 or advanced features.

**Probability:** Medium
**Impact:** Missing 1.5-2x speedup from FA-3, sparse attention, etc.

**Mitigation:**
1. Maintain parallel SGLang deployment for FA-3 access
2. Monitor ExLlamaV3 releases monthly
3. Plan migration to ExLlamaV3 when stable (Q2-Q3 2026)
4. Budget time for re-quantization to EXL3 format

#### Risk 3: Speculative Decoding Draft Model Mismatch

**Description:** Pre-trained draft models may not align with Hydra's domain (technical documentation, code generation, system architecture).

**Probability:** Medium
**Impact:** Lower acceptance rates (15-18% instead of 25%+), reducing speedup from 2.3x to 1.5-1.8x

**Mitigation:**
1. Collect Hydra's query corpus (code, docs, planning)
2. Fine-tune Llama 3.2-1B using QLoRA on corpus
3. Re-quantize to EXL2 format
4. Benchmark domain-specific draft vs generic draft

#### Risk 4: UPS Overload with Dual-GPU Full Load

**Description:** RTX 5090 (450W) + RTX 4090 (300W) = 750W GPU power alone. System total can reach 1000W+, approaching 2000W UPS limit (per GPU Power Limits rule).

**Probability:** Low-Medium
**Impact:** UPS shutdown, cluster downtime

**Mitigation:**
1. Monitor total system power draw during benchmarks
2. Set conservative GPU power limits initially (5090: 400W, 4090: 280W)
3. Gradually increase and test stability
4. If approaching UPS limit: Reduce power limits or disable 4090 for batch workloads

#### Risk 5: Memory Fragmentation with Long-Running Services

**Description:** KV cache allocation/deallocation over hours/days may cause VRAM fragmentation, degrading performance.

**Probability:** Low-Medium
**Impact:** Gradual slowdown, eventual OOM crashes

**Mitigation:**
1. Enable paged attention (FlashAttention 2.5.7+) to minimize fragmentation
2. Configure automatic service restart every 24 hours (systemd timer)
3. Monitor VRAM usage trends in Grafana
4. Implement health checks with automatic restart on anomalies

---

## 14. COST-BENEFIT ANALYSIS

### Optimization ROI Comparison

| Optimization | Implementation Time | Speedup | Complexity | ROI |
|--------------|---------------------|---------|------------|-----|
| **EXL2 Quantization Tuning** | 4-6h | 1.1-1.3x | Low | ⭐⭐⭐⭐⭐ |
| **Multi-GPU Tensor Parallel** | 2-3h | 1.5-1.8x | Low | ⭐⭐⭐⭐⭐ |
| **Speculative Decoding** | 6-8h | 2.0-2.5x | Medium | ⭐⭐⭐⭐⭐ |
| **KV Cache Optimization** | 2h | 1.1-1.2x | Low | ⭐⭐⭐⭐ |
| **FlashAttention-3** | Wait for support | 1.5-2x | N/A | ⭐⭐⭐⭐ (future) |
| **SGLang Migration** | 8-10h | 1.1-1.3x | Medium-High | ⭐⭐⭐ |
| **ExLlamaV3 Migration** | Wait 6-9mo | 1.5-2x | High | ⭐⭐⭐ (future) |
| **Sparse Attention** | Wait 12-18mo | 1.3-1.5x | Very High | ⭐⭐ (research) |
| **Draft Model Training** | 12-16h | +10-15% acceptance | High | ⭐⭐ (optional) |

### Resource Allocation Recommendation

**Total Available Time Budget:** ~100 hours over 12 weeks

**Suggested Allocation:**
1. **Priority 1 (Immediate):** 15 hours → 1.5-2x baseline
2. **Priority 2 (Short-term):** 30 hours → 3.0-4.0x baseline
3. **Priority 3 (Mid-term):** 30 hours → 3.5-4.5x baseline
4. **Priority 4 (Experimental):** 25 hours → Architecture planning

**Expected Total Improvement:** 3.5-4.5x baseline = **175-315 tokens/second** for 70B models

**Alternative Allocation (Conservative - 50 hour budget):**
1. Priority 1: 15 hours
2. Priority 2 (speculative decoding only): 10 hours
3. Priority 3 (inference engine bake-off only): 10 hours
4. Priority 4 (ExLlamaV3 testing only): 6 hours
5. Documentation: 9 hours

**Expected Conservative Improvement:** 3.0-3.5x baseline = **150-245 tokens/second**

---

## 15. FUTURE-PROOFING CONSIDERATIONS

### Technology Watch List (Monthly Monitoring)

| Technology | Current Status | Monitor For | Timeline |
|------------|----------------|-------------|----------|
| **ExLlamaV3** | v0.0.15 (Nov 2025) | Tensor parallel, LoRA, performance parity | Q2-Q3 2026 |
| **EAGLE-3** | NeurIPS '25 | ExLlamaV2 integration | Q1-Q2 2026 |
| **FlashAttention-3** | Hopper only | Consumer GPU support | Q2-Q3 2026 |
| **FlashInfer** | v0.2 (Dec 2024) | ExLlamaV3 integration | Q2 2026 |
| **SqueezeAttention** | ICLR 2025 | vLLM/SGLang integration | Q3-Q4 2026 |
| **SeerAttention** | Research (2025) | Production frameworks | Q4 2026+ |
| **Mixture of Depths** | γ-MoD (ICLR 2025) | LLM architecture adoption | 2027+ |
| **FireQ (FP4-INT4)** | Hopper-optimized | Blackwell/consumer GPU kernels | Q2-Q3 2026 |

### Upgrade Triggers

**Trigger 1: ExLlamaV3 Reaches v0.2.0+**
- **Action:** Full migration from ExLlamaV2 to ExLlamaV3
- **Benefits:** EXL3 quantization (1.6 bpw), better tensor parallel, FlashInfer support
- **Timeline:** Estimate Q2-Q3 2026

**Trigger 2: Hydra Adds Additional RTX 5090**
- **Action:** Reconfigure for symmetric dual RTX 5090 setup
- **Benefits:** Linear tensor parallel scaling, 64GB total VRAM
- **Impact:** 405B models become viable at reasonable quantization (3-4 bpw)

**Trigger 3: SGLang Outperforms ExLlamaV2 by >20%**
- **Action:** Migrate primary inference to SGLang
- **Considerations:** Lose EXL2 quantization, must use FP16/FP8/GPTQ
- **Trade-off:** Higher VRAM usage for higher throughput

**Trigger 4: Sparse Attention Enters Production Frameworks**
- **Action:** Enable SqueezeAttention or SeerAttention if supported
- **Benefits:** 30-50% latency reduction, 50-70% FLOPs reduction
- **Timeline:** Estimate Q3-Q4 2026

### Long-Term Architecture Vision (2026-2027)

**Hydra Inference Stack v2.0:**
1. **Primary Engine:** ExLlamaV3 (EXL3 quantization, FA-3, FlashInfer)
2. **Speculative Decoding:** EAGLE-3 with domain-specific draft models
3. **Memory:** Sparse attention (SqueezeAttention) + quantized KV cache (FP8)
4. **Orchestration:** Multi-agent with shared KV cache (LMCache)
5. **Hardware:** Dual RTX 5090 (64GB VRAM) or next-gen GPUs

**Expected Performance (2026-2027):**
- 70B models: 500-700 tokens/second (10-14x current baseline)
- 405B models: 100-150 tokens/second (viable for production)
- Context windows: 32K+ tokens standard
- Multi-user: 16-32 concurrent users with stable latency

---

## 16. EXECUTIVE SUMMARY: ACTION ITEMS

### Week 1: Immediate Optimizations (15 hours)
- [ ] Benchmark EXL2 quantization levels (3.0, 3.5, 4.0, 4.5 bpw)
- [ ] Configure multi-GPU tensor parallelism (`--gpu_split auto`, then manual tuning)
- [ ] Verify FlashAttention 2.5.7+ and configure KV cache
- [ ] Document baseline performance across task types
- **Expected: 1.5-2x improvement → 75-140 tok/s**

### Weeks 2-4: Speculative Decoding & Engine Testing (30 hours)
- [ ] Deploy Llama 3.2-1B draft model for speculative decoding
- [ ] Install and benchmark SGLang in parallel
- [ ] Compare ExLlamaV2 vs SGLang performance on Hydra hardware
- [ ] Upgrade to latest FlashAttention version
- **Expected: 3.0-4.0x improvement → 150-280 tok/s**

### Weeks 5-8: Advanced Memory & Engine Selection (30 hours)
- [ ] Test FP8/INT8 KV cache quantization
- [ ] Experiment with larger context windows (12K-16K tokens)
- [ ] Formal inference engine bake-off (ExLlamaV2 vs SGLang vs vLLM)
- [ ] Optimize GPU power limits for sustained performance
- **Expected: 3.5-4.5x improvement → 175-315 tok/s**

### Weeks 9-12: Future Architecture & Planning (25 hours)
- [ ] Test ExLlamaV3 in sandbox environment
- [ ] Attempt 405B model with aggressive quantization
- [ ] Evaluate sparse attention research code (if available)
- [ ] Document Phase 12 inference architecture plan
- **Expected: Roadmap for 5-10x improvement by mid-2026**

### Continuous Monitoring (Ongoing)
- [ ] Deploy Grafana dashboard for LLM inference metrics
- [ ] Set up automated alerts (VRAM > 98%, throughput < 150 tok/s)
- [ ] Monthly technology watch (ExLlamaV3, EAGLE-3, FA-3, sparse attention)
- [ ] Quarterly architecture review and optimization re-assessment

---

## SOURCES & REFERENCES

### Speculative Decoding
- [GitHub - SafeAILab/EAGLE](https://github.com/SafeAILab/EAGLE)
- [NVIDIA TensorRT-LLM Speculative Decoding](https://nvidia.github.io/TensorRT-LLM/advanced/speculative-decoding.html)
- [NVIDIA: Introduction to Speculative Decoding](https://developer.nvidia.com/blog/an-introduction-to-speculative-decoding-for-reducing-latency-in-ai-inference/)
- [EAGLE-2 Paper (arXiv)](https://arxiv.org/html/2406.16858v1)
- [Together.ai: Medusa Framework](https://www.together.ai/blog/medusa)
- [AWS: EAGLE Adaptive Speculative Decoding](https://aws.amazon.com/blogs/machine-learning/amazon-sagemaker-ai-introduces-eagle-based-adaptive-speculative-decoding-to-accelerate-generative-ai-inference/)

### ExLlama Inference Engines
- [GitHub - ExLlamaV2](https://github.com/turboderp-org/exllamav2)
- [GitHub - ExLlamaV3](https://github.com/turboderp-org/exllamav3)
- [GitHub - TabbyAPI](https://github.com/theroyallab/tabbyAPI)
- [Kaitchup: Run Llama 3.3 70B with ExLlamaV3](https://kaitchup.substack.com/p/run-llama-33-70b-on-your-gpu-with)

### KV Cache Optimization
- [Microsoft Research: LLM Profiling for KV Cache](https://www.microsoft.com/en-us/research/blog/llm-profiling-guides-kv-cache-optimization/)
- [arXiv: Review of KV Cache Optimization Methods](https://arxiv.org/html/2407.18003v4)
- [NVIDIA: KV Cache Reuse in TensorRT-LLM](https://developer.nvidia.com/blog/introducing-new-kv-cache-reuse-optimizations-in-nvidia-tensorrt-llm/)
- [ACM: EMPIRIC - KV Cache Compression](https://dl.acm.org/doi/10.1145/3759441.3759448)

### Tensor Parallelism & Multi-GPU
- [Osman's Odyssey: vLLM vs ExLlamaV2 for Multi-GPU](https://www.ahmadosman.com/blog/do-not-use-llama-cpp-or-ollama-on-multi-gpus-setups-use-vllm-or-exllamav2/)
- [Medium: ExLlamaV2 Local LLM Inference](https://medium.com/@shouke.wei/exllamav2-revolutionizing-local-llm-inference-on-consumer-gpus-e14213f610bf)
- [Arsturn: Multi-GPU Performance Comparison](https://www.arsturn.com/blog/multi-gpu-showdown-benchmarking-vllm-llama-cpp-ollama-for-maximum-performance)

### Quantization
- [Medium: GPTQ vs AWQ Deep Dive](https://medium.com/@kimdoil1211/speeding-up-large-language-models-a-deep-dive-into-gptq-and-awq-quantization-0bb001eaabd4)
- [Poniak Times: 2025 State of Quantization](https://www.poniaktimes.com/2025-model-quantization-qlora-gptq-awq/)
- [arXiv: FireQ INT4-FP8 Quantization](https://arxiv.org/html/2505.20839)
- [NVIDIA: Optimizing LLMs with Post-Training Quantization](https://developer.nvidia.com/blog/optimizing-llms-for-performance-and-accuracy-with-post-training-quantization/)
- [NVIDIA: FP8 Training Introduction](https://developer.nvidia.com/blog/floating-point-8-an-introduction-to-efficient-lower-precision-ai-training/)

### FlashAttention & FlashInfer
- [GitHub - FlashInfer](https://github.com/flashinfer-ai/flashinfer)
- [FlashInfer 0.2 Release Blog](https://flashinfer.ai/2024/12/16/flashinfer-v02-release.html)
- [FlashInfer: Introducing Efficient Attention](https://flashinfer.ai/2024/02/02/introduce-flashinfer.html)
- [arXiv: FlashInfer Paper](https://www.arxiv.org/pdf/2501.01005)

### Inference Engine Comparisons
- [AIMultiple: vLLM vs LMDeploy vs SGLang](https://research.aimultiple.com/inference-engines/)
- [Medium: SGLang vs vLLM Benchmarks](https://medium.com/@saidines12/sglang-vs-vllm-part-1-benchmark-performance-3231a41033ca)
- [Cerebrium: Benchmarking Llama 3.1 APIs](https://www.cerebrium.ai/blog/benchmarking-vllm-sglang-tensorrt-for-llama-3-1-api)
- [Kanerika: SGLang vs vLLM Use Cases](https://kanerika.com/blogs/sglang-vs-vllm/)

### Hardware & GPU Optimization
- [Best GPUs for AI 2025](https://www.bestgpusforai.com/blog/best-gpus-for-ai)
- [RTX 5090 vs RTX 4090 for AI](https://bizon-tech.com/blog/nvidia-rtx-5090-comparison-gpu-benchmarks-for-ai)
- [Puget Systems: RTX 5090/5080 AI Review](https://www.pugetsystems.com/labs/articles/nvidia-geforce-rtx-5090-amp-5080-ai-review/)
- [DatabaseMart: 2×RTX 5090 Ollama Benchmark](https://www.databasemart.com/blog/ollama-gpu-benchmark-rtx5090-2)

### Sparse Attention & Mixture of Depths
- [arXiv: Mixture of Attention Spans](https://arxiv.org/abs/2406.14909)
- [ICLR 2025: γ-MoD Paper](https://proceedings.iclr.cc/paper_files/paper/2025/file/b3847cda0c8cc0cfcdacf462dc122214-Paper-Conference.pdf)
- [GitHub - MoA: Mixture of Sparse Attention](https://github.com/thu-nics/MoA)
- [arXiv: SeerAttention](https://arxiv.org/abs/2410.13276)

### Draft Model Selection & Training
- [LM Studio: Speculative Decoding Guide](https://lmstudio.ai/docs/app/advanced/speculative-decoding)
- [arXiv: Training Domain Draft Models](https://arxiv.org/html/2503.07807)
- [vLLM: Speculative Decoding Docs](https://docs.vllm.ai/en/latest/features/spec_decode/)

### 70B Model Optimization
- [NutStudio: Best GPU for Local LLM](https://nutstudio.imyfone.com/llm-tips/best-gpu-for-local-llm/)
- [LocalLLM.in: Best GPUs for Inference 2025](https://localllm.in/blog/best-gpus-llm-inference-2025)
- [Introl: Local LLM Hardware Guide](https://introl.com/blog/local-llm-hardware-pricing-guide-2025)

---

**Document Version:** 1.0
**Research Completed:** December 16, 2025
**Next Review:** January 16, 2026 (Monthly technology watch)
**Status:** Production-Ready Recommendations
