"""
Serviços para APIs Externas
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
    PayloadRPAExterno, RespostaRPAExterno,
    PayloadSATExterno, RespostaSATExterno,
    PayloadRPAProducao, PayloadSATProducao, RespostaProducao,
    TipoOperacaoExterna, StatusOperacaoExterna,
    DadosCliente, DadosOperadora, DadosProcesso, DadosExecucao, Metadata
)

logger = logging.getLogger(__name__)


class APIExternaService:
    """Serviço para comunicação com APIs externas"""

    def __init__(self):
        self.timeout = 300  # 5 minutos
        self.tentativas_maximas = 3

    def criar_payload_rpa(self, processo: Processo) -> PayloadRPAExterno:
        """Cria payload para envio ao RPA externo usando novos modelos"""
        try:
            cliente = processo.cliente
            operadora = processo.cliente.operadora

            # Criar dados do cliente
            dados_cliente = DadosCliente(
                id=str(cliente.id),
                razao_social=cliente.razao_social,
                nome_sat=cliente.nome_sat or cliente.razao_social,
                cnpj=cliente.cnpj,
                email=cliente.email,
                telefone=cliente.telefone,
                login_portal=cliente.login_portal,
                senha_portal=cliente.senha_portal,
                cpf=cliente.cpf,
                endereco={
                    "logradouro": cliente.logradouro,
                    "numero": cliente.numero,
                    "complemento": cliente.complemento,
                    "bairro": cliente.bairro,
                    "cidade": cliente.cidade,
                    "estado": cliente.estado,
                    "cep": cliente.cep
                } if cliente.logradouro else None
            )

            # Criar dados da operadora
            dados_operadora = DadosOperadora(
                id=str(operadora.id),
                codigo=operadora.codigo,
                nome=operadora.nome,
                url_portal=operadora.portal_url or f"https://portal.{operadora.nome.lower()}.com.br",
                usuario_portal=operadora.usuario_portal,
                senha_portal=operadora.senha_portal,
                tipo_autenticacao=operadora.tipo_autenticacao,
                timeout_segundos=operadora.timeout_segundos or 300,
                tentativas_maximas=operadora.tentativas_maximas or 3,
                intervalo_tentativas=operadora.intervalo_tentativas or 60
            )

            # Criar dados do processo
            dados_processo = DadosProcesso(
                id=str(processo.id),
                mes_ano=processo.mes_ano,
                status_atual=processo.status_processo,
                url_fatura=processo.url_fatura,
                data_vencimento=processo.data_vencimento.isoformat(
                ) if processo.data_vencimento else None,
                valor_fatura=float(
                    processo.valor_fatura) if processo.valor_fatura else None,
                observacoes=processo.observacoes
            )

            # Criar dados da execução
            dados_execucao = DadosExecucao(
                numero_tentativa=1,
                ip_origem="192.168.1.100",  # TODO: Obter IP real
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            # Criar metadata
            metadata = Metadata(
                modo_teste=False
            )

            # Criar payload completo
            payload = PayloadRPAExterno(
                processo_id=str(processo.id),
                operacao=TipoOperacaoExterna.DOWNLOAD_FATURA.value,
                cliente=dados_cliente,
                operadora=dados_operadora,
                processo=dados_processo,
                execucao=dados_execucao,
                metadata=metadata
            )

            # Validar payload
            erros = payload.validar()
            if erros:
                raise ValueError(f"Payload inválido: {', '.join(erros)}")

            logger.info(
                f"Payload RPA criado com sucesso para processo {processo.id}")
            return payload

        except Exception as e:
            logger.error(f"Erro ao criar payload RPA: {str(e)}")
            raise

    def criar_payload_sat(self, processo: Processo) -> PayloadSATExterno:
        """Cria payload para upload no SAT usando novos modelos"""
        try:
            cliente = processo.cliente

            # Criar metadata
            metadata = Metadata(
                modo_teste=False
            )

            payload = PayloadSATExterno(
                processo_id=str(processo.id),
                cliente_nome_sat=cliente.nome_sat or cliente.razao_social,
                dados_sat=f"{cliente.nome_sat or cliente.razao_social}|INTERNET|DEDICADA",
                arquivo_fatura={
                    "nome_arquivo": f"fatura_{processo.mes_ano.replace('/', '_')}.pdf",
                    "url_arquivo": processo.url_fatura,
                    "tamanho_bytes": 1024 * 512,  # 512KB simulado
                    "tipo_mime": "application/pdf"
                },
                metadados={
                    "mes_ano": processo.mes_ano,
                    "valor_fatura": float(processo.valor_fatura) if processo.valor_fatura else 0.0,
                    "data_vencimento": processo.data_vencimento.isoformat() if processo.data_vencimento else None,
                    "timestamp_upload": datetime.now().isoformat()
                },
                metadata=metadata
            )

            # Validar payload
            erros = payload.validar()
            if erros:
                raise ValueError(f"Payload SAT inválido: {', '.join(erros)}")

            logger.info(
                f"Payload SAT criado com sucesso para processo {processo.id}")
            return payload

        except Exception as e:
            logger.error(f"Erro ao criar payload SAT: {str(e)}")
            raise

    def criar_payload_rpa_producao(self, processo: Processo) -> PayloadRPAProducao:
        """Cria payload simplificado para API em produção - Operadoras"""
        try:
            cliente = processo.cliente
            operadora = processo.cliente.operadora

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

            # Mapear dados para formato simplificado
            payload = PayloadRPAProducao(
                login=login,
                senha=senha,
                filtro=filtro,
                cnpj=cnpj
            )

            # Validar payload
            erros = payload.validar()
            if erros:
                raise ValueError(f"Payload inválido: {', '.join(erros)}")

            logger.info(
                f"Payload RPA produção criado com sucesso para processo {processo.id}")
            return payload

        except Exception as e:
            logger.error(f"Erro ao criar payload RPA produção: {str(e)}")
            raise

    def criar_payload_sat_producao(self, processo: Processo) -> PayloadSATProducao:
        """Cria payload simplificado para API em produção - SAT"""
        try:
            cliente = processo.cliente
            operadora = processo.cliente.operadora

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

            # Gerar nome do arquivo
            nome_arquivo = f"fatura_{processo.mes_ano.replace('/', '_')}.pdf"

            # Formatar data de vencimento
            data_vencimento = processo.data_vencimento.strftime(
                "%Y-%m-%d") if processo.data_vencimento else "2025-08-15"

            payload = PayloadSATProducao(
                login=login,
                senha=senha,
                filtro=filtro,
                cnpj=cnpj,
                razao=cliente.razao_social or "EMPRESA LTDA",
                operadora=operadora.codigo if operadora else "UNK",
                nome_filtro=cliente.filtro or "fatura_mensal",
                unidade=cliente.unidade or "MATRIZ",
                servico=cliente.servico or "INTERNET_DEDICADA",
                dados_sat=cliente.dados_sat or f"{cliente.nome_sat or cliente.razao_social}|INTERNET|DEDICADA",
                nome_arquivo=nome_arquivo,
                data_vencimento=data_vencimento
            )

            # Validar payload
            erros = payload.validar()
            if erros:
                raise ValueError(
                    f"Payload SAT produção inválido: {', '.join(erros)}")

            logger.info(
                f"Payload SAT produção criado com sucesso para processo {processo.id}")
            return payload

        except Exception as e:
            logger.error(f"Erro ao criar payload SAT produção: {str(e)}")
            raise

    def enviar_para_rpa_externo(self, processo: Processo, url_endpoint: Optional[str] = None) -> RespostaRPAExterno:
        """Envia processo para RPA externo"""
        try:
            # Usar endpoint da operadora se não fornecido manualmente
            if not url_endpoint:
                operadora = processo.cliente.operadora
                if operadora and operadora.rpa_terceirizado and operadora.url_endpoint_rpa:
                    url_endpoint = operadora.url_endpoint_rpa
                else:
                    raise ValueError(
                        "Operadora não possui endpoint RPA terceirizado configurado")

            logger.info(
                f"Enviando processo {processo.id} para RPA externo: {url_endpoint}")

            # Criar execução para rastreamento
            execucao = Execucao(
                processo_id=processo.id,
                tipo_execucao=TipoExecucao.DOWNLOAD_FATURA.value,
                status_execucao=StatusExecucao.EXECUTANDO.value,
                classe_rpa_utilizada="RPA_EXTERNO",
                parametros_entrada={"url_endpoint": url_endpoint},
                data_inicio=datetime.now()
            )

            db.session.add(execucao)
            db.session.commit()

            # Criar payload
            payload = self.criar_payload_rpa(processo)
            payload_dict = payload.to_dict()

            # Configurar headers
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'TIRUS-DASH-FLASK/2.0',
                'X-Request-ID': payload.metadata.request_id
            }

            # Fazer requisição para RPA externo
            logger.debug(f"Enviando requisição para: {url_endpoint}")
            response = requests.post(
                url_endpoint,
                json=payload_dict,
                headers=headers,
                timeout=self.timeout
            )

            # Processar resposta
            if response.status_code == 200:
                resultado = response.json()

                # Criar resposta padronizada
                resposta = RespostaRPAExterno.from_dict(resultado)

                # Atualizar execução com sucesso
                execucao.finalizar_com_sucesso(
                    resultado=resultado,
                    mensagem=f"Execução RPA externo concluída com sucesso. Status: {resposta.status}"
                )

                # Atualizar processo se necessário
                if resposta.success and resposta.resultado:
                    processo.marcar_download_completo()
                    if resposta.resultado.get('url_arquivo'):
                        processo.url_fatura = resposta.resultado.get(
                            'url_arquivo')
                    if resposta.resultado.get('dados_extraidos', {}).get('valor_fatura'):
                        processo.valor_fatura = resposta.resultado['dados_extraidos']['valor_fatura']

                db.session.commit()

                logger.info(
                    f"Processo {processo.id} enviado com sucesso para RPA externo")
                return resposta

            else:
                # Tratar erro HTTP
                erro_msg = f"Erro HTTP {response.status_code}: {response.text}"
                execucao.finalizar_com_erro(
                    Exception(erro_msg),
                    {"status_code": response.status_code,
                        "response_text": response.text}
                )
                db.session.commit()

                logger.error(
                    f"Erro HTTP ao enviar processo {processo.id}: {erro_msg}")
                return RespostaRPAExterno(
                    success=False,
                    processo_id=str(processo.id),
                    erro=erro_msg,
                    request_id=payload.metadata.request_id
                )

        except requests.exceptions.Timeout:
            erro_msg = "Timeout na requisição para RPA externo"
            execucao.marcar_timeout()
            db.session.commit()

            logger.error(
                f"Timeout ao enviar processo {processo.id} para RPA externo")
            return RespostaRPAExterno(
                success=False,
                processo_id=str(processo.id),
                erro=erro_msg,
                request_id=payload.metadata.request_id if 'payload' in locals() else None
            )

        except requests.exceptions.RequestException as e:
            erro_msg = f"Erro de conexão: {str(e)}"
            execucao.finalizar_com_erro(Exception(erro_msg))
            db.session.commit()

            logger.error(
                f"Erro de conexão ao enviar processo {processo.id}: {str(e)}")
            return RespostaRPAExterno(
                success=False,
                processo_id=str(processo.id),
                erro=erro_msg,
                request_id=payload.metadata.request_id if 'payload' in locals() else None
            )

        except Exception as e:
            erro_msg = f"Erro inesperado: {str(e)}"
            execucao.finalizar_com_erro(Exception(erro_msg))
            db.session.commit()

            logger.error(
                f"Erro inesperado ao enviar processo {processo.id}: {str(e)}")
            return RespostaRPAExterno(
                success=False,
                processo_id=str(processo.id),
                erro=erro_msg,
                request_id=payload.metadata.request_id if 'payload' in locals() else None
            )

    def enviar_para_sat_externo(self, processo: Processo, url_endpoint: Optional[str] = None) -> RespostaSATExterno:
        """Envia processo para SAT externo"""
        try:
            # TODO: Implementar lógica similar ao RPA externo
            # Por enquanto, retorna resposta simulada
            logger.info(f"Enviando processo {processo.id} para SAT externo")

            payload = self.criar_payload_sat(processo)

            return RespostaSATExterno(
                success=True,
                processo_id=str(processo.id),
                protocolo_sat=f"SAT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
                mensagem="Upload para SAT realizado com sucesso",
                request_id=payload.metadata.request_id
            )

        except Exception as e:
            logger.error(
                f"Erro ao enviar processo {processo.id} para SAT externo: {str(e)}")
            return RespostaSATExterno(
                success=False,
                processo_id=str(processo.id),
                erro=str(e)
            )

    def enviar_para_rpa_producao(self, processo: Processo, url_base: str = "http://191.252.218.230:8000") -> RespostaProducao:
        """Envia processo para RPA em produção"""
        try:
            operadora = processo.cliente.operadora
            if not operadora:
                raise ValueError("Processo não possui operadora associada")

            logger.info(
                f"Enviando processo {processo.id} para RPA produção: {operadora.codigo}")

            # Criar execução para rastreamento
            execucao = Execucao(
                processo_id=processo.id,
                tipo_execucao=TipoExecucao.DOWNLOAD_FATURA.value,
                status_execucao=StatusExecucao.EXECUTANDO.value,
                classe_rpa_utilizada="RPA_PRODUCAO",
                parametros_entrada={"url_base": url_base,
                                    "operadora": operadora.codigo},
                data_inicio=datetime.now()
            )

            db.session.add(execucao)
            db.session.commit()

            # Criar payload simplificado
            payload = self.criar_payload_rpa_producao(processo)
            payload_dict = payload.to_dict()

            # Construir URL do endpoint
            endpoint_url = f"{url_base}/executar/{operadora.codigo.lower()}"

            # Configurar headers
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'TIRUS-DASH-FLASK/2.0'
            }

            # Fazer requisição para RPA em produção
            logger.debug(f"Enviando requisição para: {endpoint_url}")
            response = requests.post(
                endpoint_url,
                json=payload_dict,
                headers=headers,
                timeout=self.timeout
            )

            # Processar resposta
            if response.status_code == 200:
                resultado = response.json()
                resposta = RespostaProducao.from_dict(resultado)

                # Atualizar execução com sucesso
                execucao.finalizar_com_sucesso(
                    resultado=resultado,
                    mensagem=f"Execução RPA produção concluída. Status: {resposta.success}"
                )

                # Atualizar processo se necessário
                if resposta.success and resposta.data:
                    processo.marcar_download_completo()
                    # TODO: Extrair dados específicos da resposta se disponíveis

                db.session.commit()

                logger.info(
                    f"Processo {processo.id} enviado com sucesso para RPA produção")
                return resposta

            else:
                # Tratar erro HTTP
                erro_msg = f"Erro HTTP {response.status_code}: {response.text}"
                execucao.finalizar_com_erro(
                    Exception(erro_msg),
                    {"status_code": response.status_code,
                        "response_text": response.text}
                )
                db.session.commit()

                logger.error(
                    f"Erro HTTP ao enviar processo {processo.id}: {erro_msg}")
                return RespostaProducao(
                    success=False,
                    error=erro_msg,
                    message=f"Erro na API de produção: {erro_msg}"
                )

        except requests.exceptions.Timeout:
            erro_msg = "Timeout na requisição para RPA produção"
            execucao.marcar_timeout()
            db.session.commit()

            logger.error(
                f"Timeout ao enviar processo {processo.id} para RPA produção")
            return RespostaProducao(
                success=False,
                error=erro_msg,
                message="Timeout na execução"
            )

        except requests.exceptions.RequestException as e:
            erro_msg = f"Erro de conexão: {str(e)}"
            execucao.finalizar_com_erro(Exception(erro_msg))
            db.session.commit()

            logger.error(
                f"Erro de conexão ao enviar processo {processo.id}: {str(e)}")
            return RespostaProducao(
                success=False,
                error=erro_msg,
                message=f"Erro de conexão: {str(e)}"
            )

        except Exception as e:
            erro_msg = f"Erro inesperado: {str(e)}"
            execucao.finalizar_com_erro(Exception(erro_msg))
            db.session.commit()

            logger.error(
                f"Erro inesperado ao enviar processo {processo.id}: {str(e)}")
            return RespostaProducao(
                success=False,
                error=erro_msg,
                message=f"Erro interno: {str(e)}"
            )

    def enviar_para_sat_producao(self, processo: Processo, url_base: str = "http://191.252.218.230:8000") -> RespostaProducao:
        """Envia processo para SAT em produção"""
        try:
            logger.info(f"Enviando processo {processo.id} para SAT produção")

            # Criar execução para rastreamento
            execucao = Execucao(
                processo_id=processo.id,
                tipo_execucao=TipoExecucao.UPLOAD_SAT.value,
                status_execucao=StatusExecucao.EXECUTANDO.value,
                classe_rpa_utilizada="SAT_PRODUCAO",
                parametros_entrada={"url_base": url_base},
                data_inicio=datetime.now()
            )

            db.session.add(execucao)
            db.session.commit()

            # Criar payload simplificado
            payload = self.criar_payload_sat_producao(processo)
            payload_dict = payload.to_dict()

            # Construir URL do endpoint
            endpoint_url = f"{url_base}/executar/sat"

            # Configurar headers
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'TIRUS-DASH-FLASK/2.0'
            }

            # Fazer requisição para SAT em produção
            logger.debug(f"Enviando requisição para: {endpoint_url}")
            response = requests.post(
                endpoint_url,
                json=payload_dict,
                headers=headers,
                timeout=self.timeout
            )

            # Processar resposta
            if response.status_code == 200:
                resultado = response.json()
                resposta = RespostaProducao.from_dict(resultado)

                # Atualizar execução com sucesso
                execucao.finalizar_com_sucesso(
                    resultado=resultado,
                    mensagem=f"Execução SAT produção concluída. Status: {resposta.success}"
                )

                # Atualizar processo se necessário
                if resposta.success:
                    processo.marcar_upload_sat_completo()
                    # TODO: Extrair protocolo SAT da resposta se disponível

                db.session.commit()

                logger.info(
                    f"Processo {processo.id} enviado com sucesso para SAT produção")
                return resposta

            else:
                # Tratar erro HTTP
                erro_msg = f"Erro HTTP {response.status_code}: {response.text}"
                execucao.finalizar_com_erro(
                    Exception(erro_msg),
                    {"status_code": response.status_code,
                        "response_text": response.text}
                )
                db.session.commit()

                logger.error(
                    f"Erro HTTP ao enviar processo {processo.id}: {erro_msg}")
                return RespostaProducao(
                    success=False,
                    error=erro_msg,
                    message=f"Erro na API de produção: {erro_msg}"
                )

        except requests.exceptions.Timeout:
            erro_msg = "Timeout na requisição para SAT produção"
            execucao.marcar_timeout()
            db.session.commit()

            logger.error(
                f"Timeout ao enviar processo {processo.id} para SAT produção")
            return RespostaProducao(
                success=False,
                error=erro_msg,
                message="Timeout na execução"
            )

        except requests.exceptions.RequestException as e:
            erro_msg = f"Erro de conexão: {str(e)}"
            execucao.finalizar_com_erro(Exception(erro_msg))
            db.session.commit()

            logger.error(
                f"Erro de conexão ao enviar processo {processo.id}: {str(e)}")
            return RespostaProducao(
                success=False,
                error=erro_msg,
                message=f"Erro de conexão: {str(e)}"
            )

        except Exception as e:
            erro_msg = f"Erro inesperado: {str(e)}"
            execucao.finalizar_com_erro(Exception(erro_msg))
            db.session.commit()

            logger.error(
                f"Erro inesperado ao enviar processo {processo.id}: {str(e)}")
            return RespostaProducao(
                success=False,
                error=erro_msg,
                message=f"Erro interno: {str(e)}"
            )
