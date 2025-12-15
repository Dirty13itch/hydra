# NixOS module for GPU power management
#
# Ensures GPU power limits are set at boot and maintained.
# Critical for staying within UPS power budget.

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.hydra-gpu-power;

  # Power limit script
  setPowerLimits = pkgs.writeShellScriptBin "set-gpu-power-limits" ''
    #!/bin/bash
    set -e

    # Wait for nvidia driver to be ready
    sleep 5

    ${concatMapStringsSep "\n" (gpu: ''
      echo "Setting GPU ${toString gpu.index} power limit to ${toString gpu.powerLimit}W"
      ${pkgs.linuxPackages.nvidia_x11.bin}/bin/nvidia-smi \
        -i ${toString gpu.index} \
        -pl ${toString gpu.powerLimit} || true
    '') cfg.gpus}

    echo "GPU power limits configured"
  '';

  # Monitoring script
  monitorPower = pkgs.writeShellScriptBin "monitor-gpu-power" ''
    #!/bin/bash

    while true; do
      # Get current power draw
      power=$(${pkgs.linuxPackages.nvidia_x11.bin}/bin/nvidia-smi \
        --query-gpu=power.draw \
        --format=csv,noheader,nounits | \
        awk '{sum += $1} END {print sum}')

      # Alert if over threshold
      if (( $(echo "$power > ${toString cfg.alertThreshold}" | ${pkgs.bc}/bin/bc -l) )); then
        echo "WARNING: GPU power draw ($power W) exceeds threshold (${toString cfg.alertThreshold} W)"
        # Could add notification here (Discord webhook, etc.)
      fi

      sleep ${toString cfg.monitorInterval}
    done
  '';
in
{
  options.services.hydra-gpu-power = {
    enable = mkEnableOption "Hydra GPU power management";

    gpus = mkOption {
      type = types.listOf (types.submodule {
        options = {
          index = mkOption {
            type = types.int;
            description = "GPU index (0, 1, etc.)";
          };
          powerLimit = mkOption {
            type = types.int;
            description = "Power limit in watts";
          };
          name = mkOption {
            type = types.str;
            default = "";
            description = "GPU name for reference";
          };
        };
      });
      default = [];
      example = [
        { index = 0; powerLimit = 450; name = "RTX 5090"; }
        { index = 1; powerLimit = 300; name = "RTX 4090"; }
      ];
      description = "List of GPUs with their power limits";
    };

    alertThreshold = mkOption {
      type = types.int;
      default = 700;
      description = "Total GPU power threshold for alerts (watts)";
    };

    monitorInterval = mkOption {
      type = types.int;
      default = 60;
      description = "Power monitoring interval in seconds";
    };

    enableMonitoring = mkOption {
      type = types.bool;
      default = true;
      description = "Enable continuous power monitoring";
    };
  };

  config = mkIf cfg.enable {
    # Set power limits at boot
    systemd.services.gpu-power-limits = {
      description = "Set GPU Power Limits";
      wantedBy = [ "multi-user.target" ];
      after = [ "nvidia-persistenced.service" ];
      requires = [ "nvidia-persistenced.service" ];

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        ExecStart = "${setPowerLimits}/bin/set-gpu-power-limits";
      };
    };

    # Continuous power monitoring (optional)
    systemd.services.gpu-power-monitor = mkIf cfg.enableMonitoring {
      description = "GPU Power Monitor";
      wantedBy = [ "multi-user.target" ];
      after = [ "gpu-power-limits.service" ];

      serviceConfig = {
        Type = "simple";
        ExecStart = "${monitorPower}/bin/monitor-gpu-power";
        Restart = "always";
        RestartSec = 10;
      };
    };

    # Reset power limits after resume from suspend
    powerManagement.resumeCommands = ''
      ${setPowerLimits}/bin/set-gpu-power-limits
    '';

    # Prometheus metrics for GPU power (optional)
    services.prometheus.exporters.nvidia-gpu = mkIf config.services.prometheus.exporters.nvidia-gpu.enable {
      enable = true;
    };
  };
}
