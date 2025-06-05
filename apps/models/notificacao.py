
"""
Modelo da Notificação
"""

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import Column, String, Text, Integer, DateTime

from .base import BaseModel


class TipoNotificacao(Enum):
    """Tipos de notificação disponíveis"""
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    TELEGRAM = "TELEGRAM"
    SLACK = "SLACK"


class StatusEnvio(Enum):
    """Status de envio da notificação"""
    PENDENTE = "PENDENTE"
    ENVIADO = "ENVIADO"
    FALHOU = "FALHOU"
    CANCELADO = "CANCELADO"


class Notificacao(BaseModel):
    """
    Modelo da Notificação
    
    Representa uma notificação a ser enviada ou já enviada
    através de diferentes canais (email, WhatsApp, etc.)
    """
    
    __tablename__ = 'notificacoes'
    
    # Tipo e destinatário
    tipo_notificacao = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Tipo da notificação (EMAIL, WHATSAPP, TELEGRAM, SLACK)"
    )
    
    destinatario = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Destinatário da notificação (email, telefone, etc.)"
    )
    
    # Conteúdo da notificação
    assunto = Column(
        String(255),
        nullable=True,
        comment="Assunto da notificação (usado em emails)"
    )
    
    mensagem = Column(
        Text,
        nullable=False,
        comment="Conteúdo da mensagem"
    )
    
    # Status e controle de envio
    status_envio = Column(
        String(50),
        nullable=False,
        default=StatusEnvio.PENDENTE.value,
        index=True,
        comment="Status do envio da notificação"
    )
    
    tentativas_envio = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Número de tentativas de envio"
    )
    
    data_envio = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data e hora do envio bem-sucedido"
    )
    
    mensagem_erro = Column(
        Text,
        nullable=True,
        comment="Mensagem de erro em caso de falha no envio"
    )
    
    def __repr__(self) -> str:
        return f"<Notificacao(tipo='{self.tipo_notificacao}', destinatario='{self.destinatario}', status='{self.status_envio}')>"
    
    @property
    def foi_enviada(self) -> bool:
        """Verifica se a notificação foi enviada com sucesso"""
        return self.status_envio == StatusEnvio.ENVIADO.value
    
    @property
    def esta_pendente(self) -> bool:
        """Verifica se a notificação está pendente de envio"""
        return self.status_envio == StatusEnvio.PENDENTE.value
    
    @property
    def falhou_envio(self) -> bool:
        """Verifica se o envio da notificação falhou"""
        return self.status_envio == StatusEnvio.FALHOU.value
    
    @property
    def pode_tentar_novamente(self) -> bool:
        """Verifica se pode tentar enviar novamente (limite de 3 tentativas)"""
        return self.tentativas_envio < 3 and self.status_envio != StatusEnvio.CANCELADO.value
    
    def marcar_como_enviada(self) -> None:
        """Marca a notificação como enviada com sucesso"""
        self.status_envio = StatusEnvio.ENVIADO.value
        self.data_envio = datetime.now()
        self.mensagem_erro = None
    
    def marcar_como_falhou(self, erro: str) -> None:
        """
        Marca a notificação como falha no envio
        
        Args:
            erro: Mensagem de erro
        """
        self.tentativas_envio += 1
        self.mensagem_erro = erro
        
        if self.tentativas_envio >= 3:
            self.status_envio = StatusEnvio.FALHOU.value
        else:
            # Mantém como pendente para nova tentativa
            self.status_envio = StatusEnvio.PENDENTE.value
    
    def cancelar(self) -> None:
        """Cancela o envio da notificação"""
        self.status_envio = StatusEnvio.CANCELADO.value
    
    def resetar_para_envio(self) -> None:
        """Reseta a notificação para tentar enviar novamente"""
        self.status_envio = StatusEnvio.PENDENTE.value
        self.tentativas_envio = 0
        self.data_envio = None
        self.mensagem_erro = None
    
    @classmethod
    def criar_notificacao_email(
        cls,
        destinatario: str,
        assunto: str,
        mensagem: str
    ) -> "Notificacao":
        """
        Cria uma notificação de email
        
        Args:
            destinatario: Email do destinatário
            assunto: Assunto do email
            mensagem: Conteúdo do email
            
        Returns:
            Nova instância de Notificacao
        """
        return cls(
            tipo_notificacao=TipoNotificacao.EMAIL.value,
            destinatario=destinatario,
            assunto=assunto,
            mensagem=mensagem
        )
    
    @classmethod
    def criar_notificacao_whatsapp(
        cls,
        telefone: str,
        mensagem: str
    ) -> "Notificacao":
        """
        Cria uma notificação de WhatsApp
        
        Args:
            telefone: Número do telefone
            mensagem: Conteúdo da mensagem
            
        Returns:
            Nova instância de Notificacao
        """
        return cls(
            tipo_notificacao=TipoNotificacao.WHATSAPP.value,
            destinatario=telefone,
            mensagem=mensagem
        )
    
    @classmethod
    def criar_notificacao_telegram(
        cls,
        chat_id: str,
        mensagem: str
    ) -> "Notificacao":
        """
        Cria uma notificação do Telegram
        
        Args:
            chat_id: ID do chat do Telegram
            mensagem: Conteúdo da mensagem
            
        Returns:
            Nova instância de Notificacao
        """
        return cls(
            tipo_notificacao=TipoNotificacao.TELEGRAM.value,
            destinatario=chat_id,
            mensagem=mensagem
        )
