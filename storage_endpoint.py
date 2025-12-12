
# =============================================================================
# Storage Pool Status
# =============================================================================

@app.get("/storage/pools")
async def storage_pools():
    """Get Unraid storage pool status"""
    import os
    import re

    try:
        pools = {
            "timestamp": datetime.now().isoformat(),
            "pools": [],
            "summary": {
                "total_bytes": 0,
                "used_bytes": 0,
                "free_bytes": 0
            }
        }

        # Read disk info from df
        result = os.popen("df -B1 2>/dev/null").read()

        array_disks = []
        nvme_pool = None

        for line in result.strip().split("\n"):
            if not line or "/mnt/" not in line:
                continue
            parts = line.split()
            if len(parts) >= 6:
                filesystem = parts[0]
                # Skip tmpfs mounts
                if filesystem == "tmpfs":
                    continue
                total = int(parts[1])
                used = int(parts[2])
                avail = int(parts[3])
                percent_str = parts[4].replace("%", "")
                percent = int(percent_str) if percent_str.isdigit() else 0
                mount = parts[5]

                disk_info = {
                    "mount": mount,
                    "filesystem": filesystem,
                    "total_bytes": total,
                    "used_bytes": used,
                    "free_bytes": avail,
                    "percent_used": percent
                }

                # Categorize disks - only match /mnt/disk followed by a number
                if re.match(r"/mnt/disk\d+$", mount):
                    array_disks.append(disk_info)
                elif mount == "/mnt/hpc_nvme":
                    nvme_pool = {
                        "name": "HPC NVMe",
                        "type": "nvme_pool",
                        "total_bytes": total,
                        "used_bytes": used,
                        "free_bytes": avail,
                        "percent_used": percent,
                        "status": "healthy" if percent < 90 else "warning"
                    }

        # Calculate array totals from individual disks
        if array_disks:
            array_total = sum(d["total_bytes"] for d in array_disks)
            array_used = sum(d["used_bytes"] for d in array_disks)
            array_free = sum(d["free_bytes"] for d in array_disks)
            array_percent = round((array_used / array_total) * 100) if array_total > 0 else 0

            pools["pools"].append({
                "name": "Array",
                "type": "unraid_array",
                "total_bytes": array_total,
                "used_bytes": array_used,
                "free_bytes": array_free,
                "percent_used": array_percent,
                "disk_count": len(array_disks),
                "status": "healthy" if array_percent < 95 else "warning"
            })
            pools["summary"]["total_bytes"] += array_total
            pools["summary"]["used_bytes"] += array_used
            pools["summary"]["free_bytes"] += array_free
            pools["array_disks"] = sorted(array_disks, key=lambda x: x["mount"])

        # Add NVMe pool
        if nvme_pool:
            pools["pools"].append(nvme_pool)
            pools["summary"]["total_bytes"] += nvme_pool["total_bytes"]
            pools["summary"]["used_bytes"] += nvme_pool["used_bytes"]
            pools["summary"]["free_bytes"] += nvme_pool["free_bytes"]

        # Calculate summary percent
        if pools["summary"]["total_bytes"] > 0:
            pools["summary"]["percent_used"] = round(
                (pools["summary"]["used_bytes"] / pools["summary"]["total_bytes"]) * 100, 1
            )

        return pools
    except Exception as e:
        return {"status": "error", "error": str(e)}
