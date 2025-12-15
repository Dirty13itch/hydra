# NixOS Network Configuration with AdGuard DNS
#
# Configures network settings to use AdGuard Home on hydra-storage
# as the primary DNS resolver for the cluster.
#
# Add to /etc/nixos/configuration.nix:
#   imports = [ ./network-adguard.nix ];
#
# Or use the hydra-dns service option.

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.hydra-network;

  # AdGuard DNS server
  adguardIP = "192.168.1.244";

  # Fallback DNS (Cloudflare)
  fallbackDNS = [
    "1.1.1.1"
    "1.0.0.1"
  ];
in
{
  options.services.hydra-network = {
    enable = mkEnableOption "Hydra cluster network configuration";

    adguardIp = mkOption {
      type = types.str;
      default = adguardIP;
      description = "IP address of AdGuard Home server";
    };

    useFallback = mkOption {
      type = types.bool;
      default = true;
      description = "Include fallback DNS servers";
    };

    enableMDNS = mkOption {
      type = types.bool;
      default = true;
      description = "Enable mDNS for local service discovery";
    };

    staticHosts = mkOption {
      type = types.attrsOf types.str;
      default = {
        "hydra-ai" = "192.168.1.250";
        "hydra-compute" = "192.168.1.203";
        "hydra-storage" = "192.168.1.244";
      };
      description = "Static host mappings";
    };
  };

  config = mkIf cfg.enable {
    # DNS Configuration
    networking.nameservers = [
      cfg.adguardIp
    ] ++ optionals cfg.useFallback fallbackDNS;

    # Disable systemd-resolved's stub listener to avoid conflicts
    services.resolved = {
      enable = true;
      dnssec = "allow-downgrade";
      domains = [ "~." ];
      fallbackDns = fallbackDNS;
      llmnr = "false";
    };

    # Static hosts file entries for cluster nodes
    networking.hosts = mapAttrs' (name: ip: {
      name = ip;
      value = [ name "${name}.local" ];
    }) cfg.staticHosts;

    # mDNS for local discovery
    services.avahi = mkIf cfg.enableMDNS {
      enable = true;
      nssmdns4 = true;
      publish = {
        enable = true;
        addresses = true;
        domain = true;
        hinfo = true;
        userServices = true;
        workstation = true;
      };
    };

    # Firewall rules for DNS
    networking.firewall = {
      allowedUDPPorts = mkIf cfg.enableMDNS [ 5353 ];  # mDNS
    };

    # Network wait online configuration
    systemd.services.NetworkManager-wait-online.enable = mkDefault false;
    systemd.network.wait-online.enable = mkDefault false;
  };
}
