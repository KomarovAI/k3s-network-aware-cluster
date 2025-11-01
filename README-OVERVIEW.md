# Обзор

- Grafana: https://grafana.cockpit.work.gd
- Kubevious: https://kubevious.cockpit.work.gd
- Kibana (Logs): https://kibana.cockpit.work.gd
- ArgoCD: https://argocd.cockpit.work.gd
- Jaeger (Tracing): https://jaeger.cockpit.work.gd

## 🏗️ Архитектура

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

# One-shot deploy

На VPS выполните:

```bash
# 1. Проверка зависимостей
./scripts/check_dependencies.sh

# 2. Авто-исправление (если нужно)
sudo ./scripts/auto_fix_dependencies.sh

# 3. Базовое развертывание
python3 scripts/deploy_all_optimized.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true
```

Скрипт автоматически:
- Установит master, подскажет команду для join воркера
- Развернет **сетевые компоненты на VPS**: ingress-nginx, cert-manager и ClusterIssuer (HTTP-01)
- Применит базовые манифесты
- **На worker**: Prometheus/Grafana с автопровиженингом дашбордов
- **На worker**: Kubevious (helm) + Ingress/TLS
- Включит VPA, registry cache
- Добавит GPU мониторинг (dcgm-exporter) и панели для GPU
- Выполнит smoke-check HTTPS

## Для заблокированного порта 80

Если порт 80 заблокирован провайдером — запустите с флагом `--dns01` и задайте переменную окружения `CF_API_TOKEN` на VPS до запуска скрипта:

```bash
export CF_API_TOKEN=...  # Cloudflare API Token
python3 scripts/deploy_all_optimized.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true --dns01
```

## Enterprise фазы

После базового развертывания можно добавить enterprise компоненты:

```bash
# Phase 1: ELK Stack + KEDA Auto-scaling
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 1

# Phase 2: ArgoCD GitOps + Istio Service Mesh
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 2

# Phase 3: Jaeger Tracing + Security (OPA/Falco)
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 3

# Все фазы подряд
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase all
```

## 📡 Сетевые характеристики

### Master VPS (10 Gbps)
- **Внешний трафик**: 10 Gbps (1.25 ГБ/с) максимум
- **Оптимизация**: 512MB network buffers, TCP BBR, fq qdisc
- **Компоненты**: K3S API Server, ingress-nginx, cert-manager, CoreDNS

### Worker Home PC
- **Связь с VPS**: ~10 МБ/с (Tailscale, межузловая API/метрики)
- **Прямой интернет**: 100 Мбит/с (для Docker pulls, updates)
- **Компоненты**: Prometheus, Grafana, ELK, ArgoCD, Istio, Jaeger

## 🔍 Проверка зависимостей

**ОБЯЗАТЕЛЬНО первым шагом:**

```bash
# Комплексная проверка
./scripts/check_dependencies.sh

# Если есть проблемы
sudo ./scripts/auto_fix_dependencies.sh

# Повторная проверка
./scripts/check_dependencies.sh
```

Новые проверки в check_dependencies.sh:
- ✅ Проверка размещения ingress-nginx на master VPS
- ✅ Проверка размещения cert-manager на master VPS
- ✅ Auto-fix команды для перемещения компонентов
- ✅ Проверка Prometheus/Grafana на worker