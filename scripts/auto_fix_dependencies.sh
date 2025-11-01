#!/bin/bash
# Auto-fix script для установки всех зависимостей
# Автоматическая установка всего необходимого для K8S Enterprise deployment

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 AUTO-FIX ЗАВИСИМОСТЕЙ K8S ENTERPRISE DEPLOYMENT${NC}"
echo "==============================================================="
echo ""

# Проверка прав root/sudo
if [ "$EUID" -ne 0 ] && ! sudo -n true 2>/dev/null; then
    echo -e "${YELLOW}⚠️ Этот скрипт требует sudo права для установки пакетов${NC}"
    echo "Please run: sudo ./scripts/auto_fix_dependencies.sh"
    exit 1
fi

# Функция логирования
log_step() {
    echo -e "${BLUE}🚀 $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# 1. ОБНОВЛЕНИЕ ПАКЕТНЫХ МЕНЕДЖЕРОВ
log_step "Обновление пакетных менеджеров..."

if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    log_success "apt-get обновлен"
elif command -v yum >/dev/null 2>&1; then
    yum update -y -q
    log_success "yum обновлен"
elif command -v dnf >/dev/null 2>&1; then
    dnf update -y -q
    log_success "dnf обновлен"
else
    log_warning "Неизвестный пакетный менеджер, пропуск..."
fi

echo ""

# 2. УСТАНОВКА ОСНОВНЫХ ИНСТРУМЕНТОВ
log_step "Установка основных системных инструментов..."

BASE_PACKAGES="curl wget jq python3 python3-pip gettext-base bc unzip gnupg lsb-release ca-certificates"

if command -v apt-get >/dev/null 2>&1; then
    # Ubuntu/Debian
    PACKAGES="$BASE_PACKAGES python3-yaml python3-requests python3-dev build-essential"
    apt-get install -y -qq $PACKAGES
    log_success "Ubuntu/Debian пакеты установлены"
elif command -v yum >/dev/null 2>&1; then
    # CentOS/RHEL 7
    PACKAGES="$BASE_PACKAGES python3-devel python3-yaml python3-requests gcc gcc-c++ make"
    yum install -y -q $PACKAGES
    log_success "CentOS/RHEL пакеты установлены"
elif command -v dnf >/dev/null 2>&1; then
    # Fedora/RHEL 8+
    PACKAGES="$BASE_PACKAGES python3-devel python3-pyyaml python3-requests gcc gcc-c++ make"
    dnf install -y -q $PACKAGES
    log_success "Fedora/RHEL 8+ пакеты установлены"
else
    log_error "Неподдерживаемый пакетный менеджер"
    exit 1
fi

echo ""

# 3. PYTHON PACKAGES (с fallback на pip)
log_step "Проверка Python пакетов..."

# Проверяем requests
if ! python3 -c "import requests" >/dev/null 2>&1; then
    log_warning "requests не найден, устанавливаем через pip..."
    python3 -m pip install --user requests
fi

# Проверяем yaml
if ! python3 -c "import yaml" >/dev/null 2>&1; then
    log_warning "pyyaml не найден, устанавливаем через pip..."
    python3 -m pip install --user pyyaml
fi

# Проверяем что все работает
if python3 -c "import requests, yaml" >/dev/null 2>&1; then
    log_success "Python пакеты готовы"
else
    log_error "Python пакеты не установлены"
    exit 1
fi

echo ""

# 4. HELM INSTALLATION
log_step "Установка Helm..."

if command -v helm >/dev/null 2>&1; then
    HELM_VERSION=$(helm version --short 2>/dev/null || helm version --template='{{.Version}}' 2>/dev/null || echo "unknown")
    log_success "Helm уже установлен: $HELM_VERSION"
else
    log_step "Скачивание и установка Helm..."
    
    # Определяем архитектуру
    ARCH=$(uname -m)
    case $ARCH in
        x86_64) ARCH="amd64" ;;
        aarch64) ARCH="arm64" ;;
        armv7l) ARCH="arm" ;;
        *) log_error "Неподдерживаемая архитектура: $ARCH"; exit 1 ;;
    esac
    
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    
    # Скачиваем последнюю версию Helm
    HELM_VERSION=$(curl -s https://api.github.com/repos/helm/helm/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    HELM_URL="https://get.helm.sh/helm-${HELM_VERSION}-${OS}-${ARCH}.tar.gz"
    
    cd /tmp
    curl -fsSL "$HELM_URL" -o helm.tar.gz
    tar -zxf helm.tar.gz
    mv "${OS}-${ARCH}/helm" /usr/local/bin/helm
    chmod +x /usr/local/bin/helm
    rm -rf helm.tar.gz "${OS}-${ARCH}"
    
    # Проверяем установку
    if command -v helm >/dev/null 2>&1; then
        HELM_VERSION=$(helm version --short 2>/dev/null || helm version --template='{{.Version}}' 2>/dev/null)
        log_success "Helm установлен: $HELM_VERSION"
    else
        log_error "Helm установка не удалась"
        exit 1
    fi
fi

echo ""

# 5. KUBECTL CONFIGURATION
log_step "Настройка kubectl..."

if [ -z "${KUBECONFIG:-}" ]; then
    if [ -f "/etc/rancher/k3s/k3s.yaml" ]; then
        export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
        chmod 644 /etc/rancher/k3s/k3s.yaml
        log_success "KUBECONFIG настроен: $KUBECONFIG"
    else
        log_warning "K3S kubeconfig не найден (/etc/rancher/k3s/k3s.yaml)"
        log_warning "Проверьте что K3S установлен и работает"
    fi
else
    log_success "KUBECONFIG уже настроен: $KUBECONFIG"
fi

# Проверяем доступ к кластеру
if kubectl get nodes >/dev/null 2>&1; then
    NODE_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
    log_success "kubectl работает, найдено нод: $NODE_COUNT"
else
    log_warning "kubectl не может подключиться к кластеру"
fi

echo ""

# 6. WORKER NODE LABELING
log_step "Проверка worker нод..."

# Пытаемся найти worker ноды
WORKER_NODES=$(kubectl get nodes -l node-role.kubernetes.io/worker=worker -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)

if [ -n "$WORKER_NODES" ]; then
    log_success "Worker ноды найдены: $WORKER_NODES"
else
    log_warning "Worker ноды не найдены"
    
    # Получаем все ноды кроме master
    ALL_NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)
    MASTER_NODES=$(kubectl get nodes -l node-role.kubernetes.io/master=true -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)
    
    # Получаем ноды которые не master
    POTENTIAL_WORKERS=""
    for node in $ALL_NODES; do
        if ! echo "$MASTER_NODES" | grep -q "$node"; then
            POTENTIAL_WORKERS="$POTENTIAL_WORKERS $node"
        fi
    done
    
    if [ -n "$POTENTIAL_WORKERS" ]; then
        log_step "Найдены потенциальные worker ноды: $POTENTIAL_WORKERS"
        
        for node in $POTENTIAL_WORKERS; do
            log_step "Применяем label worker к $node..."
            if kubectl label nodes "$node" node-role.kubernetes.io/worker=worker --overwrite >/dev/null 2>&1; then
                log_success "Label worker применен к $node"
            else
                log_warning "Не удалось применить label к $node"
            fi
        done
    else
        log_warning "Нет подходящих нод для worker label"
        log_warning "Компоненты будут размещены на master нодах"
    fi
fi

echo ""

# 7. STORAGE CLASS FIX
log_step "Проверка default StorageClass..."

# Проверяем есть ли default StorageClass
DEFAULT_SC=$(kubectl get storageclass -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}' 2>/dev/null || true)

if [ -n "$DEFAULT_SC" ]; then
    log_success "Default StorageClass найден: $DEFAULT_SC"
else
    log_warning "Default StorageClass не настроен"
    
    # Пытаемся найти local-path (K3S по умолчанию)
    if kubectl get storageclass local-path >/dev/null 2>&1; then
        log_step "Настраиваем local-path как default StorageClass..."
        if kubectl patch storageclass local-path -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}' >/dev/null 2>&1; then
            log_success "local-path настроен как default"
        else
            log_warning "Не удалось настроить default StorageClass"
        fi
    else
        log_warning "StorageClass local-path не найден"
    fi
fi

echo ""

# 8. NETWORK CONNECTIVITY TESTS
log_step "Проверка сетевой связанности..."

# Проверяем ключевые ресурсы
ESSENTIAL_URLS=(
    "https://github.com"
    "https://registry-1.docker.io"
    "https://get.helm.sh"
    "https://raw.githubusercontent.com"
    "https://dl.k8s.io"
)

for url in "${ESSENTIAL_URLS[@]}"; do
    if curl -I -s --connect-timeout 5 "$url" >/dev/null 2>&1; then
        log_success "Доступ к $(echo $url | cut -d'/' -f3) работает"
    else
        log_warning "Нет доступа к $(echo $url | cut -d'/' -f3)"
    fi
done

echo ""

# 9. ФИНАЛЬНАЯ ПРОВЕРКА
log_step "Финальная проверка всех компонентов..."

# Проверяем все основные инструменты
check_tool() {
    if command -v "$1" >/dev/null 2>&1; then
        log_success "$1 доступен"
        return 0
    else
        log_error "$1 НЕ найден"
        return 1
    fi
}

SUCCESS=true

check_tool "kubectl" || SUCCESS=false
check_tool "curl" || SUCCESS=false  
check_tool "jq" || SUCCESS=false
check_tool "python3" || SUCCESS=false
check_tool "helm" || SUCCESS=false
check_tool "envsubst" || SUCCESS=false

# Python packages
if python3 -c "import requests, yaml" >/dev/null 2>&1; then
    log_success "Python packages (requests, yaml) доступны"
else
    log_error "Python packages недоступны"
    SUCCESS=false
fi

# Kubernetes access
if kubectl get nodes >/dev/null 2>&1; then
    log_success "kubectl доступ к K8S кластеру"
else
    log_error "kubectl не может подключиться к кластеру"
    SUCCESS=false
fi

echo ""
echo "==============================================================="

if [ "$SUCCESS" = true ]; then
    log_success "🎉 ВСЕ ЗАВИСИМОСТИ УСТАНОВЛЕНЫ УСПЕШНО!"
    echo ""
    echo -e "${GREEN}🚀 ГОТОВ К ЗАПУСКУ ENTERPRISE DEPLOYMENT:${NC}"
    echo ""
    echo "1. Проверьте: ./scripts/check_dependencies.sh"
    echo "2. Базовый кластер: python3 scripts/deploy_all_optimized.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true"
    echo "3. Enterprise Phase 1: python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 1"
    echo "4. Enterprise Phase 2: python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 2" 
    echo "5. Enterprise Phase 3: python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 3"
    echo ""
    exit 0
else
    log_error "😨 НЕКОТОРЫЕ ПРОБЛЕМЫ НЕ УДАЛОСЬ ИСПРАВИТЬ"
    echo ""
    echo -e "${YELLOW}📝 ПОПРОБУЙТЕ:${NC}"
    echo "1. Перезапустите этот скрипт: sudo ./scripts/auto_fix_dependencies.sh"
    echo "2. Проверьте ручно: ./scripts/check_dependencies.sh"
    echo "3. Проверьте сетевое подключение и firewall настройки"
    echo ""
    exit 1
fi