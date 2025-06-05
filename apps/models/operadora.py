
"""
Modelo da Operadora de Telecomunicações
"""

from dataclasses import dataclass
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Column, String, Boolean, Text, JSON
from sqlalchemy.orm import relationship, Mapped

from .base import BaseModel

if TYPE_CHECKING:
    from .cliente import Cliente


@dataclass
class ConfiguracaoRPA:
    """
    Configurações específicas do RPA para uma operadora
    """
    classe_rpa: str
    parametros_especiais: Optional[dict] = None
    timeout_padrao: int = 300
    tentativas_maximas: int = 3


class Operadora(BaseModel):
    """
    Modelo da Operadora de Telecomunicações
    
    Representa as operadoras que fornecem serviços de telecomunicações
    e podem ter RPAs integrados para automação de downloads de faturas.
    """
    
    __tablename__ = 'operadoras'
    
    # Campos obrigatórios
    nome = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Nome da operadora (ex: Embratel, Vivo, Oi)"
    )
    
    codigo = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="Código identificador único da operadora (sigla)"
    )
    
    # Status e configurações
    possui_rpa = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Indica se a operadora possui RPA homologado"
    )
    
    status_ativo = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Indica se a operadora está ativa para uso"
    )
    
    # Campos opcionais
    url_portal = Column(
        String(500),
        nullable=True,
        comment="URL de acesso ao portal da operadora"
    )
    
    instrucoes_acesso = Column(
        Text,
        nullable=True,
        comment="Instruções detalhadas para acesso ao portal"
    )
    
    # Configuração do RPA em formato JSON
    configuracao_rpa = Column(
        JSON,
        nullable=True,
        comment="Configurações específicas do RPA (JSON)"
    )
    
    classe_rpa = Column(
        String(100),
        nullable=True,
        comment="Nome da classe Python do RPA"
    )
    
    # Relacionamentos
    clientes: Mapped[List["Cliente"]] = relationship(
        "Cliente",
        back_populates="operadora",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    def __repr__(self) -> str:
        return f"<Operadora(codigo='{self.codigo}', nome='{self.nome}', ativo={self.status_ativo})>"
    
    @property
    def pode_ser_usada(self) -> bool:
        """Verifica se a operadora pode ser utilizada (ativa)"""
        return self.status_ativo
    
    @property
    def tem_rpa_configurado(self) -> bool:
        """Verifica se a operadora tem RPA configurado e pronto"""
        return self.possui_rpa and self.classe_rpa is not None
    
    def get_configuracao_rpa(self) -> Optional[ConfiguracaoRPA]:
        """Retorna a configuração do RPA deserializada"""
        if not self.configuracao_rpa:
            return None
        
        try:
            config_dict = self.configuracao_rpa
            return ConfiguracaoRPA(
                classe_rpa=config_dict.get('classe_rpa', self.classe_rpa),
                parametros_especiais=config_dict.get('parametros_especiais'),
                timeout_padrao=config_dict.get('timeout_padrao', 300),
                tentativas_maximas=config_dict.get('tentativas_maximas', 3)
            )
        except Exception:
            return None
    
    def set_configuracao_rpa(self, config: ConfiguracaoRPA) -> None:
        """Define a configuração do RPA"""
        self.configuracao_rpa = {
            'classe_rpa': config.classe_rpa,
            'parametros_especiais': config.parametros_especiais,
            'timeout_padrao': config.timeout_padrao,
            'tentativas_maximas': config.tentativas_maximas
        }
        self.classe_rpa = config.classe_rpa
