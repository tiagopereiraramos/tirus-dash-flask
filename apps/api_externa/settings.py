"""
Sistema de Configurações Personalizáveis para API Externa Funcional
Gerencia configurações de timeout, retry, cache e outras personalizações
"""
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class APISettings:
    """Configurações da API externa"""
    # URLs e endpoints
    base_url: str = "http://191.252.218.230:8000"
    health_endpoint: str = "/health"
    rpa_endpoint: str = "/executar/{operadora}"
    sat_endpoint: str = "/executar/sat"
    status_endpoint: str = "/status/{job_id}"

    # Timeouts
    connection_timeout: int = 30
    read_timeout: int = 90
    job_timeout: int = 300  # 5 minutos

    # Retry configuration
    max_retries: int = 3
    retry_delay: int = 2
    retry_backoff: float = 2.0

    # Cache settings
    cache_enabled: bool = True
    cache_max_size: int = 1000
    cache_ttl: int = 3600  # 1 hora
    cache_cleanup_interval: int = 300  # 5 minutos

    # Monitor settings
    monitor_enabled: bool = True
    monitor_interval: int = 10  # segundos
    monitor_max_concurrent: int = 10
    monitor_timeout: int = 60

    # Notification settings
    notifications_enabled: bool = True
    email_notifications: bool = False
    webhook_notifications: bool = False

    # Performance settings
    max_concurrent_jobs: int = 5
    job_queue_size: int = 100
    enable_compression: bool = True

    # Logging settings
    log_level: str = "INFO"
    log_file: str = "api_externa.log"
    log_max_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5

    # Security settings
    verify_ssl: bool = True
    allow_insecure: bool = False
    api_key_header: str = "X-API-Key"
    api_key: str = ""

    # Debug settings
    debug_mode: bool = False
    verbose_logging: bool = False
    enable_metrics: bool = True


@dataclass
class OperatorSettings:
    """Configurações específicas por operadora"""
    operadora: str
    enabled: bool = True
    timeout_multiplier: float = 1.0
    max_retries: int = 3
    priority: int = 1  # 1 = alta, 2 = média, 3 = baixa

    # Configurações específicas
    custom_headers: Dict[str, str] = field(default_factory=dict)
    custom_timeout: Optional[int] = None
    custom_retry_delay: Optional[int] = None

    # Limites
    max_jobs_per_hour: int = 100
    max_jobs_per_day: int = 1000
    cooldown_after_failure: int = 300  # 5 minutos

    # Configurações de payload
    default_login: str = ""
    default_senha: str = ""
    default_filtro: str = ""
    default_cnpj: str = ""


@dataclass
class SystemSettings:
    """Configurações do sistema"""
    # Database settings
    db_connection_pool_size: int = 10
    db_connection_timeout: int = 30

    # Background tasks
    background_tasks_enabled: bool = True
    task_queue_size: int = 1000
    worker_threads: int = 4

    # File storage
    temp_dir: str = "/tmp/rpa_dashboard"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    cleanup_temp_files: bool = True
    temp_file_ttl: int = 86400  # 24 horas

    # Session settings
    session_timeout: int = 3600  # 1 hora
    max_sessions_per_user: int = 5

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hora


class SettingsManager:
    """Gerenciador de configurações"""

    def __init__(self, config_file: str = None):
        """
        Inicializa o gerenciador de configurações

        Args:
            config_file: Caminho para arquivo de configuração
        """
        self.config_file = config_file or "config/api_externa.json"
        self.config_dir = Path(self.config_file).parent

        # Configurações padrão
        self.api_settings = APISettings()
        self.operator_settings: Dict[str, OperatorSettings] = {}
        self.system_settings = SystemSettings()

        # Carregar configurações
        self.load_settings()

        logger.info("SettingsManager inicializado")

    def load_settings(self):
        """Carrega configurações do arquivo"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # Carregar configurações da API
                if 'api' in config_data:
                    api_data = config_data['api']
                    for key, value in api_data.items():
                        if hasattr(self.api_settings, key):
                            setattr(self.api_settings, key, value)

                # Carregar configurações de operadoras
                if 'operators' in config_data:
                    for op_data in config_data['operators']:
                        operator = OperatorSettings(**op_data)
                        self.operator_settings[operator.operadora] = operator

                # Carregar configurações do sistema
                if 'system' in config_data:
                    system_data = config_data['system']
                    for key, value in system_data.items():
                        if hasattr(self.system_settings, key):
                            setattr(self.system_settings, key, value)

                logger.info(f"Configurações carregadas de {self.config_file}")
            else:
                # Criar configurações padrão
                self.create_default_settings()

        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {str(e)}")
            self.create_default_settings()

    def save_settings(self):
        """Salva configurações no arquivo"""
        try:
            # Criar diretório se não existir
            self.config_dir.mkdir(parents=True, exist_ok=True)

            config_data = {
                'api': asdict(self.api_settings),
                'operators': [asdict(op) for op in self.operator_settings.values()],
                'system': asdict(self.system_settings),
                'last_updated': datetime.now().isoformat()
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2,
                          ensure_ascii=False, default=str)

            logger.info(f"Configurações salvas em {self.config_file}")

        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {str(e)}")

    def create_default_settings(self):
        """Cria configurações padrão"""
        # Configurações padrão para operadoras
        default_operators = [
            OperatorSettings(
                operadora="OI",
                enabled=True,
                timeout_multiplier=1.2,
                max_retries=3,
                priority=1,
                max_jobs_per_hour=50,
                max_jobs_per_day=500
            ),
            OperatorSettings(
                operadora="VIVO",
                enabled=True,
                timeout_multiplier=1.0,
                max_retries=3,
                priority=1,
                max_jobs_per_hour=50,
                max_jobs_per_day=500
            ),
            OperatorSettings(
                operadora="EMBRATEL",
                enabled=True,
                timeout_multiplier=1.1,
                max_retries=3,
                priority=2,
                max_jobs_per_hour=30,
                max_jobs_per_day=300
            ),
            OperatorSettings(
                operadora="DIGITALNET",
                enabled=True,
                timeout_multiplier=1.0,
                max_retries=3,
                priority=2,
                max_jobs_per_hour=30,
                max_jobs_per_day=300
            ),
            OperatorSettings(
                operadora="SAT",
                enabled=True,
                timeout_multiplier=1.5,
                max_retries=2,
                priority=3,
                max_jobs_per_hour=20,
                max_jobs_per_day=200
            )
        ]

        for operator in default_operators:
            self.operator_settings[operator.operadora] = operator

        # Salvar configurações padrão
        self.save_settings()

    def get_operator_settings(self, operadora: str) -> Optional[OperatorSettings]:
        """Obtém configurações de uma operadora"""
        return self.operator_settings.get(operadora.upper())

    def update_operator_settings(self, operadora: str, **kwargs) -> bool:
        """Atualiza configurações de uma operadora"""
        try:
            if operadora not in self.operator_settings:
                # Criar nova operadora
                self.operator_settings[operadora] = OperatorSettings(
                    operadora=operadora)

            operator = self.operator_settings[operadora]

            # Atualizar campos
            for key, value in kwargs.items():
                if hasattr(operator, key):
                    setattr(operator, key, value)

            self.save_settings()
            logger.info(f"Configurações da operadora {operadora} atualizadas")
            return True

        except Exception as e:
            logger.error(
                f"Erro ao atualizar configurações da operadora {operadora}: {str(e)}")
            return False

    def get_api_setting(self, key: str, default: Any = None) -> Any:
        """Obtém uma configuração da API"""
        return getattr(self.api_settings, key, default)

    def update_api_setting(self, key: str, value: Any) -> bool:
        """Atualiza uma configuração da API"""
        try:
            if hasattr(self.api_settings, key):
                setattr(self.api_settings, key, value)
                self.save_settings()
                logger.info(
                    f"Configuração da API {key} atualizada para {value}")
                return True
            else:
                logger.warning(f"Configuração da API {key} não existe")
                return False

        except Exception as e:
            logger.error(
                f"Erro ao atualizar configuração da API {key}: {str(e)}")
            return False

    def get_system_setting(self, key: str, default: Any = None) -> Any:
        """Obtém uma configuração do sistema"""
        return getattr(self.system_settings, key, default)

    def update_system_setting(self, key: str, value: Any) -> bool:
        """Atualiza uma configuração do sistema"""
        try:
            if hasattr(self.system_settings, key):
                setattr(self.system_settings, key, value)
                self.save_settings()
                logger.info(
                    f"Configuração do sistema {key} atualizada para {value}")
                return True
            else:
                logger.warning(f"Configuração do sistema {key} não existe")
                return False

        except Exception as e:
            logger.error(
                f"Erro ao atualizar configuração do sistema {key}: {str(e)}")
            return False

    def get_all_settings(self) -> Dict[str, Any]:
        """Obtém todas as configurações"""
        return {
            'api': asdict(self.api_settings),
            'operators': {op: asdict(settings) for op, settings in self.operator_settings.items()},
            'system': asdict(self.system_settings),
            'config_file': self.config_file,
            'last_updated': datetime.now().isoformat()
        }

    def validate_settings(self) -> Dict[str, List[str]]:
        """Valida configurações"""
        errors = {
            'api': [],
            'operators': [],
            'system': []
        }

        # Validar configurações da API
        if self.api_settings.connection_timeout <= 0:
            errors['api'].append("connection_timeout deve ser maior que 0")

        if self.api_settings.read_timeout <= 0:
            errors['api'].append("read_timeout deve ser maior que 0")

        if self.api_settings.max_retries < 0:
            errors['api'].append("max_retries deve ser maior ou igual a 0")

        if self.api_settings.cache_max_size <= 0:
            errors['api'].append("cache_max_size deve ser maior que 0")

        # Validar configurações de operadoras
        for operadora, settings in self.operator_settings.items():
            if settings.timeout_multiplier <= 0:
                errors['operators'].append(
                    f"{operadora}: timeout_multiplier deve ser maior que 0")

            if settings.max_retries < 0:
                errors['operators'].append(
                    f"{operadora}: max_retries deve ser maior ou igual a 0")

            if settings.max_jobs_per_hour <= 0:
                errors['operators'].append(
                    f"{operadora}: max_jobs_per_hour deve ser maior que 0")

        # Validar configurações do sistema
        if self.system_settings.db_connection_pool_size <= 0:
            errors['system'].append(
                "db_connection_pool_size deve ser maior que 0")

        if self.system_settings.worker_threads <= 0:
            errors['system'].append("worker_threads deve ser maior que 0")

        return errors

    def reset_to_defaults(self):
        """Reseta configurações para padrão"""
        try:
            # Remover arquivo de configuração
            if os.path.exists(self.config_file):
                os.remove(self.config_file)

            # Recriar configurações padrão
            self.api_settings = APISettings()
            self.operator_settings.clear()
            self.system_settings = SystemSettings()

            self.create_default_settings()
            logger.info("Configurações resetadas para padrão")

        except Exception as e:
            logger.error(f"Erro ao resetar configurações: {str(e)}")

    def export_settings(self, format: str = 'json') -> Union[str, bytes]:
        """Exporta configurações"""
        try:
            if format == 'json':
                return json.dumps(self.get_all_settings(), indent=2, ensure_ascii=False, default=str)
            else:
                raise ValueError(f"Formato não suportado: {format}")

        except Exception as e:
            logger.error(f"Erro ao exportar configurações: {str(e)}")
            return ""

    def import_settings(self, settings_data: Dict[str, Any]) -> bool:
        """Importa configurações"""
        try:
            # Validar estrutura
            required_keys = ['api', 'operators', 'system']
            for key in required_keys:
                if key not in settings_data:
                    raise ValueError(
                        f"Chave obrigatória '{key}' não encontrada")

            # Aplicar configurações
            if 'api' in settings_data:
                for key, value in settings_data['api'].items():
                    if hasattr(self.api_settings, key):
                        setattr(self.api_settings, key, value)

            if 'operators' in settings_data:
                self.operator_settings.clear()
                for op_data in settings_data['operators']:
                    operator = OperatorSettings(**op_data)
                    self.operator_settings[operator.operadora] = operator

            if 'system' in settings_data:
                for key, value in settings_data['system'].items():
                    if hasattr(self.system_settings, key):
                        setattr(self.system_settings, key, value)

            # Salvar
            self.save_settings()
            logger.info("Configurações importadas com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao importar configurações: {str(e)}")
            return False


# Instância global
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager(config_file: str = None) -> SettingsManager:
    """Obtém instância global do gerenciador de configurações"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager(config_file)
    return _settings_manager


def get_api_settings() -> APISettings:
    """Obtém configurações da API"""
    return get_settings_manager().api_settings


def get_operator_settings(operadora: str) -> Optional[OperatorSettings]:
    """Obtém configurações de uma operadora"""
    return get_settings_manager().get_operator_settings(operadora)


def get_system_settings() -> SystemSettings:
    """Obtém configurações do sistema"""
    return get_settings_manager().system_settings
