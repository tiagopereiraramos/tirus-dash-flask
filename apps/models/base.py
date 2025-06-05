
"""
Modelo base para todos os modelos do sistema
"""

import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func


class BaseModel(DeclarativeBase):
    """
    Classe base para todos os modelos do sistema.
    
    Fornece campos comuns como ID, timestamps de criação e atualização.
    Utiliza UUID como chave primária padrão.
    """
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Gera automaticamente o nome da tabela baseado no nome da classe"""
        return cls.__name__.lower() + 's'
    
    # Chave primária UUID
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        comment="Identificador único do registro"
    )
    
    # Timestamps automáticos
    data_criacao = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Data e hora de criação do registro"
    )
    
    data_atualizacao = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Data e hora da última atualização do registro"
    )
    
    def __repr__(self) -> str:
        """Representação string do objeto para debug"""
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def to_dict(self) -> dict:
        """Converte o modelo para dicionário para serialização"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                result[column.name] = str(value)
            else:
                result[column.name] = value
        return result
