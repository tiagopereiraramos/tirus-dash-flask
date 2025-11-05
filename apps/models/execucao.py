"""
Modelo da Execução
"""

from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING
from enum import Enum

from sqlalchemy import Column, String, DateTime, Text, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship, Mapped

from .base import BaseModel, GUID

if TYPE_CHECKING:
    from .processo import Processo
    from .usuario import Usuario


class TipoExecucao(Enum):
    """Tipos de execução possíveis"""
    DOWNLOAD_FATURA = "DOWNLOAD_FATURA"
    UPLOAD_SAT = "UPLOAD_SAT"
    UPLOAD_MANUAL = "UPLOAD_MANUAL"


class StatusExecucao(Enum):
    """Status possíveis de uma execução"""
    EXECUTANDO = "EXECUTANDO"
    CONCLUIDO = "CONCLUIDO"
    FALHOU = "FALHOU"
    TENTANDO_NOVAMENTE = "TENTANDO_NOVAMENTE"
    CANCELADO = "CANCELADO"
    TIMEOUT = "TIMEOUT"


class Execucao(BaseModel):
    """
    Modelo da Execução

    Representa uma execução específica de RPA ou upload manual
    associada a um processo. Cada processo pode ter múltiplas
    execuções (tentativas).
    """

    __tablename__ = 'execucoes'

    # Relacionamento com processo
    processo_id = Column(
        GUID(),
        ForeignKey('processos.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="ID do processo associado à execução"
    )

    # Tipo e status da execução
    tipo_execucao = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Tipo da execução (DOWNLOAD_FATURA, UPLOAD_SAT, UPLOAD_MANUAL)"
    )

    status_execucao = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Status atual da execução"
    )

    # RPA utilizado
    classe_rpa_utilizada = Column(
        String(100),
        nullable=True,
        comment="Nome da classe RPA que foi utilizada"
    )

    # ID do job na API externa (para SSE e rastreamento)
    job_id = Column(
        String(100),
        nullable=True,
        index=True,
        comment="ID do job na API externa para rastreamento via SSE"
    )

    # Dados de entrada e saída (JSON)
    parametros_entrada = Column(
        JSON,
        nullable=True,
        comment="Parâmetros de entrada da execução (JSON)"
    )

    resultado_saida = Column(
        JSON,
        nullable=True,
        comment="Resultado da execução (JSON)"
    )

    # Timestamps de execução
    data_inicio = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.now,
        comment="Data e hora de início da execução"
    )

    data_fim = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data e hora de fim da execução"
    )

    # Logs e arquivos
    mensagem_log = Column(
        Text,
        nullable=True,
        comment="Log detalhado da execução"
    )

    url_arquivo_s3 = Column(
        String(500),
        nullable=True,
        comment="URL do arquivo resultante no S3/MinIO"
    )

    # Controle de tentativas
    numero_tentativa = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Número da tentativa (1, 2, 3...)"
    )

    # Detalhes de erro (JSON)
    detalhes_erro = Column(
        JSON,
        nullable=True,
        comment="Detalhes do erro quando a execução falha (JSON)"
    )

    # Usuário executor (para uploads manuais)
    executado_por_usuario_id = Column(
        GUID(),
        ForeignKey('usuarios.id', ondelete='SET NULL'),
        nullable=True,
        comment="ID do usuário que executou (para operações manuais)"
    )

    # Dados de auditoria
    ip_origem = Column(
        String(45),
        nullable=True,
        comment="IP de origem da execução"
    )

    user_agent = Column(
        Text,
        nullable=True,
        comment="User agent do navegador (para operações via web)"
    )

    # Relacionamentos
    processo: Mapped["Processo"] = relationship(
        "Processo",
        back_populates="execucoes",
        lazy="joined"
    )

    executor: Mapped[Optional["Usuario"]] = relationship(
        "Usuario",
        foreign_keys=[executado_por_usuario_id],
        lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Execucao(processo_id={self.processo_id}, tipo='{self.tipo_execucao}', status='{self.status_execucao}')>"

    @property
    def duracao_segundos(self) -> Optional[float]:
        """Retorna a duração da execução em segundos"""
        if not self.data_fim:
            return None

        delta = self.data_fim - self.data_inicio
        return delta.total_seconds()

    @property
    def esta_em_andamento(self) -> bool:
        """Verifica se a execução está em andamento"""
        return self.status_execucao in [
            StatusExecucao.EXECUTANDO.value,
            StatusExecucao.TENTANDO_NOVAMENTE.value
        ]

    @property
    def foi_bem_sucedida(self) -> bool:
        """Verifica se a execução foi bem-sucedida"""
        return self.status_execucao == StatusExecucao.CONCLUIDO.value

    @property
    def falhou(self) -> bool:
        """Verifica se a execução falhou"""
        return self.status_execucao in [
            StatusExecucao.FALHOU.value,
            StatusExecucao.TIMEOUT.value,
            StatusExecucao.CANCELADO.value
        ]

    def iniciar_execucao(self) -> None:
        """Marca o início da execução"""
        self.status_execucao = StatusExecucao.EXECUTANDO.value
        self.data_inicio = datetime.now()

    def finalizar_com_sucesso(
        self, 
        resultado: Optional[Dict[str, Any]] = None,
        url_arquivo: Optional[str] = None,
        mensagem: Optional[str] = None
    ) -> None:
        """
        Finaliza a execução com sucesso

        Args:
            resultado: Dicionário com resultado da execução
            url_arquivo: URL do arquivo gerado
            mensagem: Mensagem de sucesso
        """
        self.status_execucao = StatusExecucao.CONCLUIDO.value
        self.data_fim = datetime.now()

        if resultado:
            self.resultado_saida = resultado

        if url_arquivo:
            self.url_arquivo_s3 = url_arquivo

        if mensagem:
            self.mensagem_log = mensagem

    def finalizar_com_erro(
        self,
        erro: Exception,
        detalhes_adicionais: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Finaliza a execução com erro

        Args:
            erro: Exceção que causou o erro
            detalhes_adicionais: Detalhes adicionais do erro
        """
        self.status_execucao = StatusExecucao.FALHOU.value
        self.data_fim = datetime.now()
        self.mensagem_log = str(erro)

        # Monta detalhes do erro
        detalhes_erro = {
            'tipo_erro': type(erro).__name__,
            'mensagem': str(erro),
            'timestamp': datetime.now().isoformat()
        }

        if detalhes_adicionais:
            detalhes_erro.update(detalhes_adicionais)

        self.detalhes_erro = detalhes_erro

    def marcar_timeout(self) -> None:
        """Marca a execução como timeout"""
        self.status_execucao = StatusExecucao.TIMEOUT.value
        self.data_fim = datetime.now()
        self.mensagem_log = "Execução cancelada por timeout"

    def cancelar(self, motivo: Optional[str] = None) -> None:
        """
        Cancela a execução

        Args:
            motivo: Motivo do cancelamento
        """
        self.status_execucao = StatusExecucao.CANCELADO.value
        self.data_fim = datetime.now()

        if motivo:
            self.mensagem_log = f"Execução cancelada: {motivo}"
        else:
            self.mensagem_log = "Execução cancelada pelo usuário"

    def adicionar_log(self, mensagem: str) -> None:
        """
        Adiciona uma mensagem ao log da execução

        Args:
            mensagem: Mensagem a ser adicionada
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nova_linha = f"[{timestamp}] {mensagem}"

        if self.mensagem_log:
            self.mensagem_log += f"\n{nova_linha}"
        else:
            self.mensagem_log = nova_linha

    def get_parametros_rpa(self) -> Dict[str, Any]:
        """Retorna os parâmetros de entrada formatados para RPA"""
        if not self.parametros_entrada:
            return {}

        return self.parametros_entrada

    def set_parametros_rpa(self, parametros: Dict[str, Any]) -> None:
        """Define os parâmetros de entrada para RPA"""
        self.parametros_entrada = parametros