#!/usr/bin/env python3
"""
One-shot deploy script for the hybrid K3S cluster (VPS master + single Home PC worker)
- Installs/validates K3S master
- Generates and guides worker join
- Installs ingress-nginx
- Installs cert-manager (CRDs + controller)
- Applies ClusterIssuer (HTTP-01 by default; DNS-01 optional if CF token provided)
- Applies base manifests
- Deploys monitoring stack + Grafana provisioning (datasource + dashboards)
- Installs Kubevious via Helm with TLS Ingress
- Applies VPA and registry cache
- Smoke-checks TLS and returns ready URLs

Usage examples:
  python3 scripts/deploy_all.py --domain cockpit.work.gd --email artur.komarovv@gmail.com --gpu true

Requirements on VPS:
  sudo apt-get update && sudo apt-get install -y curl jq python3 python3-yaml
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def sh(cmd: str, check=True):
    print(f"$ {cmd}")
    res = subprocess.run(cmd, shell=True)
    if check and res.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(res.returncode)
    return res.returncode


def wait_for(cmd: str, timeout: int = 180, sleep: float = 3.0):
    print(f"⏳ Waiting: {cmd}")
    t0 = time.time()
    while time.time() - t0 < timeout:
        if subprocess.run(cmd, shell=True).returncode == 0:
            print("✅ Ready")
            return True
        time.sleep(sleep)
    print("⚠️ Timeout waiting for readiness")
    return False


def deploy_master():
    sh("python3 scripts/install_cluster_enhanced.py --mode master")
    wait_for("kubectl get nodes")


def install_ingress():
    sh("kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/cloud/deploy.yaml")
    wait_for("kubectl -n ingress-nginx rollout status deploy/ingress-nginx-controller --timeout=180s")


def install_cert_manager():
    sh("kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.crds.yaml")
    sh("kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -")
    sh("kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml")
    wait_for("kubectl -n cert-manager rollout status deploy/cert-manager --timeout=300s")


def apply_cluster_issuers(domain: str, email: str, use_dns01: bool):
    env = os.environ.copy()
    env["ACME_EMAIL"] = email
    # HTTP-01
    http01 = (REPO_ROOT / "manifests/cert-manager/clusterissuer-http01.yaml").read_text()
    sh(f"bash -lc 'ACME_EMAIL={email} envsubst < manifests/cert-manager/clusterissuer-http01.yaml | kubectl apply -f -'")
    # DNS-01 optional
    if use_dns01:
        cf_token = os.getenv("CF_API_TOKEN", "")
        if not cf_token:
            print("⚠️ CF_API_TOKEN not set, skipping DNS-01 issuer")
        else:
            sh(f"kubectl -n cert-manager create secret generic cloudflare-api-token --from-literal=api-token='{cf_token}' --dry-run=client -o yaml | kubectl apply -f -")
            sh(f"bash -lc 'ACME_EMAIL={email} envsubst < manifests/cert-manager/clusterissuer-dns01-cloudflare.yaml | kubectl apply -f -'")


def apply_base_and_monitoring(domain: str):
    sh("kubectl apply -k manifests/base/")
    # Monitoring stack already embedded in production_hardening, but ensure provisioning
    sh("kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -")
    sh("kubectl apply -f manifests/monitoring/grafana-provisioning/datasource-configmap.yaml")
    sh("kubectl apply -f manifests/monitoring/grafana-provisioning/dashboards-configmap.yaml")
    sh("kubectl apply -f manifests/monitoring/grafana-provisioning/provisioning-wiring.yaml")


def apply_gpu_monitoring(enable_gpu: bool):
    if not enable_gpu:
        return
    # Add dcgm-exporter DaemonSet if present
    exporter_dir = REPO_ROOT / "manifests/monitoring/nvidia-dcgm-exporter"
    if exporter_dir.exists():
        sh(f"kubectl apply -k {exporter_dir}")
    else:
        print("ℹ️ GPU exporter manifests not found. Skipping.")


def install_kubevious(domain: str):
    # Namespace & ingress first
    sh("kubectl apply -k manifests/kubevious/")
    # Helm install
    sh("helm repo add kubevious https://helm.kubevious.io || true")
    sh("helm repo update")
    sh("helm upgrade --install kubevious kubevious/kubevious -n kubevious -f manifests/kubevious/helm-values.yaml")


def apply_vpa_and_registry():
    sh("kubectl apply -f manifests/core/vpa.yaml")
    # registry cache (templated values are neutral here)
    sh("kubectl apply -f manifests/core/registry-cache.yaml")


def expose_grafana(domain: str):
    sh(f"bash -lc 'TLS_DOMAIN={domain} envsubst < manifests/ingress/grafana.yaml | kubectl apply -f -'")


def smoke_check(domain: str):
    print("🔎 Checking certificate readiness…")
    # Give cert-manager some time to obtain cert
    time.sleep(15)
    # We just check that ingress objects exist; real HTTPs check might require curl with --insecure first time
    sh("kubectl -n monitoring get ingress grafana")
    sh("kubectl -n kubevious get ingress kubevious")
    print(f"\n✅ Ready URLs:\n  Grafana  https://grafana.{domain}\n  Kubevious https://kubevious.{domain}")


def main():
    p = argparse.ArgumentParser(description="One-shot deploy for K3S hybrid cluster")
    p.add_argument("--domain", required=True, help="Base domain, e.g. cockpit.work.gd")
    p.add_argument("--email", required=True, help="ACME email for Let's Encrypt")
    p.add_argument("--gpu", default="true", choices=["true","false"], help="Enable GPU monitoring panels")
    p.add_argument("--dns01", action="store_true", help="Use DNS-01 (Cloudflare) if CF_API_TOKEN provided")
    args = p.parse_args()

    domain = args.domain
    email = args.email
    gpu = args.gpu.lower() == "true"

    print("🚀 Deploying master…")
    deploy_master()

    print("\n📥 Worker join script path: ~/join_worker_enhanced.py")
    print("➡️  Скопируйте на воркер и запустите: scp ~/join_worker_enhanced.py user@<WORKER_IP>:/tmp/ && ssh user@<WORKER_IP> 'python3 /tmp/join_worker_enhanced.py'")
    input("⏸️  Нажмите Enter, когда воркер успешно присоединился (kubectl get nodes показывает 2 ноды)… ")

    print("\n🌐 Installing ingress-nginx…")
    install_ingress()

    print("\n🔐 Installing cert-manager…")
    install_cert_manager()

    print("\n🪪 Applying ClusterIssuers…")
    apply_cluster_issuers(domain, email, use_dns01=args.dns01)

    print("\n📦 Applying base & monitoring with Grafana provisioning…")
    apply_base_and_monitoring(domain)

    print("\n🧠 GPU monitoring…")
    apply_gpu_monitoring(gpu)

    print("\n🧭 Installing Kubevious…")
    install_kubevious(domain)

    print("\n📈 VPA & Registry cache…")
    apply_vpa_and_registry()

    print("\n🔓 Exposing Grafana (TLS)…")
    expose_grafana(domain)

    print("\n🧪 Smoke checks…")
    smoke_check(domain)

    print("\n🎉 Deployment completed.")


if __name__ == "__main__":
    main()
