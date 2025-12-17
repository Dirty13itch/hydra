# Sandbox Evaluation: Docker vs E2B/Firecracker

## Current Implementation

Hydra uses Docker-based sandboxing with:
- Network isolation (--network=none)
- Memory/CPU limits (256MB, 0.5 CPU)
- Dropped capabilities
- Read-only root filesystem
- 30-second timeout

## E2B/Firecracker Comparison

| Feature | Docker (Current) | E2B/Firecracker |
|---------|------------------|-----------------|
| Isolation | Container (shared kernel) | MicroVM (separate kernel) |
| Boot time | ~1s | <200ms |
| Security | Process-level | Hardware-level |
| GPU Access | Yes | No (PCIe unsupported) |
| Cost | Free (self-hosted) | Cloud pricing |
| Session Limit | None | 24 hours |
| Attack Surface | Larger (kernel shared) | Minimal |

## E2B Benefits

1. **Stronger Isolation**: Hardware-level via KVM, not kernel namespaces
2. **Faster Boot**: <200ms vs ~1s Docker start
3. **Pre-warmed Pools**: Near-instant availability
4. **MCP Integration**: Official Docker partnership (Oct 2025)

## E2B Limitations

1. **No GPU Passthrough**: Firecracker lacks PCIe support
2. **Cloud Only**: Requires E2B cloud (latency + cost)
3. **24-Hour Sessions**: Not suitable for long-running tasks
4. **Cost**: Per-use pricing vs free Docker

## Recommendation

**Keep Docker for now**, with potential E2B upgrade path:

### When Docker is Sufficient
- Code testing and validation
- Local development iterations
- Workloads needing GPU
- Cost-sensitive operations

### When to Consider E2B
- Production deployments with untrusted code
- Public-facing code execution
- High-security requirements
- When cold-start latency matters

## Security Enhancements for Current Sandbox

Instead of full E2B migration, enhance Docker sandbox:

```yaml
# docker-compose security additions
security_opt:
  - no-new-privileges:true
  - seccomp:seccomp-profile.json
cap_drop:
  - ALL
read_only: true
tmpfs:
  - /tmp:size=10M,noexec
pids_limit: 100
ulimits:
  nproc: 64
  nofile:
    soft: 100
    hard: 200
```

## Self-Hosted Firecracker Option

For maximum security without cloud dependency:

1. Install Firecracker on hydra-compute
2. Use containerd + firecracker-containerd
3. Build custom microVM images
4. Requires significant setup effort

This provides E2B-level security without cloud costs but requires:
- KVM support (available on NixOS nodes)
- ~20 hours setup time
- Custom orchestration layer

## Sources

- [E2B Documentation](https://e2b.dev/docs)
- [Firecracker vs QEMU](https://e2b.dev/blog/firecracker-vs-qemu)
- [E2B GitHub](https://github.com/e2b-dev)
