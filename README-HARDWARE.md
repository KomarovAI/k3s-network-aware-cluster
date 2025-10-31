# K3S Enhanced Hybrid Cluster 🚀

> Production-ready K3S cluster optimized for enhanced VPS master + powerful Home PC workers

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Production Ready](https://img.shields.io/badge/Production-Ready-green)](https://github.com/KomarovAI/k3s-network-aware-cluster)

## 🧩 Hardware Profile (Required)

This repository is tuned for the following reference hardware:

- 🔹 Master node (VPS):
  - CPU: 3 vCPU
  - RAM: 4 GB
  - Storage: 100 GB NVMe/SSD
  - Role: Control plane only (ingress + monitoring allowed)
  - Network: Tailscale mesh, optimized with TCP BBR and HTTP compression

- 🔹 Worker nodes (Home PCs), at least 2 nodes:
  - CPU: 26 CPU cores (per node)
  - RAM: 64 GB (per node)
  - Storage: 1 TB NVMe/SSD (per node)
  - GPU: NVIDIA RTX 3090 (per node)
  - Role: All workloads (AI/ML, DB, web)
  - Network: 1 Gbps LAN, Tailscale to VPS

These specs are hard‑coded into resource recommendations, taints/tolerations, node selectors, autoscaling behavior, and monitoring footprints. Different hardware will work, but for best results keep master close to the above and ensure at least two powerful workers.

## 🏗️ Architecture

- VPS master is isolated for control plane, ingress, and monitoring
- All user workloads scheduled to worker nodes by labels/affinity
- AI/ML and compute workloads prefer GPU-enabled workers
- Network optimized via gzip/brotli, HTTP/2 multiplexing, and TCP BBR

## 🚀 Quick Start

1) Install enhanced master on VPS (3 vCPU, 4 GB RAM, 100 GB NVMe)
```bash
python3 scripts/install_cluster_enhanced.py --mode master
```

2) Join each Home PC worker (26 CPU / 64 GB / 1 TB / RTX 3090)
```bash
scp ~/join_worker_enhanced.py user@worker:/tmp/
ssh user@worker "python3 /tmp/join_worker_enhanced.py"
```

3) Apply production hardening (PSA, NetworkPolicies, RBAC, Monitoring)
```bash
python3 scripts/production_hardening.py apply
```

For full documentation, see the sections below in this README and manifests/prod/.
