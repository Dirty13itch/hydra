# Rule: NixOS is Declarative

**Priority:** CRITICAL

## On NixOS Nodes (hydra-ai, hydra-compute)

**NEVER** install packages directly with `nix-env` or package managers.

**ALWAYS** modify `/etc/nixos/configuration.nix` then rebuild:

```bash
# 1. Edit configuration
sudo nano /etc/nixos/configuration.nix

# 2. Test build (dry-run)
sudo nixos-rebuild dry-build

# 3. Apply changes
sudo nixos-rebuild switch
```

## Rollback Procedure

```bash
# List generations
sudo nix-env --list-generations -p /nix/var/nix/profiles/system

# Rollback to previous
sudo nixos-rebuild switch --rollback
```

## Docker on Unraid Only

On hydra-storage (Unraid), Docker containers are the deployment method.
Never install packages directly on Unraid.
