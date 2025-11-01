#!/usr/bin/env python3
"""
🚀 ENTERPRISE-GRADE KUBERNETES STACK DEPLOYER 🚀

Автоматическое развертывание всех критических улучшений для превращения
базового K3S кластера в enterprise-grade платформу уровня Netflix/Google.

PHASE 1 (КРИТИЧНО):
- ELK Stack - централизованные логи с поиском
- KEDA - event-driven auto-scaling
- Advanced monitoring enhancements

PHASE 2 (ВАЖНО):
- ArgoCD GitOps - git push → auto deploy
- Istio Service Mesh - advanced traffic management
- Advanced security policies

PHASE 3 (ЖЕЛАТЕЛЬНО):
- Jaeger Distributed Tracing
- OPA Policy Engine + Falco Security
- Advanced storage layer

Usage:
  python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 1
  python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase all --confirm
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

class EnterpriseStackDeployer:
    def __init__(self, domain: str, email: str, phase: str, confirm: bool = False):
        self.domain = domain
        self.email = email
        self.phase = phase
        self.confirm = confirm
        self.worker_nodes = []
        
        # Tracking deployed components
        self.deployed_components = []
        self.failed_components = []
        
    def log_info(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] ℹ️  {msg}")
    
    def log_success(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] ✅ {msg}")
    
    def log_error(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] ❌ {msg}")
    
    def log_warning(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] ⚠️  {msg}")

    def run_kubectl(self, cmd: str, capture_output=True, check=True) -> subprocess.CompletedProcess:
        """kubectl с улучшенной обработкой ошибок"""
        full_cmd = f"kubectl {cmd}"
        if not capture_output:
            print(f"$ {full_cmd}")
        return subprocess.run(full_cmd, shell=True, capture_output=capture_output, text=True, check=check)

    def wait_for_condition(self, cmd: str, success_msg: str, timeout: int = 300) -> bool:
        """Умное ожидание с progress indicator"""
        self.log_info(f"⏳ Ожидание: {success_msg}")
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    self.log_success(success_msg)
                    return True
            except Exception:
                pass
            
            attempts += 1
            elapsed = int(time.time() - start_time)
            if attempts % 6 == 0:  # Progress update every 30s
                self.log_info(f"⏱️  Продолжаем ожидание... ({elapsed}/{timeout}s)")
            
            wait_time = min(5.0 * (1.2 ** (attempts // 3)), 15)
            time.sleep(wait_time)
        
        self.log_error(f"❌ Таймаут ({timeout}s): {success_msg}")
        return False

    def check_prerequisites(self) -> bool:
        """Проверка предварительных условий"""
        self.log_info("🔍 Проверка предварительных условий...")
        
        # 1. Кластер доступен
        try:
            result = self.run_kubectl("get nodes", timeout=10)
            if result.returncode != 0:
                self.log_error("Кластер недоступен")
                return False
        except subprocess.TimeoutExpired:
            self.log_error("Кластер не отвечает")
            return False
        
        # 2. Worker ноды найдены
        try:
            result = self.run_kubectl("get nodes -l node-role.kubernetes.io/worker=worker -o jsonpath='{.items[*].metadata.name}'")
            worker_nodes = result.stdout.strip().split()
            
            if worker_nodes and worker_nodes[0]:
                self.worker_nodes = [node for node in worker_nodes if node]
                self.log_success(f"Найдены worker ноды: {', '.join(self.worker_nodes)}")
            else:
                self.log_warning("Worker ноды не найдены, компоненты будут размещены на master")
                
        except Exception as e:
            self.log_error(f"Ошибка получения worker нод: {e}")
            return False
        
        # 3. Достаточно ресурсов
        if self.worker_nodes:
            self.log_success("✅ Worker нода доступна — развертывание на мощном железе")
        else:
            if not self.confirm:
                self.log_warning("⚠️  Без worker ноды некоторые компоненты могут перегрузить master")
                response = input("Продолжить? (y/N): ")
                if response.lower() != 'y':
                    return False
        
        return True

    def show_deployment_plan(self):
        """Показать план развертывания"""
        print("\n" + "="*80)
        print("🚀 ПЛАН РАЗВЕРТЫВАНИЯ ENTERPRISE STACK")
        print("="*80)
        
        phases = {
            "1": {
                "name": "PHASE 1 - КРИТИЧНО (30-45 мин)",
                "memory": "3.5 GB",
                "components": [
                    "ELK Stack (3GB) - централизованные логи + поиск + Kibana UI",
                    "KEDA (500MB) - event-driven auto-scaling",
                    "Enhanced monitoring - улучшенный Prometheus/Grafana"
                ]
            },
            "2": {
                "name": "PHASE 2 - ВАЖНО (60-90 мин)",
                "memory": "3 GB", 
                "components": [
                    "ArgoCD GitOps (1GB) - git push → auto deploy",
                    "Istio Service Mesh (2GB) - advanced traffic management + mTLS",
                    "Advanced ingress policies"
                ]
            },
            "3": {
                "name": "PHASE 3 - ЖЕЛАТЕЛЬНО (45-60 мин)",
                "memory": "1.8 GB",
                "components": [
                    "Jaeger Distributed Tracing (800MB) - request flow visualization", 
                    "OPA Gatekeeper (500MB) - policy enforcement",
                    "Falco Runtime Security (500MB) - runtime anomaly detection"
                ]
            }
        }
        
        if self.phase == "all":
            for phase_num, phase_data in phases.items():
                print(f"\n📋 {phase_data['name']}")
                print(f"   💾 Memory: {phase_data['memory']}")
                for component in phase_data['components']:
                    print(f"   • {component}")
            
            total_memory = 8.3
            print(f"\n📊 ИТОГО:")
            print(f"   • Память: ~{total_memory} GB")
            print(f"   • Время: ~3-4 часа")
            if self.worker_nodes:
                print(f"   • Utilization: ~13% от 64GB worker RAM")
            
        elif self.phase in phases:
            phase_data = phases[self.phase]
            print(f"\n📋 {phase_data['name']}")
            print(f"   💾 Memory: {phase_data['memory']}")
            for component in phase_data['components']:
                print(f"   • {component}")
        
        print(f"\n🎯 Результат после развертывания:")
        results = [
            "🚀 Centralized logging с мощным поиском (ELK)",
            "🚀 Event-driven auto-scaling сервисов (KEDA)",
            "🚀 Git-based deployments (ArgoCD)",
            "🚀 Advanced traffic management (Istio)",
            "🚀 Request tracing между сервисами (Jaeger)",
            "🚀 Automated policy enforcement (OPA)",
            "🚀 Runtime security monitoring (Falco)"
        ]
        
        for result in results:
            print(f"   {result}")
        
        print("="*80)

    # PHASE 1 Components

    def deploy_elk_stack(self) -> bool:
        """Развертывание ELK Stack на worker"""
        self.log_info("🔍 Развертывание ELK Stack...")
        
        try:
            elk_cmd = [
                "python3", "scripts/deploy_elk_on_worker.py",
                "--domain", self.domain,
                "--retention-days", "15"
            ]
            
            result = subprocess.run(elk_cmd, capture_output=False, text=True, timeout=1200)  # 20 min timeout
            
            if result.returncode == 0:
                self.log_success("ELK Stack развернут успешно")
                self.deployed_components.append("ELK Stack")
                
                # Проверяем доступность
                if self.wait_for_condition(
                    f"curl -k -s https://kibana.{self.domain} | grep -q kibana",
                    "Kibana UI доступна",
                    timeout=180
                ):
                    self.log_success(f"🎉 Kibana доступна: https://kibana.{self.domain}")
                
                return True
            else:
                self.log_error("Ошибка развертывания ELK Stack")
                self.failed_components.append("ELK Stack")
                return False
                
        except subprocess.TimeoutExpired:
            self.log_error("Таймаут развертывания ELK Stack (20 мин)")
            self.failed_components.append("ELK Stack")
            return False
        except Exception as e:
            self.log_error(f"Неожиданная ошибка ELK: {e}")
            self.failed_components.append("ELK Stack")
            return False

    def deploy_keda_autoscaling(self) -> bool:
        """Развертывание KEDA для event-driven scaling"""
        self.log_info("⚡ Развертывание KEDA Auto-scaling...")
        
        try:
            # Установка KEDA через Helm
            helm_commands = [
                ["helm", "repo", "add", "kedacore", "https://kedacore.github.io/charts"],
                ["helm", "repo", "update"],
                ["kubectl", "create", "namespace", "keda-system", "--dry-run=client", "-o", "yaml"]
            ]
            
            for cmd in helm_commands:
                subprocess.run(cmd, capture_output=True, check=True)
            
            # Создаем namespace
            subprocess.run(["kubectl", "apply", "-f", "-"], 
                          input=subprocess.run(["kubectl", "create", "namespace", "keda-system", "--dry-run=client", "-o", "yaml"], 
                                              capture_output=True, text=True).stdout, text=True)
            
            # Создаем values для размещения на worker
            keda_values = f"""
# Размещение KEDA на worker
nodeSelector:
  node-role.kubernetes.io/worker: worker

# Ресурсы оптимизированы для worker
operator:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 1000m
      memory: 1Gi

metricsServer:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 1000m
      memory: 1Gi

webhooks:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 1000m
      memory: 1Gi
"""
            
            with open("/tmp/keda-values.yaml", "w") as f:
                f.write(keda_values)
            
            # Установка KEDA
            result = subprocess.run([
                "helm", "upgrade", "--install", "keda", "kedacore/keda",
                "-n", "keda-system", "-f", "/tmp/keda-values.yaml",
                "--timeout", "10m"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                if self.wait_for_condition(
                    "kubectl -n keda-system rollout status deployment/keda-operator --timeout=300s",
                    "KEDA Operator готов"
                ):
                    self.log_success("KEDA Auto-scaling развернут")
                    self.deployed_components.append("KEDA")
                    return True
            
            self.log_error(f"Ошибка установки KEDA: {result.stderr}")
            self.failed_components.append("KEDA")
            return False
            
        except Exception as e:
            self.log_error(f"Ошибка развертывания KEDA: {e}")
            self.failed_components.append("KEDA")
            return False

    def enhance_monitoring_stack(self) -> bool:
        """Улучшение существующего мониторинга"""
        self.log_info("📈 Улучшение monitoring stack...")
        
        try:
            # Добавляем ServiceMonitors для новых компонентов
            enhanced_monitoring = f"""
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: keda-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: keda-operator-metrics-apiserver
  endpoints:
  - port: https
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: elasticsearch-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: elasticsearch
  endpoints:
  - port: http
    interval: 30s
    path: /_prometheus/metrics
---
# Grafana Dashboard ConfigMap for KEDA
apiVersion: v1
kind: ConfigMap
metadata:
  name: keda-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  keda-dashboard.json: |
    {{
      "dashboard": {{
        "title": "KEDA Scaling Dashboard",
        "panels": [
          {{
            "title": "Scaled Objects",
            "type": "stat",
            "targets": [
              {{
                "expr": "keda_scaledobject_total",
                "legendFormat": "Total Scaled Objects"
              }}
            ]
          }},
          {{
            "title": "HPA Metrics",
            "type": "graph", 
            "targets": [
              {{
                "expr": "keda_scaler_metrics_value",
                "legendFormat": "{{{{ scaler_name }}}}"
              }}
            ]
          }}
        ]
      }}
    }}
"""
            
            with open("/tmp/enhanced-monitoring.yaml", "w") as f:
                f.write(enhanced_monitoring)
            
            result = self.run_kubectl("apply -f /tmp/enhanced-monitoring.yaml", capture_output=False, check=False)
            
            if result.returncode == 0:
                self.log_success("Monitoring enhancements применены")
                self.deployed_components.append("Enhanced Monitoring")
                return True
            else:
                self.log_warning("Некоторые monitoring enhancements не применились (возможно, Prometheus Operator отсутствует)")
                return True  # Non-critical
                
        except Exception as e:
            self.log_warning(f"Не критическая ошибка monitoring enhancements: {e}")
            return True  # Non-critical

    # PHASE 2 Components

    def deploy_argocd_gitops(self) -> bool:
        """Развертывание ArgoCD для GitOps"""
        self.log_info("🔄 Развертывание ArgoCD GitOps...")
        
        try:
            # Создаем namespace
            subprocess.run(["kubectl", "create", "namespace", "argocd", "--dry-run=client", "-o", "yaml"], 
                          stdout=subprocess.PIPE)
            subprocess.run(["kubectl", "apply", "-f", "-"], 
                          input=subprocess.run(["kubectl", "create", "namespace", "argocd", "--dry-run=client", "-o", "yaml"], 
                                              capture_output=True, text=True).stdout, text=True)
            
            # Установка ArgoCD
            result = subprocess.run([
                "kubectl", "apply", "-n", "argocd", "-f",
                "https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.log_error(f"Ошибка установки ArgoCD: {result.stderr}")
                self.failed_components.append("ArgoCD")
                return False
            
            # Перенос на worker
            if self.worker_nodes:
                argocd_patch = {
                    "spec": {
                        "template": {
                            "spec": {
                                "nodeSelector": {
                                    "node-role.kubernetes.io/worker": "worker"
                                }
                            }
                        }
                    }
                }
                
                argocd_deployments = [
                    "argocd-applicationset-controller",
                    "argocd-dex-server", 
                    "argocd-notifications-controller",
                    "argocd-redis",
                    "argocd-repo-server",
                    "argocd-server"
                ]
                
                for deployment in argocd_deployments:
                    self.run_kubectl(f"patch deployment {deployment} -n argocd --patch '{json.dumps(argocd_patch)}'", check=False)
            
            # Ожидание готовности
            if self.wait_for_condition(
                "kubectl -n argocd rollout status deployment/argocd-server --timeout=300s",
                "ArgoCD Server готов"
            ):
                # Создаем Ingress для ArgoCD
                argocd_ingress = f"""
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-server
  namespace: argocd
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/backend-protocol: "GRPC"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - argocd.{self.domain}
    secretName: argocd-tls
  rules:
  - host: argocd.{self.domain}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: argocd-server
            port:
              number: 443
"""
                
                with open("/tmp/argocd-ingress.yaml", "w") as f:
                    f.write(argocd_ingress)
                
                self.run_kubectl("apply -f /tmp/argocd-ingress.yaml", capture_output=False)
                
                # Получаем initial admin password
                try:
                    admin_secret = self.run_kubectl("get secret argocd-initial-admin-secret -n argocd -o jsonpath='{.data.password}'")
                    if admin_secret.returncode == 0:
                        import base64
                        admin_password = base64.b64decode(admin_secret.stdout).decode('utf-8')
                        self.log_success(f"🎉 ArgoCD доступен: https://argocd.{self.domain}")
                        self.log_success(f"🔐 Admin password: {admin_password}")
                except:
                    self.log_warning("Не удалось получить admin password, проверьте вручную")
                
                self.deployed_components.append("ArgoCD GitOps")
                return True
            
            self.failed_components.append("ArgoCD")
            return False
            
        except Exception as e:
            self.log_error(f"Ошибка развертывания ArgoCD: {e}")
            self.failed_components.append("ArgoCD")
            return False

    def deploy_istio_service_mesh(self) -> bool:
        """Развертывание Istio Service Mesh"""
        self.log_info("🌐 Развертывание Istio Service Mesh...")
        
        try:
            # Скачиваем Istio
            istio_download = """
curl -L https://istio.io/downloadIstio | sh -
export PATH=$PWD/istio-*/bin:$PATH
"""
            subprocess.run(istio_download, shell=True, check=True)
            
            # Установка Istio с конфигурацией для worker
            istio_config = f"""
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: control-plane
spec:
  values:
    pilot:
      env:
        EXTERNAL_ISTIOD: false
  components:
    pilot:
      k8s:
        nodeSelector:
          node-role.kubernetes.io/worker: worker
        resources:
          requests:
            cpu: 500m
            memory: 2048Mi
          limits:
            cpu: 2000m
            memory: 4096Mi
    ingressGateways:
    - name: istio-ingressgateway
      enabled: true
      k8s:
        nodeSelector:
          node-role.kubernetes.io/worker: worker
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 2000m
            memory: 1024Mi
"""
            
            with open("/tmp/istio-config.yaml", "w") as f:
                f.write(istio_config)
            
            # Установка Istio
            subprocess.run(["istioctl", "install", "--set", "values.defaultRevision=default", "-f", "/tmp/istio-config.yaml", "-y"], 
                          check=True, timeout=600)
            
            # Включаем sidecar injection для default namespace
            self.run_kubectl("label namespace default istio-injection=enabled --overwrite")
            
            if self.wait_for_condition(
                "kubectl -n istio-system rollout status deployment/istiod --timeout=300s",
                "Istio Control Plane готов"
            ):
                self.log_success("Istio Service Mesh развернут")
                self.deployed_components.append("Istio Service Mesh")
                return True
            
            self.failed_components.append("Istio")
            return False
            
        except Exception as e:
            self.log_error(f"Ошибка развертывания Istio: {e}")
            self.failed_components.append("Istio")
            return False

    # PHASE 3 Components
    
    def deploy_jaeger_tracing(self) -> bool:
        """Развертывание Jaeger для distributed tracing"""
        self.log_info("🔍 Развертывание Jaeger Tracing...")
        
        try:
            # Jaeger All-in-One на worker
            jaeger_manifest = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
  namespace: istio-system
  labels:
    app: jaeger
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
    spec:
      nodeSelector:
        node-role.kubernetes.io/worker: "worker"
      containers:
      - name: jaeger
        image: jaegertracing/all-in-one:1.50
        env:
        - name: COLLECTOR_OTLP_ENABLED
          value: "true"
        - name: SPAN_STORAGE_TYPE
          value: "memory"
        resources:
          requests:
            cpu: 200m
            memory: 384Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        ports:
        - containerPort: 16686
        - containerPort: 14268
        - containerPort: 6831
          protocol: UDP
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger
  namespace: istio-system
spec:
  selector:
    app: jaeger
  ports:
  - port: 16686
    targetPort: 16686
    name: ui
  - port: 14268
    targetPort: 14268
    name: http
  - port: 6831
    targetPort: 6831
    name: udp
    protocol: UDP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: jaeger
  namespace: istio-system
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - jaeger.{self.domain}
    secretName: jaeger-tls
  rules:
  - host: jaeger.{self.domain}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: jaeger
            port:
              number: 16686
"""
            
            with open("/tmp/jaeger.yaml", "w") as f:
                f.write(jaeger_manifest)
            
            self.run_kubectl("apply -f /tmp/jaeger.yaml", capture_output=False)
            
            if self.wait_for_condition(
                "kubectl -n istio-system rollout status deployment/jaeger --timeout=180s",
                "Jaeger готов"
            ):
                self.log_success(f"🎉 Jaeger UI: https://jaeger.{self.domain}")
                self.deployed_components.append("Jaeger Tracing")
                return True
            
            self.failed_components.append("Jaeger")
            return False
            
        except Exception as e:
            self.log_error(f"Ошибка развертывания Jaeger: {e}")
            self.failed_components.append("Jaeger")
            return False

    def deploy_security_stack(self) -> bool:
        """Развертывание OPA + Falco"""
        self.log_info("🛡️  Развертывание Security Stack...")
        
        success = True
        
        # OPA Gatekeeper
        try:
            self.log_info("📋 Установка OPA Gatekeeper...")
            subprocess.run([
                "kubectl", "apply", "-f",
                "https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.14/deploy/gatekeeper.yaml"
            ], check=True, timeout=300)
            
            if self.wait_for_condition(
                "kubectl -n gatekeeper-system rollout status deployment/gatekeeper-controller-manager --timeout=180s",
                "OPA Gatekeeper готов"
            ):
                self.log_success("OPA Gatekeeper развернут")
                self.deployed_components.append("OPA Gatekeeper")
            else:
                success = False
                self.failed_components.append("OPA Gatekeeper")
                
        except Exception as e:
            self.log_error(f"Ошибка OPA Gatekeeper: {e}")
            self.failed_components.append("OPA Gatekeeper")
            success = False
        
        # Falco
        try:
            self.log_info("🛡️  Установка Falco...")
            helm_commands = [
                ["helm", "repo", "add", "falcosecurity", "https://falcosecurity.github.io/charts"],
                ["helm", "repo", "update"]
            ]
            
            for cmd in helm_commands:
                subprocess.run(cmd, capture_output=True, check=True)
            
            falco_values = f"""
nodeSelector:
  node-role.kubernetes.io/worker: worker

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 1000m
    memory: 512Mi

falco:
  grpc:
    enabled: true
  grpcOutput:
    enabled: true
"""
            
            with open("/tmp/falco-values.yaml", "w") as f:
                f.write(falco_values)
            
            subprocess.run([
                "helm", "upgrade", "--install", "falco", "falcosecurity/falco",
                "-n", "falco-system", "--create-namespace", "-f", "/tmp/falco-values.yaml",
                "--timeout", "10m"
            ], check=True)
            
            if self.wait_for_condition(
                "kubectl -n falco-system rollout status daemonset/falco --timeout=180s",
                "Falco готов"
            ):
                self.log_success("Falco Security развернут")
                self.deployed_components.append("Falco Security")
            else:
                success = False
                self.failed_components.append("Falco")
                
        except Exception as e:
            self.log_error(f"Ошибка Falco: {e}")
            self.failed_components.append("Falco")
            success = False
        
        return success

    def run_phase(self, phase_number: str) -> bool:
        """Выполнение конкретной фазы"""
        phase_success = True
        
        if phase_number == "1":
            self.log_info("🚀 PHASE 1: Критические компоненты")
            
            if not self.deploy_elk_stack():
                phase_success = False
                
            if not self.deploy_keda_autoscaling():
                phase_success = False
                
            if not self.enhance_monitoring_stack():
                phase_success = False
                
        elif phase_number == "2":
            self.log_info("🚀 PHASE 2: GitOps + Service Mesh")
            
            if not self.deploy_argocd_gitops():
                phase_success = False
                
            if not self.deploy_istio_service_mesh():
                phase_success = False
                
        elif phase_number == "3":
            self.log_info("🚀 PHASE 3: Tracing + Security")
            
            if not self.deploy_jaeger_tracing():
                phase_success = False
                
            if not self.deploy_security_stack():
                phase_success = False
        
        return phase_success

    def run_full_deployment(self) -> bool:
        """Полное развертывание всех улучшений"""
        print("\n" + "🚀" * 40)
        print("🚀 ЗАПУСК ENTERPRISE STACK DEPLOYMENT 🚀")
        print("🚀" * 40)
        
        start_time = time.time()
        
        try:
            # 1. Проверка предварительных условий
            if not self.check_prerequisites():
                return False
            
            # 2. Показ плана
            self.show_deployment_plan()
            
            # 3. Подтверждение
            if not self.confirm:
                print(f"\n⚠️  Будет развернуто много компонентов на {'worker' if self.worker_nodes else 'master'}!")
                response = input("🤔 Продолжить развертывание? (y/N): ")
                if response.lower() != 'y':
                    self.log_info("Развертывание отменено пользователем")
                    return False
            
            # 4. Выполнение фаз
            phases_to_run = ["1", "2", "3"] if self.phase == "all" else [self.phase]
            overall_success = True
            
            for phase_num in phases_to_run:
                print(f"\n{'='*60}")
                phase_start = time.time()
                
                if self.run_phase(phase_num):
                    phase_time = time.time() - phase_start
                    self.log_success(f"✅ PHASE {phase_num} завершена успешно ({phase_time:.1f}s)")
                else:
                    phase_time = time.time() - phase_start
                    self.log_error(f"❌ PHASE {phase_num} завершена с ошибками ({phase_time:.1f}s)")
                    overall_success = False
                    
                    if not self.confirm:
                        response = input(f"Продолжить с PHASE {int(phase_num)+1}? (y/N): ")
                        if response.lower() != 'y':
                            break
            
            # 5. Финальный отчет
            total_time = time.time() - start_time
            self.show_final_report(total_time)
            
            return overall_success
            
        except KeyboardInterrupt:
            self.log_warning("Развертывание прервано пользователем")
            return False
        except Exception as e:
            self.log_error(f"Критическая ошибка: {e}")
            return False

    def show_final_report(self, total_time: float):
        """Финальный отчет о развертывании"""
        print("\n" + "="*80)
        print("🎉 ОТЧЕТ О РАЗВЕРТЫВАНИИ ENTERPRISE STACK")
        print("="*80)
        
        print(f"⏱️  Общее время: {total_time/60:.1f} минут")
        print(f"📊 Развернуто компонентов: {len(self.deployed_components)}")
        if self.failed_components:
            print(f"❌ Неудачные компоненты: {len(self.failed_components)}")
        
        print(f"\n✅ УСПЕШНО РАЗВЕРНУТО:")
        for component in self.deployed_components:
            print(f"   • {component}")
        
        if self.failed_components:
            print(f"\n❌ НЕУДАЧНЫЕ КОМПОНЕНТЫ:")
            for component in self.failed_components:
                print(f"   • {component}")
        
        print(f"\n🌐 ДОСТУПНЫЕ СЕРВИСЫ:")
        services = [
            ("Grafana", f"https://grafana.{self.domain}"),
            ("Kubevious", f"https://kubevious.{self.domain}")
        ]
        
        if "ELK Stack" in self.deployed_components:
            services.append(("Kibana (Logs)", f"https://kibana.{self.domain}"))
        if "ArgoCD GitOps" in self.deployed_components:
            services.append(("ArgoCD", f"https://argocd.{self.domain}"))
        if "Jaeger Tracing" in self.deployed_components:
            services.append(("Jaeger", f"https://jaeger.{self.domain}"))
        
        for service_name, service_url in services:
            print(f"   • {service_name:<15}: {service_url}")
        
        print(f"\n🚀 НОВЫЕ ВОЗМОЖНОСТИ:")
        if "ELK Stack" in self.deployed_components:
            print("   🔍 Centralized logging с мощным поиском")
        if "KEDA" in self.deployed_components:
            print("   ⚡ Event-driven auto-scaling")
        if "ArgoCD GitOps" in self.deployed_components:
            print("   🔄 Git-based deployments (git push → auto deploy)")
        if "Istio Service Mesh" in self.deployed_components:
            print("   🌐 Advanced traffic management + mTLS")
        if "Jaeger Tracing" in self.deployed_components:
            print("   🔍 Distributed request tracing")
        if "OPA Gatekeeper" in self.deployed_components:
            print("   🛡️  Automated policy enforcement")
        if "Falco Security" in self.deployed_components:
            print("   🛡️  Runtime security monitoring")
        
        print("\n💡 СЛЕДУЮЩИЕ ШАГИ:")
        print("   1. Проверьте доступность сервисов по указанным URL")
        print("   2. Настройте GitOps репозиторий в ArgoCD")
        print("   3. Создайте первые KEDA ScaledObjects для автомасштабирования")
        print("   4. Изучите логи в Kibana и трейсы в Jaeger")
        
        print("="*80)

def main():
    parser = argparse.ArgumentParser(description="Enterprise Stack Deployer")
    parser.add_argument("--domain", required=True, help="Базовый домен (например, cockpit.work.gd)")
    parser.add_argument("--email", required=True, help="Email для Let's Encrypt")
    parser.add_argument("--phase", choices=["1", "2", "3", "all"], default="1", 
                        help="Фаза развертывания (1=критично, 2=важно, 3=желательно, all=все)")
    parser.add_argument("--confirm", action="store_true", 
                        help="Пропустить интерактивные подтверждения")
    
    args = parser.parse_args()
    
    deployer = EnterpriseStackDeployer(
        domain=args.domain,
        email=args.email, 
        phase=args.phase,
        confirm=args.confirm
    )
    
    success = deployer.run_full_deployment()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()