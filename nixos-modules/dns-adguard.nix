# NixOS DNS Configuration for AdGuard Home
#
# Configures NixOS nodes to use AdGuard Home on hydra-storage
# for DNS resolution with cluster hostname rewrites.
#
# Add to /etc/nixos/configuration.nix:
#   imports = [ ./dns-adguard.nix ];

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.hydra-dns;
in
{
  options.services.hydra-dns = {
    enable = mkEnableOption "Hydra DNS configuration (AdGuard)";

    adguardIp = mkOption {
      type = types.str;
      default = "192.168.1.244";
      description = "IP address of AdGuard Home server";
    };

    fallbackDns = mkOption {
      type = types.listOf types.str;
      default = [ "1.1.1.1" "8.8.8.8" ];
      description = "Fallback DNS servers if AdGuard is unreachable";
    };

    searchDomains = mkOption {
      type = types.listOf types.str;
      default = [ "hydra.local" "local" ];
      description = "DNS search domains";
    };

    enableMdns = mkOption {
      type = types.bool;
      default = true;
      description = "Enable mDNS (Avahi) for .local discovery";
    };
  };

  config = mkIf cfg.enable {
    # Configure systemd-resolved with AdGuard as primary DNS
    services.resolved = {
      enable = true;
      dnssec = "false";  # AdGuard handles this
      llmnr = "true";

      # Use AdGuard as primary, with fallbacks
      extraConfig = ''
        [Resolve]
        DNS=${cfg.adguardIp}
        FallbackDNS=${concatStringsSep " " cfg.fallbackDns}
        Domains=${concatStringsSep " " cfg.searchDomains}
        DNSOverTLS=no
        MulticastDNS=yes
        Cache=yes
        CacheFromLocalhost=no
      '';
    };

    # Ensure /etc/resolv.conf points to systemd-resolved stub
    environment.etc."resolv.conf".mode = "direct-symlink";

    # Avahi for mDNS (.local resolution)
    services.avahi = mkIf cfg.enableMdns {
      enable = true;
      nssmdns4 = true;
      nssmdns6 = true;

      publish = {
        enable = true;
        addresses = true;
        domain = true;
        hinfo = true;
        userServices = true;
        workstation = true;
      };

      extraServiceFiles = {
        ssh = ''
          <?xml version="1.0" standalone='no'?>
          <!DOCTYPE service-group SYSTEM "avahi-service.dtd">
          <service-group>
            <name replace-wildcards="yes">%h SSH</name>
            <service>
              <type>_ssh._tcp</type>
              <port>22</port>
            </service>
          </service-group>
        '';
      };
    };

    # NSS configuration for hostname resolution order
    system.nssDatabases.hosts = mkForce [
      "files"
      "mymachines"
      "mdns4_minimal [NOTFOUND=return]"
      "resolve [!UNAVAIL=return]"
      "dns"
      "myhostname"
    ];

    # Network manager DNS settings (if using NetworkManager)
    networking.networkmanager.dns = mkIf config.networking.networkmanager.enable "systemd-resolved";

    # Static hosts for cluster nodes (fallback if DNS fails)
    networking.hosts = {
      "192.168.1.250" = [ "hydra-ai" "hydra-ai.hydra.local" ];
      "192.168.1.203" = [ "hydra-compute" "hydra-compute.hydra.local" ];
      "192.168.1.244" = [ "hydra-storage" "hydra-storage.hydra.local" ];
    };

    # Tailscale DNS (if Tailscale is enabled)
    # services.tailscale.extraUpFlags = [ "--accept-dns=false" ];
  };
}
