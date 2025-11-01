# K3S Enhanced Hybrid Cluster 🚀

> Production-ready K3S cluster for enhanced VPS (3 vCPU, 4GB RAM, 100GB NVMe, 10 Gbps) + single Home PC worker (26 CPU, 64GB RAM, 1TB NVMe, RTX 3090) with in-cluster TLS, monitoring, logging, autoscaling, and service mesh.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Production Ready](https://img.shields.io/badge/Production-Ready-green)](https://github.com/KomarovAI/k3s-network-aware-cluster)
[![Security](https://img.shields.io/badge/Security-NSA%2FCISA-blue)](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-release-kubernetes-hardening-guidance/)
[![K3S](https://img.shields.io/badge/K3S-v1.29+-brightgreen)](https://k3s.io/)
[![CIS Benchmark](https://img.shields.io/badge/CIS-Benchmark-orange)](https://www.cisecurity.org/benchmark/kubernetes)
[![WSL2 Support](https://img.shields.io/badge/WSL2-Support-blue)](docs/WSL2-SUPPORT.md)

## 🔗 Обзор

- **Grafana**: https://grafana.cockpit.work.gd
- **Kubevious**: https://kubevious.cockpit.work.gd  
- **Kibana (Logs)**: https://kibana.cockpit.work.gd
- **Jaeger (Tracing)**: https://jaeger.cockpit.work.gd

## 🏗️ Архитектура и железо

### Профиль конфигурации
- **VPS (master)**: 3 vCPU, 4 GB RAM, 100 GB NVMe, **10 Gbps (1.25 ГБ/с)**
  - Роль: control plane + ingress + TLS
- **Home PC (worker)**: 26 CPU, 64 GB RAM, 1 TB NVMe, RTX 3090
  - Роль: мониторинг, логирование, mesh, tracing, тяжелые сервисы
  - Соединение с VPS: ~10 МБ/с (Tailscale, межузловая связь)
  - Доступ в интернет: **100 Мбит/с** (внешний выход worker)

### 🐧 **WSL2 Support**
**NEW!** Полная поддержка Windows Subsystem for Linux 2:
- ✅ Автоматические исправления VXLAN → host-gw
- ✅ Решение проблем PersistentVolume node affinity  
- ✅ iptables compatibility fixes
- ✅ Оптимизация kernel параметров

📚 **Документация**: [WSL2-SUPPORT.md](docs/WSL2-SUPPORT.md)  
🚀 **Установка на WSL2**: `./scripts/install-worker-wsl2.sh`

### Оптимизированное распределение
- **VPS Master (10 Gbps)**: сетевые компоненты (ingress, cert-manager, API Server)
- **Home PC Worker**: вычислительные компоненты (мониторинг, логи, трейсы)
- **Оптимизация**: максимальное использование преимуществ каждой ноды

### Ключевые оптимизации
- **Сеть**: TCP BBR, gzip/brotli, APF (Priority-and-Fairness), 10 Gbps enterprise канал на VPS
- **Ресурсы**: VPA, image GC, registry cache
- **Память master**: ZRAM 1GB + swap 8GB (pri: 150/50)
- **Безопасность**: CIS Benchmark, NSA/CISA

## 🚀 Быстрый старт

### ⚡ Проверка зависимостей (обязательно первым шагом!)
```bash
# Запуск проверки всех зависимостей
./scripts/check_dependencies.sh

# Если есть проблемы - автоматическое исправление
sudo ./scripts/auto_fix_dependencies.sh

# Повторная проверка
./scripts/check_dependencies.sh
```

### Вариант 1: Базовый оптимизированный кластер
```bash
# После успешной проверки зависимостей
python3 scripts/deploy_all_optimized.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true
```

### 🐧 Вариант 1b: Worker на WSL2
```bash
# На WSL2 машине (Windows)
git clone https://github.com/KomarovAI/k3s-network-aware-cluster.git
cd k3s-network-aware-cluster
chmod +x scripts/install-worker-wsl2.sh
./scripts/install-worker-wsl2.sh
```

### Вариант 2: Enterprise улучшения (по фазам)
```bash
# Phase 1 (критично): ELK + KEDA + monitoring enhancements
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 1

# Phase 2 (важно): CI/CD Support + Istio Service Mesh  
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 2

# Phase 3 (желательно): Jaeger + OPA Gatekeeper + Falco
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 3

# Все фазы подряд
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase all
```

### Вариант 3: Только оптимизированные логи
```bash
# Развертывание ELK с compression, ILM, noise reduction, snapshots
python3 scripts/deploy_elk_on_worker.py --domain cockpit.work.gd --retention-days 15 --snapshots

# Применение только ES оптимизаций к существующему ELK
python3 scripts/es_configure_optimization.py --domain cockpit.work.gd --setup-snapshots
```

### DNS-01 (для заблокированного порта 80)
```bash
export CF_API_TOKEN="your_cloudflare_token"
python3 scripts/deploy_all_optimized.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true --dns01
```

---

## 🏢 Развертывание сервисов из отдельных репозиториев

> **Платформа предоставляет инфраструктуру (ingress, TLS, мониторинг, логи), а каждый сервис живет в СВОЕМ репозитории с прямым CI/CD через GitHub Actions → Docker Hub → kubectl**

### 📋 Архитектура сервисов

- **Платформенный репозиторий** (этот):
  - Готовит кластер, ingress-nginx, cert-manager, Grafana/Kibana, KEDA/автомасштабирование, Istio
  - НЕ хранит коды сервисов или их манифесты
- **Репозиторий сервиса** (каждый отдельно):
  - Исходники, Dockerfile, тесты
  - Kubernetes-манифесты сервиса (deployment/service/ingress)
  - GitHub Actions workflow для сборки и kubectl деплоя

### ⚡ Что уже настроено в платформе

- ✅ **Авто-TLS** для `*.DOMAIN` (cert-manager, ClusterIssuer)
- ✅ **Ingress-контроллер** (nginx) на master VPS (10 Gbps)
- ✅ **Централизованные логи** (ELK) и **мониторинг** (Grafana unified dashboard)
- ✅ **KEDA/HPA** автомасштабирование
- ✅ **Namespace** `production`, `staging`
- ✅ **ServiceAccount** `cicd-deploy` с RBAC (безопасный деплой из CI/CD)
- ✅ **Istio** (опционально): sidecar injection, mTLS, advanced routing

🔗 **Полное руководство по CI/CD**: [README-CI-CD-SETUP.md](README-CI-CD-SETUP.md)

### 🎯 Простой CI/CD без GitOps

```yaml
# .github/workflows/deploy.yml
name: Direct Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build & Deploy
        run: |
          # Build Docker image
          docker build -t ${{ secrets.DOCKERHUB_USERNAME }}/my-service:${{ github.sha }} .
          docker push ${{ secrets.DOCKERHUB_USERNAME }}/my-service:${{ github.sha }}
          
          # Direct kubectl deploy (no GitOps)
          kubectl set image deployment/my-service \
            my-service=${{ secrets.DOCKERHUB_USERNAME }}/my-service:${{ github.sha }} \
            -n production
          kubectl rollout status deployment/my-service -n production
```

**Преимущества прямого деплоя:**
- ✅ **Простота**: один шаг build → deploy
- ✅ **Надежность**: меньше движущихся частей
- ✅ **Скорость**: мгновенный деплой без GitOps задержек
- ✅ **Debugging**: прямая трассировка проблем

---

## 🌐 TLS, Ingress и Service Mesh

- **cert-manager**: автоматические Let's Encrypt сертификаты (HTTP-01/DNS-01)
- **ingress-nginx**: безопасная конфигурация (TLS 1.2/1.3, современные шифры)
- **Istio (Phase 2)**: mTLS, canary, traffic shifting, circuit breakers, retries, mirroring

## ⚖️ Авто‑масштабирование и ресурсы

- **VPA**: автоматический right‑sizing контейнеров
- **KEDA (Phase 1)**: event‑driven HPA (очереди, Kafka, Prometheus метрики и др.)
- **HPA**: горизонтальное масштабирование по custom метрикам
- **Descheduler/Cluster Autoscaler**: ребаланс/масштабирование нод (опционально)

## 📈 Мониторинг и визуализация

- **Prometheus + Grafana**: метрики, готовые дашборды (включая GPU)
- **Kubevious**: визуальный аудит k8s, поиск конфликтов и зависимостей
- **OpenTelemetry (опционально)**: унификация метрик/логов/трейсов

## 🧾 Централизованные логи (Phase 1 / отдельно)

- **ELK Stack на worker**: Elasticsearch + Logstash + Kibana + Filebeat
- **Оптимизация логов**: ILM hot-warm-cold-delete, compression (до 70% экономия), шумоподавление 
- **Бэкапы**: MinIO snapshots (daily, retention 14d)
- **Документация**: [README-LOGGING-OPTIMIZATION.md](README-LOGGING-OPTIMIZATION.md)

## 🔍 Трейсинг (Phase 3)

- **Jaeger (OTLP)**: распределенная трассировка запросов, карта зависимостей
- **Встраивание**: через OpenTelemetry auto‑instrumentation

## 🔒 Безопасность

- **Pod Security Standards (restricted)**, **RBAC**, **NetworkPolicies**
- **OPA Gatekeeper (Phase 3)**: Policy‑as‑Code, запрет небезопасных манифестов
- **Falco (Phase 3)**: runtime аномалии (поведенческая безопасность)
- **CIS/NSA-CISA**: hardening скрипты и проверки

## 🧠 Память master (устойчивость)

- **ZRAM 1GB (pri=150) + swap 8GB (pri=50)**
- **sysctl**: vm.swappiness=60, vm.vfs_cache_pressure=120
- **Итог**: ~13.8GB эффективной памяти, стабильность при пиках

## 🛠️ Управляющие скрипты (оптимизированные)

| Скрипт | Назначение | Статус |
|--------|-----------|--------|
| **check_dependencies.sh** | **🔍 Проверка всех зависимостей перед развертыванием** | ✅ Основной |
| **auto_fix_dependencies.sh** | **🔧 Автоматическое исправление зависимостей** | ✅ Основной |
| **deploy_all_optimized.py** | **🚀 Базовое развертывание кластера (production-ready)** | ✅ Основной |
| **deploy_enterprise_stack.py** | **🏢 Enterprise улучшения (ELK, KEDA, CI/CD, безопасность)** | ✅ Основной |
| **deploy_elk_on_worker.py** | **📊 Развертывание ELK Stack на worker с оптимизациями** | ✅ Специализированный |
| **es_configure_optimization.py** | **⚙️ Оптимизация Elasticsearch (ILM, SLM, compression)** | ✅ Специализированный |
| **install_cluster_enhanced.py** | **⚡ Установка базового кластера** | ✅ Основной |
| **migrate_to_worker.py** | **🔄 Миграция компонентов на worker ноды** | ✅ Утилита |
| **production_hardening.py** | **🛡️ Расширенный hardening безопасности** | ✅ Безопасность |
| **cluster_optimizer.py** | **🔧 Проверки/оптимизации/отчеты по кластеру** | ✅ Утилита |
| **quick_health_check.sh** | **🏥 Быстрая проверка здоровья кластера** | ✅ Утилита |
| **setup_memory_swap.sh** | **💾 Настройка ZRAM 1G + swap 8G для master** | ✅ Утилита |
| **wsl2-fixes.sh** | **🐧 WSL2 совместимость и исправления** | ✅ WSL2 |
| **install-worker-wsl2.sh** | **🐧 Автоматическая установка worker на WSL2** | ✅ WSL2 |

### 📦 Удаленные дубли и устаревшие файлы:
- ~~deploy_all.py~~ (заменен на deploy_all_optimized.py)
- ~~deploy_all_improved.py~~ (заменен на deploy_all_optimized.py)  
- ~~update_deploy_all_with_elk.py~~ (устаревший)
- ~~cleanup_and_optimize.py~~ (объединен с cluster_optimizer.py)
- ~~_memory_provision.py~~ (функции в setup_memory_swap.sh)
- ~~_patch_install_for_memory.py~~ (функции в setup_memory_swap.sh)
- ~~ensure_memory_hook.sh~~ (функции в setup_memory_swap.sh)

**Результат очистки: сокращено с 20 до 14 скриптов (экономия 30%)**

## 🔄 Жизненный цикл и обслуживание

- **Еженедельно**: проверка зависимостей и статуса кластера
```bash
./scripts/check_dependencies.sh
kubectl get pods -A | grep -v Running  # Найти проблемные pods
```

- **Ежемесячно**: проверка логов и ресурсов
```bash
# Проверка ELK оптимизации
kubectl port-forward -n logging deployment/elasticsearch 9200:9200 &
curl 'localhost:9200/_cat/indices?v&s=index'
curl 'localhost:9200/_ilm/policy'
```

- **Оптимизация**: анализ и улучшение производительности
```bash
python3 scripts/cluster_optimizer.py --optimize-all
python3 scripts/production_hardening.py --apply-all
```

## 🚨 Траблшутинг

**Быстрые команды:**
- **Проверка зависимостей**: `./scripts/check_dependencies.sh`
- **Auto-fix**: `sudo ./scripts/auto_fix_dependencies.sh`
- **Здоровье кластера**: `./scripts/quick_health_check.sh`
- **WSL2 проблемы**: `sudo ./scripts/wsl2-fixes.sh`
- **TLS/сертификаты**:
```bash
kubectl describe clusterissuer letsencrypt-prod
kubectl get certificaterequests --all-namespaces
kubectl logs -n cert-manager deployment/cert-manager
```
- **Ingress недоступен**:
```bash
kubectl get pods -n ingress-nginx
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
kubectl get ingress --all-namespaces
```
- **Worker не подключается**:
```bash
sudo cat /var/lib/rancher/k3s/server/node-token
curl -k https://MASTER_IP:6443/ping
tailscale status
```

## 📚 Дополнительная документация

- **[docs/WSL2-SUPPORT.md](docs/WSL2-SUPPORT.md)** — полная поддержка WSL2 с автоматическими исправлениями
- **[README-LOGGING-OPTIMIZATION.md](README-LOGGING-OPTIMIZATION.md)** — подробное описание оптимизации логов (ILM, compression, snapshots)
- **[README-CI-CD-SETUP.md](README-CI-CD-SETUP.md)** — полное руководство по настройке CI/CD для сервисов
- **[README-HARDWARE.md](README-HARDWARE.md)** — детали железа и апгрейдов

---

## 🎯 TL;DR

**Готов к production гибридный K3S с enterprise-grade возможностями:**

1. **Проверь зависимости**: `./scripts/check_dependencies.sh`
2. **Базовый кластер**: `python3 scripts/deploy_all_optimized.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true`
3. **Enterprise фичи**: `python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase all`
4. **Настройте CI/CD**: Используйте шаблоны из examples/ для каждого сервиса
5. **Если проблемы**: `python3 scripts/cluster_optimizer.py --check`

**🔥 Результат**: Сетевая платформа для автоматического деплоя сервисов через GitHub Actions → Docker Hub → kubectl. Единый мониторинг, логи, TLS, auto-scaling — всё enterprise-grade за 15 минут! 🚀

---

### 🏆 Особенности проекта

- ✅ **Production-Ready**: CIS Benchmark + NSA/CISA hardening
- ✅ **Hybrid Cloud**: VPS (сеть) + Home PC (compute) 
- ✅ **Enterprise Monitoring**: Prometheus + Grafana + ELK Stack
- ✅ **Auto-scaling**: KEDA + HPA + VPA
- ✅ **Security**: Pod Security Standards + RBAC + Network Policies
- ✅ **WSL2 Support**: Полная совместимость с Windows
- ✅ **Direct CI/CD**: GitHub Actions → kubectl (без GitOps сложности)
- ✅ **Cost Effective**: $10-20/месяц VPS vs $200-500/месяц managed Kubernetes