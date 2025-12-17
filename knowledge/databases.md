# Database Stack Knowledge Base

## Overview

| Database | Port | Purpose | Location |
|----------|------|---------|----------|
| PostgreSQL 16 | 5432 | Relational data, state | hydra-storage |
| Qdrant | 6333/6334 | Vector embeddings | hydra-storage |
| Redis 7 | 6379 | Cache, sessions, queues | hydra-storage |
| MinIO | 9000/9001 | S3-compatible storage | hydra-storage |
| Meilisearch | 7700 | Full-text search | hydra-storage |
| Neo4j | 7474/7687 | Knowledge graphs | hydra-storage |

## PostgreSQL

### Docker Setup
```yaml
postgres:
  image: postgres:16
  container_name: postgres
  environment:
    POSTGRES_USER: hydra
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: hydra
  volumes:
    - /mnt/user/databases/postgres:/var/lib/postgresql/data
  ports:
    - 5432:5432
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U hydra"]
    interval: 10s
    timeout: 5s
    retries: 5
  restart: unless-stopped
```

### Databases to Create
```sql
-- Connect as hydra user
CREATE DATABASE n8n;
CREATE DATABASE litellm;
CREATE DATABASE grafana;
CREATE DATABASE homeassistant;
CREATE DATABASE immich;
```

### Connection String
```
postgresql://hydra:${POSTGRES_PASSWORD}@192.168.1.244:5432/hydra
```

### Backup
```bash
# Dump all databases
docker exec postgres pg_dumpall -U hydra > backup.sql

# Dump specific database
docker exec postgres pg_dump -U hydra n8n > n8n_backup.sql

# Restore
cat backup.sql | docker exec -i postgres psql -U hydra
```

## Qdrant (Vector Database)

### Docker Setup
```yaml
qdrant:
  image: qdrant/qdrant:latest
  container_name: qdrant
  ports:
    - 6333:6333  # HTTP
    - 6334:6334  # gRPC
  volumes:
    - /mnt/user/databases/qdrant:/qdrant/storage
  environment:
    - QDRANT__SERVICE__GRPC_PORT=6334
  restart: unless-stopped
```

### Collections
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(host="192.168.1.244", port=6333)

# Create collection for documents
client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)

# Create collection for conversations
client.create_collection(
    collection_name="conversations",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)

# Create collection for knowledge base
client.create_collection(
    collection_name="knowledge",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)
```

### Usage
```python
# Insert vectors
client.upsert(
    collection_name="documents",
    points=[
        {
            "id": 1,
            "vector": embedding,  # 768-dim vector from nomic-embed-text
            "payload": {
                "text": "Original text",
                "source": "document.pdf",
                "page": 1
            }
        }
    ]
)

# Search
results = client.search(
    collection_name="documents",
    query_vector=query_embedding,
    limit=10
)
```

### REST API
```bash
# List collections
curl http://192.168.1.244:6333/collections

# Collection info
curl http://192.168.1.244:6333/collections/documents

# Search
curl -X POST http://192.168.1.244:6333/collections/documents/points/search \
  -H "Content-Type: application/json" \
  -d '{"vector": [...], "limit": 10}'
```

## Redis

### Docker Setup
```yaml
redis:
  image: redis:7-alpine
  container_name: redis
  ports:
    - 6379:6379
  volumes:
    - /mnt/user/databases/redis:/data
  command: redis-server --appendonly yes
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
  restart: unless-stopped
```

### Use Cases
- **Session cache:** Store user sessions
- **Job queues:** n8n, agent tasks
- **Rate limiting:** API rate limits
- **Pub/Sub:** Real-time events

### Connection
```python
import redis

r = redis.Redis(host='192.168.1.244', port=6379, db=0)

# Basic operations
r.set('key', 'value')
r.get('key')

# Lists (queues)
r.lpush('queue', 'task1')
r.rpop('queue')

# Pub/Sub
pubsub = r.pubsub()
pubsub.subscribe('channel')
```

## MinIO (S3-Compatible)

### Docker Setup
```yaml
minio:
  image: minio/minio:latest
  container_name: minio
  ports:
    - 9000:9000  # API
    - 9001:9001  # Console
  environment:
    MINIO_ROOT_USER: ${MINIO_USER}
    MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
  volumes:
    - /mnt/user/databases/minio:/data
  command: server /data --console-address ":9001"
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
    interval: 30s
    timeout: 20s
    retries: 3
  restart: unless-stopped
```

### Buckets
- `documents` - Uploaded files
- `outputs` - Generated content
- `backups` - Database backups
- `models` - Model artifacts

### Usage with boto3
```python
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='http://192.168.1.244:9000',
    aws_access_key_id=MINIO_USER,
    aws_secret_access_key=MINIO_PASSWORD
)

# Upload
s3.upload_file('local.txt', 'documents', 'remote.txt')

# Download
s3.download_file('documents', 'remote.txt', 'local.txt')

# List
objects = s3.list_objects_v2(Bucket='documents')
```

## Meilisearch (Full-Text)

### Docker Setup
```yaml
meilisearch:
  image: getmeili/meilisearch:latest
  container_name: meilisearch
  ports:
    - 7700:7700
  environment:
    MEILI_MASTER_KEY: ${MEILISEARCH_KEY}
    MEILI_ENV: production
  volumes:
    - /mnt/user/databases/meilisearch:/meili_data
  restart: unless-stopped
```

### Usage
```python
import meilisearch

client = meilisearch.Client('http://192.168.1.244:7700', MEILISEARCH_KEY)

# Create index
index = client.index('documents')

# Add documents
index.add_documents([
    {"id": 1, "title": "Doc 1", "content": "..."},
    {"id": 2, "title": "Doc 2", "content": "..."}
])

# Search
results = index.search('query', {'limit': 10})
```

### Hybrid Search Pattern
```python
# Combine Meilisearch (BM25) with Qdrant (vector)
def hybrid_search(query, alpha=0.7):
    # Get embeddings
    embedding = get_embedding(query)
    
    # Vector search
    vector_results = qdrant.search("documents", embedding, limit=20)
    
    # BM25 search
    bm25_results = meilisearch.index("documents").search(query, limit=20)
    
    # Combine with alpha weighting
    # alpha * vector_score + (1-alpha) * bm25_score
    combined = merge_results(vector_results, bm25_results, alpha)
    
    return combined[:10]
```

## Neo4j (Knowledge Graphs)

**Status:** DEPLOYED (2025-12-10)
**Container:** hydra-neo4j
**Version:** 5.26.0-community
**Credentials:** neo4j / HydraNeo4jPass2024

### Docker Setup
```yaml
hydra-neo4j:
  image: neo4j:5.26.0-community
  container_name: hydra-neo4j
  ports:
    - 7474:7474  # HTTP/Browser
    - 7687:7687  # Bolt
  environment:
    NEO4J_AUTH: neo4j/HydraNeo4jPass2024
    NEO4J_PLUGINS: ["apoc"]
  volumes:
    - /mnt/user/appdata/neo4j/data:/data
  restart: unless-stopped
```

### Connection
```bash
# Browser: http://192.168.1.244:7474
# Bolt: bolt://192.168.1.244:7687

# Python
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://192.168.1.244:7687", auth=("neo4j", "HydraNeo4jPass2024"))
```

### Use Cases
- Entity relationships (cluster topology)
- Knowledge graphs (documentation relationships)
- Dependency mapping (services, containers)

## Environment Variables

```bash
# .env file
POSTGRES_PASSWORD=your_secure_password
MINIO_USER=hydra
MINIO_PASSWORD=your_secure_password
MEILISEARCH_KEY=your_master_key
NEO4J_PASSWORD=your_password
REDIS_URL=redis://192.168.1.244:6379
```

## Backup Strategy

### Automated Backups (n8n workflow)
```
Trigger: Daily at 2 AM
→ pg_dump all PostgreSQL DBs
→ Qdrant snapshot
→ Redis BGSAVE
→ Upload to MinIO backups bucket
→ Retain 7 days, delete older
```

### Manual Backup Commands
```bash
# PostgreSQL
docker exec postgres pg_dumpall -U hydra | gzip > postgres_$(date +%Y%m%d).sql.gz

# Qdrant
curl -X POST http://192.168.1.244:6333/snapshots

# Redis
docker exec redis redis-cli BGSAVE

# MinIO (sync to backup location)
mc mirror minio/documents /mnt/backup/minio/
```

## Health Checks

```bash
# PostgreSQL
docker exec postgres pg_isready -U hydra

# Qdrant
curl http://192.168.1.244:6333/health

# Redis
docker exec redis redis-cli ping

# MinIO
curl http://192.168.1.244:9000/minio/health/live

# Meilisearch
curl http://192.168.1.244:7700/health

# Neo4j
curl http://192.168.1.244:7474
```
