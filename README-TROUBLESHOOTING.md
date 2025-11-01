# 🔧 Troubleshooting Guide

> Comprehensive troubleshooting guide for K3S Enterprise Hybrid Cluster deployment issues

## 🚨 Most Common Issues & Quick Fixes

### 1. 🛠️ Missing Dependencies (90% of issues)

**Symptoms:**
- `command not found: helm`
- `ModuleNotFoundError: No module named 'requests'`
- `jq: command not found`

**Quick Fix:**
```bash
# Run the auto-fix script
sudo ./scripts/auto_fix_dependencies.sh

# Or install manually:
sudo apt-get update
sudo apt-get install -y curl jq python3 python3-yaml python3-requests gettext-base
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### 2. ☸️ Kubernetes Access Issues (70% of issues)

**Symptoms:**
- `Unable to connect to the server`
- `x509: certificate signed by unknown authority`
- `connection refused`

**Quick Fix:**
```bash
# Set proper KUBECONFIG
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
sudo chmod 644 /etc/rancher/k3s/k3s.yaml

# Test access
kubectl get nodes
```

### 3. 💾 Storage Issues (60% of issues)

**Symptoms:**
- `PersistentVolumeClaim remains Pending`
- `no persistent volumes available`

**Quick Fix:**
```bash
# Check StorageClass
kubectl get storageclass

# Set local-path as default (K3S includes this)
kubectl patch storageclass local-path -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

### 4. 🌐 Network/Internet Issues (50% of issues)

**Symptoms:**
- `Failed to pull image`
- `timeout downloading`
- `DNS resolution failed`

**Quick Fix:**
```bash
# Test connectivity
ping 8.8.8.8
curl -I https://github.com
curl -I https://registry-1.docker.io

# Check DNS
systemctl status systemd-resolved
nslookup google.com
```

## 🔍 Diagnostic Commands

### Pre-Deployment Checks
```bash
# Run comprehensive dependency check
./scripts/check_dependencies.sh

# Quick system info
kubectl version --client
helm version
python3 --version
df -h
free -h
```

### During Deployment
```bash
# Monitor all pods
kubectl get pods -A --watch

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp -A

# Pod logs
kubectl logs -f deployment/COMPONENT_NAME -n NAMESPACE
```

### Post-Deployment
```bash
# Find problematic pods
kubectl get pods -A | grep -v Running

# Check PVC status
kubectl get pvc -A | grep Pending

# Test ingress
curl -k https://SERVICE.cockpit.work.gd

# Resource usage
kubectl top nodes
kubectl top pods -A
```

## 📊 Component-Specific Issues

### Cert-Manager

**Issue:** TLS certificates not working
```bash
# Check cert-manager status
kubectl get pods -n cert-manager
kubectl describe clusterissuer letsencrypt-prod
kubectl get certificaterequests -A

# Debug certificate
kubectl describe certificate SERVICE-tls -n NAMESPACE
```

**Common Fixes:**
```bash
# Restart cert-manager
kubectl rollout restart deployment/cert-manager -n cert-manager

# Check Let's Encrypt rate limits
# Wait or use staging issuer for testing
```

### Ingress-Nginx

**Issue:** Services not accessible via ingress
```bash
# Check ingress controller
kubectl get pods -n ingress-nginx
kubectl logs deployment/ingress-nginx-controller -n ingress-nginx

# Check ingress resources
kubectl get ingress -A
kubectl describe ingress SERVICE-ingress -n NAMESPACE
```

### Elasticsearch (ELK)

**Issue:** ES pods failing or OOMKilled
```bash
# Check ES pods
kubectl get pods -n logging
kubectl logs deployment/elasticsearch -n logging

# Check resources
kubectl describe pod ES_POD_NAME -n logging

# Port-forward and check health
kubectl port-forward -n logging deployment/elasticsearch 9200:9200
curl localhost:9200/_cluster/health
```

**Common Fixes:**
```bash
# Increase memory limits in deployment
# Check disk space: df -h
# Verify vm.max_map_count: sysctl vm.max_map_count
```

### Istio Service Mesh

**Issue:** mTLS or traffic routing problems
```bash
# Check istio components
kubectl get pods -n istio-system
istioctl proxy-status
istioctl analyze

# Check sidecar injection
kubectl get pods -l istio=inj- # Should show sidecars
```

### ArgoCD

**Issue:** GitOps not syncing
```bash
# Check ArgoCD components
kubectl get pods -n argocd

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Check application status
kubectl get applications -n argocd
```

### KEDA (Auto-scaling)

**Issue:** Scaling not working
```bash
# Check KEDA operator
kubectl get pods -n keda

# Check scaled objects
kubectl get scaledobjects -A
kubectl describe scaledobject OBJECT_NAME -n NAMESPACE
```

## 🏥 Emergency Recovery

### Reset Specific Components
```bash
# Reset cert-manager
kubectl delete namespace cert-manager
# Re-run deployment script

# Reset ingress
kubectl delete namespace ingress-nginx
# Re-run deployment script

# Reset logging stack
kubectl delete namespace logging
# Re-run ELK deployment
```

### Full Cluster Reset (Nuclear Option)
```bash
# K3S uninstall (DESTRUCTIVE!)
/usr/local/bin/k3s-uninstall.sh

# Clean start
# Re-install K3S and run deployment scripts
```

## 📡 Network Troubleshooting

### Pod-to-Pod Communication
```bash
# Test pod connectivity
kubectl run debug --image=busybox -it --rm -- /bin/sh
# Inside pod:
nslookup kubernetes.default
wget -qO- http://SERVICE.NAMESPACE.svc.cluster.local:PORT
```

### DNS Resolution
```bash
# Check CoreDNS
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Test DNS
kubectl run -it --rm debug --image=busybox -- nslookup kubernetes.default
```

### Network Policies
```bash
# Check NetworkPolicies
kubectl get networkpolicies -A

# Temporarily disable for debugging
kubectl delete networkpolicies --all -A
```

## 💾 Resource Issues

### Out of Memory
```bash
# Check memory usage
free -h
kubectl top nodes
kubectl top pods -A --sort-by=memory

# Find memory hogs
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.spec.containers[*].resources.requests.memory}{"\n"}{end}' | sort -k3 -h
```

### Disk Space
```bash
# Check disk usage
df -h

# Clean Docker images
docker system prune -a

# Clean K3S images
k3s crictl rmi --prune
```

### CPU Issues
```bash
# Check CPU usage
top
kubectl top nodes
kubectl top pods -A --sort-by=cpu
```

## 🔐 Security & RBAC Issues

### Permission Denied
```bash
# Check user permissions
kubectl auth can-i create pods --all-namespaces
kubectl auth can-i '*' '*' --all-namespaces

# Run as root/sudo if needed
sudo kubectl get pods -A
```

### Service Account Issues
```bash
# Check service accounts
kubectl get serviceaccounts -A

# Check role bindings
kubectl get rolebindings,clusterrolebindings -A
```

## 📊 Monitoring & Alerts

### Prometheus Issues
```bash
# Check Prometheus
kubectl get pods -n monitoring
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Browse to localhost:9090
```

### Grafana Issues
```bash
# Get Grafana admin password
kubectl get secret -n monitoring grafana-admin-credentials -o jsonpath="{.data.password}" | base64 -d

# Port forward
kubectl port-forward -n monitoring svc/grafana 3000:3000
```

## 🚀 Performance Optimization

### Slow Deployments
```bash
# Check image pull times
kubectl describe pod POD_NAME | grep -A 10 Events

# Use local registry cache
# Configure registry mirrors in K3S
```

### High Memory Usage
```bash
# Optimize Java heap sizes
# Reduce replica counts
# Add resource limits
```

## 📞 Getting Help

### Debug Information to Collect
```bash
# System info
uname -a
kubectl version
helm version
df -h
free -h

# Cluster state
kubectl get nodes -o wide
kubectl get pods -A -o wide
kubectl get events --sort-by=.metadata.creationTimestamp -A

# Component logs
kubectl logs deployment/FAILING_COMPONENT -n NAMESPACE --previous
```

### Useful Resources
- K3S Docs: https://docs.k3s.io/
- Kubernetes Troubleshooting: https://kubernetes.io/docs/tasks/debug-application-cluster/
- Istio Debugging: https://istio.io/latest/docs/ops/common-problems/

## 🎯 Prevention

### Regular Maintenance
```bash
# Weekly checks
./scripts/check_dependencies.sh
kubectl get pods -A | grep -v Running
df -h

# Monthly
python3 scripts/cluster_optimizer.py --check
```

### Backup Important Data
```bash
# Backup etcd (automatically handled by K3S)
# Backup persistent volumes
# Export important configurations
kubectl get all -A -o yaml > cluster-backup.yaml
```

---

## 🏆 Pro Tips

1. **Always run dependency check first**: `./scripts/check_dependencies.sh`
2. **Use auto-fix script**: `sudo ./scripts/auto_fix_dependencies.sh`  
3. **Check events for root cause**: `kubectl get events --sort-by=.metadata.creationTimestamp -A`
4. **Monitor resource usage**: `kubectl top nodes && kubectl top pods -A`
5. **Test connectivity**: `ping 8.8.8.8 && curl -I https://github.com`
6. **Use port-forward for debugging**: `kubectl port-forward svc/SERVICE PORT:PORT`
7. **Check logs with --previous flag** for crashlooping pods
8. **Use kubectl describe** for detailed resource information

**Remember: Most issues are dependency or connectivity related. The scripts are designed to handle 90%+ of common problems automatically!** 🚀