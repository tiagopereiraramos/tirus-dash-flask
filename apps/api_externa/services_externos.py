"""
Serviços para integração com API externa funcional
"""
import logging
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timedelta
import uuid

from .client import APIExternaClient
from .models import (
    AutomacaoPayload,
    AutomacaoPayloadSat,
    JobStatus,
    JobResponse,
    ExecutionLog
)
from .cache import get_cache
from .monitor import get_monitor

from apps.models import Processo, Cliente, Operadora, Execucao
from apps import db

logger = logging.getLogger(__name__)


class APIExternaFuncionalService:
    """Serviço para integração com API externa funcional"""

    def __init__(self, base_url: str = "http://191.252.218.230:8000", timeout: int = 90):
        """
        Inicializa o serviço

        Args:
            base_url: URL base da API externa
            timeout: Timeout em segundos para requisições
        """
        self.client = APIExternaClient(base_url=base_url, timeout=timeout)
        self.cache = get_cache()
        self.monitor = get_monitor(self.client)

        # Importar módulo de autenticação
        from .auth import get_auth
        self.auth = get_auth()

        logger.info(f"APIExternaFuncionalService inicializado: {base_url}")

    def criar_payload_operadora(self, processo: Processo) -> AutomacaoPayload:
        """
        Cria payload para execução de operadora

        Args:
            processo: Processo a ser executado

        Returns:
            AutomacaoPayload configurado

        Raises:
            ValueError: Se dados obrigatórios estiverem faltando
        """
        try:
            cliente = processo.cliente
            operadora = cliente.operadora

            # Lógica inteligente para login baseada na operadora
            if cliente.login_portal:
                login = cliente.login_portal
            elif operadora.codigo == 'OI':
                # Para Oi, usar o filtro como login
                login = cliente.filtro or f"{cliente.cnpj}"
            else:
                # Para outras operadoras, usar CNPJ como fallback
                login = f"{cliente.cnpj}"

            # Usar valores padrão se dados estiverem faltando
            senha = cliente.senha_portal or "senha123"
            filtro = cliente.filtro or "fatura_mensal"
            cnpj = cliente.cnpj or "00000000000000"

            payload = AutomacaoPayload(
                login=login,
                senha=senha,
                filtro=filtro,
                cnpj=cnpj
            )

            # Validar payload
            errors = payload.validate()
            if errors:
                raise ValueError(f"Payload inválido: {', '.join(errors)}")

            logger.info(
                f"Payload criado para processo {processo.id}: {operadora.codigo}")
            return payload

        except Exception as e:
            logger.error(
                f"Erro ao criar payload para processo {processo.id}: {str(e)}")
            raise

    def criar_payload_sat(self, processo: Processo) -> AutomacaoPayloadSat:
        """
        Cria payload para execução SAT

        Args:
            processo: Processo a ser executado

        Returns:
            AutomacaoPayloadSat configurado

        Raises:
            ValueError: Se dados obrigatórios estiverem faltando
        """
        try:
            cliente = processo.cliente
            operadora = cliente.operadora

            # Gerar nome de arquivo baseado no processo
            nome_arquivo = f"fatura_{operadora.codigo.lower()}_{processo.mes_ano}.pdf"

            # Data de vencimento (usar data atual + 15 dias se não definida)
            if processo.data_vencimento:
                data_vencimento = processo.data_vencimento
            else:
                data_venc = datetime.now() + timedelta(days=15)
                data_vencimento = data_venc.strftime("%d/%m/%Y")

            # Determinar login e senha (mesma lógica do download)
            if cliente.login_portal:
                login = cliente.login_portal
            elif operadora.codigo == 'OI':
                login = cliente.filtro or cliente.cnpj
            else:
                login = cliente.cnpj
            
            senha = cliente.senha_portal or "senha123"
            filtro = cliente.filtro or "fatura_mensal"
            
            payload = AutomacaoPayloadSat(
                login=login,
                senha=senha,
                filtro=filtro,
                cnpj=cliente.cnpj or "00000000000000",
                razao=cliente.razao_social or "EMPRESA LTDA",
                operadora=operadora.codigo,
                nome_filtro=f"{operadora.codigo} FIXO",
                unidade=cliente.unidade or "MATRIZ",
                servico=cliente.servico or "TELEFONIA",
                dados_sat=cliente.dados_sat or f"{cliente.nome_sat}|INTERNET|DEDICADA",
                nome_arquivo=nome_arquivo,
                data_vencimento=data_vencimento,
                processo_id=str(processo.id)
            )

            # Validar payload
            errors = payload.validate()
            if errors:
                raise ValueError(f"Payload SAT inválido: {', '.join(errors)}")

            logger.info(f"Payload SAT criado para processo {processo.id}")
            return payload

        except Exception as e:
            logger.error(
                f"Erro ao criar payload SAT para processo {processo.id}: {str(e)}")
            raise

    def executar_rpa_externo(
        self,
        processo: Processo,
        sincrono: bool = False
    ) -> Union[JobResponse, Dict[str, Any]]:
        """
        Executa RPA externo para um processo

        Args:
            processo: Processo a ser executado
            sincrono: Se True, executa de forma síncrona

        Returns:
            JobResponse se assíncrono, resultado direto se síncrono

        Raises:
            ValueError: Se processo ou operadora forem inválidos
            Exception: Se execução falhar
        """
        # Importar modelo de execução
        from apps.models.execucao import Execucao, TipoExecucao, StatusExecucao
        from apps.models.usuario import Usuario
        from flask_login import current_user

        # Criar registro de execução
        execucao = Execucao(
            processo_id=processo.id,
            tipo_execucao=TipoExecucao.DOWNLOAD_FATURA.value,
            status_execucao=StatusExecucao.EXECUTANDO.value,
            classe_rpa_utilizada="API_EXTERNA",
            parametros_entrada={
                "operadora": processo.cliente.operadora.codigo,
                "cliente": processo.cliente.razao_social,
                "cnpj": processo.cliente.cnpj,
                "filtro": processo.cliente.filtro,
                "sincrono": sincrono
            },
            numero_tentativa=1,
            ip_origem="127.0.0.1",  # TODO: Obter IP real
            user_agent="API Externa Integration"
        )

        # Associar usuário se logado
        if current_user and not current_user.is_anonymous:
            execucao.executado_por_usuario_id = current_user.id

        # Adicionar execução ao banco
        db.session.add(execucao)
        db.session.commit()

        try:
            # Validar processo
            if not processo:
                raise ValueError("Processo é obrigatório")

            cliente = processo.cliente
            operadora = cliente.operadora

            if not operadora:
                raise ValueError("Processo deve ter uma operadora associada")

            # Verificar se operadora é suportada
            operadoras_suportadas = ['OI', 'VIVO', 'EMBRATEL', 'DIGITALNET']
            if operadora.codigo not in operadoras_suportadas:
                raise ValueError(
                    f"Operadora {operadora.codigo} não é suportada")

            # Criar payload
            payload = self.criar_payload_operadora(processo)

            # Adicionar payload aos parâmetros de entrada
            execucao.parametros_entrada.update(payload.to_dict())
            db.session.commit()

            # Executar na API externa
            logger.info(
                f"Executando RPA para processo {processo.id} - Operadora: {operadora.codigo}")

            # Adicionar log de início
            execucao.adicionar_log(
                f"Iniciando execução RPA para operadora {operadora.codigo}")
            execucao.adicionar_log(f"Payload criado: {payload.to_dict()}")
            db.session.commit()

            resultado = self.client.executar_operadora(
                operadora=operadora.codigo,
                payload=payload,
                sincrono=sincrono
            )

            # Se assíncrono, adicionar ao monitor
            if not sincrono and isinstance(resultado, JobResponse):
                # IMPORTANTE: Armazenar o resultado do job na execução para que possa ser listado
                execucao.resultado_saida = {
                    'job_id': resultado.job_id,
                    'status': resultado.status,
                    'tipo': 'rpa',
                    'operadora': operadora.codigo,
                    'processo_id': str(processo.id),
                    'timestamp_criacao': datetime.now().isoformat(),
                    'assincrono': True
                }

                self.monitor.add_job(
                    job_id=resultado.job_id,
                    processo_id=str(processo.id),
                    operadora=operadora.codigo
                )

                # Armazenar no cache
                job_status = JobStatus(
                    job_id=resultado.job_id,
                    operadora=operadora.codigo,
                    status=resultado.status,
                    progress=0
                )
                self.cache.set(resultado.job_id, job_status, str(processo.id))

                logger.info(
                    f"Job {resultado.job_id} criado e adicionado ao monitor")

                # Para execução assíncrona, NÃO finalizar a execução ainda
                # A execução só será finalizada quando o job for concluído
                # e retornar a URL da fatura
                execucao.adicionar_log(
                    f"Job criado com sucesso: {resultado.job_id}")
                execucao.adicionar_log(f"Status inicial: {resultado.status}")
                execucao.adicionar_log("Aguardando conclusão do job...")
                db.session.commit()

            # Atualizar status do processo
            if sincrono:
                # Para execução síncrona, verificar se a fatura foi baixada
                if hasattr(resultado, 'url_fatura') and resultado.url_fatura:
                    processo.status_processo = "DOWNLOAD_CONCLUIDO"
                    processo.url_fatura = resultado.url_fatura
                    execucao.finalizar_com_sucesso(
                        resultado=resultado.to_dict() if hasattr(resultado, 'to_dict') else resultado,
                        url_arquivo=resultado.url_fatura,
                        mensagem=f"Download concluído com sucesso. URL: {resultado.url_fatura}"
                    )
                else:
                    processo.status_processo = "ERRO_DOWNLOAD"
                    execucao.finalizar_com_erro(
                        erro=Exception("Download não retornou URL da fatura"),
                        detalhes_adicionais={
                            "tipo": "erro_download_sem_url", "resultado": resultado}
                    )
            else:
                processo.status_processo = "DOWNLOAD_EM_ANDAMENTO"

            db.session.commit()

            return resultado

        except ValueError as e:
            # Atualizar execução com erro de validação
            execucao.finalizar_com_erro(
                erro=e,
                detalhes_adicionais={"tipo": "erro_validacao"}
            )
            db.session.commit()

            # Re-raise ValueError sem tentar acessar processo.id
            raise
        except Exception as e:
            logger.error(
                f"Erro ao executar RPA para processo {processo.id if processo else 'None'}: {str(e)}")

            # Atualizar execução com erro
            execucao.finalizar_com_erro(
                erro=e,
                detalhes_adicionais={"tipo": "erro_execucao"}
            )
            db.session.commit()

            # Atualizar status do processo para erro (se processo existir)
            if processo:
                processo.status_processo = "ERRO_DOWNLOAD"
                db.session.commit()

            raise

    def executar_sat_externo(
        self,
        processo: Processo,
        sincrono: bool = False
    ) -> Union[JobResponse, Dict[str, Any]]:
        """
        Executa SAT externo para um processo

        Args:
            processo: Processo a ser executado
            sincrono: Se True, executa de forma síncrona

        Returns:
            JobResponse se assíncrono, resultado direto se síncrono

        Raises:
            ValueError: Se processo for inválido
            Exception: Se execução falhar
        """
        # Importar modelo de execução
        from apps.models.execucao import Execucao, TipoExecucao, StatusExecucao
        from apps.models.usuario import Usuario
        from flask_login import current_user

        # Criar registro de execução
        execucao = Execucao(
            processo_id=processo.id,
            tipo_execucao=TipoExecucao.UPLOAD_SAT.value,
            status_execucao=StatusExecucao.EXECUTANDO.value,
            classe_rpa_utilizada="API_EXTERNA_SAT",
            parametros_entrada={
                "cliente": processo.cliente.razao_social,
                "cnpj": processo.cliente.cnpj,
                "operadora": processo.cliente.operadora.codigo,
                "sincrono": sincrono
            },
            numero_tentativa=1,
            ip_origem="127.0.0.1",  # TODO: Obter IP real
            user_agent="API Externa Integration"
        )

        # Associar usuário se logado
        if current_user and not current_user.is_anonymous:
            execucao.executado_por_usuario_id = current_user.id

        # Adicionar execução ao banco
        db.session.add(execucao)
        db.session.commit()

        try:
            # Validar processo
            if not processo:
                raise ValueError("Processo é obrigatório")

            # Criar payload SAT
            payload = self.criar_payload_sat(processo)

            # Adicionar payload aos parâmetros de entrada
            execucao.parametros_entrada.update(payload.to_dict())
            db.session.commit()

            # Executar na API externa
            logger.info(f"Executando SAT para processo {processo.id}")

            # Adicionar log de início
            execucao.adicionar_log(
                f"Iniciando execução SAT para processo {processo.id}")
            execucao.adicionar_log(f"Payload SAT criado: {payload.to_dict()}")
            db.session.commit()

            resultado = self.client.executar_sat(
                payload=payload,
                sincrono=sincrono
            )

            # Se assíncrono, adicionar ao monitor
            if not sincrono and isinstance(resultado, JobResponse):
                # IMPORTANTE: Armazenar o resultado do job na execução para que possa ser listado
                execucao.resultado_saida = {
                    'job_id': resultado.job_id,
                    'status': resultado.status,
                    'tipo': 'sat',
                    'operadora': 'SAT',
                    'processo_id': str(processo.id),
                    'timestamp_criacao': datetime.now().isoformat(),
                    'assincrono': True
                }

                self.monitor.add_job(
                    job_id=resultado.job_id,
                    processo_id=str(processo.id),
                    operadora="SAT"
                )

                # Armazenar no cache
                job_status = JobStatus(
                    job_id=resultado.job_id,
                    operadora="SAT",
                    status=resultado.status,
                    progress=0
                )
                self.cache.set(resultado.job_id, job_status, str(processo.id))

                logger.info(
                    f"Job SAT {resultado.job_id} criado e adicionado ao monitor")

                # Para execução assíncrona, NÃO finalizar a execução ainda
                # A execução só será finalizada quando o job for concluído
                execucao.adicionar_log(
                    f"Job SAT criado com sucesso: {resultado.job_id}")
                execucao.adicionar_log(f"Status inicial: {resultado.status}")
                execucao.adicionar_log("Aguardando conclusão do job SAT...")
                db.session.commit()

            # Atualizar status do processo
            if sincrono:
                # Para execução síncrona, verificar resultado
                if hasattr(resultado, 'result') and resultado.result:
                    processo.status_processo = "UPLOAD_REALIZADO"
                    execucao.finalizar_com_sucesso(
                        resultado=resultado.to_dict() if hasattr(resultado, 'to_dict') else resultado,
                        mensagem=f"Upload SAT concluído com sucesso"
                    )
                else:
                    processo.status_processo = "ERRO_SAT"
                    execucao.finalizar_com_erro(
                        erro=Exception("Upload SAT não retornou resultado"),
                        detalhes_adicionais={
                            "tipo": "erro_sat_sem_resultado", "resultado": resultado}
                    )
            else:
                processo.status_processo = "SAT_EM_ANDAMENTO"

            db.session.commit()

            return resultado

        except Exception as e:
            logger.error(
                f"Erro ao executar SAT para processo {processo.id}: {str(e)}")

            # Atualizar execução com erro
            execucao.finalizar_com_erro(
                erro=e,
                detalhes_adicionais={"tipo": "erro_sat"}
            )
            db.session.commit()

            # Atualizar status do processo para erro
            processo.status_processo = "ERRO_SAT"
            db.session.commit()

            raise

    def consultar_status_job(self, job_id: str, processo_id: str = "") -> Optional[JobStatus]:
        """
        Consulta status de um job

        Args:
            job_id: ID do job
            processo_id: ID do processo (opcional)

        Returns:
            JobStatus se encontrado, None caso contrário
        """
        try:
            # Tentar cache primeiro
            cached_status = self.cache.get(job_id, processo_id)
            if cached_status:
                return cached_status

            # Consultar API externa
            status = self.client.consultar_status(job_id)

            # Armazenar no cache
            self.cache.set(job_id, status, processo_id)

            return status

        except Exception as e:
            logger.error(f"Erro ao consultar status do job {job_id}: {str(e)}")
            return None

    def processar_resultado_job(self, job_id: str, processo_id: str, resultado: Dict[str, Any]) -> bool:
        """
        Processa o resultado de um job concluído e atualiza o processo

        Args:
            job_id: ID do job
            processo_id: ID do processo
            resultado: Resultado do job

        Returns:
            True se processado com sucesso, False caso contrário
        """
        try:
            from apps.models.processo import Processo
            from apps.models.execucao import Execucao, StatusExecucao

            # Buscar processo
            processo = Processo.query.get(processo_id)
            if not processo:
                logger.error(f"Processo {processo_id} não encontrado")
                return False

            # Buscar execução associada ao job
            execucao = None
            for exec in processo.execucoes:
                if exec.tem_job_associado() and exec.get_job_id() == job_id:
                    execucao = exec
                    break

            if not execucao:
                logger.error(f"Execução não encontrada para job {job_id}")
                return False

            # Verificar se o job foi bem-sucedido
            if resultado.get('status') == 'COMPLETED':
                # Verificar se há URL da fatura no resultado
                url_fatura = resultado.get('url_fatura') or resultado.get(
                    'result', {}).get('url_fatura')

                if url_fatura:
                    # Download bem-sucedido
                    processo.status_processo = "DOWNLOAD_CONCLUIDO"
                    processo.url_fatura = url_fatura

                    execucao.finalizar_com_sucesso(
                        resultado=resultado,
                        url_arquivo=url_fatura,
                        mensagem=f"Download concluído com sucesso via job {job_id}. URL: {url_fatura}"
                    )

                    logger.info(
                        f"Processo {processo_id} atualizado com sucesso. URL: {url_fatura}")
                else:
                    # Job concluído mas sem URL da fatura
                    processo.status_processo = "ERRO_DOWNLOAD"

                    execucao.finalizar_com_erro(
                        erro=Exception(
                            "Job concluído mas não retornou URL da fatura"),
                        detalhes_adicionais={
                            "tipo": "erro_job_sem_url",
                            "job_id": job_id,
                            "resultado": resultado
                        }
                    )

                    logger.error(
                        f"Job {job_id} concluído mas sem URL da fatura")
            else:
                # Job falhou
                processo.status_processo = "ERRO_DOWNLOAD"

                erro_msg = resultado.get('error') or resultado.get(
                    'message') or "Job falhou"
                execucao.finalizar_com_erro(
                    erro=Exception(erro_msg),
                    detalhes_adicionais={
                        "tipo": "erro_job_falhou",
                        "job_id": job_id,
                        "resultado": resultado
                    }
                )

                logger.error(f"Job {job_id} falhou: {erro_msg}")

            db.session.commit()
            return True

        except Exception as e:
            logger.error(
                f"Erro ao processar resultado do job {job_id}: {str(e)}")
            return False

    def monitorar_job(
        self,
        job_id: str,
        processo_id: str = "",
        max_wait: int = 300,
        poll_interval: int = 5
    ) -> Optional[JobStatus]:
        """
        Monitora um job até conclusão

        Args:
            job_id: ID do job
            processo_id: ID do processo (opcional)
            max_wait: Tempo máximo de espera em segundos
            poll_interval: Intervalo entre consultas em segundos

        Returns:
            JobStatus final se concluído, None se timeout
        """
        try:
            logger.info(f"Iniciando monitoramento do job {job_id}")

            status = self.client.monitorar_job(
                job_id=job_id,
                max_wait=max_wait,
                poll_interval=poll_interval
            )

            # Atualizar cache
            self.cache.set(job_id, status, processo_id)

            # Processar resultado se concluído
            if status.status == 'COMPLETED':
                self._processar_resultado_sucesso(job_id, status, processo_id)
            elif status.status == 'FAILED':
                self._processar_resultado_falha(job_id, status, processo_id)

            return status

        except Exception as e:
            logger.error(f"Erro ao monitorar job {job_id}: {str(e)}")
            return None

    def atualizar_status_processo_automatico(self, job_id: str, processo_id: str) -> bool:
        """
        Atualiza automaticamente o status do processo baseado no resultado do job

        Args:
            job_id: ID do job
            processo_id: ID do processo

        Returns:
            bool: True se atualizado com sucesso, False caso contrário
        """
        try:
            logger.info(
                f"Atualizando status do processo {processo_id} automaticamente para job {job_id}")

            # Consultar status do job na API externa
            status = self.client.consultar_status(job_id)
            if not status:
                logger.error(f"Não foi possível obter status do job {job_id}")
                return False

            # Buscar processo e execução
            processo = Processo.query.get(processo_id)
            if not processo:
                logger.error(f"Processo {processo_id} não encontrado")
                return False

            # Buscar execução mais recente (pode ser EXECUTANDO ou já finalizada)
            execucao = processo.execucoes.order_by(
                Execucao.data_inicio.desc()).first()
            if not execucao:
                logger.warning(
                    f"Nenhuma execução encontrada para processo {processo_id}")
                return False

            # Se a execução já foi finalizada, não precisa atualizar
            if execucao.status_execucao in ['CONCLUIDO', 'FALHOU']:
                logger.info(
                    f"Execução {execucao.id} já foi finalizada com status {execucao.status_execucao}")
                return True

            logger.info(f"Job {job_id} status: {status.status}")

            if status.status == 'COMPLETED':
                # Verificar se há resultado
                if status.result and status.result.get('arquivo_fatura'):
                    logger.info(
                        f"Job {job_id} concluído com sucesso, atualizando processo")

                    # Atualizar execução com sucesso
                    execucao.finalizar_com_sucesso(
                        resultado=status.result,
                        mensagem='Job concluído com sucesso via atualização automática'
                    )

                    # Atualizar resultado_saida com o status final
                    execucao.resultado_saida = {
                        **execucao.resultado_saida,
                        'status': 'COMPLETED',
                        'result': status.result,
                        'finalizado_em': datetime.now().isoformat()
                    }

                    # Atualizar processo
                    processo.status_processo = 'DOWNLOAD_CONCLUIDO'
                    processo.url_fatura = status.result['arquivo_fatura']
                    processo.caminho_s3_fatura = status.result['arquivo_fatura']

                    # Adicionar dados da fatura se disponíveis
                    if status.result.get('valor_fatura'):
                        processo.valor_fatura = status.result['valor_fatura']
                    if status.result.get('data_vencimento'):
                        processo.data_vencimento = status.result['data_vencimento']

                    db.session.commit()
                    logger.info(
                        f"Processo {processo_id} atualizado para DOWNLOAD_CONCLUIDO")
                    return True
                else:
                    logger.warning(
                        f"Job {job_id} concluído mas sem resultado (arquivo_fatura é None)")

                    # Atualizar execução com erro
                    execucao.finalizar_com_erro(
                        Exception('Job concluído mas sem resultado'),
                        {'message':
                            'Nenhum resultado capturado (arquivo_fatura é None)'}
                    )

                    # Atualizar resultado_saida com o status final
                    execucao.resultado_saida = {
                        **execucao.resultado_saida,
                        'status': 'COMPLETED',
                        'result': None,
                        'error': 'Nenhum resultado capturado (arquivo_fatura é None)',
                        'finalizado_em': datetime.now().isoformat()
                    }

                    # Atualizar processo
                    processo.status_processo = 'ERRO_DOWNLOAD'
                    db.session.commit()
                    logger.info(
                        f"Processo {processo_id} atualizado para ERRO_DOWNLOAD")
                    return True

            elif status.status == 'FAILED':
                logger.info(f"Job {job_id} falhou, atualizando processo")

                # Atualizar execução com erro
                execucao.finalizar_com_erro(
                    Exception('Job falhou na API externa'),
                    {'message': status.error or 'Job falhou sem detalhes'}
                )

                # Atualizar processo
                processo.status_processo = 'ERRO_DOWNLOAD'
                db.session.commit()
                logger.info(
                    f"Processo {processo_id} atualizado para ERRO_DOWNLOAD")
                return True
            else:
                logger.info(
                    f"Job {job_id} ainda em andamento: {status.status}")
                return False

        except Exception as e:
            logger.error(
                f"Erro ao atualizar status do processo {processo_id} automaticamente: {str(e)}")
            db.session.rollback()
            return False

    def _processar_resultado_sucesso(self, job_id: str, status: JobStatus, processo_id: str):
        """Processa resultado de sucesso"""
        try:
            if processo_id:
                processo = Processo.query.get(processo_id)
                if processo:
                    # Determinar novo status baseado na operadora
                    if status.operadora == "SAT":
                        processo.status_processo = "SAT_CONCLUIDO"
                    else:
                        processo.status_processo = "DOWNLOAD_CONCLUIDO"

                    db.session.commit()
                    logger.info(
                        f"Status do processo {processo_id} atualizado para sucesso")

            # Log de sucesso
            log = ExecutionLog(
                job_id=job_id,
                processo_id=processo_id,
                operadora=status.operadora,
                level="INFO",
                message=f"Job {job_id} concluído com sucesso",
                details={"result": status.result}
            )
            logger.info(f"Job {job_id} concluído com sucesso: {status.result}")

        except Exception as e:
            logger.error(
                f"Erro ao processar resultado de sucesso do job {job_id}: {str(e)}")

    def _processar_resultado_falha(self, job_id: str, status: JobStatus, processo_id: str):
        """Processa resultado de falha"""
        try:
            if processo_id:
                processo = Processo.query.get(processo_id)
                if processo:
                    # Determinar novo status baseado na operadora
                    if status.operadora == "SAT":
                        processo.status_processo = "ERRO_SAT"
                    else:
                        processo.status_processo = "ERRO_DOWNLOAD"

                    db.session.commit()
                    logger.info(
                        f"Status do processo {processo_id} atualizado para erro")

            # Log de erro
            log = ExecutionLog(
                job_id=job_id,
                processo_id=processo_id,
                operadora=status.operadora,
                level="ERROR",
                message=f"Job {job_id} falhou: {status.error}",
                details={"error": status.error}
            )
            logger.error(f"Job {job_id} falhou: {status.error}")

        except Exception as e:
            logger.error(
                f"Erro ao processar resultado de falha do job {job_id}: {str(e)}")

    def cancelar_job(self, job_id: str, processo_id: str = "") -> bool:
        """
        Cancela um job em execução

        Args:
            job_id: ID do job
            processo_id: ID do processo (opcional)

        Returns:
            True se cancelado com sucesso, False caso contrário
        """
        try:
            # Cancelar na API externa
            sucesso = self.client.cancelar_job(job_id)

            if sucesso:
                # Remover do monitor
                self.monitor.remove_job(job_id)

                # Remover do cache
                self.cache.delete(job_id, processo_id)

                # Atualizar status do processo
                if processo_id:
                    processo = Processo.query.get(processo_id)
                    if processo:
                        processo.status_processo = "CANCELADO"
                        db.session.commit()

                logger.info(f"Job {job_id} cancelado com sucesso")

            return sucesso

        except Exception as e:
            logger.error(f"Erro ao cancelar job {job_id}: {str(e)}")
            return False

    def obter_logs_job(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Obtém logs detalhados de um job

        Args:
            job_id: ID do job

        Returns:
            Lista de logs
        """
        try:
            return self.client.obter_logs(job_id)
        except Exception as e:
            logger.error(f"Erro ao obter logs do job {job_id}: {str(e)}")
            return []

    def listar_jobs_processo(self, processo_id: str) -> List[JobStatus]:
        """
        Lista todos os jobs de um processo

        Args:
            processo_id: ID do processo

        Returns:
            Lista de JobStatus
        """
        try:
            return self.cache.get_by_processo(processo_id)
        except Exception as e:
            logger.error(
                f"Erro ao listar jobs do processo {processo_id}: {str(e)}")
            return []

    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do serviço

        Returns:
            Dicionário com estatísticas
        """
        try:
            cache_stats = self.cache.get_stats()
            monitor_stats = self.monitor.get_stats()

            return {
                "cache": cache_stats,
                "monitor": monitor_stats,
                "api_health": self.client.health_check(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {}

    def limpar_cache(self) -> int:
        """
        Limpa itens expirados do cache

        Returns:
            Número de itens removidos
        """
        try:
            return self.cache.cleanup_expired()
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {str(e)}")
            return 0

    def executar_download_processo(self, processo_id: str) -> Dict[str, Any]:
        """
        Executa download RPA para um processo específico

        Args:
            processo_id: ID do processo

        Returns:
            Dicionário com resultado da execução
        """
        try:
            processo = Processo.query.get(processo_id)
            if not processo:
                return {
                    'success': False,
                    'message': 'Processo não encontrado'
                }

            # Executar RPA externo
            resultado = self.executar_rpa_externo(processo, sincrono=False)

            # O método executar_rpa_externo já cria a execução e retorna JobResponse
            if hasattr(resultado, 'job_id'):
                return {
                    'success': True,
                    'message': 'Download RPA iniciado com sucesso',
                    'job_id': resultado.job_id,
                    'status': resultado.status
                }
            else:
                return {
                    'success': False,
                    'message': 'Erro ao iniciar download RPA'
                }

        except Exception as e:
            logger.error(
                f"Erro ao executar download RPA para processo {processo_id}: {str(e)}")
            return {
                'success': False,
                'message': f'Erro ao executar download: {str(e)}'
            }

    def executar_rpa_terceirizado_processo(self, processo_id: str) -> Dict[str, Any]:
        """
        Executa RPA terceirizado para um processo específico

        Args:
            processo_id: ID do processo

        Returns:
            Dicionário com resultado da execução
        """
        try:
            processo = Processo.query.get(processo_id)
            if not processo:
                return {
                    'success': False,
                    'message': 'Processo não encontrado'
                }

            # Executar RPA externo (terceirizado)
            resultado = self.executar_rpa_externo(processo, sincrono=False)

            # O método executar_rpa_externo já cria a execução e retorna JobResponse
            if hasattr(resultado, 'job_id'):
                return {
                    'success': True,
                    'message': 'RPA terceirizado iniciado com sucesso',
                    'job_id': resultado.job_id,
                    'status': resultado.status
                }
            else:
                return {
                    'success': False,
                    'message': 'Erro ao iniciar RPA terceirizado'
                }

        except Exception as e:
            logger.error(
                f"Erro ao executar RPA terceirizado para processo {processo_id}: {str(e)}")
            return {
                'success': False,
                'message': f'Erro ao executar RPA terceirizado: {str(e)}'
            }

    def executar_sat_terceirizado_processo(self, processo_id: str) -> Dict[str, Any]:
        """
        Executa SAT terceirizado para um processo específico

        Args:
            processo_id: ID do processo

        Returns:
            Dicionário com resultado da execução
        """
        try:
            processo = Processo.query.get(processo_id)
            if not processo:
                return {
                    'success': False,
                    'message': 'Processo não encontrado'
                }

            # Executar SAT externo (terceirizado)
            resultado = self.executar_sat_externo(processo, sincrono=False)

            # O método executar_sat_externo já cria a execução e retorna JobResponse
            if hasattr(resultado, 'job_id'):
                return {
                    'success': True,
                    'message': 'SAT terceirizado iniciado com sucesso',
                    'job_id': resultado.job_id,
                    'status': resultado.status
                }
            else:
                return {
                    'success': False,
                    'message': 'Erro ao iniciar SAT terceirizado'
                }

        except Exception as e:
            logger.error(
                f"Erro ao executar SAT terceirizado para processo {processo_id}: {str(e)}")
            return {
                'success': False,
                'message': f'Erro ao executar SAT terceirizado: {str(e)}'
            }
