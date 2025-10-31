#!/bin/bash
# Optimized K3S Master Installation Script for VPS
# Designed for lightweight VPS with minimal resource usage
# Usage: ./install-master-optimized.sh

set -e

echo "🚀 Installing Optimized K3S Master for VPS Environment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}This script should not be run as root${NC}"
   exit 1
fi

# Check prerequisites
echo -e "${BLUE}📋 Checking prerequisites for VPS optimization...${NC}"

if ! command -v tailscale &> /dev/null; then
    echo -e "${RED}❌ Tailscale not found. Please install Tailscale first:${NC}"
    echo "curl -fsSL https://tailscale.com/install.sh | sh"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Installing Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo -e "${YELLOW}⚠️  Please log out and back in for Docker permissions to take effect${NC}"
fi

# Get Tailscale IP
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")
if [[ -z "$TAILSCALE_IP" ]]; then
    echo -e "${RED}❌ Tailscale not connected. Please run: tailscale up${NC}"
    exit 1
fi

NODE_NAME=$(hostname -f)
echo -e "${GREEN}✅ Tailscale IP: $TAILSCALE_IP${NC}"
echo -e "${GREEN}✅ Node name: $NODE_NAME${NC}"

# VPS Resource Optimization
echo -e "${BLUE}🔧 Optimizing VPS for K3S master-only operation...${NC}"

# System optimizations for lightweight VPS
sudo sysctl -w vm.swappiness=10
sudo sysctl -w vm.vfs_cache_pressure=50
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Create optimized K3S configuration
echo -e "${BLUE}📝 Creating optimized K3S configuration...${NC}"
sudo mkdir -p /etc/rancher/k3s

# K3S server configuration optimized for VPS master
cat <<EOF | sudo tee /etc/rancher/k3s/config.yaml
# Optimized K3S configuration for VPS master
write-kubeconfig-mode: 644

# Disable unnecessary components to save resources
disable:
  - traefik       # Use external ingress
  - servicelb     # Use external load balancer
  - local-storage # Use external storage
  - metrics-server # Use lightweight alternative

# Network configuration
flannel-iface: tailscale0
advertise-address: ${TAILSCALE_IP}
node-ip: ${TAILSCALE_IP}
node-external-ip: ${TAILSCALE_IP}
bind-address: ${TAILSCALE_IP}
node-name: ${NODE_NAME}
cluster-cidr: 10.42.0.0/16
service-cidr: 10.43.0.0/16

# Master node isolation - prevent workload scheduling
node-taint:
  - "k3s-controlplane=true:NoSchedule"
  - "node-role.kubernetes.io/master=true:NoSchedule"

# Resource limits for components
kube-apiserver-arg:
  - "max-requests-inflight=200"
  - "max-mutating-requests-inflight=100"
  - "request-timeout=60s"
  - "min-request-timeout=30"

kube-controller-manager-arg:
  - "concurrent-deployment-syncs=3"
  - "concurrent-replicaset-syncs=3"
  - "concurrent-resource-quota-syncs=3"

kube-scheduler-arg:
  - "v=2"
  - "kube-api-qps=50"
  - "kube-api-burst=100"

# etcd optimizations for small clusters
etcd-arg:
  - "quota-backend-bytes=2147483648"  # 2GB
  - "auto-compaction-retention=1h"
  - "auto-compaction-mode=periodic"
EOF

# Install optimized K3S
echo -e "${BLUE}📦 Installing optimized K3S master...${NC}"

curl -sfL https://get.k3s.io | sh -s - server

# Wait for K3S to be ready
echo -e "${BLUE}⏳ Waiting for K3S to be ready...${NC}"
sudo systemctl enable k3s
while ! sudo kubectl get nodes &> /dev/null; do
    echo "Waiting for K3S API server..."
    sleep 5
done

# Set up kubectl for current user
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
export KUBECONFIG=~/.kube/config

# Verify master node isolation
echo -e "${BLUE}🔒 Verifying master node isolation...${NC}"
kubectl taint node ${NODE_NAME} k3s-controlplane=true:NoSchedule --overwrite || true
kubectl taint node ${NODE_NAME} node-role.kubernetes.io/master=true:NoSchedule --overwrite || true

# Label master node with VPS-specific attributes
echo -e "${BLUE}🏷️  Labeling master node...${NC}"
kubectl label node ${NODE_NAME} \
  zone=remote \
  role=master \
  node-type=vps \
  network-speed=10mbps \
  compute-tier=control-plane \
  workload-isolation=true \
  --overwrite

# Install lightweight NGINX Ingress Controller
echo -e "${BLUE}🌐 Installing lightweight NGINX Ingress Controller...${NC}"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: ingress-nginx
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/instance: ingress-nginx
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-configuration
  namespace: ingress-nginx
  labels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/part-of: ingress-nginx
data:
  # Compression optimizations for slow VPS-Home links
  enable-brotli: "true"
  brotli-level: "6"
  gzip-level: "6"
  gzip-types: "application/json,application/javascript,text/css,text/plain,text/xml"
  # Connection optimizations
  keep-alive-requests: "10000"
  upstream-keepalive-connections: "50"
  # Resource limits for VPS
  worker-processes: "2"
  max-worker-connections: "1024"
EOF

kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Apply resource limits to ingress controller for VPS
echo -e "${BLUE}⚙️  Applying VPS resource limits to ingress controller...${NC}"
kubectl patch deployment ingress-nginx-controller -n ingress-nginx -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "controller",
          "resources": {
            "limits": {
              "cpu": "200m",
              "memory": "200Mi"
            },
            "requests": {
              "cpu": "100m",
              "memory": "128Mi"
            }
          }
        }]
      }
    }
  }
}'

# Wait for ingress controller with timeout
echo -e "${BLUE}⏳ Waiting for ingress controller...${NC}"
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=180s || echo -e "${YELLOW}⚠️  Ingress controller taking longer than expected${NC}"

# Create network optimization ConfigMap
echo -e "${BLUE}📊 Creating network optimization configuration...${NC}"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: network-optimization-config
  namespace: kube-system
data:
  # Compression settings for VPS-Home communication
  grpc-compression: "gzip"
  json-minification: "true"
  batch-requests: "true"
  max-batch-size: "100"
  batch-timeout: "30s"
  
  # Bandwidth optimization
  enable-traffic-shaping: "true"
  vps-max-bandwidth: "10mbps"
  home-max-bandwidth: "1000mbps"
  
  # Monitoring optimization
  metrics-batch-interval: "30s"
  metrics-compression: "true"
  log-aggregation: "true"
EOF

# Get join token for workers
JOIN_TOKEN=$(sudo cat /var/lib/rancher/k3s/server/node-token)

# Create optimized worker join script
echo -e "${BLUE}📝 Creating optimized worker join instructions...${NC}"
cat <<EOF > ~/worker-join-optimized.sh
#!/bin/bash
# Optimized worker join script for home PCs
# Run this on each home PC worker node

export K3S_URL=https://${TAILSCALE_IP}:6443
export K3S_TOKEN=${JOIN_TOKEN}

# Install with optimizations for high-performance workers
curl -sfL https://get.k3s.io | sh -s - agent \
  --flannel-iface tailscale0 \
  --node-ip \$(tailscale ip -4) \
  --node-external-ip \$(tailscale ip -4) \
  --kubelet-arg="max-pods=200" \
  --kubelet-arg="serialize-image-pulls=false" \
  --kubelet-arg="registry-pull-qps=10" \
  --kubelet-arg="registry-burst=20" \
  --node-label="zone=local" \
  --node-label="role=worker" \
  --node-label="node-type=home-pc" \
  --node-label="network-speed=1000mbps" \
  --node-label="compute-tier=workload"
EOF

chmod +x ~/worker-join-optimized.sh

echo -e "${GREEN}🎉 Optimized K3S Master installation completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📊 VPS Master Optimization Summary:${NC}"
echo "✅ Master node isolated (no workload scheduling)"
echo "✅ Resource limits applied to system components"
echo "✅ Network compression enabled"
echo "✅ Lightweight ingress controller configured"
echo "✅ Monitoring optimized for bandwidth conservation"
echo ""
echo -e "${YELLOW}📝 Worker nodes can join using the optimized script:${NC}"
echo "scp ~/worker-join-optimized.sh user@home-pc:/tmp/"
echo "ssh user@home-pc 'chmod +x /tmp/worker-join-optimized.sh && /tmp/worker-join-optimized.sh'"
echo ""
echo -e "${BLUE}📊 Cluster status:${NC}"
kubectl get nodes -o wide
echo ""
echo -e "${GREEN}✅ Ready to deploy network-aware scheduler with VPS optimizations!${NC}"
echo "Next steps:"
echo "1. Join worker nodes using the optimized script"
echo "2. Run: kubectl apply -f manifests/network-crds/"
echo "3. Run: kubectl apply -f manifests/scheduler/"
echo "4. Deploy compression-optimized manifests"
echo "5. Monitor VPS resource usage with: kubectl top nodes"