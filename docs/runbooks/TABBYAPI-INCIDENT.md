# TabbyAPI Incident Runbook

**Service:** TabbyAPI (ExLlamaV2 inference server)
**Node:** hydra-ai (192.168.1.250)
**Port:** 5000
**Last Updated:** 2025-12-19

## Quick Reference

```bash
# SSH to hydra-ai
ssh typhon@192.168.1.250

# Check service status
sudo systemctl status tabbyapi

# View logs
sudo journalctl -u tabbyapi -f --no-pager -n 100

# Restart service
sudo systemctl restart tabbyapi

# Verify health
curl -s http://192.168.1.250:5000/health | jq .
```

---

## Alert Response

### TabbyAPIDown (Critical)

**Alert:** `TabbyAPI has been unreachable for over 1 minute`

1. **Check if service is running:**
   ```bash
   ssh typhon@192.168.1.250 "sudo systemctl status tabbyapi"
   ```

2. **If service is stopped, check why:**
   ```bash
   ssh typhon@192.168.1.250 "sudo journalctl -u tabbyapi --no-pager -n 50"
   ```

3. **Common causes:**
   - VRAM exhausted (OOM killed)
   - NixOS rebuild changed library paths
   - Port conflict with zombie process
   - Model file corrupted or missing

4. **Resolution:**
   ```bash
   # Clear orphan processes and restart
   ssh typhon@192.168.1.250 "sudo systemctl restart tabbyapi"

   # Verify recovery
   sleep 30 && curl -s http://192.168.1.250:5000/health
   ```

---

### TabbyAPINoModel (Warning)

**Alert:** `TabbyAPI is running but no model is loaded`

1. **Check current model status:**
   ```bash
   curl -s http://192.168.1.250:5000/v1/model | jq .
   ```

2. **Check available VRAM:**
   ```bash
   ssh typhon@192.168.1.250 "nvidia-smi --query-gpu=memory.free,memory.total --format=csv"
   ```

3. **Load the default model:**
   ```bash
   curl -X POST http://192.168.1.250:5000/v1/model/load \
     -H "Content-Type: application/json" \
     -d '{"model_name": "Midnight-Miqu-70B-v1.5-exl2-2.5bpw"}'
   ```

4. **If model fails to load:**
   - Check `/mnt/models` mount is working
   - Verify model directory exists
   - Check VRAM availability (need ~50GB for 70B 2.5bpw)

---

### TabbyAPIRestartLoop (Critical)

**Alert:** `TabbyAPI has restarted more than 3 times in 10 minutes`

This indicates a systemic issue. DO NOT just restart again.

1. **Stop the restart loop:**
   ```bash
   ssh typhon@192.168.1.250 "sudo systemctl stop tabbyapi"
   ```

2. **Identify root cause from logs:**
   ```bash
   ssh typhon@192.168.1.250 "sudo journalctl -u tabbyapi --since '10 min ago' --no-pager"
   ```

3. **Check for common issues:**

   **a) VRAM issues:**
   ```bash
   ssh typhon@192.168.1.250 "nvidia-smi"
   ```
   - If VRAM is full from leaked processes, reboot GPUs:
   ```bash
   ssh typhon@192.168.1.250 "sudo systemctl stop tabbyapi && sudo nvidia-smi --gpu-reset && sudo systemctl start tabbyapi"
   ```

   **b) Library path issues (after NixOS rebuild):**
   ```bash
   ssh typhon@192.168.1.250 "ldd /opt/tabbyapi/venv/lib/python3.11/site-packages/exllamav2_ext.*.so"
   ```
   - If libraries are missing, rebuild venv:
   ```bash
   ssh typhon@192.168.1.250 "cd /opt/tabbyapi && rm -rf venv && python -m venv venv && ./venv/bin/pip install -r requirements.txt"
   ```

   **c) Port conflict:**
   ```bash
   ssh typhon@192.168.1.250 "lsof -i :5000"
   ```
   - Kill orphan processes:
   ```bash
   ssh typhon@192.168.1.250 "sudo kill -9 \$(lsof -ti:5000)"
   ```

4. **After fixing, start service:**
   ```bash
   ssh typhon@192.168.1.250 "sudo systemctl start tabbyapi"
   ```

---

### TabbyAPISlowHealthCheck (Warning)

**Alert:** `Health check latency exceeds 2000ms`

1. **Check GPU utilization:**
   ```bash
   ssh typhon@192.168.1.250 "nvidia-smi dmon -s u -d 1 -c 5"
   ```

2. **Check if inference is blocked:**
   ```bash
   curl -s http://192.168.1.250:5000/v1/completions \
     -H "Content-Type: application/json" \
     -d '{"prompt":"test","max_tokens":1}' \
     -w "\nTime: %{time_total}s\n"
   ```

3. **If consistently slow:**
   - Check for thermal throttling: `nvidia-smi -q -d TEMPERATURE`
   - Check power limits: `nvidia-smi -q -d POWER`
   - Consider reducing context length or batch size

---

## Preventive Measures

### Before NixOS Rebuild

1. **Always test in dry-run first:**
   ```bash
   sudo nixos-rebuild dry-build
   ```

2. **After rebuild, verify TabbyAPI:**
   ```bash
   /mnt/user/appdata/hydra-dev/scripts/verify-inference-stack.sh
   ```

### Before Loading Large Models

1. **Check available VRAM:**
   ```bash
   nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits
   ```

2. **Model VRAM requirements:**
   | Model | BPW | VRAM Required |
   |-------|-----|---------------|
   | 70B | 2.5 | ~48GB |
   | 70B | 3.0 | ~55GB |
   | 70B | 4.0 | ~65GB |

3. **Set power limits before heavy load:**
   ```bash
   ssh typhon@192.168.1.250 "sudo nvidia-smi -pl 450"  # RTX 5090
   ssh typhon@192.168.1.250 "sudo nvidia-smi -i 1 -pl 300"  # RTX 4090
   ```

---

## Recovery Procedures

### Full Service Recovery

```bash
# 1. Stop service
ssh typhon@192.168.1.250 "sudo systemctl stop tabbyapi"

# 2. Clear GPU memory
ssh typhon@192.168.1.250 "sudo nvidia-smi --gpu-reset"

# 3. Clear any orphan processes
ssh typhon@192.168.1.250 "pkill -f 'python.*/opt/tabbyapi' || true"

# 4. Verify mounts
ssh typhon@192.168.1.250 "ls /mnt/models"

# 5. Start service
ssh typhon@192.168.1.250 "sudo systemctl start tabbyapi"

# 6. Wait and verify
sleep 60
curl -s http://192.168.1.250:5000/health | jq .
curl -s http://192.168.1.250:5000/v1/model | jq .
```

### LiteLLM Fallback Verification

If TabbyAPI is down, verify fallback is working:

```bash
# This should fallback to Ollama
curl -X POST http://192.168.1.244:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"tabby","messages":[{"role":"user","content":"test"}],"max_tokens":5}'
```

---

## Escalation

If unable to resolve within 30 minutes:

1. Check for known issues: https://github.com/theroyallab/tabbyAPI/issues
2. Review recent changes to `/etc/nixos/configuration.nix`
3. Consider loading a smaller model temporarily
4. As last resort: reboot hydra-ai node

---

## Related Resources

- [TabbyAPI GitHub](https://github.com/theroyallab/tabbyAPI)
- [ExLlamaV2 Documentation](https://github.com/turboderp/exllamav2)
- Verification script: `/mnt/user/appdata/hydra-dev/scripts/verify-inference-stack.sh`
- Stability analysis: `/mnt/user/appdata/hydra-dev/docs/TABBYAPI_STABILITY_ANALYSIS.md`
