@app.get("/gpu/status")
async def gpu_status():
    """Get GPU metrics directly from GPU nodes"""
    import re
    gpus = []

    # GPU endpoints configuration
    GPU_ENDPOINTS = [
        {"node": "hydra-ai", "url": "http://192.168.1.250:9835/metrics", "format": "dcgm"},
        {"node": "hydra-compute", "url": "http://192.168.1.203:9835/metrics", "format": "custom"}
    ]

    for endpoint in GPU_ENDPOINTS:
        try:
            r = await client.get(endpoint["url"], timeout=5.0)
            if r.status_code == 200:
                text = r.text
                if endpoint["format"] == "dcgm":
                    # Parse DCGM metrics - find all GPUs
                    for line in text.split("\n"):
                        if line.startswith("DCGM_FI_DEV_GPU_TEMP{"):
                            match = re.search(r'modelName="([^"]+)".*} (\d+)', line)
                            if match:
                                name = match.group(1).replace("NVIDIA GeForce ", "")
                                temp = float(match.group(2))
                                gpu_idx_match = re.search(r'gpu="(\d+)"', line)
                                if gpu_idx_match:
                                    gpu_idx = gpu_idx_match.group(1)
                                    util_match = re.search(rf'DCGM_FI_DEV_GPU_UTIL{{gpu="{gpu_idx}"[^}}]*}} (\d+)', text)
                                    power_match = re.search(rf'DCGM_FI_DEV_POWER_USAGE{{gpu="{gpu_idx}"[^}}]*}} ([\d.]+)', text)

                                    gpus.append({
                                        "node": endpoint["node"],
                                        "index": gpu_idx,
                                        "name": name,
                                        "temp_c": temp,
                                        "utilization": float(util_match.group(1)) if util_match else 0,
                                        "power_w": float(power_match.group(1)) if power_match else 0,
                                    })
                elif endpoint["format"] == "custom":
                    # Parse custom nvidia metrics
                    for line in text.split("\n"):
                        if line.startswith("nvidia_gpu_temperature_celsius{"):
                            match = re.search(r'name="([^"]+)"} (\d+)', line)
                            if match:
                                name = match.group(1).replace("NVIDIA_GeForce_", "").replace("_", " ")
                                temp = float(match.group(2))
                                gpu_idx_match = re.search(r'gpu="(\d+)"', line)
                                if gpu_idx_match:
                                    gpu_idx = gpu_idx_match.group(1)
                                    util_match = re.search(rf'nvidia_gpu_utilization_percent{{gpu="{gpu_idx}"[^}}]*}} (\d+)', text)
                                    power_match = re.search(rf'nvidia_gpu_power_draw_watts{{gpu="{gpu_idx}"[^}}]*}} ([\d.]+)', text)
                                    mem_used_match = re.search(rf'nvidia_gpu_memory_used_bytes{{gpu="{gpu_idx}"[^}}]*}} (\d+)', text)
                                    mem_total_match = re.search(rf'nvidia_gpu_memory_total_bytes{{gpu="{gpu_idx}"[^}}]*}} (\d+)', text)

                                    gpus.append({
                                        "node": endpoint["node"],
                                        "index": gpu_idx,
                                        "name": name,
                                        "temp_c": temp,
                                        "utilization": float(util_match.group(1)) if util_match else 0,
                                        "power_w": float(power_match.group(1)) if power_match else 0,
                                        "memory_used_gb": round(float(mem_used_match.group(1)) / (1024**3), 2) if mem_used_match else 0,
                                        "memory_total_gb": round(float(mem_total_match.group(1)) / (1024**3), 2) if mem_total_match else 0,
                                    })
        except Exception as e:
            pass

    return {"gpus": gpus}
