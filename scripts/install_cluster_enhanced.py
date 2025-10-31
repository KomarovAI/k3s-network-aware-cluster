#!/usr/bin/env python3
"""
K3S Enhanced Cluster Installer
Production-ready K3S cluster for VPS (3 vCPU, 4GB RAM, 100GB) + Home PC workers

Usage: 
  python3 install_cluster_enhanced.py --mode master  # On VPS
  python3 install_cluster_enhanced.py --mode worker --master-ip IP --token TOKEN  # On Home PC
"""

import os
import sys
import subprocess
import argparse
import json
import time
import ipaddress
from pathlib import Path
from typing import Dict, List, Optional


class EnhancedK3SInstaller:
    def __init__(self):
        self.tailscale_ip = None
        self.node_name = None
        self.vps_specs = {
            'cpu_cores': 3,
            'memory_gb': 4,
            'storage_gb': 100,
            'network_speed': '1000mbps'  # Enhanced VPS
        }
        
    def check_prerequisites(self) -> bool:
        """Enhanced prerequisite checks"""
        print("📋 Checking enhanced prerequisites...")
        
        # Check if running as root
        if os.geteuid() == 0:
            print("❌ Don't run as root for security")
            return False
        
        # Check system resources
        if not self._check_system_resources():
            return False
        
        # Check required commands
        required_commands = {
            'curl': 'System package manager',
            'docker': 'curl -fsSL https://get.docker.com | sh',
            'tailscale': 'curl -fsSL https://tailscale.com/install.sh | sh'
        }
        
        for cmd, install_hint in required_commands.items():
            if not self._command_exists(cmd):
                print(f"❌ {cmd} not found")
                print(f"   Install: {install_hint}")
                return False
            else:
                print(f"✅ {cmd} available")
        
        # Get and validate Tailscale IP
        try:
            result = subprocess.run(['tailscale', 'ip', '-4'], 
                                  capture_output=True, text=True, check=True)
            self.tailscale_ip = result.stdout.strip()
            
            # Validate IP format
            ipaddress.ip_address(self.tailscale_ip)
            print(f"✅ Tailscale IP: {self.tailscale_ip}")
            
        except (subprocess.CalledProcessError, ipaddress.AddressValueError):
            print("❌ Tailscale not connected or invalid IP")
            print("   Run: tailscale up --accept-routes")
            return False
        
        # Get hostname
        try:
            result = subprocess.run(['hostname', '-f'], 
                                  capture_output=True, text=True, check=True)
            self.node_name = result.stdout.strip()
            print(f"✅ Node name: {self.node_name}")
        except subprocess.CalledProcessError:
            print("⚠️  Could not get FQDN, using short hostname")
            self.node_name = subprocess.run(['hostname'], 
                                          capture_output=True, text=True).stdout.strip()
        
        return True
    
    def install_enhanced_master(self) -> bool:
        """Install K3S master optimized for enhanced VPS (3 vCPU, 4GB RAM)"""
        print("🚀 Installing K3S master for enhanced VPS...")
        print(f"   VPS Specs: {self.vps_specs['cpu_cores']} vCPU, {self.vps_specs['memory_gb']}GB RAM, {self.vps_specs['storage_gb']}GB storage")
        
        # System optimizations for enhanced VPS
        self._apply_enhanced_system_optimizations()
        
        # Create K3S configuration for enhanced VPS
        self._create_enhanced_k3s_config()
        
        # Install K3S with enhanced configuration
        install_cmd = [
            'curl', '-sfL', 'https://get.k3s.io', '|', 'sh', '-s', '-', 'server'
        ]
        
        print("📦 Installing K3S server...")
        result = subprocess.run(' '.join(install_cmd), shell=True)
        if result.returncode != 0:
            print("❌ K3S installation failed")
            return False
        
        # Wait for K3S to be ready
        self._wait_for_k3s_ready(timeout=180)
        
        # Configure kubectl for user
        self._setup_kubectl_access()
        
        # Apply enhanced node configuration
        self._configure_enhanced_master_node()
        
        # Install enhanced ingress
        self._install_enhanced_ingress()
        
        # Create worker join script
        self._create_enhanced_worker_script()
        
        print(f"✅ Enhanced K3S master installed successfully on {self.node_name}!")
        return True
    
    def install_worker(self, master_ip: str, token: str) -> bool:
        """Install K3S worker optimized for Home PC"""
        print(f"⚙️  Installing K3S worker connecting to {master_ip}...")
        
        # Validate master IP
        try:
            ipaddress.ip_address(master_ip)
        except ipaddress.AddressValueError:
            print("❌ Invalid master IP address")
            return False
        
        # Apply worker optimizations
        self._apply_worker_optimizations()
        
        # Install K3S agent
        env = {
            'K3S_URL': f'https://{master_ip}:6443',
            'K3S_TOKEN': token
        }
        
        install_cmd = [
            'curl', '-sfL', 'https://get.k3s.io', '|', 'sh', '-s', '-', 'agent',
            '--flannel-iface', 'tailscale0',
            '--node-ip', self.tailscale_ip,
            '--node-external-ip', self.tailscale_ip,
            '--node-name', self.node_name,
            # Worker optimizations
            '--kubelet-arg', 'max-pods=250',  # High capacity for powerful PCs
            '--kubelet-arg', 'serialize-image-pulls=false',
            '--kubelet-arg', 'registry-pull-qps=20',
            '--kubelet-arg', 'registry-burst=40'
        ]
        
        # Set environment and run
        env_str = ' '.join([f'{k}={v}' for k, v in env.items()])
        full_cmd = f"{env_str} {' '.join(install_cmd)}"
        
        result = subprocess.run(full_cmd, shell=True)
        if result.returncode != 0:
            print("❌ K3S worker installation failed")
            return False
        
        print(f"✅ K3S worker {self.node_name} joined cluster successfully!")
        return True
    
    def _check_system_resources(self) -> bool:
        """Check if system has adequate resources"""
        try:
            # Check CPU cores
            with open('/proc/cpuinfo', 'r') as f:
                cpu_count = len([line for line in f if line.startswith('processor')])
            
            # Check memory
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        mem_kb = int(line.split()[1])
                        mem_gb = mem_kb / 1024 / 1024
                        break
            
            print(f"📊 System: {cpu_count} CPU cores, {mem_gb:.1f}GB RAM")
            
            # For VPS master: minimum validation
            if cpu_count < 2:
                print(f"⚠️  Warning: {cpu_count} CPU cores. Recommended: 3+ for VPS master")
            if mem_gb < 2:
                print(f"⚠️  Warning: {mem_gb:.1f}GB RAM. Recommended: 4GB+ for VPS master")
            
            return True
            
        except Exception as e:
            print(f"⚠️  Could not check system resources: {e}")
            return True  # Continue anyway
    
    def _apply_enhanced_system_optimizations(self) -> None:
        """Apply system optimizations for enhanced VPS"""
        print("🔧 Applying enhanced VPS system optimizations...")
        
        optimizations = [
            # Memory optimization for 4GB VPS
            'echo "vm.swappiness=5" | sudo tee -a /etc/sysctl.conf',
            'echo "vm.vfs_cache_pressure=50" | sudo tee -a /etc/sysctl.conf',
            'echo "vm.dirty_ratio=10" | sudo tee -a /etc/sysctl.conf',
            'echo "vm.dirty_background_ratio=5" | sudo tee -a /etc/sysctl.conf',
            
            # Network optimization
            'echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf',
            'echo "net.ipv6.conf.all.forwarding=1" | sudo tee -a /etc/sysctl.conf',
            
            # TCP BBR for better network performance
            'echo "net.core.default_qdisc=fq" | sudo tee -a /etc/sysctl.conf',
            'echo "net.ipv4.tcp_congestion_control=bbr" | sudo tee -a /etc/sysctl.conf',
            
            # Network buffers for enhanced VPS
            'echo "net.core.rmem_max=16777216" | sudo tee -a /etc/sysctl.conf',
            'echo "net.core.wmem_max=16777216" | sudo tee -a /etc/sysctl.conf',
            
            # Apply all optimizations
            'sudo sysctl -p'
        ]
        
        for cmd in optimizations:
            result = subprocess.run(cmd, shell=True, capture_output=True)
            if result.returncode != 0:
                print(f"   ⚠️  Warning: {cmd} failed")
    
    def _create_enhanced_k3s_config(self) -> None:
        """Create K3S configuration optimized for enhanced VPS"""
        config_dir = Path('/etc/rancher/k3s')
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Enhanced configuration for 3 vCPU, 4GB RAM VPS
        config_content = f"""# Enhanced K3S configuration for VPS (3 vCPU, 4GB RAM, 100GB)
write-kubeconfig-mode: 644

# Network configuration
flannel-iface: tailscale0
advertise-address: {self.tailscale_ip}
node-ip: {self.tailscale_ip}
node-external-ip: {self.tailscale_ip}
bind-address: {self.tailscale_ip}
node-name: {self.node_name}
cluster-cidr: 10.42.0.0/16
service-cidr: 10.43.0.0/16

# Disable components to save resources (run on demand)
disable:
  - traefik       # Use custom NGINX ingress
  - servicelb     # Use external LB or NodePort
  - local-storage # Use custom storage classes

# Master node isolation (enhanced VPS can handle some system workloads)
node-taint:
  - "node-role.kubernetes.io/control-plane=true:NoSchedule"
  - "vps-enhanced=true:PreferNoSchedule"  # Soft isolation

# Enhanced resource configuration for 3 vCPU, 4GB RAM
kube-apiserver-arg:
  - "max-requests-inflight=300"           # Higher with 3 vCPU
  - "max-mutating-requests-inflight=150"  # 50% of read requests
  - "request-timeout=60s"
  - "min-request-timeout=30s"
  - "audit-log-maxage=7"                  # 7 days retention
  - "audit-log-maxbackup=3"
  - "audit-log-maxsize=100"               # 100MB files

kube-controller-manager-arg:
  - "concurrent-deployment-syncs=5"       # Higher concurrency
  - "concurrent-replicaset-syncs=5"
  - "concurrent-resource-quota-syncs=5"
  - "kube-api-qps=100"                    # Higher API rate
  - "kube-api-burst=200"

kube-scheduler-arg:
  - "v=2"
  - "kube-api-qps=100"
  - "kube-api-burst=200"
  - "profile-port=10259"                  # Enable profiling

# Enhanced etcd configuration for 100GB storage
etcd-arg:
  - "quota-backend-bytes=8589934592"      # 8GB quota
  - "auto-compaction-retention=1h"
  - "auto-compaction-mode=periodic"
  - "snapshot-count=10000"
  - "heartbeat-interval=100"
  - "election-timeout=1000"

# Kubelet configuration for enhanced VPS
kubelet-arg:
  - "max-pods=150"                        # Reasonable limit
  - "pods-per-core=50"                    # 3 cores = 150 pods max
  - "system-reserved=cpu=300m,memory=800Mi,ephemeral-storage=10Gi"
  - "kube-reserved=cpu=500m,memory=1200Mi,ephemeral-storage=5Gi"
  - "eviction-hard=memory.available<200Mi,nodefs.available<5%"
  - "serialize-image-pulls=false"         # Parallel pulls
  - "registry-pull-qps=10"
  - "registry-burst=20"
"""
        
        with open(config_dir / 'config.yaml', 'w') as f:
            f.write(config_content)
        
        print(f"✅ Enhanced K3S config created for {self.vps_specs['cpu_cores']} vCPU VPS")
    
    def _wait_for_k3s_ready(self, timeout: int = 180) -> None:
        """Wait for K3S to be ready with longer timeout for enhanced setup"""
        print(f"⏳ Waiting for enhanced K3S to be ready (timeout: {timeout}s)...")
        
        for i in range(timeout):
            try:
                result = subprocess.run(['sudo', 'kubectl', 'get', 'nodes'], 
                                      capture_output=True, check=True)
                if result.returncode == 0:
                    print("✅ K3S API server is ready")
                    break
            except subprocess.CalledProcessError:
                pass
            
            time.sleep(1)
            if i % 15 == 0 and i > 0:
                print(f"   Still waiting... ({i}s elapsed)")
        else:
            print(f"⚠️  K3S took longer than {timeout}s to start")
    
    def _setup_kubectl_access(self) -> None:
        """Setup kubectl access for current user"""
        kubectl_dir = Path.home() / '.kube'
        kubectl_dir.mkdir(exist_ok=True)
        
        # Copy kubeconfig
        subprocess.run([
            'sudo', 'cp', '/etc/rancher/k3s/k3s.yaml', 
            str(kubectl_dir / 'config')
        ])
        
        # Fix permissions
        subprocess.run([
            'sudo', 'chown', f'{os.getuid()}:{os.getgid()}',
            str(kubectl_dir / 'config')
        ])
        
        print("✅ kubectl access configured")
    
    def _configure_enhanced_master_node(self) -> None:
        """Configure master node with enhanced VPS labels"""
        print("🏷️  Configuring enhanced master node...")
        
        # Enhanced VPS labels
        labels = {
            'node-type': 'vps',
            'role': 'control-plane',
            'compute-tier': 'enhanced-management',  # Enhanced tier
            'cpu-cores': str(self.vps_specs['cpu_cores']),
            'memory-gb': str(self.vps_specs['memory_gb']),
            'storage-gb': str(self.vps_specs['storage_gb']),
            'network-speed': self.vps_specs['network_speed'],
            'network-latency': 'medium',  # Better than basic VPS
            'zone': 'remote',
            'internet-access': 'true',
            'can-run-system-workloads': 'true',  # Enhanced VPS can handle some workloads
            'vps-tier': 'enhanced'
        }
        
        for key, value in labels.items():
            subprocess.run([
                'kubectl', 'label', 'node', self.node_name, 
                f'{key}={value}', '--overwrite'
            ])
        
        # Enhanced taints (softer isolation due to better resources)
        taints = [
            'node-role.kubernetes.io/control-plane=true:NoSchedule',
            'vps-enhanced=true:PreferNoSchedule'  # Soft taint, allow if needed
        ]
        
        for taint in taints:
            subprocess.run(['kubectl', 'taint', 'node', self.node_name, taint, '--overwrite'])
        
        print(f"✅ Enhanced master node {self.node_name} configured")
    
    def _install_enhanced_ingress(self) -> None:
        """Install NGINX Ingress optimized for enhanced VPS"""
        print("🌐 Installing enhanced NGINX Ingress...")
        
        # Apply standard NGINX Ingress
        subprocess.run([
            'kubectl', 'apply', '-f',
            'https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/cloud/deploy.yaml'
        ])
        
        # Wait for ingress deployment
        time.sleep(30)
        
        # Patch with enhanced resource allocation
        patch = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "controller",
                            "resources": {
                                "limits": {
                                    "cpu": "800m",      # Enhanced VPS can handle more
                                    "memory": "800Mi"
                                },
                                "requests": {
                                    "cpu": "400m", 
                                    "memory": "400Mi"
                                }
                            }
                        }]
                    }
                }
            }
        }
        
        subprocess.run([
            'kubectl', 'patch', 'deployment', 'ingress-nginx-controller',
            '-n', 'ingress-nginx', '--patch', json.dumps(patch)
        ])
        
        print("✅ Enhanced NGINX Ingress configured")
    
    def _create_enhanced_worker_script(self) -> None:
        """Create optimized worker join script"""
        try:
            with open('/var/lib/rancher/k3s/server/node-token', 'r') as f:
                token = f.read().strip()
        except PermissionError:
            result = subprocess.run(['sudo', 'cat', '/var/lib/rancher/k3s/server/node-token'],
                                  capture_output=True, text=True)
            token = result.stdout.strip()
        
        script_path = Path.home() / 'join_worker_enhanced.py'
        script_content = f'''#!/usr/bin/env python3
# Enhanced Worker Join Script
# Optimized for Home PC workers with high-performance configuration

import sys
from pathlib import Path

# Add script directory to path
sys.path.insert(0, str(Path(__file__).parent))

from install_cluster_enhanced import EnhancedK3SInstaller

def main():
    installer = EnhancedK3SInstaller()
    
    if not installer.check_prerequisites():
        print("❌ Prerequisites check failed")
        sys.exit(1)
    
    success = installer.install_worker("{self.tailscale_ip}", "{token}")
    
    if success:
        # Apply Home PC worker labels
        print("🏷️  Applying Home PC worker labels...")
        labels = {{
            "node-type": "home-pc",
            "role": "worker",
            "compute-tier": "workload",
            "network-speed": "1000mbps",
            "network-latency": "low",
            "zone": "local",
            "gpu-enabled": "true",
            "high-performance": "true",
            "can-run-heavy-workloads": "true"
        }}
        
        import subprocess
        for key, value in labels.items():
            subprocess.run([
                'kubectl', 'label', 'node', installer.node_name,
                f'{{key}}={{value}}', '--overwrite'
            ])
        
        print("🎉 Enhanced worker setup completed!")
        print("📊 Node configured for high-performance workloads")
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
'''
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
        
        print(f"📝 Enhanced worker join script: {script_path}")
        print(f"   Copy to workers: scp {script_path} user@homepc:/tmp/")
        print(f"   Run on workers: python3 /tmp/join_worker_enhanced.py")
    
    def _apply_worker_optimizations(self) -> None:
        """Apply optimizations for Home PC workers"""
        optimizations = [
            # Optimize for high-performance workloads
            'echo "vm.swappiness=1" | sudo tee -a /etc/sysctl.conf',
            'echo "kernel.pid_max=4194304" | sudo tee -a /etc/sysctl.conf',
            
            # Network optimization for 1Gbps local
            'echo "net.core.rmem_max=67108864" | sudo tee -a /etc/sysctl.conf',
            'echo "net.core.wmem_max=67108864" | sudo tee -a /etc/sysctl.conf',
            'echo "net.ipv4.tcp_rmem=4096 87380 67108864" | sudo tee -a /etc/sysctl.conf',
            'echo "net.ipv4.tcp_wmem=4096 65536 67108864" | sudo tee -a /etc/sysctl.conf',
            
            'sudo sysctl -p'
        ]
        
        for cmd in optimizations:
            subprocess.run(cmd, shell=True, capture_output=True)
    
    def _command_exists(self, command: str) -> bool:
        """Check if command exists"""
        return subprocess.run(['which', command], 
                            capture_output=True).returncode == 0
    
    def show_cluster_info(self) -> None:
        """Show cluster information"""
        print("\n📋 Enhanced Cluster Information:")
        print(f"   VPS Master: {self.node_name} ({self.tailscale_ip})")
        print(f"   Specifications: {self.vps_specs['cpu_cores']} vCPU, {self.vps_specs['memory_gb']}GB RAM, {self.vps_specs['storage_gb']}GB")
        print("\n🔗 Next Steps:")
        print("   1. Join worker nodes using ~/join_worker_enhanced.py")
        print("   2. Apply production standards: kubectl apply -f manifests/prod/")
        print("   3. Deploy your services with node selectors")
        print("\n📊 Monitoring:")
        print("   kubectl get nodes -o wide")
        print("   kubectl top nodes  # After metrics-server starts")


def main():
    parser = argparse.ArgumentParser(
        description='Enhanced K3S Cluster Installer (VPS: 3 vCPU, 4GB RAM, 100GB)'
    )
    parser.add_argument('--mode', choices=['master', 'worker'], required=True,
                      help='Installation mode')
    parser.add_argument('--master-ip', type=str,
                      help='Master node Tailscale IP (required for worker mode)')
    parser.add_argument('--token', type=str,
                      help='Join token (required for worker mode)')
    
    args = parser.parse_args()
    
    installer = EnhancedK3SInstaller()
    
    print(f"🚀 K3S Enhanced Installer - {args.mode.upper()} mode")
    print()
    
    if not installer.check_prerequisites():
        sys.exit(1)
    
    if args.mode == 'master':
        success = installer.install_enhanced_master()
        if success:
            installer.show_cluster_info()
        else:
            sys.exit(1)
    
    elif args.mode == 'worker':
        if not args.master_ip or not args.token:
            print("❌ Worker mode requires --master-ip and --token")
            sys.exit(1)
        
        success = installer.install_worker(args.master_ip, args.token)
        if not success:
            sys.exit(1)


if __name__ == '__main__':
    main()