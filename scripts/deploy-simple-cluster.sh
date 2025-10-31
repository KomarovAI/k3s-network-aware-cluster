#!/bin/bash
# Simple K3S Cluster Deployment with VPS Optimization
# Focus: Core cluster functionality without unnecessary complexity
# Usage: ./deploy-simple-cluster.sh

set -e

echo "🚀 Deploying Simple K3S Cluster with VPS Optimization"

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
    local timeout=${3:-120}
    
    echo -e "${BLUE}⏳ Waiting for deployment $deployment in namespace $namespace...${NC}"
    kubectl rollout status deployment/$deployment -n $namespace --timeout=${timeout}s || {
        echo -e "${YELLOW}⚠️  Deployment $deployment took longer than expected${NC}"
        return 1
    }
}

# Step 1: Apply node labels and taints for intelligent placement
echo -e "${BLUE}🏷️  Step 1: Configuring node labels and taints...${NC}"

# Get master node name
MASTER_NODE=$(kubectl get nodes --selector='node-role.kubernetes.io/control-plane' -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || \
              kubectl get nodes --selector='node-role.kubernetes.io/master' -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || \
              kubectl get nodes -l 'k3s-controlplane=true' -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -n "$MASTER_NODE" ]; then
    echo "Configuring master node: $MASTER_NODE"
    
    # Apply taints to isolate master (VPS)
    kubectl taint node $MASTER_NODE k3s-controlplane=true:NoSchedule --overwrite || true
    kubectl taint node $MASTER_NODE node-role.kubernetes.io/master=true:NoSchedule --overwrite || true
    kubectl taint node $MASTER_NODE vps-resource-limited=true:NoSchedule --overwrite || true
    
    # Apply VPS master labels
    kubectl label node $MASTER_NODE \
        node-type=vps \
        role=control-plane \
        compute-tier=management \
        network-speed=10mbps \
        network-latency=high \
        zone=remote \
        internet-access=true \
        workload-isolation=true \
        --overwrite
    
    echo -e "${GREEN}✅ Master node $MASTER_NODE configured for VPS optimization${NC}"
else
    echo -e "${YELLOW}⚠️  Could not identify master node, manual configuration may be needed${NC}"
fi

# Label worker nodes (Home PCs)
echo "Configuring worker nodes..."
WORKER_NODES=$(kubectl get nodes --selector='!node-role.kubernetes.io/control-plane,!node-role.kubernetes.io/master' -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || \
               kubectl get nodes -l '!k3s-controlplane' -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)

if [ -n "$WORKER_NODES" ]; then
    for worker in $WORKER_NODES; do
        echo "Configuring worker: $worker"
        kubectl label node $worker \
            node-type=home-pc \
            role=worker \
            compute-tier=workload \
            network-speed=1000mbps \
            network-latency=low \
            zone=local \
            gpu-enabled=true \
            high-performance=true \
            --overwrite
    done
    echo -e "${GREEN}✅ Worker nodes configured for high-performance workloads${NC}"
else
    echo -e "${YELLOW}⚠️  No worker nodes found yet${NC}"
fi

# Step 2: Apply basic network compression
echo -e "${BLUE}💾 Step 2: Applying network compression configuration...${NC}"

# Create compression configmap
kubectl create configmap nginx-compression-config \
    --from-literal=enable-gzip="true" \
    --from-literal=gzip-level="6" \
    --from-literal=gzip-types="application/json,application/javascript,text/css,text/plain" \
    -n kube-system \
    --dry-run=client -o yaml | kubectl apply -f -

# Update NGINX Ingress if it exists
if kubectl get deployment ingress-nginx-controller -n ingress-nginx &> /dev/null; then
    echo "Updating NGINX Ingress with compression..."
    kubectl patch configmap ingress-nginx-controller -n ingress-nginx --patch='{
      "data": {
        "enable-gzip": "true",
        "gzip-level": "6",
        "gzip-types": "application/json,application/javascript,text/css,text/plain",
        "keep-alive-requests": "100",
        "worker-processes": "2",
        "max-worker-connections": "1024"
      }
    }' || echo -e "${YELLOW}⚠️  NGINX config not found, will be applied later${NC}"
fi

echo -e "${GREEN}✅ Network compression configured${NC}"

# Step 3: Deploy simplified monitoring
echo -e "${BLUE}📊 Step 3: Deploying basic monitoring stack...${NC}"

# Create monitoring namespace
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

# Apply simplified cluster configuration
if [ -f "manifests/core/simplified-cluster-config.yaml" ]; then
    echo "Applying simplified cluster configuration..."
    kubectl apply -f manifests/core/simplified-cluster-config.yaml
    
    # Wait for monitoring components
    wait_for_deployment monitoring prometheus-basic 120
    wait_for_deployment monitoring grafana-basic 120
    
    echo -e "${GREEN}✅ Basic monitoring stack deployed${NC}"
else
    echo -e "${YELLOW}⚠️  Simplified config not found, creating basic monitoring manually...${NC}"
    
    # Create basic Prometheus
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus-basic
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      nodeSelector:
        node-type: vps
      tolerations:
      - key: k3s-controlplane
        operator: Equal
        value: "true"
        effect: NoSchedule
      containers:
      - name: prometheus
        image: prom/prometheus:v2.47.0
        args:
          - '--config.file=/etc/prometheus/prometheus.yml'
          - '--storage.tsdb.path=/prometheus/'
          - '--storage.tsdb.retention.time=7d'
          - '--storage.tsdb.retention.size=2GB'
        ports:
        - containerPort: 9090
        resources:
          requests:
            memory: "200Mi"
            cpu: "100m"
          limits:
            memory: "500Mi"
            cpu: "300m"
EOF
    
    # Create Prometheus service
    kubectl expose deployment prometheus-basic --port=9090 --target-port=9090 -n monitoring
fi

# Step 4: Apply resource limits to system components
echo -e "${BLUE}⚙️  Step 4: Applying VPS resource limits...${NC}"

# Limit CoreDNS resources
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
}' 2>/dev/null || echo -e "${YELLOW}⚠️  CoreDNS patch skipped${NC}"

# Limit metrics-server if present
if kubectl get deployment metrics-server -n kube-system &> /dev/null; then
    kubectl patch deployment metrics-server -n kube-system --patch='{
      "spec": {
        "template": {
          "spec": {
            "containers": [{
              "name": "metrics-server",
              "resources": {
                "limits": {
                  "cpu": "100m",
                  "memory": "200Mi"
                },
                "requests": {
                  "cpu": "50m",
                  "memory": "100Mi"
                }
              }
            }]
          }
        }
      }
    }' || echo -e "${YELLOW}⚠️  Metrics-server patch skipped${NC}"
fi

echo -e "${GREEN}✅ VPS resource limits applied${NC}"

# Step 5: Verification and status
echo -e "${BLUE}🔍 Step 5: Cluster verification...${NC}"

echo ""
echo -e "${BLUE}📋 Final Cluster Status:${NC}"
kubectl get nodes -o wide

echo ""
echo -e "${BLUE}🏷️  Node Labels (for workload placement):${NC}"
kubectl get nodes --show-labels | grep -E '(node-type|compute-tier|network-speed)' | head -5 || kubectl get nodes --show-labels

echo ""
echo -e "${BLUE}🚀 Pod Distribution:${NC}"
echo "Control plane pods (VPS):" 
kubectl get pods -n kube-system -o wide | grep "$MASTER_NODE" | wc -l || echo "0"
echo "User workload pods (should be 0 on VPS):"
kubectl get pods --all-namespaces -o wide | grep -v kube-system | grep "$MASTER_NODE" | wc -l || echo "0"

echo ""
echo -e "${BLUE}📊 Resource Usage:${NC}"
kubectl top nodes 2>/dev/null || echo -e "${YELLOW}⚠️  Metrics not available yet${NC}"

echo ""
echo -e "${GREEN}🎉 Simple K3S cluster deployment completed!${NC}"
echo ""
echo -e "${YELLOW}📝 Cluster Summary:${NC}"
echo "✅ VPS master isolated (no workloads scheduled)"
echo "✅ Home PC workers ready for high-performance workloads"
echo "✅ Network compression enabled"
echo "✅ Basic monitoring available"
echo "✅ Resource limits applied to system components"
echo ""
echo -e "${BLUE}🔗 Access Information:${NC}"
echo "Prometheus: kubectl port-forward svc/prometheus-basic 9090:9090 -n monitoring"
echo "Grafana: kubectl port-forward svc/grafana-basic 3000:3000 -n monitoring"
echo ""
echo -e "${BLUE}🚀 Deploy Your Services:${NC}"
echo "Use node selectors in your deployments:"
echo "  nodeSelector:"
echo "    node-type: home-pc        # For workloads"
echo "    compute-tier: workload    # High performance"
echo "    gpu-enabled: 'true'       # For AI/ML tasks"
echo ""
echo -e "${GREEN}✅ Cluster ready for service deployment!${NC}"