# K3S Enhanced Hybrid Cluster 🚀

> Production-ready K3S cluster for enhanced VPS (3 vCPU, 4GB RAM, 100GB NVMe, 10 Gbps) + single Home PC worker (26 CPU, 64GB RAM, 1TB NVMe, RTX 3090) with in-cluster TLS, monitoring, logging, GitOps, autoscaling, and service mesh.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Production Ready](https://img.shields.io/badge/Production-Ready-green)](https://github.com/KomarovAI/k3s-network-aware-cluster)
[![Security](https://img.shields.io/badge/Security-NSA%2FCISA-blue)](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-release-kubernetes-hardening-guidance/)
[![K3S](https://img.shields.io/badge/K3S-v1.29+-brightgreen)](https://k3s.io/)
[![CIS Benchmark](https://img.shields.io/badge/CIS-Benchmark-orange)](https://www.cisecurity.org/benchmark/kubernetes)

## 🔗 Обзор

- **Grafana**: https://grafana.cockpit.work.gd
- **Kubevious**: https://kubevious.cockpit.work.gd
- **Kibana (Logs)**: https://kibana.cockpit.work.gd
- **ArgoCD**: https://argocd.cockpit.work.gd
- **Jaeger (Tracing)**: https://jaeger.cockpit.work.gd

## 🏗️ Архитектура и железо

### Профиль конфигурации
- **VPS (master)**: 3 vCPU, 4 GB RAM, 100 GB NVMe, **10 Gbps (1.25 ГБ/с)**
  - Роль: control plane + ingress + TLS
- **Home PC (worker)**: 26 CPU, 64 GB RAM, 1 TB NVMe, RTX 3090
  - Роль: мониторинг, логирование, GitOps, mesh, tracing, тяжелые сервисы
  - Соединение с VPS: ~10 МБ/с (Tailscale, межузловая связь)
  - Доступ в интернет: **100 Мбит/с** (внешний выход worker)

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

### 🔧 Настройка для новой команды/сервиса

#### 1. Секреты в репозитории сервиса (GitHub → Settings → Secrets and variables → Actions):

**Repository Secrets:**
```
DOCKERHUB_USERNAME=your_username
DOCKERHUB_TOKEN=dckr_pat_xxxxxxxxxx
KUBE_TOKEN=eyJhbGciOiJSUzI1NiIs...  # Получить от платформы (см. ниже)
```

**Repository Variables:**
```
DOMAIN_BASE=cockpit.work.gd
KUBE_SERVER=https://your-vps-tailscale-ip:6443
```

#### 2. Получение KUBE_TOKEN (делает платформа один раз):
```bash
# В кластере после установки Phase 2
kubectl create token cicd-deploy --duration=8760h
# Скопируйте токен в KUBE_TOKEN каждого сервисного репозитория
```

#### 3. Структура репозитория сервиса:
```
my-service/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions workflow
├── k8s/
│   ├── deployment.yaml         # Kubernetes manifests
│   ├── service.yaml
│   └── ingress.yaml
├── src/                        # Код сервиса
├── tests/                      # Тесты
├── Dockerfile
└── docker-compose.test.yml     # Интеграционные тесты
```

#### 4. Готовые шаблоны (копировать из платформы):
```bash
# GitHub Actions workflow
curl -o .github/workflows/deploy.yml \
  https://raw.githubusercontent.com/KomarovAI/k3s-network-aware-cluster/feature/vps-optimization/examples/github-actions-deploy.yml

# Kubernetes manifests
curl -o k8s/deployment.yaml \
  https://raw.githubusercontent.com/KomarovAI/k3s-network-aware-cluster/feature/vps-optimization/examples/service-manifests-template/deployment.yaml
  
curl -o k8s/service.yaml \
  https://raw.githubusercontent.com/KomarovAI/k3s-network-aware-cluster/feature/vps-optimization/examples/service-manifests-template/service.yaml
  
curl -o k8s/ingress.yaml \
  https://raw.githubusercontent.com/KomarovAI/k3s-network-aware-cluster/feature/vps-optimization/examples/service-manifests-template/ingress.yaml

# Отредактировать переменные: SERVICE_NAME, KUBE_NAMESPACE
```

### 🎯 Как работает пайплайн сервиса

```bash
git push origin main
# ↓ GitHub Actions автоматически:
# ✅ Запустит тесты (юнит + интеграционные)
# ✅ Соберет Docker образ
# ✅ Запушит в Docker Hub
# ✅ Обновит кластер (kubectl set image)
# ✅ Проверит rollout status
# ✅ Выполнит health-check
# 🎉 Сервис обновлен и доступен!
```

### 📊 Паттерны деплоя

**А. Простой сервис** (статический фронтенд, API):
```yaml
# В GitHub Actions:
kubectl set image deployment/my-service my-service=komarovai/my-service:${{ github.sha }} -n production
kubectl rollout status deployment/my-service -n production --timeout=300s
```

**Б. Сервис с базой данных**:
```yaml
# 1. Миграции БД (если нужны)
kubectl run migration-${{ github.sha }} --rm -i --restart=Never \
  --image=komarovai/my-service:${{ github.sha }} \
  --env="DB_URL=${{ secrets.DB_URL }}" \
  -- python manage.py migrate

# 2. Обновление сервиса
kubectl set image deployment/my-service my-service=komarovai/my-service:${{ github.sha }} -n production
```

**В. Микросервисная архитектура** (несколько компонентов):
```yaml
# Параллельное обновление всех компонентов
kubectl set image deployment/api-service api-service=komarovai/api:${{ github.sha }} -n production &
kubectl set image deployment/worker-service worker-service=komarovai/worker:${{ github.sha }} -n production &
kubectl set image deployment/frontend frontend=komarovai/frontend:${{ github.sha }} -n production &
wait
```

### 🔍 Что получаете автоматически

#### После деплоя каждого сервиса:
- ✅ **https://SERVICE_NAME.cockpit.work.gd** — автоматический TLS
- ✅ **Централизованные логи** в Kibana (автосбор через Filebeat)
- ✅ **Метрики** в Grafana unified dashboard (при label `monitoring: enabled`)
- ✅ **Auto-scaling** (HPA/KEDA по CPU/памяти/очередям/cron)
- ✅ **Service mesh** (mTLS, canary, traffic management через Istio)
- ✅ **Distributed tracing** (Jaeger через Istio sidecar)
- ✅ **Security policies** (OPA/Falco автоматические проверки)

#### Единый дашборд для всех сервисов:
🎯 **https://grafana.cockpit.work.gd** → **"Cluster Enterprise Overview"**
- Все сервисы, CPU, память, сеть, auto-scaling, логи, трейсы в **одном месте**

### 🛠️ Готовые шаблоны и примеры

| Файл | Назначение |
|------|------------|
| **[examples/github-actions-deploy.yml](examples/github-actions-deploy.yml)** | **GitHub Actions workflow для сервиса** |
| **[examples/service-manifests-template/](examples/service-manifests-template/)** | **Готовые Kubernetes манифесты** |
| **[README-CI-CD-SETUP.md](README-CI-CD-SETUP.md)** | **Полное руководство по CI/CD** |

### 🚀 Быстрый старт для новой команды

1. **Создайте репозиторий сервиса** и добавьте secrets/variables (см. выше)
2. **Скопируйте шаблоны** в свой репозиторий
3. **Отредактируйте переменные**: SERVICE_NAME, KUBE_NAMESPACE
4. **git push** → автоматический деплой!

**Подробности**: [README-CI-CD-SETUP.md](README-CI-CD-SETUP.md)

---

## 🌐 TLS, Ingress и Service Mesh

- **cert-manager**: автоматические Let's Encrypt сертификаты (HTTP-01/DNS-01)
- **ingress-nginx**: безопасная конфигурация (TLS 1.2/1.3, современные шифры)
- **Istio (Phase 2)**: mTLS, canary, traffic shifting, circuit breakers, retries, mirroring

## 📦 GitOps и деплой

- **ArgoCD (опционально)**: git push → автоматический деплой, one-click rollback
- **Прямой CI/CD (рекомендуемо)**: GitHub Actions → Docker Hub → kubectl (надежнее)
- **Helm/Helmfile**: переиспользуемые шаблоны, версии, быстрый деплой 

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

## 🛠️ Управляющие скрипты

| Скрипт | Назначение |
|--------|------------|
| **check_dependencies.sh** | **🔍 Проверка всех зависимостей перед развертыванием** |
| **auto_fix_dependencies.sh** | **🔧 Автоматическое исправление зависимостей** |
| deploy_all_optimized.py | Базовый оптимизированный деплой кластера |
| deploy_enterprise_stack.py | Enterprise улучшения (ELK, KEDA, Istio, Jaeger, OPA, Falco) |
| deploy_elk_on_worker.py | Развертывание ELK Stack на worker с оптимизациями |
| es_configure_optimization.py | Оптимизация Elasticsearch (ILM, SLM, compression) |
| cluster_optimizer.py | Проверки/оптимизации/отчеты по кластеру |
| production_hardening.py | Расширенный hardening безопасности |
| setup_memory_swap.sh | Настройка ZRAM 1G + swap 8G для master |

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

## 🚨 Траблшутинг

**Если что-то сломалось - см. [README-TROUBLESHOOTING.md](README-TROUBLESHOOTING.md)**

**Быстрые команды:**
- **Проверка зависимостей**: `./scripts/check_dependencies.sh`
- **Auto-fix**: `sudo ./scripts/auto_fix_dependencies.sh`
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

- **[README-LOGGING-OPTIMIZATION.md](README-LOGGING-OPTIMIZATION.md)** — подробное описание оптимизации логов (ILM, compression, snapshots)
- **[README-TROUBLESHOOTING.md](README-TROUBLESHOOTING.md)** — comprehensive troubleshooting guide для всех компонентов
- **[README-ELK-DEPLOYMENT.md](README-ELK-DEPLOYMENT.md)** — подробности по развертыванию ELK Stack  
- **[README-OVERVIEW.md](README-OVERVIEW.md)** — краткая памятка по развертыванию
- **[README-CI-CD-SETUP.md](README-CI-CD-SETUP.md)** — полное руководство по настройке CI/CD для сервисов
- **[README-HARDWARE.md](README-HARDWARE.md)** — детали железа и апгрейдов

---

## 🎯 TL;DR

**Готов к production гибридный K3S с enterprise-grade возможностями:**

1. **Проверь зависимости**: `./scripts/check_dependencies.sh`
2. **Базовый кластер**: `python3 scripts/deploy_all_optimized.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true`
3. **Enterprise фичи**: `python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase all`
4. **Настройте CI/CD**: [README-CI-CD-SETUP.md](README-CI-CD-SETUP.md)
5. **Если проблемы**: [README-TROUBLESHOOTING.md](README-TROUBLESHOOTING.md)

**🔥 Результат**: Сетевая платформа для автоматического деплоя сервисов через GitHub Actions → Docker Hub → kubectl. Единый мониторинг, логи, TLS, auto-scaling — всё enterprise-grade за 15 минут! 🚀