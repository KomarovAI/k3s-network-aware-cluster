# K3S Enhanced Hybrid Cluster 🚀

> Production-ready K3S cluster for enhanced VPS (3 vCPU, 4GB RAM, 100GB NVMe, 1.25 Gbps) + single Home PC worker (26 CPU, 64GB RAM, 1TB NVMe, RTX 3090) with in-cluster TLS, monitoring, and beautiful dashboards.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Production Ready](https://img.shields.io/badge/Production-Ready-green)](https://github.com/KomarovAI/k3s-network-aware-cluster)
[![Security](https://img.shields.io/badge/Security-NSA%2FCISA-blue)](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-release-kubernetes-hardening-guidance/)
[![K3S](https://img.shields.io/badge/K3S-v1.29+-brightgreen)](https://k3s.io/)
[![CIS Benchmark](https://img.shields.io/badge/CIS-Benchmark-orange)](https://www.cisecurity.org/benchmark/kubernetes)

## 🔗 Обзор

- **Grafana**: https://grafana.cockpit.work.gd
- **Kubevious**: https://kubevious.cockpit.work.gd

## 🏗️ Архитектура и железо

### Профиль конфигурации
- **VPS (master)**: 3 vCPU, 4 GB RAM, 100 GB NVMe, 1.25 Gbps
  - Роль: control plane + ingress + monitoring
- **Home PC (worker)**: 26 CPU, 64 GB RAM, 1 TB NVMe, RTX 3090
  - Соединение с VPS: ~10 МБ/с (Tailscale)

### Оптимизации
- **Сеть**: TCP BBR, сжатие (brotli/gzip), Priority-and-Fairness
- **Ресурсы**: tuned kube-apiserver/etcd/kubelet, image GC, VPA
- **Кэширование**: pull-through registry cache
- **Безопасность**: CIS Benchmark, NSA/CISA hardening

## 🚀 Быстрый старт

### Вариант 1: Улучшенный деплой (рекомендуется)

```bash
# Установка зависимостей
sudo apt-get update && sudo apt-get install -y curl jq python3 python3-yaml gettext-base
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Развертывание с улучшенной обработкой ошибок
python3 scripts/deploy_all_improved.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true
```

### Вариант 2: Стандартный деплой

```bash
# Установка базовых зависимостей
sudo apt-get update && sudo apt-get install -y curl jq python3 python3-yaml

# Стандартное развертывание
python3 scripts/deploy_all.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true
```

### DNS-01 (для заблокированного порта 80)

```bash
export CF_API_TOKEN="your_cloudflare_token"
python3 scripts/deploy_all_improved.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true --dns01
```

## 🔧 Управление и оптимизация

### Проверка состояния кластера

```bash
# Полная проверка здоровья кластера
python3 scripts/cluster_optimizer.py --check

# Генерация детального отчета
python3 scripts/cluster_optimizer.py --report --output cluster_report.json
```

### Применение оптимизаций

```bash
# Автоматическое применение оптимизаций
python3 scripts/cluster_optimizer.py --apply

# Ручной hardening (расширенный)
python3 scripts/production_hardening.py
```

### Мониторинг производительности

```bash
# Проверка ресурсов нод
kubectl top nodes

# Анализ использования ресурсов подов
kubectl top pods --all-namespaces

# Проверка сетевых политик
kubectl get networkpolicy --all-namespaces
```

## 🌐 TLS и Ingress

- **cert-manager**: автоматические Let's Encrypt сертификаты
- **ClusterIssuer**: HTTP-01 (по умолчанию) или DNS-01 (Cloudflare)
- **ingress-nginx**: с безопасной конфигурацией (TLS 1.2/1.3, современные шифры)
- **Сжатие**: brotli/gzip для оптимизации трафика

## 📈 Мониторинг и визуализация

### Стек мониторинга (автопровиженинг)
- **Prometheus**: метрики кластера и приложений
- **Grafana**: готовые дашборды:
  - K8S Core Overview — API/etcd/Nodes/Workloads/Ingress
  - Hybrid Cluster Overview — профиль VPS master + home PC worker
  - GPU Monitoring — Utilization, VRAM, Temperature, Power (опционально)

### Kubevious — визуальный аудит
- **Helm-чарт** с готовым Ingress/TLS
- **Глубокая визуализация**: приложения, связи, зависимости
- **Rule engine**: автоматическая подсветка проблем
- **Доступ**: kubevious.cockpit.work.gd

## 🔒 Безопасность и соответствие

### Стандарты безопасности
- **Pod Security Standards** v1.29 (restricted)
- **Zero-Trust NetworkPolicies**
- **RBAC hardening** с принципом наименьших привилегий
- **CIS Kubernetes Benchmark** автоматическое применение
- **NSA/CISA** рекомендации по хардингу

### Функции безопасности
```bash
# Проверка соответствия CIS
python3 scripts/cluster_optimizer.py --check

# Применение политик безопасности
python3 scripts/cluster_optimizer.py --apply

# Аудит прав доступа
kubectl auth can-i --list --as=system:serviceaccount:default:default
```

## 📦 Оптимизация ресурсов

### Кэширование и производительность
- **Pull-through registry cache**: экономия трафика на загрузке образов
- **VPA (Vertical Pod Autoscaler)**: автоматическая оптимизация ресурсов
- **Image GC**: автоматическая очистка неиспользуемых образов
- **CoreDNS оптимизация**: кэширование DNS с настроенными таймаутами

### Мониторинг GPU (опционально)
```bash
# Проверка GPU метрик
kubectl get pods -n monitoring | grep dcgm

# Просмотр GPU дашбордов в Grafana
# https://grafana.cockpit.work.gd/d/gpu-overview
```

## 🛠️ Управляющие скрипты

| Скрипт | Назначение | Использование |
|--------|------------|---------------|
| `deploy_all_improved.py` | Улучшенное развертывание с проверками | Основной способ развертывания |
| `deploy_all.py` | Стандартное развертывание | Простой способ развертывания |
| `cluster_optimizer.py` | Проверка и оптимизация кластера | Регулярная проверка здоровья |
| `install_cluster_enhanced.py` | Установка master/worker нод | Используется автоматически |
| `production_hardening.py` | Расширенный hardening | Дополнительная безопасность |

## 🔄 Жизненный цикл кластера

### Начальное развертывание
1. **Подготовка VPS** — установка зависимостей
2. **Развертывание master** — `deploy_all_improved.py`
3. **Подключение worker** — скрипт join генерируется автоматически
4. **Проверка состояния** — `cluster_optimizer.py --check`
5. **Финальная оптимизация** — `cluster_optimizer.py --apply`

### Регулярное обслуживание
```bash
# Еженедельная проверка (рекомендуется)
python3 scripts/cluster_optimizer.py --check

# Ежемесячная оптимизация
python3 scripts/cluster_optimizer.py --apply

# Генерация отчета для анализа
python3 scripts/cluster_optimizer.py --report --output monthly_report.json
```

### Обновление компонентов
```bash
# Обновление cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml

# Обновление ingress-nginx
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/cloud/deploy.yaml

# Обновление Kubevious
helm upgrade kubevious kubevious/kubevious -n kubevious
```

## 🚨 Устранение неисправностей

### Частые проблемы

**Проблема**: Сертификаты не выдаются
```bash
# Проверка ClusterIssuer
kubectl describe clusterissuer letsencrypt-prod

# Проверка заказов сертификатов
kubectl get certificaterequests --all-namespaces

# Логи cert-manager
kubectl logs -n cert-manager deployment/cert-manager
```

**Проблема**: Ingress недоступен
```bash
# Проверка состояния ingress-nginx
kubectl get pods -n ingress-nginx

# Проверка логов
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller

# Проверка конфигурации
kubectl get ingress --all-namespaces
```

**Проблема**: Worker нода не подключается
```bash
# На master ноде - проверка токена
sudo cat /var/lib/rancher/k3s/server/node-token

# На worker ноде - проверка подключения
curl -k https://MASTER_IP:6443/ping

# Проверка Tailscale соединения
tailscale status
```

### Диагностика с помощью optimizer
```bash
# Комплексная диагностика
python3 scripts/cluster_optimizer.py --check

# Детальный анализ проблем
python3 scripts/cluster_optimizer.py --report | jq '.warnings[]'
```

## ⚙️ Конфигурационные особенности

### Для одного воркера
- **Replicas по умолчанию**: 1 (адаптировано для гибридной конфигурации)
- **PDB (Pod Disruption Budget)**: не применяются автоматически
- **Taints/Tolerations**: мастер принимает рабочие нагрузки при необходимости

### GPU поддержка
- **Требования**: NVIDIA драйвер + nvidia-container-toolkit на worker ноде
- **Мониторинг**: DCGM exporter для метрик GPU
- **Дашборды**: автоматическое подключение GPU панелей в Grafana

### Сетевые ограничения
- **Медленный канал**: оптимизация для ~10 МБ/с между VPS и домашним PC
- **Сжатие трафика**: включено для всех HTTP соединений
- **DNS оптимизация**: кэширование на 30 секунд

## 📚 Дополнительная документация

- **[README-OVERVIEW.md](README-OVERVIEW.md)** — краткая памятка по развертыванию
- **[README-HARDWARE.md](README-HARDWARE.md)** — детали железа и возможных апгрейдов
- **[CLEANUP_ANALYSIS.md](CLEANUP_ANALYSIS.md)** — анализ оптимизации проекта

## 🆘 Поддержка

Для вопросов и проблем:
1. Проверьте [Issues](https://github.com/KomarovAI/k3s-network-aware-cluster/issues)
2. Запустите диагностику: `python3 scripts/cluster_optimizer.py --check`
3. Создайте issue с выводом диагностики и описанием проблемы

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE)

---

**🎯 TL;DR**: Готовый к продакшну K3S кластер для гибридной VPS+HomeLab конфигурации с автоматическим TLS, мониторингом, безопасностью по CIS Benchmark и красивыми дашбордами. Развертывание одной командой за 10 минут.
