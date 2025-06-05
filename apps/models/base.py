"""
Modelo base para todos os modelos do sistema
"""

import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
import uuid
from apps import db

class GUID(TypeDecorator):
    """
    Tipo personalizado que funciona tanto com PostgreSQL quanto SQLite
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value

class BaseModel(db.Model):
    __abstract__ = True

    id = Column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )

    data_criacao = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    data_atualizacao = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
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