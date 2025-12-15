# NixOS ComfyUI Service Module
#
# Configures ComfyUI for image generation on hydra-compute.
# Runs on RTX 5070 Ti (16GB VRAM).
#
# Add to /etc/nixos/configuration.nix:
#   imports = [ ./comfyui.nix ];

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.hydra-comfyui;

  # Python environment with ComfyUI dependencies
  pythonEnv = pkgs.python311.withPackages (ps: with ps; [
    torch
    torchvision
    torchaudio
    numpy
    pillow
    scipy
    tqdm
    einops
    transformers
    safetensors
    aiohttp
    pyyaml
    requests
    kornia
    spandrel
    soundfile
  ]);
in
{
  options.services.hydra-comfyui = {
    enable = mkEnableOption "ComfyUI image generation server";

    package = mkOption {
      type = types.package;
      default = pkgs.callPackage ./comfyui-package.nix { };
      description = "ComfyUI package";
    };

    host = mkOption {
      type = types.str;
      default = "0.0.0.0";
      description = "Host address to bind to";
    };

    port = mkOption {
      type = types.port;
      default = 8188;
      description = "Port to listen on";
    };

    modelsDir = mkOption {
      type = types.path;
      default = "/mnt/models/diffusion";
      description = "Directory for diffusion models";
    };

    outputDir = mkOption {
      type = types.path;
      default = "/var/lib/comfyui/output";
      description = "Directory for generated images";
    };

    inputDir = mkOption {
      type = types.path;
      default = "/var/lib/comfyui/input";
      description = "Directory for input images";
    };

    tempDir = mkOption {
      type = types.path;
      default = "/var/lib/comfyui/temp";
      description = "Directory for temporary files";
    };

    gpuDevice = mkOption {
      type = types.str;
      default = "cuda:0";
      description = "GPU device to use";
    };

    lowVram = mkOption {
      type = types.bool;
      default = false;
      description = "Enable low VRAM mode";
    };

    highVram = mkOption {
      type = types.bool;
      default = true;
      description = "Enable high VRAM optimizations";
    };

    user = mkOption {
      type = types.str;
      default = "comfyui";
      description = "User to run ComfyUI as";
    };

    group = mkOption {
      type = types.str;
      default = "comfyui";
      description = "Group to run ComfyUI as";
    };

    extraArgs = mkOption {
      type = types.listOf types.str;
      default = [ ];
      description = "Extra command-line arguments";
    };
  };

  config = mkIf cfg.enable {
    # Create user and group
    users.users.${cfg.user} = {
      isSystemUser = true;
      group = cfg.group;
      extraGroups = [ "video" "render" ];
      home = "/var/lib/comfyui";
      description = "ComfyUI service user";
    };

    users.groups.${cfg.group} = { };

    # Ensure directories exist
    systemd.tmpfiles.rules = [
      "d /var/lib/comfyui 0755 ${cfg.user} ${cfg.group} -"
      "d ${cfg.outputDir} 0755 ${cfg.user} ${cfg.group} -"
      "d ${cfg.inputDir} 0755 ${cfg.user} ${cfg.group} -"
      "d ${cfg.tempDir} 0755 ${cfg.user} ${cfg.group} -"
    ];

    # Systemd service
    systemd.services.comfyui = {
      description = "ComfyUI Image Generation Server";
      wantedBy = [ "multi-user.target" ];
      after = [ "network.target" "nvidia-persistenced.service" ];

      environment = {
        HOME = "/var/lib/comfyui";
        COMFYUI_PATH = "/var/lib/comfyui";
        CUDA_VISIBLE_DEVICES = "0";  # Use first GPU
        PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True";
      };

      serviceConfig = {
        Type = "simple";
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = "/var/lib/comfyui";
        StateDirectory = "comfyui";

        ExecStart = let
          args = [
            "--listen" cfg.host
            "--port" (toString cfg.port)
            "--output-directory" cfg.outputDir
            "--input-directory" cfg.inputDir
            "--temp-directory" cfg.tempDir
          ]
          ++ optionals cfg.lowVram [ "--lowvram" ]
          ++ optionals cfg.highVram [ "--highvram" ]
          ++ cfg.extraArgs;
        in "${pythonEnv}/bin/python -u main.py ${concatStringsSep " " args}";

        Restart = "on-failure";
        RestartSec = 10;

        # Security
        NoNewPrivileges = true;
        PrivateTmp = true;

        # GPU access
        SupplementaryGroups = [ "video" "render" ];
        DeviceAllow = [
          "/dev/nvidia0 rw"
          "/dev/nvidiactl rw"
          "/dev/nvidia-uvm rw"
        ];

        # Resource limits
        LimitNOFILE = 65536;
        LimitMEMLOCK = "infinity";
      };
    };

    # Symlink models directory
    systemd.services.comfyui.preStart = ''
      # Link model directories
      mkdir -p /var/lib/comfyui/models
      ln -sfn ${cfg.modelsDir}/checkpoints /var/lib/comfyui/models/checkpoints || true
      ln -sfn ${cfg.modelsDir}/loras /var/lib/comfyui/models/loras || true
      ln -sfn ${cfg.modelsDir}/vae /var/lib/comfyui/models/vae || true
      ln -sfn ${cfg.modelsDir}/controlnet /var/lib/comfyui/models/controlnet || true
      ln -sfn ${cfg.modelsDir}/upscale_models /var/lib/comfyui/models/upscale_models || true
      ln -sfn ${cfg.modelsDir}/embeddings /var/lib/comfyui/models/embeddings || true
      ln -sfn ${cfg.modelsDir}/clip /var/lib/comfyui/models/clip || true
    '';

    # Firewall
    networking.firewall.allowedTCPPorts = [ cfg.port ];
  };
}
