# WSL2 Support for K3S Network-Aware Cluster

Данная документация описывает особенности развёртывания K3S кластера на Windows Subsystem for Linux 2 (WSL2).

## 🚨 Особенности WSL2

WSL2 имеет несколько ограничений, которые влияют на работу Kubernetes:

### 1️⃣ **VXLAN Limitation**
- **Проблема**: WSL2 kernel не поддерживает VXLAN (UDP 8472)
- **Симптомы**: Cross-node pod communication не работает
- **Решение**: Переключение Flannel на `host-gw` backend

### 2️⃣ **PersistentVolume Node Affinity**
- **Проблема**: local-path provisioner создаёт immutable node affinity
- **Симптомы**: Поды остаются в Pending состоянии
- **Решение**: Использование hostPath volumes для stateful workloads

### 3️⃣ **Mount Propagation Issues**  
- **Проблема**: node-exporter не может монтировать host файловую систему
- **Симптомы**: node-exporter в CreateContainerError
- **Решение**: Настройка правильных mount permissions

### 4️⃣ **iptables Compatibility**
- **Проблема**: WSL2 использует iptables-nft по умолчанию
- **Симптомы**: Проблемы с kube-proxy и service networking
- **Решение**: Переключение на iptables-legacy

## 🚀 Быстрый старт

### Предварительные требования:
- Windows 11 с WSL2
- Ubuntu 22.04/24.04 в WSL2
- Tailscale установлен и настроен
- Минимум 8GB RAM для WSL2

### 1. Установка Worker ноды на WSL2:

```bash
# Клонируем репозиторий
git clone https://github.com/KomarovAI/k3s-network-aware-cluster.git
cd k3s-network-aware-cluster

# Делаем скрипт исполняемым
chmod +x scripts/install-worker-wsl2.sh

# Запускаем установку
./scripts/install-worker-wsl2.sh
```

Скрипт автоматически:
- Обновит систему и установит зависимости
- Проверит Tailscale подключение
- Применит WSL2 исправления
- Установит K3S agent
- Настроит hostPath volumes

### 2. Применение исправлений на существующем кластере:

```bash
# Применяем исправления к существующей установке
chmod +x scripts/wsl2-fixes.sh
sudo ./scripts/wsl2-fixes.sh
```

## 🔧 Ручное применение исправлений

Если автоматические скрипты не подходят, вы можете применить исправления вручную:

### 1. Переключение Flannel на host-gw:

```bash
# На master ноде
sudo systemctl stop k3s
sudo sed -i 's/--flannel-backend=vxlan/--flannel-backend=host-gw/g' /etc/systemd/system/k3s.service
sudo systemctl daemon-reload
sudo systemctl start k3s

# На worker ноде
sudo systemctl stop k3s-agent  
sudo sed -i 's/--flannel-backend=vxlan/--flannel-backend=host-gw/g' /etc/systemd/system/k3s-agent.service
sudo systemctl daemon-reload
sudo systemctl start k3s-agent
```

### 2. Создание flannel subnet.env:

```bash
sudo mkdir -p /run/flannel
echo "FLANNEL_NETWORK=10.42.0.0/16" | sudo tee /run/flannel/subnet.env
echo "FLANNEL_SUBNET=10.42.0.1/24" | sudo tee -a /run/flannel/subnet.env
echo "FLANNEL_MTU=1450" | sudo tee -a /run/flannel/subnet.env
```

### 3. Настройка hostPath volumes:

```bash
# Создаём директории
sudo mkdir -p /mnt/{mysql-data,grafana-data,prometheus-data}
sudo chmod 755 /mnt/{mysql-data,grafana-data,prometheus-data}

# Устанавливаем владельцев
sudo chown -R 999:999 /mnt/mysql-data      # MySQL
sudo chown -R 472:472 /mnt/grafana-data    # Grafana
sudo chown -R 65534:65534 /mnt/prometheus-data  # Prometheus
```

### 4. Исправление iptables:

```bash
# Переключаем на legacy iptables
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy

# Перезапускаем K3S
sudo systemctl restart k3s-agent  # или k3s на master
```

## 📁 Пример конфигурации для Stateful Workloads

### MySQL с hostPath volume:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  template:
    spec:
      nodeSelector:
        kubernetes.io/hostname: worker-wsl2
      containers:
      - name: mysql
        image: mysql:8.0
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
      volumes:
      - name: data
        hostPath:
          path: /mnt/mysql-data
          type: DirectoryOrCreate
```

### Grafana с hostPath volume:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
spec:
  template:
    spec:
      nodeSelector:
        kubernetes.io/hostname: worker-wsl2
      containers:
      - name: grafana
        image: grafana/grafana:latest
        volumeMounts:
        - name: storage
          mountPath: /var/lib/grafana
      volumes:
      - name: storage
        hostPath:
          path: /mnt/grafana-data
          type: DirectoryOrCreate
```

## 🧪 Тестирование и диагностика

### Проверка статуса кластера:

```bash
# Проверяем ноды
kubectl get nodes -o wide

# Проверяем поды
kubectl get pods -A

# Проверяем flannel
kubectl get pods -A | grep flannel
```

### Тест DNS и сетевой связности:

```bash
# Тест DNS между нодами
kubectl run dns-test --rm -i --tty --image=busybox \
  --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"worker-wsl2"}}}' \
  -- nslookup kubernetes.default.svc.cluster.local

# Тест связности между подами
kubectl run net-test --rm -i --tty --image=busybox \
  --overrides='{"spec":{"nodeSelector":{"kubernetes.io/hostname":"worker-wsl2"}}}' \
  -- ping -c 3 google.com
```

### Логи и отладка:

```bash
# Логи K3S agent
sudo journalctl -u k3s-agent -f

# Логи kubelet
sudo journalctl -u k3s-agent --grep kubelet -f

# Проверка flannel конфигурации
cat /run/flannel/subnet.env
```

## 📊 Производительность и ресурсы

### Рекомендуемые настройки WSL2:

Создайте файл `.wslconfig` в `%USERPROFILE%`:

```ini
[wsl2]
memory=32GB          # Увеличить для database workloads
processors=8         # Использовать больше ядер
localhostForwarding=true
swap=0               # Отключить swap для производительности
nestedVirtualization=false
```

### Оптимизация kernel параметров:

```bash
# Добавьте в /etc/sysctl.conf
fs.file-max = 1048576
fs.nr_open = 1048576  
net.core.somaxconn = 32768
vm.max_map_count = 262144
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1

# Применить
sudo sysctl -p
```

## ⚠️ Известные ограничения

1. **LoadBalancer Services**: Не поддерживаются, используйте NodePort или Ingress
2. **Device Plugins**: GPU поддержка ограничена 
3. **Privileged Containers**: Могут вызывать проблемы безопасности
4. **SystemD Services**: Не все systemd unit files работают корректно

## 🔗 Полезные ссылки

- [WSL2 официальная документация](https://docs.microsoft.com/en-us/windows/wsl/)
- [K3S официальная документация](https://docs.k3s.io/)
- [Flannel CNI документация](https://github.com/flannel-io/flannel)
- [Tailscale документация](https://tailscale.com/kb/)

## 🌟 Поддержка

Если у вас возникли вопросы или проблемы с WSL2 поддержкой:

1. Проверьте [Issues](../../issues) на наличие похожих проблем
2. Создайте новое [Issue](../../issues/new) с меткой `wsl2`
3. Приложите логи: `sudo journalctl -u k3s-agent --no-pager -n 50`
4. Укажите версии Windows, WSL2 и Ubuntu
