# K3S Enhanced Hybrid Cluster 🚀

> Production-ready K3S cluster for enhanced VPS (3 vCPU, 4GB RAM, 100GB NVMe, 10 Gbps) + single Home PC worker (26 CPU, 64GB RAM, 1TB NVMe, RTX 3090) with in-cluster TLS, monitoring, logging, autoscaling, and service mesh.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Production Ready](https://img.shields.io/badge/Production-Ready-green)](https://github.com/KomarovAI/k3s-network-aware-cluster)
[![Security](https://img.shields.io/badge/Security-NSA%2FCISA-blue)](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-release-kubernetes-hardening-guidance/)
[![K3S](https://img.shields.io/badge/K3S-v1.29+-brightgreen)](https://k3s.io/)
[![CIS Benchmark](https://img.shields.io/badge/CIS-Benchmark-orange)](https://www.cisecurity.org/benchmark/kubernetes)

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

🔗 Полное руководство по CI/CD: **[README-CI-CD-SETUP.md](README-CI-CD-SETUP.md)**

---

## 🛠️ Управляющие скрипты (оптимизированные)

| Скрипт | Назначение | Статус |
|--------|-----------|---------|
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

### 📦 Удаленные дубли и устаревшие файлы:
- ~~deploy_all.py~~ (заменен на deploy_all_optimized.py)
- ~~deploy_all_improved.py~~ (заменен на deploy_all_optimized.py)  
- ~~update_deploy_all_with_elk.py~~ (устаревший)
- ~~cleanup_and_optimize.py~~ (объединен с cluster_optimizer.py)
- ~~_memory_provision.py~~ (функции в setup_memory_swap.sh)
- ~~_patch_install_for_memory.py~~ (функции в setup_memory_swap.sh)
- ~~ensure_memory_hook.sh~~ (функции в setup_memory_swap.sh)

**Результат очистки: сокращено с 20 до 12 скриптов (экономия 40%)**

---

## 🎥 TL;DR

**Готов к production гибридный K3S с enterprise-grade возможностями:**

1. **Проверь зависимости**: `./scripts/check_dependencies.sh`
2. **Базовый кластер**: `python3 scripts/deploy_all_optimized.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true`
3. **Enterprise фичи**: `python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase all`
4. **Настройте CI/CD**: Используйте шаблоны из examples/ для каждого сервиса
5. **Если проблемы**: `python3 scripts/cluster_optimizer.py --check`

**🔥 Результат**: Сетевая платформа для автоматического деплоя сервисов через GitHub Actions → Docker Hub → kubectl. Единый мониторинг, логи, TLS, auto-scaling — всё enterprise-grade за 15 минут! 🚀