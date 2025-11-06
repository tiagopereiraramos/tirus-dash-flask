"""
Serviços para integração com API Externa em Produção
URL: http://191.252.218.230:8000
Documentação: DOCUMENTACAO_INTEGRACAO_FRONTEND.md
"""

import requests
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from apps import db
from apps.models import Processo, Cliente, Operadora, Execucao
from apps.models.execucao import TipoExecucao, StatusExecucao
from .models import (
    AutomacaoPayload,
    AutomacaoPayloadSat,
    JobResponse,
    JobStatus
)
from .auth import get_auth

logger = logging.getLogger(__name__)


class APIExternaService:
    """
    Serviço para comunicação com API Externa em Produção
    
    Esta classe gerencia toda a integração com a API RPA externa,
    incluindo criação de payloads, envio de requisições e monitoramento de jobs.
    """

    def __init__(self, base_url: str = "http://191.252.218.230:8000"):
        """
        Inicializa o serviço de API externa
        
        Args:
            base_url: URL base da API externa em produção
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = 30  # Timeout para criação de jobs (não para execução)
        self.auth = get_auth()
        
        logger.info(f"APIExternaService inicializado: {self.base_url}")

    def criar_payload_operadora(self, processo: Processo) -> AutomacaoPayload:
        """
        Cria payload para execução de RPA em operadora (OI, VIVO, EMBRATEL, DIGITALNET)
        
        Args:
            processo: Processo do banco de dados
            
        Returns:
            AutomacaoPayload com dados formatados para a API
            
        Raises:
            ValueError: Se dados obrigatórios estiverem faltando
        """
        try:
            cliente = processo.cliente
            operadora = processo.cliente.operadora

            # Determinar login com base na operadora
            if cliente.login_portal:
                login = cliente.login_portal
            elif operadora.codigo == 'OI':
                # Para OI, usar filtro como login
                login = cliente.filtro or cliente.cnpj
            else:
                # Para outras, usar CNPJ
                login = cliente.cnpj

            # Valores com fallback
            senha = cliente.senha_portal or "senha123"
            filtro = cliente.filtro or "fatura_mensal"
            cnpj = cliente.cnpj or "00000000000000"

            # Criar payload
            payload = AutomacaoPayload(
                login=login,
                senha=senha,
                filtro=filtro,
                cnpj=cnpj,
                processo_id=str(processo.id)  # IMPORTANTE: Adicionar processo_id para rastreamento
            )

            # Validar
            erros = payload.validate()
            if erros:
                raise ValueError(f"Payload inválido: {', '.join(erros)}")

            logger.info(f"Payload operadora criado para processo {processo.id}")
            return payload

        except Exception as e:
            logger.error(f"Erro ao criar payload operadora: {str(e)}")
            raise

    def criar_payload_sat(self, processo: Processo) -> AutomacaoPayloadSat:
        """
        Cria payload para upload no SAT
        
        Args:
            processo: Processo do banco de dados
            
        Returns:
            AutomacaoPayloadSat com dados formatados para a API
            
        Raises:
            ValueError: Se dados obrigatórios estiverem faltando
        """
        try:
            cliente = processo.cliente
            operadora = processo.cliente.operadora

            # Valores com fallback
            cnpj = cliente.cnpj or "00000000000000"
            filtro = cliente.filtro or "fatura_mensal"

            # Gerar nome do arquivo
            nome_arquivo = f"fatura_{processo.mes_ano.replace('/', '_')}.pdf"

            # IMPORTANTE: Formato de data DD/MM/YYYY conforme documentação
            if processo.data_vencimento:
                data_vencimento = processo.data_vencimento.strftime("%d/%m/%Y")
            else:
                data_vencimento = "15/08/2025"

            # Criar payload SAT (sem login/senha/filtro - vêm de ENV na API externa)
            payload = AutomacaoPayloadSat(
                cnpj=cnpj,
                razao=cliente.razao_social or "EMPRESA LTDA",
                operadora=operadora.codigo if operadora else "UNK",
                nome_filtro=filtro,
                unidade=cliente.unidade or "MATRIZ",
                servico=cliente.servico or "INTERNET_DEDICADA",
                dados_sat=cliente.dados_sat or f"{cliente.nome_sat or cliente.razao_social}|INTERNET|DEDICADA",
                nome_arquivo=nome_arquivo,
                data_vencimento=data_vencimento,
                processo_id=str(processo.id)
            )

            # Validar
            erros = payload.validate()
            if erros:
                raise ValueError(f"Payload SAT inválido: {', '.join(erros)}")

            # DEBUG: Log do payload completo
            import json
            logger.info(f"Payload SAT criado para processo {processo.id}")
            logger.debug(f"Payload SAT JSON: {json.dumps(payload.to_dict(), indent=2, ensure_ascii=False)}")
            return payload

        except Exception as e:
            logger.error(f"Erro ao criar payload SAT: {str(e)}")
            raise

    def executar_operadora(self, processo: Processo) -> JobResponse:
        """
        Executa RPA para operadora (cria job assíncrono)
        
        Args:
            processo: Processo do banco de dados
            
        Returns:
            JobResponse com informações do job criado
            
        Raises:
            ValueError: Se operadora for inválida
            requests.RequestException: Se houver erro na comunicação
        """
        execucao = None
        
        try:
            operadora = processo.cliente.operadora
            if not operadora:
                raise ValueError("Processo não possui operadora associada")

            # IMPORTANTE: Endpoint com operadora em UPPERCASE conforme documentação
            endpoint = f"/executar/{operadora.codigo.upper()}"
            
            logger.info(f"Executando operadora {operadora.codigo} para processo {processo.id}")

            # Criar execução para rastreamento
            execucao = Execucao(
                processo_id=processo.id,
                tipo_execucao=TipoExecucao.DOWNLOAD_FATURA.value,
                status_execucao=StatusExecucao.EXECUTANDO.value,
                classe_rpa_utilizada="API_EXTERNA_PRODUCAO",
                parametros_entrada={
                    "operadora": operadora.codigo,
                    "endpoint": endpoint
                },
                data_inicio=datetime.now()
            )
            db.session.add(execucao)
            db.session.commit()

            # Criar payload
            payload = self.criar_payload_operadora(processo)
            payload_dict = payload.to_dict()

            # IMPORTANTE: Headers com autenticação JWT
            headers = self.auth.get_headers()

            # Fazer requisição
            url = f"{self.base_url}{endpoint}"
            logger.debug(f"POST {url}")
            
            response = requests.post(
                url,
                json=payload_dict,
                headers=headers,
                timeout=self.timeout
            )

            # Processar resposta
            if response.status_code == 200:
                data = response.json()
                job_response = JobResponse.from_dict(data)

                # Atualizar execução com job_id (campo direto para SSE)
                execucao.job_id = job_response.job_id
                execucao.parametros_entrada['job_id'] = job_response.job_id
                db.session.commit()

                logger.info(f"Job criado: {job_response.job_id} para processo {processo.id}")
                return job_response

            else:
                erro_msg = f"Erro HTTP {response.status_code}: {response.text}"
                if execucao:
                    execucao.finalizar_com_erro(Exception(erro_msg))
                    db.session.commit()
                
                logger.error(erro_msg)
                raise requests.RequestException(erro_msg)

        except Exception as e:
            logger.error(f"Erro ao executar operadora: {str(e)}")
            if execucao:
                execucao.finalizar_com_erro(Exception(str(e)))
                db.session.commit()
            raise

    def executar_sat(self, processo: Processo) -> JobResponse:
        """
        Executa upload no SAT (cria job assíncrono)
        
        Args:
            processo: Processo do banco de dados
            
        Returns:
            JobResponse com informações do job criado
            
        Raises:
            requests.RequestException: Se houver erro na comunicação
        """
        execucao = None
        
        try:
            endpoint = "/executar/sat"
            
            logger.info(f"Executando SAT para processo {processo.id}")

            # Criar execução para rastreamento
            execucao = Execucao(
                processo_id=processo.id,
                tipo_execucao=TipoExecucao.UPLOAD_SAT.value,
                status_execucao=StatusExecucao.EXECUTANDO.value,
                classe_rpa_utilizada="API_EXTERNA_SAT_PRODUCAO",
                parametros_entrada={"endpoint": endpoint},
                data_inicio=datetime.now()
            )
            db.session.add(execucao)
            db.session.commit()

            # Criar payload
            payload = self.criar_payload_sat(processo)
            payload_dict = payload.to_dict()

            # IMPORTANTE: Headers com autenticação JWT
            headers = self.auth.get_headers()

            # Fazer requisição
            url = f"{self.base_url}{endpoint}"
            logger.debug(f"POST {url}")
            
            response = requests.post(
                url,
                json=payload_dict,
                headers=headers,
                timeout=self.timeout
            )

            # Processar resposta
            if response.status_code == 200:
                data = response.json()
                job_response = JobResponse.from_dict(data)

                # Atualizar execução com job_id (campo direto para SSE)
                execucao.job_id = job_response.job_id
                execucao.parametros_entrada['job_id'] = job_response.job_id
                db.session.commit()

                logger.info(f"Job SAT criado: {job_response.job_id} para processo {processo.id}")
                return job_response

            else:
                erro_msg = f"Erro HTTP {response.status_code}: {response.text}"
                if execucao:
                    execucao.finalizar_com_erro(Exception(erro_msg))
                    db.session.commit()
                
                logger.error(erro_msg)
                raise requests.RequestException(erro_msg)

        except Exception as e:
            logger.error(f"Erro ao executar SAT: {str(e)}")
            if execucao:
                execucao.finalizar_com_erro(Exception(str(e)))
                db.session.commit()
            raise

    def consultar_status(self, job_id: str) -> JobStatus:
        """
        Consulta o status de um job
        
        Args:
            job_id: ID do job a consultar
            
        Returns:
            JobStatus com informações atualizadas do job
            
        Raises:
            requests.RequestException: Se houver erro na comunicação
        """
        try:
            endpoint = f"/status/{job_id}"
            headers = self.auth.get_headers()
            url = f"{self.base_url}{endpoint}"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return JobStatus.from_api_response(data)
            elif response.status_code == 404:
                raise ValueError(f"Job {job_id} não encontrado")
            else:
                raise requests.RequestException(f"Erro HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Erro ao consultar status do job {job_id}: {str(e)}")
            raise

    def health_check(self) -> bool:
        """
        Verifica se a API externa está funcionando
        
        Returns:
            True se API está saudável, False caso contrário
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check falhou: {str(e)}")
            return False
