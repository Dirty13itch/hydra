# Performance Tuning Runbook

Procedures for optimizing Hydra cluster performance.

## GPU Configuration

### Set Power Limits

Always set power limits before heavy workloads to protect UPS:

```bash
# hydra-ai: RTX 5090 (32GB) + RTX 4090 (24GB)
ssh typhon@192.168.1.250 "sudo nvidia-smi -i 0 -pl 450 && sudo nvidia-smi -i 1 -pl 300"

# hydra-compute: RTX 5070 Ti (16GB) + RTX 3060 (12GB)
ssh typhon@192.168.1.203 "sudo nvidia-smi -i 0 -pl 250 && sudo nvidia-smi -i 1 -pl 170"
```

### Optimize GPU Memory

```bash
# Enable persistence mode (keeps driver loaded)
sudo nvidia-smi -pm 1

# Set compute mode to exclusive (one process per GPU)
sudo nvidia-smi -c EXCLUSIVE_PROCESS

# Reset to default (shared mode)
sudo nvidia-smi -c DEFAULT
```

---

## TabbyAPI Tuning

### Model Loading Optimization

**GPU Split for 70B models:**
```yaml
# /opt/tabbyapi/config.yml
model:
  model_name: Llama-3.3-70B-Instruct-exl2-4.0bpw
  max_seq_len: 8192
  gpu_split: [0.65, 0.35]  # 5090 gets more
  cache_mode: Q4          # Quantized KV cache saves VRAM
  cache_size: 8192
  chunk_size: 2048
  num_experts_per_token: 2  # For MoE models
```

**Fast inference settings:**
```yaml
generation:
  temperature: 0.7
  top_p: 0.9
  top_k: 40
  repetition_penalty: 1.05
  max_tokens: 2048
```

### Context Length vs Speed Trade-off

| max_seq_len | VRAM Usage | Speed | Use Case |
|-------------|------------|-------|----------|
| 4096 | ~45GB | Fast | Quick responses |
| 8192 | ~48GB | Medium | Default |
| 16384 | ~52GB | Slower | Document analysis |
| 32768 | ~56GB | Slowest | Long context needed |

### Restart with New Config

```bash
ssh typhon@192.168.1.250
sudo nano /opt/tabbyapi/config.yml
sudo systemctl restart tabbyapi
journalctl -u tabbyapi -f  # Watch for errors
```

---

## Ollama Tuning

### Model Quantization

```bash
# Check available quantizations
ollama show qwen2.5:14b --modelfile

# Pull specific quantization
ollama pull qwen2.5:14b-instruct-q4_K_M  # Balanced
ollama pull qwen2.5:14b-instruct-q5_K_M  # Higher quality
ollama pull qwen2.5:14b-instruct-q8_0    # Best quality
```

### Parallel Requests

```bash
# Set OLLAMA_NUM_PARALLEL (in systemd unit)
# /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_NUM_PARALLEL=4"
Environment="OLLAMA_MAX_LOADED_MODELS=2"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### GPU Layers

```bash
# Force GPU layers for a model
ollama run qwen2.5:14b --gpu-layers 40

# Check how many layers are on GPU
ollama ps
```

---

## Database Performance

### PostgreSQL

```bash
# Check slow queries
docker exec hydra-postgres psql -U hydra -c "
  SELECT pid, now() - pg_stat_activity.query_start AS duration, query
  FROM pg_stat_activity
  WHERE state != 'idle' AND query_start IS NOT NULL
  ORDER BY duration DESC LIMIT 5;
"

# Check table sizes
docker exec hydra-postgres psql -U hydra -c "
  SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
  FROM pg_catalog.pg_statio_user_tables
  ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;
"

# Vacuum and analyze (maintenance)
docker exec hydra-postgres psql -U hydra -c "VACUUM ANALYZE;"
```

### Qdrant

```bash
# Check collection stats
curl -s http://192.168.1.244:6333/collections/memory/points/count | jq .

# Optimize collection (defragment)
curl -X POST "http://192.168.1.244:6333/collections/memory/index" \
  -H "Content-Type: application/json" \
  -d '{"vectors": {}}'

# Check indexing status
curl -s http://192.168.1.244:6333/collections/memory | jq '.result.status'
```

### Redis

```bash
# Check memory usage
docker exec hydra-redis redis-cli -a 'PASSWORD' info memory

# Check slow operations
docker exec hydra-redis redis-cli -a 'PASSWORD' slowlog get 10

# Set max memory (2GB limit)
docker exec hydra-redis redis-cli -a 'PASSWORD' config set maxmemory 2gb
docker exec hydra-redis redis-cli -a 'PASSWORD' config set maxmemory-policy allkeys-lru
```

---

## Network Optimization

### Verify 10GbE Usage

```bash
# Check link speed
ethtool enp6s0 | grep Speed

# Monitor throughput
iftop -i enp6s0

# Test bandwidth between nodes
iperf3 -s  # On one node
iperf3 -c 192.168.1.250  # From another
```

### NFS Mount Options

```bash
# Optimal NFS mount for models (in /etc/nixos/configuration.nix)
fileSystems."/mnt/models" = {
  device = "192.168.1.244:/mnt/user/models";
  fsType = "nfs";
  options = [
    "rsize=1048576"
    "wsize=1048576"
    "hard"
    "intr"
    "noatime"
    "nfsvers=4.2"
  ];
};
```

---

## Memory Optimization

### System Memory

```bash
# Check memory usage
free -h

# Clear page cache (safe)
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

# Check memory pressure
cat /proc/pressure/memory
```

### Swap Configuration

```bash
# Reduce swap tendency (for inference nodes)
sudo sysctl vm.swappiness=10

# Make permanent
echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
```

---

## Docker Resource Limits

### Set Container Limits

```yaml
# In docker-compose.yml
services:
  litellm:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 1G
```

### Check Container Stats

```bash
# Real-time resource usage
docker stats --no-stream

# Specific container
docker stats litellm --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

## Benchmark & Verify

### Inference Benchmark

```bash
# Run benchmark script
python scripts/benchmark-inference.py --endpoint tabbyapi --iterations 10

# Quick test
time curl -s -X POST http://192.168.1.250:5000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a haiku about AI", "max_tokens": 50}' | jq .usage
```

### Expected Performance

| Model | Endpoint | Tokens/sec | TTFT |
|-------|----------|------------|------|
| 70B @ 4bpw | TabbyAPI | 15-25 | 0.5-1s |
| 8B @ 6bpw | TabbyAPI | 80-120 | 0.1-0.3s |
| 14B q4_K_M | Ollama | 40-60 | 0.3-0.5s |
| 7B q4_K_M | Ollama | 80-100 | 0.1-0.2s |

### Network Latency Check

```bash
# Inter-node latency
for ip in 192.168.1.250 192.168.1.203 192.168.1.244; do
    ping -c 5 $ip | tail -1
done

# Expected: <0.5ms on 10GbE LAN
```

---

## Troubleshooting Slow Performance

1. **Check GPU utilization**
   ```bash
   nvidia-smi dmon -s u  # GPU utilization monitor
   ```

2. **Check if thermal throttling**
   ```bash
   nvidia-smi --query-gpu=temperature.gpu,clocks.gr,clocks.mem --format=csv -l 1
   ```

3. **Check NFS latency**
   ```bash
   time ls /mnt/models
   # Should be <100ms
   ```

4. **Check container bottleneck**
   ```bash
   docker stats --no-stream | sort -k 3 -h -r | head
   ```

5. **Check disk I/O**
   ```bash
   iostat -x 1 5
   ```
