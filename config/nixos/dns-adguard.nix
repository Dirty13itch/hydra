# NixOS DNS Configuration - AdGuard Integration
#
# This module configures NixOS nodes to use hydra-storage's AdGuard DNS
# for local name resolution and ad blocking.
#
# Deploy to both hydra-ai and hydra-compute:
#   scp dns-adguard.nix typhon@192.168.1.250:/tmp/
#   ssh typhon@192.168.1.250 "sudo cp /tmp/dns-adguard.nix /etc/nixos/ && \
#     sudo nixos-rebuild switch"
#
# Repeat for hydra-compute (192.168.1.203)

{ config, pkgs, lib, ... }:

{
  # Network configuration with AdGuard DNS
  networking = {
    # Use AdGuard on hydra-storage as primary DNS
    nameservers = [
      "192.168.1.244"  # hydra-storage AdGuard (primary)
      "1.1.1.1"        # Cloudflare (fallback)
      "8.8.8.8"        # Google (fallback)
    ];

    # Disable NetworkManager's DNS management to use our static config
    networkmanager.dns = "none";

    # Enable resolved for DNS caching and DNSSEC
    # Note: We disable stub listener to avoid port 53 conflicts
  };

  # systemd-resolved configuration
  services.resolved = {
    enable = true;

    # Use our custom nameservers, don't auto-detect
    fallbackDns = [ "1.1.1.1" "8.8.8.8" ];

    # DNSSEC validation (optional, AdGuard handles this)
    dnssec = "allow-downgrade";

    # DNS over TLS (optional)
    # dnsovertls = "opportunistic";

    # Disable multicast DNS (we use AdGuard rewrites)
    llmnr = "false";

    # Extra config for resolved
    extraConfig = ''
      # Cache DNS results locally
      Cache=yes
      CacheFromLocalhost=yes

      # Timeout settings
      DNSStubListenerExtra=
    '';
  };

  # Ensure /etc/resolv.conf points to resolved
  environment.etc."resolv.conf".mode = "direct-symlink";

  # Hosts file additions for cluster hostnames (backup if DNS fails)
  networking.extraHosts = ''
    # Hydra Cluster Nodes
    192.168.1.250 hydra-ai hydra-ai.local
    192.168.1.203 hydra-compute hydra-compute.local
    192.168.1.244 hydra-storage hydra-storage.local

    # Tailscale IPs (for remote access)
    100.84.120.44 hydra-ai.ts hydra-ai.tailnet
    100.74.73.44 hydra-compute.ts hydra-compute.tailnet
    100.111.54.59 hydra-storage.ts hydra-storage.tailnet
  '';

  # DNS utilities for troubleshooting
  environment.systemPackages = with pkgs; [
    dnsutils    # dig, nslookup
    bind        # named-checkconf
  ];
}
