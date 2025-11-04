"""
Modelos para APIs Externas
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime, timedelta
import uuid


class TipoOperacaoExterna(Enum):
    """Tipos de operações suportadas pelas APIs externas"""
    DOWNLOAD_FATURA = "DOWNLOAD_FATURA"
    UPLOAD_SAT = "UPLOAD_SAT"
    TESTE_CONEXAO = "TESTE_CONEXAO"


class StatusOperacaoExterna(Enum):
    """Status das operações externas"""
    PENDENTE = "PENDENTE"
    EXECUTANDO = "EXECUTANDO"
    SUCESSO = "SUCESSO"
    ERRO = "ERRO"
    TIMEOUT = "TIMEOUT"


@dataclass
class DadosCliente:
    """Dados do cliente para integração externa"""
    id: str
    razao_social: str
    nome_sat: str
    cnpj: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    login_portal: Optional[str] = None
    senha_portal: Optional[str] = None
    cpf: Optional[str] = None
    filtro: str = "fatura_mensal"
    unidade: str = "MATRIZ"
    servico: str = "INTERNET_DEDICADA"
    dados_sat: Optional[str] = None
    endereco: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validação pós-inicialização"""
        if not self.dados_sat:
            self.dados_sat = f"{self.nome_sat}|INTERNET|DEDICADA"


@dataclass
class DadosOperadora:
    """Dados da operadora para integração externa"""
    id: str
    codigo: str
    nome: str
    url_portal: str
    usuario_portal: Optional[str] = None
    senha_portal: Optional[str] = None
    tipo_autenticacao: Optional[str] = None
    timeout_segundos: int = 300
    tentativas_maximas: int = 3
    intervalo_tentativas: int = 60
    configuracao_rpa: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Configuração padrão do RPA se não fornecida"""
        if not self.configuracao_rpa:
            self.configuracao_rpa = {
                "timeout_padrao": self.timeout_segundos,
                "tentativas_maximas": self.tentativas_maximas,
                "parametros_especiais": {
                    "wait_element": 10,
                    "headless": True,
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            }


@dataclass
class DadosProcesso:
    """Dados do processo para integração externa"""
    id: str
    mes_ano: str
    status_atual: str
    url_fatura: Optional[str] = None
    data_vencimento: Optional[str] = None
    valor_fatura: Optional[float] = None
    observacoes: Optional[str] = None


@dataclass
class DadosExecucao:
    """Dados da execução para integração externa"""
    numero_tentativa: int = 1
    ip_origem: str = "192.168.1.100"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    timestamp_inicio: str = field(
        default_factory=lambda: datetime.now().isoformat())


@dataclass
class Metadata:
    """Metadados da integração"""
    timestamp_envio: str = field(
        default_factory=lambda: datetime.now().isoformat())
    versao_payload: str = "2.0"
    sistema_origem: str = "TIRUS_DASH_FLASK"
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    modo_teste: bool = False


@dataclass
class PayloadRPAExterno:
    """Payload padrão para envio aos RPAs externos - Versão 2.0"""
    processo_id: str
    operacao: str
    cliente: DadosCliente
    operadora: DadosOperadora
    processo: DadosProcesso
    execucao: DadosExecucao
    metadata: Metadata = field(default_factory=Metadata)

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "processo_id": self.processo_id,
            "operacao": self.operacao,
            "cliente": {
                "id": self.cliente.id,
                "razao_social": self.cliente.razao_social,
                "nome_sat": self.cliente.nome_sat,
                "cnpj": self.cliente.cnpj,
                "email": self.cliente.email,
                "telefone": self.cliente.telefone,
                "login_portal": self.cliente.login_portal,
                "senha_portal": self.cliente.senha_portal,
                "cpf": self.cliente.cpf,
                "filtro": self.cliente.filtro,
                "unidade": self.cliente.unidade,
                "servico": self.cliente.servico,
                "dados_sat": self.cliente.dados_sat,
                "endereco": self.cliente.endereco
            },
            "operadora": {
                "id": self.operadora.id,
                "codigo": self.operadora.codigo,
                "nome": self.operadora.nome,
                "url_portal": self.operadora.url_portal,
                "credenciais": {
                    "usuario": self.operadora.usuario_portal,
                    "senha": self.operadora.senha_portal,
                    "tipo_autenticacao": self.operadora.tipo_autenticacao
                },
                "configuracoes": {
                    "timeout_segundos": self.operadora.timeout_segundos,
                    "tentativas_maximas": self.operadora.tentativas_maximas,
                    "intervalo_tentativas": self.operadora.intervalo_tentativas
                },
                "configuracao_rpa": self.operadora.configuracao_rpa
            },
            "processo": {
                "id": self.processo.id,
                "mes_ano": self.processo.mes_ano,
                "status_atual": self.processo.status_atual,
                "url_fatura": self.processo.url_fatura,
                "data_vencimento": self.processo.data_vencimento,
                "valor_fatura": self.processo.valor_fatura,
                "observacoes": self.processo.observacoes
            },
            "execucao": {
                "numero_tentativa": self.execucao.numero_tentativa,
                "ip_origem": self.execucao.ip_origem,
                "user_agent": self.execucao.user_agent,
                "timestamp_inicio": self.execucao.timestamp_inicio
            },
            "metadata": {
                "timestamp_envio": self.metadata.timestamp_envio,
                "versao_payload": self.metadata.versao_payload,
                "sistema_origem": self.metadata.sistema_origem,
                "request_id": self.metadata.request_id,
                "modo_teste": self.metadata.modo_teste
            }
        }

    def validar(self) -> List[str]:
        """Valida campos obrigatórios"""
        erros = []

        if not self.processo_id:
            erros.append("processo_id é obrigatório")

        if not self.operacao:
            erros.append("operacao é obrigatória")

        if not self.cliente.id:
            erros.append("cliente.id é obrigatório")

        if not self.cliente.razao_social:
            erros.append("cliente.razao_social é obrigatório")

        if not self.cliente.cnpj:
            erros.append("cliente.cnpj é obrigatório")

        if not self.operadora.id:
            erros.append("operadora.id é obrigatório")

        if not self.operadora.codigo:
            erros.append("operadora.codigo é obrigatório")

        if not self.operadora.nome:
            erros.append("operadora.nome é obrigatório")

        if not self.operadora.url_portal:
            erros.append("operadora.url_portal é obrigatório")

        if not self.processo.id:
            erros.append("processo.id é obrigatório")

        if not self.processo.mes_ano:
            erros.append("processo.mes_ano é obrigatório")

        return erros


@dataclass
class RespostaRPAExterno:
    """Resposta padrão dos RPAs externos"""
    success: bool
    processo_id: str
    execucao_id: Optional[str] = None
    status: Optional[str] = None
    mensagem: Optional[str] = None
    resultado: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    erro: Optional[str] = None
    request_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RespostaRPAExterno':
        """Cria instância a partir de dicionário"""
        return cls(
            success=data.get('success', False),
            processo_id=data.get('processo_id', ''),
            execucao_id=data.get('execucao_id'),
            status=data.get('status'),
            mensagem=data.get('mensagem'),
            resultado=data.get('resultado'),
            timestamp=data.get('timestamp'),
            erro=data.get('erro'),
            request_id=data.get('request_id')
        )


@dataclass
class PayloadSATExterno:
    """Payload para upload no SAT"""
    processo_id: str
    cliente_nome_sat: str
    dados_sat: str
    arquivo_fatura: Dict[str, Any]
    metadados: Dict[str, Any]
    metadata: Metadata = field(default_factory=Metadata)

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "processo_id": self.processo_id,
            "cliente_nome_sat": self.cliente_nome_sat,
            "dados_sat": self.dados_sat,
            "arquivo_fatura": self.arquivo_fatura,
            "metadados": self.metadados,
            "metadata": {
                "timestamp_envio": self.metadata.timestamp_envio,
                "versao_payload": self.metadata.versao_payload,
                "sistema_origem": self.metadata.sistema_origem,
                "request_id": self.metadata.request_id,
                "modo_teste": self.metadata.modo_teste
            }
        }

    def validar(self) -> List[str]:
        """Valida campos obrigatórios"""
        erros = []

        if not self.processo_id:
            erros.append("processo_id é obrigatório")

        if not self.cliente_nome_sat:
            erros.append("cliente_nome_sat é obrigatório")

        if not self.dados_sat:
            erros.append("dados_sat é obrigatório")

        if not self.arquivo_fatura:
            erros.append("arquivo_fatura é obrigatório")

        if not self.metadados:
            erros.append("metadados é obrigatório")

        return erros


@dataclass
class RespostaSATExterno:
    """Resposta do sistema SAT"""
    success: bool
    processo_id: str
    protocolo_sat: Optional[str] = None
    mensagem: Optional[str] = None
    timestamp: Optional[str] = None
    erro: Optional[str] = None
    request_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RespostaSATExterno':
        """Cria instância a partir de dicionário"""
        return cls(
            success=data.get('success', False),
            processo_id=data.get('processo_id', ''),
            protocolo_sat=data.get('protocolo_sat'),
            mensagem=data.get('mensagem'),
            timestamp=data.get('timestamp'),
            erro=data.get('erro'),
            request_id=data.get('request_id')
        )


@dataclass
class PayloadRPAProducao:
    """Payload simplificado para API em produção - Operadoras"""
    login: str
    senha: str
    filtro: str
    cnpj: str

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "login": self.login,
            "senha": self.senha,
            "filtro": self.filtro,
            "cnpj": self.cnpj
        }

    def validar(self) -> List[str]:
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
class PayloadSATProducao:
    """Payload simplificado para API em produção - SAT"""
    login: str
    senha: str
    filtro: str
    cnpj: str
    razao: str
    operadora: str
    nome_filtro: str
    unidade: str
    servico: str
    dados_sat: str
    nome_arquivo: str
    data_vencimento: str

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "login": self.login,
            "senha": self.senha,
            "filtro": self.filtro,
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

    def validar(self) -> List[str]:
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


@dataclass
class RespostaProducao:
    """Resposta padrão da API em produção"""
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RespostaProducao':
        """Cria instância a partir de dicionário"""
        # Mapear campos da API de produção para nosso modelo
        status = data.get('status', '')
        resultado = data.get('resultado')

        # Converter status string para boolean
        success = status.lower() in ['sucesso', 'success', 'ok', 'true']

        # Mapear resultado para data
        data_field = resultado if resultado is not None else data.get('data')

        return cls(
            success=success,
            message=data.get('message') or f"Status: {status}",
            data=data_field,
            error=data.get('error'),
            timestamp=data.get('timestamp')
        )

# Novos modelos para API externa funcional


@dataclass
class JobStatus:
    """Status de um job da API externa"""
    job_id: str
    operadora: str
    status: str  # PENDING, RUNNING, COMPLETED, FAILED
    progress: int = 0  # 0-100%
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'JobStatus':
        """Cria instância a partir da resposta da API externa"""
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


@dataclass
class ExecutionLog:
    """Log de execução de um job"""
    id: Optional[int] = None
    job_id: str = ""
    processo_id: str = ""
    operadora: str = ""
    timestamp: str = ""
    level: str = "INFO"  # INFO, WARNING, ERROR, DEBUG
    message: str = ""
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'processo_id': self.processo_id,
            'operadora': self.operadora,
            'timestamp': self.timestamp,
            'level': self.level,
            'message': self.message,
            'details': self.details
        }


@dataclass
class ResultCache:
    """Cache de resultados da API externa"""
    id: Optional[int] = None
    job_id: str = ""
    processo_id: str = ""
    operadora: str = ""
    result_data: Optional[Dict[str, Any]] = None
    status: str = "PENDING"
    created_at: str = ""
    updated_at: str = ""
    expires_at: str = ""
    access_count: int = 0

    def __post_init__(self):
        if self.result_data is None:
            self.result_data = {}
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.expires_at:
            # Cache expira em 24 horas
            expires = datetime.now() + timedelta(hours=24)
            self.expires_at = expires.isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'processo_id': self.processo_id,
            'operadora': self.operadora,
            'result_data': self.result_data,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'expires_at': self.expires_at,
            'access_count': self.access_count
        }

    def is_expired(self) -> bool:
        """Verifica se o cache expirou"""
        if not self.expires_at:
            return False
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now() > expires

    def touch(self):
        """Atualiza timestamp de acesso"""
        self.updated_at = datetime.now().isoformat()
        self.access_count += 1

# Modelos para payloads da API externa funcional


@dataclass
class AutomacaoPayload:
    """Payload para execução de RPA em operadoras (API externa funcional)"""
    login: str
    senha: str
    filtro: str
    cnpj: str

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "login": self.login,
            "senha": self.senha,
            "filtro": self.filtro,
            "cnpj": self.cnpj
        }

    def validate(self) -> List[str]:
        """Valida o payload e retorna lista de erros"""
        errors = []

        if not self.login:
            errors.append("login é obrigatório")
        if not self.senha:
            errors.append("senha é obrigatória")
        if not self.filtro:
            errors.append("filtro é obrigatório")
        if not self.cnpj:
            errors.append("cnpj é obrigatório")

        return errors


@dataclass
class AutomacaoPayloadSat:
    """Payload para execução de RPA no SAT (API externa funcional)"""
    cnpj: str
    razao: str
    operadora: str
    nome_filtro: str
    unidade: str
    servico: str
    dados_sat: str
    nome_arquivo: str
    data_vencimento: str

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
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

    def validate(self) -> List[str]:
        """Valida o payload e retorna lista de erros"""
        errors = []

        if not self.cnpj:
            errors.append("cnpj é obrigatório")
        if not self.razao:
            errors.append("razao é obrigatória")
        if not self.operadora:
            errors.append("operadora é obrigatória")
        if not self.nome_filtro:
            errors.append("nome_filtro é obrigatório")
        if not self.unidade:
            errors.append("unidade é obrigatória")
        if not self.servico:
            errors.append("servico é obrigatório")
        if not self.dados_sat:
            errors.append("dados_sat é obrigatório")
        if not self.nome_arquivo:
            errors.append("nome_arquivo é obrigatório")
        if not self.data_vencimento:
            errors.append("data_vencimento é obrigatória")

        return errors


@dataclass
class JobResponse:
    """Resposta de criação de job da API externa"""
    job_id: str
    status: str
    message: str
    status_url: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobResponse':
        """Cria instância a partir de dicionário"""
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
