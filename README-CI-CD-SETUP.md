# 🚀 CI/CD Setup Guide

> Полное руководство по настройке **прямого CI/CD** для сервисов через **GitHub Actions → Docker Hub → kubectl**

[![Direct CI/CD](https://img.shields.io/badge/CI%2FCD-Direct-green)](https://github.com/KomarovAI/k3s-network-aware-cluster)
[![Docker Hub](https://img.shields.io/badge/Registry-Docker%20Hub-blue)](https://hub.docker.com/)
[![Production Ready](https://img.shields.io/badge/Production-Ready-green)](https://github.com/KomarovAI/k3s-network-aware-cluster)

## 🎯 Подход: **"Работает код = деплоится автоматически"**

```
Код сервиса → GitHub Actions → Docker Hub → Прямой деплой в кластер
     ↓              ↓              ↓                    ↓
  тесты прошли → образ собран → kubectl apply →     ✅ Живой сервис
```

**Преимущества:**
- ✅ **Надежность**: деплой только если тесты прошли
- ✅ **Простота**: никаких дополнительных GitOps репо
- ✅ **Контроль**: все этапы в GitHub Actions
- ✅ **Быстрые откаты**: kubectl rollout undo

---

## 1️⃣ Настройка кластера (однократно)

### Шаг 1: Основной кластер
```bash
# На VPS
git clone https://github.com/KomarovAI/k3s-network-aware-cluster.git
cd k3s-network-aware-cluster
git checkout feature/vps-optimization

./scripts/check_dependencies.sh
python3 scripts/deploy_all_optimized.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true
```

### Шаг 2: Enterprise компоненты для CI/CD
```bash
# Phase 1: ELK + KEDA + Enhanced Monitoring
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 1 --confirm

# Phase 2: CI/CD Support + Istio Service Mesh
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 2 --confirm

# Phase 3 (опционально): Jaeger + Security
python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 3 --confirm
```

### Шаг 3: Получение CI/CD токена
```bash
# На VPS после установки Phase 2
echo "🔐 CI/CD токен для GitHub Secrets:"
kubectl create token cicd-deploy --duration=8760h

# Копируем этот токен в GitHub
```

---

## 2️⃣ Настройка GitHub Secrets

### Минимальные секреты (для каждого сервиса):

#### **Repository Secrets** (Settings → Secrets and variables → Actions):
```
DOCKERHUB_USERNAME=your_username
DOCKERHUB_TOKEN=dckr_pat_xxxxxxxxxx
KUBE_TOKEN=eyJhbGciOiJSUzI1NiIs...  # Токен с Предыдущего Шага
```

#### **Repository Variables**:
```
DOMAIN_BASE=cockpit.work.gd
KUBE_SERVER=https://your-vps-tailscale-ip:6443
```

### Опциональные секреты:
```
# Уведомления
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=-1001234567890

# Для private registry
GHCR_TOKEN=ghp_xxxxxxxxx  # GitHub Container Registry

# Для секретов сервиса
DB_PASSWORD=secure_password
API_SECRET_KEY=your_secret_key
JWT_SECRET=jwt_signing_key
```

---

## 3️⃣ Создание сервиса

### Минимальная структура репо сервиса:
```
my-service/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions workflow
├── k8s/
│   ├── deployment.yaml      # Kubernetes manifests
│   ├── service.yaml
│   └── ingress.yaml
├── src/                     # Код сервиса
├── tests/                   # Тесты
├── Dockerfile
└── docker-compose.test.yml  # Интеграционные тесты
```

### Копирование шаблонов:
```bash
# Копируем шаблоны в свой сервис
mkdir -p my-service/{.github/workflows,k8s}

# GitHub Actions workflow
curl -o my-service/.github/workflows/deploy.yml \
  https://raw.githubusercontent.com/KomarovAI/k3s-network-aware-cluster/feature/vps-optimization/examples/github-actions-deploy.yml

# Kubernetes manifests
curl -o my-service/k8s/deployment.yaml \
  https://raw.githubusercontent.com/KomarovAI/k3s-network-aware-cluster/feature/vps-optimization/examples/service-manifests-template/deployment.yaml

curl -o my-service/k8s/service.yaml \
  https://raw.githubusercontent.com/KomarovAI/k3s-network-aware-cluster/feature/vps-optimization/examples/service-manifests-template/service.yaml

curl -o my-service/k8s/ingress.yaml \
  https://raw.githubusercontent.com/KomarovAI/k3s-network-aware-cluster/feature/vps-optimization/examples/service-manifests-template/ingress.yaml
```

### Настройка параметров:
```bash
# Отредактируйте в .github/workflows/deploy.yml:
env:
  SERVICE_NAME: my-awesome-service  # Название сервиса
  KUBE_NAMESPACE: production        # production или staging
  KUBE_SERVER: https://YOUR-VPS-IP:6443  # IP вашего VPS
```

---

## 4️⃣ Паттерны деплоя

### А. **Простой сервис** (статичный фронтенд, API):
```yaml
# В GitHub Actions:
- name: Deploy
  run: |
    kubectl set image deployment/my-service my-service=komarovai/my-service:${{ github.sha }} -n production
    kubectl rollout status deployment/my-service -n production --timeout=300s
```

### Б. **Сервис с базой данных**:
```yaml
# 1. Сначала миграции бД (если нужны)
- name: Run DB migrations
  run: |
    kubectl run migration-${{ github.sha }} --rm -i --restart=Never \
      --image=komarovai/my-service:${{ github.sha }} \
      --env="DB_URL=${{ secrets.DB_URL }}" \
      -- python manage.py migrate

# 2. Потом обновляем сервис
- name: Deploy service
  run: |
    kubectl set image deployment/my-service my-service=komarovai/my-service:${{ github.sha }} -n production
```

### В. **Микросервисная архитектура** (несколько компонентов):
```yaml
# Обновляем несколько deployments
- name: Deploy all components
  run: |
    # API
    kubectl set image deployment/api-service api-service=komarovai/api:${{ github.sha }} -n production
    # Worker
    kubectl set image deployment/worker-service worker-service=komarovai/worker:${{ github.sha }} -n production
    # Frontend
    kubectl set image deployment/frontend frontend=komarovai/frontend:${{ github.sha }} -n production
    
    # Ожидаем все одновременно
    kubectl rollout status deployment/api-service -n production &
    kubectl rollout status deployment/worker-service -n production &
    kubectl rollout status deployment/frontend -n production &
    wait
```

### Г. **Canary деплой** (если включен Istio):
```yaml
- name: Canary deployment (5% traffic)
  run: |
    # Создаем canary deployment
    kubectl patch deployment my-service -n production --patch \
      '{"metadata":{"name":"my-service-canary"}}'
    kubectl set image deployment/my-service-canary my-service=komarovai/my-service:${{ github.sha }} -n production
    
    # Обновляем Istio VirtualService (5% на canary)
    kubectl patch virtualservice my-service -n production --patch \
      '{"spec":{"http":[{"route":[{"destination":{"host":"my-service"},"weight":95},{"destination":{"host":"my-service-canary"},"weight":5}]}]}}'
```

---

## 5️⃣ Пример полного workflow

### Подготовка сервиса:
```bash
# 1. Создаем новый репозиторий
mkdir my-awesome-api && cd my-awesome-api
git init && git remote add origin https://github.com/YourUsername/my-awesome-api.git

# 2. Копируем шаблоны
mkdir -p .github/workflows k8s
curl -o .github/workflows/deploy.yml https://raw.githubusercontent.com/KomarovAI/k3s-network-aware-cluster/feature/vps-optimization/examples/github-actions-deploy.yml
curl -o k8s/deployment.yaml https://raw.githubusercontent.com/KomarovAI/k3s-network-aware-cluster/feature/vps-optimization/examples/service-manifests-template/deployment.yaml
curl -o k8s/service.yaml https://raw.githubusercontent.com/KomarovAI/k3s-network-aware-cluster/feature/vps-optimization/examples/service-manifests-template/service.yaml
curl -o k8s/ingress.yaml https://raw.githubusercontent.com/KomarovAI/k3s-network-aware-cluster/feature/vps-optimization/examples/service-manifests-template/ingress.yaml

# 3. Настраиваем параметры
# Отредактируйте SERVICE_NAME и другие параметры в файлах

# 4. Первоначальный деплой вручную
export SERVICE_NAME=my-awesome-api
export KUBE_NAMESPACE=production 
export IMAGE_TAG=v1.0.0
export DOMAIN_BASE=cockpit.work.gd
export DOCKERHUB_USERNAME=your_username
export DOCKER_REGISTRY=docker.io

# Применяем манифесты с подстановкой
envsubst < k8s/deployment.yaml | kubectl apply -f -
envsubst < k8s/service.yaml | kubectl apply -f -
envsubst < k8s/ingress.yaml | kubectl apply -f -

# 5. Пушим в GitHub
git add . && git commit -m "Initial service setup"
git push -u origin main
```

### Автоматический деплой:
```bash
# Любое обновление кода:
git add .
git commit -m "fix: important bugfix"
git push

# → GitHub Actions автоматически:
#   ✅ Запустит тесты
#   ✅ Соберет Docker образ
#   ✅ Запушит в Docker Hub
#   ✅ Обновит кластер
#   ✅ Проверит health check
#   🎉 Сервис обновлен!
```

---

## 6️⃣ Мониторинг и отладка

### Grafana — единый дашборд:
- **URL**: https://grafana.cockpit.work.gd
- **Dashboard**: "Cluster Enterprise Overview" — видны все сервисы, CPU, мемори, сеть, auto-scaling
- **Метрики сервиса**: автоматически собираются (label `monitoring: enabled`)

### Kibana — централизованные логи:
- **URL**: https://kibana.cockpit.work.gd  
- **Логи сервиса**: автоматически собираются через Filebeat
- **Поиск**: по namespace, сервису, ошибкам, времени

### Jaeger — tracing между сервисами:
- **URL**: https://jaeger.cockpit.work.gd
- **Трейсы**: автоматически через Istio sidecar

---

## 7️⃣ Auto-scaling настройка

### HPA (стандартный):
```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-service-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### KEDA ScaledObject (для event-driven scaling):
```yaml
# keda-scaling.yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: my-service-scaler
  namespace: production
spec:
  scaleTargetRef:
    name: my-service
  minReplicaCount: 1
  maxReplicaCount: 20
  cooldownPeriod: 300  # 5 мин scale-down cooldown
  
  triggers:
  # По HTTP метрикам
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc:9090
      metricName: http_requests_per_second
      threshold: "100"
      query: sum(rate(http_requests_total{job="my-service"}[1m]))
  
  # По очереди Redis/RabbitMQ
  - type: redis
    metadata:
      address: redis.default.svc:6379
      listName: my-service-queue
      listLength: "10"
  
  # По cron расписанию (например, ночные отчеты)
  - type: cron
    metadata:
      timezone: Europe/Moscow
      start: "0 2 * * *"   # 02:00 мск
      end: "0 4 * * *"     # 04:00 мск
      desiredReplicas: "5"
```

---

## 8️⃣ Troubleshooting

### Ошибки деплоя:
```bash
# Проверка статуса deployment
kubectl rollout status deployment/my-service -n production

# Логи подов
kubectl logs -n production -l app=my-service --tail=100

# Откат к предыдущей версии
kubectl rollout undo deployment/my-service -n production

# Проверка сети
kubectl get ingress -n production
kubectl describe ingress my-service -n production
```

### Проблемы с TLS:
```bash
# Проверка сертификатов
kubectl get certificates -n production
kubectl describe certificate my-service-tls -n production

# Логи cert-manager
kubectl logs -n cert-manager deployment/cert-manager
```

### Проблемы с registry:
```bash
# Проверка пулла образов
kubectl describe pod -n production -l app=my-service

# Проверка registry secrets
kubectl get secrets -n production
```

---

## 9️⃣ Best Practices

### Безопасность:
- ✅ Используйте **ServiceAccount токены** вместо admin kubeconfig
- ✅ **Минимальные RBAC права** для каждого сервиса
- ✅ **NetworkPolicies** для ограничения трафика
- ✅ **Security contexts** (runAsNonRoot, readOnlyRootFilesystem)

### Производительность:
- ✅ **Resource limits** обязательны
- ✅ **Health checks** (liveness + readiness probes)
- ✅ **Anti-affinity** для распределения по нодам
- ✅ **PodDisruptionBudget** для HA

### Мониторинг:
- ✅ **Prometheus метрики**: /metrics endpoint обязателен
- ✅ **Логи в stdout**: автоматическая сборка через ELK
- ✅ **Distributed tracing**: автоматически через Istio sidecar

---

## 🎉 Результат

После настройки получаешь **enterprise-grade CI/CD платформу**:

🚀 **git push** → автотесты → Docker Hub → **автодеплой** → **автомониторинг**

### Что получаешь автоматически:
- ✅ **TLS сертификаты** (Let's Encrypt)
- ✅ **Auto-scaling** (по CPU/Memory/очередям/cron)
- ✅ **Централизованные логи** (с поиском)
- ✅ **Monitoring** (метрики + алерты)
- ✅ **Service mesh** (mTLS + traffic management)
- ✅ **Distributed tracing** (debugging межсервисных вызовов)
- ✅ **Security policies** (автоматическая проверка)

### Унифицированный дашборд:
✨ **https://grafana.cockpit.work.gd** — все сервисы, метрики, логи, трейсы в **одном месте**!

---

## 📈 Пример реального сервиса

Полный пример смотри в: **[examples/service-manifests-template/](examples/service-manifests-template/)**

**От кода до production за 5 минут! 🚀**