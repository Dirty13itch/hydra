# Maintenance Runbook

Regular maintenance procedures for the Hydra cluster.

## Daily Tasks (Automated)

These are handled automatically but can be manually verified:

- [ ] Backup verification (2:30 AM)
- [ ] Health check alerts working
- [ ] Log rotation

```bash
# Verify last backup
ls -la /mnt/user/backups/latest/

# Check health endpoint
curl -s http://192.168.1.244:8600/health/summary | jq .status
```

---

## Weekly Tasks

### Docker Cleanup

```bash
ssh root@192.168.1.244

# Remove unused images
docker image prune -f

# Remove unused volumes (careful!)
docker volume prune -f

# Remove build cache
docker builder prune -f

# Full cleanup (removes all unused)
docker system prune -f

# Check space recovered
df -h /var/lib/docker
```

### Log Review

```bash
# Check for errors in Grafana (Loki)
# http://192.168.1.244:3003/explore
# Query: {job="docker"} |= "error" | line_format "{{.container_name}}: {{.message}}"

# Or via CLI
ssh root@192.168.1.244 "docker logs --since 24h litellm 2>&1 | grep -i error | tail -20"
ssh root@192.168.1.244 "docker logs --since 24h qdrant 2>&1 | grep -i error | tail -20"
```

### NixOS Updates Check

```bash
# Check for updates (don't apply yet)
ssh typhon@192.168.1.250 "sudo nix-channel --update && nixos-rebuild dry-build"
ssh typhon@192.168.1.203 "sudo nix-channel --update && nixos-rebuild dry-build"
```

---

## Monthly Tasks

### Update Docker Images

```bash
ssh root@192.168.1.244

# Pull latest images
cd /mnt/user/appdata/hydra-stack
docker-compose pull

# Update one service at a time (safer)
docker-compose up -d --no-deps litellm
docker-compose up -d --no-deps grafana
docker-compose up -d --no-deps prometheus
# ... repeat for each service

# Or update all at once (faster but riskier)
docker-compose up -d
```

### NixOS Updates

```bash
# On each NixOS node
sudo nix-channel --update
sudo nixos-rebuild switch

# If issues, rollback
sudo nixos-rebuild switch --rollback
```

### Backup Restore Test

```bash
# Run restore test script
/mnt/user/appdata/hydra-stack/scripts/restore-test.sh

# Verify all databases restored correctly
```

### Disk Health Check

```bash
ssh root@192.168.1.244

# Check array status in Unraid UI
# http://192.168.1.244/Main

# Check SMART status
for disk in /dev/sd[a-z]; do
    echo "=== $disk ==="
    smartctl -H $disk | grep -E "result|PASSED|FAILED"
done

# Check disk space
df -h /mnt/user /mnt/cache
```

### Security Updates

```bash
# Check for vulnerable images
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image --severity CRITICAL $(docker images -q)

# Update affected images
docker-compose pull <affected-service>
docker-compose up -d <affected-service>
```

---

## Quarterly Tasks

### Full System Audit

1. **Review all services**
   ```bash
   curl -s http://192.168.1.244:8600/health/services | jq -r '.[] | "\(.name): \(.status)"'
   ```

2. **Check resource usage trends** (Grafana dashboards)

3. **Review Prometheus alerts**
   ```bash
   curl -s http://192.168.1.244:9090/api/v1/alerts | jq '.data.alerts[] | select(.state=="firing")'
   ```

4. **Audit Docker volumes**
   ```bash
   docker volume ls --format "table {{.Name}}\t{{.Driver}}"
   # Remove any orphaned volumes
   docker volume rm $(docker volume ls -qf dangling=true)
   ```

### Certificate Renewal

```bash
# Check Vaultwarden certificate expiry
openssl s_client -connect 192.168.1.244:8444 -servername localhost 2>/dev/null | \
    openssl x509 -noout -dates
```

### Password Rotation (Recommended)

Update passwords in:
- PostgreSQL
- Redis
- LiteLLM master key
- Vaultwarden admin token

```bash
# Example: Rotate PostgreSQL password
# 1. Generate new password
NEW_PASS=$(openssl rand -base64 24)

# 2. Update in PostgreSQL
docker exec hydra-postgres psql -U hydra -c "ALTER USER hydra PASSWORD '$NEW_PASS';"

# 3. Update in docker-compose.yml
# 4. Restart dependent services
docker-compose up -d litellm n8n miniflux
```

---

## Ad-Hoc Maintenance

### Clear Model Cache

```bash
# TabbyAPI
ssh typhon@192.168.1.250
rm -rf /opt/tabbyapi/cache/*
sudo systemctl restart tabbyapi

# Ollama
ssh typhon@192.168.1.203
rm -rf ~/.ollama/models/blobs/*  # Removes cached layers
```

### Compact Qdrant Collections

```bash
# Get collection names
COLLECTIONS=$(curl -s http://192.168.1.244:6333/collections | jq -r '.result.collections[].name')

# Optimize each collection
for col in $COLLECTIONS; do
    echo "Optimizing $col..."
    curl -X POST "http://192.168.1.244:6333/collections/$col/index"
done
```

### PostgreSQL Maintenance

```bash
# Vacuum all databases
docker exec hydra-postgres psql -U hydra -c "VACUUM VERBOSE ANALYZE;"

# Reindex (if queries are slow)
docker exec hydra-postgres psql -U hydra -c "REINDEX DATABASE hydra;"
```

### Check and Repair Unraid Array

```bash
# Via Unraid UI: Tools > Check Filesystem

# Or via CLI (careful!)
xfs_repair -n /dev/md1  # Check only, no repair
```

---

## Emergency Maintenance Window

When you need to take the cluster down for maintenance:

### Pre-Maintenance

1. **Notify users** (if applicable)

2. **Disable alerts**
   ```bash
   # Silence alerts in Alertmanager
   curl -X POST http://192.168.1.244:9093/api/v2/silences \
     -H "Content-Type: application/json" \
     -d '{
       "matchers": [{"name": "job", "value": ".*", "isRegex": true}],
       "startsAt": "'$(date -Iseconds)'",
       "endsAt": "'$(date -d '+2 hours' -Iseconds)'",
       "comment": "Maintenance window",
       "createdBy": "admin"
     }'
   ```

3. **Stop non-critical services**
   ```bash
   docker stop sillytavern perplexica comfyui
   ```

### During Maintenance

- Keep monitoring SSH sessions open
- Take notes of changes made
- Test after each change

### Post-Maintenance

1. **Restart services**
   ```bash
   docker-compose up -d
   ```

2. **Verify health**
   ```bash
   curl -s http://192.168.1.244:8600/health/summary | jq .
   ```

3. **Clear alert silences**
   ```bash
   # Via Alertmanager UI or API
   ```

4. **Document changes** (in git commit or changelog)

---

## Monitoring Checklist

### Daily Glance

- [ ] Grafana dashboard green
- [ ] No critical alerts
- [ ] TabbyAPI responding
- [ ] GPU temperatures normal

### Weekly Review

- [ ] Disk space > 20% free
- [ ] No unusual error patterns in logs
- [ ] Backup files recent
- [ ] Memory usage stable

### Monthly Deep Dive

- [ ] All Docker images up to date
- [ ] NixOS packages current
- [ ] Security scan clean
- [ ] Performance benchmarks normal
- [ ] Backup restore test passed
