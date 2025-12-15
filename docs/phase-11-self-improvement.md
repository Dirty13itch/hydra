# Phase 11: Self-Improvement Tools

**Status:** DEPLOYED
**API:** http://192.168.1.244:8700
**Docs:** http://192.168.1.244:8700/docs

## Overview

The `src/hydra_tools/` package contains autonomous improvement capabilities for the Hydra cluster.

## Components

### Intelligent Routing (`routellm.py`)

Prompt classifier for dynamic model routing:
- Routes simple tasks to 7B models (fast/cheap)
- Routes complex tasks to 70B models (quality)
- Routes code tasks to codestral

### Learning & Preferences (`preference_learning.py`)

User preference tracking:
- Records interactions with feedback
- Tracks model performance per task type
- Suggests preferred models based on history

### Self-Diagnosis (`self_diagnosis.py`)

Failure analysis engine:
- Classifies failures (inference, network, resource, etc.)
- Detects recurring patterns
- Suggests auto-remediation for known issues
- Generates diagnostic reports with health scores

### Resource Optimization (`resource_optimization.py`)

Cluster resource analyzer:
- Tracks GPU/CPU/RAM utilization patterns
- Suggests optimal model placement
- Provides power management recommendations

### Knowledge Optimization (`knowledge_optimization.py`)

Knowledge lifecycle management:
- Detects stale entries by category thresholds
- Finds redundant knowledge for consolidation
- Prunes with optional archival

### Capability Expansion (`capability_expansion.py`)

Feature gap tracking:
- Records capability gaps when tasks fail
- Prioritizes based on frequency and impact
- Generates roadmap entries for implementation

## API Integration

```python
from hydra_tools.self_diagnosis import create_diagnosis_router
from hydra_tools.resource_optimization import create_optimization_router
from hydra_tools.knowledge_optimization import create_knowledge_router
from hydra_tools.capability_expansion import create_capabilities_router

app.include_router(create_diagnosis_router())
app.include_router(create_optimization_router())
app.include_router(create_knowledge_router())
app.include_router(create_capabilities_router())
```

## Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| GET /health | Aggregate cluster health |
| GET /diagnosis | Self-diagnosis report |
| GET /optimization | Resource optimization suggestions |
| GET /knowledge | Knowledge health status |
| GET /capabilities | Capability gap tracking |
| POST /route | RouteLLM prompt classification |
