# Rule: Discovery Before Action

**Priority:** CRITICAL

Before implementing ANY change to the Hydra cluster:

1. **Read relevant knowledge files** - Check `knowledge/*.md` for the domain
2. **Verify current state** - Run health checks before modifying
3. **Check what's running** - Don't assume, verify with `docker ps`, `systemctl status`, etc.

## Knowledge File Index

| Domain | File | When to Read |
|--------|------|--------------|
| Hardware/Network | `knowledge/infrastructure.md` | Node operations, network issues |
| Inference | `knowledge/inference-stack.md` | Model loading, TabbyAPI, LiteLLM |
| Databases | `knowledge/databases.md` | PostgreSQL, Qdrant, Redis |
| Models | `knowledge/models.md` | Model selection, downloads |
| Monitoring | `knowledge/observability.md` | Prometheus, Grafana, Loki |
| Automation | `knowledge/automation.md` | n8n, workflows |

## Quick Health Check

```bash
# Before any changes, verify cluster health
curl -s http://192.168.1.244:8700/health | jq .
```
