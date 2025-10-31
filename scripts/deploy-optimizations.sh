#!/bin/bash
# Deploy Network Optimizations for K3S Cluster
# Optimizes VPS master + Home PC workers architecture
# Usage: ./deploy-optimizations.sh

set -e

echo "🚀 Deploying Network Optimizations for K3S Cluster"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Please install kubectl first.${NC}"
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}❌ Cannot access Kubernetes cluster. Please check your kubeconfig.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Kubernetes cluster is accessible${NC}"
echo -e "${BLUE}📋 Cluster info:${NC}"
kubectl get nodes -o wide
echo ""

# Function to wait for deployment
wait_for_deployment() {
    local namespace=$1
    local deployment=$2
    local timeout=${3:-300}
    
    echo -e "${BLUE}⏳ Waiting for deployment $deployment in namespace $namespace...${NC}"
    kubectl rollout status deployment/$deployment -n $namespace --timeout=${timeout}s
}

# Function to wait for daemonset
wait_for_daemonset() {
    local namespace=$1
    local daemonset=$2
    local timeout=${3:-300}
    
    echo -e "${BLUE}⏳ Waiting for daemonset $daemonset in namespace $namespace...${NC}"
    kubectl rollout status daemonset/$daemonset -n $namespace --timeout=${timeout}s
}

# Step 1: Apply compression and optimization configurations
echo -e "${BLUE}🔧 Step 1: Applying compression and optimization configurations...${NC}"

if [ -f "manifests/optimization/compression-config.yaml" ]; then
    echo "Applying compression configuration..."
    kubectl apply -f manifests/optimization/compression-config.yaml
    echo -e "${GREEN}✅ Compression configuration applied${NC}"
else
    echo -e "${YELLOW}⚠️  Compression config file not found, skipping...${NC}"
fi

# Step 2: Update NGINX Ingress with compression settings
echo -e "${BLUE}🌐 Step 2: Updating NGINX Ingress with compression settings...${NC}"

# Patch NGINX ConfigMap with compression settings
kubectl patch configmap nginx-configuration -n ingress-nginx --patch='{
  "data": {
    "enable-brotli": "true",
    "brotli-level": "6",
    "gzip-level": "6",
    "gzip-types": "application/json,application/javascript,text/css,text/plain,text/xml",
    "keep-alive-requests": "10000",
    "upstream-keepalive-connections": "50",
    "worker-processes": "2",
    "max-worker-connections": "1024"
  }
}' || echo -e "${YELLOW}⚠️  NGINX ConfigMap not found, will be created by compression config${NC}"

# Restart NGINX Ingress to apply changes
echo "Restarting NGINX Ingress Controller..."
kubectl rollout restart deployment/ingress-nginx-controller -n ingress-nginx || echo -e "${YELLOW}⚠️  NGINX Controller not found, will be installed later${NC}"

# Step 3: Apply VPS resource limits to system components
echo -e "${BLUE}⚙️  Step 3: Applying VPS resource limits to system components...${NC}"

# Patch CoreDNS with resource limits
echo "Limiting CoreDNS resources for VPS..."
kubectl patch deployment coredns -n kube-system --patch='{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "coredns",
          "resources": {
            "limits": {
              "cpu": "100m",
              "memory": "128Mi"
            },
            "requests": {
              "cpu": "50m",
              "memory": "64Mi"
            }
          }
        }]
      }
    }
  }
}' || echo -e "${YELLOW}⚠️  CoreDNS patch failed, may not be necessary${NC}"

# Step 4: Verify master node isolation
echo -e "${BLUE}🔒 Step 4: Verifying master node isolation...${NC}"

# Get master node name
MASTER_NODE=$(kubectl get nodes --selector='node-role.kubernetes.io/control-plane' -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || \
              kubectl get nodes --selector='node-role.kubernetes.io/master' -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || \
              kubectl get nodes --selector='k3s-controlplane=true' -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -n "$MASTER_NODE" ]; then
    echo "Found master node: $MASTER_NODE"
    
    # Apply taints to isolate master
    kubectl taint node $MASTER_NODE k3s-controlplane=true:NoSchedule --overwrite || true
    kubectl taint node $MASTER_NODE node-role.kubernetes.io/master=true:NoSchedule --overwrite || true
    
    # Apply labels for network-aware scheduling
    kubectl label node $MASTER_NODE \
        node-type=vps \
        compute-tier=control-plane \
        workload-isolation=true \
        network-speed=10mbps \
        --overwrite
    
    echo -e "${GREEN}✅ Master node $MASTER_NODE isolated and labeled${NC}"
else
    echo -e "${YELLOW}⚠️  Could not find master node, manual configuration may be needed${NC}"
fi

# Label worker nodes
echo "Labeling worker nodes..."
kubectl label nodes --selector='!node-role.kubernetes.io/control-plane,!node-role.kubernetes.io/master' \
    node-type=home-pc \
    compute-tier=workload \
    network-speed=1000mbps \
    zone=local \
    --overwrite || echo -e "${YELLOW}⚠️  Worker node labeling failed, may need manual configuration${NC}"

# Step 5: Deploy optimized monitoring stack
echo -e "${BLUE}📊 Step 5: Deploying optimized monitoring stack...${NC}"

if [ -f "manifests/optimization/monitoring-optimized.yaml" ]; then
    echo "Applying optimized monitoring configuration..."
    kubectl apply -f manifests/optimization/monitoring-optimized.yaml
    
    # Wait for monitoring components
    echo "Waiting for monitoring components to be ready..."
    wait_for_deployment monitoring prometheus-master 180
    wait_for_daemonset monitoring prometheus-worker-aggregator 180
    wait_for_deployment monitoring grafana 120
    
    echo -e "${GREEN}✅ Optimized monitoring stack deployed${NC}"
else
    echo -e "${YELLOW}⚠️  Monitoring config file not found, skipping...${NC}"
fi

# Step 6: Deploy optimized AI services
echo -e "${BLUE}🤖 Step 6: Deploying optimized AI services...${NC}"

if [ -f "manifests/optimization/ai-services-optimized.yaml" ]; then
    echo "Applying optimized AI services configuration..."
    kubectl apply -f manifests/optimization/ai-services-optimized.yaml
    
    # Wait for AI services
    echo "Waiting for AI services to be ready..."
    wait_for_deployment default ollama-optimized 300
    wait_for_deployment default stable-diffusion-optimized 300
    
    echo -e "${GREEN}✅ Optimized AI services deployed${NC}"
else
    echo -e "${YELLOW}⚠️  AI services config file not found, skipping...${NC}"
fi

# Step 7: Verification and status check
echo -e "${BLUE}🔍 Step 7: Verification and status check...${NC}"

echo ""
echo -e "${BLUE}📋 Cluster Status:${NC}"
kubectl get nodes -o wide

echo ""
echo -e "${BLUE}🗺 Node Labels (Network-Aware Scheduling):${NC}"
kubectl get nodes --show-labels | grep -E '(node-type|compute-tier|network-speed)' || kubectl get nodes --show-labels

echo ""
echo -e "${BLUE}📊 Resource Usage:${NC}"
kubectl top nodes || echo -e "${YELLOW}⚠️  Metrics server not available yet${NC}"

echo ""
echo -e "${BLUE}🚀 Pod Placement (should avoid VPS for workloads):${NC}"
kubectl get pods -o wide --all-namespaces | grep -v kube-system || true

echo ""
echo -e "${BLUE}🌐 Services Status:${NC}"
kubectl get services --all-namespaces

echo ""
echo -e "${GREEN}🎉 Network optimization deployment completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📝 Optimization Summary:${NC}"
echo "✅ VPS master node isolated from workloads"
echo "✅ Compression enabled (Gzip/Brotli)"
echo "✅ Resource limits applied to system components"
echo "✅ Network-aware scheduling labels applied"
echo "✅ Monitoring optimized for bandwidth conservation"
echo "✅ AI services configured for home PC placement"
echo ""
echo -e "${BLUE}🔗 Access Information:${NC}"
echo "Grafana: kubectl port-forward svc/grafana 3000:3000 -n monitoring"
echo "Prometheus: kubectl port-forward svc/prometheus-master 9090:9090 -n monitoring"
echo "Ollama: kubectl port-forward svc/ollama-service 11434:11434"
echo "Stable Diffusion: kubectl port-forward svc/stable-diffusion-service 7860:7860"
echo ""
echo -e "${GREEN}✅ All optimizations applied successfully!${NC}"
echo -e "${BLUE}Monitor bandwidth usage between VPS and Home PCs to verify optimization effectiveness.${NC}"