#!/usr/bin/env python3
"""
Оптимизатор кластера K3S для гибридной конфигурации VPS + Home PC.
Применяет оптимизации на основе CIS Benchmark и best practices.

Использование:
  python3 scripts/cluster_optimizer.py --apply
  python3 scripts/cluster_optimizer.py --check
  python3 scripts/cluster_optimizer.py --report
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

REPO_ROOT = Path(__file__).resolve().parents[1]

class ClusterOptimizer:
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.optimizations_applied = 0
        self.warnings = []
        
    def log_info(self, msg: str):
        print(f"ℹ️  {msg}")
    
    def log_success(self, msg: str):
        print(f"✅ {msg}")
        self.checks_passed += 1
    
    def log_error(self, msg: str):
        print(f"❌ {msg}")
        self.checks_failed += 1
    
    def log_warning(self, msg: str):
        print(f"⚠️  {msg}")
        self.warnings.append(msg)
    
    def run_kubectl(self, cmd: str, capture_output=True) -> subprocess.CompletedProcess:
        """Выполнение kubectl команды"""
        full_cmd = f"kubectl {cmd}"
        return subprocess.run(full_cmd, shell=True, capture_output=capture_output, text=True)
    
    def check_cluster_health(self) -> bool:
        """Проверка здоровья кластера"""
        self.log_info("Проверка здоровья кластера...")
        
        # Проверка доступности API
        result = self.run_kubectl("cluster-info")
        if result.returncode == 0:
            self.log_success("Кластер API доступен")
        else:
            self.log_error("Кластер API недоступен")
            return False
        
        # Проверка нод
        result = self.run_kubectl("get nodes -o json")
        if result.returncode == 0:
            nodes = json.loads(result.stdout)
            ready_nodes = 0
            for node in nodes['items']:
                for condition in node['status']['conditions']:
                    if condition['type'] == 'Ready' and condition['status'] == 'True':
                        ready_nodes += 1
                        break
            
            if ready_nodes >= 1:
                self.log_success(f"Готовые ноды: {ready_nodes}")
            else:
                self.log_error("Нет готовых нод")
                return False
        
        return True
    
    def check_security_policies(self) -> Dict[str, bool]:
        """Проверка политик безопасности"""
        self.log_info("Проверка политик безопасности...")
        results = {}
        
        # Pod Security Standards
        result = self.run_kubectl("get psp --ignore-not-found")
        if result.returncode == 0 and result.stdout.strip():
            self.log_success("Pod Security Policies найдены")
            results['psp'] = True
        else:
            self.log_warning("Pod Security Policies не найдены")
            results['psp'] = False
        
        # Network Policies
        result = self.run_kubectl("get networkpolicy --all-namespaces -o json")
        if result.returncode == 0:
            policies = json.loads(result.stdout)
            if policies['items']:
                self.log_success(f"Network Policies: {len(policies['items'])}")
                results['network_policies'] = True
            else:
                self.log_warning("Network Policies не найдены")
                results['network_policies'] = False
        
        # RBAC
        result = self.run_kubectl("auth can-i list clusterroles")
        if result.returncode == 0:
            self.log_success("RBAC настроен")
            results['rbac'] = True
        else:
            self.log_error("RBAC может быть не настроен")
            results['rbac'] = False
        
        return results
    
    def check_resource_optimization(self) -> Dict[str, Any]:
        """Проверка оптимизации ресурсов"""
        self.log_info("Проверка оптимизации ресурсов...")
        results = {}
        
        # VPA (Vertical Pod Autoscaler)
        result = self.run_kubectl("get crd verticalpodautoscalers.autoscaling.k8s.io --ignore-not-found")
        if result.returncode == 0 and result.stdout.strip():
            self.log_success("VPA CRD найден")
            results['vpa'] = True
        else:
            self.log_warning("VPA не установлен")
            results['vpa'] = False
        
        # Registry cache
        result = self.run_kubectl("get deployment registry-cache -n kube-system --ignore-not-found")
        if result.returncode == 0 and result.stdout.strip():
            self.log_success("Registry cache найден")
            results['registry_cache'] = True
        else:
            self.log_warning("Registry cache не найден")
            results['registry_cache'] = False
        
        # Resource limits на подах
        result = self.run_kubectl("get pods --all-namespaces -o json")
        if result.returncode == 0:
            pods = json.loads(result.stdout)
            pods_with_limits = 0
            total_pods = len(pods['items'])
            
            for pod in pods['items']:
                for container in pod['spec']['containers']:
                    if 'resources' in container and 'limits' in container['resources']:
                        pods_with_limits += 1
                        break
            
            if total_pods > 0:
                percentage = (pods_with_limits / total_pods) * 100
                if percentage >= 70:
                    self.log_success(f"Resource limits: {percentage:.1f}% подов")
                    results['resource_limits'] = True
                else:
                    self.log_warning(f"Resource limits только на {percentage:.1f}% подов")
                    results['resource_limits'] = False
        
        return results
    
    def check_monitoring_stack(self) -> Dict[str, bool]:
        """Проверка стека мониторинга"""
        self.log_info("Проверка мониторинга...")
        results = {}
        
        # Prometheus
        result = self.run_kubectl("get deployment prometheus -n monitoring --ignore-not-found")
        if result.returncode == 0 and result.stdout.strip():
            self.log_success("Prometheus найден")
            results['prometheus'] = True
        else:
            self.log_warning("Prometheus не найден")
            results['prometheus'] = False
        
        # Grafana
        result = self.run_kubectl("get deployment grafana -n monitoring --ignore-not-found")
        if result.returncode == 0 and result.stdout.strip():
            self.log_success("Grafana найден")
            results['grafana'] = True
        else:
            self.log_warning("Grafana не найден")
            results['grafana'] = False
        
        # Kubevious
        result = self.run_kubectl("get deployment kubevious -n kubevious --ignore-not-found")
        if result.returncode == 0 and result.stdout.strip():
            self.log_success("Kubevious найден")
            results['kubevious'] = True
        else:
            self.log_warning("Kubevious не найден")
            results['kubevious'] = False
        
        return results
    
    def check_ingress_and_tls(self) -> Dict[str, bool]:
        """Проверка Ingress и TLS"""
        self.log_info("Проверка Ingress и TLS...")
        results = {}
        
        # Ingress Controller
        result = self.run_kubectl("get deployment ingress-nginx-controller -n ingress-nginx --ignore-not-found")
        if result.returncode == 0 and result.stdout.strip():
            self.log_success("Ingress Controller найден")
            results['ingress_controller'] = True
        else:
            self.log_error("Ingress Controller не найден")
            results['ingress_controller'] = False
        
        # cert-manager
        result = self.run_kubectl("get deployment cert-manager -n cert-manager --ignore-not-found")
        if result.returncode == 0 and result.stdout.strip():
            self.log_success("cert-manager найден")
            results['cert_manager'] = True
        else:
            self.log_error("cert-manager не найден")
            results['cert_manager'] = False
        
        # ClusterIssuer
        result = self.run_kubectl("get clusterissuer letsencrypt-prod --ignore-not-found")
        if result.returncode == 0 and result.stdout.strip():
            self.log_success("ClusterIssuer найден")
            results['cluster_issuer'] = True
        else:
            self.log_warning("ClusterIssuer не найден")
            results['cluster_issuer'] = False
        
        # TLS сертификаты
        result = self.run_kubectl("get certificates --all-namespaces -o json")
        if result.returncode == 0:
            certs = json.loads(result.stdout)
            ready_certs = 0
            for cert in certs['items']:
                if 'status' in cert and 'conditions' in cert['status']:
                    for condition in cert['status']['conditions']:
                        if condition['type'] == 'Ready' and condition['status'] == 'True':
                            ready_certs += 1
                            break
            
            if ready_certs > 0:
                self.log_success(f"TLS сертификаты готовы: {ready_certs}")
                results['tls_certs'] = True
            else:
                self.log_warning("TLS сертификаты не готовы")
                results['tls_certs'] = False
        
        return results
    
    def apply_network_optimizations(self) -> bool:
        """Применение сетевых оптимизаций"""
        self.log_info("Применение сетевых оптимизаций...")
        
        # Применяем CoreDNS оптимизацию
        coredns_config = '''
apiВерсия: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health {
            lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
            ttl 30
        }
        prometheus :9153
        forward . 8.8.8.8 8.8.4.4 {
            max_concurrent 1000
        }
        cache 30
        loop
        reload
        loadbalance
    }
'''
        
        try:
            # Сохраняем во временный файл
            temp_file = Path("/tmp/coredns-optimized.yaml")
            temp_file.write_text(coredns_config)
            
            result = self.run_kubectl(f"apply -f {temp_file}")
            if result.returncode == 0:
                self.log_success("CoreDNS оптимизация применена")
                self.optimizations_applied += 1
                return True
            else:
                self.log_error("CoreDNS оптимизация не удалась")
                return False
        except Exception as e:
            self.log_error(f"Ошибка при оптимизации CoreDNS: {e}")
            return False
    
    def apply_hardening_policies(self) -> bool:
        """Применение политик укрепления"""
        self.log_info("Применение политик укрепления...")
        
        # Default deny сетевая политика
        network_policy = '''
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to: []
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
'''
        
        try:
            temp_file = Path("/tmp/network-policies.yaml")
            temp_file.write_text(network_policy)
            
            result = self.run_kubectl(f"apply -f {temp_file}")
            if result.returncode == 0:
                self.log_success("Сетевые политики применены")
                self.optimizations_applied += 1
                return True
            else:
                self.log_error("Не удалось применить сетевые политики")
                return False
        except Exception as e:
            self.log_error(f"Ошибка при применении сетевых политик: {e}")
            return False
    
    def generate_report(self) -> Dict[str, Any]:
        """Генерация отчета о состоянии кластера"""
        self.log_info("Генерация отчета...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'cluster_health': self.check_cluster_health(),
            'security_policies': self.check_security_policies(),
            'resource_optimization': self.check_resource_optimization(),
            'monitoring_stack': self.check_monitoring_stack(),
            'ingress_and_tls': self.check_ingress_and_tls(),
            'summary': {
                'checks_passed': self.checks_passed,
                'checks_failed': self.checks_failed,
                'warnings': len(self.warnings),
                'optimizations_applied': self.optimizations_applied
            },
            'warnings': self.warnings
        }
        
        return report
    
    def run_full_check(self) -> bool:
        """Полная проверка кластера"""
        print("🔍 Полная проверка кластера...\n")
        
        healthy = self.check_cluster_health()
        if not healthy:
            return False
        
        self.check_security_policies()
        self.check_resource_optimization()
        self.check_monitoring_stack()
        self.check_ingress_and_tls()
        
        print(f"\n📊 Результаты проверки:")
        print(f"  ✅ Пройдено: {self.checks_passed}")
        print(f"  ❌ Не удалось: {self.checks_failed}")
        print(f"  ⚠️  Предупреждения: {len(self.warnings)}")
        
        if self.warnings:
            print("\n⚠️  Предупреждения:")
            for warning in self.warnings:
                print(f"    • {warning}")
        
        return self.checks_failed == 0
    
    def apply_optimizations(self) -> bool:
        """Применение оптимизаций"""
        print("🚀 Применение оптимизаций...\n")
        
        if not self.check_cluster_health():
            self.log_error("Кластер нездоров, оптимизация отменена")
            return False
        
        self.apply_network_optimizations()
        self.apply_hardening_policies()
        
        # Применяем production hardening скрипт
        hardening_script = REPO_ROOT / "scripts/production_hardening.py"
        if hardening_script.exists():
            self.log_info("Запуск production hardening...")
            result = subprocess.run(["python3", str(hardening_script)], capture_output=True, text=True)
            if result.returncode == 0:
                self.log_success("Production hardening применен")
                self.optimizations_applied += 1
            else:
                self.log_error("Production hardening не удался")
        
        print(f"\n🎉 Применено оптимизаций: {self.optimizations_applied}")
        return True

def main():
    parser = argparse.ArgumentParser(description="Оптимизатор K3S кластера")
    parser.add_argument("--check", action="store_true", help="Проверить состояние кластера")
    parser.add_argument("--apply", action="store_true", help="Применить оптимизации")
    parser.add_argument("--report", action="store_true", help="Сгенерировать JSON отчет")
    parser.add_argument("--output", help="Файл для сохранения отчета")
    
    args = parser.parse_args()
    
    if not any([args.check, args.apply, args.report]):
        parser.print_help()
        sys.exit(1)
    
    optimizer = ClusterOptimizer()
    
    try:
        if args.check:
            success = optimizer.run_full_check()
            sys.exit(0 if success else 1)
        
        elif args.apply:
            success = optimizer.apply_optimizations()
            sys.exit(0 if success else 1)
        
        elif args.report:
            report = optimizer.generate_report()
            
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                print(f"📊 Отчет сохранен: {args.output}")
            else:
                print(json.dumps(report, indent=2, ensure_ascii=False))
    
    except KeyboardInterrupt:
        print("\n⚠️  Операция прервана")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
