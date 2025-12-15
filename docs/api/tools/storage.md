# Storage Tools

Tools for file operations on NFS-mounted shared storage.

## read_file

Read content from a file on shared storage.

```python
from hydra_tools.storage import read_file

# Read entire file
content = read_file("/mnt/shared/docs/readme.md")

# Read with offset
content = read_file(
    path="/mnt/shared/data/large_file.txt",
    offset=1000,
    limit=500
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | str | required | File path (absolute) |
| `offset` | int | 0 | Line offset to start from |
| `limit` | int | 1000 | Maximum lines to read |

### Allowed Paths

| Path | Description |
|------|-------------|
| `/mnt/shared/` | Shared scratch space |
| `/mnt/models/` | AI model storage |
| `/mnt/user/` | Unraid user shares |

## write_file

Write content to a file.

```python
from hydra_tools.storage import write_file

# Write new file
result = write_file(
    path="/mnt/shared/output/result.json",
    content='{"status": "success"}'
)

# Append to file
result = write_file(
    path="/mnt/shared/logs/app.log",
    content="New log entry\n",
    append=True
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | str | required | File path (absolute) |
| `content` | str | required | Content to write |
| `append` | bool | False | Append instead of overwrite |

## list_files

List files in a directory.

```python
from hydra_tools.storage import list_files

# List directory
files = list_files("/mnt/shared/docs")

# With pattern matching
files = list_files(
    path="/mnt/models/exl2",
    pattern="*.safetensors"
)

# Recursive listing
files = list_files(
    path="/mnt/shared",
    recursive=True,
    limit=100
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | str | required | Directory path |
| `pattern` | str | `"*"` | Glob pattern |
| `recursive` | bool | False | Include subdirectories |
| `limit` | int | 100 | Maximum files to return |

### Response Format

```json
{
  "files": [
    {
      "name": "model.safetensors",
      "path": "/mnt/models/exl2/model.safetensors",
      "size": 14000000000,
      "modified": "2025-12-10T10:30:00Z",
      "is_dir": false
    }
  ],
  "total": 1
}
```

## file_exists

Check if a file or directory exists.

```python
from hydra_tools.storage import file_exists

exists = file_exists("/mnt/models/exl2/Llama-3.1-70B")
if exists:
    print("Model directory found")
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | str | required | Path to check |

## file_info

Get detailed information about a file.

```python
from hydra_tools.storage import file_info

info = file_info("/mnt/models/exl2/config.json")
print(f"Size: {info['size']} bytes")
print(f"Modified: {info['modified']}")
```

### Response Format

```json
{
  "path": "/mnt/models/exl2/config.json",
  "name": "config.json",
  "size": 1234,
  "modified": "2025-12-10T10:30:00Z",
  "created": "2025-12-01T08:00:00Z",
  "is_dir": false,
  "permissions": "644"
}
```

## delete_file

Delete a file or empty directory.

```python
from hydra_tools.storage import delete_file

# Delete file
result = delete_file("/mnt/shared/temp/old_file.txt")

# Delete empty directory
result = delete_file("/mnt/shared/temp/empty_dir")
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | str | required | Path to delete |

### Safety

- Cannot delete non-empty directories
- Cannot delete outside allowed paths
- Cannot delete system files

## copy_file

Copy a file within storage.

```python
from hydra_tools.storage import copy_file

result = copy_file(
    source="/mnt/shared/data/file.txt",
    destination="/mnt/shared/backup/file.txt"
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source` | str | required | Source file path |
| `destination` | str | required | Destination path |
| `overwrite` | bool | False | Overwrite if exists |

## Error Handling

```python
from hydra_tools import ToolError
from hydra_tools.storage import read_file

try:
    content = read_file("/mnt/shared/missing.txt")
except ToolError as e:
    if "not found" in str(e).lower():
        print("File does not exist")
    elif "permission" in str(e).lower():
        print("Access denied")
```

## Path Restrictions

For security, only these paths are accessible:

- `/mnt/shared/` - General scratch space
- `/mnt/models/` - Model storage (read-only recommended)
- `/mnt/user/hydra_shared/` - Unraid shared folder

Attempts to access other paths will raise `ToolError`.

## Best Practices

1. **Use absolute paths** - Relative paths are not supported
2. **Check existence first** - Use `file_exists` before operations
3. **Handle large files carefully** - Use offset/limit for big files
4. **Clean up temp files** - Delete files when done
5. **Avoid model directories** - Don't modify model files
