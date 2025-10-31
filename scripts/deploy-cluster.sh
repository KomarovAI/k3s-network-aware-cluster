#!/bin/bash
# Deploy complete K3S cluster with network-aware scheduling

set -e

echo "🚀 Deploying K3S Network-Aware Cluster"

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
    echo -e "${RED}❌ Cannot connect to Kubernetes cluster. Please check your kubeconfig.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Kubernetes cluster is accessible${NC}"

# Apply CRDs
echo -e "${BLUE}📋 Applying Custom Resource Definitions...${NC}"
kubectl apply -f manifests/network-crds/

# Wait for CRDs to be established
echo -e "${BLUE}⏳ Waiting for CRDs to be ready...${NC}"
sleep 5

# Verify CRDs
if kubectl get crd networktopologies.network.komarov.dev &> /dev/null; then
    echo -e "${GREEN}✅ NetworkTopology CRD is ready${NC}"
else
    echo -e "${RED}❌ NetworkTopology CRD failed to install${NC}"
    exit 1
fi

# Apply scheduler and controller
echo -e "${BLUE}🧠 Deploying network-aware scheduler and controller...${NC}"
kubectl apply -f manifests/scheduler/scheduler-deployment.yaml

# Wait for scheduler to be ready
echo -e "${BLUE}⏳ Waiting for scheduler to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=network-aware-scheduler -n kube-system --timeout=180s

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Network-aware scheduler is ready${NC}"
else
    echo -e "${YELLOW}⚠️  Scheduler took longer than expected, checking status...${NC}"
    kubectl get pods -n kube-system -l app=network-aware-scheduler
fi

# Wait for controller to be ready
echo -e "${BLUE}⏳ Waiting for network controller to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=network-controller -n kube-system --timeout=180s

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Network controller is ready${NC}"
else
    echo -e "${YELLOW}⚠️  Controller took longer than expected, checking status...${NC}"
    kubectl get pods -n kube-system -l app=network-controller
fi

# Apply AI services
echo -e "${BLUE}🤖 Deploying AI services...${NC}"
kubectl apply -f manifests/applications/ai-services/deployments.yaml

# Wait for AI services to start
echo -e "${BLUE}⏳ Waiting for AI services to start...${NC}"
sleep 10

# Check deployment status
echo -e "${BLUE}📈 Checking deployment status...${NC}"
echo ""
echo -e "${BLUE}=== CLUSTER STATUS ===${NC}"
kubectl get nodes -o wide
echo ""
echo -e "${BLUE}=== NETWORK COMPONENTS ===${NC}"
kubectl get pods -n kube-system | grep network
echo ""
echo -e "${BLUE}=== AI SERVICES ===${NC}"
kubectl get pods -n default
echo ""
echo -e "${BLUE}=== NETWORK TOPOLOGY ===${NC}"
if kubectl get networktopology komarov-network &> /dev/null; then
    kubectl get networktopology komarov-network -o yaml | head -20
else
    echo -e "${YELLOW}⚠️  Network topology not yet created${NC}"
fi

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Check scheduler logs: kubectl logs -n kube-system -l app=network-aware-scheduler"
echo "2. Check controller logs: kubectl logs -n kube-system -l app=network-controller"
echo "3. View network topology: kubectl get networktopology komarov-network -o yaml"
echo "4. Monitor AI services: kubectl get pods -w"
echo "5. Access services through ingress: https://ai.komarov.dev"
echo ""
echo -e "${YELLOW}Troubleshooting:${NC}"
echo "- If pods are pending, check node labels: kubectl get nodes --show-labels"
echo "- If scheduler issues: kubectl describe pods -n kube-system -l app=network-aware-scheduler"
echo "- If network issues: kubectl logs -n kube-system -l app=network-controller"
echo ""
echo -e "${GREEN}Happy clustering! 🚀${NC}"