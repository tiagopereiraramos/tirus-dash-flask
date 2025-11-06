"""
Modelos para Integração com API Externa (http://191.252.218.230:8000)
Alinhado 100% com a documentação oficial da API em produção
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime


# =============================================================================
# MODELOS DE PAYLOAD - Exatamente como a API espera
# =============================================================================

@dataclass
class AutomacaoPayload:
    """
    Payload para execução de RPA em operadoras (OI, VIVO, EMBRATEL, DIGITALNET)
    
    Endpoint: POST /executar/{operadora}
    Documentação: Seção 4.2.2
    """
    login: str
    senha: str
    filtro: str
    cnpj: str
    processo_id: Optional[str] = None  # UUID do processo (opcional mas recomendado)

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para envio à API"""
        payload = {
            "login": self.login,
            "senha": self.senha,
            "filtro": self.filtro,
            "cnpj": self.cnpj
        }
        
        # Adicionar processo_id se fornecido (para rastreamento e atualização automática)
        if self.processo_id:
            payload["processo_id"] = self.processo_id
            
        return payload

    def validate(self) -> List[str]:
        """Valida campos obrigatórios"""
        erros = []
        
        if not self.login:
            erros.append("login é obrigatório")
        if not self.senha:
            erros.append("senha é obrigatória")
        if not self.filtro:
            erros.append("filtro é obrigatório")
        if not self.cnpj:
            erros.append("cnpj é obrigatório")
            
        return erros


@dataclass
class AutomacaoPayloadSat:
    """
    Payload para execução de RPA no SAT
    
    Endpoint: POST /executar/sat
    Documentação: Seção 4.2.3
    """
    login: str
    senha: str
    cnpj: str
    razao: str
    operadora: str
    nome_filtro: str
    unidade: str
    servico: str
    dados_sat: str
    nome_arquivo: str
    data_vencimento: str  # Formato: DD/MM/YYYY
    processo_id: str = None  # Para rastreamento

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para envio à API"""
        payload = {
            "login": self.login,
            "senha": self.senha,
            "cnpj": self.cnpj,
            "razao": self.razao,
            "operadora": self.operadora,
            "nome_filtro": self.nome_filtro,
            "unidade": self.unidade,
            "servico": self.servico,
            "dados_sat": self.dados_sat,
            "nome_arquivo": self.nome_arquivo,
            "data_vencimento": self.data_vencimento
        }
        
        # Adicionar processo_id se fornecido (para rastreamento)
        if self.processo_id:
            payload["processo_id"] = self.processo_id
            
        return payload

    def validate(self) -> List[str]:
        """Valida campos obrigatórios"""
        erros = []
        
        if not self.login:
            erros.append("login é obrigatório")
        if not self.senha:
            erros.append("senha é obrigatória")
        if not self.cnpj:
            erros.append("cnpj é obrigatório")
        if not self.razao:
            erros.append("razao é obrigatória")
        if not self.operadora:
            erros.append("operadora é obrigatória")
        if not self.nome_filtro:
            erros.append("nome_filtro é obrigatório")
        if not self.unidade:
            erros.append("unidade é obrigatória")
        if not self.servico:
            erros.append("servico é obrigatório")
        if not self.dados_sat:
            erros.append("dados_sat é obrigatório")
        if not self.nome_arquivo:
            erros.append("nome_arquivo é obrigatório")
        if not self.data_vencimento:
            erros.append("data_vencimento é obrigatória")
            
        return erros


# =============================================================================
# MODELOS DE RESPOSTA - Conforme a API retorna
# =============================================================================

@dataclass
class JobResponse:
    """
    Resposta ao criar um novo job
    
    Documentação: Seção 5.3
    """
    job_id: str
    status: str  # Sempre "PENDING" quando criado
    message: str
    status_url: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobResponse':
        """Cria instância a partir da resposta da API"""
        return cls(
            job_id=data.get('job_id', ''),
            status=data.get('status', 'PENDING'),
            message=data.get('message', ''),
            status_url=data.get('status_url', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'job_id': self.job_id,
            'status': self.status,
            'message': self.message,
            'status_url': self.status_url
        }


@dataclass
class JobStatus:
    """
    Status detalhado de um job
    
    Documentação: Seção 5.4
    """
    job_id: str
    operadora: str
    status: str  # PENDING, RUNNING, COMPLETED, FAILED
    progress: int = 0  # 0-100
    result: Optional[str] = None  # Caminho do arquivo quando COMPLETED
    error: Optional[str] = None  # Mensagem de erro quando FAILED
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'JobStatus':
        """Cria instância a partir da resposta da API"""
        return cls(
            job_id=data.get('job_id', ''),
            operadora=data.get('operadora', ''),
            status=data.get('status', 'PENDING'),
            progress=data.get('progress', 0),
            result=data.get('result'),
            error=data.get('error'),
            created_at=data.get('created_at'),
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            logs=data.get('logs', [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'job_id': self.job_id,
            'operadora': self.operadora,
            'status': self.status,
            'progress': self.progress,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'logs': self.logs
        }
    
    @property
    def is_finished(self) -> bool:
        """Verifica se o job já foi concluído"""
        return self.status in ['COMPLETED', 'FAILED']
    
    @property
    def is_success(self) -> bool:
        """Verifica se o job foi concluído com sucesso"""
        return self.status == 'COMPLETED'
    
    @property
    def is_error(self) -> bool:
        """Verifica se o job falhou"""
        return self.status == 'FAILED'


@dataclass
class HealthResponse:
    """
    Resposta do health check
    
    Documentação: Seção 5.5
    """
    status: str  # healthy ou unhealthy
    message: str
    jobs_pending: int
    jobs_active: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HealthResponse':
        """Cria instância a partir da resposta da API"""
        return cls(
            status=data.get('status', 'unhealthy'),
            message=data.get('message', ''),
            jobs_pending=data.get('jobs_pending', 0),
            jobs_active=data.get('jobs_active', 0)
        )


# =============================================================================
# BACKWARD COMPATIBILITY - Aliases para manter compatibilidade com código existente
# =============================================================================

# Manter compatibilidade com código existente que usa os nomes antigos
PayloadRPAProducao = AutomacaoPayload
PayloadSATProducao = AutomacaoPayloadSat
