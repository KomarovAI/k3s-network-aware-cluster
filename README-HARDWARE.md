# K3S Hardware Profile

## Master (VPS)
- CPU: 3 vCPU
- RAM: 4 GB
- Storage: 100 GB NVMe
- Network: 1 250 МБ/с внешний канал (Интернет + связь с воркерами через Tailscale)
- Role: Control plane only (ingress + monitoring allowed)

## Workers (Home PCs) — минимум 2 узла
- CPU: 26 CPU cores (per node)
- RAM: 64 GB (per node)
- Storage: 1 TB NVMe (per node)
- GPU: NVIDIA RTX 3090 (per node)
- Network: 10 МБ/с до VPS (через Tailscale), 1 ГБ/с локальная LAN
- Role: All workloads (AI/ML, DB, web)

Примечание: Конфигурация репозитория (лейблы/таинты, HPA/PDB, ingress/monitoring ресурсы) учитывает **10 МБ/с** канал у воркеров и **1 250 МБ/с** у VPS. Для других профилей адаптируйте manifests/prod и скрипты в scripts/.
