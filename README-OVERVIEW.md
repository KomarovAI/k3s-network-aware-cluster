# Обзор

- Grafana: https://grafana.cockpit.work.gd
- Kubevious: https://kubevious.cockpit.work.gd

# One-shot deploy

На VPS выполните:

```bash
sudo apt-get update && sudo apt-get install -y curl jq python3 python3-yaml
python3 scripts/deploy_all.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true
```

Скрипт:
- Установит master, подскажет команду для join воркера
- Развернет ingress-nginx, cert-manager и ClusterIssuer (HTTP-01)
- Применит базовые манифесты
- Настроит Prometheus/Grafana с автопровиженингом дашбордов
- Поставит Kubevious (helm) + Ingress/TLS
- Включит VPA, registry cache
- Добавит GPU мониторинг (dcgm-exporter) и панели для GPU
- Выполнит smoke-check HTTPS

Если порт 80 заблокирован провайдером — запустите с флагом `--dns01` и задайте переменную окружения `CF_API_TOKEN` на VPS до запуска скрипта:

```bash
export CF_API_TOKEN=...  # Cloudflare API Token
python3 scripts/deploy_all.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true --dns01
```
