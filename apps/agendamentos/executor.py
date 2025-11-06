"""
Executor de Agendamentos
Monitora e executa tarefas agendadas periodicamente
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
import threading
import time

from croniter import croniter
from sqlalchemy.exc import SQLAlchemyError

from apps import db
from apps.models import Agendamento, TipoAgendamento, Processo, Cliente, StatusProcesso
from apps.api_externa.services import APIExternaService

logger = logging.getLogger(__name__)


class AgendamentoExecutor:
    """
    Executor responsável por verificar e executar agendamentos
    """
    
    def __init__(self, intervalo_verificacao: int = 60):
        """
        Inicializa o executor de agendamentos
        
        Args:
            intervalo_verificacao: Intervalo em segundos entre verificações (padrão: 60s)
        """
        self.intervalo_verificacao = intervalo_verificacao
        self.executando = False
        self.thread: Optional[threading.Thread] = None
        
        logger.info(f"AgendamentoExecutor inicializado (intervalo: {intervalo_verificacao}s)")
    
    def iniciar(self):
        """Inicia o executor em background"""
        if self.executando:
            logger.warning("Executor já está em execução")
            return
        
        self.executando = True
        self.thread = threading.Thread(target=self._loop_verificacao, daemon=True)
        self.thread.start()
        logger.info("Executor de agendamentos iniciado")
    
    def parar(self):
        """Para o executor"""
        self.executando = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Executor de agendamentos parado")
    
    def _loop_verificacao(self):
        """Loop principal que verifica agendamentos periodicamente"""
        while self.executando:
            try:
                self.verificar_e_executar_agendamentos()
            except Exception as e:
                logger.error(f"Erro no loop de verificação de agendamentos: {e}", exc_info=True)
            
            # Aguardar intervalo antes da próxima verificação
            time.sleep(self.intervalo_verificacao)
    
    def verificar_e_executar_agendamentos(self):
        """
        Verifica agendamentos que devem ser executados e os executa
        """
        try:
            # Buscar agendamentos ativos que devem ser executados agora
            agora = datetime.now()
            
            agendamentos = Agendamento.query.filter(
                Agendamento.status_ativo == True,
                Agendamento.proxima_execucao <= agora
            ).all()
            
            if agendamentos:
                logger.info(f"Encontrados {len(agendamentos)} agendamento(s) para executar")
            
            for agendamento in agendamentos:
                try:
                    self.executar_agendamento(agendamento)
                except Exception as e:
                    logger.error(f"Erro ao executar agendamento {agendamento.nome_agendamento}: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Erro ao verificar agendamentos: {e}", exc_info=True)
    
    def executar_agendamento(self, agendamento: Agendamento):
        """
        Executa um agendamento específico
        
        Args:
            agendamento: Objeto Agendamento a ser executado
        """
        logger.info(f"Executando agendamento: {agendamento.nome_agendamento} (tipo: {agendamento.tipo_agendamento})")
        
        try:
            # Executar baseado no tipo
            if agendamento.tipo_agendamento == TipoAgendamento.CRIAR_PROCESSOS_MENSAIS.value:
                self._executar_criar_processos_mensais(agendamento)
            
            elif agendamento.tipo_agendamento == TipoAgendamento.EXECUTAR_DOWNLOADS.value:
                self._executar_downloads_automaticos(agendamento)
            
            elif agendamento.tipo_agendamento == TipoAgendamento.ENVIAR_RELATORIOS.value:
                self._executar_enviar_relatorios(agendamento)
            
            elif agendamento.tipo_agendamento == TipoAgendamento.LIMPEZA_LOGS.value:
                self._executar_limpeza_logs(agendamento)
            
            elif agendamento.tipo_agendamento == TipoAgendamento.BACKUP_DADOS.value:
                self._executar_backup_dados(agendamento)
            
            else:
                logger.warning(f"Tipo de agendamento desconhecido: {agendamento.tipo_agendamento}")
            
            # Calcular próxima execução usando croniter
            proxima_execucao = self._calcular_proxima_execucao(agendamento.cron_expressao)
            agendamento.marcar_execucao(proxima_execucao)
            
            db.session.commit()
            logger.info(f"Agendamento executado com sucesso. Próxima execução: {proxima_execucao}")
        
        except Exception as e:
            logger.error(f"Erro ao executar agendamento {agendamento.nome_agendamento}: {e}", exc_info=True)
            db.session.rollback()
    
    def _calcular_proxima_execucao(self, cron_expressao: str) -> datetime:
        """
        Calcula a próxima execução baseado na expressão cron
        
        Args:
            cron_expressao: Expressão cron
        
        Returns:
            Datetime da próxima execução
        """
        try:
            cron = croniter(cron_expressao, datetime.now())
            return cron.get_next(datetime)
        except Exception as e:
            logger.error(f"Erro ao calcular próxima execução para cron '{cron_expressao}': {e}")
            # Fallback: próxima execução em 24h
            return datetime.now() + timedelta(days=1)
    
    # ===== EXECUTORES DE TAREFAS ESPECÍFICAS =====
    
    def _executar_criar_processos_mensais(self, agendamento: Agendamento):
        """
        Cria processos mensais para todos os clientes ativos
        """
        logger.info("Iniciando criação de processos mensais")
        
        try:
            from apps.processos.routes import criar_processos_mensais_automatico
            
            resultado = criar_processos_mensais_automatico()
            logger.info(f"Processos mensais criados: {resultado}")
        
        except Exception as e:
            logger.error(f"Erro ao criar processos mensais: {e}", exc_info=True)
            raise
    
    def _executar_downloads_automaticos(self, agendamento: Agendamento):
        """
        Executa downloads automáticos de faturas pendentes
        """
        logger.info("Iniciando execução de downloads automáticos")
        
        try:
            parametros = agendamento.get_parametros()
            apenas_pendentes = parametros.get('apenas_processos_pendentes', True)
            limite_simultaneas = parametros.get('limite_execucoes_simultaneas', 5)
            
            # Buscar processos aguardando download
            query = Processo.query.filter_by(status=StatusProcesso.AGUARDANDO_DOWNLOAD.value)
            
            # Filtrar por operadora se especificado
            if agendamento.operadora_id:
                query = query.join(Cliente).filter(Cliente.operadora_id == agendamento.operadora_id)
            
            processos_pendentes = query.limit(limite_simultaneas).all()
            
            logger.info(f"Encontrados {len(processos_pendentes)} processo(s) pendente(s) para download")
            
            # Executar downloads
            api_service = APIExternaService()
            execucoes_criadas = 0
            
            for processo in processos_pendentes:
                try:
                    # Executar download via API externa
                    operadora = processo.cliente.operadora.nome
                    resultado = api_service.executar_operadora(operadora, processo.id)
                    
                    if resultado.get('success'):
                        execucoes_criadas += 1
                        logger.info(f"Download iniciado para processo {processo.id} (job: {resultado.get('job_id')})")
                    else:
                        logger.warning(f"Falha ao iniciar download para processo {processo.id}: {resultado.get('error')}")
                
                except Exception as e:
                    logger.error(f"Erro ao executar download para processo {processo.id}: {e}")
                    continue
            
            logger.info(f"Downloads automáticos executados: {execucoes_criadas}/{len(processos_pendentes)}")
        
        except Exception as e:
            logger.error(f"Erro ao executar downloads automáticos: {e}", exc_info=True)
            raise
    
    def _executar_enviar_relatorios(self, agendamento: Agendamento):
        """
        Envia relatórios por email
        """
        logger.info("Iniciando envio de relatórios")
        
        try:
            parametros = agendamento.get_parametros()
            tipo_relatorio = parametros.get('tipo_relatorio', 'semanal')
            destinatarios = parametros.get('destinatarios', [])
            
            # TODO: Implementar lógica de geração e envio de relatórios
            logger.warning("Funcionalidade de envio de relatórios ainda não implementada")
        
        except Exception as e:
            logger.error(f"Erro ao enviar relatórios: {e}", exc_info=True)
            raise
    
    def _executar_limpeza_logs(self, agendamento: Agendamento):
        """
        Executa limpeza de logs antigos
        """
        logger.info("Iniciando limpeza de logs")
        
        try:
            # TODO: Implementar lógica de limpeza de logs
            logger.warning("Funcionalidade de limpeza de logs ainda não implementada")
        
        except Exception as e:
            logger.error(f"Erro ao executar limpeza de logs: {e}", exc_info=True)
            raise
    
    def _executar_backup_dados(self, agendamento: Agendamento):
        """
        Executa backup do banco de dados
        """
        logger.info("Iniciando backup de dados")
        
        try:
            # TODO: Implementar lógica de backup
            logger.warning("Funcionalidade de backup ainda não implementada")
        
        except Exception as e:
            logger.error(f"Erro ao executar backup: {e}", exc_info=True)
            raise


# Instância global do executor
_executor_instance: Optional[AgendamentoExecutor] = None


def obter_executor() -> AgendamentoExecutor:
    """
    Retorna a instância global do executor (singleton)
    
    Returns:
        Instância do AgendamentoExecutor
    """
    global _executor_instance
    
    if _executor_instance is None:
        _executor_instance = AgendamentoExecutor()
    
    return _executor_instance


def iniciar_executor():
    """Inicia o executor de agendamentos"""
    executor = obter_executor()
    executor.iniciar()
    logger.info("Executor de agendamentos iniciado via função global")


def parar_executor():
    """Para o executor de agendamentos"""
    executor = obter_executor()
    executor.parar()
    logger.info("Executor de agendamentos parado via função global")
