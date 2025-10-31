#!/bin/bash
# K3S Worker Installation Script with GPU Support
# Usage: MASTER_IP=100.64.1.5 MASTER_TOKEN=K10xxx... ./install-worker.sh

set -e

echo "🚀 Installing K3S Worker with GPU Support"

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

# Check required environment variables
if [[ -z "$MASTER_IP" ]]; then
    echo -e "${RED}❌ MASTER_IP environment variable not set${NC}"
    echo "Usage: MASTER_IP=100.64.1.5 MASTER_TOKEN=K10xxx... ./install-worker.sh"
    exit 1
fi

if [[ -z "$MASTER_TOKEN" ]]; then
    echo -e "${RED}❌ MASTER_TOKEN environment variable not set${NC}"
    echo "Usage: MASTER_IP=100.64.1.5 MASTER_TOKEN=K10xxx... ./install-worker.sh"
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
echo -e "${GREEN}✅ Master IP: $MASTER_IP${NC}"

# Configure system
echo -e "${BLUE}🔧 Configuring system...${NC}"

# Enable IP forwarding
echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Detect GPU
GPU_TYPE="none"
GPU_LABELS=""

if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}🎮 NVIDIA GPU detected${NC}"
    GPU_INFO=$(nvidia-smi --query-gpu=name --format=csv,noheader,nounits | head -1)
    echo -e "${GREEN}✅ GPU: $GPU_INFO${NC}"
    
    # Install NVIDIA Container Toolkit if not present
    if ! dpkg -l | grep -q nvidia-container-toolkit; then
        echo -e "${BLUE}📦 Installing NVIDIA Container Toolkit...${NC}"
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
        curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
        
        sudo apt-get update
        sudo apt-get install -y nvidia-container-toolkit
        sudo systemctl restart docker
    fi
    
    GPU_TYPE="nvidia"
    # Determine GPU model for labeling
    if echo "$GPU_INFO" | grep -qi "rtx.*3090"; then
        GPU_LABELS="gpu=nvidia gpu-model=rtx3090 gpu-memory=24gb role=ai-worker"
    elif echo "$GPU_INFO" | grep -qi "rtx.*4070"; then
        GPU_LABELS="gpu=nvidia gpu-model=rtx4070 gpu-memory=12gb role=ai-worker"
    elif echo "$GPU_INFO" | grep -qi "rtx.*3060"; then
        GPU_LABELS="gpu=nvidia gpu-model=rtx3060 gpu-memory=12gb role=ai-worker"
    else
        GPU_LABELS="gpu=nvidia role=ai-worker"
    fi
else
    echo -e "${YELLOW}⚠️  No NVIDIA GPU detected${NC}"
    GPU_LABELS="role=worker"
fi

# Install K3S Worker
echo -e "${BLUE}📦 Installing K3S worker...${NC}"

curl -sfL https://get.k3s.io | K3S_URL=https://${MASTER_IP}:6443 K3S_TOKEN=${MASTER_TOKEN} sh -s - agent \
  --flannel-iface tailscale0 \
  --node-ip ${TAILSCALE_IP} \
  --node-external-ip ${TAILSCALE_IP} \
  --node-name ${NODE_NAME} \
  --container-runtime-endpoint unix:///var/run/containerd/containerd.sock

# Wait for node to be ready
echo -e "${BLUE}⏳ Waiting for node to join cluster...${NC}"
sudo systemctl enable k3s-agent

# Wait a bit for the node to register
sleep 10

# Set up kubectl config (copy from master or use kubeconfig)
echo -e "${BLUE}🔧 Setting up kubectl access...${NC}"
mkdir -p ~/.kube

# Try to get kubeconfig from master
if command -v scp &> /dev/null; then
    echo "You may need to copy kubeconfig from master manually:"
    echo "scp user@${MASTER_IP}:~/.kube/config ~/.kube/config"
fi

# Install NVIDIA Device Plugin if GPU detected
if [[ "$GPU_TYPE" == "nvidia" ]]; then
    echo -e "${BLUE}🎮 Installing NVIDIA Device Plugin...${NC}"
    # We'll need kubectl access for this, so provide instructions
    echo -e "${YELLOW}After kubectl is configured, run:${NC}"
    echo "kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.13.0/nvidia-device-plugin.yml"
fi

# Prepare node labeling commands
echo -e "${BLUE}🏷️  Node labeling commands (run after kubectl is configured):${NC}"
echo "kubectl label node ${NODE_NAME} zone=local network-speed=10mbps $GPU_LABELS --overwrite"

echo -e "${GREEN}🎉 K3S Worker installation completed successfully!${NC}"
echo ""
echo -e "${BLUE}📊 Next steps:${NC}"
echo "1. Copy kubeconfig from master: scp user@${MASTER_IP}:~/.kube/config ~/.kube/config"
echo "2. Label this node: kubectl label node ${NODE_NAME} zone=local network-speed=10mbps $GPU_LABELS --overwrite"
if [[ "$GPU_TYPE" == "nvidia" ]]; then
    echo "3. Install NVIDIA Device Plugin: kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.13.0/nvidia-device-plugin.yml"
fi
echo "4. Verify node status: kubectl get nodes -o wide"
echo ""
echo -e "${GREEN}✅ Worker node ready for network-aware scheduling!${NC}"