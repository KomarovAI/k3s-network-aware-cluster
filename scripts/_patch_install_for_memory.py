#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch install_cluster_enhanced.py to invoke ZRAM(1G)/swap(4G) provisioning
before K3S installation on master.
"""

from pathlib import Path

file_path = Path('scripts/install_cluster_enhanced.py')
text = file_path.read_text(encoding='utf-8')

# Insert import for memory provision helper
if 'from scripts._memory_provision import provision_memory_safety_layer' not in text:
    text = text.replace(
        'from typing import Dict, List, Optional\n\n',
        'from typing import Dict, List, Optional\n\nfrom scripts._memory_provision import provision_memory_safety_layer\n\n'
    )

# Hook call inside install_enhanced_master before system optimizations
needle = 'print("🚀 Installing K3S master for enhanced VPS...")\n        print(f"   VPS Specs:'
if 'provision_memory_safety_layer()' not in text:
    text = text.replace(
        '        # System optimizations for enhanced VPS\n        self._apply_enhanced_system_optimizations()',
        '        # Memory safety layer (ZRAM 1G pri=150 + swapfile 4G pri=50)\n        provision_memory_safety_layer()\n\n        # System optimizations for enhanced VPS\n        self._apply_enhanced_system_optimizations()'
    )

# Adjust sysctl defaults in _apply_enhanced_system_optimizations to align with ZRAM profile
text = text.replace('vm.swappiness=5', 'vm.swappiness=60')
text = text.replace('vm.vfs_cache_pressure=50', 'vm.vfs_cache_pressure=120')

file_path.write_text(text, encoding='utf-8')
print('Patched scripts/install_cluster_enhanced.py to include ZRAM/swap provisioning and sysctl tuning.')
