# 📈 ELK Stack на Worker ноде - Централизованное логирование

## 🔥 Краткое описание

ELK Stack (Elasticsearch + Logstash + Kibana + Filebeat) автоматически развертывается на **worker ноде** для максимальной производительности и минимальной нагрузки на master.

### ⚡ Преимущества размещения на Worker:
- **64GB RAM** vs 4GB на master → Elasticsearch может использовать до 8-16GB
- **26 CPU cores** vs 3 на master → быстрая индексация и парсинг
- **SSD 1TB** → большие индексы без конкуренции с etcd
- **Мастер остается стабильным** и отзывчивым

## 🚀 Быстрый запуск

### Обычный режим (Elasticsearch 8GB RAM, 15 дней retention)
```bash
# Одновременно с остальным кластером
python3 scripts/deploy_all_optimized.py \
  --domain cockpit.work.gd \
  --email artur.komarovv@gmail.com \
  --gpu true \
  --enable-elk

# Или отдельно только ELK
python3 scripts/deploy_elk_on_worker.py --domain cockpit.work.gd
```

### Облегченный режим (Elasticsearch 2GB RAM, 7 дней retention)
```bash
# Если worker нода слабая или нужно экономить ресурсы
python3 scripts/deploy_all_optimized.py \
  --domain cockpit.work.gd \
  --email artur.komarovv@gmail.com \
  --enable-elk \
  --elk-light \
  --elk-retention 7
```

## 📋 Компоненты ELK Stack

### 🔍 Elasticsearch (основной компонент)
- **Назначение**: поисковый движок для индексации логов
- **Ресурсы**: 2-8GB RAM, 1-4 CPU cores (зависит от режима)
- **Storage**: 20-50GB PVC для индексов
- **Особенности**: single-node конфигурация, автоочистка старых логов

### 🔄 Logstash (преобразование логов)
- **Назначение**: парсинг, фильтрация и обогащение логов
- **Ресурсы**: 512MB-1GB RAM, 200m-1000m CPU
- **Порты**: 5044 (Beats input), 8080 (HTTP input)
- **Особенности**: JSON парсинг, Kubernetes metadata enrichment

### 📈 Kibana (UI для визуализации)
- **Назначение**: веб-интерфейс для поиска и анализа логов
- **Ресурсы**: 256-512MB RAM, 200m-1000m CPU
- **URL**: https://kibana.{domain}
- **Особенности**: автоматический Ingress с TLS

### 📦 Filebeat (сбор логов)
- **Назначение**: агент сбора логов со всех нод кластера
- **Ресурсы**: 128-256MB RAM, 50-200m CPU на каждой ноде
- **Развертывание**: DaemonSet (на всех нодах)
- **Особенности**: Kubernetes autodiscovery, hostNetwork для доступа к логам

### 🔍 Jaeger (опционально)
- **Назначение**: distributed tracing для микросервисов
- **Ресурсы**: 384MB-1GB RAM, 200m-1000m CPU
- **URL**: https://jaeger.{domain} 
- **Особенности**: all-in-one режим, OTLP collector

### 🔍 Blackbox Exporter (опционально)
- **Назначение**: мониторинг внешних HTTP/HTTPS endpoints
- **Ресурсы**: 96-256MB RAM, 50-200m CPU
- **Интеграция**: автоматический service discovery в Prometheus

## 📋 Режимы развертывания

| Режим | Elasticsearch | Logstash | Storage | Retention | Jaeger |
|--------|---------------|----------|---------|-----------|--------|
| **Обычный** | 8GB RAM, 4CPU | 1GB RAM | 50Gi | 15 дней | ✅ |
| **Облегченный** | 2GB RAM, 1CPU | 512MB RAM | 20Gi | 7 дней | ❌ |

## 🔧 Команды управления

### Развертывание
```bash
# Полный ELK с Jaeger
python3 scripts/deploy_elk_on_worker.py --domain cockpit.work.gd --retention-days 15

# Облегченный режим
python3 scripts/deploy_elk_on_worker.py --domain cockpit.work.gd --retention-days 7 --light-mode

# Проверка статуса
kubectl -n logging get pods -o wide
kubectl -n logging get ingress
```

### Откат
```bash
# Полное удаление ELK Stack
python3 scripts/deploy_elk_on_worker.py --rollback

# Или вручную
kubectl delete namespace logging
```

### Мониторинг
```bash
# Проверка здоровья Elasticsearch
kubectl -n logging exec deployment/elasticsearch -- curl -s localhost:9200/_cluster/health | jq .

# Просмотр индексов
kubectl -n logging exec deployment/elasticsearch -- curl -s localhost:9200/_cat/indices

# Логи Logstash
kubectl -n logging logs deployment/logstash -f

# Проверка сбора логов
kubectl -n logging logs daemonset/filebeat --tail=50
```

## 🔗 Интеграция с мониторингом

### Prometheus метрики
- Elasticsearch автоматически экспортирует метрики в Prometheus
- ServiceMonitor настраивается автоматически
- Grafana дашборды для ELK метрик

### Grafana дашборды
Рекомендуемые дашборды для импорта:
- **Elasticsearch Cluster**: ID 266 (метрики кластера)
- **Logstash Monitoring**: ID 14191 (производительность пайплайнов)
- **Kubernetes Logs**: Custom dashboard для логов подов

## 📋 Конфигурация и настройки

### Elasticsearch оптимизации
- **Single-node режим**: для минимального overhead
- **Index Lifecycle Management**: автоочистка старых логов
- **Disk watermarks**: 85% (low) / 90% (high) для защиты от переполнения
- **Memory allocation**: JVM heap = 50% от общей RAM (ES best practice)

### Logstash pipeline
- **Input**: Beats (port 5044) + HTTP (port 8080)
- **Filters**: JSON парсинг, Kubernetes metadata, timestamp normalization
- **Output**: Elasticsearch с daily rotation (`logs-k3s-YYYY.MM.dd`)

### Filebeat автообнаружение
- **Kubernetes autodiscovery**: автоматические конфигурации для контейнеров
- **Metadata enrichment**: namespace, pod name, container name
- **Multi-line handling**: стеки ошибок Java/Python

## 📡 Сетевые соображения

### Латентность
- **Master → Worker**: 10-50ms через Tailscale
- **Log shipping**: некритично для логов (не real-time)
- **Kibana UI**: доступен через Ingress на master

### Безопасность
- **TLS**: все Ingress автоматически получают Let's Encrypt сертификаты
- **RBAC**: Filebeat имеет минимальные права read-only
- **Network isolation**: компоненты ELK изолированы в namespace `logging`

## 📈 Мониторинг и алерты

### Ключевые метрики (доступны в Prometheus)
```bash
# Elasticsearch cluster health
elasticsearch_cluster_health_status

# Использование диска
elasticsearch_filesystem_data_free_bytes

# Производительность индексации
elasticsearch_indices_indexing_index_total

# JVM memory usage
elasticsearch_jvm_memory_used_bytes

# Logstash events per second
logstash_events_in_total
logstash_events_out_total
```

### Рекомендуемые алерты
```yaml
# Elasticsearch cluster health
- alert: ElasticsearchClusterRed
  expr: elasticsearch_cluster_health_status{color="red"} == 1
  for: 5m
  annotations:
    summary: "Elasticsearch cluster health is RED"
    
# Disk space
- alert: ElasticsearchDiskSpaceLow
  expr: elasticsearch_filesystem_data_free_percent < 15
  for: 5m
  annotations:
    summary: "Elasticsearch disk space below 15%"

# Memory usage
- alert: ElasticsearchHighMemory
  expr: elasticsearch_jvm_memory_used_percent > 90
  for: 10m
  annotations:
    summary: "Elasticsearch JVM memory usage > 90%"
```

## 🔍 Первые шаги после установки

### 1. Настройка Kibana
1. Открыть https://kibana.{domain}
2. Перейти в **Index Management** → **Index Patterns**
3. Создать index pattern: `logs-k3s-*` и `filebeat-k3s-*`
4. Выбрать timestamp field: `@timestamp`

### 2. Проверка поступления логов
1. Перейти в **Discover**
2. Выбрать index pattern `logs-k3s-*`
3. Проверить появление логов от подов

### 3. Создание дашбордов
Полезные визуализации:
- **Error rate by pod**: количество ошибок по подам
- **Log volume by namespace**: объем логов по namespace
- **Response time distribution**: распределение времени ответа
- **Top error messages**: частые ошибки

## 🔧 Troubleshooting

### Общие проблемы

**Elasticsearch не запускается:**
```bash
# Проверка логов
kubectl -n logging logs deployment/elasticsearch

# Проверка ресурсов
kubectl -n logging describe pod -l app=elasticsearch

# Проверка PVC
kubectl -n logging get pvc
```

**Filebeat не собирает логи:**
```bash
# Проверка DaemonSet
kubectl -n logging get ds filebeat
kubectl -n logging get pods -l app=filebeat

# Логи Filebeat
kubectl -n logging logs daemonset/filebeat --tail=100

# Проверка доступа к host логам
kubectl -n logging exec daemonset/filebeat -- ls -la /var/log/containers/
```

**Kibana не видит данные:**
```bash
# Проверка соединения с Elasticsearch
kubectl -n logging exec deployment/kibana -- curl -s http://elasticsearch:9200/_cluster/health

# Проверка индексов
kubectl -n logging exec deployment/elasticsearch -- curl -s localhost:9200/_cat/indices

# Логи Kibana
kubectl -n logging logs deployment/kibana --tail=50
```

### Performance tuning
```bash
# Увеличить Elasticsearch memory
kubectl -n logging patch deployment elasticsearch --patch '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "elasticsearch",
          "resources": {
            "limits": {"memory": "16Gi"},
            "requests": {"memory": "4Gi"}
          },
          "env": [{"name": "ES_JAVA_OPTS", "value": "-Xms8g -Xmx8g"}]
        }]
      }
    }
  }
}'

# Уменьшить retention
kubectl -n logging exec deployment/elasticsearch -- curl -X PUT 'localhost:9200/_ilm/policy/k3s-logs-policy' -H 'Content-Type: application/json' -d '{
  "policy": {
    "phases": {
      "hot": {"actions": {"rollover": {"max_size": "2GB", "max_age": "1d"}}},
      "delete": {"min_age": "7d"}
    }
  }
}'
```

## 🔗 Полезные ссылки

- **Kibana Query DSL**: [Elasticsearch Query DSL Guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html)
- **Filebeat Kubernetes**: [Filebeat Kubernetes Configuration](https://www.elastic.co/guide/en/beats/filebeat/current/running-on-kubernetes.html)
- **Logstash Patterns**: [Grok Pattern Library](https://github.com/logstash-plugins/logstash-patterns-core/tree/master/patterns)
- **Jaeger Tracing**: [Jaeger Architecture](https://www.jaegertracing.io/docs/1.50/architecture/)

## ⚡ Примеры использования

### Поиск ошибок в Kibana
```bash
# Ошибки в последние 15 минут
kubernetes.namespace:"default" AND message:"error" AND @timestamp:[now-15m TO now]

# Логи конкретного пода
kubernetes.pod.name:"my-app-*" AND @timestamp:[now-1h TO now]

# HTTP 5xx ошибки
message:"HTTP" AND (message:"500" OR message:"502" OR message:"503")
```

### Jaeger tracing примеры
```bash
# Поиск медленных запросов (в UI)
- Service: your-web-app
- Operation: HTTP GET /api/users
- Duration: > 1s

# Анализ dependency graph
- Посмотреть System Architecture в Jaeger UI
- Найти узкие места между сервисами
```

## 📋 План развития

### Ближайшие улучшения
- [ ] **Multi-node Elasticsearch** (если появятся еще worker ноды)
- [ ] **Hot/Warm tier architecture** (оптимизация storage)
- [ ] **ML anomaly detection** (обнаружение аномалий)
- [ ] **Watcher alerts** (сложные alert rules на основе логов)
- [ ] **Fleet management** (централизованное управление Beats)

### Продвинутые фичи
- [ ] **SIEM capabilities** (интеграция с Elastic Security)
- [ ] **APM integration** (Application Performance Monitoring)
- [ ] **Custom parsers** для специфичных логов
- [ ] **Log correlation** с business metrics

---

**🎯 Итог**: ELK Stack на worker ноде обеспечивает мощное централизованное логирование без нагрузки на master, с полной автоматизацией и enterprise-grade фичами.**