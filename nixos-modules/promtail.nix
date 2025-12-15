# NixOS Promtail Module for Hydra Cluster
#
# Configures Promtail to ship logs to Loki on hydra-storage.
# Use on hydra-ai and hydra-compute.
#
# Add to /etc/nixos/configuration.nix:
#   imports = [ ./promtail.nix ];

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.hydra-promtail;

  promtailConfig = {
    server = {
      http_listen_port = cfg.httpPort;
      grpc_listen_port = 0;
    };

    positions = {
      filename = "/var/lib/promtail/positions.yaml";
    };

    clients = [{
      url = "${cfg.lokiUrl}/loki/api/v1/push";
      tenant_id = "hydra";
      batchwait = "1s";
      batchsize = 1048576;
    }];

    scrape_configs = [
      # Journal logs
      {
        job_name = "journal";
        journal = {
          max_age = "12h";
          labels = {
            job = "systemd-journal";
            node = config.networking.hostName;
          };
        };
        relabel_configs = [
          {
            source_labels = [ "__journal__systemd_unit" ];
            target_label = "unit";
          }
          {
            source_labels = [ "__journal_priority_keyword" ];
            target_label = "level";
          }
        ];
        pipeline_stages = [
          {
            # Map priority to log level
            template = {
              source = "level";
              template = ''
                {{ if eq .Value "emerg" }}emergency
                {{ else if eq .Value "alert" }}alert
                {{ else if eq .Value "crit" }}critical
                {{ else if eq .Value "err" }}error
                {{ else if eq .Value "warning" }}warning
                {{ else if eq .Value "notice" }}notice
                {{ else if eq .Value "info" }}info
                {{ else if eq .Value "debug" }}debug
                {{ else }}unknown{{ end }}
              '';
            };
          }
          {
            labels = {
              level = "";
            };
          }
        ];
      }
      # Service-specific logs
      {
        job_name = "services";
        static_configs = [
          {
            targets = [ "localhost" ];
            labels = {
              job = "hydra-services";
              node = config.networking.hostName;
              __path__ = "/var/log/hydra/*.log";
            };
          }
        ];
        pipeline_stages = [
          {
            json = {
              expressions = {
                level = "level";
                message = "message";
                service = "service";
              };
            };
          }
          {
            labels = {
              level = "";
              service = "";
            };
          }
        ];
      }
    ] ++ optionals cfg.scrapeTabbyAPI [
      # TabbyAPI logs
      {
        job_name = "tabbyapi";
        static_configs = [
          {
            targets = [ "localhost" ];
            labels = {
              job = "tabbyapi";
              node = config.networking.hostName;
              service = "tabbyapi";
              __path__ = "/var/log/tabbyapi/*.log";
            };
          }
        ];
        pipeline_stages = [
          {
            regex = {
              expression = "(?P<timestamp>\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}) \\| (?P<level>\\w+) +\\| (?P<message>.*)";
            };
          }
          {
            labels = {
              level = "";
            };
          }
        ];
      }
    ] ++ optionals cfg.scrapeOllama [
      # Ollama logs
      {
        job_name = "ollama";
        static_configs = [
          {
            targets = [ "localhost" ];
            labels = {
              job = "ollama";
              node = config.networking.hostName;
              service = "ollama";
              __path__ = "/var/log/ollama/*.log";
            };
          }
        ];
      }
    ];
  };

  configFile = pkgs.writeText "promtail.yaml" (builtins.toJSON promtailConfig);
in
{
  options.services.hydra-promtail = {
    enable = mkEnableOption "Promtail log shipper for Hydra cluster";

    lokiUrl = mkOption {
      type = types.str;
      default = "http://192.168.1.244:3100";
      description = "Loki push URL";
    };

    httpPort = mkOption {
      type = types.port;
      default = 9080;
      description = "HTTP port for Promtail metrics";
    };

    scrapeTabbyAPI = mkOption {
      type = types.bool;
      default = false;
      description = "Whether to scrape TabbyAPI logs";
    };

    scrapeOllama = mkOption {
      type = types.bool;
      default = false;
      description = "Whether to scrape Ollama logs";
    };
  };

  config = mkIf cfg.enable {
    # Install promtail
    environment.systemPackages = [ pkgs.grafana-loki ];

    # Create log directories
    systemd.tmpfiles.rules = [
      "d /var/log/hydra 0755 root root -"
      "d /var/lib/promtail 0755 promtail promtail -"
    ];

    # Create user
    users.users.promtail = {
      isSystemUser = true;
      group = "promtail";
      description = "Promtail log shipper";
    };
    users.groups.promtail = { };

    # Systemd service
    systemd.services.promtail = {
      description = "Promtail Log Shipper";
      wantedBy = [ "multi-user.target" ];
      after = [ "network.target" ];

      serviceConfig = {
        Type = "simple";
        User = "promtail";
        Group = "promtail";
        ExecStart = "${pkgs.grafana-loki}/bin/promtail -config.file=${configFile}";
        Restart = "on-failure";
        RestartSec = 10;

        # Security
        NoNewPrivileges = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        ReadWritePaths = [ "/var/lib/promtail" ];
        ReadOnlyPaths = [ "/var/log" ];

        # Allow reading journal
        SupplementaryGroups = [ "systemd-journal" ];
      };
    };

    # Firewall
    networking.firewall.allowedTCPPorts = [ cfg.httpPort ];
  };
}
