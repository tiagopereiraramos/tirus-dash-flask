"""
Sistema de cache para API externa funcional
"""
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import threading
import time

from .models import JobStatus, ResultCache

logger = logging.getLogger(__name__)


class APICache:
    """Sistema de cache para API externa"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Inicializa o sistema de cache

        Args:
            max_size: Número máximo de itens no cache
            default_ttl: TTL padrão em segundos (1 hora)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, ResultCache] = {}
        self.lock = threading.RLock()

        # Iniciar thread de limpeza
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()

        logger.info(
            f"Cache inicializado: max_size={max_size}, ttl={default_ttl}s")

    def _cleanup_worker(self):
        """Worker thread para limpeza automática do cache"""
        while True:
            try:
                time.sleep(300)  # Limpar a cada 5 minutos
                self.cleanup_expired()
            except Exception as e:
                logger.error(f"Erro no cleanup worker: {str(e)}")

    def _generate_key(self, job_id: str, processo_id: str = "") -> str:
        """Gera chave única para o cache"""
        if processo_id:
            return f"job:{job_id}:processo:{processo_id}"
        return f"job:{job_id}"

    def get(self, job_id: str, processo_id: str = "") -> Optional[JobStatus]:
        """
        Obtém item do cache

        Args:
            job_id: ID do job
            processo_id: ID do processo (opcional)

        Returns:
            JobStatus se encontrado e válido, None caso contrário
        """
        key = self._generate_key(job_id, processo_id)

        with self.lock:
            if key in self.cache:
                cache_item = self.cache[key]

                # Verificar se expirou
                if cache_item.is_expired():
                    logger.debug(f"Cache expirado para {key}")
                    del self.cache[key]
                    return None

                # Atualizar contador de acesso
                cache_item.touch()

                # Converter para JobStatus
                try:
                    return JobStatus.from_api_response(cache_item.result_data)
                except Exception as e:
                    logger.error(
                        f"Erro ao converter cache para JobStatus: {str(e)}")
                    del self.cache[key]
                    return None

        return None

    def set(
        self,
        job_id: str,
        job_status: JobStatus,
        processo_id: str = "",
        ttl: Optional[int] = None
    ) -> None:
        """
        Armazena item no cache

        Args:
            job_id: ID do job
            job_status: Status do job para armazenar
            processo_id: ID do processo (opcional)
            ttl: TTL em segundos (usa default se None)
        """
        key = self._generate_key(job_id, processo_id)

        with self.lock:
            # Verificar se cache está cheio
            if len(self.cache) >= self.max_size:
                self._evict_oldest()

            # Criar item de cache
            cache_item = ResultCache(
                job_id=job_id,
                processo_id=processo_id,
                operadora=job_status.operadora,
                result_data=job_status.to_dict(),
                status=job_status.status
            )

            # Definir TTL personalizado se fornecido
            if ttl:
                expires = datetime.now() + timedelta(seconds=ttl)
                cache_item.expires_at = expires.isoformat()

            self.cache[key] = cache_item
            logger.debug(f"Item armazenado no cache: {key}")

    def delete(self, job_id: str, processo_id: str = "") -> bool:
        """
        Remove item do cache

        Args:
            job_id: ID do job
            processo_id: ID do processo (opcional)

        Returns:
            True se removido, False se não encontrado
        """
        key = self._generate_key(job_id, processo_id)

        with self.lock:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Item removido do cache: {key}")
                return True

        return False

    def exists(self, job_id: str, processo_id: str = "") -> bool:
        """
        Verifica se item existe no cache

        Args:
            job_id: ID do job
            processo_id: ID do processo (opcional)

        Returns:
            True se existe e não expirou, False caso contrário
        """
        return self.get(job_id, processo_id) is not None

    def cleanup_expired(self) -> int:
        """
        Remove itens expirados do cache

        Returns:
            Número de itens removidos
        """
        removed_count = 0

        with self.lock:
            expired_keys = []

            for key, cache_item in self.cache.items():
                if cache_item.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                del self.cache[key]
                removed_count += 1

        if removed_count > 0:
            logger.info(f"Removidos {removed_count} itens expirados do cache")

        return removed_count

    def _evict_oldest(self) -> None:
        """Remove o item mais antigo do cache (LRU)"""
        if not self.cache:
            return

        # Encontrar item com menor access_count
        oldest_key = min(self.cache.keys(),
                         key=lambda k: self.cache[k].access_count)

        del self.cache[oldest_key]
        logger.debug(f"Item removido por LRU: {oldest_key}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do cache

        Returns:
            Dicionário com estatísticas
        """
        with self.lock:
            total_items = len(self.cache)
            expired_items = sum(
                1 for item in self.cache.values() if item.is_expired())

            # Calcular TTL médio
            avg_ttl = 0
            if total_items > 0:
                total_ttl = 0
                for item in self.cache.values():
                    if item.expires_at:
                        expires = datetime.fromisoformat(item.expires_at)
                        ttl = (expires - datetime.now()).total_seconds()
                        total_ttl += max(0, ttl)
                avg_ttl = total_ttl / total_items

            return {
                'total_items': total_items,
                'expired_items': expired_items,
                'max_size': self.max_size,
                'usage_percent': (total_items / self.max_size) * 100,
                'avg_ttl_seconds': avg_ttl,
                'default_ttl_seconds': self.default_ttl
            }

    def clear(self) -> None:
        """Limpa todo o cache"""
        with self.lock:
            self.cache.clear()
            logger.info("Cache limpo completamente")

    def get_by_processo(self, processo_id: str) -> List[JobStatus]:
        """
        Obtém todos os jobs de um processo

        Args:
            processo_id: ID do processo

        Returns:
            Lista de JobStatus
        """
        result = []

        with self.lock:
            for key, cache_item in self.cache.items():
                if cache_item.processo_id == processo_id and not cache_item.is_expired():
                    try:
                        job_status = JobStatus.from_api_response(
                            cache_item.result_data)
                        result.append(job_status)
                    except Exception as e:
                        logger.error(
                            f"Erro ao converter cache para JobStatus: {str(e)}")

        return result

    def get_recent_jobs(self, limit: int = 50) -> List[JobStatus]:
        """
        Obtém jobs mais recentes

        Args:
            limit: Número máximo de jobs

        Returns:
            Lista de JobStatus ordenados por data de criação
        """
        result = []

        with self.lock:
            # Filtrar itens válidos
            valid_items = [
                (key, item) for key, item in self.cache.items()
                if not item.is_expired()
            ]

            # Ordenar por data de criação (mais recente primeiro)
            sorted_items = sorted(
                valid_items,
                key=lambda x: x[1].created_at,
                reverse=True
            )

            # Limitar resultados
            for key, cache_item in sorted_items[:limit]:
                try:
                    job_status = JobStatus.from_api_response(
                        cache_item.result_data)
                    result.append(job_status)
                except Exception as e:
                    logger.error(
                        f"Erro ao converter cache para JobStatus: {str(e)}")

        return result


# Instância global do cache
_cache_instance: Optional[APICache] = None


def get_cache() -> APICache:
    """Obtém instância global do cache"""
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = APICache()

    return _cache_instance


def clear_cache() -> None:
    """Limpa o cache global"""
    global _cache_instance

    if _cache_instance:
        _cache_instance.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Obtém estatísticas do cache global"""
    cache = get_cache()
    return cache.get_stats()
