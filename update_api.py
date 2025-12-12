#!/usr/bin/env python3
import re
import sys

# Add StoragePoolsData type to api.ts
api_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/api.ts"
with open(api_file, "r") as f:
    content = f.read()

# Check if already added
if "StoragePoolsData" not in content:
    # Add interface after GpuInfo
    type_def = '''
export interface StoragePool {
  name: string;
  type: string;
  total_bytes: number;
  used_bytes: number;
  free_bytes: number;
  percent_used: number;
  disk_count?: number;
  status: string;
}

export interface StoragePoolsData {
  timestamp: string;
  pools: StoragePool[];
  summary: {
    total_bytes: number;
    used_bytes: number;
    free_bytes: number;
    percent_used: number;
  };
}
'''
    # Insert after GpuInfo interface
    insert_point = content.find("export interface LettaAgent")
    if insert_point > 0:
        content = content[:insert_point] + type_def + "\n" + content[insert_point:]

# Add API method if not present
if "storagePools:" not in content:
    # Add before restartContainer
    content = content.replace(
        "restartContainer: (container: string",
        "storagePools: () => fetchJSON<StoragePoolsData>('/storage/pools'),\n  restartContainer: (container: string"
    )

# Add to exports if needed
if "StoragePoolsData" not in content.split("export default api")[0].split("export { api }")[0]:
    content = content.replace(
        "export default api;",
        "export type { StoragePoolsData, StoragePool };\nexport default api;"
    )

with open(api_file, "w") as f:
    f.write(content)

print("Updated api.ts successfully")
