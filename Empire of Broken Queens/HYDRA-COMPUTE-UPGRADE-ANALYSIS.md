# Hydra Cluster - hydra-compute GPU Upgrade Analysis

## Executive Summary

**Change:** Replacing RTX 3060 12GB with second RTX 5070 Ti 16GB on hydra-compute

**Impact:** This upgrade **simplifies** the architecture significantly by creating a homogeneous GPU pool on the generation node.

### Before vs After

```
BEFORE:                                    AFTER:
hydra-compute (heterogeneous)              hydra-compute (homogeneous)
├── RTX 5070 Ti (16GB) - Blackwell        ├── RTX 5070 Ti (16GB) - Blackwell
└── RTX 3060 (12GB) - Ampere              └── RTX 5070 Ti (16GB) - Blackwell

Total VRAM: 28GB                           Total VRAM: 32GB (+4GB)
Total TGP: 470W                            Total TGP: 600W (+130W)
GPU Scheduling: Complex (heterogeneous)    GPU Scheduling: Simple (identical)
```

### Cluster Totals

| Node | Before | After | Change |
|------|--------|-------|--------|
| hydra-ai | 56GB (5090+4090) | 56GB | No change |
| hydra-compute | 28GB (5070Ti+3060) | 32GB (5070Ti×2) | +4GB |
| **Total** | **84GB** | **88GB** | **+4GB** |

---

## Part 1: Power & Thermal Analysis

### Power Requirements

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| GPU TGP (max) | 470W | 600W | +130W |
| Estimated system total | ~620W | ~750W | +130W |
| Recommended PSU | 750W | 850W+ | +100W |

**Power Sources:**
- [RTX 5070 Ti: 300W TGP](https://www.techpowerup.com/gpu-specs/geforce-rtx-5070-ti.c4243)
- [RTX 3060: 170W TGP](https://www.techpowerup.com/gpu-specs/geforce-rtx-3060-12-gb.c3682)

### Thermal Considerations

1. **Increased heat output** - 130W more to dissipate
2. **Case airflow** - Verify adequate cooling for two 300W cards
3. **GPU slot spacing** - Ensure cards have adequate gap for cooling
4. **Ambient temperature** - May run warmer, monitor closely initially

### Action Items
- [x] Verify PSU capacity ≥850W with 80+ Gold rating → **CONFIRMED: 1000W PSU**
- [x] Check 12V rail can deliver ~50A combined → **1000W adequate**
- [ ] Ensure adequate case airflow
- [ ] Apply undervolt for thermals: `nvidia-smi -pl 250` or use MSI Afterburner curve

---

## Part 2: What This Upgrade SIMPLIFIES

### 2.1 GPU Scheduling (Major Simplification)

**BEFORE:** Complex heterogeneous scheduling
```yaml
# Had to differentiate GPU types
nodeSelector:
  hydra.io/has-5070ti: "true"   # For image gen
nodeSelector:
  hydra.io/has-3060: "true"      # For voice/video

# Different workloads had different GPU requirements
env:
  - name: CUDA_VISIBLE_DEVICES
    value: "1"  # Explicitly select 3060
```

**AFTER:** Simple homogeneous pool
```yaml
# Any GPU on hydra-compute is identical
nodeSelector:
  kubernetes.io/hostname: hydra-compute
resources:
  limits:
    nvidia.com/gpu: 1  # Either GPU works equally well
```

### 2.2 Node Labels (Simplified)

**BEFORE:**
```yaml
hydra.io/vram-total: "28"
hydra.io/has-5070ti: "true"
hydra.io/has-3060: "true"
hydra.io/gpu-classes: "5070ti,3060"  # Multiple classes
```

**AFTER:**
```yaml
hydra.io/vram-total: "32"
hydra.io/has-5070ti: "true"
hydra.io/gpu-class: "5070ti"   # Single class
hydra.io/gpu-count: "2"        # Count of identical GPUs
```

### 2.3 Workload Distribution (Simplified)

**BEFORE:** Workload-specific GPU assignment
| Workload | Assigned GPU | Reason |
|----------|-------------|--------|
| ComfyUI | RTX 5070 Ti | Needs 16GB VRAM |
| LoRA Training | RTX 5070 Ti | Needs 14GB+ VRAM |
| GPT-SoVITS | RTX 3060 | 12GB sufficient |
| Ollama small | RTX 3060 | 8GB sufficient |
| AnimateDiff | RTX 3060 | Video secondary task |

**AFTER:** Any workload can use any GPU
| Workload | Assigned GPU | Reason |
|----------|-------------|--------|
| ComfyUI | Either | Both have 16GB |
| LoRA Training | Either | Both have 16GB |
| GPT-SoVITS | Either | Both have 16GB |
| Ollama small | Either | Both have 16GB |
| AnimateDiff | Either | Both have 16GB |

### 2.4 Driver & Architecture Uniformity

**BEFORE:**
- Blackwell (5070 Ti) + Ampere (3060) = Different architectures
- Potential driver compatibility edge cases
- Different CUDA compute capabilities (SM 100 vs SM 86)
- Different optimization paths

**AFTER:**
- Dual Blackwell = Identical architecture
- Single driver optimization path
- Same CUDA compute capability (SM 100)
- Same DLSS 4 / Frame Generation support
- Same encoding/decoding capabilities

---

## Part 3: New Capabilities Enabled

### 3.1 True Parallel Processing

With two identical GPUs, we can now run **identical parallel workloads**:

```
┌────────────────────────────────────────────────────────────────┐
│                    hydra-compute (dual 5070 Ti)                │
│                                                                │
│    ┌─────────────────────┐    ┌─────────────────────┐         │
│    │   GPU 0: 5070 Ti    │    │   GPU 1: 5070 Ti    │         │
│    │                     │    │                     │         │
│    │  ComfyUI Instance 1 │    │  ComfyUI Instance 2 │         │
│    │  Generating Queen A │    │  Generating Queen B │         │
│    │                     │    │                     │         │
│    └─────────────────────┘    └─────────────────────┘         │
│                                                                │
│    Result: 2x image generation throughput                      │
└────────────────────────────────────────────────────────────────┘
```

**Throughput gains:**
- Image generation: 2x (two parallel ComfyUI)
- Voice synthesis: 2x (two parallel GPT-SoVITS)
- Video generation: 2x (two parallel AnimateDiff)

### 3.2 Multi-GPU Training (Data Parallel)

Can now use both GPUs for faster LoRA training:

```python
# PyTorch DataParallel across both GPUs
model = torch.nn.DataParallel(model, device_ids=[0, 1])

# Or use distributed training
accelerate launch --multi_gpu --num_processes=2 train.py
```

**Training speedup:**
- LoRA training: ~1.8x faster (data parallel scaling)
- Effective batch size: 2x with gradient accumulation

### 3.3 32GB Combined VRAM Pool (Potential)

While not NVLink, the two 5070 Ti cards could theoretically be used together:

```
Total addressable VRAM: 32GB combined
Possible models:
- 33B parameter models at 4-bit (~16GB needed per GPU in split)
- Larger diffusion models with model offloading
- Bigger batch sizes for training
```

**Note:** Without NVLink, PCIe communication adds overhead. Best for embarrassingly parallel workloads rather than tensor parallel.

### 3.4 Redundancy & Load Balancing

```yaml
# Kubernetes deployment with anti-affinity
spec:
  replicas: 2
  template:
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: comfyui
                topologyKey: "nvidia.com/gpu"
```

- If one GPU fails, workloads continue on the other
- Load balancer can distribute requests across instances
- No single point of failure for generation pipeline

---

## Part 4: Architecture Changes Required

### 4.1 Kubernetes Node Labels (Update)

**REMOVE:**
```yaml
hydra.io/has-3060: "true"
```

**UPDATE:**
```yaml
# Old
hydra.io/vram-total: "28"

# New
hydra.io/vram-total: "32"
hydra.io/gpu-class: "5070ti"
hydra.io/gpu-count: "2"
hydra.io/homogeneous: "true"  # New flag for identical GPUs
```

### 4.2 K3s Agent Configuration (Update)

```nix
# /etc/nixos/k3s-agent.nix - UPDATED

services.k3s = {
  enable = true;
  role = "agent";
  serverAddr = "https://192.168.1.250:6443";
  token = k3sToken;

  extraFlags = toString [
    "--kubelet-arg=max-pods=110"
    # Updated labels
    "--node-label=hydra.io/workload=generation"
    "--node-label=hydra.io/workload=training"
    "--node-label=hydra.io/vram-total=32"           # Was 28
    "--node-label=hydra.io/gpu-class=5070ti"        # Single class
    "--node-label=hydra.io/gpu-count=2"             # New
    "--node-label=hydra.io/homogeneous=true"        # New
    # REMOVED: --node-label=hydra.io/has-3060=true
  ];
};
```

### 4.3 Resource Profiles (Simplified)

**BEFORE:** Needed different profiles for different GPUs
```yaml
resourceProfiles:
  comfyui:
    gpu: "5070ti"
    vram: 10240
  voice:
    gpu: "3060"
    vram: 8192
  video:
    gpu: "3060"
    vram: 10240
```

**AFTER:** Single profile for all workloads
```yaml
resourceProfiles:
  generation:
    gpu: "5070ti"
    vramPerGpu: 16384
    maxWorkloads: 2
    parallelCapable: true
```

### 4.4 Workload Queue Strategy (Simplified)

**BEFORE:** Separate queues per GPU type
```
Queue: 5070ti-queue → ComfyUI, LoRA
Queue: 3060-queue → Voice, Video, Small LLM
```

**AFTER:** Single unified queue
```
Queue: hydra-compute-pool → All generation workloads
  - Scheduler picks any available GPU
  - Simple FIFO or priority-based
  - Load balancing automatic
```

### 4.5 ComfyUI Deployment (Enable Parallel)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: comfyui
  namespace: ai-workloads
spec:
  replicas: 2  # Run two instances!
  selector:
    matchLabels:
      app: comfyui
  template:
    metadata:
      labels:
        app: comfyui
    spec:
      runtimeClassName: nvidia
      nodeSelector:
        kubernetes.io/hostname: hydra-compute
      containers:
        - name: comfyui
          image: ghcr.io/ai-dock/comfyui:latest
          ports:
            - containerPort: 8188
          resources:
            limits:
              nvidia.com/gpu: 1  # One GPU each
              memory: "24Gi"
            requests:
              nvidia.com/gpu: 1
              memory: "16Gi"
---
# Load balancer service
apiVersion: v1
kind: Service
metadata:
  name: comfyui-lb
spec:
  type: LoadBalancer
  selector:
    app: comfyui
  ports:
    - port: 8188
      targetPort: 8188
```

---

## Part 5: Schema Architecture Updates

### 5.1 GPU Resource Schema (Simplified)

**BEFORE:**
```typescript
interface GpuResource {
  nodeId: string;
  gpuIndex: number;
  gpuClass: '5090' | '4090' | '5070ti' | '3060';
  vram: number;
  capabilities: string[];
}
```

**AFTER:**
```typescript
interface GpuResource {
  nodeId: string;
  gpuIndex: number;
  gpuClass: '5090' | '4090' | '5070ti';  // Removed 3060
  vram: number;
  capabilities: string[];
}

// New: GPU pool concept
interface GpuPool {
  nodeId: string;
  gpuClass: string;
  count: number;
  homogeneous: boolean;
  totalVram: number;
  availableSlots: number;
}
```

### 5.2 Workload Profile Schema (Simplified)

**BEFORE:**
```typescript
interface WorkloadProfile {
  name: string;
  gpuRequirements: {
    preferredClass: string[];  // List of acceptable GPU classes
    minVram: number;
    preferHeterogeneous: boolean;
  };
}
```

**AFTER:**
```typescript
interface WorkloadProfile {
  name: string;
  gpuRequirements: {
    minVram: number;
    preferNode?: string;  // Optional node preference
    parallelCapable: boolean;  // Can use multiple GPUs
  };
}
```

### 5.3 Database Schema (Minor Update)

```sql
-- Update queens.generation_config
-- No longer need gpu_preference field

-- Update generation_tasks
ALTER TABLE generation_tasks
  DROP COLUMN IF EXISTS preferred_gpu_class;

-- Simplify to just node preference
ALTER TABLE generation_tasks
  ADD COLUMN IF NOT EXISTS target_node VARCHAR(50) DEFAULT 'hydra-compute';
```

---

## Part 6: Empire of Broken Queens Impact

### 6.1 Generation Pipeline (Doubled Throughput)

**BEFORE (Sequential):**
```
Time 0:00 - Generate Emilie portrait (5070 Ti)
Time 0:30 - Generate Jordan portrait (5070 Ti)
Time 1:00 - Generate Nikki portrait (5070 Ti)
...
```

**AFTER (Parallel):**
```
Time 0:00 - Generate Emilie portrait (GPU 0) + Jordan portrait (GPU 1)
Time 0:30 - Generate Nikki portrait (GPU 0) + Puma portrait (GPU 1)
...

Throughput: 2x faster
```

### 6.2 Overnight Generation Capacity

**BEFORE:**
- ~30 seconds per image
- ~120 images/hour
- ~960 images/night (8 hours)

**AFTER:**
- ~30 seconds per image × 2 GPUs
- ~240 images/hour
- **~1,920 images/night** (2x improvement)

### 6.3 LoRA Training (Faster)

Using data parallel training across both GPUs:

```bash
# Launch multi-GPU training
accelerate launch \
  --multi_gpu \
  --num_processes 2 \
  --mixed_precision bf16 \
  train_network.py \
  --network_dim 64 \
  --train_batch_size 2  # Effective batch size 4
```

**Training time reduction:** ~45% faster per LoRA

---

## Part 7: What I Would NOT Change

### 7.1 Overall Architecture

The fundamental architecture remains sound:
- hydra-ai for inference (5090+4090) - No change needed
- hydra-compute for generation (now 5070Ti×2) - Simplified
- hydra-storage for data (Unraid) - No change needed

### 7.2 K3s Kubernetes Strategy

The K3s on NixOS approach is still correct:
- Declarative configuration
- GPU scheduling via containerd/CDI
- NFS storage backend
- Kueue for job queuing

### 7.3 Database Architecture

PostgreSQL, Redis, Qdrant schema designs unchanged:
- Queen entity model: No change
- Generation tasks: Minor simplification
- Quality metrics: No change

### 7.4 Observability Stack

Prometheus/Grafana/Loki configuration stays the same:
- Just update dashboard labels
- Remove 3060-specific panels
- Add parallel workload metrics

---

## Part 8: Migration Checklist

### Hardware Phase
- [x] Verify PSU ≥850W with adequate 12V rail → **1000W confirmed**
- [ ] Physically install second RTX 5070 Ti
- [ ] Verify both cards detected: `nvidia-smi`
- [ ] Test thermal under load: monitor temps for 30 minutes
- [ ] Apply undervolt: `nvidia-smi -pl 250` (both GPUs)

### Software Phase
- [ ] Update NixOS configuration with new labels
- [ ] Run `sudo nixos-rebuild switch`
- [ ] Verify K3s agent reconnects with new labels
- [ ] Update any hardcoded GPU references

### Workload Phase
- [ ] Scale ComfyUI deployment to 2 replicas
- [ ] Test parallel generation
- [ ] Update generation scripts for dual GPU
- [ ] Verify load balancing works

### Documentation Phase
- [ ] Update CLAUDE.md with new configuration
- [ ] Update KUBERNETES-NIXOS-ARCHITECTURE.md
- [ ] Update HYDRA-SCHEMA-ARCHITECTURE.md
- [ ] Archive this analysis document

---

## Conclusion

**The upgrade is a net positive that simplifies the architecture.**

Key benefits:
1. **+4GB VRAM** (28→32GB on hydra-compute)
2. **2x throughput** potential with parallel processing
3. **Simpler scheduling** with homogeneous GPU pool
4. **Uniform architecture** (all Blackwell on compute node)
5. **Better redundancy** with identical GPUs

Key considerations:
1. **+130W power draw** - verify PSU capacity
2. **Thermal management** - monitor closely initially
3. **Documentation updates** - several files need changes

**Recommendation:** Proceed with the upgrade. The architectural simplification alone justifies the change, and the doubled throughput is a significant bonus for the generation pipeline.

---

*Analysis Version: 1.0*
*Generated: December 12, 2025*
*Author: Hydra Autonomous Steward*
