"""
Módulo de integração com API Externa em Produção
URL: http://191.252.218.230:8000
"""

from .client import APIExternaClient
from .services import APIExternaService
from .auth import APIExternaAuth, get_auth
from .models import (
    AutomacaoPayload,
    AutomacaoPayloadSat,
    JobResponse,
    JobStatus
)

__all__ = [
    'APIExternaClient',
    'APIExternaService',
    'APIExternaAuth',
    'get_auth',
    'AutomacaoPayload',
    'AutomacaoPayloadSat',
    'JobResponse',
    'JobStatus'
]
