# 🗂️ Оптимизация логирования ELK Stack

> Comprehensive guide по оптимизации логов: сжатие, шумоподавление, бэкапы, ILM hot-warm-cold-delete

## 🎯 Что дает оптимизация

- **Экономия места**: до 60-70% меньше disk usage через compression + ILM
- **Быстрый поиск**: меньше шума → быстрее индексация и запросы
- **Автоматические бэкапы**: daily snapshots с retention
- **Performance**: оптимизированные shards/replicas для single-node

## ⚡ Быстрый старт

```bash
# Применить все оптимизации логов
python3 scripts/es_configure_optimization.py --domain cockpit.work.gd

# С бэкапами в MinIO
python3 scripts/es_configure_optimization.py --domain cockpit.work.gd --setup-snapshots

# Проверить статус
kubectl port-forward -n logging deployment/elasticsearch 9200:9200 &
curl "localhost:9200/_cat/indices?v&s=index"
curl "localhost:9200/_ilm/policy"
```

## 🏗️ Компоненты оптимизации

### 1. ILM Policies (Hot-Warm-Cold-Delete)

**Основные логи (logs-k3s-*):**
- **Hot (0-3d)**: быстрая индексация, rollover по 3GB/1d
- **Warm (3-10d)**: forcemerge до 1 сегмента + best_compression (~60% экономия)
- **Cold (10-15d)**: freeze + низкий приоритет
- **Delete (>15d)**: автоудаление

**Filebeat логи (filebeat-k3s-*):**
- Более агрессивная политика (12d total retention)
- Rollover по 2GB/1d

### 2. Index Templates

**Оптимизации:**
- `number_of_shards: 1` (для single-node ES)
- `number_of_replicas: 0` (экономия 50% места)
- Keyword fields только где нужно
- `doc_values: false` для не-агрегируемых полей
- `ignore_above: 256/4096` для длинных strings

### 3. Noise Reduction Pipeline

**Filebeat уровень (до отправки в Logstash):**
```yaml
# Drop health checks
- drop_event:
    when:
      regexp:
        kubernetes.container.name: '.*health.*|.*liveness.*|.*readiness.*'

# Drop nginx success requests  
- drop_event:
    when:
      and:
        - regexp:
            kubernetes.labels.app: 'nginx|ingress'
        - regexp:
            message: 'HTTP/[12]\.[0-9]" [23][0-9][0-9]'

# Truncate >16KB messages
- script:
    source: |
      if (msg && msg.length > 16384) {
        event.Put("message", msg.substring(0, 16384) + "... [TRUNCATED]");
      }
```

**Logstash уровень (дополнительная фильтрация):**
- Drop k8s system events ниже warn
- JSON parsing для structured logs  
- HTTP request parsing
- Log level нормализация
- Опциональная дедупликация по fingerprint

### 4. Snapshots & Backup

**MinIO Backend:**
- Встроенный S3-compatible storage на worker
- Bucket: `elk-snapshots`
- Compression: включено

**SLM Policy:**
- Schedule: daily в 03:00
- Retention: 7-30 snapshots (14 дней)
- Incremental snapshots (экономия места)

## 📊 Ожидаемые результаты

### До оптимизации:
- **Volume**: ~500MB/день на средний workload
- **Storage**: линейный рост без cleanup
- **Search speed**: медленный на больших индексах
- **Noise level**: ~70% полезных логов

### После оптимизации:
- **Volume**: ~150-200MB/день (drop 60% шума)
- **Storage**: stable через ILM + compression 
- **Search speed**: в 3-5x быстрее
- **Noise level**: ~95% полезных логов
- **Disk savings**: до 70% через compression

## 🔧 Управление и мониторинг

### Проверка ILM статуса
```bash
# Статус ILM для всех индексов
kubectl port-forward -n logging deployment/elasticsearch 9200:9200 &
curl "localhost:9200/_cat/indices?v&h=index,status,pri,rep,docs.count,store.size"

# Детали ILM policy
curl "localhost:9200/_ilm/policy/k3s-logs-policy?pretty"

# Explain ILM для конкретного индекса
curl "localhost:9200/logs-k3s-000001/_ilm/explain?pretty"
```

### Принудительные операции
```bash
# Force rollover
curl -X POST "localhost:9200/logs-k3s/_rollover?pretty"

# Manual forcemerge (только для warm/cold индексов!)
curl -X POST "localhost:9200/logs-k3s-000001/_forcemerge?max_num_segments=1&only_expunge_deletes=true"

# Trigger ILM step
curl -X POST "localhost:9200/_ilm/move/logs-k3s-000001?pretty" \
  -H 'Content-Type: application/json' -d '{ "current_step": { "phase": "warm", "action": "forcemerge", "name": "forcemerge" }, "next_step": { "phase": "warm", "action": "readonly", "name": "readonly" } }'
```

### Snapshots операции
```bash
# Список snapshots
curl "localhost:9200/_snapshot/elk-s3-repo/_all?pretty"

# Manual snapshot
curl -X PUT "localhost:9200/_snapshot/elk-s3-repo/manual-$(date +%Y%m%d)?wait_for_completion=false&pretty"

# Restore из snapshot
curl -X POST "localhost:9200/_snapshot/elk-s3-repo/daily-k3s-logs-snap-2023-11-01/_restore?pretty" \
  -H 'Content-Type: application/json' -d '{
    "indices": "logs-k3s-*",
    "ignore_unavailable": true,
    "include_global_state": false,
    "rename_pattern": "(.+)",
    "rename_replacement": "restored-$1"
  }'
```

### Мониторинг performance
```bash
# Cluster health + disk usage
curl "localhost:9200/_cluster/health?pretty"
curl "localhost:9200/_nodes/stats/fs?pretty" | jq '.nodes[].fs.total'

# Index sizes по времени  
curl "localhost:9200/_cat/indices/logs-k3s-*?v&h=index,creation.date.string,store.size&s=index"

# ILM status summary
curl "localhost:9200/_cat/indices?v&h=index,health,pri,rep,docs.count,store.size,creation.date.string" | grep -E "(logs-k3s|filebeat-k3s)"
```

## 🚨 Alerts & Thresholds

**Критические метрики:**
- `elasticsearch_filesystem_data_free_percent < 15%`
- `elasticsearch_jvm_memory_used_percent > 85%`
- `elasticsearch_cluster_health_status != "green"`
- `elasticsearch_indices_indexing_throttle_time > 0`

**Snapshot alerts:**
- `elasticsearch_snapshot_stats_snapshot_failed_total > 0`
- `elasticsearch_slm_stats_retention_runs_total == 0` (за 48h)

## 🎛️ Тюнинг под нагрузку

### Высокая нагрузка (>1GB/день)
```bash
# Increase refresh interval
curl -X PUT "localhost:9200/logs-k3s/_settings" -H 'Content-Type: application/json' -d '{
  "refresh_interval": "60s"
}'

# Bulk optimization
# В filebeat.yml: bulk_max_size: 5000, worker: 4
```

### Низкая память ES (<2GB heap)
```bash
# Reduce field data cache
curl -X PUT "localhost:9200/_cluster/settings" -H 'Content-Type: application/json' -d '{
  "persistent": {
    "indices.fielddata.cache.size": "20%",
    "indices.query.bool.max_clause_count": 2048
  }
}'
```

### Медленная сеть
```bash
# Increase bulk timeout в Logstash
# output { elasticsearch { timeout => 120 } }
```

## 📈 Expected Performance Impact

| Метрика | До оптимизации | После оптимизации | Улучшение |
|---------|---------------|-------------------|------------|
| **Disk usage** | 100% | 30-40% | 60-70% экономия |
| **Search speed** | 100% | 300-500% | 3-5x быстрее |
| **Ingest rate** | 100% | 120-150% | Быстрее на 20-50% |
| **Noise level** | 70% useful | 95% useful | Меньше мусора |
| **Operational overhead** | Manual | Automated | ILM автопилот |

## 🛠️ Maintenance Commands

### Еженедельно
```bash
# Проверка health
python3 scripts/es_configure_optimization.py --domain cockpit.work.gd

# Force cleanup старых логов
curl -X POST "localhost:9200/_ilm/move/*/_retry?pretty"
```

### Ежемесячно  
```bash
# Проверка snapshot repository
curl "localhost:9200/_snapshot/_status?pretty"

# Cleanup failed snapshots
curl -X DELETE "localhost:9200/_snapshot/elk-s3-repo/failed-snapshot-name"
```

### При проблемах
```bash
# Check ILM errors
curl "localhost:9200/_cat/indices?v&h=index,health,status" | grep yellow
curl "localhost:9200/_ilm/explain/problematic-index?pretty"

# Reset stuck ILM
curl -X POST "localhost:9200/_ilm/stop"
curl -X POST "localhost:9200/_ilm/start"
```

---

## 💡 Pro Tips

1. **Мониторь disk watermarks**: 85% (low) → 90% (high) → 95% (flood)
2. **Forcemerge только warm/cold индексы** (никогда hot!)
3. **Test restore из snapshots** раз в месяц
4. **Kibana Index Patterns**: используй `logs-k3s*` для всех логов
5. **Custom retention**: можешь менять min_age в ILM policies

**🔥 Result**: Твои логи теперь enterprise-grade с автооптимизацией!