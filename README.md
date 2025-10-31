# K3S Enhanced Hybrid Cluster 🚀

> **Production-ready K3S cluster optimized for enhanced VPS (3 vCPU, 4GB RAM, 100GB NVMe) + powerful Home PC workers (2× workers: 26 CPU, 64GB RAM, 1TB NVMe, RTX 3090)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Production Ready](https://img.shields.io/badge/Production-Ready-green)](https://github.com/KomarovAI/k3s-network-aware-cluster)
[![Security](https://img.shields.io/badge/Security-NSA%2FCISA-blue)](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-release-kubernetes-hardening-guidance/)

## 🧩 Reference Hardware Profile (explicit)

- 🔹 **Master node (VPS)**:
  - CPU: **3 vCPU**
  - RAM: **4 GB**
  - Storage: **100 GB NVMe**
  - Role: Control plane only (ingress + monitoring allowed)
  - Network: Tailscale mesh, TCP BBR, HTTP/2 + gzip/brotli

- 🔹 **Worker nodes (Home PCs) — at least 2 nodes**:
  - CPU: **26 CPU cores (per node)**
  - RAM: **64 GB (per node)**
  - Storage: **1 TB NVMe (per node)**
  - GPU: **NVIDIA RTX 3090 (per node)**
  - Role: All workloads (AI/ML, DB, web)
  - Network: 1 Gbps LAN (local), Tailscale to VPS

This repo is tuned to these specs: node labels/taints, HPA/PDB thresholds, monitoring retention, and ingress resources reflect this capacity. Other hardware works, but best results are achieved with the above profile.

## 🏗️ Architecture (summary)

- VPS master is isolated (control plane + ingress + monitoring)
- Workloads scheduled to Home PCs via labels/affinity
- GPU/compute workloads land on RTX 3090 nodes
- Network optimized via compression + TCP BBR

## 🚀 Quick Start

1) **Install enhanced master** (VPS 3 vCPU / 4GB / 100GB NVMe)
```bash
python3 scripts/install_cluster_enhanced.py --mode master
```

2) **Join workers** (2× Home PC: 26 CPU / 64GB / 1TB / RTX 3090)
```bash
scp ~/join_worker_enhanced.py user@worker:/tmp/
ssh user@worker "python3 /tmp/join_worker_enhanced.py"
```

3) **Apply production hardening** (PSA, NetworkPolicies, RBAC, Monitoring)
```bash
python3 scripts/production_hardening.py apply
```

> Detailed docs continue below. For hardware-only details see README-HARDWARE.md
