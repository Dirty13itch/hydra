# NixOS Firewall Configuration - Hydra Cluster Ports
#
# This module configures permanent firewall rules for Hydra services.
# Replaces temporary iptables rules with declarative NixOS config.
#
# Deploy to NixOS nodes:
#   scp firewall-hydra.nix typhon@192.168.1.250:/tmp/
#   ssh typhon@192.168.1.250 "sudo cp /tmp/firewall-hydra.nix /etc/nixos/ && \
#     sudo nixos-rebuild switch"

{ config, pkgs, lib, ... }:

{
  # Firewall configuration
  networking.firewall = {
    enable = true;

    # Allow ICMP (ping) for network diagnostics
    allowPing = true;

    # TCP ports to open
    allowedTCPPorts = [
      # SSH
      22

      # Node Exporter (Prometheus metrics)
      9100

      # Custom nvidia-smi exporter (GPU metrics)
      9835

      # TabbyAPI (hydra-ai only, but safe to declare on both)
      5000

      # Open WebUI (hydra-ai)
      3000

      # Ollama (hydra-compute)
      11434

      # ComfyUI (hydra-compute)
      8188

      # NFS (for cross-node mounts if needed)
      2049
      111    # portmapper

      # Tailscale (handled by Tailscale service, but explicit)
      41641
    ];

    # UDP ports
    allowedUDPPorts = [
      # Tailscale
      41641

      # NFS
      2049
      111
    ];

    # Allow specific ranges for dynamic NFS ports
    allowedTCPPortRanges = [
      { from = 32765; to = 32769; }  # NFS callback
    ];

    allowedUDPPortRanges = [
      { from = 32765; to = 32769; }  # NFS callback
    ];

    # Trust cluster subnet entirely
    trustedInterfaces = [ "lo" ];

    # Extra rules for more granular control
    extraCommands = ''
      # Trust hydra-storage (192.168.1.244) completely
      iptables -A INPUT -s 192.168.1.244 -j ACCEPT

      # Trust other cluster nodes
      iptables -A INPUT -s 192.168.1.250 -j ACCEPT
      iptables -A INPUT -s 192.168.1.203 -j ACCEPT

      # Trust Tailscale subnet
      iptables -A INPUT -s 100.64.0.0/10 -j ACCEPT

      # Trust local 10GbE subnet (if different from management)
      iptables -A INPUT -s 10.0.0.0/8 -j ACCEPT
    '';

    # Logging for dropped packets (useful for debugging)
    logReversePathDrops = true;
    logRefusedConnections = false;  # Set true for debugging
  };

  # Ensure firewall is properly configured on boot
  systemd.services.firewall.wantedBy = [ "multi-user.target" ];
}
