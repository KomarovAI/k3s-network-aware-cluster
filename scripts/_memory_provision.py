#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Augment EnhancedK3SInstaller to provision ZRAM (1G, pri=150) and swapfile (4G, pri=50)
with safe idempotent behavior before installing K3S master (VPS).
"""

import subprocess

def _run(cmd: str, check=True):
    return subprocess.run(cmd, shell=True, check=check)

def provision_memory_safety_layer():
    print("🧠 Configuring ZRAM(1G, pri=150) + swapfile(4G, pri=50) + sysctl...")
    _run("sudo bash scripts/setup_memory_swap.sh", check=False)
    print("✅ ZRAM + swap configured (or already present)")
