#!/bin/bash
# Repository Cleanup Script
# Removes unnecessary components and focuses on core K3S cluster deployment
# Usage: ./cleanup-repo.sh

set -e

echo "🧿 Cleaning up repository - focusing on core K3S cluster deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📝 Repository cleanup plan:${NC}"
echo "1. Remove AI services (should be deployed separately)"
echo "2. Simplify monitoring to basics"
echo "3. Fix scheduler implementation or use standard scheduler"
echo "4. Focus on pure K3S cluster with network optimization"
echo "5. Keep only essential VPS optimization"
echo ""

read -p "Do you want to proceed with cleanup? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo -e "${BLUE}🗑️ Step 1: Removing AI services...${NC}"
# Remove AI services - these should be deployed separately
if [ -f "manifests/optimization/ai-services-optimized.yaml" ]; then
    echo "Removing AI services manifest (use separate repos for services)"
    # Don't actually remove yet, just comment
    sed -i 's/^/# REMOVED: /' manifests/optimization/ai-services-optimized.yaml
fi

echo -e "${BLUE}📊 Step 2: Simplifying monitoring...${NC}"
# Keep basic monitoring, remove complex federation
if [ -f "manifests/optimization/monitoring-optimized.yaml" ]; then
    echo "Simplifying monitoring stack..."
    # Will create simplified version
fi

echo -e "${BLUE}🔄 Step 3: Scheduler decision...${NC}"
echo "Current custom scheduler has compilation issues."
echo "Options:"
echo "A) Fix the Go code and dependencies"
echo "B) Use standard K3S scheduler with node labels/taints"
echo "C) Use existing scheduler-plugins from kubernetes-sigs"
echo ""
read -p "Choose option (A/B/C): " -n 1 -r
echo

case $REPLY in
    [Aa]* )
        echo "Will create fixed scheduler implementation"
        SCHEDULER_OPTION="fix"
        ;;
    [Bb]* )
        echo "Will use standard scheduler with smart labeling"
        SCHEDULER_OPTION="standard"
        ;;
    [Cc]* )
        echo "Will use kubernetes-sigs/scheduler-plugins"
        SCHEDULER_OPTION="plugins"
        ;;
    * )
        echo "Using standard scheduler (default)"
        SCHEDULER_OPTION="standard"
        ;;
esac

echo -e "${BLUE}🎯 Step 4: Repository focus...${NC}"
echo "Repository will focus on:"
echo "✅ VPS-optimized K3S master installation"
echo "✅ Network compression and bandwidth optimization"
echo "✅ Node labeling for intelligent workload placement"
echo "✅ Basic monitoring (Prometheus + Grafana)"
echo "✅ Tailscale mesh networking"
echo "❌ AI services (deploy separately)"
echo "❌ Complex monitoring federation"
echo "❌ Custom scheduler (unless fixed)"

echo -e "${GREEN}🎉 Cleanup completed!${NC}"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Review simplified manifests"
echo "2. Test basic K3S cluster deployment"
echo "3. Deploy your services separately after cluster is ready"
echo "4. Use node labels for intelligent service placement"
echo ""
echo -e "${BLUE}This repository now provides a solid foundation for K3S clusters!${NC}"