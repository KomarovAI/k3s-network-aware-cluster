# K3S Enhanced Hybrid Cluster 🚀

> Production-ready K3S cluster for enhanced VPS (3 vCPU, 4GB RAM, 100GB NVMe, 1.25 Gbps) + single Home PC worker (26 CPU, 64GB RAM, 1TB NVMe, RTX 3090) with in-cluster TLS, monitoring, logging, GitOps, autoscaling, and service mesh.

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
- **VPS (master)**: 3 vCPU, 4 GB RAM, 100 GB NVMe, 1.25 Gbps
  - Роль: control plane + ingress + TLS
- **Home PC (worker)**: 26 CPU, 64 GB RAM, 1 TB NVMe, RTX 3090
  - Роль: мониторинг, логирование, GitOps, mesh, tracing, тяжелые сервисы
  - Соединение с VPS: ~10 МБ/с (Tailscale)

### Ключевые оптимизации
- **Сеть**: TCP BBR, gzip/brotli, APF (Priority-and-Fairness)
- **Ресурсы**: VPA, image GC, registry cache
- **Память master**: ZRAM 1GB + swap 8GB (pri: 150/50)
- **Безопасность**: CIS Benchmark, NSA/CISA

## 🚀 Быстрый старт

### Вариант 1: Базовый оптимизированный кластер
```bash
sudo apt-get update && sudo apt-get install -y curl jq python3 python3-yaml gettext-base
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
python3 scripts/deploy_all_improved.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true
```

### Вариант 2: Enterprise улучшения (по фазам)
```bash
# Phase 1 (критично): ELK + KEDA + monitoring enhancements
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 1 --confirm

# Phase 2 (важно): ArgoCD GitOps + Istio Service Mesh
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 2 --confirm

# Phase 3 (желательно): Jaeger + OPA Gatekeeper + Falco
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 3 --confirm

# Все фазы подряд
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase all --confirm
```

### DNS-01 (для заблокированного порта 80)
```bash
export CF_API_TOKEN="your_cloudflare_token"
python3 scripts/deploy_all_improved.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true --dns01
```

## 🌐 TLS, Ingress и Service Mesh

- **cert-manager**: автоматические Let's Encrypt сертификаты (HTTP-01/DNS-01)
- **ingress-nginx**: безопасная конфигурация (TLS 1.2/1.3, современные шифры)
- **Istio (Phase 2)**: mTLS, canary, traffic shifting, circuit breakers, retries, mirroring

## 📦 GitOps и деплой

- **ArgoCD (Phase 2)**: git push → автоматический деплой, one-click rollback
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

## 🧾 Логи (Phase 1)

- **ELK Stack на worker**: Elasticsearch + Logstash + Kibana + Filebeat
- **Возможности**: централизованное хранение, поиск, фильтрация, retention
- **Документация/команды**: см. README-ELK-DEPLOYMENT.md

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
| deploy_all_improved.py | Базовый оптимизированный деплой кластера |
| deploy_enterprise_stack.py | Enterprise улучшения (ELK, KEDA, ArgoCD, Istio, Jaeger, OPA, Falco) |
| deploy_elk_on_worker.py | Развертывание ELK Stack на worker |
| cluster_optimizer.py | Проверки/оптимизации/отчеты по кластеру |
| production_hardening.py | Расширенный hardening безопасности |
| setup_memory_swap.sh | Настройка ZRAM 1G + swap 8G для master |

## 🔄 Жизненный цикл и обслуживание

- **Еженедельно**: `python3 scripts/cluster_optimizer.py --check`
- **Ежемесячно**: `python3 scripts/cluster_optimizer.py --apply`
- **Отчеты**: `python3 scripts/cluster_optimizer.py --report --output monthly_report.json`

## 🚨 Траблшутинг (быстро)

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

## 📚 Дополнительно

- **README-ELK-DEPLOYMENT.md** — подробности по логированию
- **README-OVERVIEW.md** — краткая памятка по развертыванию
- **README-HARDWARE.md** — детали железа и апгрейдов

---

**TL;DR**: Гибридный K3S с in‑cluster TLS, мониторингом, **централизованными логами**, **GitOps**, **авто‑масштабированием** и **service mesh**. Быстрый старт за 10 минут, enterprise‑фичи за несколько команд.