# Example NixOS configuration for hydra-compute
#
# hydra-compute hardware:
# - CPU: AMD Ryzen or Intel (adjust accordingly)
# - GPUs: RTX 5070 Ti 16GB + RTX 3060 12GB
# - RAM: 64GB
# - Role: Secondary inference (Ollama), image generation (ComfyUI)
#
# Add to /etc/nixos/configuration.nix:
#   imports = [ ./hydra-compute.nix ];

{ config, pkgs, ... }:

{
  imports = [
    ../ollama.nix
    ../comfyui.nix
    ../gpu-power.nix
    ../dns-adguard.nix
  ];

  # Hostname
  networking.hostName = "hydra-compute";

  # DNS via AdGuard
  services.hydra-dns = {
    enable = true;
    adguardIp = "192.168.1.244";
  };

  # Ollama for fast inference
  services.hydra-ollama = {
    enable = true;
    host = "0.0.0.0";
    port = 11434;
    modelsDir = "/mnt/models/ollama";
    gpuDevices = "0";  # Use RTX 5070 Ti
    maxLoadedModels = 2;
    extraEnvironment = {
      OLLAMA_KEEP_ALIVE = "24h";  # Keep models loaded
    };
  };

  # ComfyUI for image generation
  services.hydra-comfyui = {
    enable = true;
    host = "0.0.0.0";
    port = 8188;
    modelsDir = "/mnt/models/diffusion";
    highVram = true;  # 5070 Ti has 16GB
    extraArgs = [
      "--preview-method" "auto"
      "--use-pytorch-cross-attention"
    ];
  };

  # GPU power management
  services.hydra-gpu-power = {
    enable = true;
    gpus = [
      { index = 0; powerLimit = 250; name = "RTX 5070 Ti"; }
      { index = 1; powerLimit = 150; name = "RTX 3060"; }
    ];
    alertThreshold = 350;
    enableMonitoring = true;
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

  # CUDA packages
  environment.systemPackages = with pkgs; [
    cudaPackages.cudatoolkit
    cudaPackages.cudnn
    nvtopPackages.nvidia
    git
    htop
    jq
    wget
    curl
  ];

  # Firewall
  networking.firewall = {
    enable = true;
    allowedTCPPorts = [
      22      # SSH
      11434   # Ollama
      8188    # ComfyUI
      9100    # Node exporter
      9835    # GPU metrics
    ];
  };

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

  # Enable sudo without password for wheel group
  security.sudo.wheelNeedsPassword = false;

  # System settings
  system.stateVersion = "24.05";
}
