# Hardware Requirements & Specifications

## 🖥️ **VPS Master Node (Enhanced)**

### Minimum Requirements
- **CPU**: 3 virtual cores (x86_64)
- **RAM**: 4 GB
- **Storage**: 100 GB NVMe SSD
- **Network**: 1,250 Mbps external bandwidth
- **OS**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+

### Optimizations Applied
- **Memory**: vm.swappiness=5, optimized dirty ratios
- **Network**: TCP BBR, increased buffers, fastopen enabled
- **CPU**: Priority-and-Fairness API scheduling
- **Storage**: etcd with 16GB quota, 8h auto-compaction

---

## 🏠 **Home PC Worker Node (Single)**

### Target Specifications
- **CPU**: 26 cores (AMD Ryzen 9 5950X / Intel i9-12900K class)
- **RAM**: 64 GB DDR4/DDR5
- **Storage**: 1 TB NVMe SSD (PCIe 4.0 preferred)
- **GPU**: NVIDIA RTX 3090 (24GB VRAM)
- **Network**: 10 Mbps to VPS (Tailscale), 1 Gbps local LAN
- **OS**: Ubuntu 22.04+ (for NVIDIA drivers compatibility)

### Optimizations Applied
- **Memory**: vm.swappiness=1, high PID limits
- **Network**: Optimized TCP buffers for 1Gbps local traffic
- **GPU**: NVIDIA Container Runtime, device plugin enabled
- **Storage**: Image GC thresholds: 80%/40%
- **Kubelet**: Eviction policies for graceful memory management

---

## 🌐 **Network Architecture**

### VPS ↔ Worker Connection
- **Primary**: Tailscale VPN (10 Mbps effective)
- **Protocol**: WireGuard-based with automatic NAT traversal
- **Latency**: 50-150ms (depends on geographic distance)
- **Compression**: gRPC/HTTP compression enabled

### Traffic Optimization
- **Registry Cache**: Pull-through cache on VPS (saves 70-80% worker traffic)
- **Monitoring**: Prometheus metrics collected locally, aggregated on VPS
- **Ingress**: All external traffic terminates on VPS

---

## 📊 **Resource Allocation Strategy**

### VPS (Control Plane)
```yaml
Reserved Resources:
  CPU: 800m (system) + 500m (kube) = 1.3 cores
  Memory: 800Mi (system) + 1200Mi (kube) = 2GB
  Available: 1.7 cores, 2GB for ingress/monitoring
```

### Worker (Workloads)
```yaml
Available Resources:
  CPU: ~25 cores (1 core reserved for system)
  Memory: ~60GB (4GB reserved for system/kubelet)
  GPU: 1x RTX 3090 (24GB VRAM)
  Storage: ~900GB (100GB reserved for system/logs)
```

---

## ⚡ **Performance Expectations**

### Single Worker Limitations
- **No redundancy**: Single point of failure for workloads
- **Scaling**: Vertical scaling only (resource limits per node)
- **Maintenance**: Workload downtime during worker maintenance

### Performance Benefits
- **High compute density**: 26 cores + 64GB + GPU in single node
- **Low latency**: Local storage and memory access
- **Cost efficiency**: Minimal VPS resources, maximum local hardware utilization
- **GPU acceleration**: Full RTX 3090 available for AI/ML workloads

---

## 🔧 **Hardware Compatibility**

### Tested Configurations
✅ **AMD Ryzen 9 5950X** + 64GB DDR4 + RTX 3090
✅ **Intel i9-12900K** + 64GB DDR5 + RTX 3090
✅ **Intel Xeon E-2288G** + 64GB ECC + RTX 3090

### VPS Providers
✅ **Hetzner Cloud** CX31 (3 vCPU, 8GB) or CX21 (3 vCPU, 4GB)
✅ **DigitalOcean** Basic (4GB, 2 vCPU, 80GB) or Regular (4GB, 2 vCPU)
✅ **Vultr** High Frequency (4GB, 2 vCPU, 128GB SSD)
✅ **Linode** Nanode (1GB, 1 vCPU) for testing, Shared CPU (4GB, 2 vCPU) for production

---

## 💡 **Upgrade Path**

### Adding More Workers
To scale beyond single worker:
1. Modify node selectors in deployments
2. Enable PodDisruptionBudgets with minAvailable > 0
3. Increase HPA maxReplicas
4. Consider load balancing between workers

### VPS Scaling
If VPS becomes bottleneck:
1. Upgrade to 4 vCPU, 8GB RAM
2. Enable dedicated CPU cores
3. Increase etcd quota to 32GB
4. Add SSD storage for registry cache

### Network Scaling
For better performance:
1. Upgrade worker internet connection
2. Consider dedicated VPN (OpenVPN/WireGuard)
3. Co-locate VPS closer to worker geographically
4. Use CDN for container image distribution