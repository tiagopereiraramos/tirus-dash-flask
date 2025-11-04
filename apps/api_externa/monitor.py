"""
Sistema de monitoramento de jobs da API externa funcional
"""
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .client import APIExternaClient
from .models import JobStatus, ExecutionLog
from .cache import get_cache

logger = logging.getLogger(__name__)


class JobMonitor:
    """Monitor de jobs da API externa"""

    def __init__(self, client: APIExternaClient, max_concurrent: int = 10):
        """
        Inicializa o monitor de jobs

        Args:
            client: Cliente da API externa
            max_concurrent: Número máximo de jobs monitorados simultaneamente
        """
        self.client = client
        self.max_concurrent = max_concurrent
        self.cache = get_cache()

        # Jobs sendo monitorados
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.job_lock = threading.RLock()

        # Thread pool para monitoramento
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)

        # Callbacks para notificações
        self.status_callbacks: List[Callable[[str, JobStatus], None]] = []
        self.completion_callbacks: List[Callable[[str, JobStatus], None]] = []
        self.error_callbacks: List[Callable[[str, str], None]] = []

        # Thread de monitoramento
        self.monitor_thread = None
        self.running = False

        logger.info(
            f"JobMonitor inicializado: max_concurrent={max_concurrent}")

    def start(self):
        """Inicia o monitor de jobs"""
        if self.running:
            logger.warning("JobMonitor já está rodando")
            return

        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_worker, daemon=True)
        self.monitor_thread.start()

        logger.info("JobMonitor iniciado")

    def stop(self):
        """Para o monitor de jobs"""
        if not self.running:
            return

        self.running = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        self.executor.shutdown(wait=True)
        logger.info("JobMonitor parado")

    def add_job(
        self,
        job_id: str,
        processo_id: str = "",
        operadora: str = "",
        max_wait: int = 300,
        poll_interval: int = 5
    ) -> bool:
        """
        Adiciona um job para monitoramento

        Args:
            job_id: ID do job
            processo_id: ID do processo (opcional)
            operadora: Nome da operadora
            max_wait: Tempo máximo de espera em segundos
            poll_interval: Intervalo entre consultas em segundos

        Returns:
            True se adicionado com sucesso, False caso contrário
        """
        with self.job_lock:
            if job_id in self.active_jobs:
                logger.warning(f"Job {job_id} já está sendo monitorado")
                return False

            if len(self.active_jobs) >= self.max_concurrent:
                logger.warning(
                    f"Limite de jobs atingido ({self.max_concurrent})")
                return False

            self.active_jobs[job_id] = {
                'processo_id': processo_id,
                'operadora': operadora,
                'max_wait': max_wait,
                'poll_interval': poll_interval,
                'start_time': datetime.now(),
                'last_check': None,
                'status': 'PENDING'
            }

            logger.info(f"Job {job_id} adicionado para monitoramento")
            return True

    def remove_job(self, job_id: str) -> bool:
        """
        Remove um job do monitoramento

        Args:
            job_id: ID do job

        Returns:
            True se removido, False se não encontrado
        """
        with self.job_lock:
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
                logger.info(f"Job {job_id} removido do monitoramento")
                return True

        return False

    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """
        Obtém status de um job (do cache ou API)

        Args:
            job_id: ID do job

        Returns:
            JobStatus se encontrado, None caso contrário
        """
        # Tentar cache primeiro
        cached_status = self.cache.get(job_id)
        if cached_status:
            return cached_status

        # Se não está no cache, consultar API
        try:
            status = self.client.consultar_status(job_id)
            self.cache.set(job_id, status)
            return status
        except Exception as e:
            logger.error(f"Erro ao consultar status do job {job_id}: {str(e)}")
            return None

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """
        Obtém lista de jobs ativos

        Returns:
            Lista de informações dos jobs ativos
        """
        with self.job_lock:
            return list(self.active_jobs.values())

    def add_status_callback(self, callback: Callable[[str, JobStatus], None]):
        """Adiciona callback para mudanças de status"""
        self.status_callbacks.append(callback)

    def add_completion_callback(self, callback: Callable[[str, JobStatus], None]):
        """Adiciona callback para conclusão de jobs"""
        self.completion_callbacks.append(callback)

    def add_error_callback(self, callback: Callable[[str, str], None]):
        """Adiciona callback para erros"""
        self.error_callbacks.append(callback)

    def _monitor_worker(self):
        """Worker thread para monitoramento de jobs"""
        while self.running:
            try:
                # Obter jobs ativos
                with self.job_lock:
                    active_jobs = list(self.active_jobs.items())

                # Monitorar cada job
                for job_id, job_info in active_jobs:
                    if not self.running:
                        break

                    try:
                        self._monitor_single_job(job_id, job_info)
                    except Exception as e:
                        logger.error(
                            f"Erro ao monitorar job {job_id}: {str(e)}")
                        self._handle_job_error(job_id, str(e))

                # Aguardar antes da próxima iteração
                time.sleep(2)

            except Exception as e:
                logger.error(f"Erro no monitor worker: {str(e)}")
                time.sleep(5)

    def _monitor_single_job(self, job_id: str, job_info: Dict[str, Any]):
        """Monitora um job específico"""
        # Verificar timeout
        start_time = job_info['start_time']
        max_wait = job_info['max_wait']

        if datetime.now() - start_time > timedelta(seconds=max_wait):
            logger.warning(f"Job {job_id} atingiu timeout ({max_wait}s)")
            self._handle_job_timeout(job_id)
            return

        # Consultar status
        status = self.get_job_status(job_id)
        if not status:
            return

        # Atualizar informações do job
        with self.job_lock:
            if job_id in self.active_jobs:
                self.active_jobs[job_id]['last_check'] = datetime.now()
                self.active_jobs[job_id]['status'] = status.status

        # Armazenar no cache
        self.cache.set(job_id, status, job_info.get('processo_id', ''))

        # Notificar mudança de status
        self._notify_status_change(job_id, status)

        # Verificar se concluído
        if status.status in ['COMPLETED', 'FAILED']:
            self._handle_job_completion(job_id, status)

    def _handle_job_completion(self, job_id: str, status: JobStatus):
        """Processa conclusão de um job"""
        logger.info(f"Job {job_id} concluído com status: {status.status}")

        # Remover do monitoramento
        self.remove_job(job_id)

        # Notificar callbacks
        for callback in self.completion_callbacks:
            try:
                callback(job_id, status)
            except Exception as e:
                logger.error(f"Erro no callback de conclusão: {str(e)}")

    def _handle_job_error(self, job_id: str, error: str):
        """Processa erro em um job"""
        logger.error(f"Erro no job {job_id}: {error}")

        # Remover do monitoramento
        self.remove_job(job_id)

        # Notificar callbacks de erro
        for callback in self.error_callbacks:
            try:
                callback(job_id, error)
            except Exception as e:
                logger.error(f"Erro no callback de erro: {str(e)}")

    def _handle_job_timeout(self, job_id: str):
        """Processa timeout de um job"""
        logger.warning(f"Timeout do job {job_id}")

        # Remover do monitoramento
        self.remove_job(job_id)

        # Notificar callbacks de erro
        error_msg = f"Job {job_id} atingiu timeout"
        for callback in self.error_callbacks:
            try:
                callback(job_id, error_msg)
            except Exception as e:
                logger.error(f"Erro no callback de erro: {str(e)}")

    def _notify_status_change(self, job_id: str, status: JobStatus):
        """Notifica mudança de status"""
        for callback in self.status_callbacks:
            try:
                callback(job_id, status)
            except Exception as e:
                logger.error(f"Erro no callback de status: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do monitor

        Returns:
            Dicionário com estatísticas
        """
        with self.job_lock:
            active_count = len(self.active_jobs)

            # Calcular tempo médio de execução
            avg_runtime = 0
            if active_count > 0:
                total_runtime = 0
                for job_info in self.active_jobs.values():
                    runtime = (datetime.now() -
                               job_info['start_time']).total_seconds()
                    total_runtime += runtime
                avg_runtime = total_runtime / active_count

            return {
                'active_jobs': active_count,
                'max_concurrent': self.max_concurrent,
                'avg_runtime_seconds': avg_runtime,
                'status_callbacks': len(self.status_callbacks),
                'completion_callbacks': len(self.completion_callbacks),
                'error_callbacks': len(self.error_callbacks)
            }


class AsyncJobMonitor:
    """Monitor de jobs assíncrono"""

    def __init__(self, client: APIExternaClient):
        """
        Inicializa o monitor assíncrono

        Args:
            client: Cliente da API externa
        """
        self.client = client
        self.cache = get_cache()
        self.running = False
        self.monitor_tasks: Dict[str, asyncio.Task] = {}

        logger.info("AsyncJobMonitor inicializado")

    async def start_monitoring(
        self,
        job_id: str,
        processo_id: str = "",
        max_wait: int = 300,
        poll_interval: int = 5
    ) -> asyncio.Task:
        """
        Inicia monitoramento assíncrono de um job

        Args:
            job_id: ID do job
            processo_id: ID do processo (opcional)
            max_wait: Tempo máximo de espera em segundos
            poll_interval: Intervalo entre consultas em segundos

        Returns:
            Task do monitoramento
        """
        if job_id in self.monitor_tasks:
            logger.warning(f"Job {job_id} já está sendo monitorado")
            return self.monitor_tasks[job_id]

        task = asyncio.create_task(
            self._monitor_job(job_id, processo_id, max_wait, poll_interval)
        )
        self.monitor_tasks[job_id] = task

        logger.info(f"Monitoramento assíncrono iniciado para job {job_id}")
        return task

    async def stop_monitoring(self, job_id: str) -> bool:
        """
        Para monitoramento de um job

        Args:
            job_id: ID do job

        Returns:
            True se parado, False se não encontrado
        """
        if job_id in self.monitor_tasks:
            task = self.monitor_tasks[job_id]
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            del self.monitor_tasks[job_id]
            logger.info(f"Monitoramento parado para job {job_id}")
            return True

        return False

    async def _monitor_job(
        self,
        job_id: str,
        processo_id: str,
        max_wait: int,
        poll_interval: int
    ):
        """Monitora um job de forma assíncrona"""
        start_time = time.time()

        while True:
            try:
                # Verificar timeout
                elapsed = time.time() - start_time
                if elapsed > max_wait:
                    logger.warning(
                        f"Job {job_id} atingiu timeout ({max_wait}s)")
                    break

                # Consultar status
                status = self.client.consultar_status(job_id)

                # Armazenar no cache
                self.cache.set(job_id, status, processo_id)

                logger.info(
                    f"Job {job_id}: {status.status} ({status.progress}%)")

                # Se concluído, parar
                if status.status in ['COMPLETED', 'FAILED']:
                    logger.info(
                        f"Job {job_id} concluído com status: {status.status}")
                    break

                # Aguardar antes da próxima consulta
                await asyncio.sleep(poll_interval)

            except asyncio.CancelledError:
                logger.info(f"Monitoramento cancelado para job {job_id}")
                break
            except Exception as e:
                logger.error(f"Erro ao monitorar job {job_id}: {str(e)}")
                await asyncio.sleep(poll_interval)

    def get_active_tasks(self) -> List[str]:
        """Obtém lista de jobs sendo monitorados"""
        return list(self.monitor_tasks.keys())

    async def stop_all(self):
        """Para todos os monitoramentos"""
        tasks = list(self.monitor_tasks.values())

        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self.monitor_tasks.clear()
        logger.info("Todos os monitoramentos parados")


# Instância global do monitor
_monitor_instance: Optional[JobMonitor] = None


def get_monitor(client: Optional[APIExternaClient] = None) -> JobMonitor:
    """Obtém instância global do monitor"""
    global _monitor_instance

    if _monitor_instance is None:
        if client is None:
            client = APIExternaClient()
        _monitor_instance = JobMonitor(client)

    return _monitor_instance


def start_monitor():
    """Inicia o monitor global"""
    monitor = get_monitor()
    monitor.start()


def stop_monitor():
    """Para o monitor global"""
    global _monitor_instance

    if _monitor_instance:
        _monitor_instance.stop()
        _monitor_instance = None
