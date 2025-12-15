# Example GPU power configuration for hydra-ai
#
# hydra-ai has:
# - GPU 0: RTX 5090 32GB (default TDP: 575W, limit: 450W)
# - GPU 1: RTX 4090 24GB (default TDP: 450W, limit: 300W)
#
# Total configured limit: 750W (vs 1025W default)
# This provides ~750W headroom for system + other nodes

{ config, pkgs, ... }:

{
  imports = [
    ../gpu-power.nix
  ];

  services.hydra-gpu-power = {
    enable = true;

    gpus = [
      {
        index = 0;
        powerLimit = 450;  # 5090: 450W vs 575W default
        name = "RTX 5090";
      }
      {
        index = 1;
        powerLimit = 300;  # 4090: 300W vs 450W default
        name = "RTX 4090";
      }
    ];

    # Alert if total GPU power exceeds 700W
    alertThreshold = 700;

    # Check every 60 seconds
    monitorInterval = 60;

    enableMonitoring = true;
  };

  # Ensure nvidia-persistenced is running
  hardware.nvidia.nvidiaPersistenced = true;

  # Prometheus GPU metrics
  services.prometheus.exporters.node = {
    enable = true;
    enabledCollectors = [ "systemd" ];
  };
}
