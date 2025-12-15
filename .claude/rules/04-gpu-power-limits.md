# Rule: GPU Power Limits

**Priority:** HIGH

Set power limits BEFORE heavy inference workloads to prevent UPS overload.

## Power Limits by GPU

| GPU | Node | Power Limit |
|-----|------|-------------|
| RTX 5090 | hydra-ai | 450W |
| RTX 4090 | hydra-ai | 300W |
| RTX 5070 Ti (x2) | hydra-compute | 250W each |

## Constraint: UPS Capacity

Total UPS capacity: **2000W**
hydra-ai alone can peak: **1400W**

## Commands

```bash
# Check current power draw
nvidia-smi --query-gpu=power.draw,power.limit --format=csv

# Set power limit (requires sudo)
sudo nvidia-smi -pl 450  # RTX 5090
sudo nvidia-smi -pl 300  # RTX 4090
```

## VRAM Constraints

| Node | Total VRAM | Max Model Size |
|------|-----------|----------------|
| hydra-ai | 56GB (32+24) | ~50GB loaded |
| hydra-compute | 32GB (16+16) | ~28GB loaded |
