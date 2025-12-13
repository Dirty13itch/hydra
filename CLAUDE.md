# Hydra Canonical Context (auto-loaded)

This repository is the canonical source of truth for the Hydra home cluster.

## Latest ground-truth snapshot
@docs/canonical/00-system-reality/LATEST_SNAPSHOT.md

## Full file-level reconciliation report
@docs/canonical/00-system-reality/HYDRA_FULL_FILE_ANALYSIS_AND_RECONCILIATION.md

## Service reconciliation matrix
@docs/canonical/00-system-reality/HYDRA_SERVICE_RECONCILIATION_MATRIX.md

## Full per-file manifest (CSV)
@docs/canonical/00-system-reality/HYDRA_FILE_MANIFEST.csv

## Stable SSH targets
- hydra-storage (Unraid) 192.168.1.244
- hydra-compute (NixOS) 192.168.1.203
- hydra-ai (NixOS) 192.168.1.250

Rules:
- Prefer hostnames (hydra-*) over raw IPs in configs/scripts.
- Keep legacy/prototypes in /legacy. Do not deploy from /legacy.
