# Rule: Test Before Commit

**Priority:** HIGH

## Validation Steps

1. **Dry-run first** - Use `--dry-run` flags where available
2. **Verify after deployment** - Check service health
3. **Know rollback path** - Have a plan before changes

## Docker Service Changes

```bash
# Validate compose file
docker-compose config

# Deploy
docker-compose up -d <service>

# Verify health
docker-compose ps
docker-compose logs -f <service>
```

## NixOS Changes

```bash
# Test build first
sudo nixos-rebuild dry-build

# Only then apply
sudo nixos-rebuild switch
```

## Model Loading

```bash
# Check VRAM before loading
nvidia-smi --query-gpu=memory.free --format=csv

# Verify model loaded
curl -s http://192.168.1.250:5000/v1/model | jq .
```
