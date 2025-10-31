# K3S Enhanced Hybrid Cluster 🚀

> Production-ready K3S cluster for enhanced VPS (3 vCPU, 4GB RAM, 100GB NVMe, 1.25 Gbps) + single Home PC worker (26 CPU, 64GB RAM, 1TB NVMe, RTX 3090) with in-cluster TLS, monitoring, and beautiful dashboards.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Production Ready](https://img.shields.io/badge/Production-Ready-green)](https://github.com/KomarovAI/k3s-network-aware-cluster)
[![Security](https://img.shields.io/badge/Security-NSA%2FCISA-blue)](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-release-kubernetes-hardening-guidance/)

## 🔗 Обзор

- Grafana: https://grafana.cockpit.work.gd
- Kubevious: https://kubevious.cockpit.work.gd

## 🧩 Профиль железа и сети

- VPS (master): 3 vCPU, 4 GB RAM, 100 GB NVMe, 1.25 Gbps; роль: control plane + ingress + monitoring
- Home PC (worker, один): 26 CPU, 64 GB RAM, 1 TB NVMe, RTX 3090; канал до VPS ~10 МБ/с (Tailscale)

Оптимизации: TCP BBR, сжатие (brotli/gzip), Priority-and-Fairness, tuned kube-apiserver/etcd/kubelet, image GC, VPA, pull-through registry cache.

## 🚀 Быстрый старт (одной командой)

На VPS выполните:

```bash
sudo apt-get update && sudo apt-get install -y curl jq python3 python3-yaml
python3 scripts/deploy_all.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true
```

Скрипт сделает:
- Установка master; выдача join-скрипта для воркера
- Установка ingress-nginx, cert-manager, ClusterIssuer (HTTP-01)
- Применение базовых manifests
- Развёртывание Prometheus + Grafana с автопровиженингом datasource и дашбордов
- Установка Kubevious (Helm) и Ingress с TLS
- Включение VPA и registry cache
- (Опционально) GPU мониторинг (nvidia/dcgm-exporter) + GPU панели
- Smoke-check TLS и готовность веб-интерфейсов

Если порт 80 заблокирован провайдером — используйте DNS-01 (Cloudflare):

```bash
export CF_API_TOKEN=...  # Cloudflare API token
python3 scripts/deploy_all.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true --dns01
```

## 🌐 TLS и Ingress

- cert-manager внутри кластера: ClusterIssuer для Let’s Encrypt (HTTP-01 по умолчанию, DNS-01 опционально)
- ingress-nginx с безопасной конфигурацией (TLS 1.2/1.3, шифры, brotli/gzip)

## 📈 Мониторинг и дашборды (из коробки)

- Prometheus + Grafana (автопровиженинг):
  - K8S Core Overview — API/etcd/Nodes/Workloads/Ingress
  - Hybrid Cluster Overview — профиль VPS master + один home-pc worker (CPU/RAM/FS/Network/Ingress/Control Plane)
  - (Опционально) GPU панели: Utilization, VRAM, Temperature, Power
- Все панели подгружаются автоматически при деплое

## 🧭 Kubevious — визуальный аудит кластера

- Helm-чарт с Ingress/TLS (kubevious.cockpit.work.gd)
- Глубокая визуализация приложений, связи/зависимости, rule engine, подсветка ошибок

## 🔒 Безопасность

- Pod Security Standards v1.29 (restricted), Zero-Trust NetworkPolicies, RBAC hardening
- Хардeнинг по NSA/CISA и CIS Benchmark (production_hardening.py)

## 📦 Registry cache

- Внутрикластерный pull-through cache с credentials из секретов; экономия трафика на загрузке образов

## 🛠️ Управление и скрипты

- scripts/install_cluster_enhanced.py — установка master/worker
- scripts/production_hardening.py — применение правил безопасности и оптимизаций
- scripts/deploy_all.py — "одной кнопкой" весь стек (рекомендуется)

## ⚙️ Примечания

- Один воркер: replicas по умолчанию = 1; PDB не навязываются
- Если включен GPU мониторинг — требуется NVIDIA драйвер и nvidia-container-toolkit на воркере
- Для DNS-01 нужен Cloudflare токен (CF_API_TOKEN)

## 📚 Дополнительно

- README-OVERVIEW.md — короткая памятка по развёртыванию и ссылкам
- README-HARDWARE.md — детали железа и апгрейдов
