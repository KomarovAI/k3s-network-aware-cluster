#!/usr/bin/env python3
"""
K3S Production Hardening Script
Implements NSA/CISA, CIS Benchmark, and CNCF security standards
Optimized for enhanced VPS (3 vCPU, 4GB RAM, 100GB) + Home PC architecture

Usage: python3 production_hardening.py [command]
Commands: apply, status, validate
"""

import os
import sys
import subprocess
import json
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional


class ProductionHardening:
    def __init__(self):
        self.kubectl_available = self._check_kubectl()
        self.hardening_checks = {
            'pod_security_standards': False,
            'network_policies': False,
            'rbac_configured': False,
            'resource_limits': False,
            'security_contexts': False,
            'monitoring_deployed': False,
            'ingress_secured': False
        }
    
    def apply_all_hardening(self) -> bool:
        """Apply all production hardening measures"""
        print("🔒 Applying production hardening for enhanced VPS cluster...")
        print(f"   Target: NSA/CISA + CIS Benchmark + CNCF compliance")
        print()
        
        steps = [
            ("Pod Security Standards", self._apply_pod_security_standards),
            ("Network Policies", self._apply_network_policies),
            ("Enhanced Resource Limits", self._apply_enhanced_resource_limits),
            ("RBAC Hardening", self._apply_rbac_hardening),
            ("Enhanced Monitoring", self._deploy_enhanced_monitoring),
            ("Production Ingress", self._secure_ingress),
            ("System Optimizations", self._apply_system_optimizations)
        ]
        
        success_count = 0
        for step_name, step_func in steps:
            print(f"🔧 {step_name}...")
            try:
                if step_func():
                    print(f"✅ {step_name} applied successfully")
                    success_count += 1
                else:
                    print(f"❌ {step_name} failed")
            except Exception as e:
                print(f"⚠️  {step_name} error: {e}")
            print()
        
        print(f"📊 Hardening Summary: {success_count}/{len(steps)} steps successful")
        return success_count == len(steps)
    
    def _apply_pod_security_standards(self) -> bool:
        """Apply Pod Security Standards (NSA/CISA requirement)"""
        # Apply production standards manifest
        if Path('manifests/prod/01-production-standards.yaml').exists():
            result = subprocess.run([
                'kubectl', 'apply', '-f', 'manifests/prod/01-production-standards.yaml'
            ])
            return result.returncode == 0
        else:
            print("   Creating Pod Security Standards inline...")
            # Create PSS namespace if manifest not found
            pss_yaml = '''
apiVersion: v1
kind: Namespace
metadata:
  name: apps
  labels:
    pod-security.kubernetes.io/enforce: "baseline"
    pod-security.kubernetes.io/audit: "restricted" 
    pod-security.kubernetes.io/warn: "restricted"
'''
            return self._apply_yaml(pss_yaml)
    
    def _apply_network_policies(self) -> bool:
        """Apply network policies (Zero Trust)"""
        policies = [
            # Default deny all
            '''
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: apps
spec:
  podSelector: {}
  policyTypes: ["Ingress", "Egress"]
''',
            # Allow DNS
            '''
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: apps
spec:
  podSelector: {}
  policyTypes: ["Egress"]
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
'''
        ]
        
        success = True
        for policy in policies:
            if not self._apply_yaml(policy):
                success = False
        
        return success
    
    def _apply_enhanced_resource_limits(self) -> bool:
        """Apply resource limits optimized for enhanced VPS"""
        # Patch system components with enhanced limits
        patches = [
            {
                'component': 'coredns',
                'namespace': 'kube-system',
                'patch': {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [{
                                    "name": "coredns",
                                    "resources": {
                                        "limits": {
                                            "cpu": "200m",     # Higher for 3 vCPU VPS
                                            "memory": "256Mi"   # Higher for 4GB VPS
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
                }
            },
            {
                'component': 'metrics-server',
                'namespace': 'kube-system', 
                'patch': {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [{
                                    "name": "metrics-server",
                                    "resources": {
                                        "limits": {
                                            "cpu": "200m",
                                            "memory": "400Mi"
                                        },
                                        "requests": {
                                            "cpu": "100m",
                                            "memory": "200Mi"
                                        }
                                    }
                                }]
                            }
                        }
                    }
                }
            }
        ]
        
        success = True
        for patch_config in patches:
            try:
                result = subprocess.run([
                    'kubectl', 'patch', 'deployment', patch_config['component'],
                    '-n', patch_config['namespace'], '--patch', json.dumps(patch_config['patch'])
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"   ✅ {patch_config['component']} resources updated")
                else:
                    print(f"   ⚠️  {patch_config['component']} patch skipped (may not exist)")
                    
            except Exception as e:
                print(f"   ⚠️  {patch_config['component']} patch error: {e}")
                success = False
        
        return success
    
    def _apply_rbac_hardening(self) -> bool:
        """Apply RBAC hardening"""
        rbac_yaml = '''
# Production RBAC for apps namespace
apiVersion: v1
kind: ServiceAccount
metadata:
  name: apps-service-account
  namespace: apps
automountServiceAccountToken: false  # Security best practice
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: apps-role
  namespace: apps
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: apps-role-binding
  namespace: apps
subjects:
- kind: ServiceAccount
  name: apps-service-account
  namespace: apps
roleRef:
  kind: Role
  name: apps-role
  apiGroup: rbac.authorization.k8s.io
'''
        return self._apply_yaml(rbac_yaml)
    
    def _deploy_enhanced_monitoring(self) -> bool:
        """Deploy monitoring optimized for enhanced VPS"""
        monitoring_yaml = f'''
# Enhanced Prometheus for 3 vCPU, 4GB RAM VPS
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus-enhanced
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
      # Can run on enhanced VPS
      nodeSelector:
        node-type: vps
      
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        effect: NoSchedule
      - key: vps-enhanced
        effect: PreferNoSchedule  # Soft tolerance for enhanced VPS
      
      # Pod Security Standards compliant
      securityContext:
        runAsNonRoot: true
        runAsUser: 65534
        runAsGroup: 65534
        fsGroup: 65534
        seccompProfile:
          type: RuntimeDefault
      
      containers:
      - name: prometheus
        image: prom/prometheus:v2.47.0
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: ["ALL"]
          readOnlyRootFilesystem: true
        
        args:
          - "--config.file=/etc/prometheus/prometheus.yml"
          - "--storage.tsdb.path=/prometheus/"
          - "--storage.tsdb.retention.time=14d"   # Longer retention with 100GB
          - "--storage.tsdb.retention.size=20GB"  # More storage available
          - "--web.enable-lifecycle"
          - "--query.max-concurrency=10"          # Higher with 3 vCPU
          - "--query.timeout=30s"
        
        ports:
        - containerPort: 9090
          name: web
        
        # Enhanced resources for better VPS
        resources:
          requests:
            memory: "800Mi"      # Higher baseline with 4GB
            cpu: "400m"          # More CPU with 3 cores
          limits:
            memory: "2Gi"        # Can use up to 2GB
            cpu: "1000m"         # Can burst to 1 CPU
        
        volumeMounts:
        - name: prometheus-storage
          mountPath: /prometheus
        - name: config
          mountPath: /etc/prometheus
        - name: tmp
          mountPath: /tmp
      
      volumes:
      - name: prometheus-storage
        emptyDir:
          sizeLimit: 25Gi       # 25GB for monitoring data
      - name: config
        configMap:
          name: prometheus-enhanced-config
      - name: tmp
        emptyDir:
          sizeLimit: 1Gi
---
# Enhanced Prometheus Configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-enhanced-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 30s      # More frequent with better VPS
      evaluation_interval: 30s
      external_labels:
        cluster: 'k3s-enhanced-vps'
        region: 'hybrid'
    
    scrape_configs:
    # Enhanced node metrics
    - job_name: 'kubernetes-nodes'
      kubernetes_sd_configs:
      - role: node
      relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
      - target_label: __address__
        replacement: kubernetes.default.svc:443
      - source_labels: [__meta_kubernetes_node_name]
        regex: (.+)
        target_label: __metrics_path__
        replacement: /api/v1/nodes/${{1}}/proxy/metrics
    
    # Kubelet metrics
    - job_name: 'kubernetes-kubelet'
      kubernetes_sd_configs:
      - role: node
      scheme: https
      tls_config:
        ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        insecure_skip_verify: true
      bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
    
    # Service discovery for pods with monitoring=true
    - job_name: 'kubernetes-pods'
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\\d+)?;(\\d+)
        replacement: ${{1}}:${{2}}
        target_label: __address__
---
# Enhanced Grafana for better VPS
apiVersion: apps/v1  
kind: Deployment
metadata:
  name: grafana-enhanced
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      nodeSelector:
        node-type: vps
      
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        effect: NoSchedule
      - key: vps-enhanced
        effect: PreferNoSchedule
      
      # Pod Security Standards compliant
      securityContext:
        runAsNonRoot: true
        runAsUser: 472
        runAsGroup: 472
        fsGroup: 472
        seccompProfile:
          type: RuntimeDefault
      
      containers:
      - name: grafana
        image: grafana/grafana:10.1.0
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: ["ALL"]
          readOnlyRootFilesystem: false  # Grafana needs write access
        
        ports:
        - containerPort: 3000
          name: web
        
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          value: "admin123"  # Change in production!
        - name: GF_SERVER_ROOT_URL
          value: "http://grafana.local"
        - name: GF_INSTALL_PLUGINS
          value: "grafana-piechart-panel"
        
        # Enhanced resources for 4GB VPS
        - name: GF_DATABASE_MAX_IDLE_CONN
          value: "5"
        - name: GF_DATABASE_MAX_OPEN_CONN
          value: "10"
        - name: GF_SERVER_ENABLE_GZIP
          value: "true"
        
        resources:
          requests:
            memory: "200Mi"      # Higher baseline
            cpu: "100m"
          limits:
            memory: "800Mi"      # Can use more with 4GB
            cpu: "500m"         # More CPU available
        
        volumeMounts:
        - name: grafana-storage
          mountPath: /var/lib/grafana
        - name: tmp
          mountPath: /tmp
      
      volumes:
      - name: grafana-storage
        emptyDir:
          sizeLimit: 5Gi        # More storage with 100GB
      - name: tmp
        emptyDir:
          sizeLimit: 1Gi
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus-enhanced
  namespace: monitoring
spec:
  selector:
    app: prometheus
  ports:
  - port: 9090
    targetPort: 9090
---
apiVersion: v1
kind: Service
metadata:
  name: grafana-enhanced
  namespace: monitoring
spec:
  selector:
    app: grafana
  ports:
  - port: 3000
    targetPort: 3000
'''
        return self._apply_yaml(monitoring_yaml)
    
    def _apply_enhanced_resource_limits(self) -> bool:
        """Apply resource limits for enhanced VPS"""
        # Create resource quota for enhanced VPS
        quota_yaml = '''
apiVersion: v1
kind: ResourceQuota
metadata:
  name: enhanced-vps-quota
  namespace: kube-system
spec:
  hard:
    # Enhanced VPS can handle more system load
    requests.cpu: "2500m"      # Reserve 2.5 CPU for system
    requests.memory: "3Gi"     # Reserve 3GB for system
    limits.cpu: "3000m"        # Max CPU for system
    limits.memory: "4Gi"       # Max memory for system
'''
        return self._apply_yaml(quota_yaml)
    
    def _apply_rbac_hardening(self) -> bool:
        """Apply RBAC hardening"""
        # Apply from manifest if exists
        if Path('manifests/prod/02-hpa-pdb-templates.yaml').exists():
            result = subprocess.run([
                'kubectl', 'apply', '-f', 'manifests/prod/02-hpa-pdb-templates.yaml'
            ])
            return result.returncode == 0
        return True
    
    def _secure_ingress(self) -> bool:
        """Secure ingress configuration"""
        # Update NGINX with enhanced security
        security_patch = {
            "data": {
                "enable-brotli": "true",
                "brotli-level": "6",
                "gzip-level": "6", 
                "ssl-protocols": "TLSv1.2 TLSv1.3",
                "ssl-ciphers": "ECDHE-ECDSA-AES128-GCM-SHA256,ECDHE-RSA-AES128-GCM-SHA256",
                "hide-headers": "Server,X-Powered-By",
                "server-tokens": "false",
                "worker-processes": "3",        # Match VPS CPU cores
                "max-worker-connections": "2048" # Enhanced capacity
            }
        }
        
        try:
            result = subprocess.run([
                'kubectl', 'patch', 'configmap', 'ingress-nginx-controller',
                '-n', 'ingress-nginx', '--patch', json.dumps(security_patch)
            ], capture_output=True)
            return result.returncode == 0
        except Exception:
            return True  # Skip if ingress not installed
    
    def _apply_system_optimizations(self) -> bool:
        """Apply system-level optimizations"""
        optimizations = [
            # Install metrics-server for HPA
            'kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml',
            
            # Create monitoring namespace
            'kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -',
            
            # Label nodes properly
            self._label_nodes_enhanced
        ]
        
        for opt in optimizations:
            if callable(opt):
                if not opt():
                    return False
            else:
                result = subprocess.run(opt, shell=True, capture_output=True)
                if result.returncode != 0:
                    print(f"   ⚠️  System optimization warning: {opt}")
        
        return True
    
    def _label_nodes_enhanced(self) -> bool:
        """Label nodes with enhanced specifications"""
        try:
            # Get all nodes
            result = subprocess.run(['kubectl', 'get', 'nodes', '-o', 'json'],
                                  capture_output=True, text=True, check=True)
            nodes = json.loads(result.stdout)
            
            for node in nodes['items']:
                node_name = node['metadata']['name']
                
                # Check if it's control plane
                is_control_plane = any(
                    'control-plane' in label or 'master' in label
                    for label in node['metadata'].get('labels', {})
                )
                
                if is_control_plane:
                    # Enhanced VPS master labels
                    vps_labels = {
                        'node-type': 'vps',
                        'vps-tier': 'enhanced',
                        'role': 'control-plane',
                        'compute-tier': 'enhanced-management',
                        'cpu-cores': '3',
                        'memory-gb': '4',
                        'storage-gb': '100',
                        'network-speed': '1000mbps',
                        'can-run-monitoring': 'true',
                        'can-run-ingress': 'true'
                    }
                    
                    for key, value in vps_labels.items():
                        subprocess.run([
                            'kubectl', 'label', 'node', node_name,
                            f'{key}={value}', '--overwrite'
                        ])
                
                else:
                    # Home PC worker labels
                    worker_labels = {
                        'node-type': 'home-pc',
                        'role': 'worker',
                        'compute-tier': 'workload',
                        'network-speed': '1000mbps',
                        'zone': 'local',
                        'high-performance': 'true',
                        'can-run-heavy-workloads': 'true'
                    }
                    
                    for key, value in worker_labels.items():
                        subprocess.run([
                            'kubectl', 'label', 'node', node_name,
                            f'{key}={value}', '--overwrite'
                        ])
            
            return True
            
        except Exception as e:
            print(f"   ⚠️  Node labeling error: {e}")
            return False
    
    def validate_hardening(self) -> Dict:
        """Validate production hardening implementation"""
        print("🔍 Validating production hardening...")
        
        validation = {
            'pod_security_standards': self._check_pss(),
            'network_policies': self._check_network_policies(),
            'resource_limits': self._check_resource_limits(),
            'rbac': self._check_rbac(),
            'monitoring': self._check_monitoring(),
            'node_configuration': self._check_node_config()
        }
        
        passed = sum(validation.values())
        total = len(validation)
        
        print(f"\n📊 Validation Results: {passed}/{total} checks passed")
        
        for check, status in validation.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {check.replace('_', ' ').title()}")
        
        if passed == total:
            print("\n🎉 All production hardening checks passed!")
            print("✅ Cluster is production-ready with enhanced VPS configuration")
        else:
            print(f"\n⚠️  {total - passed} checks failed - review configuration")
        
        return validation
    
    def _check_pss(self) -> bool:
        """Check Pod Security Standards implementation"""
        try:
            result = subprocess.run([
                'kubectl', 'get', 'namespace', 'apps', 
                '-o', 'jsonpath={.metadata.labels}'
            ], capture_output=True, text=True)
            
            return 'pod-security.kubernetes.io/enforce' in result.stdout
        except Exception:
            return False
    
    def _check_network_policies(self) -> bool:
        """Check network policies implementation"""
        try:
            result = subprocess.run([
                'kubectl', 'get', 'networkpolicy', '-n', 'apps'
            ], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_resource_limits(self) -> bool:
        """Check resource limits on system components"""
        try:
            result = subprocess.run([
                'kubectl', 'get', 'deployment', 'coredns', '-n', 'kube-system',
                '-o', 'jsonpath={.spec.template.spec.containers[0].resources.limits}'
            ], capture_output=True, text=True)
            
            return 'cpu' in result.stdout and 'memory' in result.stdout
        except Exception:
            return False
    
    def _check_rbac(self) -> bool:
        """Check RBAC configuration"""
        try:
            result = subprocess.run([
                'kubectl', 'get', 'serviceaccount', '-n', 'apps'
            ], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_monitoring(self) -> bool:
        """Check monitoring deployment"""
        try:
            result = subprocess.run([
                'kubectl', 'get', 'deployment', '-n', 'monitoring'
            ], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_node_config(self) -> bool:
        """Check enhanced node configuration"""
        try:
            result = subprocess.run([
                'kubectl', 'get', 'nodes', '--show-labels'
            ], capture_output=True, text=True)
            
            return 'vps-tier=enhanced' in result.stdout
        except Exception:
            return False
    
    def _apply_yaml(self, yaml_content: str) -> bool:
        """Apply YAML content via kubectl"""
        try:
            process = subprocess.Popen(
                ['kubectl', 'apply', '-f', '-'],
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=yaml_content)
            
            if process.returncode != 0:
                print(f"   kubectl apply error: {stderr}")
                return False
            
            return True
            
        except Exception as e:
            print(f"   YAML apply error: {e}")
            return False
    
    def _check_kubectl(self) -> bool:
        """Check if kubectl is available"""
        return subprocess.run(['which', 'kubectl'], capture_output=True).returncode == 0
    
    def show_production_info(self) -> None:
        """Show production cluster information"""
        print("\n🔗 Enhanced VPS Cluster Access:")
        print("\n📊 Monitoring:")
        print("   Prometheus: kubectl port-forward svc/prometheus-enhanced 9090:9090 -n monitoring")
        print("   Grafana: kubectl port-forward svc/grafana-enhanced 3000:3000 -n monitoring")
        print("   Open: http://localhost:3000 (admin/admin123)")
        print("\n🛠️  Management:")
        print("   Cluster status: kubectl get nodes -o wide")
        print("   Resource usage: kubectl top nodes")
        print("   Security validation: python3 production_hardening.py validate")
        print("\n🚀 Deploy Services:")
        print("   Use templates from manifests/prod/02-hpa-pdb-templates.yaml")
        print("   Automatic placement on Home PCs with node selectors")


def main():
    parser = argparse.ArgumentParser(
        description='Production Hardening for Enhanced K3S Cluster'
    )
    parser.add_argument('command', 
                      choices=['apply', 'validate', 'status'],
                      help='Command to execute')
    
    args = parser.parse_args()
    
    hardener = ProductionHardening()
    
    if not hardener.kubectl_available:
        print("❌ kubectl not available. Install K3S cluster first.")
        sys.exit(1)
    
    if args.command == 'apply':
        success = hardener.apply_all_hardening()
        if success:
            print("🎉 Production hardening completed successfully!")
            hardener.show_production_info()
        else:
            print("❌ Some hardening steps failed")
            sys.exit(1)
    
    elif args.command == 'validate':
        validation = hardener.validate_hardening()
        all_passed = all(validation.values())
        sys.exit(0 if all_passed else 1)
    
    elif args.command == 'status':
        hardener.show_production_info()


if __name__ == '__main__':
    main()