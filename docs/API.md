# Hydra Tools API

**Version:** 2.9.0


Self-improvement and optimization toolkit for the Hydra cluster.

## Core Features

* **Self-Diagnosis** - Failure analysis, pattern detection, auto-remediation
* **Resource Optimization** - GPU/CPU/RAM analysis, model placement suggestions
* **Knowledge Optimization** - Stale detection, redundancy consolidation
* **Capability Tracking** - Feature gaps, priority scoring, roadmap generation
* **Intelligent Routing** - Route prompts to optimal models
* **Preference Learning** - Track user preferences and model performance

## Transparency Framework

* **Activity Logging** - Unified activity log for all autonomous actions
* **System Control** - Control modes, emergency stop, workflow toggles
* **Constitution** - Safety constraints and audit trail

## Search & Knowledge

* **Hybrid Search** - Combined semantic + keyword search (Qdrant + Meilisearch)
* **Document Ingestion** - Index documents and URLs to knowledge base
* **Web Research** - Search web and crawl pages (SearXNG + Firecrawl)
* **Memory Architecture** - MIRIX 6-tier memory system

## Orchestration & Agents

* **CrewAI Orchestration** - Multi-agent crews for research, monitoring, maintenance
* **Agent Scheduler** - AIOS-style agent task scheduling
* **Autonomous Controller** - Proactive task spawning and execution

## Infrastructure

* **Cluster Health** - Unified health monitoring across all nodes
* **Predictive Maintenance** - Trend analysis and failure prediction
* **Container Health** - External healthchecks for containers
* **State Reconciliation** - Drift detection and auto-remediation
* **Unraid Integration** - Storage management and monitoring

## Creative Pipeline (Phase 12)

* **Character Consistency** - Face embedding and style reference management
* **Asset Quality Scoring** - Automated quality assessment for generated images
* **Batch Portrait Generation** - Queue multiple character portraits
* **Voice Pipeline** - STT, LLM, TTS voice interaction

## Notifications & Dashboards

* **Alert Routing** - Notification routing to Discord, Slack
* **Discovery Archive** - Cross-session learning and improvement tracking
* **Dashboard API** - Real-time SSE streaming for Command Center


## Table of Contents

- [activity](#activity)
- [agent-scheduler](#agent-scheduler)
- [agentic-rag](#agentic-rag)
- [aggregate](#aggregate)
- [alerts](#alerts)
- [asset-quality](#asset-quality)
- [auth](#auth)
- [autonomous](#autonomous)
- [benchmark](#benchmark)
- [calendar](#calendar)
- [capabilities](#capabilities)
- [characters](#characters)
- [cluster-health](#cluster-health)
- [comfyui](#comfyui)
- [constitution](#constitution)
- [container-health](#container-health)
- [control](#control)
- [conversation-cache](#conversation-cache)
- [crews](#crews)
- [dashboard](#dashboard)
- [diagnosis](#diagnosis)
- [discord](#discord)
- [discoveries](#discoveries)
- [events](#events)
- [face-detection](#face-detection)
- [graphiti-memory](#graphiti-memory)
- [hardware](#hardware)
- [home-automation](#home-automation)
- [info](#info)
- [ingest](#ingest)
- [knowledge](#knowledge)
- [letta-bridge](#letta-bridge)
- [logs](#logs)
- [memory](#memory)
- [optimization](#optimization)
- [predictive-maintenance](#predictive-maintenance)
- [preference-collector](#preference-collector)
- [preferences](#preferences)
- [presence](#presence)
- [reconcile](#reconcile)
- [reranker](#reranker)
- [research](#research)
- [research-queue](#research-queue)
- [routing](#routing)
- [sandbox](#sandbox)
- [scheduler](#scheduler)
- [search](#search)
- [self-improvement](#self-improvement)
- [semantic-cache](#semantic-cache)
- [services](#services)
- [story-crew](#story-crew)
- [unraid](#unraid)
- [vision](#vision)
- [voice](#voice)
- [wake-word](#wake-word)

## activity

### POST `/activity`

**Log Activity**

Log a new activity.

**Request Body:**

Content-Type: `application/json`
Schema: `LogActivityRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/activity`

**Query Activities**

Query activities with filters.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `source` | query | any | No |  |
| `action_type` | query | any | No |  |
| `result` | query | any | No |  |
| `since` | query | any | No |  |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/activity/pending`

**Get Pending**

Get all pending approval activities.

**Responses:**

- `200`: Successful Response

---

### GET `/activity/{activity_id}`

**Get Activity**

Get a single activity by ID.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `activity_id` | path | integer | Yes |  |
| `include_chain` | query | boolean | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### PUT `/activity/{activity_id}/result`

**Update Activity Result**

Update the result of an activity.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `activity_id` | path | integer | Yes |  |

**Request Body:**

Content-Type: `application/json`
Schema: `UpdateResultRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/activity/{activity_id}/approve`

**Approve Activity**

Approve a pending activity.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `activity_id` | path | integer | Yes |  |

**Request Body:**

Content-Type: `application/json`
Schema: `ApprovalRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/activity/{activity_id}/reject`

**Reject Activity**

Reject a pending activity.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `activity_id` | path | integer | Yes |  |

**Request Body:**

Content-Type: `application/json`
Schema: `ApprovalRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## agent-scheduler

### GET `/agent-scheduler/status`

**Get Status**

Get scheduler status and statistics.

**Responses:**

- `200`: Successful Response

---

### POST `/agent-scheduler/schedule`

**Schedule Task**

Schedule a new agent task.

**Request Body:**

Content-Type: `application/json`
Schema: `ScheduleRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/agent-scheduler/task/{task_id}`

**Get Task**

Get status of a specific task.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `task_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### DELETE `/agent-scheduler/task/{task_id}`

**Cancel Task**

Cancel a queued task.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `task_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/agent-scheduler/queue`

**Get Queue**

Get all queued tasks.

**Responses:**

- `200`: Successful Response

---

### POST `/agent-scheduler/task/{task_id}/checkpoint`

**Checkpoint Task**

Checkpoint a running task.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `task_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/agent-scheduler/start`

**Start Scheduler**

Start the scheduler.

**Responses:**

- `200`: Successful Response

---

### POST `/agent-scheduler/stop`

**Stop Scheduler**

Stop the scheduler gracefully.

**Responses:**

- `200`: Successful Response

---

## agentic-rag

### POST `/agentic-rag/query`

**Agentic Query**

Execute an agentic RAG query with self-reflection.

The system will:
1. Retrieve documents from multiple sources
2. Grade documents for relevance
3. Rewrite query if needed and re-retrieve
4. Generate answer with citations
5. Verify answer is grounded (hallucination check)

**Request Body:**

Content-Type: `application/json`
Schema: `QueryRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/agentic-rag/health`

**Agentic Rag Health**

Check Agentic RAG health.

**Responses:**

- `200`: Successful Response

---

### POST `/agentic-rag/grade-documents`

**Grade Documents**

Grade a list of documents for relevance to a query.

Useful for testing the grading component independently.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `query` | query | string | Yes |  |

**Request Body:**

Content-Type: `application/json`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/agentic-rag/rewrite-query`

**Rewrite Query**

Rewrite a query using specified strategy.

Strategies:
- refine: Make more specific
- broaden: Make more general
- transform: Use different terms

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `query` | query | string | Yes |  |
| `strategy` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## aggregate

### GET `/aggregate/health`

**Aggregate Health**

Aggregate health status from all subsystems.

Provides a single endpoint for overall system health.

**Responses:**

- `200`: Successful Response

---

## alerts

### GET `/alerts/recent`

**Get Recent Alerts**

Get recent alerts from the log.

Returns alerts from today's log file, optionally filtered by severity or node.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |
| `severity` | query | any | No |  |
| `node` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/alerts/send`

**Send Alert**

Send a custom alert to notification channels.

Routes to Discord, Slack, or both based on channel parameter.

**Request Body:**

Content-Type: `application/json`
Schema: `SendAlertRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/alerts/test`

**Send Test Alert**

Send a test alert to verify notification channels.

Sends an INFO-level test alert to Discord.

**Responses:**

- `200`: Successful Response

---

### GET `/alerts/status`

**Get Alert Status**

Get the status of the alerting system.

Checks connectivity to notification services and log availability.

**Responses:**

- `200`: Successful Response

---

### GET `/alerts/channels`

**List Channels**

List available notification channels.

Returns configured channels and their status.

**Responses:**

- `200`: Successful Response

---

### GET `/alerts/silences`

**List Silences**

List Alertmanager silences.

Returns all silences or only active ones based on the active_only parameter.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `active_only` | query | boolean | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/alerts/silence`

**Create Silence**

Create an Alertmanager silence.

Silences matching alerts for the specified duration.
Matchers define which alerts to silence based on label matching.

**Request Body:**

Content-Type: `application/json`
Schema: `CreateSilenceRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### DELETE `/alerts/silence/{silence_id}`

**Delete Silence**

Delete (expire) an Alertmanager silence.

This immediately expires the silence, allowing matching alerts to fire again.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `silence_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/alerts/silence/alert/{alertname}`

**Silence By Alertname**

Silence a specific alert by name.

Convenience endpoint to silence all instances of a specific alert.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `alertname` | path | string | Yes |  |
| `duration_minutes` | query | integer | No |  |
| `comment` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/alerts/silence/node/{node}`

**Silence By Node**

Silence all alerts for a specific node.

Useful during planned maintenance on a specific node.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `node` | path | string | Yes |  |
| `duration_minutes` | query | integer | No |  |
| `comment` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/alerts/silence/service/{service}`

**Silence By Service**

Silence all alerts for a specific service.

Useful during service deployments or known maintenance.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `service` | path | string | Yes |  |
| `duration_minutes` | query | integer | No |  |
| `comment` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/alerts/silence/maintenance`

**Silence For Maintenance**

Create silences for planned maintenance.

Silences alerts for specified nodes and/or services.
If neither is specified, silences all non-critical alerts.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `duration_minutes` | query | integer | No |  |
| `comment` | query | any | No |  |

**Request Body:**

Content-Type: `application/json`
Schema: `Body_silence_for_maintenance_alerts_silence_maintenance_post`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/alerts/silence/check/{alertname}`

**Check If Silenced**

Check if a specific alert is currently silenced.

Returns silence information if the alert is silenced, or indicates it's active.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `alertname` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## asset-quality

### POST `/quality/evaluate`

**Evaluate Asset**

Evaluate quality of a generated asset.

**Request Body:**

Content-Type: `application/json`
Schema: `EvaluateRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/quality/report/{asset_id}`

**Get Report**

Get quality report for a specific asset.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `asset_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/quality/pending-reviews`

**Get Pending Reviews**

Get all assets pending human review.

**Responses:**

- `200`: Successful Response

---

### GET `/quality/statistics`

**Get Statistics**

Get quality statistics across all evaluated assets.

**Responses:**

- `200`: Successful Response

---

### GET `/quality/thresholds`

**Get Thresholds**

Get current quality thresholds.

**Responses:**

- `200`: Successful Response

---

### PUT `/quality/thresholds`

**Update Thresholds**

Update quality thresholds.

**Request Body:**

Content-Type: `application/json`
Schema: `ThresholdsUpdate`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/quality/tier/{tier}`

**Get Reports By Tier**

Get all reports of a specific quality tier.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `tier` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## auth

### GET `/auth/status`

**Auth Status**

Check authentication status.

Returns whether auth is enabled and if the provided key is valid.
This endpoint works both with and without authentication.

**Responses:**

- `200`: Successful Response

---

### POST `/auth/generate-key`

**Generate Api Key**

Generate a new random API key.

Note: This just generates a key - you must add it to your environment
variables (HYDRA_API_KEY or HYDRA_API_KEYS) to use it.

**Responses:**

- `200`: Successful Response

---

## autonomous

### GET `/autonomous/status`

**Get Status**

Get autonomous controller status.

**Responses:**

- `200`: Successful Response

---

### POST `/autonomous/start`

**Start Controller**

Start the autonomous controller.

**Responses:**

- `200`: Successful Response

---

### POST `/autonomous/stop`

**Stop Controller**

Stop the autonomous controller.

**Responses:**

- `200`: Successful Response

---

### GET `/autonomous/rules`

**Get Rules**

Get all trigger rules.

**Responses:**

- `200`: Successful Response

---

### POST `/autonomous/rules/{rule_id}/enable`

**Enable Rule**

Enable a trigger rule.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `rule_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/autonomous/rules/{rule_id}/disable`

**Disable Rule**

Disable a trigger rule.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `rule_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/autonomous/history`

**Get History**

Get autonomous action history.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/autonomous/spawn`

**Spawn Task**

Manually spawn an autonomous task.

This bypasses trigger rules but still respects constitutional constraints.

**Request Body:**

Content-Type: `application/json`
Schema: `SpawnTaskRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/autonomous/state`

**Get Current State**

Get current system state as perceived by the controller.

**Responses:**

- `200`: Successful Response

---

### POST `/autonomous/perceive`

**Force Perceive**

Force a perception cycle.

**Responses:**

- `200`: Successful Response

---

### POST `/autonomous/evaluate`

**Evaluate Rules**

Evaluate all rules against current state without acting.

**Responses:**

- `200`: Successful Response

---

### POST `/autonomous/queue`

**Add To Queue**

Add a work item to the autonomous queue.

**Request Body:**

Content-Type: `application/json`
Schema: `WorkItemCreate`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/autonomous/queue`

**List Queue**

List items in the work queue.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `status` | query | any | No |  |
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/autonomous/queue/stats`

**Get Queue Stats**

Get queue statistics.

**Responses:**

- `200`: Successful Response

---

### POST `/autonomous/process`

**Process Queue**

Process pending items in the queue (runs in background).

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/autonomous/process/{item_id}`

**Process Single Item**

Process a single work item immediately.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `item_id` | path | integer | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### DELETE `/autonomous/queue/{item_id}`

**Cancel Work Item**

Cancel a pending work item.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `item_id` | path | integer | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/autonomous/queue/chapter`

**Queue Chapter Generation**

Queue a chapter for generation.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `chapter_number` | query | integer | Yes |  |
| `priority` | query | any | No |  |
| `scheduled_after` | query | any | No |  |

**Request Body:**

Content-Type: `application/json`
Schema: `Body_queue_chapter_generation_autonomous_queue_chapter_post`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/autonomous/queue/research`

**Queue Research**

Queue a research task.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `topic` | query | string | Yes |  |
| `depth` | query | string | No |  |
| `priority` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/autonomous/queue/maintenance`

**Queue Maintenance**

Queue a maintenance task.

Available actions:
- health_check: Run comprehensive health checks (default)
- docker_cleanup: Prune unused Docker resources
- disk_check: Check disk usage across cluster
- backup_verify: Verify recent backups exist
- database_optimize: Optimize PostgreSQL/Qdrant
- benchmark: Run self-improvement benchmarks

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `action` | query | string | No |  |
| `priority` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/autonomous/queue/inference`

**Queue Inference**

Queue an inference task.

Routes to TabbyAPI via LiteLLM for batch LLM processing.

Args:
    prompt: The user prompt to process
    system: System prompt for context
    model: Model name (default: tabby for TabbyAPI)
    max_tokens: Maximum tokens to generate
    temperature: Sampling temperature

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `prompt` | query | string | Yes |  |
| `system` | query | string | No |  |
| `model` | query | string | No |  |
| `max_tokens` | query | integer | No |  |
| `temperature` | query | number | No |  |
| `priority` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/autonomous/queue/overnight`

**Queue Overnight Batch**

Queue a batch of overnight work items.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `generate_missing_assets` | query | boolean | No |  |

**Request Body:**

Content-Type: `application/json`
Schema: `Body_queue_overnight_batch_autonomous_queue_overnight_post`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/autonomous/resources`

**Get Cluster Resources**

Get current resource status across all cluster nodes.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `force_refresh` | query | boolean | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/autonomous/resources/summary`

**Get Resource Summary**

Get a quick summary of cluster resources.

**Responses:**

- `200`: Successful Response

---

### GET `/autonomous/scheduler/status`

**Get Scheduler Status**

Get current status of the 24/7 autonomous scheduler.

**Responses:**

- `200`: Successful Response

---

### POST `/autonomous/scheduler/start`

**Start Scheduler**

Start the 24/7 autonomous scheduler.

**Responses:**

- `200`: Successful Response

---

### POST `/autonomous/scheduler/stop`

**Stop Scheduler**

Stop the 24/7 autonomous scheduler.

**Responses:**

- `200`: Successful Response

---

### PUT `/autonomous/scheduler/thresholds`

**Update Thresholds**

Update resource thresholds for the scheduler.

**Request Body:**

Content-Type: `application/json`
Schema: `ThresholdUpdate`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## benchmark

### GET `/benchmark/status`

**Get Status**

Get benchmark system status.

**Responses:**

- `200`: Successful Response

---

### POST `/benchmark/run`

**Run Benchmarks**

Run full benchmark suite and persist results.

**Responses:**

- `200`: Successful Response

---

### GET `/benchmark/latest`

**Get Latest**

Get latest benchmark results from database.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/benchmark/history`

**Get History**

Get benchmark history.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/benchmark/single/{benchmark_name}`

**Run Single Benchmark**

Run a single benchmark.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `benchmark_name` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## calendar

### GET `/calendar/status`

**Get Status**

Get current calendar status.

**Responses:**

- `200`: Successful Response

---

### GET `/calendar/config`

**Get Config**

Get current schedule configuration.

**Responses:**

- `200`: Successful Response

---

### GET `/calendar/events`

**List Events**

List all scheduled events.

**Responses:**

- `200`: Successful Response

---

### POST `/calendar/events`

**Add Event**

Add a scheduled event.

**Request Body:**

Content-Type: `application/json`
Schema: `AddEventRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### DELETE `/calendar/events/{event_id}`

**Delete Event**

Delete a scheduled event.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `event_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/calendar/check/{task_type}`

**Check Task**

Check if a task type is allowed now.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `task_type` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/calendar/schedule`

**Get Schedule**

Get the default schedule configuration.

**Responses:**

- `200`: Successful Response

---

## capabilities

### POST `/capabilities/gap`

**Record Gap**

Record a capability gap.

**Request Body:**

Content-Type: `application/json`
Schema: `GapRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/capabilities/backlog`

**Get Backlog**

Get prioritized backlog.

**Responses:**

- `200`: Successful Response

---

### GET `/capabilities/metrics`

**Get Metrics**

Get capability metrics.

**Responses:**

- `200`: Successful Response

---

### PATCH `/capabilities/gap/{gap_id}`

**Update Gap**

Update a capability gap.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `gap_id` | path | string | Yes |  |

**Request Body:**

Content-Type: `application/json`
Schema: `UpdateRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/capabilities/export`

**Export Markdown**

Export backlog to markdown.

**Responses:**

- `200`: Successful Response

---

## characters

### GET `/characters/`

**List Characters**

List all characters.

**Responses:**

- `200`: Successful Response

---

### POST `/characters/`

**Create Character**

Create a new character.

**Request Body:**

Content-Type: `application/json`
Schema: `CharacterCreate`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### PATCH `/characters/{character_id}/voice`

**Update Character Voice**

Update a character's voice profile.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `character_id` | path | string | Yes |  |

**Request Body:**

Content-Type: `application/json`
Schema: `UpdateVoiceRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### PATCH `/characters/{character_id}/references`

**Update Character References**

Update a character's reference images.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `character_id` | path | string | Yes |  |

**Request Body:**

Content-Type: `application/json`
Schema: `UpdateReferencesRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/parse-script`

**Parse Script**

Parse a visual novel script into scenes with full dialogue data.

**Request Body:**

Content-Type: `application/json`
Schema: `ScriptParseRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/generate-portrait`

**Generate Portrait**

Generate a character portrait workflow.

**Request Body:**

Content-Type: `application/json`
Schema: `GeneratePortraitRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/batch-generate`

**Batch Generate Portraits**

Generate portraits for multiple characters in batch.

If character_ids is empty, generates for all characters.
Generates all combinations of emotions x poses for each character.

**Request Body:**

Content-Type: `application/json`
Schema: `BatchPortraitRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/batch-status/{batch_id}`

**Get Batch Status**

Get status of a batch generation job.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `batch_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/coverage`

**Get Portrait Coverage**

Get portrait coverage statistics for all characters.

Returns how many characters have reference images and which emotions are covered.

**Responses:**

- `200`: Successful Response

---

### POST `/characters/generate-missing`

**Generate Missing Portraits**

Generate portraits for all characters missing reference images.

Convenience endpoint that wraps batch-generate with skip_existing=True.

**Request Body:**

Content-Type: `application/json`
Schema: `Body_generate_missing_portraits_characters_generate_missing_post`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/by-id/{character_id}`

**Get Character**

Get a character by ID. Use /by-id/{uuid} to avoid route conflicts.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `character_id` | path | string | Yes | Character UUID |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/generate-chapter-assets`

**Generate Chapter Assets**

Generate all assets for a chapter: portraits, TTS, and backgrounds.

Takes parsed scene data and queues generation for:
- Character portraits (unique character+emotion combinations)
- TTS voice lines (all dialogues)
- Background images (unique scene backgrounds)

**Request Body:**

Content-Type: `application/json`
Schema: `ChapterAssetRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/generate-tts-batch`

**Generate Tts Batch**

Generate TTS for a batch of dialogue lines.

Each dialogue should have: character, text, emotion, voice_id, output_path

**Request Body:**

Content-Type: `application/json`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/quality-score`

**Score Image Quality**

Score image quality using aesthetic predictor and consistency comparison.

Returns:
- aesthetic_score: 0-10 score from aesthetic predictor
- consistency_score: 0-1 similarity to reference image (if provided)
- overall_score: Combined weighted score

**Request Body:**

Content-Type: `application/json`
Schema: `QualityScoreRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/batch-quality-score`

**Batch Score Quality**

Score multiple images against a reference.

**Request Body:**

Content-Type: `application/json`
Schema: `BatchQualityRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/generate-background`

**Generate Background**

Generate a single scene background image.

**Request Body:**

Content-Type: `application/json`
Schema: `hydra_tools__character_consistency__create_character_router__<locals>__BackgroundRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/generate-backgrounds-batch`

**Generate Backgrounds Batch**

Generate multiple scene backgrounds.

**Request Body:**

Content-Type: `application/json`
Schema: `BatchBackgroundRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/voices`

**List Available Voices**

List all available TTS voices with categories and descriptions.

**Responses:**

- `200`: Successful Response

---

### POST `/characters/assign-voice`

**Assign Voice To Character**

Assign a TTS voice to a character.

**Request Body:**

Content-Type: `application/json`
Schema: `VoiceAssignmentRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/voice-assignments`

**Get Voice Assignments**

Get current voice assignments for all characters.

**Responses:**

- `200`: Successful Response

---

### POST `/characters/preview-voice`

**Preview Voice**

Generate a voice preview for a given voice ID.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `voice_id` | query | string | Yes |  |
| `text` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/create-chapter-structure`

**Create Chapter Structure**

Create standardized directory structure for a chapter.

**Request Body:**

Content-Type: `application/json`
Schema: `ChapterStructureRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/chapter-assets/{chapter_number}`

**Get Chapter Assets**

Get inventory of all assets for a chapter.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `chapter_number` | path | integer | Yes |  |
| `output_base` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/transition-types`

**List Transition Types**

List all available transition types with descriptions.

**Responses:**

- `200`: Successful Response

---

### POST `/characters/scene-transition`

**Update Scene Transition**

Update transition metadata for a specific scene.

**Request Body:**

Content-Type: `application/json`
Schema: `SceneTransitionUpdate`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/scene-transitions/{chapter}`

**Get Chapter Transitions**

Get all scene transitions for a chapter.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `chapter` | path | integer | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/auto-generate-transitions`

**Auto Generate Transitions**

Auto-generate transition recommendations based on scene content.

**Request Body:**

Content-Type: `application/json`
Schema: `AutoTransitionRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/apply-transition-preset`

**Apply Transition Preset**

Apply a preset transition style to all scenes in a chapter.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `chapter` | query | integer | Yes |  |
| `preset` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/package-chapter`

**Package Chapter**

Package all chapter assets into a distributable archive.

**Request Body:**

Content-Type: `application/json`
Schema: `ChapterPackageRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/list-packages`

**List Packages**

List all packaged chapter archives.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `output_base` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### DELETE `/characters/delete-package/{package_name}`

**Delete Package**

Delete a packaged chapter archive.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `package_name` | path | string | Yes |  |
| `output_base` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/upscale-models`

**List Upscale Models**

List available upscaling models and their capabilities.

**Responses:**

- `200`: Successful Response

---

### POST `/characters/upscale`

**Upscale Image**

Upscale a single image using ComfyUI.

Uses Real-ESRGAN or similar models for high-quality upscaling.

**Request Body:**

Content-Type: `application/json`
Schema: `UpscaleRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/upscale-batch`

**Upscale Batch**

Upscale multiple images in batch.

Queues all images for upscaling and returns job IDs.

**Request Body:**

Content-Type: `application/json`
Schema: `BatchUpscaleRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/upscale-directory`

**Upscale Directory**

Upscale all images in a directory.

Finds all images with specified extensions and queues for upscaling.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `input_dir` | query | string | Yes |  |
| `output_dir` | query | any | No |  |
| `scale` | query | integer | No |  |
| `model` | query | string | No |  |
| `extensions` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/upscale-presets`

**Upscale Presets**

Get recommended upscaling presets for different use cases.

**Responses:**

- `200`: Successful Response

---

### GET `/characters/relationship-types`

**Get Relationship Types**

Get available relationship types.

**Responses:**

- `200`: Successful Response

---

### POST `/characters/relationship`

**Add Relationship**

Add or update a relationship between characters.

**Request Body:**

Content-Type: `application/json`
Schema: `RelationshipEdge`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### DELETE `/characters/relationship/{source}/{target}`

**Remove Relationship**

Remove a relationship between characters.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `source` | path | string | Yes |  |
| `target` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/relationships`

**Get All Relationships**

Get complete relationship graph.

**Responses:**

- `200`: Successful Response

---

### GET `/characters/relationships/{character_id}`

**Get Character Relationships**

Get all relationships for a specific character.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `character_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/relationship-graph/export`

**Export Relationship Graph**

Export relationship graph in various formats.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `format` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/relationship-graph/seed`

**Seed Relationship Graph**

Seed initial relationships for Empire of Broken Queens.

**Responses:**

- `200`: Successful Response

---

### GET `/characters/relationship-stats`

**Relationship Stats**

Get statistics about the relationship graph.

**Responses:**

- `200`: Successful Response

---

### GET `/characters/workflow-templates`

**List Workflow Templates**

List all available workflow templates.

**Responses:**

- `200`: Successful Response

---

### GET `/characters/workflow-templates/{template_name}`

**Get Workflow Template**

Get details about a specific workflow template.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `template_name` | path | string | Yes |  |
| `include_workflow` | query | boolean | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### DELETE `/characters/workflow-templates/{template_name}`

**Delete Workflow Template**

Delete a workflow template.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `template_name` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/workflow-templates/{template_name}/validate`

**Validate Template Variables**

Validate that all required variables are provided for a template.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `template_name` | path | string | Yes |  |

**Request Body:**

Content-Type: `application/json`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/workflow-templates/{template_name}/apply`

**Apply Workflow Template**

Apply a workflow template with variable substitution and optionally submit to ComfyUI.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `template_name` | path | string | Yes |  |
| `submit` | query | boolean | No |  |

**Request Body:**

Content-Type: `application/json`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/workflow-templates/save`

**Save Workflow Template**

Save a new workflow template.

**Request Body:**

Content-Type: `application/json`
Schema: `Body_save_workflow_template_characters_workflow_templates_save_post`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/characters/automate-chapter`

**Automate Chapter**

End-to-end chapter automation pipeline.

Orchestrates the complete chapter production workflow:
1. generate_script - Generate chapter script using LLM
2. create_structure - Create directory structure
3. generate_tts - Generate TTS audio for all dialogue
4. generate_assets - Generate visual assets (optional)
5. score_quality - Score generated assets (optional)
6. package - Package chapter for distribution

Usage:
```json
{
    "chapter_number": 1,
    "featured_characters": ["seraphina", "marcus"],
    "themes": ["betrayal", "power"],
    "stages": ["generate_script", "create_structure", "generate_tts", "package"]
}
```

**Request Body:**

Content-Type: `application/json`
Schema: `ChapterPipelineRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/characters/pipeline-status/{chapter_number}`

**Get Pipeline Status**

Get the current status of a chapter's automation pipeline.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `chapter_number` | path | integer | Yes |  |
| `output_base` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## cluster-health

### GET `/health/cluster`

**Get Cluster Health**

Get complete cluster health status.

Checks all configured services and returns comprehensive health info.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `refresh` | query | boolean | No | Force refresh (bypass cache) |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/health/summary`

**Get Health Summary**

Get quick health summary.

Returns just the summary without individual service details.

**Responses:**

- `200`: Successful Response

---

### GET `/health/services`

**Get Services Health**

Get per-service health status.

Supports filtering by category, node, or status.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `category` | query | any | No | Filter by category |
| `node` | query | any | No | Filter by node |
| `status` | query | any | No | Filter by status |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/health/service/{name}`

**Get Service Health**

Get health for a specific service.

Returns health info for the named service.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `name` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/health/nodes`

**Get Nodes Health**

Get health grouped by node.

Returns health counts for each cluster node.

**Responses:**

- `200`: Successful Response

---

### GET `/health/categories`

**Get Categories Health**

Get health grouped by category.

Returns health counts for each service category.

**Responses:**

- `200`: Successful Response

---

### GET `/health/prometheus`

**Query Prometheus**

Query Prometheus directly.

Execute a PromQL instant query against Prometheus.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `query` | query | string | Yes | PromQL query |
| `time` | query | any | No | Evaluation time (RFC3339 or Unix) |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/health/prometheus/range`

**Query Prometheus Range**

Query Prometheus range.

Execute a PromQL range query against Prometheus.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `query` | query | string | Yes | PromQL query |
| `start` | query | string | Yes | Start time |
| `end` | query | string | Yes | End time |
| `step` | query | string | No | Query step |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/health/gpu`

**Get Gpu Health**

Get GPU health metrics from Prometheus.

Returns GPU utilization, memory, and temperature across nodes.

**Responses:**

- `200`: Successful Response

---

## comfyui

### GET `/comfyui/queue`

**Get Queue Status**

Get current ComfyUI queue status.

**Responses:**

- `200`: Successful Response

---

### GET `/comfyui/history/{prompt_id}`

**Get Prompt History**

Get execution history for a prompt.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `prompt_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/comfyui/portrait`

**Generate Portrait**

Generate a character portrait.

**Request Body:**

Content-Type: `application/json`
Schema: `PortraitRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/comfyui/background`

**Generate Background**

Generate a scene background.

**Request Body:**

Content-Type: `application/json`
Schema: `hydra_tools__comfyui_client__create_comfyui_router__<locals>__BackgroundRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/comfyui/templates`

**List Templates**

List available workflow templates.

**Responses:**

- `200`: Successful Response

---

## constitution

### GET `/constitution/status`

**Get Status**

Get constitutional enforcer status

**Responses:**

- `200`: Successful Response

---

### POST `/constitution/check`

**Check Operation**

Check if an operation is allowed

**Request Body:**

Content-Type: `application/json`
Schema: `OperationCheck`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/constitution/audit`

**Get Audit Log**

Get audit log entries

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |
| `operation_type` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/constitution/emergency/stop`

**Emergency Stop**

Activate emergency stop

**Responses:**

- `200`: Successful Response

---

### POST `/constitution/emergency/resume`

**Emergency Resume**

Resume after emergency stop (requires human actor)

**Request Body:**

Content-Type: `application/json`
Schema: `EmergencyAction`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/constitution/constraints`

**Get Constraints**

Get all constitutional constraints

**Responses:**

- `200`: Successful Response

---

## container-health

### GET `/container-health/check-all`

**Check All Containers**

Run healthchecks on all configured containers.

**Responses:**

- `200`: Successful Response

---

### GET `/container-health/check/{container_name}`

**Check Single Container**

Run healthcheck on a specific container.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `container_name` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/container-health/status`

**Get Health Status**

Get current cached health status (without running new checks).

**Responses:**

- `200`: Successful Response

---

### GET `/container-health/unhealthy`

**Get Unhealthy Containers**

Get list of unhealthy containers.

**Responses:**

- `200`: Successful Response

---

### GET `/container-health/configs`

**Get Healthcheck Configs**

Get list of configured healthchecks.

**Responses:**

- `200`: Successful Response

---

### GET `/container-health/metrics`

**Get Prometheus Metrics**

Get Prometheus metrics for container health.

**Responses:**

- `200`: Successful Response

---

### POST `/container-health/restart/{container_name}`

**Restart Container**

Restart a container by name. Respects constitutional protections.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `container_name` | path | string | Yes |  |
| `reason` | query | string | No |  |
| `initiated_by` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/container-health/remediate`

**Remediate Container**

Execute a remediation action on a container with full audit logging.

**Request Body:**

Content-Type: `application/json`
Schema: `RemediationRequestFull`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/container-health/remediation-history`

**Get History**

Get remediation audit log history.

Filters:
- container_name: Filter by specific container
- action: Filter by action type (restart, stop, start)
- status: Filter by status (success, error, blocked)
- since: ISO timestamp to filter from

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |
| `container_name` | query | any | No |  |
| `action` | query | any | No |  |
| `status` | query | any | No |  |
| `since` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/container-health/remediation-stats`

**Get Stats**

Get statistics from the remediation audit log.

**Responses:**

- `200`: Successful Response

---

### GET `/container-health/list`

**List Containers**

List all running containers with their status.

**Responses:**

- `200`: Successful Response

---

## control

### GET `/control/mode`

**Get Mode**

Get current system mode.

**Responses:**

- `200`: Successful Response

---

### POST `/control/mode`

**Set Mode**

Set system mode.

**Request Body:**

Content-Type: `application/json`
Schema: `SetModeRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/control/check-action`

**Check Action**

Check if an action is allowed under current mode.

**Request Body:**

Content-Type: `application/json`
Schema: `CheckActionRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/control/emergency-stop`

**Emergency Stop**

Emergency stop - set safe mode immediately.

**Responses:**

- `200`: Successful Response

---

## conversation-cache

### GET `/conversation-cache/status`

**Cache Status**

Get conversation cache status and statistics.

**Responses:**

- `200`: Successful Response

---

### POST `/conversation-cache/initialize`

**Initialize Cache**

Initialize the conversation cache.

**Responses:**

- `200`: Successful Response

---

### POST `/conversation-cache/messages`

**Store Message**

Store a message in conversation history.

**Request Body:**

Content-Type: `application/json`
Schema: `StoreMessageRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/conversation-cache/conversations/{conversation_id}`

**Get Conversation**

Get conversation history.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `conversation_id` | path | string | Yes |  |
| `limit` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### DELETE `/conversation-cache/conversations/{conversation_id}`

**Clear Conversation**

Clear a conversation.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `conversation_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/conversation-cache/context`

**Cache Context**

Cache a preprocessed context window.

**Request Body:**

Content-Type: `application/json`
Schema: `CacheContextRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/conversation-cache/context/{context_hash}`

**Get Context**

Get cached context window.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `context_hash` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/conversation-cache/prompts`

**Cache Prompt**

Cache a prompt template.

**Request Body:**

Content-Type: `application/json`
Schema: `PromptTemplateRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/conversation-cache/prompts/{template_name}`

**Get Prompt**

Get a cached prompt template.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `template_name` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/conversation-cache/sessions`

**Set Session**

Store session state.

**Request Body:**

Content-Type: `application/json`
Schema: `SessionStateRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/conversation-cache/sessions/{session_id}`

**Get Session**

Get session state.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `session_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## crews

### GET `/crews/list`

**List Crews**

List all available crews and their capabilities.

Returns information about each crew's agents and available tasks.

**Responses:**

- `200`: Successful Response

---

### GET `/crews/status`

**Crews Status**

Get current status of crew system.

Returns availability and configuration info.

**Responses:**

- `200`: Successful Response

---

### POST `/crews/research/topic`

**Research Topic**

Research a topic using the Research Crew.

Orchestrates Web Researcher, Analyst, and Reporter agents to
gather information, synthesize findings, and generate a report.

**Request Body:**

Content-Type: `application/json`
Schema: `hydra_tools__crews_api__ResearchRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/crews/research/model`

**Research Model**

Research a specific AI model.

Gathers information about architecture, quantization options,
VRAM requirements, benchmarks, and recommended use cases.

**Request Body:**

Content-Type: `application/json`
Schema: `ModelResearchRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/crews/research/technology`

**Research Technology**

Research a technology or framework.

Investigates version history, features, integration requirements,
performance characteristics, and alternatives.

**Request Body:**

Content-Type: `application/json`
Schema: `TechnologyResearchRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/crews/monitoring/check`

**Monitoring Check**

Run a health check using the Monitoring Crew.

Orchestrates Health Monitor, Performance Analyst, and Alert Manager
to check cluster health, analyze trends, and generate alerts.

**Request Body:**

Content-Type: `application/json`
Schema: `MonitoringRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/crews/monitoring/quick`

**Monitoring Quick Check**

Run a quick health check (critical services only).

Faster check focusing on essential services.

**Responses:**

- `200`: Successful Response

---

### GET `/crews/monitoring/full`

**Monitoring Full Check**

Run a comprehensive health check.

Full check of all cluster components with detailed analysis.

**Responses:**

- `200`: Successful Response

---

### POST `/crews/monitoring/node`

**Monitoring Check Node**

Check health of a specific node.

Focused check on a single cluster node.

**Request Body:**

Content-Type: `application/json`
Schema: `NodeCheckRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/crews/monitoring/gpus`

**Monitoring Check Gpus**

Check GPU health across all nodes.

Monitors GPU memory, temperature, and utilization.

**Responses:**

- `200`: Successful Response

---

### GET `/crews/monitoring/inference`

**Monitoring Check Inference**

Check inference pipeline health.

Monitors TabbyAPI, Ollama, LiteLLM gateway status.

**Responses:**

- `200`: Successful Response

---

### POST `/crews/maintenance/run`

**Maintenance Run**

Run a custom maintenance task using the Maintenance Crew.

Orchestrates Planner, Executor, and Validator agents for safe
maintenance with rollback capability.

**Request Body:**

Content-Type: `application/json`
Schema: `MaintenanceRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/crews/maintenance/docker-cleanup`

**Maintenance Docker Cleanup**

Clean up Docker resources (images, volumes, networks).

Removes unused resources to reclaim disk space.

**Request Body:**

Content-Type: `application/json`
Schema: `DockerCleanupRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/crews/maintenance/database`

**Maintenance Database**

Run database maintenance (vacuum, analyze, etc).

Optimizes database performance and reclaims space.

**Request Body:**

Content-Type: `application/json`
Schema: `DatabaseMaintenanceRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/crews/maintenance/backup-databases`

**Maintenance Backup Databases**

Backup all databases to MinIO.

Creates snapshots of PostgreSQL, Qdrant, and Redis.

**Responses:**

- `200`: Successful Response

---

### POST `/crews/maintenance/update-containers`

**Maintenance Update Containers**

Update Docker containers to latest images.

Pulls new images and recreates containers with rollback.

**Request Body:**

Content-Type: `application/json`
Schema: `ContainerUpdateRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/crews/maintenance/nix-gc`

**Maintenance Nix Gc**

Run NixOS garbage collection.

Removes old generations and reclaims disk space.

**Request Body:**

Content-Type: `application/json`
Schema: `NixGCRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/crews/maintenance/optimize-qdrant`

**Maintenance Optimize Qdrant**

Optimize Qdrant collections.

Runs optimization on vector indices for better performance.

**Responses:**

- `200`: Successful Response

---

### POST `/crews/maintenance/model-cache-cleanup`

**Maintenance Model Cache Cleanup**

Clean up unused model cache files.

Removes old model files to reclaim disk space on hydra-ai.

**Responses:**

- `200`: Successful Response

---

### POST `/crews/maintenance/log-rotation`

**Maintenance Log Rotation**

Rotate and compress logs.

Archives old logs to save disk space.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `target` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## dashboard

### GET `/dashboard/agents`

**Get Agents**

Get all agents with their current status

**Responses:**

- `200`: Successful Response

---

### POST `/dashboard/agents`

**Create Agent**

Create a new agent (persisted)

**Request Body:**

Content-Type: `application/json`
Schema: `CreateAgentRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/dashboard/agents/{agent_id}`

**Get Agent**

Get specific agent details

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `agent_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### PATCH `/dashboard/agents/{agent_id}`

**Update Agent**

Update agent status/task

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `agent_id` | path | string | Yes |  |

**Request Body:**

Content-Type: `application/json`
Schema: `AgentUpdateRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### DELETE `/dashboard/agents/{agent_id}`

**Delete Agent**

Delete an agent (persisted)

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `agent_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/dashboard/agents/{agent_id}/thinking`

**Get Agent Thinking**

Get agent's thinking stream

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `agent_id` | path | string | Yes |  |
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/dashboard/agents/{agent_id}/thinking`

**Add Thinking Step**

Add a thinking step to agent's stream

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `agent_id` | path | string | Yes |  |

**Request Body:**

Content-Type: `application/json`
Schema: `ThinkingStepRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### PATCH `/dashboard/agents/{agent_id}/config`

**Update Agent Config**

Update agent configuration (persisted)

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `agent_id` | path | string | Yes |  |

**Request Body:**

Content-Type: `application/json`
Schema: `AgentConfigRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/dashboard/projects`

**Get Projects**

Get all projects

**Responses:**

- `200`: Successful Response

---

### GET `/dashboard/projects/{project_id}`

**Get Project**

Get specific project

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `project_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/dashboard/nodes`

**Get Nodes**

Get cluster node status with GPU metrics from Prometheus

**Responses:**

- `200`: Successful Response

---

### GET `/dashboard/services`

**Get Services**

Get service status from cluster health API

**Responses:**

- `200`: Successful Response

---

### GET `/dashboard/models`

**Get Models**

Get loaded and available AI models

**Responses:**

- `200`: Successful Response

---

### GET `/dashboard/collections`

**Get Collections**

Get knowledge base collections from Qdrant

**Responses:**

- `200`: Successful Response

---

### GET `/dashboard/stats`

**Get System Stats**

Get aggregated system statistics with real GPU metrics

**Responses:**

- `200`: Successful Response

---

## diagnosis

### POST `/diagnosis/failure`

**Record Failure**

Record a new failure event.

**Request Body:**

Content-Type: `application/json`
Schema: `FailureInput`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/diagnosis/resolve`

**Resolve Failure**

Mark a failure as resolved.

**Request Body:**

Content-Type: `application/json`
Schema: `ResolutionInput`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/diagnosis/report`

**Get Report**

Get diagnostic report.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `hours` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/diagnosis/report/markdown`

**Get Report Markdown**

Get diagnostic report as markdown.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `hours` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/diagnosis/patterns`

**List Patterns**

List all failure patterns.

**Responses:**

- `200`: Successful Response

---

### GET `/diagnosis/patterns/{pattern_id}`

**Get Pattern**

Get pattern details.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `pattern_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/diagnosis/remediation/{event_id}`

**Suggest Remediation**

Get auto-remediation suggestion for an event.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `event_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/diagnosis/health`

**Diagnosis Health**

Health check with current status.

**Responses:**

- `200`: Successful Response

---

## discord

### GET `/discord/status`

**Discord Status**

Check Discord integration status.

**Responses:**

- `200`: Successful Response

---

### POST `/discord/notify`

**Send Notification**

Send a notification to Discord.

**Request Body:**

Content-Type: `application/json`
Schema: `DiscordNotifyRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/discord/command/{command}`

**Execute Command**

Execute a Discord command (for testing).

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `command` | path | string | Yes |  |
| `arg` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/discord/briefing/morning`

**Send Morning Briefing**

Generate and send a comprehensive morning briefing.

Gathers:
- Cluster health status
- Container health summary
- Recent alerts
- GPU utilization
- Memory system status
- Pending tasks

Sends formatted briefing to Discord if configured.

**Request Body:**

Content-Type: `application/json`
Schema: `MorningBriefingConfig`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/discord/briefing/preview`

**Preview Briefing**

Preview what the morning briefing would contain without sending.

**Responses:**

- `200`: Successful Response

---

### POST `/discord/webhook/interaction`

**Discord Interaction**

Handle Discord interaction webhook.

This endpoint receives slash command interactions from Discord.
Requires setting up a Discord application with slash commands.

**Responses:**

- `200`: Successful Response

---

## discoveries

### GET `/discoveries/status`

**Get Status**

Get archive status and statistics.

**Responses:**

- `200`: Successful Response

---

### POST `/discoveries/archive`

**Archive Discovery**

Archive a new discovery.

**Request Body:**

Content-Type: `application/json`
Schema: `ArchiveRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/discoveries/list`

**List Discoveries**

List all discoveries.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `type` | query | any | No |  |
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/discoveries/search`

**Search Discoveries**

Search discoveries by query.

**Request Body:**

Content-Type: `application/json`
Schema: `hydra_tools__discovery_archive__SearchRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/discoveries/relevant`

**Find Relevant**

Find discoveries relevant to current context.

**Request Body:**

Content-Type: `application/json`
Schema: `RelevantRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/discoveries/{discovery_id}`

**Get Discovery**

Get a specific discovery by ID.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `discovery_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/discoveries/archive-session`

**Archive Session**

Archive a session summary for future reference.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `summary` | query | string | Yes |  |

**Request Body:**

Content-Type: `application/json`
Schema: `Body_archive_session_discoveries_archive_session_post`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/discoveries/improvements/successful`

**Get Successful Improvements**

Get improvements that resulted in benchmark increases.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## events

### GET `/api/v1/events/stream`

**Event Stream**

SSE endpoint for real-time dashboard updates.

Streams events to the client as they occur. The connection remains open
and events are pushed in real-time.

Args:
    client_id: Optional identifier for the client (auto-generated if not provided)
    events: Comma-separated list of event types to subscribe to

Event Types:
    - cluster_health: Overall cluster status (every 5s)
    - container_status: Container state changes
    - gpu_metrics: GPU utilization and temperature (every 5s)
    - agent_status: AI agent activity
    - alert: Alert notifications
    - heartbeat: Keep-alive signal (every 30s)

Returns:
    StreamingResponse with SSE content type

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `client_id` | query | any | No | Optional client identifier |
| `events` | query | any | No | Comma-separated list of event types to subscribe to |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/api/v1/events/broadcast/alert`

**Broadcast Alert**

Broadcast an alert to all connected clients.

Used by other services to push alert notifications.

**Request Body:**

Content-Type: `application/json`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/api/v1/events/broadcast/notification`

**Broadcast Notification**

Broadcast a notification to all connected clients.

Used for general notifications (not alerts).

**Request Body:**

Content-Type: `application/json`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/api/v1/events/broadcast/container-update`

**Broadcast Container Update**

Broadcast a container status update.

Called when a container starts, stops, or changes state.

**Request Body:**

Content-Type: `application/json`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/api/v1/events/broadcast/model-update`

**Broadcast Model Update**

Broadcast a model status update.

Called when a model loads, unloads, or changes status.

**Request Body:**

Content-Type: `application/json`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/api/v1/events/status`

**Get Sse Status**

Get SSE connection statistics.

**Responses:**

- `200`: Successful Response

---

## face-detection

### POST `/faces/detect`

**Detect Faces**

Detect faces in an image.

Returns face locations, confidence, and quality-relevant metrics.

**Request Body:**

Content-Type: `application/json`
Schema: `DetectRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/faces/analyze`

**Analyze For Quality**

Analyze image for quality scoring integration.

Returns face data formatted for asset_quality.py integration.

**Request Body:**

Content-Type: `application/json`
Schema: `DetectRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/faces/status`

**Detector Status**

Get face detector status.

**Responses:**

- `200`: Successful Response

---

## graphiti-memory

### GET `/graphiti/status`

**Graphiti Status**

Get Graphiti memory status and statistics.

**Responses:**

- `200`: Successful Response

---

### POST `/graphiti/initialize`

**Initialize Graphiti**

Initialize Graphiti connection.

**Responses:**

- `200`: Successful Response

---

### POST `/graphiti/episodes`

**Add Episode**

Add an episode to the knowledge graph.

**Request Body:**

Content-Type: `application/json`
Schema: `AddEpisodeRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/graphiti/search`

**Search Memory**

Search the knowledge graph with hybrid retrieval.

**Request Body:**

Content-Type: `application/json`
Schema: `hydra_tools__graphiti_memory__create_graphiti_router__<locals>__SearchRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/graphiti/hybrid-search`

**Hybrid Search Endpoint**

Hybrid search combining graph, semantic, and keyword search.

This is the recommended search endpoint for best accuracy.

**Request Body:**

Content-Type: `application/json`
Schema: `hydra_tools__graphiti_memory__create_graphiti_router__<locals>__SearchRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/graphiti/nodes/{uuid}`

**Get Node**

Get a specific node by UUID.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `uuid` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/graphiti/nodes/{uuid}/edges`

**Get Node Edges**

Get all edges connected to a node.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `uuid` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## hardware

### GET `/hardware/inventory`

**Get Hardware Inventory**

Get complete cluster hardware inventory.

Returns CPU, RAM, and GPU information for all nodes.
Results are cached for 60 seconds unless refresh=True.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `refresh` | query | boolean | No | Force refresh (bypass cache) |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/hardware/gpus`

**Get Gpu Status**

Get GPU status for all nodes.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `refresh` | query | boolean | No | Force refresh (bypass cache) |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/hardware/summary`

**Get Hardware Summary**

Get a quick summary of cluster hardware.

**Responses:**

- `200`: Successful Response

---

## home-automation

### GET `/home/status`

**Get Status**

Get Home Assistant connection status.

**Responses:**

- `200`: Successful Response

---

### GET `/home/rooms`

**Get Rooms**

Get all rooms with their states.

**Responses:**

- `200`: Successful Response

---

### GET `/home/devices`

**Get Devices**

Get all controllable devices.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `room_id` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/home/scenes`

**Get Scenes**

Get all scenes.

**Responses:**

- `200`: Successful Response

---

### POST `/home/light/control`

**Control Light**

Control a light entity.

**Request Body:**

Content-Type: `application/json`
Schema: `LightControlRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/home/scene/activate`

**Activate Scene**

Activate a scene.

**Request Body:**

Content-Type: `application/json`
Schema: `SceneActivateRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/home/room/{room_id}/lights/{action}`

**Control Room Lights**

Control all lights in a room.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `room_id` | path | string | Yes |  |
| `action` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## info

### GET `/`

**Root**

API root - basic info.

**Responses:**

- `200`: Successful Response

---

### GET `/health`

**Health Check**

Health check endpoint for container orchestration.

**Responses:**

- `200`: Successful Response

---

## ingest

### POST `/ingest`

**Ingest File**

Upload a file for ingestion.

Supports:
- Images (jpg, png, gif, webp) → Vision analysis + OCR
- PDFs → Text extraction + analysis
- Documents (txt, md, docx) → Text analysis
- Code files → Syntax analysis

Returns immediately with item ID. Poll /ingest/{id} for results.

**Request Body:**

Content-Type: `multipart/form-data`
Schema: `fastapi___compat__v2__Body_ingest_file_ingest_post`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/ingest`

**List Ingests**

List recent ingestions.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/ingest/clipboard`

**Ingest Clipboard**

Ingest a clipboard paste (base64-encoded image).

For Ctrl+V paste from Command Center UI.
Accepts data URL format (data:image/png;base64,...) or raw base64.

**Request Body:**

Content-Type: `application/json`
Schema: `hydra_tools__unified_ingest__create_ingest_router__<locals>__ClipboardRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/ingest/url`

**Ingest Url**

Ingest a URL.

Delegates to research queue for processing.
Supports web pages, GitHub repos, arXiv papers.

**Request Body:**

Content-Type: `application/json`
Schema: `hydra_tools__unified_ingest__create_ingest_router__<locals>__UrlRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/ingest/text`

**Ingest Text**

Ingest raw text content.

For pasting text directly into Command Center.

**Request Body:**

Content-Type: `application/json`
Schema: `hydra_tools__unified_ingest__create_ingest_router__<locals>__TextRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/ingest/{item_id}`

**Get Ingest Status**

Get status and results of an ingestion.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `item_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/ingest/{item_id}/stream`

**Stream Progress**

SSE stream for real-time progress updates.

Connect to this endpoint to receive progress events:
- progress: 0-100
- step: current processing step
- status: pending/processing/completed/failed

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `item_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/ingest/stats/summary`

**Get Ingest Stats**

Get ingestion statistics.

**Responses:**

- `200`: Successful Response

---

## knowledge

### POST `/knowledge/entry`

**Add Entry**

Add a knowledge entry for tracking.

**Request Body:**

Content-Type: `application/json`
Schema: `EntryInput`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/knowledge/metrics`

**Get Metrics**

Get knowledge store metrics.

**Responses:**

- `200`: Successful Response

---

### GET `/knowledge/stale`

**Find Stale**

Find stale entries.

**Responses:**

- `200`: Successful Response

---

### GET `/knowledge/redundant`

**Find Redundant**

Find redundant entries.

**Responses:**

- `200`: Successful Response

---

### POST `/knowledge/prune`

**Prune Entries**

Prune specified entries.

**Request Body:**

Content-Type: `application/json`
Schema: `PruneInput`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/knowledge/consolidate`

**Consolidate Entries**

Consolidate redundant entries.

**Request Body:**

Content-Type: `application/json`
Schema: `ConsolidateInput`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/knowledge/optimize`

**Run Optimization**

Run full optimization pass.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `prune_stale` | query | boolean | No |  |
| `consolidate_redundant` | query | boolean | No |  |
| `min_confidence` | query | number | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/knowledge/report`

**Get Health Report**

Get knowledge health report.

**Responses:**

- `200`: Successful Response

---

### GET `/knowledge/health`

**Knowledge Health**

Quick health check.

**Responses:**

- `200`: Successful Response

---

## letta-bridge

### GET `/letta-bridge/v1/models`

**List Models**

List available models (Letta agents).

**Responses:**

- `200`: Successful Response

---

### POST `/letta-bridge/v1/chat/completions`

**Chat Completions**

OpenAI-compatible chat completions endpoint.

**Request Body:**

Content-Type: `application/json`
Schema: `ChatCompletionRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/letta-bridge/health`

**Health**

Health check endpoint.

**Responses:**

- `200`: Successful Response

---

## logs

### GET `/logs/health`

**Get Health**

Get Loki health status.

**Responses:**

- `200`: Successful Response

---

### GET `/logs/services`

**Get Services**

Get list of services with logs.

**Responses:**

- `200`: Successful Response

---

### GET `/logs/query`

**Query Logs**

Query logs from Loki.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `service` | query | any | No | Filter by service/container name |
| `level` | query | any | No | Filter by log level (INFO, WARN, ERROR, DEBUG) |
| `search` | query | any | No | Text search in log messages |
| `hours` | query | integer | No | Hours of logs to fetch (1-168) |
| `limit` | query | integer | No | Maximum number of logs to return |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/logs/labels`

**Get Labels**

Get available log labels.

**Responses:**

- `200`: Successful Response

---

### GET `/logs/labels/{label}/values`

**Get Label Values**

Get values for a specific label.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `label` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## memory

### GET `/memory/status`

**Get Status**

Get memory system status.

**Responses:**

- `200`: Successful Response

---

### GET `/memory/core`

**Get Core Memory**

Get core memory context.

**Responses:**

- `200`: Successful Response

---

### POST `/memory/core`

**Set Core Memory**

Set a core memory value.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `category` | query | string | Yes |  |
| `content` | query | string | Yes |  |
| `key` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/memory/episodic`

**Record Episode**

Record an episodic event.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `content` | query | string | Yes |  |
| `event_type` | query | string | Yes |  |
| `session_id` | query | any | No |  |
| `outcome` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/memory/episodic/recent`

**Get Recent Episodes**

Get recent episodic memories.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |
| `session_id` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/memory/semantic`

**Store Fact**

Store a semantic fact.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `content` | query | string | Yes |  |
| `domain` | query | string | Yes |  |
| `confidence` | query | number | No |  |
| `source` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/memory/semantic/query`

**Query Knowledge**

Query semantic knowledge.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `query` | query | string | Yes |  |
| `domain` | query | any | No |  |
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/memory/procedural`

**Store Skill**

Store a procedural skill.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `skill_name` | query | string | Yes |  |
| `content` | query | string | Yes |  |

**Request Body:**

Content-Type: `application/json`
Schema: `Body_store_skill_memory_procedural_post`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/memory/procedural/find`

**Find Skill**

Find a skill matching context.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `context` | query | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/memory/procedural/extract`

**Extract Skill**

Extract a reusable skill from a completed task.

Uses LLM to analyze the task and extract a procedural skill
that can be reused in similar situations. This is a key pattern
from the MIRIX memory architecture for skill learning.

**Request Body:**

Content-Type: `application/json`
Schema: `SkillExtractionRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/memory/consolidate`

**Consolidate**

Run memory consolidation.

**Responses:**

- `200`: Successful Response

---

### GET `/memory/context`

**Assemble Context**

Assemble relevant context for a query.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `query` | query | string | Yes |  |
| `max_tokens` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/memory/stats`

**Get Stats**

Get memory statistics.

**Responses:**

- `200`: Successful Response

---

### POST `/memory/enable-qdrant`

**Enable Qdrant**

Enable Qdrant vector storage backend.

Switches from JSON file storage to Qdrant with semantic search.

**Responses:**

- `200`: Successful Response

---

### POST `/memory/disable-qdrant`

**Disable Qdrant**

Disable Qdrant and fall back to JSON storage.

**Responses:**

- `200`: Successful Response

---

### GET `/memory/qdrant-status`

**Qdrant Status**

Get Qdrant backend status.

**Responses:**

- `200`: Successful Response

---

### POST `/memory/migrate-to-qdrant`

**Migrate To Qdrant**

Migrate all memories from JSON storage to Qdrant.

This will:
1. Enable Qdrant backend
2. Copy all existing JSON memories to Qdrant with embeddings
3. Keep JSON as fallback

**Responses:**

- `200`: Successful Response

---

### POST `/memory/semantic-search`

**Semantic Search**

Perform semantic search across all memories.

Requires Qdrant backend to be enabled for true semantic search.
Falls back to text matching if using JSON backend.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `query` | query | string | Yes |  |
| `limit` | query | integer | No |  |
| `min_relevance` | query | number | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/memory/graph/status`

**Graph Status**

Get Neo4j graph store status.

**Responses:**

- `200`: Successful Response

---

### POST `/memory/graph/sync`

**Sync To Graph**

Sync all memories from Qdrant to Neo4j graph.

Creates Memory nodes in Neo4j for each memory in Qdrant.

**Responses:**

- `200`: Successful Response

---

### POST `/memory/graph/relationship`

**Create Relationship**

Create a relationship between two memories.

Common relationship types:
- RELATED_TO: General relationship
- DEPENDS_ON: Dependency relationship
- DERIVED_FROM: Source relationship
- CONTRADICTS: Contradictory facts
- SUPERSEDES: Updated information

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `from_id` | query | string | Yes |  |
| `to_id` | query | string | Yes |  |
| `rel_type` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/memory/graph/related/{memory_id}`

**Get Related Memories**

Get memories related to a given memory via graph traversal.

Enables multi-hop reasoning across connected facts.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `memory_id` | path | string | Yes |  |
| `max_hops` | query | integer | No |  |
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/memory/graph/path`

**Find Path**

Find the shortest path between two memories.

Returns the nodes and relationships along the path.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `from_id` | query | string | Yes |  |
| `to_id` | query | string | Yes |  |
| `max_hops` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/memory/decay/run`

**Run Decay**

Manually run memory decay process.

Applies time-based decay to memories that haven't been accessed recently.
Higher decay rates for less important memories.

**Responses:**

- `200`: Successful Response

---

### POST `/memory/conflicts/detect`

**Detect Conflicts**

Detect potentially conflicting memories.

Uses semantic similarity to find memories with high overlap
that might contain contradictory information.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `threshold` | query | number | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/memory/conflicts/resolve`

**Resolve Conflict**

Resolve a memory conflict by keeping one and marking the other as superseded.

The removed memory is not deleted but marked as superseded and moved to vault.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `keep_id` | query | string | Yes |  |
| `remove_id` | query | string | Yes |  |
| `create_supersedes_relationship` | query | boolean | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/memory/health/memory`

**Memory Health**

Get memory system health metrics.

Includes decay status, conflict warnings, and consolidation needs.

**Responses:**

- `200`: Successful Response

---

## optimization

### GET `/optimization/suggestions`

**Get Suggestions**

Get current optimization suggestions.

**Responses:**

- `200`: Successful Response

---

### GET `/optimization/patterns/{node}`

**Get Patterns**

Get utilization patterns for a node.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `node` | path | string | Yes |  |
| `hours` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/optimization/model-placement`

**Get Model Placement**

Get model placement suggestions.

**Responses:**

- `200`: Successful Response

---

### GET `/optimization/power`

**Get Power Recommendations**

Get power management recommendations.

**Responses:**

- `200`: Successful Response

---

### GET `/optimization/report`

**Get Report**

Get comprehensive optimization report.

**Responses:**

- `200`: Successful Response

---

### POST `/optimization/collect/{node}`

**Collect Snapshot**

Collect resource snapshot from node.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `node` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/optimization/health`

**Get Cluster Health**

Get cluster resource health summary.

**Responses:**

- `200`: Successful Response

---

## predictive-maintenance

### GET `/predictive/health`

**Get Health Report**

Get comprehensive predictive health report.

**Responses:**

- `200`: Successful Response

---

### GET `/predictive/disk`

**Get Disk Predictions**

Get disk space predictions.

**Responses:**

- `200`: Successful Response

---

### GET `/predictive/vram`

**Get Vram Predictions**

Get GPU VRAM predictions.

**Responses:**

- `200`: Successful Response

---

### GET `/predictive/thermal`

**Get Thermal Predictions**

Get GPU thermal predictions.

**Responses:**

- `200`: Successful Response

---

### GET `/predictive/memory`

**Get Memory Predictions**

Get system memory predictions.

**Responses:**

- `200`: Successful Response

---

### GET `/predictive/score`

**Get Cluster Score**

Get aggregate cluster health score.

**Responses:**

- `200`: Successful Response

---

### GET `/predictive/alerts/predictive`

**Get Predictive Alerts**

Get currently firing predictive alerts.

**Responses:**

- `200`: Successful Response

---

## preference-collector

### POST `/preference-collector/litellm/callback`

**Litellm Callback**

Webhook endpoint for LiteLLM callbacks.

Configure LiteLLM with:
```yaml
litellm_settings:
  success_callback: ["webhook"]
  failure_callback: ["webhook"]
  callbacks:
    webhook_url: "http://192.168.1.244:8700/preference-collector/litellm/callback"
```

**Responses:**

- `200`: Successful Response

---

### POST `/preference-collector/feedback`

**Submit Feedback**

Submit feedback for a previous interaction.

**Request Body:**

Content-Type: `application/json`
Schema: `FeedbackSubmission`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/preference-collector/stats`

**Get Collection Stats**

Get preference collection statistics.

**Responses:**

- `200`: Successful Response

---

### GET `/preference-collector/recommendations`

**Get Recommendations**

Get model recommendations based on collected data.

**Responses:**

- `200`: Successful Response

---

### POST `/preference-collector/analyze`

**Analyze Preferences**

Analyze collected preferences.

**Request Body:**

Content-Type: `application/json`
Schema: `InteractionQuery`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/preference-collector/simulate`

**Simulate Interaction**

Simulate an interaction for testing.
Useful for bootstrapping preference data.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `prompt` | query | string | Yes |  |
| `model` | query | string | Yes |  |
| `latency_ms` | query | integer | No |  |
| `feedback` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/preference-collector/sync-from-litellm`

**Sync From Litellm**

Sync usage data from LiteLLM SpendLogs database.

This is the primary method for collecting preference data.
Reads from LiteLLM's PostgreSQL database directly.

Args:
    limit: Max records to sync (default 100)
    since_hours: Only sync records from last N hours (default 24)

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |
| `since_hours` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/preference-collector/litellm-stats`

**Get Litellm Stats**

Get usage statistics directly from LiteLLM database.

This provides raw usage data before preference processing.

**Responses:**

- `200`: Successful Response

---

## preferences

### POST `/preferences/interaction`

**Record Interaction**

Record a user interaction for preference learning.

Feedback can be: positive, negative, regenerate, or null.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `prompt` | query | string | Yes |  |
| `model` | query | string | Yes |  |
| `response` | query | string | Yes |  |
| `latency_ms` | query | integer | No |  |
| `feedback` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/preferences/recommend`

**Get Recommendation**

Get model recommendation based on learned preferences.

Either provide a prompt (for auto-detection) or task_type.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `prompt` | query | string | No |  |
| `task_type` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/preferences/stats`

**Get Preference Stats**

Get current preference statistics.

**Responses:**

- `200`: Successful Response

---

## presence

### GET `/presence/status`

**Get Status**

Get current presence status.

**Responses:**

- `200`: Successful Response

---

### POST `/presence/sync`

**Sync Presence**

Sync presence state with Home Assistant.

**Responses:**

- `200`: Successful Response

---

### POST `/presence/set/{state}`

**Set Presence**

Manually set presence state.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `state` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/presence/configs`

**Get Configs**

Get presence configurations.

**Responses:**

- `200`: Successful Response

---

## reconcile

### GET `/reconcile/state`

**Get Cluster State**

Get current cluster state.

Queries all nodes for their current status and running services.

**Responses:**

- `200`: Successful Response

---

### GET `/reconcile/drift`

**Detect Drift**

Detect drift from desired state.

Compares current state against expected services and configuration.

**Responses:**

- `200`: Successful Response

---

### GET `/reconcile/plan`

**Generate Plan**

Generate reconciliation plan.

Creates a plan of actions to fix detected drift.

**Responses:**

- `200`: Successful Response

---

### POST `/reconcile/apply`

**Apply Reconciliation**

Apply reconciliation plan.

Executes actions to fix drift. Use dry_run=true to preview changes.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `dry_run` | query | boolean | No | Dry run (don't apply changes) |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/reconcile/desired`

**Get Desired State**

Get desired state configuration.

Returns the expected cluster configuration.

**Responses:**

- `200`: Successful Response

---

### POST `/reconcile/desired`

**Update Desired State**

Update desired state configuration.

Modifies the expected cluster configuration.
Note: This is a placeholder - actual persistence requires file/database storage.

**Request Body:**

Content-Type: `application/json`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/reconcile/history`

**Get Reconciliation History**

Get reconciliation history.

Returns recent reconciliation operations and their results.
Note: This is a placeholder - actual history requires persistence.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## reranker

### POST `/rerank/`

**Rerank Documents**

Rerank a list of documents based on relevance to query.

Methods:
- embedding: Fast cosine similarity reranking
- llm: LLM-based relevance scoring (slower but more accurate)

**Request Body:**

Content-Type: `application/json`
Schema: `RerankRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/rerank/health`

**Reranker Health**

Check reranker health.

**Responses:**

- `200`: Successful Response

---

## research

### POST `/research/web`

**Web Search**

Search the web using SearXNG metasearch engine.

Aggregates results from multiple search engines.

**Request Body:**

Content-Type: `application/json`
Schema: `WebSearchRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/research/topic`

**Research Topic**

Research a topic by searching and crawling relevant sources.

Combines SearXNG search with Firecrawl content extraction.
Optionally indexes results to the knowledge base.

**Request Body:**

Content-Type: `application/json`
Schema: `hydra_tools__search_api__ResearchRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/research/crawl`

**Crawl Url**

Crawl a single URL and return its content.

Uses Firecrawl to extract clean markdown content.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `url` | query | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## research-queue

### POST `/research/queue`

**Queue Research**

Queue a URL, document, or text for research analysis.

Source types:
- url: Web page URL
- arxiv: arXiv paper URL
- github: GitHub repository URL
- text: Raw text content
- document: File path (must be accessible to API)

Priorities:
- critical: Process immediately
- high: Process within the hour
- normal: Process in next batch
- low: Process when idle

**Request Body:**

Content-Type: `application/json`
Schema: `QueueItemRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/research/queue`

**List Queue**

List queued research items.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `status` | query | any | No |  |
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/research/queue/stats`

**Get Queue Stats**

Get research queue statistics.

**Responses:**

- `200`: Successful Response

---

### GET `/research/queue/results/completed`

**Get Completed Results**

Get all completed research analyses.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/research/queue/{item_id}`

**Get Queue Item**

Get a specific research item.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `item_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### DELETE `/research/queue/{item_id}`

**Delete Item**

Delete a research item from the queue.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `item_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/research/queue/{item_id}/process`

**Process Item**

Manually trigger processing of a queued item.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `item_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/research/queue/process-all`

**Process All Queued**

Trigger processing of all queued items.

**Responses:**

- `200`: Successful Response

---

## routing

### POST `/routing/classify`

**Classify Prompt**

Classify a prompt and recommend optimal model.

Returns model recommendation based on complexity analysis.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `prompt` | query | string | Yes |  |
| `system_prompt` | query | string | No |  |
| `prefer_quality` | query | boolean | No |  |
| `prefer_speed` | query | boolean | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/routing/tiers`

**Get Model Tiers**

Get available model tiers and their characteristics.

**Responses:**

- `200`: Successful Response

---

## sandbox

### GET `/sandbox/status`

**Get Status**

Get sandbox manager status.

**Responses:**

- `200`: Successful Response

---

### POST `/sandbox/execute`

**Execute Code**

Execute code in a sandboxed container.

Security features:
- Network isolation (default)
- Memory limits
- CPU limits
- Execution timeout
- Read-only filesystem
- Dropped capabilities

**Request Body:**

Content-Type: `application/json`
Schema: `ExecuteRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/sandbox/history`

**Get History**

Get recent execution history.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |
| `status` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/sandbox/test-isolation`

**Test Isolation**

Run isolation tests to verify sandbox security.

Tests:
- Network isolation
- Memory limits
- Read-only filesystem
- Basic execution
- Non-root user

**Responses:**

- `200`: Successful Response

---

### POST `/sandbox/cleanup`

**Cleanup Containers**

Clean up orphaned sandbox containers.

**Responses:**

- `200`: Successful Response

---

### GET `/sandbox/languages`

**Get Languages**

Get supported languages.

**Responses:**

- `200`: Successful Response

---

## scheduler

### GET `/scheduler/status`

**Get Status**

Get scheduler status and upcoming runs.

**Responses:**

- `200`: Successful Response

---

### POST `/scheduler/trigger/{crew_name}`

**Trigger Crew**

Manually trigger a crew run.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `crew_name` | path | string | Yes |  |
| `topic` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/scheduler/enable/{crew_name}`

**Enable Schedule**

Enable a crew schedule.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `crew_name` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/scheduler/disable/{crew_name}`

**Disable Schedule**

Disable a crew schedule.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `crew_name` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## search

### POST `/search/query`

**Hybrid Search**

Perform hybrid search combining semantic and keyword search.

Uses Qdrant for semantic similarity and Meilisearch for BM25 keyword matching.
Results are combined using weighted scoring.

**Request Body:**

Content-Type: `application/json`
Schema: `hydra_tools__search_api__SearchRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/search/semantic`

**Semantic Search**

Perform semantic-only search using vector similarity.

Uses Qdrant to find conceptually similar content.

**Request Body:**

Content-Type: `application/json`
Schema: `hydra_tools__search_api__SearchRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/search/keyword`

**Keyword Search**

Perform keyword-only search using BM25.

Uses Meilisearch for exact keyword matching.

**Request Body:**

Content-Type: `application/json`
Schema: `hydra_tools__search_api__SearchRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/search/collections`

**List Collections**

List available search collections and indexes.

**Responses:**

- `200`: Successful Response

---

## self-improvement

### GET `/self-improvement/status`

**Get Status**

Get self-improvement engine status

**Responses:**

- `200`: Successful Response

---

### POST `/self-improvement/benchmark`

**Run Benchmarks**

Run full benchmark suite

**Responses:**

- `200`: Successful Response

---

### GET `/self-improvement/benchmarks/baseline`

**Get Baseline**

Get baseline benchmark scores

**Responses:**

- `200`: Successful Response

---

### GET `/self-improvement/proposals`

**List Proposals**

List all proposals

**Responses:**

- `200`: Successful Response

---

### POST `/self-improvement/proposals`

**Create Proposal**

Create an improvement proposal

**Request Body:**

Content-Type: `application/json`
Schema: `ProposalCreate`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/self-improvement/proposals/{proposal_id}`

**Get Proposal**

Get a specific proposal

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `proposal_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/self-improvement/proposals/{proposal_id}/test`

**Test Proposal**

Test a proposal in sandbox

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `proposal_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/self-improvement/proposals/{proposal_id}/deploy`

**Deploy Proposal**

Deploy a validated proposal

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `proposal_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/self-improvement/archive`

**Get Archive**

Get improvement archive

**Responses:**

- `200`: Successful Response

---

### POST `/self-improvement/archive/{entry_id}/rollback`

**Rollback Improvement**

Rollback a deployed improvement

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `entry_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/self-improvement/analyze-and-propose`

**Analyze And Propose**

Analyze current benchmark results and use LLM to generate improvement proposals.

This is the core DGM-inspired workflow:
1. Run benchmarks to identify weak areas
2. Use LLM to analyze results and propose improvements
3. Return proposals ready for testing

**Responses:**

- `200`: Successful Response

---

### GET `/self-improvement/workflow`

**Get Improvement Workflow**

Get the full self-improvement workflow status.

**Responses:**

- `200`: Successful Response

---

### POST `/self-improvement/dgm-cycle`

**Run Dgm Cycle**

Run a complete Darwin Gödel Machine improvement cycle.

This is the FULL autonomous loop:
1. Run comprehensive benchmarks
2. Analyze results with LLM
3. Constitutional filter proposals
4. Archive benchmark results to Discovery Archive
5. Return actionable proposals

Safe to run autonomously - does not auto-deploy.

**Responses:**

- `200`: Successful Response

---

### POST `/self-improvement/quick-health-check`

**Quick Health Check**

Quick health check that can be run frequently.
Returns actionable insights without full benchmark suite.

**Responses:**

- `200`: Successful Response

---

## semantic-cache

### GET `/cache/status`

**Cache Status**

Get semantic cache status and statistics.

**Responses:**

- `200`: Successful Response

---

### POST `/cache/lookup`

**Cache Lookup**

Look up a query in the semantic cache.

Returns cached response if found with similarity above threshold.

**Request Body:**

Content-Type: `application/json`
Schema: `CacheLookupRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/cache/store`

**Cache Store**

Store a query-response pair in the cache.

**Request Body:**

Content-Type: `application/json`
Schema: `CacheStoreRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/cache/cleanup`

**Cache Cleanup**

Remove expired entries from the cache.

**Responses:**

- `200`: Successful Response

---

### GET `/cache/config`

**Cache Config**

Get current cache configuration.

**Responses:**

- `200`: Successful Response

---

### POST `/cache/initialize`

**Cache Initialize**

Initialize the semantic cache (create collection if needed).

**Responses:**

- `200`: Successful Response

---

## services

### GET `/services/unified`

**Get Unified Services**

Get all services with unified health status.

Merges:
- Homepage services.yaml (static config: name, url, icon)
- /health/cluster (live health: status, latency)

Returns services organized by category with real-time status.

**Responses:**

- `200`: Successful Response

---

### GET `/services/config`

**Get Services Config**

Get raw parsed Homepage services configuration.

Returns the parsed services.yaml without health data overlay.

**Responses:**

- `200`: Successful Response

---

### GET `/services/categories`

**Get Categories**

Get available service categories.

Returns list of categories and service counts per category.

**Responses:**

- `200`: Successful Response

---

### GET `/services/by-category/{category}`

**Get Services By Category**

Get services filtered by category.

Returns only services in the specified category with health status.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `category` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/services/by-node/{node}`

**Get Services By Node**

Get services filtered by cluster node.

Returns only services running on the specified node.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `node` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/services/health-summary`

**Get Health Summary**

Get aggregated health summary across all services.

Quick overview of system health without full service details.

**Responses:**

- `200`: Successful Response

---

### GET `/services/stream`

**Stream Service Updates**

Server-Sent Events stream for real-time service status updates.

Pushes updates every 10 seconds with current service health status.
Clients can use EventSource to subscribe to this stream.

**Responses:**

- `200`: Successful Response

---

## story-crew

### POST `/story/generate-chapter`

**Generate Chapter**

Generate a complete chapter using the story crew.

**Request Body:**

Content-Type: `application/json`
Schema: `GenerateChapterRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/story/generate-scene`

**Generate Scene**

Generate a single scene with design and dialogue.

**Request Body:**

Content-Type: `application/json`
Schema: `GenerateSceneRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/story/generate-dialogue`

**Generate Dialogue**

Generate dialogue variations for a character.

**Request Body:**

Content-Type: `application/json`
Schema: `DialogueRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/story/export-renpy/{chapter_number}`

**Export Renpy**

Export a generated chapter to Ren'Py format.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `chapter_number` | path | integer | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/story/crew-status`

**Crew Status**

Get story crew status.

**Responses:**

- `200`: Successful Response

---

## unraid

### GET `/api/v1/unraid/health`

**Unraid Health Check**

Check Unraid API connectivity and health.

Returns connection status, response time, and Unraid version.

**Responses:**

- `200`: Successful Response

---

### GET `/api/v1/unraid/array/status`

**Get Array Status**

Get Unraid array status.

Returns array state, disk counts, and parity check progress.

**Responses:**

- `200`: Successful Response

---

### POST `/api/v1/unraid/array/start`

**Start Array**

Start the Unraid array.

Requires array to be in STOPPED state.

**Responses:**

- `200`: Successful Response

---

### POST `/api/v1/unraid/array/stop`

**Stop Array**

Stop the Unraid array.

WARNING: This will stop all array-dependent services.

**Responses:**

- `200`: Successful Response

---

### POST `/api/v1/unraid/array/parity-check`

**Start Parity Check**

Start a parity check.

Args:
    correct: If true, correct any errors found (correcting check)

**Request Body:**

Content-Type: `application/json`
Schema: `ParityCheckRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/api/v1/unraid/array/parity-check/pause`

**Pause Parity Check**

Pause the current parity check.

**Responses:**

- `200`: Successful Response

---

### POST `/api/v1/unraid/array/parity-check/resume`

**Resume Parity Check**

Resume a paused parity check.

**Responses:**

- `200`: Successful Response

---

### POST `/api/v1/unraid/array/parity-check/cancel`

**Cancel Parity Check**

Cancel the current parity check.

**Responses:**

- `200`: Successful Response

---

### GET `/api/v1/unraid/disks`

**Get Disks**

Get all disk information.

Args:
    include_smart: Include detailed SMART attributes for each disk

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `include_smart` | query | boolean | No | Include detailed SMART attributes |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/api/v1/unraid/disks/health`

**Get Disk Health**

Get disk health summary.

Returns aggregated health status across all disks.

**Responses:**

- `200`: Successful Response

---

### GET `/api/v1/unraid/containers`

**List Containers**

List all Docker containers on Unraid.

**Responses:**

- `200`: Successful Response

---

### GET `/api/v1/unraid/containers/stats`

**Get Container Stats**

Get container statistics summary.

**Responses:**

- `200`: Successful Response

---

### GET `/api/v1/unraid/containers/{container_id}`

**Get Container**

Get a specific container by ID or name.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `container_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/api/v1/unraid/containers/{container_id}/start`

**Start Container**

Start a Docker container.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `container_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/api/v1/unraid/containers/{container_id}/stop`

**Stop Container**

Stop a Docker container.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `container_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/api/v1/unraid/containers/{container_id}/restart`

**Restart Container**

Restart a Docker container.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `container_id` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/api/v1/unraid/vms`

**List Vms**

List all virtual machines.

**Responses:**

- `200`: Successful Response

---

### POST `/api/v1/unraid/vms/{vm_uuid}/start`

**Start Vm**

Start a virtual machine.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `vm_uuid` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/api/v1/unraid/vms/{vm_uuid}/stop`

**Stop Vm**

Stop a virtual machine.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `vm_uuid` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/api/v1/unraid/vms/{vm_uuid}/pause`

**Pause Vm**

Pause a virtual machine.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `vm_uuid` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/api/v1/unraid/vms/{vm_uuid}/resume`

**Resume Vm**

Resume a paused virtual machine.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `vm_uuid` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/api/v1/unraid/system/info`

**Get System Info**

Get Unraid system information (CPU, memory, OS).

**Responses:**

- `200`: Successful Response

---

### GET `/api/v1/unraid/notifications`

**Get Notifications**

Get recent Unraid notifications.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No | Maximum notifications to return |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/api/v1/unraid/users`

**List Users**

List all Unraid users.

**Responses:**

- `200`: Successful Response

---

### GET `/api/v1/unraid/metrics`

**Get Comprehensive Metrics**

Get comprehensive metrics for dashboard display.

Returns aggregated data from array, disks, containers, and system.
Efficient single endpoint for dashboard refresh.

**Responses:**

- `200`: Successful Response

---

### GET `/api/v1/unraid/metrics/simple`

**Get Simple Metrics**

Get metrics from Unraid Simple Monitoring API (if installed).

Returns null if the Simple Monitoring API is not installed.

**Responses:**

- `200`: Successful Response

---

## vision

### GET `/vision/health`

**Vision Health**

Check vision service health and available models.

**Responses:**

- `200`: Successful Response

---

### GET `/vision/models`

**List Vision Models**

List available vision models.

**Responses:**

- `200`: Successful Response

---

### POST `/vision/pull/{model_name}`

**Pull Vision Model**

Pull a vision model.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `model_name` | path | string | Yes |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/vision/describe`

**Describe Image**

Generate a description of an image.

**Request Body:**

Content-Type: `application/json`
Schema: `DescribeRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/vision/question`

**Question Image**

Answer a question about an image.

**Request Body:**

Content-Type: `application/json`
Schema: `QuestionRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/vision/ocr`

**Ocr Image**

Extract text from an image.

**Request Body:**

Content-Type: `application/json`
Schema: `DescribeRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/vision/analyze`

**Analyze Image**

Perform detailed analysis of an image.

**Request Body:**

Content-Type: `application/json`
Schema: `AnalyzeRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/vision/screenshot`

**Analyze Screenshot**

Analyze a screenshot with UI understanding.

**Request Body:**

Content-Type: `application/json`
Schema: `AnalyzeRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/vision/upload`

**Upload And Analyze**

Upload an image file and analyze it.

**Request Body:**

Content-Type: `multipart/form-data`
Schema: `Body_upload_and_analyze_vision_upload_post`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## voice

### GET `/voice/status`

**Get Voice Status**

Get voice pipeline status.

Returns status of all voice pipeline components.
Optimized: Runs all health checks in parallel for faster response.

**Responses:**

- `200`: Successful Response

---

### POST `/voice/transcribe`

**Transcribe Audio**

Transcribe audio to text.

Uses faster-whisper for GPU-accelerated speech recognition.

**Request Body:**

Content-Type: `multipart/form-data`
Schema: `Body_transcribe_audio_voice_transcribe_post`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/voice/speak`

**Text To Speech**

Convert text to speech.

Uses Kokoro TTS for natural voice synthesis.

**Request Body:**

Content-Type: `application/json`
Schema: `SpeakRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/voice/chat`

**Voice Chat**

Full voice chat pipeline.

Processes text through LLM and optionally generates speech response.
Target latency: <500ms for simple queries.

**Request Body:**

Content-Type: `application/json`
Schema: `VoiceChatRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/voice/wake`

**Handle Wake Event**

Handle wake word detection.

Called when "Hey Hydra" is detected by the wakeword service.
Prepares the voice pipeline for incoming audio.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `confidence` | query | number | No |  |
| `model` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/voice/settings`

**Get Voice Settings**

Get current voice settings.

Returns voice, model, and feature configuration.

**Responses:**

- `200`: Successful Response

---

### POST `/voice/settings`

**Update Voice Settings**

Update voice settings.

Modifies voice, model, or feature configuration.

**Request Body:**

Content-Type: `application/json`
Schema: `VoiceSettingsRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### GET `/voice/voices`

**List Voices**

List available TTS voices.

Returns all voices available in Kokoro TTS.

**Responses:**

- `200`: Successful Response

---

### POST `/voice/chat/stream`

**Voice Chat Stream**

Streaming voice chat pipeline.

Uses LLM streaming + sentence-buffered TTS for lower perceived latency.
Returns SSE stream with audio chunks.

**Request Body:**

Content-Type: `application/json`
Schema: `VoiceChatRequest`

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## wake-word

### GET `/voice/wake/status`

**Get Status**

Get wake word detector status.

**Responses:**

- `200`: Successful Response

---

### POST `/voice/wake/start`

**Start Detection**

Start wake word detection.

**Responses:**

- `200`: Successful Response

---

### POST `/voice/wake/stop`

**Stop Detection**

Stop wake word detection.

**Responses:**

- `200`: Successful Response

---

### GET `/voice/wake/history`

**Get History**

Get detection history.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `limit` | query | integer | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/voice/wake/configure`

**Configure**

Configure wake word detection.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `model` | query | string | No |  |
| `threshold` | query | number | No |  |
| `vad_threshold` | query | number | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/voice/wake/test`

**Test Detection**

Test wake word detection by simulating a detection event.
Useful for testing the pipeline without actual audio.

**Responses:**

- `200`: Successful Response

---

### POST `/voice/wake/trigger-voice-chat`

**Trigger Voice Chat**

Trigger voice chat pipeline after wake word detection.

This endpoint is called by the wake word detection system
(e.g., Home Assistant, n8n workflow) with the user's spoken text.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `text` | query | string | Yes |  |
| `voice` | query | string | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

### POST `/voice/wake/callback`

**Wake Word Callback**

Callback endpoint for external wake word detection systems.

Called by Home Assistant, Wyoming satellite, or other systems
when a wake word is detected. Can optionally include audio or text.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|----|----------|-------------|
| `wake_word` | query | string | No |  |
| `confidence` | query | number | No |  |
| `audio_base64` | query | any | No |  |
| `text` | query | any | No |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

---

## API Statistics

- **Total Endpoints:** 471
- **Tag Categories:** 55

### Endpoints by Category

| Category | Endpoints |
|----------|-----------|
| activity | 7 |
| agent-scheduler | 8 |
| agentic-rag | 4 |
| aggregate | 1 |
| alerts | 13 |
| asset-quality | 7 |
| auth | 2 |
| autonomous | 28 |
| benchmark | 5 |
| calendar | 7 |
| capabilities | 5 |
| characters | 52 |
| cluster-health | 9 |
| comfyui | 5 |
| constitution | 6 |
| container-health | 11 |
| control | 4 |
| conversation-cache | 11 |
| crews | 20 |
| dashboard | 15 |
| diagnosis | 8 |
| discord | 6 |
| discoveries | 8 |
| events | 6 |
| face-detection | 3 |
| graphiti-memory | 7 |
| hardware | 3 |
| home-automation | 7 |
| info | 2 |
| ingest | 8 |
| knowledge | 9 |
| letta-bridge | 3 |
| logs | 5 |
| memory | 27 |
| optimization | 7 |
| predictive-maintenance | 7 |
| preference-collector | 8 |
| preferences | 3 |
| presence | 4 |
| reconcile | 7 |
| reranker | 2 |
| research | 3 |
| research-queue | 8 |
| routing | 2 |
| sandbox | 6 |
| scheduler | 4 |
| search | 4 |
| self-improvement | 14 |
| semantic-cache | 6 |
| services | 7 |
| story-crew | 5 |
| unraid | 26 |
| vision | 9 |
| voice | 9 |
| wake-word | 8 |

