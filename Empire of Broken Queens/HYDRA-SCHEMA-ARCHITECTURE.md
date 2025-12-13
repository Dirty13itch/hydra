# Hydra Cluster - Complete Schema Architecture

## Overview

This document maps the complete schema system across all vertical layers of the Hydra cluster, defining data models, API contracts, state machines, and inter-layer communication patterns.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VERTICAL LAYER STACK                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 7: User Interface        │ Dashboards, CLI, API Clients              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 6: Application           │ AI Workloads, Agents, Pipelines           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 5: Orchestration         │ K8s, Job Queues, Workflows                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 4: Service Mesh          │ API Gateway, Service Discovery, Events    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 3: Memory/State          │ Databases, Caches, Vector Stores          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 2: Storage               │ NFS, PVs, Model Storage                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 1: Compute               │ GPUs, CPUs, Memory                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 0: Observability         │ Metrics, Logs, Traces, Alerts             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# Layer 7: User Interface Schemas

## 7.1 Dashboard Configuration Schema

```yaml
# Homepage dashboard widget configuration
type: HomepageConfig
properties:
  services:
    type: array
    items:
      type: ServiceWidget
      properties:
        name: string
        icon: string
        href: string
        description: string
        server: string
        port: integer
        widget:
          type: WidgetConfig
          properties:
            type: enum[docker, prometheus, custom]
            url: string
            key: string
            fields: array[string]

  bookmarks:
    type: array
    items:
      type: BookmarkGroup
      properties:
        name: string
        bookmarks: array[Bookmark]

  widgets:
    type: array
    items:
      type: InfoWidget
      properties:
        type: enum[search, datetime, openmeteo, resources]
        config: object
```

## 7.2 Control Plane UI State Schema

```typescript
// Frontend application state
interface ControlPlaneState {
  // Cluster overview
  cluster: {
    nodes: NodeStatus[];
    totalGpuMemory: number;
    usedGpuMemory: number;
    healthScore: number;
  };

  // Active workloads
  workloads: {
    id: string;
    name: string;
    type: WorkloadType;
    status: WorkloadStatus;
    node: string;
    gpuAllocation: GpuAllocation;
    startTime: timestamp;
    metrics: WorkloadMetrics;
  }[];

  // Job queue
  queue: {
    pending: QueuedJob[];
    running: QueuedJob[];
    completed: QueuedJob[];
    failed: QueuedJob[];
  };

  // Generation pipeline state
  pipeline: {
    currentTask: GenerationTask | null;
    progress: number;
    estimatedCompletion: timestamp | null;
    todayStats: GenerationStats;
  };
}

type WorkloadType =
  | 'inference'      // LLM inference
  | 'generation'     // Image generation
  | 'training'       // LoRA training
  | 'voice'          // Voice synthesis
  | 'video'          // Video generation
  | 'orchestration'; // Agent orchestration

type WorkloadStatus =
  | 'pending'
  | 'initializing'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'terminated';

interface GpuAllocation {
  gpuId: string;
  gpuName: string;
  vramAllocated: number;
  vramTotal: number;
  utilizationPercent: number;
}
```

## 7.3 CLI Command Schema

```yaml
# kubectl/k9s resource views
type: KubernetesResourceView
resources:
  - apiVersion: v1
    kind: Pod
    columns:
      - name: NAME
        jsonPath: .metadata.name
      - name: NODE
        jsonPath: .spec.nodeName
      - name: GPU
        jsonPath: .spec.containers[*].resources.limits.nvidia\.com/gpu
      - name: STATUS
        jsonPath: .status.phase
      - name: AGE
        jsonPath: .metadata.creationTimestamp

  - apiVersion: batch/v1
    kind: Job
    columns:
      - name: NAME
        jsonPath: .metadata.name
      - name: COMPLETIONS
        jsonPath: .status.succeeded
      - name: DURATION
        jsonPath: .status.completionTime
      - name: GPU
        jsonPath: .spec.template.spec.containers[*].resources.limits.nvidia\.com/gpu
```

---

# Layer 6: Application Schemas

## 6.1 Core Domain Models

### 6.1.1 Queen Entity (Empire of Broken Queens)

```typescript
// Core queen domain model - source of truth
interface Queen {
  // Identity
  id: string;                    // UUID
  slug: string;                  // URL-safe identifier (e.g., "emilie-ekstrom")
  name: string;                  // Display name
  title: string;                 // In-game title (e.g., "Nordic Ice")
  tier: QueenTier;              // Story tier

  // Physical DNA (19-trait system)
  physicalDna: PhysicalDna;

  // Personality DNA
  personalityDna: PersonalityDna;

  // Voice DNA
  voiceDna: VoiceDna;

  // Game state (per-playthrough, stored separately)
  // See GameState schema

  // Generation metadata
  generationConfig: GenerationConfig;

  // Asset references
  assets: QueenAssets;

  // Timestamps
  createdAt: timestamp;
  updatedAt: timestamp;
}

type QueenTier =
  | 'alpha'      // Act 1 - Emilie, Jordan, Nikki
  | 'elite'      // Act 2 - Puma, Nicolette
  | 'core'       // Act 2-3 - Alanah, Madison, Savannah
  | 'exotic'     // Act 3 - Esperanza
  | 'specialist' // Act 3-4 - Trina, Brooklyn
  | 'legacy';    // Act 4 - Ava, Shyla

interface PhysicalDna {
  // Measurements
  height: {
    inches: number;
    cm: number;
    category: 'petite' | 'average' | 'tall';
  };

  bust: {
    size: string;           // e.g., "34DD"
    enhanced: boolean;
    placement: 'high' | 'natural';
  };

  waist: number;            // inches
  hips: number;             // inches

  // Body type
  bodyType: 'petite' | 'athletic' | 'curvy' | 'hourglass' | 'amazon';
  fitness: 'slim' | 'toned' | 'athletic' | 'curvy';

  // Features
  hair: {
    color: string;
    style: string;
    length: 'short' | 'medium' | 'long';
  };

  eyes: {
    color: string;
    shape: string;
  };

  skin: {
    tone: string;
    features: string[];     // freckles, tattoos, etc.
  };

  ethnicity: string;
  agePresentation: string;  // e.g., "early 30s"

  // Distinctive features
  distinguishingFeatures: string[];
}

interface PersonalityDna {
  // Core traits (1-10 scale)
  dominance: number;
  submission: number;
  intelligence: number;
  manipulation: number;
  loyalty: number;
  jealousy: number;
  sensuality: number;
  aggression: number;

  // Corruption response
  corruptionResistance: number;     // How hard to corrupt
  corruptionSpeed: number;          // Once started, how fast
  surrenderStyle: 'gradual' | 'sudden' | 'fighting' | 'eager';

  // Communication style
  speechPatterns: string[];
  accent: string;
  verbalTics: string[];

  // Behavioral traits
  publicPersona: string;
  privatePersona: string;
  secretDesires: string[];
  triggers: string[];               // What breaks her resistance
}

interface VoiceDna {
  // Base characteristics
  accent: string;
  pitch: 'low' | 'medium' | 'high';
  timbre: string;

  // Emotional markers
  arousalMarkers: string[];         // How arousal sounds
  surrenderMarkers: string[];       // How surrender sounds

  // Reference files
  referenceClips: string[];         // Paths to voice samples
  trainedModelPath: string | null;  // GPT-SoVITS model
}

interface GenerationConfig {
  // Image generation
  basePrompt: string;               // Core prompt template
  negativePrompt: string;
  loraPath: string | null;
  loraStrength: number;
  instantIdReference: string | null;

  // Quality thresholds
  aestheticThreshold: number;       // LAION score minimum
  technicalThreshold: number;       // MUSIQ score minimum
  faceMatchThreshold: number;       // Face similarity minimum

  // Generation targets
  targetPortraits: number;
  targetExpressions: number;
  targetPoses: number;
  targetExplicit: number;
}

interface QueenAssets {
  // Reference images (input)
  references: {
    portraits: string[];
    fullBody: string[];
    expressions: string[];
  };

  // Generated images (output)
  generated: {
    portraits: AssetGroup;
    expressions: AssetGroup;
    poses: AssetGroup;
    explicit: AssetGroup;
  };

  // Voice assets
  voice: {
    referenceClips: string[];
    generatedLines: VoiceLine[];
  };

  // Video assets
  video: {
    idleLoops: string[];
    reactions: string[];
    cinematics: string[];
  };
}

interface AssetGroup {
  path: string;                     // Directory path
  count: number;
  qualityScores: {
    min: number;
    max: number;
    average: number;
  };
  lastGenerated: timestamp;
}

interface VoiceLine {
  id: string;
  text: string;
  corruptionLevel: number;
  emotion: string;
  audioPath: string;
  duration: number;
}
```

### 6.1.2 Generation Task Model

```typescript
// Generation task - represents a single generation job
interface GenerationTask {
  id: string;                       // UUID
  type: GenerationType;
  status: TaskStatus;
  priority: TaskPriority;

  // Target
  queenId: string;
  queenSlug: string;

  // Configuration
  config: GenerationTaskConfig;

  // Execution
  assignedNode: string | null;
  assignedGpu: string | null;
  startedAt: timestamp | null;
  completedAt: timestamp | null;

  // Results
  outputs: GenerationOutput[];
  qualityMetrics: QualityMetrics | null;

  // Error handling
  retryCount: number;
  maxRetries: number;
  lastError: string | null;

  // Metadata
  createdAt: timestamp;
  updatedAt: timestamp;
  createdBy: string;                // System or user
}

type GenerationType =
  | 'portrait'
  | 'expression'
  | 'pose'
  | 'explicit'
  | 'background'
  | 'video_idle'
  | 'video_reaction'
  | 'video_cinematic'
  | 'voice_line'
  | 'dialogue_batch'
  | 'lora_training';

type TaskStatus =
  | 'queued'
  | 'assigned'
  | 'running'
  | 'quality_check'
  | 'completed'
  | 'failed'
  | 'cancelled';

type TaskPriority =
  | 'critical'    // 1000 - Must run immediately
  | 'high'        // 100 - Priority queue
  | 'normal'      // 10 - Standard queue
  | 'low'         // 1 - Background/batch
  | 'idle';       // 0 - Only when nothing else

interface GenerationTaskConfig {
  // For image generation
  prompt?: string;
  negativePrompt?: string;
  model?: string;
  lora?: string;
  loraStrength?: number;
  steps?: number;
  cfg?: number;
  width?: number;
  height?: number;
  seed?: number;
  batchSize?: number;

  // For voice generation
  text?: string;
  voiceModel?: string;
  emotion?: string;
  speed?: number;

  // For video generation
  sourceImage?: string;
  duration?: number;
  fps?: number;
  motionType?: string;

  // For training
  trainingImages?: string[];
  epochs?: number;
  learningRate?: number;
  networkDim?: number;
}

interface GenerationOutput {
  id: string;
  path: string;
  type: 'image' | 'audio' | 'video' | 'model';

  // Quality scores
  aestheticScore: number | null;
  technicalScore: number | null;
  faceMatchScore: number | null;

  // Approval status
  approved: boolean;
  rejectionReason: string | null;

  // Metadata
  generatedAt: timestamp;
  generationParams: object;
}

interface QualityMetrics {
  totalGenerated: number;
  totalApproved: number;
  totalRejected: number;
  approvalRate: number;

  aestheticScores: {
    min: number;
    max: number;
    mean: number;
    stdDev: number;
  };

  technicalScores: {
    min: number;
    max: number;
    mean: number;
    stdDev: number;
  };

  faceMatchScores: {
    min: number;
    max: number;
    mean: number;
    stdDev: number;
  };
}
```

### 6.1.3 Agent Models

```typescript
// Multi-agent system models
interface Agent {
  id: string;
  name: string;
  type: AgentType;
  status: AgentStatus;

  // Configuration
  config: AgentConfig;

  // Memory references
  memoryConfig: AgentMemoryConfig;

  // Tool access
  tools: AgentTool[];

  // Execution context
  currentTask: AgentTask | null;

  // Metrics
  metrics: AgentMetrics;
}

type AgentType =
  | 'director'      // Plans scenes, coordinates other agents
  | 'writer'        // Generates dialogue
  | 'artist'        // Manages image generation
  | 'curator'       // Quality control
  | 'voice_actor'   // Voice synthesis
  | 'archivist'     // Memory management
  | 'guardian';     // Safety/guardrails

type AgentStatus =
  | 'idle'
  | 'planning'
  | 'executing'
  | 'waiting'       // Waiting for another agent
  | 'error';

interface AgentConfig {
  // LLM configuration
  model: string;                    // Model ID for TabbyAPI/LiteLLM
  temperature: number;
  maxTokens: number;
  systemPrompt: string;

  // Behavior
  autonomyLevel: 'supervised' | 'semi-autonomous' | 'autonomous';
  decisionThreshold: number;        // Confidence required for autonomous action
  escalationTarget: string | null;  // Agent to escalate to

  // Rate limits
  maxActionsPerMinute: number;
  maxTokensPerHour: number;
}

interface AgentMemoryConfig {
  // Short-term (context window)
  shortTermCapacity: number;        // Max tokens in working memory

  // Long-term (Qdrant)
  qdrantCollection: string;
  embeddingModel: string;
  retrievalLimit: number;

  // Procedural (PostgreSQL)
  taskHistoryLimit: number;

  // Letta integration
  lettaAgentId: string | null;
}

interface AgentTool {
  name: string;
  description: string;
  endpoint: string;                 // API endpoint
  inputSchema: JsonSchema;
  outputSchema: JsonSchema;
  rateLimit: number;                // Calls per minute
  requiresApproval: boolean;        // Human-in-the-loop
}

interface AgentTask {
  id: string;
  type: string;
  description: string;
  input: object;
  status: 'pending' | 'running' | 'completed' | 'failed';
  output: object | null;
  startedAt: timestamp;
  completedAt: timestamp | null;
}

interface AgentMetrics {
  tasksCompleted: number;
  tasksFailed: number;
  averageTaskDuration: number;
  tokensUsed: number;
  lastActiveAt: timestamp;
}
```

## 6.2 LLM Request/Response Schemas

### 6.2.1 TabbyAPI Schema

```typescript
// TabbyAPI OpenAI-compatible interface
interface TabbyApiRequest {
  // Standard OpenAI fields
  model: string;
  messages: ChatMessage[];
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  top_k?: number;

  // TabbyAPI extensions
  min_p?: number;
  typical_p?: number;
  repetition_penalty?: number;
  frequency_penalty?: number;
  presence_penalty?: number;

  // Sampler order
  sampler_order?: SamplerType[];

  // Grammar/constraints
  grammar?: string;                 // GBNF grammar
  json_schema?: JsonSchema;         // Structured output

  // Generation params
  stop?: string[];
  stream?: boolean;
  seed?: number;
}

interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

type SamplerType =
  | 'top_k'
  | 'top_p'
  | 'min_p'
  | 'typical_p'
  | 'temperature'
  | 'repetition_penalty';

interface TabbyApiResponse {
  id: string;
  object: 'chat.completion';
  created: number;
  model: string;
  choices: {
    index: number;
    message: {
      role: 'assistant';
      content: string;
    };
    finish_reason: 'stop' | 'length' | 'content_filter';
  }[];
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

// Streaming response
interface TabbyApiStreamChunk {
  id: string;
  object: 'chat.completion.chunk';
  created: number;
  model: string;
  choices: {
    index: number;
    delta: {
      role?: 'assistant';
      content?: string;
    };
    finish_reason: 'stop' | 'length' | null;
  }[];
}
```

### 6.2.2 ComfyUI API Schema

```typescript
// ComfyUI workflow execution
interface ComfyUIPromptRequest {
  prompt: ComfyUIWorkflow;
  client_id?: string;
}

interface ComfyUIWorkflow {
  // Node ID -> Node Definition
  [nodeId: string]: ComfyUINode;
}

interface ComfyUINode {
  class_type: string;
  inputs: {
    [inputName: string]: any;       // Literal value or [nodeId, outputIndex]
  };
  _meta?: {
    title?: string;
  };
}

// Standard workflow nodes for queen generation
interface QueenGenerationWorkflow {
  // Checkpoint loader
  '1': {
    class_type: 'CheckpointLoaderSimple';
    inputs: {
      ckpt_name: string;            // e.g., "RealVisXL_V5.0.safetensors"
    };
  };

  // LoRA loader (optional)
  '2': {
    class_type: 'LoraLoader';
    inputs: {
      model: ['1', 0];              // From checkpoint
      clip: ['1', 1];
      lora_name: string;
      strength_model: number;
      strength_clip: number;
    };
  };

  // Positive prompt
  '3': {
    class_type: 'CLIPTextEncode';
    inputs: {
      clip: ['2', 1];
      text: string;                 // Queen-specific prompt
    };
  };

  // Negative prompt
  '4': {
    class_type: 'CLIPTextEncode';
    inputs: {
      clip: ['2', 1];
      text: string;                 // Standard negative
    };
  };

  // KSampler
  '5': {
    class_type: 'KSampler';
    inputs: {
      model: ['2', 0];
      positive: ['3', 0];
      negative: ['4', 0];
      latent_image: ['6', 0];
      seed: number;
      steps: number;
      cfg: number;
      sampler_name: string;
      scheduler: string;
      denoise: number;
    };
  };

  // Empty latent
  '6': {
    class_type: 'EmptyLatentImage';
    inputs: {
      width: number;
      height: number;
      batch_size: number;
    };
  };

  // VAE decode
  '7': {
    class_type: 'VAEDecode';
    inputs: {
      samples: ['5', 0];
      vae: ['1', 2];
    };
  };

  // Save image
  '8': {
    class_type: 'SaveImage';
    inputs: {
      images: ['7', 0];
      filename_prefix: string;
    };
  };
}

// Queue response
interface ComfyUIQueueResponse {
  prompt_id: string;
  number: number;
  node_errors: object;
}

// History response
interface ComfyUIHistoryResponse {
  [promptId: string]: {
    prompt: [number, string, ComfyUIWorkflow, object, string[]];
    outputs: {
      [nodeId: string]: {
        images?: {
          filename: string;
          subfolder: string;
          type: string;
        }[];
      };
    };
    status: {
      status_str: string;
      completed: boolean;
      messages: [string, object][];
    };
  };
}
```

---

# Layer 5: Orchestration Schemas

## 5.1 Kubernetes Resource Schemas

### 5.1.1 Custom Resource Definitions

```yaml
# AI Workload CRD
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: aiworkloads.hydra.io
spec:
  group: hydra.io
  versions:
    - name: v1alpha1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required:
                - workloadType
                - gpuRequirements
              properties:
                workloadType:
                  type: string
                  enum:
                    - inference
                    - generation
                    - training
                    - voice
                    - video

                gpuRequirements:
                  type: object
                  properties:
                    minVram:
                      type: integer
                      description: Minimum VRAM in MB
                    preferredGpu:
                      type: string
                      description: Preferred GPU class
                    count:
                      type: integer
                      default: 1

                modelConfig:
                  type: object
                  properties:
                    modelPath:
                      type: string
                    modelSize:
                      type: integer
                    quantization:
                      type: string

                scaling:
                  type: object
                  properties:
                    minReplicas:
                      type: integer
                      default: 0
                    maxReplicas:
                      type: integer
                      default: 1
                    scaleToZeroDelay:
                      type: string
                      default: "15m"

            status:
              type: object
              properties:
                phase:
                  type: string
                gpuAllocation:
                  type: object
                conditions:
                  type: array
                  items:
                    type: object
  scope: Namespaced
  names:
    plural: aiworkloads
    singular: aiworkload
    kind: AIWorkload
    shortNames:
      - aiw

---
# Generation Job CRD
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: generationjobs.hydra.io
spec:
  group: hydra.io
  versions:
    - name: v1alpha1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required:
                - jobType
                - target
              properties:
                jobType:
                  type: string
                  enum:
                    - portrait
                    - expression
                    - voice
                    - video
                    - training

                target:
                  type: object
                  properties:
                    queenId:
                      type: string
                    queenSlug:
                      type: string
                    count:
                      type: integer
                      default: 1

                quality:
                  type: object
                  properties:
                    aestheticThreshold:
                      type: number
                      default: 6.5
                    technicalThreshold:
                      type: number
                      default: 70
                    faceMatchThreshold:
                      type: number
                      default: 0.7

                schedule:
                  type: object
                  properties:
                    priority:
                      type: string
                      enum: [critical, high, normal, low, idle]
                      default: normal
                    deadline:
                      type: string
                      format: date-time
                    runAfter:
                      type: string
                      format: date-time

            status:
              type: object
              properties:
                phase:
                  type: string
                  enum:
                    - Pending
                    - Queued
                    - Running
                    - QualityCheck
                    - Completed
                    - Failed
                generated:
                  type: integer
                approved:
                  type: integer
                rejected:
                  type: integer
                startTime:
                  type: string
                  format: date-time
                completionTime:
                  type: string
                  format: date-time
  scope: Namespaced
  names:
    plural: generationjobs
    singular: generationjob
    kind: GenerationJob
    shortNames:
      - genjob
```

### 5.1.2 Kueue Queue Schemas

```yaml
# Cluster Queue for GPU workloads
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: hydra-gpu-queue
spec:
  namespaceSelector: {}
  queueingStrategy: StrictFIFO

  resourceGroups:
    # Inference resources (hydra-ai)
    - coveredResources: ["cpu", "memory", "nvidia.com/gpu"]
      flavors:
        - name: inference-5090
          resources:
            - name: nvidia.com/gpu
              nominalQuota: 1
              borrowingLimit: 0
            - name: memory
              nominalQuota: 64Gi

        - name: inference-4090
          resources:
            - name: nvidia.com/gpu
              nominalQuota: 1
            - name: memory
              nominalQuota: 32Gi

    # Generation resources (hydra-compute)
        - name: generation-5070ti
          resources:
            - name: nvidia.com/gpu
              nominalQuota: 1
            - name: memory
              nominalQuota: 32Gi

        - name: generation-3060
          resources:
            - name: nvidia.com/gpu
              nominalQuota: 1
            - name: memory
              nominalQuota: 16Gi

  preemption:
    reclaimWithinCohort: Any
    withinClusterQueue: LowerPriority

---
# Local Queue in ai-workloads namespace
apiVersion: kueue.x-k8s.io/v1beta1
kind: LocalQueue
metadata:
  name: ai-jobs
  namespace: ai-workloads
spec:
  clusterQueue: hydra-gpu-queue

---
# Workload Priority Class mapping
apiVersion: kueue.x-k8s.io/v1beta1
kind: WorkloadPriorityClass
metadata:
  name: inference-critical
value: 1000000
description: "Critical inference - never preempt"

---
apiVersion: kueue.x-k8s.io/v1beta1
kind: WorkloadPriorityClass
metadata:
  name: generation-high
value: 100000
description: "Image generation - high priority"

---
apiVersion: kueue.x-k8s.io/v1beta1
kind: WorkloadPriorityClass
metadata:
  name: training-normal
value: 10000
description: "Training jobs - normal priority"
```

## 5.2 n8n Workflow Schemas

### 5.2.1 Workflow Definition Schema

```typescript
// n8n workflow structure
interface N8nWorkflow {
  id: string;
  name: string;
  active: boolean;

  nodes: N8nNode[];
  connections: N8nConnections;

  settings: {
    executionOrder: 'v0' | 'v1';
    saveDataSuccessExecution: 'all' | 'none';
    saveDataErrorExecution: 'all' | 'none';
    saveManualExecutions: boolean;
  };

  staticData: object;

  tags: string[];

  createdAt: string;
  updatedAt: string;
}

interface N8nNode {
  id: string;
  name: string;
  type: string;                     // e.g., "n8n-nodes-base.httpRequest"
  typeVersion: number;
  position: [number, number];

  parameters: object;               // Node-specific parameters

  credentials?: {
    [credentialType: string]: {
      id: string;
      name: string;
    };
  };

  disabled?: boolean;
  notes?: string;
  notesInFlow?: boolean;
}

interface N8nConnections {
  [sourceNodeName: string]: {
    main: Array<Array<{
      node: string;
      type: 'main';
      index: number;
    }>>;
  };
}

// Empire overnight generation workflow
const overnightGenerationWorkflow: N8nWorkflow = {
  id: 'overnight-generation',
  name: 'Empire Overnight Generation',
  active: true,

  nodes: [
    {
      id: 'cron',
      name: 'Schedule Trigger',
      type: 'n8n-nodes-base.scheduleTrigger',
      typeVersion: 1,
      position: [0, 0],
      parameters: {
        rule: {
          interval: [{
            field: 'cronExpression',
            expression: '0 22 * * *'  // 10 PM daily
          }]
        }
      }
    },
    {
      id: 'get-queue',
      name: 'Get Generation Queue',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4,
      position: [200, 0],
      parameters: {
        url: 'http://hydra-control-plane-backend:3101/api/generation/queue',
        method: 'GET',
        responseFormat: 'json'
      }
    },
    {
      id: 'expand-prompts',
      name: 'Expand Prompts via TabbyAPI',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4,
      position: [400, 0],
      parameters: {
        url: 'http://192.168.1.250:5000/v1/chat/completions',
        method: 'POST',
        bodyParameters: {
          model: 'current',
          messages: '={{ $json.promptExpansionMessages }}',
          max_tokens: 500
        }
      }
    },
    {
      id: 'queue-comfyui',
      name: 'Queue to ComfyUI',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4,
      position: [600, 0],
      parameters: {
        url: 'http://192.168.1.203:8188/prompt',
        method: 'POST',
        bodyParameters: {
          prompt: '={{ $json.workflow }}'
        }
      }
    },
    {
      id: 'quality-filter',
      name: 'Quality Filter',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4,
      position: [800, 0],
      parameters: {
        url: 'http://hydra-quality-scorer:8000/score',
        method: 'POST'
      }
    },
    {
      id: 'save-approved',
      name: 'Save Approved Images',
      type: 'n8n-nodes-base.function',
      typeVersion: 1,
      position: [1000, 0],
      parameters: {
        functionCode: `
          // Move approved images to final location
          const approved = $input.all().filter(i => i.json.approved);
          // ...
        `
      }
    }
  ],

  connections: {
    'Schedule Trigger': {
      main: [[{ node: 'Get Generation Queue', type: 'main', index: 0 }]]
    },
    'Get Generation Queue': {
      main: [[{ node: 'Expand Prompts via TabbyAPI', type: 'main', index: 0 }]]
    },
    // ... etc
  },

  settings: {
    executionOrder: 'v1',
    saveDataSuccessExecution: 'all',
    saveDataErrorExecution: 'all',
    saveManualExecutions: true
  },

  staticData: {},
  tags: ['empire', 'generation', 'overnight'],
  createdAt: '2025-12-12T00:00:00.000Z',
  updatedAt: '2025-12-12T00:00:00.000Z'
};
```

---

# Layer 4: Service Mesh Schemas

## 4.1 API Gateway Schema (LiteLLM)

```yaml
# LiteLLM router configuration
model_list:
  # Primary inference - TabbyAPI 70B
  - model_name: "hydra-70b"
    litellm_params:
      model: "openai/Midnight-Miqu-70B-v1.5"
      api_base: "http://192.168.1.250:5000/v1"
      api_key: "not-needed"
    model_info:
      id: "tabbyapi-70b"
      mode: "chat"
      max_tokens: 8192
      input_cost_per_token: 0
      output_cost_per_token: 0

  # Secondary inference - Ollama models
  - model_name: "hydra-qwen-7b"
    litellm_params:
      model: "ollama/qwen2.5:7b"
      api_base: "http://192.168.1.203:11434"
    model_info:
      id: "ollama-qwen-7b"
      mode: "chat"
      max_tokens: 4096

  - model_name: "hydra-qwen-32b"
    litellm_params:
      model: "ollama/qwen2.5:32b"
      api_base: "http://192.168.1.203:11434"
    model_info:
      id: "ollama-qwen-32b"
      mode: "chat"
      max_tokens: 4096

# Router settings
router_settings:
  routing_strategy: "least-busy"
  model_group_alias:
    "gpt-4": "hydra-70b"
    "gpt-3.5-turbo": "hydra-qwen-7b"
    "claude-3": "hydra-70b"

  # Fallback chain
  fallbacks:
    - "hydra-70b"
    - "hydra-qwen-32b"
    - "hydra-qwen-7b"

# Rate limiting
general_settings:
  master_key: "sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7"

  # Request limits
  max_budget: null
  budget_duration: null

  # Caching
  cache: true
  cache_params:
    type: "redis"
    host: "hydra-redis"
    port: 6379
    password: "ls32WXmttrQ6v3Jxw9bh6XmFqhCYmIC"
```

## 4.2 Event Schema

```typescript
// Inter-service event schema
interface HydraEvent {
  id: string;                       // UUID
  type: EventType;
  source: string;                   // Service that emitted
  timestamp: timestamp;

  // Event-specific payload
  payload: EventPayload;

  // Correlation
  correlationId: string;            // Links related events
  causationId: string | null;       // Event that caused this one

  // Metadata
  metadata: {
    version: string;
    environment: string;
    node: string;
  };
}

type EventType =
  // Generation events
  | 'generation.task.created'
  | 'generation.task.started'
  | 'generation.task.progress'
  | 'generation.task.completed'
  | 'generation.task.failed'
  | 'generation.image.created'
  | 'generation.image.approved'
  | 'generation.image.rejected'

  // Training events
  | 'training.lora.started'
  | 'training.lora.progress'
  | 'training.lora.completed'
  | 'training.lora.failed'

  // Agent events
  | 'agent.task.assigned'
  | 'agent.task.completed'
  | 'agent.memory.updated'
  | 'agent.escalation.requested'

  // System events
  | 'system.node.healthy'
  | 'system.node.unhealthy'
  | 'system.gpu.alert'
  | 'system.storage.alert'

  // Pipeline events
  | 'pipeline.overnight.started'
  | 'pipeline.overnight.completed'
  | 'pipeline.report.generated';

type EventPayload =
  | GenerationTaskEvent
  | ImageEvent
  | TrainingEvent
  | AgentEvent
  | SystemEvent
  | PipelineEvent;

interface GenerationTaskEvent {
  taskId: string;
  queenId: string;
  queenSlug: string;
  taskType: GenerationType;
  status: TaskStatus;
  progress?: number;
  generated?: number;
  approved?: number;
  error?: string;
}

interface ImageEvent {
  imageId: string;
  taskId: string;
  queenId: string;
  path: string;
  scores: {
    aesthetic: number;
    technical: number;
    faceMatch: number;
  };
  approved: boolean;
  rejectionReason?: string;
}

interface TrainingEvent {
  jobId: string;
  queenId: string;
  modelType: 'lora' | 'voice' | 'embedding';
  step: number;
  totalSteps: number;
  loss?: number;
  outputPath?: string;
}

interface AgentEvent {
  agentId: string;
  agentType: AgentType;
  taskId: string;
  action: string;
  result?: object;
  escalationReason?: string;
}

interface SystemEvent {
  node: string;
  component: 'gpu' | 'cpu' | 'memory' | 'storage' | 'network';
  status: 'healthy' | 'warning' | 'critical';
  metric?: string;
  value?: number;
  threshold?: number;
}

interface PipelineEvent {
  pipelineId: string;
  pipelineName: string;
  stage: string;
  status: 'started' | 'completed' | 'failed';
  stats?: {
    totalTasks: number;
    completedTasks: number;
    failedTasks: number;
    totalGenerated: number;
    totalApproved: number;
  };
}
```

## 4.3 Service Discovery Schema

```yaml
# Kubernetes Service definitions
apiVersion: v1
kind: Service
metadata:
  name: hydra-services
  namespace: ai-workloads
  labels:
    app.kubernetes.io/part-of: hydra
spec:
  # Internal DNS: hydra-services.ai-workloads.svc.cluster.local

---
# Service registry (stored in Redis)
type: ServiceRegistry
schema:
  services:
    type: map
    keyType: string
    valueType:
      type: object
      properties:
        name:
          type: string
        endpoints:
          type: array
          items:
            type: object
            properties:
              address: string
              port: integer
              protocol: string
              healthy: boolean
              lastCheck: timestamp
        metadata:
          type: object
          properties:
            version: string
            capabilities: array[string]
            gpuRequired: boolean
            gpuClass: string

# Example service registration
example:
  services:
    tabbyapi:
      name: "TabbyAPI"
      endpoints:
        - address: "192.168.1.250"
          port: 5000
          protocol: "http"
          healthy: true
          lastCheck: "2025-12-12T14:00:00Z"
      metadata:
        version: "0.15.0"
        capabilities:
          - "chat"
          - "completions"
          - "embeddings"
        gpuRequired: true
        gpuClass: "5090+4090"

    comfyui:
      name: "ComfyUI"
      endpoints:
        - address: "192.168.1.203"
          port: 8188
          protocol: "http"
          healthy: true
          lastCheck: "2025-12-12T14:00:00Z"
      metadata:
        version: "0.3.76"
        capabilities:
          - "txt2img"
          - "img2img"
          - "inpainting"
          - "video"
        gpuRequired: true
        gpuClass: "5070ti"
```

---

# Layer 3: Memory/State Schemas

## 3.1 PostgreSQL Schemas

### 3.1.1 Core Domain Tables

```sql
-- =============================================================================
-- QUEENS TABLE - Core entity
-- =============================================================================
CREATE TABLE queens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    title VARCHAR(200),
    tier VARCHAR(50) NOT NULL CHECK (tier IN ('alpha', 'elite', 'core', 'exotic', 'specialist', 'legacy')),

    -- Physical DNA (JSONB for flexibility)
    physical_dna JSONB NOT NULL DEFAULT '{}',

    -- Personality DNA
    personality_dna JSONB NOT NULL DEFAULT '{}',

    -- Voice DNA
    voice_dna JSONB NOT NULL DEFAULT '{}',

    -- Generation configuration
    generation_config JSONB NOT NULL DEFAULT '{}',

    -- Asset counts (denormalized for performance)
    portrait_count INTEGER DEFAULT 0,
    expression_count INTEGER DEFAULT 0,
    pose_count INTEGER DEFAULT 0,
    voice_line_count INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'reference_ready', 'lora_training', 'lora_ready', 'generation_active', 'complete')),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_queens_slug ON queens(slug);
CREATE INDEX idx_queens_tier ON queens(tier);
CREATE INDEX idx_queens_status ON queens(status);

-- =============================================================================
-- GENERATION_TASKS TABLE - Track all generation jobs
-- =============================================================================
CREATE TABLE generation_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Task identification
    task_type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',

    -- Target
    queen_id UUID REFERENCES queens(id) ON DELETE CASCADE,

    -- Configuration (full config stored as JSONB)
    config JSONB NOT NULL DEFAULT '{}',

    -- Execution
    status VARCHAR(50) DEFAULT 'queued',
    assigned_node VARCHAR(100),
    assigned_gpu VARCHAR(50),

    -- Progress
    total_count INTEGER DEFAULT 0,
    completed_count INTEGER DEFAULT 0,
    approved_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,

    -- Timing
    queued_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Error handling
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,

    -- Metadata
    created_by VARCHAR(100) DEFAULT 'system',
    k8s_job_name VARCHAR(253),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_gen_tasks_queen ON generation_tasks(queen_id);
CREATE INDEX idx_gen_tasks_status ON generation_tasks(status);
CREATE INDEX idx_gen_tasks_type ON generation_tasks(task_type);
CREATE INDEX idx_gen_tasks_queued ON generation_tasks(queued_at) WHERE status = 'queued';

-- =============================================================================
-- GENERATED_ASSETS TABLE - Track all generated files
-- =============================================================================
CREATE TABLE generated_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relationships
    task_id UUID REFERENCES generation_tasks(id) ON DELETE SET NULL,
    queen_id UUID REFERENCES queens(id) ON DELETE CASCADE,

    -- Asset identification
    asset_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size BIGINT,
    file_hash VARCHAR(64),  -- SHA256

    -- Quality scores
    aesthetic_score DECIMAL(5,3),
    technical_score DECIMAL(5,3),
    face_match_score DECIMAL(5,3),
    composite_score DECIMAL(5,3),

    -- Approval
    approved BOOLEAN DEFAULT FALSE,
    approval_method VARCHAR(50),  -- 'auto', 'manual'
    rejection_reason VARCHAR(500),

    -- Generation metadata
    generation_params JSONB DEFAULT '{}',
    prompt_used TEXT,
    seed BIGINT,

    -- Embedding reference (for similarity search)
    embedding_id VARCHAR(100),

    -- Timestamps
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_assets_queen ON generated_assets(queen_id);
CREATE INDEX idx_assets_type ON generated_assets(asset_type);
CREATE INDEX idx_assets_approved ON generated_assets(approved);
CREATE INDEX idx_assets_score ON generated_assets(composite_score DESC);

-- =============================================================================
-- QUALITY_METRICS TABLE - Aggregated quality statistics
-- =============================================================================
CREATE TABLE quality_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Period
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    granularity VARCHAR(20) NOT NULL,  -- 'hourly', 'daily', 'weekly'

    -- Target (optional - null for global)
    queen_id UUID REFERENCES queens(id) ON DELETE CASCADE,
    task_type VARCHAR(50),

    -- Counts
    total_generated INTEGER DEFAULT 0,
    total_approved INTEGER DEFAULT 0,
    total_rejected INTEGER DEFAULT 0,
    approval_rate DECIMAL(5,4),

    -- Score distributions
    aesthetic_scores JSONB DEFAULT '{}',  -- min, max, mean, stddev, percentiles
    technical_scores JSONB DEFAULT '{}',
    face_match_scores JSONB DEFAULT '{}',

    -- Rejection reasons
    rejection_breakdown JSONB DEFAULT '{}',  -- reason -> count

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_quality_period ON quality_metrics(period_start, period_end);
CREATE INDEX idx_quality_queen ON quality_metrics(queen_id);

-- =============================================================================
-- AGENT_TASKS TABLE - Multi-agent task tracking
-- =============================================================================
CREATE TABLE agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Agent
    agent_id VARCHAR(100) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,

    -- Task
    task_type VARCHAR(100) NOT NULL,
    task_description TEXT,
    input_data JSONB DEFAULT '{}',

    -- Execution
    status VARCHAR(50) DEFAULT 'pending',
    output_data JSONB,

    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Metrics
    tokens_used INTEGER DEFAULT 0,
    duration_ms INTEGER,

    -- Error
    error_message TEXT,

    -- Correlation
    correlation_id UUID,
    parent_task_id UUID REFERENCES agent_tasks(id)
);

-- Indexes
CREATE INDEX idx_agent_tasks_agent ON agent_tasks(agent_id);
CREATE INDEX idx_agent_tasks_status ON agent_tasks(status);
CREATE INDEX idx_agent_tasks_correlation ON agent_tasks(correlation_id);

-- =============================================================================
-- LORA_MODELS TABLE - Track trained LoRA models
-- =============================================================================
CREATE TABLE lora_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    queen_id UUID REFERENCES queens(id) ON DELETE CASCADE,
    model_name VARCHAR(200) NOT NULL,
    version INTEGER DEFAULT 1,

    -- Model details
    base_model VARCHAR(200) NOT NULL,
    network_dim INTEGER,
    network_alpha INTEGER,

    -- Training config
    training_config JSONB DEFAULT '{}',
    training_images INTEGER,
    training_steps INTEGER,
    final_loss DECIMAL(10,6),

    -- Files
    model_path VARCHAR(1000) NOT NULL,
    model_size BIGINT,

    -- Status
    status VARCHAR(50) DEFAULT 'training',

    -- Quality
    test_scores JSONB DEFAULT '{}',

    -- Timestamps
    training_started_at TIMESTAMP WITH TIME ZONE,
    training_completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_lora_queen ON lora_models(queen_id);
CREATE INDEX idx_lora_status ON lora_models(status);

-- =============================================================================
-- VOICE_MODELS TABLE - Track voice clone models
-- =============================================================================
CREATE TABLE voice_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    queen_id UUID REFERENCES queens(id) ON DELETE CASCADE,
    model_name VARCHAR(200) NOT NULL,

    -- Model type
    model_type VARCHAR(50) NOT NULL,  -- 'gpt-sovits', 'xtts', 'rvc'

    -- Training data
    reference_clips JSONB DEFAULT '[]',
    total_duration_seconds DECIMAL(10,2),

    -- Files
    model_path VARCHAR(1000) NOT NULL,

    -- Status
    status VARCHAR(50) DEFAULT 'training',

    -- Quality
    similarity_score DECIMAL(5,3),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- PLAYER_SAVES TABLE - Game save data (if needed)
-- =============================================================================
CREATE TABLE player_saves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    player_name VARCHAR(100),
    save_slot INTEGER NOT NULL,

    -- Game state
    current_act INTEGER DEFAULT 1,
    current_chapter INTEGER DEFAULT 1,

    -- Queen relationships (JSONB for flexibility)
    queen_states JSONB DEFAULT '{}',  -- queen_id -> {corruption, relationship, unlocked_scenes}

    -- Flags and variables
    flags JSONB DEFAULT '{}',
    variables JSONB DEFAULT '{}',

    -- Timestamps
    playtime_seconds INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- EVENTS TABLE - Event sourcing for audit trail
-- =============================================================================
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_type VARCHAR(100) NOT NULL,
    source VARCHAR(100) NOT NULL,

    -- Payload
    payload JSONB NOT NULL DEFAULT '{}',

    -- Correlation
    correlation_id UUID,
    causation_id UUID,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Timestamp (immutable)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Partitioning by time for performance
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_time ON events(created_at);
CREATE INDEX idx_events_correlation ON events(correlation_id);

-- =============================================================================
-- FUNCTIONS AND TRIGGERS
-- =============================================================================

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER queens_updated_at
    BEFORE UPDATE ON queens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER generation_tasks_updated_at
    BEFORE UPDATE ON generation_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Update queen asset counts
CREATE OR REPLACE FUNCTION update_queen_asset_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.approved = TRUE THEN
        UPDATE queens SET
            portrait_count = portrait_count + CASE WHEN NEW.asset_type = 'portrait' THEN 1 ELSE 0 END,
            expression_count = expression_count + CASE WHEN NEW.asset_type = 'expression' THEN 1 ELSE 0 END,
            pose_count = pose_count + CASE WHEN NEW.asset_type = 'pose' THEN 1 ELSE 0 END
        WHERE id = NEW.queen_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_asset_counts
    AFTER INSERT OR UPDATE ON generated_assets
    FOR EACH ROW
    EXECUTE FUNCTION update_queen_asset_counts();
```

### 3.1.2 Database Views

```sql
-- =============================================================================
-- VIEWS
-- =============================================================================

-- Queen generation status overview
CREATE VIEW v_queen_generation_status AS
SELECT
    q.id,
    q.slug,
    q.name,
    q.tier,
    q.status,
    q.portrait_count,
    q.expression_count,
    COALESCE(lm.status, 'none') as lora_status,
    COALESCE(vm.status, 'none') as voice_status,
    (q.generation_config->>'targetPortraits')::int as target_portraits,
    ROUND(q.portrait_count::decimal / NULLIF((q.generation_config->>'targetPortraits')::int, 0) * 100, 1) as portrait_progress
FROM queens q
LEFT JOIN lora_models lm ON q.id = lm.queen_id AND lm.status = 'ready'
LEFT JOIN voice_models vm ON q.id = vm.queen_id AND vm.status = 'ready';

-- Active generation tasks
CREATE VIEW v_active_tasks AS
SELECT
    gt.id,
    gt.task_type,
    q.slug as queen_slug,
    gt.status,
    gt.assigned_node,
    gt.assigned_gpu,
    gt.completed_count,
    gt.total_count,
    ROUND(gt.completed_count::decimal / NULLIF(gt.total_count, 0) * 100, 1) as progress,
    gt.started_at,
    EXTRACT(EPOCH FROM (NOW() - gt.started_at)) as duration_seconds
FROM generation_tasks gt
JOIN queens q ON gt.queen_id = q.id
WHERE gt.status IN ('queued', 'running', 'quality_check');

-- Daily generation statistics
CREATE VIEW v_daily_stats AS
SELECT
    DATE(ga.generated_at) as date,
    COUNT(*) as total_generated,
    COUNT(*) FILTER (WHERE ga.approved = TRUE) as approved,
    COUNT(*) FILTER (WHERE ga.approved = FALSE) as rejected,
    ROUND(AVG(ga.aesthetic_score), 3) as avg_aesthetic,
    ROUND(AVG(ga.technical_score), 3) as avg_technical,
    ROUND(COUNT(*) FILTER (WHERE ga.approved = TRUE)::decimal / NULLIF(COUNT(*), 0) * 100, 1) as approval_rate
FROM generated_assets ga
GROUP BY DATE(ga.generated_at)
ORDER BY date DESC;

-- GPU utilization by task type
CREATE VIEW v_gpu_utilization AS
SELECT
    gt.assigned_node,
    gt.assigned_gpu,
    gt.task_type,
    COUNT(*) as task_count,
    SUM(EXTRACT(EPOCH FROM (COALESCE(gt.completed_at, NOW()) - gt.started_at))) as total_seconds,
    AVG(EXTRACT(EPOCH FROM (gt.completed_at - gt.started_at))) as avg_duration
FROM generation_tasks gt
WHERE gt.started_at IS NOT NULL
GROUP BY gt.assigned_node, gt.assigned_gpu, gt.task_type;
```

## 3.2 Redis Schemas

```typescript
// Redis key patterns and data structures

// =============================================================================
// SESSION MANAGEMENT
// =============================================================================

// User sessions
// Key: session:{sessionId}
// Type: Hash
interface SessionData {
  userId: string;
  username: string;
  roles: string;           // JSON array
  createdAt: string;
  lastAccess: string;
  metadata: string;        // JSON object
}
// TTL: 24 hours

// =============================================================================
// CACHING
// =============================================================================

// LLM response cache
// Key: llm:cache:{hash(prompt+model+params)}
// Type: String (JSON)
interface LlmCacheEntry {
  response: string;
  model: string;
  tokens: number;
  cachedAt: string;
}
// TTL: 1 hour

// ComfyUI workflow cache
// Key: comfyui:workflow:{workflowId}
// Type: String (JSON)
// TTL: 24 hours

// Queen data cache
// Key: queen:{slug}
// Type: Hash
interface QueenCache {
  id: string;
  name: string;
  tier: string;
  physicalDna: string;     // JSON
  generationConfig: string; // JSON
  portraitCount: string;
  status: string;
}
// TTL: 5 minutes

// =============================================================================
// RATE LIMITING
// =============================================================================

// API rate limit counters
// Key: ratelimit:{service}:{clientId}:{window}
// Type: String (integer count)
// TTL: window duration

// Token budget tracking
// Key: tokens:{service}:{hour}
// Type: String (integer)
// TTL: 2 hours

// =============================================================================
// JOB QUEUES
// =============================================================================

// Generation task queue
// Key: queue:generation:{priority}
// Type: List (LPUSH/RPOP)
// Values: task IDs

// Processing tasks (in-flight)
// Key: processing:generation
// Type: Set
// Values: task IDs

// Dead letter queue
// Key: dlq:generation
// Type: List
// Values: JSON objects with task and error

// =============================================================================
// PUBSUB CHANNELS
// =============================================================================

// Event channels
// Channel: events:generation
// Channel: events:training
// Channel: events:system
// Channel: events:agents

// Live progress updates
// Channel: progress:{taskId}

// =============================================================================
// REAL-TIME STATE
// =============================================================================

// Current GPU allocation
// Key: gpu:allocation:{node}:{gpuIndex}
// Type: Hash
interface GpuAllocation {
  taskId: string;
  taskType: string;
  queenSlug: string;
  vramUsed: string;
  startedAt: string;
}

// Node health status
// Key: node:health:{nodeName}
// Type: Hash
interface NodeHealth {
  status: string;          // 'healthy', 'warning', 'critical'
  lastCheck: string;
  gpuTemp0: string;
  gpuTemp1: string;
  gpuMemory0: string;
  gpuMemory1: string;
  cpuUsage: string;
  memoryUsage: string;
}
// TTL: 60 seconds (stale = unhealthy)

// Active workflow state
// Key: workflow:state:{workflowId}
// Type: Hash
interface WorkflowState {
  status: string;
  currentStep: string;
  progress: string;
  startedAt: string;
  lastUpdate: string;
}

// =============================================================================
// LOCKS
// =============================================================================

// Distributed locks
// Key: lock:{resource}
// Type: String (lock owner ID)
// TTL: lock duration + buffer

// Examples:
// lock:lora:training:{queenSlug} - Only one LoRA training per queen
// lock:comfyui:batch - Only one batch at a time
// lock:overnight:pipeline - Only one overnight run
```

## 3.3 Qdrant Vector Schemas

```typescript
// Qdrant collection schemas

// =============================================================================
// QUEEN EMBEDDINGS COLLECTION
// =============================================================================

interface QueenEmbeddingsCollection {
  name: 'queen_embeddings';

  vectors: {
    // Face embedding from reference images
    face: {
      size: 512;           // InsightFace embedding dimension
      distance: 'Cosine';
    };

    // Style embedding from generated images
    style: {
      size: 768;           // CLIP embedding dimension
      distance: 'Cosine';
    };

    // Text embedding of physical description
    description: {
      size: 1024;          // Text embedding dimension
      distance: 'Cosine';
    };
  };

  payload: {
    queen_id: string;
    queen_slug: string;
    queen_name: string;
    tier: string;
    embedding_type: 'reference' | 'generated' | 'description';
    source_file: string;
    created_at: string;
  };
}

// =============================================================================
// GENERATED IMAGES COLLECTION
// =============================================================================

interface GeneratedImagesCollection {
  name: 'generated_images';

  vectors: {
    // Visual embedding for similarity search
    visual: {
      size: 768;           // CLIP ViT-L/14
      distance: 'Cosine';
    };
  };

  payload: {
    // Identity
    image_id: string;
    task_id: string;
    queen_id: string;
    queen_slug: string;

    // Classification
    asset_type: string;    // portrait, expression, pose, etc.

    // Quality
    aesthetic_score: number;
    technical_score: number;
    face_match_score: number;
    approved: boolean;

    // Generation
    prompt: string;
    seed: number;

    // File
    file_path: string;

    // Timestamp
    generated_at: string;
  };

  indexes: {
    queen_slug: 'keyword';
    asset_type: 'keyword';
    approved: 'bool';
    aesthetic_score: 'float';
  };
}

// =============================================================================
// DIALOGUE EMBEDDINGS COLLECTION
// =============================================================================

interface DialogueEmbeddingsCollection {
  name: 'dialogue_embeddings';

  vectors: {
    semantic: {
      size: 1024;          // Text embedding
      distance: 'Cosine';
    };
  };

  payload: {
    dialogue_id: string;
    queen_id: string;
    queen_slug: string;

    // Content
    text: string;
    speaker: string;       // 'queen' | 'player' | 'narrator'

    // Context
    corruption_level: number;
    scene: string;
    emotion: string;

    // Generation
    generated_by: string;  // model ID

    created_at: string;
  };

  indexes: {
    queen_slug: 'keyword';
    corruption_level: 'integer';
    emotion: 'keyword';
  };
}

// =============================================================================
// AGENT MEMORY COLLECTION
// =============================================================================

interface AgentMemoryCollection {
  name: 'agent_memory';

  vectors: {
    content: {
      size: 1024;
      distance: 'Cosine';
    };
  };

  payload: {
    memory_id: string;
    agent_id: string;
    agent_type: string;

    // Memory type
    memory_type: 'episodic' | 'semantic' | 'procedural';

    // Content
    content: string;
    summary: string;

    // Context
    task_id: string;
    correlation_id: string;

    // Importance
    importance: number;    // 0-1
    access_count: number;
    last_accessed: string;

    created_at: string;
  };

  indexes: {
    agent_id: 'keyword';
    memory_type: 'keyword';
    importance: 'float';
  };
}

// =============================================================================
// QDRANT OPERATIONS
// =============================================================================

// Create collection
const createQueenEmbeddings = {
  create_collection: {
    collection_name: 'queen_embeddings',
    vectors_config: {
      face: { size: 512, distance: 'Cosine' },
      style: { size: 768, distance: 'Cosine' },
      description: { size: 1024, distance: 'Cosine' }
    },
    optimizers_config: {
      memmap_threshold: 20000
    },
    replication_factor: 1
  }
};

// Search for similar faces
const searchSimilarFaces = {
  search: {
    collection_name: 'queen_embeddings',
    vector: {
      name: 'face',
      vector: [/* 512 floats */]
    },
    filter: {
      must: [
        { key: 'embedding_type', match: { value: 'reference' } }
      ]
    },
    limit: 10,
    with_payload: true
  }
};

// Find images by quality
const findHighQualityImages = {
  scroll: {
    collection_name: 'generated_images',
    filter: {
      must: [
        { key: 'approved', match: { value: true } },
        { key: 'aesthetic_score', range: { gte: 7.0 } }
      ]
    },
    limit: 100,
    with_payload: true,
    with_vectors: false
  }
};
```

## 3.4 Neo4j Graph Schemas

```cypher
// =============================================================================
// NODE SCHEMAS
// =============================================================================

// Queen node
CREATE CONSTRAINT queen_id IF NOT EXISTS
FOR (q:Queen) REQUIRE q.id IS UNIQUE;

CREATE CONSTRAINT queen_slug IF NOT EXISTS
FOR (q:Queen) REQUIRE q.slug IS UNIQUE;

// Queen properties
// (:Queen {
//   id: UUID,
//   slug: String,
//   name: String,
//   tier: String,
//   dominance: Float,
//   submission: Float,
//   jealousy: Float
// })

// Scene node
CREATE CONSTRAINT scene_id IF NOT EXISTS
FOR (s:Scene) REQUIRE s.id IS UNIQUE;

// (:Scene {
//   id: UUID,
//   name: String,
//   act: Integer,
//   chapter: Integer,
//   corruption_required: Integer
// })

// Dialogue node
CREATE CONSTRAINT dialogue_id IF NOT EXISTS
FOR (d:Dialogue) REQUIRE d.id IS UNIQUE;

// (:Dialogue {
//   id: UUID,
//   text: String,
//   speaker: String,
//   emotion: String,
//   corruption_level: Integer
// })

// Asset node
CREATE CONSTRAINT asset_id IF NOT EXISTS
FOR (a:Asset) REQUIRE a.id IS UNIQUE;

// (:Asset {
//   id: UUID,
//   type: String,
//   path: String,
//   approved: Boolean
// })

// =============================================================================
// RELATIONSHIP SCHEMAS
// =============================================================================

// Queen relationships
// (q1:Queen)-[:RIVALS_WITH {intensity: Float}]->(q2:Queen)
// (q1:Queen)-[:ALLIES_WITH {trust: Float}]->(q2:Queen)
// (q1:Queen)-[:JEALOUS_OF {trigger: String}]->(q2:Queen)
// (q:Queen)-[:APPEARS_IN]->(s:Scene)
// (q:Queen)-[:SPEAKS]->(d:Dialogue)
// (q:Queen)-[:HAS_ASSET]->(a:Asset)

// Scene relationships
// (s1:Scene)-[:LEADS_TO {choice: String}]->(s2:Scene)
// (s:Scene)-[:REQUIRES]->(s2:Scene)
// (s:Scene)-[:UNLOCKS]->(s2:Scene)

// =============================================================================
// SAMPLE QUERIES
// =============================================================================

// Find queens who would be jealous if player favors another
MATCH (target:Queen {slug: $targetSlug})
MATCH (jealous:Queen)-[r:JEALOUS_OF]->(target)
WHERE jealous.jealousy > 0.5
RETURN jealous.name, jealous.jealousy, r.trigger;

// Find scene path from current to target
MATCH path = shortestPath(
  (start:Scene {id: $currentSceneId})-[:LEADS_TO*]->(end:Scene {id: $targetSceneId})
)
RETURN path;

// Find all queens in a scene with their relationships
MATCH (s:Scene {id: $sceneId})<-[:APPEARS_IN]-(q:Queen)
OPTIONAL MATCH (q)-[r:RIVALS_WITH|ALLIES_WITH|JEALOUS_OF]-(other:Queen)
WHERE (other)-[:APPEARS_IN]->(s)
RETURN q, r, other;

// Find recommended next scenes based on corruption level
MATCH (current:Scene {id: $currentId})-[:LEADS_TO]->(next:Scene)
WHERE next.corruption_required <= $playerCorruption
MATCH (next)<-[:APPEARS_IN]-(q:Queen)
RETURN next, collect(q.name) as queens
ORDER BY next.corruption_required DESC
LIMIT 5;
```

## 3.5 Letta (MemGPT) Agent Memory Schema

```typescript
// Letta agent configuration and memory structure

interface LettaAgentConfig {
  // Agent identity
  agent_id: string;
  name: string;
  persona: string;

  // Model configuration
  llm_config: {
    model: string;          // e.g., "tabbyapi/70b"
    model_endpoint: string;
    model_endpoint_type: string;
    context_window: number;
  };

  // Embedding configuration
  embedding_config: {
    embedding_model: string;
    embedding_endpoint: string;
    embedding_dim: number;
  };

  // Memory configuration
  memory: {
    // Core memory (always in context)
    core_memory: {
      persona: string;      // Agent's self-description
      human: string;        // Description of user/system
    };

    // Recall memory (searchable)
    recall_memory: {
      type: 'qdrant';
      collection: string;
      search_limit: number;
    };

    // Archival memory (long-term storage)
    archival_memory: {
      type: 'qdrant';
      collection: string;
    };
  };

  // System prompt
  system: string;

  // Tools available
  tools: string[];
}

// Per-queen Letta agent
const queenAgentConfig: LettaAgentConfig = {
  agent_id: 'queen-emilie-agent',
  name: 'Emilie Ekström Agent',
  persona: `I am the AI agent responsible for Emilie Ekström, the Nordic Ice Queen.
I maintain her character consistency across all generations.
I know her physical attributes, personality traits, voice characteristics, and story arc.
I ensure all generated content aligns with her established character.`,

  llm_config: {
    model: 'tabbyapi/70b',
    model_endpoint: 'http://192.168.1.250:5000/v1',
    model_endpoint_type: 'openai',
    context_window: 8192
  },

  embedding_config: {
    embedding_model: 'text-embedding-3-small',
    embedding_endpoint: 'http://192.168.1.244:4000/v1',
    embedding_dim: 1024
  },

  memory: {
    core_memory: {
      persona: `Emilie Ekström Character Profile:
- Swedish CEO, former exotic dancer
- 5'10", athletic elegant build
- Brown hair, brown eyes, early 30s
- Cold exterior hiding deep submission desires
- Signature: Swedish accent, uses "Sir" when aroused
- Corruption triggers: power dynamics, being seen as object`,

      human: `Generation Pipeline System:
- Generates portraits, expressions, dialogue
- Must maintain character consistency
- Quality thresholds: aesthetic > 6.5, technical > 70
- Current status: LoRA trained, generation active`
    },

    recall_memory: {
      type: 'qdrant',
      collection: 'emilie_recall',
      search_limit: 10
    },

    archival_memory: {
      type: 'qdrant',
      collection: 'emilie_archival'
    }
  },

  system: `You are the character consistency agent for Emilie Ekström.
Your responsibilities:
1. Review generation prompts for character accuracy
2. Evaluate generated images for consistency
3. Write dialogue that matches her voice
4. Track her character development across scenes

Always respond in JSON format with your analysis and recommendations.`,

  tools: [
    'search_archival_memory',
    'insert_archival_memory',
    'search_recall_memory',
    'http_request',
    'send_message'
  ]
};

// Memory entry structure
interface LettaMemoryEntry {
  id: string;
  agent_id: string;

  // Memory content
  text: string;
  embedding: number[];

  // Metadata
  memory_type: 'recall' | 'archival';
  timestamp: string;

  // Contextual info
  source: string;          // What created this memory
  importance: number;      // 0-1 scale

  // Usage tracking
  access_count: number;
  last_accessed: string;
}

// Message format
interface LettaMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;

  // For tool calls
  tool_calls?: {
    id: string;
    type: 'function';
    function: {
      name: string;
      arguments: string;
    };
  }[];

  // For tool responses
  tool_call_id?: string;
  name?: string;
}
```

---

# Layer 2: Storage Schemas

## 2.1 NFS Directory Structure

```yaml
# NFS export: 192.168.1.244:/mnt/user/

# =============================================================================
# MODELS DIRECTORY
# =============================================================================
models/
  # Diffusion models
  diffusion/
    realvis-xl-v5.0/
      RealVisXL_V5.0.safetensors
      RealVisXL_V5.0_fp16.safetensors
    sdxl-base/
    flux/

  # LLM models (ExL2 format)
  exl2/
    Midnight-Miqu-70B-v1.5-exl2-2.5bpw/
      config.json
      model.safetensors
      tokenizer.json

  # LoRA models (generated)
  loras/
    empire/
      emilie_ekstrom_lora.safetensors
      jordan_night_lora.safetensors
      # ...

  # Embeddings
  embeddings/
    insightface/
    clip-vit-l-14/

  # Voice models
  voice/
    gpt-sovits/
      pretrained/
      queens/
        emilie/
        jordan/

  # GGUF models for Ollama
  ollama/
    blobs/
    manifests/

# =============================================================================
# HYDRA SHARED DIRECTORY
# =============================================================================
hydra_shared/
  # Empire of Broken Queens project
  empire-of-broken-queens/
    # Reference images (input)
    reference_images/
      {QueenName}/
        *.jpg
        *.png

    # Generated assets (output)
    assets/
      images/
        queens/
          {queen_slug}/
            portraits/
            expressions/
            poses/
            explicit/
        backgrounds/
        ui/

      loras/
        {queen_slug}_lora.safetensors

      voice/
        {queen_slug}/
          *.wav

      video/
        {queen_slug}/
          idle/
          reactions/
          cinematics/

    # Quality test outputs
    quality_tests/
      {date}/
        *.png
        scores.json

    # Game files
    game/
      scripts/
      images/
      audio/

    # Documentation
    docs/

    # Tools and configs
    tools/
      workflows/
        queen_portrait.json
        batch_generation.json

  # Temporary/scratch space
  temp/
    comfyui_output/
    training_temp/

  # Overnight generation outputs
  overnight/
    {date}/
      generated/
      approved/
      rejected/
      report.md
```

## 2.2 Kubernetes PersistentVolume Schemas

```yaml
# =============================================================================
# STORAGE CLASSES
# =============================================================================
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs-models
provisioner: nfs.csi.k8s.io
parameters:
  server: 192.168.1.244
  share: /mnt/user/models
reclaimPolicy: Retain
volumeBindingMode: Immediate
mountOptions:
  - nconnect=8
  - rsize=1048576
  - wsize=1048576
  - hard
  - noatime

---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs-shared
provisioner: nfs.csi.k8s.io
parameters:
  server: 192.168.1.244
  share: /mnt/user/hydra_shared
reclaimPolicy: Retain
volumeBindingMode: Immediate

---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-nvme
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete

# =============================================================================
# PERSISTENT VOLUMES
# =============================================================================
apiVersion: v1
kind: PersistentVolume
metadata:
  name: models-pv
  labels:
    type: nfs
    content: models
spec:
  capacity:
    storage: 2Ti
  accessModes:
    - ReadOnlyMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: nfs-models
  nfs:
    server: 192.168.1.244
    path: /mnt/user/models

---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: empire-assets-pv
  labels:
    type: nfs
    content: assets
spec:
  capacity:
    storage: 500Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: nfs-shared
  nfs:
    server: 192.168.1.244
    path: /mnt/user/hydra_shared/empire-of-broken-queens/assets

---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: comfyui-output-pv
  labels:
    type: nfs
    content: output
spec:
  capacity:
    storage: 100Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: nfs-shared
  nfs:
    server: 192.168.1.244
    path: /mnt/user/hydra_shared/temp/comfyui_output

# =============================================================================
# PERSISTENT VOLUME CLAIMS
# =============================================================================
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: models-pvc
  namespace: ai-workloads
spec:
  accessModes:
    - ReadOnlyMany
  storageClassName: nfs-models
  resources:
    requests:
      storage: 2Ti
  selector:
    matchLabels:
      content: models

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: empire-assets-pvc
  namespace: ai-workloads
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: nfs-shared
  resources:
    requests:
      storage: 500Gi
  selector:
    matchLabels:
      content: assets

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: comfyui-output-pvc
  namespace: ai-workloads
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: nfs-shared
  resources:
    requests:
      storage: 100Gi
  selector:
    matchLabels:
      content: output
```

---

# Layer 1: Compute Schemas

## 1.1 GPU Resource Definitions

```yaml
# GPU resource specifications per node

# =============================================================================
# HYDRA-AI NODE
# =============================================================================
node: hydra-ai
gpus:
  - index: 0
    name: "NVIDIA GeForce RTX 5090"
    uuid: "GPU-xxxxx"
    memory: 32768  # MB
    compute_capability: "12.0"
    pcie_bus: "0000:41:00.0"
    power_limit: 450  # Watts

    # K8s resource name
    resource: "nvidia.com/gpu"

    # Custom labels
    labels:
      hydra.io/gpu-class: "5090"
      hydra.io/gpu-vram: "32768"
      hydra.io/gpu-capability: "inference"

    # Workload affinity
    preferred_workloads:
      - "llm-inference-large"
      - "video-generation"
      - "multi-gpu-inference"

  - index: 1
    name: "NVIDIA GeForce RTX 4090"
    uuid: "GPU-yyyyy"
    memory: 24576  # MB
    compute_capability: "8.9"
    pcie_bus: "0000:61:00.0"
    power_limit: 300  # Watts

    resource: "nvidia.com/gpu"

    labels:
      hydra.io/gpu-class: "4090"
      hydra.io/gpu-vram: "24576"
      hydra.io/gpu-capability: "inference"

    preferred_workloads:
      - "llm-inference-medium"
      - "video-generation"
      - "image-generation"

# =============================================================================
# HYDRA-COMPUTE NODE
# =============================================================================
node: hydra-compute
gpus:
  - index: 0
    name: "NVIDIA GeForce RTX 5070 Ti"
    uuid: "GPU-zzzzz"
    memory: 16384  # MB
    compute_capability: "12.0"
    pcie_bus: "0000:01:00.0"
    power_limit: 285  # Watts

    resource: "nvidia.com/gpu"

    labels:
      hydra.io/gpu-class: "5070ti"
      hydra.io/gpu-vram: "16384"
      hydra.io/gpu-capability: "generation"

    preferred_workloads:
      - "image-generation"
      - "lora-training"
      - "video-short"

  - index: 1
    name: "NVIDIA GeForce RTX 3060"
    uuid: "GPU-wwwww"
    memory: 12288  # MB
    compute_capability: "8.6"
    pcie_bus: "0000:06:00.0"
    power_limit: 170  # Watts

    resource: "nvidia.com/gpu"

    labels:
      hydra.io/gpu-class: "3060"
      hydra.io/gpu-vram: "12288"
      hydra.io/gpu-capability: "auxiliary"

    preferred_workloads:
      - "voice-synthesis"
      - "embedding-generation"
      - "quality-scoring"
      - "ollama-small"
```

## 1.2 Workload Resource Requirements

```typescript
// Resource requirement profiles for different workload types

interface ResourceProfile {
  name: string;
  description: string;

  // GPU requirements
  gpu: {
    count: number;
    minVram: number;          // MB
    preferredClass: string[];
    exclusive: boolean;       // No GPU sharing
  };

  // CPU requirements
  cpu: {
    request: string;          // e.g., "2000m"
    limit: string;
  };

  // Memory requirements
  memory: {
    request: string;          // e.g., "16Gi"
    limit: string;
  };

  // Storage requirements
  storage: {
    ephemeral: string;        // Temp storage
    modelAccess: boolean;     // Needs /mnt/models
    outputAccess: boolean;    // Needs write to output
  };

  // Scheduling hints
  scheduling: {
    priority: string;
    preemptible: boolean;
    maxDuration: string;      // For jobs
  };
}

const resourceProfiles: Record<string, ResourceProfile> = {
  'llm-inference-70b': {
    name: 'LLM Inference (70B)',
    description: 'Large language model inference for 70B parameter models',
    gpu: {
      count: 2,
      minVram: 48000,
      preferredClass: ['5090', '4090'],
      exclusive: true
    },
    cpu: {
      request: '4000m',
      limit: '8000m'
    },
    memory: {
      request: '32Gi',
      limit: '64Gi'
    },
    storage: {
      ephemeral: '10Gi',
      modelAccess: true,
      outputAccess: false
    },
    scheduling: {
      priority: 'inference-critical',
      preemptible: false,
      maxDuration: 'unlimited'
    }
  },

  'image-generation-sdxl': {
    name: 'Image Generation (SDXL)',
    description: 'Stable Diffusion XL image generation',
    gpu: {
      count: 1,
      minVram: 10000,
      preferredClass: ['5070ti', '4090'],
      exclusive: false
    },
    cpu: {
      request: '2000m',
      limit: '4000m'
    },
    memory: {
      request: '16Gi',
      limit: '32Gi'
    },
    storage: {
      ephemeral: '20Gi',
      modelAccess: true,
      outputAccess: true
    },
    scheduling: {
      priority: 'generation-high',
      preemptible: true,
      maxDuration: 'unlimited'
    }
  },

  'lora-training-sdxl': {
    name: 'LoRA Training (SDXL)',
    description: 'LoRA fine-tuning for SDXL models',
    gpu: {
      count: 1,
      minVram: 14000,
      preferredClass: ['5070ti'],
      exclusive: true
    },
    cpu: {
      request: '4000m',
      limit: '8000m'
    },
    memory: {
      request: '32Gi',
      limit: '48Gi'
    },
    storage: {
      ephemeral: '50Gi',
      modelAccess: true,
      outputAccess: true
    },
    scheduling: {
      priority: 'training-normal',
      preemptible: true,
      maxDuration: '4h'
    }
  },

  'voice-synthesis': {
    name: 'Voice Synthesis (GPT-SoVITS)',
    description: 'Voice cloning and TTS generation',
    gpu: {
      count: 1,
      minVram: 8000,
      preferredClass: ['3060'],
      exclusive: false
    },
    cpu: {
      request: '2000m',
      limit: '4000m'
    },
    memory: {
      request: '8Gi',
      limit: '16Gi'
    },
    storage: {
      ephemeral: '10Gi',
      modelAccess: true,
      outputAccess: true
    },
    scheduling: {
      priority: 'generation-high',
      preemptible: true,
      maxDuration: 'unlimited'
    }
  },

  'quality-scoring': {
    name: 'Quality Scoring',
    description: 'Aesthetic and technical image quality assessment',
    gpu: {
      count: 1,
      minVram: 4000,
      preferredClass: ['3060'],
      exclusive: false
    },
    cpu: {
      request: '1000m',
      limit: '2000m'
    },
    memory: {
      request: '4Gi',
      limit: '8Gi'
    },
    storage: {
      ephemeral: '5Gi',
      modelAccess: true,
      outputAccess: false
    },
    scheduling: {
      priority: 'batch-low',
      preemptible: true,
      maxDuration: '1h'
    }
  }
};
```

---

# Layer 0: Observability Schemas

## 0.1 Prometheus Metrics Schema

```yaml
# Custom metrics definitions for Hydra cluster

# =============================================================================
# GPU METRICS
# =============================================================================
metrics:
  # GPU utilization
  - name: hydra_gpu_utilization_percent
    type: gauge
    help: "GPU compute utilization percentage"
    labels:
      - node
      - gpu_index
      - gpu_name

  - name: hydra_gpu_memory_used_bytes
    type: gauge
    help: "GPU memory used in bytes"
    labels:
      - node
      - gpu_index
      - gpu_name

  - name: hydra_gpu_memory_total_bytes
    type: gauge
    help: "GPU total memory in bytes"
    labels:
      - node
      - gpu_index
      - gpu_name

  - name: hydra_gpu_temperature_celsius
    type: gauge
    help: "GPU temperature in Celsius"
    labels:
      - node
      - gpu_index
      - gpu_name

  - name: hydra_gpu_power_watts
    type: gauge
    help: "GPU power draw in watts"
    labels:
      - node
      - gpu_index
      - gpu_name

# =============================================================================
# GENERATION METRICS
# =============================================================================
  - name: hydra_generation_tasks_total
    type: counter
    help: "Total generation tasks by status"
    labels:
      - task_type
      - status
      - queen_slug

  - name: hydra_generation_duration_seconds
    type: histogram
    help: "Generation task duration in seconds"
    labels:
      - task_type
      - queen_slug
    buckets: [1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600]

  - name: hydra_images_generated_total
    type: counter
    help: "Total images generated"
    labels:
      - queen_slug
      - asset_type
      - approved

  - name: hydra_quality_score
    type: histogram
    help: "Quality scores distribution"
    labels:
      - queen_slug
      - score_type  # aesthetic, technical, face_match
    buckets: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

  - name: hydra_approval_rate
    type: gauge
    help: "Image approval rate (0-1)"
    labels:
      - queen_slug
      - asset_type

# =============================================================================
# LLM METRICS
# =============================================================================
  - name: hydra_llm_requests_total
    type: counter
    help: "Total LLM requests"
    labels:
      - model
      - endpoint
      - status

  - name: hydra_llm_tokens_total
    type: counter
    help: "Total tokens processed"
    labels:
      - model
      - direction  # input, output

  - name: hydra_llm_request_duration_seconds
    type: histogram
    help: "LLM request duration"
    labels:
      - model
    buckets: [0.1, 0.5, 1, 2, 5, 10, 30, 60]

  - name: hydra_llm_tokens_per_second
    type: gauge
    help: "Current tokens per second throughput"
    labels:
      - model
      - node

# =============================================================================
# AGENT METRICS
# =============================================================================
  - name: hydra_agent_tasks_total
    type: counter
    help: "Total agent tasks"
    labels:
      - agent_id
      - agent_type
      - status

  - name: hydra_agent_task_duration_seconds
    type: histogram
    help: "Agent task duration"
    labels:
      - agent_type
    buckets: [1, 5, 10, 30, 60, 120, 300]

  - name: hydra_agent_memory_operations_total
    type: counter
    help: "Agent memory operations"
    labels:
      - agent_id
      - operation  # read, write, search

# =============================================================================
# QUEUE METRICS
# =============================================================================
  - name: hydra_queue_depth
    type: gauge
    help: "Current queue depth"
    labels:
      - queue_name
      - priority

  - name: hydra_queue_wait_seconds
    type: histogram
    help: "Time spent waiting in queue"
    labels:
      - queue_name
    buckets: [1, 5, 10, 30, 60, 300, 600, 1800, 3600]
```

## 0.2 Grafana Dashboard Schema

```json
{
  "dashboard": {
    "title": "Hydra Cluster - AI Operations",
    "uid": "hydra-ai-ops",
    "tags": ["hydra", "ai", "gpu"],

    "templating": {
      "list": [
        {
          "name": "node",
          "type": "query",
          "datasource": "Prometheus",
          "query": "label_values(hydra_gpu_utilization_percent, node)"
        },
        {
          "name": "queen",
          "type": "query",
          "datasource": "Prometheus",
          "query": "label_values(hydra_generation_tasks_total, queen_slug)"
        }
      ]
    },

    "panels": [
      {
        "title": "GPU Utilization",
        "type": "timeseries",
        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "hydra_gpu_utilization_percent{node=~\"$node\"}",
            "legendFormat": "{{node}} GPU{{gpu_index}}"
          }
        ]
      },
      {
        "title": "GPU Memory Usage",
        "type": "gauge",
        "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "hydra_gpu_memory_used_bytes / hydra_gpu_memory_total_bytes * 100"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "max": 100,
            "thresholds": {
              "steps": [
                {"value": 0, "color": "green"},
                {"value": 70, "color": "yellow"},
                {"value": 90, "color": "red"}
              ]
            }
          }
        }
      },
      {
        "title": "Generation Tasks",
        "type": "stat",
        "gridPos": {"x": 0, "y": 8, "w": 6, "h": 4},
        "targets": [
          {
            "expr": "sum(hydra_generation_tasks_total{status=\"running\"})",
            "legendFormat": "Running"
          },
          {
            "expr": "sum(hydra_generation_tasks_total{status=\"queued\"})",
            "legendFormat": "Queued"
          }
        ]
      },
      {
        "title": "Images Generated Today",
        "type": "stat",
        "gridPos": {"x": 6, "y": 8, "w": 6, "h": 4},
        "targets": [
          {
            "expr": "sum(increase(hydra_images_generated_total[24h]))"
          }
        ]
      },
      {
        "title": "Approval Rate",
        "type": "gauge",
        "gridPos": {"x": 12, "y": 8, "w": 6, "h": 4},
        "targets": [
          {
            "expr": "avg(hydra_approval_rate{queen_slug=~\"$queen\"})"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percentunit",
            "max": 1,
            "thresholds": {
              "steps": [
                {"value": 0, "color": "red"},
                {"value": 0.5, "color": "yellow"},
                {"value": 0.7, "color": "green"}
              ]
            }
          }
        }
      },
      {
        "title": "Quality Score Distribution",
        "type": "histogram",
        "gridPos": {"x": 0, "y": 12, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "sum(rate(hydra_quality_score_bucket{queen_slug=~\"$queen\"}[1h])) by (le)",
            "legendFormat": "{{le}}"
          }
        ]
      },
      {
        "title": "LLM Throughput",
        "type": "timeseries",
        "gridPos": {"x": 12, "y": 12, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "sum(rate(hydra_llm_tokens_total{direction=\"output\"}[5m]))",
            "legendFormat": "Tokens/sec"
          }
        ]
      },
      {
        "title": "Generation Queue Depth",
        "type": "timeseries",
        "gridPos": {"x": 0, "y": 20, "w": 12, "h": 6},
        "targets": [
          {
            "expr": "hydra_queue_depth",
            "legendFormat": "{{queue_name}} ({{priority}})"
          }
        ]
      },
      {
        "title": "GPU Temperatures",
        "type": "timeseries",
        "gridPos": {"x": 12, "y": 20, "w": 12, "h": 6},
        "targets": [
          {
            "expr": "hydra_gpu_temperature_celsius{node=~\"$node\"}",
            "legendFormat": "{{node}} GPU{{gpu_index}}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "celsius",
            "thresholds": {
              "steps": [
                {"value": 0, "color": "blue"},
                {"value": 60, "color": "green"},
                {"value": 80, "color": "yellow"},
                {"value": 90, "color": "red"}
              ]
            }
          }
        }
      }
    ]
  }
}
```

## 0.3 Alert Rules Schema

```yaml
# Prometheus alerting rules

groups:
  - name: hydra-gpu-alerts
    interval: 30s
    rules:
      - alert: GpuHighTemperature
        expr: hydra_gpu_temperature_celsius > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GPU temperature high on {{ $labels.node }}"
          description: "GPU {{ $labels.gpu_index }} on {{ $labels.node }} is at {{ $value }}°C"

      - alert: GpuCriticalTemperature
        expr: hydra_gpu_temperature_celsius > 90
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "GPU temperature critical on {{ $labels.node }}"
          description: "GPU {{ $labels.gpu_index }} on {{ $labels.node }} is at {{ $value }}°C - immediate action required"

      - alert: GpuMemoryExhausted
        expr: hydra_gpu_memory_used_bytes / hydra_gpu_memory_total_bytes > 0.95
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GPU memory nearly exhausted on {{ $labels.node }}"
          description: "GPU {{ $labels.gpu_index }} memory at {{ $value | humanizePercentage }}"

  - name: hydra-generation-alerts
    interval: 1m
    rules:
      - alert: GenerationQueueBacklog
        expr: hydra_queue_depth{queue_name="generation"} > 100
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Generation queue backlog"
          description: "{{ $value }} tasks queued for over 30 minutes"

      - alert: LowApprovalRate
        expr: hydra_approval_rate < 0.5
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Low image approval rate for {{ $labels.queen_slug }}"
          description: "Approval rate is {{ $value | humanizePercentage }} - check quality settings"

      - alert: GenerationTaskStuck
        expr: time() - hydra_generation_task_start_time > 3600
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Generation task stuck"
          description: "Task {{ $labels.task_id }} has been running for over 1 hour"

  - name: hydra-inference-alerts
    interval: 30s
    rules:
      - alert: TabbyApiDown
        expr: up{job="tabbyapi"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "TabbyAPI is down"
          description: "TabbyAPI inference service is not responding"

      - alert: LowInferenceThroughput
        expr: rate(hydra_llm_tokens_total{direction="output"}[5m]) < 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low LLM inference throughput"
          description: "Throughput is only {{ $value }} tokens/sec"

  - name: hydra-agent-alerts
    interval: 1m
    rules:
      - alert: AgentTaskFailureRate
        expr: rate(hydra_agent_tasks_total{status="failed"}[1h]) / rate(hydra_agent_tasks_total[1h]) > 0.1
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High agent task failure rate"
          description: "Agent {{ $labels.agent_id }} has {{ $value | humanizePercentage }} failure rate"
```

## 0.4 Log Schema (Loki)

```typescript
// Structured log format for Loki ingestion

interface HydraLogEntry {
  // Standard fields
  timestamp: string;         // ISO 8601
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'FATAL';
  message: string;

  // Service identification
  service: string;           // e.g., 'tabbyapi', 'comfyui', 'n8n'
  node: string;              // e.g., 'hydra-ai', 'hydra-compute'
  instance: string;          // Pod name or container ID

  // Request tracing
  trace_id?: string;
  span_id?: string;
  parent_span_id?: string;

  // Context
  correlation_id?: string;   // Links related operations
  user_id?: string;

  // Structured data
  data?: {
    // Generation logs
    task_id?: string;
    queen_slug?: string;
    asset_type?: string;

    // LLM logs
    model?: string;
    tokens_input?: number;
    tokens_output?: number;
    duration_ms?: number;

    // Quality logs
    aesthetic_score?: number;
    technical_score?: number;
    approved?: boolean;

    // Error logs
    error_type?: string;
    stack_trace?: string;

    // GPU logs
    gpu_index?: number;
    vram_used_mb?: number;
    temperature_c?: number;
  };
}

// Loki label configuration
const lokiLabels = {
  // Required labels (indexed)
  job: 'string',            // Service category
  instance: 'string',       // Specific instance
  level: 'string',          // Log level

  // Optional labels
  node: 'string',
  service: 'string',

  // Don't use high-cardinality labels
  // BAD: trace_id, task_id, user_id
};

// Example log queries
const lokiQueries = {
  // All errors in last hour
  errors: '{level="ERROR"} |= "" | json',

  // Generation task logs
  generationTasks: '{job="generation"} | json | task_id != ""',

  // LLM requests by model
  llmByModel: '{job="inference"} | json | model="Midnight-Miqu-70B"',

  // Quality failures
  qualityFailures: '{job="quality"} | json | approved="false"',

  // GPU temperature warnings
  gpuWarnings: '{job="gpu-monitor", level=~"WARN|ERROR"}'
};
```

---

# Inter-Layer Communication

## API Contract Definitions

```typescript
// =============================================================================
// CONTROL PLANE API
// =============================================================================

// POST /api/generation/tasks
interface CreateGenerationTaskRequest {
  taskType: GenerationType;
  queenId: string;
  config: GenerationTaskConfig;
  priority?: TaskPriority;
  scheduledFor?: string;       // ISO 8601 datetime
}

interface CreateGenerationTaskResponse {
  taskId: string;
  status: 'queued';
  position: number;            // Queue position
  estimatedStart: string;
}

// GET /api/generation/tasks/{taskId}
interface GetGenerationTaskResponse {
  task: GenerationTask;
  outputs: GenerationOutput[];
  metrics: QualityMetrics | null;
}

// GET /api/queens/{slug}
interface GetQueenResponse {
  queen: Queen;
  stats: {
    totalAssets: number;
    approvalRate: number;
    lastGenerated: string;
  };
  recentOutputs: GenerationOutput[];
}

// POST /api/queens/{slug}/generate
interface GenerateQueenAssetsRequest {
  assetTypes: GenerationType[];
  count: number;
  priority?: TaskPriority;
}

// =============================================================================
// COMFYUI API BRIDGE
// =============================================================================

// POST /api/comfyui/queue
interface QueueComfyUIWorkflowRequest {
  workflow: ComfyUIWorkflow;
  queenSlug: string;
  taskType: GenerationType;
  metadata: {
    correlationId: string;
    priority: TaskPriority;
  };
}

interface QueueComfyUIWorkflowResponse {
  promptId: string;
  queuePosition: number;
}

// =============================================================================
// QUALITY SERVICE API
// =============================================================================

// POST /api/quality/score
interface ScoreImageRequest {
  imagePath: string;
  queenSlug: string;
  referenceEmbeddingId?: string;
}

interface ScoreImageResponse {
  imageId: string;
  scores: {
    aesthetic: number;
    technical: number;
    faceMatch: number;
    composite: number;
  };
  approved: boolean;
  rejectionReason?: string;
}

// POST /api/quality/batch
interface BatchScoreRequest {
  images: {
    path: string;
    queenSlug: string;
  }[];
}

interface BatchScoreResponse {
  results: ScoreImageResponse[];
  summary: {
    total: number;
    approved: number;
    rejected: number;
    averageScores: {
      aesthetic: number;
      technical: number;
      faceMatch: number;
    };
  };
}

// =============================================================================
// AGENT API
// =============================================================================

// POST /api/agents/{agentId}/task
interface AssignAgentTaskRequest {
  taskType: string;
  input: object;
  context?: {
    correlationId: string;
    parentTaskId?: string;
  };
}

interface AssignAgentTaskResponse {
  taskId: string;
  status: 'pending' | 'running';
  estimatedDuration?: number;
}

// GET /api/agents/{agentId}/memory/search
interface SearchAgentMemoryRequest {
  query: string;
  memoryType?: 'recall' | 'archival';
  limit?: number;
}

interface SearchAgentMemoryResponse {
  results: {
    id: string;
    content: string;
    relevance: number;
    metadata: object;
  }[];
}
```

---

# Schema Versioning

```yaml
# Schema version tracking
schemas:
  domain:
    queen: "1.0.0"
    generation_task: "1.0.0"
    agent: "1.0.0"

  database:
    postgresql: "1.0.0"
    redis: "1.0.0"
    qdrant: "1.0.0"
    neo4j: "1.0.0"

  kubernetes:
    aiworkload_crd: "v1alpha1"
    generationjob_crd: "v1alpha1"

  api:
    control_plane: "1.0.0"
    comfyui_bridge: "1.0.0"
    quality_service: "1.0.0"
    agent_service: "1.0.0"

  metrics:
    prometheus: "1.0.0"

  events:
    hydra_events: "1.0.0"

# Migration tracking
migrations:
  - version: "1.0.0"
    date: "2025-12-12"
    description: "Initial schema release"
    changes:
      - "Created core domain models"
      - "Defined PostgreSQL schema"
      - "Set up Redis key patterns"
      - "Configured Qdrant collections"
      - "Established Neo4j graph schema"
```

---

*Schema Architecture Version: 1.0.0*
*Generated: December 12, 2025*
*Author: Hydra Autonomous Steward*
