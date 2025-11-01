#!/usr/bin/env python3
"""
Скрипт для переноса компонентов мониторинга с master на worker ноду.
Освобождает критические ресурсы на master VPS.

Использование:
  python3 scripts/migrate_to_worker.py --component prometheus
  python3 scripts/migrate_to_worker.py --component grafana  
  python3 scripts/migrate_to_worker.py --component kubevious
  python3 scripts/migrate_to_worker.py --component all
  python3 scripts/migrate_to_worker.py --rollback prometheus
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Dict, List

class WorkerMigration:
    def __init__(self):
        self.worker_label = "node-role.kubernetes.io/worker=worker"
        self.master_label = "node-role.kubernetes.io/control-plane=true"
        
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
        print(f"$ {full_cmd}")
        return subprocess.run(full_cmd, shell=True, capture_output=capture_output, text=True, check=check)
    
    def wait_for_rollout(self, resource: str, namespace: str, timeout: int = 300):
        """Ожидание завершения развертывания"""
        self.log_info(f"Ожидание готовности {resource} в namespace {namespace}...")
        try:
            self.run_kubectl(f"rollout status {resource} -n {namespace} --timeout={timeout}s")
            self.log_success(f"{resource} готов")
            return True
        except subprocess.CalledProcessError:
            self.log_error(f"Таймаут ожидания готовности {resource}")
            return False
    
    def get_worker_nodes(self) -> List[str]:
        """Получение списка worker нод"""
        try:
            result = self.run_kubectl("get nodes -l node-role.kubernetes.io/worker=worker -o jsonpath='{.items[*].metadata.name}'")
            nodes = result.stdout.strip().split()
            if not nodes or nodes == ['']:
                self.log_warning("Worker ноды не найдены, будет использован любой доступный узел")
                return []
            return nodes
        except subprocess.CalledProcessError:
            self.log_warning("Не удалось получить список worker нод")
            return []
    
    def ensure_worker_labels(self):
        """Убедиться что worker ноды имеют правильные labels"""
        self.log_info("Проверка labels на worker нодах...")
        
        # Получаем все ноды кроме master
        try:
            result = self.run_kubectl("get nodes -o json")
            nodes_data = json.loads(result.stdout)
            
            worker_nodes = []
            for node in nodes_data['items']:
                node_name = node['metadata']['name']
                labels = node['metadata'].get('labels', {})
                
                # Пропускаем master ноды
                if any(label.startswith('node-role.kubernetes.io/control-plane') for label in labels.keys()):
                    continue
                    
                worker_nodes.append(node_name)
                
                # Добавляем необходимые labels
                if 'node-role.kubernetes.io/worker' not in labels:
                    self.run_kubectl(f"label nodes {node_name} node-role.kubernetes.io/worker=worker")
                    self.log_success(f"Добавлен label worker для ноды {node_name}")
                
                if 'monitoring' not in labels:
                    self.run_kubectl(f"label nodes {node_name} monitoring=enabled")
                    self.log_success(f"Добавлен label monitoring для ноды {node_name}")
            
            if worker_nodes:
                self.log_success(f"Найдены worker ноды: {', '.join(worker_nodes)}")
            else:
                self.log_error("Не найдено worker нод для миграции")
                return False
                
            return True
            
        except Exception as e:
            self.log_error(f"Ошибка при проверке нод: {e}")
            return False
    
    def migrate_registry_cache(self, rollback=False):
        """Перенос registry cache"""
        self.log_info("Миграция Registry Cache...")
        
        node_selector = "{}" if rollback else '{"node-role.kubernetes.io/worker":"worker"}'
        action = "Возврат" if rollback else "Перенос"
        
        try:
            # Проверяем существование deployment
            result = self.run_kubectl("get deployment registry-cache -n kube-system", check=False)
            if result.returncode != 0:
                self.log_warning("Registry cache deployment не найден, пропускаем")
                return True
            
            # Обновляем nodeSelector
            patch = f'{{"spec":{{"template":{{"spec":{{"nodeSelector":{node_selector}}}}}}}}}'
            self.run_kubectl(f"patch deployment registry-cache -n kube-system -p '{patch}'")
            
            # Ждем готовности
            if self.wait_for_rollout("deployment/registry-cache", "kube-system"):
                self.log_success(f"{action} Registry Cache завершен")
                return True
            else:
                return False
                
        except subprocess.CalledProcessError as e:
            self.log_error(f"Ошибка миграции Registry Cache: {e}")
            return False
    
    def migrate_grafana(self, rollback=False):
        """Перенос Grafana"""
        self.log_info("Миграция Grafana...")
        
        node_selector = "{}" if rollback else '{"node-role.kubernetes.io/worker":"worker"}'
        action = "Возврат" if rollback else "Перенос"
        
        try:
            # Проверяем существование deployment
            result = self.run_kubectl("get deployment grafana -n monitoring", check=False)
            if result.returncode != 0:
                self.log_warning("Grafana deployment не найден, пропускаем")
                return True
            
            # Создаем PV для Grafana на worker (если не существует)
            if not rollback:
                pvc_yaml = """
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
      storage: 5Gi
"""
                
                # Проверяем существование PVC
                result = self.run_kubectl("get pvc grafana-storage-worker -n monitoring", check=False)
                if result.returncode != 0:
                    with open("/tmp/grafana-pvc.yaml", "w") as f:
                        f.write(pvc_yaml)
                    self.run_kubectl("apply -f /tmp/grafana-pvc.yaml")
                    self.log_success("Создан PVC для Grafana на worker")
            
            # Обновляем nodeSelector
            patch = f'{{"spec":{{"template":{{"spec":{{"nodeSelector":{node_selector}}}}}}}}}'
            self.run_kubectl(f"patch deployment grafana -n monitoring -p '{patch}'")
            
            # Ждем готовности
            if self.wait_for_rollout("deployment/grafana", "monitoring"):
                self.log_success(f"{action} Grafana завершен")
                return True
            else:
                return False
                
        except subprocess.CalledProcessError as e:
            self.log_error(f"Ошибка миграции Grafana: {e}")
            return False
    
    def migrate_kubevious(self, rollback=False):
        """Перенос Kubevious"""
        self.log_info("Миграция Kubevious...")
        
        action = "Возврат" if rollback else "Перенос"
        
        try:
            # Проверяем существование Helm release
            result = self.run_kubectl("get deployment kubevious -n kubevious", check=False)
            if result.returncode != 0:
                self.log_warning("Kubevious не найден, пропускаем")
                return True
            
            if rollback:
                # Возврат через Helm
                result = subprocess.run("helm upgrade kubevious kubevious/kubevious -n kubevious --set nodeSelector=null", 
                                      shell=True, capture_output=True, text=True, check=False)
            else:
                # Перенос через Helm с nodeSelector
                helm_cmd = 'helm upgrade kubevious kubevious/kubevious -n kubevious --set "nodeSelector.node-role\\.kubernetes\\.io/worker=worker"'
                result = subprocess.run(helm_cmd, shell=True, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                # Ждем готовности
                if self.wait_for_rollout("deployment/kubevious", "kubevious"):
                    self.log_success(f"{action} Kubevious завершен")
                    return True
            else:
                self.log_error(f"Ошибка Helm операции: {result.stderr}")
                # Fallback к kubectl patch
                node_selector = "{}" if rollback else '{"node-role.kubernetes.io/worker":"worker"}'
                patch = f'{{"spec":{{"template":{{"spec":{{"nodeSelector":{node_selector}}}}}}}}}'
                self.run_kubectl(f"patch deployment kubevious -n kubevious -p '{patch}'")
                
                if self.wait_for_rollout("deployment/kubevious", "kubevious"):
                    self.log_success(f"{action} Kubevious завершен (через kubectl)")
                    return True
                
        except subprocess.CalledProcessError as e:
            self.log_error(f"Ошибка миграции Kubevious: {e}")
            return False
        
        return False
    
    def migrate_prometheus(self, rollback=False):
        """Перенос Prometheus (наиболее критичный)"""
        self.log_info("Миграция Prometheus (это займет время из-за большого объема данных)...")
        
        node_selector = "{}" if rollback else '{"node-role.kubernetes.io/worker":"worker"}'
        action = "Возврат" if rollback else "Перенос"
        
        try:
            # Проверяем существование deployment
            result = self.run_kubectl("get deployment prometheus -n monitoring", check=False)
            if result.returncode != 0:
                self.log_warning("Prometheus deployment не найден, пропускаем")
                return True
            
            # Создаем больший PVC для Prometheus на worker (если не существует)
            if not rollback:
                pvc_yaml = """
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
      storage: 50Gi
"""
                
                # Проверяем существование PVC
                result = self.run_kubectl("get pvc prometheus-storage-worker -n monitoring", check=False)
                if result.returncode != 0:
                    with open("/tmp/prometheus-pvc.yaml", "w") as f:
                        f.write(pvc_yaml)
                    self.run_kubectl("apply -f /tmp/prometheus-pvc.yaml")
                    self.log_success("Создан PVC для Prometheus на worker (50Gi)")
            
            # Временно останавливаем Prometheus для безопасной миграции
            self.log_info("Временная остановка Prometheus...")
            self.run_kubectl("scale deployment prometheus -n monitoring --replicas=0")
            
            # Ждем остановки
            time.sleep(10)
            
            # Обновляем nodeSelector
            patch = f'{{"spec":{{"template":{{"spec":{{"nodeSelector":{node_selector}}}}}}}}}'
            self.run_kubectl(f"patch deployment prometheus -n monitoring -p '{patch}'")
            
            # Запускаем обратно
            self.log_info("Запуск Prometheus на новой ноде...")
            self.run_kubectl("scale deployment prometheus -n monitoring --replicas=1")
            
            # Ждем готовности (увеличенный таймаут из-за больших данных)
            if self.wait_for_rollout("deployment/prometheus", "monitoring", timeout=600):
                self.log_success(f"{action} Prometheus завершен")
                self.log_info("Проверьте доступность метрик в Grafana")
                return True
            else:
                return False
                
        except subprocess.CalledProcessError as e:
            self.log_error(f"Ошибка миграции Prometheus: {e}")
            return False
    
    def check_migration_status(self):
        """Проверка статуса миграции"""
        self.log_info("Проверка текущего размещения компонентов...")
        
        components = [
            ("registry-cache", "kube-system"),
            ("grafana", "monitoring"),
            ("kubevious", "kubevious"),
            ("prometheus", "monitoring")
        ]
        
        for component, namespace in components:
            try:
                result = self.run_kubectl(f"get pods -n {namespace} -l app={component} -o jsonpath='{{.items[0].spec.nodeName}}'")
                node_name = result.stdout.strip()
                
                if node_name:
                    # Получаем информацию о ноде
                    node_result = self.run_kubectl(f"get node {node_name} -o jsonpath='{{.metadata.labels}}'")
                    labels = json.loads(node_result.stdout)
                    
                    if "node-role.kubernetes.io/worker" in labels:
                        status = "🏠 Worker"
                    elif "node-role.kubernetes.io/control-plane" in labels:
                        status = "🎛️  Master"
                    else:
                        status = "❓ Unknown"
                    
                    print(f"  • {component:<15} → {status} ({node_name})")
                else:
                    print(f"  • {component:<15} → ❌ Не найден")
                    
            except subprocess.CalledProcessError:
                print(f"  • {component:<15} → ❌ Ошибка проверки")
    
    def migrate_all(self, rollback=False):
        """Миграция всех компонентов"""
        action = "Откат всех компонентов" if rollback else "Миграция всех компонентов на worker"
        self.log_info(f"Начинаем {action}...")
        
        if not rollback and not self.ensure_worker_labels():
            return False
        
        # Порядок миграции: от простого к сложному
        migrations = [
            ("Registry Cache", self.migrate_registry_cache),
            ("Grafana", self.migrate_grafana),
            ("Kubevious", self.migrate_kubevious),
            ("Prometheus", self.migrate_prometheus)
        ]
        
        success_count = 0
        for name, migrate_func in migrations:
            self.log_info(f"{'Откат' if rollback else 'Миграция'} {name}...")
            if migrate_func(rollback):
                success_count += 1
            else:
                self.log_error(f"Ошибка {'отката' if rollback else 'миграции'} {name}")
        
        self.log_info(f"Завершено: {success_count}/{len(migrations)} компонентов")
        
        # Проверяем итоговое состояние
        self.check_migration_status()
        
        if success_count == len(migrations):
            self.log_success(f"{'Откат' if rollback else 'Миграция'} успешно завершена!")
            if not rollback:
                self.log_info("Рекомендуется мониторить систему в течение нескольких часов")
            return True
        else:
            self.log_warning(f"{'Откат' if rollback else 'Миграция'} завершена частично")
            return False

def main():
    parser = argparse.ArgumentParser(description="Миграция компонентов между master и worker нодами")
    parser.add_argument("--component", choices=["prometheus", "grafana", "kubevious", "registry-cache", "all"],
                       help="Компонент для миграции")
    parser.add_argument("--rollback", help="Откатить компонент обратно на master")
    parser.add_argument("--status", action="store_true", help="Показать текущее размещение компонентов")
    
    args = parser.parse_args()
    
    if not any([args.component, args.rollback, args.status]):
        parser.print_help()
        sys.exit(1)
    
    migrator = WorkerMigration()
    
    try:
        if args.status:
            migrator.check_migration_status()
            return
        
        if args.rollback:
            # Откат конкретного компонента
            component = args.rollback
            migrator.log_info(f"Откат {component} обратно на master...")
            
            if component == "prometheus":
                success = migrator.migrate_prometheus(rollback=True)
            elif component == "grafana":
                success = migrator.migrate_grafana(rollback=True)
            elif component == "kubevious":
                success = migrator.migrate_kubevious(rollback=True)
            elif component == "registry-cache":
                success = migrator.migrate_registry_cache(rollback=True)
            elif component == "all":
                success = migrator.migrate_all(rollback=True)
            else:
                migrator.log_error(f"Неизвестный компонент: {component}")
                sys.exit(1)
        
        elif args.component:
            # Миграция на worker
            component = args.component
            
            if component == "all":
                success = migrator.migrate_all()
            else:
                if not migrator.ensure_worker_labels():
                    sys.exit(1)
                
                if component == "prometheus":
                    success = migrator.migrate_prometheus()
                elif component == "grafana":
                    success = migrator.migrate_grafana()
                elif component == "kubevious":
                    success = migrator.migrate_kubevious()
                elif component == "registry-cache":
                    success = migrator.migrate_registry_cache()
                else:
                    migrator.log_error(f"Неизвестный компонент: {component}")
                    sys.exit(1)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        migrator.log_warning("Операция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        migrator.log_error(f"Неожиданная ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
