#!/usr/bin/env python3
"""
Módulo de autenticação para API externa
Gerencia tokens JWT e autenticação com a API externa
"""

import logging
import requests
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from flask import current_app

logger = logging.getLogger(__name__)


class APIExternaAuth:
    """Gerencia autenticação com a API externa"""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        """
        Inicializa o gerenciador de autenticação

        Args:
            base_url: URL base da API externa
            token: Token JWT (opcional, será obtido automaticamente se não fornecido)
        """
        self.base_url = base_url or current_app.config.get(
            'API_EXTERNA_URL', 'http://191.252.218.230:8000')
        self._token = token
        self._token_expires_at = None
        self._session = requests.Session()

        # Configurar headers padrão
        self._session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

        # Verificar se há token configurado na inicialização
        config_token = current_app.config.get('API_EXTERNA_TOKEN')
        if config_token and not self._token:
            logger.info("Token configurado encontrado na inicialização")
            self._token = config_token
            self._token_expires_at = datetime.now() + timedelta(hours=12)

        # Token da API externa (deve ser configurado via variável de ambiente)
        if not config_token:
            logger.warning(
                "⚠️  Token da API externa não configurado! "
                "Configure a variável de ambiente API_EXTERNA_TOKEN"
            )
            self._token = None
            self._token_expires_at = None

    @property
    def token(self) -> Optional[str]:
        """Obtém o token global (usado por todos os usuários)"""
        # 1. Verificar se há token de um admin no banco (token global)
        try:
            from apps.authentication.models import Users
            admin_user = Users.query.filter_by(is_admin=True).filter(
                Users.api_externa_token.isnot(None), 
                Users.api_externa_token != ''
            ).first()
            
            if admin_user and admin_user.api_externa_token:
                logger.info(f"Usando token global do admin: {admin_user.username}")
                return admin_user.api_externa_token.strip()
        except Exception as e:
            logger.debug(f"Não foi possível obter token global do admin: {str(e)}")
        
        # 2. Usar token configurado no .env como fallback
        config_token = current_app.config.get('API_EXTERNA_TOKEN')
        if config_token:
            logger.info("Usando token configurado do .env (fallback)")
            return config_token

        # 3. Usar token interno se disponível
        if self._token:
            logger.info("Usando token interno da API externa")
            return self._token

        # 4. Se não há token configurado, retornar None
        logger.error("Nenhum token configurado encontrado")
        return None

    def get_headers(self) -> Dict[str, str]:
        """Obtém headers com autenticação para requisições"""
        token = self.token
        if token:
            return {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        else:
            return {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

    def test_connection(self) -> Dict[str, Any]:
        """Testa a conexão com a API externa"""
        try:
            headers = self.get_headers()
            response = self._session.get(
                f"{self.base_url}/health", headers=headers)

            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Conexão com API externa estabelecida',
                    'status': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'message': response.text
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Erro ao conectar com API externa'
            }

    def list_jobs(self) -> Dict[str, Any]:
        """Lista todos os jobs ativos na API externa"""
        try:
            headers = self.get_headers()
            response = self._session.get(
                f"{self.base_url}/jobs", headers=headers)

            if response.status_code == 200:
                return {
                    'success': True,
                    'jobs': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'message': response.text
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Erro ao listar jobs'
            }

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Obtém o status de um job específico"""
        try:
            headers = self.get_headers()
            response = self._session.get(
                f"{self.base_url}/status/{job_id}", headers=headers)

            if response.status_code == 200:
                return {
                    'success': True,
                    'status': response.json()
                }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': 'JOB_NOT_FOUND',
                    'message': f'Job {job_id} não encontrado'
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'message': response.text
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Erro ao obter status do job'
            }


# Instância global
_auth_instance: Optional[APIExternaAuth] = None


def get_auth() -> APIExternaAuth:
    """Obtém instância global do gerenciador de autenticação"""
    global _auth_instance

    if _auth_instance is None:
        _auth_instance = APIExternaAuth()

    return _auth_instance


def test_api_externa_connection() -> Dict[str, Any]:
    """Testa a conexão com a API externa"""
    auth = get_auth()
    return auth.test_connection()


def list_api_externa_jobs() -> Dict[str, Any]:
    """Lista jobs da API externa"""
    auth = get_auth()
    return auth.list_jobs()


def get_api_externa_job_status(job_id: str) -> Dict[str, Any]:
    """Obtém status de um job da API externa"""
    auth = get_auth()
    return auth.get_job_status(job_id)
