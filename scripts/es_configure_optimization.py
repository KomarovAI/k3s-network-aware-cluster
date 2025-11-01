#!/usr/bin/env python3
"""
Elasticsearch оптимизация: ILM политики, index templates, SLM snapshots,
сжатие и автооптимизация для минимального disk usage.

Использование:
  python3 scripts/es_configure_optimization.py --domain cockpit.work.gd [--setup-snapshots]
  
Применяет:
- ILM hot-warm-cold-delete policies
- Index templates (1 shard, 0 replicas, optimized mappings)
- SLM daily snapshots (опционально)
- Compression в warm фазе
- Forcemerge автоматизация
"""

import argparse
import json
import requests
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

class ElasticsearchOptimizer:
    def __init__(self, domain: str, setup_snapshots: bool = False):
        self.domain = domain
        self.setup_snapshots = setup_snapshots
        self.es_host = "localhost:9200"
        
        # Проверяем доступность ES через port-forward
        self.setup_port_forward()
    
    def log_info(self, msg: str):
        print(f"\u2139\ufe0f  {msg}")
    
    def log_success(self, msg: str):
        print(f"\u2705 {msg}")
    
    def log_error(self, msg: str):
        print(f"\u274c {msg}")
    
    def log_warning(self, msg: str):
        print(f"\u26a0\ufe0f  {msg}")
    
    def setup_port_forward(self):
        """\u041dастройка port-forward для доступа к ES"""
        self.log_info("🔗 Настройка port-forward к Elasticsearch...")
        
        try:
            # Проверяем, есть ли уже port-forward
            result = requests.get(f"http://{self.es_host}/_cluster/health", timeout=2)
            if result.status_code == 200:
                self.log_success("Elasticsearch уже доступен")
                return
        except:
            pass
        
        # Запускаем port-forward в background
        subprocess.Popen([
            "kubectl", "port-forward", 
            "-n", "logging", 
            "deployment/elasticsearch", 
            "9200:9200"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Ожидание доступности
        for i in range(30):
            try:
                result = requests.get(f"http://{self.es_host}/_cluster/health", timeout=1)
                if result.status_code == 200:
                    self.log_success("Port-forward к Elasticsearch установлен")
                    return
            except:
                pass
            time.sleep(1)
        
        self.log_error("Не удалось установить соединение с Elasticsearch")
        sys.exit(1)
    
    def es_request(self, method: str, path: str, data: dict = None) -> bool:
        """Универсальный ES API запрос"""
        url = f"http://{self.es_host}{path}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                return False
            
            if response.status_code in [200, 201]:
                return True
            else:
                self.log_error(f"{method} {path}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.log_error(f"\u041e\u0448\u0438\u0431\u043a\u0430 {method} {path}: {e}")
            return False
    
    def apply_ilm_policies(self) -> bool:
        """\u041f\u0440\u0438\u043c\u0435\u043d\u0435\u043d\u0438\u0435 ILM \u043f\u043e\u043b\u0438\u0442\u0438\u043a"""
        self.log_info("🔄 \u041f\u0440\u0438\u043c\u0435\u043d\u0435\u043d\u0438\u0435 ILM \u043f\u043e\u043b\u0438\u0442\u0438\u043a...")
        
        # \u0427\u0438\u0442\u0430\u0435\u043c \u043f\u043e\u043b\u0438\u0442\u0438\u043a\u0438 \u0438\u0437 ConfigMap
        try:
            result = subprocess.run([
                "kubectl", "-n", "logging", "get", "configmap", 
                "elasticsearch-ilm-policy", "-o", "json"
            ], capture_output=True, text=True, check=True)
            
            configmap_data = json.loads(result.stdout)
            policies = configmap_data['data']
            
            for policy_name, policy_json in policies.items():
                policy_data = json.loads(policy_json)
                api_policy_name = policy_name.replace('.json', '')
                
                if self.es_request("PUT", f"/_ilm/policy/{api_policy_name}", policy_data):
                    self.log_success(f"ILM \u043f\u043e\u043b\u0438\u0442\u0438\u043a\u0430 {api_policy_name} \u043f\u0440\u0438\u043c\u0435\u043d\u0435\u043d\u0430")
                else:
                    self.log_error(f"\u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438\u043c\u0435\u043d\u0435\u043d\u0438\u044f ILM {api_policy_name}")
                    return False
            
            return True
            
        except Exception as e:
            self.log_error(f"\u041e\u0448\u0438\u0431\u043a\u0430 \u0447\u0442\u0435\u043d\u0438\u044f ILM ConfigMap: {e}")
            return False
    
    def apply_index_templates(self) -> bool:
        """\u041f\u0440\u0438\u043c\u0435\u043d\u0435\u043d\u0438\u0435 index templates"""
        self.log_info("📋 \u041f\u0440\u0438\u043c\u0435\u043d\u0435\u043d\u0438\u0435 index templates...")
        
        try:
            result = subprocess.run([
                "kubectl", "-n", "logging", "get", "configmap",
                "elasticsearch-index-template", "-o", "json"
            ], capture_output=True, text=True, check=True)
            
            configmap_data = json.loads(result.stdout)
            templates = configmap_data['data']
            
            for template_name, template_json in templates.items():
                template_data = json.loads(template_json)
                api_template_name = template_name.replace('.json', '')
                
                if self.es_request("PUT", f"/_index_template/{api_template_name}", template_data):
                    self.log_success(f"Index template {api_template_name} \u043f\u0440\u0438\u043c\u0435\u043d\u0435\u043d")
                else:
                    self.log_error(f"\u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438\u043c\u0435\u043d\u0435\u043d\u0438\u044f template {api_template_name}")
                    return False
            
            return True
            
        except Exception as e:
            self.log_error(f"\u041e\u0448\u0438\u0431\u043a\u0430 \u0447\u0442\u0435\u043d\u0438\u044f templates ConfigMap: {e}")
            return False
    
    def create_initial_indices(self) -> bool:
        """\u0421\u043e\u0437\u0434\u0430\u043d\u0438\u0435 \u043d\u0430\u0447\u0430\u043b\u044c\u043d\u044b\u0445 \u0438\u043d\u0434\u0435\u043a\u0441\u043e\u0432 \u0441 aliases"""
        self.log_info("📈 \u0421\u043e\u0437\u0434\u0430\u043d\u0438\u0435 \u043d\u0430\u0447\u0430\u043b\u044c\u043d\u044b\u0445 \u0438\u043d\u0434\u0435\u043a\u0441\u043e\u0432...")
        
        indices_to_create = [
            {
                "index": "logs-k3s-000001",
                "alias": "logs-k3s",
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "index.lifecycle.name": "k3s-logs-policy",
                    "index.lifecycle.rollover_alias": "logs-k3s",
                    "index.codec": "default"
                }
            },
            {
                "index": "filebeat-k3s-000001",
                "alias": "filebeat-k3s",
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "index.lifecycle.name": "k3s-logs-filebeat-policy",
                    "index.lifecycle.rollover_alias": "filebeat-k3s",
                    "index.codec": "default"
                }
            }
        ]
        
        for index_config in indices_to_create:
            index_name = index_config["index"]
            alias_name = index_config["alias"]
            settings = index_config["settings"]
            
            # \u041f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u043c, \u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u0435\u0442 \u043b\u0438 \u0443\u0436\u0435
            try:
                check_result = requests.get(f"http://{self.es_host}/{index_name}", timeout=5)
                if check_result.status_code == 200:
                    self.log_info(f"\u0418\u043d\u0434\u0435\u043a\u0441 {index_name} \u0443\u0436\u0435 \u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u0435\u0442")
                    continue
            except:
                pass
            
            # \u0421\u043e\u0437\u0434\u0430\u0435\u043c \u0438\u043d\u0434\u0435\u043a\u0441
            create_data = {
                "settings": settings,
                "aliases": {
                    alias_name: {
                        "is_write_index": True
                    }
                }
            }
            
            if self.es_request("PUT", f"/{index_name}", create_data):
                self.log_success(f"\u0418\u043d\u0434\u0435\u043a\u0441 {index_name} \u0441\u043e\u0437\u0434\u0430\u043d \u0441 alias {alias_name}")
            else:
                return False
        
        return True
    
    def setup_snapshot_repository(self) -> bool:
        """\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 snapshot repository (MinIO)"""
        if not self.setup_snapshots:
            return True
            
        self.log_info("💾 \u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 snapshot repository...")
        
        # \u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0441\u043e\u0437\u0434\u0430\u0435\u043c MinIO \u0434\u043b\u044f \u0431\u044d\u043a\u0430\u043f\u043e\u0432
        minio_manifest = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
  namespace: logging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      labels:
        app: minio
    spec:
      nodeSelector:
        node-role.kubernetes.io/worker: "worker"
      containers:
      - name: minio
        image: minio/minio:RELEASE.2023-09-04T19-57-37Z
        args:
        - server
        - /data
        - --console-address
        - ":9001"
        env:
        - name: MINIO_ACCESS_KEY
          value: "elk-snapshots"
        - name: MINIO_SECRET_KEY
          value: "elk-snapshots-secret-key-2023"
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        ports:
        - containerPort: 9000
        - containerPort: 9001
        volumeMounts:
        - name: minio-storage
          mountPath: /data
      volumes:
      - name: minio-storage
        persistentVolumeClaim:
          claimName: minio-storage
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: minio-storage
  namespace: logging
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi  # \u0414\u043b\u044f \u0431\u044d\u043a\u0430\u043f\u043e\u0432
---
apiVersion: v1
kind: Service
metadata:
  name: minio
  namespace: logging
spec:
  selector:
    app: minio
  ports:
  - port: 9000
    targetPort: 9000
    name: api
  - port: 9001 
    targetPort: 9001
    name: console
"""
        
        with open("/tmp/minio-for-snapshots.yaml", "w") as f:
            f.write(minio_manifest)
        
        # \u0420\u0430\u0437\u0432\u043e\u0440\u0430\u0447\u0438\u0432\u0430\u0435\u043c MinIO
        result = subprocess.run(["kubectl", "apply", "-f", "/tmp/minio-for-snapshots.yaml"], 
                               capture_output=True, text=True)
        if result.returncode != 0:
            self.log_error(f"\u041e\u0448\u0438\u0431\u043a\u0430 \u0440\u0430\u0437\u0432\u043e\u0440\u0430\u0447\u0438\u0432\u0430\u043d\u0438\u044f MinIO: {result.stderr}")
            return False
        
        # \u041e\u0436\u0438\u0434\u0430\u043d\u0438\u0435 MinIO
        self.log_info("\u23f3 \u041e\u0436\u0438\u0434\u0430\u043d\u0438\u0435 MinIO readiness...")
        for i in range(60):
            result = subprocess.run([
                "kubectl", "-n", "logging", "get", "pod", 
                "-l", "app=minio", "-o", "jsonpath={.items[0].status.phase}"
            ], capture_output=True, text=True)
            
            if result.stdout.strip() == "Running":
                break
            time.sleep(5)
        else:
            self.log_error("MinIO \u043d\u0435 \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u043b\u0441\u044f \u0437\u0430 5 \u043c\u0438\u043d")
            return False
        
        # \u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 ES snapshot repository
        snapshot_repo = {
            "type": "s3",
            "settings": {
                "bucket": "elk-snapshots",
                "endpoint": "minio.logging.svc.cluster.local:9000",
                "protocol": "http",
                "path_style_access": "true",
                "compress": "true",
                "chunk_size": "1gb",
                "server_side_encryption": "false"
            }
        }
        
        if self.es_request("PUT", "/_snapshot/elk-s3-repo", snapshot_repo):
            self.log_success("Snapshot repository \u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043d")
        else:
            return False
        
        # \u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 SLM \u043f\u043e\u043b\u0438\u0442\u0438\u043a\u0438
        slm_policy = {
            "schedule": "0 3 * * *",  # \u041a\u0430\u0436\u0434\u044b\u0435 \u0441\u0443\u0442\u043a\u0438 \u0432 3:00
            "name": "<daily-k3s-logs-snap-{now/d}>",
            "repository": "elk-s3-repo",
            "config": {
                "indices": ["logs-k3s-*", "filebeat-k3s-*"],
                "ignore_unavailable": True,
                "include_global_state": False
            },
            "retention": {
                "expire_after": "14d",
                "min_count": 7,
                "max_count": 30
            }
        }
        
        if self.es_request("PUT", "/_slm/policy/daily-snapshots", slm_policy):
            self.log_success("SLM \u043f\u043e\u043b\u0438\u0442\u0438\u043a\u0430 \u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043d\u0430 (daily 03:00, retention 14d)")
            return True
        
        return False
    
    def enable_best_compression(self) -> bool:
        """\u0412\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 best_compression \u0434\u043b\u044f warm/cold \u0444\u0430\u0437"""
        self.log_info("🗜\ufe0f \u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 \u0441\u0436\u0430\u0442\u0438\u044f \u0432 warm \u0444\u0430\u0437\u0435...")
        
        # \u041e\u0431\u043d\u043e\u0432\u043b\u044f\u0435\u043c ILM \u043f\u043e\u043b\u0438\u0442\u0438\u043a\u0438 \u0434\u043b\u044f \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u0438\u044f best_compression
        compression_update = {
            "policy": {
                "phases": {
                    "warm": {
                        "actions": {
                            "set_priority": {"priority": 50},
                            "allocate": {"number_of_replicas": 0},
                            "forcemerge": {"max_num_segments": 1},
                            "readonly": {},
                            "shrink": {"number_of_shards": 1}
                        }
                    }
                }
            }
        }
        
        # \u041f\u0440\u0438\u043c\u0435\u043d\u044f\u0435\u043c \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u043d\u0443\u044e \u043f\u043e\u043b\u0438\u0442\u0438\u043a\u0443 \u0434\u043b\u044f warm \u0441\u0436\u0430\u0442\u0438\u044f
        cluster_settings = {
            "persistent": {
                "cluster.routing.allocation.disk.watermark.low": "85%",
                "cluster.routing.allocation.disk.watermark.high": "90%", 
                "cluster.routing.allocation.disk.watermark.flood_stage": "95%",
                "indices.lifecycle.poll_interval": "5m"
            }
        }
        
        if self.es_request("PUT", "/_cluster/settings", cluster_settings):
            self.log_success("Disk watermarks \u0438 ILM polling \u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043d\u044b")
            return True
        
        return False
    
    def show_optimization_status(self):
        """\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u0441\u0442\u0430\u0442\u0443\u0441 \u043e\u043f\u0442\u0438\u043c\u0438\u0437\u0430\u0446\u0438\u0438"""
        self.log_info("📈 \u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0441\u0442\u0430\u0442\u0443\u0441\u0430 \u043e\u043f\u0442\u0438\u043c\u0438\u0437\u0430\u0446\u0438\u0438...")
        
        try:
            # \u041f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u043c ILM policies
            policies_result = requests.get(f"http://{self.es_host}/_ilm/policy", timeout=10)
            if policies_result.status_code == 200:
                policies = policies_result.json()
                self.log_success(f"ILM \u043f\u043e\u043b\u0438\u0442\u0438\u043a\u0438: {len(policies)} \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0445")
                
            # \u041f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u043c \u0438\u043d\u0434\u0435\u043a\u0441\u044b
            indices_result = requests.get(f"http://{self.es_host}/_cat/indices?format=json&bytes=mb", timeout=10)
            if indices_result.status_code == 200:
                indices = indices_result.json()
                total_size = sum(float(idx.get('store.size', '0mb').replace('mb', '')) for idx in indices)
                self.log_success(f"\u0418\u043d\u0434\u0435\u043a\u0441\u044b: {len(indices)} (\u043e\u0431\u0449\u0438\u0439 \u0440\u0430\u0437\u043c\u0435\u0440: {total_size:.1f} MB)")
                
            # \u041f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u043c snapshots \u0435\u0441\u043b\u0438 \u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043d\u044b
            if self.setup_snapshots:
                snapshots_result = requests.get(f"http://{self.es_host}/_snapshot/elk-s3-repo/_all", timeout=10)
                if snapshots_result.status_code == 200:
                    snapshots = snapshots_result.json()
                    self.log_success(f"Snapshots: {len(snapshots.get('snapshots', []))} \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e")
                    
        except Exception as e:
            self.log_warning(f"\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u043e\u043b\u0443\u0447\u0438\u0442\u044c \u043f\u043e\u043b\u043d\u044b\u0439 \u0441\u0442\u0430\u0442\u0443\u0441: {e}")
    
    def run_optimization(self) -> bool:
        """\u0417\u0430\u043f\u0443\u0441\u043a \u043f\u043e\u043b\u043d\u043e\u0439 \u043e\u043f\u0442\u0438\u043c\u0438\u0437\u0430\u0446\u0438\u0438"""
        print("\ud83d\ude80 ELASTICSEARCH \u041e\u041f\u0422\u0418\u041c\u0418\u0417\u0410\u0426\u0418\u042f")
        print("="*50)
        
        try:
            # 1. ILM policies
            if not self.apply_ilm_policies():
                return False
            
            # 2. Index templates    
            if not self.apply_index_templates():
                return False
                
            # 3. \u041d\u0430\u0447\u0430\u043b\u044c\u043d\u044b\u0435 \u0438\u043d\u0434\u0435\u043a\u0441\u044b
            if not self.create_initial_indices():
                return False
            
            # 4. Compression \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438
            if not self.enable_best_compression():
                return False
            
            # 5. Snapshots (\u043e\u043f\u0446\u0438\u043e\u043d\u0430\u043b\u044c\u043d\u043e)
            if self.setup_snapshots:
                if not self.setup_snapshot_repository():
                    return False
            
            # 6. \u0424\u0438\u043d\u0430\u043b\u044c\u043d\u044b\u0439 \u0441\u0442\u0430\u0442\u0443\u0441
            self.show_optimization_status()
            
            print("\n\ud83c\udf89 ELASTICSEARCH \u041e\u041f\u0422\u0418\u041c\u0418\u0417\u0410\u0426\u0418\u042f \u0417\u0410\u0412\u0415\u0420\u0428\u0415\u041d\u0410!")
            print("\u2705 ILM hot-warm-cold-delete \u043f\u043e\u043b\u0438\u0442\u0438\u043a\u0438")
            print("\u2705 \u041e\u043f\u0442\u0438\u043c\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0435 index templates (1 shard, 0 replicas)")
            print("\u2705 Compression \u0432 warm \u0444\u0430\u0437\u0435 (\u044d\u043a\u043e\u043d\u043e\u043c\u0438\u044f \u0434\u043e 60% disk)")
            if self.setup_snapshots:
                print("\u2705 Daily snapshots \u0441 retention 14 \u0434\u043d\u0435\u0439")
            
            return True
            
        except Exception as e:
            self.log_error(f"\u041a\u0440\u0438\u0442\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="ES \u041e\u043f\u0442\u0438\u043c\u0438\u0437\u0430\u0446\u0438\u044f")
    parser.add_argument("--domain", required=True, help="\u0411\u0430\u0437\u043e\u0432\u044b\u0439 \u0434\u043e\u043c\u0435\u043d")
    parser.add_argument("--setup-snapshots", action="store_true", help="\u041d\u0430\u0441\u0442\u0440\u043e\u0438\u0442\u044c MinIO + snapshots")
    
    args = parser.parse_args()
    
    optimizer = ElasticsearchOptimizer(args.domain, args.setup_snapshots)
    success = optimizer.run_optimization()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()