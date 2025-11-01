#!/usr/bin/env bash
set -euo pipefail

# Configure 1G ZRAM (priority 150) and 8G swapfile (priority 50)
# Safe to run multiple times (idempotent)

echo "[ZRAM] Installing zram-tools..."
if ! command -v zramswap >/dev/null 2>&1; then
  apt-get update -y && apt-get install -y zram-tools >/dev/null 2>&1 || true
fi

mkdir -p /etc
cat >/etc/default/zramswap <<'EOF'
ALGO=lz4
PERCENT=0
PRIORITY=150
ZRAM_SIZE=1024
EOF

# Ensure zramswap service enabled
if systemctl list-unit-files | grep -q zramswap.service; then
  systemctl enable --now zramswap || true
else
  # Fallback manual zram setup if service not present
  modprobe zram || true
  echo lz4 > /sys/block/zram0/comp_algorithm || true
  echo $((1024*1024*1024)) > /sys/block/zram0/disksize || true
  mkswap /dev/zram0 || true
  swapon -p 150 /dev/zram0 || true
fi

echo "[SWAPFILE] Ensuring 8G swapfile with priority 50..."
SWAPFILE=/swapfile
if ! grep -q "^/swapfile" /etc/fstab 2>/dev/null; then
  if [ ! -f "$SWAPFILE" ]; then
    fallocate -l 8G "$SWAPFILE" || dd if=/dev/zero of="$SWAPFILE" bs=1M count=8192
    chmod 600 "$SWAPFILE"
    mkswap "$SWAPFILE"
  fi
  echo "/swapfile none swap sw,pri=50 0 0" >> /etc/fstab
fi

# Activate swapfile with proper priority
if ! swapon --show | grep -q "/swapfile"; then
  swapon -p 50 /swapfile
fi

# Kernel tunables
apply_sysctl() {
  KEY="$1"; VAL="$2"; FILE=/etc/sysctl.conf
  if grep -q "^${KEY}=" "$FILE" 2>/dev/null; then
    sed -i "s|^${KEY}=.*|${KEY}=${VAL}|" "$FILE"
  else
    echo "${KEY}=${VAL}" >> "$FILE"
  fi
}

apply_sysctl vm.swappiness 60
apply_sysctl vm.vfs_cache_pressure 120

sysctl -p >/dev/null 2>&1 || true

# Show resulting configuration
printf "\n=== Active swaps ===\n"
swapon --show || true
printf "\n=== /etc/default/zramswap ===\n"
cat /etc/default/zramswap || true
printf "\n=== /etc/fstab swap entries ===\n"
grep -E "\s+swap\s+" /etc/fstab || true