"""
Serviço de monitoramento em tempo real para API externa
"""
import logging
import json
import threading
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import queue

from .client import APIExternaClient
from .models import JobStatus, ExecutionLog

logger = logging.getLogger(__name__)


class MonitorTempoReal:
    """Monitor de tempo real para jobs da API externa"""

    def __init__(self, client: APIExternaClient):
        """
        Inicializa o monitor

        Args:
            client: Cliente da API externa
        """
        self.client = client
        self.monitors = {}  # job_id -> thread
        self.callbacks = {}  # job_id -> lista de callbacks
        self.running = False
        self.lock = threading.Lock()

        logger.info("Monitor de tempo real inicializado")

    def adicionar_callback(self, job_id: str, callback: Callable[[JobStatus], None]):
        """
        Adiciona callback para um job específico

        Args:
            job_id: ID do job
            callback: Função a ser chamada quando houver atualização
        """
        with self.lock:
            if job_id not in self.callbacks:
                self.callbacks[job_id] = []
            self.callbacks[job_id].append(callback)

        logger.debug(f"Callback adicionado para job {job_id}")

    def remover_callback(self, job_id: str, callback: Callable[[JobStatus], None]):
        """
        Remove callback de um job

        Args:
            job_id: ID do job
            callback: Função a ser removida
        """
        with self.lock:
            if job_id in self.callbacks:
                try:
                    self.callbacks[job_id].remove(callback)
                    if not self.callbacks[job_id]:
                        del self.callbacks[job_id]
                except ValueError:
                    pass

        logger.debug(f"Callback removido para job {job_id}")

    def iniciar_monitoramento(self, job_id: str):
        """
        Inicia monitoramento em tempo real para um job

        Args:
            job_id: ID do job para monitorar
        """
        with self.lock:
            if job_id in self.monitors:
                logger.warning(f"Monitoramento já ativo para job {job_id}")
                return

            # Criar thread para monitoramento
            thread = threading.Thread(
                target=self._monitorar_job,
                args=(job_id,),
                daemon=True,
                name=f"Monitor-{job_id}"
            )

            self.monitors[job_id] = thread
            thread.start()

        logger.info(f"Monitoramento iniciado para job {job_id}")

    def parar_monitoramento(self, job_id: str):
        """
        Para monitoramento de um job

        Args:
            job_id: ID do job
        """
        with self.lock:
            if job_id in self.monitors:
                # Marcar para parar
                self.running = False

                # Aguardar thread terminar
                thread = self.monitors[job_id]
                if thread.is_alive():
                    thread.join(timeout=5)

                del self.monitors[job_id]

        logger.info(f"Monitoramento parado para job {job_id}")

    def _monitorar_job(self, job_id: str):
        """
        Loop de monitoramento para um job específico

        Args:
            job_id: ID do job
        """
        logger.info(f"Iniciando monitoramento do job {job_id}")

        try:
            # Conectar ao stream de eventos
            response = self.client.obter_status_tempo_real(job_id)

            # Processar stream de eventos
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                # Processar evento SSE
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])  # Remove 'data: '
                        self._processar_evento(job_id, data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Erro ao decodificar evento: {e}")
                        continue

        except Exception as e:
            logger.error(f"Erro no monitoramento do job {job_id}: {e}")

            # Fallback para polling tradicional
            self._monitorar_job_polling(job_id)

    def _monitorar_job_polling(self, job_id: str):
        """
        Monitoramento por polling (fallback)

        Args:
            job_id: ID do job
        """
        logger.info(f"Iniciando monitoramento por polling para job {job_id}")

        ultimo_status = None
        ultimo_progresso = None

        while self.running:
            try:
                # Consultar status
                status = self.client.consultar_status(job_id)

                # Verificar se houve mudança
                if (status.status != ultimo_status or
                        status.progress != ultimo_progresso):

                    self._processar_evento(job_id, status.to_dict())
                    ultimo_status = status.status
                    ultimo_progresso = status.progress

                # Se job concluído, parar monitoramento
                if status.status in ['COMPLETED', 'FAILED', 'CANCELLED']:
                    logger.info(
                        f"Job {job_id} concluído com status {status.status}")
                    break

                # Aguardar antes da próxima consulta
                time.sleep(2)

            except Exception as e:
                logger.error(f"Erro no polling do job {job_id}: {e}")
                time.sleep(5)

        # Remover do monitoramento
        with self.lock:
            if job_id in self.monitors:
                del self.monitors[job_id]

    def _processar_evento(self, job_id: str, data: Dict[str, Any]):
        """
        Processa evento recebido

        Args:
            job_id: ID do job
            data: Dados do evento
        """
        try:
            # Converter para JobStatus
            if isinstance(data, dict):
                status = JobStatus.from_api_response(data)
            else:
                status = data

            # Chamar callbacks
            with self.lock:
                if job_id in self.callbacks:
                    for callback in self.callbacks[job_id]:
                        try:
                            callback(status)
                        except Exception as e:
                            logger.error(
                                f"Erro em callback para job {job_id}: {e}")

            logger.debug(
                f"Evento processado para job {job_id}: {status.status}")

        except Exception as e:
            logger.error(f"Erro ao processar evento para job {job_id}: {e}")

    def obter_jobs_monitorados(self) -> List[str]:
        """
        Retorna lista de jobs sendo monitorados

        Returns:
            Lista de IDs de jobs
        """
        with self.lock:
            return list(self.monitors.keys())

    def parar_todos(self):
        """Para todos os monitoramentos"""
        with self.lock:
            for job_id in list(self.monitors.keys()):
                self.parar_monitoramento(job_id)

        logger.info("Todos os monitoramentos parados")


# Instância global do monitor
_monitor_instance = None


def get_monitor_tempo_real(client: APIExternaClient = None) -> MonitorTempoReal:
    """
    Obtém instância global do monitor de tempo real

    Args:
        client: Cliente da API externa (opcional)

    Returns:
        Instância do monitor
    """
    global _monitor_instance

    if _monitor_instance is None:
        if client is None:
            client = APIExternaClient()
        _monitor_instance = MonitorTempoReal(client)

    return _monitor_instance

