
"""
Modelo do Usuário
"""

from typing import List, TYPE_CHECKING
from enum import Enum

from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship, Mapped

from .base import BaseModel

if TYPE_CHECKING:
    from .processo import Processo
    from .execucao import Execucao


class PerfilUsuario(Enum):
    """Perfis de usuário do sistema"""
    ADMINISTRADOR = "ADMINISTRADOR"
    APROVADOR = "APROVADOR"
    OPERADOR = "OPERADOR"


class Usuario(BaseModel):
    """
    Modelo do Usuário
    
    Representa os usuários do sistema com diferentes perfis
    de acesso e permissões.
    """
    
    __tablename__ = 'usuarios'
    
    # Dados pessoais
    nome_completo = Column(
        String(255),
        nullable=False,
        comment="Nome completo do usuário"
    )
    
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Email do usuário (usado para login)"
    )
    
    telefone = Column(
        String(20),
        nullable=True,
        comment="Telefone do usuário para notificações"
    )
    
    # Perfil e status
    perfil_usuario = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Perfil do usuário (ADMINISTRADOR, APROVADOR, OPERADOR)"
    )
    
    status_ativo = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Indica se o usuário está ativo no sistema"
    )
    
    # Relacionamentos
    processos_aprovados: Mapped[List["Processo"]] = relationship(
        "Processo",
        foreign_keys="Processo.aprovado_por_usuario_id",
        back_populates="aprovador",
        lazy="dynamic"
    )
    
    execucoes_realizadas: Mapped[List["Execucao"]] = relationship(
        "Execucao",
        foreign_keys="Execucao.executado_por_usuario_id",
        back_populates="executor",
        lazy="dynamic"
    )
    
    def __repr__(self) -> str:
        return f"<Usuario(email='{self.email}', perfil='{self.perfil_usuario}')>"
    
    @property
    def eh_administrador(self) -> bool:
        """Verifica se o usuário é administrador"""
        return self.perfil_usuario == PerfilUsuario.ADMINISTRADOR.value
    
    @property
    def eh_aprovador(self) -> bool:
        """Verifica se o usuário é aprovador"""
        return self.perfil_usuario in [
            PerfilUsuario.ADMINISTRADOR.value,
            PerfilUsuario.APROVADOR.value
        ]
    
    @property
    def eh_operador(self) -> bool:
        """Verifica se o usuário é operador"""
        return self.perfil_usuario in [
            PerfilUsuario.ADMINISTRADOR.value,
            PerfilUsuario.OPERADOR.value
        ]
    
    @property
    def pode_aprovar_processos(self) -> bool:
        """Verifica se o usuário pode aprovar processos"""
        return self.status_ativo and self.eh_aprovador
    
    @property
    def pode_executar_operacoes(self) -> bool:
        """Verifica se o usuário pode executar operações"""
        return self.status_ativo and self.eh_operador
    
    @property
    def pode_administrar_sistema(self) -> bool:
        """Verifica se o usuário pode administrar o sistema"""
        return self.status_ativo and self.eh_administrador
    
    def ativar(self) -> None:
        """Ativa o usuário"""
        self.status_ativo = True
    
    def desativar(self) -> None:
        """Desativa o usuário"""
        self.status_ativo = False
    
    def alterar_perfil(self, novo_perfil: PerfilUsuario) -> None:
        """
        Altera o perfil do usuário
        
        Args:
            novo_perfil: Novo perfil a ser atribuído
        """
        self.perfil_usuario = novo_perfil.value
    
    def get_permissoes(self) -> List[str]:
        """
        Retorna lista de permissões baseada no perfil
        
        Returns:
            Lista de strings com as permissões
        """
        permissoes = []
        
        if self.eh_administrador:
            permissoes.extend([
                'gerenciar_usuarios',
                'gerenciar_operadoras',
                'gerenciar_clientes',
                'aprovar_processos',
                'executar_operacoes',
                'visualizar_relatorios',
                'gerenciar_agendamentos',
                'gerenciar_notificacoes'
            ])
        elif self.eh_aprovador:
            permissoes.extend([
                'aprovar_processos',
                'visualizar_processos',
                'visualizar_relatorios'
            ])
        elif self.eh_operador:
            permissoes.extend([
                'executar_operacoes',
                'visualizar_processos',
                'upload_manual'
            ])
        
        return permissoes
    
    def tem_permissao(self, permissao: str) -> bool:
        """
        Verifica se o usuário tem uma permissão específica
        
        Args:
            permissao: Nome da permissão a verificar
            
        Returns:
            True se o usuário tem a permissão
        """
        return permissao in self.get_permissoes()
