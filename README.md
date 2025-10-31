# K3S Enhanced Hybrid Cluster 🚀

> **Production-ready K3S cluster optimized for enhanced VPS (3 vCPU, 4GB RAM, 100GB NVMe) + powerful Home PC worker (1× worker: 26 CPU, 64GB RAM, 1TB NVMe, RTX 3090)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Production Ready](https://img.shields.io/badge/Production-Ready-green)](https://github.com/KomarovAI/k3s-network-aware-cluster)
[![Security](https://img.shields.io/badge/Security-NSA%2FCISA-blue)](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-release-kubernetes-hardening-guidance/)

## 🧩 Reference Hardware & Network Profile (explicit)

- 🔹 **Master node (VPS)**:
  - CPU: **3 vCPU**
  - RAM: **4 GB**
  - Storage: **100 GB NVMe**
  - Network: **1 250 МБ/с внешний канал** (к Интернету и к воркеру через Tailscale)
  - Role: Control plane only (ingress + monitoring allowed)

- 🔹 **Worker node (Home PC) — single node**:
  - CPU: **26 CPU cores**
  - RAM: **64 GB**
  - Storage: **1 TB NVMe**
  - GPU: **NVIDIA RTX 3090**
  - Network: **10 МБ/с канал до VPS** (через Tailscale); **1 ГБ/с локальная LAN**
  - Role: All workloads (AI/ML, DB, web)

> Примечание: Репозиторий тюнится под эти параметры. Лейблы/таинты, правила размещения, HPA, ретеншн мониторинга и ресурсы ingress учитывают узкий канал **10 МБ/с** у воркера и широкий **1 250 МБ/с** у VPS.

## 🏗️ Architecture (summary)

- VPS master изолирован (control plane + ingress + monitoring)
- Все пользовательские нагрузки размещаются на Home PC (node selectors/affinity)
- Компрессия трафика (gzip/brotli) и TCP BBR компенсируют **10 МБ/с** канал у воркера
- Мониторинг и ingress на VPS используют **1 250 МБ/с** внешний канал
- Pull-through registry cache на VPS экономит трафик для образов
- VPA автоматически оптимизирует ресурсы системных компонентов

## 🚀 Quick Start

1) **Install enhanced master** (VPS 3 vCPU / 4GB / 100GB NVMe / **1 250 МБ/с**)
```bash
python3 scripts/install_cluster_enhanced.py --mode master
```

2) **Join worker** (1× Home PC: 26 CPU / 64GB / 1TB / RTX 3090 / **10 МБ/с** до VPS)
```bash
scp ~/join_worker_enhanced.py user@worker:/tmp/
ssh user@worker "python3 /tmp/join_worker_enhanced.py"
```

3) **Apply production hardening** (PSA, NetworkPolicies, RBAC, Monitoring, VPA)
```bash
python3 scripts/production_hardening.py apply --with-vpa --with-registry-cache
```

> Подробности по железу: см. README-HARDWARE.md

## 🔧 Key Optimizations

### Network & Traffic
- **TCP BBR** congestion control for better throughput over limited links
- **Pull-through registry cache** on VPS to minimize image download traffic
- **HTTP/3 & gRPC compression** for API server communication
- **Priority-and-Fairness** queuing for API requests

### Resource Management
- **VPA (Vertical Pod Autoscaler)** for automatic resource optimization
- **Enhanced etcd** configuration with 16GB quota and 8h compaction
- **GPU scheduling** optimized for single RTX 3090 worker
- **Image garbage collection** tuned for limited storage

### Security & Compliance
- **Pod Security Standards v1.29** with restricted enforcement
- **Zero-Trust network policies** with default deny-all
- **RBAC hardening** with minimal service account privileges
- **NSA/CISA hardening** guidelines implementation

## 📊 Single Worker Considerations

This cluster is optimized for **single worker** deployments:
- Default replicas: **1** (no redundancy assumptions)
- HPA starts from **minReplicas: 1**
- PDB configured for **maxUnavailable: 0** when needed
- All workloads scheduled on single powerful Home PC
- GPU resources: **nvidia.com/gpu: 1** available

## 🎯 Use Cases

Perfect for:
- **Development environments** with powerful local hardware
- **AI/ML experimentation** with dedicated GPU
- **Cost-optimized production** for single-tenant applications  
- **Edge computing** scenarios with centralized control plane
- **Hybrid cloud** setups minimizing VPS resource usage