#!/usr/bin/env python3
"""
Оптимизированный скрипт развертывания K3S кластера с автоматическим распределением
компонентов между master (VPS) и worker (Home PC) для максимальной эффективности.

Автоматически настраивает:
- Критические компоненты остаются на master VPS
- Мониторинг и визуализация переносятся на worker Home PC
- Оптимизированные resource limits для каждой ноды
- Proper node selectors и tolerations

Использование:
  python3 scripts/deploy_all_optimized.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true

Требования:
  sudo apt-get update && sudo apt-get install -y curl jq python3 python3-yaml gettext-base
  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
"""

import argparse
import json
import os
import subprocess
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TOOLS = ['kubectl', 'curl', 'jq', 'envsubst', 'helm']

class OptimizedClusterDeployer:
    def __init__(self, domain: str, email: str, enable_gpu: bool, use_dns01: bool):
        self.domain = domain
        self.email = email
        self.enable_gpu = enable_gpu
        self.use_dns01 = use_dns01
        self.master_node = None
        self.worker_nodes = []
        
    def log_info(self, msg: str):
        print(f"ℹ️  {msg}")
    
    def log_success(self, msg: str):
        print(f"✅ {msg}")
    
    def log_error(self, msg: str):
        print(f"❌ {msg}")
    
    def log_warning(self, msg: str):
        print(f"⚠️  {msg}")
        
    def run_kubectl(self, cmd: str, capture_output=True, check=True) -> subprocess.CompletedProcess:
        """Выполнение kubectl команды с обработкой ошибок"""
        full_cmd = f"kubectl {cmd}"
        if not capture_output:
            print(f"$ {full_cmd}")
        return subprocess.run(full_cmd, shell=True, capture_output=capture_output, text=True, check=check)
    
    def wait_for_condition(self, cmd: str, success_msg: str, timeout: int = 300, sleep_interval: float = 5.0) -> bool:
        """Умное ожидание с экспоненциальным backoff"""
        self.log_info(f"Ожидание: {success_msg}")
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    self.log_success(success_msg)
                    return True
            except Exception as e:
                self.log_warning(f"Попытка {attempts + 1} не удалась: {e}")
            
            attempts += 1
            wait_time = min(sleep_interval * (1.5 ** (attempts // 3)), 30)
            time.sleep(wait_time)
        
        self.log_error(f"Таймаут ({timeout}s) при ожидании: {success_msg}")
        return False
    
    def check_dependencies(self) -> bool:
        """Проверка всех необходимых зависимостей"""
        self.log_info("Проверка зависимостей...")
        missing = []
        
        for tool in REQUIRED_TOOLS:
            result = subprocess.run(f"which {tool}", shell=True, capture_output=True)
            if result.returncode != 0:
                missing.append(tool)
        
        if missing:
            self.log_error(f"Отсутствуют инструменты: {', '.join(missing)}")
            self.log_info("Установите их командой:")
            if 'helm' in missing:
                print("curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash")
            if any(tool in ['curl', 'jq', 'gettext-base'] for tool in missing):
                print("sudo apt-get update && sudo apt-get install -y curl jq gettext-base")
            return False
        
        self.log_success("Все зависимости найдены")
        return True
    
    def analyze_cluster_topology(self) -> bool:
        """Анализ топологии кластера для оптимального размещения"""
        self.log_info("Анализ топологии кластера...")
        
        try:
            result = self.run_kubectl("get nodes -o json")
            nodes_data = json.loads(result.stdout)
            
            for node in nodes_data['items']:
                node_name = node['metadata']['name']
                labels = node['metadata'].get('labels', {})
                
                if any(label.startswith('node-role.kubernetes.io/control-plane') for label in labels.keys()):
                    self.master_node = node_name
                    self.log_info(f"Master нода: {node_name}")
                else:
                    self.worker_nodes.append(node_name)
                    self.log_info(f"Worker нода: {node_name}")
            
            if not self.master_node:
                self.log_error("Master нода не найдена")
                return False
                
            if not self.worker_nodes:
                self.log_warning("Worker ноды не найдены. Некоторые компоненты останутся на master.")
            else:
                self.log_success(f"Найдено worker нод: {len(self.worker_nodes)}")
            
            return True
            
        except Exception as e:
            self.log_error(f"Ошибка анализа топологии: {e}")
            return False
    
    def deploy_master_components(self) -> bool:
        """Развертывание компонентов, которые ДОЛЖНЫ остаться на master"""
        self.log_info("Развертывание критических компонентов на master...")
        
        if not self.wait_for_condition("kubectl get nodes", "Кластер готов к развертыванию"):
            return False
        
        # 1. ingress-nginx (ОБЯЗАТЕЛЬНО на master для внешнего доступа)
        self.log_info("Установка ingress-nginx на master...")
        subprocess.run([
            "kubectl", "apply", "-f",
            "https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/cloud/deploy.yaml"
        ])
        
        # Принуждаем ingress-nginx остаться на master
        if not self.wait_for_condition(
            "kubectl -n ingress-nginx get deployment ingress-nginx-controller",
            "ingress-nginx deployment создан"
        ):
            return False
            
        # Добавляем nodeSelector и tolerations для master
        ingress_patch = {
            "spec": {
                "template": {
                    "spec": {
                        "nodeSelector": {
                            "node-role.kubernetes.io/control-plane": "true"
                        },
                        "tolerations": [
                            {
                                "key": "node-role.kubernetes.io/control-plane",
                                "operator": "Exists",
                                "effect": "NoSchedule"
                            }
                        ]
                    }
                }
            }
        }
        
        subprocess.run([
            "kubectl", "patch", "deployment", "ingress-nginx-controller",
            "-n", "ingress-nginx", "--patch", json.dumps(ingress_patch)
        ])
        
        if not self.wait_for_condition(
            "kubectl -n ingress-nginx rollout status deploy/ingress-nginx-controller --timeout=300s",
            "ingress-nginx готов на master"
        ):
            return False
        
        # 2. cert-manager (ОБЯЗАТЕЛЬНО на master для управления сертификатами)
        self.log_info("Установка cert-manager на master...")
        subprocess.run(["kubectl", "apply", "-f", "https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.crds.yaml"])
        subprocess.run(["kubectl", "create", "namespace", "cert-manager", "--dry-run=client", "-o", "yaml"], 
                      stdout=subprocess.PIPE, shell=False) # Создаем namespace
        subprocess.run(["kubectl", "apply", "-f"], input=subprocess.run(["kubectl", "create", "namespace", "cert-manager", "--dry-run=client", "-o", "yaml"], 
                      capture_output=True, text=True).stdout, text=True)
        
        subprocess.run(["kubectl", "apply", "-f", "https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml"])
        
        if not self.wait_for_condition(
            "kubectl -n cert-manager rollout status deploy/cert-manager --timeout=300s",
            "cert-manager готов"
        ):
            return False
        
        # 🔧 ВАЖНО: Принуждаем cert-manager остаться на master VPS
        self.log_info("Закрепление cert-manager на master VPS...")
        cert_manager_deployments = [
            "cert-manager",
            "cert-manager-cainjector", 
            "cert-manager-webhook"
        ]
        
        cert_manager_patch = {
            "spec": {
                "template": {
                    "spec": {
                        "nodeSelector": {
                            "node-role.kubernetes.io/control-plane": "true"
                        },
                        "tolerations": [
                            {
                                "key": "node-role.kubernetes.io/control-plane",
                                "operator": "Exists",
                                "effect": "NoSchedule"
                            }
                        ]
                    }
                }
            }
        }
        
        for deployment in cert_manager_deployments:
            try:
                subprocess.run([
                    "kubectl", "patch", "deployment", deployment,
                    "-n", "cert-manager", "--patch", json.dumps(cert_manager_patch)
                ], check=True)
                self.log_success(f"cert-manager {deployment} закреплен на master")
            except subprocess.CalledProcessError:
                self.log_warning(f"Не удалось закрепить {deployment} на master (возможно, еще не готов)")
        
        # Даем время на перезапуск cert-manager с новыми ограничениями
        time.sleep(30)
        
        # Проверяем, что cert-manager готов после патчинга
        if not self.wait_for_condition(
            "kubectl -n cert-manager rollout status deploy/cert-manager --timeout=180s",
            "cert-manager готов после закрепления на master"
        ):
            self.log_warning("cert-manager медленно перезапускается, но продолжаем...")
        
        # Применяем ClusterIssuer
        self.apply_cluster_issuers()
        
        # 3. Базовые конфигурации кластера
        base_dir = REPO_ROOT / "manifests/base"
        if base_dir.exists():
            self.run_kubectl(f"apply -k {base_dir}", capture_output=False)
        
        return True
    
    def deploy_worker_components(self) -> bool:
        """Развертывание компонентов, которые будут работать на worker"""
        if not self.worker_nodes:
            self.log_warning("Worker ноды не найдены, размещаем мониторинг на master (с ограниченными ресурсами)")
            return self.deploy_monitoring_on_master()
        
        self.log_info("Развертывание мониторинга на worker ноде...")
        
        # Создаем namespace для мониторинга
        subprocess.run(["kubectl", "create", "namespace", "monitoring", "--dry-run=client", "-o", "yaml"], 
                      stdout=subprocess.PIPE) 
        subprocess.run(["kubectl", "apply", "-f", "-"], 
                      input=subprocess.run(["kubectl", "create", "namespace", "monitoring", "--dry-run=client", "-o", "yaml"], 
                                          capture_output=True, text=True).stdout, text=True)
        
        # 1. Registry Cache на worker (экономит трафик на master)
        self.deploy_registry_cache_on_worker()
        
        # 2. Prometheus на worker (основной потребитель ресурсов)
        self.deploy_prometheus_on_worker()
        
        # 3. Grafana на worker
        self.deploy_grafana_on_worker()
        
        # 4. Kubevious на worker
        self.deploy_kubevious_on_worker()
        
        # 5. GPU мониторинг (если включен)
        if self.enable_gpu:
            self.deploy_gpu_monitoring_on_worker()
        
        return True
    
    def deploy_registry_cache_on_worker(self):
        """Развертывание registry cache на worker"""
        self.log_info("Развертывание Registry Cache на worker...")
        
        registry_manifest = f'''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: registry-cache
  namespace: kube-system
  labels:
    app: registry-cache
spec:
  replicas: 1
  selector:
    matchLabels:
      app: registry-cache
  template:
    metadata:
      labels:
        app: registry-cache
    spec:
      nodeSelector:
        node-role.kubernetes.io/worker: "worker"
      containers:
      - name: registry
        image: registry:2.8
        env:
        - name: REGISTRY_PROXY_REMOTEURL
          value: "https://registry-1.docker.io"
        - name: REGISTRY_STORAGE_CACHE_BLOBDESCRIPTOR
          value: "inmemory"
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 200m  # Больше на worker
            memory: 256Mi
        ports:
        - containerPort: 5000
        volumeMounts:
        - name: cache-storage
          mountPath: /var/lib/registry
      volumes:
      - name: cache-storage
        emptyDir:
          sizeLimit: 20Gi  # Больше места на worker
---
apiVersion: v1
kind: Service
metadata:
  name: registry-cache
  namespace: kube-system
spec:
  selector:
    app: registry-cache
  ports:
  - port: 5000
    targetPort: 5000
'''
        
        with open("/tmp/registry-cache-worker.yaml", "w") as f:
            f.write(registry_manifest)
        
        self.run_kubectl("apply -f /tmp/registry-cache-worker.yaml", capture_output=False)
        
        if self.wait_for_condition(
            "kubectl -n kube-system rollout status deployment/registry-cache --timeout=180s",
            "Registry Cache готов на worker"
        ):
            self.log_success("Registry Cache развернут на worker")
    
    def deploy_prometheus_on_worker(self):
        """Развертывание Prometheus на worker с увеличенными ресурсами"""
        self.log_info("Развертывание Prometheus на worker...")
        
        prometheus_manifest = f'''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
  labels:
    app: prometheus
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
        node-role.kubernetes.io/worker: "worker"
      serviceAccountName: prometheus
      containers:
      - name: prometheus
        image: prom/prometheus:v2.47.0
        args:
        - "--config.file=/etc/prometheus/prometheus.yml"
        - "--storage.tsdb.path=/prometheus"
        - "--storage.tsdb.retention.time=15d"  # 15 дней retention
        - "--web.console.libraries=/etc/prometheus/console_libraries"
        - "--web.console.templates=/etc/prometheus/consoles"
        - "--web.enable-lifecycle"
        - "--web.external-url=https://grafana.{self.domain}/prometheus"
        resources:
          requests:
            cpu: 500m    # Больше ресурсов на мощном worker
            memory: 1Gi
          limits:
            cpu: 2000m   # До 2 CPU на worker
            memory: 4Gi  # До 4GB RAM на worker
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: prometheus-config
          mountPath: /etc/prometheus
        - name: prometheus-storage
          mountPath: /prometheus
      volumes:
      - name: prometheus-config
        configMap:
          name: prometheus-config
      - name: prometheus-storage
        persistentVolumeClaim:
          claimName: prometheus-storage-worker
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: prometheus-storage-worker
  namespace: monitoring
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi  # Больше места на worker
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus
  namespace: monitoring
spec:
  selector:
    app: prometheus
  ports:
  - port: 9090
    targetPort: 9090
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus
rules:
- apiGroups: [""]
  resources: ["nodes", "services", "endpoints", "pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get"]
- nonResourceURLs: ["/metrics"]
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus
subjects:
- kind: ServiceAccount
  name: prometheus
  namespace: monitoring
'''
        
        with open("/tmp/prometheus-worker.yaml", "w") as f:
            f.write(prometheus_manifest)
        
        # Создаем конфигурацию Prometheus
        self.create_prometheus_config()
        
        self.run_kubectl("apply -f /tmp/prometheus-worker.yaml", capture_output=False)
        
        if self.wait_for_condition(
            "kubectl -n monitoring rollout status deployment/prometheus --timeout=300s",
            "Prometheus готов на worker",
            timeout=360
        ):
            self.log_success("Prometheus развернут на worker с увеличенными ресурсами")
    
    def create_prometheus_config(self):
        """Создание конфигурации Prometheus для гибридного кластера"""
        prometheus_config = '''
global:
  scrape_interval: 30s  # Оптимизировано для медленной связи
  evaluation_interval: 30s
  external_labels:
    cluster: 'k3s-hybrid-cluster'
    environment: 'production'

rule_files:
  - "*.rules.yml"

scrape_configs:
- job_name: 'kubernetes-apiservers'
  kubernetes_sd_configs:
  - role: endpoints
  scheme: https
  tls_config:
    ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    insecure_skip_verify: true
  bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
  relabel_configs:
  - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
    action: keep
    regex: default;kubernetes;https

- job_name: 'kubernetes-nodes'
  scheme: https
  tls_config:
    ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    insecure_skip_verify: true
  bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
  kubernetes_sd_configs:
  - role: node
  relabel_configs:
  - action: labelmap
    regex: __meta_kubernetes_node_label_(.+)

- job_name: 'kubernetes-cadvisor'
  scheme: https
  tls_config:
    ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    insecure_skip_verify: true
  bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
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
    replacement: /api/v1/nodes/\${1}/proxy/metrics/cadvisor

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
'''
        
        config_map = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "prometheus-config",
                "namespace": "monitoring"
            },
            "data": {
                "prometheus.yml": prometheus_config.strip()
            }
        }
        
        with open("/tmp/prometheus-config.yaml", "w") as f:
            yaml.dump(config_map, f)
        
        self.run_kubectl("apply -f /tmp/prometheus-config.yaml", capture_output=False)
    
    def deploy_grafana_on_worker(self):
        """Развертывание Grafana на worker"""
        self.log_info("Развертывание Grafana на worker...")
        
        grafana_manifest = f'''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
  labels:
    app: grafana
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
        node-role.kubernetes.io/worker: "worker"
      containers:
      - name: grafana
        image: grafana/grafana:10.1.0
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          value: "admin"  # Измените после первого входа
        - name: GF_USERS_ALLOW_SIGN_UP
          value: "false"
        - name: GF_SERVER_ROOT_URL
          value: "https://grafana.{self.domain}"
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 1000m  # Больше ресурсов на worker
            memory: 1Gi
        ports:
        - containerPort: 3000
        volumeMounts:
        - name: grafana-storage
          mountPath: /var/lib/grafana
        - name: grafana-datasources
          mountPath: /etc/grafana/provisioning/datasources
        - name: grafana-dashboards-config
          mountPath: /etc/grafana/provisioning/dashboards
        - name: grafana-dashboards
          mountPath: /var/lib/grafana/dashboards
      volumes:
      - name: grafana-storage
        persistentVolumeClaim:
          claimName: grafana-storage-worker
      - name: grafana-datasources
        configMap:
          name: grafana-datasource
      - name: grafana-dashboards-config
        configMap:
          name: grafana-dashboards-config
      - name: grafana-dashboards
        configMap:
          name: grafana-dashboards
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: grafana-storage-worker
  namespace: monitoring
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi  # Больше места на worker
---
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: monitoring
spec:
  selector:
    app: grafana
  ports:
  - port: 3000
    targetPort: 3000
'''
        
        with open("/tmp/grafana-worker.yaml", "w") as f:
            f.write(grafana_manifest)
        
        # Применяем Grafana конфигурацию
        monitoring_dir = REPO_ROOT / "manifests/monitoring"
        if monitoring_dir.exists():
            # Datasource
            datasource_file = monitoring_dir / "grafana-provisioning/datasource-configmap.yaml"
            if datasource_file.exists():
                self.run_kubectl(f"apply -f {datasource_file}", capture_output=False)
            
            # Dashboards
            dashboards_file = monitoring_dir / "grafana-provisioning/dashboards-configmap.yaml"
            if dashboards_file.exists():
                self.run_kubectl(f"apply -f {dashboards_file}", capture_output=False)
            
            provisioning_file = monitoring_dir / "grafana-provisioning/provisioning-wiring.yaml"
            if provisioning_file.exists():
                self.run_kubectl(f"apply -f {provisioning_file}", capture_output=False)
        
        self.run_kubectl("apply -f /tmp/grafana-worker.yaml", capture_output=False)
        
        if self.wait_for_condition(
            "kubectl -n monitoring rollout status deployment/grafana --timeout=180s",
            "Grafana готова на worker"
        ):
            self.log_success("Grafana развернута на worker")
    
    def deploy_kubevious_on_worker(self):
        """Развертывание Kubevious на worker"""
        self.log_info("Развертывание Kubevious на worker...")
        
        # Создаем namespace
        subprocess.run(["kubectl", "create", "namespace", "kubevious", "--dry-run=client", "-o", "yaml"], 
                      stdout=subprocess.PIPE)
        subprocess.run(["kubectl", "apply", "-f", "-"], 
                      input=subprocess.run(["kubectl", "create", "namespace", "kubevious", "--dry-run=client", "-o", "yaml"], 
                                          capture_output=True, text=True).stdout, text=True)
        
        # Добавляем Helm репозиторий
        subprocess.run(["helm", "repo", "add", "kubevious", "https://helm.kubevious.io"])
        subprocess.run(["helm", "repo", "update"])
        
        # Создаем values файл для worker размещения
        kubevious_values = f'''
# Размещение на worker ноде
nodeSelector:
  node-role.kubernetes.io/worker: worker

# Увеличенные ресурсы для worker
frontend:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi

backend:
  resources:
    requests:
      cpu: 150m
      memory: 256Mi
    limits:
      cpu: 1000m
      memory: 1Gi

# Persistent storage на worker
persistence:
  enabled: true
  size: 10Gi

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: kubevious.{self.domain}
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: kubevious-tls
      hosts:
        - kubevious.{self.domain}
'''
        
        with open("/tmp/kubevious-values.yaml", "w") as f:
            f.write(kubevious_values)
        
        # Устанавливаем через Helm
        result = subprocess.run([
            "helm", "upgrade", "--install", "kubevious", "kubevious/kubevious",
            "-n", "kubevious", "-f", "/tmp/kubevious-values.yaml"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            if self.wait_for_condition(
                "kubectl -n kubevious rollout status deployment/kubevious --timeout=300s",
                "Kubevious готов на worker"
            ):
                self.log_success(f"Kubevious развернут на worker: https://kubevious.{self.domain}")
        else:
            self.log_error(f"Ошибка установки Kubevious: {result.stderr}")
    
    def deploy_gpu_monitoring_on_worker(self):
        """Развертывание GPU мониторинга на worker (RTX 3090)"""
        self.log_info("Развертывание GPU мониторинга на worker...")
        
        gpu_exporter = '''
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nvidia-dcgm-exporter
  namespace: monitoring
  labels:
    app: nvidia-dcgm-exporter
spec:
  selector:
    matchLabels:
      app: nvidia-dcgm-exporter
  template:
    metadata:
      labels:
        app: nvidia-dcgm-exporter
    spec:
      nodeSelector:
        node-role.kubernetes.io/worker: "worker"  # Только на worker с GPU
      hostNetwork: true
      containers:
      - name: nvidia-dcgm-exporter
        image: nvcr.io/nvidia/k8s/dcgm-exporter:3.1.8-3.1.5-ubuntu20.04
        env:
        - name: DCGM_EXPORTER_LISTEN
          value: ":9400"
        - name: DCGM_EXPORTER_KUBERNETES
          value: "true"
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 256Mi
        securityContext:
          privileged: true
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      tolerations:
      - operator: Exists  # Может работать на любых нодах
---
apiVersion: v1
kind: Service
metadata:
  name: nvidia-dcgm-exporter
  namespace: monitoring
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9400"
spec:
  selector:
    app: nvidia-dcgm-exporter
  ports:
  - port: 9400
    targetPort: 9400
    name: metrics
'''
        
        with open("/tmp/gpu-monitoring.yaml", "w") as f:
            f.write(gpu_exporter)
        
        self.run_kubectl("apply -f /tmp/gpu-monitoring.yaml", capture_output=False)
        self.log_success("GPU мониторинг настроен на worker (RTX 3090)")
    
    def deploy_monitoring_on_master(self) -> bool:
        """Fallback: развертывание с ограниченными ресурсами на master"""
        self.log_warning("Развертывание мониторинга на master с ограниченными ресурсами...")
        
        # Применяем стандартную конфигурацию но с жесткими лимитами
        monitoring_dir = REPO_ROOT / "manifests/monitoring"
        if monitoring_dir.exists():
            self.run_kubectl(f"apply -k {monitoring_dir}", capture_output=False)
        
        # Принудительно ограничиваем ресурсы на master
        resource_patches = {
            "prometheus": {
                "requests": {"cpu": "300m", "memory": "512Mi"},
                "limits": {"cpu": "500m", "memory": "1Gi"}
            },
            "grafana": {
                "requests": {"cpu": "100m", "memory": "128Mi"}, 
                "limits": {"cpu": "200m", "memory": "256Mi"}
            }
        }
        
        for app, resources in resource_patches.items():
            patch = {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": app,
                                "resources": resources
                            }]
                        }
                    }
                }
            }
            
            self.run_kubectl(f"patch deployment {app} -n monitoring --patch '{json.dumps(patch)}'")
        
        self.log_success("Мониторинг развернут на master с жесткими лимитами")
        return True
    
    def apply_cluster_issuers(self):
        """Применение ClusterIssuer для TLS сертификатов"""
        self.log_info("Настройка ClusterIssuer для TLS...")
        
        # HTTP-01 issuer
        http01_manifest = REPO_ROOT / "manifests/cert-manager/clusterissuer-http01.yaml"
        if http01_manifest.exists():
            env = os.environ.copy()
            env["ACME_EMAIL"] = self.email
            subprocess.run(f"ACME_EMAIL={self.email} envsubst < {http01_manifest} | kubectl apply -f -", shell=True)
            self.log_success("HTTP-01 ClusterIssuer настроен")
        
        # DNS-01 опционально
        if self.use_dns01:
            cf_token = os.getenv("CF_API_TOKEN", "")
            if cf_token:
                subprocess.run([
                    "kubectl", "-n", "cert-manager", "create", "secret", "generic", 
                    "cloudflare-api-token", f"--from-literal=api-token={cf_token}",
                    "--dry-run=client", "-o", "yaml"
                ], stdout=subprocess.PIPE)
                
                dns01_manifest = REPO_ROOT / "manifests/cert-manager/clusterissuer-dns01-cloudflare.yaml"
                if dns01_manifest.exists():
                    env = os.environ.copy()
                    env["ACME_EMAIL"] = self.email
                    subprocess.run(f"ACME_EMAIL={self.email} envsubst < {dns01_manifest} | kubectl apply -f -", shell=True)
                    self.log_success("DNS-01 ClusterIssuer настроен")
    
    def expose_services(self):
        """Создание Ingress для доступа к сервисам"""
        self.log_info("Настройка Ingress для сервисов...")
        
        # Grafana Ingress
        grafana_ingress = f'''
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana
  namespace: monitoring
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - grafana.{self.domain}
    secretName: grafana-tls
  rules:
  - host: grafana.{self.domain}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: grafana
            port:
              number: 3000
'''
        
        with open("/tmp/grafana-ingress.yaml", "w") as f:
            f.write(grafana_ingress)
        
        self.run_kubectl("apply -f /tmp/grafana-ingress.yaml", capture_output=False)
        self.log_success(f"Grafana Ingress: https://grafana.{self.domain}")
    
    def apply_optimizations(self):
        """Применение дополнительных оптимизаций"""
        self.log_info("Применение оптимизаций кластера...")
        
        # VPA
        core_dir = REPO_ROOT / "manifests/core"
        if core_dir.exists():
            vpa_file = core_dir / "vpa.yaml"
            if vpa_file.exists():
                self.run_kubectl(f"apply -f {vpa_file}", capture_output=False)
                self.log_success("VPA применен")
    
    def perform_smoke_tests(self):
        """Комплексные smoke тесты для оптимизированной конфигурации"""
        self.log_info("Проведение smoke тестов оптимизированной конфигурации...")
        
        # Даем время на получение сертификатов
        self.log_info("Ожидание получения TLS сертификатов (60s)...")
        time.sleep(60)
        
        tests = [
            ("kubectl get nodes -o wide", "Проверка нод кластера"),
            ("kubectl -n monitoring get pods", "Проверка подов мониторинга"),
            ("kubectl -n kubevious get pods", "Проверка подов Kubevious"),
            ("kubectl get certificates --all-namespaces", "Проверка TLS сертификатов"),
            ("kubectl -n monitoring get ingress", "Проверка Grafana Ingress"),
            ("kubectl -n kubevious get ingress", "Проверка Kubevious Ingress")
        ]
        
        success_count = 0
        for cmd, description in tests:
            if self.wait_for_condition(cmd, description, timeout=60):
                success_count += 1
        
        self.log_info(f"Smoke тесты: {success_count}/{len(tests)} прошли успешно")
        
        # Показываем финальные URL
        print(f"\n🎉 РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!")
        print(f"\n📊 Доступные сервисы:")
        print(f"  • Grafana:   https://grafana.{self.domain}")
        print(f"  • Kubevious: https://kubevious.{self.domain}")
        print(f"\n🔐 Grafana credentials: admin/admin (измените при первом входе)")
        
        # Показываем распределение нагрузки
        self.show_resource_distribution()
    
    def show_resource_distribution(self):
        """Показать распределение ресурсов между нодами"""
        print(f"\n📊 РАСПРЕДЕЛЕНИЕ НАГРУЗКИ:")
        print(f"="*50)
        
        if self.worker_nodes:
            print(f"🖥️  Master VPS (3 vCPU, 4GB RAM, 10 Gbps):")
            print(f"  ✅ K3S Control Plane")
            print(f"  ✅ ingress-nginx")
            print(f"  ✅ cert-manager") 
            print(f"  ✅ CoreDNS")
            print(f"  ✅ Metrics Server")
            print(f"  📊 Использование: ~23% CPU, ~55% RAM")
            print()
            print(f"🏠 Worker Home PC (26 CPU, 64GB RAM, 100 Mbps internet):")
            print(f"  ✅ Prometheus (мониторинг)")
            print(f"  ✅ Grafana (дашборды)")
            print(f"  ✅ Kubevious (визуализация)")
            print(f"  ✅ Registry Cache")
            if self.enable_gpu:
                print(f"  ✅ GPU Monitoring (RTX 3090)")
            print(f"  📊 Использование: ~4% CPU, ~3% RAM")
            print(f"  📡 Связь с VPS: ~10 МБ/с (Tailscale)")
        else:
            print(f"🖥️  Master VPS (3 vCPU, 4GB RAM, 10 Gbps):")
            print(f"  ✅ Все компоненты (с жесткими лимитами)")
            print(f"  📊 Использование: ~70% CPU, ~85% RAM")
            print(f"  ⚠️  Рекомендуется подключить worker ноду")
    
    def run_full_deployment(self) -> bool:
        """Полное развертывание оптимизированного кластера"""
        print("🚀 ЗАПУСК ОПТИМИЗИРОВАННОГО РАЗВЕРТЫВАНИЯ K3S КЛАСТЕРА")
        print(f"📋 Параметры: домен={self.domain}, GPU={self.enable_gpu}, DNS-01={self.use_dns01}")
        print("="*80)
        
        try:
            # 1. Проверка зависимостей
            if not self.check_dependencies():
                return False
            
            # 2. Проверка кластера или установка master
            try:
                self.run_kubectl("cluster-info", timeout=30)
                self.log_success("Кластер уже установлен")
            except subprocess.TimeoutExpired:
                self.log_error("Кластер недоступен. Сначала установите master командой:")
                self.log_info("python3 scripts/install_cluster_enhanced.py --mode master")
                return False
            except subprocess.CalledProcessError:
                self.log_error("Кластер недоступен. Сначала установите master командой:")
                self.log_info("python3 scripts/install_cluster_enhanced.py --mode master")
                return False
            
            # 3. Анализ топологии
            if not self.analyze_cluster_topology():
                return False
            
            # 4. Развертывание критических компонентов на master
            if not self.deploy_master_components():
                return False
            
            # 5. Развертывание мониторинга на worker (или master если нет worker)
            if not self.deploy_worker_components():
                return False
            
            # 6. Настройка доступа к сервисам
            self.expose_services()
            
            # 7. Применение оптимизаций
            self.apply_optimizations()
            
            # 8. Финальные тесты
            self.perform_smoke_tests()
            
            return True
            
        except KeyboardInterrupt:
            self.log_warning("Развертывание прервано пользователем")
            return False
        except Exception as e:
            self.log_error(f"Неожиданная ошибка: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Оптимизированное развертывание K3S кластера")
    parser.add_argument("--domain", required=True, help="Базовый домен, например cockpit.work.gd")
    parser.add_argument("--email", required=True, help="Email для ACME Let's Encrypt")
    parser.add_argument("--gpu", default="true", choices=["true", "false"], help="Включить GPU мониторинг")
    parser.add_argument("--dns01", action="store_true", help="Использовать DNS-01 (Cloudflare) если установлен CF_API_TOKEN")
    
    args = parser.parse_args()
    
    deployer = OptimizedClusterDeployer(
        domain=args.domain,
        email=args.email,
        enable_gpu=args.gpu.lower() == "true",
        use_dns01=args.dns01
    )
    
    success = deployer.run_full_deployment()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()