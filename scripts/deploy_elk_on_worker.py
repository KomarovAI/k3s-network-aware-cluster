#!/usr/bin/env python3
"""
Развертывание ELK Stack на worker ноде с оптимизацией ресурсов.
Автоматически настраивает nodeSelector, увеличенные лимиты памяти,
Ingress с TLS и интеграцию с существующим мониторингом.

Usage:
  python3 scripts/deploy_elk_on_worker.py --domain cockpit.work.gd --retention-days 15
  python3 scripts/deploy_elk_on_worker.py --domain cockpit.work.gd --retention-days 7 --light-mode
  python3 scripts/deploy_elk_on_worker.py --rollback
"""

import argparse
import json
import subprocess
import sys
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional

class ELKWorkerDeployer:
    def __init__(self, domain: str, retention_days: int = 15, light_mode: bool = False):
        self.domain = domain
        self.retention_days = retention_days
        self.light_mode = light_mode
        self.namespace = "logging"
        
    def log_info(self, msg: str):
        print(f"ℹ️  {msg}")
    
    def log_success(self, msg: str):
        print(f"✅ {msg}")
    
    def log_error(self, msg: str):
        print(f"❌ {msg}")
    
    def log_warning(self, msg: str):
        print(f"⚠️  {msg}")
    
    def run_kubectl(self, cmd: str, capture_output=True, check=True) -> subprocess.CompletedProcess:
        """Выполнение kubectl команды"""
        full_cmd = f"kubectl {cmd}"
        if not capture_output:
            print(f"$ {full_cmd}")
        return subprocess.run(full_cmd, shell=True, capture_output=capture_output, text=True, check=check)
    
    def wait_for_condition(self, cmd: str, success_msg: str, timeout: int = 300) -> bool:
        """Ожидание готовности с экспоненциальным backoff"""
        self.log_info(f"Ожидание: {success_msg}")
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
            wait_time = min(5 * (1.5 ** (attempts // 3)), 30)
            time.sleep(wait_time)
        
        self.log_error(f"Таймаут ({timeout}s) при ожидании: {success_msg}")
        return False
    
    def check_worker_nodes(self) -> bool:
        """Проверка наличия worker нод"""
        try:
            result = self.run_kubectl("get nodes -l node-role.kubernetes.io/worker=worker -o jsonpath='{.items[*].metadata.name}'")
            worker_nodes = result.stdout.strip().split()
            
            if not worker_nodes or worker_nodes == ['']:
                self.log_error("Worker ноды не найдены. ELK Stack нужно размещать на worker!")
                self.log_info("Сначала подключите worker ноду командой:")
                self.log_info("python3 ~/join_worker_enhanced.py")
                return False
                
            self.log_success(f"Найдены worker ноды: {', '.join(worker_nodes)}")
            return True
            
        except subprocess.CalledProcessError:
            self.log_error("Не удалось получить список worker нод")
            return False
    
    def create_namespace_and_storage(self):
        """Создание namespace и storage для ELK"""
        self.log_info("Создание namespace и storage...")
        
        # Создаем namespace
        namespace_yaml = f"""
apiVersion: v1
kind: Namespace
metadata:
  name: {self.namespace}
  labels:
    name: {self.namespace}
    purpose: centralized-logging
"""
        
        # Elasticsearch PVC для worker
        elasticsearch_storage = "50Gi" if not self.light_mode else "20Gi"
        elasticsearch_pvc = f"""
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: elasticsearch-storage
  namespace: {self.namespace}
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: {elasticsearch_storage}
"""
        
        # Kibana PVC для dashboards
        kibana_pvc = f"""
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: kibana-storage
  namespace: {self.namespace}
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 2Gi
"""
        
        with open("/tmp/elk-namespace-storage.yaml", "w") as f:
            f.write(namespace_yaml + "---" + elasticsearch_pvc + "---" + kibana_pvc)
        
        self.run_kubectl("apply -f /tmp/elk-namespace-storage.yaml", capture_output=False)
        self.log_success("Namespace и storage созданы")
    
    def deploy_elasticsearch(self):
        """Развертывание Elasticsearch на worker с увеличенными ресурсами"""
        self.log_info("Развертывание Elasticsearch на worker...")
        
        # Ресурсы зависят от режима
        if self.light_mode:
            es_memory_request = "1Gi"
            es_memory_limit = "2Gi" 
            es_cpu_request = "500m"
            es_cpu_limit = "1000m"
            heap_size = "1g"
        else:
            es_memory_request = "2Gi"
            es_memory_limit = "8Gi"  # Больше памяти на мощном worker
            es_cpu_request = "1000m"
            es_cpu_limit = "4000m"   # До 4 CPU на worker
            heap_size = "4g"
        
        elasticsearch_manifest = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elasticsearch
  namespace: {self.namespace}
  labels:
    app: elasticsearch
    component: logging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
        component: logging
    spec:
      nodeSelector:
        node-role.kubernetes.io/worker: "worker"
      containers:
      - name: elasticsearch
        image: elasticsearch:8.11.0
        env:
        - name: discovery.type
          value: single-node
        - name: ES_JAVA_OPTS
          value: "-Xms{heap_size} -Xmx{heap_size}"
        - name: xpack.security.enabled
          value: "false"
        - name: indices.lifecycle.rollover.max_age
          value: "{self.retention_days}d"
        - name: cluster.routing.allocation.disk.threshold_enabled
          value: "true"
        - name: cluster.routing.allocation.disk.watermark.low
          value: "85%"
        - name: cluster.routing.allocation.disk.watermark.high
          value: "90%"
        resources:
          requests:
            cpu: {es_cpu_request}
            memory: {es_memory_request}
          limits:
            cpu: {es_cpu_limit}
            memory: {es_memory_limit}
        ports:
        - containerPort: 9200
        - containerPort: 9300
        volumeMounts:
        - name: elasticsearch-storage
          mountPath: /usr/share/elasticsearch/data
        readinessProbe:
          httpGet:
            path: /_cluster/health
            port: 9200
          initialDelaySeconds: 30
          timeoutSeconds: 30
        livenessProbe:
          httpGet:
            path: /_cluster/health
            port: 9200
          initialDelaySeconds: 60
          timeoutSeconds: 30
      volumes:
      - name: elasticsearch-storage
        persistentVolumeClaim:
          claimName: elasticsearch-storage
---
apiVersion: v1
kind: Service
metadata:
  name: elasticsearch
  namespace: {self.namespace}
spec:
  selector:
    app: elasticsearch
  ports:
  - port: 9200
    targetPort: 9200
    name: http
  - port: 9300
    targetPort: 9300
    name: transport
"""
        
        with open("/tmp/elasticsearch.yaml", "w") as f:
            f.write(elasticsearch_manifest)
        
        self.run_kubectl("apply -f /tmp/elasticsearch.yaml", capture_output=False)
        
        if self.wait_for_condition(
            f"kubectl -n {self.namespace} rollout status deployment/elasticsearch --timeout=300s",
            "Elasticsearch готов на worker",
            timeout=360
        ):
            self.log_success(f"Elasticsearch развернут на worker с {es_memory_limit} RAM")
    
    def deploy_logstash(self):
        """Развертывание Logstash на worker"""
        self.log_info("Развертывание Logstash на worker...")
        
        # Конфигурация Logstash
        logstash_config = f"""
input {{
  beats {{
    port => 5044
  }}
  http {{
    port => 8080
  }}
}}

filter {{
  if [kubernetes] {{
    mutate {{
      add_field => {{ "cluster" => "k3s-hybrid" }}
    }}
  }}
  
  # Парсинг JSON логов
  if [message] =~ /^\\{{/ {{
    json {{
      source => "message"
      target => "json_data"
    }}
  }}
  
  # Добавляем временную метку
  date {{
    match => [ "timestamp", "ISO8601" ]
  }}
}}

output {{
  elasticsearch {{
    hosts => ["elasticsearch:9200"]
    index => "logs-k3s-%{{+YYYY.MM.dd}}"
    template_overwrite => true
    template_name => "k3s-logs"
  }}
  
  # Debug output
  stdout {{ codec => rubydebug }}
}}
"""
        
        # ConfigMap для конфигурации
        logstash_configmap = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "logstash-config",
                "namespace": self.namespace
            },
            "data": {
                "logstash.conf": logstash_config.strip()
            }
        }
        
        # Logstash Deployment
        logstash_memory = "512Mi" if self.light_mode else "1Gi"
        logstash_cpu = "200m" if self.light_mode else "500m"
        
        logstash_manifest = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: logstash
  namespace: {self.namespace}
  labels:
    app: logstash
    component: logging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: logstash
  template:
    metadata:
      labels:
        app: logstash
        component: logging
    spec:
      nodeSelector:
        node-role.kubernetes.io/worker: "worker"
      containers:
      - name: logstash
        image: logstash:8.11.0
        env:
        - name: LS_JAVA_OPTS
          value: "-Xmx{logstash_memory.replace('i', '').replace('G', 'g').replace('M', 'm')}"
        resources:
          requests:
            cpu: {logstash_cpu}
            memory: {logstash_memory}
          limits:
            cpu: 1000m
            memory: {logstash_memory.replace('512Mi', '1Gi')}
        ports:
        - containerPort: 5044
        - containerPort: 8080
        volumeMounts:
        - name: logstash-config
          mountPath: /usr/share/logstash/pipeline
      volumes:
      - name: logstash-config
        configMap:
          name: logstash-config
---
apiVersion: v1
kind: Service
metadata:
  name: logstash
  namespace: {self.namespace}
spec:
  selector:
    app: logstash
  ports:
  - port: 5044
    targetPort: 5044
    name: beats
  - port: 8080
    targetPort: 8080
    name: http
"""
        
        # Применяем конфигурацию и деплой
        with open("/tmp/logstash-configmap.yaml", "w") as f:
            yaml.dump(logstash_configmap, f)
        
        with open("/tmp/logstash.yaml", "w") as f:
            f.write(logstash_manifest)
        
        self.run_kubectl("apply -f /tmp/logstash-configmap.yaml", capture_output=False)
        self.run_kubectl("apply -f /tmp/logstash.yaml", capture_output=False)
        
        if self.wait_for_condition(
            f"kubectl -n {self.namespace} rollout status deployment/logstash --timeout=180s",
            "Logstash готов на worker"
        ):
            self.log_success(f"Logstash развернут на worker с {logstash_memory} RAM")
    
    def deploy_kibana(self):
        """Развертывание Kibana на worker с Ingress"""
        self.log_info("Развертывание Kibana на worker...")
        
        kibana_memory = "256Mi" if self.light_mode else "512Mi"
        
        kibana_manifest = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kibana
  namespace: {self.namespace}
  labels:
    app: kibana
    component: logging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kibana
  template:
    metadata:
      labels:
        app: kibana
        component: logging
    spec:
      nodeSelector:
        node-role.kubernetes.io/worker: "worker"
      containers:
      - name: kibana
        image: kibana:8.11.0
        env:
        - name: ELASTICSEARCH_HOSTS
          value: "http://elasticsearch:9200"
        - name: SERVER_HOST
          value: "0.0.0.0"
        - name: SERVER_PUBLICBASEURL
          value: "https://kibana.{self.domain}"
        - name: LOGGING_ROOT_LEVEL
          value: "warn"
        resources:
          requests:
            cpu: 200m
            memory: {kibana_memory}
          limits:
            cpu: 1000m
            memory: {kibana_memory.replace('256Mi', '512Mi')}
        ports:
        - containerPort: 5601
        volumeMounts:
        - name: kibana-storage
          mountPath: /usr/share/kibana/data
        readinessProbe:
          httpGet:
            path: /api/status
            port: 5601
          initialDelaySeconds: 60
          timeoutSeconds: 30
      volumes:
      - name: kibana-storage
        persistentVolumeClaim:
          claimName: kibana-storage
---
apiVersion: v1
kind: Service
metadata:
  name: kibana
  namespace: {self.namespace}
spec:
  selector:
    app: kibana
  ports:
  - port: 5601
    targetPort: 5601
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: kibana
  namespace: {self.namespace}
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - kibana.{self.domain}
    secretName: kibana-tls
  rules:
  - host: kibana.{self.domain}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: kibana
            port:
              number: 5601
"""
        
        with open("/tmp/kibana.yaml", "w") as f:
            f.write(kibana_manifest)
        
        self.run_kubectl("apply -f /tmp/kibana.yaml", capture_output=False)
        
        if self.wait_for_condition(
            f"kubectl -n {self.namespace} rollout status deployment/kibana --timeout=240s",
            "Kibana готова на worker"
        ):
            self.log_success(f"Kibana доступна: https://kibana.{self.domain}")
    
    def deploy_filebeat_daemonset(self):
        """Развертывание Filebeat DaemonSet для сбора логов с всех нод"""
        self.log_info("Развертывание Filebeat DaemonSet...")
        
        # Конфигурация Filebeat
        filebeat_config = f"""
filebeat.autodiscover:
  providers:
    - type: kubernetes
      node: ${{NODE_NAME}}
      hints.enabled: true
      hints.default_config:
        type: container
        paths:
          - /var/log/containers/*${{data.kubernetes.container.id}}.log

processors:
  - add_kubernetes_metadata:
      host: ${{NODE_NAME}}
      matchers:
      - logs_path:
          logs_path: "/var/log/containers/"

# Отправляем в Logstash на worker
output.logstash:
  hosts: ["logstash.{self.namespace}.svc.cluster.local:5044"]
  
# Дополнительно в Elasticsearch напрямую (fallback)
output.elasticsearch:
  hosts: ["elasticsearch.{self.namespace}.svc.cluster.local:9200"]
  index: "filebeat-k3s-%{{+yyyy.MM.dd}}"

logging.level: warning
"""
        
        filebeat_configmap = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "filebeat-config",
                "namespace": self.namespace
            },
            "data": {
                "filebeat.yml": filebeat_config.strip()
            }
        }
        
        # Filebeat DaemonSet (на всех нодах)
        filebeat_manifest = f"""
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: filebeat
  namespace: {self.namespace}
  labels:
    app: filebeat
    component: logging
spec:
  selector:
    matchLabels:
      app: filebeat
  template:
    metadata:
      labels:
        app: filebeat
        component: logging
    spec:
      serviceAccountName: filebeat
      terminationGracePeriodSeconds: 30
      hostNetwork: true
      dnsPolicy: ClusterFirstWithHostNet
      containers:
      - name: filebeat
        image: elastic/filebeat:8.11.0
        args:
        - "-c"
        - "/etc/filebeat.yml"
        - "-e"
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        resources:
          requests:
            cpu: 50m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
        securityContext:
          runAsUser: 0
        volumeMounts:
        - name: config
          mountPath: /etc/filebeat.yml
          readOnly: true
          subPath: filebeat.yml
        - name: data
          mountPath: /usr/share/filebeat/data
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
        - name: varlog
          mountPath: /var/log
          readOnly: true
      volumes:
      - name: config
        configMap:
          defaultMode: 0640
          name: filebeat-config
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
      - name: varlog
        hostPath:
          path: /var/log
      - name: data
        hostPath:
          path: /var/lib/filebeat-data
          type: DirectoryOrCreate
      tolerations:
      - operator: Exists  # Может работать на всех нодах включая master
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: filebeat
  namespace: {self.namespace}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: filebeat
rules:
- apiGroups: [""]
  resources:
  - namespaces
  - pods
  - nodes
  verbs:
  - get
  - watch
  - list
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: filebeat
subjects:
- kind: ServiceAccount
  name: filebeat
  namespace: {self.namespace}
roleRef:
  kind: ClusterRole
  name: filebeat
  apiGroup: rbac.authorization.k8s.io
"""
        
        # Применяем конфигурацию
        with open("/tmp/filebeat-configmap.yaml", "w") as f:
            yaml.dump(filebeat_configmap, f)
        
        with open("/tmp/filebeat.yaml", "w") as f:
            f.write(filebeat_manifest)
        
        self.run_kubectl("apply -f /tmp/filebeat-configmap.yaml", capture_output=False)
        self.run_kubectl("apply -f /tmp/filebeat.yaml", capture_output=False)
        
        if self.wait_for_condition(
            f"kubectl -n {self.namespace} rollout status daemonset/filebeat --timeout=120s",
            "Filebeat DaemonSet готов"
        ):
            self.log_success("Filebeat собирает логи со всех нод кластера")
    
    def deploy_optional_components(self):
        """Развертывание опциональных компонентов (Jaeger, External monitoring)"""
        self.log_info("Развертывание опциональных компонентов...")
        
        # Jaeger All-in-One на worker
        jaeger_manifest = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
  namespace: {self.namespace}
  labels:
    app: jaeger
    component: tracing
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
        component: tracing
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
          value: "memory"  # Можно переключить на Elasticsearch
        resources:
          requests:
            cpu: 200m
            memory: 384Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        ports:
        - containerPort: 16686  # UI
        - containerPort: 14268  # HTTP collector
        - containerPort: 6831   # UDP collector
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger
  namespace: {self.namespace}
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
  namespace: {self.namespace}
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
        
        # Blackbox Exporter для external monitoring
        blackbox_manifest = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blackbox-exporter
  namespace: {self.namespace}
  labels:
    app: blackbox-exporter
    component: external-monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blackbox-exporter
  template:
    metadata:
      labels:
        app: blackbox-exporter
        component: external-monitoring
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9115"
    spec:
      nodeSelector:
        node-role.kubernetes.io/worker: "worker"
      containers:
      - name: blackbox-exporter
        image: prom/blackbox-exporter:v0.24.0
        resources:
          requests:
            cpu: 50m
            memory: 96Mi
          limits:
            cpu: 200m
            memory: 256Mi
        ports:
        - containerPort: 9115
---
apiVersion: v1
kind: Service
metadata:
  name: blackbox-exporter
  namespace: {self.namespace}
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9115"
spec:
  selector:
    app: blackbox-exporter
  ports:
  - port: 9115
    targetPort: 9115
"""
        
        # Применяем компоненты
        with open("/tmp/jaeger.yaml", "w") as f:
            f.write(jaeger_manifest)
        
        with open("/tmp/blackbox-exporter.yaml", "w") as f:
            f.write(blackbox_manifest)
        
        self.run_kubectl("apply -f /tmp/jaeger.yaml", capture_output=False)
        self.run_kubectl("apply -f /tmp/blackbox-exporter.yaml", capture_output=False)
        
        # Ждем готовности
        if self.wait_for_condition(
            f"kubectl -n {self.namespace} rollout status deployment/jaeger --timeout=120s",
            "Jaeger готов"
        ):
            self.log_success(f"Jaeger UI: https://jaeger.{self.domain}")
        
        if self.wait_for_condition(
            f"kubectl -n {self.namespace} rollout status deployment/blackbox-exporter --timeout=60s",
            "Blackbox Exporter готов"
        ):
            self.log_success("External monitoring настроен")
    
    def create_index_templates(self):
        """Создание index templates для оптимизации Elasticsearch"""
        self.log_info("Настройка Elasticsearch index templates...")
        
        # Ждем готовности Elasticsearch
        if not self.wait_for_condition(
            f"kubectl -n {self.namespace} exec deployment/elasticsearch -- curl -s http://localhost:9200/_cluster/health",
            "Elasticsearch API готов"
        ):
            return
        
        # Index template для логов K3S
        index_template = {
            "index_patterns": ["logs-k3s-*", "filebeat-k3s-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,  # Single node
                    "index.lifecycle.name": "k3s-logs-policy",
                    "index.lifecycle.rollover_alias": "k3s-logs"
                },
                "mappings": {
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "kubernetes.namespace": {"type": "keyword"},
                        "kubernetes.pod.name": {"type": "keyword"},
                        "kubernetes.container.name": {"type": "keyword"},
                        "message": {"type": "text", "analyzer": "standard"}
                    }
                }
            }
        }
        
        with open("/tmp/index-template.json", "w") as f:
            json.dump(index_template, f, indent=2)
        
        # Применяем через kubectl exec
        template_cmd = f"""kubectl -n {self.namespace} exec deployment/elasticsearch -- curl -X PUT 'localhost:9200/_index_template/k3s-logs-template' -H 'Content-Type: application/json' -d '@-' < /tmp/index-template.json"""
        result = subprocess.run(template_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.log_success("Index templates настроены")
        
        # Index Lifecycle Policy для автоочистки
        lifecycle_policy = {
            "policy": {
                "phases": {
                    "hot": {
                        "actions": {
                            "rollover": {
                                "max_size": "5GB",
                                "max_age": "1d"
                            }
                        }
                    },
                    "delete": {
                        "min_age": f"{self.retention_days}d"
                    }
                }
            }
        }
        
        with open("/tmp/lifecycle-policy.json", "w") as f:
            json.dump(lifecycle_policy, f, indent=2)
        
        lifecycle_cmd = f"""kubectl -n {self.namespace} exec deployment/elasticsearch -- curl -X PUT 'localhost:9200/_ilm/policy/k3s-logs-policy' -H 'Content-Type: application/json' -d '@-' < /tmp/lifecycle-policy.json"""
        subprocess.run(lifecycle_cmd, shell=True, capture_output=True)
        
        self.log_success(f"Настроена автоочистка логов через {self.retention_days} дней")
    
    def setup_elk_monitoring_integration(self):
        """Интеграция ELK с существующим Prometheus мониторингом"""
        self.log_info("Настройка интеграции с Prometheus...")
        
        # ServiceMonitor для Elasticsearch
        service_monitor = f"""
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: elasticsearch
  namespace: {self.namespace}
  labels:
    app: elasticsearch
spec:
  selector:
    matchLabels:
      app: elasticsearch
  endpoints:
  - port: http
    interval: 30s
    path: /_prometheus/metrics
"""
        
        with open("/tmp/elasticsearch-servicemonitor.yaml", "w") as f:
            f.write(service_monitor)
        
        # Пробуем применить ServiceMonitor (если есть Prometheus Operator)
        result = self.run_kubectl("apply -f /tmp/elasticsearch-servicemonitor.yaml", check=False, capture_output=True)
        
        if result.returncode == 0:
            self.log_success("ServiceMonitor для Elasticsearch создан")
        else:
            self.log_info("ServiceMonitor не создан (Prometheus Operator не найден)")
    
    def rollback_elk_stack(self):
        """Откат ELK Stack"""
        self.log_info("Откат ELK Stack...")
        
        try:
            self.run_kubectl(f"delete namespace {self.namespace}", capture_output=False)
            self.log_success("ELK Stack удален")
            return True
        except subprocess.CalledProcessError:
            self.log_error("Ошибка при удалении ELK Stack")
            return False
    
    def run_smoke_tests(self):
        """Smoke tests для проверки ELK Stack"""
        self.log_info("Проведение smoke tests...")
        
        tests = [
            (f"kubectl -n {self.namespace} get pods", "Проверка статуса подов ELK"),
            (f"kubectl -n {self.namespace} exec deployment/elasticsearch -- curl -s localhost:9200/_cluster/health", "Проверка Elasticsearch health"),
            (f"kubectl -n {self.namespace} get ingress", "Проверка Ingress конфигурации"),
            ("kubectl get certificates --all-namespaces | grep kibana", "Проверка TLS сертификатов")
        ]
        
        success_count = 0
        for cmd, description in tests:
            if self.wait_for_condition(cmd, description, timeout=60):
                success_count += 1
        
        self.log_info(f"Smoke tests: {success_count}/{len(tests)} прошли успешно")
        
        if success_count == len(tests):
            print(f"\n🎉 ELK STACK РАЗВЕРНУТ УСПЕШНО!")
            print(f"📊 Доступные сервисы:")
            print(f"  • Kibana (логи и дашборды): https://kibana.{self.domain}")
            if not self.light_mode:
                print(f"  • Jaeger (трассировка): https://jaeger.{self.domain}")
            print(f"\n💡 Первые шаги:")
            print(f"  1. Откройте Kibana и создайте index pattern: logs-k3s-*")
            print(f"  2. Проверьте поступление логов в Index Management")
            print(f"  3. Создайте дашборды для мониторинга приложений")
    
    def deploy_full_elk_stack(self) -> bool:
        """Полное развертывание ELK Stack на worker"""
        print("🚀 РАЗВЕРТЫВАНИЕ ELK STACK НА WORKER НОДЕ")
        print("="*60)
        print(f"📋 Параметры: домен={self.domain}, retention={self.retention_days}d, light_mode={self.light_mode}")
        print()
        
        try:
            # 1. Проверка worker нод
            if not self.check_worker_nodes():
                return False
            
            # 2. Создание namespace и storage
            self.create_namespace_and_storage()
            
            # 3. Развертывание Elasticsearch
            self.deploy_elasticsearch()
            
            # 4. Развертывание Logstash
            self.deploy_logstash()
            
            # 5. Развертывание Kibana с Ingress
            self.deploy_kibana()
            
            # 6. Развертывание Filebeat DaemonSet
            self.deploy_filebeat_daemonset()
            
            # 7. Опциональные компоненты
            if not self.light_mode:
                self.deploy_optional_components()
            
            # 8. Настройка index templates
            time.sleep(30)  # Даем время Elasticsearch загрузиться
            self.create_index_templates()
            
            # 9. Интеграция с мониторингом
            self.setup_elk_monitoring_integration()
            
            # 10. Smoke tests
            self.run_smoke_tests()
            
            return True
            
        except KeyboardInterrupt:
            self.log_warning("Развертывание прервано пользователем")
            return False
        except Exception as e:
            self.log_error(f"Неожиданная ошибка: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Развертывание ELK Stack на worker ноде")
    parser.add_argument("--domain", required=True, help="Базовый домен для Ingress")
    parser.add_argument("--retention-days", type=int, default=15, help="Срок хранения логов (дней)")
    parser.add_argument("--light-mode", action="store_true", help="Облегченный режим (меньше ресурсов)")
    parser.add_argument("--rollback", action="store_true", help="Удалить ELK Stack")
    
    args = parser.parse_args()
    
    if args.rollback:
        deployer = ELKWorkerDeployer("", 0)
        success = deployer.rollback_elk_stack()
    else:
        deployer = ELKWorkerDeployer(args.domain, args.retention_days, args.light_mode)
        success = deployer.deploy_full_elk_stack()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()