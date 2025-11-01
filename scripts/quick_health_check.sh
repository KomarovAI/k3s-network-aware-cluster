#!/bin/bash

# Quick health check для K3S кластера
# Использование: ./scripts/quick_health_check.sh

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    local status=$1
    local message=$2
    if [[ $status == "OK" ]]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [[ $status == "WARNING" ]]; then
        echo -e "${YELLOW}⚠️  $message${NC}"
    else
        echo -e "${RED}❌ $message${NC}"
    fi
}

print_header() {
    echo -e "${BLUE}\n🔍 $1${NC}"
    echo "═══════════════════════════════════════"
}

check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        print_status "ERROR" "kubectl не найден"
        exit 1
    fi
    print_status "OK" "kubectl доступен"
}

check_cluster_connection() {
    if kubectl cluster-info &> /dev/null; then
        print_status "OK" "Подключение к кластеру установлено"
    else
        print_status "ERROR" "Не удается подключиться к кластеру"
        exit 1
    fi
}

check_nodes() {
    local ready_nodes
    ready_nodes=$(kubectl get nodes --no-headers | grep -c " Ready ")
    local total_nodes
    total_nodes=$(kubectl get nodes --no-headers | wc -l)
    
    if [[ $ready_nodes -eq $total_nodes ]] && [[ $ready_nodes -ge 1 ]]; then
        print_status "OK" "Ноды готовы: $ready_nodes/$total_nodes"
    else
        print_status "ERROR" "Проблема с нодами: готово $ready_nodes из $total_nodes"
    fi
    
    # Детали по нодам
    kubectl get nodes -o wide
}

check_system_pods() {
    local not_running
    not_running=$(kubectl get pods -n kube-system --no-headers | grep -v " Running " | grep -v " Completed " | wc -l)
    
    if [[ $not_running -eq 0 ]]; then
        print_status "OK" "Все системные поды работают"
    else
        print_status "WARNING" "$not_running системных подов не в состоянии Running"
        kubectl get pods -n kube-system | grep -v " Running " | grep -v " Completed "
    fi
}

check_ingress() {
    if kubectl get deployment ingress-nginx-controller -n ingress-nginx &> /dev/null; then
        local ready_replicas
        ready_replicas=$(kubectl get deployment ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.readyReplicas}')
        if [[ $ready_replicas -ge 1 ]]; then
            print_status "OK" "Ingress Controller работает ($ready_replicas replicas)"
        else
            print_status "ERROR" "Ingress Controller не готов"
        fi
    else
        print_status "WARNING" "Ingress Controller не найден"
    fi
}

check_cert_manager() {
    if kubectl get deployment cert-manager -n cert-manager &> /dev/null; then
        local ready_replicas
        ready_replicas=$(kubectl get deployment cert-manager -n cert-manager -o jsonpath='{.status.readyReplicas}')
        if [[ $ready_replicas -ge 1 ]]; then
            print_status "OK" "cert-manager работает ($ready_replicas replicas)"
        else
            print_status "ERROR" "cert-manager не готов"
        fi
    else
        print_status "WARNING" "cert-manager не найден"
    fi
}

check_monitoring() {
    # Проверка Grafana
    if kubectl get deployment grafana -n monitoring &> /dev/null; then
        local ready_replicas
        ready_replicas=$(kubectl get deployment grafana -n monitoring -o jsonpath='{.status.readyReplicas}')
        if [[ $ready_replicas -ge 1 ]]; then
            print_status "OK" "Grafana работает ($ready_replicas replicas)"
        else
            print_status "WARNING" "Grafana не готов"
        fi
    else
        print_status "WARNING" "Grafana не найден"
    fi
    
    # Проверка Prometheus
    if kubectl get deployment prometheus -n monitoring &> /dev/null; then
        print_status "OK" "Prometheus найден"
    else
        print_status "WARNING" "Prometheus не найден"
    fi
}

check_kubevious() {
    if kubectl get deployment kubevious -n kubevious &> /dev/null; then
        local ready_replicas
        ready_replicas=$(kubectl get deployment kubevious -n kubevious -o jsonpath='{.status.readyReplicas}')
        if [[ $ready_replicas -ge 1 ]]; then
            print_status "OK" "Kubevious работает ($ready_replicas replicas)"
        else
            print_status "WARNING" "Kubevious не готов"
        fi
    else
        print_status "WARNING" "Kubevious не найден"
    fi
}

check_certificates() {
    local total_certs
    total_certs=$(kubectl get certificates --all-namespaces --no-headers 2>/dev/null | wc -l)
    
    if [[ $total_certs -gt 0 ]]; then
        local ready_certs
        ready_certs=$(kubectl get certificates --all-namespaces --no-headers 2>/dev/null | grep -c " True ")
        if [[ $ready_certs -eq $total_certs ]]; then
            print_status "OK" "TLS сертификаты готовы: $ready_certs/$total_certs"
        else
            print_status "WARNING" "TLS сертификаты: готово $ready_certs из $total_certs"
        fi
    else
        print_status "WARNING" "TLS сертификаты не найдены"
    fi
}

check_resources() {
    echo -e "\n${BLUE}📊 Использование ресурсов:${NC}"
    if command -v kubectl top &> /dev/null; then
        kubectl top nodes 2>/dev/null || echo "Метрики недоступны (требуется metrics-server)"
    else
        echo "kubectl top недоступен"
    fi
}

show_endpoints() {
    echo -e "\n${BLUE}🌐 Доступные endpoints:${NC}"
    
    # Получаем Ingress'ы
    kubectl get ingress --all-namespaces -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,HOSTS:.spec.rules[*].host,TLS:.spec.tls[*].secretName --no-headers 2>/dev/null | while read -r namespace name hosts tls; do
        if [[ -n "$hosts" ]] && [[ "$hosts" != "<none>" ]]; then
            if [[ -n "$tls" ]] && [[ "$tls" != "<none>" ]]; then
                echo "  🔒 https://$hosts ($namespace/$name)"
            else
                echo "  🌐 http://$hosts ($namespace/$name)"
            fi
        fi
    done
}

print_summary() {
    echo -e "\n${BLUE}📋 Сводка:${NC}"
    echo "═══════════════════════════════════════"
    echo -e "${GREEN}✅${NC} Готово к работе"
    echo -e "${YELLOW}⚠️${NC}  Требует внимания"
    echo -e "${RED}❌${NC} Критическая проблема"
    
    echo -e "\n${BLUE}🔧 Для детальной диагностики:${NC}"
    echo "  python3 scripts/cluster_optimizer.py --check"
    echo "  python3 scripts/cluster_optimizer.py --report"
}

# Главная функция
main() {
    echo -e "${BLUE}🚀 Быстрая проверка здоровья K3S кластера${NC}"
    echo -e "${BLUE}$(date)${NC}"
    echo "═══════════════════════════════════════════════════════════"
    
    print_header "Базовые проверки"
    check_kubectl
    check_cluster_connection
    
    print_header "Состояние нод"
    check_nodes
    
    print_header "Системные компоненты"
    check_system_pods
    
    print_header "Ingress и TLS"
    check_ingress
    check_cert_manager
    check_certificates
    
    print_header "Мониторинг"
    check_monitoring
    check_kubevious
    
    check_resources
    show_endpoints
    print_summary
    
    echo -e "\n${GREEN}🎉 Проверка завершена!${NC}"
}

# Запуск
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
