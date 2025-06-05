
"""
Modelo do Agendamento
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, Boolean, Text, DateTime, JSON

from .base import BaseModel


class TipoAgendamento(Enum):
    """Tipos de agendamento disponíveis"""
    CRIAR_PROCESSOS_MENSAIS = "CRIAR_PROCESSOS_MENSAIS"
    EXECUTAR_DOWNLOADS = "EXECUTAR_DOWNLOADS"
    ENVIAR_RELATORIOS = "ENVIAR_RELATORIOS"
    LIMPEZA_LOGS = "LIMPEZA_LOGS"
    BACKUP_DADOS = "BACKUP_DADOS"


class Agendamento(BaseModel):
    """
    Modelo do Agendamento
    
    Representa um agendamento de tarefa automatizada
    que é executada periodicamente via cron.
    """
    
    __tablename__ = 'agendamentos'
    
    # Identificação do agendamento
    nome_agendamento = Column(
        String(255),
        nullable=False,
        unique=True,
        comment="Nome único do agendamento"
    )
    
    descricao = Column(
        Text,
        nullable=True,
        comment="Descrição detalhada do agendamento"
    )
    
    # Configuração do cron
    cron_expressao = Column(
        String(100),
        nullable=False,
        comment="Expressão cron para agendamento (formato: min hora dia mês dia_semana)"
    )
    
    # Tipo e status
    tipo_agendamento = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Tipo do agendamento"
    )
    
    status_ativo = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Indica se o agendamento está ativo"
    )
    
    # Controle de execução
    proxima_execucao = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Data e hora da próxima execução"
    )
    
    ultima_execucao = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data e hora da última execução"
    )
    
    # Parâmetros específicos (JSON)
    parametros_execucao = Column(
        JSON,
        nullable=True,
        comment="Parâmetros específicos para execução (JSON)"
    )
    
    def __repr__(self) -> str:
        return f"<Agendamento(nome='{self.nome_agendamento}', tipo='{self.tipo_agendamento}', ativo={self.status_ativo})>"
    
    @property
    def esta_ativo(self) -> bool:
        """Verifica se o agendamento está ativo"""
        return self.status_ativo
    
    @property
    def deve_executar_agora(self) -> bool:
        """Verifica se o agendamento deve ser executado agora"""
        if not self.status_ativo or not self.proxima_execucao:
            return False
        
        return datetime.now() >= self.proxima_execucao
    
    @property
    def foi_executado_recentemente(self) -> bool:
        """Verifica se foi executado nas últimas 24 horas"""
        if not self.ultima_execucao:
            return False
        
        delta = datetime.now() - self.ultima_execucao
        return delta.total_seconds() < 86400  # 24 horas
    
    def ativar(self) -> None:
        """Ativa o agendamento"""
        self.status_ativo = True
    
    def desativar(self) -> None:
        """Desativa o agendamento"""
        self.status_ativo = False
    
    def marcar_execucao(self, proxima_execucao: Optional[datetime] = None) -> None:
        """
        Marca que o agendamento foi executado
        
        Args:
            proxima_execucao: Data/hora da próxima execução (opcional)
        """
        self.ultima_execucao = datetime.now()
        if proxima_execucao:
            self.proxima_execucao = proxima_execucao
    
    def definir_proxima_execucao(self, proxima: datetime) -> None:
        """
        Define a próxima execução
        
        Args:
            proxima: Data/hora da próxima execução
        """
        self.proxima_execucao = proxima
    
    def get_parametros(self) -> Dict[str, Any]:
        """Retorna os parâmetros de execução"""
        return self.parametros_execucao or {}
    
    def set_parametros(self, parametros: Dict[str, Any]) -> None:
        """
        Define os parâmetros de execução
        
        Args:
            parametros: Dicionário com parâmetros
        """
        self.parametros_execucao = parametros
    
    def validar_cron_expressao(self) -> bool:
        """
        Valida se a expressão cron está no formato correto
        
        Returns:
            True se a expressão estiver válida
        """
        try:
            partes = self.cron_expressao.strip().split()
            
            # Deve ter exatamente 5 partes: min hora dia mês dia_semana
            if len(partes) != 5:
                return False
            
            # Validação básica dos valores
            minuto, hora, dia, mes, dia_semana = partes
            
            # Validações simples (aceita * e números)
            def validar_campo(valor: str, min_val: int, max_val: int) -> bool:
                if valor == '*':
                    return True
                
                try:
                    num = int(valor)
                    return min_val <= num <= max_val
                except ValueError:
                    # Pode ser uma expressão mais complexa (*/5, 1-5, etc.)
                    return True
            
            return (
                validar_campo(minuto, 0, 59) and
                validar_campo(hora, 0, 23) and
                validar_campo(dia, 1, 31) and
                validar_campo(mes, 1, 12) and
                validar_campo(dia_semana, 0, 7)
            )
            
        except Exception:
            return False
    
    @classmethod
    def criar_agendamento_processos_mensais(cls) -> "Agendamento":
        """
        Cria agendamento para criação automática de processos mensais
        Executa todo dia 1º às 06:00
        """
        return cls(
            nome_agendamento="Criar Processos Mensais",
            descricao="Cria automaticamente os processos mensais para todos os clientes ativos",
            cron_expressao="0 6 1 * *",  # Todo dia 1º às 06:00
            tipo_agendamento=TipoAgendamento.CRIAR_PROCESSOS_MENSAIS.value,
            parametros_execucao={}
        )
    
    @classmethod
    def criar_agendamento_downloads(cls) -> "Agendamento":
        """
        Cria agendamento para execução de downloads
        Executa de segunda a sexta às 08:00
        """
        return cls(
            nome_agendamento="Executar Downloads Automáticos",
            descricao="Executa downloads automáticos de faturas via RPA",
            cron_expressao="0 8 * * 1-5",  # Segunda a sexta às 08:00
            tipo_agendamento=TipoAgendamento.EXECUTAR_DOWNLOADS.value,
            parametros_execucao={
                "apenas_processos_pendentes": True,
                "limite_execucoes_simultaneas": 5
            }
        )
    
    @classmethod
    def criar_agendamento_relatorios(cls) -> "Agendamento":
        """
        Cria agendamento para envio de relatórios
        Executa toda sexta-feira às 17:00
        """
        return cls(
            nome_agendamento="Envio de Relatórios Semanais",
            descricao="Envia relatórios semanais por email para administradores",
            cron_expressao="0 17 * * 5",  # Toda sexta às 17:00
            tipo_agendamento=TipoAgendamento.ENVIAR_RELATORIOS.value,
            parametros_execucao={
                "tipo_relatorio": "semanal",
                "incluir_graficos": True
            }
        )
