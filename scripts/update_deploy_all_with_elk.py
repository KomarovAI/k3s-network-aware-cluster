#!/usr/bin/env python3
"""
Обновляем deploy_all_optimized.py чтобы включить ELK Stack в автоматическое
развертывание на worker ноде вместе с остальным мониторингом.
"""

from pathlib import Path

def update_deploy_script():
    """Patch deploy_all_optimized.py to include ELK deployment"""
    
    file_path = Path('scripts/deploy_all_optimized.py')
    content = file_path.read_text(encoding='utf-8')
    
    # Добавляем флаг для ELK
    if '--enable-elk' not in content:
        # Добавляем аргумент
        content = content.replace(
            'parser.add_argument("--dns01", action="store_true", help="Использовать DNS-01 (Cloudflare) если установлен CF_API_TOKEN")',
            '''parser.add_argument("--dns01", action="store_true", help="Использовать DNS-01 (Cloudflare) если установлен CF_API_TOKEN")
    parser.add_argument("--enable-elk", action="store_true", help="Развернуть ELK Stack на worker для централизованного логирования")
    parser.add_argument("--elk-retention", type=int, default=15, help="Срок хранения логов ELK (дней)")
    parser.add_argument("--elk-light", action="store_true", help="Облегченный режим ELK (меньше ресурсов)")
    parser.add_argument("--elk-light", action="store_true", help="Облегченный режим ELK (меньше ресурсов)")'''
        )
        
        # Добавляем параметр в конструктор
        content = content.replace(
            'def __init__(self, domain: str, email: str, enable_gpu: bool, use_dns01: bool):',
            'def __init__(self, domain: str, email: str, enable_gpu: bool, use_dns01: bool, enable_elk: bool = False, elk_retention: int = 15, elk_light: bool = False):'
        )
        
        content = content.replace(
            'self.use_dns01 = use_dns01',
            '''self.use_dns01 = use_dns01
        self.enable_elk = enable_elk
        self.elk_retention = elk_retention
        self.elk_light = elk_light'''
        )
        
        # Добавляем метод для ELK
        elk_method = '''    
    def deploy_elk_stack_on_worker(self):
        """Развертывание ELK Stack на worker ноде"""
        if not self.enable_elk:
            return True
            
        self.log_info("Развертывание ELK Stack на worker...")
        
        # Запускаем специальный скрипт
        elk_cmd = [
            "python3", "scripts/deploy_elk_on_worker.py",
            "--domain", self.domain,
            "--retention-days", str(self.elk_retention)
        ]
        
        if self.elk_light:
            elk_cmd.append("--light-mode")
        
        result = subprocess.run(elk_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.log_success(f"ELK Stack развернут на worker: https://kibana.{self.domain}")
            if not self.elk_light:
                self.log_success(f"Jaeger развернут: https://jaeger.{self.domain}")
            return True
        else:
            self.log_error(f"Ошибка развертывания ELK: {result.stderr}")
            return False
'''
        
        # Вставляем метод перед deploy_worker_components
        content = content.replace(
            'def deploy_worker_components(self) -> bool:',
            elk_method + '\n    def deploy_worker_components(self) -> bool:'
        )
        
        # Добавляем вызов ELK в deploy_worker_components
        content = content.replace(
            '        # 5. GPU мониторинг (если включен)',
            '''        # 5. ELK Stack (если включен)
        if not self.deploy_elk_stack_on_worker():
            self.log_error("Ошибка развертывания ELK Stack")
        
        # 6. GPU мониторинг (если включен)'''
        )
        
        # Обновляем создание экземпляра класса
        content = content.replace(
            '''deployer = OptimizedClusterDeployer(
        domain=args.domain,
        email=args.email,
        enable_gpu=args.gpu.lower() == "true",
        use_dns01=args.dns01
    )''',
            '''deployer = OptimizedClusterDeployer(
        domain=args.domain,
        email=args.email,
        enable_gpu=args.gpu.lower() == "true",
        use_dns01=args.dns01,
        enable_elk=args.enable_elk,
        elk_retention=args.elk_retention,
        elk_light=args.elk_light
    )'''
        )
        
        # Обновляем show_resource_distribution
        content = content.replace(
            'print(f"  ✅ Kubevious (визуализация)")',
            '''print(f"  ✅ Kubevious (визуализация)")
            if self.enable_elk:
                print(f"  ✅ ELK Stack (логирование)")
                if not self.elk_light:
                    print(f"  ✅ Jaeger (трассировка)")'''
        )
        
        # Обновляем финальные URL
        content = content.replace(
            'print(f"  • Kubevious: https://kubevious.{self.domain}")',
            '''print(f"  • Kubevious: https://kubevious.{self.domain}")
        if self.enable_elk:
            print(f"  • Kibana:    https://kibana.{self.domain}")
            if not self.elk_light:
                print(f"  • Jaeger:    https://jaeger.{self.domain}")'''
        )
        
        # Обновляем использование RAM на worker
        content = content.replace(
            'print(f"  📊 Использование: ~4% CPU, ~3% RAM")',
            '''elk_ram_usage = "~6-8% RAM" if self.enable_elk else "~3% RAM"
            elk_cpu_usage = "~6-8% CPU" if self.enable_elk else "~4% CPU"
            print(f"  📊 Использование: {elk_cpu_usage}, {elk_ram_usage}")'''
        )
    
    file_path.write_text(content, encoding='utf-8')
    print('✅ deploy_all_optimized.py обновлен для работы с ELK Stack')

if __name__ == '__main__':
    update_deploy_script()