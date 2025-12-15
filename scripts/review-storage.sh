#!/bin/bash
# Storage Cleanup Review Script
# Run on hydra-storage to identify cleanup opportunities

echo "=============================================="
echo "  Hydra Storage Cleanup Review"
echo "=============================================="
echo ""

# Check temp_migration folder (Nov 28 backups)
echo "=== temp_migration (old backups) ==="
if [ -d "/mnt/user/temp_migration" ]; then
    du -sh /mnt/user/temp_migration
    echo "Contents:"
    ls -lah /mnt/user/temp_migration/ | head -20
    echo ""
    echo "Action: Review and delete if no longer needed (potentially 2.9TB)"
else
    echo "Directory not found"
fi
echo ""

# Check Docker dangling images
echo "=== Docker Cleanup Opportunities ==="
echo "Dangling images:"
docker images -f "dangling=true" -q | wc -l
echo "Build cache:"
docker system df | grep "Build Cache"
echo ""
echo "To clean: docker system prune -af --volumes"
echo ""

# Check log files
echo "=== Large Log Files ==="
find /mnt/user/appdata -name "*.log" -size +100M 2>/dev/null | head -10
echo ""

# Check model duplicates
echo "=== Model Storage ==="
du -sh /mnt/user/models/exl2 2>/dev/null || echo "N/A"
du -sh /mnt/user/models/gguf 2>/dev/null || echo "N/A"
du -sh /mnt/user/models/diffusion 2>/dev/null || echo "N/A"
echo ""

# Check database sizes
echo "=== Database Sizes ==="
docker exec hydra-postgres psql -U hydra -c "SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) AS size FROM pg_database ORDER BY pg_database_size(pg_database.datname) DESC;" 2>/dev/null || echo "PostgreSQL not accessible"
echo ""

# Overall disk usage
echo "=== Disk Usage Summary ==="
df -h /mnt/user
echo ""

# Unraid cache
echo "=== Cache Drive ==="
df -h /mnt/cache 2>/dev/null || echo "Cache not available"
echo ""

echo "=============================================="
echo "Review complete. Actions to consider:"
echo "  1. Delete /mnt/user/temp_migration if backups confirmed"
echo "  2. Run docker system prune"
echo "  3. Rotate/compress large log files"
echo "  4. Archive unused models"
echo "=============================================="
