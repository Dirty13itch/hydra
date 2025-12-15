# NixOS Ollama Service Module
#
# Configures Ollama for local inference on hydra-compute.
# Used for fast 7B-14B models on 5070 Ti (16GB VRAM).
#
# Add to /etc/nixos/configuration.nix:
#   imports = [ ./ollama.nix ];

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.hydra-ollama;
in
{
  options.services.hydra-ollama = {
    enable = mkEnableOption "Ollama inference server";

    host = mkOption {
      type = types.str;
      default = "0.0.0.0";
      description = "Host address to bind to";
    };

    port = mkOption {
      type = types.port;
      default = 11434;
      description = "Port to listen on";
    };

    modelsDir = mkOption {
      type = types.path;
      default = "/var/lib/ollama/models";
      description = "Directory for model storage";
    };

    gpuLayers = mkOption {
      type = types.nullOr types.int;
      default = null;
      description = "Number of GPU layers (null for auto)";
    };

    gpuDevices = mkOption {
      type = types.str;
      default = "0";
      description = "CUDA visible devices";
    };

    maxLoadedModels = mkOption {
      type = types.int;
      default = 1;
      description = "Maximum number of models to keep loaded";
    };

    extraEnvironment = mkOption {
      type = types.attrsOf types.str;
      default = { };
      description = "Extra environment variables";
    };
  };

  config = mkIf cfg.enable {
    # Use the official NixOS Ollama service if available, otherwise define custom
    services.ollama = {
      enable = true;
      host = cfg.host;
      port = cfg.port;

      # Environment configuration
      environmentVariables = {
        OLLAMA_HOST = "${cfg.host}:${toString cfg.port}";
        OLLAMA_MODELS = cfg.modelsDir;
        CUDA_VISIBLE_DEVICES = cfg.gpuDevices;
        OLLAMA_NUM_PARALLEL = "2";
        OLLAMA_MAX_LOADED_MODELS = toString cfg.maxLoadedModels;
        # Flash attention for better performance
        OLLAMA_FLASH_ATTENTION = "1";
      } // cfg.extraEnvironment;

      # Enable GPU acceleration
      acceleration = "cuda";
    };

    # Ensure models directory exists
    systemd.tmpfiles.rules = [
      "d ${cfg.modelsDir} 0755 ollama ollama -"
    ];

    # Firewall
    networking.firewall.allowedTCPPorts = [ cfg.port ];

    # GPU access
    hardware.graphics.enable = true;

    # CUDA support
    environment.systemPackages = with pkgs; [
      cudaPackages.cudatoolkit
      cudaPackages.cudnn
    ];
  };
}
