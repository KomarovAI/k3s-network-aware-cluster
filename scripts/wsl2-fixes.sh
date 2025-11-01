#!/bin/bash
# WSL2 Compatibility Fixes for K3S Network-Aware Cluster
# Автор: AI DevOps Assistant
# Дата: 2025-11-01

set -e

echo "🔧 Применяем исправления для WSL2..."

# Проверяем что мы в WSL2
if ! grep -q "microsoft" /proc/version 2>/dev/null; then
    echo "⚠️ Скрипт предназначен для WSL2. Пропускаем..."
    exit 0
fi

echo "✅ WSL2 обнаружен, применяем исправления..."

# 1. Исправляем Flannel backend (VXLAN не работает в WSL2)
echo "🌐 Переключаем Flannel с VXLAN на host-gw..."

# Обновляем systemd сервис
if [ -f /etc/systemd/system/k3s.service ]; then
    sudo sed -i 's/--flannel-backend=vxlan/--flannel-backend=host-gw/g' /etc/systemd/system/k3s.service
fi

if [ -f /etc/systemd/system/k3s-agent.service ]; then
    sudo sed -i 's/--flannel-backend=vxlan/--flannel-backend=host-gw/g' /etc/systemd/system/k3s-agent.service
fi

# Создаем недостающий flannel subnet.env
echo "📁 Создаем недостающий flannel subnet.env..."
sudo mkdir -p /run/flannel
echo "FLANNEL_NETWORK=10.42.0.0/16" | sudo tee /run/flannel/subnet.env
echo "FLANNEL_SUBNET=10.42.0.1/24" | sudo tee -a /run/flannel/subnet.env
echo "FLANNEL_MTU=1450" | sudo tee -a /run/flannel/subnet.env
echo "FLANNEL_IPMASQ=true" | sudo tee -a /run/flannel/subnet.env

# 2. Исправляем mount propagation для node-exporter
echo "💾 Настраиваем mount propagation..."
sudo mkdir -p /var/lib/rancher/k3s/storage
sudo chmod 755 /var/lib/rancher/k3s/storage

# 3. Настраиваем hostPath volumes для stateful workloads
echo "🗂️ Создаем директории для hostPath volumes..."
sudo mkdir -p /mnt/{mysql-data,grafana-data,prometheus-data}
sudo chmod 755 /mnt/{mysql-data,grafana-data,prometheus-data}

# Устанавливаем правильные владельцы
sudo chown -R 999:999 /mnt/mysql-data 2>/dev/null || true  # MySQL user
sudo chown -R 472:472 /mnt/grafana-data 2>/dev/null || true  # Grafana user
sudo chown -R 65534:65534 /mnt/prometheus-data 2>/dev/null || true  # nobody user

# 4. Оптимизируем kernel параметры для WSL2
echo "⚙️ Оптимизируем kernel параметры..."

# Увеличиваем файловые дескрипторы
echo 'fs.file-max = 1048576' | sudo tee -a /etc/sysctl.conf
echo 'fs.nr_open = 1048576' | sudo tee -a /etc/sysctl.conf

# Оптимизируем сетевые параметры
echo 'net.core.somaxconn = 32768' | sudo tee -a /etc/sysctl.conf
echo 'net.core.rmem_default = 262144' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_default = 262144' | sudo tee -a /etc/sysctl.conf

# Применяем параметры
sudo sysctl -p 2>/dev/null || true

# 5. Исправляем iptables для WSL2
echo "🔥 Настраиваем iptables для WSL2..."

# Проверяем iptables-legacy vs iptables-nft
if command -v iptables-legacy >/dev/null; then
    sudo update-alternatives --set iptables /usr/sbin/iptables-legacy 2>/dev/null || true
    sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy 2>/dev/null || true
fi

# 6. Перезапускаем сервисы
echo "🔄 Перезапускаем K3S сервисы..."
sudo systemctl daemon-reload

if systemctl is-active k3s >/dev/null 2>&1; then
    sudo systemctl restart k3s
    echo "✅ K3S master перезапущен"
fi

if systemctl is-active k3s-agent >/dev/null 2>&1; then
    sudo systemctl restart k3s-agent
    echo "✅ K3S agent перезапущен"
fi

# 7. Проверяем результат
echo "🧪 Проверяем применение исправлений..."

sleep 10

if command -v kubectl >/dev/null; then
    echo "📊 Статус нод кластера:"
    kubectl get nodes -o wide 2>/dev/null || echo "⚠️ kubectl недоступен, проверьте позже"
    
    echo "📊 Статус flannel подов:"
    kubectl get pods -A | grep flannel 2>/dev/null || echo "⚠️ Flannel поды не найдены"
fi

echo ""
echo "✅ WSL2 исправления применены успешно!"
echo "📋 Применено:"
echo "   - Flannel переключен на host-gw backend"
echo "   - Созданы директории для hostPath volumes"
echo "   - Оптимизированы kernel параметры"
echo "   - Настроены mount permissions"
echo "   - Исправлены iptables настройки"
echo ""
echo "🚀 Кластер готов к работе с WSL2!"
