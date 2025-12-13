# Hydra Cluster - Kubernetes on NixOS Architecture

## Executive Summary

This document outlines the architecture for deploying Kubernetes (K3s) on top of NixOS for the Hydra cluster, enabling proper orchestration of heterogeneous GPU workloads across the cluster.

**Key Decision: K3s over MicroK8s**
- K3s is the preferred choice for NixOS (MicroK8s requires snap which isn't native to NixOS)
- K3s is lightweight (~100MB binary), production-ready, and CNCF certified
- Native NixOS module support via `services.k3s`
- Better for heterogeneous hardware and bare metal deployments

---

## Part 1: Current State vs Target State

### Current Architecture (Docker-based)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          hydra-storage (Unraid)                          │
│                          192.168.1.244                                   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    60+ Docker Containers                          │   │
│  │  PostgreSQL │ Redis │ Qdrant │ n8n │ Prometheus │ etc.           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Storage: NFS exports to compute nodes                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
┌───────────────────▼───────────────┐ ┌────────────▼────────────────────┐
│       hydra-ai (NixOS)            │ │     hydra-compute (NixOS)       │
│       192.168.1.250               │ │     192.168.1.203               │
│                                   │ │                                 │
│  RTX 5090 (32GB) + RTX 4090 (24GB)│ │  RTX 5070 Ti (16GB) x2          │
│                                   │ │  (32GB total - homogeneous)     │
│  ┌─────────────────────────────┐  │ │  ┌─────────────────────────┐    │
│  │ TabbyAPI (systemd service)  │  │ │  │ ComfyUI (Docker)        │    │
│  │ Open WebUI (Docker)         │  │ │  │ Ollama (NixOS service)  │    │
│  └─────────────────────────────┘  │ │  │ Kohya (Docker)          │    │
│                                   │ │  └─────────────────────────┘    │
└───────────────────────────────────┘ └─────────────────────────────────┘
```

**Problems with Current Architecture:**
1. No unified orchestration across nodes
2. Manual GPU resource allocation
3. No automatic failover/rescheduling
4. No job queuing system
5. Workloads can't span multiple nodes
6. No declarative infrastructure

### Target Architecture (K3s Kubernetes)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        K3s Kubernetes Cluster                            │
│                        (Declarative NixOS Configuration)                 │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       CONTROL PLANE (hydra-ai)                           │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ K3s Server │ etcd │ API Server │ Controller Manager │ Scheduler  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Node Labels:                                                            │
│    - gpu.nvidia.com/class=5090                                           │
│    - gpu.nvidia.com/class=4090                                           │
│    - node-role.kubernetes.io/control-plane=true                          │
│    - hydra.io/vram-total=56                                              │
│    - hydra.io/workload=inference                                         │
│                                                                          │
│  GPU Resources:                                                          │
│    - nvidia.com/gpu: 2 (RTX 5090 + RTX 4090)                            │
│    - nvidia.com/gpu-5090: 1                                              │
│    - nvidia.com/gpu-4090: 1                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                              K3s Agent
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                       WORKER NODE (hydra-compute)                        │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │            K3s Agent │ kubelet │ containerd │ nvidia-runtime      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Node Labels:                                                            │
│    - gpu.nvidia.com/class=5070ti                                         │
│    - hydra.io/vram-total=32                                              │
│    - hydra.io/homogeneous=true                                           │
│    - hydra.io/workload=generation                                        │
│    - hydra.io/workload=training                                          │
│                                                                          │
│  GPU Resources:                                                          │
│    - nvidia.com/gpu: 2 (RTX 5070 Ti x2)                                 │
│    - nvidia.com/gpu-5070ti: 2                                            │
│    - hydra.io/gpu-pool=generation                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                              NFS Storage
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                    STORAGE NODE (hydra-storage)                          │
│                    (Remains Unraid - Not in K3s cluster)                 │
│                                                                          │
│  Services that stay on Unraid:                                           │
│    - PostgreSQL (data persistence)                                       │
│    - Redis, Qdrant, Neo4j (databases)                                    │
│    - NFS Server (storage backend)                                        │
│    - Prometheus/Grafana (monitoring)                                     │
│    - Content acquisition stack (*arr)                                    │
│                                                                          │
│  Why not K3s on Unraid:                                                  │
│    - Unraid is optimized for storage, not compute                        │
│    - Complex Docker environment already stable                           │
│    - No GPU workloads needed on storage node                             │
│    - Database persistence better handled natively                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: NixOS K3s Configuration

### 2.1 K3s Server Node (hydra-ai)

```nix
# /etc/nixos/k3s-server.nix
{ config, pkgs, lib, ... }:

let
  # K3s cluster token - generate with: openssl rand -hex 32
  k3sToken = "YOUR_CLUSTER_TOKEN_HERE";  # Move to agenix/sops in production
in
{
  # ==========================================================================
  # K3s Server Configuration
  # ==========================================================================

  services.k3s = {
    enable = true;
    role = "server";

    # Cluster configuration
    token = k3sToken;
    clusterInit = true;  # Initialize new cluster (first server only)

    # Server-specific flags
    extraFlags = toString [
      "--disable=traefik"              # We'll use our own ingress
      "--disable=servicelb"            # Use MetalLB instead
      "--flannel-backend=host-gw"      # Better performance on local network
      "--write-kubeconfig-mode=0644"   # Allow non-root kubeconfig access
      "--kube-apiserver-arg=allow-privileged=true"  # Required for GPU pods
      "--kubelet-arg=max-pods=110"     # Increase max pods
    ];

    # Auto-deploy manifests (AddOns)
    manifests = {
      # NVIDIA RuntimeClass
      nvidia-runtime-class = {
        apiVersion = "node.k8s.io/v1";
        kind = "RuntimeClass";
        metadata.name = "nvidia";
        handler = "nvidia";
      };

      # GPU Node Labels (applied via DaemonSet)
      gpu-labels = {
        apiVersion = "apps/v1";
        kind = "DaemonSet";
        metadata = {
          name = "gpu-labeler";
          namespace = "kube-system";
        };
        spec = {
          selector.matchLabels.name = "gpu-labeler";
          template = {
            metadata.labels.name = "gpu-labeler";
            spec = {
              hostNetwork = true;
              containers = [{
                name = "labeler";
                image = "busybox:latest";
                command = ["sh" "-c" "sleep infinity"];
              }];
              tolerations = [{
                key = "nvidia.com/gpu";
                operator = "Exists";
                effect = "NoSchedule";
              }];
            };
          };
        };
      };
    };
  };

  # ==========================================================================
  # Containerd with NVIDIA Runtime
  # ==========================================================================

  virtualisation.containerd = {
    enable = true;
    settings = {
      version = 2;
      plugins = {
        "io.containerd.grpc.v1.cri" = {
          enable_cdi = true;
          cdi_spec_dirs = ["/etc/cdi" "/var/run/cdi"];
          containerd = {
            default_runtime_name = "nvidia";
            runtimes = {
              nvidia = {
                privileged_without_host_devices = false;
                runtime_type = "io.containerd.runc.v2";
                options = {
                  BinaryName = "${pkgs.nvidia-container-toolkit}/bin/nvidia-container-runtime";
                };
              };
              runc = {
                runtime_type = "io.containerd.runc.v2";
              };
            };
          };
        };
      };
    };
  };

  # ==========================================================================
  # Firewall Rules for K3s
  # ==========================================================================

  networking.firewall.allowedTCPPorts = [
    6443   # K3s API server
    2379   # etcd client
    2380   # etcd peer
    10250  # Kubelet API
    10251  # kube-scheduler
    10252  # kube-controller-manager
    8472   # Flannel VXLAN (if using vxlan backend)
  ];

  networking.firewall.allowedUDPPorts = [
    8472   # Flannel VXLAN
  ];

  # ==========================================================================
  # NVIDIA Container Toolkit (CDI mode)
  # ==========================================================================

  hardware.nvidia-container-toolkit = {
    enable = true;
    mount-nvidia-executables = true;
  };

  # Generate CDI spec for containerd
  systemd.services.nvidia-cdi-generator = {
    description = "Generate NVIDIA CDI specification";
    after = [ "nvidia-persistenced.service" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.nvidia-container-toolkit}/bin/nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml";
    };
  };

  # ==========================================================================
  # kubectl and helm for management
  # ==========================================================================

  environment.systemPackages = with pkgs; [
    kubectl
    kubernetes-helm
    k9s        # Terminal UI for Kubernetes
    stern      # Multi-pod log tailing
  ];

  # Add kubeconfig to environment
  environment.variables.KUBECONFIG = "/etc/rancher/k3s/k3s.yaml";
}
```

### 2.2 K3s Agent Node (hydra-compute)

```nix
# /etc/nixos/k3s-agent.nix
{ config, pkgs, lib, ... }:

let
  k3sToken = "YOUR_CLUSTER_TOKEN_HERE";  # Same token as server
  k3sServerAddr = "https://192.168.1.250:6443";
in
{
  # ==========================================================================
  # K3s Agent Configuration
  # ==========================================================================

  services.k3s = {
    enable = true;
    role = "agent";

    # Connect to server
    serverAddr = k3sServerAddr;
    token = k3sToken;

    # Agent-specific flags
    extraFlags = toString [
      "--kubelet-arg=max-pods=110"
      "--node-label=hydra.io/workload=generation"
      "--node-label=hydra.io/workload=training"
      "--node-label=hydra.io/vram-total=28"
    ];
  };

  # ==========================================================================
  # Containerd with NVIDIA Runtime (same as server)
  # ==========================================================================

  virtualisation.containerd = {
    enable = true;
    settings = {
      version = 2;
      plugins = {
        "io.containerd.grpc.v1.cri" = {
          enable_cdi = true;
          cdi_spec_dirs = ["/etc/cdi" "/var/run/cdi"];
          containerd = {
            default_runtime_name = "nvidia";
            runtimes = {
              nvidia = {
                privileged_without_host_devices = false;
                runtime_type = "io.containerd.runc.v2";
                options = {
                  BinaryName = "${pkgs.nvidia-container-toolkit}/bin/nvidia-container-runtime";
                };
              };
              runc = {
                runtime_type = "io.containerd.runc.v2";
              };
            };
          };
        };
      };
    };
  };

  # ==========================================================================
  # Firewall Rules for K3s Agent
  # ==========================================================================

  networking.firewall.allowedTCPPorts = [
    10250  # Kubelet API
    8472   # Flannel VXLAN
  ];

  networking.firewall.allowedUDPPorts = [
    8472   # Flannel VXLAN
  ];

  # ==========================================================================
  # NVIDIA Container Toolkit
  # ==========================================================================

  hardware.nvidia-container-toolkit = {
    enable = true;
    mount-nvidia-executables = true;
  };

  systemd.services.nvidia-cdi-generator = {
    description = "Generate NVIDIA CDI specification";
    after = [ "nvidia-persistenced.service" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.nvidia-container-toolkit}/bin/nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml";
    };
  };

  environment.systemPackages = with pkgs; [
    kubectl
    k9s
  ];
}
```

---

## Part 3: GPU Scheduling Strategy

### 3.1 Node Labels for GPU Types

```yaml
# hydra-ai node labels
apiVersion: v1
kind: Node
metadata:
  name: hydra-ai
  labels:
    # Standard Kubernetes labels
    kubernetes.io/hostname: hydra-ai
    node.kubernetes.io/instance-type: threadripper-7960x

    # GPU capability labels
    nvidia.com/gpu.product: NVIDIA-GeForce-RTX-5090
    nvidia.com/gpu.memory: "32768"
    nvidia.com/gpu.count: "2"

    # Custom Hydra labels
    hydra.io/gpu-class: inference
    hydra.io/vram-total: "56"
    hydra.io/has-5090: "true"
    hydra.io/has-4090: "true"

---
# hydra-compute node labels
apiVersion: v1
kind: Node
metadata:
  name: hydra-compute
  labels:
    kubernetes.io/hostname: hydra-compute
    node.kubernetes.io/instance-type: ryzen-9-9900x

    nvidia.com/gpu.product: NVIDIA-GeForce-RTX-5070-Ti
    nvidia.com/gpu.memory: "16384"
    nvidia.com/gpu.count: "2"

    hydra.io/gpu-class: generation
    hydra.io/vram-total: "32"
    hydra.io/has-5070ti: "true"
    hydra.io/gpu-count: "2"
    hydra.io/homogeneous: "true"
```

### 3.2 Pod Scheduling Examples

#### Schedule 70B Model to RTX 5090 (largest VRAM)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: tabbyapi-70b
spec:
  runtimeClassName: nvidia
  nodeSelector:
    hydra.io/has-5090: "true"
  containers:
    - name: tabbyapi
      image: ghcr.io/theroyallab/tabbyapi:latest
      resources:
        limits:
          nvidia.com/gpu: 2  # Use both GPUs on hydra-ai
      volumeMounts:
        - name: models
          mountPath: /models
  volumes:
    - name: models
      nfs:
        server: 192.168.1.244
        path: /mnt/user/models
```

#### Schedule ComfyUI to RTX 5070 Ti

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: comfyui
spec:
  replicas: 1
  selector:
    matchLabels:
      app: comfyui
  template:
    metadata:
      labels:
        app: comfyui
    spec:
      runtimeClassName: nvidia
      nodeSelector:
        hydra.io/has-5070ti: "true"
      containers:
        - name: comfyui
          image: ghcr.io/ai-dock/comfyui:latest
          ports:
            - containerPort: 8188
          resources:
            limits:
              nvidia.com/gpu: 1
          volumeMounts:
            - name: models
              mountPath: /opt/ComfyUI/models
            - name: output
              mountPath: /opt/ComfyUI/output
      volumes:
        - name: models
          nfs:
            server: 192.168.1.244
            path: /mnt/user/models/diffusion
        - name: output
          nfs:
            server: 192.168.1.244
            path: /mnt/user/hydra_shared/comfyui_output
```

#### Schedule LoRA Training to RTX 5070 Ti (with GPU affinity)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: lora-training-emilie
spec:
  template:
    spec:
      runtimeClassName: nvidia
      restartPolicy: Never
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: hydra.io/has-5070ti
                    operator: In
                    values:
                      - "true"
      containers:
        - name: kohya
          image: kohya-sdxl:latest
          command: ["python", "sdxl_train_network.py"]
          args:
            - "--pretrained_model=/models/realvis-xl-v5.0.safetensors"
            - "--train_data_dir=/training/emilie"
            - "--output_dir=/output"
          resources:
            limits:
              nvidia.com/gpu: 1
              memory: "32Gi"
            requests:
              nvidia.com/gpu: 1
              memory: "16Gi"
```

#### Schedule Voice Cloning to hydra-compute (any GPU)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gpt-sovits
spec:
  replicas: 1
  selector:
    matchLabels:
      app: gpt-sovits
  template:
    metadata:
      labels:
        app: gpt-sovits
    spec:
      runtimeClassName: nvidia
      nodeSelector:
        kubernetes.io/hostname: hydra-compute
      containers:
        - name: gpt-sovits
          image: breakstring/gpt-sovits:latest
          ports:
            - containerPort: 9874
          resources:
            limits:
              nvidia.com/gpu: 1  # Any 5070 Ti on hydra-compute
              memory: "16Gi"
```

**Note:** With homogeneous dual 5070 Ti on hydra-compute, no GPU affinity needed - scheduler picks any available GPU.

### 3.3 GPU Resource Quotas

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: gpu-quota
  namespace: ai-workloads
spec:
  hard:
    requests.nvidia.com/gpu: "4"   # Total GPUs in cluster
    limits.nvidia.com/gpu: "4"
    requests.memory: "128Gi"
    limits.memory: "256Gi"
```

---

## Part 4: Workload Distribution Strategy

### 4.1 GPU Assignment Matrix

| Workload | GPU | VRAM Required | Node | Priority |
|----------|-----|---------------|------|----------|
| TabbyAPI 70B | RTX 5090 + 4090 | 48GB | hydra-ai | Critical |
| ComfyUI SDXL | RTX 5070 Ti | 10GB | hydra-compute | High |
| LoRA Training | RTX 5070 Ti | 14GB | hydra-compute | Medium |
| GPT-SoVITS | RTX 5070 Ti | 8GB | hydra-compute | Medium |
| Video Gen (Mochi) | RTX 4090 | 18GB | hydra-ai | Low |
| Ollama (small models) | RTX 5070 Ti | 8GB | hydra-compute | Low |

### 4.2 Priority Classes

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: inference-critical
value: 1000000
globalDefault: false
description: "Critical inference workloads (TabbyAPI)"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: generation-high
value: 100000
globalDefault: false
description: "Image generation workloads"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: training-medium
value: 10000
globalDefault: false
description: "LoRA training jobs"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: batch-low
value: 1000
globalDefault: true
description: "Batch processing and background tasks"
```

### 4.3 Kueue for Job Queuing (Optional)

```yaml
# Kueue ClusterQueue for AI workloads
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: ai-workloads
spec:
  namespaceSelector: {}
  resourceGroups:
    - coveredResources: ["cpu", "memory", "nvidia.com/gpu"]
      flavors:
        - name: inference-flavor
          resources:
            - name: nvidia.com/gpu
              nominalQuota: 2
            - name: memory
              nominalQuota: 64Gi
        - name: generation-flavor
          resources:
            - name: nvidia.com/gpu
              nominalQuota: 2
            - name: memory
              nominalQuota: 32Gi
```

---

## Part 5: Migration Strategy

### Phase 1: Infrastructure Setup (Day 1)

1. **Generate cluster token:**
```bash
openssl rand -hex 32 > /etc/k3s-token
```

2. **Update NixOS configurations:**
```bash
# On hydra-ai
sudo nano /etc/nixos/configuration.nix
# Add: imports = [ ./k3s-server.nix ];

# On hydra-compute
sudo nano /etc/nixos/configuration.nix
# Add: imports = [ ./k3s-agent.nix ];
```

3. **Apply configurations:**
```bash
# On hydra-ai first (server)
sudo nixos-rebuild switch

# Then on hydra-compute (agent)
sudo nixos-rebuild switch
```

4. **Verify cluster:**
```bash
kubectl get nodes
# Should show both nodes as Ready
```

### Phase 2: GPU Operator Setup (Day 1)

```bash
# Install NVIDIA GPU Operator via Helm
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

helm install nvidia-gpu-operator nvidia/gpu-operator \
  --namespace nvidia-gpu-operator \
  --create-namespace \
  --set operator.defaultRuntime=containerd \
  --set toolkit.env[0].name=CONTAINERD_CONFIG \
  --set toolkit.env[0].value=/var/lib/rancher/k3s/agent/etc/containerd/config.toml \
  --set toolkit.env[1].name=CONTAINERD_SOCKET \
  --set toolkit.env[1].value=/run/k3s/containerd/containerd.sock \
  --set driver.enabled=false  # Drivers already installed via NixOS
```

### Phase 3: Migrate Workloads (Days 2-3)

**Order of migration (lowest risk first):**

1. **Ollama** (already NixOS service, simple containerization)
2. **ComfyUI** (already Docker, convert to K8s Deployment)
3. **TabbyAPI** (convert systemd to K8s Deployment)
4. **New workloads** (GPT-SoVITS, Mochi, etc.)

**Keep on Unraid (don't migrate):**
- All databases (PostgreSQL, Redis, Qdrant, Neo4j)
- Monitoring stack (Prometheus, Grafana, Loki)
- Content acquisition (*arr stack)
- n8n (workflows reference Unraid services)

### Phase 4: Configure Storage (Day 2)

```yaml
# NFS StorageClass
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs-models
provisioner: nfs.csi.k8s.io
parameters:
  server: 192.168.1.244
  share: /mnt/user/models
  mountPermissions: "0755"
mountOptions:
  - nconnect=8
  - rsize=1048576
  - wsize=1048576
  - hard
  - noatime
---
# PersistentVolume for models
apiVersion: v1
kind: PersistentVolume
metadata:
  name: models-pv
spec:
  capacity:
    storage: 2Ti
  accessModes:
    - ReadOnlyMany
  nfs:
    server: 192.168.1.244
    path: /mnt/user/models
  persistentVolumeReclaimPolicy: Retain
  storageClassName: nfs-models
```

### Phase 5: Deploy Services (Days 3-5)

```yaml
# Example: TabbyAPI Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tabbyapi
  namespace: ai-inference
spec:
  replicas: 1
  strategy:
    type: Recreate  # GPU workloads need Recreate, not RollingUpdate
  selector:
    matchLabels:
      app: tabbyapi
  template:
    metadata:
      labels:
        app: tabbyapi
    spec:
      runtimeClassName: nvidia
      priorityClassName: inference-critical
      nodeSelector:
        hydra.io/has-5090: "true"
      containers:
        - name: tabbyapi
          image: ghcr.io/theroyallab/tabbyapi:latest
          ports:
            - containerPort: 5000
          resources:
            limits:
              nvidia.com/gpu: 2
              memory: 64Gi
            requests:
              nvidia.com/gpu: 2
              memory: 32Gi
          volumeMounts:
            - name: models
              mountPath: /app/models
            - name: config
              mountPath: /app/config.yml
              subPath: config.yml
          env:
            - name: CUDA_DEVICE_ORDER
              value: "PCI_BUS_ID"
      volumes:
        - name: models
          persistentVolumeClaim:
            claimName: models-pvc
        - name: config
          configMap:
            name: tabbyapi-config
---
apiVersion: v1
kind: Service
metadata:
  name: tabbyapi
  namespace: ai-inference
spec:
  type: ClusterIP
  ports:
    - port: 5000
      targetPort: 5000
  selector:
    app: tabbyapi
```

---

## Part 6: Benefits of Kubernetes

### 6.1 Immediate Benefits

| Feature | Docker | Kubernetes | Improvement |
|---------|--------|------------|-------------|
| GPU scheduling | Manual | Automatic | No manual allocation |
| Failover | None | Automatic | Workloads restart on failure |
| Scaling | Manual | HPA/VPA | Auto-scale on demand |
| Resource limits | Per-container | Cluster-wide | Better utilization |
| Job queuing | None | Kueue/native Jobs | Queue training jobs |
| Declarative | docker-compose | YAML manifests | GitOps ready |

### 6.2 Long-term Benefits

1. **Multi-node inference**: Run 70B+ models across both nodes with tensor parallelism
2. **Batch job management**: Queue LoRA training jobs, run overnight
3. **Auto-scaling to zero**: Use KEDA to scale down idle services
4. **Better monitoring**: Native Prometheus metrics via kube-state-metrics
5. **GitOps ready**: Store all manifests in Git, deploy via Flux/ArgoCD
6. **Easier upgrades**: Rolling updates for services

### 6.3 Potential Challenges

| Challenge | Mitigation |
|-----------|------------|
| K3s + NVIDIA on NixOS complexity | Follow tested configurations |
| Learning curve | Use k9s for visual management |
| Database persistence | Keep databases on Unraid |
| Network complexity | Use simple host-gw networking |
| Debugging GPU issues | Enable verbose logging |

---

## Part 7: Commands Reference

### Cluster Management

```bash
# Check cluster status
kubectl get nodes -o wide

# View GPU resources
kubectl describe nodes | grep -A 10 nvidia

# Check all pods
kubectl get pods -A

# View GPU allocation
kubectl get pods -A -o custom-columns=\
"NAME:.metadata.name,NODE:.spec.nodeName,GPU:.spec.containers[*].resources.limits.nvidia\.com/gpu"

# View logs
kubectl logs -f deployment/tabbyapi -n ai-inference

# Interactive shell
kubectl exec -it deployment/comfyui -- bash

# Port forward for local access
kubectl port-forward svc/tabbyapi 5000:5000 -n ai-inference
```

### GPU Debugging

```bash
# Check GPU status on node
kubectl debug node/hydra-ai -it --image=nvidia/cuda:12.4.0-base-ubuntu22.04 -- nvidia-smi

# View device plugin logs
kubectl logs -n kube-system -l app=nvidia-device-plugin-daemonset

# Check CDI specs
kubectl exec -it -n nvidia-gpu-operator daemonset/nvidia-container-toolkit-daemonset -- \
  cat /etc/cdi/nvidia.yaml
```

### NixOS Rollback

```bash
# If K3s breaks things, rollback NixOS
sudo nixos-rebuild switch --rollback

# List generations
sudo nix-env --list-generations -p /nix/var/nix/profiles/system
```

---

## Part 8: Decision Matrix

### Should You Migrate to K3s?

| Factor | Weight | Current (Docker) | Target (K3s) | Decision |
|--------|--------|------------------|--------------|----------|
| Workload complexity | High | 4/10 | 8/10 | K3s better |
| GPU scheduling | High | 2/10 | 9/10 | K3s better |
| Maintenance burden | Medium | 6/10 | 5/10 | Similar |
| Learning curve | Medium | 8/10 | 4/10 | Docker easier |
| Future scalability | High | 3/10 | 9/10 | K3s better |
| Debugging ease | Medium | 7/10 | 5/10 | Docker easier |

**Recommendation**: Migrate to K3s for the GPU nodes (hydra-ai, hydra-compute). Keep Unraid with Docker for storage/databases.

### Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| 1 | Day 1 | K3s infrastructure setup |
| 2 | Day 1 | GPU operator installation |
| 3 | Days 2-3 | Migrate compute workloads |
| 4 | Days 4-5 | Testing and optimization |
| 5 | Week 2 | Advanced features (Kueue, auto-scaling) |

---

## Conclusion

Kubernetes (K3s) on NixOS provides a robust foundation for the Hydra cluster's GPU workload management. The key benefits are:

1. **Declarative configuration** - Everything in NixOS config files
2. **Automatic GPU scheduling** - No manual allocation needed
3. **Job queuing** - Queue overnight training/generation jobs
4. **Proper resource limits** - Prevent GPU memory contention
5. **Native NixOS integration** - Leverage NixOS's reproducibility

The recommended approach is a phased migration:
- Phase 1: Set up K3s on NixOS nodes
- Phase 2: Install GPU operator
- Phase 3: Migrate inference/generation workloads
- Phase 4: Keep databases on Unraid
- Phase 5: Enable advanced features

This architecture positions the Hydra cluster for future growth, including multi-node inference, automated batch processing, and GitOps-style deployment.

---

**Sources:**
- [K3s NixOS Wiki](https://nixos.wiki/wiki/K3s)
- [NVIDIA GPU on NixOS K8s](https://fangpenlin.com/posts/2025/03/01/nvidia-gpu-on-bare-metal-nixos-k8s-explained/)
- [K3s vs MicroK8s](https://www.wallarm.com/cloud-native-products-101/k3s-vs-microk8s-lightweight-kubernetes-distributions)
- [Kubernetes GPU Scheduling](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
- [NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/getting-started.html)
- [NVIDIA KAI Scheduler](https://www.vcluster.com/blog/gpu-scheduling-with-nvidia-kai-and-vcluster)
- [Kueue for AI Workloads](https://www.coreweave.com/blog/kueue-a-kubernetes-native-system-for-ai-training-workloads)

---

*Document Version: 1.0*
*Generated: December 12, 2025*
*Author: Hydra Autonomous Steward*
