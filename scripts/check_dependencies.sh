#!/bin/bash
# Comprehensive dependency checker для K8S Enterprise deployment
# Автоматическая проверка всех зависимостей перед развертыванием кластера

set -euo pipefail

# Colors для output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 ПРОВЕРКА ЗАВИСИМОСТЕЙ ДЛЯ K8S ENTERPRISE DEPLOYMENT${NC}"
echo "=================================================================="
echo ""

MISSING_TOOLS=""
MISSING_PYTHON_PACKAGES=""
CRITICAL_ISSUES=""
WARNINGS=""

# Функция проверки команды
check_command() {
    if command -v $1 >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ $1${NC} $(command -v $1)"
        return 0
    else
        echo -e "  ${RED}❌ $1 НЕ НАЙДЕН${NC}"
        MISSING_TOOLS="$MISSING_TOOLS $1"
        return 1
    fi
}

# Проверка Python package
check_python_package() {
    if python3 -c "import $1" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ $1${NC}"
        return 0
    else
        echo -e "  ${RED}❌ $1${NC}"
        MISSING_PYTHON_PACKAGES="$MISSING_PYTHON_PACKAGES $1"
        return 1
    fi
}

# 1. СИСТЕМНЫЕ ИНСТРУМЕНТЫ
echo -e "${BLUE}📦 Проверка системных инструментов:${NC}"
check_command kubectl
check_command curl
check_command jq
check_command python3
check_command envsubst
check_command helm

echo ""

# 2. PYTHON PACKAGES
echo -e "${BLUE}🐍 Проверка Python пакетов:${NC}"
check_python_package requests
check_python_package yaml

echo ""

# 3. KUBERNETES ACCESS
echo -e "${BLUE}☸️ Проверка доступа к K8S:${NC}"
if kubectl get nodes >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ kubectl доступ к кластеру${NC}"
    echo "  📋 Найденные ноды:"
    kubectl get nodes -o wide | while read line; do
        echo "    $line"
    done
    
    # Проверка worker ноды
    WORKER_NODES=$(kubectl get nodes -l node-role.kubernetes.io/worker=worker -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    if [ -n "$WORKER_NODES" ]; then
        echo -e "  ${GREEN}✅ Worker ноды найдены: $WORKER_NODES${NC}"
        
        # 🔧 НОВОЕ: Проверка сетевых компонентов на master
        echo -e "\n  ${BLUE}🌐 Проверка сетевых компонентов на master:${NC}"
        
        # Проверка ingress-nginx на master
        INGRESS_NODE=$(kubectl get pod -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx -o jsonpath='{.items[0].spec.nodeName}' 2>/dev/null)
        MASTER_NODE=$(kubectl get nodes -l node-role.kubernetes.io/control-plane=true -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        
        if [ -n "$INGRESS_NODE" ] && [ -n "$MASTER_NODE" ]; then
            if [ "$INGRESS_NODE" = "$MASTER_NODE" ]; then
                echo -e "    ${GREEN}✅ ingress-nginx размещен на master: $INGRESS_NODE${NC}"
            else
                echo -e "    ${YELLOW}⚠️ ingress-nginx на worker: $INGRESS_NODE (рекомендуется на master)${NC}"
                WARNINGS="$WARNINGS ingress-placement"
            fi
        elif kubectl get deployment -n ingress-nginx ingress-nginx-controller >/dev/null 2>&1; then
            echo -e "    ${YELLOW}⚠️ ingress-nginx найден, но не спланирован${NC}"
            WARNINGS="$WARNINGS ingress-pending"
        else
            echo -e "    ${BLUE}ℹ️ ingress-nginx не установлен (будет установлен автоматически)${NC}"
        fi
        
        # Проверка cert-manager на master
        CERTMGR_NODE=$(kubectl get pod -n cert-manager -l app=cert-manager -o jsonpath='{.items[0].spec.nodeName}' 2>/dev/null)
        
        if [ -n "$CERTMGR_NODE" ] && [ -n "$MASTER_NODE" ]; then
            if [ "$CERTMGR_NODE" = "$MASTER_NODE" ]; then
                echo -e "    ${GREEN}✅ cert-manager размещен на master: $CERTMGR_NODE${NC}"
            else
                echo -e "    ${YELLOW}⚠️ cert-manager на worker: $CERTMGR_NODE (рекомендуется на master)${NC}"
                WARNINGS="$WARNINGS cert-manager-placement"
            fi
        elif kubectl get deployment -n cert-manager cert-manager >/dev/null 2>&1; then
            echo -e "    ${YELLOW}⚠️ cert-manager найден, но не спланирован${NC}"
            WARNINGS="$WARNINGS cert-manager-pending"
        else
            echo -e "    ${BLUE}ℹ️ cert-manager не установлен (будет установлен автоматически)${NC}"
        fi
        
    else
        echo -e "  ${YELLOW}⚠️ Worker ноды не найдены (компоненты будут на master)${NC}"
        WARNINGS="$WARNINGS worker-nodes"
    fi
    
else
    echo -e "  ${RED}❌ НЕТ доступа к кластеру${NC}"
    echo -e "  ${YELLOW}💡 Попробуйте:${NC}"
    echo "    export KUBECONFIG=/etc/rancher/k3s/k3s.yaml"
    echo "    sudo chmod 644 /etc/rancher/k3s/k3s.yaml"
    CRITICAL_ISSUES="$CRITICAL_ISSUES kubectl-access"
fi

echo ""

# 4. STORAGE CLASS
echo -e "${BLUE}💾 Проверка Storage:${NC}"
if kubectl get storageclass >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ StorageClass найден:${NC}"
    kubectl get storageclass | while read line; do
        echo "    $line"
    done
    
    # Проверка default StorageClass
    DEFAULT_SC=$(kubectl get storageclass -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}')
    if [ -n "$DEFAULT_SC" ]; then
        echo -e "  ${GREEN}✅ Default StorageClass: $DEFAULT_SC${NC}"
    else
        echo -e "  ${YELLOW}⚠️ Default StorageClass не установлен${NC}"
        WARNINGS="$WARNINGS default-storage"
    fi
else
    echo -e "  ${RED}❌ StorageClass не найден${NC}"
    CRITICAL_ISSUES="$CRITICAL_ISSUES storage"
fi

echo ""

# 5. СЕТЕВОЙ ДОСТУП
echo -e "${BLUE}🌐 Проверка сетевого доступа:${NC}"

# Интернет
if ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Интернет доступен${NC}"
else
    echo -e "  ${RED}❌ Нет интернета${NC}"
    CRITICAL_ISSUES="$CRITICAL_ISSUES internet"
fi

# HTTPS доступ
if curl -I -s --connect-timeout 5 https://github.com >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ HTTPS доступ работает${NC}"
else
    echo -e "  ${RED}❌ HTTPS проблемы (proxy/firewall?)${NC}"
    CRITICAL_ISSUES="$CRITICAL_ISSUES https"
fi

# Docker Hub
if curl -I -s --connect-timeout 5 https://registry-1.docker.io >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Docker Hub доступен${NC}"
else
    echo -e "  ${YELLOW}⚠️ Docker Hub недоступен${NC}"
    WARNINGS="$WARNINGS docker-hub"
fi

# GitHub (для ArgoCD/Istio)
if curl -I -s --connect-timeout 5 https://raw.githubusercontent.com >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ GitHub raw content доступен${NC}"
else
    echo -e "  ${YELLOW}⚠️ GitHub недоступен${NC}"
    WARNINGS="$WARNINGS github"
fi

echo ""

# 6. СИСТЕМНЫЕ РЕСУРСЫ
echo -e "${BLUE}💪 Проверка ресурсов:${NC}"

# Диск
echo "  💽 Диск:"
df -h | head -n 1
DISK_INFO=$(df -h | grep -E "(/$|/var)" | head -n 2)
echo "$DISK_INFO" | while read line; do
    echo "    $line"
    # Проверка свободного места (>10GB)
    AVAIL=$(echo $line | awk '{print $4}' | sed 's/[^0-9.]//g')
    if [ ! -z "$AVAIL" ] && [ $(echo "$AVAIL < 10" | bc -l 2>/dev/null || echo 0) -eq 1 ]; then
        echo -e "    ${YELLOW}⚠️ Мало свободного места: $AVAIL${NC}"
        WARNINGS="$WARNINGS disk-space"
    fi
done

echo ""
echo "  🧠 Память:"
free -h
MEMORY_AVAIL=$(free -m | awk 'NR==2{print $7}')
if [ ! -z "$MEMORY_AVAIL" ] && [ "$MEMORY_AVAIL" -lt 1000 ]; then
    echo -e "    ${YELLOW}⚠️ Доступно <1GB памяти: ${MEMORY_AVAIL}MB${NC}"
    WARNINGS="$WARNINGS memory"
fi

echo ""

# 7. K8S КОМПОНЕНТЫ
echo -e "${BLUE}☸️ Проверка K8S компонентов:${NC}"

# Проверка cert-manager
if kubectl get crd certificates.cert-manager.io >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ cert-manager CRDs найдены${NC}"
else
    echo -e "  ${YELLOW}⚠️ cert-manager не установлен (будет установлен автоматически)${NC}"
fi

# Проверка ingress controller
if kubectl get pods -n ingress-nginx >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ ingress-nginx найден${NC}"
else
    echo -e "  ${YELLOW}⚠️ ingress-nginx не установлен (будет установлен автоматически)${NC}"
fi

# Проверка metrics-server
if kubectl top nodes >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ metrics-server работает${NC}"
else
    echo -e "  ${YELLOW}⚠️ metrics-server не отвечает (не критично для базовой установки)${NC}"
fi

echo ""

# 8. СПЕЦИФИЧНЫЕ ПРОВЕРКИ
echo -e "${BLUE}🎯 Специфичные проверки для enterprise stack:${NC}"

# GPU support на worker
if kubectl get nodes -o yaml | grep -q "nvidia.com/gpu" 2>/dev/null; then
    echo -e "  ${GREEN}✅ GPU support найден на нодах${NC}"
elif [ -n "$WORKER_NODES" ]; then
    echo -e "  ${YELLOW}⚠️ GPU support не обнаружен (может потребоваться nvidia-device-plugin)${NC}"
    WARNINGS="$WARNINGS gpu-support"
else
    echo -e "  ${BLUE}ℹ️ GPU проверка пропущена (нет worker нод)${NC}"
fi

# DNS resolution для домена
if nslookup cockpit.work.gd >/dev/null 2>&1; then
    echo -e "  ${GREEN}✅ DNS резолюция домена работает${NC}"
else
    echo -e "  ${YELLOW}⚠️ DNS проблемы с доменом (может повлиять на cert-manager)${NC}"
    WARNINGS="$WARNINGS dns-domain"
fi

echo ""

# 9. 🔧 НОВОЕ: ПРОВЕРКА РАЗМЕЩЕНИЯ КОМПОНЕНТОВ
if [ -n "$WORKER_NODES" ]; then
    echo -e "${BLUE}🎯 Проверка оптимального размещения компонентов:${NC}"
    
    # Мониторинг должен быть на worker
    PROMETHEUS_NODE=$(kubectl get pod -n monitoring -l app=prometheus -o jsonpath='{.items[0].spec.nodeName}' 2>/dev/null)
    if [ -n "$PROMETHEUS_NODE" ]; then
        if echo "$WORKER_NODES" | grep -q "$PROMETHEUS_NODE"; then
            echo -e "    ${GREEN}✅ Prometheus на worker: $PROMETHEUS_NODE${NC}"
        else
            echo -e "    ${YELLOW}⚠️ Prometheus на master: $PROMETHEUS_NODE (лучше на worker)${NC}"
            WARNINGS="$WARNINGS prometheus-placement"
        fi
    else
        echo -e "    ${BLUE}ℹ️ Prometheus еще не развернут${NC}"
    fi
    
    GRAFANA_NODE=$(kubectl get pod -n monitoring -l app=grafana -o jsonpath='{.items[0].spec.nodeName}' 2>/dev/null)
    if [ -n "$GRAFANA_NODE" ]; then
        if echo "$WORKER_NODES" | grep -q "$GRAFANA_NODE"; then
            echo -e "    ${GREEN}✅ Grafana на worker: $GRAFANA_NODE${NC}"
        else
            echo -e "    ${YELLOW}⚠️ Grafana на master: $GRAFANA_NODE (лучше на worker)${NC}"
            WARNINGS="$WARNINGS grafana-placement"
        fi
    else
        echo -e "    ${BLUE}ℹ️ Grafana еще не развернут${NC}"
    fi
fi

echo ""

# 10. ИТОГОВАЯ ОЦЕНКА
echo -e "${BLUE}🎯 ИТОГОВАЯ ОЦЕНКА ГОТОВНОСТИ:${NC}"
echo "================================================"

if [ -n "$CRITICAL_ISSUES" ]; then
    echo -e "${RED}❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ НАЙДЕНЫ:${NC}"
    for issue in $CRITICAL_ISSUES; do
        case $issue in
            "kubectl-access")
                echo -e "  🔧 ${YELLOW}kubectl доступ:${NC} export KUBECONFIG=/etc/rancher/k3s/k3s.yaml && sudo chmod 644 \$KUBECONFIG"
                ;;
            "internet")
                echo -e "  🔧 ${YELLOW}Интернет:${NC} проверьте подключение и DNS настройки"
                ;;
            "https")
                echo -e "  🔧 ${YELLOW}HTTPS:${NC} проверьте proxy settings или firewall"
                ;;
            "storage")
                echo -e "  🔧 ${YELLOW}Storage:${NC} K3S должен включать local-path provisioner автоматически"
                ;;
        esac
    done
    echo ""
fi

if [ -n "$MISSING_TOOLS" ]; then
    echo -e "${RED}❌ ОТСУТСТВУЮТ ИНСТРУМЕНТЫ:${NC}$MISSING_TOOLS"
    echo ""
    echo -e "${YELLOW}📦 КОМАНДЫ УСТАНОВКИ:${NC}"
    echo "sudo apt-get update"
    echo "sudo apt-get install -y curl jq python3 python3-yaml python3-requests gettext-base"
    echo "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
    echo ""
fi

if [ -n "$MISSING_PYTHON_PACKAGES" ]; then
    echo -e "${RED}❌ ОТСУТСТВУЮТ PYTHON ПАКЕТЫ:${NC}$MISSING_PYTHON_PACKAGES"
    echo "pip3 install requests pyyaml"
    echo "# или: sudo apt-get install -y python3-requests python3-yaml"
    echo ""
fi

if [ -n "$WARNINGS" ]; then
    echo -e "${YELLOW}⚠️ ПРЕДУПРЕЖДЕНИЯ (не критично):${NC}"
    for warning in $WARNINGS; do
        case $warning in
            "worker-nodes")
                echo "  • Worker ноды: компоненты будут размещены на master"
                ;;
            "gpu-support")
                echo "  • GPU: установите nvidia-device-plugin если нужен GPU monitoring"
                ;;
            "dns-domain")
                echo "  • DNS домена: может повлиять на автоматическое получение TLS сертификатов"
                ;;
            "memory")
                echo "  • Память: рассмотрите увеличение или настройку resource limits"
                ;;
            "disk-space")
                echo "  • Диск: освободите место или настройте retention policies"
                ;;
            "ingress-placement")
                echo -e "  • ${YELLOW}ingress-nginx на worker:${NC} лучше переместить на master (10 Gbps VPS)"
                echo "    🔧 Auto-fix: kubectl patch deployment ingress-nginx-controller -n ingress-nginx --patch '"
                echo '        {"spec":{"template":{"spec":{"nodeSelector":{"node-role.kubernetes.io/control-plane":"true"},"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}]}}}}'
                echo "    🔧 И перезапуст: kubectl rollout restart deployment/ingress-nginx-controller -n ingress-nginx"
                ;;
            "cert-manager-placement")
                echo -e "  • ${YELLOW}cert-manager на worker:${NC} лучше переместить на master (TLS endpoint)"
                echo "    🔧 Auto-fix:"
                echo "    for deploy in cert-manager cert-manager-cainjector cert-manager-webhook; do"
                echo "      kubectl patch deployment \$deploy -n cert-manager --patch '"
                echo '        {"spec":{"template":{"spec":{"nodeSelector":{"node-role.kubernetes.io/control-plane":"true"},"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}]}}}}'
                echo "    done"
                ;;
            "prometheus-placement")
                echo -e "  • ${YELLOW}Prometheus на master:${NC} лучше переместить на worker (больше рам)"
                echo "    🔧 Переразверните: python3 scripts/deploy_all_optimized.py с worker нодой"
                ;;
            "grafana-placement")
                echo -e "  • ${YELLOW}Grafana на master:${NC} лучше переместить на worker (визуальные данные)"
                echo "    🔧 Переразверните: python3 scripts/deploy_all_optimized.py с worker нодой"
                ;;
        esac
    done
    echo ""
fi

# Финальная оценка
if [ -z "$CRITICAL_ISSUES" ] && [ -z "$MISSING_TOOLS" ] && [ -z "$MISSING_PYTHON_PACKAGES" ]; then
    echo -e "${GREEN}🎉 ВСЕ ЗАВИСИМОСТИ НАЙДЕНЫ - ГОТОВ К РАЗВЕРТЫВАНИЮ!${NC}"
    echo ""
    echo -e "${GREEN}🚀 Следующие шаги:${NC}"
    echo "  1. Базовый кластер: python3 scripts/deploy_all_optimized.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true"
    echo "  2. Enterprise Phase 1: python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 1"
    echo "  3. Enterprise Phase 2: python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 2"
    echo "  4. Enterprise Phase 3: python3 scripts/deploy_enterprise_stack.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --phase 3"
    
    # 🔧 НОВОЕ: Показываем спецификацию сети
    if [ -n "$WORKER_NODES" ]; then
        echo ""
        echo -e "${BLUE}📡 СЕТЕВОЕ РАСПРЕДЕЛЕНИЕ:${NC}"
        echo "  🖥️ Master VPS: 10 Gbps (1.25 ГБ/с) - сетевые компоненты"
        echo "  🏠 Worker PC: связь с VPS ~10 МБ/с (Tailscale), интернет 100 Мбит/с"
        echo "  ✅ Оптимальное распределение: сеть на VPS, вычисления на worker"
    fi
    
    exit 0
else
    echo -e "${RED}❌ НАЙДЕНЫ ПРОБЛЕМЫ - ИСПРАВЬТЕ ПЕРЕД РАЗВЕРТЫВАНИЕМ${NC}"
    echo ""
    echo -e "${YELLOW}📝 QUICK FIX КОМАНДЫ:${NC}"
    echo "# Установка всех зависимостей одной командой:"
    echo "sudo apt-get update && sudo apt-get install -y curl jq python3 python3-yaml python3-requests gettext-base"
    echo "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
    echo "export KUBECONFIG=/etc/rancher/k3s/k3s.yaml && sudo chmod 644 /etc/rancher/k3s/k3s.yaml"
    echo ""
    echo "# После исправления запустите снова:"
    echo "./scripts/check_dependencies.sh"
    
    # 🔧 НОВОЕ: Auto-fix команды для размещения компонентов
    if echo "$WARNINGS" | grep -q "ingress-placement\|cert-manager-placement"; then
        echo ""
        echo -e "${YELLOW}🔧 AUTO-FIX ДЛЯ РАЗМЕЩЕНИЯ КОМПОНЕНТОВ:${NC}"
        
        if echo "$WARNINGS" | grep -q "ingress-placement"; then
            echo "# Перемещение ingress-nginx на master (10 Gbps VPS):"
            echo 'kubectl patch deployment ingress-nginx-controller -n ingress-nginx --patch \''
            echo '  \047{"spec":{"template":{"spec":{"nodeSelector":{"node-role.kubernetes.io/control-plane":"true"},"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}]}}}}\047'
            echo "kubectl rollout restart deployment/ingress-nginx-controller -n ingress-nginx"
            echo ""
        fi
        
        if echo "$WARNINGS" | grep -q "cert-manager-placement"; then
            echo "# Перемещение cert-manager на master (TLS endpoint):"
            echo "for deploy in cert-manager cert-manager-cainjector cert-manager-webhook; do"
            echo '  kubectl patch deployment $deploy -n cert-manager --patch \''
            echo '    \047{"spec":{"template":{"spec":{"nodeSelector":{"node-role.kubernetes.io/control-plane":"true"},"tolerations":[{"key":"node-role.kubernetes.io/control-plane","operator":"Exists","effect":"NoSchedule"}]}}}}\047'
            echo "done"
            echo ""
        fi
    fi
    
    exit 1
fi