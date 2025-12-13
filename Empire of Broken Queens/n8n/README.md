# Empire of Broken Queens - n8n Workflows

## Setup Instructions

### 1. Create PostgreSQL Credential

Before importing workflows, create a PostgreSQL credential in n8n:

1. Go to **Settings → Credentials → Add Credential**
2. Select **Postgres**
3. Configure:
   - **Name:** `Empire PostgreSQL`
   - **Host:** `192.168.1.244`
   - **Database:** `empire_of_broken_queens`
   - **User:** `hydra`
   - **Password:** `<your-password>`
   - **Port:** `5432`
   - **SSL:** `disable` (internal network)

### 2. Import Workflows

**Via n8n UI:**
1. Go to **Workflows**
2. Click **Import from File**
3. Select the JSON file
4. Save and activate

**Via CLI (if using n8n CLI):**
```bash
n8n import:workflow --input=overnight_generation_workflow.json
n8n import:workflow --input=parallel_generation_workflow.json
```

---

## Workflow Descriptions

### overnight_generation_workflow.json

**Purpose:** Automated overnight generation pipeline

**Schedule:** Runs at 10 PM daily, stops at 6 AM

**Flow:**
1. Gets pipeline config from database
2. Fetches all queens and their asset summaries
3. Calculates what needs to be generated (targets: 50 portraits, 16 expressions, etc.)
4. Creates generation tasks in database
5. Queues each task to ComfyUI
6. Waits for completion, updates status
7. Generates morning report
8. Saves metrics to database

**Triggers:**
- Schedule: 10 PM daily
- Manual: For testing

### parallel_generation_workflow.json

**Purpose:** API endpoint for parallel generation using dual 5070 Ti GPUs

**Endpoint:** `POST http://192.168.1.244:5678/webhook/empire-generate`

**Request Body:**
```json
{
  "queen_slug": "emilie-ekstrom",
  "queen_name": "Emilie Ekström",
  "task_type": "portrait",
  "count": 10,
  "priority": "high",
  "lora_path": "/mnt/models/loras/emilie-v1.safetensors",
  "lora_strength": 0.8,
  "base_prompt": "custom prompt here",
  "width": 1024,
  "height": 1024,
  "steps": 30,
  "cfg": 7.0
}
```

**Response:**
```json
{
  "task_id": "uuid",
  "total_queued": 10,
  "status": "queued",
  "message": "Queued 10 images across 2 GPUs"
}
```

**Flow:**
1. Receives webhook request
2. Splits batch into 2 (one per GPU)
3. Creates task records in database
4. Builds ComfyUI requests
5. Queues to ComfyUI (2 at a time for parallel processing)
6. Returns task ID and status

---

## Database Tables Used

These workflows interact with:

- `queens` - Queen definitions
- `generation_tasks` - Task queue and tracking
- `generated_assets` - Output tracking
- `quality_metrics` - Aggregated statistics
- `generation_config` - Pipeline configuration
- `queen_asset_summary` (view) - Asset counts per queen

---

## Configuration

Pipeline settings stored in `generation_config` table:

```sql
-- View current config
SELECT key, value FROM generation_config;

-- Update overnight settings
UPDATE generation_config
SET value = '{"enabled": true, "start_hour": 23, "end_hour": 5}'
WHERE key = 'overnight_pipeline';

-- Update quality thresholds
UPDATE generation_config
SET value = '{"aesthetic_min": 0.7, "auto_approve_threshold": 0.85}'
WHERE key = 'quality_thresholds';
```

---

## Monitoring

Check generation status:

```sql
-- Pending tasks
SELECT * FROM generation_queue;

-- Recent tasks
SELECT id, task_type, queen_slug, status, completed_count, total_count
FROM generation_tasks
ORDER BY created_at DESC
LIMIT 20;

-- Asset counts by queen
SELECT * FROM queen_asset_summary;
```

---

## Troubleshooting

**ComfyUI not responding:**
- Check `http://192.168.1.203:8188/` is accessible
- Verify ComfyUI container is running

**Database connection failed:**
- Verify PostgreSQL credential in n8n
- Check `empire_of_broken_queens` database exists
- Test: `psql -h 192.168.1.244 -U hydra -d empire_of_broken_queens`

**Tasks stuck in queued:**
- Check n8n execution logs
- Verify ComfyUI queue isn't full
- Check for error messages in `generation_tasks.last_error`
