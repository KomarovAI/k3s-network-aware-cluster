# K3S Network-Aware Cluster 🚀

> **Production-ready K3S cluster with intelligent network-aware scheduling, Tailscale integration, and automatic bandwidth/latency optimization for distributed AI workloads**

[![Build Status](https://github.com/KomarovAI/k3s-network-aware-cluster/workflows/CI/badge.svg)](https://github.com/KomarovAI/k3s-network-aware-cluster/actions)
[![Go Report Card](https://goreportcard.com/badge/github.com/KomarovAI/k3s-network-aware-cluster)](https://goreportcard.com/report/github.com/KomarovAI/k3s-network-aware-cluster)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Overview

This project implements an enterprise-grade K3S cluster with **intelligent network-aware scheduling** that automatically:

- 📊 **Measures network characteristics** between nodes (bandwidth, latency, cost)
- 🧠 **Makes smart scheduling decisions** based on real-time network topology
- ⚡ **Optimizes workload placement** to minimize network bottlenecks
- 🔒 **Secures inter-node communication** via Tailscale mesh VPN
- 📈 **Provides comprehensive monitoring** with Prometheus & Grafana

### Key Features

✅ **Automatic network topology discovery**  
✅ **Real-time bandwidth and latency monitoring**  
✅ **Custom K3S scheduler with network awareness**  
✅ **Tailscale integration for secure mesh networking**  
✅ **GPU workload optimization for AI/ML tasks**  
✅ **Production-ready monitoring and alerting**  
✅ **CI/CD pipeline with automated deployments**  

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   VPS Germany   │    │   Home PC #1    │    │   Home PC #2    │
│   (Master)      │    │   (AI Worker)   │    │   (AI Worker)   │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • K3S Master    │◄──►│ • RTX 3090      │◄──►│ • RTX 4070      │
│ • Ingress       │    │ • Ollama        │    │ • Stable Diff   │
│ • Monitoring    │    │ • 32GB RAM      │    │ • 16GB RAM      │
│ • file-pull     │    │ • NVMe SSD      │    │ • NVMe SSD      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────── Tailscale Mesh Network ──────────────┘
              (10 Mbps ↔ 1 Gbps local)
```

## 🚀 Quick Start

### Prerequisites

- 2+ Linux machines (VPS + home PCs)
- Docker installed on all nodes
- NVIDIA GPU (optional, for AI workloads)
- Tailscale account

### 1. Setup Tailscale

```bash
# On all nodes
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --accept-routes --advertise-routes=10.42.0.0/16,10.43.0.0/16
```

### 2. Install K3S Master (VPS)

```bash
git clone https://github.com/KomarovAI/k3s-network-aware-cluster.git
cd k3s-network-aware-cluster

# Run master installation
./scripts/install-master.sh
```

### 3. Install K3S Workers (PCs)

```bash
# Get master token and IP from step 2
export MASTER_IP="100.64.1.5"  # Tailscale IP
export MASTER_TOKEN="K10xxx..."

# Run worker installation
./scripts/install-worker.sh
```

### 4. Deploy Network-Aware Scheduler

```bash
# Apply CRDs and scheduler
kubectl apply -f manifests/network-crds/
kubectl apply -f manifests/scheduler/

kubectl get pods -n kube-system | grep network-aware
```

### 5. Deploy AI Services

```bash
# Deploy AI workloads with network-aware scheduling
kubectl apply -f manifests/applications/ai-services/

# Check pod placement
kubectl get pods -o wide
```

## 📊 Network-Aware Scheduling

### How It Works

The custom scheduler automatically measures and considers:

| Metric | Description | Impact on Scheduling |
|--------|-------------|---------------------|
| **Bandwidth** | Measured via iperf3 | Pods requiring high data transfer prefer fast nodes |
| **Latency** | Measured via ping RTT | Real-time workloads avoid high-latency paths |
| **Cost** | Calculated from speed | Expensive transfers (slow links) are penalized |
| **Topology** | Node roles and zones | AI workloads prefer GPU nodes, web prefers public nodes |

### Example: Smart Pod Placement

```yaml
# AI workload automatically goes to local GPU node
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
spec:
  template:
    metadata:
      annotations:
        network.komarov.dev/min-bandwidth: "1mbps"
        network.komarov.dev/max-latency: "100ms"
        network.komarov.dev/data-locality: "high"
    spec:
      schedulerName: network-aware-scheduler  # 🧠 Smart scheduling
      containers:
      - name: ollama
        image: ollama/ollama:latest
```

**Result**: Scheduler places Ollama on local PC (1ms latency) instead of VPS (45ms latency)

## 🔧 Configuration

### Network Topology Definition

```yaml
# manifests/network-crds/komarov-topology.yaml
apiVersion: network.komarov.dev/v1
kind: NetworkTopology
metadata:
  name: komarov-network
spec:
  nodes:
    vps-germany:
      bandwidth:
        pc-home: "10mbps"     # Slow internet link
        internet: "1000mbps"  # Fast public access
      latency:
        pc-home: "45ms"       # International latency
        internet: "5ms"       # Local datacenter
      cost:
        pc-home: 0.8          # High cost (slow)
        internet: 0.1         # Low cost (fast)
    pc-home:
      bandwidth:
        vps-germany: "10mbps"
        local: "1000mbps"     # Local network is fast
      latency:
        vps-germany: "45ms"
        local: "1ms"          # Local is instant
      cost:
        vps-germany: 0.8
        local: 0.1
```

## 📈 Monitoring

### Grafana Dashboards

The project includes pre-built dashboards for:

- **Network Topology Map** - Visual representation of node connections
- **Bandwidth Utilization** - Real-time traffic between nodes  
- **Scheduling Decisions** - Why pods were placed where
- **AI Workload Performance** - GPU utilization and task completion times

### Access Monitoring

```bash
# Port-forward Grafana
kubectl port-forward svc/grafana 3000:3000 -n monitoring

# Open http://localhost:3000
# Username: admin
# Password: kubectl get secret grafana -o jsonpath="{.data.admin-password}" | base64 -d
```

## 🧪 Testing

### Network Benchmark

```bash
# Run comprehensive network benchmark
kubectl apply -f tests/network-benchmark.yaml

# View results
kubectl logs job/network-benchmark
```

## 📦 Components

### Core Components

| Component | Description | Language | Status |
|-----------|-------------|----------|--------|
| **Network-Aware Scheduler** | Custom K3S scheduler with network intelligence | Go | ✅ Ready |
| **Network Controller** | Monitors and updates network topology | Go | ✅ Ready |
| **Metrics Collector** | Gathers bandwidth/latency data | Go | ✅ Ready |
| **Tailscale Integration** | Secure mesh networking | Shell | ✅ Ready |
| **AI Services** | Ollama, Stable Diffusion, etc. | YAML | ✅ Ready |
| **Monitoring Stack** | Prometheus, Grafana, AlertManager | YAML | ✅ Ready |

### Project Structure

```
├── cluster/                  # Cluster setup scripts
│   ├── tailscale/           # Tailscale configuration
│   ├── k3s/                 # K3S installation scripts
│   └── monitoring/          # Monitoring setup
├── scheduler/               # Custom scheduler implementation
│   ├── network-aware-scheduler/  # Main scheduler code
│   ├── network-controller/      # Network topology controller
│   └── crds/                    # Custom resource definitions
├── manifests/               # Kubernetes manifests
│   ├── scheduler/           # Scheduler deployment
│   ├── network-crds/        # Network topology CRDs
│   ├── rbac/                # RBAC configuration
│   └── applications/        # Application deployments
├── docker/                  # Docker images
├── scripts/                 # Installation and utility scripts
├── tests/                   # Test manifests and scripts
└── docs/                    # Additional documentation
```

## 🌟 Use Cases

### Perfect For:

- **🤖 Distributed AI/ML workloads** - Ollama, Stable Diffusion, training jobs
- **🎮 Game servers** - Low-latency requirements across regions
- **📊 Edge computing** - Processing close to data sources
- **🏠 Homelab clusters** - Mixed hardware with varying network speeds
- **☁️ Hybrid cloud** - On-premises + cloud with intelligent workload placement

### Real-World Example

```yaml
# Automatic optimization:
# • AI inference runs on local GPU (1ms latency)
# • Web API runs on VPS (5ms to internet)
# • Heavy data processing stays local (1Gbps bandwidth)
# • File sync happens during off-peak (cost optimization)
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Kubernetes SIG-Scheduling** for scheduler framework
- **Tailscale** for excellent mesh networking
- **K3S team** for lightweight Kubernetes
- **Rancher** for K3S and ecosystem tools

## 📞 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/KomarovAI/k3s-network-aware-cluster/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/KomarovAI/k3s-network-aware-cluster/discussions)
- 📧 **Email**: komarov.ai.dev@gmail.com

---

**⭐ Star this repo if it helps you build better distributed systems!**