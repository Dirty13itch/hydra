# Dual Ollama Configuration for hydra-compute
#
# This module configures two Ollama instances, one per GPU (2x RTX 5070 Ti),
# with Nginx load balancing for optimal throughput.
#
# Based on research: For 7B models, separate instances beat tensor parallelism
# due to PCIe communication overhead.
#
# Deploy:
#   1. Copy to hydra-compute: scp ollama-dual.nix typhon@192.168.1.203:/etc/nixos/
#   2. Add to imports in configuration.nix: imports = [ ./ollama-dual.nix ];
#   3. Rebuild: sudo nixos-rebuild switch
#
# Endpoints:
#   - http://192.168.1.203:11400 - Load balanced (use this)
#   - http://192.168.1.203:11434 - GPU 0 direct
#   - http://192.168.1.203:11435 - GPU 1 direct

{ config, lib, pkgs, ... }:

with lib;

let
  ollamaPackage = pkgs.ollama;
  modelsDir = "/var/lib/ollama/models";
in
{
  # Disable the default Ollama service if enabled
  services.ollama.enable = mkForce false;

  # Create models directory
  systemd.tmpfiles.rules = [
    "d ${modelsDir} 0755 root root -"
  ];

  # ==========================================================================
  # OLLAMA INSTANCE 1 - GPU 0
  # ==========================================================================
  systemd.services.ollama-gpu0 = {
    description = "Ollama LLM Server - GPU 0 (RTX 5070 Ti #0)";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" ];

    environment = {
      HOME = "/var/lib/ollama";
      OLLAMA_HOST = "0.0.0.0:11434";
      OLLAMA_MODELS = modelsDir;
      CUDA_VISIBLE_DEVICES = "0";
      OLLAMA_FLASH_ATTENTION = "1";
      OLLAMA_NUM_PARALLEL = "2";
      OLLAMA_MAX_LOADED_MODELS = "2";
      OLLAMA_KEEP_ALIVE = "10m";
    };

    serviceConfig = {
      Type = "simple";
      ExecStart = "${ollamaPackage}/bin/ollama serve";
      Restart = "always";
      RestartSec = "5";

      # Security hardening
      NoNewPrivileges = true;
      ProtectSystem = "strict";
      ProtectHome = true;
      ReadWritePaths = [ modelsDir "/var/lib/ollama" ];

      # Resource limits
      MemoryMax = "32G";
      CPUQuota = "400%";  # 4 cores max
    };
  };

  # ==========================================================================
  # OLLAMA INSTANCE 2 - GPU 1
  # ==========================================================================
  systemd.services.ollama-gpu1 = {
    description = "Ollama LLM Server - GPU 1 (RTX 5070 Ti #1)";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" ];

    environment = {
      HOME = "/var/lib/ollama-gpu1";
      OLLAMA_HOST = "0.0.0.0:11435";
      OLLAMA_MODELS = modelsDir;  # Share models directory
      CUDA_VISIBLE_DEVICES = "1";
      OLLAMA_FLASH_ATTENTION = "1";
      OLLAMA_NUM_PARALLEL = "2";
      OLLAMA_MAX_LOADED_MODELS = "2";
      OLLAMA_KEEP_ALIVE = "10m";
    };

    serviceConfig = {
      Type = "simple";
      ExecStart = "${ollamaPackage}/bin/ollama serve";
      Restart = "always";
      RestartSec = "5";

      # Security hardening
      NoNewPrivileges = true;
      ProtectSystem = "strict";
      ProtectHome = true;
      ReadWritePaths = [ modelsDir "/var/lib/ollama-gpu1" ];

      # Resource limits
      MemoryMax = "32G";
      CPUQuota = "400%";  # 4 cores max
    };
  };

  # Create home directory for GPU 1 instance
  systemd.tmpfiles.rules = [
    "d /var/lib/ollama-gpu1 0755 root root -"
  ];

  # ==========================================================================
  # NGINX LOAD BALANCER
  # ==========================================================================
  services.nginx = {
    enable = true;

    # Upstream configuration for load balancing
    upstreams = {
      ollama_backend = {
        servers = {
          "127.0.0.1:11434" = { weight = 1; };
          "127.0.0.1:11435" = { weight = 1; };
        };
        extraConfig = ''
          least_conn;
          keepalive 32;
        '';
      };
    };

    # Virtual host for load balanced endpoint
    virtualHosts = {
      "ollama-lb" = {
        listen = [
          { addr = "0.0.0.0"; port = 11400; }
        ];

        locations = {
          "/" = {
            proxyPass = "http://ollama_backend";
            extraConfig = ''
              proxy_http_version 1.1;
              proxy_set_header Host $host;
              proxy_set_header X-Real-IP $remote_addr;
              proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
              proxy_set_header Connection "";

              # Long timeout for LLM inference
              proxy_read_timeout 300s;
              proxy_connect_timeout 10s;
              proxy_send_timeout 60s;

              # Buffering settings for streaming
              proxy_buffering off;
              proxy_cache off;

              # For streaming responses
              chunked_transfer_encoding on;
            '';
          };

          # Health check endpoint
          "/health" = {
            return = "200 'OK'";
            extraConfig = ''
              add_header Content-Type text/plain;
            '';
          };
        };
      };
    };

    # Global nginx settings
    recommendedProxySettings = true;
    recommendedOptimisation = true;

    appendConfig = ''
      worker_processes auto;
      worker_rlimit_nofile 65535;
    '';

    eventsConfig = ''
      worker_connections 4096;
      use epoll;
      multi_accept on;
    '';
  };

  # ==========================================================================
  # FIREWALL
  # ==========================================================================
  networking.firewall.allowedTCPPorts = [
    11400  # Load balanced endpoint (primary)
    11434  # GPU 0 direct access
    11435  # GPU 1 direct access
  ];

  # ==========================================================================
  # GPU SUPPORT
  # ==========================================================================
  hardware.graphics.enable = true;

  # NVIDIA drivers and CUDA
  hardware.nvidia = {
    package = config.boot.kernelPackages.nvidiaPackages.stable;
    modesetting.enable = true;
    powerManagement.enable = false;
  };

  environment.systemPackages = with pkgs; [
    ollamaPackage
    nvidia-docker
    cudaPackages.cudatoolkit
  ];
}
