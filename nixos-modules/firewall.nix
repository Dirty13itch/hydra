# NixOS Firewall Configuration for Hydra Cluster
#
# Configures firewall rules for all cluster services.
# Separates rules by node role.
#
# Add to /etc/nixos/configuration.nix:
#   imports = [ ./firewall.nix ];

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.hydra-firewall;

  # Trusted cluster network
  clusterNetwork = "192.168.1.0/24";

  # Tailscale network
  tailscaleNetwork = "100.64.0.0/10";

  # Common ports for all nodes
  commonPorts = {
    tcp = [
      22      # SSH
      9100    # Node Exporter
    ];
    udp = [
      5353    # mDNS
    ];
  };

  # Role-specific ports
  rolePorts = {
    # hydra-ai: Primary inference
    inference-primary = {
      tcp = [
        3000    # Open WebUI
        5000    # TabbyAPI
        9835    # GPU Metrics (nvidia-smi exporter)
      ];
      udp = [];
    };

    # hydra-compute: Secondary inference, image gen
    inference-secondary = {
      tcp = [
        8188    # ComfyUI
        9835    # GPU Metrics
        11434   # Ollama
      ];
      udp = [];
    };

    # hydra-storage: Docker services (managed by Unraid, not NixOS)
    storage = {
      tcp = [];
      udp = [];
    };

    # Development node
    development = {
      tcp = [
        3000    # Dev server
        5000    # Flask/FastAPI
        8000    # Django
        8080    # Generic
      ];
      udp = [];
    };
  };
in
{
  options.services.hydra-firewall = {
    enable = mkEnableOption "Hydra cluster firewall configuration";

    role = mkOption {
      type = types.enum [ "inference-primary" "inference-secondary" "storage" "development" ];
      description = "Node role for firewall configuration";
    };

    trustCluster = mkOption {
      type = types.bool;
      default = true;
      description = "Allow all traffic from cluster network";
    };

    trustTailscale = mkOption {
      type = types.bool;
      default = true;
      description = "Allow all traffic from Tailscale network";
    };

    extraPorts = mkOption {
      type = types.submodule {
        options = {
          tcp = mkOption {
            type = types.listOf types.port;
            default = [];
          };
          udp = mkOption {
            type = types.listOf types.port;
            default = [];
          };
        };
      };
      default = { tcp = []; udp = []; };
      description = "Additional ports to open";
    };

    logDropped = mkOption {
      type = types.bool;
      default = false;
      description = "Log dropped packets (can be noisy)";
    };
  };

  config = mkIf cfg.enable {
    networking.firewall = {
      enable = true;

      # Allow ping
      allowPing = true;

      # Combined TCP ports
      allowedTCPPorts =
        commonPorts.tcp
        ++ rolePorts.${cfg.role}.tcp
        ++ cfg.extraPorts.tcp;

      # Combined UDP ports
      allowedUDPPorts =
        commonPorts.udp
        ++ rolePorts.${cfg.role}.udp
        ++ cfg.extraPorts.udp;

      # Trust cluster and Tailscale networks
      trustedInterfaces = [ "lo" ] ++ optional config.services.tailscale.enable "tailscale0";

      # Extra commands for network-based rules
      extraCommands = ''
        # Trust cluster network
        ${optionalString cfg.trustCluster ''
          iptables -A INPUT -s ${clusterNetwork} -j ACCEPT
          ip6tables -A INPUT -s fe80::/10 -j ACCEPT
        ''}

        # Trust Tailscale
        ${optionalString cfg.trustTailscale ''
          iptables -A INPUT -s ${tailscaleNetwork} -j ACCEPT
        ''}

        # Log dropped packets
        ${optionalString cfg.logDropped ''
          iptables -A INPUT -m limit --limit 5/min -j LOG --log-prefix "iptables-dropped: " --log-level 4
        ''}
      '';

      # Stop commands (cleanup)
      extraStopCommands = ''
        iptables -D INPUT -s ${clusterNetwork} -j ACCEPT 2>/dev/null || true
        iptables -D INPUT -s ${tailscaleNetwork} -j ACCEPT 2>/dev/null || true
      '';
    };

    # Ensure iptables is available
    environment.systemPackages = [ pkgs.iptables ];
  };
}
