"""
Módulo de integração com APIs externas
"""
from .models import (
    # Modelos existentes
    PayloadRPAExterno,
    RespostaRPAExterno,
    PayloadSATExterno,
    RespostaSATExterno,
    PayloadRPAProducao,
    PayloadSATProducao,
    RespostaProducao,
    # Novos modelos para API externa funcional
    JobStatus,
    ExecutionLog,
    ResultCache,
    AutomacaoPayload,
    AutomacaoPayloadSat,
    JobResponse
)

# Novos módulos da Fase 4: Funcionalidades Avançadas
from .notifications import (
    NotificationConfig,
    NotificationEvent,
    NotificationManager,
    get_notification_manager,
    set_notification_config
)

from .reports import (
    ReportConfig,
    PerformanceMetrics,
    OperatorMetrics,
    ErrorAnalysis,
    TrendData,
    ReportGenerator,
    get_report_generator
)

from .settings import (
    APISettings,
    OperatorSettings,
    SystemSettings,
    SettingsManager,
    get_settings_manager,
    get_api_settings,
    get_operator_settings,
    get_system_settings
)

from .services import APIExternaService
from .services_externos import APIExternaFuncionalService
from .routes import bp as api_externa_bp
from .routes_externos import bp_externos as api_externos_bp
from .routes_avancadas import bp_avancadas as api_avancadas_bp
from .routes_monitoramento import bp_monitoramento as api_monitoramento_bp
from .routes_logs_tempo_real import api_logs_tempo_real_bp

# Novos módulos da API externa funcional
from .client import APIExternaClient
from .cache import get_cache, clear_cache, get_cache_stats
from .monitor import JobMonitor, AsyncJobMonitor, get_monitor, start_monitor, stop_monitor

# Módulo de autenticação
from .auth import (
    APIExternaAuth,
    get_auth,
    test_api_externa_connection,
    list_api_externa_jobs,
    get_api_externa_job_status
)

__all__ = [
    # Modelos
    'PayloadRPAExterno',
    'RespostaRPAExterno',
    'PayloadSATExterno',
    'RespostaSATExterno',
    'PayloadRPAProducao',
    'PayloadSATProducao',
    'RespostaProducao',
    'JobStatus',
    'ExecutionLog',
    'ResultCache',
    'AutomacaoPayload',
    'AutomacaoPayloadSat',
    'JobResponse',
    # Notificações
    'NotificationConfig',
    'NotificationEvent',
    'NotificationManager',
    'get_notification_manager',
    'set_notification_config',
    # Relatórios
    'ReportConfig',
    'PerformanceMetrics',
    'OperatorMetrics',
    'ErrorAnalysis',
    'TrendData',
    'ReportGenerator',
    'get_report_generator',
    # Configurações
    'APISettings',
    'OperatorSettings',
    'SystemSettings',
    'SettingsManager',
    'get_settings_manager',
    'get_api_settings',
    'get_operator_settings',
    'get_system_settings',
    # Serviços
    'APIExternaService',
    'APIExternaFuncionalService',
    # Blueprints
    'api_externa_bp',
    'api_externos_bp',
    'api_avancadas_bp',
    'api_monitoramento_bp',
    'api_logs_tempo_real_bp',
    # Cliente e Cache
    'APIExternaClient',
    'get_cache',
    'clear_cache',
    'get_cache_stats',
    # Monitor
    'JobMonitor',
    'AsyncJobMonitor',
    'get_monitor',
    'start_monitor',
    'stop_monitor',
    # Autenticação
    'APIExternaAuth',
    'get_auth',
    'test_api_externa_connection',
    'list_api_externa_jobs',
    'get_api_externa_job_status'
]
