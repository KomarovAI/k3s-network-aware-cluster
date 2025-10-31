#!/bin/bash
# K3S Master Installation Script with Tailscale Integration
# Usage: ./install-master.sh

set -e

echo "🚀 Installing K3S Master with Network-Aware Scheduling"

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
echo -e "${BLUE}📋 Checking prerequisites...${NC}"

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

# Configure system
echo -e "${BLUE}🔧 Configuring system...${NC}"

# Enable IP forwarding
echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Install K3S
echo -e "${BLUE}📦 Installing K3S master...${NC}"

curl -sfL https://get.k3s.io | sh -s - server \
  --write-kubeconfig-mode 644 \
  --disable traefik \
  --disable servicelb \
  --flannel-iface tailscale0 \
  --advertise-address ${TAILSCALE_IP} \
  --node-ip ${TAILSCALE_IP} \
  --node-external-ip ${TAILSCALE_IP} \
  --bind-address ${TAILSCALE_IP} \
  --node-name ${NODE_NAME} \
  --cluster-cidr 10.42.0.0/16 \
  --service-cidr 10.43.0.0/16 \
  --kube-scheduler-arg="v=2"

# Wait for K3S to be ready
echo -e "${BLUE}⏳ Waiting for K3S to be ready...${NC}"
sudo systemctl enable k3s
while ! sudo kubectl get nodes &> /dev/null; do
    echo "Waiting for K3S API server..."
    sleep 5
done

# Set up kubectl for current user
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config

# Label master node
echo -e "${BLUE}🏷️  Labeling master node...${NC}"
kubectl label node ${NODE_NAME} zone=remote role=master network-speed=1000mbps --overwrite

# Install NGINX Ingress Controller
echo -e "${BLUE}🌐 Installing NGINX Ingress Controller...${NC}"
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Wait for ingress controller
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

# Get join token for workers
JOIN_TOKEN=$(sudo cat /var/lib/rancher/k3s/server/node-token)

echo -e "${GREEN}🎉 K3S Master installation completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📝 Worker nodes can join using:${NC}"
echo "export K3S_URL=https://${TAILSCALE_IP}:6443"
echo "export K3S_TOKEN=${JOIN_TOKEN}"
echo "curl -sfL https://get.k3s.io | sh -s - agent --flannel-iface tailscale0 --node-ip \$(tailscale ip -4) --node-external-ip \$(tailscale ip -4)"
echo ""
echo -e "${BLUE}📊 Cluster status:${NC}"
kubectl get nodes -o wide
echo ""
echo -e "${GREEN}✅ Ready to deploy network-aware scheduler!${NC}"
echo "Next steps:"
echo "1. Join worker nodes to the cluster"
echo "2. Run: kubectl apply -f manifests/network-crds/"
echo "3. Run: kubectl apply -f manifests/scheduler/"
echo "4. Deploy your applications with network-aware scheduling"