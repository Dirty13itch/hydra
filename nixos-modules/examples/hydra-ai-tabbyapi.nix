# Example NixOS configuration for hydra-ai with TabbyAPI
#
# Add to /etc/nixos/configuration.nix:
#   imports = [ ./hydra-ai-tabbyapi.nix ];
#
# Or add the module to your flake inputs and import it.

{ config, pkgs, ... }:

{
  imports = [
    ../tabbyapi.nix
  ];

  services.tabbyapi = {
    enable = true;

    # Network - bind to all interfaces for cluster access
    host = "0.0.0.0";
    port = 5000;

    # Disable auth for internal network (behind firewall)
    disableAuth = true;

    # Model configuration
    modelDir = "/mnt/models/exl2";

    # Default model to load - adjust based on available VRAM
    # 70B @ 4bpw needs ~40GB, fits on 5090+4090 (56GB total)
    defaultModel = "Llama-3.1-70B-Instruct-exl2-4.0bpw";

    # Context length - balance between capability and VRAM
    maxSeqLen = 8192;

    # GPU configuration for hydra-ai (5090 32GB + 4090 24GB)
    gpuSplitAuto = true;  # Let ExLlamaV2 figure out optimal split

    # KV cache quantization - Q8 is good balance
    cacheMode = "Q8";

    # Power management - critical for UPS budget
    # 5090 default TDP is 575W, we limit to 450W
    gpuPowerLimit = 450;

    # Logging
    logPrompt = false;  # Don't log prompts for privacy
    logGenerationParams = true;

    # Developer options
    cudaMallocBackend = true;

    # Extra environment
    extraEnvironment = {
      CUDA_VISIBLE_DEVICES = "0,1";  # Both GPUs
      PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True";
    };
  };

  # Ensure NFS mount is available before TabbyAPI starts
  systemd.services.tabbyapi = {
    after = [ "mnt-models.mount" ];
    requires = [ "mnt-models.mount" ];
  };

  # NFS mount for models (if not already configured)
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

  # Firewall rules
  networking.firewall = {
    enable = true;
    allowedTCPPorts = [
      5000  # TabbyAPI
      22    # SSH
    ];
  };

  # NVIDIA driver configuration
  hardware.nvidia = {
    modesetting.enable = true;
    powerManagement.enable = true;
    open = false;  # Use proprietary driver for compute
    nvidiaSettings = true;
  };

  services.xserver.videoDrivers = [ "nvidia" ];

  # CUDA support
  hardware.graphics.enable = true;

  # Nvidia container toolkit for optional containerized inference
  hardware.nvidia-container-toolkit.enable = true;
}
