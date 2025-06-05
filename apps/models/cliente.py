
"""
Modelo do Cliente
"""

import hashlib
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Column, String, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped

from .base import BaseModel

if TYPE_CHECKING:
    from .operadora import Operadora
    from .processo import Processo


class Cliente(BaseModel):
    """
    Modelo do Cliente
    
    Representa um cliente que possui faturas de telecomunicações
    para serem processadas automaticamente ou manualmente.
    
    A unicidade é garantida pela combinação: CNPJ + Operadora + Unidade + Serviço
    """
    
    __tablename__ = 'clientes'
    
    # Hash único baseado nos dados do cliente
    hash_unico = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Hash único gerado a partir dos dados do cliente"
    )
    
    # Dados principais do cliente
    razao_social = Column(
        String(255),
        nullable=False,
        comment="Razão social da empresa cliente"
    )
    
    nome_sat = Column(
        String(255),
        nullable=False,
        comment="Nome do cliente no sistema SAT"
    )
    
    cnpj = Column(
        String(20),
        nullable=False,
        index=True,
        comment="CNPJ do cliente (sem formatação)"
    )
    
    # Relacionamento com operadora
    operadora_id = Column(
        UUID(as_uuid=True),
        ForeignKey('operadoras.id', ondelete='RESTRICT'),
        nullable=False,
        index=True,
        comment="ID da operadora associada ao cliente"
    )
    
    # Dados específicos para processamento
    filtro = Column(
        String(255),
        nullable=True,
        comment="Filtro específico para busca de faturas"
    )
    
    servico = Column(
        String(255),
        nullable=False,
        comment="Tipo de serviço contratado"
    )
    
    dados_sat = Column(
        Text,
        nullable=True,
        comment="Dados específicos para integração com SAT"
    )
    
    unidade = Column(
        String(100),
        nullable=False,
        comment="Unidade/filial do cliente"
    )
    
    site_emissao = Column(
        String(255),
        nullable=True,
        comment="Site onde a fatura é emitida"
    )
    
    # Credenciais de acesso ao portal
    login_portal = Column(
        String(100),
        nullable=True,
        comment="Login para acesso ao portal da operadora"
    )
    
    senha_portal = Column(
        String(100),
        nullable=True,
        comment="Senha para acesso ao portal da operadora"
    )
    
    cpf = Column(
        String(20),
        nullable=True,
        comment="CPF adicional quando necessário (sem formatação)"
    )
    
    # Status
    status_ativo = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Indica se o cliente está ativo para processamento"
    )
    
    # Relacionamentos
    operadora: Mapped["Operadora"] = relationship(
        "Operadora",
        back_populates="clientes",
        lazy="joined"
    )
    
    processos: Mapped[List["Processo"]] = relationship(
        "Processo",
        back_populates="cliente",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # Constraints de unicidade
    __table_args__ = (
        UniqueConstraint(
            'cnpj', 'operadora_id', 'unidade', 'servico',
            name='uq_cliente_cnpj_operadora_unidade_servico'
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Cliente(hash='{self.hash_unico}', razao_social='{self.razao_social}')>"
    
    def gerar_hash_unico(self) -> str:
        """
        Gera hash único baseado nos dados-chave do cliente
        
        A hash é gerada a partir de: nome_sat, operadora_codigo, servico, 
        dados_sat, filtro, unidade
        """
        if not hasattr(self, '_operadora_codigo'):
            # Se a operadora não está carregada, busca o código
            if self.operadora:
                operadora_codigo = self.operadora.codigo
            else:
                # Fallback - não deveria acontecer em condições normais
                operadora_codigo = str(self.operadora_id)
        else:
            operadora_codigo = self._operadora_codigo
        
        # Normaliza os dados para hash
        dados_hash = [
            self.nome_sat or '',
            operadora_codigo or '',
            self.servico or '',
            self.dados_sat or '',
            self.filtro or '',
            self.unidade or ''
        ]
        
        # Converte tudo para string, remove espaços e transforma em minúsculo
        dados_normalizados = '|'.join(str(d).strip().lower() for d in dados_hash)
        
        # Gera hash SHA-256 e pega os primeiros 50 caracteres
        hash_obj = hashlib.sha256(dados_normalizados.encode('utf-8'))
        return hash_obj.hexdigest()[:50]
    
    def atualizar_hash(self) -> None:
        """Atualiza a hash única do cliente"""
        self.hash_unico = self.gerar_hash_unico()
    
    @property
    def pode_usar_rpa(self) -> bool:
        """Verifica se o cliente pode usar RPA (operadora tem RPA ativo)"""
        return (
            self.status_ativo and 
            self.operadora and 
            self.operadora.possui_rpa and 
            self.operadora.status_ativo
        )
    
    @property
    def requer_upload_manual(self) -> bool:
        """Verifica se o cliente requer upload manual (operadora sem RPA)"""
        return (
            self.status_ativo and 
            self.operadora and 
            not self.operadora.possui_rpa and 
            self.operadora.status_ativo
        )
    
    @property
    def tem_credenciais_completas(self) -> bool:
        """Verifica se o cliente tem todas as credenciais necessárias"""
        return bool(self.login_portal and self.senha_portal)
    
    def validar_dados_obrigatorios(self) -> List[str]:
        """
        Valida se todos os dados obrigatórios estão preenchidos
        
        Returns:
            Lista de campos obrigatórios que estão em falta
        """
        campos_faltando = []
        
        campos_obrigatorios = [
            ('razao_social', self.razao_social),
            ('nome_sat', self.nome_sat),
            ('cnpj', self.cnpj),
            ('servico', self.servico),
            ('unidade', self.unidade),
            ('operadora_id', self.operadora_id)
        ]
        
        for campo, valor in campos_obrigatorios:
            if not valor or (isinstance(valor, str) and not valor.strip()):
                campos_faltando.append(campo)
        
        # Se a operadora tem RPA, precisa de credenciais
        if self.pode_usar_rpa and not self.tem_credenciais_completas:
            if not self.login_portal:
                campos_faltando.append('login_portal')
            if not self.senha_portal:
                campos_faltando.append('senha_portal')
        
        return campos_faltando
