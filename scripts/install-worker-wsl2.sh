#!/bin/bash
# Установка K3S Worker ноды на WSL2
# Оптимизировано для Windows Subsystem for Linux 2
# Дата: 2025-11-01

set -e

# Конфигурация
READ -p "🌐 Введите IP адрес master ноды (Tailscale): " K3S_MASTER_IP
READ -p "🔑 Введите K3S токен: " K3S_TOKEN
READ -p "🏷️ Введите имя worker ноды [worker-wsl2]: " NODE_NAME

NODE_NAME=${NODE_NAME:-"worker-wsl2"}
K3S_URL="https://${K3S_MASTER_IP}:6443"

echo "🚀 Установка K3S Worker на WSL2..."
echo "⚙️ Master IP: $K3S_MASTER_IP"
echo "🏷️ Node Name: $NODE_NAME"

# Проверяем WSL2
if ! grep -q "microsoft" /proc/version; then
    echo "⚠️ Предупреждение: скрипт оптимизирован для WSL2"
    read -p "🤔 Продолжить установку? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Установка отменена"
        exit 1
    fi
fi

# Обновляем систему
echo "🔄 Обновляем систему..."
sudo apt update
sudo apt upgrade -y

# Устанавливаем необходимые пакеты
echo "📦 Устанавливаем зависимости..."
sudo apt install -y \
    curl \
    wget \
    gnupg \
    lsb-release \
    ca-certificates \
    apt-transport-https \
    software-properties-common \
    iptables \
    conntrack \
    socat

# Проверяем Tailscale
echo "🌐 Проверяем Tailscale..."
if ! command -v tailscale >/dev/null; then
    echo "📥 Устанавливаем Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
    
    echo "⚠️ Подключитесь к Tailscale:"
    echo "sudo tailscale up"
    echo "🔄 После подключения запустите скрипт снова"
    exit 1
fi

# Проверяем состояние Tailscale
if ! tailscale status --json | jq -r '.BackendState' | grep -q "Running"; then
    echo "⚠️ Tailscale не подключен. Запустите: sudo tailscale up"
    exit 1
fi

# Получаем Tailscale IP
TAILSCALE_IP=$(tailscale ip --4)
echo "✅ Tailscale IP: $TAILSCALE_IP"

# Проверяем доступность master ноды
echo "🌐 Проверяем доступность master ноды..."
if ! curl -k --connect-timeout 10 https://${K3S_MASTER_IP}:6443/version >/dev/null 2>&1; then
    echo "❌ Master нода недоступна: $K3S_MASTER_IP:6443"
    echo "🔍 Проверьте:"
    echo "   1. Master нода запущена"
    echo "   2. Tailscale сеть работает"
    echo "   3. Firewall настроен"
    exit 1
fi

echo "✅ Master нода доступна"

# Проверяем что K3S еще не установлен
if systemctl is-active k3s-agent >/dev/null 2>&1; then
    echo "⚠️ K3S agent уже запущен. Переустанавливаем..."
    sudo systemctl stop k3s-agent
    sudo /usr/local/bin/k3s-agent-uninstall.sh
fi

# Применяем WSL2 исправления ДО установки K3S
echo "🔧 Применяем WSL2 пре-исправления..."

# Настраиваем iptables
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy 2>/dev/null || true
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy 2>/dev/null || true

# Оптимизируем kernel параметры
echo 'fs.file-max = 1048576' | sudo tee -a /etc/sysctl.conf
echo 'fs.nr_open = 1048576' | sudo tee -a /etc/sysctl.conf
echo 'net.core.somaxconn = 32768' | sudo tee -a /etc/sysctl.conf
echo 'vm.max_map_count = 262144' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p 2>/dev/null || true

# Создаем директории для hostPath volumes
sudo mkdir -p /mnt/{mysql-data,grafana-data,prometheus-data}
sudo chmod 755 /mnt/{mysql-data,grafana-data,prometheus-data}

# Устанавливаем K3S agent с оптимизациями для WSL2
echo "🚀 Устанавливаем K3S agent..."

curl -sfL https://get.k3s.io | K3S_URL="$K3S_URL" \
    K3S_TOKEN="$K3S_TOKEN" \
    K3S_NODE_NAME="$NODE_NAME" \
    INSTALL_K3S_EXEC="agent --node-external-ip=$TAILSCALE_IP --flannel-iface=tailscale0" \
    sh -

# Проверяем установку
if ! systemctl is-active k3s-agent >/dev/null 2>&1; then
    echo "❌ Ошибка запуска K3S agent"
    sudo journalctl -u k3s-agent --no-pager -n 20
    exit 1
fi

echo "✅ K3S agent установлен и запущен"

# Применяем WSL2 пост-исправления
echo "🔧 Применяем WSL2 пост-исправления..."

# Подготовка к запуску wsl2-fixes.sh
if [ -f "./scripts/wsl2-fixes.sh" ]; then
    chmod +x ./scripts/wsl2-fixes.sh
    ./scripts/wsl2-fixes.sh
else
    echo "⚠️ wsl2-fixes.sh не найден, применяем базовые исправления..."
    
    # Минимальные исправления
    sudo mkdir -p /run/flannel
    echo "FLANNEL_NETWORK=10.42.0.0/16" | sudo tee /run/flannel/subnet.env
    
    # Переключаем на host-gw
    sudo sed -i 's/--flannel-backend=vxlan/--flannel-backend=host-gw/g' /etc/systemd/system/k3s-agent.service 2>/dev/null || true
    
    sudo systemctl daemon-reload
    sudo systemctl restart k3s-agent
fi

# Проверяем финальный статус
echo "🧪 Проверяем статус worker ноды..."
sleep 10

echo "📊 Статус K3S agent:"
sudo systemctl status k3s-agent --no-pager -l

echo ""
echo "✅ K3S Worker нода успешно установлена на WSL2!"
echo "📋 Конфигурация:"
echo "   - Node Name: $NODE_NAME"
echo "   - Tailscale IP: $TAILSCALE_IP"
echo "   - Master URL: $K3S_URL"
echo "   - Flannel Backend: host-gw (оптимизировано для WSL2)"
echo ""
echo "🚀 Проверьте ноду на master сервере: kubectl get nodes -o wide"
echo "📈 Смотрите логи: sudo journalctl -u k3s-agent -f"
