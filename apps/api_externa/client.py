"""
Cliente HTTP para comunicação com API externa funcional
"""
import requests
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
import time
import json

from .models import (
    AutomacaoPayload,
    AutomacaoPayloadSat,
    JobStatus,
    JobResponse
)

logger = logging.getLogger(__name__)


class APIExternaClient:
    """Cliente HTTP para API externa funcional"""

    def __init__(self, base_url: str = "http://191.252.218.230:8000", timeout: int = 90):
        """
        Inicializa o cliente HTTP

        Args:
            base_url: URL base da API externa
            timeout: Timeout em segundos para requisições
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

        # Configurar headers padrão
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'BRM-RPA-Dashboard/1.0'
        })

        # Configurar retry
        self.max_retries = 3
        self.retry_delay = 2  # segundos

        # Importar módulo de autenticação
        from .auth import get_auth
        self.auth = get_auth()

        logger.info(f"Cliente API externa inicializado: {base_url}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        use_auth: bool = True
    ) -> requests.Response:
        """
        Faz uma requisição HTTP com retry automático

        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint da API
            data: Dados para enviar (JSON)
            params: Parâmetros de query
            retry_count: Contador de tentativas

        Returns:
            Response da requisição

        Raises:
            requests.RequestException: Se a requisição falhar após todas as tentativas
        """
        url = f"{self.base_url}{endpoint}"

        try:
            logger.debug(f"Fazendo requisição {method} para {url}")

            # Obter headers com autenticação se necessário
            headers = {}
            if use_auth and hasattr(self, 'auth'):
                headers = self.auth.get_headers()

            # Fazer a requisição
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=self.timeout
            )

            # Log da resposta
            logger.debug(f"Resposta {response.status_code} de {url}")

            # Se sucesso, retorna a resposta
            if response.status_code < 400:
                return response

            # Se erro 4xx, não tenta novamente
            if 400 <= response.status_code < 500:
                logger.warning(
                    f"Erro {response.status_code} de {url}: {response.text}")
                return response

            # Se erro 5xx, tenta novamente
            if response.status_code >= 500:
                raise requests.RequestException(
                    f"Erro {response.status_code}: {response.text}")
            
            # Fallback para outros códigos de status
            return response

        except (requests.RequestException, requests.Timeout) as e:
            logger.warning(f"Erro na requisição {method} {url}: {str(e)}")

            # Se ainda há tentativas, tenta novamente
            if retry_count < self.max_retries:
                logger.info(
                    f"Tentativa {retry_count + 1}/{self.max_retries + 1}")
                # Backoff exponencial
                time.sleep(self.retry_delay * (retry_count + 1))
                return self._make_request(method, endpoint, data, params, retry_count + 1)

            # Se esgotou as tentativas, levanta exceção
            raise requests.RequestException(
                f"Falha após {self.max_retries + 1} tentativas: {str(e)}")

    def health_check(self) -> bool:
        """
        Verifica se a API externa está funcionando

        Returns:
            True se a API está funcionando, False caso contrário
        """
        try:
            response = self._make_request('GET', '/health')
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erro no health check: {str(e)}")
            return False

    def executar_operadora(
        self,
        operadora: str,
        payload: AutomacaoPayload,
        sincrono: bool = False
    ) -> Union[JobResponse, Dict[str, Any]]:
        """
        Executa RPA para uma operadora

        Args:
            operadora: Nome da operadora (OI, VIVO, EMBRATEL, DIGITALNET)
            payload: Payload com dados de autenticação
            sincrono: Se True, executa de forma síncrona

        Returns:
            JobResponse se assíncrono, resultado direto se síncrono

        Raises:
            ValueError: Se payload for inválido
            requests.RequestException: Se a requisição falhar
        """
        # Validar payload
        errors = payload.validate()
        if errors:
            raise ValueError(f"Payload inválido: {', '.join(errors)}")

        # Validar operadora
        operadoras_validas = ['OI', 'VIVO', 'EMBRATEL', 'DIGITALNET']
        if operadora.upper() not in operadoras_validas:
            raise ValueError(
                f"Operadora inválida: {operadora}. Válidas: {operadoras_validas}")

        # Determinar endpoint
        endpoint = f"/executar/{operadora.upper()}"
        if sincrono:
            endpoint += "/sync"

        try:
            response = self._make_request('POST', endpoint, payload.to_dict())

            if response.status_code == 200:
                data = response.json()

                if sincrono:
                    # Execução síncrona retorna resultado direto
                    return data
                else:
                    # Execução assíncrona retorna JobResponse
                    return JobResponse.from_dict(data)
            else:
                logger.error(
                    f"Erro {response.status_code} ao executar {operadora}: {response.text}")
                response.raise_for_status()
                raise ValueError(f"Erro HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"Erro ao executar operadora {operadora}: {str(e)}")
            raise

    def executar_sat(
        self,
        payload: AutomacaoPayloadSat,
        sincrono: bool = False
    ) -> Union[JobResponse, Dict[str, Any]]:
        """
        Executa RPA para SAT

        Args:
            payload: Payload com dados do SAT
            sincrono: Se True, executa de forma síncrona

        Returns:
            JobResponse se assíncrono, resultado direto se síncrono

        Raises:
            ValueError: Se payload for inválido
            requests.RequestException: Se a requisição falhar
        """
        # Validar payload
        errors = payload.validate()
        if errors:
            raise ValueError(f"Payload SAT inválido: {', '.join(errors)}")

        # Determinar endpoint
        endpoint = "/executar/sat"
        if sincrono:
            endpoint += "/sync"

        try:
            import json
            payload_dict = payload.to_dict()
            logger.info(f"🔍 DEBUG - Payload SAT enviado para {endpoint}:")
            logger.info(f"🔍 {json.dumps(payload_dict, indent=2, ensure_ascii=False)}")
            response = self._make_request('POST', endpoint, payload_dict)

            if response.status_code == 200:
                data = response.json()

                if sincrono:
                    # Execução síncrona retorna resultado direto
                    return data
                else:
                    # Execução assíncrona retorna JobResponse
                    return JobResponse.from_dict(data)
            else:
                logger.error(
                    f"Erro {response.status_code} ao executar SAT: {response.text}")
                response.raise_for_status()
                raise ValueError(f"Erro HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"Erro ao executar SAT: {str(e)}")
            raise

    def consultar_status(self, job_id: str) -> JobStatus:
        """
        Consulta o status de um job

        Args:
            job_id: ID do job para consultar

        Returns:
            JobStatus com informações do job

        Raises:
            requests.RequestException: Se a requisição falhar
        """
        try:
            response = self._make_request('GET', f"/status/{job_id}")

            if response.status_code == 200:
                data = response.json()
                return JobStatus.from_api_response(data)
            elif response.status_code == 404:
                raise ValueError(f"Job {job_id} não encontrado")
            else:
                logger.error(
                    f"Erro {response.status_code} ao consultar status: {response.text}")
                response.raise_for_status()
                raise ValueError(f"Erro HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"Erro ao consultar status do job {job_id}: {str(e)}")
            raise

    def listar_jobs(self, limit: int = 100) -> list:
        """
        Lista jobs recentes

        Args:
            limit: Número máximo de jobs para retornar

        Returns:
            Lista de jobs

        Raises:
            requests.RequestException: Se a requisição falhar
        """
        try:
            response = self._make_request(
                'GET', '/jobs', params={'limit': limit})

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"Erro {response.status_code} ao listar jobs: {response.text}")
                response.raise_for_status()
                raise ValueError(f"Erro HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"Erro ao listar jobs: {str(e)}")
            raise

    def monitorar_job(
        self,
        job_id: str,
        max_wait: int = 300,  # 5 minutos
        poll_interval: int = 5  # 5 segundos
    ) -> JobStatus:
        """
        Monitora um job até conclusão ou timeout

        Args:
            job_id: ID do job para monitorar
            max_wait: Tempo máximo de espera em segundos
            poll_interval: Intervalo entre consultas em segundos

        Returns:
            JobStatus final do job

        Raises:
            TimeoutError: Se o job não concluir no tempo limite
            requests.RequestException: Se a requisição falhar
        """
        start_time = time.time()

        while True:
            # Verificar timeout
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise TimeoutError(
                    f"Job {job_id} não concluiu em {max_wait} segundos")

            # Consultar status
            status = self.consultar_status(job_id)

            logger.info(f"Job {job_id}: {status.status} ({status.progress}%)")

            # Se concluído, retorna
            if status.status in ['COMPLETED', 'FAILED']:
                return status

            # Aguardar antes da próxima consulta
            time.sleep(poll_interval)

    def cancelar_job(self, job_id: str) -> bool:
        """
        Cancela um job em execução

        Args:
            job_id: ID do job para cancelar

        Returns:
            True se cancelado com sucesso, False caso contrário
        """
        try:
            response = self._make_request('DELETE', f"/jobs/{job_id}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erro ao cancelar job {job_id}: {str(e)}")
            return False

    def obter_logs(self, job_id: str) -> list:
        """
        Obtém logs detalhados de um job

        Args:
            job_id: ID do job

        Returns:
            Lista de logs

        Raises:
            requests.RequestException: Se a requisição falhar
        """
        try:
            response = self._make_request('GET', f"/jobs/{job_id}/logs")

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"Erro {response.status_code} ao obter logs: {response.text}")
                response.raise_for_status()
                raise ValueError(f"Erro HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"Erro ao obter logs do job {job_id}: {str(e)}")
            raise

    def obter_logs_tempo_real(self, job_id: Optional[str] = None) -> requests.Response:
        """
        Obtém logs em tempo real via Server-Sent Events

        Args:
            job_id: ID do job específico (opcional, se não fornecido retorna todos)

        Returns:
            Response com stream de eventos

        Raises:
            requests.RequestException: Se a requisição falhar
        """
        try:
            endpoint = "/events/logs"
            params = {}
            if job_id:
                params['job_id'] = job_id

            response = self._make_request(
                'GET', endpoint, params=params, use_auth=True)

            if response.status_code == 200:
                logger.info(f"Conectado ao stream de logs em tempo real")
                return response
            else:
                logger.error(
                    f"Erro {response.status_code} ao conectar ao stream de logs: {response.text}")
                response.raise_for_status()
                raise ValueError(f"Erro HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"Erro ao conectar ao stream de logs: {str(e)}")
            raise

    def obter_status_tempo_real(self, job_id: Optional[str] = None) -> requests.Response:
        """
        Obtém status em tempo real via Server-Sent Events

        Args:
            job_id: ID do job específico (opcional, se não fornecido retorna todos)

        Returns:
            Response com stream de eventos

        Raises:
            requests.RequestException: Se a requisição falhar
        """
        try:
            endpoint = "/events/status"
            params = {}
            if job_id:
                params['job_id'] = job_id

            response = self._make_request(
                'GET', endpoint, params=params, use_auth=True)

            if response.status_code == 200:
                logger.info(f"Conectado ao stream de status em tempo real")
                return response
            else:
                logger.error(
                    f"Erro {response.status_code} ao conectar ao stream de status: {response.text}")
                response.raise_for_status()
                raise ValueError(f"Erro HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"Erro ao conectar ao stream de status: {str(e)}")
            raise

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.session.close()
        logger.debug("Sessão HTTP fechada")
