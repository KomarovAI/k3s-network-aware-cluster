#!/usr/bin/env python3
"""
Импортированная версия скрипта развертывания с улучшенной обработкой ошибок,
проверкой зависимостей и более надежной логикой ожидания.

Использование:
  python3 scripts/deploy_all_improved.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true

Требования на VPS:
  sudo apt-get update && sudo apt-get install -y curl jq python3 python3-yaml gettext-base helm
"""

import argparse
import os
import subprocess
import sys
import time
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TOOLS = ['kubectl', 'curl', 'jq', 'envsubst', 'helm']

class DeploymentError(Exception):
    """Исключение для ошибок развертывания"""
    pass

def log_info(msg: str):
    """Информационное сообщение"""
    print(f"ℹ️  {msg}")

def log_success(msg: str):
    """Сообщение об успехе"""
    print(f"✅ {msg}")

def log_error(msg: str):
    """Сообщение об ошибке"""
    print(f"❌ {msg}")

def log_warning(msg: str):
    """Предупреждение"""
    print(f"⚠️  {msg}")

def sh(cmd: str, check=True, capture_output=False) -> subprocess.CompletedProcess:
    """Выполнение shell команды с улучшенной обработкой ошибок"""
    print(f"$ {cmd}")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=capture_output,
            text=True if capture_output else None
        )
        if check and result.returncode != 0:
            raise DeploymentError(f"Команда завершилась с ошибкой: {cmd}")
        return result
    except Exception as e:
        if check:
            raise DeploymentError(f"Ошибка выполнения команды '{cmd}': {e}")
        return result

def wait_for_condition(cmd: str, success_msg: str, timeout: int = 300, sleep_interval: float = 5.0) -> bool:
    """Улучшенное ожидание с экспоненциальным backoff"""
    log_info(f"Ожидание готовности: {success_msg}")
    start_time = time.time()
    attempts = 0
    
    while time.time() - start_time < timeout:
        try:
            result = sh(cmd, check=False, capture_output=True)
            if result.returncode == 0:
                log_success(success_msg)
                return True
        except Exception as e:
            log_warning(f"Попытка {attempts + 1} не удалась: {e}")
        
        attempts += 1
        # Экспоненциальный backoff до максимума 30 секунд
        wait_time = min(sleep_interval * (1.5 ** attempts), 30)
        time.sleep(wait_time)
    
    log_error(f"Таймаут ({timeout}s) при ожидании: {success_msg}")
    return False

def check_dependencies():
    """Проверка наличия необходимых инструментов"""
    log_info("Проверка зависимостей...")
    missing = []
    
    for tool in REQUIRED_TOOLS:
        result = sh(f"which {tool}", check=False, capture_output=True)
        if result.returncode != 0:
            missing.append(tool)
    
    if missing:
        log_error(f"Отсутствуют необходимые инструменты: {', '.join(missing)}")
        log_info("Установите их командой:")
        if 'helm' in missing:
            print("curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash")
        if any(tool in ['curl', 'jq', 'gettext-base'] for tool in missing):
            print("sudo apt-get update && sudo apt-get install -y curl jq gettext-base")
        sys.exit(1)
    
    log_success("Все зависимости найдены")

def validate_cluster_state():
    """Проверка состояния кластера перед началом"""
    log_info("Проверка состояния K3S кластера...")
    
    # Проверяем, что кластер доступен
    if not wait_for_condition("kubectl cluster-info", "Кластер доступен", timeout=60):
        raise DeploymentError("K3S кластер недоступен")
    
    # Проверяем количество нод
    result = sh("kubectl get nodes --no-headers | wc -l", capture_output=True)
    node_count = int(result.stdout.strip())
    
    if node_count < 1:
        raise DeploymentError("В кластере нет активных нод")
    
    log_success(f"Кластер готов, найдено нод: {node_count}")
    return node_count

def deploy_master_if_needed():
    """Развертывание master ноды если необходимо"""
    try:
        validate_cluster_state()
        log_info("Master нода уже развернута")
    except DeploymentError:
        log_info("Развертывание master ноды...")
        sh("python3 scripts/install_cluster_enhanced.py --mode master")
        if not wait_for_condition("kubectl get nodes", "Master нода готова"):
            raise DeploymentError("Не удалось развернуть master ноду")

def install_ingress_nginx():
    """Установка ingress-nginx с проверками"""
    log_info("Установка ingress-nginx...")
    
    # Проверяем, не установлен ли уже
    result = sh("kubectl get namespace ingress-nginx", check=False, capture_output=True)
    if result.returncode == 0:
        log_info("ingress-nginx уже установлен")
        return
    
    sh("kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/cloud/deploy.yaml")
    
    if not wait_for_condition(
        "kubectl -n ingress-nginx get deployment ingress-nginx-controller -o jsonpath='{.status.readyReplicas}' | grep -q '^1$'",
        "ingress-nginx готов",
        timeout=300
    ):
        raise DeploymentError("Не удалось установить ingress-nginx")

def install_cert_manager():
    """Установка cert-manager с проверками"""
    log_info("Установка cert-manager...")
    
    # Проверяем, не установлен ли уже
    result = sh("kubectl get namespace cert-manager", check=False, capture_output=True)
    if result.returncode == 0:
        log_info("cert-manager уже установлен")
        return
    
    # CRDs
    sh("kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.crds.yaml")
    
    # Namespace
    sh("kubectl create namespace cert-manager")
    
    # Controller
    sh("kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml")
    
    if not wait_for_condition(
        "kubectl -n cert-manager get deployment cert-manager -o jsonpath='{.status.readyReplicas}' | grep -q '^1$'",
        "cert-manager готов",
        timeout=300
    ):
        raise DeploymentError("Не удалось установить cert-manager")

def apply_cluster_issuers(domain: str, email: str, use_dns01: bool):
    """Применение ClusterIssuer с валидацией"""
    log_info("Применение ClusterIssuers...")
    
    # HTTP-01
    env = os.environ.copy()
    env["ACME_EMAIL"] = email
    
    http01_manifest = REPO_ROOT / "manifests/cert-manager/clusterissuer-http01.yaml"
    if not http01_manifest.exists():
        raise DeploymentError(f"Файл {http01_manifest} не найден")
    
    sh(f"ACME_EMAIL={email} envsubst < {http01_manifest} | kubectl apply -f -")
    
    # DNS-01 опционально
    if use_dns01:
        cf_token = os.getenv("CF_API_TOKEN", "")
        if not cf_token:
            log_warning("CF_API_TOKEN не установлен, пропускаем DNS-01 issuer")
        else:
            # Создаем секрет с токеном
            sh(f"kubectl -n cert-manager create secret generic cloudflare-api-token --from-literal=api-token='{cf_token}' --dry-run=client -o yaml | kubectl apply -f -")
            
            dns01_manifest = REPO_ROOT / "manifests/cert-manager/clusterissuer-dns01-cloudflare.yaml"
            if dns01_manifest.exists():
                sh(f"ACME_EMAIL={email} envsubst < {dns01_manifest} | kubectl apply -f -")
            else:
                log_warning("DNS-01 ClusterIssuer файл не найден")

def apply_base_manifests():
    """Применение базовых манифестов"""
    log_info("Применение базовых манифестов...")
    
    base_dir = REPO_ROOT / "manifests/base"
    if base_dir.exists():
        sh(f"kubectl apply -k {base_dir}")
    else:
        log_warning("Директория базовых манифестов не найдена")

def setup_monitoring(domain: str):
    """Настройка мониторинга с проверками"""
    log_info("Настройка мониторинга...")
    
    # Создаем namespace
    sh("kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -")
    
    monitoring_dir = REPO_ROOT / "manifests/monitoring"
    if not monitoring_dir.exists():
        log_warning("Директория мониторинга не найдена")
        return
    
    # Применяем конфигурацию Grafana
    grafana_configs = [
        "grafana-provisioning/datasource-configmap.yaml",
        "grafana-provisioning/dashboards-configmap.yaml",
        "grafana-provisioning/provisioning-wiring.yaml"
    ]
    
    for config in grafana_configs:
        config_path = monitoring_dir / config
        if config_path.exists():
            sh(f"kubectl apply -f {config_path}")
        else:
            log_warning(f"Конфигурация {config} не найдена")

def setup_gpu_monitoring(enable_gpu: bool):
    """Настройка GPU мониторинга"""
    if not enable_gpu:
        log_info("GPU мониторинг отключен")
        return
        
    log_info("Настройка GPU мониторинга...")
    gpu_exporter_dir = REPO_ROOT / "manifests/monitoring/nvidia-dcgm-exporter"
    
    if gpu_exporter_dir.exists():
        sh(f"kubectl apply -k {gpu_exporter_dir}")
        log_success("GPU мониторинг настроен")
    else:
        log_warning("Манифесты GPU экспортера не найдены")

def install_kubevious(domain: str):
    """Установка Kubevious с Helm"""
    log_info("Установка Kubevious...")
    
    # Применяем namespace и ingress
    kubevious_dir = REPO_ROOT / "manifests/kubevious"
    if kubevious_dir.exists():
        sh(f"kubectl apply -k {kubevious_dir}")
    
    # Добавляем Helm репозиторий
    sh("helm repo add kubevious https://helm.kubevious.io")
    sh("helm repo update")
    
    # Проверяем, установлен ли уже
    result = sh("helm list -n kubevious -q", check=False, capture_output=True)
    if "kubevious" in (result.stdout or ""):
        log_info("Kubevious уже установлен")
        return
    
    # Устанавливаем
    values_file = kubevious_dir / "helm-values.yaml"
    if values_file.exists():
        sh(f"helm upgrade --install kubevious kubevious/kubevious -n kubevious --create-namespace -f {values_file}")
    else:
        sh("helm upgrade --install kubevious kubevious/kubevious -n kubevious --create-namespace")
    
    # Ждем готовности
    wait_for_condition(
        "kubectl -n kubevious get deployment kubevious -o jsonpath='{.status.readyReplicas}' | grep -q '^1$'",
        "Kubevious готов"
    )

def apply_optimization_features():
    """Применение VPA и registry cache"""
    log_info("Применение оптимизаций...")
    
    core_dir = REPO_ROOT / "manifests/core"
    
    # VPA
    vpa_file = core_dir / "vpa.yaml"
    if vpa_file.exists():
        sh(f"kubectl apply -f {vpa_file}")
        log_success("VPA применен")
    
    # Registry cache
    registry_file = core_dir / "registry-cache.yaml"
    if registry_file.exists():
        sh(f"kubectl apply -f {registry_file}")
        log_success("Registry cache применен")

def expose_services(domain: str):
    """Создание Ingress для сервисов"""
    log_info("Настройка Ingress для сервисов...")
    
    ingress_dir = REPO_ROOT / "manifests/ingress"
    if not ingress_dir.exists():
        log_warning("Директория ingress не найдена")
        return
    
    # Grafana Ingress
    grafana_ingress = ingress_dir / "grafana.yaml"
    if grafana_ingress.exists():
        env = os.environ.copy()
        env["TLS_DOMAIN"] = domain
        sh(f"TLS_DOMAIN={domain} envsubst < {grafana_ingress} | kubectl apply -f -")
        log_success(f"Grafana Ingress настроен: https://grafana.{domain}")

def perform_smoke_tests(domain: str):
    """Проведение smoke тестов"""
    log_info("Проведение smoke тестов...")
    
    # Даем время на получение сертификатов
    log_info("Ожидание получения TLS сертификатов...")
    time.sleep(30)
    
    # Проверяем Ingress объекты
    tests = [
        ("kubectl -n monitoring get ingress grafana", "Grafana Ingress"),
        ("kubectl -n kubevious get ingress kubevious", "Kubevious Ingress"),
        ("kubectl get clusterissuer letsencrypt-prod -o jsonpath='{.status.conditions[0].status}'", "ClusterIssuer")
    ]
    
    for cmd, name in tests:
        if wait_for_condition(cmd, f"{name} готов", timeout=60):
            log_success(f"{name} успешно настроен")
        else:
            log_warning(f"{name} может быть не готов")
    
    # Выводим финальные URL
    print("\n🎉 Развертывание завершено!")
    print(f"\n📊 Доступные сервисы:")
    print(f"  • Grafana:   https://grafana.{domain}")
    print(f"  • Kubevious: https://kubevious.{domain}")
    print(f"\n🔐 Grafana credentials: admin/admin (измените при первом входе)")

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description="Улучшенный скрипт развертывания K3S гибридного кластера")
    parser.add_argument("--domain", required=True, help="Базовый домен, например cockpit.work.gd")
    parser.add_argument("--email", required=True, help="Email для ACME Let's Encrypt")
    parser.add_argument("--gpu", default="true", choices=["true", "false"], help="Включить GPU мониторинг")
    parser.add_argument("--dns01", action="store_true", help="Использовать DNS-01 (Cloudflare) если установлен CF_API_TOKEN")
    parser.add_argument("--skip-deps-check", action="store_true", help="Пропустить проверку зависимостей")
    
    args = parser.parse_args()
    
    try:
        print("🚀 Начало развертывания K3S гибридного кластера")
        print(f"📋 Параметры: домен={args.domain}, GPU={args.gpu}, DNS-01={args.dns01}")
        
        # Проверка зависимостей
        if not args.skip_deps_check:
            check_dependencies()
        
        # Пошаговое развертывание
        deploy_master_if_needed()
        
        node_count = validate_cluster_state()
        if node_count == 1:
            log_warning("Обнаружена только 1 нода (master). Рекомендуется подключить worker ноду.")
            log_info("Инструкция для подключения worker: ~/join_worker_enhanced.py")
            response = input("Продолжить без worker ноды? (y/N): ")
            if response.lower() != 'y':
                log_info("Развертывание приостановлено. Подключите worker и повторите запуск.")
                return
        
        install_ingress_nginx()
        install_cert_manager()
        apply_cluster_issuers(args.domain, args.email, args.dns01)
        apply_base_manifests()
        setup_monitoring(args.domain)
        setup_gpu_monitoring(args.gpu.lower() == "true")
        install_kubevious(args.domain)
        apply_optimization_features()
        expose_services(args.domain)
        perform_smoke_tests(args.domain)
        
        log_success("🎉 Развертывание успешно завершено!")
        
    except DeploymentError as e:
        log_error(f"Ошибка развертывания: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        log_warning("Развертывание прервано пользователем")
        sys.exit(1)
    except Exception as e:
        log_error(f"Неожиданная ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
