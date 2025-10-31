#!/usr/bin/env bash
set -euo pipefail

# One-time patch to inject ZRAM/swap provisioning into installer, then remove itself from docs
python3 scripts/_patch_install_for_memory.py || true

# shellcheck disable=SC2016
if ! grep -q 'provision_memory_safety_layer' scripts/install_cluster_enhanced.py; then
  echo "[WARN] Memory provisioning hook not injected. Please run: python3 scripts/_patch_install_for_memory.py" >&2
  exit 1
fi

echo "[OK] Installer patched for ZRAM/swap provisioning."
