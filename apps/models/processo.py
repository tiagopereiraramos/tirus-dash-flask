"""
Modelo do Processo Mensal
"""

from dataclasses import dataclass
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from decimal import Decimal

from sqlalchemy import Column, String, Boolean, Text, Date, DateTime, ForeignKey, UniqueConstraint, DECIMAL
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uuid

from .base import BaseModel, GUID

if TYPE_CHECKING:
    from .cliente import Cliente
    from .execucao import Execucao  
    from .usuario import Usuario


class StatusProcesso(Enum):
    """Status possíveis para um processo"""
    AGUARDANDO_DOWNLOAD = "AGUARDANDO_DOWNLOAD"
    DOWNLOAD_COMPLETO = "DOWNLOAD_COMPLETO"
    UPLOAD_SAT_REALIZADO = "UPLOAD_SAT_REALIZADO"
    # Status relacionados às execuções (serão implementados no módulo de execuções)
    DOWNLOAD_EM_ANDAMENTO = "DOWNLOAD_EM_ANDAMENTO"
    DOWNLOAD_FALHOU = "DOWNLOAD_FALHOU"
    AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO"
    APROVADO = "APROVADO"
    REJEITADO = "REJEITADO"
    ENVIANDO_SAT = "ENVIANDO_SAT"
    ENVIADO_SAT = "ENVIADO_SAT"
    FALHA_ENVIO_SAT = "FALHA_ENVIO_SAT"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"


class Processo(BaseModel):
    """
    Modelo do Processo Mensal

    Representa um processo de download e envio de fatura para um cliente
    específico em um determinado mês/ano.

    Unicidade garantida por: Cliente + Mês/Ano
    """

    __tablename__ = 'processos'

    # Relacionamento com cliente
    cliente_id = Column(
        GUID,
        ForeignKey('clientes.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="ID do cliente associado ao processo"
    )

    # Período do processo (formato: MM/AAAA)
    mes_ano = Column(
        String(7),
        nullable=False,
        index=True,
        comment="Mês e ano do processo no formato MM/AAAA"
    )

    # Status do processo
    status_processo = Column(
        String(50),
        nullable=False,
        default=StatusProcesso.AGUARDANDO_DOWNLOAD.value,
        index=True,
        comment="Status atual do processo"
    )

    # Dados da fatura
    url_fatura = Column(
        String(500),
        nullable=True,
        comment="URL da fatura no portal da operadora"
    )

    caminho_s3_fatura = Column(
        String(500),
        nullable=True,
        comment="Caminho da fatura armazenada no S3/MinIO"
    )

    data_vencimento = Column(
        Date,
        nullable=True,
        comment="Data de vencimento da fatura"
    )

    valor_fatura = Column(
        DECIMAL(15, 2),
        nullable=True,
        comment="Valor da fatura"
    )

    # Aprovação
    aprovado_por_usuario_id = Column(
        GUID,
        ForeignKey('usuarios.id', ondelete='SET NULL'),
        nullable=True,
        comment="ID do usuário que aprovou o processo"
    )

    data_aprovacao = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data e hora da aprovação"
    )

    # Envio para SAT
    enviado_para_sat = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica se foi enviado para o SAT"
    )

    data_envio_sat = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data e hora do envio para SAT"
    )

    # Flags de controle
    upload_manual = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica se foi feito upload manual da fatura"
    )

    criado_automaticamente = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica se o processo foi criado automaticamente"
    )

    # Observações
    observacoes = Column(
        Text,
        nullable=True,
        comment="Observações sobre o processo"
    )

    # Relacionamentos
    cliente: Mapped["Cliente"] = relationship(
        "Cliente",
        back_populates="processos",
        lazy="joined"
    )

    aprovador: Mapped[Optional["Usuario"]] = relationship(
        "Usuario",
        foreign_keys=[aprovado_por_usuario_id],
        lazy="select"
    )

    execucoes: Mapped[List["Execucao"]] = relationship(
        "Execucao",
        back_populates="processo",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="Execucao.data_inicio.desc()"
    )

    # Constraints de unicidade
    __table_args__ = (
        UniqueConstraint(
            'cliente_id', 'mes_ano',
            name='uq_processo_cliente_mes_ano'
        ),
    )

    def __repr__(self) -> str:
        return f"<Processo(cliente_id={self.cliente_id}, mes_ano='{self.mes_ano}', status='{self.status_processo}')>"

    @property
    def mes(self) -> int:
        """Retorna o mês do processo"""
        return int(self.mes_ano.split('/')[0])

    @property
    def ano(self) -> int:
        """Retorna o ano do processo"""
        return int(self.mes_ano.split('/')[1])

    @property
    def esta_pendente_aprovacao(self) -> bool:
        """Verifica se o processo está pendente de aprovação"""
        return self.status_processo == StatusProcesso.AGUARDANDO_APROVACAO.value

    @property
    def esta_aprovado(self) -> bool:
        """Verifica se o processo foi aprovado"""
        return self.status_processo == StatusProcesso.APROVADO.value

    @property
    def esta_concluido(self) -> bool:
        """Verifica se o processo foi concluído"""
        return self.status_processo == StatusProcesso.CONCLUIDO.value

    @property
    def pode_ser_aprovado(self) -> bool:
        """Verifica se o processo pode ser aprovado"""
        return (
            self.status_processo == StatusProcesso.DOWNLOAD_COMPLETO.value and
            (self.caminho_s3_fatura is not None or self.upload_manual)
        )
    
    @property
    def pode_enviar_sat(self) -> bool:
        """Verifica se o processo pode ser enviado para o SAT"""
        return self.status_processo == StatusProcesso.APROVADO.value
    
    @property
    def tem_fatura_para_visualizar(self) -> bool:
        """Verifica se há fatura disponível para visualização"""
        return bool(self.caminho_s3_fatura or self.url_fatura)

    @property
    def tem_fatura_disponivel(self) -> bool:
        """Verifica se há fatura disponível"""
        return bool(self.caminho_s3_fatura)

    def aprovar(self, usuario_id: GUID, observacoes: Optional[str] = None) -> None:
        """
        Aprova o processo

        Args:
            usuario_id: ID do usuário que está aprovando
            observacoes: Observações da aprovação
        """
        self.status_processo = StatusProcesso.APROVADO.value
        self.aprovado_por_usuario_id = usuario_id
        self.data_aprovacao = datetime.now()
        if observacoes:
            self.observacoes = observacoes

    def rejeitar(self, observacoes: Optional[str] = None) -> None:
        """
        Rejeita o processo

        Args:
            observacoes: Motivo da rejeição
        """
        self.status_processo = StatusProcesso.REJEITADO.value
        self.aprovado_por_usuario_id = None
        self.data_aprovacao = None
        if observacoes:
            self.observacoes = observacoes

    def marcar_enviado_sat(self) -> None:
        """Marca o processo como enviado para o SAT"""
        self.enviado_para_sat = True
        self.data_envio_sat = datetime.now()
        self.status_processo = StatusProcesso.ENVIADO_SAT.value

    def atualizar_status(self, novo_status: StatusProcesso) -> None:
        """Atualiza o status do processo"""
        self.status_processo = novo_status.value
    
    def enviar_para_sat(self) -> None:
        """Marca o processo como enviado para o SAT"""
        self.status_processo = StatusProcesso.UPLOAD_SAT_REALIZADO.value
        self.enviado_para_sat = True
        self.data_envio_sat = datetime.now()

    @classmethod
    def criar_mes_ano_atual(cls) -> str:
        """Retorna o mês/ano atual no formato MM/AAAA"""
        agora = datetime.now()
        return f"{agora.month:02d}/{agora.year}"

    @classmethod
    def validar_formato_mes_ano(cls, mes_ano: str) -> bool:
        """
        Valida se o formato do mês/ano está correto

        Args:
            mes_ano: String no formato MM/AAAA

        Returns:
            True se o formato estiver correto
        """
        try:
            partes = mes_ano.split('/')
            if len(partes) != 2:
                return False

            mes = int(partes[0])
            ano = int(partes[1])

            return 1 <= mes <= 12 and 2000 <= ano <= 9999
        except (ValueError, IndexError):
            return False