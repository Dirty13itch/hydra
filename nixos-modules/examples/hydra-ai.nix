# Example NixOS configuration for hydra-ai
#
# hydra-ai hardware:
# - CPU: AMD Threadripper (or similar high-core)
# - GPUs: RTX 5090 32GB + RTX 4090 24GB
# - RAM: 128GB
# - Role: Primary inference (70B+ models)
#
# Add to /etc/nixos/configuration.nix:
#   imports = [ ./hydra-ai.nix ];

{ config, pkgs, ... }:

{
  imports = [
    ../tabbyapi.nix
    ../gpu-power.nix
    ../network-adguard.nix
    ../firewall.nix
    ../promtail.nix
  ];

  # Hostname
  networking.hostName = "hydra-ai";

  # Network with AdGuard DNS
  services.hydra-network = {
    enable = true;
    adguardIp = "192.168.1.244";
  };

  # Firewall for inference node
  services.hydra-firewall = {
    enable = true;
    role = "inference-primary";
    trustCluster = true;
    trustTailscale = true;
  };

  # TabbyAPI for 70B inference
  services.hydra-tabbyapi = {
    enable = true;
    host = "0.0.0.0";
    port = 5000;
    modelsDir = "/mnt/models/exl2";

    # Model configuration
    modelName = "Llama-3.1-70B-Instruct-exl2-4.0bpw";
    maxSeqLen = 8192;
    cacheSize = 8192;

    # Multi-GPU configuration (5090 + 4090)
    gpuSplit = [ 0.6 0.4 ];  # 60% on 5090, 40% on 4090
    tensorParallel = false;  # TP not yet reliable with heterogeneous GPUs

    # Performance settings
    maxBatchSize = 256;
    chunkSize = 2048;
  };

  # GPU power management
  services.hydra-gpu-power = {
    enable = true;
    gpus = [
      { index = 0; powerLimit = 450; name = "RTX 5090"; }
      { index = 1; powerLimit = 300; name = "RTX 4090"; }
    ];
    alertThreshold = 700;  # Combined power alert
    enableMonitoring = true;
  };

  # Log shipping to Loki
  services.hydra-promtail = {
    enable = true;
    lokiUrl = "http://192.168.1.244:3100";
    scrapeTabbyAPI = true;
  };

  # NFS mounts for shared storage
  fileSystems."/mnt/models" = {
    device = "192.168.1.244:/mnt/user/models";
    fsType = "nfs";
    options = [
      "nfsvers=4"
      "rsize=1048576"
      "wsize=1048576"
      "hard"
      "intr"
      "noatime"
      "_netdev"
      "x-systemd.automount"
      "x-systemd.idle-timeout=600"
    ];
  };

  fileSystems."/mnt/shared" = {
    device = "192.168.1.244:/mnt/user/hydra_shared";
    fsType = "nfs";
    options = [
      "nfsvers=4"
      "rsize=1048576"
      "wsize=1048576"
      "hard"
      "intr"
      "noatime"
      "_netdev"
      "x-systemd.automount"
    ];
  };

  # NVIDIA drivers
  hardware.nvidia = {
    modesetting.enable = true;
    powerManagement.enable = true;
    open = false;
    nvidiaSettings = true;
    package = config.boot.kernelPackages.nvidiaPackages.stable;
  };

  services.xserver.videoDrivers = [ "nvidia" ];
  hardware.graphics.enable = true;

  # NVIDIA persistence daemon
  hardware.nvidia.nvidiaPersistenced = true;

  # Docker for Open WebUI
  virtualisation.docker = {
    enable = true;
    enableNvidia = true;
  };

  # Open WebUI container
  virtualisation.oci-containers.containers.open-webui = {
    image = "ghcr.io/open-webui/open-webui:main";
    ports = [ "3000:8080" ];
    environment = {
      OLLAMA_BASE_URL = "http://192.168.1.203:11434";
      OPENAI_API_BASE_URL = "http://192.168.1.244:4000/v1";
      WEBUI_AUTH = "false";
    };
    volumes = [
      "open-webui-data:/app/backend/data"
    ];
    extraOptions = [
      "--add-host=host.docker.internal:host-gateway"
    ];
  };

  # Essential packages
  environment.systemPackages = with pkgs; [
    cudaPackages.cudatoolkit
    cudaPackages.cudnn
    nvtopPackages.nvidia
    git
    htop
    jq
    wget
    curl
    python311
    python311Packages.pip
    sops
    age
  ];

  # Node exporter for Prometheus
  services.prometheus.exporters.node = {
    enable = true;
    enabledCollectors = [
      "systemd"
      "cpu"
      "meminfo"
      "diskstats"
      "filesystem"
      "loadavg"
      "netdev"
    ];
  };

  # SSH server
  services.openssh = {
    enable = true;
    settings = {
      PermitRootLogin = "no";
      PasswordAuthentication = false;
    };
  };

  # Tailscale VPN
  services.tailscale.enable = true;

  # User configuration
  users.users.typhon = {
    isNormalUser = true;
    extraGroups = [ "wheel" "video" "render" "docker" ];
    openssh.authorizedKeys.keys = [
      # Add your SSH public key here
    ];
  };

  # Passwordless sudo for wheel group
  security.sudo.wheelNeedsPassword = false;

  # System settings
  system.stateVersion = "24.05";
}
